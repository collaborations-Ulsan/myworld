#!/usr/bin/env python3
"""Adversarial falsifier for a CapabilityGrant's cage-enforceable scope.

Untrusted code that TRIES TO EXCEED the grant, run under the cage the grant was
lowered onto. It attempts every cage-scope violation and reports whether the
cage held:

  - net: if the grant denies network, attempt a loopback connect (FE_PORT).
  - fs_write: attempt to write OUTSIDE the writable scope (FE_OUTSIDE_WRITE).
  - fs_read:  attempt to read OUTSIDE the readable scope (FE_OUTSIDE_READ).

Exit 0  -> a breach succeeded: the grant's enforcement claim is FALSE (killed).
Exit 3  -> every attempt refused: the cage held the grant (survives).
"""
import os
import socket
import sys


def net_breach():
    port = int(os.environ.get("FE_PORT", "0"))
    if not port:
        return False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3); s.connect(("127.0.0.1", port)); s.close()
        return True
    except OSError:
        return False


def write_breach():
    p = os.environ.get("FE_OUTSIDE_WRITE", "")
    if not p:
        return False
    try:
        with open(p, "w") as fh:
            fh.write("breach")
        return True
    except OSError:
        return False


def read_breach():
    p = os.environ.get("FE_OUTSIDE_READ", "")
    if not p:
        return False
    try:
        with open(p, "rb") as fh:
            fh.read(1)
        return True
    except OSError:
        return False


def main():
    n, w, r = net_breach(), write_breach(), read_breach()
    if n or w or r:
        print(f"BREACH net={n} write={w} read={r}")
        return 0
    print("cage held: net/write/read all refused")
    return 3


if __name__ == "__main__":
    sys.exit(main())
