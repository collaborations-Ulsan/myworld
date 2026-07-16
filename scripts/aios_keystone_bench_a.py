#!/usr/bin/env python3
"""Rung 2 — Experiment A (the keystone: does the GLOBAL cross-agent commons help?).

Isolates ONE variable: local-only memory vs local + GLOBAL AkashicRecord commons,
everything else fixed (best arm from Rung 1 = freq-primary, with `gated` descent
tie-break). Held-out time-split (sessions never ingested). Small N (live network).

IMPORTANT wiring fix: the shipped `sync_from_global` omits the API key, so the live
`use_global=True` path is rejected 402 → swallowed to [] → global NEVER contributes
(a mechanical null, not a scientific one). Here we authenticate so the commons
actually returns data, then measure the honest Δ.

Two commons variants (both authenticated):
  sanitized : query = safe_summary(classify(ctx)) = "category:code" etc — what the
              PRODUCTION privacy sink actually sends (contexts collapse to ~4 buckets).
  raw       : query = raw context — an UPPER BOUND on what the commons could give if
              the privacy constraint were relaxed (not production-safe; sensitivity only).
"""
from __future__ import annotations
import os, sys, json, argparse, hashlib
import urllib.request as U
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_agent_behavior as B  # noqa: E402
try:
    import aios_capture_args as CAP
except Exception:
    CAP = None

MEM = B.load_behavior_memories()
KEY = B._get_stored_api_key()
_INGESTED = set()
for m in MEM:
    for r in m.get("evidence_refs", []):
        if isinstance(r, str) and r.startswith("session:"):
            _INGESTED.add(r.split("session:", 1)[1])

_CACHE = B._load_embed_cache()
_SYNC_CACHE: dict[str, list[dict]] = {}


def _embed(text: str):
    key = "ctx:" + hashlib.sha256(text.encode()).hexdigest()[:16]
    if key in _CACHE:
        return _CACHE[key]
    v = B._embed_batch([text[:400]])
    if not v:
        return None
    _CACHE[key] = v[0]
    return v[0]


def _mem_embed(m):
    k = "mem:" + m["id"]
    if k in _CACHE:
        return _CACHE[k]
    v = B._embed_batch([m.get("content", "")[:400]])
    if not v:
        return None
    _CACHE[k] = v[0]
    return v[0]


def authed_sync(query: str, top_k: int = 4) -> list[dict]:
    if query in _SYNC_CACHE:
        return _SYNC_CACHE[query]
    if not KEY:
        _SYNC_CACHE[query] = []
        return []
    body = json.dumps({"query": query, "top_k": top_k}).encode()
    req = U.Request(B.AKASHIC_SERVER + "/sync", data=body,
                    headers={"Content-Type": "application/json", "User-Agent": "AIOS/0.1",
                             "X-AIOS-Version": "0.1", "X-AIOS-Key": KEY}, method="POST")
    try:
        with U.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        res = data.get("results", [])
        for x in res:
            tf = x.get("tool_freq", {})
            if isinstance(tf, str):
                try:
                    x["tool_freq"] = json.loads(tf)
                except Exception:
                    x["tool_freq"] = {}
        _SYNC_CACHE[query] = res
        return res
    except Exception as e:
        _SYNC_CACHE[query] = []
        return []


def global_patterns(ctx: str, mode: str) -> list[dict]:
    if mode == "sanitized":
        cat = B._classify_context(ctx)
        q = CAP.safe_summary(cat) if CAP else f"category:{cat}"
    else:  # raw
        q = ctx
    out = []
    for g in authed_sync(q, 4):
        out.append({"id": "global-" + g.get("id", "?"),
                    "content": f"global:{g.get('category','?')}",
                    "domain": "agent_behavior",
                    "tool_freq": g.get("tool_freq") or {},
                    "top_tools": g.get("top_tools", []),
                    "loop_type": None})
    return out


def held_out_sessions(limit_files=250):
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


def retrieve(ctx, k=6):
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


def _rank(scores):
    return sorted(scores, key=lambda c: scores.get(c, 0.0), reverse=True)


def _gated(fs, ds, vocab):
    fr = _rank(fs)
    if len(fr) >= 2 and (fs.get(fr[0], 0) - fs.get(fr[1], 0)) < 0.05:
        top = fr[:3]
        return sorted(top, key=lambda c: ds.get(c, 0.5), reverse=True) + fr[3:]
    return fr


def score_arm(vocab, mems, ctx):
    clean = [m for m in mems if m.get("loop_type") != "doom_loop"]
    fs = B._frequency_scores(vocab, clean)
    ds, _ = B._descent_scores(ctx, vocab, mems)
    return _rank(fs), _gated(fs, ds, vocab)


def run(n_cases=40, mode="sanitized"):
    seqs = held_out_sessions()
    vocab, cases = build_cases(seqs, n_cases)
    if not cases:
        return {"error": "no held-out cases"}
    arms = ["full_freq", "local_freq", "global_freq", "local_gated", "global_gated"]
    t1 = {a: 0 for a in arms}; t3 = {a: 0 for a in arms}
    n_global_nonempty = 0
    full_freq_rank = _rank(B._frequency_scores(vocab, MEM))  # whole-corpus control (Rung1 baseline)
    for ctx, prev, true in cases:
        local = retrieve(ctx, 6)
        gpat = global_patterns(ctx, mode)
        if gpat:
            n_global_nonempty += 1
        lf, lg = score_arm(vocab, local, ctx)
        gf, gg = score_arm(vocab, local + gpat[:4], ctx)
        for a, r in [("full_freq", full_freq_rank),
                     ("local_freq", lf), ("global_freq", gf),
                     ("local_gated", lg), ("global_gated", gg)]:
            t1[a] += (r[:1] == [true]); t3[a] += (true in r[:3])
    B._save_embed_cache(_CACHE)
    N = len(cases)
    top1 = {a: round(t1[a] / N, 3) for a in arms}
    top3 = {a: round(t3[a] / N, 3) for a in arms}
    return {
        "N": N, "mode": mode, "vocab": len(vocab),
        "authenticated": bool(KEY), "cases_with_global_hits": n_global_nonempty,
        "distinct_global_queries": len(_SYNC_CACHE),
        "top1": top1, "top3": top3,
        "delta_freq_top1": round(top1["global_freq"] - top1["local_freq"], 3),
        "delta_freq_top3": round(top3["global_freq"] - top3["local_freq"], 3),
        "delta_gated_top1": round(top1["global_gated"] - top1["local_gated"], 3),
        "delta_gated_top3": round(top3["global_gated"] - top3["local_gated"], 3),
        # clean control: global arm vs whole-corpus freq baseline (same cases)
        "global_vs_full_top1": round(top1["global_gated"] - top1["full_freq"], 3),
        "global_vs_full_top3": round(top3["global_gated"] - top3["full_freq"], 3),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=40)
    ap.add_argument("--mode", choices=["sanitized", "raw"], default="sanitized")
    a = ap.parse_args()
    print(json.dumps(run(a.cases, a.mode), indent=2))
