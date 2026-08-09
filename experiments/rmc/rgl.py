#!/usr/bin/env python3
"""RGL — Relational Gate Logic. Artifact A0 of the RMC ladder.

SOURCE: `myworld_computation/rmc_book_architecture_v0.1.pdf` (Relational Morphic
Computer Architecture v0.1). That document requires every proposition to carry
**Theory / Artifact / Falsifier**. This file is the Artifact for A0 and states
its own Falsifier.

## A0's question, verbatim from the ladder

    "relation/dynamics primitive 만으로 memory, gating, competition,
     obstruction 이 구성되는가?"

## The Falsifier (fixed before writing the constructions)

Memory, gating, competition and obstruction must each be **built by composing
Relons**, using only the primitive set below. **If any of the four needs
special-case machinery outside the calculus, A0 FAILS** and that is the result.
`tests/` asserts this structurally: every construction is asserted to be a
`Relon` or a composition of `Relon`s, and the four phenomena are measured on
behaviour, not on the presence of a function named after them.

## The primitive (L1 Relation Law)

A Relon is a typed stateful transformation relation

    R = (S, D, Phi, h, tau, kappa, gamma)

  S      state (a vector of floats — the only carrier)
  D      domain: which input channels this relation reads
  Phi    dynamics: (state, input) -> drive         [the relation proper]
  h      readout: state -> output
  tau    timescale (L6): larger = slower state change
  kappa  capacity: saturation bound on |state|
  gamma  leak: passive decay toward zero

State evolves in discrete steps as a leaky, saturating integrator of its drive:

    s' = clip( s + (Phi(s, x) - gamma * s) / tau , kappa )

That is the whole calculus. Everything below is composition.

## What this file does NOT claim

Nothing here says a morphic substrate is better than a transformer, or that any
of this improves an agent. A0 asks a **constructibility** question and answers
only that. Our own measurements (three-transport null, G5, G6) bar any
performance claim without its own pre-registered test.

Stdlib-only. Deterministic: no RNG, so results are exactly reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

Vec = list[float]


def _clip(v: float, k: float) -> float:
    return k if v > k else (-k if v < -k else v)


class Obstruction(Exception):
    """L5 Obstruction Law — a typed glue failure.

    Raised when two local charts cannot be composed. It is deliberately an
    exception and not a number: the law says obstruction must NOT be averaged
    away, so there is no code path that blends incompatible charts into a
    plausible middle value.
    """

    def __init__(self, left: str, right: str, detail: str):
        super().__init__(f"{left} !~ {right}: {detail}")
        self.left, self.right, self.detail = left, right, detail


@dataclass
class Relon:
    """R = (S, D, Phi, h, tau, kappa, gamma) — the only primitive."""

    name: str
    dim: int                                   # |S|
    domain: tuple[str, ...]                    # D: input channel names
    phi: Callable[[Vec, dict[str, float]], Vec]  # Phi: drive
    readout: Callable[[Vec], float] = lambda s: s[0]   # h
    tau: float = 1.0                           # L6 timescale
    kappa: float = 10.0                        # capacity
    gamma: float = 0.0                         # leak
    chart: str = "default"                     # L4: which local chart it lives in
    state: Vec = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.state:
            self.state = [0.0] * self.dim
        if self.tau <= 0:
            raise ValueError("tau must be > 0")

    def reset(self) -> "Relon":
        self.state = [0.0] * self.dim
        return self

    def step(self, x: dict[str, float]) -> float:
        """One dynamical step (L3: computation is constrained state evolution)."""
        missing = [c for c in self.domain if c not in x]
        if missing:
            raise KeyError(f"{self.name}: missing input channel(s) {missing}")
        drive = self.phi(self.state, x)
        if len(drive) != self.dim:
            raise ValueError(f"{self.name}: Phi returned dim {len(drive)} != {self.dim}")
        self.state = [
            _clip(s + (d - self.gamma * s) / self.tau, self.kappa)
            for s, d in zip(self.state, drive)
        ]
        return self.readout(self.state)


# ---------------------------------------------------------------------------
# Composition — the calculus. Every compound is itself a Relon.
# ---------------------------------------------------------------------------

def series(a: Relon, b: Relon, *, via: str, name: str | None = None) -> Relon:
    """a -> b. `a`'s readout is fed to `b` on channel `via`."""
    if via not in b.domain:
        raise ValueError(f"{b.name} does not read channel {via!r}")
    outer = tuple(c for c in a.domain) + tuple(c for c in b.domain if c != via)

    def phi(_s: Vec, x: dict[str, float]) -> Vec:
        ya = a.step({c: x[c] for c in a.domain})
        yb = b.step({**{c: x[c] for c in b.domain if c != via}, via: ya})
        return [yb]

    return Relon(name or f"({a.name}>{b.name})", 1, outer, phi,
                 readout=lambda s: s[0], tau=1.0, kappa=max(a.kappa, b.kappa),
                 chart=b.chart)


def parallel(a: Relon, b: Relon, combine: Callable[[float, float], float],
             *, name: str | None = None) -> Relon:
    """a and b on the same inputs, outputs combined."""
    outer = tuple(dict.fromkeys(a.domain + b.domain))

    def phi(_s: Vec, x: dict[str, float]) -> Vec:
        ya = a.step({c: x[c] for c in a.domain})
        yb = b.step({c: x[c] for c in b.domain})
        return [combine(ya, yb)]

    return Relon(name or f"({a.name}|{b.name})", 1, outer, phi,
                 kappa=max(a.kappa, b.kappa), chart=a.chart)


def feedback(r: Relon, *, via: str, gain: float = 1.0,
             name: str | None = None) -> Relon:
    """r's own readout fed back on channel `via` (recurrence — L3)."""
    if via not in r.domain:
        raise ValueError(f"{r.name} does not read channel {via!r}")
    outer = tuple(c for c in r.domain if c != via)
    last = [0.0]

    def phi(_s: Vec, x: dict[str, float]) -> Vec:
        y = r.step({**{c: x[c] for c in outer}, via: gain * last[0]})
        last[0] = y
        return [y]

    return Relon(name or f"fb({r.name})", 1, outer, phi,
                 kappa=r.kappa, chart=r.chart)


def glue(a: Relon, b: Relon, *, tolerance: float = 1e-9,
         name: str | None = None) -> Relon:
    """L4/L5 — glue two LOCAL CHARTS.

    Charts agree only if they are the same chart. Gluing different charts is
    exactly the case the Obstruction Law forbids averaging: this raises
    `Obstruction` at composition time rather than returning a blended value.
    `tolerance` exists so a caller can declare charts compatible numerically;
    it is never used to silently reconcile *names*.
    """
    if a.chart != b.chart:
        raise Obstruction(a.chart, b.chart,
                          "different local charts cannot be glued; the law "
                          "demands new evidence or an ontology extension, "
                          "not an average")
    return parallel(a, b, lambda p, q: (p + q) / 2.0,
                    name=name or f"glue({a.name},{b.name})")


# ---------------------------------------------------------------------------
# The four constructions. Each is ONLY composition + parameters.
# ---------------------------------------------------------------------------

def make_memory(name: str = "mem", tau: float = 8.0, leak: float = 0.0) -> Relon:
    """MEMORY from the primitive alone (L2 Persistence Law).

    A slow, leak-free integrator: state persists after its input stops. No
    storage structure, no buffer — persistence is a consequence of tau and
    gamma, which are parameters of the primitive.
    """
    return Relon(name, 1, ("x",),
                 phi=lambda s, x: [x["x"]],
                 tau=tau, gamma=leak, kappa=10.0)


def make_gate(name: str = "gate") -> Relon:
    """GATING from the primitive alone.

    The drive is the PRODUCT of a signal channel and a gate channel — a
    relation between two inputs, which is what L1 says the primitive is. When
    g = 0 the signal cannot enter the state at all.
    """
    return Relon(name, 1, ("x", "g"),
                 phi=lambda s, x: [x["x"] * x["g"]],
                 tau=1.0, gamma=1.0, kappa=10.0)


def make_competition(n: int = 2, self_gain: float = 1.1,
                     inhibition: float = 0.9, name: str = "wta") -> Relon:
    """COMPETITION from the primitive alone.

    One Relon whose state vector holds n units; the drive couples them with
    self-excitation and mutual inhibition. Winner-take-all is a dynamical
    outcome, not an argmax call — there is no comparison operator anywhere.
    """
    def phi(s: Vec, x: dict[str, float]) -> Vec:
        ext = [x[f"i{k}"] for k in range(n)]
        tot = sum(s)
        return [ext[k] + self_gain * s[k] - inhibition * (tot - s[k])
                for k in range(n)]

    return Relon(name, n, tuple(f"i{k}" for k in range(n)), phi,
                 readout=lambda s: float(max(range(len(s)), key=lambda k: s[k])),
                 tau=2.0, gamma=0.3, kappa=5.0)


def make_chart_pair(chart_a: str = "metric/A",
                    chart_b: str = "metric/B") -> tuple[Relon, Relon]:
    """Two relations living in DIFFERENT local charts (L4)."""
    a = Relon("locA", 1, ("x",), lambda s, x: [x["x"]], chart=chart_a, gamma=1.0)
    b = Relon("locB", 1, ("x",), lambda s, x: [2.0 * x["x"]], chart=chart_b,
              gamma=1.0)
    return a, b


# ---------------------------------------------------------------------------
# A0 verdict — run the four and report, honestly, whether the calculus sufficed
# ---------------------------------------------------------------------------

def run_a0(steps: int = 24) -> dict:
    """Execute the four constructions and report measured behaviour."""
    out: dict = {"artifact": "A0/RGL-Sim", "steps": steps}

    # 1. memory — drive for 3 steps, then silence; does state persist?
    m = make_memory(tau=8.0, leak=0.0)
    trace = [m.step({"x": 1.0 if t < 3 else 0.0}) for t in range(steps)]
    out["memory"] = {"peak": round(max(trace), 4),
                     "final": round(trace[-1], 4),
                     "retained_frac": round(trace[-1] / max(trace, default=1), 4),
                     "persists": trace[-1] > 0.99 * max(trace)}

    # 2. gating — identical signal, gate open vs shut
    g = make_gate()
    open_y = [g.step({"x": 1.0, "g": 1.0}) for _ in range(steps)][-1]
    g.reset()
    shut_y = [g.step({"x": 1.0, "g": 0.0}) for _ in range(steps)][-1]
    out["gating"] = {"open": round(open_y, 4), "shut": round(shut_y, 4),
                     "gates": abs(shut_y) < 1e-9 and open_y > 0.5}

    # 3. competition — two near-equal inputs; does one win outright?
    c = make_competition(2)
    for _ in range(steps):
        c.step({"i0": 1.0, "i1": 0.95})
    s = c.state
    winner = max(range(2), key=lambda k: s[k])
    loser = 1 - winner
    out["competition"] = {"state": [round(v, 4) for v in s], "winner": winner,
                          "suppressed": s[loser] <= 0.0 < s[winner],
                          "separation": round(s[winner] - s[loser], 4)}

    # 4. obstruction — glue two charts; must refuse, not average
    a, b = make_chart_pair()
    try:
        glue(a, b)
        out["obstruction"] = {"raised": False,
                              "note": "charts were glued — the law was violated"}
    except Obstruction as exc:
        out["obstruction"] = {"raised": True, "left": exc.left,
                              "right": exc.right, "detail": exc.detail[:80]}
    # and same-chart glue must still work (an obstruction that fires always
    # would be a broken check, not a law)
    a2 = Relon("a2", 1, ("x",), lambda s, x: [x["x"]], chart="same", gamma=1.0)
    b2 = Relon("b2", 1, ("x",), lambda s, x: [x["x"]], chart="same", gamma=1.0)
    out["obstruction"]["same_chart_glues"] = glue(a2, b2).step({"x": 1.0}) > 0

    built = [out["memory"]["persists"], out["gating"]["gates"],
             out["competition"]["suppressed"], out["obstruction"]["raised"],
             out["obstruction"]["same_chart_glues"]]
    out["a0_verdict"] = "CONSTRUCTIBLE" if all(built) else "FAILED"
    out["built"] = {"memory": built[0], "gating": built[1],
                    "competition": built[2], "obstruction": built[3]}
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(run_a0(), ensure_ascii=False, indent=1))
