#!/usr/bin/env python3
"""OpenCrab Pack v1 exporter for the AIOS OntologyOS ledger.

Exports the merged knowledge ledger (docs/ontology/ledger/_merged.json) to a
portable, verifiable **Pack v1** ZIP:

    manifest.json
    graph/nodes.jsonl
    graph/edges.jsonl
    evidence/index.jsonl
    quality/report.json

This is the storage/recording brick from the Sovereign Coordination Stack
(docs/AIOS_SOVEREIGN_COORDINATION_STACK_2026-07-22.md):
- **Storage pillar** — adopt the OpenCrab Pack v1 container shape (peer interop),
  our `_merged.json` maps to it losslessly (`{id,type,name,attrs,source[],domain[]}`).
- **Recording pillar** — extend it with a per-record content hash + a Merkle root
  over all node/edge hashes, so a peer can verify the pack was not tampered
  (tamper-evidence without a central authority), and a JSON-LD `@context` so the
  same pack exports losslessly to RDF 1.2 as the W3C-stable federation lingua franca.

Federation (draft-first invariant): a peer importing this pack lands it as a DRAFT
subgraph, merged by node-hash identity; conflicts become contradiction edges, never
silent overwrites. (Import is a separate module; this file only EXPORTS.)

Stdlib-only (json, hashlib, zipfile) -- matches this package's zero-dependency
independence; loads and runs with no optional deps installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

SCHEMA = "opencrab-pack"
VERSION = "v1"
EXTENDS = "opencrab-pack-v1"  # base container shape we extend with hashes + JSON-LD

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = REPO_ROOT / "docs" / "ontology" / "ledger" / "_merged.json"
DEFAULT_OUT = REPO_ROOT / "docs" / "ontology" / "ledger" / "aios_ontology_pack_v1.zip"

# JSON-LD context: lets the property graph export losslessly to RDF 1.2 (W3C
# Candidate Rec) -- the stable cross-system federation vocabulary.
JSONLD_CONTEXT = {
    "@vocab": "https://aios.dev/ontology#",
    "id": "@id",
    "type": "@type",
    "name": "rdfs:label",
    "domain": "aios:domain",
    "evidence": "prov:wasDerivedFrom",
    "rel": "aios:relation",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "prov": "http://www.w3.org/ns/prov#",
    "aios": "https://aios.dev/ns#",
}

PACK_FILES = [
    "manifest.json",
    "graph/nodes.jsonl",
    "graph/edges.jsonl",
    "evidence/index.jsonl",
    "quality/report.json",
]


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canon(obj: Any) -> str:
    """Deterministic canonical JSON (sorted keys, no whitespace, unicode kept)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _content_hash(obj: dict) -> str:
    return "sha256:" + _sha256(_canon(obj))


def _evidence_id(source: str) -> str:
    return "ev:" + _sha256(source)[:16]


def merkle_root(hashes: list[str]) -> str:
    """Deterministic binary Merkle root over sorted leaf hashes. Empty -> hash of ''.
    Odd layers duplicate the last node (standard). Root ties the whole pack to one
    verifiable digest a peer can recompute from graph/nodes.jsonl + graph/edges.jsonl."""
    if not hashes:
        return "sha256:" + _sha256("")
    layer = sorted(hashes)
    while len(layer) > 1:
        nxt: list[str] = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i + 1] if i + 1 < len(layer) else layer[i]
            nxt.append("sha256:" + _sha256(a + b))
        layer = nxt
    return layer[0]


def build_pack(merged: dict) -> dict:
    """Transform a merged ledger dict into an in-memory Pack v1 (no I/O)."""
    evidence: dict[str, dict] = {}  # source_string -> evidence record (dedup)

    def ev_ids(sources: list[str] | None) -> list[str]:
        ids = []
        for s in sources or []:
            eid = _evidence_id(s)
            if s not in evidence:
                evidence[s] = {"evidence_id": eid, "source": s, "hash": "sha256:" + _sha256(s)}
            ids.append(eid)
        return ids

    nodes = []
    for e in merged.get("entities", []):
        core = {
            "id": e["id"],
            "type": e.get("type"),
            "name": e.get("name"),
            "attrs": e.get("attrs", {}),
            "domain": e.get("domain", []),
            "evidence": ev_ids(e.get("source")),
        }
        node = dict(core)
        node["hash"] = _content_hash(core)
        nodes.append(node)

    edges = []
    for r in merged.get("relations", []):
        core = {
            "src_id": r["src_id"],
            "rel": r["rel"],
            "dst_id": r["dst_id"],
            "domain": r.get("domain", []),
            "evidence": ev_ids(r.get("source")),
        }
        edge = dict(core)
        edge["hash"] = _content_hash(core)
        edges.append(edge)

    ev_index = sorted(evidence.values(), key=lambda x: x["evidence_id"])
    root = merkle_root([n["hash"] for n in nodes] + [e["hash"] for e in edges])

    stats = merged.get("stats", {})
    quality = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "total_evidence": len(ev_index),
        "contradicts_count": stats.get("contradicts_count"),
        "cross_domain_entity_count": stats.get("cross_domain_entity_count"),
        "provenance_gap_entity_count": stats.get("provenance_gap_entity_count"),
        "provenance_gap_relation_count": stats.get("provenance_gap_relation_count"),
        "dropped_dangler_count": stats.get("dropped_dangler_count"),
        "entities_by_type": stats.get("entities_by_type"),
        "merkle_root": root,
    }
    manifest = {
        "schema": SCHEMA,
        "version": VERSION,
        "extends": EXTENDS,
        "generated_by": "aios/experiments/ontology/pack_export.py",
        "counts": {"nodes": len(nodes), "edges": len(edges), "evidence": len(ev_index)},
        "merkle_root": root,
        "jsonld_context": JSONLD_CONTEXT,
        "files": PACK_FILES,
    }
    return {"manifest": manifest, "nodes": nodes, "edges": edges, "evidence": ev_index, "quality": quality}


def _jsonl(rows: list[dict]) -> str:
    return "".join(_canon(r) + "\n" for r in rows)


def write_pack(pack: dict, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(pack["manifest"], indent=2, ensure_ascii=False))
        z.writestr("graph/nodes.jsonl", _jsonl(pack["nodes"]))
        z.writestr("graph/edges.jsonl", _jsonl(pack["edges"]))
        z.writestr("evidence/index.jsonl", _jsonl(pack["evidence"]))
        z.writestr("quality/report.json", json.dumps(pack["quality"], indent=2, ensure_ascii=False))
    return out_path


def read_pack(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        manifest = json.loads(z.read("manifest.json"))
        nodes = [json.loads(l) for l in z.read("graph/nodes.jsonl").decode().splitlines() if l.strip()]
        edges = [json.loads(l) for l in z.read("graph/edges.jsonl").decode().splitlines() if l.strip()]
        evidence = [json.loads(l) for l in z.read("evidence/index.jsonl").decode().splitlines() if l.strip()]
        quality = json.loads(z.read("quality/report.json"))
    return {"manifest": manifest, "nodes": nodes, "edges": edges, "evidence": evidence, "quality": quality}


def verify_pack(pack: dict) -> tuple[bool, str]:
    """Recompute the Merkle root from nodes+edges and check it matches the manifest.
    This is the cross-party tamper-evidence check: a peer runs this to trust the pack."""
    recomputed = merkle_root([n["hash"] for n in pack["nodes"]] + [e["hash"] for e in pack["edges"]])
    claimed = pack["manifest"].get("merkle_root")
    if recomputed != claimed:
        return False, f"merkle mismatch: recomputed {recomputed} != manifest {claimed}"
    # also re-verify each node/edge content hash
    for n in pack["nodes"]:
        core = {k: n[k] for k in ("id", "type", "name", "attrs", "domain", "evidence")}
        if _content_hash(core) != n["hash"]:
            return False, f"node hash mismatch: {n['id']}"
    for e in pack["edges"]:
        core = {k: e[k] for k in ("src_id", "rel", "dst_id", "domain", "evidence")}
        if _content_hash(core) != e["hash"]:
            return False, f"edge hash mismatch: {e['src_id']}-{e['rel']}->{e['dst_id']}"
    return True, "ok"


def export(in_path: Path = DEFAULT_IN, out_path: Path = DEFAULT_OUT) -> dict:
    merged = json.loads(in_path.read_text(encoding="utf-8"))
    pack = build_pack(merged)
    write_pack(pack, out_path)
    ok, msg = verify_pack(pack)
    return {"out": str(out_path), "counts": pack["manifest"]["counts"],
            "merkle_root": pack["manifest"]["merkle_root"], "self_verify": ok, "verify_msg": msg}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export the AIOS ontology ledger to an OpenCrab Pack v1 ZIP.")
    ap.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", dest="out_path", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--verify", type=Path, default=None, help="verify an existing pack ZIP and exit")
    args = ap.parse_args(argv)
    if args.verify:
        ok, msg = verify_pack(read_pack(args.verify))
        print(json.dumps({"verify": str(args.verify), "ok": ok, "msg": msg}, indent=2))
        return 0 if ok else 1
    result = export(args.in_path, args.out_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["self_verify"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
