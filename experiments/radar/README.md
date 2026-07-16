# AIOS Ecosystem Radar

Founder directive (2026-07-17): keep tracking frontier + long-tail papers on
arxiv — including ones that haven't gotten attention yet — plus X/Twitter,
Threads, Reddit, and GitHub communities, continuously across sessions.

This organ is the **scriptable half** of that directive: a stdlib-only,
cron-safe sweep of every source that has a public, unauthenticated,
script-friendly API. It is a sibling to `scripts/aios_star_radar.py`, not a
replacement — see "Relationship to star_radar" below.

## What it does

1. **`sources.py`** — pulls normalized items (`{id, title, url, date,
   source, abstract_or_desc, signal}`) from:
   - **arxiv API**, sorted by `submittedDate` (NOT relevance/citations) over
     `cs.AI`/`cs.LG`/`cs.CL`/`cs.MA`. Recency sort is the point: it surfaces
     papers that haven't accumulated citations yet, which is exactly the
     long-tail the founder asked for.
   - **HuggingFace** `daily_papers` API (community-submitted, upvote signal).
   - **GitHub search API**, sorted by `updated`, over a small set of
     AIOS-relevant keywords (agent, LLM eval, evolutionary agent, skill
     library).
   - **Reddit** public `.json` listings for r/LocalLLaMA and
     r/MachineLearning (no auth, descriptive User-Agent).
   Each source is wrapped so a timeout/HTTP error/parse failure never takes
   the whole sweep down — see `fetch_all()`.

2. **`seen.py`** — an append-only JSONL ledger (`.aios/radar/seen.jsonl` at
   the repo root — gitignored runtime state, same convention as
   `scripts/aios_star_radar.py`'s `.aios/star_radar/` receipts) keyed by each
   item's stable id. This is what makes the radar *continuous*: every run
   only surfaces items not already recorded.

3. **`score.py`** — a simple weighted-keyword relevance score against AIOS's
   current open threads (compounding loop / self-improvement, verifier &
   verification, reward hacking, memory & continual learning,
   evolutionary/GEPA/genetic methods, long-horizon reliability, ontology,
   local-LLM agents). Deterministic, auditable, no model call.

4. **`run_radar.py`** — the CLI: sweep → dedupe vs. seen → score → write a
   dated digest `experiments/radar/digests/RADAR_<date>.md` → append newly
   seen ids to the ledger. Idempotent (safe to run daily; a same-day re-run
   just shows however much is new *since the last run*, which converges to
   0 within the same day). `--dry-run` previews without writing the seen
   ledger or the digest file.

## Usage

```bash
python experiments/radar/run_radar.py                # sweep, write digest + seen
python experiments/radar/run_radar.py --dry-run       # preview only, no writes
python experiments/radar/run_radar.py --json          # machine-readable receipt
python experiments/radar/run_radar.py --top-n 20      # more items in "worth a look"
```

## Scheduling (not installed by this script — operator/founder decision)

The script is cron-safe: absolute paths derived from `__file__`, no TTY
interaction, bounded per-request timeouts. To run it daily, add a line like
this to your crontab (`crontab -e`) — adjust the interpreter path if you use
a different Python (this repo's default is `/home/user/miniconda3/bin/python3`,
`python3 --version` → 3.13):

```cron
7 6 * * * cd /home/user/workspaces/jaewon/myworld && /home/user/miniconda3/bin/python3 experiments/radar/run_radar.py >> .aios/radar/cron.log 2>&1
```

This is documentation only — the cron entry is **not installed** by this
organ; installing it is an explicit operator/founder action.

## Session-gated sources (NOT fetched by this script)

X/Twitter and Threads have no stable, unauthenticated, script-friendly API
as of 2026-07 — pulling them requires a logged-in browser session. This
organ does **not** fake-fetch them from the cron script. Instead:

- A live Claude session's Ground phase should check them manually via the
  `council` skill (its Grok/X lane) or `insane-search`, and fold anything
  worth keeping into the next digest/memory entry by hand.
- `sources.SESSION_GATED_SOURCES` documents this list in code so the digest
  always prints a reminder instead of silently omitting them.

## Relationship to `scripts/aios_star_radar.py`

`scripts/aios_star_radar.py` already exists and does a related but distinct
job: it tracks **high-momentum GitHub repos** (stars-based, `created:>date
stars:>N`) and uses a **local LLM** to distill each one into an
absorption-candidate, which it writes as **draft MemoryOS objects**. It is
single-source (GitHub only) and requires a local LLM to be serving.

This organ (`experiments/radar/`) is deliberately a different design:

- **Multi-source** (arxiv + HuggingFace + GitHub + Reddit), not GitHub-only.
- **Recency-sorted**, not stars-sorted — the founder's ask was explicitly
  about long-tail/under-noticed work, which a stars/momentum filter would
  systematically exclude.
- **No LLM dependency** — scoring is a deterministic weighted-keyword match,
  so the sweep runs even when no local LLM is serving, and cron-safety
  doesn't depend on model availability.
- **No MemoryOS writes** — it produces a plain markdown digest for a human
  (or a future session) to read; promoting anything into MemoryOS stays a
  separate, explicit step (`aios-memory-propose` skill), keeping this organ
  simple and side-effect-free beyond its own ledger/digest.

They were kept **separate rather than merged** because merging would have
meant either (a) making the GitHub-momentum-plus-LLM-distillation path
depend on arxiv/Reddit fetch machinery it doesn't need, or (b) making this
organ depend on a local LLM being up, which would break "safe to run daily
via cron" — the founder's explicit continuity requirement. Both organs can
run independently on their own schedules.

## Testing

`tests/test_radar.py` — 17 deterministic tests, all mocked/pure (canned
arxiv Atom XML, GitHub JSON, Reddit JSON, HF JSON; no live network). Covers
parsing per source, seen-ledger dedupe (second pass over the same items
surfaces nothing), scoring rank order, digest shape, and dry-run
write-nothing behavior.

Run: `python3 -m pytest tests/test_radar.py -v`
