"""Unified frozen-model client for the AGI certification-layer witness experiment.

Why this exists (see README.md): arms A/B/C compete at a FIXED TOTAL TOKEN BUDGET, and
ablations (R2-R7) rerun IDENTICAL prompts against the same models. Two needs fall out of
that:
  1. One routing surface for both providers in play (NIM frontier pool, local ollama) so
     arms.py / certs don't special-case transport.
  2. A persistent, content-addressed response cache so reruns are fast and byte-identical
     -- but the cache must NEVER let a cache hit look cheaper than a cache miss, or the
     budget accounting (the whole point of the metric) would be gamed. A cache hit
     replays the ORIGINAL prompt_tokens/completion_tokens recorded on first call; only
     wall-clock latency and API cost are saved, not budget.

Stdlib only (urllib, json, hashlib, os) -- no external deps, per RESOURCES.md constraints
(CPU-only box, frozen models, no training).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request

# ---- paths -------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "data")
_CACHE_PATH = os.path.join(_DATA_DIR, "llm_cache.jsonl")
_NIM_KEY_ENV_FILE = os.path.expanduser("~/.config/nvidia/api.env")

_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
_OLLAMA_URL = "http://localhost:11434/api/chat"

_DEFAULT_TIMEOUT = 90.0
_MAX_RETRIES = 3


# ---- errors --------------------------------------------------------------
class BudgetExhausted(Exception):
    """Raised by TokenBudget.spend() when a spend would exceed the total budget."""


class LLMError(Exception):
    """Non-retryable provider error (e.g. HTTP 4xx, unknown model prefix)."""


# ---- token budget ----------------------------------------------------------
class TokenBudget:
    """Tracks a fixed total token budget shared across an arm's whole run.

    Deliberately dumb: no wall-clock, no provider awareness. Callers add
    prompt_tokens + completion_tokens from each `complete()` result (cached or not --
    see module docstring) via `.spend()`.
    """

    def __init__(self, total: int):
        self.total = total
        self._spent = 0

    def spend(self, n: int) -> None:
        if n < 0:
            raise ValueError("cannot spend a negative token count")
        if self._spent + n > self.total:
            raise BudgetExhausted(
                f"spend({n}) would exceed budget: spent={self._spent} total={self.total}"
            )
        self._spent += n

    def remaining(self) -> int:
        return self.total - self._spent

    def spent(self) -> int:
        return self._spent


# ---- token estimation (fallback when provider omits `usage`) ----------------
def _estimate_tokens(text: str) -> int:
    """Whitespace/4-char heuristic. Used only when a provider's usage field is absent
    (ollama commonly omits it). Not exact -- callers get `estimated=True` alongside it."""
    if not text:
        return 0
    by_words = len(text.split())
    by_chars = max(1, len(text) // 4)
    # average the two cheap heuristics; good enough for budget bookkeeping, not billing.
    return max(1, (by_words + by_chars) // 2)


# ---- NIM API key -------------------------------------------------------------
def _load_nim_key() -> str:
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key
    if os.path.exists(_NIM_KEY_ENV_FILE):
        with open(_NIM_KEY_ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if line.startswith("NVIDIA_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise LLMError(
        f"NVIDIA_API_KEY not set and not found in {_NIM_KEY_ENV_FILE}"
    )


# ---- cache -------------------------------------------------------------------
def _cache_key(model: str, system: str | None, prompt: str, seed: int, temp: float, max_tokens: int) -> str:
    """sha256 over the exact call shape. No wall-clock, no randomness -- deterministic
    across processes/days so reruns of ablations hit the same cache."""
    payload = json.dumps(
        {
            "model": model,
            "system": system,
            "prompt": prompt,
            "seed": seed,
            "temp": temp,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_load(key: str) -> dict | None:
    if not os.path.exists(_CACHE_PATH):
        return None
    # Linear scan of an append-only jsonl. Fine at this experiment's scale (~100 tasks x
    # k=6 samples x few arms); switch to an index if it ever gets big.
    with open(_CACHE_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("key") == key:
                return rec
    return None


def _cache_append(key: str, entry: dict) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    rec = {"key": key, **entry}
    with open(_CACHE_PATH, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


# ---- HTTP with retry ----------------------------------------------------------
def _post_json(url: str, headers: dict, body: dict, timeout: float) -> dict:
    """POST JSON with 3 retries + exponential backoff on 429/5xx/timeout. 4xx raises
    immediately with a clear error (not retryable -- bad request/auth won't fix itself).
    NIM big models can cold-start slow, hence the generous default timeout."""
    data = json.dumps(body).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if e.code == 429 or 500 <= e.code < 600:
                last_err = LLMError(f"HTTP {e.code} from {url}: {body_text[:500]}")
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise last_err
            # 4xx (other than 429): not retryable, fail clearly.
            raise LLMError(f"HTTP {e.code} (non-retryable) from {url}: {body_text[:500]}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = LLMError(f"network/timeout error from {url}: {e}")
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise last_err
    # unreachable, but keeps type-checkers happy
    raise last_err or LLMError(f"unknown failure calling {url}")


# ---- provider calls ------------------------------------------------------------
def _call_nim(model_id: str, prompt: str, seed: int, temp: float, max_tokens: int, system: str | None, timeout: float) -> dict:
    key = _load_nim_key()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model_id,
        "messages": messages,
        "temperature": temp,
        "max_tokens": max_tokens,
        "seed": seed,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = _post_json(_NIM_URL, headers, body, timeout)
    choice = resp["choices"][0]
    # Reasoning models (e.g. gpt-oss-120b) can return content=None if max_tokens is
    # exhausted by the hidden reasoning trace before the final answer is emitted
    # (finish_reason="length" with reasoning_content populated but content null).
    # Normalize to "" so callers always get a str, never None.
    text = choice["message"].get("content") or ""
    usage = resp.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    estimated = prompt_tokens is None or completion_tokens is None
    if prompt_tokens is None:
        prompt_tokens = _estimate_tokens((system or "") + prompt)
    if completion_tokens is None:
        completion_tokens = _estimate_tokens(text)
    return {
        "text": text,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "estimated": estimated,
    }


def _call_ollama(model_name: str, prompt: str, seed: int, temp: float, max_tokens: int, system: str | None, timeout: float) -> dict:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temp,
            "seed": seed,
            "num_predict": max_tokens,
        },
    }
    headers = {"Content-Type": "application/json"}
    resp = _post_json(_OLLAMA_URL, headers, body, timeout)
    text = resp.get("message", {}).get("content", "")
    # ollama often reports prompt_eval_count / eval_count; fall back to estimate if absent.
    prompt_tokens = resp.get("prompt_eval_count")
    completion_tokens = resp.get("eval_count")
    estimated = prompt_tokens is None or completion_tokens is None
    if prompt_tokens is None:
        prompt_tokens = _estimate_tokens((system or "") + prompt)
    if completion_tokens is None:
        completion_tokens = _estimate_tokens(text)
    return {
        "text": text,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "estimated": estimated,
    }


# ---- public API ----------------------------------------------------------------
def complete(
    model: str,
    prompt: str,
    *,
    seed: int = 0,
    temp: float = 0.0,
    max_tokens: int = 1024,
    system: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict:
    """Route + call a frozen model, transparently cached.

    `model` is prefix-routed:
      "nim:<org/id>"    -> NVIDIA NIM chat completions (e.g. "nim:openai/gpt-oss-120b")
      "ollama:<name>"   -> local ollama chat (e.g. "ollama:qwen2.5-coder:7b")

    Returns {"text", "prompt_tokens", "completion_tokens", "cached", "model"}.

    Cache contract (see module docstring): on a cache hit, prompt_tokens/completion_tokens
    are the ORIGINAL counts from the first (uncached) call -- budget accounting is
    identical whether the arm reruns a prompt or not. The cache buys reproducibility and
    speed, never a budget discount.
    """
    if ":" not in model:
        raise LLMError(f"model must be prefixed with 'nim:' or 'ollama:', got: {model!r}")
    prefix, _, model_id = model.partition(":")

    key = _cache_key(model, system, prompt, seed, temp, max_tokens)
    hit = _cache_load(key)
    if hit is not None:
        return {
            "text": hit["text"],
            "prompt_tokens": hit["prompt_tokens"],
            "completion_tokens": hit["completion_tokens"],
            "cached": True,
            "model": model,
        }

    if prefix == "nim":
        result = _call_nim(model_id, prompt, seed, temp, max_tokens, system, timeout)
    elif prefix == "ollama":
        result = _call_ollama(model_id, prompt, seed, temp, max_tokens, system, timeout)
    else:
        raise LLMError(f"unknown model prefix {prefix!r} (expected 'nim' or 'ollama')")

    _cache_append(
        key,
        {
            "text": result["text"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "model": model,
        },
    )
    return {
        "text": result["text"],
        "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
        "cached": False,
        "model": model,
    }


# ---- self-test -----------------------------------------------------------------
if __name__ == "__main__":
    # NOTE on max_tokens: openai/gpt-oss-120b on NIM is a reasoning model -- it spends
    # completion tokens on a hidden reasoning trace (message.reasoning_content) BEFORE
    # emitting the final message.content. Empirically verified: at max_tokens=8 (and
    # even 64), the budget is entirely consumed by reasoning, finish_reason="length",
    # and content=null. 300 tokens is enough headroom for this trivial prompt to reach
    # finish_reason="stop" with real content. This is a provider/model quirk, not a
    # client bug -- _call_nim() normalizes content=None to "" either way (see above).
    print("=== complete() first call (uncached) ===")
    r1 = complete("nim:openai/gpt-oss-120b", "Reply with exactly: OK", max_tokens=300)
    print(f"text={r1['text']!r} prompt_tokens={r1['prompt_tokens']} "
          f"completion_tokens={r1['completion_tokens']} cached={r1['cached']} model={r1['model']}")
    assert r1["cached"] is False, "first call should be a cache miss"

    print("\n=== complete() second call (should hit cache) ===")
    r2 = complete("nim:openai/gpt-oss-120b", "Reply with exactly: OK", max_tokens=300)
    print(f"text={r2['text']!r} prompt_tokens={r2['prompt_tokens']} "
          f"completion_tokens={r2['completion_tokens']} cached={r2['cached']} model={r2['model']}")
    assert r2["cached"] is True, "second identical call should hit cache"
    assert r2["text"] == r1["text"], "cached text must match original"
    assert r2["prompt_tokens"] == r1["prompt_tokens"], "cached prompt_tokens must match original (no budget discount)"
    assert r2["completion_tokens"] == r1["completion_tokens"], "cached completion_tokens must match original"
    print("PASS: cache hit returns identical text + identical (non-discounted) token counts")

    print("\n=== TokenBudget behavior ===")
    budget = TokenBudget(total=100)
    budget.spend(30)
    print(f"spent={budget.spent()} remaining={budget.remaining()}")
    budget.spend(50)
    print(f"spent={budget.spent()} remaining={budget.remaining()}")
    try:
        budget.spend(30)  # 80 + 30 = 110 > 100 -> should raise
        print("FAIL: expected BudgetExhausted")
    except BudgetExhausted as e:
        print(f"PASS: BudgetExhausted raised as expected: {e}")

    print("\nALL SELF-TESTS PASSED")
