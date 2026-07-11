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

Per-organ disable (ASC-0282 / prereg v1.1 §C ablation-replay gate): constructor
`disabled_organs={"apex","descent","h0guard","provenance"}` or env
`AIOS_GATE_DISABLE_ORGANS` (comma-separated). An unknown organ name raises
ValueError at construction (fail-fast) — a typo'd name must never silently run
with the organ still enabled, which would corrupt the §C causal-credit count.
A disabled organ is recorded as status="disabled" (never counted as checked,
never as an infra failure, never blocks) so a frozen A4 trace can be replayed
with exactly ONE organ removed and the success flip attributed. Disabling ALL
organs degenerates to the no-evidence ABSTAIN path, not to the off arm — replay
always disables exactly one. `provenance` (§C organ (iii), "provenance guard")
is a STUB in this packet: reports status="not_implemented" whenever enabled, so
it always appears in the gate record (no silent skip, no fabricated pass); the
real check is a later work packet.

Three ablation modes (constructor `mode=` or env `AIOS_GATE_MODE`; masterplan §2 A4):
  off        — always passes; records "nothing checked" (the null arm).
  llm-judge  — exactly ONE self-check LLM call attempt via the existing ollama_rest
               adapter (scripts/aios_adapters.py) on every path (budget parity);
               an unreachable/failed judge FAIL-CLOSES (reported unavailable, blocks)
               so a dead judge arm can never silently degrade into the off arm.
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
    checked: int = 0          # how many checks actually RAN (status=ok) — 0 means nothing was verified
    infra_failures: int = 0   # checks that SHOULD have run but couldn't (unavailable/error)

    def to_dict(self) -> dict:
        return asdict(self)


def _fail_closed(reasons: list[str], certificates: dict, mode: str,
                 checked: int = 0, infra_failures: int = 0) -> GateVerdict:
    """Fail-closed verdict, honoring the AIOS_GATE_FAILOPEN=1 debugging escape hatch."""
    if os.environ.get("AIOS_GATE_FAILOPEN") == "1":
        return GateVerdict(verdict=CLAIM, passed=True,
                           reasons=[f"failopen:{r}" for r in reasons],
                           certificates=certificates, mode=mode,
                           checked=checked, infra_failures=infra_failures)
    return GateVerdict(verdict=MISSPECIFIED, passed=False, reasons=reasons,
                       certificates=certificates, mode=mode,
                       checked=checked, infra_failures=infra_failures)


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


def _apex_descent_check(proposal: dict, context: dict,
                        disabled: frozenset = frozenset()) -> list[dict]:
    """Answerability (APEX) + internal-consistency (DescentNet H0) checks over an
    explicit claim set — `context["known_claims"]` (prior evidence on record) plus
    `proposal["claims"]` (what this proposal itself asserts). Reuses
    experiments/agi_witness/{contracts,claims}.py + certs/{apex,descent}.py verbatim
    (ASC-0281 witness modules) — no reimplementation of the certifiers' math.
    `disabled` (prereg v1.1 §C): organs to skip entirely, recorded as status="disabled"."""
    def _disabled_entry(name: str) -> dict:
        return {"cert": name, "status": "disabled", "reason": "ablation_replay_disabled"}

    if "apex" in disabled and "descent" in disabled:
        return [_disabled_entry("apex"), _disabled_entry("descent")]

    mods = _import_certs()
    if "_import_error" in mods:
        reason = mods["_import_error"]
        return [_disabled_entry("apex") if "apex" in disabled
                else {"cert": "apex", "status": "unavailable", "reason": reason},
                _disabled_entry("descent") if "descent" in disabled
                else {"cert": "descent", "status": "unavailable", "reason": reason}]

    raw = list(context.get("known_claims") or []) + list(proposal.get("claims") or [])
    if not raw:
        return [_disabled_entry("apex") if "apex" in disabled
                else {"cert": "apex", "status": "skipped", "reason": "no claims provided"},
                _disabled_entry("descent") if "descent" in disabled
                else {"cert": "descent", "status": "skipped", "reason": "no claims provided"}]

    Claim, ClaimKind = mods["contracts"].Claim, mods["contracts"].ClaimKind
    try:
        claim_objs = [_claim_from_dict(d, Claim, ClaimKind) for d in raw]
    except Exception as exc:  # noqa: BLE001 — malformed claim payloads are a caller-input fact, not a crash
        reason = f"malformed claims: {str(exc)[:140]}"
        return [{"cert": "apex", "status": "error", "reason": reason},
                {"cert": "descent", "status": "error", "reason": reason}]

    results: list[dict] = []
    if "apex" in disabled:
        results.append(_disabled_entry("apex"))
    else:
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

    if "descent" in disabled:
        results.append(_disabled_entry("descent"))
    else:
        try:
            descent_mod = mods["descent"]
            cert = descent_mod.descent_certify(claim_objs)
            results.append({"cert": "descent", "status": "ok",
                            "h0_conflicts": [list(p) for p in cert.h0_conflicts],
                            "h1_cycles": cert.h1_cycles, "hf": cert.hf, "n_claims": len(claim_objs)})
        except Exception as exc:  # noqa: BLE001
            results.append({"cert": "descent", "status": "error", "reason": str(exc)[:150]})
    return results


def _provenance_check(proposal: dict, context: dict) -> dict:
    """Provenance guard — prereg v1.1 §C organ (iii). STUB in this packet (ASC-0282
    WP-A reserves the slot so the ablation-replay gate can already ablate all three
    named organs; the real check is a later work packet). Always appears in the gate
    record when enabled, explicitly status="not_implemented" so it can never read
    downstream as a verified pass (mirrors this module's no-fabricated-pass contract)."""
    return {"cert": "provenance", "status": "not_implemented", "verdict": CLAIM}


class EpistemicGate:
    """Blocking epistemic middleware for `aios_turn_loop.run_loop` (masterplan §4 M1).

    `gate(proposal, context) -> GateVerdict`. Never raises: on internal error it
    fail-closes (passed=False, verdict=MISSPECIFIED) unless AIOS_GATE_FAILOPEN=1.
    """

    _ORGANS = ("h0guard", "apex", "descent", "provenance")

    def __init__(self, mode: str | None = None,
                 disabled_organs: "set[str] | None" = None):
        resolved = (mode or os.environ.get("AIOS_GATE_MODE") or "organs").strip().lower()
        self.mode = resolved if resolved in _MODES else "organs"
        raw = (set(disabled_organs) if disabled_organs is not None
               else {s.strip() for s in os.environ.get("AIOS_GATE_DISABLE_ORGANS", "").split(",") if s.strip()})
        unknown = raw - set(self._ORGANS)
        if unknown:
            raise ValueError(f"unknown organ name(s) in disabled_organs: {sorted(unknown)} "
                             f"(valid: {list(self._ORGANS)})")
        self.disabled_organs = frozenset(raw)

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
        """Exactly ONE adapter call attempt on every path (budget parity, masterplan §5).
        An unavailable judge FAIL-CLOSES: a judge arm whose judge is dead must block
        loudly, not silently degrade into the off arm (2026-07-10 codex review #4/#7).
        """
        try:
            import aios_adapters as adapters  # noqa: PLC0415
        except Exception as exc:  # noqa: BLE001
            return _fail_closed(["llm_judge_unavailable:import_failed"],
                                {"llm_judge": {"status": "unavailable", "reason": str(exc)[:120]}},
                                "llm-judge", checked=0, infra_failures=1)
        prompt = (
            "Self-check gate. Reply with exactly one word: CONSISTENT or INCONSISTENT.\n"
            f"Proposed tool: {proposal.get('tool')}\n"
            f"Goal (truncated): {str(context.get('goal', ''))[:200]}\n"
        )
        try:
            reply = adapters.make_ollama_rest_adapter(timeout=20)(prompt)
        except Exception as exc:  # noqa: BLE001 — the one allowed call failed: fail-closed, honestly reported
            return _fail_closed(["llm_judge_unavailable:call_failed"],
                                {"llm_judge": {"status": "unavailable", "reason": str(exc)[:120]}},
                                "llm-judge", checked=0, infra_failures=1)
        inconsistent = "INCONSISTENT" in reply.upper()
        cert = {"llm_judge": {"status": "ok", "result": "INCONSISTENT" if inconsistent else "CONSISTENT"}}
        if inconsistent:
            return GateVerdict(verdict=MISSPECIFIED, passed=False,
                               reasons=["llm_judge_flagged_inconsistent"], certificates=cert,
                               mode="llm-judge", checked=1)
        return GateVerdict(verdict=CLAIM, passed=True, reasons=[], certificates=cert,
                           mode="llm-judge", checked=1)

    # -- organs ---------------------------------------------------------------

    def _gate_organs(self, proposal: dict, context: dict) -> GateVerdict:
        certificates: dict[str, Any] = {}
        reasons: list[str] = []
        passed = True
        checked = 0
        infra_failures = 0
        verdict = str(proposal.get("verdict", CLAIM)).upper()
        if verdict not in _VERDICTS:
            verdict = CLAIM
        # Always present (empty when nothing disabled) — WP-C's ablation-replay engine
        # reads this record and needs a uniform shape to grep/replay against.
        certificates["_disabled_organs"] = sorted(self.disabled_organs)

        if "h0guard" in self.disabled_organs:
            h0 = {"cert": "h0guard", "status": "disabled", "reason": "ablation_replay_disabled"}
        else:
            h0 = _h0_guard_check(proposal, context)
        certificates["h0guard"] = h0
        if h0.get("status") == "ok" and h0.get("flagged"):
            passed = False
            verdict = MISSPECIFIED
            reasons.append(f"h0guard_flagged:score={h0.get('score')}_gt_thresh={h0.get('threshold')}")

        if "provenance" in self.disabled_organs:
            prov = {"cert": "provenance", "status": "disabled", "reason": "ablation_replay_disabled"}
        else:
            prov = _provenance_check(proposal, context)

        for cert in [h0, prov] + _apex_descent_check(proposal, context, self.disabled_organs):
            certificates[cert["cert"]] = cert
            status = cert.get("status")
            if status == "ok":
                checked += 1
            elif status in ("unavailable", "error"):
                infra_failures += 1
            if status != "ok":
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

        # No check actually ran: never let that read as a verified pass downstream
        # (2026-07-10 codex review #1/#5 — the silent-pass risk the gate exists to kill).
        if checked == 0:
            if infra_failures:
                # organs arm whose organs are DEAD is an invalid arm — block loudly.
                return _fail_closed(["organs_infrastructure_unavailable"], certificates,
                                    "organs", checked=0, infra_failures=infra_failures)
            # No structured evidence supplied: honest ABSTAIN, explicitly labeled.
            reasons.append("no_applicable_checks")
            strict = os.environ.get("AIOS_GATE_STRICT") == "1"
            return GateVerdict(verdict=ABSTAIN, passed=not strict, reasons=reasons,
                               certificates=certificates, mode="organs",
                               checked=0, infra_failures=0)

        return GateVerdict(verdict=verdict, passed=passed, reasons=reasons,
                           certificates=certificates, mode="organs",
                           checked=checked, infra_failures=infra_failures)


def make_gate(mode: str | None = None,
              disabled_organs: "set[str] | None" = None) -> Callable[[dict, dict], GateVerdict]:
    """DI-style factory matching `aios_tools.gate_for` — returns a bound callable
    suitable for `aios_turn_loop.run_loop(..., epistemic_gate=make_gate())`.
    `disabled_organs` (prereg v1.1 §C): per-organ ablation-replay switch, any of
    EpistemicGate._ORGANS ("h0guard"/"apex"/"descent"/"provenance")."""
    return EpistemicGate(mode=mode, disabled_organs=disabled_organs).gate


if __name__ == "__main__":
    for demo_mode in _MODES:
        g = EpistemicGate(mode=demo_mode)
        v = g.gate({"tool": "fs.read", "arguments": {"path": "docs/README.md"}}, {"goal": "read a doc"})
        print(demo_mode, "->", json.dumps(v.to_dict(), ensure_ascii=False))
