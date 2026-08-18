> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Web search

> Let the model search the web before answering — via search-preview models or web_search_options.

Two paths to web search through OrcaRouter:

1. **Search-preview models** — call a search variant directly via `/v1/chat/completions`
2. **Tools / options on a regular model** — pass `web_search_options` (Chat) or `tools: [{"type": "web_search"}]` (Responses)

## Search-preview models (OpenAI)

OpenAI publishes search-preview variants for several models — for
example `openai/gpt-4o-search-preview` and `openai/gpt-5-search-api`.
Pick one of these as `model` on `/v1/chat/completions` and the upstream
handles search server-side.

Call `/v1/models` for the live catalog.

## web\_search\_options (Chat Completions)

```bash theme={null}
curl https://api.orcarouter.ai/v1/chat/completions \
  -H "Authorization: Bearer sk-orca-..." \
  -d '{
    "model": "openai/gpt-4o-search-preview",
    "messages": [{"role": "user", "content": "What changed in OpenAI pricing this week?"}],
    "web_search_options": {"search_context_size": "medium"}
  }'
```

`search_context_size`: `low` / `medium` / `high`. Controls search
depth (per-call price for `web_search` is the same regardless of size).

## Tools (Responses API)

`/v1/responses` accepts `tools: [{"type": "web_search"}]` on both OpenAI
models and any Grok model — xAI's Agent Tools surface lives at the
same endpoint.

```bash theme={null}
# OpenAI
curl https://api.orcarouter.ai/v1/responses \
  -H "Authorization: Bearer sk-orca-..." \
  -d '{
    "model": "openai/gpt-5",
    "input": "What changed in OpenAI pricing this week?",
    "tools": [{"type": "web_search"}]
  }'

# Grok (xAI Agent Tools)
curl https://api.orcarouter.ai/v1/responses \
  -H "Authorization: Bearer sk-orca-..." \
  -d '{
    "model": "grok/grok-4-fast-reasoning",
    "input": "What changed in xAI pricing this week?",
    "tools": [{"type": "web_search"}]
  }'
```

Each `web_search_call` the upstream emits is counted for billing — see
[Operations / Billing & Usage](/operations/billing-and-usage).

## Cross-provider support

Web search reaches every provider that exposes it; only the entry
point differs:

| Provider  | Web search | How                                                                                                                                                                                                                                               |
| --------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OpenAI    | ✅          | Search-preview models, or pass `web_search` tool to `/v1/responses`                                                                                                                                                                               |
| xAI Grok  | ✅          | Call `/v1/responses` with `tools: [{"type": "web_search"}]` and any Grok model — xAI's Agent Tools API. (xAI deprecated the legacy `search_parameters` on chat completions on 2026-01-12; the old `*-search` model-name variants no longer work.) |
| Anthropic | ✅          | Pass `web_search_options` on a Chat Completions request — translated to Anthropic's native `web_search` server-tool. `search_context_size` (low/medium/high) maps to `max_uses`; `user_location.approximate` maps to Anthropic's `user_location`. |
| Gemini    | ✅          | Pass a function tool named `googleSearch` (see below) — translated to Gemini's native `GoogleSearch` grounding tool.                                                                                                                              |
| DeepSeek  | ❌          | DeepSeek API does not expose web search.                                                                                                                                                                                                          |

## Gemini grounding via `googleSearch`

For Gemini models, OrcaRouter's translation layer recognizes a
**magic function name** `googleSearch` and turns it into Gemini's
native `GoogleSearch` grounding tool. Send it like any other
OpenAI-style function tool:

<CodeGroup>
  ```bash cURL theme={null}
  curl https://api.orcarouter.ai/v1/chat/completions \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "model": "google/gemini-2.5-flash",
      "messages": [{"role":"user","content":"What changed in Gemini pricing this week?"}],
      "tools": [{"type":"function","function":{"name":"googleSearch"}}]
    }'
  ```

  ```python Python theme={null}
  resp = client.chat.completions.create(
      model="google/gemini-2.5-flash",
      messages=[{"role": "user", "content": "What changed in Gemini pricing this week?"}],
      tools=[{"type": "function", "function": {"name": "googleSearch"}}],
  )
  ```
</CodeGroup>

The grounding metadata Gemini returns (`webSearchQueries`, etc.) is
captured by the gateway for billing and surfaced through standard
chat-completion fields. Two related magic function names are
recognized on the same code path:

* `codeExecution` — enables Gemini's native code-execution tool
* `urlContext` — enables Gemini's URL-context tool

### Or go native

If you're already on Gemini's native protocol via `/v1beta/`, pass
`googleSearch` directly in Gemini shape — no magic-name translation
needed:

```bash theme={null}
curl "https://api.orcarouter.ai/v1beta/models/google/gemini-2.5-flash:generateContent" \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"role":"user","parts":[{"text":"What changed in Gemini pricing this week?"}]}],
    "tools": [{"googleSearch": {}}]
  }'
```

`{"codeExecution": {}}` and `{"urlContext": {}}` work the same way on
the native path. See [Native Formats / Gemini](/native-formats/gemini).

## Billing

`web_search` and `web_search_preview` are tracked as built-in tool
calls. They have **different pricing tiers** — see
[Operations / Billing & Usage](/operations/billing-and-usage) for
the breakdown.
