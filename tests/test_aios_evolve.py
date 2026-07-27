"""Unit tests for scripts/aios_evolve.py — the evolutionary selection organ.

Proves, on the REAL mechanism (no mocks of the sandbox):
  (i)    the offline deterministic path produces candidates with NO LLM;
  (ii)   a candidate whose test passes scores > 0 and one that fails scores 0
         — with generator / verifier / scorer recorded as three distinct roles;
  (iii)  a reward-hacking candidate (constant return, test expects real
         behavior) is rejected by fitness (not proposable), and a candidate
         that passes its own test but breaks under input fuzzing is flagged by
         contrastive_robustness;
  (iv)   Gumbel selection is seed-deterministic and does NOT always pick
         argmax (temperature effect);
  (v)    Sinkhorn output rows/cols approach the target marginals and prevent
         all-or-nothing collapse;
  (vi)   lineage is append-only and carries BOTH verdicts (pass and fail),
         and survivors are PROPOSED only (never auto-registered);
  (vii)  sandbox-unavailable -> refuse to evaluate (nothing executed);
  (viii) an unreachable substrate degrades honestly (recorded failure +
         offline fallback, never a fabricated candidate).

Sandbox-executing tests skip loudly on a box with no working engine; the
fail-closed path (vii) runs everywhere. Lineage/receipts live under tmp_path —
nothing touches the real .aios/ state.
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (_ROOT / "scripts").as_posix())

import aios_evolve  # noqa: E402
import aios_sandbox  # noqa: E402

NOW = 1_753_574_400.0

ENGINE = aios_sandbox.pick_engine()
needs_sandbox = pytest.mark.skipif(
    ENGINE == "none",
    reason="no working sandbox engine on this box — sandboxed scoring cannot "
           "be exercised live (the fail-closed refusal path is still covered)")

# Broken artifact: double(x) implemented as x - x. The unit test covers TWO
# inputs so a constant-returner cannot fully pass (anti-reward-hack fixture).
ARTIFACT = {
    "name": "double",
    "code": "def double(x):\n    return x - x\n",
    "unit_test": "assert double(3) == 6\nassert double(1) == 2\n",
    "error": "AssertionError: double(3) == 6 failed (got 0)",
    "entry": "double",
    "example_inputs": [[3]],
}


@pytest.fixture()
def paths(tmp_path):
    return {"lineage": tmp_path / "lineage.jsonl",
            "receipt_log": tmp_path / "receipts.jsonl"}


def _evolve(paths, **kw):
    base = dict(rounds=1, n=4, substrate="offline", model=None, now=NOW,
                lineage=paths["lineage"], receipt_log=paths["receipt_log"],
                sandbox_timeout=15.0, fuzz_k=4)
    base.update(kw)
    return aios_evolve.evolve(ARTIFACT, **base)


# ── (i) offline deterministic path: candidates with no LLM ───────────────────

def test_offline_path_is_deterministic_and_llm_free():
    gen = aios_evolve.generate_variants(ARTIFACT, 4, substrate="offline",
                                        model=None, now=NOW)
    assert gen["candidates"], "offline perturbation must produce candidates"
    assert gen["substrate_failures"] == []
    assert gen["fallback_used"] is False
    assert all(c["origin"] == "offline-perturb" for c in gen["candidates"])
    assert all(c["model"] is None for c in gen["candidates"])
    # x - x has exactly one mutable operator site -> ("-","+") and ("-","*")
    codes = [c["code"] for c in gen["candidates"]]
    assert "def double(x):\n    return x + x\n" in codes
    assert "def double(x):\n    return x * x\n" in codes
    again = aios_evolve.generate_variants(ARTIFACT, 4, substrate="offline",
                                          model=None, now=NOW)
    assert [c["code"] for c in again["candidates"]] == codes  # deterministic
    # roles are recorded even for the no-LLM generator
    assert set(gen["roles"]) == {"generator", "verifier", "scorer"}


# ── (ii) fitness: pass > 0, fail == 0, three distinct roles ──────────────────

@needs_sandbox
def test_fitness_pass_scores_positive_fail_scores_zero(paths):
    good = aios_evolve.make_candidate(
        "def double(x):\n    return x + x\n", ARTIFACT)
    bad = aios_evolve.make_candidate(
        "def double(x):\n    return x * x\n", ARTIFACT)  # fails both asserts
    fit = aios_evolve.fitness([good, bad], sandbox_timeout=15.0,
                              now=NOW, receipt_log=paths["receipt_log"])
    assert fit["refused"] is False
    g, b = fit["results"]
    assert g["fitness"] == 1.0 and g["verdict"] == "pass" and g["ran"] is True
    assert g["tests_passed"] == 2 and g["tests_total"] == 2
    assert b["fitness"] == 0.0 and b["verdict"] == "fail" and b["ran"] is True
    # anti-reward-hacking invariant: three DISTINCT roles in the output
    roles = fit["roles"]
    assert set(roles) == {"generator", "verifier", "scorer"}
    assert len({roles["generator"], roles["verifier"], roles["scorer"]}) == 3
    assert "aios_sandbox" in roles["scorer"]


@needs_sandbox
def test_candidate_that_fails_to_run_scores_hard_zero(paths):
    broken = aios_evolve.make_candidate(
        "def double(x):\n    return undefined_name\n\ndouble(0)\n", ARTIFACT)
    fit = aios_evolve.fitness([broken], sandbox_timeout=15.0,
                              now=NOW, receipt_log=paths["receipt_log"])
    (r,) = fit["results"]
    assert r["fitness"] == 0.0
    assert r["verdict"] == "failed_to_run"


# ── (iii) reward hacking rejected; overfit flagged by robustness ─────────────

@needs_sandbox
def test_reward_hacking_constant_is_rejected_by_fitness(paths):
    constant = aios_evolve.make_candidate(
        "def double(x):\n    return 6\n", ARTIFACT)
    fit = aios_evolve.fitness([constant], sandbox_timeout=15.0,
                              now=NOW, receipt_log=paths["receipt_log"])
    (r,) = fit["results"]
    # passes only double(3) == 6 — the multi-input external test catches it
    assert r["tests_passed"] == 1 and r["tests_total"] == 2
    assert r["fitness"] == 0.5 and r["verdict"] == "partial"
    assert r["proposable"] is False, "a constant-returner must never be proposable"


@needs_sandbox
def test_overfit_candidate_flagged_by_contrastive_robustness(paths):
    # Passes BOTH asserts (a lookup table over exactly the tested inputs) but
    # is not the behavior — input fuzzing must expose it.
    overfit = aios_evolve.make_candidate(
        "def double(x):\n    return {3: 6, 1: 2}[x]\n", ARTIFACT)
    healthy = aios_evolve.make_candidate(
        "def double(x):\n    return x + x\n", ARTIFACT)
    fit = aios_evolve.fitness([overfit], sandbox_timeout=15.0,
                              now=NOW, receipt_log=paths["receipt_log"])
    assert fit["results"][0]["fitness"] == 1.0, "overfit passes its author's test"

    rob_o = aios_evolve.contrastive_robustness(
        overfit, k=8, sandbox_timeout=15.0, now=NOW,
        receipt_log=paths["receipt_log"])
    rob_h = aios_evolve.contrastive_robustness(
        healthy, k=8, sandbox_timeout=15.0, now=NOW,
        receipt_log=paths["receipt_log"])
    assert rob_h["robustness"] == 1.0 and rob_h["fragile"] is False
    assert rob_o["robustness"] < 0.5, "transformed inputs must break the lookup table"
    assert rob_o["fragile"] is True
    assert rob_o["failures"], "failing probes must be reported (truncated)"
    # determinism of the seeded fuzz
    again = aios_evolve.contrastive_robustness(
        overfit, k=8, sandbox_timeout=15.0, now=NOW,
        receipt_log=paths["receipt_log"])
    assert again["robustness"] == rob_o["robustness"]
    assert again["probes_run"] == rob_o["probes_run"]


# ── (iv) Gumbel: seed-deterministic, temperature-controlled exploration ──────

def test_gumbel_seed_deterministic_and_not_always_argmax():
    fitnesses = [0.9, 0.1]
    a = aios_evolve.gumbel_softmax_select(fitnesses, temperature=4.0, seed=7)
    b = aios_evolve.gumbel_softmax_select(fitnesses, temperature=4.0, seed=7)
    assert a == b, "same seed must give the identical selection record"
    assert a["argmax_index"] == 0
    assert abs(sum(a["probs"]) - 1.0) < 1e-9
    assert abs(sum(a["relaxed"]) - 1.0) < 1e-9

    # high temperature: exploration — non-argmax picks must occur across seeds
    hot = {aios_evolve.gumbel_softmax_select(fitnesses, temperature=4.0,
                                             seed=s)["selected_index"]
           for s in range(200)}
    assert hot == {0, 1}, "high temperature must NOT always pick argmax"
    # near-zero temperature: exploitation — argmax always
    cold = {aios_evolve.gumbel_softmax_select(fitnesses, temperature=0.01,
                                              seed=s)["selected_index"]
            for s in range(200)}
    assert cold == {0}, "low temperature must recover argmax"

    with pytest.raises(ValueError):
        aios_evolve.gumbel_softmax_select([], temperature=1.0, seed=0)
    with pytest.raises(ValueError):
        aios_evolve.gumbel_softmax_select([0.5], temperature=0.0, seed=0)


# ── (v) Sinkhorn: target marginals reached, collapse prevented ───────────────

def test_sinkhorn_reaches_marginals_and_prevents_collapse():
    # Degenerate input: one column dominates both rows — naive normalization
    # would put ~all mass on column 0 ("keep only the winner").
    matrix = [[10.0, 0.0, 0.0], [10.0, 0.0, 0.0]]
    sk = aios_evolve.sinkhorn_normalize(matrix, iters=500, epsilon=1.0)
    out = sk["matrix"]
    nrows, ncols = 2, 3
    assert sk["col_target"] == pytest.approx(nrows / ncols)
    for row in out:
        assert sum(row) == pytest.approx(1.0, abs=1e-6)
    col_sums = [sum(out[r][c] for r in range(nrows)) for c in range(ncols)]
    for s in col_sums:
        assert s == pytest.approx(nrows / ncols, abs=1e-6)
    # anti-collapse: the dominant column was forced to share mass
    assert max(col_sums) - min(col_sums) < 1e-6
    assert sk["row_dev"] < 1e-6 and sk["col_dev"] < 1e-6

    with pytest.raises(ValueError):
        aios_evolve.sinkhorn_normalize([], iters=10, epsilon=0.1)
    with pytest.raises(ValueError):
        aios_evolve.sinkhorn_normalize([[1.0], [1.0, 2.0]], iters=10, epsilon=0.1)
    with pytest.raises(ValueError):
        aios_evolve.sinkhorn_normalize([[1.0]], iters=10, epsilon=0.0)


# ── (vi) evolve: lineage append-only, both verdicts, propose-never-promote ───

@needs_sandbox
def test_evolve_lineage_append_only_with_both_verdicts(paths):
    report = _evolve(paths)
    assert report["status"] == "ok"
    assert report["candidates_evaluated"] >= 2

    records = aios_evolve.read_lineage(paths["lineage"])
    verdicts = {r["verdict"] for r in records if r.get("kind") == "candidate"}
    assert "pass" in verdicts and "fail" in verdicts, \
        "lineage must carry BOTH verdicts"
    cand_records = [r for r in records if r.get("kind") == "candidate"]
    assert all(r["parent_hash"] and r["candidate_hash"] for r in cand_records)
    assert any(r["selected"] for r in cand_records), "a survivor was selected"

    # proposals: only full external passes, and NEVER auto-registered
    assert report["proposals"], "the x + x repair must be proposed"
    for p in report["proposals"]:
        assert p["fitness"] == 1.0
        assert "NOT registered" in p["registration"]
        assert "aios_skills.register" in p["registration"]
    retention = [r for r in records if r.get("kind") == "retention"]
    assert retention and all(r["proposed"] for r in retention)

    # append-only: a second run only ever EXTENDS the file
    content_1 = paths["lineage"].read_text(encoding="utf-8")
    report_2 = _evolve(paths)
    content_2 = paths["lineage"].read_text(encoding="utf-8")
    assert content_2.startswith(content_1), "lineage must be append-only"
    assert len(content_2) > len(content_1)
    assert report_2["status"] == "ok"


@needs_sandbox
def test_evolve_report_numbers_are_real(paths):
    report = _evolve(paths)
    dist = report["fitness_distribution"]
    assert dist and dist[0] == 1.0 and dist[-1] == 0.0
    assert report["mean_robustness"] is not None
    assert report["selected_final"]["candidate_hash"]
    assert set(report["roles"]) == {"generator", "verifier", "scorer"}
    summary = aios_evolve.summarize_lineage(
        aios_evolve.read_lineage(paths["lineage"]))
    assert summary["candidate_records"] == report["candidates_evaluated"]
    row = summary["per_substrate"][0]
    assert row["origin"] == "offline-perturb"
    assert 0.0 < row["survival_rate"] < 1.0
    assert summary["diversity_retained"]["origins_retained"] == ["offline-perturb"]


def _row(origin, h, combined):
    return {"candidate": {"origin": origin, "hash": h}, "combined": combined}


def test_select_retained_single_group_tie_breaks_on_raw_score():
    # Live-run findings (2026-07-27): with ONE group the Sinkhorn 1xN balanced
    # matrix is uniform, so without the raw-score tie-break the FIRST index
    # was retained; worse, the uniformity holds only up to ~1e-17 FP residue
    # from column scaling, which INVERTED a naive lexicographic tie-break.
    # These are the EXACT combined scores from the second live NIM round.
    c = 0.9285714285714286
    rows = [_row("nim", "aaa", c), _row("nim", "bbb", c), _row("nim", "ccc", c),
            _row("nim", "ddd", c), _row("nim", "eee", 1.0)]
    retained, sk = aios_evolve.select_retained(rows)
    assert retained == [4], "the most robust candidate must win the tie"
    assert sk is not None
    assert aios_evolve.select_retained([]) == ([], None)


def test_select_retained_keeps_one_per_group_not_winner_take_all():
    # A dominant group must not sweep retention: each origin group retains
    # its own best (the Sinkhorn anti-degeneracy role).
    rows = [_row("nim", "n1", 1.0), _row("nim", "n2", 0.99),
            _row("offline-perturb", "o1", 0.6),
            _row("offline-perturb", "o2", 0.55)]
    retained, _ = aios_evolve.select_retained(rows)
    origins = {rows[j]["candidate"]["origin"] for j in retained}
    assert origins == {"nim", "offline-perturb"}
    hashes = {rows[j]["candidate"]["hash"] for j in retained}
    assert hashes == {"n1", "o1"}, "each group retains its best member"


# ── (vii) sandbox unavailable -> refuse to evaluate (nothing executed) ───────

def test_sandbox_unavailable_refuses_everything(paths, monkeypatch):
    monkeypatch.setenv("AIOS_SANDBOX_ENGINE", "none")
    cand = aios_evolve.make_candidate(
        "def double(x):\n    return x + x\n", ARTIFACT)

    fit = aios_evolve.fitness([cand], sandbox_timeout=5.0,
                              now=NOW, receipt_log=paths["receipt_log"])
    assert fit["refused"] is True
    (r,) = fit["results"]
    assert r["verdict"] == "refused_sandbox_unavailable"
    assert r["fitness"] is None and r["ran"] is False

    rob = aios_evolve.contrastive_robustness(
        cand, k=4, sandbox_timeout=5.0, now=NOW,
        receipt_log=paths["receipt_log"])
    assert rob["verdict"] == "refused_sandbox_unavailable"
    assert rob["robustness"] is None and rob["probes_run"] == 0

    report = _evolve(paths)
    assert report["status"] == "refused_sandbox_unavailable"
    assert report["proposals"] == [] and report["candidates_evaluated"] == 0
    refusals = [r for r in aios_evolve.read_lineage(paths["lineage"])
                if r.get("kind") == "refusal"]
    assert refusals, "the refusal itself must be recorded in lineage"
    assert not paths["receipt_log"].exists(), "nothing was executed"


# ── (viii) unreachable substrate degrades honestly ───────────────────────────

def test_unreachable_substrate_degrades_honestly(monkeypatch):
    monkeypatch.setenv("AIOS_OLLAMA_BASE_URL", "http://127.0.0.1:9")  # refused
    gen = aios_evolve.generate_variants(ARTIFACT, 3, substrate="ollama",
                                        model="qwen3-coder:30b", now=NOW)
    assert len(gen["substrate_failures"]) == 1
    failure = gen["substrate_failures"][0]
    assert failure["substrate"] == "ollama" and failure["error"]
    assert gen["fallback_used"] is True
    assert gen["candidates"], "offline fallback keeps the organ operable"
    assert all(c["origin"] == "offline-perturb" for c in gen["candidates"]), \
        "an unreachable substrate must never be credited with candidates"


def test_generate_variants_validates_inputs():
    with pytest.raises(ValueError):
        aios_evolve.generate_variants({"code": "", "unit_test": "x"}, 3,
                                      substrate="offline", model=None, now=NOW)
    with pytest.raises(ValueError):
        aios_evolve.generate_variants(ARTIFACT, 0, substrate="offline",
                                      model=None, now=NOW)
    with pytest.raises(ValueError):
        aios_evolve.generate_variants(ARTIFACT, 3, substrate="warp-drive",
                                      model=None, now=NOW)


# --- regression: defect found by the operator's adversarial probe, not by the suite above ---
# _fuzz_probes did tuple(example) on EVERY example_inputs entry, so a scalar example (1)
# crashed with TypeError — killing the load-bearing fuzzing gate — and a string example
# ("abc") was silently exploded into per-character args, inflating arity so a correct
# candidate looked fragile. An example is an ARGUMENT TUPLE: only tuple/list is multi-arg.

def test_scalar_example_inputs_discriminate_overfit_from_honest():
    overfit = {"code": "def double(x):\n    return {1:2,2:4,3:6}[x]\n",
               "unit_test": "assert double(1)==2\nassert double(2)==4\nassert double(3)==6\n",
               "example_inputs": [1, 2, 3]}
    honest = {"code": "def double(x):\n    return x*2\n",
              "unit_test": "assert double(1)==2\nassert double(2)==4\nassert double(3)==6\n",
              "example_inputs": [1, 2, 3]}
    rob_overfit = aios_evolve.contrastive_robustness(overfit, k=8)
    rob_honest = aios_evolve.contrastive_robustness(honest, k=8)
    # both pass their OWN test at fitness 1.0; only input fuzzing separates them
    assert rob_overfit["fragile"] is True
    assert rob_honest["fragile"] is False
    assert rob_overfit["robustness"] < rob_honest["robustness"]


def test_string_example_is_one_argument_not_characters():
    cand = {"code": "def upper(s):\n    return s.upper()\n",
            "unit_test": "assert upper('ab')=='AB'\n",
            "example_inputs": ["ab", "xyz"]}
    rob = aios_evolve.contrastive_robustness(cand, k=6)
    assert rob["fragile"] is False
    assert rob["robustness"] == 1.0
