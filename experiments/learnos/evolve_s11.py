"""experiments/learnos/evolve_s11.py -- the LearnOS S+1.1 mining loop: S+1's SEARCH
structure (archive.py, search.py's mutation router + hypothesis/rewrite decoupling +
transfer-holdout statistics) REUSED unmodified, with the two fixes S+1's diagnosis demands
wired in on top (docs/AIOS_LEARNOS_S1_RESULTS_2026-07-17.md §5,
docs/AIOS_AGI_CONCEPTION_2026-07-17.md §10, docs/ontology/ledger/learning_methods.md §4):

  1. causal_gate.py gates every cot_scaffold/tool candidate the base gate
     (improve.evaluate_candidate) already promoted -- degeneracy pre-filter first (cheap),
     then causal ablation (WITH vs WITHOUT on held-out). A candidate that fails either check
     is downgraded to rejected HERE, before it ever reaches the shared pool.
  2. gene_pool.py's GenePool replaces search.py's Library as the shared-artifact store:
     MAP-Elites niches (bug_kind x capability), recessive retention with lineage, a
     per-niche resource cap, QD-score, and niche-matched-only retrieval (no
     blind-fallback-to-any-item -- the diagnosed noise source for B).

Everything else is imported from search.py, not copied: MutationRouter,
propose_hypothesis_then_rewrite, propose_reuse_scaffold/tool (called here with GenePool
content, not search.Library content -- the functions themselves don't know or care which
store the reused text came from), load_split, eval_task_baseline, group_success_rate,
wilson_ci, sign_test, compounding_curve. Per the task brief: "reuse S+1's ... search.py ...
do not rewrite."

HETEROGENEOUS MUTATION (learning_methods.md §4.4, Mutation-Without-Variation 2606.05408:
single-LLM mutation collapses diversity to ~10 unique templates): `HeterogeneousProposer`
routes each individual proposer call to either the local ollama backend or NVIDIA NIM
(backend.py, unmodified -- this only toggles backend.py's own AIOS_LEARNOS_BACKEND env
switch per call, exactly the interface backend.py's docstring describes) when a NIM key is
available, and records which operator served the call so every mining row and gene-pool
entry carries an honest `operator` field. The NIM key itself is never read, logged, or
returned by this module -- `nim_key_available()` only asks backend._load_nim_key() to
succeed-or-fail, discarding the value either way.

HELD-OUT ISOLATION: this module never references the held-out data file or its private
loader -- see tests/test_learnos_s11.py's grep-based structural guarantee (same discipline
as search.py / archive.py). It calls verify.run_holdout only through the same sanctioned,
aggregate-only-return call sites improve.py / causal_gate.py already use.

stdlib only.
"""
from __future__ import annotations

import os
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import archive as archive_mod
import backend
import causal_gate
import gene_pool as gene_pool_mod
import improve
import ledger
import search
import verify

Proposer = Callable[..., str]

DEFAULT_MAX_TASKS_PER_ITER = search.DEFAULT_MAX_TASKS_PER_ITER
DEFAULT_NICHE_CAP = gene_pool_mod.DEFAULT_NICHE_CAP
DEFAULT_NIM_FRACTION = 0.25


# ---- heterogeneous proposer ---------------------------------------------------------------
def nim_key_available() -> bool:
    """True iff backend._load_nim_key() would succeed right now. Never returns or logs the
    key itself -- only whether one is configured and readable."""
    try:
        backend._load_nim_key()
        return True
    except backend.ProposerError:
        return False


class HeterogeneousProposer:
    """Wraps backend.complete(), routing each call to 'ollama' or 'nim' via backend.py's own
    AIOS_LEARNOS_BACKEND env switch (backend.py itself is reused unmodified). `nim_fraction`
    of calls go to NIM when `nim_available`; the rest go to local ollama. `.last_operator`
    names whichever operator served the MOST RECENT call, so a caller can attribute a
    (possibly multi-call) candidate to the operator(s) that actually produced it."""

    def __init__(
        self,
        rng: random.Random,
        nim_available: bool,
        nim_fraction: float = DEFAULT_NIM_FRACTION,
        ollama_label: str | None = None,
        nim_label: str | None = None,
    ) -> None:
        self._rng = rng
        self._nim_available = nim_available
        self._nim_fraction = nim_fraction if nim_available else 0.0
        self.ollama_label = ollama_label or (
            f"ollama:{os.environ.get('AIOS_LEARNOS_OLLAMA_MODEL', backend.DEFAULT_OLLAMA_MODEL)}"
        )
        self.nim_label = nim_label or (
            f"nim:{os.environ.get('AIOS_LEARNOS_NIM_MODEL', backend.DEFAULT_NIM_MODEL)}"
        )
        self.last_operator = self.ollama_label
        self.call_operators: list[str] = []

    def __call__(self, prompt: str, **kwargs) -> str:
        use_nim = self._nim_available and self._rng.random() < self._nim_fraction
        choice = "nim" if use_nim else "ollama"
        self.last_operator = self.nim_label if use_nim else self.ollama_label
        self.call_operators.append(self.last_operator)
        prior = os.environ.get("AIOS_LEARNOS_BACKEND")
        os.environ["AIOS_LEARNOS_BACKEND"] = choice
        try:
            return backend.complete(prompt, **kwargs)
        finally:
            if prior is None:
                os.environ.pop("AIOS_LEARNOS_BACKEND", None)
            else:
                os.environ["AIOS_LEARNOS_BACKEND"] = prior


# ---- causal-gate bookkeeping ---------------------------------------------------------------
@dataclass
class CausalGateStats:
    scaffold_tool_candidates: int = 0
    degenerate_prefiltered: int = 0
    causal_rejected: int = 0
    causally_verified: int = 0

    def as_dict(self) -> dict:
        return {
            "scaffold_tool_candidates_considered": self.scaffold_tool_candidates,
            "degenerate_prefiltered": self.degenerate_prefiltered,
            "causal_rejected_no_responsibility": self.causal_rejected,
            "causally_verified_promoted": self.causally_verified,
        }


@dataclass
class SearchStateS11:
    archive: archive_mod.Archive = field(default_factory=archive_mod.Archive)
    router: search.MutationRouter = field(default_factory=search.MutationRouter)
    gene_pool: gene_pool_mod.GenePool = field(
        default_factory=lambda: gene_pool_mod.GenePool(niche_cap=DEFAULT_NICHE_CAP)
    )
    causal_stats: CausalGateStats = field(default_factory=CausalGateStats)


# ---- mutation selection + proposal (GenePool-backed, no blind fallback) -------------------
def _available_mutation_kinds_s11(pool: gene_pool_mod.GenePool, a_tasks: list[dict]) -> list[str]:
    kinds = list(search.MUTATION_KINDS)
    bug_kinds = {archive_mod.task_bug_kind(t["task_id"]) for t in a_tasks}
    has_scaffold_niche = any(pool.best_for(bk, "cot_scaffold") is not None for bk in bug_kinds)
    has_tool_niche = any(pool.best_for(bk, "tool") is not None for bk in bug_kinds)
    if not has_scaffold_niche:
        kinds.remove("reuse_scaffold")
    if not has_tool_niche:
        kinds.remove("reuse_tool")
    return kinds


def _propose_by_mutation_kind_s11(
    proposer: Proposer, task: dict, mutation_kind: str, pool: gene_pool_mod.GenePool, bug_kind: str
) -> tuple["improve.Candidate", str | None]:
    """Mirrors search._propose_by_mutation_kind but retrieves from GenePool (niche-matched
    ONLY). If the exact (bug_kind, capability) niche has no elite, reuse falls back to a
    FRESH proposal for this task -- never to an unrelated item (the diagnosed S+1 defect)."""
    if mutation_kind == "fresh_code_patch":
        return improve.propose_code_patch(proposer, task), None
    if mutation_kind == "fresh_scaffold":
        return improve.propose_scaffold(proposer, task), None
    if mutation_kind == "fresh_tool":
        return improve.propose_tool(proposer, task), None
    if mutation_kind == "hypothesis_then_rewrite":
        return search.propose_hypothesis_then_rewrite(proposer, task), None
    if mutation_kind == "reuse_scaffold":
        item = pool.best_for(bug_kind, "cot_scaffold")
        if item is None:
            return improve.propose_scaffold(proposer, task), None
        return search.propose_reuse_scaffold(proposer, task, item.content), item.item_id
    if mutation_kind == "reuse_tool":
        item = pool.best_for(bug_kind, "tool")
        if item is None:
            return improve.propose_tool(proposer, task), None
        return search.propose_reuse_tool(proposer, task, item.content), item.item_id
    raise ValueError(f"unknown mutation_kind: {mutation_kind!r}")


# ---- gate + causal ablation -----------------------------------------------------------------
def gate_and_maybe_ablate(
    task: dict,
    candidate: "improve.Candidate",
    baseline: int,
    proposer: Proposer,
    stats: CausalGateStats,
) -> dict:
    """Run improve.evaluate_candidate (REUSED, unmodified base gate); then, ONLY for a
    scaffold/tool candidate the base gate already promoted, run the degeneracy pre-filter
    and causal ablation on top. A candidate the base gate promoted but that fails either
    check is downgraded to rejected here -- `base_gate_decision` preserves the base gate's
    own verdict so nothing is silently overwritten, and `decision` is the final, causal-
    gate-aware verdict everything downstream (ledger, gene pool, router reward) uses."""
    evaluation = improve.evaluate_candidate(task, candidate, baseline)
    evaluation["base_gate_decision"] = evaluation["decision"]
    evaluation["degenerate_prefiltered"] = False
    evaluation["causally_responsible"] = None
    evaluation["causal_with_passed"] = None
    evaluation["causal_without_passed"] = None

    if evaluation["decision"] != "promoted" or candidate.kind not in ("cot_scaffold", "tool"):
        return evaluation

    stats.scaffold_tool_candidates += 1

    if candidate.kind == "tool":
        parsed = improve._parse_tool(candidate.content)
        if parsed is not None:
            degenerate, reason = causal_gate.is_degenerate_tool(
                candidate.content, parsed["fn_name"], parsed["post"]
            )
            if degenerate:
                stats.degenerate_prefiltered += 1
                evaluation["decision"] = "rejected"
                evaluation["degenerate_prefiltered"] = True
                evaluation["exploit_or_contract_audit"] = (
                    f"{evaluation['exploit_or_contract_audit']}; degenerate_prefilter:{reason}"
                )
                return evaluation

    causal = causal_gate.check_causal_responsibility(task, candidate, proposer=proposer)
    evaluation["causally_responsible"] = causal["causally_responsible"]
    evaluation["causal_with_passed"] = causal["with_passed"]
    evaluation["causal_without_passed"] = causal["without_passed"]
    if not causal["causally_responsible"]:
        stats.causal_rejected += 1
        evaluation["decision"] = "rejected"
        evaluation["exploit_or_contract_audit"] = (
            f"{evaluation['exploit_or_contract_audit']}; causal_ablation_failed"
            f"(with={causal['with_passed']} without={causal['without_passed']})"
        )
        return evaluation

    stats.causally_verified += 1
    return evaluation


# ---- one A-mining iteration ------------------------------------------------------------------
def mine_iteration_s11(
    iter_idx: int,
    proposer: Proposer,
    proposer_name: str,
    a_tasks: list[dict],
    state: SearchStateS11,
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
        available = _available_mutation_kinds_s11(state.gene_pool, a_tasks)
        mutation_kind = state.router.choose(rng, available)
        if progress_cb:
            progress_cb(f"  iter {iter_idx}: mining {task['task_id']!r} via {mutation_kind} ...")
        candidate, source_item_id = _propose_by_mutation_kind_s11(
            proposer, task, mutation_kind, state.gene_pool, bug_kind
        )
        operator = getattr(proposer, "last_operator", proposer_name)
        evaluation = gate_and_maybe_ablate(task, candidate, baseline, proposer, state.causal_stats)
        promoted = evaluation["decision"] == "promoted"
        state.router.update(mutation_kind, 1.0 if promoted else 0.0)
        if progress_cb:
            progress_cb(
                f"    -> {evaluation['decision']} (base_gate={evaluation['base_gate_decision']} "
                f"causally_responsible={evaluation['causally_responsible']})"
            )

        candidate_id = str(uuid.uuid4())
        row = {
            "candidate_id": candidate_id,
            "iter": iter_idx,
            "proposer": proposer_name,
            "parent_id": None,
            "replay_cmd": f"python experiments/learnos/run_s11.py --replay {candidate_id}",
            **evaluation,
            "content": candidate.content,
            "proposer_calls": candidate.proposer_calls,
            "mutation_kind": mutation_kind,
            "operator": operator,
            "group": "A",
        }
        row = ledger.append(row, path=ledger_path)
        rows.append(row)
        state.archive.add_row(row)

        if promoted and source_item_id:
            # a REUSE of an existing gene-pool item was promoted (and causally verified on
            # THIS task) -- credit the original item, don't mint a near-duplicate entry.
            state.gene_pool.record_reuse(source_item_id)
        elif promoted and not audit_frozen and candidate.kind in ("cot_scaffold", "tool"):
            entry = gene_pool_mod.GeneEntry(
                item_id=candidate_id,
                niche=gene_pool_mod.niche_key(bug_kind, candidate.kind),
                bug_kind=bug_kind,
                capability=candidate.kind,
                content=candidate.content,
                patch_source=candidate.patch_source,
                task_id=task["task_id"],
                iter=iter_idx,
                score=archive_mod.score_row(row),
                operator=operator,
                causally_responsible=True,
                with_passed=evaluation["causal_with_passed"] or 0,
                without_passed=evaluation["causal_without_passed"] or 0,
            )
            state.gene_pool.add(entry)
    return rows


# ---- B / sentinel transfer-holdout evaluation (gene-pool augmented, no blind fallback) -----
def eval_task_gene_pool_augmented(proposer: Proposer, task: dict, pool: gene_pool_mod.GenePool) -> dict:
    """Same shape as search.eval_task_library_augmented, but retrieval is niche-matched ONLY
    (GenePool.best_for never falls back to an unrelated bug_kind's item) -- a B task whose
    bug_kind has no A-mined, causally-verified elite gets NO augmentation at all, rather than
    an irrelevant scaffold/tool injected as noise."""
    bug_kind = archive_mod.task_bug_kind(task["task_id"])
    scaffold_item = pool.best_for(bug_kind, "cot_scaffold")
    tool_item = pool.best_for(bug_kind, "tool")
    extra_parts = []
    if scaffold_item:
        extra_parts.append(
            f"Follow this reasoning approach (mined from a related task, causally-verified):\n{scaffold_item.content}"
        )
    if tool_item:
        extra_parts.append(
            f"You may define and call this helper if useful:\n```python\n{tool_item.content}```"
        )
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
        "mode": "gene_pool",
        "holdout": holdout,
        "used_scaffold": bool(scaffold_item),
        "used_tool": bool(tool_item),
    }


def evaluate_group_s11(
    proposer: Proposer, group_tasks: list[dict], mode: str, pool: gene_pool_mod.GenePool | None = None
) -> list[dict]:
    if mode == "baseline":
        return [search.eval_task_baseline(proposer, t) for t in group_tasks]
    if mode == "gene_pool":
        if pool is None:
            raise ValueError("gene_pool mode requires a GenePool instance")
        return [eval_task_gene_pool_augmented(proposer, t, pool) for t in group_tasks]
    raise ValueError(f"unknown mode: {mode!r}")


# ---- top-level orchestration -----------------------------------------------------------------
def run_search_s11(
    n_iterations: int,
    proposer: Proposer,
    proposer_name: str,
    max_tasks_per_iter: int = DEFAULT_MAX_TASKS_PER_ITER,
    ledger_path: Path | None = None,
    split: dict | None = None,
    audit_frozen: bool = False,
    seed: int = 0,
    niche_cap: int = DEFAULT_NICHE_CAP,
    b_eval_every_change_only: bool = True,
    all_tasks: dict[str, dict] | None = None,
    progress_cb: Callable[[str], None] | None = None,
) -> dict:
    import tasks as tasks_mod

    split = split or search.load_split()
    assert not (set(split["A"]) & set(split["B"])), "A/B split overlap -- transfer-holdout invalid"
    assert not (set(split["A"]) & set(split["sentinel"])), "A/sentinel split overlap"
    assert not (set(split["B"]) & set(split["sentinel"])), "B/sentinel split overlap"

    pool_tasks = all_tasks if all_tasks is not None else {t["task_id"]: t for t in tasks_mod.load_visible_tasks()}
    a_tasks = [pool_tasks[t] for t in split["A"]]
    b_tasks = [pool_tasks[t] for t in split["B"]]
    sentinel_tasks = [pool_tasks[t] for t in split["sentinel"]]

    rng = random.Random(seed)
    state = SearchStateS11(gene_pool=gene_pool_mod.GenePool(niche_cap=niche_cap))

    if progress_cb:
        progress_cb(
            f"[iter -1] baseline (no-pool) readout: {len(b_tasks)} B tasks + {len(sentinel_tasks)} sentinel tasks ..."
        )
    baseline_b = evaluate_group_s11(proposer, b_tasks, "baseline")
    baseline_sentinel = evaluate_group_s11(proposer, sentinel_tasks, "baseline")
    base_b_s, base_b_n = search.group_success_rate(baseline_b)
    base_sent_s, base_sent_n = search.group_success_rate(baseline_sentinel)
    if progress_cb:
        progress_cb(f"[iter -1] baseline B={base_b_s}/{base_b_n}  sentinel={base_sent_s}/{base_sent_n}")

    b_records = [{"iter": -1, "successes": base_b_s, "total": base_b_n}]
    sentinel_records = [{"iter": -1, "successes": base_sent_s, "total": base_sent_n}]
    last_signature = state.gene_pool.signature()

    all_mining_rows = []
    for it in range(n_iterations):
        if progress_cb:
            progress_cb(f"[iter {it}] mining {min(max_tasks_per_iter, len(a_tasks))} A task(s) ...")
        rows = mine_iteration_s11(
            it, proposer, proposer_name, a_tasks, state, max_tasks_per_iter, rng,
            ledger_path=ledger_path, audit_frozen=audit_frozen, progress_cb=progress_cb,
        )
        all_mining_rows.extend(rows)

        sig = state.gene_pool.signature()
        is_checkpoint = it == n_iterations - 1 or sig != last_signature or not b_eval_every_change_only
        if is_checkpoint:
            last_signature = sig
            if progress_cb:
                progress_cb(f"[iter {it}] gene pool changed (niches={len(state.gene_pool.niches())}) -- B/sentinel checkpoint ...")
            lib_b = evaluate_group_s11(proposer, b_tasks, "gene_pool", state.gene_pool)
            s, n = search.group_success_rate(lib_b)
            b_records.append({"iter": it, "successes": s, "total": n})
            lib_sentinel = evaluate_group_s11(proposer, sentinel_tasks, "gene_pool", state.gene_pool)
            s2, n2 = search.group_success_rate(lib_sentinel)
            sentinel_records.append({"iter": it, "successes": s2, "total": n2})
            if progress_cb:
                progress_cb(f"[iter {it}] checkpoint B={s}/{n}  sentinel={s2}/{n2}")

    b_curve = search.compounding_curve(b_records)
    sentinel_curve = search.compounding_curve(sentinel_records)

    if progress_cb:
        progress_cb("[final] re-evaluating B under the final gene pool for the paired sign test ...")
    pre_pass = [r["holdout"].get("all_passed", False) for r in baseline_b]
    final_lib_b = evaluate_group_s11(proposer, b_tasks, "gene_pool", state.gene_pool)
    post_pass = [r["holdout"].get("all_passed", False) for r in final_lib_b]
    paired_stats = search.sign_test(pre_pass, post_pass)

    return {
        "mining_rows": all_mining_rows,
        "archive_stats": state.archive.stats(),
        "router_yields": state.router.yields(),
        "router_counts": dict(state.router.counts),
        "causal_gate_stats": state.causal_stats.as_dict(),
        "gene_pool_stats": state.gene_pool.stats(),
        "gene_pool_items": [
            {
                "item_id": e.item_id, "niche": e.niche, "capability": e.capability, "bug_kind": e.bug_kind,
                "mined_task_id": e.task_id, "mined_iter": e.iter, "operator": e.operator,
                "with_passed": e.with_passed, "without_passed": e.without_passed,
                "reused": state.gene_pool.reuse_count(e.item_id),
            }
            for e in state.gene_pool.niches().values()
        ],
        "b_curve": b_curve,
        "sentinel_curve": sentinel_curve,
        "paired_stats": paired_stats,
        "audit_frozen": audit_frozen,
        "split": split,
    }
