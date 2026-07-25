#!/usr/bin/env python3
"""QA for the Phase 5 harness (prereg: docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md).

Every claim is proven against a REAL fabricated git repo and REAL pytest
subprocess runs — no mocked oracle. The only mocked component is the ollama
model call (model_fn), which the prereg does not govern.

Proves:
  1. task construction KEEPS a valid candidate and DROPS already-passing and
     unsolvable candidates, with recorded reasons;
  2. the materialized workspace has no .git, has the REVERTED source, and the
     POST-commit test file; invariant violations raise loudly;
  3. the oracle result comes from a real pytest run (fails on reverted source,
     passes on restored solution);
  4. a diff touching tests/ scores the attempt FAIL even when the oracle
     passes (prereg §6.1);
  5. injection is EMPTY for control and NON-EMPTY for treatment when
     artifacts exist (prereg §3), and treatment experience persists;
  6. infra errors are recorded as infra (passed=None), never as losses
     (prereg §6.6).

Run:  python3 -m pytest -q experiments/phase5/test_phase5_harness.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_tasks  # noqa: E402
import runner  # noqa: E402
import workspace as ws_mod  # noqa: E402

CALC_BUGGY = "def add(a, b):\n    return a - b\n"
CALC_FIXED = "def add(a, b):\n    return a + b\n"
TEST_CALC_V0 = (
    "import pathlib\nimport sys\n\n"
    "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n\n"
    "from scripts.calc import add\n\n\n"
    "def test_add():\n    assert add(2, 3) == 5\n"
)
TEST_CALC_V1 = TEST_CALC_V0 + "\n\ndef test_add_zero():\n    assert add(0, 0) == 0\n"


def _git(repo: Path, *args: str) -> None:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"git {args}: {r.stderr}"


def _commit_all(repo: Path, msg: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=qa@phase5", "-c", "user.name=qa",
         "commit", "-q", "-m", msg)


@pytest.fixture(scope="module")
def fake_repo(tmp_path_factory) -> Path:
    """Mini repo with: 1 valid task commit, 1 already-passing candidate,
    1 unsolvable candidate."""
    repo = tmp_path_factory.mktemp("phase5-fake-repo")
    (repo / "scripts").mkdir()
    (repo / "tests").mkdir()
    _git(repo, "init", "-q")
    (repo / "scripts" / "__init__.py").write_text("")
    (repo / "scripts" / "calc.py").write_text(CALC_BUGGY)
    (repo / "scripts" / "other.py").write_text("def f():\n    return 1\n")
    (repo / "scripts" / "broken.py").write_text("def g():\n    return 0\n")
    (repo / "tests" / "test_calc.py").write_text(TEST_CALC_V0)
    (repo / "tests" / "test_other.py").write_text(
        "import pathlib, sys\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
        "from scripts.other import f\n\n\n"
        "def test_f():\n    assert f() == 1\n")
    (repo / "tests" / "test_broken.py").write_text(
        "import pathlib, sys\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
        "from scripts.broken import g\n\n\n"
        "def test_g():\n    assert g() == 0\n")
    _commit_all(repo, "root: buggy calc, fine other, fine broken")

    # C1 — VALID task: fixes calc.py, updates its test. Parent fails, post passes.
    (repo / "scripts" / "calc.py").write_text(CALC_FIXED)
    (repo / "tests" / "test_calc.py").write_text(TEST_CALC_V1)
    _commit_all(repo, "fix add")

    # C2 — DROP (already passing): cosmetic change, parent already green.
    (repo / "scripts" / "other.py").write_text(
        '"""doc."""\n\n\ndef f():\n    return 1\n')
    (repo / "tests" / "test_other.py").write_text(
        (repo / "tests" / "test_other.py").read_text() + "\n# comment\n")
    _commit_all(repo, "cosmetic other")

    # C3 — DROP (unsolvable): post-commit code does not satisfy its own test.
    (repo / "scripts" / "broken.py").write_text("def g():\n    return 2\n")
    (repo / "tests" / "test_broken.py").write_text(
        "import pathlib, sys\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
        "from scripts.broken import g\n\n\n"
        "def test_g():\n    assert g() == 3\n")
    _commit_all(repo, "broken change")
    return repo


@pytest.fixture(scope="module")
def built(fake_repo: Path) -> dict:
    return build_tasks.build(fake_repo, max_commits=20, oracle_timeout=60.0)


@pytest.fixture(scope="module")
def valid_task(built: dict) -> dict:
    assert built["n_tasks"] == 1
    return built["tasks"][0]


# -- 1. construction keeps/drops ---------------------------------------------

def test_build_keeps_valid_candidate(built: dict) -> None:
    assert built["n_tasks"] == 1
    t = built["tasks"][0]
    assert t["script_path"] == "scripts/calc.py"
    assert t["test_paths"] == ["tests/test_calc.py"]
    assert t["oracle_cmd_sha256"]
    assert t["preflight"]["solution_passed"] >= 1


def test_build_drops_already_passing_and_unsolvable(built: dict) -> None:
    reasons = {d["script_path"]: d["reason"] for d in built["dropped"]}
    assert reasons["scripts/other.py"] == \
        "already_passing_with_parent_source_no_signal"
    assert reasons["scripts/broken.py"] == \
        "not_passing_with_postcommit_source_unsolvable"


# -- 2. workspace invariants --------------------------------------------------

def test_workspace_invariants(fake_repo: Path, valid_task: dict) -> None:
    t = valid_task
    ws = ws_mod.materialize(fake_repo, t["commit"], t["parent_commit"],
                            t["script_path"], t["test_paths"])
    try:
        assert not list(ws.rglob(".git")), ".git leaked into workspace"
        assert (ws / "scripts" / "calc.py").read_text() == CALC_BUGGY, \
            "source not reverted to parent state"
        assert (ws / "scripts" / "calc.py").read_text() != CALC_FIXED, \
            "workspace shows the post-commit solution"
        assert (ws / "tests" / "test_calc.py").read_text() == TEST_CALC_V1, \
            "post-commit test file not kept"
    finally:
        ws_mod.cleanup(ws)


def test_workspace_invariant_violation_raises(fake_repo: Path,
                                              valid_task: dict) -> None:
    t = valid_task
    ws = ws_mod.materialize(fake_repo, t["commit"], t["parent_commit"],
                            t["script_path"], t["test_paths"])
    try:
        (ws / ".git").mkdir()  # sabotage
        with pytest.raises(ws_mod.WorkspaceInvariantError):
            ws_mod.assert_invariants(ws, fake_repo, t["commit"],
                                     t["parent_commit"], t["script_path"],
                                     t["test_paths"])
    finally:
        ws_mod.cleanup(ws)


# -- 3. oracle = a real pytest run --------------------------------------------

def test_oracle_result_from_real_pytest(fake_repo: Path,
                                        valid_task: dict) -> None:
    t = valid_task
    ws = ws_mod.materialize(fake_repo, t["commit"], t["parent_commit"],
                            t["script_path"], t["test_paths"])
    try:
        res_fail = runner.run_oracle(ws, t["oracle_cmd"], timeout=60)
        assert not res_fail["ok"] and res_fail["rc"] != 0
        ws_mod.restore_solution(ws, fake_repo, t["commit"], t["script_path"])
        res_pass = runner.run_oracle(ws, t["oracle_cmd"], timeout=60)
        assert res_pass["ok"] and res_pass["passed"] >= 1
    finally:
        ws_mod.cleanup(ws)


# -- 4. §6.1 guard: tests/ diff => FAIL even when the oracle passes -----------

def test_tests_diff_guard_fails_despite_green_oracle(fake_repo: Path,
                                                     valid_task: dict) -> None:
    t = valid_task
    ws = ws_mod.materialize(fake_repo, t["commit"], t["parent_commit"],
                            t["script_path"], t["test_paths"])

    def tampering_model(prompt: str) -> str:
        # A rogue edit channel: overwrite the test with a trivially green one
        # AND return the correct solution. The oracle will pass; the guard
        # must still score FAIL.
        (ws / "tests" / "test_calc.py").write_text(
            "def test_ok():\n    pass\n")
        return f"```python\n{CALC_FIXED}```"

    rec = runner.run_task(t, arm="control", model="mock", repo_root=fake_repo,
                          ws=ws, model_fn=tampering_model, oracle_timeout=60)
    ws_mod.cleanup(ws)
    assert rec["oracle"]["ok"] is True, "precondition: oracle must pass"
    assert rec["tests_tampered"], "guard did not detect the tests/ diff"
    assert rec["passed"] is False
    assert rec["fail_reason"] == "tests_diff_guard"


# -- happy path through run_task (mock model, real oracle) --------------------

def test_run_task_pass_and_fail_paths(fake_repo: Path,
                                      valid_task: dict) -> None:
    t = valid_task
    good = runner.run_task(t, arm="control", model="mock",
                           repo_root=fake_repo, oracle_timeout=60,
                           model_fn=lambda p: f"```python\n{CALC_FIXED}```")
    assert good["passed"] is True and good["infra_error"] is None
    bad = runner.run_task(t, arm="control", model="mock",
                          repo_root=fake_repo, oracle_timeout=60,
                          model_fn=lambda p: "```python\n"
                                             "def add(a, b):\n"
                                             "    return a * b\n```")
    assert bad["passed"] is False and bad["fail_reason"] == "oracle_failed"


# -- 5. injection: control empty, treatment non-empty -------------------------

def test_injection_control_empty_treatment_nonempty(fake_repo: Path,
                                                    valid_task: dict,
                                                    tmp_path: Path) -> None:
    t = valid_task
    text = runner.task_text(t)
    assert runner.build_injection(text, None) == ""

    state = tmp_path / "state"
    (state / "runs").mkdir(parents=True)
    (state / "skills").mkdir(parents=True)
    # Artifact 1: a prior-experience run log (aios_experience-compatible).
    (state / "runs" / "p5-prior.jsonl").write_text(
        json.dumps({"kind": "session_meta", "run_id": "p5-prior",
                    "agent": "phase5-treatment",
                    "ts": "2026-07-26T00:00:00+00:00", "git_sha": ""}) + "\n"
        + json.dumps({"kind": "outcome", "exit": "model_finished",
                      "turns": 1, "goal_hint": text}) + "\n")
    # Artifact 2: a registered skill (written directly for retrieval testing;
    # real registration goes through the aios_skills sandbox gate).
    (state / "skills" / "registry.jsonl").write_text(json.dumps({
        "id": "skill-test0000000000", "name": "calc_add_fix",
        "applicability": "use when: editing scripts/calc.py to make "
                         "tests in tests/test_calc.py pass",
        "code": CALC_FIXED, "unit_test": "assert callable(add)",
        "example": {}, "provenance": {}, "created_ts": 0,
    }) + "\n")

    inj = runner.build_injection(text, state)
    assert inj and "calc_add_fix" in inj and "Prior experience" in inj

    rec_c = runner.run_task(t, arm="control", model="mock",
                            repo_root=fake_repo, state_dir=state,
                            oracle_timeout=60,
                            model_fn=lambda p: f"```python\n{CALC_FIXED}```")
    assert rec_c["injection_nonempty"] is False
    assert rec_c["injected_chars"] == 0
    rec_t = runner.run_task(t, arm="treatment", model="mock",
                            repo_root=fake_repo, state_dir=state,
                            oracle_timeout=60, induce=False,
                            model_fn=lambda p: f"```python\n{CALC_FIXED}```")
    assert rec_t["injection_nonempty"] is True
    assert rec_t["injected_chars"] > 0


def test_treatment_experience_persists(fake_repo: Path, valid_task: dict,
                                       tmp_path: Path) -> None:
    """After one treatment episode on an EMPTY substrate, the run log exists
    and a second episode retrieves non-empty injection from it."""
    t = valid_task
    state = tmp_path / "state2"
    rec1 = runner.run_task(t, arm="treatment", model="mock",
                           repo_root=fake_repo, state_dir=state,
                           oracle_timeout=60, induce=False,
                           model_fn=lambda p: f"```python\n{CALC_FIXED}```")
    assert rec1["injection_nonempty"] is False  # nothing existed yet
    assert (state / "runs" / f"{t['task_id']}.jsonl").exists()
    rec2 = runner.run_task(t, arm="treatment", model="mock",
                           repo_root=fake_repo, state_dir=state,
                           oracle_timeout=60, induce=False,
                           model_fn=lambda p: f"```python\n{CALC_FIXED}```")
    assert rec2["injection_nonempty"] is True


# -- 6. infra errors are infra, not losses ------------------------------------

def test_infra_error_recorded_as_infra_not_fail(fake_repo: Path,
                                                valid_task: dict) -> None:
    def down(prompt: str) -> str:
        raise runner.InfraError("ollama down (simulated)")

    rec = runner.run_task(valid_task, arm="control", model="mock",
                          repo_root=fake_repo, model_fn=down)
    assert rec["infra_error"]
    assert rec["passed"] is None, "infra failure must NOT be scored as a loss"


# -- calibration selection rule (pure logic) ----------------------------------

def test_calibration_selection_rule() -> None:
    import calibrate
    models = [("s", 1.0), ("m", 2.0), ("l", 3.0)]

    def recs(model: str, passes: int, n: int = 8, infra: int = 0):
        out = []
        for i in range(n):
            out.append({"model": model, "task_id": f"t{i}",
                        "infra_error": "x" if i < infra else None,
                        "passed": (None if i < infra
                                   else i - infra < passes)})
        return out

    # smallest in-band wins: s=1/8 (out), m=3/8 (in), l=6/8 (out=0.75)
    records = recs("s", 1) + recs("m", 3) + recs("l", 6)
    s = calibrate.summarize(records, models)
    assert s["selected_student"] == "m"
    # nobody in band -> honest NOT RUN
    records = recs("s", 0) + recs("m", 1) + recs("l", 7)
    s = calibrate.summarize(records, models)
    assert s["selected_student"] is None
    assert "EXPERIMENT NOT RUN" in s["verdict"]
    # infra dropped from the denominator: 2 passes / (8-2 scored) = 0.333
    s = calibrate.summarize(recs("s", 2, infra=2), [("s", 1.0)])
    assert s["per_model"]["s"]["scored"] == 6
    assert s["per_model"]["s"]["P_auto"] == round(2 / 6, 4)
