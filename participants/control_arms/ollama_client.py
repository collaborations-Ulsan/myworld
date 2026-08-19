"""Fixed-model client for the control arms (M2/M3), built to contract §2.

  primary    qwen3.8:27b       http://localhost:11434/api/generate  (2-token direct answers)
  gate3 alt  muse-glimmer:30b  same endpoint  (THINKING model: `response` empty,
             content lands in `thinking`, ~147 tokens even for a one-word answer,
             not disabled by think:false -> read BOTH fields)

temperature is fixed 0; seed is a deterministic hash of qid; cost is reported as
the REAL counts ollama bills (prompt_eval_count / eval_count) — no synthetic
prompt-cache discount, because overclaiming B's efficiency would unfairly
handicap arm C. Stdlib only (urllib); no third-party deps, no GPU on this side.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request

DEFAULT_HOST = "http://localhost:11434"
PRIMARY_MODEL = "qwen3.8:27b"
GATE3_MODEL = "muse-glimmer:30b"


def qid_seed(qid: str) -> int:
    """Deterministic per-qid seed so a run is reproducible (contract §2)."""
    return int(hashlib.sha256(qid.encode()).hexdigest()[:8], 16)


def parse_ollama_response(body: dict) -> dict:
    """Extract answer + real token counts from an /api/generate reply.

    Handles thinking models: the user-facing answer is `response` when present,
    otherwise falls back to `thinking` (muse-glimmer). Both raw fields are kept
    for audit so a caller can see when a 'blank' answer was actually reasoning.
    """
    response = (body.get("response") or "").strip()
    thinking = (body.get("thinking") or "").strip()
    answer = response if response else thinking
    return {
        "answer": answer,
        "response_raw": response,
        "thinking_raw": thinking,
        "answer_from": "response" if response else ("thinking" if thinking else "empty"),
        "prompt_tokens": int(body.get("prompt_eval_count", 0)),
        "completion_tokens": int(body.get("eval_count", 0)),
    }


def generate(prompt: str, qid: str, model: str = PRIMARY_MODEL,
             num_predict: int = 256, host: str = DEFAULT_HOST, timeout: float = 300.0) -> dict:
    """One fixed-model call. Returns parsed answer + real cost (incl. wall_ms).

    Not unit-tested against a live endpoint from this side (the model runs on the
    harness host); `parse_ollama_response` carries the tested logic.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "seed": qid_seed(qid), "num_predict": num_predict},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode())
    wall_ms = int((time.perf_counter() - t0) * 1000)
    out = parse_ollama_response(body)
    out["wall_ms"] = wall_ms
    out["model"] = model
    return out


# --- parsing self-test (no network) -------------------------------------- #
if __name__ == "__main__":
    direct = parse_ollama_response(
        {"response": "42", "prompt_eval_count": 30, "eval_count": 2})
    assert direct["answer"] == "42" and direct["answer_from"] == "response"
    assert direct["prompt_tokens"] == 30 and direct["completion_tokens"] == 2

    thinky = parse_ollama_response(
        {"response": "", "thinking": "the answer is docs", "eval_count": 147})
    assert thinky["answer"] == "the answer is docs", thinky
    assert thinky["answer_from"] == "thinking", thinky
    assert thinky["completion_tokens"] == 147

    empty = parse_ollama_response({"response": "", "thinking": ""})
    assert empty["answer"] == "" and empty["answer_from"] == "empty"

    # determinism of the seed
    assert qid_seed("q123") == qid_seed("q123")
    print("ok  parse_ollama_response + qid_seed  (thinking-field gotcha covered)")
