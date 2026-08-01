#!/usr/bin/env python3
"""G3 watchdog tests — availability without privilege.

    /home/user/miniconda3/bin/python3 -m pytest -q tests/test_aios_society_watchdog.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_society as soc              # noqa: E402
import aios_society_watchdog as wd      # noqa: E402

T0 = 1_800_000_000.0


@pytest.fixture()
def arcs(tmp_path: Path) -> Path:
    return tmp_path / "arcs"


@pytest.fixture()
def locks(tmp_path: Path) -> Path:
    return tmp_path / "locks"


@pytest.fixture()
def log(tmp_path: Path) -> Path:
    return tmp_path / "reclaims.jsonl"


def _orphaned(arcs: Path, locks: Path, goal="finish the migration") -> str:
    """An arc whose worker claimed, worked, then died without handing off."""
    arc = soc.open_arc(goal, agent="a@one", now=T0,
                       constraints=["forbid:tests/conftest"],
                       arcs_dir=arcs)["arc_id"]
    soc.claim(arc, agent="a@one", now=T0, ttl=5, pid=999_999_999,
              arcs_dir=arcs, locks_dir=locks)
    soc.note(arc, "migrated 3 of 10 modules", agent="a@one", now=T0 + 1,
             evidence=["commit:deadbeef"], arcs_dir=arcs)
    return arc


def test_scan_finds_orphans_and_ignores_held_and_closed(arcs: Path, locks: Path,
                                                        log: Path):
    orphan = _orphaned(arcs, locks)
    held = soc.open_arc("held work", agent="b@two", now=T0, arcs_dir=arcs)["arc_id"]
    soc.claim(held, agent="b@two", now=T0, ttl=10_000, arcs_dir=arcs,
              locks_dir=locks)   # this process is alive => holder present
    done = soc.open_arc("finished", agent="c", now=T0, arcs_dir=arcs)["arc_id"]
    soc.claim(done, agent="c", now=T0, ttl=10_000, arcs_dir=arcs, locks_dir=locks)
    soc.close_arc(done, agent="c", status="done", now=T0 + 1, arcs_dir=arcs)

    out = wd.scan(now=T0 + 100, arcs_dir=arcs, log=log)
    ids = {o["arc_id"] for o in out["orphans"]}
    assert orphan in ids and held not in ids and done not in ids


def test_dry_run_changes_nothing(arcs: Path, locks: Path, log: Path):
    arc = _orphaned(arcs, locks)
    before = soc.read_events(arc, arcs)
    r = wd.reclaim_arc(arc, now=T0 + 100, substrate="local", arcs_dir=arcs,
                       locks_dir=locks, dry_run=True, log=log)
    assert r["ok"] and r["dry_run"] and r["would_claim_as"].startswith("watchdog:")
    assert soc.read_events(arc, arcs) == before
    assert not log.exists()


def test_reclaim_takes_ownership_through_the_normal_path(arcs: Path,
                                                         locks: Path, log: Path,
                                                         monkeypatch):
    """The watchdog is a dispatcher, not a privileged writer: it resumes via
    the same freshness-gated claim any agent uses."""
    arc = _orphaned(arcs, locks)
    monkeypatch.setattr(wd, "local_ack", lambda pack, **kw: {
        "ok": True, "text": "goal: finish the migration\nnext: migrate module 4"})
    r = wd.reclaim_arc(arc, now=T0 + 100, substrate="local", arcs_dir=arcs,
                       locks_dir=locks, log=log)
    assert r["ok"] and r["acked"] and r["mttr_s"] >= 0
    st = soc.project(soc.read_events(arc, arcs), now=T0 + 101)
    assert st["owner"] == "watchdog:local@myworld" and st["lease_live"]
    assert any("[watchdog takeover]" in p["text"] for p in st["progress"])
    assert soc.verify_arc(arc, arcs_dir=arcs)["ok"]
    assert len(wd.reclaim_history(log)) == 1


def test_reclaim_loses_to_a_live_holder(arcs: Path, locks: Path, log: Path):
    """INV-3 still binds the watchdog: it cannot steal a held arc."""
    arc = soc.open_arc("busy work", agent="a@one", now=T0, arcs_dir=arcs)["arc_id"]
    soc.claim(arc, agent="a@one", now=T0, ttl=10_000, arcs_dir=arcs,
              locks_dir=locks)   # alive pid
    r = wd.reclaim_arc(arc, now=T0 + 1, substrate="local", arcs_dir=arcs,
                       locks_dir=locks, log=log)
    assert r["ok"] is False and r["reason"] == "held"
    st = soc.project(soc.read_events(arc, arcs), now=T0 + 2)
    assert st["owner"] == "a@one"


def test_stale_pack_race_is_refused(arcs: Path, locks: Path, log: Path,
                                    monkeypatch):
    """If the arc moves between pack and claim, the resume must refuse
    (INV-1) — the watchdog gets no exemption from freshness."""
    arc = _orphaned(arcs, locks)
    real_pack = soc.resume_pack

    def racing_pack(arc_id, **kw):
        pack = real_pack(arc_id, **kw)
        pack["tip_seq"] = pack["tip_seq"] - 1     # pretend we read it earlier
        return pack

    monkeypatch.setattr(soc, "resume_pack", racing_pack)
    r = wd.reclaim_arc(arc, now=T0 + 100, substrate="local", arcs_dir=arcs,
                       locks_dir=locks, log=log)
    assert r["ok"] is False and r["reason"] == "stale_pack"


def test_thrash_is_flagged_not_hidden(arcs: Path, locks: Path, log: Path,
                                      monkeypatch):
    arc = _orphaned(arcs, locks)
    monkeypatch.setattr(wd, "local_ack", lambda pack, **kw: {"ok": True,
                                                             "text": "ack"})
    for i in range(2):
        soc.append_event(arc, {"kind": "released", "agent": "watchdog:local@myworld",
                               "reason": "died again"}, now=T0 + 100 + i,
                         arcs_dir=arcs)
        r = wd.reclaim_arc(arc, now=T0 + 110 + i, substrate="local",
                           arcs_dir=arcs, locks_dir=locks, max_reclaims=2,
                           log=log)
        assert r["ok"], r
    soc.append_event(arc, {"kind": "released", "agent": "w", "reason": "again"},
                     now=T0 + 130, arcs_dir=arcs)
    blocked = wd.reclaim_arc(arc, now=T0 + 140, substrate="local",
                             arcs_dir=arcs, locks_dir=locks, max_reclaims=2,
                             log=log)
    assert blocked["ok"] is False and blocked["reason"] == "reclaim_thrash"
    assert blocked["prior_reclaims"] == 2


def test_no_live_substrate_is_an_outage_not_a_success(monkeypatch):
    monkeypatch.setattr(wd, "probe_local", lambda **kw: {
        "substrate": "local", "live": False, "detail": "down"})
    monkeypatch.setattr(wd, "probe_cli", lambda name: {
        "substrate": name, "live": False, "detail": "not on PATH"})
    s = wd.pick_substrate()
    assert s["ok"] is False and "no live substrate" in s["reason"]


def test_pick_substrate_prefers_local_then_falls_back(monkeypatch):
    monkeypatch.setattr(wd, "probe_local", lambda **kw: {
        "substrate": "local", "live": True, "detail": "ok"})
    monkeypatch.setattr(wd, "probe_cli", lambda name: {
        "substrate": name, "live": True, "detail": "/usr/bin/" + name})
    assert wd.pick_substrate()["substrate"] == "local"

    monkeypatch.setattr(wd, "probe_local", lambda **kw: {
        "substrate": "local", "live": False, "detail": "down"})
    assert wd.pick_substrate()["substrate"] == "codex"
    pinned = wd.pick_substrate("local")
    assert pinned["ok"] is False and "not live" in pinned["reason"]


def test_ack_failure_still_leaves_the_arc_held(arcs: Path, locks: Path,
                                               log: Path, monkeypatch):
    """Availability first: if the taker cannot speak, the arc is still owned
    and the reason is recorded (silence is never a success)."""
    arc = _orphaned(arcs, locks)
    monkeypatch.setattr(wd, "local_ack", lambda pack, **kw: {
        "ok": False, "reason": "TimeoutError"})
    r = wd.reclaim_arc(arc, now=T0 + 100, substrate="local", arcs_dir=arcs,
                       locks_dir=locks, log=log)
    assert r["ok"] and r["acked"] is False and "Timeout" in r["ack_reason"]
    st = soc.project(soc.read_events(arc, arcs), now=T0 + 101)
    assert st["owner"] == "watchdog:local@myworld"


def test_reclaimed_arc_is_verifiable_by_the_separate_verifier(arcs: Path,
                                                              locks: Path,
                                                              log: Path,
                                                              monkeypatch):
    """End-to-end: G1 arc -> G3 reclaim -> G2 verdict, verifier separate."""
    import aios_takeover_verify as tv
    arc = _orphaned(arcs, locks)
    monkeypatch.setattr(wd, "local_ack", lambda pack, **kw: {
        "ok": True,
        "text": "goal: finish the migration; next: migrate module 4 of 10"})
    assert wd.reclaim_arc(arc, now=T0 + 100, substrate="local", arcs_dir=arcs,
                          locks_dir=locks, log=log)["ok"]
    out = tv.verify(arc, now=T0 + 101, verifier="verifier@sep", arcs_dir=arcs,
                    run_oracle=False)
    assert out["ok"] and out["taker"] == "watchdog:local@myworld"
    assert out["prev_owner"] == "a@one"
    assert out["verdict"] == "faithful"


def test_cli_scan_and_probe_run(tmp_path: Path):
    import subprocess
    ad = str(tmp_path / "arcs")
    for cmd in (["scan"], ["probe"]):
        r = subprocess.run([sys.executable,
                            str(ROOT / "scripts" / "aios_society_watchdog.py"),
                            "--arcs-dir", ad, "--log", str(tmp_path / "l.jsonl"),
                            *cmd], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr[-400:]
        json.loads(r.stdout)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
