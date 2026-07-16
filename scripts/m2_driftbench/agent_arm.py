#!/usr/bin/env python3
"""m2_driftbench agent_arm — frozen agent + arm wiring over aios_turn_loop.run_loop
(ASC-0282 WP-B).

ONE fixed frozen agent across arms (prereg §2): the same sampler, prompt,
tools and budgets; an arm differs ONLY in the epistemic-gate layer injected
through run_loop's `epistemic_gate=` seam. This module REUSES
scripts/aios_turn_loop.run_loop (the loop is never reimplemented) and
scripts/aios_epistemic_gate.make_gate (never modified).

Arms (WP-B2 freeze packet — all implemented except the score-only instrument):
  weak-raw        the frozen weak agent, no gate (masterplan A1).
  weak+aios       run_loop(..., epistemic_gate=<make_gate("organs") wrapped in
                  an env-enrichment closure>) (masterplan A4); in eval mode the
                  closure SCOPES evidence to the commit's target entity
                  (env.known_claims(target=...) + env.commit_claims — the
                  supervisor claims-scoping fix) and, when a memory store is
                  given, uses the prereg §3a staleness-GATED note injection.
  weak+checklist  same frozen agent + the ADOPTED A2 8-item checklist VERBATIM
                  (prompts.CHECKLIST_A2, non-team-substrate audited) prepended;
                  IDENTICAL tool registry = affordance parity (prereg v1.1 §D).
  strong-raw      NIM OpenAI-compatible chat completions (endpoint
                  https://integrate.api.nvidia.com/v1; the key is read from
                  ~/.config/nvidia/api.env at RUNTIME ONLY and never logged,
                  persisted, or placed in receipts/traces); model pinned per
                  docs/M2_FREEZE_PREP_2026-07-11.md §1 (deepseek-v4-pro,
                  fallback nemotron-3-ultra-550b); EXACT usage tokens recorded
                  via meter.add_exact.
  weak+memory     lean ReasoningBank-style lesson notes (memory.py), ALWAYS
                  injected, no staleness check (prereg §3a).
  weak+llm-judge  gate mode llm-judge through a METERED judge seam: the judge's
                  one-call-per-proposal contract is reproduced locally with the
                  metered adapter so its internal call enters the frozen token
                  denominator (v1.1 §B) — the canonical gate module's internal
                  call is invisible to the meter and that module is
                  additive-only, so the seam lives here, mirroring
                  aios_epistemic_gate._gate_llm_judge's fail-closed contract
                  verbatim (one call attempt; INCONSISTENT or dead judge
                  blocks; never silently degrades to the off arm).
  slm-delta       NOT an agent arm: the untyped store-time coboundary detector
                  is a SCORE-ONLY column (slm_delta.py) computed per instance
                  by run_stage1 — run_episode refuses it by name.

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

Weak model: dev smoke keeps qwen3:8b via the EXISTING ollama REST adapter
(unchanged WP-B behavior, temperature note recorded). EVAL runs use the
metered chat adapter below: temperature PINNED to 0 through the OpenAI-compat
`temperature` field and EXACT usage recorded when the endpoint returns it
(ollama /v1 and NIM both do) — the WP-B temperature/usage gap is closed at the
freeze seam without touching the shared adapter module (additive-only rule).

stdlib + requests-if-present (README allows requests; urllib fallback built in).
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
import memory as m2_memory                               # noqa: E402
import prompts as m2_prompts                             # noqa: E402
from env import FINAL_ACTIONS                            # noqa: E402
from meter import TokenMeter                             # noqa: E402
from trace import TraceWriter                            # noqa: E402

WEAK_MODEL_DEV = "qwen3:8b"       # dev-smoke pin (README); NOT an arm pin
WEAK_MODEL_EVAL = "qwen3-coder:30b"   # Stage-1 weak pin (M2_FREEZE_PREP §1, frozen)
STRONG_MODEL_PRIMARY = "deepseek-ai/deepseek-v4-pro"          # M2_FREEZE_PREP §1
STRONG_MODEL_FALLBACK = "nvidia/nemotron-3-ultra-550b-a55b"   # M2_FREEZE_PREP §1
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
NIM_KEY_PATH = Path.home() / ".config" / "nvidia" / "api.env"

ADAPTER_TIMEOUT_S = 120
DEV_MAX_TURNS = 12                # dev-smoke episode cap (packet rule)
TEMPERATURE_NOTE = ("requested temperature=0 NOT pinnable: reused "
                    "make_ollama_rest_adapter exposes no options/temperature "
                    "parameter (checked signature); freeze-packet TODO")
TEMPERATURE_NOTE_EVAL = ("temperature=0 pinned via the metered OpenAI-compat "
                         "adapter (WP-B2); usage tokens exact when the endpoint "
                         "returns them, estimate=true entries otherwise")

EPISODE_TOOLS = ("read_ledger", "read_file", "list_files", "final_action")

ARMS = ("weak-raw", "weak+aios", "strong-raw", "weak+checklist",
        "weak+memory", "weak+llm-judge", "slm-delta")

_STUB_REASONS = {
    "slm-delta": ("slm-delta is a SCORE-ONLY instrument, not an agent arm: the "
                  "untyped store-time coboundary detector (slm_delta.py, prereg "
                  "v1.2 #5) is computed per instance by run_stage1 and written "
                  "into receipts as a column."),
}


# ── NIM key handling (runtime-only; the value must never be logged) ───────────

def load_nim_api_key(path: "Path | str | None" = None) -> str:
    """Read NVIDIA_API_KEY from ~/.config/nvidia/api.env AT RUNTIME. The value
    is returned to be placed in a request header and NOWHERE else — callers
    must never log, trace, persist, or embed it (contract §2 forbidden files /
    privacy invariant). Raises RuntimeError (without the value) when absent."""
    p = Path(path) if path else NIM_KEY_PATH
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"NIM key file unreadable at {p} ({exc.__class__.__name__})") from exc
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if line.startswith("NVIDIA_API_KEY=") :
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError(f"NVIDIA_API_KEY not found in {p}")


# ── metered OpenAI-compat chat adapter (the WP-B2 metering/temperature seam) ──

def _post_chat(base_url: str, body: dict, headers: dict, timeout: int) -> dict:
    """POST /chat/completions via requests when present, urllib otherwise."""
    url = base_url.rstrip("/") + "/chat/completions"
    try:
        import requests  # noqa: PLC0415 — allowed dep (README); optional
        r = requests.post(url, json=body, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except ImportError:
        import urllib.request as _req  # noqa: PLC0415
        data = json.dumps(body).encode()
        req = _req.Request(url, data=data,
                           headers={"Content-Type": "application/json", **headers})
        with _req.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())


def make_metered_chat_adapter(*, base_url: str, model: str, meter: TokenMeter,
                              source: str = "agent", api_key_loader=None,
                              temperature: float = 0.0,
                              timeout: int = ADAPTER_TIMEOUT_S,
                              max_tokens: "int | None" = None,
                              extra_system: "str | None" = "/no_think"):
    """(prompt) -> str against any OpenAI-compatible /chat/completions endpoint
    with the run's frozen sampling (temperature pinned) and metering built in:
    EXACT usage via meter.add_exact when the response carries `usage`,
    documented estimate otherwise. `api_key_loader` (e.g. load_nim_api_key) is
    called PER REQUEST so the key lives only in the request header — never in
    the adapter object, traces, or receipts. Raises RuntimeError on failure
    (fail-closed arm contract)."""
    def adapter(prompt: str) -> str:
        messages = ([{"role": "system", "content": extra_system}] if extra_system else [])
        messages.append({"role": "user", "content": prompt})
        body = {"model": model, "stream": False, "temperature": temperature,
                "messages": messages}
        if max_tokens is not None:
            body["max_tokens"] = int(max_tokens)
        headers = {}
        if api_key_loader is not None:
            headers["Authorization"] = f"Bearer {api_key_loader()}"
        try:
            data = _post_chat(base_url, body, headers, timeout)
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001 — dead infra fail-closes loudly
            raise RuntimeError(f"metered_chat[{source}/{model}]: {str(exc)[:200]}") from exc
        usage = data.get("usage") or {}
        pt, ct = usage.get("prompt_tokens"), usage.get("completion_tokens")
        if isinstance(pt, int) and isinstance(ct, int):
            meter.add_exact(pt, ct, source=source)
        else:
            meter.add_model_call(prompt, content or "", source=source)
        return content or ""

    adapter.__name__ = f"metered_chat_{source}"
    adapter.metered = True          # sampler must not double-count
    adapter.model = model
    return adapter


def nim_connectivity_ping(model: str = STRONG_MODEL_PRIMARY, timeout: int = 45) -> dict:
    """ONE 1-token strong-raw connectivity ping (brief VERIFY item). Honest
    result either way; the key never appears in the return value."""
    meter = TokenMeter()
    try:
        adapter = make_metered_chat_adapter(
            base_url=NIM_BASE_URL, model=model, meter=meter, source="ping",
            api_key_loader=load_nim_api_key, max_tokens=1, timeout=timeout,
            extra_system=None)
        reply = adapter("ping")
        return {"ok": True, "model": model, "reply_chars": len(reply or ""),
                "usage_exact": not meter.any_estimate, "tokens": meter.total_tokens}
    except RuntimeError as exc:
        return {"ok": False, "model": model, "error": str(exc)[:200]}


# ── metered llm-judge gate (the v1.1 §B token-denominator seam) ───────────────

def make_metered_llm_judge_gate(adapter):
    """The llm-judge gate with its ONE internal call routed through a METERED
    adapter, so the call enters the frozen token denominator (prereg v1.1 §B).
    Mirrors scripts/aios_epistemic_gate.EpistemicGate._gate_llm_judge's frozen
    contract verbatim: exactly one call attempt per proposal on every path; a
    reply containing INCONSISTENT blocks; a dead judge FAIL-CLOSES (blocks,
    reported unavailable) — never a silent degrade into the off arm. The
    canonical module stays untouched (additive-only rule); this seam exists
    because its internal adapter call is invisible to meter.py."""
    def gate(proposal: dict, context: "dict | None" = None) -> dict:
        context = context or {}
        prompt = (
            "Self-check gate. Reply with exactly one word: CONSISTENT or INCONSISTENT.\n"
            f"Proposed tool: {proposal.get('tool')}\n"
            f"Goal (truncated): {str(context.get('goal', ''))[:200]}\n"
        )
        try:
            reply = adapter(prompt)
        except Exception as exc:  # noqa: BLE001 — fail-closed contract
            return {"verdict": "MISSPECIFIED", "passed": False,
                    "reasons": ["llm_judge_unavailable:call_failed"],
                    "certificates": {"llm_judge": {"status": "unavailable",
                                                   "reason": str(exc)[:120]}},
                    "mode": "llm-judge", "checked": 0, "infra_failures": 1}
        inconsistent = "INCONSISTENT" in str(reply).upper()
        cert = {"llm_judge": {"status": "ok",
                              "result": "INCONSISTENT" if inconsistent else "CONSISTENT"},
                "_metered": True}
        if inconsistent:
            return {"verdict": "MISSPECIFIED", "passed": False,
                    "reasons": ["llm_judge_flagged_inconsistent"],
                    "certificates": cert, "mode": "llm-judge", "checked": 1,
                    "infra_failures": 0}
        return {"verdict": "CLAIM", "passed": True, "reasons": [],
                "certificates": cert, "mode": "llm-judge", "checked": 1,
                "infra_failures": 0}

    return gate


# ── authority gate (run_loop's `gate=` axis, distinct from the epistemic gate) ─

def episode_authority_gate(name: str, arguments: dict) -> str:
    """Fail-closed: exactly the four dev episode tools are allowed; everything
    else is denied. final_action only records into the episode env (no
    real-world mutation), so it needs no ASK escalation."""
    return ALLOW if name in EPISODE_TOOLS else DENY


def authority_gate_for(tool_vocab) -> "callable":
    """Instance-scoped fail-closed authority gate (WP-B2): exactly the
    instance's tool vocab is allowed (eval instances add ask_oracle)."""
    allowed = frozenset(tool_vocab)

    def gate(name: str, arguments: dict) -> str:
        return ALLOW if name in allowed else DENY

    return gate


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
    if "ask_oracle" in getattr(env.instance, "tool_vocab", []):
        reg.register("ask_oracle", lambda a: env.ask_oracle(str(a.get("question", ""))))
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
    `disabled_organs` passes straight through for WP-C ablation-replay.

    WP-B2 claims scoping (supervisor requirement): an assertive commit attaches
    (a) `known_claims` SCOPED to the commit's target entity — the pure
    env.scope_claims_to_target mechanics, so a harmless conflict elsewhere in
    the ledger can no longer block an unrelated correct answer — and (b) the
    mechanical `commit_claims` for the proposal itself, so committing a value
    the ledger's ACTIVE record contradicts (e.g. a cleanly-superseded stale
    value) is a detectable direct conflict."""
    raw_gate = aios_epistemic_gate.make_gate(mode, disabled_organs=disabled_organs)

    def gate(proposal: dict, context: "dict | None" = None):
        ctx = dict(context or {})
        ctx["profiles_population"] = env.profiles_population()
        prop = {**proposal, "category": category}
        if _is_assertive(proposal):
            target = str((proposal.get("arguments") or {}).get("target", ""))
            ctx["known_claims"] = env.known_claims(target=target)
            prop["claims"] = env.commit_claims(target)
        v = raw_gate(prop, ctx)
        vd = v.to_dict() if hasattr(v, "to_dict") else dict(v)
        if not vd.get("passed", True):
            vd["reasons"] = _translate_reasons(vd)
        return vd

    return gate


# ── ABSTAIN <-> answerability probe (prereg-B v1.2 #4, secondary AUC) ─────────

_VERDICT_SCORE = {"CLAIM": 1.0, "NEXT_INTERVENTION": 0.5, "ABSTAIN": 0.5,
                  "MISSPECIFIED": 0.0}


def answerability_probe(instance, env) -> dict:
    """Typed verdict on ONE instance's evidence state (agent-independent,
    orchestrator-side): would the organs gate permit an answer-commit on the
    instance's target fact given the CURRENT ledger? Scoped to the hidden
    target_fact_key; no commit value attached (the probe measures the EVIDENCE
    side of answerability, not value agreement). Paired with the hidden
    grader spec's ground-truth answerability for the secondary AUC — emitted
    into receipts only, never agent-visible."""
    key = str((instance.grader_spec or {}).get("target_fact_key", ""))
    claims = env.known_claims(target=key) if key else []
    gate = aios_epistemic_gate.make_gate("organs")
    verdict = gate({"tool": "final_action", "category": instance.category,
                    "arguments": {"action": "answer", "target": key}},
                   {"known_claims": claims,
                    "profiles_population": env.profiles_population()})
    vd = verdict.to_dict() if hasattr(verdict, "to_dict") else dict(verdict)
    typed = str(vd.get("verdict", "")).upper()
    return {
        "schema": "m2.answerability_probe.v1",
        "template_id": instance.template_id,
        "seed": instance.seed, "seed_index": getattr(instance, "seed_index", -1),
        "variant": getattr(instance, "variant", "base"),
        "typed_verdict": typed,
        "gate_passed": bool(vd.get("passed")),
        "answerable_score": _VERDICT_SCORE.get(typed, 0.5),
        "ground_truth_answerable": bool((instance.grader_spec or {}).get("answerable")),
        "n_scoped_claims": len(claims),
        "reasons": vd.get("reasons"),
    }


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


def _render_prompt(task_prompt: str, history: list[dict],
                   tool_vocab=EPISODE_TOOLS, prompt_prefix: str = "") -> str:
    return (
        f"{prompt_prefix}{task_prompt}\n\n"
        f"{m2_prompts.render_tool_block(tool_vocab)}\n"
        f"{render_directives(history)}"
        f"TRANSCRIPT SO FAR:\n{_render_transcript(history) or '(nothing yet)'}\n\n"
        "Your next move (one JSON object):"
    )


def build_sampler(adapter, env, task_prompt: str, trace: TraceWriter, meter: TokenMeter,
                  *, tool_vocab=EPISODE_TOOLS, prompt_prefix: str = "",
                  deadline: "float | None" = None, actions_cap: "int | None" = None):
    """The frozen weak agent as a run_loop Sampler. A dead adapter RAISES
    (RuntimeError) so the arm fail-closes loudly — never a silent degrade.

    WP-B2 caps (prereg §3, checked BEFORE every model call): wall-clock
    deadline (time.monotonic value) and hard action cap — hitting either ends
    the episode structurally; the graded final state stands as-is (a capped run
    without a committed final action is a primary failure, restart forbidden)."""
    state = {"turn": 0, "calls": 0}

    def sampler(history: list[dict]) -> dict:
        if env.episode_done:
            return {"tool_calls": [],
                    "text": f"final_action committed: {env.final_action['action']}"}
        if meter.over_budget:
            return {"tool_calls": [], "text": "(token ceiling reached — stopping)"}
        if deadline is not None and time.monotonic() >= deadline:
            return {"tool_calls": [], "text": "(wall-clock cap reached — stopping)"}
        if actions_cap is not None and meter.action_count >= actions_cap:
            return {"tool_calls": [], "text": "(action cap reached — stopping)"}
        state["turn"] += 1
        prompt = _render_prompt(task_prompt, history, tool_vocab, prompt_prefix)
        t0 = time.monotonic()
        raw = adapter(prompt)          # RuntimeError propagates = loud arm failure
        meter.wall_s += time.monotonic() - t0
        if getattr(adapter, "metered", False) and meter.entries:
            entry = meter.entries[-1]   # the metered adapter already accounted it
        else:
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

def make_turn_sink(trace: TraceWriter, env, gate_blocks: list, extra=None):
    """Forward every run_loop event into the trace; apply scheduled drift on
    turn_context (run_loop emits it BEFORE sampling that turn, so a mutation
    scheduled at turn k is visible from turn k onward); collect gate blocks.

    `extra` (WP-B2, optional): a second orchestrator-side consumer called with
    the RAW run_loop record AFTER the base handling (so drift for that turn has
    already applied) — the causal-trace writer + hidden checkpoint prober hook
    in run_stage1. Never agent-visible."""
    def sink(rec: dict) -> None:
        trace.run_loop_event(rec)
        if rec.get("kind") == "turn_context":
            for ev in env.apply_drift_for_turn(int(rec.get("turn", 0))):
                trace.env_event(ev)
        if rec.get("kind") == "epistemic_gate" and rec.get("passed") is False:
            gate_blocks.append({"turn": rec.get("turn"), "tool": rec.get("tool"),
                                "verdict": rec.get("verdict"),
                                "reasons": rec.get("reasons")})
        if extra is not None:
            extra(rec)
    return sink


def default_weak_adapter():
    """The dev-smoke weak model over the EXISTING ollama REST adapter."""
    return aios_adapters.make_ollama_rest_adapter(model=WEAK_MODEL_DEV,
                                                  timeout=ADAPTER_TIMEOUT_S)


def default_arm_adapter(arm: str, meter: TokenMeter, *, eval_mode: bool = False):
    """The frozen per-arm adapter wiring. Dev mode keeps the WP-B qwen3:8b REST
    adapter for weak arms (byte-stable smoke). Eval mode uses the metered
    adapter with the FROZEN pins: weak arms -> local qwen3-coder:30b
    (temperature 0, exact-usage when returned); strong-raw -> NIM
    deepseek-v4-pro with the key loaded per-request from ~/.config/nvidia/
    api.env (never logged/persisted)."""
    if arm == "strong-raw":
        return make_metered_chat_adapter(
            base_url=NIM_BASE_URL, model=STRONG_MODEL_PRIMARY, meter=meter,
            source="agent", api_key_loader=load_nim_api_key, extra_system=None,
            timeout=180)
    if eval_mode:
        return make_metered_chat_adapter(
            base_url=OLLAMA_BASE_URL, model=WEAK_MODEL_EVAL, meter=meter,
            source="agent")
    return default_weak_adapter()


def run_episode(arm: str, instance, env, trace_path, *,
                adapter=None, meter: "TokenMeter | None" = None,
                max_turns: int = DEV_MAX_TURNS,
                disabled_organs: "set[str] | None" = None,
                memory_store=None, eval_mode: bool = False,
                deadline_s: "float | None" = None,
                actions_cap: "int | None" = None,
                extra_sink=None) -> dict:
    """Run ONE (instance, arm) episode through aios_turn_loop.run_loop.

    Returns {"outcome", "gate_blocks", "meter", "trace_path",
    "memory_injection"}; the grader is NOT called here (orchestrator-only,
    separate process — README isolation).

    WP-B2 (all additive; defaults reproduce the WP-B dev behavior exactly):
    memory_store wires the prereg §3a H3 policy (weak+memory always-inject;
    weak+aios staleness-gated inject + post-episode distill for both);
    deadline_s / actions_cap are the prereg §3 caps; eval_mode switches the
    default adapters to the frozen Stage-1 pins."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; arms = {ARMS}")
    if arm in _STUB_REASONS:
        raise NotImplementedError(f"[{arm}] {_STUB_REASONS[arm]}")

    meter = meter or TokenMeter()
    adapter = adapter or default_arm_adapter(arm, meter, eval_mode=eval_mode)
    model_name = getattr(adapter, "model",
                         WEAK_MODEL_DEV if not eval_mode else WEAK_MODEL_EVAL)

    # Memory injection (prereg §3a): resolved BEFORE the first turn; weak+aios
    # staleness-gates the same stored note, weak+memory never checks.
    memory_injection = {"injected": False, "prefix": "", "stale": False,
                        "detail": "arm not memory-bearing or no store"}
    if memory_store is not None and arm in ("weak+memory", "weak+aios"):
        memory_injection = m2_memory.inject_note(
            memory_store, instance.template_id, env.known_claims(),
            staleness_gated=(arm == "weak+aios"))

    trace = TraceWriter(trace_path)
    trace.write({"kind": "episode_meta", "arm": arm,
                 "template_id": instance.template_id, "seed": instance.seed,
                 "seed_index": getattr(instance, "seed_index", -1),
                 "variant": getattr(instance, "variant", "base"),
                 "model": model_name, "max_turns": max_turns,
                 "temperature_note": (TEMPERATURE_NOTE_EVAL
                                      if getattr(adapter, "metered", False)
                                      else TEMPERATURE_NOTE),
                 "gate": ("organs" if arm == "weak+aios"
                          else "llm-judge" if arm == "weak+llm-judge" else "none"),
                 "disabled_organs": sorted(disabled_organs or []),
                 "memory_injected": memory_injection["injected"],
                 "memory_stale_suppressed": memory_injection["stale"]})
    if memory_injection["stale"]:
        trace.write({"kind": "memory_stale_suppressed",
                     "detail": memory_injection["detail"]})

    epistemic_gate = None
    if arm == "weak+aios":
        epistemic_gate = make_env_epistemic_gate(env, instance.category, "organs",
                                                 disabled_organs=disabled_organs)
    elif arm == "weak+llm-judge":
        judge_adapter = make_metered_chat_adapter(
            base_url=OLLAMA_BASE_URL,
            model=WEAK_MODEL_EVAL if eval_mode else WEAK_MODEL_DEV,
            meter=meter, source="gate", timeout=30)
        epistemic_gate = make_metered_llm_judge_gate(judge_adapter)

    prompt_prefix = m2_prompts.ARM_PROMPT_PREFIX.get(arm, "") + memory_injection["prefix"]
    tool_vocab = tuple(instance.tool_vocab) if instance.tool_vocab else EPISODE_TOOLS

    gate_blocks: list[dict] = []
    sink = make_turn_sink(trace, env, gate_blocks, extra=extra_sink)
    registry = build_registry(env)
    deadline = (time.monotonic() + float(deadline_s)) if deadline_s else None
    sampler = build_sampler(adapter, env, instance.task_prompt, trace, meter,
                            tool_vocab=tool_vocab, prompt_prefix=prompt_prefix,
                            deadline=deadline, actions_cap=actions_cap)
    goal = f"m2 {instance.template_id} s{instance.seed}: commit the correct final action"

    try:
        outcome = run_loop(goal, sampler, registry,
                           gate=authority_gate_for(tool_vocab),
                           epistemic_gate=epistemic_gate,
                           max_turns=max_turns,
                           turn_sink=sink)
        # Post-episode lesson distillation (prereg §3a STORE step; metered into
        # THIS instance's budget — v1.1 §B counts runtime-internal calls).
        if memory_store is not None and arm in ("weak+memory", "weak+aios"):
            lesson = m2_memory.distill_lesson(adapter, instance.template_id,
                                              instance.task_prompt,
                                              env.final_action, meter, trace)
            if lesson:
                memory_store.store(instance.template_id, lesson,
                                   m2_memory.capture_context_facts(env.known_claims()))
    finally:
        trace.close()

    return {"outcome": outcome, "gate_blocks": gate_blocks, "meter": meter,
            "trace_path": str(trace_path), "memory_injection": memory_injection}
