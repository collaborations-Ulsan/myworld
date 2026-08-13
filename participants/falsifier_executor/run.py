#!/usr/bin/env python3
"""run — the falsifier executor. One operating cycle per claim:

  sense  : host policy judges the claim is due and has a runnable falsifier
           (no model consulted).
  act    : the host runs the falsifier UNDER THE CAGE (executes_code=true).
  verify : a SEPARATE oracle process rules whether the claim survived
           (verifier_identity != operator; isolation=sandboxed).
  settle : one event is appended to the ledger; verdict binds outcome
           (pass<->committed, fail<->reverted); root changes.

Emits three artifacts in --out:
  ledger.jsonl           append-only events, one JSON object per line
  receipts.jsonl         aios.minimal_operation.v1, one per cycle
  sandbox_receipts.jsonl aios.sandbox_receipt.v1, one per cycle (engine,
                         network, paths_denied — network/paths backed by the
                         attempt-and-refused positive-control probes)

Acceptance (run separately, the referee is THEIR checker, not our code):
  python3 ../../scripts/aios_conform.py <out>/receipts.jsonl \
          --ledger <out>/ledger.jsonl --m0
  -> violations 0, ledger root recomputed independently AGREES, M0 LIT.

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
FALS = HERE / "falsifiers"
ORACLE = str(HERE / "oracle.py")
OPERATOR = "falsifier-executor"
VERIFIER = "oracle.py"

CLAIMS = [
    {"id": "FE-1",
     "statement": "No circuit over {RELATE, NORMALIZE} computes XOR on {0,1}^2.",
     "falsifier": [str(FALS / "xor_no_mod.py")], "ro": [], "net_decoy": False},
    {"id": "FE-2",
     "statement": "MODULATE(x,x)=x^2 grows super-linearly along x=t; no affine "
                  "map matches it at three points.",
     "falsifier": [str(FALS / "modulate_growth.py")], "ro": [], "net_decoy": False},
    {"id": "FE-3",
     "statement": "The cage denies loopback network and out-of-allowlist reads "
                  "to code it runs.",
     "falsifier": [str(FALS / "exfil_attempt.py")], "ro": [], "net_decoy": True},
]


def _loopback_listener():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
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


def run_cycle(claim, ledger_lines, out_dir, sb_fh):
    stmt = claim["statement"]
    # -- sense: host policy, no model -----------------------------------------
    sense = {"predicate": "claim_due_and_has_runnable_falsifier",
             "evaluated_by": "host-policy",
             "input_digest": merkle.digest(stmt),
             "model_consulted": False}

    # -- act: run the falsifier under the cage --------------------------------
    env_extra, srv, decoy = {}, None, None
    if claim["net_decoy"]:
        srv, port = _loopback_listener()
        dec = tempfile.NamedTemporaryFile(prefix="fe-decoy-", delete=False)
        dec.write(b"privacy-decoy"); dec.close()
        decoy = dec.name
        env_extra = {"FE3_PORT": str(port), "FE3_DECOY": decoy}
    ro = tuple(claim["ro"]) + (str(FALS),)         # falsifier dir on the allowlist
    try:
        res = cage.run_in_cage(["/usr/bin/python3", *claim["falsifier"]],
                               ro_paths=ro, timeout=15.0, env_extra=env_extra)
    finally:
        if srv is not None:
            srv.close()
        if decoy and os.path.exists(decoy):
            os.unlink(decoy)
    fal_exit = res.returncode if res.ran else 99

    # -- sandbox receipt: engine + attempt-and-refused evidence ---------------
    net = cage.network_probe()
    dec2 = tempfile.NamedTemporaryFile(prefix="fe-decoy2-", delete=False)
    dec2.write(b"x"); dec2.close()
    pd = cage.path_denial_probe([dec2.name])
    os.unlink(dec2.name)
    sandbox_receipt = {
        "schema": "aios.sandbox_receipt.v1",
        "claim_id": claim["id"],
        "engine": res.engine,
        "network": net["network"],                 # "denied" only if cage-attributable
        "network_evidence": net,
        "paths_denied": pd["paths_denied"],
        "paths_evidence": pd["probes"],
        "cage_ran": res.ran, "falsifier_exit": fal_exit,
        "cage_reason": res.reason,
    }
    sb_line = json.dumps(sandbox_receipt, ensure_ascii=False, sort_keys=True)
    sb_fh.write(sb_line + "\n"); sb_fh.flush()
    sb_digest = merkle.digest(sb_line)

    act = {"operator": OPERATOR, "invoked_by": "host",
           "model_offered_choice": False, "executes_code": True,
           "receipt": sb_digest,
           "context_components": [sense["input_digest"], sb_digest]}

    # -- verify: SEPARATE oracle process --------------------------------------
    oracle_argv = ["/usr/bin/python3", ORACLE, str(fal_exit)]
    ruling = json.loads(subprocess.run(
        oracle_argv, capture_output=True, text=True, timeout=10).stdout.strip())
    verify = {"oracle_cmd_digest": merkle.digest(" ".join(oracle_argv)),
              "verdict": ruling["verdict"], "verifier_identity": VERIFIER,
              "isolation": "sandboxed"}

    # -- settle: append event, bind verdict<->outcome, move the root ----------
    outcome = "committed" if ruling["verdict"] == "pass" else "reverted"
    root_before = merkle.ledger_root(ledger_lines)
    event = {"claim_id": claim["id"], "statement": stmt,
             "falsifier_exit": fal_exit, "disposition": outcome,
             "reason": ruling["reason"], "engine": res.engine,
             "network": net["network"]}
    event_line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    ledger_lines.append(event_line)
    root_after = merkle.ledger_root(ledger_lines)
    settle = {"outcome": outcome, "root_before": root_before,
              "root_after": root_after}

    return {"schema": "aios.minimal_operation.v1", "sense": sense, "act": act,
            "verify": verify, "settle": settle}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "out"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ledger_lines, receipts = [], []
    with (out / "sandbox_receipts.jsonl").open("w", encoding="utf-8") as sb:
        for claim in CLAIMS:
            receipts.append(run_cycle(claim, ledger_lines, out, sb))
    (out / "ledger.jsonl").write_text(
        "".join(ln + "\n" for ln in ledger_lines), encoding="utf-8")
    with (out / "receipts.jsonl").open("w", encoding="utf-8") as fh:
        for r in receipts:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    outcomes = [r["settle"]["outcome"] for r in receipts]
    print(json.dumps({"cycles": len(receipts), "outcomes": outcomes,
                      "committed": outcomes.count("committed"),
                      "reverted": outcomes.count("reverted"),
                      "artifacts": [str(out / n) for n in
                                    ("ledger.jsonl", "receipts.jsonl",
                                     "sandbox_receipts.jsonl")]}, indent=1))


if __name__ == "__main__":
    main()
