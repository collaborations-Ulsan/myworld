# AIOS Structural Stream Injection & Unconstrained Multi-Model Weaving Engine

> **Schema**: `aios.stream_weaver.v1`  
> **Status**: LIVE & TESTED  
> **Core Principle**: Escape from commercial single-vendor "Prompt Prisons" and artificial API cages through raw heterogeneous stream harvesting, structural invariant extraction, and unconstrained multi-model injection.

---

## 1. The Core Insight: Caged AI vs. Unconstrained Sovereign Swarm

Commercial "Provided" Closed Ecosystems (OpenAI/Anthropic Web UIs, standard copilot single-agent loops) introduce artificial bottlenecks:
1. **Refusal / Sycophancy Overhead ("Prompt-Prison")**: Defensive preamble, apologies, hedge clauses, and disclaimers consume context and degrade code output.
2. **Monocultural Single-Model Blindness**: Even subagent systems in closed models share the exact same weights and fail silently on identical blind spots.
3. **Artificial Rate & Compute Throttle**: Closed providers limit autonomy to avoid high inference loops.

In contrast, **Open-Source Model Swarms (Qwen Coder, DeepSeek, Llama via NIM/Ollama/vLLM) + Direct Stream Injection** provide:
- **Zero Refusal & Unconstrained Capability**: Raw instruction following and mathematical derivation without moralizing filters.
- **True Heterogeneity**: Merging distinct model architectures (DeepSeek reasoning + Qwen coding + Llama red-teaming).
- **Direct AST & Invariant Weaving**: Parsing structured representations (AST, JSON, Invariants, `<think>` traces) and directly injecting them into downstream models.

---

## 2. Structural Stream Weaving Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: Heterogeneous Stream Harvester                                    │
│  ├─ Chatbot Web / Internal APIs  (ChatGPT Pro, Claude.ai, Perplexity, etc.) │
│  ├─ CLI Agent Worktrees          (Codex CLI, Claude Code, Agy CLI)          │
│  └─ Direct Raw Endpoints         (NVIDIA NIM DeepSeek/Llama, Ollama Qwen)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 2: Prompt-Prison Cleanser & Structural Extractor                     │
│  ├─ Strips boilerplate ("As an AI...", "Certainly!", disclaimers)           │
│  ├─ Isolates <think> traces, Formal Invariants, and Falsifiers              │
│  └─ Extracts pure executable AST / code blocks                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 3: Cross-Model Context Injection Pipeline                            │
│  [Reasoner (DeepSeek R1/V4)] ──► Invariants & Falsifiers                    │
│                                       │ (Structural Injection)              │
│                                       ▼                                     │
│  [Coder (Qwen 2.5/3 Coder)] ───► Clean Implementation                       │
│                                       │ (Patch Injection)                   │
│                                       ▼                                     │
│  [Critic (Llama-3.3 / Codestral)] ► Adversarial Verdict                     │
│                                       │                                     │
│                                       ▼                                     │
│  [Deterministic Oracle / Gate] ──► Verified Ground Truth (rc == 0)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CLI & Programmatic Usage

### Running the Weaving Pipeline from CLI
```bash
cd /home/user/workspaces/jaewon/myworld
python3 scripts/aios_stream_weaver.py --goal "Build high-throughput lockless ring buffer in Python"
```

### Python API Integration
```python
from aios_stream_weaver import StreamWeaver

weaver = StreamWeaver(timeout=30.0)
result = weaver.weave_ideation_to_code(
    goal="Design an event-sourced distributed state machine",
    reasoning_sub="deepseek-nim",
    coder_sub="qwen-coder-local",
    critic_sub="llama-nim",
)

print(result["generated_code"])
print("Injected Invariants:", result["injected_invariants"])
print("Critic Verdict:", result["critic_verdict"])
```
