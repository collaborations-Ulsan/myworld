#!/usr/bin/env python3
"""Model-residency arbiter — stop concurrent sessions from thrashing the GPU.

Built from a bill I paid on 2026-08-10. Two calibration runs died at their
25-minute timeouts because the model they called was not resident while a
different session held another one; the same job finished in **40 seconds** once
it used the model already loaded. Nothing was broken — several Claude Code
sessions simply share one box and one ollama, each asks for whatever model its
own task prefers, and every mismatch pays a multi-GB load.

Cross-session messaging (Claude Code v2.1.224+) gave sessions a way to TALK.
It gave them no way to AGREE about a shared physical resource, and a chat
channel is not an allocator. This is the smallest allocator that helps:

    advise    given the models that would do, name the one already resident
    acquire   take a lease on a model so peers know it is in use
    release   give it back
    status    what is resident, what is leased, who is waiting

The load-bearing command is `advise`, and it is the cheap one. Most agent tasks
have several models that would do; picking the resident one costs nothing and
saves a multi-GB load. Today's paraphrase step is the case in point — a 30B was
specified where any small instruct model would do, and the 30B was not resident.

HONEST LIMIT, and it is the interesting one: this arbiter cannot make a peer
comply. Claude Code exposes `CLAUDE_CODE_MESSAGING_SOCKET` so a script can post
into ITS OWN session, but there is no documented host-side push into a PEER
session — only the model calling SendMessage, i.e. an offer the peer's model may
decline. Our own measurement of offers is zero uses in 96 episodes. So this ships
as advisory, its own limitation is the specification of what is missing above the
transport, and `status --json` reports `enforcement: "advisory"` so no caller can
mistake it for a guarantee.

    python3 scripts/aios_gpu_arbiter.py status
    python3 scripts/aios_gpu_arbiter.py advise --models qwen3:8b,qwen2.5-coder:7b
    python3 scripts/aios_gpu_arbiter.py acquire --model bge-m3 --ttl 600

Schema: aios.gpu_arbiter.v0   Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

SCHEMA = "aios.gpu_arbiter.v0"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
# Deliberately outside any one repo: the resource is the machine, so the lease
# table has to be visible to every session on it, whatever repo it sits in.
STATE = Path(os.environ.get("AIOS_ARBITER_DIR",
                            Path.home() / ".aios" / "arbiter"))
LEASES = STATE / "leases.jsonl"


def _get(path: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(f"{OLLAMA}{path}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def resident() -> tuple[list[dict], str | None]:
    """Models loaded right now, newest first. Second element is why not."""
    try:
        payload = _get("/api/ps")
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        # A dead ollama and an idle ollama look identical if this returns [].
        return [], f"{type(exc).__name__}: {exc}"[:160]
    out = []
    for m in payload.get("models", []) or []:
        out.append({"name": m.get("name") or m.get("model"),
                    "vram_gb": round((m.get("size_vram") or 0) / 1e9, 2),
                    "expires_at": m.get("expires_at")})
    return out, None


def _read_leases(now: float) -> list[dict]:
    if not LEASES.exists():
        return []
    # Last write wins per holder+model, so a re-acquire renews rather than
    # stacking duplicate leases. A RELEASE is a write too, and skipping released
    # records before the fold — which this did — meant a release could never
    # supersede the acquire it was releasing. Caught by
    # tests/test_gpu_arbiter.py::test_leases_expire_and_release_removes_them.
    latest: dict[tuple[str, str], dict] = {}
    for ln in LEASES.open(encoding="utf-8"):
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        latest[(r.get("holder"), r.get("model"))] = r
    return [r for r in latest.values()
            if not r.get("released") and float(r.get("expires_at", 0)) > now]


def _append(rec: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEASES.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def _holder() -> str:
    """Who we are. The messaging socket is the closest thing Claude Code gives
    a session to a stable identity, so use it when present and fall back to the
    pid — a lease from an unknown holder is worse than a coarse one."""
    sock = os.environ.get("CLAUDE_CODE_MESSAGING_SOCKET")
    return f"session:{Path(sock).name}" if sock else f"pid:{os.getpid()}"


def cmd_status(now: float) -> dict:
    loaded, err = resident()
    leases = _read_leases(now)
    return {
        "schema": SCHEMA,
        "enforcement": "advisory",
        "resident": loaded,
        "ollama_error": err,
        "leases": [{"holder": l["holder"], "model": l["model"],
                    "expires_in_s": round(l["expires_at"] - now)}
                   for l in leases],
        "note": ("resident=[] with ollama_error set means the server did not "
                 "answer — that is not the same as nothing being loaded"),
    }


def cmd_advise(models: list[str], now: float) -> dict:
    """Pick from candidates that would all do the job. Resident wins."""
    loaded, err = resident()
    names = [m["name"] for m in loaded]
    base = {name.split(":")[0] for name in names}
    exact = [m for m in models if m in names]
    family = [m for m in models if m not in exact and m.split(":")[0] in base]
    leases = {l["model"] for l in _read_leases(now)}
    choice = (exact or family or models)[0] if models else None
    return {
        "schema": SCHEMA, "choose": choice,
        "reason": ("already resident" if exact else
                   "same family is resident (partial reuse)" if family else
                   "nothing resident — this call pays a load" if not err else
                   "cannot see ollama; falling back to the first candidate"),
        "resident": names, "ollama_error": err,
        "would_evict": [n for n in names if n != choice and n in leases],
        "candidates": models,
    }


def cmd_acquire(model: str, ttl: float, now: float) -> dict:
    leases = _read_leases(now)
    me = _holder()
    conflict = [l for l in leases if l["model"] != model and l["holder"] != me]
    rec = {"holder": me, "model": model, "acquired_at": now,
           "expires_at": now + ttl, "released": False}
    _append(rec)
    return {
        "schema": SCHEMA, "granted": True, "holder": me, "model": model,
        "expires_in_s": round(ttl),
        # Granted regardless: see the docstring — there is no host-side way to
        # make a peer wait, so reporting a refusal we cannot enforce would be a
        # lie dressed as a guarantee.
        "contention": [{"holder": l["holder"], "model": l["model"]}
                       for l in conflict],
        "advice": ("another session holds a different model; loading yours may "
                   "evict theirs" if conflict else "no contention seen"),
    }


def cmd_release(model: str, now: float) -> dict:
    _append({"holder": _holder(), "model": model, "released": True,
             "acquired_at": now, "expires_at": now})
    return {"schema": SCHEMA, "released": True, "model": model}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    a1 = sub.add_parser("advise")
    a1.add_argument("--models", required=True,
                    help="comma list of models that would all do")
    a2 = sub.add_parser("acquire")
    a2.add_argument("--model", required=True)
    a2.add_argument("--ttl", type=float, default=900.0)
    a3 = sub.add_parser("release")
    a3.add_argument("--model", required=True)
    for p in (ap, a1, a2, a3):
        pass
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    now = time.time()
    if a.cmd == "status":
        out = cmd_status(now)
    elif a.cmd == "advise":
        out = cmd_advise([m for m in a.models.split(",") if m], now)
    elif a.cmd == "acquire":
        out = cmd_acquire(a.model, a.ttl, now)
    else:
        out = cmd_release(a.model, now)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
