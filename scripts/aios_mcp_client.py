#!/usr/bin/env python3
"""AIOS MCP client — minimal stdio JSON-RPC 2.0 client (masterplan §4 M5/D4-6).

Survey grounding (docs/AIOS_OSS_ABSORPTION_SURVEY_2026-07-10.md §(g)1): "one MCP
client integration opens the official registry (~9,652 servers)". This is that one
integration — deliberately small and stdlib-only (subprocess + json) so it has no
hard dependency on the `mcp` pip package. If that package happens to be installed,
this module still does not route through it: the stdlib subprocess/JSON-RPC path
below is the one and only implementation, always exercised, always tested. The
try-import exists purely so callers can query `HAS_MCP_SDK` if they want to branch
to something SDK-based themselves; aios_mcp_client never does.

Transport: MCP stdio — one JSON-RPC 2.0 message per line on the child's
stdin/stdout (matches scripts/aios_mcp_server.py's own reader). Dogfooding: the
first configured server (.aios/mcp_servers.json → "aios-self") is AIOS's own MCP
server — this client's live test target is AIOS reaching itself through its own
protocol.

Design contract: never hang (every stdout read honors a wall-clock deadline via
select()), never fabricate a result (every failure path returns an honest
{"status": "error"|"timeout", "reason": ...} dict instead of raising, except for
programmer-error argument misuse).

Schema: aios.mcp_client.v1
"""
from __future__ import annotations

import json
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:  # optional — see module docstring; never used by this client, only reported
    import mcp as _mcp_sdk  # noqa: F401
    HAS_MCP_SDK = True
except ImportError:
    HAS_MCP_SDK = False

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / ".aios" / "mcp_servers.json"
PROTOCOL_VERSION = "2025-06-18"
CLIENT_NAME = "aios-mcp-client"
CLIENT_VERSION = "0.1.0"
SCHEMA_VERSION = "aios.mcp_client.v1"


class McpClient:
    """One stdio-transport MCP client per connected server subprocess.

    Every public method returns a dict with a "status" key ("ok" on success,
    "error"/"timeout" otherwise) — the same convention aios_tools.py's other
    handlers use, so an McpClient can sit directly behind a turn-loop tool
    without an adapter layer.
    """

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self._proc: subprocess.Popen | None = None
        self._next_msg_id = 0
        self.server_info: dict[str, Any] = {}

    # -- lifecycle --------------------------------------------------------

    def connect(self, command: list[str], cwd: Path | str | None = None) -> dict:
        """Spawn the server subprocess and run the initialize/initialized
        handshake. Returns {"status": "ok", "server": <InitializeResult>} or an
        honest {"status": "error", "reason": ...}."""
        if not command or not isinstance(command, list):
            return {"status": "error", "reason": "command must be a non-empty list"}
        try:
            self._proc = subprocess.Popen(
                [str(c) for c in command],
                cwd=str(cwd) if cwd else None,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            return {"status": "error", "reason": f"spawn failed: {exc}"}

        init = self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
        })
        if init.get("status") != "ok":
            self.close()
            return init
        self.server_info = init.get("result") or {}
        self._notify("notifications/initialized", {})
        return {"status": "ok", "server": self.server_info}

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        except Exception:  # noqa: BLE001 — close() must never raise
            pass

    def __enter__(self) -> "McpClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- protocol operations ------------------------------------------------

    def list_tools(self) -> dict:
        """-> {"status": "ok", "tools": [{"name","description","inputSchema"}, ...]}
        or an honest error dict."""
        if self._proc is None:
            return {"status": "error", "reason": "not connected"}
        r = self._request("tools/list", {})
        if r.get("status") != "ok":
            return r
        raw_tools = (r.get("result") or {}).get("tools") or []
        tools = [
            {
                "name": t.get("name"),
                "description": t.get("description", ""),
                "inputSchema": t.get("inputSchema", {}),
            }
            for t in raw_tools
            if isinstance(t, dict) and t.get("name")
        ]
        return {"status": "ok", "tools": tools}

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """Invoke one server tool. -> {"status": "ok", "text": "<joined text
        parts>", "isError": bool, "raw": <full result>} or an honest error dict.
        Never raises for protocol/timeout failures."""
        if self._proc is None:
            return {"status": "error", "reason": "not connected"}
        name = str(name or "").strip()
        if not name:
            return {"status": "error", "reason": "tool name required"}
        r = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        if r.get("status") != "ok":
            return r
        result = r.get("result") or {}
        content = result.get("content") or []
        text = "\n".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
        return {"status": "ok", "text": text, "isError": bool(result.get("isError")), "raw": result}

    # -- JSON-RPC plumbing ----------------------------------------------------

    def _next_id(self) -> int:
        self._next_msg_id += 1
        return self._next_msg_id

    def _write(self, msg: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise OSError("no process")
        self._proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _notify(self, method: str, params: dict) -> None:
        try:
            self._write({"jsonrpc": "2.0", "method": method, "params": params})
        except (OSError, ValueError):
            pass  # notifications are best-effort — no response is ever expected

    def _request(self, method: str, params: dict) -> dict:
        mid = self._next_id()
        try:
            self._write({"jsonrpc": "2.0", "id": mid, "method": method, "params": params})
        except (OSError, ValueError) as exc:
            return {"status": "error", "reason": f"write failed: {exc}"}
        return self._read_response(mid)

    def _read_response(self, expected_id: int) -> dict:
        """Read lines from the server's stdout until a response with
        `expected_id` arrives, honoring a wall-clock deadline (select() on the
        pipe) so a hung or silent server can never block the caller forever."""
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"status": "timeout", "reason": f"no response within {self.timeout}s"}
            if self._proc is None or self._proc.stdout is None:
                return {"status": "error", "reason": "no process"}
            try:
                ready, _, _ = select.select([self._proc.stdout], [], [], min(remaining, 1.0))
            except (OSError, ValueError) as exc:
                return {"status": "error", "reason": f"select failed: {exc}"}
            if not ready:
                if self._proc.poll() is not None:
                    return self._exited_error()
                continue
            line = self._proc.stdout.readline()
            if line == "":
                return self._exited_error() if self._proc.poll() is not None else \
                    {"status": "error", "reason": "server closed stdout"}
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                return {"status": "error", "reason": f"malformed response: {line[:160]}"}
            if not isinstance(msg, dict) or msg.get("id") != expected_id:
                continue  # a notification or an out-of-order reply — keep waiting
            if "error" in msg:
                err = msg["error"] or {}
                reason = err.get("message", err) if isinstance(err, dict) else err
                return {"status": "error", "reason": str(reason)[:200]}
            return {"status": "ok", "result": msg.get("result")}

    def _exited_error(self) -> dict:
        stderr = ""
        try:
            if self._proc is not None and self._proc.stderr:
                stderr = (self._proc.stderr.read() or "")[:200]
        except Exception:  # noqa: BLE001 — best-effort diagnostics only
            pass
        code = self._proc.returncode if self._proc is not None else None
        reason = f"server process exited (code {code})"
        if stderr.strip():
            reason += f": {stderr.strip()}"
        return {"status": "error", "reason": reason}


# -- config-driven connect helper (.aios/mcp_servers.json) ----------------------

def load_server_config(name: str, config_path: Path | None = None) -> dict:
    """Read one server entry from .aios/mcp_servers.json. -> {"status": "ok",
    "command": [...], "cwd": <str|None>} or an honest error dict."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if not path.is_file():
        return {"status": "error", "reason": f"config not found: {path}"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "error", "reason": f"config unreadable: {exc}"}
    if not isinstance(data, dict):
        return {"status": "error", "reason": "config must be a JSON object"}
    entry = data.get(name)
    if not isinstance(entry, dict):
        return {"status": "error", "reason": f"no server named {name!r} in {path}"}
    command = entry.get("command")
    if not isinstance(command, list) or not command:
        return {"status": "error", "reason": f"server {name!r} has no command list"}
    return {"status": "ok", "command": [str(c) for c in command], "cwd": entry.get("cwd")}


def connect_named(
    name: str,
    config_path: Path | None = None,
    timeout: float = 15.0,
) -> tuple["McpClient | None", dict]:
    """Look up `name` in .aios/mcp_servers.json, spawn it, and hand back a
    connected client + its handshake result. Relative commands in the config
    (e.g. "scripts/aios_mcp_server.py") are resolved against the repo ROOT
    unless the entry names its own "cwd". Returns (None, <error dict>) on any
    failure — never raises, never hangs."""
    cfg = load_server_config(name, config_path)
    if cfg.get("status") != "ok":
        return None, cfg
    client = McpClient(timeout=timeout)
    cwd = Path(cfg["cwd"]) if cfg.get("cwd") else ROOT
    handshake = client.connect(cfg["command"], cwd=cwd)
    if handshake.get("status") != "ok":
        client.close()
        return None, handshake
    return client, handshake


# -- CLI (manual live probing) --------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--server", default="aios-self", help="server name in .aios/mcp_servers.json")
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--call", metavar="TOOL", help="call this tool instead of listing")
    p.add_argument("--args", default="{}", help="JSON arguments object for --call")
    p.add_argument("--timeout", type=float, default=15.0)
    args = p.parse_args(argv)

    client, handshake = connect_named(args.server, args.config, timeout=args.timeout)
    if client is None:
        print(json.dumps(handshake, ensure_ascii=False, indent=2))
        return 1
    try:
        if args.call:
            try:
                arguments = json.loads(args.args)
            except ValueError:
                print(json.dumps({"status": "error", "reason": "bad --args JSON"}, ensure_ascii=False))
                return 2
            result = client.call_tool(args.call, arguments)
        else:
            result = client.list_tools()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") == "ok" else 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
