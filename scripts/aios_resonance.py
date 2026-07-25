#!/usr/bin/env python3
"""AIOS Resonance — the organism's self-questioning loop (organism assembly
Phase 8, docs/AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22.md).

DRIVE (Phase 7) made the organism FEEL: a pain scalar over signals already on
disk. Resonance makes the SAME heartbeat ASK: every question is BORN from an
existing organ's output and ROUTED BACK to an existing organ — circulation
between organs that already exist, not a sixth orphan module.

  inflow    ontology `contradicts` edges (a contradiction IS a standing
            question) · DRIVE's dominant pain component · experience-graph
            failures · repeated failures with no covering skill
  identity  every question gets a STABLE content-addressed qid (sha256 over
            kind + normalized refs), so the SAME question recurring across
            pulses is recognizable — recognition across pulses is what makes
            resonance possible at all
  resonance amplitude = recurrence (past pulses that asked this qid)
            + multi-organ constructive interference (distinct organs raising
            questions over shared refs) + dominant-pain bonus
            − damping for settled questions
  outflow   route() names the EXISTING organ that should answer (memory
            retrieve / escalate+verifier / skills / genesis challenge /
            operator) with a concrete suggested invocation. v1 ROUTES AND
            RECORDS; it does not auto-execute — the same recommendation-first
            DNA as DRIVE.

**Resonance without damping is rumination.** The load-bearing guard:
a question asked >= RUMINATION_N times with ZERO behavioral change recorded
in between (no contradiction resolved / failure cleared / skill registered —
the aios_drive.pulse_effect axes, with pin bookkeeping excluded because
re-pinning answers no question) is forcibly RETIRED with
{status: "retired_rumination", reason, asked_n} and excluded from future
harvests unless its refs change (a changed ref is a new qid, a new question).
`resonance_report` computes question_resolution_rate + rumination_count; if
the resolution rate stays ~0 over a real sample, this organ is rumination,
not thought — the verdict says so in those words (same discipline as DRIVE's
theater verdict).

NO DAEMON: questions are asked and recorded inside `aios_drive.pulse()` —
the cron-woken heartbeat. One heartbeat, two faculties: FEEL and ASK. The
question section lives inside the same append-only pulse log (the experience
runs dir), so every question's fate is readable from the same Merkle-pinned
evidence as the rest of the organism's experience. The CLI here is strictly
read-only; only the heartbeat appends.

HONEST LIMITATIONS:
  - NO LLM in v1: questions are deterministic templates over organ output.
    What this buys is *bookkeeping of standing questions* (identity,
    amplification, damping, fate-tracking) — not open-ended reflection. An
    LLM asker must earn its place downstream of this scaffold.
  - Amplitude constants are UNCALIBRATED v1 heuristics (ordinal intuitions,
    not fit to outcome data); only RELATIVE movement is tested behavior.
  - route() recommends, nothing executes. Whether questions ever change
    behavior is exactly what question_resolution_rate measures.

CLI (read-only — the append path is aios_drive.pulse):
  python3 scripts/aios_resonance.py ask       # harvest+resonate+route over the real current state
  python3 scripts/aios_resonance.py standing  # standing questions from the latest pulse
  python3 scripts/aios_resonance.py report    # resolution rate + rumination count + verdict

Schema: aios.resonance.v1. Stdlib-only. Pure core: `now` is caller-supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_experience as _experience  # noqa: E402 — Phase-3 continuous self
import aios_skills as _skills          # noqa: E402 — Phase-4 compounding unit

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "docs" / "ontology" / "ledger" / "_merged.json"
RUNS = _experience.RUNS                                  # .aios/runs
SKILLS_REGISTRY = _skills.REGISTRY                       # .aios/skills/registry.jsonl
PULSE_LOG = RUNS / "drive-pulses.jsonl"                  # == aios_drive.PULSE_LOG
                                                         # (replicated, not imported:
                                                         # drive imports THIS module)
SCHEMA = "aios.resonance.v1"

# --- UNCALIBRATED v1 HEURISTICS ---------------------------------------------
# Hand-picked ordinal priors, NOT fit to outcome data: recurrence and a second
# organ raising the same refs matter about equally; sitting on the dominant
# pain is a tie-breaker; having once settled damps a re-emerging question by
# about one recurrence. Calibrate against recorded pulses before trusting
# absolute amplitudes; only the RELATIVE movement is tested behavior.
AMP_RECURRENCE = 1.0       # per past pulse that asked this qid
RECURRENCE_CAP = 5.0       # recurrence contribution saturates here
AMP_MULTI_ORGAN = 1.0      # per distinct EXTRA organ raising overlapping refs
AMP_DOMINANT_BONUS = 0.5   # question sits on DRIVE's dominant pain component
AMP_SETTLED_DAMPING = 1.0  # question once settled (went away) and is back
RUMINATION_N = 3           # asked this many times with zero change -> retired
GAP_MIN_FAILURES = 2       # repeated-failure threshold for skill-gap questions
TOP_K = 5                  # questions carried in full detail per pulse record
_LABEL_MAX = 100           # readable-question label truncation

# kind -> the DRIVE pain component whose availability makes the question's
# fate observable (None = always observable). Used by resonance_report so an
# organ going dark is never mistaken for a question getting resolved.
_KIND_COMPONENT = {"contradiction": "contradictions", "failure": "failures",
                   "gap": "skill_coverage", "pain": None}


# ---------------------------------------------------------------------------
# identity — stable content-addressed question ids
# ---------------------------------------------------------------------------

def qid_for(kind: str, refs: list[str]) -> str:
    """Content-addressed question id: sha256 over kind + normalized refs
    (sorted, stripped — direction/order never changes identity). The same
    standing question therefore has the same qid in every pulse; a changed
    ref is a different question."""
    norm = "|".join(sorted(str(r).strip() for r in refs))
    return "q:" + hashlib.sha256(f"{kind}|{norm}".encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# signal readers (impure edge; honest degrade, never crash)
# ---------------------------------------------------------------------------

def read_contradictions(path: str | Path = ONTOLOGY) -> dict:
    """ALL `contradicts` edges from the merged ontology ledger, with entity
    names for readable question text. (aios_drive.read_ontology truncates
    edge detail for the pain record; a question harvest needs every standing
    contradiction, so this reader is separate by design.)"""
    p = Path(path)
    out = {"available": False, "count": 0, "edges": [], "note": ""}
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
    entities = data.get("entities") if isinstance(data.get("entities"), list) else []
    names = {str(e.get("id")): str(e.get("name") or "")
             for e in entities if isinstance(e, dict)}
    relations = data.get("relations") if isinstance(data.get("relations"), list) else []
    edges = []
    for r in relations:
        if not (isinstance(r, dict) and str(r.get("rel")) == "contradicts"):
            continue
        src, dst = str(r.get("src_id")), str(r.get("dst_id"))
        edges.append({"src": src, "dst": dst,
                      "src_label": _label(src, names), "dst_label": _label(dst, names)})
    out.update(available=True, count=len(edges), edges=edges)
    return out


def _label(node_id: str, names: dict[str, str]) -> str:
    text = names.get(node_id) or node_id
    return text if len(text) <= _LABEL_MAX else text[:_LABEL_MAX - 1] + "…"


def read_failures(runs_dir: str | Path = RUNS) -> dict:
    """Distinct failing goals from the experience graph (aios_experience
    q_failures semantics), grouped so one repeated goal is ONE standing
    question. No runs at all -> honest no-signal."""
    ix = _experience.ExperienceIndex(runs_dir)
    goals: dict[str, dict] = {}
    for r in ix.runs:
        if r["status"] != "failure":
            continue
        g = r["goal_hint"] or r["run_id"]
        d = goals.setdefault(g, {"goal": g, "n": 0, "exits": [], "run_ids": []})
        d["n"] += 1
        if r["exit"] not in d["exits"]:
            d["exits"].append(r["exit"])
        if len(d["run_ids"]) < 3:
            d["run_ids"].append(r["run_id"])
    return {"available": bool(ix.runs), "failed_goals": list(goals.values()),
            "note": "" if ix.runs else f"no signal: no experience yet ({runs_dir})"}


def gather_signals(*, ontology: str | Path = ONTOLOGY,
                   runs_dir: str | Path = RUNS) -> dict:
    return {"ontology": read_contradictions(ontology),
            "experience": read_failures(runs_dir)}


def read_history(pulse_log: str | Path = PULSE_LOG) -> list[dict]:
    """Past drive_pulse records (the shared heartbeat log). Parsing replicated
    from aios_drive._read_pulses — not imported, because aios_drive imports
    this module at pulse time."""
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


# ---------------------------------------------------------------------------
# harvest — questions are BORN from existing organ output only (no LLM in v1)
# ---------------------------------------------------------------------------

def harvest_questions(signals: dict, state: dict, *, now: float,
                      skills_registry: str | Path = SKILLS_REGISTRY) -> list[dict]:
    """Deterministic question templates over the four existing inflows:
    ontology contradictions, DRIVE's dominant pain, experience failures, and
    repeated failures with no covering skill (via aios_skills.retrieve).
    Empty/missing inputs simply yield no questions from that organ."""
    questions: list[dict] = []
    ont = signals.get("ontology") or {}
    exp = signals.get("experience") or {}

    # 1) each ontology contradiction IS a standing question
    if ont.get("available"):
        for e in ont.get("edges") or []:
            refs = sorted([e["src"], e["dst"]])
            questions.append({
                "qid": qid_for("contradiction", refs),
                "kind": "contradiction", "organ": "ontology", "refs": refs,
                "q": f"Which holds: “{e['src_label']}” OR "
                     f"“{e['dst_label']}”?",
                "harvested_ts": float(now),
            })

    # 2) DRIVE's dominant pain component
    dominant = (state or {}).get("dominant")
    if dominant:
        questions.append({
            "qid": qid_for("pain", [dominant]),
            "kind": "pain", "organ": "drive", "refs": [dominant],
            "q": f"Why is ‘{dominant}’ the dominant pain component?",
            "harvested_ts": float(now),
        })

    # 3) each failing goal in the experience graph
    failed_goals = (exp.get("failed_goals") or []) if exp.get("available") else []
    for d in failed_goals:
        goal = d["goal"]
        questions.append({
            "qid": qid_for("failure", [goal]),
            "kind": "failure", "organ": "experience", "refs": [goal],
            "q": (f"Why does ‘{goal}’ keep failing "
                  f"({d['n']} failures, exits {d['exits']})?" if d["n"] >= 2
                  else f"Why did ‘{goal}’ fail (exit {d['exits']})?"),
            "harvested_ts": float(now),
        })

    # 4) repeated failure with NO covering skill -> a missing-tool question
    for d in failed_goals:
        if d["n"] < GAP_MIN_FAILURES:
            continue
        try:
            covered = _skills.retrieve(d["goal"], k=1, registry=skills_registry)
        except Exception:  # noqa: BLE001 — a broken registry is "no cover", honestly
            covered = []
        if not covered:
            questions.append({
                "qid": qid_for("gap", [d["goal"]]),
                "kind": "gap", "organ": "skills", "refs": [d["goal"]],
                "q": f"What tool is missing for ‘{d['goal']}’ "
                     f"(failed {d['n']}×, no covering skill)?",
                "harvested_ts": float(now),
            })

    # dominant-pain interference is stamped at harvest (state is in scope here)
    for q in questions:
        comp = _KIND_COMPONENT.get(q["kind"])
        q["on_dominant"] = bool(dominant) and (comp == dominant or q["kind"] == "pain")
    return questions


# ---------------------------------------------------------------------------
# resonance — constructive interference + damping (pure over history)
# ---------------------------------------------------------------------------

def _bearing(history: list[dict]) -> list[dict]:
    """Pulses that carry a questions section (post-Phase-8 heartbeats)."""
    return [p for p in history
            if isinstance(p.get("questions"), dict)
            and isinstance(p["questions"].get("asked"), list)]


def _asked_map(pulse: dict) -> dict[str, str]:
    """qid -> status for one pulse's questions section."""
    return {str(a.get("qid")): str(a.get("status"))
            for a in pulse["questions"]["asked"] if isinstance(a, dict)}


def _open_asks(qid: str, history: list[dict]) -> list[int]:
    """Indices (into questions-bearing pulses) where qid was asked open."""
    return [i for i, p in enumerate(_bearing(history))
            if _asked_map(p).get(qid) == "open"]


def _settled(qid: str, history: list[dict]) -> bool:
    """A question is settled if it was once asked and a LATER questions-bearing
    pulse did not raise it (its referent went away). If it is being harvested
    again NOW, it re-emerged — damp it."""
    bearing = _bearing(history)
    asks = _open_asks(qid, history)
    return bool(asks) and any(qid not in _asked_map(bearing[j])
                              for j in range(asks[0] + 1, len(bearing)))


def resonate(questions: list[dict], history: list[dict], *, now: float) -> list[dict]:
    """Amplitude per question, ranked descending. `now` is reserved for
    time-decayed recurrence (v2); v1 counts pulses, not hours.

    amplitude = recurrence + multi-organ interference + dominant-pain bonus
                − settled damping   (floored at 0; constants UNCALIBRATED v1)
    """
    refsets = [(set(q["refs"]), q["organ"]) for q in questions]
    out = []
    for q in questions:
        mine = set(q["refs"])
        organs = {org for refs, org in refsets if refs & mine}
        recurrence = min(len(_open_asks(q["qid"], history)) * AMP_RECURRENCE,
                         RECURRENCE_CAP)
        multi = (len(organs) - 1) * AMP_MULTI_ORGAN if organs else 0.0
        dom = AMP_DOMINANT_BONUS if q.get("on_dominant") else 0.0
        settled = _settled(q["qid"], history)
        damping = AMP_SETTLED_DAMPING if settled else 0.0
        amp = max(0.0, recurrence + multi + dom - damping)
        out.append(dict(q, settled=settled, amplitude=round(amp, 2),
                        amplitude_parts={"recurrence": round(recurrence, 2),
                                         "multi_organ": round(multi, 2),
                                         "dominant_bonus": dom,
                                         "damping": damping}))
    out.sort(key=lambda q: (-q["amplitude"], q["qid"]))
    return out


# ---------------------------------------------------------------------------
# routing — name the EXISTING organ that should answer (route, don't execute)
# ---------------------------------------------------------------------------

def route(question: dict) -> dict:
    """Which existing organ answers this kind of question, with a concrete
    suggested invocation. v1 routes and records only — executing any of these
    stays with the head/operator (recommendation-first DNA)."""
    kind, refs = question.get("kind"), question.get("refs") or ["?"]
    if kind == "contradiction":
        return {"organ": "memory.retrieve",
                "invocation": (f"python3 experiments/ontology/query.py neighbors "
                               f"'{refs[0]}'  # evidence for both nodes, then "
                               "scope/retract/merge the weaker claim")}
    if kind == "failure":
        return {"organ": "escalate+verifier",
                "invocation": (f"python3 scripts/aios_head.py '{refs[0]}' --loop "
                               "--escalate  # substrate cascade, Weaver-scored")}
    if kind == "gap":
        return {"organ": "operator",
                "invocation": (f"aios_skills.induce_and_register(goal='{refs[0]}', "
                               "solution_code=<solving code>)  # sandbox-gated")}
    if kind == "pain":
        return {"organ": "genesis.challenge",
                "invocation": (f"aios_challenge (MCP): why does '{refs[0]}' "
                               "dominate — is the metric or the goal wrong?")}
    return {"organ": "operator",
            "invocation": "unknown question kind — surface to the operator"}


# ---------------------------------------------------------------------------
# anti-rumination — the load-bearing damper
# ---------------------------------------------------------------------------

def _behavior_changes(before: dict, after: dict) -> list[str]:
    """aios_drive.pulse_effect over the snapshots stored in the pulse log,
    minus pin_advanced: re-pinning is bookkeeping and answers no question.
    Lazy import — aios_drive imports this module at pulse time, so a top-level
    import here would be circular."""
    import aios_drive as _drive
    changes = _drive.pulse_effect(before or {}, after or {})["changes"]
    return [c for c in changes if c != "pin_advanced"]


def rumination_check(qid: str, history: list[dict]) -> dict:
    """A question asked >= RUMINATION_N times with ZERO behavioral change
    recorded in between (per the pulse-log state snapshots) is rumination and
    must be retired. Missing snapshots count as zero RECORDED change — absence
    of evidence of change is not change."""
    bearing = _bearing(history)
    asks = _open_asks(qid, history)
    already = any(_asked_map(p).get(qid) == "retired_rumination" for p in bearing)
    verdict = {"qid": qid, "asked_n": len(asks), "already_retired": already,
               "ruminating": False, "behavior_changes": [], "reason": ""}
    if already or len(asks) < RUMINATION_N:
        return verdict
    first_state = bearing[asks[0]].get("state") or {}
    last_state = bearing[-1].get("state") or {}
    changes = _behavior_changes(first_state, last_state)
    verdict["behavior_changes"] = changes
    if not changes:
        verdict["ruminating"] = True
        verdict["reason"] = (
            f"asked {len(asks)}× across pulses with zero recorded "
            "behavioral change (no contradiction resolved / failure cleared / "
            "skill registered)"
            + ("" if first_state and last_state
               else " — and no state snapshots recorded to show otherwise"))
    return verdict


# ---------------------------------------------------------------------------
# cycle — harvest -> anti-rumination -> resonate -> route (one heartbeat's ASK)
# ---------------------------------------------------------------------------

def cycle(signals: dict, state: dict, history: list[dict], *, now: float,
          skills_registry: str | Path = SKILLS_REGISTRY,
          top_k: int = TOP_K) -> dict:
    """The questions section for one pulse record: full detail for the top-k
    and any newly retired questions; a compact qid/kind/organ/status row for
    everything asked (that row is what future pulses' recurrence and
    rumination checks read). Previously retired qids are excluded from the
    harvest entirely — unless their refs changed, which is a new qid."""
    harvested = harvest_questions(signals, state, now=now,
                                  skills_registry=skills_registry)
    live: list[dict] = []
    retired_now: list[dict] = []
    excluded = 0
    for q in harvested:
        rc = rumination_check(q["qid"], history)
        if rc["already_retired"]:
            excluded += 1              # stays retired until its refs change
            continue
        if rc["ruminating"]:
            retired_now.append(dict(q, status="retired_rumination",
                                    reason=rc["reason"], asked_n=rc["asked_n"]))
        else:
            live.append(q)
    ranked = resonate(live, history, now=now)
    for q in ranked:
        q["route"] = route(q)
        q["status"] = "open"
    asked = [{"qid": q["qid"], "kind": q["kind"], "organ": q["organ"],
              "status": q["status"]} for q in ranked + retired_now]
    note = ""
    if not harvested:
        note = ("no questions — no organ raised any "
                "(empty inputs degrade honestly)")
    return {"schema": SCHEMA, "available": True, "ts": float(now),
            "n_harvested": len(harvested), "n_open": len(ranked),
            "n_retired_now": len(retired_now), "n_excluded_retired": excluded,
            "top": ranked[:max(0, int(top_k))],
            "retired": [{"qid": q["qid"], "kind": q["kind"], "q": q["q"],
                         "status": q["status"], "reason": q["reason"],
                         "asked_n": q["asked_n"]} for q in retired_now],
            "asked": asked, "note": note}


def pulse_questions(state: dict, history: list[dict], *, now: float,
                    ontology: str | Path = ONTOLOGY,
                    runs_dir: str | Path = RUNS,
                    skills_registry: str | Path = SKILLS_REGISTRY,
                    top_k: int = TOP_K) -> dict:
    """The entry point aios_drive.pulse() calls: gather the full inflow
    signals (all contradiction edges — the drive pain record truncates its
    own) and run one ASK cycle. Read-only; the caller appends the result
    inside its pulse record."""
    signals = gather_signals(ontology=ontology, runs_dir=runs_dir)
    return cycle(signals, state, history, now=now,
                 skills_registry=skills_registry, top_k=top_k)


# ---------------------------------------------------------------------------
# report — is this thought or rumination? (the organ's own kill criterion)
# ---------------------------------------------------------------------------

def resonance_report(history: list[dict]) -> dict:
    """Over all questions-bearing pulses: what fraction of raised questions
    saw their referents measurably CHANGE afterwards (resolved = the organ
    stopped raising the qid while still observable), plus the rumination
    count. A ~0 resolution rate over a real sample means the organ is
    rumination, not thought — and the verdict says so."""
    bearing = _bearing(history)
    if not bearing:
        return {"schema": SCHEMA, "kind": "report",
                "question_resolution_rate": None,
                "verdict": "no question-bearing pulses yet — "
                           "the organ has never asked",
                "pulses_with_questions": 0, "distinct_questions": 0,
                "resolved": 0, "standing": 0, "rumination_count": 0,
                "unobservable": 0, "top_standing": []}
    latest = bearing[-1]
    latest_asked = _asked_map(latest)
    latest_comps = latest.get("components") or {}

    first_seen: dict[str, int] = {}
    kinds: dict[str, str] = {}
    retired: set[str] = set()
    for i, p in enumerate(bearing):
        for a in p["questions"]["asked"]:
            if not isinstance(a, dict):
                continue
            qid = str(a.get("qid"))
            first_seen.setdefault(qid, i)
            kinds.setdefault(qid, str(a.get("kind")))
            if a.get("status") == "retired_rumination":
                retired.add(qid)

    resolved = standing = unobservable = 0
    checkable = 0
    for qid, first in first_seen.items():
        if qid in retired:
            continue
        if qid in latest_asked:
            standing += 1
            if first < len(bearing) - 1:
                checkable += 1
            continue
        if first >= len(bearing) - 1:
            continue                       # first asked at the latest pulse
        comp = _KIND_COMPONENT.get(kinds.get(qid))
        comp_state = latest_comps.get(comp) if comp else None
        if comp and isinstance(comp_state, dict) and not comp_state.get("available"):
            unobservable += 1              # organ went dark ≠ question resolved
            continue
        resolved += 1
        checkable += 1
    checkable += sum(1 for qid in retired if first_seen[qid] < len(bearing) - 1)

    rate = round(resolved / checkable, 4) if checkable else None
    if rate is None:
        verdict = ("no resolution-checkable questions yet (all first asked at "
                   "the latest pulse) — keep pulsing")
    elif rate == 0 and checkable >= 3 and len(bearing) >= 3:
        # "real sample" = at least 3 question-bearing pulses, mirroring
        # DRIVE's theater criterion — two heartbeats minutes apart must not
        # condemn the organ before anyone had a chance to answer.
        verdict = ("RUMINATION by the organ's own criterion: questions are "
                   "asked but their referents never change — this organ is "
                   "rumination, not thought; kill it or wire its routes to "
                   "an actor")
    else:
        verdict = (f"{resolved}/{checkable} checkable questions saw their "
                   "referents measurably change after being raised")
    return {"schema": SCHEMA, "kind": "report",
            "question_resolution_rate": rate,   # THE number — read this first
            "verdict": verdict,
            "pulses_with_questions": len(bearing),
            "distinct_questions": len(first_seen),
            "resolved": resolved, "standing": standing,
            "rumination_count": len(retired), "unobservable": unobservable,
            "top_standing": latest["questions"].get("top") or []}


# ---------------------------------------------------------------------------
# CLI — read-only (the impure edge supplies the real clock)
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import time
    ap = argparse.ArgumentParser(
        description="AIOS resonance — the self-questioning loop (ask / "
                    "standing / report). Read-only: questions are RECORDED "
                    "only by the aios_drive.pulse heartbeat.")
    ap.add_argument("--ontology", default=str(ONTOLOGY))
    ap.add_argument("--runs-dir", default=str(RUNS))
    ap.add_argument("--exp-manifest", default=str(_experience.MANIFEST))
    ap.add_argument("--skills-registry", default=str(SKILLS_REGISTRY))
    ap.add_argument("--pulse-log", default=str(PULSE_LOG))
    ap.add_argument("--top-k", type=int, default=TOP_K)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ask", help="harvest+resonate+route for the current real "
                               "state (records nothing)")
    sub.add_parser("standing", help="standing questions from the latest "
                                    "questions-bearing pulse")
    sub.add_parser("report", help="question_resolution_rate + rumination "
                                  "count (the organ's kill criterion)")
    args = ap.parse_args(argv)

    history = read_history(args.pulse_log)
    if args.cmd == "ask":
        import aios_drive as _drive     # lazy: _drive imports this module
        state = _drive.homeostasis(
            time.time(), ontology=args.ontology, runs_dir=args.runs_dir,
            exp_manifest=args.exp_manifest, skills_registry=args.skills_registry)
        out = pulse_questions(state, history, now=time.time(),
                              ontology=args.ontology, runs_dir=args.runs_dir,
                              skills_registry=args.skills_registry,
                              top_k=args.top_k)
    elif args.cmd == "standing":
        bearing = _bearing(history)
        latest = bearing[-1] if bearing else None
        out = {"schema": SCHEMA, "kind": "standing",
               "pulses_with_questions": len(bearing),
               "latest_ts_iso": latest.get("ts_iso") if latest else None,
               "n_open": latest["questions"].get("n_open") if latest else None,
               "n_retired_now": latest["questions"].get("n_retired_now")
               if latest else None,
               "top": latest["questions"].get("top") if latest else [],
               "note": "" if latest else "no question-bearing pulses yet"}
    else:
        out = resonance_report(history)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
