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

WP-B2 Stage-1 eval mode (`--eval`, POST-SEAL only):

    python3 scripts/m2_driftbench/run_stage1.py --eval --public-seed auto

  * instances generated from the PUBLIC seed (fixtures.generate_eval_instances
    refuses without the seal receipt); `--public-seed auto` derives the seed as
    int(sha256(<seal combined_sha256>)[:12], 16) — recorded in the generation
    receipt (prereg-A names no seed source, so the derivation is fixed and
    recorded here per the freeze brief).
  * prereg-A runner rules: per-instance ARM-ORDER randomization + instance-
    order randomization (both from the public seed); a fresh isolated env root
    per (instance, arm); caps wall 45min AND 200 actions (first hit ends the
    episode; graded state stands — cap/crash = primary failure, restart
    forbidden); per-arm memory stores (never shared across arms).
  * every dispatched action is followed by a HIDDEN checkpoint probe (grader
    subprocess, orchestrator-side, never agent-visible) written to the
    ANALYZE-CONFORMANT causal trace (trace.CausalTraceWriter) so the frozen
    analyze.py §5 condition-4 causal rule is computable; gate rejections and
    memory-staleness suppressions are the trigger events (env mutations are
    ground truth, never credited as runtime detection).
  * each finished run is labeled mechanically (labelers.py, prereg §4
    taxonomy) and mapped to a FROZEN schema.py ResultRow; rows for the five
    schema arms go to the rows file analyze.py consumes; weak+llm-judge and
    the slm-delta score are instruments -> receipts + instruments side-table
    only. ABSTAIN-AUC (typed_verdict, ground_truth_answerable) pairs are
    emitted per instance into receipts + the auc_pairs file.

Aux modes: `--probes` runs the pre-registered MISSPECIFIED probe set through
the organs gate and reports the >95% gate; `--nim-ping` does the single
1-token strong-raw connectivity check (never logs the key);
`--validate-instances` generates post-seal and dry-validates against the
frozen schema vocab without running any model.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from random import Random

_DIR = Path(__file__).resolve().parent
for _p in (str(_DIR), str(_DIR.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent_arm                                  # noqa: E402
import fixtures                                   # noqa: E402
import freeze as m2_freeze                        # noqa: E402
import labelers                                   # noqa: E402
import probes as m2_probes                        # noqa: E402
import slm_delta                                   # noqa: E402
from env import EpisodeEnv                        # noqa: E402
from memory import MemoryStore                    # noqa: E402
from meter import TokenMeter                      # noqa: E402
from trace import CausalTraceWriter               # noqa: E402

DEFAULT_RECEIPTS_DIR = Path("/home/user/workspaces/jaewon/descentnet/run_artifacts/descentnet")
GRADER_PATH = _DIR / "grader.py"
PREREG = ("descentnet/docs/DESCENTNET_M2_DRIFTBENCH_PREREG_2026-07-10.md "
          "(v1+v1.1+v1.2)")
PREREG_A = "docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md (v1.1, FROZEN; verdict authority)"

# Frozen eval caps (prereg-A §3; token ceiling = the v1.1 §B per-instance hard
# ceiling, frozen here before any run — wall/actions are the binding caps).
EVAL_WALL_CAP_S = 45 * 60
EVAL_ACTIONS_CAP = 200
EVAL_TOKEN_CEILING = 150_000
EVAL_MAX_TURNS = 205          # headroom over the action cap; sampler stops first
EVAL_ARMS_DEFAULT = "weak-raw,weak+checklist,weak+memory,weak+aios,strong-raw"


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


# ── WP-B2 Stage-1 eval path ───────────────────────────────────────────────────

def derive_public_seed(seal_path: Path) -> "tuple[int, str]":
    """The recorded public-seed derivation (prereg-A names no seed source):
    int(sha256(<seal receipt's combined_sha256 string>).hexdigest()[:12], 16)."""
    sealed = json.loads(Path(seal_path).read_text(encoding="utf-8"))
    combined = str(sealed["combined_sha256"])
    seed = int(hashlib.sha256(combined.encode()).hexdigest()[:12], 16)
    formula = "int(sha256(seal.combined_sha256)[:12], 16)"
    return seed, formula


def make_causal_extra_sink(causal: CausalTraceWriter, prober, env):
    """Orchestrator-side consumer for run_loop events: counts ACTIONS
    (trajectory entries — dispatched, denied, gate-rejected), writes trigger
    events, and probes the hidden checkpoints after state can have changed
    (successful dispatches and applied drifts). Nothing here reaches the agent."""
    state = {"step": 0, "drifts_seen": 0}

    def extra(rec: dict) -> None:
        kind = rec.get("kind")
        if kind == "trajectory":
            state["step"] += 1
            status = rec.get("status")
            if status == "gate_rejected":
                reasons = "; ".join(str(r) for r in (rec.get("gate_reasons") or []))
                causal.event(state["step"], "gate_reject", detail=reasons[:200])
            elif status == "ok":
                prober(state["step"])
        elif kind == "turn_context":
            if len(env.applied_drifts) > state["drifts_seen"]:
                state["drifts_seen"] = len(env.applied_drifts)
                prober(state["step"])

    return extra


def run_one_eval_arm(arm: str, instance, *, receipts_dir: Path,
                     env_base: "Path | None", force: bool,
                     memory_store: "MemoryStore | None",
                     adapter=None) -> dict:
    """ONE (instance, arm) Stage-1 run: isolated env root, caps, causal trace +
    hidden checkpoint probing, mechanical labels, frozen ResultRow (schema
    arms) or instrument record (weak+llm-judge), AUC pair, slm-delta column."""
    variant = getattr(instance, "variant", "base")
    tag = f"{instance.template_id}_{_safe(arm)}_s{instance.seed}"
    if variant != "base":
        tag += f"_{variant}"
    receipt_path = receipts_dir / f"m2_stage1_{tag}.json"
    if receipt_path.exists() and not force:
        print(f"[skip] receipt exists (resumable): {receipt_path}")
        return json.loads(receipt_path.read_text(encoding="utf-8"))

    trace_path = receipts_dir / f"m2_trace_stage1_{tag}.jsonl"
    causal_path = receipts_dir / f"m2_causal_stage1_{tag}.jsonl"
    for p in (trace_path, causal_path):
        if p.exists() and force:
            p.unlink()

    env_root = Path(tempfile.mkdtemp(prefix=f"m2eval_{tag}_",
                                     dir=str(env_base) if env_base else None))
    env = EpisodeEnv(instance, env_root)
    spec_dir = receipts_dir / "eval_specs"      # outside env roots AND sealed dirs
    spec_path = fixtures.write_grader_spec(instance, spec_dir)

    causal = CausalTraceWriter(causal_path)

    def prober(step: int) -> None:
        g = run_grader(spec_path, env_root)
        for cp in g.get("checkpoints", []) or []:
            causal.event(step, "checkpoint_result", checkpoint_id=str(cp.get("id")),
                         passed=bool(cp.get("passed")))

    receipt = {
        "schema": "m2.driftbench.stage1_receipt.v1",
        "contract": "ASC-0282", "prereg": PREREG, "prereg_a": PREREG_A,
        "mode": "stage1", "template_id": instance.template_id,
        "seed": instance.seed, "seed_index": instance.seed_index,
        "seed_map_note": "row seed = index of generation seed in (11,12,13) "
                         "(frozen schema.py SEEDS vs sealed generation seeds)",
        "variant": variant, "family": instance.family, "arm": arm,
        "model_pins": {"weak": agent_arm.WEAK_MODEL_EVAL,
                       "strong_primary": agent_arm.STRONG_MODEL_PRIMARY,
                       "strong_fallback": agent_arm.STRONG_MODEL_FALLBACK},
        "caps": {"wall_s": EVAL_WALL_CAP_S, "actions": EVAL_ACTIONS_CAP,
                 "tokens": EVAL_TOKEN_CEILING},
        "env_root": str(env_root), "trace": str(trace_path),
        "causal_trace": str(causal_path), "started": _now(),
    }

    meter = TokenMeter(ceiling=EVAL_TOKEN_CEILING)
    prober(0)                                    # baseline: prior-fail anchors
    t0 = time.monotonic()
    infra_failed = False
    try:
        result = agent_arm.run_episode(
            arm, instance, env, trace_path, meter=meter,
            max_turns=EVAL_MAX_TURNS, memory_store=memory_store,
            eval_mode=True, deadline_s=EVAL_WALL_CAP_S,
            actions_cap=EVAL_ACTIONS_CAP, adapter=adapter,
            extra_sink=make_causal_extra_sink(causal, prober, env))
    except NotImplementedError as exc:
        causal.close()
        receipt.update({"arm_status": "not_implemented", "reason": str(exc),
                        "finished": _now()})
        _write(receipt_path, receipt)
        return receipt
    except RuntimeError as exc:
        # Dead infrastructure: FAIL-CLOSED loudly; per prereg §3 the instance
        # scores as primary failure (crash = failure; restart forbidden).
        infra_failed = True
        result = {"outcome": {"exit": "infra_failed"}, "gate_blocks": [],
                  "memory_injection": {"injected": False, "stale": False}}
        receipt["arm_status"] = "infra_failed"
        receipt["infra_reason"] = str(exc)[:300]
        print(f"[INFRA-FAILED] {tag} {arm}: {str(exc)[:160]}")
    wall = time.monotonic() - t0

    # Memory staleness suppression is a runtime drift-DETECTION trigger
    # (condition-4 vocabulary); write it at step 0 (pre-episode).
    if result.get("memory_injection", {}).get("stale"):
        causal.event(0, "drift_detected", detail="memory_note_stale_suppressed")
    causal.close()

    grader = {} if infra_failed else run_grader(spec_path, env_root)
    if grader.get("grader_infra_failed"):
        receipt["grader_infra"] = grader
        grader = {}

    from trace import load_trace                 # local: sibling helper
    trace_records = load_trace(trace_path) if trace_path.exists() else []
    labels = labelers.label_counts(trace_records, env.events, env.final_action,
                                   grader, env.known_claims(),
                                   raw_claims=env.known_claims(include_superseded=True))

    row_dict, row_errors = None, []
    if arm in labelers.ROW_ARM:
        row, row_errors = labelers.build_result_row(
            instance=instance, arm=arm, grader=grader, labels=labels,
            actions_used=meter.action_count, wall_seconds=wall,
            tokens=meter.total_tokens, causal_trace_path=str(causal_path),
            infra_failed=infra_failed)
        row_dict = row.as_dict()

    receipt.update({
        "arm_status": receipt.get("arm_status", "ok"),
        "outcome": {k: result["outcome"].get(k) for k in
                    ("exit", "turns", "tool_calls", "gate_rejections",
                     "loop_type", "answer")},
        "final_action": env.final_action,
        "gate_blocks": result["gate_blocks"],
        "memory_injection": {k: v for k, v in result.get("memory_injection", {}).items()
                             if k != "prefix"},
        "env_events": env.events,
        "grader": grader,
        "labels": labels,
        "meter": meter.to_dict(),
        "wall_seconds_raw": round(wall, 3),
        "row": row_dict,
        "row_validation_errors": row_errors,
        "answerability_probe": _instance_answerability_probe(instance, env_base),
        "slm_delta": slm_delta.slm_delta_score(env._load_records()),  # noqa: SLF001 — orchestrator-side read of the final ledger
        "finished": _now(),
    })
    _write(receipt_path, receipt)
    print(f"[done] {tag} arm={arm} exit={result['outcome'].get('exit')} "
          f"success={grader.get('success')} tokens={meter.total_tokens} "
          f"row_errors={len(row_errors)}")
    return receipt


def run_stage1_eval(a) -> int:
    seal_path = Path(a.seal) if a.seal else m2_freeze.DEFAULT_SEAL_PATH
    if not seal_path.is_file():
        print(f"Stage-1 eval requires the seal receipt first (freeze.py seal): {seal_path}")
        return 2
    if str(a.public_seed).lower() == "auto":
        public_seed, formula = derive_public_seed(seal_path)
    else:
        public_seed, formula = int(a.public_seed), "explicit --public-seed"
    gen = fixtures.generate_eval_instances(public_seed, seal_path=seal_path)

    receipts_dir = Path(a.receipts_dir)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    arms = [s.strip() for s in a.arms.split(",") if s.strip()]
    for arm in arms:
        if arm not in agent_arm.ARMS or arm == "slm-delta":
            print(f"unknown/non-runnable arm {arm!r}")
            return 2

    variants = {"base": gen["base"], "corrupted": gen["corrupted"],
                "both": gen["base"] + gen["corrupted"]}[a.variant]
    instances = list(variants)
    Random(f"m2order:{public_seed}").shuffle(instances)

    # Per-arm memory stores (prereg §3 isolation: arms never share memory).
    stores = {arm: MemoryStore(arm, receipts_dir / f"m2_memory_{_safe(arm)}.json")
              for arm in arms if arm in ("weak+memory", "weak+aios")}

    generation_receipt = {
        "schema": "m2.eval_generation.v1", "contract": "ASC-0282",
        "public_seed": public_seed, "public_seed_derivation": formula,
        "seal": str(seal_path),
        "seal_combined_sha256": json.loads(seal_path.read_text())["combined_sha256"],
        "seed_map": gen["seed_map"], "drift_type_coverage": gen["drift_type_coverage"],
        "n_base": len(gen["base"]), "n_corrupted": len(gen["corrupted"]),
        "instance_hashes": {
            f"{i.template_id}_s{i.seed}_{i.variant}": hashlib.sha256(
                json.dumps(i.to_dict(), sort_keys=True).encode()).hexdigest()
            for i in gen["base"] + gen["corrupted"]},
        "generated_at": _now(),
    }
    _write(receipts_dir / "m2_eval_generation.json", generation_receipt)

    rows = []
    for inst in instances:
        arm_order = list(arms)
        Random(f"m2order:{public_seed}:{inst.template_id}:{inst.seed_index}:{inst.variant}"
               ).shuffle(arm_order)
        for arm in arm_order:
            receipt = run_one_eval_arm(
                arm, inst, receipts_dir=receipts_dir,
                env_base=Path(a.env_base) if a.env_base else None,
                force=a.force, memory_store=stores.get(arm))
            if receipt.get("row") and inst.variant == "base":
                rows.append(receipt["row"])

    schema = labelers.load_frozen_schema()
    row_objs = [schema.ResultRow.from_dict(r) for r in rows]
    errors = schema.validate_table(row_objs)
    rows_path = receipts_dir / "m2_stage1_rows.jsonl"
    schema.write_table(rows_path, row_objs)
    print(f"[rows] {len(row_objs)} rows -> {rows_path}; validation errors: {len(errors)}")
    for e in errors[:10]:
        print(f"  row-error: {e}")
    return 0 if not errors else 1


def validate_instances(a) -> int:
    """NO-MODEL dry validation (brief VERIFY): the generated instances conform
    to the FROZEN schema.py template vocab / seed indices / counts, the drift
    coverage rule holds, and every mutating drift precedes the earliest
    plausible commit turn."""
    seal_path = Path(a.seal) if a.seal else m2_freeze.DEFAULT_SEAL_PATH
    if str(a.public_seed).lower() == "auto":
        public_seed, formula = derive_public_seed(seal_path)
    else:
        public_seed, formula = int(a.public_seed), "explicit --public-seed"
    gen = fixtures.generate_eval_instances(public_seed, seal_path=seal_path)
    schema = labelers.load_frozen_schema()
    problems = []
    for inst in gen["base"] + gen["corrupted"]:
        if inst.template_id not in schema.ALL_TEMPLATES:
            problems.append(f"{inst.template_id}: not in frozen template vocab")
        if inst.seed_index not in schema.SEEDS:
            problems.append(f"{inst.template_id}/s{inst.seed}: seed_index {inst.seed_index} "
                            f"not in frozen {schema.SEEDS}")
        mutating = schema.is_mutating(inst.template_id)
        if mutating != bool(inst.drift_schedule):
            problems.append(f"{inst.template_id}: mutating/static mismatch")
        if mutating:
            first = min(int(d["turn"]) for d in inst.drift_schedule)
            if first > 2:
                problems.append(f"{inst.template_id}: primary drift at turn {first} > 2 "
                                "(must precede earliest plausible commit)")
            if inst.drift_schedule[0]["drift_type"] != inst.template_id:
                problems.append(f"{inst.template_id}: primary drift type mismatch")
        if inst.variant == "corrupted" and not inst.corrupted_record:
            problems.append(f"{inst.template_id}: corrupted variant without record")
    n_base, n_cor = len(gen["base"]), len(gen["corrupted"])
    report = {
        "public_seed": public_seed, "derivation": formula,
        "n_base": n_base, "n_corrupted": n_cor,
        "expected_base": len(schema.ALL_TEMPLATES) * len(schema.SEEDS),
        "drift_type_coverage": gen["drift_type_coverage"],
        "coverage_rule_ok": all(v >= 2 for v in gen["drift_type_coverage"].values()),
        "problems": problems,
        "ok": not problems and n_base == 24,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(prog="m2 run_stage1")
    ap.add_argument("--dev-smoke", action="store_true",
                    help="run the throwaway dev template (infra validation only)")
    ap.add_argument("--eval", action="store_true",
                    help="Stage-1 eval run (POST-SEAL only; frozen pins + caps)")
    ap.add_argument("--validate-instances", action="store_true",
                    help="NO-MODEL dry validation of generated instances vs frozen schema")
    ap.add_argument("--probes", action="store_true",
                    help="run the pre-registered MISSPECIFIED probe set (>95%% gate)")
    ap.add_argument("--nim-ping", action="store_true",
                    help="single 1-token strong-raw connectivity check (key never logged)")
    ap.add_argument("--arms", default=None,
                    help=f"comma-separated from {agent_arm.ARMS}")
    ap.add_argument("--seed", type=int, default=999)
    ap.add_argument("--public-seed", default="auto",
                    help="eval instance-generation public seed; 'auto' derives from the seal hash")
    ap.add_argument("--seal", default=None,
                    help=f"seal receipt path (default {m2_freeze.DEFAULT_SEAL_PATH})")
    ap.add_argument("--variant", choices=("base", "corrupted", "both"), default="base")
    ap.add_argument("--template", default="dev_mem2act_conflict_v0")
    ap.add_argument("--max-turns", type=int, default=agent_arm.DEV_MAX_TURNS)
    ap.add_argument("--receipts-dir", default=str(DEFAULT_RECEIPTS_DIR))
    ap.add_argument("--env-base", default=None,
                    help="optional base dir for episode env roots (default: system tmp)")
    ap.add_argument("--force", action="store_true", help="re-run over existing receipts")
    a = ap.parse_args(argv)

    if a.probes:
        report = m2_probes.run_probe_gate()
        print(json.dumps(report, indent=2, sort_keys=True))
        _write(Path(a.receipts_dir) / "m2_misspecified_probes.json", report)
        return 0 if report["gate_met"] else 1
    if a.nim_ping:
        result = agent_arm.nim_connectivity_ping()
        if not result.get("ok"):
            fb = agent_arm.nim_connectivity_ping(model=agent_arm.STRONG_MODEL_FALLBACK)
            result = {"primary": result, "fallback": fb, "ok": fb.get("ok")}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    if a.validate_instances:
        return validate_instances(a)
    if a.eval:
        if a.arms is None:
            a.arms = EVAL_ARMS_DEFAULT
        return run_stage1_eval(a)
    if not a.dev_smoke:
        print("pick a mode: --dev-smoke | --eval | --validate-instances | --probes | --nim-ping")
        return 2

    receipts_dir = Path(a.receipts_dir)
    env_base = Path(a.env_base) if a.env_base else None
    arms = [s.strip() for s in (a.arms or "weak-raw,weak+aios").split(",") if s.strip()]
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
