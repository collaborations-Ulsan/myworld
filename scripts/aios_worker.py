#!/usr/bin/env python3
"""aios.worker.v1 — the end of the loop: a spawned session that actually does the work.

Until this existed the factory dispatched into nothing. Sessions were tmux panes holding a
shell, so assignment looked like progress while the board stayed busy and produced
nothing — the same shape as a capability nobody holds, one level further in.

The worker polls ITS OWN mesh inbox, executes by CAPABILITY, and never asks a model what
to do. The mapping from capability to command is a table: coordination stays algorithmic,
and only the work inside the command is agentic. A worker that decided its own actions
would be a second scheduler with worse guarantees.

Closure goes through aios_factory.close(), which runs a check command and reads its exit
status — so a worker cannot finish a task by believing it did.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_mesh as mesh                                       # noqa: E402
import aios_factory as fac                                     # noqa: E402

HUB = Path.home() / "workspaces" / "jaewon" / "council" / "hub.py"
ART = ROOT / ".aios" / "worker_artifacts"

# capability -> (command builder, check builder). Both are code; neither consults a model
# about WHETHER the work is done.
def _grounding(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.grounding.json"
    q = goal.replace("grounding: ", "")[:400].replace('"', "'")
    return (f'python3 "{HUB}" ask perplexity-api "{q}" > "{out}" 2>&1',
            f'test -s "{out}" && python3 -c "import json,sys;d=json.load(open(\'{out}\'));'
            f'sys.exit(0 if d.get(\'ok\') and len(d.get(\'text\',\'\'))>200 else 1)"')


def _adversarial(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.redteam.json"
    q = goal.replace("adversarial review: ", "")[:400].replace('"', "'")
    return (f'python3 "{HUB}" redteam "{q}" > "{out}" 2>&1',
            f'test -s "{out}" && test $(wc -c < "{out}") -gt 400')


def _docs(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.harvest.log"
    return (f'python3 "{ROOT}/scripts/aios_doc_harvest.py" fetch --provider all '
            f'--limit 40 > "{out}" 2>&1', f'test -s "{out}"')


def _graph(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.graph.txt"
    return (f'python3 "{ROOT}/scripts/aios_graph_audit.py" > "{out}" 2>&1',
            f'grep -q "ORPHANS" "{out}"')


HANDLERS = {"external": _grounding, "grounding": _grounding, "adversarial": _adversarial,
            "docs": _docs, "graph": _graph}


def work_once(name: str, timeout: int = 900) -> dict | None:
    inbox = [m for m in mesh.poll(name) if m.get("state") in ("submitted", "working")]
    tasks = fac.state()
    for msg in inbox:
        tid = (msg.get("body") or {}).get("task_id")
        t = tasks.get(tid)
        if not t or t["state"] != "working" or t["owner"] != name:
            continue
        cap = t["capability"]
        h = HANDLERS.get(cap)
        if h is None:
            fac._emit(kind="fail", task_id=tid,
                      reason=f"no handler for capability {cap!r} — refusing to improvise")
            return {"task": tid, "result": "no handler"}
        ART.mkdir(parents=True, exist_ok=True)
        cmd, check = h(t["goal"], tid)
        fac._emit(kind="progress", task_id=tid, note=f"executing {cap}")
        try:
            subprocess.run(cmd, shell=True, cwd=ROOT, timeout=timeout,
                           capture_output=True)
        except subprocess.TimeoutExpired:
            fac._emit(kind="fail", task_id=tid, reason=f"exceeded {timeout}s")
            return {"task": tid, "result": "timeout"}
        ok, why = fac.close(tid, check)          # closure is a check, not a claim
        return {"task": tid, "capability": cap, "closed": ok, "why": why}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=os.environ.get("AIOS_MESH_NAME", ""))
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    if not a.name:
        print("need --name or AIOS_MESH_NAME", file=sys.stderr); return 2
    print(f"worker {a.name} up; handlers: {sorted(HANDLERS)}", flush=True)
    while True:
        mesh.heartbeat(a.name)
        r = work_once(a.name)
        if r:
            print(f"[{time.strftime('%H:%M:%S')}] {r}", flush=True)
        elif a.once:
            print("nothing assigned to me", flush=True)
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
