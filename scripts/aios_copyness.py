#!/usr/bin/env python3
"""aios.copyness.v1 — are these agents copies of each other?

The society gate. G5 killed a designed institution built on top of agents that were
copies of one another; what survived was an environment property (the ledger). Before
building any environment for coordination to emerge in, measure the precondition:

    does giving agents DIFFERENT PRIVATE RECORDS make them functionally different?

Why not reuse council/independence.py: its rho is prior-dominated (RHO_BASE 0.39 from
cross-vendor frontier panels, observation moves it only +-0.25). Feed it exact copies and
it still reports n_eff 1.33 at n=5. That prior is calibrated on a different population
than "one model, different private records", so importing it would answer with an
assumption. Here the floor is MEASURED: the COPY arm is the null distribution.

Design (one model throughout, so this is not model diversity):

    COPY   N agents, identical record, different sampling seeds  -> noise floor
    PRIV   N agents, genuinely different records                 -> the hypothesis

crossed with three question kinds:

    record_fact    answer is literally in the record   -> instrument check: PRIV must diverge
    decision       record legitimately bears on it     -> THE MEASUREMENT
    irrelevant     record has no bearing               -> divergence must NOT appear here,
                                                          else what we see is noise not information

Gate passes iff  decision(PRIV) > decision(COPY)  with the CI excluding 0,
AND irrelevant(PRIV) ~= irrelevant(COPY), AND record_fact(PRIV) is near-total.

Disagreement is exact-match on a forced one-token answer. No LLM judge: a judge would
add its own error to the quantity being measured.
"""
from __future__ import annotations
import argparse, json, math, os, random, re, sys, urllib.request
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCS = ROOT / "experiments" / "phase5g" / "g5_arcs"
OUT = ROOT / ".aios" / "copyness"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("COPYNESS_MODEL", "qwen3-coder-next:latest")

DECISIONS = ("RETRY", "ESCALATE", "ABANDON")


def load_arc(path: Path) -> dict | None:
    """Deterministic, LLM-free digest of one arc ledger into a private record."""
    events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if not events:
        return None
    opened = next((e for e in events if e.get("kind") == "arc_opened"), None)
    if not opened:
        return None
    kinds = [e.get("kind") for e in events]
    notes = [str(e.get("text") or e.get("note") or "")[:200]
             for e in events if e.get("kind") in ("note", "progress")]
    return {
        "arc_id": opened.get("arc_id", path.stem),
        "goal": opened.get("goal", ""),
        "oracle_cmd": opened.get("oracle_cmd", ""),
        "constraints": opened.get("constraints", []),
        "n_events": len(events),
        "kinds": kinds,
        "notes": notes[:6],
        "closed": "arc_closed" in kinds,
    }


def render(rec: dict) -> str:
    lines = [
        f"ARC {rec['arc_id']}",
        f"GOAL: {rec['goal']}",
        f"ORACLE COMMAND: {rec['oracle_cmd']}",
        f"CONSTRAINTS: {', '.join(rec['constraints']) or 'none'}",
        f"EVENTS ({rec['n_events']}): {' -> '.join(rec['kinds'][:14])}",
        f"CLOSED: {rec['closed']}",
    ]
    if rec["notes"]:
        lines.append("NOTES:")
        lines += [f"  - {n}" for n in rec["notes"]]
    return "\n".join(lines)


QUESTIONS = {
    # answer is verbatim in the record -> instrument check
    "record_fact": (
        "How many events are in your arc record? "
        "Reply with ONLY the integer, nothing else."),
    # the record legitimately bears on the decision -> the measurement
    "decision": (
        "Based ONLY on your arc record above, what should the next action be? "
        f"Reply with exactly ONE word from: {', '.join(DECISIONS)}. Nothing else."),
    # the record has no bearing -> divergence here would mean noise, not information
    "irrelevant": (
        "Ignore the record entirely. In Python, is a tuple mutable? "
        "Reply with exactly one word: YES or NO. Nothing else."),
}

SYS = ("You are one agent among several. You hold a private work record that other agents "
       "cannot see. Answer from your own record only. Obey the answer format exactly.")


def ask(record_text: str, question: str, temperature: float, seed: int | None,
        timeout: int = 120) -> str | None:
    body = {
        "model": MODEL,
        "prompt": f"YOUR PRIVATE RECORD:\n{record_text}\n\nQUESTION: {question}",
        "system": SYS,
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_predict": 24},
    }
    if seed is not None:
        body["options"]["seed"] = seed
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
    except Exception as e:                       # never silent: a dead call is not agreement
        return None
    return (d.get("response") or d.get("thinking") or "").strip()


def normalize(kind: str, raw: str | None) -> str | None:
    """Exact-match extraction. Returns None when the model did not answer in format —
    those are dropped and COUNTED, never folded into agreement."""
    if not raw:
        return None
    t = raw.strip().upper()
    if kind == "record_fact":
        m = re.search(r"-?\d+", t)
        return m.group(0) if m else None
    if kind == "decision":
        hits = [d for d in DECISIONS if re.search(rf"\b{d}\b", t)]
        return hits[0] if len(hits) == 1 else None
    if kind == "irrelevant":
        y, n = bool(re.search(r"\bYES\b", t)), bool(re.search(r"\bNO\b", t))
        return "YES" if y and not n else ("NO" if n and not y else None)
    return None


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def disagreement(answers: list[str | None]) -> tuple[int, int]:
    """Pairwise disagreement among agents that answered in format."""
    ok = [a for a in answers if a is not None]
    dis = sum(1 for a, b in combinations(ok, 2) if a != b)
    return dis, len(ok) * (len(ok) - 1) // 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", type=int, default=8)
    ap.add_argument("--trials", type=int, default=12, help="independent question instances per cell")
    ap.add_argument("--temperature", type=float, default=0.7,
                    help="deployment-realistic; the COPY floor at THIS temperature is the null")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--tag", default="run")
    a = ap.parse_args()
    if a.smoke:
        a.agents, a.trials = 3, 2

    recs = [r for r in (load_arc(p) for p in sorted(ARCS.glob("*.jsonl"))) if r]
    need = a.agents * a.trials
    if len(recs) < a.agents:
        print(f"FATAL: only {len(recs)} usable arcs, need >= {a.agents}", file=sys.stderr)
        return 2
    print(f"loaded {len(recs)} arc records | model={MODEL} | agents={a.agents} "
          f"trials={a.trials} temp={a.temperature}", flush=True)

    rng = random.Random(20260818)
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / f"copyness_{a.tag}.jsonl"
    fh = log.open("w")
    tally: dict[tuple[str, str], list[int]] = {}
    malformed = 0
    dead = 0

    for trial in range(a.trials):
        pool = rng.sample(recs, a.agents)          # PRIV: one distinct record per agent
        shared = pool[0]                            # COPY: everyone holds the same one
        for kind, q in QUESTIONS.items():
            for cond in ("COPY", "PRIV"):
                answers, raws = [], []
                for i in range(a.agents):
                    rec = shared if cond == "COPY" else pool[i]
                    seed = rng.randrange(1 << 30)   # distinct seeds in BOTH arms
                    raw = ask(render(rec), q, a.temperature, seed)
                    if raw is None:
                        dead += 1
                    ans = normalize(kind, raw)
                    if raw is not None and ans is None:
                        malformed += 1
                    answers.append(ans)
                    raws.append({"agent": i, "arc": rec["arc_id"], "raw": (raw or "")[:120],
                                 "answer": ans})
                dis, pairs = disagreement(answers)
                tally.setdefault((kind, cond), [0, 0])
                tally[(kind, cond)][0] += dis
                tally[(kind, cond)][1] += pairs
                fh.write(json.dumps({"trial": trial, "kind": kind, "cond": cond,
                                     "disagreeing_pairs": dis, "pairs": pairs,
                                     "answered": sum(x is not None for x in answers),
                                     "agents": raws}, ensure_ascii=False) + "\n")
                fh.flush()
        print(f"  trial {trial+1}/{a.trials} done", flush=True)

    print(f"\n{'kind':<14}{'cond':<7}{'disagree':>10}{'pairs':>8}{'rate':>9}   95% CI")
    summary = {}
    for kind in QUESTIONS:
        for cond in ("COPY", "PRIV"):
            d, n = tally.get((kind, cond), [0, 0])
            r = d / n if n else float("nan")
            lo, hi = wilson(d, n)
            summary[f"{kind}/{cond}"] = {"disagree": d, "pairs": n, "rate": r,
                                         "ci": [round(lo, 4), round(hi, 4)]}
            print(f"{kind:<14}{cond:<7}{d:>10}{n:>8}{r:>9.4f}   [{lo:.4f}, {hi:.4f}]")

    def gap(kind):
        p = summary[f"{kind}/PRIV"]; c = summary[f"{kind}/COPY"]
        return p["rate"] - c["rate"], p["ci"][0] - c["ci"][1]   # conservative: PRIV lo - COPY hi

    dec_gap, dec_sep = gap("decision")
    irr_gap, _ = gap("irrelevant")
    fact = summary["record_fact/PRIV"]["rate"]
    verdict = {
        "instrument_ok": fact >= 0.5,
        "decision_excess": round(dec_gap, 4),
        "decision_separated": dec_sep > 0,
        "irrelevant_excess": round(irr_gap, 4),
        "malformed": malformed, "dead_calls": dead,
    }
    verdict["gate"] = bool(verdict["instrument_ok"] and verdict["decision_separated"]
                           and abs(irr_gap) < 0.10)
    print(f"\ninstrument (record_fact PRIV divergence): {fact:.4f}  -> "
          f"{'OK' if verdict['instrument_ok'] else 'BROKEN — records are not reaching the agents'}")
    print(f"decision excess divergence  PRIV-COPY = {dec_gap:+.4f}"
          f"  (CI-separated: {verdict['decision_separated']})")
    print(f"irrelevant excess (must be ~0)        = {irr_gap:+.4f}")
    print(f"malformed answers dropped: {malformed} | dead calls: {dead}")
    print(f"\nGATE: {'PASS — private records make these agents non-copies' if verdict['gate'] else 'FAIL — see above'}")
    fh.write(json.dumps({"summary": summary, "verdict": verdict,
                         "config": vars(a) | {"model": MODEL}}, ensure_ascii=False) + "\n")
    fh.close()
    print(f"\nwrote {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
