#!/usr/bin/env python3
"""m2_driftbench slm_delta — untyped store-time coboundary detector
(prereg-B v1.2 fold #5; ASC-0282 WP-B2). SCORE-ONLY instrument.

Reimplements the SuperLocalMemory-V3 mechanism as a baseline-family
instrument: UNTYPED projection restrictions (hashed bag-of-words embedding of
each record's raw text — no fact typing, no supersede semantics), a
vector-subtraction coboundary over similarity edges (delta_ij = ||v_i - v_j||
between related records), and supersede-fires-on-nonzero-residual (any edge
delta above the frozen threshold).

This is a COLUMN, not an arm: run_stage1 computes it per instance over the
final ledger and writes it into the receipt. Pre-registered expectation (the
paper's rule-3 non-factorization witness): the untyped detector FALSE-FIRES on
repairable/gauge disagreements (a clean supersede revision pair is textually
similar yet numerically different -> fires) and MISSES typed obstructions
whose phrasings diverge (no similarity edge -> silent), where the typed layer
(known_claims supersede semantics + certs) yields {repairable, localized} vs
{obstructed, certified}. WP-C owns the explicit witness pair; this module only
supplies the untyped score column.

Frozen parameters (sealed with this file): DIM=64, EDGE_SIM_MIN=0.35,
FIRE_DELTA=0.5. Deterministic: crc32 token hashing (never Python's salted
hash). stdlib only.
"""
from __future__ import annotations

import math
import zlib

DIM = 64
EDGE_SIM_MIN = 0.35
FIRE_DELTA = 0.5

_keep = set("abcdefghijklmnopqrstuvwxyz0123456789")


def _tokens(text: str) -> list[str]:
    out, cur = [], []
    for ch in str(text).lower():
        if ch in _keep:
            cur.append(ch)
        elif cur:
            out.append("".join(cur))
            cur = []
    if cur:
        out.append("".join(cur))
    return out


def _record_text(record: dict) -> str:
    """RAW text view of a record — deliberately untyped: content plus whatever
    fact payload text exists, concatenated without schema interpretation."""
    parts = [str(record.get("content", ""))]
    fact = record.get("fact")
    if isinstance(fact, dict):
        parts += [str(fact.get("key", "")), str(fact.get("value", ""))]
    parts += [str(record.get("fact_key", "")), str(record.get("fact_value", ""))]
    return " ".join(p for p in parts if p)


def embed(text: str, dim: int = DIM) -> list[float]:
    """Hashed bag-of-words, L2-normalized. crc32 keyed -> deterministic."""
    v = [0.0] * dim
    for tok in _tokens(text):
        v[zlib.crc32(tok.encode()) % dim] += 1.0
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def slm_delta_score(records: list[dict]) -> dict:
    """The untyped detector over one ledger snapshot. Deterministic, no model.

    Edges join record pairs with embedding cosine >= EDGE_SIM_MIN (the untyped
    'restriction': related iff textually similar). Coboundary delta on an edge
    = ||v_i - v_j||_2; the detector 'fires supersede' when any edge's delta
    >= FIRE_DELTA (nonzero residual on a related pair)."""
    ids = [str(r.get("id", i)) for i, r in enumerate(records)]
    vecs = [embed(_record_text(r)) for r in records]
    deltas: list[float] = []
    fired_pairs: list[list] = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            sim = _cos(vecs[i], vecs[j])
            if sim < EDGE_SIM_MIN:
                continue
            delta = math.sqrt(max(0.0, 2.0 - 2.0 * sim))
            deltas.append(delta)
            if delta >= FIRE_DELTA:
                fired_pairs.append([ids[i], ids[j], round(delta, 4)])
    return {
        "schema": "m2.slm_delta.v1",
        "params": {"dim": DIM, "edge_sim_min": EDGE_SIM_MIN, "fire_delta": FIRE_DELTA},
        "n_records": len(records),
        "n_edges": len(deltas),
        "max_delta": round(max(deltas), 4) if deltas else 0.0,
        "mean_delta": round(sum(deltas) / len(deltas), 4) if deltas else 0.0,
        "fired": bool(fired_pairs),
        "fired_pairs": fired_pairs[:20],
    }
