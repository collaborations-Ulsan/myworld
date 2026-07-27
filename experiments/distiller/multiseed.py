#!/usr/bin/env python3
"""Multi-seed distillation variance probe (2026-07-22).

Big-B (N_B=300) showed the two trajectory arms -- identical 270 (prompt->target)
pairs, differing only in RNG -- diverge +14.0pp (sig) vs +1.4pp (ns). That is
training stochasticity, not a data-content or causal-gate effect (verified in
train_lora: --seed now controls split+init+data order). This probe samples that
variance: train arm=lora_unverified_trajectory across K seeds, eval each on the
SAME N_B=300 held-out vs the SAME base, report the pass-rate distribution.

Verdict rule (no-launder): if mean arm-rate stays significantly > base across
seeds -> distillation robustly works (EARN effect size). If it scatters widely
-> weak/unstable signal. Either way, report the distribution straight.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONF = HERE / "data" / "confirmatory"
ARM = "lora_unverified_trajectory"
SFT = "sft_unverified_trajectory.jsonl"
B_INSTANCES = 50           # 6 families x 50 -> N_B=300 (matches big-B)
EVAL_SEED = 20260717       # FIXED -> identical 300 B tasks + identical base every seed
SEEDS = [int(s) for s in (sys.argv[1:] or ["1", "2", "3", "4", "5"])]
ROOT = CONF / "multiseed"


def run(cmd: list[str], log: Path) -> float:
    t0 = time.time()
    with log.open("w") as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(HERE.parent.parent))
    dt = time.time() - t0
    if p.returncode != 0:
        print(f"  !! FAILED rc={p.returncode} (see {log})", flush=True)
    return dt


def parse_report(report_path: Path, arm: str) -> dict:
    rep = json.loads(report_path.read_text())
    pa = rep["per_arm"]
    base = pa.get("base", {})
    a = pa.get(arm, {})
    paired = a.get("paired_vs_base", {})
    base_rate = base.get("b_pass_rate")
    arm_rate = a.get("b_pass_rate")
    return {
        "n_b": rep.get("n_b_tasks"),
        "base_rate": base_rate,
        "arm_rate": arm_rate,
        "delta_pp": (None if (arm_rate is None or base_rate is None) else round((arm_rate - base_rate) * 100, 1)),
        "p_value": paired.get("p_value_one_sided"),
        "significant": paired.get("significant_at_0.05"),
        "n_pairs": paired.get("n_pairs"),
        "escalation_rate": a.get("escalation_rate"),
        "sentinel_regressed": (a.get("sentinel") or {}).get("regressed"),
    }


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for seed in SEEDS:
        sdir = ROOT / f"seed{seed}"
        sdir.mkdir(parents=True, exist_ok=True)
        shutil.copy(CONF / SFT, sdir / SFT)
        print(f"[seed {seed}] train arm={ARM} ...", flush=True)
        t_train = run(
            [sys.executable, str(HERE / "train_lora.py"), "--arm", ARM,
             "--out-dir", str(sdir), "--seed", str(seed), "--epochs", "3"],
            sdir / "train.log",
        )
        adapter = sdir / f"lora_{ARM}"
        has_adapter = (adapter / "adapter_model.safetensors").exists() or (adapter / "adapter_model.bin").exists()
        print(f"[seed {seed}] train done in {t_train:.0f}s (adapter={'ok' if has_adapter else 'MISSING'}); eval N_B~300 ...", flush=True)
        t_eval = run(
            [sys.executable, str(HERE / "evaluate.py"), "--arms", "base", ARM,
             "--out-dir", str(sdir), "--b-instances", str(B_INSTANCES), "--seed", str(EVAL_SEED)],
            sdir / "eval.log",
        )
        report = sdir / "evaluate_report.json"
        row = {"seed": seed, "t_train_s": round(t_train), "t_eval_s": round(t_eval)}
        if report.exists():
            row.update(parse_report(report, ARM))
        else:
            row["error"] = "no report"
        results.append(row)
        print(f"[seed {seed}] {json.dumps(row)}", flush=True)
        (ROOT / "multiseed_results.json").write_text(json.dumps(results, indent=2))

    # summary
    deltas = [r["delta_pp"] for r in results if r.get("delta_pp") is not None]
    if deltas:
        n = len(deltas); mean = sum(deltas)/n
        var = sum((d-mean)**2 for d in deltas)/(n-1) if n > 1 else 0.0
        sd = var**0.5
        print("\n=== MULTISEED SUMMARY ===", flush=True)
        print(f"seeds={[r['seed'] for r in results]} deltas_pp={deltas}", flush=True)
        print(f"mean={mean:.1f}pp sd={sd:.1f}pp min={min(deltas)} max={max(deltas)} n_sig={sum(1 for r in results if r.get('significant'))}/{n}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
