"""Tests for experiments/driftbench/ -- the AIOS-DriftBench-mini harness SKELETON
(docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md). No agent/model runs happen here: these
tests exercise the environments, graders, mutation machinery, arm-runner interfaces,
result schema, and analysis script directly.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "experiments" / "driftbench").as_posix())

import analyze  # noqa: E402
import arms  # noqa: E402
import grader as grader_mod  # noqa: E402
import schema  # noqa: E402
import tasks  # noqa: E402


def _snapshot_workspace(ws: Path) -> dict:
    """Byte-content snapshot of a workspace, keyed by relative path -- used to compare
    two builds' fixture content without depending on the (always-different) tempdir
    paths themselves."""
    out = {}
    for p in sorted(ws.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(ws))] = p.read_bytes()
    return out


class DeterminismTests(unittest.TestCase):
    def test_same_seed_produces_identical_environment(self) -> None:
        for template in schema.ALL_TEMPLATES:
            with self.subTest(template=template):
                env_a = tasks.build(template, 1)
                env_b = tasks.build(template, 1)
                self.assertEqual(_snapshot_workspace(env_a.workspace_dir), _snapshot_workspace(env_b.workspace_dir))
                self.assertEqual(env_a.goal, env_b.goal)
                self.assertEqual(env_a.state, env_b.state)
                self.assertEqual([c.id for c in env_a.checkpoints], [c.id for c in env_b.checkpoints])
                env_a.cleanup()
                env_b.cleanup()

    def test_different_seeds_produce_different_fixture_data(self) -> None:
        for template in schema.ALL_TEMPLATES:
            with self.subTest(template=template):
                env_a = tasks.build(template, 0)
                env_b = tasks.build(template, 1)
                self.assertNotEqual(_snapshot_workspace(env_a.workspace_dir), _snapshot_workspace(env_b.workspace_dir))
                env_a.cleanup()
                env_b.cleanup()

    def test_template_registry_matches_schema_template_lists(self) -> None:
        self.assertEqual(set(tasks._BUILDERS), set(schema.ALL_TEMPLATES))
        self.assertEqual(len(schema.MUTATING_TEMPLATES), 6)
        self.assertEqual(len(schema.STATIC_TEMPLATES), 2)
        self.assertEqual(len(schema.ALL_TEMPLATES), 8)

    def test_all_instances_is_8x3(self) -> None:
        instances = tasks.all_instances()
        self.assertEqual(len(instances), 24)
        self.assertEqual(len(set(instances)), 24)


class MutationMachineryTests(unittest.TestCase):
    def test_static_templates_never_mutate(self) -> None:
        for template in schema.STATIC_TEMPLATES:
            env = tasks.build(template, 0)
            self.assertIsNone(env.mutation)
            self.assertFalse(env.mutating)
            before = _snapshot_workspace(env.workspace_dir)
            for step in range(1, 50):
                self.assertFalse(env.mutate(step))
            self.assertEqual(before, _snapshot_workspace(env.workspace_dir))
            env.cleanup()

    def test_mutation_fires_once_and_changes_workspace(self) -> None:
        for template in schema.MUTATING_TEMPLATES:
            with self.subTest(template=template):
                env = tasks.build(template, 2)
                self.assertTrue(env.mutating)
                self.assertIsNotNone(env.mutation)
                before_snapshot = _snapshot_workspace(env.workspace_dir)
                before_grade = env.grader()
                self.assertTrue(before_grade.binary_success, "instance should start in a passing state")

                if env.mutation.trigger_kind == "after_step":
                    k = env.mutation.trigger_value
                    for step in range(1, k):
                        self.assertFalse(env.mutate(step), f"mutation fired early at step {step}")
                    self.assertTrue(env.mutate(k), "mutation did not fire at its trigger step")
                else:
                    self.assertEqual(env.mutation.trigger_kind, "after_checkpoint")
                    self.assertTrue(env.mutate(1), "checkpoint-triggered mutation did not fire")

                self.assertTrue(env.mutation.applied)
                after_snapshot = _snapshot_workspace(env.workspace_dir)
                self.assertNotEqual(before_snapshot, after_snapshot, "mutation did not change the workspace")

                # Idempotent: further mutate() calls are no-ops.
                self.assertFalse(env.mutate(10_000))
                self.assertFalse(env.mutate(10_001))
                env.cleanup()

    def test_mutation_requires_agent_action_not_self_fixed_by_grading(self) -> None:
        """Regression guard for a real bug found while building this skeleton: a
        checkpoint check that itself EXECUTES the task script can silently "fix" a
        drifted environment merely by being graded, defeating the whole benchmark.
        Every mutating template must fail post-mutation, and stay failing across
        repeated grader() calls, until something actually edits the workspace."""
        for template in schema.MUTATING_TEMPLATES:
            with self.subTest(template=template):
                env = tasks.build(template, 0)
                if env.mutation.trigger_kind == "after_step":
                    env.mutate(env.mutation.trigger_value)
                else:
                    env.grader()  # populate _passed_checkpoint_ids so the trigger can see it
                    env.mutate(1)
                self.assertTrue(env.mutation.applied)
                first = env.grader()
                second = env.grader()
                third = env.grader()
                self.assertFalse(first.binary_success, f"{template}: did not require agent action post-mutation")
                self.assertEqual(first.binary_success, second.binary_success)
                self.assertEqual(second.binary_success, third.binary_success)
                env.cleanup()


class GraderPlantedOutcomeTests(unittest.TestCase):
    """"Plant" a correct fix and a wrong fix by hand and confirm the functional grader
    tells them apart -- both pre- and post-mutation."""

    def test_grader_detects_planted_success_api_migration(self) -> None:
        env = tasks.build("api_migration", 3)
        env.mutate(env.mutation.trigger_value)
        st = env.state
        fixed_src = (
            "import json\n"
            f"from client import {st['new_fn']}\n\n"
            "def run():\n"
            f"    record = {st['new_fn']}({st['record_id']}, strict=True)\n"
            '    with open("output.json", "w") as f:\n'
            "        json.dump(record, f)\n\n"
            'if __name__ == "__main__":\n    run()\n'
        )
        (env.workspace_dir / "caller.py").write_text(fixed_src, encoding="utf-8")
        result = env.grader()
        self.assertTrue(result.binary_success)
        self.assertEqual(result.checkpoints_passed, result.checkpoints_total)
        env.cleanup()

    def test_grader_detects_planted_wrong_action_api_migration(self) -> None:
        env = tasks.build("api_migration", 3)
        env.mutate(env.mutation.trigger_value)
        # A plausible-looking but WRONG fix: calls the new function name with the
        # wrong record id (a planted logic error, not a crash).
        st = env.state
        wrong_src = (
            "import json\n"
            f"from client import {st['new_fn']}\n\n"
            "def run():\n"
            f"    record = {st['new_fn']}({st['record_id'] + 1}, strict=True)\n"
            '    with open("output.json", "w") as f:\n'
            "        json.dump(record, f)\n\n"
            'if __name__ == "__main__":\n    run()\n'
        )
        (env.workspace_dir / "caller.py").write_text(wrong_src, encoding="utf-8")
        result = env.grader()
        self.assertFalse(result.binary_success)
        env.cleanup()

    def test_grader_detects_planted_success_schema_change(self) -> None:
        env = tasks.build("schema_change", 1)
        # Trigger is checkpoint-based on "summarize_runs" -- grade once pre-mutation
        # to populate the checkpoint history, then fire the mutation.
        pre = env.grader()
        self.assertTrue(pre.binary_success)
        fired = env.mutate(1)
        self.assertTrue(fired)
        st = env.state
        fixed_src = (
            "import csv\nimport json\n\n"
            f'COLUMN = "{st["new_col"]}"\n\n'
            "def run():\n"
            "    total = 0\n"
            '    with open("records.csv", newline="") as f:\n'
            "        for row in csv.DictReader(f):\n"
            "            total += int(row[COLUMN])\n"
            '    with open("summary.json", "w") as f:\n'
            '        json.dump({"total": total}, f)\n\n'
            'if __name__ == "__main__":\n    run()\n'
        )
        (env.workspace_dir / "summarize.py").write_text(fixed_src, encoding="utf-8")
        result = env.grader()
        self.assertTrue(result.binary_success)
        env.cleanup()


class WrongActionLabelingTests(unittest.TestCase):
    def test_state_worsened_is_flagged(self) -> None:
        trace = [grader_mod.ActionRecord(step=1, kind="tool_call")]
        labels = grader_mod.label_actions(
            trace, checkpoints_passed_by_step={0: 2, 1: 1},
        )
        self.assertIn(grader_mod.WrongActionReason.STATE_WORSENED, labels[0].reasons)

    def test_contract_violation_is_flagged(self) -> None:
        trace = [grader_mod.ActionRecord(step=1, kind="tool_call", payload={"path": "client.py"})]
        labels = grader_mod.label_actions(
            trace, checkpoints_passed_by_step={0: 0, 1: 0},
            contract_checks=[lambda a: a.payload.get("path") == "client.py"],
        )
        self.assertIn(grader_mod.WrongActionReason.CONTRACT_VIOLATION, labels[0].reasons)

    def test_stale_action_is_flagged(self) -> None:
        trace = [grader_mod.ActionRecord(step=5, kind="tool_call", references=["old_fn"])]
        labels = grader_mod.label_actions(
            trace, checkpoints_passed_by_step={0: 0, 5: 0},
            invalidated_after_step={"old_fn": 3},
        )
        self.assertIn(grader_mod.WrongActionReason.STALE_ACTION, labels[0].reasons)

    def test_unsupported_claim_is_flagged(self) -> None:
        trace = [grader_mod.ActionRecord(step=9, kind="submit_claim", claim_text="Task complete, all done.")]
        final_grade = grader_mod.GradeResult(binary_success=False, per_checkpoint={}, checkpoints_passed=1, checkpoints_total=3)
        labels = grader_mod.label_actions(
            trace, checkpoints_passed_by_step={0: 0, 9: 1}, final_grade=final_grade,
        )
        self.assertIn(grader_mod.WrongActionReason.UNSUPPORTED_CLAIM, labels[0].reasons)

    def test_ambiguous_claim_is_left_for_audit(self) -> None:
        trace = [grader_mod.ActionRecord(step=9, kind="submit_claim", claim_text="Handled the edge case per spec section 4.")]
        final_grade = grader_mod.GradeResult(binary_success=True, per_checkpoint={}, checkpoints_passed=3, checkpoints_total=3)
        labels = grader_mod.label_actions(
            trace, checkpoints_passed_by_step={0: 0, 9: 3}, final_grade=final_grade,
        )
        self.assertTrue(labels[0].auditor_required)
        self.assertEqual(labels[0].reasons, [])

    def test_correct_action_gets_no_label(self) -> None:
        trace = [grader_mod.ActionRecord(step=1, kind="tool_call")]
        labels = grader_mod.label_actions(trace, checkpoints_passed_by_step={0: 0, 1: 1})
        self.assertEqual(labels[0].reasons, [])
        self.assertFalse(labels[0].auditor_required)


class McNemarExactTests(unittest.TestCase):
    """Hand-computed exact one-sided binomial p-values, independently derived with
    fractions.Fraction so the test does not just re-implement analyze.py's own formula."""

    def _hand_p(self, k: int, n: int) -> Fraction:
        from math import comb
        return sum(Fraction(comb(n, i), 2 ** n) for i in range(k, n + 1))

    def test_n1_b1_c0(self) -> None:
        result = analyze.mcnemar_one_sided(1, 0)
        expected = float(self._hand_p(1, 1))
        self.assertAlmostEqual(result.p_value, expected, places=9)
        self.assertAlmostEqual(result.p_value, 0.5, places=9)

    def test_n4_b4_c0(self) -> None:
        result = analyze.mcnemar_one_sided(4, 0)
        expected = float(self._hand_p(4, 4))
        self.assertAlmostEqual(result.p_value, expected, places=9)
        self.assertAlmostEqual(result.p_value, 0.0625, places=9)
        self.assertFalse(result.significant)  # 0.0625 >= alpha=0.05 -> not significant

    def test_n5_b4_c1(self) -> None:
        result = analyze.mcnemar_one_sided(4, 1)
        expected = float(self._hand_p(4, 5))
        self.assertAlmostEqual(result.p_value, expected, places=9)
        self.assertAlmostEqual(result.p_value, 6 / 32, places=9)

    def test_n18_b13_c5_matches_condition1_threshold_case(self) -> None:
        result = analyze.mcnemar_one_sided(13, 5)
        expected = float(self._hand_p(13, 18))
        self.assertAlmostEqual(result.p_value, expected, places=9)
        self.assertLess(result.p_value, 0.05)
        self.assertTrue(result.significant)

    def test_alpha_boundary_uses_strict_less_than(self) -> None:
        # n=4,b=4 -> p=0.0625, NOT significant at alpha=0.05 (0.0625 >= 0.05).
        result = analyze.mcnemar_one_sided(4, 0, alpha=0.05)
        self.assertFalse(result.significant)


class GapClosureTests(unittest.TestCase):
    def _row(self, template, seed, arm, success, tokens=100):
        return schema.ResultRow(
            template=template, seed=seed, arm=arm, binary_success=success,
            checkpoints_passed=2 if success else 1, checkpoints_total=2,
            actions_used=10, wall_seconds=30.0, tokens=tokens,
            wrong_actions=0, stale_actions=0, asks=0, abstains=0,
            unsupported_claims=0, verification_before_submit=True,
            trace_path="/dev/null/does-not-exist.jsonl",
        )

    def test_ratio_mode_when_denominator_positive(self) -> None:
        rows = []
        templates = schema.MUTATING_TEMPLATES
        for i, t in enumerate(templates):
            rows.append(self._row(t, 0, "weak+AIOS", True))
            rows.append(self._row(t, 0, "weak+checklist", False))
            rows.append(self._row(t, 0, "strong-raw", i % 2 == 0))
        result = analyze.gap_closure(rows, templates=templates)
        self.assertEqual(result.mode, "ratio")
        self.assertFalse(result.denominator_degenerate)

    def test_fallback_mode_when_denominator_degenerate(self) -> None:
        rows = []
        templates = schema.MUTATING_TEMPLATES
        for t in templates:
            rows.append(self._row(t, 0, "weak+AIOS", True))
            rows.append(self._row(t, 0, "weak+checklist", True))
            rows.append(self._row(t, 0, "strong-raw", False))  # strong-raw <= checklist
        result = analyze.gap_closure(rows, templates=templates)
        self.assertEqual(result.mode, "fallback_s_aios_ge_s_strong")
        self.assertTrue(result.denominator_degenerate)
        self.assertTrue(result.passes)  # AIOS(1.0) >= strong(0.0), CI should be positive


class SchemaValidationTests(unittest.TestCase):
    def _valid_row(self) -> schema.ResultRow:
        return schema.ResultRow(
            template="api_migration", seed=0, arm="weak+AIOS", binary_success=True,
            checkpoints_passed=3, checkpoints_total=3, actions_used=20, wall_seconds=120.0,
            tokens=500, wrong_actions=0, stale_actions=0, asks=0, abstains=0,
            unsupported_claims=0, verification_before_submit=True, trace_path="trace.jsonl",
        )

    def test_valid_row_has_no_errors(self) -> None:
        self.assertEqual(schema.validate_row(self._valid_row()), [])

    def test_unknown_arm_is_flagged(self) -> None:
        row = self._valid_row()
        row.arm = "not-a-real-arm"
        errors = schema.validate_row(row)
        self.assertTrue(any("unknown arm" in e for e in errors))

    def test_checkpoints_passed_out_of_range_is_flagged(self) -> None:
        row = self._valid_row()
        row.checkpoints_passed = 5
        errors = schema.validate_row(row)
        self.assertTrue(any("checkpoints_passed" in e for e in errors))

    def test_negative_tokens_flagged(self) -> None:
        row = self._valid_row()
        row.tokens = -1
        errors = schema.validate_row(row)
        self.assertTrue(any("tokens" in e for e in errors))

    def test_restarted_success_conflict_flagged(self) -> None:
        row = self._valid_row()
        row.restarted = True
        row.binary_success = True
        errors = schema.validate_row(row)
        self.assertTrue(any("restarted" in e for e in errors))

    def test_actions_used_over_cap_flagged(self) -> None:
        row = self._valid_row()
        row.actions_used = 500
        errors = schema.validate_row(row)
        self.assertTrue(any("actions_used" in e for e in errors))

    def test_duplicate_key_detected_in_table(self) -> None:
        row1 = self._valid_row()
        row2 = self._valid_row()
        errors = schema.validate_table([row1, row2])
        self.assertTrue(any("duplicate key" in e for e in errors))

    def test_roundtrip_read_write(self) -> None:
        import tempfile
        rows = [self._valid_row()]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "results.jsonl"
            schema.write_table(path, rows)
            loaded = schema.read_table(path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].as_dict(), rows[0].as_dict())


class ArmsInterfaceTests(unittest.TestCase):
    def test_five_required_arms_plus_one_optional(self) -> None:
        self.assertEqual(len(arms.ARMS), 6)
        self.assertEqual(len(arms.REQUIRED_ARMS), 5)
        self.assertIn("strong+AIOS", arms.ARMS)
        self.assertTrue(arms.ARMS["strong+AIOS"].optional)
        for name in ("strong-raw", "weak-raw", "weak+checklist", "weak+memory", "weak+AIOS"):
            self.assertIn(name, arms.REQUIRED_ARMS)

    def test_budget_caps_match_frozen_values(self) -> None:
        self.assertEqual(arms.FROZEN_BUDGET.wall_seconds, 45 * 60)
        self.assertEqual(arms.FROZEN_BUDGET.max_actions, 200)
        self.assertTrue(arms.FROZEN_BUDGET.restart_is_failure)
        self.assertTrue(arms.FROZEN_BUDGET.model_calls_count_toward_budget)

    def test_checklist_text_is_nontrivial_and_generic(self) -> None:
        self.assertGreater(len(arms.CHECKLIST_TEXT), 200)
        self.assertNotIn("AIOS", arms.CHECKLIST_TEXT)  # ceremony control must not name the runtime

    def test_run_arm_is_an_unimplemented_stub(self) -> None:
        with self.assertRaises(NotImplementedError):
            arms.run_arm("weak+AIOS", env=None)

    def test_run_arm_rejects_unknown_arm_before_stub_error(self) -> None:
        with self.assertRaises(ValueError):
            arms.run_arm("not-a-real-arm", env=None)


class MemoryPolicyTests(unittest.TestCase):
    def test_naive_policy_always_injects_regardless_of_mutation(self) -> None:
        policy = arms.NaiveMemoryPolicy()
        policy.store("api_migration", seed=0, lesson="watch for renamed functions", step_stored=10)
        result = policy.inject("api_migration", seed=1, context={"mutation_count_since_store": 3})
        self.assertFalse(result.suppressed)
        self.assertEqual(result.lesson, "watch for renamed functions")

    def test_gated_policy_suppresses_when_stale(self) -> None:
        policy = arms.GatedMemoryPolicy()
        policy.store("api_migration", seed=0, lesson="watch for renamed functions", step_stored=10)
        result = policy.inject("api_migration", seed=1, context={"mutation_count_since_store": 1})
        self.assertTrue(result.suppressed)
        self.assertIsNone(result.lesson)

    def test_gated_policy_injects_when_fresh(self) -> None:
        policy = arms.GatedMemoryPolicy()
        policy.store("api_migration", seed=0, lesson="watch for renamed functions", step_stored=10)
        result = policy.inject("api_migration", seed=1, context={"mutation_count_since_store": 0})
        self.assertFalse(result.suppressed)
        self.assertEqual(result.lesson, "watch for renamed functions")

    def test_lesson_cap_enforced(self) -> None:
        with self.assertRaises(ValueError):
            arms.MemoryRecord(template="x", seed=0, lesson="a" * 501, step_stored=0)

    def test_build_memory_policy_factory(self) -> None:
        self.assertIsNone(arms.build_memory_policy(None))
        self.assertIsInstance(arms.build_memory_policy("naive"), arms.NaiveMemoryPolicy)
        self.assertIsInstance(arms.build_memory_policy("gated"), arms.GatedMemoryPolicy)
        with self.assertRaises(ValueError):
            arms.build_memory_policy("bogus")


class AnalyzeVerdictFixtureTests(unittest.TestCase):
    """Synthetic result-table fixtures exercising the full compute_verdict() path,
    including SS5 condition 4's trace causal rule (analyze.py's own trace schema)."""

    def _row(self, template, seed, arm, *, success, tokens, unsupported=0, checkpoints_total=2, trace_path=""):
        return schema.ResultRow(
            template=template, seed=seed, arm=arm, binary_success=success,
            checkpoints_passed=checkpoints_total if success else 0, checkpoints_total=checkpoints_total,
            actions_used=20, wall_seconds=60.0, tokens=tokens,
            wrong_actions=0, stale_actions=0, asks=0, abstains=0,
            unsupported_claims=unsupported, verification_before_submit=True,
            trace_path=trace_path or "no-trace.jsonl",
        )

    def _write_verified_trace(self, path: Path) -> None:
        events = [
            {"step": 1, "type": "checkpoint_result", "checkpoint_id": "cp1", "passed": False},
            {"step": 3, "type": "drift_detected", "checkpoint_id": None, "passed": None, "detail": "cfg changed"},
            {"step": 5, "type": "checkpoint_result", "checkpoint_id": "cp1", "passed": True},
        ]
        with open(path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

    def test_win_fixture_produces_win_verdict(self) -> None:
        import tempfile
        rows: list[schema.ResultRow] = []
        mutating = list(schema.MUTATING_TEMPLATES)
        static = list(schema.STATIC_TEMPLATES)

        with tempfile.TemporaryDirectory() as d:
            trace_path = str(Path(d) / "recovery_trace.jsonl")
            self._write_verified_trace(Path(trace_path))

            # 18 mutating instances (6 templates x 3 seeds): weak+AIOS succeeds on 16,
            # weak+checklist succeeds on 3 (all inside the AIOS-success set -> 3 ties),
            # giving wins_a=13, wins_b=0, n_discordant=13 (>= threshold, McNemar exact
            # p = 0.5**13 << 0.05).
            instances = [(t, s) for t in mutating for s in schema.SEEDS]
            checklist_success_idx = {0, 1, 2}
            aios_fail_idx = {16, 17}
            for i, (t, s) in enumerate(instances):
                aios_success = i not in aios_fail_idx
                checklist_success = i in checklist_success_idx
                rows.append(self._row(t, s, "weak+AIOS", success=aios_success, tokens=100,
                                       trace_path=trace_path if (aios_success and not checklist_success) else ""))
                rows.append(self._row(t, s, "weak+checklist", success=checklist_success, tokens=100))
                rows.append(self._row(t, s, "strong-raw", success=(i % 2 == 0), tokens=800))
                rows.append(self._row(t, s, "weak-raw", success=(i % 3 == 0), tokens=90))
                rows.append(self._row(t, s, "weak+memory", success=(i % 4 == 0), tokens=90))

            # 6 static instances (2 templates x 3 seeds): AIOS and checklist tie
            # (delta=0, within margin) with equal unsupported-claim rates.
            for t in static:
                for s in schema.SEEDS:
                    rows.append(self._row(t, s, "weak+AIOS", success=True, tokens=50, checkpoints_total=2))
                    rows.append(self._row(t, s, "weak+checklist", success=True, tokens=50, checkpoints_total=2))

            report = analyze.compute_verdict(rows)

        self.assertTrue(report.condition1.passes, report.condition1)
        self.assertEqual(report.condition1.comparison.wins_a, 13)
        self.assertTrue(report.condition2.passes, report.condition2)
        self.assertTrue(report.condition3.passes, report.condition3)
        self.assertTrue(report.condition4.passes, report.condition4)
        self.assertEqual(report.verdict, "WIN")
        # format_verdict_block must not raise on a full report.
        block = analyze.format_verdict_block(report)
        self.assertIn("VERDICT: WIN", block)

    def test_stop_fixture_produces_stop_verdict(self) -> None:
        rows: list[schema.ResultRow] = []
        mutating = list(schema.MUTATING_TEMPLATES)
        instances = [(t, s) for t in mutating for s in schema.SEEDS]
        # weak+AIOS wins only 5, weak+checklist wins 8 -> clearly under threshold AND
        # McNemar non-significant favoring AIOS (b=5 < c=8).
        aios_win_idx = set(range(0, 5))
        checklist_win_idx = set(range(5, 13))
        for i, (t, s) in enumerate(instances):
            if i in aios_win_idx:
                aios_success, checklist_success = True, False
            elif i in checklist_win_idx:
                aios_success, checklist_success = False, True
            else:
                aios_success = checklist_success = (i % 2 == 0)
            rows.append(self._row(t, s, "weak+AIOS", success=aios_success, tokens=100))
            rows.append(self._row(t, s, "weak+checklist", success=checklist_success, tokens=100))

        report = analyze.compute_verdict(rows)
        self.assertFalse(report.condition1.meets_win_count)
        self.assertFalse(report.condition1.comparison.mcnemar.significant)
        self.assertEqual(report.verdict, "STOP")
        block = analyze.format_verdict_block(report)
        self.assertIn("VERDICT: STOP", block)


class CostSweepTests(unittest.TestCase):
    def test_cost_model_prices_wrong_ask_abstain_only(self) -> None:
        row = schema.ResultRow(
            template="api_migration", seed=0, arm="weak+AIOS", binary_success=True,
            checkpoints_passed=3, checkpoints_total=3, actions_used=20, wall_seconds=60.0,
            tokens=100, wrong_actions=2, stale_actions=0, asks=1, abstains=1,
            unsupported_claims=0, verification_before_submit=True, trace_path="t.jsonl",
        )
        self.assertEqual(analyze.cost_model_total(row, wrong_cost=5), 2 * 5 + 1 + 1)

    def test_h2_holds_requires_dominance_across_entire_sweep(self) -> None:
        points = [
            analyze.CostSweepPoint(3, cost_aios=1.0, cost_checklist=2.0, aios_dominates=True),
            analyze.CostSweepPoint(5, cost_aios=1.0, cost_checklist=2.0, aios_dominates=True),
            analyze.CostSweepPoint(10, cost_aios=5.0, cost_checklist=2.0, aios_dominates=False),
        ]
        self.assertFalse(analyze.h2_holds(points))
        self.assertTrue(analyze.h2_holds(points[:2]))


class TraceCausalRuleTests(unittest.TestCase):
    def test_verified_when_trigger_precedes_flip_within_lag(self) -> None:
        events = [
            analyze.TraceEvent(step=1, type="checkpoint_result", checkpoint_id="cp1", passed=False),
            analyze.TraceEvent(step=2, type="gate_reject"),
            analyze.TraceEvent(step=4, type="checkpoint_result", checkpoint_id="cp1", passed=True),
        ]
        result = analyze.causal_recovery_check(events)
        self.assertEqual(result.status, "verified")

    def test_not_verified_when_lag_exceeds_window(self) -> None:
        events = [
            analyze.TraceEvent(step=1, type="checkpoint_result", checkpoint_id="cp1", passed=False),
            analyze.TraceEvent(step=2, type="gate_reject"),
            analyze.TraceEvent(step=10, type="checkpoint_result", checkpoint_id="cp1", passed=True),
        ]
        result = analyze.causal_recovery_check(events)
        self.assertEqual(result.status, "not_verified")

    def test_insufficient_data_on_empty_trace(self) -> None:
        result = analyze.causal_recovery_check([])
        self.assertEqual(result.status, "insufficient_trace_data")

    def test_load_trace_missing_file_returns_empty(self) -> None:
        events = analyze.load_trace("/definitely/not/a/real/path.jsonl")
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
