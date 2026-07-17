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
    string/list/cipher manipulation (no interval/matrix/date structure at all), B is
    matrix/validation/interval-merge-adjacent-but-DIFFERENT-operation problems -- disjoint
    operation classes in a related domain, so a model cannot succeed on B by pattern-matching A's
    template.
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
# A families (train) -- string/list/cipher manipulation, HARDENED for headroom
# (docs/AIOS_DISTILLER_PILOT_RESULTS_2026-07-18.md substrate-calibration pass). The original 8
# families here (second_largest_distinct, run_length_encode, merge_overlapping_intervals,
# rotate_list_right, top_n_frequent_words, flatten_nested_list, caesar_cipher_shift,
# chunk_list_fixed_size) were single-concept "cookbook" problems qwen3:1.7b solved 26/30 (87%)
# live in the 2026-07-17 pilot collect -- no headroom, only N_verified=4. Replaced with genuinely
# multi-step / classically error-prone problems (nested-bracket decode, subtractive-notation
# numerals, bijective base-26, two-pointer dedup, deque-style windowing, index-not-boolean bracket
# matching, key-cycling cipher) in the SAME string/list/cipher domain shape, live-calibrated
# against qwen3:1.7b to land pass-rate in the ~30-70% band (see calibrate.py and
# data/calibration_report.json for the measured numbers).
# ---------------------------------------------------------------------------------------------

def _sample_int_list(rng: random.Random, lo=-20, hi=20, n_lo=1, n_hi=8) -> list:
    return [rng.randint(lo, hi) for _ in range(rng.randint(n_lo, n_hi))]


def _sample_string(rng: random.Random, alphabet="abc", n_lo=0, n_hi=10) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(n_lo, n_hi)))


def _gen_nested_rle(rng: random.Random, depth: int = 0, max_depth: int = 2) -> str:
    """A well-formed nested run-length-encoded string, e.g. 'ab3[c2[d]]e' -- used only to build
    decode_nested_run_length instances. Outer-level repeat counts may run to 2 digits (occasional
    multi-digit-count coverage); nested counts stay small so decoded length never blows up."""
    parts = []
    for _ in range(rng.randint(1, 3)):
        if depth < max_depth and rng.random() < 0.5:
            inner = _gen_nested_rle(rng, depth + 1, max_depth)
            k = rng.randint(1, 12) if depth == 0 else rng.randint(1, 4)
            parts.append(f"{k}[{inner}]")
        else:
            parts.append("".join(rng.choice("abc") for _ in range(rng.randint(1, 3))))
    return "".join(parts)


A_FAMILIES: list[FamilySpec] = [
    FamilySpec(
        name="decode_nested_run_length", split="A", entry_point="decode_nested_run_length",
        params="s",
        golden_body=(
            "def decode_nested_run_length(s):\n"
            "    stack = []\n"
            "    cur_str = ''\n"
            "    cur_num = 0\n"
            "    for ch in s:\n"
            "        if ch.isdigit():\n"
            "            cur_num = cur_num * 10 + int(ch)\n"
            "        elif ch == '[':\n"
            "            stack.append((cur_str, cur_num))\n"
            "            cur_str = ''\n"
            "            cur_num = 0\n"
            "        elif ch == ']':\n"
            "            prev_str, num = stack.pop()\n"
            "            cur_str = prev_str + cur_str * num\n"
            "        else:\n"
            "            cur_str += ch\n"
            "    return cur_str\n"
        ),
        description=(
            "Write decode_nested_run_length(s) that decodes a run-length-encoded string where "
            "k[substring] means substring repeated k (a positive integer, possibly multi-digit) "
            "times. Encodings may NEST arbitrarily deep, e.g. '2[3[a]b]' -> 'aaabaaab'. Plain "
            "lowercase letters outside any bracket pass through unchanged. The input is always a "
            "validly-encoded string."
        ),
        example_args=("3[a]2[bc]",),
        arg_sampler=lambda rng: (_gen_nested_rle(rng),),
    ),
    FamilySpec(
        name="int_to_roman", split="A", entry_point="int_to_roman",
        params="num",
        golden_body=(
            "def int_to_roman(num):\n"
            "    vals = [\n"
            "        (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),\n"
            "        (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),\n"
            "        (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'),\n"
            "    ]\n"
            "    out = []\n"
            "    for v, sym in vals:\n"
            "        while num >= v:\n"
            "            out.append(sym)\n"
            "            num -= v\n"
            "    return ''.join(out)\n"
        ),
        description=(
            "Write int_to_roman(num) that converts an integer num (1 <= num <= 3999) to its Roman "
            "numeral string using standard subtractive notation (e.g. 4 -> 'IV', 9 -> 'IX', "
            "1994 -> 'MCMXCIV')."
        ),
        example_args=(1994,),
        arg_sampler=lambda rng: (rng.randint(1, 3999),),
    ),
    FamilySpec(
        name="zigzag_convert", split="A", entry_point="zigzag_convert",
        params="s, n",
        golden_body=(
            "def zigzag_convert(s, n):\n"
            "    if n <= 1 or n >= len(s):\n"
            "        return s\n"
            "    rows = [''] * n\n"
            "    cur, step = 0, 1\n"
            "    for ch in s:\n"
            "        rows[cur] += ch\n"
            "        if cur == 0:\n"
            "            step = 1\n"
            "        elif cur == n - 1:\n"
            "            step = -1\n"
            "        cur += step\n"
            "    return ''.join(rows)\n"
        ),
        description=(
            "Write zigzag_convert(s, n) that arranges string s in a zigzag pattern across n rows "
            "(down then diagonally up, repeating) and returns the characters read row by row, e.g. "
            "zigzag_convert('PAYPALISHIRING', 3) -> 'PAHNAPLSIIGYIR'. If n <= 1 or n >= len(s), "
            "return s unchanged."
        ),
        example_args=("PAYPALISHIRING", 3),
        arg_sampler=lambda rng: (_sample_string(rng, alphabet="ABCDEFGH", n_lo=1, n_hi=12), rng.randint(1, 5)),
    ),
    FamilySpec(
        name="three_sum_zero_triplets", split="A", entry_point="three_sum_zero_triplets",
        params="xs",
        golden_body=(
            "def three_sum_zero_triplets(xs):\n"
            "    xs = sorted(xs)\n"
            "    n = len(xs)\n"
            "    res = set()\n"
            "    for i in range(n - 2):\n"
            "        if i > 0 and xs[i] == xs[i - 1]:\n"
            "            continue\n"
            "        lo, hi = i + 1, n - 1\n"
            "        while lo < hi:\n"
            "            s = xs[i] + xs[lo] + xs[hi]\n"
            "            if s == 0:\n"
            "                res.add((xs[i], xs[lo], xs[hi]))\n"
            "                lo += 1\n"
            "                hi -= 1\n"
            "            elif s < 0:\n"
            "                lo += 1\n"
            "            else:\n"
            "                hi -= 1\n"
            "    return sorted(res)\n"
        ),
        description=(
            "Write three_sum_zero_triplets(xs) that returns a sorted list of all UNIQUE triplets "
            "(as ascending (a, b, c) tuples) drawn from list xs whose values sum to zero. No "
            "duplicate triplets (by value, not position); [] if none exist."
        ),
        example_args=([-1, 0, 1, 2, -1, -4],),
        arg_sampler=lambda rng: (_sample_int_list(rng, lo=-8, hi=8, n_lo=3, n_hi=9),),
    ),
    FamilySpec(
        name="number_to_excel_column", split="A", entry_point="number_to_excel_column",
        params="n",
        golden_body=(
            "def number_to_excel_column(n):\n"
            "    out = []\n"
            "    while n > 0:\n"
            "        n, rem = divmod(n - 1, 26)\n"
            "        out.append(chr(ord('A') + rem))\n"
            "    return ''.join(reversed(out))\n"
        ),
        description=(
            "Write number_to_excel_column(n) that converts a positive integer n (1-indexed) into "
            "a spreadsheet-style column title: 1 -> 'A', 26 -> 'Z', 27 -> 'AA', 28 -> 'AB', "
            "703 -> 'AAA' (bijective base-26 -- there is no digit for zero)."
        ),
        example_args=(28,),
        arg_sampler=lambda rng: (rng.randint(1, 18278),),
    ),
    FamilySpec(
        name="first_unbalanced_bracket_index", split="A", entry_point="first_unbalanced_bracket_index",
        params="s",
        golden_body=(
            "def first_unbalanced_bracket_index(s):\n"
            "    opens = set('([{')\n"
            "    closes = {')': '(', ']': '[', '}': '{'}\n"
            "    stack = []\n"
            "    for i, ch in enumerate(s):\n"
            "        if ch in opens:\n"
            "            stack.append((ch, i))\n"
            "        elif ch in closes:\n"
            "            if not stack or stack[-1][0] != closes[ch]:\n"
            "                return i\n"
            "            stack.pop()\n"
            "    if stack:\n"
            "        return stack[0][1]\n"
            "    return -1\n"
        ),
        description=(
            "Write first_unbalanced_bracket_index(s) where s may contain '()[]{}' plus other "
            "characters (ignored). Return the index of the first closing bracket that has no "
            "matching open (empty stack, or wrong type); if every bracket matches but some opens "
            "are never closed, return the index of the EARLIEST unclosed opening bracket; return "
            "-1 if s is fully balanced."
        ),
        example_args=("(a[b)c]",),
        arg_sampler=lambda rng: (_sample_string(rng, alphabet="()[]{}abc", n_lo=0, n_hi=12),),
    ),
    FamilySpec(
        name="sliding_window_maximum", split="A", entry_point="sliding_window_maximum",
        params="xs, k",
        golden_body=(
            "def sliding_window_maximum(xs, k):\n"
            "    n = len(xs)\n"
            "    if n == 0 or k <= 0 or k > n:\n"
            "        return []\n"
            "    from collections import deque\n"
            "    dq = deque()\n"
            "    out = []\n"
            "    for i, x in enumerate(xs):\n"
            "        while dq and xs[dq[-1]] <= x:\n"
            "            dq.pop()\n"
            "        dq.append(i)\n"
            "        if dq[0] <= i - k:\n"
            "            dq.popleft()\n"
            "        if i >= k - 1:\n"
            "            out.append(xs[dq[0]])\n"
            "    return out\n"
        ),
        description=(
            "Write sliding_window_maximum(xs, k) that returns a list containing the maximum value "
            "of every contiguous window of size k as it slides left-to-right across xs (length "
            "len(xs) - k + 1). Return [] if xs is empty, k <= 0, or k > len(xs)."
        ),
        example_args=([1, 3, -1, -3, 5, 3, 6, 7], 3),
        arg_sampler=lambda rng: (_sample_int_list(rng, lo=-9, hi=9, n_lo=0, n_hi=10), rng.randint(1, 5)),
    ),
    FamilySpec(
        name="vigenere_cipher_encode", split="A", entry_point="vigenere_cipher_encode",
        params="s, key",
        golden_body=(
            "def vigenere_cipher_encode(s, key):\n"
            "    if not key:\n"
            "        return s\n"
            "    out = []\n"
            "    key = key.lower()\n"
            "    ki = 0\n"
            "    for ch in s:\n"
            "        if ch.isalpha():\n"
            "            shift = ord(key[ki % len(key)]) - ord('a')\n"
            "            base = ord('A') if ch.isupper() else ord('a')\n"
            "            out.append(chr((ord(ch) - base + shift) % 26 + base))\n"
            "            ki += 1\n"
            "        else:\n"
            "            out.append(ch)\n"
            "    return ''.join(out)\n"
        ),
        description=(
            "Write vigenere_cipher_encode(s, key) that Vigenere-encodes s using repeating "
            "lowercase `key`: each ALPHABETIC character of s is shifted by the alphabet position "
            "(A=0) of the next key letter (case of the output letter matches the input letter; "
            "the key only advances on alphabetic input characters -- non-letters are copied "
            "through unchanged and do not consume a key position). key is always non-empty "
            "lowercase letters."
        ),
        example_args=("Hello, World!", "key"),
        arg_sampler=lambda rng: (
            _sample_string(rng, alphabet="AaBbCcXxYyZz, !", n_lo=1, n_hi=12),
            _sample_string(rng, alphabet="abcxyz", n_lo=1, n_hi=5),
        ),
    ),
]

# ---------------------------------------------------------------------------------------------
# B families (held-out) -- matrix/validation/interval-merge-adjacent-BUT-different-op domain
# shapes. Structurally DISJOINT from A_FAMILIES (asserted below); no template is shared with A.
# HARDENED alongside A (see A_FAMILIES comment above) so held-out headroom is comparable, not
# just A's escalation-generating headroom.
# ---------------------------------------------------------------------------------------------


def _sample_matrix(rng: random.Random) -> list:
    rows = rng.randint(0, 4)
    cols = rng.randint(1, 4) if rows else 0
    return [[rng.randint(-9, 9) for _ in range(cols)] for _ in range(rows)]


def _sample_iso_date_like(rng: random.Random) -> str:
    """Mostly plausible YYYY-MM-DD strings (biased toward day-31 and Feb-29 edge cases, so both
    True and False outcomes are common), occasionally outright malformed junk."""
    if rng.random() < 0.15:
        return "".join(rng.choice("0123456789-abc") for _ in range(rng.randint(0, 10)))
    year = rng.randint(1900, 2100)
    month = rng.randint(1, 12)
    day = rng.randint(1, 31)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _sample_intervals_for_rooms(rng: random.Random) -> list:
    out = []
    for _ in range(rng.randint(0, 6)):
        start = rng.randint(0, 20)
        out.append((start, start + rng.randint(1, 10)))
    return out


def _sample_unsorted_overlapping_intervals(rng: random.Random) -> tuple:
    hi = rng.randint(6, 20)
    raw = []
    for _ in range(rng.randint(0, 5)):
        start = rng.randint(0, hi - 1)
        raw.append((start, start + rng.randint(1, max(1, hi - start))))
    rng.shuffle(raw)
    return raw, 0, hi


B_FAMILIES: list[FamilySpec] = [
    FamilySpec(
        name="matrix_spiral_order", split="B", entry_point="matrix_spiral_order",
        params="m",
        golden_body=(
            "def matrix_spiral_order(m):\n"
            "    if not m or not m[0]:\n"
            "        return []\n"
            "    out = []\n"
            "    top, bottom = 0, len(m) - 1\n"
            "    left, right = 0, len(m[0]) - 1\n"
            "    while top <= bottom and left <= right:\n"
            "        for c in range(left, right + 1):\n"
            "            out.append(m[top][c])\n"
            "        top += 1\n"
            "        for r in range(top, bottom + 1):\n"
            "            out.append(m[r][right])\n"
            "        right -= 1\n"
            "        if top <= bottom:\n"
            "            for c in range(right, left - 1, -1):\n"
            "                out.append(m[bottom][c])\n"
            "            bottom -= 1\n"
            "        if left <= right:\n"
            "            for r in range(bottom, top - 1, -1):\n"
            "                out.append(m[r][left])\n"
            "            left += 1\n"
            "    return out\n"
        ),
        description=(
            "Write matrix_spiral_order(m) that returns all elements of the 2D list m (rectangular, "
            "equal-length rows, possibly empty) visited in clockwise spiral order starting from "
            "the top-left element."
        ),
        example_args=([[1, 2, 3], [4, 5, 6], [7, 8, 9]],),
        arg_sampler=lambda rng: (_sample_matrix(rng),),
    ),
    FamilySpec(
        name="longest_bitonic_subarray", split="B", entry_point="longest_bitonic_subarray",
        params="xs",
        golden_body=(
            "def longest_bitonic_subarray(xs):\n"
            "    n = len(xs)\n"
            "    if n == 0:\n"
            "        return 0\n"
            "    inc = [1] * n\n"
            "    for i in range(1, n):\n"
            "        if xs[i] > xs[i - 1]:\n"
            "            inc[i] = inc[i - 1] + 1\n"
            "    dec = [1] * n\n"
            "    for i in range(n - 2, -1, -1):\n"
            "        if xs[i] > xs[i + 1]:\n"
            "            dec[i] = dec[i + 1] + 1\n"
            "    return max(inc[i] + dec[i] - 1 for i in range(n))\n"
        ),
        description=(
            "Write longest_bitonic_subarray(xs) that returns the length of the longest contiguous "
            "subarray that STRICTLY increases to a peak and then STRICTLY decreases (a purely "
            "increasing or purely decreasing run also counts, with an empty far side). 0 for an "
            "empty list, 1 for a single element."
        ),
        example_args=([1, 3, 5, 4, 2],),
        arg_sampler=lambda rng: (_sample_int_list(rng, lo=-9, hi=9, n_lo=0, n_hi=9),),
    ),
    FamilySpec(
        name="validate_iso_date_leapyear", split="B", entry_point="validate_iso_date_leapyear",
        params="s",
        golden_body=(
            "def validate_iso_date_leapyear(s):\n"
            "    parts = s.split('-')\n"
            "    if len(parts) != 3:\n"
            "        return False\n"
            "    y_str, mo_str, d_str = parts\n"
            "    if len(y_str) != 4 or len(mo_str) != 2 or len(d_str) != 2:\n"
            "        return False\n"
            "    if not (y_str.isdigit() and mo_str.isdigit() and d_str.isdigit()):\n"
            "        return False\n"
            "    year, month, day = int(y_str), int(mo_str), int(d_str)\n"
            "    if month < 1 or month > 12:\n"
            "        return False\n"
            "    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\n"
            "    if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):\n"
            "        max_day = 29\n"
            "    else:\n"
            "        max_day = days_in_month[month - 1]\n"
            "    return 1 <= day <= max_day\n"
        ),
        description=(
            "Write validate_iso_date_leapyear(s) returning True iff s is EXACTLY 'YYYY-MM-DD' "
            "(4-digit year, 2-digit month, 2-digit day, dash-separated) AND represents a real "
            "calendar date: month in 1..12, day within that month's actual length, with the "
            "Gregorian leap-year rule for February (divisible by 4, except century years unless "
            "divisible by 400)."
        ),
        example_args=("2024-02-29",),
        arg_sampler=lambda rng: (_sample_iso_date_like(rng),),
    ),
    FamilySpec(
        name="kth_most_common_char", split="B", entry_point="kth_most_common_char",
        params="s, k",
        golden_body=(
            "def kth_most_common_char(s, k):\n"
            "    if not s or k < 1:\n"
            "        return None\n"
            "    counts = {}\n"
            "    first_seen = {}\n"
            "    for i, ch in enumerate(s):\n"
            "        counts[ch] = counts.get(ch, 0) + 1\n"
            "        if ch not in first_seen:\n"
            "            first_seen[ch] = i\n"
            "    ordered = sorted(counts.keys(), key=lambda c: (-counts[c], first_seen[c]))\n"
            "    if k > len(ordered):\n"
            "        return None\n"
            "    return ordered[k - 1]\n"
        ),
        description=(
            "Write kth_most_common_char(s, k) returning the k-th most frequent character in s "
            "(1-indexed; ties broken by first occurrence in s). Return None if s is empty, k < 1, "
            "or k exceeds the number of distinct characters in s."
        ),
        example_args=("aabbbcc", 2),
        arg_sampler=lambda rng: (_sample_string(rng, alphabet="abcd", n_lo=0, n_hi=12), rng.randint(1, 5)),
    ),
    FamilySpec(
        name="minimum_meeting_rooms", split="B", entry_point="minimum_meeting_rooms",
        params="intervals",
        golden_body=(
            "def minimum_meeting_rooms(intervals):\n"
            "    if not intervals:\n"
            "        return 0\n"
            "    starts = sorted(s for s, e in intervals)\n"
            "    ends = sorted(e for s, e in intervals)\n"
            "    rooms = 0\n"
            "    max_rooms = 0\n"
            "    si = ei = 0\n"
            "    n = len(intervals)\n"
            "    while si < n:\n"
            "        if starts[si] < ends[ei]:\n"
            "            rooms += 1\n"
            "            si += 1\n"
            "            max_rooms = max(max_rooms, rooms)\n"
            "        else:\n"
            "            rooms -= 1\n"
            "            ei += 1\n"
            "    return max_rooms\n"
        ),
        description=(
            "Write minimum_meeting_rooms(intervals) where intervals is a list of (start, end) "
            "meeting tuples (possibly overlapping, any order). Return the minimum number of rooms "
            "needed so no two overlapping meetings share a room."
        ),
        example_args=([(0, 30), (5, 10), (15, 20)],),
        arg_sampler=lambda rng: (_sample_intervals_for_rooms(rng),),
    ),
    FamilySpec(
        name="interval_gaps_after_merge", split="B", entry_point="interval_gaps_after_merge",
        params="intervals, lo, hi",
        golden_body=(
            "def interval_gaps_after_merge(intervals, lo, hi):\n"
            "    if not intervals:\n"
            "        merged = []\n"
            "    else:\n"
            "        s = sorted(intervals, key=lambda p: p[0])\n"
            "        merged = [list(s[0])]\n"
            "        for start, end in s[1:]:\n"
            "            if start <= merged[-1][1]:\n"
            "                merged[-1][1] = max(merged[-1][1], end)\n"
            "            else:\n"
            "                merged.append([start, end])\n"
            "    out = []\n"
            "    cur = lo\n"
            "    for start, end in merged:\n"
            "        if start > cur:\n"
            "            out.append((cur, start))\n"
            "        cur = max(cur, end)\n"
            "    if cur < hi:\n"
            "        out.append((cur, hi))\n"
            "    return out\n"
        ),
        description=(
            "Write interval_gaps_after_merge(intervals, lo, hi) where intervals is a list of "
            "(start, end) tuples within [lo, hi] that may be UNSORTED and OVERLAPPING. First merge "
            "any overlapping/touching intervals, then return the list of GAP (start, end) tuples "
            "in [lo, hi] not covered by any (merged) interval."
        ),
        example_args=([(5, 7), (1, 3)], 0, 10),
        arg_sampler=lambda rng: _sample_unsorted_overlapping_intervals(rng),
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
