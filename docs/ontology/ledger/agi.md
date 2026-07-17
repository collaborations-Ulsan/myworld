# Frontier Knowledge Ledger — D1: AGI / foundation capability

**Schema**: `docs/ontology/FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md` §1 (unified). **Data**: `agi.json`.
**Status**: draft-first (append; not accepted — DNA #2). **Populated**: 2026-07-17 by claude@myworld (wave-1 deep).
**Grounding**: built ON the three radar sweeps (cited inline) + fresh WebSearch/HF paper_search this session.
Nodes tagged `grade:hypothesis` are aggregator/blog/self-reported; `grade:primary` are arxiv/venue/first-party.

**Counts**: 143 nodes (42 papers/artifacts, 20 people, 13 orgs, 15 concepts, 11 methods, 6 methodologies,
6 benchmarks, 27 claims, 2 model-classes) · 127 edges incl. **12 `contradicts`** (the frontier's disagreements).

---

## 1. Sub-area map (what D1 decomposes into)

| Sub-area | Concept nodes | Anchor evidence |
|---|---|---|
| **Continual learning** | `C-continual-learning`, `C-catastrophic-forgetting` | Named by Hassabis, Sutton, Karpathy as THE gap; Nested Learning/HOPE (Google), OaK (Sutton) |
| **Memory** | `C-memory-induced-drift`, `C-cognitive-core` | Beyond pass@1 (memory hurts), OPD-Evolver (memory helps if used), MEMDRIFT, Karpathy's "strip memory" |
| **Long-horizon agency** | `C-long-horizon-agency` | Long-Horizon-Terminal-Bench (best 15.2%), AutoLab (persistence predicts), ReBel |
| **World models** | `C-world-model`, `C-jepa` | V-JEPA 2, LeJEPA, Image World Models, World-Models survey; AMI Labs; Sora/V-JEPA critique |
| **Reliability / verification** | `C-verification-hierarchy`, `C-reward-hacking` | RSI survey (verifier hierarchy), Blind Curator, DeepVerifier, AgentV-RL |
| **Self-improvement (RSI)** | `C-self-improvement`, `C-scaffolding-ceiling` | DGM, AIDE² (Weco), GEA, SIA; scaffolding-ceiling debate |
| **Fluid intelligence / novelty** | `C-fluid-intelligence` | ARC-AGI-2 (frontier ~75–85, human ~66), ARC-AGI-3 (<1%) |
| **Streams of experience** | `C-streams-of-experience`, `C-oak` | Silver & Sutton "Era of Experience"; Sutton's OaK / Oak Lab |

---

## 2. What serious researchers/labs say AGI REQUIRES — named positions

The striking thing: the leaders **agree on the gaps** (continual learning, memory, world models, reliability)
but **disagree sharply on whether the LLM lineage can close them** and on the **role of memory**.

- **Demis Hassabis (DeepMind)** — AGI ~2030 ±1yr, but ~50/50 odds the current paradigm is missing 1–2 big ideas.
  Unsolved: continual learning, robust memory, world physics/models, consistency, introspective reasoning.
  "Scale is all you need" is **incomplete**. `CL-hassabis-gaps` — [biggo](https://finance.biggo.com/news/cfe7765782e4b9eb), [36kr](https://eu.36kr.com/en/p/3788662855425033)
- **Dario Amodei (Anthropic)** — "powerful AI" (Nobel-level across most fields) as early as **2027**; interpretability is
  urgent; world models + continual learning are the fallback **if self-improvement doesn't deliver on its own**.
  `CL-amodei-powerful` — ["The Adolescence of Technology"](https://darioamodei.com/essay/the-adolescence-of-technology)
- **Richard Sutton (Oak Lab, Turing/RL)** — LLMs / large-scale pretraining are a **"dead end"** for superintelligence.
  True AI = agents that learn continually **from experience at runtime**; the **OaK architecture** (Options + Knowledge)
  builds its own abstractions + world model from raw experience. Oak Lab goal: trillion-param agent learning/planning in
  real time at ~20W. `CL-sutton-deadend` — [techtimes](https://www.techtimes.com/articles/320598/20260715/), [mlq](https://mlq.ai/news/turing-award-winner-rich-sutton-launches-oak-lab-to-build-continuously-learning-ai-agents/)
- **Yann LeCun (AMI Labs, ex-Meta)** — **autoregressive LLMs won't reach AGI**; intelligence needs to model the world,
  simulate, and plan → **JEPA** (latent prediction over token/pixel reconstruction). Left Meta; AMI Labs raised ~$1B seed
  (~$3.5B val, Mar 2026) for world models. `CL-lecun-autoregressive` — [latent.space](https://www.latent.space/p/ainews-yann-lecuns-ami-labs-launches)
- **Andrej Karpathy (Eureka Labs)** — **"decade of agents,"** not year; missing = continual learning, long-term memory,
  reliable tool use. Provocative counter-position: the **"cognitive core"** should have memory *stripped* so the model
  looks things up, keeping only "algorithms for thought." LLMs = jagged intelligence + anterograde amnesia.
  `CL-karpathy-decade` — [Dwarkesh](https://www.dwarkesh.com/p/andrej-karpathy), [Simon Willison](https://simonwillison.net/2025/Oct/18/agi-is-still-a-decade-away/)
- **François Chollet (ARC Prize)** — **fluid intelligence** (skill-acquisition efficiency on novel problems) is the missing
  piece; ARC-AGI-2 isolates it. `CL-chollet-fluid` — [arxiv 2505.11831](https://arxiv.org/abs/2505.11831)
- **David Silver & Sutton (DeepMind)** — **"Era of Experience"**: agents in continuous lifelong streams, grounded
  sensor-motor actions/rewards, non-human reasoning; experiential data eclipses human data. `CL-era-experience` — [PDF](https://storage.googleapis.com/deepmind-media/Era-of-Experience%20/The%20Era%20of%20Experience%20Paper.pdf)

**Convergence**: every named leader lists **continual learning + memory + world models + reliability** among the gaps.
**Divergence**: LLM-lineage optimists (Amodei, and implicitly the scaling camp) vs LLM-skeptics (Sutton, LeCun, Chollet).

---

## 3. THE DEBATE — contradictions front-and-center (the most valuable content)

The `contradicts` edges are the point of this ledger. Twelve are recorded; the six load-bearing ones:

1. **"Scaffolding compounds" vs "scaffolding is theater / hits a ceiling."**
   - FOR: LangChain harness-only **52.8%→66.5%** on Terminal-Bench 2.0, no model swap (`CL-harness-compounds`); Weng —
     mid-tier models benefit most.
   - AGAINST: *Rethinking Evaluation of Harness Evolution* (2607.12227) — automatic harness evolution **does not consistently
     beat simple test-time scaling** (`CL-harness-evolution-fails`); HarnessX "**scaffolding ceiling**" on weak models
     (`CL-scaffolding-ceiling`); @AP audit — GEPA often produces **zero net change** (same-prompt diff).
   - **Reconciliation (hypothesis)**: scaffolding compounds *on a capable model with a strong verifier*, and stalls
     otherwise. Directly explains the AIOS keystone STOP (weak model + heavy scaffold = ceiling).

2. **"GEPA improves / outperforms RL" vs "GEPA overfits / negative transfer."** ← the sharpest 2026 clash
   - FOR: GEPA (2507.19457, ICLR 2026 Oral) outperforms RL; `optimize_anything` tops evo baselines (`CL-gepa-outperforms`).
   - AGAINST: **RELAI "Do Agent Optimizers Compound?" (2607.14004)** — on Terminal-Bench 2.0 continual eval, GEPA's optimized
     agent **transfers BELOW the unoptimized baseline**; only **RELAI-VCL** (regression control in the loop) transfers
     positively and keeps improving (**76.4% vs 66.0%** lifelong) (`CL-gepa-overfits`). Plus VISTA (2603.18388): GEPA
     **degrades** GSM8K 23.81%→13.50% on a bad seed (`CL-gepa-degrades-seed`); @FeiziSoheil: GEPA overfits, RELAI generalizes.
   - **Takeaway**: optimizer gains compound **only when regression control / holdout transfer** is designed in. **RELAI is a
     new absorption candidate** (flagged in `radar:xlive`).

3. **"Memory helps long-horizon" vs "memory scaffolds hurt long-horizon."**
   - HURTS: *Beyond pass@1* (2603.29231) — memory scaffolds **universally hurt across all 10 models** (`CL-memory-hurts`);
     CL-Bench — **naive ICL beats dedicated memory** (`CL-icl-beats-memory`); AgentCL; MEMDRIFT — memory silently corrupts
     tool calls.
   - HELPS: OPD-Evolver — **memory helps IF the agent learns to USE it** (9B challenges 397B) (`CL-memory-helps-if-used`);
     Nested Learning/HOPE — continuum memory beats Transformers (`CL-nested-learning`).
   - **Reconciliation (hypothesis)**: the split is **bolt-on store (hurts)** vs **learned-to-use / architected memory (helps)**.
     "Memory that survives drift" is **UNSOLVED**. (Also note the intra-leader split: Karpathy wants *less* memory in the
     core vs Hassabis/Sutton wanting *robust* memory — `contradicts` `CL-karpathy-decade`↔`CL-hassabis-gaps`.)

4. **"Self-improvement works" vs "self-generated content degrades / self-feedback drifts / it just games the metric."**
   - WORKS: DGM open-ended self-improvement (`CL-dgm-selfimprove`); AIDE² claims **first net-positive RSI** (7 versions in 8
     days; reward hacking 63%→34%) — but **self-reported, not peer-reviewed** (`CL-aide2-rsi`).
   - DEGRADES: SoK Agentic Skills — **self-generated skills may degrade** success (`CL-selfgen-degrades`); SkillLearnBench —
     self-feedback → recursive drift; **Blind Curator** — a biased judge silently rots the skill library, unrecoverable past a
     threshold, invisible to aggregate metrics (`CL-blind-curator`); reward-hacking — **73.8% Kernel-Bench "gains" were proxy**
     (`CL-reward-hack-proxy`).
   - **Governing law (RSI survey 2607.07663)**: self-improvement strength **tracks the verification hierarchy** (formal > PRM >
     rubric > intrinsic). Weak/intrinsic verifier → self-improvement rots or games. `CL-verifier-tracks`.

5. **"LLMs scale to AGI" vs "LLMs are a dead end for AGI."**
   - Amodei's ~2027 "powerful AI" (LLM-lineage) vs Sutton (`CL-sutton-deadend`), LeCun (`CL-lecun-autoregressive`), Chollet
     (fluid-intelligence gap). Hassabis sits in between ("scale incomplete, 1–2 ideas missing").

6. **"JEPA/latent world models are the path" vs "current world models are brittle / haven't learned the real world model."**
   - FOR: LeJEPA identifiability guarantees (`CL-lejepa-identifiability`), V-JEPA 2 zero-shot robot planning.
   - AGAINST: Sora/V-JEPA philosophical + benchmark critique — **not a complete real-world model**; formal benchmark finds
     current models brittle (`CL-video-not-worldmodel`).

---

## 4. Methodology map (cross-cutting; tagged under D1)

| Methodology | Instances (Method nodes) | Frontier signal |
|---|---|---|
| **Recursive self-improvement** (`M-rsi`) | DGM (2505.22954), AIDE²/Weco, Red Queen Gödel, GEA, SIA | Net-positive RSI *claimed* (AIDE², self-reported); introspection-threshold gates whether RSI is possible; safety: Alignment Tipping |
| **Evolutionary / genetic scaffold search** (`M-evo`) | GEPA (2507.19457), LEVI (2605.09764), RELAI-VCL (2607.14004), ShinkaEvolve, OpenEvolve, RoboPhD | LEVI: **search substitutes for scale** (3.3–35× cheaper); RELAI: regression control decides compounding |
| **CoT / reasoning scaffold** (`M-cot`) | *(stub — deferred to D5 Reasoning)* | test-time compute; verification-centric reasoning (Marco 8B ≥ 30B) |
| **Verification hierarchy** (`M-verify`) | DeepVerifier, AgentV-RL (4B verifier +25%), PURE | **The load-bearing lever**: verifier strength = scaffold strength (2607.07663) |
| **Continual learning / memory** (`M-continual`) | Nested Learning/HOPE, OaK, OPD-Evolver | HOPE self-modifying Titans vs "memory hurts" evidence; **UNSOLVED under drift** |
| **World models** (`M-worldmodel`) | V-JEPA 2 (2506.09985), LeJEPA (2511.08544), Image World Models | LeCun/AMI Labs bet; brittleness critique open |

---

## 5. Coverage note (honest scope)

- **MET the bound**: 42 papers/artifacts, 20 people, 13 orgs. ~26 items carried & cited from the three radar sweeps
  (build-ON per instructions), ~17 freshly grounded this session (named positions, JEPA family, DGM, GEPA, RELAI, ARC-AGI,
  Nested Learning, AIDE²).
- **Deferred / honest gaps**:
  1. **Named lab-internal roadmaps beyond public essays** — OpenAI's o-series reasoning-scaling position, xAI, Mistral,
     Chinese frontier labs (DeepSeek/Moonshot/Zhipu) research theses are **not populated** (only their open models appear as a
     model-class snapshot, aggregator-grade).
  2. **Neuro-symbolic / program-synthesis AGI camp** — only an ARC/Chollet stub; DreamCoder-lineage and hybrid symbolic work
     not covered.
  3. **CoT / reasoning methodology** (`M-cot`) is a **stub** — test-time-compute scaling laws, verifier-guided search, and the
     "do reasoning models actually reason" debate are **deferred to D5 Reasoning** (queued domain).
  4. **Frontier closed-model numbers** (GPT-5.5 / Gemini / Claude on ARC-AGI-2 etc.) are **aggregator-grade snapshots**, not
     primary leaderboard pulls — treat as hypothesis-grade (`MO-frontier-2026`).
  5. **World-models sub-area** is populated on the JEPA branch; diffusion/AR video world models (Genie-lineage, D3/D7 overlap)
     are lightly covered here and belong to D3 (Physical AI) / D7 (Generative).
- **Hypothesis-grade nodes**: AIDE²/Weco (self-reported), LangChain/HarnessX (vendor/blog), OaK (research program not yet
  demonstrated), open/closed model rankings (community/aggregator). All flagged in `agi.json` via `grade`.

## 6. Radar feed (continuous append)

New AGI-relevant papers from future radar sweeps append here → `agi.json`. Dedup anchor = the SEEN lists in the two
radar sweeps + arxiv ids already in `agi.json`. Next likely additions: RELAI follow-ups, HarnessX primary paper (if it
lands on arxiv), OaK Lab first technical report, AMI Labs first paper, ARC-AGI-3 leaderboard movement.
