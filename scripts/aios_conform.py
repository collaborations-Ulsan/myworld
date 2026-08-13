#!/usr/bin/env python3
"""Conformance checker for AIOS Seam v0 — the normative half of the spec.

`spec/aios-seam-v0.md` says this checker is normative and prose is not. Writing
that sentence without shipping the checker would have been the exact failure
this repository spent a day measuring: a mechanism offered and never used.

Two independent things are verified:

  1. **Receipt shape** — every clause from spec §2, each of which exists to
     reject a specific fake. A cycle that only emits receipts when it succeeds
     is not a verified cycle, so `reverted` receipts are checked as strictly as
     `committed` ones.
  2. **Ledger identity** — the leaf/root rule from spec §1, RE-IMPLEMENTED HERE
     from the prose rather than imported. That is deliberate. If this file
     imported `aios_society.merkle_root`, agreement would prove only that a
     function equals itself; reimplementing it is the smallest possible stand-in
     for the foreign implementation the spec demands.

It imports nothing from AIOS. If it ever needs to, the seam is not a seam.

    python3 scripts/aios_conform.py ideation/receipts.jsonl --ledger ideation/ledger.jsonl
    python3 scripts/aios_conform.py --m0 ideation/receipts.jsonl --ledger ideation/ledger.jsonl

Exit 0 = conforming. Exit 1 = a violation, printed with the clause it broke.
Schema: aios.conformance.v0   Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _h(b: str) -> str:
    return "sha256:" + hashlib.sha256(b.encode("utf-8")).hexdigest()


def leaf(i: int, line: str) -> str:
    """spec §1: position-salted so reordering a history changes the root."""
    return _h(f"{i}\x00{line}")


def root(leaves: list[str]) -> str:
    """spec §1: sort, then fold pairs; an odd tail element pairs with itself."""
    if not leaves:
        return _h("")
    layer = sorted(leaves)
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i + 1] if i + 1 < len(layer) else layer[i]
            nxt.append(_h(a + b))
        layer = nxt
    return layer[0]


def ledger_root(path: Path) -> str:
    if not path.exists():
        return root([])
    lines = [ln.rstrip("\n") for ln in path.open(encoding="utf-8")]
    return root([leaf(i, ln) for i, ln in enumerate(lines)])


# --- spec §2, one function per clause so a violation names its own rule -----

REQUIRED = {
    "sense": ("predicate", "evaluated_by", "input_digest", "model_consulted"),
    "act": ("operator", "invoked_by", "model_offered_choice"),
    "verify": ("oracle_cmd_digest", "verdict", "verifier_identity"),
    "settle": ("outcome", "root_before", "root_after"),
}


def check_receipt(r: dict) -> list[str]:
    bad = []
    for member, keys in REQUIRED.items():
        if not isinstance(r.get(member), dict):
            bad.append(f"missing member: {member}")
            continue
        for k in keys:
            if k not in r[member]:
                bad.append(f"{member}.{k} missing")
    if bad:
        return bad

    s, a, v, t = r["sense"], r["act"], r["verify"], r["settle"]
    if s["model_consulted"] is not False:
        bad.append("sense.model_consulted must be false — otherwise an OFFER "
                   "can claim the cycle, and offers measured zero")
    if a["invoked_by"] != "host":
        bad.append("act.invoked_by must be 'host'")
    if a["model_offered_choice"] is not False:
        bad.append("act.model_offered_choice must be false")
    if v["verifier_identity"] == a["operator"]:
        bad.append("verify.verifier_identity == act.operator — executor is "
                   "grading itself")
    if v["verdict"] not in {"pass", "fail"}:
        bad.append(f"verify.verdict not in pass|fail: {v['verdict']!r}")
    if t["outcome"] not in {"committed", "reverted"}:
        bad.append(f"settle.outcome not in committed|reverted: {t['outcome']!r}")
    if t["root_before"] == t["root_after"]:
        bad.append("settle.root_before == root_after — settled without writing")
    expect = "committed" if v["verdict"] == "pass" else "reverted"
    if t["outcome"] != expect:
        bad.append(f"verdict={v['verdict']} but outcome={t['outcome']} — the "
                   "verdict is decoration if it does not bind the outcome")
    # spec §2b — separation. Optional members, but once `executes_code` is
    # declared true the isolation claim becomes load-bearing and is enforced.
    ISOLATION = {"same_process", "separate_process", "remote", "sandboxed"}
    iso = v.get("isolation")
    if iso is not None and iso not in ISOLATION:
        bad.append(f"verify.isolation not in {sorted(ISOLATION)}: {iso!r}")
    if a.get("executes_code") is True:
        if iso is None:
            bad.append("act.executes_code=true but verify.isolation is absent — "
                       "an executor that runs code must show the boundary")
        elif iso == "same_process":
            bad.append("act.executes_code=true with verify.isolation="
                       "'same_process' — the verifier is inside the trust "
                       "domain it judges and can be rewritten by it")
    # spec §2c — binding. An edge that fired and was then dropped is a new
    # zero, so the receipt has to show its output entering the act's input.
    e = r.get("edge")
    if isinstance(e, dict):
        for k in ("edge_id", "invoked_by", "output_digest"):
            if k not in e:
                bad.append(f"edge.{k} missing")
        if not bad:
            if e["invoked_by"] != "host":
                bad.append("edge.invoked_by must be 'host' — an edge the model "
                           "chose to call is an offer, and offers measured zero")
            if not DIGEST.match(str(e["output_digest"])):
                bad.append(f"edge.output_digest is not sha256:<64 hex>: "
                           f"{e['output_digest']!r}")
            ctx = a.get("context_components")
            if not isinstance(ctx, list):
                bad.append("edge present but act.context_components missing — "
                           "nothing shows the edge output reached the act")
            elif e["output_digest"] not in ctx:
                bad.append("edge.output_digest not in act.context_components — "
                           "the edge fired and its result was ignored, which is "
                           "an invocation without a use")
    elif e is not None:
        bad.append(f"edge must be an object, got {type(e).__name__}")
    # spec §2d — exact-byte delivery (D1) and the uptake canary (U0).
    ai = r.get("act_input")
    if isinstance(ai, dict):
        comps = ai.get("components")
        if not isinstance(comps, list) or not comps:
            bad.append("act_input.components missing — a manifest with no "
                       "components tiles nothing")
        elif not isinstance(ai.get("length"), int):
            bad.append("act_input.length missing — spans cannot be checked "
                       "against an unknown input size")
        else:
            if ai.get("assembled_by") == a.get("operator"):
                bad.append("act_input.assembled_by == act.operator — a "
                           "description of the input written by the thing being "
                           "described is not evidence")
            cursor, ok = 0, True
            for c_ in sorted(comps, key=lambda x: x.get("start", -1)):
                st, en = c_.get("start"), c_.get("end")
                if not isinstance(st, int) or not isinstance(en, int) or en <= st:
                    bad.append(f"act_input component has no usable span: {c_!r}")
                    ok = False
                    break
                if st != cursor:
                    bad.append(f"act_input components do not tile the input: "
                               f"gap or overlap at byte {cursor} (next starts "
                               f"{st}) — an untiled manifest lets a producer "
                               f"name the edge and assemble something else")
                    ok = False
                    break
                cursor = en
            if ok and cursor != ai["length"]:
                bad.append(f"act_input components cover {cursor} of "
                           f"{ai['length']} bytes — the manifest must account "
                           f"for every byte of the input")
            if isinstance(e, dict) and e.get("output_digest"):
                spans = [c_ for c_ in comps if c_.get("digest") == e["output_digest"]]
                if not spans:
                    bad.append("edge.output_digest has no byte range in "
                               "act_input.components — declared, not delivered")
    elif ai is not None:
        bad.append(f"act_input must be an object, got {type(ai).__name__}")

    up = r.get("uptake")
    if isinstance(up, dict):
        need = ("nonce", "act_id", "selected_action", "commitment")
        miss = [k for k in need if k not in up]
        if miss:
            bad.append(f"uptake missing {miss} — the canary is unverifiable")
        else:
            want = _h(f"{up['nonce']}{up['act_id']}{up['selected_action']}")
            if want != up["commitment"]:
                bad.append("uptake.commitment does not recompute — the act did "
                           "not carry a value that existed only inside the edge")
    elif up is not None:
        bad.append(f"uptake must be an object, got {type(up).__name__}")

    for member, key in (("sense", "input_digest"), ("verify", "oracle_cmd_digest"),
                        ("settle", "root_before"), ("settle", "root_after")):
        val = r[member][key]
        if not DIGEST.match(str(val)):
            bad.append(f"{member}.{key} is not sha256:<64 hex>: {val!r}")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("receipts", type=Path)
    ap.add_argument("--ledger", type=Path, default=None)
    ap.add_argument("--m0", action="store_true",
                    help="also judge whether the minimal operation is LIT")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    rows, parse_errors = [], []
    for n, ln in enumerate(a.receipts.open(encoding="utf-8")):
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"line {n}: {exc}")

    violations = []
    for n, r in enumerate(rows):
        for msg in check_receipt(r):
            violations.append({"receipt": n, "violation": msg})

    ledger = {}
    if a.ledger:
        computed = ledger_root(a.ledger)
        # The last receipt claims the root it produced; an independent
        # recomputation of the whole history must land on the same value.
        claimed = rows[-1]["settle"]["root_after"] if rows else None
        ledger = {"path": str(a.ledger), "recomputed_root": computed,
                  "last_receipt_root_after": claimed,
                  "agrees": computed == claimed}
        if not ledger["agrees"]:
            violations.append({"receipt": len(rows) - 1,
                               "violation": "ledger root recomputed from the "
                               "spec does not match the last receipt"})

    conforming = [n for n in range(len(rows))
                  if not any(v["receipt"] == n for v in violations)]
    reverted = [n for n in conforming
                if rows[n]["settle"]["outcome"] == "reverted"]

    out = {
        "schema": "aios.conformance.v0",
        "receipts": len(rows), "conforming": len(conforming),
        "violations": violations, "parse_errors": parse_errors,
        "ledger": ledger,
    }
    if a.m0:
        out["m0"] = {
            "lit": bool(conforming) and bool(reverted),
            "conforming_receipts": len(conforming),
            "reverted_receipts": len(reverted),
            "rule": ("a conforming receipt exists AND at least one of them was "
                     "REVERTED — without an executed revert the rejection path "
                     "is code that has never run, which is lit-looking, not lit"),
        }

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"receipts {len(rows)} · conforming {len(conforming)} · "
              f"violations {len(violations)}")
        for v in violations[:12]:
            print(f"  receipt[{v['receipt']}] {v['violation']}")
        if ledger:
            print(f"ledger root recomputed independently: "
                  f"{'AGREES' if ledger['agrees'] else 'DISAGREES'}")
        if a.m0:
            m = out["m0"]
            print(f"\nM0 {'LIT' if m['lit'] else 'NOT LIT'} — "
                  f"{m['conforming_receipts']} conforming, "
                  f"{m['reverted_receipts']} reverted")
    return 1 if (violations or parse_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
