"""experiments/learnos/search.py -- the S+1 evolutionary SEARCH loop
(docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md), replacing v0's linear per-task improver with:

  1. an ARCHIVE (archive.py) instead of hill-climbing -- every mined candidate is filed into
     a diversity cell, not just compared to "the current best for this task".
  2. a MUTATION ROUTER -- a simple observed-yield bandit over candidate-generation
     strategies (fresh code_patch / fresh scaffold / fresh tool / hypothesis-then-rewrite /
     reuse an already-promoted scaffold / reuse an already-promoted tool), so search shifts
     toward whichever strategy is actually promoting.
  3. hypothesis-generation DECOUPLED from rewriting (VISTA 2603.18388: a defect seed
     degraded GEPA 23.81 -> 13.50 when one call both diagnosed and rewrote; separating the
     two calls recovered to 87.57). `propose_hypothesis_then_rewrite` is exactly two
     independent proposer calls, never one call doing both jobs.
  4. the TRANSFER-HOLDOUT compounding measurement -- v0's decisive missing piece. Mining
     (`mine_iteration`) ONLY ever touches A-split tasks; skills/tools/scaffolds only ever
     enter the shared Library from an A-mined, gate-PROMOTED candidate. The compounding
     metric is the held-out success rate on B (`evaluate_group(..., "library", ...)`) as a
     function of iteration -- B tasks are NEVER mined, only read via verify.run_holdout,
     which (same isolation guarantee as v0) returns aggregate pass counts only, never test
     source or per-test error detail.

HELD-OUT / TRANSFER ISOLATION (structural, not a comment, mirrored from tasks.py's
discipline): this module never references the held-out data file or its private loader --
see tests/test_learnos_s1.py::test_search_and_archive_never_reference_held_out_path, which
greps this file's (and archive.py's) source for the two forbidden identifiers. Mining
functions (`mine_iteration`, `_propose_by_mutation_kind`) take an explicit `a_tasks`/`task`
argument and never see the B or sentinel task lists -- see
test_mine_iteration_never_touches_tasks_outside_its_pool.

stdlib only (json, math, random, uuid, dataclasses).
"""
from __future__ import annotations

import json
import math
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import archive as archive_mod
import improve
import ledger
import tasks
import verify

Proposer = Callable[..., str]

_SPLIT_PATH = Path(__file__).resolve().parent / "data" / "task_split.json"

MUTATION_KINDS = (
    "fresh_code_patch",
    "fresh_scaffold",
    "fresh_tool",
    "hypothesis_then_rewrite",
    "reuse_scaffold",
    "reuse_tool",
)

DEFAULT_MAX_TASKS_PER_ITER = 3


# ---- task split -------------------------------------------------------------------------
def load_split() -> dict:
    raw = json.loads(_SPLIT_PATH.read_text(encoding="utf-8"))
    return {"A": list(raw["A"]), "B": list(raw["B"]), "sentinel": list(raw["sentinel"])}


def _tasks_by_id(ids: list[str], pool: dict[str, dict]) -> list[dict]:
    return [pool[tid] for tid in ids]


# ---- mutation router (observed-yield bandit) --------------------------------------------
@dataclass
class MutationRouter:
    epsilon: float = 0.25
    counts: dict[str, int] = field(default_factory=lambda: {k: 0 for k in MUTATION_KINDS})
    rewards: dict[str, float] = field(default_factory=lambda: {k: 0.0 for k in MUTATION_KINDS})

    def mean(self, kind: str) -> float:
        c = self.counts[kind]
        return (self.rewards[kind] / c) if c else 0.0

    def choose(self, rng: random.Random, available: list[str] | None = None) -> str:
        arms = available if available else list(MUTATION_KINDS)
        unseen = [a for a in arms if self.counts[a] == 0]
        if unseen:
            return rng.choice(unseen)  # explore every arm at least once before exploiting
        if rng.random() < self.epsilon:
            return rng.choice(arms)
        best_mean = max(self.mean(a) for a in arms)
        best = [a for a in arms if self.mean(a) == best_mean]
        return rng.choice(best)

    def update(self, kind: str, reward: float) -> None:
        self.counts[kind] += 1
        self.rewards[kind] += reward

    def yields(self) -> dict[str, float]:
        return {k: self.mean(k) for k in MUTATION_KINDS}


# ---- shared skill/tool library (promoted A-mined artifacts ONLY) ------------------------
@dataclass
class LibraryItem:
    item_id: str
    kind: str  # cot_scaffold | tool
    content: str
    bug_kind: str
    mined_task_id: str
    mined_iter: int
    promotions: int = 0  # how many times a candidate that REUSED this item later got promoted


class Library:
    def __init__(self) -> None:
        self.items: list[LibraryItem] = []

    def add(self, item: LibraryItem) -> None:
        self.items.append(item)

    def items_of(self, kind: str) -> list[LibraryItem]:
        return [i for i in self.items if i.kind == kind]

    def best_for(self, bug_kind: str, kind: str) -> LibraryItem | None:
        pool = [i for i in self.items_of(kind) if i.bug_kind == bug_kind]
        if not pool:
            pool = self.items_of(kind)
        if not pool:
            return None
        return max(pool, key=lambda i: i.promotions)

    def record_reuse_promotion(self, item_id: str) -> None:
        for item in self.items:
            if item.item_id == item_id:
                item.promotions += 1
                return

    def signature(self) -> tuple:
        return tuple(sorted(i.item_id for i in self.items))


@dataclass
class SearchState:
    archive: archive_mod.Archive = field(default_factory=archive_mod.Archive)
    router: MutationRouter = field(default_factory=MutationRouter)
    library: Library = field(default_factory=Library)


# ---- hypothesis-generation DECOUPLED from rewriting (VISTA) -----------------------------
def _prompt_hypothesis(task: dict) -> str:
    return (
        "You are DIAGNOSING (not fixing) a small Python bug. In 1-3 sentences, state WHAT "
        "is wrong and WHY. No code, no fences, no fix.\n\n"
        f"Buggy source:\n```python\n{task['buggy_source']}```\n\n"
        "Tests it must pass:\n" + "\n".join(f"- {t}" for t in task["visible_tests"])
    )


def propose_hypothesis_then_rewrite(proposer: Proposer, task: dict) -> improve.Candidate:
    """Two SEPARATE proposer calls: one that only diagnoses, one that only rewrites given
    the diagnosis. VISTA (2603.18388) showed collapsing this into one call is exactly what
    degrades quality under a defect seed (23.81 -> 13.50); separating recovers it (87.57)."""
    hypothesis = proposer(_prompt_hypothesis(task)).strip()
    extra = f"Diagnosis from a separate reasoning pass (trust it, do not re-diagnose):\n{hypothesis}"
    patch_text = proposer(improve._prompt_code_patch(task, extra_context=extra))
    patch_source = improve._extract_code(patch_text)
    return improve.Candidate(
        kind="code_patch",
        content=patch_source,
        patch_source=patch_source,
        proposer_calls=2,
        meta={"hypothesis": hypothesis},
    )


# ---- reuse mutations (adapt an already-PROMOTED library item to a NEW A task) -----------
def propose_reuse_scaffold(proposer: Proposer, task: dict, scaffold_text: str) -> improve.Candidate:
    extra = f"Follow this reasoning approach (reused from a previously PROMOTED scaffold):\n{scaffold_text}"
    patch_text = proposer(improve._prompt_code_patch(task, extra_context=extra))
    patch_source = improve._extract_code(patch_text)
    return improve.Candidate(
        kind="cot_scaffold", content=scaffold_text, patch_source=patch_source,
        proposer_calls=1, meta={"reused": True},
    )


def propose_reuse_tool(proposer: Proposer, task: dict, tool_source: str) -> improve.Candidate:
    extra = f"You may define and call this previously PROMOTED helper if useful:\n```python\n{tool_source}```"
    patch_text = proposer(improve._prompt_code_patch(task, extra_context=extra))
    patch_source = improve._extract_code(patch_text)
    full_patch_source = (tool_source + "\n" + patch_source) if patch_source.strip() else patch_source
    return improve.Candidate(
        kind="tool", content=tool_source, patch_source=full_patch_source,
        proposer_calls=1, meta={"reused": True},
    )


def _propose_by_mutation_kind(
    proposer: Proposer, task: dict, mutation_kind: str, library: Library, bug_kind: str
) -> tuple[improve.Candidate, str | None]:
    """Returns (candidate, source_item_id_or_None) -- the item_id is set only for
    reuse_scaffold/reuse_tool, so the caller can credit that library item on promotion."""
    if mutation_kind == "fresh_code_patch":
        return improve.propose_code_patch(proposer, task), None
    if mutation_kind == "fresh_scaffold":
        return improve.propose_scaffold(proposer, task), None
    if mutation_kind == "fresh_tool":
        return improve.propose_tool(proposer, task), None
    if mutation_kind == "hypothesis_then_rewrite":
        return propose_hypothesis_then_rewrite(proposer, task), None
    if mutation_kind == "reuse_scaffold":
        item = library.best_for(bug_kind, "cot_scaffold")
        if item is None:
            return improve.propose_scaffold(proposer, task), None
        return propose_reuse_scaffold(proposer, task, item.content), item.item_id
    if mutation_kind == "reuse_tool":
        item = library.best_for(bug_kind, "tool")
        if item is None:
            return improve.propose_tool(proposer, task), None
        return propose_reuse_tool(proposer, task, item.content), item.item_id
    raise ValueError(f"unknown mutation_kind: {mutation_kind!r}")


def _available_mutation_kinds(library: Library) -> list[str]:
    kinds = list(MUTATION_KINDS)
    if not library.items_of("cot_scaffold"):
        kinds.remove("reuse_scaffold")
    if not library.items_of("tool"):
        kinds.remove("reuse_tool")
    return kinds


# ---- one A-mining iteration (skills/tools/scaffolds are extracted ONLY from A) ----------
def mine_iteration(
    iter_idx: int,
    proposer: Proposer,
    proposer_name: str,
    a_tasks: list[dict],
    state: SearchState,
    max_tasks_per_iter: int = DEFAULT_MAX_TASKS_PER_ITER,
    rng: random.Random | None = None,
    ledger_path: Path | None = None,
    audit_frozen: bool = False,
    progress_cb: Callable[[str], None] | None = None,
) -> list[dict]:
    rng = rng or random.Random(0)
    already_promoted = ledger.promoted_task_ids(ledger_path)
    batch = improve.sample_tasks(a_tasks, already_promoted, max_tasks_per_iter)
    rows = []
    for task in batch:
        bug_kind = archive_mod.task_bug_kind(task["task_id"])
        baseline = improve.baseline_holdout_passed(task)
        available = _available_mutation_kinds(state.library)
        mutation_kind = state.router.choose(rng, available)
        if progress_cb:
            progress_cb(f"  iter {iter_idx}: mining {task['task_id']!r} via {mutation_kind} ...")
        candidate, source_item_id = _propose_by_mutation_kind(
            proposer, task, mutation_kind, state.library, bug_kind
        )
        evaluation = improve.evaluate_candidate(task, candidate, baseline)
        promoted = evaluation["decision"] == "promoted"
        state.router.update(mutation_kind, 1.0 if promoted else 0.0)
        if progress_cb:
            progress_cb(f"    -> {evaluation['decision']} (visible={evaluation['visible_pass']} holdout={evaluation['holdout_pass']})")

        candidate_id = str(uuid.uuid4())
        row = {
            "candidate_id": candidate_id,
            "iter": iter_idx,
            "proposer": proposer_name,
            "parent_id": None,
            "replay_cmd": f"python experiments/learnos/run_s1.py --replay {candidate_id}",
            **evaluation,
            "content": candidate.content,
            "proposer_calls": candidate.proposer_calls,
            "mutation_kind": mutation_kind,
            "group": "A",
        }
        row = ledger.append(row, path=ledger_path)
        rows.append(row)
        state.archive.add_row(row)

        if promoted and source_item_id:
            # a REUSE of an existing item was promoted -- credit the original item, don't
            # file a near-duplicate new one (that would silently inflate library_size with
            # copies instead of tracking genuinely NEW mined skills).
            state.library.record_reuse_promotion(source_item_id)
        elif promoted and not audit_frozen and candidate.kind in ("cot_scaffold", "tool"):
            state.library.add(
                LibraryItem(
                    item_id=candidate_id,
                    kind=candidate.kind,
                    content=candidate.content,
                    bug_kind=bug_kind,
                    mined_task_id=task["task_id"],
                    mined_iter=iter_idx,
                )
            )
    return rows


# ---- B / sentinel transfer-holdout evaluation (never mines; readout only) ---------------
def eval_task_baseline(proposer: Proposer, task: dict) -> dict:
    """iter -1 / no-library readout: a direct code_patch attempt, no scaffold/tool
    augmentation. Constant across iterations (doesn't depend on the library)."""
    text = proposer(improve._prompt_code_patch(task))
    patch_source = improve._extract_code(text)
    holdout = (
        verify.run_holdout(task["task_id"], patch_source)
        if patch_source.strip()
        else {"passed": 0, "total": None, "all_passed": False, "timed_out": False, "error": "empty_patch"}
    )
    return {"task_id": task["task_id"], "mode": "baseline", "holdout": holdout}


def eval_task_library_augmented(proposer: Proposer, task: dict, library: Library) -> dict:
    """Library-augmented readout: pick the best-matching PROMOTED artifact (mined only from
    A) for this task's bug_kind and offer it as context, mirroring how a real skill/tool/
    scaffold would be reused on an unseen task. verify.run_holdout is the same sanctioned,
    aggregate-only-return call site improve.py's gate uses -- no new held-out reader."""
    bug_kind = archive_mod.task_bug_kind(task["task_id"])
    scaffold_item = library.best_for(bug_kind, "cot_scaffold")
    tool_item = library.best_for(bug_kind, "tool")
    extra_parts = []
    if scaffold_item:
        extra_parts.append(f"Follow this reasoning approach (mined from a related task):\n{scaffold_item.content}")
    if tool_item:
        extra_parts.append(f"You may define and call this helper if useful:\n```python\n{tool_item.content}```")
    extra = "\n\n".join(extra_parts) if extra_parts else None
    text = proposer(improve._prompt_code_patch(task, extra_context=extra))
    patch_source = improve._extract_code(text)
    if tool_item and patch_source.strip():
        patch_source = tool_item.content + "\n" + patch_source
    holdout = (
        verify.run_holdout(task["task_id"], patch_source)
        if patch_source.strip()
        else {"passed": 0, "total": None, "all_passed": False, "timed_out": False, "error": "empty_patch"}
    )
    return {
        "task_id": task["task_id"],
        "mode": "library",
        "holdout": holdout,
        "used_scaffold": bool(scaffold_item),
        "used_tool": bool(tool_item),
    }


def evaluate_group(
    proposer: Proposer, group_tasks: list[dict], mode: str, library: Library | None = None
) -> list[dict]:
    if mode == "baseline":
        return [eval_task_baseline(proposer, t) for t in group_tasks]
    if mode == "library":
        if library is None:
            raise ValueError("library mode requires a Library instance")
        return [eval_task_library_augmented(proposer, t, library) for t in group_tasks]
    raise ValueError(f"unknown mode: {mode!r}")


def group_success_rate(results: list[dict]) -> tuple[int, int]:
    successes = sum(1 for r in results if r["holdout"].get("all_passed"))
    return successes, len(results)


# ---- statistics (no compounding claim without the curve + this caveat) ------------------
def wilson_ci(successes: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    """95% Wilson score interval -- stdlib math only, valid at small n unlike the naive
    normal approximation."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def sign_test(pre_pass: list[bool], post_pass: list[bool]) -> dict:
    """Exact paired sign test (McNemar's exact test) comparing PRE (iter -1 baseline) vs
    POST (a later-iteration library-augmented run) pass/fail on the SAME held-out task set,
    in the SAME order. b = pre-fail -> post-pass ("improved"), c = pre-pass -> post-fail
    ("regressed"); under the null of no directional effect, min(b, c) ~ Binomial(b+c, 0.5).
    stdlib-only (math.comb). This is deliberately a LOW-power test at the n this run uses --
    the caller must report that caveat alongside any p-value, per the design doc's "no
    compounding claim without the B-curve + statistical caveat"."""
    if len(pre_pass) != len(post_pass):
        raise ValueError("pre_pass and post_pass must be paired (same length, same order)")
    improved = sum(1 for pre, post in zip(pre_pass, post_pass) if (not pre) and post)
    regressed = sum(1 for pre, post in zip(pre_pass, post_pass) if pre and (not post))
    n = improved + regressed
    if n == 0:
        p_value = 1.0
    else:
        k = min(improved, regressed)
        tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2**n)
        p_value = min(1.0, 2 * tail)
    return {
        "n_pairs": len(pre_pass),
        "improved": improved,
        "regressed": regressed,
        "n_discordant": n,
        "p_value_two_sided": p_value,
    }


def compounding_curve(records: list[dict]) -> dict:
    """records: [{"iter": int, "successes": int, "total": int}, ...]. Returns per-point
    rate + Wilson CI, sorted by iter, plus a bare final-vs-first rising/falling/flat read
    (NOT a significance claim by itself -- see sign_test)."""
    points = []
    for r in sorted(records, key=lambda r: r["iter"]):
        total = r["total"] or 0
        rate = (r["successes"] / total) if total else 0.0
        lo, hi = wilson_ci(r["successes"], total)
        points.append(
            {"iter": r["iter"], "successes": r["successes"], "total": total, "rate": rate, "ci_lo": lo, "ci_hi": hi}
        )
    if len(points) >= 2:
        rising = points[-1]["rate"] > points[0]["rate"]
        falling = points[-1]["rate"] < points[0]["rate"]
        flat = points[-1]["rate"] == points[0]["rate"]
    else:
        rising = falling = flat = False
    return {"points": points, "final_vs_first": {"rising": rising, "falling": falling, "flat": flat}}


# ---- top-level orchestration --------------------------------------------------------------
def run_search(
    n_iterations: int,
    proposer: Proposer,
    proposer_name: str,
    max_tasks_per_iter: int = DEFAULT_MAX_TASKS_PER_ITER,
    ledger_path: Path | None = None,
    split: dict | None = None,
    audit_frozen: bool = False,
    seed: int = 0,
    b_eval_every_change_only: bool = True,
    all_tasks: dict[str, dict] | None = None,
    progress_cb: Callable[[str], None] | None = None,
) -> dict:
    split = split or load_split()
    assert not (set(split["A"]) & set(split["B"])), "A/B split overlap -- transfer-holdout invalid"
    assert not (set(split["A"]) & set(split["sentinel"])), "A/sentinel split overlap"
    assert not (set(split["B"]) & set(split["sentinel"])), "B/sentinel split overlap"

    pool = all_tasks if all_tasks is not None else {t["task_id"]: t for t in tasks.load_visible_tasks()}
    a_tasks = _tasks_by_id(split["A"], pool)
    b_tasks = _tasks_by_id(split["B"], pool)
    sentinel_tasks = _tasks_by_id(split["sentinel"], pool)

    rng = random.Random(seed)
    state = SearchState()

    if progress_cb:
        progress_cb(f"[iter -1] baseline (no-library) readout: {len(b_tasks)} B tasks + {len(sentinel_tasks)} sentinel tasks ...")
    baseline_b = evaluate_group(proposer, b_tasks, "baseline")
    baseline_sentinel = evaluate_group(proposer, sentinel_tasks, "baseline")
    base_b_s, base_b_n = group_success_rate(baseline_b)
    base_sent_s, base_sent_n = group_success_rate(baseline_sentinel)
    if progress_cb:
        progress_cb(f"[iter -1] baseline B={base_b_s}/{base_b_n}  sentinel={base_sent_s}/{base_sent_n}")

    b_records = [{"iter": -1, "successes": base_b_s, "total": base_b_n}]
    sentinel_records = [{"iter": -1, "successes": base_sent_s, "total": base_sent_n}]
    last_signature = state.library.signature()

    all_mining_rows = []
    for it in range(n_iterations):
        if progress_cb:
            progress_cb(f"[iter {it}] mining {min(max_tasks_per_iter, len(a_tasks))} A task(s) ...")
        rows = mine_iteration(
            it, proposer, proposer_name, a_tasks, state, max_tasks_per_iter, rng,
            ledger_path=ledger_path, audit_frozen=audit_frozen, progress_cb=progress_cb,
        )
        all_mining_rows.extend(rows)

        sig = state.library.signature()
        is_checkpoint = it == n_iterations - 1 or sig != last_signature or not b_eval_every_change_only
        if is_checkpoint:
            last_signature = sig
            if progress_cb:
                progress_cb(f"[iter {it}] library changed (size={len(state.library.items)}) -- B/sentinel checkpoint ...")
            lib_b = evaluate_group(proposer, b_tasks, "library", state.library)
            s, n = group_success_rate(lib_b)
            b_records.append({"iter": it, "successes": s, "total": n})
            lib_sentinel = evaluate_group(proposer, sentinel_tasks, "library", state.library)
            s2, n2 = group_success_rate(lib_sentinel)
            sentinel_records.append({"iter": it, "successes": s2, "total": n2})
            if progress_cb:
                progress_cb(f"[iter {it}] checkpoint B={s}/{n}  sentinel={s2}/{n2}")

    b_curve = compounding_curve(b_records)
    sentinel_curve = compounding_curve(sentinel_records)

    if progress_cb:
        progress_cb("[final] re-evaluating B under the final library for the paired sign test ...")
    pre_pass = [r["holdout"].get("all_passed", False) for r in baseline_b]
    final_lib_b = evaluate_group(proposer, b_tasks, "library", state.library)
    post_pass = [r["holdout"].get("all_passed", False) for r in final_lib_b]
    paired_stats = sign_test(pre_pass, post_pass)

    return {
        "mining_rows": all_mining_rows,
        "archive_stats": state.archive.stats(),
        "router_yields": state.router.yields(),
        "router_counts": dict(state.router.counts),
        "library_size": len(state.library.items),
        "library_items": [
            {"item_id": i.item_id, "kind": i.kind, "bug_kind": i.bug_kind, "mined_task_id": i.mined_task_id,
             "mined_iter": i.mined_iter, "promotions": i.promotions}
            for i in state.library.items
        ],
        "b_curve": b_curve,
        "sentinel_curve": sentinel_curve,
        "paired_stats": paired_stats,
        "audit_frozen": audit_frozen,
        "split": split,
    }
