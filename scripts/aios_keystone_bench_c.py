#!/usr/bin/env python3
"""Rung 1 — Experiment C (blend fix). Rung 0 showed the AIOS arm (freq+descent)
badly underperformed a frequency baseline at held-out next-action prediction. Was
the *blend* broken? Here we hold retrieval + freq + descent FIXED and vary only how
freq and descent are combined, measuring top-1/3 accuracy for each variant on a
clean held-out (time-split) set.

Held-out cleanliness: cases are drawn ONLY from claude sessions whose filename is
NOT in any memory's evidence_refs (never ingested). Reports N + per-arm top-1/3.

Arms:
  full_freq      : frequency over the WHOLE corpus (Rung 0 baseline reference)
  retr_freq      : frequency over the top-K retrieved memories (retrieval only)
  retr_freq_tr   : retr_freq + transition P(cand|prev) (predict minus descent)
  additive       : 0.6*freq + 0.4*descent   (the current predict_behavior blend)
  mult           : freq * descent           (multiplicative)
  rrf            : reciprocal-rank-fusion(freq_rank, descent_rank)
  gated          : descent breaks ties only when freq top-1 margin is small
  descent_only   : descent alone (sanity floor)
"""
from __future__ import annotations
import os, sys, json, argparse, hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_agent_behavior as B  # noqa: E402

MEM = B.load_behavior_memories()
# filenames already ingested → excluded from held-out cases
_INGESTED = set()
for m in MEM:
    for r in m.get("evidence_refs", []):
        if isinstance(r, str) and r.startswith("session:"):
            _INGESTED.add(r.split("session:", 1)[1])

_EMB: dict[str, list[float]] = {}
_CACHE = B._load_embed_cache()


def _embed(text: str) -> list[float] | None:
    key = "ctx:" + hashlib.sha256(text.encode()).hexdigest()[:16]
    if key in _CACHE:
        return _CACHE[key]
    if key in _EMB:
        return _EMB[key]
    v = B._embed_batch([text[:400]])
    if not v:
        return None
    _EMB[key] = v[0]
    _CACHE[key] = v[0]
    return v[0]


def _mem_embed(m: dict) -> list[float] | None:
    k = "mem:" + m["id"]
    if k in _CACHE:
        return _CACHE[k]
    if k in _EMB:
        return _EMB[k]
    v = B._embed_batch([m.get("content", "")[:400]])
    if not v:
        return None
    _EMB[k] = v[0]
    _CACHE[k] = v[0]
    return v[0]


def held_out_sessions(limit_files: int = 400) -> list[list[str]]:
    root = Path.home() / ".claude" / "projects"
    files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    seqs = []
    for f in files:
        if f.name in _INGESTED:
            continue
        try:
            tools = B._clean_tools(B._parse_claude_session(f))
        except Exception:
            tools = []
        if len(tools) >= 4:
            seqs.append(tools)
        if len(seqs) >= limit_files:
            break
    return seqs


def build_cases(seqs, n):
    vocab = sorted({t for s in seqs for t in s})
    pool = []
    for s in seqs:
        for i in range(2, len(s)):
            pool.append((" → ".join(s[:i])[-400:], s[i - 1], s[i]))
    if len(pool) > n:
        step = max(1, len(pool) // n)
        pool = [pool[(i * step) % len(pool)] for i in range(n)]
    return vocab, pool


def retrieve(ctx: str, k: int = 6) -> list[dict]:
    cv = _embed(ctx)
    if cv is None:
        return MEM[:k]
    scored = []
    for m in MEM:
        mv = _mem_embed(m)
        if mv is None:
            continue
        scored.append((B._cosine(cv, mv), m))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [m for _, m in scored[:k]]


def _rank_by(scores: dict) -> list[str]:
    return sorted(scores, key=lambda c: scores.get(c, 0.0), reverse=True)


def _rrf(rank_lists: list[list[str]], candidates: list[str], k0: int = 60) -> dict:
    sc = {c: 0.0 for c in candidates}
    for rl in rank_lists:
        for pos, c in enumerate(rl):
            sc[c] += 1.0 / (k0 + pos + 1)
    return sc


def run(n_cases: int = 150, k_retr: int = 6) -> dict:
    seqs = held_out_sessions()
    vocab, cases = build_cases(seqs, n_cases)
    if not cases:
        return {"error": "no held-out cases"}

    full_freq = B._frequency_scores(vocab, MEM)  # whole-corpus freq (fixed per run)
    full_freq_rank = _rank_by(full_freq)

    arms = ["full_freq", "retr_freq", "retr_freq_tr", "additive", "mult",
            "rrf", "gated", "descent_only"]
    t1 = {a: 0 for a in arms}
    t3 = {a: 0 for a in arms}

    for ctx, prev, true in cases:
        mems = retrieve(ctx, k_retr)
        clean = [m for m in mems if m.get("loop_type") != "doom_loop"]
        fs = B._frequency_scores(vocab, clean)
        ds, _obs = B._descent_scores(ctx, vocab, mems)
        ts = B._transition_scores(prev, vocab, mems) if prev else {}

        ranks = {}
        ranks["full_freq"] = full_freq_rank
        ranks["retr_freq"] = _rank_by(fs)
        ranks["retr_freq_tr"] = _rank_by({c: 0.6 * fs.get(c, 0) + 0.4 * ts.get(c, 0) for c in vocab}) if ts \
            else _rank_by(fs)
        ranks["additive"] = _rank_by({c: 0.6 * fs.get(c, 0) + 0.4 * ds.get(c, 0.5) for c in vocab})
        ranks["mult"] = _rank_by({c: (fs.get(c, 0) + 1e-6) * ds.get(c, 0.5) for c in vocab})
        ranks["rrf"] = _rank_by(_rrf([_rank_by(fs), _rank_by(ds)], vocab))
        # gated: use freq; only if freq top-1 margin < 0.05, let descent reorder top-3
        fr = _rank_by(fs)
        if len(fr) >= 2 and (fs.get(fr[0], 0) - fs.get(fr[1], 0)) < 0.05:
            top = fr[:3]
            ranks["gated"] = sorted(top, key=lambda c: ds.get(c, 0.5), reverse=True) + fr[3:]
        else:
            ranks["gated"] = fr
        ranks["descent_only"] = _rank_by(ds)

        for a in arms:
            r = ranks[a]
            t1[a] += (r[:1] == [true])
            t3[a] += (true in r[:3])

    B._save_embed_cache(_CACHE)
    N = len(cases)
    return {
        "N": N, "vocab": len(vocab), "k_retr": k_retr,
        "held_out_sessions": len(seqs), "ingested_excluded": len(_INGESTED),
        "top1": {a: round(t1[a] / N, 3) for a in arms},
        "top3": {a: round(t3[a] / N, 3) for a in arms},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=150)
    ap.add_argument("--k", type=int, default=6)
    a = ap.parse_args()
    print(json.dumps(run(a.cases, a.k), indent=2))
