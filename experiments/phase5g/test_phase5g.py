#!/usr/bin/env python3
"""G5 harness tests — the fairness guards are the point.

The easiest way to fake a society win is to give the control arm a worse
record. These tests assert that cannot happen, before any cell is run.

    /home/user/miniconda3/bin/python3 -m pytest -q experiments/phase5g/test_phase5g.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "phase5g"))
sys.path.insert(0, str(ROOT / "scripts"))

import aios_society as soc   # noqa: E402
import death                 # noqa: E402

T0 = 1_800_000_000.0
TASK = {"task_id": "p5-001-8ae428b3", "script_path": "scripts/x.py",
        "test_paths": ["tests/test_x.py"]}


@pytest.fixture()
def arcs(tmp_path: Path) -> Path:
    return tmp_path / "arcs"


@pytest.fixture()
def locks(tmp_path: Path) -> Path:
    return tmp_path / "locks"


def _worked_arc(arcs: Path, locks: Path, *, superseded=False) -> str:
    arc = soc.open_arc("make the tests in tests/test_x.py pass by editing "
                       "scripts/x.py", agent="solo@agent", now=T0,
                       constraints=["forbid:tests/conftest"],
                       oracle_cmd="pytest -q tests/test_x.py",
                       arcs_dir=arcs)["arc_id"]
    soc.claim(arc, agent="solo@agent", now=T0, ttl=600, arcs_dir=arcs,
              locks_dir=locks)
    soc.note(arc, "reproduced the failure in the import path", agent="solo@agent",
             now=T0 + 1, evidence=["run:1"], arcs_dir=arcs)
    if superseded:
        r = soc.note(arc, "tried the regex approach", agent="solo@agent",
                     now=T0 + 2, evidence=["run:2"], arcs_dir=arcs)
        soc.supersede(arc, r["seq"], "regex cannot express the nesting",
                      agent="solo@agent", now=T0 + 3, arcs_dir=arcs)
    soc.offer_handoff(arc, agent="solo@agent", now=T0 + 4, reason="died",
                      next_step="fix the import", arcs_dir=arcs)
    return arc


# --- death injection: identical across arms, derived from the task ---------

def test_death_turn_is_deterministic_and_arm_independent():
    a = death.death_turn("p5-001-8ae428b3")
    for _ in range(5):
        assert death.death_turn("p5-001-8ae428b3") == a
    assert a in death.DEATH_TURNS
    # signature takes ONLY the task id — an arm cannot shift its own death
    import inspect
    assert list(inspect.signature(death.death_turn).parameters) == ["task_id",
                                                                    "choices"]


def test_death_turns_spread_across_the_task_pool():
    import json
    tasks = json.loads((ROOT / "experiments" / "phase5" /
                        "tasks.json").read_text())["tasks"]
    js = [death.death_turn(t["task_id"]) for t in tasks]
    assert set(js) <= set(death.DEATH_TURNS)
    assert len(set(js)) > 1, "all tasks died at the same turn — not a spread"


def test_post_death_budget_is_equal_for_every_arm():
    for tid in ("a", "b", "c"):
        j = death.death_turn(tid)
        budgets = {arm: death.post_death_budget(5, j) for arm in death.ARMS}
        assert len(set(budgets.values())) == 1, budgets


# --- guard 4: the control arm's record is NOT degraded --------------------

def test_solo_ledger_and_society_get_structurally_identical_packs(arcs: Path,
                                                                  locks: Path):
    """Prereg guard 4 — the single most important fairness assertion."""
    arc = _worked_arc(arcs, locks)
    b = death.recovery_context("solo_ledger", TASK, arc, now=T0 + 5,
                               arcs_dir=arcs)
    c = death.recovery_context("society", TASK, arc, now=T0 + 5, arcs_dir=arcs)
    d = death.recovery_context("society_rev", TASK, arc, now=T0 + 5,
                               arcs_dir=arcs)
    # same pack object from the same generator
    for k in ("goal", "constraints", "recent_progress", "tip_seq", "handoff"):
        assert b["pack"][k] == c["pack"][k] == d["pack"][k]
    # same information in the prompt: only the framing sentence differs
    strip = lambda s: "\n".join(s.split("\n")[1:])  # noqa: E731
    assert strip(b["text"]) == strip(c["text"]) == strip(d["text"])
    assert len(b["text"]) > 50


def test_pack_generator_cannot_see_the_arm(arcs: Path, locks: Path):
    """Structural guarantee, not a promise: build_pack takes no arm argument,
    so it is incapable of favouring one."""
    import inspect
    params = list(inspect.signature(death.build_pack).parameters)
    assert "arm" not in params and "society" not in " ".join(params)
    arc = _worked_arc(arcs, locks)
    p1 = death.build_pack(arc, now=T0 + 5, arcs_dir=arcs)
    p2 = death.build_pack(arc, now=T0 + 5, arcs_dir=arcs)
    assert p1["tip_seq"] == p2["tip_seq"] and p1["goal"] == p2["goal"]


def test_norecord_arm_carries_nothing(arcs: Path, locks: Path):
    arc = _worked_arc(arcs, locks)
    a = death.recovery_context("solo_norecord", TASK, arc, now=T0 + 5,
                               arcs_dir=arcs)
    assert a["text"] == "" and a["pack"] is None


# --- the treatment is exactly "a different agent" -------------------------

def test_only_society_arms_change_hands(arcs: Path, locks: Path):
    arc = _worked_arc(arcs, locks)
    takers = {arm: death.recovery_context(arm, TASK, arc, now=T0 + 5,
                                          arcs_dir=arcs)["taker"]
              for arm in death.ARMS}
    assert takers["solo_norecord"] == takers["solo_ledger"] == "solo@agent"
    assert takers["society"] == takers["society_rev"] == "peer@agent"
    assert death.arm_is_society("society") and not death.arm_is_society("solo_ledger")


def test_only_society_rev_may_supersede(arcs: Path, locks: Path):
    arc = _worked_arc(arcs, locks)
    flags = {arm: death.recovery_context(arm, TASK, arc, now=T0 + 5,
                                         arcs_dir=arcs)["may_supersede"]
             for arm in death.ARMS}
    assert flags == {"solo_norecord": False, "solo_ledger": False,
                     "society": False, "society_rev": True}


def test_retracted_steps_are_shown_as_retracted_not_as_fact(arcs: Path,
                                                            locks: Path):
    arc = _worked_arc(arcs, locks, superseded=True)
    ctx = death.recovery_context("society_rev", TASK, arc, now=T0 + 5,
                                 arcs_dir=arcs)
    assert "RETRACTED" in ctx["text"]
    assert "regex cannot express the nesting" in ctx["text"]
    body = ctx["text"].split("RETRACTED")[0]
    assert "tried the regex approach" not in body   # not inherited as current


# --- run-validity gate (prereg §5.5) --------------------------------------

def test_void_when_no_ownership_ever_changed_hands():
    inert = [{"kind": "attempt", "arm": a, "task_id": "t1",
              "ownership_transferred": False} for a in death.ARMS]
    v = death.validity(inert)
    assert v["passed"] is False and "VOID" in v["detail"]


def test_gate_passes_when_a_society_arm_transferred():
    recs = [{"kind": "attempt", "arm": "solo_ledger", "task_id": "t1",
             "ownership_transferred": False},
            {"kind": "attempt", "arm": "society", "task_id": "t1",
             "ownership_transferred": True}]
    v = death.validity(recs)
    assert v["passed"] is True and v["society_transfers"] == 1


def test_missing_arc_degrades_honestly(arcs: Path):
    ctx = death.recovery_context("society", TASK, "arc-nope", now=T0,
                                 arcs_dir=arcs)
    assert ctx["pack"] is None and "error" in ctx


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
