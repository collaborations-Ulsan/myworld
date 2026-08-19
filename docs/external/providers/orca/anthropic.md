> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Anthropic native HTTP

> Raw HTTP shape for POST /v1/messages — content blocks, tool use, named SSE events.

`/v1/messages` is OrcaRouter's first-class Anthropic surface — the
exact Anthropic Messages API shape. Use this when you want native
Anthropic features (content blocks, tool use, prompt caching) and
direct access to the protocol.

## Minimal request

```bash theme={null}
curl https://api.orcarouter.ai/v1/messages \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "anthropic/claude-sonnet-4.6",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Streaming (SSE named events)

```bash theme={null}
curl ... -d '{... "stream": true}'
```

Anthropic uses **named events** (not OpenAI's `data: [DONE]`):

```
event: message_start
data: {...}

event: content_block_delta
data: {...}

event: message_stop
data: {...}
```

See [Advanced / Streaming](/advanced/streaming) for the full event shapes.

## See also

* [Compatibility / Anthropic SDK](/compatibility/anthropic-sdk) — Anthropic SDK with `base_url`
* [API Reference / Messages](/api-reference/messages/create-a-message) — full schema with try-it
