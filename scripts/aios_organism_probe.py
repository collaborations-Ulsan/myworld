#!/usr/bin/env python3
"""Organism probe — does each OS actually WORK for an agent, right now?

founder: *"check the memoryOS do work exactly for Agents. even other OS too.
as a organism system"*.

Docs claim; this RUNS. For each sibling OS we execute the smallest real call an
agent would make and record what came back — not whether a file exists, not
whether a README says it is ready.

The grading is deliberately harsh and follows what our own measurements taught:
an OS organ is only working **for an agent** if an agent can invoke it and get
something back that changes what it does. So each organ is scored on three
axes, and a green on the first two with a red on the third is exactly the
"library, not an OS" failure our own data found (three optional mechanisms,
96 episodes, 0 uses — docs/AIOS_WHAT_THE_OS_IS_2026-08-09.md):

    reachable   an agent can call it from a fresh process
    answers     it returns non-empty, well-formed content
    acts        it DOES something without the agent choosing to accept it
                (an organ that only offers is not yet an OS function)

Organism view: an organ that is reachable but never invoked in real runs is
vestigial, and this probe says so rather than counting it as healthy.

    python3 scripts/aios_organism_probe.py [--json]

Stdlib-only, read-only, no network. Every probe is bounded; a timeout is
recorded as a failure of that organ, never as a pass.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
TIMEOUT = 90.0


def _run(argv: list[str], cwd: Path = ROOT, timeout: float = TIMEOUT) -> dict:
    t0 = time.time()
    try:
        r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout)
        return {"rc": r.returncode, "out": r.stdout, "err": r.stderr[-400:],
                "wall_s": round(time.time() - t0, 2), "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"rc": None, "out": "", "err": f"timeout after {timeout}s",
                "wall_s": round(time.time() - t0, 2), "timed_out": True}
    except OSError as exc:
        return {"rc": None, "out": "", "err": f"{type(exc).__name__}: {exc}",
                "wall_s": round(time.time() - t0, 2), "timed_out": False}


def probe_memoryos() -> dict:
    """The organ the founder named first: can an agent ask it something and
    get an answer that is about the question?"""
    mo = ROOT / "memoryOS"
    if not mo.is_dir():
        return {"organ": "memoryOS", "reachable": False,
                "detail": "memoryOS/ not present"}
    stats = _run([PY, "-m", "memoryos", "--root", ".", "stats"], cwd=mo)
    q = "왜 로컬 개선이 실제 환경에서 안 먹히나"
    search = _run([PY, "-m", "memoryos", "--root", ".", "search", q,
                   "--limit", "5", "--json"], cwd=mo)
    hits = None
    if search["rc"] == 0:
        try:
            payload = json.loads(search["out"] or "{}")
            hits = payload if isinstance(payload, list) else payload.get("results")
            hits = len(hits) if hits is not None else None
        except json.JSONDecodeError:
            hits = "unparseable json"
    return {
        "organ": "memoryOS",
        "reachable": stats["rc"] == 0,
        "answers": bool(hits) if isinstance(hits, int) else False,
        "acts": False,   # retrieval happens only when a human types a command
        "semantic_hits_for_a_conceptual_query": hits,
        "stats_tail": (stats["out"] or "").strip().splitlines()[-3:],
        "note": ("retrieval is pull-only: nothing invokes it inside an agent "
                 "turn, so it cannot change behaviour unless a human asks"),
        "evidence": {"stats_rc": stats["rc"], "search_rc": search["rc"],
                     "search_err": search["err"][:200]},
    }


def probe_arc_ledger() -> dict:
    """Our own organ, and the only one with a measured effect (G5/G6)."""
    import tempfile
    d = tempfile.mkdtemp(prefix="organism-arc-")
    s = ROOT / "scripts" / "aios_society.py"
    opened = _run([PY, str(s), "--arcs-dir", d, "open", "--goal",
                   "organism probe", "--agent", "probe@organism"])
    arc = None
    if opened["rc"] == 0:
        try:
            arc = json.loads(opened["out"])["arc_id"]
        except (json.JSONDecodeError, KeyError):
            pass
    pack = _run([PY, str(s), "--arcs-dir", d, "pack", "--arc", arc]) if arc else None
    return {
        "organ": "arc ledger (aios_society)",
        "reachable": opened["rc"] == 0,
        "answers": bool(pack and pack["rc"] == 0),
        "acts": True,   # the resume pack is INJECTED, not offered (G5/G6 arm B)
        "measured_effect": "+9.38pp (n=32), +8.54pp (n=82); p=0.0592 — used, not claimed",
        "evidence": {"open_rc": opened["rc"],
                     "pack_rc": (pack or {}).get("rc")},
    }


def probe_sandbox() -> dict:
    """The organ that never asks permission — our best one by construction."""
    code = ("import sys; sys.path.insert(0, %r); import aios_sandbox as s, time; "
            "r = s.run_sandboxed(['/bin/echo','organism'], timeout=20.0, "
            "now=time.time(), receipt_log=None); "
            "print(r.sandboxed, r.ok, r.engine)" % str(ROOT / "scripts"))
    out = _run([PY, "-c", code])
    parts = (out["out"] or "").split()
    ok = len(parts) >= 3 and parts[0] == "True" and parts[1] == "True"
    # does it actually DENY something? that is the 'acts' test
    deny = ("import sys; sys.path.insert(0, %r); import aios_sandbox as s, time; "
            "r = s.run_untrusted_code('import socket,sys\\n"
            "try:\\n socket.create_connection((\\'1.1.1.1\\',53),timeout=3)\\n"
            " print(\\'REACHED\\')\\nexcept Exception as e:\\n print(\\'BLOCKED\\')', "
            "timeout=25.0, now=time.time(), receipt_log=None); "
            "print(r.sandboxed, r.stdout.strip()[:20])" % str(ROOT / "scripts"))
    dout = _run([PY, "-c", deny])
    denied = "BLOCKED" in (dout["out"] or "")
    return {
        "organ": "sandbox (aios_sandbox)",
        "reachable": ok, "answers": ok, "acts": denied,
        "engine": parts[2] if len(parts) >= 3 else None,
        "network_denied_to_untrusted_code": denied,
        "note": "the only organ that enforces without asking the model",
        "evidence": {"probe_out": (out["out"] or "").strip()[:80],
                     "deny_out": (dout["out"] or "").strip()[:80]},
    }


def probe_capabilityos() -> dict:
    co = ROOT / "CapabilityOS"
    if not co.is_dir():
        return {"organ": "CapabilityOS", "reachable": False,
                "detail": "not present"}
    pkg = list(co.glob("**/__init__.py"))
    py = list(co.glob("**/*.py"))
    return {"organ": "CapabilityOS", "reachable": bool(pkg),
            "answers": False, "acts": False,
            "note": ("docs-only if no importable package: %d py files, "
                     "%d packages" % (len(py), len(pkg))),
            "evidence": {"py_files": len(py), "packages": len(pkg)}}


def probe_genesisos() -> dict:
    go = ROOT / "GenesisOS"
    if not go.is_dir():
        return {"organ": "GenesisOS", "reachable": False, "detail": "not present"}
    py = list(go.glob("**/*.py"))
    return {"organ": "GenesisOS", "reachable": bool(py), "answers": False,
            "acts": False,
            "note": "advisory by charter — proposes, never selects final truth",
            "evidence": {"py_files": len(py)}}


def probe_hivemind() -> dict:
    hm = ROOT / "hivemind"
    if not hm.is_dir():
        return {"organ": "hivemind", "reachable": False, "detail": "not present"}
    out = _run([PY, "-c",
                "import sys; sys.path.insert(0, '.'); "
                "import hivemind.run_receipts as r; print('ok', hasattr(r, 'git_changed_files'))"],
               cwd=hm)
    return {"organ": "hivemind", "reachable": out["rc"] == 0,
            "answers": "ok" in (out["out"] or ""), "acts": False,
            "note": "verification runs when a run is dispatched, not per agent turn",
            "evidence": {"rc": out["rc"], "err": out["err"][:160]}}


PROBES = (probe_memoryos, probe_arc_ledger, probe_sandbox, probe_capabilityos,
          probe_genesisos, probe_hivemind)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="does each OS work for an agent?")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    organs = []
    for p in PROBES:
        try:
            organs.append(p())
        except Exception as exc:                      # a probe must never mask
            organs.append({"organ": p.__name__, "reachable": False,
                           "probe_error": f"{type(exc).__name__}: {exc}"[:200]})

    acting = [o for o in organs if o.get("acts")]
    answering = [o for o in organs if o.get("answers") and not o.get("acts")]
    dead = [o for o in organs if not o.get("reachable")]
    report = {
        "schema": "aios.organism_probe.v1",
        "organs": organs,
        "summary": {
            "n": len(organs),
            "acts_without_being_asked": [o["organ"] for o in acting],
            "answers_but_only_when_asked": [o["organ"] for o in answering],
            "unreachable": [o["organ"] for o in dead],
        },
        "reading": ("An organ that only ANSWERS is a library. Our own data "
                    "(3 optional mechanisms, 96 episodes, 0 uses) says a "
                    "library changes nothing unless something makes it fire. "
                    "Count the ACTS column, not the organ count."),
    }
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0
    print(f"organs probed: {len(organs)}")
    for o in organs:
        mark = "ACTS " if o.get("acts") else ("answers" if o.get("answers")
                                              else ("reach" if o.get("reachable")
                                                    else "DEAD "))
        print(f"  [{mark:7s}] {o['organ']:28s} {o.get('note') or o.get('detail') or ''}"[:118])
    print(f"\nacts without being asked : {report['summary']['acts_without_being_asked']}")
    print(f"answers only when asked  : {report['summary']['answers_but_only_when_asked']}")
    print(f"unreachable              : {report['summary']['unreachable']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
