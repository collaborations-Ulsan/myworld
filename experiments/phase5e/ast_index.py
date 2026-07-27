#!/usr/bin/env python3
"""Channel-E stack-trace AST-closure masking (prereg §2b + Errata op-2).

FROZEN PROTOCOL: docs/AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md.

Builds an offline AST index of a task workspace's Python files, extracts the
frame set F from the FAILING TEST'S output (given in the initial task state,
never derived from the solution), computes the k-hop static call-graph closure
C(F) (k=2, frozen; UNDIRECTED expansion; simple-name edge resolution), and
returns the treatment arm's visible file surface:

    files(C(F)) ∪ repo-internal imports(files(C(F))) ∪ task test files

Non-circular by construction: the target script is NEVER seeded by name; it
enters the surface only if the trace/call-graph actually reaches it — which is
the pre-registered `closure_precision` diagnostic, not an assumption.

Stdlib-only.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

K_HOPS = 2  # frozen (prereg §2b)

# Traceback frame patterns over pytest output (long AND short tb styles).
_TB_LONG_RE = re.compile(r'File "([^"]+\.py)", line \d+, in (\S+)')
_TB_SHORT_RE = re.compile(r"^([^\s:]+\.py):\d+:\s+in\s+(\S+)", re.MULTILINE)
_FILE_ONLY_RE = re.compile(r"^([^\s:]+\.py):\d+:", re.MULTILINE)


def _rel(path: str, ws: Path) -> str | None:
    """Workspace-relative form of a trace path, or None when outside ws."""
    p = Path(path)
    if not p.is_absolute():
        candidate = (ws / p)
        return str(p) if candidate.exists() else None
    try:
        return str(p.resolve().relative_to(ws.resolve()))
    except ValueError:
        return None  # interpreter/site-packages frame — not repo surface


class Index:
    """AST index over a workspace: defs, name-resolved call edges, imports."""

    def __init__(self) -> None:
        # node id = (relpath, def_name); def_name is the top-level def/class
        self.defs_by_file: dict[str, set[str]] = {}
        self.files_by_name: dict[str, set[str]] = {}   # simple name -> files
        self.calls: dict[tuple[str, str], set[str]] = {}  # node -> called names
        self.imports: dict[str, set[str]] = {}  # relpath -> repo relpaths
        self.py_files: list[str] = []


def _module_to_relpath(mod: str, py_files: set[str]) -> str | None:
    """Repo-internal import resolution: 'scripts.aios_x'/'aios_x' -> file."""
    tail = mod.replace(".", "/")
    for cand in (f"{tail}.py", f"{tail}/__init__.py"):
        if cand in py_files:
            return cand
    base = mod.rsplit(".", 1)[-1]
    hits = [f for f in py_files if Path(f).stem == base]
    return hits[0] if len(hits) == 1 else None


def _called_names(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def build_index(ws: Path | str) -> Index:
    ws = Path(ws)
    ix = Index()
    files = sorted(str(p.relative_to(ws)) for p in ws.rglob("*.py")
                   if p.is_file())
    ix.py_files = files
    fileset = set(files)
    for rel in files:
        try:
            tree = ast.parse((ws / rel).read_text(encoding="utf-8",
                                                  errors="replace"))
        except SyntaxError:
            ix.defs_by_file[rel] = set()
            continue
        defs: set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                defs.add(node.name)
                ix.files_by_name.setdefault(node.name, set()).add(rel)
                ix.calls[(rel, node.name)] = _called_names(node)
        # module-level driver code also calls things
        top_calls = _called_names(ast.Module(
            body=[n for n in tree.body
                  if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef))], type_ignores=[]))
        if top_calls:
            ix.calls[(rel, "<module>")] = top_calls
            defs.add("<module>")
        ix.defs_by_file[rel] = defs
        imps: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    hit = _module_to_relpath(a.name, fileset)
                    if hit:
                        imps.add(hit)
            elif isinstance(node, ast.ImportFrom) and node.module:
                hit = _module_to_relpath(node.module, fileset)
                if hit:
                    imps.add(hit)
        ix.imports[rel] = imps
    return ix


def trace_frames(oracle_output: str, ws: Path | str) -> list[tuple[str, str]]:
    """Frame set F from the failing test's output: (relpath, func) pairs,
    de-duplicated, order preserved. Frames outside the workspace are dropped.
    File-only references (assertion lines) yield (relpath, '')."""
    ws = Path(ws)
    seen: set[tuple[str, str]] = set()
    frames: list[tuple[str, str]] = []

    def add(path: str, fn: str) -> None:
        rel = _rel(path, ws)
        if rel is None:
            return
        key = (rel, fn)
        if key not in seen:
            seen.add(key)
            frames.append(key)

    for m in _TB_LONG_RE.finditer(oracle_output):
        add(m.group(1), m.group(2))
    for m in _TB_SHORT_RE.finditer(oracle_output):
        add(m.group(1), m.group(2))
    for m in _FILE_ONLY_RE.finditer(oracle_output):
        add(m.group(1), "")
    return frames


def closure_nodes(ix: Index, frames: list[tuple[str, str]],
                  test_paths: list[str], k: int = K_HOPS) -> set[tuple[str, str]]:
    """k-hop UNDIRECTED closure over the call graph from the seed frames.
    Fallback (Errata op-2): no resolvable frames -> the test files' own defs.
    The target script is never seeded by name."""
    seeds: set[tuple[str, str]] = set()
    for rel, fn in frames:
        if rel not in ix.defs_by_file:
            continue
        if fn and fn in ix.defs_by_file[rel]:
            seeds.add((rel, fn))
        else:
            seeds.update((rel, d) for d in ix.defs_by_file[rel])
    if not seeds:
        for tp in test_paths:
            seeds.update((tp, d) for d in ix.defs_by_file.get(tp, set()))

    # reverse edge map: called simple name -> caller nodes
    callers_of: dict[str, set[tuple[str, str]]] = {}
    for node, names in ix.calls.items():
        for nm in names:
            callers_of.setdefault(nm, set()).add(node)

    frontier, cover = set(seeds), set(seeds)
    for _ in range(k):
        nxt: set[tuple[str, str]] = set()
        for node in frontier:
            # forward: defs matching names this node calls
            for nm in ix.calls.get(node, ()):
                for f in ix.files_by_name.get(nm, ()):
                    nxt.add((f, nm))
            # backward: nodes that call this node's name
            nxt.update(callers_of.get(node[1], ()))
        nxt -= cover
        if not nxt:
            break
        cover |= nxt
        frontier = nxt
    return cover


def visible_files(ix: Index, cover: set[tuple[str, str]],
                  test_paths: list[str]) -> list[str]:
    """Treatment surface: files of the closure ∪ their repo-internal imports
    ∪ the task's test files (Errata op-2)."""
    files = {rel for rel, _ in cover}
    for rel in list(files):
        files |= ix.imports.get(rel, set())
    files |= {tp for tp in test_paths if tp in ix.defs_by_file}
    return sorted(files)


def compute_surface(ws: Path | str, oracle_output: str,
                    test_paths: list[str], script_path: str) -> dict:
    """One-call summary used by the episode runner + run-validity metrics."""
    ws = Path(ws)
    ix = build_index(ws)
    frames = trace_frames(oracle_output, ws)
    cover = closure_nodes(ix, frames, test_paths)
    files = visible_files(ix, cover, test_paths)
    return {
        "index": ix, "frames": frames, "nodes": sorted(cover),
        "files": files,
        "n_files": len(files), "n_repo_py_files": len(ix.py_files),
        "differs_from_whole_repo": len(files) < len(ix.py_files),
        "target_in_closure": script_path in files,
    }
