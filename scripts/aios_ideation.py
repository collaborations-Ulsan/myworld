#!/usr/bin/env python3
"""Ideation absorption — turn ideas scattered across the internet into an asset.

founder: *"인터넷에 방대하게 흩어진 Ideation들을 흡수해서 자산화 해"*

A summary document would be the wrong shape. Our own measurement says so: every
mechanism we OFFERED was used exactly zero times (skill dispatch 0/32,
supersede 0/32, closure masking 0 physical blocks across 96 episodes —
docs/AIOS_WHAT_THE_OS_IS_2026-08-09.md). A pile of harvested ideas an agent
*may* consult is another zero. So absorption is built here as a closed cycle
that runs without the model choosing to run it, and whose output is refused
unless it survives a check the generator cannot influence:

    SENSE    a source has items newer than our cursor        (policy, not model)
    ACT      the host hands each item to a fixed distiller   (model never asked
                                                              *whether* to run)
    VERIFY   a deterministic grounding oracle judges it      (verifier != executor)
    SETTLE   the claim is committed, or REVERTED, on ledger  (both change the root)

That is the four-tuple from docs/AIOS_MINIMAL_OPERATION_2026-08-09.md, and this
organ is deliberately built to be its first live predicate: absorption is not
the Channel-E `dispatch` mechanism, so it is outside the Mortuary Clause.

WHAT THE ORACLE ACTUALLY CHECKS (this is the whole value; read it before
trusting a row):

  1. VERBATIM GROUNDING — the distiller must quote a span that appears, byte for
     byte after whitespace normalisation, in the text we fetched. A paraphrase
     fails. This is what makes a local 30B model safe to point at the open web:
     it cannot smuggle an invention past a substring test.
  2. FALSIFIER PRESENT — a claim with no named way to kill it is not an asset,
     it is a quote. Rejected.
  3. NOVELTY NEEDS A WITNESS — and right now we do not have one. Every claim is
     still reduced to its nearest framing in OUR corpus and the score is
     recorded, but the threshold is MEASURED against two controls (`calibrate`:
     positives = local-model paraphrases of our own sentences, negatives =
     abstracts from an unrelated field) and as of 2026-08-10 it does not
     separate them — three statistics, Youden J = 0.5167 (document-level max
     cosine), 0.5673 (passage-level max cosine), 0.4476 (passage-level peak-z).
     So a well-formed row is labelled `grounded`, NOT `novel`, and `rename` is
     only ever emitted when a calibration with separated=true exists.

HONEST LIMITS, stated where they cannot be missed:
  - The oracle proves the quote is REAL. It does not prove the claim is TRUE,
    and — until dedup separates — it does not prove the claim is NEW either.
    `epistemic_type` starts at `Proposal` and only a run receipt raises it.
  - `dedup_method`, `dedup_trusted` and `novelty_assessed` are recorded on every
    row. A row with novelty_assessed=false says nothing about novelty; do not
    read `grounded` as a weaker word for `novel`.
  - Nothing private leaves the box: queries are constants or CLI arguments,
    never file content; distillation and embedding are local (ollama).

    python3 scripts/aios_ideation.py run --limit 12
    python3 scripts/aios_ideation.py stats
    python3 scripts/aios_ideation.py export        # -> ideation/DIGEST.md

Schema: aios.ideation.v1   Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_society import _canon, _sha256, _leaf, merkle_root  # noqa: E402

SCHEMA = "aios.ideation.v1"
ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "ideation"                 # the committed asset
STATE = ROOT / ".aios" / "ideation"       # operational cache (raw text, cursor)
LEDGER = ASSET / "ledger.jsonl"
RECEIPTS = ASSET / "receipts.jsonl"
UA = "aios-ideation/0.1 (+https://github.com/cjw0076/myworld)"

DISTILL_MODEL = os.environ.get("AIOS_IDEATION_MODEL", "qwen3:30b-a3b")
EMBED_MODEL = os.environ.get("AIOS_IDEATION_EMBED", "bge-m3")
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# Models that can all do the job, best-first. The arbiter picks whichever is
# already resident, because on this box a mismatch costs a multi-GB load: two
# calibration runs died at 25-minute timeouts over exactly this while the same
# work finished in 40 seconds on a resident model.
#
# Swapping down trades output quality for latency, and that trade is SAFE HERE
# for one specific reason: a weaker distiller does not smuggle bad rows in, it
# just gets refused more often by the verbatim-grounding oracle. The cost lands
# as a higher revert rate, which is visible — `stats` breaks reverts down per
# operator so the trade is measured rather than assumed.
DISTILL_CANDIDATES = [DISTILL_MODEL, "qwen3:8b", "qwen2.5-coder:14b",
                      "qwen2.5:7b", "qwen3:4b"]
PARAPHRASE_CANDIDATES = ["qwen3:8b", "qwen2.5:7b", "qwen2.5-coder:7b", "qwen3:4b"]


def pick_model(candidates: list[str], verbose: bool = False) -> str:
    """Host-mandated model choice. The generator is never asked which it wants.

    Wiring this in is the whole point: an arbiter nothing calls is one more
    offered mechanism, and offered mechanisms measured zero uses in 96 episodes.
    """
    try:
        import aios_gpu_arbiter as arb
        got = arb.cmd_advise(candidates, time.time())
    except Exception as exc:                      # never block work on advice
        if verbose:
            print(f"[arbiter] unavailable ({type(exc).__name__}) — "
                  f"using {candidates[0]}", flush=True)
        return candidates[0]
    if verbose:
        print(f"[arbiter] {got['choose']} ({got['reason']})", flush=True)
    return got["choose"] or candidates[0]

# Queries are derived from OUR open problems, not from a generic trend feed.
# Harvesting what is popular gives us popularity; harvesting what we are stuck
# on gives us leverage. Each entry is (label, arxiv_query, keyword_query).
TOPICS = [
    ("activation", "agent tool invocation policy enforcement",
     "agent tool use enforcement interception"),
    ("verification", "verifiable agent execution receipt attestation",
     "verifiable agent execution attestation"),
    ("memory", "agent long-term memory retrieval context",
     "agent memory context compaction"),
    ("continuity", "agent checkpoint resume context loss recovery",
     "agent context window resume checkpoint"),
    ("society", "multi-agent coordination failure handoff",
     "multi agent handoff coordination failure"),
    ("sandbox", "LLM agent sandbox capability confinement",
     "agent sandbox capability security"),
    ("selfimprove", "self-improving agent external verifier reward hacking",
     "self improving agent verifier"),
    ("os", "LLM agent operating system kernel scheduler",
     "agent operating system kernel"),
]


# ---------------------------------------------------------------------------
# fetch helpers — public endpoints only, no credentials, no repo content sent
# ---------------------------------------------------------------------------

def _get(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _norm(s: str) -> str:
    """Whitespace/case normalisation used by the grounding check.

    Deliberately conservative: it collapses runs of whitespace and lowercases,
    and nothing else. Stripping punctuation here would let a paraphrase pass,
    which is the exact failure this oracle exists to catch.
    """
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _item(kind: str, url: str, title: str, text: str) -> dict:
    body = (text or "").strip()
    return {
        "source_kind": kind,
        "url": url,
        "title": (title or "").strip(),
        "text": body,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_digest": "sha256:" + _sha256(body),
        "item_id": "src-" + _sha256(url)[:16],
    }


def harvest_arxiv(query: str, limit: int) -> list[dict]:
    q = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0, "max_results": limit,
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    raw = _get(f"http://export.arxiv.org/api/query?{q}").decode("utf-8", "replace")
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", raw, re.S):
        def tag(t):
            m = re.search(rf"<{t}>(.*?)</{t}>", entry, re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        link = re.search(r'<id>(.*?)</id>', entry, re.S)
        out.append(_item("arxiv", link.group(1).strip() if link else "",
                         tag("title"), tag("summary")))
    return out


def harvest_hn(query: str, limit: int) -> list[dict]:
    q = urllib.parse.urlencode({"query": query, "hitsPerPage": limit,
                                "tags": "story"})
    payload = json.loads(_get(f"https://hn.algolia.com/api/v1/search?{q}"))
    out = []
    for h in payload.get("hits", []):
        body = " ".join(x for x in [h.get("title"), h.get("story_text")] if x)
        if len(body) < 60:      # a bare headline carries no quotable span
            continue
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        out.append(_item("hn", url, h.get("title") or "", body))
    return out


def harvest_github(query: str, limit: int) -> list[dict]:
    q = urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc",
                                "per_page": limit})
    payload = json.loads(_get(f"https://api.github.com/search/repositories?{q}"))
    out = []
    for r in payload.get("items", []):
        body = (r.get("description") or "").strip()
        if len(body) < 60:
            continue
        out.append(_item("github", r.get("html_url") or "",
                         r.get("full_name") or "", body))
    return out


ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})")


def harvest_url(url: str) -> list[dict]:
    """Absorb one specific source the operator points at.

    The founder handing over a link is a recurring move, and a ledger that can
    only ingest its own queries would send that link to a chat message instead
    of to the record. For arXiv we go through the API rather than scraping the
    page: the grounding oracle needs the exact text the claim must quote, and
    a rendered page's whitespace and boilerplate would make a true quote fail.
    """
    m = ARXIV_ID.search(url)
    if m:
        raw = _get("http://export.arxiv.org/api/query?"
                   + urllib.parse.urlencode({"id_list": m.group(1)})
                   ).decode("utf-8", "replace")
        entry = re.search(r"<entry>(.*?)</entry>", raw, re.S)
        if not entry:
            raise ValueError(f"arXiv returned no entry for {m.group(1)}")
        body = entry.group(1)

        def tag(t):
            g = re.search(rf"<{t}>(.*?)</{t}>", body, re.S)
            return re.sub(r"\s+", " ", g.group(1)).strip() if g else ""
        return [_item("arxiv", f"https://arxiv.org/abs/{m.group(1)}",
                      tag("title"), tag("summary"))]
    html = _get(url, timeout=30.0).decode("utf-8", "replace")
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 200:
        raise ValueError(f"fetched {url} but got {len(text)} chars of text")
    return [_item("url", url, url, text[:20000])]


def harvest_peer(path: Path, sender: str, provenance: str) -> list[dict]:
    """Absorb a message another agent session sent us.

    Cross-session messaging (Claude Code v2.1.224+) carries plain text and no
    history, so a consult's substance lives only in two transcripts and dies
    with them. On 2026-08-10 four peers returned real refutations — one of them
    cut a hypothesis of mine in half — and none of it is retrievable today
    except from a conversation log. This turns a consult into a ledger row.

    The oracle applies UNCHANGED: the distiller must quote the peer's message
    verbatim, so it cannot invent an answer the peer did not give. What is
    weaker here is PROVENANCE, not grounding — if the receiver transcribes the
    message rather than capturing it at arrival, the sender's copy is the
    authoritative one and was not consulted. That is recorded per row instead
    of being smoothed over, because `transcribed_by_receiver` and
    `captured_at_arrival` are not the same evidence.
    """
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) < 120:
        raise ValueError(f"{path} holds {len(text)} chars — too short to quote")
    it = _item("peer", f"peer://{sender}", f"consult reply from {sender}", text)
    it["provenance"] = provenance
    return [it]


HARVESTERS = {"arxiv": harvest_arxiv, "hn": harvest_hn, "github": harvest_github}

# Politeness delay per source, seconds. arXiv's terms ask for roughly one
# request every 3 seconds and GitHub's unauthenticated search allows ~10/min;
# a full sweep is 8 topics x 3 sources, so firing them back-to-back would get us
# throttled and, worse, would look like an empty result rather than a refusal.
COURTESY = {"arxiv": 3.0, "github": 6.0, "hn": 0.5}


# ---------------------------------------------------------------------------
# local model calls — distillation and embedding both stay on this box
# ---------------------------------------------------------------------------

def _ollama(path: str, body: dict, timeout: float = 300.0) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA}{path}", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


DISTILL_PROMPT = """You extract ONE reusable engineering idea from a source.

Return STRICT JSON with exactly these keys:
  "claim"     : one sentence, <=280 chars, stating a mechanism or finding that
                could change how an agent system is built. No marketing.
  "falsifier" : the cheapest concrete test that would show the claim is WRONG.
                Name an observable or a command. >=20 chars.
  "evidence"  : a span COPIED VERBATIM from the SOURCE TEXT below, >=40 chars,
                that supports the claim. Copy it exactly. Do not paraphrase,
                do not fix typos, do not translate. If no span supports a real
                idea, return "claim": "" and leave the rest empty.

SOURCE TITLE: {title}
SOURCE TEXT:
{text}
"""


def distill(item: dict, model: str = DISTILL_MODEL) -> dict:
    """ACT — the host hands the item to a fixed operator.

    The model is never asked *whether* to run, and never picks the operator.
    That asymmetry is the point; see the module docstring.
    """
    prompt = DISTILL_PROMPT.format(title=item["title"][:300],
                                   text=item["text"][:6000])
    r = _ollama("/api/generate", {"model": model, "prompt": prompt,
                                  "format": "json", "stream": False,
                                  "think": False,
                                  "options": {"temperature": 0.2}})
    # Reasoning models (qwen3 family) route the answer into `thinking` and leave
    # `response` empty when thinking is on. Measured 2026-08-10: without this
    # fallback every single row came back `empty_claim` — the oracle was
    # rejecting the transport, not the content.
    raw = ((r.get("response") or "").strip()
           or (r.get("thinking") or "").strip())
    try:
        got = json.loads(raw)
    except json.JSONDecodeError:
        return {"claim": "", "falsifier": "", "evidence": "",
                "parse_error": raw[:200]}
    return {"claim": (got.get("claim") or "").strip(),
            "falsifier": (got.get("falsifier") or "").strip(),
            "evidence": (got.get("evidence") or "").strip()}


EMBED_ERROR: str | None = None      # why the last embed() gave up
EMBED_FAILED: list[dict] = []       # inputs this embedder cannot encode

# MEASURED 2026-08-10: ollama + bge-m3 returns HTTP 500
# {"error":"failed to encode response: json: unsupported value: NaN"} for some
# inputs — deterministic, reproduced on 3/3 retries for the same text. It is an
# embedder defect, not a transient. Aborting the whole batch on it would let one
# bad line silence a 400-doc corpus, so such inputs get a ZERO vector (cosine 0
# against everything, so they can never produce a false `rename`) and are
# counted. The count must be reported: a doc with a zero vector is a doc a
# harvested claim can never be found to duplicate, which inflates novelty.
NAN_MARKER = "unsupported value: NaN"


def embed(texts: list[str], model: str = EMBED_MODEL,
          allow_partial: bool = True) -> list[list[float]] | None:
    """Batch embed via ollama; None means the embedder is unavailable.

    Returning None (rather than silently falling back) matters: `dedup_method`
    is recorded per row, and a lexical row must never be mistaken for a
    semantic one. The reason is stashed in EMBED_ERROR — an embedder that
    failed must never look like an embedder that found nothing.
    """
    global EMBED_ERROR, EMBED_FAILED
    EMBED_ERROR, EMBED_FAILED = None, []

    # Fast path: ollama /api/embed takes a list. Passage-level dedup means
    # thousands of vectors, and one call per passage turns a 3-minute job into
    # half an hour. A batch that trips the NaN defect falls back to the SERIAL
    # path so one bad passage cannot void the batch.
    #
    # The fallback must be _embed_serial, NOT embed: a sub-batch of 32 is still
    # > 8, so re-entering embed() took the batch path again, failed again, and
    # recursed until `RecursionError` — which surfaced as two calibration runs
    # dying at their timeout and made vectorising the cosine maths look
    # ineffective. The cost was never in the maths; the process was spinning.
    if len(texts) > 8:
        acc, failed, ok = [], [], True
        for i in range(0, len(texts), 32):
            chunk = texts[i:i + 32]
            group = [(t or "").strip()[:2000] or " " for t in chunk]
            try:
                r = _ollama("/api/embed", {"model": model, "input": group},
                            timeout=300.0)
                vs = r.get("embeddings") or []
                if len(vs) != len(group):
                    raise ValueError("length mismatch")
                acc.extend(vs)
            except (urllib.error.URLError, OSError, json.JSONDecodeError,
                    ValueError):
                sub = _embed_serial(chunk, model, allow_partial)
                if sub is None:
                    ok = False
                    break
                failed.extend({**b, "index": b["index"] + i}
                              for b in EMBED_FAILED)
                acc.extend(sub)
        if ok and len(acc) == len(texts):
            EMBED_FAILED = failed
            if failed:
                EMBED_ERROR = (f"{len(failed)}/{len(texts)} inputs "
                               f"unembeddable (zero-vectored)")
            return acc
        EMBED_FAILED = failed

    return _embed_serial(texts, model, allow_partial)


def _embed_serial(texts: list[str], model: str,
                  allow_partial: bool) -> list[list[float]] | None:
    """One call per text. Slow, but it isolates a single poisoned input."""
    global EMBED_ERROR, EMBED_FAILED
    EMBED_ERROR, EMBED_FAILED = None, []
    out, dim = [], None
    for n, t in enumerate(texts):
        body = (t or "").strip()[:2000]
        if not body:
            EMBED_ERROR = f"text[{n}] empty after strip"
            return None
        last, vec = None, None
        for attempt in range(3):
            try:
                r = _ollama("/api/embed", {"model": model, "input": body},
                            timeout=180.0)
                vec = (r.get("embeddings") or [None])[0]
                if vec is None:
                    r = _ollama("/api/embeddings",
                                {"model": model, "prompt": body}, timeout=180.0)
                    vec = r.get("embedding")
                if vec:
                    dim = dim or len(vec)
                    break
                last = "empty vector in response"
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:200]
                except OSError:
                    pass
                last = f"HTTP {exc.code}: {detail}"
                if NAN_MARKER in detail:
                    break          # deterministic defect — retrying is waste
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                last = f"{type(exc).__name__}: {exc}"[:160]
            time.sleep(1.5 * (attempt + 1))
        if vec:
            out.append(vec)
            continue
        EMBED_FAILED.append({"index": n, "reason": (last or "")[:120],
                             "head": body[:70]})
        if not allow_partial or dim is None:
            EMBED_ERROR = f"text[{n}]: {last}"
            return None
        out.append([0.0] * dim)    # cosine 0 — can never fake a match
    if EMBED_FAILED:
        EMBED_ERROR = (f"{len(EMBED_FAILED)}/{len(texts)} inputs unembeddable "
                       f"(zero-vectored): {EMBED_FAILED[0]['reason'][:60]}")
    return out


def _cos(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return num / (na * nb) if na and nb else 0.0


def _trigrams(s: str) -> set[str]:
    s = _norm(s)
    return {s[i:i + 3] for i in range(max(0, len(s) - 2))}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    return len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0


# ---------------------------------------------------------------------------
# our corpus — what "we already said this" is measured against
# ---------------------------------------------------------------------------

def load_corpus(limit_files: int = 400, chunk: int = 700,
                per_doc: int = 6) -> list[dict]:
    """Our docs, cut into PASSAGES — the unit a claim is compared against.

    Measured 2026-08-10: embedding each doc as one 1200-char gist made the
    dedup useless (Youden J = 0.52 — our own sentences scored 0.58 against our
    corpus while unrelated protein-crystallography abstracts scored 0.50). A
    one-sentence claim and a whole document are different granularities, and a
    document vector is an average that washes out the specific idea. Passages
    fix the mismatch; the calibration re-run is what says whether they did.
    """
    out = []
    for p in sorted((ROOT / "docs").rglob("*.md"))[:limit_files]:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        head = re.search(r"^#\s+(.+)$", txt, re.M)
        title = head.group(1).strip() if head else p.stem
        body = re.sub(r"```.*?```", " ", txt, flags=re.S)
        body = re.sub(r"\s+", " ", body).strip()
        rel = str(p.relative_to(ROOT))
        for i in range(0, min(len(body), chunk * per_doc), chunk):
            seg = body[i:i + chunk]
            if len(seg) < 120:
                break
            out.append({"path": rel, "title": title, "gist": seg,
                        "offset": i})
    return out


def corpus_vectors(corpus: list[dict]) -> list[list[float]] | None:
    """Embed the corpus once and cache it, keyed by the corpus content."""
    STATE.mkdir(parents=True, exist_ok=True)
    key = _sha256(_canon([c["path"] + str(c.get("offset")) + c["gist"][:120]
                          for c in corpus]))
    cache = STATE / f"corpus_emb_{key[:16]}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text())
        except json.JSONDecodeError:
            pass
    vecs = embed([f"{c['title']}\n{c['gist']}" for c in corpus])
    if vecs is not None:
        cache.write_text(json.dumps(vecs))
    return vecs


# REMOVED 2026-08-10: a `calibrate_threshold()` that took the p95 of our
# corpus's own nearest-neighbour similarity. It read plausibly ("as close as our
# own docs are to each other") but measured the wrong thing — our docs are all
# about one subject, so it returned 0.9119 while real harvested claims scored
# 0.5-0.65, i.e. it would have flagged nothing, ever. Replaced by cmd_calibrate,
# which measures the cut against a positive and a negative control instead of
# deriving it from the corpus alone.


# A field far enough from ours that a high similarity would be an artifact of
# the embedder, not of shared content. Used as the negative control below.
NEG_QUERY = "protein crystallography diffraction phase retrieval"


def _doc_sentences(path: Path, after: int = 1200) -> list[str]:
    """Sentences from deep inside a doc — past the part we embedded as its gist.

    Drawing the positive control from text the corpus vector never saw is what
    makes it a fair 'same idea, different words' probe instead of a tautology.
    """
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")[after:]
    except OSError:
        return []
    txt = re.sub(r"```.*?```", " ", txt, flags=re.S)
    txt = re.sub(r"[|#*`>\-]+", " ", txt)
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+|\n\n", txt)
            if 60 <= len(s.strip()) <= 280]


PARAPHRASE_PROMPT = """Restate the SENTENCE with the same meaning in different
words. Rules: do not reuse any run of 5+ consecutive words from it; keep every
technical term that has no synonym; one sentence; no commentary.
Return STRICT JSON: {{"restated": "..."}}

SENTENCE: {s}
"""


# Restating one sentence does not need the distiller's capacity, and using the
# big model here is actively harmful: it is not resident, so every call pays a
# model swap. Measured 2026-08-10 — 40 paraphrases had not finished in 30
# minutes on qwen3:30b-a3b.
PARAPHRASE_MODEL = os.environ.get("AIOS_IDEATION_PARAPHRASE", "qwen3:8b")


def _paraphrase(sentence: str, model: str | None = None) -> str:
    model = model or PARAPHRASE_MODEL
    try:
        r = _ollama("/api/generate",
                    {"model": model, "prompt": PARAPHRASE_PROMPT.format(s=sentence),
                     "format": "json", "stream": False, "think": False,
                     "options": {"temperature": 0.7}}, timeout=180.0)
        raw = ((r.get("response") or "").strip()
               or (r.get("thinking") or "").strip())
        out = (json.loads(raw).get("restated") or "").strip()
        # A "paraphrase" that copied the sentence would inflate the positive
        # scores and make the dedup look better than it is.
        return "" if _norm(out) == _norm(sentence) else out
    except (urllib.error.URLError, OSError, json.JSONDecodeError,
            AttributeError, TypeError):
        return ""


def cmd_calibrate(n_pos: int = 40, n_neg: int = 40,
                  verbose: bool = True) -> dict:
    """Measure the dedup threshold instead of declaring it.

    positive = a sentence we wrote, from a part of a doc the corpus vector did
               not include -> the score a genuine restatement earns
    negative = abstracts from an unrelated field -> the score unrelated text
               earns from this embedder

    The cut is the value that maximises (TPR - FPR). If the two distributions
    overlap badly, that is reported, not smoothed over: an unseparated pair
    means this embedder cannot tell 'we already said this' from 'we did not',
    and the `rename` verdict should not be trusted.
    """
    corpus = load_corpus()
    vecs = corpus_vectors(corpus)
    if vecs is None:
        return {"error": "embedder unavailable — cannot calibrate",
                "detail": EMBED_ERROR}
    # The positive control must be a PARAPHRASE, not the original sentence.
    # Matching a doc's own words back to itself measures plagiarism detection;
    # what we need to know is whether an outside claim that says the same thing
    # in different words gets caught. So a local model restates our sentences
    # and those restatements are the positives.
    originals, done = [], set()
    for c in corpus:
        if len(originals) >= n_pos:
            break
        if c["path"] in done:
            continue
        sents = _doc_sentences(ROOT / c["path"])
        if sents:
            originals.append(sents[len(sents) // 2])
            done.add(c["path"])
    # Instrumented on purpose. Two calibration runs died at their 1500s
    # timeout and vectorising the cosine maths did not help, which means the
    # cost was never where it was assumed to be. Guessing again would be a
    # third wasted run, so the loop now says where the time goes.
    para_model = pick_model(PARAPHRASE_CANDIDATES, verbose=verbose)
    pos_texts, t_para = [], time.time()
    for n, s in enumerate(originals, 1):
        t1 = time.time()
        p = _paraphrase(s, para_model)
        if p:
            pos_texts.append(p)
        if verbose:
            print(f"  [paraphrase {n:>2}/{len(originals)}] "
                  f"{round(time.time() - t1, 1)}s "
                  f"{'ok' if p else 'EMPTY'}", flush=True)
    if verbose:
        print(f"  paraphrase total {round(time.time() - t_para, 1)}s "
              f"({len(pos_texts)}/{len(originals)} usable)", flush=True)
    neg_items = harvest_arxiv(NEG_QUERY, n_neg)
    neg_texts = [f"{i['title']}. {i['text'][:400]}" for i in neg_items]
    pv = embed(pos_texts)
    pv_bad = list(EMBED_FAILED)
    nv = embed(neg_texts)
    nv_bad = list(EMBED_FAILED)
    if pv is None or nv is None:
        return {"error": "embedding failed mid-calibration",
                "positive_error": EMBED_ERROR}
    # A zero-vectored control would score 0 and drag the distribution, so drop
    # those samples from the statistics rather than let them bias the cut.
    bad_p = {b["index"] for b in pv_bad}
    bad_n = {b["index"] for b in nv_bad}
    M = _as_matrix(vecs)
    pos = sorted(_peak_z(v, vecs, M)[1] for i, v in enumerate(pv) if i not in bad_p)
    neg = sorted(_peak_z(v, vecs, M)[1] for i, v in enumerate(nv) if i not in bad_n)

    lo, hi = min(pos + neg), max(pos + neg)
    best, best_j = lo, -1.0
    for cut in [lo + (hi - lo) * i / 400 for i in range(401)]:
        tpr = sum(1 for p in pos if p >= cut) / max(1, len(pos))
        fpr = sum(1 for n in neg if n >= cut) / max(1, len(neg))
        if tpr - fpr > best_j:
            best_j, best = tpr - fpr, cut

    def q(xs, p):
        return round(xs[int(p * (len(xs) - 1))], 4) if xs else None
    out = {"schema": "aios.ideation.calibration.v1",
           "statistic": "peak-z (max cosine, z-scored against the claim's own "
                        "similarity distribution over the whole corpus)",
           "embedder": EMBED_MODEL, "corpus_docs": len(corpus),
           "corpus_passages": len(corpus),
           "positive": {"n": len(pos), "p05": q(pos, .05), "p50": q(pos, .5),
                        "p95": q(pos, .95),
                        "source": ("local-model PARAPHRASES of sentences from "
                                   "our docs (past char 1200) — same idea, "
                                   "different words")},
           "negative": {"n": len(neg), "p05": q(neg, .05), "p50": q(neg, .5),
                        "p95": q(neg, .95), "source": f"arxiv: {NEG_QUERY}"},
           "threshold": best, "youden_j": round(best_j, 4),
           "separated": best_j >= 0.8,
           "unembeddable": {"positive": len(pv_bad), "negative": len(nv_bad),
                            "cause": (pv_bad or nv_bad or [{}])[0].get("reason"),
                            "effect": ("dropped from the statistics; in the "
                                       "corpus they become zero vectors, which "
                                       "can only inflate novelty, never fake a "
                                       "duplicate")},
           "note": ("youden_j < 0.8 means the distributions overlap: the "
                    "`rename` verdict is then weak evidence, not a finding")}
    ASSET.mkdir(parents=True, exist_ok=True)
    (ASSET / "calibration.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def load_calibration() -> dict | None:
    p = ASSET / "calibration.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_threshold() -> tuple[float | None, bool]:
    """(threshold, trusted). `trusted` is False unless the calibration that
    produced the threshold actually separated its two controls — a threshold
    from an unseparated calibration is a number, not a decision boundary."""
    c = load_calibration()
    if not c:
        return None, False
    try:
        return float(c["threshold"]), bool(c.get("separated"))
    except (KeyError, ValueError, TypeError):
        return None, False


def _as_matrix(vecs):
    """Unit-normalised corpus matrix, numpy if available.

    Pure Python cost this: a full calibration is ~80 samples x ~2100 passages x
    1024 dims, which timed out at 1500s on 2026-08-10. numpy turns it into one
    matmul. The stdlib path is kept because this module is otherwise dependency
    -free and must still run in a bare wheel — it is slower, not different.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    m = np.asarray(vecs, dtype="float32")
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n < 1e-9] = 1.0
    return m / n


def _peak_z(claim_vec, vecs, matrix=None) -> tuple[float, float, int]:
    """(raw max, z-score of the max against its own background, argmax).

    Why z and not the raw max: the max over ~2000 passages is a tail statistic,
    so even unrelated text scores respectably just by sampling. Measured
    2026-08-10 — raw-max separation of our own paraphrases from protein
    crystallography abstracts was only 0.63 vs 0.52 (Youden J 0.57). The
    question that actually matters is not "how close is the best match" but
    "does the best match STAND OUT from this claim's own background", which is
    exactly a z-score and is invariant to how big the corpus is.
    """
    if matrix is not None:
        import numpy as np
        v = np.asarray(claim_vec, dtype="float32")
        nrm = float(np.linalg.norm(v))
        if nrm < 1e-9:
            return 0.0, 0.0, 0
        sims = matrix @ (v / nrm)
        i = int(sims.argmax())
        top, mean, sd = float(sims[i]), float(sims.mean()), float(sims.std())
        return top, ((top - mean) / sd if sd > 1e-9 else 0.0), i
    sims = [_cos(claim_vec, w) for w in vecs]
    if not sims:
        return 0.0, 0.0, 0
    top = max(sims)
    i = sims.index(top)
    mean = sum(sims) / len(sims)
    var = sum((s - mean) ** 2 for s in sims) / len(sims)
    sd = var ** 0.5
    return top, ((top - mean) / sd if sd > 1e-9 else 0.0), i


def nearest(claim: str, corpus: list[dict], vecs, claim_vec, matrix=None) -> dict:
    if vecs is not None and claim_vec is not None:
        top, z, i = _peak_z(claim_vec, vecs, matrix)
        return {"method": f"embed:{EMBED_MODEL}/peak-z", "similarity": round(z, 4),
                "raw_max_cosine": round(top, 4),
                "path": corpus[i]["path"], "title": corpus[i]["title"]}
    sims = [(_jaccard(claim, c["title"] + " " + c["gist"][:400]), i)
            for i, c in enumerate(corpus)]
    s, i = max(sims) if sims else (0.0, 0)
    return {"method": "lexical:trigram-jaccard", "similarity": round(s, 4),
            "path": corpus[i]["path"] if corpus else None,
            "title": corpus[i]["title"] if corpus else None}


# ---------------------------------------------------------------------------
# VERIFY — deterministic, and blind to who generated the claim
# ---------------------------------------------------------------------------

# --- falsifier_exec (2026-08-13) -------------------------------------------
# MEASURED by the base layer against this very ledger: of 49 rows, **0** carried
# a falsifier that could be executed as authored. Every one was a natural-language
# experiment sketch pointing at something outside this machine — a chemist, a
# web-scale corpus, a physical 2D magnet, a search that is self-contained in
# theory and infeasible in practice. It refused to have a model translate them,
# which was right: a generator writing its own test is the thing our null report
# says does not work.
#
# So the compounding loop does not light until falsifiers are BORN executable,
# and that is a property of the row, not of the executor. This field is how a row
# says it can be run:
#
#   "falsifier_exec": {"cmd": [...], "ro": [...], "net_decoy": false}
#       exit 3 -> the claim survived the attempt  -> Attested
#       exit 0 -> the claim was killed            -> Refuted
#
# OPTIONAL on purpose. Requiring it would refuse every row harvested from an
# abstract, which would not make those falsifiers executable — it would only stop
# us recording that they exist. What must NOT happen is calling such a row part
# of a compounding loop, so `liftable` states the difference and `stats` reports
# the fraction, turning a one-off finding into a standing metric.
EXEC_KEYS = ("cmd",)


def falsifier_exec_ok(row: dict) -> bool:
    fx = row.get("falsifier_exec")
    if not isinstance(fx, dict):
        return False
    cmd = fx.get("cmd")
    return isinstance(cmd, list) and bool(cmd) and all(isinstance(c, str) for c in cmd)


def liftable(row: dict) -> bool:
    """Can this row ever leave Proposal?

    A row whose falsifier is prose cannot be raised by any amount of execution,
    and saying so is the honest alternative to either discarding it or pretending
    it participates.
    """
    return falsifier_exec_ok(row)


MIN_EVIDENCE = 40
MIN_FALSIFIER = 20
MAX_CLAIM = 280
# UNCALIBRATED, and labelled as such on every row that uses it. The lexical path
# only runs when the embedder is unavailable; there is no measurement behind
# this number, so a `rename` from the lexical path is a hint, not a finding.
LEXICAL_RENAME_THRESHOLD = 0.45
# Used when no calibration file exists. Deliberately high: with no measured cut
# the safe error is to call everything `novel` (an unflagged duplicate wastes a
# human's minute) rather than to suppress real finds as renames.
UNCALIBRATED_Z = 3.5


def verify(item: dict, prop: dict, near: dict, threshold: float,
           dedup_trusted: bool = False) -> dict:
    """The oracle. It never calls a model and never sees the generator's name.

    `dedup_trusted` is what stops this function from making a claim it cannot
    back. MEASURED 2026-08-10, three ways, on 2127 passages of our own docs
    (positives = local-model paraphrases of our sentences, negatives = an
    unrelated field):

        raw max cosine, document-level gist   Youden J = 0.5167
        raw max cosine, passage-level         Youden J = 0.5673
        peak-z, passage-level                 Youden J = 0.4476

    None separates. So the verdict for a well-formed row is `grounded` — the
    quote is real and a falsifier is present — and NOT `novel`, because we
    cannot currently tell "nobody here said this" from "our embedder cannot
    see that we did". `novel`/`rename` are only emitted when a calibration
    with separated=true exists.
    """
    reasons = []
    claim, ev, fal = prop.get("claim", ""), prop.get("evidence", ""), prop.get("falsifier", "")
    if not claim:
        reasons.append("empty_claim")
    if len(claim) > MAX_CLAIM:
        reasons.append(f"claim_too_long:{len(claim)}")
    if len(ev) < MIN_EVIDENCE:
        reasons.append(f"evidence_too_short:{len(ev)}")
    elif _norm(ev) not in _norm(item["text"]):
        # THE check: a paraphrase, a translation, or an invention dies here.
        reasons.append("evidence_not_verbatim_in_source")
    if len(fal) < MIN_FALSIFIER:
        reasons.append(f"falsifier_missing:{len(fal)}")
    # The embed path scores in z units and the lexical path in Jaccard units;
    # one threshold cannot serve both, and silently applying the z cut to a
    # Jaccard score would mean the lexical path never fires at all.
    cut = threshold if str(near.get("method", "")).startswith("embed") \
        else LEXICAL_RENAME_THRESHOLD
    if not dedup_trusted:
        verdict = "grounded"
    elif near.get("similarity", 0.0) >= cut:
        verdict = "rename"
    else:
        verdict = "novel"
    return {
        "oracle": "grounding_v1",
        "verifier_identity": "aios_ideation.verify (deterministic code)",
        "checks": {"verbatim_evidence": "evidence_not_verbatim_in_source" not in reasons,
                   "falsifier_present": not any(r.startswith("falsifier") for r in reasons),
                   "claim_bounded": not any(r.startswith("claim") for r in reasons)},
        "reasons": reasons,
        "dedup": near, "dedup_threshold": threshold,
        "dedup_trusted": dedup_trusted,
        "novelty_assessed": dedup_trusted,
        "pass": not reasons, "verdict": "reverted" if reasons else verdict,
    }


# ---------------------------------------------------------------------------
# ledger — append-only, position-salted Merkle root (same shape as arc ledger)
# ---------------------------------------------------------------------------

def _append(path: Path, rec: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    seq = sum(1 for _ in path.open(encoding="utf-8")) if path.exists() else 0
    rec = dict(rec, seq=seq)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(_canon(rec) + "\n")
    return seq


def ledger_root(path: Path | None = None) -> str:
    # Resolved at CALL time, never bound as a default: a default argument would
    # freeze the module-level LEDGER at import, so any caller that redirects the
    # ledger (tests, a second asset dir) would silently hash the wrong file and
    # report root_before == root_after. Found by the M0 receipt test.
    path = LEDGER if path is None else path
    if not path.exists():
        return merkle_root([])
    leaves = [_leaf(i, ln.rstrip("\n"))
              for i, ln in enumerate(path.open(encoding="utf-8"))]
    return merkle_root(leaves)


def seen_ids(path: Path | None = None) -> set[str]:
    path = LEDGER if path is None else path
    if not path.exists():
        return set()
    out = set()
    for ln in path.open(encoding="utf-8"):
        try:
            out.add(json.loads(ln).get("item_id"))
        except json.JSONDecodeError:
            continue
    return out - {None}


# ---------------------------------------------------------------------------
# the cycle
# ---------------------------------------------------------------------------

def run_cycle(sources: list[str], topics: list[str], limit: int,
              per_source: int, threshold_arg: str, model: str,
              verbose: bool = True, urls: list[str] | None = None,
              items: list[dict] | None = None) -> dict:
    t0 = time.time()
    known = seen_ids()

    # --- SENSE: a deterministic predicate over source state. No model. -------
    fetched, errors = list(items or []), []
    for u in (urls or []):
        try:
            fetched.extend(harvest_url(u))
        except (urllib.error.URLError, OSError, json.JSONDecodeError,
                ValueError) as exc:
            errors.append({"source": "url", "topic": u,
                           "error": f"{type(exc).__name__}: {exc}"[:160]})
    for label, aq, kq in TOPICS:
        if (urls or items) and not topics and not sources:
            break
        if topics and label not in topics:
            continue
        for src in sources:
            try:
                got = HARVESTERS[src](aq if src == "arxiv" else kq, per_source)
                fetched.extend(got)
                time.sleep(COURTESY.get(src, 1.0))
            except (urllib.error.URLError, OSError, json.JSONDecodeError,
                    ValueError) as exc:
                # A source that failed is NOT a source that found nothing.
                errors.append({"source": src, "topic": label,
                               "error": f"{type(exc).__name__}: {exc}"[:160]})
    by_id = {}
    for it in fetched:
        by_id.setdefault(it["item_id"], it)
    fresh = [it for k, it in by_id.items() if k not in known][:limit]
    sense = {"predicate": "source_items_newer_than_ledger",
             "evaluated_by": "policy", "model_consulted": False,
             "candidates": len(by_id), "fresh": len(fresh),
             "source_errors": errors}
    if verbose:
        print(f"[sense] {len(by_id)} candidates, {len(fresh)} unseen, "
              f"{len(errors)} source errors")
    if errors and verbose:
        for e in errors[:4]:
            print(f"        ! {e['source']}/{e['topic']}: {e['error'][:70]}")
    if not fresh:
        return {"schema": SCHEMA, "sense": sense, "settled": [],
                "note": "no fresh items — nothing to absorb this cycle"}

    corpus = load_corpus()
    vecs = corpus_vectors(corpus)
    matrix = _as_matrix(vecs) if vecs is not None else None
    if threshold_arg == "auto":
        # Prefer a MEASURED cut (positive/negative controls) over the corpus
        # self-similarity fallback. The fallback is conservative by
        # construction — our docs are all about one subject, so their mutual
        # similarity is high and almost nothing outside gets flagged.
        measured, trusted = load_threshold()
        threshold = measured if measured is not None else UNCALIBRATED_Z
        tsrc = ("calibrated+separated" if trusted else
                ("calibrated but NOT separated" if measured is not None
                 else "UNCALIBRATED"))
    else:
        threshold, trusted, tsrc = float(threshold_arg), False, "explicit"
    if verbose:
        print(f"[dedup] corpus={len(corpus)} docs, method="
              f"{'embed' if vecs else 'lexical (embedder unavailable)'}, "
              f"threshold={threshold} ({tsrc})")

    settled = []
    for n, item in enumerate(fresh, 1):
        # --- ACT: fixed operator, host-invoked ------------------------------
        t1 = time.time()
        prop = distill(item, model)
        act = {"operator": f"distill@{model}", "invoked_by": "host",
               "model_offered_choice": False,
               "operator_digest": "sha256:" + _sha256(DISTILL_PROMPT + model),
               "wall_s": round(time.time() - t1, 2)}

        # --- VERIFY: deterministic, generator-blind --------------------------
        cvec = None
        if vecs is not None and prop.get("claim"):
            got = embed([prop["claim"]])
            cvec = got[0] if got else None
        near = nearest(prop.get("claim", ""), corpus, vecs, cvec, matrix)
        ver = verify(item, prop, near, threshold, trusted)

        # --- SETTLE: committed or reverted; both change the root -------------
        root_before = ledger_root()
        rec = {"schema": SCHEMA, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "item_id": item["item_id"], "source": {
                   "kind": item["source_kind"], "url": item["url"],
                   "title": item["title"], "digest": item["source_digest"],
                   **({"provenance": item["provenance"]}
                      if "provenance" in item else {})},
               "claim": prop.get("claim", ""), "falsifier": prop.get("falsifier", ""),
               "evidence": prop.get("evidence", ""),
               "epistemic_type": "Proposal",   # only a run receipt raises this
               "verdict": ver["verdict"], "oracle": ver}
        seq = _append(LEDGER, rec)
        root_after = ledger_root()
        receipt = {
            "schema": "aios.minimal_operation.v1", "cycle": "ideation_absorb",
            "sense": {"predicate": sense["predicate"], "evaluated_by": "policy",
                      "input_digest": item["source_digest"],
                      "model_consulted": False},
            "act": {"operator": act["operator"], "invoked_by": "host",
                    "model_offered_choice": False,
                    "operator_digest": act["operator_digest"],
                    # The distiller returns TEXT over HTTP and runs nothing of
                    # ours, so the verifier sharing this process is safe. Stated
                    # rather than assumed: the day a falsifier is executed this
                    # flips to true and spec 2b refuses `same_process`.
                    "executes_code": False},
            "verify": {"oracle_cmd_digest": "sha256:" + _sha256("grounding_v1"),
                       "verdict": "pass" if ver["pass"] else "fail",
                       "verifier_identity": ver["verifier_identity"],
                       "isolation": "same_process"},
            "settle": {"outcome": "committed" if ver["pass"] else "reverted",
                       "ledger_seq": seq, "root_before": root_before,
                       "root_after": root_after},
        }
        _append(RECEIPTS, receipt)
        settled.append({"item_id": item["item_id"], "verdict": ver["verdict"],
                        "similarity": near.get("similarity"),
                        "claim": prop.get("claim", "")[:110]})
        if verbose:
            mark = {"novel": "NOVEL ", "rename": "rename",
                    "grounded": "ground", "reverted": "REVERT"}[ver["verdict"]]
            why = "" if ver["pass"] else " <- " + ",".join(ver["reasons"][:2])
            print(f"  [{n:>2}/{len(fresh)}] {mark} sim={near.get('similarity'):.3f} "
                  f"{item['source_kind']:<6} {prop.get('claim','')[:64]}{why}")

    counts = {}
    for s in settled:
        counts[s["verdict"]] = counts.get(s["verdict"], 0) + 1
    return {"schema": SCHEMA, "sense": sense, "settled": settled,
            "counts": counts, "wall_s": round(time.time() - t0, 1),
            "ledger_root": ledger_root()}


# ---------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------

def read_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for ln in LEDGER.open(encoding="utf-8"):
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def read_receipts() -> list[dict]:
    if not RECEIPTS.exists():
        return []
    out = []
    for ln in RECEIPTS.open(encoding="utf-8"):
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def cmd_stats() -> dict:
    rows = read_ledger()
    by_verdict, by_source = {}, {}
    for r in rows:
        by_verdict[r.get("verdict")] = by_verdict.get(r.get("verdict"), 0) + 1
        k = (r.get("source") or {}).get("kind")
        by_source[k] = by_source.get(k, 0) + 1
    reverted = by_verdict.get("reverted", 0)
    lift = sum(1 for r in rows if liftable(r))
    # Per-operator revert rate: the arbiter is allowed to swap in a smaller
    # distiller, so the price of that swap has to be visible here rather than
    # taken on trust.
    per_model: dict[str, dict] = {}
    for rec in read_receipts():
        op = rec.get("act", {}).get("operator", "?")
        d = per_model.setdefault(op, {"cycles": 0, "reverted": 0})
        d["cycles"] += 1
        if rec.get("settle", {}).get("outcome") == "reverted":
            d["reverted"] += 1
    for d in per_model.values():
        d["revert_rate"] = round(d["reverted"] / d["cycles"], 3) if d["cycles"] else None
    return {"schema": SCHEMA, "rows": len(rows), "by_verdict": by_verdict,
            "by_source": by_source, "by_operator": per_model,
            "liftable": lift, "liftable_fraction": round(lift / len(rows), 3) if rows else None,
            "liftable_note": ("rows that can ever leave Proposal, i.e. that carry "
                              "a runnable falsifier_exec. Measured 0/49 on "
                              "2026-08-13: the compounding loop is not lit, and "
                              "a ledger of unliftable rows is an archive"),
            "ledger_root": ledger_root(),
            "revert_ever_executed": reverted > 0,
            "note": ("revert_ever_executed=false means the rejection path is "
                     "code that has never run — do not call the cycle proven")}


def cmd_export() -> Path:
    rows = read_ledger()
    novel = [r for r in rows if r.get("verdict") == "novel"]
    rename = [r for r in rows if r.get("verdict") == "rename"]
    rev = [r for r in rows if r.get("verdict") == "reverted"]
    L = []
    L.append("# Ideation asset — absorbed, grounded, deduped\n")
    L.append(f"*generated by `scripts/aios_ideation.py export` · rows={len(rows)} "
             f"· root=`{ledger_root()[:23]}…`*\n")
    L.append("Every row below survived a **verbatim grounding check** (the quoted "
             "span appears byte-for-byte in the fetched source) and carries a "
             "**falsifier**. `novel` means it was not already close to something "
             "in `docs/`; it does **not** mean the claim is true — "
             "`epistemic_type` stays `Proposal` until a run receipt raises it.\n")
    L.append(f"\n## Novel to us ({len(novel)})\n")
    for r in novel:
        s = r.get("source", {})
        L.append(f"- **{r.get('claim')}**  \n"
                 f"  ↳ falsifier: {r.get('falsifier')}  \n"
                 f"  ↳ source: [{s.get('title','')[:80]}]({s.get('url')}) "
                 f"({s.get('kind')}) · nearest ours: "
                 f"`{(r.get('oracle',{}).get('dedup',{}) or {}).get('path')}` "
                 f"@{(r.get('oracle',{}).get('dedup',{}) or {}).get('similarity')}")
    L.append(f"\n## Already ours, under another name ({len(rename)})\n")
    for r in rename[:40]:
        d = (r.get("oracle", {}).get("dedup", {}) or {})
        L.append(f"- {r.get('claim')[:150]} → `{d.get('path')}` @{d.get('similarity')}")
    L.append(f"\n## Rejected by the oracle ({len(rev)})\n")
    L.append("These are the cycle's teeth: claims the distiller produced that "
             "could not be grounded in the source it was given.\n")
    for r in rev[:40]:
        L.append(f"- `{','.join(r.get('oracle',{}).get('reasons',[])[:3])}` — "
                 f"{(r.get('claim') or '(empty)')[:110]}")
    ASSET.mkdir(parents=True, exist_ok=True)
    out = ASSET / "DIGEST.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="one full SENSE→ACT→VERIFY→SETTLE cycle")
    r.add_argument("--sources", default="arxiv,hn,github")
    r.add_argument("--topics", default="", help="comma list; default = all")
    r.add_argument("--limit", type=int, default=12, help="items to absorb")
    r.add_argument("--per-source", type=int, default=6)
    r.add_argument("--threshold", default="auto",
                   help="'auto' = p95 of our corpus self-similarity")
    r.add_argument("--model", default=None,
                   help="pin a distiller; default = whichever candidate the "
                        "arbiter reports resident")
    r.add_argument("--url", action="append", default=[],
                   help="absorb this specific source (repeatable)")
    r.add_argument("--json", action="store_true")
    pr = sub.add_parser("peer", help="absorb a peer session's reply")
    pr.add_argument("--from", dest="sender", required=True,
                    help="the peer session name, e.g. quantum-3e")
    pr.add_argument("--text-file", type=Path, required=True,
                    help="file holding the message text VERBATIM")
    pr.add_argument("--provenance", default="transcribed_by_receiver",
                    choices=["captured_at_arrival", "transcribed_by_receiver"],
                    help="how the text got into that file; they are not the "
                         "same evidence and the row says which")
    pr.add_argument("--model", default=None)
    pr.add_argument("--json", action="store_true")
    c = sub.add_parser("calibrate", help="measure the dedup threshold")
    c.add_argument("--n-pos", type=int, default=40)
    c.add_argument("--n-neg", type=int, default=40)
    c.add_argument("--quiet", action="store_true")
    sub.add_parser("stats", help="what the asset holds")
    sub.add_parser("export", help="render ideation/DIGEST.md")
    v = sub.add_parser("verify-ledger", help="recompute the Merkle root")
    v.add_argument("--expect", default=None)
    a = ap.parse_args(argv)

    if a.cmd == "run":
        # --url alone means "just this source": do not also sweep the topics.
        srcs = [] if (a.url and a.sources == "arxiv,hn,github") else \
            [s for s in a.sources.split(",") if s in HARVESTERS]
        model = a.model or pick_model(DISTILL_CANDIDATES, verbose=not a.json)
        res = run_cycle(
            srcs, [t for t in a.topics.split(",") if t], a.limit,
            a.per_source, a.threshold, model, verbose=not a.json,
            urls=a.url)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print(f"\ncounts={res.get('counts')} root={res.get('ledger_root','')[:23]}…")
        return 0
    if a.cmd == "peer":
        model = a.model or pick_model(DISTILL_CANDIDATES, verbose=not a.json)
        got = harvest_peer(a.text_file, a.sender, a.provenance)
        res = run_cycle([], [], 1, 1, "auto", model, verbose=not a.json,
                        items=got)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print(f"\ncounts={res.get('counts')} "
                  f"root={res.get('ledger_root','')[:23]}…")
        return 0
    if a.cmd == "calibrate":
        print(json.dumps(cmd_calibrate(a.n_pos, a.n_neg, not a.quiet),
                         ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "stats":
        print(json.dumps(cmd_stats(), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "export":
        print(cmd_export())
        return 0
    if a.cmd == "verify-ledger":
        got = ledger_root()
        print(got)
        return 0 if (a.expect is None or got == a.expect) else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
