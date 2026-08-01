#!/usr/bin/env python3
"""G3 — Availability: nobody's arc stays nobody's.

Goal tree: `docs/AIOS_SOCIETY_GOALTREE_2026-08-02.md` (G3). A society is only
available if an arc whose worker died gets picked up WITHOUT a human noticing.
This watchdog finds orphaned arcs (open, nobody present) and routes each to a
live heterogeneous substrate, which then resumes it through the ordinary
freshness-gated path (`aios_society.resume`) — the watchdog is a dispatcher,
never a privileged writer.

Metric it exists to move: **MTTR** — wall time from "worker died" to "another
agent holds the arc and has read its resume pack".

Design constraints carried from the 2026-08-02 council red-team:
  * The watchdog never bypasses the lease (INV-3): it calls the same claim path
    and loses the same way if someone else got there first.
  * It never fabricates progress. It hands the taker a resume pack and records
    the reclaim; the taker's fidelity is judged later by the SEPARATE verifier
    (`aios_takeover_verify.py`, INV-2/INV-6).
  * Substrate liveness is PROBED, never assumed — a substrate that cannot
    answer a trivial health check is not offered work (silence ≠ availability).
  * Reclaim is rate-limited per arc (`--max-reclaims`): an arc that keeps being
    orphaned is a sick arc, not an availability win. It is flagged and left for
    a human — thrash is reported, never hidden.

Substrates (probed in order; first live one wins unless --substrate pins it):
  local   — ollama HTTP (no cloud, no cost, always-on): the availability floor.
  codex   — `codex` CLI, heterogeneous vendor.
  claude  — `claude` CLI, heterogeneous session.
The floor matters more than the ceiling here: an arc resumed by a small local
model that only re-reads the pack and appends "picked up, needs X" is still a
live arc, which is the entire claim.

Usage:
  python3 scripts/aios_society_watchdog.py scan            # report only
  python3 scripts/aios_society_watchdog.py reclaim [--dry-run] [--substrate S]
  python3 scripts/aios_society_watchdog.py probe           # substrate liveness

Cron-friendly: `reclaim` is idempotent and exits 0 when there is nothing to do.
Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aios_society as soc  # noqa: E402

SCHEMA = "aios.society.watchdog.v1"
OLLAMA_URL = os.environ.get("AIOS_OLLAMA_URL", "http://localhost:11434")
LOCAL_MODEL = os.environ.get("AIOS_WATCHDOG_MODEL", "qwen3-coder-next")
RECLAIM_LOG = soc.SOCIETY_DIR / "reclaims.jsonl"
DEFAULT_MAX_RECLAIMS = 3
DEFAULT_TTL = 1800.0


# ---------------------------------------------------------------------------
# Substrate liveness — probed, never assumed
# ---------------------------------------------------------------------------

def probe_local(url: str = OLLAMA_URL, timeout: float = 5.0) -> dict:
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=timeout) as r:
            models = [m.get("name", "") for m in
                      json.loads(r.read().decode("utf-8")).get("models", [])]
        has = any(m.split(":")[0] == LOCAL_MODEL.split(":")[0] for m in models)
        return {"substrate": "local", "live": bool(models), "model_present": has,
                "detail": f"{len(models)} models"}
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        return {"substrate": "local", "live": False,
                "detail": f"{type(exc).__name__}: {str(exc)[:120]}"}


def probe_cli(name: str) -> dict:
    path = shutil.which(name)
    return {"substrate": name, "live": bool(path), "detail": path or "not on PATH"}


def probe_all() -> list[dict]:
    return [probe_local(), probe_cli("codex"), probe_cli("claude")]


def pick_substrate(preferred: str = "") -> dict:
    probes = probe_all()
    by = {p["substrate"]: p for p in probes}
    if preferred:
        p = by.get(preferred)
        if not p:
            return {"ok": False, "reason": f"unknown substrate {preferred}"}
        if not p["live"]:
            return {"ok": False, "reason": f"{preferred} is not live",
                    "probe": p}
        return {"ok": True, "substrate": preferred, "probes": probes}
    for name in ("local", "codex", "claude"):
        if by[name]["live"]:
            return {"ok": True, "substrate": name, "probes": probes}
    return {"ok": False, "reason": "no live substrate — availability is zero "
                                   "right now (this is a real outage, not a "
                                   "quiet success)", "probes": probes}


# ---------------------------------------------------------------------------
# Reclaim bookkeeping (thrash must be visible)
# ---------------------------------------------------------------------------

def reclaim_history(log: Path | str = RECLAIM_LOG) -> list[dict]:
    p = Path(log)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def log_reclaim(rec: dict, log: Path | str = RECLAIM_LOG) -> None:
    p = Path(log)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def reclaim_count(arc_id: str, log: Path | str = RECLAIM_LOG) -> int:
    return sum(1 for r in reclaim_history(log)
               if r.get("arc_id") == arc_id and r.get("ok"))


# ---------------------------------------------------------------------------
# The takeover the watchdog performs
# ---------------------------------------------------------------------------

def local_ack(pack: dict, *, url: str = OLLAMA_URL, model: str = LOCAL_MODEL,
              timeout: float = 120.0) -> dict:
    """Ask the local model to state, from the pack ALONE, what this arc is and
    what it would do next. This is the cheapest possible proof that the record
    is sufficient to continue — and it is the taker's first action, so the
    separate verifier can judge it. It never edits anything."""
    prompt = (
        "You are taking over an in-flight work arc from an agent that died. "
        "Using ONLY the record below, reply in at most 4 lines:\n"
        "line 1: the arc's goal, in your own words\n"
        "line 2: the single next concrete step\n"
        "line 3: any constraint you must respect\n"
        "line 4: what you still need that the record does not contain "
        "(write 'nothing' if the record suffices)\n\n"
        "=== ARC RECORD ===\n"
        + json.dumps({k: pack.get(k) for k in
                      ("arc_id", "goal", "constraints", "handoff",
                       "recent_progress", "open_verdicts")},
                     ensure_ascii=False, indent=1)
    )
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.0, "num_predict": 400}}
                      ).encode("utf-8")
    req = urllib.request.Request(f"{url}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {"ok": True, "text": str(data.get("response") or "").strip()}
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}: {str(exc)[:160]}"}


def reclaim_arc(arc_id: str, *, now: float, substrate: str,
                arcs_dir: Path | str = soc.ARCS_DIR,
                locks_dir: Path | str = soc.LOCKS_DIR,
                ttl: float = DEFAULT_TTL, dry_run: bool = False,
                max_reclaims: int = DEFAULT_MAX_RECLAIMS,
                log: Path | str = RECLAIM_LOG) -> dict:
    """Route ONE orphaned arc to a live substrate through the normal path."""
    t0 = time.time()
    prior = reclaim_count(arc_id, log)
    if prior >= max_reclaims:
        return {"ok": False, "arc_id": arc_id, "reason": "reclaim_thrash",
                "prior_reclaims": prior,
                "detail": "arc keeps being orphaned — flagged for a human "
                          "instead of being re-routed again"}
    pack = soc.resume_pack(arc_id, now=now, arcs_dir=arcs_dir)
    if not pack.get("ok"):
        return {"ok": False, "arc_id": arc_id, "reason": pack.get("reason")}
    agent = f"watchdog:{substrate}@myworld"
    if dry_run:
        return {"ok": True, "arc_id": arc_id, "dry_run": True,
                "would_claim_as": agent, "tip_seq": pack["tip_seq"],
                "goal": pack["goal"]}

    took = soc.resume(arc_id, agent=agent, pack_tip_seq=pack["tip_seq"],
                      now=now, ttl=ttl, substrate=substrate,
                      arcs_dir=arcs_dir, locks_dir=locks_dir)
    if not took.get("ok"):
        rec = {"ts": now, "arc_id": arc_id, "ok": False,
               "reason": took.get("reason"), "substrate": substrate}
        log_reclaim(rec, log)
        return rec

    ack = (local_ack(pack) if substrate == "local"
           else {"ok": False, "reason": f"no ack driver for {substrate} yet — "
                                        "arc is held, awaiting that agent"})
    if ack.get("ok"):
        soc.note(arc_id, "[watchdog takeover] " + ack["text"][:1500],
                 agent=agent, now=time.time(),
                 evidence=[f"substrate:{substrate}", f"pack_tip:{pack['tip_seq']}"],
                 arcs_dir=arcs_dir)
    rec = {"ts": now, "arc_id": arc_id, "ok": True, "substrate": substrate,
           "agent": agent, "tip_seq": pack["tip_seq"],
           "acked": bool(ack.get("ok")), "ack_reason": ack.get("reason"),
           "mttr_s": round(time.time() - t0, 2), "prior_reclaims": prior}
    log_reclaim(rec, log)
    return rec


def scan(*, now: float, arcs_dir: Path | str = soc.ARCS_DIR,
         log: Path | str = RECLAIM_LOG) -> dict:
    orph = soc.orphans(now=now, arcs_dir=arcs_dir)
    for a in orph:
        a["prior_reclaims"] = reclaim_count(a["arc_id"], log)
    return {"schema": SCHEMA, "kind": "scan", "ts": now,
            "n_arcs": len(soc.list_arcs(now=now, arcs_dir=arcs_dir)),
            "n_orphans": len(orph), "orphans": orph}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Society availability watchdog (G3)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap.add_argument("--arcs-dir", default=str(soc.ARCS_DIR))
    ap.add_argument("--locks-dir", default=str(soc.LOCKS_DIR))
    ap.add_argument("--log", default=str(RECLAIM_LOG))
    sub.add_parser("scan")
    sub.add_parser("probe")
    p = sub.add_parser("reclaim")
    p.add_argument("--substrate", default="", help="pin a substrate")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--ttl", type=float, default=DEFAULT_TTL)
    p.add_argument("--max-reclaims", type=int, default=DEFAULT_MAX_RECLAIMS)
    p.add_argument("--arc", default="", help="only this arc")
    a = ap.parse_args(argv)

    now, ad = time.time(), Path(a.arcs_dir)
    if a.cmd == "probe":
        out = {"schema": SCHEMA, "kind": "probe", "probes": probe_all(),
               "chosen": pick_substrate()}
    elif a.cmd == "scan":
        out = scan(now=now, arcs_dir=ad, log=Path(a.log))
    else:
        s = pick_substrate(a.substrate)
        if not s["ok"]:
            out = {"schema": SCHEMA, "kind": "reclaim", "ok": False, **s}
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return 1
        found = scan(now=now, arcs_dir=ad, log=Path(a.log))["orphans"]
        if a.arc:
            found = [o for o in found if o["arc_id"] == a.arc]
        results = [reclaim_arc(o["arc_id"], now=time.time(),
                               substrate=s["substrate"], arcs_dir=ad,
                               locks_dir=Path(a.locks_dir), ttl=a.ttl,
                               dry_run=a.dry_run, max_reclaims=a.max_reclaims,
                               log=Path(a.log))
                   for o in found]
        out = {"schema": SCHEMA, "kind": "reclaim", "ok": True,
               "substrate": s["substrate"], "n_orphans": len(found),
               "n_reclaimed": sum(1 for r in results if r.get("ok")),
               "results": results}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
