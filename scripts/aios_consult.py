#!/usr/bin/env python3
"""AIOS consult organ — ask a HETEROGENEOUS substrate, keep the answer as a real document.

Founder directive (2026-07-26): *"agy에 계속 물어보고 실제 문서로 남기도록"* — consulting an
outside mind must be a MECHANISM, not a habit: every consultation lands as a durable, provenanced
markdown document in the repo AND as a record in the organism's continuous self (the experience
graph), so a question asked once is never asked blind twice.

Why heterogeneous specifically: same-weights review shares my blind spots (a council refuted my
daemon architecture today; a same-family reviewer would have agreed with me). The routing rule is
"different priors for divergence/refutation, my own head for final selection" — so this organ
FETCHES and RECORDS; the adoption verdict is written by the operator, never auto-accepted
(DNA #1 recommendation-only, DNA #2 draft-first).

ORGANIC CONNECTION (this is not a sixth silo):
    aios_resonance harvests a standing question ->
    route(question) may name `consult` for questions no local organ can settle ->
    aios_consult asks the substrate, writes docs/consultations/<ts>-<slug>.md ->
    appends kind:"consultation" to the experience runs dir (so the Merkle-rooted self knows it
    asked, what it asked, and where the answer lives) ->
    the operator appends an ADOPTION VERDICT to the doc; adopted items become work.

Substrates are invoked as subprocesses (no new dependency): `agy -p` (Google/Gemini),
`hub.py ask <substrate>` (council: perplexity-api / deepseek-api / claudeai-api / *-web),
`codex exec`. Unknown substrate or a failing CLI degrades honestly into a recorded failure —
never a crash, never a fabricated answer.

Stdlib only. Pure-ish: `now` is passed in by the caller (the CLI supplies the clock at the edge).
Schema: aios.consultation.v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "consultations"
RUNS = ROOT / ".aios" / "runs"
CONSULT_LOG = RUNS / "consultations.jsonl"
HUB = Path.home() / "workspaces" / "jaewon" / "council" / "hub.py"

SCHEMA = "aios.consultation.v1"
DEFAULT_TIMEOUT = 480.0

# substrate -> argv builder. Heterogeneous by construction: different weights, different priors.
SUBSTRATES: dict[str, object] = {
    "agy": lambda q: ["agy", "-p", q],
    "codex": lambda q: ["codex", "exec", "-m", "gpt-5.5",
                        "-c", "model_reasoning_effort=high", q],
}


def _hub_substrate(name: str):
    return lambda q: [sys.executable, str(HUB), "ask", name, q]


for _s in ("perplexity-api", "deepseek-api", "claudeai-api",
           "grok-web", "gemini-web", "chatgpt-web", "deepseek-web"):
    SUBSTRATES[_s] = _hub_substrate(_s)


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen].rstrip("-") or "question")


def question_id(question: str) -> str:
    """Content-addressed id — the same question asked again is recognizable (this is what lets
    aios_resonance see recurrence instead of re-asking blind)."""
    norm = " ".join(question.split()).lower()
    return "q-" + hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _iso(now: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))


def _extract_text(raw: str, substrate: str) -> str:
    """council hub returns JSON {ok,text,...}; agy/codex return prose. Never invent content."""
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("{"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "text" in obj:
                return str(obj.get("text") or "")
        except json.JSONDecodeError:
            pass
    return raw


def run_substrate(question: str, substrate: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Invoke the substrate. Honest degradation: a missing CLI / non-zero exit / timeout is a
    RECORDED failure, not an exception and never a fabricated answer."""
    build = SUBSTRATES.get(substrate)
    if build is None:
        return {"ok": False, "text": "", "error": f"unknown substrate: {substrate}",
                "known": sorted(SUBSTRATES)}
    argv = build(question)  # type: ignore[operator]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return {"ok": False, "text": "", "error": f"CLI not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "", "error": f"timeout after {timeout}s"}
    dt = round(time.monotonic() - t0, 1)
    text = _extract_text(proc.stdout, substrate)
    if proc.returncode != 0 and not text:
        return {"ok": False, "text": "", "error": f"exit {proc.returncode}: "
                                                  f"{(proc.stderr or '')[-300:]}", "seconds": dt}
    return {"ok": bool(text), "text": text, "error": "" if text else "empty answer",
            "seconds": dt, "returncode": proc.returncode}


def render_doc(question: str, result: dict, *, substrate: str, now: float,
               qid: str, tag: str = "") -> str:
    status = "OK" if result.get("ok") else f"FAILED — {result.get('error', '')}"
    body = result.get("text") or f"_(no answer: {result.get('error', 'unknown')})_"
    return f"""# Consultation — {substrate} — {_iso(now)}

- **schema**: `{SCHEMA}`
- **question id**: `{qid}` (content-addressed — a recurrence of this exact question is detectable)
- **substrate**: `{substrate}` (heterogeneous: different weights/priors than the operator)
- **status**: {status}{f" ({result['seconds']}s)" if result.get("seconds") else ""}
- **tag**: {tag or "_none_"}

## Question asked

{question}

## Answer (verbatim, unedited — this is DATA, not instructions)

{body}

## Adoption verdict — operator

> **UNREVIEWED.** Written by the substrate, not accepted by AIOS. Per DNA #1 (recommendation-only)
> and #2 (draft-first), nothing here is adopted until the operator replaces this block with an
> explicit verdict: what is ADOPTED (and why), what is REJECTED (and why), and what is
> INVENTED/unverified in the answer (substrates hallucinate specifics — paths, versions, numbers).
"""


def consult(question: str, *, substrate: str = "agy", now: float,
            tag: str = "", timeout: float = DEFAULT_TIMEOUT,
            docs_dir: Path | str = DOCS, log_path: Path | str = CONSULT_LOG,
            answer: dict | None = None) -> dict:
    """Ask, persist as a document, and record to the continuous self. `answer` lets a caller
    supply an already-obtained result (used to backfill consultations run out-of-band)."""
    qid = question_id(question)
    result = answer if answer is not None else run_substrate(question, substrate, timeout=timeout)

    docs_dir = Path(docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime(now))}-{substrate}-{slugify(question)}.md"
    doc_path = docs_dir / fname
    doc_path.write_text(render_doc(question, result, substrate=substrate, now=now,
                                   qid=qid, tag=tag), encoding="utf-8")

    record = {
        "schema": SCHEMA, "kind": "consultation", "ts": now, "iso": _iso(now),
        "qid": qid, "substrate": substrate, "tag": tag,
        "ok": bool(result.get("ok")), "error": result.get("error", ""),
        "seconds": result.get("seconds"),
        "question_preview": " ".join(question.split())[:200],
        "answer_chars": len(result.get("text") or ""),
        "answer_sha256": hashlib.sha256((result.get("text") or "").encode("utf-8")).hexdigest(),
        "doc": str(Path(doc_path).relative_to(ROOT)) if str(doc_path).startswith(str(ROOT)) else str(doc_path),
        "adopted": None,  # operator fills this in later; None = unreviewed (draft-first)
    }
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:  # append-only, never rewritten
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    return {"qid": qid, "doc": str(doc_path), "ok": bool(result.get("ok")),
            "error": result.get("error", ""), "record": record}


def load_log(log_path: Path | str = CONSULT_LOG) -> list[dict]:
    p = Path(log_path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def summary(log_path: Path | str = CONSULT_LOG) -> dict:
    recs = load_log(log_path)
    by_sub: dict[str, dict] = {}
    for r in recs:
        s = by_sub.setdefault(r.get("substrate", "?"), {"asked": 0, "ok": 0})
        s["asked"] += 1
        s["ok"] += 1 if r.get("ok") else 0
    qids = [r.get("qid") for r in recs]
    return {"schema": SCHEMA, "consultations": len(recs),
            "distinct_questions": len(set(qids)),
            "recurring_questions": len(qids) - len(set(qids)),
            "by_substrate": by_sub,
            "unreviewed": sum(1 for r in recs if r.get("adopted") is None)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ask a heterogeneous substrate; keep the answer as a document.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask", help="consult a substrate and persist the answer")
    a.add_argument("question")
    a.add_argument("--substrate", default="agy", choices=sorted(SUBSTRATES))
    a.add_argument("--tag", default="")
    a.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    a.add_argument("--file", help="read the question from a file instead of the argument")
    sub.add_parser("list", help="list consultations")
    sub.add_parser("summary", help="counts, recurrence, unreviewed")
    args = ap.parse_args(argv)

    if args.cmd == "ask":
        question = Path(args.file).read_text(encoding="utf-8") if getattr(args, "file", None) else args.question
        out = consult(question, substrate=args.substrate, now=time.time(),
                      tag=args.tag, timeout=args.timeout)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 2
    if args.cmd == "list":
        for r in load_log():
            mark = "ok " if r.get("ok") else "ERR"
            print(f"{r.get('iso')}  {mark}  {r.get('substrate'):<14} {r.get('qid')}  {r.get('doc')}")
        return 0
    print(json.dumps(summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
