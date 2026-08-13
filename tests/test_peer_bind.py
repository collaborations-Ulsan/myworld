"""Tests for binding durable identities to ephemeral sessions.

The behaviour that matters is refusal to believe a record about itself. A
session file carries its own `status`, and trusting it is the same mistake as
trusting a lease holder's word about being alive — which this repository
already made once, in the arc lease.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_peer_bind as P  # noqa: E402


@pytest.fixture
def fleet(tmp_path, monkeypatch):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    ws = tmp_path / "ws"
    (ws / "quantum").mkdir(parents=True)
    (ws / "myworld").mkdir(parents=True)
    monkeypatch.setattr(P, "SESSIONS", sessions)
    monkeypatch.setattr(P, "WORKSPACE_ROOT", ws)
    return sessions, ws


def write_session(sessions, ws, *, name, repo, pid, sock=True, status="idle"):
    s = sessions / f"{pid}.json"
    sock_path = sessions / f"{pid}.sock"
    if sock:
        sock_path.write_text("")
    s.write_text(json.dumps({
        "name": name, "nameSource": "derived", "sessionId": f"sid-{pid}",
        "cwd": str(ws / repo), "pid": pid, "kind": "interactive",
        "messagingSocketPath": str(sock_path), "status": status,
        "updatedAt": "1786622442535",
    }))
    return s


def test_a_dead_process_is_gone_however_the_record_describes_itself(fleet):
    """The record says idle. The process does not exist. The record loses."""
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-3e", repo="quantum",
                  pid=999_999, status="idle")
    out = P.resolve("claude@quantum", None)
    assert out["address"] == []
    assert out["gone"][0]["claimed_status"] == "idle"


def test_a_live_process_without_its_socket_is_not_reachable(fleet):
    """Alive is not the same as addressable — the inbox has to exist."""
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-fd", repo="quantum",
                  pid=os.getpid(), sock=False)
    assert P.resolve("claude@quantum", None)["address"] == []


def test_an_identity_resolves_to_todays_session_not_yesterdays_name(fleet):
    """The whole point: the advisor is addressable again after its name died."""
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-3e", repo="quantum", pid=999_999)
    write_session(sessions, ws, name="quantum-fd", repo="quantum",
                  pid=os.getpid())
    out = P.resolve("claude@quantum", None)
    assert out["address"] == ["quantum-fd"]
    assert [g["name"] for g in out["gone"]] == ["quantum-3e"]


def test_two_live_sessions_in_one_workspace_are_reported_ambiguous(fleet):
    """An agent_id that picks two contexts has not picked one, and silently
    choosing the first would send work to whichever happened to sort first."""
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-fd", repo="quantum",
                  pid=os.getpid())
    write_session(sessions, ws, name="quantum-d4", repo="quantum",
                  pid=os.getppid())
    out = P.resolve("claude@quantum", None)
    assert out["ambiguous"] is True and len(out["address"]) == 2


def test_resolve_exits_nonzero_when_nobody_answers(fleet):
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-3e", repo="quantum", pid=999_999)
    assert P.main(["resolve", "--agent", "claude@quantum", "--json"]) == 1
    write_session(sessions, ws, name="quantum-fd", repo="quantum",
                  pid=os.getpid())
    assert P.main(["resolve", "--agent", "claude@quantum", "--json"]) == 0


def test_discover_counts_derived_names(fleet):
    """If every name is derived, none of them is an identity — the count is the
    evidence for that claim rather than an assertion about it."""
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-fd", repo="quantum",
                  pid=os.getpid())
    write_session(sessions, ws, name="myworld-f5", repo="myworld",
                  pid=os.getppid())
    out = P.discover()
    assert out["derived_names"] == 2
    assert set(out["by_repo"]) == {"quantum", "myworld"}


def test_sessions_outside_the_workspace_are_not_attributed_to_a_repo(fleet):
    sessions, ws = fleet
    s = write_session(sessions, ws, name="stray", repo="quantum",
                      pid=os.getpid())
    rec = json.loads(s.read_text())
    rec["cwd"] = "/tmp/somewhere-else"
    s.write_text(json.dumps(rec))
    assert P.resolve(None, "quantum")["address"] == []
    assert "(outside workspace)" in P.discover()["by_repo"]


def test_an_unreadable_record_is_surfaced_not_skipped(fleet):
    """Silence is not a finding: a corrupt record must be reported, because a
    directory that half-parses looks exactly like a smaller fleet."""
    sessions, _ = fleet
    (sessions / "broken.json").write_text("{not json")
    assert any("broken.json" in p for p in P.discover()["problems"])


def test_discover_declares_what_it_cannot_see(fleet):
    """Measured 2026-08-13: 34 peers via ListAgents, 19 in the disk registry.
    Reporting the 19 as the fleet would be a silent 44% under-count, so the
    blind spot has to travel with the answer."""
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-fd", repo="quantum", pid=os.getpid())
    cov = P.discover()["coverage"]
    assert "Remote Control" in " ".join(cov["blind_to"])
    assert "cloud" in " ".join(cov["blind_to"]).lower()
    assert cov["authoritative_source_for_those"]


def test_derived_names_collide_within_a_workspace(fleet):
    """The naming failure, as data: two live sessions in one workspace differ
    only by a random suffix, so neither name says which is which."""
    sessions, ws = fleet
    write_session(sessions, ws, name="quantum-fd", repo="quantum", pid=os.getpid())
    write_session(sessions, ws, name="quantum-d4", repo="quantum", pid=os.getppid())
    out = P.resolve("claude@quantum", None)
    assert out["ambiguous"] is True
    assert sorted(out["address"]) == ["quantum-d4", "quantum-fd"]
