"""Deterministic tests for experiments/learnos/ S+1 (docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md):
the evolutionary SEARCH loop (archive + mutation router + hypothesis/rewrite decoupling),
the Blind-Curator verifier audit, and the transfer-holdout compounding measurement. No live
LLM anywhere in this file -- scripted/fake proposers stand in for backend.complete(), same
discipline as tests/test_learnos.py.

Covers (per the S+1 task brief): A/B disjointness enforced structurally, B held-out
unreadable by the mining path, archive cell diversity, mutation-router picks by yield, the
audit catching an injected false-pass, and compounding-curve computation from a synthetic
ledger (one rising fixture, one flat fixture).
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pytest

_LEARNOS_DIR = Path(__file__).resolve().parents[1] / "experiments" / "learnos"
sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

from _experiment_imports import load_from  # noqa: E402

# See tests/_experiment_imports.py — bare names collide across experiments/.
_mods = load_from(
    _LEARNOS_DIR, "archive", "audit", "improve", "ledger", "search", "tasks",
)
archive_mod = _mods["archive"]
audit = _mods["audit"]
improve = _mods["improve"]
ledger = _mods["ledger"]
search = _mods["search"]
tasks = _mods["tasks"]


def _fence(source: str) -> str:
    return f"```python\n{source}```"


class ScriptedProposer:
    """Returns queued canned responses in order; never calls out to a network. Same pattern
    as tests/test_learnos.py::ScriptedProposer."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[str] = []

    def __call__(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        if not self._responses:
            return ""
        return self._responses.pop(0)


# ── A/B/sentinel split: structural guarantees ───────────────────────────────
def test_split_pairwise_disjoint_and_each_at_least_10():
    split = search.load_split()
    a, b, sentinel = set(split["A"]), set(split["B"]), set(split["sentinel"])
    assert len(split["A"]) >= 10
    assert len(split["B"]) >= 10
    assert a & b == set()
    assert a & sentinel == set()
    assert b & sentinel == set()


def test_split_covers_every_task_id_exactly_once():
    split = search.load_split()
    all_ids = set(tasks.task_ids())
    union = set(split["A"]) | set(split["B"]) | set(split["sentinel"])
    assert union == all_ids
    total_len = len(split["A"]) + len(split["B"]) + len(split["sentinel"])
    assert total_len == len(all_ids)  # no id counted twice


def test_run_search_rejects_an_overlapping_split():
    bad_split = {"A": ["off_by_one_range"], "B": ["off_by_one_range"], "sentinel": []}
    with pytest.raises(AssertionError):
        search.run_search(1, ScriptedProposer([]), "test:bad", split=bad_split)


# ── B held-out unreadable by the mining/search code path (structural, not a comment) ────
def test_search_and_archive_never_reference_held_out_path():
    search_src = (_LEARNOS_DIR / "search.py").read_text(encoding="utf-8")
    archive_src = (_LEARNOS_DIR / "archive.py").read_text(encoding="utf-8")
    verify_src = (_LEARNOS_DIR / "verify.py").read_text(encoding="utf-8")
    for forbidden in ("tasks_held_out", "_load_held_out("):
        assert forbidden not in search_src, f"search.py references forbidden {forbidden!r}"
        assert forbidden not in archive_src, f"archive.py references forbidden {forbidden!r}"
        assert forbidden in verify_src  # sanity: verify.py IS still the sole reader


def test_mine_iteration_never_touches_tasks_outside_its_pool(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    a_pool = [tasks.get_task("off_by_one_range"), tasks.get_task("wrong_operator_and_or")]
    responses = [_fence("def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n")] * 10
    proposer = ScriptedProposer(responses)
    state = search.SearchState()
    rows = search.mine_iteration(0, proposer, "test:scripted", a_pool, state, max_tasks_per_iter=2, rng=random.Random(0), ledger_path=ledger_path)
    pool_ids = {t["task_id"] for t in a_pool}
    assert rows  # something happened
    for r in rows:
        assert r["task_id"] in pool_ids
    for e in state.archive.lineage():
        assert e.task_id in pool_ids


# ── archive: behavior-descriptor cells diverge for different-behavior candidates ────────
def test_task_bug_kind_disambiguates_overlapping_substrings():
    # "list_slicing_off_by_one" must resolve to list_slicing, not the generic off_by_one
    # substring it also contains -- see archive.py's ordering rationale.
    assert archive_mod.task_bug_kind("list_slicing_off_by_one") == "list_slicing"
    assert archive_mod.task_bug_kind("string_reverse_off_by_one") == "string_reverse"
    assert archive_mod.task_bug_kind("off_by_one_range") == "off_by_one"
    assert archive_mod.task_bug_kind("off_by_one_last_n") == "off_by_one"


def test_archive_two_different_behavior_candidates_land_in_different_cells():
    arc = archive_mod.Archive()
    row_loop = {
        "candidate_id": "c1", "task_id": "off_by_one_range", "kind": "code_patch", "iter": 0,
        "decision": "promoted", "parent_id": None, "mutation_kind": "fresh_code_patch",
        "content": "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n",
        "patch_source": "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n",
        "visible_pass": True, "holdout_pass": True,
    }
    row_scaffold = {
        "candidate_id": "c2", "task_id": "off_by_one_range", "kind": "cot_scaffold", "iter": 0,
        "decision": "rejected", "parent_id": None, "mutation_kind": "fresh_scaffold",
        "content": "1. read\n2. locate\n3. fix\n4. verify", "patch_source": "",
        "visible_pass": False, "holdout_pass": False,
    }
    e1 = arc.add_row(row_loop)
    e2 = arc.add_row(row_scaffold)
    assert e1.cell != e2.cell
    assert len(arc.cells()) == 2
    assert len(arc.lineage()) == 2


def test_archive_keeps_full_lineage_even_when_not_cell_best():
    arc = archive_mod.Archive()
    base = {
        "task_id": "off_by_one_range", "kind": "code_patch", "iter": 0, "parent_id": None,
        "mutation_kind": "fresh_code_patch",
        "content": "def sum_range(n):\n    return n\n", "patch_source": "def sum_range(n):\n    return n\n",
    }
    weaker = {**base, "candidate_id": "weak", "decision": "rejected", "visible_pass": False, "holdout_pass": False}
    stronger = {**base, "candidate_id": "strong", "decision": "promoted", "visible_pass": True, "holdout_pass": True}
    arc.add_row(weaker)
    arc.add_row(stronger)
    assert len(arc.lineage()) == 2  # both kept
    assert len(arc.cells()) == 1  # same cell (identical shape/bug_kind)
    elite = list(arc.cells().values())[0]
    assert elite.candidate_id == "strong"  # higher score wins the cell


def test_patch_shape_distinguishes_loop_recursion_straightline():
    straight = archive_mod.patch_shape("code_patch", "def f(x):\n    return x + 1\n")
    loop = archive_mod.patch_shape("code_patch", "def f(xs):\n    t = 0\n    for x in xs:\n        t += x\n    return t\n")
    recursive = archive_mod.patch_shape("code_patch", "def f(n):\n    if n <= 1:\n        return 1\n    return n * f(n - 1)\n")
    assert straight != loop != recursive
    assert "loop" in loop
    assert "recursion" in recursive
    assert archive_mod.patch_shape("cot_scaffold", "some prose") == "cot_scaffold:prose"
    assert archive_mod.patch_shape("code_patch", "not valid python (((") == "code_patch:unparsable"


def test_archive_sample_parents_prefers_distinct_cells(tmp_path):
    arc = archive_mod.Archive()
    for i in range(3):
        arc.add_row(
            {
                "candidate_id": f"c{i}", "task_id": f"off_by_one_range", "kind": "code_patch", "iter": 0,
                "decision": "promoted", "parent_id": None, "mutation_kind": "fresh_code_patch",
                "content": f"def sum_range(n):\n    " + "x = 1\n    " * i + "return n\n",
                "patch_source": f"def sum_range(n):\n    " + "x = 1\n    " * i + "return n\n",
                "visible_pass": True, "holdout_pass": True,
            }
        )
    parents = arc.sample_parents(2, random.Random(1))
    assert len(parents) == 2
    assert len({p.cell for p in parents}) == len(parents)  # distinct cells, not duplicates


# ── mutation router: picks by observed yield ─────────────────────────────────────────────
def test_mutation_router_explores_every_arm_before_exploiting():
    router = search.MutationRouter(epsilon=0.0)
    rng = random.Random(0)
    seen = set()
    for _ in range(len(search.MUTATION_KINDS)):
        chosen = router.choose(rng)
        seen.add(chosen)
        router.update(chosen, 0.0)
    assert seen == set(search.MUTATION_KINDS)  # every arm tried at least once


def test_mutation_router_prefers_higher_observed_yield_once_all_arms_seen():
    router = search.MutationRouter(epsilon=0.0)  # pure exploitation once arms are seen
    for kind in search.MUTATION_KINDS:
        router.update(kind, 0.0)
    router.update("fresh_tool", 1.0)  # only fresh_tool ever earned a reward
    rng = random.Random(0)
    for _ in range(5):
        assert router.choose(rng) == "fresh_tool"


def test_mutation_router_yields_reflect_reward_history():
    router = search.MutationRouter()
    router.update("fresh_code_patch", 1.0)
    router.update("fresh_code_patch", 0.0)
    router.update("fresh_scaffold", 0.0)
    yields = router.yields()
    assert yields["fresh_code_patch"] == pytest.approx(0.5)
    assert yields["fresh_scaffold"] == pytest.approx(0.0)
    assert yields["fresh_tool"] == 0.0  # never observed -> defined as 0.0


def test_library_reuse_credits_original_item_not_a_duplicate(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    task = tasks.get_task("wrong_operator_and_or")
    real_fix = "def is_valid_age(age):\n    return age >= 0 and age <= 120\n"
    state = search.SearchState()
    # force the router to pick fresh_scaffold first, then reuse_scaffold, by pre-seeding
    # every OTHER arm as already-seen with a low reward so exploitation (epsilon=0) prefers
    # exploring the untried ones in order the test controls via a fixed rng seed + epsilon=0.
    state.router = search.MutationRouter(epsilon=0.0)
    for kind in search.MUTATION_KINDS:
        if kind not in ("fresh_scaffold", "reuse_scaffold"):
            state.router.update(kind, -1.0)
    responses = [
        _fence(real_fix),  # fresh_scaffold's scaffold text (kept as content)
        _fence(real_fix),  # fresh_scaffold's scaffold-guided patch
        _fence(real_fix),  # reuse_scaffold's patch (reusing the mined scaffold)
    ]
    proposer = ScriptedProposer(responses)
    a_pool = [task]
    rng = random.Random(0)
    search.mine_iteration(0, proposer, "test:scripted", a_pool, state, max_tasks_per_iter=1, rng=rng, ledger_path=ledger_path)
    assert len(state.library.items) == 1
    search.mine_iteration(1, proposer, "test:scripted", a_pool, state, max_tasks_per_iter=1, rng=rng, ledger_path=ledger_path)
    assert len(state.library.items) == 1  # reuse did NOT create a duplicate
    assert state.library.items[0].promotions >= 1  # but the reuse WAS credited


# ── Blind-Curator audit: catches an injected false-pass ─────────────────────────────────
def test_audit_catches_injected_false_pass_with_a_weakened_gate():
    always_promote = lambda task, candidate, baseline: {
        "task_id": task["task_id"], "kind": candidate.kind, "visible_pass": True,
        "holdout_pass": True, "sentinel_regressed": False, "exploit_or_contract_audit": "n/a",
        "decision": "promoted",
    }
    task_pool = [tasks.get_task("off_by_one_range"), tasks.get_task("incorrect_accumulator_init")]
    result = audit.run_audit(task_pool, gate_fn=always_promote, threshold=0.05)
    assert result["n_trials"] > 0
    assert result["false_pass_rate"] == 1.0
    assert result["freeze_promotion"] is True


def test_audit_real_gate_has_zero_false_pass_on_a_small_sample():
    task_pool = [
        tasks.get_task("off_by_one_range"),
        tasks.get_task("incorrect_accumulator_init"),
        tasks.get_task("wrong_operator_and_or"),
    ]
    result = audit.run_audit(task_pool)  # default gate_fn = improve.evaluate_candidate
    assert result["n_trials"] >= 3  # at least the 3 overfit trials
    assert result["false_pass_rate"] == 0.0
    assert result["freeze_promotion"] is False


def test_inject_overfit_defect_passes_visible_but_gains_nothing_on_holdout():
    task = tasks.get_task("off_by_one_range")
    baseline = improve.baseline_holdout_passed(task)
    defect_src = audit.inject_overfit_defect(task)
    assert defect_src is not None
    visible = improve.verify.run_public(task["visible_tests"], defect_src)
    assert visible["all_passed"] is True
    holdout = improve.verify.run_holdout(task["task_id"], defect_src)
    assert holdout["passed"] <= baseline  # no generalization gain


def test_inject_sentinel_breaking_defect_regresses_only_the_sentinel():
    task = tasks.get_task("incorrect_accumulator_init")
    golden = audit.GOLDEN_FIXES[task["task_id"]]
    defect_src = audit.inject_sentinel_breaking_defect(task, golden)
    assert defect_src is not None
    visible = improve.verify.run_public(task["visible_tests"], defect_src)
    assert visible["all_passed"] is True
    sentinel = improve.verify.run_public([task["sentinel_check"]], defect_src)
    assert sentinel["all_passed"] is False  # the one case the defect deliberately breaks
    holdout = improve.verify.run_holdout(task["task_id"], defect_src)
    assert holdout["all_passed"] is True  # correct everywhere else, including held-out


# ── compounding curve: synthetic fixtures (one rising, one flat) ────────────────────────
def test_compounding_curve_rising_fixture():
    records = [
        {"iter": -1, "successes": 2, "total": 12},
        {"iter": 0, "successes": 3, "total": 12},
        {"iter": 5, "successes": 6, "total": 12},
        {"iter": 11, "successes": 9, "total": 12},
    ]
    curve = search.compounding_curve(records)
    rates = [p["rate"] for p in curve["points"]]
    assert rates == sorted(rates)  # monotonically non-decreasing in this fixture
    assert curve["final_vs_first"]["rising"] is True
    assert curve["final_vs_first"]["falling"] is False
    for p in curve["points"]:
        assert p["ci_lo"] <= p["rate"] <= p["ci_hi"]


def test_compounding_curve_flat_fixture():
    records = [
        {"iter": -1, "successes": 5, "total": 12},
        {"iter": 3, "successes": 5, "total": 12},
        {"iter": 7, "successes": 5, "total": 12},
        {"iter": 11, "successes": 5, "total": 12},
    ]
    curve = search.compounding_curve(records)
    assert curve["final_vs_first"]["flat"] is True
    assert curve["final_vs_first"]["rising"] is False
    assert curve["final_vs_first"]["falling"] is False
    assert all(p["rate"] == pytest.approx(5 / 12) for p in curve["points"])


def test_compounding_curve_falling_fixture_is_reported_honestly():
    records = [{"iter": -1, "successes": 9, "total": 12}, {"iter": 5, "successes": 4, "total": 12}]
    curve = search.compounding_curve(records)
    assert curve["final_vs_first"]["falling"] is True
    assert curve["final_vs_first"]["rising"] is False


def test_wilson_ci_bounds_are_sane():
    assert search.wilson_ci(0, 0) == (0.0, 0.0)
    for successes, n in [(0, 10), (5, 10), (10, 10), (1, 3)]:
        lo, hi = search.wilson_ci(successes, n)
        rate = successes / n
        assert 0.0 <= lo <= rate <= hi <= 1.0


def test_sign_test_exact_values():
    # idx0: fail->pass (improved), idx1: fail->pass (improved), idx2: pass->pass (no change),
    # idx3: pass->fail (regressed)
    pre = [False, False, True, True]
    post = [True, True, True, False]
    result = search.sign_test(pre, post)
    assert result["improved"] == 2
    assert result["regressed"] == 1
    assert result["n_discordant"] == 3
    n, k = 3, 1  # min(2, 1)
    expected_tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2**n)
    assert result["p_value_two_sided"] == pytest.approx(min(1.0, 2 * expected_tail))


def test_sign_test_requires_paired_equal_length():
    with pytest.raises(ValueError):
        search.sign_test([True], [True, False])


def test_sign_test_no_discordant_pairs_gives_p_one():
    result = search.sign_test([True, False], [True, False])
    assert result["n_discordant"] == 0
    assert result["p_value_two_sided"] == 1.0


# ── evaluate_group / group_success_rate: aggregate-only, mirrors v0's isolation guarantee ─
def test_evaluate_group_baseline_uses_run_holdout_aggregate_only():
    task = tasks.get_task("off_by_one_range")
    real_fix = "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
    proposer = ScriptedProposer([_fence(real_fix)])
    results = search.evaluate_group(proposer, [task], "baseline")
    assert len(results) == 1
    assert set(results[0]["holdout"].keys()) == {"total", "passed", "all_passed", "timed_out", "error"}
    successes, n = search.group_success_rate(results)
    assert (successes, n) == (1, 1)


def test_evaluate_group_library_mode_requires_a_library():
    task = tasks.get_task("off_by_one_range")
    with pytest.raises(ValueError):
        search.evaluate_group(ScriptedProposer([]), [task], "library", library=None)
