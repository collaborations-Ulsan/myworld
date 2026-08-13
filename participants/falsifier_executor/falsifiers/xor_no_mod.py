#!/usr/bin/env python3
"""Falsifier for claim FE-1:
   "No circuit over {RELATE (affine), NORMALIZE (x/(rho+sum p^2))} can compute
    XOR on {0,1}^2."

This is the real round-1 falsification of my own RMC theorem, now run as
untrusted code UNDER THE CAGE. It builds f(x,y) = -(2/3)s + (10/3)*N(s),
s = x+y, N(s) = s/(1+s^2), and checks all four corners against XOR.

Exit 0  -> counterexample found: the claim is FALSE (killed).
Exit 3  -> no counterexample: the claim SURVIVES.
Self-contained: only arithmetic, no imports of RMC code.
"""
import sys


def N(s):
    return s / (1.0 + s * s)


def f(x, y):
    s = x + y
    return -(2.0 / 3.0) * s + (10.0 / 3.0) * N(s)


def main():
    ok = True
    for x in (0, 1):
        for y in (0, 1):
            if abs(f(x, y) - (x ^ y)) > 1e-9:
                ok = False
    if ok:
        print("COUNTEREXAMPLE RELATE+NORMALIZE computes XOR on {0,1}^2")
        return 0                      # claim killed
    print("no counterexample")
    return 3                          # claim survives


if __name__ == "__main__":
    sys.exit(main())
