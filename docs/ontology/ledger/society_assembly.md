# Frontier Knowledge Ledger — D7: Multi-agent society + assembly/composition

**Schema**: `docs/ontology/FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md` §1 (unified). **Data**: `society_assembly.json`.
**Status**: draft-first (append; not accepted — DNA #2). **Populated**: 2026-07-17 by claude@myworld.
**Grounding**: 3 parallel grounded research agents (society / assembly / generative-composition) + own WebSearch, HF `paper_search`, WebFetch this session — every node/edge sourced. All arxiv ids verified to resolve unless tagged `grade:hypothesis`.
**Format**: CANONICAL flat-entity + `{src_id,rel,dst_id}` edges (matches `learning_methods.json` / `_merged.json` ingestion). **Reuses shared ids** — `org:sakana_ai`, `org:google_deepmind`, `org:meta_fair`, `person:percy_liang`, `methodology:agentic_pipelines_multi_agent_orchestration_tool_use`, `methodology:diffusion_flow_matching_generative_models` — so cross-domain edges resolve.

**Master-table reconciliation**: master §2 slots `D7 = "Generative modeling"`. The **founder brief 2026-07-17 reassigns/expands D7** to *multi-agent society + assembly/composition* ("AGI = gather the scattered frontier pieces into ONE SOCIETY, assemble not invent" / 사회를 만드느냐, 흩어진 것을 모아서 하나의 AGI로). The generative-composition family (F3) carries the generative-modeling content **as composition methods**. This is an explicit founder re-scope, not schema drift.

**Counts**: 149 nodes (48 papers, 32 people, 16 orgs/labs, 26 claims, 16 concepts, 7 benchmarks, 3 methodologies, 1 domain) · 248 edges incl. **14 `contradicts`** — the frontier's disagreements, with the multi-agent-helps-vs-hurts crux front and center.

---

## 1. The three families (map)

| Family | Founder's words | What it is | Methodology node |
|---|---|---|---|
| **F1** | "사회를 만드느냐" (build a society) | **Multi-agent society**: agent societies (Generative Agents lineage), role-differentiated planner/solver/critic, debate/reflection, specialist coevolution, A2A/ACP society infrastructure | `methodology:multi_agent_society` |
| **F2** | "흩어진 것을 모아서 하나로" (gather the scattered into one) | **Assembly/composition of models & methods**: weight-space merging, mixture-of-agents, routing/ensembling, skill/tool composition, LLM-as-orchestrator | `methodology:model_method_assembly_composition` |
| **F3** | "조립, 발명이 아니라" (assemble, don't invent) | **Generative composition methods**: diffusion reasoning/planning, flow matching, latent-program synthesis/library learning, workflow/agent distillation, retrieval/memory composition | `methodology:generative_composition_methods` |

### F1 — Multi-agent society
- **Societies / Generative Agents lineage**: Generative Agents (Park et al., [2304.03442](https://arxiv.org/abs/2304.03442), UIST 2023 — 25 agents, memory-stream + reflection + planning) → **AgentSociety** ([2502.08691](https://arxiv.org/abs/2502.08691), Tsinghua FIB, >10k agents / ~5M interactions) → **Concordia** GABM ([2312.03664](https://arxiv.org/abs/2312.03664), Google DeepMind, "Game Master"). *(md-only neighbors: OASIS 1M-agents [2411.11581](https://arxiv.org/abs/2411.11581).)*
- **Role-differentiated (planner/solver/critic)**: **MAE** = Multi-Agent Evolve ([2510.23595](https://arxiv.org/abs/2510.23595), Proposer/Solver/Judge from one LLM + RL, +4.54% on Qwen2.5-3B); **SAGE** = Multi-Agent Self-Evolution ([2603.15255](https://arxiv.org/abs/2603.15255), Challenger/Planner/Solver/Critic). *(Acronym collisions recorded: MAEBE [2506.03053], a distinct SAGE [2601.09750].)*
- **Joint alignment / harmonization**: **MOAT** ([2509.09629](https://arxiv.org/abs/2509.09629), EMNLP 2025 Findings) — alternates planning-agent alignment ↔ grounding-agent improvement; +3.1% held-in / +4.4% held-out, proven convergence.
- **Debate & reflection**: Du et al. multiagent debate ([2305.14325](https://arxiv.org/abs/2305.14325), ICML 2024). *("DAR" is **not** a real single named paper — nearest real 2026 work: RUMAD [2602.23864], Debate-as-Reward [2604.16723], SDRL [2601.22297], md-only.)*
- **Specialist coevolution**: **AC/DC** = "Assessment Coevolving with Diverse Capabilities" ([2604.14969](https://arxiv.org/abs/2604.14969), Sakana-affiliated — Y. Tian, Y. Tang) — coevolves LLMs **via model merging** + synthetic tasks into an archive of small experts beating larger LLMs. **This is the hinge node** where society (coevolving specialists) and assembly (merging) meet.
- **Society infrastructure (agent-to-agent protocols)**: survey of MCP / A2A / ACP / ANP ([2505.02279](https://arxiv.org/abs/2505.02279)). **A2A** (Google, 2025-04) → donated to **Linux Foundation** 2025-06, 150+ orgs by 2026-04; **ACP** (IBM) for edge/local. Governance gaps: [2606.31498](https://arxiv.org/pdf/2606.31498).

### F2 — Assembly / composition of models
- **Model merging (weight space, no training)**: Task Arithmetic ([2212.04089](https://arxiv.org/abs/2212.04089)) → TIES ([2306.01708](https://arxiv.org/abs/2306.01708)) → DARE/Super-Mario ([2311.03099](https://arxiv.org/abs/2311.03099)) → **Evolutionary Merge** (Sakana, [2403.13187](https://arxiv.org/abs/2403.13187), Nature MI 2025 — EvoLLM-JP 7B > some 70B). Also Model Soups ([2203.05482](https://arxiv.org/abs/2203.05482)). Survey [2603.09938]. *(2026 landscape md-only: STAR, Sparsity-Aware Evolution, Fisher-Rao merging, LoRA Soups.)*
- **Mixture-of-agents / ensembling (output space)**: MoA ([2406.04692](https://arxiv.org/abs/2406.04692), 65.1 > 57.5 GPT-4o); **Self-MoA** ([2502.00674](https://arxiv.org/abs/2502.00674) — single-best-model self-ensemble **beats** mixed MoA); More Agents Is All You Need ([2402.05120](https://arxiv.org/abs/2402.05120)); LLM-Blender ([2306.02561](https://arxiv.org/abs/2306.02561)); **Co-Failure Ceiling** ([2606.27288](https://arxiv.org/abs/2606.27288), 1−β cap).
- **Routing (pick-one)**: RouteLLM ([2406.18665](https://arxiv.org/abs/2406.18665), >2× cheaper); FrugalGPT ([2305.05176](https://arxiv.org/abs/2305.05176), up to 98% cost cut).
- **Inference-time multi-model search**: **AB-MCTS / TreeQuest** (Sakana, [2503.04412](https://arxiv.org/abs/2503.04412)) — multi-LLM 27.5% > 23% (o4-mini) on ARC-AGI-2; picks *which model per step* by Thompson sampling.
- **Skill/tool composition & LLM-as-orchestrator**: Voyager skill library ([2305.16291](https://arxiv.org/abs/2305.16291)); SkillComposer ([2606.32025](https://arxiv.org/abs/2606.32025)).

### F3 — Generative composition methods (compact)
- **Diffusion for reasoning/planning**: LLaDA ([2502.09992](https://arxiv.org/abs/2502.09992), 8B ≈ LLaMA3-8B); Diffusion-of-Thought ([2402.07754](https://arxiv.org/abs/2402.07754)); d1 RL ([2504.12216](https://arxiv.org/abs/2504.12216)); **Think First, Diffuse Fast** ([2603.13243](https://arxiv.org/abs/2603.13243) — dLLMs *underperform* multi-step, +11.6pp with an AR plan); Diffuser planning-as-inference ([2205.09991](https://arxiv.org/abs/2205.09991)).
- **Flow matching**: Lipman et al. ([2210.02747](https://arxiv.org/abs/2210.02747)); Discrete Flow Matching ([2407.15595](https://arxiv.org/abs/2407.15595)).
- **Latent-program synthesis / library learning**: DreamCoder ([2006.08381](https://arxiv.org/abs/2006.08381)); LILO ([2310.19791](https://arxiv.org/abs/2310.19791)) — programs as composable skills.
- **Distillation as composition**: Agent Distillation ([2505.17612](https://arxiv.org/abs/2505.17612)); **AgentArk** ([2602.03955](https://arxiv.org/abs/2602.03955)) — multi-agent → one model's weights; capacity-gap caveat: an over-capable teacher *degrades* the student ([2604.08880](https://arxiv.org/abs/2604.08880)). **AIOS's own ASC-0284** capsule-distillation returned `HONEST_NEGATIVE` (see §4).
- **Retrieval/memory composition**: write-vs-retrieve bottleneck ([2603.02473](https://arxiv.org/abs/2603.02473)) — retrieval dominates, write-time processing barely matters.

---

## 2. THE CONTRADICTION — does a society of assembled pieces beat a single strong model? (front and center)

This is the load-bearing disagreement of D7, preserved as 14 `contradicts` edges. **Two levels — agents, and models:**

**PRO ("assemble → more"):**
- Anthropic's orchestrator + parallel subagents beat single-agent Opus **+90.2%** on an internal research eval — *but ~15× the tokens* ([blog](https://www.anthropic.com/engineering/multi-agent-research-system)).
- MoA 65.1 > 57.5 GPT-4o ([2406.04692]); Evolutionary merge 7B > 70B ([2403.13187]); AB-MCTS multi-model > each individual on ARC-AGI-2 ([2503.04412]); AC/DC small experts > larger LLMs ([2604.14969]).

**ANTI ("a single strong model / simpler method wins"):**
- **MedAgentBoard** ([2505.12371], NeurIPS 2025): multi-agent does **not** consistently beat advanced single LLMs and **loses to specialized conventional methods** on VQA/EHR.
- **MAST — Why Do Multi-Agent LLM Systems Fail?** ([2503.13657], Berkeley): gains over single-agent "often remain **minimal**"; failures are structural (14 modes).
- **Multi-Agent Teams Hold Experts Back** ([2602.01011], Stanford): teams lose to their own best member by **up to −37.6%**, even told who the expert is.
- **The Illusion of Multi-Agent Advantage** ([2606.13003]): auto-MAS **underperform CoT-Self-Consistency at up to 10× cost**.
- **Debate or Vote** ([2508.17536]) + **Stop Overvaluing MAD** ([2502.08788]): **majority voting**, not debate, drives the gains; debate is a martingale.
- **Self-MoA** ([2502.00674]): mixing different LLMs **lowers** average quality; single-best self-ensemble wins by +6.6% / +3.8%.
- **Co-Failure Ceiling** ([2606.27288]): accuracy is capped at **1−β**; "combining models **rarely beats the single best model without a strong query-level routing signal**."
- **In-the-Wild Merging** ([2511.21437]): of 6 merging methods, **only Task Arithmetic reliably gains**; interference-aware methods are inert in the wild.
- **Are More LLM Calls All You Need?** ([2403.02419], NeurIPS 2024): accuracy **rises then FALLS** as calls increase.

---

## 3. The ASSEMBLY-INTO-SOCIETY synthesis (how the frontier says to compose scattered pieces)

The founder's thesis — *assemble scattered frontier pieces into one system* — is **conditionally supported, not unconditionally**. The frontier's own evidence converges on a single rule:

> **A society of assembled pieces beats a single strong model only when (a) the pieces fail on *different* inputs (decorrelated errors), AND (b) there is a query-level routing / selection signal that exploits that diversity. Absent both, adding pieces raises the shared-failure rate β, lowers average quality, injects weight-interference, and pays a coordination/token tax — degrading the whole.**

Concretely, **WHEN it wins**:
- Heterogeneous, *strong* components + a selector that routes per-query or per-step (AB-MCTS Thompson sampling; RouteLLM; MoA over *comparable-quality* open models). Diversity helps **conditional on quality held equal** (Self-MoA's own finding, read positively).
- Open-ended / exploratory tasks where curated orchestration with isolated subagents pays off (Anthropic research eval) — at a real cost multiple.
- Coevolution that *manufactures* decorrelation: AC/DC grows specialists that fail differently by construction, then merges/selects among them.

**WHEN it loses**: correlated or weaker components; naive averaging/voting without a routing signal; debate expected to add reasoning it structurally cannot (martingale); auto-generated agent graphs that add bloat; distillation from an over-capable teacher. On closed-form single-answer tasks, a single strong model + CoT-Self-Consistency is a stubborn baseline that assembled societies frequently fail to beat.

**Net for AIOS**: the founder's "assemble, don't invent" is the *right* engineering bet — but the moat is **not** "add more organs/agents/models." It is the **routing/selection + decorrelation layer** that decides which piece answers each query. That layer is exactly where AIOS already sits (substrate_router, 5-OS query ritual, heterogeneous adversarial lane). D7 says: invest there, not in agent count.

### Top-3 assembly methods to ABSORB for AIOS
1. **AB-MCTS / TreeQuest multi-model inference-time search** ([2503.04412], Sakana, OSS) — per-*step* model selection by Thompson sampling over a heterogeneous pool. Directly upgrades AIOS's substrate_router from static routing to adaptive wider-vs-deeper + which-model search. Decorrelation + routing in one algorithm.
2. **Evolutionary model merging** ([2403.13187], Sakana, param + data-flow space) + **AC/DC coevolution** ([2604.14969]) — assemble *new* sovereign local experts on the dual RTX 5090 from open weights without training, and coevolve them to fail differently. This is the concrete build-path for AIOS's "narrow QLoRA / device-runnable expert" thesis.
3. **Routing as the value layer** — RouteLLM/FrugalGPT ([2406.18665], [2305.05176]) preference-learned strong/weak + cascade routing, guarded by the **Co-Failure-Ceiling discipline** ([2606.27288]): before adding any organ/model, measure whether it fails on *different* inputs and whether a routing signal exists — otherwise it cannot help. Adopt this as an AIOS absorption gate (mirrors the existing absorption-probe).

---

## 4. AIOS's own negative (honest, kept)

**ASC-0284** (closed, `HONEST_NEGATIVE`): distilling a multi-step agent "runtime capsule" into a small local model (`qwen3:1.7b`) — B1 (capsule) won **0/12** paired tasks, both arms 0/12 exact success, capsule **increased** scope violations 1→3 and malformed outputs 1→2. Workflow/capsule distillation did **not** transfer to a T1 substrate. This is `claim:d7_aios_asc0284_capsule_negative`, edged `contradicts` the AgentArk "multi-agent-distills-cleanly" claim — a real, first-party data point on the *distillation-as-composition* side, consistent with the capacity-gap literature ([2604.08880], [2505.14216]).

---

## 5. Coverage & honest gaps

- **Bound**: target ~30-45 papers / ~20-35 people — **MET** (48 papers, 32 people, 16 orgs/labs). Deliberately kept slightly over on papers to preserve the *full* helps-vs-hurts evidence set intact; trimming it would launder the contradiction.
- **`grade:hypothesis`** (4 papers): single-author/unreviewed or abstract-only numbers — Co-Failure-Ceiling [2606.27288], SkillComposer [2606.32025], Capacity-Gap [2604.08880], merging survey [2603.09938]. Treat their numbers as provisional.
- **Deferred / md-only** (not noded): "DAR" (not a real paper — RUMAD/Debate-as-Reward/SDRL are the real nearest); per-protocol A2A/ACP spec papers (noded via survey + concept); society-sim neighbors (OASIS, Concordia companion); 2026 merging-landscape (STAR, Sparsity-Aware Evolution, Bayesian/Fisher-Rao, LoRA Soups); coevolution neighbors (SEAL, CoEvoSkills); commercial diffusion LLMs (Mercury, Gemini Diffusion — no primary preprint); industry blogs (Anthropic, Cognition "Don't Build Multi-Agents" and its 2026-03 reversal) as secondary sources.
- **`contradicts` edges (14)** are the deliverable's spine — they encode that the frontier is *not* settled on whether an assembled society beats a single strong model. Preserved, not resolved.
- The **radar organ** should append new society/assembly papers (esp. 2026 routing + merging + coevolution) into this file continuously.
