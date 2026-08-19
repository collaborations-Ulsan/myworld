# AIOS Absorption Backlog — ecosystem ideas → AIOS development

Operator digest of what Star Radar (`scripts/aios_star_radar.py`) absorbed from the
GitHub ecosystem on 2026-06-07, turned into a prioritized AIOS development backlog.
Each was reviewed and accepted into MemoryOS (draft-first). "흡수" = the idea drives
AIOS development, not just a note.

## Built this session (absorption → shipped capability)

| absorbed idea | source | AIOS evolution built | tests |
|---|---|---|---|
| security enforcement (sandbox, credential isolation, prompt-injection, endpoint allowlist) | **ironclaw** (peer Agent OS) | `aios_secret_scan` (blocks high-confidence secrets at commit), `aios_prompt_guard` (sanitize untrusted LLM input), `aios_endpoint_policy` (outbound allowlist) | ✓ |
| shareable installable .claude skill collections | **mattpocock/skills, gstack, antigravity** (100k+★ trend) | `aios_skill_catalog` — unified index (59 skills) + `--export <name>` (install one) + `--export-all` (install the whole AIOS harness collection as a bundle). AIOS skills are now a shareable installable library. | ✓ |
| agent-management / work history | **paperclip** (~69k★) | `aios_work_history` — unified chronological timeline across all organs' receipts (what AIOS did, when, which organ, outcome, substrate). Complements the value ledger. | ✓ |

## Backlog (absorbed, mapped to AIOS, not yet built — operator/founder to prioritize)

| absorbed idea | source | concrete AIOS action | size |
|---|---|---|---|
| **self-evolving skills** (eval→improve→test→keep/rollback) | darwin-skill | CORRECTION (verify-before-building): AIOS **already has** `scripts/aios_self_evolve.py` — a per-specialist organ that distills VERIFIED-GOOD invocations into a principles file, with the critical no-self-distillation safety (never evolve from a helper's own raw output). darwin-skill's contribution is the explicit propose→test→**keep/rollback A/B** (variant vs current, keep the strictly-better) — an ENHANCEMENT to the existing organ, not a missing capability. Parametric (LoRA on the verified set) is the named follow-on. | S |
| **benchmarked memory system** | MemPalace (~54k★) | benchmark MemoryOS against MemPalace; run the retrieval-research-cycle vs it; study its patterns while keeping AIOS active-graph + draft-first differentiators. | S |
| **queryable knowledge graph from code/docs** | graphify (~60k★) | adopt queryable cross-source graph patterns in MemoryOS (aligns project_lgm_memory_thesis). | M |
| **single-GPU agent research loop** | karpathy/autoresearch (~85k★) | run research/eval agents on the local dual-5090 via Hive. | M |

| **harness construction + failure introspection** | ECC (~240k★) | **ABSORBED as text 2026-08-16** → `docs/AIOS_HARNESS_CONSTRUCTION_ABSORBED_2026-08-16.md`. Two things AIOS never wrote down: (a) how to shape a tool surface — action-space granularity by RISK (micro for deploy/permission, macro only when round-trips dominate), the 4-field observation contract (`status`/`summary`/`next_actions`/`artifacts`), and the **error recovery contract** (root-cause hint + safe retry + explicit stop condition IN the error payload) which is the missing operational half of DNA invariant 4; (b) the capture→diagnose→contained-recovery→report loop that must run BEFORE a retry, because a blind retry destroys the evidence. Concrete AIOS action: hold CapabilityOS tools at micro/medium (a recommendation must stay inspectable), let HiveMind hold macro (it emits receipts), and make organ errors carry the 3-part recovery contract. ECC itself NOT installed — 25.3k tokens of always-on skill descriptions, 6 node spawns per Bash call, and its `council` is a same-weights 4-voice panel that would shadow ours (+0.047 same-family ceiling). | S |

## Process note

The local-LLM distiller mis-called darwin-skill "low fit"; **Claude-verify overrode
it** (the absorption pipeline's mandatory verify step — never act on unverified
substrate output). Re-run the radar periodically (dedup surfaces only new repos);
promote genuine fits via /aios-memory-propose.
