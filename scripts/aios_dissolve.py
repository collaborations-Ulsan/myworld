#!/usr/bin/env python3
"""aios.dissolve.v1 — retire the OS layer where it is a label, keep it where it is load-bearing.

Founder's call: the OSes may not need to exist unless they are trained models. Measured
before acting, because a triage of mine archived a file memoryOS imported and broke its
CLI this morning.

  memoryOS      75,136 LOC, 2.0G of accumulated state, a real draft->accept gate, and it
                executed work today. KEEP. It is a store with a gate, which is a component
                worth having; the "OS" framing is what goes.
  CapabilityOS   3,564 LOC, 1 external import, 0 calls today. Its job as re-derived is a
                routing-outcome ledger, which aios_decision_ledger already is in 150 lines.
  GenesisOS      5,348 LOC, 9 external imports. Its job is the adversary, and the adversary
                that actually ran today was council/hub.py redteam.
  hivemind      33,431 LOC, 1 external import, 1,332 state files. Its job is execution
                evidence, which the factory's close-by-check does in 20 lines.

DISSOLUTION IS NOT DELETION. Nothing is removed here. What this does is:
  1. name the surviving capability owner for each dissolved organ, so routing still works
  2. list the exact call sites that must be repointed BEFORE anything moves
  3. refuse to report an organ as dissolvable while a call site still depends on it

The refusal in (3) is the whole file. An organ with live call sites is not a label, whatever
the commit history says.
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PLAN = {
    "CapabilityOS": {"absorb_into": "scripts/aios_decision_ledger.py",
                     "capability_owner": "myworld",
                     "why": "routing-outcome ledger; 150 lines already do it"},
    "GenesisOS": {"absorb_into": "council/hub.py redteam",
                  "capability_owner": "external",
                  "why": "the adversary that ran today was council, not this repo; and a "
                         "same-weights critic is 1.07 effective votes"},
    "hivemind": {"absorb_into": "scripts/aios_factory.py close()",
                 "capability_owner": "myworld",
                 "why": "execution evidence = run a check, read rc"},
}
KEEP = {"memoryOS": "store + draft gate, 2.0G real state, executed work today"}


def call_sites(org: str) -> dict:
    def run(pat, *extra):
        try:
            return [l for l in subprocess.run(
                ["grep", "-rlE", pat, "--include=*.py", *extra, "."],
                capture_output=True, text=True, timeout=60).stdout.splitlines() if l]
        except Exception:
            return ["<grep failed>"]
    imports = [p.removeprefix("./") for p in
               run(rf"^\s*(from|import)\s+\.*({org}|{org.lower()})")]
    imports = [p for p in imports if not p.startswith(f"{org}/")]
    cli = [p.removeprefix("./") for p in
           run(rf"python3 -m {org.lower()}|{org}/[\w/]+\.py")]
    cli = [p for p in cli if not p.startswith(f"{org}/")]
    return {"imports": sorted(set(imports)), "cli": sorted(set(cli))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    report = {"keep": KEEP, "dissolve": {}}
    for org, plan in PLAN.items():
        sites = call_sites(org)
        blocked = sites["imports"] + sites["cli"]
        report["dissolve"][org] = {**plan, **sites,
                                   "ready": not blocked, "blocking": len(blocked)}
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1)); return 0

    for org, why in KEEP.items():
        print(f"  KEEP      {org:<14}{why}")
    print()
    for org, r in report["dissolve"].items():
        state = "READY" if r["ready"] else f"BLOCKED ({r['blocking']} call site)"
        print(f"  {state:<24}{org}")
        print(f"      흡수처   {r['absorb_into']}   (능력 소유자 → {r['capability_owner']})")
        print(f"      근거     {r['why']}")
        for p in r["imports"]:
            print(f"      import   {p}")
        for p in r["cli"]:
            print(f"      CLI      {p}")
        print()
    n = sum(1 for r in report["dissolve"].values() if r["ready"])
    print(f"  {n}/{len(PLAN)} 해체 가능. 나머지는 호출부를 먼저 끊어야 한다 — "
          f"오늘 아침 그 순서를 지키지 않아 memoryOS CLI가 죽었다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
