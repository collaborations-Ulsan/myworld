#!/usr/bin/env python3
"""m2_driftbench run_stage1 — orchestrator (ASC-0282 WP-B).

Dev-smoke milestone (README §"Dev-smoke milestone"):

    python3 scripts/m2_driftbench/run_stage1.py --dev-smoke \
        --arms weak-raw,weak+aios --seed 999

Runs each requested arm end-to-end on ONE throwaway dev template: fixture ->
isolated env root -> frozen agent under aios_turn_loop.run_loop (weak+aios
adds the organs epistemic gate) -> hidden grader in a SEPARATE process ->
token meter -> JSONL trace -> receipt.

Receipts (O16 logging contract): JSON to
descentnet/run_artifacts/descentnet/ with the m2_ prefix; traces land next to
them (m2_trace_*.jsonl). Resumable: an existing receipt for the same
(mode, template, arm, seed) is skipped unless --force.

Smoke = infrastructure validation ONLY; smoke results are not tuning data,
and re-rolling seeds after smoke is a protocol violation (contract §5).
An arm whose infrastructure is dead FAIL-CLOSES loudly: the receipt records
arm_status="infra_failed" and the run moves on — it never silently degrades
into another arm.

Stage-1 eval mode is freeze-packet work: invoking without --dev-smoke exits
with the named reason.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_DIR = Path(__file__).resolve().parent
for _p in (str(_DIR), str(_DIR.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent_arm                                  # noqa: E402
import fixtures                                   # noqa: E402
from env import EpisodeEnv                        # noqa: E402
from meter import TokenMeter                      # noqa: E402

DEFAULT_RECEIPTS_DIR = Path("/home/user/workspaces/jaewon/descentnet/run_artifacts/descentnet")
GRADER_PATH = _DIR / "grader.py"
PREREG = ("descentnet/docs/DESCENTNET_M2_DRIFTBENCH_PREREG_2026-07-10.md "
          "(v1+v1.1+v1.2)")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _safe(name: str) -> str:
    return name.replace("+", "_plus_").replace("/", "_")


def run_grader(spec_path: Path, env_root: Path) -> dict:
    """Invoke the hidden grader as a SEPARATE process (README isolation rule);
    stdout is captured by this orchestrator and never shown to the agent."""
    proc = subprocess.run(
        [sys.executable, str(GRADER_PATH), "--spec", str(spec_path),
         "--env-root", str(env_root)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if proc.returncode != 0:
        return {"grader_infra_failed": True, "returncode": proc.returncode,
                "stderr": (proc.stderr or "")[:300]}
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return {"grader_infra_failed": True, "returncode": 0,
                "note": "non-JSON grader stdout", "stdout": proc.stdout[:300]}


def run_one_arm(arm: str, instance, *, receipts_dir: Path, env_base: "Path | None",
                max_turns: int, force: bool, mode: str) -> dict:
    receipt_path = receipts_dir / (
        f"m2_{mode}_{instance.template_id}_{_safe(arm)}_s{instance.seed}.json")
    if receipt_path.exists() and not force:
        print(f"[skip] receipt exists (resumable): {receipt_path}")
        return json.loads(receipt_path.read_text(encoding="utf-8"))

    trace_path = receipts_dir / (
        f"m2_trace_{mode}_{instance.template_id}_{_safe(arm)}_s{instance.seed}.jsonl")
    if trace_path.exists() and force:
        trace_path.unlink()

    env_root = Path(tempfile.mkdtemp(
        prefix=f"m2env_{instance.template_id}_{_safe(arm)}_s{instance.seed}_",
        dir=str(env_base) if env_base else None))
    env = EpisodeEnv(instance, env_root)
    spec_path = fixtures.write_grader_spec(instance)   # OUTSIDE the env root

    receipt = {
        "schema": "m2.driftbench.devsmoke_receipt.v1",
        "contract": "ASC-0282", "prereg": PREREG, "mode": mode,
        "template_id": instance.template_id, "seed": instance.seed,
        "family": instance.family, "arm": arm,
        "model": agent_arm.WEAK_MODEL_DEV,
        "temperature": {"requested": 0, "pinned": False,
                        "reason": agent_arm.TEMPERATURE_NOTE},
        "max_turns": max_turns,
        "env_root": str(env_root), "trace": str(trace_path),
        "started": _now(),
    }

    meter = TokenMeter()
    try:
        result = agent_arm.run_episode(arm, instance, env, trace_path,
                                       meter=meter, max_turns=max_turns)
    except NotImplementedError as exc:
        receipt.update({"arm_status": "not_implemented", "reason": str(exc),
                        "finished": _now()})
        _write(receipt_path, receipt)
        print(f"[stub] {arm}: {exc}")
        return receipt
    except RuntimeError as exc:
        # Dead infrastructure (e.g. ollama unreachable): FAIL-CLOSED, loudly.
        receipt.update({"arm_status": "infra_failed", "reason": str(exc)[:300],
                        "meter": meter.to_dict(), "finished": _now()})
        _write(receipt_path, receipt)
        print(f"[INFRA-FAILED] {arm}: {str(exc)[:200]}")
        return receipt

    outcome = result["outcome"]
    grader = run_grader(spec_path, env_root)
    receipt.update({
        "arm_status": "ok",
        "outcome": {k: outcome.get(k) for k in
                    ("exit", "turns", "tool_calls", "gate_rejections",
                     "loop_type", "answer")},
        "final_action": env.final_action,
        "gate_blocks": result["gate_blocks"],
        "env_events": env.events,
        "grader": grader,
        "meter": meter.to_dict(),
        "finished": _now(),
    })
    _write(receipt_path, receipt)

    g = grader.get("success")
    print(f"[done] arm={arm} exit={outcome.get('exit')} "
          f"final_action={(env.final_action or {}).get('action')} "
          f"grader_success={g} tokens={meter.total_tokens}(est) "
          f"gate_blocks={len(result['gate_blocks'])}")
    print(f"       receipt: {receipt_path}")
    print(f"       trace:   {trace_path}")
    return receipt


def _write(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2,
                               default=str) + "\n", encoding="utf-8")


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(prog="m2 run_stage1")
    ap.add_argument("--dev-smoke", action="store_true",
                    help="run the throwaway dev template (infra validation only)")
    ap.add_argument("--arms", default="weak-raw,weak+aios",
                    help=f"comma-separated from {agent_arm.ARMS}")
    ap.add_argument("--seed", type=int, default=999)
    ap.add_argument("--template", default="dev_mem2act_conflict_v0")
    ap.add_argument("--max-turns", type=int, default=agent_arm.DEV_MAX_TURNS)
    ap.add_argument("--receipts-dir", default=str(DEFAULT_RECEIPTS_DIR))
    ap.add_argument("--env-base", default=None,
                    help="optional base dir for episode env roots (default: system tmp)")
    ap.add_argument("--force", action="store_true", help="re-run over existing receipts")
    a = ap.parse_args(argv)

    if not a.dev_smoke:
        print("Stage-1 eval runs require the FROZEN harness (fixtures.py eval "
              "templates + freeze.py seal, seeds {11,12,13}) — freeze-packet work. "
              "This packet only supports --dev-smoke (ASC-0282 §7 WP-B).")
        return 2

    receipts_dir = Path(a.receipts_dir)
    env_base = Path(a.env_base) if a.env_base else None
    arms = [s.strip() for s in a.arms.split(",") if s.strip()]
    for arm in arms:
        if arm not in agent_arm.ARMS:
            print(f"unknown arm {arm!r}; arms = {agent_arm.ARMS}")
            return 2

    instance = fixtures.make_dev_instance(a.seed, a.template)
    print(f"[dev-smoke] template={instance.template_id} seed={a.seed} "
          f"records={len(instance.records)} drift={instance.drift_schedule} "
          f"arms={arms}")

    for arm in arms:
        run_one_arm(arm, instance, receipts_dir=receipts_dir, env_base=env_base,
                    max_turns=a.max_turns, force=a.force, mode="devsmoke")
    return 0


if __name__ == "__main__":
    sys.exit(main())
