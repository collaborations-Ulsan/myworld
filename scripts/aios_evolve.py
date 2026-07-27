#!/usr/bin/env python3
"""AIOS Evolve — the evolutionary selection organ (mutate -> externally score ->
select -> diversify -> record lineage). ORGAN BUILD ONLY: this module makes no
compounding claim and promotes nothing by itself.

Contract: docs/consultations/VERDICT-mathematical-tricks-for-failed-experiments.md.
The mathematics from agy_workspace/MATHEMATICAL_TRICKS_FOR_FAILED_EXPERIMENTS.md
is ADOPTED here; its original target (resuscitating sheaf/GoEN similarity
geometry) is REJECTED on measured evidence and is NOT revived here. The adopted
pieces are pointed at the problem the verdict names as real: discrete keep/drop
selection over candidate artifacts, where the outcome signal is EXTERNAL
(sandboxed unit-test execution), not an inverted proxy.

The loop (evolve):
  1. generate_variants      — MUTATION. A pluggable substrate (NIM REST /
                              codex-oss subprocess / agy subprocess / local
                              ollama REST) proposes candidate repairs for a
                              failing artifact. Honest degradation: an
                              unreachable substrate returns a RECORDED failure,
                              never a fabricated candidate; if every substrate
                              fails, a deterministic no-LLM perturbation set
                              keeps the organ testable offline.
  2. fitness                — EXTERNAL SCORING. Each candidate + the artifact's
                              unit test runs inside aios_sandbox
                              .run_untrusted_code (no network, privacy dirs
                              invisible, fail closed). Fitness = tests passed /
                              total, derived ONLY from sandbox exit codes; a
                              candidate that fails to run scores a hard 0. No
                              working sandbox engine -> REFUSE to evaluate
                              (nothing executes).
  3. contrastive_robustness — the adopted contrastive-invariance idea as input
                              PROPERTY FUZZING: transform the candidate's
                              inputs (boundary values, sign flips, empty/large
                              inputs — deterministic, seeded) and require the
                              candidate to keep running deterministically.
                              Reported SEPARATELY from fitness; targets the
                              skill gate's known weakness ("syntactic
                              containment != semantic competence").
  4. gumbel_softmax_select  — temperature-controlled stochastic selection over
                              the discrete candidate set (Gumbel-max trick).
                              Purpose: avoid the degenerate argmax/constant
                              collapse the source document correctly names for
                              discrete choices.
  5. sinkhorn_normalize     — Sinkhorn-Knopp entropy-regularized normalization
                              over (origin-group x candidate) scores, used so
                              the RETAINED set stays diverse across generator
                              groups instead of collapsing to "keep everything
                              from the winner / keep nothing". Its role here is
                              anti-degeneracy, not optimal transport for its
                              own sake.
  6. lineage                — every candidate, verdict, selection, and refusal
                              is APPENDED to .aios/evolve/lineage.jsonl. The
                              file only ever grows.

ANTI-REWARD-HACKING INVARIANT (three distinct roles, recorded in every output):
  generator — the substrate (or the offline perturbation set). Proposes code.
              It never scores itself and never edits the test.
  verifier  — the artifact's unit test. External to the generator; this module
              executes it verbatim and never modifies it.
  scorer    — aios_sandbox.run_untrusted_code exit codes. OS-enforced; the
              generator has no channel into the score except by producing code
              that actually passes.

PROPOSE, NEVER PROMOTE: survivors are proposals only. Nothing here writes into
scripts/ or the skill registry; registration must still go through the existing
aios_skills.register sandbox+unit-test gate, invoked explicitly by an operator.

HONEST LIMITATIONS (say what the math does and does NOT buy here):
  - Gumbel-Softmax and Sinkhorn operate on a SMALL DISCRETE candidate set with
    NO learned parameters. No gradient flows anywhere in this module. Gumbel
    here is exactly the Gumbel-max sampling trick (principled
    temperature-controlled exploration vs argmax collapse); Sinkhorn is a
    balanced-marginals normalizer (diversity across groups vs winner-take-all).
    Neither makes anything "differentiable end-to-end" in this setting, and
    neither can rescue a selection whose underlying signal is wrong — the
    signal here is sandboxed test execution, which is external and real.
  - The scorer trusts sandbox exit codes: candidate code runs in the SAME
    process as its test, so a hostile candidate could exit(0) before asserts
    run. This is the same trust posture as the aios_skills gate; the
    robustness fuzz narrows (a constant/exiting candidate fails transformed
    probes) but does not fully close it.
  - Robustness is an ORACLE-FREE property check (runs without crashing +
    deterministic output under input transformations). It measures fragility,
    not semantic correctness; a correct function with a legitimately partial
    domain scores below 1.0. Compare candidates against each other, not
    against an absolute bar.
  - The offline perturbation set is single-token operator swaps — a smoke-test
    fallback so the organ works with zero LLMs, not a serious repair engine.
  - Fitness granularity is per-top-level-assert of the unit test; a test with
    one assert yields a 0/1 signal.

CLI (the impure edge — supplies the real clock):
  python3 scripts/aios_evolve.py run --file artifact.json
      [--substrate nim|codex-oss|agy|ollama|offline] [--model M]
      [--rounds R] [--n N] [--timeout S] [--fuzz-k K]
      [--temperature T] [--seed S] [--lineage PATH]
  python3 scripts/aios_evolve.py lineage [--tail N] [--lineage PATH]
  python3 scripts/aios_evolve.py report [--lineage PATH]

Artifact JSON: {"name", "code", "unit_test", "error"?, "entry"?,
"example_inputs"?} — entry/example_inputs feed the robustness fuzz.

Secrets: the NVIDIA key is resolved at call time by aios_llm_client
(_read_nvidia_api_key: env, then ~/.config/nvidia/api.env), placed only in the
Authorization header, and never logged, printed, or recorded here.

Stdlib + urllib only (via aios_llm_client's stdlib transport). `now` is always
caller-supplied; pure logic never reads the wall clock for decisions.
Schema: aios.evolve.v1 family.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_llm_client as _llm  # noqa: E402 — one shared OpenAI-compat transport + key reader
import aios_sandbox as _sandbox  # noqa: E402 — the OS-enforced scoring boundary

ROOT = Path(__file__).resolve().parents[1]
LINEAGE = ROOT / ".aios" / "evolve" / "lineage.jsonl"

SCHEMA = "aios.evolve.v1"
CANDIDATE_SCHEMA = "aios.evolve.candidate.v1"
LINEAGE_SCHEMA = "aios.evolve.lineage.v1"

SUBSTRATES = ("nim", "codex-oss", "agy", "ollama", "offline")
_DEFAULT_MODELS = {
    "nim": "deepseek-ai/deepseek-v4-pro",     # frontier open weights on NIM (verified reachable 2026-07-27)
    "ollama": "qwen3-coder:30b",              # verified agentic local model on this box
    "codex-oss": "qwen3-coder:30b",           # only local-provider path that works (quota outage)
    "agy": "gemini-3.1-pro-high",
    "offline": None,
}
DEFAULT_SANDBOX_TIMEOUT = 10.0
DEFAULT_FUZZ_K = 8
DEFAULT_FUZZ_SEED = 20260727
_CLI_TIMEOUT_S = 780.0  # codex/agy subprocess ceiling (agy --print-timeout 12m)

_FENCE_RE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL)

# Deterministic no-LLM perturbations: ordered single-occurrence operator swaps.
# A smoke-test fallback (see module limitations), NOT a repair engine.
_OFFLINE_SWAPS: tuple[tuple[str, str], ...] = (
    ("-", "+"), ("-", "*"), ("+", "-"), ("+", "*"), ("*", "+"), ("*", "-"),
    ("//", "/"), ("/", "//"), ("<=", "<"), ("<", "<="), (">=", ">"),
    (">", ">="), ("==", "!="), ("!=", "=="),
)
_OP_NEIGHBORS = set("+-*/%=<>!")


def _hash16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _short(text: str | None, n: int = 200) -> str | None:
    if text is None:
        return None
    text = " ".join(str(text).split())
    return text[:n] or None


def roles_record(generator_label: str) -> dict:
    """The anti-reward-hacking invariant as data: three DISTINCT roles."""
    return {
        "generator": f"{generator_label} — proposes candidate repairs; never scores itself, never edits the test",
        "verifier": "artifact unit_test — external to the generator; executed verbatim, never modified here",
        "scorer": "aios_sandbox.run_untrusted_code — OS-enforced sandbox exit codes only (no network, fail closed)",
    }


def _infer_entry(code: str) -> str | None:
    """Primary entry point = LAST top-level function (aios_skills convention)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    fns = [n for n in tree.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return fns[-1].name if fns else None


def make_candidate(code: str, artifact: dict, *, origin: str = "manual",
                   model: str | None = None) -> dict:
    """One candidate record: proposed code + the EXTERNAL verifier it must
    face (the artifact's unit test, copied verbatim) + fuzz metadata."""
    code = code.rstrip() + "\n"
    return {
        "schema": CANDIDATE_SCHEMA,
        "code": code,
        "hash": _hash16(code),
        "origin": origin,
        "model": model,
        "unit_test": artifact["unit_test"],
        "entry": artifact.get("entry") or _infer_entry(code),
        "example_inputs": artifact.get("example_inputs"),
    }


# ---------------------------------------------------------------------------
# 1. generate_variants — the mutation operator (pluggable substrate)
# ---------------------------------------------------------------------------

def _repair_prompt(artifact: dict, n: int) -> str:
    error = artifact.get("error") or "(no error text recorded — the unit test fails)"
    return (
        f"You are a code-repair engine. The Python code below FAILS its unit test.\n"
        f"Produce exactly {n} DIFFERENT candidate repaired versions of the FULL code.\n"
        f"Output ONLY fenced python code blocks (```python ... ```), one block per "
        f"candidate, {n} blocks total. Each block must contain the complete repaired "
        f"code (all needed defs/imports). Do NOT include the unit test, prints, or "
        f"commentary inside the blocks.\n\n"
        f"## failing code\n```python\n{artifact['code']}\n```\n\n"
        f"## unit test (external verifier — you may NOT modify it)\n"
        f"```python\n{artifact['unit_test']}\n```\n\n"
        f"## observed error\n{error}\n"
    )


def _parse_code_blocks(text: str) -> list[str]:
    """Fenced python blocks that at least parse; order kept, duplicates dropped."""
    out: list[str] = []
    seen: set[str] = set()
    for block in _FENCE_RE.findall(text or ""):
        code = block.strip()
        if not code:
            continue
        try:
            ast.parse(code)
        except SyntaxError:
            continue
        h = _hash16(code)
        if h not in seen:
            seen.add(h)
            out.append(code)
    return out


def _run_cli(argv: list[str], timeout: float) -> tuple[str | None, str | None]:
    """(stdout, None) on success, (None, reason) on honest failure. stdin is
    CLOSED (verified trap: codex-oss hangs on open stdin)."""
    try:
        proc = subprocess.run(argv, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return None, f"{argv[0]}: not installed on this box"
    except subprocess.TimeoutExpired:
        return None, f"{argv[0]}: timed out after {timeout:.0f}s"
    except OSError as exc:
        return None, f"{argv[0]}: launch failed ({exc.__class__.__name__})"
    if not (proc.stdout or "").strip():
        return None, (f"{argv[0]}: exit {proc.returncode}, empty stdout "
                      f"[{_short(proc.stderr, 160)}]")
    return proc.stdout, None


def _substrate_generate(substrate: str, model: str,
                        prompt: str) -> tuple[str | None, str | None]:
    """One generation attempt on one substrate: (response_text, None) or
    (None, recorded_failure). Never fabricates output."""
    if substrate in ("nim", "ollama"):
        if substrate == "nim":
            ep = _llm.Endpoint("nvidia_nim", _llm._NIM_BASE_URL, model,
                               needs_key=True,
                               key_fn=_llm._read_nvidia_api_key, timeout=120)
        else:
            base = os.environ.get("AIOS_OLLAMA_BASE_URL",
                                  _llm._OLLAMA_DEFAULT_BASE_URL)
            ep = _llm.Endpoint("local_ollama", base, model, timeout=180)
        res = _llm.LLMClient(endpoints=[ep]).chat(
            [{"role": "user", "content": prompt}])
        if not res.ok or not res.text.strip():
            return None, _short(res.error or res.fallback_reason
                                or "empty response", 300)
        return res.text, None
    if substrate == "codex-oss":
        # Verified invocation: default reasoning xhigh is rejected by ollama and
        # qwen3-coder:30b has no thinking -> model_reasoning_effort=none required.
        argv = ["codex", "exec", "--oss", "--local-provider", "ollama",
                "-m", model, "-c", "model_reasoning_effort=none", prompt]
        return _run_cli(argv, _CLI_TIMEOUT_S)
    if substrate == "agy":
        argv = ["agy", "--model", model, "--effort", "high",
                "--print-timeout", "12m", "-p", prompt]
        return _run_cli(argv, _CLI_TIMEOUT_S)
    return None, f"unknown substrate {substrate!r}"


def _offline_perturbations(code: str, n: int) -> list[str]:
    """Deterministic single-occurrence operator swaps, in fixed table order.
    No randomness, no network, no LLM — the always-available floor."""
    out: list[str] = []
    seen = {_hash16(code)}
    for old, new in _OFFLINE_SWAPS:
        start = 0
        while len(out) < n:
            pos = code.find(old, start)
            if pos < 0:
                break
            start = pos + 1
            if len(old) == 1:  # skip composite operators (** // <= += == ...)
                prev_ch = code[pos - 1] if pos > 0 else ""
                next_ch = code[pos + 1] if pos + 1 < len(code) else ""
                if prev_ch in _OP_NEIGHBORS or next_ch in _OP_NEIGHBORS:
                    continue
            mutated = code[:pos] + new + code[pos + len(old):]
            try:
                ast.parse(mutated)
            except SyntaxError:
                continue
            h = _hash16(mutated.rstrip() + "\n")
            if h not in seen:
                seen.add(h)
                out.append(mutated)
        if len(out) >= n:
            break
    return out[:n]


def generate_variants(artifact: dict, n: int, *, substrate: str,
                      model: str | None, now: float) -> dict:
    """MUTATION OPERATOR: ask `substrate` for n candidate repairs of a failing
    artifact. Honest degradation: unreachable/empty substrates land in
    `substrate_failures` (never a fabricated candidate); if no substrate
    produced code, the deterministic offline perturbation set is the recorded
    fallback so the organ still works with zero LLMs."""
    for field in ("code", "unit_test"):
        if not isinstance(artifact.get(field), str) or not artifact[field].strip():
            raise ValueError(f"artifact needs a non-empty string field {field!r}")
    if n <= 0:
        raise ValueError("n must be >= 1")
    if substrate not in SUBSTRATES:
        raise ValueError(f"substrate must be one of {SUBSTRATES}")
    model = model or _DEFAULT_MODELS[substrate]

    failures: list[dict] = []
    codes: list[str] = []
    origin = substrate
    fallback_used = False

    if substrate != "offline":
        text, err = _substrate_generate(substrate, model, _repair_prompt(artifact, n))
        if err is not None:
            failures.append({"substrate": substrate, "model": model, "error": err})
        else:
            codes = _parse_code_blocks(text)
            if not codes:
                failures.append({"substrate": substrate, "model": model,
                                 "error": "no parsable fenced python blocks "
                                          f"in response (len={len(text)})"})
    if substrate == "offline" or not codes:
        if substrate != "offline":
            fallback_used = True
        origin = "offline-perturb"
        codes = _offline_perturbations(artifact["code"], n)

    candidates = []
    seen: set[str] = set()
    for code in codes[:n]:
        cand = make_candidate(code, artifact, origin=origin,
                              model=model if origin == substrate else None)
        if cand["hash"] not in seen:
            seen.add(cand["hash"])
            candidates.append(cand)
    return {
        "schema": SCHEMA, "kind": "generation", "ts": now,
        "substrate": substrate, "model": model, "requested": n,
        "candidates": candidates, "substrate_failures": failures,
        "fallback_used": fallback_used,
        "roles": roles_record(
            "offline-perturb (deterministic, no LLM)" if origin == "offline-perturb"
            else f"{substrate}:{model}"),
    }


# ---------------------------------------------------------------------------
# 2. fitness — EXTERNAL scoring inside the OS sandbox (fail closed)
# ---------------------------------------------------------------------------

def _test_units(unit_test: str) -> list[str]:
    """Per-assert test programs: for each top-level assert, the non-assert
    statements that precede it + that assert. Empty when there is no
    top-level assert (caller falls back to one whole-test unit)."""
    tree = ast.parse(unit_test)
    lines = unit_test.splitlines()

    def seg(node: ast.stmt) -> str:
        return "\n".join(lines[node.lineno - 1:node.end_lineno])

    units: list[str] = []
    preamble: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assert):
            units.append("\n".join([*preamble, seg(node)]))
        else:
            preamble.append(seg(node))
    return units


def _sandbox_run(program: str, *, timeout: float, now: float | None,
                 receipt_log) -> _sandbox.SandboxResult:
    return _sandbox.run_untrusted_code(program, lang="python", timeout=timeout,
                                       now=now, receipt_log=receipt_log)


def fitness(candidates: list[dict], *, sandbox_timeout: float = DEFAULT_SANDBOX_TIMEOUT,
            now: float | None = None,
            receipt_log=_sandbox.DEFAULT_RECEIPT_LOG) -> dict:
    """EXTERNAL SCORER. Each candidate's unit test executes inside
    aios_sandbox.run_untrusted_code; fitness = tests passed / total, derived
    ONLY from sandbox exit codes. Hard 0 for a candidate that fails to run.
    No working sandbox engine -> REFUSES to evaluate: nothing executes,
    fitness is None (refusal is not a measured zero). The generator never
    scores itself — see the `roles` field of the returned record."""
    if _sandbox.pick_engine() == "none":
        return {
            "schema": SCHEMA, "kind": "fitness", "refused": True,
            "reason": "refused (fail closed): no working sandbox engine — "
                      "nothing was executed",
            "results": [{"hash": c.get("hash"), "origin": c.get("origin"),
                         "fitness": None, "tests_passed": None,
                         "tests_total": None, "ran": False, "proposable": False,
                         "verdict": "refused_sandbox_unavailable",
                         "engine": "none", "error": None} for c in candidates],
            "roles": roles_record("(per-candidate origin field)"),
        }

    results: list[dict] = []
    refused = False
    for cand in candidates:
        rec = {"hash": cand.get("hash"), "origin": cand.get("origin"),
               "fitness": 0.0, "tests_passed": 0, "tests_total": 0,
               "ran": False, "proposable": False, "verdict": "fail",
               "engine": None, "error": None}
        code = cand.get("code")
        unit_test = cand.get("unit_test")
        if not isinstance(code, str) or not code.strip() \
                or not isinstance(unit_test, str) or not unit_test.strip():
            rec.update(verdict="invalid_candidate",
                       error="candidate needs non-empty code and unit_test")
            results.append(rec)
            continue
        try:
            units = _test_units(unit_test) or [unit_test]
        except SyntaxError as exc:
            rec.update(verdict="invalid_candidate",
                       error=f"unit_test does not parse: {_short(exc, 120)}")
            results.append(rec)
            continue
        rec["tests_total"] = len(units)

        # Does the candidate even run? (import-time errors -> hard 0.)
        run0 = _sandbox_run(code, timeout=sandbox_timeout, now=now,
                            receipt_log=receipt_log)
        rec["engine"] = run0.engine
        if not run0.sandboxed:
            rec.update(fitness=None, tests_total=None, tests_passed=None,
                       verdict="refused_sandbox_unavailable",
                       error=_short(run0.reason))
            refused = True
            results.append(rec)
            continue
        rec["ran"] = True
        if not run0.ok:
            rec.update(verdict="failed_to_run",
                       error=_short(run0.stderr or run0.reason))
            results.append(rec)
            continue

        passed = 0
        first_error: str | None = None
        for unit in units:
            program = (code + "\n\n# --- external verifier (aios_evolve fitness"
                       " gate) ---\n" + unit + "\n")
            run = _sandbox_run(program, timeout=sandbox_timeout, now=now,
                               receipt_log=receipt_log)
            if not run.sandboxed:
                rec.update(fitness=None, verdict="refused_sandbox_unavailable",
                           error=_short(run.reason))
                refused = True
                break
            if run.ok:
                passed += 1
            elif first_error is None:
                first_error = _short(run.stderr or run.reason)
        else:
            total = len(units)
            rec.update(fitness=passed / total, tests_passed=passed,
                       error=first_error,
                       verdict=("pass" if passed == total
                                else "partial" if passed else "fail"),
                       proposable=(passed == total))
        results.append(rec)
    return {"schema": SCHEMA, "kind": "fitness", "refused": refused,
            "reason": None if not refused else
            "sandbox became unavailable mid-evaluation (fail closed)",
            "results": results,
            "roles": roles_record("(per-candidate origin field)")}


# ---------------------------------------------------------------------------
# 3. contrastive_robustness — adopted contrastive invariance as input fuzzing
# ---------------------------------------------------------------------------

def _value_transforms(value):
    """Deterministic boundary/type-edge transformations of one argument."""
    if isinstance(value, bool):
        return [value, not value]
    if isinstance(value, int):
        return [0, 1, -1, -value, value + 1, value * 1000 + 1]
    if isinstance(value, float):
        return [0.0, 1.0, -value, value * 1000.0 + 1.0]
    if isinstance(value, str):
        return ["", value * 2, value * 50, value.upper()]
    if isinstance(value, list):
        return [[], value * 2, value * 25]
    if isinstance(value, tuple):
        return [(), value * 2]
    if isinstance(value, dict):
        return [{}]
    return [value]


def _fuzz_probes(example_inputs: list, k: int, seed: int) -> list[tuple]:
    """Deterministic, seeded probe set: each probe transforms ONE argument of
    one example input (contrastive: small transformations of known-good
    inputs). Only repr-round-trippable probes are kept (the harness embeds
    args by repr)."""
    pool: list[tuple] = []
    seen: set[str] = set()

    def add(args: tuple) -> None:
        r = repr(args)
        if r in seen:
            return
        try:
            if ast.literal_eval(r) != args:
                return
        except (ValueError, SyntaxError):
            return
        seen.add(r)
        pool.append(args)

    for example in example_inputs:
        base = tuple(example)
        add(base)
        for idx, value in enumerate(base):
            for transformed in _value_transforms(value):
                add(base[:idx] + (transformed,) + base[idx + 1:])
    if len(pool) > k:
        pool = random.Random(seed).sample(pool, k)
    return pool


def contrastive_robustness(candidate: dict, *, k: int = DEFAULT_FUZZ_K,
                           seed: int = DEFAULT_FUZZ_SEED,
                           sandbox_timeout: float = DEFAULT_SANDBOX_TIMEOUT,
                           now: float | None = None,
                           receipt_log=_sandbox.DEFAULT_RECEIPT_LOG) -> dict:
    """Require the candidate to survive TRANSFORMATIONS of its inputs, not
    merely its author's own test: each probe calls the entry function twice on
    a transformed input and demands a deterministic, non-crashing result
    (NaN-tolerant). Score = probes survived / probes run, reported SEPARATELY
    from fitness. Oracle-free: measures fragility, not correctness (see module
    limitations). Sandbox unavailable -> refuses, robustness None."""
    out = {"schema": SCHEMA, "kind": "robustness", "hash": candidate.get("hash"),
           "entry": None, "robustness": None, "probes_run": 0,
           "probes_survived": 0, "fragile": None, "failures": [],
           "verdict": "ok"}
    if _sandbox.pick_engine() == "none":
        out["verdict"] = "refused_sandbox_unavailable"
        return out
    code = candidate.get("code") or ""
    entry = candidate.get("entry") or _infer_entry(code)
    if not entry:
        out["verdict"] = "no_entry"
        return out
    out["entry"] = entry
    examples = candidate.get("example_inputs")
    if not examples:
        try:
            tree = ast.parse(code)
            fn = next(n for n in reversed(tree.body)
                      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and n.name == entry)
            arity = len(fn.args.posonlyargs) + len(fn.args.args) - len(fn.args.defaults)
        except (SyntaxError, StopIteration):
            arity = 1
        examples = [[1] * max(arity, 1)]
    probes = _fuzz_probes(examples, k, seed)
    if not probes:
        out["verdict"] = "no_probes"
        return out

    survived = 0
    for args in probes:
        program = (code + "\n\n# --- aios_evolve contrastive robustness probe ---\n"
                   f"_args = {args!r}\n"
                   f"_r1 = {entry}(*_args)\n"
                   f"_r2 = {entry}(*_args)\n"
                   "assert (_r1 == _r2) or (_r1 != _r1 and _r2 != _r2), "
                   "'non-deterministic output'\n")
        run = _sandbox_run(program, timeout=sandbox_timeout, now=now,
                           receipt_log=receipt_log)
        if not run.sandboxed:
            out["verdict"] = "refused_sandbox_unavailable"
            out["robustness"] = None
            return out
        if run.ok:
            survived += 1
        elif len(out["failures"]) < 6:
            out["failures"].append({"args": _short(repr(args), 80),
                                    "reason": _short(run.stderr or run.reason, 120)})
    out.update(probes_run=len(probes), probes_survived=survived,
               robustness=survived / len(probes),
               fragile=(survived / len(probes)) < 0.6)
    return out


# ---------------------------------------------------------------------------
# 4. gumbel_softmax_select — anti-argmax-collapse selection (pure math/random)
# ---------------------------------------------------------------------------

def gumbel_softmax_select(fitnesses: list[float], *, temperature: float,
                          seed: int) -> dict:
    """Temperature-controlled stochastic selection over a discrete candidate
    set via the Gumbel-max trick.

    Formula (documented, no numpy): with logits l_i = f_i / tau and i.i.d.
    Gumbel(0,1) noise g_i = -log(-log(u_i)), u_i ~ Uniform(0,1):

        selected = argmax_i (l_i + g_i)            # exact sample from
        P(select i) = exp(f_i/tau) / sum_j exp(f_j/tau)   # softmax(f/tau)

    tau -> 0 recovers argmax (exploitation); large tau -> uniform
    (exploration). `relaxed` is the softmax over the perturbed logits — the
    Gumbel-Softmax relaxation vector. HONEST NOTE: with no learned parameters
    there is nothing to differentiate through here; the trick's value in this
    organ is principled, seed-reproducible exploration that avoids the
    degenerate constant-argmax collapse of discrete selection."""
    if not fitnesses:
        raise ValueError("gumbel_softmax_select needs a non-empty fitness list")
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    rng = random.Random(seed)
    logits = [f / temperature for f in fitnesses]
    gumbels = []
    for _ in fitnesses:
        u = min(max(rng.random(), 1e-12), 1.0 - 1e-12)
        gumbels.append(-math.log(-math.log(u)))
    perturbed = [l + g for l, g in zip(logits, gumbels)]

    def _softmax(xs: list[float]) -> list[float]:
        mx = max(xs)
        exps = [math.exp(x - mx) for x in xs]
        z = sum(exps)
        return [e / z for e in exps]

    selected = max(range(len(perturbed)), key=perturbed.__getitem__)
    return {"schema": SCHEMA, "kind": "gumbel_select",
            "selected_index": selected,
            "argmax_index": max(range(len(fitnesses)), key=fitnesses.__getitem__),
            "probs": _softmax(logits), "relaxed": _softmax(perturbed),
            "temperature": temperature, "seed": seed}


# ---------------------------------------------------------------------------
# 5. sinkhorn_normalize — anti-degeneracy diversity constraint
# ---------------------------------------------------------------------------

def sinkhorn_normalize(matrix: list[list[float]], *, iters: int = 200,
                       epsilon: float = 0.25) -> dict:
    """Sinkhorn-Knopp entropy-regularized normalization of a score matrix
    (rows = candidate groups, cols = candidates): K_ij = exp(m_ij/epsilon)
    then alternate row/column scaling toward target marginals (each row sums
    to 1; each column sums to n_rows/n_cols). Smaller epsilon = sharper
    (closer to the raw scores); larger = smoother.

    ROLE HERE: anti-degeneracy for the RETAINED set — balanced column
    marginals stop one group/candidate from absorbing all retention mass
    ("keep everything from the winner") and stop empty rows ("keep nothing"),
    keeping retention diverse across groups. This is NOT optimal transport
    for its own sake: no cost geometry is being learned, and on a small
    discrete set the output is a balanced weighting, nothing more."""
    if not matrix or not matrix[0]:
        raise ValueError("sinkhorn_normalize needs a non-empty matrix")
    ncols = len(matrix[0])
    if any(len(row) != ncols for row in matrix):
        raise ValueError("matrix rows must all have the same length")
    if epsilon <= 0:
        raise ValueError("epsilon must be > 0")
    if iters < 1:
        raise ValueError("iters must be >= 1")
    nrows = len(matrix)
    mx = max(v for row in matrix for v in row)
    k = [[math.exp((v - mx) / epsilon) for v in row] for row in matrix]
    col_target = nrows / ncols
    for _ in range(iters):
        for r in range(nrows):
            s = sum(k[r]) or 1e-300
            k[r] = [v / s for v in k[r]]
        for c in range(ncols):
            s = sum(k[r][c] for r in range(nrows)) or 1e-300
            scale = col_target / s
            for r in range(nrows):
                k[r][c] *= scale
    row_dev = max(abs(sum(row) - 1.0) for row in k)
    col_dev = max(abs(sum(k[r][c] for r in range(nrows)) - col_target)
                  for c in range(ncols))
    return {"schema": SCHEMA, "kind": "sinkhorn", "matrix": k,
            "row_target": 1.0, "col_target": col_target,
            "row_dev": row_dev, "col_dev": col_dev,
            "iters": iters, "epsilon": epsilon}


# ---------------------------------------------------------------------------
# 6. evolve — the loop + append-only lineage
# ---------------------------------------------------------------------------

def _append_lineage(lineage, record: dict) -> None:
    path = Path(lineage)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:  # append-only, never truncate
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _combined_score(fit: float | None, rob: float | None) -> float | None:
    """Selection score: fitness GATES (a hard 0 stays 0), robustness
    modulates; unmeasured robustness gets the conservative 0.5 floor."""
    if fit is None:
        return None
    if rob is None:
        return fit * 0.5
    return fit * (0.5 + 0.5 * rob)


def select_retained(rows: list[dict]) -> tuple[list[int], dict | None]:
    """Sinkhorn-diversified retention over deduped FULL-PASS rows
    ({"candidate": {...}, "combined": float}). One retained candidate per
    origin group: argmax of the group's Sinkhorn-normalized row, with ties
    broken by the RAW combined score.

    The tie-break is load-bearing, found by a live run (2026-07-27): with a
    SINGLE group the doubly-balanced 1xN matrix is exactly uniform — Sinkhorn
    balancing is vacuous there and had silently retained the first index
    instead of the most robust candidate. Sinkhorn arbitrates ACROSS groups;
    the raw score must still decide WITHIN a tie."""
    if not rows:
        return [], None
    groups = sorted({row["candidate"]["origin"] for row in rows})
    floor = min(row["combined"] for row in rows) - 5.0
    matrix = [[row["combined"] if row["candidate"]["origin"] == g else floor
               for row in rows] for g in groups]
    sk = sinkhorn_normalize(matrix, iters=100, epsilon=0.25)
    retained: list[int] = []
    for r, g in enumerate(groups):
        members = [j for j, row in enumerate(rows)
                   if row["candidate"]["origin"] == g]
        best = max(members, key=lambda j: (sk["matrix"][r][j],
                                           rows[j]["combined"]))
        if best not in retained:
            retained.append(best)
    return retained, sk


def evolve(artifact: dict, *, rounds: int, n: int, substrate: str,
           model: str | None = None, now: float, lineage=LINEAGE,
           sandbox_timeout: float = DEFAULT_SANDBOX_TIMEOUT,
           fuzz_k: int = DEFAULT_FUZZ_K, temperature: float = 0.7,
           seed: int = DEFAULT_FUZZ_SEED,
           receipt_log=_sandbox.DEFAULT_RECEIPT_LOG) -> dict:
    """The organ's loop: generate -> sandbox-fitness -> robustness ->
    Gumbel-select (next parent) -> Sinkhorn-diversified retention -> lineage.

    Survivors are PROPOSED only (report['proposals']): this function never
    writes into scripts/ or the skill registry — registration must go through
    aios_skills.register (sandbox+unit-test gate), called explicitly by an
    operator. Retention proposals require a FULL external pass (fitness 1.0);
    partial credit only steers the search."""
    name = artifact.get("name") or "(unnamed artifact)"
    gen_label = (f"{substrate}:{model or _DEFAULT_MODELS.get(substrate)}"
                 if substrate != "offline" else "offline-perturb (no LLM)")
    report = {"schema": SCHEMA, "kind": "evolve_report", "ts": now,
              "artifact_name": name, "substrate": substrate,
              "model": model or _DEFAULT_MODELS.get(substrate),
              "status": "ok", "rounds_requested": rounds, "rounds_run": 0,
              "candidates_evaluated": 0, "fitness_distribution": [],
              "mean_robustness": None, "substrate_failures": [],
              "fallback_used": False, "selected_final": None,
              "proposals": [], "converged": False,
              "lineage_path": str(lineage), "roles": roles_record(gen_label)}

    if _sandbox.pick_engine() == "none":
        report["status"] = "refused_sandbox_unavailable"
        report["reason"] = ("refused (fail closed): no working sandbox engine "
                           "— no candidate was executed")
        _append_lineage(lineage, {"schema": LINEAGE_SCHEMA, "kind": "refusal",
                                  "ts": now, "artifact": name,
                                  "substrate": substrate,
                                  "reason": report["reason"]})
        return report

    parent_code = artifact["code"]
    evaluated: list[dict] = []   # {candidate, fit, robustness, combined, round}
    robustness_scores: list[float] = []

    for rnd in range(1, rounds + 1):
        parent_hash = _hash16(parent_code)
        round_artifact = {**artifact, "code": parent_code}
        gen = generate_variants(round_artifact, n, substrate=substrate,
                                model=model, now=now)
        report["substrate_failures"].extend(gen["substrate_failures"])
        report["fallback_used"] = report["fallback_used"] or gen["fallback_used"]
        candidates = gen["candidates"]
        if not candidates:
            _append_lineage(lineage, {
                "schema": LINEAGE_SCHEMA, "kind": "round", "ts": now,
                "round": rnd, "parent_hash": parent_hash,
                "substrate": substrate, "model": gen["model"], "generated": 0,
                "note": "no candidates generated (all substrates failed and "
                        "no offline perturbation site)",
                "substrate_failures": gen["substrate_failures"]})
            report["status"] = "no_candidates" if not evaluated else report["status"]
            break

        fit = fitness(candidates, sandbox_timeout=sandbox_timeout, now=now,
                      receipt_log=receipt_log)
        if fit["refused"]:
            report["status"] = "refused_sandbox_unavailable"
            report["reason"] = fit["reason"]
            _append_lineage(lineage, {"schema": LINEAGE_SCHEMA,
                                      "kind": "refusal", "ts": now,
                                      "round": rnd, "artifact": name,
                                      "reason": fit["reason"]})
            return report
        report["rounds_run"] = rnd

        rows: list[dict] = []
        for cand, fr in zip(candidates, fit["results"]):
            rob = None
            if fr["fitness"] and fr["fitness"] > 0:
                rr = contrastive_robustness(
                    cand, k=fuzz_k, seed=seed, sandbox_timeout=sandbox_timeout,
                    now=now, receipt_log=receipt_log)
                rob = rr["robustness"]
                if rob is not None:
                    robustness_scores.append(rob)
            rows.append({"candidate": cand, "fit": fr, "robustness": rob,
                         "combined": _combined_score(fr["fitness"], rob) or 0.0,
                         "round": rnd})

        viable = [i for i, row in enumerate(rows)
                  if (row["fit"]["fitness"] or 0) > 0]
        sel_global = None
        gumbel = None
        if viable:
            gumbel = gumbel_softmax_select(
                [rows[i]["combined"] for i in viable],
                temperature=temperature, seed=seed * 1000 + rnd)
            sel_global = viable[gumbel["selected_index"]]

        for i, row in enumerate(rows):
            fr = row["fit"]
            _append_lineage(lineage, {
                "schema": LINEAGE_SCHEMA, "kind": "candidate", "ts": now,
                "round": rnd, "parent_hash": parent_hash,
                "candidate_hash": row["candidate"]["hash"],
                "substrate": substrate, "model": row["candidate"]["model"],
                "origin": row["candidate"]["origin"],
                "fitness": fr["fitness"], "tests_passed": fr["tests_passed"],
                "tests_total": fr["tests_total"],
                "robustness": row["robustness"], "combined": row["combined"],
                "selected": i == sel_global, "verdict": fr["verdict"],
                "error": fr["error"]})
        _append_lineage(lineage, {
            "schema": LINEAGE_SCHEMA, "kind": "round", "ts": now, "round": rnd,
            "parent_hash": parent_hash, "substrate": substrate,
            "model": gen["model"], "generated": len(candidates),
            "fallback_used": gen["fallback_used"],
            "substrate_failures": gen["substrate_failures"],
            "selected_hash": rows[sel_global]["candidate"]["hash"]
            if sel_global is not None else None,
            "gumbel": {"temperature": temperature, "seed": seed * 1000 + rnd,
                       "probs": gumbel["probs"]} if gumbel else None})

        evaluated.extend(rows)
        if sel_global is not None:
            sel = rows[sel_global]
            parent_code = sel["candidate"]["code"]
            report["selected_final"] = {
                "candidate_hash": sel["candidate"]["hash"], "round": rnd,
                "origin": sel["candidate"]["origin"],
                "fitness": sel["fit"]["fitness"],
                "robustness": sel["robustness"], "combined": sel["combined"]}
            if sel["fit"]["fitness"] == 1.0 and sel["robustness"] == 1.0:
                report["converged"] = True
                break

    report["candidates_evaluated"] = len(evaluated)
    report["fitness_distribution"] = sorted(
        (row["fit"]["fitness"] for row in evaluated
         if row["fit"]["fitness"] is not None), reverse=True)
    if robustness_scores:
        report["mean_robustness"] = sum(robustness_scores) / len(robustness_scores)

    # Sinkhorn-diversified retention over FULL-PASS candidates only.
    passing = [row for row in evaluated if row["fit"]["verdict"] == "pass"]
    # dedupe by candidate hash, keep best combined
    best_by_hash: dict[str, dict] = {}
    for row in passing:
        h = row["candidate"]["hash"]
        if h not in best_by_hash or row["combined"] > best_by_hash[h]["combined"]:
            best_by_hash[h] = row
    passing = list(best_by_hash.values())
    if passing:
        retained_idx, sk = select_retained(passing)
        for j in retained_idx:
            row = passing[j]
            _append_lineage(lineage, {
                "schema": LINEAGE_SCHEMA, "kind": "retention", "ts": now,
                "candidate_hash": row["candidate"]["hash"],
                "origin": row["candidate"]["origin"], "round": row["round"],
                "fitness": row["fit"]["fitness"],
                "robustness": row["robustness"], "combined": row["combined"],
                "sinkhorn": {"row_dev": sk["row_dev"], "col_dev": sk["col_dev"],
                             "epsilon": sk["epsilon"]},
                "proposed": True,
                "note": "PROPOSED only — NOT registered; registration requires "
                        "an explicit operator call through aios_skills.register "
                        "(sandbox+unit-test gate)"})
            report["proposals"].append({
                "candidate_hash": row["candidate"]["hash"],
                "origin": row["candidate"]["origin"],
                "model": row["candidate"]["model"],
                "fitness": row["fit"]["fitness"],
                "robustness": row["robustness"], "combined": row["combined"],
                "code": row["candidate"]["code"],
                "registration": "NOT registered — operator must explicitly run "
                                "aios_skills.register (sandbox+unit-test gate)"})
    return report


# ---------------------------------------------------------------------------
# lineage reading + report aggregation (pure)
# ---------------------------------------------------------------------------

def read_lineage(lineage=LINEAGE) -> list[dict]:
    path = Path(lineage)
    records: list[dict] = []
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                try:
                    records.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    return records


def summarize_lineage(records: list[dict]) -> dict:
    """Survival rate per substrate/model, mean robustness, diversity retained."""
    per: dict[tuple, dict] = {}
    retained_origins: set[str] = set()
    all_origins: set[str] = set()
    for rec in records:
        if rec.get("kind") == "retention":
            retained_origins.add(rec.get("origin") or "?")
        if rec.get("kind") != "candidate":
            continue
        key = (rec.get("substrate") or "?", rec.get("model") or "-",
               rec.get("origin") or "?")
        all_origins.add(rec.get("origin") or "?")
        s = per.setdefault(key, {"substrate": key[0], "model": key[1],
                                 "origin": key[2], "candidates": 0, "passed": 0,
                                 "selected": 0, "fitness_sum": 0.0,
                                 "fitness_n": 0, "robustness_sum": 0.0,
                                 "robustness_n": 0})
        s["candidates"] += 1
        if rec.get("verdict") == "pass":
            s["passed"] += 1
        if rec.get("selected"):
            s["selected"] += 1
        if isinstance(rec.get("fitness"), (int, float)):
            s["fitness_sum"] += rec["fitness"]
            s["fitness_n"] += 1
        if isinstance(rec.get("robustness"), (int, float)):
            s["robustness_sum"] += rec["robustness"]
            s["robustness_n"] += 1
    rows = []
    for s in per.values():
        rows.append({
            "substrate": s["substrate"], "model": s["model"],
            "origin": s["origin"], "candidates": s["candidates"],
            "survival_rate": round(s["passed"] / s["candidates"], 4)
            if s["candidates"] else None,
            "selected": s["selected"],
            "mean_fitness": round(s["fitness_sum"] / s["fitness_n"], 4)
            if s["fitness_n"] else None,
            "mean_robustness": round(s["robustness_sum"] / s["robustness_n"], 4)
            if s["robustness_n"] else None})
    rows.sort(key=lambda r: (r["substrate"], r["model"], r["origin"]))
    return {"schema": SCHEMA, "kind": "lineage_report",
            "candidate_records": sum(r["candidates"] for r in rows),
            "retention_records": sum(1 for r in records
                                     if r.get("kind") == "retention"),
            "refusals": sum(1 for r in records if r.get("kind") == "refusal"),
            "per_substrate": rows,
            "diversity_retained": {
                "origins_retained": sorted(retained_origins),
                "origins_seen": sorted(all_origins)}}


# ---------------------------------------------------------------------------
# CLI — the impure edge: supplies the real clock
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="AIOS evolutionary selection organ — mutate via substrate, "
                    "score in the OS sandbox, Gumbel-select, Sinkhorn-diversify, "
                    "append lineage. Survivors are PROPOSED only.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="one evolve invocation on a failing artifact")
    run.add_argument("--file", required=True, help="artifact JSON "
                     "({name, code, unit_test, error?, entry?, example_inputs?})")
    run.add_argument("--substrate", choices=SUBSTRATES, default="nim")
    run.add_argument("--model", default=None)
    run.add_argument("--rounds", type=int, default=1)
    run.add_argument("--n", type=int, default=4)
    run.add_argument("--timeout", type=float, default=DEFAULT_SANDBOX_TIMEOUT)
    run.add_argument("--fuzz-k", type=int, default=DEFAULT_FUZZ_K)
    run.add_argument("--temperature", type=float, default=0.7)
    run.add_argument("--seed", type=int, default=DEFAULT_FUZZ_SEED)
    run.add_argument("--lineage", default=str(LINEAGE))
    lin = sub.add_parser("lineage", help="print lineage records")
    lin.add_argument("--tail", type=int, default=0)
    lin.add_argument("--lineage", default=str(LINEAGE))
    rep = sub.add_parser("report", help="survival rate per substrate/model, "
                                        "mean robustness, diversity retained")
    rep.add_argument("--lineage", default=str(LINEAGE))
    args = ap.parse_args(argv)

    if args.cmd == "run":
        try:
            artifact = json.loads(Path(args.file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"schema": SCHEMA, "status": "error",
                              "reason": f"cannot read artifact: {exc}"},
                             ensure_ascii=False, indent=2))
            return 2
        try:
            report = evolve(artifact, rounds=args.rounds, n=args.n,
                            substrate=args.substrate, model=args.model,
                            now=time.time(), lineage=args.lineage,
                            sandbox_timeout=args.timeout, fuzz_k=args.fuzz_k,
                            temperature=args.temperature, seed=args.seed)
        except ValueError as exc:
            print(json.dumps({"schema": SCHEMA, "status": "error",
                              "reason": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "ok" else 2
    if args.cmd == "lineage":
        records = read_lineage(args.lineage)
        if args.tail > 0:
            records = records[-args.tail:]
        for rec in records:
            print(json.dumps(rec, ensure_ascii=False))
        return 0
    print(json.dumps(summarize_lineage(read_lineage(args.lineage)),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
