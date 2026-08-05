# Channel-E results — arms run (generated 2026-07-27T19:02:09+00:00, driver `run_arms_e.py`)

Protocol: `docs/AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md` (frozen; Errata N=32). Student FROZEN in both arms: `qwen3-coder-next`. K=5 turns, identical interface, escalation OFF. Raw per-task records: `channel_e_results.jsonl`.

**MORTUARY CLAUSE in force**: if the kill rule fires, Channel E is falsified and with it the "compound in the OS" thesis — no re-run with a new mechanism, metric, or task shape.

## Run-validity gate (§3)

**PASSED** — dispatch invocations: 0, tasks with non-trivial closure: 32 (the treatment substrate was active).

## Headline numbers (paired tasks only; infra-dropped and voided excluded)

- paired tasks analysed: **32** of 32 (infra-dropped: 0, voided: 0)
- P_auto control: **0.375** · P_auto treatment: **0.375** · C_overall = **0.0**
- discordant pairs: b (T-only pass) = **3**, c (C-only pass) = **3** (rate 0.1875)
- McNemar exact one-sided p (H1: treatment > control, α=0.05): **0.6562**
- power of N=32 for the pre-registered ≥15 pp target (Connor 1987, at max(observed disc, 0.15)): **0.6314**

## Per-epoch compounding statistic

| epoch | pairs | P_auto(C) | P_auto(T) | C_k |
|---|---|---|---|---|
| E1 | 8 | 0.625 | 0.375 | -0.25 |
| E2 | 8 | 0.375 | 0.625 | 0.25 |
| E3 | 8 | 0.125 | 0.25 | 0.125 |
| E4 | 8 | 0.375 | 0.25 | -0.125 |

OLS slope of C_k over epochs: **0.025**

## Secondary (pre-registered §4 — reported, never substituted for the primary)

- turns among solved: control mean 5.0, treatment mean 4.42 (predicted mechanism: turn compression)
- dispatch invocations per treatment task: "none \u2014 dispatch never used"
- closure precision (true fix inside C(F)): **0.8438** over 32 treatment tasks
- closure sizes: [{"task_id": "p5-001-8ae428b3", "n_files": 2}, {"task_id": "p5-002-a6785e7f", "n_files": 8}, {"task_id": "p5-003-0d1a189f", "n_files": 4}, {"task_id": "p5-004-badd98c2", "n_files": 4}, {"task_id": "p5-005-2f94aa2e", "n_files": 5}, {"task_id": "p5-007-87afc6f1", "n_files": 3}, {"task_id": "p5-008-af31841e", "n_files": 6}, {"task_id": "p5-009-eea69885", "n_files": 5}, {"task_id": "p5-010-0d5a12b5", "n_files": 5}, {"task_id": "p5-012-e4825c5b", "n_files": 7}, {"task_id": "p5-013-fd6d0aab", "n_files": 9}, {"task_id": "p5-014-72ddf784", "n_files": 3}, {"task_id": "p5-015-e2bd3444", "n_files": 4}, {"task_id": "p5-016-a5f20467", "n_files": 3}, {"task_id": "p5-018-d20a71c3", "n_files": 4}, {"task_id": "p5-019-b5e92f7a", "n_files": 6}, {"task_id": "p5-020-6ee07972", "n_files": 4}, {"task_id": "p5-021-fb704b5c", "n_files": 1}, {"task_id": "p5-023-9ae0fdd1", "n_files": 7}, {"task_id": "p5-024-ba17518d", "n_files": 1}, {"task_id": "p5-025-09b5c312", "n_files": 2}, {"task_id": "p5-026-35358b51", "n_files": 2}, {"task_id": "p5-027-eabf59c3", "n_files": 4}, {"task_id": "p5-029-86f8b0d9", "n_files": 4}, {"task_id": "p5-030-c069564a", "n_files": 6}, {"task_id": "p5-031-09cce709", "n_files": 4}, {"task_id": "p5-032-77450c42", "n_files": 8}, {"task_id": "p5-034-7bf9d8a2", "n_files": 2}, {"task_id": "p5-035-a49332bf", "n_files": 4}, {"task_id": "p5-036-372841b1", "n_files": 3}, {"task_id": "p5-037-fb01c7a1", "n_files": 3}, {"task_id": "p5-038-8d16b2a4", "n_files": 12}]
- oracle-block attempts (both arms, §1.3 guard): 33
- skills registered during the run (gate-passed): [{"task_id": "p5-003-0d1a189f", "verdict": "registered", "id": "skill-8d032c6fa99b814e"}, {"task_id": "p5-004-badd98c2", "verdict": "registered", "id": "skill-ca3393c3ed119e37"}, {"task_id": "p5-015-e2bd3444", "verdict": "registered", "id": "skill-c11b761ef96b7448"}, {"task_id": "p5-020-6ee07972", "verdict": "registered", "id": "skill-241a7e527b27044d"}]
- skills rejected by the gate: [{"task_id": "p5-002-a6785e7f", "verdict": "rejected_unit_test_failed", "id": "skill-50f633b94e44d194"}, {"task_id": "p5-012-e4825c5b", "verdict": "rejected_unit_test_failed", "id": "skill-39a41ad3fde54abb"}, {"task_id": "p5-016-a5f20467", "verdict": "rejected_unit_test_failed", "id": "skill-d16834905c483168"}, {"task_id": "p5-018-d20a71c3", "verdict": "rejected_unit_test_failed", "id": "skill-e6577d628369e80c"}, {"task_id": "p5-019-b5e92f7a", "verdict": "rejected_unit_test_failed", "id": "skill-097550f4e3873083"}, {"task_id": "p5-029-86f8b0d9", "verdict": "rejected_unit_test_failed", "id": "skill-5ed2bf18e712bf2d"}, {"task_id": "p5-030-c069564a", "verdict": "rejected_unit_test_failed", "id": "skill-8df9ac061508fb51"}, {"task_id": "p5-031-09cce709", "verdict": "rejected_unit_test_failed", "id": "skill-53f52144e9c36f34"}]

## Guards

- tests/ tampering incidents (scored FAIL): none
- infra-dropped tasks: none

## KILL RULE (§4, computed — verdict recorded by the operator in the prereg Errata)

- C_overall ≤ 0: **True**
- one-sided 95% upper bound on the advantage: **0.1259** — excludes ≥5 pp: **False**
- discordance ≲5% with the mechanism fired: **False** (dispatch fired 0×, non-trivial closure on 32 tasks)

Interpretation boundary (§5, written before the data): ≥+15 pp significant with the mechanism demonstrably active → first earned evidence, Scaffolding-Swap next. 0 < C < 15 pp → unconfirmed hint, thesis does NOT survive on it. C ≤ 0 or kill-rule fired → thesis dead; publish the three-channel null. Prior: 20% compounds / 80% well-instrumented null.

---

## Operator verdict + post-hoc diagnostics (claude@myworld, 2026-07-28 — appended below the generated report; the numbers above are untouched)

**KILL RULE FIRED on §4 condition 1 (`C_overall = 0.000 ≤ 0`). Channel E falsified; with the Mortuary
Clause the "compound in the OS" thesis is dead. θ (weights), X (context), E (runtime/control-flow) —
all three transports returned well-instrumented nulls.** Verdict recorded in the prereg Errata.

Adversarial post-checks run BEFORE recording the verdict (all factual, from `channel_e_results.jsonl`):

1. **Instrument sensitivity**: discordance 18.75% (6/32 pairs) — vs the X-pilot's 4.3%. The K-turn
   interface can move outcomes; the null is not a frozen dial.
2. **Mask-miss artifact ruled out**: 5/32 tasks had the true fix OUTSIDE C(F) (closure precision
   0.844). Four of them failed in both arms (no pair asymmetry); exactly one (p5-001) is a C-only loss.
   Charitably flipping that single pair gives C ≈ +3.1 pp, McNemar p = 0.34 — nowhere near the
   pre-registered ≥15 pp bar. The null is robust to the mask's imprecision.
3. **Honest mechanism exposure**: (a) dispatch — 4 skills were gate-registered during the run
   (8 rejected by the sandbox+unit-test gate) and offered on every subsequent task's tool surface, yet
   the model invoked a skill **0 times in 32 episodes**; (b) masking — **0** read/write tool calls were
   physically blocked: the treatment model never even attempted an out-of-closure file. The E-substrate
   as specified therefore acted purely through guidance (the restricted listing), and that guidance
   produced no net advantage. This is reported so the null is attributed precisely: *offered-but-unused
   dispatch + guidance-only masking*, evaluated jointly per the frozen Mortuary Clause.

### 3b. Correction to the attribution above (2026-08-05)

The statement in (a) was imprecise and is corrected here rather than quietly edited. Sharpened by the
author of the QEL design when we put these numbers to it
(`docs/external/gpt/qel_author_response_to_our_null_2026-08-05.md`):

> **With 0 invocations, the sub-routines' own efficacy was NOT measured.** No episode is
> "as-treated", so the intrinsic effect of verified dispatch is *unidentified*, not falsified. What
> this run falsified is a narrower and different proposition: **"show a model a verified dispatch
> surface and it will recognise and call it."** That design failed.

Two consequences we adopt:
- **The 0/32 is itself a statistic.** Under an i.i.d. Bernoulli assumption the one-sided 95% upper
  bound on the invocation rate is ≈ **8.9%** — and since the instrument WAS sensitive (18.75%
  discordance), "no applicable occasion arose" is a strained explanation.
- **An operator claim needs three stages, and we failed at the first:** (i) does invocation happen at
  all, (ii) is the invoked operator better than the primitive, (iii) is there a net system-level
  improvement. Failing (i) means this run **may not be counted as a test of a runtime experience
  transport at all** — which does not rescue Channel E (the Mortuary Clause evaluated the named
  architecture as a whole, and the masking half fired on 32/32 tasks and still produced C = 0.000),
  but it does mean the honest claim is narrower than "verified sub-routine dispatch does not help".
- The missing piece is an **activation policy**: our design had *capability* (may) and *receipt* (what
  happened) but no *when/who selects*. Channel E used the weakest possible mode — model-optional. A
  host-auto or mandatory-preflight mode was never tested.
4. **Small-N honesty**: the one-sided 95% upper bound (+12.6 pp) does not exclude a small real
   advantage; power for ≥15 pp at the observed discordance was 0.63. What N=32 does settle, under the
   pre-registered kill rule, is that the claimed ≥15 pp mechanism effect is absent.

What survives (earned, and standing on its own evidence): the enforced-sovereignty sandbox, the
external-oracle verification gates, the tamper-evident append-only record, and the paired-task
instrument itself (task builder + K-turn harness + pre-registration discipline, three smoke-caught
defect classes documented).
