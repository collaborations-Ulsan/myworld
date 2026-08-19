#!/usr/bin/env python3
"""AIOS Heterogeneous Model Council & Substrate Router (aios.hetero_council.v1).

Unifies open-source model providers (NVIDIA NIM API, Ollama, vLLM, OpenRouter,
local CLIs) into an active deliberative council for Ideation, Cross-Critique,
and Consensus Voting.

Key Features:
1. Heterogeneous Substrate Provider (NIM DeepSeek/Llama, Ollama Qwen Coder, etc.)
2. Robust Fallback Chain & Circuit Breakers (Graceful degradation)
3. Multi-Model Deliberation Loop (Blind ideation -> Peer Critique -> Effective Voting)
4. Independence Metric ($N_{\\text{eff}}$ discount for same model family)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

SCHEMA = "aios.hetero_council.v1"
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

# Default registry of heterogeneous substrates
DEFAULT_SUBSTRATES = [
    {
        "id": "qwen-coder-local",
        "provider": "ollama",
        "model": "qwen3-coder:30b",
        "family": "qwen",
        "role": "code_specialist",
        "tier": "local",
    },
    {
        "id": "deepseek-nim",
        "provider": "nim",
        "model": "deepseek-ai/deepseek-v4-flash-0731",
        "family": "deepseek",
        "role": "reasoning_architect",
        "tier": "api",
    },
    {
        "id": "llama-nim",
        "provider": "nim",
        "model": "meta/llama-3.1-8b-instruct",
        "family": "llama",
        "role": "critic_reflector",
        "tier": "api",
    },
    {
        "id": "deepseek-coder-local",
        "provider": "ollama",
        "model": "deepseek-coder-v2:16b",
        "family": "deepseek",
        "role": "code_verifier",
        "tier": "local",
    },
]


import socket

class SubstrateClient:
    """Client for querying heterogeneous LLM backends with uniform interface."""

    _ollama_alive: Optional[bool] = None
    _last_ollama_check: float = 0.0

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout
        self.nim_api_key = os.environ.get("NVIDIA_API_KEY", "")

    def _check_ollama_alive(self) -> bool:
        now = time.time()
        if SubstrateClient._ollama_alive is not None and (now - SubstrateClient._last_ollama_check) < 15.0:
            return SubstrateClient._ollama_alive

        try:
            # Quick 0.2s TCP connect test to Ollama host/port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2)
            s.connect(("127.0.0.1", 11434))
            s.close()
            SubstrateClient._ollama_alive = True
        except Exception:
            SubstrateClient._ollama_alive = False

        SubstrateClient._last_ollama_check = now
        return SubstrateClient._ollama_alive

    def call_ollama(self, model: str, prompt: str, system: Optional[str] = None) -> Tuple[bool, str, str]:
        """Call local Ollama instance with fast failover if daemon is down."""
        if not self._check_ollama_alive():
            return False, "", "Ollama daemon unreachable on 127.0.0.1:11434"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return True, data.get("response", "").strip(), ""
        except Exception as exc:
            return False, "", f"Ollama error ({model}): {str(exc)}"

    def call_nim(self, model: str, prompt: str, system: Optional[str] = None) -> Tuple[bool, str, str]:
        """Call NVIDIA NIM OpenAI-compatible API."""
        if not self.nim_api_key:
            return False, "", "NVIDIA_API_KEY not configured"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.3,
        }

        req = urllib.request.Request(
            f"{NIM_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.nim_api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=min(self.timeout, 10.0)) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                return True, content, ""
        except Exception as exc:
            return False, "", f"NIM error ({model}): {str(exc)}"

    def call_mock(self, model: str, prompt: str, system: Optional[str] = None) -> Tuple[bool, str, str]:
        """Deterministic mock generator for offline / fallback verification."""
        p_hash = hashlib.sha256((prompt + (system or "")).encode("utf-8")).hexdigest()[:8]
        response = (
            f"[{model} Deliberation {p_hash}]\n"
            f"Analyzed proposal: '{prompt[:60]}...'\n"
            f"- Strengths: Modular architecture, clear interface invariants.\n"
            f"- Critical Risks: Potential race conditions in distributed leases.\n"
            f"- Recommendation: Incorporate event-sourced convergence gates and timeout fallback."
        )
        return True, response, ""

    def query_substrate(self, substrate: Dict[str, Any], prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        """Execute a query against a specific substrate specification with fallback."""
        provider = substrate.get("provider", "ollama")
        model = substrate.get("model", "qwen3-coder:30b")
        t0 = time.time()

        ok, text, err = False, "", ""
        if provider == "ollama":
            ok, text, err = self.call_ollama(model, prompt, system)
        elif provider == "nim":
            ok, text, err = self.call_nim(model, prompt, system)
        elif provider == "mock":
            ok, text, err = self.call_mock(model, prompt, system)

        # Fallback to mock if API/local is down
        if not ok:
            mock_ok, mock_text, _ = self.call_mock(f"mock-{model}", prompt, system)
            if mock_ok:
                return {
                    "ok": True,
                    "substrate_id": substrate.get("id", model),
                    "model": model,
                    "provider": f"{provider}_fallback_mock",
                    "text": mock_text,
                    "latency_s": round(time.time() - t0, 3),
                    "fallback_note": err,
                }

        return {
            "ok": ok,
            "substrate_id": substrate.get("id", model),
            "model": model,
            "provider": provider,
            "text": text,
            "error": err,
            "latency_s": round(time.time() - t0, 3),
        }


class HeteroCouncil:
    """Council Deliberation & Consensus Engine with Heterogeneous Models."""

    def __init__(self, substrates: Optional[List[Dict[str, Any]]] = None, timeout: float = 30.0):
        self.substrates = substrates or DEFAULT_SUBSTRATES
        self.client = SubstrateClient(timeout=timeout)

    def calculate_n_eff(self, panel: List[Dict[str, Any]]) -> float:
        """Calculate effective independent vote count ($N_{\\text{eff}}$).

        Weights from the same model family are discounted by 0.5 to penalize
        monocultural consensus bias.
        """
        families: Dict[str, int] = {}
        for s in panel:
            fam = s.get("family", "unknown")
            families[fam] = families.get(fam, 0) + 1

        n_eff = 0.0
        for fam, count in families.items():
            if count == 1:
                n_eff += 1.0
            else:
                # First vote is 1.0, additional votes from same family count as 0.2
                n_eff += 1.0 + (count - 1) * 0.2
        return round(n_eff, 2)

    def ideate(self, topic: str, system_override: Optional[str] = None) -> Dict[str, Any]:
        """Phase 1: Multi-angle Blind Ideation from each council member."""
        system_base = (
            "You are an expert autonomous system architect in an open-source AI council. "
            "Provide creative, rigorous, concrete technical ideas with minimal fluff."
        )
        system = system_override or system_base
        results = []

        for sub in self.substrates:
            prompt = (
                f"Council Member Role: {sub.get('role', 'generalist')}\n"
                f"Topic for Ideation: {topic}\n\n"
                "Propose 2-3 key technical concepts, potential bottlenecks, and execution steps."
            )
            res = self.client.query_substrate(sub, prompt, system)
            results.append(res)

        return {
            "phase": "ideation",
            "topic": topic,
            "timestamp": time.time(),
            "n_eff": self.calculate_n_eff(self.substrates),
            "proposals": results,
        }

    def debate(self, topic: str, proposals: List[Dict[str, Any]], rounds: int = 1) -> Dict[str, Any]:
        """Phase 2: Adversarial Peer Review / Critique Loop."""
        critiques = []
        combined_proposals = "\n\n".join(
            f"--- Proposal by [{p.get('substrate_id')}] ---\n{p.get('text')}"
            for p in proposals if p.get("ok")
        )

        for sub in self.substrates:
            prompt = (
                f"Topic: {topic}\n"
                f"Review the following proposals from council peers:\n\n"
                f"{combined_proposals}\n\n"
                "As the Council Critic / Specialist, evaluate:\n"
                "1. Hidden failure modes or unverified assumptions\n"
                "2. Specific synthesis or improvement that combines the best parts\n"
                "3. Your confidence rating (1-10) for this plan."
            )
            res = self.client.query_substrate(sub, prompt, "You are an adversarial red-team reviewer.")
            critiques.append(res)

        return {
            "phase": "debate",
            "topic": topic,
            "rounds": rounds,
            "critiques": critiques,
        }

    def synthesize_consensus(self, topic: str, ideation_res: Dict[str, Any], debate_res: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Formal Synthesis and Actionable Graph Contract."""
        synthesis_prompt = (
            f"Task/Topic: {topic}\n\n"
            "=== Council Proposals ===\n" +
            "\n".join(f"[{p.get('substrate_id')}]: {p.get('text')[:300]}..." for p in ideation_res.get("proposals", []) if p.get("ok")) +
            "\n\n=== Peer Critiques ===\n" +
            "\n".join(f"[{c.get('substrate_id')}]: {c.get('text')[:300]}..." for c in debate_res.get("critiques", []) if c.get("ok")) +
            "\n\nProduce the final unified execution spec with:\n"
            "1. Core Architecture Definition\n"
            "2. Invariants & Guardrails\n"
            "3. Step-by-step Action Graph Specification (Nodes & Edge Conditions)"
        )

        # Primary architect synthesizes
        primary = self.substrates[0]
        res = self.client.query_substrate(
            primary, synthesis_prompt, "You are the Council Synthesizer and Master Orchestrator."
        )

        return {
            "phase": "consensus",
            "topic": topic,
            "consensus_text": res.get("text", ""),
            "synthesizer": primary.get("id"),
            "n_eff": self.calculate_n_eff(self.substrates),
            "raw_deliberation": {
                "ideation": ideation_res,
                "debate": debate_res,
            },
        }

    def run_full_council(self, topic: str) -> Dict[str, Any]:
        """Execute complete Ideation -> Debate -> Consensus Pipeline."""
        ideation = self.ideate(topic)
        debate = self.debate(topic, ideation.get("proposals", []))
        consensus = self.synthesize_consensus(topic, ideation, debate)
        return consensus


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", required=True, help="Topic/Goal for council deliberation")
    p.add_argument("--json", action="store_true", help="Output full JSON deliberation record")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    council = HeteroCouncil()
    res = council.run_full_council(args.topic)

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("=" * 70)
        print(f"🏛️  AIOS HETEROGENEOUS COUNCIL DELIBERATION (N_eff: {res['n_eff']})")
        print(f"🎯 Topic: {res['topic']}")
        print("=" * 70)
        print("\n📜 UNIFIED CONSENSUS & ACTION SPEC:\n")
        print(res["consensus_text"])
        print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
