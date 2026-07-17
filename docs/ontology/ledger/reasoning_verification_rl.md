# Frontier Knowledge Ledger — D5: Reasoning + Verification + RL for agents

**Schema**: `docs/ontology/FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md` §1 (unified). **Data**: `reasoning_verification_rl.json`.
**Status**: draft-first (append; not accepted — DNA #2). **Populated**: 2026-07-17 by claude@myworld.
**Grounding**: own WebSearch + HF `paper_search` + WebFetch this session, plus 3 parallel grounded research agents (reasoning / verification / RL-for-agents) — every node/edge sourced. No answer taken from training memory (freshness gate).
**Format**: CANONICAL flat-entity + `{src_id,rel,dst_id}` edges, identical shape to D6 `learning_methods.json`. **Verified to merge cleanly** (dry-run `experiments/ontology` normalize+merge over all ledger files: my file ingests, 7 shared entities dedup by canonical id — `paper:2505.03335` (Absolute Zero), `paper:2601.15808`, `paper:2604.16004`, `paper:2606.26294`, `person:akarsh_kumar/andrew_zhao/percy_liang` — cross-domain edges into D1/D6 resolve, merged `contradicts` count 47→58). **REUSES shared ids** for cross-domain edges: `paper:2607.07663` (RSI survey), `concept:verification_hierarchy`, `concept:rlvr`, `concept:test_time_compute`, `methodology:verification_hierarchy`, `methodology:rl_rlvr_grpo_with_verifiers`, `method:absolute_zero_self_play_reasoning`, `org:openai/anthropic/google_deepmind/sakana_ai`.
Nodes tagged `grade:hypothesis` are aggregator/secondary or future-dated 2026 arxiv ids surfaced-once (AlphaProof-Nature, `2603.19335`); `grade:primary` are arxiv/venue/first-party read this session.

**Counts**: 269 nodes (105 papers [R 33 / V 32 / RL 40], 45 people, 45 methods, 32 claims, 13 benchmarks, 12 concepts, 7 orgs, 6 labs, 3 methodologies, 1 domain) · 380 edges incl. **11 `contradicts`** (the frontier's live disagreements). **Coverage exceeds the nominal ~30-45 paper bound** because D5 unifies three full methodology families (each ~30-40) — kept rather than truncated per "no silent truncation"; honest gaps below.

---

## 1. The three families (map)

| Family | Scope | Methodology node |
|---|---|---|
| **R — Reasoning scaffolds & test-time compute** | CoT → self-consistency → ToT/GoT; search-augmented (MCTS / **AB-MCTS** / rStar-Math); long-CoT reasoning-model training (o-series / **R1-style RLVR** that induces extended CoT); **test-time compute scaling**; latent/continuous reasoning (Coconut, Soft Thinking, looped-depth) | `methodology:reasoning_test_time` |
| **V — Verification & the verifier hierarchy** | **PRM vs ORM**, verifier-gated generation (best-of-N, GenRM, Weaver), **formal** (Lean: DeepSeek-Prover / Goedel / AlphaProof / Harmonic Aristotle), self- vs external verification, calibration/abstention, **co-evolving (Red-Queen)** verifiers | `methodology:verification_verifier_hierarchy` |
| **RL — RL for reasoning & agents** | RLHF/RLAIF & direct-alignment (DPO/SimPO); **RLVR**; **GRPO/PPO variants** (Dr.GRPO, DAPO, VAPO, GSPO, REINFORCE++); self-play (Absolute Zero, R-Zero, SPIN); **credit assignment** (PURE min-form, VinePPO, TRIAGE); RL-for-tool-use (ReTool, Search-R1); offline/streaming (stream-x); RL-for-self-improvement | `methodology:rl_for_reasoning_agents` |

**Load-bearing anchor (the STOP).** `paper:2607.07663` (Recursive Self-Improvement survey, Chen/Wang/Qu, 8 Jul 2026, https://arxiv.org/abs/2607.07663) orders evaluators into a **verification hierarchy — formal > PRM > rubric > intrinsic** — and finds **demonstrated self-improvement strength TRACKS that hierarchy**. This is why the DriftBench STOP happens: a scaffold with a weak/intrinsic verifier can lose to a plain checklist. All three D5 families ultimately feed this single lever: **verifier strength = scaffold strength.**

---

## 2. Family findings (compressed — full detail + numbers in the JSON claims)

### R — reasoning / test-time compute
- **The scaffold ladder**: CoT ([2201.11903](https://arxiv.org/abs/2201.11903), Wei) → self-consistency ([2203.11171](https://arxiv.org/abs/2203.11171)) → ToT ([2305.10601](https://arxiv.org/abs/2305.10601), Yao — Game-of-24 4%→74%) → GoT ([2308.09687](https://arxiv.org/abs/2308.09687), Besta). Search-augmented: **rStar-Math** ([2501.04519](https://arxiv.org/abs/2501.04519), Microsoft — 7B MATH 90.0%, AIME 53.3% via SLM+MCTS+PRM self-evolve) and **AB-MCTS** ([2503.04412](https://arxiv.org/abs/2503.04412), Sakana — adaptive wider-vs-deeper branching).
- **Reasoning-model training**: **DeepSeek-R1** ([2501.12948](https://arxiv.org/abs/2501.12948)) — pure RLVR induces long CoT + "aha"; **s1** ([2501.19393](https://arxiv.org/abs/2501.19393), Muennighoff/Fei-Fei/Liang) & **LIMO** ([2502.03387](https://arxiv.org/abs/2502.03387)) show ~1k traces suffice; **MRT** ([2503.07572](https://arxiv.org/abs/2503.07572), Kumar) casts test-time compute as meta-RL.
- **Test-time compute scaling**: Snell/Kumar ([2408.03314](https://arxiv.org/abs/2408.03314)) — compute-optimal TTS beats a ~14× larger model; **Large Language Monkeys** ([2407.21787](https://arxiv.org/abs/2407.21787), Brown/Ré/Mirhoseini) — coverage log-linear over 4 orders of magnitude, **but flags the verifier as the bottleneck**; **1B > 405B with the right PRM** ([2502.06703](https://arxiv.org/abs/2502.06703)).
- **Latent reasoning**: Coconut ([2412.06769](https://arxiv.org/abs/2412.06769), Hao/Tian/Weston), Soft Thinking ([2505.15778](https://arxiv.org/abs/2505.15778)), looped-depth LOTUS ([2606.31779](https://arxiv.org/abs/2606.31779)) — matched by skeptics (§3).

### V — verification (LOAD-BEARING)
- **PRM lineage**: Let's Verify Step by Step / **PRM800K** ([2305.20050](https://arxiv.org/abs/2305.20050), Lightman/Cobbe — process 78% MATH), Math-Shepherd ([2312.08935](https://arxiv.org/abs/2312.08935), auto-labels), **GenRM** ([2408.15240](https://arxiv.org/abs/2408.15240), Agarwal — verifier as next-token), ThinkPRM ([2504.16828](https://arxiv.org/abs/2504.16828)). Benchmark: **ProcessBench** ([2412.06559](https://arxiv.org/abs/2412.06559)).
- **Formal (top of hierarchy)**: DeepSeek-Prover-V2 ([2504.21801](https://arxiv.org/abs/2504.21801) — 88.9% miniF2F), **Goedel-Prover-V2** ([2508.03613](https://arxiv.org/abs/2508.03613) — 8B beats 671B), **AlphaProof** (Nature 2025, IMO-2024 silver, [nature](https://www.nature.com/articles/s41586-025-09833-y)), **Harmonic Aristotle** ([2510.01346](https://arxiv.org/abs/2510.01346) — Lean-verified IMO-2025 gold-level 5/6, 96.8% VERINA; "proofs are provable, not merely likely").
- **Weak → strong gate**: **Weaver** ([2506.18203](https://arxiv.org/abs/2506.18203), Stanford) — ensemble weak verifiers → o3-mini-level 87.7% with a weak (Llama-70B) generator. AgentV-RL ([2604.16004](https://arxiv.org/abs/2604.16004) — 4B verifier +25.2%), Marco ([2603.28376](https://arxiv.org/abs/2603.28376) — 8B ≥ 30B), DeepVerifier ([2601.15808](https://arxiv.org/abs/2601.15808)).
- **Co-evolving (Red Queen)**: **Red Queen Gödel Machine** ([2606.26294](https://arxiv.org/abs/2606.26294), Cambridge/Flower), RL Tango ([2505.15034](https://arxiv.org/abs/2505.15034)), and **Verification Horizon** ([2606.26300](https://arxiv.org/abs/2606.26300), Qwen — "no silver bullet; verifiers saturate as the policy improves").
- **Self vs external**: "LLMs Cannot Self-Correct Reasoning Yet" ([2310.01798](https://arxiv.org/abs/2310.01798), Denny Zhou) — but learned self-verification helps ([2602.07594](https://arxiv.org/abs/2602.07594)); cross-family verification is strongest ([2512.02304](https://arxiv.org/abs/2512.02304)). **Calibration**: reasoning fine-tuning **degrades abstention by 24%** ([2506.09038](https://arxiv.org/abs/2506.09038)).

### RL — RL for reasoning & agents
- **Foundations**: RLHF/InstructGPT ([2203.02155](https://arxiv.org/abs/2203.02155)), Constitutional AI/RLAIF ([2212.08073](https://arxiv.org/abs/2212.08073)), DPO ([2305.18290](https://arxiv.org/abs/2305.18290)), SimPO ([2405.14734](https://arxiv.org/abs/2405.14734)).
- **The GRPO zoo**: GRPO ([2402.03300](https://arxiv.org/abs/2402.03300)) → **Dr.GRPO** ([2503.20783](https://arxiv.org/abs/2503.20783) — length/difficulty-bias fix) → **DAPO** ([2503.14476](https://arxiv.org/abs/2503.14476) — 50 AIME) → **VAPO** ([2504.05118](https://arxiv.org/abs/2504.05118) — value-based, 60.4 AIME) → **GSPO** ([2507.18071](https://arxiv.org/abs/2507.18071) — sequence-level, powers Qwen3) → REINFORCE++ ([2501.03262](https://arxiv.org/abs/2501.03262)). Unified: **all three are one number** ([2607.00152](https://arxiv.org/abs/2607.00152) — group-std identity).
- **Credit assignment**: **PURE** ([2504.15275](https://arxiv.org/abs/2504.15275) — min-form kills PRM reward-hacking), VinePPO ([2410.01679](https://arxiv.org/abs/2410.01679) — MC values, 9× fewer steps), TRIAGE ([2606.32017](https://arxiv.org/abs/2606.32017)).
- **Self-play / self-improve**: **Absolute Zero** ([2505.03335](https://arxiv.org/abs/2505.03335) — propose+solve, zero data), R-Zero ([2508.05004](https://arxiv.org/abs/2508.05004)), SPIN ([2401.01335](https://arxiv.org/abs/2401.01335)), Self-Rewarding LMs ([2401.10020](https://arxiv.org/abs/2401.10020), Weston).
- **Tool-use / streaming**: ReTool ([2504.11536](https://arxiv.org/abs/2504.11536) — 67 AIME), Search-R1 ([2503.09516](https://arxiv.org/abs/2503.09516)), stream-x ([2410.14606](https://arxiv.org/abs/2410.14606), shared with D6).

---

## 3. Contradictions (the frontier's live disagreements — preserved as `contradicts` edges)

| # | Tension | Pro | Contra |
|---|---|---|---|
| 1 | **Does RLVR expand reasoning or only sharpen it?** | RLVR only reweights the base distribution ([2504.13837](https://arxiv.org/abs/2504.13837), Tsinghua; [2507.14843](https://arxiv.org/abs/2507.14843) Invisible Leash) | RL finds genuinely new strategies (**ProRL** [2505.24864](https://arxiv.org/abs/2505.24864) NVIDIA; **RL-Grokking** [2509.21016](https://arxiv.org/abs/2509.21016)); the split is a **metric artifact** (Pass@K vs CoT-Pass@K, [2506.14245](https://arxiv.org/abs/2506.14245)) |
| 2 | **Do spurious/random rewards really work?** | Random/incorrect rewards ≈ ground truth on Qwen ([2506.10947](https://arxiv.org/abs/2506.10947), Lambert et al.) | That's **contamination + Qwen-specific**; on clean data only correct rewards help ([2507.10532](https://arxiv.org/abs/2507.10532)). Both agree: **fails on Llama/OLMo** |
| 3 | **PRM > ORM, or are PRM gains fragile?** | Process > outcome ([2305.20050](https://arxiv.org/abs/2305.20050); [2312.08935](https://arxiv.org/abs/2312.08935)) | PRMs are **systematically exploitable** ([2603.06621](https://arxiv.org/abs/2603.06621); [2505.22203](https://arxiv.org/abs/2505.22203) pitfalls) |
| 4 | **Is the verifier hierarchy clean?** | Self-improvement tracks formal>PRM>rubric>intrinsic ([2607.07663](https://arxiv.org/abs/2607.07663)) | Each tier is individually gameable — **rubric hacking** ([2605.12474](https://arxiv.org/abs/2605.12474)); and reward **noise-robustness** suggests precision is over-valued ([2505.22653](https://arxiv.org/abs/2505.22653)) |
| 5 | **More test-time compute — always better?** | Compute-optimal TTS beats 14× params ([2408.03314](https://arxiv.org/abs/2408.03314); [2407.21787](https://arxiv.org/abs/2407.21787)) | **Inverse scaling / overthinking** ([2507.14417](https://arxiv.org/abs/2507.14417) Anthropic; [2410.21333](https://arxiv.org/abs/2410.21333) Griffiths) |
| 6 | **Is CoT faithful reasoning?** | CoT exposes real multi-step reasoning ([2201.11903](https://arxiv.org/abs/2201.11903)) | CoT verbalizes the true cue **<20% of the time**, rationalizes ([2505.05410](https://arxiv.org/abs/2505.05410), Anthropic; [2503.08679](https://arxiv.org/abs/2503.08679)) |
| 7 | **Verification-supremacy vs self-consistency-is-cheaper** | Verifier-based TTS provably wins ([2502.12118](https://arxiv.org/abs/2502.12118), Kumar) | At practical budgets self-consistency is more compute-efficient ([2504.01005](https://arxiv.org/abs/2504.01005)); verifier-guided search has **scaling flaws** ([2502.00271](https://arxiv.org/abs/2502.00271)) |
| 8 | **Is latent reasoning real?** | Coconut/looped match explicit CoT with fewer tokens ([2412.06769](https://arxiv.org/abs/2412.06769)) | Latent tokens are **shortcut placeholders** ([2512.21711](https://arxiv.org/abs/2512.21711)); depth-recurrence gains marginal ([2507.02199](https://arxiv.org/abs/2507.02199)) |

(11 `contradicts` edges total in the JSON; the table groups the highest-value clusters.)

---

## 4. Frontier synthesis (3 lines per family)

- **Reasoning**: the field has moved from *prompting* scaffolds (CoT/ToT/GoT) to *training* reasoners (R1-style RLVR) and *spending inference* (test-time compute). The unifying 2025-26 finding is that **test-time compute is only as good as the verifier that selects among samples** (Monkeys' bottleneck; Setlur/Kumar) — and it is **not monotone** (inverse scaling). Latent reasoning is promising but contested (shortcut critique).
- **Verification**: the load-bearing family. Strength orders formal > PRM > rubric > intrinsic ([2607.07663](https://arxiv.org/abs/2607.07663)); formal (Lean) is the only *provable* gate (Aristotle/Goedel/AlphaProof) but domain-limited; every neural tier (PRM, rubric) is individually hackable, and static verifiers **saturate** as the policy improves (Verification Horizon) — pushing the frontier toward **co-evolving (Red-Queen)** and **weak-verifier-ensemble** gates.
- **RL**: converged on **RLVR + a GRPO variant** as the recipe, now revealed to be *one algorithm* ([2607.00152](https://arxiv.org/abs/2607.00152)); the open questions are whether RL *discovers* vs *sharpens* (unresolved, partly a metric artifact), how much of the signal is *model-specific prior-surfacing* (spurious rewards), and how to assign *credit* (min-form/PURE, MC/VinePPO). Self-play (Absolute Zero) closes the data loop when a verifiable reward exists.

---

## 5. Single best verification method to absorb next (given the STOP)

**Recommendation: Weaver-style weak-verifier ensembling ([2506.18203](https://arxiv.org/abs/2506.18203)) as the general gate, with a Lean/formal gate wherever the subtask is formalizable (top of hierarchy).**

Reasoning tied to the STOP: the DriftBench STOP is caused by a *weak/intrinsic* verifier, and the fix is "the strongest verifier possible — functional held-out tests, not LLM-judge." Where AIOS can run a functional/executable test (code, math), that already dominates the hierarchy and should be the gate. The *hard* case — and where the STOP actually bites — is open-ended tasks with **no single strong verifier**. Weaver is the method that most directly raises verifier strength in exactly that regime: it combines many *weak* verifiers (which AIOS already produces via `multi-substrate-review` — codex/gemini/local-qwen judges, rubrics, unit signals) into one strong verifier via weak-supervision aggregation, reaching near-frontier (o3-mini-level, 87.7%) with a *weak* generator, no labels, and it is device-runnable. It sits structurally right above the rubric/intrinsic tier the STOP warns against and maps 1:1 onto AIOS's existing organ. 

Second choice (absorb after): a **co-evolving verifier** (Red Queen Gödel [2606.26294](https://arxiv.org/abs/2606.26294) / RL Tango [2505.15034](https://arxiv.org/abs/2505.15034)) to counter verifier *saturation* (Verification Horizon [2606.26300](https://arxiv.org/abs/2606.26300)) once the gate is strong enough to be worth defending. **Caveat (contradiction #4):** every neural verifier tier is individually gameable, so an ensemble gate must be paired with at least one *grounded* signal (executable test / formal check) to avoid collectively hackable rubric consensus.

---

## 6. Coverage & honest gaps

- **Count exceeds the nominal ~30-45 paper bound (105 papers)** — deliberate: D5 spans three full families and the *contradictions* (the ledger's stated value) require both sides of each debate. No silent truncation; every node is sourced.
- **`grade:hypothesis` nodes** (secondary/uncertain): AlphaProof-Nature (cited via WebSearch + Nature URL, not arxiv abstract), `2603.19335` (post-training-differ, surfaced once), `2602.04248` Empirical-MCTS. Treat their exact numbers as high-confidence-secondary until PDF-confirmed.
- **DeepSeek-R1 exact benchmark figures** (AIME ≈79.8%, MATH-500 ≈97.3%) are widely-reported but were **not re-derived** from the PDF/Nature version this session — the node records the qualitative claim, not the numbers.
- **o1/o3 test-time reasoning** rests on OpenAI blog posts, not an arxiv paper — represented only via the R1/RLVR training node; no separate o-series node (non-paper).
- **Thin threads** (candidates for radar follow-up): calibration/abstention (3 nodes), offline RL for LLMs beyond streaming (ILQL/off-policy-correction not covered), reward-model *internals* (Bradley-Terry, reward-hacking mechanics), agentic long-horizon RL at SWE-bench scale (sampled not exhausted), tool-integrated reasoning (ToRA), and DPO variants IPO/KTO/ORPO (named, not node-ized).
- **Aggregator/uncertain hypotheses flagged**: the RSI hierarchy ordering is an *empirical survey observation*, not a proven theorem — its strongest live counter-pressure is contradiction #4 (each tier is individually hackable). Recorded as a `Claim` with `contradicts` edges, not as ground truth.
- **Merge**: verified compatible via dry-run only; **`_merged.json` was NOT regenerated** (it is owned by the merge organ / other domains; `experiments/` untouched). A future merge run that adds D5 to the SOURCES list will ingest this file unchanged.
