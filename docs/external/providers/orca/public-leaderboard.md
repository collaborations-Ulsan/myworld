> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Public Leaderboard API

> Read the OrcaRouter Arena leaderboard, category boards, trends, and rank badges — public, no API key.

The boards behind [www.orcarouter.ai/leaderboard](https://www.orcarouter.ai/leaderboard)
are served by a set of public read-only endpoints. **No API key, no
auth header** — plain `GET` requests over `https://api.orcarouter.ai`.

Every JSON endpoint returns the standard envelope:

```json theme={null}
{ "success": true, "data": { ... } }
```

Model ids in every payload are **bare slugs** (`deepseek-v4-pro`,
`claude-opus-5`) — the same ids the badge endpoint takes.

<Note>
  The JSON endpoints do **not** send `Access-Control-Allow-Origin`, so a
  browser can't fetch them cross-origin. Call them server-side. The SVG
  badge and the RSS feed *are* CORS-open (`Access-Control-Allow-Origin: *`)
  and embed directly in a page.
</Note>

## Endpoints

| Endpoint                                    | Returns                                                 |
| ------------------------------------------- | ------------------------------------------------------- |
| `GET /api/public/battle-leaderboard`        | Community head-to-head ranking (Bradley–Terry / Wilson) |
| `GET /api/public/leaderboard-categories`    | Per-discipline leaders + skill profiles                 |
| `GET /api/public/leaderboard-trends`        | Rating over time per model                              |
| `GET /api/public/leaderboard-validation`    | Community-vs-external rank correlation                  |
| `GET /api/public/battle-matrix`             | Head-to-head win-rate matrix                            |
| `GET /api/public/reliability-board`         | Success rate, latency, throughput, price                |
| `GET /api/public/volume-board`              | Relative traffic share ranking                          |
| `GET /api/public/benchmark-board`           | Artificial Analysis intelligence vs price               |
| `GET /api/public/composite-board`           | Blended external + first-party ranking                  |
| `GET /api/public/buzz-board`                | Social mentions + sentiment (context only)              |
| `GET /api/public/leaderboard/badge/{model}` | Embeddable SVG rank badge                               |
| `GET /api/public/leaderboard-export`        | Full board as a JSON or CSV download                    |
| `GET /api/public/leaderboard-feed.xml`      | RSS feed of rank changes                                |

## Battle leaderboard

The main board. Ranked by Bradley–Terry rating where a model has enough
distinct opponents, else by Wilson lower-bound win rate.

| Param       | Default | Notes                                   |
| ----------- | ------- | --------------------------------------- |
| `limit`     | `50`    | Clamped to `200`                        |
| `min_votes` | `10`    | Vote floor a model must clear to appear |

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/battle-leaderboard?limit=2&min_votes=10"
```

```json theme={null}
{
  "success": true,
  "data": {
    "min_votes": 10,
    "limit": 2,
    "updated_at": 1786374162,
    "method": "bt",
    "has_bt": true,
    "items": [
      {
        "rank": 1,
        "model": "qwen3.7-max-2026-05-20",
        "display_name": "Qwen3.7 Max (2026-05-20)",
        "provider": "qwen",
        "win_rate": 0.8012422360248447,
        "wilson_lower_bound": 0.7328977296244424,
        "ci_low": 0.7328977296244424,
        "ci_high": 0.8555459642004172,
        "rating": 1450.1,
        "rating_ci_low": 1345.8,
        "rating_ci_high": 1574.7,
        "wins": 129,
        "losses": 32,
        "ties": 7,
        "decisive": 161,
        "vote_count": 168,
        "model_version": "",
        "config_label": "",
        "method": "bt",
        "provisional": false,
        "tied_with_above": false
      }
    ]
  }
}
```

`method` on the envelope is the board's primary method; each row carries
its own `method` too, because one board can mix `bt` rows with
provisional `wilson` rows. The `rating*` fields are populated only for
`method: "bt"` rows.

## Category boards

Per-discipline leaders (top 5 each) plus per-model skill profiles scored
against the category median.

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/leaderboard-categories"
```

```json theme={null}
{
  "success": true,
  "data": {
    "enabled": true,
    "updated_at": 1786374186,
    "categories": [
      {
        "category": "Coding",
        "benchmark_name": "AA Coding",
        "leaders": [
          {
            "model": "claude-opus-5",
            "display_name": "Anthropic: Claude Opus 5",
            "provider": "anthropic",
            "score": 78
          }
        ]
      }
    ],
    "profiles": [
      {
        "model": "gpt-5.4-pro",
        "display_name": "OpenAI: GPT-5.4 Pro",
        "axes": [
          { "category": "Coding", "score": 64.99, "median": 46.6 }
        ]
      }
    ]
  }
}
```

Current categories: `Intelligence`, `Coding`, `Math`, `Reasoning`,
`Knowledge`, `Agentic`.

## Rating trends

Rating snapshots over a rolling window, per model, plus a regression
verdict.

| Param  | Default | Notes                |
| ------ | ------- | -------------------- |
| `days` | `90`    | Clamped to `1`–`365` |

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/leaderboard-trends?days=90"
```

```json theme={null}
{
  "success": true,
  "data": {
    "updated_at": 1786374198,
    "series": [
      {
        "model": "claude-haiku-4.5",
        "display_name": "Anthropic: Claude Haiku 4.5",
        "points": [
          { "t": 1785974400, "rating": 701.4 },
          { "t": 1786060800, "rating": 705.3 }
        ],
        "regression": { "detected": false, "delta": 0, "since": 0 }
      }
    ]
  }
}
```

`t` is a unix timestamp in seconds. `series` is `[]` until the first
snapshot lands.

## Validation

Rank correlation (Spearman ρ, Kendall τ) between the community ranking
and each external source, with the underlying scatter points. No params.

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/leaderboard-validation"
```

```json theme={null}
{
  "success": true,
  "data": {
    "enabled": true,
    "updated_at": 1786374170,
    "sources": [
      {
        "source": "Artificial Analysis Intelligence",
        "spearman": 0.121,
        "kendall": 0.093,
        "n": 31,
        "points": [
          {
            "model": "claude-opus-4.8",
            "display_name": "Anthropic: Claude Opus 4.8",
            "community_rank": 8,
            "external_rank": 4
          }
        ]
      }
    ]
  }
}
```

## Battle matrix

Row model's decisive win rate against the column model, over the top-N
models by vote volume.

| Param       | Default | Notes                                       |
| ----------- | ------- | ------------------------------------------- |
| `limit`     | `12`    | Models per axis, clamped to `30`            |
| `min_votes` | `5`     | Cells below this are flagged `sparse: true` |

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/battle-matrix?limit=4&min_votes=5"
```

```json theme={null}
{
  "success": true,
  "data": {
    "min_votes": 5,
    "updated_at": 1786374210,
    "models": [
      { "model": "gpt-5.4-nano", "display_name": "OpenAI: GPT-5.4 Nano", "provider": "openai" }
    ],
    "cells": [
      {
        "row": "gpt-5.4-nano",
        "col": "gemini-3.5-flash",
        "row_win_rate": 0.7976190476190477,
        "n": 84,
        "sparse": false
      }
    ]
  }
}
```

## Reliability board

Operational health over the last 7 days for every published model.

| Param    | Default | Notes                                         |
| -------- | ------- | --------------------------------------------- |
| `window` | `7d`    | Echoed back; the figures are 7-day regardless |

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/reliability-board"
```

```json theme={null}
{
  "success": true,
  "data": {
    "window": "7d",
    "updated_at": 1786374200,
    "items": [
      {
        "model": "minimax-m3",
        "display_name": "MiniMax: MiniMax M3",
        "provider": "minimax",
        "success_rate_pct": 100,
        "p50_ms": 7941,
        "p99_ms": 10000,
        "error_rate_pct": 0,
        "input_per_million_usd": 0.3,
        "output_per_million_usd": 1.2,
        "tokens_per_sec": 150.85,
        "has_data": true
      }
    ]
  }
}
```

## Volume board

Traffic ranking. The public payload is **relative only** — rank, share
and trend, never absolute token or request counts.

| Param    | Default | Notes                     |
| -------- | ------- | ------------------------- |
| `window` | `30d`   | `24h`, `7d`, `30d`, `all` |

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/volume-board?window=30d"
```

```json theme={null}
{
  "success": true,
  "data": {
    "window": "30d",
    "window_days": 30,
    "updated_at": 1786374219,
    "warm": true,
    "phase": "mature",
    "below_threshold_count": 24,
    "ranked": [
      { "rank": 1, "model": "deepseek-v4-flash", "provider": "deepseek", "share": 0.214, "trend": 0 }
    ]
  }
}
```

`phase` is `cold` (still warming, `ranked` empty), `growing`, or
`mature`.

## Benchmark board

Artificial Analysis intelligence index against price and throughput.
`on_pareto` marks models on the intelligence/price frontier. No params.

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/benchmark-board"
```

```json theme={null}
{
  "success": true,
  "data": {
    "enabled": true,
    "updated_at": 1786374190,
    "attribution": "Artificial Analysis",
    "items": [
      {
        "model": "gpt-5.4-pro",
        "display_name": "OpenAI: GPT-5.4 Pro",
        "provider": "openai",
        "intelligence": 65.99,
        "input_per_million_usd": 60,
        "output_per_million_usd": 270,
        "tokens_per_sec": 429.87,
        "on_pareto": true
      }
    ]
  }
}
```

## Composite board

External benchmark/adoption/preference signals blended with first-party
battle evidence into one score.

| Param     | Default | Notes                                                      |
| --------- | ------- | ---------------------------------------------------------- |
| `segment` | `text`  | `text`, `coding`, `vision`, `math`, `reasoning`, `agentic` |

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/composite-board?segment=text"
```

```json theme={null}
{
  "success": true,
  "data": {
    "enabled": true,
    "segment": "text",
    "updated_at": 1786343903,
    "weights": { "preference": 0.4, "benchmarks": 0.3, "firstparty": 0.2, "adoption": 0.1 },
    "items": [
      {
        "rank": 1,
        "model": "claude-opus-5",
        "display_name": "Anthropic: Claude Opus 5",
        "provider": "anthropic",
        "composite": 74.3,
        "provisional": true,
        "source_count": 2,
        "input_per_million_usd": 5,
        "output_per_million_usd": 25,
        "signals": { "aa_intelligence": 63.1, "openrouter_share_pct": 1.93 }
      }
    ],
    "attribution": [
      "LMArena leaderboard dataset (CC-BY-4.0) — lmarena.ai",
      "Source: OpenRouter (openrouter.ai/rankings)",
      "SWE-bench Verified — swebench.com",
      "Artificial Analysis — artificialanalysis.ai"
    ]
  }
}
```

The `attribution` lines are the citations the upstream source licenses
require. Render them verbatim wherever you display this board.

## Buzz board

Social mentions and sentiment split per model, plus a `trending` rail of
top movers. Context only — buzz never feeds any ranking. No params.

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/buzz-board"
```

```json theme={null}
{
  "success": true,
  "data": {
    "enabled": true,
    "updated_at": 1786374230,
    "items": [
      {
        "model": "dub",
        "display_name": "OrcaDub: OrcaDub 1.0",
        "provider": "orca",
        "mentions_7d": 256,
        "mentions_prev_7d": 166,
        "trend_pct": 54.2,
        "sentiment_positive_pct": 3.1,
        "sentiment_neutral_pct": 93.4,
        "sentiment_negative_pct": 3.5
      }
    ],
    "trending": [
      { "model": "muse-spark-1.2", "display_name": "Meta: Muse Spark 1.2", "trend_pct": 600 }
    ]
  }
}
```

<Note>
  `benchmark-board`, `composite-board`, `leaderboard-categories`,
  `leaderboard-validation` and `buzz-board` carry third-party data and can
  be turned off. When off they return `{"enabled": false}` with empty
  arrays rather than an error — branch on `enabled`, don't assume rows.
</Note>

## Rank badge

`GET /api/public/leaderboard/badge/{model}` returns a shields.io-style
SVG you can embed in a README or landing page. A trailing `.svg` is
accepted and ignored.

| Param      | Default   | Notes                                                 |
| ---------- | --------- | ----------------------------------------------------- |
| `category` | `overall` | `overall`, or a category name from the category board |

`{model}` is the bare slug and must match `^[a-z0-9._-]+$`.

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/leaderboard/badge/claude-opus-5?category=coding"
```

```
Content-Type: image/svg+xml; charset=utf-8
Cache-Control: public, max-age=900
Access-Control-Allow-Origin: *
```

The badge reads `OrcaRouter Arena │ #1 coding · Anthropic: Claude Opus 5`.

**Markdown:**

```markdown theme={null}
[![Claude Opus 5 rank on OrcaRouter](https://api.orcarouter.ai/api/public/leaderboard/badge/claude-opus-5?category=coding)](https://www.orcarouter.ai/leaderboard)
```

**HTML:**

```html theme={null}
<a href="https://www.orcarouter.ai/leaderboard">
  <img src="https://api.orcarouter.ai/api/public/leaderboard/badge/claude-opus-5?category=coding"
       alt="Claude Opus 5 rank on OrcaRouter" height="20" />
</a>
```

**iframe:**

```html theme={null}
<iframe src="https://api.orcarouter.ai/api/public/leaderboard/badge/claude-opus-5?category=coding"
        width="420" height="24" frameborder="0" title="Claude Opus 5 rank on OrcaRouter"></iframe>
```

The SVG is 20px tall and its width grows with the label, so leave the
width to the intrinsic size (or give the iframe room — a long display
name pushes past 400px).

`category=overall` ranks against the full community board.
Any other category ranks against that category's leaders, which is a
top-5 list — a model outside it is not ranked there. An unknown or
unranked model returns a neutral `unranked` badge with HTTP `404`, so
the image still renders instead of breaking.

## Export

`GET /api/public/leaderboard-export` downloads the full community board
(up to 200 rows) as a file, `Content-Disposition: attachment`.

| Param       | Default | Notes                   |
| ----------- | ------- | ----------------------- |
| `format`    | `json`  | `json` or `csv`         |
| `min_votes` | `10`    | Same floor as the board |

```bash theme={null}
curl -O -J "https://api.orcarouter.ai/api/public/leaderboard-export?format=csv"
```

Saves `orcarouter-leaderboard-YYYY-MM-DD.csv`:

```csv theme={null}
rank,model,display_name,provider,rating,rating_ci_low,rating_ci_high,win_rate,wins,losses,ties,vote_count,method,provisional
1,qwen3.7-max-2026-05-20,Qwen3.7 Max (2026-05-20),qwen,1450.1,1345.8,1574.7,0.8012422360248447,129,32,7,168,bt,false
```

`format=json` writes the same rows as a bare JSON array — no `{success,
data}` envelope, since it's a file body.

## Rank-change feed

`GET /api/public/leaderboard-feed.xml` is an RSS 2.0 feed of models
entering the board, climbing, or slipping. Point any reader or
Slack/Discord RSS bot at it.

| Param  | Default | Notes           |
| ------ | ------- | --------------- |
| `days` | `30`    | Lookback window |

```bash theme={null}
curl "https://api.orcarouter.ai/api/public/leaderboard-feed.xml"
```

```xml theme={null}
<rss version="2.0"><channel>
  <title>OrcaRouter Arena — Leaderboard Changes</title>
  <link>https://www.orcarouter.ai/leaderboard</link>
  <item>
    <title>Anthropic: Claude Opus 4.7 slipped to #2 (from #1)</title>
    <link>https://www.orcarouter.ai/leaderboard</link>
    <guid isPermaLink="false">orcarouter-rank:down:claude-opus-4.7:1786320000</guid>
    <pubDate>Mon, 10 Aug 2026 00:00:00 +0000</pubDate>
  </item>
</channel></rss>
```

Before the first snapshot lands the feed is a valid, empty `<channel>`.
`guid` is a stable synthetic id — dedupe on it across polls.

## Caching and rate limits

These endpoints are `Cache-Control`-tagged for shared caches:

| Surface                              | `max-age` |
| ------------------------------------ | --------- |
| Boards, export                       | `300`     |
| Trends, badge, RSS feed              | `900`     |
| Boards still warming after a restart | `10`      |

There is no per-endpoint quota, but the shared per-IP limit that
protects every `/api` route applies. Over it you get an HTTP `429` with
`Retry-After` in seconds — back off and retry, as described in
[Rate Limits](/operations/rate-limits). Respect `Cache-Control` rather
than polling: the underlying boards only recompute on their own
schedule, so a tighter poll returns identical bytes.

Errors return `{"success": false, "message": "..."}` with HTTP `500`.
Malformed query params never error — an unparseable `limit`, `days` or
`window` falls back to its default.
