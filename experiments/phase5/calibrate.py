#!/usr/bin/env python3
"""Phase 5 substrate calibration (prereg §4 ONLY — no arm is run here).

FROZEN PROTOCOL: docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md.

1. Reserve a held-out calibration subset (deterministic, evenly spaced over
   the chronological task list) -> experiments/phase5/calibration_holdout.json.
   Once written the holdout is FROZEN: subsequent invocations load it, never
   re-pick. These task_ids are EXCLUDED from the main run's task list.
2. Run each frozen candidate student on every holdout task in CONTROL mode
   (no injection, no substrate) — one attempt, external oracle.
3. Report each model's calibration P_auto = passes / (n - infra_errors);
   infra errors are reported separately, never counted as losses (§6.6).
4. Pre-registered selection rule: the SMALLEST model whose P_auto lands in
   [0.20, 0.60]. If none lands in the band:
   "EXPERIMENT NOT RUN — no candidate has measurable headroom."

Incremental + resumable: results append to calibration_results.json after
every attempt; finished (model, task) pairs are skipped on re-invocation.
Exit codes: 0 = calibration complete (summary printed), 3 = budget hit,
more attempts remain (invoke again).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from runner import run_task  # noqa: E402

SCHEMA = "aios.phase5.calibration.v1"
TASKS_JSON = HERE / "tasks.json"
HOLDOUT_JSON = HERE / "calibration_holdout.json"
RESULTS_JSON = HERE / "calibration_results.json"

# Frozen candidate students (prereg §4), ascending parameter count as
# reported by `ollama show` on this machine (2026-07-26).
CANDIDATES = [
    ("qwen2.5-coder:7b", 7.6),
    ("qwen3:8b", 8.2),
    ("qwen3-coder:30b", 30.5),
    ("qwen3-coder-next", 79.7),
]
BAND = (0.20, 0.60)


def select_holdout(tasks: list[dict], size: int) -> list[str]:
    """Deterministic evenly spaced indices over the chronological task list."""
    n = len(tasks)
    if n <= size:
        return [t["task_id"] for t in tasks]
    idx = sorted({round(i * (n - 1) / (size - 1)) for i in range(size)})
    return [tasks[i]["task_id"] for i in idx]


def load_or_freeze_holdout(tasks: list[dict], size: int) -> list[str]:
    if HOLDOUT_JSON.exists():
        data = json.loads(HOLDOUT_JSON.read_text(encoding="utf-8"))
        ids = data["task_ids"]
        known = {t["task_id"] for t in tasks}
        missing = [i for i in ids if i not in known]
        if missing:
            raise RuntimeError(f"frozen holdout ids not in tasks.json: "
                               f"{missing}")
        return ids
    ids = select_holdout(tasks, size)
    HOLDOUT_JSON.write_text(json.dumps({
        "schema": SCHEMA, "kind": "holdout",
        "frozen_at": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"),
        "rule": ("deterministic evenly spaced indices over the chronological "
                 "task list; EXCLUDED from the main run"),
        "size": len(ids), "task_ids": ids,
    }, indent=2) + "\n", encoding="utf-8")
    return ids


def _load_results() -> dict:
    if RESULTS_JSON.exists():
        return json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    return {"schema": SCHEMA, "records": []}


def _save_results(res: dict) -> None:
    RESULTS_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=2)
                            + "\n", encoding="utf-8")


def summarize(records: list[dict], models: list[tuple[str, float]]) -> dict:
    per_model: dict[str, dict] = {}
    for name, params_b in models:
        recs = [r for r in records if r["model"] == name]
        infra = [r for r in recs if r["infra_error"]]
        scored = [r for r in recs if not r["infra_error"]]
        passes = sum(1 for r in scored if r["passed"])
        p = (passes / len(scored)) if scored else None
        per_model[name] = {
            "params_b": params_b, "attempts": len(recs),
            "infra_errors": len(infra), "scored": len(scored),
            "passes": passes,
            "P_auto": round(p, 4) if p is not None else None,
            "in_band": (p is not None and BAND[0] <= p <= BAND[1]),
        }
    selected = None
    for name, _ in models:  # ascending size — smallest in-band wins
        if per_model[name]["in_band"]:
            selected = name
            break
    return {
        "band": list(BAND), "per_model": per_model,
        "selected_student": selected,
        "verdict": (f"selected {selected} (smallest model with P_auto in "
                    f"[{BAND[0]}, {BAND[1]}])" if selected else
                    "EXPERIMENT NOT RUN — no candidate has measurable "
                    "headroom"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phase 5 calibration (prereg §4)")
    ap.add_argument("--tasks-file", default=str(TASKS_JSON))
    ap.add_argument("--holdout-size", type=int, default=8)
    ap.add_argument("--call-timeout", type=float, default=360.0)
    ap.add_argument("--oracle-timeout", type=float, default=180.0)
    ap.add_argument("--max-seconds", type=float, default=0.0,
                    help="stop starting new attempts after this budget; "
                         "exit 3 when attempts remain")
    ap.add_argument("--models", default="",
                    help="comma-separated subset of candidates (default: all)")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)

    tasks_doc = json.loads(Path(args.tasks_file).read_text(encoding="utf-8"))
    tasks = tasks_doc["tasks"]
    by_id = {t["task_id"]: t for t in tasks}
    holdout = load_or_freeze_holdout(tasks, args.holdout_size)

    models = CANDIDATES
    if args.models:
        want = {m.strip() for m in args.models.split(",") if m.strip()}
        models = [m for m in CANDIDATES if m[0] in want]

    res = _load_results()
    done = {(r["model"], r["task_id"]) for r in res["records"]}
    todo = [(name, tid) for name, _ in models for tid in holdout
            if (name, tid) not in done]

    t0 = time.time()
    if not args.report_only:
        for name, tid in todo:
            if args.max_seconds and (time.time() - t0) > args.max_seconds:
                print(json.dumps({"status": "budget_hit",
                                  "remaining": len(
                                      [(m, t) for m, t in todo
                                       if (m, t) not in done])}))
                return 3
            print(f"[calibrate] {name} on {tid} ...", flush=True)
            rec = run_task(by_id[tid], arm="control", model=name,
                           call_timeout=args.call_timeout,
                           oracle_timeout=args.oracle_timeout)
            rec["kind"] = "calibration"
            res["records"].append(rec)
            done.add((name, tid))
            _save_results(res)
            print(f"[calibrate] {name} {tid} -> passed={rec['passed']} "
                  f"infra={rec['infra_error']} wall={rec['wall_s']}s",
                  flush=True)

    remaining = [(m, t) for m, _ in CANDIDATES for t in holdout
                 if (m, t) not in done]
    summary = summarize(res["records"], CANDIDATES)
    summary["holdout_task_ids"] = holdout
    summary["complete"] = not remaining
    res["summary"] = summary
    _save_results(res)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not remaining else 3


if __name__ == "__main__":
    raise SystemExit(main())
