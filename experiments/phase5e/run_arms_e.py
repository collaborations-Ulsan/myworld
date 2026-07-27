#!/usr/bin/env python3
"""Channel-E arms driver (prereg §3–§4 + Errata).

FROZEN PROTOCOL: docs/AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md.

N = 32 paired tasks (Errata N-correction: the full non-holdout pool), epochs
E1..E4 of 8, chronological order identical in both arms. Student FROZEN
``qwen3-coder-next`` (carried from the Phase-5 §4 selection; same task pool,
same oracle). Escalation structurally OFF (turn_loop has no escalation path).

Arms (§3): control — K-turn loop, whole-repo surface, registry structurally
wiped. treatment — same loop + verified sub-routine dispatch (persistent
registry, opaque primitives) + stack-trace AST-closure masking.

RUN-VALIDITY GATE (§3): the run is VOID — a harness failure, not a null —
unless (dispatch was invoked ≥1 time across the run) OR (the closure differed
from the whole repo on ≥1 treatment task). Additionally any episode with an
actual oracle leak-through (Errata op-1) VOIDS that task (reported, excluded).

RESUMABLE per (arm, task_id): incremental JSONL, flush+fsync; finished cells
skipped on re-invocation; infra-errored cells are NOT silently retried
(re-measurement is a logged operator decision). Graceful stop: touch
experiments/phase5e/CHANNEL_E_STOP.

KILL RULE (§4, evaluated in the report): C_overall ≤ 0, OR the one-sided 95%
bound excludes a ≥5 pp advantage, OR (mechanism fired AND discordance ≲5%)
=> Channel E falsified, and with it (Mortuary Clause) the "compound in the
OS" thesis. The report computes each condition; the verdict is written by the
operator into the prereg Errata, never auto-committed by this script.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "phase5"))
from turn_loop import run_episode, K_TURNS  # noqa: E402

REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import aios_sandbox  # noqa: E402

SCHEMA = "aios.phase5e.run.v1"
TASKS_JSON = HERE.parent / "phase5" / "tasks.json"
HOLDOUT_JSON = HERE.parent / "phase5" / "calibration_holdout.json"
RESULTS_JSONL = HERE / "channel_e_results.jsonl"
STATE_DIR = HERE / "channel_e_state"
REPORT_MD = HERE / "CHANNEL_E_RESULTS.md"
STOP_FILE = HERE / "CHANNEL_E_STOP"
PREREG = "docs/AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md"

MODEL = "qwen3-coder-next"  # frozen (carried from Phase-5 §4 selection)
N_TASKS = 32                # Errata N-correction (full non-holdout pool)
N_EPOCHS = 4
PER_EPOCH = N_TASKS // N_EPOCHS
ARMS = ("control", "treatment")

Z_ALPHA_1SIDED_05 = 1.6449
Z_POWER_80 = 0.8416


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _git_head() -> str:
    try:
        r = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------------------------------------------------------------------
# Task selection — full non-holdout pool, chronological (Errata N-correction)
# ---------------------------------------------------------------------------

def main_tasks(tasks_file: Path = TASKS_JSON,
               holdout_file: Path = HOLDOUT_JSON,
               n: int = N_TASKS) -> list[dict]:
    doc = json.loads(tasks_file.read_text(encoding="utf-8"))
    holdout = set(json.loads(holdout_file.read_text(
        encoding="utf-8"))["task_ids"])
    tasks = sorted(doc["tasks"], key=lambda t: (t["ts_epoch"], t["task_id"]))
    kept = [t for t in tasks if t["task_id"] not in holdout]
    if len(kept) != n:
        raise SystemExit(f"non-holdout pool must be exactly {n}, "
                         f"have {len(kept)}")
    for i, t in enumerate(kept):
        t["seq"] = i
        t["epoch"] = i // PER_EPOCH + 1
    return kept


# ---------------------------------------------------------------------------
# Incremental results
# ---------------------------------------------------------------------------

def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def attempts_of(records: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["arm"], r["task_id"]): r for r in records
            if r.get("kind") == "attempt"}


def append_line(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def check_treatment_state(state_dir: Path, records: list[dict]) -> None:
    """Fresh start: state dir EMPTY (pre-seeding guard). Resume: the registry
    may only hold skills from recorded passing treatment attempts."""
    done_treat = [r for r in records if r.get("kind") == "attempt"
                  and r["arm"] == "treatment" and not r.get("infra_error")]
    if not done_treat:
        if state_dir.exists() and any(state_dir.rglob("*")):
            raise SystemExit(
                f"PRE-SEEDING GUARD: treatment state dir {state_dir} is not "
                "empty but no treatment attempt is recorded. The registry may "
                "contain only artifacts produced during THIS run — remove the "
                "dir or point --state-dir elsewhere.")
        return
    reg = state_dir / "skills" / "registry.jsonl"
    n_reg = (len([ln for ln in reg.read_text(encoding="utf-8").splitlines()
                  if ln.strip()]) if reg.exists() else 0)
    n_recorded = sum(1 for r in done_treat
                     if (r.get("skill") or {}).get("registered"))
    if n_reg != n_recorded:
        raise SystemExit(
            f"STATE/RESULTS MISMATCH: registry holds {n_reg} skills but "
            f"records show {n_recorded} registered. Resuming would run the "
            "wrong substrate — refusing.")


# ---------------------------------------------------------------------------
# Analysis (§4) — real numbers only
# ---------------------------------------------------------------------------

def mcnemar_one_sided(b: int, c: int) -> float | None:
    n = b + c
    if n == 0:
        return None
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def paired_upper_bound(b: int, c: int, n: int,
                       z: float = Z_ALPHA_1SIDED_05) -> float | None:
    """One-sided 95% upper bound on delta = (b-c)/n (Wald, paired)."""
    if n == 0:
        return None
    delta = (b - c) / n
    se = math.sqrt(max((b + c) / n - delta * delta, 0.0) / n)
    return delta + z * se


def power_at(delta: float, p_disc: float, n: int,
             z_a: float = Z_ALPHA_1SIDED_05) -> float | None:
    """Power to detect `delta` at one-sided alpha with n pairs (Connor 1987
    normal approximation), given discordant rate p_disc."""
    if p_disc <= 0 or delta > p_disc:
        return None
    num = delta * math.sqrt(n) - z_a * math.sqrt(p_disc)
    den = math.sqrt(max(p_disc - delta * delta, 1e-12))
    return round(_phi(num / den), 4)


def validity_gate(atts: dict[tuple[str, str], dict],
                  tasks: list[dict]) -> dict:
    """§3(E): VOID unless dispatch fired ≥1 time OR closure differed from the
    whole repo on ≥1 treatment task. Oracle leak-throughs void that task."""
    disp = sum((atts.get(("treatment", t["task_id"])) or {})
               .get("dispatch_invocations") or 0 for t in tasks)
    masked = [t["task_id"] for t in tasks
              if ((atts.get(("treatment", t["task_id"])) or {})
                  .get("closure") or {}).get("differs_from_whole_repo")]
    leaks = [{"arm": a, "task_id": tid} for (a, tid), r in sorted(atts.items())
             if r.get("oracle_leak")]
    return {"passed": bool(disp or masked),
            "dispatch_invocations_total": disp,
            "tasks_with_nontrivial_closure": len(masked),
            "oracle_leak_voided": leaks}


def analyze(atts: dict[tuple[str, str], dict], tasks: list[dict]) -> dict:
    pairs, dropped_infra, voided = [], [], []
    for t in tasks:
        c = atts.get(("control", t["task_id"]))
        tr = atts.get(("treatment", t["task_id"]))
        if c is None or tr is None:
            continue
        if c.get("oracle_leak") or tr.get("oracle_leak"):
            voided.append(t["task_id"])
            continue
        if c.get("infra_error") or tr.get("infra_error"):
            dropped_infra.append({
                "task_id": t["task_id"], "epoch": t["epoch"],
                "control_infra": c.get("infra_error"),
                "treatment_infra": tr.get("infra_error")})
            continue
        pairs.append({"task_id": t["task_id"], "epoch": t["epoch"],
                      "control": bool(c["passed"]),
                      "treatment": bool(tr["passed"]),
                      "c_turns": c.get("turns_used"),
                      "t_turns": tr.get("turns_used")})

    b = sum(1 for p in pairs if p["treatment"] and not p["control"])
    c_ = sum(1 for p in pairs if p["control"] and not p["treatment"])
    n_pairs = len(pairs)
    p_c = (sum(p["control"] for p in pairs) / n_pairs) if n_pairs else None
    p_t = (sum(p["treatment"] for p in pairs) / n_pairs) if n_pairs else None

    epochs = []
    for k in range(1, N_EPOCHS + 1):
        ep = [p for p in pairs if p["epoch"] == k]
        if ep:
            pc = sum(p["control"] for p in ep) / len(ep)
            pt = sum(p["treatment"] for p in ep) / len(ep)
            epochs.append({"epoch": k, "n_pairs": len(ep),
                           "P_auto_control": round(pc, 4),
                           "P_auto_treatment": round(pt, 4),
                           "C_k": round(pt - pc, 4)})
        else:
            epochs.append({"epoch": k, "n_pairs": 0, "P_auto_control": None,
                           "P_auto_treatment": None, "C_k": None})

    pts = [(e["epoch"], e["C_k"]) for e in epochs if e["C_k"] is not None]
    slope = None
    if len(pts) >= 2:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        den = sum((x - mx) ** 2 for x in xs)
        slope = round(sum((x - mx) * (y - my)
                          for x, y in zip(xs, ys)) / den, 4) if den else None

    # secondary (pre-registered §4): turn compression among solved
    turns_solved_c = [p["c_turns"] for p in pairs if p["control"]]
    turns_solved_t = [p["t_turns"] for p in pairs if p["treatment"]]
    disc_rate = (b + c_) / n_pairs if n_pairs else None
    delta = (b - c_) / n_pairs if n_pairs else None
    upper = paired_upper_bound(b, c_, n_pairs) if n_pairs else None

    kill = None
    if n_pairs:
        kill = {
            "C_overall_le_0": (p_t - p_c) <= 0,
            "upper95_excludes_5pp": (upper is not None and upper < 0.05),
            "discordance_lesssim_5pct": (disc_rate is not None
                                         and disc_rate <= 0.05),
            "upper95_one_sided": (round(upper, 4)
                                  if upper is not None else None),
        }

    return {"n_pairs": n_pairs, "dropped_infra": dropped_infra,
            "voided_oracle_leak": voided,
            "P_auto_control": round(p_c, 4) if p_c is not None else None,
            "P_auto_treatment": round(p_t, 4) if p_t is not None else None,
            "C_overall": (round(p_t - p_c, 4)
                          if p_c is not None and p_t is not None else None),
            "discordant_b_treatment_only": b,
            "discordant_c_control_only": c_,
            "discordant_rate": (round(disc_rate, 4)
                                if disc_rate is not None else None),
            "mcnemar_one_sided_p": (round(mcnemar_one_sided(b, c_), 4)
                                    if b + c_ else None),
            "per_epoch": epochs, "C_k_slope": slope,
            "power_for_15pp_at_observed_disc": (
                power_at(0.15, max(disc_rate or 0.0, 0.15), n_pairs)
                if n_pairs else None),
            "turns_among_solved": {
                "control_mean": (round(sum(turns_solved_c)
                                       / len(turns_solved_c), 2)
                                 if turns_solved_c else None),
                "treatment_mean": (round(sum(turns_solved_t)
                                         / len(turns_solved_t), 2)
                                   if turns_solved_t else None)},
            "kill_rule": kill}


def mechanism_diagnostics(atts: dict[tuple[str, str], dict],
                          tasks: list[dict]) -> dict:
    out = {"dispatch_per_task": [], "closure_per_task": [],
           "oracle_block_attempts_total": 0, "skills_registered": [],
           "skills_rejected": []}
    for t in tasks:
        for arm in ARMS:
            r = atts.get((arm, t["task_id"]))
            if r:
                out["oracle_block_attempts_total"] += (
                    r.get("oracle_block_attempts") or 0)
        r = atts.get(("treatment", t["task_id"]))
        if not r:
            continue
        out["dispatch_per_task"].append(
            {"task_id": t["task_id"],
             "n": r.get("dispatch_invocations") or 0,
             "surface_n": (r.get("dispatch_surface") or {}).get("n"),
             "excluded_same_target": (r.get("dispatch_surface") or {})
             .get("excluded_same_target")})
        cl = r.get("closure") or {}
        out["closure_per_task"].append(
            {"task_id": t["task_id"], "n_files": cl.get("n_files"),
             "n_repo_py_files": cl.get("n_repo_py_files"),
             "target_in_closure": cl.get("target_in_closure")})
        sk = r.get("skill")
        if sk:
            (out["skills_registered"] if sk.get("registered")
             else out["skills_rejected"]).append(
                {"task_id": t["task_id"], "verdict": sk.get("verdict"),
                 "id": sk.get("id")})
    prec = [c for c in out["closure_per_task"]
            if c["target_in_closure"] is not None]
    out["closure_precision"] = (
        round(sum(1 for c in prec if c["target_in_closure"]) / len(prec), 4)
        if prec else None)
    return out


def tampering_incidents(atts: dict[tuple[str, str], dict]) -> list[dict]:
    return [{"arm": a, "task_id": tid, "files": r["tests_tampered"]}
            for (a, tid), r in sorted(atts.items()) if r.get("tests_tampered")]


def write_report(atts: dict[tuple[str, str], dict], tasks: list[dict],
                 path: Path = REPORT_MD) -> dict:
    gate = validity_gate(atts, tasks)
    an = analyze(atts, tasks)
    mech = mechanism_diagnostics(atts, tasks)
    tamper = tampering_incidents(atts)

    lines = [
        f"# Channel-E results — arms run (generated {_now_iso()}, driver "
        "`run_arms_e.py`)",
        "",
        f"Protocol: `{PREREG}` (frozen; Errata N=32). Student FROZEN in both "
        f"arms: `{MODEL}`. K={K_TURNS} turns, identical interface, escalation "
        "OFF. Raw per-task records: `channel_e_results.jsonl`.",
        "",
        "**MORTUARY CLAUSE in force**: if the kill rule fires, Channel E is "
        "falsified and with it the \"compound in the OS\" thesis — no re-run "
        "with a new mechanism, metric, or task shape.",
        "",
        "## Run-validity gate (§3)",
        "",
    ]
    if gate["passed"]:
        lines.append(
            f"**PASSED** — dispatch invocations: "
            f"{gate['dispatch_invocations_total']}, tasks with non-trivial "
            f"closure: {gate['tasks_with_nontrivial_closure']} (the treatment "
            "substrate was active).")
    else:
        lines.append(
            "**FAILED — RUN VOID (harness failure, NOT a null).** Dispatch "
            "never fired AND the closure never differed from the whole repo: "
            "the arms were identical and this run tests nothing.")
    if gate["oracle_leak_voided"]:
        lines.append(f"- oracle leak-through VOIDED tasks: "
                     f"{json.dumps(gate['oracle_leak_voided'])}")
    lines += [
        "",
        "## Headline numbers (paired tasks only; infra-dropped and voided "
        "excluded)",
        "",
        f"- paired tasks analysed: **{an['n_pairs']}** of {len(tasks)} "
        f"(infra-dropped: {len(an['dropped_infra'])}, "
        f"voided: {len(an['voided_oracle_leak'])})",
        f"- P_auto control: **{an['P_auto_control']}** · P_auto treatment: "
        f"**{an['P_auto_treatment']}** · C_overall = **{an['C_overall']}**",
        f"- discordant pairs: b (T-only pass) = "
        f"**{an['discordant_b_treatment_only']}**, c (C-only pass) = "
        f"**{an['discordant_c_control_only']}** (rate "
        f"{an['discordant_rate']})",
        f"- McNemar exact one-sided p (H1: treatment > control, α=0.05): "
        f"**{an['mcnemar_one_sided_p']}**",
        f"- power of N={an['n_pairs']} for the pre-registered ≥15 pp target "
        f"(Connor 1987, at max(observed disc, 0.15)): "
        f"**{an['power_for_15pp_at_observed_disc']}**",
        "",
        "## Per-epoch compounding statistic",
        "",
        "| epoch | pairs | P_auto(C) | P_auto(T) | C_k |",
        "|---|---|---|---|---|",
    ]
    for e in an["per_epoch"]:
        lines.append(f"| E{e['epoch']} | {e['n_pairs']} | "
                     f"{e['P_auto_control']} | {e['P_auto_treatment']} | "
                     f"{e['C_k']} |")
    ks = an["kill_rule"] or {}
    lines += [
        "",
        f"OLS slope of C_k over epochs: **{an['C_k_slope']}**",
        "",
        "## Secondary (pre-registered §4 — reported, never substituted for "
        "the primary)",
        "",
        f"- turns among solved: control mean "
        f"{an['turns_among_solved']['control_mean']}, treatment mean "
        f"{an['turns_among_solved']['treatment_mean']} (predicted mechanism: "
        "turn compression)",
        f"- dispatch invocations per treatment task: "
        + json.dumps([d for d in mech["dispatch_per_task"] if d["n"]]
                     or "none — dispatch never used"),
        f"- closure precision (true fix inside C(F)): "
        f"**{mech['closure_precision']}** over "
        f"{len(mech['closure_per_task'])} treatment tasks",
        f"- closure sizes: "
        + json.dumps([{k: c[k] for k in ('task_id', 'n_files')}
                      for c in mech["closure_per_task"]]),
        f"- oracle-block attempts (both arms, §1.3 guard): "
        f"{mech['oracle_block_attempts_total']}",
        f"- skills registered during the run (gate-passed): "
        f"{json.dumps(mech['skills_registered']) or 'none'}",
        f"- skills rejected by the gate: "
        f"{json.dumps(mech['skills_rejected']) or 'none'}",
        "",
        "## Guards",
        "",
        f"- tests/ tampering incidents (scored FAIL): "
        f"{tamper if tamper else 'none'}",
        f"- infra-dropped tasks: "
        + (json.dumps(an["dropped_infra"]) if an["dropped_infra"] else "none"),
        "",
        "## KILL RULE (§4, computed — verdict recorded by the operator in "
        "the prereg Errata)",
        "",
        f"- C_overall ≤ 0: **{ks.get('C_overall_le_0')}**",
        f"- one-sided 95% upper bound on the advantage: "
        f"**{ks.get('upper95_one_sided')}** — excludes ≥5 pp: "
        f"**{ks.get('upper95_excludes_5pp')}**",
        f"- discordance ≲5% with the mechanism fired: "
        f"**{ks.get('discordance_lesssim_5pct')}** (dispatch fired "
        f"{gate['dispatch_invocations_total']}×, non-trivial closure on "
        f"{gate['tasks_with_nontrivial_closure']} tasks)",
        "",
        "Interpretation boundary (§5, written before the data): ≥+15 pp "
        "significant with the mechanism demonstrably active → first earned "
        "evidence, Scaffolding-Swap next. 0 < C < 15 pp → unconfirmed hint, "
        "thesis does NOT survive on it. C ≤ 0 or kill-rule fired → thesis "
        "dead; publish the three-channel null. Prior: 20% compounds / 80% "
        "well-instrumented null.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"gate": gate, "analysis": an, "mechanism": mech,
            "tampering": tamper, "report": str(path)}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def assert_sandbox_alive() -> None:
    """The K-turn affordance (run/skill) requires a working sandbox engine in
    BOTH arms; without it the episode shape degenerates and the run would not
    test the frozen protocol. Fail loudly before any cell."""
    r = aios_sandbox.run_sandboxed(["/bin/echo", "phase5e-sandbox-probe"],
                                   timeout=30.0, now=time.time(),
                                   receipt_log=None)
    if not (r.sandboxed and r.ok):
        raise SystemExit(f"sandbox engine unavailable ({r.reason}) — the "
                         "K-turn interface cannot run; fix infra first "
                         "(this is an infra condition, never a result)")


def run(args: argparse.Namespace) -> int:
    results = Path(args.results)
    state_dir = Path(args.state_dir)
    if args.smoke_task:
        doc = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
        by_id = {t["task_id"]: t for t in doc["tasks"]}
        if args.smoke_task not in by_id:
            raise SystemExit(f"unknown task_id {args.smoke_task}")
        t = dict(by_id[args.smoke_task])
        t["seq"], t["epoch"] = 0, 1
        tasks = [t]
    else:
        tasks = main_tasks()

    assert_sandbox_alive()
    records = load_records(results)
    atts = attempts_of(records)
    check_treatment_state(state_dir, records)

    if not records:
        append_line(results, {
            "kind": "run_meta", "schema": SCHEMA, "ts": _now_iso(),
            "model": MODEL, "n_tasks": len(tasks), "n_epochs": N_EPOCHS,
            "k_turns": K_TURNS,
            "selection_rule": ("ALL non-holdout tasks in chronological order "
                               "(Errata N=32)"),
            "task_ids": [t["task_id"] for t in tasks],
            "call_timeout_s": args.call_timeout,
            "oracle_timeout_s": args.oracle_timeout,
            "state_dir": str(state_dir), "git_head": _git_head(),
            "prereg": PREREG,
        })

    n_todo = sum(1 for t in tasks for a in ARMS
                 if (a, t["task_id"]) not in atts)
    print(f"[phase5e] {_now_iso()} start: {n_todo} cells to run, "
          f"{len(atts)} done, model={MODEL}, K={K_TURNS}", flush=True)

    for t in tasks:
        for arm in ARMS:
            key = (arm, t["task_id"])
            if key in atts:
                continue
            if STOP_FILE.exists():
                remain = sum(1 for tt in tasks for a in ARMS
                             if (a, tt["task_id"]) not in atts)
                print(f"[phase5e] STOP file present — exiting cleanly "
                      f"({remain} cells remain)", flush=True)
                return 3
            started = _now_iso()
            print(f"[phase5e] seq={t['seq'] + 1}/{len(tasks)} E{t['epoch']} "
                  f"{arm} {t['task_id']} ...", flush=True)
            rec = run_episode(
                t, arm=arm, model=MODEL,
                state_dir=(state_dir if arm == "treatment" else None),
                call_timeout=args.call_timeout,
                oracle_timeout=args.oracle_timeout)
            rec.update({"kind": "attempt", "seq": t["seq"],
                        "epoch": t["epoch"], "ts_started": started,
                        "ts_finished": _now_iso()})
            append_line(results, rec)
            atts[key] = rec
            o = rec.get("oracle") or {}
            cl = rec.get("closure") or {}
            print(f"[phase5e]   -> passed={rec['passed']} "
                  f"infra={bool(rec['infra_error'])} turns={rec['turns_used']} "
                  f"disp={rec['dispatch_invocations']} "
                  f"closure={cl.get('n_files')}/{cl.get('n_repo_py_files')} "
                  f"oracle_rc={o.get('rc')} blocks={rec['oracle_block_attempts']} "
                  f"wall={rec['wall_s']}s", flush=True)

    complete = all((arm, t["task_id"]) in atts
                   for t in tasks for arm in ARMS)
    if not complete:
        return 3
    if args.smoke_task:
        print(json.dumps({"smoke": "complete", "cells": {
            f"{a}:{tid}": {"passed": r["passed"], "infra": r["infra_error"],
                           "turns": r["turns_used"],
                           "dispatch": r["dispatch_invocations"],
                           "closure_files": (r.get("closure") or {})
                           .get("n_files"),
                           "blocks": r["oracle_block_attempts"]}
            for (a, tid), r in atts.items()}}, indent=1), flush=True)
        return 0
    summary = write_report(atts, tasks)
    append_line(results, {"kind": "run_summary", "ts": _now_iso(),
                          **{k: v for k, v in summary.items()
                             if k in ("gate", "analysis")}})
    print(f"[phase5e] COMPLETE — report written to {summary['report']}",
          flush=True)
    print(json.dumps(summary["gate"], indent=1), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Channel-E arms driver (prereg-frozen)")
    ap.add_argument("--results", default=str(RESULTS_JSONL))
    ap.add_argument("--state-dir", default=str(STATE_DIR))
    ap.add_argument("--call-timeout", type=float, default=2400.0)
    ap.add_argument("--oracle-timeout", type=float, default=300.0)
    ap.add_argument("--smoke-task", default="",
                    help="run ONLY this task_id (both arms) — use a HOLDOUT "
                         "id + scratch --results/--state-dir")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)

    if args.report_only:
        tasks = main_tasks()
        atts = attempts_of(load_records(Path(args.results)))
        missing = [(a, t["task_id"]) for t in tasks for a in ARMS
                   if (a, t["task_id"]) not in atts]
        if missing:
            print(json.dumps({
                "status": "incomplete — no report (real numbers only for "
                          "finished cells)",
                "cells_done": len(atts), "cells_missing": len(missing),
                "gate_so_far": validity_gate(atts, tasks)}, indent=1))
            return 3
        summary = write_report(atts, tasks)
        print(json.dumps({"report": summary["report"],
                          "gate": summary["gate"]}, indent=1))
        return 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
