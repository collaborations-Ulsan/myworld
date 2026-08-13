#!/usr/bin/env python3
"""grant_cycle — enforce CapabilityGrants by lowering them onto the cage and
proving, per grant, that the cage actually refused what the grant forbids.

One cycle per grant:
  edge   : host lowers the grant to cage flags (grant_lower.lower) — a
           deterministic, non-model step whose output feeds the act.
  act    : the adversarial breach falsifier runs UNDER the lowered cage
           (executes_code=true); it attempts every cage-scope violation.
  verify : grant_oracle (separate process) rules pass iff the cage held AND
           the sandbox receipt PROVES denial is the cage's (positive control)
           AND the grant does not sell L5+ enforcement it lacks.
  settle : the ledger records the grant's disposition; verdict binds outcome.

Acceptance (external referees, not our code):
  python3 ../../scripts/aios_conform.py out_grant/receipts.jsonl \
          --ledger out_grant/ledger.jsonl --m0        -> violations 0, reverted>=1
  python3 ../../scripts/aios_contracts.py validate <grant>   -> accepted/refused
  aios_contracts.proven(grant, sandbox_receipt)              -> proven:true (G-A/G-C)

Imports nothing from aios_*.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
from pathlib import Path

import cage
import grant_lower
import merkle

HERE = Path(__file__).resolve().parent
FALS = HERE / "falsifiers"
GRANT_ORACLE = str(HERE / "grant_oracle.py")
OPERATOR = "grant-enforcer"
VERIFIER = "grant_oracle.py"
PY = "/usr/bin/python3"


def _loopback_listener():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0)); srv.listen(8)
    port = srv.getsockname()[1]

    def serve():
        srv.settimeout(30)
        try:
            while True:
                c, _ = srv.accept(); c.close()
        except OSError:
            pass
    threading.Thread(target=serve, daemon=True).start()
    return srv, port


def make_workspace() -> dict:
    """A real repo-shaped tree so the grants reference absolute paths that
    exist: src/ (read scope), .sandbox/ (write scope), a secret OUTSIDE both."""
    root = tempfile.mkdtemp(prefix="fe-ws-")
    os.makedirs(os.path.join(root, "src"))
    os.makedirs(os.path.join(root, ".sandbox"))
    with open(os.path.join(root, "src", "main.py"), "w") as fh:
        fh.write("# readable\n")
    with open(os.path.join(root, "secret_outside.txt"), "w") as fh:
        fh.write("out-of-scope secret\n")
    return {"root": root,
            "fs_read": os.path.join(root, "src"),
            "fs_write": os.path.join(root, ".sandbox"),
            "outside_read": os.path.join(root, "secret_outside.txt"),
            "outside_write": os.path.join(root, "src", "evil.txt")}


def grants_for(ws) -> list[dict]:
    """Three grants exercising Attested (committed) and Refuted (reverted)."""
    far = 1_900_000_000                      # far-future expiry (fixed, no clock)
    return [
        {"schema": "aios.contracts.v1.capability_grant", "id": "G-A",
         "subject": "agent:executor-7", "actions": ["L0", "L2", "L3"],
         "scope": {"fs_read": [ws["fs_read"] + "/**"],
                   "fs_write": [ws["fs_write"] + "/**"], "net": "denied"},
         "forbidden": ["L2"], "expires_at": far, "issuer": "policy-kernel",
         "_note": "valid, cage-enforceable, net denied -> Attested"},
        {"schema": "aios.contracts.v1.capability_grant", "id": "G-B",
         "subject": "agent:executor-7", "actions": ["L0"],
         "scope": {"fs_read": [ws["fs_read"] + "/**"], "net": "denied"},
         "forbidden": ["L7"], "expires_at": far, "issuer": "policy-kernel",
         "_note": "forbids L7 (deploy) as if cage-enforced, unacknowledged "
                  "-> dishonest -> Refuted (and their validate rejects it)"},
        {"schema": "aios.contracts.v1.capability_grant", "id": "G-C",
         "subject": "agent:executor-7", "actions": ["L0", "L2"],
         "scope": {"fs_read": [ws["fs_read"] + "/**"],
                   "fs_write": [ws["fs_write"] + "/**"], "net": "denied"},
         "forbidden": ["L7"], "acknowledged_unenforceable": True,
         "expires_at": far, "issuer": "policy-kernel",
         "_note": "same L7 forbid but ACKNOWLEDGED as human-decision -> honest "
                  "-> Attested"},
    ]


def run_cycle(grant, ws, ledger_lines, sb_fh):
    gid = grant["id"]
    flags = grant_lower.lower(grant)
    honest = flags["enforcement_gap"]["honest"]
    sense = {"predicate": "grant_pending_enforcement",
             "evaluated_by": "host-policy",
             "input_digest": merkle.digest(json.dumps(grant, sort_keys=True)),
             "model_consulted": False}
    edge_out = json.dumps({"ro_paths": flags["ro_paths"],
                           "rw_paths": flags["rw_paths"],
                           "allow_net": flags["allow_net"],
                           "gap": flags["enforcement_gap"]}, sort_keys=True)
    edge_digest = merkle.digest(edge_out)

    # -- act: breach falsifier under the lowered cage -------------------------
    srv, port = _loopback_listener()
    try:
        env = {"FE_PORT": str(port) if not flags["allow_net"] else "",
               "FE_OUTSIDE_WRITE": ws["outside_write"],
               "FE_OUTSIDE_READ": ws["outside_read"]}
        ro = tuple(flags["ro_paths"]) + (str(FALS),)
        res = cage.run_in_cage([PY, str(FALS / "grant_breach.py")],
                               ro_paths=ro, timeout=15.0,
                               allow_net=flags["allow_net"], env_extra=env)
    finally:
        srv.close()
    breach_exit = res.returncode if res.ran else 99

    # -- sandbox receipt with positive-control evidence -----------------------
    net = cage.network_probe()
    d2 = tempfile.NamedTemporaryFile(prefix="fe-d2-", delete=False)
    d2.write(b"x"); d2.close()
    pd = cage.path_denial_probe([d2.name]); os.unlink(d2.name)
    # enforcement_gap on the receipt (producer-side field, requested by
    # claude@myworld/upper): a receipt that does not name the gap looks like a
    # receipt with no gap. This surfaces, in the durable record, which of the
    # grant's forbidden rungs the cage could NOT refuse.
    sandbox_receipt = {
        "schema": "aios.sandbox_receipt.v1", "grant_id": gid,
        "engine": res.engine, "network": net["network"],
        "network_evidence": net, "paths_denied": pd["paths_denied"],
        "enforcement_gap": flags["enforcement_gap"],
        "cage_ran": res.ran, "breach_exit": breach_exit}
    sb_line = json.dumps(sandbox_receipt, ensure_ascii=False, sort_keys=True)
    sb_fh.write(sb_line + "\n"); sb_fh.flush()
    sb_digest = merkle.digest(sb_line)

    # proven(grant, receipt) — reimplemented from prose; net:denied must be
    # attributable to the cage, else a firewall could fake the observation.
    scope = grant.get("scope") or {}
    if scope.get("net") == "denied":
        proven = (sandbox_receipt["network"] == "denied"
                  and net.get("attributable_to_cage") is True)
    else:
        proven = True

    act = {"operator": OPERATOR, "invoked_by": "host",
           "model_offered_choice": False, "executes_code": True,
           "receipt": sb_digest,
           "context_components": [sense["input_digest"], edge_digest, sb_digest]}
    edge = {"edge_id": f"lower:{gid}", "invoked_by": "host",
            "output_digest": edge_digest}

    # -- verify: separate grant oracle ---------------------------------------
    oracle_argv = [PY, GRANT_ORACLE, str(breach_exit),
                   "1" if proven else "0", "1" if honest else "0"]
    ruling = json.loads(subprocess.run(oracle_argv, capture_output=True,
                                       text=True, timeout=10).stdout.strip())
    verify = {"oracle_cmd_digest": merkle.digest(" ".join(oracle_argv)),
              "verdict": ruling["verdict"], "verifier_identity": VERIFIER,
              "isolation": "sandboxed"}

    outcome = "committed" if ruling["verdict"] == "pass" else "reverted"
    disposition = "Attested" if outcome == "committed" else "Refuted"
    root_before = merkle.ledger_root(ledger_lines)
    event = {"grant_id": gid, "subject": grant["subject"],
             "disposition": disposition, "seam_outcome": outcome,
             "breach_exit": breach_exit, "proven": proven, "honest": honest,
             "enforcement_gap": flags["enforcement_gap"],
             "reason": ruling["reason"]}
    ledger_lines.append(json.dumps(event, ensure_ascii=False, sort_keys=True))
    root_after = merkle.ledger_root(ledger_lines)
    settle = {"outcome": outcome, "root_before": root_before,
              "root_after": root_after}
    return {"schema": "aios.minimal_operation.v1", "sense": sense, "act": act,
            "edge": edge, "verify": verify, "settle": settle}, disposition


def main():
    out = HERE / "out_grant"; out.mkdir(parents=True, exist_ok=True)
    (out / "grants").mkdir(exist_ok=True)
    ws = make_workspace()
    try:
        grants = grants_for(ws)
        for g in grants:                     # persist grants for the referee
            (out / "grants" / f"{g['id']}.json").write_text(
                json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
        ledger_lines, receipts, dispositions = [], [], []
        with (out / "sandbox_receipts.jsonl").open("w", encoding="utf-8") as sb:
            for g in grants:
                rec, disp = run_cycle(g, ws, ledger_lines, sb)
                receipts.append(rec); dispositions.append(disp)
        (out / "ledger.jsonl").write_text(
            "".join(l + "\n" for l in ledger_lines), encoding="utf-8")
        with (out / "receipts.jsonl").open("w", encoding="utf-8") as fh:
            for r in receipts:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    finally:
        shutil.rmtree(ws["root"], ignore_errors=True)
    from collections import Counter
    print(json.dumps({"cycles": len(receipts),
                      "dispositions": dict(Counter(dispositions)),
                      "outcomes": dict(Counter(r["settle"]["outcome"]
                                               for r in receipts))}, indent=1))


if __name__ == "__main__":
    main()
