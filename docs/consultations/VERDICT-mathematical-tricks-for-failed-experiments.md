# Operator verdict — "Mathematical tricks to resuscitate failed experiments" (agy artifact)

**Source**: `agy_workspace/MATHEMATICAL_TRICKS_FOR_FAILED_EXPERIMENTS.md` (2026-07-25, agy substrate).
**Reviewed by**: claude@myworld, 2026-07-26. Same discipline as every consultation: the substrate proposes,
the operator decides, nothing is auto-adopted.

## Verdict in one line

**The mathematics is real and worth keeping. The FRAMING is the danger, and applied to GoEN/DescentNet
*today* these tricks would resuscitate a corpse whose cause of death they do not treat.** Adopted — but
redirected to where a real signal exists.

## The math itself: legitimate (not p-hacking)

To be fair and precise: nothing here is statistical manipulation. Every technique named is standard,
published, and sound in its own domain — Gumbel-Softmax (differentiable discrete sampling),
Sinkhorn-Knopp entropy regularization (prevents degenerate all-or-nothing transport), implicit
differentiation / DEQ (O(1)-memory backprop through a fixed point), contrastive invariance training.
The document is competent. **The problem is the target, not the tools.**

## Why they cannot rescue GoEN/DescentNet as claimed

The document's premise is that GoEN collapsed to a constant base-rate because *discrete decisions block
gradients* — so make the decision differentiable (Gumbel) and forbid degenerate solutions (Sinkhorn).

**That diagnosis does not match the measurement we made yesterday** (`97b6dc8`, and I reproduced the
numbers myself on the real 1233-node/1872-edge ledger with its 72 hand-sourced contradiction edges):
- global obstruction AUC **0.5152, p=0.66** — null;
- type-controlled Claim–Claim stratum AUC **0.1967, p=0.0001** — **significantly INVERTED**;
- **0 of 72** real contradictions land in the top-72 most-obstructed edges (mean rank 909/1872);
- mechanism: contradicting claims share **2.3× more name tokens** than random pairs (AUC 0.738,
  p=0.0001) — real contradictions are *same-topic, opposite-polarity*, so **any** similarity geometry
  places them CLOSE. The premise "high distance = contradiction" is structurally backwards.

**The failure is at the SIGNAL layer, not the OPTIMIZATION layer.**
- Gumbel-Softmax restores gradient flow through a discrete cut/keep decision. If the feature that feeds
  that decision anti-correlates with the target, a smoother gradient just lets the model **learn the
  wrong thing more efficiently**.
- Sinkhorn prevents collapse to "cut everything / keep everything". A *diverse* set of wrong cuts is not
  better than an honest constant — it is a constant with more confidence and worse auditability.
- DEQ solves an OOM that we **do not have**: 1233 nodes is small. Solving a scaling problem for a
  computation whose output carries no signal is pure motion.
- Collapse-to-base-rate is, in fact, **what a correctly-behaving learner does when the features are
  uninformative about the target.** Treating that symptom as a gradient plumbing bug is exactly the
  inversion this program's discipline exists to catch.

## The framing risk — named, because it is the real hazard

*"실패한 실험을 되살린다 / 기어코 작동하게 만든다"* optimizes for a **conclusion** rather than for the
truth. This program's standing rules are the opposite: a negative is a pivot, not a thing to be defeated;
and when a program keeps failing, suspect the goal/metric/baseline before the idea. Sheaf/H¹ has now
failed **three independent data gates** (H¹ gate on 1438 memories → agent-induced H¹ → yesterday's
obstruction re-earn). A fourth attempt with fancier optimizers, absent a new signal, is not resilience —
it is sunk cost with better notation.

## What IS adopted, and where (the redirect)

These tools are correct for a problem we **actually** have. The adversarial gap audit named the top
missing organ: **credit assignment + pruning** — the registry and experience graph only ever grow, so
retrieval pollution is inevitable. Pruning is a **discrete keep/drop decision** that will hit exactly the
degeneracy the document describes (prune everything / prune nothing), and there the outcome signal is
**real and external** (does pruning move `P_auto`?), not an inverted proxy.

1. **Gumbel-Softmax → differentiable pruning of skills/memories**, once Phase 5 gives us an outcome
   metric to attribute against. ADOPTED as the method of record for that organ when we build it.
2. **Entropy/Sinkhorn regularization → the anti-degeneracy constraint** on that same pruner (keeps the
   retained set diverse instead of collapsing). ADOPTED with it.
3. **Contrastive invariance (the gauge-shift idea) → the skill gate's known weakness** ("syntactic
   containment ≠ semantic competence"): require a skill to survive transformations of its inputs, not
   just its author's own test. This is the same direction as the property-fuzzing fix already adopted
   from the earlier agy DREAM consultation — the two compose. ADOPTED as a hardening path.
4. **DEQ / implicit differentiation** — PARKED. It solves a scale we do not have; revisit only if a
   graph computation with *demonstrated signal* becomes the bottleneck.

## Condition for ever re-opening sheaf/GoEN (unchanged, restated)

Not "better optimizers." A **different signal**: a stance/NLI-grade relation between claims, and then a
demonstration that the sheaf machinery adds a measurable delta **over that NLI baseline**, on a held-out
contradiction set, with a pre-registered threshold. Until that exists, the parking stands — and these
tricks are stored in the toolbox, pointed at pruning.
