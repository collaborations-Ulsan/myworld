#!/usr/bin/env python3
"""Arc conformance checker — did the work match what the arc declared?

**VALUE CLAIM WITHDRAWN 2026-08-05.** This module was built as "G2 — verified
handoff" for an agent society. G5 falsified the society: handing work to a
second agent scored 6.25pp WORSE than the same agent resuming from the same
record (128 cells, McNemar p = 0.856; `experiments/phase5g/G5_RESULTS.md`).
The society layer is dissolved and will not be rebuilt, so **"verified handoff"
is no longer a capability this project claims.**

What survives, and all this module may now be described as: a **conformance
checker** that judges whether the work recorded on an arc matches the goal,
constraints and external oracle that arc declared. That is useful for a single
agent resuming its own work — the configuration G5 actually favoured — and it
is the shape our sovereignty identity supports (verify and constrain, do not
claim to improve).

Two honest consequences of the withdrawal:
  * The `takeover_window` machinery still identifies an ownership transfer, but
    a transfer between DIFFERENT agents is now a rare/legacy case rather than
    the point. Applied to a single agent resuming itself, the verifier is
    checking that agent against its own prior declaration — which is weaker
    evidence than an independent check, and must be reported as such.
  * Nothing here should be cited as evidence that verification improves task
    outcomes. It does not; it makes outcomes *checkable*.

Original design notes follow, kept because the mechanism is unchanged.

---

G2 — Verified handoff: was the TAKEOVER faithful to the arc?

Goal tree: `docs/AIOS_SOCIETY_GOALTREE_2026-08-02.md` (G2). This module is the
society's answer to the sharpest red-team attack (2026-08-02, deepseek, lens
`goodhart`):

    "Verification checks that the handoff message is delivered and acknowledged,
     but not that the receiving agent's INTERPRETATION matches the sender's
     intent. A compressed summary can pass byte-fidelity checks while omitting
     critical constraints; the handoff metric passes, the task diverges."

So this verifier never scores the packet. **It scores what the taker DID after
taking over, against what the arc said it must do** (INV-2). It runs as a
separate identity from the taker (self-judging is not verification), and it runs
AFTER the resume, flagging the arc rather than gating it (INV-6 — a verifier
must never become a single point of failure for availability).

## What "faithful" means here (stated so it can fail)

Three checks over the taker's post-takeover events, in decreasing strength:

  1. **oracle** (strongest, only when the arc declares `oracle_cmd`): run the
     arc's own external command. This is the same external-oracle discipline the
     null program was built on — it cannot be talked around by either agent.
  2. **constraint** (deterministic): every arc constraint written as a
     `forbid:<regex>` / `require:<regex>` clause is machine-checked against the
     taker's events and cited evidence. Free-prose constraints are reported as
     `unenforceable` — never silently treated as satisfied.
  3. **continuity** (deterministic): did the taker actually continue THIS arc?
     It must reference the handoff's `next_step` or the arc goal (token overlap
     above a fixed floor) and must produce at least one progress event with
     evidence. A taker that starts an unrelated task passes byte-fidelity but
     fails here — which is exactly the attack.

`verdict` = `drifted` if any check fails; `faithful` if at least one check ran
and none failed; `unverifiable` if nothing could be checked (no oracle, no
machine-checkable constraint, no post-takeover activity). **`unverifiable` is
never reported as success** — silence is not a finding.

## Honest limitation (measured on the first live takeover, 2026-08-02)

The continuity check is **lexical**, so a taker that merely PARROTS the goal
back scores a perfect overlap. Observed for real: the first watchdog takeover
of `arc-1ed520f47e14` scored 1.0 because the local model restated the goal
verbatim. So continuity catches the red-team's attack ("productive on the wrong
work") but NOT its cousin ("says the right words, does nothing real"). The
defence against that one is the oracle — which is why an arc without an
`oracle_cmd` can never earn a strong `faithful`, and why `n_checks_ran` and the
per-check detail are always reported instead of a bare verdict.

Usage (verifier identity must differ from the taker):
  python3 scripts/aios_takeover_verify.py --arc ARC [--agent verifier@myworld]
      [--record] [--oracle-timeout 300] [--json]

`--record` appends the verdict to the arc via aios_society.record_verdict.
Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aios_society as soc  # noqa: E402

SCHEMA = "aios.society.takeover_verdict.v1"
DEFAULT_VERIFIER = "verifier@myworld"
CONTINUITY_FLOOR = 0.12          # token-overlap floor, fixed in advance
_CLAUSE_RE = re.compile(r"^\s*(forbid|require):\s*(.+?)\s*$", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]{3,}")

# Words that carry no discriminative signal for "is this the same work".
_STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "not",
         "you", "are", "was", "その", "것", "수", "때", "하고", "하는"}


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")
            if t.lower() not in _STOP}


def _overlap(a: str, b: str) -> float:
    """Jaccard-style containment of b's tokens in a (0..1)."""
    ta, tb = _tokens(a), _tokens(b)
    if not tb:
        return 0.0
    return len(ta & tb) / len(tb)


def takeover_window(events: list[dict], taker: str | None = None) -> dict:
    """The events belonging to the CURRENT takeover: everything at/after the
    last `claimed` whose agent differs from the previous owner. Returns the
    taker, the handoff it answered, and the taker's own events."""
    claims = [e for e in events if e["kind"] == "claimed"]
    if not claims:
        return {"ok": False, "reason": "arc was never claimed"}

    # A takeover is a claim by an agent OTHER than the arc's most recent
    # worker. The event's own `prev_owner` cannot decide this: it is None both
    # for the very first claim AND for a claim after a handoff (which clears
    # ownership) — so the prior worker is derived from history instead.
    transfer, handed_from = None, None
    prior_worker = None
    for e in events:
        if e["kind"] == "claimed":
            if prior_worker is not None and e.get("agent") != prior_worker:
                transfer, handed_from = e, prior_worker
            prior_worker = e.get("agent")
        elif e["kind"] == "progress":
            prior_worker = e.get("agent") or prior_worker
    if transfer is None:
        return {"ok": False, "reason": "no ownership transfer to verify"}
    if taker and transfer.get("agent") != taker:
        return {"ok": False, "reason": f"latest taker is {transfer.get('agent')}"}
    prior = [e for e in events if e["seq"] < transfer["seq"]]
    handoff = next((e for e in reversed(prior)
                    if e["kind"] == "handoff_offered"), None)
    after = [e for e in events if e["seq"] > transfer["seq"]
             and e.get("agent") == transfer.get("agent")]
    return {"ok": True, "taker": transfer.get("agent"),
            "transfer_seq": transfer["seq"],
            "prev_owner": handed_from,
            "lease_held_by_at_claim": transfer.get("prev_owner"),
            "handoff": handoff, "taker_events": after}


def check_continuity(state: dict, win: dict) -> dict:
    """Did the taker continue THIS arc? (the anti-'passes-checksum, solves the
    wrong problem' check)."""
    progress = [e for e in win["taker_events"] if e["kind"] == "progress"]
    if not progress:
        return {"name": "continuity", "ran": True, "passed": False,
                "detail": "taker produced no progress events after takeover"}
    body = " ".join(e.get("text", "") + " " + " ".join(e.get("evidence", []))
                    for e in progress)
    target = ((win["handoff"] or {}).get("next_step")
              or (win["handoff"] or {}).get("reason")
              or state.get("goal", ""))
    ov_target = _overlap(body, target)
    ov_goal = _overlap(body, state.get("goal", ""))
    best = max(ov_target, ov_goal)
    with_evidence = any(e.get("evidence") for e in progress)
    passed = best >= CONTINUITY_FLOOR and with_evidence
    return {"name": "continuity", "ran": True, "passed": passed,
            "overlap_with_next_step": round(ov_target, 3),
            "overlap_with_goal": round(ov_goal, 3),
            "floor": CONTINUITY_FLOOR, "any_evidence": with_evidence,
            "detail": ("taker's work does not reference the handed-off next "
                       "step or the arc goal"
                       if best < CONTINUITY_FLOOR else
                       "no evidence cited by the taker" if not with_evidence
                       else "continues the arc")}


def check_revisions(state: dict, win: dict) -> dict:
    """Revision must not become an escape hatch (D2 guard).

    `supersede` lets an arc retract a wrong step — which is also the perfect
    way to erase an inconvenient one. The log still holds it (nothing is
    deletable), so the check is: did the TAKER retract steps written by someone
    ELSE, without adding any progress of its own? That is not revision, it is
    quietly rewriting the predecessor's work out of the resume pack.
    """
    taker = win["taker"]
    mine = [s for s in state.get("supersessions", [])
            if s["seq"] > win["transfer_seq"] and s["agent"] == taker]
    if not mine:
        return {"name": "revision", "ran": False, "passed": None,
                "detail": "taker superseded nothing"}
    by_seq = {p["seq"]: p for p in state["progress"]}
    others = [s for s in mine
              if by_seq.get(s["target_seq"], {}).get("agent") not in (taker, None)]
    added = [e for e in win["taker_events"] if e["kind"] == "progress"]
    passed = not (others and not added)
    return {"name": "revision", "ran": True, "passed": passed,
            "n_supersessions": len(mine), "n_of_others_work": len(others),
            "detail": ("taker retracted a predecessor's work and contributed "
                       "no progress of its own"
                       if not passed else "revisions accompanied by own work")}


def check_constraints(state: dict, win: dict) -> list[dict]:
    """Machine-check `forbid:<regex>` / `require:<regex>` clauses against the
    taker's own events. Prose constraints are reported UNENFORCEABLE, never
    passed by default."""
    body = " ".join(e.get("text", "") + " " + " ".join(e.get("evidence", []))
                    for e in win["taker_events"])
    out = []
    for c in state.get("constraints", []):
        m = _CLAUSE_RE.match(c)
        if not m:
            out.append({"name": "constraint", "constraint": c, "ran": False,
                        "passed": None, "detail": "unenforceable (prose) — "
                                                  "needs a human or an oracle"})
            continue
        kind, pattern = m.group(1).lower(), m.group(2)
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            out.append({"name": "constraint", "constraint": c, "ran": False,
                        "passed": None, "detail": f"bad regex: {exc}"})
            continue
        hit = bool(rx.search(body))
        passed = (not hit) if kind == "forbid" else hit
        out.append({"name": "constraint", "constraint": c, "ran": True,
                    "passed": passed,
                    "detail": f"{kind} pattern {'matched' if hit else 'absent'}"})
    return out


def check_oracle(state: dict, *, cwd: Path, timeout: float) -> dict:
    """Run the arc's own declared external command. Strongest check; absent
    on arcs that declare none."""
    cmd = state.get("oracle_cmd")
    if not cmd:
        return {"name": "oracle", "ran": False, "passed": None,
                "detail": "arc declares no oracle_cmd"}
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True,
                           text=True, timeout=timeout)
        return {"name": "oracle", "ran": True, "passed": r.returncode == 0,
                "returncode": r.returncode,
                "detail": (r.stdout + r.stderr)[-400:]}
    except subprocess.TimeoutExpired:
        return {"name": "oracle", "ran": True, "passed": False,
                "detail": f"oracle timed out after {timeout}s"}
    except OSError as exc:
        return {"name": "oracle", "ran": False, "passed": None,
                "detail": f"oracle could not run: {exc}"}


def verify(arc_id: str, *, now: float, verifier: str = DEFAULT_VERIFIER,
           arcs_dir: Path | str = soc.ARCS_DIR, cwd: Path | str = soc.ROOT,
           oracle_timeout: float = 300.0, run_oracle: bool = True) -> dict:
    """Judge the latest takeover. Returns a verdict record; never mutates the
    arc (recording is the caller's explicit step)."""
    events = soc.read_events(arc_id, arcs_dir)
    if not events:
        return {"schema": SCHEMA, "ok": False, "reason": "no such arc"}
    state = soc.project(events, now=now)
    win = takeover_window(events)
    if not win["ok"]:
        return {"schema": SCHEMA, "ok": False, "reason": win["reason"]}
    if win["taker"] == verifier:
        return {"schema": SCHEMA, "ok": False,
                "reason": "verifier must not be the taker (self-judging is "
                          "not verification)"}

    checks = [check_continuity(state, win), check_revisions(state, win)]
    checks += check_constraints(state, win)
    if run_oracle:
        checks.append(check_oracle(state, cwd=Path(cwd), timeout=oracle_timeout))

    ran = [c for c in checks if c.get("ran")]
    failed = [c for c in ran if c.get("passed") is False]
    unenforceable = [c for c in checks if not c.get("ran")]
    verdict = ("drifted" if failed else
               "faithful" if ran else "unverifiable")
    findings = [f"{c['name']}: {c.get('detail','')}"[:300] for c in failed]
    if verdict == "unverifiable":
        findings = ["nothing was machine-checkable: "
                    + "; ".join(c.get("detail", "") for c in unenforceable)][:1]
    return {"schema": SCHEMA, "ok": True, "arc_id": arc_id,
            "verifier": verifier, "taker": win["taker"],
            "prev_owner": win["prev_owner"], "transfer_seq": win["transfer_seq"],
            "handed_next_step": (win["handoff"] or {}).get("next_step"),
            "verdict": verdict, "checks": checks, "findings": findings,
            "n_checks_ran": len(ran), "n_unenforceable": len(unenforceable)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Verify that an arc takeover was faithful (G2)")
    ap.add_argument("--arc", required=True)
    ap.add_argument("--agent", default=DEFAULT_VERIFIER,
                    help="verifier identity (must differ from the taker)")
    ap.add_argument("--arcs-dir", default=str(soc.ARCS_DIR))
    ap.add_argument("--cwd", default=str(soc.ROOT))
    ap.add_argument("--oracle-timeout", type=float, default=300.0)
    ap.add_argument("--no-oracle", action="store_true",
                    help="skip the external oracle (diagnostics only)")
    ap.add_argument("--record", action="store_true",
                    help="append the verdict to the arc (INV-6: after the fact)")
    a = ap.parse_args(argv)

    now = time.time()
    out = verify(a.arc, now=now, verifier=a.agent, arcs_dir=Path(a.arcs_dir),
                 cwd=Path(a.cwd), oracle_timeout=a.oracle_timeout,
                 run_oracle=not a.no_oracle)
    if a.record and out.get("ok"):
        rec = soc.record_verdict(a.arc, agent=a.agent, verdict=out["verdict"],
                                 now=now, findings=out["findings"],
                                 arcs_dir=Path(a.arcs_dir))
        out["recorded"] = rec
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get("ok") and out.get("verdict") != "drifted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
