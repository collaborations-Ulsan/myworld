"""AIOS-DriftBench-mini analysis script (pre-registered per pre-reg SS4/SS6).

Deterministic given a results file: reads a ResultRow table (schema.py), computes the
SS5 WIN/STOP verdict block, and nothing else. This script's own sha256 (computed once at
freeze time and recorded in the pre-reg Errata per SS6) is part of what gets frozen
before the first run -- see docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md SS6.

AMBIGUITY FLAGS (resolved here, not silently):

1. **Trace schema.** SS5 condition 4 (trace causal rule) needs a trace EVENT schema the
   pre-reg does not define (it only says "전체 trace 캡처"). This module defines a
   minimal JSONL schema (`TraceEvent` / `load_trace` below) sufficient to run the
   <=5-action causal-precedence check. Any real arm-runner MUST emit traces in this
   shape for condition 4 to be computable; if a row's trace_path is missing/unreadable
   this module reports condition 4 as "insufficient_trace_data" rather than guessing
   pass or fail.

2. **Condition-4 threshold.** SS5 names the per-instance causal rule but not what
   FRACTION of credited wins must satisfy it for the overall condition to pass. This
   module takes the strict reading: ALL credited wins (weak+AIOS beats weak+checklist
   on a mutating instance) must show a trace-verified causal recovery. Anything less
   would silently credit some paired wins with unverified causal provenance. If a
   future re-read of the pre-reg intends a softer threshold, that is a pre-reg Errata
   change, not a silent edit here.

3. **Cost definition (condition 2).** The pre-reg says only "총비용" (total cost)
   without pinning tokens vs wall-clock vs a composite $ figure. This module uses
   `ResultRow.tokens` as the cost proxy (the most common LLM-cost unit) and reports
   wall_seconds separately for transparency. A real run should pin the canonical cost
   definition in the Errata before treating this sub-check as binding.

4. **Three-way verdict.** SS5 names exactly two outcomes, WIN (all 4 conditions) and
   STOP (condition 1 fails in the specific documented way: <13/18 AND McNemar
   non-significant). It does not name what to print when condition 1 passes but a LATER
   condition (2/3/4) fails. This module reports that case as "MIXED" with the exact
   failing condition(s) named, rather than silently forcing it into WIN or STOP.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from schema import MUTATING_TEMPLATES, STATIC_TEMPLATES, ResultRow, read_table

ALPHA = 0.05
WRONG_COST_SWEEP = (3, 5, 10, 20)
GAP_CLOSURE_THRESHOLD = 0.5
STATIC_MARGIN_INSTANCES = 1  # |Delta successes (count)| <= 1 over the 6 static instances (= 1/6 margin)
BOOTSTRAP_ITERS = 10000
BOOTSTRAP_SEED = 20260711  # frozen, deterministic (pre-reg SS4: "seeded")
MAX_RECOVERY_LAG_ACTIONS = 5  # SS5 condition 4: recovery must follow trigger within <=5 actions
CONDITION1_MIN_WINS = 13
CONDITION1_MIN_INSTANCES = 18


# ---------------------------------------------------------------------------
# Exact one-sided McNemar (binomial), stdlib-only (math.comb)
# ---------------------------------------------------------------------------
def binom_sf_ge(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k) for X ~ Binomial(n, p), exact via math.comb. n is small in this design
    (<=18 discordant pairs at most on the confirmatory comparison), so this is exact and
    fast -- no normal approximation needed."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


@dataclass
class McNemarResult:
    b: int  # discordant pairs where arm_a wins
    c: int  # discordant pairs where arm_b wins
    n_discordant: int
    p_value: float  # one-sided exact, P(X >= b | n=b+c, p=0.5)
    significant: bool


def mcnemar_one_sided(wins_a: int, wins_b: int, *, alpha: float = ALPHA) -> McNemarResult:
    n = wins_a + wins_b
    p = binom_sf_ge(wins_a, n, 0.5) if n > 0 else 1.0
    return McNemarResult(b=wins_a, c=wins_b, n_discordant=n, p_value=p, significant=p < alpha)


# ---------------------------------------------------------------------------
# Paired wins on mutating instances only (pre-reg SS5: "동률은 win 아님")
# ---------------------------------------------------------------------------
@dataclass
class PairedComparison:
    arm_a: str
    arm_b: str
    n_instances: int
    wins_a: int  # a succeeds, b fails
    wins_b: int  # b succeeds, a fails
    ties: int  # both succeed or both fail
    mcnemar: McNemarResult


def _index_by_instance(rows: list[ResultRow], arm: str, templates: tuple) -> dict:
    return {(r.template, r.seed): r for r in rows if r.arm == arm and r.template in templates}


def paired_comparison(
    rows: list[ResultRow], arm_a: str, arm_b: str, *, templates: tuple = MUTATING_TEMPLATES,
) -> PairedComparison:
    idx_a = _index_by_instance(rows, arm_a, templates)
    idx_b = _index_by_instance(rows, arm_b, templates)
    keys = sorted(set(idx_a) & set(idx_b))
    wins_a = wins_b = ties = 0
    for key in keys:
        sa = idx_a[key].binary_success
        sb = idx_b[key].binary_success
        if sa and not sb:
            wins_a += 1
        elif sb and not sa:
            wins_b += 1
        else:
            ties += 1
    mc = mcnemar_one_sided(wins_a, wins_b)
    return PairedComparison(
        arm_a=arm_a, arm_b=arm_b, n_instances=len(keys),
        wins_a=wins_a, wins_b=wins_b, ties=ties, mcnemar=mc,
    )


# ---------------------------------------------------------------------------
# Gap-closure formula + denominator rule + paired bootstrap CI (SS5 condition 2)
# ---------------------------------------------------------------------------
@dataclass
class BootstrapCI:
    point: float
    lo: float
    hi: float
    n_iters: int


def _success_rate(rows: list[ResultRow], arm: str, templates: tuple) -> float:
    subset = [r for r in rows if r.arm == arm and r.template in templates]
    if not subset:
        return float("nan")
    return sum(1 for r in subset if r.binary_success) / len(subset)


def _paired_binary_by_instance(rows: list[ResultRow], arm: str, templates: tuple) -> dict:
    return {(r.template, r.seed): r.binary_success for r in rows if r.arm == arm and r.template in templates}


def bootstrap_success_rate_diff_ci(
    rows: list[ResultRow], arm_a: str, arm_b: str, *,
    templates: tuple = MUTATING_TEMPLATES, n_iters: int = BOOTSTRAP_ITERS, seed: int = BOOTSTRAP_SEED,
) -> BootstrapCI:
    """Paired bootstrap CI for S_a - S_b, resampling INSTANCES (template, seed pairs)
    with replacement -- the correct unit given the paired design (pre-reg SS5
    condition 2)."""
    a = _paired_binary_by_instance(rows, arm_a, templates)
    b = _paired_binary_by_instance(rows, arm_b, templates)
    keys = sorted(set(a) & set(b))
    n = len(keys)
    if n == 0:
        return BootstrapCI(point=float("nan"), lo=float("nan"), hi=float("nan"), n_iters=0)
    point = _success_rate(rows, arm_a, templates) - _success_rate(rows, arm_b, templates)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_iters):
        sample = [keys[rng.randrange(n)] for _ in range(n)]
        sa = sum(1 for k in sample if a[k]) / n
        sb = sum(1 for k in sample if b[k]) / n
        diffs.append(sa - sb)
    diffs.sort()
    lo = diffs[int(0.025 * n_iters)]
    hi = diffs[min(n_iters - 1, int(0.975 * n_iters))]
    return BootstrapCI(point=point, lo=lo, hi=hi, n_iters=n_iters)


def _bootstrap_gap_ratio_ci(
    rows: list[ResultRow], *, templates: tuple = MUTATING_TEMPLATES,
    n_iters: int = BOOTSTRAP_ITERS, seed: int = BOOTSTRAP_SEED,
) -> BootstrapCI:
    aios = _paired_binary_by_instance(rows, "weak+AIOS", templates)
    checklist = _paired_binary_by_instance(rows, "weak+checklist", templates)
    strong = _paired_binary_by_instance(rows, "strong-raw", templates)
    keys = sorted(set(aios) & set(checklist) & set(strong))
    n = len(keys)
    if n == 0:
        return BootstrapCI(point=float("nan"), lo=float("nan"), hi=float("nan"), n_iters=0)
    s_aios0 = sum(aios[k] for k in keys) / n
    s_checklist0 = sum(checklist[k] for k in keys) / n
    s_strong0 = sum(strong[k] for k in keys) / n
    denom0 = s_strong0 - s_checklist0
    point = (s_aios0 - s_checklist0) / denom0 if denom0 else float("nan")
    rng = random.Random(seed)
    values = []
    for _ in range(n_iters):
        sample = [keys[rng.randrange(n)] for _ in range(n)]
        sa = sum(aios[k] for k in sample) / n
        sc = sum(checklist[k] for k in sample) / n
        ss = sum(strong[k] for k in sample) / n
        denom = ss - sc
        if denom == 0:
            continue  # skip degenerate resamples rather than divide by zero
        values.append((sa - sc) / denom)
    if not values:
        return BootstrapCI(point=point, lo=float("nan"), hi=float("nan"), n_iters=0)
    values.sort()
    m = len(values)
    lo = values[int(0.025 * m)]
    hi = values[min(m - 1, int(0.975 * m))]
    return BootstrapCI(point=point, lo=lo, hi=hi, n_iters=m)


@dataclass
class GapClosureResult:
    mode: str  # "ratio" | "fallback_s_aios_ge_s_strong"
    s_aios: float
    s_checklist: float
    s_strong: float
    value: float  # the ratio, or (s_aios - s_strong) in fallback mode
    ci: BootstrapCI
    passes: bool
    denominator_degenerate: bool


def gap_closure(rows: list[ResultRow], *, templates: tuple = MUTATING_TEMPLATES) -> GapClosureResult:
    s_aios = _success_rate(rows, "weak+AIOS", templates)
    s_checklist = _success_rate(rows, "weak+checklist", templates)
    s_strong = _success_rate(rows, "strong-raw", templates)
    denom = s_strong - s_checklist
    if denom > 0:
        value = (s_aios - s_checklist) / denom
        ci = _bootstrap_gap_ratio_ci(rows, templates=templates)
        passes = (not math.isnan(value)) and value > GAP_CLOSURE_THRESHOLD and (not math.isnan(ci.lo)) and ci.lo > 0
        return GapClosureResult("ratio", s_aios, s_checklist, s_strong, value, ci, passes, False)
    # Denominator <= 0 (strong-raw <= checklist): fall back to S_AIOS >= S_strong, same CI rule.
    ci = bootstrap_success_rate_diff_ci(rows, "weak+AIOS", "strong-raw", templates=templates)
    value = s_aios - s_strong
    passes = (not math.isnan(value)) and value >= 0 and (not math.isnan(ci.lo)) and ci.lo > 0
    return GapClosureResult("fallback_s_aios_ge_s_strong", s_aios, s_checklist, s_strong, value, ci, passes, True)


def _total_tokens(rows: list[ResultRow], arm: str, templates: tuple) -> dict:
    return {(r.template, r.seed): r.tokens for r in rows if r.arm == arm and r.template in templates}


def cost_ci_condition(
    rows: list[ResultRow], *, templates: tuple = MUTATING_TEMPLATES,
    n_iters: int = BOOTSTRAP_ITERS, seed: int = BOOTSTRAP_SEED,
) -> BootstrapCI:
    """CI for (cost_AIOS - cost_strong) in tokens (see AMBIGUITY FLAG 3 above); condition
    2's cost check passes when this CI's upper bound is < 0 (AIOS strictly cheaper)."""
    aios = _total_tokens(rows, "weak+AIOS", templates)
    strong = _total_tokens(rows, "strong-raw", templates)
    keys = sorted(set(aios) & set(strong))
    n = len(keys)
    if n == 0:
        return BootstrapCI(point=float("nan"), lo=float("nan"), hi=float("nan"), n_iters=0)
    point = (sum(aios.values()) - sum(strong.values())) / n
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_iters):
        sample = [keys[rng.randrange(n)] for _ in range(n)]
        diffs.append(sum(aios[k] - strong[k] for k in sample) / n)
    diffs.sort()
    lo = diffs[int(0.025 * n_iters)]
    hi = diffs[min(n_iters - 1, int(0.975 * n_iters))]
    return BootstrapCI(point=point, lo=lo, hi=hi, n_iters=n_iters)


@dataclass
class Condition2Result:
    gap: GapClosureResult
    cost: BootstrapCI
    cost_passes: bool
    passes: bool


def condition2(rows: list[ResultRow]) -> Condition2Result:
    gap = gap_closure(rows)
    cost = cost_ci_condition(rows)
    cost_passes = (not math.isnan(cost.hi)) and cost.hi < 0
    return Condition2Result(gap=gap, cost=cost, cost_passes=cost_passes, passes=(gap.passes and cost_passes))


# ---------------------------------------------------------------------------
# Static equivalence-margin guard (SS5 condition 3)
# ---------------------------------------------------------------------------
@dataclass
class StaticGuardResult:
    delta_successes: int
    within_margin: bool
    unsupported_claim_rate_aios: float
    unsupported_claim_rate_checklist: float
    no_unsupported_increase: bool
    passes: bool


def static_equivalence_guard(rows: list[ResultRow], *, margin: int = STATIC_MARGIN_INSTANCES) -> StaticGuardResult:
    aios = [r for r in rows if r.arm == "weak+AIOS" and r.template in STATIC_TEMPLATES]
    checklist = [r for r in rows if r.arm == "weak+checklist" and r.template in STATIC_TEMPLATES]
    succ_a = sum(1 for r in aios if r.binary_success)
    succ_c = sum(1 for r in checklist if r.binary_success)
    delta = abs(succ_a - succ_c)
    within = delta <= margin
    rate_a = (sum(r.unsupported_claims for r in aios) / len(aios)) if aios else float("nan")
    rate_c = (sum(r.unsupported_claims for r in checklist) / len(checklist)) if checklist else float("nan")
    no_increase = (not math.isnan(rate_a)) and (not math.isnan(rate_c)) and rate_a <= rate_c
    return StaticGuardResult(delta, within, rate_a, rate_c, no_increase, within and no_increase)


# ---------------------------------------------------------------------------
# Cost-model sweep (H2, secondary -- pre-reg SS4/SS5)
# ---------------------------------------------------------------------------
@dataclass
class CostSweepPoint:
    wrong_cost: int
    cost_aios: float
    cost_checklist: float
    aios_dominates: bool  # lower cost is better


def cost_model_total(row: ResultRow, wrong_cost: int) -> float:
    """pre-reg SS4 H2 cost model: wrong in {3,5,10,20}, ask=abstain=1, correct=0.
    "correct" actions are implicit (actions_used minus the priced categories) and
    contribute 0 -- only wrong/ask/abstain are priced."""
    return row.wrong_actions * wrong_cost + row.asks * 1 + row.abstains * 1


def cost_sweep(
    rows: list[ResultRow], *, templates: tuple = MUTATING_TEMPLATES, wrong_costs: tuple = WRONG_COST_SWEEP,
) -> list[CostSweepPoint]:
    points = []
    for wc in wrong_costs:
        aios_rows = [r for r in rows if r.arm == "weak+AIOS" and r.template in templates]
        checklist_rows = [r for r in rows if r.arm == "weak+checklist" and r.template in templates]
        cost_a = sum(cost_model_total(r, wc) for r in aios_rows) / len(aios_rows) if aios_rows else float("nan")
        cost_c = sum(cost_model_total(r, wc) for r in checklist_rows) / len(checklist_rows) if checklist_rows else float("nan")
        dominates = (not math.isnan(cost_a)) and (not math.isnan(cost_c)) and cost_a <= cost_c
        points.append(CostSweepPoint(wc, cost_a, cost_c, dominates))
    return points


def h2_holds(points: list[CostSweepPoint]) -> bool:
    """pre-reg SS5: H2 holds only if the gated arm dominates across the WHOLE sweep."""
    return bool(points) and all(p.aios_dominates for p in points)


# ---------------------------------------------------------------------------
# Trace causal rule (SS5 condition 4) -- see AMBIGUITY FLAGS 1 and 2 above.
# ---------------------------------------------------------------------------
@dataclass
class TraceEvent:
    step: int
    type: str  # "gate_reject" | "drift_detected" | "rollback" | "checkpoint_result" | ...
    checkpoint_id: Optional[str] = None
    passed: Optional[bool] = None
    detail: str = ""


def load_trace(path) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    p = Path(path) if path else None
    if p is None or not p.exists():
        return events
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(TraceEvent(**json.loads(line)))
    return events


TRIGGER_EVENT_TYPES = frozenset({"gate_reject", "drift_detected", "rollback"})


@dataclass
class CausalCheckResult:
    status: str  # "verified" | "not_verified" | "insufficient_trace_data"
    detail: str


def causal_recovery_check(events: list[TraceEvent], *, max_lag: int = MAX_RECOVERY_LAG_ACTIONS) -> CausalCheckResult:
    """SS5 condition 4: a trigger event (gate reject / drift detection / rollback) must
    PRECEDE the corrective action within <=5 actions, and that correction must flip a
    previously-failing checkpoint to passing. Runs over ONE instance's trace."""
    if not events:
        return CausalCheckResult("insufficient_trace_data", "no trace events loaded")
    triggers = [e for e in events if e.type in TRIGGER_EVENT_TYPES]
    if not triggers:
        return CausalCheckResult("not_verified", "no gate-reject/drift-detected/rollback event in trace")
    checkpoint_results = [e for e in events if e.type == "checkpoint_result" and e.checkpoint_id is not None]
    for trig in triggers:
        for cr in checkpoint_results:
            if cr.step <= trig.step or (cr.step - trig.step) > max_lag:
                continue
            prior_fail = any(
                e.checkpoint_id == cr.checkpoint_id and e.passed is False and e.step <= trig.step
                for e in checkpoint_results
            )
            if prior_fail and cr.passed:
                return CausalCheckResult(
                    "verified",
                    f"trigger@step={trig.step} ({trig.type}) -> checkpoint {cr.checkpoint_id} "
                    f"flipped to pass@step={cr.step} (lag={cr.step - trig.step})",
                )
    return CausalCheckResult("not_verified", "no trigger->recovery flip found within the lag window")


@dataclass
class Condition4Result:
    per_instance: dict
    n_verified: int
    n_total: int
    passes: bool


def condition4_trace_causal_rule(rows: list[ResultRow], *, trace_loader=load_trace) -> Condition4Result:
    aios_by_key = _index_by_instance(rows, "weak+AIOS", MUTATING_TEMPLATES)
    checklist_by_key = _index_by_instance(rows, "weak+checklist", MUTATING_TEMPLATES)
    credited_wins = [
        key for key in sorted(set(aios_by_key) & set(checklist_by_key))
        if aios_by_key[key].binary_success and not checklist_by_key[key].binary_success
    ]
    per_instance = {}
    for key in credited_wins:
        row = aios_by_key[key]
        events = trace_loader(row.trace_path)
        per_instance[key] = causal_recovery_check(events)
    n_verified = sum(1 for r in per_instance.values() if r.status == "verified")
    n_total = len(per_instance)
    passes = n_total > 0 and n_verified == n_total
    return Condition4Result(per_instance=per_instance, n_verified=n_verified, n_total=n_total, passes=passes)


# ---------------------------------------------------------------------------
# H3 (descriptive, secondary -- pre-reg SS5)
# ---------------------------------------------------------------------------
def h3_descriptive(rows: list[ResultRow], *, templates: tuple = MUTATING_TEMPLATES) -> dict:
    s_raw = _success_rate(rows, "weak-raw", templates)
    s_memory = _success_rate(rows, "weak+memory", templates)
    s_aios = _success_rate(rows, "weak+AIOS", templates)
    proevolve_reproduced = (not math.isnan(s_memory)) and (not math.isnan(s_raw)) and s_memory < s_raw
    h3_holds = (not math.isnan(s_aios)) and (not math.isnan(s_raw)) and s_aios >= s_raw
    return {
        "s_weak_raw": s_raw, "s_weak_memory": s_memory, "s_weak_aios": s_aios,
        "proevolve_reproduced": proevolve_reproduced, "h3_holds": h3_holds,
    }


# ---------------------------------------------------------------------------
# Condition 1 + overall verdict
# ---------------------------------------------------------------------------
@dataclass
class Condition1Result:
    comparison: PairedComparison
    win_threshold: int
    meets_win_count: bool
    passes: bool


def condition1(rows: list[ResultRow]) -> Condition1Result:
    comparison = paired_comparison(rows, "weak+AIOS", "weak+checklist", templates=MUTATING_TEMPLATES)
    meets_win_count = comparison.wins_a >= CONDITION1_MIN_WINS
    passes = meets_win_count and comparison.mcnemar.significant
    return Condition1Result(comparison, CONDITION1_MIN_WINS, meets_win_count, passes)


@dataclass
class VerdictReport:
    condition1: Condition1Result
    condition2: Condition2Result
    condition3: StaticGuardResult
    condition4: Condition4Result
    sweep: list
    h2: bool
    h3: dict
    verdict: str  # "WIN" | "STOP" | "MIXED"


def compute_verdict(rows: list[ResultRow]) -> VerdictReport:
    c1 = condition1(rows)
    c2 = condition2(rows)
    c3 = static_equivalence_guard(rows)
    c4 = condition4_trace_causal_rule(rows)

    stop = (not c1.meets_win_count) and (not c1.comparison.mcnemar.significant)
    win = c1.passes and c2.passes and c3.passes and c4.passes
    if win:
        verdict = "WIN"
    elif stop:
        verdict = "STOP"
    else:
        verdict = "MIXED"

    sweep = cost_sweep(rows)
    h2 = h2_holds(sweep)
    h3 = h3_descriptive(rows)

    return VerdictReport(c1, c2, c3, c4, sweep, h2, h3, verdict)


def format_verdict_block(report: VerdictReport) -> str:
    c1, c2, c3, c4 = report.condition1, report.condition2, report.condition3, report.condition4
    lines = []
    lines.append("=" * 72)
    lines.append("AIOS-DriftBench-mini -- M2 verdict (pre-reg SS5)")
    lines.append("=" * 72)
    lines.append(
        f"[Condition 1] paired wins (mutating): weak+AIOS {c1.comparison.wins_a}/"
        f"{c1.comparison.n_instances} vs weak+checklist "
        f"(need >={c1.win_threshold}/{CONDITION1_MIN_INSTANCES}); "
        f"McNemar one-sided p={c1.comparison.mcnemar.p_value:.4f} "
        f"(alpha={ALPHA}) significant={c1.comparison.mcnemar.significant} "
        f"-> {'PASS' if c1.passes else 'FAIL'}"
    )
    lines.append(
        f"[Condition 2] gap-closure mode={c2.gap.mode} value={c2.gap.value:.3f} "
        f"CI=[{c2.gap.ci.lo:.3f}, {c2.gap.ci.hi:.3f}] "
        f"(denominator_degenerate={c2.gap.denominator_degenerate}); "
        f"cost(tokens) diff CI upper={c2.cost.hi:.1f} (<0 required) "
        f"-> {'PASS' if c2.passes else 'FAIL'}"
    )
    lines.append(
        f"[Condition 3] static guard: |Delta successes|={c3.delta_successes} "
        f"(margin<={STATIC_MARGIN_INSTANCES}), unsupported-claim rate "
        f"AIOS={c3.unsupported_claim_rate_aios:.3f} vs checklist={c3.unsupported_claim_rate_checklist:.3f} "
        f"-> {'PASS' if c3.passes else 'FAIL'}"
    )
    lines.append(
        f"[Condition 4] trace causal rule: {c4.n_verified}/{c4.n_total} credited wins "
        f"trace-verified -> {'PASS' if c4.passes else 'FAIL'}"
    )
    lines.append("-" * 72)
    lines.append(f"VERDICT: {report.verdict}")
    lines.append("-" * 72)
    lines.append(f"[H2 secondary] cost sweep wrong={list(WRONG_COST_SWEEP)}: dominates every point={report.h2}")
    for p in report.sweep:
        lines.append(
            f"    wrong_cost={p.wrong_cost}: AIOS={p.cost_aios:.2f} "
            f"checklist={p.cost_checklist:.2f} dominates={p.aios_dominates}"
        )
    h3 = report.h3
    lines.append(
        f"[H3 secondary] weak-raw={h3['s_weak_raw']:.3f} weak+memory={h3['s_weak_memory']:.3f} "
        f"weak+AIOS={h3['s_weak_aios']:.3f} ProEvolve reproduced={h3['proevolve_reproduced']} "
        f"H3 holds={h3['h3_holds']}"
    )
    lines.append("=" * 72)
    return "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="AIOS-DriftBench-mini analysis (pre-reg SS4/SS6)")
    parser.add_argument("results_path", help="path to a JSONL result table (schema.ResultRow rows)")
    args = parser.parse_args(argv)
    rows = read_table(args.results_path)
    report = compute_verdict(rows)
    print(format_verdict_block(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
