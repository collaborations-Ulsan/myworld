> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Audio input

> Send audio to a multimodal Gemini model via /v1/chat/completions or the native /v1beta/ path.

Audio input is supported by Gemini multimodal models. Two paths:

## Path 1: OpenAI-shape `input_audio` on `/v1/chat/completions`

The gateway translates the OpenAI `input_audio` content part to
Gemini's `inline_data` automatically. The `format` field maps to
the right MIME type (`mp3` → `audio/mp3`, `wav` → `audio/wav`, etc.).

```bash theme={null}
curl https://api.orcarouter.ai/v1/chat/completions \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemini-2.5-flash",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is happening in this audio clip?"},
        {"type": "input_audio", "input_audio": {"data": "<base64>", "format": "mp3"}}
      ]
    }]
  }'
```

## Path 2: Native `/v1beta/` with `inline_data`

If you're already on Gemini's native protocol, pass `inline_data`
directly — no translation involved.

```bash theme={null}
curl "https://api.orcarouter.ai/v1beta/models/google/gemini-2.5-flash:generateContent" \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "role": "user",
      "parts": [
        {"text": "What is happening in this audio clip?"},
        {"inline_data": {"mime_type": "audio/mp3", "data": "<base64>"}}
      ]
    }]
  }'
```

## Supported model families

Gemini multimodal models accept inline audio — for example
`google/gemini-2.5-flash` and the Gemini 3.x line. Behavior matches
Google's published Gemini API exactly.

## Limits

Inline audio payloads are size-capped by the upstream provider. For
longer files, the provider's own File API (uploaded outside OrcaRouter
against the provider directly) is the typical workaround. Check
Google's Gemini API documentation for current size and duration
limits.

## See also

* [Native Formats / Gemini](/native-formats/gemini)
* [Compatibility / Google GenAI SDK](/compatibility/google-genai-sdk)
