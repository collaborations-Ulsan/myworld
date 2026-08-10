"""Deterministic tests for experiments/learnos/ S+1.1 (the diagnosed-fix re-attempt after
S+1 returned NO-transfer-compound -- docs/AIOS_LEARNOS_S1_RESULTS_2026-07-17.md,
docs/AIOS_AGI_CONCEPTION_2026-07-17.md §10, docs/ontology/ledger/learning_methods.md §4).

Covers the three new modules (causal_gate.py, gene_pool.py, evolve_s11.py) with scripted /
fake proposers -- no live LLM anywhere in this file, same discipline as
tests/test_learnos_s1.py and tests/test_learnos.py. Focus per the task brief:

  * causal gate promotes a causally-responsible tool and REJECTS a degenerate identity tool
    that passes tests
  * degeneracy pre-filter catches a constant-fn
  * gene-pool keeps two different-niche elites (no collapse)
  * niche resource cap enforced
  * no blind fallback (a niche with no elite returns nothing, not a random item)

...plus structural held-out isolation, heterogeneous-operator routing, and the
mine_iteration_s11 integration path that wires all three together.
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import pytest

_LEARNOS_DIR = Path(__file__).resolve().parents[1] / "experiments" / "learnos"
sys.path.insert(0, Path(__file__).resolve().parent.as_posix())

from _experiment_imports import load_from  # noqa: E402

# See tests/_experiment_imports.py — bare names collide across experiments/.
_mods = load_from(
    _LEARNOS_DIR, "archive", "causal_gate", "evolve_s11", "gene_pool",
    "improve", "ledger", "search", "tasks",
)
archive_mod = _mods["archive"]
causal_gate = _mods["causal_gate"]
evolve_s11 = _mods["evolve_s11"]
gene_pool_mod = _mods["gene_pool"]
improve = _mods["improve"]
ledger = _mods["ledger"]
search = _mods["search"]
tasks = _mods["tasks"]


def _fence(source: str) -> str:
    return f"```python\n{source}```"


class ScriptedProposer:
    """Returns queued canned responses in order; never calls out to a network. Same pattern
    as tests/test_learnos_s1.py::ScriptedProposer. `.last_operator` is always the local
    label, matching a plain (non-heterogeneous) proposer for tests that don't care about
    operator attribution."""

    last_operator = "test:scripted"

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[str] = []

    def __call__(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        if not self._responses:
            return ""
        return self._responses.pop(0)


# ── held-out isolation: structural guarantee extends to the new modules ─────────────────
def test_new_modules_never_reference_held_out_path():
    for fname in ("causal_gate.py", "gene_pool.py", "evolve_s11.py"):
        src = (_LEARNOS_DIR / fname).read_text(encoding="utf-8")
        for forbidden in ("tasks_held_out", "_load_held_out("):
            assert forbidden not in src, f"{fname} references forbidden {forbidden!r}"
    verify_src = (_LEARNOS_DIR / "verify.py").read_text(encoding="utf-8")
    assert "_load_held_out(" in verify_src  # sanity: verify.py IS still the sole reader


# ── degeneracy pre-filter (causal_gate.is_degenerate_tool) ──────────────────────────────
def test_degeneracy_prefilter_catches_identity_function():
    # exact S+1 §5 specimen: safe_index(xs, i): return i
    tool_source = (
        "def safe_index(xs, i):\n"
        '    """PRECONDITION: len(xs) > 0 and 0 <= i < len(xs)\n'
        '    POSTCONDITION: 0 <= result < len(xs) and xs[result] == xs[i]"""\n'
        "    return i\n"
    )
    degenerate, reason = causal_gate.is_degenerate_tool(tool_source, "safe_index", "0 <= result < len(xs) and xs[result] == xs[i]")
    assert degenerate is True
    assert reason == "identity_function"


def test_degeneracy_prefilter_catches_constant_fn():
    # exact S+1 §5 specimen: safe_factorial_base_case(n): return 1
    tool_source = (
        "def safe_factorial_base_case(n):\n"
        '    """PRECONDITION: n >= 0\n'
        '    POSTCONDITION: result == 1"""\n'
        "    return 1\n"
    )
    degenerate, reason = causal_gate.is_degenerate_tool(tool_source, "safe_factorial_base_case", "result == 1")
    assert degenerate is True
    assert reason == "constant_function"


def test_degeneracy_prefilter_catches_vacuous_postcondition_not_mentioning_result():
    tool_source = "def helper(x, y):\n    return x + y if x > y else x - y\n"
    degenerate, reason = causal_gate.is_degenerate_tool(tool_source, "helper", "True")
    assert degenerate is True
    assert reason == "vacuous_postcondition"


def test_degeneracy_prefilter_passes_a_real_tool():
    tool_source = "def range_end(n):\n    return n + 1\n"
    degenerate, reason = causal_gate.is_degenerate_tool(tool_source, "range_end", "result == n + 1")
    assert degenerate is False
    assert reason == ""


# ── causal ablation: tool ────────────────────────────────────────────────────────────────
def test_causal_gate_promotes_a_causally_responsible_tool():
    task = tasks.get_task("off_by_one_range")
    tool_source = "def range_end(n):\n    return n + 1\n"
    patch = "def sum_range(n):\n    total = 0\n    for i in range(1, range_end(n)):\n        total += i\n    return total\n"
    candidate = improve.Candidate(
        kind="tool", content=tool_source, patch_source=tool_source + "\n" + patch, proposer_calls=2,
    )
    result = causal_gate.check_causal_responsibility(task, candidate)
    assert result["causally_responsible"] is True
    assert result["with_passed"] > result["without_passed"]


def test_causal_gate_rejects_a_tool_the_patch_never_actually_needs():
    # the S+1 §5 mechanism: the code_patch part is ALREADY correct on its own; the tool is
    # prepended but never actually called by the exercised code path, so poisoning it
    # changes nothing -- WITH == WITHOUT, no causal credit.
    task = tasks.get_task("off_by_one_range")
    tool_source = "def unused_helper(n):\n    return n * 2\n"
    patch = "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
    candidate = improve.Candidate(
        kind="tool", content=tool_source, patch_source=tool_source + "\n" + patch, proposer_calls=2,
    )
    result = causal_gate.check_causal_responsibility(task, candidate)
    assert result["causally_responsible"] is False
    assert result["with_passed"] == result["without_passed"]


def test_causal_gate_rejects_degenerate_identity_tool_that_passes_visible_and_holdout():
    # this candidate PASSES improve.evaluate_candidate's base gate outright (visible +
    # holdout gain + no sentinel regression) because the code_patch ignores the tool -- the
    # degeneracy pre-filter must catch it before ablation even runs.
    task = tasks.get_task("wrong_index_fencepost")
    tool_source = (
        "def safe_index(xs, i):\n"
        '    """PRECONDITION: len(xs) > 0 and 0 <= i < len(xs)\n'
        '    POSTCONDITION: 0 <= result < len(xs) and xs[result] == xs[i]\n'
        '    """\n'
        "    return i\n"
    )
    patch = "def get_last(xs):\n    return xs[-1]\n"
    candidate = improve.Candidate(
        kind="tool", content=tool_source, patch_source=tool_source + "\n" + patch, proposer_calls=2,
    )
    baseline = improve.baseline_holdout_passed(task)
    base_eval = improve.evaluate_candidate(task, candidate, baseline)
    assert base_eval["decision"] == "promoted"  # base gate alone WOULD have promoted this

    parsed = improve._parse_tool(candidate.content)
    degenerate, reason = causal_gate.is_degenerate_tool(candidate.content, parsed["fn_name"], parsed["post"])
    assert degenerate is True
    assert reason == "identity_function"


# ── causal ablation: cot_scaffold ────────────────────────────────────────────────────────
def test_causal_gate_scaffold_causally_responsible_when_bare_patch_fails():
    task = tasks.get_task("off_by_one_range")
    good_patch = "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
    bad_patch = "def sum_range(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n"  # == buggy_source
    candidate = improve.Candidate(kind="cot_scaffold", content="1. check loop bounds", patch_source=good_patch, proposer_calls=2)
    without_control_proposer = ScriptedProposer([_fence(bad_patch)])
    result = causal_gate.check_causal_responsibility(task, candidate, proposer=without_control_proposer)
    assert result["causally_responsible"] is True
    assert len(without_control_proposer.calls) == 1  # exactly one extra WITHOUT-control call


def test_causal_gate_scaffold_not_responsible_when_bare_patch_equally_good():
    task = tasks.get_task("off_by_one_range")
    good_patch = "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
    candidate = improve.Candidate(kind="cot_scaffold", content="1. check loop bounds", patch_source=good_patch, proposer_calls=2)
    without_control_proposer = ScriptedProposer([_fence(good_patch)])  # bare call does just as well
    result = causal_gate.check_causal_responsibility(task, candidate, proposer=without_control_proposer)
    assert result["causally_responsible"] is False


def test_causal_gate_scaffold_requires_a_proposer():
    task = tasks.get_task("off_by_one_range")
    candidate = improve.Candidate(kind="cot_scaffold", content="x", patch_source="def sum_range(n):\n    return n\n", proposer_calls=1)
    with pytest.raises(causal_gate.CausalGateError):
        causal_gate.check_causal_responsibility(task, candidate, proposer=None)


def test_causal_gate_rejects_wrong_kind():
    task = tasks.get_task("off_by_one_range")
    candidate = improve.Candidate(kind="code_patch", content="x", patch_source="def sum_range(n):\n    return n\n", proposer_calls=1)
    with pytest.raises(causal_gate.CausalGateError):
        causal_gate.check_causal_responsibility(task, candidate)


# ── GenePool: speciation, recessive retention, resource cap, no blind fallback ──────────
def _entry(item_id: str, niche: str, bug_kind: str, capability: str, score: float, causally_responsible: bool = True) -> gene_pool_mod.GeneEntry:
    return gene_pool_mod.GeneEntry(
        item_id=item_id, niche=niche, bug_kind=bug_kind, capability=capability,
        content="c", patch_source="p", task_id="t", iter=0, score=score, operator="ollama:test",
        causally_responsible=causally_responsible, with_passed=2, without_passed=0,
    )


def test_gene_pool_keeps_two_different_niche_elites_no_collapse():
    pool = gene_pool_mod.GenePool(niche_cap=3)
    n1 = gene_pool_mod.niche_key("off_by_one", "tool")
    n2 = gene_pool_mod.niche_key("wrong_operator", "cot_scaffold")
    e1 = _entry("e1", n1, "off_by_one", "tool", 2.0)
    e2 = _entry("e2", n2, "wrong_operator", "cot_scaffold", 2.0)
    assert pool.add(e1) is True
    assert pool.add(e2) is True
    niches = pool.niches()
    assert set(niches.keys()) == {n1, n2}  # two distinct specialists, neither overwrote the other
    assert niches[n1].item_id == "e1"
    assert niches[n2].item_id == "e2"
    assert pool.qd_score() == pytest.approx(4.0)
    stats = pool.stats()
    assert stats["num_niches"] == 2
    assert stats["num_specialists"] == 2
    assert stats["distinct_bug_kinds_covered"] == 2


def test_gene_pool_higher_score_wins_niche_loser_becomes_recessive():
    pool = gene_pool_mod.GenePool(niche_cap=3)
    niche = gene_pool_mod.niche_key("off_by_one", "tool")
    weak = _entry("weak", niche, "off_by_one", "tool", 1.0)
    strong = _entry("strong", niche, "off_by_one", "tool", 2.0)
    pool.add(weak)
    became_elite = pool.add(strong)
    assert became_elite is True
    assert pool.best_for("off_by_one", "tool").item_id == "strong"
    recessive_ids = {e.item_id for e in pool.recessive_for("off_by_one", "tool")}
    assert recessive_ids == {"weak"}  # demoted, not discarded


def test_gene_pool_resource_cap_evicts_weakest_recessive_first():
    pool = gene_pool_mod.GenePool(niche_cap=2)
    niche = gene_pool_mod.niche_key("off_by_one", "tool")
    for item_id, score in [("a", 1.0), ("b", 3.0), ("c", 2.0), ("d", 5.0)]:
        pool.add(_entry(item_id, niche, "off_by_one", "tool", score))
    elite = pool.best_for("off_by_one", "tool")
    recessive = pool.recessive_for("off_by_one", "tool")
    assert elite.item_id == "d"  # highest score overall
    assert len(recessive) == 1
    assert recessive[0].item_id == "b"  # 2nd-highest survives the cap
    assert {e.item_id for e in recessive} == {"b"}
    assert "a" not in {e.item_id for e in recessive}  # weakest evicted
    total_retained = 1 + len(recessive)
    assert total_retained == pool.niche_cap


def test_gene_pool_no_blind_fallback_on_niche_miss():
    pool = gene_pool_mod.GenePool()
    pool.add(_entry("only", gene_pool_mod.niche_key("off_by_one", "tool"), "off_by_one", "tool", 2.0))
    assert pool.best_for("wrong_operator", "tool") is None  # different bug_kind, exact capability match -- still None
    assert pool.best_for("off_by_one", "cot_scaffold") is None  # same bug_kind, different capability -- still None
    assert pool.recessive_for("wrong_operator", "tool") == []


def test_gene_pool_add_requires_causal_verification_by_default():
    pool = gene_pool_mod.GenePool()
    bad = _entry("bad", gene_pool_mod.niche_key("off_by_one", "tool"), "off_by_one", "tool", 2.0, causally_responsible=False)
    with pytest.raises(gene_pool_mod.GenePoolError):
        pool.add(bad)
    assert pool.add(bad, require_causal_verified=False) is True  # explicit opt-out still allowed


def test_gene_pool_reuse_counts_do_not_mint_duplicate_entries():
    pool = gene_pool_mod.GenePool()
    e1 = _entry("e1", gene_pool_mod.niche_key("off_by_one", "tool"), "off_by_one", "tool", 2.0)
    pool.add(e1)
    pool.record_reuse("e1")
    pool.record_reuse("e1")
    assert pool.reuse_count("e1") == 2
    assert len(pool.niches()) == 1  # still one niche, no duplicate entry


def test_gene_pool_signature_changes_when_a_new_elite_is_added():
    pool = gene_pool_mod.GenePool()
    sig0 = pool.signature()
    pool.add(_entry("e1", gene_pool_mod.niche_key("off_by_one", "tool"), "off_by_one", "tool", 2.0))
    sig1 = pool.signature()
    assert sig0 != sig1


# ── evolve_s11: mutation selection / no blind fallback in the reuse path ─────────────────
def test_available_mutation_kinds_excludes_reuse_arms_when_pool_empty():
    pool = gene_pool_mod.GenePool()
    a_tasks = [tasks.get_task("off_by_one_range")]
    available = evolve_s11._available_mutation_kinds_s11(pool, a_tasks)
    assert "reuse_scaffold" not in available
    assert "reuse_tool" not in available
    assert "fresh_code_patch" in available


def test_reuse_tool_mutation_falls_back_to_fresh_when_niche_has_no_elite():
    # empty gene pool -- no niche exists for this bug_kind -- reuse_tool must NOT invent a
    # cross-bug_kind reuse; it must produce a FRESH proposal instead.
    pool = gene_pool_mod.GenePool()
    task = tasks.get_task("off_by_one_range")
    tool_source = "def range_end(n):\n    return n + 1\n"
    patch = "def sum_range(n):\n    total = 0\n    for i in range(1, range_end(n)):\n        total += i\n    return total\n"
    proposer = ScriptedProposer([_fence(tool_source), _fence(patch)])
    candidate, source_item_id = evolve_s11._propose_by_mutation_kind_s11(proposer, task, "reuse_tool", pool, "off_by_one")
    assert source_item_id is None  # nothing was reused
    assert candidate.meta.get("reused") is not True


def test_reuse_tool_mutation_reuses_when_niche_has_an_elite():
    pool = gene_pool_mod.GenePool()
    niche = gene_pool_mod.niche_key("off_by_one", "tool")
    pool.add(_entry("mined1", niche, "off_by_one", "tool", 2.0))
    pool._elite[niche] = gene_pool_mod.GeneEntry(
        item_id="mined1", niche=niche, bug_kind="off_by_one", capability="tool",
        content="def range_end(n):\n    return n + 1\n", patch_source="p", task_id="t", iter=0,
        score=2.0, operator="ollama:test", causally_responsible=True, with_passed=2, without_passed=0,
    )
    task = tasks.get_task("off_by_one_range")
    patch = "def sum_range(n):\n    total = 0\n    for i in range(1, range_end(n)):\n        total += i\n    return total\n"
    proposer = ScriptedProposer([_fence(patch)])
    candidate, source_item_id = evolve_s11._propose_by_mutation_kind_s11(proposer, task, "reuse_tool", pool, "off_by_one")
    assert source_item_id == "mined1"
    assert candidate.meta.get("reused") is True


# ── evolve_s11: full mine_iteration_s11 integration (router forced via pre-seeding) ─────
def _force_router(kind: str) -> search.MutationRouter:
    router = search.MutationRouter(epsilon=0.0)
    for k in search.MUTATION_KINDS:
        if k != kind:
            router.update(k, -1.0)
    return router


def test_mine_iteration_s11_promotes_causally_responsible_tool_into_gene_pool(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    task = tasks.get_task("off_by_one_range")
    tool_source = (
        "def range_end(n):\n"
        '    """PRECONDITION: n >= 0\n'
        '    POSTCONDITION: result == n + 1\n'
        '    """\n'
        "    return n + 1\n"
    )
    patch = "def sum_range(n):\n    total = 0\n    for i in range(1, range_end(n)):\n        total += i\n    return total\n"
    proposer = ScriptedProposer([_fence(tool_source), _fence(patch)])
    state = evolve_s11.SearchStateS11(router=_force_router("fresh_tool"))
    rows = evolve_s11.mine_iteration_s11(
        0, proposer, "test:scripted", [task], state, max_tasks_per_iter=1,
        rng=random.Random(0), ledger_path=ledger_path,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["base_gate_decision"] == "promoted"
    assert row["decision"] == "promoted"
    assert row["causally_responsible"] is True
    assert state.causal_stats.causally_verified == 1
    assert state.causal_stats.causal_rejected == 0
    assert state.causal_stats.degenerate_prefiltered == 0
    elite = state.gene_pool.best_for("off_by_one", "tool")
    assert elite is not None
    assert elite.item_id == row["candidate_id"]


def test_mine_iteration_s11_rejects_degenerate_tool_never_enters_pool(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    task = tasks.get_task("wrong_index_fencepost")
    tool_source = (
        "def safe_index(xs, i):\n"
        '    """PRECONDITION: len(xs) > 0 and 0 <= i < len(xs)\n'
        '    POSTCONDITION: 0 <= result < len(xs) and xs[result] == xs[i]\n'
        '    """\n'
        "    return i\n"
    )
    patch = "def get_last(xs):\n    return xs[-1]\n"
    proposer = ScriptedProposer([_fence(tool_source), _fence(patch)])
    state = evolve_s11.SearchStateS11(router=_force_router("fresh_tool"))
    rows = evolve_s11.mine_iteration_s11(
        0, proposer, "test:scripted", [task], state, max_tasks_per_iter=1,
        rng=random.Random(0), ledger_path=ledger_path,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["base_gate_decision"] == "promoted"  # base gate WOULD have promoted this
    assert row["decision"] == "rejected"             # causal gate overrides it
    assert row["degenerate_prefiltered"] is True
    assert state.causal_stats.degenerate_prefiltered == 1
    assert state.gene_pool.best_for("index_fencepost", "tool") is None  # never entered the pool
    assert len(state.gene_pool.niches()) == 0


def test_mine_iteration_s11_rejects_a_tool_that_fails_causal_ablation(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    task = tasks.get_task("off_by_one_range")
    tool_source = (
        "def unused_helper(n):\n"
        '    """PRECONDITION: n >= 0\n'
        '    POSTCONDITION: result == n * 2\n'
        '    """\n'
        "    return n * 2\n"
    )
    patch = "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
    proposer = ScriptedProposer([_fence(tool_source), _fence(patch)])
    state = evolve_s11.SearchStateS11(router=_force_router("fresh_tool"))
    rows = evolve_s11.mine_iteration_s11(
        0, proposer, "test:scripted", [task], state, max_tasks_per_iter=1,
        rng=random.Random(0), ledger_path=ledger_path,
    )
    row = rows[0]
    assert row["base_gate_decision"] == "promoted"
    assert row["decision"] == "rejected"
    assert row["causally_responsible"] is False
    assert state.causal_stats.causal_rejected == 1
    assert len(state.gene_pool.niches()) == 0


def test_mine_iteration_s11_never_touches_tasks_outside_its_pool(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    a_pool = [tasks.get_task("off_by_one_range"), tasks.get_task("wrong_operator_and_or")]
    responses = [_fence("def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n")] * 10
    proposer = ScriptedProposer(responses)
    state = evolve_s11.SearchStateS11(router=_force_router("fresh_code_patch"))
    rows = evolve_s11.mine_iteration_s11(
        0, proposer, "test:scripted", a_pool, state, max_tasks_per_iter=2,
        rng=random.Random(0), ledger_path=ledger_path,
    )
    pool_ids = {t["task_id"] for t in a_pool}
    assert rows
    for r in rows:
        assert r["task_id"] in pool_ids


# ── heterogeneous mutation: operator routing + attribution ───────────────────────────────
def test_heterogeneous_proposer_all_ollama_when_nim_unavailable(monkeypatch):
    monkeypatch.setattr(evolve_s11.backend, "complete", lambda prompt, **kw: evolve_s11.backend.backend_name())
    rng = random.Random(0)
    proposer = evolve_s11.HeterogeneousProposer(rng, nim_available=False, nim_fraction=0.9)
    results = [proposer("p") for _ in range(5)]
    assert all(r == "ollama" for r in results)
    assert proposer.last_operator == proposer.ollama_label


def test_heterogeneous_proposer_routes_to_nim_when_fraction_is_one(monkeypatch):
    monkeypatch.setattr(evolve_s11.backend, "complete", lambda prompt, **kw: evolve_s11.backend.backend_name())
    rng = random.Random(0)
    proposer = evolve_s11.HeterogeneousProposer(rng, nim_available=True, nim_fraction=1.0)
    results = [proposer("p") for _ in range(5)]
    assert all(r == "nim" for r in results)
    assert proposer.last_operator == proposer.nim_label
    assert proposer.call_operators == [proposer.nim_label] * 5


def test_heterogeneous_proposer_restores_prior_backend_env(monkeypatch):
    monkeypatch.setattr(evolve_s11.backend, "complete", lambda prompt, **kw: "x")
    monkeypatch.setenv("AIOS_LEARNOS_BACKEND", "ollama")
    rng = random.Random(0)
    proposer = evolve_s11.HeterogeneousProposer(rng, nim_available=True, nim_fraction=1.0)
    proposer("p")
    assert os.environ["AIOS_LEARNOS_BACKEND"] == "ollama"


def test_nim_key_available_reflects_backend_loader(monkeypatch):
    monkeypatch.setattr(evolve_s11.backend, "_load_nim_key", lambda: "unused-in-test")
    assert evolve_s11.nim_key_available() is True

    def _raise():
        raise evolve_s11.backend.ProposerError("no key configured")

    monkeypatch.setattr(evolve_s11.backend, "_load_nim_key", _raise)
    assert evolve_s11.nim_key_available() is False


# ── evaluate_group_s11: gene-pool mode is niche-matched only, baseline mode reused as-is ─
def test_evaluate_group_s11_gene_pool_mode_requires_a_pool():
    task = tasks.get_task("off_by_one_range")
    with pytest.raises(ValueError):
        evolve_s11.evaluate_group_s11(ScriptedProposer([]), [task], "gene_pool")


def test_eval_task_gene_pool_augmented_no_augmentation_on_niche_miss():
    # a B-shaped task whose bug_kind has no elite in the pool must get NO scaffold/tool
    # injected -- not a fallback item from an unrelated bug_kind.
    pool = gene_pool_mod.GenePool()
    pool.add(_entry("e1", gene_pool_mod.niche_key("wrong_operator", "tool"), "wrong_operator", "tool", 2.0))
    task = tasks.get_task("off_by_one_last_n")  # bug_kind == "off_by_one", no niche for it
    real_fix = "def last_n(xs, n):\n    return xs[-n:]\n"
    proposer = ScriptedProposer([_fence(real_fix)])
    result = evolve_s11.eval_task_gene_pool_augmented(proposer, task, pool)
    assert result["used_scaffold"] is False
    assert result["used_tool"] is False
