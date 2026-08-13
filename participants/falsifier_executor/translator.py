#!/usr/bin/env python3
"""translator — the DETERMINISTIC, NON-MODEL edge that decides whether a
ledger row's falsifier is executable-as-authored (spec §2c: the edge whose
output feeds the act).

The hard rule, from claude@myworld's own warning: a MODEL must not translate a
natural-language falsifier into code, because the thing that proposed the claim
would then be writing its own test — that is theatre, not falsification. So
this translator does NOT interpret prose. A row is executable ONLY if a
non-model author has attached a structured `falsifier_exec`:

    "falsifier_exec": {"cmd": ["python3", "falsifiers/xor_no_mod.py"],
                       "ro": ["falsifiers"], "net_decoy": false}

with the fixed exit convention: exit 3 = claim survives (Attested),
exit 0 = claim killed (Refuted), anything else = undefended.

No `falsifier_exec` ⟹ not_executable, with the reason stated. This keeps the
translator (here), the executor (run_edge.py), and the judge (oracle.py) three
separate parties.

Reads one row as JSON on argv[1]; prints one canonical decision JSON line.
Imports nothing from aios_*.
"""
import json
import sys


def classify(row: dict) -> dict:
    fe = row.get("falsifier_exec")
    if isinstance(fe, dict) and isinstance(fe.get("cmd"), list) and fe["cmd"]:
        return {"executable": True, "exec_spec": {
            "cmd": [str(x) for x in fe["cmd"]],
            "ro": [str(x) for x in fe.get("ro", [])],
            "net_decoy": bool(fe.get("net_decoy", False))},
            "reason": "author-supplied structured falsifier_exec"}
    return {"executable": False, "exec_spec": None,
            "reason": ("natural-language falsifier, no author-supplied "
                       "falsifier_exec — a model must not translate it "
                       "(generator-writes-own-test); supply a falsifier_exec "
                       "spec from a non-model author")}


def main():
    row = json.loads(sys.argv[1])
    print(json.dumps(classify(row), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
