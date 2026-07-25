# Obstruction Re-Earn Gate — Result (2026-07-25)

**Verdict: FAILED — STAYS PARKED.** The sheaf/GoEN revival proposed in
`docs/2026_07_evolution_sprint/` (AIOS_MATH_OPTIMIZATION_PORTING.md,
RESEARCH_ADVANCEMENT_PROPOSAL_2026.md, `aios_descent_goen_bridge.py`) does not
pass its re-earn gate on our real knowledge graph. The obstruction score as
written carries **no positive signal** about known contradictions globally, and
under type control it is **significantly anti-correlated** with them: real
contradictions sit at LOW obstruction, so the proposed "Evolutionary Scalpel"
(prune highest-friction edges) would preferentially cut the WRONG edges. This
replicates, in a sharper form, the prior negative that parked sheaf/H^1
("H^1 was effectively detecting a simpler signal"): here the simpler signal is
lexical/topical proximity plus endpoint-type composition.

## Context the sprint docs omit

This program already gated sheaf/H^1 NEGATIVE on real data (1438 real cases, 0
with the claimed structure; cycle-not-edge) and PARKED it; GoEN was on the kill
list for calibration collapse. The sprint docs present the revival as settled
architecture ("화려한 부활") with zero new evidence. It was therefore treated
as a NEW hypothesis and given the cheapest decisive test.

## Setup

- **Data (real, hand-sourced):** `docs/ontology/ledger/_merged.json` — 1233
  entities, 1872 relations, **72 `contradicts` edges** (from research ledgers),
  31 cross-domain entities. Schema per `experiments/ontology/merge.py`.
- **Probe:** `experiments/evolution_sprint/obstruction_probe.py`
  (self-contained, numpy + stdlib, deterministic seed 20260725, md5 hashing;
  runs in ~2 s).
- **Node features (PROXY, not semantics):** no embeddings exist for this
  ledger, so each node gets a deterministic signed-hash bag-of-tokens vector
  (name + type + domain tokens, dim 512, L2-normalized).
- **Obstruction score:** the bridge prototype's
  `friction = ||x_i − x_j||² · weight` (ledger has no edge weights → bridge
  default 1.0), plus a Laplacian variant (same friction on features smoothed by
  2 steps of symmetric-normalized diffusion over the real graph).
- **Statistics:** rank-based AUC (contradicts = positives), class
  means/medians, permutation test (10,000 label shuffles), global-ranking
  position of the contradicts edges.
- **Pre-stated stop rule:** AUC ≈ 0.5 / permutation p not significant ⇒ no
  signal ⇒ revival fails the gate and stays parked. EARNED requires AUC clearly
  > 0.5 with significant p AND survival of the type-controlled strata (a
  global-only signal that dies under type control = the "simpler signal"
  failure again). AUC significantly < 0.5 is also a failure of the proposal as
  written (the score anti-detects contradictions).

## Numbers

### A. Global edge test — 72 contradicts vs 1800 other edges (the tasked primary)

| score | AUC | perm p (two-sided) | pos mean/median | neg mean/median |
|---|---|---|---|---|
| raw friction (prototype) | **0.5152** | **0.660** (n.s.) | 1.572 / 1.620 | 1.530 / 1.617 |
| Laplacian-smoothed | 0.2525 | 0.0001 (inverted) | 0.072 / 0.056 | 0.478 / 0.124 |

Global obstruction ranking (raw friction, rank 1 = most obstructed of 1872
edges): contradicts mean rank **909.1**, median **927.5** (≈ the middle of the
pack); **0/72 in the top-72**; 12/72 in the top-10%. If the scalpel pruned the
top-72 "most obstructed" edges, it would cut **zero** real contradictions.

Confound present in A: contradicts endpoint types are 61 Claim–Claim,
10 Paper–Paper, 1 Concept–Paper, while most other edges are cross-type
(`authored` Person–Paper etc.) — so A's null is the honest primary readout, and
the strata below are the decisive control.

### B. Type-controlled strata (the discriminating test)

| stratum | n_pos / n_neg | AUC | perm p (two-sided) | pos mean | neg mean |
|---|---|---|---|---|---|
| contradicts CC vs ALL unlinked Claim–Claim pairs (raw) | 61 / 16,767 | **0.1967** | **0.0001** | 1.608 | 1.806 |
| same, Laplacian | 61 / 16,767 | 0.0002 | 0.0001 | 0.059 | 0.509 |
| contradicts PP vs 5000 unlinked Paper–Paper pairs (raw) | 10 / 5,000 | 0.1154 | 0.0001 | 1.352 | 1.723 |
| footnote: contradicts CC vs the only 8 non-contradicts CC edges | 61 / 8 | 0.672 | 0.113 (n.s.) | — | — |

Direction is **significantly INVERTED**: known contradictions score LOWER
obstruction than random same-type pairs. Ranking by friction and pruning high
scorers would systematically spare real contradictions and cut random pairs
first.

### C. Hebbian half — cross-domain entity pairs (proxy for "co-activated but unlinked") vs unlinked pairs

| comparison | n_pos / n_neg | AUC (distance² as score) | perm p |
|---|---|---|---|
| vs 5000 random unlinked pairs (raw) | 457 / 5,000 | 0.2588 | 0.0001 |
| vs same, Laplacian | 457 / 5,000 | 0.3333 | 0.0001 |
| vs 4570 TYPE-MATCHED unlinked pairs (raw) | 457 / 4,570 | 0.3184 | 0.0001 |

The proxy "co-activated" pairs ARE geometrically distinguishable (closer than
random, survives type matching) — but in the trivially expected direction and
partly by construction (see limitations). This is not evidence for the Hebbian
wiring mechanism; it says nothing about whether wiring such pairs helps.

### D. Diagnostic — the geometry is lexical overlap

Name-token Jaccard, contradicts CC vs unlinked CC pairs: pos mean **0.0644**
vs neg mean **0.0284**, AUC **0.738**, p = 0.0001. Contradicting claims share
~2.3× more name tokens than random claim pairs — they are about the SAME topic
("reward … sufficient … intelligence" vs "reward … NOT sufficient"). Any
similarity-based geometry therefore places real contradictions CLOSE, which
mechanically inverts the proposal's core premise "high distance + high weight =
contradiction".

## Verdict

**FAILED — STAYS PARKED** under the pre-stated stop rule:

- The tasked primary (global edge AUC) is null: 0.5152, p = 0.660.
- The type-controlled discriminating test is significantly inverted
  (AUC 0.197, p = 0.0001), i.e. the score anti-detects contradictions.
- The residual structure that IS detectable (D) is lexical/topical proximity —
  a simpler signal, exactly the prior parking rationale.
- 0/72 known contradictions appear in the top-72 obstruction ranking, so the
  concrete mechanism the revival proposes (prune the most-obstructed edges)
  would have cut zero real contradictions on our own data.

## Limitations (honest)

1. **The feature proxy is the biggest one.** Hashed bag-of-tokens is lexical,
   not semantic. It is responsible for the *magnitude* of the inversion — but
   likely not its *direction*: contradictions are same-topic-opposite-polarity
   pairs, and dense semantic embeddings are also well known to place same-topic
   statements close regardless of negation/stance. So real embeddings would
   plausibly move B from "strongly inverted" toward "inverted-or-null", not to
   the AUC > 0.5 the revival needs. This is an argument from known embedding
   behavior, not a measurement — a stronger test would need real embeddings
   (see below).
2. **B-lap's extreme value (AUC 0.0002) is partly mechanical.** Diffusion
   smoothing contracts distances across existing edges; contradicts pairs ARE
   edges while the control pairs are unlinked, so part of that inversion is
   "being an edge at all", not contradiction structure. The clean number is the
   unsmoothed B-CC-raw AUC = 0.197 — still decisively inverted.
3. **C is partly an artifact of feature construction.** Domain tokens are in
   the feature vector and cross-domain entities carry ≥2 of only 6 domain
   tags, so cross-domain pairs mechanically share domain tokens. The Hebbian
   result should be read as "the proxy is detectable", not "Hebbian wiring is
   validated". We also have no real co-activation logs; cross-domain membership
   is a weak stand-in.
4. **72 positives is small** (61 in the dominant stratum), though the
   permutation tests are exact for this size and the inversion is far from
   marginal.
5. **No true sheaf machinery was tested** — no restriction maps or orientation
   data exist in the ledger, so this probes the bridge's actual computable
   score (squared-distance friction), which is what the prototype ships. If a
   future proposal supplies genuine restriction maps, that would be a different
   hypothesis needing its own gate.

## What a stronger (still honest) test would need — IF anyone wants to re-open

Not a recommendation to proceed; the gate is failed. But to re-open, a
proposal would need, at minimum:

1. **Real semantic embeddings** for the 184 claims (local embedder is fine),
   re-running B-CC-raw. Prediction from D: still ≤ 0.5.
2. **A polarity/stance-aware score** (e.g. NLI contradiction probability),
   which is where contradiction detection actually lives — but then the signal
   is the NLI model, and the sheaf/friction machinery adds nothing over plain
   pairwise scoring; the revival would have to show a delta OVER that baseline.
3. **A held-out contradiction set** not used in any tuning, and a pre-registered
   AUC threshold.

## Reproduce

```
python3 experiments/evolution_sprint/obstruction_probe.py   # ~2 s, deterministic
```
