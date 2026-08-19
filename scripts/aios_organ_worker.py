#!/usr/bin/env python3
"""aios.organ_worker.v1 — the organs execute what they are assigned.

Goal state: the user instructs one session, and agents and OSes distribute the work
between themselves. That was blocked on something simple — the organs held mesh cards but
nothing ran behind them, so an assignment of memory.retrieve landed and stopped. A card
without a process is a promise, and the factory cannot tell the difference until the task
never moves.

Each capability maps to a REAL command in its own repo. Where an organ genuinely cannot do
the thing yet, the handler says so and fails the task with a reason, rather than returning
a plausible nothing. That distinction is the whole point of today: a substrate that could
not answer must not look like one that answered emptily.

Closure still goes through the capability's consumed_by evidence, never through the
command's exit status alone.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_mesh as mesh                                       # noqa: E402
import aios_factory as fac                                     # noqa: E402
import aios_capabilities as caps                               # noqa: E402
import aios_decision_ledger as dl                              # noqa: E402

ART = ROOT / ".aios" / "organ_artifacts"


def _memory_retrieve(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.retrieve.json"
    q = goal.replace('"', "'")[:300]
    return (f'cd "{ROOT}/memoryOS" && python3 -m memoryos --root . context build '
            f'--task "{q}" --json > "{out}" 2>&1',
            # Consumption for a retrieve is a NON-EMPTY pack that carries provenance —
            # not "the command exited 0". The first version guessed the keys (items /
            # context) and failed a working retrieve; memoryOS returns decisions/memories
            # with a trace_id. Guessing a schema and reporting the miss as an organ failure
            # is how a working organ gets written off as dead.
            f'python3 -c "import json,sys;d=json.load(open(\'{out}\'));'
            f'n=sum(len(d.get(k) or []) for k in (\'decisions\',\'memories\',\'items\',\'context\'));'
            f'sys.exit(0 if n and d.get(\'trace_id\') else 1)"')


def _memory_propose(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.propose.json"
    return (f'cd "{ROOT}/memoryOS" && python3 -m memoryos --root . draft add '
            f'--text "{goal[:300]}" --json > "{out}" 2>&1', f'test -s "{out}"')


def _graph_audit(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.audit.txt"
    return (f'python3 "{ROOT}/scripts/aios_graph_audit.py" > "{out}" 2>&1',
            f'grep -q "ORPHANS" "{out}"')


def _capability_recommend(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.route.txt"
    return (f'python3 "{ROOT}/scripts/aios_substrate.py" --report > "{out}" 2>&1',
            f'grep -q "grounded" "{out}"')


def _capability_outcome(goal: str, tid: str) -> tuple[str, str]:
    out = ART / f"{tid}.outcome.txt"
    return (f'python3 "{ROOT}/scripts/aios_decision_ledger.py" policy > "{out}" 2>&1',
            # a routing ledger with no counterfactual is not a ledger yet, and says so
            f'grep -qE "identifiable|empty ledger" "{out}"')


def _grounding_external(goal: str, tid: str) -> tuple[str, str]:
    """myworld owns grounding.external and had no handler, so every task bounced. Owning a
    capability without executing it is worse than not owning it: the router keeps choosing
    you."""
    out = ART / f"{tid}.grounding.json"
    hub = Path.home() / "workspaces" / "jaewon" / "council" / "hub.py"
    q = goal.replace('"', "'")[:300]
    return (f'python3 "{hub}" ask perplexity-api "{q}" > "{out}" 2>&1',
            # consumption still demands a link that RESOLVES — this substrate is known not
            # to provide one, so these will close as produced-but-not-consumed and the
            # ledger will say so rather than flattering the pipeline
            f'python3 -c "import json,re,sys,urllib.request;'
            f'd=json.load(open(\'{out}\'));u=re.findall(r\'https?://[^\\s\\\"]+\',d.get(\'text\') or \'\');'
            f'sys.exit(0 if any(len(x.rstrip(chr(47)).split(chr(47)))>3 for x in u) else 1)"')


def _adversarial_refute(goal: str, tid: str) -> tuple[str, str]:
    """Reads the upstream pack when there is one, so GenesisOS attacks what memoryOS
    actually returned rather than the task title. That difference is the whole point of a
    cross-OS chain."""
    out = ART / f"{tid}.redteam.json"
    hub = Path.home() / "workspaces" / "jaewon" / "council" / "hub.py"
    q = goal.replace('"', "'")[:300]
    ups = [u for u in (os.environ.get("AIOS_UPSTREAM") or "").split(":") if u]
    if ups:
        try:
            d = json.loads(Path(ups[0]).read_text())
            claims = [str(x.get("text") or x.get("summary") or x)[:140]
                      for x in (d.get("decisions") or d.get("memories") or [])[:4]]
            if claims:
                q = (f"{q} — 상류 memoryOS가 회수한 주장들: "
                     + " | ".join(claims))[:900].replace('"', "'")
        except Exception:
            pass
    return (f'python3 "{hub}" redteam "{q}" > "{out}" 2>&1',
            # an adversary that produced nothing evidence-backed did not do the job
            f'python3 -c "import json,sys;d=json.load(open(\'{out}\'));'
            f'sys.exit(0 if (d.get(\'evidence_backed\') or 0) > 0 else 1)"')


ARTIFACT_SUFFIX = {"memory.retrieve": "retrieve.json", "memory.propose": "propose.json",
                   "graph.audit": "audit.txt", "capability.recommend": "route.txt",
                   "capability.record_outcome": "outcome.txt",
                   "grounding.external": "grounding.json",
                   "adversarial.refute": "redteam.json"}


def _artifact_for(cap: str, tid: str) -> Path:
    return ART / f"{tid}.{ARTIFACT_SUFFIX.get(cap, 'out')}"


def _not_yet(name: str):
    def h(goal: str, tid: str) -> tuple[str, str]:
        raise NotImplementedError(
            f"{name} has no implementation in its organ yet. Failing loudly: a handler that "
            f"returned success here would make an organ that does nothing look like one "
            f"that works, which is the exact accounting this system exists to prevent.")
    return h


HANDLERS = {
    "memory.retrieve": _memory_retrieve,
    "memory.propose": _memory_propose,
    "memory.review": _not_yet("memory.review"),
    "capability.recommend": _capability_recommend,
    "capability.record_outcome": _capability_outcome,
    "graph.audit": _graph_audit,
    "grounding.external": _grounding_external,
    "adversarial.refute": _adversarial_refute,
    "execute.receipt": _not_yet("execute.receipt"),
    "execute.verified": _not_yet("execute.verified"),
    "adversarial.reframe": _not_yet("adversarial.reframe"),
}


def work_once(name: str, timeout: int = 600) -> dict | None:
    """PULL: ask for the oldest ready task this worker can actually execute.

    The handler table is the capability claim, so 'assigned something I cannot do' is not
    a state that exists any more — which deletes the release/refuse/TTL path entirely."""
    t = fac.claim_next(name, sorted(HANDLERS))
    if t is not None:
        tid = t["task_id"]
        cap = t["capability"]
        h = HANDLERS.get(cap)
        if h is None:
            # RELEASE, not fail. Two holders can claim the same capability and the factory
            # picks the first; if the one that got it cannot execute, failing the task
            # buries work another holder could do. Releasing puts it back in the queue.
            fac._emit(kind="release", task_id=tid, owner=name,
                      reason=f"{name} holds no handler for {cap} — returning to queue")
            return {"task": tid, "result": f"released ({cap} not mine)"}
        ART.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        # Upstream artifacts, exported so a handler can read what the previous organ
        # produced. AIOS_UPSTREAM is empty for a head-of-chain task, and a handler that
        # requires it must fail rather than pretend — an organ silently ignoring its
        # input is the pipeline version of counting invocation as use.
        ups = fac.artifacts_of(t.get("deps") or [])
        os.environ["AIOS_UPSTREAM"] = ":".join(ups)
        try:
            cmd, check = h(t["goal"], tid)
        except NotImplementedError as e:
            fac._emit(kind="fail", task_id=tid, reason=str(e)[:300])
            dl.record(cap, called=True, trigger="factory", context={"task_id": tid},
                      outcome="unimplemented", consumed=False, note=str(e)[:200])
            return {"task": tid, "capability": cap, "closed": False, "why": "unimplemented"}
        fac._emit(kind="progress", task_id=tid, note=f"{name} executing {cap}")
        try:
            subprocess.run(cmd, shell=True, cwd=ROOT, timeout=timeout, capture_output=True)
        except subprocess.TimeoutExpired:
            fac._emit(kind="fail", task_id=tid, reason=f"exceeded {timeout}s")
            return {"task": tid, "result": "timeout"}
        ok, why = fac.close(tid, check, artifact=str(_artifact_for(cap, tid)))
        spec = caps.CAPABILITIES.get(cap)
        dl.record(cap, called=True, trigger="factory", context={"task_id": tid},
                  cost_ms=int((time.time() - t0) * 1000),
                  outcome="closed" if ok else "refused", consumed=ok,
                  note=(spec.consumed_by[:120] if spec else ""))
        return {"task": tid, "capability": cap, "closed": ok, "why": why}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=os.environ.get("AIOS_MESH_NAME", ""))
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    if not a.name:
        print("need --name", file=sys.stderr); return 2
    mine = [c for c, h in HANDLERS.items()
            if any(c in x.domains for x in mesh.directory() if x.name == a.name)]
    print(f"organ worker {a.name} up; assigned capabilities: {mine or '(none)'}", flush=True)
    while True:
        mesh.heartbeat(a.name)
        r = work_once(a.name)
        if r:
            print(f"[{time.strftime('%H:%M:%S')}] {r}", flush=True)
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
