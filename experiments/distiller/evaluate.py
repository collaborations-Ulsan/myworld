"""experiments/distiller/evaluate.py -- the FROZEN eval (docs/AIOS_DISTILLER_PREREG_2026-07-17.md
v1.1 S3 step 5, S4, S6 guards #1 & #3).

Arms: base-student, and (only if a trained adapter is present -- see train_lora.py) each of
Student-LoRA-verified(trajectory+solution) / Student-LoRA-UNVERIFIED / Student-LoRA-solution-only.

FROZEN discipline (prereg S6 guard #3):
  * STRIPPED PROMPT: every arm, every task, uses the exact same `tasks.prompt_text(task)` used at
    collect time (collect.py imports the identical function) -- no arm ever sees extra decoration.
  * SOLUTION-ONLY SCORING: an arm's raw completion is always run through `collect.extract_code`
    before grading, discarding any reasoning/trajectory text -- a trajectory-trained arm cannot
    win by having its rationale pattern-matched, only its extracted code is ever graded.
  * B split only, held_out_tests + adversarial_tests (never A, never visible_tests) via
    experiments/learnos/verify.run_public -- reused directly, same sandboxed subprocess.
  * Sentinel: every arm is also run on the sentinel split; a LoRA arm's sentinel pass rate falling
    below the base arm's is a REGRESSION, reported plainly (prereg S6 "sentinel rehearsal" guard).
  * H2 (escalation rate, prereg S6 correction): counts ONLY successful local solves under an
    IDENTICAL token/temperature/timeout budget across every arm -- never call-count reduction.
  * Statistic: a paired ONE-SIDED EXACT test (McNemar/sign-test form) on the discordant per-task
    pairs between base and a LoRA arm, alpha=0.05, implemented via stdlib `math.comb` (no scipy).

N_verified pilot banner: read from collect.py's own `data/collect_summary.json` (the actual, live
measurement) -- never recomputed or guessed here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

_DISTILLER_DIR = Path(__file__).resolve().parent
if str(_DISTILLER_DIR) in sys.path:
    sys.path.remove(str(_DISTILLER_DIR))
sys.path.insert(0, str(_DISTILLER_DIR))

import collect  # noqa: E402 -- experiments/distiller/collect.py (call_student, extract_code, sys.path setup)
import verify  # noqa: E402 -- experiments/learnos/verify.py (path added by collect.py's import above)
import train_lora  # noqa: E402 -- experiments/distiller/train_lora.py (_cuda_kernels_usable -- see _hf_lora_caller)

# reuse collect.py's already-loaded tasks module rather than a second `import tasks` -- see
# collect.py's own comment: experiments/learnos/ ALSO ships a module literally named tasks.py,
# and a bare `import tasks` here would be vulnerable to whichever one got into sys.modules
# first in this process (verified live: broke under `pytest tests/test_learnos_s11.py
# tests/test_distiller.py` in one session even though this file's sys.path looked correct
# in isolation).
distiller_tasks = collect.distiller_tasks

DATA_DIR = _DISTILLER_DIR / "data"
N_VERIFIED_PILOT_THRESHOLD = collect.N_VERIFIED_PILOT_THRESHOLD
ALPHA = 0.05

BASE_ARM = "base"
LORA_ARMS = (
    "lora_verified_trajectory",       # Student-LoRA-verified(trajectory+solution)
    "lora_verified_solution_only",    # Student-LoRA-solution-only
    "lora_unverified_trajectory",     # Student-LoRA-UNVERIFIED (same volume, no causal gate)
)
ALL_ARMS = (BASE_ARM,) + LORA_ARMS


# ---------------------------------------------------------------------------------------------
# statistics -- stdlib-only exact paired one-sided test
# ---------------------------------------------------------------------------------------------

def paired_one_sided_exact_test(base_pass: list[bool], variant_pass: list[bool]) -> dict:
    """One-sided exact McNemar/sign test: H0 = the variant is not better than base; H1 = variant
    beats base. Discordant pairs only: n01 = base-fail/variant-pass, n10 = base-pass/variant-fail.
    p = P(X >= n01 | X ~ Binomial(n01+n10, 0.5)), stdlib math.comb (no scipy dependency)."""
    if len(base_pass) != len(variant_pass):
        raise ValueError("paired arrays must be the same length")
    n01 = sum(1 for b, v in zip(base_pass, variant_pass) if (not b) and v)   # base fail, variant pass
    n10 = sum(1 for b, v in zip(base_pass, variant_pass) if b and (not v))   # base pass, variant fail
    n = n01 + n10
    if n == 0:
        p = 1.0
    else:
        p = sum(math.comb(n, k) for k in range(n01, n + 1)) / (2 ** n)
    return {
        "n_pairs": len(base_pass), "n01_base_fail_variant_pass": n01, "n10_base_pass_variant_fail": n10,
        "n_discordant": n, "p_value_one_sided": p, "significant_at_0.05": (p < ALPHA and n01 > n10),
    }


def escalation_rate(local_solved: list[bool]) -> float:
    """H2 metric (prereg S6 correction): fraction of tasks the arm did NOT solve locally under the
    SAME budget as every other arm -- counts only successful equal-budget local solves, never a
    raw call-count reduction."""
    if not local_solved:
        return 0.0
    return 1.0 - (sum(1 for x in local_solved if x) / len(local_solved))


def sentinel_regression(base_sentinel_pass: list[bool], arm_sentinel_pass: list[bool]) -> dict:
    base_rate = (sum(base_sentinel_pass) / len(base_sentinel_pass)) if base_sentinel_pass else 1.0
    arm_rate = (sum(arm_sentinel_pass) / len(arm_sentinel_pass)) if arm_sentinel_pass else 1.0
    return {"base_rate": base_rate, "arm_rate": arm_rate, "regressed": arm_rate < base_rate}


# ---------------------------------------------------------------------------------------------
# arm callers
# ---------------------------------------------------------------------------------------------

def lora_adapter_dir(arm_name: str, out_dir: Path) -> Path:
    return out_dir / f"lora_{arm_name}"


def lora_arm_available(arm_name: str, out_dir: Path) -> bool:
    d = lora_adapter_dir(arm_name, out_dir)
    return (d / "adapter_model.safetensors").exists() or (d / "adapter_model.bin").exists()


def _hf_lora_caller(arm_name: str, out_dir: Path, base_model_id: str):
    """Build a caller(prompt) -> str backed by transformers + peft, loading the base HF model
    once and applying the LoRA adapter at `lora_adapter_dir(arm_name, out_dir)`. Only importable
    if peft is installed (see train_lora.py's NOT-RUN banner for what happens when it isn't --
    this function is simply never invoked in that case, checked by the caller via
    `trainer_available()` before calling this)."""
    import torch  # local import: heavy optional dependency, only touched when peft IS installed
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # same live-verified sm_120 (RTX 5090) kernel gap train_lora.py's _run_real_training hit --
    # see that function's docstring. Reusing train_lora._cuda_kernels_usable() rather than a
    # second copy of the same probe.
    use_cuda = train_lora._cuda_kernels_usable()
    if not use_cuda:
        arch_list = torch.cuda.get_arch_list() if torch.cuda.is_available() else []
        print(
            f"[evaluate]   GPU present but no compiled kernel for its compute capability "
            f"(torch arch_list={arch_list}) -- loading {arm_name} on CPU (slower, but real)."
        )
    device_map = "auto" if use_cuda else {"": "cpu"}
    dtype = torch.bfloat16 if use_cuda else torch.float32

    tok = AutoTokenizer.from_pretrained(base_model_id)
    base = AutoModelForCausalLM.from_pretrained(base_model_id, torch_dtype=dtype, device_map=device_map)
    model = PeftModel.from_pretrained(base, str(lora_adapter_dir(arm_name, out_dir)))
    model.eval()

    def caller(prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=collect.STUDENT_MAX_TOKENS, temperature=0.2, do_sample=False)
        return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    return caller


def trainer_available() -> bool:
    return importlib.util.find_spec("peft") is not None or importlib.util.find_spec("unsloth") is not None


def _base_student_caller(prompt: str, student_model: str) -> str:
    resp = collect.call_student(prompt, model=student_model)
    return resp["content"] if resp["ok"] else ""


def make_arm_caller(arm_name: str, out_dir: Path, student_model: str, base_model_id: str):
    if arm_name == BASE_ARM:
        return lambda prompt: _base_student_caller(prompt, student_model)
    if not trainer_available():
        return None
    if not lora_arm_available(arm_name, out_dir):
        return None
    return _hf_lora_caller(arm_name, out_dir, base_model_id)


# ---------------------------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------------------------

def score_task(task: dict, raw_output: str) -> dict:
    """Solution-only scoring (prereg guard #3): extract the code block, discard the rest, grade
    against held_out_tests + adversarial_tests ONLY (never visible_tests -- those were shown as
    the worked example in the prompt)."""
    solution = collect.extract_code(raw_output)
    priv = distiller_tasks.held_out_bundle(task)
    exprs = priv["held_out_tests"] + priv["adversarial_tests"]
    if not solution.strip() or not exprs:
        return {"solved": False, "passed": 0, "total": len(exprs)}
    r = verify.run_public(exprs, solution, timeout=collect.GRADE_TIMEOUT_S)
    return {"solved": r["all_passed"], "passed": r["passed"], "total": r["total"]}


def score_sentinel(task: dict, raw_output: str) -> bool:
    solution = collect.extract_code(raw_output)
    if not solution.strip():
        return False
    r = verify.run_public([task["sentinel_check"]], solution, timeout=collect.GRADE_TIMEOUT_S)
    return bool(r["all_passed"])


def run_arm_on_split(arm_name: str, caller, split_tasks: list[dict], log=print) -> dict:
    per_task = {}
    for task in split_tasks:
        prompt = distiller_tasks.prompt_text(task)  # the SAME stripped prompt used at collect time
        try:
            raw = caller(prompt)
        except Exception as exc:  # noqa: BLE001 -- an eval-time infra error is data, not a crash
            log(f"[evaluate]   {arm_name}/{task['task_id']} infra error: {exc}")
            raw = ""
        result = score_task(task, raw)
        per_task[task["task_id"]] = result
    return per_task


def run_arm_on_sentinel(arm_name: str, caller, sentinel_tasks: list[dict]) -> list[bool]:
    out = []
    for task in sentinel_tasks:
        prompt = distiller_tasks.prompt_text(task)
        try:
            raw = caller(prompt)
        except Exception:  # noqa: BLE001
            raw = ""
        out.append(score_sentinel(task, raw))
    return out


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------

def _read_n_verified(out_dir: Path) -> int:
    p = out_dir / "collect_summary.json"
    if not p.exists():
        return 0
    return json.loads(p.read_text(encoding="utf-8")).get("n_verified", 0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS Experience-Distiller: frozen B-split evaluation.")
    p.add_argument("--seed", type=int, default=20260717)
    p.add_argument("--b-instances", type=int, default=6)
    p.add_argument("--student-model", default=collect.STUDENT_MODEL_DEFAULT)
    p.add_argument("--base-model-id", default="Qwen/Qwen3-1.7B",
                    help="HF hub id for the LoRA arms' base weights (verified present on HF hub 2026-07-17)")
    p.add_argument("--out-dir", default=str(DATA_DIR))
    p.add_argument("--arms", nargs="*", default=None, help="subset of arms to run (default: all available)")
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    all_tasks = distiller_tasks.build_tasks(seed=args.seed, b_instances=args.b_instances)
    b_tasks = distiller_tasks.by_split(all_tasks, "B")
    sentinel_tasks = distiller_tasks.by_split(all_tasks, "sentinel")

    requested = args.arms if args.arms else list(ALL_ARMS)
    results: dict[str, dict] = {}
    sentinel_results: dict[str, list[bool]] = {}
    skipped: dict[str, str] = {}

    for arm in requested:
        caller = make_arm_caller(arm, out_dir, args.student_model, args.base_model_id)
        if caller is None:
            reason = "trainer (peft/unsloth) not installed" if not trainer_available() else "adapter not trained yet"
            skipped[arm] = reason
            print(f"[evaluate] SKIP {arm}: {reason}")
            continue
        print(f"[evaluate] running arm={arm} on {len(b_tasks)} B tasks + {len(sentinel_tasks)} sentinel tasks...")
        results[arm] = run_arm_on_split(arm, caller, b_tasks)
        sentinel_results[arm] = run_arm_on_sentinel(arm, caller, sentinel_tasks)

    base_pass_by_id = {tid: r["solved"] for tid, r in results.get(BASE_ARM, {}).items()}
    task_ids = [t["task_id"] for t in b_tasks]

    report: dict = {
        "n_b_tasks": len(b_tasks), "n_sentinel_tasks": len(sentinel_tasks),
        "arms_run": list(results.keys()), "arms_skipped": skipped,
        "n_verified_from_collect": _read_n_verified(out_dir),
        "per_arm": {}, "generated_at": time.time(),
    }
    for arm, per_task in results.items():
        solved = [per_task[tid]["solved"] for tid in task_ids]
        b_pass_rate = sum(solved) / len(solved) if solved else 0.0
        entry = {
            "b_pass_rate": b_pass_rate,
            "escalation_rate": escalation_rate(solved),
            "sentinel": sentinel_regression(sentinel_results.get(BASE_ARM, sentinel_results.get(arm, [])),
                                             sentinel_results[arm]),
        }
        if arm != BASE_ARM and base_pass_by_id:
            variant_pass = [per_task[tid]["solved"] for tid in task_ids]
            base_pass_aligned = [base_pass_by_id[tid] for tid in task_ids]
            entry["paired_vs_base"] = paired_one_sided_exact_test(base_pass_aligned, variant_pass)
        report["per_arm"][arm] = entry

    n_verified = report["n_verified_from_collect"]
    banner = collect.pilot_banner(n_verified)
    report["banner"] = banner

    print("=" * 78)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(banner)
    print("=" * 78)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evaluate_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
