"""experiments/radar/sources.py -- scriptable ecosystem-radar sources.

Founder directive (2026-07-17): keep tracking frontier + long-tail papers and
communities across sessions, not just the well-cited/trending ones. This
module pulls from every source that is SCRIPTABLE (no browser, no logged-in
session) with stdlib-only HTTP:

  - arxiv API      -- recency-sorted (submittedDate, NOT relevance) over
                      cs.AI/cs.LG/cs.CL/cs.MA. Recency sort is deliberate: it
                      is what surfaces the long-tail / not-yet-cited papers
                      the founder asked for, as opposed to a "top papers"
                      view that would only ever show already-famous work.
  - HuggingFace    -- daily_papers endpoint (community-submitted + upvotes).
  - GitHub search  -- api.github.com/search/repositories, sorted by `updated`
                      for a small set of AIOS-relevant keywords.
  - Reddit         -- public .json listings (no auth) for a couple of
                      relevant subreddits, with a descriptive User-Agent.

Every fetch_* function returns EITHER a list of normalized items:
    {id, title, url, date, source, abstract_or_desc, signal}
OR raises nothing -- callers should prefer `fetch_all()` / the per-source
`try_fetch_*` wrappers below, which always return
    {"items": [...], "error": None | "<short message>"}
so one dead source never takes the whole radar sweep down.

SESSION-GATED SOURCES (not implemented here, by design):
  X/Twitter and Threads have no stable, unauthenticated, script-friendly API
  as of 2026-07. Pulling them requires a logged-in browser session (e.g. the
  `council` skill's Grok/X lane or `insane-search`). This module does NOT
  fake-fetch them. `SESSION_GATED_SOURCES` below documents what a live Claude
  session's Ground phase should check manually; `run_radar.py` prints a
  reminder for these instead of silently omitting them.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "aios-ecosystem-radar/0.1 (research script; contact aios-operator)"
DEFAULT_TIMEOUT = 15

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_CATEGORIES = ("cs.AI", "cs.LG", "cs.CL", "cs.MA")

HF_DAILY_PAPERS_API = "https://huggingface.co/api/daily_papers"

GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
GITHUB_KEYWORDS = (
    "agent",
    "LLM eval",
    "evolutionary agent",
    "skill library",
)

REDDIT_SUBREDDITS = ("LocalLLaMA", "MachineLearning")

# Documented, not fetched here -- see module docstring.
SESSION_GATED_SOURCES = ("x_twitter", "threads")

ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def _http_get(url: str, *, timeout: int = DEFAULT_TIMEOUT, accept: str | None = None) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 -- fixed allowlisted hosts
        return resp.read()


# ---------------------------------------------------------------------------
# arxiv
# ---------------------------------------------------------------------------

def _arxiv_id_from_entry_id(entry_id: str) -> str:
    """http://arxiv.org/abs/2607.14049v1 -> 2607.14049 (stable, version-free)."""
    tail = entry_id.rsplit("/", 1)[-1]
    tail = tail.split("v")[0] if "v" in tail.rsplit(".", 1)[-1] else tail
    # strip a trailing vN if present
    if "v" in tail:
        base, _, ver = tail.rpartition("v")
        if ver.isdigit():
            tail = base
    return tail


def parse_arxiv_atom(xml_text: str) -> list[dict]:
    """Parse an arxiv Atom feed into normalized items. Pure, no network."""
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for entry in root.findall("a:entry", ATOM_NS):
        raw_id = (entry.findtext("a:id", default="", namespaces=ATOM_NS) or "").strip()
        if not raw_id:
            continue
        arxiv_id = _arxiv_id_from_entry_id(raw_id)
        title = (entry.findtext("a:title", default="", namespaces=ATOM_NS) or "").strip()
        title = " ".join(title.split())
        summary = (entry.findtext("a:summary", default="", namespaces=ATOM_NS) or "").strip()
        summary = " ".join(summary.split())
        published = (entry.findtext("a:published", default="", namespaces=ATOM_NS) or "")[:10]
        items.append({
            "id": f"arxiv:{arxiv_id}",
            "title": title,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "date": published,
            "source": "arxiv",
            "abstract_or_desc": summary,
            "signal": 0,
        })
    return items


def fetch_arxiv(categories: tuple[str, ...] = ARXIV_CATEGORIES, max_results: int = 50,
                 timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    search_query = " OR ".join(f"cat:{c}" for c in categories)
    params = {
        "search_query": search_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    body = _http_get(url, timeout=timeout)
    return parse_arxiv_atom(body.decode("utf-8", errors="replace"))


# ---------------------------------------------------------------------------
# HuggingFace daily papers
# ---------------------------------------------------------------------------

def parse_hf_papers(payload: list) -> list[dict]:
    """Parse the huggingface.co/api/daily_papers JSON list. Pure, no network."""
    items: list[dict] = []
    for entry in payload or []:
        paper = entry.get("paper", {}) or {}
        paper_id = paper.get("id") or entry.get("id")
        if not paper_id:
            continue
        title = entry.get("title") or paper.get("title") or ""
        summary = entry.get("summary") or paper.get("summary") or ""
        date = (entry.get("publishedAt") or paper.get("publishedAt") or "")[:10]
        signal = paper.get("upvotes", entry.get("numComments", 0)) or 0
        items.append({
            "id": f"hf:{paper_id}",
            "title": title.strip(),
            "url": f"https://huggingface.co/papers/{paper_id}",
            "date": date,
            "source": "huggingface",
            "abstract_or_desc": summary.strip(),
            "signal": signal,
        })
    return items


def fetch_hf_papers(limit: int = 30, timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    url = f"{HF_DAILY_PAPERS_API}?{urllib.parse.urlencode({'limit': limit})}"
    body = _http_get(url, timeout=timeout, accept="application/json")
    return parse_hf_papers(json.loads(body.decode("utf-8", errors="replace")))


# ---------------------------------------------------------------------------
# GitHub search (recent repos by keyword, sorted by last update)
# ---------------------------------------------------------------------------

def parse_github_search(payload: dict) -> list[dict]:
    """Parse a GitHub search/repositories response. Pure, no network."""
    items: list[dict] = []
    for r in (payload or {}).get("items", []) or []:
        full_name = r.get("full_name")
        if not full_name:
            continue
        items.append({
            "id": f"github:{full_name}",
            "title": full_name,
            "url": r.get("html_url") or f"https://github.com/{full_name}",
            "date": (r.get("pushed_at") or r.get("updated_at") or r.get("created_at") or "")[:10],
            "source": "github",
            "abstract_or_desc": (r.get("description") or "").strip(),
            "signal": r.get("stargazers_count", 0),
        })
    return items


def fetch_github(keywords: tuple[str, ...] = GITHUB_KEYWORDS, per_keyword: int = 8,
                  sort: str = "updated", timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    seen_ids: set[str] = set()
    items: list[dict] = []
    for kw in keywords:
        q = f"{kw} in:name,description"
        params = {"q": q, "sort": sort, "order": "desc", "per_page": per_keyword}
        url = f"{GITHUB_SEARCH_API}?{urllib.parse.urlencode(params)}"
        body = _http_get(url, timeout=timeout, accept="application/vnd.github+json")
        for it in parse_github_search(json.loads(body.decode("utf-8", errors="replace"))):
            if it["id"] not in seen_ids:
                seen_ids.add(it["id"])
                items.append(it)
        time.sleep(0.5)  # be polite to the unauthenticated search rate limit
    return items


# ---------------------------------------------------------------------------
# Reddit public JSON listings
# ---------------------------------------------------------------------------

def parse_reddit_listing(payload: dict) -> list[dict]:
    """Parse a reddit /new.json listing response. Pure, no network."""
    items: list[dict] = []
    children = ((payload or {}).get("data", {}) or {}).get("children", []) or []
    for c in children:
        d = c.get("data", {}) or {}
        post_id = d.get("id")
        if not post_id:
            continue
        created = d.get("created_utc")
        date = time.strftime("%Y-%m-%d", time.gmtime(created)) if created else ""
        items.append({
            "id": f"reddit:{d.get('subreddit', '')}:{post_id}",
            "title": (d.get("title") or "").strip(),
            "url": f"https://www.reddit.com{d.get('permalink', '')}" if d.get("permalink") else d.get("url", ""),
            "date": date,
            "source": "reddit",
            "abstract_or_desc": (d.get("selftext") or "")[:500].strip(),
            "signal": d.get("score", 0),
        })
    return items


def fetch_reddit(subreddit: str, limit: int = 20, timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?{urllib.parse.urlencode({'limit': limit})}"
    body = _http_get(url, timeout=timeout, accept="application/json")
    return parse_reddit_listing(json.loads(body.decode("utf-8", errors="replace")))


# ---------------------------------------------------------------------------
# Aggregate, error-safe sweep
# ---------------------------------------------------------------------------

def _safe(source_name: str, fn, *args, **kwargs) -> dict:
    try:
        items = fn(*args, **kwargs)
        return {"items": items, "error": None}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, OSError, ValueError) as exc:
        return {"items": [], "error": f"{source_name}: {type(exc).__name__}: {exc}"}


def fetch_all(*, timeout: int = DEFAULT_TIMEOUT) -> dict[str, dict]:
    """Sweep every scriptable source. Never raises -- each source reports its
    own {"items": [...], "error": ...} so one dead source doesn't kill the run.
    """
    results: dict[str, dict] = {
        "arxiv": _safe("arxiv", fetch_arxiv, timeout=timeout),
        "huggingface": _safe("huggingface", fetch_hf_papers, timeout=timeout),
        "github": _safe("github", fetch_github, timeout=timeout),
    }
    for sub in REDDIT_SUBREDDITS:
        results[f"reddit_{sub.lower()}"] = _safe(f"reddit_{sub}", fetch_reddit, sub, timeout=timeout)
    return results
