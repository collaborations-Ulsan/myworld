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
