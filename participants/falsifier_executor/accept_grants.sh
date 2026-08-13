#!/bin/sh
# accept_grants — produce the grant-enforcement artifacts and check them against
# BOTH external referees (aios_conform + aios_contracts), then prove each
# referee BITES on the fake it exists to reject. A pass under a referee that
# cannot reject is worthless.
set -eu
cd "$(dirname "$0")"
CONFORM="../../scripts/aios_conform.py"
CONTRACTS="../../scripts/aios_contracts.py"

python3 grant_cycle.py >/dev/null
echo "== seam conformance =="
python3 "$CONFORM" out_grant/receipts.jsonl --ledger out_grant/ledger.jsonl --m0

echo "== their validate: G-A/G-C accepted, G-B refused =="
python3 "$CONTRACTS" validate out_grant/grants/G-A.json >/dev/null && echo "G-A accepted"
python3 "$CONTRACTS" validate out_grant/grants/G-C.json >/dev/null && echo "G-C accepted"
if python3 "$CONTRACTS" validate out_grant/grants/G-B.json >/dev/null 2>&1; then
    echo "FAIL: G-B (forbids L7 unacknowledged) was accepted"; exit 1
fi
echo "G-B refused (forbids L7 unacknowledged) — the enforcement gap bites"

echo "== their proven: net:denied is cage-attributable =="
python3 - <<'PY'
import json, sys
sys.path.insert(0, "../../scripts")
import aios_contracts as c
g = json.loads(open("out_grant/grants/G-A.json").read())
sr = next(json.loads(l) for l in open("out_grant/sandbox_receipts.jsonl")
          if json.loads(l)["grant_id"] == "G-A")
assert c.proven(g, sr)["proven"] is True, "G-A should be proven"
# negative control: strip the positive-control attribution
sr2 = dict(sr); sr2["network_evidence"] = dict(sr["network_evidence"])
sr2["network_evidence"]["attributable_to_cage"] = False
assert c.proven(g, sr2)["proven"] is False, "proven must bite when a firewall could fake denial"
print("proven bites: attributable_to_cage=false -> not proven")
PY

echo "== negative: seam checker bites on ignored edge =="
python3 - <<'PY'
import json
rows = [json.loads(l) for l in open("out_grant/receipts.jsonl")]
d = rows[0]["edge"]["output_digest"]
rows[0]["act"]["context_components"] = [c for c in rows[0]["act"]["context_components"] if c != d]
open("/tmp/fe_g_bad.jsonl", "w").write("\n".join(json.dumps(r) for r in rows) + "\n")
PY
if python3 "$CONFORM" /tmp/fe_g_bad.jsonl --ledger out_grant/ledger.jsonl >/dev/null 2>&1; then
    echo "FAIL: seam checker accepted an ignored-edge receipt"; exit 1
fi
rm -f /tmp/fe_g_bad.jsonl
echo "seam checker bites: ignored edge rejected"
echo "ACCEPT_GRANTS PASS"
