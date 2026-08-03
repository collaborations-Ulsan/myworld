from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "experiments" / "evolution_sprint" / "semantic_mutation.py"

spec = importlib.util.spec_from_file_location("semantic_mutation_under_test", MODULE_PATH)
semantic_mutation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = semantic_mutation
spec.loader.exec_module(semantic_mutation)


def broken_artifact() -> semantic_mutation.FailedArtifact:
    return semantic_mutation.FailedArtifact(
        artifact_id="test-broken-add",
        function_source="def add(a, b):\n    return a - b\n",
        failing_unit_test="assert add(2, 3) == 5\nassert add(-2, 7) == 5\n",
        error_text="AssertionError: expected 5",
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_deterministic_offline_mutation_produces_candidate() -> None:
    candidates, meta = semantic_mutation.generate_candidates(
        broken_artifact(),
        n=4,
        use_llm=False,
    )

    assert meta["mode"] == "deterministic_offline"
    assert meta["degraded"] is True
    assert candidates
    assert any("return a + b" in candidate.code for candidate in candidates)


def test_passing_candidate_is_marked_survivor(tmp_path: Path) -> None:
    artifact = broken_artifact()
    candidate = semantic_mutation.Candidate(
        code="def add(a, b):\n    return a + b\n",
        source="unit",
    )
    sandbox, error = semantic_mutation._load_sandbox(ROOT)
    assert sandbox is not None, error

    result = semantic_mutation.evaluate_candidate(
        candidate,
        artifact,
        now="2026-07-25T00:00:00+00:00",
        sandbox_module=sandbox,
        receipt_log=tmp_path / "sandbox_receipts.jsonl",
    )

    assert result["verdict"] == "survivor"
    assert result["survivor"] is True
    assert result["sandboxed"] is True


def test_failing_candidate_is_rejected(tmp_path: Path) -> None:
    artifact = broken_artifact()
    candidate = semantic_mutation.Candidate(
        code="def add(a, b):\n    return a - b\n",
        source="unit",
    )
    sandbox, error = semantic_mutation._load_sandbox(ROOT)
    assert sandbox is not None, error

    result = semantic_mutation.evaluate_candidate(
        candidate,
        artifact,
        now="2026-07-25T00:00:01+00:00",
        sandbox_module=sandbox,
        receipt_log=tmp_path / "sandbox_receipts.jsonl",
    )

    assert result["verdict"] == "rejected"
    assert result["survivor"] is False
    assert result["sandboxed"] is True
    assert result["returncode"] != 0


def test_sandbox_unavailable_refuses_without_unsandboxed_execution(tmp_path: Path) -> None:
    marker = tmp_path / "should_not_exist"
    artifact = semantic_mutation.FailedArtifact(
        artifact_id="sandbox-refusal",
        function_source="def touch_marker():\n    return 'parent'\n",
        failing_unit_test=(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
            "assert touch_marker() == 'child'\n"
        ),
        error_text="forced sandbox unavailable",
    )
    candidate = semantic_mutation.Candidate(
        code="def touch_marker():\n    return 'child'\n",
        source="unit",
    )

    result = semantic_mutation.evaluate_candidate(
        candidate,
        artifact,
        now="2026-07-25T00:00:02+00:00",
        sandbox_module=None,
        sandbox_error="forced missing sandbox",
    )

    assert result["verdict"] == "refused_sandbox_unavailable"
    assert result["sandboxed"] is False
    assert not marker.exists()


def test_lineage_is_append_only_and_records_survivor_and_rejection(tmp_path: Path) -> None:
    artifact = broken_artifact()
    lineage = tmp_path / "lineage.jsonl"
    now = "2026-07-25T00:00:03+00:00"
    sandbox, error = semantic_mutation._load_sandbox(ROOT)
    assert sandbox is not None, error
    candidates = [
        semantic_mutation.Candidate(
            code="def add(a, b):\n    return a + b\n",
            source="unit",
            note="expected survivor",
        ),
        semantic_mutation.Candidate(
            code="def add(a, b):\n    return a - b\n",
            source="unit",
            note="expected rejection",
        ),
    ]
    parent_hash = semantic_mutation.artifact_hash(artifact)

    for index, candidate in enumerate(candidates):
        evaluation = semantic_mutation.evaluate_candidate(
            candidate,
            artifact,
            now=now,
            sandbox_module=sandbox,
            receipt_log=tmp_path / "sandbox_receipts.jsonl",
        )
        semantic_mutation.append_lineage(
            lineage,
            {
                "schema": semantic_mutation.SCHEMA,
                "kind": "lineage",
                "ts": now,
                "candidate_index": index,
                "parent_hash": parent_hash,
                "candidate_hash": evaluation["candidate_hash"],
                "verdict": evaluation["verdict"],
                "error": evaluation["error"],
            },
        )

    first = lineage.read_text(encoding="utf-8")
    semantic_mutation.append_lineage(
        lineage,
        {
            "schema": semantic_mutation.SCHEMA,
            "kind": "lineage",
            "ts": now,
            "candidate_index": 2,
            "parent_hash": parent_hash,
            "candidate_hash": "sha256:extra",
            "verdict": "rejected",
            "error": "extra",
        },
    )
    second = lineage.read_text(encoding="utf-8")
    records = read_jsonl(lineage)

    assert second.startswith(first)
    assert len(records) == 3
    assert {"survivor", "rejected"} <= {record["verdict"] for record in records}
    assert all(record["parent_hash"] == parent_hash for record in records)
