# Phase 5 PILOT results — arms run (generated 2026-07-26T16:57:23+00:00, driver `run_arms.py`)

**THE PILOT IS PRE-DECLARED UNDERPOWERED AND IS NOT A VERDICT ON H1** (prereg §5: N=24 can only detect a ≈≥25 pp effect). Its registered purposes are (a) end-to-end harness validation, (b) confirming the retrieval injection actually fires, (c) a variance estimate to size the confirmatory run. Only the confirmatory run settles H1.

Protocol: `docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md` (frozen). Student FROZEN in both arms: `qwen3-coder-next` (§4 rule: calibration P_auto 0.375 ∈ [0.20, 0.60], 8/8 scored, 0 infra). Escalation OFF. Raw per-task records: `pilot_results.jsonl`.

## Run-validity gate (§3)

**PASSED** — treatment injection non-empty on 18 task(s) after E1 (the arms genuinely differed; the mechanism under test was active).

## Headline numbers (paired tasks only, infra-dropped excluded)

- paired tasks analysed: **23** of 24 (infra-dropped: 1, §6.6)
- P_auto control: **0.2174** · P_auto treatment: **0.1739** · C_overall = **-0.0435**
- discordant pairs: b (T-only pass) = **0**, c (C-only pass) = **1**
- McNemar exact one-sided p (H1: treatment > control, α=0.05): **1.0**

## Per-epoch compounding statistic (§1)

| epoch | pairs | P_auto(C) | P_auto(T) | C_k |
|---|---|---|---|---|
| E1 | 5 | 0.6 | 0.4 | -0.2 |
| E2 | 6 | 0.1667 | 0.1667 | 0.0 |
| E3 | 6 | 0.1667 | 0.1667 | 0.0 |
| E4 | 6 | 0.0 | 0.0 | 0.0 |

OLS slope of C_k over epochs: **0.06** (H1 requires C_k > 0 overall AND positive slope; a level difference alone is a one-off prompt advantage, not compounding).

## Guards (§6)

- tests/ tampering incidents (scored FAIL, §6.1): none
- infra-dropped tasks (§6.6): [{"task_id": "p5-001-8ae428b3", "epoch": 1, "control_infra": "ollama call failed: TimeoutError: timed out", "treatment_infra": null}]
- skill induction (§6.2 diagnostics only; P_auto is unaffected by skill count): 4 attempts, 3 registered, 1 rejected by the sandbox+unit-test gate
  - registered: [{"task_id": "p5-003-0d1a189f", "verdict": "registered", "id": "skill-cbb2a72c6199318d"}, {"task_id": "p5-007-87afc6f1", "verdict": "registered", "id": "skill-623bd9890c24754f"}, {"task_id": "p5-015-e2bd3444", "verdict": "registered", "id": "skill-8c6a92ca6c14f085"}]
- treatment injection sizes (chars): [{"task_id": "p5-001-8ae428b3", "injected_chars": 0}, {"task_id": "p5-002-a6785e7f", "injected_chars": 218}, {"task_id": "p5-003-0d1a189f", "injected_chars": 339}, {"task_id": "p5-004-badd98c2", "injected_chars": 12102}, {"task_id": "p5-005-2f94aa2e", "injected_chars": 12083}, {"task_id": "p5-007-87afc6f1", "injected_chars": 12083}, {"task_id": "p5-008-af31841e", "injected_chars": 61647}, {"task_id": "p5-009-eea69885", "injected_chars": 61682}, {"task_id": "p5-010-0d5a12b5", "injected_chars": 61688}, {"task_id": "p5-012-e4825c5b", "injected_chars": 61674}, {"task_id": "p5-013-fd6d0aab", "injected_chars": 61646}, {"task_id": "p5-014-72ddf784", "injected_chars": 61645}, {"task_id": "p5-015-e2bd3444", "injected_chars": 61659}, {"task_id": "p5-016-a5f20467", "injected_chars": 70515}, {"task_id": "p5-018-d20a71c3", "injected_chars": 70518}, {"task_id": "p5-019-b5e92f7a", "injected_chars": 70506}, {"task_id": "p5-020-6ee07972", "injected_chars": 70508}, {"task_id": "p5-021-fb704b5c", "injected_chars": 70520}, {"task_id": "p5-023-9ae0fdd1", "injected_chars": 70528}, {"task_id": "p5-024-ba17518d", "injected_chars": 70546}, {"task_id": "p5-025-09b5c312", "injected_chars": 70546}, {"task_id": "p5-026-35358b51", "injected_chars": 70550}, {"task_id": "p5-027-eabf59c3", "injected_chars": 70544}, {"task_id": "p5-029-86f8b0d9", "injected_chars": 70538}]

## Confirmatory-run sizing (§5, from the observed discordant rate)

- observed discordant-pair rate: **0.0435** · observed net advantage: **-0.0435**
- pairs for 80% power at the OBSERVED delta (one-sided α=0.05, Connor 1987): **None** (not estimable — observed delta ≤ 0; use the grid below)

| detectable advantage | assumed discordant rate | pairs needed |
|---|---|---|
| 0.05 | 0.05 | 122 |
| 0.10 | 0.1 | 60 |
| 0.15 | 0.15 | 40 |
| 0.20 | 0.2 | 29 |
| 0.25 | 0.25 | 23 |

(Assumed discordant rate = max(observed, delta) — a delta cannot exceed the discordant rate. The prereg expects the confirmatory N in the 100–300 range, requiring commits mined deeper than the last 400.)

## Interpretation boundary (§7, written before the data)

- C>0 + positive slope + significant → first earned evidence of OS-level compounding → Scaffolding-Swap falsification next.
- C>0, flat slope → one-off prompt-context advantage, NOT compounding.
- C≈0 → organs do not improve first-attempt autonomous resolution at this scale (honest negative).
- C<0 → substrate actively hurts (retrieval pollution) → credit-assignment/pruning diagnosis.
- Pre-registered prior: 20% compounds / 80% well-instrumented null.

**Restated: this pilot is underpowered by design and NONE of the above may be claimed from it as a verdict on H1 — the confirmatory run decides.**

---

# Operator section (claude@myworld, 2026-07-27) — independent verification, reading, and decision

## Independent recomputation
I recomputed the paired analysis from `pilot_results.jsonl` myself, without the driver: paired N=23
(1 infra drop: `p5-001`, control-arm ollama timeout), control 5/23 = **0.2174**, treatment 4/23 =
**0.1739**, **C_overall = −4.3 pp**, n01 = **0**, n10 = **1**, exact one-sided **p = 1.000**, per-epoch
C_k = **−20 / 0 / 0 / 0 pp**. **The driver's numbers reproduce exactly.** Injection: 23/23 non-empty,
**median 61,688 chars**, max 70,550.

## What this settles, and what it does not
- **Does NOT settle** a small X-channel effect (≈±5 pp). N=23 cannot exclude it — exactly as pre-declared.
- **DOES settle, descriptively: `n01 = 0`.** Across 23 paired tasks, with ~62k characters of verified
  prior experience injected on *every* treatment task, the substrate **never once** turned a control
  failure into a pass. Not rarely — zero. The one discordant pair points the other way.
- **The discordance rate is itself the finding.** 1/23 = 4.3 % means the substrate is nearly **inert on
  outcomes** while being enormous in the prompt. Extrapolating the driver's own sizing table from the
  observed rate, confirming a small effect needs **N in the hundreds of tasks** (~1,000+ cells at
  5–25 min each) — weeks of compute to confirm a transport that produced zero rescues.

## Decision (recorded, not taken silently)
Under the channel taxonomy adopted from the operator-led gemini-3.1-pro-high dialogue — θ (weights) DEAD
by five nulls; **X (context/prompt)**; E (runtime/control-flow) UNTESTED — **this pilot is the X
transport**, and X now carries two independent negatives: the earlier case-retrieval result (+13 pp at
N=90 → ~0 at N=300) and this pilot with n01 = 0.

**Decision: do NOT spend the confirmatory budget on X.** Declare the **X transport dead** on the
accumulated evidence and spend the program's single remaining shot on the pre-registered **Channel-E**
trial, under the Mortuary Clause.

**Cost of this decision, stated because it cuts against me:** stopping X at pilot scale leaves a small X
effect formally unexcluded. I accept that explicitly rather than bury it. The justification is n01 = 0
plus a 4.3 % discordance rate, against weeks of compute on a mechanism that delivered 62k characters per
task to no measurable effect.

## The instrument finding (why this is not merely a null)
The same dialogue produced a diagnosis of *this benchmark*: a D=1, single-episode, whole-file-regeneration
interface gives an OS runtime **zero execution steps in which to intervene**, so it is structurally
incapable of exhibiting Channel-E compounding even if it exists. The E trial therefore changes ONLY the
execution interface (K-turn loop) — same repo, same commits, same oracles, K fixed globally in advance,
zero intermediate oracle leakage — so that "the old shape could not show it" cannot become an
unfalsifiable instrument. E4's 0.00/0.00 is consistent with that diagnosis.

**Net:** the organism's *verified* results remain what they were (enforced sovereignty, external
verification, tamper-evident record, sandbox-gated skills). Its *compounding* claim has now failed in two
of three physical transports, and gets exactly one more shot.
