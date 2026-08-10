#!/usr/bin/env python3
"""Claimcheck — the grounding oracle turned on OURSELVES.

I built this because of what today measured about me rather than about the
system. Eight errors of mine were caught on 2026-08-10; every one was caught by
something outside my reasoning — instrumentation, a peer agent's refutation, a
test, the founder — and **zero** by thinking harder. If that is the real ratio,
then the thing worth building is not a better generator. It is a cheaper,
faster error-catcher, running where I cannot decline it.

`aios_ideation.py` already does this for the outside world: a harvested claim is
refused unless its quoted span appears verbatim in the fetched source. This is
the same oracle pointed inward.

    A number that appears in one of our documents must appear in an artifact
    that the document cites.

That is all it checks, and the modesty is the point. It cannot tell whether a
claim is true, whether the statistic was computed correctly, or whether the
prose around it is honest. It catches exactly one failure — **a number that
drifted away from, or never existed in, the measurement it claims to come
from** — and that failure is not hypothetical here: this repository has already
had to retract two headline claims for exactly it.

Deliberately model-free and deterministic. A checker that asked a model whether
a claim was supported would be the executor grading itself, which is the thing
our own null report says does not work.

    python3 scripts/aios_claimcheck.py                 # every tracked doc
    python3 scripts/aios_claimcheck.py docs/X.md       # one doc
    python3 scripts/aios_claimcheck.py --strict        # exit 1 on unresolved

Schema: aios.claimcheck.v1   Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = "aios.claimcheck.v1"
ROOT = Path(__file__).resolve().parents[1]

# A "claim" is a number specific enough that inventing it would be a real
# fabrication. Round numbers, years and version strings are excluded not because
# they are unimportant but because they collide with everything and would drown
# the signal — an unresolved list nobody reads is the same as no checker.
CLAIM_PATTERNS = [
    ("effect_pp",  r"[+\-−]?\d+\.\d+\s*pp"),          # +8.54pp, −6.25pp
    ("p_value",    r"\bp\s*=\s*0?\.\d+"),              # p=0.0592
    ("ratio",      r"\b\d+\s*/\s*\d+\b"),              # 0/32, 164/164
    ("n_count",    r"\bn\s*=\s*\d+"),                  # n=82
    ("decimal4",   r"\b\d+\.\d{3,}\b"),                # 0.4476, 0.9767
]

# Numbers that match the shapes above but carry no evidential weight.
# Found by the checker's own first run: 369 "unresolved claims" were
# overwhelmingly arXiv identifiers and DOIs, which have the shape of a precise
# decimal but assert nothing. A checker whose output is mostly its own noise
# gets ignored, which is the same as not existing.
NOISE = re.compile(
    r"^(?:19|20)\d\d$"                     # years
    # NO bare M/D rule. Caught by tests/test_claimcheck.py: it ate `0/32`,
    # `2/6` and `0/96` — the ratios this whole repo turns on. Our dates are ISO
    # anyway, so the rule cost everything and bought nothing.
    r"|^v?\d+\.\d+\.\d+$"                 # versions
    r"|^\d{4}\.\d{4,5}$"                   # arXiv ids: 2406.12775
    r"|^10\.\d{4}$"                        # DOI prefixes
    r"|^\d{4}/\d{2}$",                     # 2026/04
)

DOC_GLOBS = ("docs/*.md", "spec/*.md", "*.md")
# Anything in backticks that resolves to a real path is treated as a citation.
CITATION = re.compile(r"`([A-Za-z0-9_./\-]+\.(?:md|py|json|jsonl|txt|toml|yml|yaml))")
# Docs also lean on external papers, cited by identifier rather than by path.
# Those numbers are unverifiable from inside this repo — which is exactly the
# gap `aios_ideation.py` exists to close, since a ledger row carries the source
# digest and a span quoted verbatim from it. So an arXiv id counts as a citation
# **only if we actually absorbed that paper**; otherwise it is reported as work
# to do, not silently accepted.
EXTERNAL_REF = re.compile(r"arxiv[:\s]\s*(\d{4}\.\d{4,5})", re.I)
IDEATION_LEDGER = ROOT / "ideation" / "ledger.jsonl"


def _norm_num(s: str) -> str:
    """Canonical form so '+8.54pp', '8.54 pp' and '8.54' all compare equal.

    Unicode minus is folded to ASCII: our docs use '−' in prose and our JSON
    uses '-', and treating those as different numbers would make the checker
    report drift that does not exist.
    """
    s = s.replace("−", "-").replace(" ", "")
    s = re.sub(r"(pp|%)$", "", s)
    s = re.sub(r"^\+", "", s)
    s = re.sub(r"^(?:p=|n=)", "", s)
    return s


def extract_claims(text: str) -> list[dict]:
    out, seen = [], set()
    # Fenced code and inline code are the artifact's own voice, not a prose
    # claim about it — checking them would flag a doc for quoting its own data.
    body = re.sub(r"```.*?```", " ", text, flags=re.S)
    body = re.sub(r"`[^`\n]*`", " ", body)
    for kind, pat in CLAIM_PATTERNS:
        for m in re.finditer(pat, body):
            raw = m.group(0)
            norm = _norm_num(raw)
            if NOISE.match(norm) or norm in seen:
                continue
            seen.add(norm)
            line = body.count("\n", 0, m.start()) + 1
            out.append({"kind": kind, "raw": raw.strip(), "norm": norm,
                        "line": line})
    return out


def cited_paths(text: str, doc: Path) -> list[Path]:
    paths = []
    for m in CITATION.finditer(text):
        raw = m.group(1)
        for cand in (ROOT / raw, doc.parent / raw):
            if cand.is_file() and cand.resolve() not in {p.resolve() for p in paths}:
                paths.append(cand)
                break
    return paths


def absorbed_sources() -> dict[str, str]:
    """arXiv id -> the text we hold for it, from the ideation ledger.

    This is where the two organs meet. claimcheck finds numbers it cannot
    verify; the ideation cycle is what makes them verifiable. Their composition
    turns a complaint into a queue.
    """
    out = {}
    if not IDEATION_LEDGER.exists():
        return out
    for ln in IDEATION_LEDGER.open(encoding="utf-8"):
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        url = (r.get("source") or {}).get("url", "")
        m = re.search(r"(\d{4}\.\d{4,5})", url)
        if m:
            out[m.group(1)] = " ".join(
                str(r.get(k, "")) for k in ("claim", "evidence", "falsifier"))
    return out


def _rel(p: Path) -> str:
    """Display path. A cited file can resolve OUTSIDE the repo — `.claude/` is a
    symlink here — and that is a legitimate citation, so only the label falls
    back to absolute rather than the citation being dropped."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def evidence_text(paths: list[Path], budget: int = 4_000_000) -> str:
    """Concatenate cited artifacts. Numbers are matched against this blob."""
    chunks, total = [], 0
    for p in paths:
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunks.append(t)
        total += len(t)
        if total > budget:
            break
    return "\n".join(chunks)


def check_doc(doc: Path) -> dict:
    text = doc.read_text(encoding="utf-8", errors="replace")
    claims = extract_claims(text)
    paths = cited_paths(text, doc)
    blob = evidence_text(paths)
    absorbed = absorbed_sources()
    refs = {m.group(1) for m in EXTERNAL_REF.finditer(text)}
    have, missing = sorted(refs & absorbed.keys()), sorted(refs - absorbed.keys())
    blob += "\n" + "\n".join(absorbed[r] for r in have)
    # Numbers inside the evidence are normalised the same way, so a doc saying
    # "+8.54pp" is grounded by a JSON field holding 8.54.
    ev = set()
    for _, pat in CLAIM_PATTERNS:
        for m in re.finditer(pat, blob):
            ev.add(_norm_num(m.group(0)))
    for m in re.finditer(r"-?\d+\.?\d*", blob):
        ev.add(_norm_num(m.group(0)))

    grounded, unresolved = [], []
    for c in claims:
        (grounded if c["norm"] in ev else unresolved).append(c)
    return {
        "doc": _rel(doc),
        "citations": [_rel(p) for p in paths],
        "claims": len(claims),
        "grounded": len(grounded),
        "unresolved": unresolved,
        "external_refs_absorbed": have,
        "external_refs_unabsorbed": missing,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("docs", nargs="*", help="docs to check (default: all)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any claim is unresolved")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-claims", type=int, default=1)
    a = ap.parse_args(argv)

    targets: list[Path] = []
    if a.docs:
        targets = [Path(d) if Path(d).is_absolute() else ROOT / d for d in a.docs]
    else:
        for g in DOC_GLOBS:
            targets.extend(sorted(ROOT.glob(g)))
    targets = [t for t in targets if t.is_file()]

    reports = [check_doc(t) for t in targets]
    reports = [r for r in reports if r["claims"] >= a.min_claims]

    tot_c = sum(r["claims"] for r in reports)
    tot_u = sum(len(r["unresolved"]) for r in reports)
    uncited = [r for r in reports if not r["citations"] and r["claims"]]
    queue: dict[str, list[str]] = {}
    for r in reports:
        for ref in r["external_refs_unabsorbed"]:
            queue.setdefault(ref, []).append(r["doc"])
    summary = {
        "schema": SCHEMA, "docs": len(reports), "claims": tot_c,
        "unresolved": tot_u,
        "docs_with_numbers_but_no_citation": [r["doc"] for r in uncited],
        "absorption_queue": {k: v for k, v in sorted(
            queue.items(), key=lambda kv: -len(kv[1]))},
        "reading": ("unresolved = a number in prose that appears in no artifact "
                    "the document cites. It is NOT proof of a false claim — the "
                    "evidence may live in a repo this checker cannot read, or "
                    "the doc may simply not cite it. It IS proof that the claim "
                    "cannot be checked from here, which for a public record is "
                    "already a defect."),
    }
    if a.json:
        print(json.dumps({"summary": summary, "reports": reports},
                         ensure_ascii=False, indent=1))
    else:
        for r in sorted(reports, key=lambda r: -len(r["unresolved"])):
            if not r["unresolved"]:
                continue
            print(f"\n{r['doc']}  ({r['grounded']}/{r['claims']} grounded, "
                  f"{len(r['citations'])} citations)")
            for c in r["unresolved"][:8]:
                print(f"   L{c['line']:<5} {c['kind']:<10} {c['raw']}")
            if len(r["unresolved"]) > 8:
                print(f"   … +{len(r['unresolved']) - 8} more")
        print(f"\n{tot_c} claims across {len(reports)} docs · "
              f"{tot_c - tot_u} grounded · {tot_u} unresolved")
        if queue:
            top = sorted(queue.items(), key=lambda kv: -len(kv[1]))[:8]
            print(f"\nexternal papers our docs lean on but never absorbed: "
                  f"{len(queue)}  (feed to: aios_ideation.py run --url ...)")
            for ref, docs in top:
                print(f"   arXiv:{ref}  cited by {len(docs)} doc(s)")
        if uncited:
            print(f"docs with numbers but zero citations: {len(uncited)}")
            for d in uncited[:6]:
                print(f"   {d['doc']}  ({d['claims']} numbers)")
    return 1 if (a.strict and tot_u) else 0


if __name__ == "__main__":
    raise SystemExit(main())
