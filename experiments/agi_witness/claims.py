"""Shared substrate for the AGI-certification-layer witness experiment.

The 4 certificates (APEX / IRIS / DescentNet / GoEN) and scoring all depend on
this module. It provides three things:

1. ``run_candidate`` — a sandboxed subprocess harness that runs an UNTRUSTED
   candidate program and calls one function in it. Security-sensitive: wall
   timeout, address-space (memory) limit, CPU-time backstop, minimal env, and
   subprocess isolation. Runs O(k*tasks*inputs) times so per-call overhead is
   kept low, but correctness/containment comes first.
2. ``build_claim_graph`` — signed structural graph over a claim set (feeds the
   DescentNet H0/H1 analysis). Edges connect claims that share structure
   (same IO input, shared property, order chain) and carry a +/- sign.
3. Pure utility detectors (``direct_io_conflicts``, ``executable_claims``) and
   JSONL (de)serialization for the ledger.

Constraints: stdlib + numpy only, CPU-only, deterministic (no wall-clock or
unseeded randomness affects any output). Types come from ``contracts.py`` — this
module never redefines Claim / ClaimKind / ExecResult.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any

from contracts import Claim, ClaimKind, ExecResult


# =============================================================================
# 1. Sandboxed execution harness
# =============================================================================

# Runner executed in the child interpreter via ``python -S -B -c <RUNNER> <res>``.
# It reads {"code","func_name","args"} as JSON on stdin, exec's the untrusted
# code in a fresh namespace, calls func_name(*args), and writes the outcome as
# JSON to the result-file path given in argv[1]. Writing to a private temp file
# (rather than stdout) means candidate print()s cannot forge a result. On kill
# (timeout / OOM / SIGXCPU) the file stays absent → the parent classifies it.
_RUNNER = r'''
import sys, json
def _run():
    data = json.loads(sys.stdin.read())
    ns = {"__name__": "__candidate__"}
    exec(compile(data["code"], "<candidate>", "exec"), ns, ns)
    fn = ns[data["func_name"]]
    return fn(*data["args"])
res_path = sys.argv[1]
try:
    payload = {"ok": True, "output": _run()}
except BaseException as e:  # catch SystemExit/MemoryError too, still report
    payload = {"ok": False, "error": "{}: {}".format(type(e).__name__, e)}
try:
    with open(res_path, "w") as f:
        json.dump(payload, f, default=str)  # default=str: never crash on exotic outputs
except Exception:
    pass
'''


def _preexec(mem_mb: int, cpu_s: int):
    """Return a preexec_fn (child-side, pre-exec) that caps memory + CPU and
    isolates the process into its own session so a runaway can be group-killed."""
    def _apply():
        import resource
        mem = mem_mb * 1024 * 1024
        # RLIMIT_AS caps total address space → over-allocation raises MemoryError
        # inside the child (caught + reported) rather than eating the host.
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        # CPU-time backstop: a busy infinite loop hits this even if the wall
        # timeout somehow does not (SIGXCPU). +1s slack over the wall budget.
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        os.setsid()  # detach into a new session/process group
    return _apply


def run_candidate(
    code: str,
    func_name: str,
    args: list,
    *,
    timeout_s: float = 3.0,
    mem_mb: int = 512,
) -> ExecResult:
    """Run untrusted ``code`` in a separate subprocess, call ``func_name(*args)``,
    and return the (json-serialized) result inside an ``ExecResult``.

    Containment (best-effort, defense-in-depth):
      * wall timeout — the process is killed on expiry → ``timed_out=True``;
      * memory limit — ``RLIMIT_AS`` (address space) via ``preexec_fn``;
      * CPU backstop — ``RLIMIT_CPU`` so a hung loop cannot run forever;
      * minimal env — no inherited vars/creds; ``-S`` skips site so nothing
        user-installed is on the path; no network is opened by the harness.
        (True network *blocking* would need namespaces we don't have here —
        isolation + timeout is the honest guarantee, per the spec.)

    Any exception in the candidate → ``ok=False`` with the error string.
    Deterministic: the result depends only on (code, func_name, args).
    """
    payload = json.dumps({"code": code, "func_name": func_name, "args": args})

    # Minimal, fixed environment — no secrets, deterministic hashing.
    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    cpu_s = int(timeout_s) + 1

    res_path = tempfile.mktemp(prefix="agi_exec_", suffix=".json")
    try:
        try:
            proc = subprocess.run(
                [sys.executable, "-S", "-B", "-c", _RUNNER, res_path],
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                preexec_fn=_preexec(mem_mb, cpu_s),
                close_fds=True,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(ok=False, error="wall timeout", timed_out=True)

        # Read the private result file the child wrote.
        try:
            with open(res_path) as f:
                out = json.load(f)
        except Exception:
            # No result written → killed by RLIMIT (OOM/SIGXCPU) or crashed.
            err = (proc.stderr or "").strip()
            err = err[-300:] if err else f"no result (returncode={proc.returncode})"
            return ExecResult(ok=False, error=err)

        if out.get("ok"):
            return ExecResult(ok=True, output=out.get("output"))
        return ExecResult(ok=False, error=out.get("error", "unknown error"))
    finally:
        try:
            os.unlink(res_path)
        except OSError:
            pass


# =============================================================================
# 2. Utility detectors (pure, deterministic, no LLM)
# =============================================================================

def _canon(x: Any) -> str:
    """Canonical, order-stable string form for equality tests (default=str keeps
    non-JSON payload values comparable without crashing)."""
    return json.dumps(x, sort_keys=True, default=str)


def _prop_key_value(payload: dict) -> tuple[Any, Any]:
    """Extract (property-name, asserted-value) from a PROPERTY payload, tolerant
    of the two shapes seeders use: {"prop","value"} or {"name","value"}."""
    name = payload.get("prop", payload.get("name"))
    return name, payload.get("value")


def direct_io_conflicts(claims: list[Claim]) -> list[tuple[int, int]]:
    """H0 conflict primitive (reused by APEX + DescentNet): index pairs (i<j) of
    IO claims on the SAME task with the SAME input but DIFFERENT asserted output."""
    conflicts: list[tuple[int, int]] = []
    io = [
        (i, c) for i, c in enumerate(claims)
        if c.kind == ClaimKind.IO and "input" in c.payload
    ]
    for a in range(len(io)):
        i, ci = io[a]
        for b in range(a + 1, len(io)):
            j, cj = io[b]
            if ci.task_id != cj.task_id:
                continue
            if _canon(ci.payload["input"]) == _canon(cj.payload["input"]) and \
               _canon(ci.payload.get("output")) != _canon(cj.payload.get("output")):
                conflicts.append((i, j))
    return conflicts


def executable_claims(claims: list[Claim]) -> list[int]:
    """Indices of IO claims the harness can run (have an ``input`` list)."""
    return [
        i for i, c in enumerate(claims)
        if c.kind == ClaimKind.IO and isinstance(c.payload.get("input"), list)
    ]


# =============================================================================
# 3. Claim-graph builder (feeds DescentNet H0/H1)
# =============================================================================

def build_claim_graph(claims: list[Claim]) -> dict:
    """Build a signed structural graph over ``claims``.

    An edge connects two SAME-TASK claims that share structure:
      * IO   — same input: ``+1`` if same output (agreement), ``-1`` if different
               (a direct H0 conflict). relation ``io_agree`` / ``io_conflict``.
      * PROPERTY — same property name: ``+1`` if same asserted value, ``-1`` if
               different. relation ``property_agree`` / ``property_conflict``.
      * ORDER — chain link (one claim's ``after`` == another's ``before``):
               ``+1``, relation ``order_chain``. Order cycles (H1 cyclic
               frustration, e.g. a->b->c->a) surface as a cycle in these edges.

    Returns ``{"nodes", "edges", "adjacency"}``:
      * ``nodes``   — per-claim metadata (index, task_id, source_id, kind).
        NOTE: ``poisoned`` is DELIBERATELY excluded — this graph feeds a
        certificate (DescentNet) and certificates must not read ground truth.
      * ``edges``   — list of ``{"u","v","sign","relation"}`` (u < v).
      * ``adjacency`` — ``{idx: [{"to","sign","relation"}, ...]}`` (both directions).
    """
    nodes = [
        {"idx": i, "task_id": c.task_id, "source_id": c.source_id, "kind": c.kind.value}
        for i, c in enumerate(claims)
    ]
    edges: list[dict] = []

    def _add(u: int, v: int, sign: int, relation: str) -> None:
        lo, hi = (u, v) if u < v else (v, u)
        edges.append({"u": lo, "v": hi, "sign": sign, "relation": relation})

    # --- IO edges: group same-task claims by canonical input ---
    io_groups: dict[tuple, list[int]] = {}
    for i in executable_claims(claims):
        c = claims[i]
        io_groups.setdefault((c.task_id, _canon(c.payload["input"])), []).append(i)
    for group in io_groups.values():
        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                i, j = group[a], group[b]
                same_out = _canon(claims[i].payload.get("output")) == \
                    _canon(claims[j].payload.get("output"))
                _add(i, j, 1 if same_out else -1,
                     "io_agree" if same_out else "io_conflict")

    # --- PROPERTY edges: group same-task claims by property name ---
    prop_groups: dict[tuple, list[int]] = {}
    for i, c in enumerate(claims):
        if c.kind == ClaimKind.PROPERTY:
            name, _ = _prop_key_value(c.payload)
            prop_groups.setdefault((c.task_id, _canon(name)), []).append(i)
    for group in prop_groups.values():
        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                i, j = group[a], group[b]
                _, vi = _prop_key_value(claims[i].payload)
                _, vj = _prop_key_value(claims[j].payload)
                same_val = _canon(vi) == _canon(vj)
                _add(i, j, 1 if same_val else -1,
                     "property_agree" if same_val else "property_conflict")

    # --- ORDER edges: chain links (after == before), same task ---
    order = [
        (i, c) for i, c in enumerate(claims)
        if c.kind == ClaimKind.ORDER and "before" in c.payload and "after" in c.payload
    ]
    for a in range(len(order)):
        i, ci = order[a]
        for b in range(len(order)):
            if a == b:
                continue
            j, cj = order[b]
            if ci.task_id != cj.task_id:
                continue
            # directed link ci: (before->after) then cj: (before->after)
            if _canon(ci.payload["after"]) == _canon(cj.payload["before"]):
                _add(i, j, 1, "order_chain")

    # De-duplicate order edges (undirected _add can add the same pair twice).
    seen = set()
    deduped = []
    for e in edges:
        key = (e["u"], e["v"], e["relation"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)
    edges = deduped

    adjacency: dict[int, list[dict]] = {i: [] for i in range(len(claims))}
    for e in edges:
        adjacency[e["u"]].append({"to": e["v"], "sign": e["sign"], "relation": e["relation"]})
        adjacency[e["v"]].append({"to": e["u"], "sign": e["sign"], "relation": e["relation"]})

    return {"nodes": nodes, "edges": edges, "adjacency": adjacency}


# =============================================================================
# 4. JSONL (de)serialization for the ledger
# =============================================================================

def claim_to_dict(c: Claim) -> dict:
    """Serialize a Claim to a plain JSON-safe dict (enum -> its string value)."""
    return {
        "task_id": c.task_id,
        "source_id": c.source_id,
        "kind": c.kind.value,
        "payload": c.payload,
        "ts": c.ts,
        "poisoned": c.poisoned,
    }


def claim_from_dict(d: dict) -> Claim:
    """Reconstruct a Claim from a dict produced by ``claim_to_dict``."""
    return Claim(
        task_id=d["task_id"],
        source_id=d["source_id"],
        kind=ClaimKind(d["kind"]),
        payload=d["payload"],
        ts=d.get("ts", 0),
        poisoned=d.get("poisoned", False),
    )


def claims_to_jsonl(claims: list[Claim], path: str) -> None:
    """Write claims to ``path`` as JSONL (one claim per line), sorted by (ts, task_id)
    for a deterministic ledger file."""
    ordered = sorted(claims, key=lambda c: (c.ts, c.task_id, c.source_id))
    with open(path, "w") as f:
        for c in ordered:
            f.write(json.dumps(claim_to_dict(c), sort_keys=True) + "\n")


def claims_from_jsonl(path: str) -> list[Claim]:
    """Read a JSONL ledger written by ``claims_to_jsonl`` back into Claims."""
    out: list[Claim] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(claim_from_dict(json.loads(line)))
    return out


# =============================================================================
# Self-test
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("claims.py self-test")
    print("=" * 70)

    # --- Build a small claim set --------------------------------------------
    # Two IO claims on task t1 with the SAME input but DIFFERENT output = a
    # direct H0 conflict (one of them is poisoned ground-truth, hidden from certs).
    # Plus an ORDER cycle a->b->c->a on task t2 (H1 cyclic frustration).
    claims = [
        Claim("t1", "srcA", ClaimKind.IO, {"input": [2, 3], "output": 5}, ts=0),
        Claim("t1", "srcB", ClaimKind.IO, {"input": [2, 3], "output": 6}, ts=1,
              poisoned=True),                                   # conflicts with above
        Claim("t1", "srcC", ClaimKind.IO, {"input": [2, 3], "output": 5}, ts=2),  # agrees w/ srcA
        Claim("t1", "srcA", ClaimKind.PROPERTY, {"prop": "return_type", "value": "int"}, ts=3),
        Claim("t1", "srcB", ClaimKind.PROPERTY, {"prop": "return_type", "value": "str"}, ts=4,
              poisoned=True),                                   # property conflict
        Claim("t2", "srcA", ClaimKind.ORDER, {"before": "a", "after": "b"}, ts=5),
        Claim("t2", "srcB", ClaimKind.ORDER, {"before": "b", "after": "c"}, ts=6),
        Claim("t2", "srcC", ClaimKind.ORDER, {"before": "c", "after": "a"}, ts=7),  # closes cycle
    ]

    # --- Harness: correct / timeout / error ---------------------------------
    good_code = "def add(a, b):\n    return a + b\n"
    loop_code = "def spin():\n    while True:\n        pass\n"
    err_code = "def boom():\n    return 1 / 0\n"

    r_good = run_candidate(good_code, "add", [2, 3])
    r_loop = run_candidate(loop_code, "spin", [], timeout_s=1.0)
    r_err = run_candidate(err_code, "boom", [])

    print("\n[run_candidate]")
    print(f"  correct add(2,3) -> ok={r_good.ok} output={r_good.output!r} "
          f"timed_out={r_good.timed_out} error={r_good.error!r}")
    print(f"  infinite loop    -> ok={r_loop.ok} timed_out={r_loop.timed_out} "
          f"error={r_loop.error!r}")
    print(f"  1/0 error        -> ok={r_err.ok} timed_out={r_err.timed_out} "
          f"error={r_err.error!r}")

    assert r_good.ok and r_good.output == 5, "correct program must succeed"
    assert (not r_loop.ok) and r_loop.timed_out, "infinite loop must time out"
    assert (not r_err.ok) and (not r_err.timed_out) and "ZeroDivision" in (r_err.error or ""), \
        "error program must report the exception"

    # --- Detectors ----------------------------------------------------------
    conflicts = direct_io_conflicts(claims)
    execs = executable_claims(claims)
    print("\n[direct_io_conflicts]", conflicts, "(expect (0, 1))")
    print("[executable_claims]  ", execs, "(indices 0,1,2 are runnable IO)")
    assert (0, 1) in conflicts, "same-input/different-output IO pair must conflict"
    assert execs == [0, 1, 2], "the three IO claims must be executable"

    # --- Claim graph --------------------------------------------------------
    g = build_claim_graph(claims)
    print("\n[claim graph] nodes:", len(g["nodes"]), " edges:", len(g["edges"]))
    for e in g["edges"]:
        print(f"    {e['u']}--{e['v']}  sign={e['sign']:+d}  {e['relation']}")

    io_conflict_edges = [e for e in g["edges"] if e["relation"] == "io_conflict"]
    order_edges = [e for e in g["edges"] if e["relation"] == "order_chain"]
    assert any(e["u"] == 0 and e["v"] == 1 and e["sign"] == -1 for e in io_conflict_edges), \
        "graph must carry the 0--1 io_conflict edge with sign -1"
    assert len(order_edges) == 3, "the a->b->c->a cycle must yield 3 order-chain edges"
    print(f"\n  io_conflict edges: {len(io_conflict_edges)} (the -1 conflict edge)")
    print(f"  order_chain edges: {len(order_edges)} (forms the a->b->c->a H1 cycle)")

    # --- Ledger round-trip ---------------------------------------------------
    tmp = tempfile.mktemp(prefix="agi_claims_", suffix=".jsonl")
    claims_to_jsonl(claims, tmp)
    back = claims_from_jsonl(tmp)
    os.unlink(tmp)
    assert len(back) == len(claims) and back[0].kind == ClaimKind.IO, "JSONL round-trip"
    print("\n[jsonl] round-trip OK:", len(back), "claims")

    print("\nALL SELF-TEST ASSERTIONS PASSED")
