"""aios_escalate tests (masterplan §4 M5/D7-10) — no live network call.

All generators used here are fake, deterministic prompt->answer callables
injected via EscalationOrgan's dependency-injection constructor — the same
pattern as test_aios_llm_client.py's fake `post`. The treequest-unavailable
fallback path is exercised by monkeypatching `_HAVE_TREEQUEST` to False, so
the suite proves both the real treequest.ABMCTSA path and the vendored
fallback without needing to uninstall the package.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _load(name: str):
    full = f"{name}_under_test"
    spec = importlib.util.spec_from_file_location(full, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[full] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


def _len_score(answer: str) -> float:
    """Deterministic fake verifier: score scales with length, capped at 1.0."""
    return min(1.0, len(answer) / 40.0)


class EscalationOrganTreequestTests(unittest.TestCase):
    """Exercises the real treequest.ABMCTSA path (package is installed)."""

    def setUp(self) -> None:
        self.E = _load("aios_escalate")
        if not self.E._HAVE_TREEQUEST:
            self.skipTest("treequest not installed in this environment")

    def test_budget_is_respected(self) -> None:
        calls = {"n": 0}

        def gen(prompt: str) -> str:
            calls["n"] += 1
            return f"answer-{calls['n']}"

        organ = self.E.EscalationOrgan({"g": gen}, _len_score)
        result = organ.escalate("goal", budget=7)
        self.assertEqual(result["budget_used"], 7)
        self.assertEqual(len(result["provenance"]), 7)
        self.assertEqual(calls["n"], 7)

    def test_best_selection_picks_highest_scoring_answer(self) -> None:
        # A stronger generator (longer, higher-scoring answers) should win.
        def weak(prompt: str) -> str:
            return "short"

        def strong(prompt: str) -> str:
            return "a much longer and more thorough answer than the weak one"

        organ = self.E.EscalationOrgan({"weak": weak, "strong": strong}, _len_score)
        result = organ.escalate("goal", budget=10)
        self.assertEqual(result["best_score"], 1.0)
        self.assertIn("longer and more thorough", result["best_answer"])

    def test_provider_breakdown_counts_generations_per_generator(self) -> None:
        def gen_a(prompt: str) -> str:
            return "aaaa"

        def gen_b(prompt: str) -> str:
            return "bbbb"

        organ = self.E.EscalationOrgan({"a": gen_a, "b": gen_b}, _len_score)
        result = organ.escalate("goal", budget=8)
        breakdown = result["provider_breakdown"]
        self.assertEqual(set(breakdown), {"a", "b"})
        total = sum(v["generations"] for v in breakdown.values())
        self.assertEqual(total, 8)
        for v in breakdown.values():
            self.assertEqual(v["successes"], v["generations"])
            self.assertGreaterEqual(v["avg_score"], 0.0)

    def test_all_generators_down_returns_named_failure(self) -> None:
        def always_fails(prompt: str) -> str:
            raise ConnectionError("endpoint unreachable")

        organ = self.E.EscalationOrgan({"dead1": always_fails, "dead2": always_fails}, _len_score)
        result = organ.escalate("goal", budget=4)
        self.assertEqual(result["error"], "all_generators_down")
        self.assertEqual(result["budget_used"], 4)
        self.assertEqual(set(result["generators"]), {"dead1", "dead2"})
        self.assertNotIn("best_answer", result)
        for entry in result["provenance"]:
            self.assertFalse(entry["ok"])

    def test_partial_failure_is_recorded_not_fatal(self) -> None:
        def flaky(prompt: str) -> str:
            raise TimeoutError("down")

        def healthy(prompt: str) -> str:
            return "a working answer of reasonable length"

        organ = self.E.EscalationOrgan({"flaky": flaky, "healthy": healthy}, _len_score)
        result = organ.escalate("goal", budget=6)
        self.assertNotIn("error", result)
        self.assertIn("flaky", result["generators_down"])
        self.assertNotIn("healthy", result["generators_down"])
        self.assertTrue(result["best_answer"])
        # flaky's failed attempt(s) are recorded in provenance, not dropped
        flaky_entries = [e for e in result["provenance"] if e["generator"] == "flaky"]
        self.assertTrue(flaky_entries)
        self.assertFalse(any(e["ok"] for e in flaky_entries))

    def test_provenance_is_reconstructable_via_parent_id(self) -> None:
        def gen(prompt: str) -> str:
            return "x" * 20

        organ = self.E.EscalationOrgan({"g": gen}, _len_score)
        result = organ.escalate("goal", budget=5)
        ids = {e["id"] for e in result["provenance"]}
        for e in result["provenance"]:
            self.assertIn(e["generator"], {"g"})
            self.assertIn("score", e)
            if e["parent_id"] is not None:
                self.assertIn(e["parent_id"], ids)

    def test_score_is_clamped_to_unit_interval(self) -> None:
        def gen(prompt: str) -> str:
            return "y" * 500  # would score >>1.0 under _len_score without clamping

        organ = self.E.EscalationOrgan({"g": gen}, _len_score)
        result = organ.escalate("goal", budget=2)
        self.assertLessEqual(result["best_score"], 1.0)
        for e in result["provenance"]:
            self.assertLessEqual(e["score"], 1.0)
            self.assertGreaterEqual(e["score"], 0.0)

    def test_engine_label_names_treequest(self) -> None:
        organ = self.E.EscalationOrgan({"g": lambda p: "abc"}, _len_score)
        result = organ.escalate("goal", budget=2)
        self.assertEqual(result["engine"], "treequest.ABMCTSA")
        self.assertEqual(result["tree_stats"]["engine"], "treequest.ABMCTSA")

    def test_rejects_empty_generator_pool(self) -> None:
        with self.assertRaises(ValueError):
            self.E.EscalationOrgan({}, _len_score)

    def test_rejects_non_positive_budget(self) -> None:
        organ = self.E.EscalationOrgan({"g": lambda p: "x"}, _len_score)
        with self.assertRaises(ValueError):
            organ.escalate("goal", budget=0)


class EscalationOrganFallbackTests(unittest.TestCase):
    """Exercises the treequest-unavailable fallback via monkeypatch — proves
    the module degrades honestly instead of crashing when the dependency is
    missing."""

    def setUp(self) -> None:
        self.E = _load("aios_escalate")
        self._had_treequest = self.E._HAVE_TREEQUEST
        self.E._HAVE_TREEQUEST = False
        self.addCleanup(setattr, self.E, "_HAVE_TREEQUEST", self._had_treequest)

    def test_fallback_runs_and_labels_itself_honestly(self) -> None:
        organ = self.E.EscalationOrgan({"g": lambda p: "a reasonable answer"}, _len_score)
        result = organ.escalate("goal", budget=5)
        self.assertNotIn("error", result)
        self.assertTrue(result["engine"].startswith("fallback"))
        self.assertIn("treequest-unavailable", result["engine"])
        self.assertEqual(result["budget_used"], 5)

    def test_fallback_respects_budget_and_selects_best(self) -> None:
        def weak(prompt: str) -> str:
            return "no"

        def strong(prompt: str) -> str:
            return "a long and thorough correct answer to the goal"

        organ = self.E.EscalationOrgan({"weak": weak, "strong": strong}, _len_score)
        result = organ.escalate("goal", budget=9)
        self.assertEqual(result["budget_used"], 9)
        self.assertEqual(len(result["provenance"]), 9)
        self.assertEqual(result["best_answer"], "a long and thorough correct answer to the goal")

    def test_fallback_all_generators_down(self) -> None:
        def dies(prompt: str) -> str:
            raise RuntimeError("nope")

        organ = self.E.EscalationOrgan({"a": dies, "b": dies}, _len_score)
        result = organ.escalate("goal", budget=3)
        self.assertEqual(result["error"], "all_generators_down")


class DemoScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.E = _load("aios_escalate")

    def test_empty_answer_scores_zero(self) -> None:
        self.assertEqual(self.E._demo_scorer(""), 0.0)
        self.assertEqual(self.E._demo_scorer("   "), 0.0)

    def test_score_bounded_to_unit_interval(self) -> None:
        self.assertLessEqual(self.E._demo_scorer("x" * 5000), 1.0)
        self.assertGreaterEqual(self.E._demo_scorer("x" * 5000), 0.0)
        self.assertLessEqual(self.E._demo_scorer("hello world"), 1.0)


class MakeDefaultGeneratorsTests(unittest.TestCase):
    """No live network — only checks pool shape/env wiring."""

    def setUp(self) -> None:
        self.E = _load("aios_escalate")

    def test_default_pool_has_local_and_nim_entries(self) -> None:
        gens = self.E.make_default_generators()
        names = list(gens)
        self.assertTrue(any(n.startswith("local:") for n in names))
        self.assertTrue(any(n.startswith("nim:") for n in names))
        # default NIM pool is exactly the two founder-verified models
        nim_names = {n for n in names if n.startswith("nim:")}
        self.assertEqual(nim_names, {
            "nim:qwen/qwen3.5-397b-a17b",
            "nim:nvidia/nemotron-3-ultra-550b-a55b",
        })

    def test_env_overrides_ollama_model_and_nim_pool(self) -> None:
        import os
        import unittest.mock as mock

        with mock.patch.dict(os.environ, {
            "AIOS_OLLAMA_MODEL": "qwen3:8b",
            "AIOS_NIM_POOL": "vendor/model-x,vendor/model-y",
        }):
            gens = self.E.make_default_generators()
        self.assertIn("local:qwen3:8b", gens)
        self.assertIn("nim:vendor/model-x", gens)
        self.assertIn("nim:vendor/model-y", gens)

    def test_nim_generator_raises_cleanly_without_a_key(self) -> None:
        import os
        import unittest.mock as mock

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NVIDIA_API_KEY", None)
            with mock.patch.object(self.E, "_read_nvidia_api_key", return_value=""):
                gens = self.E.make_default_generators()
                nim_fn = next(fn for name, fn in gens.items() if name.startswith("nim:"))
                with self.assertRaises(RuntimeError):
                    nim_fn("prompt")


class CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.E = _load("aios_escalate")

    def test_main_returns_nonzero_on_all_generators_down(self) -> None:
        import unittest.mock as mock

        def dead_pool():
            return {"dead": lambda p: (_ for _ in ()).throw(RuntimeError("down"))}

        with mock.patch.object(self.E, "make_default_generators", side_effect=dead_pool):
            rc = self.E.main(["a hard goal", "--budget", "2"])
        self.assertEqual(rc, 1)

    def test_main_returns_zero_on_success(self) -> None:
        import unittest.mock as mock

        def working_pool():
            return {"g": lambda p: "a fine answer"}

        with mock.patch.object(self.E, "make_default_generators", side_effect=working_pool):
            rc = self.E.main(["a hard goal", "--budget", "3"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
