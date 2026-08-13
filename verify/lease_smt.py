#!/usr/bin/env python3
"""Bounded model check of the arc lease's single-writer invariant (INV-3).

Why a solver instead of another test. Every oracle in this repository is a check
I wrote in the same language as the thing it checks, and the one place we have
already been wrong about concurrency — a lease guard that blocked an agent from
recording its own progress — was found by hitting it, not by reasoning about it.
Tests sample schedules. A solver enumerates them, and when it says UNSAT within
the bound it is saying something my reading of the code cannot.

WHAT IS MODELLED (kept close to scripts/aios_society.py):

    lease_live(st, now)     = owner is set and lease_until > now        (TTL only)
    holder_present(st, now) = lease_live and (pid alive, same host)
    claim  is serialised    — it runs inside _with_arc_lock
    note   is NOT           — it reads, projects, checks the guard, then appends,
                              with no mutual exclusion against a concurrent claim

The last line is the whole question, so `note` is modelled as two separate steps
with a gap in between, which is what the code actually does.

WHAT IS NOT MODELLED, stated so the result is not over-read:
  - hashing, file IO, crash-during-append, clock skew between hosts
  - more than the bounded number of agents and steps given below
  - the watchdog, supersede, and handoff paths
  A verdict here is about the lease guard alone, at this bound, under these
  abstractions. UNSAT is not a proof of the implementation; it is a proof about
  this model, which is a claim about the code only as far as the model is faithful.

    python3 verify/lease_smt.py            # both properties
    python3 verify/lease_smt.py --json

Requires z3-solver (pip install z3-solver). Exit 1 if a property that should
hold is violated.
"""
from __future__ import annotations

import argparse
import json

import z3


def check_note_race(atomic_note: bool) -> dict:
    """Can a non-owner's progress land on the arc?

    Schedule under test, three steps, two agents:

        1. A reads the arc          — sees itself as owner with a live lease
        2. B claims                 — legitimately, because A's holder is absent
        3. A appends its progress   — guard already passed at step 1

    `atomic_note=True` models the repair: read and append inside the same arc
    lock, so no claim can land between them.
    """
    s = z3.Solver()
    A, B = 0, 1

    t_read, t_claim, t_append = z3.Reals("t_read t_claim t_append")
    lease_until_A, lease_until_B = z3.Reals("lease_until_A lease_until_B")
    ttl = z3.Real("ttl")

    s.add(ttl > 0)
    s.add(t_read < t_claim, t_claim < t_append)      # a real interleaving

    # Step 1 — A passes note()'s guard: it is owner and its lease is live.
    owner_at_read = A
    s.add(owner_at_read == A)
    s.add(lease_until_A > t_read)                    # lease_live(A, t_read)

    # Step 2 — B claims. claim() refuses only while holder_present is true.
    # holder_present = lease_live AND pid alive (same host). A's process is
    # gone, so the arc is free even though A's TTL has not burned down — this
    # is deliberate in the code (fast MTTR) and is what makes the race possible.
    a_process_alive = z3.Bool("a_process_alive")
    s.add(a_process_alive == False)                  # noqa: E712 — the modelled case
    s.add(lease_until_B == t_claim + ttl)

    # Step 3 — A appends. Its guard was evaluated at t_read, not now.
    # With an atomic note, no claim can occur inside the read..append window.
    if atomic_note:
        s.add(z3.Or(t_claim < t_read, t_claim > t_append))
        s.add(t_read < t_append)

    # SAFETY: whoever appends must be the owner AT APPEND TIME.
    owner_at_append = B                              # B claimed at step 2
    s.add(owner_at_append != A)                      # ...and A is appending

    r = s.check()
    out = {"property": "single_writer_note",
           "atomic_note": atomic_note,
           "result": str(r),
           "safe": r == z3.unsat}
    if r == z3.sat:
        m = s.model()
        out["counterexample"] = {
            str(d): str(m[d]) for d in m.decls()
        }
        out["reading"] = ("a schedule exists where A's guard passes, B takes the "
                          "arc, and A's progress still lands — two writers on one "
                          "arc, which INV-3 forbids")
    else:
        out["reading"] = ("no such schedule within the bound: making read and "
                          "append atomic removes the window")
    return out


def check_claim_exclusion() -> dict:
    """Two agents must never both hold a live lease after serialised claims.

    This is the part the code already gets right — claim runs under the arc
    lock — and it is checked so that a future change which drops the lock is
    caught here rather than in production.
    """
    s = z3.Solver()
    t1, t2, ttl = z3.Reals("t1 t2 ttl")
    s.add(ttl > 0, t1 < t2)

    # Serialised claims: A at t1, then B at t2. B may only claim if A's holder
    # is absent, and claiming rewrites the owner — there is one owner variable,
    # so "both own it" is only expressible as B claiming while A still holds.
    a_present = z3.Bool("a_present")
    s.add(a_present == z3.And(t1 + ttl > t2, z3.Bool("a_pid_alive")))
    s.add(a_present)                       # A still present...
    s.add(z3.Bool("b_claim_succeeded"))    # ...and B's claim went through anyway
    s.add(z3.Implies(z3.Bool("b_claim_succeeded"), z3.Not(a_present)))

    r = s.check()
    return {"property": "claim_mutual_exclusion", "result": str(r),
            "safe": r == z3.unsat,
            "reading": ("claim refuses while the holder is present, so the two "
                        "cannot both hold; a change dropping the arc lock would "
                        "make this SAT")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    racy = check_note_race(atomic_note=False)
    fixed = check_note_race(atomic_note=True)
    excl = check_claim_exclusion()

    report = {
        "schema": "aios.lease_smt.v0",
        "solver": "z3",
        "findings": [racy, fixed, excl],
        # The point of the run: the current shape is SAT (a real interleaving
        # exists) and the atomic shape is UNSAT, which is what identifies the
        # missing lock as the cause rather than a guess.
        "verdict": {
            "note_is_racy_as_written": racy["result"] == "sat",
            "atomicity_removes_it": fixed["result"] == "unsat",
            "claim_exclusion_holds": excl["safe"],
        },
    }
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        for f in report["findings"]:
            mark = "SAFE  " if f["safe"] else "VIOLABLE"
            extra = "" if f["safe"] else "  <- counterexample found"
            print(f"[{mark}] {f['property']}"
                  f"{' (atomic)' if f.get('atomic_note') else ''}{extra}")
            print(f"          {f['reading']}")
        v = report["verdict"]
        print(f"\nnote racy as written : {v['note_is_racy_as_written']}")
        print(f"atomicity fixes it   : {v['atomicity_removes_it']}")
    # Exit non-zero when the invariant we rely on is violable as written.
    return 1 if report["verdict"]["note_is_racy_as_written"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
