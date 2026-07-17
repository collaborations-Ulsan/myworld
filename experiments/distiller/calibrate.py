"""experiments/distiller/calibrate.py -- live substrate calibration for tasks.py's A/B families
(the NEW DISCIPLINE from docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md 2026-07-18: "CALIBRATE THE
SUBSTRATE FIRST, then attach mechanism" -- DriftBench/S+1/S+1.1/the 2026-07-17 distiller pilot
(qwen3:1.7b solved 26/30 = 87%, N_verified=4) all died on substrate miscalibration, not mechanism).

Samples N tasks from A and N from B (deterministic, seeded shuffle) and runs the REAL student
(collect.call_student -- the same native ollama /api/chat path collect.py uses at collect time)
ONCE per task -- no escalation, no teacher, no training -- then grades the single completion
under BOTH of the pipeline's own live criteria:

  * "visible"  -- collect.py's ACTUAL escalation-trigger criterion (task['visible_tests'] only,
    graded the same way collect.collect()'s loop does). This is the number the prereg's 30-70%
    band targets: it is literally what produced the prior pilot's "26/30 (87%) -- no headroom"
    verdict, so it is the one this script iterates against.
  * "heldout"  -- evaluate.py's ACTUAL eval-time scoring criterion (held_out_tests +
    adversarial_tests, via evaluate.score_task, never visible_tests) -- the number that
    determines whether the eventual B-split LoRA comparison (step 3) has any headroom to show a
    lift in at all. Reported for both A and B so a design-time mismatch between "escalates" and
    "generalizes" is visible before a single hour is spent on collect/train.

No raw model completions are persisted (only task_id/family/split + pass/fail counts) -- nothing
to privacy/secret-scan here, unlike collect.py's SFT trajectory writes.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

_DISTILLER_DIR = Path(__file__).resolve().parent
if str(_DISTILLER_DIR) in sys.path:
    sys.path.remove(str(_DISTILLER_DIR))
sys.path.insert(0, str(_DISTILLER_DIR))

import collect  # noqa: E402 -- call_student, extract_code, GRADE_TIMEOUT_S, verify (learnos), sys.path setup
import evaluate  # noqa: E402 -- score_task (the frozen held-out+adversarial, solution-only scorer)

distiller_tasks = collect.distiller_tasks
DATA_DIR = _DISTILLER_DIR / "data"
TARGET_BAND = (0.30, 0.70)


def sample_tasks(tasks: list[dict], n: int, seed: int, tag: str) -> list[dict]:
    """Deterministic representative sample across families (seeded shuffle, not "first N" which
    would just be one family's instances given tasks.py's build order)."""
    rng = random.Random(f"aios-distiller:calibrate:{tag}:{seed}")
    pool = list(tasks)
    rng.shuffle(pool)
    return pool[: min(n, len(pool))]


def measure_split(tasks: list[dict], student_model: str, log=print) -> tuple[list[dict], dict]:
    """One live student call per task; grades the single completion under both criteria (see
    module docstring). Returns (per_task_records, summary)."""
    records = []
    for task in tasks:
        prompt = distiller_tasks.prompt_text(task)
        t0 = time.monotonic()
        resp = collect.call_student(prompt, model=student_model)
        dt = time.monotonic() - t0
        raw = resp["content"] if resp["ok"] else ""
        source = collect.extract_code(raw) if raw.strip() else ""

        visible = (
            collect.verify.run_public(task["visible_tests"], source, timeout=collect.GRADE_TIMEOUT_S)
            if source.strip() else {"all_passed": False, "passed": 0, "total": len(task["visible_tests"])}
        )
        heldout = evaluate.score_task(task, raw)

        rec = {
            "task_id": task["task_id"], "family": task["family"], "split": task["split"],
            "student_ok": resp["ok"], "error": resp.get("error"), "elapsed_s": round(dt, 2),
            "visible_solved": bool(visible["all_passed"]),
            "visible_passed": visible["passed"], "visible_total": visible["total"],
            "heldout_solved": bool(heldout["solved"]),
            "heldout_passed": heldout["passed"], "heldout_total": heldout["total"],
        }
        records.append(rec)
        log(
            f"[calibrate]   ({len(records)}/{len(tasks)}) {task['task_id']} [{dt:.1f}s]: "
            f"visible={'PASS' if rec['visible_solved'] else 'fail'} "
            f"heldout={'PASS' if rec['heldout_solved'] else 'fail'}"
            + ("" if resp["ok"] else f" INFRA_ERROR={resp.get('error')}")
        )

    n = len(records)
    n_infra = sum(1 for r in records if not r["student_ok"])
    summary = {
        "n": n,
        "n_infra_errors": n_infra,
        "visible_pass_rate": (sum(r["visible_solved"] for r in records) / n) if n else 0.0,
        "heldout_pass_rate": (sum(r["heldout_solved"] for r in records) / n) if n else 0.0,
    }
    return records, summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS Experience-Distiller: live substrate calibration (A/B pass-rate).")
    p.add_argument("--seed", type=int, default=20260717)
    p.add_argument("--a-instances", type=int, default=6)
    p.add_argument("--b-instances", type=int, default=6)
    p.add_argument("--n-a", type=int, default=20)
    p.add_argument("--n-b", type=int, default=20)
    p.add_argument("--student-model", default=collect.STUDENT_MODEL_DEFAULT)
    p.add_argument("--out-dir", default=str(DATA_DIR))
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_tasks = distiller_tasks.build_tasks(seed=args.seed, a_instances=args.a_instances, b_instances=args.b_instances)
    a_tasks = sample_tasks(distiller_tasks.by_split(all_tasks, "A"), args.n_a, args.seed, "A")
    b_tasks = sample_tasks(distiller_tasks.by_split(all_tasks, "B"), args.n_b, args.seed, "B")

    t0 = time.monotonic()
    print(f"[calibrate] student={args.student_model} -- measuring {len(a_tasks)} A-tasks ...")
    a_records, a_summary = measure_split(a_tasks, args.student_model)
    print(f"[calibrate] student={args.student_model} -- measuring {len(b_tasks)} B-tasks ...")
    b_records, b_summary = measure_split(b_tasks, args.student_model)
    elapsed = time.monotonic() - t0

    lo, hi = TARGET_BAND
    a_in_band = lo <= a_summary["visible_pass_rate"] <= hi
    report = {
        "student_model": args.student_model, "seed": args.seed, "elapsed_s": elapsed,
        "target_band": {"lo": lo, "hi": hi},
        "a_visible_in_target_band": a_in_band,
        "a": {**a_summary, "records": a_records},
        "b": {**b_summary, "records": b_records},
        "generated_at": time.time(),
    }

    headline = {
        "student_model": args.student_model,
        "a_visible_pass_rate": a_summary["visible_pass_rate"],
        "a_heldout_pass_rate": a_summary["heldout_pass_rate"],
        "b_visible_pass_rate": b_summary["visible_pass_rate"],
        "b_heldout_pass_rate": b_summary["heldout_pass_rate"],
        "a_visible_in_target_band_30_70": a_in_band,
        "n_a": a_summary["n"], "n_b": b_summary["n"], "elapsed_s": round(elapsed, 1),
    }
    print("=" * 78)
    print(json.dumps(headline, indent=2, sort_keys=True))
    print("=" * 78)
    (out_dir / "calibration_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
