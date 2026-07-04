"""Tests for aios_acp_drive.py — the INVERSION OF CONTROL organ.

Hermetic: AIOS_HOME points at a tmp dir (real ~/.aios untouched). NO real
engines, NO network — a tiny FAKE ACP server (tests/fake_acp_server.py, spawned
via sys.executable) performs the real newline-delimited JSON-RPC handshake,
streams chunks + a tool_call, and raises two permission requests (one benign,
one privacy-gated) so we can assert the OS-moment adjudication end-to-end.
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
FAKE_SERVER = Path(__file__).resolve().parent / "fake_acp_server.py"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class AdjudicateUnitTest(unittest.TestCase):
    def setUp(self):
        self.m = _load("aios_acp_drive_under_test", "aios_acp_drive.py")

    def test_allows_benign(self):
        allow, _ = self.m._adjudicate({"title": "Write notes.txt",
                                       "locations": [{"path": "notes.txt"}],
                                       "rawInput": {"path": "notes.txt"}})
        self.assertTrue(allow)

    def test_denies_gated_segment(self):
        for path in ("dain/notes.md", "x/minyoung/y.txt", "_from_desktop/a"):
            allow, reason = self.m._adjudicate({"title": "Write",
                                                "locations": [{"path": path}]})
            self.assertFalse(allow, path)
            self.assertIn("segment", reason)

    def test_denies_gated_substring(self):
        allow, reason = self.m._adjudicate({"title": "read .env",
                                            "rawInput": {"path": "./.env"}})
        self.assertFalse(allow)
        self.assertIn("substring", reason)

    def test_denies_destructive(self):
        allow, reason = self.m._adjudicate({"title": "shell",
                                            "rawInput": {"command": "rm -rf /etc"}})
        self.assertFalse(allow)
        self.assertIn("rm -rf", reason)
        allow2, reason2 = self.m._adjudicate({"title": "push",
                                              "rawInput": {"command": "git push --force origin main"}})
        self.assertFalse(allow2)
        self.assertIn("force", reason2)


class DriveIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.m = _load("aios_acp_drive_under_test", "aios_acp_drive.py")
        self.selfmod = _load("aios_agent_self_under_test2", "aios_agent_self.py")
        self.tmp = tempfile.TemporaryDirectory()
        self._prev_home = os.environ.get("AIOS_HOME")
        self._prev_agent = os.environ.get("AIOS_AGENT_ID")
        self._prev_dump = os.environ.get("FAKE_ACP_PROMPT_DUMP")
        self._prev_hang = os.environ.get("FAKE_ACP_HANG")
        os.environ["AIOS_HOME"] = self.tmp.name
        os.environ.pop("AIOS_AGENT_ID", None)
        os.environ.pop("FAKE_ACP_HANG", None)
        self.dump = str(Path(self.tmp.name) / "prompt_dump.txt")
        os.environ["FAKE_ACP_PROMPT_DUMP"] = self.dump
        self.workdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        for key, prev in (("AIOS_HOME", self._prev_home),
                          ("AIOS_AGENT_ID", self._prev_agent),
                          ("FAKE_ACP_PROMPT_DUMP", self._prev_dump),
                          ("FAKE_ACP_HANG", self._prev_hang)):
            if prev is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev
        self.tmp.cleanup()
        self.workdir.cleanup()

    def _fake_cmd(self):
        return [sys.executable, str(FAKE_SERVER)]

    _SELF_MARK = "acp-drive-self-marker-xyz"

    def _seed_self(self, agent_id="a1"):
        self.selfmod.learn("decision", self._SELF_MARK, agent_id=agent_id)
        entries = self.selfmod._read_jsonl(self.selfmod.agent_dir(agent_id) / "learned.jsonl")
        eid = entries[-1]["id"]
        self.selfmod.accept(eid, reviewer="tester", note="ok", agent_id=agent_id)

    def test_handshake_chunks_and_permissions(self):
        self._seed_self("a1")
        receipt = self.m.drive(goal="do the thing", engine="x", cwd=self.workdir.name,
                               inject_self=True, timeout=60,
                               engine_cmd=self._fake_cmd(), agent_id="a1")
        # Handshake completed with a real stop reason.
        self.assertEqual(receipt["stop_reason"], "end_turn")
        self.assertIsNone(receipt["error"])
        self.assertEqual(receipt["session_id"], "sess_fake_001")
        # Two permission decisions, correctly adjudicated.
        perms = receipt["permissions"]
        self.assertEqual(len(perms), 2)
        by_id = {p["tool_call_id"]: p for p in perms}
        self.assertEqual(by_id["tc_1"]["decision"], "allow")
        self.assertEqual(by_id["tc_1"]["outcome"], "selected")
        self.assertEqual(by_id["tc_2"]["decision"], "deny")
        self.assertIn("dain", by_id["tc_2"]["reason"])
        # Events (chunks + tool_call + permissions) were recorded.
        self.assertGreaterEqual(receipt["events"], 4)

    def test_receipt_written_under_tmp_home(self):
        self._seed_self("a1")
        receipt = self.m.drive(goal="g", engine="x", cwd=self.workdir.name,
                               engine_cmd=self._fake_cmd(), agent_id="a1", timeout=60)
        rp = Path(receipt["receipt_path"])
        self.assertTrue(rp.exists())
        self.assertTrue(str(rp).startswith(self.tmp.name))
        self.assertIn("drive", rp.parts)
        loaded = json.loads(rp.read_text())
        self.assertEqual(loaded["stop_reason"], "end_turn")
        self.assertEqual(len(loaded["permissions"]), 2)

    def test_self_injected_when_store_exists(self):
        self._seed_self("a1")
        receipt = self.m.drive(goal="g", engine="x", cwd=self.workdir.name,
                               inject_self=True, engine_cmd=self._fake_cmd(),
                               agent_id="a1", timeout=60)
        self.assertTrue(receipt["self_injected"])
        prompt_text = Path(self.dump).read_text()
        self.assertIn(self._SELF_MARK, prompt_text)
        self.assertIn("g", prompt_text)

    def test_no_self_flag_omits_self(self):
        self._seed_self("a1")
        receipt = self.m.drive(goal="just-the-goal", engine="x", cwd=self.workdir.name,
                               inject_self=False, engine_cmd=self._fake_cmd(),
                               agent_id="a1", timeout=60)
        self.assertFalse(receipt["self_injected"])
        prompt_text = Path(self.dump).read_text()
        self.assertNotIn(self._SELF_MARK, prompt_text)
        self.assertIn("just-the-goal", prompt_text)

    def test_no_self_injection_when_store_absent(self):
        # No _seed_self -> no store for agent 'ghost'.
        receipt = self.m.drive(goal="g", engine="x", cwd=self.workdir.name,
                               inject_self=True, engine_cmd=self._fake_cmd(),
                               agent_id="ghost", timeout=60)
        self.assertFalse(receipt["self_injected"])

    def test_timeout_kills_child_cleanly(self):
        os.environ["FAKE_ACP_HANG"] = "1"
        receipt = self.m.drive(goal="g", engine="x", cwd=self.workdir.name,
                               engine_cmd=self._fake_cmd(), agent_id="a1", timeout=2)
        self.assertEqual(receipt["stop_reason"], "timeout")
        self.assertIsNotNone(receipt["error"])
        # Receipt still written despite the kill.
        self.assertTrue(Path(receipt["receipt_path"]).exists())


if __name__ == "__main__":
    unittest.main()
