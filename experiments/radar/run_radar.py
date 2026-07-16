#!/usr/bin/env python3
"""experiments/radar/run_radar.py -- CLI entry point for the ecosystem radar.

Sweeps every SCRIPTABLE source (sources.py), dedupes against the seen-ledger
(seen.py) so only genuinely NEW items surface, scores what's left against
AIOS's open threads (score.py), and writes a dated digest under
experiments/radar/digests/RADAR_<date>.md. Then it appends the newly-seen ids
to the ledger, so the next run's delta only contains what's new since today.

Idempotent / cron-safe: no TTY interaction, absolute-path-friendly (run from
any cwd, since paths are derived from this file's location), stdlib-only.

Usage:
    python experiments/radar/run_radar.py                 # sweep + write
    python experiments/radar/run_radar.py --dry-run        # preview only
    python experiments/radar/run_radar.py --json           # machine-readable summary
    python experiments/radar/run_radar.py --top-n 15       # more items in "worth a look"

X/Twitter and Threads are SESSION-GATED (need a logged-in browser via the
`council` skill or `insane-search`) -- this script does not and cannot fetch
them; it prints a reminder to check them manually instead.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import score    # noqa: E402
import seen     # noqa: E402
import sources  # noqa: E402

RADAR_DIR = Path(__file__).resolve().parent
DEFAULT_DIGEST_DIR = RADAR_DIR / "digests"


def build_digest(results: dict[str, dict], new_by_source: dict[str, list[dict]],
                  ranked: list[dict], date_str: str, top_n_per_source: int = 8,
                  top_n_ranked: int = 10) -> str:
    """Render the markdown digest. Pure function -- no I/O, easy to test."""
    lines: list[str] = []
    lines.append(f"# AIOS Ecosystem Radar — {date_str}")
    lines.append("")
    lines.append("Continuous scriptable sweep: arxiv (recency-sorted, long-tail-friendly), "
                  "HuggingFace daily papers, GitHub (keyword search, sorted by update), "
                  "Reddit (public JSON listings).")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| source | fetched | new | error |")
    lines.append("|---|---|---|---|")
    for src in sorted(results.keys()):
        r = results[src]
        n_fetched = len(r.get("items", []))
        n_new = len(new_by_source.get(src, []))
        err = r.get("error") or "-"
        lines.append(f"| {src} | {n_fetched} | {n_new} | {err} |")
    lines.append("")

    lines.append("## Worth a Look (ranked by relevance score)")
    lines.append("")
    if not ranked:
        lines.append("_No new items scored above zero this run._")
    for i, it in enumerate(ranked[:top_n_ranked], start=1):
        kws = ", ".join(it.get("matched_keywords", [])) or "-"
        lines.append(f"{i}. **[{it.get('score', 0):.1f}]** {it.get('title', '(untitled)')} "
                      f"({it.get('source')}, {it.get('date', '?')}) — {it.get('url', '')}")
        lines.append(f"   matched: {kws}")
    lines.append("")

    lines.append("## New Items by Source")
    for src in sorted(new_by_source.keys()):
        items = new_by_source[src]
        lines.append("")
        lines.append(f"### {src} ({len(items)} new)")
        if not items:
            lines.append("_none_")
            continue
        for it in items[:top_n_per_source]:
            desc = (it.get("abstract_or_desc") or "")[:160].replace("\n", " ")
            lines.append(f"- {it.get('title', '(untitled)')} ({it.get('date', '?')}) — {it.get('url', '')}")
            if desc:
                lines.append(f"  {desc}")
    lines.append("")

    lines.append("## Session-Gated Sources (not fetched by this script)")
    lines.append("")
    lines.append("X/Twitter and Threads have no stable unauthenticated API as of 2026-07 — "
                  "they require a logged-in browser session. Check them in a live Claude "
                  "session via the `council` skill (Grok/X lane) or `insane-search`, not by "
                  "extending this cron script.")
    for s in sources.SESSION_GATED_SOURCES:
        lines.append(f"- {s}")
    lines.append("")

    return "\n".join(lines)


def run(*, timeout: int = 15, top_n_per_source: int = 8, top_n_ranked: int = 10,
        seen_path: Path = seen.DEFAULT_SEEN_PATH, digest_dir: Path = DEFAULT_DIGEST_DIR,
        dry_run: bool = False, fetch_fn=sources.fetch_all) -> dict:
    """Run one full radar sweep. Returns a JSON-serializable receipt dict.

    `fetch_fn` is injectable so tests can pass a canned fetch without network.
    """
    date_str = time.strftime("%Y-%m-%d")
    results = fetch_fn(timeout=timeout)

    seen_ids = seen.load_seen(seen_path)
    new_by_source: dict[str, list[dict]] = {}
    all_new: list[dict] = []
    for src, r in results.items():
        fresh = seen.filter_new(r.get("items", []), seen_ids)
        new_by_source[src] = fresh
        all_new.extend(fresh)

    ranked = score.rank_items(all_new)

    digest_text = build_digest(results, new_by_source, ranked, date_str,
                                top_n_per_source=top_n_per_source, top_n_ranked=top_n_ranked)

    digest_path = digest_dir / f"RADAR_{date_str}.md"
    wrote_digest = False
    if not dry_run:
        digest_dir.mkdir(parents=True, exist_ok=True)
        digest_path.write_text(digest_text)
        wrote_digest = True

    new_ids = [it["id"] for it in all_new if it.get("id")]
    appended = 0
    if not dry_run:
        appended = seen.append_seen(new_ids, seen_path)

    return {
        "date": date_str,
        "dry_run": dry_run,
        "sources": {src: {"fetched": len(r.get("items", [])), "error": r.get("error")}
                    for src, r in results.items()},
        "new_counts": {src: len(items) for src, items in new_by_source.items()},
        "total_new": len(all_new),
        "top_ranked": [
            {"id": it["id"], "title": it["title"], "source": it["source"],
             "score": it["score"], "url": it["url"]}
            for it in ranked[:top_n_ranked]
        ],
        "digest_path": str(digest_path) if wrote_digest else None,
        "seen_appended": appended,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--timeout", type=int, default=15, help="per-request HTTP timeout (seconds)")
    p.add_argument("--top-n", type=int, default=10, help="items in the ranked 'worth a look' list")
    p.add_argument("--top-n-per-source", type=int, default=8, help="items listed per source in the digest")
    p.add_argument("--dry-run", action="store_true", help="sweep + score + preview, write nothing")
    p.add_argument("--json", action="store_true", help="print the receipt as JSON instead of a summary")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt = run(timeout=args.timeout, top_n_per_source=args.top_n_per_source,
                  top_n_ranked=args.top_n, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0

    print(f"=== AIOS Ecosystem Radar — {receipt['date']} "
          f"{'(dry-run)' if receipt['dry_run'] else ''} ===")
    for src, s in receipt["sources"].items():
        err = f" ERROR: {s['error']}" if s["error"] else ""
        print(f"  {src}: fetched={s['fetched']} new={receipt['new_counts'].get(src, 0)}{err}")
    print(f"\ntotal new: {receipt['total_new']}")
    print("\nTop ranked:")
    for it in receipt["top_ranked"][:5]:
        print(f"  [{it['score']:.1f}] {it['title']} ({it['source']}) — {it['url']}")
    if receipt["digest_path"]:
        print(f"\ndigest written: {receipt['digest_path']}")
    else:
        print("\n(dry-run: no digest or seen-ledger written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
