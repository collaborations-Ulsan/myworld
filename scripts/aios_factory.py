#!/usr/bin/env python3
"""aios.factory.v1 — the loop that does not switch off.

Founder: sessions that wake each other, work toward a purpose, report to each other, hand
each other work — a factory that never shuts down, improving recursively.

THE COORDINATION IS ALGORITHMIC. Deciding what is ready, who holds the capability, whether
a lease expired, whether a result counts — none of that is a judgement call, so none of it
asks a model. Agents do the WORK; the factory decides when and routes where, mechanically.
That is not an efficiency choice: a scheduler that can be talked into scheduling something
is not a scheduler, and a verifier that can be persuaded is not a verifier.

  queue      durable jsonl, append-only. A task is its events, not a mutable row.
  ready      deps satisfied AND resources available AND not leased elsewhere — all checks
             are comparisons, all reproducible.
  dispatch   capability match against the mesh directory (aios_mesh.who_knows)
  recursion  a worker may enqueue new work. BOUNDED: depth and per-tick budget, because
             "agents hand each other work" and "fork bomb" are the same program without a
             ceiling.
  done       a worker cannot close its own task. Completion needs a check that is code.

Never a hard timeout on our own work: a task stalls when its progress stream stops moving,
not when a clock says so. That distinction cost us a whole panel run at exit 124.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_mesh as mesh                                       # noqa: E402
import aios_resources as res                                   # noqa: E402
import aios_capabilities as caps                                # noqa: E402

FAC = ROOT / ".aios" / "factory"
EVENTS = FAC / "events.jsonl"
MAX_DEPTH = 3                 # a worker's worker's worker may not spawn more work
MAX_NEW_PER_TICK = 8          # bounded recursion, per the docstring
STALL_S = 1800                # no progress event in this long -> stalled, not "timed out"
REFUSAL_TTL = 600             # a refusal expires; capabilities get added


def _emit(**kw) -> dict:
    FAC.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.time(), **kw}
    with EVENTS.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _events() -> list[dict]:
    if not EVENTS.exists():
        return []
    out = []
    for line in EVENTS.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def state() -> dict[str, dict]:
    """Fold the append-only stream into current task state. Pure function of the log —
    which is why two readers never disagree and a crash loses nothing."""
    tasks: dict[str, dict] = {}
    for e in _events():
        tid = e.get("task_id")
        if not tid:
            continue
        k = e.get("kind")
        if k == "enqueue":
            tasks[tid] = {"task_id": tid, "goal": e["goal"], "capability": e["capability"],
                          "deps": e.get("deps", []), "depth": e.get("depth", 0),
                          "state": "queued", "created": e["ts"], "parent": e.get("parent"),
                          "owner": None, "progress_at": e["ts"], "result": None}
        elif tid in tasks:
            t = tasks[tid]
            if k == "claim":
                t.update(state="working", owner=e["owner"], progress_at=e["ts"])
            elif k == "progress":
                t["progress_at"] = e["ts"]
            elif k == "done":
                t.update(state="done", result=e.get("result"), progress_at=e["ts"])
            elif k == "fail":
                t.update(state="failed", result=e.get("reason"), progress_at=e["ts"])
            elif k == "release":
                # Remember WHO gave it back. Re-offering a task to the holder that just
                # refused it is an infinite ping-pong: measured one task released four
                # times in a minute, because owning a capability and having a handler for
                # it are different things.
                # timestamped, because a refusal is a fact about a MOMENT. A holder that
                # refused before it had a handler must not be excluded forever — measured:
                # adding the missing handler changed nothing because the exclusion was
                # permanent, so the task stayed unassignable for a reason that no longer
                # existed.
                t.setdefault("refused_by", {})[e.get("owner") or t.get("owner")] = e["ts"]
                t.update(state="queued", owner=None, progress_at=e["ts"])
    return tasks


def enqueue(goal: str, capability: str, deps=(), depth: int = 0,
            parent: str | None = None, dedup: bool = True) -> str:
    """Deduplicated by (goal, capability) while an identical task is still open.

    Without this the ambient router re-enqueues on every repeat of a prompt shape, and the
    queue fills with redundant work that looks like demand. Measured: three timing runs of
    the same prompt produced six tasks."""
    if dedup:
        for t in state().values():
            if (t["goal"] == goal[:200] and t["capability"] == capability
                    and t["state"] in ("queued", "working")):
                return t["task_id"]
    # Closed vocabulary. An unknown capability fails HERE rather than becoming a task that
    # waits forever behind a typo — measured: unheld:adversarial sat with no owner while
    # the board read as busy.
    caps.validate(capability)
    if depth > MAX_DEPTH:
        raise SystemExit(f"depth {depth} exceeds MAX_DEPTH {MAX_DEPTH} — refusing. "
                         f"Unbounded self-enqueue is a fork bomb with better manners.")
    tid = uuid.uuid4().hex[:12]
    _emit(kind="enqueue", task_id=tid, goal=goal, capability=capability,
          deps=list(deps), depth=depth, parent=parent)
    return tid


def ready(tasks: dict[str, dict]) -> list[dict]:
    """Every clause is a comparison. No model is consulted about readiness."""
    done = {t for t, v in tasks.items() if v["state"] == "done"}
    out = []
    for t in tasks.values():
        if t["state"] != "queued":
            continue
        if any(d not in done for d in t["deps"]):
            continue
        out.append(t)
    return sorted(out, key=lambda t: t["created"])


def stalled(tasks: dict[str, dict]) -> list[dict]:
    now = time.time()
    return [t for t in tasks.values()
            if t["state"] == "working" and (now - t["progress_at"]) > STALL_S]


def assign(task: dict) -> str | None:
    """Capability match against the live mesh, skipping anyone who already handed it back.
    Nobody claiming it IS an answer; everybody having refused it is a DIFFERENT answer and
    must not read as the first."""
    refused = task.get("refused_by") or {}
    now = time.time()
    for c in mesh.who_knows(task["capability"]):
        when = refused.get(c.name)
        if when is None or (now - when) > REFUSAL_TTL:
            return c.name
    return None


def tick(dry: bool = False) -> dict:
    tasks = state()
    rdy = ready(tasks)
    st = stalled(tasks)
    ok, why = res.can_spawn(need_ram_mb=1024)
    acted = {"ready": len(rdy), "stalled": len(st), "assigned": [], "released": [],
             "resource_ok": ok, "resource_why": why}

    for t in st:                                   # progress-based, never clock-based
        acted["released"].append(t["task_id"])
        if not dry:
            _emit(kind="release", task_id=t["task_id"], owner=t.get("owner"),
                  reason=f"no progress for {int(time.time()-t['progress_at'])}s")

    if not ok:
        return acted                               # a refusal with a reason beats thrashing

    unheld: dict[str, int] = {}
    for t in rdy[:MAX_NEW_PER_TICK]:
        who = assign(t)
        if who is None:
            # A capability nobody holds is a finding, not a queue entry to forget. Silence
            # here would let work sit forever while the board looked merely busy.
            # distinguish "nobody holds it" from "every holder refused it"
            key = t["capability"] + (" (all holders refused)" if t.get("refused_by") else "")
            unheld[key] = unheld.get(key, 0) + 1
            continue
        acted["assigned"].append({"task": t["task_id"], "to": who})
        if not dry:
            _emit(kind="claim", task_id=t["task_id"], owner=who)
            mesh.send(who, "aios@factory", "work",
                      {"task_id": t["task_id"], "goal": t["goal"], "depth": t["depth"]},
                      ceiling="L1_local_write")
    if unheld:
        acted["unheld_capabilities"] = unheld
        if not dry:
            _emit(kind="unheld", capabilities=unheld)
    return acted


def close(task_id: str, check_cmd: str) -> tuple[bool, str]:
    """A worker cannot close its own task by saying so. Completion runs a command and
    reads its exit code — the anti-reward-hacking clause, as code rather than as a rule."""
    try:
        p = subprocess.run(check_cmd, shell=True, capture_output=True, text=True,
                           timeout=600, cwd=ROOT)
    except Exception as e:
        _emit(kind="fail", task_id=task_id, reason=f"check crashed: {type(e).__name__}")
        return False, f"check crashed: {type(e).__name__}"
    if p.returncode == 0:
        _emit(kind="done", task_id=task_id, result=(p.stdout or "")[:400],
              check=check_cmd[:200])
        return True, "closed by check"
    _emit(kind="fail", task_id=task_id, reason=f"check rc={p.returncode}: "
                                               f"{(p.stderr or p.stdout)[:200]}")
    return False, f"check failed rc={p.returncode}"


def run(interval: int, max_ticks: int = 0) -> int:
    """The wake cycle. Sleeps between ticks; every tick is idempotent, so a missed one
    costs nothing and a doubled one costs nothing."""
    n = 0
    _emit(kind="factory_start", interval=interval, pid=os.getpid())
    while max_ticks == 0 or n < max_ticks:
        a = tick()
        _emit(kind="tick", n=n, **{k: v for k, v in a.items() if k != "resource_why"})
        uh = a.get("unheld_capabilities")
        print(f"[{time.strftime('%H:%M:%S')}] tick {n}  ready={a['ready']} "
              f"assigned={len(a['assigned'])} stalled={a['stalled']}"
              f"{'  NOBODY HOLDS: ' + ','.join(uh) if uh else ''}"
              f"{'' if a['resource_ok'] else '  HOLD: ' + a['resource_why'][:60]}", flush=True)
        n += 1
        time.sleep(interval)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="subcmd", required=True)
    e = s.add_parser("add"); e.add_argument("goal"); e.add_argument("capability")
    e.add_argument("--deps", nargs="*", default=[]); e.add_argument("--depth", type=int, default=0)
    t = s.add_parser("tick"); t.add_argument("--dry", action="store_true")
    r = s.add_parser("run"); r.add_argument("--interval", type=int, default=300)
    r.add_argument("--max-ticks", type=int, default=0)
    c = s.add_parser("close"); c.add_argument("task_id"); c.add_argument("check")
    s.add_parser("ls")
    a = ap.parse_args()

    if a.subcmd == "add":
        print(enqueue(a.goal, a.capability, a.deps, a.depth))
    elif a.subcmd == "tick":
        print(json.dumps(tick(dry=a.dry), ensure_ascii=False, indent=1))
    elif a.subcmd == "run":
        return run(a.interval, a.max_ticks)
    elif a.subcmd == "close":
        ok, why = close(a.task_id, a.check)
        print(f"{'CLOSED' if ok else 'REFUSED'}: {why}")
        return 0 if ok else 1
    elif a.subcmd == "ls":
        ts = state()
        by = {}
        for t in ts.values():
            by[t["state"]] = by.get(t["state"], 0) + 1
        print(f"{len(ts)} task(s)  {by}")
        for t in sorted(ts.values(), key=lambda t: t["created"]):
            age = int(time.time() - t["progress_at"])
            print(f"  {t['task_id']}  {t['state']:<8}d{t['depth']} {t['capability']:<14}"
                  f"{age:>6}s  {t['goal'][:46]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
