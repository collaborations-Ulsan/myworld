#!/usr/bin/env python3
"""aios.graph.audit.v1 — is this an organism or a pile?

The standing finding was that every brick we build is an ORPHAN. That is a claim about
edges, so this makes it a query instead of an impression. Run it after every build; the
numbers are the anti-theater guard — accumulation moves node count, organism moves
connectivity.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, sys
from collections import defaultdict, deque
from pathlib import Path

DB = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", help="restrict the audit to one organ")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--neighbors", metavar="PATH",
                    help="what cites this, and what does it cite — ask BEFORE building "
                         "something new, so a planned artifact is not born an orphan")
    ap.add_argument("--orphans-in", metavar="LAYER",
                    help="list the disconnected artifacts of one organ")
    a = ap.parse_args()
    con = sqlite3.connect(DB)

    if a.neighbors:
        q = a.neighbors
        hits = [r for (r,) in con.execute(
            "select id from nodes where id = ? or id like ?", (q, f"%{q}%"))][:6]
        if not hits:
            print(f"no node matches {q!r} — it is not in the graph at all"); return 1
        for h in hits:
            ins = list(con.execute(
                "select src, kind from edges where dst = ? limit 25", (h,)))
            outs = list(con.execute(
                "select dst, kind from edges where src = ? limit 25", (h,)))
            print(f"\n{h}")
            print(f"  <- cited by {len(ins)}" + ("" if ins else "   ORPHAN INBOUND"))
            for sname, k in ins[:8]:
                print(f"       [{k}] {sname}")
            print(f"  -> cites {len(outs)}" + ("" if outs else "   DEAD END"))
            for dname, k in outs[:8]:
                print(f"       [{k}] {dname}")
        return 0

    if a.orphans_in:
        rows = list(con.execute("select id from nodes where layer = ?", (a.orphans_in,)))
        linked = {r for (r,) in con.execute(
            "select src from edges union select dst from edges")}
        orph = [r for (r,) in rows if r not in linked]
        print(f"{a.orphans_in}: {len(orph)} orphans of {len(rows)}")
        for r in sorted(orph)[:40]:
            print("  ", r)
        return 0

    where = " where layer = ?" if a.layer else ""
    params = (a.layer,) if a.layer else ()
    nodes = {r: (k, l) for r, k, l in
             con.execute(f"select id, kind, layer from nodes{where}", params)}
    adj = defaultdict(set)
    deg_out = defaultdict(int)
    deg_in = defaultdict(int)
    n_edges = 0
    for s, d, k in con.execute("select src, dst, kind from edges"):
        if s in nodes and d in nodes:
            adj[s].add(d); adj[d].add(s)
            deg_out[s] += 1; deg_in[d] += 1
            n_edges += 1

    N = len(nodes)
    orphans = [r for r in nodes if not adj[r]]
    # consumed but never composing: something points at it, it points at nothing
    dead_ends = [r for r in nodes if deg_in[r] > 0 and deg_out[r] == 0]

    seen, comps = set(), []
    for r in nodes:
        if r in seen:
            continue
        q, comp = deque([r]), []
        seen.add(r)
        while q:
            x = q.popleft(); comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); q.append(y)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    lcc = len(comps[0]) if comps else 0

    dangling = con.execute(
        "select count(*) from failures where reason like 'dangling_ref%'").fetchone()[0]

    out = {
        "nodes": N, "edges": n_edges,
        "orphans": len(orphans), "orphan_rate": round(len(orphans) / N, 4) if N else 0,
        "largest_component": lcc, "organism_ratio": round(lcc / N, 4) if N else 0,
        "components": len(comps),
        "dead_ends": len(dead_ends),
        "dangling_refs": dangling,
    }
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2)); return 0

    print(f"nodes {N:,}   edges {n_edges:,}   components {len(comps):,}")
    print(f"ORPHANS            {len(orphans):>7,}  ({out['orphan_rate']:.1%})   아무도 안 가리키고 아무것도 안 가리킴")
    print(f"largest component  {lcc:>7,}  ({out['organism_ratio']:.1%})   <- 유기체 비율")
    print(f"dead ends          {len(dead_ends):>7,}          쓰이기만 하고 아무것도 구성 안 함")
    print(f"dangling refs      {dangling:>7,}          존재하지 않는 파일을 가리킴 = 부패")

    print("\nlayer                  n     orphan%   in_lcc%")
    per = defaultdict(lambda: [0, 0, 0])
    lccset = set(comps[0]) if comps else set()
    for r, (k, l) in nodes.items():
        per[l][0] += 1
        per[l][1] += (not adj[r])
        per[l][2] += (r in lccset)
    for l, (n, o, c) in sorted(per.items(), key=lambda kv: -kv[1][0])[:14]:
        print(f"{l:<18}{n:>7,}    {o/n:>6.1%}    {c/n:>6.1%}")

    print("\n최다 인용 (실제로 조직에 쓰이는 것):")
    for r in sorted(nodes, key=lambda x: -deg_in[x])[:10]:
        print(f"  {deg_in[r]:>5}  {r}")

    docs = [r for r, (k, l) in nodes.items() if k in ("doc", "spec", "contract", "experiment")]
    d_orph = [r for r in docs if not adj[r]]
    print(f"\n문서·계약·실험만: {len(docs):,}개 중 고아 {len(d_orph):,} ({len(d_orph)/max(1,len(docs)):.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
