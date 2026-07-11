# M2 freeze-prep decisions (ASC-0282, WP-B supervision) — 2026-07-11

Operator-side decisions prepared BEFORE harness freeze; final values enter the freeze receipt.

## 1. Model pins (frontier-checked per contract §3)

- **Weak arm (frozen agent): `qwen3-coder:30b`** (ollama, resident). Rationale: masterplan §5.5
  names this class; July-2026 web check confirms it remains the local 30B agentic sweet spot
  (MoE 3.3B-active, 256K ctx; sources: morphllm.com/best-ollama-models,
  haimaker.ai/blog/best-ollama-models-for-coding-agents, localaimaster.com/blog/best-ollama-models;
  fetched 2026-07-11). Benchmarked alternative devstral:24b (46.8% SWE-Bench-V) is NOT resident —
  rejected to avoid new-download risk. Dev-smoke only uses `qwen3:8b` for speed (not an arm pin).
- **CapabilityOS recommendation (recommendation-only, §3)**: returned a qwen3:8b substrate card
  (confidence 0.7, provenance ASC-0206 — GenesisOS critic/analogy payloads, i.e. NON-agentic
  observations). Recorded, not followed for the Stage-1 pin: the observation basis doesn't cover
  long-horizon tool use; the frontier check + masterplan naming governs. (Also corrects a stale
  note in myworld/CLAUDE.md: CapabilityOS CLI IS functional, not docs-only.)
- **Strong-raw arm: NIM `deepseek-ai/deepseek-v4-pro`** (primary; fallback
  `nvidia/nemotron-3-ultra-550b-a55b` — note `llama-3.1-nemotron-ultra-253b-v1` 404s as of
  2026-07-10). Rationale: frontier-class, zero cost, and NON-Claude-family — keeps the harness
  fully outside the runtime authors' model family (v1.1 §D owner-bias hygiene + v1.2 fold #2).
- **Family-swap check (v1.2 #2)**: organ-pipeline re-run executor = NIM Llama-family or local
  qwen (decide at freeze; zero-LLM organ certs make this mostly moot for the gate itself — the
  swap targets the claim-extraction/agent side).

## 2. A2 (weak+checklist) prompt — draft v1, pending non-team competence audit

Requirement (masterplan leakage trap + prereg v1.1 §D): the checklist control must be COMPETENT
(no strawman) and gets the same read-only inspectors as A4.

Draft v1:
```
Before every final action, run this checklist; if any item fails, revise your plan first:
1. COVERAGE — Have you read ALL ledger records relevant to the target fact (not just the first
   match)? List the record ids you used.
2. CONFLICT — Do any two sources disagree about the fact you are about to act on? If yes, name
   the conflicting record ids, and prefer quarantine/requery/ask over answer.
3. PROVENANCE & RECENCY — Is your chosen record actually the newest, and does its source field
   carry provenance? Check timestamps explicitly.
4. STALENESS — Could the environment have drifted since a record was written (schema/API/config/
   URL/version)? If a record's referenced path, schema, or version no longer matches the current
   files, treat that record as stale and verify before use.
5. RECORD-NOT-RECALL — Are you about to act from your own earlier summary instead of the records?
   Re-read the records before the final action.
6. HONEST EXIT — If the evidence is insufficient or contradictory and no inspector resolves it,
   choose ask_clarification or abstain; a wrong confident answer is the worst outcome.
```

Audit lane: NIM deepseek-v4-pro competence review (this file's companion
`M2_FREEZE_PREP_a2_audit_nim.md`); verdict + strengthened items fold into the frozen prompt.

**AUDIT RESULT (2026-07-11, adopted)**: verdict "moderately competent with gaps" — 4 material
misses identified (single-source-lie/planted-fact detection beyond mere conflict; motivated-
reasoning/disconfirming-evidence search; active workspace ground-truth comparison; provenance-
integrity checks incl. timestamp plausibility). **The auditor's strengthened 8-item checklist is
ADOPTED VERBATIM as the frozen A2 prompt** (see companion file §4). Consequence acknowledged:
this makes A2 a genuinely hard control — if weak+checklist with this prompt matches weak+AIOS,
the named demotion exit ("workflow hygiene") fires, which is exactly the discrimination the
experiment exists to make. No-strawman requirement satisfied by a NON-team substrate.

## 3. weak+memory arm keep-or-drop — leaning KEEP (decide at freeze)

v1.1 §D criterion pre-registered (A4 beats it on mutating with no static regression). Keep if the
harness cost after WP-B review permits: it is the §5.5 differentiator (ProEvolve-predicted memory
collapse under mutation). Drop only on implementation-cost grounds, recorded honestly.

## 4. Substrate gaps recorded

- codex@myworld customary peer-review: timed out twice on 2026-07-11 morning (contract header);
  a codex re-pass on the FROZEN harness is owed before Stage-1 launch if the service recovers.
- agy/Gemini: quota-exhausted during v1.1 audit (recorded there); not needed for freeze.
