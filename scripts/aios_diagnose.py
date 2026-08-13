#!/usr/bin/env python3
"""Diagnostic partition — ask each epistemic organ the question it is actually for.

founder: descentnet, quantum, universe, goen and the dipeen work are not
separate projects. They are one program.

Reading them as one program changes what a consultation is. On 2026-08-10 I sent
four bespoke prompts about a single failure and got back four answers that were
valuable **because they were different questions**, not different opinions:

    quantum      is this an existence obstruction, or an execution one?
                 -> Vorob'ev (1962): pairwise-consistent marginals on an ACYCLIC
                    hypergraph always extend, so the obstruction cannot arise
    universe     is it answerable at all, and at what budget?
                 -> Theorem D shape: n_min = Omega(eps^-2l). Depth/budget, cliff
                    not slope
    descentnet   is a global section absent?
                 -> `gluable` at maximal confidence. The section EXISTS and the
                    machine fails to compute it
    goen         does meaning survive transport between frames?
                 -> only where transport is the identity; error is multiplicative
                    in composition depth

Four verdicts, and none of them agreed with another — they PARTITIONED the
problem. That is the opposite of a panel, and it matters because our own measured
ceiling says a panel of Claudes is worth about one vote (n_eff 1.75 across 16
substrates on 2026-08-13). Consultation is worth something here not because the
answerers are independent minds but because they hold different EVIDENCE and ask
different questions.

This module keeps that repeatable. It does not send anything and does not vote:
it emits the per-organ question in that organ's own register, and records the
returned verdicts as a partition with an explicit residue.

    python3 scripts/aios_diagnose.py organs
    python3 scripts/aios_diagnose.py brief --claim "..." --observation "..."
    python3 scripts/aios_diagnose.py record --claim-id C1 --organ quantum \\
        --verdict not_mine --because "Vorob'ev: the chain is acyclic"

Schema: aios.diagnose.v0   Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

SCHEMA = "aios.diagnose.v0"
ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ideation" / "diagnoses.jsonl"

# The registry IS the content of this module. Each entry is the question that
# organ can answer better than anyone else, phrased so a wrong answer is
# recognisable — a question an organ cannot fail is not a diagnostic.
ORGANS: dict[str, dict] = {
    "quantum": {
        "workspace": "quantum",
        "asks": "Is this an EXISTENCE obstruction or an EXECUTION failure?",
        "register": ("marginals and joints, monogamy, contextuality, weak "
                     "measurement, decision boundaries under compression"),
        "answers_no_when": ("the parts extend to a consistent whole, so nothing "
                            "forbids the answer and only the computation failed"),
        "proved_useful": ("2026-08-10: killed the quantum-marginal framing of "
                          "two-hop composition at theorem level"),
    },
    "universe": {
        "workspace": "universe",
        "asks": "Is it answerable at all, and at what sample or depth budget?",
        "register": ("APEX answerability, identifiability, intervention depth, "
                     "gauge vs budget-blocked, Le Cam deficiency"),
        "answers_no_when": ("widening the instrument set recovers the answer, so "
                            "the limit is budget rather than the question"),
        "proved_useful": ("2026-08-10: classified our failure as depth-graded "
                          "(Theorem D) rather than a gluing obstruction"),
    },
    "descentnet": {
        "workspace": "descentnet",
        "asks": "Is a global section ABSENT, or merely uncomputed?",
        "register": ("typed covers, cocycle conditions on triple overlaps, "
                     "coker(D) obstruction, gluable | ambiguous | obstructed"),
        "answers_no_when": ("the cocycle closes and the residual is zero — the "
                            "section exists and something failed to find it"),
        "proved_useful": ("2026-08-10: returned `gluable` at maximal confidence "
                          "and refused to let a parked sheaf line be revived"),
    },
    "goen": {
        "workspace": "_from_desktop",
        "asks": "Does meaning survive transport between frames?",
        "register": ("orthogonal transport, cycle-consistency, flat sections, "
                     "holonomy, grow-only ledgers with derived views"),
        "answers_no_when": ("the transport is the identity, i.e. the consumer "
                            "reads in the frame the record was written in"),
        "proved_useful": ("2026-08-10: scoped a design rule of mine to the "
                          "resumption class and refused its generalisation"),
        "boundary": ("lives under the privacy boundary — technical structure "
                     "only, never private content, in either direction"),
    },
    "computation": {
        "workspace": "myworld_computation",
        "asks": "Can this be EXECUTED under a real boundary and settled?",
        "register": ("cages, namespaces, Landlock, deterministic oracles, "
                     "exit codes, receipts that revert"),
        "answers_no_when": ("the claim's oracle lives in a laboratory rather "
                            "than in code, so no executor here can settle it"),
        "proved_useful": ("2026-08-13: found 0 of 49 ledger falsifiers runnable "
                          "and refused to have a model translate them"),
    },
}

# What this partition is NOT, kept next to what it is.
NOT_A_PANEL = (
    "Verdicts here are not votes and must never be counted as agreement. Our "
    "measured ceiling is n_eff 1.75 across 16 substrates; consultation pays "
    "because these organs hold different EVIDENCE and ask different questions, "
    "not because they are independent minds. Two organs claiming the same "
    "failure is a signal about the failure, not a stronger result."
)

VERDICTS = ("mine", "not_mine", "partly", "unknown")


def brief(claim: str, observation: str) -> dict:
    """The per-organ question, in that organ's own register."""
    out = []
    for name, o in ORGANS.items():
        out.append({
            "organ": name, "workspace": o["workspace"],
            "question": o["asks"],
            "ask_in_this_register": o["register"],
            "prompt": (
                f"claim under test: {claim}\n"
                f"observation: {observation}\n\n"
                f"{o['asks']}\n"
                f"Answer in your own register ({o['register']}), and say "
                f"NOT MINE if it is not — a 'not mine' with a reason is the "
                f"useful answer, not a failure to help. You answer no when: "
                f"{o['answers_no_when']}."
            ),
            **({"boundary": o["boundary"]} if "boundary" in o else {}),
        })
    return {"schema": SCHEMA, "claim": claim, "observation": observation,
            "organs": out, "not_a_panel": NOT_A_PANEL}


def record(claim_id: str, organ: str, verdict: str, because: str,
           evidence: str = "") -> dict:
    if organ not in ORGANS:
        raise ValueError(f"unknown organ {organ!r}; known: {sorted(ORGANS)}")
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if not because.strip():
        raise ValueError("a verdict without a reason is a vote, and votes are "
                         "the thing this module exists to avoid")
    rec = {"schema": SCHEMA, "claim_id": claim_id, "organ": organ,
           "verdict": verdict, "because": because.strip(),
           "evidence": evidence, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return rec


def partition(claim_id: str) -> dict:
    rows = []
    if LEDGER.exists():
        for ln in LEDGER.open(encoding="utf-8"):
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if r.get("claim_id") == claim_id:
                rows.append(r)
    latest = {r["organ"]: r for r in rows}          # last verdict per organ wins
    claimed = [o for o, r in latest.items() if r["verdict"] in ("mine", "partly")]
    declined = [o for o, r in latest.items() if r["verdict"] == "not_mine"]
    silent = [o for o in ORGANS if o not in latest]
    return {
        "schema": SCHEMA, "claim_id": claim_id,
        "claimed_by": claimed, "declined_by": declined, "not_asked": silent,
        "verdicts": [{"organ": o, "verdict": r["verdict"], "because": r["because"]}
                     for o, r in sorted(latest.items())],
        # Silence is not a declination. An organ that was never asked has not
        # said "not mine", so a partition with anyone still silent cannot be
        # called a diagnosis however clean the answers so far look — the
        # unasked organ is exactly where the diagnosis might have gone.
        "reading": (
            f"incomplete: {len(silent)} organ(s) not asked ({', '.join(silent)}) "
            f"— silence is not a declination, so no diagnosis yet" if silent else
            "no organ claimed it — a class none of these questions covers, which "
            "is a finding" if not claimed else
            "more than one organ claimed it — the failure spans registers and the "
            "diagnosis is not yet sharp" if len(claimed) > 1 else
            "a single register claimed it, and every other declined — that is a "
            "diagnosis"),
        "complete": not silent,
        "not_a_panel": NOT_A_PANEL,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("organs")
    b = sub.add_parser("brief")
    b.add_argument("--claim", required=True)
    b.add_argument("--observation", default="")
    r = sub.add_parser("record")
    r.add_argument("--claim-id", required=True)
    r.add_argument("--organ", required=True)
    r.add_argument("--verdict", required=True, choices=VERDICTS)
    r.add_argument("--because", required=True)
    r.add_argument("--evidence", default="")
    p = sub.add_parser("partition")
    p.add_argument("--claim-id", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "organs":
        print(json.dumps({"organs": ORGANS, "not_a_panel": NOT_A_PANEL},
                         ensure_ascii=False, indent=1))
    elif a.cmd == "brief":
        print(json.dumps(brief(a.claim, a.observation), ensure_ascii=False,
                         indent=1))
    elif a.cmd == "record":
        print(json.dumps(record(a.claim_id, a.organ, a.verdict, a.because,
                                a.evidence), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(partition(a.claim_id), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
