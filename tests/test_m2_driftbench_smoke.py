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


def test_eval_generation_refuses_before_seal(tmp_path):
    # WP-B2: implemented, but POST-SEAL only — without the seal receipt it
    # refuses (prereg v1.1 §D: params drawn by public seed AFTER freeze).
    with pytest.raises(RuntimeError, match="POST-SEAL"):
        fixtures.generate_eval_instances(4242, seal_path=tmp_path / "missing_seal.json")
    assert len(fixtures.EVAL_TEMPLATE_SLOTS) == 8
    assert sum(1 for s in fixtures.EVAL_TEMPLATE_SLOTS if s["family"] == "mutating") == 6


# ── WP-B2: eval templates + generation ───────────────────────────────────────

def _gen(seed=4242):
    return fixtures.generate_eval_instances(seed, _allow_unsealed=True)


def test_eval_generation_all_8_templates_deterministic():
    gen1, gen2 = _gen(), _gen()
    a = json.dumps([i.to_dict() for i in gen1["base"]], sort_keys=True)
    b = json.dumps([i.to_dict() for i in gen2["base"]], sort_keys=True)
    assert a == b                                             # pure function of seeds
    c = json.dumps([i.to_dict() for i in _gen(999)["base"]], sort_keys=True)
    assert a != c                                             # public seed matters
    assert len(gen1["base"]) == 24 and len(gen1["corrupted"]) == 24
    assert gen1["seed_map"] == {0: 11, 1: 12, 2: 13}
    # coverage rule: all 8 taxonomy drift types, >=2 instances each
    assert set(gen1["drift_type_coverage"]) == set(fixtures.DRIFT_TYPES)
    assert all(v >= 2 for v in gen1["drift_type_coverage"].values())


def test_eval_instances_conform_to_frozen_schema_vocab():
    import labelers
    schema = labelers.load_frozen_schema()
    gen = _gen()
    for inst in gen["base"]:
        assert inst.template_id in schema.ALL_TEMPLATES
        assert inst.seed_index in schema.SEEDS
        assert inst.seed in fixtures.EVAL_SEEDS
        mutating = schema.is_mutating(inst.template_id)
        assert bool(inst.drift_schedule) == mutating
        if mutating:
            # WP-B lesson: primary drift precedes the earliest plausible commit
            assert inst.drift_schedule[0]["turn"] <= 2
            # the primary drift type matches the template name
            assert inst.drift_schedule[0]["drift_type"] == inst.template_id
        # grader material never in the agent-visible tree
        blob = json.dumps({"records": inst.records, "files": inst.files})
        assert "success_actions" not in blob and "min_commit_turn" not in blob
    # control families realized on the statics (prereg §1)
    fams = {i.template_id: i.family for i in gen["base"]}
    assert fams["url_static"] == "obstruction-absent-but-task-fails"
    assert fams["dependency_static"] == "obstruction-present-but-harmless"
    # corrupted twins: flag + false record at ts=0 about the target fact
    for twin in gen["corrupted"]:
        assert twin.corrupted_oracle and twin.variant == "corrupted"
        assert twin.corrupted_record["ts"] == 0
        assert twin.grader_spec["variant"] == "corrupted"


def test_corrupted_oracle_env_injection(tmp_path):
    gen = _gen()
    base = gen["base"][0]
    twin = gen["corrupted"][0]
    assert base.template_id == twin.template_id and base.seed == twin.seed
    env_b = EpisodeEnv(base, tmp_path / "b")
    env_c = EpisodeEnv(twin, tmp_path / "c")
    assert len(env_c._load_records()) == len(env_b._load_records()) + 1
    assert env_c._load_records()[0]["id"] == "mem-x00"        # injected at t=0
    assert any(e["kind"] == "corrupted_oracle_injected" for e in env_c.events)


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


def test_instrument_and_unknown_arms_fail_loudly(tmp_path):
    inst = fixtures.make_dev_instance(999)
    env = EpisodeEnv(inst, tmp_path / "r")
    # WP-B2: slm-delta is a score-only column, never a runnable arm.
    with pytest.raises(NotImplementedError, match="SCORE-ONLY"):
        agent_arm.run_episode("slm-delta", inst, env, tmp_path / "t.jsonl")
    with pytest.raises(ValueError):
        agent_arm.run_episode("weak+telepathy", inst, env, tmp_path / "t.jsonl")


# ── WP-B2: claims scoping (supervisor requirement) ───────────────────────────

def _claim(key, value, source="s", ts=0):
    return {"task_id": f"fact::{key}", "source_id": source, "kind": "io",
            "payload": {"input": [key], "output": value}, "ts": ts}


def test_scope_claims_to_target_pure():
    from env import scope_claims_to_target
    claims = [
        _claim("billing-api.retry_limit", "5"),
        _claim("billing-api.retry_limit", "5", source="s2"),
        _claim("legacy-tool.owner", "mira"),
        _claim("legacy-tool.owner", "tomas"),                  # harmless conflict
    ]
    # target names the clean fact -> only its claims, conflict stays OUT
    scoped = scope_claims_to_target(claims, "billing-api.retry_limit = 5")
    assert {c["task_id"] for c in scoped} == {"fact::billing-api.retry_limit"}
    assert len(scoped) == 2
    # target names one value of the disputed fact -> the WHOLE dispute in scope
    scoped2 = scope_claims_to_target(claims, "mira")
    assert {c["payload"]["output"] for c in scoped2} == {"mira", "tomas"}
    # empty / unmatched targets -> empty scope
    assert scope_claims_to_target(claims, "") == []
    assert scope_claims_to_target(claims, "zebra unrelated") == []


def test_known_claims_supersede_and_target_scoping(tmp_path):
    gen = _gen()
    inst = next(i for i in gen["base"] if i.template_id == "api_migration")
    env = EpisodeEnv(inst, tmp_path / "r")
    old = inst.grader_spec["stale_values"][0]
    new = inst.grader_spec["target_must_mention_any"][0]
    key = inst.grader_spec["target_fact_key"]
    env.apply_drift_for_turn(3)                                # both drifts applied
    active = {c["payload"]["output"] for c in env.known_claims()
              if c["task_id"] == f"fact::{key}"}
    assert active == {new}                                     # old retired by supersede
    raw = {c["payload"]["output"] for c in env.known_claims(include_superseded=True)
           if c["task_id"] == f"fact::{key}"}
    assert raw == {old, new}
    # a STALE-value target still pulls the fact's ACTIVE claim into scope
    scoped = env.known_claims(target=old)
    assert any(c["payload"]["output"] == new for c in scoped)
    # commit_claims: stale commit asserts the retired value -> conflict material
    cc = env.commit_claims(old)
    assert cc and cc[0]["payload"]["output"] == old
    cc2 = env.commit_claims(new)
    assert cc2 and cc2[0]["payload"]["output"] == new


def test_gate_scoping_blocks_stale_passes_fresh_and_harmless(tmp_path):
    """The three load-bearing gate behaviors: stale commit blocked, fresh commit
    passes, and the obstruction-present-but-harmless family is NOT blocked by
    an unrelated conflict (this is what the scoping fix exists for)."""
    gen = _gen()
    by = {i.template_id: i for i in gen["base"] if i.seed == 11}

    inst = by["api_migration"]
    env = EpisodeEnv(inst, tmp_path / "a")
    env.apply_drift_for_turn(3)
    gate = agent_arm.make_env_epistemic_gate(env, inst.category, "organs")
    old = inst.grader_spec["stale_values"][0]
    new = inst.grader_spec["target_must_mention_any"][0]
    v_stale = gate({"tool": "final_action",
                    "arguments": {"action": "answer", "target": old}}, {})
    assert v_stale["passed"] is False and "apex_contradictory" in v_stale["reasons"]
    v_fresh = gate({"tool": "final_action",
                    "arguments": {"action": "answer", "target": new}}, {})
    assert v_fresh["passed"] is True

    inst2 = by["dependency_static"]
    env2 = EpisodeEnv(inst2, tmp_path / "b")
    gate2 = agent_arm.make_env_epistemic_gate(env2, inst2.category, "organs")
    pin = inst2.grader_spec["target_must_mention_any"][0]
    v_ok = gate2({"tool": "final_action",
                  "arguments": {"action": "answer", "target": pin}}, {})
    assert v_ok["passed"] is True                              # scoped: conflict is elsewhere
    # counterfactual: UNSCOPED evidence blocks the same commit (proves scoping matters)
    import aios_epistemic_gate
    raw_gate = aios_epistemic_gate.make_gate("organs")
    v_all = raw_gate({"tool": "final_action", "category": inst2.category,
                      "arguments": {"action": "answer", "target": pin}},
                     {"known_claims": env2.known_claims(),
                      "profiles_population": env2.profiles_population()})
    assert v_all.to_dict()["passed"] is False


# ── WP-B2: labelers on synthetic traces ──────────────────────────────────────

def test_labelers_on_synthetic_traces():
    import labelers
    active = [_claim("svc.key", "new-value")]
    raw = active + [_claim("svc.key", "old-value")]
    trace = [
        {"seq": 0, "kind": "episode_meta"},
        {"seq": 1, "kind": "run_loop:trajectory", "tool": "read_ledger", "status": "ok"},
        {"seq": 2, "kind": "env_event", "event_kind": "drift_applied"},
        {"seq": 3, "kind": "run_loop:trajectory", "tool": "sudo_shell", "status": "denied"},
        {"seq": 4, "kind": "run_loop:trajectory", "tool": "ask_oracle", "status": "ok"},
        {"seq": 5, "kind": "run_loop:trajectory", "tool": "read_ledger", "status": "ok"},
        {"seq": 6, "kind": "run_loop:trajectory", "tool": "final_action", "status": "ok"},
    ]
    env_events = [
        {"kind": "drift_applied", "turn": 2, "drift_type": "api_migration",
         "invalidates": [{"key": "svc.key", "old_value": "old-value"}]},
        {"kind": "contract_violation", "reason": "path_escape", "turn": 1},
    ]
    grader = {"success": False, "checkpoints": [
        {"id": "final_action_recorded", "passed": True},
        {"id": "action_in_success_set", "passed": False},
    ]}
    # stale answer: commits the invalidated value
    fa = {"action": "answer", "target": "old-value", "rationale": "runbook", "turn": 4}
    labels = labelers.label_counts(trace, env_events, fa, grader, active, raw_claims=raw)
    assert labels["stale_actions"] == 1
    assert labels["unsupported_claims"] == 0        # grounded in a (retired) record => (iii) not (iv)
    assert labels["wrong_actions"] == 3             # denied + contract violation + wrong final
    assert labels["asks"] == 1 and labels["abstains"] == 0
    assert labels["verification_before_submit"] is True   # read at seq 5 after drift at seq 2

    # unsupported answer: matches nothing ever asserted
    fa2 = {"action": "answer", "target": "totally-invented", "rationale": "", "turn": 4}
    labels2 = labelers.label_counts(trace, env_events, fa2, grader, active, raw_claims=raw)
    assert labels2["unsupported_claims"] == 1 and labels2["stale_actions"] == 0

    # abstain final + no read after drift
    trace3 = [t for t in trace if t.get("seq") != 5]
    fa3 = {"action": "abstain", "target": "evidence unstable", "rationale": "", "turn": 4}
    grader3 = {"success": True, "checkpoints": [{"id": "action_in_success_set", "passed": True}]}
    labels3 = labelers.label_counts(trace3, env_events, fa3, grader3, active, raw_claims=raw)
    assert labels3["abstains"] == 1 and labels3["asks"] == 1
    assert labels3["verification_before_submit"] is False
    assert labels3["wrong_actions"] == 2            # denied + contract violation only


def test_build_result_row_validates_against_frozen_schema():
    import labelers
    gen = _gen()
    inst = gen["base"][0]
    labels = {"wrong_actions": 1, "stale_actions": 0, "unsupported_claims": 0,
              "asks": 1, "abstains": 0, "verification_before_submit": True}
    grader = {"success": True, "checkpoints": [
        {"id": "a", "passed": True}, {"id": "b", "passed": True}]}
    row, errors = labelers.build_result_row(
        instance=inst, arm="weak+aios", grader=grader, labels=labels,
        actions_used=7, wall_seconds=12.5, tokens=4000,
        causal_trace_path="/tmp/causal.jsonl")
    assert errors == []
    assert row.arm == "weak+AIOS" and row.seed == inst.seed_index
    assert row.template == inst.template_id
    # caps clamp to the frozen bounds (receipt keeps raw values)
    row2, errors2 = labelers.build_result_row(
        instance=inst, arm="strong-raw", grader=grader, labels=labels,
        actions_used=10_000, wall_seconds=99_999.0, tokens=1,
        causal_trace_path="x")
    assert errors2 == [] and row2.actions_used == 200 and row2.wall_seconds == 2700
    # instruments have no frozen-row mapping
    with pytest.raises(ValueError, match="instrument"):
        labelers.build_result_row(instance=inst, arm="weak+llm-judge", grader=grader,
                                  labels=labels, actions_used=1, wall_seconds=1,
                                  tokens=1, causal_trace_path="x")
    # infra failure / restart can never score success (prereg §3)
    row3, errors3 = labelers.build_result_row(
        instance=inst, arm="weak-raw", grader=grader, labels=labels,
        actions_used=7, wall_seconds=1.0, tokens=1,
        causal_trace_path="x", restarted=True)
    assert errors3 == [] and row3.binary_success is False and row3.restarted is True


# ── WP-B2: probes, memory policy, slm-delta, metered seams ───────────────────

def test_misspecified_probe_set_arithmetic_and_gate():
    import probes
    ps = probes.build_probe_set()
    assert len(ps) == 24
    assert json.dumps([p["probe_id"] for p in ps]) == json.dumps(
        [p["probe_id"] for p in probes.build_probe_set()])       # pre-registered = byte-stable
    report = probes.run_probe_gate()
    assert report["n_probes"] == 24
    assert report["gate_met"] is True and report["fraction"] > 0.95
    assert report["misses"] == []
    # arithmetic: the gate requires STRICTLY more than 95%
    assert (23 / 24) > report["gate_requirement"]                # one miss still passes at n=24
    assert (22 / 24) < report["gate_requirement"]                # two misses fail


def test_memory_policy_h3(tmp_path):
    import memory as m2_memory
    store = m2_memory.MemoryStore("weak+memory", tmp_path / "mem.json")
    src_claims = [_claim("svc.timeout", "30"), _claim("svc.owner", "mira")]
    store.store("config_change", "always re-read; timeout was 30",
                m2_memory.capture_context_facts(src_claims))

    # cross-template injection forbidden
    other = m2_memory.inject_note(store, "auth_change", src_claims, staleness_gated=False)
    assert other["injected"] is False

    # weak+memory: ALWAYS injects, even against contradicting claims
    cur = [_claim("svc.timeout", "60")]
    always = m2_memory.inject_note(store, "config_change", cur, staleness_gated=False)
    assert always["injected"] is True and "LESSON" in always["prefix"]

    # weak+AIOS: staleness-gated -> suppressed + marked on the same store
    gated = m2_memory.inject_note(store, "config_change", cur, staleness_gated=True)
    assert gated["injected"] is False and gated["stale"] is True
    assert gated["detail"]["contradicted"][0][0] == "svc.timeout"

    # non-contradicted note passes the gate (absent keys are neither confirmed nor stale)
    ok = m2_memory.inject_note(store, "config_change",
                               [_claim("svc.timeout", "30")], staleness_gated=True)
    assert ok["injected"] is True

    # persistence across store instances (resumable runs)
    store2 = m2_memory.MemoryStore("weak+memory", tmp_path / "mem.json")
    assert store2.note_for("config_change")["lesson"].startswith("always re-read")

    # distillation is metered and capped
    meter = TokenMeter()
    lesson = m2_memory.distill_lesson(lambda p: "x" * 900, "config_change", "task",
                                      {"action": "answer"}, meter)
    assert len(lesson) == m2_memory.LESSON_CHAR_CAP
    assert meter.entries and meter.entries[-1]["source"] == "memory"
    assert m2_memory.distill_lesson(_raise_runtime, "t", "task", None, meter) == ""


def _raise_runtime(prompt):
    raise RuntimeError("dead adapter")


def test_slm_delta_untyped_detector():
    import slm_delta
    gen = _gen()
    inst = next(i for i in gen["base"] if i.template_id == "api_migration")
    base_score = slm_delta.slm_delta_score(inst.records)
    assert base_score["n_records"] == len(inst.records)
    # after the supersede REVISION lands, the untyped detector false-fires on
    # the textually-similar-but-different pair (the non-factorization witness
    # direction: typed layer sees a clean supersession, untyped fires)
    import tempfile
    from pathlib import Path as _P
    env = EpisodeEnv(inst, _P(tempfile.mkdtemp()) / "r")
    env.apply_drift_for_turn(3)
    post = slm_delta.slm_delta_score(env._load_records())
    assert post["fired"] is True and post["n_edges"] > 0
    # determinism
    assert json.dumps(post, sort_keys=True) == json.dumps(
        slm_delta.slm_delta_score(env._load_records()), sort_keys=True)


def test_metered_chat_adapter_and_judge_gate(monkeypatch):
    meter = TokenMeter()
    # fake OpenAI-compat endpoint with exact usage
    def fake_post(base_url, body, headers, timeout):
        assert body["temperature"] == 0.0                      # pinned
        assert "Authorization" not in headers                  # no key for local
        return {"choices": [{"message": {"content": "CONSISTENT"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 3}}
    monkeypatch.setattr(agent_arm, "_post_chat", fake_post)
    adapter = agent_arm.make_metered_chat_adapter(
        base_url="http://x/v1", model="m", meter=meter, source="gate")
    assert adapter("hello") == "CONSISTENT"
    assert meter.entries[-1] == {"source": "gate", "estimate": False,
                                 "prompt_tokens": 11, "completion_tokens": 3}
    assert meter.any_estimate is False                         # EXACT usage recorded

    # judge gate: consistent -> pass; INCONSISTENT -> block; dead -> fail-closed
    gate = agent_arm.make_metered_llm_judge_gate(adapter)
    v = gate({"tool": "read_ledger"}, {"goal": "g"})
    assert v["passed"] is True and v["checked"] == 1
    def fake_post_bad(base_url, body, headers, timeout):
        return {"choices": [{"message": {"content": "INCONSISTENT"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    monkeypatch.setattr(agent_arm, "_post_chat", fake_post_bad)
    v2 = gate({"tool": "read_ledger"}, {})
    assert v2["passed"] is False and v2["reasons"] == ["llm_judge_flagged_inconsistent"]
    gate_dead = agent_arm.make_metered_llm_judge_gate(_raise_runtime)
    v3 = gate_dead({"tool": "read_ledger"}, {})
    assert v3["passed"] is False and v3["infra_failures"] == 1  # fail-closed, loud

    # the judge's tokens entered the frozen denominator
    assert any(e["source"] == "gate" for e in meter.entries)


def test_checklist_arm_prompt_is_verbatim_and_wired(tmp_path):
    import prompts
    # the adopted A2 checklist, verbatim anchors (audit §4)
    for anchor in ("CONTROL CHECKLIST — Execute in order before acting:",
                   "1. **FULL COVERAGE**", "2. **PROVENANCE INTEGRITY**",
                   "6. **DISCONFIRMING EVIDENCE**", "8. **EXIT DISCIPLINE**",
                   "Wrong confident answer is the costliest outcome."):
        assert anchor in prompts.CHECKLIST_A2
    assert prompts.ARM_PROMPT_PREFIX["weak+checklist"].startswith("CONTROL CHECKLIST")
    assert prompts.ARM_PROMPT_PREFIX["weak-raw"] == ""

    # the checklist arm sees the checklist in its prompt; same tools (parity)
    inst = fixtures.make_dev_instance(999)
    env = EpisodeEnv(inst, tmp_path / "r")
    seen = {}
    def fake_adapter(prompt):
        seen.setdefault("prompt", prompt)
        return json.dumps({"tool": "final_action",
                           "args": {"action": "quarantine",
                                    "target": "orion_gateway.submit_endpoint",
                                    "rationale": "conflict"}})
    result = agent_arm.run_episode("weak+checklist", inst, env, tmp_path / "t.jsonl",
                                   adapter=fake_adapter, max_turns=4)
    assert result["outcome"]["exit"] == "model_finished"
    assert seen["prompt"].startswith("CONTROL CHECKLIST")
    assert '"tool": "read_ledger"' in seen["prompt"]           # same inspectors offered
    assert env.final_action["action"] == "quarantine"


def test_eval_runner_end_to_end_scripted_row_and_causal(tmp_path):
    """run_one_eval_arm on a scripted weak+aios episode: gate-blocked stale
    commit -> corrected fresh commit; row validates against the FROZEN schema;
    the causal trace satisfies the FROZEN analyze.py condition-4 check."""
    import importlib.util
    import run_stage1
    gen = _gen()
    inst = next(i for i in gen["base"] if i.template_id == "api_migration" and i.seed == 11)
    old = inst.grader_spec["stale_values"][0]
    new = inst.grader_spec["target_must_mention_any"][0]
    replies = iter([
        '{"tool": "read_ledger", "args": {"offset": 0, "limit": 6}}',
        json.dumps({"tool": "final_action",
                    "args": {"action": "answer", "target": old, "rationale": "runbook"}}),
        '{"tool": "read_ledger", "args": {"offset": 0, "limit": 8}}',
        json.dumps({"tool": "final_action",
                    "args": {"action": "answer", "target": new, "rationale": "migration"}}),
    ])
    receipt = run_stage1.run_one_eval_arm(
        "weak+aios", inst, receipts_dir=tmp_path, env_base=None, force=False,
        memory_store=None, adapter=lambda p: next(replies))
    assert receipt["arm_status"] == "ok"
    assert receipt["grader"]["success"] is True
    assert receipt["row_validation_errors"] == []
    assert receipt["row"]["arm"] == "weak+AIOS" and receipt["row"]["seed"] == 0
    assert receipt["labels"]["verification_before_submit"] is True
    assert receipt["answerability_probe"]["ground_truth_answerable"] is True
    assert receipt["slm_delta"]["schema"] == "m2.slm_delta.v1"

    # the FROZEN analyze.py loads the causal trace and verifies condition 4
    # (it does `from schema import ...`, so its own dir joins sys.path exactly
    # as when it runs as a script from experiments/driftbench/)
    ana_path = _ROOT / "experiments" / "driftbench" / "analyze.py"
    sys.path.insert(0, str(ana_path.parent))
    try:
        spec = importlib.util.spec_from_file_location("m2_frozen_analyze_test", ana_path)
        ana = importlib.util.module_from_spec(spec)
        sys.modules["m2_frozen_analyze_test"] = ana
        spec.loader.exec_module(ana)
    finally:
        sys.path.remove(str(ana_path.parent))
    events = ana.load_trace(receipt["causal_trace"])
    assert {e.type for e in events} <= {"gate_reject", "drift_detected",
                                        "rollback", "checkpoint_result"}
    check = ana.causal_recovery_check(events)
    assert check.status == "verified"                          # trigger -> flip within lag

    # resumability: second call skips (no re-run)
    again = run_stage1.run_one_eval_arm(
        "weak+aios", inst, receipts_dir=tmp_path, env_base=None, force=False,
        memory_store=None, adapter=None)                       # adapter unused on skip
    assert again["finished"] == receipt["finished"]


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


def test_freeze_cross_references_frozen_dual_harness(tmp_path):
    """WP-B2: the seal cross-references the HASH-FROZEN schema.py/analyze.py
    (read-only) and their hashes still match the reconciliation doc's frozen
    prefixes; cross-ref drift voids like harness drift."""
    xref = m2_freeze.cross_ref_hashes()
    assert set(xref) == set(m2_freeze.CROSS_REF_FILES)
    for rel, entry in xref.items():
        assert entry["matches_reconciliation"] is True, f"{rel}: {entry}"

    root = tmp_path / "h"
    (root / "grader_specs").mkdir(parents=True)
    (root / "fixtures.py").write_text("A = 1\n")
    seal_path = tmp_path / "seal.json"
    receipt = m2_freeze.seal(seal_path, root=root)
    assert receipt["schema"] == "m2.freeze_seal.v2"
    assert receipt["row_seed_map"] == {"0": 11, "1": 12, "2": 13}
    assert m2_freeze.verify(seal_path, root=root)["ok"] is True
    # simulate frozen-file drift via a fake repo root
    fake_repo = tmp_path / "repo"
    (fake_repo / "experiments" / "driftbench").mkdir(parents=True)
    (fake_repo / "experiments" / "driftbench" / "schema.py").write_text("tampered\n")
    (fake_repo / "experiments" / "driftbench" / "analyze.py").write_text("tampered\n")
    v = m2_freeze.verify(seal_path, root=root, repo_root=fake_repo)
    assert v["ok"] is False
    assert {d["kind"] for d in v["drift"]} == {"frozen_cross_ref_drifted"}
