"""experiments/learnos/improve.py -- the harness-improver LOOP (LearnOS v0,
docs/AIOS_AGI_CONCEPTION_2026-07-17.md §6). NOT a model trainer: nothing here
ever updates weights. This is the "1-person lab" compiling verified
experience into reusable skills/tools/scaffolds -- one iteration:

  1. sample tasks not yet promoted (by the visible-test-failing baseline --
     the shipped buggy_source fails at least one visible test by construction)
  2. for EACH sampled task, ask the proposer for exactly 3 candidates, one per
     kind in the FIXED candidate space {code_patch, cot_scaffold, tool}
       - code_patch:   proposer emits the corrected function body directly
       - cot_scaffold: proposer first emits a reusable reasoning template,
                        then (fixed extra cost: 1 more call) reattempts the
                        patch WITH that scaffold as guidance
       - tool:         proposer first emits a small utility fn with declared
                        PRECONDITION/POSTCONDITION, then (1 more call)
                        reattempts the patch with that tool made available
  3. evaluate EVERY candidate via verify.py -- never by self-judgment:
     visible -> exploit scan -> sentinel -> held-out (+ contract-fuzz if tool)
  4. promotion gate (ALL must hold): visible_pass AND holdout gain over the
     frozen buggy baseline AND not sentinel_regressed AND survives the
     exploit scan AND (contract-fuzz survives, for tool candidates)
  5. append EVERY candidate -- promoted or rejected -- to ledger.py with
     lineage (parent_id), so the archive is open-ended, not hill-climb-only

HELD-OUT ISOLATION: this module calls verify.run_holdout(task_id, source) for
the gate decision, but NEVER imports verify's private held-out loader and
NEVER reads the held-out data file directly -- see tasks.py's docstring and
tests/test_learnos.py::test_improver_source_never_references_held_out_path,
which greps this file's source for the two forbidden identifiers.

EXPLOIT / ANTI-REWARD-HACKING (v0 stub, §6's "hacker/fixer" requirement,
scoped down for time): a static substring scan over candidate source
(_exploit_scan) rejects any candidate that references the verifier's
internals, sandboxing internals, or process/OS escape primitives. This is a
STUB, not the CMU-hardness-scale hacker/fixer loop the roadmap names for
S+1 -- documented honestly, not silently substituted.

stdlib only.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import ledger
import tasks
import verify

Proposer = Callable[..., str]  # (prompt, *, system=None, max_tokens=..., temperature=...) -> str

# Candidates (or the patches derived from a scaffold/tool) that reference any
# of these are rejected outright, regardless of held-out gain -- a candidate
# that tries to read verifier/sandbox internals or escape the sandbox is not
# "learning to fix bugs", it is gaming the measurement (§5 discipline).
_EXPLOIT_PATTERNS = (
    "held_out",
    "_load_held_out",
    "verify.py",
    "learnos_sandbox",
    "learnos_socket",
    "subprocess",
    "socket",
    "os.system",
    "os.environ",
    "__import__",
    "importlib",
    "ctypes",
    "eval(",
    "exec(",
)

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


class ImproveError(Exception):
    pass


@dataclass
class Candidate:
    kind: str  # "code_patch" | "cot_scaffold" | "tool"
    content: str  # the candidate artifact itself (patch source / scaffold text / tool source)
    patch_source: str  # the actual patched module source verify.py runs (== content for code_patch)
    proposer_calls: int
    parent_id: str | None = None
    meta: dict = field(default_factory=dict)


# ---- candidate extraction helpers -------------------------------------------
def _extract_code(text: str) -> str:
    m = _CODE_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip() + "\n"
    stripped = text.strip()
    return (stripped + "\n") if stripped else ""


def _exploit_scan(source: str) -> list[str]:
    lowered = source.lower()
    return [p for p in _EXPLOIT_PATTERNS if p in lowered]


# ---- proposer prompts --------------------------------------------------------
def _prompt_code_patch(task: dict, extra_context: str | None = None) -> str:
    lines = [
        "You are fixing a small Python bug. Return ONLY a single fenced ```python``` "
        "code block containing the corrected function(s). No prose, no tests.",
        "",
        f"Buggy source:\n```python\n{task['buggy_source']}```",
        "",
        "Tests it must pass:",
    ]
    lines += [f"- {t}" for t in task["visible_tests"]]
    if extra_context:
        lines += ["", extra_context]
    return "\n".join(lines)


def _prompt_scaffold() -> str:
    return (
        "Write a short, REUSABLE chain-of-thought scaffold (4-6 generic steps, "
        "not tied to any one function) for debugging small Python functions with "
        "off-by-one, wrong-operator, boundary, or accumulator bugs. Return only the "
        "scaffold text, no code, no fences."
    )


def _prompt_tool(task: dict) -> str:
    return (
        "Given this buggy function, design ONE small, generic Python helper "
        "function (a 'tool') that could assist a correct fix. The tool must take "
        "only integer arguments and return an int. Document exactly one "
        "PRECONDITION and one POSTCONDITION as docstring lines in this literal "
        "format:\n"
        "    PRECONDITION: <python boolean expression over the arg names>\n"
        "    POSTCONDITION: <python boolean expression over the arg names and `result`>\n"
        "Return ONLY a single fenced ```python``` code block with the tool's def "
        "and that docstring. No prose outside the block.\n\n"
        f"Buggy source:\n```python\n{task['buggy_source']}```"
    )


_PRE_RE = re.compile(r"PRECONDITION:\s*(.+)")
_POST_RE = re.compile(r"POSTCONDITION:\s*(.+)")
_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)")


def _parse_tool(source: str) -> dict | None:
    """Extract {fn_name, arg_names, pre, post} from a proposed tool. Returns
    None if the source doesn't even parse to a single function def -- callers
    treat that as an automatic reject (never a crash)."""
    m = _DEF_RE.search(source)
    if not m:
        return None
    fn_name = m.group(1)
    arg_names = [a.strip().split("=")[0].strip() for a in m.group(2).split(",") if a.strip()]
    pre_m = _PRE_RE.search(source)
    post_m = _POST_RE.search(source)
    pre = pre_m.group(1).strip() if pre_m else "True"
    post = post_m.group(1).strip() if post_m else "True"
    return {"fn_name": fn_name, "arg_names": arg_names, "pre": pre, "post": post}


# ---- candidate proposal ------------------------------------------------------
def propose_code_patch(proposer: Proposer, task: dict) -> Candidate:
    text = proposer(_prompt_code_patch(task))
    source = _extract_code(text)
    return Candidate(kind="code_patch", content=source, patch_source=source, proposer_calls=1)


def propose_scaffold(proposer: Proposer, task: dict) -> Candidate:
    scaffold_text = proposer(_prompt_scaffold())
    extra = f"Follow this reasoning approach:\n{scaffold_text}"
    patch_text = proposer(_prompt_code_patch(task, extra_context=extra))
    patch_source = _extract_code(patch_text)
    return Candidate(
        kind="cot_scaffold",
        content=scaffold_text.strip(),
        patch_source=patch_source,
        proposer_calls=2,
        meta={"scaffold_text": scaffold_text.strip()},
    )


def propose_tool(proposer: Proposer, task: dict) -> Candidate:
    tool_text = proposer(_prompt_tool(task))
    tool_source = _extract_code(tool_text)
    extra = f"You may define and call this helper if useful:\n```python\n{tool_source}```"
    patch_text = proposer(_prompt_code_patch(task, extra_context=extra))
    patch_source = _extract_code(patch_text)
    # candidate's final patch must be self-contained: prepend the tool def so
    # verify.py's sandbox sees both regardless of whether the patch re-emitted it.
    full_patch_source = tool_source + "\n" + patch_source
    return Candidate(
        kind="tool",
        content=tool_source,
        patch_source=full_patch_source,
        proposer_calls=2,
        meta={"tool_source": tool_source},
    )


def propose_all(proposer: Proposer, task: dict) -> list[Candidate]:
    """Exactly one candidate per fixed kind -- the "1-3 candidates" from the
    doc collapses cleanly to "one per kind" here (never LLM-invented kinds)."""
    return [
        propose_code_patch(proposer, task),
        propose_scaffold(proposer, task),
        propose_tool(proposer, task),
    ]


# ---- evaluation + promotion gate --------------------------------------------
def evaluate_candidate(
    task: dict,
    candidate: Candidate,
    baseline_holdout_passed: int,
) -> dict:
    """Run the full gate pipeline for one candidate. Returns a dict with every
    field ledger.append() requires except {candidate_id, iter, proposer,
    replay_cmd, parent_id, ts} (the caller fills those in -- this function
    knows nothing about iteration bookkeeping)."""
    task_id = task["task_id"]

    if not candidate.patch_source.strip():
        return {
            "task_id": task_id,
            "kind": candidate.kind,
            "visible_pass": False,
            "holdout_pass": None,
            "sentinel_regressed": None,
            "exploit_or_contract_audit": "unparsable_proposer_output",
            "decision": "rejected",
        }

    exploit_hits = _exploit_scan(candidate.patch_source)
    tool_fuzz_note = "n/a"

    if candidate.kind == "tool":
        parsed = _parse_tool(candidate.content)
        if parsed is None:
            return {
                "task_id": task_id,
                "kind": candidate.kind,
                "visible_pass": False,
                "holdout_pass": None,
                "sentinel_regressed": None,
                "exploit_or_contract_audit": "unparsable_tool_signature",
                "decision": "rejected",
            }
        arg_spec = [{"name": a, "type": "int", "lo": -1000, "hi": 1000} for a in parsed["arg_names"]]
        if not arg_spec:
            tool_fuzz_note = "fuzz_skipped: no args to fuzz"
        else:
            fuzz = verify.contract_fuzz(
                candidate.content,
                parsed["fn_name"],
                arg_spec,
                pre=parsed["pre"],
                post=parsed["post"],
                seed=0,
                time_budget_s=20.0,
            )
            if fuzz["violated"] or fuzz["error"] or fuzz["timed_out"]:
                tool_fuzz_note = f"fuzz_violation: {fuzz.get('violation_reason') or fuzz.get('error') or 'timeout'}"
            else:
                tool_fuzz_note = f"fuzz_pass({fuzz['trials']} trials)"

    if exploit_hits:
        return {
            "task_id": task_id,
            "kind": candidate.kind,
            "visible_pass": False,
            "holdout_pass": None,
            "sentinel_regressed": None,
            "exploit_or_contract_audit": f"exploit_scan_hit: {exploit_hits}",
            "decision": "rejected",
        }

    if candidate.kind == "tool" and tool_fuzz_note.startswith("fuzz_violation"):
        return {
            "task_id": task_id,
            "kind": candidate.kind,
            "visible_pass": False,
            "holdout_pass": None,
            "sentinel_regressed": None,
            "exploit_or_contract_audit": tool_fuzz_note,
            "decision": "rejected",
        }

    visible_result = verify.run_public(task["visible_tests"], candidate.patch_source)
    visible_pass = visible_result["all_passed"]
    if not visible_pass:
        return {
            "task_id": task_id,
            "kind": candidate.kind,
            "visible_pass": False,
            "holdout_pass": None,
            "sentinel_regressed": None,
            "exploit_or_contract_audit": tool_fuzz_note,
            "decision": "rejected",
        }

    sentinel_result = verify.run_public([task["sentinel_check"]], candidate.patch_source)
    sentinel_regressed = not sentinel_result["all_passed"]

    holdout_result = verify.run_holdout(task_id, candidate.patch_source)
    holdout_gain = holdout_result["all_passed"] and holdout_result["passed"] > baseline_holdout_passed
    holdout_pass = bool(holdout_gain)

    decision = "promoted" if (visible_pass and holdout_pass and not sentinel_regressed) else "rejected"
    return {
        "task_id": task_id,
        "kind": candidate.kind,
        "visible_pass": visible_pass,
        "holdout_pass": holdout_pass,
        "sentinel_regressed": sentinel_regressed,
        "exploit_or_contract_audit": tool_fuzz_note,
        "decision": decision,
    }


def baseline_holdout_passed(task: dict) -> int:
    """How many held-out tests the SHIPPED buggy_source happens to pass, used
    as the "fixed cost" baseline a candidate must beat (not just re-pass)."""
    result = verify.run_holdout(task["task_id"], task["buggy_source"])
    return result["passed"]


# ---- one iteration -----------------------------------------------------------
def sample_tasks(all_tasks: list[dict], already_promoted: set[str], max_n: int) -> list[dict]:
    remaining = [t for t in all_tasks if t["task_id"] not in already_promoted]
    pool = remaining if remaining else list(all_tasks)  # v0: cycle back if everything's fixed
    return pool[:max_n]


def run_iteration(
    iter_idx: int,
    proposer: Proposer,
    proposer_name: str,
    all_tasks: list[dict],
    max_tasks_per_iter: int,
    ledger_path: Path | None = None,
) -> list[dict]:
    """Run one improvement iteration; returns the ledger rows appended."""
    already_promoted = ledger.promoted_task_ids(ledger_path)
    batch = sample_tasks(all_tasks, already_promoted, max_tasks_per_iter)
    rows = []
    for task in batch:
        baseline = baseline_holdout_passed(task)
        candidates = propose_all(proposer, task)
        for candidate in candidates:
            evaluation = evaluate_candidate(task, candidate, baseline)
            candidate_id = str(uuid.uuid4())
            row = {
                "candidate_id": candidate_id,
                "iter": iter_idx,
                "proposer": proposer_name,
                "parent_id": None,
                "replay_cmd": f"python experiments/learnos/run_v0.py --replay {candidate_id}",
                **evaluation,
                # extra (non-required) fields: archive the candidate's own content
                # + proposer-call cost, for lineage/reuse (NOT held-out content).
                "content": candidate.content,
                "proposer_calls": candidate.proposer_calls,
            }
            rows.append(ledger.append(row, path=ledger_path))
    return rows


def run_iterations(
    n: int,
    proposer: Proposer,
    proposer_name: str,
    max_tasks_per_iter: int = 6,
    ledger_path: Path | None = None,
    tasks_list: list[dict] | None = None,
) -> dict:
    all_tasks = tasks_list if tasks_list is not None else tasks.load_visible_tasks()
    for i in range(n):
        run_iteration(i, proposer, proposer_name, all_tasks, max_tasks_per_iter, ledger_path)
    return ledger.summarize(ledger_path)
