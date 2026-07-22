# AIOS Organism Assembly — durable phased plan + progress log (2026-07-22)

**Keystone**: compose the organism — connect the verified organs into the living turn-loop; compound in the
OS (tested skills + experience graph), models ephemeral. Not more features — connection. Full rationale:
`docs/AIOS_STATE_AND_ORGANISM_SYNTHESIS_2026-07-22.md`. Founder GO 2026-07-22 ("긴 작업 될테니 대비하고").

**Invariants (every phase)**: fail-closed · do NOT break the existing 297-test surface (add integration
tests) · no-launder honest per-phase verdict · commit per increment · aliveness measured by BEHAVIOR
(errors caught / decisions changed / skills grown / exfil blocked), never by how alive it sounds.

**Resume protocol (after context compaction)**: read this file's Progress Log + `git log --oneline -20`.
Each phase is independently committed; the log below is the source of truth for "where am I."

---

## Phase 1 — Mount the enforced body (sovereignty pair → the loop)  [STATUS: DONE ✓ verified `e19659d4`]
The top unwired seam. Make the privacy boundary ENFORCED in the running kernel, not a docstring.
- 1a. `run_sandboxed` wraps code/tool execution in `aios_tools` (subprocess / skill.use / domain.run exec paths). ENFORCE (fail-closed: no engine → don't run).
- 1b. `egress_check` (ENFORCE) on `aios_tools` web.fetch/scrape/search (clearly off-box network).
- 1c. `egress_check` (RECEIPT/advisory mode first) on `aios_adapters` provider sends — audit trail without breaking the loop; tighten to enforce after validation.
- **Accept**: existing 297 tests still pass · new integration tests prove (i) a tool that tries to exfiltrate/read a private dir is blocked, (ii) a normal tool run still works, (iii) provider sends emit egress receipts. Verified by my own adversarial pass.

## Phase 2 — Mount self-verification (escalate + Weaver → the loop)  [STATUS: TODO]
- Loop failure / low-confidence → `EscalationOrgan` with default `verifier="weaver"` (demo fallback if torch absent).
- Mount `aios_escalate` into head/turn_loop failure path (today zero callers).
- **Accept**: a task the base student fails triggers escalation+verify; verifier catch-rate measurable; no regression.

## Phase 3 — Sovereign Experience Graph (the continuous self)  [STATUS: TODO]
- Every run / decision / verifier result / skill / failure / provider-route → one queryable, versioned,
  tamper-evident store (build on run_log + Merkle Pack + tlog-tiles). The organism's memory + "aliveness" substrate.
- **Accept**: the loop writes to it each turn; it's queryable ("what did I learn / fail at"); tamper-evident (peer-verifiable Merkle root).

## Phase 4 — Skills as the compounding unit (Code Artifact Induction)  [STATUS: TODO]
- On solving a hard task: write a verified Python tool (applicability predicate + example + counterexample
  + unit test + provenance) → sandbox-test it → register Merkle-rooted → future tasks retrieve/compose it.
- The heritable gene, not the scar. Compounding happens HERE, in the OS, not in weights.
- **Accept**: a solved task produces a registered tested skill; a later task reuses it; skill-reuse EV measurable.

## Phase 5 — Settle learning on a measurable testbed  [STATUS: TODO]
- Codex's discriminating experiment: 2 model (1.7B, 7-8B) × 3 transfer-distance (E0 same / E1 near / E2 cross)
  × 4 learning-unit (none / retrieval / skill-library / +scaffold-evolution), Pass@K, deterministic verifier,
  bootstrap CI. Stop rules localize substrate vs transfer vs scaffold-organ vs retire-testbed.
- Distillation only downstream of evidence, into 4-8B+, from verified trajectories.
- **Accept**: the null is LOCALIZED (not just "null"); a decision on whether/where learning compounds.

---

## Progress Log (append-only; newest last)
- 2026-07-22 — Plan created. Capstone synthesis committed (`c116f9b`). Prior session bricks (all ORPHAN,
  to be mounted here): Weaver `c1d71e6`, egress gate `bf83336`, sandbox `12227b2` (adversarially verified),
  Pack `455b550`. Starting Phase 1.
- 2026-07-22 — **Phase 1 DONE + independently verified** (`e19659d4`). Sovereignty pair mounted into the
  running kernel: 1a untrusted tool-code exec (`aios_tool_executor.execute_tool`) now routes through
  `run_sandboxed(allow_net=False)` fail-closed (kernel fs primitives untouched); 1b web.fetch/scrape/search
  egress-enforced (secret/private-path URLs blocked, clean pass); 1c provider sends emit egress receipts
  (advisory, non-blocking). QA: existing 177 pass + 16 new phase1 tests + 2148 collected zero-breakage. My
  adversarial pass confirmed on the REAL handlers: secret/dain/AWS URLs blocked, run_sandboxed invoked with
  allow_net=False on real exec, fs.list unregressed, receipt appended without blocking. First ORPHAN→WIRED
  conversion — the loop enforces its own boundary. **Honest gaps carried to later**: 1c is receipt-only (a
  secret in a provider prompt is recorded but still sent — enforce/scrub deferred); sibling-OS CLIs +
  contract-runner subprocesses remain unsandboxed (out of Phase-1 scope). Next: Phase 2.
