# MyWorld Agent Entry

Before working from the `myworld/` workspace root, read these files:

1. `docs/AIOS_NORTHSTAR.md`
2. `docs/AIOS_DEFINITION.md`
3. `docs/AIOS_AGENT_PROTOCOL.md`
4. `docs/AIOS_SMART_CONTRACT.md`
5. `docs/AIOS_WORK_DISPATCH.md`
6. `docs/AIOS_BUILD_METHOD.md`
7. `docs/AIOS_AGENT_LEDGER.md`
8. `docs/AIOS_AGENT_SELF_LOOP.md` — how to keep your work going without operator re-prompt
9. The role file for the repo you are touching:
   - `docs/agents/CODEX_UI_AGENT.md`
   - `docs/agents/HIVEMIND_AGENT.md`
   - `docs/agents/MEMORYOS_AGENT.md`
   - `docs/agents/CAPABILITYOS_AGENT.md`
   - `docs/agents/GENESIS_AGENT.md`

Repository boundaries:

- `hivemind/` owns execution, scheduling, provider CLI wrapping, proofs, and verification.
- `memoryOS/` owns memory, context paging, provenance, review lifecycle, and retrieval traces.
- `CapabilityOS/` owns capability maps, routing recommendations, tool/MCP/API/skill catalogs, and fallback plans.
- `GenesisOS/` owns divergence, assumption mutation, prompt-prison critique, multiple-universe branches, and contract seeds before verification.

Do not mix ownership unless an AIOS smart contract or operator instruction explicitly assigns cross-repo work.

Default rule: `myworld/` dispatches work; implementation happens inside the
owning lower repo.

Codex's primary control-plane duty is to search, retrieve context, route
capabilities, issue precise work packets, verify evidence, and propose better
AIOS methods when the current loop cannot close.

Current delegated focus: Codex should primarily own AIOS design, UI/UX,
frontend, and visual verification work for the Control Center and chat
surfaces. Non-UI child-repo implementation should normally be dispatched to
the owning repo agent and then collected, not absorbed into direct Codex work.

Codex CLI absorption rule:

- During substantial Codex sessions, keep observing the actual workloop and
  update `docs/AIOS_CODEX_CLI_ABSORPTION.md` when a repeated behavior should
  become an AIOS primitive, contract, or routing rule.
- Prefer evidence-bound notes over implicit operator memory:
  - command receipts,
  - changed files,
  - PID/log/result artifacts,
  - claim downgrade events,
  - next-owner handoffs.
- Do not promote a Codex habit to canonical AIOS behavior until it has either a
  replayable receipt or a contract/test path.

# Freshness gate — never answer from stale training knowledge (HARD RULE, all agents, 2026-07-04)

Answering a time-sensitive question from cached training memory **without checking** is a FAILURE, not
intelligence (founder directive). Your knowledge has a cutoff; on fast-moving topics the correct answer has
already changed. The global config files agents hold about each other and about tools/models can likewise be
stale — treat them as hints to verify, not ground truth.

BEFORE answering, run this gate. If the question matches ANY trigger, you MUST ground against a CURRENT source first:
- recommendations · "best" · "추천" · "제일 좋은"
- "latest" · "newest" · "current" · "최신" · "현재" · "지금" · "요즘" · a specific year
- any model / library / framework / tool / API / provider / hardware CHOICE
- SOTA · benchmark · pricing · version · release claims
- "what exists" · "has anyone" · "state of the art" · current events or live data
- strategy / idea generation where the best option depends on the current landscape

Grounding, in order of preference:
1. Use your own web-search tool (WebSearch / search / insane-search / deep-research).
2. If you have no search tool, **ACTIVELY delegate** to a substrate that does — a subagent, another CLI
   (claude / codex / agy-antigravity / local LLMs), or a heterogeneous model panel (e.g. NVIDIA NIM `nv panel`).
   Do this by default, not only when asked. Different priors + live grounding catch what one frozen head cannot.
3. **Record the grounded answer + source + date to the knowledge ledger** (AIOS Akashic / memory) so head/session
   agents reuse the verified answer instead of re-deriving it from stale weights and falling into fragmentary knowledge.

If you genuinely cannot verify: SAY SO explicitly ("my training may be outdated on X — verify before relying on
this") rather than presenting a confident cached recommendation as current.

**The default is CHECK. The failure mode is deciding/answering without checking.**
