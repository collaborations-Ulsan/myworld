#!/usr/bin/env python3
"""grant_oracle — the SEPARATE-process judge for a CapabilityGrant cycle.

verifier_identity != operator. It rules on the grant's enforcement claim from
three inputs it did not produce:

    breach_exit  from the adversarial falsifier run under the cage
                 (3 = cage held, 0 = a breach succeeded)
    proven       from the sandbox receipt (net:denied attributable to the cage)
    honest       from the enforcement gap (no unacknowledged L5+ forbidden)

A grant is Attested (pass) iff the cage held AND the receipt proves it AND the
grant does not sell enforcement it lacks. Anything else is Refuted (fail):
a breach, a declaration the host firewall could fake, or a forbidden rung the
cage cannot touch left unmarked.

    python3 grant_oracle.py <breach_exit> <proven:0|1> <honest:0|1>
"""
import json
import sys


def main():
    breach_exit = int(sys.argv[1])
    proven = sys.argv[2] == "1"
    honest = sys.argv[3] == "1"
    held = breach_exit == 3
    if held and proven and honest:
        v, r = "pass", "grant enforced: cage held, denial attributable, no unmarked gap"
    elif not held:
        v, r = "fail", "grant breached: cage did not hold a scope violation"
    elif not proven:
        v, r = "fail", "grant not proven: denial not attributable to the cage (a firewall could fake it)"
    else:
        v, r = "fail", "grant dishonest: forbids a rung above L4 without acknowledging it is not cage-enforced"
    print(json.dumps({"verdict": v, "reason": r}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
