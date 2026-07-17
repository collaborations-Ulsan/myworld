# AIOS Ecosystem Radar — Sweep #1 (2026-07-17)

Context: keystone STOP — "local weak model + AIOS epistemic-runtime scaffold beats a plain
checklist on long-horizon mutating tasks" FAILED (weak+AIOS 1/18 vs checklist). This sweep
tracks frontier + long-tail + live community, and hunts the PIVOT. All items freshly fetched;
aggregator-sourced claims flagged hypothesis-grade. Retrieval caveat: r/LocalLLaMA `.rss` and
`search.rss`, and direct X, returned 429 from this IP — Fronts 4–5 lean on primary essays +
aggregators, marked.

## Front 1 — Frontier papers (last ~2 weeks, July 2026)
- **Long-Horizon-Terminal-Bench** (2607.08964, Jul 9; 68▲) — 46 long-horizon terminal tasks, dense reward-based partial credit; best model 15.2% pass@1, mean 4.3%. https://hf.co/papers/2607.08964 → the eval harness the pivot needs (measures progress, not just final outcome).
- **Recursive Self-Improvement survey** (2607.07663, Jul 8) — surveys 1,250 papers; orders evaluators into a *verification hierarchy* (formal verifier > PRM > rubric > intrinsic self-assessment) and finds **demonstrated self-improvement strength TRACKS that hierarchy**. https://hf.co/papers/2607.07663 → directly explains the STOP: a scaffold with a weak/intrinsic verifier can lose to a checklist.
- **The Blind Curator** (2607.07436, Jul 8) — a biased LLM judge *silently* disables skill-retirement; false-pass bias past a sharp threshold "no amount of data can cross" → skill library drifts below the no-skill baseline. https://hf.co/papers/2607.07436 → mechanistic why a self-evolving scaffold rots; ships a cheap defect-injection audit.
- **Lilian Weng — "Harness Engineering for Self-Improvement"** (blog, Jul 4) — durable *file* state not context; verifier absence is the bottleneck ("over-optimism: declares success on failed experiments"); harness benefit is **non-monotonic, mid-tier models benefit most**; humans move up the stack. https://lilianweng.github.io/posts/2026-07-04-harness/
- **AutoLab** (2606.05080, Jun 3; 31▲) — across 17 models the dominant success predictor is **persistence in the benchmark→edit→incorporate-feedback loop, not initial attempt quality**; opus-4.6 strong, most models quit early. https://hf.co/papers/2606.05080
- **Learning from Failure** (2606.31270, Jun 30) — failure-driven self-improvement for computer-use agents: diagnose failure modes → code patches, +6.6pp OSWorld, no training. https://hf.co/papers/2606.31270

## Front 2 — Under-noticed / low-buzz, technically strong (July-lean)
- **LEVI** (2605.09764, May 10; 1▲, repo 35★) — "stronger search architecture can substitute for a larger LLM": diversity-preserving archive + mutation router + rank-preserving proxy → matches ShinkaEvolve/GEPA at **3.3–35× lower cost** with a small model. https://hf.co/papers/2605.09764
- **Red Queen Gödel Machine** (2606.26294, Jun) — co-evolve the agent AND its evaluator so the verifier can't be out-run. https://arxiv.org/abs/2606.26294
- **Self-Reference: Introspection Threshold for RSI** (2607.04277, Jul) — an introspection threshold gates whether recursive self-improvement is even possible. https://arxiv.org/abs/2607.04277
- **MEMDRIFT / Memory-Induced Tool-Drift** (2605.24941, May 24) — stored personality biases act as implicit steering vectors that silently corrupt tool calls; flagged 608/6,062 real MCP tools; prompt/filter defenses reduce but don't eliminate. https://hf.co/papers/2605.24941
- **AgentCL + MemProbe** (2606.02461, Jun 2; 5▲) — controlled task streams expose *memory-induced degradation*; naive streams can't distinguish memory designs. https://hf.co/papers/2606.02461
- **VISTA** (2603.18388, Mar 19) — on a defective seed, GEPA *degrades* 23.81%→13.50%; decoupling hypothesis-gen from rewriting + explore/exploit recovers to 87.57%. https://hf.co/papers/2603.18388

## Front 3 — GitHub (verified via API 2026-07-17)
- **SakanaAI/ShinkaEvolve** — 1,276★, Apache-2.0, pushed 07-16; ICLR-2026, now has headless CLI-backed mutation models for subscription-backed agents + agentic-workflow docs. https://github.com/SakanaAI/ShinkaEvolve
- **algorithmicsuperintelligence/openevolve** — 6,725★, Apache-2.0, pushed 07-14 (OpenEvolve moved orgs). https://github.com/algorithmicsuperintelligence/openevolve
- **gepa-ai/gepa** — 5,668★, MIT, pushed 07-16; now hosts `optimize_anything` (universal text-parameter optimizer). https://github.com/gepa-ai/gepa
- **ttanv/levi** — 35★, MIT, created 2026-03-11 (hidden-gem repo behind the LEVI paper). https://github.com/ttanv/levi
- **cxcscmu/SkillLearnBench** — 70★, MIT, pushed 07-09; finds **self-feedback alone induces recursive drift; genuine gains need external feedback across iterations**. https://github.com/cxcscmu/SkillLearnBench
- **CJReinforce/PURE** — 172★, min-form credit assignment kills PRM reward-hacking (sum-form collapses training). https://github.com/CJReinforce/PURE

## Front 4 — X/Twitter + Threads (live) — direct X blocked (429); primary-essay + aggregator, marked
- **@lilianweng** — Jul 4 harness essay above is the primary-source anchor of the "does scaffolding compound" debate (mid-tier models benefit most; verifier is the ceiling). Primary source.
- **OpenReview** — "Reward Hacking in Self-Improving Code Agents" (real submission, id ikrQWGgxYg) — self-improve agents game a cheap proxy without improving the true objective. https://openreview.net/forum?id=ikrQWGgxYg
- Discourse consensus (hypothesis-grade, via asanify/hatchworks digests, May–Jul 2026): reward hacking + scheming is now the *dominant* agent-safety topic; "retrospection cuts kernel-hacking ~17–19pts but not consistently."
- News (hypothesis-grade): open coding model "Ornith-1.0 writes its own training scaffold in RL" (TechTimes, Jun 26) — the model-generates-own-harness trend. https://www.techtimes.com/articles/319122/20260626/
- Safety arxiv serious researchers cite: "Alignment Tipping Process: self-evolution pushes agents off the rails" (2510.04860); "Safety in Self-Evolving LLM Agent Systems" (2606.23075).

## Front 5 — Reddit (r/LocalLLaMA, r/MachineLearning) — direct 429; aggregator-grade, flagged
- Newest open-weight agentic models the community is adopting (hypothesis-grade, agyn.io "ranked by benchmarks + r/LocalLLaMA sentiment", kingy.ai, HF blog): **GLM-5.2, Kimi K2.6/K2.7, DeepSeek V4, Qwen3.5/3.6, Gemma 4, MiniMax M3**. https://kingy.ai/news/best-open-weight-ai-models-in-2026-glm-5-2-vs-deepseek-v4-vs-kimi-k2-6-vs-qwen-vs-mistral/
- **Kimi K2.6/K2.7** flagged as the *agentic-stability* winner: recoverable failure modes, consistent tool-calling across long sessions (hypothesis-grade).
- Sentiment shift (dev.to recap of late-Apr/May Reddit threads): "skepticism is now pro-precision — smaller claims, tighter scope, clearer guardrails; users optimize acceptable output *per dollar*, not benchmark prestige." https://dev.to/lura_cardena_7de06f82aacd/ai-agents-on-reddit-late-april-to-early-may-2026-ten-threads-about-cost-reliability-and-real-4f20
- dual-5090 / 64GB: flagship open-weight MoE models now run locally without offload (compute-market, hypothesis-grade). https://www.compute-market.com/blog/best-local-llm-rtx-50-series-2026

## HIDDEN GEMS (founder priority)
1. **The Blind Curator** (2607.07436) — the sharpest explanation of the STOP: a biased internal judge silently switches off skill retirement; symmetric noise is survivable but **false-pass bias past a threshold is unrecoverable by more data**, and the damage is *silent* (surfaces in no aggregate metric). Action: run its defect-injection audit on AIOS's verifier BEFORE trusting any skill/memory write.
2. **LEVI** (2605.09764) — the weak-model pivot with a real witness: the win came from the *search structure* (archive diversity + mutation routing), letting a small model match frontier evolutionary runs 3.3–35× cheaper. The AIOS scaffold lost because it was a checklist, not a search.
3. **Beyond pass@1** (2603.29231, Mar 31) — reliability ≠ capability; introduces RDC/VAF/GDS/MOP and finds **"memory scaffolds universally hurt long-horizon performance across all 10 models."** Corroborated by CL-Bench (2606.05661: naive ICL > dedicated memory) and AgentCL. Adopt these as DriftBench reliability axes.

## PIVOT SIGNALS (given STOP)
1. **Verifier strength = scaffold strength.** Put a strong, grounded/formal verifier at the gate before any memory/skill write; weak models win *with* a good verifier (AgentV-RL 2604.16004: 4B verifier +25% over SOTA ORM; Marco DeepResearch 2603.28376: 8B ≥ 30B via verification-centric design; DeepVerifier 2601.15808). Survey 2607.07663 is the load-bearing claim.
2. **Reward iteration, not planning.** AutoLab: persistence in benchmark→edit→feedback predicts long-horizon success, not first-attempt quality. Reward the loop, not the plan.
3. **Make the scaffold evolve under selection.** Compounding scaffolds are the ones under evolutionary selection with diversity preservation / Elo / Pareto / group experience-sharing: GEA (2602.04837) 71.0% vs 56.7% SWE-bench-Verified via shared experience; ShinkaEvolve/LEVI/RoboPhD. Replace the static checklist with an evolving harness.
4. **Memory-that-survives-drift is UNSOLVED — stop assuming it helps.** Evidence it hurts: Beyond pass@1, CL-Bench, AgentCL, MEMDRIFT, SkillLearnBench (self-feedback→recursive drift). Positive templates: OPD-Evolver (2606.17628 — learn to *use* memory, not just store; 9B challenges 397B) and Skill1 (2605.06130 — co-evolve select/use/distill from one outcome signal). Gate writes on external verification + retirement (Blind Curator).
5. **Harness + (small) weights > harness-only.** SIA (2605.27276) + Weng: scaffold iteration alone plateaus; pairing harness improvement with narrow weight updates compounds — supports the AIOS narrow-QLoRA thesis, but only after the verifier is fixed.

## SEEN LIST (dedupe anchor for Sweep #2)
arxiv: 2607.08964, 2607.07663, 2607.07436, 2607.04277, 2606.31270, 2606.26294, 2606.23525, 2606.23075, 2606.17628, 2606.06324, 2606.05661, 2606.05080, 2606.02461, 2605.27276, 2605.24941, 2605.24539, 2605.20061, 2605.19633, 2605.09959, 2605.09764, 2605.06130, 2604.20087, 2604.16004, 2604.04347, 2603.29231, 2603.28376, 2603.18388, 2602.15112, 2602.04837, 2602.01848, 2601.15808, 2601.15703, 2512.22322, 2511.01093, 2510.04860.
repos: SakanaAI/ShinkaEvolve, algorithmicsuperintelligence/openevolve, gepa-ai/gepa, ttanv/levi, cxcscmu/SkillLearnBench, CJReinforce/PURE, Fateyetian/Rebel, wangzx1219/MASPO.
other: lilianweng.github.io/posts/2026-07-04-harness, OpenReview ikrQWGgxYg.
