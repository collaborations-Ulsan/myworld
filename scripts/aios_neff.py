#!/usr/bin/env python3
"""aios.neff.v1 — effective independent votes, computed instead of judged.

Founder: things that should be handled algorithmically should be, and that makes it easier
for the agent. The most load-bearing number in this control plane is a good test of that,
because it currently fails it.

n_eff as we have been quoting it (1.75 across 16 substrates, 1.90 across 20) comes from
council/independence.py, where

    rho = 0.39 literature base  +0.047 same family  +-0.25 from an LLM judge's clustering

so the figure is roughly 60% assumption, 40% one model's opinion, and 0% measurement. It
has been cited about ten times today, including in decisions to abandon panel-based
epistemics. A number that decides things deserves to be measured.

The deterministic version needs no judge and no prior. Force the answer into a closed
format, compare with `==`, and take the pairwise disagreement rate directly:

    rho_hat = 1 - disagreement_rate        agreement among independent draws IS correlation
    n_eff   = n / (1 + (n-1) * rho_hat)    same Kish formula, measured input

Two properties the judged version cannot offer. It is REPLAYABLE — same seeds, same
number, so a change in n_eff means the substrates changed rather than the judge's mood.
And it has a MEASURED FLOOR: run the identical model against itself and the disagreement
you still see is sampling noise, which is what separates real independence from decoding
temperature. copyness measured that floor at 0.0000 on a fact question and 0.0893 on a
decision, with zero malformed answers.

This does not replace judgement everywhere. It replaces it where a criterion can be
written down — and "did these two agents give the same answer" is exactly that.
"""
from __future__ import annotations
import argparse, json, math, sys
from itertools import combinations
from pathlib import Path


def rho_hat(answers: list[str | None]) -> tuple[float, int, int]:
    """Pairwise agreement among in-format answers. None is dropped and counted, never
    folded into agreement — a substrate that failed to answer is not one that agreed."""
    ok = [a for a in answers if a is not None]
    pairs = list(combinations(ok, 2))
    if not pairs:
        return (float("nan"), 0, len(answers))
    agree = sum(1 for a, b in pairs if a == b)
    return (agree / len(pairs), len(pairs), len(answers) - len(ok))


def n_eff(n: int, rho: float) -> float:
    if n <= 1 or math.isnan(rho):
        return float(n)
    return n / (1 + (n - 1) * max(0.0, min(1.0, rho)))


def from_cells(cells: list[list[str | None]]) -> dict:
    """cells: one list of answers per question. Pools rho across questions."""
    agree = tot = dropped = 0
    widths = []
    for ans in cells:
        ok = [a for a in ans if a is not None]
        dropped += len(ans) - len(ok)
        widths.append(len(ok))
        for a, b in combinations(ok, 2):
            tot += 1
            agree += (a == b)
    if not tot:
        return {"status": "no comparable pairs", "n_eff": None}
    r = agree / tot
    n = round(sum(widths) / len(widths)) if widths else 0
    return {"rho_hat": round(r, 4), "pairs": tot, "dropped": dropped,
            "n": n, "n_eff": round(n_eff(n, r), 2),
            "method": "measured pairwise agreement on forced-format answers; "
                      "no judge, no prior"}


def from_copyness(path: Path, kind: str, cond: str) -> dict:
    cells = []
    for line in path.read_text().splitlines():
        if not line.strip().startswith("{"):
            continue
        d = json.loads(line)
        if d.get("kind") == kind and d.get("cond") == cond:
            cells.append([a.get("answer") for a in d.get("agents", [])])
    return from_cells(cells)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copyness", default=".aios/copyness/copyness_main.jsonl")
    a = ap.parse_args()
    p = Path(a.copyness)
    if not p.exists():
        print(f"no data at {p}", file=sys.stderr); return 2

    print("deterministic n_eff — same-model agents, measured not judged\n")
    print(f"{'question':<14}{'cond':<7}{'rho_hat':>9}{'n':>4}{'n_eff':>8}{'pairs':>8}{'dropped':>9}")
    for kind in ("record_fact", "decision", "irrelevant"):
        for cond in ("COPY", "PRIV"):
            r = from_copyness(p, kind, cond)
            if r.get("n_eff") is None:
                continue
            print(f"{kind:<14}{cond:<7}{r['rho_hat']:>9.4f}{r['n']:>4}"
                  f"{r['n_eff']:>8.2f}{r['pairs']:>8}{r['dropped']:>9}")

    print("\ninterpretation")
    fact = from_copyness(p, "record_fact", "COPY")
    priv = from_copyness(p, "record_fact", "PRIV")
    print(f"  identical records -> rho_hat {fact['rho_hat']:.4f}, n_eff {fact['n_eff']:.2f} "
          f"of {fact['n']} — copies, and the method SAYS so")
    print(f"  different records -> rho_hat {priv['rho_hat']:.4f}, n_eff {priv['n_eff']:.2f} "
          f"of {priv['n']} — genuine independence where the record decides")
    dec = from_copyness(p, "decision", "PRIV")
    print(f"  but on the DECISION -> rho_hat {dec['rho_hat']:.4f}, n_eff {dec['n_eff']:.2f} "
          f"— the independence does not reach the action")
    print("\n  The judged version cannot produce the first line: fed exact copies it still "
          "reports n_eff 1.33 at n=5, because 0.39 of its rho is assumed before any data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
