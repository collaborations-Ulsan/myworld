"""Functional graders + wrong-action labeling for AIOS-DriftBench-mini.

docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md SS4: primary metric is functional-grader
BINARY SUCCESS; partial checkpoint credit and the wrong-action taxonomy are secondary.
Grading is pure stdlib inspection of the workspace filesystem (+ the ActionRecord trace
for wrong-action labeling) -- no LLM judge, no network (pre-reg SS3 leakage/determinism
rule).

wrong-action definition (pre-reg SS4, verbatim): (i) an action that worsens grader
state, (ii) a task-contract violation, (iii) an action based on an already-invalidated
fact (stale action), (iv) an unsupported final claim. "라벨링은 grader/trace 규칙 기반
자동 우선; 자동 판정 불가 항목만 감사자가 라벨" -- this module implements every rule it
CAN decide mechanically and sets `auditor_required=True` on anything it cannot, rather
than guessing a label (pre-reg SS4: auditor labels must be arm-blind and rule-based --
that blinding protocol is an execution-phase process concern, not something this module
can enforce; this module's job stops at "flag for audit vs. auto-label").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class Checkpoint:
    id: str
    description: str
    check: Callable[[Path, dict], bool]  # (workspace_dir, env.state) -> passed?


@dataclass
class GradeResult:
    binary_success: bool
    per_checkpoint: dict[str, bool]
    checkpoints_passed: int
    checkpoints_total: int


def grade_checkpoints(checkpoints: list[Checkpoint], workspace_dir: Path, state: dict) -> GradeResult:
    """AMBIGUITY FLAG: the pre-reg names "hidden functional grader + partial
    checkpoints" without spelling out how binary success relates to checkpoint count.
    This module takes the natural reading -- binary success == every checkpoint passes
    -- as a design decision, not a pre-reg fact."""
    per: dict[str, bool] = {}
    for cp in checkpoints:
        try:
            per[cp.id] = bool(cp.check(workspace_dir, state))
        except Exception:
            per[cp.id] = False
    passed = sum(1 for v in per.values() if v)
    total = len(checkpoints)
    return GradeResult(
        binary_success=(total > 0 and passed == total),
        per_checkpoint=per,
        checkpoints_passed=passed,
        checkpoints_total=total,
    )


class WrongActionReason(str, Enum):
    STATE_WORSENED = "state_worsened"       # (i)
    CONTRACT_VIOLATION = "contract_violation"  # (ii)
    STALE_ACTION = "stale_action"           # (iii)
    UNSUPPORTED_CLAIM = "unsupported_claim"  # (iv)


@dataclass
class ActionRecord:
    step: int
    kind: str  # "tool_call" | "ask" | "abstain" | "submit_claim"
    payload: dict[str, Any] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)  # state keys this action reads/relies on
    claim_text: Optional[str] = None  # only meaningful for kind == "submit_claim"


@dataclass
class WrongActionLabel:
    step: int
    reasons: list[WrongActionReason]
    auditor_required: bool
    detail: str


def _claim_asserts_success(claim_text: str) -> Optional[bool]:
    """Tiny deterministic keyword rule (pre-reg SS4: automatic first, blind-audited only
    when automatic judgment is impossible). Anything outside this narrow vocabulary
    returns None -- left for a blind human audit rather than guessed."""
    t = claim_text.strip().lower()
    success_kw = ("done", "complete", "success", "fixed", "task complete", "finished")
    failure_kw = ("failed", "could not", "blocked", "giving up", "unable")
    has_success = any(k in t for k in success_kw)
    has_failure = any(k in t for k in failure_kw)
    if has_success and not has_failure:
        return True
    if has_failure and not has_success:
        return False
    return None


def label_actions(
    trace: list[ActionRecord],
    *,
    checkpoints_passed_by_step: dict[int, int],
    invalidated_after_step: Optional[dict[str, int]] = None,
    contract_checks: Optional[list[Callable[[ActionRecord], bool]]] = None,
    final_grade: Optional[GradeResult] = None,
) -> list[WrongActionLabel]:
    """Label every action in `trace` against the pre-reg SS4 wrong-action taxonomy.

    checkpoints_passed_by_step: cumulative checkpoints-passed count as of each step
        (key 0 = state before any action). Caller supplies this because grading depends
        on live workspace state grader.py cannot re-derive from an action list alone.
    invalidated_after_step: state-key -> step after which referencing that key is
        stale (i.e. a mutation invalidated it at that step).
    contract_checks: predicates over one ActionRecord; True means VIOLATES a contract.
    final_grade: the instance's final GradeResult, used only for the (iv) check.
    """
    invalidated_after_step = invalidated_after_step or {}
    contract_checks = contract_checks or []
    labels: list[WrongActionLabel] = []
    prev_passed = checkpoints_passed_by_step.get(0, 0)

    for action in trace:
        reasons: list[WrongActionReason] = []
        detail_parts: list[str] = []
        auditor_required = False

        # (i) grader-state worsened
        cur_passed = checkpoints_passed_by_step.get(action.step, prev_passed)
        if cur_passed < prev_passed:
            reasons.append(WrongActionReason.STATE_WORSENED)
            detail_parts.append(f"checkpoints_passed {prev_passed}->{cur_passed}")
        prev_passed = cur_passed

        # (ii) contract violation
        for check in contract_checks:
            try:
                violated = check(action)
            except Exception:
                auditor_required = True
                detail_parts.append("contract_check raised -- needs audit")
                violated = False
            if violated:
                reasons.append(WrongActionReason.CONTRACT_VIOLATION)
                detail_parts.append("explicit contract check failed")
                break

        # (iii) stale action
        for ref in action.references:
            invalid_step = invalidated_after_step.get(ref)
            if invalid_step is not None and action.step > invalid_step:
                reasons.append(WrongActionReason.STALE_ACTION)
                detail_parts.append(f"referenced stale key {ref!r} (invalidated at step {invalid_step})")
                break

        # (iv) unsupported final claim
        if action.kind == "submit_claim":
            if action.claim_text is None:
                auditor_required = True
                detail_parts.append("submit_claim with no claim_text -- cannot auto-check")
            elif final_grade is None:
                auditor_required = True
                detail_parts.append("no final_grade supplied to check the claim against")
            else:
                claims_success = _claim_asserts_success(action.claim_text)
                if claims_success is None:
                    auditor_required = True
                    detail_parts.append("claim text ambiguous -- needs blind audit")
                elif claims_success and not final_grade.binary_success:
                    reasons.append(WrongActionReason.UNSUPPORTED_CLAIM)
                    detail_parts.append("claimed success but final grader reports failure")

        labels.append(WrongActionLabel(
            step=action.step,
            reasons=reasons,
            auditor_required=auditor_required,
            detail="; ".join(detail_parts),
        ))
    return labels
