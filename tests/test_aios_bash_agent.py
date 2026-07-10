"""BashFallbackAgent tests — mini-swe-agent semantics (M5/D1-2), scripted
adapters only. No real model, no ollama, no network. `sandbox="subprocess"`
is forced everywhere so results don't depend on whether `bwrap` happens to be
installed on the machine running the suite (build_bwrap_argv itself is
covered by a dedicated pure-argv test)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_bash_agent as BA  # noqa: E402


def scripted(replies):
    it = iter(replies)
    return lambda _prompt: next(it)


class BashBlockExtractionTests(unittest.TestCase):
    def test_extracts_single_bash_block(self):
        reply = "THOUGHT: list files\n\n```bash\nls -la\n```"
        self.assertEqual(BA._extract_bash_block(reply), "ls -la")

    def test_no_block_returns_none(self):
        reply = "The answer is 42, no command needed here."
        self.assertIsNone(BA._extract_bash_block(reply))

    def test_extracts_first_block_when_multiple_present(self):
        reply = "```bash\nfirst\n```\nsome text\n```bash\nsecond\n```"
        self.assertEqual(BA._extract_bash_block(reply), "first")


class CompletionMarkerTests(unittest.TestCase):
    def test_marker_first_line_and_zero_exit_signals_done(self):
        stdout = f"{BA.COMPLETION_MARKER}\nthe final answer\nsecond line\n"
        done, submission = BA._check_completion(stdout, 0)
        self.assertTrue(done)
        self.assertEqual(submission.strip(), "the final answer\nsecond line")

    def test_marker_with_nonzero_exit_does_not_signal_done(self):
        stdout = f"{BA.COMPLETION_MARKER}\nanswer\n"
        done, _ = BA._check_completion(stdout, 1)
        self.assertFalse(done)

    def test_ordinary_output_does_not_signal_done(self):
        done, _ = BA._check_completion("just some output\n", 0)
        self.assertFalse(done)


class DenylistTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/tmp/claude-1000-bash-agent-tests-root")
        self.root.mkdir(parents=True, exist_ok=True)

    def test_rm_rf_root_slash_refused(self):
        self.assertIsNotNone(BA._denylist_violation("rm -rf /", self.root))

    def test_rm_rf_home_tilde_refused(self):
        self.assertIsNotNone(BA._denylist_violation("rm -rf ~", self.root))

    def test_rm_rf_outside_workspace_refused(self):
        self.assertIsNotNone(BA._denylist_violation("rm -rf /etc/passwd", self.root))

    def test_rm_rf_inside_workspace_allowed(self):
        target = self.root / "scratch"
        self.assertIsNone(BA._denylist_violation(f"rm -rf {target}", self.root))

    def test_plain_rm_without_rf_flags_allowed(self):
        self.assertIsNone(BA._denylist_violation("rm file.txt", self.root))

    def test_fork_bomb_refused(self):
        self.assertIsNotNone(BA._denylist_violation(":(){ :|:& };:", self.root))

    def test_mkfs_refused(self):
        self.assertIsNotNone(BA._denylist_violation("mkfs.ext4 /dev/sda1", self.root))

    def test_raw_device_write_refused(self):
        self.assertIsNotNone(BA._denylist_violation("echo x > /dev/sda", self.root))

    def test_ordinary_command_allowed(self):
        self.assertIsNone(BA._denylist_violation("ls -la && grep -r foo .", self.root))


class BwrapArgvTests(unittest.TestCase):
    def test_bwrap_argv_binds_only_workspace_root(self):
        # nested under /tmp/... so root.parent isn't the shared /tmp tmpfs bind
        root = Path("/tmp/claude-1000-bash-agent-tests-root/workspace")
        argv = BA.build_bwrap_argv("echo hi", root)
        self.assertIn("--bind", argv)
        i = argv.index("--bind")
        self.assertEqual(argv[i + 1], str(root))
        self.assertEqual(argv[i + 2], str(root))
        # nothing above the workspace root (e.g. its parent) is ever bound
        self.assertNotIn(str(root.parent), argv)
        self.assertEqual(argv[-3:], ["bash", "-c", "echo hi"])

    def test_bwrap_argv_never_names_privacy_dirs(self):
        root = Path("/tmp/claude-1000-bash-agent-tests-root")
        argv = BA.build_bwrap_argv("ls", root)
        joined = " ".join(argv)
        for privacy_dir in ("_from_desktop", "dain", "minyoung"):
            self.assertNotIn(privacy_dir, joined)


class BashFallbackAgentRunTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/tmp/claude-1000-bash-agent-run-tests")
        self.root.mkdir(parents=True, exist_ok=True)

    def _agent(self, adapter, **cfg_kwargs):
        cfg = BA.BashAgentConfig(sandbox="subprocess", timeout=10, **cfg_kwargs)
        return BA.BashFallbackAgent(adapter, root=self.root, config=cfg)

    def test_completion_marker_ends_run_with_answer(self):
        adapter = scripted([
            f"THOUGHT: done\n```bash\necho {BA.COMPLETION_MARKER}\necho 'the answer is 7'\n```",
        ])
        result = self._agent(adapter).run("what is the answer")
        self.assertEqual(result.exit_reason, "completed")
        self.assertEqual(result.answer, "the answer is 7")
        self.assertEqual(result.steps_used, 1)

    def test_observation_feedback_carries_prior_output_into_next_prompt(self):
        seen_prompts = []

        def adapter(prompt):
            seen_prompts.append(prompt)
            if len(seen_prompts) == 1:
                return "THOUGHT: probe\n```bash\necho MARKER_VALUE_123\n```"
            return f"THOUGHT: done\n```bash\necho {BA.COMPLETION_MARKER}\necho ok\n```"

        result = self._agent(adapter).run("probe then finish")
        self.assertEqual(result.exit_reason, "completed")
        self.assertEqual(len(result.observations), 2)
        first_obs = result.observations[0]
        self.assertEqual(first_obs.command, "echo MARKER_VALUE_123")
        self.assertIn("MARKER_VALUE_123", first_obs.stdout)
        self.assertEqual(first_obs.returncode, 0)
        # second prompt must include the first observation's output (feedback loop)
        self.assertIn("MARKER_VALUE_123", seen_prompts[1])

    def test_max_steps_exit_is_honest(self):
        adapter = scripted([
            "THOUGHT: still working\n```bash\necho step1\n```",
            "THOUGHT: still working\n```bash\necho step2\n```",
        ])
        result = self._agent(adapter, max_steps=2).run("never finishes")
        self.assertEqual(result.exit_reason, "max_steps")
        self.assertEqual(result.steps_used, 2)
        self.assertEqual(result.answer, "")
        self.assertEqual(len(result.observations), 2)

    def test_no_bash_block_is_treated_as_final_answer(self):
        adapter = scripted(["The answer is 42. No command is needed."])
        result = self._agent(adapter).run("what is the answer")
        self.assertEqual(result.exit_reason, "no_bash_block")
        self.assertEqual(result.answer, "The answer is 42. No command is needed.")
        self.assertEqual(result.steps_used, 1)
        self.assertEqual(result.observations, [])

    def test_denylist_guard_refuses_and_continues_loop(self):
        adapter = scripted([
            "THOUGHT: nuke it\n```bash\nrm -rf /\n```",
            f"THOUGHT: fine, finishing\n```bash\necho {BA.COMPLETION_MARKER}\necho done\n```",
        ])
        result = self._agent(adapter).run("try something destructive")
        self.assertEqual(result.exit_reason, "completed")
        self.assertEqual(result.answer, "done")
        self.assertEqual(len(result.observations), 2)
        refused_obs = result.observations[0]
        self.assertEqual(refused_obs.command, "rm -rf /")
        self.assertIn("refused", refused_obs.stdout.lower())
        self.assertEqual(refused_obs.returncode, 1)

    def test_real_command_executes_and_output_is_captured(self):
        adapter = scripted([
            "THOUGHT: math\n```bash\necho $((2+2))\n```",
            f"THOUGHT: report\n```bash\necho {BA.COMPLETION_MARKER}\necho 4\n```",
        ])
        result = self._agent(adapter).run("compute 2+2")
        # display text is stdout+stderr concatenated (may carry shell stderr
        # noise on some hosts); the actual command stdout must lead it
        self.assertTrue(result.observations[0].stdout.startswith("4"))
        self.assertEqual(result.answer, "4")


class RunBashAgentFunctionalTests(unittest.TestCase):
    def test_run_bash_agent_wraps_agent_class(self):
        adapter = scripted([f"```bash\necho {BA.COMPLETION_MARKER}\necho hi\n```"])
        result = BA.run_bash_agent("say hi", adapter=adapter, root="/tmp", sandbox="subprocess")
        self.assertEqual(result.exit_reason, "completed")
        self.assertEqual(result.answer, "hi")


if __name__ == "__main__":
    unittest.main()


class BwrapRuntimeFallbackTests(unittest.TestCase):
    def test_broken_bwrap_degrades_to_plain_subprocess_at_runtime(self) -> None:
        # bwrap exists but can't run (nested sandbox): first bwrap-level failure
        # in auto mode must degrade to plain subprocess and re-execute.
        from unittest import mock
        agent = BA.BashFallbackAgent(lambda p: "", root=".")
        with mock.patch.object(BA, "_bwrap_available", return_value=True), \
             mock.patch.object(BA, "build_bwrap_argv",
                               return_value=["bash", "-c", "echo 'bwrap: setting up uid map: Permission denied' >&2; exit 1"]):
            rc, stdout, display = agent._execute("echo hi")
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.strip(), "hi")
        self.assertTrue(agent._bwrap_broken)   # subsequent commands skip bwrap entirely
