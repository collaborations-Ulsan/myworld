#!/usr/bin/env python3
"""aios_akashic_guard — cheap H⁰ consistency filter for Akashic commons poison-resistance.

The keystone program (docs/AIOS_KEYSTONE_EXPERIMENT.md, Rungs 0-4) established, no-launder:
DescentNet's H¹ obstruction does NOT catch the realistic commons threat (independent
cross-source poison is H⁰-shaped — a vocabulary shift, not a cyclic contradiction). A cheap
H⁰ consistency filter — how atypical an entry's tools are for its declared category — is the
actual detector (~zero cost), dominating H¹ at every richness. On this commons it separates
injected cross-category poison from clean entries at AUC ≈ 0.97.

So THIS is what ships as the commons poison guard. Because the commons vocabulary is noisy
ReAct trace tokens, the flag is RELATIVE, not an absolute cutoff: an entry is flagged only when
it is more atypical for its category than ~95% of that category's own entries (per-category p95
threshold → ≈5% false-flag by construction). DRAFT-FIRST: flags, never auto-deletes — DNA #2/#3
(append-only, operator override).

CLI:
  aios guard                          # audit the commons: most-anomalous entries (candidate poison)
  aios guard --score code Edit,Bash   # score a candidate before it enters the commons
  aios guard --top 20 [--json]
"""
from __future__ import annotations
import os, sys, json, argparse, math
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_agent_behavior as B  # noqa: E402

def _tools(entry) -> list[str]:
    tt = entry.get("top_tools") or []
    if not tt:
        tf = entry.get("tool_freq") or {}
        if isinstance(tf, str):
            try: tf = json.loads(tf)
            except json.JSONDecodeError: tf = {}
        tt = [t for t, _ in sorted(tf.items(), key=lambda x: -x[1])[:8]]
    return [str(t) for t in tt]

def build_profiles(memories) -> dict:
    """Per-category typical tool set + frequency centroid + self-calibrated anomaly threshold.

    The commons vocabulary is noisy ReAct trace tokens (`Thought:`, `bash:find`, `click[Buy`…),
    so an absolute anomaly cutoff is meaningless — a clean hand-typed tool list scores high just
    because it doesn't contain the trace noise. The honest signal is RELATIVE: flag an entry only
    when it is more atypical for its declared category than ~95% of that category's own entries.
    So we store each category's p95 clean-score threshold (false-flag ≈ 5% by construction)."""
    by_cat = defaultdict(Counter)
    counts = Counter()
    members = defaultdict(list)
    for m in memories:
        cat = m.get("category", "?"); counts[cat] += 1
        members[cat].append(m)
        for t in _tools(m):
            by_cat[cat][t] += 1
    profiles = {}
    for cat, cnt in by_cat.items():
        common = {t for t, _ in cnt.most_common(15)}
        total = sum(cnt.values()) or 1
        dist = {t: c / total for t, c in cnt.items()}
        profiles[cat] = {"common": common, "dist": dist, "n": counts[cat], "thresh": 1.0}
    # second pass: per-category p95 of member anomaly scores = self-calibrated flag threshold
    for cat, ms in members.items():
        scores = sorted(poison_score(m, profiles) for m in ms)
        if scores:
            profiles[cat]["thresh"] = scores[min(int(len(scores) * 0.95), len(scores) - 1)]
    return profiles

def poison_score(entry, profiles) -> float:
    """0-1 anomaly: high = this entry's tools are ATYPICAL for its declared category.

    Calibrated H0 signal = 1 − mean typicality of the entry's tools, where a tool's
    typicality is its category frequency normalized to the category's most-common tool.
    A clean entry (tools are common for its category) → low; a mislabeled/poisoned entry
    (tools absent from the category) → high. (Asymmetric containment, not Jaccard — Jaccard
    mis-penalizes a clean entry for not carrying ALL of the category's tools.)"""
    cat = entry.get("category", "?")
    prof = profiles.get(cat)
    tools = _tools(entry)
    if not prof or not tools:
        return 0.0
    d = prof["dist"]
    maxp = max(d.values()) if d else 1.0
    typicality = [min(d.get(t, 0.0) / maxp, 1.0) for t in tools]
    return round(1.0 - sum(typicality) / len(typicality), 3)

def _flagged(score, cat, profiles) -> bool:
    return score > profiles.get(cat, {}).get("thresh", 1.0)

def audit(memories, top_n: int = 15) -> list[dict]:
    profiles = build_profiles(memories)
    scored = [{"id": m.get("id"), "category": m.get("category"),
               "score": poison_score(m, profiles), "top_tools": _tools(m)[:5],
               "flagged": _flagged(poison_score(m, profiles), m.get("category"), profiles)}
              for m in memories]
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_n]

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aios guard", description="Cheap H0 commons poison guard")
    ap.add_argument("--score", nargs=2, metavar=("CATEGORY", "TOOLS"),
                    help="score a candidate: <category> <comma,separated,tools>")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    mems = B.load_behavior_memories()
    profiles = build_profiles(mems)

    if a.score:
        cat, tools = a.score
        cand = {"category": cat, "top_tools": [t.strip() for t in tools.split(",") if t.strip()]}
        s = poison_score(cand, profiles)
        thr = profiles.get(cat, {}).get("thresh", 1.0)
        flagged = _flagged(s, cat, profiles)
        flag = "⚠ ANOMALOUS (more atypical than 95% of this category — quarantine)" if flagged else "✓ within category norm"
        if a.json:
            print(json.dumps({"category": cat, "score": s, "thresh": round(thr, 3), "flagged": flagged})); return 0
        print(f"poison score {s:.3f}  (category flag threshold {thr:.3f})  {flag}")
        print(f"  category '{cat}' typical tools: {sorted(profiles.get(cat, {}).get('common', []))[:10]}")
        return 0

    flagged = audit(mems, a.top)
    if a.json:
        print(json.dumps({"entries": len(mems), "flagged": flagged}, indent=2)); return 0
    print(f"\n✦ Akashic commons poison audit (cheap H0 filter) — {len(mems)} entries")
    print("  most-anomalous (candidate poison / mislabel; draft-first — flagged, not deleted):\n")
    print(f"  {'score':>6}  {'category':<10}{'tools':<40}{'id'}")
    for e in flagged:
        mark = "⚠" if e["flagged"] else " "
        print(f" {mark}{e['score']:>6.3f}  {str(e['category']):<10}{','.join(e['top_tools'])[:38]:<40}{e['id']}")
    n_flag = sum(1 for e in flagged if e["flagged"])
    print(f"\n  {n_flag} flagged above their category's p95 anomaly threshold (operator reviews; never auto-deleted — DNA append-only).")
    print("  guard candidate before contribute:  aios guard --score <category> <tools>")
    return 0

if __name__ == "__main__":
    sys.exit(main())
