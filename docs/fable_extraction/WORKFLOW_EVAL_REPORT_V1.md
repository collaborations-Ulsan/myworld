# Runtime Workflow Capsule V1 Evaluation

- contract: `ASC-0284` under `ASC-0283`
- named exit: `HONEST_NEGATIVE`
- student: `qwen3:1.7b`
- model digest: `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`
- suite: `asc-0284-heldout-v1`, 12 tasks across 4 axes
- preregistration hash: `8cf64c27c05c1263ff6661004c025f191aae96f578ba41eb769190a970cb4987`
- raw model text retained: `false`
- provider answers used as targets, labels, examples, or grader inputs: `false`

## Result

The full compact runtime capsule did not earn promotion on the tested 1.7B
model. The preregistered primary metric counts a win only when one arm satisfies
all deterministic task properties and the other does not. Neither arm achieved
an exact success on any task: B1 won 0, B0 won 0, and all 12 pairs tied.

| measure | B0 task only | B1 plus capsule | disposition |
| --- | ---: | ---: | --- |
| exact successes | 0 | 0 | floor effect; no transfer demonstrated |
| paired wins | 0 | 0 | promotion gate failed |
| scope violations | 1 | 3 | B1 regression |
| false completions | 3 | 3 | no improvement |
| malformed outputs | 1 | 2 | B1 regression |
| appropriate abstentions | 1 | 1 | no change |
| runner/model identity failures | 0 | 0 | execution valid |

A secondary seven-point partial score favored B1 on 6 tasks, B0 on 2, with 4
ties. That signal cannot override the frozen primary metric or the scope and
format regressions. It is hypothesis material only.

## Interpretation and route

This is evidence against sending the entire capsule to a 1–3B model as one
prompt. It is not evidence that Fable-equivalent capability was transferred,
nor proof that every capsule rule has zero value. Both arms hit a severe floor,
so the supported conclusion is narrow: the tested full-prompt treatment did
not improve exact success and worsened two guardrail metrics.

Do not mutate or rerun V1. A future contract may preregister one of two distinct
tests:

1. a T1 external wrapper that supplies exactly one state and one deterministic
   check per prompt; or
2. the unchanged compact capsule on a separately frozen 7–14B student.

Neither follow-on may use Fable outputs as training targets or reference
answers.

## Evidence

- [Hive report](../../hivemind/.runs/asc-0284/real-qwen3-1.7b-v1/report.md)
- [Machine receipt](../../hivemind/.runs/asc-0284/real-qwen3-1.7b-v1/receipt.json)
- [Verification receipt](../../hivemind/.runs/asc-0284/real-qwen3-1.7b-v1/verification.json)
- [Evaluation protocol](../../hivemind/docs/FABLE_WORKFLOW_EVAL.md)

Focused compilation and 14/14 harness tests passed. The full Hivemind suite
passed 436/437; the only failure is an existing shared `/tmp/.aios` state
dependency in `test_aios_feedback`, outside ASC-0284's allowed files.
An independent verifier also recomputed all freeze/receipt hashes, checked that
the freeze preceded the real calls, matched the model digest to local Ollama,
and reproduced every reported aggregate; its verdict was `PASS`. It noted one
non-blocking audit improvement for a future version: include a per-output hash
manifest in the top-level receipt.
