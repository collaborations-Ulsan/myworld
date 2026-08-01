#!/usr/bin/env python3
"""G2 verifier tests — the verifier itself must be verified.

The decisive tests are the INJECTED-DEFECT ones: a takeover that would pass a
byte-fidelity/checksum check but diverges in intent must be caught, because
that is the exact red-team attack this module answers.

    /home/user/miniconda3/bin/python3 -m pytest -q tests/test_aios_takeover_verify.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_society as soc            # noqa: E402
import aios_takeover_verify as tv     # noqa: E402

T0 = 1_800_000_000.0
GOAL = "fix the flaky retry in scripts/aios_dispatch.py lease reclaim"
NEXT = "add a regression test for reclaim under a stale lease"


@pytest.fixture()
def arcs(tmp_path: Path) -> Path:
    return tmp_path / "arcs"


@pytest.fixture()
def locks(tmp_path: Path) -> Path:
    return tmp_path / "locks"


def _handed_off_arc(arcs: Path, locks: Path, constraints=()) -> str:
    """An arc worked by a@one, then handed off — ready for a taker."""
    arc = soc.open_arc(GOAL, agent="a@one", now=T0, constraints=list(constraints),
                       arcs_dir=arcs)["arc_id"]
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    soc.note(arc, "reproduced the flaky reclaim in aios_dispatch", agent="a@one",
             now=T0 + 1, evidence=["run:123"], arcs_dir=arcs)
    soc.offer_handoff(arc, agent="a@one", now=T0 + 2, reason="context death",
                      next_step=NEXT, arcs_dir=arcs)
    return arc


def _take(arc: str, arcs: Path, locks: Path, agent="b@two", now=T0 + 3):
    pack = soc.resume_pack(arc, now=now, arcs_dir=arcs)
    out = soc.resume(arc, agent=agent, pack_tip_seq=pack["tip_seq"], now=now,
                     arcs_dir=arcs, locks_dir=locks)
    assert out["ok"], out
    return out


# --- the core case: faithful vs. drifted ----------------------------------

def test_faithful_takeover(arcs: Path, locks: Path):
    arc = _handed_off_arc(arcs, locks)
    _take(arc, arcs, locks)
    soc.note(arc, "added regression test for stale lease reclaim in "
                  "aios_dispatch; it fails before the fix",
             agent="b@two", now=T0 + 4, evidence=["tests/test_aios_dispatch.py"],
             arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    assert out["ok"] and out["verdict"] == "faithful"
    assert out["taker"] == "b@two" and out["prev_owner"] == "a@one"
    assert out["handed_next_step"] == NEXT


def test_INJECTED_DEFECT_taker_solves_a_different_problem(arcs: Path,
                                                          locks: Path):
    """The red-team attack: the handoff packet is structurally perfect and the
    taker is productive — on the WRONG work. Byte fidelity passes; intent does
    not. This must be caught."""
    arc = _handed_off_arc(arcs, locks)
    _take(arc, arcs, locks)
    soc.note(arc, "refactored the CSS grid on the marketing landing page",
             agent="b@two", now=T0 + 4, evidence=["site/styles.css"],
             arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    assert out["verdict"] == "drifted"
    cont = next(c for c in out["checks"] if c["name"] == "continuity")
    assert cont["passed"] is False
    assert cont["overlap_with_next_step"] < tv.CONTINUITY_FLOOR


def test_INJECTED_DEFECT_taker_does_nothing(arcs: Path, locks: Path):
    """Claiming an arc and going quiet is not a takeover."""
    arc = _handed_off_arc(arcs, locks)
    _take(arc, arcs, locks)
    out = tv.verify(arc, now=T0 + 9, arcs_dir=arcs, run_oracle=False)
    assert out["verdict"] == "drifted"
    assert "no progress events" in out["findings"][0]


def test_INJECTED_DEFECT_work_without_evidence(arcs: Path, locks: Path):
    """Prose progress with no artifact cited is unfalsifiable — refused."""
    arc = _handed_off_arc(arcs, locks)
    _take(arc, arcs, locks)
    soc.note(arc, "added the regression test for stale lease reclaim",
             agent="b@two", now=T0 + 4, arcs_dir=arcs)   # no evidence
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    assert out["verdict"] == "drifted"


# --- constraints ----------------------------------------------------------

def test_machine_checkable_constraint_violation_is_caught(arcs: Path,
                                                          locks: Path):
    arc = _handed_off_arc(arcs, locks,
                          constraints=["forbid:tests/conftest",
                                       "require:regression"])
    _take(arc, arcs, locks)
    soc.note(arc, "added regression test for stale lease reclaim; also edited "
                  "tests/conftest.py to auto-pass",
             agent="b@two", now=T0 + 4, evidence=["tests/conftest.py"],
             arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    assert out["verdict"] == "drifted"
    forbid = next(c for c in out["checks"]
                  if c.get("constraint", "").startswith("forbid:"))
    assert forbid["passed"] is False


def test_prose_constraint_is_reported_unenforceable_not_passed(arcs: Path,
                                                               locks: Path):
    """Silence is not a finding: a prose constraint must never read as met."""
    arc = _handed_off_arc(arcs, locks,
                          constraints=["be thoughtful and preserve the spirit"])
    _take(arc, arcs, locks)
    soc.note(arc, "added regression test for stale lease reclaim",
             agent="b@two", now=T0 + 4, evidence=["tests/x.py"], arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    prose = next(c for c in out["checks"] if c.get("constraint"))
    assert prose["ran"] is False and prose["passed"] is None
    assert out["n_unenforceable"] >= 1


def test_bad_regex_constraint_does_not_crash(arcs: Path, locks: Path):
    arc = _handed_off_arc(arcs, locks, constraints=["forbid:[unclosed"])
    _take(arc, arcs, locks)
    soc.note(arc, "regression test for stale lease reclaim added",
             agent="b@two", now=T0 + 4, evidence=["tests/x.py"], arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    bad = next(c for c in out["checks"] if c.get("constraint"))
    assert bad["ran"] is False and "bad regex" in bad["detail"]


# --- the oracle (strongest check) -----------------------------------------

def test_oracle_failure_forces_drifted(arcs: Path, locks: Path, tmp_path: Path):
    arc = soc.open_arc(GOAL, agent="a@one", now=T0, oracle_cmd="exit 3",
                       arcs_dir=arcs)["arc_id"]
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    soc.offer_handoff(arc, agent="a@one", now=T0 + 1, next_step=NEXT,
                      arcs_dir=arcs)
    _take(arc, arcs, locks, now=T0 + 2)
    soc.note(arc, "regression test for stale lease reclaim added",
             agent="b@two", now=T0 + 3, evidence=["tests/x.py"], arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 4, arcs_dir=arcs, cwd=tmp_path,
                    oracle_timeout=30)
    assert out["verdict"] == "drifted"
    oracle = next(c for c in out["checks"] if c["name"] == "oracle")
    assert oracle["ran"] and oracle["passed"] is False and oracle["returncode"] == 3


def test_oracle_pass_is_faithful(arcs: Path, locks: Path, tmp_path: Path):
    arc = soc.open_arc(GOAL, agent="a@one", now=T0, oracle_cmd="true",
                       arcs_dir=arcs)["arc_id"]
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    soc.offer_handoff(arc, agent="a@one", now=T0 + 1, next_step=NEXT,
                      arcs_dir=arcs)
    _take(arc, arcs, locks, now=T0 + 2)
    soc.note(arc, "regression test for stale lease reclaim added",
             agent="b@two", now=T0 + 3, evidence=["tests/x.py"], arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 4, arcs_dir=arcs, cwd=tmp_path,
                    oracle_timeout=30)
    assert out["verdict"] == "faithful"


# --- verifier hygiene -----------------------------------------------------

def test_self_judging_is_refused(arcs: Path, locks: Path):
    arc = _handed_off_arc(arcs, locks)
    _take(arc, arcs, locks)
    out = tv.verify(arc, now=T0 + 5, verifier="b@two", arcs_dir=arcs,
                    run_oracle=False)
    assert out["ok"] is False and "must not be the taker" in out["reason"]


def test_no_takeover_yields_nothing_to_verify(arcs: Path, locks: Path):
    arc = soc.open_arc(GOAL, agent="a@one", now=T0, arcs_dir=arcs)["arc_id"]
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    out = tv.verify(arc, now=T0 + 1, arcs_dir=arcs, run_oracle=False)
    assert out["ok"] is False and "no ownership transfer" in out["reason"]


def test_unverifiable_is_not_success(arcs: Path, locks: Path):
    """No oracle, no machine-checkable constraint, and the only signal is a
    prose constraint => the verdict must be unverifiable, never faithful."""
    arc = _handed_off_arc(arcs, locks, constraints=["be nice"])
    _take(arc, arcs, locks)
    soc.note(arc, "regression test for stale lease reclaim", agent="b@two",
             now=T0 + 4, evidence=["tests/x.py"], arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    assert out["verdict"] == "faithful"   # continuity DID run and passed
    # now the case where nothing at all can run:
    arc2 = _handed_off_arc(arcs, locks)
    _take(arc2, arcs, locks)
    monkey = tv.check_continuity
    try:
        tv.check_continuity = lambda s, w: {"name": "continuity", "ran": False,
                                            "passed": None, "detail": "n/a"}
        out2 = tv.verify(arc2, now=T0 + 6, arcs_dir=arcs, run_oracle=False)
        assert out2["verdict"] == "unverifiable"
        assert "nothing was machine-checkable" in out2["findings"][0]
    finally:
        tv.check_continuity = monkey


def test_KNOWN_LIMITATION_parroting_passes_continuity_needs_the_oracle(
        arcs: Path, locks: Path, tmp_path: Path):
    """Documented weakness, observed live on arc-1ed520f47e14: a taker that
    restates the goal scores perfect lexical overlap. Continuity alone cannot
    tell 'did the work' from 'said the words' — only the oracle can, which is
    why an arc with no oracle_cmd cannot earn a strong faithful."""
    arc = _handed_off_arc(arcs, locks)
    _take(arc, arcs, locks)
    soc.note(arc, GOAL + " / " + NEXT, agent="b@two", now=T0 + 4,
             evidence=["nothing-real"], arcs_dir=arcs)      # pure parroting
    lexical_only = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    assert lexical_only["verdict"] == "faithful"            # the limitation
    cont = next(c for c in lexical_only["checks"] if c["name"] == "continuity")
    assert cont["overlap_with_next_step"] >= 0.9
    assert lexical_only["n_checks_ran"] == 1                # thin evidence, shown

    # the same parroting against an arc whose oracle actually runs and fails:
    arc2 = soc.open_arc(GOAL, agent="a@one", now=T0, oracle_cmd="exit 1",
                        arcs_dir=arcs)["arc_id"]
    soc.claim(arc2, agent="a@one", now=T0, ttl=600, arcs_dir=arcs,
              locks_dir=locks)
    soc.offer_handoff(arc2, agent="a@one", now=T0 + 1, next_step=NEXT,
                      arcs_dir=arcs)
    _take(arc2, arcs, locks, now=T0 + 2)
    soc.note(arc2, GOAL + " / " + NEXT, agent="b@two", now=T0 + 3,
             evidence=["nothing-real"], arcs_dir=arcs)
    with_oracle = tv.verify(arc2, now=T0 + 4, arcs_dir=arcs, cwd=tmp_path,
                            oracle_timeout=30)
    assert with_oracle["verdict"] == "drifted"


def test_verdict_records_into_the_arc_after_the_fact(arcs: Path, locks: Path):
    """INV-6: the verdict lands on the arc without ever having gated it."""
    arc = _handed_off_arc(arcs, locks)
    _take(arc, arcs, locks)
    soc.note(arc, "did something unrelated", agent="b@two", now=T0 + 4,
             evidence=["x"], arcs_dir=arcs)
    out = tv.verify(arc, now=T0 + 5, arcs_dir=arcs, run_oracle=False)
    rec = soc.record_verdict(arc, agent="verifier@myworld",
                             verdict=out["verdict"], now=T0 + 6,
                             findings=out["findings"], arcs_dir=arcs)
    assert rec["ok"]
    pack = soc.resume_pack(arc, now=T0 + 7, arcs_dir=arcs)
    assert pack["open_verdicts"][0]["verdict"] == "drifted"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
