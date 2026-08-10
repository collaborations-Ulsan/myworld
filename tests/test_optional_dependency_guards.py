#!/usr/bin/env python3
"""Optional-dependency guard regression — a broken optional dep must not crash the core.

2026-08-10: `scripts/aios_escalate.py` probed the optional `treequest` package
with `except ImportError`. On a machine where treequest was *installed but
broken* (it imports jax, and a jax/ml_dtypes version conflict raises
`ValueError` at import time), the narrow handler did not catch it and the
exception propagated — aborting collection of the **entire** test suite, and
taking down any CLI path that touched the module.

CI never saw it: on a clean runner the package is simply absent, so the
ImportError path is the only one exercised. The failure only appears on a
machine that happens to have the optional dependency in a bad state — which is
to say, on a user's machine.

AIOS advertises a core with no required dependencies. That promise means an
optional dependency in any state — absent, broken, half-installed, missing a
native library — must degrade to *unavailable*, never crash. `ImportError`
covers only the first of those.

Rule enforced here: a module-level `try:` that imports a third-party package
must not be guarded by `ImportError`/`ModuleNotFoundError` alone.

    python3 -m pytest -q tests/test_optional_dependency_guards.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

STDLIB = set(sys.stdlib_module_names)

# First-party modules are exempt: they ship in the same wheel, so "absent" is
# the only failure mode that can reach the guard, and ImportError states that
# intent precisely. `scripts` is the repo-relative path used by the dual-import
# pattern (`try: from scripts import x / except ModuleNotFoundError: import x`),
# which resolves differently for a clone than for an installed wheel — also
# first-party.
FIRST_PARTY_PREFIXES = (
    "aios",
    "scripts",
    "memoryos",
    "capabilityos",
    "genesisos",
    "hivemind",
)

NARROW = {"ImportError", "ModuleNotFoundError"}


def _root_package(name: str | None) -> str:
    return (name or "").split(".", 1)[0]


def _is_third_party(name: str | None) -> bool:
    root = _root_package(name)
    if not root:  # relative import (`from . import x`) — first-party by definition
        return False
    if root in STDLIB:
        return False
    return not root.startswith(FIRST_PARTY_PREFIXES)


def _imported_third_party(node: ast.Try) -> list[str]:
    found = []
    for stmt in ast.walk(node):
        if isinstance(stmt, ast.Import):
            found += [a.name for a in stmt.names if _is_third_party(a.name)]
        elif isinstance(stmt, ast.ImportFrom) and stmt.level == 0:
            if _is_third_party(stmt.module):
                found.append(stmt.module or "")
    return found


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    """Exception class names this handler catches. Empty set == bare `except:`."""
    t = handler.type
    if t is None:
        return set()
    parts = t.elts if isinstance(t, ast.Tuple) else [t]
    names = set()
    for p in parts:
        if isinstance(p, ast.Name):
            names.add(p.id)
        elif isinstance(p, ast.Attribute):
            names.add(p.attr)
    return names


def _catches_broadly(handler: ast.ExceptHandler) -> bool:
    names = _handler_names(handler)
    if not names:  # bare except
        return True
    return bool(names & {"Exception", "BaseException"})


def _offenders(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:  # not our concern here; compileall covers it
        return []

    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        packages = _imported_third_party(node)
        if not packages:
            continue
        if any(_catches_broadly(h) for h in node.handlers):
            continue
        narrow_only = {n for h in node.handlers for n in _handler_names(h)}
        if narrow_only and narrow_only <= NARROW:
            bad.append(
                f"{path.name}:{node.lineno} guards {sorted(set(packages))} "
                f"with {sorted(narrow_only)} only"
            )
    return bad


def _script_files() -> list[Path]:
    return sorted(p for p in SCRIPTS.glob("*.py") if p.is_file())


def test_scripts_directory_is_present() -> None:
    assert _script_files(), f"no python files under {SCRIPTS}"


@pytest.mark.parametrize("path", _script_files(), ids=lambda p: p.name)
def test_optional_third_party_imports_degrade_instead_of_crashing(path: Path) -> None:
    offenders = _offenders(path)
    assert not offenders, (
        "Optional third-party import guarded too narrowly — an installed-but-broken "
        "dependency will crash instead of degrading to unavailable.\n  "
        + "\n  ".join(offenders)
        + "\n\nUse `except Exception:` for third-party optional imports."
    )
