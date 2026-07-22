# System-space pivot — first tests: a well-powered DOUBLE NULL (2026-07-22)

**One line (no-launder, correcting my own same-day claim)**: at proper power (N_B=300), BOTH
weight-distillation AND non-weight case-retrieval are NULL on qwen3-1.7b for this task family. The
ExpeL "+12–13pp significant" I reported at N_B=90 was underpowered noise — it **evaporated at N_B=300**
(k2 −6.0pp, k3 −0.3pp, both ns), exactly the trap that overturned the distillation "+14pp" earlier the
same day. Two promising small-N positives, two confirmatory NULLs, in one session. The confirmatory
discipline earned its keep twice.

## The numbers

**ExpeL case-retrieval (bet #1), N_B=90 → N_B=300:**
| arm | N_B=90 | N_B=300 (confirmatory) |
|---|---|---|
| base | 0.211 | 0.307 |
| bm25 k=2 | 0.333 (+12.2pp, p=0.017 ✅) | 0.247 (**−6.0pp, p=0.99 ❌**) |
| bm25 k=3 | 0.344 (+13.3pp, p=0.011 ✅) | 0.303 (**−0.3pp, p=0.60 ❌**) |

At N=300 (well-powered to detect ~10pp) the effect is genuinely ~0, not merely undetectable. The base
also swung 0.211→0.307 across the two subsets — small-N eval variance was doing the talking at N=90.
(The relevance-control run — bm25 vs random retrieval — was made moot: there is no effect to attribute.)

**Weight-distillation (multiseed, 5 seeds, N_B=300 each):**
deltas = −4.3 / +18.0 / +2.7 / −4.3 / +2.3 pp → **mean +2.9pp, sd 8.1pp, 1/5 significant**. Straddles
zero with huge variance. The earlier "+14pp/+18pp" were the high tail of a variance-dominated process.

## Honest reading (both directions)

- **Not laundered up**: neither method is a reliable positive here. The pivot's first cheap test (ExpeL)
  FAILED to replicate. I over-called it last turn on N=90; this corrects it.
- **Not laundered down into terminus**: a well-powered NULL is information. At N=300 the methods do
  ~nothing on **this specific regime**: `qwen3-1.7b` student × **cross-family transfer-holdout** (A/B
  families DISJOINT) × these B tasks. The null is localized to the regime, not proven universal.

## The recurring meta-lesson (5th time) — it's the TESTBED, not method #6

Arc tally: DriftBench STOP · S+1 no-transfer · S+1.1 · distillation NULL · ExpeL NULL = **five rigorous
attempts, zero replicated positive**, all on the SAME regime (tiny 1.7b substrate + cross-family
transfer-holdout + small-N eval). The recurring wall is **substrate-calibration, not mechanism** (a
lesson this program has hit before). Blindly trying method #6 on a noise/ceiling regime is the trap.

**The null is one of three things — and they're cheaply separable:**
1. **Substrate too weak** — 1.7b lacks capacity for ANY method to move (Gemini's divergence diagnosis).
   Test: re-run base vs ExpeL vs one distillation draw with `--student-model qwen3-coder-next` (the
   provider-grade local model pulled today). If effects appear on a model with headroom → capacity.
2. **Transfer too hard** — cross-family (A→B disjoint) is the killer, not the method (consistent with
   S+1's no-transfer finding). Test: WITHIN-distribution eval (retrieve A-cases for A held-out). If
   retrieval helps within-family but not cross-family → it's a transfer problem, target transfer.
3. **Genuinely no compounding here** — if both above stay null, this task family doesn't compound and
   the testbed must be replaced, not the method.

## Decision

**STOP adding method variants to this regime. Localize the null first** (substrate vs transfer vs
genuine) with the two cheap diagnostics above — both reuse the existing harness (`--student-model`
swap; within-distribution split) and the already-pulled qwen3-coder-next. Only after the null is
localized does the next method (bet #3 inference-time search + Weaver, which needs neither transfer nor
training and extracts latent capability via external verification) get tested — on a testbed where an
effect could actually be seen. Anti-thrash: a 6th null on the same broken testbed teaches nothing new.

Related: [[project_methodology_pivot_system_space]], [[project_provider_independence_two_horizons]]
(the local-substrate upgrade is now on the critical path, not a side quest), [[project_agi_build_arc_2026_07]].
Corrects the optimistic framing in commit `8444f15`.
