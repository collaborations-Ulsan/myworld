#!/usr/bin/env python3
"""experiments/learnos/run_s1.py -- CLI for LearnOS S+1
(docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md), the pivot after the DriftBench keystone STOP.

    python experiments/learnos/run_s1.py [--iterations N] [--max-tasks-per-iter K]
                                          [--audit-threshold T] [--seed S]
                                          [--ledger-path PATH] [--skip-audit]
    python experiments/learnos/run_s1.py --replay <candidate_id> [--ledger-path PATH]

Runs the Blind-Curator verifier audit (audit.py) FIRST -- per the design doc, a promotion
must never be trusted before the verifier auditing it has been checked -- then N evolutionary
search iterations (search.py) mining ONLY from the A task split, and prints:

  * the audit's false-pass rate and whether promotion got frozen for this run
  * the per-iteration mining/promotion summary
  * the DECISIVE readout: the B (transfer-holdout) compounding curve -- held-out success
    rate on tasks NEVER used to mine any skill/tool/scaffold, at iter -1 (no library) and at
    every iteration the shared library changed
  * the sentinel (regression) curve, same shape, over a THIRD disjoint task pool
  * the paired sign-test comparing iter -1 vs the final iteration on B (with the required
    small-n caveat -- this is a low-power test at this scale, not proof either way)

Proposer backend is pluggable via v0's backend.py (default local ollama qwen3-coder:30b, or
AIOS_LEARNOS_BACKEND=nim for NVIDIA NIM) -- unchanged from v0, reused as-is.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit  # noqa: E402
import backend  # noqa: E402
import ledger  # noqa: E402
import search  # noqa: E402
import tasks  # noqa: E402

DEFAULT_S1_LEDGER_PATH = Path(__file__).resolve().parent / "data" / "ledger_s1.jsonl"

BANNER = (
    "=" * 78 + "\n"
    "LearnOS S+1 -- SEARCH + TRANSFER-HOLDOUT compounding test\n"
    "(docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md, pivot after the DriftBench keystone STOP)\n"
    "\n"
    "S+1 tests TRANSFER compounding on held-out set B: skills/tools/CoT-scaffolds are mined\n"
    "ONLY from A; the compounding metric is B's held-out success rate as a function of\n"
    "iteration, where B tasks are NEVER touched by mining. A flat or falling B-curve is a\n"
    "VALID, HONEST result (Beyond-pass@1 / CL-Bench predict memory scaffolds can HURT\n"
    "long-horizon transfer) -- it is reported as-is, not laundered into a defensible null or\n"
    "hidden as a failure. The sentinel curve (a third, disjoint pool) checks the accumulated\n"
    "library doesn't regress tasks the system could already solve.\n" + "=" * 78
)


def proposer_label() -> str:
    name = backend.backend_name()
    if name == "nim":
        model = os.environ.get("AIOS_LEARNOS_NIM_MODEL", backend.DEFAULT_NIM_MODEL)
    else:
        model = os.environ.get("AIOS_LEARNOS_OLLAMA_MODEL", backend.DEFAULT_OLLAMA_MODEL)
    return f"{name}:{model}"


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
    parser.add_argument("--ledger-path", type=str, default=None)
    parser.add_argument("--results-json", type=str, default=None, help="optional path to dump the full results dict as JSON")
    parser.add_argument("--replay", type=str, default=None, metavar="CANDIDATE_ID")
    args = parser.parse_args(argv)

    ledger_path = Path(args.ledger_path) if args.ledger_path else DEFAULT_S1_LEDGER_PATH

    if args.replay:
        return _replay(args.replay, ledger_path)

    print(BANNER)
    label = proposer_label()
    print(f"\nproposer backend: {label}")
    print(f"iterations: {args.iterations}  max_tasks_per_iter: {args.max_tasks_per_iter}  seed: {args.seed}")
    print(f"ledger path: {ledger_path}")

    split = search.load_split()
    all_tasks = {t["task_id"]: t for t in tasks.load_visible_tasks()}
    print(f"task split -- A(mine): {len(split['A'])}  B(transfer-holdout): {len(split['B'])}  sentinel: {len(split['sentinel'])}")

    def proposer(prompt: str, **kwargs) -> str:
        kwargs.setdefault("max_tokens", 400)
        kwargs.setdefault("timeout", 180.0)
        return backend.complete(prompt, **kwargs)

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
                "  FREEZE: false-pass rate exceeds threshold -- promotion to the shared library is "
                "FROZEN for this run (mining and evaluation still proceed; the ledger still records "
                "every candidate honestly, but nothing new enters the shared skill/tool library)."
            )
        else:
            print("  verifier trusted for this run -- promotions may enter the shared library.")

    print(f"\n--- running {args.iterations} search iterations (A-mining only) ---")

    def progress(msg: str) -> None:
        print(msg, flush=True)

    result = search.run_search(
        n_iterations=args.iterations,
        proposer=proposer,
        proposer_name=label,
        max_tasks_per_iter=args.max_tasks_per_iter,
        ledger_path=ledger_path,
        split=split,
        audit_frozen=audit_frozen,
        seed=args.seed,
        all_tasks=all_tasks,
        progress_cb=progress,
    )

    print(f"\nmining candidates evaluated: {len(result['mining_rows'])}")
    promoted = [r for r in result["mining_rows"] if r["decision"] == "promoted"]
    print(f"mining candidates promoted:  {len(promoted)}")
    print(f"archive: {result['archive_stats']}")
    print(f"mutation router observed yields: { {k: round(v, 3) for k, v in result['router_yields'].items()} }")
    print(f"mutation router call counts:     {result['router_counts']}")
    print(f"shared library size (genuinely NEW promoted scaffolds/tools, mined from A only): {result['library_size']}")
    for item in result["library_items"]:
        print(f"    - [{item['kind']}] {item['bug_kind']} (mined from {item['mined_task_id']} @iter{item['mined_iter']}, reused-and-promoted {item['promotions']}x)")

    _print_curve("B (transfer-holdout, DECISIVE)", result["b_curve"])
    _print_curve("sentinel (regression guard)", result["sentinel_curve"])

    ps = result["paired_stats"]
    print(
        f"\n--- paired sign test: iter -1 (no library) vs final iteration, on B ---\n"
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
