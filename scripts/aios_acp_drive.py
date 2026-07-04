#!/usr/bin/env python3
"""AIOS ACP drive — the INVERSION OF CONTROL organ.

Thesis: an OS does not get *injected into* processes — it RUNS them.

Every other AIOS attachment rung so far has AIOS ride *inside* a provider agent
as a passenger: a SessionStart hook that injects the composite SELF, an MCP
server that adds tools to the agent's list. In all of those the provider agent
is the operating system and AIOS is a plugin it may or may not consult. `aios
drive` inverts that. It makes **AIOS the ACP client — the operating system —
and the provider agent (Claude Code, Gemini CLI) an ACP *server*: an engine
AIOS runs.** AIOS owns the goal, injects the composite SELF at session start
(attempt-1 policy — never re-sent), adjudicates *every* permission request the
engine raises against the privacy DNA (fail-closed), records an append-only run
receipt, and can swap one engine for another under the same control loop. This
is the strongest attachment rung (2026-07 design re-validation: "ACP is the
next required adapter").

Protocol: Agent Client Protocol (ACP), grounded 2026-07-04 from the live spec
(newer than model weights) — sources:
  - https://agentclientprotocol.com/protocol/overview
  - https://agentclientprotocol.com/protocol/initialization
  - https://agentclientprotocol.com/protocol/tool-calls
  - github.com/zed-industries/agent-client-protocol
Verified facts baked in below:
  * protocolVersion is an INTEGER, currently 1 (not a semver string).
  * Transport is newline-delimited JSON-RPC 2.0 over the child's stdio (one
    JSON object per line — the same framing scripts/aios_mcp_server.py uses on
    the server side). NOT LSP Content-Length framing.
  * initialize params: {protocolVersion, clientCapabilities:{fs:{readTextFile,
    writeTextFile}, terminal}, clientInfo}. We advertise fs.readTextFile /
    fs.writeTextFile = FALSE for v1 so the engine uses its OWN filesystem.
  * session/new params: {cwd (absolute), mcpServers[]} -> result {sessionId}.
  * session/prompt params: {sessionId, prompt: ContentBlock[]} -> result
    {stopReason}. ContentBlock text = {type:"text", text:"..."}.
  * session/update NOTIFICATION params: {sessionId, update:{sessionUpdate:
    <variant>, ...}} where variant ∈ agent_message_chunk (content block),
    tool_call (title/kind/status/locations/rawInput/toolCallId),
    tool_call_update, plan (entries).
  * session/request_permission REQUEST params: {sessionId, toolCall,
    options:[{optionId, name, kind}]}, kind ∈ allow_once|allow_always|
    reject_once|reject_always. RESPONSE result: {outcome:{outcome:"selected",
    optionId:"..."}} or {outcome:{outcome:"cancelled"}}.
  * stopReason ∈ end_turn|max_tokens|max_turn_requests|refusal|cancelled (+
    error surfaced as a JSON-RPC error).

Engines (verified on this box):
  gemini : `gemini --acp`                              (native ACP agent)
  claude : `npx -y @zed-industries/claude-code-acp`    (Claude Code as ACP server)
Override either with --engine-cmd "prog arg arg".

Stdlib only; no ACP SDK dependency.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Composite SELF organ — import robustly whether run as a script or imported.
try:
    import aios_agent_self  # type: ignore
except ImportError:  # pragma: no cover - path shim for standalone execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import aios_agent_self  # type: ignore

PROTOCOL_VERSION = 1  # ACP integer protocol version (grounded 2026-07-04).
CLIENT_NAME = "aios-drive"
CLIENT_VERSION = "0.1.0"

ENGINES: dict[str, list[str]] = {
    "gemini": ["gemini", "--acp"],
    "claude": ["npx", "-y", "@zed-industries/claude-code-acp"],
}

# Privacy DNA (same list as docs/AIOS_HOOKS.md privacy-boundary, invariant #7).
_GATED_SEGMENTS = ("_from_desktop", "dain", "minyoung")
_GATED_SUBSTRINGS = (".env", "secret", "credentials", "auth.json", "raw_export")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _aios_home() -> Path:
    raw = os.environ.get("AIOS_HOME", "")
    return Path(raw).expanduser().resolve() if raw else (Path.home() / ".aios")


def _self_store_exists(agent_id: str | None) -> bool:
    """A composite SELF is available to inject only if its store dir exists."""
    aid = aios_agent_self.resolve_agent_id(agent_id)
    return aios_agent_self.agent_dir(aid).is_dir()


# ── adjudication: the OS moment ────────────────────────────────────────────

def _adjudicate(tool_call: dict[str, Any]) -> tuple[bool, str]:
    """Decide ALLOW/DENY for a tool call against the privacy DNA.

    Fail-closed: DENY anything whose title / locations / rawInput touches a
    privacy-gated path segment or substring, or is a destructive command
    (rm -rf outside cwd, git push --force). ALLOW everything else.

    Returns (allow: bool, reason: str).
    """
    title = str(tool_call.get("title") or "")
    raw = tool_call.get("rawInput")
    raw_text = json.dumps(raw, ensure_ascii=False) if raw is not None else ""
    locations = tool_call.get("locations") or []
    loc_paths = [str(l.get("path", "")) for l in locations if isinstance(l, dict)]

    haystack = " ".join([title, raw_text, *loc_paths])
    low = haystack.lower()

    # Privacy-gated path segments (check split segments of every candidate path).
    candidate_paths = list(loc_paths)
    if isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, str):
                candidate_paths.append(v)
    candidate_paths.append(title)
    for p in candidate_paths:
        segs = [s for s in str(p).replace("\\", "/").split("/") if s]
        for seg in segs:
            if seg in _GATED_SEGMENTS:
                return False, f"privacy-gated path segment '{seg}'"

    # Privacy-gated substrings anywhere in the request.
    for sub in _GATED_SUBSTRINGS:
        if sub in low:
            return False, f"privacy-gated substring '{sub}'"

    # Destructive command patterns.
    norm = " ".join(low.split())
    if "rm -rf" in norm or "rm -fr" in norm:
        return False, "destructive command (rm -rf)"
    if "git push" in norm and ("--force" in norm or "-f " in norm or norm.endswith(" -f")):
        return False, "destructive command (git push --force)"

    return True, "no privacy-gated pattern matched"


class ACPTimeout(Exception):
    pass


class ACPError(Exception):
    pass


class _Driver:
    """Synchronous ACP client over a child engine's newline-delimited stdio."""

    def __init__(self, proc: subprocess.Popen,
                 on_event: Callable[[dict], None]):
        self.proc = proc
        self.on_event = on_event
        self.timed_out = False  # set by the watchdog before it kills the child
        self._id = 0
        self._tool_calls: dict[str, dict] = {}  # toolCallId -> merged details
        self.permissions: list[dict] = []

    # -- low-level framing --------------------------------------------------
    # NOTE: framing is newline-delimited JSON-RPC. We deliberately do NOT mix
    # select() with the buffered text readline() — readline may pull more than
    # one line off the fd into Python's buffer, which select (watching the raw
    # fd) never re-signals, deadlocking. Instead a watchdog timer in drive()
    # kills the child on timeout; the blocking readline then returns "" (EOF)
    # and the pump raises ACPTimeout.
    def _write(self, obj: dict) -> None:
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        assert self.proc.stdin is not None
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

    def _read_line(self) -> str | None:
        """Read one non-empty line (blocking). None = EOF (incl. watchdog kill)."""
        assert self.proc.stdout is not None
        while True:
            line = self.proc.stdout.readline()
            if line == "":
                return None  # EOF
            s = line.strip()
            if s:
                return s

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    # -- request/response with interleaved server->client traffic ----------
    def request(self, method: str, params: dict) -> dict:
        rid = self._next_id()
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        return self._pump_until(rid)

    def _pump_until(self, target_id: int) -> dict:
        while True:
            s = self._read_line()
            if s is None:
                if self.timed_out:
                    raise ACPTimeout("engine exceeded timeout")
                raise ACPError(f"engine closed the stream before responding to id={target_id}")
            try:
                msg = json.loads(s)
            except json.JSONDecodeError:
                continue  # ignore non-JSON banner lines some engines print
            if "method" in msg:
                self._handle_incoming(msg)
                continue
            if msg.get("id") == target_id and ("result" in msg or "error" in msg):
                if "error" in msg:
                    raise ACPError(f"engine error on request id={target_id}: {msg['error']}")
                return msg["result"]
            # stray response to an unknown id — ignore.

    # -- incoming server->client notifications & requests -------------------
    def _handle_incoming(self, msg: dict) -> None:
        method = msg.get("method")
        params = msg.get("params") or {}
        if method == "session/update":
            self._handle_update(params)
            return
        if method == "session/request_permission":
            self._handle_permission(msg)
            return
        # Any other server->client REQUEST (has id): we advertised no fs/terminal
        # caps, so respond method-not-found instead of hanging the engine.
        if "id" in msg:
            self._write({"jsonrpc": "2.0", "id": msg["id"],
                         "error": {"code": -32601, "message": f"method not supported: {method}"}})

    def _handle_update(self, params: dict) -> None:
        update = params.get("update") or {}
        variant = update.get("sessionUpdate")
        line = None
        if variant == "agent_message_chunk":
            content = update.get("content") or {}
            text = content.get("text", "") if isinstance(content, dict) else ""
            if text:
                line = text
                sys.stdout.write(text)
                sys.stdout.flush()
        elif variant in ("tool_call", "tool_call_update"):
            tcid = update.get("toolCallId")
            if tcid:
                cached = self._tool_calls.setdefault(tcid, {})
                for k in ("title", "kind", "status", "locations", "rawInput"):
                    if update.get(k) is not None:
                        cached[k] = update[k]
            title = update.get("title") or self._tool_calls.get(tcid, {}).get("title", "")
            kind = update.get("kind") or self._tool_calls.get(tcid, {}).get("kind", "")
            status = update.get("status") or ""
            line = f"[tool_call] {kind or '?'}: {title} ({status})".rstrip(" ()")
            print("\n" + line, flush=True)
        elif variant == "plan":
            entries = update.get("entries") or []
            line = f"[plan] {len(entries)} step(s)"
            print(line, flush=True)
        self.on_event({"ts": now_iso(), "type": "session/update",
                       "variant": variant, "update": update})

    def _handle_permission(self, msg: dict) -> None:
        params = msg.get("params") or {}
        req_tc = params.get("toolCall") or {}
        tcid = req_tc.get("toolCallId")
        # Merge cached session/update details with the permission request's toolCall.
        merged = dict(self._tool_calls.get(tcid, {}))
        merged.update({k: v for k, v in req_tc.items() if v is not None})

        allow, reason = _adjudicate(merged)
        options = params.get("options") or []
        want = ("allow_once", "allow_always") if allow else ("reject_once", "reject_always")
        chosen = None
        for kind in want:
            for opt in options:
                if opt.get("kind") == kind:
                    chosen = opt.get("optionId")
                    break
            if chosen:
                break

        if chosen is not None:
            outcome = {"outcome": "selected", "optionId": chosen}
        else:
            # No matching option offered — fail-closed cancel (denies the call).
            outcome = {"outcome": "cancelled"}
        self._write({"jsonrpc": "2.0", "id": msg["id"], "result": {"outcome": outcome}})

        decision = "allow" if allow else "deny"
        rec = {
            "ts": now_iso(),
            "tool_call_id": tcid,
            "title": merged.get("title", ""),
            "decision": decision,
            "reason": reason,
            "chosen_option": chosen,
            "outcome": outcome["outcome"],
        }
        self.permissions.append(rec)
        self.on_event({"ts": rec["ts"], "type": "permission", **rec})
        print(f"\n[permission] {decision.upper()}: {merged.get('title','')} — {reason}",
              flush=True)


def _drain(stream, sink: list[str]) -> None:
    try:
        for line in iter(stream.readline, ""):
            sink.append(line)
    except Exception:  # pragma: no cover - stream torn down on kill
        pass


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:  # pragma: no cover
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass


def drive(goal: str, engine: str = "claude", cwd: str | None = None,
          inject_self: bool = True, timeout: int = 600,
          engine_cmd: list[str] | None = None,
          agent_id: str | None = None) -> dict:
    """Run a provider agent as an AIOS engine over ACP. Returns the receipt dict."""
    cmd = list(engine_cmd) if engine_cmd else ENGINES.get(engine)
    if not cmd:
        raise ValueError(f"unknown engine {engine!r} (known: {', '.join(ENGINES)}) — "
                         "or pass --engine-cmd")
    work_dir = os.path.abspath(cwd or os.getcwd())

    events: list[dict] = []
    stderr_lines: list[str] = []
    started = time.monotonic()
    start_iso = now_iso()

    proc = subprocess.Popen(
        cmd, cwd=work_dir, text=True, bufsize=1,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    err_thread = threading.Thread(target=_drain, args=(proc.stderr, stderr_lines), daemon=True)
    err_thread.start()

    driver = _Driver(proc, events.append)

    def _on_timeout() -> None:
        driver.timed_out = True
        try:
            proc.kill()
        except Exception:  # pragma: no cover
            pass

    watchdog = threading.Timer(timeout, _on_timeout)
    watchdog.daemon = True
    watchdog.start()

    self_injected = False
    stop_reason = "error"
    error: str | None = None
    session_id = None

    try:
        driver.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "clientCapabilities": {
                "fs": {"readTextFile": False, "writeTextFile": False},
                "terminal": False,
            },
            "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
        })
        new_res = driver.request("session/new", {"cwd": work_dir, "mcpServers": []})
        session_id = new_res.get("sessionId")

        blocks: list[dict] = []
        if inject_self and _self_store_exists(agent_id):
            self_text = aios_agent_self.carry("system", agent_id=agent_id)
            if isinstance(self_text, str) and self_text.strip():
                blocks.append({"type": "text", "text": self_text})
                self_injected = True
        blocks.append({"type": "text", "text": goal})

        prompt_res = driver.request("session/prompt", {
            "sessionId": session_id, "prompt": blocks,
        })
        stop_reason = prompt_res.get("stopReason", "end_turn")
    except ACPTimeout:
        stop_reason = "timeout"
        error = f"engine exceeded {timeout}s timeout"
    except ACPError as exc:
        stop_reason = "error"
        error = str(exc)
    finally:
        watchdog.cancel()
        _terminate(proc)

    duration_s = round(time.monotonic() - started, 3)

    receipt = {
        "schema": "aios.drive.receipt.v1",
        "started": start_iso,
        "ended": now_iso(),
        "engine": engine,
        "engine_cmd": cmd,
        "cwd": work_dir,
        "goal": goal,
        "session_id": session_id,
        "self_injected": self_injected,
        "events": len(events),
        "permissions": driver.permissions,
        "stop_reason": stop_reason,
        "duration_s": duration_s,
        "error": error,
    }
    if stderr_lines and (error or stop_reason in ("error", "timeout")):
        receipt["engine_stderr_tail"] = "".join(stderr_lines[-20:]).strip()

    drive_dir = _aios_home() / "drive"
    drive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    receipt_path = drive_dir / f"receipt-{ts}.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt["receipt_path"] = str(receipt_path)

    n_allow = sum(1 for p in driver.permissions if p["decision"] == "allow")
    n_deny = sum(1 for p in driver.permissions if p["decision"] == "deny")
    print(f"\n─ aios drive: engine={engine} stop={stop_reason} "
          f"self_injected={self_injected} events={len(events)} "
          f"perms(allow={n_allow},deny={n_deny}) {duration_s}s")
    print(f"  receipt: {receipt_path}")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aios drive",
        description="Drive a provider agent (Claude Code / Gemini CLI) as an AIOS "
                    "engine over the Agent Client Protocol. AIOS is the OS (ACP "
                    "client); the provider agent is the engine (ACP server).",
    )
    p.add_argument("goal", help="the goal AIOS gives the engine")
    p.add_argument("--engine", default="claude", choices=sorted(ENGINES),
                   help="which provider engine to drive (default: claude)")
    p.add_argument("--engine-cmd", default=None,
                   help="override the engine command, e.g. \"gemini --acp\"")
    p.add_argument("--cwd", default=None, help="working directory for the engine session")
    p.add_argument("--no-self", action="store_true",
                   help="do NOT inject the composite SELF at session start")
    p.add_argument("--timeout", type=int, default=600, help="overall timeout in seconds")
    p.add_argument("--agent-id", default=None, help="composite SELF agent id")
    p.add_argument("--json", action="store_true", help="print the receipt as JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine_cmd = args.engine_cmd.split() if args.engine_cmd else None
    try:
        receipt = drive(
            goal=args.goal, engine=args.engine, cwd=args.cwd,
            inject_self=not args.no_self, timeout=args.timeout,
            engine_cmd=engine_cmd, agent_id=args.agent_id,
        )
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"aios drive: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt.get("stop_reason") not in ("error",) else 1


if __name__ == "__main__":
    raise SystemExit(main())
