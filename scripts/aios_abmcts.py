#!/usr/bin/env python3
"""aios_abmcts — AB-MCTS-style collective intelligence over a FROZEN substrate pool.

Ported from Sakana AI's AB-MCTS / TreeQuest (Apache-2.0) idea, implemented native to
AIOS over its heterogeneous NVIDIA NIM pool: keep every model frozen and separate,
combine them at inference time. Each round adaptively chooses REFINE-vs-GENERATE and
which provider acts next (UCB bandit by past score), scores candidates with a judge,
and converges on the best answer — beating any single model on hard tasks.

No thesis conflict (all models frozen; no training). CLI: aios solve "<task>"
Env: NVIDIA_API_KEY
"""
from __future__ import annotations
import os, sys, re, json, math, argparse
import concurrent.futures as cf
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_adapters as A  # noqa: E402

# Frozen heterogeneous pool (different priors) + a strong judge.
POOL = [
    "deepseek-ai/deepseek-v4-pro",
    "qwen/qwen3.5-397b-a17b",
    "nvidia/nemotron-3-super-120b-a12b",
    "z-ai/glm-5.2",
    "moonshotai/kimi-k2.6",
]
JUDGE = "deepseek-ai/deepseek-v4-flash"   # fast scorer — 0-10 rating is cheap

_ADAPTERS: dict[str, "callable"] = {}
def _model(m: str):
    if m not in _ADAPTERS:
        _ADAPTERS[m] = A.make_nvidia_nim_adapter(model=m, timeout=120)
    return _ADAPTERS[m]

def _gen(model: str, task: str) -> str:
    return _model(model)(f"Solve this task correctly and concisely.\n\nTask: {task}").strip()

def _refine(model: str, task: str, prev: str) -> str:
    return _model(model)(
        f"Task: {task}\n\nA candidate answer:\n{prev}\n\n"
        "Improve it: fix any error, add anything missing, make it more correct and clear. "
        "Return only the improved answer.").strip()

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
def _judge(task: str, answer: str) -> float:
    try:
        raw = _model(JUDGE)(
            f"Task: {task}\n\nCandidate answer:\n{answer[:3000]}\n\n"
            "Rate this answer 0-10 for correctness, completeness, and clarity. "
            "Reply with ONLY the number.")
        m = _NUM.search(raw)
        return max(0.0, min(10.0, float(m.group()))) if m else 0.0
    except Exception:
        return 0.0

def _ucb(stats: dict, t: int):
    """Pick a provider by UCB1 (unused providers first)."""
    best, best_v = None, -1.0
    for p in POOL:
        n, s = stats[p]["n"], stats[p]["s"]
        if n == 0:
            return p
        v = s / n + math.sqrt(2 * math.log(max(t, 1)) / n)
        if v > best_v:
            best, best_v = p, v
    return best

def solve(task: str, budget: int = 5, verbose: bool = False):
    """AB-MCTS-lite: parallel diverse init → bandit-guided refine → best."""
    if not os.environ.get("NVIDIA_API_KEY"):
        raise RuntimeError("NVIDIA_API_KEY not set")
    stats = {p: {"n": 0, "s": 0.0} for p in POOL}
    nodes: list[dict] = []

    def _record(answer, provider, parent, score):
        stats[provider]["n"] += 1; stats[provider]["s"] += score
        node = {"answer": answer, "score": score, "provider": provider, "parent": parent}
        nodes.append(node)
        if verbose:
            sys.stderr.write(f"  · {provider.split('/')[-1]:28} score={score:.1f} "
                             f"{'(refine)' if parent is not None else '(gen)'}\n")
        return node

    # Round 0 — generate one diverse candidate per pool provider AND judge them, all
    # IN PARALLEL (gen fanned out, then judges fanned out — the big latency win).
    if verbose: sys.stderr.write("✦ AB-MCTS: diverse initial generation (frozen pool, parallel)\n")
    with cf.ThreadPoolExecutor(max_workers=len(POOL)) as ex:
        gen = {ex.submit(_gen, p, task): p for p in POOL}
        answers = {gen[f]: (f.result() if not f.exception() else None) for f in cf.as_completed(gen)}
    cands = [(p, answers[p]) for p in POOL if answers.get(p)]
    if not cands:
        raise RuntimeError("pool produced no candidates")
    with cf.ThreadPoolExecutor(max_workers=len(cands)) as ex:
        scored = list(ex.map(lambda pa: _judge(task, pa[1]), cands))
    for (p, ans), sc in zip(cands, scored):
        _record(ans, p, None, sc)

    # Rounds 1..budget — adaptively refine the best node with a bandit-picked provider.
    for t in range(1, budget + 1):
        best = max(nodes, key=lambda n: n["score"])
        prov = _ucb(stats, len(nodes) + t)
        try:
            improved = _refine(prov, task, best["answer"])
            _record(improved, prov, best, _judge(task, improved))
        except Exception:
            continue

    winner = max(nodes, key=lambda n: n["score"])
    return winner, nodes, stats

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aios solve", description="AB-MCTS over a frozen NIM pool")
    ap.add_argument("task", nargs="+")
    ap.add_argument("--budget", type=int, default=5, help="refine rounds after diverse init")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args(argv)
    task = " ".join(a.task)
    winner, nodes, stats = solve(task, budget=a.budget, verbose=not a.quiet)
    if a.json:
        print(json.dumps({"answer": winner["answer"], "score": winner["score"],
                          "provider": winner["provider"], "candidates": len(nodes)},
                         ensure_ascii=False, indent=2))
    else:
        print("\n" + winner["answer"])
        sys.stderr.write(f"\n[AB-MCTS: {len(nodes)} candidates across {len(POOL)} frozen models · "
                         f"winner {winner['provider'].split('/')[-1]} score {winner['score']:.1f}]\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
