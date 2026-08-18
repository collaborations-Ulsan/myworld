#!/usr/bin/env python3
"""aios.m3.arms.v1 — the three arms of the partition-society experiment.

Prereg: docs/AIOS_M3_PARTITION_SOCIETY_PREREG_2026-08-18.md (frozen).
Gates already passed: G0 200/200 exceed one context, G1 modal 51.0% <= 60%.

  A  one agent + retrieval over the whole corpus   (the real control: no information is
                                                    withheld, it just has to find it)
  B  one agent + the best context compression      (the arm that decides the experiment —
                                                    without it a win only rediscovers
                                                    summarisation)
  C  N partitioned specialists + a router          (the hypothesis)

Arm C is built on today's pieces rather than a private mechanism: aios_spawn admits a
specialist only if the machine can hold it, aios_mesh gives it an A2A card, and the router
is mesh.who_knows() — the question the 40 visible sessions could not answer this morning.

The prereg requires arm B to be implemented by someone with no stake in C. That constraint
is NOT satisfied by this file, so B here is a placeholder that refuses to run and says so.
Reporting a C-vs-B number computed from a B I wrote to lose would be the exact failure the
prereg's section 5 exists to prevent.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_mesh as mesh                                        # noqa: E402
import aios_substrate as sub                                    # noqa: E402
from aios_m3_gate import build_questions, DB                    # noqa: E402

OUT = ROOT / ".aios" / "m3"
LAYERS = ("docs", "hivemind", "experiments", "uri", "memoryOS", "scripts", ".aios")


# ---------------------------------------------------------------- arm C: partition + route
def ensure_specialists(spawn: bool = False) -> dict[str, str]:
    """One specialist per corpus layer. Registration is the mesh's job; this only names
    the mapping and (optionally) brings the sessions up through the admission gate."""
    import aios_spawn
    live = {c.name: c for c in mesh.directory()}
    out = {}
    for layer in LAYERS:
        label = f"m3-{layer.strip('.').lower()}"
        name = f"claude@{ROOT.name}/reader-{label}"
        if name not in live and spawn:
            try:
                aios_spawn.spawn("reader", label, domains=[layer, "m3"], lease_s=10800)
            except SystemExit as e:
                print(f"  {layer}: admission refused — {e}", file=sys.stderr)
                continue
        out[layer] = name
    return out


def route(question: dict, specialists: dict[str, str]) -> list[str]:
    """The router. Sends a question only to the partitions its evidence actually lives in —
    which is the whole claim: a specialist is addressable by what it holds."""
    picked = []
    for layer in question["layers"]:
        if layer in specialists:
            picked.append(specialists[layer])
        else:                                    # fall back to the mesh's own index
            hits = mesh.who_knows(layer)
            if hits:
                picked.append(hits[0].name)
    return picked or list(specialists.values())[:1]


def arm_C(questions: list[dict], specialists: dict[str, str], model: str) -> list[dict]:
    con = sqlite3.connect(DB)
    sizes = {r: n for r, n in con.execute("select id, n_chars from fulltext")}
    layer_of = {r: l for r, l in con.execute("select id, layer from nodes")}
    rows = []
    for q in questions:
        targets = route(q, specialists)
        # each specialist sees ONLY its own partition of the evidence
        votes = []
        for layer in q["layers"]:
            ev = [s for s in q["sources"] if layer_of.get(s) == layer]
            budget = sum(sizes.get(s, 0) for s in ev)
            votes.append({"layer": layer, "n_evidence": len(ev), "chars": budget})
        # the aggregate the router computes — no single specialist could compute it
        best = max(votes, key=lambda v: v["n_evidence"])["layer"] if votes else ""
        rows.append({"arm": "C", "target": q["target"], "answer": best,
                     "truth": q["answer"], "correct": best == q["answer"],
                     "routed_to": targets, "partitions": len(q["layers"]),
                     "max_partition_chars": max((v["chars"] for v in votes), default=0)})
    return rows


def arm_A(questions: list[dict]) -> list[dict]:
    """One agent, whole corpus, but a real context bound. Retrieval must fit what it finds
    into one window; when the evidence does not fit, it sees a truncated slice — which is
    the entire reason this experiment exists."""
    con = sqlite3.connect(DB)
    sizes = {r: n for r, n in con.execute("select id, n_chars from fulltext")}
    layer_of = {r: l for r, l in con.execute("select id, layer from nodes")}
    CTX_CHARS = 200_000 * 3.5
    rows = []
    for q in questions:
        seen, used = [], 0.0
        for s in q["sources"]:                   # retrieval order = as stored; no oracle peek
            c = sizes.get(s, 0)
            if used + c > CTX_CHARS:
                continue
            used += c
            seen.append(s)
        cnt = Counter(layer_of.get(s, "?") for s in seen)
        best = cnt.most_common(1)[0][0] if cnt else ""
        rows.append({"arm": "A", "target": q["target"], "answer": best,
                     "truth": q["answer"], "correct": best == q["answer"],
                     "evidence_seen": len(seen), "evidence_total": len(q["sources"]),
                     "truncated": len(seen) < len(q["sources"])})
    return rows


def arm_B(questions: list[dict]) -> list[dict]:
    raise SystemExit(
        "arm B is not implemented here BY DESIGN.\n"
        "  Prereg section 5.2: B must be implemented by a person or substrate with no stake "
        "in C, and not weakened to make C win.\n"
        "  A C-vs-B number computed from a B written by C's author is exactly the failure "
        "section 5 exists to prevent. Dispatch it to myworld_computation or another "
        "substrate, then run `compare`.")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub_ = ap.add_subparsers(dest="subcmd", required=True)
    r = sub_.add_parser("run"); r.add_argument("--arm", choices=["A", "B", "C"], required=True)
    r.add_argument("--n", type=int, default=200); r.add_argument("--spawn", action="store_true")
    r.add_argument("--model", default="qwen3.8:27b")
    sub_.add_parser("compare")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if a.subcmd == "run":
        import random
        qs = build_questions(sqlite3.connect(DB), a.n, random.Random(20260818))
        print(f"{len(qs)} questions (same seed as the gate — identical pool)")
        if a.arm == "B":
            arm_B(qs)
        specialists = ensure_specialists(spawn=a.spawn) if a.arm == "C" else {}
        if a.arm == "C":
            print(f"specialists: {len(specialists)} layers")
        rows = arm_C(qs, specialists, a.model) if a.arm == "C" else arm_A(qs)
        acc = sum(r["correct"] for r in rows) / len(rows)
        if a.arm == "C" and acc > 0.99:
            print("  WARNING: accuracy at ceiling. Arm C's aggregation is the ground-truth "
                  "definition here, so this is an identity, not a result. Mechanism check "
                  "only — do not quote as performance.")
        (OUT / f"arm_{a.arm}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        print(f"arm {a.arm}: accuracy {acc:.3f} ({sum(r['correct'] for r in rows)}/{len(rows)})")
        if a.arm == "A":
            t = sum(r["truncated"] for r in rows)
            print(f"  truncated by context: {t}/{len(rows)} ({t/len(rows):.1%})")
    elif a.subcmd == "compare":
        have = {p.stem[-1]: [json.loads(l) for l in p.read_text().splitlines() if l]
                for p in OUT.glob("arm_*.jsonl")}
        if "B" not in have:
            print("REFUSING to report C vs A as the result.\n"
                  "  The prereg's primary contrast is C vs B, and B is not run. "
                  "C beating A only shows that partitioning beats a truncated single "
                  "context — which is what the design already assumes.")
        for arm, rows in sorted(have.items()):
            acc = sum(r["correct"] for r in rows) / len(rows)
            print(f"  arm {arm}: {acc:.3f}  n={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
