#!/usr/bin/env python3
"""AIOS MCP server — the agent delegation interface.

This is what makes an agent *delegate functions to AIOS* rather than treat
AIOS as an optional library. It exposes AIOS organs as MCP tools over the
stdio transport (newline-delimited JSON-RPC 2.0). Any MCP-speaking agent
(Claude Code, Codex, etc.) that registers this server gets AIOS organs in
its tool list — and routes work through them.

Exposed tools (the clerk-level system calls — never the chief-level ones):

  aios_route      — ask CapabilityOS which capability/helper fits a task
  aios_helper_run — delegate a routine subtask to a specialist helper
  aios_retrieve   — pull context from MemoryOS accepted memory
  aios_challenge  — get a GenesisOS prompt-prison critique of reasoning
  aios_observe    — report an observation back to AIOS (agent → AIOS)

Authority boundary (DNA / ASC-0174): this server exposes observe/ingest/
retrieve/route/challenge — the clerk system calls. It does NOT expose
execute/override/promote/close as free tools — those are authority-bearing
and stay with the deterministic kernel + operator. A tool computes or
proposes; it never accepts memory or closes a contract.

Transport: MCP stdio — one JSON-RPC message per line on stdin/stdout.
Stdlib only; no MCP SDK dependency.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "aios"
SERVER_VERSION = "0.1.0"

# Learning kinds for the composite AGENT SELF organ (mirrors aios_agent_self._VALID_KINDS).
_SELF_KINDS = ("correction", "what_worked", "decision", "limit")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    except OSError as exc:
        return False, f"exec failed: {exc}"
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "non-zero exit").strip()
    return True, proc.stdout.strip()


# --- tool definitions -------------------------------------------------------

def tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": "aios_route",
            "description": "Ask AIOS (CapabilityOS) which capability or specialist helper fits a task. Use this before doing routine work yourself — AIOS may have a specialist for it.",
            "inputSchema": {
                "type": "object",
                "properties": {"task": {"type": "string", "description": "the task to route"}},
                "required": ["task"],
            },
        },
        {
            "name": "aios_helper_run",
            "description": "Delegate a routine subtask to an AIOS specialist helper (e.g. summarization, classification, consolidation) instead of doing it yourself. Helpers are local-LLM task experts. Returns a computed proposal.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "helper": {"type": "string", "description": "helper id, e.g. cap_helper_summarize"},
                    "input": {"type": "string", "description": "the text/input for the helper"},
                },
                "required": ["helper", "input"],
            },
        },
        {
            "name": "aios_retrieve",
            "description": "Retrieve relevant context from AIOS MemoryOS accepted memory for a task. Use this to recall prior decisions and provenance instead of assuming.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "what to retrieve context about"}},
                "required": ["query"],
            },
        },
        {
            "name": "aios_challenge",
            "description": "Get a GenesisOS prompt-prison critique of a piece of reasoning — detects single-frame, assumption-silent, and time-frozen thinking. Use this when a decision feels too easy.",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "the reasoning/thesis to critique"}},
                "required": ["text"],
            },
        },
        {
            "name": "aios_direct",
            "description": "GenesisOS direction: given a situation (what's stuck/unclear/drifting), returns a recommended branch type, first concrete move, what to avoid, and 1h/1w/1y time horizons. Use when you don't know what to do next — not to critique, but to choose direction.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "situation": {"type": "string", "description": "current situation — what's stuck, unclear, or drifting"},
                    "context": {"type": "string", "description": "optional: prior decisions or constraints"},
                },
                "required": ["situation"],
            },
        },
        {
            "name": "aios_observe",
            "description": "Report an observation back to AIOS (a capability gap, failure mode, workflow pattern, or decision). This is how an agent feeds AIOS's memory and dream cycle.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "short human-readable observation"},
                    "event_type": {"type": "string", "description": "capability_gap | failure_mode | workflow_pattern | decision | handoff"},
                    "context": {"type": "string", "description": "repo, task, or contract where observed"},
                },
                "required": ["summary"],
            },
        },
        # Gateway to ALL AIOS organs (deferred-loading: discover via aios_list_tools,
        # invoke via aios_invoke through the authority gate) — exposes the full organ
        # set without dumping 150 schemas into context (the token-bloat trap).
        {
            "name": "aios_list_tools",
            "description": "List every AIOS organ available as a tool (name, class, domain). Call this to discover what AIOS can do before invoking via aios_invoke.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "aios_invoke",
            "description": "Invoke any AIOS organ tool (from aios_list_tools) THROUGH the authority gate. Read/advisory tools run; write tools require the agent's authority or return needs_approval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "organ tool name from aios_list_tools"},
                    "arguments": {"type": "object", "description": "arguments for the tool"},
                    "agent": {"type": "string", "description": "caller identity for the gate (default codex@myworld)"},
                },
                "required": ["tool"],
            },
        },
        {
            "name": "aios_predict_behavior",
            "description": (
                "Predict the most likely next action an AI agent will take, given context and candidates. "
                "Uses DescentNet (Sheaf Theory backbone) + AIOS AkashicRecord of prior agent behavior traces. "
                "Returns ranked candidates with confidence scores and H¹ ambiguity signal. "
                "Use for: competition prediction, agent simulation, behavior modeling."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "Current agent context / situation / observation"},
                    "candidates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Possible next actions the agent could take",
                    },
                    "top_k": {"type": "integer", "default": 3, "description": "How many top predictions to return"},
                },
                "required": ["context", "candidates"],
            },
        },
        {
            "name": "aios_ingest_cli_session",
            "description": (
                "Ingest recent CLI session logs into AIOS AkashicRecord as behavioral memories. "
                "Privacy-safe: only tool names / action types are stored, never content or arguments. "
                "Opt-in: choose which session categories to include. "
                "This grows the AkashicRecord so future predictions improve."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["claude", "codex", "gemini"],
                        "description": "Which CLI provider's sessions to ingest",
                    },
                    "opt_in": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["docs", "data", "code", "personal"]},
                        "description": "Categories of sessions to include (opt-in, privacy control)",
                    },
                    "limit": {"type": "integer", "default": 20, "description": "Max recent sessions to scan"},
                },
                "required": ["provider"],
            },
        },
        {
            "name": "aios_onboard",
            "description": (
                "Absorb this device's capabilities and verify what AIOS can use RIGHT NOW. "
                "Scans local LLMs (Ollama), agent CLIs (claude/codex/gemini/grok/cursor), MCP servers "
                "and skills; classifies which are executable (have an adapter); runs a fast e2e probe; "
                "and returns a readiness manifest. Call this first when onboarding AIOS onto a new "
                "machine — it tells you exactly which providers are ready to route work to."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "probe": {"type": "boolean", "default": True,
                              "description": "run live e2e probes (Ollama reachable, each CLI invocable)"},
                },
            },
        },
        # --- Composite AGENT SELF (per-agent persistent identity) ------------
        # The composite self = a frozen model + a memory/identity that SURVIVES
        # the session and travels across substrates. These tools let ANY MCP
        # client birth, learn, checkpoint, and carry a persistent "someone".
        # Write side (accept/reject) is deliberately NOT exposed — draft-first.
        {
            "name": "aios_self_status",
            "description": (
                "The composite self is a persistent identity (model + memory that survives sessions). "
                "This returns its state: counts of draft/accepted/rejected learnings, last birth + "
                "last checkpoint timestamps, and the local store path. Call first to see if a self exists."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "agent id (default: $AIOS_AGENT_ID or 'default')"},
                },
            },
        },
        {
            "name": "aios_self_birth",
            "description": (
                "BIRTH the composite self: compile and RETURN the full SELF.md text (identity + accepted "
                "learnings + where the last session left off). Inject this at session start to give a "
                "frozen model continuity — it wakes up as the same 'someone', not amnesiac. Returns the "
                "text itself so a remote client can paste it into its own context."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "agent id (default: $AIOS_AGENT_ID or 'default')"},
                    "max_words": {"type": "integer", "default": 1200, "description": "word budget for the compiled self"},
                },
            },
        },
        {
            "name": "aios_self_learn",
            "description": (
                "Teach the composite self something durable (a correction, what worked, a decision, or a limit). "
                "This appends a DRAFT only — MCP callers can PROPOSE but never silently accept (AIOS DNA #2, "
                "draft-first). A draft does NOT appear in future births until a human explicitly accepts it via "
                "the local CLI: `aios self accept <id> --reviewer <who> --note <why>`. Returns the draft id."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "one content-rich sentence (single line, no newlines)"},
                    "kind": {"type": "string", "enum": list(_SELF_KINDS),
                             "description": "correction | what_worked | decision | limit"},
                    "refs": {"type": "array", "items": {"type": "string"},
                             "description": "optional evidence refs (paths/urls) for the provenance chain"},
                    "agent": {"type": "string", "description": "agent id (default: $AIOS_AGENT_ID or 'default')"},
                },
                "required": ["text", "kind"],
            },
        },
        {
            "name": "aios_self_checkpoint",
            "description": (
                "DEATH half of the loop: record where this session left off so the next birth can resume. "
                "Append what is in flight and the next step; the composite self carries this across the "
                "session boundary. Call before ending a session or handing off."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "in_flight": {"type": "string", "description": "what is currently in progress"},
                    "next": {"type": "string", "description": "the next concrete step to resume with"},
                    "note": {"type": "string", "description": "optional extra context"},
                    "session": {"type": "string", "description": "optional session id"},
                    "agent": {"type": "string", "description": "agent id (default: $AIOS_AGENT_ID or 'default')"},
                },
                "required": ["in_flight", "next"],
            },
        },
        {
            "name": "aios_self_carry",
            "description": (
                "CARRY the composite self onto another substrate: render the compiled self as a ready-to-paste "
                "block for the target — 'claude' (CLAUDE.md / SessionStart hook), 'codex' (AGENTS.md), 'system' "
                "(plain system-prompt text), or 'json'. The model is replaceable; the 'someone' persists. "
                "Use this to move a self from one agent/tool to another."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "enum": ["claude", "codex", "system", "json"],
                           "description": "target substrate to render the self for"},
                    "agent": {"type": "string", "description": "agent id (default: $AIOS_AGENT_ID or 'default')"},
                },
                "required": ["to"],
            },
        },
    ]


# --- tool handlers ----------------------------------------------------------

def call_route(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    task = str(args.get("task", "")).strip()
    if not task:
        return False, "task is required"
    ok, out = _run([sys.executable, "-m", "capabilityos.cli", "recommend", "--task", task, "--json"],
                    root / "CapabilityOS")
    if ok:
        try:
            recs = json.loads(out).get("recommendations", [])[:5]
            lines = [f"{r.get('id')} (score {r.get('score', 0):.1f}) — {r.get('name')}" for r in recs]
            return True, "AIOS route (CapabilityOS) — top capabilities:\n" + ("\n".join(lines) or "(no match)")
        except ValueError:
            return True, out
    # Fallback: role_router keyword heuristic when CapabilityOS is unavailable
    rr_ok, rr_out = _run([sys.executable, (root / "scripts" / "aios_role_router.py").as_posix(), task], root)
    if rr_ok:
        try:
            r = json.loads(rr_out)
            return True, (
                f"AIOS route (role_router fallback) — role: {r['role']} "
                f"provider: {r['provider']} confidence: {r['confidence']}\n"
                f"reason: {r['reason']}"
            )
        except (ValueError, KeyError):
            return True, rr_out
    return False, out


def call_helper_run(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    helper = str(args.get("helper", "")).strip()
    text = str(args.get("input", ""))
    if not helper or not text:
        return False, "helper and input are required"
    ok, out = _run([sys.executable, (root / "scripts" / "aios_helper.py").as_posix(),
                    "--root", root.as_posix(), "run", "--helper", helper, "--input", text, "--json"], root)
    if not ok:
        return False, out
    try:
        d = json.loads(out)
        return True, f"[{d.get('helper_id')} via {d.get('model')}] (computed proposal — not an accepted record)\n\n{d.get('result', '')}"
    except ValueError:
        return True, out


def call_retrieve(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    query = str(args.get("query", "")).strip()
    if not query:
        return False, "query is required"
    ok, out = _run([sys.executable, "-m", "memoryos", "context", "build", "--task", query, "--json"],
                    root / "memoryOS")
    if not ok:
        return False, out
    try:
        d = json.loads(out)
        decisions = d.get("decisions", [])[:5]
        lines = [f"- {x.get('content', '')[:160]}" for x in decisions]
        return True, f"AIOS MemoryOS context (trace {d.get('trace_id', '?')}):\n" + ("\n".join(lines) or "(no accepted memory matched)")
    except ValueError:
        return True, out


def call_challenge(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    text = str(args.get("text", "")).strip()
    if not text:
        return False, "text is required"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(text)
        tmp = fh.name
    ok, out = _run([sys.executable, "-m", "genesisos.cli", "critic", "--text", tmp, "--json"],
                   root / "GenesisOS")
    Path(tmp).unlink(missing_ok=True)
    if not ok:
        return False, out
    try:
        d = json.loads(out)
        sigs = d.get("prison_signatures", [])
        if not sigs:
            return True, "GenesisOS critique: no prompt-prison signatures detected."
        lines = [f"- {s.get('signature')}: {s.get('evidence')} → escape: {s.get('escape_vector')}" for s in sigs]
        return True, "GenesisOS critique (advisory only):\n" + "\n".join(lines)
    except ValueError:
        return True, out


def call_direct(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    situation = str(args.get("situation", "")).strip()
    if not situation:
        return False, "situation is required"
    context = str(args.get("context", "")).strip() or None
    ctx_args = ["--context", context] if context else []
    ok, out = _run(
        [sys.executable, "-m", "genesisos.cli", "direct",
         "--situation", situation, *ctx_args, "--json"],
        root / "GenesisOS",
    )
    if not ok:
        return False, out
    try:
        d = json.loads(out)
        diag = d.get("diagnosis", {})
        rec = d.get("recommendation", {})
        lines = [
            f"signal: {diag.get('discomfort_signal')}",
            f"branch: {rec.get('branch_type')} — {rec.get('premise')}",
            f"first_move: {d.get('first_move')}",
            f"avoid: {d.get('avoid')}",
        ]
        horizons = d.get("time_horizons", {})
        for h, v in horizons.items():
            lines.append(f"{h}: {v}")
        return True, "GenesisOS direction (advisory only):\n" + "\n".join(lines)
    except ValueError:
        return True, out


def call_observe(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    summary = str(args.get("summary", "")).strip()
    if not summary:
        return False, "summary is required"
    event_type = str(args.get("event_type", "workflow_pattern"))
    context = str(args.get("context", "mcp_agent_session"))
    buf = root / ".aios" / "observation_buffer" / "mcp_agent"
    buf.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    obs = {
        "spec_version": "aios.agent_interface.v0.1",
        "agent_id": "mcp_agent",
        "substrate": "mcp_client",
        "observed_at": now_iso(),
        "context": context,
        "event_type": event_type,
        "summary": summary,
        "privacy_class": "workspace_internal",
        "recommended_route": "none",
    }
    path = buf / f"{stamp}.json"
    path.write_text(json.dumps(obs, indent=2, ensure_ascii=False), encoding="utf-8")
    return True, f"observation recorded to AIOS: {path.relative_to(root)}"


def _aios_tools_mod():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import aios_tools  # noqa: E402
    import aios_turn_loop  # noqa: E402
    return aios_tools, aios_turn_loop


def _agent_self_mod():
    """In-process handle to the composite AGENT SELF organ (no subprocess)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import aios_agent_self  # noqa: E402
    return aios_agent_self


def call_list_tools(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    """Discovery: the full organ catalog (deferred-loading — no schema dump)."""
    try:
        tools, _ = _aios_tools_mod()
        return True, json.dumps({"tools": tools.list_tools()}, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return False, f"list_tools unavailable: {exc}"


def call_invoke(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    """Invoke an organ THROUGH the authority gate — external agents are gated too."""
    name = str(args.get("tool", "")).strip()
    if not name:
        return False, "tool is required"
    arguments = args.get("arguments") or {}
    agent = str(args.get("agent") or "codex@myworld")
    try:
        tools, tl = _aios_tools_mod()
        decision = tools.gate_for(agent)(name, arguments)
        if decision == tl.DENY:
            return True, json.dumps({"status": "denied", "tool": name, "reason": "gate denied"})
        if decision == tl.ASK:
            return True, json.dumps({"status": "needs_approval", "tool": name,
                                     "reason": f"{agent} not authorized; operator approval required"})
        status, result = tools.build_registry().dispatch(tl.ToolCall(name, dict(arguments)))
        return True, json.dumps({"status": status, "tool": name, "result": result}, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return False, f"invoke failed: {exc}"


def call_predict_behavior(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    context = str(args.get("context", "")).strip()
    candidates = args.get("candidates", [])
    top_k = int(args.get("top_k") or 3)
    if not context or not candidates:
        return False, "context and candidates are required"
    ok, out = _run(
        [sys.executable, str(root / "scripts" / "aios_agent_behavior.py"),
         "predict", "--context", context[:400],
         "--candidates", ",".join(str(c) for c in candidates),
         "--top-k", str(top_k), "--json"],
        root,
    )
    return ok, out


def call_ingest_cli_session(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    provider = str(args.get("provider", "claude"))
    opt_in = args.get("opt_in") or ["code", "docs"]
    limit = int(args.get("limit") or 20)
    ok, out = _run(
        [sys.executable, str(root / "scripts" / "aios_agent_behavior.py"),
         "ingest", "--from", provider,
         "--opt-in", ",".join(str(c) for c in opt_in),
         "--limit", str(limit), "--json"],
        root,
    )
    return ok, out


def call_onboard(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    cmd = [sys.executable, str(root / "scripts" / "aios_onboard.py"), "--json"]
    if args.get("probe") is False:
        cmd.append("--no-probe")
    return _run(cmd, root, timeout=120)


# --- Composite AGENT SELF handlers (in-process; local-only; no network) ------

def call_self_status(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    try:
        s = _agent_self_mod()
        return True, json.dumps(s.status(agent_id=args.get("agent")), ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return False, f"self_status failed: {exc}"


def call_self_birth(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    """Birth the self and return the compiled SELF.md text (so a remote client can inject it)."""
    try:
        s = _agent_self_mod()
        max_words = int(args.get("max_words") or 1200)
        rendered = s.carry("json", agent_id=args.get("agent"), max_words=max_words)
        return True, str(rendered.get("self_md", "")) if isinstance(rendered, dict) else str(rendered)
    except Exception as exc:  # noqa: BLE001
        return False, f"self_birth failed: {exc}"


def call_self_learn(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    """Append a DRAFT learning (DNA #2: propose only — acceptance is a human CLI review)."""
    text = str(args.get("text", "")).strip()
    kind = str(args.get("kind", "")).strip()
    if not text:
        return False, "text is required"
    if kind not in _SELF_KINDS:
        return False, f"kind must be one of {list(_SELF_KINDS)}"
    refs = args.get("refs") or []
    if not isinstance(refs, list):
        refs = [str(refs)]
    try:
        s = _agent_self_mod()
        entry = s.learn(kind, text, refs=[str(r) for r in refs], agent_id=args.get("agent"))
        return True, json.dumps({
            "status": "draft",
            "id": entry.get("id"),
            "note": "DRAFT recorded — not yet in the self. Accept via: "
                    f"aios self accept {entry.get('id')} --reviewer <who> --note <why>",
        }, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return False, f"self_learn failed: {exc}"


def call_self_checkpoint(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    in_flight = str(args.get("in_flight", "")).strip()
    next_ = str(args.get("next", "")).strip()
    if not in_flight or not next_:
        return False, "in_flight and next are required"
    try:
        s = _agent_self_mod()
        entry = s.checkpoint(in_flight, next_, note=(args.get("note") or None),
                             session=(args.get("session") or None), agent_id=args.get("agent"))
        return True, json.dumps({"status": "checkpointed", **entry}, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return False, f"self_checkpoint failed: {exc}"


def call_self_carry(root: Path, args: dict[str, Any]) -> tuple[bool, str]:
    target = str(args.get("to", "")).strip()
    if target not in ("claude", "codex", "system", "json"):
        return False, "to must be one of claude|codex|system|json"
    try:
        s = _agent_self_mod()
        rendered = s.carry(target, agent_id=args.get("agent"))
        return True, json.dumps(rendered, ensure_ascii=False) if isinstance(rendered, dict) else str(rendered)
    except Exception as exc:  # noqa: BLE001
        return False, f"self_carry failed: {exc}"


HANDLERS = {
    "aios_route": call_route,
    "aios_helper_run": call_helper_run,
    "aios_retrieve": call_retrieve,
    "aios_challenge": call_challenge,
    "aios_direct": call_direct,
    "aios_observe": call_observe,
    "aios_list_tools": call_list_tools,
    "aios_invoke": call_invoke,
    "aios_predict_behavior": call_predict_behavior,
    "aios_ingest_cli_session": call_ingest_cli_session,
    "aios_onboard": call_onboard,
    "aios_self_status": call_self_status,
    "aios_self_birth": call_self_birth,
    "aios_self_learn": call_self_learn,
    "aios_self_checkpoint": call_self_checkpoint,
    "aios_self_carry": call_self_carry,
}


# --- JSON-RPC / MCP loop ----------------------------------------------------

def handle(root: Path, msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    mid = msg.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": "AIOS organs as MCP tools. Delegate routine work to aios_helper_run, "
                            "route via aios_route, recall via aios_retrieve, pressure-test reasoning "
                            "via aios_challenge, and report findings via aios_observe.",
        }}

    if method in ("notifications/initialized", "initialized"):
        return None  # notification — no response

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": tool_specs()}}

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = HANDLERS.get(name)
        if handler is None:
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"unknown tool: {name}"}], "isError": True}}
        ok, text = handler(root, arguments)
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": text}], "isError": not ok}}

    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}

    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="AIOS MCP server — agent delegation interface")
    p.add_argument("--root", default=".", help="AIOS control-plane root")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        try:
            response = handle(root, msg)
        except Exception as exc:  # noqa: BLE001 — never crash the server loop
            response = {"jsonrpc": "2.0", "id": msg.get("id"),
                        "error": {"code": -32603, "message": f"internal error: {exc}"}}
        if response is not None:
            out.write(json.dumps(response, ensure_ascii=False) + "\n")
            out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
