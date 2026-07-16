"""experiments/radar/score.py -- relevance scoring against AIOS open threads.

Simple weighted-keyword scoring (no ML, no network, deterministic): each item
is scored against a fixed set of phrases that map to AIOS's current open
research/engineering threads. This is intentionally crude -- a TF-style
keyword match, not semantic search -- so it is auditable and needs no model
call. It exists to turn "50 new arxiv papers" into "here are the 5 worth a
human look," not to be a precise relevance classifier.

Threads covered (per founder direction + AIOS memory/CLAUDE.md threads):
  compounding loop / self-improvement, verifier & verification, reward
  hacking, memory & continual learning, evolutionary/GEPA/genetic methods,
  long-horizon reliability, ontology, local-LLM agents.
"""
from __future__ import annotations

# phrase -> weight. Longer/more specific phrases carry more weight than
# generic single words, so e.g. "reward hacking" outweighs bare "agent".
KEYWORD_WEIGHTS: dict[str, float] = {
    # compounding loop / self-improvement
    "self-improving": 3, "self improving": 3, "self-improvement": 3,
    "recursive self-improvement": 4, "compounding": 2,
    # verifier / verification
    "verifier": 3, "verification": 2, "verifiable rewards": 3, "formally verified": 2,
    # reward hacking
    "reward hacking": 4, "specification gaming": 4, "reward model": 1.5,
    # memory / continual learning
    "continual learning": 3, "lifelong learning": 2.5, "catastrophic forgetting": 2.5,
    "memory-augmented": 2, "long-term memory": 2, "memory": 1,
    # evolutionary / GEPA / genetic
    "gepa": 4, "evolutionary": 2, "genetic algorithm": 2, "evolution strategy": 2,
    "evolutionary search": 2.5, "population-based": 1.5,
    # long-horizon reliability
    "long-horizon": 3, "long horizon": 3, "agentic benchmark": 2, "task completion rate": 1.5,
    "reliability": 1,
    # ontology
    "ontology": 3, "knowledge graph": 1.5, "world model": 1.5,
    # local-LLM agents
    "local llm": 2.5, "on-device": 1.5, "small language model": 2, "slm": 1,
    "agentic": 1, "agent": 0.5,
}


def score_item(item: dict, weights: dict[str, float] = KEYWORD_WEIGHTS) -> tuple[float, list[str]]:
    """Return (score, matched_keywords) for a normalized radar item.

    Matches against title + abstract_or_desc, case-insensitive, substring
    match (simple and deterministic -- no tokenizer dependency).
    """
    haystack = f"{item.get('title', '')} {item.get('abstract_or_desc', '')}".lower()
    score = 0.0
    matched: list[str] = []
    for phrase, weight in weights.items():
        if phrase in haystack:
            score += weight
            matched.append(phrase)
    return score, matched


def rank_items(items: list[dict], weights: dict[str, float] = KEYWORD_WEIGHTS) -> list[dict]:
    """Return items sorted by descending relevance score. Does not mutate
    the input items -- returns new dicts with 'score' and 'matched_keywords'
    added."""
    scored = []
    for it in items:
        score, matched = score_item(it, weights)
        enriched = dict(it)
        enriched["score"] = score
        enriched["matched_keywords"] = matched
        scored.append(enriched)
    scored.sort(key=lambda x: (x["score"], x.get("signal") or 0), reverse=True)
    return scored
