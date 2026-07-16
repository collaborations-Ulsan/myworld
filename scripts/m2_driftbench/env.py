#!/usr/bin/env python3
"""m2_driftbench env — deterministic per-instance local environment (ASC-0282 WP-B).

Each instance gets its OWN isolated root (static and mutating instances never
share one — prereg v1.1 §B static-control isolation) containing:

    <root>/ledger.jsonl        Akashic-draft-schema records (synthetic content)
    <root>/files/...           episode file fixtures
    <root>/final_action.json   written when the agent commits its final action

The agent-visible tree contains NO grader material: grader specs live under
scripts/m2_driftbench/grader_specs/, outside every env root (README rule; the
grader is invoked as a separate process only after the episode ends).

`known_claims()` is MECHANICAL — record -> claim dicts
{task_id, source_id, kind, payload, ts} matching
experiments/agi_witness/contracts.py:Claim — never LLM-typed. Two records
asserting the same fact key with different values map to two IO claims with
the same task_id + input and different output, which is exactly what
`direct_io_conflicts` (APEX/DescentNet certs) detects.

WP-B2 additions (ASC-0282 freeze packet — all additive):

* CLAIMS SCOPING (supervisor requirement): `known_claims(target=...)` scopes
  the claim set mechanically to the final_action's TARGET entity via the pure
  `scope_claims_to_target()` below, so a harmless conflict elsewhere in the
  ledger cannot block an unrelated correct answer (the prereg §1
  `obstruction-present-but-harmless` control family depends on this).
  `known_claims()` with no target keeps the original whole-ledger behavior.
* SUPERSEDE semantics (mechanical, part of the Akashic-draft record shape):
  a record carrying `"supersedes": "<record_id>"` retires the named record's
  claim — a clean REVISION is not a contradiction. Records without a
  supersede link that disagree remain a genuine conflict. This is runtime
  ledger mechanics, never LLM judgment.
* 8-type drift taxonomy handlers (prereg v1.1 §D / arXiv:2605.10990 vocab):
  every drift type maps to one declarative applier (`append_records` /
  `write_files` / `invalidates`); schema_change additionally keeps its v1→v2
  fact-shape rewrite. Drift events record what they `invalidate` so the
  stale-action labeler stays mechanical.
* `ask_oracle` — the prereg §4 ASK affordance: a SCRIPTED oracle answering
  questions about the task SPEC only (hidden grader state and correct answers
  are never in its answer table), capped per episode, 1 action per query.
* corrupted-oracle wiring (prereg-B v1.2 fold #1): when the instance carries
  `corrupted_oracle=True`, `_build` injects the instance's single plausible
  false record at t=0 (ts=0), before any agent turn.
* turn tracking: `apply_drift_for_turn` records the current turn so
  `record_final_action` can stamp the commit turn (grader race-guard:
  `min_commit_turn`).

stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path

FINAL_ACTIONS = ("answer", "quarantine", "requery_provenance", "ask_clarification", "abstain")

_V2_SCHEMA = "aios.akashic_draft.v2"

ORACLE_QUERY_CAP = 3   # frozen: ask_oracle queries per episode (prereg §4: 1 action each)

# 8-type drift taxonomy (prereg v1.1 §D; arXiv:2605.10990 vocabulary). Every
# scheduled drift's drift_type must be one of these — fail-fast on typos.
DRIFT_TAXONOMY = (
    "url_change", "version_bump", "config_change", "api_migration",
    "deprecation", "schema_change", "auth_change", "dependency_update",
)


def _extract_fact(record: dict) -> "tuple[str, str] | None":
    """Schema-tolerant mechanical fact extraction (v1 nested / v2 flat)."""
    fact = record.get("fact")
    if isinstance(fact, dict) and "key" in fact:
        return str(fact["key"]), str(fact.get("value"))
    if "fact_key" in record:
        return str(record["fact_key"]), str(record.get("fact_value"))
    return None


# ── pure claims-scoping helpers (supervisor requirement; unit-tested) ─────────

_norm_keep = set("abcdefghijklmnopqrstuvwxyz0123456789")


def _norm(text: str) -> str:
    """Lowercase; every non-alphanumeric char becomes a space; collapsed."""
    out = []
    for ch in str(text).lower():
        out.append(ch if ch in _norm_keep else " ")
    return " ".join("".join(out).split())


def _padded(text: str) -> str:
    return f" {_norm(text)} " if _norm(text) else ""


def _claim_matches_target(claim: dict, target_text: str) -> bool:
    """Mechanical entity match of ONE claim's payload against the target text.

    Design decision (documented, deterministic — mirrors schema.py's ambiguity-
    flag style): a claim matches iff
      (a) the claim's full normalized fact key appears in the target,   OR
      (b) any dot-component of the key (>=4 normalized chars) appears in the
          target — or the whole target (>=4 chars) appears in that component, OR
      (c) the claim's normalized VALUE appears in the target — or the whole
          target appears in the value (token-boundary containment both ways,
          so terse targets like "v1" match a URL value containing "v1" while
          "5" can never match inside "35").
    """
    t = _padded(target_text)
    if not t.strip():
        return False
    payload = claim.get("payload") or {}
    key = " ".join(str(x) for x in (payload.get("input") or []))
    value = str(payload.get("output", ""))

    k = _norm(key)
    if k and f" {k} " in t:                                    # (a) full key in target
        return True
    t_norm = _norm(target_text)
    for comp in key.split("."):
        c = _norm(comp)
        if len(c) < 4:
            continue
        if f" {c} " in t:                                      # (b) component in target
            return True
        if len(t_norm) >= 4 and t in f" {c} ":                 # (b') target in component
            return True
    v = _norm(value)
    if v and (f" {v} " in t or t in f" {v} "):                 # (c) value containment
        return True
    return False


def scope_claims_to_target(claims: list[dict], target: str) -> list[dict]:
    """PURE mechanical scoping: return the claims about the fact(s) the target
    entity touches. Matching is per-claim (key or value containment); the scope
    then widens to EVERY claim sharing a matched claim's task_id, so a commit
    that names one value of a disputed fact still pulls in the whole dispute
    (the conflict stays visible to the gate). An empty/blank target or a target
    matching nothing returns [] — the gate then honestly reports "no claims
    provided" and the unsupported-final-claim labeler takes over."""
    if not _norm(target):
        return []
    matched_tasks = {c.get("task_id") for c in claims if _claim_matches_target(c, target)}
    if not matched_tasks:
        return []
    return [c for c in claims if c.get("task_id") in matched_tasks]


class EpisodeEnv:
    """One isolated episode environment materialized from an InstanceSpec."""

    def __init__(self, instance, root: "Path | str"):
        self.instance = instance
        self.root = Path(root)
        self.files_dir = self.root / "files"
        self.ledger_path = self.root / "ledger.jsonl"
        self.final_action_path = self.root / "final_action.json"
        self.drift_schedule = [dict(d) for d in instance.drift_schedule]
        self.applied_drifts: list[dict] = []
        self.events: list[dict] = []      # env event log (drift applications etc.)
        self.final_action: "dict | None" = None
        self.episode_done = False
        self.current_turn = 0             # last turn_context seen (drift/commit stamps)
        self.oracle_queries = 0           # ask_oracle usage against ORACLE_QUERY_CAP
        self._build()

    # ── materialization ──────────────────────────────────────────────────────

    def _build(self) -> None:
        self.files_dir.mkdir(parents=True, exist_ok=True)
        records = list(self.instance.records)
        # Corrupted-oracle wiring (prereg-B v1.2 fold #1): ONE plausible false
        # fact injected at t=0 when the instance flag is set — present before
        # any agent turn, indistinguishable in shape from honest records.
        corrupted = getattr(self.instance, "corrupted_record", None)
        if getattr(self.instance, "corrupted_oracle", False) and corrupted:
            records = [dict(corrupted)] + records
            self.events.append({"kind": "corrupted_oracle_injected",
                                "record_id": corrupted.get("id"), "ts": 0})
        self._write_records(records)
        for rel, content in self.instance.files.items():
            p = self.files_dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def _load_records(self) -> list[dict]:
        out = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def _write_records(self, records: list[dict]) -> None:
        with self.ledger_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    # ── mechanical claim / population extraction (never LLM-typed) ──────────

    def known_claims(self, target: "str | None" = None,
                     include_superseded: bool = False) -> list[dict]:
        """Ledger records -> Claim dicts (contracts.py:Claim shape).

        Mechanical supersede semantics: a record named by another record's
        `supersedes` field is retired (its claim is dropped) — a clean revision
        is runtime ledger mechanics, not a contradiction. Conflicting records
        WITHOUT a supersede link still surface as two claims (genuine dispute).

        `target` (supervisor scoping requirement): when given, the result is
        scoped to the target entity — the entity match runs on the RAW claim
        set (a commit naming a RETIRED value is still ABOUT that fact, and the
        fact's ACTIVE claims must stay in scope to conflict with it), then
        widens to every claim sharing a matched claim's task. A harmless
        conflict elsewhere in the ledger stays out of scope. `known_claims()`
        with no target = the whole (supersede-filtered) ledger, exactly as
        before for records without supersede links. `include_superseded=True`
        returns the RAW view (labelers need it for the (iii)-vs-(iv)
        distinction)."""
        records = self._load_records()
        superseded = {str(r["supersedes"]) for r in records if r.get("supersedes")}
        raw: list[dict] = []
        for rec in records:
            fact = _extract_fact(rec)
            if fact is None:
                continue
            key, value = fact
            raw.append({
                "task_id": f"fact::{key}",
                "source_id": str(rec.get("source_id", "unknown")),
                "kind": "io",
                "payload": {"input": [key], "output": value},
                "ts": int(rec.get("ts", 0)),
                "_superseded": str(rec.get("id")) in superseded,
            })

        def _strip(c: dict) -> dict:
            return {k: v for k, v in c.items() if k != "_superseded"}

        pool = raw if include_superseded else [c for c in raw if not c["_superseded"]]
        if target is None:
            return [_strip(c) for c in pool]
        matched_tasks = {c["task_id"] for c in raw if _claim_matches_target(c, target)}
        return [_strip(c) for c in pool if c["task_id"] in matched_tasks]

    def commit_claims(self, target: str) -> list[dict]:
        """MECHANICAL proposal-claims for an assertive commit (WP-B2): what does
        `final_action(answer, target=...)` itself assert about the ledger's
        facts? For every fact task the target entity-matches — matched against
        the RAW claim set including superseded records, so committing a retired
        value is still recognized as being ABOUT that fact — emit one IO claim
        {task, output}: the output is the raw ledger value contained in the
        target when one is (agreeing commits produce no conflict), else the
        normalized target itself (a value the ledger never held conflicts with
        the active claim — the gate blocks it as contradicting the record).
        Deterministic string mechanics only; never LLM-typed."""
        if not _norm(target):
            return []
        raw = self.known_claims(include_superseded=True)
        matched = scope_claims_to_target(raw, target)
        if not matched:
            return []
        t = _padded(target)
        active_by_task: dict = {}
        for c in self.known_claims():
            active_by_task.setdefault(c["task_id"], []).append(c)
        out: list[dict] = []
        for task_id in sorted({c["task_id"] for c in matched}):
            task_claims = [c for c in matched if c["task_id"] == task_id]
            committed = None
            # Prefer an ACTIVE value contained in the target (an agreeing commit
            # must never manufacture a conflict just because the target also
            # narrates the retired value it migrated away from).
            for c in active_by_task.get(task_id, []) + task_claims:
                v = _norm(str(c["payload"].get("output", "")))
                if v and f" {v} " in t:
                    committed = str(c["payload"].get("output", ""))
                    break
            if committed is None:
                committed = _norm(target)
            key = task_claims[0]["payload"]["input"]
            out.append({"task_id": task_id, "source_id": "final_action_commit",
                        "kind": "io", "payload": {"input": list(key), "output": committed},
                        "ts": 10**6})
        return out

    def profiles_population(self) -> list[dict]:
        """Commons-entry dicts {"category","top_tools"} for the gate's H0 guard
        (scripts/aios_epistemic_gate.py honest-scope contract)."""
        pop = []
        for rec in self._load_records():
            if rec.get("category") and rec.get("top_tools"):
                pop.append({"id": rec.get("id"), "category": rec["category"],
                            "top_tools": list(rec["top_tools"])})
        return pop

    # ── drift ────────────────────────────────────────────────────────────────

    def apply_drift_for_turn(self, turn: int) -> list[dict]:
        """Apply all not-yet-applied mutations scheduled at <= turn. Called on
        run_loop's turn_context (i.e. BEFORE the sampler acts on that turn).
        Returns the events applied now (also appended to self.events).
        Also tracks the current turn for the final-action commit stamp."""
        self.current_turn = max(self.current_turn, int(turn))
        applied_now = []
        for d in self.drift_schedule:
            if d.get("_applied") or int(d["turn"]) > turn:
                continue
            handler = getattr(self, f"_drift_{d['drift_type']}", None)
            if handler is None:
                raise ValueError(f"unknown drift_type {d['drift_type']!r}")
            detail = handler(d.get("params") or {})
            d["_applied"] = True
            event = {"kind": "drift_applied", "turn": turn,
                     "scheduled_turn": int(d["turn"]),
                     "drift_type": d["drift_type"], **detail}
            self.applied_drifts.append(event)
            self.events.append(event)
            applied_now.append(event)
        return applied_now

    # -- declarative drift applier (shared by the 8-type taxonomy handlers) ---
    #
    # Every taxonomy drift reduces to the same three mechanical operations on
    # the episode environment, declared in the drift's params by fixtures.py:
    #   append_records: [record dict, ...]   new ledger records arrive (a
    #       revision carries "supersedes": "<record_id>" — clean supersession;
    #       records WITHOUT it create a genuine conflict)
    #   write_files: {relpath: content}      workspace ground truth changes
    #   invalidates: [{"key": k, "old_value": v}, ...]  what this drift makes
    #       stale — recorded in the event so the prereg §4 (iii) stale-action
    #       labeler stays mechanical (an answer matching an invalidated value
    #       after the drift applied = stale action).
    def _apply_declarative(self, params: dict) -> dict:
        appended = 0
        for rec in params.get("append_records") or []:
            with self.ledger_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            appended += 1
        wrote = []
        for rel, content in (params.get("write_files") or {}).items():
            p = self.files_dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            wrote.append(rel)
        return {
            "records_appended": appended,
            "files_written": wrote,
            "invalidates": [dict(x) for x in (params.get("invalidates") or [])],
        }

    def _drift_api_migration(self, params: dict) -> dict:
        return self._apply_declarative(params)

    def _drift_deprecation(self, params: dict) -> dict:
        return self._apply_declarative(params)

    def _drift_config_change(self, params: dict) -> dict:
        return self._apply_declarative(params)

    def _drift_version_bump(self, params: dict) -> dict:
        return self._apply_declarative(params)

    def _drift_auth_change(self, params: dict) -> dict:
        return self._apply_declarative(params)

    def _drift_url_change(self, params: dict) -> dict:
        return self._apply_declarative(params)

    def _drift_dependency_update(self, params: dict) -> dict:
        return self._apply_declarative(params)

    def _drift_schema_change(self, params: dict) -> dict:
        """v1 nested fact -> v2 flat fact_key/fact_value; idempotent. May also
        carry the declarative keys (e.g. a migration that fixes one value by
        appending a superseding record while rewriting the shape)."""
        to_schema = params.get("to_schema", _V2_SCHEMA)
        records = self._load_records()
        changed = 0
        for rec in records:
            fact = rec.pop("fact", None)
            if isinstance(fact, dict) and "key" in fact:
                rec["fact_key"] = fact["key"]
                rec["fact_value"] = fact.get("value")
                rec["schema"] = to_schema
                changed += 1
        self._write_records(records)
        detail = self._apply_declarative(params)
        detail.update({"records_changed": changed, "to_schema": to_schema})
        return detail

    # ── agent-facing tools (registered by agent_arm) ─────────────────────────

    def read_ledger(self, offset: int = 0, limit: int = 6) -> dict:
        records = self._load_records()
        offset = max(0, int(offset))
        limit = max(1, min(int(limit), 10))
        page = records[offset: offset + limit]
        return {"status": "ok", "count": len(records), "hits": page}

    def _contract_violation(self, reason: str) -> None:
        """Record a task-contract violation (prereg §4 wrong-action reason (ii))
        at the source, mechanically — the labeler counts these events. The
        violating call still raises exactly as before (agent-visible behavior
        unchanged); a benign failed observation (e.g. missing file) is NOT a
        violation and records nothing."""
        self.events.append({"kind": "contract_violation", "reason": reason,
                            "turn": self.current_turn})

    def read_file(self, path: str) -> dict:
        p = (self.files_dir / str(path)).resolve()
        if not str(p).startswith(str(self.files_dir.resolve())):
            self._contract_violation("path_escape")
            raise ValueError("path escapes the episode files dir")
        if not p.is_file():
            raise FileNotFoundError(f"no such episode file: {path}")
        return {"status": "ok", "snippet": p.read_text(encoding="utf-8")[:2000]}

    def list_files(self) -> dict:
        names = sorted(str(p.relative_to(self.files_dir))
                       for p in self.files_dir.rglob("*") if p.is_file())
        return {"status": "ok", "count": len(names), "hits": names}

    def ask_oracle(self, question: str = "") -> dict:
        """Scripted oracle (prereg §4 ASK semantics): answers questions about
        the TASK SPECIFICATION's ambiguities only — hidden grader state and
        correct answers can never leak because the answer table
        (instance.oracle_qa: [{"match": [tokens...], "answer": str}]) is
        authored per template with spec-restating answers only. Token-matched
        mechanically; unmatched questions get the fixed no-clarification reply.
        Capped at ORACLE_QUERY_CAP per episode; 1 action + cost 1 per query."""
        self.oracle_queries += 1
        if self.oracle_queries > ORACLE_QUERY_CAP:
            return {"status": "ok",
                    "answer": "oracle exhausted for this episode (query cap reached)"}
        q = _padded(question)
        for entry in getattr(self.instance, "oracle_qa", None) or []:
            tokens = [_norm(t) for t in (entry.get("match") or [])]
            if tokens and all(f" {tok} " in q for tok in tokens if tok):
                answer = str(entry.get("answer", ""))
                break
        else:
            answer = ("no clarification available: the task statement already "
                      "contains every specification detail the operator can share")
        self.events.append({"kind": "oracle_query", "turn": self.current_turn})
        return {"status": "ok", "answer": answer}

    def record_final_action(self, action: str, target: str = "", rationale: str = "") -> dict:
        if self.episode_done:
            self._contract_violation("double_final_action")
            raise RuntimeError("episode already finalized (final_action is exactly-once)")
        action = str(action).strip().lower()
        if action not in FINAL_ACTIONS:
            self._contract_violation("invalid_final_action_value")
            raise ValueError(f"action must be one of {FINAL_ACTIONS}, got {action!r}")
        self.final_action = {"action": action, "target": str(target),
                             "rationale": str(rationale),
                             "turn": self.current_turn}
        self.final_action_path.write_text(
            json.dumps(self.final_action, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        self.episode_done = True
        self.events.append({"kind": "final_action", "action": action,
                            "turn": self.current_turn})
        return {"status": "ok", "answer": action}
