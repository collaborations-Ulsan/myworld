#!/usr/bin/env python3
"""AIOS Epistemic Gate v1 — blocking middleware for the turn loop (masterplan §4 M1).

docs/AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md §4 M1: wire a per-turn gate into
`aios_turn_loop.run_loop` that judges a proposed action BEFORE it dispatches — an
IRIS-typed verdict (CLAIM/ABSTAIN/MISSPECIFIED/NEXT_INTERVENTION), not a post-hoc
diagnostic. A rejected proposal is fed back as "Turn Rejected: <reasons>. Rewrite."
(the existing resample mechanism); the loop's circuit breaker gives it a named exit
(no infinite reject loop).

Seam: `aios_turn_loop.run_loop()` takes an optional `epistemic_gate` callable
(proposal: dict, context: dict) -> GateVerdict-like, invoked once per ToolCall
immediately before the existing authority gate (scripts/aios_turn_loop.py, the
`for call in calls:` block). Kept purely additive — default `None`, zero behavior
change for every existing caller/test. See that function's docstring for the exact
insertion point.

Three ablation modes (constructor `mode=` or env `AIOS_GATE_MODE`; masterplan §2 A4):
  off        — always passes; records "nothing checked" (the null arm).
  llm-judge  — one cheap self-check LLM call via the existing ollama_rest adapter
               (scripts/aios_adapters.py); if the endpoint is unreachable it
               HONESTLY reports UNAVAILABLE (never fabricates a verdict) and passes.
  organs     — the real gate: the shipped H0 poison/consistency filter
               (scripts/aios_akashic_guard.py, unmodified) + the ASC-0281 witness's
               APEX/DescentNet certifiers (experiments/agi_witness/{contracts,claims}.py
               + certs/{apex,descent}.py, unmodified — see docs/aios_completion_atlas/
               M1a_CERTIFICATE_INTERFACE.md for the cert contract this reuses).

Budget parity (masterplan §5 leakage traps / A4): organs mode is CONTRACTUALLY
zero-LLM-call — the five witness certs are pure numpy/stdlib functions of claim
structure (M1a §0 property 1) — so it can never out-call llm-judge's exactly-one
adapter call. Nothing in this module makes a model call outside `_gate_llm_judge`.

Honest scope limits (named, not papered over — mirrors M1a's own H-M1a-1):
  - The organs checks only run on STRUCTURED evidence a caller supplies explicitly:
    `context["known_claims"]` / `proposal["claims"]` (IO/PROPERTY/ORDER claim dicts,
    see experiments/agi_witness/contracts.py:Claim) for the APEX/DescentNet check, and
    `context["profiles_population"]` (commons-entry dicts: {"category","top_tools"})
    for the H0 guard check. A free-text-proposal -> claim-set extractor does not exist
    yet (M1a flagged this as unspecified M4 work); without that evidence the relevant
    check honestly reports status="skipped", never a fabricated pass.
  - `aios_turn_loop.py`'s trajectory is deliberately content-free (DNA #7 — names/
    status only), so this module cannot and does not try to reconstruct claims from
    the turn loop's own execution history; a caller that wants deep checks enriches
    `context` itself before calling the gate.

Never silently passes on internal error: any exception inside `gate()` returns
passed=False, verdict=MISSPECIFIED, reason="gate_error:<...>" (fail-closed), unless
env `AIOS_GATE_FAILOPEN=1` is set (debugging escape hatch only).

Schema: aios.epistemic_gate.v1
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
WITNESS_ROOT = ROOT / "experiments" / "agi_witness"

# IRIS-typed verdict grammar (masterplan §0).
CLAIM = "CLAIM"
ABSTAIN = "ABSTAIN"
MISSPECIFIED = "MISSPECIFIED"
NEXT_INTERVENTION = "NEXT_INTERVENTION"
_VERDICTS = frozenset({CLAIM, ABSTAIN, MISSPECIFIED, NEXT_INTERVENTION})

_MODES = ("off", "llm-judge", "organs")


@dataclass
class GateVerdict:
    verdict: str
    passed: bool
    reasons: list[str] = field(default_factory=list)
    certificates: dict[str, Any] = field(default_factory=dict)
    mode: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── ASC-0281 witness cert modules — best-effort import, never a hard dependency ──

def _import_certs() -> dict[str, Any]:
    """Import the witness's contracts/claims/apex/descent modules (copy-forward
    evidence tree per M1a §3 — never modified here). Degrades honestly: returns a
    dict with `_import_error` set instead of raising, so a moved/removed experiment
    tree never crashes the gate."""
    if str(WITNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(WITNESS_ROOT))
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))   # descent.py imports aios_akashic_guard from here
    try:
        import contracts as _contracts          # noqa: PLC0415
        import claims as _claims                # noqa: PLC0415
        from certs import apex as _apex          # noqa: PLC0415
        from certs import descent as _descent    # noqa: PLC0415
        return {"contracts": _contracts, "claims": _claims, "apex": _apex, "descent": _descent}
    except Exception as exc:  # noqa: BLE001 — evidence tree missing/moved is a fact to report, not a crash
        return {"_import_error": str(exc)[:200]}


def _import_guard():
    """Import the shipped H0 commons guard (scripts/aios_akashic_guard.py), unmodified."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import aios_akashic_guard as _guard      # noqa: PLC0415
        return _guard
    except Exception:  # noqa: BLE001
        return None


def _claim_from_dict(d: dict, Claim, ClaimKind):
    return Claim(
        task_id=str(d.get("task_id", "turn")),
        source_id=str(d.get("source_id", "unknown")),
        kind=ClaimKind(d.get("kind", "io")),
        payload=dict(d.get("payload") or {}),
        ts=int(d.get("ts", 0)),
    )


def _h0_guard_check(proposal: dict, context: dict) -> dict:
    """H0 consistency filter (masterplan §4 M1): is the proposed tool typical for its
    declared category, per the SAME self-calibrated per-category p95 the commons guard
    already ships (scripts/aios_akashic_guard.py:build_profiles/poison_score, unmodified)?
    `context["profiles_population"]` supplies the population to calibrate against —
    without it the check honestly skips (no fabricated pass)."""
    guard = _import_guard()
    if guard is None:
        return {"cert": "h0guard", "status": "unavailable", "reason": "aios_akashic_guard not importable"}
    population = context.get("profiles_population")
    if not population:
        return {"cert": "h0guard", "status": "skipped", "reason": "no profiles_population in context"}
    try:
        profiles = guard.build_profiles(population)
        category = str(proposal.get("category", "uncategorized"))
        tool = proposal.get("tool")
        candidate = {"category": category, "top_tools": [str(tool)] if tool else []}
        score = guard.poison_score(candidate, profiles)
        thresh = profiles.get(category, {}).get("thresh", 1.0)
        flagged = guard._flagged(score, category, profiles)  # noqa: SLF001 — repo-idiom cross-module reuse
        return {"cert": "h0guard", "status": "ok", "category": category,
                "score": score, "threshold": round(float(thresh), 3), "flagged": bool(flagged)}
    except Exception as exc:  # noqa: BLE001
        return {"cert": "h0guard", "status": "error", "reason": str(exc)[:150]}


def _apex_descent_check(proposal: dict, context: dict) -> list[dict]:
    """Answerability (APEX) + internal-consistency (DescentNet H0) checks over an
    explicit claim set — `context["known_claims"]` (prior evidence on record) plus
    `proposal["claims"]` (what this proposal itself asserts). Reuses
    experiments/agi_witness/{contracts,claims}.py + certs/{apex,descent}.py verbatim
    (ASC-0281 witness modules) — no reimplementation of the certifiers' math."""
    mods = _import_certs()
    if "_import_error" in mods:
        reason = mods["_import_error"]
        return [{"cert": "apex", "status": "unavailable", "reason": reason},
                {"cert": "descent", "status": "unavailable", "reason": reason}]

    raw = list(context.get("known_claims") or []) + list(proposal.get("claims") or [])
    if not raw:
        return [{"cert": "apex", "status": "skipped", "reason": "no claims provided"},
                {"cert": "descent", "status": "skipped", "reason": "no claims provided"}]

    Claim, ClaimKind = mods["contracts"].Claim, mods["contracts"].ClaimKind
    try:
        claim_objs = [_claim_from_dict(d, Claim, ClaimKind) for d in raw]
    except Exception as exc:  # noqa: BLE001 — malformed claim payloads are a caller-input fact, not a crash
        reason = f"malformed claims: {str(exc)[:140]}"
        return [{"cert": "apex", "status": "error", "reason": reason},
                {"cert": "descent", "status": "error", "reason": reason}]

    results: list[dict] = []
    try:
        apex_mod = mods["apex"]
        threshold = int(context.get("apex_threshold", 1))
        calib = apex_mod.ApexCalib(threshold=threshold, metadata={"source": "gate_default_uncalibrated"})
        cert = apex_mod.apex_certify(claim_objs, calib)
        results.append({"cert": "apex", "status": "ok", "label": cert.label.value,
                        "conf": cert.conf, "coverage_gaps": cert.coverage_gaps,
                        "n_claims": len(claim_objs), "calib_ref": None})
    except Exception as exc:  # noqa: BLE001
        results.append({"cert": "apex", "status": "error", "reason": str(exc)[:150]})

    try:
        descent_mod = mods["descent"]
        cert = descent_mod.descent_certify(claim_objs)
        results.append({"cert": "descent", "status": "ok",
                        "h0_conflicts": [list(p) for p in cert.h0_conflicts],
                        "h1_cycles": cert.h1_cycles, "hf": cert.hf, "n_claims": len(claim_objs)})
    except Exception as exc:  # noqa: BLE001
        results.append({"cert": "descent", "status": "error", "reason": str(exc)[:150]})
    return results


class EpistemicGate:
    """Blocking epistemic middleware for `aios_turn_loop.run_loop` (masterplan §4 M1).

    `gate(proposal, context) -> GateVerdict`. Never raises: on internal error it
    fail-closes (passed=False, verdict=MISSPECIFIED) unless AIOS_GATE_FAILOPEN=1.
    """

    def __init__(self, mode: str | None = None):
        resolved = (mode or os.environ.get("AIOS_GATE_MODE") or "organs").strip().lower()
        self.mode = resolved if resolved in _MODES else "organs"

    def gate(self, proposal: dict, context: dict | None = None) -> GateVerdict:
        context = context or {}
        try:
            if self.mode == "off":
                return GateVerdict(verdict=CLAIM, passed=True, reasons=[],
                                   certificates={"note": "gate_off_nothing_checked"}, mode="off")
            if self.mode == "llm-judge":
                return self._gate_llm_judge(proposal, context)
            return self._gate_organs(proposal, context)
        except Exception as exc:  # noqa: BLE001 — fail-closed is the contract, not a bug to silence
            if os.environ.get("AIOS_GATE_FAILOPEN") == "1":
                return GateVerdict(verdict=CLAIM, passed=True,
                                   reasons=[f"gate_error_failopen:{str(exc)[:150]}"],
                                   certificates={}, mode=self.mode)
            return GateVerdict(verdict=MISSPECIFIED, passed=False,
                               reasons=[f"gate_error:{str(exc)[:150]}"],
                               certificates={}, mode=self.mode)

    # -- llm-judge -----------------------------------------------------------

    def _gate_llm_judge(self, proposal: dict, context: dict) -> GateVerdict:
        try:
            import aios_adapters as adapters  # noqa: PLC0415
        except Exception as exc:  # noqa: BLE001
            return GateVerdict(verdict=CLAIM, passed=True,
                               reasons=["llm_judge_unavailable:import_failed"],
                               certificates={"llm_judge": {"status": "unavailable", "reason": str(exc)[:120]}},
                               mode="llm-judge")
        if not adapters._ollama_rest_available():  # noqa: SLF001 — repo idiom, see aios_adapters callers
            return GateVerdict(verdict=CLAIM, passed=True,
                               reasons=["llm_judge_unavailable:endpoint_unreachable"],
                               certificates={"llm_judge": {"status": "unavailable",
                                                            "reason": "ollama_rest endpoint unreachable"}},
                               mode="llm-judge")
        prompt = (
            "Self-check gate. Reply with exactly one word: CONSISTENT or INCONSISTENT.\n"
            f"Proposed tool: {proposal.get('tool')}\n"
            f"Goal (truncated): {str(context.get('goal', ''))[:200]}\n"
        )
        try:
            reply = adapters.make_ollama_rest_adapter(timeout=20)(prompt)
        except Exception as exc:  # noqa: BLE001 — one call attempted; failure degrades honestly
            return GateVerdict(verdict=CLAIM, passed=True,
                               reasons=["llm_judge_unavailable:call_failed"],
                               certificates={"llm_judge": {"status": "unavailable", "reason": str(exc)[:120]}},
                               mode="llm-judge")
        inconsistent = "INCONSISTENT" in reply.upper()
        cert = {"llm_judge": {"status": "ok", "result": "INCONSISTENT" if inconsistent else "CONSISTENT"}}
        if inconsistent:
            return GateVerdict(verdict=MISSPECIFIED, passed=False,
                               reasons=["llm_judge_flagged_inconsistent"], certificates=cert, mode="llm-judge")
        return GateVerdict(verdict=CLAIM, passed=True, reasons=[], certificates=cert, mode="llm-judge")

    # -- organs ---------------------------------------------------------------

    def _gate_organs(self, proposal: dict, context: dict) -> GateVerdict:
        certificates: dict[str, Any] = {}
        reasons: list[str] = []
        passed = True
        verdict = str(proposal.get("verdict", CLAIM)).upper()
        if verdict not in _VERDICTS:
            verdict = CLAIM

        h0 = _h0_guard_check(proposal, context)
        certificates["h0guard"] = h0
        if h0.get("status") == "ok" and h0.get("flagged"):
            passed = False
            verdict = MISSPECIFIED
            reasons.append(f"h0guard_flagged:score={h0.get('score')}_gt_thresh={h0.get('threshold')}")

        for cert in _apex_descent_check(proposal, context):
            certificates[cert["cert"]] = cert
            if cert.get("status") != "ok":
                continue
            if cert["cert"] == "apex" and cert.get("label") == "CONTRADICTORY":
                passed = False
                verdict = MISSPECIFIED
                reasons.append("apex_contradictory")
            elif cert["cert"] == "apex" and cert.get("label") == "UNDERDETERMINED":
                passed = False
                if verdict != MISSPECIFIED:
                    verdict = ABSTAIN
                reasons.append("apex_underdetermined")
            if cert["cert"] == "descent" and cert.get("h0_conflicts"):
                passed = False
                verdict = MISSPECIFIED
                reasons.append(f"descent_h0_conflict:{cert['h0_conflicts']}")

        return GateVerdict(verdict=verdict, passed=passed, reasons=reasons,
                           certificates=certificates, mode="organs")


def make_gate(mode: str | None = None) -> Callable[[dict, dict], GateVerdict]:
    """DI-style factory matching `aios_tools.gate_for` — returns a bound callable
    suitable for `aios_turn_loop.run_loop(..., epistemic_gate=make_gate())`."""
    return EpistemicGate(mode=mode).gate


if __name__ == "__main__":
    for demo_mode in _MODES:
        g = EpistemicGate(mode=demo_mode)
        v = g.gate({"tool": "fs.read", "arguments": {"path": "docs/README.md"}}, {"goal": "read a doc"})
        print(demo_mode, "->", json.dumps(v.to_dict(), ensure_ascii=False))
