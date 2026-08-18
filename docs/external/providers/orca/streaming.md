> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Streaming

> Server-Sent Events for incremental output — Chat Completions, Responses, and Anthropic Messages.

Set `stream: true` to receive incremental tokens as Server-Sent Events
instead of one final response. Latency-to-first-token drops to a
single network round-trip.

## OpenAI-compatible (Chat / Responses)

<CodeGroup>
  ```bash cURL theme={null}
  curl -N https://api.orcarouter.ai/v1/chat/completions \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "model": "openai/gpt-4o-mini",
      "messages": [{"role":"user","content":"Tell me a haiku."}],
      "stream": true
    }'
  ```

  ```python Python theme={null}
  from openai import OpenAI

  client = OpenAI(base_url="https://api.orcarouter.ai/v1", api_key="sk-orca-...")

  stream = client.chat.completions.create(
      model="openai/gpt-4o-mini",
      messages=[{"role": "user", "content": "Tell me a haiku."}],
      stream=True,
  )
  for chunk in stream:
      delta = chunk.choices[0].delta.content
      if delta:
          print(delta, end="", flush=True)
  ```

  ```ts TypeScript theme={null}
  import OpenAI from "openai";

  const openai = new OpenAI({
    baseURL: "https://api.orcarouter.ai/v1",
    apiKey: "sk-orca-...",
  });

  const stream = await openai.chat.completions.create({
    model: "openai/gpt-4o-mini",
    messages: [{ role: "user", content: "Tell me a haiku." }],
    stream: true,
  });
  for await (const chunk of stream) {
    process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
  }
  ```
</CodeGroup>

Each line is `data: {...}`. Stream ends with `data: [DONE]`.

To get the final `usage` object inside the stream, pass
`stream_options: { include_usage: true }` — the chunk just before
`[DONE]` will include token counts.

## Anthropic Messages

Anthropic uses **named SSE events**. On OrcaRouter's first-class
Anthropic surface, the full set Anthropic emits comes through directly:

```
event: message_start
event: content_block_start
event: ping
event: content_block_delta
event: content_block_stop
event: message_delta
event: message_stop
```

Each event is followed by a `data: {...}` JSON line.

<CodeGroup>
  ```bash cURL theme={null}
  curl -N https://api.orcarouter.ai/v1/messages \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -H "anthropic-version: 2023-06-01" \
    -d '{
      "model": "anthropic/claude-sonnet-4.6",
      "max_tokens": 256,
      "messages": [{"role":"user","content":"Tell me a haiku."}],
      "stream": true
    }'
  ```

  ```python Python theme={null}
  from anthropic import Anthropic

  client = Anthropic(base_url="https://api.orcarouter.ai", api_key="sk-orca-...")

  with client.messages.stream(
      model="anthropic/claude-sonnet-4.6",
      max_tokens=256,
      messages=[{"role": "user", "content": "Tell me a haiku."}],
  ) as stream:
      for text in stream.text_stream:
          print(text, end="", flush=True)
  ```
</CodeGroup>

## Errors during a stream

Errors emitted mid-stream cannot use HTTP status codes (the status
was sent when the stream opened). See
[Operations / Errors](/operations/errors#streaming-errors) for the
in-band error shapes.

## Streaming and fallback

Once any byte of the response has been sent to the client, OrcaRouter
can no longer fall back to the next chain entry — see the streaming
caveat in [Model Fallbacks](/routing/model-fallbacks).

## Next steps

<CardGroup cols={2}>
  <Card title="Tool calling" icon="wrench" href="/advanced/tool-calling">
    Stream tool-call deltas as they arrive.
  </Card>

  <Card title="Errors" icon="triangle-exclamation" href="/operations/errors#streaming-errors">
    Handle mid-stream failures.
  </Card>
</CardGroup>
