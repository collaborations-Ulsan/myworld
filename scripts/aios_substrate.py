#!/usr/bin/env python3
"""aios.substrate.v1 — one call interface over local models, APIs, and (last) CLIs.

Founder's target: weave ever-improving local LLMs, coders and APIs dynamically, and beat
Claude Code / Codex. Three things that target implies, each of which is a constraint here.

1. THE CLAIM MUST BE HARNESS-vs-HARNESS. We do not train models, so "beat Claude Code"
   can only honestly mean: same model, better harness. That is measurable and the number
   is known — harness is worth 10-15pp on a fixed model (LangChain Deep Agents Code took
   GPT-5.2-Codex from 52.8 to 66.5 on Terminal-Bench 2.0), and Terminal-Bench 2.1 is
   reported to measure the harness at least as much as the model. Current bar:
   Codex CLI 89.5, Claude Code 89.1 (grounded 2026-08-18).

2. DIRECT CALLS, NOT SHELLED-OUT CLIs. Measured in one session: the CLI/web panel
   answered 10 of 20; direct HTTP to a local model had zero dead calls. A CLI returns an
   exit code; a direct call returns seed, tokens, latency and body — which is the
   difference between a result you can replay and one you can only re-run and hope.
   CLIs stay, but as an adapter of last resort, flagged unobservable, and each one must
   name the direct substitute that would replace it.

3. DYNAMIC ROUTING IS NOT ASSUMED TO PAY. Our own measurement (A1/MCF-0) had a FROZEN
   router beat adaptive persistent state. So the adaptive router is deliberately not
   implemented here. The static capability table is the baseline an adaptive router must
   beat, exactly as arm B is in the M2 prereg. Build the table, measure, then earn the
   loop.
"""
from __future__ import annotations
import json, os, subprocess, time, urllib.request, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECEIPTS = ROOT / ".aios" / "substrate_receipts.jsonl"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Benchmarks carry their source and date because they expire. A number without a date is
# a claim about today made from stale weights, which is the failure this file exists to avoid.
GROUNDED = "2026-08-18 (WebSearch: SWE-bench Verified / Terminal-Bench 2.1 leaderboards)"

REGISTRY: dict[str, dict] = {
    # id                transport   observable  swe_v  term_b  notes
    "qwen3-coder-next": dict(transport="ollama", observable=True, swe_verified=70.6,
                             local=True, vram_gb=None, note="current local default"),
    "qwen3-coder:30b":  dict(transport="ollama", observable=True, swe_verified=None,
                             local=True, note="agentic tool-use verified locally"),
    # --- grounded as better than what we run; not installed yet, so marked candidate ---
    "qwen3.6-27b":      dict(transport="ollama", observable=True, swe_verified=77.2,
                             local=True, vram_gb=22, candidate=True,
                             note="fits one 5090; we have two"),
    "glm-5.2":          dict(transport="api", observable=True, terminal_bench=81.0,
                             candidate=True, note="strongest open-weight agentic/terminal"),
    "deepseek-v4-pro-max": dict(transport="api", observable=True, swe_verified=80.6,
                                candidate=True, note="highest open-weight SWE-bench V"),
    # --- unobservable adapters: kept only where no API exists ---
    "chatgpt-web":      dict(transport="cli", observable=False,
                             substitute="openai api", note="per-request signed anti-bot tokens"),
    "grok-web":         dict(transport="cli", observable=False,
                             substitute="xai api", note="live X data, no API replay"),
    "codex-cli":        dict(transport="cli", observable=False,
                             substitute="openai responses api",
                             note="carries its own agent loop; that is what we are replacing"),
}

# The static baseline an adaptive router has to beat. Deliberately dumb and written down.
STATIC_ROUTE = {
    "code_edit":     "qwen3-coder-next",
    "tool_use":      "qwen3-coder:30b",
    "short_extract": "qwen3-coder-next",
    "adversarial":   "chatgpt-web",      # divergence needs different weights, not a fork
}


def _receipt(**kw) -> None:
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a") as fh:
        fh.write(json.dumps(kw, ensure_ascii=False) + "\n")


def call(model: str, prompt: str, *, system: str = "", temperature: float = 0.0,
         seed: int | None = None, max_tokens: int = 512, timeout: int = 180) -> dict:
    """One shape for every substrate. Always returns; never raises for a provider fault.

    A failed call is recorded as a failure, never as an empty success — a substrate that
    timed out looks exactly like one that thought hard and had nothing to say.
    """
    spec = REGISTRY.get(model)
    if spec is None:
        return {"ok": False, "error": f"unknown model {model!r}", "text": ""}
    if spec.get("candidate"):
        return {"ok": False, "error": f"{model} is a grounded candidate, not installed",
                "text": "", "grounded": GROUNDED}
    rid = uuid.uuid4().hex[:12]
    t0 = time.time()
    out: dict = {"ok": False, "text": "", "error": ""}

    if spec["transport"] == "ollama":
        body = {"model": model, "prompt": prompt, "system": system, "stream": False,
                "think": False,
                "options": {"temperature": temperature, "num_predict": max_tokens}}
        if seed is not None:
            body["options"]["seed"] = seed
        try:
            req = urllib.request.Request(f"{OLLAMA}/api/generate",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            out = {"ok": True, "text": (d.get("response") or d.get("thinking") or "").strip(),
                   "eval_count": d.get("eval_count"),
                   "prompt_eval_count": d.get("prompt_eval_count"), "error": ""}
        except Exception as e:
            out = {"ok": False, "text": "", "error": f"{type(e).__name__}: {e}"[:300]}

    elif spec["transport"] == "cli":
        # last resort. The receipt says so, so no downstream analysis can mistake this
        # for a replayable call.
        hub = Path.home() / "workspaces" / "jaewon" / "council" / "hub.py"
        try:
            p = subprocess.run(["python3", str(hub), "ask", model, prompt],
                               capture_output=True, text=True, timeout=timeout)
            txt = ""
            try:
                txt = (json.loads(p.stdout).get("text") or "").strip()
            except Exception:
                txt = p.stdout.strip()
            out = {"ok": bool(txt), "text": txt,
                   "error": "" if txt else (p.stderr or "empty")[:300]}
        except Exception as e:
            out = {"ok": False, "text": "", "error": f"{type(e).__name__}: {e}"[:300]}
    else:
        out = {"ok": False, "text": "", "error": f"transport {spec['transport']} not wired"}

    out |= {"model": model, "rid": rid, "ms": int((time.time() - t0) * 1000),
            "observable": spec["observable"], "seed": seed}
    _receipt(rid=rid, ts=time.time(), model=model, ok=out["ok"], ms=out["ms"],
             observable=spec["observable"], seed=seed, temperature=temperature,
             chars=len(out["text"]), error=out["error"][:200])
    return out


def route(task_class: str) -> str:
    """The STATIC baseline. There is no adaptive path on purpose — see module docstring."""
    return STATIC_ROUTE.get(task_class, "qwen3-coder-next")


def stack_report() -> str:
    lines = [f"grounded {GROUNDED}", ""]
    for m, s in REGISTRY.items():
        flag = ("CANDIDATE" if s.get("candidate") else
                ("live" if s["observable"] else "UNOBSERVABLE"))
        score = s.get("swe_verified") or s.get("terminal_bench")
        lines.append(f"  {m:<22}{flag:<12}{'' if score is None else score:>6}  {s.get('note','')}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        print(stack_report()); raise SystemExit(0)
    r = call(route("short_extract"), "Reply with exactly one word: OK", seed=1, max_tokens=8)
    print(json.dumps(r, ensure_ascii=False))
