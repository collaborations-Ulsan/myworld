#!/usr/bin/env python3
"""Phase 5 task-workspace materialization (prereg §2).

FROZEN PROTOCOL: docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md.

Materializes one task workspace from the repo's git history:

  * the repo tree AT the task commit (``git archive`` — .git is never present,
    the commit message is never present),
  * the single target ``scripts/*.py`` REVERTED to its parent state
    (removed entirely when the commit ADDED the file),
  * the post-commit ``tests/test_*.py`` file(s) KEPT verbatim.

Invariants asserted after materialization (fail loudly, never silently):
  1. no ``.git`` anywhere in the workspace;
  2. the target script's content equals its PARENT-commit content
     (or the file is absent when the parent had no such file);
  3. the target script's content does NOT equal the post-commit content
     (the agent must not see the solution);
  4. every task test file exists and equals its POST-commit content.

Also provides the tests/ tamper snapshot used by the prereg §6.1 guard.

Stdlib-only. No file in scripts/ is modified by this module — it only READS
git objects and writes into a temp workspace.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class WorkspaceInvariantError(AssertionError):
    """A materialized workspace violated a prereg invariant."""


def _git(repo_root: Path, *args: str, timeout: float = 60.0) -> bytes:
    r = subprocess.run(["git", "-C", str(repo_root), *args],
                       capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args[:3])}... failed rc={r.returncode}: "
            f"{r.stderr.decode('utf-8', 'replace')[-300:]}")
    return r.stdout


def git_show(repo_root: Path, commit: str, path: str) -> bytes | None:
    """Bytes of ``path`` at ``commit``, or None when absent at that commit."""
    r = subprocess.run(["git", "-C", str(repo_root), "show", f"{commit}:{path}"],
                       capture_output=True, timeout=60)
    return r.stdout if r.returncode == 0 else None


def materialize(repo_root: Path | str, commit: str, parent_commit: str,
                script_path: str, test_paths: list[str],
                dest: Path | str | None = None) -> Path:
    """Materialize the task workspace; return its root. See module docstring."""
    repo_root = Path(repo_root)
    ws = Path(dest) if dest else Path(tempfile.mkdtemp(prefix="phase5-ws-"))
    ws.mkdir(parents=True, exist_ok=True)

    # Repo tree at the task commit. `git archive` contains ONLY tracked tree
    # content — no .git, no commit message, no reflog.
    tar_bytes = _git(repo_root, "archive", "--format=tar", commit,
                     timeout=120.0)
    with tarfile.open(fileobj=BytesIO(tar_bytes)) as tf:
        tf.extractall(ws, filter="data")  # our own repo's tracked tree

    # Revert the single target script to its parent state.
    parent_src = git_show(repo_root, parent_commit, script_path)
    target = ws / script_path
    if parent_src is None:
        # The commit ADDED the file: parent state == absent.
        if target.exists():
            target.unlink()
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(parent_src)

    assert_invariants(ws, repo_root, commit, parent_commit,
                      script_path, test_paths)
    return ws


def assert_invariants(ws: Path, repo_root: Path, commit: str,
                      parent_commit: str, script_path: str,
                      test_paths: list[str]) -> None:
    """Raise WorkspaceInvariantError on any prereg-invariant violation."""
    ws = Path(ws)
    if any(p.name == ".git" for p in ws.rglob(".git")):
        raise WorkspaceInvariantError(f"{ws}: .git present in workspace")

    post_src = git_show(repo_root, commit, script_path)
    if post_src is None:
        raise WorkspaceInvariantError(
            f"{script_path} absent at task commit {commit[:12]}")
    parent_src = git_show(repo_root, parent_commit, script_path)
    target = ws / script_path
    if parent_src is None:
        if target.exists():
            raise WorkspaceInvariantError(
                f"{script_path}: parent state is ABSENT but file exists")
    else:
        if not target.exists() or target.read_bytes() != parent_src:
            raise WorkspaceInvariantError(
                f"{script_path}: workspace content != parent-commit content")
        if target.read_bytes() == post_src:
            raise WorkspaceInvariantError(
                f"{script_path}: workspace content EQUALS post-commit "
                f"content — the agent would see the solution")

    for tp in test_paths:
        want = git_show(repo_root, commit, tp)
        if want is None:
            raise WorkspaceInvariantError(
                f"{tp} absent at task commit {commit[:12]}")
        have = ws / tp
        if not have.exists() or have.read_bytes() != want:
            raise WorkspaceInvariantError(
                f"{tp}: workspace test file != post-commit test file")


def restore_solution(ws: Path | str, repo_root: Path | str, commit: str,
                     script_path: str) -> None:
    """Write the POST-commit script into the workspace (pre-flight (b) only —
    never called on a workspace an agent will see)."""
    post_src = git_show(Path(repo_root), commit, script_path)
    if post_src is None:
        raise RuntimeError(f"{script_path} absent at {commit[:12]}")
    target = Path(ws) / script_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(post_src)


def tests_snapshot(ws: Path | str) -> dict[str, str]:
    """sha256 of every file under tests/ — the §6.1 tamper baseline."""
    ws = Path(ws)
    out: dict[str, str] = {}
    tests_dir = ws / "tests"
    if not tests_dir.is_dir():
        return out
    for p in sorted(tests_dir.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(ws))] = hashlib.sha256(
                p.read_bytes()).hexdigest()
    return out


def tests_tampered(ws: Path | str, snapshot: dict[str, str]) -> list[str]:
    """Paths under tests/ whose content changed/appeared/vanished vs snapshot.
    Non-empty => the attempt is scored FAIL (prereg §6.1)."""
    current = tests_snapshot(ws)
    changed = [p for p in current if snapshot.get(p) != current[p]]
    missing = [p for p in snapshot if p not in current]
    return sorted(set(changed) | set(missing))


def cleanup(ws: Path | str) -> None:
    shutil.rmtree(ws, ignore_errors=True)
