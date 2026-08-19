"""M2 arm B — best-effort CONVENTIONAL cache / materialization.

Independent strong control for the memory-as-computation prereg (M2). Built from
prereg prose only; imports none of the peer's aios_* / memoryOS code. The peer's
`compare` invokes this as an external subprocess (referee pattern).

Prereg's own definition of B: "내용주소 캐시 + 프롬프트 캐시 + 정적 인덱스". This
module implements exactly that, with the two guards the independent-implementer
review demanded (see README):

  - version-keyed invalidation  -> B never serves a stale wrong answer, so it
    passes Gate 1 (capability non-inferiority) cleanly instead of losing it and
    handing C an unfair win.
  - answer reuse is EXACT-K only. Near-match (the static index) accelerates the
    *search* half of f; the model still computes on retrieved context, so a
    near neighbour's answer is never substituted for a different question.

K is treated as an opaque structured value until the peer supplies the
operational legitimate-K definition (contract item 5). The fixed model call is
an injected `compute_fn` (contract item 2) so this core is model-agnostic and
unit-testable without a GPU.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional


# --------------------------------------------------------------------------- #
# Canonicalisation + content-addressing
# --------------------------------------------------------------------------- #

def canonical(obj) -> str:
    """Stable canonical string for any JSON-able K. Order-independent for dicts."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_key(k, dep_versions: Optional[dict] = None, corpus_version: str = "") -> str:
    """Content address over (legitimate K, the versions it depends on).

    Invalidation is *in the key*: if a depended-on doc changes, its version
    changes, the key changes, the old entry can never be hit -> no stale serve.
    `dep_versions` (per-dependency {doc_id: version}) is the precise form (CDN /
    build-cache standard); `corpus_version` is the coarse fallback when the
    caller cannot enumerate dependencies.
    """
    deps = canonical(dep_versions or {})
    payload = canonical(k) + "\x1f" + deps + "\x1f" + corpus_version
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Static index (BM25) — materialises the expensive-search half of f
# --------------------------------------------------------------------------- #

_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class StaticIndex:
    """Deterministic BM25 over the corpus, built once and reused across queries.

    This is the prereg's "정적 인덱스": the search work is materialised, not
    recomputed per query. Retrieval is cheap (no model). Correctness is not at
    risk here — the model still runs on whatever this returns.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self._docs: dict[str, list[str]] = {}
        self._df: Counter = Counter()
        self._postings: dict[str, dict[str, int]] = defaultdict(dict)
        self._len: dict[str, int] = {}
        self._avglen = 0.0

    def add(self, doc_id: str, text: str) -> None:
        toks = _tok(text)
        self._docs[doc_id] = toks
        tf = Counter(toks)
        self._len[doc_id] = len(toks)
        for term, c in tf.items():
            self._postings[term][doc_id] = c
            self._df[term] += 1
        self._avglen = sum(self._len.values()) / max(1, len(self._len))

    def add_all(self, docs: Iterable[tuple[str, str]]) -> None:
        for doc_id, text in docs:
            self.add(doc_id, text)

    def retrieve(self, query: str, top_k: int = 8) -> list[tuple[str, float]]:
        N = max(1, len(self._docs))
        q_terms = set(_tok(query))
        scores: dict[str, float] = defaultdict(float)
        for term in q_terms:
            if term not in self._postings:
                continue
            idf = math.log(1 + (N - self._df[term] + 0.5) / (self._df[term] + 0.5))
            for doc_id, tf in self._postings[term].items():
                dl = self._len[doc_id]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self._avglen or 1))
                scores[doc_id] += idf * (tf * (self.k1 + 1)) / (denom or 1)
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:top_k]


# --------------------------------------------------------------------------- #
# Cost meter — the M2 Gate-2 denominator ("fresh model compute")
# --------------------------------------------------------------------------- #

@dataclass
class CostMeter:
    model_calls: int = 0
    fresh_tokens: int = 0          # tokens the model actually processed (after prompt-cache discount)
    cached_prefix_tokens: int = 0  # tokens served from prompt cache (not fresh)
    retrievals: int = 0

    def as_dict(self) -> dict:
        return {
            "model_calls": self.model_calls,
            "fresh_tokens": self.fresh_tokens,
            "cached_prefix_tokens": self.cached_prefix_tokens,
            "retrievals": self.retrievals,
        }


class PromptCache:
    """Accounting model of a provider KV / prefix cache.

    Records prompt prefixes already seen; on a repeat prefix the shared tokens
    are billed as `cached_prefix_tokens` (not fresh). Maps onto the real
    provider prompt-cache at run time; here it is pure accounting so cost is
    reproducible without a live provider.
    """

    def __init__(self):
        self._seen_prefixes: dict[str, int] = {}  # prefix-hash -> prefix token length

    def split(self, prompt_tokens: list[str]) -> tuple[int, int]:
        """Return (cached_prefix_len, fresh_len) for this prompt."""
        best = 0
        # longest previously-seen prefix wins (standard prefix-cache behaviour)
        for i in range(len(prompt_tokens), 0, -1):
            h = hashlib.sha1(" ".join(prompt_tokens[:i]).encode()).hexdigest()
            if h in self._seen_prefixes:
                best = i
                break
        # register the full prompt's prefixes for future reuse
        h_full = hashlib.sha1(" ".join(prompt_tokens).encode()).hexdigest()
        self._seen_prefixes[h_full] = len(prompt_tokens)
        return best, len(prompt_tokens) - best


# --------------------------------------------------------------------------- #
# The arm
# --------------------------------------------------------------------------- #

@dataclass
class ArmResult:
    answer: object
    path: str                      # "exact_hit" | "computed"
    cost: dict = field(default_factory=dict)


class ConventionalCacheArm:
    """M2 arm B = exact content-address cache  ⊕  static index  ⊕  prompt cache,
    with version-keyed invalidation. `compute_fn(prompt) -> (answer, token_list)`
    is the fixed model call, injected."""

    def __init__(self, index: Optional[StaticIndex] = None, top_k: int = 8):
        self.index = index or StaticIndex()
        self.top_k = top_k
        self._store: dict[str, object] = {}     # content_key -> answer (verified when stored)
        self.meter = CostMeter()
        self.prompt_cache = PromptCache()

    def answer(
        self,
        question: str,
        k,
        compute_fn: Callable[[str], tuple[object, list[str]]],
        dep_versions: Optional[dict] = None,
        corpus_version: str = "",
        build_prompt: Optional[Callable[[str, list[tuple[str, float]]], tuple[str, list[str]]]] = None,
    ) -> ArmResult:
        ck = content_key(k, dep_versions, corpus_version)

        # 1. exact content-address hit under the current dependency versions.
        #    Provably correct (same K, same deps => same f(K)); zero model compute.
        if ck in self._store:
            return ArmResult(self._store[ck], "exact_hit", self.meter.as_dict())

        # 2. miss -> materialised search (cheap, no model) then the model computes.
        hits = self.index.retrieve(question, self.top_k)
        self.meter.retrievals += 1
        if build_prompt is not None:
            prompt, prompt_tokens = build_prompt(question, hits)
        else:
            snippet = " | ".join(d for d, _ in hits)
            prompt = f"{question}\n[ctx] {snippet}"
            prompt_tokens = _tok(prompt)

        cached_len, fresh_len = self.prompt_cache.split(prompt_tokens)
        answer, _ = compute_fn(prompt)
        self.meter.model_calls += 1
        self.meter.fresh_tokens += fresh_len
        self.meter.cached_prefix_tokens += cached_len

        self._store[ck] = answer   # only stored after the model produced it => never a stale substitute
        return ArmResult(answer, "computed", self.meter.as_dict())
