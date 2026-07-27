"""experiments/distiller/train_lora.py -- LoRA/QLoRA on the student from collect.py's SFT sets
(docs/AIOS_DISTILLER_PREREG_2026-07-17.md v1.1 S3 step 4, S6 guards #2 & "Sentinel 보호").

Four arms (prereg S6 guard #2 -- the two controls are the DECISIVE part of this experiment, not
an afterthought):
  * base                          -- no training, collect.call_student directly (evaluate.py only)
  * lora_verified_trajectory      -- causal-gate-VERIFIED records, {prompt -> trajectory+solution}
  * lora_verified_solution_only   -- the SAME verified records,    {prompt -> solution only}
  * lora_unverified_trajectory    -- SAME tasks/teacher volume, NO causal gate, {prompt -> trajectory+solution}

Sentinel rehearsal (prereg S6): every training set is mixed with sentinel (task, golden_solution)
examples at SENTINEL_REHEARSAL_FRACTION (10-20%) so an arm cannot "improve" by trading away
existing base capability -- evaluate.py's sentinel_regression() is the check that this worked.

If neither `peft` nor `unsloth` is importable (checked live, not assumed) this module does NOT
silently skip: it still exports each arm's exact training file (sentinel-mixed jsonl) and prints
the exact documented train command, then a clear "NOT-RUN" banner -- run_distiller.py's summary
carries this state through honestly. When a trainer IS present, `main()` actually runs it.

Base weights for real training: Qwen/Qwen3-1.7B (verified present on HF hub 2026-07-17 via
mcp__claude_ai_Hugging_Face -- NOT the ollama GGUF blob qwen3:1.7b used for inference; GGUF is not
peft/transformers-trainable, HF safetensors are a separate download for this step only).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

_DISTILLER_DIR = Path(__file__).resolve().parent
if str(_DISTILLER_DIR) in sys.path:
    sys.path.remove(str(_DISTILLER_DIR))
sys.path.insert(0, str(_DISTILLER_DIR))

# experiments/learnos/ ALSO ships a module literally named tasks.py -- a bare `import tasks`
# is unsafe if anything in this process already cached sys.modules["tasks"] from that other
# package (sys.modules wins over sys.path reordering; see collect.py's identical comment for
# the live-verified failure mode). This module deliberately does NOT import collect.py (which
# would pull in the heavier aios_adapters/verify/causal_gate/audit chain just to reach `tasks`
# -- train_lora.py only ever needs task text + golden solutions for dataset export), so it
# loads tasks.py under the same private, collision-proof sys.modules key collect.py uses.
_TASKS_MODULE_KEY = "aios_distiller_tasks"
if _TASKS_MODULE_KEY in sys.modules:
    distiller_tasks = sys.modules[_TASKS_MODULE_KEY]
else:
    import importlib.util as _importlib_util
    _spec = _importlib_util.spec_from_file_location(_TASKS_MODULE_KEY, _DISTILLER_DIR / "tasks.py")
    distiller_tasks = _importlib_util.module_from_spec(_spec)
    sys.modules[_TASKS_MODULE_KEY] = distiller_tasks
    _spec.loader.exec_module(distiller_tasks)

DATA_DIR = _DISTILLER_DIR / "data"
BASE_MODEL_ID_DEFAULT = "Qwen/Qwen3-1.7B"
SENTINEL_REHEARSAL_FRACTION = 0.15  # prereg S6: "10-20%"
EARLY_STOP_PATIENCE = 2

ARM_DATASET_FILES = {
    "lora_verified_trajectory": "sft_verified_trajectory.jsonl",
    "lora_verified_solution_only": "sft_verified_solution_only.jsonl",
    "lora_unverified_trajectory": "sft_unverified_trajectory.jsonl",
}


def trainer_available() -> bool:
    return importlib.util.find_spec("peft") is not None or importlib.util.find_spec("unsloth") is not None


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _target_text(record: dict, arm: str) -> str:
    if arm == "lora_verified_solution_only":
        return record["solution"]
    return record.get("trajectory") or record["solution"]


def build_training_examples(
    arm: str, out_dir: Path = DATA_DIR, seed: int = 1,
    sentinel_fraction: float = SENTINEL_REHEARSAL_FRACTION,
) -> list[dict]:
    """{prompt, target} pairs for `arm`, sentinel-rehearsal-mixed. Deterministic given `seed` --
    pure data prep, runs (and is tested) with no trainer installed."""
    dataset_path = out_dir / ARM_DATASET_FILES[arm]
    records = _read_jsonl(dataset_path)
    examples = [{"prompt": r["prompt"], "target": _target_text(r, arm), "source": "distilled"} for r in records]

    all_tasks = distiller_tasks.build_tasks(seed=seed)
    sentinel_tasks = distiller_tasks.by_split(all_tasks, "sentinel")
    sentinel_examples = [
        {
            "prompt": distiller_tasks.prompt_text(t),
            "target": f"```python\n{distiller_tasks.held_out_bundle(t)['golden_solution']}```",
            "source": "sentinel_rehearsal",
        }
        for t in sentinel_tasks
    ]
    if not examples or not sentinel_examples:
        return examples + sentinel_examples

    rng = random.Random(f"aios-distiller:sentinel-mix:{seed}:{arm}")
    n_total_target = max(len(examples), 1)
    n_sentinel = max(1, round(sentinel_fraction / (1 - sentinel_fraction) * n_total_target))
    mixed_sentinel = [rng.choice(sentinel_examples) for _ in range(n_sentinel)]
    combined = examples + mixed_sentinel
    rng.shuffle(combined)
    return combined


def export_arm_dataset(arm: str, out_dir: Path = DATA_DIR, seed: int = 1) -> Path:
    examples = build_training_examples(arm, out_dir, seed=seed)
    export_path = out_dir / f"train_{arm}.jsonl"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, sort_keys=True) + "\n")
    return export_path


def documented_train_command(arm: str, out_dir: Path, base_model_id: str) -> str:
    dataset = out_dir / f"train_{arm}.jsonl"
    adapter_out = out_dir / f"lora_{arm}"
    return (
        f"python experiments/distiller/train_lora.py --arm {arm} --base-model-id {base_model_id} "
        f"--dataset {dataset} --output {adapter_out} --epochs 3 "
        f"--sentinel-fraction {SENTINEL_REHEARSAL_FRACTION} --early-stopping-patience {EARLY_STOP_PATIENCE}\n"
        "  # underlying recipe (once `pip install peft transformers accelerate` or unsloth is "
        f"available): base={base_model_id} (HF safetensors, NOT the ollama GGUF blob) + "
        "peft.LoraConfig(r=16, lora_alpha=32, target_modules=[q_proj,k_proj,v_proj,o_proj,"
        "gate_proj,up_proj,down_proj], lora_dropout=0.05) + transformers.Trainer with "
        f"load_best_model_at_end=True, early_stopping_patience={EARLY_STOP_PATIENCE}, "
        f"a held-out 10% split of {dataset.name} as eval_dataset (sentinel-rehearsal examples "
        "included in both train and eval so an early stop that trades sentinel for A/B gain is "
        "caught, not rewarded)."
    )


def _cuda_kernels_usable() -> bool:
    """True iff a CUDA device is visible AND this torch build actually has a compiled kernel for
    its compute capability. `torch.cuda.is_available()` alone is NOT sufficient -- live-verified
    2026-07-18 on this box: torch 2.6.0+cu124 enumerates the RTX 5090 fine (is_available()=True,
    device count/name all correct) but ships no compiled kernel for its sm_120 (Blackwell,
    compute capability (12, 0)) architecture -- `torch.cuda.get_arch_list()` tops out at sm_90 --
    so a real kernel launch (peft's adapter dtype cast, the first op that isn't pure allocation)
    raises 'CUDA error: no kernel image is available for execution on the device', well after
    model loading has already spent GPU time/memory. Checked live rather than assumed."""
    import torch  # noqa: PLC0415 -- local import: heavy optional dependency
    if not torch.cuda.is_available():
        return False
    try:
        major, minor = torch.cuda.get_device_capability(0)
        return f"sm_{major}{minor}" in torch.cuda.get_arch_list()
    except Exception:  # noqa: BLE001 -- any probe failure means "don't trust this device"
        return False


def _run_real_training(arm: str, dataset_path: Path, output_dir: Path, base_model_id: str, epochs: int, seed: int = 1) -> dict:
    """Actual peft/transformers LoRA SFT loop. Only ever called when trainer_available() is True
    (gated in main()) -- never imported/executed otherwise, so this module still loads cleanly
    with zero optional dependencies installed."""
    import torch  # noqa: PLC0415 -- local import: heavy optional dependency
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling,
        EarlyStoppingCallback, Trainer, TrainingArguments,
    )

    examples = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rng = random.Random(f"aios-distiller:split:{arm}:{seed}")
    rng.shuffle(examples)
    n_eval = max(1, len(examples) // 10)
    eval_examples, train_examples = examples[:n_eval], examples[n_eval:]

    tok = AutoTokenizer.from_pretrained(base_model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def _tokenize(batch):
        texts = [f"{p}\n{t}{tok.eos_token}" for p, t in zip(batch["prompt"], batch["target"])]
        return tok(texts, truncation=True, max_length=1024)

    train_ds = Dataset.from_list(train_examples).map(_tokenize, batched=True, remove_columns=["prompt", "target", "source"])
    eval_ds = Dataset.from_list(eval_examples).map(_tokenize, batched=True, remove_columns=["prompt", "target", "source"])

    use_cuda = _cuda_kernels_usable()
    if not use_cuda:
        arch_list = torch.cuda.get_arch_list() if torch.cuda.is_available() else []
        print(
            f"[train_lora]   GPU present but no compiled kernel for its compute capability "
            f"(torch arch_list={arch_list}) -- falling back to CPU training (slower, but a real "
            f"trained adapter, not a faked/skipped one)."
        )
    device_map = "auto" if use_cuda else {"": "cpu"}
    dtype = torch.bfloat16 if use_cuda else torch.float32

    model = AutoModelForCausalLM.from_pretrained(base_model_id, torch_dtype=dtype, device_map=device_map)
    lora_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)

    args = TrainingArguments(
        output_dir=str(output_dir), num_train_epochs=epochs, per_device_train_batch_size=2,
        gradient_accumulation_steps=8, learning_rate=2e-4, logging_steps=10,
        eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
        metric_for_best_model="eval_loss", report_to=[], use_cpu=not use_cuda,
        seed=seed, data_seed=seed,
    )
    trainer = Trainer(
        model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds,
        data_collator=DataCollatorForLanguageModeling(tok, mlm=False),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=EARLY_STOP_PATIENCE)],
    )
    train_result = trainer.train()
    model.save_pretrained(str(output_dir))
    return {"train_loss": train_result.training_loss, "n_train": len(train_examples), "n_eval": len(eval_examples)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS Experience-Distiller: LoRA training (or documented plan).")
    p.add_argument("--arm", choices=list(ARM_DATASET_FILES), default=None, help="train one arm; default: all")
    p.add_argument("--out-dir", default=str(DATA_DIR))
    p.add_argument("--base-model-id", default=BASE_MODEL_ID_DEFAULT)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    arms = [args.arm] if args.arm else list(ARM_DATASET_FILES)
    available = trainer_available()

    plan = {"trainer_available": available, "arms": {}}
    for arm in arms:
        export_path = export_arm_dataset(arm, out_dir, seed=args.seed)
        n_examples = sum(1 for _ in export_path.open(encoding="utf-8"))
        entry = {"dataset_path": str(export_path), "n_examples": n_examples,
                  "train_command": documented_train_command(arm, out_dir, args.base_model_id)}
        if available and n_examples > 1:
            print(f"[train_lora] trainer present -- running real LoRA SFT for arm={arm} ({n_examples} examples)")
            entry["result"] = _run_real_training(arm, export_path, out_dir / f"lora_{arm}", args.base_model_id, args.epochs, seed=args.seed)
            entry["status"] = "trained"
        else:
            entry["status"] = "NOT-RUN"
        plan["arms"][arm] = entry

    print("=" * 78)
    if not available:
        print("NOT-RUN: neither `peft` nor `unsloth` is installed in this environment.")
        print("Dataset export + the exact documented train command for each arm follow -- ")
        print("no LoRA weights were produced by this invocation.")
    print(json.dumps(plan, indent=2, sort_keys=True))
    print("=" * 78)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "train_lora_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
