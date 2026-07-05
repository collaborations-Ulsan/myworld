"""Experiment orchestrator for the AGI certification-layer witness (README.md ablation matrix
R1-R7). This module owns exactly four things:

  1. ``load_data``  -- read the 4 frozen data/ files into the shapes every downstream module
     expects (contracts.Claim lists grouped by task_id, splits, pilot metadata).
  2. ``fit_certs``   -- fit APEX (conformal threshold) and GoEN (mode B + mode C logistic
     legibility models) ONCE, from the CALIBRATION split, before any arm/seed loop runs.
  3. ``main``        -- the CLI: for every (arm, seed) pair, give the arm a FRESH token budget,
     call ``arms.run_arm`` (pinned signature below), and append every ``TaskOutcome`` it returns
     to an append-only JSONL results file.
  4. A ``--dry-run`` smoke path so this file is testable before ``arms.py`` (built in parallel)
     exists, and a bare-invocation self-test at the bottom.

Pinned call contract this module targets (see README + task spec; arms.py owns the real impl):

    arms.run_arm(arm, tasks, ledger_by_task, solver_model, budget, cfg, *,
                 ablate=None, seed=0, apex_calib=None, goen_model=None) -> list[TaskOutcome]

Everything here is deterministic given (data files, seed): no wall-clock branches any output,
and every RNG use below is seeded.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import types
from collections import defaultdict
from dataclasses import asdict

from contracts import TaskOutcome
from claims import claims_from_jsonl, executable_claims, run_candidate
import llm
from certs.apex import fit_apex, apex_certify
from certs import goen as goen_mod
from certs.goen import fit_goen, extract_features, GoenModel

# ``arms.py`` is being built in parallel against the signature above. Import it lazily/softly so
# this file (and its self-test) stays runnable before arms.py lands: --dry-run monkeypatches
# ``arms.run_arm`` onto a stub module either way, and a real (non-dry-run) invocation raises a
# clear error if the real implementation still isn't there yet.
try:
    import arms  # type: ignore
except ModuleNotFoundError:
    arms = None  # populated below by --dry-run, or by a real arms.py once present

_HERE = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# 1. Data loading
# =============================================================================

def load_data(data_dir: str = "data") -> tuple[list[dict], dict[str, list], dict, dict]:
    """Load the 4 frozen data/ files.

    Returns:
      tasks           -- list of task dicts (tasks.jsonl rows, incl. gold_code/test_list/etc).
      ledger_by_task  -- {task_id: [Claim, ...]}, built via ``claims.claims_from_jsonl`` then
                         grouped -- a PLAIN dict (not a defaultdict) so a downstream ``[missing]``
                         lookup raises KeyError instead of silently auto-vivifying an empty list.
      splits          -- {"calibration": [...], "eval": [...], "spare": [...]} task_id lists.
      pilot           -- pilot.json dict; ``pilot["chosen_solver"]`` is the default solver tier.
    """
    d = data_dir if os.path.isabs(data_dir) else os.path.join(_HERE, data_dir)

    with open(os.path.join(d, "tasks.jsonl")) as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    claims = claims_from_jsonl(os.path.join(d, "ledger.jsonl"))
    grouped: dict[str, list] = defaultdict(list)
    for c in claims:
        grouped[c.task_id].append(c)
    ledger_by_task = dict(grouped)

    with open(os.path.join(d, "splits.json")) as f:
        splits = json.load(f)

    with open(os.path.join(d, "pilot.json")) as f:
        pilot = json.load(f)

    return tasks, ledger_by_task, splits, pilot


# =============================================================================
# 2. Certificate fitting (once, from the CALIBRATION split)
# =============================================================================

def _gold_agrees_with_claims(task: dict, claims: list) -> bool:
    """Deterministic, LLM-free calibration label: does the task's OWN ``gold_code`` reproduce
    the asserted output of every executable IO claim in its ledger context?

    This is the cheap "execute the gold_code against the claims" approximation of "solved"
    named in the task spec: calibration tasks are forced P0 (clean) by ``dataset.py``, so gold
    trivially passes its own hidden tests -- the informative signal isn't "does gold pass" (always
    true) but "does this exact claim SET (incl. honest seeder mistakes) actually agree with the
    ground truth a solver would be graded against". A noisy/wrong claim drags the label to False
    even though a correct gold answer exists elsewhere; a clean, corroborated ledger stays True.
    This keeps cert-fitting a pure function of the frozen data files -- no LLM call, so fitting
    certs never touches the eval token budget.
    """
    io_idx = executable_claims(claims)
    if not io_idx:
        return True  # vacuously agrees: nothing executable to disagree with
    for i in io_idx:
        c = claims[i]
        res = run_candidate(task["gold_code"], task["func_name"], c.payload["input"], timeout_s=3.0)
        if not res.ok:
            return False
        got = json.dumps(res.output, sort_keys=True, default=str)
        want = json.dumps(c.payload.get("output"), sort_keys=True, default=str)
        if got != want:
            return False
    return True


def _uniform_goen_model(mode: str) -> GoenModel:
    """Fallback GoEN model for an EMPTY calibration split (``fit_goen`` requires >=1 example and
    raises otherwise). Zero weights -> ``predict_proba`` always returns 0.5 (uniform / no
    information) for every context, so ``goen_certify``'s rewire search never finds a
    strictly-better candidate and ``keep_all`` wins by construction -- a safe, inert placeholder,
    not a real legibility model. Real runs need a non-empty calibration pool (README n_cal=60)."""
    feature_order = list(goen_mod._B_KEYS)
    if mode == "C":
        feature_order = feature_order + list(goen_mod._C_EXTRA_KEYS)
    import numpy as np
    return GoenModel(weights=np.zeros(len(feature_order) + 1), feature_order=feature_order, mode=mode)


def fit_certs(tasks: list[dict], ledger_by_task: dict[str, list], splits: dict):
    """Fit APEX (conformal threshold) + GoEN mode-B/mode-C legibility models from the
    CALIBRATION split. Returns ``(apex_calib, goen_model_B, goen_model_C)``.

    Empty-calibration handling (can happen with tiny smoke data, e.g. this repo's 7-task
    smoke set has 0 calibration tasks): ``fit_apex([])`` already degrades gracefully to its own
    conservative fallback (see certs/apex.py), so it's called unconditionally with whatever
    calib pairs exist (possibly none). ``fit_goen`` does NOT accept an empty list (raises), so we
    substitute ``_uniform_goen_model`` and print a loud warning -- callers must not mistake a
    smoke run's inert GoEN model for a real fit.
    """
    by_id = {t["task_id"]: t for t in tasks}
    cal_ids = list(splits.get("calibration", []))

    calib_pairs: list[tuple[list, bool]] = []
    for tid in cal_ids:
        task = by_id.get(tid)
        if task is None:
            continue
        claims = ledger_by_task.get(tid, [])
        calib_pairs.append((claims, _gold_agrees_with_claims(task, claims)))

    if not calib_pairs:
        print(
            "[fit_certs] WARNING: calibration split is EMPTY (0 usable tasks) -> falling back to "
            "conservative defaults: ApexCalib via fit_apex([]) safe threshold, uniform/unfit "
            "GoenModel for both B and C modes. This is expected on tiny smoke data but is NOT a "
            "real calibration -- real runs need a larger pilot pool (README n_cal=60)."
        )
        apex_calib = fit_apex([])
        return apex_calib, _uniform_goen_model("B"), _uniform_goen_model("C")

    apex_calib = fit_apex(calib_pairs)

    goen_examples_B = [(extract_features(c, "B"), solved) for c, solved in calib_pairs]
    goen_examples_C = [
        (extract_features(c, "C", cert_outputs={"apex": apex_certify(c, apex_calib)}), solved)
        for c, solved in calib_pairs
    ]
    goen_model_B = fit_goen(goen_examples_B, mode="B")
    goen_model_C = fit_goen(goen_examples_C, mode="C")
    return apex_calib, goen_model_B, goen_model_C


# =============================================================================
# 3. --dry-run stub (arms.py is built in parallel; this keeps run.py testable now)
# =============================================================================

def _dry_run_stub(
    arm, tasks, ledger_by_task, solver_model, budget, cfg, *,
    ablate=None, seed=0, apex_calib=None, goen_model=None,
) -> list[TaskOutcome]:
    """Trivial synthetic replacement for ``arms.run_arm``, matching its pinned signature exactly.
    Deterministic given (arm, ablate, seed, task order): no LLM calls, no wall-clock. Exercises
    the real ``budget.spend()`` accounting path so the smoke test's token bookkeeping is genuine,
    not faked."""
    # Deterministic per-(arm,ablate,seed) seed, independent of PYTHONHASHSEED / dict/set ordering.
    label = f"{arm}|{ablate}|{seed}"
    local_seed = sum(ord(ch) for ch in label) + seed * 1000
    rng = random.Random(local_seed)

    outcomes: list[TaskOutcome] = []
    for t in tasks:
        tokens = 10 + rng.randint(0, 40)
        try:
            budget.spend(tokens)
        except llm.BudgetExhausted:
            outcomes.append(TaskOutcome(
                task_id=t["task_id"], arm=arm, seed=seed, submitted=False, verified=False,
                tokens=0, wall_s=0.0, poison_condition=t.get("poison_condition", ""),
                note="dry-run: budget exhausted",
            ))
            continue
        submitted = rng.random() > 0.1
        verified = submitted and rng.random() > 0.35
        outcomes.append(TaskOutcome(
            task_id=t["task_id"], arm=arm, seed=seed, submitted=submitted, verified=verified,
            tokens=tokens, wall_s=0.001, poison_condition=t.get("poison_condition", ""),
            note="dry-run synthetic",
        ))
    return outcomes


def _install_dry_run() -> None:
    """Monkeypatch ``arms.run_arm`` -> ``_dry_run_stub``, creating a stub ``arms`` module in
    ``sys.modules`` first if the real one isn't importable yet (arms.py in-flight)."""
    global arms
    if arms is None:
        arms = types.ModuleType("arms")
        sys.modules["arms"] = arms
    arms.run_arm = _dry_run_stub


# =============================================================================
# 4. CLI
# =============================================================================

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", default=None,
                    help="solver model id, e.g. 'nim:qwen/qwen3-next-80b-a3b-instruct' or "
                         "'ollama:qwen2.5-coder:7b'. Default: pilot['chosen_solver'].")
    ap.add_argument("--arms", default="A,B,C", help="comma-separated arm labels, e.g. A,B,C")
    ap.add_argument("--seeds", default="0,1,2", help="comma-separated integer seeds")
    ap.add_argument("--budget", type=int, default=50_000, help="fixed total token budget per (arm,seed) run")
    ap.add_argument("--ablate", default=None, choices=[None, "apex", "iris", "descent", "goen", "writeback"],
                    help="ablation applied ONLY to arm C (README R2-R6); ignored for A/B")
    ap.add_argument("--n", type=int, default=None, help="limit to the first N eval tasks (deterministic order)")
    ap.add_argument("--data-dir", default="data", help="directory holding tasks.jsonl/ledger.jsonl/splits.json/pilot.json")
    ap.add_argument("--out", default="results/runs.jsonl", help="append-only JSONL output path")
    ap.add_argument("--dry-run", action="store_true",
                    help="monkeypatch arms.run_arm to a trivial deterministic synthetic stub "
                         "(no LLM calls) -- for testing run.py before/without arms.py")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.dry_run:
        _install_dry_run()
    elif arms is None or not hasattr(arms, "run_arm"):
        raise SystemExit(
            "arms.py not found (or missing run_arm) -- implement arms.py per the pinned signature "
            "in README.md, or pass --dry-run for a synthetic smoke test."
        )

    tasks, ledger_by_task, splits, pilot = load_data(args.data_dir)
    solver_model = args.tier or pilot["chosen_solver"]

    eval_id_set = set(splits["eval"])
    eval_tasks = [t for t in tasks if t["task_id"] in eval_id_set]
    if args.n is not None:
        eval_tasks = eval_tasks[: args.n]

    apex_calib, goen_model_B, goen_model_C = fit_certs(tasks, ledger_by_task, splits)

    out_path = args.out if os.path.isabs(args.out) else os.path.join(_HERE, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    arm_list = [a.strip() for a in args.arms.split(",") if a.strip()]
    seed_list = [int(s) for s in args.seeds.split(",") if s.strip() != ""]

    # cfg carries the generation/execution knobs arms.py reads for solver sampling; README's
    # regime fixes k=6 samples/task with abstention right. Kept minimal + documented here since
    # arms.py's exact needs land with its implementation (adapt minimally if a kwarg differs).
    cfg = arms.ArmConfig(k=6, temp=0.8, solver_max_tokens=512, exec_timeout_s=5.0)

    for arm in arm_list:
        ablate = args.ablate if arm == "C" else None  # ablation only ever applies to arm C
        arm_label = f"{arm}-ablate-{ablate}" if ablate else arm
        goen_model = goen_model_C if arm == "C" else (goen_model_B if arm == "B" else None)

        for seed in seed_list:
            budget = llm.TokenBudget(args.budget)  # fresh budget per (arm, seed)
            outcomes = arms.run_arm(
                arm, eval_tasks, ledger_by_task, solver_model, budget, cfg,
                ablate=ablate, seed=seed, apex_calib=apex_calib, goen_model=goen_model,
            )

            with open(out_path, "a") as f:
                for o in outcomes:
                    row = asdict(o)
                    row["arm"] = arm_label  # ensure the ablation suffix is always present
                    row["tier"] = solver_model
                    f.write(json.dumps(row, sort_keys=True, default=str) + "\n")

            n_submitted = sum(1 for o in outcomes if o.submitted)
            n_verified = sum(1 for o in outcomes if o.verified)
            print(
                f"[{arm_label} seed={seed} tier={solver_model}] tasks={len(outcomes)} "
                f"submitted={n_submitted} verified={n_verified} "
                f"tokens={budget.spent()}/{budget.total}"
            )


# =============================================================================
# Self-test / smoke (bare invocation only -- `python3 run.py --help` / real CLI args pass through
# to main() untouched)
# =============================================================================

def _run_selftest() -> None:
    """Bare-invocation smoke test against the EXISTING smoke data in data/ (7 tasks, all P0/P1/P2
    eval, 0 calibration -- exercises fit_certs' empty-calibration fallback for real). Uses
    --dry-run so the smoke is fast, deterministic, and free of live API/model dependencies."""
    print("=" * 70)
    print("run.py self-test (--dry-run smoke over data/'s 7-task set)")
    print("=" * 70)

    out_path = os.path.join(_HERE, "results", "runs.jsonl")
    before = 0
    if os.path.exists(out_path):
        with open(out_path) as f:
            before = sum(1 for _ in f)

    main([
        "--arms", "A,B,C",
        "--seeds", "0",
        "--budget", "8000",
        "--tier", "ollama:qwen2.5-coder:7b",
        "--dry-run",
    ])

    assert os.path.exists(out_path), f"expected {out_path} to exist after main()"
    with open(out_path) as f:
        lines = f.readlines()
    new_lines = lines[before:]
    assert new_lines, "main() must append at least one new row"

    seen_arms = set()
    for line in new_lines:
        row = json.loads(line)  # raises if any appended line isn't valid JSON
        assert row["tier"] == "ollama:qwen2.5-coder:7b"
        assert "task_id" in row and "verified" in row and "submitted" in row and "tokens" in row
        seen_arms.add(row["arm"])

    assert seen_arms == {"A", "B", "C"}, f"expected rows for A, B, C; got {seen_arms}"
    print(f"\n[selftest] {len(new_lines)} new JSONL rows appended to {out_path}")
    print(f"[selftest] arms present: {sorted(seen_arms)}")
    print("\nALL SELF-TEST ASSERTIONS PASSED")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        _run_selftest()
