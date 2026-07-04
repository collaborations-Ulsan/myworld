"""Tests for aios_agent_self.py — the composite AGENT SELF organ.

Hermetic: AIOS_HOME is pointed at a tmp dir so the real ~/.aios is never touched.
No network. Exercises the birth/learn/accept/checkpoint/carry lifecycle and the
draft-first + append-only DNA invariants.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location(
        "aios_agent_self_under_test", SCRIPTS / "aios_agent_self.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_agent_self_under_test"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class AgentSelfTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self._prev_home = os.environ.get("AIOS_HOME")
        self._prev_agent = os.environ.get("AIOS_AGENT_ID")
        os.environ["AIOS_HOME"] = self.tmp.name
        os.environ.pop("AIOS_AGENT_ID", None)  # use explicit agent ids in tests

    def tearDown(self):
        if self._prev_home is None:
            os.environ.pop("AIOS_HOME", None)
        else:
            os.environ["AIOS_HOME"] = self._prev_home
        if self._prev_agent is not None:
            os.environ["AIOS_AGENT_ID"] = self._prev_agent
        self.tmp.cleanup()

    # ── birth ──────────────────────────────────────────────────────────────
    def test_birth_seeds_identity_and_compiles(self):
        info = self.m.birth("a1")
        self.assertTrue(Path(info["path"]).exists())
        identity = self.m.agent_dir("a1") / "identity.md"
        self.assertTrue(identity.exists())
        body = Path(info["path"]).read_text()
        self.assertIn("## Where I left off", body)
        self.assertIn("INJECTION POLICY", body)
        self.assertIn("68%->19%", body)
        self.assertIn("AIOS DNA:", body)
        self.assertGreater(info["word_count"], 0)

    def test_real_home_untouched(self):
        # env points at tmp — nothing should appear under the real ~/.aios/self/a1
        self.m.birth("a1")
        real = Path.home() / ".aios" / "self" / "a1"
        self.assertNotEqual(str(real), str(self.m.agent_dir("a1")))
        self.assertTrue(str(self.tmp.name) in str(self.m.agent_dir("a1")))

    # ── draft-first invariant ──────────────────────────────────────────────
    def test_learn_is_draft_not_in_self_until_accepted(self):
        self.m.birth("a1")
        e = self.m.learn("correction", "Always grep the ledger before asserting a number.",
                         agent_id="a1")
        self.assertEqual(e["status"], "draft")
        info = self.m.birth("a1")
        body = Path(info["path"]).read_text()
        self.assertNotIn("grep the ledger", body)  # draft must not appear

        self.m.accept(e["id"], reviewer="codex@myworld", note="verified useful", agent_id="a1")
        info2 = self.m.birth("a1")
        body2 = Path(info2["path"]).read_text()
        self.assertIn("grep the ledger", body2)  # accepted appears

    def test_accept_without_note_fails(self):
        self.m.birth("a1")
        e = self.m.learn("decision", "Chose stdlib over a new dep.", agent_id="a1")
        with self.assertRaises(ValueError):
            self.m.accept(e["id"], reviewer="codex@myworld", note="")

    def test_accept_without_reviewer_fails(self):
        self.m.birth("a1")
        e = self.m.learn("decision", "Chose stdlib over a new dep.", agent_id="a1")
        with self.assertRaises(ValueError):
            self.m.accept(e["id"], reviewer="", note="ok")

    def test_accepted_newest_first(self):
        self.m.birth("a1")
        e1 = self.m.learn("what_worked", "First learning about parallel tool calls.", agent_id="a1")
        e2 = self.m.learn("what_worked", "Second learning about background jobs.", agent_id="a1")
        self.m.accept(e1["id"], reviewer="r", note="n", agent_id="a1")
        self.m.accept(e2["id"], reviewer="r", note="n", agent_id="a1")
        body = Path(self.m.birth("a1")["path"]).read_text()
        i_first = body.index("First learning")
        i_second = body.index("Second learning")
        self.assertLess(i_second, i_first)  # newest (second) appears first

    # ── multi-line rejection ───────────────────────────────────────────────
    def test_multiline_learn_rejected(self):
        self.m.birth("a1")
        with self.assertRaises(ValueError):
            self.m.learn("limit", "line one\nline two", agent_id="a1")
        with self.assertRaises(ValueError):
            self.m.learn("limit", "   ", agent_id="a1")

    # ── max-words truncation ───────────────────────────────────────────────
    def test_max_words_truncation_note(self):
        self.m.birth("a1")
        for i in range(30):
            e = self.m.learn("decision", f"Decision number {i} " + ("word " * 20).strip(),
                             agent_id="a1")
            self.m.accept(e["id"], reviewer="r", note="n", agent_id="a1")
        info = self.m.birth("a1", max_words=120)
        body = Path(info["path"]).read_text()
        self.assertIn("older learnings not shown", body)
        self.assertLess(info["accepted_shown"], info["accepted_total"])

    # ── checkpoint ─────────────────────────────────────────────────────────
    def test_checkpoint_in_self(self):
        self.m.birth("a1")
        self.m.checkpoint("refactoring the launcher", "wire the dispatch", agent_id="a1")
        body = Path(self.m.birth("a1")["path"]).read_text()
        self.assertIn("refactoring the launcher", body)
        self.assertIn("wire the dispatch", body)

    # ── carry: all four targets ────────────────────────────────────────────
    def test_carry_all_targets(self):
        self.m.birth("a1")
        e = self.m.learn("what_worked", "Backgrounded the build and polled.", agent_id="a1")
        self.m.accept(e["id"], reviewer="r", note="n", agent_id="a1")

        claude = self.m.carry("claude", agent_id="a1")
        self.assertIn("```markdown", claude)
        self.assertIn("Backgrounded the build", claude)

        codex = self.m.carry("codex", agent_id="a1")
        self.assertIn("```markdown", codex)
        self.assertIn("AGENTS.md", codex)

        system = self.m.carry("system", agent_id="a1")
        self.assertNotIn("#", system)  # no markdown headers
        self.assertIn("Backgrounded the build", system)

        j = self.m.carry("json", agent_id="a1")
        self.assertIsInstance(j, dict)
        # round-trips through json
        parsed = json.loads(json.dumps(j))
        self.assertIn("self_md", parsed)
        self.assertEqual(parsed["agent_id"], "a1")

    # ── append-only invariant ──────────────────────────────────────────────
    def test_accept_is_append_only(self):
        self.m.birth("a1")
        e = self.m.learn("decision", "A durable decision worth keeping.", agent_id="a1")
        learned = self.m.agent_dir("a1") / "learned.jsonl"
        n_before = len(learned.read_text().splitlines())
        self.assertEqual(n_before, 1)
        self.m.accept(e["id"], reviewer="r", note="n", agent_id="a1")
        n_after = len(learned.read_text().splitlines())
        self.assertEqual(n_after, 2)  # supersede record APPENDED, not rewritten
        # original draft line still present verbatim
        first_line = json.loads(learned.read_text().splitlines()[0])
        self.assertEqual(first_line["status"], "draft")

    # ── status counts ──────────────────────────────────────────────────────
    def test_status_counts(self):
        self.m.birth("a1")
        e1 = self.m.learn("decision", "One decision here.", agent_id="a1")
        e2 = self.m.learn("limit", "A known limit here.", agent_id="a1")
        self.m.learn("correction", "A pending draft here.", agent_id="a1")
        self.m.accept(e1["id"], reviewer="r", note="n", agent_id="a1")
        self.m.reject(e2["id"], reviewer="r", note="n", agent_id="a1")
        self.m.checkpoint("x", "y", agent_id="a1")
        st = self.m.status("a1")
        self.assertEqual(st["accepted"], 1)
        self.assertEqual(st["rejected"], 1)
        self.assertEqual(st["drafts"], 1)
        self.assertEqual(st["checkpoints"], 1)
        self.assertTrue(st["store"].startswith(self.tmp.name))

    # ── CLI smoke ──────────────────────────────────────────────────────────
    def test_cli_status_runs(self):
        rc = self.m.main(["--agent", "a1", "status"])
        self.assertEqual(rc, 0)

    def test_cli_learn_bad_kind_rejected(self):
        # argparse rejects an invalid --kind choice with SystemExit(2)
        with self.assertRaises(SystemExit):
            self.m.main(["--agent", "a1", "learn", "--kind", "nope", "--text", "x"])


if __name__ == "__main__":
    unittest.main()
