"""Minimal stdio MCP client (masterplan §4 M5/D4-6): handshake, tools/list,
tools/call, timeout path, malformed-response error dict -- against a tiny fake
server spawned as a subprocess (deterministic, no network) -- plus a live
dogfood connection to AIOS's own scripts/aios_mcp_server.py, and the
aios_tools.register_mcp_tools bridge.
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_mcp_client as C
import aios_tools as T
import aios_turn_loop as L

# A deterministic fake MCP server: initialize / tools.list / tools.call over
# newline-delimited JSON-RPC 2.0 on stdio -- same transport aios_mcp_server.py
# and aios_mcp_client.py speak. "hang" never responds (timeout path); "boom"
# returns a tool-level error (isError=True); any other unknown tool name
# returns a JSON-RPC protocol-level error.
FAKE_SERVER_SRC = r"""
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    method = msg.get("method")
    mid = msg.get("id")
    if method == "initialize":
        resp = {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fake-test-server", "version": "0.0.1"},
        }}
    elif method in ("notifications/initialized", "initialized"):
        continue
    elif method == "tools/list":
        resp = {"jsonrpc": "2.0", "id": mid, "result": {"tools": [
            {"name": "echo", "description": "echoes text back",
             "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}},
            {"name": "delete_thing", "description": "deletes something (write pattern)",
             "inputSchema": {"type": "object", "properties": {}}},
        ]}}
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "hang":
            continue
        if name == "echo":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [
                    {"type": "text", "text": str(args.get("text", ""))},
                    {"type": "text", "text": "part-two"},
                ],
                "isError": False,
            }}
        elif name == "boom":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": "it broke"}], "isError": True,
            }}
        else:
            resp = {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32601, "message": "unknown tool: " + str(name)}}
    elif method == "ping":
        resp = {"jsonrpc": "2.0", "id": mid, "result": {}}
    else:
        continue
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
"""

# Responds to every input line with a non-JSON garbage line -- exercises the
# malformed-response error path from inside connect()'s initialize request.
MALFORMED_SERVER_SRC = r"""
import sys
for line in sys.stdin:
    if not line.strip():
        continue
    sys.stdout.write("not-json-at-all-oops\n")
    sys.stdout.flush()
"""


def _spawn_fake_client(timeout: float = 8.0):
    client = C.McpClient(timeout=timeout)
    handshake = client.connect([sys.executable, "-c", FAKE_SERVER_SRC])
    return client, handshake


class HandshakeTests(unittest.TestCase):
    def test_connect_performs_initialize_handshake(self) -> None:
        client, handshake = _spawn_fake_client()
        try:
            self.assertEqual(handshake["status"], "ok")
            self.assertEqual(handshake["server"]["serverInfo"]["name"], "fake-test-server")
        finally:
            client.close()

    def test_connect_rejects_empty_command(self) -> None:
        client = C.McpClient()
        self.assertEqual(client.connect([])["status"], "error")

    def test_connect_reports_spawn_failure_honestly(self) -> None:
        client = C.McpClient(timeout=3.0)
        result = client.connect(["/no/such/executable/at/all/xyz123"])
        self.assertEqual(result["status"], "error")
        client.close()


class ListToolsTests(unittest.TestCase):
    def test_list_tools_returns_declared_tools(self) -> None:
        client, handshake = _spawn_fake_client()
        try:
            self.assertEqual(handshake["status"], "ok")
            result = client.list_tools()
            self.assertEqual(result["status"], "ok")
            self.assertEqual({t["name"] for t in result["tools"]}, {"echo", "delete_thing"})
        finally:
            client.close()

    def test_list_tools_before_connect_is_honest_error(self) -> None:
        self.assertEqual(C.McpClient().list_tools()["status"], "error")


class CallToolTests(unittest.TestCase):
    def test_call_tool_joins_text_parts(self) -> None:
        client, handshake = _spawn_fake_client()
        try:
            self.assertEqual(handshake["status"], "ok")
            result = client.call_tool("echo", {"text": "hello"})
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["text"], "hello\npart-two")
            self.assertFalse(result["isError"])
        finally:
            client.close()

    def test_call_tool_surfaces_tool_level_error(self) -> None:
        client, handshake = _spawn_fake_client()
        try:
            self.assertEqual(handshake["status"], "ok")
            result = client.call_tool("boom", {})
            self.assertEqual(result["status"], "ok")      # protocol succeeded
            self.assertTrue(result["isError"])              # the TOOL itself failed
            self.assertEqual(result["text"], "it broke")
        finally:
            client.close()

    def test_call_tool_surfaces_protocol_error(self) -> None:
        client, handshake = _spawn_fake_client()
        try:
            self.assertEqual(handshake["status"], "ok")
            self.assertEqual(client.call_tool("no_such_tool", {})["status"], "error")
        finally:
            client.close()

    def test_call_tool_requires_name(self) -> None:
        client, handshake = _spawn_fake_client()
        try:
            self.assertEqual(handshake["status"], "ok")
            self.assertEqual(client.call_tool("")["status"], "error")
        finally:
            client.close()

    def test_call_tool_before_connect_is_honest_error(self) -> None:
        self.assertEqual(C.McpClient().call_tool("x")["status"], "error")


class TimeoutTests(unittest.TestCase):
    def test_call_tool_times_out_instead_of_hanging(self) -> None:
        client, handshake = _spawn_fake_client()
        try:
            self.assertEqual(handshake["status"], "ok")
            client.timeout = 0.8
            start = time.monotonic()
            result = client.call_tool("hang", {})
            elapsed = time.monotonic() - start
            self.assertEqual(result["status"], "timeout")
            self.assertLess(elapsed, 5.0)   # bounded -- proves it never hangs
        finally:
            client.close()


class MalformedResponseTests(unittest.TestCase):
    def test_malformed_response_is_honest_error_not_a_crash(self) -> None:
        client = C.McpClient(timeout=5.0)
        result = client.connect([sys.executable, "-c", MALFORMED_SERVER_SRC])
        self.assertEqual(result["status"], "error")
        self.assertIn("malformed response", result["reason"])
        client.close()


class ConfigTests(unittest.TestCase):
    def test_load_server_config_reads_aios_self_entry(self) -> None:
        cfg = C.load_server_config("aios-self")
        self.assertEqual(cfg["status"], "ok")
        self.assertEqual(cfg["command"], ["python3", "scripts/aios_mcp_server.py"])

    def test_load_server_config_missing_name_is_honest(self) -> None:
        self.assertEqual(C.load_server_config("no-such-server")["status"], "error")

    def test_load_server_config_missing_file_is_honest(self) -> None:
        cfg = C.load_server_config("anything", Path("/nonexistent/path/mcp_servers.json"))
        self.assertEqual(cfg["status"], "error")


class ConnectNamedLiveTests(unittest.TestCase):
    """Dogfood target: AIOS's own MCP server, reached through its own client
    via .aios/mcp_servers.json's "aios-self" entry (masterplan §4 M5/D4-6)."""

    def test_connect_named_reaches_the_real_aios_mcp_server(self) -> None:
        client, handshake = C.connect_named("aios-self", timeout=20.0)
        self.assertIsNotNone(client, handshake)
        try:
            self.assertEqual(handshake["status"], "ok")
            listing = client.list_tools()
            self.assertEqual(listing["status"], "ok")
            names = {t["name"] for t in listing["tools"]}
            self.assertIn("aios_route", names)
            self.assertIn("aios_self_status", names)
            self.assertGreaterEqual(len(listing["tools"]), 10)
            # a real read-only round trip through the actual server
            status_result = client.call_tool("aios_self_status", {})
            self.assertEqual(status_result["status"], "ok")
        finally:
            client.close()


class RegisterMcpToolsBridgeTests(unittest.TestCase):
    """aios_tools.register_mcp_tools -- additive bridge into a Registry +
    TOOL_SPEC-style listing, with conservative write-pattern classification."""

    def test_bridges_tools_additively_with_write_classification(self) -> None:
        client, handshake = _spawn_fake_client()
        self.assertEqual(handshake["status"], "ok")
        try:
            registry = L.Registry()
            isolated_spec: dict = {}
            result = T.register_mcp_tools(registry, client, "mcp.fake.", tool_spec=isolated_spec)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(set(result["registered"]), {"mcp.fake.echo", "mcp.fake.delete_thing"})
            self.assertIn("mcp.fake.echo", registry.handlers)
            self.assertIn("mcp.fake.delete_thing", registry.handlers)
            self.assertEqual(isolated_spec["mcp.fake.echo"][0], "advisory")
            self.assertEqual(isolated_spec["mcp.fake.delete_thing"][0], "write")
            self.assertEqual(isolated_spec["mcp.fake.delete_thing"][1], "commit_to_child_repo")
        finally:
            client.close()

    def test_dispatch_through_registry_actually_calls_the_server(self) -> None:
        client, handshake = _spawn_fake_client()
        self.assertEqual(handshake["status"], "ok")
        try:
            registry = L.Registry()
            T.register_mcp_tools(registry, client, "mcp.fake.", tool_spec={})
            status, result = registry.dispatch(L.ToolCall("mcp.fake.echo", {"text": "via-registry"}))
            self.assertEqual(status, "ok")
            self.assertEqual(result["status"], "ok")
            self.assertIn("via-registry", result["text"])
        finally:
            client.close()

    def test_list_tools_failure_degrades_honestly(self) -> None:
        class _DeadClient:
            def list_tools(self):
                return {"status": "error", "reason": "not connected"}

        result = T.register_mcp_tools(L.Registry(), _DeadClient(), "mcp.dead.", tool_spec={})
        self.assertNotEqual(result["status"], "ok")
        self.assertEqual(result["registered"], [])

    def test_gate_for_reads_bridged_tools_from_the_real_global_spec(self) -> None:
        """One integration test against the REAL module-global TOOL_SPEC, proving
        gate_for()/list_tools() see bridged tools automatically -- snapshot +
        restore so this can never pollute other tests in the same session."""
        snapshot = dict(T.TOOL_SPEC)
        client, handshake = _spawn_fake_client()
        self.assertEqual(handshake["status"], "ok")
        try:
            registry = L.Registry()
            T.register_mcp_tools(registry, client, "mcp.fake2.")   # default: real global TOOL_SPEC
            self.assertIn("mcp.fake2.echo", T.TOOL_SPEC)
            self.assertEqual(T.gate_for("codex@myworld")("mcp.fake2.echo", {}), L.ALLOW)
            # write-pattern tool: an unauthorized agent is asked, never silently allowed
            self.assertEqual(T.gate_for("test_outsider")("mcp.fake2.delete_thing", {}), L.ASK)
            self.assertIn("mcp.fake2.echo", {t["name"] for t in T.list_tools()})
        finally:
            client.close()
            T.TOOL_SPEC.clear()
            T.TOOL_SPEC.update(snapshot)


if __name__ == "__main__":
    unittest.main()
