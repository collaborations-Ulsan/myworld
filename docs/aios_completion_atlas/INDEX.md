# AIOS Completion Atlas — the maps to complete AIOS

**Purpose:** capture, while Fable 5 (heterogeneous frontier designer) is available
(**through 2026-07-07**), EVERY design map needed to complete AIOS — so that after Fable is
gone, implementation can proceed with same-weights Claude subagents + the founder, without
needing Fable's frontier prior again. Fable draws the DESIGN; Claude subagents build it.

**Discipline:** Fable is the scarce, expiring resource. Extract only what is Fable-UNIQUE
(frontier heterogeneous design, critique, formalization) — NOT implementation labor. Every map
is written durably here so it outlives the window.

## The map set (priority order — highest Fable-leverage / most framing-critical first)

| id | map | what it fixes | status |
|----|-----|---------------|--------|
| **M0** | **Master Completion Map** — end-state architecture of a COMPLETED AIOS; every component (cert layer + substrate + service + Akashic); control/data flows; the contracts between them; crisp "AIOS is complete when ___"; top-level dependency graph (D0–D6). Refined this atlas index (see `M0_MASTER_MAP.md` §4). | the north star + frame for all other maps | **done** (Fable, 2026-07-05) |
| **M1a** | **Certificate Interface Spec** — the `Certificate` type, cost accounting, guard/lint tier, extraction plan for `experiments/agi_witness/certs/*` → a library. Unconditional (useful whatever the witness verdict). See `M1a_CERTIFICATE_INTERFACE.md`. | certs usable as guards today, without composition claims | **done** (Fable, 2026-07-05) |
| **M1b** | **Composition Law (ACT)** — the coupled wiring formalized (Poly + sheaves + optics/categorical cybernetics). **CONDITIONAL on the witness (D0) firing positive** — formalizing before the verdict is theory-theater (panel: "taxonomy masquerading as unification"). | the theory that makes the 4 certs ONE object | gated on D0 |
| **M2** | **Substrate & Service Map** — AIOS as a running service: install/onboard/doctor UX, packaged ≤20-file core, provider adapters, MCP + chat surface, permission model, how a user connects and gets real value. | "AIOS 사용이 안된다" → serviceable | pending |
| **M3** | **Akashic Commons & Trust Map** — unify the THREE Akashic incarnations (work-index / CF worker / witness claims-ledger) into one typed append schema; hash-chain + `aios verify`; the TRUSTED-WRITER model (writer signatures, admission, honest v1 scope-out); poison-guard (H⁰) integration; local/global tiers. | who may write / how it's trusted; ledger vs diary | pending |
| **M4** | **Roadmap / Gap / Deprecation Map** — D0–D6 expanded to ordered work items with owners; fossil archival (kernel-audit Keep/Archive/Delete made executable); precisely what Claude subagents implement post-Fable. THE enabler of "proceed after Fable." | executable path without Fable | after M1a–M3 |
| **M5** | **Memory-Compounding Evaluation Map** — protocol proving the north-star claim itself: same task class twice → measured improvement citing accepted memory; CapabilityOS observation-loop metric; GenesisOS challenge wiring test. | the north star is asserted, never measured (hole H5) | pending |

Per-OS completion specs for hivemind / memoryOS / CapabilityOS / GenesisOS stay folded into
M0/M4 — M0 confirmed the sibling repos are healthy; the gaps are seam-level (unwired organs),
not per-OS rewrites.

## Grounding each map must respect
- `docs/AIOS_AGI_CERTIFICATION_KEYSTONE.md` — thesis, heterogeneous-panel verdict (parts are prior-art; novelty only in composition), the running witness experiment.
- The 2025-26 frontier is LIVE and converging (verifiable-agent-execution ledgers, applied category theory for agents) — maps must situate AIOS in it, not pretend isolation.
- Honesty: a map claims "complete" only for what is actually specified; open holes are named as holes.
