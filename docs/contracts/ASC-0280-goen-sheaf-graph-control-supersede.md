# ASC-0280 — GoEN sheaf graph-control supersedes ASC-0194 (evidence-gated)

- contract_id: ASC-0280
- status: proposed
- goal: adopt the GoEN sheaf graph-control engine as MemoryOS's graph-control backbone,
  superseding the ASC-0194 dream-cycle — ONLY behind the evidence gate below, reversible,
  with ASC-0194 kept as fallback.
- supersedes: (on close) ASC-0194 graph-control role; ASC-0194 record itself stays append-only.
- created: 2026-07-02
- proposer: claude@GoEN (founder-directed: "Supersede — GoEN IS the backbone", 2026-07-01)
- accepted: 2026-07-02 (founder directive "1번부터 순서대로 진행" — build-order #3 GO; codex@memoryOS
  pickup of WP-1 pending)
- closed: —

## Why (one paragraph)

MemoryOS today has NO materialized edge layer (no edges/hyperedges ledgers; supersedes=1,
contradicts=0 across 373 objects) — the graph the OS is named for is essentially unbuilt. GoEN's
engine derives it from REAL signals (28,613 retrieval-trace co-access chains + λ-gated embedding
kNN), maintains it with validated mechanisms (Householder transport, ker(L_F) recall, section-defect
conflict, trust-region churn caps), and emits every change as a draft GraphEditProposal
(recommendation-only). The Phase-3 shadow bake-off on the real store (2026-07-02) passed its
pre-registered gates; full parity remains blocked by an incumbent-side ledger defect (below).

## Evidence (bake-off, pre-registered; committed artifact: GoEN repo
`ai_shared/BAKEOFF_GOEN_VS_ASC0194_2026-07-02.json` @ commit afe2095; working copy
`goen_bench/results/bakeoff_goen_vs_asc0194/report.json`)

| contrast | result | verdict |
|---|---|---|
| P0 completion | ASC-0194 FAILS on the real store (corrupt trailing line in its own `graph_control_runs.jsonl`, 1/827 truncated append; loader dies). Completes only on a repaired sandbox, and there exits via its own `budget_exhausted` stop (score partial, all downstream stages skipped; 826 prior runs; 7.45 s). GoEN completes on the real store (cohort λ=0.82, 2,627 derived edges, 0.27 s). | parity comparison OUTSTANDING — not a GoEN win by forfeit; repair is a cutover prerequisite |
| P1 recall (net-new) | ker(L_F) recall on the real derived graph: recall_auc 0.9974 ± 0.001 (t-CI, n=20 fixed mask seeds) vs same-rank random projection (a weak baseline, and the stored data is harmonic by construction — partially tautological); the informative contrast is masked-node reconstruction cos 0.945 vs neighbor-mean 0.813 | GATE PASS (per prereg), read via the masked-node contrast |
| P2 multi-way conflict (net-new) | section-defect AUC 0.803 ± 0.094 (n=16 fixed injection seeds, 15 effective) on wrong-link injection; pairwise steelman 0.760 ± 0.094 | GATE PASS; superiority vs pairwise = TIE (CIs overlap) — reported as tie |
| P3 consolidation (net-new) | goen 0.9966 vs frequency 0.9881 held-out precision — CEILING EFFECT (both >0.98), statistically separated but practically thin | descriptive only; do not headline |

Engine math: 15/15 checks (`verify_backbone.py`) incl. exact reduction to the validated scalar
Laplacian and the section-defect lemma (odd reflection cycles: det(H_c)=−1 ⇒ matrix test invalid;
section test exact-0 on consistent cycles — theory-paper §4.1).

## External landscape note (2026-07-02)

This contract's claims are INTERNAL-comparative (GoEN engine vs ASC-0194 on our store). For any
external/public positioning, the binding calibration is the GoEN repo's
`ai_shared/NOVELTY_RECALIBRATION_2026-07-02.md` (July-2026 web-grounded): sheaf-conflict and
Hebbian-activity memory graphs are already published externally (SuperLocalMemory V3, HeLa-Mem);
the genuinely open residuals are bridge-protected topology-aware eviction, implemented
sheaf-kernel recall, and a benchmarked cycle-level conflict win (BEAM is the right proving ground).

## Scope

- repos: memoryOS (integration target), GoEN (`goen_bench/goen_memoryos/` engine, read-only vs memoryOS)
- allowed_files: `memoryOS/memory/graph_proposals.jsonl`, `memoryOS/memory/annotations.jsonl`
  (append-only, draft-only, via public store API); memoryOS code changes ONLY by codex@memoryOS
  under this contract.
- forbidden: destructive edits to any ledger; auto-approval of proposals; touching `_from_desktop`,
  `dain/`, `minyoung/`; writing to `objects.jsonl`/`reviews.jsonl` except via the normal review flow.

## Plan (phases, each reversible)

1. **P4a — incumbent ledger repair** (codex@memoryOS): quarantine the truncated trailing line of
   `graph_control_runs.jsonl` (append-only fix: move bad line to a `.quarantine` sidecar); make
   `_read_jsonl` fold-tolerant (skip+count corrupt lines — GoEN's ledger reader already does this).
2. **P4b — full parity rerun**: bake-off P0 with a WORKING incumbent (its stage queues vs GoEN's);
   pre-registered: GoEN must not regress incumbent health/coverage queues.
3. **P4c — shadow live**: GoEN runs on a schedule in shadow, emitting draft proposals + goen_signal
   annotations into the real store (recommendation-only; operator reviews via the normal
   drafts-priority inbox).
4. **P4d — cutover behind a flag**: `graph-control --engine goen|asc0194` (default asc0194 until
   operator flips); ASC-0194 remains callable; every GoEN apply goes through the existing
   approved-proposal lane.

## Verification gate (done vs not-done)

- P4b parity report committed with: incumbent completes; GoEN completes; no incumbent-queue
  regression; P1/P2 gates re-pass on the then-current store.
- One full shadow week (P4c) with zero DNA violations (no non-draft writes, no auto-approvals).
- Operator (founder) flips the flag = close; any gate failure → GoEN stays augment/shadow, contract
  closes as "not superseded" (that is a valid, honest close).

## Stop conditions

- Any GoEN write outside `graph_proposals.jsonl`/`annotations.jsonl` → halt + operator checkpoint.
- Proposal churn > trust-region cap or components-increase guard fires → engine self-truncates
  (named stop) and the run is reported.
- Founder HOLD/NO-GO at any phase.

## AIOS Role Evidence

- MemoryOS / Retriever: real-store snapshot meta (371 objects, 342 cached embeddings, 28,613
  co-access chains) — bake-off report `meta` block.
- Hive / Wrapper: pending_or_not_required (bake-off ran locally in the GoEN repo env).
- CapabilityOS / Router: pending_or_not_required (no route decision needed for a proposed contract).
- GenesisOS / Philosophy: prompt-prison check applied — the engine mirrors ASC-0194's pipeline
  shape for comparability BUT adds the net-new axes (recall, multi-way conflict) the incumbent's
  frame lacks; the section-defect lemma came from questioning the standard holonomy-norm frame.

### 5-Persona Use
- Hive / Wrapper: single-provider local run justified (deterministic harness, no LLM calls)
- MemoryOS / Retriever: streamed selective reads (`load_embeddings_for_targets`, trace streaming)
- CapabilityOS / Router: n/a at proposal stage
- GenesisOS / Philosophy: incumbent-frame lock-in named as the risk; mitigated by net-new metrics

## Work Packets

- WP-1 (codex@memoryOS): P4a repair + fold-tolerant loader. — **UNBLOCKED 2026-07-02 (contract
  accepted); awaiting codex@memoryOS pickup.** Repair spec: quarantine the truncated trailing
  line of `memory/graph_control_runs.jsonl` (append-only: move to a `.quarantine` sidecar, never
  edit in place) + make `store._read_jsonl` skip-and-count corrupt lines.
- WP-2 (claude@GoEN): P4b parity rerun + report. — pending WP-1
- WP-3 (operator): review shadow-week drafts; flag decision. — pending WP-2

## Evidence addendum (2026-07-02, build-order #1–#2)

- Conflict organ upgraded: DescentNet typed-cover machinery ported into GoEN graph-control
  (ordinal Condorcet-cycle detector + Hodge obstruction + typed tolerances; 21/21 checks;
  GoEN repo commit `1a906df`).
- Honest negative on the retention niche: the real-store bridge-eviction witness FAILED its
  pre-registered gate (saturated budget — design error; at real pressure the clause separates
  from its ablation and LFU but uniform-random retention beats all policies at hop-bounded
  recall). Bridge protection survives as the controller's prune-CONSTRAINT, not a retention
  priority. GoEN repo commit `6893ae8`. This does not affect the P4 gates (which are parity +
  recall + conflict), but it is part of the honest record.
