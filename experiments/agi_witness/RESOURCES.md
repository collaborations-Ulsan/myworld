# AGI witness experiment — VERIFIED box resources (2026-07-05)

Grounded by probe, not by stale config. Executor agents: read this, don't re-probe.

## Compute
- **CPU only.** RTX 5090 is sm_120/Blackwell — CUDA-incompatible with installed torch
  (is_available() lies; kernels error). Treat as no-GPU. No paid training. Frozen models only.

## NIM (heterogeneous frontier pool) — `nv ask "<FULL/ID>" "<prompt>"`
- **`nv ask` requires the FULL org-prefixed id** (e.g. `deepseek-ai/deepseek-v4-pro`), NOT the
  short name. Short names 404. `nv panel --set <set>` maps short names internally.
- Confirmed working: `deepseek-ai/deepseek-v4-pro` → answers. 121 models total (`nv models`).
- Panel-confirmed answering models: `deepseek-ai/deepseek-v4-pro`, `qwen/qwen3.5-397b-a17b`,
  `nvidia/nemotron-3-ultra-550b-a55b`. Some listed ids 404 (e.g. nemotron-ultra-253b, gpt-oss-120b,
  bare `deepseek-v4-pro`) — always confirm an id answers before batching against it.
- Key auto-sourced from `~/.config/nvidia/api.env` (NVIDIA_API_KEY). Big models can cold-start
  slow (llama-3.3-70b timed out at 40s once) — allow generous timeouts / retry.

## Local (ollama) — cheap, offline, high-volume
- Installed NOW (verified): `qwen2.5-coder:7b`, `qwen3:8b`, `qwen2.5:7b`, `nomic-embed-text:latest`.
- NOT installed (stale global-config claim): `qwen3-coder:30b`. Do not assume it.
- Embeddings: `nomic-embed-text` via ollama.

## Data — the Akashic behavior commons
- `python3 -c "import sys; sys.path.insert(0,'scripts'); import aios_agent_behavior as B; B.load_behavior_memories()"`
  → **1065 entries**. Per-entry keys: category, content, confidence, domain, provider, relations,
  evidence_refs, id (+ top_tools/tool_freq on many). Categories: code 311, personal 300, data 300, docs 154.
- Shipped H⁰ poison guard reusable: `scripts/aios_akashic_guard.py`
  (`build_profiles(mems)`, `poison_score(entry, profiles)`, `_flagged(score, cat, profiles)`).
