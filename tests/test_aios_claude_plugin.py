"""Tests for the Claude Code plugin distribution surface (plugin/aios/).

Structural, hermetic, no network: parses the marketplace + plugin manifests and
asserts they are internally consistent and that every script path the hook and
MCP server reference actually exists in the bundle. This guards against the
plugin silently breaking when a script is renamed or the manifests drift.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_DIR = ROOT / "plugin" / "aios"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


class TestMarketplaceManifest(unittest.TestCase):
    def test_marketplace_parses_and_names_aios_claude(self):
        m = _load(MARKETPLACE)
        self.assertEqual(m["name"], "aios-claude")
        self.assertIsInstance(m["plugins"], list)
        self.assertEqual(len(m["plugins"]), 1)

    def test_marketplace_lists_aios_plugin_with_existing_source(self):
        m = _load(MARKETPLACE)
        entry = m["plugins"][0]
        self.assertEqual(entry["name"], "aios")
        # source is a repo-relative path that must resolve to the plugin dir.
        src = (ROOT / entry["source"]).resolve()
        self.assertEqual(src, PLUGIN_DIR.resolve())
        self.assertTrue((src / ".claude-plugin" / "plugin.json").is_file())


class TestPluginManifest(unittest.TestCase):
    def test_plugin_json_parses_and_is_named_aios(self):
        p = _load(PLUGIN_DIR / ".claude-plugin" / "plugin.json")
        self.assertEqual(p["name"], "aios")
        self.assertIn("version", p)
        self.assertIn("description", p)
        # author cjw0076 per the distribution spec.
        self.assertEqual(p["author"]["name"], "cjw0076")

    def test_marketplace_and_plugin_versions_agree(self):
        p = _load(PLUGIN_DIR / ".claude-plugin" / "plugin.json")
        self.assertRegex(p["version"], r"^\d+\.\d+\.\d+")


class TestBundledScriptPaths(unittest.TestCase):
    """Every ${CLAUDE_PLUGIN_ROOT}/scripts/<x> reference must resolve to a real
    file through the bundle (the `scripts` symlink/dir)."""

    def _resolve_plugin_path(self, ref: str) -> Path:
        rel = ref.replace("${CLAUDE_PLUGIN_ROOT}/", "")
        return PLUGIN_DIR / rel

    def test_scripts_bundle_present(self):
        self.assertTrue((PLUGIN_DIR / "scripts").exists())
        self.assertTrue((PLUGIN_DIR / "scripts" / "aios_mcp_server.py").is_file())
        self.assertTrue((PLUGIN_DIR / "scripts" / "aios_agent_self.py").is_file())

    def test_hook_command_references_existing_script(self):
        hooks = _load(PLUGIN_DIR / "hooks" / "hooks.json")
        session_start = hooks["hooks"]["SessionStart"]
        cmds = [h["command"] for group in session_start for h in group["hooks"]]
        self.assertTrue(cmds, "no SessionStart hook command found")
        joined = " ".join(cmds)
        self.assertIn("carry --to claude --hook", joined)
        for ref in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/\S+?\.py", joined):
            self.assertTrue(self._resolve_plugin_path(ref).is_file(),
                            f"hook references missing script: {ref}")

    def test_mcp_server_command_references_existing_script(self):
        mcp = _load(PLUGIN_DIR / ".mcp.json")
        server = mcp["mcpServers"]["aios"]
        self.assertEqual(server["command"], "python3")
        refs = [a for a in server["args"] if a.endswith(".py")]
        self.assertTrue(refs, "no .py arg in mcp server args")
        for ref in refs:
            self.assertTrue(self._resolve_plugin_path(ref).is_file(),
                            f"mcp server references missing script: {ref}")
        # --root must be pinned to the plugin root so the server finds its bundle.
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", server["args"])


if __name__ == "__main__":
    unittest.main()
