#!/usr/bin/env python3
"""aios.return.v1 — results come back, and artifacts enter the graph by themselves.

Measured today: 4,873 lines of code against 14,313 lines of prose. An engineering problem
answered with three times more writing than building. This file is the correction, and it
targets the two things that actually block the goal — neither of which is a DNA invariant.

  1. Results never returned. A worker closed a task and the user had to go ask.
  2. Artifacts never entered the graph, so knowing where a thing lives stayed a human job.

Both are code, so both get code. No new invariant, no new doc section.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_factory as fac                                     # noqa: E402

GRAPH = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"
SEEN = ROOT / ".aios" / "returned.jsonl"


def _seen() -> set[str]:
    if not SEEN.exists():
        return set()
    out = set()
    for line in SEEN.read_text().splitlines():
        try:
            out.add(json.loads(line)["task_id"])
        except Exception:
            pass
    return out


def ingest(task: dict) -> bool:
    """Put the artifact in the graph so location stops being something anyone must know."""
    art = task.get("artifact")
    if not art or not Path(art).exists() or not GRAPH.exists():
        return False
    p = Path(art)
    try:
        con = sqlite3.connect(GRAPH, timeout=10)
        nid = f"artifact:{p.name}"
        text = ""
        try:
            text = p.read_text(errors="replace")[:200_000]
        except OSError:
            pass
        con.execute("insert or replace into nodes values (?,?,?,?,?,?)",
                    (nid, "artifact", "produced", p.stat().st_size,
                     int(p.stat().st_mtime), task["goal"][:200]))
        if text:
            con.execute("insert or replace into fulltext values (?,?,?)",
                        (nid, text, len(text)))
        # edge to the capability's owner so `who_knows` can reach it later
        con.execute("insert into edges values (?,?,?)",
                    (f"capability:{task['capability']}", nid, "produces"))
        for dep in task.get("deps") or []:
            d = fac.state().get(dep) or {}
            if d.get("artifact"):
                con.execute("insert into edges values (?,?,?)",
                            (f"artifact:{Path(d['artifact']).name}", nid, "feeds"))
        con.commit(); con.close()
        return True
    except Exception:
        return False


def sweep(quiet: bool = False) -> list[dict]:
    """Everything finished since last time. This is what a single session should be told
    without having to ask — the whole point of instructing from one place."""
    seen = _seen()
    fresh = [t for t in fac.state().values()
             if t["state"] in ("done", "failed") and t["task_id"] not in seen]
    fresh.sort(key=lambda t: t["progress_at"])
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    with SEEN.open("a") as fh:
        for t in fresh:
            ok = ingest(t)
            fh.write(json.dumps({"task_id": t["task_id"], "ts": time.time(),
                                 "ingested": ok}, ensure_ascii=False) + "\n")
            lines.append({**t, "ingested": ok})
    if not quiet:
        if not fresh:
            print("새로 끝난 것 없음.")
        for t in lines:
            mark = "OK " if t["state"] == "done" else "FAIL"
            g = "→graph" if t["ingested"] else "      "
            print(f"  {mark} {g} {t['capability']:<26}{t['goal'][:44]}")
            if t["state"] == "failed" and t.get("result"):
                print(f"            {str(t['result'])[:90]}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    sweep(quiet=a.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
