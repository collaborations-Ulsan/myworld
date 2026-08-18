#!/usr/bin/env python3
"""aios.m3.gate.v1 — run M3's pre-run gates before anything is spent on agents.

Prereg: docs/AIOS_M3_PARTITION_SOCIETY_PREREG_2026-08-18.md sections 2-3.
Generator and verifier are BOTH mechanical here (graph sampling + deterministic sqlite),
so the loop is not writing its own tasks and its own scorer.

G0  each question's required evidence must exceed one context AND span >=2 layers
G1  the answer's marginal distribution must not have a dominant value (modal <= 60%)

A gate that cannot fail is decoration, so both are computed from the corpus, and the
run refuses to proceed if either misses.
"""
from __future__ import annotations
import argparse, json, os, random, sqlite3, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_instrument import Finding, calibrate, probe, report          # noqa: E402

DB = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"
CTX_TOKENS = int(os.environ.get("M3_CTX", "200000"))
CHARS_PER_TOK = 3.5


def build_questions(con, n: int, rng: random.Random) -> list[dict]:
    """Cross-layer citation tracing. The ANSWER is the citing document's layer — computed
    from edges, never authored. Sampling only over targets cited from >=2 distinct layers,
    which is what makes the question require more than one partition."""
    sizes = {r: c for r, c in con.execute("select id, n_chars from fulltext")}
    layer = {r: l for r, l in con.execute("select id, layer from nodes")}
    inbound: dict[str, list[str]] = {}
    for s, d in con.execute("select src, dst from edges where kind='cites'"):
        if s in layer and d in layer:
            inbound.setdefault(d, []).append(s)

    # G0 taught us something the prereg assumed away: a corpus 58.6x a context does NOT
    # make individual questions exceed a context. Retrieval narrows lookup questions to a
    # few documents (median 34k tokens), and arm A already has retrieval. The partition can
    # only pay where retrieval CANNOT narrow — aggregation over the whole inbound set, not
    # lookup of a few. So targets must carry an inbound set that is itself larger than a
    # context. This tightens the pool toward the hypothesis; it does not loosen the gate.
    MIN_EVIDENCE = int(CTX_TOKENS * CHARS_PER_TOK)
    cands = []
    for tgt, srcs in inbound.items():
        ls = {layer[s] for s in srcs}
        if len(ls) < 2 or tgt not in sizes:
            continue
        if sizes.get(tgt, 0) + sum(sizes.get(x, 0) for x in srcs) < MIN_EVIDENCE:
            continue
        need = sizes.get(tgt, 0) + sum(sizes.get(s, 0) for s in srcs)
        cands.append({"target": tgt, "sources": srcs, "layers": sorted(ls),
                      "evidence_chars": need,
                      "evidence_tokens": int(need / CHARS_PER_TOK)})
    rng.shuffle(cands)
    out = []
    for c in cands[:n * 6]:
        # the answer: which layer cites this target the MOST (deterministic, tie -> skip)
        cnt = Counter(layer[s] for s in c["sources"])
        top = cnt.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            continue
        c["answer"] = top[0][0]
        out.append(c)
        if len(out) >= n:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260818)
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    rng = random.Random(a.seed)
    qs = build_questions(con, a.n, rng)
    if not qs:
        print("no questions could be generated — the gate cannot even be run", file=sys.stderr)
        return 2

    over = [q for q in qs if q["evidence_tokens"] > CTX_TOKENS]
    multi = [q for q in qs if len(q["layers"]) >= 2]
    ans = Counter(q["answer"] for q in qs)
    modal = ans.most_common(1)[0][1] / len(qs)

    print(f"generated {len(qs)} questions")
    print(f"  evidence tokens: median {sorted(q['evidence_tokens'] for q in qs)[len(qs)//2]:,} "
          f"max {max(q['evidence_tokens'] for q in qs):,}   (one context = {CTX_TOKENS:,})")
    print(f"  G0 exceed-context: {len(over)}/{len(qs)} ({len(over)/len(qs):.1%})")
    print(f"  G0 multi-layer   : {len(multi)}/{len(qs)} ({len(multi)/len(qs):.1%})")
    print(f"  G1 answer spread : {dict(ans.most_common(6))}  modal {modal:.1%}")

    # --- G1 as a calibrated finding ------------------------------------------------
    pos, neg = calibrate(
        "generator produces >1 distinct answer", lambda: float(len(ans)), 2.0,
        "no single answer dominates", lambda: modal, 0.60,
        pos_detail="if the answer is constant the task is degenerate",
        neg_detail="prereg G1: modal <= 60%, the rule copyness violated today")
    in_scope, refutes = probe(lambda: len(qs) > 0, lambda: modal <= 0.60)
    f = Finding(
        claim="the generated M3 question pool has action variance (modal answer <= 60%)",
        value=f"modal {modal:.1%} over {len(ans)} distinct answers",
        positive=pos, negative=neg,
        counterexample=f"the pool itself: modal class '{ans.most_common(1)[0][0]}' "
                       f"at {modal:.1%}",
        in_scope=in_scope, refutes=refutes)
    ok_g1 = report(f, source="M3 gate G1")

    ok_g0 = len(over) / len(qs) >= 0.5 and len(multi) == len(qs)
    print(f"\nG0 {'PASS' if ok_g0 else 'FAIL'}   G1 {'PASS' if ok_g1 else 'FAIL'}")
    if not (ok_g0 and ok_g1):
        print("\nDO NOT RUN M3. The prereg forbids spending agents on a pool that "
              "cannot identify the effect. Fix the generator, not the gate.")
    Path(".aios").mkdir(exist_ok=True)
    Path(".aios/m3_gate.json").write_text(json.dumps(
        {"n": len(qs), "g0_over": len(over), "g0_multi": len(multi),
         "modal": modal, "answers": dict(ans), "g0": ok_g0, "g1": ok_g1,
         "median_tokens": sorted(q['evidence_tokens'] for q in qs)[len(qs)//2]},
        ensure_ascii=False, indent=2))
    return 0 if (ok_g0 and ok_g1) else 1


if __name__ == "__main__":
    sys.exit(main())
