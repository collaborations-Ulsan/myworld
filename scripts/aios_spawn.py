#!/usr/bin/env python3
"""aios.spawn.v1 — AIOS opens its own agent sessions, in tmux, locally, on demand.

The pieces this stands on were built first and are not re-implemented here:
  aios_resources.py   can_spawn() — the machine is asked BEFORE anything is started
  aios_mesh.py        the A2A-shaped card directory the new session appears in
  aios_ambient_hook   SubagentStart registers the card without anyone remembering to

What this adds is the act of creating a peer, and the two things that make a spawner
safe rather than a fork bomb:

  ADMISSION   every spawn passes the resource gate. Measured 2026-08-18: an idle
              phi4-mini held 36.8GB of VRAM and left 12.4GB free, so a spawner that did
              not look would have cheerfully started work that could not run. A gate that
              cannot refuse is decoration.

  REAPING     a spawned session that nobody talks to is a leak. Sessions carry a purpose
              and a lease; the reaper closes the ones whose lease expired AND whose pane
              is idle. Both conditions, because either alone kills useful work — the same
              lesson the arc-lease model checker taught us.

Sovereign by construction: tmux on this box, no cloud, no provider session API. If every
provider disappeared tomorrow the mesh would still have members.
"""
from __future__ import annotations
import argparse, json, os, re, shlex, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_resources as res                                    # noqa: E402
import aios_mesh as mesh                                        # noqa: E402

SESSION = os.environ.get("AIOS_TMUX_SESSION", "aios")
LEDGER = ROOT / ".aios" / "spawn_ledger.jsonl"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,30}$")

# what a role needs, so admission is a fact and not a vibe
PROFILES = {
    "reader":     dict(vram_mb=0,     ram_mb=1024,  ceiling="L0_read",
                       purpose="read and summarise a partition of the corpus"),
    "local-llm":  dict(vram_mb=20000, ram_mb=4096,  ceiling="L1_local_write",
                       purpose="run a local model for bulk or private work"),
    "builder":    dict(vram_mb=0,     ram_mb=4096,  ceiling="L2_process",
                       purpose="edit and test code in a worktree"),
    "harvester":  dict(vram_mb=0,     ram_mb=2048,  ceiling="L3_network_read",
                       purpose="fetch external documents"),
}


def _tmux(*args: str, check: bool = True) -> str:
    p = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=20)
    if check and p.returncode != 0:
        raise RuntimeError(f"tmux {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout.strip()


def _ledger(**kw) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps({"ts": time.time(), **kw}, ensure_ascii=False) + "\n")


def ensure_session() -> None:
    if subprocess.run(["tmux", "has-session", "-t", SESSION],
                      capture_output=True).returncode != 0:
        _tmux("new-session", "-d", "-s", SESSION, "-n", "_root")


def spawn(role: str, label: str, cmd: str = "", *, domains=(), lease_s: int = 7200,
          force: bool = False) -> dict:
    if role not in PROFILES:
        raise SystemExit(f"role must be one of {sorted(PROFILES)}")
    if not NAME_RE.match(label):
        raise SystemExit("label must be lowercase alnum/dash, 2-31 chars")
    prof = PROFILES[role]

    ok, why = res.can_spawn(need_vram_mb=prof["vram_mb"], need_ram_mb=prof["ram_mb"])
    if not ok and not force:
        _ledger(event="refused", role=role, label=label, reason=why)
        raise SystemExit(f"REFUSED: {why}\n"
                         f"  (aios_resources.py --make-room {prof['vram_mb']} may free it)")
    if not ok:
        _ledger(event="forced", role=role, label=label, reason=why)
        print(f"WARNING forced past admission: {why}", file=sys.stderr)

    ensure_session()
    win = f"{role}-{label}"
    name = f"claude@{ROOT.name}/{win}"
    _tmux("new-window", "-t", SESSION, "-n", win, "-d")
    pane = _tmux("list-panes", "-t", f"{SESSION}:{win}", "-F", "#{pane_id}").splitlines()[0]
    pid = int(_tmux("display-message", "-p", "-t", pane, "#{pane_pid}"))

    card = mesh.register(name, role=role, workspace=ROOT.name, domains=list(domains),
                         skills=[role], ceiling=prof["ceiling"], pid=pid)
    # the session learns its own address, so anything it runs can speak as itself
    for kv in (f"AIOS_MESH_NAME={shlex.quote(name)}",
               f"AIOS_MESH_ROLE={role}",
               f"AIOS_SPAWN_LEASE={int(time.time()) + lease_s}"):
        _tmux("send-keys", "-t", pane, f"export {kv}", "Enter")
    if cmd:
        _tmux("send-keys", "-t", pane, cmd, "Enter")

    _ledger(event="spawn", name=name, role=role, pane=pane, pid=pid,
            lease_until=int(time.time()) + lease_s, purpose=prof["purpose"], cmd=cmd[:200])
    return {"name": name, "window": f"{SESSION}:{win}", "pane": pane, "pid": pid,
            "ceiling": prof["ceiling"], "lease_until": int(time.time()) + lease_s}


def _spawned() -> list[dict]:
    if not LEDGER.exists():
        return []
    live: dict[str, dict] = {}
    for line in LEDGER.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("event") == "spawn":
            live[r["name"]] = r
        elif r.get("event") == "reap":
            live.pop(r["name"], None)
    return list(live.values())


def reap(dry: bool = True) -> list[dict]:
    """Close sessions whose lease expired AND that are idle. BOTH — a lease alone kills
    work that is still running, and idleness alone kills a session that is simply waiting."""
    now = time.time()
    out = []
    for r in _spawned():
        expired = now > r.get("lease_until", 0)
        try:
            alive = subprocess.run(["kill", "-0", str(r["pid"])],
                                   capture_output=True).returncode == 0
        except Exception:
            alive = False
        busy = False
        if alive:
            try:
                cpu = subprocess.run(
                    ["ps", "-o", "pcpu=", "--ppid", str(r["pid"])],
                    capture_output=True, text=True, timeout=10).stdout.split()
                busy = any(float(x) > 1.0 for x in cpu if x)
            except Exception:
                busy = True                      # unknown means busy; never reap on a guess
        why = ("dead" if not alive else
               "lease expired and idle" if (expired and not busy) else "")
        if not why:
            continue
        out.append({**r, "why": why})
        if not dry:
            subprocess.run(["tmux", "kill-window", "-t", r["pane"]], capture_output=True)
            _ledger(event="reap", name=r["name"], reason=why)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    # dest must NOT be "cmd": the up subparser has a --cmd option, and argparse writes
    # both into the same Namespace attribute. The subcommand name was silently
    # overwritten by --cmd's default "", so `up` matched no branch and exited 0 having
    # done nothing — while `ls` and `profiles`, which have no --cmd, worked fine.
    sub = ap.add_subparsers(dest="subcmd", required=True)
    sp = sub.add_parser("up"); sp.add_argument("role", choices=sorted(PROFILES))
    sp.add_argument("label"); sp.add_argument("--cmd", default="")
    sp.add_argument("--domains", nargs="*", default=[]); sp.add_argument("--lease", type=int, default=7200)
    sp.add_argument("--force", action="store_true")
    sub.add_parser("ls")
    rp = sub.add_parser("reap"); rp.add_argument("--yes", action="store_true")
    sub.add_parser("profiles")
    a = ap.parse_args()

    if a.subcmd == "profiles":
        for k, v in PROFILES.items():
            print(f"  {k:<11}vram={v['vram_mb']:>6}MB  ceiling={v['ceiling']:<16}{v['purpose']}")
    elif a.subcmd == "up":
        r = spawn(a.role, a.label, a.cmd, domains=a.domains, lease_s=a.lease, force=a.force)
        print(f"spawned {r['name']}\n  window {r['window']}  pid {r['pid']}  "
              f"ceiling {r['ceiling']}")
    elif a.subcmd == "ls":
        rows = _spawned()
        print(f"{len(rows)} spawned session(s)")
        for r in rows:
            left = int(r.get("lease_until", 0) - time.time())
            print(f"  {r['name']:<40}{r['role']:<11}lease {left:>6}s  {r.get('purpose','')[:40]}")
    elif a.subcmd == "reap":
        rows = reap(dry=not a.yes)
        print(f"{len(rows)} reapable" + ("" if a.yes else "  (dry run — pass --yes)"))
        for r in rows:
            print(f"  {r['name']:<40}{r['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
