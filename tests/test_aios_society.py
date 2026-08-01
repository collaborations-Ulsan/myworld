#!/usr/bin/env python3
"""Society Kernel tests — one test per red-team invariant (INV-1..INV-6) plus
the projection/integrity basics.

    /home/user/miniconda3/bin/python3 -m pytest -q tests/test_aios_society.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_society as soc  # noqa: E402

T0 = 1_800_000_000.0


@pytest.fixture()
def arcs(tmp_path: Path) -> Path:
    return tmp_path / "arcs"


@pytest.fixture()
def locks(tmp_path: Path) -> Path:
    return tmp_path / "locks"


def _open(arcs: Path, goal="ship the thing", constraints=("never touch tests/",)):
    r = soc.open_arc(goal, agent="a@one", now=T0, constraints=list(constraints),
                     oracle_cmd="pytest -q", arcs_dir=arcs)
    assert r["ok"]
    return r["arc_id"]


# --- basics ---------------------------------------------------------------

def test_open_and_project(arcs: Path):
    arc = _open(arcs)
    st = soc.project(soc.read_events(arc, arcs), now=T0)
    assert st["exists"] and st["status"] == "open"
    assert st["goal"] == "ship the thing"
    assert st["constraints"] == ["never touch tests/"]
    assert st["owner"] is None and st["tip_seq"] == 0


def test_missing_arc_is_not_an_exception(arcs: Path):
    assert soc.resume_pack("arc-doesnotexist", now=T0, arcs_dir=arcs)["ok"] is False
    assert soc.claim("arc-nope", agent="x", now=T0, arcs_dir=arcs)["ok"] is False


def test_append_only_history_and_root_changes(arcs: Path):
    arc = _open(arcs)
    r1 = soc.arc_root(arc, arcs_dir=arcs)
    soc.claim(arc, agent="a@one", now=T0, arcs_dir=arcs, locks_dir=arcs / "l")
    r2 = soc.arc_root(arc, arcs_dir=arcs)
    assert r1 != r2
    events = soc.read_events(arc, arcs)
    assert [e["seq"] for e in events] == list(range(len(events)))


# --- INV-3 single writer, no split brain ----------------------------------

def test_inv3_live_lease_blocks_a_second_writer(arcs: Path, locks: Path):
    arc = _open(arcs)
    ok = soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs,
                   locks_dir=locks)
    assert ok["ok"] and ok["owner"] == "a@one"
    denied = soc.claim(arc, agent="b@two", now=T0 + 1, ttl=600, arcs_dir=arcs,
                       locks_dir=locks)
    assert denied["ok"] is False and denied["reason"] == "held"
    st = soc.project(soc.read_events(arc, arcs), now=T0 + 1)
    assert st["owner"] == "a@one"          # no fork, no second writer
    assert st["contested"] == 1            # the attempt is on the record


def test_inv3_expired_lease_is_reclaimable(arcs: Path, locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=10, arcs_dir=arcs, locks_dir=locks)
    late = soc.claim(arc, agent="b@two", now=T0 + 999, ttl=600, arcs_dir=arcs,
                     locks_dir=locks)
    assert late["ok"] and late["prev_owner"] == "a@one"


def test_inv3_dead_holder_frees_the_arc_without_waiting_for_ttl(arcs: Path,
                                                                locks: Path):
    """Liveness is DERIVED (council/presence.py discipline): an unexpired lease
    whose pid is gone stops blocking takeover — fast MTTR. The two lease views
    are distinct: the write view (TTL) still names the owner, the takeover view
    (TTL AND liveness) does not hold."""
    arc = _open(arcs)
    soc.append_event(arc, {"kind": "claimed", "agent": "ghost", "substrate": "x",
                           "pid": 999_999_999, "owner_host": os.uname().nodename,
                           "lease_until": T0 + 10_000, "prev_owner": None},
                     now=T0, arcs_dir=arcs)
    st = soc.project(soc.read_events(arc, arcs), now=T0 + 1)
    assert st["owner"] == "ghost"
    assert st["lease_live"] is True          # TTL has not expired
    assert st["holder_present"] is False     # but nobody is home
    took = soc.claim(arc, agent="b@two", now=T0 + 2, arcs_dir=arcs,
                     locks_dir=locks)
    assert took["ok"] and took["prev_owner"] == "ghost"


def test_agent_writes_progress_across_its_own_process_deaths(arcs: Path,
                                                             locks: Path):
    """An agent is not a process. With a live TTL the owning agent may append
    from any process — otherwise a CLI agent could never record its own work."""
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=600, pid=999_999_999,
              arcs_dir=arcs, locks_dir=locks)
    assert soc.note(arc, "written from a different process", agent="a@one",
                    now=T0 + 1, arcs_dir=arcs)["ok"]


# --- INV-5 continuous progress; only the holder writes --------------------

def test_inv5_progress_appends_and_nonholder_is_refused(arcs: Path, locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    assert soc.note(arc, "step 1 done", agent="a@one", now=T0 + 1,
                    evidence=["commit:abc123"], arcs_dir=arcs)["ok"]
    bad = soc.note(arc, "I also did things", agent="b@two", now=T0 + 2,
                   arcs_dir=arcs)
    assert bad["ok"] is False and bad["reason"] == "not the lease holder"
    st = soc.project(soc.read_events(arc, arcs), now=T0 + 2)
    assert [p["text"] for p in st["progress"]] == ["step 1 done"]
    assert st["progress"][0]["evidence"] == ["commit:abc123"]


# --- INV-1 freshness ------------------------------------------------------

def test_inv1_stale_pack_is_refused_then_accepted_after_resync(arcs: Path,
                                                               locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    pack = soc.resume_pack(arc, now=T0 + 1, arcs_dir=arcs)
    soc.note(arc, "world moved on", agent="a@one", now=T0 + 2, arcs_dir=arcs)
    soc.offer_handoff(arc, agent="a@one", now=T0 + 3, reason="dying",
                      next_step="continue at step 2", arcs_dir=arcs)

    stale = soc.resume(arc, agent="b@two", pack_tip_seq=pack["tip_seq"],
                       now=T0 + 4, arcs_dir=arcs, locks_dir=locks)
    assert stale["ok"] is False and stale["reason"] == "stale_pack"
    assert stale["freshness"]["missed_events"] == 2

    fresh = soc.resume_pack(arc, now=T0 + 5, arcs_dir=arcs)
    good = soc.resume(arc, agent="b@two", pack_tip_seq=fresh["tip_seq"],
                      now=T0 + 6, arcs_dir=arcs, locks_dir=locks)
    assert good["ok"] and good["owner"] == "b@two"


def test_inv1_pack_carries_causal_position_and_root(arcs: Path, locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    pack = soc.resume_pack(arc, now=T0 + 1, arcs_dir=arcs)
    assert pack["tip_seq"] == 1
    assert pack["tip_hash"].startswith("sha256:")
    assert pack["root"] == soc.arc_root(arc, arcs_dir=arcs)
    assert pack["goal"] and pack["constraints"] == ["never touch tests/"]


# --- INV-4 ownership always attributable ----------------------------------

def test_inv4_every_event_names_its_agent_and_owner_transfers(arcs: Path,
                                                              locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    soc.note(arc, "did a thing", agent="a@one", now=T0 + 1, arcs_dir=arcs)
    soc.offer_handoff(arc, agent="a@one", now=T0 + 2, reason="context death",
                      next_step="verify the fix", arcs_dir=arcs)
    st = soc.project(soc.read_events(arc, arcs), now=T0 + 3)
    assert st["owner"] is None and st["handoff"]["next_step"] == "verify the fix"

    pack = soc.resume_pack(arc, now=T0 + 3, arcs_dir=arcs)
    soc.resume(arc, agent="b@two", pack_tip_seq=pack["tip_seq"], now=T0 + 4,
               arcs_dir=arcs, locks_dir=locks)
    events = soc.read_events(arc, arcs)
    assert all(e.get("agent") for e in events)
    transfer = [e for e in events if e["kind"] == "claimed"][-1]
    assert transfer["prev_owner"] is None and transfer["agent"] == "b@two"
    assert soc.verify_arc(arc, arcs_dir=arcs)["ok"]


# --- INV-6 verification never blocks availability -------------------------

def test_inv6_verdict_lands_after_resume_and_flags_the_arc(arcs: Path,
                                                           locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=1, arcs_dir=arcs, locks_dir=locks)
    pack = soc.resume_pack(arc, now=T0 + 10, arcs_dir=arcs)
    took = soc.resume(arc, agent="b@two", pack_tip_seq=pack["tip_seq"],
                      now=T0 + 11, arcs_dir=arcs, locks_dir=locks)
    assert took["ok"]                      # resumed with NO verifier involved
    v = soc.record_verdict(arc, agent="verifier@sep", verdict="drifted",
                           now=T0 + 30, findings=["ignored constraint"],
                           arcs_dir=arcs)
    assert v["ok"]
    pack2 = soc.resume_pack(arc, now=T0 + 31, arcs_dir=arcs)
    assert pack2["open_verdicts"] and pack2["open_verdicts"][0]["verdict"] == "drifted"
    assert soc.record_verdict(arc, agent="v", verdict="nonsense", now=T0 + 32,
                              arcs_dir=arcs)["ok"] is False


# --- availability surface (G3) --------------------------------------------

def test_orphans_lists_only_unheld_open_arcs(arcs: Path, locks: Path):
    held = _open(arcs, goal="held arc")
    dead = _open(arcs, goal="dead worker arc")
    done = _open(arcs, goal="finished arc")
    soc.claim(held, agent="a@one", now=T0, ttl=10_000, arcs_dir=arcs,
              locks_dir=locks)
    soc.claim(dead, agent="c@three", now=T0, ttl=5, arcs_dir=arcs,
              locks_dir=locks)
    soc.claim(done, agent="d@four", now=T0, ttl=10_000, arcs_dir=arcs,
              locks_dir=locks)
    soc.close_arc(done, agent="d@four", status="done", now=T0 + 1,
                  evidence=["oracle:pass"], arcs_dir=arcs)

    ids = {a["arc_id"] for a in soc.orphans(now=T0 + 100, arcs_dir=arcs)}
    assert ids == {dead}


def test_close_is_terminal(arcs: Path, locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    assert soc.close_arc(arc, agent="a@one", status="done", now=T0 + 1,
                         arcs_dir=arcs)["ok"]
    assert soc.close_arc(arc, agent="a@one", status="done", now=T0 + 2,
                         arcs_dir=arcs)["ok"] is False
    assert soc.claim(arc, agent="b@two", now=T0 + 3, arcs_dir=arcs,
                     locks_dir=locks)["ok"] is False
    assert soc.close_arc(arc, agent="a", status="maybe", now=T0 + 4,
                         arcs_dir=arcs)["ok"] is False


# --- integrity ------------------------------------------------------------

def test_verify_catches_tampering(arcs: Path, locks: Path):
    arc = _open(arcs)
    soc.claim(arc, agent="a@one", now=T0, ttl=600, arcs_dir=arcs, locks_dir=locks)
    soc.note(arc, "real work", agent="a@one", now=T0 + 1, arcs_dir=arcs)
    assert soc.verify_arc(arc, arcs_dir=arcs)["ok"]

    p = soc.arc_path(arc, arcs)
    lines = p.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[-1]); rec["seq"] = 99            # rewrite history
    lines[-1] = json.dumps(rec, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bad = soc.verify_arc(arc, arcs_dir=arcs)
    assert bad["ok"] is False and any("seq" in s for s in bad["problems"])


def test_unknown_event_kind_refused(arcs: Path):
    arc = _open(arcs)
    with pytest.raises(ValueError):
        soc.append_event(arc, {"kind": "mutiny", "agent": "x"}, now=T0,
                         arcs_dir=arcs)


# --- CLI end-to-end (a real second process, the actual society case) ------

def test_cli_roundtrip_second_process_resumes(tmp_path: Path):
    ad = str(tmp_path / "arcs")
    py = sys.executable

    def run(*args):
        r = subprocess.run([py, str(ROOT / "scripts" / "aios_society.py"),
                            "--arcs-dir", ad, *args],
                           capture_output=True, text=True, timeout=60)
        return r.returncode, json.loads(r.stdout or "{}")

    rc, out = run("open", "--goal", "cross-process arc", "--agent", "a@one",
                  "--constraint", "no network")
    assert rc == 0 and out["ok"]
    arc = out["arc_id"]

    # A long lease: the arc must be reclaimable because a@one's PROCESS DIED,
    # not because a clock ran out — that is the real context-death case, and
    # liveness is derived (dead pid => void lease), never taken on trust.
    rc, out = run("claim", "--arc", arc, "--agent", "a@one", "--ttl", "36000")
    assert rc == 0 and out["ok"]
    rc, _ = run("note", "--arc", arc, "--agent", "a@one", "--text", "half done")
    assert rc == 0

    # a@one's process is gone; a different agent picks the arc up
    rc, orph = run("list", "--orphans")
    assert rc == 0 and any(a["arc_id"] == arc for a in orph)

    rc, pack = run("pack", "--arc", arc)
    assert rc == 0 and pack["goal"] == "cross-process arc"
    assert pack["constraints"] == ["no network"]
    assert any(p["text"] == "half done" for p in pack["recent_progress"])

    rc, out = run("resume", "--arc", arc, "--agent", "b@two",
                  "--pack-tip", str(pack["tip_seq"]))
    assert rc == 0 and out["ok"] and out["owner"] == "b@two"
    rc, out = run("verify", "--arc", arc)
    assert rc == 0 and out["ok"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
