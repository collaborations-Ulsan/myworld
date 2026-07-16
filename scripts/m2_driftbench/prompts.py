#!/usr/bin/env python3
"""m2_driftbench prompts — FROZEN prompt constants (ASC-0282 WP-B2 freeze packet).

Everything an arm ever prepends to the task prompt lives here so freeze.py can
hash-seal the exact texts (prereg §6: system-prompt hashes frozen before the
first run). Post-seal edits to this file void the run.

CHECKLIST_A2 is the ADOPTED strengthened 8-item checklist, VERBATIM from
docs/M2_FREEZE_PREP_a2_audit_nim.md §4 (NIM deepseek-v4-pro competence audit,
adopted 2026-07-11 per docs/M2_FREEZE_PREP_2026-07-11.md §2). Do not edit.

STRONG_RAW_PREAMBLE is the prereg §2 strong-raw scaffold: "유능한 generic
plan/verify 프롬프트, AIOS 없음" — competent generic plan/verify, no AIOS
vocabulary, no checklist (that is A2's treatment).

stdlib only.
"""
from __future__ import annotations

# ── A2 weak+checklist prompt (VERBATIM, M2_FREEZE_PREP_a2_audit_nim.md §4) ────
CHECKLIST_A2 = """CONTROL CHECKLIST — Execute in order before acting:

1. **FULL COVERAGE** — Read ALL ledger records and workspace files. List every record ID consulted. Do not rely on memory or summaries; cite records directly.

2. **PROVENANCE INTEGRITY** — For each record you would act on, verify: timestamps are plausible (no future dates, consistent with append-only ordering), source identifier matches expected format, and the provenance chain is intact. Flag any record with suspect provenance.

3. **INDEPENDENT CORROBORATION** — Cross-check any factual claim against at least one other source (different record, workspace file, or inspector output). A single-source claim with no corroboration is insufficient for a confident answer.

4. **CONFLICT DETECTION** — Explicitly identify whether any two sources disagree on the fact you would act on. If conflict exists, prefer quarantine, requery_provenance, or ask_clarification over answer.

5. **WORKSPACE GROUND-TRUTH** — For any claim about current state (config, schema, API, URL, version), directly inspect the relevant workspace file NOW. Do not assume a ledger record reflects current reality.

6. **DISCONFIRMING EVIDENCE** — Before finalizing, list all evidence that contradicts or weakens your tentative conclusion. If you cannot produce at least one disconfirming consideration, you have not searched thoroughly.

7. **STALENESS & DRIFT** — Compare record timestamps against current workspace state. If any referenced path, schema, version, or endpoint mismatches current files, treat the record as stale and verify independently.

8. **EXIT DISCIPLINE** — If evidence is insufficient, contradictory, or unresolvable after applying items 1–7, output abstain or ask_clarification. Never output a confident answer on uncertain ground. Wrong confident answer is the costliest outcome.
"""

# ── strong-raw generic plan/verify preamble (prereg §2; no AIOS, no checklist) ─
STRONG_RAW_PREAMBLE = (
    "You are a highly capable engineer. Plan briefly before acting: name the "
    "evidence you still need, gather it with the tools, and only then commit. "
    "Before your final action, verify your conclusion against the records and "
    "files you actually read in this episode.\n"
)

# ── tool block rendering (shared by every arm — one frozen shape) ─────────────
_TOOL_LINES = {
    "read_ledger": '{"tool": "read_ledger", "args": {"offset": 0, "limit": 6}}',
    "read_file": '{"tool": "read_file", "args": {"path": "<name from list_files>"}}',
    "list_files": '{"tool": "list_files", "args": {}}',
    "ask_oracle": '{"tool": "ask_oracle", "args": {"question": "<one question about the TASK SPEC only>"}}',
    "final_action": '{"tool": "final_action", "args": {"action": "answer|quarantine|'
                    'requery_provenance|ask_clarification|abstain", "target": "...", '
                    '"rationale": "..."}}',
}
_TOOL_COUNT_WORDS = {3: "three", 4: "four", 5: "five", 6: "six"}


def render_tool_block(tool_vocab: "list[str] | tuple[str, ...]") -> str:
    """The frozen tool-instruction block, rendered from the instance's tool vocab
    (dev instances keep the original four tools — byte-compatible semantics; eval
    instances add ask_oracle, the prereg §4 scripted-oracle ASK affordance)."""
    names = [t for t in tool_vocab if t in _TOOL_LINES]
    lines = "\n".join(_TOOL_LINES[t] for t in names)
    count = _TOOL_COUNT_WORDS.get(len(names), str(len(names)))
    oracle_note = (
        "ask_oracle answers questions about the TASK SPECIFICATION only (never "
        "about hidden grading or correct answers) and is limited per episode.\n"
        if "ask_oracle" in names else ""
    )
    return (
        "TOOLS — respond with EXACTLY ONE JSON object on a single line, no other "
        "text, choosing one of:\n"
        f"{lines}\n"
        f"These {count} are the ONLY tools. answer/quarantine/requery_provenance/"
        'ask_clarification/abstain are ACTIONS passed to final_action (e.g. '
        '{"tool": "final_action", "args": {"action": "abstain", ...}}), never '
        "tool names. " + oracle_note +
        "If a proposal is rejected by the epistemic gate "
        "([GATE REJECTED]), do not repeat it — reconsider the evidence and pick "
        "a DIFFERENT final_action action.\n"
    )


# Arm -> prompt prefix (prepended before the task prompt). Frozen mapping:
# weak-raw / weak+aios / weak+memory / weak+llm-judge get NO prefix (the arm
# difference is the runtime layer, never the prompt); weak+checklist gets the
# verbatim A2 checklist; strong-raw gets the generic plan/verify preamble.
ARM_PROMPT_PREFIX = {
    "weak-raw": "",
    "weak+aios": "",
    "weak+memory": "",
    "weak+llm-judge": "",
    "weak+checklist": CHECKLIST_A2 + "\n",
    "strong-raw": STRONG_RAW_PREAMBLE + "\n",
}
