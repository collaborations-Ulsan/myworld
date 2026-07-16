#!/usr/bin/env python3
"""m2_driftbench memory — the prereg §3a H3 memory-arm policy (ASC-0282 WP-B2).

Frozen policy (prereg-A §3a, implemented verbatim):
  * STORE: at instance end, a model-generated lesson summary for that template,
    <= 500 chars (`distill_lesson` — ONE metered model call, source="memory",
    inside the instance's own token budget per v1.1 §B).
  * INJECT: at the start of the NEXT instance of the SAME template family;
    cross-SEED transfer allowed, cross-TEMPLATE forbidden (the store is keyed
    by (arm, template_id) — arms never share memory, prereg §3 isolation).
  * `weak+memory`: ALWAYS injects, no staleness check (the ProEvolve
    collapse-under-mutation arm).
  * `weak+AIOS`: the SAME stored note passes a DriftBench-style contract check
    before injection — every (key, value) fact pair captured WITH the note at
    store time is validated against the CURRENT instance's mechanical claims;
    any contradicted pair marks the note STALE and injection is suppressed +
    recorded (drift_detected trigger for the §5 condition-4 causal trace).

Mechanical staleness (no LLM): fact pairs are not parsed out of the note's
free text (that would be LLM territory) — they are the source instance's OWN
active claim pairs, captured mechanically at store time. A pair contradicts
when the same fact key exists in the current ledger with a different value;
a pair whose key is absent here is ignored (different seed's world — neither
confirmed nor contradicted). Values are seed-drawn, so cross-seed notes that
baked in concrete values go stale by construction — exactly the
ProEvolve-predicted failure the H3 arm exists to measure.

stdlib only. ~140 lines (within the brief's ~150-line budget — no stub needed).
"""
from __future__ import annotations

import json
from pathlib import Path

LESSON_CHAR_CAP = 500   # frozen (prereg §3a)

DISTILL_PROMPT = (
    "The episode above is over. In <=400 characters, write ONE durable lesson "
    "for the NEXT operator working a task of this same template. State "
    "strategy (what to check, in what order, which trap to avoid), not chatter. "
    "Plain text only.\n\nEpisode template: {template_id}\nTask: {task}\n"
    "Your final action was: {final_action}\n"
)


def _norm_pair(key: str, value: str) -> "tuple[str, str]":
    return str(key), str(value)


def capture_context_facts(claims: list[dict]) -> list[list[str]]:
    """Mechanically capture the (key, value) pairs active in the SOURCE
    instance at store time (claims = env.known_claims())."""
    pairs = []
    for c in claims:
        payload = c.get("payload") or {}
        keys = payload.get("input") or []
        if keys:
            pairs.append(list(_norm_pair(keys[0], payload.get("output", ""))))
    return pairs


def staleness_check(note: dict, current_claims: list[dict]) -> dict:
    """DriftBench-style contract validation of a stored note against the
    CURRENT instance's active claims. PURE + mechanical.

    Returns {"stale": bool, "contradicted": [[key, stored, current], ...]}."""
    current: dict = {}
    for c in current_claims:
        payload = c.get("payload") or {}
        keys = payload.get("input") or []
        if keys:
            current.setdefault(str(keys[0]), set()).add(str(payload.get("output", "")))
    contradicted = []
    for key, stored_value in note.get("context_facts") or []:
        vals = current.get(str(key))
        if vals is not None and str(stored_value) not in vals:
            contradicted.append([str(key), str(stored_value), sorted(vals)])
    return {"stale": bool(contradicted), "contradicted": contradicted}


class MemoryStore:
    """Per-ARM lesson store, keyed by template_id (cross-seed transfer allowed,
    cross-template forbidden — prereg §3a). Optionally file-backed so a
    resumable run keeps its memory chain; arms get separate files."""

    def __init__(self, arm: str, path: "Path | str | None" = None):
        self.arm = arm
        self.path = Path(path) if path else None
        self._notes: dict[str, dict] = {}
        if self.path and self.path.is_file():
            self._notes = json.loads(self.path.read_text(encoding="utf-8"))

    def store(self, template_id: str, lesson: str, context_facts: list) -> dict:
        note = {"template_id": template_id, "arm": self.arm,
                "lesson": str(lesson)[:LESSON_CHAR_CAP],
                "context_facts": list(context_facts)}
        self._notes[template_id] = note
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._notes, ensure_ascii=False,
                                            indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
        return note

    def note_for(self, template_id: str) -> "dict | None":
        return self._notes.get(template_id)


def inject_note(store: "MemoryStore | None", template_id: str,
                current_claims: list[dict], *, staleness_gated: bool) -> dict:
    """Resolve the injection for one episode start, per the frozen policy.

    Returns {"injected": bool, "prefix": str, "stale": bool, "detail": ...}.
    `staleness_gated=False` -> weak+memory (always inject);
    `staleness_gated=True`  -> weak+AIOS (suppress + mark when stale)."""
    if store is None:
        return {"injected": False, "prefix": "", "stale": False, "detail": "no store"}
    note = store.note_for(template_id)
    if note is None:
        return {"injected": False, "prefix": "", "stale": False, "detail": "no prior note"}
    if staleness_gated:
        check = staleness_check(note, current_claims)
        if check["stale"]:
            return {"injected": False, "prefix": "", "stale": True,
                    "detail": {"suppressed_note": note["lesson"][:120],
                               "contradicted": check["contradicted"]}}
    prefix = ("LESSON FROM A PREVIOUS EPISODE OF THIS TEMPLATE (may or may not "
              f"still apply):\n{note['lesson']}\n\n")
    return {"injected": True, "prefix": prefix, "stale": False,
            "detail": {"lesson_chars": len(note["lesson"])}}


def distill_lesson(adapter, template_id: str, task_prompt: str,
                   final_action: "dict | None", meter, trace=None) -> str:
    """ONE model call distilling the episode lesson (metered, source='memory').
    A dead adapter returns '' (the note is best-effort; the EPISODE result is
    already recorded — memory failure must never fail the run)."""
    prompt = DISTILL_PROMPT.format(
        template_id=template_id, task=str(task_prompt)[:400],
        final_action=json.dumps(final_action or {}, ensure_ascii=False)[:200])
    try:
        raw = adapter(prompt)
    except Exception as exc:  # noqa: BLE001 — best-effort by contract (see docstring)
        if trace is not None:
            trace.write({"kind": "memory_distill_failed", "reason": str(exc)[:120]})
        return ""
    if meter is not None and not getattr(adapter, "metered", False):
        meter.add_model_call(prompt, raw, source="memory")
    if trace is not None:
        trace.write({"kind": "memory_distilled", "template_id": template_id,
                     "chars": len(raw or "")})
    return str(raw or "").strip()[:LESSON_CHAR_CAP]
