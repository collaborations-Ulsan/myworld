#!/usr/bin/env python3
"""experiments/learnos/run_s11.py -- CLI for LearnOS S+1.1, the diagnosed-fix re-attempt
after S+1 returned NO-transfer-compound (docs/AIOS_LEARNOS_S1_RESULTS_2026-07-17.md,
docs/AIOS_AGI_CONCEPTION_2026-07-17.md §10, docs/ontology/ledger/learning_methods.md §4).

    python experiments/learnos/run_s11.py [--iterations N] [--max-tasks-per-iter K]
                                           [--audit-threshold T] [--seed S] [--niche-cap N]
                                           [--nim-fraction F] [--no-nim]
                                           [--ledger-path PATH] [--skip-audit]
    python experiments/learnos/run_s11.py --replay <candidate_id> [--ledger-path PATH]

Same transfer-holdout protocol as S+1 (A mine / B held-out / sentinel, Blind-Curator audit
first, B/sentinel compounding curves + Wilson CI + paired sign test), reusing search.py's
statistics and evolutionary-search primitives unmodified (evolve_s11.py). Two additions,
per S+1's §5 diagnosis:

  * causal_gate.py -- a cot_scaffold/tool candidate the base gate promotes is promoted into
    the shared pool ONLY if it also survives a degeneracy pre-filter and a causal-ablation
    check (does REMOVING it measurably degrade the held-out result?).
  * gene_pool.py -- MAP-Elites niches (bug_kind x capability) with one elite + a capped
    recessive pool per niche, QD-score, and niche-matched-ONLY retrieval (no
    blind-fallback-to-any-item, the diagnosed noise source for B in S+1).

Proposer backend is heterogeneous when a NIM key is configured: each individual proposer
call is independently routed to local ollama (default) or NVIDIA NIM
(evolve_s11.HeterogeneousProposer), recording which operator produced each candidate. Falls
back to ollama-only if no NIM key is available or --no-nim is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit  # noqa: E402
import backend  # noqa: E402
import evolve_s11  # noqa: E402
import ledger  # noqa: E402
import search  # noqa: E402
import tasks  # noqa: E402

DEFAULT_S11_LEDGER_PATH = Path(__file__).resolve().parent / "data" / "ledger_s11.jsonl"

BANNER = (
    "=" * 78 + "\n"
    "LearnOS S+1.1 -- causal-ablation gate + gene-pool (D6) re-attempt after S+1's\n"
    "NO-transfer-compound verdict (docs/AIOS_LEARNOS_S1_RESULTS_2026-07-17.md,\n"
    "docs/AIOS_AGI_CONCEPTION_2026-07-17.md §10)\n"
    "\n"
    "S+1 diagnosed WHY B fell (12/12 -> 10/12 on library injection, never recovered): the\n"
    "promotion gate checked only 'final patch passes', never whether the tool/scaffold was\n"
    "CAUSALLY responsible for the fix, and Library.best_for() blindly fell back to any item\n"
    "when no bug_kind match existed. S+1.1 fixes both: causal_gate.py requires WITH to\n"
    "strictly beat WITHOUT on held-out before anything enters the pool, and gene_pool.py's\n"
    "GenePool.best_for() returns None (no augmentation) on a niche miss instead of a random\n"
    "item. A flat or falling B-curve here is STILL a valid, honest result -- reported as-is,\n"
    "not laundered -- and would be stronger evidence for the Sutton/OaK side (naive\n"
    "accumulation around a frozen model doesn't compound even after causal verification).\n"
    + "=" * 78
)


def _local_label() -> str:
    return f"ollama:{os.environ.get('AIOS_LEARNOS_OLLAMA_MODEL', backend.DEFAULT_OLLAMA_MODEL)}"


def _replay(candidate_id: str, ledger_path: Path) -> int:
    rows = [r for r in ledger.read_all(ledger_path) if r["candidate_id"] == candidate_id]
    if not rows:
        print(f"no ledger row found for candidate_id={candidate_id!r} in {ledger_path}")
        return 1
    print(json.dumps(rows[0], indent=2, sort_keys=True))
    return 0


def _print_curve(name: str, curve: dict) -> None:
    print(f"\n--- {name} curve (successes/total, Wilson 95% CI) ---")
    for p in curve["points"]:
        print(
            f"  iter {p['iter']:>3}: {p['successes']}/{p['total']} "
            f"(rate={p['rate']:.3f}, 95% CI=[{p['ci_lo']:.3f}, {p['ci_hi']:.3f}])"
        )
    fvf = curve["final_vs_first"]
    trend = "RISING" if fvf["rising"] else ("FALLING" if fvf["falling"] else "FLAT")
    print(f"  final vs first: {trend}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iterations", type=int, default=12)
    parser.add_argument("--max-tasks-per-iter", type=int, default=3)
    parser.add_argument("--audit-threshold", type=float, default=audit.DEFAULT_THRESHOLD)
    parser.add_argument("--skip-audit", action="store_true", help="skip the Blind-Curator audit (NOT recommended)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--niche-cap", type=int, default=evolve_s11.DEFAULT_NICHE_CAP)
    parser.add_argument("--nim-fraction", type=float, default=evolve_s11.DEFAULT_NIM_FRACTION,
                         help="fraction of proposer calls routed to NIM when a key is available")
    parser.add_argument("--no-nim", action="store_true", help="disable heterogeneous mutation; local ollama only")
    parser.add_argument("--ledger-path", type=str, default=None)
    parser.add_argument("--results-json", type=str, default=None, help="optional path to dump the full results dict as JSON")
    parser.add_argument("--replay", type=str, default=None, metavar="CANDIDATE_ID")
    args = parser.parse_args(argv)

    ledger_path = Path(args.ledger_path) if args.ledger_path else DEFAULT_S11_LEDGER_PATH

    if args.replay:
        return _replay(args.replay, ledger_path)

    print(BANNER)

    nim_available = (not args.no_nim) and evolve_s11.nim_key_available()
    op_rng = random.Random(args.seed + 1000)  # separate stream from the mutation-router rng
    proposer = evolve_s11.HeterogeneousProposer(op_rng, nim_available, nim_fraction=args.nim_fraction)
    label = f"heterogeneous(ollama+nim)" if nim_available else "ollama-only"
    print(f"\nproposer: {label}  (ollama={proposer.ollama_label}"
          + (f"  nim={proposer.nim_label}  nim_fraction={args.nim_fraction}" if nim_available else "") + ")")
    print(f"iterations: {args.iterations}  max_tasks_per_iter: {args.max_tasks_per_iter}  "
          f"seed: {args.seed}  niche_cap: {args.niche_cap}")
    print(f"ledger path: {ledger_path}")

    split = search.load_split()
    all_tasks = {t["task_id"]: t for t in tasks.load_visible_tasks()}
    print(f"task split -- A(mine): {len(split['A'])}  B(transfer-holdout): {len(split['B'])}  sentinel: {len(split['sentinel'])}")

    class _BoundedProposer:
        """Applies the default max_tokens/timeout S+1 used, then delegates to the
        heterogeneous proposer. `.last_operator` always reflects the underlying
        HeterogeneousProposer's most recent call (a plain closure attribute would go
        stale)."""

        def __call__(self, prompt: str, **kwargs) -> str:
            kwargs.setdefault("max_tokens", 400)
            kwargs.setdefault("timeout", 180.0)
            return proposer(prompt, **kwargs)

        @property
        def last_operator(self) -> str:
            return proposer.last_operator

    tracking_proposer = _BoundedProposer()

    audit_frozen = False
    if args.skip_audit:
        print("\n--- Blind-Curator verifier audit: SKIPPED (--skip-audit) ---")
    else:
        print("\n--- Blind-Curator verifier audit (running BEFORE trusting any promotion) ---")
        audit_result = audit.run_audit(list(all_tasks.values()), threshold=args.audit_threshold)
        audit_frozen = audit_result["freeze_promotion"]
        print(
            f"  trials={audit_result['n_trials']}  false_passes={audit_result['false_passes']}  "
            f"false_pass_rate={audit_result['false_pass_rate']:.3f}  threshold={audit_result['threshold']:.3f}"
        )
        if audit_frozen:
            print(
                "  FREEZE: false-pass rate exceeds threshold -- promotion to the gene pool is "
                "FROZEN for this run (mining and evaluation still proceed; the ledger still records "
                "every candidate honestly, but nothing new enters the shared gene pool)."
            )
        else:
            print("  verifier trusted for this run -- promotions may enter the gene pool.")

    print(f"\n--- running {args.iterations} search iterations (A-mining only, causal-gated) ---")

    def progress(msg: str) -> None:
        print(msg, flush=True)

    result = evolve_s11.run_search_s11(
        n_iterations=args.iterations,
        proposer=tracking_proposer,
        proposer_name=label,
        max_tasks_per_iter=args.max_tasks_per_iter,
        ledger_path=ledger_path,
        split=split,
        audit_frozen=audit_frozen,
        seed=args.seed,
        niche_cap=args.niche_cap,
        all_tasks=all_tasks,
        progress_cb=progress,
    )

    print(f"\nmining candidates evaluated: {len(result['mining_rows'])}")
    promoted = [r for r in result["mining_rows"] if r["decision"] == "promoted"]
    base_gate_promoted = [r for r in result["mining_rows"] if r.get("base_gate_decision") == "promoted"]
    print(f"mining candidates promoted (final, causal-gate-aware): {len(promoted)}")
    print(f"  of which base gate alone would have promoted: {len(base_gate_promoted)}")
    print(f"archive: {result['archive_stats']}")
    print(f"mutation router observed yields: { {k: round(v, 3) for k, v in result['router_yields'].items()} }")
    print(f"mutation router call counts:     {result['router_counts']}")

    cg = result["causal_gate_stats"]
    print(
        "\n--- causal gate stats ---\n"
        f"  scaffold/tool candidates the base gate promoted and considered: {cg['scaffold_tool_candidates_considered']}\n"
        f"  degenerate (identity/constant/vacuous-postcondition) pre-filtered: {cg['degenerate_prefiltered']}\n"
        f"  causal-ablation rejected (WITH did not strictly beat WITHOUT):    {cg['causal_rejected_no_responsibility']}\n"
        f"  causally-verified and promoted into the gene pool:                {cg['causally_verified_promoted']}"
    )

    gp = result["gene_pool_stats"]
    print(
        "\n--- gene pool stats (MAP-Elites, bug_kind x capability niches) ---\n"
        f"  niches (specialists): {gp['num_niches']}  distinct bug_kinds covered: {gp['distinct_bug_kinds_covered']}\n"
        f"  niches_per_bug_kind: {gp['niches_per_bug_kind']}\n"
        f"  niches_per_capability: {gp['niches_per_capability']}\n"
        f"  QD-score: {gp['qd_score']:.2f}  total_lineage: {gp['total_lineage']}  "
        f"recessive retained: {gp['total_recessive_retained']}  niche_cap: {gp['niche_cap']}"
    )
    for item in result["gene_pool_items"]:
        print(
            f"    - [{item['capability']}] {item['bug_kind']} (mined from {item['mined_task_id']} "
            f"@iter{item['mined_iter']} by {item['operator']}, with={item['with_passed']} "
            f"without={item['without_passed']}, reused-and-promoted {item['reused']}x)"
        )

    _print_curve("B (transfer-holdout, DECISIVE)", result["b_curve"])
    _print_curve("sentinel (regression guard)", result["sentinel_curve"])

    ps = result["paired_stats"]
    print(
        f"\n--- paired sign test: iter -1 (no pool) vs final iteration, on B ---\n"
        f"  n_pairs={ps['n_pairs']}  improved={ps['improved']}  regressed={ps['regressed']}  "
        f"n_discordant={ps['n_discordant']}  p_value(two-sided)={ps['p_value_two_sided']:.4f}\n"
        f"  CAVEAT: n_pairs={ps['n_pairs']} is SMALL -- this test has low statistical power at this "
        f"scale. A non-significant p-value does NOT prove no transfer; a significant one at this n "
        f"should still be treated as preliminary, not proof, per the design doc's 'no compounding "
        f"claim without the B-curve + statistical caveat.'"
    )

    if args.results_json:
        Path(args.results_json).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nfull results dict written to {args.results_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
