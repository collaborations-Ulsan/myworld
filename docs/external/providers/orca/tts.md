> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Text-to-speech

> Generate speech audio from text via /v1/audio/speech (OpenAI shape) or Gemini's native /v1beta/.

OrcaRouter exposes two paths for text-to-speech depending on which
provider's TTS model you want to use.

## OpenAI-shape: `/v1/audio/speech`

Use this with OpenAI's TTS model family — `openai/tts-1`,
`openai/tts-1-hd`, `openai/gpt-4o-mini-tts`, and similar:

```bash theme={null}
curl https://api.orcarouter.ai/v1/audio/speech \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/tts-1",
    "input": "Hello, world!",
    "voice": "alloy"
  }' \
  --output speech.mp3
```

The response is binary audio. The `Content-Type` header tells you
which format the upstream returned (`audio/mpeg`, `audio/wav`,
`audio/opus`, or `audio/flac`).

## Gemini TTS: native `/v1beta/`

Gemini TTS preview models (e.g. `google/gemini-2.5-flash-preview-tts`)
are not served on `/v1/audio/speech` — call them through Gemini's
native surface instead:

```bash theme={null}
curl "https://api.orcarouter.ai/v1beta/models/google/gemini-2.5-flash-preview-tts:generateContent" \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "Hello, world!"}]}],
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "speechConfig": {
        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}
      }
    }
  }'
```

Audio bytes come back as base64 inside the response's `inlineData`
field. See Google's Gemini TTS docs for the full set of voice names
and configuration options.

## See also

* [API Reference / Audio](/api-reference/audio/generate-speech) — full schema with try-it
* [Native Formats / Gemini](/native-formats/gemini)
* [Advanced / Audio input](/advanced/audio-input) — sending audio TO a chat model
