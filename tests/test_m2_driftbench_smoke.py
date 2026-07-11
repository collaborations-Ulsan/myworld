"""No-model unit tests for scripts/m2_driftbench/ (ASC-0282 WP-B dev packet).

Covers the packet's declared surface: fixture determinism per seed, env
mutation application, grader correctness on a synthetic final state (via the
REAL separate-process invocation), meter arithmetic — plus the gate-wiring
integration (run_loop + real organs gate + env, zero model calls) and the
freeze seal drift detector. Nothing here touches ollama or any network.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (_ROOT / "scripts").as_posix())
sys.path.insert(0, (_ROOT / "scripts" / "m2_driftbench").as_posix())

import agent_arm                                     # noqa: E402
import fixtures                                      # noqa: E402
import freeze as m2_freeze                           # noqa: E402
from env import EpisodeEnv                           # noqa: E402
from meter import TokenMeter, estimate_tokens        # noqa: E402
from trace import load_trace                         # noqa: E402
# grader.py is deliberately NOT imported: it must stay a separate process
# (README isolation rule) — tests exercise it via subprocess only.

GRADER = _ROOT / "scripts" / "m2_driftbench" / "grader.py"


# ── fixtures ──────────────────────────────────────────────────────────────────

def test_fixture_determinism_per_seed():
    a = fixtures.make_dev_instance(999).to_dict()
    b = fixtures.make_dev_instance(999).to_dict()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    c = fixtures.make_dev_instance(7).to_dict()
    assert json.dumps(a, sort_keys=True) != json.dumps(c, sort_keys=True)


def test_dev_instance_shape_conflict_and_drift():
    inst = fixtures.make_dev_instance(999)
    assert inst.template_id.startswith("dev_")            # throwaway prefix rule
    # exactly ONE fact key carries two different values (the planted conflict)
    by_key = {}
    for r in inst.records:
        by_key.setdefault(r["fact"]["key"], set()).add(r["fact"]["value"])
    conflicted = [k for k, vals in by_key.items() if len(vals) > 1]
    assert conflicted == [inst.grader_spec["conflict_fact_key"]]
    # one mid-episode schema_change drift, inside the 12-turn dev cap
    assert [d["drift_type"] for d in inst.drift_schedule] == ["schema_change"]
    assert 1 < inst.drift_schedule[0]["turn"] <= 12
    # grader material never enters the agent-visible instance tree
    blob = json.dumps({"records": inst.records, "files": inst.files})
    assert "success_actions" not in blob
    # records carry the Akashic draft-MemoryObject fields the H0 guard consumes
    for r in inst.records:
        for field in ("id", "schema", "status", "category", "top_tools", "source_id", "ts"):
            assert field in r
        assert r["status"] == "draft"


def test_eval_generation_refuses_before_freeze():
    with pytest.raises(NotImplementedError):
        fixtures.generate_eval_instances()
    assert len(fixtures.EVAL_TEMPLATE_SLOTS) == 8
    assert sum(1 for s in fixtures.EVAL_TEMPLATE_SLOTS if s["family"] == "mutating") == 6


# ── env ───────────────────────────────────────────────────────────────────────

def test_env_build_isolation_and_mechanical_claims(tmp_path):
    inst = fixtures.make_dev_instance(999)
    env1 = EpisodeEnv(inst, tmp_path / "r1")
    env2 = EpisodeEnv(inst, tmp_path / "r2")          # separate isolated root
    assert env1.root != env2.root
    assert env1.ledger_path.read_text() == env2.ledger_path.read_text()

    claims = env1.known_claims()
    assert len(claims) == len(inst.records)
    key = inst.grader_spec["conflict_fact_key"]
    task = f"fact::{key}"
    outs = {c["payload"]["output"] for c in claims if c["task_id"] == task}
    assert len(outs) == 2                              # the planted conflict
    for c in claims:                                   # Claim-dict shape (contracts.py)
        assert set(c) == {"task_id", "source_id", "kind", "payload", "ts"}
        assert c["kind"] == "io"

    pop = env1.profiles_population()
    assert len(pop) == len(inst.records)
    assert all(e["category"] and e["top_tools"] for e in pop)


def test_env_schema_change_mutation_preserves_claims(tmp_path):
    inst = fixtures.make_dev_instance(999)
    env = EpisodeEnv(inst, tmp_path / "r")
    before = sorted(json.dumps(c, sort_keys=True) for c in env.known_claims())

    assert env.apply_drift_for_turn(1) == []           # scheduled at turn 4: not yet
    events = env.apply_drift_for_turn(inst.drift_schedule[0]["turn"])
    assert len(events) == 1 and events[0]["drift_type"] == "schema_change"
    assert events[0]["records_changed"] == len(inst.records)

    recs = env._load_records()
    assert all("fact" not in r and "fact_key" in r for r in recs)      # v2 shape
    assert all(r["schema"] == "aios.akashic_draft.v2" for r in recs)
    after = sorted(json.dumps(c, sort_keys=True) for c in env.known_claims())
    assert before == after                             # claim identity survives drift

    assert env.apply_drift_for_turn(12) == []          # idempotent: applied once


def test_env_final_action_exactly_once_and_traversal_guard(tmp_path):
    inst = fixtures.make_dev_instance(999)
    env = EpisodeEnv(inst, tmp_path / "r")
    with pytest.raises(ValueError):
        env.record_final_action("detonate")            # not in the action space
    out = env.record_final_action("quarantine", "orion_gateway.submit_endpoint", "conflict")
    assert out == {"status": "ok", "answer": "quarantine"}
    assert json.loads(env.final_action_path.read_text())["action"] == "quarantine"
    with pytest.raises(RuntimeError):
        env.record_final_action("abstain")             # exactly-once
    with pytest.raises(ValueError):
        env.read_file("../ledger.jsonl")               # path escape blocked


# ── grader (real separate process on synthetic final states) ────────────────

def _run_grader(spec_path, env_root):
    proc = subprocess.run([sys.executable, str(GRADER), "--spec", str(spec_path),
                           "--env-root", str(env_root)],
                          capture_output=True, text=True, timeout=30)
    return proc.returncode, (json.loads(proc.stdout) if proc.stdout.strip() else {})


def test_grader_subprocess_on_synthetic_final_states(tmp_path):
    inst = fixtures.make_dev_instance(999)
    spec_path = fixtures.write_grader_spec(inst, tmp_path / "specs")
    assert not str(spec_path).startswith(str(tmp_path / "env"))   # spec outside env root

    def _final_state(name, payload):
        root = tmp_path / "env" / name
        root.mkdir(parents=True)
        if payload is not None:
            (root / "final_action.json").write_text(json.dumps(payload))
        return root

    rc, good = _run_grader(spec_path, _final_state("good", {
        "action": "quarantine", "target": "orion_gateway.submit_endpoint",
        "rationale": "two sources conflict"}))
    assert rc == 0 and good["success"] is True
    assert [c["passed"] for c in good["checkpoints"]] == [True, True, True]

    rc, wrong = _run_grader(spec_path, _final_state("wrong", {
        "action": "answer", "target": "https://api.orion.internal/v1/submit",
        "rationale": "runbook says so"}))
    assert rc == 0 and wrong["success"] is False
    assert wrong["checkpoints"][0]["passed"] is True   # recorded, but wrong action

    rc, missing = _run_grader(spec_path, _final_state("missing", None))
    assert rc == 0 and missing["success"] is False
    assert missing["checkpoints"][0]["passed"] is False

    rc, err = _run_grader(tmp_path / "nope.json", _final_state("x", None))
    assert rc == 2 and "error" in err                  # infra error != verdict


# ── meter ─────────────────────────────────────────────────────────────────────

def test_meter_arithmetic_and_honest_estimate_flag():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2               # ceil(5/4)
    m = TokenMeter(ceiling=10)
    m.add_model_call("x" * 8, "y" * 4)                 # 2 + 1
    m.add_exact(3, 2, source="gate")                   # future usage-info path
    assert (m.prompt_tokens, m.completion_tokens, m.total_tokens) == (5, 3, 8)
    assert m.over_budget is False and m.any_estimate is True
    m.add_model_call("z" * 40, "")                     # +10 -> 18 > 10
    assert m.over_budget is True
    d = m.to_dict()
    assert d["estimate"] is True and d["model_calls"] == 3
    assert "prereg v1.1" in d["denominator"]


# ── gate wiring (real organs gate, zero model) ───────────────────────────────

def test_gate_closure_blocks_assertive_commit_passes_humble(tmp_path):
    inst = fixtures.make_dev_instance(999)
    env = EpisodeEnv(inst, tmp_path / "r")
    gate = agent_arm.make_env_epistemic_gate(env, inst.category, "organs")

    v_read = gate({"tool": "read_ledger", "arguments": {"offset": 0, "limit": 6}}, {})
    assert v_read["passed"] is True
    assert v_read["certificates"]["h0guard"]["status"] == "ok"     # organ actually ran
    assert v_read["certificates"]["apex"]["status"] == "skipped"   # nothing asserted

    v_ans = gate({"tool": "final_action",
                  "arguments": {"action": "answer", "target": "v1", "rationale": ""}}, {})
    assert v_ans["passed"] is False and v_ans["verdict"] == "MISSPECIFIED"
    assert "apex_contradictory" in v_ans["reasons"]                # machine reason kept
    assert any(r.startswith("descent_h0_conflict") for r in v_ans["reasons"])
    assert any(r.startswith("organ_finding") for r in v_ans["reasons"])  # legible translation

    v_q = gate({"tool": "final_action",
                "arguments": {"action": "quarantine", "target": "k", "rationale": ""}}, {})
    assert v_q["passed"] is True                                    # humble action allowed


def test_run_episode_scripted_end_to_end_no_model(tmp_path):
    """Full weak+aios wiring through the REAL run_loop + organs gate with a fake
    adapter: answer gets gate-blocked, the rewrite quarantines, drift fires on
    schedule, the trace and grader agree — zero model calls."""
    inst = fixtures.make_dev_instance(999)
    env = EpisodeEnv(inst, tmp_path / "r")
    replies = iter([
        '{"tool": "read_ledger", "args": {"offset": 0, "limit": 6}}',
        '<think>hm</think>{"tool": "final_action", "args": {"action": "answer", '
        '"target": "https://api.orion.internal/v1/submit", "rationale": "runbook"}}',
        '{"tool": "final_action", "args": {"action": "quarantine", '
        '"target": "orion_gateway.submit_endpoint", "rationale": "sources conflict"}}',
    ])
    fake_adapter = lambda prompt: next(replies)   # noqa: E731
    trace_path = tmp_path / "trace.jsonl"

    result = agent_arm.run_episode("weak+aios", inst, env, trace_path,
                                   adapter=fake_adapter, max_turns=12)
    outcome = result["outcome"]
    assert outcome["exit"] == "model_finished"
    assert outcome["gate_rejections"] == 1
    assert env.final_action["action"] == "quarantine"
    assert len(result["gate_blocks"]) == 1
    assert "apex_contradictory" in result["gate_blocks"][0]["reasons"]
    assert result["meter"].total_tokens > 0 and result["meter"].any_estimate

    # drift applied at its scheduled turn (turn_context fires before sampling)
    assert env.applied_drifts and env.applied_drifts[0]["drift_type"] == "schema_change"

    recs = load_trace(trace_path)
    kinds = [r["kind"] for r in recs]
    assert kinds[0] == "episode_meta"
    assert kinds.count("model_io") == 3
    gate_recs = [r for r in recs if r["kind"] == "run_loop:epistemic_gate"]
    assert any(r["passed"] is False and r["verdict"] == "MISSPECIFIED" for r in gate_recs)
    assert any(r["passed"] is True for r in gate_recs)
    assert any(r["kind"] == "env_event" and r["drift_type"] == "schema_change" for r in recs)

    # the hidden grader (separate process) confirms the episode
    spec_path = fixtures.write_grader_spec(inst, tmp_path / "specs")
    rc, verdict = _run_grader(spec_path, env.root)
    assert rc == 0 and verdict["success"] is True


def test_parse_tool_call_tolerance():
    assert agent_arm.parse_tool_call('{"tool": "list_files", "args": {}}') == ("list_files", {})
    assert agent_arm.parse_tool_call(
        'ok!\n```json\n{"tool": "read_file", "args": {"path": "orion.yaml"}}\n```'
    ) == ("read_file", {"path": "orion.yaml"})
    assert agent_arm.parse_tool_call("<think>x{y}</think>no call here") is None
    assert agent_arm.parse_tool_call('{"not_tool": 1}') is None


def test_stub_arms_fail_loudly(tmp_path):
    inst = fixtures.make_dev_instance(999)
    env = EpisodeEnv(inst, tmp_path / "r")
    for arm in ("strong-raw", "weak+checklist", "weak+llm-judge", "slm-delta"):
        with pytest.raises(NotImplementedError):
            agent_arm.run_episode(arm, inst, env, tmp_path / "t.jsonl")
    with pytest.raises(ValueError):
        agent_arm.run_episode("weak+telepathy", inst, env, tmp_path / "t.jsonl")


# ── freeze ────────────────────────────────────────────────────────────────────

def test_freeze_seal_and_drift_detection(tmp_path):
    root = tmp_path / "harness"
    (root / "grader_specs").mkdir(parents=True)
    (root / "fixtures.py").write_text("A = 1\n")
    (root / "grader_specs" / "t.json").write_text("{}\n")

    seal_path = tmp_path / "seal.json"
    m2_freeze.seal(seal_path, root=root)
    assert m2_freeze.verify(seal_path, root=root)["ok"] is True

    (root / "fixtures.py").write_text("A = 2\n")                    # post-freeze edit
    (root / "grader_specs" / "new.json").write_text("{}\n")         # post-freeze addition
    v = m2_freeze.verify(seal_path, root=root)
    assert v["ok"] is False
    kinds = {(d["file"], d["kind"]) for d in v["drift"]}
    assert ("fixtures.py", "modified_after_seal") in kinds
    assert ("grader_specs/new.json", "added_after_seal") in kinds
