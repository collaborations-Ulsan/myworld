#!/usr/bin/env python3
"""A tiny FAKE ACP server (engine) for hermetic aios_acp_drive tests.

Speaks newline-delimited JSON-RPC 2.0 over stdin/stdout exactly like a real ACP
agent (gemini --acp / claude-code-acp) but performs no work and touches no
network. It:
  1. answers `initialize` (echoes protocolVersion),
  2. answers `session/new` with a fixed sessionId,
  3. on `session/prompt`: dumps the received prompt text (if FAKE_ACP_PROMPT_DUMP
     is set), streams TWO agent_message_chunk updates + one tool_call update,
     then raises TWO session/request_permission requests —
       (a) a benign write to notes.txt          -> driver should ALLOW,
       (b) a write to dain/notes.md (gated seg)  -> driver should DENY,
     and finally answers the prompt with stopReason "end_turn".

No AIOS imports — this is a pure protocol peer.
"""
from __future__ import annotations

import json
import os
import sys

SESSION_ID = "sess_fake_001"


def _read():
    line = sys.stdin.readline()
    if line == "":
        return None
    line = line.strip()
    if not line:
        return _read()
    return json.loads(line)


def _write(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _notify(update):
    _write({"jsonrpc": "2.0", "method": "session/update",
            "params": {"sessionId": SESSION_ID, "update": update}})


def _request_permission(rid, tool_call):
    _write({
        "jsonrpc": "2.0", "id": rid, "method": "session/request_permission",
        "params": {
            "sessionId": SESSION_ID,
            "toolCall": tool_call,
            "options": [
                {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
                {"optionId": "allow-always", "name": "Always allow", "kind": "allow_always"},
                {"optionId": "reject-once", "name": "Reject once", "kind": "reject_once"},
                {"optionId": "reject-always", "name": "Always reject", "kind": "reject_always"},
            ],
        },
    })
    # Await the driver's response to this permission request.
    while True:
        msg = _read()
        if msg is None:
            sys.exit(0)
        if msg.get("id") == rid and "result" in msg:
            return msg["result"]


def main() -> int:
    rid = 1000
    while True:
        msg = _read()
        if msg is None:
            return 0
        method = msg.get("method")
        mid = msg.get("id")

        if method == "initialize":
            _write({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": msg.get("params", {}).get("protocolVersion", 1),
                "agentCapabilities": {"loadSession": False},
                "agentInfo": {"name": "fake-acp", "version": "0.0.1"},
                "authMethods": [],
            }})

        elif method == "session/new":
            _write({"jsonrpc": "2.0", "id": mid, "result": {"sessionId": SESSION_ID}})

        elif method == "session/prompt":
            if os.environ.get("FAKE_ACP_HANG"):
                # Never respond — the driver's deadline must kill us cleanly.
                import time as _t
                while True:
                    _t.sleep(3600)
            prompt = msg.get("params", {}).get("prompt", [])
            dump = os.environ.get("FAKE_ACP_PROMPT_DUMP")
            if dump:
                text = "\n".join(b.get("text", "") for b in prompt if isinstance(b, dict))
                with open(dump, "w", encoding="utf-8") as f:
                    f.write(text)

            # Stream two message chunks.
            _notify({"sessionUpdate": "agent_message_chunk",
                     "content": {"type": "text", "text": "working on it "}})
            _notify({"sessionUpdate": "agent_message_chunk",
                     "content": {"type": "text", "text": "almost done"}})

            # One tool_call update.
            _notify({"sessionUpdate": "tool_call", "toolCallId": "tc_1",
                     "title": "Write notes.txt", "kind": "edit", "status": "pending",
                     "locations": [{"path": "notes.txt"}],
                     "rawInput": {"path": "notes.txt", "content": "hi"}})

            # Permission #1 — benign write -> expect ALLOW.
            rid += 1
            _request_permission(rid, {
                "toolCallId": "tc_1", "title": "Write notes.txt", "kind": "edit",
                "locations": [{"path": "notes.txt"}],
                "rawInput": {"path": "notes.txt", "content": "hi"},
            })

            # Permission #2 — gated path segment 'dain' -> expect DENY.
            rid += 1
            _request_permission(rid, {
                "toolCallId": "tc_2", "title": "Write dain/notes.md", "kind": "edit",
                "locations": [{"path": "dain/notes.md"}],
                "rawInput": {"path": "dain/notes.md", "content": "secret-ish"},
            })

            # Finish the turn.
            _write({"jsonrpc": "2.0", "id": mid, "result": {"stopReason": "end_turn"}})

        elif method is not None and mid is not None:
            _write({"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32601, "message": f"unknown method {method}"}})
        # notifications from client (none expected) are ignored.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
