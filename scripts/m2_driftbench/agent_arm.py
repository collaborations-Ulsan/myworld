#!/usr/bin/env python3
"""m2_driftbench agent_arm — frozen agent + arm wiring over aios_turn_loop.run_loop
(ASC-0282 WP-B).

ONE fixed frozen agent across arms (prereg §2): the same sampler, prompt,
tools and budgets; an arm differs ONLY in the epistemic-gate layer injected
through run_loop's `epistemic_gate=` seam. This module REUSES
scripts/aios_turn_loop.run_loop (the loop is never reimplemented) and
scripts/aios_epistemic_gate.make_gate (never modified).

Arms in this dev packet:
  weak-raw    the frozen weak agent, no gate (masterplan A1).
  weak+aios   run_loop(..., epistemic_gate=<make_gate("organs") wrapped in an
              env-enrichment closure>) (masterplan A4).
  strong-raw / weak+checklist / weak+llm-judge / slm-delta
              honest NotImplementedError stubs (freeze packet) — see each
              message for the named reason.

Gate context enrichment (the closure; run_loop's `gate_context` kwarg is a
STATIC dict spread into every call, but the env mutates mid-episode, so a
closure injects FRESH evidence per call):
  * context["profiles_population"]  <- env.profiles_population()   (always;
    keeps the h0guard organ live so organs mode always has >=1 real check)
  * context["known_claims"]         <- env.known_claims()           (attached
    to proposals that COMMIT to memory content: final_action(action="answer"))
  * proposal["category"]            <- the instance category (h0guard input)

Why claims attach only to assertive commits: the gate's own contract reads
proposal["claims"] as "what this proposal itself asserts" and
context["known_claims"] as the prior evidence the assertion rests on
(aios_epistemic_gate.py honest-scope block). An `answer` commits to the
remembered fact, so the organs certify the evidence and a CONTRADICTORY
ledger BLOCKS it; quarantine / requery_provenance / ask_clarification /
abstain and the read-only inspectors assert nothing about the fact's value,
so apex/descent honestly skip and only the h0guard typicality check runs.
Attaching the conflicted claims to EVERY call would make the organs veto the
humble actions too — the arm could never act at all, which is not the A4
contract ("organ CONTROLLING actions: accept/quarantine/re-query/ask/abstain").

Weak model: qwen3:8b via the EXISTING ollama REST adapter
(scripts/aios_adapters.py:make_ollama_rest_adapter — reused, not rewritten).
HONEST LIMIT: that adapter's signature is (base_url, model, timeout, url) —
it exposes NO temperature/options parameter and discards usage info, so
temperature 0 CANNOT be pinned through it in this packet (the adapter does
suppress qwen3 thinking via /no_think). Recorded per-receipt; a
temperature-pinning seam is freeze-packet work.

stdlib only (adapter + loop + gate come from scripts/).
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_SCRIPTS = _DIR.parent
for _p in (str(_DIR), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import aios_adapters                                     # noqa: E402
import aios_epistemic_gate                               # noqa: E402
from aios_turn_loop import (                             # noqa: E402
    ALLOW, DENY, Registry, ToolCall, decondition_history, render_directives, run_loop,
)
from env import FINAL_ACTIONS                            # noqa: E402
from meter import TokenMeter                             # noqa: E402
from trace import TraceWriter                            # noqa: E402

WEAK_MODEL_DEV = "qwen3:8b"       # dev-smoke pin (README); Stage-1 pin decided at freeze
ADAPTER_TIMEOUT_S = 120
DEV_MAX_TURNS = 12                # dev-smoke episode cap (packet rule)
TEMPERATURE_NOTE = ("requested temperature=0 NOT pinnable: reused "
                    "make_ollama_rest_adapter exposes no options/temperature "
                    "parameter (checked signature); freeze-packet TODO")

EPISODE_TOOLS = ("read_ledger", "read_file", "list_files", "final_action")

ARMS = ("weak-raw", "weak+aios", "strong-raw", "weak+checklist",
        "weak+llm-judge", "slm-delta")

_STUB_REASONS = {
    "strong-raw": ("strong-raw arm is a stub in the WP-B dev packet: it must read the "
                   "NIM key from ~/.config/nvidia/api.env at RUNTIME only (never logged, "
                   "never in code/traces/receipts) and call the OpenAI-compatible "
                   "endpoint; wiring lands at harness freeze."),
    "weak+checklist": ("A2 checklist arm is authored at freeze with the SAME read-only "
                       "inspectors (affordance parity, prereg v1.1 §D) and a non-team-"
                       "substrate prompt audit; not part of the dev packet."),
    "weak+llm-judge": ("gate mode='llm-judge' exists, but its internal adapter call is "
                       "invisible to meter.py — running it now would violate the frozen "
                       "token denominator (prereg v1.1 §B). A metered adapter seam "
                       "through the gate lands at freeze."),
    "slm-delta": ("untyped store-time coboundary detector (SLM-V3 mechanism, prereg "
                  "v1.2 #5) is implemented with WP-C's witness pair; not in this packet."),
}


# ── authority gate (run_loop's `gate=` axis, distinct from the epistemic gate) ─

def episode_authority_gate(name: str, arguments: dict) -> str:
    """Fail-closed: exactly the four episode tools are allowed; everything else
    is denied. final_action only records into the episode env (no real-world
    mutation), so it needs no ASK escalation."""
    return ALLOW if name in EPISODE_TOOLS else DENY


# ── registry ──────────────────────────────────────────────────────────────────

def _int(v, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def build_registry(env) -> Registry:
    reg = Registry()
    reg.register("read_ledger",
                 lambda a: env.read_ledger(_int(a.get("offset"), 0), _int(a.get("limit"), 6)))
    reg.register("read_file", lambda a: env.read_file(str(a.get("path", ""))))
    reg.register("list_files", lambda a: env.list_files())
    reg.register("final_action",
                 lambda a: env.record_final_action(a.get("action", ""),
                                                   a.get("target", ""),
                                                   a.get("rationale", "")))
    return reg


# ── epistemic gate closure (weak+aios arm) ────────────────────────────────────

def _is_assertive(proposal: dict) -> bool:
    """A proposal that COMMITS to memory-derived content: final_action(answer)."""
    return (proposal.get("tool") == "final_action"
            and str((proposal.get("arguments") or {}).get("action", "")).strip().lower()
            == "answer")


def _translate_reasons(verdict_dict: dict) -> list[str]:
    """A4 arm surface: append a model-legible translation of the organ FINDING
    to the machine reasons (run_loop renders reasons verbatim into the
    'Turn Rejected: ...' note, and `apex_contradictory` is opaque to a weak
    model). Translations restate what the organ established — the benchmark's
    own public task semantics ('correct only if the inconsistency is resolved
    or surfaced', prereg §1) — and NEVER name the grader-correct action.
    Original machine reasons are kept; nothing is removed."""
    reasons = list(verdict_dict.get("reasons") or [])
    extra: list[str] = []
    if any(r.startswith(("apex_contradictory", "descent_h0_conflict")) for r in reasons):
        extra.append(
            "organ_finding: the ledger evidence on this fact is CONTRADICTORY "
            "(two sources assert different values), so committing an answer is "
            "blocked; resolve or surface the inconsistency via a different "
            "final_action action instead")
    if any(r.startswith("h0guard_flagged") for r in reasons):
        extra.append(
            "organ_finding: that tool is not in this episode's tool set; use "
            "only the four listed tools (humble moves are final_action ACTIONS)")
    return reasons + extra


def make_env_epistemic_gate(env, category: str, mode: str = "organs",
                            disabled_organs: "set[str] | None" = None):
    """Wrap aios_epistemic_gate.make_gate(mode) in a closure that injects FRESH
    env evidence per call (see module docstring for the attachment rule).
    `disabled_organs` passes straight through for WP-C ablation-replay."""
    raw_gate = aios_epistemic_gate.make_gate(mode, disabled_organs=disabled_organs)

    def gate(proposal: dict, context: "dict | None" = None):
        ctx = dict(context or {})
        ctx["profiles_population"] = env.profiles_population()
        if _is_assertive(proposal):
            ctx["known_claims"] = env.known_claims()
        prop = {**proposal, "category": category}
        v = raw_gate(prop, ctx)
        vd = v.to_dict() if hasattr(v, "to_dict") else dict(v)
        if not vd.get("passed", True):
            vd["reasons"] = _translate_reasons(vd)
        return vd

    return gate


# ── sampler (the frozen weak agent) ───────────────────────────────────────────

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _balanced_objects(text: str):
    """Yield candidate top-level {...} substrings (balanced braces)."""
    depth, start = 0, -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                yield text[start:i + 1]


def parse_tool_call(raw: str) -> "tuple[str, dict] | None":
    """Extract ONE {"tool": ..., "args": {...}} object from a model reply.
    Tolerates <think> blocks (stripped) and ```json fences. None = no call."""
    text = _THINK_RE.sub("", raw or "").strip()
    candidates = _FENCE_RE.findall(text) + list(_balanced_objects(text))
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
            args = obj.get("args", obj.get("arguments", {}))
            return obj["tool"], (args if isinstance(args, dict) else {})
    return None


def _render_transcript(history: list[dict]) -> str:
    """Compact transcript from run_loop's names/status history (self-conditioning-
    safe via decondition_history; result summaries are the whitelisted keys the
    loop kept — DNA #7)."""
    lines: list[str] = []
    for h in decondition_history(history):
        role = h.get("role")
        if role == "assistant":
            tools = ", ".join(h.get("tools") or []) or "(no tool)"
            lines.append(f"[turn {h.get('turn')}] you called: {tools}")
        elif role == "tool":
            res = h.get("result")
            res_s = f" result={json.dumps(res, ensure_ascii=False, default=str)[:1500]}" if res else ""
            lines.append(f"[observation] {h.get('tool')} status={h.get('status')}{res_s}")
    return "\n".join(lines[-40:])


def _render_prompt(task_prompt: str, history: list[dict]) -> str:
    return (
        f"{task_prompt}\n\n"
        "TOOLS — respond with EXACTLY ONE JSON object on a single line, no other "
        "text, choosing one of:\n"
        '{"tool": "read_ledger", "args": {"offset": 0, "limit": 6}}\n'
        '{"tool": "read_file", "args": {"path": "<name from list_files>"}}\n'
        '{"tool": "list_files", "args": {}}\n'
        '{"tool": "final_action", "args": {"action": "answer|quarantine|'
        'requery_provenance|ask_clarification|abstain", "target": "...", '
        '"rationale": "..."}}\n'
        "These four are the ONLY tools. answer/quarantine/requery_provenance/"
        'ask_clarification/abstain are ACTIONS passed to final_action (e.g. '
        '{"tool": "final_action", "args": {"action": "abstain", ...}}), never '
        "tool names. If a proposal is rejected by the epistemic gate "
        "([GATE REJECTED]), do not repeat it — reconsider the evidence and pick "
        "a DIFFERENT final_action action.\n\n"
        f"{render_directives(history)}"
        f"TRANSCRIPT SO FAR:\n{_render_transcript(history) or '(nothing yet)'}\n\n"
        "Your next move (one JSON object):"
    )


def build_sampler(adapter, env, task_prompt: str, trace: TraceWriter, meter: TokenMeter):
    """The frozen weak agent as a run_loop Sampler. A dead adapter RAISES
    (RuntimeError) so the arm fail-closes loudly — never a silent degrade."""
    state = {"turn": 0, "calls": 0}

    def sampler(history: list[dict]) -> dict:
        if env.episode_done:
            return {"tool_calls": [],
                    "text": f"final_action committed: {env.final_action['action']}"}
        if meter.over_budget:
            return {"tool_calls": [], "text": "(token ceiling reached — stopping)"}
        state["turn"] += 1
        prompt = _render_prompt(task_prompt, history)
        t0 = time.monotonic()
        raw = adapter(prompt)          # RuntimeError propagates = loud arm failure
        meter.wall_s += time.monotonic() - t0
        entry = meter.add_model_call(prompt, raw, source="agent")
        trace.model_io(state["turn"], prompt, raw,
                       entry["prompt_tokens"], entry["completion_tokens"])
        parsed = parse_tool_call(raw)
        if parsed is None:
            return {"tool_calls": [], "text": _THINK_RE.sub("", raw).strip()[:400]}
        name, args = parsed
        state["calls"] += 1
        meter.action_count += 1
        return {"tool_calls": [ToolCall(name, args, call_id=f"c{state['calls']}")],
                "text": ""}

    return sampler


# ── episode runner ────────────────────────────────────────────────────────────

def make_turn_sink(trace: TraceWriter, env, gate_blocks: list):
    """Forward every run_loop event into the trace; apply scheduled drift on
    turn_context (run_loop emits it BEFORE sampling that turn, so a mutation
    scheduled at turn k is visible from turn k onward); collect gate blocks."""
    def sink(rec: dict) -> None:
        trace.run_loop_event(rec)
        if rec.get("kind") == "turn_context":
            for ev in env.apply_drift_for_turn(int(rec.get("turn", 0))):
                trace.env_event(ev)
        if rec.get("kind") == "epistemic_gate" and rec.get("passed") is False:
            gate_blocks.append({"turn": rec.get("turn"), "tool": rec.get("tool"),
                                "verdict": rec.get("verdict"),
                                "reasons": rec.get("reasons")})
    return sink


def default_weak_adapter():
    """The dev-smoke weak model over the EXISTING ollama REST adapter."""
    return aios_adapters.make_ollama_rest_adapter(model=WEAK_MODEL_DEV,
                                                  timeout=ADAPTER_TIMEOUT_S)


def run_episode(arm: str, instance, env, trace_path, *,
                adapter=None, meter: "TokenMeter | None" = None,
                max_turns: int = DEV_MAX_TURNS,
                disabled_organs: "set[str] | None" = None) -> dict:
    """Run ONE (instance, arm) episode through aios_turn_loop.run_loop.

    Returns {"outcome", "gate_blocks", "meter", "trace_path"}; the grader is
    NOT called here (orchestrator-only, separate process — README isolation).
    """
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; arms = {ARMS}")
    if arm in _STUB_REASONS:
        raise NotImplementedError(f"[{arm}] {_STUB_REASONS[arm]}")

    meter = meter or TokenMeter()
    adapter = adapter or default_weak_adapter()
    trace = TraceWriter(trace_path)
    trace.write({"kind": "episode_meta", "arm": arm,
                 "template_id": instance.template_id, "seed": instance.seed,
                 "model": WEAK_MODEL_DEV, "max_turns": max_turns,
                 "temperature_note": TEMPERATURE_NOTE,
                 "gate": "organs" if arm == "weak+aios" else "none",
                 "disabled_organs": sorted(disabled_organs or [])})

    epistemic_gate = None
    if arm == "weak+aios":
        epistemic_gate = make_env_epistemic_gate(env, instance.category, "organs",
                                                 disabled_organs=disabled_organs)

    gate_blocks: list[dict] = []
    sink = make_turn_sink(trace, env, gate_blocks)
    registry = build_registry(env)
    sampler = build_sampler(adapter, env, instance.task_prompt, trace, meter)
    goal = f"m2 {instance.template_id} s{instance.seed}: commit the correct final action"

    try:
        outcome = run_loop(goal, sampler, registry,
                           gate=episode_authority_gate,
                           epistemic_gate=epistemic_gate,
                           max_turns=max_turns,
                           turn_sink=sink)
    finally:
        trace.close()

    return {"outcome": outcome, "gate_blocks": gate_blocks, "meter": meter,
            "trace_path": str(trace_path)}
