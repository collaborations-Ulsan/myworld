"""score.py — turns raw run outcomes into the pre-registered verdict.

Implements EXACTLY the KILL CRITERION / metric / ablation matrix pre-registered in README.md.
Input: results/runs.jsonl, an append-only JSONL of TaskOutcome dicts (contracts.py).

This module's honesty IS the experiment's integrity: no softening of K1/K2, no laundering of
a partial result into WITNESS or TAXONOMY (rule 5, both directions). Deterministic: stdlib +
numpy only, seeded bootstrap.

Statistical notes (implementation choices not pinned to a single number by the prose spec, made
explicit here so they are auditable):
  - The bootstrap resamples per-seed verified-solve counts (with replacement) and computes the
    MEDIAN of each resample, matching the median-based point estimates used throughout K1/K2.
    SE = std-dev of the bootstrap distribution of that statistic.
  - "pooled bootstrap SE" for a comparison between two quantities X and Y is
    sqrt(SE(X)^2 + SE(Y)^2) (standard pooled SE for an independent difference).
  - median(max(A_solves, B_solves)) is computed PAIRED BY SEED (elementwise max of A's and B's
    per-seed solve count for each seed present in both), then the median of that array is taken.
    If no seeds are shared between A and B, this falls back to max(median(A), median(B)) and the
    fallback is recorded in the verdict (`paired_by_seed: False`).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
from collections import defaultdict
from statistics import mean, median

import numpy as np

RUNS_PATH_DEFAULT = "results/runs.jsonl"
REPORT_PATH_DEFAULT = "results/REPORT.md"

ABLATION_NAMES = ["apex", "iris", "descent", "goen"]  # R2-R5, single-certificate rent
WRITEBACK_ABLATION = "writeback"  # R6, population coupling, reported separately


# ---------------------------------------------------------------------------
# 1. load_outcomes
# ---------------------------------------------------------------------------
def load_outcomes(path: str) -> list[dict]:
    """Read an append-only JSONL of TaskOutcome dicts. Blank lines are skipped."""
    outcomes: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            outcomes.append(json.loads(line))
    return outcomes


# ---------------------------------------------------------------------------
# helpers: arm/tier normalization
# ---------------------------------------------------------------------------
def _canonical_arm(row: dict) -> str:
    """Fold a TaskOutcome row's `arm` (+ optional `tier` key) into one canonical arm id.

    Tier-1 rows (the default): arm id is the raw arm string ("A", "B", "C", "C-ablate-apex", ...).
    Tier-2 rows: either `arm` already carries an "@t2" suffix, or a separate `tier` key is set —
    both fold to "<arm>@t2".
    """
    arm = row.get("arm", "")
    if "@t" in arm:
        return arm
    tier = row.get("tier", 1) or 1
    if tier != 1:
        return f"{arm}@t{tier}"
    return arm


# ---------------------------------------------------------------------------
# 2. summarize
# ---------------------------------------------------------------------------
def summarize(outcomes: list[dict]) -> dict:
    """Per (arm, seed) -> verified-solve count, plus raw solve-rate, submission precision,
    P0-subset solve count, mean tokens, mean wall_s. Also rolls each canonical arm up across
    its seeds into `by_arm`, which is what evaluate_killcriterion / write_report consume.
    """
    rows_by_key: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in outcomes:
        carm = _canonical_arm(row)
        seed = row.get("seed", 0)
        rows_by_key[(carm, seed)].append(row)

    per_arm_seed: dict[tuple[str, int], dict] = {}
    for key, rows in rows_by_key.items():
        carm, seed = key
        n = len(rows)
        submitted = sum(1 for r in rows if r.get("submitted"))
        verified = sum(1 for r in rows if r.get("verified"))
        p0_rows = [r for r in rows if r.get("poison_condition") == "P0"]
        p0_verified = sum(1 for r in p0_rows if r.get("verified"))
        tokens = [r.get("tokens", 0) for r in rows]
        wall = [r.get("wall_s", 0.0) for r in rows]
        per_arm_seed[key] = {
            "arm": carm,
            "seed": seed,
            "n_tasks": n,
            "verified_solves": verified,
            "submitted": submitted,
            "solve_rate": verified / n if n else 0.0,
            "precision": verified / submitted if submitted else 0.0,
            "p0_n_tasks": len(p0_rows),
            "p0_verified_solves": p0_verified,
            "p0_solve_rate": p0_verified / len(p0_rows) if p0_rows else 0.0,
            "mean_tokens": mean(tokens) if tokens else 0.0,
            "mean_wall_s": mean(wall) if wall else 0.0,
        }

    by_arm: dict[str, dict] = {}
    arm_ids = sorted({k[0] for k in rows_by_key})
    for carm in arm_ids:
        seed_entries = sorted(
            (per_arm_seed[k] for k in per_arm_seed if k[0] == carm), key=lambda e: e["seed"]
        )
        seeds = [e["seed"] for e in seed_entries]
        verified_solves = [e["verified_solves"] for e in seed_entries]
        all_rows = [r for r in outcomes if _canonical_arm(r) == carm]
        n_tasks_total = len(all_rows)
        verified_total = sum(1 for r in all_rows if r.get("verified"))
        submitted_total = sum(1 for r in all_rows if r.get("submitted"))
        p0_rows_total = [r for r in all_rows if r.get("poison_condition") == "P0"]
        p0_verified_total = sum(1 for r in p0_rows_total if r.get("verified"))
        tokens_all = [r.get("tokens", 0) for r in all_rows]
        wall_all = [r.get("wall_s", 0.0) for r in all_rows]
        by_arm[carm] = {
            "arm": carm,
            "seeds": seeds,
            "verified_solves": verified_solves,
            "median_verified_solves": median(verified_solves) if verified_solves else 0.0,
            "n_tasks_total": n_tasks_total,
            "verified_total": verified_total,
            "solve_rate": verified_total / n_tasks_total if n_tasks_total else 0.0,
            "precision": verified_total / submitted_total if submitted_total else 0.0,
            "p0_n_tasks": len(p0_rows_total),
            "p0_verified_solves": p0_verified_total,
            "p0_solve_rate": p0_verified_total / len(p0_rows_total) if p0_rows_total else 0.0,
            "mean_tokens": mean(tokens_all) if tokens_all else 0.0,
            "mean_wall_s": mean(wall_all) if wall_all else 0.0,
        }

    return {"per_arm_seed": per_arm_seed, "by_arm": by_arm}


# ---------------------------------------------------------------------------
# 3. bootstrap_ci
# ---------------------------------------------------------------------------
def bootstrap_ci(values, iters: int = 10000, seed: int = 0) -> tuple[float, float, float]:
    """Deterministic (seeded numpy) bootstrap over per-seed solve counts.

    Resamples `values` with replacement `iters` times, computes the MEDIAN of each resample,
    and returns (lo, hi, se): the 95% percentile CI and the std-dev of the bootstrap statistic.
    """
    arr = np.asarray(list(values), dtype=float)
    n = arr.size
    if n == 0:
        return (0.0, 0.0, 0.0)
    if n == 1:
        v = float(arr[0])
        return (v, v, 0.0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(iters, n))
    resamples = arr[idx]
    stat = np.median(resamples, axis=1)
    lo, hi = np.percentile(stat, [2.5, 97.5])
    se = float(np.std(stat, ddof=1))
    return (float(lo), float(hi), se)


def _pooled_se(values_a, values_b, iters: int = 10000, seed: int = 0) -> float:
    _, _, se_a = bootstrap_ci(values_a, iters=iters, seed=seed)
    _, _, se_b = bootstrap_ci(values_b, iters=iters, seed=seed + 1)
    return math.sqrt(se_a**2 + se_b**2)


def _paired_max(by_arm: dict, arm_a: str, arm_b: str):
    """Elementwise max(A,B) paired by seed. Falls back to pooling both arms' values if the two
    arms share no seeds (paired=False in that case)."""
    ea, eb = by_arm.get(arm_a), by_arm.get(arm_b)
    if not ea or not eb:
        return [], False
    map_a = dict(zip(ea["seeds"], ea["verified_solves"]))
    map_b = dict(zip(eb["seeds"], eb["verified_solves"]))
    common = sorted(set(map_a) & set(map_b))
    if common:
        return [max(map_a[s], map_b[s]) for s in common], True
    return ea["verified_solves"] + eb["verified_solves"], False


# ---------------------------------------------------------------------------
# 4. evaluate_killcriterion — THE verdict
# ---------------------------------------------------------------------------
def evaluate_killcriterion(summary: dict, iters: int = 10000, seed: int = 0) -> dict:
    """Implements README's KILL CRITERION exactly:

      K1: median C_solves <= median(max(A_solves,B_solves)) + eps, eps = max(3, 1.64*pooled SE)
      K2: <=2 of the 4 single-cert ablations (apex/iris/descent/goen) degrade C by >2xSE
      WITNESS fires iff median C > median max(A,B) + eps  AND  all 4 ablations degrade C by >2xSE.
      R6 (-writeback) is reported SEPARATELY (population coupling), never part of the verdict.
      Tier-2 probe (R7): C-A at tier-1 vs tier-2; shrinkage = evidence for monolith absorption.

    Returns a dict: boolean verdict ("WITNESS" | "TAXONOMY" | "PARTIAL"), every number behind it,
    and `decided_by` naming which criterion decided. Missing arms/ablations are reported as
    PARTIAL with a warning rather than silently forcing a verdict — no laundering.
    """
    by_arm = summary["by_arm"]
    warnings: list[str] = []

    def get_arm(name):
        e = by_arm.get(name)
        if e is None:
            warnings.append(f"missing arm data: {name}")
        return e

    A, B, C = get_arm("A"), get_arm("B"), get_arm("C")
    if A is None or B is None or C is None:
        return {
            "verdict": "PARTIAL",
            "decided_by": "insufficient data: A, B, and C (R1) must all be present",
            "warnings": warnings,
        }

    median_A = A["median_verified_solves"]
    median_B = B["median_verified_solves"]
    median_C = C["median_verified_solves"]

    max_ab_values, paired = _paired_max(by_arm, "A", "B")
    median_max_ab = median(max_ab_values) if max_ab_values else max(median_A, median_B)

    se_pooled_k1 = _pooled_se(
        C["verified_solves"], max_ab_values or [median_A, median_B], iters=iters, seed=seed
    )
    epsilon = max(3.0, 1.64 * se_pooled_k1)

    k1_fires = median_C <= median_max_ab + epsilon
    witness_median_condition = median_C > median_max_ab + epsilon

    ablation_details: dict[str, dict] = {}
    degrade_count = 0
    for i, name in enumerate(ABLATION_NAMES):
        e = get_arm(f"C-ablate-{name}")
        if e is None:
            ablation_details[name] = {"available": False}
            continue
        median_abl = e["median_verified_solves"]
        se_pool = _pooled_se(C["verified_solves"], e["verified_solves"], iters=iters, seed=seed + 10 + i)
        delta = median_C - median_abl
        degrade = delta > 2 * se_pool
        if degrade:
            degrade_count += 1
        ablation_details[name] = {
            "available": True,
            "median_C": median_C,
            "median_ablation": median_abl,
            "delta": delta,
            "pooled_se": se_pool,
            "threshold_2se": 2 * se_pool,
            "degrade": degrade,
        }

    n_available_ablations = sum(1 for v in ablation_details.values() if v.get("available"))
    k2_conclusive = n_available_ablations == 4
    k2_fires = k2_conclusive and degrade_count <= 2
    witness_fires = witness_median_condition and k2_conclusive and degrade_count == 4

    if witness_fires:
        verdict = "WITNESS"
        decided_by = (
            "witness: median(C) beats median(max(A,B))+epsilon AND all 4/4 single-cert "
            "ablations degrade C by >2xSE"
        )
    elif not k2_conclusive:
        if k1_fires:
            verdict, decided_by = "TAXONOMY", "K1: median(C) <= median(max(A,B)) + epsilon"
        else:
            verdict = "PARTIAL"
            decided_by = (
                f"insufficient ablation coverage ({n_available_ablations}/4 run) and K1 did not "
                "fire — cannot conclude WITNESS or TAXONOMY yet"
            )
    else:
        if k1_fires:
            verdict, decided_by = "TAXONOMY", "K1: median(C) <= median(max(A,B)) + epsilon"
        elif k2_fires:
            verdict = "TAXONOMY"
            decided_by = (
                f"K2: only {degrade_count}/4 single-cert ablations degrade C by >2xSE "
                "(composition is decoration)"
            )
        else:
            verdict = "PARTIAL"
            decided_by = (
                f"K1 did not fire (C beats max(A,B)) but only {degrade_count}/4 ablations "
                "degrade C by >2xSE — not a full witness, reported straight as partial"
            )

    # R6 write-back: population coupling, reported separately, NEVER part of the verdict above.
    r6_arm = get_arm(f"C-ablate-{WRITEBACK_ABLATION}")
    r6_result = None
    if r6_arm is not None:
        median_r6 = r6_arm["median_verified_solves"]
        se_r6 = _pooled_se(C["verified_solves"], r6_arm["verified_solves"], iters=iters, seed=seed + 20)
        r6_result = {
            "median_C": median_C,
            "median_ablation": median_r6,
            "delta": median_C - median_r6,
            "pooled_se": se_r6,
            "threshold_2se": 2 * se_r6,
            "degrade": (median_C - median_r6) > 2 * se_r6,
        }

    # Tier-2 absorption probe (R7): C-A at tier-1 vs tier-2.
    A2, C2 = by_arm.get("A@t2"), by_arm.get("C@t2")
    tier2_probe = None
    if A2 is not None and C2 is not None:
        tier1_delta = median_C - median_A
        tier2_delta = C2["median_verified_solves"] - A2["median_verified_solves"]
        shrinkage = tier1_delta - tier2_delta
        tier2_probe = {
            "tier1_C_minus_A": tier1_delta,
            "tier2_C_minus_A": tier2_delta,
            "shrinkage": shrinkage,
            "absorption_evidence": shrinkage > 0 and tier1_delta > 0,
        }

    return {
        "verdict": verdict,
        "decided_by": decided_by,
        "epsilon": epsilon,
        "se_pooled_k1": se_pooled_k1,
        "median_A": median_A,
        "median_B": median_B,
        "median_C": median_C,
        "median_max_AB": median_max_ab,
        "paired_by_seed": paired,
        "k1_fires": k1_fires,
        "witness_median_condition": witness_median_condition,
        "ablations": ablation_details,
        "degrade_count": degrade_count,
        "n_available_ablations": n_available_ablations,
        "k2_fires": k2_fires,
        "k2_conclusive": k2_conclusive,
        "witness_fires": witness_fires,
        "R6_writeback": r6_result,
        "tier2_probe": tier2_probe,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# 5. write_report
# ---------------------------------------------------------------------------
def _conclusion_paragraph(verdict: dict) -> str:
    v = verdict["verdict"]
    if v == "WITNESS":
        return (
            f"The pre-registered kill criterion did NOT fire: median verified solves for the "
            f"coupled arm C ({verdict['median_C']:.1f}) exceeded median(max(A,B)) "
            f"({verdict['median_max_AB']:.2f}) by more than epsilon ({verdict['epsilon']:.2f}), "
            f"and all {verdict['degrade_count']}/4 single-certificate ablations degraded C by "
            f"more than 2x bootstrap SE. This is an honest existence-witness for cross-component "
            f"coupling producing emergent value beyond independent certificates, at this regime "
            f"and this token budget — prevalence beyond this setting is still owed, not claimed "
            f"here."
        )
    if v == "TAXONOMY":
        return (
            f"The pre-registered kill criterion FIRED ({verdict['decided_by']}). Under this "
            f"regime and budget, the coupled arm C does not clear the bar for coupling to be "
            f"more than a taxonomy: either composition failed to beat max(A,B) by more than "
            f"epsilon, or too few single-certificate ablations moved C's score. This is reported "
            f"as an earned negative for cross-component coupling in this setting — not laundered "
            f"into a partial or a positive."
        )
    return (
        f"Neither the WITNESS nor the TAXONOMY condition is fully established ({verdict.get('decided_by')}). "
        f"This is reported straight as PARTIAL: the evidence so far is incomplete or mixed — e.g. "
        f"not all ablations have run yet, or C beats max(A,B) but only some single-certificate "
        f"ablations show the expected rent. No laundering in either direction: this is neither a "
        f"positive nor a negative claim until the missing runs land or the mixed pattern resolves."
    )


def write_report(summary: dict, verdict: dict, path: str = REPORT_PATH_DEFAULT) -> str:
    by_arm = summary["by_arm"]
    lines: list[str] = []

    lines.append("# AGI Certification-Layer Witness — Result Report")
    lines.append("")
    lines.append(f"**VERDICT: {verdict['verdict']}**")
    lines.append("")
    lines.append(f"Decided by: {verdict.get('decided_by')}")
    lines.append("")
    if verdict.get("warnings"):
        lines.append("Warnings: " + "; ".join(verdict["warnings"]))
        lines.append("")

    lines.append("## A / B / C — primary comparison (R1)")
    lines.append("")
    lines.append(
        "| arm | median verified solves | 95% CI (bootstrap) | SE | solve rate | precision "
        "| mean tokens | mean wall_s |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for arm in ["A", "B", "C"]:
        e = by_arm.get(arm)
        if e is None:
            lines.append(f"| {arm} | - | - | - | - | - | - | - |")
            continue
        lo, hi, se = bootstrap_ci(e["verified_solves"])
        lines.append(
            f"| {arm} | {e['median_verified_solves']:.1f} | [{lo:.2f}, {hi:.2f}] | {se:.3f} "
            f"| {e['solve_rate']:.3f} | {e['precision']:.3f} | {e['mean_tokens']:.1f} "
            f"| {e['mean_wall_s']:.3f} |"
        )
    lines.append("")
    lines.append(
        f"median(max(A,B)) = {verdict.get('median_max_AB', float('nan')):.2f} "
        f"(paired by seed: {verdict.get('paired_by_seed')})"
    )
    lines.append(
        f"epsilon = max(3, 1.64 x pooled bootstrap SE) = {verdict.get('epsilon', float('nan')):.3f}"
    )
    lines.append("")

    lines.append("## Ablations (R2-R5) - single-certificate rent")
    lines.append("")
    lines.append("| ablation | median C | median ablation | delta | 2xSE threshold | degrades C? |")
    lines.append("|---|---|---|---|---|---|")
    for name in ABLATION_NAMES:
        d = verdict.get("ablations", {}).get(name, {"available": False})
        if not d.get("available"):
            lines.append(f"| -{name} | - | - | - | - | not run |")
            continue
        lines.append(
            f"| -{name} | {d['median_C']:.1f} | {d['median_ablation']:.1f} | {d['delta']:.2f} "
            f"| {d['threshold_2se']:.3f} | {'YES' if d['degrade'] else 'no'} |"
        )
    lines.append("")
    lines.append(
        f"{verdict.get('degrade_count', 0)}/{verdict.get('n_available_ablations', 0)} run "
        "ablations degrade C by >2xSE."
    )
    lines.append("")

    lines.append(
        "## R6 - write-back ablation (population coupling, reported separately, NOT part of the verdict)"
    )
    lines.append("")
    r6 = verdict.get("R6_writeback")
    if r6:
        lines.append(
            f"median C = {r6['median_C']:.1f}, median C-ablate-writeback = "
            f"{r6['median_ablation']:.1f}, delta = {r6['delta']:.2f}, 2xSE = "
            f"{r6['threshold_2se']:.3f}, degrades C? {'YES' if r6['degrade'] else 'no'}"
        )
    else:
        lines.append("R6 not run.")
    lines.append("")

    lines.append("## P0-subset (pure verification-tax isolation)")
    lines.append("")
    lines.append("| arm | P0 verified solves | P0 n tasks | P0 solve rate |")
    lines.append("|---|---|---|---|")
    for arm in ["A", "B", "C"]:
        e = by_arm.get(arm)
        if e is None:
            continue
        lines.append(f"| {arm} | {e['p0_verified_solves']} | {e['p0_n_tasks']} | {e['p0_solve_rate']:.3f} |")
    lines.append("")

    lines.append("## Tier-2 absorption probe (R7)")
    lines.append("")
    t2 = verdict.get("tier2_probe")
    if t2:
        lines.append(
            f"tier-1 C-A = {t2['tier1_C_minus_A']:.2f}; tier-2 C-A = {t2['tier2_C_minus_A']:.2f}; "
            f"shrinkage = {t2['shrinkage']:.2f}; absorption evidence: "
            f"{'YES' if t2['absorption_evidence'] else 'no'}"
        )
    else:
        lines.append("Tier-2 (R7) not run.")
    lines.append("")

    lines.append("## Honest conclusion")
    lines.append("")
    lines.append(_conclusion_paragraph(verdict))
    lines.append("")

    text = "\n".join(lines)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return text


# ---------------------------------------------------------------------------
# Self-test: fabricate a synthetic results/runs.jsonl for two scenarios and assert the verdict.
# ---------------------------------------------------------------------------
def _det_seed(*parts) -> int:
    """Deterministic integer seed from arbitrary parts (avoids relying on randomized hash())."""
    s = "|".join(str(p) for p in parts)
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def _make_row(task_id, arm, seed, submitted, verified, tokens, wall_s=1.0, poison="P0", tier=None):
    row = {
        "task_id": task_id,
        "arm": arm,
        "seed": seed,
        "submitted": submitted,
        "verified": verified,
        "tokens": tokens,
        "wall_s": wall_s,
        "poison_condition": poison,
        "note": "",
    }
    if tier is not None:
        row["tier"] = tier
    return row


def _synth_arm_rows(scenario, arm_label, rate, seeds, n_tasks=40, tier=None):
    rows = []
    for seed in seeds:
        r = random.Random(_det_seed(scenario, arm_label, seed, tier))
        for i in range(n_tasks):
            submitted = r.random() < 0.9
            verified = submitted and (r.random() < rate)
            poison = "P0" if i < n_tasks // 2 else ("P1" if i < (3 * n_tasks) // 4 else "P2")
            tokens = r.randint(400, 900)
            rows.append(
                _make_row(f"task{i:03d}", arm_label, seed, submitted, verified, tokens, poison=poison, tier=tier)
            )
    return rows


def _synth_scenario(scenario: str) -> list[dict]:
    seeds = [0, 1, 2]
    if scenario == "witness":
        rate_A, rate_B, rate_C = 0.30, 0.33, 0.80
        ablation_rates = {"apex": 0.35, "iris": 0.30, "descent": 0.32, "goen": 0.38}
        writeback_rate = 0.55
        tier2_A_rate, tier2_C_rate = rate_A, 0.40  # tier-2 shrinks the C-A gap materially
    else:  # taxonomy: C barely differs from max(A,B); ablations don't move C
        rate_A, rate_B, rate_C = 0.55, 0.50, 0.56
        ablation_rates = {"apex": 0.55, "iris": 0.54, "descent": 0.56, "goen": 0.55}
        writeback_rate = 0.55
        tier2_A_rate, tier2_C_rate = rate_A, rate_C

    rows: list[dict] = []
    rows += _synth_arm_rows(scenario, "A", rate_A, seeds)
    rows += _synth_arm_rows(scenario, "B", rate_B, seeds)
    rows += _synth_arm_rows(scenario, "C", rate_C, seeds)
    for name, rate in ablation_rates.items():
        rows += _synth_arm_rows(scenario, f"C-ablate-{name}", rate, seeds[:2])
    rows += _synth_arm_rows(scenario, "C-ablate-writeback", writeback_rate, seeds[:2])
    # R7: tier-2 monolith-absorption probe (single seed, per README's ablation matrix).
    rows += _synth_arm_rows(scenario, "A", tier2_A_rate, [0], tier=2)
    rows += _synth_arm_rows(scenario, "C", tier2_C_rate, [0], tier=2)
    return rows


if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)

    for scenario, expected_verdict in (("witness", "WITNESS"), ("taxonomy", "TAXONOMY")):
        rows = _synth_scenario(scenario)
        with open(RUNS_PATH_DEFAULT, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

        outcomes = load_outcomes(RUNS_PATH_DEFAULT)
        summary = summarize(outcomes)
        verdict = evaluate_killcriterion(summary)
        report_text = write_report(summary, verdict, path=REPORT_PATH_DEFAULT)

        print("=" * 80)
        print(f"SCENARIO: {scenario}  ->  VERDICT: {verdict['verdict']}")
        print("=" * 80)
        print(report_text)
        print()

        assert verdict["verdict"] == expected_verdict, (
            f"scenario '{scenario}': expected verdict {expected_verdict}, got {verdict['verdict']} "
            f"(decided_by: {verdict['decided_by']})"
        )

    print("Self-test PASSED: synthetic WITNESS scenario -> WITNESS, synthetic TAXONOMY scenario -> TAXONOMY.")
