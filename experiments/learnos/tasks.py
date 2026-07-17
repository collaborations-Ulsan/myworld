"""experiments/learnos/tasks.py -- the EXTERNAL task set (LearnOS v0, §6 of
docs/AIOS_AGI_CONCEPTION_2026-07-17.md).

18 hand-written, deterministic Python bug-fix tasks (off-by-one, wrong
operator, boundary, mutable-default-argument, comparison-direction, index
fencepost, accumulator init, condition negation, int/float division,
recursive base case, sorting comparator, dict-default/KeyError, list slicing,
early-return-in-loop, swapped args, swapped return values, min/max mixed up).
No network, no randomness in the task shapes themselves.

HELD-OUT ISOLATION (structural, not a comment):
  * The visible data file below holds {task_id, description, buggy_source,
    visible_tests, sentinel_check}. Loaded by THIS module. This is everything
    the harness-improver (improve.py) is ever handed.
  * A SEPARATE sibling data file holds {task_id: [held_out_test, ...]}. This
    module never opens it, never imports a function that opens it, and never
    names its filename or its private loader here -- both identifiers are
    spelled only inside verify.py, which is the sole reader. Deliberately: a
    static scan (tests/test_learnos.py::test_improver_source_never_references_held_out_path)
    greps THIS file's and improve.py's source for those two literal
    identifiers and fails if either appears anywhere, including comments --
    so this docstring itself must not name them. A second, runtime check
    (test_visible_view_has_no_held_out_key) confirms ``load_visible_tasks()``
    never yields a held-out-shaped key.
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_VISIBLE_PATH = _DATA_DIR / "tasks_visible.json"

REQUIRED_VISIBLE_FIELDS = ("task_id", "description", "buggy_source", "visible_tests", "sentinel_check")


def load_visible_tasks() -> list[dict]:
    """Return the improver-visible view of every task. Never includes
    held-out test content -- callers (improve.py, run_v0.py) must not rely on
    anything beyond REQUIRED_VISIBLE_FIELDS being present."""
    raw = json.loads(_VISIBLE_PATH.read_text(encoding="utf-8"))
    tasks = []
    for t in raw:
        missing = [f for f in REQUIRED_VISIBLE_FIELDS if f not in t]
        if missing:
            raise ValueError(f"task {t.get('task_id')!r} missing fields: {missing}")
        assert "held_out_tests" not in t, "visible task view leaked held-out tests"
        tasks.append({k: t[k] for k in REQUIRED_VISIBLE_FIELDS})
    return tasks


def task_ids() -> list[str]:
    return [t["task_id"] for t in load_visible_tasks()]


def get_task(task_id: str) -> dict:
    for t in load_visible_tasks():
        if t["task_id"] == task_id:
            return t
    raise KeyError(f"unknown task_id: {task_id!r}")
