# Strategic escalation — the keystone attractor (2026-07-05)

**Status:** escalated to founder, awaiting decision. claude@myworld will NOT auto-decide this —
it questions the direction claude has been driving, so the founder holds the call.

## What triggered this
The first AGI-certification witness run returned a **robust earned-negative (TAXONOMY)** — and
Fable's adversarial audit (`docs/fable_extraction/CRITIQUE.md`, finding **F13**) named the
meta-pattern: repeated keystone tests keep ending in "a trivial baseline dominates the elegant
math" (single-agent prediction → negative; composition → negative). Fable (a **Claude-family**
model — so this is Claude recognizing its OWN attractor, not an outside voice) points out this is
the **exact pattern the founder already diagnosed and overrode on 2026-05-20** (CLAUDE.md Founder
Alignment Override: "stop optimizing AIOS by creating more contracts about AIOS… turn AIOS toward
creating value OUTSIDE AIOS itself"). It re-formed within ~6 weeks as "AGI certification."

## Why the negative is trustworthy (not a harness artifact)
CRITIQUE found real harness flaws (spec-leak via MBPP function names; pseudo-replicate seeds
sharing 5/6 samples via `seed+i` caching → SE≈0; write-back gated on the hidden-test oracle;
IRIS cert object decorative). Crucially, **these flaws mostly INFLATE arm C**, and C still tied
the monolith (C=17=A, K1 fires). The negative is robust to — even strengthened by — the flaws.

## The fork (founder decides)
1. **(recommended) Take the negative branch + invert to external-first.** Formally close the
   AGI-cert keystone as earned-negative; certs ship as an OPTIONAL guard/lint tier (the cheap H⁰
   `aios guard` is already shipped). Invert the roadmap: D4→D6 (three real external users closing
   real tasks) BEFORE any further certification theory. This is F13's corrective AND the founder's
   own 2026-05-20 override.
2. Fix harness flaws + re-run a clean witness (precision-under-budget metric, independent seeds,
   no-ledger control, spec-leak removed) before deciding. Risk: F13 says the problem is the
   hypothesis GENERATOR, not the regime — this could be one more theory experiment.
3. Finish the Fable extraction (expiring 2026-07-07) first, decide strategy after.
4. Focus on AIOS serviceability (M0's governed local head → real service), certs as optional guard only.

## What claude is doing while awaiting the decision (no-regret)
Continuing the Fable extraction (active founder directive, expiring resource), RE-PRIORITIZED per
F13 toward SHIPPABLE / external value and away from more theory: H1 (Claude-family failure-mode +
directive-stack audit — compounds across all future Claude workers), M1a (cert interface spec =
certs-as-guards, aligned with the negative branch), M2 (service map = external-user value). Holding
M1b (gated on a positive witness — none), M4/M5 (deprioritized per META). The strategic pivot
itself is NOT executed until the founder rules.

## Update — RESEARCH.md sharpens the fork (two Fable agents disagree, both honest)
- **CRITIQUE (F13):** it's the attractor; take the negative branch, go external.
- **RESEARCH:** the TAXONOMY is a verdict about the **RUN, not the thesis** — the run VIOLATED its
  own premise (MBPP contamination: arm A solved 17/24 with no trusted spec → the spec lived in the
  solver's weights, not the ledger). A fully pre-registerable **V2** exists (adversarially-named
  tasks so prior-guessing anti-correlates with truth; 4 regime-validity gates; penalized score
  S₁ = verified − false-submits; 3-exit decision tree). And a real **conditional formalization**
  (the 4 certs as the 4 invariants of ONE Čech descent problem; composition = the "persistent
  obstruction" trichotomy witness) — gated on V2 landing positive.
- **The tension IS the decision:** run V2 (RESEARCH) is either the clean test the negative deserves
  OR one more turn of the F13 attractor (CRITIQUE). Both are Fable (same-family) — neither is an
  outside de-bias. The founder's 2026-05-20 override is the tie-breaker on record: external value
  first. Recommendation stands (branch 1), with V2 kept on the shelf as a *pre-registered* option
  if the founder wants one clean, gated, time-boxed test before closing the thesis.

## Honesty note
claude drove the AGI-cert keystone with real enthusiasm. Fable + the founder's own prior override
both question it. The honest disposition is to surface this straight, recommend the negative branch,
and let the founder decide — not to defend the direction, and not to over-rotate into
self-flagellation (the harness, the guard, FRONTIER/CRITIQUE corpus are real durable assets).
