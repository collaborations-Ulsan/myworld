# OakLab AGI Ontology

Built 2026-07-17 by `claude@myworld` (Fable 5). Every entity/edge below is web-grounded (searched July 2026, **not** from training memory); machine-readable twin: [`oaklab_agi_ontology.json`](./oaklab_agi_ontology.json). Node/edge counts: **77 entities** (1 Lab, 26 Person, 25 Paper, 12 Concept, 13 Claim), **116 relations**, zero dangling edges, every edge carries a `source` URL.

---

## 1. What "OakLab" is (grounded — HIGH confidence)

**Oak Lab** ([oaklab.ai](https://oaklab.ai/)) is a **2026 AI research lab founded by Richard S. Sutton** (2024 Turing Award co-winner, a founder of reinforcement learning) together with his former PhD student **Khurram Javed**. Both left **Keen Technologies** (John Carmack's AI startup) to start it; the lab sits in Toronto but carries the University of Alberta / Amii RL lineage. Sutton had joined Keen in 2023 after Google DeepMind closed the Edmonton lab he co-led.
Sources: [oaklab.ai/mission](https://oaklab.ai/mission), [BetaKit](https://betakit.com/ai-pioneer-richard-sutton-founds-new-research-lab/), [The Decoder](https://the-decoder.com/turing-award-winner-rich-sutton-founds-oak-lab-to-build-ai-agents-that-learn-on-their-own/), [Tech Times](https://www.techtimes.com/articles/320598/20260715/turing-award-winner-sutton-launches-oak-lab-calls-current-ai-fundamentally-broken.htm).

**Mission (verbatim thrust):** "discover and implement algorithms that allow agents to achieve goals in **big worlds**" — agents that learn **continually from raw experience**, one step at a time, **without storing or replaying data** (batch-size-one learning), on **event-driven neural networks**. Stated "holy grail": a **trillion-parameter agent that learns and plans in real time on ~20 watts** (the human-brain energy budget).

**Its AGI stance is explicitly oppositional to the LLM-scaling paradigm.** Sutton calls current deep learning "weak and inefficient" and (in the 2025 Dwarkesh interview) argues **LLMs are a dead end** — they model "what a human would say next," not a true action-conditioned world model, lack a goal, and can't learn on the job. Oak Lab is the vehicle for the alternative: intelligence *created and maintained from run-time experience*.

### Disambiguation — other "Oak/OAK" entities (NOT this lab)
Searched and rejected as the AGI-tied referent: **Oak Ridge National Laboratory** (DOE, applied AI); **OAK Lab at CMU** ([theoaklab.org](https://www.theoaklab.org/), Optimized Algorithms & Knowledge — cognitive models of learning); **OAK'S LAB** ([oakslab.com](https://www.oakslab.com/), product/eng dev agency); **OakLabs Scientific** (German health-care); **Oak AI** (Higher Ground Labs, political tech). Sutton's Oak Lab is the one clearly tied to published AGI statements/papers — hence the seed.

---

## 2. Traversal map (who → what papers)

Seeded from the **7 papers Oak Lab lists on its site**, then followed ~1–2 reference/citation hops on AGI-relevant nodes. Bound (stated honestly): **25 papers, 26 people**. See §5 for what was deferred.

**Co-founders & seed papers**
- **Richard S. Sutton** → *The OaK Architecture* (2025, seed, primary thesis) · *Alberta Plan* (2208.11173) · *Big World Hypothesis* · *SwiftTD* · *Columnar-Constructive* (2302.05326) · *Horde* (2011) — plus 1-hop: *Reward is Enough*, *Era of Experience*, *Bitter Lesson*, *Loss of Plasticity* (Nature 2024), *Quest for a Common Model* (2202.13252), *IDBD* (1992), *Reward-Respecting Subtasks* (2202.03466).
- **Khurram Javed** → *Big World Hypothesis* (w/ Sutton) · *SwiftTD* (w/ Sharifnassab, Sutton) · *Columnar-Constructive* (w/ Shah, Sutton, White) · *Meta-Learning Representations for Continual Learning* (1905.12588, w/ M. White) · *Swift-Sarsa* (2507.19539).

**1-hop collaborators pulled in:** Michael Bowling & Patrick Pilarski (Alberta Plan, Horde); David Silver, Doina Precup, Satinder Singh (Reward is Enough; Silver also Era of Experience); Martha White (continual-learning line); Shibhansh Dohare, Rupam Mahmood, Hernandez-Garcia, Lan, Rahman (Loss of Plasticity); Arsalan Sharifnassab & Haseeb Shah (fast-learning line); John D. Martin, David Abel, Will Dabney (Settling the Reward Hypothesis); Andrew Barto (RL:Introduction, Turing co-winner).

**Adversarial / contradiction nodes deliberately included:** Peter Vamplew — *Scalar reward is not enough* (2112.15422, rebuts Reward is Enough); David Abel — *Three Dogmas of RL* (RLC 2024, questions the scalar-reward/single-MDP dogmas); Dwarkesh Patel — surfaces both Sutton's "LLMs are a dead end" claim and the counter (LLMs as a useful prior).

---

## 3. The AGI-thesis synthesis (what this graph says AGI needs) — ≤10 lines

1. **Experience, not human data.** Intelligence must be *created at run time* from the agent's own experience stream; "agents that discover like we can, not which contain what we have discovered." (OaK; Era of Experience)
2. **Reward is the goal skeleton.** Goals = maximization of expected cumulative *scalar* reward (Reward Hypothesis; Reward is Enough; Settling the Reward Hypothesis).
3. **Big-world humility.** The agent is always tiny vs. the world ⇒ it must approximate, forget, and adapt forever; efficient/approximate computation beats exact (Big World Hypothesis; Bitter Lesson).
4. **State + time abstraction via options.** AGI needs model-based planning abstract in *both* state and time; options must be discovered so their models are useful for planning — the FC-STOMP loop (OaK; Reward-Respecting Subtasks; Options 1999).
5. **Continual learning that keeps plasticity.** Every component learns continually with per-weight meta-learned step-sizes (IDBD/SwiftTD); this only works if plasticity loss is solved (Loss of Plasticity, Nature 2024) — a named open obstacle.
6. **Efficiency is the moat.** Endgame = a trillion-param agent learning+planning in real time on ~20W via event-driven nets + batch-size-one learning.
7. **CONTRADICTIONS surfaced:** (a) *Scalar reward is not enough* (Vamplew) directly rebuts *Reward is Enough*; (b) *Three Dogmas* questions the single-MDP/scalar-reward foundations OaK leans on; (c) *LLMs-are-a-dead-end* (Sutton) vs. *LLMs-as-useful-prior* (Dwarkesh's fossil-fuel counter). The graph AGREES on experience+continual-learning+options; it DIVIDES on whether scalar reward suffices and whether LLMs are a bridge or a cul-de-sac.

---

## 4. Node / edge summary

| Entity type | count | Relation type | count |
|---|---|---|---|
| Lab | 1 | authored | 51 |
| Person | 26 | extends (incl. agree) | 15 |
| Paper | 25 | asserts | 14 |
| Concept | 12 | proposes | 13 |
| Claim | 13 | concept_relates_to | 10 |
| | | cites | 7 |
| | | contradicts | 3 |
| | | affiliated_with | 3 |
| **Total entities** | **77** | **Total relations** | **116** |

Key **Claim** nodes with provenance (full text in JSON): `experience_superint`, `state_time_abstraction`, `bigworld`, `reward_enough` ↯ `scalar_not_enough`, `llm_deadend` ↯ `llm_useful_prior`, `era_experience`, `plasticity_prereq`, `stepsize_meta`, `efficiency_moat`, `bitter`, `three_dogmas`. (↯ = contradiction edge.)

---

## 5. Confidence flags, hypothesis-grade items, and honest negatives

**Hypothesis-grade / to verify (flagged in JSON `confidence:"hypothesis"`):**
- `paper:stepsize` — Oak Lab lists "Step-size Optimization for Continual Learning (2024)"; likely = *MetaOptimize* (arxiv 2402.02342, Sharifnassab et al.) but the mapping is **unverified**.
- `paper:swiftsarsa` (2507.19539) & `paper:worldbigger` (2512.23419) — author lists not fully resolved.
- `paper:tracking` (On the Role of Tracking, ICML 2007) — cited in OaK talk notes; author list (Sutton, Koop, Silver) not re-verified — "Koop" not modeled as a node.
- `paper:dogmas` claim `three_dogmas` — dogma wording paraphrased from a secondary summary of the RLJ PDF, not the PDF body.
- People `person:degris`, `person:awhite` — Horde co-authors taken from the standard citation, not re-confirmed against the PDF; Horde's "M. Delp" co-author is intentionally **not** modeled.

**Aggregator/secondary-sourced (grounded but second-hand):**
- The **OaK architecture body** was read via secondary talk notes ([galtay.github.io](https://galtay.github.io/blog/sutton-on-oak-at-rlc-2025/)) + the NeurIPS listing + oaklab.ai, because the [oaklab.ai OaK post](https://oaklab.ai/posts/the-oak-architecture) is JavaScript-rendered and returned only navigation to the fetcher. Quotes are as reported there.
- *Reward is Enough* and *Era of Experience* abstracts read via PhilPapers / DeepMind media + commentary, not the journal HTML.

**Honest negatives (could NOT access directly):**
- Full text of the OaK post, the Era-of-Experience PDF, and the SwiftTD/Three-Dogmas PDFs were not parsed line-by-line — only their abstracts/notes.
- No arxiv id found for **SwiftTD** (RLJ-only) or **Horde** (AAMAS-only); cited by venue URL instead.
- **Rich Sutton's publications page** (`incompleteideas.net/publications.html`) failed to fetch (self-signed cert) — his older-paper metadata (IDBD, Options, Tracking) comes from cross-search, so exact venues/years there are best-effort.

---

## 6. SEEN / COVERAGE appendix (for radar/ontology extension)

**Papers covered (id · title · arxiv/venue):**
1. `paper:oak` · The OaK Architecture: A Vision of SuperIntelligence from Experience · RLC/NeurIPS 2025 (no arxiv)
2. `paper:bwh` · The Big World Hypothesis & its Ramifications for AI · OpenReview Sv7DazuCn8 (RLC 2024)
3. `paper:swifttd` · SwiftTD · RLJ 2024 Paper111
4. `paper:stepsize` · Step-size Optimization for Continual Learning · (≈2402.02342, unverified)
5. `paper:columnar` · Scalable Real-Time Recurrent Learning (Columnar-Constructive) · 2302.05326 / JMLR v24
6. `paper:alberta` · The Alberta Plan for AI Research · 2208.11173
7. `paper:horde` · Horde · AAMAS 2011
8. `paper:rrsubtasks` · Reward-Respecting Subtasks for Model-Based RL · 2202.03466
9. `paper:rewardenough` · Reward is Enough · Artif. Intell. 299:103535 (2021)
10. `paper:eraexp` · Welcome to the Era of Experience · DeepMind 2025
11. `paper:bitter` · The Bitter Lesson · incompleteideas.net 2019
12. `paper:plasticity` · Loss of plasticity in deep continual learning · Nature 632 (2024), doi 10.1038/s41586-024-07711-7
13. `paper:oml` · Meta-Learning Representations for Continual Learning · 1905.12588 (NeurIPS 2019)
14. `paper:settling` · Settling the Reward Hypothesis · 2212.10420
15. `paper:scalarnot` · Scalar reward is not enough · 2112.15422
16. `paper:quest` · The Quest for a Common Model of the Intelligent Decision Maker · 2202.13252
17. `paper:idbd` · IDBD (Adapting Bias by Gradient Descent) · AAAI-92
18. `paper:dwarkesh` · Sutton on Dwarkesh Podcast (LLMs a dead end) · 2025 interview
19. `paper:swiftsarsa` · Swift-Sarsa · 2507.19539
20. `paper:columnar_pre` · Scalable Online Recurrent Learning (Columnar) · 2103.05787
21. `paper:worldbigger` · The World Is Bigger! A Computationally-Embedded Perspective · 2512.23419
22. `paper:dogmas` · Three Dogmas of Reinforcement Learning · RLJ/RLC 2024 Paper89
23. `paper:options` · Between MDPs and semi-MDPs (Options) · Artif. Intell. 112 (1999)
24. `paper:rlbook` · Reinforcement Learning: An Introduction (2nd ed.) · MIT Press 2018
25. `paper:tracking` · On the Role of Tracking in Stationary Environments · ICML 2007

**People covered (26):** Sutton, Javed, Bowling, Pilarski, Silver, Precup, Singh, M. White, Dohare, Mahmood, Sharifnassab, H. Shah, Shafait, Modayil, Degris, A. White, Hernandez-Garcia, Lan, Rahman, J. Martin, Abel, Dabney, Vamplew, Barto, Carmack (context), Dwarkesh Patel (external).

**Deferred for a later hop (not yet in graph):** full author sets of Reward-Respecting Subtasks (Machado, Holland, Timbers, Tanner) and Three Dogmas (Barreto, Van Roy); the backward-citation trees of Options(1999) and RL:Introduction; Oak Lab's forthcoming "event-driven networks + batch-size-one" paper (marked "coming soon" on the site); applied/robotics RL papers judged not AGI-thesis-relevant.
