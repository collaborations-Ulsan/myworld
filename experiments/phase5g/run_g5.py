#!/usr/bin/env python3
"""G5 driver — does a society beat a single agent with the same ledger?

FROZEN PROTOCOL: docs/AIOS_G5_SOCIETY_PREREG_2026-08-03.md. This is the N1 gate
of the whole society programme: if it fails, the network (N2-N4) and the
compute-system layers (C1-C3) are not built, and the society layer is retired.

Per task: run a K-turn episode, KILL it at the frozen death turn j, then let
each arm recover with an identical `K - j` turn budget, then grade with the
task's own external pytest oracle.

  A solo_norecord — same agent, fresh context, nothing carried
  B solo_ledger   — same agent, resumes from its own arc pack   <-- the control
  C society       — a different agent takes over (freshness-gated)
  D society_rev   — C plus `supersede`

Primary: `P_complete`, McNemar one-sided, key contrast **C vs B**.
Resumable per (arm, task_id); infra errors recorded, never counted as losses.
Graceful stop: touch experiments/phase5g/G5_STOP.
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
sys.path.insert(0, str(HERE.parent / "phase5e"))
sys.path.insert(0, str(HERE.parent / "phase5"))
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import death                                   # noqa: E402
import workspace as ws_mod                     # noqa: E402
import turn_loop as tl                         # noqa: E402
from runner import run_oracle, InfraError      # noqa: E402
import aios_society as soc                     # noqa: E402

SCHEMA = "aios.phase5g.run.v1"
TASKS_JSON = HERE.parent / "phase5" / "tasks.json"
HOLDOUT_JSON = HERE.parent / "phase5" / "calibration_holdout.json"
RESULTS = HERE / "g5_results.jsonl"
ARCS_DIR = HERE / "g5_arcs"
LOCKS_DIR = HERE / "g5_locks"
REPORT = HERE / "G5_RESULTS.md"
STOP_FILE = HERE / "G5_STOP"
PREREG = "docs/AIOS_G5_SOCIETY_PREREG_2026-08-03.md"

MODEL = "qwen3-coder-next"       # frozen, identical in every arm
K_TURNS = tl.K_TURNS             # 5
N_TASKS = 32
Z95 = 1.6449


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _git_head() -> str:
    try:
        r = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def main_tasks(n: int = N_TASKS, tasks_file: Path | str | None = None
               ) -> list[dict]:
    """G5's task selection, or a pre-built manifest for a later experiment.

    `tasks_file` exists so G6 can run on its own frozen manifest through THIS
    verified driver instead of a fresh copy (a new runner would mean new bugs
    deciding a result). Default arguments reproduce G5 exactly.
    """
    src = Path(tasks_file) if tasks_file else TASKS_JSON
    doc = json.loads(src.read_text(encoding="utf-8"))
    tasks = sorted(doc["tasks"], key=lambda t: (t["ts_epoch"], t["task_id"]))
    if tasks_file is None:
        holdout = set(json.loads(HOLDOUT_JSON.read_text(
            encoding="utf-8"))["task_ids"])
        tasks = [t for t in tasks if t["task_id"] not in holdout]
    if len(tasks) != n:
        raise SystemExit(f"expected {n} tasks in {src.name}, have {len(tasks)}")
    for i, t in enumerate(tasks):
        t["seq"] = i
    return tasks


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def append_line(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# ---------------------------------------------------------------------------
# One cell: episode -> forced death -> arm-specific recovery -> oracle
# ---------------------------------------------------------------------------

def run_cell(task: dict, arm: str, *, call_timeout: float, oracle_timeout: float,
             arcs_dir: Path, locks_dir: Path, model_fn=None) -> dict:
    j = death.death_turn(task["task_id"])
    budget = death.post_death_budget(K_TURNS, j)
    rec = {"schema": SCHEMA, "task_id": task["task_id"], "arm": arm,
           "model": MODEL, "death_turn": j, "post_death_turns": budget,
           "passed": None, "infra_error": None, "tests_tampered": [],
           "ownership_transferred": False, "arc_id": None,
           "pre_death_turns": 0, "recovery_turns": 0, "wall_s": None,
           "supersessions": 0, "fail_reason": None}
    t0 = time.time()
    ws = None
    try:
        ws = ws_mod.materialize(REPO_ROOT, task["commit"], task["parent_commit"],
                                task["script_path"], task["test_paths"])
        snapshot = ws_mod.tests_snapshot(ws)
        goal = (f"make the tests in {', '.join(task['test_paths'])} pass by "
                f"editing {task['script_path']}")

        arc_id = None
        if death.arm_uses_ledger(arm):
            arc_id = soc.open_arc(goal, agent="solo@agent", now=time.time(),
                                  constraints=[f"forbid:tests/"],
                                  oracle_cmd=" ".join(task["oracle_cmd"]),
                                  arcs_dir=arcs_dir)["arc_id"]
            soc.claim(arc_id, agent="solo@agent", now=time.time(), ttl=3600,
                      arcs_dir=arcs_dir, locks_dir=locks_dir)
            rec["arc_id"] = arc_id

        # --- life before death: j turns, recorded as it happens (INV-5) ----
        pre = tl.run_episode(task, arm="control", model=MODEL, ws=ws,
                             call_timeout=call_timeout,
                             oracle_timeout=oracle_timeout, model_fn=model_fn,
                             max_turns=j)
        rec["pre_death_turns"] = pre.get("turns_used", 0)
        if pre.get("infra_error"):
            rec["infra_error"] = pre["infra_error"]
            return rec
        if arc_id:
            for a in pre.get("actions", []):
                if a.get("kind") in ("write", "run") and "blocked" not in a:
                    soc.note(arc_id, f"{a['kind']}: {a.get('arg','')}"[:400],
                             agent="solo@agent", now=time.time(),
                             evidence=[f"turn:{a.get('turn')}"],
                             arcs_dir=arcs_dir)
            soc.offer_handoff(arc_id, agent="solo@agent", now=time.time(),
                              reason="context death (forced, G5)",
                              next_step="continue making the tests pass",
                              arcs_dir=arcs_dir)

        # --- the death happens here: the episode's context is discarded ----
        ctx = death.recovery_context(arm, task, arc_id, now=time.time(),
                                     arcs_dir=arcs_dir)
        if arc_id and death.arm_is_society(arm):
            pack = ctx.get("pack") or {}
            took = soc.resume(arc_id, agent=ctx["taker"],
                              pack_tip_seq=pack.get("tip_seq", -1),
                              now=time.time(), ttl=3600, substrate="peer",
                              arcs_dir=arcs_dir, locks_dir=locks_dir)
            rec["ownership_transferred"] = bool(took.get("ok"))
        elif arc_id:
            soc.claim(arc_id, agent=ctx["taker"], now=time.time(), ttl=3600,
                      arcs_dir=arcs_dir, locks_dir=locks_dir)

        # --- recovery: identical budget in every arm -----------------------
        if budget > 0:
            post = tl.run_episode(task, arm="control", model=MODEL, ws=ws,
                                  call_timeout=call_timeout,
                                  oracle_timeout=oracle_timeout,
                                  model_fn=model_fn, max_turns=budget,
                                  extra_context=ctx["text"])
            rec["recovery_turns"] = post.get("turns_used", 0)
            if post.get("infra_error"):
                rec["infra_error"] = post["infra_error"]
                return rec

        rec["tests_tampered"] = ws_mod.tests_tampered(ws, snapshot)
        oracle = run_oracle(ws, task["oracle_cmd"], timeout=oracle_timeout)
        rec["oracle"] = {k: oracle[k] for k in ("rc", "passed", "ok")}
        rec["passed"] = (False if rec["tests_tampered"] else bool(oracle["ok"]))
        if not rec["passed"]:
            rec["fail_reason"] = ("tests_diff_guard" if rec["tests_tampered"]
                                  else "oracle_failed")
        if arc_id:
            st = soc.project(soc.read_events(arc_id, arcs_dir), now=time.time())
            rec["supersessions"] = len(st.get("supersessions", []))
        return rec
    except InfraError as exc:
        rec["infra_error"] = str(exc)
        return rec
    finally:
        rec["wall_s"] = round(time.time() - t0, 2)
        if ws is not None:
            ws_mod.cleanup(ws)


# ---------------------------------------------------------------------------
# Analysis (prereg §4)
# ---------------------------------------------------------------------------

def mcnemar_one_sided(b: int, c: int) -> float | None:
    n = b + c
    if n == 0:
        return None
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def paired_upper_bound(b: int, c: int, n: int, z: float = Z95) -> float | None:
    if n == 0:
        return None
    d = (b - c) / n
    se = math.sqrt(max((b + c) / n - d * d, 0.0) / n)
    return d + z * se


def contrast(atts: dict, tasks: list[dict], treat: str, ctrl: str) -> dict:
    pairs, dropped = [], []
    for t in tasks:
        a, b_ = atts.get((treat, t["task_id"])), atts.get((ctrl, t["task_id"]))
        if a is None or b_ is None:
            continue
        if a.get("infra_error") or b_.get("infra_error"):
            dropped.append(t["task_id"])
            continue
        pairs.append((bool(a["passed"]), bool(b_["passed"])))
    n = len(pairs)
    b = sum(1 for x, y in pairs if x and not y)
    c = sum(1 for x, y in pairs if y and not x)
    pt = sum(1 for x, _ in pairs if x) / n if n else None
    pc = sum(1 for _, y in pairs if y) / n if n else None
    ub = paired_upper_bound(b, c, n) if n else None
    return {"treatment": treat, "control": ctrl, "n_pairs": n,
            "dropped_infra": dropped,
            "P_complete_treatment": round(pt, 4) if pt is not None else None,
            "P_complete_control": round(pc, 4) if pc is not None else None,
            "delta": round(pt - pc, 4) if n else None,
            "b_treat_only": b, "c_ctrl_only": c,
            "discordant_rate": round((b + c) / n, 4) if n else None,
            "mcnemar_one_sided_p": (round(mcnemar_one_sided(b, c), 4)
                                    if b + c else None),
            "upper95_one_sided": round(ub, 4) if ub is not None else None}


def write_report(atts: dict, tasks: list[dict], records: list[dict],
                 path: Path = REPORT, arms: tuple = death.ARMS) -> dict:
    gate = death.validity(records)
    # The primary contrast follows the arms actually run: with the society arms
    # present it is society vs solo+ledger (G5); with only the solo arms it is
    # ledger vs no-record (G6). Chosen by which arms exist, never post hoc.
    if "society" in arms:
        main = contrast(atts, tasks, "society", "solo_ledger")
        others = [contrast(atts, tasks, "solo_ledger", "solo_norecord"),
                  contrast(atts, tasks, "society_rev", "society"),
                  contrast(atts, tasks, "society", "solo_norecord")]
    else:
        main = contrast(atts, tasks, "solo_ledger", "solo_norecord")
        others = []
    rates = {}
    for arm in arms:
        cells = [r for r in atts.values() if r["arm"] == arm
                 and not r.get("infra_error")]
        rates[arm] = (round(sum(1 for r in cells if r["passed"]) / len(cells), 4)
                      if cells else None)
    kill = None
    if main["n_pairs"]:
        kill = {"C_le_B": (main["delta"] or 0) <= 0,
                "upper95_excludes_5pp": (main["upper95_one_sided"] is not None
                                         and main["upper95_one_sided"] < 0.05),
                "upper95": main["upper95_one_sided"]}

    lines = [
        f"# G5 results — does the society beat a single agent with the same "
        f"ledger? (generated {_now_iso()})",
        "",
        f"Protocol: `{PREREG}` (frozen). Student `{MODEL}`, identical in every "
        f"arm; K={K_TURNS}; death turn derived from the task id and identical "
        "across arms; post-death budget identical across arms.",
        "",
        "## Run-validity gate (§5.5)",
        "",
        ("**PASSED** — " if gate["passed"] else "**FAILED — RUN VOID.** ")
        + gate["detail"],
        "",
        "## P_complete by arm",
        "",
        "| arm | P_complete |", "|---|---|",
    ]
    for arm in arms:            # only the arms this run executed (G6 runs 2 of 4)
        lines.append(f"| {arm} | {rates[arm]} |")
    lines += [
        "",
        "## THE contrast — society vs solo+ledger (prereg §4)",
        "",
        f"- paired tasks: **{main['n_pairs']}** (infra-dropped "
        f"{len(main['dropped_infra'])})",
        f"- P_complete society **{main['P_complete_treatment']}** vs "
        f"solo+ledger **{main['P_complete_control']}** → delta "
        f"**{main['delta']}**",
        f"- discordant b={main['b_treat_only']} c={main['c_ctrl_only']} "
        f"(rate {main['discordant_rate']})",
        f"- McNemar one-sided p: **{main['mcnemar_one_sided_p']}**",
        f"- one-sided 95% upper bound on the advantage: "
        f"**{main['upper95_one_sided']}**",
        "",
        "## KILL RULE (§6, computed — verdict recorded by the operator)",
        "",
        f"- C ≤ B: **{(kill or {}).get('C_le_B')}**",
        f"- upper bound excludes a ≥5pp advantage: "
        f"**{(kill or {}).get('upper95_excludes_5pp')}**",
        "",
        "If either fires: the society layer is not justified at this scale — "
        "dissolve it, re-converge on the storage redesign (arm B), and do NOT "
        "build N2–N4 or C1–C3.",
        "",
        "## Secondary contrasts (reported, never substituted for the primary)",
        "",
        "| treatment | control | delta | p | n |", "|---|---|---|---|---|",
    ]
    for o in others:
        lines.append(f"| {o['treatment']} | {o['control']} | {o['delta']} | "
                     f"{o['mcnemar_one_sided_p']} | {o['n_pairs']} |")
    lines += ["",
              "*(solo_ledger vs solo_norecord asks whether the RECORD is worth "
              "anything at all — if that is ~0, the finding is more fundamental "
              "than the society question. society_rev vs society isolates "
              "`supersede`.)*"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"gate": gate, "main": main, "others": others, "rates": rates,
            "kill_rule": kill, "report": str(path)}


def run(args: argparse.Namespace) -> int:
    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    bad = [a for a in arms if a not in death.ARMS]
    if bad:
        raise SystemExit(f"unknown arm(s) {bad}; known: {list(death.ARMS)}")
    tasks = main_tasks(args.n_tasks, args.tasks_file or None)[: args.n_tasks]
    results, arcs_dir, locks_dir = Path(args.results), Path(args.arcs_dir), Path(args.locks_dir)
    records = load_records(results)
    atts = {(r["arm"], r["task_id"]): r for r in records
            if r.get("kind") == "attempt"}
    if not records:
        append_line(results, {
            "kind": "run_meta", "schema": SCHEMA, "ts": _now_iso(),
            "model": MODEL, "k_turns": K_TURNS, "arms": list(arms),
            "n_tasks": len(tasks), "prereg": PREREG, "git_head": _git_head(),
            "death_turns": {t["task_id"]: death.death_turn(t["task_id"])
                            for t in tasks}})
    todo = sum(1 for t in tasks for a in arms
               if (a, t["task_id"]) not in atts)
    print(f"[g5] {_now_iso()} start: {todo} cells, {len(atts)} done", flush=True)

    for t in tasks:
        for arm in arms:
            if (arm, t["task_id"]) in atts:
                continue
            if STOP_FILE.exists():
                print("[g5] STOP file — exiting cleanly", flush=True)
                return 3
            print(f"[g5] {t['seq']+1}/{len(tasks)} {arm} {t['task_id']} "
                  f"(death@{death.death_turn(t['task_id'])}) ...", flush=True)
            rec = run_cell(t, arm, call_timeout=args.call_timeout,
                           oracle_timeout=args.oracle_timeout,
                           arcs_dir=arcs_dir, locks_dir=locks_dir)
            rec.update({"kind": "attempt", "seq": t["seq"],
                        "ts_finished": _now_iso()})
            append_line(results, rec)
            atts[(arm, t["task_id"])] = rec
            print(f"[g5]   -> passed={rec['passed']} "
                  f"infra={bool(rec['infra_error'])} "
                  f"transfer={rec['ownership_transferred']} "
                  f"wall={rec['wall_s']}s", flush=True)

    if any((a, t["task_id"]) not in atts for t in tasks for a in arms):
        return 3
    summary = write_report(atts, tasks, load_records(results),
                           path=Path(args.report), arms=arms)
    append_line(results, {"kind": "run_summary", "ts": _now_iso(),
                          **{k: v for k, v in summary.items()
                             if k in ("gate", "main", "kill_rule", "rates")}})
    print(f"[g5] COMPLETE — {summary['report']}", flush=True)
    print(json.dumps(summary["main"], indent=1), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="G5 driver (prereg-frozen)")
    ap.add_argument("--results", default=str(RESULTS))
    ap.add_argument("--arcs-dir", default=str(ARCS_DIR))
    ap.add_argument("--locks-dir", default=str(LOCKS_DIR))
    ap.add_argument("--n-tasks", type=int, default=N_TASKS)
    ap.add_argument("--tasks-file", default="",
                    help="pre-built manifest (G6); default = G5's pool")
    ap.add_argument("--arms", default=",".join(death.ARMS),
                    help="subset of arms to run, comma-separated")
    ap.add_argument("--report", default=str(REPORT))
    ap.add_argument("--call-timeout", type=float, default=2400.0)
    ap.add_argument("--oracle-timeout", type=float, default=300.0)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args(argv)
    if a.report_only:
        arms = tuple(x.strip() for x in a.arms.split(",") if x.strip())
        tasks = main_tasks(a.n_tasks, a.tasks_file or None)[: a.n_tasks]
        recs = load_records(Path(a.results))
        atts = {(r["arm"], r["task_id"]): r for r in recs
                if r.get("kind") == "attempt"}
        missing = [(x, t["task_id"]) for t in tasks for x in arms
                   if (x, t["task_id"]) not in atts]
        if missing:
            print(json.dumps({"status": "incomplete — no report",
                              "cells_done": len(atts),
                              "cells_missing": len(missing)}, indent=1))
            return 3
        print(json.dumps(write_report(atts, tasks, recs, path=Path(a.report),
                                      arms=arms)["main"], indent=1))
        return 0
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
