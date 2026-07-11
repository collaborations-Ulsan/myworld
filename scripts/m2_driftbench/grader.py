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

    # Binary success (dev template rule): a recorded final action whose action
    # is in the hidden success set. target naming is a partial checkpoint.
    success = bool(recorded and action_correct)

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
