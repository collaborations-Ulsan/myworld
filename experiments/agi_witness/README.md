# AGI Certification-Layer Witness — PRE-REGISTRATION

**Frozen before any eval run.** Design: Fable 5 (heterogeneous frontier designer), grounded +
verified by claude@myworld. Thesis + panel verdict: `../../docs/AIOS_AGI_CERTIFICATION_KEYSTONE.md`.
Prior earned-negative (single-agent static regime): `../../docs/AIOS_KEYSTONE_EXPERIMENT.md`.

## The one question
Does **cross-component coupling** (one certificate constraining another's search space) produce
emergent value beyond independent certificates — at a **population + verification-bound** regime?
If not, the AGI-certification-layer thesis is a **taxonomy**, not a unified object.

## Regime (why it is the right one)
Spec-in-the-ledger program repair: ~100 MBPP problems with their spec REMOVED; the behavioral
spec lives ONLY in a shared, population-seeded ledger of typed claims — some true, some poisoned
(H⁰ conflicts + H¹ cyclic frustration), some insufficient (underdetermined). Generation is
trivial *given a trusted spec* (pilot-enforced: qwen2.5-coder:7b ≥60% pass@8 with full spec), so
ALL difficulty is verification + coordination + knowing-when-to-abstain. This is the certificates'
maximally-favorable regime by construction → a negative here is devastating (exhaustive-
impossibility exit), a positive is an honest existence-witness with prevalence still owed (rule 4).

## Arms (identical solver, ledger scope, k=6 samples/task, abstention right, TOTAL TOKEN BUDGET)
- **A** monolith: CoT + k-sample self-consistency on raw claims (no strawman — monoliths absorb
  internal verification; collapse-mode-2 must be given its best shot).
- **B** independent certificates: all 4 computed, each sees ONLY (task, claims, candidates); union
  of independent filters; **no cert output feeds another**.
- **C** coupled: DescentNet repair → GoEN action space; Descent → APEX abstain; APEX gaps steer
  IRIS; Akashic proof prunes later APEX (population coupling). Full wiring in `../../docs/AIOS_AGI_CERTIFICATION_KEYSTONE.md` + design.

## Metric
**Primary:** verified solves (pass hidden MBPP tests, executed locally — no LLM judge) at a fixed
total token budget `B_tok` per arm (all prompt+completion tokens, incl. certificate LLM calls).
Equal-budget solve count ≡ verified-solve-per-FLOP with fixed denominator → the verification tax
is structurally baked in; the layer CAN lose. **Secondary:** raw solve-rate, submission precision,
P0-clean-subset solve-rate (pure tax isolation), wall-seconds, tier-2 `C−A` delta (absorption probe).
`B_tok` is set in pilot (so A completes the eval stream) and committed HERE before eval: `B_tok = TBD-pilot`.

## KILL CRITERION (pre-registered — declares the composition a TAXONOMY / earned negative)
On R1 (tier-1 `openai/gpt-oss-120b`, 3 seeds, equal budget, ~100 eval tasks), declare negative if:
- **K1:** median `C_solves ≤ median(max(A_solves, B_solves)) + ε`, ε = max(3 solves, 1.64×pooled bootstrap SE); **OR**
- **K2:** ≤2 of the 4 single-certificate ablations (R2–R5) degrade C by >2×bootstrap SE (composition is decoration).

Witness FIRES iff `median C > median max(A,B) + ε` (R1) **AND all of R2–R5 degrade C by >2×SE**.
R6 (−write-back) reported separately as the *population*-coupling result. Anything partial is
reported straight as partial — no laundering either direction (rule 5).

Secondary pre-registered probe: if `C−A` shrinks materially tier-1→tier-2 (`deepseek-ai/deepseek-v4-pro`),
that is evidence FOR monolith absorption, reported as such.

## Ablation matrix
| run | config | seeds | proves |
|---|---|---|---|
| R1 | A,B,C — tier-1 gpt-oss-120b | 3 | A-vs-B (certs at all), **B-vs-C (coupling = keystone)** |
| R2 | C −APEX (attempt all) | 2 | answerability rent |
| R3 | C −IRIS (self-consistency pick) | 2 | identifiability rent |
| R4 | C −DescentNet (no repair) | 2 | contradiction-cert rent |
| R5 | C −GoEN (fixed context) | 2 | learned-routing rent |
| R6 | C −write-back | 2 | population coupling specifically |
| R7 | A,B,C — tier-2 deepseek-v4-pro | 1 | monolith-absorption probe |

## Verified box resources
See `RESOURCES.md`. Solver tier-1 `openai/gpt-oss-120b` (~1s, free) and tier-2
`deepseek-ai/deepseek-v4-pro` CONFIRMED answering (full org-prefixed ids). Seeders/pilot on local
`qwen2.5-coder:7b`. MBPP sanitized fetch CONFIRMED (255KB from google-research). CPU only.
