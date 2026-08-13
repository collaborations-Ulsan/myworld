#!/usr/bin/env python3
"""classify_ledger — run the deterministic translator over claude@myworld's
real ideation ledger and report, HONESTLY, how many Proposals could actually
be advanced by execution vs. how many are not_executable-as-authored.

No epistemic type is changed here: a Proposal is not advanced unless a real
falsifier RUNS to a verdict (that is run_edge.py's job, and only on rows that
carry an author-supplied falsifier_exec). This script is the honest bridge: it
answers "can the compounding loop even turn on from this ledger?" without
fabricating a single test.

  python3 classify_ledger.py ../../ideation/ledger.jsonl
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRANSLATOR = str(HERE / "translator.py")


def main():
    ledger = sys.argv[1] if len(sys.argv) > 1 else str(HERE.parents[1] / "ideation" / "ledger.jsonl")
    rows = [json.loads(l) for l in open(ledger) if l.strip()]
    decisions = []
    for r in rows:
        row = {"claim": r.get("claim", ""), "falsifier": r.get("falsifier", ""),
               "falsifier_exec": r.get("falsifier_exec")}
        out = subprocess.run(["/usr/bin/python3", TRANSLATOR,
                              json.dumps(row, ensure_ascii=False)],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        d = json.loads(out)
        decisions.append({"item_id": r.get("item_id"),
                          "epistemic_type": r.get("epistemic_type"),
                          "executable": d["executable"], "reason": d["reason"]})
    n = len(decisions)
    ex = sum(d["executable"] for d in decisions)
    report = {
        "ledger": ledger, "rows": n,
        "executable_as_authored": ex,
        "not_executable": n - ex,
        "advanceable_now": ex,
        "epistemic_types": dict(Counter(d["epistemic_type"] for d in decisions)),
        "finding": (f"{ex}/{n} of the ledger's falsifiers are executable as "
                    "authored; the compounding loop Proposal->Attested|Refuted "
                    "cannot turn on until falsifiers are authored with a "
                    "structured falsifier_exec (a non-model translator, or the "
                    "claim's author, must supply it — a model translating the "
                    "NL falsifier would be the generator writing its own test)."),
        "decisions": decisions,
    }
    out = HERE / "out_edge" / "ledger_translation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "decisions"}, indent=1))


if __name__ == "__main__":
    main()
