"""Tests for the ideation absorption organ.

The important one is `test_receipt_satisfies_M0_judgment_rule`: it encodes the
single-event judgment rule from docs/AIOS_MINIMAL_OPERATION_2026-08-09.md §3 as
an executable assertion, so the rule cannot quietly drift away from the code
that is supposed to satisfy it.

No network, no model: harvesting and distillation are stubbed. What is under
test is the ORACLE and the LEDGER, which are exactly the parts that must not
depend on a model being available.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_ideation as I  # noqa: E402

@pytest.fixture(autouse=True)
def _no_courtesy_delay(monkeypatch):
    """Production politeness to arXiv/GitHub must not be paid by the test suite."""
    monkeypatch.setattr(I, "COURTESY", {k: 0.0 for k in I.COURTESY})


SOURCE_TEXT = (
    "We introduce a policy layer that intercepts every tool call an agent "
    "emits and evaluates it against a declarative contract before execution. "
    "Denied calls never reach the runtime, and each decision is recorded."
)


def _item():
    return I._item("arxiv", "http://example.invalid/abs/1", "A Policy Layer",
                   SOURCE_TEXT)


def _near(sim=0.1):
    return {"method": "lexical:trigram-jaccard", "similarity": sim,
            "path": "docs/X.md", "title": "X"}


# --- the oracle -----------------------------------------------------------

def test_verbatim_evidence_passes():
    prop = {"claim": "Tool calls can be intercepted and denied before they run.",
            "falsifier": "run an agent with a deny-all contract; a call reaches the runtime",
            "evidence": "intercepts every tool call an agent emits and evaluates it"}
    v = I.verify(_item(), prop, _near(), 0.9)
    assert v["pass"] is True
    # NOT "novel": with dedup uncalibrated the oracle can only vouch that the
    # quote is real and a falsifier is present.
    assert v["verdict"] == "grounded"
    assert v["novelty_assessed"] is False


def test_paraphrase_is_rejected():
    """The whole point: a plausible restatement must not survive."""
    prop = {"claim": "Tool calls can be intercepted before execution.",
            "falsifier": "run an agent with a deny-all contract and watch the runtime",
            # same meaning, different words -> not in the source
            "evidence": "catches each tool invocation the agent produces and checks it"}
    v = I.verify(_item(), prop, _near(), 0.9)
    assert v["pass"] is False
    assert "evidence_not_verbatim_in_source" in v["reasons"]


def test_whitespace_and_case_do_not_break_grounding():
    prop = {"claim": "Denied calls never reach the runtime.",
            "falsifier": "instrument the runtime and count denied calls that arrive",
            "evidence": "DENIED CALLS   never\n  reach the runtime"}
    v = I.verify(_item(), prop, _near(), 0.9)
    assert v["pass"] is True


def test_missing_falsifier_is_rejected():
    prop = {"claim": "Tool calls can be intercepted.",
            "falsifier": "no", "evidence": "intercepts every tool call an agent emits"}
    v = I.verify(_item(), prop, _near(), 0.9)
    assert v["pass"] is False
    assert any(r.startswith("falsifier") for r in v["reasons"])


def test_overlong_claim_is_rejected():
    prop = {"claim": "x" * (I.MAX_CLAIM + 1),
            "falsifier": "run the thing and see whether it does the thing",
            "evidence": "intercepts every tool call an agent emits and evaluates it"}
    v = I.verify(_item(), prop, _near(), 0.9)
    assert v["pass"] is False
    assert any(r.startswith("claim_too_long") for r in v["reasons"])


def test_similar_claim_is_filed_as_rename_when_dedup_is_trusted():
    prop = {"claim": "Tool calls can be intercepted and denied before they run.",
            "falsifier": "run an agent with a deny-all contract; a call reaches the runtime",
            "evidence": "intercepts every tool call an agent emits and evaluates it"}
    v = I.verify(_item(), prop, _near(sim=0.95), 0.9, dedup_trusted=True)
    assert v["pass"] is True          # it is well-formed...
    assert v["verdict"] == "rename"   # ...but it is not news to us


def test_untrusted_dedup_never_claims_novelty():
    """The rule the 2026-08-10 calibration forced, pinned so it cannot drift.

    Three statistics were measured against a positive and a negative control
    (J = 0.5167 / 0.5673 / 0.4476) and none separated. Until one does, no row
    may be labelled `novel` — neither the near ones nor the far ones.
    """
    prop = {"claim": "Tool calls can be intercepted and denied before they run.",
            "falsifier": "run an agent with a deny-all contract; a call reaches the runtime",
            "evidence": "intercepts every tool call an agent emits and evaluates it"}
    for sim in (0.01, 0.5, 0.95, 99.0):
        v = I.verify(_item(), prop, _near(sim=sim), 0.9, dedup_trusted=False)
        assert v["verdict"] == "grounded", f"sim={sim} leaked a novelty claim"
        assert v["dedup_trusted"] is False


def test_unseparated_calibration_is_not_trusted(tmp_path, monkeypatch):
    """A threshold from an unseparated calibration is a number, not a boundary."""
    monkeypatch.setattr(I, "ASSET", tmp_path)
    (tmp_path / "calibration.json").write_text(json.dumps(
        {"threshold": 3.87, "separated": False, "youden_j": 0.4476}))
    thr, trusted = I.load_threshold()
    assert thr == 3.87 and trusted is False
    (tmp_path / "calibration.json").write_text(json.dumps(
        {"threshold": 3.87, "separated": True, "youden_j": 0.91}))
    assert I.load_threshold() == (3.87, True)


# --- the ledger -----------------------------------------------------------

def test_append_changes_the_root(tmp_path):
    p = tmp_path / "l.jsonl"
    before = I.ledger_root(p)
    I._append(p, {"a": 1})
    after = I.ledger_root(p)
    assert before != after


def test_reordering_history_changes_the_root(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    I._append(a, {"x": 1}); I._append(a, {"y": 2})
    I._append(b, {"y": 2}); I._append(b, {"x": 1})
    # position-salted leaves: same events in a different order is a different
    # history, and the root must say so
    assert I.ledger_root(a) != I.ledger_root(b)


# --- the M0 judgment rule, as executable spec ------------------------------

@pytest.mark.parametrize("grounded", [True, False])
def test_receipt_satisfies_M0_judgment_rule(tmp_path, monkeypatch, grounded):
    """One cycle must emit a receipt that passes §3 of the minimal-operation doc:

        model_consulted=false AND invoked_by=host AND verifier != executor
        AND outcome in {committed, reverted} AND root_before != root_after

    Run twice: once where the distiller is honest (committed) and once where it
    invents its evidence (reverted). Both must produce a conforming receipt —
    a cycle that only emits receipts when it succeeds is not a verified cycle.
    """
    monkeypatch.setattr(I, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(I, "RECEIPTS", tmp_path / "receipts.jsonl")
    monkeypatch.setattr(I, "ASSET", tmp_path)
    monkeypatch.setattr(I, "STATE", tmp_path / "state")
    monkeypatch.setattr(I, "HARVESTERS", {"arxiv": lambda q, n: [_item()]})
    monkeypatch.setattr(I, "load_corpus", lambda *a, **k: [
        {"path": "docs/X.md", "title": "X", "gist": "unrelated text", "offset": 0}])
    monkeypatch.setattr(I, "corpus_vectors", lambda c: None)   # lexical path
    monkeypatch.setattr(I, "distill", lambda item, model=None: {
        "claim": "Tool calls can be intercepted and denied before they run.",
        "falsifier": "run an agent with a deny-all contract; a call reaches the runtime",
        "evidence": ("intercepts every tool call an agent emits" if grounded
                     else "a sentence that is nowhere in the fetched source at all"),
    })

    res = I.run_cycle(["arxiv"], ["activation"], 5, 1, "0.9", "stub",
                      verbose=False)
    assert len(res["settled"]) == 1

    receipts = [json.loads(l) for l in (tmp_path / "receipts.jsonl").open()]
    assert len(receipts) == 1
    r = receipts[0]
    assert r["sense"]["model_consulted"] is False
    assert r["act"]["invoked_by"] == "host"
    assert r["act"]["model_offered_choice"] is False
    assert r["verify"]["verifier_identity"] != r["act"]["operator"]
    assert r["settle"]["outcome"] in {"committed", "reverted"}
    assert r["settle"]["root_before"] != r["settle"]["root_after"]
    assert r["settle"]["outcome"] == ("committed" if grounded else "reverted")


def test_source_failure_is_not_reported_as_empty(monkeypatch, tmp_path):
    """Silence is not a finding: a source that raised must be visible."""
    monkeypatch.setattr(I, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(I, "RECEIPTS", tmp_path / "receipts.jsonl")

    def boom(q, n):
        raise OSError("network down")

    monkeypatch.setattr(I, "HARVESTERS", {"arxiv": boom})
    res = I.run_cycle(["arxiv"], ["activation"], 5, 1, "0.9", "stub",
                      verbose=False)
    assert res["sense"]["source_errors"], "a failed source must be recorded"
    assert res["sense"]["fresh"] == 0


def test_numpy_and_stdlib_peak_z_agree():
    """The numpy path is an optimisation, so it must not be a second algorithm.

    A bare wheel with no numpy takes the pure-Python branch; if the two branches
    disagreed, the same claim would be judged `novel` on one install and
    `rename` on another.
    """
    vecs = [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0], [0.0, 1.0, 0.0],
            [0.2, 0.2, 0.9], [-1.0, 0.0, 0.0]]
    claim = [0.95, 0.05, 0.1]
    slow = I._peak_z(claim, vecs, None)
    fast = I._peak_z(claim, vecs, I._as_matrix(vecs))
    assert fast[2] == slow[2], "argmax differs"
    assert abs(fast[0] - slow[0]) < 1e-5, "max cosine differs"
    assert abs(fast[1] - slow[1]) < 1e-4, "z-score differs"


def test_batch_embed_falls_back_without_recursing(monkeypatch):
    """A failing batch must degrade to serial, not re-enter the batch path.

    Regression: the fallback used to call embed() with a 32-item sub-batch,
    which is still above the batch threshold, so it failed and recursed until
    RecursionError. It looked like a slow calibration, not a crash.
    """
    seen = {"batch": 0, "single": 0}

    def fake(path, body, timeout=0):
        if isinstance(body.get("input"), list):
            seen["batch"] += 1
            raise OSError("batch endpoint unavailable")
        seen["single"] += 1
        return {"embeddings": [[1.0, 0.0]]}

    monkeypatch.setattr(I, "_ollama", fake)
    out = I.embed([f"text {i}" for i in range(20)])
    assert out is not None and len(out) == 20
    assert seen["single"] == 20, "should have fallen back to one call per text"
    assert seen["batch"] == 1, "should not have retried the batch path"


def test_embed_marks_unembeddable_inputs(monkeypatch):
    """A NaN-defect input becomes a zero vector AND is counted — never silent.

    Zero vectors are the safe direction: cosine 0 against everything, so such a
    passage can only be missed as a duplicate, never invented as one.
    """
    calls = {"n": 0}

    def fake(path, body, timeout=0):
        calls["n"] += 1
        if "bad" in json.dumps(body):
            raise I.urllib.error.HTTPError(
                "u", 500, "err", {},
                __import__("io").BytesIO(b'{"error":"json: unsupported value: NaN"}'))
        return {"embeddings": [[1.0, 0.0, 0.0]]}

    monkeypatch.setattr(I, "_ollama", fake)
    out = I.embed(["good one", "a bad one", "good two"])
    assert out is not None
    assert out[1] == [0.0, 0.0, 0.0]
    assert len(I.EMBED_FAILED) == 1 and I.EMBED_FAILED[0]["index"] == 1
    assert I.EMBED_ERROR and "unembeddable" in I.EMBED_ERROR
