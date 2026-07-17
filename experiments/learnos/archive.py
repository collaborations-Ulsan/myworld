"""experiments/learnos/archive.py -- diversity-preserving archive (MAP-Elites-lite) for
LearnOS S+1 (docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md).

LEVI (2605.09764) lesson the S+1 design cites: a strong SEARCH *structure* (archive +
mutation routing) beats hill-climb-only optimization, often replacing a much larger model.
v0's ledger.py already gives an append-only log of every evaluated candidate; this module
adds the missing piece -- a behavior-descriptor CELL grid on top of that log, so search.py
can select DIVERSE parents instead of always mutating whichever candidate currently scores
highest (hill-climb-only, explicitly forbidden by the design doc).

CELL = (bug_kind, patch_shape):
  * bug_kind -- which category of bug the task represents (off_by_one, boundary,
    accumulator_init, ...). Derived from the task_id by substring match against a small
    ordered table: every task_id in this corpus already encodes its bug category in its
    name (see experiments/learnos/data/task_split.json's A/B pairing, which pairs tasks by
    this same category so a mined skill's transfer can be tested on a same-category-but-
    unseen sibling).
  * patch_shape -- a coarse structural signature of the candidate's patch source, computed
    with the stdlib `ast` module (loop? recursion? conditional? line-count bucket), plus
    the candidate kind (code_patch / cot_scaffold / tool) as a prefix so a tool and a
    code_patch mined for the same bug never collide into one cell.

Only the highest-scoring candidate per cell is kept as that cell's "elite" -- but the FULL
lineage (every candidate ever added, promoted or rejected) is retained separately in
`Archive.lineage()`, so nothing is silently discarded. That is the open-endedness the design
doc requires ("no hill-climb-only").

stdlib only (ast, dataclasses, random, collections).
"""
from __future__ import annotations

import ast
import collections
import random
from dataclasses import dataclass, field

# Ordered so more specific category names are checked before the generic ones they could
# otherwise be mistaken for (e.g. "list_slicing_off_by_one" must resolve to "list_slicing",
# not "off_by_one" -- see the ordering rationale in the module docstring).
_BUG_KIND_ORDER = (
    "wrong_operator",
    "boundary",
    "mutable_default",
    "comparison_direction",
    "string_reverse",
    "index_fencepost",
    "accumulator_init",
    "condition_negation",
    "float_int_division",
    "recursive_base_case",
    "sorting_comparator",
    "dict_default",
    "list_slicing",
    "early_return",
    "swapped_args",
    "swapped_return",
    "wrong_modulo",
    "min_max_mixed",
    "off_by_one",
)


def task_bug_kind(task_id: str) -> str:
    """Coarse bug-category tag for a task_id, used as one axis of the behavior descriptor.
    Deterministic substring match -- doesn't need semantic understanding, only a consistent
    bucketing so same-category A/B pairs land in the same cell family."""
    for kind in _BUG_KIND_ORDER:
        if kind in task_id:
            return kind
    return "other"


def patch_shape(kind: str, source: str) -> str:
    """Structural signature of a candidate's source, used as the other axis of the
    behavior descriptor. `kind` is one of code_patch/cot_scaffold/tool (ledger.VALID_KINDS)."""
    if kind == "cot_scaffold":
        return "cot_scaffold:prose"
    if not source or not source.strip():
        return f"{kind}:empty"
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return f"{kind}:unparsable"
    nodes = list(ast.walk(tree))
    has_loop = any(isinstance(n, (ast.For, ast.While)) for n in nodes)
    has_cond = any(isinstance(n, ast.If) for n in nodes)
    funcs = [n for n in nodes if isinstance(n, ast.FunctionDef)]
    func_names = {f.name for f in funcs}
    has_recursion = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in func_names
        for n in nodes
    )
    line_count = len([ln for ln in source.strip().splitlines() if ln.strip()])
    size_bucket = "short" if line_count <= 3 else ("medium" if line_count <= 8 else "long")
    tags = []
    if has_loop:
        tags.append("loop")
    if has_recursion:
        tags.append("recursion")
    if has_cond:
        tags.append("cond")
    if not tags:
        tags.append("straightline")
    return f"{kind}:{size_bucket}:{'+'.join(tags)}"


@dataclass(frozen=True)
class ArchiveEntry:
    candidate_id: str
    task_id: str
    bug_kind: str
    shape: str
    cell: str
    kind: str  # code_patch | cot_scaffold | tool
    score: float
    iter: int
    decision: str  # promoted | rejected
    parent_id: str | None
    mutation_kind: str | None
    content: str
    patch_source: str


def score_row(row: dict) -> float:
    """Score a ledger-shaped row for cell-elite comparison. Promoted beats any held-out
    gain beats any visible-only pass beats an outright reject -- monotone with the gate's
    own promotion discipline (improve.evaluate_candidate), never re-judges it."""
    if row.get("decision") == "promoted":
        return 2.0
    if row.get("holdout_pass"):
        return 1.0
    if row.get("visible_pass"):
        return 0.3
    return 0.0


class Archive:
    """Diversity-preserving archive: cell-elites (best-per-behavior-cell) + full lineage."""

    def __init__(self) -> None:
        self._cell_best: dict[str, ArchiveEntry] = {}
        self._lineage: list[ArchiveEntry] = []

    def add(self, entry: ArchiveEntry) -> bool:
        """Append to lineage unconditionally; update the cell-elite only if entry beats the
        current elite for its cell. Returns True iff it became (or stayed, on a tie broken
        by score) the new elite."""
        self._lineage.append(entry)
        current = self._cell_best.get(entry.cell)
        if current is None or entry.score > current.score:
            self._cell_best[entry.cell] = entry
            return True
        return False

    def add_row(self, row: dict) -> ArchiveEntry:
        """Build an ArchiveEntry from a ledger-shaped dict (candidate_id, task_id, kind,
        iter, decision, parent_id, plus the extra content/patch_source/mutation_kind fields
        search.py attaches) and archive it."""
        bug_kind = task_bug_kind(row["task_id"])
        source = row.get("patch_source") or row.get("content") or ""
        shape = patch_shape(row["kind"], source)
        cell = f"{bug_kind}::{shape}"
        entry = ArchiveEntry(
            candidate_id=row["candidate_id"],
            task_id=row["task_id"],
            bug_kind=bug_kind,
            shape=shape,
            cell=cell,
            kind=row["kind"],
            score=score_row(row),
            iter=row["iter"],
            decision=row["decision"],
            parent_id=row.get("parent_id"),
            mutation_kind=row.get("mutation_kind"),
            content=row.get("content", ""),
            patch_source=row.get("patch_source", ""),
        )
        self.add(entry)
        return entry

    def cells(self) -> dict[str, ArchiveEntry]:
        return dict(self._cell_best)

    def lineage(self) -> list[ArchiveEntry]:
        return list(self._lineage)

    def sample_parents(self, n: int, rng: random.Random) -> list[ArchiveEntry]:
        """Diversity-preserving selection: sample across DISTINCT cells first (shuffled, not
        best-score-first -- that would degrade to hill-climbing); only backfill from the full
        lineage (score-weighted) if there aren't enough distinct cells yet."""
        bests = list(self._cell_best.values())
        rng.shuffle(bests)
        if len(bests) >= n:
            return bests[:n]
        picked = list(bests)
        picked_ids = {e.candidate_id for e in picked}
        pool = [e for e in self._lineage if e.candidate_id not in picked_ids]
        pool.sort(key=lambda e: e.score, reverse=True)
        for e in pool:
            if len(picked) >= n:
                break
            picked.append(e)
        return picked

    def stats(self) -> dict:
        by_bug_kind = collections.Counter(e.bug_kind for e in self._cell_best.values())
        return {
            "num_cells": len(self._cell_best),
            "num_lineage": len(self._lineage),
            "distinct_bug_kinds_covered": len(by_bug_kind),
            "cells_per_bug_kind": dict(sorted(by_bug_kind.items())),
        }
