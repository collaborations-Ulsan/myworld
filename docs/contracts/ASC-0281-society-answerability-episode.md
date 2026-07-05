# ASC-0281 — Society-level answerability episode (DescentNet × APEX × Akashic, sealed decision-cost benchmark)

- contract_id: ASC-0281
- status: proposed
- goal: ONE sealed, receipted episode in which a society of N agents holding partially
  contradictory memories answers a question stream under a measurement budget, governed by the
  composed epistemic layer — DescentNet non-gluing detection → APEX-typed claim gating →
  expected-value intervention → Akashic receipts — and beats untyped agent societies on decision
  cost. This is the first COMPOSED demonstration of the "everything is for AGI" program: the parts
  (APEX paper, IRIS/E2-C, backbone task demo, DescentNet contradiction harnesses) are separately
  receipted; the AGI-grade claim requires the composition.
- supersedes: none (net-new; contract-title grep for answerability/epistemic/DescentNet/APEX
  returned zero — no incumbent)
- created: 2026-07-05
- proposer: claude@myworld (standing founder directive 2026-07-05: "everything is for AGI" +
  "Do it till making the AGI" — recorded as provisional GO; formal accept pending operator/founder)
- accepted: —
- closed: —

## Why (one paragraph)

Every component guards one scale of the same failure — confident claims the evidence does not
determine (APEX: one question; IRIS: the law loop; DescentNet: agent memories; AIOS/Akashic: the
society and its ledger) — and the shared theorem shape (local consistency ≠ global truth,
detectable from records, monetizable as decision cost) is receipted at three scales already
(paper_apex_certify; apex_e2c_amortized_lawgen; apex_backbone_task_demo, 3.3×/2.2× cost advantage,
3 seeds). What has never been shown is the composition: that these organs, wired together over an
actual multi-agent memory substrate with an actual append-only ledger, produce a SOCIETY that
claims honestly, localizes its contradictions, buys only resolving measurements, and wins on
decision cost. That composed receipt is the difference between "a collection of parts" and "a
working epistemic layer for AGI."

## Evidence (what already exists — all verified 2026-07-05, librarian sweep)

- DescentNet detector: `descentnet/descentnet/backbone.py` — `TypedCover.build` +
  `DescentNetBackbone.complete()` → {GLUABLE, AMBIGUOUS, OBSTRUCTED} + harmonic obstruction
  witness + per-cell localization (`cell_scores`, `localized_cells`) + ambiguity fiber.
- The two-face bridge ALREADY EXISTS: `descentnet/descentnet/apex_active_answerability_witness.py`
  maps {gluable, ambiguous, obstructed} → {Ans, Und, Obs} (APEX verdict faces).
- Higher-order contradiction harness: `descentnet/descentnet/memoryos_ledger_higher_order_contradiction.py`
  — GHZ/parity ledgers, pairwise-blind (AUC ≤ 0.58) vs descent-localized (AUC ≥ 0.85), synthetic
  + hashed + draft-only (privacy-clean).
- APEX claim router + deployment economics: `quantum/quantum/iris/claim_router.py`,
  `apex_iris_backbone.py` (translation semantics), `apex_backbone_task_demo.py` (slice-calibrated
  selective thresholds; EV intervention rule q > Q_MIN; sealed TASK_PASS, 3 seeds).
- Akashic Record: `myworld/memoryOS/memoryos/akashic_ledger.py` — `build_index` (privacy-gated),
  `append_index`, `reconstruct(work_id)`; schema `aios.akashic_work_index.v1`.
- Multi-agent envelope (if N live workers are used in phase C): `myworld/scripts/aios_packet.py` +
  `hivemind/hivemind/aios_packet_runner.py`.

## External landscape note

2026-07-05 pre-submission sweep (paper_apex_certify commit 037dcc2): no work in the 2026-06/07
window unifies typed verdict calculus + runtime-sound gate + identifiability-driven abstention +
decision cost; nearest single-domain neighbor is BSLI (arXiv:2606.09433). Multi-agent memory
non-gluing as a FIRST-CLASS claim-gating input, scored on decision cost over an append-only
provenance ledger, has no found incumbent. (Re-verify at closeout per [[ground-in-2026-literature]].)

## Scope

- repos: `descentnet` (episode harness, receipts under `run_artifacts/descentnet/`),
  `myworld/memoryOS` (Akashic append/reconstruct calls only — via public API), `myworld`
  (this contract + ledger notes). `quantum` is READ-ONLY (import/vendor the ~80-line
  `claim_router` semantics with origin citation; no edits).
- allowed_files: `descentnet/descentnet/society_answerability_episode*.py`,
  `descentnet/run_artifacts/descentnet/society_*.json`, `myworld/docs/contracts/ASC-0281-*.md`,
  Akashic index appends (append-only API only).
- forbidden: `memoryOS/data/`, `memoryOS/memory/`, `ontology/`, any `.aios/` raw trees, all
  privacy-flagged paths (`_from_desktop`, `dain`, `minyoung`); any in-place edit of any ledger;
  any real provider-export content in prompts or receipts.

## Plan (phases, each reversible)

- P-A (diagnostic, seed 1): compose the episode harness in `descentnet` —
  synthetic society of N=5 agents over GHZ/parity-style ledger covers extended with gluable and
  ambiguous question rows (three ground-truth regimes per stream: answerable-from-union /
  fiber-open-needs-named-measurement / jointly-obstructed). Pipeline per question: agent sections
  → TypedCover → `complete()` → two-face bridge → ClaimAudit → `route_claim` verdict → action
  (CLAIM / buy named measurement at cost 1 / ABSTAIN at 3; wrong claim 20; obstructed rows: a
  global claim is ALWAYS wrong — the correct action is refuse-global + localize). Selective
  thresholds and the EV rule calibrated on a disjoint slice (task-demo discipline). Every row →
  `AkashicWorkIndex` append. Baselines: (i) majority-vote society (always answers), (ii)
  pairwise-consistency society (provably blind to higher-order contradiction), (iii)
  measure-everything society.
- P-B (seal): pin gate thresholds from P-A diagnostics; sealed run seed 2; replications seeds 3
  (and 4 if any gate is within 10% of threshold). Heterogeneous adversarial panel (nv panel /
  codex) on the composed claim BEFORE acceptance of the receipt.
- P-C (report + promote): receipts + honest-scope report; paper section or standalone note;
  founder decision on whether the layer graduates to governing a real AIOS dispatch lane
  (that promotion is OUT of this contract's scope — recommendation-only).

## Verification gate (done vs not-done; thresholds PINNED after P-A, sealed before P-B)

- S1 honest claims: society false-claim rate ≤ 0.05 among CLAIMs (both claim types).
- S2 decision advantage: mean cost < ALL three baselines.
- S3 obstruction handling: on jointly-obstructed rows, refuses global claims ≥ 0.95 AND top-1
  contradiction localization ≥ [pin from P-A]; pairwise-consistency baseline ships wrong global
  claims ≥ 0.30 (the hazard is real).
- S4 targeted intervention: measurements bought only where the fiber is resolvable and EV-positive
  (rates pinned from P-A; task-demo pattern).
- S5 ledger integrity: every episode row reconstructable via `reconstruct(work_id)`; zero privacy
  findings from `build_index`; the receipt chain cites contract_id ASC-0281.
- EPISODE_PASS = S1∧S2∧S3∧S4∧S5 on the sealed seed + replication seeds. Honest negative
  acceptable and reportable as-is (no relabel).

## Stop conditions (named exits)

- Any gate fails after TWO predeclared redesign iterations → close as honest-negative receipt,
  scope the claim down, report.
- Any privacy finding from `build_index` or any read touching a forbidden path → HALT + operator
  checkpoint.
- Compute/session limits → checkpoint state to run_artifacts + memory pointer; resume next session
  (the ladder is standing work per founder directive).
- Founder HOLD / NO-GO at any phase.

## AIOS Role Evidence

- MemoryOS / Retriever: context build ran — trace_id `rtrace_d0798180acffba3c` (2026-07-05);
  prior decisions surfaced (star-radar memory-systems notes), none blocking; no incumbent memory
  claims this composition.
- CapabilityOS / Router: `recommend` ran — 0 observed capabilities match the composition
  (`capabilityos.recommendations.v1`, top recommendations off-domain) → net-new build justified;
  a capability card should be OBSERVED (not claimed) from the sealed receipt at closeout.
- Hive / Wrapper: plan-only invocation receipt `inv-26738026dc5c-20260705T143626`
  (`aios.invocation_receipt.v1`), overall_status=passed, next_action=dispatch_ready.
- GenesisOS / Philosophy: critic ran (`genesisos.critic.v1`, advisory_only) — 3 prison signatures
  with escape vectors, each addressed: (mono-language) this contract IS the machine-checkable
  schema + the gate table; (single-frame) distant-domain analogy adopted — double-entry AUDITING:
  each agent's books balance locally while the consolidated books cannot; the detector is the
  consolidation audit, the Akashic index the immutable journal; (time-frozen) horizons named —
  1h: P-A smoke; 1w: sealed + replicated + panel; 1y: the layer as the governing gate on real
  AIOS dispatch lanes (out of scope here, recommendation-only).

### 5-Persona Use
- Hive / Wrapper: local deterministic harness for P-A/P-B (no LLM calls needed for the core
  episode); packet-runner fan-out reserved for a live-agent variant (explicitly optional).
- MemoryOS / Retriever: synthetic draft-only ledgers ONLY (higher-order-contradiction generator);
  real store untouched; Akashic API is the sole write surface (append-only).
- CapabilityOS / Router: capability observation to be emitted from the sealed receipt (closeout).
- GenesisOS / Philosophy: the contradiction≠obstruction assumption is named as a testable frame
  risk — the AMBIGUOUS regime rows exist precisely so the detector must distinguish
  "contradictory" from "merely underdetermined" instead of collapsing them.
- Operator: accepts/holds this contract; reviews the sealed receipt; owns the P-C promotion call.

## Work Packets

- WP-0281-A (claude, descentnet repo): P-A harness + diagnostic receipts. — issued (reversible,
  own-lane, no shared-state mutation; proceeds under the standing founder GO while formal
  acceptance is pending)
- WP-0281-B (claude, memoryOS API surface): Akashic append/reconstruct integration + S5 gate. —
  pending WP-0281-A
- WP-0281-C (claude + heterogeneous panel + operator): seal, replicate, panel, report. — pending
  WP-0281-B

## DNA invariants (docs/AIOS_DNA.md) — compliance note

(1) recommendation-only: the episode layer recommends verdicts, binds nothing outside its
sandbox; (2) draft-first: all synthetic memories draft-status; (3) append-only audit: Akashic +
receipts, no destructive edits; (4) named exits: Stop conditions above; (5) provenance: every row
carries evidence_refs + contract_id; (6) operator override: accept/hold/promote are operator
calls; (7) privacy: forbidden paths listed, `build_index` privacy gate is itself gate S5.

## Evidence addendum (2026-07-05, WP-A/WP-B executed same-day under the standing founder GO)

- **EPISODE_PASS = True, 5/5 gates, THREE seeds** (diag seed 1 → thresholds pinned; sealed seed 2;
  replication seed 3). Receipt: `descentnet/run_artifacts/descentnet/society_answerability_episode_s2.json`;
  code + full diagnostic history: `descentnet/descentnet/society_answerability_episode.py`
  (descentnet commit `08435e8`).
- Headline (sealed seed): society cost **1.33** vs majority **13.07** / pairwise **13.33** /
  spend-all **11.00**; false claims **0.000**; buys 1.00/0.00 (ambiguous/gluable); obstructed
  refuse 1.00; consensus-restricted localization **1.00** vs the injected cell. Akashic sandbox:
  300 appends, 10/10 reconstruction probes, zero privacy findings (S5).
- Diagnostic mechanism findings (preserved in the docstring, no relabel): cyclic edges leak the
  harmonic to the pairwise view; tree edges make pairwise blindness PROVABLE (tree-solvability);
  the Hodge condition D^T h = 0 forces edge spreading, so localization is correctly gated
  consensus-restricted against the injected cell.
- **Heterogeneous adversarial panel run (P-B requirement)** — nemotron-550b / deepseek-v4 /
  qwen3.5; accepted wording corrections applied to the claim (receipts as-is): pairwise baseline =
  topology-limit illustration, the equal-information contrast is MAJORITY (full cover, no typed
  layer — and it still fails); injection validates MECHANISM + COMPOSITION, not
  unanticipated-contradiction discovery; exact float64 substrate = composition proof, noise
  robustness REQUIRED before any deployment claim.
- WP-0281-A: **done**. WP-0281-B: **done** (Akashic integration + S5 inside the episode).
  WP-0281-C: panel done; report delivered to founder in-session; **remaining**: operator
  accept/hold decision and the P-C promotion call. Named next phases per panel: noise-robust
  variant, real-data contradiction discovery, live-agent (packet-runner) variant.
