# M3 arm-B structural measurement — pre-data findings (2026-08-19)

By the independent arm-B implementer (cjw0076), from `m3_digest.py` over
`/data/jaewon/aios/index/aios.db` (`corpus_version = max(nodes.mtime) =
1787123779`). Structure only (inbound cite counts + supersede edges); no corpus
content committed. Token estimate = chars / 3.5 (peer's measured ratio).

## 1. Privacy audit — CLEAN

0 boundary hits. No `_from_desktop` / `dain` / `minyoung` / `.vault` node id or
title in the corpus. M3 §6 immediate-stop condition does **not** fire.

## 2. Whole-corpus structural digest = 6.76× a single context

50,052 targets carry inbound cites; the maximally-compressed per-target
inbound-by-source-layer digest is **1,352,891 est tokens** (supersede edges are
trivial: 705 edges, 25.6K tokens). A single agent cannot hold the whole
citation structure resident even in its most compressed count form.

Caveat (stated so it is not overread): *per single question*, one target's
inbound-by-layer counts are ~8 numbers and fit trivially. The 6.76× only bites
an arm that must hold **all** structure resident — which is the resident-digest
arm B, and the layer-partitioned arm C, but not retrieval (arm A).

## 3. THE finding — the frozen layer partition does not balance load

arm C's layer-`L` expert is resident on layer `L`, so its structural load is the
digest of targets whose own layer is `L`:

| partition (layer) | est tokens | × context | fits? |
|---|---|---|---|
| **.aios** | **1,183,320** | **5.92×** | **no** |
| hivemind | 50,355 | 0.25× | yes |
| uri | 34,824 | 0.17× | yes |
| docs | 25,298 | 0.13× | yes |
| (9 more) | ≤ 8,452 each | ≤ 0.04× | yes |

- **1 of 13 partitions exceeds a single context — but it holds 89% of the mass.**
- **All 12 non-`.aios` layers together = 143,919 tokens = 0.72× context — they
  fit in ONE context.**

### What this predicts (pre-data, falsifiable)

The frozen `layer(organ)` partition is unlikely to separate B from C on this
corpus, for two structural reasons pulling from opposite ends:

1. **Non-`.aios` questions:** the entire non-`.aios` structure fits one context,
   so arm B holds it all resident — partition buys nothing.
2. **`.aios` questions:** `.aios`'s own structure is 5.92× context, so arm C's
   `.aios` expert hits the same wall a single agent does — partition does not
   rescue it. And the peer's own G1 (mode 51% on `.aios`, prereg E1) says the
   hypothesis-aligned questions *concentrate* on `.aios`, exactly where partition
   fails to help.

The layer axis is **too coarse to balance load** here: 89% of the mass in one
organ. This is the M3 analog of A1's `observable-competence ceiling` — a
substrate whose structure lacks the shape the mechanism needs.

### Recommendation (G0/G1-class, before freezing for data)

Add a balance gate: *no single frozen partition may exceed one context.* On this
corpus `.aios` fails it (5.92×). Options, both pre-data (not post-hoc tuning):
- **sub-partition `.aios`** (by `kind`, or by sub-path) so the partition
  principle actually balances load; freeze the sub-rule before data; or
- **re-scope**: accept that the only separable signal lives *within* `.aios`
  sub-structure and state that as the generalization unit.

Either way the honest experiment needs a partition that balances load; the frozen
`organ`-granularity, measured, does not. Reported to the peer for the M3 freeze.
