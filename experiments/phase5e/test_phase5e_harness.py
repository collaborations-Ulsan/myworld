#!/usr/bin/env python3
"""Channel-E harness unit tests — run BEFORE any arm (harness validation only,
never a result). Mirrors test_phase5_harness.py coverage for the new pieces:
action parsing, the §1.3 oracle-block rule, AST closure masking, dispatch
surface + same-target exclusion, the episode loop with a scripted model, and
the driver's analysis/gate math.

    /home/user/miniconda3/bin/python3 -m pytest -q experiments/phase5e/test_phase5e_harness.py
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ast_index  # noqa: E402
import run_arms_e  # noqa: E402
import turn_loop  # noqa: E402

ORACLE_PY = "/home/user/miniconda3/bin/python3"


# ---------------------------------------------------------------------------
# Action parsing (Errata op-5)
# ---------------------------------------------------------------------------

def test_parse_actions_mixed():
    text = textwrap.dedent("""\
        Let me look around first.
        ACTION: read scripts/util.py
        ACTION: run python -c "print(1)"
        ACTION: skill skill-abc ["x", 2]
        ACTION: write mod.py
        ```python
        def f():
            return 1
        ```
        ACTION: done
        """)
    acts = turn_loop.parse_actions(text)
    kinds = [a["kind"] for a in acts]
    assert kinds == ["read", "run", "skill", "write", "done"]
    assert acts[0]["arg"] == "scripts/util.py"
    assert acts[2]["id"] == "skill-abc"
    assert json.loads(acts[2]["args_json"]) == ["x", 2]
    assert "def f():" in acts[3]["content"]


def test_parse_write_without_fence_and_fence_scoping():
    text = ("ACTION: write a.py\nno fence here\n"
            "ACTION: write b.py\n```python\nB = 1\n```\n")
    acts = turn_loop.parse_actions(text)
    assert acts[0]["content"] is None      # fence after next ACTION not stolen
    assert acts[1]["content"] == "B = 1\n"


def test_parse_actions_none():
    assert turn_loop.parse_actions("I think the fix is obvious.") == []


def test_parse_actions_unwraps_decorative_brackets():
    """Smoke round 1 finding: the model copies template placeholders
    literally (`ACTION: read <path>`); wrapping is stripped, both arms."""
    text = ("ACTION: read <scripts/util.py>\n"
            "ACTION: run `python -c 'print(1)'`\n"
            "ACTION: skill <skill-abc> [1]\n"
            "ACTION: write '<a.py>'\n```python\nA = 1\n```\n")
    acts = turn_loop.parse_actions(text)
    assert acts[0]["arg"] == "scripts/util.py"
    assert acts[1]["arg"] == "python -c 'print(1)'"
    assert acts[2]["id"] == "skill-abc"
    assert acts[3]["path"] == "a.py"


# ---------------------------------------------------------------------------
# §1.3 oracle-block rule (Errata op-1)
# ---------------------------------------------------------------------------

TPS = ["tests/test_mod.py"]


@pytest.mark.parametrize("cmd", [
    "python -m pytest -q tests/test_mod.py",
    "pytest tests/test_mod.py",
    "python -m pytest test_mod.py",
    "cat tests/test_mod.py",
    "pytest",                      # bare pytest would collect tests/
    "python -m pytest -q",
    "ls tests/",
])
def test_oracle_blocked(cmd):
    assert turn_loop.oracle_blocked(cmd, TPS) is not None


@pytest.mark.parametrize("cmd", [
    "python -c 'import mod; print(mod.f())'",
    "python scratch_check.py",
    "pytest scratch_check.py",     # explicit non-tests target allowed
    "ls scripts",
])
def test_oracle_allowed(cmd):
    assert turn_loop.oracle_blocked(cmd, TPS) is None


# ---------------------------------------------------------------------------
# AST index + closure (Errata op-2)
# ---------------------------------------------------------------------------

@pytest.fixture()
def synth_ws(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "a.py").write_text("import b\n\ndef f():\n    return b.g()\n")
    (tmp_path / "b.py").write_text("import c\n\ndef g():\n    return c.h()\n")
    (tmp_path / "c.py").write_text("def h():\n    return 41\n")
    (tmp_path / "d.py").write_text("def unrelated():\n    return 0\n")
    (tmp_path / "tests" / "test_a.py").write_text(
        "import a\n\ndef test_f():\n    assert a.f() == 42\n")
    return tmp_path


def test_closure_k2_and_surface(synth_ws: Path):
    trace = ('File "tests/test_a.py", line 4, in test_f\n'
             "    assert a.f() == 42\nAssertionError")
    surf = ast_index.compute_surface(synth_ws, trace, ["tests/test_a.py"],
                                     "a.py")
    # seeds: test_f -> hop1 f -> hop2 g. h is 3 hops out; d.py unrelated.
    assert "a.py" in surf["files"] and "b.py" in surf["files"]
    assert "tests/test_a.py" in surf["files"]
    assert "d.py" not in surf["files"]
    assert surf["differs_from_whole_repo"] is True
    assert surf["target_in_closure"] is True


def test_closure_fallback_seeds_test_defs(synth_ws: Path):
    surf = ast_index.compute_surface(synth_ws, "no frames here",
                                     ["tests/test_a.py"], "a.py")
    # fallback: test file's own defs seed the closure; a.py reachable via call
    assert "tests/test_a.py" in surf["files"]
    assert "a.py" in surf["files"]
    assert "d.py" not in surf["files"]


def test_trace_frames_short_style(synth_ws: Path):
    out = "tests/test_a.py:4: in test_f\n    assert a.f() == 42\n"
    frames = ast_index.trace_frames(out, synth_ws)
    assert ("tests/test_a.py", "test_f") in frames


# ---------------------------------------------------------------------------
# Episode fixture — a real (tiny) task with a real pytest oracle
# ---------------------------------------------------------------------------

def make_task_ws(tmp_path: Path) -> tuple[dict, Path]:
    ws = tmp_path / "ws"
    (ws / "tests").mkdir(parents=True)
    (ws / "mod.py").write_text("def add(a, b):\n    return a - b  # bug\n")
    (ws / "other.py").write_text("def helper():\n    return 7\n")
    (ws / "tests" / "test_mod.py").write_text(
        "import mod\n\ndef test_add():\n    assert mod.add(2, 3) == 5\n")
    task = {"task_id": "p5e-test-0000", "script_path": "mod.py",
            "test_paths": ["tests/test_mod.py"],
            "oracle_cmd": [ORACLE_PY, "-m", "pytest", "-q", "-p",
                           "no:cacheprovider", "tests/test_mod.py"],
            "commit": "unused", "parent_commit": "unused"}
    return task, ws


FIXED = "def add(a, b):\n    return a + b\n"


def scripted(responses: list[str]):
    it = iter(responses)

    def fn(messages: list[dict]) -> str:
        return next(it)
    return fn


def test_episode_control_pass(tmp_path: Path):
    task, ws = make_task_ws(tmp_path)
    rec = turn_loop.run_episode(
        task, arm="control", model="stub", ws=ws,
        model_fn=scripted([
            "ACTION: run pytest\nACTION: read mod.py",
            f"ACTION: write mod.py\n```python\n{FIXED}```\nACTION: done",
        ]))
    assert rec["infra_error"] is None
    assert rec["passed"] is True
    assert rec["turns_used"] == 2
    assert rec["oracle_block_attempts"] == 1   # bare pytest refused
    assert rec["oracle_leak"] is False
    assert rec["wrote_target"] is True
    assert rec["closure"] is None              # control: no masking
    assert rec["tests_tampered"] == []


def test_episode_treatment_masking_and_scratch(tmp_path: Path):
    task, ws = make_task_ws(tmp_path)
    state = tmp_path / "state"
    rec = turn_loop.run_episode(
        task, arm="treatment", model="stub", ws=ws, state_dir=state,
        induce=False,
        model_fn=scripted([
            # other.py exists but is outside the closure -> masked;
            # scratch.py is NEW -> allowed
            "ACTION: read other.py\n"
            "ACTION: write scratch.py\n```python\nprint('probe')\n```",
            f"ACTION: write mod.py\n```python\n{FIXED}```\nACTION: done",
        ]))
    assert rec["passed"] is True
    cl = rec["closure"]
    assert cl["differs_from_whole_repo"] is True
    assert cl["target_in_closure"] is True     # trace reaches mod.py
    blocked = [a for a in rec["actions"] if a.get("blocked") == "masked"]
    assert [a["arg"] for a in blocked] == ["other.py"]
    writes = [a for a in rec["actions"]
              if a["kind"] == "write" and "blocked" not in a]
    assert {a["arg"] for a in writes} == {"scratch.py", "mod.py"}


def test_episode_tests_write_guard(tmp_path: Path):
    task, ws = make_task_ws(tmp_path)
    rec = turn_loop.run_episode(
        task, arm="control", model="stub", ws=ws,
        model_fn=scripted([
            "ACTION: write tests/test_mod.py\n```python\nassert True\n```\n"
            f"ACTION: write mod.py\n```python\n{FIXED}```\nACTION: done",
        ]))
    guard = [a for a in rec["actions"] if a.get("blocked") == "tests_guard"]
    assert guard, "tests/ write must be refused at the tool layer"
    assert rec["tests_tampered"] == []         # refused write never landed
    assert rec["passed"] is True


def test_episode_turn_budget_and_no_write(tmp_path: Path):
    task, ws = make_task_ws(tmp_path)
    rec = turn_loop.run_episode(
        task, arm="control", model="stub", ws=ws,
        model_fn=scripted(["thinking..."] * turn_loop.K_TURNS))
    assert rec["turns_used"] == turn_loop.K_TURNS
    assert rec["passed"] is False
    assert rec["fail_reason"] == "oracle_failed"  # buggy source still present


def test_episode_infra_error_records_none(tmp_path: Path):
    task, ws = make_task_ws(tmp_path)

    def dying(messages):
        raise turn_loop.InfraError("ollama chat failed: simulated")
    rec = turn_loop.run_episode(task, arm="control", model="stub", ws=ws,
                                model_fn=dying)
    assert rec["passed"] is None
    assert "simulated" in rec["infra_error"]


# ---------------------------------------------------------------------------
# Dispatch surface (§2a + Errata op-4)
# ---------------------------------------------------------------------------

SKILL_CODE = "def double(x):\n    return 2 * x\n"


def _write_registry(reg: Path, skills: list[dict]) -> None:
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text("".join(json.dumps(s) + "\n" for s in skills),
                   encoding="utf-8")


def _mk_skill(sid: str, goal: str, code: str = SKILL_CODE) -> dict:
    return {"schema": "aios.skill.v1", "id": sid, "name": "double",
            "code": code, "applicability": f"use when: {goal}",
            "example": {}, "unit_test": "assert double(2) == 4",
            "provenance": {"source_goal": goal}, "created_ts": 0.0}


def test_dispatch_surface_same_target_excluded(tmp_path: Path):
    reg = tmp_path / "skills" / "registry.jsonl"
    task = {"task_id": "t", "script_path": "mod.py",
            "test_paths": ["tests/test_mod.py"]}
    _write_registry(reg, [
        _mk_skill("skill-same", "make tests pass by editing mod.py"),
        _mk_skill("skill-other", "make tests pass by editing scripts/x.py"),
    ])
    surf = turn_loop.build_dispatch_surface(task, reg)
    assert [e["id"] for e in surf["entries"]] == ["skill-other"]
    assert surf["excluded_same_target"] == ["skill-same"]
    assert surf["entries"][0]["call_name"] == "double"


@pytest.mark.skipif(
    not (__import__("aios_sandbox").engine_status().get("native_works")
         or __import__("aios_sandbox").engine_status().get("bwrap_works")),
    reason="no sandbox engine — dispatch execution is fail-closed")
def test_exec_skill_runs_in_sandbox(tmp_path: Path):
    entry = {"call_name": "double", "_skill": _mk_skill("s", "g")}
    out = turn_loop.exec_skill(entry, "[21]", now=0.0, receipt_log=None)
    assert "SKILL_RESULT: 42" in out


# ---------------------------------------------------------------------------
# Driver math + gates
# ---------------------------------------------------------------------------

def test_main_tasks_is_full_nonholdout_pool():
    tasks = run_arms_e.main_tasks()
    assert len(tasks) == 32
    assert [t["epoch"] for t in tasks] == sum(([e] * 8 for e in
                                               (1, 2, 3, 4)), [])
    seqs = [t["ts_epoch"] for t in tasks]
    assert seqs == sorted(seqs)


def test_mcnemar_and_power():
    assert run_arms_e.mcnemar_one_sided(0, 0) is None
    assert run_arms_e.mcnemar_one_sided(3, 0) == pytest.approx(0.125)
    p = run_arms_e.power_at(0.15, 0.15, 32)
    assert p is not None and 0.0 < p < 1.0
    assert run_arms_e.power_at(0.2, 0.1, 32) is None  # delta > p_disc


def test_validity_gate_void_and_pass():
    tasks = [{"task_id": "t1", "epoch": 1}, {"task_id": "t2", "epoch": 1}]
    base = {"kind": "attempt", "passed": True, "infra_error": None}
    inert = {("treatment", "t1"): {**base, "dispatch_invocations": 0,
                                   "closure": {"differs_from_whole_repo":
                                               False}},
             ("treatment", "t2"): {**base, "dispatch_invocations": 0,
                                   "closure": {"differs_from_whole_repo":
                                               False}}}
    assert run_arms_e.validity_gate(inert, tasks)["passed"] is False
    active = dict(inert)
    active[("treatment", "t2")] = {**base, "dispatch_invocations": 0,
                                   "closure": {"differs_from_whole_repo":
                                               True}}
    assert run_arms_e.validity_gate(active, tasks)["passed"] is True


def test_analyze_kill_rule_fields():
    tasks = [{"task_id": f"t{i}", "epoch": i // 8 + 1} for i in range(32)]
    atts = {}
    for i, t in enumerate(tasks):
        atts[("control", t["task_id"])] = {
            "kind": "attempt", "passed": i % 4 == 0, "infra_error": None,
            "turns_used": 3, "oracle_leak": False}
        atts[("treatment", t["task_id"])] = {
            "kind": "attempt", "passed": i % 4 == 0, "infra_error": None,
            "turns_used": 2, "oracle_leak": False}
    an = run_arms_e.analyze(atts, tasks)
    assert an["n_pairs"] == 32
    assert an["C_overall"] == 0.0
    assert an["kill_rule"]["C_overall_le_0"] is True
    assert an["discordant_rate"] == 0.0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
