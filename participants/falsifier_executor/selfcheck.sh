#!/bin/sh
# selfcheck — produce the artifacts, run THEIR checker (external referee), and
# prove the checker BITES on the §2b clause this participant exists to satisfy.
# A checker that cannot reject is not a check; a pass under one that can is
# meaningful. Exit 0 only if all three hold.
set -eu
cd "$(dirname "$0")"
CHECK="../../scripts/aios_conform.py"

python3 run.py >/dev/null
echo "== positive: conformance =="
python3 "$CHECK" out/receipts.jsonl --ledger out/ledger.jsonl --m0

echo "== negative: mutate one receipt to executes_code=true + same_process =="
python3 - <<'PY'
import json
rows = [json.loads(l) for l in open("out/receipts.jsonl")]
rows[0]["verify"]["isolation"] = "same_process"
open("/tmp/fe_bad.jsonl", "w").write("\n".join(json.dumps(r) for r in rows) + "\n")
PY
if python3 "$CHECK" /tmp/fe_bad.jsonl --ledger out/ledger.jsonl >/dev/null 2>&1; then
    echo "FAIL: checker accepted a same_process receipt — the §2b clause is dead"
    exit 1
fi
echo "OK: checker rejected the same_process receipt (exit nonzero) — §2b is live"
rm -f /tmp/fe_bad.jsonl

echo "== §2c: edge-bound cycles (Proposal -> Attested|Refuted) =="
python3 run_edge.py >/dev/null
python3 "$CHECK" out_edge/receipts.jsonl --ledger out_edge/ledger.jsonl --m0

echo "== negative: drop the edge output from act.context_components =="
python3 - <<'PY'
import json
rows = [json.loads(l) for l in open("out_edge/receipts.jsonl")]
d = rows[0]["edge"]["output_digest"]
rows[0]["act"]["context_components"] = [c for c in rows[0]["act"]["context_components"] if c != d]
open("/tmp/fe_edge_bad.jsonl", "w").write("\n".join(json.dumps(r) for r in rows) + "\n")
PY
if python3 "$CHECK" /tmp/fe_edge_bad.jsonl --ledger out_edge/ledger.jsonl >/dev/null 2>&1; then
    echo "FAIL: checker accepted an edge whose output was ignored — §2c is dead"
    exit 1
fi
echo "OK: checker rejected the ignored-edge receipt — §2c binding is live"
rm -f /tmp/fe_edge_bad.jsonl

echo "== honest bridge: classify the real ideation ledger (no fabrication) =="
python3 classify_ledger.py | grep -E 'executable_as_authored|not_executable|rows'
echo "SELFCHECK PASS"
