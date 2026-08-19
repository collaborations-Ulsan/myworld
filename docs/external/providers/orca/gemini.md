> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Gemini native HTTP

> Direct passthrough to /v1beta/models/{model}:generateContent — full Gemini protocol fidelity.

OrcaRouter's `/v1beta/` surface is a direct passthrough to Google's
Gemini API. Pick this path when you want Gemini features that don't
fit OpenAI shape — inline audio/video data, native built-in tools
like `googleSearch`, fully-formed `generationConfig.thinkingConfig`,
or simply because you're already on the `google-genai` SDK.

For everyday chat the OpenAI-compatible path
(`POST /v1/chat/completions` with `model=google/...`) is usually
simpler and works across providers — see
[Compatibility / Google GenAI SDK](/compatibility/google-genai-sdk)
for SDK setup.

## Path layout

```
POST https://api.orcarouter.ai/v1beta/models/{model}:{action}
```

Recognized actions:

| Action                   | What it does                 |
| ------------------------ | ---------------------------- |
| `:generateContent`       | One-shot response (JSON)     |
| `:streamGenerateContent` | SSE stream of partial chunks |

Other Gemini actions (`countTokens`, `tunedModels.*`, etc.) are not
routed through this surface today.

## Authentication

The gateway accepts three header forms on this surface, so the
official `google-genai` SDK works without header hacks:

* `Authorization: Bearer sk-orca-...`
* `x-goog-api-key: sk-orca-...`
* `?key=sk-orca-...` (query string, last resort for tools that don't
  support setting headers)

## Examples

<CodeGroup>
  ```bash One-shot theme={null}
  curl "https://api.orcarouter.ai/v1beta/models/google/gemini-2.5-flash:generateContent" \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "contents": [{"role": "user", "parts": [{"text": "Write a one-sentence haiku about the sea."}]}]
    }'
  ```

  ```bash Stream theme={null}
  curl -N "https://api.orcarouter.ai/v1beta/models/google/gemini-2.5-flash:streamGenerateContent" \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "contents": [{"role": "user", "parts": [{"text": "Tell me a long story."}]}]
    }'
  ```

  ```bash Web grounding theme={null}
  curl "https://api.orcarouter.ai/v1beta/models/google/gemini-2.5-flash:generateContent" \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "contents": [{"role":"user","parts":[{"text":"What changed in Gemini pricing this week?"}]}],
      "tools": [{"googleSearch": {}}]
    }'
  ```

  ```bash Image generation theme={null}
  curl "https://api.orcarouter.ai/v1beta/models/google/gemini-2.5-flash-image:generateContent" \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "contents": [{"role":"user","parts":[{"text":"A watercolour of a foggy harbor at dawn."}]}],
      "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
    }'
  ```
</CodeGroup>

## Built-in tools

Gemini's three native built-in tools work as documented by Google —
pass them in the request body's `tools` array:

| Tool                    | Effect                                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------------------ |
| `{"googleSearch": {}}`  | Web grounding. The response carries `groundingMetadata`. OrcaRouter captures `webSearchQueries` for billing. |
| `{"codeExecution": {}}` | Lets the model run sandboxed Python.                                                                         |
| `{"urlContext": {}}`    | Lets the model fetch and summarize URLs you mention.                                                         |

The same three tools are reachable from OpenAI-shape Chat Completions
via reserved function names — see
[Advanced / Web search](/advanced/web-search) and
[Advanced / Tool calling](/advanced/tool-calling).

## See also

* [Compatibility / Google GenAI SDK](/compatibility/google-genai-sdk) — pointing the SDK at OrcaRouter
* [API Reference / Gemini Native](/api-reference/gemini-native/gemini-native-generate) — full request / response schema with try-it
