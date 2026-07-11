"""The kernel head can now run a reactive agent TURN-LOOP (organs as kernel tools,
authority-gated) — additive to the existing single-pass plan path. This is what keeps
the turn-loop from being an orphan: the head actually drives it.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_head as H
import aios_turn_loop as L


def scripted(steps):
    it = iter(steps)
    return lambda h: next(it)


class HeadLoopTests(unittest.TestCase):
    def test_head_runs_the_loop_routing_organs_through_kernel(self) -> None:
        r = H.run_loop_goal("inspect", agent_id="codex@myworld", sampler=scripted([
            {"tool_calls": [L.ToolCall("self.audit",
                {"claims": [{"text": "head", "path": "scripts/aios_head.py"}]})]},
            # head runs with answer_bounce=1: an answerless finish gets one nudge,
            # so the finishing step must state an answer (2026-07-10 head probe fix)
            {"tool_calls": [], "text": "audit complete"},
        ]))
        self.assertEqual(r["exit"], "model_finished")
        self.assertEqual(r["answer"], "audit complete")
        self.assertTrue(r["kernel_routed"])

    def test_no_sampler_is_honest(self) -> None:
        self.assertEqual(H.run_loop_goal("x")["exit"], "no_sampler")

    def test_head_sampler_applies_all_renewal_pillars(self) -> None:
        # Runner unification (Cycle 5): the head path now shares the harness's
        # pillars — decondition (1), plan-repair render (3), constraint render (4).
        seen = {"p": ""}
        sampler = H.make_provider_sampler(
            "claude", {"claude": lambda p: (seen.__setitem__("p", p), '{"done":true}')[1]},
            goal="g")
        sampler([
            {"role": "user", "kind": "goal"},
            {"role": "tool", "tool": "x", "status": "error", "result": {"status": "error", "output": "OLDERR"}},
            {"role": "tool", "tool": "y", "status": "error", "result": {"status": "error", "output": "RECENTERR"}},
            {"role": "system", "kind": "plan_repair", "content": "RE-PLAN NOW"},
            {"role": "system", "kind": "constraint", "content": "NEVER WRITE PROD"},
        ])
        p = seen["p"]
        self.assertIn("RE-PLAN NOW", p)        # pillar 3 rendered
        self.assertIn("NEVER WRITE PROD", p)   # pillar 4 rendered
        self.assertNotIn("OLDERR", p)          # pillar 1: old error elided
        self.assertIn("RECENTERR", p)          # pillar 1: recent error kept

    def test_provider_sampler_degrades_when_provider_unreachable(self) -> None:
        # a provider adapter that raises → sampler ends the loop cleanly, no fabrication
        def boom(_prompt):
            raise RuntimeError("provider down")
        sampler = H.make_provider_sampler("claude", {"claude": boom})
        r = H.run_loop_goal("x", sampler=sampler)
        self.assertEqual(r["exit"], "model_finished")   # ended, did not invent a tool call
        self.assertEqual(r["tool_calls"], 0)

    def test_provider_sampler_parses_a_tool_call(self) -> None:
        # a provider returning a JSON move → one tool call, then done
        replies = iter(['{"tool":"fs.read","arguments":{"path":"scripts/aios_head.py"}}',
                        '{"done":true}'])
        sampler = H.make_provider_sampler("claude", {"claude": lambda p: next(replies)})
        r = H.run_loop_goal("read head", agent_id="codex@myworld", sampler=sampler)
        self.assertEqual([t["tool"] for t in r["trajectory"]], ["fs.read"])


class EpistemicGateFlagTests(unittest.TestCase):
    """ASC-0282 WP-A: --gate/--gate-disable plumbing (scripts/aios_head.py main())
    into run_loop_goal/run_organic_goal, via the _resolve_epistemic_gate helper."""

    def test_resolve_epistemic_gate_stays_none_without_flag_or_env(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AIOS_GATE_MODE", None)
            self.assertIsNone(H._resolve_epistemic_gate(None, []))

    def test_gate_disable_flag_reaches_run_loop_with_matching_disabled_organs(self) -> None:
        # Programmatic equivalent of `--gate organs --gate-disable h0guard`.
        gate = H._resolve_epistemic_gate("organs", ["h0guard"])
        self.assertIsNotNone(gate)
        events: list[dict] = []
        r = H.run_loop_goal("inspect", agent_id="codex@myworld", sampler=scripted([
            {"tool_calls": [L.ToolCall("self.audit",
                {"claims": [{"text": "head", "path": "scripts/aios_head.py"}]})]},
            {"tool_calls": [], "text": "audit complete"},
        ]), turn_sink=events.append, epistemic_gate=gate)
        gate_events = [e for e in events if e.get("kind") == "epistemic_gate"]
        self.assertTrue(gate_events)
        self.assertEqual(gate_events[0]["certificates"]["_disabled_organs"], ["h0guard"])
        self.assertEqual(r["exit"], "model_finished")


if __name__ == "__main__":
    unittest.main()
