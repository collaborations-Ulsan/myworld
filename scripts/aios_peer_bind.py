#!/usr/bin/env python3
"""Bind durable agent identities to whichever session currently embodies them.

Observed live on 2026-08-13 with 34 peer sessions up. Yesterday's advisors were
`quantum-3e`, `goen-95`, `universe-52`. Today the fleet holds `quantum-fd`,
`quantum-d4`, `goen-4d`, `goen-40`, `universe-ef`, `universe-be`, and not one of
yesterday's names resolves. The peer that cut a hypothesis of mine in half with
Vorob'ev's theorem cannot be addressed today, and a ledger row that recorded
`peer://quantum-3e` points at nothing.

Claude Code says so itself in each session's registration file:

    "name": "quantum-fd", "nameSource": "derived"

A derived name is a `session_id`. What is stable is the WORKSPACE, so this
module resolves an `agent_id` (durable, in `aios_agent_registry`) to the live
session whose cwd sits under that agent's workspace, and hands back the name to
address it with. `scripts/aios_contracts.py` states that separation; this makes
it usable.

Liveness is DERIVED, never taken from the record — the same discipline the arc
lease uses. A registration file says `status: idle`, but a file is a claim: the
pid must be alive AND the messaging socket must still exist, or the session is
reported gone regardless of what it wrote about itself.

    python3 scripts/aios_peer_bind.py discover
    python3 scripts/aios_peer_bind.py resolve --agent claude@quantum
    python3 scripts/aios_peer_bind.py resolve --workspace quantum --json

Reads only. Stdlib only. Schema: aios.peer_bind.v0
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

SCHEMA = "aios.peer_bind.v0"
SESSIONS = Path(os.environ.get("CLAUDE_SESSIONS_DIR",
                               Path.home() / ".claude" / "sessions"))
WORKSPACE_ROOT = Path(os.environ.get("AIOS_WORKSPACE_ROOT",
                                     Path.home() / "workspaces" / "jaewon"))


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True                     # exists, owned by someone else
    except (TypeError, ValueError, OSError):
        return False
    return True


def read_sessions() -> tuple[list[dict], list[str]]:
    """Every registration record, with liveness derived rather than believed."""
    out, problems = [], []
    if not SESSIONS.is_dir():
        return out, [f"no session directory at {SESSIONS}"]
    for p in sorted(SESSIONS.glob("*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{p.name}: {type(exc).__name__}")
            continue
        try:
            pid = int(rec.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        sock = rec.get("messagingSocketPath") or ""
        alive = bool(pid) and _pid_alive(pid)
        reachable = alive and bool(sock) and Path(sock).exists()
        out.append({
            "name": rec.get("name"),
            "name_source": rec.get("nameSource"),
            "session_id": rec.get("sessionId"),
            "cwd": rec.get("cwd"),
            "pid": pid,
            "kind": rec.get("kind"),
            "tmux": rec.get("tmux"),
            "socket": sock,
            "claimed_status": rec.get("status"),
            # The two that matter, and neither is read from the file's own
            # status field: a record can say "idle" long after its process died.
            "process_alive": alive,
            "reachable": reachable,
            "age_s": _age(rec),
        })
    return out, problems


def _age(rec: dict) -> float | None:
    try:
        return round(time.time() - int(rec.get("updatedAt", 0)) / 1000.0, 1)
    except (TypeError, ValueError):
        return None


def _repo_of(cwd: str | None) -> str | None:
    """The workspace a session is working in — the part that is NOT ephemeral."""
    if not cwd:
        return None
    try:
        rel = Path(cwd).resolve().relative_to(WORKSPACE_ROOT)
    except (ValueError, OSError):
        return None
    return rel.parts[0] if rel.parts else None


def discover() -> dict:
    sessions, problems = read_sessions()
    by_repo: dict[str, list[dict]] = {}
    for s in sessions:
        repo = _repo_of(s["cwd"])
        s["repo"] = repo
        if s["reachable"]:
            by_repo.setdefault(repo or "(outside workspace)", []).append(s)
    derived = sum(1 for s in sessions if s.get("name_source") == "derived")
    return {
        "schema": SCHEMA,
        # MEASURED 2026-08-13: ListAgents reported 34 peers while this registry
        # held 19. The gap is not a bug here — Remote Control and cloud sessions
        # never write to ~/.claude/sessions, so they are structurally invisible
        # to anything reading disk. Reporting 19 as though it were the fleet
        # would be the failure this repo has spent the day cataloguing, so the
        # limit travels with the answer.
        "coverage": {
            "sees": "local CLI sessions that bound an inbox socket",
            "blind_to": ["Remote Control sessions on this or other machines",
                         "Claude Code on the web (cloud) sessions",
                         "sessions started in bare mode, which bind no socket"],
            "authoritative_source_for_those": "the ListAgents tool, not disk",
            "self_excluded_by_ListAgents": True,
        },
        "sessions_seen": len(sessions),
        "reachable": sum(1 for s in sessions if s["reachable"]),
        "stale_records": sum(1 for s in sessions if not s["process_alive"]),
        "derived_names": derived,
        "by_repo": {k: [{"name": s["name"], "kind": s["kind"],
                         "cwd": s["cwd"], "age_s": s["age_s"]}
                        for s in v]
                    for k, v in sorted(by_repo.items())},
        "problems": problems,
        "reading": ("names are derived per session, so they identify a session "
                    "and not an agent; address by repo + role and re-resolve "
                    "each time rather than storing a name"),
    }


def resolve(agent: str | None, workspace: str | None) -> dict:
    """agent_id (or a bare workspace) -> the names that currently answer for it."""
    repo = workspace
    if agent and not repo:
        # `claude@quantum` / `codex@memoryOS` — the part after @ is the workspace.
        repo = agent.split("@", 1)[1] if "@" in agent else agent
    sessions, problems = read_sessions()
    live = [s for s in sessions if s["reachable"] and _repo_of(s["cwd"]) == repo]
    dead = [s for s in sessions if not s["reachable"] and _repo_of(s["cwd"]) == repo]
    return {
        "schema": SCHEMA, "agent": agent, "workspace": repo,
        "address": [s["name"] for s in live],
        "candidates": [{"name": s["name"], "cwd": s["cwd"], "kind": s["kind"],
                        "tmux": s["tmux"], "age_s": s["age_s"]} for s in live],
        "gone": [{"name": s["name"], "claimed_status": s["claimed_status"]}
                 for s in dead],
        "ambiguous": len(live) > 1,
        "problems": problems,
        "note": ("more than one live session in a workspace means the agent_id "
                 "does not pick one — disambiguate by cwd or role before "
                 "sending, since the two are different contexts"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover", help="live sessions grouped by workspace")
    d.add_argument("--json", action="store_true")
    r = sub.add_parser("resolve", help="who currently answers for an agent")
    r.add_argument("--agent")
    r.add_argument("--workspace")
    r.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "discover":
        out = discover()
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
        else:
            print(f"{out['reachable']} reachable of {out['sessions_seen']} "
                  f"records ({out['stale_records']} stale, "
                  f"{out['derived_names']} derived names)")
            for repo, ss in out["by_repo"].items():
                print(f"  {repo:<24} {', '.join(s['name'] for s in ss)}")
            print(f"\n{out['reading']}")
        return 0

    if not (a.agent or a.workspace):
        ap.error("resolve needs --agent or --workspace")
    out = resolve(a.agent, a.workspace)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"{out['agent'] or out['workspace']} -> "
              f"{out['address'] or 'NOBODY LIVE'}")
        if out["ambiguous"]:
            print(f"  ambiguous: {out['note']}")
        for g in out["gone"]:
            print(f"  gone: {g['name']} (record still says "
                  f"{g['claimed_status']!r})")
    return 0 if out["address"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
