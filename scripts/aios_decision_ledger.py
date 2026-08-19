#!/usr/bin/env python3
"""aios.decision_ledger.v1 — every organ call, its context, and what happened after.

Founder asked whether to force organ invocation with few-shot, or to inject RL when the
agent does not know when to call. Both run into the same missing precondition, so this
builds that instead.

Few-shot is the mechanism that already failed: the four-OS query pattern is written in
CLAUDE.md, loaded every session, and the organs took zero calls in seven days. Moving the
reminder into the prompt is the same class of thing. Few-shot shapes HOW; it does not
guarantee WHETHER.

RL needs a reward, and the reward for "was calling the organ right here" is exactly the
delta-U that M2 has failed twice to make identifiable. You cannot train on an outcome you
cannot measure. So the ladder is:

    1  record decision + outcome        <- nobody does this; it is why our routing table
                                          is hand-written
    2  induce a policy from the record  (lookup table first, not a network)
    3  does it beat the FIXED rule?     A1 already warns: a frozen router beat adaptive state
    4  RL / fine-tune                   impossible without 1-3

This is rung 1, and it is CapabilityOS's job as re-derived yesterday.

The ledger records the COUNTERFACTUAL SLOT deliberately: `skipped` entries, where a trigger
matched and we chose not to call. Without those the record only contains calls, every one
looks necessary, and the learned policy is "always call" by construction — the same
selection bias that makes an evaluation loop self-ratifying.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import aios_capabilities as caps                               # noqa: E402

LEDGER = ROOT / ".aios" / "decisions.jsonl"


def record(capability: str, *, called: bool, trigger: str, context: dict | None = None,
           cost_ms: int | None = None, outcome: str | None = None,
           consumed: bool | None = None, note: str = "") -> dict:
    """called=False is as important as called=True — see the docstring."""
    caps.validate(capability)
    rec = {"ts": time.time(), "capability": capability, "called": called,
           "trigger": trigger, "context": context or {}, "cost_ms": cost_ms,
           "outcome": outcome, "consumed": consumed, "note": note[:300],
           "session": os.environ.get("AIOS_MESH_NAME", "")}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def policy_table() -> dict:
    """Rung 2, deliberately the dumbest form: per (capability, trigger), how often the
    output was actually consumed. A lookup table is a policy, and it is the one an adaptive
    router must beat before adaptivity is justified."""
    agg: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"called": 0, "skipped": 0, "consumed": 0, "cost_ms": 0})
    for r in rows():
        k = (r["capability"], r["trigger"])
        if r["called"]:
            agg[k]["called"] += 1
            agg[k]["consumed"] += 1 if r.get("consumed") else 0
            agg[k]["cost_ms"] += r.get("cost_ms") or 0
        else:
            agg[k]["skipped"] += 1
    out = {}
    for (cap, trg), v in agg.items():
        n = v["called"]
        out[f"{cap}|{trg}"] = {
            **v,
            "consumed_rate": round(v["consumed"] / n, 3) if n else None,
            "mean_cost_ms": round(v["cost_ms"] / n) if n else None,
            # the honest label: with no skips there is no counterfactual and no policy
            "identifiable": bool(v["called"] and v["skipped"]),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="subcmd", required=True)
    r = s.add_parser("record")
    r.add_argument("capability"); r.add_argument("trigger")
    r.add_argument("--skipped", action="store_true")
    r.add_argument("--consumed", action="store_true")
    r.add_argument("--cost-ms", type=int); r.add_argument("--note", default="")
    s.add_parser("policy")
    s.add_parser("stats")
    a = ap.parse_args()

    if a.subcmd == "record":
        rec = record(a.capability, called=not a.skipped, trigger=a.trigger,
                     cost_ms=a.cost_ms, consumed=a.consumed or None, note=a.note)
        print(f"{'CALLED' if rec['called'] else 'SKIPPED'} {rec['capability']} "
              f"<- {rec['trigger']}")
    elif a.subcmd == "policy":
        t = policy_table()
        if not t:
            print("empty ledger — nothing has been recorded, so there is no policy to induce.\n"
                  "  That is the honest state, not a bug: rung 1 has to run before rung 2.")
            return 0
        print(f"{'capability|trigger':<44}{'called':>7}{'skip':>6}{'consumed':>10}"
              f"{'cost':>8}  identifiable")
        for k, v in sorted(t.items(), key=lambda kv: -(kv[1]['called'])):
            cr = "—" if v["consumed_rate"] is None else f"{v['consumed_rate']:.2f}"
            print(f"{k[:42]:<44}{v['called']:>7}{v['skipped']:>6}{cr:>10}"
                  f"{str(v['mean_cost_ms'] or '—'):>8}  {v['identifiable']}")
        unid = [k for k, v in t.items() if not v["identifiable"]]
        if unid:
            print(f"\n  {len(unid)} row(s) have no counterfactual (all calls, no skips). "
                  f"A policy induced from these can only say ALWAYS CALL — that is "
                  f"selection bias, not learning.")
    elif a.subcmd == "stats":
        rs = rows()
        print(f"  {len(rs)} decisions  "
              f"called={sum(r['called'] for r in rs)} skipped={sum(not r['called'] for r in rs)}")
        print("  by capability:", dict(Counter(r["capability"] for r in rs).most_common(6)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
