#!/usr/bin/env python3
"""AIOS Structural Stream Weaver & Unconstrained Multi-Model Injection Engine.

(aios.stream_weaver.v1)

Weaves heterogeneous streams across:
1. Chatbot Responses (ChatGPT Pro, Claude.ai, Perplexity, DeepSeek-Web from council/hub.py)
2. CLI Agent Executions (Codex CLI, Claude Code, Agy/Gemini CLI)
3. Direct Raw APIs (NVIDIA NIM API, Ollama Qwen/DeepSeek, OpenRouter)

Features:
- Prompt-Prison Cleansing: Strips sycophantic boilerplate, hedges, and disclaimers.
- Structural Extraction: Extracts Code ASTs, Invariants, Assumptions, Falsifiers, and <think> traces.
- Cross-Model Context Injection: Injects raw reasoning from one model directly into the prompt/graph slot of another.
- Unconstrained Execution: Bypasses single-vendor rate/safety cage constraints to achieve true multi-agent autonomy.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
COUNCIL_HUB = Path.home() / "workspaces" / "jaewon" / "council" / "hub.py"
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

try:
    from aios_hetero_council import HeteroCouncil, SubstrateClient
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from aios_hetero_council import HeteroCouncil, SubstrateClient


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 1. Structural Stream Extraction & Prompt-Prison Cleaner
# ---------------------------------------------------------------------------

@dataclass
class StructuredOutput:
    raw_text: str
    cleaned_text: str
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    think_trace: Optional[str] = None
    invariants: List[str] = field(default_factory=list)
    falsifiers: List[str] = field(default_factory=list)
    confidence: float = 1.0
    source_substrate: str = "unknown"
    source_kind: str = "api"  # "chatbot_web", "cli_agent", "raw_api", "mock"
    latency_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PromptPrisonCleaner:
    """Strips conversational fluff, apologies, disclaimers, and boilerplate cages."""

    BOILERPLATE_PATTERNS = [
        r"^(?:Certainly!|Sure!|Of course!|I'd be happy to help|As an AI|I understand you want).*?[\n\r]+",
        r"(?:Please note that|Keep in mind that|It is important to remember|I hope this helps).*?$",
        r"^(?:Here is the (?:code|implementation|solution|answer):)[\n\r]+",
        r"(?:Let me know if you need (?:further assistance|anything else)).*?$",
    ]

    @classmethod
    def clean(cls, text: str) -> str:
        s = text.strip()
        # Remove think blocks if embedded (or extract them separately)
        s_no_think = re.sub(r"<think>.*?</think>", "", s, flags=re.DOTALL).strip()
        cleaned = s_no_think
        for pat in cls.BOILERPLATE_PATTERNS:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        return cleaned or s_no_think

    @classmethod
    def extract_think_trace(cls, text: str) -> Optional[str]:
        m = re.search(r"<think>(.*?)</think>", text, flags=re.DOTALL)
        return m.group(1).strip() if m else None

    @classmethod
    def extract_code_blocks(cls, text: str) -> List[Dict[str, str]]:
        pattern = r"```([a-zA-Z0-9_-]*)\n(.*?)```"
        matches = re.findall(pattern, text, flags=re.DOTALL)
        blocks = []
        for lang, code in matches:
            blocks.append({
                "lang": lang.strip() or "text",
                "code": code.strip(),
            })
        return blocks

    @classmethod
    def extract_invariants_and_falsifiers(cls, text: str) -> Tuple[List[str], List[str]]:
        invariants = []
        falsifiers = []
        for line in text.splitlines():
            line_str = line.strip().lstrip("-*#0123456789. ")
            if re.search(r"\b(invariant|constraint|must|guarantee|require)\b", line_str, re.I):
                invariants.append(line_str)
            if re.search(r"\b(falsif|fail if|bottleneck|risk|vulnerab|edge case)\b", line_str, re.I):
                falsifiers.append(line_str)
        return invariants, falsifiers

    @classmethod
    def parse_structure(cls, raw_text: str, substrate: str, kind: str, latency_s: float = 0.0) -> StructuredOutput:
        cleaned = cls.clean(raw_text)
        think = cls.extract_think_trace(raw_text)
        code_blocks = cls.extract_code_blocks(raw_text)
        invariants, falsifiers = cls.extract_invariants_and_falsifiers(cleaned)

        return StructuredOutput(
            raw_text=raw_text,
            cleaned_text=cleaned,
            code_blocks=code_blocks,
            think_trace=think,
            invariants=invariants,
            falsifiers=falsifiers,
            source_substrate=substrate,
            source_kind=kind,
            latency_s=round(latency_s, 3),
        )


# ---------------------------------------------------------------------------
# 2. Multi-Source Harvester (Chatbot Web, CLI Agent, Raw API)
# ---------------------------------------------------------------------------

class MultiSourceHarvester:
    """Dispatches queries to Chatbots, CLI agents, and Raw APIs simultaneously."""

    def __init__(self, timeout: float = 45.0):
        self.timeout = timeout
        self.client = SubstrateClient(timeout=timeout)

    def query_council_hub(self, substrate: str, prompt: str) -> StructuredOutput:
        """Query external chatbot or CLI via council/hub.py if available."""
        t0 = time.time()
        if COUNCIL_HUB.exists():
            cmd = [sys.executable, str(COUNCIL_HUB), "ask", substrate, prompt, "--timeout", str(int(self.timeout))]
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
                out = (p.stdout or "").strip()
                # Parse JSON if hub returns JSON
                if out.startswith("{"):
                    try:
                        data = json.loads(out)
                        text = data.get("text", "")
                        return PromptPrisonCleaner.parse_structure(text, substrate, "chatbot_web", time.time() - t0)
                    except json.JSONDecodeError:
                        pass
                return PromptPrisonCleaner.parse_structure(out, substrate, "chatbot_web", time.time() - t0)
            except Exception as exc:
                err_text = f"[Council Hub Error on {substrate}: {str(exc)}]"
                return PromptPrisonCleaner.parse_structure(err_text, substrate, "chatbot_web", time.time() - t0)

        # Fallback to direct client
        res = self.client.query_substrate({"provider": "mock", "model": substrate}, prompt)
        return PromptPrisonCleaner.parse_structure(res.get("text", ""), substrate, "mock", time.time() - t0)

    def query_cli_agent(self, agent_cmd: str, prompt: str) -> StructuredOutput:
        """Query a local CLI agent (e.g. codex exec, agy -p, claude)."""
        t0 = time.time()
        full_cmd = f"{agent_cmd} {json.dumps(prompt)}"
        try:
            p = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=self.timeout)
            out = (p.stdout + "\n" + p.stderr).strip()
            return PromptPrisonCleaner.parse_structure(out, agent_cmd, "cli_agent", time.time() - t0)
        except Exception as exc:
            # Fallback mock
            mock_res = f"[{agent_cmd} Mock Worker] Executed prompt: {prompt[:50]}..."
            return PromptPrisonCleaner.parse_structure(mock_res, agent_cmd, "cli_agent", time.time() - t0)

    def query_raw_api(self, substrate_dict: Dict[str, Any], prompt: str, system: Optional[str] = None) -> StructuredOutput:
        """Query raw API backend (NVIDIA NIM or Ollama)."""
        t0 = time.time()
        res = self.client.query_substrate(substrate_dict, prompt, system)
        return PromptPrisonCleaner.parse_structure(
            res.get("text", ""),
            substrate_dict.get("id", substrate_dict.get("model", "api")),
            "raw_api",
            time.time() - t0,
        )


# ---------------------------------------------------------------------------
# 3. Cross-Stream Injection & Weaving Pipeline
# ---------------------------------------------------------------------------

class StreamWeaver:
    """Orchestrates multi-model structural injection pipelines."""

    def __init__(self, timeout: float = 30.0):
        self.harvester = MultiSourceHarvester(timeout=timeout)

    def weave_ideation_to_code(
        self,
        goal: str,
        reasoning_sub: str = "deepseek-nim",
        coder_sub: str = "qwen-coder-local",
        critic_sub: str = "llama-nim",
    ) -> Dict[str, Any]:
        """Deep collaborative multi-model pipeline:

        1. Reasoner derives architecture, invariants, and edge cases.
        2. Cleaned invariants & thinking are STRUCTURALLY INJECTED into Coder prompt.
        3. Coder generates clean, uncompromising implementation.
        4. Critic stress-tests the code for race conditions and defects.
        """
        t_start = time.time()
        trail = []

        # Step 1: Raw Reasoning & Deep Architecture Derivation
        print(f"🌀 [1/3] Querying Reasoning Substrate [{reasoning_sub}] for deep architecture...")
        reason_prompt = (
            f"Goal: {goal}\n\n"
            "Provide deep technical reasoning. Specifically identify:\n"
            "1. Core Invariants (MUST NOT VIOLATE)\n"
            "2. Potential race conditions / edge cases (Falsifiers)\n"
            "3. Precise implementation blueprint."
        )
        reason_out = self.harvester.query_raw_api(
            {"provider": "nim", "model": "deepseek-ai/deepseek-v4-flash-0731", "id": reasoning_sub},
            reason_prompt,
            "You are the unconstrained Chief Reasoning Engine."
        )
        trail.append({"step": "reasoning", "substrate": reasoning_sub, "output": reason_out.to_dict()})

        # Step 2: Structural Injection into Coder
        print(f"🧬 [2/3] Structurally Injecting Invariants into Coder [{coder_sub}]...")
        injected_invariants = "\n".join(f"- {inv}" for inv in reason_out.invariants[:5]) or "- Strict type contracts"
        injected_falsifiers = "\n".join(f"- {f}" for f in reason_out.falsifiers[:5]) or "- Handle edge inputs"

        coder_prompt = (
            f"Goal: {goal}\n\n"
            f"=== STRUCTURAL INVARIANTS (From Chief Reasoner) ===\n"
            f"{injected_invariants}\n\n"
            f"=== KNOWN VULNERABILITIES & EDGE CASES ===\n"
            f"{injected_falsifiers}\n\n"
            f"=== BLUEPRINT ===\n"
            f"{reason_out.cleaned_text[:600]}\n\n"
            "Write the complete, uncompromising production-grade Python code. "
            "No stubs, no placeholders, full type annotations."
        )

        coder_out = self.harvester.query_raw_api(
            {"provider": "ollama", "model": "qwen3-coder:30b", "id": coder_sub},
            coder_prompt,
            "You are the Core Implementation Specialist. Write robust, clean code directly."
        )
        trail.append({"step": "coding", "substrate": coder_sub, "output": coder_out.to_dict()})

        # Step 3: Adversarial Verification & Red-Teaming
        print(f"⚔️ [3/3] Cross-Critique via Adversarial Reflector [{critic_sub}]...")
        primary_code = coder_out.code_blocks[0]["code"] if coder_out.code_blocks else coder_out.cleaned_text
        critic_prompt = (
            f"Goal: {goal}\n\n"
            f"Implementation Code:\n```python\n{primary_code}\n```\n\n"
            f"Check if any of these invariants were violated:\n{injected_invariants}\n\n"
            "Output your verdict: [PASS] or [FAIL: explanation]."
        )

        critic_out = self.harvester.query_raw_api(
            {"provider": "nim", "model": "meta/llama-3.1-8b-instruct", "id": critic_sub},
            critic_prompt,
            "You are an adversarial red-team auditor. Be uncompromising."
        )
        trail.append({"step": "critique", "substrate": critic_sub, "output": critic_out.to_dict()})

        total_latency = round(time.time() - t_start, 3)

        return {
            "schema": "aios.stream_weaver.v1",
            "goal": goal,
            "total_latency_s": total_latency,
            "injected_invariants": reason_out.invariants,
            "injected_falsifiers": reason_out.falsifiers,
            "generated_code": primary_code,
            "critic_verdict": critic_out.cleaned_text,
            "pipeline_trail": trail,
        }

    def parallel_hetero_harvest(self, prompt: str, substrates: List[Dict[str, Any]]) -> List[StructuredOutput]:
        """Harvest responses across all heterogeneous sources concurrently."""
        results = []
        with cf.ThreadPoolExecutor(max_workers=len(substrates)) as executor:
            futures = {
                executor.submit(self.harvester.query_raw_api, sub, prompt): sub
                for sub in substrates
            }
            for fut in cf.as_completed(futures):
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as exc:
                    sub = futures[fut]
                    results.append(StructuredOutput(
                        raw_text=f"Error: {exc}",
                        cleaned_text="",
                        source_substrate=sub.get("id", "unknown"),
                    ))
        return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--goal", required=True, help="Goal/Task to weave across multi-model streams")
    p.add_argument("--json", action="store_true", help="Output full JSON pipeline record")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    weaver = StreamWeaver()
    print(f"🚀 Starting Unconstrained Multi-Model Stream Weaving for: '{args.goal}'\n")

    res = weaver.weave_ideation_to_code(args.goal)

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 75)
        print("🎯 WEAVING PIPELINE RESULTS")
        print(f"⏱️ Total Latency: {res['total_latency_s']}s")
        print(f"🛡️ Injected Invariants: {len(res['injected_invariants'])} found")
        print("=" * 75)
        print("\n📜 Generated Production Code:\n")
        print(res["generated_code"])
        print("\n🔍 Critic Verdict:\n")
        print(res["critic_verdict"])
        print("\n" + "=" * 75)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
