#!/usr/bin/env python3
"""experiments/learnos/run_v0.py -- CLI for LearnOS v0 (docs/AIOS_AGI_CONCEPTION_2026-07-17.md §6).

    python experiments/learnos/run_v0.py [--iterations N] [--max-tasks-per-iter K]
    python experiments/learnos/run_v0.py --replay <candidate_id>

Runs N harness-improver iterations (default 3) against the 18-task external
set, then prints the ledger summary + the held-out fix-rate curve.

Proposer backend is pluggable (backend.py): default local ollama
qwen3-coder:30b, or set AIOS_LEARNOS_BACKEND=nim for NVIDIA NIM.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backend  # noqa: E402
import improve  # noqa: E402
import ledger  # noqa: E402
import tasks  # noqa: E402

BANNER = (
    "=" * 78 + "\n"
    "LearnOS v0 -- PULSE CHECK (machinery + ledger), NOT a compounding claim.\n"
    "The 20-30-iteration frozen-holdout compounding verdict is S+1 (see\n"
    "docs/AIOS_AGI_CONCEPTION_2026-07-17.md §6/§8). This run only asks:\n"
    "does the harness-improver loop run, evaluate externally, gate honestly,\n"
    "and write an append-only ledger? The numbers below are reported as-is,\n"
    "including if the proposer produces garbage.\n" + "=" * 78
)


def proposer_label() -> str:
    name = backend.backend_name()
    if name == "nim":
        model = os.environ.get("AIOS_LEARNOS_NIM_MODEL", backend.DEFAULT_NIM_MODEL)
    else:
        model = os.environ.get("AIOS_LEARNOS_OLLAMA_MODEL", backend.DEFAULT_OLLAMA_MODEL)
    return f"{name}:{model}"


def _replay(candidate_id: str, ledger_path: Path | None) -> int:
    rows = [r for r in ledger.read_all(ledger_path) if r["candidate_id"] == candidate_id]
    if not rows:
        print(f"no ledger row found for candidate_id={candidate_id!r}")
        return 1
    print(json.dumps(rows[0], indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--max-tasks-per-iter", type=int, default=6)
    parser.add_argument("--ledger-path", type=str, default=None)
    parser.add_argument("--replay", type=str, default=None, metavar="CANDIDATE_ID")
    args = parser.parse_args(argv)

    ledger_path = Path(args.ledger_path) if args.ledger_path else None

    if args.replay:
        return _replay(args.replay, ledger_path)

    print(BANNER)
    label = proposer_label()
    print(f"proposer backend: {label}")
    print(f"iterations: {args.iterations}  max_tasks_per_iter: {args.max_tasks_per_iter}")
    print(f"task set size: {len(tasks.load_visible_tasks())}\n")

    def proposer(prompt: str, **kwargs) -> str:
        return backend.complete(prompt, **kwargs)

    summary = improve.run_iterations(
        args.iterations,
        proposer,
        label,
        max_tasks_per_iter=args.max_tasks_per_iter,
        ledger_path=ledger_path,
    )

    print("--- per-iteration ---")
    for row in summary["per_iter"]:
        print(f"  iter {row['iter']}: {row['promoted']}/{row['candidates']} candidates promoted")

    print("\n--- held-out fix-rate curve (cumulative, NOT a compounding claim at n={}) ---".format(
        args.iterations
    ))
    for point in summary["held_out_fix_rate_curve"]:
        print(
            f"  iter {point['iter']}: {point['cumulative_fixed_tasks']}/"
            f"{summary['total_distinct_tasks']} tasks fixed "
            f"(fix_rate={point['cumulative_fix_rate']:.3f})"
        )

    print(
        f"\ntotal candidates evaluated: {summary['total_candidates']}  "
        f"total promoted: {summary['total_promoted']}  "
        f"final fix_rate: {summary['final_fix_rate']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
