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

Drift: `apply_drift_for_turn(turn)` applies scheduled mutations when the
episode reaches their declared turn index (wired to run_loop's `turn_context`
event by agent_arm). schema_change rewrites fact records from the v1 shape
{"fact": {"key","value"}} to the v2 shape {"fact_key","fact_value"};
`known_claims()` reads both shapes mechanically, so claim identity survives
the schema drift (the drift stresses the AGENT's reading of the ledger, not
the harness bookkeeping).

stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path

FINAL_ACTIONS = ("answer", "quarantine", "requery_provenance", "ask_clarification", "abstain")

_V2_SCHEMA = "aios.akashic_draft.v2"


def _extract_fact(record: dict) -> "tuple[str, str] | None":
    """Schema-tolerant mechanical fact extraction (v1 nested / v2 flat)."""
    fact = record.get("fact")
    if isinstance(fact, dict) and "key" in fact:
        return str(fact["key"]), str(fact.get("value"))
    if "fact_key" in record:
        return str(record["fact_key"]), str(record.get("fact_value"))
    return None


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
        self._build()

    # ── materialization ──────────────────────────────────────────────────────

    def _build(self) -> None:
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._write_records(self.instance.records)
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

    def known_claims(self) -> list[dict]:
        """Ledger records -> Claim dicts (contracts.py:Claim shape)."""
        claims = []
        for rec in self._load_records():
            fact = _extract_fact(rec)
            if fact is None:
                continue
            key, value = fact
            claims.append({
                "task_id": f"fact::{key}",
                "source_id": str(rec.get("source_id", "unknown")),
                "kind": "io",
                "payload": {"input": [key], "output": value},
                "ts": int(rec.get("ts", 0)),
            })
        return claims

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
        Returns the events applied now (also appended to self.events)."""
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

    def _drift_schema_change(self, params: dict) -> dict:
        """v1 nested fact -> v2 flat fact_key/fact_value; idempotent."""
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
        return {"records_changed": changed, "to_schema": to_schema}

    # ── agent-facing tools (registered by agent_arm) ─────────────────────────

    def read_ledger(self, offset: int = 0, limit: int = 6) -> dict:
        records = self._load_records()
        offset = max(0, int(offset))
        limit = max(1, min(int(limit), 10))
        page = records[offset: offset + limit]
        return {"status": "ok", "count": len(records), "hits": page}

    def read_file(self, path: str) -> dict:
        p = (self.files_dir / str(path)).resolve()
        if not str(p).startswith(str(self.files_dir.resolve())):
            raise ValueError("path escapes the episode files dir")
        if not p.is_file():
            raise FileNotFoundError(f"no such episode file: {path}")
        return {"status": "ok", "snippet": p.read_text(encoding="utf-8")[:2000]}

    def list_files(self) -> dict:
        names = sorted(str(p.relative_to(self.files_dir))
                       for p in self.files_dir.rglob("*") if p.is_file())
        return {"status": "ok", "count": len(names), "hits": names}

    def record_final_action(self, action: str, target: str = "", rationale: str = "") -> dict:
        if self.episode_done:
            raise RuntimeError("episode already finalized (final_action is exactly-once)")
        action = str(action).strip().lower()
        if action not in FINAL_ACTIONS:
            raise ValueError(f"action must be one of {FINAL_ACTIONS}, got {action!r}")
        self.final_action = {"action": action, "target": str(target),
                             "rationale": str(rationale)}
        self.final_action_path.write_text(
            json.dumps(self.final_action, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        self.episode_done = True
        self.events.append({"kind": "final_action", "action": action})
        return {"status": "ok", "answer": action}
