"""QA for the OpenCrab Pack v1 exporter (experiments/ontology/pack_export.py)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "ontology"))
import pack_export as pe  # noqa: E402

SAMPLE = {
    "entities": [
        {"id": "person:sutton", "type": "Person", "name": "Richard Sutton",
         "attrs": {"field": "RL"}, "source": ["https://oaklab.ai/"], "domain": ["D1"]},
        {"id": "lab:oak", "type": "Lab", "name": "Oak Lab", "attrs": {},
         "source": ["https://oaklab.ai/", "paper:x"], "domain": ["D1", "D2"]},
        {"id": "concept:agi", "type": "Concept", "name": "AGI", "attrs": {},
         "source": [], "domain": ["D1"]},  # provenance gap: no source
    ],
    "relations": [
        {"src_id": "person:sutton", "rel": "affiliated_with", "dst_id": "lab:oak",
         "source": ["https://oaklab.ai/"], "domain": ["D1"]},
    ],
    "stats": {"contradicts_count": 3, "cross_domain_entity_count": 1,
              "provenance_gap_entity_count": 1, "provenance_gap_relation_count": 0,
              "dropped_dangler_count": 0, "entities_by_type": {"Person": 1, "Lab": 1, "Concept": 1}},
}


def test_build_pack_counts_and_shape():
    pack = pe.build_pack(SAMPLE)
    assert pack["manifest"]["counts"] == {"nodes": 3, "edges": 1, "evidence": 2}
    # every node/edge carries a content hash + evidence id list
    assert all(n["hash"].startswith("sha256:") for n in pack["nodes"])
    assert all("evidence" in e for e in pack["edges"])
    assert pack["manifest"]["schema"] == "opencrab-pack" and pack["manifest"]["version"] == "v1"
    assert "jsonld_context" in pack["manifest"]


def test_evidence_dedup_across_nodes_and_edges():
    pack = pe.build_pack(SAMPLE)
    # "https://oaklab.ai/" appears on 2 entities + 1 relation -> exactly ONE evidence record
    ids = [e["evidence_id"] for e in pack["evidence"]]
    assert len(ids) == len(set(ids)) == 2  # oaklab.ai + paper:x
    oak_id = pe._evidence_id("https://oaklab.ai/")
    assert oak_id in ids
    # sutton node and the affiliation edge both reference the same evidence id
    sutton = next(n for n in pack["nodes"] if n["id"] == "person:sutton")
    edge = pack["edges"][0]
    assert oak_id in sutton["evidence"] and oak_id in edge["evidence"]


def test_provenance_gap_node_has_empty_evidence():
    pack = pe.build_pack(SAMPLE)
    agi = next(n for n in pack["nodes"] if n["id"] == "concept:agi")
    assert agi["evidence"] == []


def test_merkle_root_deterministic_and_sensitive():
    r1 = pe.build_pack(SAMPLE)["manifest"]["merkle_root"]
    r2 = pe.build_pack(json.loads(json.dumps(SAMPLE)))["manifest"]["merkle_root"]
    assert r1 == r2 and r1.startswith("sha256:")
    mutated = json.loads(json.dumps(SAMPLE))
    mutated["entities"][0]["name"] = "TAMPERED"
    assert pe.build_pack(mutated)["manifest"]["merkle_root"] != r1


def test_merkle_root_empty():
    assert pe.merkle_root([]) == "sha256:" + pe._sha256("")


def test_roundtrip_write_read_verify(tmp_path):
    pack = pe.build_pack(SAMPLE)
    out = pe.write_pack(pack, tmp_path / "pack.zip")
    assert out.exists()
    reread = pe.read_pack(out)
    assert reread["manifest"]["counts"] == pack["manifest"]["counts"]
    ok, msg = pe.verify_pack(reread)
    assert ok, msg


def test_verify_detects_tamper(tmp_path):
    pack = pe.build_pack(SAMPLE)
    out = pe.write_pack(pack, tmp_path / "pack.zip")
    reread = pe.read_pack(out)
    reread["nodes"][0]["name"] = "TAMPERED"  # mutate content but keep old hash
    ok, msg = pe.verify_pack(reread)
    assert not ok and "hash mismatch" in msg


def test_quality_report_carries_stats():
    pack = pe.build_pack(SAMPLE)
    q = pack["quality"]
    assert q["contradicts_count"] == 3
    assert q["provenance_gap_entity_count"] == 1
    assert q["total_nodes"] == 3 and q["total_edges"] == 1
    assert q["merkle_root"] == pack["manifest"]["merkle_root"]


def test_real_ledger_export_smoke(tmp_path):
    """Export the REAL merged ledger if present; verify it round-trips."""
    if not pe.DEFAULT_IN.exists():
        pytest.skip("no _merged.json")
    result = pe.export(pe.DEFAULT_IN, tmp_path / "real_pack.zip")
    assert result["self_verify"], result["verify_msg"]
    assert result["counts"]["nodes"] > 0 and result["counts"]["edges"] > 0
    ok, msg = pe.verify_pack(pe.read_pack(tmp_path / "real_pack.zip"))
    assert ok, msg
