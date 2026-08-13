"""Adversarial tests for the seam conformance checker.

A checker that cannot fail does not certify anything, so before M0 could be
called LIT on its say-so this file mutates a valid receipt one clause at a time
and requires a rejection each time. Each mutation is named after the fake that
clause exists to stop — if a clause is ever loosened, the test says what became
possible rather than just going red.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_conform as K  # noqa: E402

D = "sha256:" + "a" * 64
D2 = "sha256:" + "b" * 64


def valid(outcome="committed"):
    return {
        "schema": "aios.minimal_operation.v1",
        "sense": {"predicate": "p", "evaluated_by": "policy",
                  "input_digest": D, "model_consulted": False},
        "act": {"operator": "distill@m", "invoked_by": "host",
                "model_offered_choice": False},
        "verify": {"oracle_cmd_digest": D, "verifier_identity": "oracle",
                   "verdict": "pass" if outcome == "committed" else "fail"},
        "settle": {"outcome": outcome, "root_before": D, "root_after": D2},
    }


def test_a_valid_receipt_passes():
    assert K.check_receipt(valid()) == []
    assert K.check_receipt(valid("reverted")) == []


@pytest.mark.parametrize("member,key,value,fake_it_enables", [
    ("sense", "model_consulted", True,
     "an offered mechanism the model picked could claim the cycle"),
    ("act", "invoked_by", "model",
     "the model selecting the action, which measured 0-of-32"),
    ("act", "model_offered_choice", True, "an offer masquerading as an act"),
    ("verify", "verdict", "maybe", "an unfalsifiable verdict"),
    ("settle", "outcome", "partial", "a settlement with no committed meaning"),
    ("settle", "root_after", D, "claiming to settle while writing nothing"),
    ("sense", "input_digest", "not-a-digest", "an unverifiable input reference"),
])
def test_each_clause_rejects_its_own_fake(member, key, value, fake_it_enables):
    r = valid()
    r[member][key] = value
    assert K.check_receipt(r), f"checker accepted: {fake_it_enables}"


def test_executor_cannot_be_its_own_verifier():
    r = valid()
    r["verify"]["verifier_identity"] = r["act"]["operator"]
    assert any("grading itself" in m for m in K.check_receipt(r))


def test_verdict_must_bind_the_outcome():
    """fail-then-commit and pass-then-revert both make the verdict decoration."""
    r = valid()
    r["verify"]["verdict"] = "fail"          # but outcome stays 'committed'
    assert any("decoration" in m for m in K.check_receipt(r))
    r2 = valid("reverted")
    r2["verify"]["verdict"] = "pass"
    assert any("decoration" in m for m in K.check_receipt(r2))


def test_missing_member_is_reported_before_clause_checks():
    r = valid()
    del r["verify"]
    assert K.check_receipt(r) == ["missing member: verify"]


# --- the ledger rule, which is the part a foreign implementation must copy ---

def test_reordering_history_changes_the_root(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    a.write_text('{"x":1}\n{"y":2}\n')
    b.write_text('{"y":2}\n{"x":1}\n')
    assert K.ledger_root(a) != K.ledger_root(b), \
        "position salting is what makes append-only enforceable"


def test_empty_ledger_has_the_defined_root(tmp_path):
    assert K.ledger_root(tmp_path / "nope.jsonl") == K._h("")


def test_odd_layer_pairs_last_element_with_itself():
    """Pinned because it is the one place two implementations silently diverge."""
    leaves = [K._h(str(i)) for i in range(3)]
    s = sorted(leaves)
    expect = K._h(K._h(s[0] + s[1]) + K._h(s[2] + s[2]))
    assert K.root(leaves) == expect


def test_m0_requires_an_actually_executed_revert(tmp_path):
    """All-committed is not lit: the rejection path would be code never run."""
    rec = tmp_path / "r.jsonl"
    rec.write_text("\n".join(json.dumps(valid()) for _ in range(3)) + "\n")
    assert K.main([str(rec), "--m0", "--json"]) == 0    # conforming...

    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        K.main([str(rec), "--m0", "--json"])
    assert json.loads(buf.getvalue())["m0"]["lit"] is False

    rec.write_text("\n".join(
        [json.dumps(valid()), json.dumps(valid("reverted"))]) + "\n")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        K.main([str(rec), "--m0", "--json"])
    assert json.loads(buf.getvalue())["m0"]["lit"] is True


def test_checker_imports_nothing_from_aios():
    """If the seam's checker needs our code, the seam is not a seam."""
    src = (ROOT / "scripts" / "aios_conform.py").read_text(encoding="utf-8")
    body = "\n".join(l for l in src.splitlines()
                     if l.startswith(("import ", "from ")))
    assert "aios_" not in body, body


# --- spec §2b: the verifier must live below what it judges ------------------

def test_executing_code_in_the_verifier_s_process_is_refused():
    """The clause that will be violated by the obvious next step.

    A ledger row already carries a `falsifier`; the whole direction of the
    design is to make those runnable. On that day the executor becomes
    untrusted code inside our own process, and without this clause the receipt
    would look exactly as conforming as a text-only one does today.
    """
    r = valid()
    r["act"]["executes_code"] = True
    r["verify"]["isolation"] = "same_process"
    assert any("trust domain it judges" in m for m in K.check_receipt(r))


def test_executing_code_without_declaring_isolation_is_refused():
    r = valid()
    r["act"]["executes_code"] = True
    assert any("must show the boundary" in m for m in K.check_receipt(r))


@pytest.mark.parametrize("iso", ["separate_process", "remote", "sandboxed"])
def test_a_real_boundary_is_accepted(iso):
    r = valid()
    r["act"]["executes_code"] = True
    r["verify"]["isolation"] = iso
    assert K.check_receipt(r) == []


def test_text_only_operator_may_honestly_share_a_process():
    """A string cannot reach into the verifier, so this is not a violation —
    the clause must not fire on the honest case or producers will stop
    declaring it."""
    r = valid()
    r["act"]["executes_code"] = False
    r["verify"]["isolation"] = "same_process"
    assert K.check_receipt(r) == []


def test_an_invented_isolation_value_is_refused():
    r = valid()
    r["verify"]["isolation"] = "very_isolated_trust_me"
    assert any("verify.isolation not in" in m for m in K.check_receipt(r))


# --- the seam's own claim: a foreign implementation can conform -------------

def test_posix_shell_producer_conforms_and_agrees_on_the_root(tmp_path):
    """The spec says the seam is real only if something outside our stack can
    pass. This runs `spec/examples/producer.sh` — /bin/sh and sha256sum, no
    Python — and requires both that its receipts conform AND that the Merkle
    root it computed in shell equals the one recomputed here. If these ever
    diverge, the written rule is underspecified and the seam is only a codebase.
    """
    import shutil
    import subprocess
    if not shutil.which("sha256sum"):
        pytest.skip("sha256sum not available")
    script = ROOT / "spec" / "examples" / "producer.sh"
    out = tmp_path / "participant"
    proc = subprocess.run(["sh", str(script), str(out)], capture_output=True,
                          text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr

    receipts = [json.loads(l) for l in (out / "receipts.jsonl").open()]
    assert len(receipts) == 2
    for r in receipts:
        assert K.check_receipt(r) == [], r

    shell_root = [l for l in proc.stdout.splitlines()
                  if l.startswith("final root:")][0].split(": ", 1)[1]
    assert K.ledger_root(out / "ledger.jsonl") == shell_root
    assert receipts[-1]["settle"]["root_after"] == shell_root

    outcomes = {r["settle"]["outcome"] for r in receipts}
    assert outcomes == {"committed", "reverted"}, \
        "a producer that never exercises rejection has not shown a verified cycle"


# --- spec §2c: an edge that fired but was ignored is a new zero -------------

def with_edge(**over):
    r = valid()
    d = "sha256:" + "c" * 64
    r["edge"] = {"edge_id": "memory-after-verify-fail", "invoked_by": "host",
                 "output_digest": d}
    r["act"]["context_components"] = [d, "sha256:" + "e" * 64]
    for k, v in over.items():
        r["edge"][k] = v
    return r, d


def test_a_bound_edge_passes():
    r, _ = with_edge()
    assert K.check_receipt(r) == []


def test_edge_output_dropped_from_the_act_is_refused():
    """The failure this clause exists for: called 32/32, ignored 32/32."""
    r, d = with_edge()
    r["act"]["context_components"] = [x for x in r["act"]["context_components"]
                                      if x != d]
    assert any("ignored" in m for m in K.check_receipt(r))


def test_edge_without_any_declared_act_context_is_refused():
    r, _ = with_edge()
    del r["act"]["context_components"]
    assert any("nothing shows the edge output reached the act" in m
               for m in K.check_receipt(r))


def test_a_model_chosen_edge_is_an_offer_not_an_edge():
    r, _ = with_edge(invoked_by="model")
    assert any("is an offer" in m for m in K.check_receipt(r))


def test_edge_output_digest_must_be_a_digest():
    r, _ = with_edge(output_digest="whatever-i-retrieved")
    assert any("edge.output_digest is not sha256" in m
               for m in K.check_receipt(r))


@pytest.mark.parametrize("missing", ["edge_id", "invoked_by", "output_digest"])
def test_incomplete_edge_is_refused(missing):
    r, _ = with_edge()
    del r["edge"][missing]
    assert any(f"edge.{missing} missing" in m for m in K.check_receipt(r))


def test_receipts_without_an_edge_are_unaffected():
    """The clause must stay optional, or every existing producer breaks and the
    seam stops being adoptable."""
    assert K.check_receipt(valid()) == []
    assert K.check_receipt(valid("reverted")) == []


def test_the_seam_cannot_read_which_experimental_arm_a_receipt_is():
    """Blinding is the experiment's business. A checker that could tell a sham
    edge from a real one would leak the arm into a file both arms produce.
    """
    real, _ = with_edge()
    sham, _ = with_edge()          # identical shape, information-free payload
    assert K.check_receipt(real) == K.check_receipt(sham) == []
    src = (ROOT / "scripts" / "aios_conform.py").read_text(encoding="utf-8")
    for leak in ("sham", "arm", "treatment", "control"):
        assert leak not in src.lower(), f"checker mentions {leak!r}"


# --- spec §2d: exact-byte delivery (D1) and the uptake canary (U0) ---------

def with_manifest(**over):
    r, d = with_edge()
    r["act_input"] = {"serialized_request_digest": D, "length": 100,
                      "assembled_by": "host-adapter",
                      "components": [{"kind": "system", "digest": D2,
                                      "start": 0, "end": 40},
                                     {"kind": "edge_output", "digest": d,
                                      "start": 40, "end": 100}]}
    r["act_input"].update(over)
    return r, d


def test_a_tiling_manifest_passes():
    r, _ = with_manifest()
    assert K.check_receipt(r) == []


def test_a_manifest_with_a_gap_is_refused():
    """An untiled manifest lets a producer name the edge and assemble something
    else in the space the manifest never accounts for."""
    r, d = with_manifest()
    r["act_input"]["components"][1]["start"] = 50      # 40..50 unaccounted
    assert any("do not tile" in m for m in K.check_receipt(r))


def test_a_manifest_that_stops_short_of_the_input_is_refused():
    r, _ = with_manifest(length=200)
    assert any("account for every byte" in m for m in K.check_receipt(r))


def test_the_edge_must_own_a_byte_range_not_just_a_mention():
    """D0 vs D1: being listed is not being delivered."""
    r, d = with_manifest()
    r["act_input"]["components"][1]["digest"] = D2      # edge no longer spans
    assert any("declared, not delivered" in m for m in K.check_receipt(r))


def test_the_operator_may_not_describe_its_own_input():
    r, _ = with_manifest(assembled_by="distill@m")      # == act.operator
    assert any("not evidence" in m for m in K.check_receipt(r))


def test_the_uptake_canary_must_recompute():
    r, _ = with_manifest()
    r["uptake"] = {"nonce": "n-123", "act_id": "act-7",
                   "selected_action": "edit:src/lease.py",
                   "commitment": K._h("n-123act-7edit:src/lease.py")}
    assert K.check_receipt(r) == []
    r["uptake"]["commitment"] = K._h("something-else")
    assert any("did not carry a value" in m for m in K.check_receipt(r))


def test_receipts_without_a_manifest_still_pass():
    """§2d must stay optional or every existing participant breaks — including
    the base layer that shipped conforming receipts an hour ago."""
    assert K.check_receipt(valid()) == []
