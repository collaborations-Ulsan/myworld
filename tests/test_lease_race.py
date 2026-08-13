"""The lease race the SMT model found, reproduced against the real code.

`verify/lease_smt.py` reports that `note` as written is VIOLABLE and that making
read-and-append atomic removes the schedule. A solver proves things about a
model, not about an implementation, so this file does the other half: it induces
the interleaving the model described and asserts the real code refuses the write.

The interleaving is induced rather than waited for. A race whose window is a few
microseconds would make a flaky test, and a test that fails one run in a
thousand teaches people to re-run it. Blocking one thread between the guard and
the append is the same schedule the solver found, made deterministic.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_society as S  # noqa: E402


def _arc(tmp_path):
    opened = S.open_arc(goal="lease race", agent="A@h", now=1000.0,
                        arcs_dir=tmp_path)
    return opened["arc_id"]


def test_a_takeover_cannot_land_inside_a_write(tmp_path):
    """The schedule the model found, and why it is now unreachable.

    Before the lock, a claim could complete while the writer sat between its
    ownership guard and its append, so the writer's progress landed on an arc it
    no longer owned. With guard and append inside the same arc lock the claim
    cannot interleave at all — it blocks — so the property to assert is
    SERIALISATION: B's claim must finish after A's write, not during it.

    NOTE for anyone copying this setup: `locks_dir` must be passed to BOTH
    claim and note. They default independently, so a caller that redirects
    `arcs_dir` alone gets two different lock directories and therefore no
    mutual exclusion — which is exactly the bug that made the first version of
    this test pass against unfixed code.
    """
    arcs, locks = tmp_path / "arcs", tmp_path / "locks"
    arcs.mkdir(); locks.mkdir()
    arc = S.open_arc(goal="lease race", agent="A@h", now=1000.0,
                     arcs_dir=arcs)["arc_id"]
    S.claim(arc, agent="A@h", now=1000.0, ttl=600.0, pid=999_999,
            arcs_dir=arcs, locks_dir=locks)

    a_inside = threading.Event()
    order: list[str] = []
    real_project = S.project

    def slow_project(events, *, now):
        st = real_project(events, now=now)
        if threading.current_thread().name == "writer" and not a_inside.is_set():
            a_inside.set()
            time.sleep(0.6)          # hold the critical section open
        return st

    S.project = slow_project
    try:
        def writer():
            r = S.note(arc, "progress from the owner", agent="A@h", now=1100.0,
                       arcs_dir=arcs, locks_dir=locks)
            order.append("note_ok" if r["ok"] else "note_refused")

        t = threading.Thread(target=writer, name="writer")
        t.start()
        assert a_inside.wait(timeout=10), "writer never reached its guard"

        took = S.claim(arc, agent="B@h", now=1100.0, ttl=600.0,
                       arcs_dir=arcs, locks_dir=locks)
        order.append("claim_ok" if took["ok"] else "claim_refused")
        t.join(timeout=10)
    finally:
        S.project = real_project

    assert order[0].startswith("note"), \
        f"the claim landed inside the write window: {order}"

    # And the log must never hold progress from an agent that was not the owner
    # when it was appended — replay it and check every progress event.
    events = S.read_events(arc, arcs)
    owner = None
    for e in events:
        if e.get("kind") == "claimed":
            owner = e["agent"]
        elif e.get("kind") == "progress":
            assert e["agent"] == owner, \
                f"progress by {e['agent']} while {owner} owned the arc"


def test_the_owner_can_still_write_after_the_fix(tmp_path):
    """The repair must not re-break what the lease guard exists to permit.

    A previous fix in this area went the other way — binding the write path to
    pid liveness stopped a CLI agent recording its own progress across
    processes. Serialising the write must not resurrect that.
    """
    arcs, locks = tmp_path / "arcs", tmp_path / "locks"
    arcs.mkdir(); locks.mkdir()
    arc = S.open_arc(goal="normal writing", agent="A@h", now=1000.0,
                     arcs_dir=arcs)["arc_id"]
    S.claim(arc, agent="A@h", now=1000.0, ttl=600.0, arcs_dir=arcs,
            locks_dir=locks)
    for i in range(3):
        r = S.note(arc, f"step {i}", agent="A@h", now=1000.0 + i,
                   arcs_dir=arcs)
        assert r["ok"], r
    progress = [e for e in S.read_events(arc, arcs) if e.get("kind") == "progress"]
    assert len(progress) == 3


def test_concurrent_owner_writes_are_serialised(tmp_path):
    """Two threads of the SAME owner must not corrupt the log."""
    arcs, locks = tmp_path / "arcs", tmp_path / "locks"
    arcs.mkdir(); locks.mkdir()
    arc = S.open_arc(goal="parallel writes", agent="A@h", now=1000.0,
                     arcs_dir=arcs)["arc_id"]
    S.claim(arc, agent="A@h", now=1000.0, ttl=600.0, arcs_dir=arcs,
            locks_dir=locks)

    errors = []

    def w(n):
        try:
            for i in range(5):
                r = S.note(arc, f"t{n}-{i}", agent="A@h", now=1000.0 + i,
                           arcs_dir=arcs)
                if not r["ok"]:
                    errors.append(r)
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    ts = [threading.Thread(target=w, args=(n,)) for n in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=30)
    assert errors == [], errors

    events = S.read_events(arc, arcs)
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs) and len(seqs) == len(set(seqs)), \
        "interleaved appends corrupted the sequence"
