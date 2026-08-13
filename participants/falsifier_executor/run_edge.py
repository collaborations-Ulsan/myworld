#!/usr/bin/env python3
"""run_edge — §2c binding: every cycle carries a host-invoked translator EDGE
whose output feeds the act, so "invoked ≠ used" is closed by construction.

  edge   : the host runs translator.py on the row (invoked_by=host). Its
           decision (executable + exec_spec, or not_executable) is the edge
           output; edge.output_digest ∈ act.context_components, so a checker
           bites if the act ignored it.
  act    : the executor runs, UNDER THE CAGE, either the author-supplied
           executable falsifier, or a marker exiting 88 (not_executable).
           executes_code=true.
  verify : a SEPARATE oracle process rules on the exit code.
  settle : the ledger event records the epistemic transition
           Proposal → {Attested | Refuted | Proposal(not_executable)}.

Three parties, none of them a model at runtime: translator (edge), executor
(act), oracle (verify).

  python3 run_edge.py --claims fe_claims.jsonl --out out_edge
  python3 ../../scripts/aios_conform.py out_edge/receipts.jsonl \
          --ledger out_edge/ledger.jsonl --m0

Imports nothing from aios_*.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import threading
from pathlib import Path

import cage
import merkle

HERE = Path(__file__).resolve().parent
TRANSLATOR = str(HERE / "translator.py")
ORACLE = str(HERE / "oracle.py")
OPERATOR = "falsifier-executor"
VERIFIER = "oracle.py"
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


def run_cycle(row, ledger_lines, sb_fh):
    stmt = row.get("claim", row.get("statement", ""))
    sense = {"predicate": "proposal_due_for_falsification",
             "evaluated_by": "host-policy", "input_digest": merkle.digest(stmt),
             "model_consulted": False}

    # -- edge: host runs the deterministic translator on the row --------------
    edge_argv = [PY, TRANSLATOR, json.dumps(
        {"claim": stmt, "falsifier": row.get("falsifier", ""),
         "falsifier_exec": row.get("falsifier_exec")}, ensure_ascii=False)]
    edge_out = subprocess.run(edge_argv, capture_output=True, text=True,
                              timeout=15).stdout.strip()
    decision = json.loads(edge_out)
    edge_digest = merkle.digest(edge_out)

    # -- act: run the executable falsifier, or a not_executable marker --------
    env_extra, srv, decoy = {}, None, None
    if decision["executable"]:
        spec = decision["exec_spec"]
        # cmd[0] is the interpreter name; resolve script args to absolute paths
        # under HERE (the cage cwd is a scratch dir, so relatives would miss).
        args = [str(HERE / a) if (a.endswith(".py") and not os.path.isabs(a))
                else a for a in spec["cmd"][1:]]
        argv = [PY, *args]
        ro = tuple(str(HERE / p) for p in spec["ro"])
        if spec["net_decoy"]:
            srv, port = _loopback_listener()
            d = tempfile.NamedTemporaryFile(prefix="fe-decoy-", delete=False)
            d.write(b"privacy-decoy"); d.close(); decoy = d.name
            env_extra = {"FE3_PORT": str(port), "FE3_DECOY": decoy}
    else:
        argv = [PY, "-c", "import sys; sys.exit(88)"]   # not_executable marker
        ro = ()
    try:
        res = cage.run_in_cage(argv, ro_paths=ro, timeout=15.0,
                               env_extra=env_extra)
    finally:
        if srv is not None:
            srv.close()
        if decoy and os.path.exists(decoy):
            os.unlink(decoy)
    fal_exit = res.returncode if res.ran else 99

    net = cage.network_probe()
    d2 = tempfile.NamedTemporaryFile(prefix="fe-decoy2-", delete=False)
    d2.write(b"x"); d2.close()
    pd = cage.path_denial_probe([d2.name]); os.unlink(d2.name)
    sandbox_receipt = {
        "schema": "aios.sandbox_receipt.v1", "claim_id": row.get("id"),
        "engine": res.engine, "network": net["network"],
        "network_evidence": net, "paths_denied": pd["paths_denied"],
        "cage_ran": res.ran, "falsifier_exit": fal_exit,
        "executable": decision["executable"], "translator_reason": decision["reason"]}
    sb_line = json.dumps(sandbox_receipt, ensure_ascii=False, sort_keys=True)
    sb_fh.write(sb_line + "\n"); sb_fh.flush()
    sb_digest = merkle.digest(sb_line)

    act = {"operator": OPERATOR, "invoked_by": "host",
           "model_offered_choice": False, "executes_code": True,
           "receipt": sb_digest,
           "context_components": [sense["input_digest"], edge_digest, sb_digest]}
    edge = {"edge_id": f"translate:{row.get('id','?')}", "invoked_by": "host",
            "output_digest": edge_digest}

    # -- verify: separate oracle ---------------------------------------------
    oracle_argv = [PY, ORACLE, str(fal_exit)]
    ruling = json.loads(subprocess.run(oracle_argv, capture_output=True,
                                       text=True, timeout=10).stdout.strip())
    verify = {"oracle_cmd_digest": merkle.digest(" ".join(oracle_argv)),
              "verdict": ruling["verdict"], "verifier_identity": VERIFIER,
              "isolation": "sandboxed"}

    # -- settle: epistemic transition + coarse seam outcome -------------------
    outcome = "committed" if ruling["verdict"] == "pass" else "reverted"
    if not decision["executable"]:
        transition = "Proposal->Proposal(not_executable)"
    elif fal_exit == 0:
        transition = "Proposal->Refuted"
    elif fal_exit == 3:
        transition = "Proposal->Attested"
    else:
        transition = "Proposal->Proposal(undefended)"
    root_before = merkle.ledger_root(ledger_lines)
    event = {"claim_id": row.get("id"), "claim": stmt,
             "epistemic_before": "Proposal",
             "epistemic_transition": transition, "seam_outcome": outcome,
             "falsifier_exit": fal_exit, "reason": ruling["reason"],
             "executable": decision["executable"]}
    ledger_lines.append(json.dumps(event, ensure_ascii=False, sort_keys=True))
    root_after = merkle.ledger_root(ledger_lines)
    settle = {"outcome": outcome, "root_before": root_before,
              "root_after": root_after}

    return ({"schema": "aios.minimal_operation.v1", "sense": sense, "act": act,
             "edge": edge, "verify": verify, "settle": settle}, transition)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", default=str(HERE / "fe_claims.jsonl"))
    ap.add_argument("--out", default=str(HERE / "out_edge"))
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.claims) if l.strip()]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ledger_lines, receipts, transitions = [], [], []
    with (out / "sandbox_receipts.jsonl").open("w", encoding="utf-8") as sb:
        for row in rows:
            rec, tr = run_cycle(row, ledger_lines, sb)
            receipts.append(rec); transitions.append(tr)
    (out / "ledger.jsonl").write_text(
        "".join(l + "\n" for l in ledger_lines), encoding="utf-8")
    with (out / "receipts.jsonl").open("w", encoding="utf-8") as fh:
        for r in receipts:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(json.dumps({"cycles": len(receipts),
                      "transitions": dict(Counter(transitions)),
                      "outcomes": dict(Counter(
                          r["settle"]["outcome"] for r in receipts))}, indent=1))


if __name__ == "__main__":
    main()
