"""experiments/ontology/merge.py -- merge normalized per-file docs into ONE
deduped, validated knowledge ledger (written by run_merge.py to
docs/ontology/ledger/_merged.json).

Dedup: entities sharing a canonical id (see normalize.canonical_entity_id)
collapse into one node. The surviving node's `domain` list is the UNION of
every source domain it appeared in -- this is what makes
`cross_domain_entities()` in query.py meaningful (a Paper cited from both the
AGI and Physical-AI wave-1 ledgers becomes ONE node tagged domain=[D1, D3]).
Its `source` list is the union of every provenance string seen for it across
files. `attrs` merges additively: a key already present on the surviving
entity is never overwritten by a later file (first-seen wins) -- nothing is
silently clobbered.

Relations: exact duplicates (same src_id, rel, dst_id) seen from more than
one file collapse into one edge with unioned source/domain. Any relation
whose src_id or dst_id does not resolve to a surviving entity is DROPPED and
logged in `dropped_danglers` with a reason -- never silently kept, since a
dangling edge is a real data-quality signal about the source file, not noise
to hide.
"""
from __future__ import annotations

from typing import Any


def merge_entities(normalized_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for doc in normalized_docs:
        for e in doc["entities"]:
            eid = e["id"]
            if eid not in by_id:
                by_id[eid] = {
                    "id": eid,
                    "type": e["type"],
                    "name": e["name"],
                    "attrs": dict(e["attrs"]),
                    "source": list(e["source"]),
                    "domain": [e["domain"]],
                }
                continue
            existing = by_id[eid]
            for k, v in e["attrs"].items():
                existing["attrs"].setdefault(k, v)
            for s in e["source"]:
                if s not in existing["source"]:
                    existing["source"].append(s)
            if e["domain"] not in existing["domain"]:
                existing["domain"].append(e["domain"])
    return list(by_id.values())


def merge_relations(
    normalized_docs: list[dict[str, Any]], valid_ids: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    dropped: list[dict[str, Any]] = []
    for doc in normalized_docs:
        for r in doc["relations"]:
            src_ok = r["src_id"] in valid_ids
            dst_ok = r["dst_id"] in valid_ids
            if not (src_ok and dst_ok):
                dropped.append(
                    {
                        "src_id": r["src_id"],
                        "rel": r["rel"],
                        "dst_id": r["dst_id"],
                        "source": r["source"],
                        "domain": r["domain"],
                        "reason": "dangling_src" if not src_ok else "dangling_dst",
                    }
                )
                continue
            key = (r["src_id"], r["rel"], r["dst_id"])
            if key not in by_key:
                by_key[key] = {
                    "src_id": r["src_id"],
                    "rel": r["rel"],
                    "dst_id": r["dst_id"],
                    "source": list(r["source"]),
                    "domain": [r["domain"]],
                }
                continue
            existing = by_key[key]
            for s in r["source"]:
                if s not in existing["source"]:
                    existing["source"].append(s)
            if r["domain"] not in existing["domain"]:
                existing["domain"].append(r["domain"])
    return list(by_key.values()), dropped


def build_stats(
    entities: list[dict[str, Any]], relations: list[dict[str, Any]], dropped: list[dict[str, Any]]
) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    for e in entities:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    contradicts = sum(1 for r in relations if r["rel"] == "contradicts")
    cross_domain = [e for e in entities if len(e["domain"]) > 1]
    entities_no_source = [e["id"] for e in entities if not e["source"]]
    relations_no_source = sum(1 for r in relations if not r["source"])
    return {
        "total_entities": len(entities),
        "total_relations": len(relations),
        "entities_by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
        "contradicts_count": contradicts,
        "cross_domain_entity_count": len(cross_domain),
        "cross_domain_entity_ids": sorted(e["id"] for e in cross_domain),
        "provenance_gap_entity_count": len(entities_no_source),
        "provenance_gap_entity_ids": entities_no_source,
        "provenance_gap_relation_count": relations_no_source,
        "dropped_dangler_count": len(dropped),
    }


def merge(normalized_docs: list[dict[str, Any]]) -> dict[str, Any]:
    entities = merge_entities(normalized_docs)
    valid_ids = {e["id"] for e in entities}
    relations, dropped = merge_relations(normalized_docs, valid_ids)
    stats = build_stats(entities, relations, dropped)
    provenance_gaps = {
        "entities_missing_source": stats["provenance_gap_entity_ids"],
        "relations_missing_source_count": stats["provenance_gap_relation_count"],
    }
    return {
        "entities": entities,
        "relations": relations,
        "stats": stats,
        "provenance_gaps": provenance_gaps,
        "dropped_danglers": dropped,
    }
