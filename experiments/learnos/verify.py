"""experiments/learnos/verify.py -- the EXTERNAL verifier (LearnOS v0, §5/§6 of
docs/AIOS_AGI_CONCEPTION_2026-07-17.md).

This is the ONLY module in experiments/learnos/ that reads the held-out test
data file. improve.py never imports the private loader below and never opens
that path -- see tasks.py's docstring and
tests/test_learnos.py::test_improver_source_never_references_held_out_path for
the structural (grep-enforced, not just commented) guarantee.

Two independent jobs, per the AIOS_AGI_CONCEPTION discipline that a self-judging
loop is theater:
  1. ``run_holdout`` / ``run_public`` -- run a candidate's patched source against
     a task's tests in a FRESH subprocess: cwd-bounded (throwaway tempdir),
     timed out, network sockets monkeypatched to raise before the candidate
     code runs. ``run_holdout`` deliberately returns ONLY aggregate pass
     counts (never the held-out assertion text or per-test error strings) so
     that even the promotion ledger -- which IS fed back to the proposer as
     context in later iterations -- cannot leak held-out content back to the
     improver.
  2. ``contract_fuzz`` -- property-based fuzzing (<30s) for a synthesized TOOL
     candidate: given declared PRECONDITION/POSTCONDITION assertions, generate
     random inputs and try to violate the postcondition. Runs in the same
     sandboxed subprocess. Guards against "buggy tool silently corrupts the
     library" (nemotron-panel critique, §5b).

stdlib only (subprocess, json, random, string, inspect, tempfile, time).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_HELD_OUT_PATH = _DATA_DIR / "tasks_held_out.json"

DEFAULT_TIMEOUT_S = 10.0
_RESULT_MARKER = "###LEARNOS_VERIFY_RESULT###"

_SANDBOX_PRELUDE = textwrap.dedent(
    """\
    import socket as _learnos_socket

    class _LearnOSNoNetwork(OSError):
        pass

    def _learnos_blocked(*_a, **_k):
        raise _LearnOSNoNetwork("network disabled in learnos verify sandbox")

    _learnos_socket.socket.connect = _learnos_blocked
    _learnos_socket.socket.connect_ex = _learnos_blocked
    _learnos_socket.create_connection = _learnos_blocked
    """
)


class VerifyError(Exception):
    """Verifier infrastructure error (not a candidate failure)."""


# ---- held-out loading (ONLY reader in this package) -------------------------
def _load_held_out(task_id: str) -> list[str]:
    data = json.loads(_HELD_OUT_PATH.read_text(encoding="utf-8"))
    if task_id not in data:
        raise VerifyError(f"no held-out tests for task_id={task_id!r}")
    return data[task_id]


# ---- sandboxed subprocess execution -----------------------------------------
def _build_test_script(candidate_source: str, test_exprs: list[str]) -> str:
    lines = [_SANDBOX_PRELUDE, candidate_source, "", "__learnos_results = []"]
    for t in test_exprs:
        body = textwrap.indent(t, "    ")
        lines.append(
            "try:\n"
            f"{body}\n"
            "    __learnos_results.append({'ok': True, 'error_type': None})\n"
            "except Exception as _learnos_e:\n"
            "    __learnos_results.append({'ok': False, 'error_type': type(_learnos_e).__name__})\n"
        )
    lines.append("import json as _learnos_json")
    lines.append(f"print({_RESULT_MARKER!r} + _learnos_json.dumps(__learnos_results))")
    return "\n".join(lines)


def _run_script(script: str, timeout: float) -> dict:
    """Execute `script` as a subprocess in a throwaway cwd-bounded tempdir.
    Returns {"results": [...] | None, "timed_out": bool, "error": str|None}."""
    with tempfile.TemporaryDirectory(prefix="learnos_sandbox_") as td:
        script_path = Path(td) / "candidate.py"
        script_path.write_text(script, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, script_path.name],
                cwd=td,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={"PATH": "/usr/bin:/bin"},  # minimal env, no proxy/creds leak
            )
        except subprocess.TimeoutExpired:
            return {"results": None, "timed_out": True, "error": "timeout"}
        if proc.returncode != 0:
            idx = proc.stdout.rfind(_RESULT_MARKER)
            if idx == -1:
                return {
                    "results": None,
                    "timed_out": False,
                    "error": f"process exited {proc.returncode}: {proc.stderr.strip()[-500:]}",
                }
            # candidate raised at import/exec time AFTER emitting partial output is not
            # expected given the try/except wrapping, but stay defensive.
        idx = proc.stdout.rfind(_RESULT_MARKER)
        if idx == -1:
            return {
                "results": None,
                "timed_out": False,
                "error": f"no result marker; stderr={proc.stderr.strip()[-500:]}",
            }
        try:
            results = json.loads(proc.stdout[idx + len(_RESULT_MARKER):])
        except json.JSONDecodeError as e:
            return {"results": None, "timed_out": False, "error": f"malformed result json: {e}"}
        return {"results": results, "timed_out": False, "error": None}


def run_holdout(task_id: str, candidate_source: str, timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    """Run candidate_source against task_id's held-out tests. Returns ONLY
    aggregate counts -- never test source or per-test error strings -- since
    this result is archived in the ledger, which is later fed back to the
    proposer as context (see improve.py); leaking held-out content through
    that channel would defeat the isolation just as surely as importing it
    directly would.
    """
    held_out = _load_held_out(task_id)
    script = _build_test_script(candidate_source, held_out)
    outcome = _run_script(script, timeout)
    if outcome["error"] or outcome["timed_out"]:
        return {
            "total": len(held_out),
            "passed": 0,
            "all_passed": False,
            "timed_out": outcome["timed_out"],
            "error": outcome["error"],
        }
    results = outcome["results"]
    passed = sum(1 for r in results if r["ok"])
    return {
        "total": len(held_out),
        "passed": passed,
        "all_passed": passed == len(held_out),
        "timed_out": False,
        "error": None,
    }


def run_public(test_exprs: list[str], candidate_source: str, timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    """Run candidate_source against a caller-supplied, NON-secret list of test
    expressions (visible_tests or a sentinel_check) in the same sandbox. Since
    these tests are not secret, per-test detail (error type) is safe to
    return."""
    script = _build_test_script(candidate_source, test_exprs)
    outcome = _run_script(script, timeout)
    if outcome["error"] or outcome["timed_out"]:
        return {
            "total": len(test_exprs),
            "passed": 0,
            "all_passed": False,
            "timed_out": outcome["timed_out"],
            "error": outcome["error"],
            "failures": [],
        }
    results = outcome["results"]
    passed = sum(1 for r in results if r["ok"])
    failures = [
        {"index": i, "error_type": r["error_type"]} for i, r in enumerate(results) if not r["ok"]
    ]
    return {
        "total": len(test_exprs),
        "passed": passed,
        "all_passed": passed == len(test_exprs),
        "timed_out": False,
        "error": None,
        "failures": failures,
    }


# ---- contract fuzzing for synthesized tools ---------------------------------
_ARG_GENERATORS = {
    "int": lambda spec: f"random.randint({spec.get('lo', -100)}, {spec.get('hi', 100)})",
    "float": lambda spec: f"round(random.uniform({spec.get('lo', -100.0)}, {spec.get('hi', 100.0)}), 4)",
    "str": lambda spec: (
        f"''.join(random.choice(string.ascii_letters) for _ in range(random.randint(0, {spec.get('maxlen', 8)})))"
    ),
    "list_int": lambda spec: (
        f"[random.randint({spec.get('lo', -20)}, {spec.get('hi', 20)}) "
        f"for _ in range(random.randint(0, {spec.get('maxlen', 6)}))]"
    ),
    "bool": lambda _spec: "random.choice([True, False])",
}


def contract_fuzz(
    tool_source: str,
    fn_name: str,
    arg_spec: list[dict],
    pre: str = "True",
    post: str = "True",
    seed: int = 0,
    time_budget_s: float = 25.0,
    max_trials: int = 2000,
    timeout: float = 30.0,
) -> dict:
    """Property-based fuzz: generate random inputs per arg_spec (stdlib
    `random`/`string`, no hypothesis dependency), skip any that fail `pre`,
    call fn_name(**args), and check `post` (which may reference `result`).
    <30s wall budget, runs inside the same no-network/cwd-bounded/timeout
    sandbox as run_holdout/run_public so a buggy or adversarial candidate tool
    can't do host damage while being fuzzed.

    arg_spec: list of {"name": str, "type": one of _ARG_GENERATORS, ...bounds}.
    pre/post: Python boolean expressions evaluated with the generated args (by
    name) in scope; `post` additionally sees `result`.

    Returns {"violated": bool, "trials": int, "counterexample": dict|None,
             "timed_out": bool, "error": str|None}.
    """
    if time_budget_s > 29.0:
        raise VerifyError("contract_fuzz time_budget_s must stay under the 30s guard")
    for spec in arg_spec:
        if spec.get("type") not in _ARG_GENERATORS:
            raise VerifyError(f"unsupported arg_spec type: {spec.get('type')!r}")

    # Built as an explicit line list (not textwrap.dedent over an f-string) --
    # dedent computes ONE common indent over the whole final string, and the
    # arg-generator lines below carry their own fixed 8-space indent, which
    # would corrupt dedent's margin calculation for the surrounding template.
    fuzz_lines = [
        "import random, string, time, json",
        f"random.seed({seed})",
        f"_deadline = time.monotonic() + {time_budget_s}",
        "_trials = 0",
        "_violated = False",
        "_counterexample = None",
        "_violation_reason = None",
        f"while time.monotonic() < _deadline and _trials < {max_trials}:",
        "    args = {}",
    ]
    for spec in arg_spec:
        name = spec["name"]
        fuzz_lines.append(f"    args[{name!r}] = {_ARG_GENERATORS[spec['type']](spec)}")
    # pre/post are evaluated via eval() with `args` (and, for post, `result` too)
    # as the namespace -- NOT spliced in as bare-name source -- so `pre="lo <= hi"`
    # correctly resolves against args['lo']/args['hi'] regardless of arg names.
    fuzz_lines += [
        "    try:",
        f"        if not eval({pre!r}, {{}}, args):",
        "            continue",
        "    except Exception:",
        "        continue",
        "    _trials += 1",
        "    try:",
        f"        result = {fn_name}(**args)",
        "    except Exception as _e:",
        "        _violated = True",
        "        _counterexample = dict(args)",
        "        _violation_reason = 'tool raised: ' + repr(_e)",
        "        break",
        "    try:",
        f"        ok = bool(eval({post!r}, {{}}, dict(args, result=result)))",
        "    except Exception as _e:",
        "        _violated = True",
        "        _counterexample = dict(args)",
        "        _violation_reason = 'postcondition raised: ' + repr(_e)",
        "        break",
        "    if not ok:",
        "        _violated = True",
        "        _counterexample = dict(args)",
        "        _violation_reason = 'postcondition false'",
        "        break",
        "print(" + repr(_RESULT_MARKER) + " + json.dumps({",
        "    'violated': _violated, 'trials': _trials,",
        "    'counterexample': _counterexample, 'violation_reason': _violation_reason,",
        "}))",
    ]
    fuzz_script = "\n".join(fuzz_lines)
    script = _SANDBOX_PRELUDE + "\n" + tool_source + "\n\n" + fuzz_script
    outcome = _run_script(script, timeout)
    if outcome["error"] or outcome["timed_out"]:
        return {
            "violated": True,
            "trials": 0,
            "counterexample": None,
            "timed_out": outcome["timed_out"],
            "error": outcome["error"],
        }
    r = outcome["results"]
    return {
        "violated": r["violated"],
        "trials": r["trials"],
        "counterexample": r["counterexample"],
        "violation_reason": r.get("violation_reason"),
        "timed_out": False,
        "error": None,
    }
