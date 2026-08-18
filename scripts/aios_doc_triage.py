#!/usr/bin/env python3
"""aios.doc.triage.v1 — sort documents by what the repo can prove about them.

Founder: too many docs left as sprawling unprocessed TODOs. Separate what was BUILT over
six months, what still must be BUILT, what already exists as a product or OSS we should
just use, and what is pure LEGACY.

Three of those four are decidable from evidence and one is not:

  BUILT      the artifacts this doc names exist on disk, and it is cited by later work
  TODO       it declares intent (사전등록/계획/예정/TODO/다음) whose named artifacts are absent
  LEGACY     nothing cites it, it cites nothing that still exists, and it is stale
  ADOPT      "this already exists as a product/OSS" is an EXTERNAL fact. The graph cannot
             decide it, so it is never inferred — it is only reported as a candidate when
             a doc is TODO and names no artifact at all, i.e. it is a wish, not a design.

A triage that guesses ADOPT from internal data would be inventing external knowledge,
which is the failure this repo has been correcting all day.
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, sys, time
from collections import Counter
from pathlib import Path

WS = Path("/home/user/workspaces/jaewon")
DB = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"

INTENT = re.compile(r"(?im)^\s*(?:[-*]\s*\[ \]|TODO|FIXME|다음 단계|다음:|계획|예정|"
                    r"해야|지어야|만들어야|사전등록|prereg|will build|next step)")
DONE = re.compile(r"(?im)(?:^\s*[-*]\s*\[x\]|완료|통과|PASS|측정했다|실행했다|커밋|점등)")
SUPERSEDED = re.compile(r"(?im)(supersede[sd]?|철회|폐기|무효|NO-GO|kill rule.{0,20}발동|"
                        r"stale|deprecated)")
PATH_RE = re.compile(r"(?<![A-Za-z0-9_.\-])[./]?[A-Za-z0-9_][A-Za-z0-9_./\-]{2,120}"
                     r"\.(?:md|py|sh|jsonl|json|toml|ya?ml)\b")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", default="docs")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", metavar="PATH")
    a = ap.parse_args()
    con = sqlite3.connect(DB)

    ids = [r for (r,) in con.execute(
        "select id from nodes where layer=? and kind in ('doc','spec','contract','experiment')",
        (a.layer,))]
    inbound = Counter(d for (d,) in con.execute("select dst from edges"))
    known = {r for (r,) in con.execute("select id from nodes")}
    # index once. The first version scanned all 113k node ids per reference, which is
    # quadratic and never returned.
    by_base: dict[str, int] = {}
    by_tail: set[str] = set()
    for k in known:
        by_base[Path(k).name] = by_base.get(Path(k).name, 0) + 1
        parts = k.split("/")
        for i in range(len(parts)):
            by_tail.add("/".join(parts[i:]))
    mt = {r: m for r, m in con.execute("select id, mtime from nodes")}
    now = time.time()

    rows = []
    for rel in ids:
        p = WS / rel
        if not p.exists() or "/_history/" in rel or "/_legacy/" in rel:
            continue
        try:
            txt = p.read_text(errors="replace")
        except OSError:
            continue
        refs = {m.group(0) for m in PATH_RE.finditer(txt)}
        refs = {r for r in refs if "/" in r}
        # a named artifact "exists" if the graph holds it under any repo prefix
        def exists(r: str) -> bool:
            r = r.lstrip("./")
            return r in by_tail or Path(r).name in by_base
        present = sum(1 for r in refs if exists(r))
        missing = len(refs) - present
        intent = len(INTENT.findall(txt))
        done = len(DONE.findall(txt))
        cited = inbound.get(rel, 0)
        idle = int((now - mt.get(rel, now)) / 86400)
        superseded = bool(SUPERSEDED.search(txt[:3000]))

        if cited == 0 and present == 0 and idle > 45:
            cls = "LEGACY"
        elif intent > 0 and present == 0 and len(refs) == 0:
            cls = "ADOPT?"                       # a wish naming nothing — check the world first
        elif intent > done and missing >= present:
            cls = "TODO"
        elif present > 0 and (done >= intent or cited > 0):
            cls = "BUILT"
        else:
            cls = "TODO"
        rows.append(dict(path=rel, cls=cls, refs=len(refs), present=present,
                         missing=missing, intent=intent, done=done, cited=cited,
                         idle=idle, superseded=superseded,
                         size=p.stat().st_size))

    by = Counter(r["cls"] for r in rows)
    print(f"{a.layer}: {len(rows)}개 문서\n")
    for c in ("BUILT", "TODO", "LEGACY", "ADOPT?"):
        print(f"  {c:<8}{by.get(c,0):>5}")
    print(f"\n초안/중복 신호: superseded 표기 {sum(r['superseded'] for r in rows)}")

    print(f"\n── TODO 중 가장 큰 것 (장황하게 남은 것) ──")
    todos = sorted([r for r in rows if r["cls"] == "TODO"],
                   key=lambda r: -r["intent"])[:a.limit or 14]
    print(f"{'intent':>7}{'done':>6}{'cited':>6}{'idle':>6}  path")
    for r in todos:
        print(f"{r['intent']:>7}{r['done']:>6}{r['cited']:>6}{r['idle']:>5}d  {r['path'][8:]}")

    print(f"\n── LEGACY 후보 ──")
    for r in sorted([r for r in rows if r["cls"] == "LEGACY"], key=lambda r: -r["idle"])[:12]:
        print(f"  {r['idle']:>4}d  {r['path'][8:]}")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
