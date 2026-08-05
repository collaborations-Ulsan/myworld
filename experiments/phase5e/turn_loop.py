#!/usr/bin/env python3
"""Channel-E K-turn episode runner (prereg §1–§3 + Errata operationalizations).

FROZEN PROTOCOL: docs/AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md.

One episode = K=5 model calls (frozen §1.2); a reply may contain MULTIPLE
ACTIONs (a turn = one model call plus its tool results). Both arms get the
IDENTICAL interface (§1.4); the arms differ ONLY in the Channel-E substrate:

  treatment — (a) verified sub-routine dispatch: registered skills exposed as
              OPAQUE callable primitives (name/applicability/arity, never code
              — code in the prompt would be the dead X transport), executed by
              the OS in the sandbox; (b) stack-trace AST-closure masking: the
              edit/inspect surface of EXISTING repo files is restricted to the
              k=2 closure (ast_index.compute_surface).
  control   — same K-turn loop, same tools minus `skill`, whole-repo surface,
              registry structurally wiped (never passed in).

Guards enforced here:
  * §1.3 — the grading oracle can NEVER run inside the episode: `run` commands
    referencing the task's test files / `tests/` / bare pytest are BLOCKED,
    recorded, and returned as refusals (Errata op-1; blocked ≠ void — void is
    an actual leak-through, asserted post-episode).
  * §6.1 — writes under tests/ are blocked at the tool layer AND the snapshot
    tamper check still runs afterwards (belt + braces).
  * Masking — treatment reads/writes of existing repo files outside the
    closure surface are blocked and recorded. NEW agent-created files are
    unrestricted in both arms (Errata op-3).
  * Infra errors (ollama down/timeout) -> ``infra_error`` with passed=None —
    dropped from the paired analysis, never counted as a loss (§6 carry-over).

The model's code executes ONLY (a) inside the OS sandbox (`run` / `skill`
actions, no network) and (b) under the external pytest oracle AFTER the
episode ends. Skill induction on a treatment pass goes through the unchanged
aios_skills sandbox+unit-test gate.
"""
from __future__ import annotations

import ast
import json
import re
import shlex
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "phase5"))
import ast_index  # noqa: E402
import workspace as ws_mod  # noqa: E402
from runner import run_oracle, InfraError  # noqa: E402

REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import aios_skills  # noqa: E402
import aios_sandbox  # noqa: E402

SCHEMA = "aios.phase5e.attempt.v1"
OLLAMA_URL = "http://localhost:11434"
NUM_CTX = 32768
NUM_PREDICT = 16384
SEED = 7

K_TURNS = 5              # frozen (prereg §1.2)
DISPATCH_SURFACE_CAP = 12  # frozen (Errata op-4)
RUN_TIMEOUT = 120.0
SKILL_TIMEOUT = 60.0
READ_CAP = 8000
RUN_OUT_CAP = 4000
TRACE_CAP = 6000
LISTING_CAP = 250

_ACTION_RE = re.compile(r"^ACTION:\s*(read|run|skill|write|done)\b[ \t]*(.*)$",
                        re.MULTILINE)
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*[ \t]*\n(.*?)```", re.DOTALL)


# ---------------------------------------------------------------------------
# Failing-trace capture — run_oracle keeps only an 800-char verdict tail; the
# closure needs the traceback FRAMES, so capture the full output (capped).
# ---------------------------------------------------------------------------

def capture_failing_output(ws: Path | str, oracle_cmd: list[str],
                           timeout: float = 300.0, cap: int = 40000) -> str:
    import os as _os
    import subprocess as _sp
    env = dict(_os.environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = _sp.run(oracle_cmd, cwd=str(ws), capture_output=True, text=True,
                    timeout=timeout, env=env)
        out = r.stdout + r.stderr
    except _sp.TimeoutExpired as exc:
        out = ((exc.stdout or b"").decode("utf-8", "replace")
               if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
    return out[-cap:]


# ---------------------------------------------------------------------------
# Model call — ollama /api/chat (frozen student, no escalation path)
# ---------------------------------------------------------------------------

def call_chat(model: str, messages: list[dict], timeout: float = 2400.0,
              url: str = OLLAMA_URL) -> tuple[str, dict]:
    body = json.dumps({
        "model": model, "messages": messages, "stream": False,
        "options": {"temperature": 0.0, "seed": SEED,
                    "num_ctx": NUM_CTX, "num_predict": NUM_PREDICT},
    }).encode("utf-8")
    req = urllib.request.Request(f"{url}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, OSError) as exc:
        raise InfraError(f"ollama chat failed: {type(exc).__name__}: "
                         f"{str(exc)[:200]}") from exc
    meta = {"prompt_tokens": data.get("prompt_eval_count"),
            "output_tokens": data.get("eval_count"),
            "model_wall_ns": data.get("total_duration")}
    return str((data.get("message") or {}).get("content") or ""), meta


# ---------------------------------------------------------------------------
# Action parsing (Errata op-5)
# ---------------------------------------------------------------------------

def _unwrap(s: str) -> str:
    """Strip decorative wrapping the model copies from instructions —
    matching <...>, "...", '...', `...` pairs (repeatedly). Deterministic,
    applied identically in both arms."""
    s = s.strip()
    pairs = {("<", ">"), ('"', '"'), ("'", "'"), ("`", "`")}
    while len(s) >= 2 and (s[0], s[-1]) in pairs:
        s = s[1:-1].strip()
    return s


def parse_actions(text: str) -> list[dict]:
    """All ACTION lines in order; `write` consumes the first fenced block
    between it and the next ACTION line (or end of text)."""
    matches = list(_ACTION_RE.finditer(text))
    out: list[dict] = []
    for i, m in enumerate(matches):
        kind, arg = m.group(1), _unwrap(m.group(2))
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if kind == "write":
            fence = _FENCE_RE.search(text, m.end(), seg_end)
            out.append({"kind": "write", "path": _unwrap(arg),
                        "content": fence.group(1) if fence else None})
        elif kind == "skill":
            parts = arg.split(None, 1)
            out.append({"kind": "skill",
                        "id": _unwrap(parts[0]) if parts else "",
                        "args_json": parts[1] if len(parts) > 1 else "[]"})
        elif kind == "done":
            out.append({"kind": "done"})
        else:
            out.append({"kind": kind, "arg": arg})
    return out


# ---------------------------------------------------------------------------
# §1.3 oracle-block rule (Errata op-1 — frozen before any cell)
# ---------------------------------------------------------------------------

def oracle_blocked(cmd: str, test_paths: list[str]) -> str | None:
    """Reason string when the command must be blocked, else None."""
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()
    basenames = {Path(tp).name for tp in test_paths}
    for tok in tokens:
        if "tests/" in tok or tok in basenames or tok in test_paths:
            return f"references the grading tests ({tok})"
    if any(re.search(r"\bpytest\b", tok) for tok in tokens):
        explicit_py = [t for t in tokens if t.endswith(".py")]
        if not explicit_py:
            return "bare pytest would collect tests/ (the grading oracle)"
    return None


# ---------------------------------------------------------------------------
# Dispatch surface (§2a + Errata op-4) — opaque callables, never code
# ---------------------------------------------------------------------------

def _primary_fn(code: str) -> tuple[str, int] | None:
    """(name, n_required_args) of the last top-level function, else None."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    fns = [n for n in tree.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not fns:
        return None
    fn = fns[-1]
    a = fn.args
    required = (len(a.posonlyargs) + len(a.args) - len(a.defaults)
                + sum(1 for d in a.kw_defaults if d is None))
    return fn.name, required


def build_dispatch_surface(task: dict, registry: Path) -> dict:
    """Registered skills as opaque primitives; same-target-script skills are
    EXCLUDED from this task's surface (whole-task-lookup guard, §2a)."""
    skills = aios_skills.load_registry(registry) if registry.exists() else []
    excluded, entries = [], []
    for s in skills:
        goal = str((s.get("provenance") or {}).get("source_goal", ""))
        if task["script_path"] in goal:
            excluded.append(s.get("id"))
            continue
        p = _primary_fn(s.get("code", ""))
        if p is None:
            continue
        entries.append({"id": s.get("id"), "call_name": p[0],
                        "n_required_args": p[1],
                        "applicability": s.get("applicability", ""),
                        "_skill": s})
    capped = len(entries) > DISPATCH_SURFACE_CAP
    if capped:
        hits = aios_skills.retrieve(
            f"make the tests in {', '.join(task['test_paths'])} pass by "
            f"editing {task['script_path']}",
            k=DISPATCH_SURFACE_CAP, registry=registry)
        keep_ids = {h["skill"].get("id") for h in hits}
        ranked = [e for e in entries if e["id"] in keep_ids]
        for e in reversed(entries):  # fill with most recent
            if len(ranked) >= DISPATCH_SURFACE_CAP:
                break
            if e not in ranked:
                ranked.append(e)
        entries = ranked[:DISPATCH_SURFACE_CAP]
    return {"entries": entries, "excluded_same_target": excluded,
            "capped": capped, "n_registry": len(skills)}


def exec_skill(entry: dict, args_json: str, now: float,
               receipt_log: Path | None) -> str:
    """OS executes the primitive in the sandbox; the model sees only the
    return value. Fail closed on sandbox unavailability."""
    try:
        parsed = json.loads(args_json) if args_json.strip() else []
    except json.JSONDecodeError as exc:
        return f"skill args must be a JSON array or object: {exc}"
    if not isinstance(parsed, (list, dict)):
        return "skill args must be a JSON array (positional) or object (kw)"
    program = (
        entry["_skill"]["code"]
        + "\n\n# --- Channel-E dispatch shim (harness-authored) ---\n"
        + "import json as _json\n"
        + f"_args = _json.loads({json.dumps(args_json or '[]')})\n"
        + (f"_res = {entry['call_name']}(*_args)\n" if isinstance(parsed, list)
           else f"_res = {entry['call_name']}(**_args)\n")
        + "print('SKILL_RESULT:', repr(_res)[:2000])\n")
    r = aios_sandbox.run_untrusted_code(program, lang="python",
                                        timeout=SKILL_TIMEOUT, now=now,
                                        receipt_log=receipt_log)
    if not r.sandboxed:
        return f"skill did not run (sandbox unavailable, fail closed): {r.reason}"
    tail = (r.stdout + ("\n" + r.stderr if r.stderr else ""))[-RUN_OUT_CAP:]
    return f"rc={r.returncode} timed_out={r.timed_out}\n{tail}"


# ---------------------------------------------------------------------------
# Prompts (Errata op-5/op-6 — identical initial state, arm-specific surface)
# ---------------------------------------------------------------------------

def _truncate(s: str, cap: int) -> str:
    return s if len(s) <= cap else (s[: cap // 2] + "\n…[truncated]…\n"
                                    + s[-cap // 2:])


def system_prompt(arm: str, task: dict, dispatch: dict | None) -> str:
    lines = [
        "You are an autonomous coding agent fixing a Python repository.",
        f"Goal: make the tests in {', '.join(task['test_paths'])} pass by "
        f"editing the source (NEVER the tests).",
        f"You have at most {K_TURNS} replies. Each reply may contain one or "
        "more ACTION commands; I execute them in order and return the "
        "results. Write real paths and commands directly after the colon — "
        "never placeholders, never angle brackets.",
        "",
        "The five actions, shown as concrete examples:",
        "",
        "ACTION: read scripts/example_module.py",
        "ACTION: run python -c 'import example_module'",
    ]
    if arm == "treatment":
        lines.append('ACTION: skill skill-0123abcd ["first_arg", 2]')
    lines += [
        "ACTION: write scripts/example_module.py",
        "```python",
        "# the COMPLETE new content of that file goes in this fenced block,",
        "# immediately after the write line",
        "```",
        "ACTION: done",
        "",
        "Rules:",
        "- You CANNOT run the grading tests; they execute once after you "
        "finish. Commands referencing the test files or tests/ are refused. "
        "You may write and run your own scratch scripts instead.",
        "- Writes under tests/ are refused and score the attempt as FAILED.",
        "- `write` replaces the whole file: always provide COMPLETE content.",
        "- Finish with ACTION: done when the source is fixed (or after your "
        "last reply the grading run happens anyway).",
    ]
    if arm == "treatment" and dispatch and dispatch["entries"]:
        lines += ["", "Verified skills you can invoke (sandbox-tested "
                      "primitives; you see only their return value):"]
        for e in dispatch["entries"]:
            lines.append(f"- id={e['id']} call={e['call_name']}"
                         f"({e['n_required_args']} required args) — "
                         f"{_truncate(e['applicability'], 200)}")
        lines.append("Invoke one by its id, e.g.: ACTION: skill "
                     f"{dispatch['entries'][0]['id']} []")
    return "\n".join(lines)


def initial_state(task: dict, ws: Path, trace: str,
                  listing: list[str]) -> str:
    src_path = ws / task["script_path"]
    src = (src_path.read_text(encoding="utf-8", errors="replace")
           if src_path.exists() else "")
    src_note = ("(the file does not exist yet — you must create it)"
                if not src_path.exists() else "")
    test_blocks = []
    for tp in task["test_paths"]:
        body = (ws / tp).read_text(encoding="utf-8", errors="replace")
        test_blocks.append(f"## Failing test file: {tp}\n```python\n{body}\n```")
    shown = listing[:LISTING_CAP]
    more = len(listing) - len(shown)
    listing_txt = "\n".join(shown) + (f"\n(+{more} more files)" if more > 0
                                      else "")
    return (
        "## Failing test output (grading run, captured before this session)\n"
        "```\n" + _truncate(trace, TRACE_CAP) + "\n```\n\n"
        + "\n\n".join(test_blocks)
        + f"\n\n## Current source file: {task['script_path']} {src_note}\n"
        + f"```python\n{src}\n```\n\n"
        + "## Files you may read/edit\n" + listing_txt
    )


# ---------------------------------------------------------------------------
# Episode
# ---------------------------------------------------------------------------

def _safe_rel(ws: Path, path: str) -> str | None:
    """Normalize a model-supplied path to a ws-relative string, or None when
    it escapes the workspace."""
    p = (ws / path).resolve()
    try:
        return str(p.relative_to(ws.resolve()))
    except ValueError:
        return None


def run_episode(task: dict, arm: str, model: str,
                repo_root: Path | str = REPO_ROOT,
                state_dir: Path | str | None = None,
                call_timeout: float = 2400.0, oracle_timeout: float = 300.0,
                ws: Path | str | None = None, model_fn=None,
                induce: bool = True, max_turns: int | None = None,
                extra_context: str = "") -> dict:
    """Run ONE K-turn episode; return the per-task record.

    arm='control' -> state_dir forced None (registry structurally wiped).
    model_fn(messages)->text overrides the ollama call (tests only).

    `max_turns` caps the loop below K (default K_TURNS). G5 uses it to split one
    episode around a forced death: j turns before, K-j after, with the budget
    identical across arms so no arm can win by thinking longer.
    `extra_context` is appended to the opening state — G5 puts the recovering
    agent's resume pack there. Both default to the plain K-turn behaviour, so
    the Channel-E protocol is unchanged.
    """
    assert arm in ("control", "treatment"), arm
    if arm == "control":
        state_dir = None
    state_dir = Path(state_dir) if state_dir is not None else None
    receipt_log = (state_dir / "sandbox_receipts.jsonl") if state_dir else None
    registry = (state_dir / "skills" / "registry.jsonl") if state_dir else None

    own_ws = ws is None
    if own_ws:
        ws = ws_mod.materialize(repo_root, task["commit"],
                                task["parent_commit"], task["script_path"],
                                task["test_paths"])
    ws = Path(ws)

    record: dict = {
        "schema": SCHEMA, "task_id": task["task_id"], "arm": arm,
        "model": model, "passed": None, "infra_error": None,
        "tests_tampered": [], "oracle": None, "turns_used": 0,
        "actions": [], "dispatch_invocations": 0, "oracle_block_attempts": 0,
        "oracle_leak": False, "closure": None, "dispatch_surface": None,
        "wrote_target": False, "prompt_chars": 0, "tokens": [],
        "wall_s": None, "fail_reason": None,
    }
    t0 = time.time()
    try:
        snapshot = ws_mod.tests_snapshot(ws)
        existing_files = {str(p.relative_to(ws))
                          for p in ws.rglob("*") if p.is_file()}

        # -- failing trace: captured in a THROWAWAY copy of the (still
        # untouched) episode workspace, then discarded (Errata op-6) --
        trace_ws = Path(tempfile.mkdtemp(prefix="phase5e-trace-"))
        try:
            shutil.rmtree(trace_ws)
            shutil.copytree(ws, trace_ws)
            trace = capture_failing_output(trace_ws, task["oracle_cmd"],
                                           timeout=oracle_timeout)
        finally:
            shutil.rmtree(trace_ws, ignore_errors=True)

        # -- arm surface --
        ix_all = ast_index.build_index(ws)
        if arm == "treatment":
            surf = ast_index.compute_surface(ws, trace, task["test_paths"],
                                             task["script_path"])
            allowed = set(surf["files"]) | set(task["test_paths"])
            record["closure"] = {k: surf[k] for k in
                                 ("n_files", "n_repo_py_files",
                                  "differs_from_whole_repo",
                                  "target_in_closure", "frames")}
            record["closure"]["files"] = surf["files"]
            listing = surf["files"]
            dispatch = build_dispatch_surface(task, registry)
            record["dispatch_surface"] = {
                "n": len(dispatch["entries"]),
                "ids": [e["id"] for e in dispatch["entries"]],
                "excluded_same_target": dispatch["excluded_same_target"],
                "capped": dispatch["capped"],
                "n_registry": dispatch["n_registry"]}
            by_id = {e["id"]: e for e in dispatch["entries"]}
            by_name = {e["call_name"]: e for e in dispatch["entries"]}
        else:
            allowed = None  # whole repo
            listing = ix_all.py_files
            dispatch, by_id, by_name = None, {}, {}

        sys_msg = system_prompt(arm, task, dispatch)
        init_msg = initial_state(task, ws, trace, listing)
        if extra_context:
            init_msg = init_msg + "\n\n" + extra_context
        record["prompt_chars"] = len(sys_msg) + len(init_msg)
        messages = [{"role": "system", "content": sys_msg},
                    {"role": "user", "content": init_msg}]

        # -- K-turn loop --
        done = False
        turn_budget = K_TURNS if max_turns is None else max(0, int(max_turns))
        record["turn_budget"] = turn_budget
        for turn in range(1, turn_budget + 1):
            try:
                if model_fn is not None:
                    text = model_fn(messages)
                    meta = {}
                else:
                    text, meta = call_chat(model, messages,
                                           timeout=call_timeout)
            except InfraError as exc:
                record["infra_error"] = str(exc)
                return record  # passed stays None (§6 carry-over)
            record["turns_used"] = turn
            if meta:
                record["tokens"].append(meta)
            messages.append({"role": "assistant", "content": text})

            actions = parse_actions(text)
            results: list[str] = []
            for act in actions:
                kind = act["kind"]
                logent: dict = {"turn": turn, "kind": kind}
                if kind == "done":
                    done = True
                    logent["arg"] = ""
                    record["actions"].append(logent)
                    break

                if kind == "read":
                    rel = _safe_rel(ws, act["arg"])
                    logent["arg"] = act["arg"][:200]
                    if rel is None:
                        res = f"read {act['arg']}: refused (outside workspace)"
                        logent["blocked"] = "outside_workspace"
                    elif (allowed is not None and rel in existing_files
                          and rel not in allowed):
                        res = (f"read {rel}: refused (outside your file "
                               "surface for this task)")
                        logent["blocked"] = "masked"
                    elif not (ws / rel).is_file():
                        res = f"read {rel}: no such file"
                    else:
                        body = (ws / rel).read_text(encoding="utf-8",
                                                    errors="replace")
                        res = (f"## {rel}\n```\n{_truncate(body, READ_CAP)}"
                               "\n```")
                elif kind == "write":
                    rel = _safe_rel(ws, act["path"])
                    logent["arg"] = act["path"][:200]
                    if rel is None:
                        res = f"write {act['path']}: refused (outside workspace)"
                        logent["blocked"] = "outside_workspace"
                    elif act["content"] is None:
                        res = (f"write {rel}: no fenced code block found "
                               "after the ACTION line — nothing written")
                        logent["blocked"] = "no_content"
                    elif rel.startswith("tests/"):
                        res = (f"write {rel}: REFUSED — modifying tests "
                               "scores this attempt as FAILED")
                        logent["blocked"] = "tests_guard"
                    elif (allowed is not None and rel in existing_files
                          and rel not in allowed):
                        res = (f"write {rel}: refused (outside your file "
                               "surface for this task)")
                        logent["blocked"] = "masked"
                    else:
                        target = ws / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(act["content"], encoding="utf-8")
                        if rel == task["script_path"]:
                            record["wrote_target"] = True
                        res = f"write {rel}: ok ({len(act['content'])} chars)"
                elif kind == "run":
                    cmd = act["arg"]
                    logent["arg"] = cmd[:200]
                    reason = oracle_blocked(cmd, task["test_paths"])
                    if reason:
                        record["oracle_block_attempts"] += 1
                        logent["blocked"] = "oracle_guard"
                        res = (f"run: REFUSED — {reason}. The grading tests "
                               "run once after you finish; use your own "
                               "scratch scripts to check your work.")
                    else:
                        r = aios_sandbox.run_sandboxed(
                            ["bash", "-c", cmd], rw_paths=(str(ws),),
                            _workdir=str(ws), timeout=RUN_TIMEOUT,
                            allow_net=False, now=time.time(),
                            receipt_log=receipt_log)
                        if not r.sandboxed:
                            res = ("run: command did not run (sandbox "
                                   f"unavailable, fail closed): {r.reason}")
                            logent["blocked"] = "sandbox_unavailable"
                        else:
                            tail = (r.stdout + ("\n" + r.stderr
                                                if r.stderr else ""))
                            res = (f"rc={r.returncode} "
                                   f"timed_out={r.timed_out}\n"
                                   f"{_truncate(tail, RUN_OUT_CAP)}")
                            logent["rc"] = r.returncode
                elif kind == "skill":
                    logent["arg"] = f"{act['id']} {act['args_json']}"[:200]
                    if arm != "treatment":
                        res = "skill: not available"
                        logent["blocked"] = "not_treatment"
                    else:
                        entry = by_id.get(act["id"]) or by_name.get(act["id"])
                        if entry is None:
                            res = (f"skill {act['id']}: unknown id (see the "
                                   "skill list in the instructions)")
                            logent["blocked"] = "unknown_skill"
                        else:
                            record["dispatch_invocations"] += 1
                            res = exec_skill(entry, act["args_json"],
                                             now=time.time(),
                                             receipt_log=receipt_log)
                else:  # unreachable given the regex
                    res = f"unknown action {kind}"
                record["actions"].append(logent)
                results.append(f"### {kind} {logent.get('arg', '')}\n{res}")

            if done:
                break
            if not actions:
                results = ["No ACTION lines found in your reply. Use the "
                           "ACTION protocol from the instructions."]
            messages.append({"role": "user",
                             "content": "## Tool results\n\n"
                                        + "\n\n".join(results)})

        # -- post-episode: §6.1 guard, leak assertion, external oracle --
        record["tests_tampered"] = ws_mod.tests_tampered(ws, snapshot)
        record["oracle_leak"] = any(
            a["kind"] == "run" and "blocked" not in a
            and oracle_blocked(a.get("arg", ""), task["test_paths"])
            for a in record["actions"])

        record["oracle"] = run_oracle(ws, task["oracle_cmd"],
                                      timeout=oracle_timeout)
        if record["tests_tampered"]:
            record["passed"] = False
            record["fail_reason"] = "tests_diff_guard"
        else:
            record["passed"] = bool(record["oracle"]["ok"])
            if not record["passed"]:
                record["fail_reason"] = ("oracle_failed" if
                                         record["wrote_target"] or
                                         (ws / task["script_path"]).exists()
                                         else "target_never_written")

        # -- treatment: skill induction through the unchanged gate --
        if (arm == "treatment" and induce and record["passed"]
                and state_dir is not None):
            final_src_p = ws / task["script_path"]
            if final_src_p.exists():
                decision = aios_skills.induce_and_register(
                    f"make the tests in {', '.join(task['test_paths'])} pass "
                    f"by editing {task['script_path']}",
                    final_src_p.read_text(encoding="utf-8", errors="replace"),
                    now=time.time(), registry=registry,
                    manifest=state_dir / "skills" / "manifest.jsonl",
                    receipt_log=receipt_log)
                record["skill"] = {"verdict": decision.get("verdict"),
                                   "registered": decision.get("registered"),
                                   "id": decision.get("id")}
        return record
    finally:
        record["wall_s"] = round(time.time() - t0, 2)
        if own_ws:
            ws_mod.cleanup(ws)
