#!/usr/bin/env python3
"""aios_keystone_bench — does the AIOS commons/DescentNet CAUSALLY beat a frequency
baseline at predicting held-out agent actions? (the AGI-thesis keystone, first rung)

Honest first measurement of Codex's keystone challenge: show the AIOS layer causally
improves over a vanilla baseline. Here, on a well-defined proxy — next-action prediction:
- held-out cases (context → true next tool) from RECENT CLI sessions (not in the trained
  memory), so it is out-of-sample;
- BASELINE = frequency-only ranking (base rates — a vanilla/RAG-like retrieval proxy);
- AIOS     = frequency × DescentNet (the sheaf-cohomology moat), use_global optional;
- metric   = top-1 / top-3 accuracy + the DELTA (AIOS − baseline). A positive, stable
  delta is causal evidence the moat adds predictive power; ~0 is an honest null (rule 9).

This is a first rung, NOT a publishable result: single machine, one task class (tool
prediction, not task-success/calibration/recovery), modest N. It measures signal, not proof.

CLI: aios keystone-bench [--cases N] [--global] [--json]
"""
from __future__ import annotations
import os, sys, json, argparse, random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_agent_behavior as B  # noqa: E402

def _sessions(limit_files: int = 120) -> list[list[str]]:
    root = Path.home() / ".claude" / "projects"
    files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    seqs = []
    for f in files[:limit_files]:
        try:
            tools = B._clean_tools(B._parse_claude_session(f))
        except Exception:
            tools = []
        if len(tools) >= 4:
            seqs.append(tools)
    return seqs

def _cases(seqs: list[list[str]], n: int, seed_offset: int = 0):
    """Held-out (context, prev, candidates, true) — candidates = tool vocabulary."""
    vocab = sorted({t for s in seqs for t in s})
    pool = []
    for s in seqs:
        for i in range(2, len(s)):
            pool.append((" → ".join(s[:i])[-400:], s[i - 1], s[i]))
    # deterministic sample (no Math.random dependence): stride the pool
    if len(pool) > n:
        step = max(1, len(pool) // n)
        pool = [pool[(i * step + seed_offset) % len(pool)] for i in range(n)]
    return vocab, pool

def _rank_baseline(candidates, mems):
    sc = B._frequency_scores(candidates, mems)
    return sorted(candidates, key=lambda c: sc.get(c, 0.0), reverse=True)

def _rank_aios(context, candidates, prev, use_global):
    r = B.predict_behavior(context, candidates, top_k=len(candidates),
                           use_global=use_global, prev_tool=prev)
    return [x["action"] for x in r.get("ranked", [])]

def run(n_cases: int = 300, use_global: bool = False) -> dict:
    seqs = _sessions()
    mems = B.load_behavior_memories()
    vocab, cases = _cases(seqs, n_cases)
    if not cases:
        return {"error": "no held-out cases"}
    base_t1 = base_t3 = ai_t1 = ai_t3 = 0
    for ctx, prev, true in cases:
        b = _rank_baseline(vocab, mems)
        a = _rank_aios(ctx, vocab, prev, use_global)
        base_t1 += (b[:1] == [true]); base_t3 += (true in b[:3])
        ai_t1 += (a[:1] == [true]);   ai_t3 += (true in a[:3])
    N = len(cases)
    return {
        "cases": N, "vocab_size": len(vocab), "descentnet_loaded": B.DESCENTNET is not None,
        "use_global": use_global,
        "baseline_top1": round(base_t1 / N, 3), "baseline_top3": round(base_t3 / N, 3),
        "aios_top1": round(ai_t1 / N, 3), "aios_top3": round(ai_t3 / N, 3),
        "delta_top1": round((ai_t1 - base_t1) / N, 3), "delta_top3": round((ai_t3 - base_t3) / N, 3),
    }

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aios keystone-bench")
    ap.add_argument("--cases", type=int, default=300)
    ap.add_argument("--global", dest="use_global", action="store_true",
                    help="include the live global commons (slower: per-case network)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = run(a.cases, a.use_global)
    if a.json:
        print(json.dumps(r, indent=2)); return 0
    if r.get("error"):
        print(r["error"]); return 1
    print(f"\n✦ AIOS keystone benchmark — next-action prediction (held-out, N={r['cases']})")
    print(f"  DescentNet loaded: {r['descentnet_loaded']} · vocab {r['vocab_size']} · global {r['use_global']}\n")
    print(f"  {'arm':<22}{'top-1':>8}{'top-3':>8}")
    print(f"  {'frequency baseline':<22}{r['baseline_top1']:>8}{r['baseline_top3']:>8}")
    print(f"  {'AIOS (freq×descent'+('×global)' if r['use_global'] else ')'):<22}{r['aios_top1']:>8}{r['aios_top3']:>8}")
    d1, d3 = r["delta_top1"], r["delta_top3"]
    print(f"  {'Δ (AIOS − baseline)':<22}{d1:>+8}{d3:>+8}")
    verdict = ("✓ AIOS layer adds predictive power (positive delta)" if (d1 > 0.01 or d3 > 0.01)
               else "≈ honest null on this rung — the layer does not beat frequency here"
               if (abs(d1) <= 0.01 and abs(d3) <= 0.01)
               else "✗ AIOS underperforms baseline here (investigate)")
    print(f"\n  {verdict}")
    print("  (first rung: tool-prediction proxy, one machine, modest N — signal, not proof.)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
