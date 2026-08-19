#!/usr/bin/env python3
"""aios.legacy.triage.v1 — what is dead weight, with evidence, and never by one signal.

Founder: clean up what turned out to be useless legacy. The knowledge graph makes that a
query instead of a vibe, but ORPHAN ALONE IS NOT A VERDICT: an entry point nobody imports
is orphaned in the graph and is exactly what you must not delete. So every candidate is
judged on four independent signals and only a conjunction convicts.

    graph      nothing cites it and it cites nothing
    git        not touched in N days
    harness    not named in CLAUDE.md / AGENTS.md / .claude/**  (an entry point IS named)
    tests      no test file references it

Output is a proposal, never a deletion. Archive (git mv) is the action, because git keeps
history and the founder can reverse it; rm is not offered.
"""
from __future__ import annotations
import argparse, functools, json, os, re, sqlite3, subprocess, sys, time
from pathlib import Path

WS = Path("/home/user/workspaces/jaewon")
DB = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"
HARNESS_GLOBS = ["CLAUDE.md", "AGENTS.md", ".claude/**/*.md", ".claude/**/*.json",
                 "README.md", "docs/AIOS_OPERATOR_PLAYBOOK.md"]


def harness_text(repo: Path) -> str:
    out = []
    for g in HARNESS_GLOBS:
        for p in repo.glob(g):
            if p.is_file():
                try:
                    out.append(p.read_text(errors="replace"))
                except OSError:
                    pass
    return "\n".join(out)


@functools.lru_cache(maxsize=64)
def is_vendored(repo_dir: str) -> bool:
    """A clone of someone else's repo holds THEIR code, not our legacy. Triaging it would
    propose archiving upstream files (measured: 8 google-gemini scripts surfaced as ours)."""
    try:
        url = subprocess.run(["git", "-C", repo_dir, "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return False
    return bool(url) and not any(o in url for o in ("cjw0076", "dipeen", "jaewon"))


def owning_repo(rel: str) -> Path | None:
    d = (WS / rel).parent
    while d != WS.parent:
        if (d / ".git").exists():
            return d
        d = d.parent
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", default=None, help="restrict to one organ")
    ap.add_argument("--stale-days", type=int, default=120)
    ap.add_argument("--kinds", nargs="*", default=["code", "doc", "spec"])
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--emit-archive-script", metavar="PATH",
                    help="write a reviewable `git mv` script; it is NOT run here")
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    q = "select id, kind, layer, mtime from nodes where kind in (%s)" % (
        ",".join("?" * len(a.kinds)))
    params = list(a.kinds)
    if a.layer:
        q += " and layer = ?"
        params.append(a.layer)
    nodes = list(con.execute(q, params))

    linked_out = {r for (r,) in con.execute("select distinct src from edges")}
    linked_in = {r for (r,) in con.execute("select distinct dst from edges")}

    hay = harness_text(WS / "myworld")
    now = time.time()
    cutoff = a.stale_days * 86400

    cands = []
    # Execution records are NOT legacy. The append-only invariant protects them, and the
    # first run of this tool proposed archiving 574 of them because .md under .runs/ looks
    # like a document. A tool that offers to delete the audit trail is worse than no tool.
    RECORD_DIRS = ("/.runs/", "/runs/", "/outbox/", "/inbox/", "/packets/", "/drafts/",
                   "/_history/", "/_legacy/", "/sessions/", "/receipts/", "/.aios/",
                   "/gpt_sessions/", "/g5_arcs/", "/logs/")
    for rel, kind, layer, mtime in nodes:
        if "/.git/" in rel or any(d in f"/{rel}" for d in RECORD_DIRS):
            continue
        if Path(rel).name in ("__init__.py", "conftest.py", "setup.py", "__main__.py"):
            continue                              # package machinery is used by import, not citation
        own = owning_repo(rel)
        if own is not None and is_vendored(str(own)):
            continue                              # third-party clone: their code, not our legacy
        # A fifth signal, added after this tool broke memoryOS. Its four graph/git/harness/
        # test signals all agreed that memoryos/local_workers.py was legacy, because a
        # Python import is not a path-shaped reference and the graph could not see it.
        # Archiving it stopped memoryOS's CLI from importing. Grep is the cheap backstop:
        # never archive a module some source still imports by name.
        if rel.endswith(".py"):
            stem = Path(rel).stem
            try:
                hit = subprocess.run(
                    ["grep", "-rlE", rf"(from|import)\s+\.*[\w\.]*\b{stem}\b",
                     "--include=*.py", str(own or WS)],
                    capture_output=True, text=True, timeout=60).stdout.strip().splitlines()
            except Exception:
                hit = ["<grep failed — refusing to archive on an unchecked import>"]
            if [h for h in hit if h and not h.endswith(rel)]:
                continue
        name = Path(rel).name
        stem = Path(rel).stem
        sig = {
            "graph_orphan": rel not in linked_in and rel not in linked_out,
            "git_stale": (now - mtime) > cutoff,
            "harness_silent": name not in hay and stem not in hay,
        }
        if not all(sig.values()):
            continue
        # tests: does anything under a tests/ dir mention the stem?
        hits = con.execute(
            "select count(*) from fulltext where id like '%/tests/%' and text like ?",
            (f"%{stem}%",)).fetchone()[0]
        sig["untested"] = hits == 0
        if not sig["untested"]:
            continue
        cands.append({"path": rel, "kind": kind, "layer": layer,
                      "days_idle": int((now - mtime) / 86400), "signals": sig})

    cands.sort(key=lambda c: -c["days_idle"])
    print(f"legacy candidates: {len(cands)}  "
          f"(all four signals agree; orphan alone was not enough)\n")
    print(f"{'idle':>6}  {'layer':<14}{'kind':<7}path")
    for c in cands[:a.limit]:
        print(f"{c['days_idle']:>5}d  {c['layer']:<14}{c['kind']:<7}{c['path']}")
    if len(cands) > a.limit:
        print(f"... and {len(cands)-a.limit} more")

    by_layer: dict[str, int] = {}
    for c in cands:
        by_layer[c["layer"]] = by_layer.get(c["layer"], 0) + 1
    print("\nby organ:", dict(sorted(by_layer.items(), key=lambda kv: -kv[1])))

    if a.emit_archive_script:
        lines = ["#!/bin/sh",
                 "# PROPOSAL — review before running. git mv keeps history; nothing is rm'd.",
                 "set -eu", ""]
        # The owning repo is the NEAREST .git above the file, not the first path segment.
        # myworld gitignores uri/ and the vendored clones and holds memoryOS as a gitlink,
        # so `git -C myworld mv` would have silently SKIPped almost every candidate.
        def owner(rel: str) -> Path | None:
            d = (WS / rel).parent
            while d != WS.parent:
                if (d / ".git").exists():
                    return d
                d = d.parent
            return None
        for c in cands:
            abs_p = WS / c["path"]
            own = owner(c["path"])
            if own is None:
                lines.append(f"# untracked, no repo: {c['path']}")
                continue
            inner = str(abs_p.relative_to(own))
            lines.append(f"mkdir -p '{own}/_legacy/{Path(inner).parent}'")
            lines.append(f"git -C '{own}' mv '{inner}' '_legacy/{inner}' "
                         f"|| mv '{abs_p}' '{own}/_legacy/{inner}'")
        Path(a.emit_archive_script).write_text("\n".join(lines) + "\n")
        os.chmod(a.emit_archive_script, 0o755)
        print(f"\nwrote proposal script: {a.emit_archive_script}  (NOT executed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
