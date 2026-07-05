# RESEARCH.md — Disposition of the AGI-witness PARTIAL, the conditional composition law, and the honest novelty ledger

**Author:** Fable 5 (`claude-fable-5`, expires 2026-07-07) · **Date:** 2026-07-05
**Status:** durable research asset for the team that continues after Fable is gone.
**Provenance discipline:** claims are marked `[verified]` (checked against live web or the repo
this session) or `[weights]` (from Fable's ~Jan-2026 prior — re-verify before relying on it).
**Inputs read:** `docs/AIOS_AGI_CERTIFICATION_KEYSTONE.md`, `docs/AIOS_KEYSTONE_EXPERIMENT.md`,
`experiments/agi_witness/README.md`, `experiments/agi_witness/results/REPORT.md`, plus the raw
run ledger `experiments/agi_witness/results/runs.jsonl` (451 rows), the drive logs, `score.py`,
and commit `f3cccd1` — all `[verified]`.

---

## 1. Honest disposition of the PARTIAL witness

### 1.1 What PARTIAL actually was: a scoring artifact, not an evidential state

The on-disk `results/REPORT.md` (mtime 17:13) says **PARTIAL — "missing arm data: A; B; C"**.
The raw ledger contains **all 451 outcome rows for every arm** `[verified]`:

- A, B, C × seeds {0,1,2} (24 eval tasks each; C seed 2 truncated at 19 — see confound #5),
- all five ablations `C-ablate-{apex,iris,descent,goen,writeback}` × seeds {0,1}.

The cause was a `score.py` ↔ `run.py` seam bug: `_canonical_arm` expected an integer `tier`,
but `run.py` writes the solver model-id string (`nim:qwen/qwen3-next-80b-a3b-instruct`), so every
row was folded to a tier-2 pseudo-arm and the scorer found "no" A/B/C. Commit `f3cccd1`
(codex@myworld, 19:15) fixed the seam and re-scored the **same 451 rows**; I independently
re-ran the fixed scorer this session and reproduce it exactly `[verified]`:

> **VERDICT: TAXONOMY — K1 fired** (median C = 17 ≤ median max(A,B) = 17 + ε=3, paired by seed)
> **and K2 fired** (only 1/4 single-certificate ablations degrade C by >2·SE).

So the first honest correction for the record: **the witness did not come back PARTIAL. It came
back TAXONOMY under the pre-registered kill criteria.** The stale REPORT.md should be
regenerated from the fixed code path so the repo never shows two verdicts for one dataset.

### 1.2 The actual numbers (from `runs.jsonl`, all `[verified]`)

R1, 24 eval tasks, budget 40k tokens/(arm,seed), solver `nim:qwen/qwen3-next-80b-a3b-instruct`:

| arm | verified (seeds 0/1/2) | median | submitted | precision | P0 | P1 | P2 |
|---|---|---|---|---|---|---|---|
| A (monolith) | 17 / 17 / 17 | **17** | 24 | 0.708 | 24/24 | 12/24 | 15/24 |
| B (independent certs) | 13 / 13 / 13 | **13** | 15 | 0.867 | 24/24 | 0/24 | 15/24 |
| C (coupled) | 17 / 17 / 15* | **17** | 21 | 0.810 | 24/24 | 11/21 | 14/22 |

\* C seed 2 completed only 19/24 tasks (38,414 tokens ≈ the 40k cap).

Ablations (median): −apex **17**, −iris **17**, −goen **17**, −writeback **17** (Δ=0 each);
−descent **13** (Δ=4 > 2·SE≈1.75 — the only rent). R6 write-back Δ=0. R7 (tier-2) not run.

### 1.3 The confounds and degeneracies, ranked by how much of the verdict they own

**#1 — Dataset contamination: the spec never lived only in the ledger (the design's core
premise is violated).** Arm A solves 17/24 — including 24/24 on the clean subset and 12/24 on
*poisoned-ledger* tasks — **without any trusted spec**. MBPP is one of the most contaminated
benchmarks in existence; models have memorized its solutions (EvoEval-style semantic rewrites
drop top-model pass@1 by 19–47 points; LiveCodeBench exists precisely because of this)
`[verified — see §3.D]`. The pre-registration enforced "generation trivial GIVEN spec" (pilot
gate) but never enforced the converse: **"generation fails WITHOUT spec."** The spec lived in
the solver's weights, so (a) the task was not verification-bound, (b) the poison could not bind
(A ignores the ledger and still scores), and (c) the whole regime — chosen to be maximally
favorable to certificates — was actually maximally favorable to the monolith's memory. This is
the single largest confound and it is fatal to interpreting this run as a test of the thesis.

**#2 — Ceiling on P0 + degenerate calibration → GoEN and APEX-calibration were constants.**
All arms score 24/24 on the clean subset (no headroom, no verification-tax signal), and the
drive log shows `[fit_goen] degenerate calibration (1.00 solved) -> constant model (base-rate)`
for both fits `[verified]`. A constant certificate cannot produce ablation rent *by
construction* — the −goen Δ=0 is uninformative about GoEN, it only confirms a constant does
nothing.

**#3 — Three of four certificates were behaviorally inert, not merely unhelpful.** The −apex,
−iris, −goen ablation arms have **token totals identical to C to the digit** (24,773 / 32,533
for seeds 0/1) `[verified]` — removing them did not change the trajectory at all. IRIS was
degenerate throughout: 214/451 rows note `iris_identified=True n_classes=1` (every candidate
set collapsed to one behavior class, so identifiability was trivially true and selected
nothing). The composition being tested was in effect **C = A + DescentNet-repair**, not a
four-certificate coupling. K2 ("composition is decoration") fired *correctly* about this run —
but it measured the degeneracy, not the thesis.

**#4 — The metric structurally rewards ignoring certificates on poisoned tasks.** On P1
(contradictory ledger) the certified arm B abstains everything (`abstain: apex=CONTRADICTORY`,
0/24 solves) while A guesses and banks 12/24 — because hidden tests exist and wrong submissions
cost nothing. Verified-solves-at-budget gives **zero credit for correct abstention and zero
penalty for reckless submission**, despite the design naming "knowing-when-to-abstain" as part
of the difficulty. Under this metric the optimal policy provably discards APEX. Meanwhile the
pre-registered *secondary* metric shows the real effect: **precision B 0.867 > C 0.810 > A
0.708** — certificates bought calibration, not solve-count. Reported straight: that is a real,
pre-registered-secondary finding, not the keystone.

**#5 — Harness validity: C seed 2 truncated (19/24 tasks) by budget exhaustion; A/B are
deterministic across seeds (17/17/17, 13/13/13, near-identical token counts), so "3 seeds" ≈ 1
replicate and the bootstrap SE is decorative; the scorer bug (#1.1) shipped a wrong verdict to
disk.** None of these flip the outcome, but all must be fixed before a verdict can be called
exhaustive.

**#6 — The one live coupling did exactly one thing: recover what abstention lost.**
C − descent = 13 = B exactly; C = 17 = A exactly `[verified]`. DescentNet H⁰-repair converts
B's P1 abstentions back into attempts (11/21 on P1). That is real causal work (the only rent in
the run, Δ=4) — but its ceiling in this regime is *recovering the uncertified baseline*, because
the monolith was never actually handicapped (#1).

### 1.4 What this run does and does not establish

**Established (earned):**
- In a contamination-compromised, generation-easy regime, the full certificate stack adds
  **zero verified-solve value** over a monolith at equal budget — consistent with, and
  extending, the prior earned negative (`AIOS_KEYSTONE_EXPERIMENT.md`).
- Certificates buy **precision/calibration** (0.867 vs 0.708), and DescentNet **H⁰-repair**
  (not H¹ detection — that was already retired in R3/R4) does real work: it restores coverage
  that certified abstention gives up, while holding precision above the monolith.
- The harness itself now works end-to-end (dataset → arms → ablations → scorer) — a real asset.

**Not established:**
- Anything about the thesis. The kill criteria fired on a regime that violated its own premise
  ("all difficulty is verification+coordination"). This TAXONOMY is a **verdict about the run**,
  not yet an exhaustive negative about the composition. Declaring the thesis dead on this run
  would be laundering in the negative direction (rule 5 both ways); declaring it alive because
  "the run was invalid" without running the fixed version would be laundering in the positive
  direction. The only honest state is: **TAXONOMY-on-an-invalid-regime; the decisive experiment
  is still owed and is now precisely specifiable.**

### 1.5 The sharpest next experiment (V2) — resolves to WITNESS or earned TAXONOMY

One redesign, four gates, two co-primary metrics, one decision tree. Everything below is
pre-registerable now.

**V2 task family — adversarially-named synthetic spec-bound programs.** Generate ~100 fresh
tasks per run (seeded): each is a function whose true behavior contains **arbitrary,
unguessable semantics** (random constant tables, randomized branch thresholds, permuted output
conventions, random finite transductions), and whose **name and signature deliberately suggest
a plausible-but-wrong semantics** (e.g. `def sort_desc(xs)` whose spec actually sorts ascending
except at three random pivot keys). This makes the memorization/prior-guessing strategy
*anti-correlated* with truth instead of merely unavailable — the strongest possible enforcement
of "the spec lives only in the ledger." The behavioral spec (typed claims, as now) is seeded
into the ledger; hidden tests are generated from the true semantics. No public benchmark, no
contamination window at all (stronger than LiveCodeBench's freshness approach, and available
offline).

**Regime-validity gates (all four must pass BEFORE R1; each failure aborts and resamples):**
- **G1 — no-ledger floor:** monolith arm with the ledger withheld must score ≤ 10% pass. (The
  check whose absence sank V1.)
- **G2 — trusted-spec ceiling:** solver with the clean full spec must reach ≥ 60% pass@k
  (kept from V1 — generation must stay easy given a trusted spec).
- **G3 — calibration non-degeneracy:** calibration-split solve-rate ∈ [0.2, 0.8], else GoEN and
  APEX thresholds are constants again and their ablations are void by construction.
- **G4 — poison bite:** raw-claims monolith on P1 must drop ≥ 20 points vs P0. (Poison that a
  certificate-free reader can shrug off tests nothing.)

**Poison with recoverable ground truth.** Split P1 into **P1-R (repairable)**: a minority of
claims poisoned, true spec uniquely recoverable by consistency reasoning over the majority —
this is where C can legitimately beat A (A is misled, B abstains, C repairs); and **P1-U
(unrecoverable)**: genuinely underdetermined — correct behavior is abstention, and only a
calibrated arm can know that. V1 had no P1-R/P1-U distinction, so there was no task on which
coupling *could* express superiority.

**Metrics.** Keep verified-solves-at-budget primary, and add a **co-primary penalized score
S₁ = verified − 1·(false submissions)** (λ=1 pre-registered; deployment semantics: a wrong
certified answer costs what a right one earns). Report risk–coverage (AURC) as secondary. This
removes the structural reward for ignoring certificates (#4) without letting precision alone be
claimed as the keystone after the fact.

**Harness fixes (all cheap):** scorer asserts arms {A,B,C} present or exits nonzero; truncated
tasks counted as failures and truncation reported; solver temperature > 0 (or resampled
candidate pools) so seeds are actual replicates; regenerate REPORT.md only from the fixed code
path; n≈100 eval tasks; re-run the tier-2 absorption probe (R7) after the primary verdict.

**Decision tree (named exits):**
- **WITNESS:** C > max(A,B) + ε on either co-primary, with ≥3/4 single-certificate ablation
  rents, under all four gates → existence witness earned (prevalence still owed, rule 4).
- **TAXONOMY (exhaustive):** C ≤ max(A,B) + ε on both co-primaries *in a regime that passed
  G1–G4* → the composition thesis is dead in its maximally-favorable regime; publish the
  negative — "certification layers do not pay at current scale even when the task is
  verification-bound by construction" is itself a strong, citable result.
- **Calibration-only middle:** C ties on solves but wins on S₁/precision only → downgrade the
  claim honestly to "certificates buy calibration, not capability," and ship it as engineering
  (the `aios guard` pattern), not as an AGI-layer claim.

V2 costs roughly 4× V1 (more tasks, temperature sampling) on the same free NIM tier + CPU —
feasible within days.

---

## 2. The composition-law formalization — CONDITIONAL

> **GATE (no theory-theater):** everything in this section is *worth writing down as
> mathematics only if V2 exits at WITNESS* (or, weaker, at calibration-only with ablation
> rents). If V2 exits TAXONOMY, this section's value is one page of documentation for why the
> formalism was never built. Do not develop it speculatively; the empirical result is the
> license.

### 2.1 The recognition: all four certificates are invariants of ONE descent problem

Fix a **site** (𝒞, J): objects of 𝒞 are *contexts* (agent × task-scope views of the shared
ledger); morphisms are context restrictions; a family {Uᵢ → U} is a *cover* in J when joint
observation over the Uᵢ suffices to determine claims on U. Let **F** be the presheaf of typed
claims/certificates on this site (the Akashic ledger *is* F). A question q with candidate local
answers is a **descent datum**: local sections sᵢ ∈ F(Uᵢ) with comparison data on overlaps.

Then the four components are not four modules — they are the four classical questions about
this single descent problem:

| component | is exactly | in the formalism |
|---|---|---|
| DescentNet | the obstruction to gluing | Čech class [δs] ∈ Ȟ¹(U, F); H⁰-repair = subtracting a coboundary (the ONLY component that did causal work in V1 — note the formalism already "knew" repair and detection are different operations) |
| APEX | answerability / abstention | existence of a global section: Ȟ⁰(U, F_q) ≠ ∅; abstention is *forced* (not heuristic) whenever the obstruction class is nonzero |
| IRIS | identifiability / decoherence | uniqueness of the global section: the gluing map's fiber = observational-equivalence class; identified ⟺ singleton |
| GoEN | rewiring / legibility | a change of coverage — a refinement of covers V → U (or Grothendieck topology J → J′) chosen to kill the obstruction: [δs] ∈ ker(Ȟ¹(U,F) → Ȟ¹(V,F)) |
| Akashic write-back | population coupling | sheafification step: a proven global section is adjoined as a new covered object of the site; *other agents' descent problems are henceforth computed over the enlarged site* |

### 2.2 The composition law (a theorem-shaped law, not a wiring convention)

The law is the **exactness of the Čech complex plus contravariant functoriality of Ȟ• under
cover refinement**:

```
0 → Ȟ⁰(U,F) → ∏F(Uᵢ) → ∏F(Uᵢⱼ) → Ȟ¹(U,F) → …      (one exact sequence)
ρ_UV : Ȟ¹(U,F) → Ȟ¹(V,F)   for every refinement V → U   (functoriality)
```

Every certificate is a stage of this one sequence, so certificates constrain each other **by
exactness**, which is precisely "one certificate constrains another's search space":

1. [δs] ≠ 0 ⟹ Ȟ⁰ = ∅ over that cover ⟹ **APEX abstention is entailed**, not chosen —
   DescentNet output *is* an APEX verdict.
2. A DescentNet repair is admissible iff the class dies (is a coboundary); when it does, **IRIS
   bounds the repair set** — the number of inequivalent glued sections is the size of the
   observational-equivalence fiber.
3. GoEN's reachable rewirings form a subposet **R** of covers. The composed system can answer q
   iff the obstruction dies somewhere reachable: [δs] ∈ ⋃_{V∈R} ker(ρ_UV). Define the
   **persistent obstruction** as the image of [δs] in colim_{V∈R} Ȟ¹(V, F).

**Persistent obstruction ≠ 0 ⟺ no reachable rewiring can make q answerable.** That is a
*certified impossibility* — a budget-independent stopping certificate for structural search.

### 2.3 The concrete witness this formalism claims and nothing else does

Existing formalisms each give one fragment: conformal/selective prediction gives abstention
with **no repair story**; CRDTs give convergence with **no question-relative answerability**;
NAS/rewiring searches with **no obstruction-driven impossibility bound**; contextuality theory
(Abramsky–Brandenburger) gives the obstruction but has **no reachable-rewiring poset and no
resource model**. Only the composed object yields the per-(question, ledger) **trichotomy**:

- (a) answerable now (Ȟ⁰ ≠ ∅);
- (b) answerable after reachable rewiring (class dies within R);
- (c) **certifiably unanswerable under every reachable rewiring** (persistent class ≠ 0).

Type-(c) certificates are the non-factorization witness: no component alone, and no existing
framework for any component, can emit "stop searching — no restructuring in your action space
can fix this," with a proof.

**Anti-theory-theater requirement:** the witness must be *behavioral*, not notational. Build
matched task pairs of types (b) and (c) with identical surface statistics; the coupled arm must
repair (b) and fast-abstain (c), with a measurable token savings on (c) versus every uncoupled
arm (verified-solves-per-token again). If the coupled system's behavior does not track the
trichotomy, the formalism is decoration and must be dropped regardless of its elegance.

**Resource-bounded caveat (collapse-mode 1 reappears here):** computing Ȟ¹ and refinement maps
costs tokens; the verification tax lives in the boundary maps. Any formal development must
include *budgeted descent* — which covers/refinements are computable within B_tok — or the
formalism silently assumes away the very objection the panel raised.

### 2.4 Why sheaf/descent and not Poly or optics as the primary object

Poly (positions = certificate verdicts, directions = evidence demands; arms as wiring diagrams;
Org/[Poly,Poly] comonoids for *learned* coupling — matching nemotron's "the composition must be
learned") is the right **implementation and plumbing language**, and optics/lenses correctly
capture each certificate's bidirectionality (forward: constrain generation; backward: update on
evidence). But both are *interface disciplines*: their laws say when things compose, not when
verification succeeds. Neither yields the impossibility theorem. Čech descent is the only
candidate where the composition law is a **theorem** (exactness + functoriality) rather than a
diagram convention. The sane architecture, if ever built: a Poly-wired system whose shared
state is the sheaf F, with the cohomological certificates as the wire contents. `[weights —
the judgment; the cited frameworks are real]`

### 2.5 Honest boundary of §2

The mathematics above is standard. Abramsky–Brandenburger already did "empirical models as
local sections; contextuality as gluing obstruction," including cohomological witnesses;
Hansen–Ghrist already did agent belief sheaves; Vorob'ev and the acyclic-database theorem
already characterized when pairwise-consistent local data glue; and 2025–26 papers are actively
colonizing sheaf-MAS territory (§3.A) `[verified]`. If this section ever becomes a paper, the
only two pieces with a chance of being genuinely new are:

- **N1:** the identification *structural rewiring = coverage refinement*, making **persistent
  obstruction a stopping certificate for architecture/topology search** (nothing in the NAS,
  rewiring, or contextuality literature couples these `[weights — verify with a fresh search
  before claiming]`);
- **N2:** **budgeted descent** — descent theory with a token/FLOP resource bound on which
  covers are computable, i.e. "certified generation under budget" as approximate colimit.

Both die if V2's empirical witness fails. Claim neither until it fires.

---

## 3. Must-read prior art (before ANY novelty claim)

Read in this order. Items marked `[verified]` were surfaced/checked against live search this
session (2026-07-05); items marked `[weights]` are from Fable's prior — confirm the citation
before quoting it.

### A. The composition's own mathematics is already occupied — read these FIRST

1. **Abramsky & Brandenburger**, "The sheaf-theoretic structure of non-locality and
   contextuality" (NJP 2011) `[weights]` — local sections, gluing obstruction, the exact
   skeleton of DescentNet. The panel missed this; it is the closest single prior work.
2. **Abramsky, Barbosa, Mansfield et al.**, "The cohomology of non-locality and contextuality"
   (2011–12) `[weights]` — Čech-cohomological *witnesses* of obstruction, i.e. certificate
   objects, a decade before this program.
3. **Vorob'ev** (1962), and **Beeri–Fagin–Maier–Yannakakis**, "On the desirability of acyclic
   database schemes" (JACM 1983) `[weights]` — when pairwise-consistent marginals/local
   relations glue globally. DescentNet's gluing question was *solved as a characterization* for
   the relational case in 1983; any claim must say what is added beyond running-intersection.
4. **Hansen & Ghrist**, "Opinion dynamics on discourse sheaves" (2020) + "Toward a spectral
   theory of cellular sheaves" (2019) `[weights]` — multi-agent belief as sheaf sections; sheaf
   Laplacians (the spectral H¹ machinery the keystone benches used).
5. **Schmid**, "Applied Sheaf Theory for Multi-agent AI (RL) Systems: A Prospectus"
   ([arXiv 2504.17700](https://arxiv.org/abs/2504.17700)) `[verified]` — 2025; the exact
   "sheaves for multi-agent AI" territory, as a prospectus.
6. "A Sheaf Framework for Strategic Multi-Agent Systems: From Consensus to Nash Equilibria"
   ([arXiv 2606.01663](https://arxiv.org/pdf/2606.01663)) `[verified]` — 2026; sheaf-MAS is
   being claimed *now*.
7. "Sheaf-Theoretic Transport and Obstruction for Detecting Theory Shift in AI Agents"
   ([arXiv 2605.14033](https://arxiv.org/pdf/2605.14033)) and "Relative Obstructions and
   Spectral Diagnostics for Sheaves on Cell Complexes"
   ([arXiv 2601.19056](https://arxiv.org/pdf/2601.19056)) `[verified]` — 2026 obstruction
   diagnostics for agents; overlaps DescentNet's detection role directly.
8. **Bodnar et al.**, neural sheaf diffusion (NeurIPS 2022); **Robinson**, sheaves for sensor
   fusion (2017); **Curry**, thesis (2014) `[weights]` — the applied-sheaf canon.

### B. The load-bearing empirical claim ("verification is the binding constraint") is now a mainstream, *tested* hypothesis — you are not proposing it, you are competing in it

9. "Trust but Verify! A Survey on Verification Design for Test-time Scaling"
   ([arXiv 2508.16665](https://arxiv.org/html/2508.16665v3)) `[verified]` — the field map;
   verifier-based vs verifier-free test-time scaling.
10. "Shrinking the Generation-Verification Gap with Weak Verifiers"
    ([arXiv 2506.18203](https://arxiv.org/html/2506.18203v1)) `[verified]` — weak verifiers
    close most of a 9B→27B gap; directly relevant to "certificates as cheap verifiers."
11. "Variation in Verification: Understanding Verification Dynamics in LLMs"
    ([arXiv 2509.17995](https://arxiv.org/abs/2509.17995)) and "Learning to Self-Verify Makes
    Language Models Better Reasoners" ([arXiv 2602.07594](https://arxiv.org/pdf/2602.07594))
    `[verified]` — when verification does/doesn't pay, and monolith-absorption in action
    (collapse-mode 2 is being *built*, not just feared).
12. **Snell et al.**, "Scaling LLM Test-Time Compute Optimally…" (2024, arXiv 2408.03314);
    **Brown et al.**, "Large Language Monkeys" (2024, arXiv 2407.21787); **Lightman et al.**,
    "Let's Verify Step by Step" (2023, arXiv 2305.20050) `[weights]` — the compute-allocation
    baselines any per-FLOP claim must beat.
13. **Kirchner et al.** (OpenAI), "Prover-Verifier Games improve legibility of LLM outputs"
    (2024, arXiv 2407.13692) `[weights]` — *legibility* as a trained property. GoEN's naming
    and framing collide with this; read before using the word "legibility" in any claim.

### C. APEX's lane is crowded (2024–26 conformal abstention for LLMs)

14. "Language Models with Conformal Factuality Guarantees"
    ([arXiv 2402.10978](https://arxiv.org/html/2402.10978)) `[verified]`.
15. "Geometry-Calibrated Conformal Abstention for Language Models"
    ([arXiv 2604.27914](https://arxiv.org/html/2604.27914)); "Entropy Alone is Insufficient for
    Safe Selective Prediction in LLMs" ([arXiv 2603.21172](https://arxiv.org/pdf/2603.21172));
    "Robust Conformal Prediction for LLMs via Internal Representations"
    ([arXiv 2604.16217](https://arxiv.org/pdf/2604.16217)); "Adaptive Conformal Semantic
    Entropy" ([arXiv 2605.04295](https://arxiv.org/html/2605.04295)); "Differentiable Conformal
    Training for LLM Reasoning Factuality" ([arXiv 2604.20098](https://arxiv.org/pdf/2604.20098))
    `[verified]` — 2025–26; APEX must position against these or not at all.
16. **Chow** (1957); **El-Yaniv & Wiener** (2010) selective prediction / risk–coverage
    `[weights]` — also the correct scoring theory for V2's abstention metric (§1.5).

### D. Benchmark validity — the confound that sank V1 has its own literature

17. **LiveCodeBench** (ICLR 2025,
    [proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/file/94074dd5a072d28ff75a76dabed43767-Paper-Conference.pdf))
    `[verified]` — contamination-controlled, time-windowed code eval; documents stark pass-rate
    drops after model cutoffs on HumanEval/MBPP-era tasks.
18. **EvoEval** (Xia et al. 2024) `[weights]`; contamination quantification for code (Riddell
    et al. 2024, arXiv 2403.04811) `[weights]`; "Where Do LLMs Still Struggle: An In-Depth
    Analysis of Code Generation Benchmarks"
    ([arXiv 2511.04355](https://arxiv.org/html/2511.04355v1)) `[verified]`;
    **Code2Bench** ([arXiv 2508.07180](https://arxiv.org/pdf/2508.07180)) `[verified]` —
    dynamic benchmark construction, the V2 task-generation approach has cousins here.

### E. Remaining components' canons (read to avoid re-deriving)

19. IRIS: **Pearl / Bareinboim** causal identifiability; **Hyvärinen & Morioka** nonlinear ICA
    (2016–17); **Khemakhem et al.** iVAE (2020) `[weights]`.
20. Akashic: Certificate Transparency (RFC 6962/9162); W3C Verifiable Credentials; **Shapiro et
    al.** CRDTs (2011); Chandy–Lamport snapshots `[weights]`.
21. ACT toolkit: **Niu & Spivak**, *Polynomial Functors: A Mathematical Theory of Interaction*;
    **Capucci et al.**, "Towards Foundations of Categorical Cybernetics" (2021); **Hedges**,
    compositional game theory; **Fong & Spivak**, *Seven Sketches*; **Cruttwell et al.**,
    "Categorical Foundations of Gradient-Based Learning" (2021) `[weights]`.

---

## 4. Honest novelty verdict

### 4.1 Component by component

| component | novelty verdict | evidence state after this run |
|---|---|---|
| APEX | **Rebrand.** Selective/conformal abstention; the 2025–26 LLM-conformal literature (§3.C) already does typed abstention with finite-sample guarantees. Any contribution is integration, not invention. | Behaviorally inert in V1 beyond forcing P1 abstention (which the metric punished). Ablation Δ=0 with identical tokens. |
| IRIS | **Rebrand.** Observational-equivalence / identifiability, standard since Pearl/ICA. | Degenerate in V1 (n_classes=1 on every task that reached it). Zero evidence of contribution. |
| DescentNet | **Math is a rebrand** (Čech/AB-contextuality/Vorob'ev/Hansen–Ghrist; the 2025–26 sheaf-MAS papers are moving into the same application). H¹-as-poison-guard is already *retired by our own R3/R4 earned negative*. **But: H⁰-repair-in-the-loop is the one component with measured causal rent in V1** (Δ=4 solves; recovers abstention-lost coverage at precision above the monolith). | The only live wire in the whole stack. Small, real, earned — and bounded: in V1 its ceiling was exactly "recover the uncertified baseline." |
| GoEN | **Rebrand + name collision.** "Legibility" is an OpenAI prover-verifier term of art (2024); rewiring-for-performance is NAS/graph-rewiring. | Never actually tested: constant model due to degenerate calibration. Unearned in the strongest sense — no run has ever exercised it. |
| Akashic | **Rebrand.** Certificate Transparency + VC + CRDT with an agent-facing API. The trusted-writer circularity (panel §2c) remains open; `aios guard` is a partial, shipped, honest patch. | Write-back ablation Δ=0 — population coupling did nothing measurable in V1. |

### 4.2 The composition

The composition is the **only** place genuine novelty can live (panel verdict, confirmed by
§3: every component's lane is individually occupied, several by 2025–26 work). Two candidate
novel objects remain, one empirical and one formal, in strict dependency order:

1. **Empirical (load-bearing, currently unearned and evidence-leaning-negative):**

   > **On a task where the spec verifiably lives only in a poisoned shared ledger (gates
   > G1–G4), a coupled certificate stack beats both the monolith and independent certificates
   > on verified-solves (or penalized score S₁) at equal token budget, with ≥3/4
   > single-certificate ablation rents.**

   This is the single claim that would EARN a real contribution. Nothing in §3.B tests
   *coupled, heterogeneous* certificates under an equal-budget, contamination-controlled,
   population regime — the sheaf-MAS papers are prospectuses/theory `[verified]`, and the
   verification-scaling literature couples at most generator+one-verifier `[verified as of
   this session's search; re-check at V2 write-up time]`. V1's correctly-scored verdict
   (TAXONOMY, K1+K2) is *evidence against* on an invalid regime; V2 decides it.

2. **Formal (gated on 1):** the persistent-obstruction stopping certificate (§2.3, N1) and
   budgeted descent (N2). Without the empirical rent these are theory-theater and must not be
   written up.

### 4.3 What to say publicly today

Exactly what the record supports, nothing more: *"We pre-registered a kill criterion for our
own AGI-certification thesis and it fired on the first run; the run also failed four of its own
regime-validity conditions, which we can now state as gates. Certificates bought calibration
(precision +0.16 over the monolith), not capability; one component (consistency-repair) shows
real causal rent. The decisive, gated experiment is specified and cheap."* That sentence is an
asset — it demonstrates the certification *discipline* the thesis is about, applied to itself.
Any stronger claim in either direction is laundering.

---

*Sources verified this session:
[arXiv 2504.17700](https://arxiv.org/abs/2504.17700),
[arXiv 2606.01663](https://arxiv.org/pdf/2606.01663),
[arXiv 2605.14033](https://arxiv.org/pdf/2605.14033),
[arXiv 2601.19056](https://arxiv.org/pdf/2601.19056),
[arXiv 2508.16665](https://arxiv.org/html/2508.16665v3),
[arXiv 2506.18203](https://arxiv.org/html/2506.18203v1),
[arXiv 2509.17995](https://arxiv.org/abs/2509.17995),
[arXiv 2602.07594](https://arxiv.org/pdf/2602.07594),
[LiveCodeBench @ ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/94074dd5a072d28ff75a76dabed43767-Paper-Conference.pdf),
[arXiv 2511.04355](https://arxiv.org/html/2511.04355v1),
[arXiv 2508.07180](https://arxiv.org/pdf/2508.07180),
[arXiv 2402.10978](https://arxiv.org/html/2402.10978),
[arXiv 2604.27914](https://arxiv.org/html/2604.27914),
[arXiv 2603.21172](https://arxiv.org/pdf/2603.21172),
[arXiv 2604.16217](https://arxiv.org/pdf/2604.16217),
[arXiv 2605.04295](https://arxiv.org/html/2605.04295),
[arXiv 2604.20098](https://arxiv.org/pdf/2604.20098).
Repo evidence: `experiments/agi_witness/results/runs.jsonl` (451 rows), `results/drive_r1c.log`
(GoEN degenerate-calibration lines), `score.py` re-run this session, commit `f3cccd1`.*
