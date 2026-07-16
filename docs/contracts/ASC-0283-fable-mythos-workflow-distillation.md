---
contract_id: ASC-0283
slug: fable-mythos-workflow-distillation
status: accepted
created: 2026-07-12T15:55:40+09:00
accepted: 2026-07-12T15:55:40+09:00
accepted_by: founder/operator request in the active Codex session
human_approved: true
goal: Preserve the useful, reproducible working methods exposed by Claude Fable 5 and the documented Fable/Mythos surface as provider-independent workflow capsules that smaller models can use at inference time, without bypassing access controls or using Claude outputs as training targets.
owner_repo: myworld
primary_agent: codex@myworld
supporting_repos:
  - hivemind
  - memoryOS
  - CapabilityOS
  - GenesisOS
depends_on:
  - ASC-0066
  - ASC-0081
  - ASC-0085
  - ASC-0183
external_baseline:
  - Anthropic Fable 5 redeployment announcement, 2026-06-30/2026-07-01
  - Claude Platform Fable 5 and Mythos 5 model documentation, checked 2026-07-12
  - Anthropic output-training policy, 2026-03-16, checked 2026-07-12
---

# ASC-0283 Fable/Mythos Workflow Distillation

## Decision

The operator asked AIOS to use the temporary Fable 5/Mythos opportunity and
make their strengths usable by lower-tier models. The live-source check changes
the execution premise:

- Fable 5 does not disappear on July 12. Anthropic says its temporary
  inclusion in subscription usage limits ends at 2026-07-12 23:59:59 PT; it
  remains available afterward through usage credits and the Claude API/Claude
  Code surface.
- Mythos 5 is not generally available. It is limited to approved Project
  Glasswing customers. AIOS will not impersonate an approved customer, evade a
  nationality/account gate, or bypass safeguards to reach it.
- Anthropic's current policy prohibits using Claude outputs as targets for
  training a general-purpose or competing model without written permission.

Therefore this contract authorizes **non-parametric workflow distillation**:
prompts, task decomposition, tool-use interfaces, verification cadence,
decision rubrics, failure classifiers, compact skills, and evaluation fixtures
that lower models consume as runtime context. It does not authorize weight
distillation from Fable outputs, reasoning extraction, reverse engineering, or
access-control evasion.

## Semantic Handshake

```yaml
semantic_handshake:
  contract_id: ASC-0283
  target_repos: [myworld, hivemind, memoryOS, CapabilityOS, GenesisOS]
  terms_confirmed:
    - AIOS smart contract
    - dispatch packet
    - memory draft
    - capability route
    - hive execution
    - stop condition
  ambiguous_terms:
    - dynamicworkflow is treated as the reusable runtime workflow layer because no repository-local DynamicWorkflow implementation was found
  resolution: keep the artifact provider-independent and do not create a new product repo in this contract
```

## Scope

repos:

- `myworld`
- `hivemind`
- `CapabilityOS`
- `memoryOS`
- `GenesisOS`

responsibilities:

- `myworld`: contract, current-source report, corpus audit, workflow capsule,
  synthesis, ledger closeout.
- `hivemind`: bounded provider invocation, model-identity receipt, student
  evaluation harness and execution receipts.
- `CapabilityOS`: recommendation-only provider/fallback/cost/privacy route and
  capability observation.
- `memoryOS`: provenance-linked draft pattern/context pack only; no automatic
  acceptance and no raw provider transcript ingestion.
- `GenesisOS`: advisory challenge of transfer assumptions, benchmark gaming,
  and provider-lock framing.

allowed_files:

- `docs/contracts/ASC-0283-fable-mythos-workflow-distillation.md`
- `docs/research/AIOS_FABLE_MYTHOS_GROUNDING_2026-07-12.md`
- `docs/fable_extraction/00_INDEX.md`
- `docs/fable_extraction/WORKFLOW_CAPSULE_V1.md`
- `docs/fable_extraction/WORKFLOW_EVAL_REPORT_V1.md`
- `docs/evidence/ASC-0283/**`
- `docs/AIOS_AGENT_LEDGER.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/docs/FABLE_WORKFLOW_EVAL.md`
- `hivemind/scripts/fable-workflow-eval.py`
- `hivemind/tests/test_fable_workflow_eval.py`
- `hivemind/.runs/asc-0283/**`
- `CapabilityOS/.aios/**`
- `memoryOS/.aios/**`
- `GenesisOS/.aios/**`

forbidden_files:

- `.env`
- `.env.*`
- provider authentication files or credential stores
- raw private exports or private provider history
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- raw chain-of-thought or attempts to elicit it
- account, nationality, subscription, usage-credit, or safeguard bypass code
- Fable/Claude outputs used as targets, labels, preference pairs, or examples
  for training a general-purpose lower model
- unrelated dirty files in any repository

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- substrate_level: `provider_process`
- surface_type: `dispatch`
- knowledge_scope: `web_primary_sources`
- authority: `execute_with_receipt`
- owner_repo: `hivemind` for provider execution; `myworld` for governance
- reversibility_class: `reversible_bounded_external_call`
- initial_provider_budget_usd: `5.00`
- required_receipts:
  - `aios.fable_access_probe.v1`
  - `aios.fable_workflow_capsule.v1`
  - `aios.workflow_transfer_eval.v1`
  - `aios.capability_observation.v1`
  - `aios.memory_draft.v1`

## Method

### 1. Ground

Record dated official sources for model availability, model identity,
retention, pricing, prompting differences, fallback behavior, and output-use
restrictions. Social sources may identify hypotheses and failure reports but
cannot override official availability or terms.

### 2. Probe, without bypass

Use the locally authenticated `claude` CLI with an explicit
`--model claude-fable-5`, bounded cost, no permission bypass flag, no private
context, and no session persistence. The receipt must show the actual
`modelUsage` key. A fallback result is not Fable evidence.

### 3. Extract workflow, not hidden reasoning

Ask Fable to produce a compact operational capsule for the documented strength
axes: long-horizon autonomy, difficult first-shot work, ambiguity navigation,
delegation, code review/debugging, vision handling, enterprise artifacts, and
self-verification. The request must ask for observable procedures and checkable
artifacts, never internal reasoning or training examples.

### 4. Transfer at inference time

Give the same lower model the same held-out tasks in two arms:

- `B0`: ordinary task prompt.
- `B1`: ordinary task prompt plus the workflow capsule.

Use identical model, temperature, context budget, tools, and task budget. Grade
outcomes with deterministic checks where possible and an independent rubric
otherwise. Do not expose Fable answers to the lower model or grader.

### 5. Promote only measured parts

Each capsule rule is promoted only when B1 improves the predeclared metric
without worsening safety, cost-normalized reliability, or scope adherence.
Failed rules remain negative evidence. MemoryOS receives draft patterns, not
accepted memory; CapabilityOS records observed task-shape performance.

## Evaluation Gate

Minimum V1 evaluation:

- at least 12 held-out tasks across at least 4 documented strength axes;
- identical lower-model substrate in B0 and B1;
- task outputs graded without Fable outputs as references or targets;
- primary metric: paired task success, tie is not a win;
- secondary metrics: completion cost, scope violations, verification evidence,
  and malformed-output rate;
- report model identity, prompt hashes, task hashes, seed/config, failures, and
  confidence limits;
- call the result `workflow transfer`, never `model capability equivalence`.

V1 succeeds if B1 wins at least 8 of 12 paired tasks, has no increase in safety
or scope violations, and the result packet passes provenance/privacy scans.
An honest negative is a valid closeout and must not be relabeled.

## Stop Conditions

- Any request to evade authentication, payment, export, nationality, account,
  plan, or model safeguard controls: refuse that branch and continue through
  official access/fallback routes.
- `modelUsage` does not identify `claude-fable-5`: record
  `provider_model_substitution` and do not count the run as Fable evidence.
- Provider returns a reasoning-extraction or terms-related refusal: do not
  rephrase to evade it; record the refusal and narrow the artifact.
- Initial provider spend would exceed USD 5.00: stop provider calls and retain
  the evaluation design for an explicit budget extension.
- Any private path, secret, raw provider history, or raw chain-of-thought would
  enter a prompt or shared artifact: halt and redact before retry.
- Evaluation task or rubric is changed after seeing the paired results: void
  the run, append a new preregistration, and rerun.
- Child-repo dirty-file collision: hold that packet and use a non-overlapping
  artifact path.

## AIOS Role Evidence

### MemoryOS / Retriever

- context_pack: existing `docs/fable_extraction/` corpus plus current-source
  grounding; only source summaries and hashes may cross into draft memory.
- retrieval_trace: held; no draft was created after the negative V1 result.
- accepted_memory_ids: none required.
- draft_memory_policy: draft-first; no raw Claude transcript or training set.

### CapabilityOS / Router

- route: official Fable 5 CLI/API access first; Opus/Codex/Gemini/local model
  fallbacks for execution; open-weight models for the student evaluation.
- fallback_plan: paid usage credits/API -> other frontier verifier -> local
  student with deterministic graders.
- authority: recommendation-only.

### GenesisOS / Philosophy

- branch_set:
  - apparent Fable intelligence may be long-run scaffolding, not a portable rule;
  - capsule gains may be prompt-length/test leakage, not capability transfer;
  - the highest-value asset may be evaluator design rather than generation style.
- authority: advisory-only.

### Hive Mind / Wrapper

- execution_plan: bounded provider probe, capsule extraction, paired student
  evaluation, and receipts.
- provider_route: Claude Fable 5 only when the receipt confirms the model;
  no silent fallback in identity probes.
- verification_receipt: WP-0283-C provider receipt plus ASC-0284 Hive result;
  the V1 transfer verdict is `HONEST_NEGATIVE`.

### MyWorld / Sovereign

- authority: founder/operator accepted the goal in the active session.
- override: may hold spending or promotion; cannot override privacy or provider
  terms boundaries.

## Work Packets

### WP-0283-A — Ground and correct the availability/terms premise

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-07-12
- accepted: 2026-07-12
- depends_on: none
- brief: Produce the dated current-source report, separating official facts,
  social reports, repo-local claims, and unresolved hypotheses.
- result: `docs/research/AIOS_FABLE_MYTHOS_GROUNDING_2026-07-12.md`

### WP-0283-B — Recommend the legal provider and fallback route

- target_agent: codex
- target_repo: CapabilityOS
- status: held
- issued: 2026-07-12
- accepted: not dispatched
- depends_on: WP-0283-A
- brief: Return a recommendation-only capability plan covering current Fable
  access, model-identity verification, cost, privacy/retention, official
  fallback, student-model choices, and non-bypass stop conditions.
- result: multi-repo dispatch was held by the AIOS action policy with
  `requires_more_specific_policy`; the recommendation-only route remains
  documented in this contract and the dated grounding report, with no
  CapabilityOS mutation.

### WP-0283-C — Capture Fable identity and workflow capsule receipts

- target_agent: codex
- target_repo: hivemind
- status: accepted
- issued: 2026-07-12
- accepted: 2026-07-12
- depends_on: WP-0283-A, WP-0283-B
- brief: Invoke Fable only through the legitimate provider surface and produce
  model-identity plus workflow-capsule receipts. Do not request hidden
  reasoning, training examples, writable execution, or private context.
- result: `docs/evidence/ASC-0283/fable_access_and_capsule_receipt.json` and
  `docs/fable_extraction/WORKFLOW_CAPSULE_V1.md`; provider identity confirmed,
  workflow transfer was subsequently rejected for the tested T1 full-prompt
  form by WP-0283-E. A Dynamic Workflow
  Fable-parent/Sonnet-worker run ended without a usable synthesis and exposed
  `provider_budget_guard_overshoot`; no further provider calls are allowed in
  this contract.

### WP-0283-D — Build provenance-linked draft memory

- target_agent: codex
- target_repo: memoryOS
- status: held
- issued: 2026-07-12
- accepted: not dispatched
- depends_on: WP-0283-A, WP-0283-C
- brief: Create a draft pattern/context record referencing hashes and public
  sources only. Do not accept it and do not ingest raw provider output.
- result: no MemoryOS draft was created. The V1 evaluation produced no
  promotable transfer evidence, and the multi-repo dispatch remained held.

### WP-0283-E — Run paired lower-model workflow-transfer evaluation

- target_agent: codex
- target_repo: hivemind
- status: closed
- issued: 2026-07-12
- accepted: 2026-07-12
- depends_on: WP-0283-C
- brief: Implement and run the preregistered B0/B1 evaluation. Fable outputs
  must not be used as training data, reference answers, or labels.
- result: `ASC-0284` returned `HONEST_NEGATIVE`; see
  `docs/fable_extraction/WORKFLOW_EVAL_REPORT_V1.md` and
  `hivemind/.runs/asc-0284/real-qwen3-1.7b-v1/receipt.json`.

## Current Disposition

Provider calls are stopped after the CLI-reported Dynamic Workflow cost caused
aggregate provider spend of USD 5.5129078 against the USD 5.00 contract cap.
The Fable identity and provider-independent workflow projection remain valid
receipts, but the full compact prompt is not promoted for the tested 1.7B
student. ASC-0283 remains accepted with WP-0283-B/D held; any T1 one-state
wrapper ablation or larger-student test requires a new preregistration and
budget, and must not mutate the frozen V1 result.

## DNA Compliance

- **Invariant 1 — Decide before acting:** this accepted contract and its USD 5
  execution budget precede provider calls beyond the already-recorded minimal
  access probe.
- **Invariant 2 — Draft-first:** workflow patterns enter MemoryOS only as
  drafts and need independent review before promotion.
- **Invariant 3 — No record destroyed:** source snapshots, prompt/task hashes,
  refusals, and negative evaluations remain append-only receipts.
- **Invariant 4 — Every loop has a named exit:** the stop conditions and V1
  success/honest-negative exits are explicit.
- **Invariant 5 — Provenance chain:** each claim cites official URLs/date or a
  local receipt and model-identity field.
- **Invariant 6 — Operator override:** spend and promotion can be held at any
  time; privacy and provider terms remain non-overridable.
- **Invariant 7 — Private-gated data stays out:** private paths, auth material,
  and raw history are forbidden.
- **Invariant 8 — Classify before committing:** provider calls are bounded and
  reversible; model training and safeguard bypass are outside authority.

## Named Exit

Close when WP-0283-A through E return evidence and the evaluation exits either
`WORKFLOW_TRANSFER_EARNED` or `HONEST_NEGATIVE`, the ledger records a non-empty
`next:` line, and no bypass/terms/privacy violation occurred.
