# AIOS Methodology Divergence — beyond small-N SFT distillation (2026-07-22)

**Origin**: founder directive "Methodology 발산", triggered at the moment the distillation keystone
wobbled (multiseed: three near-identical LoRA draws on the same 270 verified trajectories → +14.0 /
+1.4 / **−4.3**pp held-out, 18pp spread ⇒ the "+14pp positive" is a lucky high draw, not signal).
Divergence was run through **heterogeneous substrates** (not my own converged head): a fresh 2026
frontier scan + **Gemini** + **Codex** (web-grounded, 22 methods w/ cited papers). DeepSeek failed;
NIM/codex CLIs needed invocation fixes. Synthesis is mine.

## The convergent diagnosis (three independent angles → one conclusion)

The genuinely heterogeneous sources gave **complementary** failure-mechanism diagnoses that all point
the same way:

- **Frontier-scan (mine)**: the 2026 field has moved from gradient fine-tuning to **evolving the
  SYSTEM** (prompts/memory/tools/architecture) — EvoTest (2510.13220), Self-Evolving Agents survey
  (2507.21046). Weight-SFT distillation is the minority bet, swimming upstream ⇒ *method↔scale mismatch*.
- **Gemini**: *substrate parameter capacity* — a 1.7B model cannot be a general instruction-follower
  AND absorb 270 high-density causal trajectories via SFT without weight cross-talk; the 18pp variance
  is the symptom of it dropping primary capability into high-curvature local minima.
- **Codex**: *the learnable signal is in the causal control PROCESS, not the transcript tokens* — SFT
  on 270 examples tries to compress verifier-conditioned search + tool use + retrieval + retries +
  environment feedback into next-token imitation. **"The thing that learned in successful provider
  trajectories was the LOOP + VERIFIER, not the LLM's weights."**

**⇒ Earned pivot** (3 heterogeneous sources + literature + our own pre-registered multiseed data —
not a single head's convergence): **stop compressing the loop into weights; COMPOUND in system-space
— memory, skills, search, evolution — where the actual signal lives.** This is *also* more sovereign
(it evolves around ANY model, so it survives provider death) and does not need the fragile small-N
gradient. Caveat (per the panel-ceiling discipline): convergence is a *weak* signal on its own; here
it is corroborated by the multiseed negative and by complementary (not identical) mechanisms, and each
top bet ships with an executable falsification test — trust is earned by the test, not the consensus.

## The divergence space (22 methods, grouped; cheapest test + anti-reward-hack guard each)

Full per-method tests/guards in the substrate transcripts. Grouped:

1. **Non-weight verified memory** — Voyager skill library (2305.16291), ExpeL / case-based reasoning
   (2308.10144, 2504.06943), growing ontology/graph reasoning. *Store each verified episode as a
   reusable ARTIFACT (skill/case/rule), retrieved at inference — not a "gradient whisper."*
2. **Evolutionary / genetic** — GEPA prompt/policy evolution (2507.19457), AlphaEvolve (2506.13131),
   ShinkaEvolve island model (2509.19349), gene-pool + speciation + recessive-trait resurrection,
   evolutionary model-merging / AC-DC / MERGE3 / TIES-DARE-SLERP (2403.13187). *Turn the 18pp variance
   into search material (populations) instead of averaging it away.*
3. **Inference-time compute** — AB-MCTS tree search (2503.04412), best-of-N + **weak-verifier
   ensemble (Weaver 2506.18203 — already absorbed, `scripts/aios_verifier.py`)**, debate /
   adversarial self-consistency. *Buy capability with GPU search budget, not weight updates.*
4. **Online / streaming RL** (OaK/Sutton) — verifier-driven GRPO / GiGPO (2505.10978), test-time RL.
   *Optimizes action success directly; heavier compute (honest: DeepSWE = 64×H100; our budget limits
   this to narrow/test-time variants).*
5. **World-models / diffusion / active inference** — ADWM off-policy evaluator (2606.05558), Diffusion
   Policy, Dreamer (Nature 2025), active-inference controller (2412.10425). *Amplify scarce verified
   experience via a local simulator; final authority stays external.*
6. **Neurosymbolic / tool synthesis** — program synthesis over a small AIOS task DSL, ToolMaker
   self-synthesized tools (2502.11705). *Move intelligence into verifiable programs a 1.7B can call.*
7. **MoE routing by focal diversity; curriculum/self-play w/ external verification; harmonic/
   oscillatory phase controllers; developmental "baby" learning.** *(founder's named methods land here.)*

## Convergent Top-3 (both heterogeneous panels independently ranked these)

1. **Non-weight verified skill/case/ontology memory** — cheapest, most sovereign, most audit-friendly;
   directly attacks small-N variance by making each verified episode reusable. **Cheapest decisive
   test (reuses data we already have, ZERO training, ZERO variance): index our 270 verified
   trajectories as a case base → retrieve top-k into qwen3-1.7b → eval held-out zero-shot vs
   no-retrieval vs the SFT arms.** Guard: cases carry verifier outcome + failure reason; retrieval
   must not expose held-out solutions.
2. **Evolutionary program/prompt/tool search** (islands + Pareto + gene-pool) — matches our
   external-verifier setup and the founder's named methods; improves the *actual AIOS loop* (routing,
   tools, prompts, repair, scaffolds), not tiny-model logits. Guard: task set + verifier frozen before
   evolution; optimizer mutates only artifacts, never tests.
3. **Inference-time search + weak-verifier ensemble** — **fastest decisive upside; we already have
   both parts** (`aios_escalate.py` AB-MCTS + `aios_verifier.py` Weaver). Plot pass-rate per GPU-hour
   at node budgets {1,8,32,128}. Guard: terminal reward only from the external verifier.

## Anti-reward-hacking invariant (binds every bet)

Three-way separation, always: **generator proposes · external/locked verifier validates · a scorer
evaluates hidden held-out tasks.** No bet may generate its own tasks AND write its own verifier AND
score itself (the founder's core AGI constraint). Frozen task manifests + independent verifier
ownership + result-packet receipts.

## Decision + first move

**Pivot the compounding-loop keystone from weight-distillation to system-space compounding.** Order,
cheapest-decisive-first:
1. **ExpeL/case-retrieval probe** (bet #1) — reuses the 270 trajectories, no training, no GPU-train,
   no variance. If retrieval ≥ SFT arms, "compound in memory not weights" is earned cheaply. *First.*
2. **Inference-time search + Weaver** (bet #3) — parts already built; wire escalate's local generator
   to qwen3-1.7b + Weaver score_fn, sweep node budget. *Second (reuses absorbed organs).*
3. **Island/gene-pool evolutionary search** (bet #2) — the founder's methods; larger build.

multiseed continues to nail the distillation distribution (confirmatory of the negative). The
qwen3-coder-next upgrade (top-vision) gives a *bigger* local substrate — worth re-testing whether SFT's
capacity problem eases there, but the pivot does not depend on it.

## Sources (2026, codex-grounded + frontier scan)
GEPA 2507.19457 · AlphaEvolve 2506.13131 · ShinkaEvolve 2509.19349 · Evo-merge 2403.13187 · Voyager
2305.16291 · ExpeL 2308.10144 · CBR agents 2504.06943 · AB-MCTS 2503.04412 · Weaver 2506.18203 · GiGPO
2505.10978 · ADWM 2606.05558 · ToolMaker 2502.11705 · active-inference 2412.10425 · EvoTest 2510.13220 ·
Self-Evolving survey 2507.21046 · RSI survey 2607.07663. Related: [[project_agi_build_arc_2026_07]],
[[project_provider_independence_two_horizons]], [[project_hivemind_verifier_settled]].
