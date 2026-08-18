#!/usr/bin/env python3
"""aios.ambient.v1 — AIOS organs that run without being named.

Founder: reconstitute Claude/Codex features as AIOS and have them used organically,
without explicit invocation.

Measured 2026-08-18: eleven ambient hook events are available and AIOS was using five.
Three of the six idle ones map exactly onto holes measured today, so they are wired here
rather than left as capabilities we own and never fire:

  SubagentStart/Stop   a session is born / dies -> mesh self-registration.
                       ListAgents showed 40 live sessions named things like "I cannot
                       generate a specific coding task title". Identity was the gap, and
                       asking every session to register itself by hand would never happen.

  PostToolUseFailure   the diagnostic signature. THE M1 gate died because every failure
                       collapsed to fail_reason="oracle_failed": 0.811 bits, no test id,
                       no assertion, no file:line. Capturing it at the moment of failure
                       is the only place that information still exists.

  PermissionRequest    an authority decision is being made -> record it against our
                       side-effect ladder. Provider policy and our policy are different
                       objects and we should be able to see where they disagree.

Design rules for anything ambient: never raise, never block, never print to stdout unless
the event contract expects it, and always be cheap. A hook that costs a second costs it on
every tool call.
"""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
OUT = ROOT / ".aios" / "ambient"
FAILSIG = OUT / "failure_signatures.jsonl"
USESIG = OUT / "use_signals.jsonl"
AUTH = OUT / "authority_events.jsonl"

sys.path.insert(0, str(ROOT / "scripts"))

# the fields M1's gate named as the minimum for a usable failure signature
TEST_RE = re.compile(r"(?:FAILED|ERROR)\s+([\w/\.]+::[\w\[\]\-\.]+)")
ASSERT_RE = re.compile(r"(?m)^E\s+(.{0,180})")
# both shapes: pytest's "x.py:42" and CPython's 'File "x.py", line 42'
FILELINE_RE = re.compile(r'File "([^"]+\.py)", line (\d+)|([\w/\.\-]+\.py):(\d+)')
EXIT_CLASS = [("assert", r"AssertionError|assert "), ("import", r"ImportError|ModuleNotFound"),
              ("timeout", r"Timeout|timed out|TimeoutError"), ("syntax", r"SyntaxError"),
              ("type", r"TypeError"), ("attr", r"AttributeError"), ("key", r"KeyError"),
              ("crash", r"Traceback \(most recent")]


def append(p: Path, obj: dict) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass                                   # ambient code never breaks the session


def classify(text: str) -> str:
    for name, pat in EXIT_CLASS:
        if re.search(pat, text):
            return name
    return "unknown"


def on_failure(ev: dict) -> None:
    """Capture what M1 needed and never had — at the only moment it exists."""
    blob = " ".join(str(ev.get(k, "")) for k in
                    ("error", "stderr", "output", "tool_response", "result", "message"))[:20000]
    if not blob.strip():
        return
    tb = [l for l in blob.splitlines() if l.strip()][:3]
    fl = FILELINE_RE.findall(blob)
    append(FAILSIG, {
        "ts": time.time(),
        "session_id": ev.get("session_id", ""),
        "tool_name": ev.get("tool_name", ""),
        "failing_test_id": (TEST_RE.search(blob).group(1) if TEST_RE.search(blob) else ""),
        "assertion": (ASSERT_RE.search(blob).group(1).strip() if ASSERT_RE.search(blob) else ""),
        "file_line": (lambda g: f"{g[0] or g[2]}:{g[1] or g[3]}" if fl else "")(fl[0]) if fl else "",
        "traceback_head": tb,
        "exit_class": classify(blob),           # a CLASS, not an rc
    })


def on_subagent(ev: dict, starting: bool) -> None:
    try:
        import aios_mesh as mesh
    except Exception:
        return
    sid = (ev.get("session_id") or "")[:12]
    agent = ev.get("agent_type") or ev.get("subagent_type") or "subagent"
    name = f"claude@{ROOT.name}/{agent}-{sid}" if sid else f"claude@{ROOT.name}/{agent}"
    try:
        if starting:
            mesh.register(name, role=agent, workspace=ROOT.name,
                          domains=[agent], skills=[], ceiling="L1_local_write",
                          pid=os.getppid())
        else:
            mesh.heartbeat(name)
            append(OUT / "subagent_lifecycle.jsonl",
                   {"ts": time.time(), "name": name, "event": "stop"})
    except Exception:
        pass


def on_permission(ev: dict) -> None:
    """Provider policy and our ladder are different objects. Record where they meet."""
    append(AUTH, {"ts": time.time(), "session_id": ev.get("session_id", ""),
                  "tool_name": ev.get("tool_name", ""),
                  "decision": ev.get("decision") or ev.get("permission_result", ""),
                  "raw_keys": sorted(ev)[:12]})


RETRIEVAL_TOOLS = {"Read", "Grep", "Glob", "WebFetch", "WebSearch"}


def on_tool(ev: dict) -> None:
    """The use signal. memoryOS has 397,854 nodes and zero retrieval counts; nothing will
    ever fill that by being remembered, so it is filled by happening."""
    tn = ev.get("tool_name", "")
    if tn not in RETRIEVAL_TOOLS:
        return
    inp = ev.get("tool_input") or {}
    target = (inp.get("file_path") or inp.get("pattern") or inp.get("query")
              or inp.get("url") or "")
    if not target:
        return
    append(USESIG, {"ts": time.time(), "tool": tn, "target": str(target)[:300],
                    "session_id": ev.get("session_id", "")})


def main() -> int:
    try:
        ev = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    kind = ev.get("hook_event_name") or ev.get("event") or ""
    try:
        if kind == "PostToolUseFailure":
            on_failure(ev)
        elif kind == "SubagentStart":
            on_subagent(ev, True)
        elif kind == "SubagentStop":
            on_subagent(ev, False)
        elif kind == "PermissionRequest":
            on_permission(ev)
        elif kind == "PostToolUse":
            on_tool(ev)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
