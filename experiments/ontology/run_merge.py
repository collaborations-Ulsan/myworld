#!/usr/bin/env python3
"""experiments/ontology/run_merge.py -- OntologyOS v0 orchestrator.

Loads the 4 wave-1 domain ledger files (read-only), runs each through its
normalize.py adapter, merges via merge.py, and writes the unified,
deduped, validated knowledge ledger to docs/ontology/ledger/_merged.json.
Prints a summary: unique entities/relations after dedup, per-type counts,
contradicts count, cross-domain-entity count, provenance-gap count, dropped-
dangler count.

This is the QA gate for wave-1 (FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md): if
a source file doesn't normalize cleanly, this script reports exactly why
instead of forcing a shape onto it.

Usage:
    python3 experiments/ontology/run_merge.py            # human-readable summary
    python3 experiments/ontology/run_merge.py --json      # machine-readable summary
    python3 experiments/ontology/run_merge.py --out PATH  # write elsewhere
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import merge as merge_mod  # noqa: E402
import normalize  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ("oaklab", REPO_ROOT / "docs" / "ontology" / "oaklab_agi_ontology.json", normalize.normalize_oaklab),
    ("agi", REPO_ROOT / "docs" / "ontology" / "ledger" / "agi.json", normalize.normalize_agi),
    ("physical_ai", REPO_ROOT / "docs" / "ontology" / "ledger" / "physical_ai.json", normalize.normalize_physical_ai),
    ("medical", REPO_ROOT / "docs" / "ontology" / "ledger" / "medical.json", normalize.normalize_medical),
    # D6+ domain files use the CANONICAL format ({src_id,rel,dst_id}, flat entities)
    # so the shape-detecting load_and_normalize handles them directly.
    ("learning_methods", REPO_ROOT / "docs" / "ontology" / "ledger" / "learning_methods.json",
     lambda p: normalize.load_and_normalize(p, "D6")),
    ("reasoning_verification_rl", REPO_ROOT / "docs" / "ontology" / "ledger" / "reasoning_verification_rl.json",
     lambda p: normalize.load_and_normalize(p, "D5")),
    ("society_assembly", REPO_ROOT / "docs" / "ontology" / "ledger" / "society_assembly.json",
     lambda p: normalize.load_and_normalize(p, "D7")),
]
DEFAULT_OUT = REPO_ROOT / "docs" / "ontology" / "ledger" / "_merged.json"


def run(out_path: Path = DEFAULT_OUT) -> dict:
    normalized_docs = []
    per_file_report = []
    for name, path, adapter in SOURCES:
        if not path.exists():
            per_file_report.append({"file": name, "error": f"missing: {path}"})
            continue
        try:
            doc = adapter(path)
        except Exception as exc:  # honest failure report, not a forced shape
            per_file_report.append({"file": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        normalized_docs.append(doc)
        per_file_report.append(
            {
                "file": name,
                "entities": len(doc["entities"]),
                "relations": len(doc["relations"]),
                "entities_no_source": doc["entities_no_source"],
                "relations_no_source": doc["relations_no_source"],
            }
        )

    merged = merge_mod.merge(normalized_docs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {"per_file": per_file_report, "merged_stats": merged["stats"], "out_path": str(out_path)}


def _print_human(summary: dict) -> None:
    print("=== OntologyOS v0 merge summary ===")
    for row in summary["per_file"]:
        if "error" in row:
            print(f"  {row['file']}: FAILED ({row['error']})")
            continue
        print(
            f"  {row['file']}: {row['entities']} entities, {row['relations']} relations "
            f"(no-source: {row['entities_no_source']} entities / {row['relations_no_source']} relations)"
        )
    stats = summary["merged_stats"]
    print(f"\nUnique entities after dedup: {stats['total_entities']}")
    print(f"Unique relations after dedup + dangling-drop: {stats['total_relations']}")
    print("By type:")
    for t, c in stats["entities_by_type"].items():
        print(f"  {t}: {c}")
    print(f"contradicts edges: {stats['contradicts_count']}")
    print(f"cross-domain entities: {stats['cross_domain_entity_count']}")
    print(
        f"provenance gaps: {stats['provenance_gap_entity_count']} entities, "
        f"{stats['provenance_gap_relation_count']} relations"
    )
    print(f"dropped dangling edges: {stats['dropped_dangler_count']}")
    print(f"\nwrote {summary['out_path']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--json", action="store_true", help="print summary as JSON instead of human-readable text")
    args = ap.parse_args()

    summary = run(args.out)
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        _print_human(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
