> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Per-request cost

> Read the exact billed cost of each request — inline on the response, or looked up afterwards by request id.

Two surfaces answer "what did that call cost me?":

| Surface                                          | What it is                                                                            | When to use it                                                           |
| ------------------------------------------------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `usage.cost_usd` on the response (opt-in header) | A calculation made as the response is emitted, with the same formula settlement uses. | You want the cost inline, with the response you already asked for.       |
| [`GET /v1/generation`](#get-v1generation)        | The amount actually billed, read back from the settled record.                        | You lost the final frame, you're reconciling spend, or the two disagree. |

The billed amount is not reproducible client-side: tiered pricing,
peak/off-peak multipliers, cache read/write ratios, per-call billing,
and minimum-quota rounding all fold into a single number. So OrcaRouter
reports the number it charged, rather than asking you to re-derive it.

If the two surfaces ever disagree, **the lookup is right**. The inline
figure is computed at the moment the response is emitted; settlement
commits afterwards, and a spend policy or agent budget that rejects
settlement can leave the inline number higher than what you were
actually charged. Use the inline field for immediate per-call feedback
and `GET /v1/generation` as the authority.

## Inline cost on the response

Opt in per request with a header:

```
X-OrcaRouter-Include-Cost: true
```

Accepts `true` or `1`, case-insensitive. Anything else — including
absence — means off, and the field never appears for callers who
didn't ask.

The field lands in the response's own usage object, named for the
format **you called** — never the upstream that served it. A
`/v1/chat/completions` request routed to a Gemini upstream still gets
the OpenAI shape:

| Client endpoint                                                     | Field                   |
| ------------------------------------------------------------------- | ----------------------- |
| `/v1/chat/completions`, `/v1/completions`                           | `usage.cost_usd`        |
| `/v1/messages`                                                      | `usage.cost_usd`        |
| `/v1beta/models/{model}:generateContent` / `:streamGenerateContent` | `usageMetadata.costUsd` |

```json OpenAI / Anthropic shape theme={null}
{
  "usage": {
    "prompt_tokens": 1100,
    "completion_tokens": 420,
    "cost_usd": 0.00846
  }
}
```

```json Gemini shape theme={null}
{
  "usageMetadata": {
    "promptTokenCount": 1100,
    "candidatesTokenCount": 420,
    "costUsd": 0.00846
  }
}
```

The older `X-OrcaRouter-beta-usd: response` header still works as a
deprecated alias; prefer `X-OrcaRouter-Include-Cost` in new code.

### Streaming

The cost rides the frame that carries final usage:

* **OpenAI format** — the trailing usage chunk (the one with
  `"choices": []`). Send `stream_options: {"include_usage": true}`,
  since that frame is what carries it.
* **Anthropic format** — the `message_delta` event, alongside the
  final token counts.
* **Gemini format** — frames whose `usageMetadata` reports completion
  tokens. Gemini usage is **cumulative** across a stream, so each
  annotated frame is cost-so-far and the last one is the request
  total. Read the last one; don't sum them.

### When the field is absent

Absent means "no number to report here" — never "this request was
free". The field is omitted when:

* **You didn't opt in.** A vendor's own cost field is stripped rather
  than forwarded — a number OrcaRouter didn't compute is not put under
  its name.
* **The response has no usage object** — error bodies, mid-stream
  content frames. The annotation edits an existing usage report; it
  never invents one.
* **The completion is audio-billed.** Audio-token completions settle
  through a different formula; reporting the text formula's number
  would be wrong rather than merely missing.
* **The surface isn't covered.** Embeddings, rerank, images, audio and
  the native `/v1/responses` endpoint are billed but not annotated
  today. `GET /v1/generation` covers them.
* **The final frame reports zero tokens.** A turn that bills only a
  server-tool fee (web search, grounding) with no output tokens is
  charged but carries no annotated frame. The lookup reports these
  correctly.

## `GET /v1/generation`

Every OrcaRouter response returns an `X-Orca-Request-Id` header. Use it
to read the settled cost after the fact:

```bash theme={null}
curl "https://api.orcarouter.ai/v1/generation?id=$REQUEST_ID" \
  -H "Authorization: Bearer sk-orca-..."
```

```json theme={null}
{
  "data": {
    "id": "20260810120000-abc123",
    "model": "openai/gpt-4o",
    "created_at": 1786360000,
    "streamed": true,
    "token_name": "prod-key",
    "tokens_prompt": 1100,
    "tokens_completion": 420,
    "tokens_total": 1520,
    "total_cost": 0.00123,
    "cost_currency": "USD",
    "quota": 615,
    "latency_ms": 3000,
    "ttft_ms": 210
  }
}
```

* `total_cost` is what the request settled at, in USD.
* `quota` is the internal integer unit `total_cost` was converted
  from — compare it when reconciling against the Console, so you're
  comparing identical integers rather than two roundings.
* `latency_ms` is second-granular (omitted for sub-second requests);
  `ttft_ms` is millisecond-precise.

### Auth and scope

Authenticate with the same `sk-orca-` key you relayed with. The lookup
is scoped to that key's owner and workspace — another tenant's request
id returns `404`, so ids can't be probed. The key's IP allowlist
applies here exactly as on the relay. A disabled or expired key is
refused; a key that merely exhausted its quota can still read its own
receipts.

### Retries and timing

One request id can cover several upstream attempts; the lookup returns
the **terminal** attempt — the outcome you actually experienced. A
request that never succeeded reports `total_cost: 0`.

The settlement record is written after the response completes, so a
lookup fired the instant a stream ends can return `404`. Treat an
early `404` as "not settled yet" and retry briefly before treating it
as missing.

### Not covered

* **Async video / task jobs** (`/v1/video/generations` and other
  submit-and-poll surfaces) settle without the request id and always
  return `404` here. Read task spend from the task record or the
  Console.
* **Routes that fan out** (Routing DSL `parallel` / `synthesize`) bill
  each leg independently; the lookup returns a single leg, not the
  sum. Use the Console for those totals.

### Status codes

| Code  | Meaning                                                                    |
| ----- | -------------------------------------------------------------------------- |
| `400` | `id` missing or blank.                                                     |
| `401` | Key missing, invalid, disabled, or expired.                                |
| `403` | Key restricted to another scope, or your IP is not on the key's allowlist. |
| `404` | Not found, not yet settled, or belongs to another tenant.                  |
| `429` | Over the lookup's own rate limit of 120 requests/minute per user.          |

See also [Billing & usage](/operations/billing-and-usage) for how
charges are computed, and [Response Headers](/routing/response-headers)
for the other `X-Orca-*` headers.
