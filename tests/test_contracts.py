"""Adversarial tests for the contract layer.

Every rule here exists because dropping it admits a specific forgery, so each
test is named after the forgery rather than after the rule. If a clause is ever
loosened, the failing test says what became possible.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import aios_contracts as C  # noqa: E402

NOW = 1_000_000.0
D = "sha256:" + "a" * 64


def grant(**over):
    g = {"schema": "aios.contracts.v1.capability_grant",
         "subject": "agent:executor-7", "actions": ["L2", "L3"],
         "expires_at": NOW + 3600, "issuer": "policy-kernel"}
    g.update(over)
    return g


def envelope(**over):
    e = {"schema": "aios.contracts.v1.envelope", "message_id": "msg-1",
         "arc_id": "arc-1", "from": {"agent_id": "a", "workspace_id": "ws"},
         "to": {"agent_id": "b", "workspace_id": "ws"},
         "kind": "HYPOTHESIS", "trust_class": "internal_agent", "root": True}
    e.update(over)
    return e


# --- the five acceptance rules ---------------------------------------------

def test_a_producer_inventing_its_own_contract_is_refused():
    assert any("unknown schema version" in m
               for m in C.validate({"schema": "my.own.format.v9"}, now=NOW))


def test_an_event_with_no_causal_parent_is_refused():
    e = envelope()
    del e["root"]
    assert any("causal parent" in m for m in C.validate(e, now=NOW))
    e["causation_id"] = "msg-0"
    assert C.validate(e, now=NOW) == []


def test_a_message_reaching_into_another_workspace_is_refused():
    e = envelope(to={"agent_id": "b", "workspace_id": "someone-else"})
    assert any("cross-tenant" in m for m in C.validate(e, now=NOW))


def test_authority_does_not_outlive_its_issuance():
    assert any("expired" in m
               for m in C.validate(grant(expires_at=NOW - 1), now=NOW))
    assert C.validate(grant(), now=NOW) == []


def test_one_intent_must_not_produce_two_effects():
    seen: set[str] = set()
    e = envelope(delivery={"idempotency_key": "arc-1:review:3"})
    assert C.validate(e, now=NOW, seen_idempotency=seen) == []
    assert any("duplicate idempotency_key" in m
               for m in C.validate(e, now=NOW, seen_idempotency=seen))


# --- the identity separation ------------------------------------------------

def test_a_session_that_is_its_own_identity_cannot_be_resumed():
    """The failure cross-session messaging has today: sender = socket path."""
    s = {"schema": "aios.contracts.v1.session", "session_id": "sess-7",
         "agent_id": "uds:/run/user/1000/cc-socks/2456189.sock",
         "provider": "anthropic"}
    assert any("durable agent" in m for m in C.validate(s, now=NOW))
    s["agent_id"] = "research-scout"
    assert C.validate(s, now=NOW) == []


def test_an_endpoint_owns_nothing():
    e = {"schema": "aios.contracts.v1.endpoint", "endpoint_id": "ep-1",
         "session_id": "!!not-a-session!!", "address": "uds:/x.sock"}
    assert any("owns nothing" in m for m in C.validate(e, now=NOW))


# --- claims -----------------------------------------------------------------

def test_a_claim_without_a_falsifier_is_a_quote():
    c = {"schema": "aios.contracts.v1.claim", "claim_id": "c1",
         "statement": "the retry fixes it", "epistemic_type": "Proposal",
         "falsifier": "   "}
    assert any("not a claim" in m for m in C.validate(c, now=NOW))


def test_only_a_receipt_raises_a_claim_above_proposal():
    """Advice entering the ledger must not promote itself by asserting."""
    c = {"schema": "aios.contracts.v1.claim", "claim_id": "c1",
         "statement": "externalising the intermediate revives two-hop",
         "epistemic_type": "Established", "falsifier": "run arm C-prime"}
    assert any("only an execution receipt" in m for m in C.validate(c, now=NOW))
    c["receipt"] = "sha256:" + "b" * 64
    assert C.validate(c, now=NOW) == []


def test_a_verifier_may_not_be_the_executor():
    v = {"schema": "aios.contracts.v1.verdict", "verdict_id": "v1",
         "target": "task-1", "outcome": "pass", "oracle_digest": D,
         "verifier_identity": "distill@qwen", "executor_identity": "distill@qwen"}
    assert any("grading itself" in m for m in C.validate(v, now=NOW))


# --- the authority lattice --------------------------------------------------

@pytest.mark.parametrize("action", ["L2", "L3", "L6", "L7", "L8"])
def test_a_browser_chatbot_never_acts_however_confident(action):
    """It advises. Consumer UI automation is not an execution protocol."""
    out = C.authorize("browser_chatbot", action, grant=grant(actions=[action]))
    assert out["allowed"] is False
    assert "ceiling" in out or "grant" in out["reason"]


def test_a_grant_cannot_raise_a_class_ceiling():
    """The gate that stops persuasion from becoming permission."""
    g = grant(actions=["L7"], subject="agent:chatbot")
    out = C.authorize("external_federated_agent", "L7", grant=g)
    assert out["allowed"] is False and "No grant raises a class ceiling" in out["reason"]


def test_reading_needs_no_grant_but_sandbox_modification_does():
    assert C.authorize("internal_agent", "L0", now=NOW)["allowed"] is True
    assert C.authorize("internal_agent", "L2", now=NOW)["allowed"] is False
    assert C.authorize("internal_agent", "L2", grant=grant(),
                       now=NOW)["allowed"] is True


def test_authorize_and_validate_must_be_given_the_same_clock():
    """A footgun worth a test rather than a comment.

    Both take `now` and both default to the wall clock independently, so a
    caller that fixes the clock for one and not the other silently compares a
    fixture timestamp against real time and every grant looks expired. The same
    shape as claim/note defaulting locks_dir separately, which cost a whole
    debugging pass earlier today.
    """
    g = grant()                                   # expires at NOW + 3600
    assert C.validate(g, now=NOW) == []
    assert C.authorize("internal_agent", "L2", grant=g, now=NOW)["allowed"] is True
    # ...and with the real clock the same grant is long expired, which is
    # correct behaviour and exactly why the clock must be passed deliberately.
    late = C.authorize("internal_agent", "L2", grant=g)
    assert late["allowed"] is False and "expired" in late["reason"]


def test_an_expired_grant_authorises_nothing():
    out = C.authorize("internal_agent", "L2", grant=grant(expires_at=NOW - 1),
                      now=NOW)
    assert out["allowed"] is False and "expired" in out["reason"]


def test_a_grant_that_forbids_the_rung_wins_over_one_that_allows_it():
    g = grant(actions=["L2", "L3"], forbidden=["L3"])
    assert C.authorize("internal_agent", "L3", grant=g)["allowed"] is False


# --- self-ratification ------------------------------------------------------

def test_agent_text_is_never_consent():
    """The clause most likely to be quietly relaxed, so it is executable."""
    for tc in ("internal_agent", "external_federated_agent", "browser_chatbot",
               "kernel_internal"):
        e = envelope(trust_class=tc, kind="DECISION_REQUEST",
                     signature="looks-official")
        assert C.is_approval(e)["is_approval"] is False, tc


def test_only_a_signed_human_decision_approves():
    e = envelope(trust_class="human_authenticated", kind="DECISION_REQUEST",
                 signature="sig")
    assert C.is_approval(e)["is_approval"] is True
    del e["signature"]
    assert C.is_approval(e)["is_approval"] is False


def test_every_trust_class_has_a_ceiling_on_the_ladder():
    """A class with no ceiling would default to unlimited somewhere later."""
    for tc, ceiling in C.TRUST_CEILING.items():
        assert ceiling in C.LADDER, tc


# --- CapabilityGrant scope and the cage's actual reach ----------------------

def test_a_forbidden_rung_a_cage_cannot_refuse_must_be_acknowledged():
    """A grant listing forbidden:[L7] reads as protection while being, at cage
    level, a comment. It may be issued; it must not pass silently."""
    g = grant(forbidden=["L7"])
    errs = C.validate(g, now=NOW)
    assert any("cage cannot refuse" in m for m in errs)
    g["acknowledged_unenforceable"] = True
    assert C.validate(g, now=NOW) == []


def test_forbidding_only_cage_rungs_needs_no_acknowledgement():
    assert C.validate(grant(forbidden=["L2", "L3"]), now=NOW) == []


def test_enforcement_gap_splits_the_ladder_at_L5():
    gap = C.enforcement_gap(grant(forbidden=["L2", "L4", "L6", "L8"]))
    assert gap["cage_enforceable"] == ["L2", "L4"]
    assert gap["needs_signed_human_grant"] == ["L6", "L8"]
    assert gap["honest"] is False


def test_relative_globs_are_refused():
    """A relative glob means something different in every worker's cwd."""
    g = grant(scope={"fs_read": ["src/**"]})
    assert any("absolute path" in m for m in C.validate(g, now=NOW))
    g["scope"]["fs_read"] = ["/repo/src/**"]
    assert C.validate(g, now=NOW) == []


def test_unknown_scope_keys_and_net_values_are_refused():
    assert any("unknown key" in m
               for m in C.validate(grant(scope={"gpu": ["all"]}), now=NOW))
    assert any("scope.net must be" in m
               for m in C.validate(grant(scope={"net": "maybe"}), now=NOW))


def test_a_grant_is_not_proven_without_a_receipt():
    g = grant(scope={"net": "denied"})
    assert C.proven(g, None, now=NOW)["proven"] is False


def test_the_clock_footgun_bit_a_third_time():
    """Recorded because documenting it twice did not stop it.

    proven() gained a validate() call and immediately inherited the same trap:
    two functions that each default `now` to the wall clock, so a caller fixing
    the clock for one silently compares a fixture timestamp against real time.
    It cost a debugging pass in claim/note over locks_dir, another in
    authorize/validate, and this one. Three occurrences is a design smell, not
    three accidents.
    """
    g = grant(scope={"net": "denied"})
    receipt = {"network": "denied", "engine": "cage",
               "network_evidence": {"attributable_to_cage": True}}
    assert C.proven(g, receipt, now=NOW)["proven"] is True
    late = C.proven(g, receipt)                       # wall clock
    assert late["proven"] is False and "expired" in late["reason"]


def test_a_denial_not_attributed_to_the_cage_does_not_prove_the_grant():
    """The base layer's own catch: this host already blocks outbound, so a bare
    'denied' is the firewall's proof, not the cage's."""
    g = grant(scope={"net": "denied"})
    bare = {"network": "denied", "engine": "userns-netns+landlock",
            "network_evidence": {"attributable_to_cage": False}}
    assert C.proven(g, bare, now=NOW)["proven"] is False
    controlled = {"network": "denied", "engine": "userns-netns+landlock",
                  "network_evidence": {"attributable_to_cage": True,
                                       "control_uncaged": "OPEN",
                                       "cage_result": "REFUSED 101"}}
    assert C.proven(g, controlled, now=NOW)["proven"] is True


def test_an_invalid_grant_cannot_be_proven():
    """Surfaced by the base layer's G-B: refused by validate for forbidding L7
    unacknowledged, yet proven() said True because it read only the receipt.
    A well-behaved cage is not a defence for a promise the schema rejects."""
    good_receipt = {"network": "denied", "engine": "cage",
                    "network_evidence": {"attributable_to_cage": True}}
    bad = grant(forbidden=["L7"], scope={"net": "denied"})
    assert C.proven(bad, good_receipt, now=NOW)["proven"] is False
    bad["acknowledged_unenforceable"] = True
    assert C.proven(bad, good_receipt, now=NOW)["proven"] is True


def human(**over):
    g = {"subject": "agent:executor-7", "actions": ["L7"],
         "signed_by": "jaewon", "signature": "sig", "expires_at": NOW + 600,
         "trust_class": "human_authenticated"}
    g.update(over)
    return g


def test_an_unverifiable_signature_is_never_reported_as_verified():
    """With no key material there is nothing to check against, and 'signed'
    in front of an unchecked field is worse than no signature at all."""
    out = C.verify_human_grant(human(), now=NOW)
    assert out["verified"] is False and out["unverifiable"] is True
    assert out["covers_rungs_no_cage_can_refuse"] == ["L7"]


def test_a_supplied_verifier_decides():
    assert C.verify_human_grant(human(), verifier=lambda p, s: True,
                                now=NOW)["verified"] is True
    assert C.verify_human_grant(human(), verifier=lambda p, s: False,
                                now=NOW)["verified"] is False


def test_an_agent_cannot_issue_a_human_grant():
    out = C.verify_human_grant(human(trust_class="internal_agent"),
                               verifier=lambda p, s: True, now=NOW)
    assert out["verified"] is False and "writing a string" in out["reason"]


def test_the_signature_covers_everything_but_itself():
    a = C._canon_payload(human(signature="one"))
    b = C._canon_payload(human(signature="two"))
    assert a == b, "signature must not cover itself"
    c = C._canon_payload(human(actions=["L8"]))
    assert c != a, "changing the granted rungs must change what is signed"


def test_acknowledging_an_unenforceable_rung_is_honest():
    """Found by a second implementation disagreeing with mine about G-C.
    `honest` must mean honest, not 'fully enforceable' — a grant that declares
    what a cage cannot refuse is being candid, not evasive."""
    strict = C.enforcement_gap(grant(forbidden=["L7"]))
    assert strict["honest"] is False and strict["fully_cage_enforceable"] is False
    ack = C.enforcement_gap(grant(forbidden=["L7"],
                                  acknowledged_unenforceable=True))
    assert ack["honest"] is True
    assert ack["fully_cage_enforceable"] is False      # the fact is unchanged
    assert ack["needs_signed_human_grant"] == ["L7"]
