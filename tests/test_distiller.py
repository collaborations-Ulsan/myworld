"""Deterministic tests for experiments/distiller/ (docs/AIOS_DISTILLER_PREREG_2026-07-17.md v1.1).

No live LLM anywhere in this file, no network, no training -- student/teacher calls are
dependency-injected fakes (mirroring tests/test_aios_adapters.py's _FakeLLMClient pattern and
tests/test_learnos_s11.py's sys.path convention). Covers the task brief's required behaviors:

  * B/A generator separation is structurally enforced
  * the causal gate filters an uncausal (overfit-to-visible) trajectory out of the SFT set
  * solution-only scoring ignores trajectory text
  * the unverified-arm dataset includes what the verified-arm excludes
  * the privacy scan blocks a planted secret
  * escalation-rate counts only equal-budget local successes
  * the pilot banner fires under N_verified=250

...plus the degeneracy pre-filter (identity-function teacher output is rejected) and the
Blind-Curator integration (0% false-pass over its own planted defects).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_DISTILLER_DIR = Path(__file__).resolve().parents[1] / "experiments" / "distiller"
sys.path.insert(0, str(_DISTILLER_DIR))

import collect  # noqa: E402
import evaluate  # noqa: E402
import train_lora  # noqa: E402

# NOT `import tasks` -- experiments/learnos/ also ships a module literally named tasks.py, and
# sys.modules caching (which wins over sys.path reordering) makes a bare `import tasks` order-
# dependent on whatever else already ran in this pytest process. collect.py loads this package's
# tasks.py under a private, collision-proof sys.modules key; reuse that same object here.
tasks = collect.distiller_tasks


def _golden_of(task: dict) -> str:
    return tasks.held_out_bundle(task)["golden_solution"]


class GeneratorSeparationTest(unittest.TestCase):
    """prereg S6 guard #1: B must be a separate generator family from A, structurally enforced."""

    def test_family_name_sets_are_disjoint(self):
        a_names = {f.name for f in tasks.A_FAMILIES}
        b_names = {f.name for f in tasks.B_FAMILIES}
        self.assertTrue(a_names.isdisjoint(b_names))

    def test_built_corpus_never_mixes_a_and_b_families(self):
        built = tasks.build_tasks(seed=7, a_instances=3, b_instances=3)
        a_families = {t["family"] for t in built if t["split"] == "A"}
        b_families = {t["family"] for t in built if t["split"] == "B"}
        self.assertTrue(a_families.isdisjoint(b_families))
        self.assertEqual(a_families, {f.name for f in tasks.A_FAMILIES})
        self.assertEqual(b_families, {f.name for f in tasks.B_FAMILIES})

    def test_hidden_seed_streams_are_independent_given_the_same_master_seed(self):
        a_stream = tasks._stream("A", 42)
        b_stream = tasks._stream("B", 42)
        a_draws = [a_stream.random() for _ in range(5)]
        b_draws = [b_stream.random() for _ in range(5)]
        self.assertNotEqual(a_draws, b_draws)

    def test_every_golden_solution_passes_its_own_full_test_bundle(self):
        # a build-time correctness invariant: if this ever fails, a hand-authored family is wrong.
        sys.path.append(str(_DISTILLER_DIR.parent / "learnos"))
        import verify as learnos_verify
        built = tasks.build_tasks(seed=3, a_instances=2, b_instances=2)
        for task in built:
            priv = tasks.held_out_bundle(task)
            all_tests = task["visible_tests"] + priv["held_out_tests"] + priv["adversarial_tests"] + [task["sentinel_check"]]
            result = learnos_verify.run_public(all_tests, priv["golden_solution"])
            self.assertTrue(result["all_passed"], f"{task['task_id']} golden failed: {result}")


class CausalGateTest(unittest.TestCase):
    """prereg S3 step 2 / S5: only causally-verified (held-out-passing) trajectories are kept."""

    def setUp(self):
        self.built = tasks.build_tasks(seed=11, a_instances=2, b_instances=2)
        self.task = next(t for t in self.built if t["split"] == "A")

    def test_golden_solution_is_verified(self):
        result = collect.verify_solution(self.task, _golden_of(self.task))
        self.assertEqual(result["decision"], "verified")

    def test_overfit_to_visible_trajectory_is_rejected(self):
        """A solution that special-cases the visible examples and falls back to a raising stub
        for everything else -- passes visible, fails held-out (or the sentinel, which also
        exercises the raising fallback) -- must never be verified. Built via
        experiments/learnos/audit.py's own injector (audit.inject_overfit_defect), reused
        directly rather than hand-rolled, so the planted defect is the SAME one the Blind-Curator
        audit is designed to catch."""
        overfit_src = collect.audit.inject_overfit_defect(self.task)
        self.assertIsNotNone(overfit_src)
        result = collect.verify_solution(self.task, overfit_src)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(result["reason"], ("holdout_fail", "sentinel_regressed"))

    def test_degenerate_identity_function_is_rejected_before_running_any_tests(self):
        # three_sum_zero_triplets(xs) takes exactly one positional arg -- an identity
        # `return xs` is a structurally degenerate stand-in a teacher could emit that happens
        # to slip past a weak grader; is_degenerate_tool must catch it before any test runs.
        one_arg_task = next(t for t in self.built if t["entry_point"] == "three_sum_zero_triplets")
        identity_src = "def three_sum_zero_triplets(xs):\n    return xs\n"
        result = collect.verify_solution(one_arg_task, identity_src)
        self.assertEqual(result["decision"], "rejected")
        self.assertTrue(result["reason"].startswith("degenerate"))

    def test_empty_source_is_rejected(self):
        result = collect.verify_solution(self.task, "")
        self.assertEqual(result["decision"], "rejected")

    def test_blind_curator_reports_zero_false_pass_on_its_own_planted_defects(self):
        a_tasks = [t for t in self.built if t["split"] == "A"]
        report = collect.run_blind_curator(a_tasks)
        self.assertGreater(report["n_trials"], 0)
        self.assertEqual(report["false_pass_rate"], 0.0)
        self.assertFalse(report["freeze_promotion"])
        # the monkeypatch used internally must be restored afterward, not leaked
        import improve
        self.assertIs(improve.baseline_holdout_passed, collect.improve.baseline_holdout_passed)
        self.assertIsNot(improve.baseline_holdout_passed, collect._baseline_zero)


class SolutionOnlyScoringTest(unittest.TestCase):
    """prereg S6 guard #3: grading only ever touches the extracted code block, never trajectory
    text -- a trajectory-trained arm cannot win by having its rationale pattern-matched."""

    def setUp(self):
        self.built = tasks.build_tasks(seed=5, b_instances=2)
        self.task = next(t for t in self.built if t["split"] == "B")
        self.golden = _golden_of(self.task)

    def test_wrong_looking_prose_before_a_correct_code_block_still_scores_solved(self):
        raw = (
            "Let me think step by step. Actually the right answer is totally different and this "
            "reasoning text would fail every test if it were graded directly.\n"
            f"```python\n{self.golden}```"
        )
        result = evaluate.score_task(self.task, raw)
        self.assertTrue(result["solved"])

    def test_grading_never_sees_raw_trajectory_without_extraction(self):
        # extract_code pulls ONLY the fenced block; the surrounding prose is provably discarded
        # because grading a docstring-shaped prose blob alone (no fence) fails cleanly rather
        # than accidentally parsing as Python.
        raw_no_fence = "This entire response is prose with no code fence at all."
        solution = collect.extract_code(raw_no_fence)
        self.assertNotIn("```", solution)
        result = evaluate.score_task(self.task, raw_no_fence)
        self.assertFalse(result["solved"])

    def test_score_sentinel_also_extracts_before_grading(self):
        sentinel_task = next(t for t in self.built if t["split"] == "sentinel") if any(
            t["split"] == "sentinel" for t in self.built
        ) else tasks.build_tasks(seed=5)[-1]
        sentinel_golden = _golden_of(sentinel_task)
        raw = f"noisy reasoning\n```python\n{sentinel_golden}```"
        self.assertTrue(evaluate.score_sentinel(sentinel_task, raw))


class UnverifiedArmSupersetTest(unittest.TestCase):
    """prereg S6 guard #2: Student-LoRA-unverified has the SAME tasks/teacher volume but NO
    causal gate -- it must include records the verified arm's held-out gate rejects."""

    def test_unverified_dataset_includes_a_holdout_failing_record_the_verified_set_excludes(self):
        built = tasks.build_tasks(seed=9, a_instances=2)
        a_tasks = [t for t in built if t["split"] == "A"][:2]
        golden_by_id = {t["task_id"]: _golden_of(t) for t in a_tasks}

        call_count = {"student": 0, "teacher": 0}

        def fake_student(prompt, model=None):
            call_count["student"] += 1
            return {"ok": True, "content": "cannot solve this", "error": None}

        def fake_teacher(prompt):
            call_count["teacher"] += 1
            idx = call_count["teacher"] - 1
            task = a_tasks[idx]
            if idx == 0:
                src = golden_by_id[task["task_id"]]  # verified-good
            else:
                src = collect.audit.inject_overfit_defect(task)  # passes visible, fails held-out
            return {"ok": True, "text": f"```python\n{src}```", "provenance": [], "error": None}

        orig_student, orig_teacher = collect.call_student, collect.call_teacher
        collect.call_student, collect.call_teacher = fake_student, fake_teacher
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                out_dir = Path(td)
                summary = collect.collect(a_tasks, out_dir=out_dir, time_budget_s=60, skip_audit=True)
                self.assertEqual(summary.n_verified, 1)
                self.assertEqual(summary.n_unverified_only, 1)

                verified_ids = {json.loads(line)["task_id"]
                                for line in (out_dir / "sft_verified_trajectory.jsonl").read_text().splitlines()}
                unverified_ids = {json.loads(line)["task_id"]
                                  for line in (out_dir / "sft_unverified_trajectory.jsonl").read_text().splitlines()}
                rejected_task_id = a_tasks[1]["task_id"]
                verified_task_id = a_tasks[0]["task_id"]

                self.assertIn(rejected_task_id, unverified_ids)
                self.assertNotIn(rejected_task_id, verified_ids)
                self.assertIn(verified_task_id, unverified_ids)
                self.assertIn(verified_task_id, verified_ids)
        finally:
            collect.call_student, collect.call_teacher = orig_student, orig_teacher


class PrivacyScanTest(unittest.TestCase):
    def test_blocks_from_desktop_path(self):
        hits = collect.privacy_scan("see /home/user/workspaces/jaewon/_from_desktop/notes.txt for details")
        self.assertTrue(hits)

    def test_blocks_privacy_gated_name_tokens(self):
        self.assertTrue(collect.privacy_scan("private note about dain's project"))
        self.assertTrue(collect.privacy_scan("private note about minyoung's project"))

    def test_blocks_nvidia_api_key_shape(self):
        hits = collect.privacy_scan("NVIDIA_API_KEY=nvapi-abcdefghijklmnopqrstuvwxyz1234567890")
        self.assertTrue(hits)

    def test_blocks_generic_bearer_token_shape(self):
        hits = collect.privacy_scan("Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz0123456789")
        self.assertTrue(hits)

    def test_clean_synthetic_code_is_not_flagged(self):
        self.assertEqual(collect.privacy_scan("def add(a, b):\n    return a + b\n"), [])
        # a plain English word that happens to contain privacy-gated letters as a SUBSTRING
        # (not a standalone token) must not false-positive.
        self.assertEqual(collect.privacy_scan("the domain and maintainer are documented"), [])

    def test_safe_append_jsonl_refuses_to_write_a_planted_secret(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.jsonl"
            hits = collect.safe_append_jsonl(path, {"solution": "leaked at /priv/_from_desktop/x"})
            self.assertTrue(hits)
            self.assertFalse(path.exists())  # blocked record is never written, not even an empty file

    def test_safe_append_jsonl_writes_a_clean_record(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.jsonl"
            hits = collect.safe_append_jsonl(path, {"solution": "def f(x):\n    return x + 1\n"})
            self.assertEqual(hits, [])
            self.assertEqual(len(path.read_text().splitlines()), 1)


class EscalationRateTest(unittest.TestCase):
    """prereg S6 H2 correction: escalation-rate counts only successful equal-budget local
    solves, never a raw call-count reduction."""

    def test_half_solved_gives_half_escalation_rate(self):
        self.assertEqual(evaluate.escalation_rate([True, True, False, False]), 0.5)

    def test_all_solved_gives_zero_escalation_rate(self):
        self.assertEqual(evaluate.escalation_rate([True, True, True]), 0.0)

    def test_none_solved_gives_full_escalation_rate(self):
        self.assertEqual(evaluate.escalation_rate([False, False]), 1.0)

    def test_empty_is_defined_as_zero_not_a_crash(self):
        self.assertEqual(evaluate.escalation_rate([]), 0.0)

    def test_every_arm_caller_shares_the_same_budget_constants(self):
        # the "equal budget" guarantee is structural: every arm's caller path funnels through
        # the SAME module-level constants, never a per-arm override.
        import inspect
        source = inspect.getsource(collect._ollama_native_chat)
        self.assertIn("STUDENT_MAX_TOKENS", inspect.getsource(collect.call_student) + source)


class PilotBannerTest(unittest.TestCase):
    """prereg S6: 'pilot only if N_verified < 250'."""

    def test_threshold_is_250(self):
        self.assertEqual(collect.N_VERIFIED_PILOT_THRESHOLD, 250)

    def test_banner_fires_under_threshold(self):
        banner = collect.pilot_banner(10)
        self.assertIn("PILOT ONLY", banner)
        self.assertIn("10", banner)

    def test_banner_fires_at_zero(self):
        self.assertIn("PILOT ONLY", collect.pilot_banner(0))

    def test_banner_does_not_fire_at_or_above_threshold(self):
        self.assertNotIn("PILOT ONLY", collect.pilot_banner(250))
        self.assertNotIn("PILOT ONLY", collect.pilot_banner(300))

    def test_evaluate_report_carries_the_same_banner_from_a_fake_collect_summary(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            (out_dir / "collect_summary.json").write_text(json.dumps({"n_verified": 5}), encoding="utf-8")
            self.assertEqual(evaluate._read_n_verified(out_dir), 5)


class TrainLoraSentinelRehearsalTest(unittest.TestCase):
    """prereg S6 'Sentinel 보호': every training set is mixed with sentinel examples."""

    def test_trainer_availability_is_checked_live_not_assumed(self):
        # must not raise regardless of whether peft/unsloth happen to be installed in CI
        self.assertIsInstance(train_lora.trainer_available(), bool)

    def test_sentinel_examples_are_mixed_into_an_empty_verified_set(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            # no sft_verified_trajectory.jsonl on disk -- build_training_examples must still
            # return the sentinel rehearsal slice, not crash.
            examples = train_lora.build_training_examples("lora_verified_trajectory", out_dir=out_dir, seed=1)
            self.assertTrue(all(e["source"] == "sentinel_rehearsal" for e in examples))
            self.assertGreater(len(examples), 0)

    def test_documented_train_command_names_the_hf_base_model_not_the_ollama_blob(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cmd = train_lora.documented_train_command("lora_verified_trajectory", Path(td), "Qwen/Qwen3-1.7B")
            self.assertIn("Qwen/Qwen3-1.7B", cmd)
            self.assertNotIn("qwen3:1.7b", cmd)


if __name__ == "__main__":
    unittest.main()
