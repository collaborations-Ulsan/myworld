#!/usr/bin/env python3
"""aios.override.v1 — DNA #6 applied to the gates I built, not just the ones I inherited.

Measured 2026-08-19: seven DNA invariants, one of which says operator override must always
be possible — against 56 refusals I added today, of which exactly ONE (spawn --force) had
a way through. So the thing limiting the agents is not the DNA. It is my own accretion,
and it accreted without the escape clause the DNA itself insists on.

An override is not a bypass. A bypass leaves no trace and teaches nothing; an override
demands a reason, records it, and — the part that matters — becomes EVIDENCE. A gate
overridden ten times with the same reason is a gate that is wrong, and the ledger is how
we find that out instead of arguing about it.

    permit(gate, reason)     -> (allowed, note). Refused without a reason. Always logged.
    audit()                  -> which gates get overridden, how often, and why

The gates that must NOT be overridable are named here explicitly rather than by omission,
because a list of exceptions that is implicit is a list nobody can review: the privacy
boundary, and any check whose whole purpose is to stop us marking our own work as verified.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / ".aios" / "overrides.jsonl"

# Named, not implied. These stay closed because opening them removes the reason the rest
# of the system can be believed at all.
NEVER = {
    "privacy.boundary": "_from_desktop/dain/minyoung/secrets — DNA #7, founder-level",
    "verify.self_close": "a worker closing its own task by assertion; the whole "
                         "anti-reward-hacking clause is this one check",
    "verify.consumed": "marking output consumed without its evidence — that is how "
                       "invocation gets counted as use",
    "experiment.independence": "taking a control arm I authored the treatment for; "
                               "the preregistration exists to prevent exactly this",
}


def permit(gate: str, reason: str, *, who: str = "", ttl_s: int = 0) -> tuple[bool, str]:
    who = who or os.environ.get("AIOS_MESH_NAME") or "claude@myworld/upper"
    if gate in NEVER:
        _log(gate, reason, who, allowed=False, why=NEVER[gate])
        return False, f"NOT OVERRIDABLE: {NEVER[gate]}"
    if not reason or len(reason.strip()) < 12:
        _log(gate, reason, who, allowed=False, why="no reason given")
        return False, ("override refused: give a reason. An override without one is a "
                       "bypass, and a bypass teaches the system nothing.")
    _log(gate, reason, who, allowed=True, why="", ttl_s=ttl_s)
    return True, "allowed and recorded"


def _log(gate: str, reason: str, who: str, *, allowed: bool, why: str, ttl_s: int = 0) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps({"ts": time.time(), "gate": gate, "reason": reason[:300],
                             "who": who, "allowed": allowed, "refusal_note": why,
                             "expires": (time.time() + ttl_s) if ttl_s else None},
                            ensure_ascii=False) + "\n")


def audit() -> dict:
    if not LEDGER.exists():
        return {"n": 0}
    rows = []
    for line in LEDGER.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    by_gate = Counter(r["gate"] for r in rows if r["allowed"])
    repeated_reason = {}
    for g in by_gate:
        rs = Counter(r["reason"][:60] for r in rows if r["allowed"] and r["gate"] == g)
        top, n = rs.most_common(1)[0]
        if n >= 3:
            repeated_reason[g] = {"reason": top, "times": n}
    return {"n": len(rows), "allowed": sum(r["allowed"] for r in rows),
            "by_gate": dict(by_gate.most_common()),
            "suspect_gates": repeated_reason}


def main() -> int:
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="subcmd", required=True)
    p = s.add_parser("permit"); p.add_argument("gate"); p.add_argument("reason")
    p.add_argument("--ttl", type=int, default=0)
    s.add_parser("audit"); s.add_parser("never")
    a = ap.parse_args()
    if a.subcmd == "permit":
        ok, note = permit(a.gate, a.reason, ttl_s=a.ttl)
        print(f"{'ALLOWED' if ok else 'REFUSED'}: {note}")
        return 0 if ok else 1
    if a.subcmd == "never":
        for g, why in NEVER.items():
            print(f"  {g:<28}{why}")
        return 0
    r = audit()
    if not r["n"]:
        print("아직 아무 게이트도 우회되지 않았다.\n"
              "  이것은 게이트가 옳다는 뜻이 아니라, 아직 아무도 부딪히지 않았다는 뜻이다.")
        return 0
    print(f"  {r['allowed']}/{r['n']} overrides allowed")
    for g, n in r["by_gate"].items():
        print(f"    {g:<30}{n}")
    if r["suspect_gates"]:
        print("\n  같은 이유로 3회 이상 우회된 게이트 — 게이트가 틀렸다는 증거다:")
        for g, v in r["suspect_gates"].items():
            print(f"    {g}: {v['times']}회 — {v['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
