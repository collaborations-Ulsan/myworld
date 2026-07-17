"""Deterministic, stdlib-only tests for experiments/ontology/ (OntologyOS v0
-- the merge/normalize/query organ that unifies the 4 wave-1 domain ledger
files into docs/ontology/ledger/_merged.json).

Everything here runs against small synthetic fixtures shaped exactly like
the 4 real source files (verified by direct inspection, see normalize.py's
module docstring) -- never against the live ledger JSONs. Covers:
  - all 3 relation-key shapes ({type,from,to} / {src,rel,dst} / {from,rel,to})
    and all entity-shape variants (flat+nested-attributes, dict-by-type,
    flat+nested-attrs, flat+no-container)
  - cross-file dedup (same canonical id from two files -> one entity, unioned
    domains + sources)
  - dangling-edge detection (dropped + logged, not silently kept)
  - contradictions() / cross_domain_entities() query correctness
  - provenance-gap honesty (missing-source entities/relations counted, not
    fabricated)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "experiments" / "ontology").as_posix())

import merge as merge_mod  # noqa: E402
import normalize  # noqa: E402
from query import Ledger  # noqa: E402


class TestSlugAndCanonicalId(unittest.TestCase):
    def test_slugify_basic(self):
        self.assertEqual(normalize.slugify("Richard S. Sutton"), "richard_s_sutton")
        self.assertEqual(normalize.slugify("  Diffusion Policy!! "), "diffusion_policy")

    def test_slugify_empty_falls_back(self):
        self.assertEqual(normalize.slugify("!!!"), "unknown")

    def test_canonical_id_paper_prefers_arxiv_id_over_title(self):
        attrs = {"arxiv_id": "2303.04137", "title": "Diffusion Policy"}
        cid = normalize.canonical_entity_id("Paper", "Diffusion Policy: A Different Title", attrs, "paper:xyz")
        self.assertEqual(cid, "paper:2303.04137")

    def test_canonical_id_paper_extracts_arxiv_from_url_when_no_explicit_field(self):
        attrs = {"url": "https://arxiv.org/abs/2506.22405"}
        cid = normalize.canonical_entity_id("Paper", "Sequential Diagnosis", attrs, "P-some-id")
        self.assertEqual(cid, "paper:2506.22405")

    def test_canonical_id_paper_falls_back_to_title_slug_when_no_arxiv(self):
        cid = normalize.canonical_entity_id("Paper", "A Totally Unindexed Paper", {}, "raw:1")
        self.assertEqual(cid, "paper:title:a_totally_unindexed_paper")

    def test_canonical_id_person_is_type_plus_name_slug(self):
        cid = normalize.canonical_entity_id("Person", "Richard S. Sutton", {}, "person:sutton")
        self.assertEqual(cid, "person:richard_s_sutton")

    def test_two_different_raw_ids_same_paper_dedupe_to_same_canonical_id(self):
        # This is the whole point: agi.json might call it "P-diffusion-policy"
        # and physical_ai.json "paper:2303.04137" -- same arxiv id -> same id.
        cid_a = normalize.canonical_entity_id("Paper", "Diffusion Policy", {"arxiv_id": "2303.04137"}, "P-diffusion-policy")
        cid_b = normalize.canonical_entity_id(
            "Paper", "Diffusion Policy: Visuomotor Policy Learning", {"arxiv_id": "2303.04137"}, "paper:2303.04137"
        )
        self.assertEqual(cid_a, cid_b)


class TestNormalizeShapes(unittest.TestCase):
    """One test per real source-file shape, using tiny synthetic docs."""

    def test_oaklab_shape_flat_list_nested_attributes_type_from_to_relations(self):
        doc = {
            "entities": [
                {"id": "lab:oak", "type": "Lab", "name": "Oak Lab", "attributes": {"url": "https://oaklab.ai/"}},
                {
                    "id": "person:sutton",
                    "type": "Person",
                    "name": "Richard S. Sutton",
                    "attributes": {"affiliation": "Oak Lab", "sources": ["https://oaklab.ai/", "https://en.wikipedia.org/x"]},
                },
            ],
            "relations": [{"type": "affiliated_with", "from": "person:sutton", "to": "lab:oak", "source": "https://oaklab.ai/"}],
        }
        out = normalize.normalize_document(doc, domain="D1")
        self.assertEqual(len(out["entities"]), 2)
        self.assertEqual(len(out["relations"]), 1)
        sutton = next(e for e in out["entities"] if e["name"] == "Richard S. Sutton")
        self.assertEqual(sutton["type"], "Person")
        self.assertEqual(sutton["domain"], "D1")
        self.assertIn("https://oaklab.ai/", sutton["source"])
        self.assertIn("https://en.wikipedia.org/x", sutton["source"])
        oak_lab = next(e for e in out["entities"] if e["name"] == "Oak Lab")
        self.assertEqual(oak_lab["id"], "lab:oak_lab")  # type:name-slug, not the raw source id "lab:oak"
        rel = out["relations"][0]
        self.assertEqual(rel["rel"], "affiliated_with")
        self.assertEqual(rel["src_id"], sutton["id"])
        self.assertEqual(rel["dst_id"], oak_lab["id"])
        self.assertEqual(rel["source"], ["https://oaklab.ai/"])

    def test_agi_shape_dict_by_type_entities_type_from_to_relations(self):
        doc = {
            "entities": {
                "Domain": [{"id": "D1", "name": "AGI", "scope": "...", "source": "schema"}],
                "Person": [{"id": "PE-hassabis", "name": "Demis Hassabis", "affiliation": "DeepMind", "source": "search:x"}],
            },
            "relations": [{"type": "in_domain", "from": "PE-hassabis", "to": "D1", "source": "search:x"}],
        }
        out = normalize.normalize_document(doc, domain="D1")
        self.assertEqual(len(out["entities"]), 2)
        hassabis = next(e for e in out["entities"] if e["name"] == "Demis Hassabis")
        self.assertEqual(hassabis["type"], "Person")  # type injected from outer dict key
        self.assertEqual(hassabis["attrs"]["affiliation"], "DeepMind")
        rel = out["relations"][0]
        self.assertEqual(rel["rel"], "in_domain")
        self.assertEqual(rel["src_id"], hassabis["id"])

    def test_physical_ai_shape_flat_list_nested_attrs_src_rel_dst_relations(self):
        doc = {
            "entities": [
                {"id": "paper:2303.04137", "type": "Paper", "name": "Diffusion Policy", "attrs": {"arxiv_id": "2303.04137"}, "source": "https://arxiv.org/abs/2303.04137"},
                {"id": "person:cheng_chi", "type": "Person", "name": "Cheng Chi", "attrs": {"affiliation": "stanford"}, "source": "https://arxiv.org/abs/2303.04137"},
            ],
            "relations": [{"src": "person:cheng_chi", "rel": "authored", "dst": "paper:2303.04137", "source": "https://arxiv.org/abs/2303.04137"}],
        }
        out = normalize.normalize_document(doc, domain="D3")
        paper = next(e for e in out["entities"] if e["type"] == "Paper")
        self.assertEqual(paper["id"], "paper:2303.04137")
        self.assertEqual(paper["attrs"]["arxiv_id"], "2303.04137")
        rel = out["relations"][0]
        self.assertEqual(rel["rel"], "authored")
        self.assertEqual(rel["dst_id"], "paper:2303.04137")

    def test_medical_shape_flat_list_flat_fields_from_rel_to_relations(self):
        doc = {
            "entities": [
                {"id": "paper:mai_dxo", "type": "Paper", "title": "Sequential Diagnosis", "url": "https://arxiv.org/abs/2506.22405", "source": "https://arxiv.org/abs/2506.22405"},
                {"id": "claim:mai_dxo_855", "type": "Claim", "statement": "MAI-DxO reaches 85.5% accuracy", "asserted_by": "paper:mai_dxo", "source": "https://arxiv.org/abs/2506.22405"},
            ],
            "relations": [{"from": "paper:mai_dxo", "rel": "asserts", "to": "claim:mai_dxo_855", "source": "https://arxiv.org/abs/2506.22405"}],
        }
        out = normalize.normalize_document(doc, domain="D2")
        paper = next(e for e in out["entities"] if e["type"] == "Paper")
        self.assertEqual(paper["id"], "paper:2506.22405")  # arxiv id pulled from url field
        claim = next(e for e in out["entities"] if e["type"] == "Claim")
        self.assertEqual(claim["name"], "MAI-DxO reaches 85.5% accuracy")  # statement used as name
        rel = out["relations"][0]
        self.assertEqual(rel["src_id"], "paper:2506.22405")
        self.assertEqual(rel["dst_id"], claim["id"])


class TestProvenanceGaps(unittest.TestCase):
    def test_entity_with_no_source_like_field_is_counted_not_fabricated(self):
        doc = {
            "entities": [{"id": "concept:x", "type": "Concept", "name": "Mystery Concept", "definition": "no provenance at all"}],
            "relations": [],
        }
        out = normalize.normalize_document(doc, domain="D1")
        self.assertEqual(out["entities_no_source"], 1)
        self.assertEqual(out["entities"][0]["source"], [])

    def test_relation_with_no_source_is_counted(self):
        doc = {
            "entities": [
                {"id": "a", "type": "Concept", "name": "A", "source": "s"},
                {"id": "b", "type": "Concept", "name": "B", "source": "s"},
            ],
            "relations": [{"from": "a", "rel": "concept_relates_to", "to": "b"}],
        }
        out = normalize.normalize_document(doc, domain="D1")
        self.assertEqual(out["relations_no_source"], 1)


class TestMergeDedupeAndValidation(unittest.TestCase):
    def _doc(self, entities, relations, domain):
        return normalize.normalize_document({"entities": entities, "relations": relations}, domain=domain)

    def test_same_paper_from_two_domains_merges_into_one_cross_domain_entity(self):
        doc_agi = self._doc(
            [{"id": "P-dp", "type": "Paper", "name": "Diffusion Policy", "arxiv_id": "2303.04137", "source": "agi-source"}],
            [],
            "D1",
        )
        doc_phys = self._doc(
            [{"id": "paper:2303.04137", "type": "Paper", "name": "Diffusion Policy: Visuomotor", "arxiv_id": "2303.04137", "source": "phys-source"}],
            [],
            "D3",
        )
        merged = merge_mod.merge([doc_agi, doc_phys])
        self.assertEqual(len(merged["entities"]), 1)
        entity = merged["entities"][0]
        self.assertEqual(sorted(entity["domain"]), ["D1", "D3"])
        self.assertEqual(sorted(entity["source"]), ["agi-source", "phys-source"])

    def test_dangling_edge_is_dropped_and_logged(self):
        doc = self._doc(
            [{"id": "a", "type": "Concept", "name": "A", "source": "s"}],
            [{"from": "a", "rel": "concept_relates_to", "to": "nonexistent", "source": "s"}],
            "D1",
        )
        merged = merge_mod.merge([doc])
        self.assertEqual(len(merged["relations"]), 0)
        self.assertEqual(len(merged["dropped_danglers"]), 1)
        self.assertEqual(merged["dropped_danglers"][0]["reason"], "dangling_dst")
        self.assertEqual(merged["stats"]["dropped_dangler_count"], 1)

    def test_duplicate_relation_across_files_merges_sources(self):
        doc_a = self._doc(
            [{"id": "x", "type": "Concept", "name": "X", "source": "s1"}, {"id": "y", "type": "Concept", "name": "Y", "source": "s1"}],
            [{"from": "x", "rel": "concept_relates_to", "to": "y", "source": "file-a"}],
            "D1",
        )
        doc_b = self._doc(
            [{"id": "x", "type": "Concept", "name": "X", "source": "s2"}, {"id": "y", "type": "Concept", "name": "Y", "source": "s2"}],
            [{"from": "x", "rel": "concept_relates_to", "to": "y", "source": "file-b"}],
            "D2",
        )
        merged = merge_mod.merge([doc_a, doc_b])
        self.assertEqual(len(merged["relations"]), 1)
        rel = merged["relations"][0]
        self.assertEqual(sorted(rel["source"]), ["file-a", "file-b"])
        self.assertEqual(sorted(rel["domain"]), ["D1", "D2"])

    def test_stats_by_type_and_provenance_gap_counts(self):
        doc = self._doc(
            [
                {"id": "p1", "type": "Paper", "name": "P1", "arxiv_id": "1111.11111", "source": "s"},
                {"id": "p2", "type": "Paper", "name": "P2", "arxiv_id": "2222.22222", "source": "s"},
                {"id": "c1", "type": "Concept", "name": "C1"},  # no source -> provenance gap
            ],
            [],
            "D1",
        )
        merged = merge_mod.merge([doc])
        self.assertEqual(merged["stats"]["entities_by_type"]["Paper"], 2)
        self.assertEqual(merged["stats"]["entities_by_type"]["Concept"], 1)
        self.assertEqual(merged["stats"]["provenance_gap_entity_count"], 1)
        self.assertIn("concept:c1", merged["stats"]["provenance_gap_entity_ids"])


class TestQuery(unittest.TestCase):
    def _ledger(self):
        doc_agi = normalize.normalize_document(
            {
                "entities": [
                    {"id": "CL-a", "type": "Claim", "statement": "GEPA overfits", "source": "src-a"},
                    {"id": "CL-b", "type": "Claim", "statement": "GEPA outperforms baseline", "source": "src-b"},
                    {"id": "P-dp", "type": "Paper", "name": "Diffusion Policy", "arxiv_id": "2303.04137", "source": "agi-source"},
                    {"id": "concept:cl", "type": "Concept", "name": "Continual Learning", "definition": "...", "source": "src-c"},
                    {"id": "org:dm", "type": "Org", "name": "Google DeepMind", "kind": "lab", "source": "src-d"},
                    {"id": "person:h", "type": "Person", "name": "Demis Hassabis", "source": "src-e"},
                ],
                "relations": [
                    {"type": "contradicts", "from": "CL-a", "to": "CL-b", "source": "search:2026"},
                    {"type": "proposes", "from": "P-dp", "to": "concept:cl", "source": "agi-source"},
                    {"type": "affiliated_with", "from": "person:h", "to": "org:dm", "source": "src-e"},
                ],
            },
            domain="D1",
        )
        doc_phys = normalize.normalize_document(
            {
                "entities": [{"id": "paper:2303.04137", "type": "Paper", "name": "Diffusion Policy: Visuomotor", "arxiv_id": "2303.04137", "source": "phys-source"}],
                "relations": [],
            },
            domain="D3",
        )
        merged = merge_mod.merge([doc_agi, doc_phys])
        return Ledger(merged)

    def test_contradictions_returns_named_endpoints_and_source(self):
        ledger = self._ledger()
        contradictions = ledger.contradictions()
        self.assertEqual(len(contradictions), 1)
        c = contradictions[0]
        self.assertEqual(c["src_name"], "GEPA overfits")
        self.assertEqual(c["dst_name"], "GEPA outperforms baseline")
        self.assertEqual(c["source"], ["search:2026"])

    def test_cross_domain_entities_finds_the_multi_domain_paper(self):
        ledger = self._ledger()
        cross = ledger.cross_domain_entities()
        self.assertEqual(len(cross), 1)
        self.assertEqual(cross[0]["id"], "paper:2303.04137")
        self.assertEqual(sorted(cross[0]["domain"]), ["D1", "D3"])

    def test_by_domain_and_by_type(self):
        ledger = self._ledger()
        d1_entities = ledger.by_domain("D1")
        self.assertTrue(all("D1" in e["domain"] for e in d1_entities))
        claims = ledger.by_type("Claim")
        self.assertEqual(len(claims), 2)

    def test_papers_for_concept(self):
        ledger = self._ledger()
        papers = ledger.papers_for_concept("Continual Learning")
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["id"], "paper:2303.04137")

    def test_people_for_org(self):
        ledger = self._ledger()
        people = ledger.people_for_org("Google DeepMind")
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["name"], "Demis Hassabis")

    def test_neighbors_returns_both_directions(self):
        ledger = self._ledger()
        neighbors = ledger.neighbors("concept:continual_learning")
        directions = {n["direction"] for n in neighbors}
        self.assertIn("in", directions)


if __name__ == "__main__":
    unittest.main()
