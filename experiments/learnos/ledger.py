"""experiments/learnos/ledger.py -- the promotion ledger: the FIRST product of
LearnOS v0 (docs/AIOS_AGI_CONCEPTION_2026-07-17.md §6).

Append-only JSONL, one row per evaluated candidate (promoted OR rejected --
open-endedness, not hill-climb-only archiving). Every row carries the full
chain the AIOS_AGI_CONCEPTION discipline demands:

    candidate -> visible_pass -> holdout_pass -> sentinel_regressed ->
    exploit_or_contract_audit -> decision -> replay_cmd -> parent_id

`summarize()` is how a later, separate S+1 pass checks "does it compound":
per-iteration promoted-count plus the cumulative held-out fix-rate curve.

stdlib only (json, time, uuid).
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent / "data" / "ledger.jsonl"

REQUIRED_FIELDS = (
    "candidate_id",
    "iter",
    "task_id",
    "kind",
    "proposer",
    "visible_pass",
    "holdout_pass",
    "sentinel_regressed",
    "exploit_or_contract_audit",
    "decision",
    "replay_cmd",
    "parent_id",
    "ts",
)

VALID_DECISIONS = ("promoted", "rejected")
VALID_KINDS = ("code_patch", "cot_scaffold", "tool")


class LedgerError(Exception):
    pass


def append(row: dict, path: Path | None = None) -> dict:
    """Append one candidate row. Fills candidate_id/ts if absent, then
    validates every required field is present and well-formed before writing
    -- a malformed row is a bug in the caller, never silently dropped."""
    path = path or DEFAULT_LEDGER_PATH
    row = dict(row)
    row.setdefault("candidate_id", str(uuid.uuid4()))
    row.setdefault("ts", time.time())

    missing = [f for f in REQUIRED_FIELDS if f not in row]
    if missing:
        raise LedgerError(f"ledger row missing required fields: {missing}")
    if row["decision"] not in VALID_DECISIONS:
        raise LedgerError(f"decision must be one of {VALID_DECISIONS}, got {row['decision']!r}")
    if row["kind"] not in VALID_KINDS:
        raise LedgerError(f"kind must be one of {VALID_KINDS}, got {row['kind']!r}")
    if not row["replay_cmd"]:
        raise LedgerError("replay_cmd must be a non-empty string")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def read_all(path: Path | None = None) -> list[dict]:
    path = path or DEFAULT_LEDGER_PATH
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def promoted_task_ids(path: Path | None = None) -> set[str]:
    """task_ids that have at least one promoted candidate -- used by
    improve.py to stop re-attempting tasks that already compounded a fix."""
    return {r["task_id"] for r in read_all(path) if r["decision"] == "promoted"}


def summarize(path: Path | None = None) -> dict:
    """Per-iteration candidate/promoted counts + cumulative held-out fix-rate
    curve (fraction of distinct task_ids with >=1 promoted candidate so far).
    This is the artifact a later S+1 pass reads to check compounding -- NOT a
    claim this v0 run makes about compounding itself (see run_v0.py banner).
    """
    rows = read_all(path)
    if not rows:
        return {
            "total_candidates": 0,
            "total_promoted": 0,
            "per_iter": [],
            "held_out_fix_rate_curve": [],
            "final_fix_rate": 0.0,
            "total_distinct_tasks": 0,
        }

    iters_sorted = sorted({r["iter"] for r in rows})
    total_distinct_tasks = len({r["task_id"] for r in rows})
    fixed_tasks: set[str] = set()
    per_iter = []
    curve = []
    for it in iters_sorted:
        this_iter_rows = [r for r in rows if r["iter"] == it]
        promoted_this_iter = sum(1 for r in this_iter_rows if r["decision"] == "promoted")
        for r in this_iter_rows:
            if r["decision"] == "promoted":
                fixed_tasks.add(r["task_id"])
        per_iter.append(
            {
                "iter": it,
                "candidates": len(this_iter_rows),
                "promoted": promoted_this_iter,
            }
        )
        curve.append(
            {
                "iter": it,
                "cumulative_fixed_tasks": len(fixed_tasks),
                "cumulative_fix_rate": len(fixed_tasks) / total_distinct_tasks,
            }
        )

    return {
        "total_candidates": len(rows),
        "total_promoted": sum(1 for r in rows if r["decision"] == "promoted"),
        "per_iter": per_iter,
        "held_out_fix_rate_curve": curve,
        "final_fix_rate": len(fixed_tasks) / total_distinct_tasks,
        "total_distinct_tasks": total_distinct_tasks,
    }
