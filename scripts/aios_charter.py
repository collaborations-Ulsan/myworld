#!/usr/bin/env python3
"""aios.charter.v1 — every refusal owes a next move.

Founder: killing is not the end; hold a GENERATIVE charter.

Everything built today is a negation. Refuse the spawn, refuse the close, refuse the
capability, block the ping-pong, do not cite the unverified, NO-GO the experiment. Each one
is correct and together they make a system that converges on doing nothing — which is
exactly what the numbers said: 42 tasks stalled, four organs with zero commits in a week,
the factory carrying 4 units against my 21.

A charter that only says NO is half a charter. The other half is an OBLIGATION: a negative
finding must emit the work that would make it positive. Not a suggestion in a log line —
an enqueued task, in the same queue, subject to the same gates.

So the kill rules become the generator. The system's refusals are its work list.

    finding                       what it OWES
    -----------------------------------------------------------------------
    capability nobody holds       build a holder for it
    all holders refused           give the owner a handler
    produced but not consumed     replace the path that cannot be consumed
    orphan above threshold        connect it or archive it, with the reason
    dangling reference            repair the citation or drop it
    kill rule fired               write the experiment whose result reopens it
    unverified claim              ground it, with a link that resolves

The obligations are DEDUPED and BOUNDED — a charter that emits work faster than the system
finishes it is a different failure with the same shape as the ping-pong. And obligations
are enqueued at depth+1, so a repair cannot spawn an endless repair-of-repairs.
"""
from __future__ import annotations
import argparse, json, sqlite3, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_factory as fac                                     # noqa: E402
import aios_capabilities as caps                               # noqa: E402
import aios_decision_ledger as dl                              # noqa: E402

GRAPH = Path("/data/jaewon/aios/index/aios.db")
MAX_OBLIGATIONS_PER_SWEEP = 5          # bounded, for the reason in the docstring
ORPHAN_TARGETS = {"hivemind": 0.35, "experiments": 0.20, "docs": 0.02}


def _owe(goal: str, capability: str, depth: int = 1) -> str | None:
    """Enqueue an obligation. Dedup is the factory's; depth keeps repairs from recursing."""
    try:
        return fac.enqueue(goal, capability, depth=depth)
    except Exception as e:
        print(f"    (cannot enqueue: {e})", file=sys.stderr)
        return None


def from_factory() -> list[dict]:
    """Refusals the scheduler already reported, turned into work."""
    out = []
    a = fac.tick(dry=True)
    for key, n in (a.get("unheld_capabilities") or {}).items():
        cap = key.split(" (")[0]
        spec = caps.CAPABILITIES.get(cap)
        owner = spec.owner if spec else "myworld"
        if "all holders refused" in key:
            goal = (f"{owner}에 {cap} 핸들러를 구현한다 — 소유하지만 실행 못 해 "
                    f"{n}건이 되돌아왔다")
        else:
            goal = f"{cap} 보유자를 세운다 — 아무도 갖고 있지 않아 {n}건이 대기한다"
        out.append({"finding": key, "count": n, "goal": goal,
                    "capability": "execute.verified"})
    return out


def from_ledger() -> list[dict]:
    """Capabilities that produce but are never consumed owe a replacement path."""
    out = []
    for k, v in dl.policy_table().items():
        cap, _, trg = k.partition("|")
        if v["called"] >= 3 and (v["consumed_rate"] or 0) == 0.0:
            spec = caps.CAPABILITIES.get(cap)
            out.append({
                "finding": f"{cap} consumed_rate=0 over {v['called']} calls",
                "count": v["called"],
                "goal": (f"{cap} 경로를 소비 가능한 것으로 교체한다 — "
                         f"{v['called']}회 호출에 소비 0. 요구 증거: "
                         f"{(spec.consumed_by if spec else '')[:70]}"),
                "capability": "capability.record_outcome"})
    return out


def from_graph() -> list[dict]:
    """Orphan rates above the targets we wrote down owe a connection or an archive."""
    if not GRAPH.exists():
        return []
    con = sqlite3.connect(f"file:{GRAPH}?mode=ro", uri=True)
    linked = {r for (r,) in con.execute("select src from edges union select dst from edges")}
    out = []
    for layer, target in ORPHAN_TARGETS.items():
        rows = [r for (r,) in con.execute("select id from nodes where layer=?", (layer,))]
        if not rows:
            continue
        orph = [r for r in rows if r not in linked]
        rate = len(orph) / len(rows)
        if rate > target:
            out.append({
                "finding": f"{layer} orphan {rate:.1%} > target {target:.0%}",
                "count": len(orph),
                "goal": (f"{layer} 고아 {len(orph)}건을 잇거나 아카이브한다 (사유 기록). "
                         f"현재 {rate:.1%}, 목표 {target:.0%}"),
                "capability": "graph.audit"})
    con.close()
    return out


def sweep(apply: bool = False) -> dict:
    findings = from_factory() + from_ledger() + from_graph()
    findings.sort(key=lambda f: -f["count"])
    acted, skipped = [], []
    for f in findings:
        if len(acted) >= MAX_OBLIGATIONS_PER_SWEEP:
            skipped.append(f["finding"])
            continue
        tid = _owe(f["goal"], f["capability"]) if apply else "(dry)"
        acted.append({**f, "task_id": tid})
    return {"findings": len(findings), "obligations": acted, "deferred": skipped}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="enqueue the obligations (default: show them)")
    a = ap.parse_args()
    r = sweep(apply=a.apply)
    if not r["findings"]:
        print("아무 부정 소견도 없다 — 갚을 것이 없다는 뜻이지, 잘 돌고 있다는 뜻은 아니다.\n"
              "  (게이트가 아무것도 못 잡는 상태와 잡을 것이 없는 상태는 다르다)")
        return 0
    print(f"{r['findings']} finding(s) → {len(r['obligations'])} obligation(s)"
          f"{' (dry run — pass --apply)' if not a.apply else ''}\n")
    for o in r["obligations"]:
        print(f"  발견  {o['finding']}")
        print(f"  갚음  {o['goal'][:96]}")
        print(f"        → {o['capability']}  {o['task_id']}\n")
    if r["deferred"]:
        print(f"  {len(r['deferred'])} deferred this sweep (cap {MAX_OBLIGATIONS_PER_SWEEP}) — "
              f"emitting faster than we finish is the ping-pong in another shape:")
        for d in r["deferred"]:
            print(f"    · {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
