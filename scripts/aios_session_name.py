#!/usr/bin/env python3
"""Session naming protocol — the half of RC that AIOS can actually own.

founder: define a protocol, and have AIOS use RC.

Half of that is buildable and half is not, and the split is a fact rather than
an effort problem. Checked against the harvested docs
(`docs/external/providers/claude/`):

  CAN be owned by AIOS
    `--name` / `-n`  set a session's name at launch, and `claude --resume <name>`
                     resumes by it, so a name set by the host is durable
    `/rename`        changes it mid-session
    `--remote-control-session-name-prefix` (or the matching env var) controls
                     auto-generated Remote Control names, default = hostname

  CANNOT be owned by AIOS
    `ListAgents` and `SendMessage` are TOOLS. They are not CLI commands and do
    not appear in the Agent SDK surface, so no script enumerates peers or sends
    to one — only a model in a turn can. Building "AIOS drives RC" on top of
    that would make the capability exist solely when a model chooses to use it,
    which is the definition of an offer, and offers measured zero uses in 96
    episodes.

So the protocol divides on that line. AIOS owns naming, identity, the brief and
the settlement; the model owns the send alone, and the receipt says so instead
of implying the loop is closed.

THE NAME

    claude@<workspace>/<role>        e.g. claude@myworld/upper

Derived names collide by construction — measured 2026-08-13, 19 of 19 local
sessions carried nameSource=derived, and six workspaces held two sessions
differing only by two hex characters (quantum-fd vs quantum-d4). A workspace
alone does not address an agent when two of them are working in it; the role is
what makes `resolve` return one answer instead of `ambiguous`.

    python3 scripts/aios_session_name.py plan --workspace quantum --role adversary
    python3 scripts/aios_session_name.py audit

Reads only; `plan` prints a command rather than running it, because launching or
renaming another operator's session is their call and not this script's.
Schema: aios.session_name.v0   Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_peer_bind as PB  # noqa: E402

SCHEMA = "aios.session_name.v0"
NAME = re.compile(r"^claude@(?P<ws>[A-Za-z0-9_.-]+)/(?P<role>[a-z][a-z0-9-]{1,23})$")

# Roles are a closed set on purpose. An open vocabulary drifts into prose, and
# prose is what Remote Control names already are — up to 190 characters, one of
# them a model's refusal string. A role has to be short enough to read in a
# listing and stable enough to address next week.
ROLES = {
    "upper": "sets goals, specifies contracts, judges receipts",
    "base": "builds enforcement and execution substrate below the seam",
    "adversary": "tries to kill claims; authors falsifiers it did not propose",
    "librarian": "retrieves and records; never decides",
    "operator": "runs the day's arc for a product repo",
    "scratch": "exploratory, not addressed by anyone",
}


def build(workspace: str, role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; known: {sorted(ROLES)}")
    return f"claude@{workspace}/{role}"


def parse(name: str) -> dict | None:
    m = NAME.match(name or "")
    return m.groupdict() if m else None


def plan(workspace: str, role: str, remote: bool) -> dict:
    name = build(workspace, role)
    cmd = ["claude", "--name", name]
    if remote:
        # RC names are auto-generated from a prefix when no explicit name is
        # set; the prefix defaults to the hostname, which says which BOX a
        # session is on and nothing about what it is for.
        cmd = ["claude", "remote-control",
               "--remote-control-session-name-prefix", f"{workspace}-{role}"]
    return {"schema": SCHEMA, "name": name, "role_means": ROLES[role],
            "launch": " ".join(cmd),
            "rename_existing": f"/rename {name}",
            "resume_later": f"claude --resume {name}",
            "note": ("printed, not executed — renaming or launching another "
                     "operator's session is their decision")}


def audit() -> dict:
    """How much of the live fleet follows the protocol? Counted, not asserted."""
    sessions, problems = PB.read_sessions()
    live = [s for s in sessions if s["reachable"]]
    conforming, derived, other = [], [], []
    for s in live:
        if parse(s["name"] or ""):
            conforming.append(s["name"])
        elif s.get("name_source") == "derived":
            derived.append(s["name"])
        else:
            other.append(s["name"])
    # Collisions are the concrete cost of derived names, so they are reported
    # as pairs rather than as a percentage nobody acts on.
    by_repo: dict[str, list[str]] = {}
    for s in live:
        by_repo.setdefault(PB._repo_of(s["cwd"]) or "(outside)", []).append(s["name"])
    collisions = {k: v for k, v in by_repo.items() if len(v) > 1}
    return {
        "schema": SCHEMA,
        "live_sessions": len(live),
        "conforming": conforming,
        "derived_names": derived,
        "other": other,
        "workspaces_with_more_than_one_session": collisions,
        "coverage": PB.discover()["coverage"],
        "reading": (
            f"{len(conforming)}/{len(live)} follow the protocol. Every "
            f"non-conforming name identifies a session rather than an agent, so "
            f"resolve() returns 'ambiguous' for the "
            f"{len(collisions)} workspace(s) holding more than one."),
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("roles")
    p = sub.add_parser("plan")
    p.add_argument("--workspace", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--remote", action="store_true")
    a2 = sub.add_parser("audit")
    a2.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "roles":
        print(json.dumps(ROLES, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "plan":
        print(json.dumps(plan(a.workspace, a.role, a.remote),
                         ensure_ascii=False, indent=1))
        return 0
    out = audit()
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"{len(out['conforming'])}/{out['live_sessions']} conforming")
        for repo, names in out["workspaces_with_more_than_one_session"].items():
            print(f"  collision {repo:<22} {', '.join(names)}")
        print(f"\n{out['reading']}")
        print(f"blind to: {', '.join(out['coverage']['blind_to'])}")
    return 0 if not out["derived_names"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
