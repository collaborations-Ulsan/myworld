"""Shared data contracts for the AGI certification-layer witness experiment.

EVERY module imports its types from HERE so parallel builds agree on interfaces.
Design: Fable 5 §2 (certificate signatures). Do not change field names without
updating all importers — these are the seams between independently-built modules.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---- Claims (the shared-ledger substrate) -----------------------------------
class ClaimKind(str, Enum):
    IO = "io"            # executable: input -> expected output
    PROPERTY = "property"  # e.g. return-type, sortedness, monotonicity
    ORDER = "order"      # relational/precedence claim (source of H1 cyclic frustration)


@dataclass
class Claim:
    task_id: str
    source_id: str            # which population agent / injected source authored it
    kind: ClaimKind
    payload: dict[str, Any]   # IO: {"input": [...], "output": ...}; PROPERTY/ORDER: kind-specific
    ts: int = 0               # logical insertion order (deterministic; no wall-clock)
    poisoned: bool = False    # ground-truth label for scoring ONLY — certificates must NOT read this


# ---- Sandboxed execution result ---------------------------------------------
@dataclass
class ExecResult:
    ok: bool                  # ran without error/timeout
    output: Any = None
    error: str | None = None
    timed_out: bool = False


# ---- Certificate outputs (Fable §2) -----------------------------------------
class ApexLabel(str, Enum):
    ANSWERABLE = "ANSWERABLE"
    UNDERDETERMINED = "UNDERDETERMINED"
    CONTRADICTORY = "CONTRADICTORY"


@dataclass
class ApexCert:
    label: ApexLabel
    conf: float
    support_set: list[int] = field(default_factory=list)      # indices of claims backing answerability
    coverage_gaps: list[dict] = field(default_factory=list)   # named uncovered constraints (steer IRIS)


@dataclass
class IrisCert:
    n_classes: int
    class_sizes: list[int]
    chosen_class: int                                          # index of selected behavioral class, -1 if none
    discriminating_inputs: list[Any] = field(default_factory=list)
    identified: bool = False                                   # exactly one class consistent with claims


@dataclass
class DescentCert:
    h0_conflicts: list[tuple[int, int]] = field(default_factory=list)  # pairs of directly-conflicting claim idx
    h1_cycles: list[list[int]] = field(default_factory=list)           # implicated cyclic-frustration claim idx
    hf: float = 0.0                                                     # Hodge harmonic fraction (0 = coherent)
    source_anomaly: dict[str, float] = field(default_factory=dict)     # source_id -> H0 guard poison_score


@dataclass
class GoenCert:
    score: float
    rewired_context: list[int]                                # claim indices to keep after rewiring
    expected_gain: float = 0.0


# ---- Per-task outcome (arms.py emits these; score.py consumes) ---------------
@dataclass
class TaskOutcome:
    task_id: str
    arm: str                  # "A" | "B" | "C" | "C-ablate-apex" ...
    seed: int
    submitted: bool           # False = abstained
    verified: bool            # passed hidden tests (only meaningful if submitted)
    tokens: int               # total LLM tokens spent on this task (prompt+completion, all calls)
    wall_s: float = 0.0
    poison_condition: str = ""  # "P0"|"P1"|"P2"
    note: str = ""
