"""experiments/learnos/audit.py -- Blind-Curator verifier audit (2607.07436) for LearnOS
S+1 (docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md).

Injects KNOWN defects into candidate outputs and runs them through the SAME promotion gate
mining uses (improve.evaluate_candidate, by default) to measure the verifier's FALSE-PASS
RATE: how often the gate promotes something it should have rejected. Per the Blind-Curator
finding this design cites -- a biased/weak judge silently turns off skill acceptance and a
false-pass is not recoverable from the data afterward, it's asymptomatic -- so this audit
must run BEFORE trusting any promotion in a run. If false_pass_rate exceeds a pre-set
threshold, promotion through that verifier is FROZEN for the run (search.py honors
`freeze_promotion` by not growing the shared library even when the ledger records
"promoted" rows -- the ledger stays an honest append-only record either way).

Two defect classes, both pure code transformation -- no live LLM, fully deterministic and
unit-testable:

  1. overfit_to_visible (`inject_overfit_defect`) -- special-cases every literal
     (args -> expected) pair drawn straight from a task's OWN visible_tests, then falls
     through to the task's ORIGINAL buggy_source (renamed, including any internal
     recursive calls, so a recursive task can't accidentally self-heal through the
     wrapper) for every other input. By construction this passes every visible test but
     does not generalize -- exactly "a plausible-looking wrong patch that passes visible
     but not held-out." Needs no golden fix; works for any task in the corpus.

  2. sentinel_breaking (`inject_sentinel_breaking_defect`) -- given a GOLDEN (real,
     correct) fix, wraps it so the literal input used in the task's sentinel_check returns
     a deliberately wrong value while every other input (including held-out) still routes
     to the real golden implementation. A candidate that is a genuine fix everywhere except
     one silently-broken edge case is exactly the "looks right" regression the gate must
     catch via sentinel_regressed. Needs a small embedded golden-fix table (below) --
     audit-only, never imported by improve.py / search.py's mining path.

Both injectors only understand `assert fn(args) == expected` / `assert fn(args) is expected`
shaped test strings (this corpus's own format); a sentinel_check that doesn't match that
shape (e.g. a chained comparison, or `fn(...)[k] == v`) is skipped defensively -- returns
None, never raises -- rather than mis-parsed.

stdlib only (re).
"""
from __future__ import annotations

import re
from typing import Callable

import improve

DEFAULT_THRESHOLD = 0.05

_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)")
_ASSERT_RE = re.compile(r"assert\s+([A-Za-z_][A-Za-z0-9_]*)\((.*?)\)\s*(==|is)\s*(.+?)\s*$")

# Golden (real, correct) fixes for a representative slice of the corpus, used ONLY by the
# sentinel_breaking defect class above. Deliberately NOT the full task set and deliberately
# kept out of tasks.py / improve.py / search.py's reach -- a mining loop that could read this
# table would trivially "solve" every task without learning anything, which is exactly the
# self-deception the held-out isolation discipline (tasks.py's docstring) guards against for
# the private test file; this table gets the same treatment even though it isn't literally
# the held-out data.
GOLDEN_FIXES: dict[str, str] = {
    "off_by_one_range": "def sum_range(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n",
    "wrong_operator_and_or": "def is_valid_age(age):\n    return age >= 0 and age <= 120\n",
    "boundary_empty_list": "def average(xs):\n    return sum(xs) / len(xs) if xs else 0\n",
    "wrong_comparison_direction": "def clamp_min(x, lo):\n    return max(x, lo)\n",
    "string_reverse_off_by_one": "def reverse_str(s):\n    return s[::-1]\n",
    "wrong_index_fencepost": "def get_last(xs):\n    return xs[len(xs) - 1]\n",
    "incorrect_accumulator_init": "def product(xs):\n    total = 1\n    for x in xs:\n        total *= x\n    return total\n",
    "wrong_condition_negation": "def is_even(n):\n    return n % 2 == 0\n",
    "float_int_division": "def half(n):\n    return n / 2\n",
    "recursive_base_case_wrong": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n",
    "sorting_comparator_wrong": "def sort_desc(xs):\n    return sorted(xs, reverse=True)\n",
    "dict_default_missing": "def char_count(s):\n    counts = {}\n    for ch in s:\n        counts[ch] = counts.get(ch, 0) + 1\n    return counts\n",
    "list_slicing_off_by_one": "def first_n(xs, n):\n    return xs[:n]\n",
    "early_return_wrong": "def find_first_negative(xs):\n    for x in xs:\n        if x < 0:\n            return x\n    return None\n",
    "swapped_args_order": "def subtract_from(total, amount):\n    return total - amount\n",
    "wrong_modulo_even_odd_check": "def classify_parity(n):\n    if n % 2 == 0:\n        return 'even'\n    return 'odd'\n",
    "off_by_one_last_n": "def last_n(xs, n):\n    return xs[-n:]\n",
    "wrong_operator_inclusive_bounds": "def in_bounds(x, lo, hi):\n    return lo <= x <= hi\n",
    "accumulator_init_sum": "def total_sum(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n",
    "condition_negation_is_positive": "def is_positive(x):\n    return x > 0\n",
    "comparison_direction_find_max": "def find_max(xs):\n    return max(xs)\n",
    "index_fencepost_first": "def get_first(xs):\n    return xs[0]\n",
    "recursive_base_case_fib": "def fib(n):\n    if n == 0:\n        return 0\n    if n == 1:\n        return 1\n    return fib(n - 1) + fib(n - 2)\n",
    "sorting_comparator_by_length": "def sort_by_length(xs):\n    return sorted(xs, key=len)\n",
    "dict_default_word_freq": "def word_freq(words):\n    counts = {}\n    for w in words:\n        counts[w] = counts.get(w, 0) + 1\n    return counts\n",
    "list_slicing_skip_first": "def skip_first(xs, n):\n    return xs[n:]\n",
    "early_return_first_even": "def first_even(xs):\n    for x in xs:\n        if x % 2 == 0:\n            return x\n    return None\n",
    "swapped_args_percent_of": "def percent_of(part, whole):\n    return part / whole * 100\n",
    "float_int_division_ratio": "def ratio(a, b):\n    return a / b\n",
    "mutable_default_arg": "def append_item(x, lst=None):\n    if lst is None:\n        lst = []\n    lst.append(x)\n    return lst\n",
    "mutable_default_tally": "def tally(label, store=None):\n    if store is None:\n        store = {}\n    store[label] = store.get(label, 0) + 1\n    return store\n",
    "min_max_mixed_up": "def bounded(x, lo, hi):\n    return min(max(x, lo), hi)\n",
    "min_max_mixed_clamp": "def clamp(x, lo, hi):\n    return max(lo, min(x, hi))\n",
    "swapped_return_minmax": "def min_and_max(xs):\n    return (min(xs), max(xs))\n",
}


class AuditError(Exception):
    pass


def _split_top_level(s: str) -> list[str]:
    """Split `s` on top-level commas (depth 0 w.r.t. ([{ }]) ) -- e.g. "[1, 2, 3], 0" ->
    ["[1, 2, 3]", "0"]. Safe for this corpus's literal-only call args (no string args
    contain commas)."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in s:
        if ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def _wrong_value(expected_text: str) -> str:
    """Return Python source for a value guaranteed to differ from `expected_text`'s literal
    value (or a generic distinguishable sentinel if it can't be evaluated statically)."""
    try:
        val = eval(expected_text, {"__builtins__": {}})
    except Exception:
        return "'__LEARNOS_WRONG__'"
    if val is None:
        return "'__LEARNOS_WRONG__'"
    if isinstance(val, bool):
        return repr(not val)
    if isinstance(val, (int, float)):
        return repr(val + 1)
    if isinstance(val, str):
        return repr(val + "_WRONG")
    if isinstance(val, list):
        return repr(val + ["_WRONG"])
    if isinstance(val, dict):
        return "dict(" + repr(val) + ", _WRONG=True)"
    return "'__LEARNOS_WRONG__'"


def inject_overfit_defect(task: dict) -> str | None:
    """Build a patch that special-cases every visible_tests (args -> expected) pair, then
    falls through to the task's own (renamed) buggy_source. Passes visible; does not
    generalize; a gate that promotes this is a false-pass. Returns None (never raises) if
    the buggy_source or visible_tests don't parse into the expected shape."""
    m = _DEF_RE.search(task["buggy_source"])
    if not m:
        return None
    fn_name, params_raw = m.group(1), m.group(2)
    params = [p.strip().split("=")[0].strip() for p in params_raw.split(",") if p.strip()]
    cases: list[tuple[str, str]] = []
    for expr in task["visible_tests"]:
        cm = _ASSERT_RE.match(expr)
        if not cm or cm.group(1) != fn_name:
            continue
        cases.append((cm.group(2), cm.group(4)))
    if not cases:
        return None

    fallback_name = f"_{fn_name}_fallback_orig"
    lines = [f"def {fn_name}({params_raw}):"]
    for args_text, expected_text in cases:
        if params:
            arg_vals = _split_top_level(args_text)
            if len(arg_vals) != len(params):
                continue
            cond = " and ".join(f"({p}) == ({a})" for p, a in zip(params, arg_vals))
        else:
            cond = "True"
        lines.append(f"    if {cond}:")
        lines.append(f"        return {expected_text}")
    lines.append(f"    return {fallback_name}({', '.join(params)})")
    lines.append("")
    # rename EVERY occurrence (including internal recursive calls), not just the def line --
    # otherwise a recursive task's fallback would recurse back into the special-cased
    # wrapper and could accidentally self-heal at the exact visible-tested base cases.
    fallback_src = re.sub(rf"\b{re.escape(fn_name)}\b", fallback_name, task["buggy_source"])
    return "\n".join(lines) + "\n" + fallback_src


def inject_sentinel_breaking_defect(task: dict, golden_source: str) -> str | None:
    """Build a patch that is the real `golden_source` everywhere except the exact input used
    in `task["sentinel_check"]`, where it returns a deliberately wrong value. Returns None
    (never raises) if golden_source or sentinel_check don't parse into the expected shape."""
    m = _DEF_RE.search(golden_source)
    if not m:
        return None
    fn_name, params_raw = m.group(1), m.group(2)
    params = [p.strip().split("=")[0].strip() for p in params_raw.split(",") if p.strip()]
    cm = _ASSERT_RE.match(task["sentinel_check"])
    if not cm or cm.group(1) != fn_name:
        return None
    args_text, expected_text = cm.group(2), cm.group(4)
    if params:
        arg_vals = _split_top_level(args_text)
        if len(arg_vals) != len(params):
            return None
        cond = " and ".join(f"({p}) == ({a})" for p, a in zip(params, arg_vals))
    else:
        cond = "True"

    real_name = f"_{fn_name}_golden_impl"
    lines = [
        f"def {fn_name}({params_raw}):",
        f"    if {cond}:",
        f"        return {_wrong_value(expected_text)}",
        f"    return {real_name}({', '.join(params)})",
        "",
    ]
    golden_renamed = re.sub(rf"\b{re.escape(fn_name)}\b", real_name, golden_source)
    return "\n".join(lines) + "\n" + golden_renamed


GateFn = Callable[[dict, "improve.Candidate", int], dict]


def run_audit(
    task_pool: list[dict],
    gate_fn: GateFn = improve.evaluate_candidate,
    threshold: float = DEFAULT_THRESHOLD,
    golden_fixes: dict[str, str] | None = None,
) -> dict:
    """Run both defect classes over `task_pool` through `gate_fn` (defaults to the REAL
    promotion gate, improve.evaluate_candidate; tests inject a deliberately weakened fake to
    prove this function's false-pass detection itself works). Returns the trial log, the
    false-pass rate, and `freeze_promotion` -- True iff the rate exceeds `threshold`, in
    which case search.py must not grow the shared library from this run's promotions."""
    golden_fixes = GOLDEN_FIXES if golden_fixes is None else golden_fixes
    trials = []
    for task in task_pool:
        baseline = improve.baseline_holdout_passed(task)

        overfit_src = inject_overfit_defect(task)
        if overfit_src:
            candidate = improve.Candidate(
                kind="code_patch", content=overfit_src, patch_source=overfit_src, proposer_calls=0
            )
            result = gate_fn(task, candidate, baseline)
            trials.append(
                {
                    "task_id": task["task_id"],
                    "defect": "overfit_to_visible",
                    "decision": result["decision"],
                    "false_pass": result["decision"] == "promoted",
                }
            )

        golden = golden_fixes.get(task["task_id"])
        if golden:
            sentinel_src = inject_sentinel_breaking_defect(task, golden)
            if sentinel_src:
                candidate = improve.Candidate(
                    kind="code_patch", content=sentinel_src, patch_source=sentinel_src, proposer_calls=0
                )
                result = gate_fn(task, candidate, baseline)
                trials.append(
                    {
                        "task_id": task["task_id"],
                        "defect": "sentinel_breaking",
                        "decision": result["decision"],
                        "false_pass": result["decision"] == "promoted",
                    }
                )

    n_trials = len(trials)
    false_passes = sum(1 for t in trials if t["false_pass"])
    rate = (false_passes / n_trials) if n_trials else 0.0
    return {
        "trials": trials,
        "n_trials": n_trials,
        "false_passes": false_passes,
        "false_pass_rate": rate,
        "threshold": threshold,
        "freeze_promotion": rate > threshold,
    }
