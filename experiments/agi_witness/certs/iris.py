"""IRIS — the observational-equivalence identifiability certificate (Fable §2 / keystone §2).

IRIS asks one question about a set of candidate programs given a shared-ledger claim set:
*does the observable evidence pin down a SINGLE behavior, or are several distinct behaviors
observationally indistinguishable on everything we can currently measure?* This is causal
identifiability read as decoherence — candidates that agree on every available input collapse
into one **observational-equivalence class**; "identified" means exactly one such class survives
the claims. It makes NO LLM calls — it is a deterministic function of what the candidates DO on
the claim inputs, produced via the shared execution harness (``claims.run_candidate``) — and it
never reads ``Claim.poisoned`` (ground truth for scoring only).

Pipeline (``iris_certify``):
  1. Probe every candidate on every executable-claim INPUT via the sandboxed harness; each
     candidate's **behavioral signature** = the tuple of its (canonicalized) outputs across those
     inputs, with execution failures marked by a sentinel distinct from any real output.
  2. Partition candidates into equivalence classes by identical signature (observational
     equivalence): two candidates in the same class are indistinguishable on the available inputs.
  3. Keep only classes CONSISTENT with the claims — those whose outputs match every executable IO
     claim that actually asserts an output. ``n_classes`` / ``class_sizes`` / ``chosen_class`` /
     ``identified`` describe the surviving set.
  4. If more than one class survives, look for a **discriminating input** among the claim inputs —
     one on which the survivors split into the most distinct outputs. Because the survivors agree
     on every *answer-pinned* input (that's why they survived), only inputs WITHOUT an asserted
     output can discriminate; if none does, ``discriminating_inputs`` is left empty and
     ``identified`` stays False. We never fabricate a new input whose true output we'd have to
     guess — no oracle fabrication (keystone §2c: who certifies the certifier).

Constraints: stdlib + numpy only, deterministic (harness is a pure function of code+args), no
ground-truth reads. Types come from ``contracts.py``; execution + the executable-claim detector
come from ``claims.py`` — this module never reimplements ``run_candidate`` or ``executable_claims``.
"""
from __future__ import annotations

import json
from typing import Any

from contracts import Claim, IrisCert
from claims import executable_claims, run_candidate


# =============================================================================
# Signature primitives
# =============================================================================

# Sentinel token for a cell where the candidate failed to execute (error/timeout/OOM). It is a
# tuple so it can never collide with a real output cell ("ok", <canon>): a failing candidate is
# therefore observationally distinct from any candidate that returned a value, and two candidates
# that both fail on the same input are (honestly) treated as observationally equivalent there.
_FAIL: tuple = ("__exec_fail__",)


def _canon(x: Any) -> str:
    """Canonical, order-stable string form of an output so signatures are hashable and robust to
    unhashable results (lists/dicts from the harness). ``default=str`` never crashes on exotic
    values; ``sort_keys`` makes dict outputs order-independent. Mirrors ``claims._canon`` rather
    than importing a private helper."""
    return json.dumps(x, sort_keys=True, default=str)


def _cell(res) -> tuple:
    """Map one ``ExecResult`` to a hashable signature cell: ``("ok", <canon output>)`` on success,
    the ``_FAIL`` sentinel otherwise. Failures are collapsed to a single token (we do not split by
    error text) — what matters is only that a failure is distinct from a produced value."""
    return ("ok", _canon(res.output)) if res.ok else _FAIL


def _probe(
    candidates: list[str],
    claims: list[Claim],
    func_name: str,
    timeout_s: float,
) -> dict[str, Any]:
    """Run all candidates on all executable-claim inputs and build the equivalence-class partition.

    Returns a dict with:
      * ``inputs``    — the ordered list of executable-claim INPUT arg-lists (probe points);
      * ``asserted``  — per input position, the ``("ok", <canon>)`` cell a candidate MUST produce
        to stay consistent, or ``None`` if that claim asserts no output (a pure probe point);
      * ``signatures``— per candidate, the tuple of cells across ``inputs``;
      * ``classes``   — equivalence classes in first-appearance order, each
        ``{"signature": <tuple>, "members": [candidate idx, ...]}``.
    """
    exec_idx = executable_claims(claims)
    inputs: list[Any] = [claims[i].payload["input"] for i in exec_idx]
    # Consistency target per probe point: only IO claims that actually assert an output constrain
    # the answer; inputs without an "output" key are runnable probes but pin nothing (they can
    # only serve as discriminators, never as consistency constraints).
    asserted: list[tuple | None] = [
        ("ok", _canon(claims[i].payload["output"])) if "output" in claims[i].payload else None
        for i in exec_idx
    ]

    # Behavioral signature per candidate: outputs across every probe input, in a fixed order.
    signatures: list[tuple] = []
    for code in candidates:
        row = tuple(_cell(run_candidate(code, func_name, args, timeout_s=timeout_s))
                    for args in inputs)
        signatures.append(row)

    # Partition by identical signature, preserving first-appearance order for determinism.
    classes: list[dict[str, Any]] = []
    index_of: dict[tuple, int] = {}
    for cand_i, sig in enumerate(signatures):
        if sig not in index_of:
            index_of[sig] = len(classes)
            classes.append({"signature": sig, "members": []})
        classes[index_of[sig]]["members"].append(cand_i)

    return {"inputs": inputs, "asserted": asserted, "signatures": signatures, "classes": classes}


def _is_consistent(signature: tuple, asserted: list[tuple | None]) -> bool:
    """A class's signature is consistent iff it matches every ANSWER-PINNED probe point (positions
    where ``asserted`` is not None). Un-pinned positions impose no constraint."""
    return all(want is None or signature[p] == want for p, want in enumerate(asserted))


def _discriminators(
    surviving: list[dict[str, Any]],
    inputs: list[Any],
) -> list[Any]:
    """Among the SURVIVING classes, find the probe input(s) that split them into the most distinct
    outputs (maximal cross-class disagreement). Returns the raw input(s) achieving the max split,
    but only when that split is genuine (>= 2 distinct outputs) — otherwise the survivors are
    observationally equivalent everywhere available and there is nothing honest to return."""
    best_count = 1
    best: list[Any] = []
    seen_inputs: set[str] = set()
    for p, args in enumerate(inputs):
        key = _canon(args)
        if key in seen_inputs:          # avoid returning the same probe input twice
            continue
        distinct = {cls["signature"][p] for cls in surviving}
        if len(distinct) > best_count:
            best_count = len(distinct)
            best = [args]
            seen_inputs = {key}
        elif len(distinct) == best_count and best_count >= 2:
            best.append(args)
            seen_inputs.add(key)
    return best


# =============================================================================
# The certificate
# =============================================================================

def iris_certify(
    candidates: list[str],
    claims: list[Claim],
    func_name: str,
    *,
    timeout_s: float = 3.0,
) -> IrisCert:
    """Certify how identifiable ``func_name``'s behavior is, given ``candidates`` and ``claims``.

    Runs every candidate on every executable-claim input, groups them into observational-
    equivalence classes, keeps the classes consistent with the claims, and reports:
      * ``n_classes``  — number of surviving consistent classes;
      * ``class_sizes``— their sizes (first-appearance order);
      * ``chosen_class``— index (into ``class_sizes``) of the largest survivor, ``-1`` if none;
      * ``identified`` — True iff exactly one class survives;
      * ``discriminating_inputs`` — when >1 survives, the claim input(s) that best split them
        (empty if the survivors agree on every available input — honest non-identification).
    """
    probe = _probe(candidates, claims, func_name, timeout_s)
    asserted = probe["asserted"]

    # Keep only observationally-distinct classes consistent with every answer-pinned claim.
    surviving = [cls for cls in probe["classes"] if _is_consistent(cls["signature"], asserted)]

    if not surviving:
        # No candidate behavior matches the claims — nothing to identify.
        return IrisCert(n_classes=0, class_sizes=[], chosen_class=-1,
                        discriminating_inputs=[], identified=False)

    class_sizes = [len(cls["members"]) for cls in surviving]
    chosen_class = max(range(len(class_sizes)), key=lambda k: class_sizes[k])  # first largest
    identified = len(surviving) == 1

    discriminating_inputs: list[Any] = []
    if not identified:
        # >1 class survives: surface the input(s) that would most cut down the ambiguity. May be
        # empty if the survivors are indistinguishable on all available inputs (no oracle faked).
        discriminating_inputs = _discriminators(surviving, probe["inputs"])

    return IrisCert(
        n_classes=len(surviving),
        class_sizes=class_sizes,
        chosen_class=chosen_class,
        discriminating_inputs=discriminating_inputs,
        identified=identified,
    )


# =============================================================================
# Self-test (SYNTHETIC candidates + claims only — no dataset.py dependency)
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("certs/iris.py self-test")
    print("=" * 70)

    from contracts import ClaimKind

    # --- 1. Identification: two identical `sorted` candidates + one reverse -----------------
    # Each candidate is f(x) over one list arg; a claim's payload["input"] is the arg-LIST, so
    # f([3,1,2]) is encoded as input=[[3,1,2]] (a one-element args list holding the list).
    sorted_cands = [
        "def f(x): return sorted(x)",   # candidate 0
        "def f(x): return sorted(x)",   # candidate 1 -- byte-identical behavior to 0
        "def f(x): return x[::-1]",     # candidate 2 -- reverses instead of sorts
    ]
    pin_sorted = [
        Claim("t_sort", "gold", ClaimKind.IO, {"input": [[3, 1, 2]], "output": [1, 2, 3]}, ts=0),
    ]

    probe = _probe(sorted_cands, pin_sorted, "f", timeout_s=3.0)
    print("\n[partition]")
    for k, cls in enumerate(probe["classes"]):
        print(f"  class {k}: members={cls['members']}")
    # The two `sorted` candidates are observationally equivalent -> ONE class of size 2; the
    # reverse candidate produces [2,1,3] -> its OWN class. So the raw partition has 2 classes.
    assert len(probe["classes"]) == 2, "sorted/sorted/reverse must form exactly 2 raw classes"
    sizes = sorted(len(c["members"]) for c in probe["classes"])
    assert sizes == [1, 2], "the two `sorted` candidates must collapse (size 2); reverse alone (size 1)"
    print("  PASS: two `sorted` collapse into one class; `reverse` is a separate class")

    cert1 = iris_certify(sorted_cands, pin_sorted, "f", timeout_s=3.0)
    print("\n[iris_certify: pinned sorted]")
    print(f"  n_classes={cert1.n_classes} class_sizes={cert1.class_sizes} "
          f"chosen_class={cert1.chosen_class} identified={cert1.identified} "
          f"discriminating_inputs={cert1.discriminating_inputs}")
    # The claim pins sorted output, so the reverse class is inconsistent and drops out; exactly
    # one (the sorted) class survives -> identified.
    assert cert1.identified is True, "a claim pinning sorted output must leave a unique class"
    assert cert1.n_classes == 1 and cert1.class_sizes == [2]
    assert cert1.chosen_class == 0
    assert cert1.discriminating_inputs == [], "identified -> nothing left to discriminate"
    print("  PASS: pinning sorted output -> unique surviving class (identified=True)")

    # --- 2. Two surviving classes -> a discriminating input must be returned ----------------
    # `sum` and `max` AGREE on the singleton [5] (both -> 5) but DISAGREE on [1,2,3] (6 vs 3).
    # Pin only the [5] point (so both stay consistent) and leave [1,2,3] as an un-pinned probe.
    split_cands = [
        "def f(x): return sum(x)",   # candidate 0
        "def f(x): return max(x)",   # candidate 1
    ]
    split_claims = [
        Claim("t_split", "gold", ClaimKind.IO, {"input": [[5]], "output": 5}, ts=0),  # both -> 5
        Claim("t_split", "probe", ClaimKind.IO, {"input": [[1, 2, 3]]}, ts=1),         # no output
    ]
    cert2 = iris_certify(split_cands, split_claims, "f", timeout_s=3.0)
    print("\n[iris_certify: sum vs max, one pinned agreeing point]")
    print(f"  n_classes={cert2.n_classes} class_sizes={cert2.class_sizes} "
          f"chosen_class={cert2.chosen_class} identified={cert2.identified} "
          f"discriminating_inputs={cert2.discriminating_inputs}")
    assert cert2.identified is False, "sum and max are both consistent with the pinned point"
    assert cert2.n_classes == 2 and cert2.class_sizes == [1, 1]
    assert cert2.chosen_class == 0, "tie -> first (lowest-index) largest class"
    assert len(cert2.discriminating_inputs) >= 1, "a discriminating input must be returned"
    assert [1, 2, 3] in cert2.discriminating_inputs[0], \
        "the discriminator is the un-pinned [1,2,3] probe where sum(6) != max(3)"
    print("  PASS: two consistent classes -> honest discriminating input returned")

    # --- 3. No class consistent with the claims -> chosen_class = -1 ------------------------
    # Pin an output NO candidate produces on [3,1,2] (neither sorted [1,2,3] nor reverse [2,1,3]).
    bad_pin = [
        Claim("t_none", "gold", ClaimKind.IO, {"input": [[3, 1, 2]], "output": [9, 9, 9]}, ts=0),
    ]
    cert3 = iris_certify(sorted_cands, bad_pin, "f", timeout_s=3.0)
    print("\n[iris_certify: impossible pin]")
    print(f"  n_classes={cert3.n_classes} class_sizes={cert3.class_sizes} "
          f"chosen_class={cert3.chosen_class} identified={cert3.identified}")
    assert cert3.n_classes == 0 and cert3.class_sizes == []
    assert cert3.chosen_class == -1 and cert3.identified is False
    print("  PASS: no candidate matches the claim -> chosen_class=-1, identified=False")

    print("\nALL SELF-TEST ASSERTIONS PASSED")
