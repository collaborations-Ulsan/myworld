#!/usr/bin/env python3
"""A0 tests — enforce the Falsifier, then probe where the calculus breaks.

The Falsifier (fixed in rgl.py before the constructions were written): memory,
gating, competition and obstruction must each be built by COMPOSING Relons
using only the primitive set. If any needs special-case machinery outside the
calculus, A0 fails.

These tests do two jobs:
  1. assert the constructions really are Relons driven by their dynamics, not
     Python shortcuts wearing the right names;
  2. push each construction until it breaks, and record the break honestly —
     an artifact whose limits are unknown is not an artifact.

    /home/user/miniconda3/bin/python3 -m pytest -q experiments/rmc/test_rgl.py
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rgl import (Obstruction, Relon, feedback, glue, make_chart_pair,  # noqa: E402
                 make_competition, make_gate, make_memory, parallel, run_a0,
                 series)


# --- the Falsifier, structurally -----------------------------------------

@pytest.mark.parametrize("factory", [make_memory, make_gate, make_competition])
def test_every_construction_is_a_relon(factory):
    """Not a wrapper, not a helper class — the primitive itself."""
    assert isinstance(factory(), Relon)


def test_compositions_are_relons_too():
    """The calculus is closed: composing Relons yields a Relon."""
    a = make_memory("a")
    b = make_gate("b")
    assert isinstance(series(a, b, via="x"), Relon)
    assert isinstance(parallel(make_memory("p"), make_memory("q"),
                               lambda u, v: u + v), Relon)
    assert isinstance(feedback(make_gate("f"), via="g"), Relon)


def test_competition_dynamics_contain_no_comparison():
    """Winner-take-all must EMERGE from the drive.

    The dynamics function is read as source and asserted to contain no
    comparison, max/min, sort or conditional — if the winner were selected
    rather than grown, A0's claim would be false for competition.
    """
    src = inspect.getsource(make_competition)
    body = src.split("def phi(")[1].split("return Relon")[0]
    # drop the signature line: its return annotation contains '->', whose '>'
    # is not a comparison (this test's first version false-failed on exactly
    # that, which is why the check is now on the body only)
    body = body.split("\n", 1)[1]
    for banned in ("max(", "min(", "sort", "argmax", " if ", "==",
                   ">", "<"):
        assert banned not in body, f"competition drive uses {banned!r}"


def test_competition_readout_is_reporting_only():
    """Honest caveat: the READOUT uses max to name the winner. That is
    reporting, not mechanism — the separation must already exist in the state
    before any readout is called."""
    c = make_competition(2)
    for _ in range(24):
        c.step({"i0": 1.0, "i1": 0.95})
    assert c.state[0] > 0.0 > c.state[1], "separation must be in the STATE"
    assert c.state[0] - c.state[1] > 1.0


def test_obstruction_is_a_type_not_a_number():
    """L5: obstruction must not be averaged away. There must be no code path
    that returns a blended value for incompatible charts."""
    assert issubclass(Obstruction, Exception)
    a, b = make_chart_pair()
    with pytest.raises(Obstruction):
        glue(a, b)


def test_obstruction_does_not_fire_on_compatible_charts():
    """A check that always fails is not a law."""
    a = Relon("a", 1, ("x",), lambda s, x: [x["x"]], chart="same", gamma=1.0)
    b = Relon("b", 1, ("x",), lambda s, x: [x["x"]], chart="same", gamma=1.0)
    assert glue(a, b).step({"x": 2.0}) == pytest.approx(2.0)


def test_memory_persistence_comes_from_parameters_not_storage():
    """Persistence is tau/gamma, not a buffer: raising gamma must destroy it
    with no other change."""
    keep = make_memory(tau=8.0, leak=0.0)
    lossy = make_memory(tau=8.0, leak=0.5)
    for r in (keep, lossy):
        for t in range(24):
            r.step({"x": 1.0 if t < 3 else 0.0})
    # The claim is relative, not a magic threshold: leak must destroy most of
    # what leak-free retention keeps. (An earlier version asserted < 0.05 with
    # no derivation and failed at the correct value 0.091 —
    # 0.375 * (1 - 0.5/8)^21 ~= 0.097. Thresholds need a derivation or a ratio.)
    assert keep.state[0] > 0.3
    assert lossy.state[0] < 0.3 * keep.state[0]
    # and the mechanism is identical — same compiled dynamics, different gamma
    assert keep.phi.__code__.co_code == lossy.phi.__code__.co_code
    assert (keep.gamma, lossy.gamma) == (0.0, 0.5)


def test_a0_verdict_is_constructible():
    out = run_a0()
    assert out["a0_verdict"] == "CONSTRUCTIBLE"
    assert all(out["built"].values()), out["built"]


# --- where it breaks (recorded, not hidden) ------------------------------

def test_LIMIT_perfect_symmetry_deadlocks_competition():
    """Equal inputs produce no winner. Real competition needs symmetry
    breaking (noise, priors, or history) — the calculus does not supply it,
    and pretending otherwise would be the interesting failure to hide."""
    c = make_competition(2)
    for _ in range(50):
        c.step({"i0": 1.0, "i1": 1.0})
    assert c.state[0] == pytest.approx(c.state[1]), \
        "with identical inputs the states must stay tied — no hidden tiebreak"


def test_LIMIT_leak_free_memory_is_unphysical_and_saturates():
    """gamma=0 memory never forgets AND rides to capacity under sustained
    drive. Useful for A0's question, not a model of anything real: any use
    beyond A0 needs a decay policy."""
    m = make_memory(tau=2.0, leak=0.0)
    for _ in range(200):
        m.step({"x": 1.0})
    assert m.state[0] == pytest.approx(m.kappa), "saturates at capacity"


def test_LIMIT_series_composition_advances_both_clocks():
    """Known wart: `series` steps `a` and `b` once per outer step, so a
    two-stage chain runs both at the same rate. L6 says timescales differ; the
    calculus expresses that WITHIN a Relon (tau) but composition does not yet
    schedule stages independently. Recorded as A0's honest boundary."""
    a = make_memory("a", tau=1.0)
    b = make_gate("b")
    s = series(a, b, via="x")
    s.step({"x": 1.0, "g": 1.0})
    assert a.state[0] != 0.0 and b.state[0] != 0.0


def test_LIMIT_glue_tolerance_never_reconciles_names():
    """`tolerance` must not become a back door for averaging charts."""
    a, b = make_chart_pair()
    with pytest.raises(Obstruction):
        glue(a, b, tolerance=1e9)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
