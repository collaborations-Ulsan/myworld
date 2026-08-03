#!/usr/bin/env python3
"""Packaging regression guard — a wheel that cannot import is not a product.

2026-08-03: walking the import graph of the modules listed in pyproject's
`py-modules` found FOURTEEN modules that shipped code imports but that were
never packaged — including `aios_egress_gate` and `aios_authority`, i.e. the
wheel advertised a sovereignty claim whose enforcement code was absent, and
`aios_turn_loop`, the kernel spine. `pip install aios-os` produced an artifact
whose core paths raised ImportError.

This test makes that class of defect fail in CI instead of in a user's install:
every `aios_*` module reachable from the declared surface must itself be
declared. It is a static check (no build, no network), so it is cheap enough to
run on every commit.

    /home/user/miniconda3/bin/python3 -m pytest -q tests/test_packaging_completeness.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PYPROJECT = ROOT / "pyproject.toml"

# Declared as a package dir rather than a flat module, so it is shipped without
# appearing in py-modules.
PACKAGE_DIRS = {"aios_primitives"}


def declared_modules() -> set[str]:
    """Parse the py-modules list.

    Anchored on the DECLARATION (`py-modules ... = [`), not on the first
    appearance of the string: prose inside the list mentions "py-modules" too,
    and splitting on every occurrence silently truncated the parsed list —
    which made this guard report false failures on its first run.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r"py-modules\s*=\s*\[", text)
    assert m, "pyproject has no py-modules declaration"
    block = text[m.end():]
    block = block[: block.index("]")]
    return set(re.findall(r'"(aios_[a-z0-9_]+)"', block)) | PACKAGE_DIRS


def aios_imports_of(module: str) -> set[str]:
    f = SCRIPTS / f"{module}.py"
    if not f.exists():
        return set()
    try:
        tree = ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names if a.name.startswith("aios_")}
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("aios_"):
                out.add(node.module.split(".")[0])
    return out


def reachable_from_declared() -> set[str]:
    declared = declared_modules()
    frontier, seen, needed = set(declared), set(), set()
    while frontier:
        m = frontier.pop()
        if m in seen:
            continue
        seen.add(m)
        for dep in aios_imports_of(m):
            needed.add(dep)
            if dep not in seen:
                frontier.add(dep)
    return needed


def test_every_imported_module_is_packaged():
    declared = declared_modules()
    missing = sorted(
        m for m in reachable_from_declared()
        if m not in declared and (SCRIPTS / f"{m}.py").exists())
    assert not missing, (
        "modules imported by shipped code but absent from pyproject "
        f"py-modules (the wheel would ImportError): {missing}")


def test_declared_modules_exist_on_disk():
    ghosts = sorted(m for m in declared_modules() - PACKAGE_DIRS
                    if not (SCRIPTS / f"{m}.py").exists())
    assert not ghosts, f"py-modules names files that do not exist: {ghosts}"


@pytest.mark.parametrize("module", [
    "aios_sandbox",        # enforcement: the sovereignty claim
    "aios_egress_gate",    # enforcement: no silent egress
    "aios_authority",      # enforcement: who may do what
    "aios_society",        # the arc kernel
    "aios_takeover_verify",
    "aios_society_watchdog",
    "aios_turn_loop",      # kernel spine
])
def test_load_bearing_modules_are_shipped(module: str):
    """Named individually so a regression says WHICH guarantee was dropped."""
    assert module in declared_modules(), (
        f"{module} carries a product guarantee and must ship in the wheel")


def test_description_does_not_advertise_a_falsified_claim():
    """Claim hygiene: the package must not sell what our own pre-registered
    experiments falsified (three-transport null, C_overall = 0.000)."""
    text = PYPROJECT.read_text(encoding="utf-8")
    desc = re.search(r'^description\s*=\s*"(.*)"', text, re.MULTILINE)
    assert desc, "pyproject has no description"
    body = desc.group(1).lower()
    forbidden = ["carry forward what worked", "gets smarter", "smarter over time",
                 "learns from experience", "compounding intelligence",
                 "improves your agent"]
    hits = [p for p in forbidden if p in body]
    assert not hits, (
        f"package description advertises a falsified claim: {hits} — see "
        "docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
