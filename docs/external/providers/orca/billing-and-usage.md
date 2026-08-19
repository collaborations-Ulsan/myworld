> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Billing & usage

> How OrcaRouter computes charges, the usage object, and OrcaRouter-specific response headers.

## What you pay

OrcaRouter charges you the **upstream provider's published per-token
price**, with no per-token markup. Revenue comes from optional paid
subscription plans, not from inflating your token cost.

If you'd rather your own provider account be invoiced for the tokens,
attach your upstream keys instead — see [BYOK](/operations/byok), which
charges a small platform fee in place of the token price.

## The `usage` object

Every chat/responses response includes a `usage` field:

```json theme={null}
{
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 34,
    "total_tokens": 46
  }
}
```

Reasoning models add `completion_tokens_details.reasoning_tokens` for
the hidden reasoning pass.

## Built-in tool charges

When the response uses a built-in / server-side tool, the call is
counted and billed on top of token usage. OrcaRouter passes the
upstream provider's per-call rate through with no markup; refer to
each provider's pricing page for current rates.

Tools that trigger per-call charges across providers:

* **OpenAI** — `web_search`, `web_search_preview`, `image_generation`
  (Responses API built-in tools)
* **Anthropic** — `web_search` (server tool)
* **Google Gemini** — `googleSearch` grounding (per grounded prompt
  on Gemini 2.x family; per query on Gemini 3.x family)
* **xAI Grok** — `web_search`, `x_search`, `code_interpreter`
  (Agent Tools API on `/v1/responses`)

Specific OpenAI rates currently passed through:

| Tool                 | Per-call rate                                                                                                           |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `web_search`         | \$10 per 1,000 calls (unified across models)                                                                            |
| `web_search_preview` | $10 / 1k for reasoning models (`o3*`, `o4*`, `gpt-5*`); $25 / 1k for non-reasoning models (`gpt-4o*`, `gpt-4.1*`, etc.) |

For other providers' server-tool rates, see each provider's official
pricing page.

## Per-request cost

Send `X-OrcaRouter-Include-Cost: true` and the response's usage object
carries the billed cost of that call (`usage.cost_usd`, or
`usageMetadata.costUsd` on the Gemini surface). For after-the-fact
reconciliation, `GET /v1/generation?id=<request-id>` returns the
settled amount for the `X-Orca-Request-Id` any response carries.

See [Per-request cost](/operations/per-request-cost) for both surfaces.

## OrcaRouter response headers

| Header                  | When set                                              |
| ----------------------- | ----------------------------------------------------- |
| `X-Orca-Request-Id`     | Every response — the id `GET /v1/generation` looks up |
| `X-Orca-Fallback-Level` | Index of the fallback model that served the response  |
| `X-Orca-Fallback-Model` | Name of the fallback model                            |
| `X-Orca-Router`         | Name of the `orcarouter/{name}` router used           |
| `X-Orca-Resolved-Model` | Concrete model a named router resolved to             |

See [Routing / Response Headers](/routing/response-headers) for use cases.

## Looking up your usage

The Dashboard at [orcarouter.ai/console](https://www.orcarouter.ai/console)
shows daily spend, total spend over a chosen window, and a per-model
breakdown. The Dashboard does not currently break spend down per API
key — costs are aggregated at the workspace level.

Two OpenAI-shape billing endpoints are also exposed for programmatic
access:

```bash theme={null}
# Total usage so far (returns an OpenAIUsageResponse with TotalUsage)
curl https://api.orcarouter.ai/v1/dashboard/billing/usage \
  -H "Authorization: Bearer sk-orca-..."

# Remaining quota and expiry (returns OpenAISubscriptionResponse)
curl https://api.orcarouter.ai/v1/dashboard/billing/subscription \
  -H "Authorization: Bearer sk-orca-..."
```

These are summary endpoints — they don't include OpenAI's full
historical day-by-day breakdown.
