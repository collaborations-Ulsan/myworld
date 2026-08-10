"""Import bare-named modules from one specific experiment directory.

`experiments/*/` ship files with generic top-level names — `tasks.py`,
`schema.py`, `arms.py`, `grader.py`, `analyze.py`, `evaluate.py`, `verify.py` —
and several experiments use the *same* names. A test that does

    sys.path.insert(0, .../experiments/driftbench)
    import tasks

gets whichever experiment imported first in the session: `sys.modules` is keyed
on the bare name and is never re-checked against `sys.path`.

2026-08-10: that is not hypothetical. `tests/test_distiller.py` is collected
immediately before `tests/test_driftbench_harness.py`; distiller's `evaluate`
imports its own `tasks`, so by the time driftbench ran, `sys.modules["tasks"]`
was `experiments/distiller/tasks.py`. Driftbench silently tested the wrong
module and **34 assertions failed** — while running
`pytest tests/test_driftbench_harness.py` alone passed 49/49. CI runs the whole
suite, so CI saw the 34 and the badge stayed red; every attempt to reproduce it
by running the file on its own said the suite was fine.

`load_from()` closes that hole: it evicts any same-named module that came from
a different directory, puts the requested directory first on `sys.path`, and
imports under the bare names the modules expect (they import each other bare).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType


def _came_from(module: ModuleType, directory: Path) -> bool:
    origin = getattr(module, "__file__", None)
    if not origin:
        return False
    try:
        return Path(origin).resolve().parent == directory
    except OSError:  # pragma: no cover — unresolvable path, treat as foreign
        return False


def load_from(directory: str | Path, *names: str) -> dict[str, ModuleType]:
    """Import `names` from `directory`, displacing same-named foreign modules.

    Pass every bare name the group can claim, including ones imported only
    transitively — distiller's `evaluate` pulls in its own `tasks`, and that
    `tasks` is exactly what leaked into the next test file.
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"experiment directory not found: {directory}")

    for name in names:
        cached = sys.modules.get(name)
        if cached is not None and not _came_from(cached, directory):
            del sys.modules[name]

    path_entry = directory.as_posix()
    while path_entry in sys.path:
        sys.path.remove(path_entry)
    sys.path.insert(0, path_entry)

    loaded: dict[str, ModuleType] = {}
    for name in names:
        module = importlib.import_module(name)
        # A transitive import can still resolve to a stale cache entry that was
        # not in `names`; surface that instead of testing the wrong file.
        if not _came_from(module, directory):
            raise ImportError(
                f"{name!r} resolved to {getattr(module, '__file__', '?')}, "
                f"not {directory} — add every colliding name to load_from()"
            )
        loaded[name] = module
    return loaded
