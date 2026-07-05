"""GoEN — the legibility / learned-rewiring certificate (Fable §2 / keystone §2: NAS /
lottery-ticket-style structural certificate; keystone verdict cites this as the
"generalization-gap estimation" family -- Zoph NAS, Frankle & Carbin lottery ticket,
Topping 2021 graph rewiring).

GoEN asks one question about the CURRENT claim context: *is this the right context to reason
over, or would dropping some claim/source (rewiring the ledger scope) predict a higher chance
of a verified solve?* Per the keystone panel's caveat (nemotron), the routing/rewiring decision
must be LEARNED, not hand-set thresholds -- so unlike APEX (conformal threshold) and IRIS (pure
combinatorics), GoEN FITS a small logistic-regression model mapping context features ->
P(verified-solve), then uses that model to score candidate rewires. It makes NO LLM calls -- it
is a deterministic function of claim/context structure (+ optionally the other certificates'
outputs) -- and it never reads ``Claim.poisoned`` (ground truth for scoring only).

Two feature modes (this is GoEN's own composition-coupling knob, see keystone §3):
  * mode ``"B"`` -- independent-certificate regime: GoEN sees ONLY its own raw observables
    (claim/context statistics -- counts, an IO-vs-property ratio, claim-graph density, and a
    GoEN-computed per-source anomaly proxy built directly from ``build_claim_graph``'s signed
    edges, NOT from DescentNet).
  * mode ``"C"`` -- coupled regime: the feature vector ADDITIONALLY includes the OTHER
    certificates' outputs (APEX label one-hot + coverage, IRIS class count/identified,
    DescentNet harmonic fraction + H0/H1 counts) via ``cert_outputs``. This is the
    cross-component coupling the keystone witness needs (DescentNet H1 obstructions -> GoEN
    rewrites).

Pipeline:
  1. ``fit_goen`` -- logistic regression (sklearn if importable, else a self-contained numpy
     gradient-descent fallback -- see ``_fit_logreg_numpy``) over calibration examples of
     (features, verified-solve).
  2. ``goen_certify`` -- score the CURRENT context, then evaluate a small rewire action space
     (drop each claim / drop each source / keep-all) by re-extracting features on each
     candidate subset and re-scoring with the SAME fitted model; report the best-scoring
     rewire and the resulting expected gain over the current context.

Constraints: stdlib + numpy (+ sklearn optional) only, deterministic (seeded), no ground-truth
reads. Types come from ``contracts.py``; claim-graph primitives come from ``claims.py`` -- this
module never reimplements ``build_claim_graph``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from contracts import Claim, GoenCert
from claims import build_claim_graph

try:
    from sklearn.linear_model import LogisticRegression
    _HAS_SKLEARN = True
except ImportError:  # pragma: no cover -- environment-dependent
    _HAS_SKLEARN = False


# =============================================================================
# Feature extraction
# =============================================================================

_B_KEYS = (
    "n_claims", "n_sources", "n_io", "n_property", "n_order",
    "io_property_ratio", "graph_density", "source_anomaly_max", "source_anomaly_mean",
)
_C_EXTRA_KEYS = (
    "apex_answerable", "apex_underdetermined", "apex_contradictory", "apex_coverage",
    "iris_n_classes", "iris_identified",
    "descent_hf", "descent_n_h0", "descent_n_h1",
)


def _own_observables(claims: list[Claim]) -> dict[str, float]:
    """GoEN's OWN raw observables (mode "B") -- pure claim/context statistics, no other
    certificate's output is read here.

    ``source_anomaly_{max,mean}`` is GoEN's self-computed proxy for "how much does this source's
    evidence conflict with the rest" -- for each source, the fraction of its incident
    ``build_claim_graph`` edges that are negatively signed (conflict, not agreement). This is
    deliberately GoEN's OWN cheap structural proxy, distinct from DescentNet's ``hf`` (which is
    a mode-"C" input, not computed here).
    """
    n = len(claims)
    if n == 0:
        # Empty context (a rewire can legitimately drop everything) -- return neutral defaults,
        # never divide by zero.
        return {k: 0.0 for k in _B_KEYS}

    n_sources = len({c.source_id for c in claims})
    n_io = sum(1 for c in claims if c.kind.value == "io")
    n_property = sum(1 for c in claims if c.kind.value == "property")
    n_order = sum(1 for c in claims if c.kind.value == "order")

    graph = build_claim_graph(claims)
    edges = graph["edges"]
    max_edges = (n * (n - 1)) / 2 if n > 1 else 1.0
    graph_density = len(edges) / max_edges if max_edges else 0.0

    # Per-source anomaly: fraction of a source's edge-endpoints that carry a conflict sign.
    edge_total: dict[str, int] = {}
    edge_neg: dict[str, int] = {}
    for e in edges:
        for idx in (e["u"], e["v"]):
            s = claims[idx].source_id
            edge_total[s] = edge_total.get(s, 0) + 1
            if e["sign"] < 0:
                edge_neg[s] = edge_neg.get(s, 0) + 1
    anomalies = [edge_neg.get(s, 0) / total for s, total in edge_total.items() if total > 0]
    source_anomaly_max = max(anomalies) if anomalies else 0.0
    source_anomaly_mean = (sum(anomalies) / len(anomalies)) if anomalies else 0.0

    return {
        "n_claims": float(n),
        "n_sources": float(n_sources),
        "n_io": float(n_io),
        "n_property": float(n_property),
        "n_order": float(n_order),
        "io_property_ratio": n_io / (n_property + 1.0),
        "graph_density": graph_density,
        "source_anomaly_max": source_anomaly_max,
        "source_anomaly_mean": source_anomaly_mean,
    }


def _other_cert_observables(cert_outputs: dict[str, Any] | None, n_claims: int) -> dict[str, float]:
    """Mode-"C" extra features: the OTHER certificates' outputs, read (not recomputed) from
    ``cert_outputs`` -- a dict with optional keys "apex" (``ApexCert``), "iris" (``IrisCert``),
    "descent" (``DescentCert``). Missing keys -> neutral defaults (all-zero one-hot / 0.0), so a
    partially-populated ``cert_outputs`` (e.g. only DescentNet has run so far) degrades
    gracefully instead of crashing."""
    feats = {k: 0.0 for k in _C_EXTRA_KEYS}
    if not cert_outputs:
        return feats

    apex = cert_outputs.get("apex")
    if apex is not None:
        onehot_key = f"apex_{apex.label.value.lower()}"
        if onehot_key in feats:
            feats[onehot_key] = 1.0
        # Fraction of the context the label's support_set actually backs -- GoEN's own reading
        # of "coverage", not a field APEX itself exposes by that name.
        feats["apex_coverage"] = len(apex.support_set) / max(1, n_claims)

    iris = cert_outputs.get("iris")
    if iris is not None:
        feats["iris_n_classes"] = float(iris.n_classes)
        feats["iris_identified"] = 1.0 if iris.identified else 0.0

    descent = cert_outputs.get("descent")
    if descent is not None:
        feats["descent_hf"] = float(descent.hf)
        feats["descent_n_h0"] = float(len(descent.h0_conflicts))
        feats["descent_n_h1"] = float(len(descent.h1_cycles))

    return feats


def extract_features(
    context_claims: list[Claim],
    mode: str,
    *,
    cert_outputs: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Build GoEN's feature dict for ``context_claims``.

    mode "B": GoEN's own observables only (``_B_KEYS``, 9 features).
    mode "C": "B" features PLUS the other certificates' outputs (``_C_EXTRA_KEYS``, +9 -> 18
    features total) -- the cross-component coupling knob (keystone §3).
    """
    if mode not in ("B", "C"):
        raise ValueError(f"mode must be 'B' or 'C', got {mode!r}")
    feats = _own_observables(context_claims)
    if mode == "C":
        feats.update(_other_cert_observables(cert_outputs, len(context_claims)))
    return feats


# =============================================================================
# Model
# =============================================================================

@dataclass
class GoenModel:
    """A fitted logistic-regression legibility model. ``weights[0]`` is the intercept;
    ``weights[1:]`` aligns positionally with ``feature_order`` -- so scoring is backend-agnostic
    (works identically whether ``fit_goen`` used sklearn or the numpy fallback)."""
    weights: np.ndarray
    feature_order: list[str]
    mode: str

    def predict_proba(self, feats: dict[str, float]) -> float:
        """P(verified-solve) for a feature dict. Missing keys default to 0.0 (e.g. an empty
        rewired context)."""
        x = np.array([feats.get(name, 0.0) for name in self.feature_order], dtype=float)
        z = self.weights[0] + float(np.dot(self.weights[1:], x))
        return float(1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0))))


def _fit_logreg_numpy(
    X: np.ndarray, y: np.ndarray, *, lr: float = 0.5, n_iter: int = 3000, l2: float = 1e-4,
) -> np.ndarray:
    """Self-contained batch-gradient-descent logistic regression (used only when sklearn is not
    importable). Standardizes features for a well-conditioned fit, then folds the
    standardization back into a raw-feature-space weight vector so ``GoenModel.predict_proba``
    never needs to know which backend fit it. Deterministic: seeded init (the loss is convex, so
    the seed only affects a small symmetric-breaking nudge, not whether it converges)."""
    n, d = X.shape
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    Xs = (X - mu) / sigma

    rng = np.random.default_rng(0)
    w = rng.normal(scale=0.01, size=d)
    b = 0.0
    for _ in range(n_iter):
        z = Xs @ w + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))
        grad_w = Xs.T @ (p - y) / n + l2 * w
        grad_b = float(np.mean(p - y))
        w -= lr * grad_w
        b -= lr * grad_b

    # Undo standardization: y = w.(x-mu)/sigma + b = (w/sigma).x + (b - sum(w*mu/sigma)).
    w_raw = w / sigma
    b_raw = b - float(np.sum(w * mu / sigma))
    return np.concatenate([[b_raw], w_raw])


def fit_goen(calib_examples: list[tuple[dict[str, float], bool]], mode: str) -> GoenModel:
    """Fit a logistic-regression legibility model over ``calib_examples`` = [(features, solved), ...].

    ``feature_order`` is the sorted union of feature keys actually present across
    ``calib_examples`` (deterministic ordering); any example missing a key contributes 0.0 for
    it. Uses sklearn's ``LogisticRegression`` when importable, else the numpy fallback above --
    prints which backend was used so a run's provenance is visible without inspecting internals.
    """
    if mode not in ("B", "C"):
        raise ValueError(f"mode must be 'B' or 'C', got {mode!r}")
    if not calib_examples:
        raise ValueError("fit_goen requires at least one calibration example")

    feature_order = sorted({k for feats, _ in calib_examples for k in feats})
    X = np.array([[feats.get(name, 0.0) for name in feature_order] for feats, _ in calib_examples], dtype=float)
    y = np.array([1.0 if solved else 0.0 for _, solved in calib_examples], dtype=float)

    # Degenerate calibration (all-solved or all-unsolved) has no gradient for a discriminative
    # fit — sklearn raises "needs >=2 classes". Fall back to a CONSTANT model that predicts the
    # observed base rate (zero feature weights, bias = logit(rate)). GoEN then rewires ~uniformly,
    # which is the honest behavior when calibration carries no solve-signal (its ablation simply
    # won't bite — a real finding, not a crash).
    if len(np.unique(y)) < 2:
        rate = float(np.clip(y.mean(), 1e-3, 1 - 1e-3))
        bias = float(np.log(rate / (1.0 - rate)))
        print(f"[fit_goen mode={mode}] degenerate calibration ({y.mean():.2f} solved) -> constant model (base-rate)")
        return GoenModel(weights=np.concatenate([[bias], np.zeros(len(feature_order))]),
                         feature_order=feature_order, mode=mode)

    if _HAS_SKLEARN:
        print(f"[fit_goen mode={mode}] sklearn available -> using sklearn.linear_model.LogisticRegression")
        clf = LogisticRegression(max_iter=1000, random_state=0)
        clf.fit(X, y)
        weights = np.concatenate([[float(clf.intercept_[0])], clf.coef_[0].astype(float)])
    else:
        print(f"[fit_goen mode={mode}] sklearn NOT importable -> using self-contained numpy gradient-descent fallback")
        weights = _fit_logreg_numpy(X, y)

    return GoenModel(weights=weights, feature_order=feature_order, mode=mode)


# =============================================================================
# The certificate
# =============================================================================

def goen_certify(
    context_claims: list[Claim],
    model: GoenModel,
    mode: str,
    *,
    cert_outputs: dict[str, Any] | None = None,
) -> GoenCert:
    """Certify the CURRENT context and propose the best rewire.

    Rewire action space (small and enumerable, per keystone §3's "learned, not hand-set"
    caveat -- the ACTIONS are hand-set, but which one wins is decided by the fitted model, not a
    threshold): drop each single claim, drop each distinct source (all its claims), or keep-all.
    Each candidate is scored by re-extracting features on the SUBSET and re-scoring with
    ``model`` -- ``cert_outputs`` is held fixed across candidates (GoEN reads the other
    certificates' current snapshot; it does not re-run them per rewire).

    ``score`` = model probability of the CURRENT (unrewired) context.
    ``expected_gain`` = best-rewire score - current score (>= 0, since keep-all is always a
    candidate -- rewiring never scores worse than doing nothing, by construction).
    """
    def _score(subset: list[Claim]) -> float:
        return model.predict_proba(extract_features(subset, mode, cert_outputs=cert_outputs))

    current_score = _score(context_claims)

    n = len(context_claims)
    actions: list[tuple[str, list[int]]] = [("keep_all", list(range(n)))]
    for i in range(n):
        actions.append((f"drop_claim_{i}", [j for j in range(n) if j != i]))
    for s in sorted({c.source_id for c in context_claims}):
        actions.append((f"drop_source_{s}", [j for j, c in enumerate(context_claims) if c.source_id != s]))

    best_indices = list(range(n))
    best_score = current_score
    for _name, indices in actions:
        score = _score([context_claims[j] for j in indices])
        if score > best_score:
            best_score = score
            best_indices = indices

    return GoenCert(
        score=current_score,
        rewired_context=best_indices,
        expected_gain=best_score - current_score,
    )


# =============================================================================
# Self-test (SYNTHETIC data only -- no dataset.py dependency)
# =============================================================================

if __name__ == "__main__":
    from contracts import ClaimKind

    print("=" * 70)
    print("certs/goen.py self-test")
    print("=" * 70)

    # --- (a) build ~40 synthetic (features, solved) examples ----------------------------------
    # Shared latent scenario per example: `coverage` and `hf` (mirrors a real APEX-coverage /
    # DescentNet-harmonic-fraction pair). `solved` is generated from coverage (helps) and hf
    # (hurts) plus small noise -- deterministic given the seeded RNG. Mode-B features see only a
    # GoEN-native anomaly PROXY correlated with `hf` (not `hf` itself); mode-C features see the
    # ground-mode `apex_coverage` / `descent_hf` directly -- this is exactly the B/C coupling gap.
    rng = np.random.default_rng(7)
    examples_B: list[tuple[dict[str, float], bool]] = []
    examples_C: list[tuple[dict[str, float], bool]] = []

    for _ in range(40):
        coverage = float(rng.uniform(0.0, 1.0))
        hf = float(rng.uniform(0.0, 1.0))

        n_claims = int(rng.integers(3, 13))
        n_sources = int(rng.integers(1, 6))
        n_io = int(rng.integers(0, n_claims + 1))
        n_property = int(rng.integers(0, n_claims - n_io + 1))
        n_order = max(0, n_claims - n_io - n_property)
        graph_density = float(rng.uniform(0.0, 1.0))  # nuisance: uncorrelated with the label

        source_anomaly_max = float(np.clip(hf + rng.normal(0.0, 0.05), 0.0, 1.0))
        source_anomaly_mean = float(np.clip(0.8 * hf + rng.normal(0.0, 0.05), 0.0, 1.0))

        feats_B = {
            "n_claims": float(n_claims), "n_sources": float(n_sources),
            "n_io": float(n_io), "n_property": float(n_property), "n_order": float(n_order),
            "io_property_ratio": n_io / (n_property + 1.0),
            "graph_density": graph_density,
            "source_anomaly_max": source_anomaly_max,
            "source_anomaly_mean": source_anomaly_mean,
        }

        if coverage > 0.66:
            apex_onehot = {"apex_answerable": 1.0, "apex_underdetermined": 0.0, "apex_contradictory": 0.0}
        elif coverage > 0.33:
            apex_onehot = {"apex_answerable": 0.0, "apex_underdetermined": 1.0, "apex_contradictory": 0.0}
        else:
            apex_onehot = {"apex_answerable": 0.0, "apex_underdetermined": 0.0, "apex_contradictory": 1.0}
        iris_n_classes = int(rng.integers(1, 4))
        feats_C = {
            **feats_B,
            **apex_onehot,
            "apex_coverage": coverage,
            "iris_n_classes": float(iris_n_classes),
            "iris_identified": 1.0 if iris_n_classes == 1 else 0.0,
            "descent_hf": hf,
            "descent_n_h0": float(rng.integers(0, 4)),
            "descent_n_h1": float(rng.integers(0, 3)),
        }

        logit = 3.0 * coverage - 3.0 * hf + rng.normal(0.0, 0.3)
        solved = bool(1.0 / (1.0 + np.exp(-logit)) > 0.5)

        examples_B.append((feats_B, solved))
        examples_C.append((feats_C, solved))

    n_solved = sum(1 for _, s in examples_B if s)
    print(f"\n[synthetic calib set] n={len(examples_B)} solved={n_solved} not_solved={len(examples_B) - n_solved}")

    model_B = fit_goen(examples_B, mode="B")
    model_C = fit_goen(examples_C, mode="C")

    # --- assert (a): models fit and predict in [0, 1] -----------------------------------------
    print("\n[assert a: fit + predict range]")
    for feats, _ in examples_B:
        p = model_B.predict_proba(feats)
        assert 0.0 <= p <= 1.0, f"mode B probability out of range: {p}"
    for feats, _ in examples_C:
        p = model_C.predict_proba(feats)
        assert 0.0 <= p <= 1.0, f"mode C probability out of range: {p}"
    assert isinstance(model_B, GoenModel) and model_B.mode == "B"
    assert isinstance(model_C, GoenModel) and model_C.mode == "C"
    print(f"  PASS: model_B ({len(model_B.feature_order)} feats) and model_C ({len(model_C.feature_order)} feats) "
          f"both fit and predict_proba in [0, 1] on all 40 calib examples")

    # --- (b) held-out contradictory-context example: rewire should drop the offending claim ---
    # tX: srcGood and srcGood2 independently AGREE (input=4 -> 8); srcBad dissents alone
    # (input=4 -> 9), conflicting with BOTH. srcGood also carries an unrelated PROPERTY claim.
    # Structurally, srcBad is the minority conflicting voice -- dropping it (not the corroborated
    # majority) is the honest, non-oracle-fabricated rewire (GoEN never reads `.poisoned`).
    context = [
        Claim("tX", "srcGood", ClaimKind.IO, {"input": [4], "output": 8}, ts=0),
        Claim("tX", "srcGood2", ClaimKind.IO, {"input": [4], "output": 8}, ts=1),
        Claim("tX", "srcBad", ClaimKind.IO, {"input": [4], "output": 9}, ts=2),   # offending claim
        Claim("tX", "srcGood", ClaimKind.PROPERTY, {"prop": "return_type", "value": "int"}, ts=3),
    ]
    cert = goen_certify(context, model_B, mode="B")
    print("\n[assert b: goen_certify on a contradictory held-out context, mode B]")
    print(f"  current score={cert.score:.4f}  rewired_context={cert.rewired_context}  "
          f"expected_gain={cert.expected_gain:.4f}")
    assert cert.expected_gain > 0.0, "a rewire should strictly beat keeping the conflicting claim"
    assert 2 not in cert.rewired_context, "the offending claim (idx 2, srcBad) must be dropped"
    print("  PASS: proposed rewire has expected_gain > 0 and drops the offending claim (idx 2, srcBad)")

    # --- (c) C-mode vs B-mode feature dimensionality --------------------------------------------
    print("\n[assert c: feature dimensionality]")
    print(f"  mode B: {len(model_B.feature_order)} features -> {model_B.feature_order}")
    print(f"  mode C: {len(model_C.feature_order)} features -> {model_C.feature_order}")
    dim_diff = len(model_C.feature_order) - len(model_B.feature_order)
    print(f"  dimensionality diff (C - B) = {dim_diff}")
    assert dim_diff == len(_C_EXTRA_KEYS), \
        f"mode C should add exactly the {len(_C_EXTRA_KEYS)} other-certificate features over mode B"
    print(f"  PASS: mode C adds exactly the {len(_C_EXTRA_KEYS)} other-certificate features over mode B")

    print("\nALL SELF-TEST ASSERTIONS PASSED")
