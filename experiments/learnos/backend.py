"""experiments/learnos/backend.py -- pluggable proposer LLM backend for
LearnOS v0. The harness-improver (improve.py) never talks to a provider
directly; it calls `backend.complete()`.

Default: local ollama qwen3-coder:30b via its OpenAI-compatible endpoint
(http://localhost:11434/v1/chat/completions). Set env AIOS_LEARNOS_BACKEND=nim
to route to NVIDIA NIM instead. The NIM key is read from
~/.config/nvidia/api.env AT CALL TIME ONLY -- never logged, never returned,
never written anywhere by this module.

stdlib only (urllib, json, os).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_NIM_KEY_ENV_FILE = os.path.expanduser("~/.config/nvidia/api.env")
_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
_OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
DEFAULT_OLLAMA_MODEL = "qwen3-coder:30b"
DEFAULT_NIM_MODEL = "openai/gpt-oss-120b"
_DEFAULT_TIMEOUT = 120.0


class ProposerError(Exception):
    """Non-retryable proposer/backend error."""


def _load_nim_key() -> str:
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key
    if os.path.exists(_NIM_KEY_ENV_FILE):
        with open(_NIM_KEY_ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if line.startswith("NVIDIA_API_KEY"):
                    _, _, v = line.partition("=")
                    return v.strip().strip('"').strip("'")
    raise ProposerError(f"NVIDIA_API_KEY not set and not found in {_NIM_KEY_ENV_FILE}")


def backend_name() -> str:
    return os.environ.get("AIOS_LEARNOS_BACKEND", "ollama").strip().lower()


def complete(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    timeout: float = _DEFAULT_TIMEOUT,
) -> str:
    """Call the configured proposer backend; return the raw text completion
    (never raises on empty content -- returns "" so callers always get a
    str)."""
    backend = backend_name()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if backend == "nim":
        key = _load_nim_key()
        model = os.environ.get("AIOS_LEARNOS_NIM_MODEL", DEFAULT_NIM_MODEL)
        url = _NIM_URL
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    elif backend == "ollama":
        model = os.environ.get("AIOS_LEARNOS_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        url = _OLLAMA_URL
        headers = {"Content-Type": "application/json"}
    else:
        raise ProposerError(f"unknown AIOS_LEARNOS_BACKEND={backend!r} (expected 'ollama' or 'nim')")

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise ProposerError(f"HTTP {e.code} from {url}: {detail}") from e
    except (urllib.error.URLError, OSError) as e:
        raise ProposerError(f"network error calling {url}: {e}") from e

    try:
        choice = payload["choices"][0]
        return choice["message"].get("content") or ""
    except (KeyError, IndexError, TypeError) as e:
        raise ProposerError(f"unexpected response shape from {url}: {payload!r}") from e
