#!/usr/bin/env python3
"""aios_escalate — hard-task ESCALATION ORGAN (Sakana AB-MCTS / TreeQuest).

Masterplan §4 M5/D7-10 (docs/AIOS_OSS_ABSORPTION_SURVEY_2026-07-10.md, "최소
흡수 경로" step 4): when a task fails or is flagged hard, run adaptive
multi-model tree search over a pool of generators — scored by an injected
verifier callback — instead of leaning on one strong model. This is the
founder-directed "small models orchestrated > single strong model" organ.

Dependency: `pip install treequest` (Sakana AI, Apache-2.0, pure Python;
https://github.com/SakanaAI/treequest). Verified installed on this box
(treequest==0.3.2, 2026-07-10/11) — `tq.ABMCTSA()` + `tq.top_k()` are used
directly. If the import is unavailable at runtime, this module falls back to
a compact, HONESTLY-WEAKER approximation (`_fallback_search`): a UCB1 bandit
over generators plus a 50/50 expand-fresh-vs-deepen-best choice, with no
Thompson-sampling posterior over per-generator score distributions. Every
result carries an `engine` field naming which path ran.

File-ownership note: another executor owns scripts/aios_adapters.py,
aios_tools.py, aios_head.py, aios_llm_client.py for this work item. This
module therefore does NOT import any of them — `make_default_generators()`
below duplicates a tiny stdlib-only OpenAI-compat POST helper instead of
reusing aios_llm_client.LLMClient, by design, to avoid touching (or racing)
files owned elsewhere. `EscalationOrgan` itself takes generator callables via
dependency injection and has zero AIOS imports at all.

Public API:
    EscalationOrgan(generators, score_fn).escalate(goal, budget=16) -> dict
    make_default_generators() -> dict[str, Callable[[str], str]]

CLI:
    python3 scripts/aios_escalate.py "goal" [--budget N]
    (uses a demo length-capped scorer — see `_demo_scorer`; real callers
    inject a real verifier via the EscalationOrgan constructor.)

Schema: aios.escalate.v1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

try:
    import treequest as _tq
    _HAVE_TREEQUEST = True
except ImportError:  # pragma: no cover — exercised via monkeypatch in tests
    _tq = None
    _HAVE_TREEQUEST = False

GeneratorFn = Callable[[str], str]     # prompt -> answer text (may raise)
ScoreFn = Callable[[str], float]       # answer -> score in [0, 1]


# ---------------------------------------------------------------------------
# Node / provenance
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Node:
    """One generation. `id` indexes into the run's provenance list, so the
    whole tree is reconstructable from `parent_id` chains alone."""
    id: int
    answer: str
    score: float
    generator: str
    parent_id: Optional[int]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


class AllGeneratorsDownError(RuntimeError):
    """Raised (and converted to a named-failure dict) when every configured
    generator failed on every attempt — there is no honest best_answer."""


# ---------------------------------------------------------------------------
# Escalation organ
# ---------------------------------------------------------------------------

class EscalationOrgan:
    """Adaptive multi-generator search, scored by an injected verifier.

    `generators` maps a provenance label -> a plain prompt->answer callable
    (may raise on failure; escalate() catches and records that cleanly).
    `score_fn` maps an answer -> a score in [0, 1] (a verifier callback —
    dependency-injected, no hard AIOS import here).
    """

    def __init__(self, generators: dict[str, GeneratorFn], score_fn: ScoreFn):
        if not generators:
            raise ValueError("EscalationOrgan needs at least one generator")
        self.generators = dict(generators)
        self.score_fn = score_fn

    def escalate(self, goal: str, budget: int = 16) -> dict:
        """Run up to `budget` generations (one per tree-search step) and
        return the best answer found, with full provenance. Never raises for
        ordinary generator failures — a total wipeout comes back as an
        honest named failure dict (`error: "all_generators_down"`) instead
        of a fabricated best_answer.
        """
        if budget < 1:
            raise ValueError("budget must be >= 1")

        provenance: list[dict] = []
        dead: set[str] = set()

        def _refine_prompt(parent: _Node) -> str:
            return (
                f"{goal}\n\n--- Previous attempt (score {parent.score:.2f}) ---\n"
                f"{parent.answer}\n\n"
                "Improve this answer: fix any error, fill in anything missing, "
                "make it more correct and clear. Return only the improved answer."
            )

        def _make_gen(name: str, raw: GeneratorFn):
            def _gen(parent_state: "Optional[_Node]"):
                node_id = len(provenance)
                parent_id = parent_state.id if parent_state is not None else None
                if name in dead:
                    provenance.append({
                        "id": node_id, "generator": name, "score": 0.0,
                        "parent_id": parent_id, "ok": False,
                        "error": "skipped (generator failed earlier this run)",
                    })
                    return _Node(node_id, "", 0.0, name, parent_id), 0.0
                prompt = goal if parent_state is None else _refine_prompt(parent_state)
                try:
                    answer = raw(prompt)
                    score = _clamp01(self.score_fn(answer))
                    provenance.append({
                        "id": node_id, "generator": name, "score": score,
                        "parent_id": parent_id, "ok": True, "error": None,
                    })
                    return _Node(node_id, answer, score, name, parent_id), score
                except Exception as exc:  # noqa: BLE001 — any generator failure is non-fatal here
                    dead.add(name)
                    provenance.append({
                        "id": node_id, "generator": name, "score": 0.0,
                        "parent_id": parent_id, "ok": False, "error": str(exc)[:200],
                    })
                    return _Node(node_id, "", 0.0, name, parent_id), 0.0
            return _gen

        action_map = {name: _make_gen(name, raw) for name, raw in self.generators.items()}

        if _HAVE_TREEQUEST:
            engine = "treequest.ABMCTSA"
            algo = _tq.ABMCTSA()
            tree = algo.init_tree()
            for _ in range(budget):
                tree = algo.step(tree, action_map)
            pairs = _tq.top_k(tree, algo, k=1)
            best_node, best_score = pairs[0] if pairs else (None, 0.0)
        else:
            engine = "fallback (treequest-unavailable): UCB1 bandit + expand-or-deepen"
            best_node, best_score = _fallback_search(action_map, budget)

        ok_entries = [e for e in provenance if e["ok"]]
        if not ok_entries:
            return {
                "error": "all_generators_down",
                "detail": (
                    f"{len(self.generators)} generator(s) configured; every "
                    "attempt failed — no honest best_answer to return."
                ),
                "generators": sorted(self.generators.keys()),
                "engine": engine,
                "provenance": provenance,
                "budget_used": len(provenance),
            }

        by_gen: dict[str, dict] = {}
        for e in provenance:
            d = by_gen.setdefault(e["generator"], {"n": 0, "ok_n": 0, "sum_score": 0.0, "best_score": 0.0})
            d["n"] += 1
            if e["ok"]:
                d["ok_n"] += 1
                d["sum_score"] += e["score"]
                d["best_score"] = max(d["best_score"], e["score"])

        provider_breakdown = {
            g: {
                "generations": d["n"],
                "successes": d["ok_n"],
                "avg_score": round(d["sum_score"] / d["ok_n"], 4) if d["ok_n"] else 0.0,
                "best_score": d["best_score"],
            }
            for g, d in by_gen.items()
        }

        tree_stats = {
            "total_generations": len(provenance),
            "nodes_per_generator": {g: d["n"] for g, d in by_gen.items()},
            "engine": engine,
        }

        return {
            "best_answer": best_node.answer if best_node else "",
            "best_score": best_score,
            "tree_stats": tree_stats,
            "provider_breakdown": provider_breakdown,
            "budget_used": len(provenance),
            "generators_down": sorted(dead),
            "provenance": provenance,
            "engine": engine,
        }


# ---------------------------------------------------------------------------
# treequest-unavailable fallback (honestly weaker than real AB-MCTS)
# ---------------------------------------------------------------------------

def _fallback_search(action_map: "dict[str, Callable]", budget: int) -> "tuple[Optional[_Node], float]":
    """UNIFORM-BANDIT FALLBACK — used only when `import treequest` fails.

    Approximates AB-MCTS with: (1) a UCB1 bandit over generators (untried
    generators first, then explore/exploit by observed mean score) instead
    of treequest's Thompson-sampling posterior over per-generator score
    distributions, and (2) a coin-flip choice between generating a fresh
    root-level candidate and deepening (refining) the best node seen so far,
    instead of a learned expand-vs-deepen policy. This is a DELIBERATELY
    SIMPLER, WEAKER search — labelled honestly via the `engine` field in the
    result, never presented as equivalent to real AB-MCTS.
    """
    names = list(action_map.keys())
    stats = {n: {"n": 0, "s": 0.0} for n in names}
    all_nodes: list[_Node] = []
    best: Optional[_Node] = None
    best_score = -1.0

    def _pick(t: int) -> str:
        for n in names:
            if stats[n]["n"] == 0:
                return n
        return max(
            names,
            key=lambda n: stats[n]["s"] / stats[n]["n"] + math.sqrt(2 * math.log(t) / stats[n]["n"]),
        )

    for t in range(1, budget + 1):
        name = _pick(t)
        gen_fn = action_map[name]
        parent = None
        if all_nodes and random.random() < 0.5:
            parent = max(all_nodes, key=lambda nd: nd.score)
        node, score = gen_fn(parent)
        stats[name]["n"] += 1
        stats[name]["s"] += score
        all_nodes.append(node)
        if score > best_score:
            best, best_score = node, score

    return best, max(best_score, 0.0)


# ---------------------------------------------------------------------------
# Default generator pool — this box, live, DI-only (no aios_* imports)
# ---------------------------------------------------------------------------

_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
_NIM_ENV_FILE = Path.home() / ".config" / "nvidia" / "api.env"
_DEFAULT_NIM_POOL = "qwen/qwen3.5-397b-a17b,nvidia/nemotron-3-ultra-550b-a55b"
_DEFAULT_OLLAMA_MODEL = "qwen3-coder:30b"
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"


def _read_nvidia_api_key() -> str:
    """Resolve NVIDIA_API_KEY at CALL TIME: env first, else ~/.config/nvidia/
    api.env. Never logged, printed, returned, or committed — used only in an
    Authorization header (same discipline as scripts/aios_llm_client.py, not
    imported from here per the file-ownership constraint on this task)."""
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if key:
        return key
    try:
        text = _NIM_ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if line.startswith("NVIDIA_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _post_chat(base_url: str, headers: dict, model: str, prompt: str, timeout: int) -> str:
    """Minimal stdlib-only OpenAI-compatible /chat/completions POST. The one
    HTTP transport this module uses for its default pool."""
    body = json.dumps({
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed OpenAI-compat endpoints
        data = json.loads(resp.read())
    choice = (data.get("choices") or [{}])[0]
    return (choice.get("message") or {}).get("content") or ""


def make_default_generators(*, ollama_timeout: int = 90, nim_timeout: int = 90) -> "dict[str, GeneratorFn]":
    """Build the escalation pool from what's live on THIS box: local ollama
    (AIOS_OLLAMA_MODEL, default qwen3-coder:30b) plus NVIDIA NIM big models
    (AIOS_NIM_POOL, comma-separated, default two models verified answering on
    this box 2026-07-10). A down endpoint is not probed here — it is marked
    dead cleanly on its first failed call inside EscalationOrgan.escalate()
    and skipped (recorded, not fatal) for the rest of that run.
    """
    gens: "dict[str, GeneratorFn]" = {}

    ollama_model = os.environ.get("AIOS_OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)
    ollama_base = os.environ.get("AIOS_OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)

    def _ollama_gen(prompt: str, _model=ollama_model, _base=ollama_base) -> str:
        return _post_chat(_base, {}, _model, prompt, ollama_timeout)

    gens[f"local:{ollama_model}"] = _ollama_gen

    nim_pool = [m.strip() for m in os.environ.get("AIOS_NIM_POOL", _DEFAULT_NIM_POOL).split(",") if m.strip()]
    for model in nim_pool:
        def _nim_gen(prompt: str, _model=model) -> str:
            key = _read_nvidia_api_key()
            if not key:
                raise RuntimeError("NVIDIA_API_KEY not configured")
            return _post_chat(_NIM_BASE_URL, {"Authorization": f"Bearer {key}"}, _model, prompt, nim_timeout)
        gens[f"nim:{model}"] = _nim_gen

    return gens


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _demo_scorer(answer: str) -> float:
    """DEMO SCORER — a length-capped heuristic, NOT a real verifier. Reward
    substantive-but-not-bloated answers, cap near ~600 chars. Real callers
    MUST inject a domain score_fn (e.g. a Hive verifier) via the
    EscalationOrgan constructor instead of relying on this."""
    n = len(answer.strip())
    if n == 0:
        return 0.0
    if n <= 600:
        return _clamp01(n / 600.0)
    return _clamp01(1.0 - (n - 600) / 3000.0)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="AIOS escalation organ — AB-MCTS multi-model search for hard tasks.",
    )
    parser.add_argument("goal", help="the hard task / question to escalate")
    parser.add_argument("--budget", type=int, default=16, help="generations budget (default: 16)")
    args = parser.parse_args(argv)

    organ = EscalationOrgan(make_default_generators(), _demo_scorer)
    result = organ.escalate(args.goal, budget=args.budget)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
