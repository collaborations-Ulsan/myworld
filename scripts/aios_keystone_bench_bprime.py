#!/usr/bin/env python3
"""Rung 4 — Experiment B′ (PREVALENCE, the terminal rung). Closes the keystone.

B established: DescentNet's obstruction H¹ is blind to independent (H⁰) poison and
fires ONLY on frustrated CYCLIC contradiction — a real but constructed witness. The
whole keystone now reduces to ONE measurable fact: do REAL commons contradictions
ever take cyclic-frustrated (H¹) form, or are they ~always independent (H⁰)?

Only real, NON-INJECTED relational structure in the corpus is tool TRANSITIONS
(relations field is empty). So we use HodgeRank: aggregate directional tool→tool
preferences in real coherent groups, then split (via the SAME `project_edge_field`
that would guard the commons) into gradient (H⁰ = a globally consistent tool ordering,
removable) vs the non-gradient residual (H¹-type = cyclic inconsistency / frustration).

  harmonic_fraction = ||obstruction||² / ||flow||²  ∈ [0,1]
  = fraction of real pairwise-preference energy NOT explained by any global ranking.

Arms (all from REAL data, no injection):
  clean        : single-category groups (coherent) — native cyclic structure.
  contaminated : REAL cross-category mixes (real "poison": incompatible sources merged).
  grad_floor   : pure-gradient control (coboundary of random potential, same topology)
                 → establishes the float-noise floor for harmonic_fraction on each graph.

Named exits:
  contaminated harmonic_fraction meaningfully > clean AND > floor, on a non-trivial
  rate of real groups  → H¹ earns a real §5C poison-resistance role.
  else (real contamination is H⁰: raises tool-set/outlier stats but NOT harmonic flow)
  → exhaustive impossibility for the stated keystone; ship the cheap H⁰ filter.
"""
from __future__ import annotations
import os, sys, json, argparse, random
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/home/user/workspaces/jaewon/universe/descentnet")
import aios_agent_behavior as B  # noqa: E402
from api import SheafCover, coboundary, project_edge_field  # noqa: E402

DTYPE = torch.float32
CATS = frozenset({"code", "docs", "data", "personal"})


def load_sessions(limit=600):
    """Real claude sessions with rich tool sequences, tagged by category."""
    root = Path.home() / ".claude" / "projects"
    files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = {c: [] for c in CATS}
    for f in files:
        try:
            t = B._clean_tools(B._parse_claude_session(f))
        except Exception:
            t = []
        if len(t) < 8:
            continue
        c = B._classify_session(t, CATS)
        if c in out:
            out[c].append(t)
        if sum(len(v) for v in out.values()) >= limit:
            break
    return out


def transition_flow(seqs: list[list[str]], min_edge=3):
    """Aggregate directional tool→tool counts over a group → antisymmetric pairwise
    preference flow on the tool graph. Returns (tools, edges, flow[E,1]) or None."""
    T: dict[tuple[str, str], int] = {}
    tools = set()
    for s in seqs:
        for a, b in zip(s, s[1:]):
            if a == b:
                continue
            T[(a, b)] = T.get((a, b), 0) + 1
            tools.add(a); tools.add(b)
    tools = sorted(tools)
    idx = {t: i for i, t in enumerate(tools)}
    edges = []
    flowvals = []
    seen = set()
    for (a, b) in list(T.keys()):
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        i, j = idx[key[0]], idx[key[1]]
        fij = T.get((key[0], key[1]), 0)
        fji = T.get((key[1], key[0]), 0)
        tot = fij + fji
        if tot < min_edge:
            continue
        edges.append((i, j))
        flowvals.append((fij - fji) / tot)  # net preference in [-1,1]
    if len(edges) < 3 or len(tools) < 3:
        return None
    flow = torch.tensor(flowvals, dtype=DTYPE).reshape(1, len(edges), 1)
    return tools, edges, flow


def harmonic_fraction(tools, edges, flow) -> float:
    n = len(tools)
    cover = SheafCover.from_edges(n, torch.tensor(edges, dtype=torch.long), dtype=DTYPE)
    _removable, obstruction, _ = project_edge_field(cover, flow)
    num = float(obstruction.square().sum())
    den = float(flow.square().sum()) + 1e-12
    return num / den


def grad_floor(tools, edges, trials=8) -> float:
    """Pure-gradient control: harmonic fraction of coboundary(random potential)."""
    n = len(tools)
    cover = SheafCover.from_edges(n, torch.tensor(edges, dtype=torch.long), dtype=DTYPE)
    vals = []
    for _ in range(trials):
        pot = torch.randn(1, n, 1, dtype=DTYPE)
        grad = coboundary(cover, pot)
        _r, obs, _ = project_edge_field(cover, grad)
        vals.append(float(obs.square().sum()) / (float(grad.square().sum()) + 1e-12))
    return sum(vals) / len(vals)


def group_entropy(seqs) -> float:
    """Split-agnostic cheap H0 detector: Shannon entropy of the group's tool
    distribution. Mixing two incompatible vocabularies raises it — needs no sheaf."""
    import math
    c = {}
    for s in seqs:
        for t in s:
            c[t] = c.get(t, 0) + 1
    tot = sum(c.values()) or 1
    return -sum((v / tot) * math.log(v / tot) for v in c.values())


def _auc(pos, neg):
    if not pos or not neg:
        return None
    n = 0; s = 0.0
    for a in pos:
        for b in neg:
            n += 1
            s += 1.0 if a > b else (0.5 if a == b else 0.0)
    return round(s / n, 3)


def toolset_kl(a_seqs, b_seqs) -> float:
    """Cheap H0 contamination detector: symmetric-ish tool-distribution divergence."""
    def dist(seqs):
        c = {}
        for s in seqs:
            for t in s:
                c[t] = c.get(t, 0) + 1
        tot = sum(c.values()) or 1
        return {k: v / tot for k, v in c.items()}
    pa, pb = dist(a_seqs), dist(b_seqs)
    keys = set(pa) | set(pb)
    import math
    kl = 0.0
    for k in keys:
        x = pa.get(k, 1e-6); y = pb.get(k, 1e-6)
        kl += x * math.log(x / y)
    return kl


def run(n_groups=120, group_sessions=8, min_edge=3):
    data = load_sessions()
    avail = {c: v for c, v in data.items() if len(v) >= group_sessions}
    cats = list(avail.keys())
    clean_hf, clean_floor = [], []
    cont_hf, cont_floor = [], []
    cont_kl_signal = []
    clean_ent, cont_ent = [], []
    clean_above, cont_above = 0, 0
    rng = random.Random(0)
    made_clean = made_cont = 0
    for _ in range(n_groups):
        # clean: one category
        c = rng.choice(cats)
        g = rng.sample(avail[c], group_sessions)
        tf = transition_flow(g, min_edge)
        if tf:
            tools, edges, flow = tf
            hf = harmonic_fraction(tools, edges, flow)
            fl = grad_floor(tools, edges)
            clean_hf.append(hf); clean_floor.append(fl)
            clean_ent.append(group_entropy(g))
            clean_above += (hf > max(1e-6, 3 * fl))
            made_clean += 1
        # contaminated: half from cat c, half from a different real category
        if len(cats) >= 2:
            c2 = rng.choice([x for x in cats if x != c])
            h = group_sessions // 2
            g2 = rng.sample(avail[c], h) + rng.sample(avail[c2], group_sessions - h)
            tf2 = transition_flow(g2, min_edge)
            if tf2:
                tools2, edges2, flow2 = tf2
                hf2 = harmonic_fraction(tools2, edges2, flow2)
                fl2 = grad_floor(tools2, edges2)
                cont_hf.append(hf2); cont_floor.append(fl2)
                cont_ent.append(group_entropy(g2))
                cont_above += (hf2 > max(1e-6, 3 * fl2))
                cont_kl_signal.append(toolset_kl(rng.sample(avail[c], h),
                                                 rng.sample(avail[c2], group_sessions - h)))
                made_cont += 1

    import statistics as st

    def summ(x):
        if not x:
            return {}
        return {"mean": round(st.mean(x), 5), "median": round(st.median(x), 5),
                "p90": round(sorted(x)[int(0.9 * len(x))], 5) if len(x) > 3 else None,
                "max": round(max(x), 5), "min": round(min(x), 5)}

    return {
        "n_clean_groups": made_clean, "n_contaminated_groups": made_cont,
        "group_sessions": group_sessions, "categories": cats,
        "noise_floor": {"clean_grad_floor": summ(clean_floor), "cont_grad_floor": summ(cont_floor)},
        "harmonic_fraction": {
            "clean": summ(clean_hf),
            "contaminated": summ(cont_hf),
        },
        "groups_with_H1_above_3x_floor": {
            "clean": f"{clean_above}/{made_clean}",
            "contaminated": f"{cont_above}/{made_cont}",
        },
        "cheap_H0_detector_kl": summ(cont_kl_signal),
        "SEPARATION_AUC_contam_vs_clean": {
            "H1_harmonic_fraction": _auc(cont_hf, clean_hf),
            "H0_tool_entropy_cheap": _auc(cont_ent, clean_ent),
        },
        "delta_contam_minus_clean_mean_hf": round(
            (st.mean(cont_hf) if cont_hf else 0) - (st.mean(clean_hf) if clean_hf else 0), 5),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", type=int, default=120)
    ap.add_argument("--gsize", type=int, default=8)
    ap.add_argument("--minedge", type=int, default=3)
    a = ap.parse_args()
    print(json.dumps(run(a.groups, a.gsize, a.minedge), indent=2))
