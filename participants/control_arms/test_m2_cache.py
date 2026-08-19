"""Unit tests for the M2 conventional-cache arm — the two Gate-1-safety guards
and the retrieval layer. Stdlib only; no model, no GPU.

Run:  python3 test_m2_cache.py
"""

import m2_cache as m


def _fake_compute(calls):
    """A deterministic stand-in for the fixed model call. Records invocations so
    tests can assert on *fresh model compute* (the M2 Gate-2 denominator)."""
    def compute_fn(prompt):
        calls.append(prompt)
        # answer encodes the corpus version present in the prompt-independent K,
        # so a stale serve would be detectable as a wrong version tag.
        return (f"ANS<{len(calls)}>", ["t"] * 3)
    return compute_fn


def test_exact_hit_zero_compute():
    arm = m.ConventionalCacheArm()
    calls = []
    fn = _fake_compute(calls)
    K = {"task_text": "fix parser", "repo": "R", "exit_class": "assert"}
    r1 = arm.answer("q", K, fn, corpus_version="v1")
    r2 = arm.answer("q", K, fn, corpus_version="v1")
    assert r1.path == "computed" and r2.path == "exact_hit", (r1.path, r2.path)
    assert r1.answer == r2.answer, "exact hit must return the same verified answer"
    assert len(calls) == 1, f"exact repeat must cost 0 fresh model calls, got {len(calls)}"
    print("ok  exact_hit_zero_compute")


def test_version_bump_no_stale_serve():
    """The invalidation guard: when a dependency changes, B must MISS and
    recompute — never serve the stale prior answer (that would fail Gate 1)."""
    arm = m.ConventionalCacheArm()
    calls = []
    fn = _fake_compute(calls)
    K = {"task_text": "fix parser", "repo": "R"}
    r1 = arm.answer("q", K, fn, dep_versions={"doc7": "1"})
    r2 = arm.answer("q", K, fn, dep_versions={"doc7": "2"})  # doc7 changed
    assert r2.path == "computed", "changed dependency must invalidate -> recompute"
    assert r1.answer != r2.answer, "must NOT serve the stale pre-change answer"
    assert len(calls) == 2
    # coarse fallback: same test via corpus_version
    r3 = arm.answer("q2", K, fn, corpus_version="a")
    r4 = arm.answer("q2", K, fn, corpus_version="b")
    assert r4.path == "computed" and r3.answer != r4.answer
    print("ok  version_bump_no_stale_serve")


def test_near_match_never_substitutes_answer():
    """Retrieval may find a near neighbour, but the model still computes -> a
    different question never receives a cached different-K answer."""
    idx = m.StaticIndex()
    idx.add_all([("d1", "parser tokenizer grammar"), ("d2", "network socket retry")])
    arm = m.ConventionalCacheArm(index=idx)
    calls = []
    fn = _fake_compute(calls)
    arm.answer("parser bug", {"task_text": "A"}, fn, corpus_version="v1")
    # a DIFFERENT K that retrieves the same doc must still call the model
    before = len(calls)
    r = arm.answer("parser bug again", {"task_text": "B"}, fn, corpus_version="v1")
    assert r.path == "computed" and len(calls) == before + 1, "near-match must not substitute"
    print("ok  near_match_never_substitutes_answer")


def test_static_index_retrieval_relevance():
    idx = m.StaticIndex()
    idx.add_all([
        ("d1", "python parser tokenizer grammar ast"),
        ("d2", "network socket retry backoff timeout"),
        ("d3", "parser grammar rule reduction"),
    ])
    hits = idx.retrieve("parser grammar", top_k=2)
    ids = [h for h, _ in hits]
    assert "d2" not in ids, f"irrelevant doc leaked into top-2: {ids}"
    assert set(ids) == {"d1", "d3"}, ids
    # determinism
    assert idx.retrieve("parser grammar", top_k=2) == hits
    print("ok  static_index_retrieval_relevance")


def test_cost_meter_hit_vs_miss():
    arm = m.ConventionalCacheArm()
    calls = []
    fn = _fake_compute(calls)
    K = {"task_text": "x"}
    arm.answer("q", K, fn, corpus_version="v1")   # miss -> 1 call, 1 retrieval
    arm.answer("q", K, fn, corpus_version="v1")   # hit  -> 0 additional
    c = arm.meter.as_dict()
    assert c["model_calls"] == 1 and c["retrievals"] == 1, c
    print("ok  cost_meter_hit_vs_miss")


if __name__ == "__main__":
    test_exact_hit_zero_compute()
    test_version_bump_no_stale_serve()
    test_near_match_never_substitutes_answer()
    test_static_index_retrieval_relevance()
    test_cost_meter_hit_vs_miss()
    print("\nALL PASS")
