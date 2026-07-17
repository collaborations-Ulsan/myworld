"""experiments/ontology/normalize.py -- per-file adapters that normalize the
4 wave-1 domain ledger JSONs into ONE canonical schema (OntologyOS v0).

The 4 source files (read-only, never edited by this organ) diverge
structurally -- confirmed by inspection, not assumed:

  - docs/ontology/oaklab_agi_ontology.json  -- entities: flat list, per-entity
    fields nested under "attributes"; relations: {type, from, to, source}.
  - docs/ontology/ledger/agi.json           -- entities: NESTED dict-by-type
    ({"Domain": [...], "Person": [...], ...}, no per-entity "type" key);
    relations: {type, from, to, source}.
  - docs/ontology/ledger/physical_ai.json   -- entities: flat list, per-entity
    fields nested under "attrs"; relations: {src, rel, dst, source}.
  - docs/ontology/ledger/medical.json       -- entities: flat list, fields
    directly on the entity (no nested container); relations: {from, rel, to,
    source}.

Canonical entity: {id, type, name, attrs, source, domain}
Canonical relation: {src_id, rel, dst_id, source, domain}

`id` is DERIVED, not copied verbatim from the source file's own "id" field,
so the SAME real-world Paper/Person/Concept/Org referenced from two
different domain files collapses to one canonical id at merge time (see
merge.py):
  - Paper: an arxiv id if discoverable (attrs.arxiv_id / attrs.arxiv / an
    arxiv.org URL / an id string containing an arxiv-shaped id), else a slug
    of the title.
  - everything else: "<type-lower>:<slug(name)>".
This is a real, acknowledged limitation: name-slug matching does not fuzzy-
match e.g. "Richard Sutton" against "Richard S. Sutton" -- only exact
(case/punctuation-normalized) name collisions dedupe. That is reported
honestly in the live-run summary, not hidden.

Provenance: every node/edge keeps whatever source-like field the source file
actually used (source / sources / url / provenance / ref -- top-level or
nested under attributes/attrs). Entities/relations with NONE of these are
counted and reported as provenance gaps by merge.py -- never fabricated.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ARXIV_RE = re.compile(r"(\d{4}\.\d{4,5})")
SOURCE_KEYS = ("source", "sources", "url", "provenance", "ref")
# Structural keys on a raw entity that are NOT free-form attrs data.
_ENTITY_RESERVED = {"id", "type", "name", "title", "statement", "attributes", "attrs", "domain"}
_RELATION_SRC_ALIASES = ("src", "from")
_RELATION_DST_ALIASES = ("dst", "to")
_RELATION_REL_ALIASES = ("rel", "type")

_SLUG_LIMIT = 80


def slugify(text: str) -> str:
    """Lowercase, non-alnum -> underscore, collapsed. Pure function (tested)."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def _bounded_slug(label: str, limit: int = _SLUG_LIMIT) -> str:
    """slugify() but bounded -- long Claim statements would otherwise produce
    unwieldy ids. Deterministic: same label always -> same truncated id."""
    s = slugify(label)
    if len(s) <= limit:
        return s
    digest = hashlib.md5(label.encode("utf-8")).hexdigest()[:8]
    return f"{s[:limit]}_{digest}"


def _find_arxiv_id(raw_id: str, attrs: dict[str, Any], sources: list[str] | None = None) -> str | None:
    """Look for an arxiv id in, in order: explicit attrs.arxiv_id/arxiv,
    every collected source string (this is where a plain "url" field lands,
    since url is folded into `source` rather than duplicated into attrs),
    and finally the raw id itself."""
    candidates: list[str] = []
    for key in ("arxiv_id", "arxiv"):
        v = attrs.get(key)
        if isinstance(v, str):
            candidates.append(v)
    # url/source may still be present in attrs when this helper is called
    # directly (outside the normal _normalize_entity pipeline, where they are
    # instead folded into `sources` and excluded from attrs).
    for key in ("url", "source"):
        v = attrs.get(key)
        if isinstance(v, str):
            candidates.append(v)
    candidates.extend(sources or [])
    candidates.append(raw_id or "")
    for c in candidates:
        m = ARXIV_RE.search(c)
        if m:
            return m.group(1)
    return None


def canonical_entity_id(
    etype: str, label: str, attrs: dict[str, Any], raw_id: str, sources: list[str] | None = None
) -> str:
    """The dedup key. Paper -> arxiv id (preferred) else title slug.
    Everything else -> "<type>:<name-slug>"."""
    if etype == "Paper":
        arxiv_id = _find_arxiv_id(raw_id, attrs, sources)
        if arxiv_id:
            return f"paper:{arxiv_id}"
        return f"paper:title:{_bounded_slug(label)}"
    return f"{slugify(etype)}:{_bounded_slug(label)}"


def _collect_sources(entity: dict[str, Any], attrs_container: dict[str, Any]) -> list[str]:
    """Scan both the entity's top-level fields and its nested attrs/attributes
    container for any of SOURCE_KEYS; dedup, preserve first-seen order."""
    found: list[str] = []
    for container in (entity, attrs_container):
        for key in SOURCE_KEYS:
            v = container.get(key)
            if v is None:
                continue
            if isinstance(v, str):
                if v.strip():
                    found.append(v.strip())
            elif isinstance(v, list):
                found.extend(str(x).strip() for x in v if str(x).strip())
    seen: set[str] = set()
    out: list[str] = []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _normalize_entity(entity: dict[str, Any], etype: str, domain: str) -> tuple[str, dict[str, Any]]:
    """Return (raw_id, canonical_entity_dict). Caller builds the raw-id -> canonical-id map."""
    raw_id = str(entity.get("id", ""))
    label = entity.get("name") or entity.get("title") or entity.get("statement") or raw_id
    label = str(label)
    nested = entity.get("attributes") or entity.get("attrs") or {}

    attrs: dict[str, Any] = {}
    for k, v in entity.items():
        if k in _ENTITY_RESERVED or k in SOURCE_KEYS:
            continue
        attrs[k] = v
    for k, v in nested.items():
        if k in SOURCE_KEYS:
            continue
        attrs.setdefault(k, v)

    source = _collect_sources(entity, nested)
    cid = canonical_entity_id(etype, label, attrs, raw_id, source)
    canonical = {
        "id": cid,
        "type": etype,
        "name": label,
        "attrs": attrs,
        "source": source,
        "domain": domain,
    }
    return raw_id, canonical


def _normalize_relation(rel: dict[str, Any], id_map: dict[str, str], domain: str) -> dict[str, Any] | None:
    rel_name = next((rel[k] for k in _RELATION_REL_ALIASES if k in rel), None)
    raw_src = next((rel[k] for k in _RELATION_SRC_ALIASES if k in rel), None)
    raw_dst = next((rel[k] for k in _RELATION_DST_ALIASES if k in rel), None)
    if rel_name is None or raw_src is None or raw_dst is None:
        return None
    # Unresolved raw ids are deliberately kept AS-IS (not fabricated into a
    # fake canonical id): merge.py's dangling-edge validator is the single
    # source of truth for "does this edge resolve to a real entity", so an
    # id that never appeared in this file's own entity list surfaces there.
    src_id = id_map.get(str(raw_src), str(raw_src))
    dst_id = id_map.get(str(raw_dst), str(raw_dst))
    source = rel.get("source")
    if isinstance(source, str):
        source_list = [source.strip()] if source.strip() else []
    elif isinstance(source, list):
        source_list = [str(s).strip() for s in source if str(s).strip()]
    else:
        source_list = []
    return {"src_id": src_id, "rel": str(rel_name), "dst_id": dst_id, "source": source_list, "domain": domain}


def _iter_raw_entities(entities_field: Any):
    """Yield (raw_entity_dict, type_hint_or_None). Handles both the flat-list
    shape (oaklab/physical_ai/medical) and agi.json's dict-keyed-by-type shape."""
    if isinstance(entities_field, dict):
        for etype, items in entities_field.items():
            for item in items:
                yield item, etype
    else:
        for item in entities_field:
            yield item, None


def normalize_document(data: dict[str, Any], domain: str) -> dict[str, Any]:
    """Shape-detecting normalizer shared by all 4 per-file adapters below.
    Auto-detects entities-as-list vs entities-as-dict-by-type, and per-entity
    attrs nested under 'attributes'/'attrs' vs flat -- no shape is assumed."""
    entities: list[dict[str, Any]] = []
    id_map: dict[str, str] = {}
    entities_no_source = 0

    for raw_entity, type_hint in _iter_raw_entities(data.get("entities", [])):
        etype = raw_entity.get("type") or type_hint
        if not etype:
            continue
        raw_id, canonical = _normalize_entity(raw_entity, etype, domain)
        if not canonical["source"]:
            entities_no_source += 1
        id_map[raw_id] = canonical["id"]
        entities.append(canonical)

    relations: list[dict[str, Any]] = []
    relations_no_source = 0
    for raw_rel in data.get("relations", []):
        canonical_rel = _normalize_relation(raw_rel, id_map, domain)
        if canonical_rel is None:
            continue
        if not canonical_rel["source"]:
            relations_no_source += 1
        relations.append(canonical_rel)

    return {
        "entities": entities,
        "relations": relations,
        "entities_no_source": entities_no_source,
        "relations_no_source": relations_no_source,
    }


def load_and_normalize(path: Path, domain: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    result = normalize_document(data, domain)
    result["source_file"] = str(path)
    return result


# -- explicit per-file adapters (thin; named for traceability + the domain
# each source file is treated as belonging to) -------------------------------

def normalize_oaklab(path: Path, domain: str = "D1") -> dict[str, Any]:
    """docs/ontology/oaklab_agi_ontology.json -- flat entity list, nested
    'attributes', relations {type, from, to}. Treated as domain D1 (AGI):
    per FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md §4, this file IS the OakLab
    AGI-ontology "first instance" the unified schema was validated against."""
    return load_and_normalize(path, domain)


def normalize_agi(path: Path, domain: str = "D1") -> dict[str, Any]:
    """docs/ontology/ledger/agi.json -- entities nested dict-by-type (no
    per-entity 'type' key -- injected from the outer dict key), relations
    {type, from, to}."""
    return load_and_normalize(path, domain)


def normalize_physical_ai(path: Path, domain: str = "D3") -> dict[str, Any]:
    """docs/ontology/ledger/physical_ai.json -- flat entity list, nested
    'attrs', relations {src, rel, dst}."""
    return load_and_normalize(path, domain)


def normalize_medical(path: Path, domain: str = "D2") -> dict[str, Any]:
    """docs/ontology/ledger/medical.json -- flat entity list, flat fields
    (no nested attrs container), relations {from, rel, to}."""
    return load_and_normalize(path, domain)
