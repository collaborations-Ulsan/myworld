"""Tests for the model-residency arbiter.

The behaviours pinned here are the ones that cost real time on 2026-08-10: a
resident model must win over a nominally-better one, and an unreachable ollama
must never be reported as an empty machine.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_gpu_arbiter as A  # noqa: E402


@pytest.fixture
def box(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "STATE", tmp_path)
    monkeypatch.setattr(A, "LEASES", tmp_path / "leases.jsonl")
    monkeypatch.setenv("CLAUDE_CODE_MESSAGING_SOCKET", "/run/x/sess-abc.sock")
    return tmp_path


def _loaded(monkeypatch, *names):
    monkeypatch.setattr(A, "_get", lambda p, timeout=10.0: {
        "models": [{"name": n, "size_vram": 1_000_000_000} for n in names]})


def test_resident_model_wins_over_the_first_candidate(box, monkeypatch):
    """Today's actual bill: a 30B was named first while a 7B was already loaded."""
    _loaded(monkeypatch, "qwen2.5-coder:7b")
    out = A.cmd_advise(["qwen3:30b-a3b", "qwen2.5-coder:7b"], time.time())
    assert out["choose"] == "qwen2.5-coder:7b"
    assert out["reason"] == "already resident"


def test_same_family_counts_as_partial_reuse(box, monkeypatch):
    _loaded(monkeypatch, "qwen3:8b")
    out = A.cmd_advise(["llama3:70b", "qwen3:30b-a3b"], time.time())
    assert out["choose"] == "qwen3:30b-a3b"
    assert "same family" in out["reason"]


def test_nothing_resident_says_the_call_pays_a_load(box, monkeypatch):
    _loaded(monkeypatch)
    out = A.cmd_advise(["qwen3:8b"], time.time())
    assert out["choose"] == "qwen3:8b" and "pays a load" in out["reason"]


def test_unreachable_ollama_is_not_reported_as_an_empty_box(box, monkeypatch):
    """Silence is not a finding: a dead server and an idle server must differ."""
    def boom(p, timeout=10.0):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr(A, "_get", boom)

    st = A.cmd_status(time.time())
    assert st["resident"] == [] and st["ollama_error"]
    adv = A.cmd_advise(["qwen3:8b"], time.time())
    assert adv["ollama_error"] and "cannot see ollama" in adv["reason"]


def test_leases_expire_and_release_removes_them(box, monkeypatch):
    _loaded(monkeypatch, "bge-m3")
    now = time.time()
    A.cmd_acquire("bge-m3", 60.0, now)
    assert len(A._read_leases(now)) == 1
    assert A._read_leases(now + 120) == [], "an expired lease must not linger"

    A.cmd_acquire("bge-m3", 600.0, now)
    A.cmd_release("bge-m3", now)
    assert A._read_leases(now) == []


def test_reacquire_renews_rather_than_stacking(box, monkeypatch):
    _loaded(monkeypatch, "bge-m3")
    now = time.time()
    A.cmd_acquire("bge-m3", 60.0, now)
    A.cmd_acquire("bge-m3", 600.0, now)
    live = A._read_leases(now)
    assert len(live) == 1 and live[0]["expires_at"] == now + 600.0


def test_contention_is_reported_but_never_enforced(box, monkeypatch):
    """The arbiter has no host-side way to make a peer wait, so it must grant and
    say so rather than report a refusal it cannot back."""
    _loaded(monkeypatch, "qwen3:30b-a3b")
    now = time.time()
    A._append({"holder": "session:other.sock", "model": "qwen3:30b-a3b",
               "acquired_at": now, "expires_at": now + 600, "released": False})
    out = A.cmd_acquire("bge-m3", 60.0, now)
    assert out["granted"] is True
    assert out["contention"] and out["contention"][0]["holder"] == "session:other.sock"
    assert A.cmd_status(now)["enforcement"] == "advisory"


def test_holder_prefers_the_session_socket_over_the_pid(box, monkeypatch):
    assert A._holder() == "session:sess-abc.sock"
    monkeypatch.delenv("CLAUDE_CODE_MESSAGING_SOCKET")
    assert A._holder().startswith("pid:")
