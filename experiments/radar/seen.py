"""experiments/radar/seen.py -- append-only seen-ledger for the radar.

This is what makes the radar "continuous": each run only surfaces items not
already recorded from a prior run. Dedupe key is the item's stable `id`
(e.g. "arxiv:2607.14049", "github:acme/agent", "reddit:LocalLLaMA:abc123").

Storage: one JSON object per line (JSONL), append-only -- never rewritten or
truncated in place, consistent with the AIOS append-only-record convention.
Default location: .aios/radar/seen.jsonl at the repo root -- same convention
as scripts/aios_star_radar.py's receipts (.aios/star_radar/), which keeps
mechanical, ever-growing runtime state out of git (.aios/ is gitignored)
while the digests this ledger feeds (experiments/radar/digests/) stay
tracked as the durable, human-readable record.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEEN_PATH = REPO_ROOT / ".aios" / "radar" / "seen.jsonl"


def load_seen(path: Path = DEFAULT_SEEN_PATH) -> set[str]:
    """Return the set of ids already recorded as seen. Missing file -> empty set."""
    seen: set[str] = set()
    if not path.exists():
        return seen
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = rec.get("id")
        if rid:
            seen.add(rid)
    return seen


def append_seen(ids: list[str], path: Path = DEFAULT_SEEN_PATH) -> int:
    """Append newly-seen ids to the ledger. Returns count written. Idempotent
    in effect (dedup happens at read time via load_seen), but does not
    itself dedupe against prior lines -- callers should only pass ids that
    filter_new() already determined were not seen."""
    if not ids:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with path.open("a") as f:
        for rid in ids:
            f.write(json.dumps({"id": rid, "seen_at": stamp}) + "\n")
    return len(ids)


def filter_new(items: list[dict], seen_ids: set[str]) -> list[dict]:
    """Return the subset of items whose id is not already in seen_ids."""
    return [it for it in items if it.get("id") not in seen_ids]
