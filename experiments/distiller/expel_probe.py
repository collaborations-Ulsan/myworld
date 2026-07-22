#!/usr/bin/env python3
"""ExpeL / case-retrieval probe — bet #1 of the methodology pivot (2026-07-22).

The distillation keystone wobbled (multiseed: +14.0/+1.4/-4.3pp across near-identical
LoRA draws on the same 270 verified trajectories). Three heterogeneous divergence
substrates converged: the learnable signal is in the causal control PROCESS / system,
not compressible into a small model's weights at N=270. First cheap falsification
(docs/AIOS_METHODOLOGY_DIVERGENCE_2026-07-22.md, Top-3 bet #1):

  Reuse the SAME 270 verified trajectories as a NON-WEIGHT case base. For each held-out
  B task, retrieve the top-k most similar cases (BM25, CPU, zero training) and inject
  them as worked examples into qwen3-1.7b's prompt. Compare held-out pass rate:
      base (k=0, no retrieval)  vs  ExpeL (k=2, k=3 retrieval).
  ZERO training, ZERO gradient variance — if retrieval >= the SFT arms, "compound in
  memory-space not weight-space" is earned cheaply.

Anti-reward-hacking (three-way separation): generator = qwen3-1.7b (student); the
retrieved cases are A-family verified solutions (A families are DISJOINT from B, so
retrieval can NEVER expose a B held-out solution); scorer = the frozen held_out +
adversarial tests via evaluate.score_task. Same stripped prompt, same solution-only
grading as the distiller eval — reuses evaluate.py directly, no re-implementation.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) in sys.path:
    sys.path.remove(str(HERE))
sys.path.insert(0, str(HERE))

# Pre-load the CORRECT tasks module by explicit path into sys.modules, so collect/evaluate
# (which each `import tasks`) reuse this exact instance -- avoids a shadowing 'tasks' getting
# cached first (which dropped build_tasks when run from the repo root).
_spec = importlib.util.spec_from_file_location("tasks", HERE / "tasks.py")
distiller_tasks = importlib.util.module_from_spec(_spec)
sys.modules["tasks"] = distiller_tasks
_spec.loader.exec_module(distiller_tasks)

import collect  # noqa: E402
import evaluate as ev  # noqa: E402

CASES_FILE = HERE / "data" / "confirmatory" / "sft_unverified_trajectory.jsonl"
_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tok(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25:
    """Minimal pure-Python BM25 over the case-prompt corpus (no deps, CPU)."""

    def __init__(self, docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = docs_tokens
        self.N = len(docs_tokens)
        self.avgdl = sum(len(d) for d in docs_tokens) / max(1, self.N)
        self.df: dict[str, int] = {}
        self.tf: list[dict[str, int]] = []
        for d in docs_tokens:
            counts: dict[str, int] = {}
            for t in d:
                counts[t] = counts.get(t, 0) + 1
            self.tf.append(counts)
            for t in counts:
                self.df[t] = self.df.get(t, 0) + 1

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def top_k(self, query: str, k: int, exclude_idx: int | None = None) -> list[int]:
        q = _tok(query)
        scores = []
        for i, counts in enumerate(self.tf):
            if i == exclude_idx:
                continue
            dl = len(self.docs[i])
            s = 0.0
            for term in q:
                if term not in counts:
                    continue
                f = counts[term]
                s += self._idf(term) * (f * (self.k1 + 1)) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            scores.append((s, i))
        scores.sort(reverse=True)
        return [i for _, i in scores[:k]]


def load_cases() -> list[dict]:
    cases = []
    for line in CASES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            cases.append({"prompt": r["prompt"], "solution": r["solution"], "task_id": r.get("task_id", "")})
    return cases


def make_expel_caller(k: int, cases: list[dict], bm25: BM25, student_model: str):
    """Return caller(prompt)->raw. k=0 is the base (no retrieval), identical to evaluate's base arm."""
    def caller(prompt: str) -> str:
        if k <= 0:
            resp = collect.call_student(prompt, model=student_model)
            return resp["content"] if resp["ok"] else ""
        idxs = bm25.top_k(prompt, k)
        blocks = []
        for j in idxs:
            c = cases[j]
            blocks.append(f"# Worked example (a related, solved problem)\n{c['prompt']}\n"
                          f"# Correct solution:\n```python\n{c['solution']}\n```")
        augmented = ("Here are related solved problems. Use their approach as guidance, then solve the "
                     "NEW problem. Output only the solution code.\n\n"
                     + "\n\n".join(blocks)
                     + f"\n\n# NEW problem to solve\n{prompt}")
        resp = collect.call_student(augmented, model=student_model)
        return resp["content"] if resp["ok"] else ""
    return caller


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ExpeL case-retrieval probe (bet #1)")
    p.add_argument("--b-instances", type=int, default=15, help="B held-out size = 6*b_instances")
    p.add_argument("--seed", type=int, default=20260717)
    p.add_argument("--ks", type=int, nargs="*", default=[0, 2, 3], help="retrieval depths to compare")
    p.add_argument("--student-model", default=collect.STUDENT_MODEL_DEFAULT)
    p.add_argument("--out", default=str(HERE / "data" / "confirmatory" / "expel_probe_report.json"))
    args = p.parse_args(argv)

    cases = load_cases()
    bm25 = BM25([_tok(c["prompt"]) for c in cases])
    all_tasks = distiller_tasks.build_tasks(seed=args.seed, b_instances=args.b_instances)
    b_tasks = distiller_tasks.by_split(all_tasks, "B")
    print(f"[expel] {len(cases)} cases, {len(b_tasks)} B held-out tasks, ks={args.ks}", flush=True)

    per_arm: dict[str, dict] = {}
    for k in args.ks:
        arm = f"base" if k == 0 else f"expel_k{k}"
        t0 = time.time()
        caller = make_expel_caller(k, cases, bm25, args.student_model)
        per_task = ev.run_arm_on_split(arm, caller, b_tasks, log=lambda *a: None)
        solved = [per_task[t["task_id"]]["solved"] for t in b_tasks]
        rate = sum(solved) / len(solved) if solved else 0.0
        per_arm[arm] = {"k": k, "rate": rate, "n": len(solved),
                        "solved_by_id": {t["task_id"]: per_task[t["task_id"]]["solved"] for t in b_tasks}}
        print(f"[expel] {arm}: {sum(solved)}/{len(solved)} = {rate:.3f}  ({time.time()-t0:.0f}s)", flush=True)

    base = per_arm.get("base")
    report = {"n_b": len(b_tasks), "n_cases": len(cases), "arms": {}}
    for arm, d in per_arm.items():
        entry = {"k": d["k"], "rate": d["rate"], "n": d["n"]}
        if base and arm != "base":
            bp = [base["solved_by_id"][t["task_id"]] for t in b_tasks]
            vp = [d["solved_by_id"][t["task_id"]] for t in b_tasks]
            test = ev.paired_one_sided_exact_test(bp, vp)
            entry["vs_base_pp"] = round((d["rate"] - base["rate"]) * 100, 1)
            entry["p_value"] = test.get("p_value_one_sided")
            entry["significant"] = test.get("significant_at_0.05")
        report["arms"][arm] = entry
    Path(args.out).write_text(json.dumps(report, indent=2))
    print("\n=== EXPEL PROBE ===", flush=True)
    print(json.dumps(report["arms"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
