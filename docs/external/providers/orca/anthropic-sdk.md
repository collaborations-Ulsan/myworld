> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Anthropic SDK

> Point the official Anthropic SDK at OrcaRouter to call Claude models via /v1/messages.

## Quick start

```python Python theme={null}
from anthropic import Anthropic

client = Anthropic(
    base_url="https://api.orcarouter.ai",
    api_key="sk-orca-...",
)

response = client.messages.create(
    model="anthropic/claude-sonnet-4.6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.content[0].text)
```

The Anthropic SDK appends `/v1/messages` to your `base_url` itself,
so the bare host (without `/v1`) is the right form. Requests land on
`https://api.orcarouter.ai/v1/messages` — OrcaRouter's first-class
Anthropic surface. Native SSE events (`message_start`,
`content_block_delta`, `message_stop`, ...) come through directly, and
streaming, tool use, prompt caching (`cache_control`), and vision all
work end-to-end.

The SDK uses the standard `x-api-key` header to send `api_key` —
OrcaRouter's auth middleware recognizes that form on Anthropic-shape
paths, so no header munging is required. See
[Get an API key](/getting-started/get-api-key#how-to-send-the-key)
for the full table of accepted auth headers.

## See also

* [Native Formats / Anthropic](/native-formats/anthropic) — the raw HTTP shape
* [Models](/getting-started/models) — full Claude model list
