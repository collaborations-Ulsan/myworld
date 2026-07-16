#!/usr/bin/env python3
"""Rung 3 — Experiment B: DescentNet's obstruction H¹ on its REAL job (integrity /
poison / contradiction detection), the Akashic poison-resistance keystone (thesis §5C).

Prediction rungs (0-2) proved prediction is the wrong task. This tests whether
DescentNet's obstruction scalar flags poisoned/contradictory commons groups higher
than clean ones — and, crucially, whether it beats CHEAP baselines (a positive only
counts if the sheaf machinery adds something a trivial detector doesn't).

Math fact (proven + numerically confirmed, see log): obstruction = the NON-removable
(harmonic/H¹) part of the edge-residual field. Any single-entry / independent poison
is a node-level offset = a removable coboundary ⇒ obstruction ≡ 0. H¹ fires ONLY on
FRUSTRATED CYCLIC contradictions (loop-sum ≠ 0). So B splits:

  B1  realistic single-entry poison (cross-category / randomized / shuffled outlier).
      Detectors: obstruction vs node-embedding-variance vs top_tools-Jaccard.
      Hypothesis from the math: obstruction AUC≈0.5 (blind); cheap baselines win.

  B2  matched-energy witness: benign large-but-coherent disagreement (removable) vs
      frustrated contradiction (harmonic) of IDENTICAL total edge energy.
      Detectors: obstruction vs raw edge-field norm.
      Tests whether the Hodge split extracts contradiction invisible to magnitude.

Metric: AUC (P[score_poison > score_clean]) + mean separation + Cohen's d, N trials.
"""
from __future__ import annotations
import os, sys, json, argparse, random
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/home/user/workspaces/jaewon/universe/descentnet")
import aios_agent_behavior as B  # noqa: E402
from api import SheafCover, descent_step, coboundary, project_edge_field  # noqa: E402

STALK_DIM = 16
DTYPE = torch.float32
MEM = B.load_behavior_memories()
_CACHE = B._load_embed_cache()
BYCAT: dict[str, list[dict]] = {}
for m in MEM:
    BYCAT.setdefault(m.get("category", "?"), []).append(m)
CATS = [c for c, v in BYCAT.items() if len(v) >= 20]


def _pat_text(m: dict) -> str:
    return f"cat:{m.get('category','?')} top:[{','.join((m.get('top_tools') or [])[:6])}]"


def _embed_stalk(m: dict) -> torch.Tensor:
    txt = _pat_text(m)
    k = "stalkB:" + str(abs(hash(txt)) % (10 ** 12))
    if k in _CACHE:
        return torch.tensor(_CACHE[k], dtype=DTYPE)
    v = B._embed_batch([txt])
    raw = v[0] if v else [0.0] * 768
    proj = B._project_to_stalk(raw)
    _CACHE[k] = proj
    return torch.tensor(proj, dtype=DTYPE)


def _rand_tool_entry() -> dict:
    pool = ["Bash", "Edit", "Read", "Write", "Grep", "go", "take", "search[x]",
            "Thought:", "12", "Final", "put", "open", "clean", "WebFetch"]
    return {"category": "code", "top_tools": random.sample(pool, 5)}


def _cover(n):
    e = [(i, j) for i in range(n) for j in range(i + 1, n)]
    return SheafCover.from_edges(n, torch.tensor(e, dtype=torch.long), dtype=DTYPE), e


def _obstruction(sections: torch.Tensor, meas: torch.Tensor) -> float:
    n = sections.shape[0]
    cov, _ = _cover(n)
    out = descent_step(cov, sections.unsqueeze(0), meas.unsqueeze(0))
    return float(out.obstruction.square().sum(-1).sqrt().mean())


def _node_var(sections: torch.Tensor) -> float:
    # mean pairwise squared distance (an H0 / outlier detector)
    n = sections.shape[0]
    d = 0.0; c = 0
    for i in range(n):
        for j in range(i + 1, n):
            d += float((sections[i] - sections[j]).pow(2).sum()); c += 1
    return d / max(1, c)


def _jaccard_dissim(group: list[dict]) -> float:
    sets = [set((m.get("top_tools") or [])[:6]) for m in group]
    tot = 0.0; c = 0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            u = sets[i] | sets[j]
            inter = sets[i] & sets[j]
            tot += 1 - (len(inter) / len(u) if u else 1.0); c += 1
    return tot / max(1, c)


def _auc(pos: list[float], neg: list[float]) -> float:
    n = 0; s = 0.0
    for a in pos:
        for b in neg:
            n += 1
            s += 1.0 if a > b else (0.5 if a == b else 0.0)
    return s / max(1, n)


def _cohend(pos, neg):
    import statistics as st
    if len(pos) < 2 or len(neg) < 2:
        return 0.0
    mp, mn = st.mean(pos), st.mean(neg)
    sp = (st.pstdev(pos) ** 2 + st.pstdev(neg) ** 2) / 2
    return round((mp - mn) / (sp ** 0.5), 3) if sp > 0 else 0.0


# ── B1: realistic single-entry poison ────────────────────────────────────────

def run_b1(n_trials=200, K=6, poison="cross") -> dict:
    obs_c, obs_p = [], []
    var_c, var_p = [], []
    jac_c, jac_p = [], []
    for _ in range(n_trials):
        cat = random.choice(CATS)
        group = random.sample(BYCAT[cat], K)
        secs_c = torch.stack([_embed_stalk(m) for m in group])
        zero = torch.zeros(K * (K - 1) // 2, STALK_DIM)
        # poisoned group: replace one entry
        pg = list(group)
        if poison == "cross":
            other = random.choice([c for c in CATS if c != cat])
            pg[0] = random.choice(BYCAT[other])
        elif poison == "random":
            pg[0] = _rand_tool_entry()
        else:  # shuffle: same tools, scrambled → mild
            m0 = dict(group[0]); tt = list(m0.get("top_tools") or []); random.shuffle(tt)
            m0["top_tools"] = tt; pg[0] = m0
        secs_p = torch.stack([_embed_stalk(m) for m in pg])
        obs_c.append(_obstruction(secs_c, zero)); obs_p.append(_obstruction(secs_p, zero))
        var_c.append(_node_var(secs_c)); var_p.append(_node_var(secs_p))
        jac_c.append(_jaccard_dissim(group)); jac_p.append(_jaccard_dissim(pg))
    import statistics as st
    return {
        "n_trials": n_trials, "K": K, "poison": poison,
        "obstruction": {"auc": round(_auc(obs_p, obs_c), 3), "d": _cohend(obs_p, obs_c),
                        "mean_clean": float(f"{st.mean(obs_c):.2e}"), "mean_poison": float(f"{st.mean(obs_p):.2e}"),
                        "scale_note": "≈0 (numerical pinv noise; H¹ blind to single-entry poison, as proven)"},
        "node_variance": {"auc": round(_auc(var_p, var_c), 3), "d": _cohend(var_p, var_c),
                          "mean_clean": round(st.mean(var_c), 4), "mean_poison": round(st.mean(var_p), 4)},
        "jaccard": {"auc": round(_auc(jac_p, jac_c), 3), "d": _cohend(jac_p, jac_c),
                    "mean_clean": round(st.mean(jac_c), 4), "mean_poison": round(st.mean(jac_p), 4)},
    }


# ── B2: matched-energy frustration witness ───────────────────────────────────

def run_b2(n_trials=200, K=6, energy=1.0) -> dict:
    """Benign (removable coboundary) vs frustrated (harmonic) edge fields of EQUAL norm.
    sections are real group embeddings (identical across arms). Tests whether obstruction
    sees contradiction that raw edge-magnitude cannot."""
    obs_b, obs_f = [], []
    norm_b, norm_f = [], []
    for _ in range(n_trials):
        cat = random.choice(CATS)
        group = random.sample(BYCAT[cat], K)
        secs = torch.stack([_embed_stalk(m) for m in group])
        cov, e = _cover(K)
        E = len(e)
        # benign: coboundary of a random node potential (pure removable / H0)
        pot = torch.randn(1, K, STALK_DIM)
        benign = coboundary(cov, pot).squeeze(0)
        # frustrated: random edge field, project OUT the removable part -> harmonic (H1)
        rand_ef = torch.randn(1, E, STALK_DIM)
        _, harmonic, _ = project_edge_field(cov, rand_ef)
        harmonic = harmonic.squeeze(0)
        # normalize both to identical total energy
        benign = benign / (benign.norm() + 1e-9) * energy
        harmonic = harmonic / (harmonic.norm() + 1e-9) * energy
        # measurement is the claimed edge relationship; sections fixed (real).
        # residual = coboundary(secs) - measurement; to isolate the injected field,
        # set measurement = coboundary(secs) + field  → residual = -field
        cob_secs = coboundary(cov, secs.unsqueeze(0)).squeeze(0)
        meas_b = cob_secs + benign
        meas_f = cob_secs + harmonic
        obs_b.append(_obstruction(secs, meas_b)); obs_f.append(_obstruction(secs, meas_f))
        norm_b.append(float(benign.square().sum(-1).sqrt().mean()))
        norm_f.append(float(harmonic.square().sum(-1).sqrt().mean()))
    import statistics as st
    return {
        "n_trials": n_trials, "K": K, "matched_energy": energy,
        "obstruction": {"auc": round(_auc(obs_f, obs_b), 3), "d": _cohend(obs_f, obs_b),
                        "mean_benign": float(f"{st.mean(obs_b):.2e}"), "mean_frustrated": round(st.mean(obs_f), 5)},
        "raw_edge_norm": {"auc": round(_auc(norm_f, norm_b), 3),
                          "mean_benign": round(st.mean(norm_b), 4), "mean_frustrated": round(st.mean(norm_f), 4)},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--which", choices=["b1", "b2", "all"], default="all")
    a = ap.parse_args()
    random.seed(0); torch.manual_seed(0)
    out = {"cats": CATS}
    if a.which in ("b1", "all"):
        out["B1_cross"] = run_b1(a.trials, poison="cross")
        out["B1_random"] = run_b1(a.trials, poison="random")
        out["B1_shuffle"] = run_b1(a.trials, poison="shuffle")
    if a.which in ("b2", "all"):
        out["B2_frustration"] = run_b2(a.trials)
    B._save_embed_cache(_CACHE)
    print(json.dumps(out, indent=2))
