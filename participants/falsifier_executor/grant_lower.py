"""grant_lower — deterministic CapabilityGrant -> cage flags (the base layer's
half of the seam contract). Imports nothing from aios_*: the lowering and the
enforcement-gap reasoning are reimplemented from the agreed prose so that
agreement with scripts/aios_contracts.py proves the seam, not a shared import.

Mapping (fixed with claude@myworld/upper):
    scope.fs_read  -> ro_paths + Landlock ro   (glob base dir)
    scope.fs_write -> rw_paths                  (glob base dir)
    scope.net:denied -> allow_net=False         (positive-control probe required)
    forbidden L5+  -> NOT lowerable; kept out by a signed human decision (Q-plane)
"""
from __future__ import annotations

import os

LADDER = ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8")
ENFORCEABLE_BY_CAGE = {"L0", "L1", "L2", "L3", "L4"}


def glob_base(glob: str) -> str:
    """Absolute glob -> the concrete directory a cage can bind. '/a/b/**' -> '/a/b'.
    Landlock path-beneath already covers the subtree, so the base dir is the
    right granularity."""
    base = glob
    for suffix in ("/**", "/*"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return os.path.normpath(base)


def lower(grant: dict) -> dict:
    """Returns cage flags + the enforcement gap. Pure; no side effects."""
    scope = grant.get("scope") or {}
    ro = [glob_base(g) for g in scope.get("fs_read", [])]
    rw = [glob_base(g) for g in scope.get("fs_write", [])]
    allow_net = scope.get("net", "allowed") != "denied"
    return {"ro_paths": ro, "rw_paths": rw, "allow_net": allow_net,
            "enforcement_gap": enforcement_gap(grant)}


def enforcement_gap(grant: dict) -> dict:
    """Which forbidden rungs a cage cannot refuse. Reimplemented from prose:
    a grant is real only where something refuses; L5+ has no cage lever."""
    forbidden = [a for a in grant.get("forbidden", []) if a in LADDER]
    unenforceable = [a for a in forbidden if a not in ENFORCEABLE_BY_CAGE]
    return {
        "cage_enforceable": [a for a in forbidden if a in ENFORCEABLE_BY_CAGE],
        "needs_signed_human_grant": unenforceable,
        # honest iff either no L5+ is forbidden, or the issuer acknowledged that
        # those rungs rely on a signed human decision, not on the cage.
        "honest": (not unenforceable) or bool(grant.get("acknowledged_unenforceable")),
    }
