"""experiments/learnos/causal_gate.py -- causal-ablation promotion gate for LearnOS S+1.1
(docs/AIOS_LEARNOS_S1_RESULTS_2026-07-17.md §5, docs/AIOS_AGI_CONCEPTION_2026-07-17.md §10,
docs/ontology/ledger/learning_methods.md §4).

THE DIAGNOSIS THIS FIXES: S+1's promotion gate (improve.evaluate_candidate, still reused
unmodified here) checked only "does the final patch_source pass visible+holdout+sentinel" --
never whether a cot_scaffold/tool candidate's ARTIFACT was causally responsible for that
pass. Two of three tools S+1 mined turned out to be an identity function (`return i`) and a
constant function (`return 1`) with self-evidently-true postconditions -- they rode along on
a code_patch that was already correct on its own, then polluted the shared library, then
polluted B (transfer-holdout) prompts via search.py's Library.best_for fallback. This module
is the fix: nothing enters the gene pool (gene_pool.py) without surviving BOTH of these
checks.

  1. DEGENERACY PRE-FILTER (`is_degenerate_tool`) -- cheap, no subprocess/LLM call. Rejects a
     TOOL candidate outright if its body is a structural identity/constant function (AST-
     based: single `return <arg-name>` or `return <literal>` statement), or if its declared
     POSTCONDITION cannot possibly discriminate a correct implementation from an incorrect
     one -- either the literal string "True" or any expression that never even mentions the
     `result` name it's supposed to be constraining. This exactly catches S+1's two
     documented specimens (`safe_index(xs, i): return i` with `POSTCONDITION: 0 <= result <
     len(xs) and xs[result] == xs[i]` -- vacuous once `result == i` by construction under
     identity; `safe_factorial_base_case(n): return 1` with `POSTCONDITION: result == 1` --
     tautological given the body) before spending any evaluation budget on it.

  2. CAUSAL ABLATION (`check_causal_responsibility`) -- one extra verify.run_holdout call
     (reusing the SAME sanctioned, aggregate-only-return call site improve.py's gate already
     uses -- no new held-out reader) per candidate, running the task WITH the candidate and
     WITHOUT it:
       * tool:     WITHOUT = the exact same patch_source, but with the tool's own body
                   swapped for a poison stub that raises if actually called. If the patch
                   still passes held-out against a poisoned tool, the tool was never on the
                   causal path to the fix -- reject.
       * cot_scaffold: WITHOUT = a fresh code_patch proposer call with NO scaffold context
                   (one extra proposer call, the cost the design brief explicitly accepts
                   for a real ablation, not a self-report). If the bare code_patch does just
                   as well on held-out as the scaffold-guided one, the scaffold gets no
                   causal credit -- reject.
     "WITH strictly beats WITHOUT" = WITH's held-out passed-count is strictly greater than
     WITHOUT's -- not merely "WITH passes", which is exactly the vacuous test S+1 diagnosed.

Neither check ever imports or reads the held-out data file directly -- both route
exclusively through verify.run_holdout, same isolation discipline as every other module in
this package (see tests/test_learnos_s11.py's grep-based structural guarantee).

stdlib only (ast, re).
"""
from __future__ import annotations

import ast
import re

import improve
import verify

_TRIVIAL_POST_STRINGS = {"true", "1==1", "1 == 1", ""}
_RESULT_TOKEN_RE = re.compile(r"\bresult\b")

DEFAULT_ABLATION_TIMEOUT_S = 10.0


class CausalGateError(Exception):
    pass


# ---- 1. degeneracy pre-filter (tool candidates only, cheap, no subprocess/LLM) -----------
def _identity_or_constant_reason(tool_source: str, fn_name: str) -> str:
    """Structural check: the function body (ignoring a leading docstring) is exactly one
    `return <arg-name>` (identity) or `return <literal>` (constant) statement. Returns "" if
    tool_source doesn't parse, fn_name isn't found, or the body isn't that trivial shape."""
    try:
        tree = ast.parse(tool_source)
    except SyntaxError:
        return ""
    fn = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name),
        None,
    )
    if fn is None:
        return ""
    body = [
        stmt for stmt in fn.body
        if not (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        )  # drop a leading docstring, which always carries the PRECONDITION/POSTCONDITION lines
    ]
    if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
        return ""
    ret = body[0].value
    arg_names = {a.arg for a in fn.args.args}
    if isinstance(ret, ast.Name) and ret.id in arg_names:
        return "identity_function"
    if isinstance(ret, ast.Constant):
        return "constant_function"
    return ""


def _postcondition_is_vacuous(post: str) -> bool:
    """A postcondition that is literally "True" or never even references `result` cannot
    discriminate a correct implementation from an incorrect one -- it is trivially
    satisfiable by construction, independent of what the function actually computes."""
    normalized = (post or "").strip()
    if normalized.lower() in _TRIVIAL_POST_STRINGS:
        return True
    if not _RESULT_TOKEN_RE.search(normalized):
        return True
    return False


def is_degenerate_tool(tool_source: str, fn_name: str, post: str) -> tuple[bool, str]:
    """Returns (is_degenerate, reason). reason is "" iff not degenerate. Pure/cheap -- no
    subprocess, no network, no proposer call; safe to run on every tool candidate before any
    ablation spend."""
    body_reason = _identity_or_constant_reason(tool_source, fn_name)
    if body_reason:
        return True, body_reason
    if _postcondition_is_vacuous(post):
        return True, "vacuous_postcondition"
    return False, ""


# ---- 2. causal ablation -------------------------------------------------------------------
def _poison_stub(tool_source: str, fn_name: str) -> str:
    """A same-signature replacement for `fn_name` that raises unconditionally -- the WITHOUT
    control for a tool candidate. If tool_source doesn't parse or fn_name isn't found, falls
    back to a `*args, **kwargs` stub (still poisoned, just signature-agnostic)."""
    try:
        tree = ast.parse(tool_source)
        fn = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name),
            None,
        )
        if fn is not None:
            params = ast.unparse(fn.args)
            return (
                f"def {fn_name}({params}):\n"
                "    raise RuntimeError('learnos causal-ablation poison stub')\n"
            )
    except SyntaxError:
        pass
    return (
        f"def {fn_name}(*args, **kwargs):\n"
        "    raise RuntimeError('learnos causal-ablation poison stub')\n"
    )


def _ablate_tool_source(patch_source: str, tool_source: str, fn_name: str) -> str:
    """Build the WITHOUT patch_source for a tool candidate: same patch, tool body poisoned.
    If tool_source's exact text isn't found embedded in patch_source (e.g. a reuse candidate
    whose patch_source was built by concatenation, which is always the case in this
    package -- see improve.propose_tool / search.propose_reuse_tool), the poison stub is
    prepended so any call to fn_name still resolves to the poisoned version."""
    poisoned = _poison_stub(tool_source, fn_name)
    if tool_source.strip() and tool_source in patch_source:
        return patch_source.replace(tool_source, poisoned, 1)
    return poisoned + "\n" + patch_source


def run_tool_ablation(
    task_id: str, patch_source: str, tool_source: str, fn_name: str,
    timeout: float = DEFAULT_ABLATION_TIMEOUT_S,
) -> dict:
    """Run the task's held-out tests WITH the real tool and WITHOUT it (poisoned). Returns
    {"with_passed", "without_passed", "causally_responsible"} -- causally_responsible iff
    WITH strictly beats WITHOUT (not merely "WITH passes", which is the vacuous test S+1's
    gate ran)."""
    without_source = _ablate_tool_source(patch_source, tool_source, fn_name)
    with_result = verify.run_holdout(task_id, patch_source, timeout=timeout)
    without_result = verify.run_holdout(task_id, without_source, timeout=timeout)
    return {
        "with_passed": with_result["passed"],
        "without_passed": without_result["passed"],
        "causally_responsible": with_result["passed"] > without_result["passed"],
    }


def run_scaffold_ablation(task: dict, proposer, timeout: float = DEFAULT_ABLATION_TIMEOUT_S) -> dict:
    """WITHOUT-scaffold control: a fresh code_patch proposer call with NO extra_context (one
    extra proposer call). Returns {"without_passed"}."""
    text = proposer(improve._prompt_code_patch(task))
    without_source = improve._extract_code(text)
    if not without_source.strip():
        return {"without_passed": 0}
    result = verify.run_holdout(task["task_id"], without_source, timeout=timeout)
    return {"without_passed": result["passed"]}


def check_causal_responsibility(task: dict, candidate: "improve.Candidate", proposer=None) -> dict:
    """Top-level entry point: candidate.kind must be "cot_scaffold" or "tool". Returns
    {"causally_responsible": bool, "mode": str, "with_passed": int, "without_passed": int}.

    tool: no proposer needed (ablation is a pure code transformation + two verify.run_holdout
    calls). cot_scaffold: requires `proposer` (the WITHOUT control needs a real regeneration,
    not a self-report -- raises CausalGateError if omitted).
    """
    if candidate.kind not in ("cot_scaffold", "tool"):
        raise CausalGateError(
            f"causal ablation only applies to cot_scaffold/tool candidates, got {candidate.kind!r}"
        )
    with_result = verify.run_holdout(task["task_id"], candidate.patch_source)
    with_passed = with_result["passed"]

    if candidate.kind == "tool":
        parsed = improve._parse_tool(candidate.content)
        if parsed is None:
            return {
                "causally_responsible": False, "mode": "tool",
                "with_passed": with_passed, "without_passed": with_passed,
                "reason": "unparsable_tool_signature",
            }
        without = run_tool_ablation(task["task_id"], candidate.patch_source, candidate.content, parsed["fn_name"])
        return {
            "causally_responsible": with_passed > without["without_passed"],
            "mode": "tool", "with_passed": with_passed, "without_passed": without["without_passed"],
        }

    # cot_scaffold
    if proposer is None:
        raise CausalGateError("scaffold causal ablation requires a proposer for the WITHOUT control call")
    without = run_scaffold_ablation(task, proposer)
    return {
        "causally_responsible": with_passed > without["without_passed"],
        "mode": "cot_scaffold", "with_passed": with_passed, "without_passed": without["without_passed"],
    }
