#!/usr/bin/env python3
"""Canonical objects for the AIOS seam — the contract layer, made refusable.

Distilled from the 6-turn design conversation in
`docs/ChatGPT-Claude 기술 분석 요청-20260813-1906.md`, keeping only what survived
`docs/AIOS_DESIGN_PRUNED_BY_MEASUREMENT_2026-08-13.md`. The mission-cell,
federation and durable-fabric layers are NOT here: our own pre-registered
experiment closed them, and re-adding them under new names (society →
federation, handoff → dynamic cell) would be reopening a decision, not building.

What survived is the contract layer, and the conversation put it first for a
reason that matches what we measured independently: a specification whose
violations are only described is an offer, and offers measured zero uses in 96
episodes. So every rule below is enforced by `validate()` and each has an
adversarial test naming the fake it rejects.

THE ONE STRUCTURAL IDEA WORTH TAKING WHOLE (design §5):

    agent_id     a durable role — survives session death, survives provider swap
    session_id   one provider's context — dies, is replaced, is not an identity
    endpoint_id  the live connection — the most ephemeral thing in the system

Merging these is the failure cross-session messaging currently has: a peer's
sender is a socket path, so yesterday's advisor cannot be addressed today and a
ledger row cannot say who to ask again. Keeping them apart is what lets an arc
outlive every process that touched it.

The authority model is the design's side-effect ladder plus its trust classes,
and it is deliberately a LATTICE, not a boolean: a browser chatbot may propose
and may not execute, however confident it sounds, and a message from an agent is
never an approval no matter what it says about itself.

    python3 scripts/aios_contracts.py schemas
    python3 scripts/aios_contracts.py validate <file.json>
    python3 scripts/aios_contracts.py authorize --trust browser_chatbot --action L6

Schema: aios.contracts.v1   Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SCHEMA_NS = "aios.contracts.v1"
ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

# --- the side-effect ladder (design §12) ------------------------------------
# Each rung is a SEPARATE grant. The ladder exists so "can this actor act" is
# never one boolean: reading a repo and deploying to production are both "act".
LADDER = {
    "L0": "read",
    "L1": "propose",
    "L2": "modify a disposable sandbox",
    "L3": "produce a patch",
    "L4": "commit to an isolated branch",
    "L5": "open a pull request",
    "L6": "merge",
    "L7": "deploy",
    "L8": "financial or otherwise irreversible external action",
}

# --- trust classes (design §12) ---------------------------------------------
# The ceiling each class may reach WITHOUT an explicit grant. A grant can raise
# an actor within its class ceiling; nothing raises it past the ceiling, which
# is what stops a persuasive advisor from becoming an executor.
TRUST_CEILING = {
    "human_authenticated": "L8",
    "kernel_internal": "L4",
    "internal_agent": "L3",
    "external_federated_agent": "L1",
    # A browser chatbot is UI automation against a consumer product, not a
    # protocol with a stability guarantee. It advises; it does not act.
    "browser_chatbot": "L1",
    "public_web_content": "L0",
    "unknown": "L0",
}

# Only a human may approve. This is the clause that stops the loop from
# ratifying itself: an agent writing "approved" is an agent writing a string.
APPROVAL_TRUST = {"human_authenticated"}

# --- what a cage can actually enforce (2026-08-13) --------------------------
# Requested by the base layer, which lowers a grant to cage flags and reported
# the boundary precisely: namespaces, Landlock and rlimits deterministically
# enforce reading, sandbox modification and patch production. They cannot
# enforce "do not open a pull request" or "do not deploy", because those are not
# operations the kernel mediates — nothing in a cage stands between an agent and
# a remote it is allowed to reach.
#
# Marking that split in the schema matters more than it looks. A grant listing
# `forbidden: ["deploy"]` reads as protection while being, at cage level, a
# comment. The rungs below L5 are refusable by machine; the rest are refusable
# only by a signed human decision, and a grant that mixes them without saying so
# is selling enforcement it does not have.
ENFORCEABLE_BY_CAGE = {"L0", "L1", "L2", "L3", "L4"}

# A scope is the part a cage can lower directly to flags.
SCOPE_KEYS = ("fs_read", "fs_write", "net")
NET_VALUES = ("denied", "allowed")


def enforcement_gap(grant: dict) -> dict:
    """Which of this grant's promises a cage cannot keep.

    The base layer's invariant, made checkable from this side: a grant is REAL
    only where something refuses. Everything else is a declaration, and the
    schema should say which is which rather than letting a reader assume the
    whole object is enforced.
    """
    forbidden = [a for a in grant.get("forbidden", []) if a in LADDER]
    unenforceable = [a for a in forbidden if a not in ENFORCEABLE_BY_CAGE]
    unknown = [a for a in grant.get("forbidden", []) if a not in LADDER]
    return {
        "cage_enforceable": [a for a in forbidden if a in ENFORCEABLE_BY_CAGE],
        "needs_signed_human_grant": unenforceable,
        "not_on_the_ladder": unknown,
        "honest": not unenforceable,
        "reading": ("a forbidden rung above L4 cannot be refused by a cage; it "
                    "is kept out by a signed human decision or it is not kept "
                    "out at all" if unenforceable else
                    "every forbidden rung here is refusable by the cage"),
    }


def proven(grant: dict, sandbox_receipt: dict | None) -> dict:
    """Is this grant backed by something that actually refused?

    Declaration is not enforcement. The sandbox receipt must show an
    attempted-and-refused probe attributable to the cage — the base layer built
    exactly this, using a loopback positive control so a host firewall could not
    be mistaken for the cage doing its job.
    """
    if not sandbox_receipt:
        return {"proven": False, "reason": "no sandbox receipt accompanies this "
                                           "grant, so nothing was shown to refuse"}
    scope = grant.get("scope") or {}
    if scope.get("net") == "denied":
        ev = (sandbox_receipt.get("network_evidence") or {})
        if sandbox_receipt.get("network") != "denied":
            return {"proven": False, "reason": "grant says net denied; receipt "
                                               "does not"}
        if not ev.get("attributable_to_cage"):
            return {"proven": False,
                    "reason": ("denial is not attributed to the cage — without a "
                               "positive control an already-firewalled host "
                               "produces the same observation")}
    return {"proven": True, "engine": sandbox_receipt.get("engine"),
            "note": "proven for the scope keys this receipt covers, no further"}


def _rung(level: str) -> int:
    return int(level[1:])


# --- object shapes ----------------------------------------------------------
# required keys per kind; validation is structural, and semantic rules follow.
REQUIRED = {
    "agent_identity": ("agent_id", "role", "trust_class"),
    "session": ("session_id", "agent_id", "provider"),
    "endpoint": ("endpoint_id", "session_id", "address"),
    "envelope": ("message_id", "arc_id", "from", "to", "kind", "trust_class"),
    "claim": ("claim_id", "statement", "epistemic_type", "falsifier"),
    "capability_grant": ("subject", "actions", "expires_at", "issuer"),
    "verdict": ("verdict_id", "target", "outcome", "oracle_digest",
                "verifier_identity"),
}

EPISTEMIC = ("Proposal", "Observation", "Attested", "Established")
ENVELOPE_KINDS = ("ASK", "HYPOTHESIS", "PROPOSAL", "CHALLENGE", "COUNTEREXAMPLE",
                  "EVIDENCE", "PROGRESS", "BLOCKER", "ARTIFACT_READY", "VERDICT",
                  "RETRACTION")


def validate(obj: dict, *, now: float | None = None,
             seen_idempotency: set[str] | None = None) -> list[str]:
    """Return the reasons this object is refused. Empty list means accepted.

    The five acceptance rules the design named, each of which admits a specific
    forgery if dropped:

      1. unknown schema version   — a producer inventing its own contract
      2. missing causal parent    — an event with no place in a history
      3. cross-tenant reference   — one workspace reaching into another
      4. expired grant            — authority that outlived its issuance
      5. duplicate idempotency    — one intent producing two effects
    """
    now = time.time() if now is None else now
    bad: list[str] = []

    schema = obj.get("schema", "")
    if not isinstance(schema, str) or not schema.startswith(SCHEMA_NS + "."):
        bad.append(f"unknown schema version: {schema!r} — a producer that "
                   f"invents its own contract is not a participant")
        return bad
    kind = schema[len(SCHEMA_NS) + 1:]
    if kind not in REQUIRED:
        bad.append(f"unknown object kind: {kind!r}")
        return bad
    for k in REQUIRED[kind]:
        if k not in obj:
            bad.append(f"{kind}.{k} missing")
    if bad:
        return bad

    if kind == "agent_identity":
        if not ID.match(str(obj["agent_id"])):
            bad.append(f"agent_id is not a durable identifier: {obj['agent_id']!r}")
        if obj["trust_class"] not in TRUST_CEILING:
            bad.append(f"unknown trust_class: {obj['trust_class']!r}")

    if kind == "session":
        # A session is NOT an identity. It must name the durable agent it
        # currently embodies, or the agent disappears when the session does.
        if not ID.match(str(obj["agent_id"])):
            bad.append("session.agent_id must name a durable agent — a session "
                       "that is its own identity cannot be resumed")

    if kind == "endpoint":
        if not ID.match(str(obj["session_id"])):
            bad.append("endpoint.session_id must name a session; an endpoint is "
                       "the most ephemeral object and owns nothing")

    if kind == "envelope":
        if obj["kind"] not in ENVELOPE_KINDS:
            bad.append(f"envelope.kind not in {ENVELOPE_KINDS}: {obj['kind']!r}")
        if obj["trust_class"] not in TRUST_CEILING:
            bad.append(f"unknown trust_class: {obj['trust_class']!r}")
        # rule 2 — causal parent
        if not obj.get("root") and not obj.get("causation_id"):
            bad.append("envelope has neither root=true nor causation_id — an "
                       "event with no causal parent cannot be placed in a history")
        # rule 3 — cross-tenant
        w_from = (obj.get("from") or {}).get("workspace_id")
        w_to = (obj.get("to") or {}).get("workspace_id")
        if w_from and w_to and w_from != w_to:
            bad.append(f"cross-tenant reference: {w_from!r} -> {w_to!r}")
        # rule 5 — idempotency
        key = (obj.get("delivery") or {}).get("idempotency_key")
        if seen_idempotency is not None and key:
            if key in seen_idempotency:
                bad.append(f"duplicate idempotency_key: {key!r} — one intent "
                           f"must not produce two effects")
            else:
                seen_idempotency.add(key)

    if kind == "claim":
        if obj["epistemic_type"] not in EPISTEMIC:
            bad.append(f"epistemic_type not in {EPISTEMIC}")
        if not str(obj.get("falsifier", "")).strip():
            bad.append("claim.falsifier is empty — a claim with no named way to "
                       "kill it is a quote, not a claim")
        if obj["epistemic_type"] != "Proposal" and not obj.get("receipt"):
            bad.append(f"epistemic_type={obj['epistemic_type']} without a "
                       f"receipt — only an execution receipt raises a claim "
                       f"above Proposal")

    if kind == "capability_grant":
        # rule 4 — expiry
        try:
            if float(obj["expires_at"]) <= now:
                bad.append("capability_grant has expired — authority does not "
                           "outlive its issuance")
        except (TypeError, ValueError):
            bad.append(f"expires_at is not a timestamp: {obj['expires_at']!r}")
        for a in obj["actions"]:
            if a not in LADDER:
                bad.append(f"grant names a rung outside the ladder: {a!r}")
        sc = obj.get("scope")
        if sc is not None:
            if not isinstance(sc, dict):
                bad.append("grant.scope must be an object")
            else:
                for k in sc:
                    if k not in SCOPE_KEYS:
                        bad.append(f"grant.scope has unknown key {k!r}; "
                                   f"known: {SCOPE_KEYS}")
                if "net" in sc and sc["net"] not in NET_VALUES:
                    bad.append(f"grant.scope.net must be one of {NET_VALUES}")
                for k in ("fs_read", "fs_write"):
                    if k in sc and not (isinstance(sc[k], list)
                                        and all(isinstance(g, str) and g.startswith("/")
                                                for g in sc[k])):
                        bad.append(f"grant.scope.{k} must be absolute path "
                                   f"globs — a relative glob means something "
                                   f"different in every worker's cwd")
        # A grant that forbids what no cage can refuse must not read as
        # protection. It may still be issued; it must be marked.
        gap = enforcement_gap(obj)
        if gap["needs_signed_human_grant"] and not obj.get("acknowledged_unenforceable"):
            bad.append(f"grant forbids {gap['needs_signed_human_grant']} which a "
                       f"cage cannot refuse; set acknowledged_unenforceable=true "
                       f"to state that this relies on a signed human decision "
                       f"rather than on enforcement")

    if kind == "verdict":
        if obj["outcome"] not in ("pass", "fail"):
            bad.append(f"verdict.outcome not in pass|fail: {obj['outcome']!r}")
        if not DIGEST.match(str(obj["oracle_digest"])):
            bad.append("verdict.oracle_digest is not sha256:<64 hex>")
        if obj.get("verifier_identity") == obj.get("executor_identity"):
            bad.append("verdict.verifier_identity == executor_identity — the "
                       "executor is grading itself")
    return bad


def authorize(trust_class: str, action: str, *,
              grant: dict | None = None, now: float | None = None) -> dict:
    """May an actor of this trust class take this rung?

    Two independent gates, and BOTH must pass. The ceiling is a property of what
    the actor IS and cannot be granted away; the grant is a property of what it
    was permitted, and expires. An actor with a valid grant above its ceiling is
    still refused — that is what keeps a persuasive advisor from executing.
    """
    now = time.time() if now is None else now
    if trust_class not in TRUST_CEILING:
        return {"allowed": False, "reason": f"unknown trust_class {trust_class!r}"}
    if action not in LADDER:
        return {"allowed": False, "reason": f"unknown action {action!r}"}

    ceiling = TRUST_CEILING[trust_class]
    if _rung(action) > _rung(ceiling):
        return {"allowed": False, "ceiling": ceiling,
                "reason": (f"{trust_class} may not reach {action} "
                           f"({LADDER[action]}); its ceiling is {ceiling}. "
                           f"No grant raises a class ceiling.")}
    if _rung(action) >= _rung("L2"):
        if not grant:
            return {"allowed": False, "reason": f"{action} requires an explicit "
                                                f"capability grant"}
        errs = validate(grant, now=now)
        if errs:
            return {"allowed": False, "reason": f"grant refused: {errs[0]}"}
        if action not in grant.get("actions", []):
            return {"allowed": False,
                    "reason": f"grant does not include {action}"}
        if action in grant.get("forbidden", []):
            return {"allowed": False, "reason": f"grant forbids {action}"}
    return {"allowed": True, "action": action, "ceiling": ceiling}


def is_approval(envelope: dict) -> dict:
    """Does this message constitute an approval? Almost never.

    An agent-authored 'approved' is a string an agent wrote. Treating it as
    consent is how an autonomous loop ratifies itself, and it is the single
    clause most likely to be quietly relaxed later, so it is a function with a
    test rather than a sentence in a document.
    """
    tc = envelope.get("trust_class")
    ok = tc in APPROVAL_TRUST and envelope.get("kind") == "DECISION_REQUEST" \
        and bool(envelope.get("signature"))
    return {"is_approval": ok, "trust_class": tc,
            "reason": ("approval requires a human-authenticated, signed "
                       "decision; agent text is never consent")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("schemas", help="what this layer accepts")
    v = sub.add_parser("validate")
    v.add_argument("path", type=Path)
    a = sub.add_parser("authorize")
    a.add_argument("--trust", required=True)
    a.add_argument("--action", required=True)
    a.add_argument("--grant", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.cmd == "schemas":
        print(json.dumps({
            "namespace": SCHEMA_NS, "kinds": sorted(REQUIRED),
            "ladder": LADDER, "trust_ceiling": TRUST_CEILING,
            "epistemic_types": list(EPISTEMIC),
            "note": ("agent_id / session_id / endpoint_id are separate on "
                     "purpose: a session dies, an endpoint dies sooner, and the "
                     "agent must outlive both or nothing can be resumed"),
        }, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "validate":
        obj = json.loads(args.path.read_text(encoding="utf-8"))
        errs = validate(obj)
        print(json.dumps({"accepted": not errs, "refusals": errs},
                         ensure_ascii=False, indent=1))
        return 1 if errs else 0
    grant = json.loads(args.grant.read_text(encoding="utf-8")) if args.grant else None
    out = authorize(args.trust, args.action, grant=grant)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
