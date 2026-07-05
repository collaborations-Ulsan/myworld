"""APEX — the answerability type calculus (Fable §2: conformal answerability certificate).

APEX asks one question about a claim set: *is there enough independent, non-contradictory
evidence in the ledger to answer, or should the system honestly abstain?* It never calls an
LLM — it is a pure, deterministic function of the claim structure — and it never reads
``Claim.poisoned`` (that field is ground truth for scoring only; reading it here would let the
certificate cheat).

Three labels (``contracts.ApexLabel``):
  * ``CONTRADICTORY``   — the claims disagree with themselves (H0 conflict). Highest-priority
    check: contradictory evidence makes "answerable" meaningless regardless of volume.
  * ``ANSWERABLE``      — enough independent constraints pin the behavior down, per a threshold
    chosen by conformal calibration (see ``fit_apex``).
  * ``UNDERDETERMINED`` — too few independent constraints. ``coverage_gaps`` names what kind of
    evidence is missing so arm C can steer IRIS (identifiability) toward exactly that gap.

Design note on "coverage": a single executable IO claim pins one input->output behavior point;
a PROPERTY constraint (e.g. "return type is int") pins a structural fact independent of any
single IO point. Both are independent bits of evidence, so coverage counts BOTH kinds and adds
them — this mirrors ``build_claim_graph``'s grouping (same input / same property name) without
duplicating that function; here we only need cardinalities, not the signed graph.

Constraints: stdlib + numpy only, deterministic, no ground-truth reads. Types come from
``contracts.py``; claim-graph primitives come from ``claims.py`` — this module never
reimplements ``direct_io_conflicts`` or ``executable_claims``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from contracts import ApexCert, ApexLabel, Claim, ClaimKind
from claims import direct_io_conflicts, executable_claims


# =============================================================================
# Calibration artifact
# =============================================================================

@dataclass
class ApexCalib:
    """Output of conformal calibration (``fit_apex``): the coverage threshold at/above which
    a claim set is certified ANSWERABLE, plus metadata documenting how it was chosen."""
    threshold: int
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Coverage primitive (shared by apex_certify and fit_apex)
# =============================================================================

def _prop_name(payload: dict) -> Any:
    """Same tolerant PROPERTY-payload shape claims.py's seeders use: {"prop"|"name", "value"}."""
    return payload.get("prop", payload.get("name"))


def _coverage_detail(claims: list[Claim]) -> dict[str, Any]:
    """Count independent constraints in ``claims``.

    coverage = (# executable IO claims) + (# distinct (task_id, property-name) groups).
    Each executable IO claim pins one input->output point; each distinct PROPERTY group pins
    one structural fact — both are independent evidence, counted once per distinct source of
    constraint (multiple claims restating the SAME property name on the SAME task are one
    constraint, not two, whether or not they agree — agreement/conflict is DescentNet's job,
    not APEX's; APEX only asks "is there enough independent evidence").
    """
    io_idx = executable_claims(claims)

    prop_groups: dict[tuple, list[int]] = {}
    for i, c in enumerate(claims):
        if c.kind == ClaimKind.PROPERTY:
            prop_groups.setdefault((c.task_id, _prop_name(c.payload)), []).append(i)
    prop_rep_idx = [idxs[0] for idxs in prop_groups.values()]  # one representative index/group

    return {
        "io_idx": io_idx,
        "n_io": len(io_idx),
        "prop_groups": prop_groups,
        "prop_rep_idx": prop_rep_idx,
        "n_prop": len(prop_groups),
        "coverage": len(io_idx) + len(prop_groups),
    }


def _coverage_gaps(cov: dict[str, Any], threshold: int) -> list[dict]:
    """Name the uncovered constraint kinds for an UNDERDETERMINED verdict — these steer IRIS
    (arm C) toward exactly the evidence that would flip the certificate."""
    gaps: list[dict] = []
    if cov["n_io"] == 0:
        gaps.append({"kind": "io", "reason": "no executable IO claims", "have": 0, "threshold": threshold})
    elif cov["n_io"] < threshold:
        gaps.append({"kind": "io", "reason": "too few pinned inputs", "have": cov["n_io"], "threshold": threshold})
    if cov["n_prop"] == 0:
        gaps.append({"kind": "property", "reason": "no distinct property constraints", "have": 0, "threshold": threshold})
    if not gaps:
        # Both kinds present but their SUM still falls short of threshold.
        gaps.append({
            "kind": "coverage",
            "reason": "combined io+property constraints below threshold",
            "have": cov["coverage"],
            "threshold": threshold,
        })
    return gaps


def _confidence(margin: float) -> float:
    """Deterministic, monotonic squashing of a coverage margin into (0, 1): a logistic curve
    centered at the threshold (margin=0 -> 0.5; more coverage above threshold -> conf -> 1;
    below -> conf -> 0). No randomness, no wall-clock — purely a function of ``margin``."""
    return float(1.0 / (1.0 + np.exp(-margin)))


# =============================================================================
# The certificate
# =============================================================================

def apex_certify(claims: list[Claim], calib: ApexCalib) -> ApexCert:
    """Certify whether ``claims`` answer their task(s), per the conformal threshold in ``calib``.

    Order of checks (contradiction always wins — see module docstring):
      1. ``direct_io_conflicts`` non-empty -> CONTRADICTORY.
      2. else coverage >= ``calib.threshold`` -> ANSWERABLE (support_set = backing claim indices).
      3. else -> UNDERDETERMINED (``coverage_gaps`` names what's missing).
    """
    conflicts = direct_io_conflicts(claims)
    if conflicts:
        # Flatten the conflicting index pairs into support_set (the evidence the label rests
        # on), and note the pairs themselves in coverage_gaps for anyone inspecting the cert.
        support = sorted({i for pair in conflicts for i in pair})
        conf = min(0.99, 0.9 + 0.03 * len(conflicts))  # more conflicting pairs -> more certain
        return ApexCert(
            label=ApexLabel.CONTRADICTORY,
            conf=conf,
            support_set=support,
            coverage_gaps=[{"kind": "contradiction", "pairs": [list(p) for p in conflicts]}],
        )

    cov = _coverage_detail(claims)
    coverage = cov["coverage"]
    margin = coverage - calib.threshold

    if coverage >= calib.threshold:
        support = sorted(set(cov["io_idx"]) | set(cov["prop_rep_idx"]))
        return ApexCert(
            label=ApexLabel.ANSWERABLE,
            conf=_confidence(margin),
            support_set=support,
            coverage_gaps=[],
        )

    return ApexCert(
        label=ApexLabel.UNDERDETERMINED,
        conf=_confidence(margin),  # margin < 0 here -> conf < 0.5, honestly low
        support_set=[],
        coverage_gaps=_coverage_gaps(cov, calib.threshold),
    )


# =============================================================================
# Conformal calibration
# =============================================================================

def fit_apex(calib_examples: list[tuple[list[Claim], bool]]) -> ApexCalib:
    """Choose the coverage threshold conformally: the SMALLEST threshold whose ANSWERABLE
    subset (coverage >= threshold) has empirical solve rate >= 0.8 on ``calib_examples``.

    Each example is (claims-for-one-task-instance, solved: bool) — did the system that
    produced/consumed this claim set go on to a verified solve. Examples whose claims are
    already CONTRADICTORY are excluded from the fit: ``apex_certify`` labels them
    CONTRADICTORY regardless of the coverage threshold, so they carry no information about
    where to set it.

    If every candidate threshold fails the 0.8 bar (or there is no non-contradictory calib
    data at all), fall back to the most conservative threshold — one above the maximum
    observed coverage, so nothing is ever certified ANSWERABLE until real evidence says
    otherwise. This is the honest, safe default of a conformal method that ran out of margin.
    """
    scored: list[tuple[int, bool]] = []
    n_contradictory = 0
    for claims, solved in calib_examples:
        if direct_io_conflicts(claims):
            n_contradictory += 1
            continue
        scored.append((_coverage_detail(claims)["coverage"], bool(solved)))

    if not scored:
        return ApexCalib(
            threshold=1,
            metadata={
                "n_calib": len(calib_examples),
                "n_contradictory": n_contradictory,
                "n_scored": 0,
                "solve_rate_at_threshold": None,
                "note": "no non-contradictory calib examples; conservative fallback threshold",
            },
        )

    max_cov = max(cov for cov, _ in scored)
    # Candidate thresholds: every observed coverage value (ascending), plus one above the max
    # as the "never answerable" fallback if nothing else clears the 0.8 bar.
    candidates = sorted(set(cov for cov, _ in scored)) + [max_cov + 1]

    chosen = candidates[-1]
    chosen_rate = None
    for t in candidates:
        subset = [solved for cov, solved in scored if cov >= t]
        if not subset:
            continue
        rate = sum(subset) / len(subset)
        if rate >= 0.8:
            chosen = t
            chosen_rate = rate
            break

    return ApexCalib(
        threshold=chosen,
        metadata={
            "n_calib": len(calib_examples),
            "n_contradictory": n_contradictory,
            "n_scored": len(scored),
            "solve_rate_at_threshold": chosen_rate,
        },
    )


# =============================================================================
# Self-test (SYNTHETIC claims only — no dataset.py dependency)
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("certs/apex.py self-test")
    print("=" * 70)

    def _mk(task_id: str, n_io: int, n_prop: int) -> list[Claim]:
        """Build a synthetic, non-contradictory claim set with an exact coverage of n_io + n_prop:
        n_io distinct-input IO claims (all consistent) + n_prop distinct-named PROPERTY claims."""
        out: list[Claim] = []
        for i in range(n_io):
            out.append(Claim(task_id, f"io_src{i}", ClaimKind.IO,
                              {"input": [i], "output": i * 2}, ts=i))
        for j in range(n_prop):
            out.append(Claim(task_id, f"prop_src{j}", ClaimKind.PROPERTY,
                              {"prop": f"p{j}", "value": "v"}, ts=100 + j))
        return out

    # --- 1. Fit a conformal threshold over a tiny synthetic calibration set -----------------
    # Designed so coverage>=4 is the smallest bucket clearing the 0.8 solve-rate bar:
    #   cov=1: [F]                    -> rate 0/1
    #   cov=2: [F, T]                 -> cumulative (cov>=2) rate 3/6
    #   cov=3: [T, F]                 -> cumulative (cov>=3) rate 3/4
    #   cov=4: [T, T]                 -> cumulative (cov>=4) rate 2/2 = 1.0  <- first to clear 0.8
    calib_examples = [
        (_mk("cA1", 3, 1), True),   # coverage 4
        (_mk("cA2", 4, 0), True),   # coverage 4
        (_mk("cA3", 1, 1), False),  # coverage 2
        (_mk("cA4", 2, 0), True),   # coverage 2
        (_mk("cA5", 1, 0), False),  # coverage 1
        (_mk("cA6", 2, 1), True),   # coverage 3
        (_mk("cA7", 3, 0), False),  # coverage 3
    ]
    calib = fit_apex(calib_examples)
    print("\n[fit_apex]")
    print(f"  threshold = {calib.threshold}  metadata = {calib.metadata}")
    assert calib.threshold == 4, f"expected conformal threshold 4, got {calib.threshold}"
    assert calib.metadata["solve_rate_at_threshold"] == 1.0
    print("  PASS: smallest threshold clearing 80% solve rate is 4")

    # --- 2. Contradictory set: same input, two different outputs -> CONTRADICTORY ----------
    contra_claims = [
        Claim("t_contra", "srcA", ClaimKind.IO, {"input": [1, 2], "output": 3}, ts=0),
        Claim("t_contra", "srcB", ClaimKind.IO, {"input": [1, 2], "output": 4}, ts=1),
        Claim("t_contra", "srcC", ClaimKind.PROPERTY, {"prop": "return_type", "value": "int"}, ts=2),
    ]
    cert_contra = apex_certify(contra_claims, calib)
    print("\n[contradictory]")
    print(f"  label={cert_contra.label.value} conf={cert_contra.conf:.3f} "
          f"support_set={cert_contra.support_set} coverage_gaps={cert_contra.coverage_gaps}")
    assert cert_contra.label == ApexLabel.CONTRADICTORY
    assert cert_contra.conf >= 0.9
    assert set(cert_contra.support_set) == {0, 1}
    print("  PASS: same-input/different-output pair forces CONTRADICTORY regardless of coverage")

    # --- 3. Rich consistent set: coverage clears the fitted threshold -> ANSWERABLE ---------
    rich_claims = _mk("t_rich", 4, 1)  # coverage = 5 > threshold(4)
    cert_rich = apex_certify(rich_claims, calib)
    print("\n[rich/consistent]")
    print(f"  label={cert_rich.label.value} conf={cert_rich.conf:.3f} "
          f"support_set={cert_rich.support_set} coverage_gaps={cert_rich.coverage_gaps}")
    assert cert_rich.label == ApexLabel.ANSWERABLE
    assert cert_rich.support_set  # non-empty backing evidence
    assert cert_rich.coverage_gaps == []
    assert cert_rich.conf > 0.5, "coverage strictly above threshold must give conf > 0.5"
    print("  PASS: coverage 5 >= threshold 4 -> ANSWERABLE with non-empty support_set")

    # --- 4. Sparse set: coverage below threshold -> UNDERDETERMINED with named gaps ---------
    sparse_claims = _mk("t_sparse", 1, 0)  # coverage = 1 < threshold(4)
    cert_sparse = apex_certify(sparse_claims, calib)
    print("\n[sparse/underdetermined]")
    print(f"  label={cert_sparse.label.value} conf={cert_sparse.conf:.3f} "
          f"support_set={cert_sparse.support_set} coverage_gaps={cert_sparse.coverage_gaps}")
    assert cert_sparse.label == ApexLabel.UNDERDETERMINED
    assert cert_sparse.support_set == []
    assert len(cert_sparse.coverage_gaps) > 0, "gaps must be named so IRIS has something to act on"
    assert cert_sparse.conf < 0.5, "coverage strictly below threshold must give conf < 0.5"
    print("  PASS: coverage 1 < threshold 4 -> UNDERDETERMINED with non-empty coverage_gaps")

    print("\nALL SELF-TEST ASSERTIONS PASSED")
