"""experiments/distiller/run_distiller.py -- orchestrates collect -> (train if a trainer is
present) -> evaluate, and prints the honest summary banner
(docs/AIOS_DISTILLER_PREREG_2026-07-17.md v1.1 S3 step 5).

    python experiments/distiller/run_distiller.py [--seed S] [--a-instances N] [--b-instances N]
                                                   [--max-a-tasks N] [--time-budget-s T]
                                                   [--student-model NAME] [--skip-audit] [--out-dir DIR]

Every phase is also independently runnable (collect.py / train_lora.py / evaluate.py each have
their own CLI) -- this is a thin sequencing convenience, not a new code path.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_DISTILLER_DIR = Path(__file__).resolve().parent
if str(_DISTILLER_DIR) in sys.path:
    sys.path.remove(str(_DISTILLER_DIR))
sys.path.insert(0, str(_DISTILLER_DIR))

import collect  # noqa: E402
import evaluate  # noqa: E402
import train_lora  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS Experience-Distiller: full pipeline.")
    p.add_argument("--seed", type=int, default=20260717)
    p.add_argument("--a-instances", type=int, default=6)
    p.add_argument("--b-instances", type=int, default=6)
    p.add_argument("--max-a-tasks", type=int, default=None)
    p.add_argument("--time-budget-s", type=float, default=2400.0)
    p.add_argument("--student-model", default=collect.STUDENT_MODEL_DEFAULT)
    p.add_argument("--base-model-id", default=train_lora.BASE_MODEL_ID_DEFAULT)
    p.add_argument("--skip-audit", action="store_true")
    p.add_argument("--skip-train", action="store_true", help="skip train_lora even if a trainer is installed")
    p.add_argument("--skip-evaluate", action="store_true")
    p.add_argument("--out-dir", default=str(collect.DATA_DIR))
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    print("#" * 78)
    print("# AIOS Experience-Distiller -- docs/AIOS_DISTILLER_PREREG_2026-07-17.md v1.1")
    print("#" * 78)

    print("\n--- [1/3] collect ---")
    all_tasks = collect.distiller_tasks.build_tasks(seed=args.seed, a_instances=args.a_instances, b_instances=args.b_instances)
    (out_dir / "tasks_manifest.json").write_text(json.dumps(all_tasks, indent=2, sort_keys=True), encoding="utf-8")
    a_tasks = collect.distiller_tasks.by_split(all_tasks, "A")
    if args.max_a_tasks is not None:
        a_tasks = a_tasks[: args.max_a_tasks]
    summary = collect.collect(
        a_tasks, out_dir=out_dir, time_budget_s=args.time_budget_s,
        skip_audit=args.skip_audit, student_model=args.student_model,
    )
    (out_dir / "collect_summary.json").write_text(json.dumps(summary.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))

    print(f"\n--- [2/3] train_lora (trainer_available={train_lora.trainer_available()}, skip_train={args.skip_train}) ---")
    train_plan = None
    if not args.skip_train:
        train_lora.main(["--out-dir", str(out_dir), "--base-model-id", args.base_model_id, "--seed", str(args.seed)])
        train_plan = json.loads((out_dir / "train_lora_plan.json").read_text(encoding="utf-8"))
    else:
        print("skipped by --skip-train")

    report = None
    if not args.skip_evaluate:
        print("\n--- [3/3] evaluate ---")
        evaluate.main([
            "--seed", str(args.seed), "--b-instances", str(args.b_instances),
            "--student-model", args.student_model, "--base-model-id", args.base_model_id,
            "--out-dir", str(out_dir),
        ])
        report = json.loads((out_dir / "evaluate_report.json").read_text(encoding="utf-8"))
    else:
        print("\n--- [3/3] evaluate: skipped by --skip-evaluate ---")

    n_verified = summary.n_verified
    banner = collect.pilot_banner(n_verified)
    elapsed = time.monotonic() - t0
    print("\n" + "#" * 78)
    print(f"# DONE in {elapsed:.1f}s -- N_verified={n_verified} -- {banner}")
    print(f"# trainer_available={train_lora.trainer_available()}")
    if report:
        print(f"# arms_run={report.get('arms_run')} arms_skipped={report.get('arms_skipped')}")
    print("#" * 78)
    (out_dir / "run_distiller_summary.json").write_text(json.dumps({
        "n_verified": n_verified, "banner": banner, "elapsed_s": elapsed,
        "trainer_available": train_lora.trainer_available(),
        "collect_summary": summary.as_dict(), "train_plan": train_plan, "evaluate_report": report,
    }, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
