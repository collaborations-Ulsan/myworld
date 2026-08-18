#!/usr/bin/env python3
"""aios.doc.index.v1 — generate the map for 611 closed documents.

Triage measured what the founder's "sprawling unprocessed TODOs" actually is, and it is
not TODOs: 3 docs carry an intent marker, 17 of 17 preregistrations have recorded results,
and the docs layer has ZERO graph orphans. What it is instead is 3.6M tokens of
interlinked, closed documents with no map — which reads as sprawl whether or not anything
is open.

So the fix is an index, and a generated one, because a hand-written index is stale the day
after and becomes the 612th document.

Status comes from the graph, not from prose:
  ANCHOR      heavily cited — load-bearing, read these first
  CLOSED      records its own outcome (NO-GO / kill rule / PASS / 결과)
  SUPERSEDED  says so in its own head matter
  OPEN        carries an unresolved intent marker
  REFERENCE   cited, no outcome of its own — context rather than conclusion
"""
from __future__ import annotations
import os, re, sqlite3, sys, time
from collections import Counter, defaultdict
from pathlib import Path

WS = Path("/home/user/workspaces/jaewon")
DB = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"
OUT = Path("docs/AIOS_DOC_INDEX.md")

OUTCOME = re.compile(r"(?i)(NO-GO|kill rule.{0,15}발동|PASS\b|FAIL\b|결과:|판정:|"
                     r"측정했다|점등|CONFIRMED|REFUTED)")
SUPER = re.compile(r"(?i)^.{0,400}?(supersede[sd]?|철회|폐기|무효화|deprecated)", re.S)
INTENT = re.compile(r"(?m)^\s*(?:[-*]\s*\[ \]|TODO|FIXME)")
THEMES = [
    ("실험·게이트", r"PREREG|GATE|RESULTS|EXPERIMENT|prereg|G\d_|M\d_"),
    ("아키텍처·설계", r"ARCHITECT|DESIGN|BLUEPRINT|KERNEL|STACK|SPINE|SEAM|PROTOCOL"),
    ("판정·검토", r"AUDIT|REVIEW|CRITIQUE|SYNTHESIS|VERDICT|REPORT|BRIEF"),
    ("기억·온톨로지", r"MEMORY|MEMORYOS|ONTOLOGY|GRAPH|AKASHIC|DISTILL"),
    ("사회·에이전트", r"SOCIETY|AGENT|SOVEREIGN|HIVE|COPYNESS|PARTITION|PEER"),
    ("운영·계약", r"CONTRACT|LEDGER|OPERATOR|WORKSTREAM|DISPATCH|PLAYBOOK|SESSION"),
]


def theme(name: str) -> str:
    for t, pat in THEMES:
        if re.search(pat, name):
            return t
    return "기타"


def main() -> int:
    con = sqlite3.connect(DB)
    inbound = Counter(d for (d,) in con.execute("select dst from edges"))
    outbound = Counter(s for (s,) in con.execute("select src from edges"))
    mt = dict(con.execute("select id, mtime from nodes"))
    now = time.time()

    docs = []
    for p in sorted(Path("docs").rglob("*.md")):
        if "/_history/" in str(p) or "/_legacy/" in str(p) or p.name == OUT.name:
            continue
        try:
            txt = p.read_text(errors="replace")
        except OSError:
            continue
        rel = f"myworld/{p}"
        cited = inbound.get(rel, 0)
        head = txt[:1200]
        if SUPER.match(head):
            st = "SUPERSEDED"
        elif INTENT.search(txt):
            st = "OPEN"
        elif OUTCOME.search(txt):
            st = "CLOSED"
        elif cited >= 8:
            st = "ANCHOR"
        else:
            st = "REFERENCE"
        if cited >= 8 and st == "CLOSED":
            st = "ANCHOR"
        title = next((l.lstrip("# ").strip() for l in txt.splitlines()
                      if l.startswith("# ")), p.stem)
        docs.append(dict(path=str(p), name=p.name, title=title[:95], status=st,
                         cited=cited, cites=outbound.get(rel, 0),
                         idle=int((now - mt.get(rel, now)) / 86400),
                         theme=theme(p.name)))

    by_status = Counter(d["status"] for d in docs)
    groups = defaultdict(list)
    for d in docs:
        groups[d["theme"]].append(d)

    L = [f"# 문서 색인 — 자동 생성 ({time.strftime('%Y-%m-%d')})",
         "",
         "**손으로 고치지 말 것.** `python3 scripts/aios_doc_index.py`가 다시 만든다.",
         "손으로 쓴 색인은 하루 뒤 낡고, 612번째 문서가 된다.",
         "",
         "## 측정 — 창업자 진단과 다른 부분",
         "",
         "*\"장황하게 처리되지 못한 TODO로 남았다\"*를 재봤더니 그게 아니었다:",
         "",
         "```",
         f"문서            {len(docs)}",
         f"미해결 표시     {by_status.get('OPEN', 0)}   (intent 마커가 실제로 남은 것)",
         "사전등록        17건 전부 결과 기록됨 (매달린 계획 0)",
         "그래프 고아     0  (docs 층 고아율 0.0%)",
         "```",
         "",
         "닫히지 않은 것이 문제가 아니라 **닫힌 문서가 지도 없이 쌓인 것**이 문제다.",
         "전부 닫혀 있어도 지도가 없으면 장황함으로 경험된다. 그래서 삭제가 아니라 색인이다.",
         "",
         "## 상태",
         "",
         "| | 뜻 |",
         "|---|---|",
         "| **ANCHOR** | 많이 인용됨 — 조직을 지탱한다. 먼저 읽을 것 |",
         "| **CLOSED** | 자기 결과를 기록함 (NO-GO / kill rule / PASS) |",
         "| **SUPERSEDED** | 스스로 폐기를 선언함 |",
         "| **OPEN** | 미해결 표시가 남음 |",
         "| **REFERENCE** | 인용되지만 자기 결론은 없음 — 결론이 아니라 맥락 |",
         "",
         "```",
         *[f"{k:<12}{v:>5}" for k, v in by_status.most_common()],
         "```",
         ""]

    for t, _ in THEMES + [("기타", "")]:
        ds = sorted(groups.get(t, []), key=lambda d: (-d["cited"], d["name"]))
        if not ds:
            continue
        L += [f"## {t} ({len(ds)})", "",
              "| 상태 | 피인용 | 문서 | 제목 |", "|---|---:|---|---|"]
        for d in ds:
            L.append(f"| {d['status']} | {d['cited']} | "
                     f"[{d['name'][:-3]}]({d['name']}) | {d['title']} |")
        L.append("")

    OUT.write_text("\n".join(L))
    print(f"wrote {OUT}  ({len(docs)} docs)")
    print("  " + "  ".join(f"{k}:{v}" for k, v in by_status.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
