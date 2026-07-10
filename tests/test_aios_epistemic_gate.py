"""Tests for scripts/aios_epistemic_gate.py — the M1 blocking Epistemic Gate
(docs/AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md §4 M1).
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_epistemic_gate as G


class OffModeTests(unittest.TestCase):
    def test_off_mode_always_passes_and_checks_nothing(self) -> None:
        gate = G.EpistemicGate(mode="off")
        v = gate.gate({"tool": "danger", "arguments": {"cmd": "rm -rf /"}}, {"goal": "anything"})
        self.assertTrue(v.passed)
        self.assertEqual(v.verdict, G.CLAIM)
        self.assertEqual(v.reasons, [])
        self.assertIn("note", v.certificates)   # records "nothing checked", not a fabricated pass


class OrgansModeTests(unittest.TestCase):
    def test_organs_mode_rejects_a_contradictory_claim_set(self) -> None:
        # An obviously inconsistent proposal: the proposal asserts an output for an
        # input that history already recorded a DIFFERENT output for — a direct H0
        # conflict (experiments/agi_witness/claims.py:direct_io_conflicts).
        gate = G.EpistemicGate(mode="organs")
        proposal = {
            "tool": "submit_answer",
            "claims": [{"task_id": "t", "source_id": "proposal", "kind": "io",
                        "payload": {"input": [1, 2], "output": "B"}}],
        }
        context = {
            "known_claims": [{"task_id": "t", "source_id": "history", "kind": "io",
                              "payload": {"input": [1, 2], "output": "A"}}],
        }
        v = gate.gate(proposal, context)
        self.assertFalse(v.passed)
        self.assertEqual(v.verdict, G.MISSPECIFIED)
        self.assertTrue(any("conflict" in r or "contradictory" in r for r in v.reasons))
        self.assertEqual(v.certificates["apex"]["label"], "CONTRADICTORY")
        self.assertEqual(v.certificates["descent"]["h0_conflicts"], [[0, 1]])

    def test_organs_mode_h0_guard_flags_atypical_tool_for_category(self) -> None:
        gate = G.EpistemicGate(mode="organs")
        population = [{"category": "code", "top_tools": ["Read", "Edit", "Bash"]} for _ in range(20)]
        v = gate.gate({"tool": "launch_missiles", "category": "code"},
                      {"profiles_population": population})
        self.assertFalse(v.passed)
        self.assertTrue(v.certificates["h0guard"]["flagged"])

    def test_organs_mode_with_no_evidence_abstains_explicitly_never_a_silent_pass(self) -> None:
        gate = G.EpistemicGate(mode="organs")
        v = gate.gate({"tool": "fs.read", "arguments": {"path": "docs/README.md"}}, {"goal": "read a doc"})
        self.assertTrue(v.passed)                       # non-strict: does not brick a bare loop
        self.assertEqual(v.verdict, G.ABSTAIN)          # but it is NOT a CLAIM-grade pass
        self.assertEqual(v.checked, 0)                  # downstream can see nothing was verified
        self.assertIn("no_applicable_checks", v.reasons)
        self.assertEqual(v.certificates["apex"]["status"], "skipped")

    def test_organs_mode_strict_env_blocks_when_nothing_checkable(self) -> None:
        gate = G.EpistemicGate(mode="organs")
        with patch.dict(os.environ, {"AIOS_GATE_STRICT": "1"}):
            v = gate.gate({"tool": "fs.read"}, {"goal": "read a doc"})
        self.assertFalse(v.passed)
        self.assertEqual(v.verdict, G.ABSTAIN)

    def test_organs_mode_fails_closed_when_organ_infrastructure_is_dead(self) -> None:
        gate = G.EpistemicGate(mode="organs")
        with patch.object(G, "_import_certs", return_value={"_import_error": "tree gone"}):
            v = gate.gate({"tool": "x", "claims": [{"kind": "io", "payload": {}}]}, {"goal": "g"})
        self.assertFalse(v.passed)
        self.assertEqual(v.verdict, G.MISSPECIFIED)
        self.assertIn("organs_infrastructure_unavailable", v.reasons)
        self.assertGreater(v.infra_failures, 0)


class FailClosedTests(unittest.TestCase):
    def test_internal_error_fails_closed_by_default(self) -> None:
        gate = G.EpistemicGate(mode="organs")
        v = gate.gate(None, {})   # None.get(...) raises inside _gate_organs
        self.assertFalse(v.passed)
        self.assertEqual(v.verdict, G.MISSPECIFIED)
        self.assertTrue(v.reasons[0].startswith("gate_error:"))

    def test_failopen_env_escape_hatch(self) -> None:
        gate = G.EpistemicGate(mode="organs")
        with patch.dict(os.environ, {"AIOS_GATE_FAILOPEN": "1"}):
            v = gate.gate(None, {})
        self.assertTrue(v.passed)
        self.assertEqual(v.verdict, G.CLAIM)
        self.assertTrue(v.reasons[0].startswith("gate_error_failopen:"))


class ModeSelectionTests(unittest.TestCase):
    def test_env_var_selects_mode_when_constructor_arg_omitted(self) -> None:
        with patch.dict(os.environ, {"AIOS_GATE_MODE": "off"}):
            gate = G.EpistemicGate()
        self.assertEqual(gate.mode, "off")

    def test_unknown_mode_falls_back_to_organs(self) -> None:
        gate = G.EpistemicGate(mode="not-a-real-mode")
        self.assertEqual(gate.mode, "organs")


class LlmJudgeUnavailableTests(unittest.TestCase):
    def test_llm_judge_fails_closed_when_judge_call_fails(self) -> None:
        # A judge arm whose judge is dead must block loudly — it must never silently
        # degrade into the off arm (would contaminate the M2 ablation).
        import aios_adapters as adapters
        gate = G.EpistemicGate(mode="llm-judge")
        def _broken_adapter(timeout=20):
            def _call(prompt):
                raise ConnectionError("endpoint down")
            return _call
        with patch.object(adapters, "make_ollama_rest_adapter", _broken_adapter):
            v = gate.gate({"tool": "x"}, {"goal": "test"})
        self.assertFalse(v.passed)
        self.assertEqual(v.verdict, G.MISSPECIFIED)
        self.assertEqual(v.certificates["llm_judge"]["status"], "unavailable")
        self.assertIn("llm_judge_unavailable", v.reasons[0])
        self.assertEqual(v.infra_failures, 1)

    def test_llm_judge_failopen_escape_hatch_passes_with_labeled_reason(self) -> None:
        import aios_adapters as adapters
        gate = G.EpistemicGate(mode="llm-judge")
        def _broken_adapter(timeout=20):
            def _call(prompt):
                raise ConnectionError("endpoint down")
            return _call
        with patch.object(adapters, "make_ollama_rest_adapter", _broken_adapter), \
             patch.dict(os.environ, {"AIOS_GATE_FAILOPEN": "1"}):
            v = gate.gate({"tool": "x"}, {"goal": "test"})
        self.assertTrue(v.passed)
        self.assertTrue(v.reasons[0].startswith("failopen:"))


if __name__ == "__main__":
    unittest.main()
