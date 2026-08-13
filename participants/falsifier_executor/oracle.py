#!/usr/bin/env python3
"""oracle — the SEPARATE-PROCESS judge (spec §2: verifier_identity != operator).

Given a falsifier's exit code, it rules whether the claim SURVIVED. It runs as
its own process, invoked by the host, and never shares state with the executor
that ran the falsifier — so the thing that executed untrusted code is not the
thing that grades the result.

  exit 3  -> claim survived the falsifier      -> verdict "pass"
  exit 0  -> falsifier found a counterexample  -> verdict "fail" (claim killed)
  other   -> falsifier errored / inconclusive  -> verdict "fail" (undefended)

Prints one JSON line: {"verdict": ..., "reason": ...}.
"""
import json
import sys


def main():
    code = int(sys.argv[1])
    if code == 3:
        v, r = "pass", "claim survived: falsifier found no counterexample"
    elif code == 0:
        v, r = "fail", "claim killed: falsifier found a counterexample"
    else:
        v, r = "fail", f"claim undefended: falsifier exited {code}"
    print(json.dumps({"verdict": v, "reason": r}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
