#!/usr/bin/env python3
"""aios.top.v1 — the live face of the system, for a tmux pane.

Everything shown is read from durable state (the factory event log, the mesh card
directory, the machine itself), so this pane can be killed and reopened without losing
anything and without being the source of truth for anything.
"""
from __future__ import annotations
import os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_factory as fac                                     # noqa: E402
import aios_mesh as mesh                                       # noqa: E402
import aios_resources as res                                   # noqa: E402

C = {"h": "\033[1;36m", "g": "\033[32m", "y": "\033[33m", "r": "\033[31m",
     "d": "\033[2m", "0": "\033[0m", "b": "\033[1m"}


def bar(frac: float, w: int = 18) -> str:
    n = max(0, min(w, int(frac * w)))
    col = C["g"] if frac < 0.7 else C["y"] if frac < 0.9 else C["r"]
    return f"{col}{'█'*n}{C['d']}{'·'*(w-n)}{C['0']}"


def draw() -> None:
    s = res.snapshot()
    tasks = fac.state()
    cards = mesh.directory()
    by = {}
    for t in tasks.values():
        by[t["state"]] = by.get(t["state"], 0) + 1

    print("\033[H\033[J", end="")
    print(f"{C['h']}{C['b']}  AIOS{C['0']}  {time.strftime('%Y-%m-%d %H:%M:%S')}"
          f"{C['d']}   read-only view of durable state{C['0']}\n")

    g = s["gpu"]
    if g["status"] == "ok":
        for d in g["devices"]:
            used = d["used_mb"] / d["total_mb"]
            print(f"  GPU{d['index']}  {bar(used)} {d['free_mb']:>6}MB free  "
                  f"util {d['util_pct']:>3}%")
    else:
        print(f"  {C['y']}GPU UNKNOWN{C['0']} ({g.get('reason')}) — not assumed free")
    m = s["memory"]
    if m["status"] == "ok":
        print(f"  RAM   {bar(1 - m['available_mb']/m['total_mb'])} "
              f"{m['available_mb']:>6}MB avail")
    l = s["load"]
    print(f"  load  {bar(min(1.0, l.get('1m',0)/max(1,l.get('cpus',1))))} "
          f"{l.get('1m','?')} / {l.get('cpus','?')} cpu"
          f"{C['r']+'  SATURATED'+C['0'] if l.get('saturated') else ''}")
    o = s["ollama"]
    print(f"  models {C['d']}resident{C['0']} {o.get('vram_gb','?')}GB  "
          f"{','.join(x['name'] for x in o.get('models', [])) or '—'}\n")

    print(f"  {C['b']}MESH{C['0']}  {len(cards)} live")
    for c in cards[:6]:
        print(f"    {C['g']}●{C['0']} {c.name:<40}{c.role:<11}{c.side_effect_ceiling:<17}"
              f"{','.join(c.domains)[:26]}")
    if not cards:
        print(f"    {C['d']}(none registered){C['0']}")

    print(f"\n  {C['b']}FACTORY{C['0']}  {len(tasks)} task(s)  {by}")
    for t in sorted(tasks.values(), key=lambda t: -t["progress_at"])[:8]:
        age = int(time.time() - t["progress_at"])
        col = {"done": C["g"], "failed": C["r"], "working": C["y"]}.get(t["state"], C["d"])
        stall = f"{C['r']} STALLED{C['0']}" if (t["state"] == "working"
                                                and age > fac.STALL_S) else ""
        print(f"    {col}{t['state']:<8}{C['0']}d{t['depth']} {t['capability']:<13}"
              f"{age:>5}s  {t['goal'][:42]}{stall}")
    print(f"\n{C['d']}  coordination is algorithmic — readiness, leases and closure are "
          f"comparisons, not judgements{C['0']}")


def main() -> int:
    every = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 5
    try:
        while True:
            draw()
            time.sleep(every)
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
