"""Composite AGENT SELF over MCP — any MCP client can birth/learn/checkpoint/carry
a persistent self through the stdio JSON-RPC server.

Hermetic: AIOS_HOME points at a tmp dir so the real ~/.aios is never touched. No
network. Exercises the JSON-RPC round-trip (tools/list + tools/call) and the
draft-first + local-only DNA boundary (no accept/reject tool over MCP).
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, SCRIPTS.as_posix())
import aios_mcp_server as M  # noqa: E402
import aios_agent_self as SELF  # noqa: E402

NEW_TOOLS = {
    "aios_self_status", "aios_self_birth", "aios_self_learn",
    "aios_self_checkpoint", "aios_self_carry",
}


def _rpc(msg):
    """Drive one JSON-RPC message through the server exactly as stdin would."""
    return M.handle(ROOT, json.loads(json.dumps(msg)))


def _call(name, arguments):
    resp = _rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": name, "arguments": arguments}})
    result = resp["result"]
    text = result["content"][0]["text"]
    return result.get("isError", False), text


class McpSelfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._prev_home = os.environ.get("AIOS_HOME")
        self._prev_agent = os.environ.get("AIOS_AGENT_ID")
        os.environ["AIOS_HOME"] = self.tmp.name
        os.environ.pop("AIOS_AGENT_ID", None)

    def tearDown(self):
        if self._prev_home is None:
            os.environ.pop("AIOS_HOME", None)
        else:
            os.environ["AIOS_HOME"] = self._prev_home
        if self._prev_agent is not None:
            os.environ["AIOS_AGENT_ID"] = self._prev_agent
        self.tmp.cleanup()

    # ── discovery ────────────────────────────────────────────────────────────
    def test_tools_list_contains_the_5_new_tools(self):
        resp = _rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertTrue(NEW_TOOLS.issubset(names), NEW_TOOLS - names)

    def test_no_accept_or_reject_tool_exists(self):
        names = {t["name"] for t in M.tool_specs()}
        self.assertNotIn("aios_self_accept", names)
        self.assertNotIn("aios_self_reject", names)
        self.assertNotIn("aios_self_accept", M.HANDLERS)
        self.assertNotIn("aios_self_reject", M.HANDLERS)

    def test_learn_tool_description_documents_the_cli_accept_path(self):
        spec = next(t for t in M.tool_specs() if t["name"] == "aios_self_learn")
        self.assertIn("aios self accept", spec["description"])
        self.assertIn("draft", spec["description"].lower())

    # ── status / birth ───────────────────────────────────────────────────────
    def test_status_returns_counts_and_store_path(self):
        err, text = _call("aios_self_status", {"agent": "a1"})
        self.assertFalse(err)
        d = json.loads(text)
        self.assertEqual(d["agent_id"], "a1")
        self.assertIn(self.tmp.name, d["store"])

    def test_birth_returns_compiled_self_text(self):
        err, text = _call("aios_self_birth", {"agent": "a1"})
        self.assertFalse(err)
        self.assertIn("Identity — a1", text)
        self.assertIn("AIOS DNA:", text)

    # ── learn = DRAFT only, hidden from birth until accepted via the organ ────
    def test_learn_creates_draft_hidden_from_birth_until_accepted(self):
        err, text = _call("aios_self_learn", {
            "agent": "a1", "kind": "decision",
            "text": "chose stdlib-only MCP transport for portability"})
        self.assertFalse(err)
        draft = json.loads(text)
        self.assertEqual(draft["status"], "draft")
        draft_id = draft["id"]
        self.assertTrue(draft_id)

        # a draft is a proposal — it MUST NOT appear in the compiled self
        _, birth_before = _call("aios_self_birth", {"agent": "a1"})
        self.assertNotIn("stdlib-only MCP transport", birth_before)

        # acceptance happens only via the organ's own CLI-side review (not MCP)
        SELF.accept(draft_id, reviewer="tester", note="verified in test", agent_id="a1")
        _, birth_after = _call("aios_self_birth", {"agent": "a1"})
        self.assertIn("stdlib-only MCP transport", birth_after)

    def test_learn_rejects_bad_kind(self):
        err, text = _call("aios_self_learn", {"agent": "a1", "kind": "bogus", "text": "x"})
        self.assertTrue(err)

    # ── checkpoint / carry ───────────────────────────────────────────────────
    def test_checkpoint_records_death_and_birth_resumes(self):
        err, text = _call("aios_self_checkpoint", {
            "agent": "a1", "in_flight": "wiring MCP self tools", "next": "run the suite"})
        self.assertFalse(err)
        self.assertEqual(json.loads(text)["status"], "checkpointed")
        _, birth = _call("aios_self_birth", {"agent": "a1"})
        self.assertIn("wiring MCP self tools", birth)
        self.assertIn("run the suite", birth)

    def test_carry_returns_a_claude_block(self):
        err, text = _call("aios_self_carry", {"agent": "a1", "to": "claude"})
        self.assertFalse(err)
        self.assertIn("```markdown", text)
        self.assertIn("CLAUDE.md", text)
        self.assertIn("Identity — a1", text)

    def test_carry_json_target_returns_self_md(self):
        err, text = _call("aios_self_carry", {"agent": "a1", "to": "json"})
        self.assertFalse(err)
        d = json.loads(text)
        self.assertIn("Identity — a1", d["self_md"])

    # ── real ~/.aios untouched ───────────────────────────────────────────────
    def test_real_home_untouched(self):
        _call("aios_self_learn", {"agent": "a1", "kind": "limit", "text": "y"})
        _call("aios_self_birth", {"agent": "a1"})
        real = Path.home() / ".aios" / "self" / "a1"
        self.assertFalse(real.exists())


if __name__ == "__main__":
    unittest.main()
