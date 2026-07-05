# Fable 5 — Adversarial Audit of the AIOS / AGI-Certification Program

**Author:** Fable 5 (heterogeneous frontier prior, expires 2026-07-07) · **Date:** 2026-07-05
**Scope:** `AIOS_AGI_CERTIFICATION_KEYSTONE.md`, completion atlas (M0), `experiments/agi_witness/`
(code + `results/runs.jsonl` actually inspected, not just docs), `AIOS_KEYSTONE_EXPERIMENT.md`,
workspace CLAUDE.md/AGENTS.md.
**Method:** I read your artifacts AND re-aggregated your raw run data myself. Several findings
below are about what is sitting in `results/runs.jsonl` right now that your own REPORT.md
does not show you. Ranked most-severe first. No flattery; also no manufactured pessimism —
where a thing is right, I say so.

---

## F1 — CRITICAL — Your witness has ALREADY returned NEGATIVE under your own pre-registered kill criteria, and a scoring bug is reporting it as PARTIAL

**Claim (yours):** `results/REPORT.md` → "VERDICT: PARTIAL … missing arm data: A; B; C".
M0 §H3 repeats this ("A/B/C R1 medians absent").

**Reality (your own runs.jsonl, re-aggregated):** R1 is COMPLETE — A,B,C × seeds 0,1,2 and all
five ablations × seeds 0,1 are present. The numbers:

| arm | verified solves (seeds 0/1/2) | notes |
|---|---|---|
| A (monolith) | **17 / 17 / 17** of 24 | submits everything |
| B (independent certs) | 13 / 13 / 13 | abstains 9 (8× "apex=CONTRADICTORY" = all of P1) |
| C (coupled) | **17 / 17 / 15** | seed 2 attempted only 19/24 tasks — budget exhausted |
| C−apex | 17 / 17 | **byte-identical to C** (same token counts, cache reuse) |
| C−iris | 17 / 17 | same solves as C |
| C−goen | 17 / 17 | **byte-identical to C** |
| C−writeback | 17 / 17 | same solves as C |
| C−descent | 13 / 13 | drops via self-imposed abstention (see F5) |

Median C = 17. Median max(A,B) = 17. SE across seeds ≈ 0 (see F4) so ε = floor = 3.
**K1 fires: median C ≤ median max(A,B) + ε.** Only 1 of 4 single-cert ablations degrades C
(**K2 fires: composition is decoration** — three ablations are literally the same cached LLM
calls replayed). Under `README.md` §KILL CRITERION, this run's verdict is **TAXONOMY /
earned negative**, not PARTIAL.

**Why the report lies:** `score.py:69-71` (`_canonical_arm`): `tier = row.get("tier", 1) or 1;
if tier != 1: return f"{arm}@t{tier}"`. `run.py` writes `tier` as the model STRING
(`"nim:qwen/qwen3-next-80b-a3b-instruct"`), so every row is folded to
`A@tnim:qwen/...` and the scorer finds zero A/B/C rows. A team whose entire brand is
"no-launder" is currently — accidentally — laundering a fired kill-criterion into "PARTIAL,
evidence incomplete." The longer this stands, the more it looks motivated.

**Corrective:** Treat a string/tier-1-model value as tier 1 in `_canonical_arm` (or write
`tier: 1` + `solver_model` separately in `run.py`), rescore, and publish the negative straight
— subject to the validity caveats in F3/F4, which cut BOTH ways (this run also could not have
detected a true positive; say that too).

---

## F2 — CRITICAL — Arm C's population coupling is oracle-contaminated: write-back is gated on the hidden test suite

**Claim (yours):** Coupling#4 "a VERIFIED solve writes PROVEN IO claims back into the shared
ledger" — the population/Akashic coupling, the thing R6 exists to isolate.

**Reality:** `arms.py::_run_task_C`: `verified = _verify(task, cands[pick])` where `_verify`
is documented as **"Scoring truth: run the candidate against the task's HIDDEN test_list"**
(arms.py:199-200); write-back happens only `if verified and writeback_on`. The decision to
write to the ledger uses ground truth that does not exist at inference time. In deployment,
without the oracle, you would write back IO claims from plausible-but-wrong code — i.e. the
population coupling as implemented would POISON the ledger, which is precisely the failure
your whole Akashic-trust program (H1) worries about. Had C won via write-back, the result
would have been invalid; since C lost anyway, this is a latent landmine for the "full ~100-task
prevalence rung."

Deeper irony worth naming in the report: your certification-layer experiment needed **test
execution** as its internal source of truth. That is the thesis's own counterexample — the
cheapest, dominant verifier is running the tests, not typed certificates about them.

**Corrective:** Gate write-back on cert-internal signals only (claim-consistency of the picked
candidate, IRIS identification), and add a "ledger-poisoning rate under no-oracle write-back"
measurement. If precision of the no-oracle gate is low, coupling#4 is not deployable, period.

---

## F3 — CRITICAL — The regime premise ("all difficulty is verification") is false in your own data: the spec was never actually removed

**Claim (yours):** "~100 MBPP problems with their spec REMOVED; the behavioral spec lives ONLY
in a shared ledger… Generation is trivial *given a trusted spec*… so ALL difficulty is
verification + coordination" (README §Regime). "This is the certificates' maximally-favorable
regime by construction."

**Reality:** Three leaks make the regime nothing of the sort:
1. `_spec_prompt` gives the solver the **MBPP function name** ("Define a Python function named
   `remove_odd`…"). MBPP names are descriptive mini-specs.
2. **MBPP is in the training set of every frontier solver.** The solver has memorized these
   exact problems. "Spec-in-the-ledger" is cosplay when the spec is in the weights.
3. The observed data proves it: **P0 (clean) = 8/8 for EVERY arm** — a hard ceiling with zero
   headroom for certificates to add value on a third of the tasks — and the monolith solves
   **17/24 with poisoned ledgers present** (P1 4/8, P2 5/8) by just ignoring the noise.

So the task is NOT verification-bound; it is memorization-bound with a poisoned side-channel
the monolith can shrug off. A negative here is therefore NOT the "devastating exhaustive-
impossibility" the pre-registration promises — the regime never isolated the thing being
tested. (Note this cuts in the thesis's favor for once: the earned negative of F1 is
run-valid under the registration but weaker as evidence than the registration claims.)

**Missing control that would have caught this for free:** an arm A0 with **no ledger at all**
(function name only). If A0 ≈ A ≈ 17/24, the entire claims channel is decorative and every
arm comparison is measuring noise around a memorization baseline.

**Corrective:** (a) Run A0 now — it is one config line and settles the channel question.
(b) If the program continues, use non-public tasks: obfuscated function names (`f_37`),
mutated semantics (so memorized MBPP answers FAIL hidden tests), or synthetic function
families. Only when A0 collapses and A-with-ledger recovers is the regime real.

---

## F4 — HIGH — The three "seeds" are pseudo-replicates; every statistic downstream is theater

**Reality:** `_generate` samples with `seed=seed+i`, i∈0..k-1, k=6, against a content-addressed
cache keyed on (model, prompt, seed). Run-seed 0 uses sample-seeds {0..5}, run-seed 1 uses
{1..6}, run-seed 2 uses {2..7} — **adjacent seeds share 5 of 6 samples.** Result, visible in
runs.jsonl: A = 17/17/17 with token totals 29753/29692/29673. Bootstrap SE over three nearly
identical numbers ≈ 0, so the pre-registered ε collapses to its floor (3), CIs are decorative,
and "median over seeds" is a rhetorical device. Compounding: 24 tasks instead of the
pre-registered ~100 means ε=3 is ~18% of A's score — only a monster effect could ever fire the
witness. The run was simultaneously unable to produce a false positive AND unable to detect a
true one.

**Corrective:** `seed*1000 + i` (disjoint sample sets), ≥100 tasks per registration, and
report min-detectable-effect alongside ε so power is explicit before the run, not after.

---

## F5 — HIGH — The K2 "ablation rent" test is gameable, and the one ablation that bites is exactly the gamed case; one cert is decoration in the literal source-code sense

**Reality (descent):** C−descent drops 17→13 not because solving degrades but because C's OWN
pipeline abstains: 8 P1 tasks exit with "abstain: residual H0 CONTRADICTORY post-repair",
**0 tokens spent**. Meanwhile arm A solves 4/8 of those same tasks by just answering.
DescentNet's "rent" is manufactured by a wiring rule that takes the pipeline hostage when the
repair step is removed. Degradation-relative-to-C's-own-abstention-policy is not evidence a
certificate produces value; it is evidence you built a dependency.

**Reality (iris):** in `_run_task_C`, `iris_certify(...)` is computed and then **its output is
used only in the log-note string**; the actual pick is `_consistent_pick` regardless. IRIS is
decoration in the code, which is why its ablation moves nothing. The witness cannot possibly
credit IRIS because IRIS is not wired to anything.

**Corrective:** K2 must be defined as "ablation reduces verified solves below the MONOLITH
floor on the affected subset," not "below C's own abstention-happy self." And wire IRIS to an
actual decision or remove it from the arm honestly — right now arm C is a 2.5-certificate
pipeline marketed as 4.

---

## F6 — HIGH — Pre-registration integrity has already drifted in three mutually inconsistent records

- `README.md` §KILL CRITERION: R1 = tier-1 `openai/gpt-oss-120b`, ~100 eval tasks.
- The run: `nim:qwen/qwen3-next-80b-a3b-instruct`, 24 tasks.
- `data/pilot.json`: `"chosen_solver": "nim:openai/gpt-oss-120b"` ("pass@k 0.883 vs 0.850").
- `drive_r1.sh` + README elsewhere: qwen was "pilot-chosen (pre-registered)".

The pilot's own artifact chose gpt-oss-120b; the driver ran qwen and calls it pilot-chosen.
Whatever the (probably innocent: empty_rate 0.13) reason, a pre-registration whose solver,
task count, and tier-1 identity differ across three files is not a pre-registration — it is a
menu of post-hoc escape hatches. This matters double because "frozen before any eval run" is
the document's first sentence.

**Corrective:** One frozen REGISTRATION.md, hash-committed before runs; every deviation gets a
dated DEVIATIONS section entry with reason. You built exactly this discipline for DACON; apply
it to yourselves.

---

## F7 — HIGH — The thesis: correct diagnosis, unproven (and repeatedly self-disconfirmed) product

**Is "verification is the binding constraint at the frontier" true?** As a diagnosis, largely
YES — and it is CONSENSUS, not an edge. The entire 2024-26 frontier trajectory (verifier-gated
RL / RLVR, process reward models, debate, self-consistency, test-time search against checkers)
is the field acting on that diagnosis. RLVR works precisely where verification is cheap (math,
code-with-tests); the open frontier is tasks WITHOUT cheap verifiers. Your panel's collapse
mode 2 ("monolith absorption") is therefore not a hypothetical — it is the observed direction
of travel: verification value is accruing INSIDE models and training loops, not in external
OS layers wrapped around API calls.

So the load-bearing question was never "is verification important" but "does an EXTERNAL,
typed-certificate, shared-ledger layer beat (a) internal absorption and (b) the cheapest
verifier of all — just executing checks." Your own corpus now answers (b) five consecutive
times: freq beats DescentNet (keystone R0/R1); whole-corpus freq beats the commons (R2); cheap
Jaccard beats H¹ on poison (R3); H⁰ entropy dominates the sheaf stack (R4/B′); and in THIS
witness the monolith ties the full coupled stack while B pays 4 solves for its certificates
and C seed 2 burns so much budget on cert machinery it fails to even ATTEMPT 5 of 24 tasks
(38.4k/40k tokens for 19 tasks — collapse mode 1, the verification tax, live in your own
ledger). The thesis is not dead as philosophy; as a product bet it is 0-for-5 against
`collections.Counter` and `assert`.

**Corrective:** Stop testing "does the layer beat trivial baselines" — you know the answer.
The only version of the bet with a live path is the one your own nemotron caveat named and the
witness then ignored (see F10): a LEARNED verification policy, trained on real failure data,
which is a research program indistinguishable from what the labs are doing — i.e., not a moat.

---

## F8 — HIGH — Constructed-favorable poison: the threat model is authored by the defense

The ledger's poison (P1 H⁰ conflicts, P2 H¹ cyclic frustration, `claims.py`) is exactly the
taxonomy the certificates are built to detect. This is circular: you seeded the environment
with the two shapes your detectors fire on, then asked whether the detectors help. Your OWN
prior result (B′, `AIOS_KEYSTONE_EXPERIMENT.md` Rung 4) established that REAL commons
contamination is H⁰-vocabulary-shift shaped and that a trivial entropy filter beats the sheaf
machinery on it. Even a positive witness here would certify only "our certs catch the poison
we designed them to catch." The pre-registration's "maximally-favorable regime by construction
→ a negative is devastating" is the right hedge stated backwards: a POSITIVE here would be
nearly uninformative; the negative is merely expected.

**Corrective:** Poison must be sourced adversarially and exogenously: a different model
(codex/gemini) authors deceptive claims with no knowledge of the cert taxonomy; or harvest
real wrong-claims from actual agent transcripts. If certificates only beat house-brand poison,
say so in every claim.

---

## F9 — MEDIUM — The metric is blind to the only thing certification actually sells

Verified-solves-at-fixed-budget prices a wrong submission at ZERO. Under it, abstention is
pure loss, so arm A (submit everything, 70.8% precision at seed 0) structurally dominates arm
B (86.7% precision) even when B is the better *agent to trust*. But calibrated trust — knowing
WHEN you're right — is the entire economic proposition of a certification layer. You built
the one metric under which certification's product is worthless, called the regime "maximally
favorable," and then measured that certification adds no value. Meanwhile "verified-solve-per-
FLOP" is claimed but token-budget is measured: the certs' local execution (sandboxed runs,
sheaf computations) is FREE under the token metric — a hidden subsidy TO the cert arms that
still didn't save them.

**Corrective:** Score utility U(λ) = solves − λ·(wrong submissions) and report the λ-curve.
If there exists a realistic λ region where B/C dominate A, THAT is the honest certification
claim ("certs buy precision at these exchange rates") — smaller than AGI-layer, but real and
sellable. If no λ region exists, the negative becomes truly devastating.

---

## F10 — MEDIUM — Primitive-by-primitive verdict: one decorative, one unused, one retired-then-resurrected, one untested-as-designed

- **APEX** — load-bearing potential, wrong harness. It is (per your own panel) conformal/
  selective prediction under a new name; its value is precision (F9), which the metric can't
  see. Strongest objection: as implemented it's a threshold on claim-conflict counts — the
  "answerability type calculus" branding vastly exceeds the ~300-line reality. Either grow the
  calculus or rename the object.
- **IRIS** — decoration, literally: computed, logged, never consulted (F5). Behavioral-
  equivalence-class selection is a fine idea (it IS self-consistency with execution
  signatures); nothing here distinguishes it from `_majority_pick`, and the data agrees
  (C−iris = C).
- **DescentNet** — you closed a 5-rung program on 2026-07-04 with "retire H¹ as the guard;
  the realistic threat is H⁰-shaped; ship the cheap filter" — and on 2026-07-05 DescentNet is
  back in the witness's hot path with an abstention hostage-wiring that manufactures its rent
  (F5). The shelf has a revolving door. Honor your own earned negative: DescentNet appears in
  new experiments only if the environment is shown to contain H¹-shaped structure it uniquely
  handles — which F8's constructed P2 poison does not demonstrate, it presupposes.
- **GoEN** — untested as designed. "Legibility theory of when rewiring helps" arrives in the
  witness as a static keep/drop filter over claims whose ablation changes zero bits. The
  keystone doc's own sharpest caveat (nemotron: "the architecture must LEARN to verify cheaper
  than it generates; static composition fails") names the exact axis the witness then failed
  to build: **you pre-registered a static hand-wired composition one paragraph after recording
  that static composition is expected to fail.** That is the single clearest internal
  contradiction in the program.

---

## F11 — MEDIUM — Architecture (M0): an unusually honest map with an inverted priority ordering and one self-contradictory invariant

Credit first: M0 is the best document in the tree — real status marks, named holes, both
witness branches drawn. The critique is not the map; it is what the map reveals:

1. **Priority inversion.** H4 ("no external user", zero C1 instances) is the only
   existentially informative hole — every other hole (H1 trust, H2 three-Akashics, H3
   witness, H5 compounding) is internal. Yet D0 (the witness) is the item "RUNNING NOW" and
   consuming the scarce Fable window, while D4→D6 wait. A system with zero users does not
   need a certified ledger; it needs a user.
2. **Population features without a population.** Akashic-as-commons, cross-agent transfer,
   trusted-writer admission — all presuppose N agents with independent knowledge. The reality
   is one founder + one operator pair on one box. R2 already showed the "commons" was
   mechanically a no-op in production (unsent auth header, 402 swallowed to `[]`) — nobody
   noticed for weeks BECAUSE there is no population that would have noticed. Build the
   multi-writer trust machinery when there is a second writer.
3. **DNA invariant 2 structurally caps north-star C3.** Draft-first with explicit per-object
   operator review means accepted memory grows at operator-attention speed. "Memory compounds
   measurably" (C3) and "no memory accepted without human review" cannot BOTH scale; at any
   real volume you must either automate acceptance (violating the invariant) or accept that
   compounding saturates at founder bandwidth. Name the resolution now (tiered acceptance:
   auto-accept low-risk observations, review only high-authority claims) rather than
   discovering it as a wall.
4. **The fossil is still the product.** 218 contracts + 5.8k-line ledger ship in every clone
   (H6), and the 2026-05-20 founder override that froze contract-minting is itself enforced
   by… more governance prose. C6 is the right criterion; nothing in the tree suggests the
   archival will out-prioritize the next theory doc without being someone's explicit job.

---

## F12 — MEDIUM — Operating dogma worth breaking

- **"Heterogeneous panel convergence" is weaker evidence than you treat it as.** Three models
  fed the SAME framing document converge substantially because the frame does the work; their
  training distributions also overlap heavily. The panel verdict (§2) happens to be right —
  but treat panel convergence as one prior-diversified opinion, not "independent frontier
  priors, convergent verdict." True independence requires independent FRAMING: give the raw
  artifacts to a model with a hostile prompt ("find why this is theater") and a promotional
  prompt, and see what survives both.
- **The scaffolding is unmeasured by its own standard.** The workspace's prompt apparatus
  (self-observation logs, absorption protocols, growth-engine directives, life ledgers,
  5-mode discipline) is enormous, and the tree contains an `absorption-probe` skill built
  precisely to test whether such apparatus changes behavior — apparently never decisively run
  on the apparatus itself. H5 ("compounding unmeasured") applies to the meta-layer too.
- **Verification asymmetry in-house:** the team applies pre-registration/kill-criteria rigor
  to its THEORIES but not to its TOOLING — score.py shipped with a self-test scaffold
  (`_synth_arm_rows`) yet the tier-normalization path that decides the program's headline
  verdict had no test against real runner output (F1 is exactly the bug such a test catches).
  A `drive_r1.sh` that pipes scorer stderr through `grep -iv libtinfo` and leaves a stray
  file named `python3` ("Bad file descriptor") in the experiment root is not the hygiene the
  claims resting on it require.

---

## F13 — THE BIGGEST THING — You have built a world-class negative-result factory and are mistaking the rigor of the process for the progress of the program

The pattern, stated plainly: **five consecutive keystone-grade tests, five results of
"trivial baseline dominates the mathematical machinery."** Frequency beats DescentNet.
Whole-corpus frequency beats the global commons. Jaccard beats H¹. Entropy beats the sheaf
stack. A monolith with self-consistency ties the full coupled certificate pipeline (F1). The
individual no-launder honesty at each rung is genuinely excellent — better than most academic
labs. But the PROGRAM-level Bayesian update is not being made: after N independent instances
of "the beautiful math loses to `Counter()`," the correct inference is not "find the next
regime where the math might win." It is **"the process generating these hypotheses is
miscalibrated."**

The generator is theory-first: select mathematically deep objects (sheaf cohomology, conformal
calculi, category theory, Hodge decompositions), then search for a regime where they matter.
That direction is backwards, and the reason it persists is structural: **with zero external
users (H4), there is no organic stream of real failures to pull primitives from, so
hypotheses are pulled from the aesthetics of mathematics instead.** Systems that win do it
need-first — a real workload fails in a specific way, and whatever math fits that failure gets
used, which is usually embarrassingly simple (your own shipped `aios guard` — a per-category
typicality filter — is the one artifact in this whole arc with validated numbers, and it
contains no cohomology).

Note also that the founder's 2026-05-20 override diagnosed precisely this ("stop optimizing
AIOS by creating more contracts about AIOS; turn toward creating value outside AIOS itself")
— and within six weeks the marquee program was again AIOS studying AIOS, now with category
theory and an "AGI certification" banner. The attractor state of this system is self-study,
and it re-forms after every correction. Even THIS extraction — spending the scarce Fable
window on design maps and critiques of the program — is the attractor operating: the binding
constraint on this team has never been design ideas or critique; it is external contact.

**The corrective, concretely:**
1. Fix F1's scorer, publish the witness negative straight (with F3/F4 power caveats), and
   CLOSE the certification program at the named negative exit it has now reached twice. Do
   not fund the "~100-task prevalence rung" — F3 shows the regime cannot carry the claim.
2. Retire the "AGI certification layer" claim from all product docs per your own C4-negative
   branch. Keep M1a (certs as optional guards/lints) — that branch was designed for exactly
   this outcome; use it.
3. Invert the dependency graph: D4 → D6 FIRST. Three external users completing real tasks on
   fresh installs, with failure logs harvested. This is the only item that can falsify or
   validate the organism, and it needs no new theory.
4. Re-admit mathematical primitives ONLY against observed, recurring, logged failures from
   (3) — each admission pre-registered against the cheapest conceivable baseline, which has
   won 5/5 so far and must be treated as the favorite.
5. Resolve the invariant-2/C3 contradiction (F11.3) before scaling memory, or the north star
   is capped at founder bandwidth by design.

---

## Appendix — What is genuinely good (so this audit can't be laundered into "everything was wrong")

- The no-launder culture at rung level is real and rare: R2's "the +0.375 is a weak-comparator
  artifact" self-catch, B1's "AUC 0.72 is float-pinv noise," and the B′ head-to-head are
  model examples of honest negative reporting.
- M0's two-products-one-repo recognition, the named holes H1–H7, and the pre-drawn negative
  branch (cert layer → optional guard tier) are exactly right — the program only has to
  ACTUALLY TAKE the branch it drew.
- `aios guard` is the template for the whole enterprise: negative → cheapest working filter →
  shipped with honest calibration numbers. More of that; less cohomology.
- The witness's instinct to bake the verification tax into the metric (equal token budgets,
  certificate calls charged) is methodologically ahead of most agent-eval work, even though
  F9's blind spot and F3's leaks undercut this instance.

*Verification note: every number in F1–F5 was recomputed from
`experiments/agi_witness/results/runs.jsonl` and the cited source lines
(`score.py:59-72`, `arms.py:199-200, 370-470`, `drive_r1.sh`, `data/pilot.json`) during this
audit. Nothing above is quoted from the team's own summaries.*
