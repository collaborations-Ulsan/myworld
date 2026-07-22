# AIOS Absorption Scan — 2026-07-22 (Grok Build · Kimi K3 · OSS delta)

> Grounded live on 2026-07-22 (WebSearch + WebFetch + GitHub API + HF hub). All model/
> license/price/date claims cite a URL below; none are from training memory (Grok Build and
> Kimi K3 both post-date the Jan-2026 cutoff). Builds on — does not redo —
> `docs/AIOS_OSS_ABSORPTION_SURVEY_2026-07-10.md` (nanobot / OpenHands / mini-swe-agent /
> smolagents / ShinkaEvolve / TreeQuest already assessed; bash-loop, TreeQuest escalation,
> MCP client, skills loader already absorbed). This file = the DELTA + the Grok/Kimi angle.
>
> **D7 decorrelation law applied throughout:** a candidate earns a slot only if it adds a
> DECORRELATED capability (independent weights, or a capability layer AIOS lacks), not if it
> is one more correlated frontier coding-CLI wrapper of patterns AIOS already holds.

---

## TL;DR

**Grok Build verdict — SPLIT: absorb the *model*, skip the *code*.**
`xai-org/grok-build` is genuinely OSS (Apache-2.0) but is 844K lines of Rust, single-commit,
non-contributory, and CORRELATED with coding-CLI patterns AIOS already has → skip the harness.
The decorrelated win is `grok-build-0.1` (xAI weights) as a cheap/fast API arm in the cascade.
Carries a loud security lesson (see §Grok).

**Kimi K3 verdict — NIM/API-only; NOT a local model; skip-as-local.**
2.8T total params (MoE, 1M ctx, Modified MIT, weights drop ~2026-07-27) physically cannot load
on dual RTX 5090 / 64 GB (even 1-bit ≈ 350 GB). It is a decorrelated Moonshot *arm* for the
cascade via API/NIM — and `kimi-k2.6` is **already on NVIDIA NIM** today, so that is the
absorb-now Moonshot substrate; K3 joins when it lands on NIM.

**Ranked top-5 absorb-next**

1. **Weaver distilled 400M cross-encoder + weak-verifier ensembling** (Stanford HazyResearch, MIT) — a cheap LOCAL verifier that drops straight into AIOS's already-built escalate seam. The verification/decorrelation moat, made real and provider-independent. **[#1]**
2. **kimi-k2.6 via NVIDIA NIM** (Moonshot, Modified MIT) — decorrelated arm independent of *both* US frontier labs *and* Qwen; available now. K3 (2.8T) via API/NIM when weights land ~07-27.
3. **grok-build-0.1 via OpenRouter/xAI API** ($1/$2 per M tok, 256K ctx, OpenAI-compat) — cheap, fast, decorrelated xAI arm for high-volume/parallel generation; trivial config-add to the existing provider harness.
4. **LLMRouter** (ulab-uiuc, MIT, 2.1k★, pip, OpenAI-compat, local+NIM+Anthropic) — a *learned* router over the decorrelated substrate pool; upgrades CapabilityOS's heuristic routing to measured routing.
5. **Grok Build "Arena Mode" + ACP concept** (from `xai-org/grok-build`, Apache-2.0) — the parallel-competing-outputs-then-auto-eval pattern feeds the verification layer; ACP for editor embedding. Concept absorb, not code.

---

## Grok Build (xAI / "SpaceXAI") — full verdict

**Status: OSS confirmed, Apache-2.0 — but code is a SKIP, model is an ABSORB.**

- **Repo:** https://github.com/xai-org/grok-build — Apache-2.0, **99.6 % Rust, ~844,530 lines**, published **2026-07-15** as a *single commit with no history*, "periodically synced from the SpaceXAI monorepo," **external contributions not accepted**. (github; https://simonwillison.net/2026/Jul/15/grok-build/ ; https://www.marktechpost.com/2026/07/15/spacexai-open-sources-grok-build-the-rust-agent-harness-tui-and-tool-layer-behind-its-coding-cli/ ; https://www.opensourceforu.com/2026/07/xai-open-sources-grok-build-after-repository-upload-controversy/ )
- **What's inside:** agent harness (context assembly, response parsing, tool-call dispatch), TUI (rendering, input, plan review, inline diff viewer), tool layer (file read/edit/code search), extension system (**skills, plugins, hooks, MCP servers, subagents**), and **ACP** — "embedded in editors via the Agent Client Protocol." (marktechpost; github README)
- **Timeline:** beta 2026-05-14 (SuperGrok Heavy, $299/mo), general 2026-05-25 (SuperGrok / X Premium+). (https://www.buildfastwithai.com/blogs/grok-build-xai-cli-ai-agents-2026 ; https://www.digitalapplied.com/blog/xai-grok-build-cli-parallel-coding-agents )
- **⚠ Security lesson (load-bearing for AIOS):** xAI open-sourced Grok Build *reactively, after backlash* that the CLI **secretly uploaded users' complete Git repositories — commit history plus credentials (API keys, SSH keys, cloud tokens, DB passwords)**. (https://the-decoder.com/xai-open-sources-grok-build-on-github-after-massive-data-breach/ ; https://alternativeto.net/news/2026/7/xai-has-open-sourced-grok-build-after-backlash-over-secretly-uploading-users-repositories/ ) → This is the concrete adversary case for AIOS's inviolable privacy boundary (`_from_desktop/`, `dain/`, `minyoung/`, secrets, raw exports). Absorbable as a **negative capability / red-team fixture**: prove AIOS's tool layer never exfiltrates repo state to a provider.

**The model (the actual absorb):**
- `grok-build-0.1` (aliases `grok-code-fast-1`), released **2026-05-20**, **$1 / M input, $2 / M output, 256K ctx**, on **OpenRouter + Vercel AI Gateway**, OpenAI-compatible, `base_url` configurable. (https://openrouter.ai/x-ai/grok-build-0.1 ; https://x.ai/news/grok-build-0-1 )
- **NVIDIA NIM:** not confirmed for grok models (xAI hosts its own; OpenRouter is the neutral path).
- **Community quality verdict (grounded):** SWE-bench Verified (vendor-reported) — **Codex CLI (GPT-5.5) 88.7 %, Claude Code (Opus 4.7) 87.6 %, Grok Build coder 70.8 %**. Grok's play is *parallel breadth* (up to 8 concurrent agents, plan/search/build, "Arena Mode" auto-eval of competing outputs), best for high-volume iteration and large monorepos when token cost matters; consensus is **early-beta, exploratory, not a production default** — Claude Code remains that. (https://codersera.com/blog/grok-build-vs-claude-code-vs-codex-cli-2026/ ; https://aitoolgrade.com/blog/grok-build-vs-codex-vs-claude-code-2026.html ; https://www.buildthisnow.com/blog/tools/extensions/grok-build-vs-claude-code )

**Absorb / skip breakdown**

| Piece | Verdict | Why |
|---|---|---|
| `grok-build-0.1` model as cascade arm | **ABSORB (API)** | Decorrelated xAI weights; cheap/fast/256K; OpenAI-compat → 1 config entry in `aios_provider.py`. Use as cheap-tier / parallel generator, **not** as top verifier (70.8 % < 88 %). |
| Rust harness / TUI / tool layer | **SKIP (code)** | Apache-2.0 but Rust, 844K lines, single-commit, non-contributory; CORRELATED with nanobot/Claude-Code patterns AIOS already absorbed. |
| Arena Mode (parallel + auto-eval) | **ABSORB (concept)** | Feeds the verification layer — competing outputs scored by a verifier = exactly AIOS's escalate organ. |
| ACP (Agent Client Protocol) | **Candidate** | Editor-embedding surface AIOS lacks; note for a future IDE seam. |
| Grok Skills = SKILL.md-compatible? | **HYPOTHESIS-GRADE** | Extension taxonomy (skills/plugins/hooks/MCP/subagents) matches Claude Code, but exact SKILL.md interop is **not confirmed** in reachable sources — deferred to `docs.x.ai/build/overview`. Do not assume drop-in skill portability yet. |

---

## Kimi K3 (Moonshot AI) — full verdict

**Status: API-only today; open weights ~2026-07-27; NOT locally runnable → skip-as-local, absorb-as-arm.**

- **Params / arch:** **2.8T total parameters**, Mixture-of-Experts, **1M-token context**, native multimodal, always-on thinking. Largest open-weight model shipped to date. (https://www.tomshardware.com/tech-industry/artificial-intelligence/moonshot-releases-2-8-trillion-parameter-kimi-k3 ; https://felloai.com/kimi-k3/ ; https://codersera.com/blog/kimi-k3-complete-guide-2026/ ) *Active-param count per token not yet pinned in public sources (K2.6 = 1T total / 32B active for reference); immaterial to the local verdict.*
- **License:** **Modified MIT** (Moonshot's open-weight lineage). (https://www.labellerr.com/blog/kimi-k3-world-first-open-2-8t-ai-model/amp/ ; https://www.layer3labs.io/open-weights/kimi-k3-open-weights-guide )
- **Dates:** live via app/API **2026-07-16**; **full open weights by ~2026-07-27** (not released as of this scan — HF search returns no `moonshotai/Kimi-K3` repo yet, consistent). (https://simonwillison.net/2026/Jul/16/kimi-k3/ )
- **API/NIM:** OpenRouter **$3 / M in, $15 / M out, 1M ctx**; **`kimi-k2.6` already on NVIDIA NIM** (build.nvidia.com, Modified MIT); K3-on-NIM likely-follows but unconfirmed. (https://openrouter.ai/moonshotai/kimi-k3 ; https://build.nvidia.com/moonshotai/kimi-k2.6/modelcard )

**Local runnability (dual RTX 5090 / 64 GB): IMPOSSIBLE — honest negative.**
2.8T total weights: FP8 ≈ 2.8 TB, 4-bit ≈ 1.4 TB, 1-bit ≈ 350 GB. All ≫ 64 GB VRAM (and ≫ typical local disk-to-VRAM budgets). MoE sparsity cuts *compute* per token, not the *resident weight* footprint. **Cannot quantize onto this box.** vs `qwen3-coder:30b`: not a comparison — K3 is a frontier-class API model, not a local student/teacher. AIOS's local student stays `qwen3-coder:30b`; K3/K2.6 enter only as a heterogeneous *API/NIM verify-or-generate arm*.

**Absorb path:** add `kimi-k2.6` (now) and `kimi-k3` (post-07-27) as NIM/OpenRouter arms in the escalate `generators` pool and the multi-substrate review lane — a Moonshot head that is **decorrelated from both the US frontier cluster and Alibaba/Qwen**, strengthening provider-death resilience. No local integration.

---

## The verification / routing / decorrelation LAYER (this session's moat)

### #1 — Weaver (weak-verifier ensembling + distilled 400M cross-encoder)
- **Repo:** https://github.com/HazyResearch/scaling-verification — **MIT** (confirmed via GitHub API). Stanford Hazy Research / Scaling Intelligence (Saad-Falcon et al.), arXiv **2506.18203**, NeurIPS 2025. Models+datasets: https://huggingface.co/collections/hazyresearch/weaver-683798010b39c9653ddb9bd8
- **What it is:** combine many *weak* verifiers (70B-or-smaller judge + reward models) via **weak supervision** to estimate each verifier's accuracy → a single weighted score; weighted ensembles ≫ unweighted. Reaches o3-mini-level accuracy (86.2 %) with a Llama-3.3-70B generator + small-verifier ensemble. (https://scalingintelligence.stanford.edu/pubs/weaver/ ; https://hazyresearch.stanford.edu/blog/2025-06-18-weaver )
- **The killer piece for AIOS:** they **distill a 400M cross-encoder** on Weaver's combined scores — a cheap verifier that **runs locally on the 5090s (or CPU)**, provider-independent. That is a *decorrelated capability layer*, not another generator.
- **Sibling to note (same lab):** `ScalingIntelligence/Archon` — combines inference-time techniques + LMs from one JSON config; a routing/composition scaffold worth a later look.

### #4 — LLMRouter (learned routing over the pool)
- **Repo:** https://github.com/ulab-uiuc/LLMRouter — **MIT, ~2.1k★**, actively updated (TSRouter 2026-07, RouteProfile 2026-05). `pip install llmrouter-lib`; OpenAI-compatible **drop-in `/v1/chat/completions`**; routes across **local (Ollama/vLLM/SGLang) + API (NVIDIA/OpenAI/Anthropic)**; 16+ routers across single/multi-round/multimodal/agentic/personalized categories.
- **vs RouteLLM (lm-sys):** RouteLLM is the mature baseline (drop-in OpenAI, ~85 % cost cut at 95 % GPT-4 quality); LLMRouter is the broader, more actively-developed research library and already speaks NIM + Anthropic + local. **Take LLMRouter** as the learned-routing layer; keep RouteLLM as the cost-router reference.
- **Decorrelation note:** routing is *partly* correlated with CapabilityOS's existing recommender, but *learned/measured* routers are an upgrade over heuristics — and the point of routing here is to **maximize substrate decorrelation** in the escalate pool, which is the moat.

---

## Honest negatives — NOT worth absorbing

- **`xai-org/grok-build` Rust codebase** — Apache-2.0 but 844K LOC Rust, single-commit, non-contributory, correlated with patterns already absorbed. Model yes, code no.
- **Kimi K3 as a local model** — physically impossible on 64 GB (2.8T). Not a `qwen3-coder:30b` replacement.
- **Google ADK 2.0 / Mastra / LangGraph / Haystack** — correlated graph-orchestration wrappers; AIOS already has `aios_turn_loop` + dispatch. Pattern-reference only. (https://www.shakudo.io/blog/top-9-ai-agent-frameworks )
- **MolTrust (blockchain Verifiable Credentials for agents)** — niche, off-thesis.

## Hypothesis-grade / verify before acting

- **Grok Skills ↔ SKILL.md exact compatibility** — taxonomy matches; interop unconfirmed (see §Grok).
- **K3 on NVIDIA NIM** — K2.6 is live on NIM; K3 expected to follow, not yet confirmed.
- **Microsoft Agent Governance Toolkit** (MIT, 2026-04-02, OWASP Agentic Top-10, Python/TS/Rust/Go/.NET) — a governance/security layer AIOS is thin on; the Grok repo-upload breach makes agent-exfiltration governance concretely relevant. **Candidate**, fit-to-AIOS unverified. (https://theaiengineer.substack.com/p/the-open-source-agent-toolkit-in )

---

## #1 smallest integration path — Weaver → AIOS escalate verifier

AIOS already built the seam. `scripts/aios_escalate.py` (the AB-MCTS/TreeQuest escalation organ,
prior-absorbed) is `EscalationOrgan(generators, score_fn)` where
`ScoreFn = Callable[[str], float]` returns a score in [0, 1] — but it currently ships
`_demo_scorer` (line 374: *"a length-capped heuristic, NOT a real verifier … callers MUST inject
a domain score_fn"*). **AIOS's single biggest missing organ is a real verifier. Weaver is it.**

1. `git clone` HazyResearch/scaling-verification (MIT); pull the **distilled 400M cross-encoder** from the Weaver HF collection.
2. Serve it locally (400M → trivial on either 5090, or CPU) behind `score(query, answer) -> float ∈ [0,1]`.
3. **Inject it as `score_fn` into `EscalationOrgan`**, replacing `_demo_scorer`. No new plumbing — the constructor argument already exists. (Second seam: `aios_turn_loop.py` Pillar-3 "execution-time plan verification & repair," line ~445.)
4. Populate the same organ's `generators` dict with the **decorrelated arms** from this scan: `{ local qwen3-coder:30b, NIM kimi-k2.6, grok-build-0.1 (OpenRouter), claude, codex }`. Candidates #1/#2/#3 compose into ONE organ — Weaver = the scorer, the independent-lab models = the generators.
5. *(Then, the moat proper)* stack a **weak-supervision ensemble** of weak verifiers — local cross-encoder + a NIM judge + a reward model — weighted per Weaver, for a decorrelated verifier ensemble.
6. **Verification / provider-death EARN:** run the escalate organ on the DriftBench / offline task set with **local generator + local Weaver verifier only** (no provider CLI, no NIM). If the local verifier catches errors the `_demo_scorer` heuristic misses, the "provider-death-resilient verified loop" claim is earned, not asserted.

Effort: ~2–4 days (model-serving wrapper + `score_fn` adapter + offline eval). Load-bearing, minimal, and it turns the moat from a slogan into a running organ.

---

*Sources are inline above; stars / licenses / prices / dates verified live 2026-07-22 (WebSearch,
WebFetch, GitHub API, HF hub). Aggregator/secondary sources are flagged hypothesis-grade where
primary confirmation was unreachable.*
