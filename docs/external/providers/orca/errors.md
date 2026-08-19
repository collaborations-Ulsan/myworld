> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Errors

> HTTP status codes, error envelope, and how to handle upstream vs OrcaRouter errors.

## Error envelope

Most error responses use this OpenAI-compatible JSON shape:

```json theme={null}
{
  "error": {
    "message": "Descriptive error message",
    "type": "orcarouter_api_error",
    "code": "model_not_found"
  }
}
```

`type` is a broad category, `code` is a specific identifier. Some
errors add an `error.metadata` object with structured detail (the
pre-launch gate and the firewall use it). Some fast-path failures
(notably workspace-level 429s) return only an HTTP status code with the
relevant headers and no JSON body.

## HTTP status codes

| Status | Meaning             | Typical cause                                                                                                                                                                                           |
| ------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `400`  | Bad request         | Invalid parameters, missing required fields, schema violation, guardrail or firewall block                                                                                                              |
| `401`  | Unauthorized        | Missing or invalid API key                                                                                                                                                                              |
| `403`  | Forbidden           | Several distinct causes — see [Which 403 is it?](#which-403-is-it)                                                                                                                                      |
| `404`  | Not found           | Model or endpoint doesn't exist                                                                                                                                                                         |
| `425`  | Too early           | The model is announced but not live yet                                                                                                                                                                 |
| `429`  | Too many requests   | Rate limit hit — see [Rate Limits](/operations/rate-limits). Usually carries a `Retry-After` header; a free-tier rejection without one is not retryable at all (see [Free-tier 429s](#free-tier-429s)). |
| `500`  | Internal error      | OrcaRouter-side bug                                                                                                                                                                                     |
| `502`  | Upstream error      | All upstream providers failed (including any fallback chain)                                                                                                                                            |
| `503`  | Service unavailable | The requested model is temporarily unavailable upstream, or your own BYOK key could not be used                                                                                                         |

## Which 403 is it?

A `403` is **not** one condition. Topping up fixes some of them and does
nothing for the others, so check `error.code` and the message before you
act.

| What you see                                                                  | What actually happened                                                                                                                                     | What to do                                                                                                                                        |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Message starting `token cycle spend limit reached, resets at <UTC timestamp>` | The API key hit its recurring **spend limit** (day / week / month, UTC boundaries). The key is valid and your balance is irrelevant.                       | Wait until the UTC instant in the message, or raise/clear the key's cycle limit. **Topping up and editing the key's model list do nothing here.** |
| `insufficient_user_quota`                                                     | Workspace balance exhausted — or a per-member / per-agent monthly budget hard stop (`monthly budget reached for this member` / `... for this agent`).      | Top up, or raise the member/agent budget.                                                                                                         |
| `pre_consume_token_quota_failed`, message `token quota is not enough`         | The **key's own** quota cap is used up. The workspace wallet may still have credit.                                                                        | Raise that key's quota.                                                                                                                           |
| Empty `code`, message `This token has no access to model <model>`             | The model isn't on the key's allowed-model list. Router aliases authorize as a unit — whitelisting the pool members does not unlock `orcarouter/<router>`. | Add the model, or the `orcarouter/<router>` alias, to the key's allowed models.                                                                   |
| `free_quota_exhausted`                                                        | `orcarouter/free` had no free model available to serve the request.                                                                                        | Call a paid model. The free router never escapes to paid capacity on its own.                                                                     |

The cycle spend limit is the one most often misread. It usually arrives
as `access_denied`, but on the realtime/WebSocket path it arrives as
`insufficient_user_quota` — **match the `token cycle spend limit reached`
message, not the code alone.** No `Retry-After` header is sent; the reset
instant is in the message.

Messages may be localized, so prefer `error.code` plus a stable message
prefix over full-string matching.

## Error types you may see in `error.type`

| `error.type`           | Where it comes from                                       |
| ---------------------- | --------------------------------------------------------- |
| `orcarouter_api_error` | Gateway-side failures (auth, quota, rate-limit, internal) |
| `upstream_error`       | The upstream provider returned an error or timed out      |
| `openai_error`         | OpenAI-compat upstream error preserved verbatim           |
| `claude_error`         | Anthropic upstream error preserved verbatim               |
| `gemini_error`         | Gemini upstream error preserved verbatim                  |

## Error codes you may see in `error.code`

These are gateway-issued codes for failures that originate in
OrcaRouter (not the upstream):

| `error.code`                     | HTTP       | Meaning and what to do                                                                                                                                                                                              |
| -------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `insufficient_user_quota`        | 403        | Balance exhausted, or a member/agent budget hard stop. Top up or raise the budget — see [Which 403 is it?](#which-403-is-it).                                                                                       |
| `pre_consume_token_quota_failed` | 403        | This key's own quota cap is used up. Raise the key's quota.                                                                                                                                                         |
| `access_denied`                  | 403        | The key is valid but this request isn't permitted — a cycle spend limit, or the key's IP allowlist. See [Which 403 is it?](#which-403-is-it).                                                                       |
| `free_quota_exhausted`           | 403        | `orcarouter/free` found no free model able to serve the request. Call a paid model — the free router never escapes to paid capacity.                                                                                |
| `model_not_found`                | 503        | This model is not available for your account.                                                                                                                                                                       |
| `model_not_yet_available`        | 425        | The model is announced but not live yet. `error.metadata` carries `expected_window` and `closest_live_alternative` — call the alternative; the same id starts routing automatically at launch, with no code change. |
| `model_price_error`              | 400        | Pricing for this model is not set up. Contact support.                                                                                                                                                              |
| `api_not_implemented`            | 400        | Endpoint or operation not supported for the model you picked.                                                                                                                                                       |
| `bad_request_body`               | 400        | Request body could not be parsed.                                                                                                                                                                                   |
| `prompt_blocked`                 | 400        | Provider safety policy blocked the prompt before generation.                                                                                                                                                        |
| `sensitive_words_detected`       | 400        | Sensitive-content filter rejected the prompt.                                                                                                                                                                       |
| `guardrail_blocked`              | 400        | A workspace [guardrail](/features/guardrails) blocked the request. Don't retry — the same prompt blocks again. Change the input or the policy.                                                                      |
| `firewall_blocked`               | 400        | The [Agent Firewall](/features/firewall) denied a tool in your request. When the policy supplies one, `error.metadata` carries `reason_code`, `factors`, `risk_score`. Drop the tool or adjust the policy.          |
| `firewall_approval_pending`      | 400        | A tool call is held for human approval. The message carries the approval id — resolve it out of band, then re-send the same request with the `X-OrcaRouter-Firewall-Approval` header. A plain retry just re-holds.  |
| `free_rate_limited`              | 429        | Free-tier capacity limit — see [Free-tier 429s](#free-tier-429s).                                                                                                                                                   |
| `byok:key_unavailable`           | 503        | Your workspace's own provider key could not be used — see [BYOK key failures](#byok-key-failures).                                                                                                                  |
| `violation_fee.grok.csam`        | upstream's | The provider flagged the content as CSAM. Terminal — never retried, and a policy-violation fee may be billed.                                                                                                       |

If you need to programmatically distinguish, match on `error.code`
first (specific) and fall back to `error.type` (broad category).

## Free-tier 429s

`free_rate_limited` covers every free-tier rejection, and the message is
identical whichever limit tripped — the ceilings are tuned live and
deliberately unpublished. **`Retry-After` is what tells the two cases
apart**, and they need opposite handling:

| Response                        | Cause                                                                                                                                                                                                           | Correct handling                                                                                                                                                                                                                                |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `429` **with** `Retry-After`    | A rate window is full. Free traffic runs on **fixed windows** — a per-minute bucket and a per-UTC-day bucket, not a sliding window or a token bucket. The value is the seconds left in the window that tripped. | Wait out `Retry-After`, retry once. **Not** exponential backoff: the window refills entirely at its boundary, so backing off further just wastes time. This is the opposite of the guidance for ordinary quota [429s](/operations/rate-limits). |
| `429` **without** `Retry-After` | The request exceeded the free tier's **per-request prompt-token cap**. Nothing about it is time-based.                                                                                                          | Shorten the prompt. Retrying it unchanged fails identically no matter how long you wait.                                                                                                                                                        |

Never parse a limit out of the message — no number in it is guaranteed
to be there, and the same code is also returned when a free-tier channel
times out upstream. Branch on `Retry-After`, not on message text.

See [Free Models](/routing/free-models) for what the tiers govern and how
paying lifts them.

When a free model is saturated OrcaRouter will not quietly roll the
request over to a paid one, so an `extra_body.models` chain won't rescue
it. Call the paid base model instead — free-tier limits never affect it.

## BYOK key failures

`byok:key_unavailable` (`503`) means OrcaRouter could not use your
workspace's own provider key — it failed to decrypt, was stored empty, or
the relay node is missing its secrets key — **and** your workspace forbids
serving the request from platform capacity (platform fallback disabled, or
an `always_use` pin on that provider).

This error stops the whole request: no same-model retry, and **no
cross-model fallback**. An `extra_body.models` chain is skipped entirely,
because every fallback model is just another route to platform capacity —
exactly what the pin forbids. Don't count on a fallback chain to cover it.

Fix: rotate or re-add the workspace key for that provider, or re-enable
platform fallback / remove the `always_use` pin — see
[BYOK](/operations/byok).

A key your provider *rejects* (a 401/403 from the provider itself) is a
different case: you get the provider's own status and message, not this
code. But under the same pinned/no-fallback contract it is equally
terminal — the fallback chain is skipped there too.

## Streaming errors

Errors during a streamed response can't use HTTP status codes (the
status was sent when the stream opened). The format depends on the
endpoint:

### `/v1/chat/completions` and `/v1/responses` (OpenAI-compatible)

The error arrives as an in-band `data: {...}` chunk:

```
data: {"error":{"message":"...","type":"upstream_error","code":""}}

data: [DONE]
```

Parse each `data:` chunk as JSON; if it has an `error` field, treat
the stream as failed.

### `/v1/messages` (Anthropic-compatible)

Anthropic uses SSE named events. A stream failure arrives as:

```
event: error
data: {"type":"error","error":{"type":"overloaded_error","message":"..."}}
```

The stream terminates with `event: message_stop` (or is cut) after
the error event.

## Fallback errors

When `extra_body.models` is set and all models in the chain fail, you
get a `502` with details about the last upstream error. Response
headers `X-Orca-Fallback-Level` and `X-Orca-Fallback-Model` indicate
which fallback was being tried when the chain exhausted. See
[Response Headers](/routing/response-headers).

Some errors terminate the chain outright, so no fallback model is tried
at all: `byok:key_unavailable`, `model_not_yet_available`, and a
saturated free-tier model. Don't rely on a fallback chain to cover those.

Others (`guardrail_blocked`, `firewall_blocked`, `sensitive_words_detected`)
stop the retries on the current model but still let the chain advance —
which usually just reproduces the block on the next model, since the input
is what was rejected.
