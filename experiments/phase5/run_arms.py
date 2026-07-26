#!/usr/bin/env python3
"""Phase 5 PILOT arms driver (prereg §2, §3, §5, §6).

FROZEN PROTOCOL: docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md.

PILOT: N = 24 tasks — the first 24 non-holdout tasks in chronological order
(holdout ids in calibration_holdout.json are EXCLUDED; §2, §4.1), split into
4 epochs of 6 (E1..E4). Identical task order in both arms (§2, §6.4).

Student: FROZEN ``qwen3-coder-next`` — selected by the pre-registered §4 rule
(smallest candidate with calibration P_auto in [0.20, 0.60]; measured 0.375,
8/8 scored, 0 infra — see calibration_results.json + Errata). Escalation is
structurally OFF (runner.py has no escalation path).

Arms (§3):
  * control   — run_task(arm="control"): state_dir forced to None, so the
    experience graph + skill registry are structurally absent (equivalent to
    "wiped before every task"); nothing is ever injected.
  * treatment — one persistent state dir for the WHOLE arm; before each task
    top-k prior experience (aios_experience) + applicable skills
    (aios_skills.retrieve) are injected; after each task the attempt is
    recorded and, on a pass, skill induction runs through the existing
    sandbox+unit-test gate. §6.3: the state dir MUST start EMPTY (asserted).

Loop order is task-major (control then treatment per task) so an interrupted
run still yields paired data; treatment tasks execute in chronological order
either way, so the treatment substrate accumulates exactly as §3 specifies.

RESUMABLE per (arm, task_id): every attempt is appended to
pilot_results.jsonl the moment it finishes (flush+fsync); on re-invocation
finished cells are skipped and treatment-state/results consistency is checked.
Infra-errored cells (§6.6: passed=None, dropped from paired analysis) are NOT
re-run automatically — re-measurement is an operator decision (see Errata
precedent), never a silent retry.

RUN-VALIDITY GATE (§3): the run is VOID unless treatment injection is
non-empty on >=1 task after E1. The gate result is the report's headline when
it fails — never silently absorbed into a null.

Graceful stop: touch experiments/phase5/PILOT_STOP to make the driver exit
cleanly (exit 3) between cells; delete it and re-invoke to resume.

The analysis (PILOT_RESULTS.md) is generated ONLY once all 48 cells exist:
paired one-sided exact McNemar on discordant pairs (alpha=0.05), per-epoch
C_k = P_auto(T,k) - P_auto(C,k) and its OLS slope, infra drops reported
separately, tampering scored FAIL (§6.1 — enforced in runner.py), plus the
confirmatory-run sizing from the observed discordant rate (§5). The pilot is
PRE-DECLARED UNDERPOWERED and is NOT a verdict on H1 (§5).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from runner import run_task  # noqa: E402

SCHEMA = "aios.phase5.pilot.v1"
TASKS_JSON = HERE / "tasks.json"
HOLDOUT_JSON = HERE / "calibration_holdout.json"
RESULTS_JSONL = HERE / "pilot_results.jsonl"
STATE_DIR = HERE / "pilot_state"
REPORT_MD = HERE / "PILOT_RESULTS.md"
STOP_FILE = HERE / "PILOT_STOP"

MODEL = "qwen3-coder-next"  # FROZEN per prereg §4 selection rule (Errata)
N_TASKS = 24
N_EPOCHS = 4
PER_EPOCH = N_TASKS // N_EPOCHS
ARMS = ("control", "treatment")

Z_ALPHA_1SIDED_05 = 1.6449  # z_{0.95}
Z_POWER_80 = 0.8416         # z_{0.80}


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _git_head() -> str:
    try:
        r = subprocess.run(["git", "-C", str(HERE.parents[1]), "rev-parse",
                            "HEAD"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Task selection (§2, §4.1, §5)
# ---------------------------------------------------------------------------

def pilot_tasks(tasks_file: Path = TASKS_JSON,
                holdout_file: Path = HOLDOUT_JSON,
                n: int = N_TASKS) -> list[dict]:
    """First ``n`` non-holdout tasks in chronological order, epoch-annotated."""
    doc = json.loads(tasks_file.read_text(encoding="utf-8"))
    holdout = set(json.loads(holdout_file.read_text(
        encoding="utf-8"))["task_ids"])
    tasks = sorted(doc["tasks"], key=lambda t: (t["ts_epoch"], t["task_id"]))
    kept = [t for t in tasks if t["task_id"] not in holdout][:n]
    if len(kept) != n:
        raise SystemExit(f"need {n} non-holdout tasks, have {len(kept)}")
    for i, t in enumerate(kept):
        t["seq"] = i
        t["epoch"] = i // PER_EPOCH + 1
    return kept


# ---------------------------------------------------------------------------
# Incremental results (resumable per (arm, task_id))
# ---------------------------------------------------------------------------

def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def attempts_of(records: list[dict]) -> dict[tuple[str, str], dict]:
    """(arm, task_id) -> attempt record (last one wins)."""
    return {(r["arm"], r["task_id"]): r for r in records
            if r.get("kind") == "attempt"}


def append_line(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        fh.flush()
        import os
        os.fsync(fh.fileno())


def check_treatment_state(state_dir: Path, records: list[dict]) -> None:
    """§6.3 on fresh start: state dir EMPTY. On resume: one run log per
    finished non-infra treatment attempt (results/state must not diverge)."""
    done_treat = [r for r in records if r.get("kind") == "attempt"
                  and r["arm"] == "treatment" and not r.get("infra_error")]
    if not done_treat:
        if state_dir.exists() and any(state_dir.rglob("*")):
            raise SystemExit(
                f"PRE-SEEDING GUARD (§6.3): treatment state dir {state_dir} "
                "is not empty but no treatment attempt is recorded. The "
                "index may contain only artifacts produced during THIS run — "
                "remove the dir or point --state-dir elsewhere.")
        return
    missing = [r["task_id"] for r in done_treat
               if not (state_dir / "runs" / f"{r['task_id']}.jsonl").exists()]
    if missing:
        raise SystemExit(
            f"STATE/RESULTS MISMATCH: treatment attempts recorded but their "
            f"run logs are absent from {state_dir}/runs: {missing}. "
            "Resuming would inject the wrong substrate — refusing.")


# ---------------------------------------------------------------------------
# Analysis (§1, §5, §6.6) — real numbers only, generated when complete
# ---------------------------------------------------------------------------

def mcnemar_one_sided(b: int, c: int) -> float | None:
    """P(X >= b), X ~ Binomial(b+c, 0.5). One-sided: treatment > control."""
    n = b + c
    if n == 0:
        return None
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def confirmatory_n(p_disc: float, delta: float,
                   z_a: float = Z_ALPHA_1SIDED_05,
                   z_b: float = Z_POWER_80) -> int | None:
    """Connor (1987) paired-proportions sizing: pairs needed for one-sided
    alpha, given discordant-pair rate p_disc and net advantage delta."""
    if delta <= 0 or p_disc <= 0 or delta > p_disc:
        return None
    n = (z_a * math.sqrt(p_disc)
         + z_b * math.sqrt(p_disc - delta * delta)) ** 2 / delta ** 2
    return math.ceil(n)


def validity_gate(atts: dict[tuple[str, str], dict],
                  tasks: list[dict]) -> dict:
    """§3: non-empty treatment injection on >=1 task after E1."""
    hits = [t["task_id"] for t in tasks if t["epoch"] >= 2
            and (r := atts.get(("treatment", t["task_id"])))
            and r.get("injection_nonempty")]
    return {"passed": bool(hits), "tasks_after_E1_with_injection": hits}


def analyze(atts: dict[tuple[str, str], dict], tasks: list[dict]) -> dict:
    pairs, dropped_infra = [], []
    for t in tasks:
        c = atts.get(("control", t["task_id"]))
        tr = atts.get(("treatment", t["task_id"]))
        if c is None or tr is None:
            continue
        if c.get("infra_error") or tr.get("infra_error"):
            dropped_infra.append({
                "task_id": t["task_id"], "epoch": t["epoch"],
                "control_infra": c.get("infra_error"),
                "treatment_infra": tr.get("infra_error")})
            continue
        pairs.append({"task_id": t["task_id"], "epoch": t["epoch"],
                      "control": bool(c["passed"]),
                      "treatment": bool(tr["passed"])})

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

    disc_rate = (b + c_) / n_pairs if n_pairs else None
    obs_delta = (b - c_) / n_pairs if n_pairs else None
    sizing = {"observed_discordant_rate": (round(disc_rate, 4)
                                           if disc_rate is not None else None),
              "observed_delta": (round(obs_delta, 4)
                                 if obs_delta is not None else None),
              "n_pairs_for_observed_delta": (
                  confirmatory_n(disc_rate, obs_delta)
                  if disc_rate and obs_delta and obs_delta > 0 else None),
              "grid": []}
    for delta in (0.05, 0.10, 0.15, 0.20, 0.25):
        pd = max(disc_rate or 0.0, delta)
        sizing["grid"].append({"delta": delta, "p_disc_assumed": round(pd, 4),
                               "n_pairs": confirmatory_n(pd, delta)})

    return {"n_pairs": n_pairs, "dropped_infra": dropped_infra,
            "P_auto_control": round(p_c, 4) if p_c is not None else None,
            "P_auto_treatment": round(p_t, 4) if p_t is not None else None,
            "C_overall": (round(p_t - p_c, 4)
                          if p_c is not None and p_t is not None else None),
            "discordant_b_treatment_only": b,
            "discordant_c_control_only": c_,
            "mcnemar_one_sided_p": (round(mcnemar_one_sided(b, c_), 4)
                                    if b + c_ else None),
            "per_epoch": epochs, "C_k_slope": slope, "sizing": sizing}


def skill_diagnostics(atts: dict[tuple[str, str], dict],
                      tasks: list[dict]) -> dict:
    """§6.2 diagnostics only — P_auto is unaffected by skill count."""
    out = {"induction_attempts": 0, "registered": [], "rejected": []}
    for t in tasks:
        r = atts.get(("treatment", t["task_id"]))
        sk = (r or {}).get("experience", {}).get("skill")
        if sk:
            out["induction_attempts"] += 1
            (out["registered"] if sk.get("registered")
             else out["rejected"]).append(
                {"task_id": t["task_id"], "verdict": sk.get("verdict"),
                 "id": sk.get("id")})
    return out


def tampering_incidents(atts: dict[tuple[str, str], dict]) -> list[dict]:
    return [{"arm": a, "task_id": tid, "files": r["tests_tampered"]}
            for (a, tid), r in sorted(atts.items()) if r.get("tests_tampered")]


def write_report(atts: dict[tuple[str, str], dict], tasks: list[dict],
                 path: Path = REPORT_MD) -> dict:
    gate = validity_gate(atts, tasks)
    an = analyze(atts, tasks)
    sk = skill_diagnostics(atts, tasks)
    tamper = tampering_incidents(atts)
    treat_inj = [atts[("treatment", t["task_id"])] for t in tasks
                 if ("treatment", t["task_id"]) in atts]

    lines = [
        "# Phase 5 PILOT results — arms run "
        f"(generated {_now_iso()}, driver `run_arms.py`)",
        "",
        "**THE PILOT IS PRE-DECLARED UNDERPOWERED AND IS NOT A VERDICT ON H1** "
        "(prereg §5: N=24 can only detect a ≈≥25 pp effect). Its registered "
        "purposes are (a) end-to-end harness validation, (b) confirming the "
        "retrieval injection actually fires, (c) a variance estimate to size "
        "the confirmatory run. Only the confirmatory run settles H1.",
        "",
        "Protocol: `docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md` "
        "(frozen). Student FROZEN in both arms: `" + MODEL + "` "
        "(§4 rule: calibration P_auto 0.375 ∈ [0.20, 0.60], 8/8 scored, "
        "0 infra). Escalation OFF. Raw per-task records: "
        "`pilot_results.jsonl`.",
        "",
        "## Run-validity gate (§3)",
        "",
    ]
    if gate["passed"]:
        lines.append(
            f"**PASSED** — treatment injection non-empty on "
            f"{len(gate['tasks_after_E1_with_injection'])} task(s) after E1 "
            "(the arms genuinely differed; the mechanism under test was "
            "active).")
    else:
        lines.append(
            "**FAILED — RUN VOID.** Treatment injection was EMPTY on every "
            "task after E1: the arms were identical and this run tests "
            "nothing. This is the headline result; the numbers below are "
            "reported for the record only and MUST NOT be read as a null "
            "on H1.")
    an_hdr = "## Headline numbers (paired tasks only, infra-dropped excluded)"
    lines += [
        "",
        an_hdr,
        "",
        f"- paired tasks analysed: **{an['n_pairs']}** of {len(tasks)} "
        f"(infra-dropped: {len(an['dropped_infra'])}, §6.6)",
        f"- P_auto control: **{an['P_auto_control']}** · "
        f"P_auto treatment: **{an['P_auto_treatment']}** · "
        f"C_overall = **{an['C_overall']}**",
        f"- discordant pairs: b (T-only pass) = **"
        f"{an['discordant_b_treatment_only']}**, c (C-only pass) = "
        f"**{an['discordant_c_control_only']}**",
        f"- McNemar exact one-sided p (H1: treatment > control, α=0.05): "
        f"**{an['mcnemar_one_sided_p']}**"
        + ("" if an["mcnemar_one_sided_p"] is not None
           else " (no discordant pairs — test undefined)"),
        "",
        "## Per-epoch compounding statistic (§1)",
        "",
        "| epoch | pairs | P_auto(C) | P_auto(T) | C_k |",
        "|---|---|---|---|---|",
    ]
    for e in an["per_epoch"]:
        lines.append(f"| E{e['epoch']} | {e['n_pairs']} | "
                     f"{e['P_auto_control']} | {e['P_auto_treatment']} | "
                     f"{e['C_k']} |")
    lines += [
        "",
        f"OLS slope of C_k over epochs: **{an['C_k_slope']}** "
        "(H1 requires C_k > 0 overall AND positive slope; a level "
        "difference alone is a one-off prompt advantage, not compounding).",
        "",
        "## Guards (§6)",
        "",
        f"- tests/ tampering incidents (scored FAIL, §6.1): "
        f"{tamper if tamper else 'none'}",
        f"- infra-dropped tasks (§6.6): "
        + (json.dumps(an["dropped_infra"]) if an["dropped_infra"]
           else "none"),
        f"- skill induction (§6.2 diagnostics only; P_auto is unaffected by "
        f"skill count): {sk['induction_attempts']} attempts, "
        f"{len(sk['registered'])} registered, {len(sk['rejected'])} "
        f"rejected by the sandbox+unit-test gate",
        f"  - registered: {json.dumps(sk['registered']) if sk['registered'] else 'none'}",
        f"- treatment injection sizes (chars): "
        + json.dumps([{ 'task_id': r['task_id'],
                        'injected_chars': r['injected_chars']}
                      for r in treat_inj]),
        "",
        "## Confirmatory-run sizing (§5, from the observed discordant rate)",
        "",
        f"- observed discordant-pair rate: "
        f"**{an['sizing']['observed_discordant_rate']}** · observed net "
        f"advantage: **{an['sizing']['observed_delta']}**",
        f"- pairs for 80% power at the OBSERVED delta (one-sided α=0.05, "
        f"Connor 1987): **{an['sizing']['n_pairs_for_observed_delta']}**"
        + ("" if an["sizing"]["n_pairs_for_observed_delta"] is not None
           else " (not estimable — observed delta ≤ 0; use the grid below)"),
        "",
        "| detectable advantage | assumed discordant rate | pairs needed |",
        "|---|---|---|",
    ]
    for g in an["sizing"]["grid"]:
        lines.append(f"| {g['delta']:.2f} | {g['p_disc_assumed']} | "
                     f"{g['n_pairs']} |")
    lines += [
        "",
        "(Assumed discordant rate = max(observed, delta) — a delta cannot "
        "exceed the discordant rate. The prereg expects the confirmatory N "
        "in the 100–300 range, requiring commits mined deeper than the "
        "last 400.)",
        "",
        "## Interpretation boundary (§7, written before the data)",
        "",
        "- C>0 + positive slope + significant → first earned evidence of "
        "OS-level compounding → Scaffolding-Swap falsification next.",
        "- C>0, flat slope → one-off prompt-context advantage, NOT "
        "compounding.",
        "- C≈0 → organs do not improve first-attempt autonomous resolution "
        "at this scale (honest negative).",
        "- C<0 → substrate actively hurts (retrieval pollution) → "
        "credit-assignment/pruning diagnosis.",
        "- Pre-registered prior: 20% compounds / 80% well-instrumented "
        "null.",
        "",
        "**Restated: this pilot is underpowered by design and NONE of the "
        "above may be claimed from it as a verdict on H1 — the confirmatory "
        "run decides.**",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"gate": gate, "analysis": an, "skills": sk,
            "tampering": tamper, "report": str(path)}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    results = Path(args.results)
    state_dir = Path(args.state_dir)
    tasks = pilot_tasks(n=args.n_tasks)
    if args.smoke_task:
        doc = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
        by_id = {t["task_id"]: t for t in doc["tasks"]}
        if args.smoke_task not in by_id:
            raise SystemExit(f"unknown task_id {args.smoke_task}")
        t = by_id[args.smoke_task]
        t["seq"], t["epoch"] = 0, 1
        tasks = [t]

    records = load_records(results)
    atts = attempts_of(records)
    check_treatment_state(state_dir, records)

    if not records:
        append_line(results, {
            "kind": "run_meta", "schema": SCHEMA, "ts": _now_iso(),
            "model": MODEL, "n_tasks": len(tasks), "n_epochs": N_EPOCHS,
            "selection_rule": ("first N non-holdout tasks in chronological "
                               "order; holdout excluded per §4.1"),
            "task_ids": [t["task_id"] for t in tasks],
            "holdout_excluded": json.loads(HOLDOUT_JSON.read_text(
                encoding="utf-8"))["task_ids"],
            "call_timeout_s": args.call_timeout,
            "oracle_timeout_s": args.oracle_timeout,
            "state_dir": str(state_dir), "git_head": _git_head(),
            "prereg": "docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md",
        })

    todo = [(t, arm) for t in tasks for arm in ARMS
            if (arm, t["task_id"]) not in atts]
    # task-major execution order: control then treatment per task
    print(f"[pilot] {_now_iso()} start: {len(todo)} cells to run, "
          f"{len(atts)} already done, model={MODEL}", flush=True)

    for t in tasks:
        for arm in ARMS:
            key = (arm, t["task_id"])
            if key in atts:
                continue
            if STOP_FILE.exists():
                print(f"[pilot] STOP file present — exiting cleanly "
                      f"({len([1 for tt in tasks for a in ARMS if (a, tt['task_id']) not in atts])} "
                      "cells remain)", flush=True)
                return 3
            started = _now_iso()
            print(f"[pilot] seq={t['seq'] + 1}/{len(tasks)} E{t['epoch']} "
                  f"{arm} {t['task_id']} ...", flush=True)
            rec = run_task(
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
            print(f"[pilot]   -> passed={rec['passed']} "
                  f"infra={bool(rec['infra_error'])} "
                  f"oracle_rc={o.get('rc')} oracle_passed={o.get('passed')} "
                  f"inj={rec['injected_chars']}ch "
                  f"tamper={bool(rec['tests_tampered'])} "
                  f"wall={rec['wall_s']}s", flush=True)

    complete = all((arm, t["task_id"]) in atts
                   for t in tasks for arm in ARMS)
    if not complete:
        return 3
    if args.smoke_task:
        gate = validity_gate(atts, tasks)
        print(json.dumps({"smoke": "complete",
                          "cells": {f"{a}:{tid}": {
                              "passed": r["passed"],
                              "infra": r["infra_error"],
                              "injected_chars": r["injected_chars"]}
                              for (a, tid), r in atts.items()},
                          "gate_note": gate}, indent=1), flush=True)
        return 0
    summary = write_report(atts, tasks)
    append_line(results, {"kind": "run_summary", "ts": _now_iso(),
                          **{k: v for k, v in summary.items()
                             if k in ("gate", "analysis")}})
    print(f"[pilot] COMPLETE — report written to {summary['report']}",
          flush=True)
    print(json.dumps(summary["gate"], indent=1), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Phase 5 PILOT arms driver (prereg-frozen)")
    ap.add_argument("--results", default=str(RESULTS_JSONL))
    ap.add_argument("--state-dir", default=str(STATE_DIR))
    ap.add_argument("--n-tasks", type=int, default=N_TASKS)
    ap.add_argument("--call-timeout", type=float, default=2400.0,
                    help="per model-call budget (Errata: 480s produced "
                         "false infra timeouts)")
    ap.add_argument("--oracle-timeout", type=float, default=300.0)
    ap.add_argument("--smoke-task", default="",
                    help="run ONLY this task_id (both arms) — QA smoke; "
                         "point --results/--state-dir at scratch paths")
    ap.add_argument("--report-only", action="store_true",
                    help="regenerate the report from existing results")
    args = ap.parse_args(argv)

    if args.report_only:
        tasks = pilot_tasks(n=args.n_tasks)
        atts = attempts_of(load_records(Path(args.results)))
        missing = [(a, t["task_id"]) for t in tasks for a in ARMS
                   if (a, t["task_id"]) not in atts]
        if missing:
            done = len(atts)
            print(json.dumps({
                "status": "incomplete — progress only, no report written "
                          "(real numbers exist only for finished cells)",
                "cells_done": done, "cells_missing": len(missing),
                "gate_so_far": validity_gate(atts, tasks)}, indent=1))
            return 3
        summary = write_report(atts, tasks)
        print(json.dumps({"report": summary["report"],
                          "gate": summary["gate"]}, indent=1))
        return 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
