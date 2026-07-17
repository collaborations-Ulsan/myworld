#!/usr/bin/env python3
"""experiments/ontology/query.py -- query API + CLI over the merged ledger
(docs/ontology/ledger/_merged.json, written by run_merge.py).

Library:
    from query import Ledger
    ledger = Ledger.load()
    ledger.contradictions()
    ledger.cross_domain_entities()

CLI:
    python3 experiments/ontology/query.py contradictions
    python3 experiments/ontology/query.py cross-domain
    python3 experiments/ontology/query.py domain D1
    python3 experiments/ontology/query.py type Paper
    python3 experiments/ontology/query.py methodology diffusion
    python3 experiments/ontology/query.py concept "continual learning"
    python3 experiments/ontology/query.py org "Google DeepMind"
    python3 experiments/ontology/query.py neighbors paper:2303.04137
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MERGED = REPO_ROOT / "docs" / "ontology" / "ledger" / "_merged.json"


class Ledger:
    """Thin in-memory index over the merged {entities, relations} ledger."""

    def __init__(self, data: dict[str, Any]):
        self.entities: list[dict[str, Any]] = data["entities"]
        self.relations: list[dict[str, Any]] = data["relations"]
        self.by_id: dict[str, dict[str, Any]] = {e["id"]: e for e in self.entities}

    @classmethod
    def load(cls, path: Path = DEFAULT_MERGED) -> "Ledger":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def by_domain(self, domain: str) -> list[dict[str, Any]]:
        return [e for e in self.entities if domain in e.get("domain", [])]

    def by_type(self, etype: str) -> list[dict[str, Any]]:
        return [e for e in self.entities if e["type"] == etype]

    def _resolve_one(self, query: str, etypes: tuple[str, ...]) -> dict[str, Any] | None:
        """Resolve a free-text query (id, exact name, or substring of name)
        to a single entity restricted to the given types. Exact matches win
        over substring matches."""
        q = query.strip().lower()
        candidates = [e for e in self.entities if e["type"] in etypes]
        for e in candidates:
            if e["id"].lower() == q or e["name"].lower() == q:
                return e
        for e in candidates:
            if q in e["name"].lower():
                return e
        return None

    def by_methodology(self, methodology: str) -> list[dict[str, Any]]:
        """Entities practicing a methodology: Methods linked via method_is_a,
        plus any entity whose attrs.methodology names it directly (several
        source files tag Papers with attrs.methodology as a shortcut)."""
        meth = self._resolve_one(methodology, ("Methodology",))
        results: dict[str, dict[str, Any]] = {}
        if meth is not None:
            for r in self.relations:
                if r["rel"] == "method_is_a" and r["dst_id"] == meth["id"]:
                    e = self.by_id.get(r["src_id"])
                    if e:
                        results[e["id"]] = e
        q = methodology.strip().lower()
        for e in self.entities:
            m = e.get("attrs", {}).get("methodology")
            if not isinstance(m, str):
                continue
            if m.lower() == q or (meth is not None and m.lower() in {meth["id"].lower(), meth["id"].split(":", 1)[-1].lower()}):
                results[e["id"]] = e
        return list(results.values())

    def contradictions(self) -> list[dict[str, Any]]:
        """Every contradicts edge, with both endpoints' names + the edge's
        own source(s) -- the frontier disagreements the ledger is meant to
        surface (schema doc §4: 'contradicts 엣지는 보존')."""
        out = []
        for r in self.relations:
            if r["rel"] != "contradicts":
                continue
            src = self.by_id.get(r["src_id"])
            dst = self.by_id.get(r["dst_id"])
            out.append(
                {
                    "src_id": r["src_id"],
                    "src_name": src["name"] if src else None,
                    "dst_id": r["dst_id"],
                    "dst_name": dst["name"] if dst else None,
                    "source": r["source"],
                    "domain": r["domain"],
                }
            )
        return out

    def papers_for_concept(self, concept: str) -> list[dict[str, Any]]:
        c = self._resolve_one(concept, ("Concept",))
        if c is None:
            return []
        out = []
        for r in self.relations:
            if r["rel"] == "proposes" and r["dst_id"] == c["id"]:
                e = self.by_id.get(r["src_id"])
                if e and e["type"] == "Paper":
                    out.append(e)
        return out

    def people_for_org(self, org: str) -> list[dict[str, Any]]:
        o = self._resolve_one(org, ("Org", "Lab"))
        if o is None:
            return []
        out = []
        for r in self.relations:
            if r["rel"] == "affiliated_with" and r["dst_id"] == o["id"]:
                e = self.by_id.get(r["src_id"])
                if e and e["type"] == "Person":
                    out.append(e)
        return out

    def cross_domain_entities(self) -> list[dict[str, Any]]:
        """Entities tagged with >1 domain -- the interesting nodes: what one
        real paper/person/concept spans multiple wave-1 frontier domains."""
        out = [e for e in self.entities if len(e.get("domain", [])) > 1]
        return sorted(out, key=lambda e: (-len(e["domain"]), e["name"]))

    def neighbors(self, entity_id: str) -> list[dict[str, Any]]:
        out = []
        for r in self.relations:
            if r["src_id"] == entity_id:
                other = self.by_id.get(r["dst_id"])
                out.append(
                    {"direction": "out", "rel": r["rel"], "other_id": r["dst_id"], "other_name": other["name"] if other else None}
                )
            elif r["dst_id"] == entity_id:
                other = self.by_id.get(r["src_id"])
                out.append(
                    {"direction": "in", "rel": r["rel"], "other_id": r["src_id"], "other_name": other["name"] if other else None}
                )
        return out


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--merged", type=Path, default=DEFAULT_MERGED)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("contradictions")
    sub.add_parser("cross-domain")
    for name in ("domain", "type", "methodology", "concept", "org", "neighbors"):
        p = sub.add_parser(name)
        p.add_argument("value")

    args = ap.parse_args()
    if not args.merged.exists():
        print(f"error: {args.merged} not found -- run experiments/ontology/run_merge.py first", file=sys.stderr)
        return 1
    ledger = Ledger.load(args.merged)

    if args.cmd == "contradictions":
        _print(ledger.contradictions())
    elif args.cmd == "cross-domain":
        _print(ledger.cross_domain_entities())
    elif args.cmd == "domain":
        _print(ledger.by_domain(args.value))
    elif args.cmd == "type":
        _print(ledger.by_type(args.value))
    elif args.cmd == "methodology":
        _print(ledger.by_methodology(args.value))
    elif args.cmd == "concept":
        _print(ledger.papers_for_concept(args.value))
    elif args.cmd == "org":
        _print(ledger.people_for_org(args.value))
    elif args.cmd == "neighbors":
        _print(ledger.neighbors(args.value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
