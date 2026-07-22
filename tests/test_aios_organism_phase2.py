"""Organism assembly Phase 2 — self-verification mounted into the head's goal path
(docs/AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22.md, Phase 2).

When the turn loop FAILS (loop_detected / epistemic_gate_circuit_breaker /
max_turns-without-model_finished) and escalation is opted in (--escalate /
AIOS_ESCALATE=1), aios_head runs the previously zero-caller EscalationOrgan
(scripts/aios_escalate.py) over the provider-adapter pool, scored by the Weaver
verifier when torch+aios_verifier are available (demo scorer fallback otherwise),
and instruments the attempt (escalation_attempted / recovered / verifier scores /
budget_used / per-generator provenance) into the outcome + run log.

DEFAULT OFF: without the opt-in the head outcome is identical to before this
phase — no escalation module is even loaded. The original FAILURE exit is
preserved in every case: escalation is instrumented measurement, never a
laundered success (the Weaver verifier is domain-bound per its own docstring).

All samplers/generators here are fake and deterministic — no live network, no
model load (the weaver path is always torch-blocked or score_fn-stubbed).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_head as H
import aios_turn_loop as L

# Pre-import aios_escalate (and thus its `import treequest`) at COLLECTION time.
# Deterministic hard-abort otherwise (2026-07-22, this box): if treequest's first
# import happens MID-TEST while test_aios_verifier.py's collection-time torch
# C-stack is resident, the process dies with "Fatal Python error: Aborted" inside
# treequest/__init__. Both collection-time orders (treequest->torch and
# torch->treequest) are fine — only the mid-test first exec aborts.
H._load("aios_escalate")


def _esc_mod():
    """The aios_escalate module object aios_head will actually resolve at call
    time. head._load consults sys.modules under the PLAIN name — and
    tests/test_aios_verifier.py's own _load re-registers "aios_escalate" there
    mid-suite — so patch targets must be resolved per-test, not via a stale
    module-level import (a stale import made 3 of these tests' patches
    invisible in a combined run, 2026-07-22)."""
    return H._load("aios_escalate")


def failing_sampler():
    """Repeats the identical tool call forever -> loop_detected at threshold 3."""
    return lambda h: {"tool_calls": [L.ToolCall("self.audit", {"claims": []})]}


def churning_sampler():
    """A different call signature every turn -> never finishes, never loop-trips;
    with a small max_turns the loop exits `max_turns` (failure: no model_finished)."""
    state = {"n": 0}

    def sampler(history):
        state["n"] += 1
        return {"tool_calls": [L.ToolCall("self.audit", {"claims": [], "turn": state["n"]})]}

    return sampler


FAKE_GENS = {
    "prov_a": lambda p: "provider-a answer: a reasonably substantive reply",
    "prov_b": lambda p: "provider-b answer: another substantive reply text",
}


class EscalationOnFailureTests(unittest.TestCase):
    """(i) loop failure + escalate ON -> EscalationOrgan invoked with the provider
    generators and a weaver-or-demo score_fn; outcome + run log instrumented."""

    def setUp(self) -> None:
        # Deterministic env: no ambient opt-in / budget override leaks in.
        for var in ("AIOS_ESCALATE", "AIOS_ESCALATE_BUDGET"):
            self._stash = os.environ.pop(var, None)
            if self._stash is not None:
                self.addCleanup(os.environ.__setitem__, var, self._stash)

    def test_failed_loop_escalates_with_provider_generators_and_records(self) -> None:
        E = _esc_mod()
        captured: dict = {}
        real_organ = E.EscalationOrgan

        class SpyOrgan(real_organ):
            def __init__(self, generators, score_fn):
                captured["generators"] = dict(generators)
                captured["score_fn"] = score_fn
                super().__init__(generators, score_fn)

        events: list[dict] = []
        # torch blocked -> the weaver-or-demo selection deterministically lands on
        # demo (no model load in tests); the weaver-requested branch is proven in
        # WeaverSelectionTests below.
        with patch.object(E, "EscalationOrgan", SpyOrgan), \
             patch.dict(sys.modules, {"torch": None}):
            r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                sampler=failing_sampler(), turn_sink=events.append,
                                escalate=True, escalate_generators=FAKE_GENS)

        # Original failure exit preserved — escalation never launders the outcome.
        self.assertEqual(r["exit"], "loop_detected")
        esc = r["escalation"]
        self.assertTrue(esc["escalation_attempted"])
        self.assertEqual(esc["failed_exit"], "loop_detected")
        self.assertIn(esc["verifier"], ("weaver", "demo"))
        # recovered = non-empty best answer with score > 0 (mechanism measurement)
        self.assertTrue(esc["recovered"])
        self.assertGreater(esc["best_score"], 0.0)
        self.assertTrue(esc["answer"].startswith("provider-"))
        # instrumentation for the Phase-3 experience graph
        self.assertGreaterEqual(esc["budget_used"], 1)
        self.assertLessEqual(esc["budget_used"], 6)   # bounded default budget
        self.assertTrue(esc["provenance"])
        self.assertEqual(set(esc["provider_breakdown"]), {"prov_a", "prov_b"})
        # the organ really received the head's provider adapters + a live score_fn
        self.assertEqual(set(captured["generators"]), {"prov_a", "prov_b"})
        self.assertGreater(captured["score_fn"]("a non-empty answer"), 0.0)
        # run-log record emitted, content-safe (scores/provenance, no answer text)
        esc_events = [e for e in events if e.get("kind") == "escalation"]
        self.assertEqual(len(esc_events), 1)
        self.assertNotIn("answer", esc_events[0])
        self.assertIn("provenance", esc_events[0])
        json.dumps(esc_events[0])  # must be serializable into the .jsonl run log

    def test_max_turns_without_finish_also_triggers_escalation(self) -> None:
        with patch.dict(sys.modules, {"torch": None}):
            r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                sampler=churning_sampler(), max_turns=2,
                                escalate=True, escalate_generators=FAKE_GENS)
        self.assertEqual(r["exit"], "max_turns")
        self.assertTrue(r["escalation"]["escalation_attempted"])

    def test_env_var_opts_in_when_flag_not_passed(self) -> None:
        with patch.dict(os.environ, {"AIOS_ESCALATE": "1", "AIOS_ESCALATE_BUDGET": "3"}), \
             patch.dict(sys.modules, {"torch": None}):
            r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                sampler=failing_sampler(),
                                escalate_generators=FAKE_GENS)   # escalate left default None
        self.assertIn("escalation", r)
        self.assertLessEqual(r["escalation"]["budget_used"], 3)


class WeaverSelectionTests(unittest.TestCase):
    """The head asks for the REAL verifier first whenever torch is importable;
    the returned score_fn is stubbed so no model is ever loaded in tests."""

    def test_weaver_requested_when_torch_importable(self) -> None:
        import types

        E = _esc_mod()
        requested: list[str] = []

        def fake_make_score_fn(goal, *, verifier="demo"):
            requested.append(verifier)
            return E._demo_scorer

        with patch.object(E, "make_score_fn", fake_make_score_fn), \
             patch.dict(sys.modules, {"torch": types.ModuleType("torch")}):
            r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                sampler=failing_sampler(),
                                escalate=True, escalate_generators=FAKE_GENS)
        self.assertEqual(requested, ["weaver"])
        self.assertEqual(r["escalation"]["verifier"], "weaver")
        self.assertNotIn("verifier_fallback_reason", r["escalation"])


class EscalateOffDefaultTests(unittest.TestCase):
    """(ii) escalate OFF (default) -> head outcome identical to before: the
    escalation path is not taken at all, no new keys appear."""

    def test_default_off_failure_outcome_unchanged(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AIOS_ESCALATE", None)
            with patch.object(H, "_escalate_failed_goal") as spy:
                r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                    sampler=failing_sampler())
        spy.assert_not_called()
        self.assertEqual(r["exit"], "loop_detected")
        self.assertNotIn("escalation", r)

    def test_explicit_false_wins_over_env(self) -> None:
        with patch.dict(os.environ, {"AIOS_ESCALATE": "1"}):
            with patch.object(H, "_escalate_failed_goal") as spy:
                r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                    sampler=failing_sampler(), escalate=False)
        spy.assert_not_called()
        self.assertNotIn("escalation", r)

    def test_success_exit_never_escalates_even_when_opted_in(self) -> None:
        steps = iter([{"tool_calls": [], "text": "done and answered"}])
        with patch.object(H, "_escalate_failed_goal") as spy:
            r = H.run_loop_goal("easy goal", agent_id="codex@myworld",
                                sampler=lambda h: next(steps),
                                escalate=True, escalate_generators=FAKE_GENS)
        spy.assert_not_called()
        self.assertEqual(r["exit"], "model_finished")
        self.assertNotIn("escalation", r)


class WeaverAbsentFallbackTests(unittest.TestCase):
    """(iii) Weaver/torch absent (mocked ImportError) -> honest demo fallback,
    no crash, fallback reason recorded."""

    def test_torch_import_error_falls_back_to_demo_scorer(self) -> None:
        # sys.modules[name] = None makes `import torch` raise ImportError — the
        # canonical absence simulation, independent of what is installed here.
        with patch.dict(sys.modules, {"torch": None}):
            r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                sampler=failing_sampler(),
                                escalate=True, escalate_generators=FAKE_GENS)
        esc = r["escalation"]
        self.assertEqual(esc["verifier"], "demo")
        self.assertIn("verifier_fallback_reason", esc)
        self.assertTrue(esc["escalation_attempted"])
        self.assertTrue(esc["recovered"])          # demo scorer still measures
        self.assertEqual(r["exit"], "loop_detected")  # failure exit still honest


class EscalationInternalErrorTests(unittest.TestCase):
    """(iv) the escalation organ raising internally -> honest fallback to the
    ORIGINAL failed outcome; the head never crashes."""

    def test_organ_crash_keeps_original_failed_outcome(self) -> None:
        E = _esc_mod()
        with patch.object(E, "EscalationOrgan",
                          side_effect=RuntimeError("organ exploded")), \
             patch.dict(sys.modules, {"torch": None}):
            r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                sampler=failing_sampler(),
                                escalate=True, escalate_generators=FAKE_GENS)
        self.assertEqual(r["exit"], "loop_detected")   # original outcome kept
        esc = r["escalation"]
        self.assertTrue(esc["escalation_attempted"])
        self.assertFalse(esc["recovered"])
        self.assertIn("escalation_internal_error", esc["error"])
        self.assertNotIn("answer", esc)

    def test_emit_sink_failure_does_not_break_outcome(self) -> None:
        def broken_sink(rec):
            if rec.get("kind") == "escalation":
                raise OSError("disk full")

        with patch.dict(sys.modules, {"torch": None}):
            r = H.run_loop_goal("hard goal", agent_id="codex@myworld",
                                sampler=failing_sampler(), turn_sink=broken_sink,
                                escalate=True, escalate_generators=FAKE_GENS)
        self.assertTrue(r["escalation"]["escalation_attempted"])


class OrganicPathForwardingTests(unittest.TestCase):
    """The CLI's --loop/--organic route (run_organic_goal) forwards the
    escalation opt-in down to run_loop_goal, and the escalation record lands in
    the run log the postamble ingests. Preamble/postamble are stubbed — this
    tests the plumbing, not memory/capability organs."""

    def test_organic_run_forwards_escalation_and_logs_it(self) -> None:
        CB = H._load("aios_capabilityos_bridge")  # same identity the head resolves

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(H, "_organ_preamble", return_value={}), \
                 patch.object(H, "_organ_postamble", return_value={}), \
                 patch.object(CB, "recommend", return_value={}), \
                 patch.dict(sys.modules, {"torch": None}):
                r = H.run_organic_goal("hard goal", agent_id="codex@myworld",
                                       sampler=failing_sampler(), root=root,
                                       escalate=True, escalate_generators=FAKE_GENS,
                                       escalate_budget=2)
            self.assertEqual(r["exit"], "loop_detected")
            self.assertTrue(r["escalation"]["escalation_attempted"])
            self.assertLessEqual(r["escalation"]["budget_used"], 2)
            # run log (.aios/runs/<run_id>.jsonl) carries the escalation record
            log = root / ".aios" / "runs" / f"{r['run_id']}.jsonl"
            kinds = [json.loads(line).get("kind")
                     for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertIn("escalation", kinds)


if __name__ == "__main__":
    unittest.main()
