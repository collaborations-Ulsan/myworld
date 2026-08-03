#!/usr/bin/env python3
"""AIOS Society Kernel — the ARC: work state that outlives the agent.

Goal tree: `docs/AIOS_SOCIETY_GOALTREE_2026-08-02.md` (G1). Founder directive
2026-08-02: single agents forget everything on context reset and have no
availability -> build a society (or redesign storage). Here they are the same
thing: **the record IS the memory, and society members are pilgrims of the
record**.

An **arc** is a unit of work that survives its worker. It is an append-only
event log; the "current state" is a projection (ESAA/event-sourcing shape,
grounded 2026-08-02 against A2A v1.0 / Letta / LangGraph checkpointing /
AgentFS — see the goal tree's landscape section). Any agent — a new session, a
different CLI, a local model — can reconstruct an arc from its events alone and
continue it.

WHAT THIS DOES NOT CLAIM (pre-registered null, binding): the society does NOT
make agents smarter. Injecting accumulated experience into a frozen model does
not improve task performance (`docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md`,
C_overall = 0.000). The arc's claims are exactly three: **continuity**
(work outlives the worker), **availability** (someone can always take over), and
**verified handoff** (the takeover's fidelity is externally checked).

Invariants (each answers a specific adversarial attack from the 2026-08-02
council red-team; see the goal tree table):

  INV-1 freshness      A resume pack carries its causal position (tip_seq +
                       tip_hash). Resuming on a stale pack is refused ->
                       re-sync first. "Checkpoint loads" is not continuity.
  INV-2 semantic       Takeover fidelity is judged on the taker's ACTIONS vs the
                       arc's constraints, never on packet checksums
                       (`takeover_check`, verifier separate from the taker).
  INV-3 single-writer  Exclusive lease per arc via atomic O_EXCL claim + TTL.
                       No longest-chain, no split-brain: a contested claim is
                       REFUSED and recorded.
  INV-4 ownership      Every event carries its agent; the arc has exactly one
                       owner at any time; takeover writes an ownership transfer.
  INV-5 continuous     Progress is appended as it happens, not only at handoff
                       boundaries, so death costs at most the last step.
  INV-7 revisable      An arc can RETRACT a wrong step (`supersede`) without
                       rewriting history: the log is immutable, the projection
                       is current. Append-only alone let a mistake be inherited
                       as fact by every later agent. A supersession must name
                       its reason — an unexplained retraction is hiding.
  INV-6 non-blocking   Verification NEVER blocks a resume (a verifier must not
                       be a single point of failure). Verdicts land after the
                       fact and flag the arc.

Composes existing organs, invents nothing already present:
  * merkle_root  — replicated from scripts/aios_experience.py (same precedent).
  * liveness     — council/presence.py-style: a lease is void if its holder's
                   pid is gone (liveness is DERIVED, never trusted from a claim).
  * append-only  — memoryOS store.py discipline (never rewrite history).

CLI (the impure edge — supplies the real clock):
  python3 scripts/aios_society.py open   --goal "..." [--constraint C]... [--oracle "cmd"]
  python3 scripts/aios_society.py claim  --arc ARC --agent ID [--ttl 3600] [--substrate claude]
  python3 scripts/aios_society.py note   --arc ARC --agent ID --text "..." [--evidence REF]...
  python3 scripts/aios_society.py pack   --arc ARC            # resume pack (JSON)
  python3 scripts/aios_society.py supersede --arc ARC --agent ID --target-seq N --reason "..."
  python3 scripts/aios_society.py resume --arc ARC --agent ID --pack-tip N  # freshness-gated
  python3 scripts/aios_society.py handoff --arc ARC --agent ID --reason "..."
  python3 scripts/aios_society.py close  --arc ARC --agent ID --status done|abandoned
  python3 scripts/aios_society.py list [--orphans] · verify --arc ARC · root

Schema: aios.society.arc.v1 (events) / aios.society.v1 (ops). Stdlib-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOCIETY_DIR = ROOT / ".aios" / "society"
ARCS_DIR = SOCIETY_DIR / "arcs"
LOCKS_DIR = SOCIETY_DIR / "locks"

EVENT_SCHEMA = "aios.society.arc.v1"
SCHEMA = "aios.society.v1"
DEFAULT_TTL = 3600.0

# Event kinds. `progress` is the continuous one (INV-5).
KINDS = ("arc_opened", "claimed", "claim_refused", "progress", "handoff_offered",
         "released", "takeover_verdict", "superseded", "arc_closed")


# ---------------------------------------------------------------------------
# Hashing + Merkle (replicated from scripts/aios_experience.py)
# ---------------------------------------------------------------------------

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def merkle_root(hashes: list[str]) -> str:
    """Deterministic binary Merkle root over sorted leaf hashes."""
    if not hashes:
        return "sha256:" + _sha256("")
    layer = sorted(hashes)
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i + 1] if i + 1 < len(layer) else layer[i]
            nxt.append("sha256:" + _sha256(a + b))
        layer = nxt
    return layer[0]


def _leaf(seq: int, raw_line: str) -> str:
    """Position-salted leaf: reordering history changes the root."""
    return "sha256:" + _sha256(f"{seq}\x00{raw_line}")


# ---------------------------------------------------------------------------
# Storage — append-only, one JSONL per arc
# ---------------------------------------------------------------------------

def arc_path(arc_id: str, arcs_dir: Path | str = ARCS_DIR) -> Path:
    return Path(arcs_dir) / f"{arc_id}.jsonl"


def read_events(arc_id: str, arcs_dir: Path | str = ARCS_DIR) -> list[dict]:
    p = arc_path(arc_id, arcs_dir)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def append_event(arc_id: str, event: dict, *, now: float,
                 arcs_dir: Path | str = ARCS_DIR) -> dict:
    """Append ONE event. Never rewrites; seq is the count of prior events."""
    if event.get("kind") not in KINDS:
        raise ValueError(f"unknown event kind {event.get('kind')!r}")
    arcs = Path(arcs_dir)
    arcs.mkdir(parents=True, exist_ok=True)
    prior = read_events(arc_id, arcs)
    rec = {"schema": EVENT_SCHEMA, "arc_id": arc_id, "seq": len(prior),
           "ts": now, **event}
    line = _canon(rec)
    with arc_path(arc_id, arcs).open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return rec


# ---------------------------------------------------------------------------
# Projection — current state is derived, never stored (INV-4 ownership)
# ---------------------------------------------------------------------------

def project(events: list[dict], *, now: float) -> dict:
    """Fold the event log into the arc's current state."""
    if not events:
        return {"exists": False}
    head = events[0]
    st = {
        "exists": True, "arc_id": head.get("arc_id"),
        "goal": head.get("goal", ""), "constraints": head.get("constraints", []),
        "oracle_cmd": head.get("oracle_cmd"),
        "opened_by": head.get("agent"), "opened_ts": head.get("ts"),
        "status": "open", "owner": None, "owner_substrate": None,
        "lease_until": None, "owner_pid": None,
        "progress": [], "handoff": None, "closed": None,
        "takeover_verdicts": [], "contested": 0, "supersessions": [],
        "tip_seq": events[-1]["seq"], "n_events": len(events),
    }
    for e in events:
        k = e["kind"]
        if k == "claimed":
            st["owner"] = e.get("agent")
            st["owner_substrate"] = e.get("substrate")
            st["lease_until"] = e.get("lease_until")
            st["owner_pid"] = e.get("pid")
            st["handoff"] = None  # a claim consumes an outstanding offer
        elif k == "claim_refused":
            st["contested"] += 1
        elif k == "progress":
            st["progress"].append({"seq": e["seq"], "ts": e["ts"],
                                   "agent": e.get("agent"),
                                   "text": e.get("text", ""),
                                   "evidence": e.get("evidence", []),
                                   "superseded_by": None, "reason": None})
        elif k == "superseded":
            # Revision without amnesia: history is never rewritten, the
            # PROJECTION stops treating the target as current. This is the
            # operator an append-only society lacked — it could add and hand
            # off, but never undo a wrong turn (temporal supersession, the
            # shape Zep/Graphiti and Governed Shared Memory converged on).
            tgt = e.get("target_seq")
            for p in st["progress"]:
                if p["seq"] == tgt:
                    p["superseded_by"] = e["seq"]
                    p["reason"] = e.get("reason", "")
            st["supersessions"].append({"seq": e["seq"], "target_seq": tgt,
                                        "agent": e.get("agent"),
                                        "reason": e.get("reason", "")})
        elif k == "handoff_offered":
            st["handoff"] = {"seq": e["seq"], "by": e.get("agent"),
                             "reason": e.get("reason", ""),
                             "next_step": e.get("next_step", "")}
            st["owner"], st["lease_until"] = None, None
        elif k == "released":
            st["owner"], st["lease_until"] = None, None
        elif k == "takeover_verdict":
            st["takeover_verdicts"].append(
                {"seq": e["seq"], "by": e.get("agent"),
                 "verdict": e.get("verdict"), "findings": e.get("findings", [])})
        elif k == "arc_closed":
            st["status"] = e.get("status", "closed")
            st["closed"] = {"seq": e["seq"], "by": e.get("agent"),
                            "status": e.get("status"),
                            "evidence": e.get("evidence", [])}
            st["owner"], st["lease_until"] = None, None
    st["lease_live"] = lease_live(st, now=now)          # owner may write
    st["holder_present"] = holder_present(st, now=now)  # blocks takeover
    return st


# ---------------------------------------------------------------------------
# Liveness + leases (INV-3 single writer; liveness DERIVED, never claimed)
# ---------------------------------------------------------------------------

def pid_is_alive(pid) -> bool:
    """council/presence.py discipline: a corpse cannot hold a lease."""
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def lease_live(state: dict, *, now: float) -> bool:
    """WRITE view: does the owning AGENT still hold this arc? TTL only.

    Deliberately pid-free. An agent is not a process: a CLI agent shells out a
    fresh process per command, and a session survives many of them. Binding the
    write path to a pid would forbid an agent from recording its own progress —
    the exact thing this kernel exists to make possible (found by
    tests/test_aios_society.py::test_cli_roundtrip_second_process_resumes).
    """
    if not state.get("owner") or not state.get("lease_until"):
        return False
    return float(state["lease_until"]) > now


def holder_present(state: dict, *, now: float) -> bool:
    """TAKEOVER view: does the lease block a DIFFERENT agent from claiming?

    TTL AND liveness. A dead holder frees the arc immediately (fast MTTR)
    instead of parking it until the TTL burns down — liveness is DERIVED
    (council/presence.py discipline), never taken on a claimant's word. A
    holder on another host is trusted only until its TTL, recorded honestly:
    cross-host liveness needs a heartbeat we do not have yet.
    """
    if not lease_live(state, now=now):
        return False
    pid, host = state.get("owner_pid"), state.get("owner_host")
    if pid and (host in (None, os.uname().nodename)):
        return pid_is_alive(pid)
    return True


def _lock_path(arc_id: str, locks_dir: Path | str = LOCKS_DIR) -> Path:
    return Path(locks_dir) / f"{arc_id}.lock"


def _with_arc_lock(arc_id: str, fn, *, locks_dir: Path | str = LOCKS_DIR,
                   attempts: int = 50, sleep_s: float = 0.02):
    """Atomic critical section per arc (O_EXCL create; stale locks reaped).
    Cheap and local-first — the arc log is the truth, this only serializes."""
    locks = Path(locks_dir)
    locks.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(arc_id, locks)
    for _ in range(attempts):
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            break
        except FileExistsError:
            try:
                holder = int(lock.read_text(encoding="utf-8").strip() or 0)
            except (OSError, ValueError):
                holder = 0
            if holder and not pid_is_alive(holder):
                lock.unlink(missing_ok=True)   # reap a dead holder's lock
                continue
            time.sleep(sleep_s)
    else:
        raise TimeoutError(f"could not acquire arc lock for {arc_id}")
    try:
        return fn()
    finally:
        lock.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def new_arc_id(goal: str, *, now: float,
               arcs_dir: Path | str = ARCS_DIR) -> str:
    """A fresh, unused arc id.

    NOT a pure hash of (now, goal): two arcs with the same goal at the same
    timestamp would collide, and the second `open_arc` would silently append a
    second `arc_opened` event to the FIRST arc's log — two work arcs fused into
    one, the worst possible corruption for a substrate whose whole promise is
    that a record can be resumed. Found by
    tests/test_aios_takeover_verify.py::test_KNOWN_LIMITATION_parroting_...
    Entropy makes collisions vanishing; the existence check makes them
    impossible.
    """
    for _ in range(64):
        arc_id = "arc-" + _sha256(f"{now}:{goal}:{os.urandom(8).hex()}")[:12]
        if not arc_path(arc_id, arcs_dir).exists():
            return arc_id
    raise RuntimeError("could not mint an unused arc id")


def open_arc(goal: str, *, agent: str, now: float,
             constraints: list[str] | None = None,
             oracle_cmd: str | None = None,
             arcs_dir: Path | str = ARCS_DIR) -> dict:
    if not goal.strip():
        raise ValueError("an arc needs a goal")
    arc_id = new_arc_id(goal, now=now, arcs_dir=arcs_dir)
    append_event(arc_id, {"kind": "arc_opened", "agent": agent, "goal": goal,
                          "constraints": constraints or [],
                          "oracle_cmd": oracle_cmd}, now=now, arcs_dir=arcs_dir)
    return {"schema": SCHEMA, "ok": True, "arc_id": arc_id}


def claim(arc_id: str, *, agent: str, now: float, ttl: float = DEFAULT_TTL,
          substrate: str = "", pid: int | None = None,
          arcs_dir: Path | str = ARCS_DIR,
          locks_dir: Path | str = LOCKS_DIR) -> dict:
    """Take exclusive ownership (INV-3). A live lease held by someone else is
    REFUSED and the attempt is recorded — never a second writer, never a fork."""
    def _do() -> dict:
        events = read_events(arc_id, arcs_dir)
        if not events:
            return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
        st = project(events, now=now)
        if st["status"] != "open":
            return {"schema": SCHEMA, "ok": False,
                    "reason": f"arc is {st['status']}"}
        if st["holder_present"] and st["owner"] != agent:
            append_event(arc_id, {"kind": "claim_refused", "agent": agent,
                                  "held_by": st["owner"],
                                  "lease_until": st["lease_until"]},
                         now=now, arcs_dir=arcs_dir)
            return {"schema": SCHEMA, "ok": False, "reason": "held",
                    "held_by": st["owner"], "lease_until": st["lease_until"]}
        rec = append_event(arc_id, {
            "kind": "claimed", "agent": agent, "substrate": substrate,
            "pid": int(pid if pid is not None else os.getpid()),
            "owner_host": os.uname().nodename,
            "lease_until": now + float(ttl),
            "prev_owner": st["owner"]}, now=now, arcs_dir=arcs_dir)
        return {"schema": SCHEMA, "ok": True, "arc_id": arc_id,
                "owner": agent, "lease_until": rec["lease_until"],
                "prev_owner": st["owner"], "tip_seq": rec["seq"]}
    return _with_arc_lock(arc_id, _do, locks_dir=locks_dir)


def note(arc_id: str, text: str, *, agent: str, now: float,
         evidence: list[str] | None = None,
         arcs_dir: Path | str = ARCS_DIR) -> dict:
    """Append progress as it happens (INV-5). Only the lease holder may write —
    otherwise two agents could interleave a fiction."""
    events = read_events(arc_id, arcs_dir)
    if not events:
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    st = project(events, now=now)
    if st["owner"] != agent or not st["lease_live"]:
        return {"schema": SCHEMA, "ok": False, "reason": "not the lease holder",
                "owner": st["owner"], "lease_live": st["lease_live"]}
    rec = append_event(arc_id, {"kind": "progress", "agent": agent,
                                "text": text, "evidence": evidence or []},
                       now=now, arcs_dir=arcs_dir)
    return {"schema": SCHEMA, "ok": True, "seq": rec["seq"]}


def supersede(arc_id: str, target_seq: int, reason: str, *, agent: str,
              now: float, arcs_dir: Path | str = ARCS_DIR) -> dict:
    """Mark an earlier progress event as no longer current (D2).

    An append-only society could only ADD and HAND OFF; it could not undo a
    wrong turn, so a mistaken step stayed in every resume pack forever and the
    next agent inherited it as fact. `supersede` is the missing operator:
    history is preserved byte-for-byte (the audit trail is untouched) and only
    the PROJECTION changes — superseded progress is excluded from the pack's
    current view and reported separately.

    Guards: only the lease holder may revise (same rule as writing); the target
    must exist, be a progress event, and not already be superseded; and a
    reason is mandatory — an unexplained retraction is indistinguishable from
    hiding a mistake, which is exactly what the record exists to prevent.
    """
    if not reason.strip():
        return {"schema": SCHEMA, "ok": False,
                "reason": "a supersession must state why (unexplained "
                          "retraction is hiding, not revising)"}
    events = read_events(arc_id, arcs_dir)
    if not events:
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    st = project(events, now=now)
    if st["owner"] != agent or not st["lease_live"]:
        return {"schema": SCHEMA, "ok": False, "reason": "not the lease holder",
                "owner": st["owner"]}
    target = next((e for e in events if e["seq"] == int(target_seq)), None)
    if target is None:
        return {"schema": SCHEMA, "ok": False,
                "reason": f"no event at seq {target_seq}"}
    if target["kind"] != "progress":
        return {"schema": SCHEMA, "ok": False,
                "reason": f"only progress events can be superseded "
                          f"(seq {target_seq} is {target['kind']})"}
    if any(e["kind"] == "superseded" and e.get("target_seq") == int(target_seq)
           for e in events):
        return {"schema": SCHEMA, "ok": False,
                "reason": f"seq {target_seq} is already superseded"}
    rec = append_event(arc_id, {"kind": "superseded", "agent": agent,
                                "target_seq": int(target_seq),
                                "reason": reason}, now=now, arcs_dir=arcs_dir)
    return {"schema": SCHEMA, "ok": True, "seq": rec["seq"],
            "target_seq": int(target_seq)}


def current_progress(state: dict) -> list[dict]:
    """The progress a taker should act on: superseded steps excluded."""
    return [p for p in state["progress"] if p["superseded_by"] is None]


def resume_pack(arc_id: str, *, now: float, tail: int = 12,
                arcs_dir: Path | str = ARCS_DIR) -> dict:
    """Everything a NEW agent needs to continue — plus its causal position
    (INV-1): tip_seq + tip_hash, so a stale pack can be detected on use."""
    events = read_events(arc_id, arcs_dir)
    if not events:
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    st = project(events, now=now)
    raw = arc_path(arc_id, arcs_dir).read_text(encoding="utf-8").splitlines()
    tip_line = raw[-1] if raw else ""
    return {
        "schema": SCHEMA, "ok": True, "kind": "resume_pack",
        "arc_id": arc_id, "goal": st["goal"], "constraints": st["constraints"],
        "oracle_cmd": st["oracle_cmd"], "status": st["status"],
        "owner": st["owner"], "lease_live": st["lease_live"],
        "handoff": st["handoff"],
        # Only CURRENT progress is handed to a taker; retracted steps are
        # reported separately so a revision is visible as a revision and never
        # silently re-inherited as fact.
        "recent_progress": current_progress(st)[-tail:],
        "n_progress": len(current_progress(st)),
        "superseded": [{"seq": p["seq"], "text": p["text"][:200],
                        "reason": p["reason"]}
                       for p in st["progress"] if p["superseded_by"]],
        "open_verdicts": [v for v in st["takeover_verdicts"]
                          if v.get("verdict") not in ("faithful", None)],
        # causal position — the freshness gate
        "tip_seq": st["tip_seq"], "tip_hash": _leaf(st["tip_seq"], tip_line),
        "root": arc_root(arc_id, arcs_dir=arcs_dir),
    }


def freshness(arc_id: str, pack_tip_seq: int, *,
              arcs_dir: Path | str = ARCS_DIR) -> dict:
    """INV-1: is a pack still current? A hash that verifies proves the record
    was not rewritten; it does NOT prove the world stood still. Anything newer
    than the pack must be re-read BEFORE acting."""
    events = read_events(arc_id, arcs_dir)
    if not events:
        return {"ok": False, "reason": "no such arc"}
    tip = events[-1]["seq"]
    missed = [e for e in events if e["seq"] > int(pack_tip_seq)]
    return {"ok": True, "fresh": not missed, "pack_tip_seq": int(pack_tip_seq),
            "current_tip_seq": tip, "missed_events": len(missed),
            "missed_kinds": [e["kind"] for e in missed]}


def resume(arc_id: str, *, agent: str, pack_tip_seq: int, now: float,
           ttl: float = DEFAULT_TTL, substrate: str = "",
           arcs_dir: Path | str = ARCS_DIR,
           locks_dir: Path | str = LOCKS_DIR) -> dict:
    """Freshness-gated takeover: refuses a stale pack (INV-1), then claims
    (INV-3/4). Verification of fidelity happens AFTER this returns (INV-6) —
    a verifier is never allowed to block availability."""
    fr = freshness(arc_id, pack_tip_seq, arcs_dir=arcs_dir)
    if not fr.get("ok"):
        return {"schema": SCHEMA, "ok": False, "reason": fr.get("reason")}
    if not fr["fresh"]:
        return {"schema": SCHEMA, "ok": False, "reason": "stale_pack",
                "freshness": fr,
                "remedy": "re-read the resume pack (society.py pack) and retry"}
    out = claim(arc_id, agent=agent, now=now, ttl=ttl, substrate=substrate,
                arcs_dir=arcs_dir, locks_dir=locks_dir)
    out["freshness"] = fr
    return out


def offer_handoff(arc_id: str, *, agent: str, now: float, reason: str = "",
                  next_step: str = "", arcs_dir: Path | str = ARCS_DIR) -> dict:
    """Release ownership with an explicit next step. Dying agents should call
    this; the watchdog handles those that cannot (G3)."""
    events = read_events(arc_id, arcs_dir)
    if not events:
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    st = project(events, now=now)
    if st["owner"] != agent:
        return {"schema": SCHEMA, "ok": False, "reason": "not the owner",
                "owner": st["owner"]}
    rec = append_event(arc_id, {"kind": "handoff_offered", "agent": agent,
                                "reason": reason, "next_step": next_step},
                       now=now, arcs_dir=arcs_dir)
    return {"schema": SCHEMA, "ok": True, "seq": rec["seq"]}


def close_arc(arc_id: str, *, agent: str, status: str, now: float,
              evidence: list[str] | None = None,
              arcs_dir: Path | str = ARCS_DIR) -> dict:
    if status not in ("done", "abandoned"):
        return {"schema": SCHEMA, "ok": False,
                "reason": "status must be done|abandoned"}
    events = read_events(arc_id, arcs_dir)
    if not events:
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    st = project(events, now=now)
    if st["status"] != "open":
        return {"schema": SCHEMA, "ok": False,
                "reason": f"already {st['status']}"}
    rec = append_event(arc_id, {"kind": "arc_closed", "agent": agent,
                                "status": status, "evidence": evidence or []},
                       now=now, arcs_dir=arcs_dir)
    return {"schema": SCHEMA, "ok": True, "seq": rec["seq"], "status": status}


def record_verdict(arc_id: str, *, agent: str, verdict: str, now: float,
                   findings: list[str] | None = None,
                   arcs_dir: Path | str = ARCS_DIR) -> dict:
    """INV-6: a takeover verdict lands after the resume, flagging the arc; it
    never gates availability. verdict in {faithful, drifted, unverifiable}."""
    if verdict not in ("faithful", "drifted", "unverifiable"):
        return {"schema": SCHEMA, "ok": False,
                "reason": "verdict must be faithful|drifted|unverifiable"}
    if not read_events(arc_id, arcs_dir):
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    rec = append_event(arc_id, {"kind": "takeover_verdict", "agent": agent,
                                "verdict": verdict, "findings": findings or []},
                       now=now, arcs_dir=arcs_dir)
    return {"schema": SCHEMA, "ok": True, "seq": rec["seq"]}


# ---------------------------------------------------------------------------
# Society-level views (G3 availability)
# ---------------------------------------------------------------------------

def list_arcs(*, now: float, arcs_dir: Path | str = ARCS_DIR) -> list[dict]:
    arcs = Path(arcs_dir)
    if not arcs.is_dir():
        return []
    out = []
    for p in sorted(arcs.glob("arc-*.jsonl")):
        st = project(read_events(p.stem, arcs), now=now)
        if st.get("exists"):
            out.append({"arc_id": st["arc_id"], "goal": st["goal"],
                        "status": st["status"], "owner": st["owner"],
                        "lease_live": st["lease_live"],
                        "holder_present": st["holder_present"],
                        "handoff_pending": bool(st["handoff"]),
                        "n_progress": len(st["progress"]),
                        "tip_seq": st["tip_seq"]})
    return out


def orphans(*, now: float, arcs_dir: Path | str = ARCS_DIR) -> list[dict]:
    """Open arcs nobody is holding: the worker died, or handed off and left.
    This is the society's availability surface — what a watchdog reclaims."""
    return [a for a in list_arcs(now=now, arcs_dir=arcs_dir)
            if a["status"] == "open" and not a["holder_present"]]


def arc_root(arc_id: str, *, arcs_dir: Path | str = ARCS_DIR) -> str:
    p = arc_path(arc_id, arcs_dir)
    if not p.exists():
        return merkle_root([])
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return merkle_root([_leaf(i, ln) for i, ln in enumerate(lines)])


def verify_arc(arc_id: str, *, arcs_dir: Path | str = ARCS_DIR) -> dict:
    """Structural integrity: parseable, seq is a dense 0..n-1 chain, one open
    event first, ownership transitions legal. Tamper evidence via the root."""
    events = read_events(arc_id, arcs_dir)
    problems = []
    if not events:
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    if events[0]["kind"] != "arc_opened":
        problems.append("first event is not arc_opened")
    for i, e in enumerate(events):
        if e.get("seq") != i:
            problems.append(f"seq gap/reorder at index {i}: {e.get('seq')}")
        if e.get("kind") not in KINDS:
            problems.append(f"unknown kind at seq {e.get('seq')}")
        if not e.get("agent"):
            problems.append(f"event {e.get('seq')} has no agent (INV-4)")
    if sum(1 for e in events if e["kind"] == "arc_opened") != 1:
        problems.append("more than one arc_opened")
    by_seq = {e.get("seq"): e for e in events}
    seen_targets: set[int] = set()
    for e in events:
        if e["kind"] != "superseded":
            continue
        t = e.get("target_seq")
        tgt = by_seq.get(t)
        if tgt is None:
            problems.append(f"supersession at seq {e['seq']} targets missing "
                            f"seq {t}")
        elif tgt["kind"] != "progress":
            problems.append(f"supersession at seq {e['seq']} targets a "
                            f"{tgt['kind']}, not progress")
        elif t >= e["seq"]:
            problems.append(f"supersession at seq {e['seq']} targets a "
                            f"non-earlier seq {t}")
        if t in seen_targets:
            problems.append(f"seq {t} superseded more than once")
        seen_targets.add(t)
        if not str(e.get("reason", "")).strip():
            problems.append(f"supersession at seq {e['seq']} states no reason")
    closed_at = [e["seq"] for e in events if e["kind"] == "arc_closed"]
    if closed_at and closed_at[0] != events[-1]["seq"]:
        problems.append("events appended after arc_closed")
    return {"schema": SCHEMA, "ok": not problems, "arc_id": arc_id,
            "n_events": len(events), "problems": problems,
            "root": arc_root(arc_id, arcs_dir=arcs_dir)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AIOS Society Kernel — arcs that "
                                             "outlive their agents")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap.add_argument("--arcs-dir", default=str(ARCS_DIR))

    p = sub.add_parser("open"); p.add_argument("--goal", required=True)
    p.add_argument("--agent", default="claude@myworld")
    p.add_argument("--constraint", action="append", default=[])
    p.add_argument("--oracle", default=None)

    p = sub.add_parser("claim"); p.add_argument("--arc", required=True)
    p.add_argument("--agent", required=True); p.add_argument("--ttl", type=float, default=DEFAULT_TTL)
    p.add_argument("--substrate", default="")

    p = sub.add_parser("note"); p.add_argument("--arc", required=True)
    p.add_argument("--agent", required=True); p.add_argument("--text", required=True)
    p.add_argument("--evidence", action="append", default=[])

    p = sub.add_parser("pack"); p.add_argument("--arc", required=True)
    p.add_argument("--tail", type=int, default=12)

    p = sub.add_parser("supersede"); p.add_argument("--arc", required=True)
    p.add_argument("--agent", required=True)
    p.add_argument("--target-seq", type=int, required=True)
    p.add_argument("--reason", required=True)

    p = sub.add_parser("resume"); p.add_argument("--arc", required=True)
    p.add_argument("--agent", required=True); p.add_argument("--pack-tip", type=int, required=True)
    p.add_argument("--ttl", type=float, default=DEFAULT_TTL)
    p.add_argument("--substrate", default="")

    p = sub.add_parser("handoff"); p.add_argument("--arc", required=True)
    p.add_argument("--agent", required=True); p.add_argument("--reason", default="")
    p.add_argument("--next-step", default="")

    p = sub.add_parser("verdict"); p.add_argument("--arc", required=True)
    p.add_argument("--agent", required=True); p.add_argument("--verdict", required=True)
    p.add_argument("--finding", action="append", default=[])

    p = sub.add_parser("close"); p.add_argument("--arc", required=True)
    p.add_argument("--agent", required=True); p.add_argument("--status", required=True)
    p.add_argument("--evidence", action="append", default=[])

    p = sub.add_parser("list"); p.add_argument("--orphans", action="store_true")
    p = sub.add_parser("verify"); p.add_argument("--arc", required=True)
    p = sub.add_parser("root"); p.add_argument("--arc", required=True)

    a = ap.parse_args(argv)
    now, ad = time.time(), Path(a.arcs_dir)

    if a.cmd == "open":
        out = open_arc(a.goal, agent=a.agent, now=now, constraints=a.constraint,
                       oracle_cmd=a.oracle, arcs_dir=ad)
    elif a.cmd == "claim":
        out = claim(a.arc, agent=a.agent, now=now, ttl=a.ttl,
                    substrate=a.substrate, arcs_dir=ad)
    elif a.cmd == "note":
        out = note(a.arc, a.text, agent=a.agent, now=now, evidence=a.evidence,
                   arcs_dir=ad)
    elif a.cmd == "pack":
        out = resume_pack(a.arc, now=now, tail=a.tail, arcs_dir=ad)
    elif a.cmd == "supersede":
        out = supersede(a.arc, a.target_seq, a.reason, agent=a.agent, now=now,
                        arcs_dir=ad)
    elif a.cmd == "resume":
        out = resume(a.arc, agent=a.agent, pack_tip_seq=a.pack_tip, now=now,
                     ttl=a.ttl, substrate=a.substrate, arcs_dir=ad)
    elif a.cmd == "handoff":
        out = offer_handoff(a.arc, agent=a.agent, now=now, reason=a.reason,
                            next_step=a.next_step, arcs_dir=ad)
    elif a.cmd == "verdict":
        out = record_verdict(a.arc, agent=a.agent, verdict=a.verdict, now=now,
                             findings=a.finding, arcs_dir=ad)
    elif a.cmd == "close":
        out = close_arc(a.arc, agent=a.agent, status=a.status, now=now,
                        evidence=a.evidence, arcs_dir=ad)
    elif a.cmd == "list":
        out = (orphans(now=now, arcs_dir=ad) if a.orphans
               else list_arcs(now=now, arcs_dir=ad))
    elif a.cmd == "verify":
        out = verify_arc(a.arc, arcs_dir=ad)
    else:  # root
        out = {"arc_id": a.arc, "root": arc_root(a.arc, arcs_dir=ad)}

    print(json.dumps(out, ensure_ascii=False, indent=1))
    ok = out.get("ok", True) if isinstance(out, dict) else True
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
