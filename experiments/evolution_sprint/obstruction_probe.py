#!/usr/bin/env python3
"""Re-earn gate probe: does the sheaf/GoEN revival's obstruction score carry ANY
real signal about KNOWN contradictions on our actual knowledge graph?

Context (deliberately restated because the sprint docs omit it):
  - This program already gated sheaf/H^1 NEGATIVE on real data (1438 real cases,
    0 with the claimed structure; H^1 was effectively detecting a simpler
    signal; "cycle-not-edge") and PARKED it. GoEN was on the kill list for
    calibration collapse.
  - docs/2026_07_evolution_sprint/ proposes a revival ("Obstruction-Driven
    Rewiring": prune edges with high friction = ||x_i - x_j||^2 * weight,
    Hebbian-wire co-activated unlinked pairs). That is a NEW hypothesis and
    must be RE-EARNED with evidence, not assumed.

THE TEST:
  Data: docs/ontology/ledger/_merged.json — 1233 entities, 1872 relations,
  72 hand-sourced `contradicts` edges (real contradictions from research
  ledgers), 31 cross-domain entities.

  1. Node features: we have NO embeddings, so each node gets a deterministic
     signed-hash bag-of-tokens vector (tokens from name + type + domain,
     dim=512, md5-hashed index+sign, L2-normalized). THIS IS A LEXICAL PROXY,
     NOT SEMANTICS — stated up front and revisited in the limitations.
  2. Obstruction score per edge = the prototype's friction
     ||x_i - x_j||^2 * weight (ledger has no weights -> bridge default 1.0),
     plus a graph-Laplacian variant (friction on 2-step symmetric-normalized
     diffusion-smoothed features, i.e. the edge's residual Dirichlet energy
     after local gluing — the cheap stand-in for "global consistency").
  3. Discriminating question A (edge level, as tasked): do the 72 KNOWN
     contradicts edges score HIGHER friction than the other 1800 edges?
     AUC + class means/medians + permutation p + global-ranking position.
  4. Confound control B: 61/72 contradicts are Claim–Claim while most other
     edges are cross-type (authored: Person–Paper, ...), so a global AUC can
     be driven purely by endpoint-type composition — exactly the prior
     failure mode ("H^1 was detecting a simpler signal"). Stratum tests:
     contradicts Claim–Claim vs ALL unlinked Claim–Claim pairs, and
     contradicts Paper–Paper vs sampled unlinked Paper–Paper pairs.
     (Only 8 non-contradicts Claim–Claim EDGES exist — too few to be the
     control class, reported as a footnote.)
  5. Hebbian half C: cross-domain entity pairs (proxy for "co-activated but
     unlinked") vs (i) random unlinked pairs and (ii) TYPE-MATCHED random
     unlinked pairs — same confound control.
  6. Diagnostic D: name-token Jaccard overlap of contradicts pairs vs random
     unlinked Claim–Claim pairs — tests whether the geometry is just lexical
     overlap (contradicting claims are about the SAME topic, so a lexical
     proxy should place them CLOSE, inverting the "high distance =
     contradiction" premise).

STOP RULE (pre-stated):
  - If AUC ~ 0.5 / permutation p not significant on the discriminating tests,
    obstruction-ranking carries NO signal about real contradictions on our
    data -> the revival FAILS its re-earn gate and stays parked (replicating
    the prior negative).
  - EARNED requires: AUC clearly > 0.5 (direction the proposal claims:
    contradictions = HIGH friction) with significant permutation p, AND the
    signal must SURVIVE the type-controlled strata (B) — a global-only signal
    that vanishes under type control is the "simpler signal" failure again,
    not an earned revival.
  - AUC significantly < 0.5 is ALSO a failure of the proposal as written:
    the score anti-detects contradictions (the pruning scalpel would cut the
    WRONG edges), and the residual signal is lexical proximity, not sheaf
    structure.

Self-contained: numpy + stdlib only. Deterministic (fixed seeds, md5 hashing).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

LEDGER = Path(__file__).resolve().parents[2] / "docs" / "ontology" / "ledger" / "_merged.json"
DIM = 512
SEED = 20260725
N_PERM = 10_000
TOKEN_RE = re.compile(r"[a-z0-9]+")


# ----------------------------------------------------------------------------
# Features: deterministic signed-hash bag-of-tokens (PROXY, not semantics)
# ----------------------------------------------------------------------------
def entity_tokens(e: dict) -> list[str]:
    toks = TOKEN_RE.findall(e["name"].lower())
    toks.append(f"type:{e['type'].lower()}")
    toks.extend(f"domain:{d.lower()}" for d in e["domain"])
    return toks


def name_token_set(e: dict) -> frozenset[str]:
    return frozenset(TOKEN_RE.findall(e["name"].lower()))


def hashed_features(entities: list[dict], dim: int = DIM) -> np.ndarray:
    X = np.zeros((len(entities), dim), dtype=np.float64)
    for i, e in enumerate(entities):
        for tok in entity_tokens(e):
            h = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:8], "little") % dim
            sign = 1.0 if h[8] & 1 else -1.0
            X[i, idx] += sign
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return X / norms


def smooth_features(X: np.ndarray, pairs: set[tuple[int, int]], steps: int = 2) -> np.ndarray:
    """2-step symmetric-normalized diffusion (A+I) — cheap Laplacian gluing."""
    n = X.shape[0]
    A = np.zeros((n, n), dtype=np.float64)
    for i, j in pairs:
        A[i, j] = 1.0
        A[j, i] = 1.0
    A += np.eye(n)
    dinv = 1.0 / np.sqrt(A.sum(axis=1))
    A_hat = A * dinv[:, None] * dinv[None, :]
    Xs = X.copy()
    for _ in range(steps):
        Xs = A_hat @ Xs
    return Xs


def sq_dist(X: np.ndarray, pairs: np.ndarray) -> np.ndarray:
    d = X[pairs[:, 0]] - X[pairs[:, 1]]
    return np.einsum("ij,ij->i", d, d)


# ----------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------
def average_ranks(x: np.ndarray) -> np.ndarray:
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    cum = np.cumsum(counts)
    avg = (cum - counts) + (counts + 1) / 2.0  # 1-based average rank per tie group
    return avg[inv]


def auc_perm_test(pos: np.ndarray, neg: np.ndarray, rng: np.random.Generator,
                  n_perm: int = N_PERM) -> dict:
    scores = np.concatenate([pos, neg])
    n_pos, n_neg = len(pos), len(neg)
    n = n_pos + n_neg
    ranks = average_ranks(scores)
    auc = (ranks[:n_pos].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    dev_obs = abs(auc - 0.5)
    hits_two = 0
    hits_ge = 0  # one-sided: perm AUC >= observed (for direction > 0.5 claims)
    base = n_pos * (n_pos + 1) / 2.0
    denom = n_pos * n_neg
    for _ in range(n_perm):
        idx = rng.choice(n, size=n_pos, replace=False)
        auc_p = (ranks[idx].sum() - base) / denom
        if abs(auc_p - 0.5) >= dev_obs:
            hits_two += 1
        if auc_p >= auc:
            hits_ge += 1
    return {
        "n_pos": n_pos,
        "n_neg": n_neg,
        "auc": float(auc),
        "p_two_sided": (hits_two + 1) / (n_perm + 1),
        "p_one_sided_greater": (hits_ge + 1) / (n_perm + 1),
        "pos_mean": float(pos.mean()),
        "pos_median": float(np.median(pos)),
        "neg_mean": float(neg.mean()),
        "neg_median": float(np.median(neg)),
    }


def report(name: str, res: dict) -> None:
    print(f"\n[{name}]")
    print(f"  n_pos={res['n_pos']}  n_neg={res['n_neg']}")
    print(f"  AUC={res['auc']:.4f}   perm p(two-sided)={res['p_two_sided']:.4f}"
          f"   p(one-sided, pos>neg)={res['p_one_sided_greater']:.4f}")
    print(f"  pos mean/median = {res['pos_mean']:.4f} / {res['pos_median']:.4f}")
    print(f"  neg mean/median = {res['neg_mean']:.4f} / {res['neg_median']:.4f}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    data = json.loads(LEDGER.read_text())
    entities = data["entities"]
    relations = data["relations"]
    idx_of = {e["id"]: i for i, e in enumerate(entities)}
    n = len(entities)
    print(f"ledger: {n} entities, {len(relations)} relations "
          f"({sum(1 for r in relations if r['rel'] == 'contradicts')} contradicts)")

    X = hashed_features(entities)
    linked: set[tuple[int, int]] = set()
    edge_pairs = np.empty((len(relations), 2), dtype=np.int64)
    is_contra = np.zeros(len(relations), dtype=bool)
    for k, r in enumerate(relations):
        i, j = idx_of[r["src_id"]], idx_of[r["dst_id"]]
        edge_pairs[k] = (i, j)
        is_contra[k] = r["rel"] == "contradicts"
        linked.add((min(i, j), max(i, j)))
    Xs = smooth_features(X, linked)

    # Obstruction scores per EDGE (weight = 1.0: ledger has no edge weights,
    # which is also the bridge prototype's default).
    fric_raw = sq_dist(X, edge_pairs)
    fric_lap = sq_dist(Xs, edge_pairs)

    # ---------------- A. Global edge-level test (as tasked) ----------------
    print("\n================ A. GLOBAL EDGE TEST (72 contradicts vs 1800 other edges)")
    res_a_raw = auc_perm_test(fric_raw[is_contra], fric_raw[~is_contra], rng)
    report("A-raw  friction = ||x_i-x_j||^2 (prototype)", res_a_raw)
    res_a_lap = auc_perm_test(fric_lap[is_contra], fric_lap[~is_contra], rng)
    report("A-lap  friction on Laplacian-smoothed features", res_a_lap)

    # Global obstruction ranking position of the contradicts edges
    order = np.argsort(-fric_raw)  # descending: rank 1 = highest obstruction
    rank_desc = np.empty(len(fric_raw), dtype=np.int64)
    rank_desc[order] = np.arange(1, len(fric_raw) + 1)
    cr = rank_desc[is_contra]
    n_edges = len(fric_raw)
    print(f"\n  global ranking (raw friction, rank 1 = most obstructed of {n_edges}):")
    print(f"    contradicts mean rank={cr.mean():.1f}  median rank={np.median(cr):.1f}")
    print(f"    mean percentile (1.0 = top) = {1.0 - (cr.mean() - 1) / n_edges:.3f}")
    print(f"    in top-72: {(cr <= 72).sum()}/72   in top-10%: {(cr <= n_edges // 10).sum()}/72")

    # Type-pair composition (the confound)
    types = [e["type"] for e in entities]
    tp_contra = Counter(tuple(sorted((types[i], types[j]))) for (i, j) in edge_pairs[is_contra])
    print(f"\n  confound check — contradicts endpoint-type pairs: {dict(tp_contra)}")
    print("  (most non-contradicts edges are cross-type, e.g. authored: Person-Paper;")
    print("   any global AUC may be type composition, not contradiction signal)")

    # ---------------- B. Type-controlled strata ----------------
    print("\n================ B. TYPE-CONTROLLED STRATA")
    claim_idx = [i for i, e in enumerate(entities) if e["type"] == "Claim"]
    cc_pos_pairs = np.array(sorted({(min(i, j), max(i, j))
                                    for (i, j), c in zip(edge_pairs, is_contra)
                                    if c and types[i] == "Claim" and types[j] == "Claim"}),
                            dtype=np.int64)
    cc_all = [(a, b) for ai, a in enumerate(claim_idx) for b in claim_idx[ai + 1:]]
    cc_neg_pairs = np.array([p for p in cc_all if p not in linked], dtype=np.int64)
    print(f"  Claim-Claim stratum: {len(cc_pos_pairs)} contradicts pairs vs "
          f"{len(cc_neg_pairs)} unlinked Claim-Claim pairs (ALL of them)")
    res_b_raw = auc_perm_test(sq_dist(X, cc_pos_pairs), sq_dist(X, cc_neg_pairs), rng)
    report("B-CC-raw  contradicts CC vs unlinked CC (raw friction)", res_b_raw)
    res_b_lap = auc_perm_test(sq_dist(Xs, cc_pos_pairs), sq_dist(Xs, cc_neg_pairs), rng)
    report("B-CC-lap  contradicts CC vs unlinked CC (Laplacian)", res_b_lap)

    # Footnote: the only 8 non-contradicts Claim-Claim EDGES (underpowered)
    cc_edge_neg = np.array([(i, j) for (i, j), c in zip(edge_pairs, is_contra)
                            if not c and types[i] == "Claim" and types[j] == "Claim"],
                           dtype=np.int64)
    if len(cc_edge_neg):
        r = auc_perm_test(sq_dist(X, cc_pos_pairs), sq_dist(X, cc_edge_neg), rng)
        print(f"\n  footnote (underpowered, n_neg={len(cc_edge_neg)}): contradicts CC vs "
              f"non-contradicts CC EDGES -> AUC={r['auc']:.3f}, p_two={r['p_two_sided']:.3f}")

    # Paper-Paper stratum (secondary, underpowered: 10 positives)
    paper_idx = [i for i, e in enumerate(entities) if e["type"] == "Paper"]
    pp_pos_pairs = np.array(sorted({(min(i, j), max(i, j))
                                    for (i, j), c in zip(edge_pairs, is_contra)
                                    if c and types[i] == "Paper" and types[j] == "Paper"}),
                            dtype=np.int64)
    pp_neg = set()
    while len(pp_neg) < 5000:
        a, b = rng.choice(len(paper_idx), size=2, replace=False)
        p = (min(paper_idx[a], paper_idx[b]), max(paper_idx[a], paper_idx[b]))
        if p not in linked:
            pp_neg.add(p)
    pp_neg_pairs = np.array(sorted(pp_neg), dtype=np.int64)
    res_b2 = auc_perm_test(sq_dist(X, pp_pos_pairs), sq_dist(X, pp_neg_pairs), rng)
    report(f"B-PP-raw  contradicts PP (n={len(pp_pos_pairs)}) vs 5000 unlinked PP pairs", res_b2)

    # ---------------- C. Hebbian half ----------------
    print("\n================ C. HEBBIAN HALF (cross-domain pairs as 'co-activated but unlinked' proxy)")
    xdom = [i for i, e in enumerate(entities) if len(e["domain"]) > 1]
    heb_pairs = np.array(sorted({(min(a, b), max(a, b))
                                 for ai, a in enumerate(xdom) for b in xdom[ai + 1:]
                                 if (min(a, b), max(a, b)) not in linked}), dtype=np.int64)
    print(f"  {len(xdom)} cross-domain entities -> {len(heb_pairs)} unlinked cross-domain pairs")
    rand_neg = set()
    heb_set = {tuple(p) for p in heb_pairs}
    while len(rand_neg) < 5000:
        a, b = rng.choice(n, size=2, replace=False)
        p = (min(a, b), max(a, b))
        if p not in linked and p not in heb_set:
            rand_neg.add(p)
    rand_neg_pairs = np.array(sorted(rand_neg), dtype=np.int64)
    res_c_raw = auc_perm_test(sq_dist(X, heb_pairs), sq_dist(X, rand_neg_pairs), rng)
    report("C-raw  cross-domain pairs vs random unlinked pairs (raw distance^2)", res_c_raw)
    res_c_lap = auc_perm_test(sq_dist(Xs, heb_pairs), sq_dist(Xs, rand_neg_pairs), rng)
    report("C-lap  same on Laplacian-smoothed features", res_c_lap)

    # Type-matched control: negatives drawn with the SAME endpoint-type pair
    # distribution as the positives (kills the type-composition confound).
    by_type: dict[str, list[int]] = {}
    for i, t in enumerate(types):
        by_type.setdefault(t, []).append(i)
    matched = []
    for (i, j) in heb_pairs:
        ta, tb = types[i], types[j]
        got = 0
        tries = 0
        while got < 10 and tries < 400:
            tries += 1
            a = by_type[ta][rng.integers(len(by_type[ta]))]
            b = by_type[tb][rng.integers(len(by_type[tb]))]
            if a == b:
                continue
            p = (min(a, b), max(a, b))
            if p in linked or p in heb_set:
                continue
            matched.append(p)
            got += 1
    matched_pairs = np.array(matched, dtype=np.int64)
    res_c_m = auc_perm_test(sq_dist(X, heb_pairs), sq_dist(X, matched_pairs), rng)
    report(f"C-matched  cross-domain pairs vs TYPE-MATCHED unlinked pairs (n={len(matched_pairs)})",
           res_c_m)

    # ---------------- D. Lexical-overlap diagnostic ----------------
    print("\n================ D. DIAGNOSTIC — is the geometry just lexical overlap?")
    tok = [name_token_set(e) for e in entities]

    def jac(pairs: np.ndarray) -> np.ndarray:
        out = np.empty(len(pairs))
        for k, (i, j) in enumerate(pairs):
            u = len(tok[i] | tok[j])
            out[k] = len(tok[i] & tok[j]) / u if u else 0.0
        return out

    j_pos = jac(cc_pos_pairs)
    j_neg = jac(cc_neg_pairs)
    res_d = auc_perm_test(j_pos, j_neg, rng)
    print(f"  name-token Jaccard, contradicts CC vs unlinked CC:")
    print(f"    pos mean={res_d['pos_mean']:.4f}  neg mean={res_d['neg_mean']:.4f}  "
          f"AUC={res_d['auc']:.4f}  p_two={res_d['p_two_sided']:.4f}")
    print("  (AUC>0.5 here = contradicting claims share MORE tokens than random claim")
    print("   pairs -> a lexical proxy places them CLOSER -> LOW friction, inverting")
    print("   the proposal's 'high distance = contradiction' premise.)")

    # ---------------- Verdict per pre-stated stop rule ----------------
    print("\n================ VERDICT (stop rule applied)")
    sig = 0.05
    a_pos = res_a_raw["auc"] > 0.5 and res_a_raw["p_two_sided"] < sig
    b_pos = (res_b_raw["auc"] > 0.5 and res_b_raw["p_two_sided"] < sig
             and res_b_lap["auc"] > 0.5 and res_b_lap["p_two_sided"] < sig)
    if a_pos and b_pos:
        print("  EARNED: contradicts edges score higher obstruction globally AND the")
        print("  signal survives type control. Next step would be re-running with real")
        print("  embeddings + a held-out contradiction set before any rewiring code.")
    else:
        print("  FAILED-STAYS-PARKED: obstruction-ranking does not carry the claimed")
        print("  signal about real contradictions on our data (or the signal is the")
        print("  type/lexical 'simpler signal' again). The revival does not pass its")
        print("  re-earn gate; sheaf/GoEN stays parked.")
        if res_b_raw["auc"] < 0.5 and res_b_raw["p_two_sided"] < sig:
            print("  NOTE: type-controlled AUC is significantly BELOW 0.5 — under the")
            print("  lexical proxy, contradicting claims are CLOSER than random claim")
            print("  pairs, so the proposed pruning scalpel would preferentially cut")
            print("  the WRONG (non-contradiction) edges.")
    print(f"\ndone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
