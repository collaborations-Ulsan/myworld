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

## Phase 2 — Mount self-verification (escalate + Weaver → the loop)  [STATUS: DONE ✓ verified `acb6302`]
- Loop failure / low-confidence → `EscalationOrgan` with default `verifier="weaver"` (demo fallback if torch absent).
- Mount `aios_escalate` into head/turn_loop failure path (today zero callers).
- **Accept**: a task the base student fails triggers escalation+verify; verifier catch-rate measurable; no regression.

## Phase 3 — Sovereign Experience Graph (the continuous self)  [STATUS: DONE ✓ verified `1785d85`]
- Every run / decision / verifier result / skill / failure / provider-route → one queryable, versioned,
  tamper-evident store (build on run_log + Merkle Pack + tlog-tiles). The organism's memory + "aliveness" substrate.
- **Accept**: the loop writes to it each turn; it's queryable ("what did I learn / fail at"); tamper-evident (peer-verifiable Merkle root).

## Phase 4 — Skills as the compounding unit (Code Artifact Induction)  [STATUS: DONE ✓ verified `81868f7`]
- On solving a hard task: write a verified Python tool (applicability predicate + example + counterexample
  + unit test + provenance) → sandbox-test it → register Merkle-rooted → future tasks retrieve/compose it.
- The heritable gene, not the scar. Compounding happens HERE, in the OS, not in weights.
- **Accept**: a solved task produces a registered tested skill; a later task reuses it; skill-reuse EV measurable.

## Phase 6 — (was: give the organism a daemon body)  [STATUS: CANCELLED — council-REFUTED `92401c3`]
Proposed after the founder's form-factor question, then killed mid-build by a heterogeneous adversarial
council (REFUTED · REFUTED · SURVIVES-WITH-CONDITIONS). "Persistence is not presence" — the organism's
body is the append-only Merkle record on disk, not a resident process; a daemon adds attack surface, a
second source of truth, and ops burden while buying no exclusive capability. **Gate for any future
revival: name and demonstrate ONE capability impossible with fast-start CLI + file-backed MCP; then build
it socket-activated, stateless, disk-authoritative, 0600+SO_PEERCRED, no state-mutating tick.** Full
reasoning: `docs/AIOS_FORM_FACTOR_DECISION_2026-07-22.md` §0.

## Phase 5 — Settle learning on a measurable testbed  [STATUS: TODO — now the front line]
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
- 2026-07-22 — **Phase 2 DONE + verified by me** (`acb6302`). Self-verification mounted at the head:
  turn-loop FAILURE exit → optional `_escalate_failed_goal` (the zero-caller EscalationOrgan, AB-MCTS over
  provider adapters, scored by Weaver with torch-probe→demo fallback). OPT-IN default-OFF
  (--escalate/AIOS_ESCALATE) so default behavior + test surface unchanged; instruments
  escalation_attempted/recovered/best_score/provenance into the outcome+run-log (content-safe). Never
  raises → original failed outcome intact. Verified: 123 passed (phase2 + head/turn_loop/escalate/verifier/
  adapters), zero regression; wiring read (torch probe, never-raises, default-off). Second ORPHAN→WIRED
  (escalate + Weaver). **Honest**: Weaver is domain-bound → `recovered` is not a capability win, it's
  mechanism+measurement; per-domain value is a Phase-3/5 question. Next: Phase 3.
- 2026-07-22 — **Phase 3 DONE + verified by me** (`1785d85`). Sovereign Experience Graph
  (`scripts/aios_experience.py`, stdlib-only, composes run_log — no new DB) + head appends a content-safe
  `kind:"outcome"` line per goal. Queries: failures / escalations / by-goal / provider-recovery / summary;
  Merkle root (reused from pack_export) + pin/verify tamper-evidence. QA: 16 tests foreground + 34 combined
  with head, zero regression. My live verify on REAL data: 187 runs / 1215 entries / 0 malformed;
  q_by_goal("날씨")=4 real matches (organism queries its own experience); pin→verify=ok; root deterministic.
  Third organ wired — the continuous, queryable, tamper-evident self. **Honest**: 187 pre-Phase-3 runs are
  `unknown_exit` (exits weren't logged before — reported, never guessed); 0 live escalation records yet
  (Phase 2 opt-in unfired). Next: Phase 4 (the compounding organ).
- 2026-07-22 — **Phase 4 DONE + verified by me** (`81868f7`). Code Artifact Induction organ
  (`scripts/aios_skills.py`, stdlib-only, composes sandbox + Merkle): skill schema (content-addressed id,
  code, applicability, example, unit_test, provenance) · `register` runs code+unit_test INSIDE
  `run_untrusted_code` and registers ONLY on pass (verdicts registered / rejected_unit_test_failed /
  refused_sandbox_unavailable / refused_invalid / refused_duplicate) · `retrieve` (BM25) · `induce_skill`
  (AST extraction, v1 structured-not-LLM) · Merkle registry pin/verify · CLI · opt-in `induce_and_register`
  hook (NOT forced into every solve). QA: 12 tests foreground. **My adversarial pass (the load-bearing
  anti-reward-hack gate): honest skill→registered; reward-hack (code returns 0)→rejected; unit_test that
  tries NETWORK exfil→rejected (the test runs CAGED in the sandbox — a malicious skill can't exfiltrate
  during its own verification); unit_test that reads a private dir→rejected; no-engine→refused (fail-closed);
  final registry = exactly the one honest skill, verify=ok.** Fourth organ wired — the GROWTH mechanism:
  the organism accumulates only externally-verified, sandbox-caged, reusable skills. Compounding happens in
  the OS, not in weights. **Honest**: gate strength = unit-test strength (a weak test admits a weak skill;
  the external property is register never edits code/test); induce v1 is AST-structured not LLM; hook is
  opt-in, not yet fired by the live loop; retrieval is lexical BM25. Next: Phase 5 (settle learning on a
  measurable testbed — the honest 5-null resolution).
