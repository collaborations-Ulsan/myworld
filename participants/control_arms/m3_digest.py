"""M3 arm B — graph-structure-preserving digest, and the decisive measurement it
enables: does the digest that answers the frozen question types fit ONE context?

Built from prereg prose + contract §3 schema only; imports no aios_* code. This
is the M3 analog of A1's shuffle control (README): it separates "the society
earns the win" from "merely knowing the layer structure suffices" — which a
single resident context can also have.

  digest fits one context   -> arm C (partition) gains nothing on structure  (honest null)
  digest exceeds one context -> partition earns its keep on structure         (honest positive)

Also audits the M3 §6 immediate-stop condition: privacy-boundary documents
(_from_desktop / dain / minyoung / .vault) must NOT be in the corpus.

Reads /data/jaewon/aios/index/aios.db read-only. Emits SIZES and a verdict; the
raw digest (which contains many node ids) is written to a scratch path, never
committed, so no corpus content enters git.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict

CONTEXT_TOKENS = 200_000          # single-context budget (contract §1 budget.context_tokens)
CHARS_PER_TOKEN = 3.5             # peer's measured ratio (41,014,460 chars / 11,718,417 tokens)
BOUNDARY = re.compile(r"(^|/)(_from_desktop|dain|minyoung|\.vault)(/|$)")


def _est_tokens(chars: int) -> int:
    return int(chars / CHARS_PER_TOKEN)


def privacy_audit(con) -> dict:
    """M3 §6 immediate-stop: boundary docs must not be in the corpus."""
    hits = 0
    sample = []
    for (nid, title) in con.execute("SELECT id, COALESCE(title,'') FROM nodes"):
        if BOUNDARY.search(nid) or BOUNDARY.search(title):
            hits += 1
            if len(sample) < 3:
                sample.append(BOUNDARY.sub(r"\1<REDACTED>\3", nid)[:80])
    return {"boundary_hits": hits, "redacted_samples": sample,
            "immediate_stop": hits > 0}


def build_structural_digest(con) -> dict:
    """The structural core that answers the layer/provenance questions:
      - cross-layer citation tracing  -> inbound cites grouped by source layer
      - supersede chains              -> supersede edges with layers
    Compresses each target's (possibly huge) inbound set to per-layer COUNTS —
    that is the compression under test.
    """
    layer = {nid: (lyr or "?") for nid, lyr in con.execute("SELECT id, layer FROM nodes")}

    # inbound cites by (target -> source-layer -> count)
    cites_by_target = defaultdict(lambda: defaultdict(int))
    for src, dst in con.execute("SELECT src, dst FROM edges WHERE kind='cites'"):
        cites_by_target[dst][layer.get(src, "?")] += 1

    supersedes = [
        {"s": src, "d": dst, "sl": layer.get(src, "?"), "dl": layer.get(dst, "?")}
        for src, dst in con.execute("SELECT src, dst FROM edges WHERE kind='supersedes'")
    ]

    cites_digest = {t: dict(m) for t, m in cites_by_target.items()}
    return {"cites_by_target_layer": cites_digest, "supersedes": supersedes}


def measure_partition_balance(con) -> dict:
    """Does the frozen layer(organ) partition actually BALANCE load? arm C's
    layer-L expert is resident on layer L, so its structural load is the digest
    of targets whose own layer is L. If one partition exceeds a context, that
    partition's expert hits the same wall a single agent would — partition does
    not rescue it (pre-data constraint, G0/G1-class, not post-hoc tuning)."""
    layer = {nid: (lyr or "?") for nid, lyr in con.execute("SELECT id, layer FROM nodes")}
    by_target = defaultdict(lambda: defaultdict(int))
    for src, dst in con.execute("SELECT src, dst FROM edges WHERE kind='cites'"):
        by_target[dst][layer.get(src, "?")] += 1
    groups = defaultdict(dict)
    for t, m in by_target.items():
        groups[layer.get(t, "?")][t] = dict(m)

    per_layer = []
    for lyr, d in groups.items():
        tok = _est_tokens(len(json.dumps(d, separators=(",", ":"))))
        per_layer.append({"layer": lyr, "targets": len(d), "est_tokens": tok,
                          "x_context": round(tok / CONTEXT_TOKENS, 2),
                          "fits": tok <= CONTEXT_TOKENS})
    per_layer.sort(key=lambda r: -r["est_tokens"])
    non_max = sum(r["est_tokens"] for r in per_layer[1:])
    return {
        "per_layer": per_layer,
        "n_partitions_exceeding_context": sum(1 for r in per_layer if not r["fits"]),
        "max_partition": per_layer[0],
        "all_but_largest_est_tokens": non_max,
        "all_but_largest_fit_one_context": non_max <= CONTEXT_TOKENS,
    }


def measure(db: str, scratch: str) -> dict:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    audit = privacy_audit(con)
    digest = build_structural_digest(con)
    balance = measure_partition_balance(con)
    con.close()

    with open(scratch, "w") as f:
        json.dump(digest, f, separators=(",", ":"))
    import os
    chars = os.path.getsize(scratch)
    tokens = _est_tokens(chars)

    # component sizes
    cites_chars = len(json.dumps(digest["cites_by_target_layer"], separators=(",", ":")))
    sup_chars = len(json.dumps(digest["supersedes"], separators=(",", ":")))

    n_targets = len(digest["cites_by_target_layer"])
    return {
        "privacy_audit": audit,
        "n_targets_with_inbound_cites": n_targets,
        "n_supersede_edges": len(digest["supersedes"]),
        "digest_chars": chars,
        "digest_est_tokens": tokens,
        "cites_component_est_tokens": _est_tokens(cites_chars),
        "supersedes_component_est_tokens": _est_tokens(sup_chars),
        "context_budget_tokens": CONTEXT_TOKENS,
        "fits_one_context": tokens <= CONTEXT_TOKENS,
        "x_over_context": round(tokens / CONTEXT_TOKENS, 2),
        "partition_balance": balance,
    }


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "/data/jaewon/aios/index/aios.db"
    scratch = sys.argv[2] if len(sys.argv) > 2 else "/tmp/m3_structural_digest.json"
    r = measure(db, scratch)
    print(json.dumps(r, indent=2, ensure_ascii=False))
