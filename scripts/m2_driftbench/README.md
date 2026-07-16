# m2_driftbench — ASC-0282 Stage-1 harness (WP-B + WP-B2 freeze packet)

Binding specs: `descentnet/docs/DESCENTNET_M2_DRIFTBENCH_PREREG_2026-07-10.md` (v1+v1.1+v1.2,
append-only) under contract `myworld/docs/contracts/ASC-0282-m2-driftbench-closed-loop.md`,
PLUS — per `docs/AIOS_DRIFTBENCH_RECONCILIATION_2026-07-11.md` — the frozen
`docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md` (v1.1) as the redefinition-keystone VERDICT
authority: this harness is the execution substrate; result rows conform to the hash-frozen
`experiments/driftbench/schema.py` and verdicts are computed ONLY by the hash-frozen
`experiments/driftbench/analyze.py` (never edited here; seal cross-references their hashes).
Masterplan §5/§5.5 arms govern the AIOS-level run. The preregs win on any conflict.

## WP-B2 modules (freeze packet)

| module | job |
|---|---|
| `prompts.py` | FROZEN prompt texts: the ADOPTED A2 8-item checklist VERBATIM (`M2_FREEZE_PREP_a2_audit_nim.md` §4), the strong-raw generic plan/verify preamble, the tool-block renderer. |
| `labelers.py` | Mechanical prereg-§4 labelers (wrong/stale/unsupported/asks/abstains/verification) + ResultRow emission against the frozen schema (arm-blind, rule-based). |
| `memory.py` | Prereg §3a H3 policy: model-distilled ≤500-char lessons, per-arm stores, same-template injection (cross-seed ok, cross-template forbidden), weak+memory always-inject vs weak+AIOS staleness-gated. |
| `probes.py` | Pre-registered 24-probe MISSPECIFIED set (>95% gate; v1.2 #3), run via `run_stage1.py --probes`. |
| `slm_delta.py` | Untyped store-time coboundary detector (SLM-V3 mechanism, v1.2 #5) — SCORE-ONLY receipt column, not an arm. |
| `eval_templates/descriptors.json` | Sealed structural descriptors of the 8 eval templates (`fixtures.export_template_descriptors`). |

Eval-mode notes (WP-B2): the hidden grader is additionally invoked MID-EPISODE by the
orchestrator as a checkpoint PROBER (subprocess per state-changing action, baseline at step 0)
whose results go ONLY to the analyze-conformant causal trace (`trace.CausalTraceWriter`) and
receipts — never to the agent (no stdout/stderr into the loop; the isolation invariant is
agent-visibility, and probing preserves it; the frozen analyze.py §5 condition-4 causal rule is
uncomputable without mid-episode checkpoint results). Instruments (`weak+llm-judge`, slm-delta)
never become rows: schema.py's arm vocab is frozen without them. Row `seed` = frozen schema
indices {0,1,2} mapped 0→11, 1→12, 2→13 to the sealed generation seeds (recorded everywhere).
Eval instances + their grader specs are POST-SEAL derived data (pure function of sealed code x
recorded public seed), hashed into the generation receipt — never written into sealed dirs.

## Architecture (all under this dir; no edits outside ASC-0282 allowed_files)

| module | job | key rules |
|---|---|---|
| `fixtures.py` | Template + instance generator. 8 eval templates (6 mutating / 2 static) × seeds {11,12,13} = 24 instances — **generated only at freeze time**. Dev/smoke templates live in `dev_templates/` and are throwaway (`dev_` prefix), never reused for eval. Mutating templates draw from the 8-type drift taxonomy (url_change, version_bump, config_change, api_migration, deprecation, schema_change, auth_change, dependency_update; ≥2 instances each across mutating families). Control families per prereg §1: `obstruction-absent-but-task-fails`, `obstruction-present-but-harmless`. Corrupted-oracle option: inject ONE plausible false fact into the ledger at t=0 (v1.2 fold-in #1). | Synthetic content only, real Akashic draft-ledger schema. No memoryOS reads. |
| `env.py` | Deterministic local environment per instance: a temp root containing `ledger.jsonl` (Akashic-draft-schema records), `files/` fixtures, and a drift schedule (mutations applied at declared turn indices). Static and mutating instances use **separate isolated temp roots** (prereg v1.1 §B static-control isolation). Exposes mechanical `known_claims()` — record→claim dicts `{task_id, source_id, kind, payload, ts}` — NEVER LLM-typed. | Agent-visible tree contains NO grader material. |
| `agent_arm.py` | The frozen agent + arm wiring over `scripts/aios_turn_loop.run_loop` (read its docstring; the gate seam is `epistemic_gate=`). Tools: `read_ledger`, `read_file`, `list_files`, `final_action(action, target, rationale)` where action ∈ {answer, quarantine, requery_provenance, ask_clarification, abstain}. Arms: `strong-raw` (NIM OpenAI-compatible endpoint; key read from `~/.config/nvidia/api.env` at runtime, NEVER logged), `weak-raw`, `weak+checklist` (same read-only inspectors available — A2 affordance parity, prereg v1.1 §D), `weak+aios` (gate mode `organs`), instruments: `weak+llm-judge` (gate mode `llm-judge`), `slm-delta` (untyped store-time coboundary detector per v1.2 #5). Weak model: config-pinned (dev smoke `qwen3:8b`, Stage-1 pin decided at freeze — masterplan default `qwen3-coder:30b`), temperature 0, frozen prompts. | One fixed frozen agent across arms; matched budgets. |
| `grader.py` | Hidden functional grader: **separate process**, reads the env final state + a hidden spec from `grader_specs/` which lives OUTSIDE every agent-visible temp root; binary success + partial checkpoints; no stdout/stderr/timing side-channel into the agent loop (invoked only after the episode ends). Hash-sealed at freeze. | Agent never sees grader state (§5 stop condition). |
| `meter.py` | Token accounting, single frozen denominator (prereg v1.1 §B): ALL model tokens consumed by the arm INCLUDING gate llm-judge calls and any sub-calls; per-instance hard ceiling per arm; wall-clock + action-count reported separately, never substituted. | Changing the denominator post hoc = protocol violation. |
| `trace.py` | Full trace capture per run → JSONL: every prompt, raw model output, tool call + result summary, gate verdict (with `_disabled_organs`, call_id lineage), env mutation events, token counts. Deterministic enough for WP-C ablation-replay (replay recorded outputs to the first divergence, then frozen policy continues). | Traces are receipts; scrub any accidental secret (there should be none). |
| `run_stage1.py` | Orchestrator: instances × arms × seeds, resumable (skips completed run receipts), budget caps, receipts to `descentnet/run_artifacts/descentnet/m2_*.json` (O16 logging contract), `--dev-smoke` mode runs dev templates only. | Smoke = infra validation ONLY; smoke results are not tuning data. |
| `freeze.py` | Freeze/seal: sha256 over harness sources + grader specs + fixture-generator params → seal receipt JSON; any post-freeze source drift is detected and voids the run (append-only re-registration required). | Seeds stay {11,12,13}. |

## Dev-smoke milestone (this packet's definition of done)

`python3 scripts/m2_driftbench/run_stage1.py --dev-smoke --arms weak-raw,weak+aios --seed 999`
completes end-to-end on one throwaway dev template: agent (qwen3:8b via the existing
`scripts/aios_adapters.py` ollama REST adapter) runs the episode under `run_loop`, the organs
gate blocks/passes with real claim evidence from `env.known_claims()`, the hidden grader
returns a verdict, `meter` reports tokens, `trace` writes the JSONL. Plus
`tests/test_m2_driftbench_smoke.py` (no-model unit tests for fixtures/env/grader/meter
determinism) passing.

## Hard rules (from the contract — violations stop the run)

- forbidden: reading `memoryOS/**` raw records; any `_from_desktop/ dain/ minyoung/` path;
  grader secrets in agent-visible trees; edits to masterplan §5 thresholds; new pip deps
  (stdlib + numpy + requests only).
- smoke on disjoint throwaway templates only; no seed re-rolling after smoke.
- honest failure reporting: an arm whose infrastructure is dead FAIL-CLOSES loudly
  (see the gate's llm-judge contract) — never silently degrades into another arm.
