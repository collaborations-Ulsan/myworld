> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# OpenAI-compatible HTTP

> Raw HTTP shape for /v1/chat/completions and /v1/responses without an SDK.

The OpenAI-compatible surface covers Chat Completions, Responses, and
all related endpoints. Every chat model in the catalog is reachable
here, whichever provider it comes from.

## /v1/chat/completions

```bash theme={null}
curl https://api.orcarouter.ai/v1/chat/completions \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## /v1/responses

```bash theme={null}
curl https://api.orcarouter.ai/v1/responses \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-5",
    "input": "Hello"
  }'
```

**Every chat model in the catalog works here**, including Anthropic and
Gemini ones. Models whose upstream speaks the Responses protocol
natively are served directly; the rest are translated to and from their
own shape. The request you send and the response you get back are the
same either way.

If you'd rather use a provider's own protocol, `/v1/messages`
(Anthropic) and `/v1beta/.../generateContent` (Gemini) are also
available.

## See also

* [API Reference / Chat](/api-reference/chat/create-a-chat-completion) — full schema with try-it
* [Advanced / Streaming](/advanced/streaming) — SSE shape
* [Native Formats / Anthropic](/native-formats/anthropic) — Anthropic native protocol
* [Native Formats / Gemini](/native-formats/gemini) — Gemini native protocol
