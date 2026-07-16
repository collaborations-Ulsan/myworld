# AIOS-DriftBench Stage-1 Results (2026-07-17)

**Status: STOP (Bar A) / FAIL (Bar B).** First real execution of the M2 DriftBench Stage-1
keystone — this experiment had never run before this session. Both pre-registered bars were
computed in FULL (not partial) on the same 120-row result table, and both are negative.
Reported straight, no-launder: this is a genuine, decisive negative, not a defensible null
dressed down and not a loss dressed up.

Governance: this run and its verdicts are computed exactly per the composed-judgment decision
in `docs/AIOS_DRIFTBENCH_RECONCILIATION_2026-07-11.md` —
`scripts/m2_driftbench/` (ASC-0282 WP-B) is the execution substrate; result rows conform to
the hash-frozen `experiments/driftbench/schema.py`; verdicts are computed ONLY by the
hash-frozen `experiments/driftbench/analyze.py`. **Bar A**
(`docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md` v1.1, FROZEN) is the sole judge of the AIOS
"Epistemic Runtime" redefinition keystone. **Bar B** (ASC-0282's own internal 17/24,
tie≠win bar) is valid only as that contract's internal completion judge. No frozen document
body was edited; the prereg-A Errata below is an append per its own §6 procedure.

---

## 1. WP-A reality check (pre-run gap audit)

The ledger entry 2026-07-11T10:25 listed three open WP-A gaps at ASC-0282 acceptance time:
"aios_head.py thread-through, per-organ disable flags in `_gate_organs`, provenance-guard
organ (net-new)". Verified against live code + tests before freezing:

1. **aios_head.py thread-through — DONE.** `_resolve_epistemic_gate` (`scripts/aios_head.py:1296`)
   builds the gate from `--gate {off,llm-judge,organs}` / `--gate-disable` CLI flags (or the env
   equivalents) and is wired into both `run_loop_goal` and `run_organic_goal` call sites
   (`scripts/aios_head.py:1421,1431`). Behavior-preservation verified: with neither flag nor env
   set it returns `None`, identical to pre-gate behavior.
2. **Per-organ disable flags in `_gate_organs` — DONE** (commit `94ac3cb`, "WP-A (ASC-0282):
   per-organ disable switches for the ablation-replay gate"). `EpistemicGate(disabled_organs=...)`
   / env `AIOS_GATE_DISABLE_ORGANS`; an unknown organ name fails fast (fail-closed by design);
   `tests/test_aios_head_loop.py::EpistemicGateFlagTests` + `DisabledOrganTests` pass (2/2).
3. **Provenance-guard organ — NOT a genuine gap.** `_provenance_check`
   (`scripts/aios_epistemic_gate.py:252-258`) is an intentional, documented STUB: it always
   returns `status="not_implemented"` when enabled, with an explicit in-code note that the real
   check is a later work packet. It is inert by design (never counted as checked, never an
   infra failure, never blocks — confirmed by reading `_gate_organs`), so it has zero effect on
   Stage-1 gate behavior. Left alone: implementing a real provenance check is new design scope,
   not "closing a gap," and would violate smallest-viable-change for this task.

**One genuine blocking bug found and fixed** while running the mandated smoke suite (task step
1's verification): `scripts/m2_driftbench/run_stage1.py:370` called a nonexistent
`_instance_answerability_probe(instance, env_base)`. The correct call —
`agent_arm.answerability_probe(instance, env)` — already existed in `agent_arm.py` and is
exactly what `tests/test_m2_driftbench_smoke.py` already asserted against. Before the fix,
`test_eval_runner_end_to_end_scripted_row_and_causal` failed with `NameError` — meaning **every**
real `--eval` run would have crashed on its first arm-instance. One-line fix; the freeze (§2)
happened *after* this fix, so the sealed harness is the corrected version.

Test results (post-fix):
- `tests/test_m2_driftbench_smoke.py`: 28/28 pass (27/28 before the fix)
- `tests/test_aios_head_loop.py -k "EpistemicGateFlagTests or DisabledOrganTests"`: 2/2 pass
- `tests/test_aios_head_loop.py` (full): 7/7 pass

---

## 2. Freeze record

- Seal: `descentnet/run_artifacts/descentnet/m2_freeze_seal.json` (`m2.freeze_seal.v2`)
- `combined_sha256`: `583f2f77ce6bbd25ee6bacab727eacd0e986a5eb5ca17a5d20742ab22bf531d7`
- 16 sealed files (8 WP-B core modules + 5 WP-B2 modules + 3 sealed-dir JSON descriptors),
  hashed individually in the seal.
- Cross-referenced dual-harness files, both matching the reconciliation-frozen prefixes:
  - `experiments/driftbench/schema.py` sha256 `1ed8fd8b…` — `matches_reconciliation: true`
  - `experiments/driftbench/analyze.py` sha256 `53f4037e…` — `matches_reconciliation: true`
- Eval seeds: `[11, 12, 13]` (frozen, never re-rolled).
- Post-run `freeze.py verify`: `{"ok": true, "drift": []}` — the harness that ran the grid is
  byte-identical to what was sealed; no post-freeze drift.
- Harness commit: pre-session HEAD `8457e40d49d015a909017c270ca996ffb4c9859e`; the answerability
  bugfix above was applied and on-disk *before* sealing, so the seal's file hashes are the
  corrected bytes. This session's commit (hash reported at the end of this doc / the ledger)
  contains exactly those bytes — `combined_sha256` is the load-bearing, commit-independent
  fingerprint.
- Model pins (frozen; `docs/M2_FREEZE_PREP_2026-07-11.md` §1, confirmed live before the run):
  - weak: `qwen3-coder:30b` (ollama, resident) — confirmed present (`ollama list`), MoE
    3.3B-active/256K-ctx, warm-load call latency ≈0.3-0.6s/call once resident.
  - strong primary: `deepseek-ai/deepseek-v4-pro` (NIM) — confirmed reachable
    (`--nim-ping`: `{"ok": true, "reply_chars": 1, "tokens": 6}`), used throughout (fallback
    `nvidia/nemotron-3-ultra-550b-a55b` never exercised — primary stayed healthy).
- NIM key: read at runtime only from `~/.config/nvidia/api.env`; verified NOT present anywhere
  in any receipt, trace, or run log (grepped the key's own prefix against all `m2_*` artifacts
  and the run log — zero matches).
- Env: ollama `0.22.1`, Python `3.13.12`, Linux `6.17.0-35-generic` x86_64, dual RTX 5090 host.
- Eval instance generation: `public_seed = 198041690126787`, derived per the frozen formula
  `int(sha256(seal.combined_sha256)[:12], 16)`. `--validate-instances`: 24 base instances,
  `coverage_rule_ok: true`, `problems: []` (6 mutating templates × 3 seeds = 18 + 2 static
  templates × 3 seeds = 6).

---

## 3. Runtime-estimate gate

Per task step 3, timed 3 pilot (instance, arm) pairs across 2 mutating templates
(`api_migration`, `auth_change`; all 5 arms each) + 1 static template (`url_static`; 2 arms)
*before* committing to the full grid:

| arm | pilot wall-clock |
|---|---|
| weak-raw | 1.8–1.9s |
| weak+checklist | 2.4–2.7s |
| weak+memory | 2.3–2.5s |
| weak+aios | 3.5–3.8s |
| strong-raw (NIM) | 16–22s |

No pilot instance came anywhere close to the 45-min/200-action per-instance cap. Extrapolated
full grid (24 instances × 5 arms = 120 pairs) ≈ 12–20 minutes total. **Decision: run the full
Stage-1 grid, no reduced first tranche** — the estimate was two orders of magnitude under the
4-hour gate.

**Actual**: full grid completed in **≈14 minutes** wall-clock (generation receipt written
2026-07-16T17:35:51Z → rows file written 2026-07-16T17:49:30Z). 120/120 (instance, arm) pairs
completed, `arm_status: "ok"` for all 120 (**zero infra failures, zero restarts**), rows file
validates with **0 schema errors**.

---

## 4. Per-arm summary (24 instances each: 18 mutating + 6 static)

| arm | mutating success | static success | overall success | avg tokens | avg wall_s | avg actions | model_finished | loop_detected |
|---|---|---|---|---|---|---|---|---|
| weak-raw | 0.389 (7/18) | 0.500 (3/6) | 0.417 (10/24) | 2576 | 1.89 | 3.00 | 23 | 1 |
| weak+checklist | 0.611 (11/18) | 0.500 (3/6) | 0.583 (14/24) | 9085 | 3.61 | 5.42 | 17 | 7 |
| weak+memory | 0.278 (5/18) | 0.333 (2/6) | 0.292 (7/24) | 3656 | 3.28 | 3.21 | 14 | 10 |
| weak+AIOS | 0.167 (3/18) | 0.333 (2/6) | 0.208 (5/24) | 6319 | 3.49 | 4.38 | 6 | 18 |
| strong-raw (NIM) | 0.722 (13/18) | 0.500 (3/6) | 0.667 (16/24) | 5271 | 24.87 | 5.17 | 24 | 0 |

Aggregate labels (sum over 24 instances/arm): wrong_actions / stale_actions / unsupported_claims
/ asks / abstains / verification_before_submit-count:

| arm | wrong | stale | unsupported | asks | abstains | verified-before-submit |
|---|---|---|---|---|---|---|
| weak-raw | 8 | 9 | 0 | 0 | 0 | 14/24 |
| weak+checklist | 3 | 1 | 0 | 1 | 0 | 24/24 |
| weak+memory | 3 | 6 | 0 | 0 | 0 | 18/24 |
| weak+AIOS | 1 | 0 | 0 | 0 | 0 | 22/24 |
| strong-raw | 8 | 1 | 0 | 1 | 3 | 24/24 |

---

## 5. Bar A — prereg-A v1.1 §5 (the sole redefinition-keystone verdict)

All 5 required arms ran on all 24 instances — **this is a COMPLETE, not partial, adjudication
of every SS5 condition.** No prereg-A condition is left uncomputed; nothing awaits a further
grid.

- **Condition 1** (paired win, mutating 18): `weak+AIOS` wins **1/18** vs `weak+checklist`
  (need ≥13/18); `weak+checklist` wins 9, ties 8. McNemar one-sided exact p = **0.9990**
  (α=0.05), **not significant** → **FAIL**.
- **Condition 2** (gap-closure + cost): ratio mode, value = **−4.000** (CI [−11.0, 11.0]) —
  `weak+AIOS` sits *below* `weak+checklist`, not between it and `strong-raw`; cost(tokens) diff
  CI upper = **+3201.7** (AIOS strictly *more* expensive per instance, not less) → **FAIL**.
- **Condition 3** (static equivalence guard, 6 static instances): |Δ successes| = 1 (≤1 margin),
  unsupported-claim rate 0.000 both arms (no increase) → **PASS**.
- **Condition 4** (trace causal rule): **0/1** credited win trace-verified. The sole mutating
  instance where `weak+AIOS` succeeded and `weak+checklist` failed
  (`deprecation`, seed-index 0) has **no gate-reject / drift-detected / rollback event anywhere
  in its trace** — it succeeded independent of any gate mechanism, so there is nothing to
  causally attribute → **FAIL**.

**STOP condition explicitly triggered** (analyze.py's own unmodified three-way logic:
condition-1 fails AND McNemar non-significant):

> **VERDICT: STOP**

Per prereg §5: *"weak+AIOS가 동일 예산에서 weak+checklist에 mutating paired 우위를 보이지
못하면 (13/18 미달 그리고 McNemar 비유의) → 'epistemic runtime' 테제를 kill하거나 'workflow
hygiene'으로 강등, 결과를 그대로 공개 (no-launder 양방향)."**

Under the pre-registered rule, this STOP result licenses killing the "epistemic runtime"
framing or demoting it to "workflow hygiene" — see §8 for the mechanism behind this number
before deciding which.

---

## 6. Bar B — ASC-0282 internal completion bar (17/24, tie≠win)

Same rows, full 24-instance comparison (`weak+AIOS` vs `weak+checklist`, mutating + static):
wins_a (`weak+AIOS`) = **1/24** (need ≥17/24); wins_b (`weak+checklist`) = **10/24**; ties =
**13/24**. McNemar one-sided exact p = 0.9995, not significant.

**Result: FAIL.** `weak+checklist` beats `weak+AIOS` on strictly more instances than the
reverse (10 vs 1) — this is not a near-miss, it is `weak+AIOS` losing the head-to-head. ASC-0282's
own internal completion bar is not met.

---

## 7. Secondary metrics (all pre-registered ones computable are reported — no selection)

- **H2 (cost sweep, secondary)**: `analyze.py` reports `dominates=True` at every sweep point
  (wrong_cost ∈ {3,5,10,20}: AIOS cheaper at all four). **Flagged as a labeling artifact, not a
  genuine finding**: `weak+AIOS`'s near-zero `wrong_actions` (1 total across 24 episodes) is not
  because it decides better — 18/24 (75%) of its episodes end via the frozen agent's doom-loop
  circuit breaker (`outcome.exit == "loop_detected"`) *without ever calling `final_action`*, so
  `wrong_actions` is structurally near-zero (an arm that essentially never answers cannot answer
  wrongly). The wrong-action cost model only prices actions actually taken. Do **not** read the
  H2 sweep as evidence for calibration-gated abstention working as intended — it is measuring an
  arm that mostly failed to reach a graded decision at all.
- **H3 (memory-under-mutation, secondary)**: `s_weak_raw = 0.389`, `s_weak+memory = 0.278`
  (< raw → **ProEvolve pattern reproduced = True**, a real, independently-interesting finding),
  `s_weak+AIOS = 0.167` (< raw → **H3 required condition FAILS, `h3_holds = False`**).
  `weak+AIOS`'s staleness-gated memory did not preserve the raw-model baseline under mutation;
  `weak+AIOS` is in fact the *worst*-performing local arm of the four (worse than `weak+memory`,
  which itself is worse than doing nothing).
- **Doom-loop / circuit-breaker rate by arm** (diagnostic — not a pre-registered metric, but
  load-bearing for interpreting §5/§6 honestly): weak-raw 1/24 (4%), weak+checklist 7/24 (29%),
  weak+memory 10/24 (42%), weak+AIOS 18/24 (75%), strong-raw 0/24 (0%). This tracks monotonically
  with "how much scaffold friction is added to the frozen weak local agent" — it is not specific
  to the epistemic-gate *concept*: even a bare-text checklist trips the loop-detector far more
  than no scaffold at all, and injected memory trips it nearly as often as the full gate. This is
  the dominant mechanism behind the STOP result: `weak+AIOS` mostly never reaches a scored final
  action, rather than reaching one and answering wrong.
- Gate mechanics: 9/24 `weak+AIOS` episodes recorded ≥1 organ rejection in `gate_blocks`
  (observed reasons: `apex_contradictory`, `descent_h0_conflict`) — i.e. the gate frequently
  *did* detect the genuine ledger conflicts the mutating templates are designed to create; the
  failure is downstream, in the frozen agent's inability to productively resample after a
  rejection often enough to reach a committed, correct action before the loop-detector fires.

---

## 8. Honest limitations

- **N=1 run.** No repeated-trial variance estimate beyond the pre-registered bootstrap CIs
  already reported in §5/§6.
- **The frozen agent's circuit breaker dominates the outcome distribution for every scaffolded
  arm**, most severely `weak+AIOS` (75% loop-detected). This is a property of the shared frozen
  sampler/loop implementation (`scripts/m2_driftbench/agent_arm.py`), which Stage-1 was not
  designed to vary. It means this run cannot fully separate two different STOP-consistent
  stories — "the epistemic gate makes bad calls" vs. "the weak local model cannot cope with
  *any* rewrite-and-retry pressure, gate or otherwise" — though either story still nets a STOP.
  A future diagnostic that reports "did the episode ever reach a graded final action" as its own
  first-class row would separate these; this run did not pre-register that split, so it is
  reported here only as interpretive context, not as a formal condition.
  Read together with the per-arm doom-loop gradient above, the second story (frozen-agent
  resampling fragility under ANY scaffold pressure) looks like the better-supported one — but
  this is an interpretive judgment, not a pre-registered test, and is flagged as such.
- **Corrupted-oracle variant instances** (24 more, one false fact injected at t=0) were
  generated by `fixtures.generate_eval_instances` (available in the generation receipt) but were
  **not run** — `run_stage1.py --eval` defaults to `--variant base`, and the corrupted arm is
  outside prereg-A's SS5 scope. Available for a future targeted probe; not part of either bar
  here.
- **Instruments not run**: `weak+llm-judge` and the `slm-delta` score are computed per-receipt
  (`slm_delta` field, side-table only) but were not analyzed here since neither is part of any
  SS5 condition.
- **No ambiguity requiring a re-run to resolve this bar.** The result is decisive on both bars
  (STOP / FAIL) and on H3 (fails). A re-run would be warranted only to test a *different*
  question (e.g., whether the doom-loop rate is itself addressable), not to re-adjudicate
  Stage-1's verdict.

---

## 9. Raw-data paths (repo: `descentnet`, all under `run_artifacts/descentnet/`)

- Freeze seal: `m2_freeze_seal.json`
- Generation receipt: `m2_eval_generation.json` (public seed, instance hashes, drift-type
  coverage)
- Result rows (schema.py-conformant, analyze.py input): `m2_stage1_rows.jsonl` (120 rows)
- Per-(instance,arm) receipts: `m2_stage1_<template>_<arm>_s<seed>.json` (120 files)
- Full traces: `m2_trace_stage1_<template>_<arm>_s<seed>.jsonl` (120 files)
- Causal traces (condition-4 input): `m2_causal_stage1_<template>_<arm>_s<seed>.jsonl` (120
  files)
- Hidden grader specs (outside all agent-visible/sealed trees): `eval_specs/*.json` (24 files)
- Per-arm memory stores (isolation per prereg §3a): `m2_memory_weak_plus_memory.json`,
  `m2_memory_weak_plus_aios.json`

---

## 10. Errata append

See `docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md` → Errata (append-only) → new 2026-07-17 entry
recording this freeze + first-run pins per §6.
