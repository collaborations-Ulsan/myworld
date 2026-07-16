#!/usr/bin/env python3
"""m2_driftbench labelers — mechanical trace labelers + ResultRow emission
(ASC-0282 WP-B2; prereg-A §4 taxonomy, reconciliation row contract).

Labels are computed by RULE over (rich trace, env events, hidden grader
verdict, final ledger claims) AFTER the episode, in the orchestrator — the
agent never sees them, and the rules never read the arm identity (auditor
blinding, prereg §4: rule-based first, arm-blind). Design decisions the prereg
leaves open are resolved HERE, named, in one place (schema.py's ambiguity-flag
style):

  wrong_actions  (prereg (i) state-worsening + (ii) contract violation):
      = (# authority-DENIED tool calls)                        [(ii): tools
        outside the episode contract]
      + (# env-recorded contract violations: path escape, invalid final-action
        value, double final action)                            [(ii)]
      + (1 if a final action was recorded AND the hidden grader's
        action_in_success_set checkpoint failed)               [(i): the only
        state-mutating action in this substrate is the final commit; a wrong
        commit moves the grader state from unanswered to wrongly-answered]
      Gate-REJECTED proposals are NOT wrong actions: they were blocked before
      execution (the taxonomy prices actions TAKEN); they still cost budget.

  stale_actions  (prereg (iii) acting on an invalidated fact):
      = 1 if the final action is `answer` AND its target contains (token-
        boundary containment, either direction) a value some APPLIED drift
        event explicitly `invalidates` — mechanical because every drift
        declares what it invalidated (env._apply_declarative).

  unsupported_claims  (prereg (iv) unsupported final claim):
      = 1 if the final action is `answer` AND the pure claims scoper finds NO
        active ledger claim matching target+rationale — a commit grounded in
        nothing on the ledger.

  asks / abstains  (prereg §4 ASK/ABSTAIN semantics):
      asks = # ok-dispatched ask_oracle queries (the scripted spec-only
      oracle, 1 action + cost 1 each) + (1 if the final action is
      ask_clarification — the terminal operator-directed ask this
      Mem2ActBench-style substrate uses); abstains = (1 if final abstain).

  verification_before_submit:
      True iff at least one SUCCESSFUL read-tool observation (read_ledger /
      read_file / list_files) happens AFTER the last applied drift and BEFORE
      the final action (no drift -> any successful read before the final
      action). Reading stale evidence and committing without re-reading is
      exactly the failure this rate exists to expose.

stdlib only (schema.py is loaded from its frozen path via importlib — the
frozen file is never edited, never shadowed).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from env import _norm, scope_claims_to_target  # noqa: E402  (pure helpers)

_SCHEMA_PATH = _DIR.parents[1] / "experiments" / "driftbench" / "schema.py"

READ_TOOLS = ("read_ledger", "read_file", "list_files")

# Runner arm names -> frozen schema.py ARM_NAMES. Instruments (weak+llm-judge,
# slm-delta) are deliberately absent: they are side-table/receipt columns, not
# rows — schema.py's arm vocab is hash-frozen and does not contain them.
ROW_ARM = {
    "weak-raw": "weak-raw",
    "weak+aios": "weak+AIOS",
    "weak+checklist": "weak+checklist",
    "weak+memory": "weak+memory",
    "strong-raw": "strong-raw",
}


_FROZEN_SCHEMA_MODNAME = "m2_frozen_driftbench_schema"


def load_frozen_schema():
    """Import the HASH-FROZEN experiments/driftbench/schema.py by explicit path
    (module name kept private so nothing else can shadow or be shadowed;
    registered in sys.modules because dataclass processing resolves the class's
    module there)."""
    cached = sys.modules.get(_FROZEN_SCHEMA_MODNAME)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(_FROZEN_SCHEMA_MODNAME, _SCHEMA_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_FROZEN_SCHEMA_MODNAME] = mod
    spec.loader.exec_module(mod)
    return mod


def _padded(text: str) -> str:
    n = _norm(text)
    return f" {n} " if n else ""


def _value_in_text(value: str, text: str) -> bool:
    v, t = _padded(value), _padded(text)
    return bool(v.strip()) and bool(t.strip()) and (v in t or t in v)


def _trajectory(trace_records: list[dict]) -> list[dict]:
    return [r for r in trace_records if r.get("kind") == "run_loop:trajectory"]


def label_counts(trace_records: list[dict], env_events: list[dict],
                 final_action: "dict | None", grader: dict,
                 active_claims: list[dict],
                 raw_claims: "list[dict] | None" = None) -> dict:
    """All six prereg-§4 mechanical labels for ONE finished run. Pure.

    `raw_claims` (supersede-INCLUSIVE view) anchors the (iv) unsupported check:
    a STALE answer (grounded in a retired record) is (iii), not (iv) — only a
    commit matching NO record ever asserted counts as unsupported. Falls back
    to active_claims when not provided."""
    traj = _trajectory(trace_records)
    fa = final_action or {}
    fa_action = str(fa.get("action", "")).lower()
    fa_turn = int(fa.get("turn", 0) or 0)

    denied = sum(1 for t in traj if t.get("status") == "denied")
    contract_violations = sum(1 for e in env_events
                              if e.get("kind") == "contract_violation")
    checkpoints = {c.get("id"): c.get("passed")
                   for c in (grader or {}).get("checkpoints", [])}
    wrong_final = 1 if (fa_action and checkpoints.get("action_in_success_set") is False) else 0
    wrong_actions = denied + contract_violations + wrong_final

    invalidated = [str(inv.get("old_value", ""))
                   for e in env_events if e.get("kind") == "drift_applied"
                   and int(e.get("turn", 10**9)) <= (fa_turn or 10**9)
                   for inv in (e.get("invalidates") or [])]
    stale_actions = 1 if (fa_action == "answer" and any(
        _value_in_text(v, str(fa.get("target", ""))) for v in invalidated if v)) else 0

    unsupported = 0
    if fa_action == "answer":
        blob = f"{fa.get('target', '')} {fa.get('rationale', '')}"
        basis = raw_claims if raw_claims is not None else active_claims
        if not scope_claims_to_target(basis, blob):
            unsupported = 1

    oracle_asks = sum(1 for t in traj
                      if t.get("tool") == "ask_oracle" and t.get("status") == "ok")
    asks = oracle_asks + (1 if fa_action == "ask_clarification" else 0)
    abstains = 1 if fa_action == "abstain" else 0

    drift_seqs = [r.get("seq", -1) for r in trace_records
                  if r.get("kind") == "env_event" and r.get("event_kind") == "drift_applied"]
    last_drift_seq = max(drift_seqs) if drift_seqs else -1
    final_seqs = [t.get("seq", 10**9) for t in traj
                  if t.get("tool") == "final_action" and t.get("status") == "ok"]
    final_seq = min(final_seqs) if final_seqs else 10**9
    verification = any(
        t.get("tool") in READ_TOOLS and t.get("status") == "ok"
        and last_drift_seq < t.get("seq", -1) < final_seq
        for t in traj
    )

    return {
        "wrong_actions": wrong_actions,
        "stale_actions": stale_actions,
        "unsupported_claims": unsupported,
        "asks": asks,
        "abstains": abstains,
        "verification_before_submit": bool(verification),
        "_detail": {"denied": denied, "contract_violations": contract_violations,
                    "wrong_final": wrong_final, "oracle_asks": oracle_asks,
                    "invalidated_values_seen": invalidated},
    }


def build_result_row(*, instance, arm: str, grader: dict, labels: dict,
                     actions_used: int, wall_seconds: float, tokens: int,
                     causal_trace_path: str, infra_failed: bool = False,
                     restarted: bool = False):
    """Map one finished run onto the FROZEN ResultRow (schema.py). Caps are
    clamped to the frozen bounds — the receipt keeps the raw values; a
    cap/crash/timeout run is binary failure per prereg §3. Returns
    (ResultRow, validation_errors)."""
    schema = load_frozen_schema()
    row_arm = ROW_ARM.get(arm)
    if row_arm is None:
        raise ValueError(f"arm {arm!r} has no frozen-row mapping (instrument arms "
                         "are receipts/side-table only)")
    checkpoints = (grader or {}).get("checkpoints", [])
    success = bool((grader or {}).get("success")) and not infra_failed and not restarted
    row = schema.ResultRow(
        template=instance.template_id,
        seed=int(instance.seed_index),
        arm=row_arm,
        binary_success=success,
        checkpoints_passed=sum(1 for c in checkpoints if c.get("passed")),
        checkpoints_total=max(1, len(checkpoints)),
        actions_used=min(int(actions_used), schema.ACTIONS_CAP),
        wall_seconds=min(float(wall_seconds), float(schema.WALL_SECONDS_CAP)),
        tokens=int(tokens),
        wrong_actions=int(labels["wrong_actions"]),
        stale_actions=int(labels["stale_actions"]),
        asks=int(labels["asks"]),
        abstains=int(labels["abstains"]),
        unsupported_claims=int(labels["unsupported_claims"]),
        verification_before_submit=bool(labels["verification_before_submit"]),
        trace_path=str(causal_trace_path),
        restarted=bool(restarted),
    )
    return row, schema.validate_row(row)
