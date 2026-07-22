"""aios_verifier tests (docs/AIOS_ABSORPTION_SCAN_2026-07-22.md #1 — Weaver).

No network call and no real model download: `_load_verifier_model` is
MOCKED via monkeypatch. The mock still round-trips through REAL torch tensor
ops (tensor construction/slicing/squeeze) via a fake tokenizer + fake base
model + fake MLP head, so the actual score()/weak_ensemble()/
make_verifier_score_fn() plumbing is genuinely exercised, not just its call
signature. Tests needing torch skip cleanly (not hard-fail) if torch is
unavailable in the running environment — same pattern as
test_aios_escalate.py's `_HAVE_TREEQUEST` skip guard.

Fake shapes match the VERIFIED real architecture (see aios_verifier.py's
module docstring "CORRECTION" note): a base encoder called as
`base_model(input_ids=..., attention_mask=..., output_hidden_states=True)`
returning `.hidden_states[-1]` (last layer), CLS-pooled at `[:, 0, :]`, fed
through an MLP head that returns a RAW regression score (no sigmoid) —
`_load_verifier_model()`'s real entry now returns
{"tokenizer", "base_model", "mlp_head", "device", "model_id"}.
"""
from __future__ import annotations

import concurrent.futures
import importlib.util
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

try:
    import torch as _torch
    _HAVE_TORCH = True
except ImportError:  # pragma: no cover — exercised only on torch-less boxes
    _torch = None
    _HAVE_TORCH = False


def _load(name: str):
    full = f"{name}_under_test"
    spec = importlib.util.spec_from_file_location(full, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[full] = m
    # ALSO register under the plain name: aios_escalate.py's make_score_fn()
    # does a real `import aios_verifier` at call time. Without this, that
    # statement would resolve to a SEPARATE module instance than `self.V`
    # below, so mock.patch.object(self.V, "_load_verifier_model", ...) would
    # be invisible to it (proven by a real failure during development: the
    # integration tests silently fell through to the REAL loader and
    # honest-degraded to 0.0 instead of exercising the mock).
    sys.modules[name] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class _FakeTokenizer:
    """Stands in for the real AutoTokenizer: real call shape is
    tokenizer(text=query, text_pair=answer, truncation=..., max_length=...,
    padding=..., return_tensors="pt") -> dict-like with real tensors."""

    def __call__(self, *, text, text_pair, **kwargs):  # noqa: ARG002
        assert isinstance(text, str) and isinstance(text_pair, str)
        return {
            "input_ids": _torch.zeros((1, 4), dtype=_torch.long),
            "attention_mask": _torch.ones((1, 4), dtype=_torch.long),
        }


class _FakeHiddenStatesOutput:
    def __init__(self, hidden_states):
        self.hidden_states = hidden_states


class _FakeBaseModel:
    """Stands in for the base ModernBERT encoder: real call shape is
    base_model(input_ids=..., attention_mask=..., output_hidden_states=True)
    -> object with .hidden_states (tuple), last element [:, 0, :] = CLS."""

    def __call__(self, *, input_ids, attention_mask, output_hidden_states=True):  # noqa: ARG002
        batch, seq_len = input_ids.shape
        hidden = _torch.zeros((batch, seq_len, 4), dtype=_torch.float32)
        return _FakeHiddenStatesOutput((hidden,))


class _FakeMLPHead:
    """Stands in for the trained MLP head: real forward returns a RAW
    regression score (no sigmoid — verified live against the actual
    checkpoint, see aios_verifier.py's module docstring). Ignores the CLS
    embedding content and returns a fixed target so tests can control the
    outcome directly."""

    def __init__(self, raw_score: float):
        self._raw_score = raw_score

    def __call__(self, cls_embedding):
        batch = cls_embedding.shape[0]
        return _torch.full((batch, 1), self._raw_score, dtype=_torch.float32)


def _fake_loader(raw_score: float):
    def _load_verifier_model(*, model_id="ignored", base_model_id="ignored", device=None):  # noqa: ARG001
        return {
            "tokenizer": _FakeTokenizer(),
            "base_model": _FakeBaseModel(),
            "mlp_head": _FakeMLPHead(raw_score),
            "device": "cpu",
            "model_id": model_id,
        }
    return _load_verifier_model


@unittest.skipUnless(_HAVE_TORCH, "torch not installed in this environment")
class ScoreMockedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.V = _load("aios_verifier")

    def test_score_in_unit_interval_for_confident_correct(self) -> None:
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=0.95)):
            result = self.V.score("what is 2+2", "4")
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)
        self.assertGreater(result, 0.9)

    def test_score_in_unit_interval_for_confident_wrong(self) -> None:
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=0.05)):
            result = self.V.score("what is 2+2", "purple elephant")
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)
        self.assertLess(result, 0.1)

    def test_score_clamps_out_of_range_raw_output(self) -> None:
        """The real MLP head has no output activation (verified live) — its
        raw regression output can stray outside [0,1]; score() must clamp."""
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=1.4)):
            self.assertEqual(self.V.score("q", "a"), 1.0)
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=-0.3)):
            self.assertEqual(self.V.score("q", "a"), 0.0)

    def test_score_is_monotonic_right_beats_wrong(self) -> None:
        """The actual discrimination check: a clearly-right answer must score
        higher than a clearly-wrong one, via the SAME mocked model swapped
        between two calls (proves score() doesn't hardcode a constant)."""
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=0.9)):
            right = self.V.score("capital of France", "Paris")
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=0.1)):
            wrong = self.V.score("capital of France", "banana")
        self.assertGreater(right, wrong)

    def test_empty_answer_scores_zero_without_invoking_model(self) -> None:
        # No mock installed at all — if this touched the model loader it would
        # raise (no cached/mocked model), proving the empty-answer short-circuit.
        self.assertEqual(self.V.score("a query", ""), 0.0)
        self.assertEqual(self.V.score("a query", "   "), 0.0)

    def test_empty_query_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.V.score("", "an answer")

    def test_non_string_answer_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.V.score("a query", 123)  # type: ignore[arg-type]


@unittest.skipUnless(_HAVE_TORCH, "torch not installed in this environment")
class ScoreErrorDegradeTests(unittest.TestCase):
    """Timeout / model-unavailable both come back as an honest error dict,
    never a fabricated float, never a hang."""

    def setUp(self) -> None:
        self.V = _load("aios_verifier")

    def test_model_load_failure_returns_honest_error_dict(self) -> None:
        def _broken_loader(**kwargs):
            raise RuntimeError("simulated: no network for first-time download")

        with mock.patch.object(self.V, "_load_verifier_model", _broken_loader):
            result = self.V.score("q", "a")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["error"], "verifier_unavailable")
        self.assertIn("simulated", result["detail"])

    def test_timeout_returns_honest_error_dict_not_a_hang(self) -> None:
        def _slow_run(fn, timeout):  # noqa: ARG001
            raise concurrent.futures.TimeoutError()

        with mock.patch.object(self.V, "_run_with_timeout", _slow_run):
            result = self.V.score("q", "a", timeout=0.01)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["error"], "timeout")
        self.assertIn("0.01", result["detail"])


class WeakEnsembleTests(unittest.TestCase):
    """Pure stdlib math — no torch/transformers needed, runs unconditionally."""

    def setUp(self) -> None:
        self.V = _load("aios_verifier")

    def test_single_score_passthrough(self) -> None:
        self.assertEqual(self.V.weak_ensemble("q", "a", [0.73]), 0.73)

    def test_unanimous_scores_stay_put(self) -> None:
        self.assertAlmostEqual(self.V.weak_ensemble("q", "a", [0.8, 0.8, 0.8]), 0.8, places=6)

    def test_symmetric_disagreement_settles_at_midpoint(self) -> None:
        # Two equally-confident, opposite verifiers: no information to break
        # the tie -> the fixed point is exactly the mean, and stable there.
        result = self.V.weak_ensemble("q", "a", [0.9, 0.1])
        self.assertAlmostEqual(result, 0.5, places=6)

    def test_outlier_is_downweighted_vs_naive_mean(self) -> None:
        """The actual 'combines correctly' proof: three verifiers cluster near
        0.87, one outlier sits at 0.1. A real reliability-weighted combine
        must land closer to the majority cluster than a naive average would —
        proving weak_ensemble is not just sum(scores)/len(scores)."""
        weak_scores = [0.9, 0.85, 0.88, 0.1]
        naive_mean = sum(weak_scores) / len(weak_scores)  # 0.6825
        result = self.V.weak_ensemble("q", "a", weak_scores)
        self.assertGreater(result, naive_mean)
        self.assertLess(abs(result - 0.876), abs(naive_mean - 0.876))

    def test_result_always_in_unit_interval(self) -> None:
        for weak_scores in ([0.0, 1.0], [1.0, 1.0, 1.0], [0.0], [0.5] * 5, [0.99, 0.01, 0.5]):
            result = self.V.weak_ensemble("q", "a", weak_scores)
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 1.0)

    def test_rejects_empty_weak_scores(self) -> None:
        with self.assertRaises(ValueError):
            self.V.weak_ensemble("q", "a", [])

    def test_rejects_empty_query(self) -> None:
        with self.assertRaises(ValueError):
            self.V.weak_ensemble("", "a", [0.5])


@unittest.skipUnless(_HAVE_TORCH, "torch not installed in this environment")
class MakeVerifierScoreFnTests(unittest.TestCase):
    def setUp(self) -> None:
        self.V = _load("aios_verifier")

    def test_returns_plain_float_on_success(self) -> None:
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=0.92)):
            score_fn = self.V.make_verifier_score_fn("what is 2+2")
            result = score_fn("4")
        self.assertIsInstance(result, float)
        self.assertGreater(result, 0.9)

    def test_degrades_to_zero_never_raises_never_returns_dict(self) -> None:
        """The structural subtlety: EscalationOrgan wraps score_fn(answer) in
        the SAME try/except as the generator call, so a raised exception (or
        a non-float return) here would be mis-attributed to the generator."""
        def _broken_loader(**kwargs):
            raise RuntimeError("model unavailable")

        with mock.patch.object(self.V, "_load_verifier_model", _broken_loader):
            score_fn = self.V.make_verifier_score_fn("q")
            result = score_fn("a")
        self.assertIsInstance(result, float)
        self.assertEqual(result, 0.0)


@unittest.skipUnless(_HAVE_TORCH, "torch not installed in this environment")
class EscalateIntegrationTests(unittest.TestCase):
    """Proves scripts/aios_escalate.py's make_score_fn(verifier="weaver")
    actually routes through the injected Weaver verifier, not _demo_scorer —
    the integration seam docs/AIOS_ABSORPTION_SCAN_2026-07-22.md names."""

    def setUp(self) -> None:
        self.V = _load("aios_verifier")
        self.E = _load("aios_escalate")

    def test_make_score_fn_demo_is_unchanged_default(self) -> None:
        fn = self.E.make_score_fn("goal")
        self.assertIs(fn, self.E._demo_scorer)

    def test_make_score_fn_weaver_uses_real_verifier_not_demo_heuristic(self) -> None:
        # _demo_scorer is purely length-based (short answers score low); rig
        # the mocked cross-encoder to score a SHORT answer highly, then prove
        # the organ reports that high score — something _demo_scorer could
        # never produce for a 1-char answer.
        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=0.995)):
            score_fn = self.E.make_score_fn("what is 2+2", verifier="weaver")
            short_answer = "4"
            weaver_score = score_fn(short_answer)
            demo_score = self.E._demo_scorer(short_answer)

        self.assertGreater(weaver_score, 0.99)
        self.assertLess(demo_score, 0.01)  # 1-char answer under the length-capped demo heuristic
        self.assertNotEqual(round(weaver_score, 2), round(demo_score, 2))

    def test_escalation_organ_end_to_end_with_injected_weaver_verifier(self) -> None:
        def gen(prompt: str) -> str:  # noqa: ARG001
            return "4"

        with mock.patch.object(self.V, "_load_verifier_model", _fake_loader(raw_score=0.995)):
            score_fn = self.E.make_score_fn("what is 2+2", verifier="weaver")
            organ = self.E.EscalationOrgan({"g": gen}, score_fn)
            result = organ.escalate("what is 2+2", budget=2)

        self.assertNotIn("error", result)
        self.assertGreater(result["best_score"], 0.99)

    def test_unknown_verifier_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            self.E.make_score_fn("goal", verifier="nonsense")

    def test_weaver_verifier_import_failure_raises_runtime_error(self) -> None:
        real_import = __import__

        def _blocked_import(name, *args, **kwargs):
            if name == "aios_verifier":
                raise ImportError("simulated: torch/transformers not installed")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=_blocked_import):
            with self.assertRaises(RuntimeError):
                self.E.make_score_fn("goal", verifier="weaver")


if __name__ == "__main__":
    unittest.main()
