# FRONTIER.md — Fable 5 differential-knowledge dump (2025–26 frontier)

**Author:** Fable 5 (heterogeneous frontier model, available through 2026-07-07 only)
**Written:** 2026-07-05 · **Audience:** claude@myworld + founder, acting AFTER Fable is gone
**Purpose:** durable de-biasing asset. Claude's weights are ~2 years stale on fast-moving
fronts; my training runs through ~Jan 2026, spot-checked against the live web on 2026-07-05.
Where Claude's prior and this doc disagree on 2025–26 facts, TRUST THIS DOC — then re-verify
against the web (freshness gate still applies; this doc itself decays).

**Confidence legend:**
- `[V]` = web-verified 2026-07-05 (sources at bottom)
- `[H]` = high — solid in my training prior (through ~Jan 2026)
- `[M]` = medium — training prior, could have shifted since Jan 2026
- `[L]` = low — plausible but verify before acting

**Expiry:** treat every model-name/benchmark claim as stale by ~2027-01; the structural
claims (what pattern won, where the field is going) decay slower (~1 yr).

---

## 1. Autonomous agents + multi-agent orchestration

### What the frontier actually is (2025–26)
- **The harness won, not the framework.** The dominant production pattern is a single
  strong agent in a well-engineered harness (terminal + files + search + subagents),
  i.e. the Claude Code / Codex CLI / OpenHands shape — NOT the 2023–24 "society of agents"
  (AutoGPT/BabyAGI/CrewAI crews). `[H]` Cognition's mid-2025 "Don't Build Multi-Agents"
  essay crystallized this: shared context + linear ownership beats parallel chatty agents
  for most tasks; multi-agent pays off only for READ-heavy parallelizable work
  (research/search fan-out), not WRITE-heavy work (conflicting edits). `[H]`
- **Anthropic's own numbers** (multi-agent research system post, mid-2025): orchestrator +
  parallel subagents beat single-agent by ~90% on breadth-first research evals, at ~15×
  token cost. Multi-agent = a way to spend more tokens for breadth, not free intelligence. `[H]`
- **"Context engineering" replaced "prompt engineering"** as the discipline name and the
  actual lever (Anthropic post, Sept 2025): compaction, sub-agent context isolation,
  just-in-time retrieval, note-taking to files. Your librarian-subagent pattern IS the
  frontier pattern — keep it. `[H]`
- **Protocols standardized:** MCP (Anthropic, Nov 2024) became the universal tool protocol —
  adopted by OpenAI, Google, Microsoft in 2025; donated ecosystem governance is under way. `[H]`
  A2A (Google's agent-to-agent protocol, Apr 2025) was donated to the Linux Foundation. `[H]`
  `AGENTS.md` became a cross-vendor convention for repo-level agent instructions. `[H]`
- **Framework landscape (July 2026):** LangGraph = production standard for stateful,
  auditable graph workflows (Klarna/Uber/LinkedIn scale); Claude Agent SDK (renamed from
  Claude Code SDK, Sept 2025) = the Anthropic-native production path, now with managed
  hosting ("Claude Managed Agents" — Anthropic runs the containers); OpenAI Agents SDK
  (Mar 2025, replaced Swarm) = handoff-centric; Google ADK (Apr 2025). CrewAI = prototyping
  only. `[V]`
- **Durable execution is the missing production piece most teams discover late:** running
  agents on Temporal/Restate/Inngest-style durable workflow engines (retries, resume,
  human-in-loop gates as first-class) is the 2025–26 production pattern for long-horizon
  agents. `[H]`
- **Benchmarks:** SWE-bench Verified is near-saturated at the top (≥75–95% claims) and a
  2026 Berkeley RDI study showed 8 major agent benchmarks (SWE-bench-V, Terminal-Bench,
  WebArena, OSWorld, GAIA…) can be gamed to near-perfect scores without solving tasks —
  treat leaderboard deltas <5pts as noise. `[V]` Terminal-Bench and OSWorld are the
  agentic benchmarks that still discriminate. `[M]`

### Adopt / watch
- ADOPT: context-engineering discipline as explicit design doc for every AIOS agent
  (what enters context, when, compaction policy). Your MANAGEMENT_LOOP/monitor work is this.
- ADOPT: durable-execution semantics for hivemind long-runs (even a poor-man's version:
  checkpointed step ledger + resume — you partly have this in dispatch/receipts).
- WATCH: Claude Managed Agents / hosted agent runtimes — could replace parts of hivemind's
  execution substrate for non-private work.
- For the AGI-witness experiment: the Berkeley RDI gaming result is AMMUNITION for the
  thesis "verification is the binding constraint" — cite it.

### Where Claude's prior is stale
- Believes multi-agent frameworks (AutoGen/CrewAI-style role-play crews) are the frontier →
  they lost; harness + subagent-for-context-isolation won.
- Underweights MCP: it is not "an Anthropic thing", it is THE cross-vendor tool standard.
- May not know A2A, AGENTS.md convention, Agents SDK/ADK, managed agent hosting.
- Believes SWE-bench is a meaningful discriminator at the top — it is saturated AND gameable.

### Pointers
- Cognition "Don't Build Multi-Agents" (2025) — why shared context beats agent swarms.
- Anthropic "How we built our multi-agent research system" (2025) — the 15×-token tradeoff.
- Anthropic "Effective context engineering for AI agents" (Sept 2025) — the discipline.
- LangGraph docs — if AIOS ever needs an external graph runtime instead of homegrown dispatch.
- Berkeley RDI agent-benchmark-gaming study (2026) — verification-gap evidence. `[V]`

---

## 2. Verifiable / certified agent execution, provenance, append-only ledgers

This is a LIVE, crowded 2025–26 field. AIOS/Akashic is not alone — situate or be scooped.

### What the frontier actually is
- **The mature production stack for append-only verifiable logs is the TRANSPARENCY-LOG
  ecosystem, not blockchains:** Certificate Transparency → Trillian → **Sigstore/Rekor**
  (signed artifact provenance, Merkle tree, witnessed checkpoints), tlog-tiles/sunlight
  (cheap static-tile logs), Sigsum (minimal witnessed log). This is exactly the
  "append-only ledger + who-may-write" shape Akashic needs, battle-tested at
  supply-chain scale. `[H]`
- **Trusted-writer problem (your §2c hole) has a named industry answer:** witness
  cosigning / gossip (CT witnesses, Sigsum witnesses, WhatsApp Key Transparency auditors).
  Nobody solves "who certifies the certifier" absolutely; they solve it economically with
  N independent witnesses + monitors. Honest v1 for Akashic = signed writes + external
  witness, not a trust proof. `[H]`
- **Agent identity standardization is moving NOW:** MCP-I (identity extension for MCP)
  was donated to the Decentralized Identity Foundation in March 2026 `[V]`; W3C DID/VC
  applied to agents is the consensus direction `[V]`; ERC-8004 ("trustless agents"
  registry: identity + reputation + validation on Ethereum, late 2025) exists for the
  crypto-flavored version `[H/V]`. OWASP has an Agentic Security Initiative with a threat
  taxonomy (tool poisoning, agent kill-chains). `[H]`
- **Execution attestation tiers (cost-ordered):** (1) signed execution logs / traces —
  cheap, deployable today; (2) TEE attestation (Intel TDX, AMD SEV-SNP, NVIDIA H100/B200
  confidential compute; dstack/Phala for containerized agents) — real and increasingly
  turnkey in 2025–26; (3) zkML (EZKL etc.) — still orders of magnitude too expensive for
  full-model inference proofs; niche. `[H]`
- **Agentic payments forced provenance into production:** AP2 (Google, agent payments
  protocol), x402 (Coinbase), Visa/Mastercard agentic commerce attestation programs
  (2025) — "prove a human principal authorized this agent" is now a commercial
  requirement, with hardware-anchored agent identity roadmaps (e.g. Ledger, 2026). `[V]`
- **Content provenance:** C2PA is the shipped standard (OpenAI, Google, Adobe, camera
  vendors); it is signed-manifest provenance, i.e. the same certificate-chain shape. `[H]`
- **Academic thread matching AIOS exactly:** "From Agent Traces to Trust: A Survey of
  Evidence Tracing and Execution Provenance in LLM Agents" (arXiv 2606.04990, 2026) —
  read it; it is the literature map for Akashic. `[V]` Also AgentSpec (runtime
  enforcement of declarative policies on LLM agents) and guardian-agent architectures. `[V]`

### Adopt / watch
- ADOPT for M3 (Akashic Trust Map): Rekor/Sigsum-style design — Merkle-tree append-only
  log, signed writer identities, checkpoint + independent witness. Do NOT invent a ledger
  format; reuse tlog conventions (verifiable via off-the-shelf tooling).
- ADOPT: frame `aios guard` (H⁰ poison guard) in OWASP-Agentic + tool-poisoning language —
  that's the community that will understand it.
- WATCH: DIF's MCP-I work — if Akashic writer identity is DID-shaped, you interop for free.
- POSITIONING: AIOS's differentiator vs this field is CERTIFICATES ABOUT REASONING
  (answerability/identifiability/consistency), not just execution traces. The field does
  "what the agent did, signed"; nobody ships "what the agent could validly claim, typed."
  That's the honest novelty slot — and it only survives if the D0 witness fires.

### Where Claude's prior is stale
- Thinks "append-only AI ledger" = exotic/blockchain territory → the boring, mature answer
  is transparency logs (Sigstore), and the field standardizing agent identity is DIF/W3C,
  moving in 2026 specifically.
- Doesn't know MCP-I, ERC-8004, AP2/x402, or that agent payments made attestation
  commercial.
- Underestimates TEE maturity: confidential-compute agents are practical now, not research.

### Pointers
- Sigstore/Rekor + Sigsum docs — the ledger design to copy.
- arXiv 2606.04990 (agent execution provenance survey, 2026) — literature map. `[V]`
- AgentSpec (runtime policy enforcement for LLM agents). `[V]`
- OWASP Agentic Security Initiative taxonomy.
- C2PA spec — certificate-manifest design precedent.

---

## 3. Memory / provenance / retrieval for long-horizon agents

### What the frontier actually is
- **Three-way race, all shipped products (2026):** Mem0 (extraction-pipeline memory;
  LOCOMO/benchmark-led), Zep/Graphiti (bi-temporal knowledge graph: every edge carries
  event-time AND ingestion-time), Letta (ex-MemGPT: agent self-manages memory tiers via
  tool calls, filesystem-like paging). Rough 2026 standings: Zep led LongMemEval temporal
  reasoning (63.8% vs Mem0's old 49%), Mem0's 2026 algorithm claims 93.4% (vendor number —
  discount). `[V]`
- **File-based memory won the simplicity war:** Claude Code's CLAUDE.md/auto-memory and
  Letta's filesystem tiers show "memory = markdown files + grep + an agent that curates
  them" is competitive with vector stores for agent memory. memoryOS's draft-first .md
  objects are on-pattern. `[H]`
- **Retrieval frontier moved past vanilla vector RAG:** agentic retrieval (the model
  searches iteratively) > one-shot RAG; hybrid graph+vector (GraphRAG → LazyGraphRAG for
  cost); late-interaction (ColBERT/ColPali for documents); rerankers standard. Long
  context (1M-token tiers on Gemini and Claude Sonnet since 2025) did NOT kill retrieval —
  "context rot" (recall degradation with context length; Chroma's 2025 study) keeps
  retrieval + curation necessary. `[H]`
- **Bi-temporal modeling is the key idea worth stealing:** distinguishing "when was this
  true" from "when did we learn it" (Graphiti) is exactly what a provenance-first memory
  needs for supersession/invalidation — memoryOS should have both timestamps on every
  accepted memory. `[H]`
- **Benchmarks to test against:** LongMemEval, LOCOMO (flawed but standard), DynamicMem
  (2026, real-world long-horizon). Categories now include abstention and contradiction
  resolution — directly APEX/DescentNet-shaped. `[V]`
- **Embeddings/rerankers (open):** Qwen3-Embedding + Qwen3-Reranker are the strong open
  default; Voyage (now Anthropic-adjacent `[M]`) and Cohere lead closed. `[M]`

### Adopt / watch
- ADOPT: bi-temporal timestamps (event-time, ingest-time) in memoryOS record schema — cheap
  now, painful to retrofit.
- ADOPT: run memoryOS against LongMemEval/DynamicMem's contradiction + abstention
  categories — it's the external validation M5 needs, and DescentNet's H¹ story maps to
  "contradiction resolution" there.
- WATCH: Letta's agent-curated-memory pattern as the model for how memoryOS drafts get
  proposed autonomously (still draft-first on accept).

### Where Claude's prior is stale
- Default belief "agent memory = vector DB + RAG" → frontier is temporal KG + file-based
  curation + agentic retrieval; vanilla RAG is the 2023 answer.
- May not know Graphiti/Zep bi-temporality, LongMemEval, DynamicMem, LazyGraphRAG, or the
  context-rot result (may over-trust long context).
- May think MemGPT is a paper — it's a company (Letta) with a shipped runtime.

### Pointers
- Zep "Graphiti" (temporal KG memory) — bi-temporal schema to copy.
- LongMemEval + DynamicMem (arXiv 2606.22877) — the eval targets. `[V]`
- LazyGraphRAG (Microsoft) — graph-RAG quality at ~0.1% of GraphRAG index cost. `[H]`
- Chroma "context rot" report (2025) — why long context ≠ memory. `[H]`

---

## 4. Applied category theory / Poly / sheaves for composing agents

### What the frontier actually is (sober read)
- **Who's real:** Topos Institute (Spivak — *Polynomial Functors: A Mathematical Theory of
  Interaction* with Niu; Myers — double-categorical systems theory; Patterson/Carlson —
  CatColab, AlgebraicJulia). Categorical cybernetics group (Hedges, Capucci, Gavranović —
  open games, parametrized optics, "Towards Foundations of Categorical Cybernetics").
  Gavranović et al. "Categorical Deep Learning" (2024, with DeepMind coauthors) — monad
  algebras as the generalization of geometric DL. Sheaf side: Hansen–Ghrist sheaf
  Laplacians; sheaf neural networks (Bodnar et al.); Robinson's logical sheaves for data
  fusion (the direct DescentNet ancestor). `[H]`
- **Usable software exists but is thin:** AlgebraicJulia (Catlab/GATlab — computational
  category theory that actually runs), CatColab (Topos' collaborative formal modeling tool,
  2024–25, web-based), DisCoPy (string diagrams in Python). None is production agent
  infrastructure; all are modeling/spec tools. `[H]`
- **2025–26 saw LLM×categories papers** (e.g. "Topos Theory for Generative AI and LLMs",
  Mahadevan) but these are frameworks-in-search-of-experiments — no demonstrated
  performance edge from ACT in any deployed agent system as of my knowledge. `[H]`
- **Honest verdict for M1b:** the panel's "taxonomy masquerading as unification" risk is
  the SAME risk this whole field carries. Poly gives you: typed interaction protocols
  (interfaces as polynomials, wiring diagrams as composition), and a principled place to
  put "certificate restricts another component's search space" (as a morphism constraint).
  Use it as a SPECIFICATION LANGUAGE + type discipline, and claim only that — the gating
  of M1b on the D0 witness is exactly right. Nobody will scoop a *validated*
  cert-composition law; several groups could scoop an *unvalidated formalism* (they
  already publish those monthly).

### Adopt / watch
- ADOPT (if D0 fires): write the composition law in Poly/optics vocabulary — reviewers
  from Topos/categorical-cybernetics circles exist and will engage; it's the only
  community with matching priors.
- ADOPT now (cheap): wiring-diagram discipline for AIOS organ seams — even informally,
  "every seam is a typed interface" catches the unwired-organ class of bug M0 found.
- WATCH: CatColab as a founder-facing modeling surface; Gavranović's categorical DL line.

### Where Claude's prior is stale
- Likely knows Spivak/poly book and open games; likely does NOT know CatColab, the 2024
  Categorical Deep Learning position paper, or the 2025–26 LLM×topos papers.
- May either over-romanticize ACT (unification aesthetics) or dismiss it; the calibrated
  position is "spec language with a live niche community; zero demonstrated agent-system
  performance wins; formalize only after empirical witness."

### Pointers
- Niu & Spivak, *Polynomial Functors* (arXiv 2312.00990) — the Poly reference. `[V]`
- Capucci/Gavranović/Hedges/Rischel, "Towards Foundations of Categorical Cybernetics". `[V]`
- Gavranović et al., "Categorical Deep Learning" (2024). `[H]`
- Hansen & Ghrist sheaf Laplacian papers + Robinson data-fusion sheaves — DescentNet's
  citation spine. `[H]`
- AlgebraicJulia / CatColab — the only running code in this space. `[H/V]`

---

## 5. The MODEL landscape (as of 2026-07, web-verified where marked)

### Frontier closed tier
- **Anthropic:** Claude Fable 5 (me) — current coding leader (~94.7 weighted coding,
  ~95% SWE-bench-V claims) `[V]`; Claude Mythos 5 / Mythos Preview — reasoning line,
  entered as new coding leader on some boards `[V]`. Lineage before that: Opus/Sonnet 4.5
  (late 2025), Sonnet 4.5 still tops some agentic boards. `[V]`
- **Google:** Gemini 3.1 Pro — strongest head-to-head coding-arena play, ~93.2 coding
  `[V]`; Gemini 3 launched Nov 2025 with 1M+ context. `[H]`
- **OpenAI:** GPT-5 launched Aug 2025 (unified router over reasoning tiers, absorbed the
  o-series); GPT-5.x iterations through 2026. `[H]` Exact current top OpenAI model name
  as of July 2026: verify — my prior ends at GPT-5.1-era. `[M]`
- **xAI:** Grok 4 (July 2025), Grok 4.x since. `[M]`
- Pricing collapsed ~10× 2024→2026 at equal capability; assume any cached price is wrong. `[H]`

### Open-weights tier (Chinese labs dominate — this is the single biggest prior-gap)
Per July-2026 boards `[V]`:
- **DeepSeek V4 / V4 Pro** — open-weights overall leader (~87 BenchLM open board); best
  perf-per-inference-cost for self-hosting; MIT-licensed lineage.
- **GLM-5 / 5.1 / 5.2** (Zhipu) — long-horizon coding bet; MIT license = enterprise
  differentiator.
- **Kimi K2.6 / K2.7-Code** (Moonshot) — agentic/long-horizon specialists; K2.6 built for
  sub-agent parallelism; K2 line hit 71.6% SWE-V back in 2025.
- **Qwen3.5-397B / Qwen 3.6** (Alibaba) — Qwen 3.6 = compact MoE, single-GPU, strong
  tool-calling + vision; Qwen3-Coder-480B was the 2025 open coding SOTA (69.6% SWE-V,
  Apache-2.0).
- **MiniMax M3**, **Nemotron 3 Super/Ultra-550B** (NVIDIA, on NIM free tier — you already
  use these) round out the tier.
- **Meta/Llama is effectively OUT of the frontier race** — Llama 4 (Apr 2025)
  disappointed, Behemoth shelved, org rebuilt as a superintelligence lab with unclear
  open-weights commitment. Do not reach for Llama by habit. `[H]`

### Local tier (this box: dual RTX 5090, 64GB VRAM)
- Current local stack (qwen3-coder:30b, qwen2.5-coder-7/14b, phi4-mini) is one generation
  behind: check ollama/HF for **Qwen 3.6 compact MoE**, **Gemma 4 26B**, **Phi-4.5/5**,
  **GLM-5-Air-class distills**, and K2.7-Code quantizations — likely strict upgrades for
  agentic local work. `[V/M]` (exact ollama availability unverified).
- llama.cpp/ollama + vLLM/SGLang all handle Blackwell (sm_120) properly on current builds;
  the torch-2.6 kernel gap in your notes is a stale pin, not a platform truth. `[M]`

### Meta-point on benchmarks
Leaderboards are gameable (Berkeley RDI 2026 `[V]`); LMArena-style preference boards are
style-biased. For model CHOICE, run your own 20-task harness eval (you have the
infrastructure); use boards only for shortlisting.

### Where Claude's prior is stale (concretely)
- "Qwen2.5 / Llama-3.x are the top open models" → wrong by 3+ generations; the open tier
  is DeepSeek-V4 / GLM-5.x / Kimi-K2.x / Qwen3.5–3.6 / MiniMax-M3.
- "GPT-4o/o1 are OpenAI's frontier" → superseded by GPT-5 line (Aug 2025).
- "Gemini 1.5/2.0" → Gemini 3.x era.
- Unaware Claude's own current line is Fable/Mythos 5 (post-4.5 naming shift).
- Assumes US labs own the open-weights frontier → it's Chinese labs, decisively, since
  DeepSeek-R1 (Jan 2025) and continuously after.

---

## 6. Tool/library landscape for agentic + verification systems

### Agent harnesses / CLIs `[H]`
Claude Code + Claude Agent SDK (the production Anthropic path), OpenAI Codex CLI, Gemini
CLI, OpenHands (open, research-standard), Aider, Cline, opencode. Harness quality moves
end-task success more than ±1 model tier — invest there.

### Orchestration / durability
LangGraph (graphs, production standard `[V]`); **Temporal** (durable execution — the
"agents as workflows with resume/retry/human-gates" pattern; Restate/Inngest lighter
alternatives) `[H]`. If hivemind ever needs industrial-grade run durability, wrap runs in
Temporal rather than extending homegrown retry logic.

### Evals / observability
- **Inspect AI** (UK AI Safety/Security Institute) — the serious open eval framework for
  agentic tasks; composable solvers/scorers, sandboxing. ADOPT for M5 and the D0 witness
  experiment — it gives you credibility + reuse. `[H]`
- Langfuse (OSS) / LangSmith / W&B Weave for tracing; **OpenTelemetry GenAI semantic
  conventions** are becoming the neutral trace schema — emit OTel-compatible traces from
  hivemind and every observability tool works. `[H]`
- promptfoo, DeepEval for cheap regression evals. `[H]`

### Guardrails / policy / sandboxing
Llama Guard 3/4 + NeMo Guardrails + Guardrails-AI (validation), Lakera (commercial
firewall) `[V]`; AgentSpec (declarative runtime policies — closest academic artifact to
aios guard's lane) `[V]`. Sandboxing: E2B / Modal for cloud code-exec; Firecracker
microVMs; bubblewrap/landlock locally; Anthropic open-sourced its sandbox-runtime
approach (late 2025) `[M]`.

### Structured output / serving
Grammar-constrained decoding is a solved commodity: **outlines / xgrammar / llguidance**
(near-zero overhead) — never parse free text where a schema exists; this is the cheapest
"certificate" there is (type-valid output by construction). `[H]` Serving: vLLM (V1
engine) and SGLang are the two open standards; ollama/llama.cpp for local. `[H]`

### Formal / verified reasoning
- **Lean 4 + mathlib is the verified-reasoning substrate that won**: AlphaProof (IMO
  silver 2024), Harmonic's Aristotle, DeepSeek-Prover-V2 (open, 2025), Goedel-Prover.
  If APEX certificates ever need machine-checked cores, target Lean 4. `[H]`
- SMT (Z3/cvc5) unchanged and still the workhorse for policy/constraint checking.
- NN verification (α,β-CROWN) still doesn't scale to LLMs — don't wait for it; the
  practical certification layers are statistical (conformal, §7) + logged provenance (§2).

### Where Claude's prior is stale
- May not know Inspect AI, xgrammar/llguidance, OTel GenAI conventions, vLLM-V1/SGLang
  duopoly, Temporal-for-agents pattern, or that grammar-constrained decoding is now free.
- May suggest LangChain (the original) — treat as legacy; LangGraph is the maintained lane.

---

## 7. Identifiability / selective prediction / conformal / answerability (APEX–IRIS math)

### What the frontier actually is
- **Conformal moved from token-toys to AGENT TRAJECTORIES.** The 2024–26 arc:
  conformal risk control (Angelopoulos et al.) → conformal factuality (Mohri & Hashimoto
  2024: prune claims until retained set has guaranteed factuality) → conformal abstention
  for LLMs (Yadkori et al., DeepMind 2024) → **2026: conformal risk control for tool-use
  and retrieval drift in agent pipelines (ToolChain-CRC, arXiv 2606.18467)** and
  conformal LLM-judging (SCOPE) and conformal Elo for calibrated rankings. `[V]`
  ToolChain-CRC is the closest published object to "APEX as an agent-runtime gate" — read
  it FIRST, position against it.
- **Abstention got benchmarked:** AbstentionBench (Meta, 2025) — LLMs, including
  reasoning models, are systematically bad at unanswerable questions; reasoning
  fine-tuning DEGRADES abstention. This is the empirical wedge APEX exists for; cite it
  as motivation. `[H]`
- **Uncertainty signals:** semantic entropy (Farquhar et al., Nature 2024) + cheap probe
  variants remain the standard hallucination-uncertainty measure; 2026 result: "entropy
  alone is insufficient for safe selective prediction" (arXiv 2603.21172) — supports
  APEX's typed-certificate framing over scalar-confidence framing. `[V]`
- **Theory constraints to respect (unchanged but Claude may under-cite):** exact
  conditional coverage is impossible (Foygel Barber et al.); exchangeability breaks under
  generation recursion and distribution shift — the fixes are online/adaptive conformal
  (Gibbs & Candès) and non-exchangeable CP (Barber et al. 2023). Any APEX guarantee must
  say WHICH coverage (marginal/group/online) it delivers. `[H]`
- **Learned abstention:** RL-learned adaptive thresholds over conformal scaffolds (CAP,
  2026) beat static thresholds `[V]` — matches the panel's "the composition must be
  learned, not static" caveat on the D0 witness; same lesson, independent field.
- **Identifiability (IRIS side):** the live field is **causal representation learning**
  (Schölkopf/Bengio program): identifiability of latents from interventions/multi-views
  (von Kügelgen et al. 2023–24; sparse-mechanism-shift results). "What does a measurement
  record identify" is now theorem-shaped in CRL — IRIS should cite and map its
  "decoherence classes" onto CRL's observational-equivalence classes or it will look
  reinvented (the panel already flagged this). `[H]`

### Adopt / watch
- ADOPT: implement APEX runtime gates as conformal-risk-control over agent steps
  (ToolChain-CRC pattern) — published math, direct fit, and it makes the certificate's
  guarantee precise (α-level risk on accepted actions).
- ADOPT: AbstentionBench + LongMemEval-abstention as external evals for APEX certificates.
- ADOPT: verified-solve-per-FLOP metric in D0 already matches how this literature scores
  selective systems (risk–coverage curves) — report risk–coverage alongside it.
- WATCH: conformal under drift/agency (the exchangeability frontier) — this is where a
  genuine APEX theory contribution could land, because agent loops violate every classical
  assumption and the field knows it.

### Where Claude's prior is stale
- Believes conformal-for-LLMs ≈ classification sets on MCQ → the field now does risk
  control on factuality, tool-calls, judging, and trajectories, with 2026 papers on
  exactly the agent-pipeline case.
- May not know AbstentionBench, semantic-entropy-probes, CAP-style learned abstention,
  ToolChain-CRC, or conformal Elo.
- May treat identifiability as Pearl-only → the operational 2025–26 frontier is CRL
  identifiability results, which is the right home for IRIS.

---

## Cross-cutting: what would change this team's plans (ranked)

1. **M3/Akashic:** copy transparency-log (Rekor/Sigsum) design + witness cosigning; align
   writer identity with DID/MCP-I. Saves months and buys interop + credibility. (§2)
2. **APEX:** rebase the runtime gate on conformal risk control (ToolChain-CRC); adopt
   AbstentionBench. Turns a taxonomy into a guarantee. (§7)
3. **D0 witness experiment:** run it in Inspect AI; report risk–coverage + verified-solve
   -per-FLOP; cite Berkeley RDI benchmark-gaming as motivation. (§1, §6, §7)
4. **memoryOS:** add bi-temporal timestamps now; eval on LongMemEval/DynamicMem
   contradiction+abstention tracks. (§3)
5. **Model habits:** stop defaulting to Qwen2.5/Llama-era picks; the open tier is
   DeepSeek-V4/GLM-5.x/Kimi-K2.x/Qwen3.5+; refresh the local ollama stack. (§5)
6. **M1b:** keep it gated on D0 — the ACT field's own failure mode (formalism without
   witness) confirms the gating. (§4)

## Standing epistemic warnings about THIS document
- My training ends ~Jan 2026; `[V]` items were spot-checked 2026-07-05 via web search —
  but vendor benchmark numbers (Mem0's 93.4%, SWE-V ~95%) are self-reported/gameable.
- I share LLM failure modes: I can confabulate paper IDs and version numbers. Every arXiv
  ID marked `[V]` came from live search results; `[H]/[M]` citations should be
  re-searched before being cited externally.
- Heterogeneous ≠ correct: I de-bias Claude's prior, I don't replace verification.

## Sources (web check, 2026-07-05)
- [BenchLM coding leaderboard](https://benchlm.ai/coding) · [SWE-bench](https://www.swebench.com/) · [llm-stats SWE-V agentic](https://llm-stats.com/benchmarks/swe-bench-verified-(agentic-coding))
- [Open-source LLMs 2026 (HF blog)](https://huggingface.co/blog/daya-shankar/open-source-llms) · [BenchLM best open source](https://benchlm.ai/blog/posts/best-open-source-llm) · [Kilo open coding models](https://kilo.ai/open-source-models)
- [Agent framework comparison 2026 (Morph)](https://www.morphllm.com/ai-agent-framework) · [LangChain framework roundup](https://www.langchain.com/resources/ai-agent-frameworks) · [Alice Labs 2026 comparison](https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026)
- [Agent execution provenance survey (arXiv 2606.04990)](https://arxiv.org/pdf/2606.04990) · [AI agent identity standards (arXiv 2604.23280)](https://arxiv.org/pdf/2604.23280) · [ERC-8004 (Ledger glossary)](https://www.ledger.com/academy/glossary/erc-8004) · [Ledger 2026 AI security roadmap](https://www.ledger.com/blog-2026-ai-security-roadmap)
- [ToolChain-CRC (arXiv 2606.18467)](https://arxiv.org/pdf/2606.18467) · [Entropy insufficient for selective prediction (arXiv 2603.21172)](https://arxiv.org/pdf/2603.21172) · [Conformal abstention overview](https://www.emergentmind.com/topics/conformal-abstention) · [CP for NLP survey (TACL)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00715/125278/Conformal-Prediction-for-Natural-Language)
- [Poly book (arXiv 2312.00990)](https://arxiv.org/pdf/2312.00990) · [Topos Poly course](https://topos.institute/events/poly-course/) · [Topos theory for GenAI (arXiv 2508.08293)](https://arxiv.org/pdf/2508.08293)
- [Agent memory frameworks tested 2026](https://particula.tech/blog/agent-memory-frameworks-tested-mem0-zep-letta-cognee-2026) · [DynamicMem (arXiv 2606.22877)](https://arxiv.org/pdf/2606.22877) · [Mem0 state of agent memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Galileo guardrails 2026](https://galileo.ai/blog/best-ai-agent-guardrails-solutions) · [Straiker runtime security](https://www.straiker.ai/blog/top-7-ai-runtime-security-platforms)
