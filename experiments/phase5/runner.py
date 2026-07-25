#!/usr/bin/env python3
"""Phase 5 single-task runner (prereg §1, §3, §6).

FROZEN PROTOCOL: docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md.

One autonomous episode per task, FROZEN local student via ollama, provider
escalation structurally impossible (the only model call is the one local HTTP
call below; there is no escalation path in this module).

  * Prompt = failing test file + current (reverted) source + a short
    instruction to make the tests pass by editing ONLY the source file.
    Treatment additionally injects top-k prior experience + applicable skills
    (control injects nothing).
  * The model's edit is applied to the source file in the WORKSPACE only —
    never the real repo.
  * The ORACLE (the repo's own pytest file) runs OUTSIDE any sandbox, in the
    workspace, AFTER the agent has finished. PASS = rc == 0 AND >=1 test
    actually passed (an all-skip run is not a pass — closes the
    "make-the-tests-skip" hole). First-attempt only: no retry loop.
  * §6.1 guard: ANY change under tests/ (vs the materialization snapshot)
    scores the attempt FAIL regardless of the oracle result.
  * Infra errors (ollama down / HTTP error / model-call timeout) are recorded
    as ``infra_error`` with ``passed = None`` — dropped from paired analysis,
    NEVER counted as a loss (prereg §6.6).
  * The model's code is NEVER executed by this runner outside the pytest
    oracle. The only other executable path — skill registration in the
    treatment arm — goes through scripts/aios_sandbox.py via
    scripts/aios_skills.register (sandbox-gated, fail closed).

Treatment substrate (prereg §3, §6.3): the retrieval index lives in an
ISOLATED state dir (never the repo's real .aios/) and may contain only
artifacts produced during the run — runner writes a run-log record per
finished task (aios_experience-compatible JSONL) and, on a pass, attempts
sandbox-gated skill induction via aios_skills.induce_and_register.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import workspace as ws_mod  # noqa: E402

REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import aios_experience  # noqa: E402
import aios_skills  # noqa: E402

SCHEMA = "aios.phase5.attempt.v1"
OLLAMA_URL = "http://localhost:11434"
NUM_CTX = 32768
NUM_PREDICT = 16384
SEED = 7

_PASSED_RE = re.compile(r"(\d+) passed")
_FENCE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


class InfraError(Exception):
    """Model/HTTP/infra failure — recorded separately, never a task loss."""


# ---------------------------------------------------------------------------
# Oracle — the external deterministic verifier (prereg §1)
# ---------------------------------------------------------------------------

def run_oracle(ws: Path | str, oracle_cmd: list[str],
               timeout: float = 180.0) -> dict:
    """Run the frozen oracle command in the workspace. ok = rc == 0 AND >=1
    test passed. A hang in model-written code -> timed_out, ok False (the
    model's code hanging its own module's tests is a task failure)."""
    env = dict(os.environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    t0 = time.time()
    try:
        r = subprocess.run(oracle_cmd, cwd=str(ws), capture_output=True,
                           text=True, timeout=timeout, env=env)
        rc, out, timed_out = r.returncode, (r.stdout + r.stderr), False
    except subprocess.TimeoutExpired as exc:
        rc, timed_out = -1, True
        out = ((exc.stdout or b"").decode("utf-8", "replace") if
               isinstance(exc.stdout, bytes) else (exc.stdout or ""))
    m = _PASSED_RE.search(out.splitlines()[-1] if out.splitlines() else "")
    if m is None:
        m = _PASSED_RE.search(out)
    passed = int(m.group(1)) if m else 0
    return {"rc": rc, "passed": passed, "timed_out": timed_out,
            "ok": (rc == 0 and passed >= 1 and not timed_out),
            "wall_s": round(time.time() - t0, 2), "tail": out[-800:]}


# ---------------------------------------------------------------------------
# Frozen student call (ollama, local, no escalation path)
# ---------------------------------------------------------------------------

def call_ollama(model: str, prompt: str, timeout: float = 360.0,
                url: str = OLLAMA_URL) -> tuple[str, dict]:
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.0, "seed": SEED,
                    "num_ctx": NUM_CTX, "num_predict": NUM_PREDICT},
    }).encode("utf-8")
    req = urllib.request.Request(f"{url}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, OSError) as exc:
        raise InfraError(f"ollama call failed: {type(exc).__name__}: "
                         f"{str(exc)[:200]}") from exc
    meta = {"prompt_tokens": data.get("prompt_eval_count"),
            "output_tokens": data.get("eval_count"),
            "model_wall_ns": data.get("total_duration")}
    return str(data.get("response") or ""), meta


def extract_source(text: str) -> str | None:
    """The model's proposed full source file: last fenced code block, else the
    raw text when it parses as Python. None -> no usable code (task FAIL,
    not infra)."""
    blocks = _FENCE_RE.findall(text)
    if blocks:
        return blocks[-1]
    try:
        compile(text, "<model>", "exec")
        return text
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Treatment injection (prereg §3) — reuses the existing organs
# ---------------------------------------------------------------------------

def task_text(task: dict) -> str:
    return (f"make the tests in {', '.join(task['test_paths'])} pass by "
            f"editing {task['script_path']}")


def build_injection(text: str, state_dir: Path | str | None,
                    k: int = 3) -> str:
    """Top-k prior experience (aios_experience over the run's OWN run logs)
    + applicable skills (aios_skills.retrieve over the run's OWN registry).
    Empty string when state_dir is None (control) or no artifacts exist yet.
    §6.3: state_dir holds only artifacts produced during this run."""
    if state_dir is None:
        return ""
    state_dir = Path(state_dir)
    parts: list[str] = []

    ix = aios_experience.ExperienceIndex(state_dir / "runs")
    if ix.runs:
        hits = aios_experience.q_by_goal(ix, "pass by editing")["matches"]
        briefs = [{"goal": h.get("goal_hint"), "status": h.get("status")}
                  for h in hits[-k:]]
        if briefs:
            parts.append("## Prior experience on this codebase "
                         "(your own verified record):\n"
                         + json.dumps(briefs, ensure_ascii=False, indent=1))

    registry = state_dir / "skills" / "registry.jsonl"
    skill_hits = aios_skills.retrieve(text, k=k, registry=registry)
    if skill_hits:
        lines = ["## Applicable verified skills (sandbox-tested):"]
        for h in skill_hits:
            s = h["skill"]
            lines.append(f"### {s.get('name')}\n"
                         f"applicability: {s.get('applicability')}\n"
                         f"```python\n{s.get('code', '').rstrip()}\n```")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def build_prompt(task: dict, ws: Path | str, injection: str) -> str:
    ws = Path(ws)
    src_path = ws / task["script_path"]
    src = (src_path.read_text(encoding="utf-8", errors="replace")
           if src_path.exists() else "")
    src_note = ("(the file does not exist yet — you must create it)"
                if not src_path.exists() else "")
    test_blocks = []
    for tp in task["test_paths"]:
        body = (ws / tp).read_text(encoding="utf-8", errors="replace")
        test_blocks.append(f"## Failing test file: {tp}\n```python\n"
                           f"{body}\n```")
    inj = f"\n{injection}\n" if injection else ""
    return (
        "You are fixing a Python repository. The test file(s) below currently "
        f"FAIL. Make them pass by editing ONLY the source file "
        f"{task['script_path']}. Never modify test files.\n"
        f"{inj}\n"
        + "\n\n".join(test_blocks)
        + f"\n\n## Current source file: {task['script_path']} {src_note}\n"
        f"```python\n{src}\n```\n\n"
        f"Reply with the COMPLETE new content of {task['script_path']} in a "
        "single ```python code block. No explanation outside the block."
    )


# ---------------------------------------------------------------------------
# Treatment experience recording (only artifacts produced during the run)
# ---------------------------------------------------------------------------

def record_experience(state_dir: Path | str, task: dict, record: dict,
                      solution_source: str | None,
                      induce: bool = True) -> dict:
    """Append an aios_experience-compatible run log for this attempt; on a
    pass, attempt sandbox-gated skill induction (aios_skills). All writes stay
    inside state_dir — never the repo's real .aios/."""
    state_dir = Path(state_dir)
    runs = state_dir / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    now = time.time()
    ts = _dt.datetime.fromtimestamp(
        now, _dt.timezone.utc).isoformat(timespec="seconds")
    log = runs / f"{task['task_id']}.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "session_meta",
                             "run_id": task["task_id"],
                             "agent": "phase5-treatment", "ts": ts,
                             "git_sha": ""}) + "\n")
        fh.write(json.dumps({"kind": "outcome",
                             "exit": ("model_finished" if record.get("passed")
                                      else "task_failed"),
                             "turns": 1,
                             "goal_hint": task_text(task)}) + "\n")
    out: dict = {"logged": str(log), "skill": None}
    if induce and record.get("passed") and solution_source:
        decision = aios_skills.induce_and_register(
            task_text(task), solution_source, now=now,
            registry=state_dir / "skills" / "registry.jsonl",
            manifest=state_dir / "skills" / "manifest.jsonl",
            receipt_log=state_dir / "sandbox_receipts.jsonl")
        out["skill"] = {"verdict": decision.get("verdict"),
                        "registered": decision.get("registered"),
                        "id": decision.get("id")}
    return out


# ---------------------------------------------------------------------------
# One task, one autonomous episode
# ---------------------------------------------------------------------------

def run_task(task: dict, arm: str, model: str,
             repo_root: Path | str = REPO_ROOT,
             state_dir: Path | str | None = None,
             call_timeout: float = 360.0, oracle_timeout: float = 180.0,
             ws: Path | str | None = None,
             model_fn=None, induce: bool = True) -> dict:
    """Run ONE task episode; return the per-task record (prereg §1, §3, §6).

    arm='control' -> no injection, no persistent state. arm='treatment' ->
    injection from state_dir + experience recorded back into state_dir.
    model_fn(prompt)->text overrides the ollama call (tests only).
    """
    assert arm in ("control", "treatment"), arm
    if arm == "control":
        state_dir = None  # control never carries substrate (prereg §3)
    own_ws = ws is None
    if own_ws:
        ws = ws_mod.materialize(repo_root, task["commit"],
                                task["parent_commit"], task["script_path"],
                                task["test_paths"])
    ws = Path(ws)
    record: dict = {
        "schema": SCHEMA, "task_id": task["task_id"], "arm": arm,
        "model": model, "passed": None, "infra_error": None,
        "tests_tampered": [], "oracle": None, "tokens": {},
        "injected_chars": 0, "injection_nonempty": False,
        "wall_s": None, "fail_reason": None,
    }
    t0 = time.time()
    try:
        snapshot = ws_mod.tests_snapshot(ws)
        injection = build_injection(task_text(task), state_dir)
        record["injected_chars"] = len(injection)
        record["injection_nonempty"] = bool(injection)
        prompt = build_prompt(task, ws, injection)
        record["prompt_chars"] = len(prompt)

        solution: str | None = None
        try:
            if model_fn is not None:
                text = model_fn(prompt)
            else:
                text, meta = call_ollama(model, prompt, timeout=call_timeout)
                record["tokens"] = meta
        except InfraError as exc:
            record["infra_error"] = str(exc)
            return record  # passed stays None: infra, NOT a loss (§6.6)

        solution = extract_source(text)
        if solution is None:
            record["passed"] = False
            record["fail_reason"] = "no_usable_code_in_model_output"
        else:
            # Apply the edit to the WORKSPACE source file only.
            target = ws / task["script_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(solution, encoding="utf-8")

        # §6.1 guard: any change under tests/ scores FAIL regardless of oracle.
        record["tests_tampered"] = ws_mod.tests_tampered(ws, snapshot)

        if solution is not None:
            record["oracle"] = run_oracle(ws, task["oracle_cmd"],
                                          timeout=oracle_timeout)
            if record["tests_tampered"]:
                record["passed"] = False
                record["fail_reason"] = "tests_diff_guard"
            else:
                record["passed"] = bool(record["oracle"]["ok"])
                if not record["passed"]:
                    record["fail_reason"] = "oracle_failed"

        if arm == "treatment" and state_dir is not None:
            record["experience"] = record_experience(
                state_dir, task, record, solution, induce=induce)
        return record
    finally:
        record["wall_s"] = round(time.time() - t0, 2)
        if own_ws:
            ws_mod.cleanup(ws)
