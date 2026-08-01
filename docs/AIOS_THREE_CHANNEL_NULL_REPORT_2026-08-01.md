# Accumulated Experience Does Not Compound on a Frozen Agent: a Pre-Registered Three-Transport Null

**Status: internal consolidated report (2026-08-01), publication-ready draft. External posting
requires a separate founder decision (outward-facing send).**

## TL;DR

We asked one question three ways and pre-registered each attempt before running it: *can an
OS-level substrate around a FROZEN local model make accumulated, externally-verified experience
compound into better first-attempt task performance?* Experience can physically reach behavior
through exactly three transports — **θ** (write it into the weights), **X** (inject it into the
context), **E** (let it mutate the runtime/action surface). All three returned well-instrumented
nulls under external deterministic oracles:

| transport | mechanism tested | headline result |
|---|---|---|
| **θ — weights** | LoRA SFT on own verified trajectories (Qwen3-1.7B student) | single seed n=300: +14 pp, p=1.1e-5 → **5 seeds: +2.9 pp ± 8.1, 1/5 significant — seed-dominated null** |
| **X — context** | ExpeL-style case/insight retrieval; then a persistent experience+skill substrate (K=1 episodes) | +12–13 pp @N=90 (p≈0.01) → **N=300: −6.0 / −0.3 pp, n.s.** (small-N mirage); pilot: **n01 = 0 across 23 pairs** with a median 61,688 chars injected |
| **E — runtime/control-flow** | verified sub-routine dispatch + stack-trace AST-closure masking, K=5 turn loop (qwen3-coder-next student) | **C_overall = 0.000** (P_auto 0.375 both arms, b=c=3, McNemar p=0.656, N=32 pairs, 0 infra/void/tamper) |

Under the pre-registered kill rule and the binding Mortuary Clause (frozen before any E cell ran),
**the "compound in the OS" thesis is falsified at this scale**. We publish the null instead of
relitigating it.

## 1. The claim, stated so it could lose

The program's thesis (after five earlier weight-space nulls forced a pivot) was: *intelligence can
compound OUTSIDE the model* — in verified skills, an experience graph, and a drive layer — with the
model ephemeral and frozen. This is the load-bearing assumption of a large fraction of the current
agent-OS ecosystem (memory layers, skill libraries, experience replay, self-improvement loops on
frozen models). We could find no pre-registered adversarially-designed test of it, so we built one.

## 2. Method spine (shared across all three channels)

- **Tasks**: reconstructed from a private repository's own git history (guaranteed absent from any
  model's training data — removes the benchmark-contamination confound; genuinely recurring
  structure, which is the precondition for compounding). Revert one source file to its parent-commit
  state, keep the post-commit test file; task = make the tests pass.
- **Oracle**: the repo's own pre-existing pytest file, executed OUTSIDE the agent's sandbox, after
  the episode; test files read-only (any diff under `tests/` ⇒ scored fail); an all-skip run is not
  a pass. Oracle commands frozen and hashed at task construction.
- **Frozen students, escalation structurally OFF** — a win cannot come from a stronger model.
- **Paired design**, McNemar exact one-sided on discordant pairs, α = 0.05; infra failures recorded
  separately and dropped, never counted as losses.
- **Pre-registration discipline**: every experiment frozen before any arm ran; amendments only in
  append-only errata; substrate calibrated FIRST (student selected by a pre-registered band rule,
  P_auto ∈ [0.20, 0.60]); run-validity gates so an inert mechanism yields VOID, not a fake null;
  kill rules written before data.

## 3. Channel θ — weights (dead)

LoRA SFT (`experiments/distiller/`, student Qwen/Qwen3-1.7B) on the agent's own externally-verified
solution trajectories; paired eval on n=300 held-out tasks. The single-seed result was seductive:
+14 pp, n01=69 vs n10=27, p = 1.1e-5. The five-seed replication destroyed it: deltas
−4.3 / **+18.0** / +2.7 / −4.3 / +2.3 pp (mean +2.9, population σ 8.1; only seed 2 significant).
The training signal is real enough to move a run but is dominated by seed variance — a
distribution over outcomes centered near zero, not a learning effect. Evidence:
`experiments/distiller/data/confirmatory/multiseed/multiseed_results.json`.

## 4. Channel X — context (dead)

Two independent instruments:

1. **ExpeL-style case retrieval** (270 stored cases): +12.2/+13.3 pp at N=90 (p ≈ 0.017/0.011) —
   then **−6.0/−0.3 pp at N=300** (p ≈ 0.99/0.60). The significant small-N result was a mirage;
   a substrate-swap probe showed +3.3 pp n.s. Evidence:
   `experiments/distiller/data/confirmatory/expel_probe_report{,_n300}.json`.
2. **Phase-5 pilot** (`experiments/phase5/`, prereg `docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md`):
   persistent experience graph + sandbox-gated skill registry injected into the prompt across 24
   sequential tasks (K=1 episodes, student qwen3-coder-next selected by the calibration band rule).
   Injection demonstrably fired (median 61,688 chars). Result: **n01 = 0** — the substrate did not
   flip a single task in 23 analysed pairs (C_overall −4.3 pp, p = 1.0). Evidence:
   `experiments/phase5/PILOT_RESULTS.md`.

## 5. Channel E — runtime/control-flow (dead; the last shot)

Prereg `docs/AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md`, frozen with a **Mortuary Clause**: ONE
unified E-architecture is named; when evaluated, every unselected E-mechanism dies with it —
sequential testing inside E is structural p-hacking, and inventing a fourth transport is
unfalsifiable goalpost-moving.

Architecture: **verified sub-routine dispatch** (sandbox+unit-test-gated skills exposed as opaque
callable primitives — never as prompt text; X is dead and was not retested) + **stack-trace
AST-closure masking** (edit/inspect surface restricted to the k=2 import-scoped call-graph closure
of the failing test's trace; 3–12 files of ~350; true fix inside the closure on 84.4% of tasks).
Both arms got the identical K=5 turn interface; the grading oracle was structurally unrunnable
in-episode (33 blocked attempts recorded across arms).

Result (N=32 paired tasks, 64/64 cells, 0 infra-dropped, 0 voided, 0 tampering):
**P_auto 0.375 in BOTH arms; C_overall = 0.000; b = c = 3; McNemar p = 0.656; per-epoch slope
0.025 (noise).** Run-validity gate passed (32/32 non-trivial closures). Kill-rule condition 1
(`C ≤ 0`) fired. Evidence: `experiments/phase5e/CHANNEL_E_RESULTS.md`,
`experiments/phase5e/channel_e_results.jsonl`.

Adversarial post-checks before recording the verdict: discordance 18.75% (the instrument could
move outcomes — not a frozen dial); the mask-miss artifact is ruled out (4/5 mask-miss tasks failed
in both arms; charitably flipping the single asymmetric pair yields only C ≈ +3.1 pp, p = 0.34);
mechanism exposure reported precisely — dispatch was offered on every task (4 skills
gate-registered during the run, 8 rejected) and invoked **0 times in 32 episodes**; the mask
physically blocked **0** tool calls (guidance-only). The null attributes to *offered-but-unused
dispatch + guidance-only masking*, evaluated jointly per the frozen clause.

## 6. Cross-cutting diagnostics (why the OS could not compound a frozen student)

- **Scaffolding friction actively harms weak frozen agents**: doom-loop rate rose monotonically
  with scaffold weight — raw 4% → checklist 29% → memory 42% → full AIOS gate 75%
  (DriftBench Stage-1, `docs/AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md` §7).
- **The fashionable topological pathology is absent in real data**: two gates on real agent memory
  found no cohomological obstruction to repair — 0/1438 relative-measurement structures, and an
  agent-induced signed graph (74 nodes, 8 independent cycles) fully balanced, **H¹ = 0
  non-vacuously** (`docs/AIOS_AGENT_INDUCED_H1_RESULTS.md`).
- **Frozen models do not reach for offered tools**: skills passed a real verification gate yet were
  never invoked. The bottleneck is model-side (world-model / tool-use disposition), not
  harness-side (type safety, retrieval, masking precision).

## 7. Honest limits

- N=32 (E) has a one-sided 95% upper bound of +12.6 pp: **small** positive effects are not
  excluded; the pre-registered ≥15 pp mechanism-scale effect is. Power at the observed discordance
  was 0.63 for 15 pp.
- One private repository, one task family (test-repair), local frozen students (1.7B trained;
  ~30B-class and larger evaluated; the E student is the largest local coder we run). Frontier-scale
  students were structurally excluded by design (escalation OFF isolates the substrate effect).
- The E-substrate acted through guidance + tool constraint, not total information hiding (`run`
  executes in the full workspace in both arms — recorded before launch).
- These nulls do NOT adjudicate: provider-scale models under the same substrates, non-frozen
  (continually trained) students, or claims other than compounding (safety, reproducibility,
  sovereignty — see §8).

## 8. What survives (earned on its own evidence) and the re-scope

The program's durable products are exactly the things that made the null trustworthy:

1. **Enforced sovereignty**: kernel-level sandbox (Landlock/bwrap, fail-closed, no-network
   default), privacy directories invisible to executed code.
2. **External verification gates**: sandbox+unit-test skill registration (8/12 honest rejections),
   external deterministic oracles, tamper guards that caught zero violations because they made
   violations structurally unrewarding.
3. **A tamper-evident append-only record**: pre-registrations with frozen errata, Merkle-rooted
   registries, receipts, an agent ledger.
4. **The instrument itself**: private-repo paired-task builder + K-turn harness + calibration-first
   discipline (three defect classes caught by holdout smoke before any main cell — protocol
   literalism, inert masking, serving-layer misconfiguration).

**Re-scope (founder GO, 2026-08-01): AIOS is an enforced-sovereignty, externally-verified execution
substrate with a tamper-evident record — infrastructure that VERIFIES and CONSTRAINS intelligence
rather than manufacturing it.** The intelligence gap the nulls located (causal world model,
tool-use disposition, intrinsic drive) lives in the model layer, and claims there must earn their
own pre-registered evidence.

## Receipts

| artifact | path / commit |
|---|---|
| θ multiseed | `experiments/distiller/data/confirmatory/multiseed/multiseed_results.json` |
| X ExpeL probes | `experiments/distiller/data/confirmatory/expel_probe_report{,_n300}.json` |
| X pilot | `experiments/phase5/PILOT_RESULTS.md` (commit `89a190f`) |
| E prereg (frozen) | `docs/AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md` (commit `e9f0f51`, errata through `a971c0c`) |
| E results + verdict | `experiments/phase5e/CHANNEL_E_RESULTS.md` (commit `3105b4a`) |
| stopping rule provenance | operator-led gemini-3.1-pro dialogue, commit `614970a` |
| serving-infra note | ollama GPU-pin revert, ledger 2026-07-28 01:45 KST (commit `52cf236`) |
