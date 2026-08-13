"""Tests for the diagnostic partition.

The property under test is that this is not a panel. Verdicts are typed answers
to different questions, so the module must refuse the affordances that would let
them be read as agreement.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_diagnose as D  # noqa: E402


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "LEDGER", tmp_path / "diagnoses.jsonl")


def test_a_verdict_without_a_reason_is_refused():
    """A bare verdict is a vote, and votes are what this module exists to avoid."""
    with pytest.raises(ValueError, match="vote"):
        D.record("c1", "quantum", "not_mine", "   ")


def test_an_unknown_organ_is_refused():
    with pytest.raises(ValueError, match="unknown organ"):
        D.record("c1", "astrology", "mine", "because")


def test_every_organ_can_answer_no():
    """A question an organ cannot fail is not a diagnostic — each entry must say
    when it declines, or it would claim everything."""
    for name, o in D.ORGANS.items():
        assert o["answers_no_when"].strip(), name
        assert o["asks"].endswith("?"), name


def test_one_claimant_is_a_diagnosis():
    D.record("c", "quantum", "not_mine", "acyclic chain always extends")
    D.record("c", "descentnet", "not_mine", "gluable; the section exists")
    D.record("c", "universe", "mine", "depth-graded budget cliff")
    D.record("c", "goen", "not_mine", "identity transport")
    D.record("c", "computation", "not_mine", "oracle is not code")
    p = D.partition("c")
    assert p["claimed_by"] == ["universe"] and "a diagnosis" in p["reading"]


def test_two_claimants_mean_the_diagnosis_is_not_sharp():
    """Today's real result: universe claimed it and goen claimed it partly."""
    D.record("c", "universe", "mine", "depth grading")
    D.record("c", "goen", "partly", "identity transport only in the resume class")
    for o in ("quantum", "descentnet", "computation"):
        D.record("c", o, "not_mine", "not my register")
    p = D.partition("c")
    assert set(p["claimed_by"]) == {"universe", "goen"}
    assert "not yet sharp" in p["reading"]


def test_nobody_claiming_it_is_itself_a_finding():
    for o in D.ORGANS:
        D.record("c", o, "not_mine", "not my register")
    assert "a finding" in D.partition("c")["reading"]


def test_an_unasked_organ_makes_the_partition_incomplete():
    D.record("c", "universe", "mine", "depth grading")
    assert "incomplete" in D.partition("c")["reading"]


def test_the_last_verdict_per_organ_wins():
    D.record("c", "quantum", "mine", "first read")
    D.record("c", "quantum", "not_mine", "revised after Vorob'ev")
    v = [x for x in D.partition("c")["verdicts"] if x["organ"] == "quantum"]
    assert len(v) == 1 and v[0]["verdict"] == "not_mine"


def test_agreement_is_never_reported_as_strength():
    """n_eff 1.75 across 16 substrates: counting these as confirmations would be
    the exact error the measurement forbids."""
    for o in D.ORGANS:
        D.record("c", o, "mine", "claims it")
    p = D.partition("c")
    assert "not_a_panel" in p
    blob = json.dumps(p).lower()
    for word in ("consensus", "confirmed", "unanimous", "majority"):
        assert word not in blob, word
