#!/usr/bin/env python3
"""aios.instrument.v1 — an instrument may not report a finding it has not calibrated.

Measured bottleneck (2026-08-18): four instruments were wrong in one day.

    entropy -> support        inferred table size from entropy. Invalid.
    dangling refs 131,594     three parser defects. Real number 45,474.
    legacy candidates 695     574 of them were the audit trail.
    copyness "decisive no"    the question had a 90% dominant answer.

The two that did NOT go wrong had the same shape, and it is the only thing that
distinguished them:

    POSITIVE control  a case where the instrument MUST fire. If it does not, the
                      instrument is not reaching the thing it claims to measure.
    NEGATIVE control  a case where it MUST stay silent. If it fires, what it reports
                      is an artifact of the instrument, not a property of the world.

copyness had both (record_fact must diverge / irrelevant must not) and survived contact
with its own data. The entropy claim had neither and was published in a committed doc.

So this module makes the controls part of the RESULT TYPE. A Finding without both
controls passing carries `calibrated=False`, and `report()` refuses to print it as a
finding — it prints it as an observation with the failure named. It is not possible to
forget, because there is nowhere to put the number that skips the check.
"""
from __future__ import annotations
import json, sys, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable

LEDGER = Path(__file__).resolve().parent.parent / ".aios" / "instrument_calibration.jsonl"


@dataclass
class Control:
    name: str
    must: str                      # "fire" | "stay_silent"
    detail: str = ""
    observed: float | None = None
    passed: bool | None = None


@dataclass
class Finding:
    claim: str
    value: float | str
    positive: Control
    negative: Control
    counterexample: str = ""       # description of the hostile case
    in_scope: bool | None = None   # does it satisfy the claim's PREMISE? (else it tests nothing)
    refutes: bool | None = None    # given the premise holds, does the CONCLUSION fail?
    notes: list[str] = field(default_factory=list)

    @property
    def calibrated(self) -> bool:
        return (bool(self.positive.passed) and bool(self.negative.passed)
                and self.in_scope is True and self.refutes is False)

    @property
    def blockers(self) -> list[str]:
        out = []
        if not self.positive.passed:
            out.append(f"POSITIVE control '{self.positive.name}' did not fire "
                       f"(observed {self.positive.observed}) — the instrument is not "
                       f"reaching what it claims to measure")
        if not self.negative.passed:
            out.append(f"NEGATIVE control '{self.negative.name}' fired "
                       f"(observed {self.negative.observed}) — the signal is an artifact "
                       f"of the instrument, not a property of the world")
        if not self.counterexample:
            out.append("no counterexample computed — the claim was never given a chance to fail")
        elif self.in_scope is not True:
            # The trap that bit the errata: it offered "1002 values at 3.99 bits" against
            # "LOW entropy implies small support". High entropy means the premise never held,
            # so the case was out of scope and tested nothing — while reading as a test.
            out.append("counterexample does not satisfy the claim's PREMISE — it is out of "
                       "scope and tests nothing, while reading as though it did")
        elif self.refutes is True:
            out.append("counterexample REFUTES the claim — the claim is false as stated")
        return out


def calibrate(pos_name: str, pos_fn: Callable[[], float], pos_min: float,
              neg_name: str, neg_fn: Callable[[], float], neg_max: float,
              *, pos_detail: str = "", neg_detail: str = "") -> tuple[Control, Control]:
    """Run both controls. Values are measured, never asserted."""
    pv = float(pos_fn())
    nv = float(neg_fn())
    return (Control(pos_name, "fire", pos_detail, pv, pv >= pos_min),
            Control(neg_name, "stay_silent", neg_detail, nv, nv <= neg_max))


def probe(premise: Callable[[], bool], conclusion: Callable[[], bool]) -> tuple[bool, bool]:
    """Run the claim's own inference on the hostile case.

    Returns (in_scope, refutes). A case where the premise is false is NOT a test — it is
    a vacuous pass that looks like diligence, which is exactly how the wrong counterexample
    survived review this morning."""
    ok = bool(premise())
    return ok, (ok and not bool(conclusion()))


def report(f: Finding, *, source: str = "") -> bool:
    """Print, log, and return whether this may be cited as a finding."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps({"ts": time.time(), "source": source or sys.argv[0],
                             "calibrated": f.calibrated, **asdict(f)},
                            ensure_ascii=False, default=str) + "\n")
    head = "FINDING" if f.calibrated else "OBSERVATION (uncalibrated — do not cite)"
    print(f"\n{head}: {f.claim}")
    print(f"  value: {f.value}")
    print(f"  + {f.positive.name}: observed {f.positive.observed} "
          f"[{'pass' if f.positive.passed else 'FAIL'}] {f.positive.detail}")
    print(f"  - {f.negative.name}: observed {f.negative.observed} "
          f"[{'pass' if f.negative.passed else 'FAIL'}] {f.negative.detail}")
    if f.counterexample:
        verdict = ("out of scope — PREMISE FALSE" if f.in_scope is not True
               else "REFUTES" if f.refutes else "survived")
    print(f"  counterexample: {f.counterexample}  [{verdict}]")
    for b in f.blockers:
        print(f"  BLOCKER: {b}")
    for n in f.notes:
        print(f"  note: {n}")
    return f.calibrated


if __name__ == "__main__":
    # self-test: the entropy claim that shipped wrong today, run through this module.
    import math

    def entropy(ps): return -sum(p * math.log2(p) for p in ps if p > 0)

    # POSITIVE: a genuinely 2-valued distribution must show low entropy
    # NEGATIVE: a 1002-valued distribution must NOT show low entropy — if it does,
    #           entropy is not tracking support and the inference is invalid.
    LOW = 2.0                                   # "low entropy" threshold, bits
    wide = [0.94] + [0.06 / 5000] * 5000        # 5001 distinct values

    pos, neg = calibrate(
        "instrument reads entropy at all", lambda: entropy([0.75, 0.25]), 0.5,
        "entropy of a uniform 4-way is not low", lambda: 2.0 - entropy([0.25] * 4), 0.0,
        pos_detail="H([.75,.25]) = 0.811 bits — the meter moves",
        neg_detail="H(uniform 4) = 2.0 bits, so the meter is not stuck low")

    # claim: entropy < LOW  =>  support <= 2.   premise = low entropy, conclusion = small support
    in_scope, refutes = probe(lambda: entropy(wide) < LOW, lambda: len(wide) <= 2)
    f = Finding(
        claim="signature entropy below 2 bits implies the offline table has at most 2 rows",
        value="0.811 bits observed",
        positive=pos, negative=neg,
        counterexample=f"[0.94] + [0.06/5000]*5000 -> {len(wide)} distinct values "
                       f"at {entropy(wide):.3f} bits",
        in_scope=in_scope, refutes=refutes,
    )
    ok = report(f, source="self-test: the claim that shipped wrong on 2026-08-16")
    print(f"\ncitable as a finding: {ok}")
    print("\nNow the same module against the errata's own counterexample:")
    narrow = [0.5, 0.25] + [0.25 / 1000] * 1000
    i2, r2 = probe(lambda: entropy(narrow) < LOW, lambda: len(narrow) <= 2)
    print(f"  [0.5,0.25]+[0.25/1000]*1000 -> {len(narrow)} values at {entropy(narrow):.3f} bits")
    print(f"  in_scope={i2}  refutes={r2}   <- premise false: it never tested the claim.")
    print("A correction needs the same calibration as a finding.")
