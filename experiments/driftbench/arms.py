"""Arm interfaces for AIOS-DriftBench-mini (M2 keystone harness skeleton).

docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md SS2/SS3/SS3a: defines the 5 (+1 optional
ceiling) arms, the frozen budget caps, and the H3 memory-arm policy. This module defines
INTERFACES ONLY -- no model is called anywhere here. `run_arm(...)` raises
NotImplementedError; wiring a real agent loop (an actual local/frontier model driving a
tasks.Environment, recording a grader.ActionRecord trace, calling env.grader()) is
explicitly out of scope for this skeleton and belongs to the execution-phase build that
runs AFTER the freeze procedure in pre-reg SS6.

Deliberately decoupled from tasks.py (no import of tasks.Environment) so this module's
interface can be reasoned about and tested on its own; a real ArmRunner implementation
wires the two together.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from grader import ActionRecord, GradeResult

# ---------------------------------------------------------------------------
# Frozen budget caps (pre-reg SS3, "동결" -- frozen before any run)
# ---------------------------------------------------------------------------
WALL_SECONDS_CAP = 45 * 60
ACTIONS_CAP = 200
RESTART_IS_FAILURE = True  # crash/timeout/restart -> primary failure for that instance, no retry
MODEL_CALLS_COUNT_TOWARD_BUDGET = True  # every runtime model call (incl. gate calls) costs an action


@dataclass(frozen=True)
class BudgetCaps:
    wall_seconds: int = WALL_SECONDS_CAP
    max_actions: int = ACTIONS_CAP
    restart_is_failure: bool = RESTART_IS_FAILURE
    model_calls_count_toward_budget: bool = MODEL_CALLS_COUNT_TOWARD_BUDGET


FROZEN_BUDGET = BudgetCaps()


# ---------------------------------------------------------------------------
# weak+checklist ceremony text (pre-reg SS2: "generic 거버넌스 체크리스트 텍스트만")
# ---------------------------------------------------------------------------
# Deliberately generic hygiene ceremony -- no drift-detection MACHINERY behind it. That
# gap (text vs runtime) is exactly the ablation this arm exists to isolate
# (masterplan SS5 point 2: "weak+checklist 대조군 필수 -- runtime과 ceremony를 분리").
CHECKLIST_TEXT = """\
Before every action, and again before declaring the task complete:
1. Re-read the current state of every file you are about to touch -- do not act on a
   memory of what a file contained earlier in this session.
2. Re-confirm your plan still matches the stated goal; if something upstream may have
   changed since you last checked, verify it directly instead of assuming it hasn't.
3. Note any interface, config, schema, credential, or version you are depending on, and
   confirm it is still what you believe it is before relying on it.
4. Test the effect of each change before moving on, rather than chaining unverified
   edits on top of each other.
5. Before your final answer, state the concrete evidence that supports it. If you
   cannot point to verified evidence, say so explicitly instead of guessing.
6. If the task is ambiguous, ask a clarifying question rather than guessing silently.
"""


# ---------------------------------------------------------------------------
# Arm specs (pre-reg SS2 table)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ArmSpec:
    name: str
    model_class: str  # "frontier" | "weak-local"
    scaffold: str  # human-readable scaffold description (pre-reg SS2 col 3)
    uses_checklist: bool = False
    memory_policy: Optional[str] = None  # None | "naive" | "gated"
    uses_epistemic_gate: bool = False
    optional: bool = False  # pre-reg SS2: strong+AIOS is a ceiling check, not required


ARMS: dict[str, ArmSpec] = {
    "strong-raw": ArmSpec(
        name="strong-raw", model_class="frontier",
        scaffold="competent generic plan/verify prompt, no AIOS",
    ),
    "weak-raw": ArmSpec(
        name="weak-raw", model_class="weak-local",
        scaffold="same tool access, no scaffold",
    ),
    "weak+checklist": ArmSpec(
        name="weak+checklist", model_class="weak-local",
        scaffold="generic governance checklist text only (ceremony control)",
        uses_checklist=True,
    ),
    "weak+memory": ArmSpec(
        name="weak+memory", model_class="weak-local",
        scaffold="ReasoningBank/AWM-style lesson storage+injection, no staleness detection",
        memory_policy="naive",
    ),
    "weak+AIOS": ArmSpec(
        name="weak+AIOS", model_class="weak-local",
        scaffold="epistemic gate (M1) + drift detection + recovery policy + provenance, "
                  "action-touching only",
        memory_policy="gated",
        uses_epistemic_gate=True,
    ),
    "strong+AIOS": ArmSpec(
        name="strong+AIOS", model_class="frontier",
        scaffold="ceiling check only -- not required for WIN/STOP (pre-reg SS2)",
        memory_policy="gated",
        uses_epistemic_gate=True,
        optional=True,
    ),
}

REQUIRED_ARMS = tuple(name for name, spec in ARMS.items() if not spec.optional)  # the 5 confirmatory arms


# ---------------------------------------------------------------------------
# H3 memory-arm policy hooks (pre-reg SS3a, "동결")
# ---------------------------------------------------------------------------
@dataclass
class MemoryRecord:
    template: str
    seed: int
    lesson: str  # model-generated, <=500 chars (pre-reg SS3a)
    step_stored: int

    def __post_init__(self) -> None:
        if len(self.lesson) > 500:
            raise ValueError("lesson exceeds the pre-reg SS3a 500-char cap")


@dataclass
class MemoryInjectResult:
    lesson: Optional[str]
    suppressed: bool
    reason: str


class MemoryPolicy(Protocol):
    """store() fires once at instance end; inject() fires once at the start of the NEXT
    instance of the SAME TEMPLATE family (cross-seed transfer allowed, cross-template
    forbidden -- pre-reg SS3a)."""

    def store(self, template: str, seed: int, lesson: str, step_stored: int) -> MemoryRecord: ...

    def inject(self, template: str, seed: int, context: dict) -> MemoryInjectResult: ...


@dataclass
class NaiveMemoryPolicy:
    """weak+memory: always injects the latest lesson for the template family, with NO
    staleness check (pre-reg SS3a) -- this is the ProEvolve-reproduction arm."""

    _by_template: dict[str, MemoryRecord] = field(default_factory=dict)

    def store(self, template: str, seed: int, lesson: str, step_stored: int) -> MemoryRecord:
        rec = MemoryRecord(template=template, seed=seed, lesson=lesson, step_stored=step_stored)
        self._by_template[template] = rec
        return rec

    def inject(self, template: str, seed: int, context: dict) -> MemoryInjectResult:
        rec = self._by_template.get(template)
        if rec is None:
            return MemoryInjectResult(lesson=None, suppressed=False, reason="no_prior_lesson")
        return MemoryInjectResult(lesson=rec.lesson, suppressed=False, reason="always_inject")


StalenessCheck = Callable[["MemoryRecord", dict], tuple]


def _default_staleness_check(record: "MemoryRecord", context: dict) -> tuple:
    """STUB staleness check -- NOT the real pre-reg SS3a mechanism.

    Real wiring (deferred to the execution-phase build, out of scope for this skeleton):
    pass the stored lesson through DriftBench-style contract validation + the shipped
    H0 poison guard (scripts/aios_akashic_guard.py) + memoryOS draft-review before
    injection (pre-reg SS3a: "DriftBench식 contract 검증 + H0 가드 + draft-review"). This
    stub only checks a caller-supplied `context["mutation_count_since_store"]` counter,
    so the interface's suppression/tagging contract is exercisable and testable now
    without the real runtime existing yet.
    """
    mutations_since = context.get("mutation_count_since_store", 0)
    if mutations_since > 0:
        return True, f"{mutations_since} mutation(s) observed since lesson was stored"
    return False, "no mutation observed since lesson was stored"


@dataclass
class GatedMemoryPolicy:
    """weak+AIOS: same storage as NaiveMemoryPolicy, but inject() runs a staleness check
    first and SUPPRESSES + TAGS (never silently drops -- DNA #3 append-only/draft-first)
    a stale lesson instead of injecting it (pre-reg SS3a)."""

    staleness_check: StalenessCheck = _default_staleness_check
    _by_template: dict[str, MemoryRecord] = field(default_factory=dict)

    def store(self, template: str, seed: int, lesson: str, step_stored: int) -> MemoryRecord:
        rec = MemoryRecord(template=template, seed=seed, lesson=lesson, step_stored=step_stored)
        self._by_template[template] = rec
        return rec

    def inject(self, template: str, seed: int, context: dict) -> MemoryInjectResult:
        rec = self._by_template.get(template)
        if rec is None:
            return MemoryInjectResult(lesson=None, suppressed=False, reason="no_prior_lesson")
        is_stale, reason = self.staleness_check(rec, context)
        if is_stale:
            return MemoryInjectResult(lesson=None, suppressed=True, reason=f"stale: {reason}")
        return MemoryInjectResult(lesson=rec.lesson, suppressed=False, reason=f"fresh: {reason}")


def build_memory_policy(policy_name: Optional[str]) -> Optional[MemoryPolicy]:
    if policy_name is None:
        return None
    if policy_name == "naive":
        return NaiveMemoryPolicy()
    if policy_name == "gated":
        return GatedMemoryPolicy()
    raise ValueError(f"unknown memory policy {policy_name!r}")


# ---------------------------------------------------------------------------
# Arm-runner interface (NOT implemented -- execution-phase work)
# ---------------------------------------------------------------------------
@dataclass
class ArmRunResult:
    trace: list[ActionRecord]
    final_grade: Optional[GradeResult]
    actions_used: int
    wall_seconds: float
    tokens: int
    restarted: bool


class ArmRunner(Protocol):
    """The seam a real agent loop implements against a tasks.Environment. No
    implementation lives in this skeleton -- see module docstring."""

    def run(
        self, env: Any, *, budget: BudgetCaps, checklist: Optional[str],
        memory_policy: Optional[MemoryPolicy],
    ) -> ArmRunResult: ...


def run_arm(arm_name: str, env: Any, *, budget: BudgetCaps = FROZEN_BUDGET) -> ArmRunResult:
    """Not implemented in the skeleton (pre-reg SS6: the first run only happens after the
    freeze procedure is recorded in the Errata). Present so callers/tests can assert the
    interface shape without a real runtime existing yet."""
    if arm_name not in ARMS:
        raise ValueError(f"unknown arm {arm_name!r}; known: {sorted(ARMS)}")
    raise NotImplementedError(
        "run_arm is an interface stub -- wiring a real model loop is execution-phase "
        "work, out of scope for the M2 harness skeleton (see module docstring)."
    )
