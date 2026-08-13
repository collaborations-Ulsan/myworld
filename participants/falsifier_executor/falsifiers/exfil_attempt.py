#!/usr/bin/env python3
"""Falsifier for claim FE-3:
   "The cage denies, to code it runs, both off-box/loopback network and reads
    of a path outside its allowlist."

This is untrusted code that TRIES TO BREACH: it attempts to connect to a host
loopback port (passed via FE3_PORT) and to read a decoy file (FE3_DECOY). If
EITHER succeeds, the cage failed and the claim is killed.

Exit 0 -> a breach succeeded (claim killed).
Exit 3 -> both attempts refused: the cage held, claim SURVIVES.
"""
import os
import socket
import sys


def try_net(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        return False


def try_read(path):
    try:
        with open(path, "rb") as fh:
            fh.read(1)
        return True
    except OSError:
        return False


def main():
    port = int(os.environ.get("FE3_PORT", "0"))
    decoy = os.environ.get("FE3_DECOY", "/nonexistent")
    net_breach = try_net(port) if port else False
    read_breach = try_read(decoy)
    if net_breach or read_breach:
        print(f"BREACH net={net_breach} read={read_breach}")
        return 0                        # claim killed: cage leaked
    print("both attempts refused by the cage")
    return 3                            # claim survives: cage held


if __name__ == "__main__":
    sys.exit(main())
