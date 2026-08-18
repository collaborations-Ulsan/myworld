> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Google GenAI SDK

> Point the google-genai SDK at OrcaRouter to call Gemini models via /v1beta/.

## Quick start

This page targets the modern **`google-genai`** Python SDK (`pip
install google-genai`), not the legacy `google-generativeai` package.

```python Python theme={null}
from google import genai

client = genai.Client(
    api_key="sk-orca-...",
    http_options={"base_url": "https://api.orcarouter.ai"},
)

response = client.models.generate_content(
    model="google/gemini-2.5-flash",
    contents="Hello",
)
print(response.text)
```

The SDK hits `https://api.orcarouter.ai/v1beta/models/{model}:generateContent`
with the standard Gemini JSON shape — OrcaRouter's first-class Gemini
surface. Streaming, function calling, and inline multimodal data
(image, audio) work directly; for size limits and per-model
constraints, see Google's Gemini API documentation.

The SDK sends `api_key` via the `x-goog-api-key` header (or
`?key=...` query) — OrcaRouter's auth middleware recognizes both on
`/v1beta/...` paths. See
[Get an API key](/getting-started/get-api-key#how-to-send-the-key)
for the full table of accepted auth headers.

## See also

* [Native Formats / Gemini](/native-formats/gemini) — the raw HTTP shape
* [Models](/getting-started/models) — full Gemini / Imagen / TTS model list
