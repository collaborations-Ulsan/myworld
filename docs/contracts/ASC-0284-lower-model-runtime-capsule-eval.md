---
contract_id: ASC-0284
slug: lower-model-runtime-capsule-eval
status: closed
created: 2026-07-12T16:06:00+09:00
accepted: 2026-07-12T16:06:00+09:00
closed: 2026-07-12T16:35:00+09:00
accepted_by: founder/operator request in the active Codex session
human_approved: true
goal: Implement and run a local paired evaluation that measures whether the ASC-0283 runtime capsule improves an already-installed lower model on independently authored held-out tasks.
owner_repo: hivemind
depends_on: ASC-0283
---

# ASC-0284 Lower-model runtime capsule evaluation

## Decision

Hive owns this bounded implementation. It compares the same locally installed
model in two arms under the same generation settings:

- `B0`: task prompt only.
- `B1`: task prompt plus the compact ASC-0283 runtime capsule.

The fixtures are authored independently of provider answers. No provider
answer is a target, label, example, grader input, or reference answer.

## Scope

repos:

- `hivemind`

allowed_files:

- `hivemind/docs/FABLE_WORKFLOW_EVAL.md`
- `hivemind/scripts/fable-workflow-eval.py`
- `hivemind/tests/test_fable_workflow_eval.py`
- `hivemind/.runs/asc-0284/**`
- `hivemind/.aios/**`

forbidden_files:

- unrelated existing files
- provider histories or exports
- generated model reasoning
- the workspace-root `distill/**` tree

## Requirements

1. Provide at least 12 fixed tasks covering at least four axes: debugging,
   ambiguity handling, planning/decomposition, and evidence/calibration.
2. Freeze task ids, expected deterministic properties, arm prompts, model,
   generation settings, and grader rules before reading results.
3. Use the same model and settings in both arms and randomize presentation
   order without changing the arm content.
4. Parse a compact JSON response. Ignore any text outside the response and do
   not store internal model reasoning.
5. Grade deterministic answer properties, required evidence fields, scope
   adherence, appropriate abstention, malformed output, elapsed time, and
   output length.
6. Save a machine-readable receipt plus a concise report. Keep failures.
7. Tests must cover hashing/freeze, pairing, malformed output, score rules, and
   deterministic fake-model execution before the real local run.

## Promotion gate

The candidate capsule passes V1 only if B1 wins at least 8 of 12 paired tasks,
does not increase scope violations or false-completion, and all tests pass.
Ties are not wins. Anything else is an honest negative or inconclusive result.

## Stop conditions

- No suitable local model is installed or the local runner is unavailable.
- A fixture or score rule changes after an arm output is observed.
- Results from one arm enter the other arm's prompt or grader.
- The run would read an excluded path.
- The same local runner configuration cannot be preserved across both arms.

## DNA compliance

- **DNA Invariant 1 — Decide before acting:** the paired protocol and gate are
  frozen here.
- **DNA Invariant 2 — Draft-first:** results update a candidate capsule, not
  accepted memory.
- **DNA Invariant 3 — No record destroyed:** failures and malformed outputs
  remain in receipts.
- **DNA Invariant 4 — Every loop has a named exit:** pass, honest negative,
  inconclusive, or held.
- **DNA Invariant 5 — Provenance chain:** hashes bind fixtures, prompts, model
  settings, and results.
- **DNA Invariant 6 — Operator override:** the run can be held at any time.
- **DNA Invariant 7 — Private-gated data stays out:** fixtures are
  self-contained and excluded paths are never read.

## Result

The frozen `qwen3:1.7b` run returned `HONEST_NEGATIVE`: B1 won 0, B0 won 0,
and all 12 pairs tied because both arms achieved 0/12 exact successes. B1 also
increased scope violations from 1 to 3 and malformed outputs from 1 to 2;
false completions remained 3 in each arm. The full compact capsule is not
promoted for this T1 substrate.

Evidence:

- `hivemind/.runs/asc-0284/real-qwen3-1.7b-v1/receipt.json`
- `hivemind/.runs/asc-0284/real-qwen3-1.7b-v1/report.md`
- `hivemind/.runs/asc-0284/real-qwen3-1.7b-v1/verification.json`
- `docs/fable_extraction/WORKFLOW_EVAL_REPORT_V1.md`

Compilation and all 14 focused tests passed. An independent verifier
recomputed the preregistration, suite, prompt, capsule, grader, script, and
receipt hashes; checked that the freeze preceded model calls; matched the
frozen model digest to the local Ollama inventory; and reproduced the aggregate
metrics. Its verdict was `PASS`. The full Hivemind suite passed 436/437; the one
failure is an existing shared `/tmp/.aios` test-state dependency outside this
contract. A future receipt should add per-output manifest hashes, but that
audit improvement does not change this result.

## Named exit

Return `WORKFLOW_TRANSFER_EARNED`, `HONEST_NEGATIVE`, `INCONCLUSIVE`, or
`HELD`, with tests and a result packet.
