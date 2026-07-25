#!/usr/bin/env python3
"""AIOS Drive — pain-triggered proaction (organism assembly Phase 7,
docs/AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22.md; design source
docs/2026_07_evolution_sprint/AGI_MISSING_LINK_AND_HOMEOSTASIS_DESIGN.md +
§6.1 Ambient Pulse of AIOS_ORGANIC_EVOLUTION_MASTER.md).

The organism so far is entirely invocation-gated REACTION: body (enforced
sandbox/egress), self-verification (escalate + Weaver), continuous self
(experience graph), growth (verified skills) — all of it waits to be called.
This module gives it an internal motive force: a computable PAIN scalar
(homeostasis) over signals that ALREADY EXIST on disk, and a short-lived
PULSE that wakes, measures, proposes concrete remedies, appends one record,
and EXITS.

NO DAEMON (a council refuted the alternative, 2026-07-25): no resident
process, no listening socket, no in-memory authoritative state. The pulse is
cron/systemd-timer/inotify waking `python3 scripts/aios_drive.py pulse`,
which reads disk, acts (opt-in), appends, and exits. Disk is the source of
truth. See scripts/aios_pulse.cron.example.

PAIN (v1) — computed ONLY from existing signals; NO new math, NO sheaf/H^1
(that lane is parked pending a separate re-earn gate):

  contradictions   docs/ontology/ledger/_merged.json stats.contradicts_count,
                   saturating-normalized x/(x+K)
  failures         unresolved failure runs in the experience graph
                   (aios_experience q_failures semantics), x/(x+K)
  skill_coverage   shortfall of the verified-skill registry vs a target count
                   (aios_skills registry). NOTE: aios_skills v1 does NOT
                   persist gate rejections (the register() decision is
                   returned, not logged), so coverage shortfall is the only
                   durable skills signal — stated, not papered over.
  staleness        hours since the last experience pin
                   (.aios/experience/manifest.jsonl), linear up to a horizon

  pain = Σ weight_i * normalized_i   over AVAILABLE components (0..1)

Missing files / empty inputs degrade honestly: an unavailable component
contributes 0 with `available: false` — "no signal" is absence of evidence,
not health, and it is labeled as such. Empty everything -> pain 0.0, never a
crash. Pure logic never reads the clock: `now` is caller-supplied.

ANTI-THEATER GATE (the load-bearing part): every pulse records
`effect_verified` — did the organism's state VERIFIABLY improve
(contradiction resolved / failure cleared / skill registered / pin advanced)
since the previous pulse (and, for --act pulses, across the act itself)?
`report` prints the fraction of effect-checked pulses that verified.
**KILL CRITERION: if that fraction stays ~0 over a real sample of pulses,
this organ is theater — proposals nobody enacts — and must be killed.**
The number is printed first in `report` so it cannot hide.

DNA: recommendation-first (dry_run=True default — a pulse PROPOSES, it does
not execute), operator override (acting is opt-in via --act), append-only
(the pulse record is one appended JSONL line in the experience runs dir, so
it lands under the same Merkle root / pin evidence as all other experience).
When a pulse DOES act, it routes through EXISTING gates only: the sole
auto-executable remedy in v1 is `re_pin_experience` via
aios_experience.ExperienceIndex.pin (append-only, no code execution). Any
remedy involving code execution or skill registration must go through
aios_sandbox / aios_skills.register — never a new privileged path; those
remedies stay proposals for the head/operator.

HONEST LIMITATIONS:
  - Weights, saturation constants, target, horizon, and threshold are
    UNCALIBRATED v1 heuristics (see constants below) — chosen by feel, not
    fit to any outcome data. Calibration needs recorded pulses + outcomes.
  - dry_run default means the organ produces recommendations; whether it
    produces BEHAVIOR is exactly what the verified-effect fraction measures.
  - Only `re_pin_experience` is auto-executable; the highest-value remedies
    (resolve contradiction, re-attempt goal, induce skill) need the
    head/operator, so early verified-effect fractions measure the whole
    loop (organ + operator), not the organ alone.

CLI (the impure edge — supplies the real clock):
  python3 scripts/aios_drive.py pain
  python3 scripts/aios_drive.py pulse [--act]
  python3 scripts/aios_drive.py report

Schema: aios.drive.v1. Stdlib-only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_experience as _experience  # noqa: E402 — Phase-3 continuous self

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "docs" / "ontology" / "ledger" / "_merged.json"
RUNS = _experience.RUNS                                  # .aios/runs
EXP_MANIFEST = _experience.MANIFEST                      # .aios/experience/manifest.jsonl
SKILLS_REGISTRY = ROOT / ".aios" / "skills" / "registry.jsonl"
PULSE_LOG = RUNS / "drive-pulses.jsonl"                  # part of the experience graph

SCHEMA = "aios.drive.v1"

# --- UNCALIBRATED v1 HEURISTICS ---------------------------------------------
# These weights/constants are hand-picked priors, NOT fit to outcome data.
# They encode only ordinal intuitions (contradictions and failures hurt more
# than staleness; ~50 contradictions is "half-saturated" pain; a week without
# a pin is fully stale). Calibrate against recorded pulses before trusting
# absolute pain values; only the RELATIVE movement (rises with contradictions/
# failures, falls when they clear) is tested behavior.
W_CONTRADICTIONS = 0.35   # weight: ontology contradiction load
W_FAILURES = 0.30         # weight: unresolved failure runs
W_STALENESS = 0.20        # weight: time since last experience pin
W_SKILL_COVERAGE = 0.15   # weight: verified-skill shortfall vs target
K_CONTRADICTIONS = 50.0   # half-saturation count: x/(x+K)
K_FAILURES = 5.0          # half-saturation count: x/(x+K)
STALENESS_HORIZON_HOURS = 168.0   # 7 days unpinned == fully stale
SKILL_COVERAGE_TARGET = 10        # registry size at which coverage pain -> 0
PAIN_THRESHOLD = 0.25     # pulse fires (emits proposals) at/above this

_COMPONENT_ORDER = ("contradictions", "failures", "staleness", "skill_coverage")
_MAX_DETAIL = 5           # how many concrete edges/runs to carry as targets

# The one remedy a pulse may execute itself (append-only, existing organ,
# no code execution). Everything else is recommendation-only in v1.
_AUTO_EXECUTABLE = frozenset({"re_pin_experience"})


# ---------------------------------------------------------------------------
# signal readers (impure edge: disk reads; honest degrade, never crash)
# ---------------------------------------------------------------------------

def read_ontology(path: str | Path = ONTOLOGY) -> dict:
    """Contradiction load from the merged ontology ledger. Missing / corrupt
    file -> available False ("no signal"), never a crash."""
    p = Path(path)
    out = {"available": False, "contradicts_count": None, "total_entities": None,
           "edges": [], "note": ""}
    if not p.is_file():
        out["note"] = f"no signal: ontology ledger missing ({p})"
        return out
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        out["note"] = f"no signal: ontology ledger unreadable ({exc})"
        return out
    if not isinstance(data, dict):
        out["note"] = "no signal: ontology ledger is not an object"
        return out
    stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    relations = data.get("relations") if isinstance(data.get("relations"), list) else []
    edges = [(str(r.get("src_id")), str(r.get("dst_id")))
             for r in relations
             if isinstance(r, dict) and str(r.get("rel")) == "contradicts"]
    count = stats.get("contradicts_count")
    if not isinstance(count, int):
        count = len(edges)   # fall back to counting the edges themselves
    out.update(available=True, contradicts_count=count,
               total_entities=stats.get("total_entities"),
               edges=edges[:_MAX_DETAIL])
    return out


def read_experience(runs_dir: str | Path = RUNS) -> dict:
    """Unresolved failures from the continuous self (aios_experience).
    No runs at all -> available False ("no experience yet")."""
    ix = _experience.ExperienceIndex(runs_dir)
    failed = [r for r in ix.runs if r["status"] == "failure"]
    return {
        "available": bool(ix.runs),
        "runs": len(ix.runs),
        "unresolved_failures": len(failed),
        "unknown_exit_runs": sum(1 for r in ix.runs if r["status"] == "unknown_exit"),
        "tool_errors": sum(len(r["tool_errors"]) for r in ix.runs),
        "failed": [{"run_id": r["run_id"], "goal_hint": r["goal_hint"],
                    "exit": r["exit"]} for r in failed[:_MAX_DETAIL]],
        "note": "" if ix.runs else f"no signal: no experience yet ({runs_dir})",
    }


def _iso_to_epoch(ts: str) -> float | None:
    """ISO-8601 -> epoch seconds; tz-naive treated as UTC; unparseable -> None."""
    try:
        dt = _dt.datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.timestamp()


def read_pin(manifest: str | Path = EXP_MANIFEST) -> dict:
    """Last experience pin (aios_experience pin manifest). No pin -> no signal."""
    p = Path(manifest)
    out = {"available": False, "last_pin_ts": None, "last_pin_iso": None, "note": ""}
    if not p.is_file():
        out["note"] = f"no signal: no experience pin manifest ({p})"
        return out
    last = None
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and rec.get("ts"):
                    last = rec
    except OSError as exc:
        out["note"] = f"no signal: pin manifest unreadable ({exc})"
        return out
    if last is None:
        out["note"] = "no signal: pin manifest has no pins yet"
        return out
    epoch = _iso_to_epoch(last["ts"])
    if epoch is None:
        out["note"] = f"no signal: unparseable pin ts {last['ts']!r}"
        return out
    out.update(available=True, last_pin_ts=epoch, last_pin_iso=str(last["ts"]))
    return out


def read_skills(registry: str | Path = SKILLS_REGISTRY) -> dict:
    """Verified-skill count from the aios_skills registry. Missing registry ->
    no signal. NOTE (honest): aios_skills v1 returns gate rejections to the
    caller but does NOT persist them, so rejection counts cannot be read from
    disk — coverage shortfall is the only durable skills signal."""
    p = Path(registry)
    out = {"available": False, "n_skills": None,
           "note": "", "rejections_note": ("gate rejections are not persisted "
                                           "by aios_skills v1 — unavailable")}
    if not p.is_file():
        out["note"] = f"no signal: skill registry missing ({p})"
        return out
    n = 0
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    if isinstance(json.loads(line), dict):
                        n += 1
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        out["note"] = f"no signal: skill registry unreadable ({exc})"
        return out
    out.update(available=True, n_skills=n)
    return out


def gather_signals(*, ontology: str | Path = ONTOLOGY,
                   runs_dir: str | Path = RUNS,
                   exp_manifest: str | Path = EXP_MANIFEST,
                   skills_registry: str | Path = SKILLS_REGISTRY) -> dict:
    return {"ontology": read_ontology(ontology),
            "experience": read_experience(runs_dir),
            "pin": read_pin(exp_manifest),
            "skills": read_skills(skills_registry)}


# ---------------------------------------------------------------------------
# homeostasis — the PAIN scalar (pure over signals + now)
# ---------------------------------------------------------------------------

def _saturate(x: float, k: float) -> float:
    """x/(x+k): 0 at 0, monotonically rising, asymptote 1."""
    x = max(0.0, float(x))
    return x / (x + k) if x > 0 else 0.0


def compute_pain(signals: dict, now: float) -> dict:
    """Pure pain computation. `now` is caller-supplied epoch seconds — this
    function never reads the clock. Unavailable components contribute 0 and
    say so; all-unavailable -> pain 0.0 with an honest no-signal note."""
    ont, exp = signals["ontology"], signals["experience"]
    pin, sk = signals["pin"], signals["skills"]

    components: dict[str, dict] = {}

    raw_c = ont["contradicts_count"] if ont["available"] else None
    components["contradictions"] = {
        "available": ont["available"], "raw": raw_c,
        "normalized": round(_saturate(raw_c, K_CONTRADICTIONS), 4)
        if ont["available"] else 0.0,
        "weight": W_CONTRADICTIONS,
        "detail": {"edges": ont["edges"], "total_entities": ont["total_entities"],
                   "note": ont["note"]},
    }

    raw_f = exp["unresolved_failures"] if exp["available"] else None
    components["failures"] = {
        "available": exp["available"], "raw": raw_f,
        "normalized": round(_saturate(raw_f, K_FAILURES), 4)
        if exp["available"] else 0.0,
        "weight": W_FAILURES,
        "detail": {"failed": exp["failed"], "runs": exp["runs"],
                   "unknown_exit_runs": exp["unknown_exit_runs"],
                   "tool_errors": exp["tool_errors"], "note": exp["note"]},
    }

    hours = None
    if pin["available"]:
        hours = max(0.0, (float(now) - pin["last_pin_ts"]) / 3600.0)
    components["staleness"] = {
        "available": pin["available"], "raw": round(hours, 2) if hours is not None else None,
        "normalized": round(min(1.0, hours / STALENESS_HORIZON_HOURS), 4)
        if hours is not None else 0.0,
        "weight": W_STALENESS,
        "detail": {"last_pin_iso": pin["last_pin_iso"],
                   "horizon_hours": STALENESS_HORIZON_HOURS, "note": pin["note"]},
    }

    raw_s = sk["n_skills"] if sk["available"] else None
    components["skill_coverage"] = {
        "available": sk["available"], "raw": raw_s,
        "normalized": round(max(0.0, 1.0 - raw_s / SKILL_COVERAGE_TARGET), 4)
        if sk["available"] else 0.0,
        "weight": W_SKILL_COVERAGE,
        "detail": {"target": SKILL_COVERAGE_TARGET,
                   "rejections": sk["rejections_note"], "note": sk["note"]},
    }

    for c in components.values():
        c["weighted"] = round(c["weight"] * c["normalized"], 4) if c["available"] else 0.0

    pain = round(sum(c["weighted"] for c in components.values()), 4)
    available = [n for n in _COMPONENT_ORDER if components[n]["available"]]
    painful = [n for n in available if components[n]["weighted"] > 0]
    dominant = max(painful, key=lambda n: components[n]["weighted"]) if painful else None
    note = ("no signal: every component unavailable — pain 0.0 is absence of "
            "evidence, not health" if not available else "")
    return {"schema": SCHEMA, "kind": "homeostasis", "ts": float(now),
            "pain": pain, "components": components,
            "threshold": PAIN_THRESHOLD,
            "over_threshold": pain >= PAIN_THRESHOLD,
            "dominant": dominant, "note": note}


def homeostasis(now: float, *, signals: dict | None = None,
                ontology: str | Path = ONTOLOGY,
                runs_dir: str | Path = RUNS,
                exp_manifest: str | Path = EXP_MANIFEST,
                skills_registry: str | Path = SKILLS_REGISTRY) -> dict:
    """PAIN scalar + breakdown. Pass `signals` for a pure call; otherwise the
    existing on-disk signals are gathered (honest degrade on anything missing)."""
    if signals is None:
        signals = gather_signals(ontology=ontology, runs_dir=runs_dir,
                                 exp_manifest=exp_manifest,
                                 skills_registry=skills_registry)
    return compute_pain(signals, now)


# ---------------------------------------------------------------------------
# propose_actions — concrete, verifiable remedies for the dominant pain
# ---------------------------------------------------------------------------

def _proposals_for(name: str, comp: dict, state: dict) -> list[dict]:
    d = comp["detail"]
    props: list[dict] = []
    if name == "contradictions":
        for src, dst in d["edges"][:3]:
            props.append({
                "component": name, "action": "resolve_contradiction",
                "target": f"{src} <-> {dst}",
                "rationale": ("the ontology ledger asserts a `contradicts` edge "
                              "between these nodes; both cannot stand unqualified"),
                "expected_effect": (f"stats.contradicts_count decreases below "
                                    f"{comp['raw']} after the edge is resolved "
                                    "(scoped/retracted/merged) and re-merged"),
            })
        if not props and comp["raw"]:
            props.append({
                "component": name, "action": "resolve_contradiction",
                "target": "top contradicts edges in docs/ontology/ledger/_merged.json",
                "rationale": "contradiction count is nonzero but edge detail was unavailable",
                "expected_effect": f"stats.contradicts_count decreases below {comp['raw']}",
            })
    elif name == "failures":
        seen_goals: dict[str, int] = {}
        for f in d["failed"]:
            g = f["goal_hint"] or f["run_id"]
            seen_goals[g] = seen_goals.get(g, 0) + 1
        for g, n in seen_goals.items():
            if n >= 2:
                props.append({
                    "component": name, "action": "induce_skill_for_task_class",
                    "target": g,
                    "rationale": f"this goal/class failed {n} times — a scar "
                                 "repeating is a missing gene",
                    "expected_effect": ("a skill for this class passes the "
                                        "aios_skills sandbox gate (registry "
                                        "n_skills increases) and the next run "
                                        "of this class exits success"),
                })
        for f in d["failed"][:3]:
            props.append({
                "component": name, "action": "re_attempt_failed_goal",
                "target": f["goal_hint"] or f["run_id"],
                "rationale": f"run {f['run_id']} recorded failure exit "
                             f"{f['exit']!r} and no later success",
                "expected_effect": ("a new run of this goal records "
                                    "exit=model_finished; q_failures "
                                    "failed-run count decreases"),
            })
    elif name == "staleness":
        props.append({
            "component": name, "action": "re_pin_experience",
            "target": "aios_experience pin (append to the pin manifest)",
            "rationale": f"last pin was {comp['raw']}h ago "
                         f"(horizon {STALENESS_HORIZON_HOURS}h) — unpinned "
                         "growth is unverifiable growth",
            "expected_effect": ("the pin manifest gains an entry; hours-since-"
                                "pin resets to ~0 and `verify` covers all "
                                "current experience"),
        })
    elif name == "skill_coverage":
        props.append({
            "component": name, "action": "induce_skill",
            "target": ("aios_skills.induce_and_register on the most recent "
                       "successfully solved goal's solution code"),
            "rationale": f"registry holds {comp['raw']} verified skill(s) vs "
                         f"target {SKILL_COVERAGE_TARGET} — the compounding "
                         "unit is not compounding",
            "expected_effect": "registry n_skills increases (sandbox gate passed)",
        })
    return props


def propose_actions(state: dict) -> list[dict]:
    """Ranked concrete remedies: dominant pain component first, then the rest
    by weighted contribution. Each proposal names a MEASURABLE expected_effect.
    Empty when nothing hurts (no proposals is the honest output for pain 0)."""
    comps = state["components"]
    ranked = sorted(
        (n for n in _COMPONENT_ORDER if comps[n]["available"] and comps[n]["weighted"] > 0),
        key=lambda n: comps[n]["weighted"], reverse=True)
    out: list[dict] = []
    for name in ranked:
        out.extend(_proposals_for(name, comps[name], state))
    return out


# ---------------------------------------------------------------------------
# pulse_effect — the anti-theater gate (pure over two state snapshots)
# ---------------------------------------------------------------------------

def state_snapshot(state: dict) -> dict:
    """Compact comparable snapshot of a homeostasis state (raw signals only —
    effect verification compares FACTS, not the pain heuristic)."""
    c = state["components"]
    def raw(name):  # noqa: E306
        return c[name]["raw"] if c[name]["available"] else None
    return {"pain": state["pain"],
            "contradicts_count": raw("contradictions"),
            "unresolved_failures": raw("failures"),
            "n_skills": raw("skill_coverage"),
            "last_pin_ts": (_iso_to_epoch(c["staleness"]["detail"]["last_pin_iso"])
                            if c["staleness"]["available"] else None)}


def pulse_effect(before: dict, after: dict) -> dict:
    """Did anything VERIFIABLY improve between two snapshots? True only for
    concrete behavioral change (contradiction resolved / failure cleared /
    skill registered / pin advanced) — a pain-number wiggle alone is not an
    effect. Axes where either side has no signal cannot verify."""
    changes: list[str] = []
    def _both(key):  # noqa: E306
        return before.get(key) is not None and after.get(key) is not None
    if _both("contradicts_count") and after["contradicts_count"] < before["contradicts_count"]:
        changes.append("contradiction_resolved")
    if _both("unresolved_failures") and after["unresolved_failures"] < before["unresolved_failures"]:
        changes.append("failure_cleared")
    if _both("n_skills") and after["n_skills"] > before["n_skills"]:
        changes.append("skill_registered")
    if _both("last_pin_ts") and after["last_pin_ts"] > before["last_pin_ts"]:
        changes.append("pin_advanced")
    if before.get("last_pin_ts") is None and after.get("last_pin_ts") is not None:
        changes.append("pin_advanced")   # first-ever pin is an advance
    pain_delta = None
    if before.get("pain") is not None and after.get("pain") is not None:
        pain_delta = round(after["pain"] - before["pain"], 4)
    return {"effect_verified": bool(changes), "changes": changes,
            "pain_delta": pain_delta}


# ---------------------------------------------------------------------------
# pulse — the wake-up cycle (measure -> propose -> [opt-in act] -> append -> exit)
# ---------------------------------------------------------------------------

def _read_pulses(pulse_log: str | Path) -> list[dict]:
    p = Path(pulse_log)
    out: list[dict] = []
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get("kind") == "drive_pulse":
                out.append(rec)
    return out


def _act(proposals: list[dict], *, runs_dir, exp_manifest) -> list[dict]:
    """Execute ONLY the auto-executable remedies, through EXISTING organs.
    v1: re_pin_experience via aios_experience.ExperienceIndex.pin (append-only,
    no code execution). Everything else is recorded as requiring the
    head/operator — recommendation-first, never a new privileged path."""
    executed: list[dict] = []
    for p in proposals:
        if p["action"] not in _AUTO_EXECUTABLE:
            executed.append({"action": p["action"], "status": "skipped_requires_head",
                             "detail": "recommendation only in v1 — code execution "
                                       "and skill registration must go through the "
                                       "existing sandbox/skills gates via the "
                                       "head/operator"})
            continue
        try:
            entry = _experience.ExperienceIndex(runs_dir).pin(exp_manifest)
            executed.append({"action": p["action"], "status": "executed",
                             "detail": {"pinned_root": entry["merkle_root"],
                                        "n_entries": entry["n_entries"]}})
        except OSError as exc:
            executed.append({"action": p["action"], "status": "failed",
                             "detail": str(exc)})
    return executed


def pulse(now: float, *, dry_run: bool = True,
          ontology: str | Path = ONTOLOGY,
          runs_dir: str | Path = RUNS,
          exp_manifest: str | Path = EXP_MANIFEST,
          skills_registry: str | Path = SKILLS_REGISTRY,
          pulse_log: str | Path = PULSE_LOG) -> dict:
    """One wake-up: measure pain -> if over threshold emit ranked proposals ->
    ASK (Phase 8: aios_resonance questions section, guarded — resonance
    failure degrades to available:False, never breaks the pulse) ->
    (opt-in, dry_run=False) execute auto-executable remedies through existing
    gates -> append EXACTLY ONE kind:"drive_pulse" record to the experience
    runs dir -> return the record. Default dry_run=True: it PROPOSES ONLY."""
    paths = dict(ontology=ontology, runs_dir=runs_dir,
                 exp_manifest=exp_manifest, skills_registry=skills_registry)
    state = homeostasis(now, **paths)
    snapshot = state_snapshot(state)
    proposals = propose_actions(state) if state["over_threshold"] else []
    prev = _read_pulses(pulse_log)

    # Phase 8 — RESONANCE: one heartbeat, two faculties. The pulse FEELS
    # (pain, above) and ASKS (questions born from the same organ signals).
    # Guarded: a broken or missing resonance organ degrades honestly and can
    # never take the heartbeat down (import lives inside the guard).
    try:
        import aios_resonance as _resonance
        questions = _resonance.pulse_questions(
            state, prev, now=now, ontology=ontology, runs_dir=runs_dir,
            skills_registry=skills_registry)
    except Exception as exc:  # noqa: BLE001 — degrade, never break the pulse
        questions = {"available": False,
                     "note": f"resonance unavailable: {exc}"}

    executed: list[dict] = []
    acted_effect = None
    if not dry_run and proposals:
        executed = _act(proposals, runs_dir=runs_dir, exp_manifest=exp_manifest)
        if any(e["status"] == "executed" for e in executed):
            after = state_snapshot(homeostasis(now, **paths))
            acted_effect = pulse_effect(snapshot, after)
            snapshot = after   # the record carries the post-act facts

    effect_since_last = (pulse_effect(prev[-1].get("state") or {}, snapshot)
                         if prev else None)

    # effect_verified: acted pulses answer for their own act; otherwise the
    # question is "did the PREVIOUS pulse's proposals get enacted since?".
    if acted_effect is not None:
        effect_verified = acted_effect["effect_verified"]
    elif effect_since_last is not None:
        effect_verified = effect_since_last["effect_verified"]
    else:
        effect_verified = None   # first pulse ever: nothing to compare against

    record = {
        "schema": SCHEMA, "kind": "drive_pulse", "ts": float(now),
        "ts_iso": _dt.datetime.fromtimestamp(
            float(now), tz=_dt.timezone.utc).isoformat(timespec="seconds"),
        "pain": state["pain"], "threshold": state["threshold"],
        "over_threshold": state["over_threshold"], "dominant": state["dominant"],
        "components": {n: {"available": c["available"], "raw": c["raw"],
                           "normalized": c["normalized"], "weighted": c["weighted"]}
                       for n, c in state["components"].items()},
        "proposals": proposals, "questions": questions,
        "dry_run": bool(dry_run), "executed": executed,
        "state": snapshot, "effect_since_last": effect_since_last,
        "acted_effect": acted_effect, "effect_verified": effect_verified,
        "note": state["note"],
    }
    lp = Path(pulse_log)
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


# ---------------------------------------------------------------------------
# report — the kill-criterion readout
# ---------------------------------------------------------------------------

def report(pulse_log: str | Path = PULSE_LOG) -> dict:
    """Over all recorded pulses: how many fired, and WHAT FRACTION produced a
    verified behavioral effect. That fraction is the organ's kill criterion:
    ~0 over a real sample = theater = kill the organ (see module docstring)."""
    pulses = _read_pulses(pulse_log)
    fired = [p for p in pulses if p.get("over_threshold")]
    acted = [p for p in pulses
             if any(e.get("status") == "executed" for e in p.get("executed") or [])]
    checked = [p for p in pulses if p.get("effect_verified") is not None]
    verified = [p for p in checked if p.get("effect_verified") is True]
    frac = round(len(verified) / len(checked), 4) if checked else None
    if not pulses:
        verdict = "no pulses recorded yet — the organ has never woken"
    elif not checked:
        verdict = ("no effect-checkable pulses yet (first pulse has no "
                   "predecessor) — fraction undefined, keep pulsing")
    elif frac == 0 and len(checked) >= 3:
        verdict = ("THEATER by the organ's own criterion: pulses fire but "
                   "nothing ever verifiably improves — kill this organ or "
                   "wire its proposals to an actor")
    else:
        verdict = (f"{len(verified)}/{len(checked)} effect-checked pulses "
                   "produced a verified behavioral change")
    return {"schema": SCHEMA, "kind": "report",
            "verified_effect_fraction": frac,       # THE number — read this first
            "verdict": verdict,
            "pulses": len(pulses), "fired_over_threshold": len(fired),
            "acted": len(acted), "effect_checked": len(checked),
            "effect_verified": len(verified),
            "last_pulse_iso": pulses[-1].get("ts_iso") if pulses else None,
            "last_pain": pulses[-1].get("pain") if pulses else None}


# ---------------------------------------------------------------------------
# CLI — the impure edge: supplies the real clock
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import time
    ap = argparse.ArgumentParser(
        description="AIOS drive — pain-triggered proaction "
                    "(pain / pulse [--act] / report). No daemon: wake, act, exit.")
    ap.add_argument("--ontology", default=str(ONTOLOGY))
    ap.add_argument("--runs-dir", default=str(RUNS))
    ap.add_argument("--exp-manifest", default=str(EXP_MANIFEST))
    ap.add_argument("--skills-registry", default=str(SKILLS_REGISTRY))
    ap.add_argument("--pulse-log", default=str(PULSE_LOG))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pain", help="measure the pain scalar + breakdown")
    pl = sub.add_parser("pulse", help="one wake-up cycle (dry-run by default)")
    pl.add_argument("--act", action="store_true",
                    help="opt-in: execute auto-executable remedies "
                         "(v1: re_pin_experience only) through existing gates")
    sub.add_parser("report", help="verified-effect fraction over all pulses "
                                  "(the kill criterion)")
    args = ap.parse_args(argv)

    paths = dict(ontology=args.ontology, runs_dir=args.runs_dir,
                 exp_manifest=args.exp_manifest,
                 skills_registry=args.skills_registry)
    if args.cmd == "pain":
        out = homeostasis(time.time(), **paths)
    elif args.cmd == "pulse":
        out = pulse(time.time(), dry_run=not args.act,
                    pulse_log=args.pulse_log, **paths)
    else:
        out = report(args.pulse_log)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
