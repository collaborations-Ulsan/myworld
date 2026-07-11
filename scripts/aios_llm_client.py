#!/usr/bin/env python3
"""AIOS LLM Client — ONE OpenAI-compatible chat client, local<->NIM failover.

Masterplan §4 M5/D2-4 (docs/AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md):
absorbs nanobot's (HKUDS, MIT) provider-client pattern — an ordered list of
OpenAI-compatible endpoints tried in sequence, so a CLI provider (Claude/Codex)
dying does not take the head down with it. Kept intentionally smaller than
nanobot's async/streaming/circuit-breaker machinery (nanobot/providers/
fallback_provider.py, ~300 lines): this is a synchronous, stdlib-only client —
the shape aios_adapters.py already establishes for every other REST adapter in
this repo (one _http_post_json-style helper, no PyPI dependency).

Failover order (masterplan-specified):
  (a) local ollama  — http://localhost:11434/v1, free, always-on. Model:
      AIOS_OLLAMA_MODEL env (default qwen3-coder:30b — the verified agentic
      model on this box, matches aios_adapters._OLLAMA_REST_MODEL).
  (b) NVIDIA NIM     — https://integrate.api.nvidia.com/v1, needs a key. Model:
      AIOS_NIM_MODEL env (default deepseek-ai/deepseek-v4-pro — matches
      aios_adapters._NVIDIA_NIM_MODEL and is the nvagent-verified tool-calling
      default per ~/.config/nvidia/README.md).

Key handling (the leaked-key incident, CLAUDE.md): the NVIDIA key is read at
CALL TIME from NVIDIA_API_KEY, or sourced from ~/.config/nvidia/api.env if the
env var is unset. It is placed ONLY in the Authorization header. It is never
logged, printed, returned in a ChatResult, or written to any provenance
record — ChatResult.to_provenance() emits provider/model/latency/reason only.

Bounded retries: each endpoint gets at most 2 attempts (1 initial + 1 retry) —
the failover LIST is the retry policy, not per-endpoint looping. A 4xx on a
tools-bearing call is treated as "this endpoint/model doesn't support native
tool-calls" and degrades to one more attempt on the SAME endpoint without
tools, rather than burning the retry budget or failing over needlessly.

Schema: aios.llm_client.v1
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_NIM_ENV_FILE = Path.home() / ".config" / "nvidia" / "api.env"
_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
# nvagent-verified tool-calling default (~/.config/nvidia/README.md, 2026-07-03);
# matches aios_adapters._NVIDIA_NIM_MODEL — one shared convention, not a guess.
_NIM_DEFAULT_MODEL = "deepseek-ai/deepseek-v4-pro"
_OLLAMA_DEFAULT_MODEL = "qwen3-coder:30b"
_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434/v1"


def _read_nvidia_api_key() -> str:
    """Resolve NVIDIA_API_KEY at call time: env first, then ~/.config/nvidia/api.env.

    Never logs, prints, or returns this value anywhere but the caller's
    Authorization header — see the leaked-key incident note above.
    """
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if key:
        return key
    try:
        text = _NIM_ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if line.startswith("NVIDIA_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


@dataclass(frozen=True)
class Endpoint:
    """One OpenAI-compatible chat endpoint to try, in failover order."""
    name: str                                    # provenance label, e.g. "local_ollama"
    base_url: str
    model: str
    needs_key: bool = False
    key_fn: Callable[[], str] = lambda: ""       # resolved at call time, never stored
    timeout: int = 60

    def resolve_key(self) -> str:
        return self.key_fn() if self.needs_key else ""


def default_endpoints() -> list[Endpoint]:
    """(a) local ollama first (free, always-on), (b) NVIDIA NIM second (needs key)."""
    ollama_model = os.environ.get("AIOS_OLLAMA_MODEL", _OLLAMA_DEFAULT_MODEL)
    ollama_base = os.environ.get("AIOS_OLLAMA_BASE_URL", _OLLAMA_DEFAULT_BASE_URL)
    nim_model = os.environ.get("AIOS_NIM_MODEL", _NIM_DEFAULT_MODEL)
    return [
        Endpoint("local_ollama", ollama_base, ollama_model, needs_key=False, timeout=60),
        Endpoint("nvidia_nim", _NIM_BASE_URL, nim_model, needs_key=True,
                 key_fn=_read_nvidia_api_key, timeout=90),
    ]


# Native OpenAI tool-calling support — grounded in verified capability data, not
# guessed (2026-07 absorption survey: qwen3-coder-30b 93-96% well-formed tool
# calls; ~/.config/nvidia/README.md nvagent verification: deepseek-v4-pro /
# llama-3.3-70b / gpt-oss-120b tool-call OK, nemotron-super-49b does NOT).
# Unknown models default to False — conservative, falls back to the JSON-prompt
# sampler, which works on every model.
_TOOL_CAPABLE_MODELS = frozenset({
    "qwen3-coder:30b",
    "deepseek-ai/deepseek-v4-pro",
    "meta/llama-3.3-70b-instruct",
    "openai/gpt-oss-120b",
})


def supports_tools(model: str) -> bool:
    """Best-effort, grounded native-tool-call capability check for a model id."""
    return model in _TOOL_CAPABLE_MODELS


class _HTTPStatusError(Exception):
    """An HTTP error response (as opposed to a transport/timeout failure)."""
    def __init__(self, code: int, message: str):
        super().__init__(f"HTTP {code}: {message}")
        self.code = code


def _post_json(url: str, body: dict, headers: dict, timeout: int) -> dict:
    """Single stdlib HTTP POST + JSON parse — the one transport this module uses."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed OpenAI-compat endpoints
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:  # noqa: BLE001 — best-effort error body read
            pass
        raise _HTTPStatusError(exc.code, detail) from exc


@dataclass
class ChatResult:
    """One chat() outcome. text/tool_calls carry the model's move; the rest is
    provenance (never the prompt/response CONTENT — DNA #7)."""
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    provider_used: str = ""
    model: str = ""
    latency_ms: int = 0
    fallback_reason: "str | None" = None
    ok: bool = True
    error: "str | None" = None

    def to_provenance(self) -> dict:
        """Run-log-safe record: no prompt/response text, no keys — just the
        routing decision (which endpoint answered, how long, why any fallback fired)."""
        return {
            "provider_used": self.provider_used,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "fallback_reason": self.fallback_reason,
            "ok": self.ok,
            "tool_call_count": len(self.tool_calls),
        }


class LLMClient:
    """One OpenAI-compatible chat client, tried across an ordered endpoint list.

    `post` is dependency-injected (default = real HTTP) so this is unit-testable
    with a fake transport — no live network call in tests.
    """

    def __init__(self, endpoints: "list[Endpoint] | None" = None, *,
                 post: "Callable[[str, dict, dict, int], dict] | None" = None):
        self.endpoints = endpoints if endpoints is not None else default_endpoints()
        self._post = post or _post_json

    def primary_supports_tools(self) -> bool:
        """Static, pre-call decision: does the FIRST (preferred) endpoint's
        configured model support native tool-calls? Used by aios_head to choose
        the native sampler vs the JSON-prompt sampler without spending a call."""
        if not self.endpoints:
            return False
        return supports_tools(self.endpoints[0].model)

    def _call_endpoint(self, ep: Endpoint, messages: list[dict],
                       tools: "list[dict] | None", key: str) -> "tuple[ChatResult | None, str]":
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        url = ep.base_url.rstrip("/") + "/chat/completions"

        def attempt(use_tools: bool) -> tuple[dict, int]:
            body: dict[str, Any] = {"model": ep.model, "stream": False, "messages": messages}
            if use_tools and tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"
            t0 = time.monotonic()
            data = self._post(url, body, headers, ep.timeout)
            return data, int((time.monotonic() - t0) * 1000)

        degraded = False
        last_exc: Exception = RuntimeError("no attempt made")
        data: "dict | None" = None
        elapsed = 0
        for _attempt_n in range(2):                       # bounded: 1 initial + 1 retry
            try:
                data, elapsed = attempt(use_tools=bool(tools) and not degraded)
                break
            except _HTTPStatusError as exc:
                last_exc = exc
                if tools and not degraded and exc.code in (400, 404, 422):
                    # graceful degrade: this endpoint/model rejected the `tools`
                    # param — try once more on the SAME endpoint without tools
                    # instead of failing over (the endpoint itself may be fine).
                    degraded = True
                    continue
                continue
            except Exception as exc:  # noqa: BLE001 — transport/timeout failure
                last_exc = exc
                continue
        if data is None:
            return None, f"{ep.name}: {str(last_exc)[:150]}"

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = msg.get("content") or ""
        tool_calls: list[dict] = []
        for tc in (msg.get("tool_calls") or []):
            fn = tc.get("function") or {}
            raw_args = fn.get("arguments")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) and raw_args else (raw_args or {})
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"id": tc.get("id", ""), "name": fn.get("name", ""), "arguments": args})
        note = f"{ep.name}: tools unsupported, degraded to text-only" if degraded else ""
        return ChatResult(text=text, tool_calls=tool_calls, provider_used=ep.name, model=ep.model,
                          latency_ms=elapsed, fallback_reason=note or None, ok=True), note

    def chat(self, messages: list[dict], tools: "list[dict] | None" = None) -> ChatResult:
        """One chat call across the failover list. Never raises — a total
        failure returns ok=False with an honest fallback_reason/error."""
        notes: list[str] = []
        for ep in self.endpoints:
            key = ep.resolve_key()
            if ep.needs_key and not key:
                notes.append(f"{ep.name}: no api key configured")
                continue
            result, note = self._call_endpoint(ep, messages, tools, key)
            if result is not None:
                if notes:                          # honestly record why earlier endpoints were skipped
                    result.fallback_reason = "; ".join(notes)
                elif note:
                    result.fallback_reason = note
                return result
            if note:
                notes.append(note)
        reason = "; ".join(notes) or "no endpoints configured"
        return ChatResult(ok=False, provider_used="", model="", latency_ms=0,
                          fallback_reason=reason, error=reason)


if __name__ == "__main__":
    import sys
    goal = " ".join(sys.argv[1:]) or "say hello in one short sentence"
    client = LLMClient()
    res = client.chat([{"role": "user", "content": goal}])
    print(json.dumps({"text": res.text, **res.to_provenance()}, ensure_ascii=False, indent=2))
