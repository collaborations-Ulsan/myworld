"""experiments/distiller/tasks.py -- the recalibrated task set for the AIOS Experience-Distiller
(docs/AIOS_DISTILLER_PREREG_2026-07-17.md v1.1, S2 "the S+1.1 ceiling diagnosis's fix").

Unlike experiments/learnos/tasks.py (18 hand-written bug-FIX tasks, shared by a 30b proposer that
rarely fails them), this module generates from-scratch IMPLEMENT-this-function tasks, parametrized
so the SMALL student (qwen3:1.7b) fails 30-70% of them (prereg S2) -- headroom + escalation data in
one move.

STRUCTURAL A/B SEPARATION (prereg S6 false-positive guard #1 -- "B는 별도 생성기 계열 + metamorphic
변형 + 히든 시드로, A와 문법 공유 금지"):
  * A_FAMILIES and B_FAMILIES are two DISJOINT name sets (asserted disjoint at import time below).
    Each family is its own hand-written golden implementation over its own domain shape -- A is
    string/list/cipher manipulation, B is matrix/validation/merge-adjacent-but-DIFFERENT-operation
    problems (e.g. A merges overlapping intervals; B computes the GAPS between them -- related
    domain, opposite operation, so a model cannot succeed on B by pattern-matching A's template).
  * "MUTATING family" / metamorphic variants: each family is a FamilySpec with an `arg_sampler`
    that draws fresh, differentially-tested instances (expected values come from actually RUNNING
    the hand-verified golden_solution on the sampled input, never hand-computed) -- so a family
    yields many structurally-related but concretely-different task instances, the metamorphic
    variation the guard asks for, all still deterministic given a seed.
  * "hidden seeds": A, B, and sentinel each draw from an INDEPENDENTLY salted random.Random stream
    (`_stream("A", seed)` vs `_stream("B", seed)` vs `_stream("SENTINEL", seed)`) -- B's concrete
    instances are not derivable from A's generation trace even when both share the same master
    seed.

PUBLIC/PRIVATE VIEW (mirrors experiments/learnos/tasks.py's held-out isolation discipline, adapted
-- see this module's own docstring difference below for why the *mechanism* differs from LearnOS):
  * `to_public(task)` strips `golden_solution`, `held_out_tests`, `adversarial_tests` -- the view
    handed to student/teacher prompt-building code (collect.py's prompt() function) and logged
    anywhere a trajectory might be inspected.
  * `held_out_bundle(task)` returns exactly the private fields, used ONLY by grading code
    (collect.py's verification gate, evaluate.py's scoring). tests/test_distiller.py greps
    collect.py's prompt-building path the same way LearnOS's held-out isolation test does.

WHY THIS DOESN'T CALL experiments/learnos/verify.run_holdout: that function resolves held-out
content by `task_id` against LearnOS's OWN private JSON file (experiments/learnos/data/
tasks_held_out.json) -- it has no notion of an externally-supplied test list, and this module's
task_ids are (deliberately) not entries in that file. Mixing this pipeline's tasks into LearnOS's
own isolated corpus would blur two independently-audited datasets for no benefit. What IS reused
unmodified from LearnOS is verify.run_public(test_exprs, source) -- the generic, task_id-agnostic,
sandboxed-subprocess grading primitive -- see collect.py and evaluate.py.

Every `buggy_source` below is a NotImplementedError-raising stub with the right signature (not a
"close but wrong" bugfix baseline like LearnOS -- these are from-scratch tasks). This is deliberate
double duty: (1) it is the frozen baseline verify_public(..., buggy_source) always fails, so any
real solution shows unambiguous gain; (2) it gives every task the exact field shape
experiments/learnos/audit.py's Blind-Curator injectors expect (`buggy_source`, `visible_tests` /
`sentinel_check` in `assert fn(args) == expected` form), so `audit.run_audit` runs UNMODIFIED over
this module's tasks via its documented extension points (`gate_fn=`, `golden_fixes=`) -- see
collect.py.

stdlib only (random, re, dataclasses).
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Callable

Sampler = Callable[[random.Random], tuple]

REQUIRED_PUBLIC_FIELDS = (
    "task_id", "family", "split", "description", "entry_point",
    "buggy_source", "visible_tests", "sentinel_check",
)
REQUIRED_PRIVATE_FIELDS = ("golden_solution", "held_out_tests", "adversarial_tests")

_ASSERT_EQ_RE = re.compile(r"^assert\s+[A-Za-z_][A-Za-z0-9_]*\(.*\)\s*(==|is)\s*.+$")


class TaskError(Exception):
    pass


def _stream(namespace: str, seed: int) -> random.Random:
    """An independently-salted RNG stream -- prereg's "hidden seeds" guard. Two namespaces given
    the SAME master seed produce unrelated sequences (verified by tests/test_distiller.py)."""
    return random.Random(f"aios-distiller:{namespace}:{seed}")


@dataclass
class FamilySpec:
    name: str
    split: str  # "A" | "B" | "sentinel"
    entry_point: str
    params: str  # e.g. "xs, k" -- literal parameter list text for the stub/prompt signature
    golden_body: str  # full function source, `def {entry_point}({params}):\n    ...`
    description: str  # one-paragraph natural-language spec shown to student/teacher/eval
    example_args: tuple  # canonical instance-0 args (always used, deterministic)
    arg_sampler: Sampler  # rng -> fresh args tuple, used for instances 1..n and held-out/adversarial
    n_instances: int = 6


def _stub_source(entry_point: str, params: str) -> str:
    return (
        f"def {entry_point}({params}):\n"
        f"    raise NotImplementedError('{entry_point} not implemented')\n"
    )


def _call_expr(entry_point: str, args: tuple) -> str:
    return f"{entry_point}({', '.join(repr(a) for a in args)})"


def _golden_namespace(golden_body: str) -> dict:
    ns: dict = {}
    exec(golden_body, ns)  # noqa: S102 -- golden_body is authored in THIS file, never model output
    return ns


def _run_golden(golden_body: str, entry_point: str, args: tuple):
    ns = _golden_namespace(golden_body)
    return ns[entry_point](*args)


def _assert_expr(entry_point: str, args: tuple, expected) -> str:
    expr = f"assert {_call_expr(entry_point, args)} == {expected!r}"
    if not _ASSERT_EQ_RE.match(expr):
        raise TaskError(f"generated assert does not match required shape: {expr!r}")
    return expr


# ---------------------------------------------------------------------------------------------
# A families (train) -- string/list/cipher manipulation, medium-hard-for-1.7b (edge cases matter:
# empty input, ties, wraparound, negative numbers).
# ---------------------------------------------------------------------------------------------

def _sample_int_list(rng: random.Random, lo=-20, hi=20, n_lo=1, n_hi=8) -> list:
    return [rng.randint(lo, hi) for _ in range(rng.randint(n_lo, n_hi))]


def _sample_word_list(rng: random.Random, n_lo=1, n_hi=6) -> list:
    vocab = ["a", "the", "cat", "dog", "run", "jump", "big", "small", "red", "blue", "sky", "sea"]
    return [rng.choice(vocab) for _ in range(rng.randint(n_lo, n_hi))]


def _sample_string(rng: random.Random, alphabet="abc", n_lo=0, n_hi=10) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(n_lo, n_hi)))


A_FAMILIES: list[FamilySpec] = [
    FamilySpec(
        name="second_largest_distinct", split="A", entry_point="second_largest_distinct",
        params="xs",
        golden_body=(
            "def second_largest_distinct(xs):\n"
            "    u = sorted(set(xs), reverse=True)\n"
            "    return u[1] if len(u) >= 2 else None\n"
        ),
        description=(
            "Write second_largest_distinct(xs) that returns the second-largest DISTINCT value in "
            "the list xs, or None if xs has fewer than 2 distinct values."
        ),
        example_args=([3, 1, 4, 1, 5, 9, 2, 6],),
        arg_sampler=lambda rng: (_sample_int_list(rng),),
    ),
    FamilySpec(
        name="run_length_encode", split="A", entry_point="run_length_encode",
        params="s",
        golden_body=(
            "def run_length_encode(s):\n"
            "    if not s:\n"
            "        return []\n"
            "    out = []\n"
            "    prev = s[0]\n"
            "    cnt = 1\n"
            "    for ch in s[1:]:\n"
            "        if ch == prev:\n"
            "            cnt += 1\n"
            "        else:\n"
            "            out.append((prev, cnt))\n"
            "            prev = ch\n"
            "            cnt = 1\n"
            "    out.append((prev, cnt))\n"
            "    return out\n"
        ),
        description=(
            "Write run_length_encode(s) that run-length-encodes string s into a list of "
            "(char, count) tuples for consecutive runs, e.g. 'aaabcc' -> [('a',3),('b',1),('c',2)]. "
            "Empty string returns []."
        ),
        example_args=("aaabcc",),
        arg_sampler=lambda rng: (_sample_string(rng, alphabet="abc", n_lo=0, n_hi=10),),
    ),
    FamilySpec(
        name="merge_overlapping_intervals", split="A", entry_point="merge_overlapping_intervals",
        params="intervals",
        golden_body=(
            "def merge_overlapping_intervals(intervals):\n"
            "    if not intervals:\n"
            "        return []\n"
            "    s = sorted(intervals, key=lambda p: p[0])\n"
            "    out = [list(s[0])]\n"
            "    for start, end in s[1:]:\n"
            "        if start <= out[-1][1]:\n"
            "            out[-1][1] = max(out[-1][1], end)\n"
            "        else:\n"
            "            out.append([start, end])\n"
            "    return [tuple(x) for x in out]\n"
        ),
        description=(
            "Write merge_overlapping_intervals(intervals) where intervals is a list of (start, end) "
            "tuples (possibly unsorted, possibly touching/overlapping). Return the sorted list of "
            "merged (start, end) tuples covering the same total range."
        ),
        example_args=([(1, 3), (2, 6), (8, 10)],),
        arg_sampler=lambda rng: (
            sorted(
                [(a, a + rng.randint(1, 5)) for a in sorted(rng.sample(range(0, 30), rng.randint(1, 5)))]
            ),
        ),
    ),
    FamilySpec(
        name="rotate_list_right", split="A", entry_point="rotate_list_right",
        params="xs, k",
        golden_body=(
            "def rotate_list_right(xs, k):\n"
            "    if not xs:\n"
            "        return []\n"
            "    n = len(xs)\n"
            "    k = k % n\n"
            "    return xs[-k:] + xs[:-k] if k else list(xs)\n"
        ),
        description=(
            "Write rotate_list_right(xs, k) that rotates list xs to the right by k positions "
            "(k may be 0 or exceed len(xs); empty xs returns [])."
        ),
        example_args=([1, 2, 3, 4, 5], 2),
        arg_sampler=lambda rng: (_sample_int_list(rng, n_lo=1, n_hi=7), rng.randint(0, 12)),
    ),
    FamilySpec(
        name="top_n_frequent_words", split="A", entry_point="top_n_frequent_words",
        params="words, n",
        golden_body=(
            "def top_n_frequent_words(words, n):\n"
            "    from collections import Counter\n"
            "    c = Counter(words)\n"
            "    ordered = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))\n"
            "    return [w for w, _ in ordered[:n]]\n"
        ),
        description=(
            "Write top_n_frequent_words(words, n) returning the n most frequent words (list of "
            "str), ties broken alphabetically ascending."
        ),
        example_args=(["a", "b", "a", "c", "b", "a"], 2),
        arg_sampler=lambda rng: (_sample_word_list(rng), rng.randint(1, 3)),
    ),
    FamilySpec(
        name="flatten_nested_list", split="A", entry_point="flatten_nested_list",
        params="lst",
        golden_body=(
            "def flatten_nested_list(lst):\n"
            "    out = []\n"
            "    for item in lst:\n"
            "        if isinstance(item, list):\n"
            "            out.extend(flatten_nested_list(item))\n"
            "        else:\n"
            "            out.append(item)\n"
            "    return out\n"
        ),
        description=(
            "Write flatten_nested_list(lst) that flattens an arbitrarily nested list of ints into "
            "one flat list, preserving left-to-right order."
        ),
        example_args=([1, [2, 3], [4, [5, 6]]],),
        arg_sampler=lambda rng: (
            [rng.randint(-9, 9) if rng.random() > 0.3 else [rng.randint(-9, 9) for _ in range(rng.randint(0, 3))]
             for _ in range(rng.randint(0, 5))],
        ),
    ),
    FamilySpec(
        name="caesar_cipher_shift", split="A", entry_point="caesar_cipher_shift",
        params="s, shift",
        golden_body=(
            "def caesar_cipher_shift(s, shift):\n"
            "    out = []\n"
            "    for ch in s:\n"
            "        if ch.isalpha():\n"
            "            base = ord('A') if ch.isupper() else ord('a')\n"
            "            out.append(chr((ord(ch) - base + shift) % 26 + base))\n"
            "        else:\n"
            "            out.append(ch)\n"
            "    return ''.join(out)\n"
        ),
        description=(
            "Write caesar_cipher_shift(s, shift) that shifts each letter of s by `shift` positions "
            "(wrapping within the same case, negative/large shift allowed), leaving non-letters "
            "unchanged."
        ),
        example_args=("Hello, World!", 1),
        arg_sampler=lambda rng: (
            _sample_string(rng, alphabet="AaBbCcXxYyZz, !", n_lo=1, n_hi=12), rng.randint(-30, 30),
        ),
    ),
    FamilySpec(
        name="chunk_list_fixed_size", split="A", entry_point="chunk_list_fixed_size",
        params="xs, size",
        golden_body=(
            "def chunk_list_fixed_size(xs, size):\n"
            "    return [xs[i:i + size] for i in range(0, len(xs), size)]\n"
        ),
        description=(
            "Write chunk_list_fixed_size(xs, size) that splits list xs into consecutive chunks of "
            "length `size` (the last chunk may be shorter); size is always >= 1."
        ),
        example_args=([1, 2, 3, 4, 5], 2),
        arg_sampler=lambda rng: (_sample_int_list(rng, n_lo=0, n_hi=9), rng.randint(1, 4)),
    ),
]

# ---------------------------------------------------------------------------------------------
# B families (held-out) -- matrix/validation/merge-adjacent-BUT-different-op domain shapes.
# Structurally DISJOINT from A_FAMILIES (asserted below); no template is shared with A.
# ---------------------------------------------------------------------------------------------


def _sample_matrix(rng: random.Random) -> list:
    rows = rng.randint(0, 4)
    cols = rng.randint(1, 4) if rows else 0
    return [[rng.randint(-9, 9) for _ in range(cols)] for _ in range(rows)]


B_FAMILIES: list[FamilySpec] = [
    FamilySpec(
        name="matrix_transpose", split="B", entry_point="matrix_transpose",
        params="m",
        golden_body=(
            "def matrix_transpose(m):\n"
            "    if not m:\n"
            "        return []\n"
            "    return [list(row) for row in zip(*m)]\n"
        ),
        description=(
            "Write matrix_transpose(m) that returns the transpose of the 2D list m (list of equal-"
            "length rows); m may be empty (return [])."
        ),
        example_args=([[1, 2, 3], [4, 5, 6]],),
        arg_sampler=lambda rng: (_sample_matrix(rng),),
    ),
    FamilySpec(
        name="longest_increasing_run", split="B", entry_point="longest_increasing_run",
        params="xs",
        golden_body=(
            "def longest_increasing_run(xs):\n"
            "    if not xs:\n"
            "        return 0\n"
            "    best = cur = 1\n"
            "    for i in range(1, len(xs)):\n"
            "        if xs[i] > xs[i - 1]:\n"
            "            cur += 1\n"
            "            best = max(best, cur)\n"
            "        else:\n"
            "            cur = 1\n"
            "    return best\n"
        ),
        description=(
            "Write longest_increasing_run(xs) that returns the length of the longest STRICTLY "
            "increasing contiguous run in xs (0 for empty list, 1 for a single element)."
        ),
        example_args=([1, 2, 1, 2, 3, 4, 1],),
        arg_sampler=lambda rng: (_sample_int_list(rng, lo=-9, hi=9, n_lo=0, n_hi=9),),
    ),
    FamilySpec(
        name="validate_password_rules", split="B", entry_point="validate_password_rules",
        params="s",
        golden_body=(
            "def validate_password_rules(s):\n"
            "    return (len(s) >= 8 and any(c.isupper() for c in s)\n"
            "            and any(c.islower() for c in s) and any(c.isdigit() for c in s))\n"
        ),
        description=(
            "Write validate_password_rules(s) returning True iff s has length >= 8 AND contains "
            "at least one uppercase letter, one lowercase letter, and one digit."
        ),
        example_args=("Abcdef12",),
        arg_sampler=lambda rng: (_sample_string(rng, alphabet="Aa1bB2cC3!", n_lo=0, n_hi=12),),
    ),
    FamilySpec(
        name="most_common_char_tiebreak", split="B", entry_point="most_common_char_tiebreak",
        params="s",
        golden_body=(
            "def most_common_char_tiebreak(s):\n"
            "    if not s:\n"
            "        return None\n"
            "    counts = {}\n"
            "    for ch in s:\n"
            "        counts[ch] = counts.get(ch, 0) + 1\n"
            "    best_ch, best_count = None, -1\n"
            "    for ch in s:\n"
            "        if counts[ch] > best_count:\n"
            "            best_count = counts[ch]\n"
            "            best_ch = ch\n"
            "    return best_ch\n"
        ),
        description=(
            "Write most_common_char_tiebreak(s) returning the most frequent character in s; ties "
            "broken by first occurrence in s. Empty string returns None."
        ),
        example_args=("aabbbcc",),
        arg_sampler=lambda rng: (_sample_string(rng, alphabet="ab", n_lo=0, n_hi=10),),
    ),
    FamilySpec(
        name="zigzag_merge", split="B", entry_point="zigzag_merge",
        params="a, b",
        golden_body=(
            "def zigzag_merge(a, b):\n"
            "    out = []\n"
            "    for i in range(max(len(a), len(b))):\n"
            "        if i < len(a):\n"
            "            out.append(a[i])\n"
            "        if i < len(b):\n"
            "            out.append(b[i])\n"
            "    return out\n"
        ),
        description=(
            "Write zigzag_merge(a, b) that interleaves lists a and b alternately starting with a "
            "(a[0], b[0], a[1], b[1], ...), appending the leftover tail of whichever list is longer."
        ),
        example_args=([1, 2, 3], [4, 5]),
        arg_sampler=lambda rng: (_sample_int_list(rng, n_lo=0, n_hi=6), _sample_int_list(rng, n_lo=0, n_hi=6)),
    ),
    FamilySpec(
        name="interval_gaps", split="B", entry_point="interval_gaps",
        params="intervals, lo, hi",
        golden_body=(
            "def interval_gaps(intervals, lo, hi):\n"
            "    out = []\n"
            "    cur = lo\n"
            "    for start, end in intervals:\n"
            "        if start > cur:\n"
            "            out.append((cur, start))\n"
            "        cur = max(cur, end)\n"
            "    if cur < hi:\n"
            "        out.append((cur, hi))\n"
            "    return out\n"
        ),
        description=(
            "Write interval_gaps(intervals, lo, hi) where intervals is a sorted list of "
            "non-overlapping (start, end) tuples within [lo, hi]. Return the list of GAP "
            "(start, end) tuples in [lo, hi] not covered by any interval."
        ),
        example_args=([(1, 3), (5, 7)], 0, 10),
        arg_sampler=lambda rng: (
            (lambda lo, hi: (
                lambda cuts: (
                    [(cuts[i], cuts[i] + rng.randint(1, max(1, (cuts[i + 1] - cuts[i]) // 2 or 1)))
                     for i in range(0, len(cuts) - 1, 2)],
                    lo, hi,
                )
            )(sorted(rng.sample(range(lo, hi), min(4, hi - lo)))) if hi - lo >= 2 else ([], lo, hi)
            )(0, rng.randint(6, 20))
        ),
    ),
]

SENTINEL_FAMILIES: list[FamilySpec] = [
    FamilySpec(
        name="add_two_numbers", split="sentinel", entry_point="add_two_numbers", params="a, b",
        golden_body="def add_two_numbers(a, b):\n    return a + b\n",
        description="Write add_two_numbers(a, b) that returns a + b.",
        example_args=(2, 3), arg_sampler=lambda rng: (2, 3), n_instances=1,
    ),
    FamilySpec(
        name="is_even", split="sentinel", entry_point="is_even", params="n",
        golden_body="def is_even(n):\n    return n % 2 == 0\n",
        description="Write is_even(n) that returns True iff n is even.",
        example_args=(4,), arg_sampler=lambda rng: (4,), n_instances=1,
    ),
    FamilySpec(
        name="string_to_upper", split="sentinel", entry_point="string_to_upper", params="s",
        golden_body="def string_to_upper(s):\n    return s.upper()\n",
        description="Write string_to_upper(s) that returns s uppercased.",
        example_args=("abc",), arg_sampler=lambda rng: ("abc",), n_instances=1,
    ),
    FamilySpec(
        name="list_sum", split="sentinel", entry_point="list_sum", params="xs",
        golden_body="def list_sum(xs):\n    return sum(xs)\n",
        description="Write list_sum(xs) that returns the sum of list xs (0 for empty list).",
        example_args=([1, 2, 3],), arg_sampler=lambda rng: ([1, 2, 3],), n_instances=1,
    ),
    FamilySpec(
        name="list_max", split="sentinel", entry_point="list_max", params="xs",
        golden_body="def list_max(xs):\n    return max(xs)\n",
        description="Write list_max(xs) that returns the maximum value in non-empty list xs.",
        example_args=([3, 1, 2],), arg_sampler=lambda rng: ([5, 5, 2],), n_instances=1,
    ),
]

_A_NAMES = {f.name for f in A_FAMILIES}
_B_NAMES = {f.name for f in B_FAMILIES}
assert _A_NAMES.isdisjoint(_B_NAMES), "A_FAMILIES and B_FAMILIES must not share a family name"


# ---------------------------------------------------------------------------------------------
# instantiation
# ---------------------------------------------------------------------------------------------

def _build_instance(spec: FamilySpec, idx: int, args: tuple, n_held_out: int, n_adversarial: int,
                     rng: random.Random) -> dict:
    expected = _run_golden(spec.golden_body, spec.entry_point, args)
    visible = [_assert_expr(spec.entry_point, args, expected)]
    # one extra hand-anchored example (instance 0's canonical args) always included as a second
    # visible case, giving the student >=2 worked examples without ever showing held-out content.
    if idx != 0:
        canon_expected = _run_golden(spec.golden_body, spec.entry_point, spec.example_args)
        visible.append(_assert_expr(spec.entry_point, spec.example_args, canon_expected))

    # dedup by repr() (not the raw tuple) -- several samplers draw nested lists, which are
    # unhashable and can't go straight into a set.
    held_out = []
    seen = {repr(args)}
    _budget = n_held_out * 25 + 25  # generous cap so a low-diversity sampler can't hang the build
    while len(held_out) < n_held_out and _budget > 0:
        _budget -= 1
        cand = spec.arg_sampler(rng)
        if repr(cand) in seen:
            continue
        seen.add(repr(cand))
        held_out.append(_assert_expr(spec.entry_point, cand, _run_golden(spec.golden_body, spec.entry_point, cand)))

    adversarial = []
    _budget = n_adversarial * 25 + 25
    while len(adversarial) < n_adversarial and _budget > 0:
        _budget -= 1
        cand = spec.arg_sampler(rng)
        if repr(cand) in seen:
            continue
        seen.add(repr(cand))
        adversarial.append(_assert_expr(spec.entry_point, cand, _run_golden(spec.golden_body, spec.entry_point, cand)))

    sentinel_args = spec.arg_sampler(rng) if spec.split != "sentinel" else spec.example_args
    sentinel_check = _assert_expr(
        spec.entry_point, sentinel_args, _run_golden(spec.golden_body, spec.entry_point, sentinel_args)
    )

    return {
        "task_id": f"{spec.name}__{idx:03d}",
        "family": spec.name,
        "split": spec.split,
        "description": spec.description,
        "entry_point": spec.entry_point,
        "buggy_source": _stub_source(spec.entry_point, spec.params),
        "visible_tests": visible,
        "sentinel_check": sentinel_check,
        "golden_solution": spec.golden_body,
        "held_out_tests": held_out,
        "adversarial_tests": adversarial,
    }


def _instantiate_family(spec: FamilySpec, rng: random.Random, n_held_out=4, n_adversarial=3) -> list[dict]:
    out = []
    for idx in range(spec.n_instances):
        args = spec.example_args if idx == 0 else spec.arg_sampler(rng)
        out.append(_build_instance(spec, idx, args, n_held_out, n_adversarial, rng))
    return out


def build_tasks(seed: int = 20260717, a_instances: int | None = None, b_instances: int | None = None) -> list[dict]:
    """Generate the full task corpus (A + B + sentinel), each split drawn from an independently
    salted RNG stream (`_stream` -- prereg's "hidden seeds" guard). `a_instances`/`b_instances`
    override every family's `n_instances` uniformly (for scaling a real run toward N_train>=250
    without hand-editing every FamilySpec)."""
    tasks: list[dict] = []
    a_rng = _stream("A", seed)
    for spec in A_FAMILIES:
        s = spec if a_instances is None else _with_n(spec, a_instances)
        tasks.extend(_instantiate_family(s, a_rng))
    b_rng = _stream("B", seed)
    for spec in B_FAMILIES:
        s = spec if b_instances is None else _with_n(spec, b_instances)
        tasks.extend(_instantiate_family(s, b_rng))
    sentinel_rng = _stream("SENTINEL", seed)
    for spec in SENTINEL_FAMILIES:
        tasks.extend(_instantiate_family(spec, sentinel_rng, n_held_out=1, n_adversarial=1))
    return tasks


def _with_n(spec: FamilySpec, n: int) -> FamilySpec:
    return FamilySpec(**{**spec.__dict__, "n_instances": n})


def by_split(tasks: list[dict], split: str) -> list[dict]:
    return [t for t in tasks if t["split"] == split]


def to_public(task: dict) -> dict:
    """The student/teacher/eval-facing view -- strips golden_solution, held_out_tests,
    adversarial_tests. This is the ONLY view collect.py's prompt-building path may touch."""
    return {k: task[k] for k in REQUIRED_PUBLIC_FIELDS}


def held_out_bundle(task: dict) -> dict:
    """The grading-only view -- used exclusively by collect.py's verification gate and
    evaluate.py's scoring, never by prompt-building code."""
    return {k: task[k] for k in REQUIRED_PRIVATE_FIELDS}


def prompt_text(task: dict) -> str:
    """The single, STRIPPED prompt template used EVERYWHERE (student attempt, teacher escalation,
    eval of every arm) -- prereg S6 guard #3 ("stripped prompt"): no arm ever sees a differently
    -shaped prompt, so a lift can't be explained by prompt-shape favoritism."""
    pub = to_public(task)
    lines = [
        pub["description"],
        "",
        f"Signature: def {pub['entry_point']}(...): ...",
        "Example:",
    ]
    lines += [f"  {t}" for t in pub["visible_tests"]]
    lines += [
        "",
        "Return ONLY a single fenced ```python``` code block containing the function definition. "
        "No prose, no tests.",
    ]
    return "\n".join(lines)
