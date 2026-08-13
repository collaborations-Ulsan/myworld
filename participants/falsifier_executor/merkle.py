#!/usr/bin/env python3
"""merkle — spec/aios-seam-v0.md §1, reimplemented from the PROSE.

Imports nothing from aios_*. This is the producer's own ledger-identity code;
agreement with scripts/aios_conform.py is the test that the seam is real, and
that agreement is worthless if this file imported the checker's function.
"""
from __future__ import annotations

import hashlib


def _h(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def leaf(i: int, line: str) -> str:
    # decimal(i) || 0x00 || line, position-salted so reordering changes the root
    return _h(f"{i}\x00{line}")


def root(leaves: list[str]) -> str:
    if not leaves:
        return _h("")                       # sha256 of the empty string
    layer = sorted(leaves)
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i + 1] if i + 1 < len(layer) else layer[i]  # odd tail: self
            nxt.append(_h(a + b))           # concatenate the prefixed STRINGS
        layer = nxt
    return layer[0]


def ledger_root(lines: list[str]) -> str:
    return root([leaf(i, ln) for i, ln in enumerate(lines)])


def digest(text: str) -> str:
    return _h(text)
