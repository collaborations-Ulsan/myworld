# Frontier Knowledge Ledger — D6: Learning methods (beyond frozen pretrained models)

**Schema**: `docs/ontology/FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md` §1 (unified). **Data**: `learning_methods.json`.
**Status**: draft-first (append; not accepted — DNA #2). **Populated**: 2026-07-17 by claude@myworld.
**Grounding**: 3 parallel grounded research agents (developmental / quality-diversity / open-ended) + own WebSearch, HF `paper_search`, and WebFetch this session — every node/edge sourced.
**Format**: CANONICAL flat-entity + `{src_id,rel,dst_id}` edges (D1/D2/D3 used the divergent `{type,from,to}` form; this file matches `_merged.json` ingestion and **reuses shared ids** — `person:richard_s_sutton`, `person:jeff_clune`, `person:danijar_hafner`, `org:sakana_ai`, `lab:oak_lab`, `paper:2505.22954` (DGM), `paper:2507.19457` (GEPA), `concept:loss_of_plasticity_plasticity_preservation`, … — so **45 cross-domain edges into D1 resolve**).
Nodes tagged `grade:hypothesis` are aggregator/blog/pre-QD-era foundational (cited via review) or arxiv numbers not directly fetched; `grade:primary` are arxiv/venue/first-party.

**Counts**: 220 nodes (70 papers, 40 methods, 35 claims, 29 concepts, 23 people, 11 benchmarks, 8 orgs/labs, 3 methodologies, 1 domain) · 361 edges incl. **11 `contradicts`** (the frontier's disagreements) and **45 cross-domain edges into D1**.

**Founder framing**: this domain grounds the thesis that the frozen pretrained LLM is a dead-end (Sutton/OaK "learn at run-time from experience") across the three methodological families the founder named, and derives the concrete redesign of **LearnOS**'s evolutionary engine (§4).

---

## 1. The three families (map)

| Family | Founder's words | What it is | Methodology node |
|---|---|---|---|
| **F1** | "learn like a baby" | Developmental / from-scratch learning: continual & streaming RL from interaction, automatic curricula, intrinsic motivation, world-models from raw experience, plasticity preservation, test-time training | `methodology:developmental_from_scratch_learning` |
| **F2** | "leave genes behind, extract recessive traits" | Quality-Diversity + preserved gene pool: an archive keeps diverse non-champions so latent/"recessive" building blocks can be recombined/recovered later | `methodology:quality_diversity` |
| **F3** | "differentiate evolutionarily" | Open-ended evolution + speciation/niching that maintains multiple specialist lineages and prevents collapse to one champion | `methodology:open_ended_evolution` |

All three are unified by the same organizing concept — `concept:learn_from_experience_runtime` (Silver & Sutton "Era of Experience"; Sutton RLC-2025 **OaK** architecture, Oak Lab founded June 2026) — and all three feed one system-level payoff: the **LearnOS gene-pool redesign** in §4.

---

## 2. Family findings (compressed — full detail + numbers in `learning_methods.json` claims)

### F1 — developmental / from-scratch
- **Streaming RL** is the most faithful *and* device-runnable realization: **stream-x** ([2410.14606](https://arxiv.org/abs/2410.14606), Elsayed/Vasan/Mahmood, Alberta) learns batch-size-one with **no replay buffer, no target nets**, matching batch-RL sample efficiency — closest to OaK's regime.
- **World models from experience**: DreamerV3 ([2301.04104](https://arxiv.org/abs/2301.04104)) — first to mine Minecraft diamonds from scratch, one config over 150+ tasks, single GPU; **Dreamer 4** ([2509.24527](https://arxiv.org/abs/2509.24527)) — 2B agent, diamonds from *offline* video, RL-in-imagination, ~21 FPS on one GPU; TD-MPC2 ([2310.16828](https://arxiv.org/abs/2310.16828)).
- **Intrinsic motivation**: RND ([1810.12894](https://arxiv.org/abs/1810.12894)) still a baseline but degrades on real noisy-TVs → 2025-26 moves to **learning-progress** ([2509.25438](https://arxiv.org/abs/2509.25438)) and distributional targets **RDD** ([2505.11044](https://arxiv.org/abs/2505.11044)); empowerment pretraining ([2510.05996](https://arxiv.org/abs/2510.05996)).
- **Automatic curricula / UED**: PAIRED/PLR ([2110.02439](https://arxiv.org/abs/2110.02439)) → **ACCEL** ([2203.01302](https://arxiv.org/abs/2203.01302)); LLM-writes-the-environment **OMNI-EPIC** ([2405.15568](https://arxiv.org/abs/2405.15568)).
- **Plasticity-loss** (the OaK open problem): continual backprop "fully overcame" it in the *Nature* setup (89%→77% by task 2000 without it), **but** the Apr-2026 survey ([2411.04832](https://arxiv.org/abs/2411.04832)) finds **no dominant method** and scale does **not** save LLMs ([2606.24752](https://arxiv.org/abs/2606.24752)). Not solved in general.
- **Honest caveat**: the winning 2025-26 "learn-from-experience" systems (Absolute Zero [2505.03335](https://arxiv.org/abs/2505.03335), V-JEPA 2 [2506.09985](https://arxiv.org/abs/2506.09985)) are **hybrids on a pretrained base** — "beat pretrained from random init at scale" is **undemonstrated**.

### F2 — quality-diversity / gene pool / recessive recovery
- **The literal metaphor** has a 1987 home: **diploid GAs with dominance** (Goldberg & Smith) — recessive alleles are a *latent memory* of past-optimal traits, re-expressed under non-stationarity. `concept:diploidy_dominance` → `concept:recessive_latent_trait_recovery`.
- **The scalable form**: the QD **archive is the preserved gene pool**. Novelty search ([Lehman & Stanley 2011](https://dl.acm.org/doi/abs/10.1162/evco_a_00025)) → NSLC → **MAP-Elites** ([1504.04909](https://arxiv.org/abs/1504.04909)) → damage recovery in <2 min from a ~13k-gait repertoire ([Cully *Nature* 2015](https://www.nature.com/articles/nature14422)); CMA-ME/**CMA-MAE** ([2205.10752](https://arxiv.org/abs/2205.10752)). QD provably beats (μ+1)-EA on NP-hard classes ([2401.10539](https://arxiv.org/abs/2401.10539)).
- **Recessive recovery = recombination across niches**: isoline variation; **discrete gene-level crossover** ("meiosis-like", strongest late once building blocks exist — [2602.13730](https://arxiv.org/abs/2602.13730)); **In-context QD** recombines *many* archive elites at once ([2404.15794](https://arxiv.org/abs/2404.15794)).
- **LLM-driven evolution** (archive-based): ELM → QDAIF → AlphaEvolve/OpenEvolve → **ShinkaEvolve** (island archive, ~150 evals to SoTA — [2509.19349](https://arxiv.org/abs/2509.19349)) → **DGM** (agent archive, SWE-bench 20→50 — [2505.22954](https://arxiv.org/abs/2505.22954)) → **DEI** (heterogeneous LLM operators: **+124% QD-score**, model-diversity-not-parallelism — [2605.27130](https://arxiv.org/abs/2605.27130)).
- **Sharpest 2026 debate**: **Mutation Without Variation** ([2606.05408](https://arxiv.org/abs/2606.05408)) — LLM mutation collapses to ~10 unique templates vs ~270 for classical GP; the QD/archive scaffold + heterogeneous operators are what *prevent* collapse. This is empirical proof of *why you keep the pool, not the champion*.

### F3 — open-ended / speciation into specialists
- **Two anti-collapse mechanisms**: (a) *niching/speciation inside one population* — fitness sharing, crowding, RTS, **NEAT species** protect weak-but-novel structures ([Stanley & Miikkulainen 2002](https://dl.acm.org/doi/10.1162/106365602320169811)); MAP-Elites niches = one elite per behavior cell; and (b) *coevolution/minimal-criterion* — **MCC** ([Brant & Stanley 2017](https://dl.acm.org/doi/10.1145/3071178.3071186)) differentiates with **no objective/novelty/descriptor**, just a survival gate on two coupled populations (needs a **resource cap** to avoid "everyone farms the easiest maze" — [GECCO 2020](https://dl.acm.org/doi/10.1145/3377930.3389809)).
- **Open-ended lineage**: POET ([1901.01753](https://arxiv.org/abs/1901.01753)) → **Enhanced POET** ([2003.08536](https://arxiv.org/abs/2003.08536), ANNECS shows open-endedness is *encoding-dependent* — original plateaus ~20k iters) → OMNI → OMNI-EPIC → **DiCode** (+16% return, [2602.08194](https://arxiv.org/abs/2602.08194)). Manifesto: **"Open-Endedness is Essential for ASI"** ([2406.04268](https://arxiv.org/abs/2406.04268), Hughes/Rocktäschel/DeepMind).
- **2026 LLM-in-weight-space coevolution → specialists**: **AC/DC** ([2604.14969](https://arxiv.org/abs/2604.14969), Sakana) coevolves an LLM archive (model-merge crossover + weight-noise mutation) with a task archive → **specialist LLMs beating larger models at less GPU memory, broader Coverage** — an MCC/POET analogue in weight space. **Kinetix+SFL** general agent beats *specialists* on holdout ([2410.23208](https://arxiv.org/abs/2410.23208)); **FMSP/QDSP** discovers distinct strategy families ([2507.06466](https://arxiv.org/abs/2507.06466)).
- **Debates**: is FM open-endedness genuine or bounded by the training distribution? ([2511.12869](https://arxiv.org/abs/2511.12869) skeptic vs [2406.04268]); a new **information-theoretic definition** (bit-equivalent, [2606.08369](https://arxiv.org/abs/2606.08369)) critiques novelty+learnability for not indicating *capability improvement*. **FER** ([2505.11581](https://arxiv.org/abs/2505.11581), Kumar/Clune/Lehman/Stanley): open-endedly *evolved* nets lack the fractured representation SGD produces — a structural argument *for* evolution.

---

## 3. Device-runnable on dual RTX 5090 (64 GB) — ranked shortlist

Runnability is gated by **which loop the GPU is in**: classical QD/NE are GPU-native and cheap; LLM-driven evolution is *evaluation-bound* (the LLM is the operator) so a local `qwen3-coder:30b` (≈18-20 GB in 4-bit) fits one card and matches the *sample-efficient* regime.

| # | Candidate (id) | Runnable? | Why / scale | Role for LearnOS |
|---|---|---|---|---|
| **1** | **ShinkaEvolve** `method:shinkaevolve` ([2509.19349](https://arxiv.org/abs/2509.19349)) | ✅ open-source, local-LLM operator | Island **archive** of subpopulations + parent/inspiration sampling + code-novelty rejection + bandit LLM-ensemble; **~150 evals** to SoTA (circle-packing). Eval-bound, not VRAM-bound. | **Best to absorb next** — the runnable evolutionary-engine backbone |
| 2 | **QDax** `paper:2308.03665` | ✅ 1× 5090 | JAX MAP-Elites/CMA-MAE/PGA-ME on Brax; ~10⁸ env-steps/hr on one GPU; archives of 10³–10⁵ elites routine | the GPU-native gene-pool substrate |
| 3 | **GSME self-evolving harness** `method:gsme_harness` ([2607.13683](https://arxiv.org/abs/2607.13683)) | ✅ frozen open-weight model | **The LearnOS-shaped result**: QD archive indexed by (WHERE×WHY) pathology + **sealed held-out test**; +9→+15.5 pp / 86-147% retention | the target *architecture* (verify code release) |
| 4 | **TensorNEAT** `paper:2504.08339` / **pyribs** `paper:2303.00191` | ✅ 1× 5090 / CPU | GPU NEAT (500× vs NEAT-Python, RTX 4090) with **speciation**; pyribs = reference CMA-ME/MAE | drop-in speciation + QD algorithms |
| 5 | **Discrete Gene Crossover** `method:discrete_gene_crossover` ([2602.13730](https://arxiv.org/abs/2602.13730)) | ✅ (operator) | meiosis-like recombination of elite building blocks; strongest late | the **recessive-recovery operator** to add to the archive |
| 6 | **Kinetix+SFL** `method:kinetix_sfl` + local-LLM **OMNI-EPIC** loop | ✅ 1× 5090 | Jax2D millions steps/s; open-ended curriculum → beats specialists | if LearnOS needs environment/task generation |
| 7 | **DEI heterogeneous operators** `method:dei` ([2605.27130](https://arxiv.org/abs/2605.27130)) | ✅ (mix local 30B + frontier API) | +124% QD-score from operator diversity | operator-ensemble policy |

**Not local at published scale**: POET/Enhanced POET (256–750 CPU cores × days — use QDax/Kinetix as GPU-native substitutes); AlphaEvolve (closed → use OpenEvolve/ShinkaEvolve); DGM/AC/DC/DéjàQ *published* with frontier APIs (locally feasible but weaker); V-JEPA-2 / full Dreamer-4 pretraining (inference/fine-tune only on 64 GB).

**Single best to absorb next → ShinkaEvolve**, upgraded per §4 (its island archive is already a gene pool; add a QD behavior-descriptor, discrete-gene crossover, and a sealed verifier).

---

## 4. LearnOS engine implication — flat archive → gene-pool-with-recessive-recovery + speciation

**Problem**: LearnOS today is an evolutionary harness-improver with a **flat archive + external held-out verifier**. A flat, keep-the-champion archive is exactly the hill-climb that F2 says *loses the recessive/latent building blocks*, and it collapses to one lineage (the failure F3's speciation exists to prevent). The convergent, grounded redesign:

1. **Make the archive a MAP-Elites gene pool, not a leaderboard.** Key each cell by a **behavior descriptor** — adopt GSME's `(WHERE × WHY) failure-pathology × capability-niche` ([2607.13683](https://arxiv.org/abs/2607.13683)) — and keep **one elite per niche**. That preserves specialists (speciation) and gives an anti-overfitting inductive bias by construction. QD-score, not pass@1, is the objective (`concept:qd_score`).
2. **Recover recessive traits by recombining across niches.** Add lineage/ancestry tracking + **discrete gene-level (meiosis-like) crossover** ([2602.13730](https://arxiv.org/abs/2602.13730)) and **In-context QD** recombination of *many* elites ([2404.15794](https://arxiv.org/abs/2404.15794)), so non-champion patches held in other niches resurface later — the literal "extract recessive traits" mechanism (diploid-GA intuition, [Goldberg-Smith 1987]).
3. **Speciate with an island model + minimal-criterion admission.** Run subpopulation **islands** with periodic migration (ShinkaEvolve's structure), and gate admission by a **minimal criterion on the SEALED external verifier** (`concept:external_heldout_verifier`) — not the mutating LLM's self-report — with a **resource cap** per niche ([MCC 2020]) so no easy niche is farmed to collapse.
4. **Use heterogeneous mutation operators.** Single-LLM mutation collapses diversity (**Mutation Without Variation** [2606.05408](https://arxiv.org/abs/2606.05408)); mix local `qwen3-coder:30b` with a frontier model as an operator ensemble (**DEI**: model diversity, not parallelism, drives QD-score [2605.27130]).

**Net**: LearnOS's flat archive becomes a *speciating gene pool with recessive recovery* — specialists preserved per pathology niche, latent building blocks recombined across niches, admission gated by a held-out verifier, diversity protected by heterogeneous operators. **ShinkaEvolve is the runnable skeleton to absorb; GSME is the target shape; Discrete-Gene-Crossover + MCC-resource-cap are the two operators to add.**

---

## 5. Contradictions preserved (`contradicts` edges — the frontier's disagreements)

- **Is loss of plasticity solved?** continual-backprop "fully overcame" it (*Nature*) **vs** no-dominant-method survey ([2411.04832]) **vs** scale-doesn't-save-LLMs ([2606.24752]).
- **Does LLM mutation help or collapse?** ShinkaEvolve sample-efficiency **vs** Mutation-Without-Variation structural collapse **vs** DEI diversity-recoverable-via-heterogeneous-operators.
- **Is QD's diversity machinery necessary?** "Objectives Are All You Need" ([2311.02283]) **vs** novelty-beats-objective / QD-provably-helpful.
- **Is open-endedness genuine or bounded?** Hughes "essential for ASI" **vs** LLM-novelty-bounded ([2511.12869]) **vs** the info-theoretic "novelty+learnability ≠ capability improvement" critique ([2606.08369]).
- **From-scratch vs pretrained**: DreamerV3 from-scratch **vs** V-JEPA-2 / Absolute-Zero hybrids — "beat pretrained from random init at scale" undemonstrated.
- **Representations**: FER — evolution yields cleaner (unified factored) representations than SGD ([2505.11581]).

---

## 6. Coverage & deferred (honest — no silent truncation)

- **Bound target** ~55-70 papers / 3 families deep: **MET** (70 papers, 40 methods, 35 claims).
- **Grade**: `hypothesis` nodes = pre-QD-era foundational (Goldberg-Smith 1987, novelty 2011, NEAT 2002, MCC 2017) cited via reviews not original PDFs, or arxiv numbers surfaced but not directly fetched. All 2026 arxiv ids cross-checked to resolve to real papers.
- **Deferred / thin**: (1) exact numbers for **QDAIF** coverage/agreement, **DéjàQ**, **AC/DC** full benchmark tables were not machine-extractable (flagged); (2) **empowerment** sub-thread thin (2 nodes); (3) **developmental robotics / Oudeyer** camp only lightly touched; (4) **POET** has no independent large-scale replication (absence-of-evidence, not disproof); (5) neuro-symbolic / program-synthesis learning not covered (belongs to D5).
- **Radar continuation**: this file is radar-appendable — new QD/open-ended/continual papers flow into the same D6 schema; contradictions are preserved as `contradicts` edges (schema §4).
