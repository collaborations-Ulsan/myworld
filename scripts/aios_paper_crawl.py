#!/usr/bin/env python3
"""aios.paper.crawl.v1 — hop-expand a citation graph from seed papers.

Mirrors the robot-side method on /data/jaewon/robotics (papers table with s2_id + hop,
edges of kind 'cites', a failures table). Seeds go in at hop 0; each hop pulls references
AND citations from Semantic Scholar and lands them at hop+1.

Lands in the SAME database as the artifact graph (/data/jaewon/aios/index/aios.db) rather
than a separate file, so external literature and our own artifacts are one graph. That is
the point: a paper is only useful here when something of ours can cite it.
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

DB = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"
# Semantic Scholar without a key returns 429 immediately (measured 2026-08-18, twice,
# on both a fresh and a decade-old paper). OpenAlex is keyless, asks only for a mailto,
# and exposes referenced_works + cited_by directly.
OA = "https://api.openalex.org"
MAILTO = os.environ.get("OPENALEX_MAILTO", "cjw070690@gmail.com")
UA = {"User-Agent": f"aios-graph/1.0 (mailto:{MAILTO})"}


def get(url: str, tries: int = 4, timeout: int = 45) -> dict:
    """Always reports WHY. The first version collapsed every failure into
    'retries exhausted', which hid a plain HTTP 429 and cost a whole run to diagnose —
    a substrate that was rate-limited looked identical to one that was unreachable."""
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}mailto={MAILTO}"
    last = "no attempt"
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (429, 503):
                time.sleep(5 * (i + 1)); continue
            return {"__error__": last}
        except Exception as e:
            last = f"{type(e).__name__}: {e}"[:120]
            time.sleep(2 * (i + 1))
    return {"__error__": f"after {tries} tries: {last}"}


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript("""
      create table if not exists papers(
        id text primary key, s2_id text, arxiv_id text, title text, abstract text,
        year int, venue text, authors text, citation_count int, hop int, fetched_at int);
      create index if not exists idx_p_hop on papers(hop);
      create table if not exists failures(id text, reason text, at int);
    """)


def store(con, p: dict, hop: int) -> str | None:
    sid = (p.get("id") or "").rsplit("/", 1)[-1]        # OpenAlex work id, e.g. W2741809807
    if not sid:
        return None
    doi = (p.get("doi") or "")
    m = re.search(r"arxiv\.(\d{4}\.\d{4,5})", doi, re.I)
    arx = m.group(1) if m else None
    nid = f"paper:{arx or sid}"
    prev = con.execute("select hop from papers where id = ?", (nid,)).fetchone()
    if prev and prev[0] <= hop:
        return nid                                  # keep the shortest hop distance
    con.execute("insert or replace into papers values (?,?,?,?,?,?,?,?,?,?,?)",
                (nid, sid, arx, (p.get("title") or "")[:500],
                 (p.get("abstract") or "")[:8000], p.get("year"), (p.get("venue") or "")[:200],
                 json.dumps([(a.get("author") or {}).get("display_name")
                             for a in (p.get("authorships") or [])][:12], ensure_ascii=False),
                 p.get("cited_by_count"), hop, int(time.time())))
    con.execute("insert or replace into nodes values (?,?,?,?,?,?)",
                (nid, "paper", "literature", len(p.get("abstract") or ""),
                 int(time.time()), (p.get("title") or "")[:200]))
    return nid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", nargs="+", required=True, help="arXiv ids, e.g. 2604.17148")
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--per-node", type=int, default=40, help="refs/cites pulled per paper")
    ap.add_argument("--budget", type=int, default=400, help="max papers expanded")
    ap.add_argument("--delay", type=float, default=1.2, help="courtesy delay between calls")
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    ensure_schema(con)
    frontier, expanded, added = [], 0, 0

    for s in a.seed:
        ident = (f"{OA}/works/doi:10.48550/arXiv.{s}" if re.match(r"^\d{4}\.\d{4,5}$", s)
                 else f"{OA}/works/doi:{s}" if s.startswith("10.")
                 else f"{OA}/works/{s}")
        d = get(ident)
        if not d or "__error__" in (d or {}):
            con.execute("insert into failures values (?,?,?)",
                        (f"seed:{s}", (d or {}).get("__error__", "no data"), int(time.time())))
            print(f"seed {s}: FAILED — {(d or {}).get('__error__')}", file=sys.stderr)
            continue
        nid = store(con, d, 0)
        frontier.append((nid, (d.get("id") or "").rsplit("/", 1)[-1], 0))
        print(f"seed hop0  {d.get('title','')[:80]}")
    con.commit()
    if not frontier:
        print("no seed resolved — nothing to expand", file=sys.stderr)
        return 2

    while frontier and expanded < a.budget:
        nid, sid, hop = frontier.pop(0)
        if hop >= a.hops:
            continue
        work = get(f"{OA}/works/{sid}")
        if "__error__" in work:
            con.execute("insert into failures values (?,?,?)",
                        (nid, f"work: {work['__error__']}", int(time.time())))
            expanded += 1
            continue

        # references: the work carries them as ids; fetch in batches of 40 (OpenAlex OR filter)
        refs = [w.rsplit("/", 1)[-1] for w in (work.get("referenced_works") or [])][:a.per_node]
        for i in range(0, len(refs), 40):
            batch = "|".join(refs[i:i + 40])
            d = get(f"{OA}/works?filter=openalex_id:{batch}&per-page=40")
            time.sleep(a.delay)
            if "__error__" in d:
                con.execute("insert into failures values (?,?,?)",
                            (nid, f"refs: {d['__error__']}", int(time.time())))
                continue
            for w in d.get("results", []):
                child = store(con, w, hop + 1)
                if child:
                    added += 1
                    con.execute("insert into edges values (?,?,?)", (nid, child, "cites"))
                    if hop + 1 < a.hops:
                        frontier.append((child, (w.get("id") or "").rsplit("/", 1)[-1], hop + 1))

        # citations: who cites this work
        d = get(f"{OA}/works?filter=cites:{sid}&per-page={min(a.per_node, 50)}")
        time.sleep(a.delay)
        if "__error__" in d:
            con.execute("insert into failures values (?,?,?)",
                        (nid, f"cites: {d['__error__']}", int(time.time())))
        else:
            for w in d.get("results", []):
                child = store(con, w, hop + 1)
                if child:
                    added += 1
                    con.execute("insert into edges values (?,?,?)", (child, nid, "cites"))
                    if hop + 1 < a.hops:
                        frontier.append((child, (w.get("id") or "").rsplit("/", 1)[-1], hop + 1))

        expanded += 1
        con.commit()
        if expanded % 10 == 0:
            n = con.execute("select count(*) from papers").fetchone()[0]
            print(f"  expanded {expanded} | papers {n} | frontier {len(frontier)}", flush=True)

    con.commit()
    print("\nhop 분포:", dict(con.execute(
        "select hop, count(*) from papers group by hop").fetchall()))
    print("failures:", con.execute(
        "select count(*) from failures where reason not like 'dangling%'").fetchone()[0])
    print("\n최다 피인용 (hop<=2):")
    for t, c, h in con.execute(
            "select title, citation_count, hop from papers where hop<=2 "
            "order by citation_count desc limit 12"):
        print(f"  {c:>7}  h{h}  {t[:88]}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
