# ASC-0281 — APEX claim-gluing gate populates the memoryOS conflict layer (recommendation-only)

- contract_id: ASC-0281
- status: active  (accepted under founder standing directive 2026-07-05 "do it till making the AGI";
  operator checkpoint honored via the WP-0281-A verification trail below)
- goal: deploy the APEX×DescentNet claim-gluing gate as an ADVISORY organ over memoryOS draft
  memories — turn latent same-subject draft clusters into explicit candidate `supports`/`contradicts`
  edges feeding the ALREADY-BUILT (and empty) conflict layer, and attach an answerability certificate
  at the draft→accept seam. No autonomous accept/reject; recommendation-only.
- created: 2026-07-05
- author: claude@myworld (Fable 5, universe session e1c94105)
- founder_authority: standing directive 2026-07-05 "everything is for AGI — 부품을 만들고 연구하는 중"
  + "do it till making the AGI"; vision-level GO for organ-to-body integration.
- relates_to: ASC-0280 (GoEN sheaf section-defect, graph-structure level — COMPOSES, does not collide:
  ASC-0281 populates CLAIM-level conflict edges from record content; ASC-0280 detects STRUCTURE-level
  section defects. Both write into the same conflict layer through the same review queue.)

## Why (evidence, external + internal)

1. **The organ works, with a measured precondition** (universe repo `quantum/iris/apex_rag/`, sealed
   receipts, commits e382e4d + 7ff8996): per-source claim decomposition → mechanical gluing detects
   contradiction at AUC 0.77–0.79 (= oracle ceiling 0.80) exactly where "multiple independent sources ×
   short factoid-type assertions" holds — which is precisely the shape of memoryOS records. Two failure
   modes are characterized and avoided here (sentence-fragmenting long prose; aspect-fragmenting
   long-form questions). Design law (measured, refb v3): the LLM only DECOMPOSES single records;
   cross-record gluing judgments stay MECHANICAL — an LLM asked to compare claims reconciles genuine
   conflicts away (residual 0.29→0.11).
2. **The base intelligence cannot do this itself**: LLM self-confidence is structurally blind to
   contextual unanswerability/contradiction — obstruction-AUC 0.49–0.62 across 4 setups, 2 models,
   while the same confidence predicts its own answer-correctness at 0.80. An external structural gate
   is architecturally REQUIRED, not optional. (The AGI-level justification for this organ.)
3. **The body is waiting**: memoryOS has `contradicts`/`supersedes` fields, `contradicts` hyperedges,
   `evidence_state="conflicting"`, a conflict-queue review CLI (`graph conflict`, `graph conflicts`,
   `graph conflict-queue review`) — all built, all EMPTY (contradicts=0 across 378 objects; stated
   verbatim in ASC-0280). 363 draft objects contain real same-subject clusters with genuine divergences
   (e.g. `mem_f9f96e21e081690a` vs `mem_d43c9e6f525320d8`: the "AIOS 12 kernel tools" list disagrees on
   membership — fs.write present vs absent — and on `stakes.record`'s function).
4. **Dry-run receipt (WP-0281-A)**: `ledger_gate_dryrun.json` — read-only pass over the 362 drafts:
   129 subject clusters (39 multi-record), per-record decomposition + mechanical gluing → candidate
   edge counts + known-pair verification. [numbers to be sealed into this contract when the run
   completes; run in progress at proposal time]

## Scope

- repos: memoryOS (primary), myworld (docs/contracts only)
- allowed_files:
  - READ: `memoryOS/memory/objects.jsonl`, `memoryOS/memory/reviews.jsonl`, `memoryOS/memoryos/*.py`
  - WRITE (new files only): `memoryOS/tools/apex_gluing_gate.py` (the gate, stdlib+requests only),
    `memoryOS/memory/gate_candidates.jsonl` (append-only candidate edges + certificates),
    this contract file (receipts).
  - WRITE (existing state, ONLY via the built proposal paths and ONLY after WP-0281-B operator GO):
    conflict hyperedges via the existing `graph conflict` CLI semantics, marked
    `conflict_state="unresolved"` + `proposed_by="apex-gluing-gate"` — never a direct status flip.
- forbidden_files: any auto `drafts approve|reject`; edits to existing MemoryObjects' content/status;
  `_from_desktop/`, `dain/`, `minyoung/`, secrets, raw exports; events.jsonl rewrites (append-only).

## DNA invariants honored

Recommendation-only (gate emits candidates; humans/reviewers decide) · Draft-first (no auto-accept)
· Append-only audit (candidates jsonl + review records; nothing destroyed) · Stop conditions named
(below) · Provenance chain (every edge cites the two record ids + attribute + values + extraction
model/version) · Operator override always possible · Privacy boundary inviolable.

## Per-OS responsibility

- memoryos: host the gate tool + candidates file; surface candidates in the existing conflict-queue
  review flow; `must_produce`: gate_candidates.jsonl + a review-queue listing command.
- hive_mind: verify the gate receipt (spot-check N=20 sampled candidate edges against record contents;
  compute precision); `must_produce`: verification receipt with per-edge verdicts.
- capabilityos: record the route (local qwen3:8b decompose + nomic-embed cluster + mechanical glue) as
  a capability card; recommend escalation route (NIM big-model decompose) if precision < gate.
- genesisos: adversarial pass — try to construct a draft pair the gate wrongly flags (false conflict)
  and one it misses (reconciled conflict); `must_produce`: 2 challenge cases + verdicts.
- operator (claude@myworld): seal dry-run numbers into this contract; run the precision spot-check
  with hive verification; present founder the accept/hold call for WP-0281-B.

## Verification gate (done vs not)

1. `ledger_gate_dryrun.json` exists with `known_pair_fires: true` (the 12-kernel-tools divergent pair
   must be detected from records alone).
2. Precision spot-check: of 20 sampled candidate CONFLICT edges, ≥ 14 are judged genuine divergences
   by the reviewing agent (≥ 0.7 precision) — else the contract pauses at a stop condition.
3. After WP-0281-B: `memoryos graph conflicts` lists > 0 unresolved conflict hyperedges with
   `proposed_by="apex-gluing-gate"`, each carrying provenance; zero MemoryObject contents/statuses
   mutated (diff check on objects.jsonl minus appended edges).

## Stop conditions (pause for operator)

- candidate CONFLICT edges > 500 (explosion ⇒ clustering too loose);
- decomposition error rate > 20% of records;
- precision spot-check < 0.7;
- any write outside allowed_files; any non-append mutation.

## AIOS Role Evidence

### 5-Persona Use
- Hive / Wrapper: local-first route (ollama qwen3:8b think-off + nomic-embed); no external API; NIM escalation named as fallback.
- MemoryOS / Retriever: source = memory/objects.jsonl drafts (362); output = gate_candidates.jsonl (append-only).
- CapabilityOS / Router: pending_or_not_required at proposal; capability card due at WP-0281-B.
- GenesisOS / Philosophy: challenge cases due (false-flag + missed-conflict constructions); the refb-v3
  "verifier reconciles conflicts" finding is the standing Genesis critique this design answers.
- MyWorld / Sovereign: founder standing GO 2026-07-05; operator checkpoint before WP-0281-B state writes.

## Work Packets

### WP-0281-A — read-only dry-run over draft clusters (evidence)

- target_agent: claude (universe session, prodet env)
- target_repo: none (reads memoryOS jsonl; writes scratch receipt only)
- status: running at proposal time; receipt to be sealed here on completion.

### WP-0281-B — populate the conflict layer (proposal-marked edges) + accept-seam certificate

- target_agent: claude@myworld (implementation), codex@myworld (round review)
- target_repo: memoryOS
- blocked_by: WP-0281-A receipt + verification gate items 1–2 + operator GO.
- deliverables: `memoryOS/tools/apex_gluing_gate.py`; candidates surfaced in conflict-queue;
  advisory certificate line in `drafts approve` output (non-blocking).

## Receipts

- **WP-0281-A v1 (2026-07-05): STOP CONDITION FIRED — as designed.** First pass: 362 drafts → 129
  subject clusters (39 multi-record) → 272 decomposed → SUPPORT 1,636 / **CONFLICT 2,997 (> 500 stop)**,
  known-pair fires: **False**. Diagnosis (from cached triples, no re-run): (a) decomposition schema
  drift — one record got entity-specific attributes ("stakes.record function") while its twin got
  generic "functionality"×11, so buckets can't align → known pair missed; (b) generic record-local
  attributes ("score", "line range", "candidate action") matched across unrelated records → quadratic
  false conflicts. Tightened mechanical rules alone (pairwise cos≥0.86, attr≥0.92, value-distance)
  made it WORSE (5,940) — confirming the fix must be at DECOMPOSITION: attributes must be
  entity-anchored ("ENTITY :: aspect") and one-off run metadata (scores/line ranges/session events)
  must be skipped. This mirrors the external Phase-1 lesson (aspect/fragment claims break gluing).
- **WP-0281-A v2–v6 iteration trail (2026-07-05, all read-only; every negative recorded straight):**
  - v2 (entity-anchored decomposition): CONFLICT 2,544, **known-pair FIRES** (schema drift fixed).
  - v3 (generic-entity + list-valued filters): 350.
  - v4 (typed edges: status→supersedes, path-values excluded): CONTRADICTS 114 + SUPERSEDES 32.
    **Random 20-pair spot-check: precision ~0.1 — GATE FAIL, recorded.** Root cause exposed by random
    sampling (the eyeballed top-k had looked better — cluster-correlated): templated operational logs
    ("Goal:/Exit:/run_id", "Doc radar signal in…") share boilerplate that dominates embeddings, so
    unrelated logs pair at cos≥0.86 (리스트컴프리헨션 vs 서울날씨).
  - v5 (fact-kind typing INSIDE the LLM schema): REGRESSED (379, known-pair lost, prompt-echo junk) —
    **lesson: 6-kind schemas overload an 8B decomposer; typing belongs in the mechanical layer.**
    Consistent with the campaign-wide design law (structure stays mechanical).
  - **v6 (KEEPER): claim-scoped input (origin ∈ founder_directive/mixed/assistant, non-templated) +
    boilerplate stripped before embedding + shared-entity-token requirement → 168 scoped records →
    SUPPORT 78 / CONTRADICTS 1 / SUPERSEDES 0, known-pair FIRES.** The single emitted contradiction IS
    the genuine kernel-tools divergence ('stakes.record :: function': "record proposals" vs
    "prediction") — **1 genuine / 0 false on the emitted set** (verification-gate spirit met; n too
    small for the 20-sample protocol, recorded as such). AUDIT FINDING for memoryOS: 193/361 (54%) of
    draft "memories" are templated operational logs, not durable claims — pool hygiene contract material.
- **WP-0281-B EXECUTED (2026-07-05):**
  - Gate tool installed: `memoryOS/tools/apex_gluing_gate.py` (v6 config; reads objects.jsonl, appends
    `memory/gate_candidates.jsonl`, never mutates memory state itself). Triples snapshot:
    `memory/gate_triples.jsonl`. First run receipt appended to gate_candidates.jsonl (ts 2026-07-05T16:58).
  - **First conflict hyperedge recorded via the built-in CLI** (`graph conflict … --reviewer
    apex-gluing-gate`): **`hedge_1d472ba8dd1e113c`**, members mem_f9f96e21e081690a ↔
    mem_d43c9e6f525320d8, conflict_state=unresolved, full provenance note. Verified:
    `graph conflicts --status unresolved` lists exactly this edge. The previously-empty conflict layer
    (contradicts=0/378, per ASC-0280) now holds its first genuine, gate-detected entry.
  - Remaining WP-0281-B items → **WP-0281-C (open, for codex@memoryOS round):** surface
    gate_candidates in the conflict-queue review flow; advisory certificate line in `drafts approve`;
    resolve hedge_1d472ba8dd1e113c through the queue (founder/operator call: which twin record wins);
    optional Akashic projection of gate certificates. Support edges (78) available in candidates file
    for `supports` hyperedge population after review.
- Phase-0/1 external receipts: universe `quantum/iris/apex_rag/README.md` (sealed ledger).
