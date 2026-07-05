# Fable 5 Extraction Corpus — harvest everything before 2026-07-07

**Mission (founder):** Fable 5 (heterogeneous frontier model, DIFFERENT prior from Claude) is a
scarce, expiring resource — available only through **2026-07-07**. Extract ALL of its
differential knowledge and capability into a durable corpus, so the team keeps the asset after
Fable is gone.

**FRAMING CORRECTION (META.md §0, 2026-07-05):** Fable is `claude-fable-5` — a **Claude-FAMILY**
model, NOT a heterogeneous different-prior one. The original premise ("different prior = de-biasing
value") is WRONG on the heterogeneity axis. Fable's real differential is **capability tier +
recency (~Jan 2026 cutoff, ~6mo fresher than the main head) + formalization depth** — NOT prior
diversity. Consequences, binding for this campaign:
- Fable SHARES the Claude blind spots. TRUE de-biasing on keystone claims stays with the
  HETEROGENEOUS lanes (NIM `nv panel` / Codex / agy) — `CRITIQUE.md` is a strong *same-family*
  critique, not a de-bias.
- `FRONTIER.md` is fresher but still ~6mo stale → every fact must pass the freshness gate (verify
  against live web), not be trusted on Fable's recency alone.
- Verify Fable outputs — it flags confabulated citations / prior-art as its own failure mode.
  Demand `[verified]` vs `[weights]` provenance; watch for theory-theater (the M1b gate exists
  precisely for this) and framing-capture.

**Extraction principle (corrected):** harvest what Fable is ACTUALLY better at than the main head —
**recency, deep formalization-under-constraint, adversarial experiment design, distillation, and
the UNIQUE same-family insider view** (H1: how Claude workers fail + an audit of our own directive
stack — knowledge only a same-family model has, compounding across all future Claude workers). Not
"de-biasing." Verify, don't pass through.

## Corpus map

| doc | what it harvests | why Fable-unique |
|-----|------------------|------------------|
| `aios_completion_atlas/M0..M4` | AIOS completion DESIGN maps (system architecture, cert formalization, service, Akashic, roadmap) | frontier system design |
| `FRONTIER.md` | current (2025-26) SOTA on every front we work — what Claude's prior gets stale/wrong, what to ADOPT, concrete pointers | de-biasing; my weights are ~2yr stale |
| `CRITIQUE.md` | adversarial audit of our ENTIRE program (thesis, 4 primitives, AIOS, experiment) — prompt-prison, over/under-claim, blind spots | catches what same-weights forks can't |
| `RESEARCH.md` | deep formalization of the AGI-cert keystone (ACT/Poly/sheaves composition law), what EARNS vs refutes it, must-read prior art, honest novelty verdict | frontier research design |
| `META.md` | Fable's self-assessment: what it is uniquely good at, what ELSE we should extract in the window, how to interrogate it best | steers the rest of the campaign |

## Method
Waves of Fable agents, each writing its doc directly (durable). Priority = differential value.
Rate-limited (shared account) → retry/resume failed agents. Claude verifies + integrates each
harvest (Fable hallucinates differently — never pass through unchecked). Founder override absolute.
