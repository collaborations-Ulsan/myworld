"""Tests for claimcheck — the grounding oracle pointed at our own documents.

These pin the two things that decide whether the checker is worth running: what
counts as a claim (too loose and its output is noise nobody reads), and what
counts as evidence (too loose and it grounds everything, which is the same as
grounding nothing).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_claimcheck as C  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "ROOT", tmp_path)
    monkeypatch.setattr(C, "IDEATION_LEDGER", tmp_path / "ideation" / "ledger.jsonl")
    (tmp_path / "docs").mkdir()
    return tmp_path


def _write(repo, rel, text):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# --- what counts as a claim ------------------------------------------------

def test_arxiv_ids_and_dois_are_not_claims():
    """The checker's own first run flagged 369 items, overwhelmingly arXiv ids.

    A precise-looking decimal that asserts nothing must not be reported, or the
    real findings drown and the tool gets ignored.
    """
    claims = C.extract_claims("see arXiv 2406.12775 and 2511.03690, DOI 10.1023")
    assert claims == []


def test_years_and_versions_are_not_claims():
    assert C.extract_claims("in 2026 we shipped v0.3.0") == []


def test_effect_sizes_p_values_ratios_and_n_are_claims():
    kinds = {c["kind"] for c in C.extract_claims(
        "gain +8.54pp, p=0.0592, used 0/32 times, n=82, score 0.4476")}
    assert kinds == {"effect_pp", "p_value", "ratio", "n_count", "decimal4"}


def test_code_blocks_are_not_scanned():
    """A doc quoting its own receipt is not making a prose claim about it."""
    assert C.extract_claims("```\nvalue = 0.4476\n```") == []
    assert C.extract_claims("inline `0.4476` only") == []


def test_normalisation_folds_notation_but_never_the_sign():
    """Unicode minus must fold to ASCII so prose and JSON compare, but a sign is
    a claim: −6.25pp and +6.25pp are opposite findings and must not match."""
    assert C._norm_num("−6.25pp") == "-6.25"
    assert C._norm_num("+6.25 pp") == "6.25"
    assert C._norm_num("−6.25pp") != C._norm_num("+6.25pp")
    assert C._norm_num("p=0.0592") == C._norm_num("0.0592") == "0.0592"


def test_our_own_key_ratios_survive_the_noise_filter():
    """Regression: a date heuristic once swallowed 0/32, 2/6 and 0/96."""
    got = {c["norm"] for c in C.extract_claims(
        "used 0/32 times, 2/6 organs act, 0/96 blocks")}
    assert {"0/32", "2/6", "0/96"} <= got


# --- what counts as evidence -----------------------------------------------

def test_number_in_cited_artifact_is_grounded(repo):
    _write(repo, "experiments/r.json", json.dumps({"delta_pp": 8.54}))
    doc = _write(repo, "docs/d.md",
                 "The gain was +8.54pp — see `experiments/r.json`.")
    r = C.check_doc(doc)
    assert r["claims"] == 1 and r["grounded"] == 1 and r["unresolved"] == []


def test_number_absent_from_cited_artifact_is_unresolved(repo):
    _write(repo, "experiments/r.json", json.dumps({"delta_pp": 8.54}))
    doc = _write(repo, "docs/d.md",
                 "The gain was +12.90pp — see `experiments/r.json`.")
    r = C.check_doc(doc)
    assert [c["norm"] for c in r["unresolved"]] == ["12.90"]


def test_uncited_document_grounds_nothing(repo):
    doc = _write(repo, "docs/d.md", "We measured +20.3pp.")
    r = C.check_doc(doc)
    assert r["citations"] == [] and r["grounded"] == 0


# --- where the two organs meet ---------------------------------------------

def test_arxiv_reference_counts_only_once_absorbed(repo):
    doc = _write(repo, "docs/d.md",
                 "Back-patching recovered 0.570 of failures (arXiv:2406.12775).")
    before = C.check_doc(doc)
    assert before["external_refs_unabsorbed"] == ["2406.12775"]
    assert before["unresolved"], "an unabsorbed paper must not ground a number"

    _write(repo, "ideation/ledger.jsonl", json.dumps({
        "source": {"url": "https://arxiv.org/abs/2406.12775"},
        "claim": "back-patching recovers failures",
        "evidence": "recovers up to 0.570 of the failing cases",
        "falsifier": "re-run without back-patching",
    }) + "\n")
    after = C.check_doc(doc)
    assert after["external_refs_absorbed"] == ["2406.12775"]
    assert after["external_refs_unabsorbed"] == []
    assert after["unresolved"] == []


def test_absorbing_an_abstract_does_not_ground_a_body_number(repo):
    """Honest limit, pinned so it is not quietly overstated later.

    The ideation ledger holds what the abstract said. A number that lives in the
    paper's body is still unverifiable from here, and the checker must keep
    saying so rather than counting the paper as covered.
    """
    _write(repo, "ideation/ledger.jsonl", json.dumps({
        "source": {"url": "https://arxiv.org/abs/2606.26300"},
        "claim": "a static verifier is incomplete",
        "evidence": "no fixed verifier is complete",
        "falsifier": "exhibit a complete fixed verifier",
    }) + "\n")
    doc = _write(repo, "docs/d.md",
                 "The monitoring loop gave +20.3pp clean (arXiv:2606.26300).")
    r = C.check_doc(doc)
    assert r["external_refs_absorbed"] == ["2606.26300"]
    assert [c["norm"] for c in r["unresolved"]] == ["20.3"]
