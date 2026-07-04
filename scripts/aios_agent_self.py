#!/usr/bin/env python3
"""aios_agent_self — the COMPOSITE AGENT SELF organ (per-agent identity + learning).

The artifact an agent loads at birth and updates at death: a portable, white-box,
persistent SELF that gives any frozen model continuity across sessions AND across
substrates (Claude Code / Codex / local LLM / any MCP client).

Thesis (condensed): a frozen model *alone* cannot escape prompt-dependency — every
session it is born amnesiac and answers only from the prompt in front of it. The
COMPOSITE (model + memory + verifier + records) can. What an agent needs is not more
capability but three things this organ supplies:
  - continuity  — a memory that SURVIVES the session (learned.jsonl + checkpoints)
  - a spine     — identity + limits that make the agent trustworthy (identity.md)
  - portability — the SELF survives substrate swaps: the model is replaceable, the
                  *someone* persists (carry --to claude|codex|system|json)

This implements design-revalidation recommendation #2 (content-rich local behavioral
memory: decisions / corrections / outcomes — NOT tool-name signatures) at the
IDENTITY layer. White-box (human-readable files), draft-first (DNA #2: learnings are
drafts until an explicit documented review accepts them), append-only (DNA #3:
accept/reject are supersede records, never destructive rewrites). Local-only: the
self never egresses by itself (DNA #7).

Boundary (do NOT duplicate):
  - aios_self_model.py    — SYSTEM-level self-model (what AIOS is, composed scorers).
  - aios_self.py          — the discomfort organ (agent statement + verdict record).
  - aios_agent_behavior.py — behavioral ledger (tool-signature prediction).
This organ is the per-AGENT identity + learning artifact WITH a birth/death lifecycle.

Store ($AIOS_HOME or ~/.aios), per agent (env AIOS_AGENT_ID / --agent / "default"):
  <home>/self/<agent_id>/
    identity.md        — human-editable: who / role / values / limits (seeded on birth)
    learned.jsonl      — append-only {id, ts, kind, text, refs, status, reviewer, review_note}
    checkpoints.jsonl  — append-only session-death records {ts, session, in_flight, next, note}
    SELF.md            — the COMPILED artifact (identity + accepted learnings + last checkpoint)

Ops:  birth  learn  accept  reject  checkpoint  carry  install-hooks  uninstall-hooks  status
Schema: aios.agent_self.v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "aios.agent_self.v1"

# Marker embedded (as a shell comment) in every SessionStart hook command we write,
# so install is idempotent and uninstall can remove EXACTLY our entries and nothing
# else. Base = all agents; per-agent form appends "(agent=<id>)".
HOOK_MARKER = "aios-self:install-hooks"

# The self-maintenance instruction baked into carry renders — the injected self
# teaches its carrier how to keep the self alive (learn / checkpoint / review).
SELF_MAINTENANCE = (
    "SELF-MAINTENANCE: You carry this self. When you learn a durable "
    "correction/what-worked, propose it: `aios self learn --kind ... --text \"...\"`. "
    "Before the session ends, record where you left off: "
    "`aios self checkpoint --in-flight \"...\" --next \"...\"`. Acceptance requires "
    "explicit human review (`aios self accept <id> --reviewer ... --note ...`)."
)

# The 7 AIOS DNA invariants, one line — baked into every compiled SELF.md footer.
DNA_ONELINE = (
    "AIOS DNA: 1 recommendation-only  2 draft-first  3 append-only audit  "
    "4 named stop conditions  5 provenance chain  6 operator override  7 privacy boundary."
)

# Injection policy baked into the artifact — grounded in the measured A/B result.
INJECTION_POLICY = (
    "INJECTION POLICY: Load this at session start / first attempt only. Do NOT re-inject "
    "during error-feedback retries — measured: always-on injection collapses retry recovery "
    "68%->19% (docs/AIOS_HEADLINE_AB_RESULTS.md)."
)

_VALID_KINDS = ("correction", "what_worked", "decision", "limit")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _aios_home() -> Path:
    raw = os.environ.get("AIOS_HOME", "")
    return Path(raw).expanduser().resolve() if raw else (Path.home() / ".aios")


def resolve_agent_id(explicit: str | None) -> str:
    return explicit or os.environ.get("AIOS_AGENT_ID") or "default"


def agent_dir(agent_id: str) -> Path:
    return _aios_home() / "self" / agent_id


def _paths(agent_id: str):
    d = agent_dir(agent_id)
    return d, d / "identity.md", d / "learned.jsonl", d / "checkpoints.jsonl", d / "SELF.md"


def _append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _stable_id(kind: str, text: str) -> str:
    h = hashlib.sha256(f"{kind}\x00{text}".encode("utf-8")).hexdigest()
    return h[:12]


_IDENTITY_TEMPLATE = """# Identity — {agent_id}

<!-- Human-editable. This is the SPINE: who I am, so I can be trusted across sessions
     and substrates. Edit freely; `aios self birth` compiles it verbatim into SELF.md. -->

## Who
{agent_id} — (describe the agent: its name, the model/substrate it runs on today).

## Role
(What this agent is for — its job and scope.)

## Values
- Ground claims in evidence, not memory.
- Draft-first: propose, let review accept.

## Limits
- (Known blind spots, things to escalate, boundaries not to cross.)
"""


def _seed_identity(identity_path: Path, agent_id: str) -> None:
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_text(_IDENTITY_TEMPLATE.format(agent_id=agent_id), encoding="utf-8")


def _accepted_learnings(learned_path: Path) -> list[dict]:
    """Last-wins resolution over the append-only log: an accept/reject appended later
    supersedes the earlier draft for the same id. Returns accepted entries, newest first."""
    latest: dict[str, dict] = {}
    order: dict[str, int] = {}
    for i, e in enumerate(_read_jsonl(learned_path)):
        eid = e.get("id")
        if not eid:
            continue
        latest[eid] = e
        if eid not in order:
            order[eid] = i
    accepted = [e for e in latest.values() if e.get("status") == "accepted"]
    # newest first by original insertion order (first time the id appeared)
    accepted.sort(key=lambda e: order.get(e.get("id"), 0), reverse=True)
    return accepted


# ── Ops ──────────────────────────────────────────────────────────────────────

def birth(agent_id: str | None = None, max_words: int = 1200) -> dict:
    """Compile SELF.md from identity + accepted learnings + last checkpoint. Returns dict."""
    aid = resolve_agent_id(agent_id)
    d, identity_p, learned_p, checkpoints_p, self_p = _paths(aid)
    d.mkdir(parents=True, exist_ok=True)
    if not identity_p.exists():
        _seed_identity(identity_p, aid)

    identity_text = identity_p.read_text(encoding="utf-8").rstrip()

    accepted = _accepted_learnings(learned_p)
    checkpoints = _read_jsonl(checkpoints_p)
    last_ckpt = checkpoints[-1] if checkpoints else None

    parts: list[str] = []
    parts.append(identity_text)
    parts.append("")
    parts.append("## What I have learned")
    shown = 0
    if accepted:
        # Bound by max_words: keep the identity block whole, budget the learnings list.
        used = len(identity_text.split())
        lines: list[str] = []
        for e in accepted:
            line = f"- [{e.get('kind')}] {e.get('text')}"
            w = len(line.split())
            if shown and used + w > max_words:
                break
            lines.append(line)
            used += w
            shown += 1
        parts.extend(lines)
        hidden = len(accepted) - shown
        if hidden > 0:
            parts.append(f"- ({hidden} older learnings not shown — see learned.jsonl)")
    else:
        parts.append("- (nothing accepted yet — use `aios self learn` then `aios self accept`)")

    parts.append("")
    parts.append("## Where I left off")
    if last_ckpt:
        parts.append(f"- in_flight: {last_ckpt.get('in_flight', '')}")
        parts.append(f"- next: {last_ckpt.get('next', '')}")
        if last_ckpt.get("note"):
            parts.append(f"- note: {last_ckpt.get('note')}")
        parts.append(f"- (checkpoint @ {last_ckpt.get('ts', '')})")
    else:
        parts.append("- (no checkpoint yet)")

    parts.append("")
    parts.append("---")
    parts.append(INJECTION_POLICY)
    parts.append("")
    parts.append(DNA_ONELINE)
    parts.append("")

    compiled = "\n".join(parts).rstrip() + "\n"
    self_p.write_text(compiled, encoding="utf-8")
    word_count = len(compiled.split())
    return {
        "schema": SCHEMA,
        "agent_id": aid,
        "path": str(self_p),
        "word_count": word_count,
        "accepted_shown": shown,
        "accepted_total": len(accepted),
        "max_words": max_words,
    }


def learn(kind: str, text: str, refs: list[str] | None = None, agent_id: str | None = None) -> dict:
    """Append a DRAFT learning (draft-first, DNA #2). text must be one non-empty line."""
    aid = resolve_agent_id(agent_id)
    if kind not in _VALID_KINDS:
        raise ValueError(f"kind must be one of {_VALID_KINDS}, got {kind!r}")
    text = (text or "").strip()
    if not text:
        raise ValueError("text must be a non-empty single line")
    if "\n" in text or "\r" in text:
        raise ValueError("text must be a single line (no newlines) — one content-rich sentence")
    _, _, learned_p, _, _ = _paths(aid)
    entry = {
        "id": _stable_id(kind, text),
        "ts": now_iso(),
        "kind": kind,
        "text": text,
        "refs": refs or [],
        "status": "draft",
        "reviewer": None,
        "review_note": None,
    }
    _append(learned_p, entry)
    return entry


def _review(entry_id: str, status: str, reviewer: str, note: str, agent_id: str | None) -> dict:
    aid = resolve_agent_id(agent_id)
    reviewer = (reviewer or "").strip()
    note = (note or "").strip()
    if not reviewer:
        raise ValueError("review requires --reviewer (explicit documented review, DNA #2)")
    if not note:
        raise ValueError("review requires --note (explicit documented review, DNA #2)")
    _, _, learned_p, _, _ = _paths(aid)
    entries = _read_jsonl(learned_p)
    match = None
    for e in entries:
        if e.get("id") == entry_id:
            match = e
    if match is None:
        raise ValueError(f"no learning with id {entry_id!r}")
    # Append a supersede record — never rewrite the prior line (append-only, DNA #3).
    record = dict(match)
    record["ts"] = now_iso()
    record["status"] = status
    record["reviewer"] = reviewer
    record["review_note"] = note
    _append(learned_p, record)
    return record


def accept(entry_id: str, reviewer: str, note: str, agent_id: str | None = None) -> dict:
    return _review(entry_id, "accepted", reviewer, note, agent_id)


def reject(entry_id: str, reviewer: str, note: str, agent_id: str | None = None) -> dict:
    return _review(entry_id, "rejected", reviewer, note, agent_id)


def checkpoint(in_flight: str, next_: str, note: str | None = None,
               session: str | None = None, agent_id: str | None = None) -> dict:
    """The death half of the loop — record where the agent left off."""
    aid = resolve_agent_id(agent_id)
    _, _, _, checkpoints_p, _ = _paths(aid)
    entry = {
        "ts": now_iso(),
        "session": session,
        "in_flight": (in_flight or "").strip(),
        "next": (next_ or "").strip(),
        "note": (note or "").strip() or None,
    }
    _append(checkpoints_p, entry)
    return entry


def carry(target: str, agent_id: str | None = None, max_words: int = 1200,
          hook: bool = False) -> str | dict:
    """Render the freshly-compiled SELF for a target substrate.

    hook=True (SessionStart auto-birth): wrap the render in the Claude Code
    hook JSON envelope so the compiled SELF is injected as session context.
    """
    aid = resolve_agent_id(agent_id)
    info = birth(aid, max_words=max_words)  # always fresh
    _, _, _, _, self_p = _paths(aid)
    body = self_p.read_text(encoding="utf-8").rstrip()

    render: str | dict
    if target == "json":
        render = {**info, "self_md": body}
    elif target == "claude":
        render = (
            "```markdown\n"
            "<!-- AIOS composite SELF — add to CLAUDE.md or a SessionStart-hook "
            "additionalContext. Load at session start / first attempt only. -->\n"
            f"{body}\n\n"
            f"{SELF_MAINTENANCE}\n"
            "```\n"
        )
    elif target == "codex":
        render = (
            "```markdown\n"
            "<!-- AIOS composite SELF — add to AGENTS.md. Load at session start only. -->\n"
            f"{body}\n\n"
            f"{SELF_MAINTENANCE}\n"
            "```\n"
        )
    elif target == "system":
        # Plain system-prompt text — strip markdown headers/fences entirely.
        out_lines = []
        for line in body.splitlines():
            stripped = line.lstrip("#").strip() if line.lstrip().startswith("#") else line
            if stripped.strip() == "---":
                continue
            out_lines.append(stripped)
        render = "\n".join(out_lines).strip() + "\n"
    else:
        raise ValueError(f"unknown carry target {target!r} (use claude|codex|system|json)")

    if hook:
        if not isinstance(render, str):
            raise ValueError("--hook requires a text target (claude|codex|system), not json")
        # Claude Code SessionStart hook envelope (same shape the working repo hooks emit).
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": render,
            }
        }
    return render


def status(agent_id: str | None = None) -> dict:
    aid = resolve_agent_id(agent_id)
    d, identity_p, learned_p, checkpoints_p, self_p = _paths(aid)
    entries = _read_jsonl(learned_p)
    # last-wins status per id
    latest: dict[str, dict] = {}
    for e in entries:
        if e.get("id"):
            latest[e["id"]] = e
    drafts = sum(1 for e in latest.values() if e.get("status") == "draft")
    accepted = sum(1 for e in latest.values() if e.get("status") == "accepted")
    rejected = sum(1 for e in latest.values() if e.get("status") == "rejected")
    checkpoints = _read_jsonl(checkpoints_p)
    last_ckpt = checkpoints[-1]["ts"] if checkpoints else None
    last_birth = None
    if self_p.exists():
        last_birth = datetime.fromtimestamp(self_p.stat().st_mtime, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA,
        "agent_id": aid,
        "store": str(d),
        "drafts": drafts,
        "accepted": accepted,
        "rejected": rejected,
        "checkpoints": len(checkpoints),
        "last_birth": last_birth,
        "last_checkpoint": last_ckpt,
        "identity_seeded": identity_p.exists(),
    }


# ── hook install / uninstall ─────────────────────────────────────────────────

def _settings_path_for_scope(scope: str) -> Path:
    if scope == "user":
        return Path.home() / ".claude" / "settings.json"
    if scope == "project":
        return Path.cwd() / ".claude" / "settings.json"
    raise ValueError(f"scope must be 'user' or 'project', got {scope!r}")


def _self_hook_command(agent_id: str, explicit_agent: bool) -> tuple[str, str]:
    """Build the SessionStart hook command + its per-agent idempotency marker.

    Uses `aios` when on PATH (the robust invocation), else falls back to the
    current interpreter + this script's absolute path so a missing launcher on
    PATH does not break the hook."""
    agent_flag = f"--agent {shlex.quote(agent_id)} " if explicit_agent else ""
    if shutil.which("aios"):
        base = f"aios self {agent_flag}carry --to claude --hook"
    else:
        script = str(Path(__file__).resolve())
        base = (f'"{sys.executable}" "{script}" self {agent_flag}'
                "carry --to claude --hook")
    marker = f"{HOOK_MARKER}(agent={agent_id})"
    # `|| true` keeps the session non-blocking (matches the repo's other hooks);
    # the trailing `# <marker>` is what makes install idempotent and uninstall exact.
    command = f"{base} 2>/dev/null || true  # {marker}"
    return command, marker


def _load_settings(path: Path) -> dict:
    """Read-modify-write helper: never clobber a corrupt-but-precious file."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"refusing to touch {path}: not valid JSON ({e}); fix or remove it first")
    if not isinstance(data, dict):
        raise ValueError(f"refusing to touch {path}: top-level JSON is not an object")
    return data


def install_hooks(scope: str = "user", agent_id: str | None = None,
                  settings_path: str | Path | None = None) -> dict:
    """Wire a SessionStart hook that auto-births the SELF into a Claude Code
    settings.json. Idempotent and reversible; preserves all unrelated content."""
    aid = resolve_agent_id(agent_id)
    path = Path(settings_path) if settings_path else _settings_path_for_scope(scope)
    data = _load_settings(path)
    command, marker = _self_hook_command(aid, explicit_agent=agent_id is not None)

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"refusing to touch {path}: 'hooks' is not an object")
    session_start = hooks.setdefault("SessionStart", [])
    if not isinstance(session_start, list):
        raise ValueError(f"refusing to touch {path}: 'hooks.SessionStart' is not a list")

    for group in session_start:
        for h in (group.get("hooks", []) if isinstance(group, dict) else []):
            if isinstance(h, dict) and marker in (h.get("command") or ""):
                return {
                    "schema": SCHEMA, "status": "already-installed", "agent_id": aid,
                    "scope": scope, "settings": str(path), "command": command,
                    "revert": f"aios self uninstall-hooks --scope {scope}",
                }

    # Append our OWN hook group — never mutate any pre-existing group.
    session_start.append({"hooks": [{"type": "command", "command": command}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "schema": SCHEMA, "status": "installed", "agent_id": aid, "scope": scope,
        "settings": str(path), "command": command,
        "wrote": f"SessionStart hook -> {path} (auto-births the SELF every session)",
        "revert": f"aios self uninstall-hooks --scope {scope}",
    }


def uninstall_hooks(scope: str = "user", agent_id: str | None = None,
                    settings_path: str | Path | None = None) -> dict:
    """Remove EXACTLY the SessionStart hook entries we installed (marker-matched),
    leaving every other hook and setting untouched."""
    path = Path(settings_path) if settings_path else _settings_path_for_scope(scope)
    if not path.exists():
        return {"schema": SCHEMA, "status": "no-settings", "scope": scope,
                "settings": str(path), "removed": 0}
    data = _load_settings(path)
    removed = 0
    hooks = data.get("hooks")
    if isinstance(hooks, dict) and isinstance(hooks.get("SessionStart"), list):
        session_start = hooks["SessionStart"]
        new_groups = []
        for group in session_start:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            kept = []
            for h in group.get("hooks", []):
                if isinstance(h, dict) and HOOK_MARKER in (h.get("command") or ""):
                    removed += 1
                    continue
                kept.append(h)
            if kept:
                new_group = dict(group)
                new_group["hooks"] = kept
                new_groups.append(new_group)
            elif "hooks" not in group:
                new_groups.append(group)
            # else: group had only our hook(s) -> drop the now-empty group
        hooks["SessionStart"] = new_groups
    if removed:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"schema": SCHEMA, "status": "uninstalled" if removed else "nothing-to-remove",
            "scope": scope, "settings": str(path), "removed": removed}


# ── CLI ──────────────────────────────────────────────────────────────────────

def _emit(obj) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, ensure_ascii=True, indent=2))
    else:
        print(obj)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aios self", description=__doc__.split("\n")[0])
    p.add_argument("--root", help=argparse.SUPPRESS)  # tolerated (launcher may pass it)
    p.add_argument("--agent", help="agent id (default: $AIOS_AGENT_ID or 'default')")
    sub = p.add_subparsers(dest="op", required=True)

    b = sub.add_parser("birth", help="compile SELF.md (load at session start)")
    b.add_argument("--max-words", type=int, default=1200)

    l = sub.add_parser("learn", help="append a draft learning")
    l.add_argument("--kind", required=True, choices=_VALID_KINDS)
    l.add_argument("--text", required=True)
    l.add_argument("--refs", default="", help="comma-separated paths/urls")

    a = sub.add_parser("accept", help="accept a draft (requires --reviewer and --note)")
    a.add_argument("id")
    a.add_argument("--reviewer", required=True)
    a.add_argument("--note", required=True)

    r = sub.add_parser("reject", help="reject a draft (requires --reviewer and --note)")
    r.add_argument("id")
    r.add_argument("--reviewer", required=True)
    r.add_argument("--note", required=True)

    c = sub.add_parser("checkpoint", help="record session-death: where I left off")
    c.add_argument("--in-flight", required=True)
    c.add_argument("--next", required=True)
    c.add_argument("--note", default="")
    c.add_argument("--session", default="")

    cr = sub.add_parser("carry", help="render SELF for a target substrate")
    cr.add_argument("--to", required=True, choices=["claude", "codex", "system", "json"])
    cr.add_argument("--max-words", type=int, default=1200)
    cr.add_argument("--hook", action="store_true",
                    help="wrap the render in a Claude Code SessionStart hook envelope")

    ih = sub.add_parser("install-hooks",
                        help="wire a SessionStart hook that auto-births the SELF")
    ih.add_argument("--scope", choices=["user", "project"], default="user")

    uh = sub.add_parser("uninstall-hooks", help="remove exactly our SessionStart hook")
    uh.add_argument("--scope", choices=["user", "project"], default="user")

    sub.add_parser("status", help="counts + last birth/checkpoint + store path")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    aid = args.agent
    try:
        if args.op == "birth":
            _emit(birth(aid, max_words=args.max_words))
        elif args.op == "learn":
            refs = [x.strip() for x in (args.refs or "").split(",") if x.strip()]
            _emit(learn(args.kind, args.text, refs=refs, agent_id=aid))
        elif args.op == "accept":
            _emit(accept(args.id, args.reviewer, args.note, agent_id=aid))
        elif args.op == "reject":
            _emit(reject(args.id, args.reviewer, args.note, agent_id=aid))
        elif args.op == "checkpoint":
            _emit(checkpoint(args.in_flight, args.next, note=args.note or None,
                             session=args.session or None, agent_id=aid))
        elif args.op == "carry":
            _emit(carry(args.to, agent_id=aid, max_words=args.max_words, hook=args.hook))
        elif args.op == "install-hooks":
            _emit(install_hooks(scope=args.scope, agent_id=aid))
        elif args.op == "uninstall-hooks":
            _emit(uninstall_hooks(scope=args.scope, agent_id=aid))
        elif args.op == "status":
            _emit(status(aid))
        else:  # pragma: no cover
            return 2
    except ValueError as e:
        print(f"aios self: error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
