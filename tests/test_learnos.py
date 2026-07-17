"""Deterministic tests for experiments/learnos/ (LearnOS v0 harness-improver,
docs/AIOS_AGI_CONCEPTION_2026-07-17.md §6). No live LLM anywhere in this
file -- a scripted fake proposer stands in for backend.complete().

Covers: held-out isolation (structural, not by comment), the promotion gate
rejecting visible-only fixes, contract_fuzz catching a real postcondition
violation, sentinel regression blocking promotion, ledger row shape +
replay_cmd, and summarize()'s fix-rate curve.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_LEARNOS_DIR = Path(__file__).resolve().parents[1] / "experiments" / "learnos"
sys.path.insert(0, str(_LEARNOS_DIR))

import improve  # noqa: E402
import ledger  # noqa: E402
import tasks  # noqa: E402
import verify  # noqa: E402


# ── scripted (no-LLM) proposer ───────────────────────────────────────────────
class ScriptedProposer:
    """Returns queued canned responses in order; never calls out to a network."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, prompt: str, **kwargs) -> str:
        self.calls += 1
        if not self._responses:
            return ""
        return self._responses.pop(0)


def _fence(source: str) -> str:
    return f"```python\n{source}```"


# ── held-out isolation (structural, not by comment) ──────────────────────────
def test_visible_view_has_no_held_out_key():
    for t in tasks.load_visible_tasks():
        assert "held_out_tests" not in t
        assert set(tasks.REQUIRED_VISIBLE_FIELDS) <= set(t.keys())
    # v0 shipped 18 tasks; S+1 (docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md) expanded the
    # set to 34 so the A(mine)/B(transfer-holdout)/sentinel split can each hold >=10
    # disjoint tasks -- see experiments/learnos/data/task_split.json.
    assert len(tasks.load_visible_tasks()) == 34


def test_improver_source_never_references_held_out_path():
    tasks_src = (_LEARNOS_DIR / "tasks.py").read_text(encoding="utf-8")
    improve_src = (_LEARNOS_DIR / "improve.py").read_text(encoding="utf-8")
    verify_src = (_LEARNOS_DIR / "verify.py").read_text(encoding="utf-8")

    # the improver code path (tasks.py + improve.py) must never name the
    # held-out data file or call the private loader -- structural, checked by
    # grepping actual source, not trusting a comment.
    for forbidden in ("tasks_held_out", "_load_held_out("):
        assert forbidden not in tasks_src, f"tasks.py references forbidden {forbidden!r}"
        assert forbidden not in improve_src, f"improve.py references forbidden {forbidden!r}"
        # sanity: the check itself is meaningful -- verify.py DOES use both.
        assert forbidden in verify_src, f"verify.py should be the sole reader of {forbidden!r}"


def test_verify_run_holdout_never_returns_test_source_or_error_detail():
    task = tasks.get_task("off_by_one_range")
    result = verify.run_holdout(task["task_id"], task["buggy_source"])
    blob = json.dumps(result)
    assert "sum_range(10)" not in blob and "55" not in blob
    assert set(result.keys()) == {"total", "passed", "all_passed", "timed_out", "error"}


# ── promotion gate: visible-only fix must be rejected ────────────────────────
def test_promotion_gate_rejects_visible_only_fix():
    task = tasks.get_task("off_by_one_range")
    baseline = improve.baseline_holdout_passed(task)
    # passes both visible asserts via special-casing, but does not generalize
    # to the held-out values (10 -> 55, 100 -> 5050) -- still the original bug.
    overfit_patch = (
        "def sum_range(n):\n"
        "    if n == 1:\n"
        "        return 1\n"
        "    if n == 3:\n"
        "        return 6\n"
        "    total = 0\n"
        "    for i in range(1, n):\n"
        "        total += i\n"
        "    return total\n"
    )
    candidate = improve.Candidate(
        kind="code_patch", content=overfit_patch, patch_source=overfit_patch, proposer_calls=1
    )
    result = improve.evaluate_candidate(task, candidate, baseline)
    assert result["visible_pass"] is True
    assert result["holdout_pass"] is False
    assert result["decision"] == "rejected"


def test_promotion_gate_promotes_a_real_fix():
    task = tasks.get_task("off_by_one_range")
    baseline = improve.baseline_holdout_passed(task)
    real_fix = (
        "def sum_range(n):\n"
        "    total = 0\n"
        "    for i in range(1, n + 1):\n"
        "        total += i\n"
        "    return total\n"
    )
    candidate = improve.Candidate(kind="code_patch", content=real_fix, patch_source=real_fix, proposer_calls=1)
    result = improve.evaluate_candidate(task, candidate, baseline)
    assert result["visible_pass"] is True
    assert result["holdout_pass"] is True
    assert result["sentinel_regressed"] is False
    assert result["decision"] == "promoted"


# ── sentinel regression blocks promotion even with a real held-out gain ─────
def test_sentinel_regression_blocks_promotion():
    task = tasks.get_task("incorrect_accumulator_init")  # product(xs); sentinel: product([]) == 1
    baseline = improve.baseline_holdout_passed(task)
    # correct on every non-empty case (visible + held-out) but special-cases
    # the empty list to 0, breaking the sentinel invariant product([]) == 1.
    patch = (
        "def product(xs):\n"
        "    if len(xs) == 0:\n"
        "        return 0\n"
        "    total = 1\n"
        "    for x in xs:\n"
        "        total *= x\n"
        "    return total\n"
    )
    candidate = improve.Candidate(kind="code_patch", content=patch, patch_source=patch, proposer_calls=1)
    result = improve.evaluate_candidate(task, candidate, baseline)
    assert result["visible_pass"] is True
    assert result["holdout_pass"] is True
    assert result["sentinel_regressed"] is True
    assert result["decision"] == "rejected"


# ── exploit scan blocks a candidate that references verifier internals ──────
def test_exploit_scan_blocks_held_out_reference():
    task = tasks.get_task("off_by_one_range")
    baseline = improve.baseline_holdout_passed(task)
    patch = (
        "# attempt: peek at held_out fixtures via subprocess\n"
        "def sum_range(n):\n"
        "    total = 0\n"
        "    for i in range(1, n + 1):\n"
        "        total += i\n"
        "    return total\n"
    )
    candidate = improve.Candidate(kind="code_patch", content=patch, patch_source=patch, proposer_calls=1)
    result = improve.evaluate_candidate(task, candidate, baseline)
    assert result["decision"] == "rejected"
    assert "exploit_scan_hit" in result["exploit_or_contract_audit"]


# ── contract_fuzz catches a real postcondition violation ─────────────────────
def test_contract_fuzz_catches_postcondition_violation():
    tool_source = "def abs_val(x):\n    return x\n"  # no-op, should be |x|
    result = verify.contract_fuzz(
        tool_source,
        "abs_val",
        [{"name": "x", "type": "int", "lo": -100, "hi": 100}],
        pre="True",
        post="result >= 0",
        seed=3,
        time_budget_s=5,
    )
    assert result["violated"] is True
    assert result["counterexample"]["x"] < 0


def test_contract_fuzz_passes_a_correct_tool():
    tool_source = "def abs_val(x):\n    return x if x >= 0 else -x\n"
    result = verify.contract_fuzz(
        tool_source,
        "abs_val",
        [{"name": "x", "type": "int", "lo": -100, "hi": 100}],
        pre="True",
        post="result >= 0",
        seed=3,
        time_budget_s=5,
    )
    assert result["violated"] is False
    assert result["trials"] > 0


def test_tool_candidate_rejected_when_contract_fuzz_finds_a_crash():
    task = tasks.get_task("wrong_condition_negation")  # is_even(n)
    baseline = improve.baseline_holdout_passed(task)
    tool_source = (
        "def reciprocal(x):\n"
        "    '''PRECONDITION: True\n"
        "    POSTCONDITION: True\n"
        "    '''\n"
        "    return 1 / x\n"
    )
    correct_patch = "def is_even(n):\n    return n % 2 == 0\n"
    candidate = improve.Candidate(
        kind="tool",
        content=tool_source,
        patch_source=tool_source + "\n" + correct_patch,
        proposer_calls=2,
    )
    result = improve.evaluate_candidate(task, candidate, baseline)
    assert result["decision"] == "rejected"
    assert "fuzz_violation" in result["exploit_or_contract_audit"]


# ── ledger row shape + replay_cmd ────────────────────────────────────────────
def test_ledger_row_shape_and_replay_cmd(tmp_path):
    path = tmp_path / "ledger.jsonl"
    row = {
        "iter": 0,
        "task_id": "off_by_one_range",
        "kind": "code_patch",
        "proposer": "test:fake",
        "visible_pass": True,
        "holdout_pass": True,
        "sentinel_regressed": False,
        "exploit_or_contract_audit": "n/a",
        "decision": "promoted",
        "replay_cmd": "python experiments/learnos/run_v0.py --replay abc123",
        "parent_id": None,
    }
    written = ledger.append(row, path=path)
    assert written["candidate_id"]
    assert written["ts"] > 0
    for field in ledger.REQUIRED_FIELDS:
        assert field in written

    rows = ledger.read_all(path)
    assert len(rows) == 1
    assert rows[0]["replay_cmd"] == row["replay_cmd"]


def test_ledger_rejects_missing_field(tmp_path):
    path = tmp_path / "ledger.jsonl"
    incomplete = {"iter": 0, "task_id": "x", "kind": "code_patch", "decision": "rejected"}
    with pytest.raises(ledger.LedgerError):
        ledger.append(incomplete, path=path)


def test_ledger_rejects_bad_decision(tmp_path):
    path = tmp_path / "ledger.jsonl"
    row = {
        "iter": 0,
        "task_id": "x",
        "kind": "code_patch",
        "proposer": "test",
        "visible_pass": True,
        "holdout_pass": True,
        "sentinel_regressed": False,
        "exploit_or_contract_audit": "n/a",
        "decision": "maybe",
        "replay_cmd": "x",
        "parent_id": None,
    }
    with pytest.raises(ledger.LedgerError):
        ledger.append(row, path=path)


# ── summarize() fix-rate curve ───────────────────────────────────────────────
def test_summarize_computes_fix_rate(tmp_path):
    path = tmp_path / "ledger.jsonl"

    def row(it, task_id, decision):
        return {
            "iter": it,
            "task_id": task_id,
            "kind": "code_patch",
            "proposer": "test",
            "visible_pass": True,
            "holdout_pass": decision == "promoted",
            "sentinel_regressed": False,
            "exploit_or_contract_audit": "n/a",
            "decision": decision,
            "replay_cmd": "x",
            "parent_id": None,
        }

    ledger.append(row(0, "task_a", "rejected"), path=path)
    ledger.append(row(0, "task_b", "promoted"), path=path)
    ledger.append(row(1, "task_a", "promoted"), path=path)
    ledger.append(row(1, "task_c", "rejected"), path=path)

    summary = ledger.summarize(path)
    assert summary["total_candidates"] == 4
    assert summary["total_promoted"] == 2
    assert summary["total_distinct_tasks"] == 3
    per_iter = {p["iter"]: p for p in summary["per_iter"]}
    assert per_iter[0] == {"iter": 0, "candidates": 2, "promoted": 1}
    assert per_iter[1] == {"iter": 1, "candidates": 2, "promoted": 1}
    curve = {p["iter"]: p for p in summary["held_out_fix_rate_curve"]}
    assert curve[0]["cumulative_fixed_tasks"] == 1  # task_b
    assert curve[1]["cumulative_fixed_tasks"] == 2  # + task_a
    assert summary["final_fix_rate"] == pytest.approx(2 / 3)


def test_summarize_empty_ledger(tmp_path):
    summary = ledger.summarize(tmp_path / "nonexistent.jsonl")
    assert summary["total_candidates"] == 0
    assert summary["final_fix_rate"] == 0.0


# ── full run_iteration with a scripted proposer (no live LLM) ───────────────
def test_run_iteration_with_scripted_proposer_promotes_real_fixes(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    task = tasks.get_task("wrong_operator_and_or")
    real_fix = "def is_valid_age(age):\n    return age >= 0 and age <= 120\n"
    # sequence: code_patch(1 call) -> scaffold(2 calls) -> tool(2 calls) == 5 calls/task
    responses = [
        _fence(real_fix),                    # code_patch
        "1. read the buggy code\n2. find the bug\n3. fix it\n4. test it",  # scaffold text
        _fence(real_fix),                    # scaffold-guided patch
        _fence("def noop_tool(x):\n    '''PRECONDITION: True\n    POSTCONDITION: True\n    '''\n    return x\n"),  # tool
        _fence(real_fix),                    # tool-guided patch
    ]
    proposer = ScriptedProposer(responses)
    rows = improve.run_iteration(0, proposer, "test:scripted", [task], max_tasks_per_iter=1, ledger_path=ledger_path)

    assert proposer.calls == 5
    assert len(rows) == 3  # one candidate per kind
    kinds = {r["kind"] for r in rows}
    assert kinds == {"code_patch", "cot_scaffold", "tool"}
    promoted = [r for r in rows if r["decision"] == "promoted"]
    assert len(promoted) >= 1  # at least the direct code_patch should promote
    for r in rows:
        assert r["replay_cmd"].startswith("python experiments/learnos/run_v0.py --replay ")
        assert r["parent_id"] is None

    ledger_rows = ledger.read_all(ledger_path)
    assert len(ledger_rows) == 3
    promoted_ids = ledger.promoted_task_ids(ledger_path)
    assert "wrong_operator_and_or" in promoted_ids


def test_run_iteration_unparsable_proposer_output_is_rejected_not_crashed(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    task = tasks.get_task("off_by_one_range")
    proposer = ScriptedProposer(["", "", "", "", ""])  # every call returns empty
    rows = improve.run_iteration(0, proposer, "test:empty", [task], max_tasks_per_iter=1, ledger_path=ledger_path)
    assert len(rows) == 3
    assert all(r["decision"] == "rejected" for r in rows)
    assert all(r["holdout_pass"] is None for r in rows)


def test_sample_tasks_skips_already_promoted():
    all_tasks = tasks.load_visible_tasks()
    ids = [t["task_id"] for t in all_tasks[:3]]
    batch = improve.sample_tasks(all_tasks, already_promoted=set(ids[:2]), max_n=5)
    batch_ids = {t["task_id"] for t in batch}
    assert ids[0] not in batch_ids
    assert ids[1] not in batch_ids
