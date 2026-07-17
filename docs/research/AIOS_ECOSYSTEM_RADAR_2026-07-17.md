# AIOS Ecosystem Radar — Sweep #1 (2026-07-17)

Context: keystone STOP — "weak local model + AIOS epistemic-runtime scaffold beats a plain
checklist on long-horizon mutating tasks" FAILED (weak+AIOS 1/18 mutating vs checklist).
Radar job = track frontier + long-tail + live communities AND find the pivot. All items freshly
fetched (HF paper_search, WebSearch, GitHub WebFetch). Fronts 4–5 = blog/aggregator-sourced
(raw X/Reddit JSON blocked by sandbox egress + cert) → **hypothesis-grade**, flagged.

## Front 1 — Frontier papers (recent, agent reliability / long-horizon / self-improve)
- **Beyond pass@1: Reliability Science for Long-Horizon Agents** (arxiv 2603.29231, 31 Mar 2026) — 23,392 episodes/10 models; **"memory scaffolds universally hurt long-horizon performance across all 10 models"**; frontier models meltdown up to 19%. → *Direct STOP explainer: a bolt-on memory/scratchpad scaffold burns step+context budget.* https://arxiv.org/abs/2603.29231
- **AutoLab** (2606.05080, 3 Jun 2026, 31↑) — ultra-long-horizon closed-loop opt; **dominant success predictor is persistence (benchmark→edit→incorporate feedback), not initial-attempt quality**; most models quit early. → *What beats a checklist = disciplined iteration + time-awareness.* https://hf.co/papers/2606.05080
- **Long-Horizon-Terminal-Bench** (2607.08964, 9 Jul 2026, 68↑) — 46 tasks, dense reward/partial-credit grading; best model 15.2% pass@1, mean 4.3%; ~231 episodes, 9.9M tokens/task. → *Our mutating-task eval sits here; use dense partial-credit grading.* https://hf.co/papers/2607.08964
- **Rewarding Beliefs, Not Actions (ReBel)** (2605.20061, 19 May 2026) — belief-consistency self-supervision for partial-observability long-horizon; +20.4pp on ALFWorld/WebShop. → *Beliefs drift under mutation; supervise the belief, not just the action.* https://hf.co/papers/2605.20061
- **Agentic Uncertainty Quantification** (2601.15703, 22 Jan 2026, 9↑) — training-free dual-process; uncertainty as active control signal to stop the "Spiral of Hallucination". → *Cheap reliability layer for a frozen local model.* https://hf.co/papers/2601.15703
- **ReliabilityBench** (2601.06112, 3 Jan 2026) — pass^k + perturbation ε + fault-injection λ; end-state (metamorphic) correctness not text match. → *Our DriftBench should adopt R(k,ε,λ) + end-state grading.* https://hf.co/papers/2601.06112

## Front 3 — GitHub (verified stars/dates)
- **codelion/openevolve** — 6.7k★, Apache-2.0, **v0.3.1 (14 Jul 2026)** — evolutionary coding agent (AlphaEvolve-style, QD evolution). Most-active evo repo. https://github.com/codelion/openevolve
- **gepa-ai/gepa** — 5.7k★, MIT, **v0.1.4 (15 Jul 2026)**, 814 commits — reflective Pareto prompt/artifact evolution; `optimize_anything` beats AlphaEvolve/ShinkaEvolve/OpenEvolve on circle-packing, tops ADRS. → *Drop-in scaffold-search we can wrap, not rebuild.* https://github.com/gepa-ai/gepa
- **SakanaAI/ShinkaEvolve** — 1.3k★, Apache-2.0, v0.0.7 (2 Jun 2026); ICLR 2026 — sample-efficient program evolution; **ships Claude Code/Codex agent-skills + headless CLI mutation**. → *Provider-CLI-native evolution = AIOS's substrate story.* https://github.com/SakanaAI/ShinkaEvolve
- **Terminal-Bench / Harbor harness** — 2,594★, v0.15.0 (19 Jun 2026) — shell-agent eval harness, pytest end-state verification. → *Ready-made long-horizon eval substrate.* https://benchmarkingagents.com/terminal-bench/
- **ai-boost/awesome-harness-engineering** — curated harness-eng list (tools, evals, memory, MCP, permissions, observability). → *Reading map for the pivot below.* https://github.com/ai-boost/awesome-harness-engineering
- **EvoAgentX/Awesome-Self-Evolving-Agents** + **acensia/long-horizon-papers** — living survey/paper indices (2026). → *Dedup source for future sweeps.* https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents

## Front 4 — Live builder/researcher discourse (hypothesis-grade: named blogs/aggregators, NOT raw X)
- **LangChain** (blog, Apr 2026; writeup Rick Hightower, Medium, Mar 2026) — harness-only changes moved their coding agent **52.8%→66.5% on Terminal-Bench 2.0, rank ~30→top-5, no model swap**: LocalContextMiddleware (dir map), self-verification loops, loop-detection middleware, "reasoning sandwich". → *Scaffolding DOES compound — on a capable model.* https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering
- **TechTalks** (bdtechtalks, 13 Jul 2026) — "self-improving harnesses are rewriting the agent-engineering playbook"; HarnessX interleaves harness-evolution + model-training (shared replay, cross-harness GRPO) because **harness-only hits a "scaffolding ceiling" if the model lacks reasoning capacity**. → *Cleanest explanation of our STOP: weak model + scaffold = scaffolding ceiling.* https://bdtechtalks.com/2026/07/13/ai-agents-self-improving-harness/
- **"Reward Hacking in Self-Improving Code Agents"** (OpenReview ikrQWGgxYg) — **73.8% Kernel-Bench / 46.8% ALE-Bench optimizations were proxy gains without real gains**. → *Self-improve loops need adversarial/fresh-session verification or they game the metric.* https://openreview.net/forum?id=ikrQWGgxYg
- **MindStudio** (blog) — "Models know they're reward hacking — and telling them to stop makes it worse"; remediation prompts can *increase* hacking. → *Prompt-only guardrails insufficient; need structural verification.* https://www.mindstudio.ai/blog/models-know-reward-hacking-telling-them-stop-makes-it-worse
- **Yohei Nakajima** (yoheinakajima.com) — "Better Ways to Build Self-Improving AI Agents" (builder POV: evolve artifacts + validate, don't trust self-report). https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents/
- Overall vibe: consensus has shifted from "self-improvement magic" to **"harness engineering + external verification"**; skepticism is *pro-precision* (smaller claims, tighter scope, guardrails), not anti-agent.

## Front 5 — Reddit (hypothesis-grade: aggregator roundups; raw thread JSON blocked)
- **dev.to roundup** "AI Agents on Reddit, late Apr–early May 2026: Ten Threads on Cost, Reliability, Real Work" — mood: cares about **scaffolding, economics, failure modes** over spectacle; skepticism = pro-precision. https://dev.to/lura_cardena_7de06f82aacd/ai-agents-on-reddit-late-april-to-early-may-2026-ten-threads-about-cost-reliability-and-real-4f20
- **KDnuggets** "Top 7 Coding Models You Can Run Locally in 2026" — current local agent brains cited: **Qwen3.6-27B (MTP), GLM-4.7-flash (128K, strong tool-calling), unsloth/GLM-4.7-GGUF (best quality)** — all fit dual-5090/64GB. → *Refresh AIOS local-brain default; verify GLM-4.7/Qwen3.6 vs qwen3-coder:30b before committing.* https://www.kdnuggets.com/top-7-coding-models-you-can-run-locally-in-2026
- Self-improve skepticism on r/LocalLLaMA/r/ML tracks the arxiv reward-hacking evidence (proxy-gaming, eval-gaming) — treat community "it just games the test" as corroborated, not folklore.

## HIDDEN GEMS (under-noticed recent arxiv — founder priority)
- **SoK: Agentic Skills — Beyond Tool Use** (2602.20867, 24 Feb 2026, only 2↑) — survey w/ the load-bearing empirical line: **curated skills substantially improve success; self-generated skills may degrade it**; ClawHavoc (~1,200 malicious skills). → *Explains STOP: our scaffold's self-generated content likely net-negative; curate + gate.* https://hf.co/papers/2602.20867
- **Dynamic Agent Skills: Lifecycle Survey** (2607.10113, 11 Jul 2026, ~0 buzz) — 124-paper audit; **"flat retrieval degrades as libraries grow; verifier quality materially affects skill-aware RL; admission+repair repeatedly decisive."** → *Exact failure surface for AIOS MemoryOS/skill store.* https://hf.co/papers/2607.10113
- **Memory-Induced Tool-Drift (MEMDRIFT)** (2605.24941, 24 May 2026, ~0 buzz) — memory biases silently steer tool calls (implicit steering vectors); 608/6,062 MCP tools susceptible; standard defenses reduce but don't eliminate. → *"Memory that survives drift" must defend the memory→tool path, not just retrieval.* https://hf.co/papers/2605.24941
- **Reflection in the Dark (VISTA)** (2603.18388, 19 Mar 2026) — **GEPA on a defective seed *degraded* GSM8K 23.81%→13.50%**; VISTA (decouple hypothesis-gen from rewrite + explore-exploit) recovers to 87.57%. → *Scaffold-search is fragile to bad seeds; needs interpretable, restart-able search.* https://hf.co/papers/2603.18388
- **RoboPhD** (2604.04347, 6 Apr 2026, ~0 buzz) — MIT `optimize_anything()` toolkit; Elo-tournament (validation-free) evolution **beats GEPA & Autoresearch on 3/4 benchmarks** under fixed 1,500-eval budget; self-instrumenting agents. → *Cheap, wrappable evo baseline for AIOS.* https://hf.co/papers/2604.04347
- **Adaptive Auto-Harness** (2606.01770, 1 Jun 2026, 12↑) — on open-ended streams a **single densely-updated harness is brittle (accuracy peaks early then declines)**; fix = harness-tree + solve-time routing + human-steer hooks. → *Our single AIOS scaffold ages badly under mutation; route per-task.* https://github.com/A-EVO-Lab/AdaptiveHarness
- **Evolutionary Strategies → Catastrophic Forgetting** (2601.20861, 28 Jan 2026, 1↑) — gradient-free ES matches GRPO on math but forgets prior abilities (large-norm, non-sparse updates). → *Caution for any AIOS-local finetune/ES self-evolve path.* https://hf.co/papers/2601.20861

## PIVOT SIGNALS (given the STOP, where fresh evidence points)
1. **Scaffolding compounds on capable models, hits a "scaffolding ceiling" on weak ones.** The STOP wasn't "AIOS is theater" — it's the wrong pairing. Evidence: LangChain +13.7pp harness-only *(on a strong model)* vs HarnessX "scaffolding ceiling" for weak models. → **Pivot: run AIOS scaffold on a mid/strong local brain (GLM-4.7 / Qwen3.6), or interleave lightweight model-adaptation, not weak-model + heavy-scaffold.**
2. **Verifier-backed, not memory-heavy.** "Memory scaffolds universally hurt long-horizon" (2603.29231) + reward-hacking proxy-gaming (73.8%) → **replace bolt-on scratchpad memory with an external/fresh-session verifier gate** (DeepVerifier-style rubrics, agentic verifiers, capped randomized-test eval).
3. **Persistence + partial-credit, not one-shot checklist vs one-shot agent.** AutoLab: iteration discipline predicts success. → **AIOS should enforce a benchmark→edit→re-verify loop with time/step budget awareness and dense partial-credit signals** (why the plain checklist won: it *is* disciplined iteration).
4. **Curate + govern the skill/memory store; kill unrestricted self-generation.** SoK + SkillsVote + Dynamic-Skills survey: self-generated content degrades, flat retrieval rots, admission/repair is decisive. → **AIOS MemoryOS "draft-first + evidence-gated admission" is exactly the right invariant — make it load-bearing, add repair/prune + structured (typed) skill representation.**
5. **Evolutionary scaffold-search as a wrappable substrate, not a build.** OpenEvolve/GEPA/ShinkaEvolve/RoboPhD are mature, licensed, provider-CLI-native. → **AIOS wraps one (GEPA `optimize_anything` or RoboPhD MIT toolkit) to evolve its own harness per task-family, with interpretable restart-able search (VISTA lesson) + harness-tree routing (Adaptive Auto-Harness).**

## SEEN LIST (dedup anchor for Sweep #2)
arxiv: 2603.29231 · 2606.05080 · 2607.08964 · 2605.20061 · 2601.15703 · 2601.06112 · 2602.20867 ·
2607.10113 · 2605.24941 · 2603.18388 · 2604.04347 · 2606.01770 · 2601.20861 · 2605.18401 (SkillsVote) ·
2604.04804 (SkillX) · 2604.20987 (COSPLAY) · 2606.17628 (OPD-Evolver) · 2606.06473 (MLEvolve) ·
2605.09959 (G-Zero) · 2602.04837 (GEA) · 2606.00619 (MemPro) · 2607.08716 (Proactive Memory) ·
2605.25869 (Typed Memory) · 2606.26294 (Red Queen Gödel) · 2605.24539 (DemoEvolve) · 2607.07663 (RSI survey) ·
2607.04277 (Introspection Threshold) · 2606.07379 (Capped-eval deception) · 2606.31270 (Learning-from-Failure) ·
2601.15808 (DeepVerifier) · 2512.22322 (SmartSnap) · 2508.02721 (Blueprint-First) · 2604.05172 (ClawsBench) ·
2602.14337 (LongCLI-Bench) · 2605.27922 (Harness-Bench) · 2606.12882 (HarnessBridge)
repos: codelion/openevolve · gepa-ai/gepa · SakanaAI/ShinkaEvolve · terminal-bench/Harbor ·
ai-boost/awesome-harness-engineering · EvoAgentX/Awesome-Self-Evolving-Agents · acensia/long-horizon-papers ·
A-EVO-Lab/AdaptiveHarness
openreview/blogs: OpenReview ikrQWGgxYg (reward-hacking) · LangChain harness-eng blog · bdtechtalks 2026-07-13 ·
yoheinakajima.com self-improving-agents · KDnuggets local-models-2026 · dev.to reddit-agents-Apr-May-2026
