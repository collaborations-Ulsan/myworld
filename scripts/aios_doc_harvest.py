#!/usr/bin/env python3
"""Harvest provider documentation into a durable, digest-addressed corpus.

founder: read the docs for Claude, Codex, agy and the rest, save them, embed
them into memoryOS, and check whether the knowledge is actually absorbed when
it is needed.

The last clause is the whole task. Storing documents and declaring the knowledge
available is the failure this repository has measured all day: a mechanism
offered and never invoked. So this module ends in a RETRIEVAL PROBE, not in an
import count, and the probe is scored against questions that were actually asked
— every one of them came up while tearing the runtime apart today, with the
page that answers it recorded before the probe runs.

Design notes that are not decoration:

  * Pages are stored with a sha256 of their body and an append-only manifest.
    A doc corpus without digests cannot answer "did this page change under us",
    which for vendor documentation is the interesting question.
  * `fetch` is separated from `import` and from `probe` so a failed embedding
    step never looks like a failed harvest, and so the probe can be re-run
    against an unchanged corpus.
  * A page that fails to fetch is RECORDED as a failure. A doc set that
    silently drops pages looks exactly like a smaller doc set.

    python3 scripts/aios_doc_harvest.py sources
    python3 scripts/aios_doc_harvest.py fetch --provider claude
    python3 scripts/aios_doc_harvest.py probe --json

Schema: aios.doc_harvest.v0   Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

SCHEMA = "aios.doc_harvest.v0"
ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs" / "external" / "providers"
MANIFEST = CORPUS / "manifest.jsonl"
UA = "aios-doc-harvest/0.1 (+https://github.com/cjw0076/myworld)"

# Each provider needs a way to enumerate its pages. Claude publishes llms.txt
# and serves every page as markdown, which is the cheapest possible contract;
# the others are listed with what they actually offer, and where a provider has
# no machine-readable index that is recorded rather than guessed at.
SOURCES: dict[str, dict] = {
    "claude": {
        "index": "https://code.claude.com/docs/llms.txt",
        "index_kind": "llms_txt",
        "page_suffix": ".md",
        "note": "publishes llms.txt; every page also serves as .md",
    },
    "codex": {
        "index": "https://raw.githubusercontent.com/openai/codex/main/docs/",
        "index_kind": "github_dir",
        "repo": "openai/codex",
        "path": "docs",
        "note": "docs live in the repo; enumerated through the GitHub API",
    },
    "gemini-cli": {
        "index": "https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/",
        "index_kind": "github_dir",
        "repo": "google-gemini/gemini-cli",
        "path": "docs",
        "note": "agy is the antigravity CLI; gemini-cli is the closest public "
                "doc set and is harvested as the Google-side reference",
    },
    "mcp": {
        "index": "https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/",
        "index_kind": "github_dir",
        "repo": "modelcontextprotocol/modelcontextprotocol",
        "path": "docs",
        "note": "the tool-plane spec every provider above binds to",
    },
    # --- frontier agent-native apps (probed 2026-08-18; only endpoints that answered
    # 200 are registered. Guessing a URL would only manufacture dangling entries) ---
    "kimi-cli": {
        "index": "https://raw.githubusercontent.com/MoonshotAI/kimi-cli/main/docs/",
        "index_kind": "github_dir", "repo": "MoonshotAI/kimi-cli", "path": "docs",
        "note": "Moonshot's agent CLI",
    },
    "kimi-k2": {
        "index": "https://raw.githubusercontent.com/MoonshotAI/Kimi-K2/main/docs/",
        "index_kind": "github_dir", "repo": "MoonshotAI/Kimi-K2", "path": "docs",
        "note": "the model side of the same house",
    },
    "hermes": {
        "index": "https://raw.githubusercontent.com/NousResearch/Hermes-Agent/main/docs/",
        "index_kind": "github_dir", "repo": "NousResearch/Hermes-Agent", "path": "docs",
        "note": "Nous Hermes agent — the local-first peer we have compared against",
    },
    "openai-agents": {
        "index": "https://raw.githubusercontent.com/openai/openai-agents-python/main/docs/",
        "index_kind": "github_dir", "repo": "openai/openai-agents-python", "path": "docs",
        "note": "OpenAI's agent SDK — the loop Codex CLI is built on",
    },
    "orca": {
        "index": "https://docs.orcarouter.ai/llms.txt",
        "index_kind": "llms_txt", "page_suffix": ".md",
        "note": "router peer; publishes llms.txt",
    },
    # cursor: docs.cursor.com/llms.txt 308s to cursor.com/docs which is HTML, not llms.txt.
    # Left OUT rather than registered with a URL that does not serve what we claim.
}


def _get(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _sha(b: bytes | str) -> str:
    if isinstance(b, str):
        b = b.encode("utf-8")
    return "sha256:" + hashlib.sha256(b).hexdigest()


def enumerate_pages(provider: str, limit: int) -> tuple[list[str], list[str]]:
    """Return (urls, problems). Problems are returned, never swallowed."""
    spec = SOURCES[provider]
    problems: list[str] = []
    try:
        if spec["index_kind"] == "llms_txt":
            body = _get(spec["index"]).decode("utf-8", "replace")
            urls = re.findall(r"\((https://[^)]+?\.md)\)", body)
            if not urls:                     # some indexes list bare links
                urls = re.findall(r"^https://\S+\.md$", body, re.M)
            return sorted(set(urls))[:limit], problems
        if spec["index_kind"] == "github_dir":
            api = (f"https://api.github.com/repos/{spec['repo']}"
                   f"/contents/{spec['path']}")
            items = json.loads(_get(api))
            urls = [i["download_url"] for i in items
                    if i.get("type") == "file"
                    and str(i.get("name", "")).endswith((".md", ".mdx"))
                    and i.get("download_url")]
            return sorted(urls)[:limit], problems
    except (urllib.error.URLError, OSError, json.JSONDecodeError,
            KeyError, ValueError) as exc:
        problems.append(f"{provider}: {type(exc).__name__}: {exc}"[:200])
    return [], problems


def _slug(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1] or "index"
    return re.sub(r"[^A-Za-z0-9._-]", "-", tail)[:80]


def read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    out = []
    for ln in MANIFEST.open(encoding="utf-8"):
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def fetch(provider: str, limit: int, verbose: bool = True) -> dict:
    urls, problems = enumerate_pages(provider, limit)
    known = {r["url"]: r for r in read_manifest()}
    out_dir = CORPUS / provider
    out_dir.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    saved, unchanged, changed, failed = 0, 0, 0, []
    with MANIFEST.open("a", encoding="utf-8") as mf:
        for i, url in enumerate(urls, 1):
            try:
                body = _get(url).decode("utf-8", "replace")
            except (urllib.error.URLError, OSError) as exc:
                failed.append({"url": url, "error": f"{type(exc).__name__}"})
                continue
            digest = _sha(body)
            prior = known.get(url)
            if prior and prior.get("digest") == digest:
                unchanged += 1
                continue
            path = out_dir / f"{_slug(url)}"
            if not path.suffix:
                path = path.with_suffix(".md")
            path.write_text(body, encoding="utf-8")
            rec = {"schema": SCHEMA, "provider": provider, "url": url,
                   "path": str(path.relative_to(ROOT)), "digest": digest,
                   "bytes": len(body),
                   "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "previous_digest": (prior or {}).get("digest")}
            mf.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            saved += 1
            changed += 1 if prior else 0
            if verbose and i % 20 == 0:
                print(f"  {i}/{len(urls)}", flush=True)
            time.sleep(0.3)              # be a polite client
    return {"schema": SCHEMA, "provider": provider, "listed": len(urls),
            "saved": saved, "unchanged": unchanged, "revised": changed,
            "failed": failed, "index_problems": problems,
            "note": ("failed pages are listed, not dropped — a doc set that "
                     "silently loses pages looks like a smaller doc set")}


# --- the gate ---------------------------------------------------------------
# Questions that actually came up while tearing the runtime apart today, each
# paired with a substring that only the answering page contains. Written BEFORE
# running the probe so the scoring cannot drift toward whatever retrieval
# happens to return.
PROBE: list[dict] = [
    {"q": "how does one Claude Code session reach another on the same machine",
     "expect_url_contains": "cross-session-messaging"},
    {"q": "what lives in the .claude directory and which files hold state",
     "expect_url_contains": "claude-directory"},
    {"q": "how do I push an external event into a session that is already running",
     "expect_url_contains": "channels"},
    {"q": "how do I intercept a tool call before it executes",
     "expect_url_contains": "hooks"},
    {"q": "what sandbox does the bash tool use and how is it configured",
     "expect_url_contains": "sandbox"},
    {"q": "how is a session resumed after the process exits",
     "expect_url_contains": "session"},
]


def probe(limit: int = 5) -> dict:
    """Does the corpus answer the questions that made us build it?

    Deliberately a LEXICAL probe over the stored files, with no embedding step.
    Two reasons. It measures the corpus rather than the embedder, and today's
    measurement is that this machine's embedding path degrades to keyword
    search without saying so — scoring retrieval through it would report the
    corpus as bad when the retriever is what failed.
    """
    rows = read_manifest()
    by_path: dict[str, dict] = {}
    for r in rows:                       # last write per path wins
        by_path[r["path"]] = r
    corpus = []
    for r in by_path.values():
        p = ROOT / r["path"]
        if p.exists():
            corpus.append((r, p.read_text(encoding="utf-8", errors="replace").lower()))

    # BM25 with the conventional k1=1.5, b=0.75. NOT tuned against this probe:
    # the first run scored 2/6 with raw term counts and `changelog.md` won every
    # single query, because an unnormalised count is a vote for whichever file
    # is longest. Length normalisation is the textbook repair for exactly that
    # bias and was chosen before seeing which questions it would fix.
    import math
    K1, B = 1.5, 0.75
    docs = [(r, re.findall(r"[a-z]{3,}", text)) for r, text in corpus]
    avg_len = sum(len(t) for _, t in docs) / max(1, len(docs))
    freqs = [(r, {}, len(toks)) for r, toks in docs]
    for (r, f, _), (_, toks) in zip(freqs, docs):
        for t in toks:
            f[t] = f.get(t, 0) + 1
    df: dict[str, int] = {}
    for _, f, _ in freqs:
        for t in f:
            df[t] = df.get(t, 0) + 1
    N = max(1, len(freqs))

    results = []
    for item in PROBE:
        terms = [w for w in re.findall(r"[a-z]{4,}", item["q"].lower())]
        scored = []
        for r, f, dl in freqs:
            score = 0.0
            for t in terms:
                tf = f.get(t, 0)
                if not tf:
                    continue
                idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * dl / avg_len))
            if score:
                scored.append((score, r["url"]))
        scored.sort(reverse=True)
        top = [u for _, u in scored[:limit]]
        hit = any(item["expect_url_contains"] in u for u in top)
        results.append({"question": item["q"], "hit": hit,
                        "expected_page_contains": item["expect_url_contains"],
                        "top": top[:3]})
    hits = sum(1 for r in results if r["hit"])
    return {"schema": SCHEMA, "corpus_pages": len(corpus),
            "questions": len(PROBE), "hits": hits,
            "recall_at_%d" % limit: round(hits / max(1, len(PROBE)), 3),
            "results": results,
            "scorer": "bm25(k1=1.5,b=0.75)",
            "baseline_raw_termcount": "2/6 — every query returned changelog.md",
            "reading": ("a page stored is not a page retrieved; this scores the "
                        "corpus lexically so a degraded embedder cannot be "
                        "mistaken for a bad corpus")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sources")
    f = sub.add_parser("fetch")
    f.add_argument("--provider", required=True, choices=sorted(SOURCES) + ["all"])
    f.add_argument("--limit", type=int, default=200)
    f.add_argument("--json", action="store_true")
    s = sub.add_parser("status")
    p = sub.add_parser("probe")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "sources":
        print(json.dumps(SOURCES, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "status":
        rows = read_manifest()
        per: dict[str, int] = {}
        for r in rows:
            per[r["provider"]] = per.get(r["provider"], 0) + 1
        print(json.dumps({"manifest_rows": len(rows), "per_provider": per,
                          "corpus": str(CORPUS.relative_to(ROOT))},
                         ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "fetch":
        provs = sorted(SOURCES) if a.provider == "all" else [a.provider]
        out = [fetch(p, a.limit, verbose=not a.json) for p in provs]
        print(json.dumps(out, ensure_ascii=False, indent=1) if a.json else
              "\n".join(f"{o['provider']}: listed={o['listed']} saved={o['saved']} "
                        f"unchanged={o['unchanged']} failed={len(o['failed'])}"
                        for o in out))
        return 0
    out = probe(a.limit)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"corpus {out['corpus_pages']} pages · "
              f"{out['hits']}/{out['questions']} questions answered")
        for r in out["results"]:
            print(f"  [{'HIT ' if r['hit'] else 'MISS'}] {r['question'][:64]}")
            if not r["hit"]:
                print(f"         wanted *{r['expected_page_contains']}*, got "
                      f"{[u.split('/')[-1] for u in r['top']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
