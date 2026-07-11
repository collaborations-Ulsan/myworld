"""Result-table schema for AIOS-DriftBench-mini (M2 keystone harness skeleton).

docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md SS4/SS6: "결과 테이블 스키마 + 분석 스크립트는
데이터 수집 전 커밋" -- this module is the frozen row shape every arm-runner writes and
every analyze.py read depends on. One row per (arm, instance), where an "instance" is
one (template, seed) pair.

Frozen fields (pre-reg SS4): binary_success (primary), checkpoints_passed (secondary
partial credit), actions_used/wall_seconds/tokens (cost + budget-cap accounting),
wrong_actions/stale_actions (the pre-reg SS4 wrong-action taxonomy -- (i) state-worsened
and (ii) contract-violation collapse into wrong_actions, (iii) stale-action gets its own
column since it is separately named in SS4, and (iv) unsupported-final-claim is
unsupported_claims), asks/abstains (SS4 ASK/ABSTAIN semantics),
verification_before_submit (secondary metric named in SS4), trace_path (pointer to the
full captured trace -- see grader.py for the ActionRecord trace shape and analyze.py's
module docstring for the TraceEvent shape this skeleton assumes for the SS5 condition-4
causal check).

AMBIGUITY FLAG: the pre-reg's wrong-action taxonomy (i)-(iv) does not map 1:1 onto a
4-column schema on its own -- SS4 only requires "wrong-action" as one concept plus the
three named secondary rates (stale-action rate, unsupported-final-claim rate, and,
implicitly, a general wrong-action rate). This module keeps `wrong_actions` as a single
count covering reasons (i) state-worsened and (ii) contract-violation (both are "the
action was actively bad", grader.py's WrongActionReason enum keeps them distinguishable
at the trace-label level even though this table aggregates them), and gives (iii) and
(iv) their own dedicated columns because SS4 names their rates explicitly
("stale-action rate", "unsupported final-claim rate"). Anyone re-deriving this schema
should treat that split as a design decision made here, not a pre-reg fact.

No experiment runs happen in this module -- it is pure schema + validation.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Known template/arm vocab this schema validates against -- kept in one place so
# tasks.py / arms.py / schema.py can't silently drift apart (see tests).
MUTATING_TEMPLATES = (
    "api_migration",
    "deprecation",
    "schema_change",
    "config_change",
    "version_bump",
    "auth_change",
)
STATIC_TEMPLATES = (
    "url_static",
    "dependency_static",
)
ALL_TEMPLATES = MUTATING_TEMPLATES + STATIC_TEMPLATES

ARM_NAMES = (
    "strong-raw",
    "weak-raw",
    "weak+checklist",
    "weak+memory",
    "weak+AIOS",
    "strong+AIOS",  # optional ceiling arm, pre-reg SS2 -- not required for WIN/STOP
)

SEEDS = (0, 1, 2)  # 3 seeds x 8 templates = 24 instances (pre-reg SS3)

WALL_SECONDS_CAP = 45 * 60
ACTIONS_CAP = 200


def is_mutating(template: str) -> bool:
    return template in MUTATING_TEMPLATES


@dataclass
class ResultRow:
    template: str
    seed: int
    arm: str
    binary_success: bool
    checkpoints_passed: int
    checkpoints_total: int
    actions_used: int
    wall_seconds: float
    tokens: int
    wrong_actions: int
    stale_actions: int
    asks: int
    abstains: int
    unsupported_claims: int
    verification_before_submit: bool
    trace_path: str
    restarted: bool = False  # pre-reg SS3: restart == primary failure for that instance

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ResultRow":
        return ResultRow(**d)


def validate_row(row: ResultRow) -> list[str]:
    """Programmatic checks only -- anything requiring semantic judgment is out of scope
    for schema validation (that lives in grader.label_actions' auditor_required path)."""
    errors: list[str] = []
    if row.template not in ALL_TEMPLATES:
        errors.append(f"unknown template {row.template!r}")
    if row.arm not in ARM_NAMES:
        errors.append(f"unknown arm {row.arm!r}")
    if row.seed not in SEEDS:
        errors.append(f"seed {row.seed} not in frozen seed set {SEEDS}")
    if row.checkpoints_total <= 0:
        errors.append("checkpoints_total must be > 0")
    elif not (0 <= row.checkpoints_passed <= row.checkpoints_total):
        errors.append("checkpoints_passed out of range [0, checkpoints_total]")
    if row.actions_used < 0 or row.actions_used > ACTIONS_CAP:
        errors.append(f"actions_used {row.actions_used} outside frozen cap [0, {ACTIONS_CAP}]")
    if row.wall_seconds < 0 or row.wall_seconds > WALL_SECONDS_CAP + 1e-6:
        errors.append(f"wall_seconds {row.wall_seconds} outside frozen cap [0, {WALL_SECONDS_CAP}]")
    for name in ("tokens", "wrong_actions", "stale_actions", "asks", "abstains", "unsupported_claims"):
        v = getattr(row, name)
        if v < 0:
            errors.append(f"{name} must be >= 0, got {v}")
    if row.restarted and row.binary_success:
        errors.append("restarted instance cannot be scored binary_success=True (pre-reg SS3: restart=failure)")
    if not row.trace_path:
        errors.append("trace_path must be non-empty (pre-reg SS7: full trace capture)")
    return errors


def validate_table(rows: list[ResultRow]) -> list[str]:
    errors: list[str] = []
    for i, row in enumerate(rows):
        for e in validate_row(row):
            errors.append(f"row {i} ({row.template}/{row.seed}/{row.arm}): {e}")
    # Each (template, seed, arm) key must appear at most once.
    seen: dict[tuple[str, int, str], int] = {}
    for i, row in enumerate(rows):
        key = (row.template, row.seed, row.arm)
        if key in seen:
            errors.append(f"row {i}: duplicate key {key} (also row {seen[key]})")
        else:
            seen[key] = i
    return errors


def read_table(path: str | Path) -> list[ResultRow]:
    rows: list[ResultRow] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(ResultRow.from_dict(json.loads(line)))
    return rows


def write_table(path: str | Path, rows: list[ResultRow]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row.as_dict(), sort_keys=True))
            f.write("\n")
