#!/usr/bin/env python3
"""Phase 5 task construction from this repo's git history (prereg §2).

FROZEN PROTOCOL: docs/AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md.

Candidate = a non-merge commit that
  * touches (A or M) exactly ONE ``scripts/*.py``, and
  * ships/updates (A or M) at least one ``tests/test_*.py``, and
  * every such test file still exists in the current repo.
This filter reproduces the prereg feasibility measurement exactly
(51 candidates in the last 400 commits, measured 2026-07-26).

Pre-flight (each candidate, in a real materialized workspace):
  (a) with the script REVERTED to its parent state the oracle must FAIL
      — otherwise the task is already solved: no signal → DROP;
  (b) with the POST-commit script restored the oracle must PASS
      (rc == 0 AND ≥1 test actually passed — an all-skip run is not a pass)
      — otherwise the task is unsolvable/flaky in this harness → DROP.
Dropped candidates are recorded with reasons in the output JSON.

Oracle command is frozen at construction time and sha256-hashed into the task
record (prereg §6.5). Output: experiments/phase5/tasks.json, chronological.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import workspace as ws_mod  # noqa: E402
from runner import run_oracle  # noqa: E402

REPO_ROOT = HERE.parents[1]
SCHEMA = "aios.phase5.tasks.v1"
SCRIPT_RE = re.compile(r"^scripts/[^/]+\.py$")
TEST_RE = re.compile(r"^tests/test_[^/]+\.py$")


def _git_lines(repo_root: Path, *args: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(repo_root), *args],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {r.stderr[-300:]}")
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def mine_candidates(repo_root: Path, max_commits: int) -> list[dict]:
    """Commits matching the prereg §2 filter, newest-first as mined."""
    out: list[dict] = []
    for line in _git_lines(repo_root, "log", f"-{max_commits}", "--no-merges",
                           "--format=%H %ct"):
        sha, ct = line.split()
        scripts: list[str] = []
        tests: list[str] = []
        for ns in _git_lines(repo_root, "diff-tree", "-r", "--no-commit-id",
                             "--name-status", sha):
            parts = ns.split("\t")
            if len(parts) < 2:
                continue
            status, path = parts[0], parts[-1]
            if status not in ("A", "M"):
                continue
            if SCRIPT_RE.match(path):
                scripts.append(path)
            elif TEST_RE.match(path):
                tests.append(path)
        if len(scripts) == 1 and tests:
            out.append({"commit": sha, "ts_epoch": int(ct),
                        "script_path": scripts[0],
                        "test_paths": sorted(tests)})
    return out


def preflight(repo_root: Path, cand: dict,
              oracle_timeout: float) -> tuple[dict | None, dict | None]:
    """(task_record, None) when the candidate survives, (None, drop) when not."""
    sha = cand["commit"]

    def drop(reason: str, detail: str = "") -> tuple[None, dict]:
        return None, {"commit": sha, "script_path": cand["script_path"],
                      "reason": reason, "detail": detail}

    missing = [tp for tp in cand["test_paths"]
               if not (repo_root / tp).exists()]
    if missing:
        return drop("test_file_gone_at_head", ",".join(missing))

    try:
        parent = _git_lines(repo_root, "rev-parse", f"{sha}^")[0]
    except (RuntimeError, IndexError):
        return drop("root_commit_no_parent")

    oracle_cmd = [sys.executable, "-m", "pytest", "-q",
                  "-p", "no:cacheprovider", *cand["test_paths"]]
    ws = None
    try:
        ws = ws_mod.materialize(repo_root, sha, parent,
                                cand["script_path"], cand["test_paths"])
    except (ws_mod.WorkspaceInvariantError, RuntimeError, OSError) as exc:
        if ws:
            ws_mod.cleanup(ws)
        return drop("materialize_failed", str(exc)[:200])
    try:
        # (a) reverted source -> oracle must FAIL.
        res_a = run_oracle(ws, oracle_cmd, timeout=oracle_timeout)
        if res_a["ok"]:
            return drop("already_passing_with_parent_source_no_signal",
                        f"rc={res_a['rc']} passed={res_a['passed']}")
        # (b) post-commit source restored -> oracle must PASS.
        ws_mod.restore_solution(ws, repo_root, sha, cand["script_path"])
        res_b = run_oracle(ws, oracle_cmd, timeout=oracle_timeout)
        if not res_b["ok"]:
            return drop("not_passing_with_postcommit_source_unsolvable",
                        f"rc={res_b['rc']} passed={res_b['passed']} "
                        f"timed_out={res_b['timed_out']} "
                        f"tail={res_b['tail'][-160:]}")
    finally:
        ws_mod.cleanup(ws)

    task = {
        "commit": sha,
        "parent_commit": parent,
        "script_path": cand["script_path"],
        "test_paths": cand["test_paths"],
        "oracle_cmd": oracle_cmd,
        "oracle_cmd_sha256": hashlib.sha256(
            json.dumps(oracle_cmd).encode()).hexdigest(),
        "ts": _dt.datetime.fromtimestamp(
            cand["ts_epoch"], _dt.timezone.utc).isoformat(),
        "ts_epoch": cand["ts_epoch"],
        "parent_state": ("absent" if ws_mod.git_show(
            repo_root, parent, cand["script_path"]) is None else "present"),
        "preflight": {"reverted_rc": res_a["rc"],
                      "reverted_passed": res_a["passed"],
                      "solution_passed": res_b["passed"]},
    }
    return task, None


def build(repo_root: Path, max_commits: int = 400,
          oracle_timeout: float = 180.0,
          progress: bool = False) -> dict:
    cands = mine_candidates(repo_root, max_commits)
    tasks: list[dict] = []
    dropped: list[dict] = []
    for i, cand in enumerate(cands):
        task, drop = preflight(repo_root, cand, oracle_timeout)
        if task:
            tasks.append(task)
        else:
            dropped.append(drop)
        if progress:
            print(f"[{i + 1}/{len(cands)}] {cand['commit'][:8]} "
                  f"{'KEEP' if task else 'drop:' + drop['reason']}",
                  flush=True)
    tasks.sort(key=lambda t: (t["ts_epoch"], t["commit"]))
    for i, t in enumerate(tasks):
        t["task_id"] = f"p5-{i:03d}-{t['commit'][:8]}"
    head = _git_lines(repo_root, "rev-parse", "HEAD")[0]
    return {
        "schema": SCHEMA,
        "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"),
        "repo_head": head,
        "max_commits": max_commits,
        "filter": ("non-merge; exactly one A/M scripts/*.py; >=1 A/M "
                   "tests/test_*.py; test file exists at HEAD; preflight "
                   "(a) parent-reverted oracle FAILS and (b) post-commit "
                   "oracle PASSES (rc==0 and >=1 test passed)"),
        "n_candidates": len(cands),
        "n_tasks": len(tasks),
        "n_dropped": len(dropped),
        "tasks": tasks,
        "dropped": dropped,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build Phase 5 tasks (prereg §2)")
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--max-commits", type=int, default=400)
    ap.add_argument("--oracle-timeout", type=float, default=180.0)
    ap.add_argument("--out", default=str(HERE / "tasks.json"))
    args = ap.parse_args(argv)

    t0 = time.time()
    result = build(Path(args.repo_root), args.max_commits,
                   args.oracle_timeout, progress=True)
    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({"n_candidates": result["n_candidates"],
                      "n_tasks": result["n_tasks"],
                      "n_dropped": result["n_dropped"],
                      "drop_reasons": _reason_counts(result["dropped"]),
                      "elapsed_s": round(time.time() - t0, 1),
                      "out": args.out}, indent=2))
    return 0


def _reason_counts(dropped: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in dropped:
        out[d["reason"]] = out.get(d["reason"], 0) + 1
    return out


if __name__ == "__main__":
    raise SystemExit(main())
