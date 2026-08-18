#!/usr/bin/env python3
"""aios.mesh.v1 — sessions that know each other, without Claude RC or a cloud.

Founder: rebuild this as an AIOS system rather than riding Claude's Remote Control.

MEASURED STARTING POINT (2026-08-18, ListAgents): 40 sessions are already visible across
three substrates — 25 tmux, 9 Remote Control, 5 cloud. Perception and messaging already
work. What is missing is IDENTITY: the sessions are named things like "I cannot generate a
specific coding task title because the request is not in English", so you can see them and
cannot ask which one knows about memoryOS. The gap was never transport.

ABSORBED, NOT INVENTED. A2A went to the Linux Foundation and is in production at 150+
orgs; its three pieces are exactly our three holes, so we take the shapes:

    Agent Card      capability descriptor  -> our identity gap
    traceparent     W3C trace propagation  -> our correlation gap (measured 2026-08-13:
                    asked four substrates, had to match answers to questions by content)
    Task lifecycle  submitted/working/completed/failed/canceled  -> our state gap

WHAT WE CHANGE, AND WHY. A2A assumes HTTP endpoints and a central registry. We are
sovereign per person and provider-death tolerant, so the registry is a local directory of
cards with pid-based liveness, and transport is the filesystem. Being A2A-SHAPED means a
card here can be served at /.well-known/agent-card.json later without redesign; being
local means nothing dies when a provider does.

WHAT A2A DOES NOT EXPRESS is our residual: authority, reversibility, and verification.
A card here therefore carries `enforcement` and `side_effect_ceiling` from our ladder, so
a peer can refuse a task that exceeds what the sender is allowed to ask for.
"""
from __future__ import annotations
import json, os, socket, sys, time, uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path

ROOT = Path(os.environ.get("AIOS_MESH_ROOT",
                           Path(__file__).resolve().parent.parent / ".aios" / "mesh"))
CARDS = ROOT / "cards"
INBOX = ROOT / "inbox"
EVENTS = ROOT / "events.jsonl"

# our ladder, from spec/aios-seam-v0.md — A2A has no place for this and it is the point
CEILINGS = ("L0_read", "L1_local_write", "L2_process", "L3_network_read",
            "L4_network_write", "L5_install", "L6_credential", "L7_external_send",
            "L8_irreversible")
TASK_STATES = ("submitted", "working", "input-required", "completed", "canceled", "failed")


@dataclass
class Card:
    """A2A-shaped agent card. Serve at /.well-known/agent-card.json unchanged if we ever
    want to; today it lives on disk so no provider can take it away."""
    name: str                       # claude@<workspace>/<role> — the protocol we already wrote
    role: str
    workspace: str
    skills: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    pid: int = 0
    host: str = ""
    substrate: str = "local"
    enforcement: str = "advisory"          # ours, not A2A's
    side_effect_ceiling: str = "L1_local_write"
    version: str = "aios.mesh.card.v1"
    started_at: float = 0.0
    heartbeat_at: float = 0.0

    def alive(self, stale_s: float = 900) -> bool:
        """Two independent positive signals, OR'd — never one as sole authority.

        The first version made pid authoritative and returned False the moment it died,
        so every card registered from a CLI became a corpse when that shell exited, even
        with a fresh heartbeat. A live pid PROVES life; a dead pid proves only that the
        recorded pid is gone, which is also what happens when a transient process did the
        registering. A fresh heartbeat is independent evidence and must be allowed to
        carry the card on its own.

        TTL alone would lie the other way — it buries a busy session and keeps a dead one
        until expiry (the arc lease race the model checker found). Hence: OR, not either."""
        if self.pid and self.host == socket.gethostname():
            try:
                os.kill(self.pid, 0)
                return True                       # strong positive
            except (ProcessLookupError, PermissionError):
                pass                              # NOT a proof of death; fall through
        return (time.time() - self.heartbeat_at) < stale_s


def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    tmp.replace(p)                      # atomic: a reader never sees a half-written card


def _event(**kw) -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a") as fh:
        fh.write(json.dumps({"ts": time.time(), **kw}, ensure_ascii=False) + "\n")


def register(name: str, role: str, workspace: str, skills=(), domains=(),
             ceiling: str = "L1_local_write", substrate: str = "local",
             pid: int | None = None) -> Card:
    """pid must be the SESSION's, not the registering process's. Registering from a CLI
    one-shot recorded the python interpreter's pid, which was already dead by the time
    anything listed the directory — every card read as a corpse. Default to the parent."""
    if ceiling not in CEILINGS:
        raise ValueError(f"ceiling must be one of {CEILINGS}")
    c = Card(name=name, role=role, workspace=workspace, skills=list(skills),
             domains=list(domains), pid=pid or os.getppid(), host=socket.gethostname(),
             substrate=substrate, side_effect_ceiling=ceiling,
             started_at=time.time(), heartbeat_at=time.time())
    _write(CARDS / f"{name.replace('/', '__')}.json", asdict(c))
    _event(kind="register", name=name, role=role, ceiling=ceiling)
    return c


def heartbeat(name: str) -> None:
    p = CARDS / f"{name.replace('/', '__')}.json"
    if p.exists():
        d = json.loads(p.read_text())
        d["heartbeat_at"] = time.time()
        _write(p, d)


def directory(alive_only: bool = True) -> list[Card]:
    out = []
    for p in sorted(CARDS.glob("*.json")):
        try:
            c = Card(**json.loads(p.read_text()))
        except Exception:
            continue
        if not alive_only or c.alive():
            out.append(c)
    return out


def who_knows(topic: str) -> list[Card]:
    """The question the 40 visible sessions cannot answer today."""
    t = topic.lower()
    hits = [c for c in directory()
            if any(t in s.lower() for s in c.skills + c.domains + [c.role, c.workspace])]
    return sorted(hits, key=lambda c: -sum(t in s.lower() for s in c.skills + c.domains))


def send(to: str, frm: str, kind: str, body: dict, *, traceparent: str = "",
         ceiling: str = "L1_local_write") -> dict:
    """Deliver a task. traceparent is W3C so a reply can never be ambiguous again."""
    tid = uuid.uuid4().hex[:16]
    if not traceparent:
        traceparent = f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"
    msg = {"schema": "aios.mesh.task.v1", "task_id": tid, "traceparent": traceparent,
           "to": to, "from": frm, "kind": kind, "state": "submitted",
           "requested_ceiling": ceiling, "body": body, "ts": time.time()}
    _write(INBOX / to.replace("/", "__") / f"{tid}.json", msg)
    _event(kind="send", task_id=tid, to=to, **{"from": frm}, traceparent=traceparent)
    return msg


def poll(name: str) -> list[dict]:
    d = INBOX / name.replace("/", "__")
    return [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.exists() else []


def accept(name: str, task_id: str) -> tuple[bool, str]:
    """Refuse work that exceeds our own ceiling. This is the clause A2A has no field for:
    a peer may ask for anything, and the answer can be no with a reason."""
    p = INBOX / name.replace("/", "__") / f"{task_id}.json"
    if not p.exists():
        return False, "no such task"
    msg = json.loads(p.read_text())
    me = next((c for c in directory() if c.name == name), None)
    if me is None:
        return False, "not registered"
    if CEILINGS.index(msg["requested_ceiling"]) > CEILINGS.index(me.side_effect_ceiling):
        msg["state"] = "failed"
        msg["reason"] = (f"requested {msg['requested_ceiling']} exceeds my ceiling "
                         f"{me.side_effect_ceiling}")
        _write(p, msg)
        _event(kind="refuse", task_id=task_id, reason=msg["reason"])
        return False, msg["reason"]
    msg["state"] = "working"
    _write(p, msg)
    _event(kind="accept", task_id=task_id, by=name)
    return True, "working"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register"); r.add_argument("name"); r.add_argument("role")
    r.add_argument("--workspace", default="myworld"); r.add_argument("--skills", nargs="*", default=[])
    r.add_argument("--domains", nargs="*", default=[]); r.add_argument("--ceiling", default="L1_local_write")
    r.add_argument("--pid", type=int, default=None, help="the SESSION pid (default: parent)")
    sub.add_parser("dir").add_argument("--all", action="store_true")
    w = sub.add_parser("who"); w.add_argument("topic")
    s = sub.add_parser("send"); s.add_argument("to"); s.add_argument("kind")
    s.add_argument("--from", dest="frm", required=True); s.add_argument("--body", default="{}")
    s.add_argument("--ceiling", default="L1_local_write")
    p_ = sub.add_parser("poll"); p_.add_argument("name")
    ac = sub.add_parser("accept"); ac.add_argument("name"); ac.add_argument("task_id")
    a = ap.parse_args()

    if a.cmd == "register":
        c = register(a.name, a.role, a.workspace, a.skills, a.domains, a.ceiling, pid=a.pid)
        print(f"registered {c.name}  pid={c.pid}  ceiling={c.side_effect_ceiling}")
    elif a.cmd == "dir":
        ds = directory(alive_only=not a.all)
        print(f"{len(ds)} card(s)")
        for c in ds:
            print(f"  {'live' if c.alive() else 'dead':<5} {c.name:<34}{c.role:<14}"
                  f"{c.side_effect_ceiling:<18}{','.join(c.domains)[:40]}")
    elif a.cmd == "who":
        hits = who_knows(a.topic)
        print(f"'{a.topic}' → {len(hits)}")
        for c in hits:
            print(f"  {c.name:<34}{','.join(c.skills + c.domains)[:60]}")
        if not hits:
            print("  (nobody claims it — that is an answer, not an error)")
    elif a.cmd == "send":
        m = send(a.to, a.frm, a.kind, json.loads(a.body), ceiling=a.ceiling)
        print(f"task {m['task_id']}  traceparent {m['traceparent']}")
    elif a.cmd == "poll":
        for m in poll(a.name):
            print(f"  [{m['state']:<10}] {m['task_id']}  from {m['from']}  {m['kind']}")
    elif a.cmd == "accept":
        ok, why = accept(a.name, a.task_id)
        print(f"{'ACCEPTED' if ok else 'REFUSED'}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
