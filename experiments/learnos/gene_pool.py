"""experiments/learnos/gene_pool.py -- MAP-Elites gene-pool archive for LearnOS S+1.1
(docs/ontology/ledger/learning_methods.md §4, the D6-grounded redesign the founder's
"leave genes behind / extract recessive traits / speciate" directive converges on; also
docs/AIOS_AGI_CONCEPTION_2026-07-17.md §10's pivot).

Builds ON archive.py's existing helpers (task_bug_kind is imported and reused) but does
NOT modify archive.py and does NOT reuse archive.py's Archive class directly -- this module
defines its OWN, coarser niche key for shared-LIBRARY-RETRIEVAL purposes: (bug_kind,
capability) where capability = candidate kind (cot_scaffold | tool). That's deliberately
coarser than archive.py's diversity cell (bug_kind x patch_shape, which also buckets by
structural shape for search.py's own parent-sampling diversity) because gene_pool.py answers
a different question -- "is there a causally-verified tool/scaffold for THIS bug_kind" -- not
"what's the most different-shaped candidate to mutate next."

THE DIAGNOSED BUG THIS FIXES (docs/AIOS_LEARNOS_S1_RESULTS_2026-07-17.md §5): S+1's
search.Library.best_for() fell back to *any* item of the requested kind when no bug_kind
match existed, injecting unrelated tools/scaffolds into unrelated B tasks' prompts as noise
(the concrete failures were `wrong_operator_inclusive_bounds` picking up an irrelevant
`mutable_default` tool via fallback, and `swapped_args_percent_of` getting a totally
unrelated scaffold+tool). GenePool.best_for() returns None on a niche miss. No fallback,
ever -- callers (evolve_s11.py) must treat a niche miss as "no augmentation available",
never "grab the nearest thing".

Per learning_methods.md §4's four numbered redesign points:
  1. one ELITE per niche (speciation) -- add() only replaces a niche's elite if the new
     entry's score is strictly higher; the previous elite (if any) demotes into the
     niche's recessive pool rather than being discarded.
  2. a RECESSIVE pool per niche -- non-champion but still causally-verified entries are
     retained (with lineage), so a later mining pass could recombine/recover them even
     though they didn't win their niche. (Recombination itself is out of scope for this
     sprint -- retention with lineage is the piece this task asked for.)
  3. a per-niche resource cap (minimal-criterion style, GECCO 2020 "everyone farms the
     easiest maze") -- once elite+recessive together exceed `niche_cap` for a niche, the
     WEAKEST recessive entries are evicted first (the elite is never evicted); a niche
     cannot grow without bound and crowd out the pool's total retained budget.
  4. QD-score (not pass@1) -- sum of elite scores across all filled niches; this is the
     "how much of the behavior space is covered, and how well" headline metric this design
     reports instead of a single scalar pass rate.

Every entry admitted here must ALREADY have survived causal_gate.py's ablation check
(causally_responsible=True) -- gene_pool.py does not re-run that check itself; add()'s
`require_causal_verified` flag (default True) is a defense-in-depth guard so a caller can't
accidentally add an unverified candidate to the shared pool.

stdlib only (collections, dataclasses).
"""
from __future__ import annotations

import collections
from dataclasses import dataclass

DEFAULT_NICHE_CAP = 3


class GenePoolError(Exception):
    pass


def niche_key(bug_kind: str, capability: str) -> str:
    return f"{bug_kind}::{capability}"


@dataclass(frozen=True)
class GeneEntry:
    item_id: str
    niche: str            # niche_key(bug_kind, capability)
    bug_kind: str
    capability: str       # "cot_scaffold" | "tool"
    content: str           # scaffold text / tool source
    patch_source: str
    task_id: str            # the A task this was mined from
    iter: int
    score: float
    operator: str            # which proposer backend produced this candidate
    causally_responsible: bool
    with_passed: int
    without_passed: int
    parent_id: str | None = None


class GenePool:
    """MAP-Elites gene pool: one elite per (bug_kind, capability) niche, a per-niche
    recessive pool (capped), full lineage, QD-score, and niche-matched-only retrieval."""

    def __init__(self, niche_cap: int = DEFAULT_NICHE_CAP) -> None:
        self.niche_cap = niche_cap
        self._elite: dict[str, GeneEntry] = {}
        self._recessive: dict[str, list[GeneEntry]] = collections.defaultdict(list)
        self._lineage: list[GeneEntry] = []
        self._reuse_counts: dict[str, int] = {}

    def add(self, entry: GeneEntry, require_causal_verified: bool = True) -> bool:
        """Admit `entry` into its niche. Returns True iff it became the niche's new elite
        (False means it was retained in the recessive pool, or evicted immediately by the
        resource cap if the niche was already full of stronger entries).

        Raises GenePoolError if require_causal_verified and entry.causally_responsible is
        False -- a non-causally-verified candidate must never enter the shared pool at all.
        This is a defense-in-depth check; evolve_s11.py's mining loop is the primary
        enforcement point (it only calls add() on candidates causal_gate already passed)."""
        if require_causal_verified and not entry.causally_responsible:
            raise GenePoolError(
                f"refusing to add non-causally-verified entry {entry.item_id!r} to niche "
                f"{entry.niche!r} -- causal_gate.check_causal_responsibility must pass first"
            )
        self._lineage.append(entry)
        became_elite = False
        current_elite = self._elite.get(entry.niche)
        if current_elite is None or entry.score > current_elite.score:
            if current_elite is not None:
                self._recessive[entry.niche].append(current_elite)
            self._elite[entry.niche] = entry
            became_elite = True
        else:
            self._recessive[entry.niche].append(entry)
        self._enforce_niche_cap(entry.niche)
        return became_elite

    def _enforce_niche_cap(self, niche: str) -> None:
        """Minimal-criterion-style resource cap: once elite+recessive together exceed
        niche_cap for this niche, evict the WEAKEST recessive entries first (never the
        elite) until back at cap. Stops one easy niche from unboundedly accumulating
        retained entries at the expense of the pool's overall diversity budget."""
        recessives = self._recessive.get(niche, [])
        has_elite = niche in self._elite
        total = len(recessives) + (1 if has_elite else 0)
        if total <= self.niche_cap:
            return
        recessives = sorted(recessives, key=lambda e: e.score, reverse=True)
        keep = max(0, self.niche_cap - (1 if has_elite else 0))
        self._recessive[niche] = recessives[:keep]

    def best_for(self, bug_kind: str, capability: str) -> GeneEntry | None:
        """Niche-matched retrieval ONLY -- returns None on a niche miss, never a
        different-bug_kind or different-capability item. Direct fix for S+1's diagnosed
        blind-fallback-to-any-item defect (search.Library.best_for)."""
        return self._elite.get(niche_key(bug_kind, capability))

    def recessive_for(self, bug_kind: str, capability: str) -> list[GeneEntry]:
        """The retained-but-not-champion pool for one niche, for later recombination /
        recessive-trait recovery. Empty list (never a fallback item) on a niche miss."""
        return list(self._recessive.get(niche_key(bug_kind, capability), []))

    def record_reuse(self, item_id: str) -> None:
        """Credit a reuse-and-promoted event against an EXISTING elite or recessive entry,
        without minting a duplicate pool entry (mirrors search.Library.record_reuse_promotion's
        discipline)."""
        self._reuse_counts[item_id] = self._reuse_counts.get(item_id, 0) + 1

    def reuse_count(self, item_id: str) -> int:
        return self._reuse_counts.get(item_id, 0)

    def niches(self) -> dict[str, GeneEntry]:
        return dict(self._elite)

    def lineage(self) -> list[GeneEntry]:
        return list(self._lineage)

    def qd_score(self) -> float:
        """Sum of elite scores across all filled niches -- coverage x quality, the QD-score
        this design reports instead of a bare pass@1 rate."""
        return sum(e.score for e in self._elite.values())

    def signature(self) -> tuple:
        """Stable snapshot of which niches are filled and by which candidate -- used by
        run_search_s11 to decide when to checkpoint the B/sentinel curve (mirrors
        search.Library.signature())."""
        return tuple(sorted((niche, e.item_id) for niche, e in self._elite.items()))

    def stats(self) -> dict:
        by_bug_kind = collections.Counter(e.bug_kind for e in self._elite.values())
        by_capability = collections.Counter(e.capability for e in self._elite.values())
        total_recessive = sum(len(v) for v in self._recessive.values())
        return {
            "num_niches": len(self._elite),
            "num_specialists": len(self._elite),  # one elite per niche == one specialist per niche
            "distinct_bug_kinds_covered": len(by_bug_kind),
            "niches_per_bug_kind": dict(sorted(by_bug_kind.items())),
            "niches_per_capability": dict(sorted(by_capability.items())),
            "qd_score": self.qd_score(),
            "total_lineage": len(self._lineage),
            "total_recessive_retained": total_recessive,
            "niche_cap": self.niche_cap,
        }
