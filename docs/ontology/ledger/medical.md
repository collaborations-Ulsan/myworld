# Frontier Knowledge Ledger — D2: Medical / Biomedical AI

**Populated:** 2026-07-17 · **Schema:** `docs/ontology/FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md` §1 (unified) · **Graph:** `medical.json`
**Draft-first** (DNA #2): nodes are appended, not accepted. Aggregator / vendor-self-report / single-source claims are tagged **hypothesis-grade** below.

**Graph size:** 195 nodes / 333 edges — Domain 1, Methodology 8, Method 12, Paper 51, Person 28, Lab 25, Model 11, Benchmark 10, Concept 15, Claim 34.
Every node and edge carries a `source`. This file is the first instance populated in `docs/ontology/ledger/`; it sets the JSON convention (`{"entities":[...],"relations":[...]}`, readable slug ids, `source` on all) for sibling domain files.

Grounding method: 4 parallel research agents (WebSearch + HF `paper_search`/hub) + independent operator grounding; the highest-signal headline items (Boltz-2, Evo 2, AlphaGenome, MAI-DxO, MedGemma, Baichuan, Chai-2, Protenix, RFdiffusion2) were cross-checked in a second lane. HF `hf.co/papers/<id>` maps 1:1 to `arxiv.org/abs/<id>`; 26MM ids are 2026 papers.

---

## 1. Sub-area map (what the graph covers)

| Sub-area | Anchor works (arXiv/DOI) |
|---|---|
| **Clinical LLMs / reasoning** | MAI-DxO 2506.22405 · Baichuan-M2 2509.02208 / M3 2602.06570 · MedGemma 1.5 2604.05081 · Med-RLVR 2502.19655 |
| **Agentic diagnosis / EHR agents** | AMIE 2503.06074 · MedAgentBoard 2505.12371 · PhysicianBench 2605.02240 · Context Clues (EHR) 2412.16178 |
| **Medical VLMs / multimodal** | Lingshu 2506.07044 · MedVLThinker 2508.02669 · MedBLINK 2508.02951 · ClinHallu 2606.14697 |
| **Medical imaging FMs** | Pillar-0 2511.17803 · Curia-2 2604.01987 · Atlas 2 (path) 2601.05148 · THREADS 2501.16652 · MOOZY 2603.27048 |
| **Imaging: segmentation / generative** | MedSAM2 2504.03600 · DM4CT 2602.18589 · SUMI 2604.07329 |
| **Clinical-safety UQ** | ConVOLT (conformal) 2603.00798 · scanner-shift robustness 2601.04163 |
| **Protein structure / co-folding** | Boltz-2 (bioRxiv 2025.06.14.659707) · Pearl 2510.24670 · Protenix (2025.01.08.631967) · OpenFold3 · DeCAF 2606.08375 |
| **Protein / molecule design** | RFdiffusion2 (2025.04.09.648075) · La-Proteina 2507.09466 · Chai-2 (2025.07.05.663018) · ESM3 (Science ads0018) · Apo2Mol 2511.14559 |
| **Docking / dynamics** | DiffDock-L 2402.18396 · PoseX 2505.01700 · BioEmu (Science adv9817) |
| **Drug-discovery agents** | Mozi 2603.03655 · TxAgent 2503.10970 |
| **Genomics / DNA FMs** | Evo 2 (Nature s41586-026-10176-5) · AlphaGenome (Nature s41586-025-10014-0) · GENEB 2606.04525 |
| **Single-cell / virtual cell** | STATE (2025.06.26.661135) · C2S-Scale (2025.04.14.648850) · Lingshu-Cell 2603.25240 · AssayBench 2605.10876 |
| **Biomedical AI-scientist agents** | Biomni (Science) · AI co-scientist 2502.18864 · Robin (Nature s41586-026-10652-y) |

## 2. Key methodologies (the "how", cross-cutting — `Methodology` nodes)

1. **Foundation models / SSL** — masked/autoregressive/contrastive/JEPA pretraining on genomes, cells, slides, CT/MRI, EHR. Now every sub-area's substrate.
2. **Diffusion & flow-matching** — the dominant generative engine for protein backbones, molecules, cell-state transitions, and image synthesis/reconstruction; 2026 shift toward **flow maps / few-step distillation** (DeCAF) and **inference-time (test-time) search**.
3. **RL / RLVR / GRPO with verifiers** — reasoning elicited from *checkable* rewards; medicine's twist is **dynamic/interactive verifiers** (patient simulators + rubric generators, Baichuan) replacing static answer keys.
4. **Agentic pipelines / orchestration** — specialty-routed multi-agent panels (MAI-DxO), governed drug-discovery agents (Mozi), tool-universe reasoning (TxAgent), end-to-end AI-scientists (Biomni/Robin/co-scientist).
5. **Uncertainty / verification for clinical safety** — conformal prediction, calibration, OOD/hallucination detection, selective prediction. The named gate to deployment.
6. **Generative / evolutionary de novo design** — enzymes from reaction mechanism (RFdiffusion2), zero-shot antibodies (Chai-2), genome-scale generation (Evo 2).
7. **Retrieval-augmented generation** — grounding clinical/biomedical LLMs in literature/EHR/live tool APIs.
8. **Biomolecular co-folding** — all-atom joint protein/NA/ligand prediction (+ affinity); the AlphaFold3 successor race.

## 3. Frontier synthesis — what this graph says the medical-AI frontier IS (2026)

- **The headline number moved from the base model to the *system*.** Diagnosis SOTA is now agentic/orchestrated (MAI-DxO 85.5% vs ~20% physicians on SDBench [2506.22405]); MDIA/AMIE echo "lift is architecture, not the prompt." But the same graph carries the cool-down (see §4).
- **Static exams are dead as a target; sequential/interactive/multimodal/EHR-grounded evaluation is the live frontier.** MedQA is ~saturated; the reasoning-vs-recall gap is widest on case-based, multi-turn, EHR-embedded tasks (PhysicianBench, EHR-Complex, Context Clues).
- **Dynamic verifiers + RLVR are the new training signal** for clinical reliability and safety (Baichuan-M2/M3, Med-RLVR, VPRMs), explicitly aimed at hallucination suppression, not exam recall.
- **Structure prediction has pivoted past static folds.** Authors uniformly name the frontier as: (a) **conformational ensembles / dynamics** (BioEmu, cryo-EM-supervised Boltz-2), (b) **affinity to FEP-parity generalizing to novel chemotypes** (Boltz-2), (c) **antibody–antigen complexes** (the shared weak spot of AF3 / Protenix / OpenFold3), (d) **inference-time compute & synthetic-data scaling** as the real levers (DeCAF, Pearl, DiffDock-L).
- **Generative design crossed into wet-lab-validated territory:** all-41 enzyme active sites (RFdiffusion2), 16% zero-shot antibody hit rate (Chai-2), esmGFP (ESM3), a wet-lab-confirmed C2S-Scale drug combo, Robin's ripasudil-for-dry-AMD.
- **Genomics has a foundation-scale generative model (Evo 2, 40B, 9.3T bp) and a unified regulatory model (AlphaGenome).** Both are strong on *prediction* (variant effect); *generative* genome utility and *virtual-cell* perturbation prediction remain contested.
- **Open weights are winning the substrate layer:** MedGemma, Baichuan-M2, Boltz-2 (MIT), Protenix (Apache, first open model to beat AF3), OpenFold3 (full training data), Evo 2 — open models now set or match SOTA in most sub-areas, with a closed tier at the very frontier (AlphaFold3, AlphaGenome, ESM3-6B, Isomorphic).

**Open problems the graph surfaces** (per authors): conformational dynamics & ensembles; affinity/antibody generalization; virtual-cell perturbation prediction that *reliably* beats baselines; robustness under scanner/site/distribution shift; hallucination & faithful reasoning in clinical MLLMs; grounded multimodal (imaging+genomics+EHR) evaluation; and biosecurity/dual-use of genome-generative models (flagged in the International AI Safety Report 2026).

## 4. Contradictions surfaced (the frontier's disagreements — `contradicts` edges)

These are preserved deliberately (schema §4: "프론티어의 불일치가 지식이다").

1. **Multi-agent value.** MAI-DxO's 85.5% headline vs **MedAgentBoard [2505.12371]**: multi-agent often does *not* beat a strong single LLM or classical ML; also MedMASLab/M3MAD-Bench show fragility + overhead.
2. **"AI beats doctors" is disputed at the setup level.** SDBench barred physicians from colleagues/textbooks/tools; NEJM-CPC cases are extreme teaching cases; data-leakage can't be excluded; never run in live workflow. **Hypothesis-grade** as a clinical-superiority claim.
3. **LLMs still lose to XGBoost/SVM** on structured clinical *prediction* (**ClinicalBench [2411.06469]**) — undercuts "LLM revolutionizes clinical decisions."
4. **Medical MLLMs fail basic perception** — MedBLINK: best model ~65% vs 96% human — vs strong FM AUROC headlines (Pillar-0).
5. **Do we even need dedicated 3D FMs?** **AnyMC3D [2512.12887]** (2D adapts beat 3D; general FMs match medical) and a small CNN winning the MICCAI brain-MRI FM challenges vs the scale-maximalist Pillar-0 / Curia-2 / Atlas 2 direction.
6. **Foundation models vs simple baselines (single-cell/genomics).** **Ahlmann-Eltze/Huber, Nature Methods 2025 [s41592-025-02772-6]** + **GENEB [2606.04525]** + **AssayBench [2605.10876]** (zero-shot generalist LLMs beat *bio-specific* ones) vs STATE / Lingshu-Cell / C2S-Scale wins. Partly a **metric artifact** ("Diversity by Design" shows mean-prediction dominance is a scoring artifact).
7. **AI vs physics in docking.** **PoseX [2505.01700]** ("AI defeats physics") vs strong classical docking baselines with known pocket that near pocket-specified AF3; and **AF3 affinity is unreliable** (ipTM insufficient) — the explicit motivation for Boltz-2's affinity head.
8. **Diffusion is not "solved" for real reconstruction.** **DM4CT [2602.18589]**: diffusion priors underperform under real correlated noise/geometry.
9. **Robustness under domain shift.** **Scanner-shift [2601.04163]** + "Good/Bad/Brittle" [2607.04401] (diminishing returns from scale) vs Atlas 2's deployment-grade robustness claim.
10. **Grader variance / vendor self-reports.** MDIA scores 0.627 vs 0.659 depending on grader; DR.INFO's HealthBench-Hard 0.68 is a vendor-self-reported agentic-RAG pipeline — **hypothesis-grade** vs base-model scores.

## 5. Key people / labs (28 people / 25 labs in graph — representative)

- **Clinical/agentic:** Harsha Nori, Hoifung Poon (Microsoft AI — MAI-DxO, Med-RLVR); Vivek Natarajan, Khaled Saab, Andrew Sellergren (Google DeepMind Health — AMIE, MedGemma); Baichuan Inc. (M1/M2/M3); Nigam Shah, Michael Wornow (Stanford — EHRSHOT, Context Clues); Danielle Bitterman (ClinicalBench, safety).
- **Imaging:** Faisal Mahmood (Harvard/BWH — UNI/CONCH/TITAN/THREADS); Aignostics/Charité (Atlas 2); Raidium (Curia-2).
- **Protein/drug:** David Baker (IPD/UW — RFdiffusion2); John Jumper, Demis Hassabis (DeepMind/Isomorphic); Alex Rives (EvolutionaryScale — ESM3); Regina Barzilay, Tommi Jaakkola, Gabriele Corso, Jeremy Wohlwend (MIT Jameel — Boltz/DiffDock/DeCAF); Genesis Therapeutics (Pearl/DeCAF); Chai Discovery (Chai-2); ByteDance AML (Protenix); NVIDIA/Karsten Kreis (Proteina line); Frank Noe (MSR — BioEmu); Insilico Medicine (clinical AI drugs).
- **Genomics/cell/agents:** Patrick Hsu, Brian Hie (Arc Institute — Evo 2, STATE); Google DeepMind (AlphaGenome); van Dijk Lab/Yale + Google (C2S-Scale); Marinka Zitnik (Harvard — TxAgent); Jure Leskovec, Kexin Huang (Stanford — Biomni); Sam Rodriques (FutureHouse — Robin); Wolfgang Huber (EMBL — baseline critique).

## 6. Coverage & deferred (honest, no silent truncation)

**Included as full nodes:** 51 papers / 12 concrete methods / 11 models / 10 benchmarks spanning all requested sub-areas + methodologies. This is above the ~25-40 target because 4 agents + operator grounding surfaced more strongly-grounded 2026 work than the bound; per founder guidance (include under-noticed strong work; no silent truncation) I kept the well-sourced set rather than cutting real signal. All are draft-grade pending review.

**Grounded but NOT promoted to full nodes** (kept lean; recorded here for the radar organ to pick up): ESM-C, Proteina/Proteina-Complexa, Fold-CP (2603.14806), FLOWR.root, SPRINT, 3DMolFormer, Apo2Mol is in-graph; AlphaProteo (2409.08022), PepMirror, TD3B (Duke); imaging — MedGemma-base (2507.05201), MedSAM-3 text-promptable (2511.19046), RoentGen-v2 (2508.16783), CT-FM (2501.09001), Merlin, CADS, ConVOLT is in-graph; SegWithU (2604.15271), conformal fairness (2605.14260); clinical — HuatuoGPT-o1 (2412.18925), Fleming-R1 (2509.15279), Doctor-R1 (2510.04284), MedMO (2602.06965), VPRMs (2601.17223), BRIDGE (2504.19467), MedXpertQA (2501.18362), DiagnosisArena (2505.14107), MedBench v4 (2511.14439), medical-hallucinations taxonomy (2503.05777); genomics/cell — HyenaDNA, Caduceus, GENERator, JEPA-DNA (2602.17162), Cell-JEPA, PerturbDiff (2602.19685), scDFM (2602.07103), Chreode (2605.28111), PerturbCellRL (2606.27752), Tahoe-100M (in-graph as benchmark), EVA (2602.10168), SEAL (2602.14177), PAST, CellForge (2508.02276), AutoScientists (2605.28655), Virtual Cell Challenge perspective (Cell S0092-8674(25)00675-0).

**Honest gaps / could not fully verify:**
- **Paywalled full texts:** Nature/Nature-Medicine AMIE 2026, Evo 2, AlphaGenome, Robin, Biomni (Science), ESM3, BioEmu — claims taken from preprints + official blogs + abstracts, not the peer-reviewed tables. Several **bioRxiv PDFs returned 403** (Boltz-2, Chai-2, Protenix, RFdiffusion2) — numeric claims are from abstracts / official announcements / secondary coverage, not a full read of every results table.
- **Exact numbers unextracted:** Baichuan-M3 (abstract exposes no scores), EHR-Complex per-model rates, OpenFold3 vs AF3 LDDT/DockQ ("competitive across most modalities" only), Proteina-Complexa (no numeric benchmarks in abstract).
- **Hypothesis-grade / aggregator sources:** MedXpertQA leaderboard top-entry names (llm-stats.com), DR.INFO vendor self-report, Virtual Cell Challenge exact final leaderboard numbers, STATE numbers (Arc's own pages, no independent reproduction). Flagged as such above.
- **2026-numbered arXiv ids (26MM.NNNNN)** are verified via HF `paper_search` index rather than an individual PDF fetch for each; titles/authors/dates are from that index and may reflect a revision rather than v1.
- No benchmark was independently re-run; all SOTA numbers are as-claimed by the cited source.

**Deferred sub-threads** (queued for radar continuation): MRI k-space reconstruction FMs; ultrasound/echo FMs; digital-pathology↔spatial-transcriptomics generative models; FDA/regulatory-specific reliability frameworks; dedicated OpenAI/DeepSeek/Google *medical* 2026 model reports (surfaced only as baselines).
