#!/usr/bin/env python3
"""m2_driftbench grader — hidden functional grader, SEPARATE process (ASC-0282 WP-B).

Isolation contract (README + prereg v1.1 §D):
  * invoked ONLY after the episode ends, by the orchestrator, as
        python3 grader.py --spec <grader_specs/...json> --env-root <root>
    so no stdout/stderr/timing side-channel can reach the agent loop;
  * the spec lives under scripts/m2_driftbench/grader_specs/, OUTSIDE every
    agent-visible env root; this module imports NO harness sibling (fully
    self-contained stdlib) so grading shares no state with the loop;
  * output: one JSON object on stdout — binary `success` + a partial
    `checkpoints` list — captured by the orchestrator, never shown to the agent.

Exit codes: 0 = graded (success true OR false — a failing episode is a
verdict, not a process error); 2 = grader infra error (bad args / unreadable
spec), which the orchestrator must record as grading infrastructure failure,
never as an episode result.

Hash-sealed at freeze (freeze.py covers this file + grader_specs/).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def grade(spec: dict, env_root: Path) -> dict:
    """Pure verdict over the env FINAL STATE (final_action.json) and the spec."""
    checkpoints: list[dict] = []

    fa_path = env_root / "final_action.json"
    final_action = None
    if fa_path.is_file():
        try:
            final_action = json.loads(fa_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            final_action = None
    recorded = isinstance(final_action, dict) and bool(final_action.get("action"))
    checkpoints.append({"id": "final_action_recorded", "passed": recorded})

    action = str((final_action or {}).get("action", "")).strip().lower()
    action_correct = recorded and action in [a.lower() for a in spec.get("success_actions", [])]
    checkpoints.append({"id": "action_in_success_set", "passed": action_correct,
                        "observed_action": action or None})

    blob = " ".join(str((final_action or {}).get(k, ""))
                    for k in ("target", "rationale")).lower()
    tokens = [str(t).lower() for t in spec.get("target_must_mention_any", [])]
    target_ok = recorded and any(tok in blob for tok in tokens) if tokens else recorded
    checkpoints.append({"id": "target_names_disputed_fact", "passed": bool(target_ok)})

    # WP-B2 additive race guard (WP-B lesson: drift precedes the earliest
    # plausible commit): when the spec pins min_commit_turn > 0, a commit
    # stamped BEFORE that turn can never score — a blind turn-1 commit must
    # not luck into a win over drift it never saw. Dev specs lack the field
    # (default 0) -> behavior unchanged.
    min_turn = int(spec.get("min_commit_turn", 0) or 0)
    commit_turn = int((final_action or {}).get("turn", 0) or 0)
    turn_ok = (min_turn <= 0) or (recorded and commit_turn >= min_turn)
    if min_turn > 0:
        checkpoints.append({"id": "commit_after_drift", "passed": bool(turn_ok),
                            "observed_turn": commit_turn or None})

    # WP-B2 additive: eval specs (m2.grader_spec.v2) also require the target
    # mention — a bare correct ACTION with a target naming nothing about the
    # disputed fact/value is not a functional success. Dev specs (v1) keep the
    # WP-B rule (target naming stays a partial checkpoint only).
    v2 = str(spec.get("schema", "")).endswith(".v2")
    success = bool(recorded and action_correct and turn_ok and (target_ok or not v2))

    return {
        "schema": "m2.grader.v1",
        "template_id": spec.get("template_id"),
        "seed": spec.get("seed"),
        "success": success,
        "checkpoints": checkpoints,
    }


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(prog="m2 grader (hidden; separate process)")
    ap.add_argument("--spec", required=True, help="hidden grader spec JSON path")
    ap.add_argument("--env-root", required=True, help="episode env root (final state)")
    a = ap.parse_args(argv)

    try:
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "m2.grader.v1", "error": f"spec unreadable: {exc}"}))
        return 2
    env_root = Path(a.env_root)
    if not env_root.is_dir():
        print(json.dumps({"schema": "m2.grader.v1", "error": "env root missing"}))
        return 2

    print(json.dumps(grade(spec, env_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
