#!/usr/bin/env python3
"""aios.resources.v1 — what this machine actually has, right now.

Spawning agents without looking at the box is how you get five sessions competing for a
GPU that already has 26GB resident. Every spawn decision reads this first.

Reports, never guesses: a probe that fails is reported as unknown, not as zero. A missing
nvidia-smi means "GPU state unknown", which must not read the same as "no GPU load" —
that distinction is the difference between a safe refusal and a confident overcommit.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def _run(cmd: list[str], timeout: int = 10) -> str | None:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout if p.returncode == 0 else None
    except Exception:
        return None


def gpus() -> dict:
    out = _run(["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits"])
    if out is None:
        return {"status": "unknown", "reason": "nvidia-smi unavailable", "devices": []}
    devs = []
    for line in out.strip().splitlines():
        f = [x.strip() for x in line.split(",")]
        if len(f) < 5:
            continue
        tot, used = int(f[2]), int(f[3])
        devs.append({"index": int(f[0]), "name": f[1], "total_mb": tot, "used_mb": used,
                     "free_mb": tot - used, "util_pct": int(f[4])})
    return {"status": "ok", "devices": devs,
            "free_mb_total": sum(d["free_mb"] for d in devs),
            "largest_free_mb": max((d["free_mb"] for d in devs), default=0)}


def memory() -> dict:
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, _, v = line.partition(":")
            info[k] = int(v.strip().split()[0])
        return {"status": "ok", "total_mb": info["MemTotal"] // 1024,
                "available_mb": info["MemAvailable"] // 1024}
    except Exception as e:
        return {"status": "unknown", "reason": type(e).__name__}


def disk(paths=("/", "/data")) -> dict:
    out = {}
    for p in paths:
        try:
            u = shutil.disk_usage(p)
            out[p] = {"free_gb": round(u.free / 1e9, 1), "total_gb": round(u.total / 1e9, 1)}
        except Exception:
            out[p] = {"status": "unknown"}
    return out


def load() -> dict:
    try:
        one, five, fifteen = os.getloadavg()
        return {"status": "ok", "1m": round(one, 2), "5m": round(five, 2),
                "cpus": os.cpu_count(),
                "saturated": one > (os.cpu_count() or 1) * 0.9}
    except Exception:
        return {"status": "unknown"}


def ollama_resident() -> dict:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=5) as r:
            d = json.loads(r.read())
        ms = [{"name": m["name"], "vram_gb": round(m.get("size_vram", m.get("size", 0)) / 1e9, 1)}
              for m in d.get("models", [])]
        return {"status": "ok", "models": ms,
                "vram_gb": round(sum(m["vram_gb"] for m in ms), 1)}
    except Exception as e:
        return {"status": "unknown", "reason": type(e).__name__}


def sessions() -> dict:
    out = _run(["tmux", "list-panes", "-a", "-F", "#{session_name}:#{window_index}.#{pane_index}"])
    if out is None:
        return {"status": "unknown", "reason": "tmux unavailable"}
    panes = [l for l in out.strip().splitlines() if l]
    return {"status": "ok", "panes": len(panes)}


def snapshot() -> dict:
    return {"ts": time.time(), "gpu": gpus(), "memory": memory(), "disk": disk(),
            "load": load(), "ollama": ollama_resident(), "tmux": sessions()}


def can_spawn(need_vram_mb: int = 0, need_ram_mb: int = 2048,
              need_disk_gb: float = 1.0) -> tuple[bool, str]:
    """A refusal with a reason beats a spawn that thrashes."""
    s = snapshot()
    if need_vram_mb:
        g = s["gpu"]
        if g["status"] != "ok":
            return False, f"GPU state unknown ({g.get('reason')}) — refusing to assume it is free"
        if g["largest_free_mb"] < need_vram_mb:
            return False, (f"largest free VRAM {g['largest_free_mb']}MB < needed {need_vram_mb}MB "
                           f"(resident: {s['ollama'].get('vram_gb','?')}GB)")
    m = s["memory"]
    if m["status"] == "ok" and m["available_mb"] < need_ram_mb:
        return False, f"RAM available {m['available_mb']}MB < needed {need_ram_mb}MB"
    if s["load"].get("saturated"):
        return False, f"load {s['load']['1m']} on {s['load']['cpus']} cpus — saturated"
    free = s["disk"].get("/data", {}).get("free_gb", 0)
    if free and free < need_disk_gb:
        return False, f"/data free {free}GB < needed {need_disk_gb}GB"
    return True, "ok"


def evictable(min_free_mb: int) -> list[dict]:
    """Which resident models could be released to make room.

    Measured 2026-08-18: phi4-mini held 36.8GB of VRAM while idle, leaving 12.4GB free —
    not enough for Muse Glimmer 30B (18GB) or Qwen3.8-27B. The machine was not short of
    hardware; it was short of eviction. This is the cheap fix that a kernel-level rewrite
    would not have found, because the problem was never scheduling."""
    o = ollama_resident()
    if o["status"] != "ok":
        return []
    g = gpus()
    need = max(0, min_free_mb - g.get("largest_free_mb", 0))
    if need <= 0:
        return []
    out, freed = [], 0
    for m in sorted(o["models"], key=lambda m: -m["vram_gb"]):
        if freed >= need:
            break
        out.append(m)
        freed += m["vram_gb"] * 1024
    return out


def evict(name: str) -> tuple[bool, str]:
    """Release a model by asking ollama to keep it for zero seconds. Reversible: the next
    request reloads it. We never kill the daemon — other work depends on it."""
    body = json.dumps({"model": name, "keep_alive": 0}).encode()
    try:
        req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30):
            pass
        return True, f"released {name}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    if "--json" in sys.argv:
        print(json.dumps(snapshot(), ensure_ascii=False, indent=1)); return 0
    if "--make-room" in sys.argv:
        i = sys.argv.index("--make-room")
        need = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 18000
        cands = evictable(need)
        if not cands:
            print(f"already {gpus().get('largest_free_mb')}MB free — nothing to evict")
            return 0
        for m in cands:
            print(f"  evict {m['name']} ({m['vram_gb']}GB) …", end=" ")
            ok, why = evict(m["name"])
            print("ok" if ok else why)
        time.sleep(2)
        print(f"  largest free VRAM now: {gpus().get('largest_free_mb')}MB")
        return 0
    if "--can-spawn" in sys.argv:
        i = sys.argv.index("--can-spawn")
        vram = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 0
        ok, why = can_spawn(need_vram_mb=vram)
        print(f"{'CAN SPAWN' if ok else 'REFUSE'}: {why}")
        return 0 if ok else 1
    s = snapshot()
    g = s["gpu"]
    if g["status"] == "ok":
        for d in g["devices"]:
            print(f"  GPU{d['index']} {d['name']:<24}{d['free_mb']:>7}MB free / "
                  f"{d['total_mb']}MB   util {d['util_pct']}%")
        print(f"  largest free VRAM: {g['largest_free_mb']}MB")
    else:
        print(f"  GPU: UNKNOWN ({g.get('reason')})")
    print(f"  RAM  {s['memory'].get('available_mb','?')}MB available / {s['memory'].get('total_mb','?')}MB")
    print(f"  load {s['load'].get('1m','?')} on {s['load'].get('cpus','?')} cpus"
          f"{'  SATURATED' if s['load'].get('saturated') else ''}")
    for p, d in s["disk"].items():
        print(f"  disk {p:<7}{d.get('free_gb','?')}GB free")
    o = s["ollama"]
    print(f"  ollama resident: {o.get('vram_gb','?')}GB  "
          f"{[m['name'] for m in o.get('models', [])]}")
    print(f"  tmux panes: {s['tmux'].get('panes','?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
