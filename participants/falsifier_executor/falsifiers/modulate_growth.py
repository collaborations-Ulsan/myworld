#!/usr/bin/env python3
"""Falsifier for claim FE-2:
   "MODULATE(x,x)=x^2 grows super-linearly along the ray x=t, while no affine
    map a*t+b can match it at three distinct points."

Attempts to REFUTE by solving for an affine map through (t, t^2) at t=1,2,3.
An affine map is determined by two points; the third must then disagree, so
the system is inconsistent and no counterexample exists.

Exit 0 -> found an affine map matching t^2 at all three points (claim killed).
Exit 3 -> no such affine map: the separation SURVIVES.
"""
import sys


def main():
    pts = [(1.0, 1.0), (2.0, 4.0), (3.0, 9.0)]        # (t, t^2)
    (t0, y0), (t1, y1), (t2, y2) = pts
    a = (y1 - y0) / (t1 - t0)                          # slope from first two
    b = y0 - a * t0
    if abs(a * t2 + b - y2) < 1e-9:
        print("COUNTEREXAMPLE affine map matches t^2 at three points")
        return 0                                       # claim killed
    print(f"affine fit misses t=3 by {abs(a * t2 + b - y2)} — quadratic is not affine")
    return 3                                            # claim survives


if __name__ == "__main__":
    sys.exit(main())
