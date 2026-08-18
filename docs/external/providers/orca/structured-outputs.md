> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Structured outputs

> Constrain model output to JSON or a JSON schema via response_format.

Two paths:

* `response_format: {"type": "json_object"}` — model returns valid JSON
* `response_format: {"type": "json_schema", "json_schema": {...}}` — model
  output conforms to your schema

## Example (json\_schema, OpenAI)

```python theme={null}
resp = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Extract name and age."}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name", "age"],
            },
        },
    },
)
```

## Cross-provider support

`response_format` is supported wherever the upstream model can honor
it. For Gemini, OrcaRouter's translation layer maps it to
`responseMimeType` + `responseSchema`. For OpenAI / Grok / DeepSeek
(all OpenAI-compatible upstreams), the field reaches the upstream in
its native shape. Anthropic doesn't expose a `response_format`
equivalent, so use Anthropic's `tool_use` pattern when you need
schema-constrained output there.

| Provider   | json\_object | json\_schema | Notes                                               |
| ---------- | ------------ | ------------ | --------------------------------------------------- |
| OpenAI     | ✅            | ✅            | OpenAI's native field shape                         |
| Grok (xAI) | ✅            | ✅            | xAI is OpenAI-compatible                            |
| DeepSeek   | ✅            | ⚠️           | Check DeepSeek's per-model support                  |
| Gemini     | ✅            | ✅            | Translated to `responseMimeType` + `responseSchema` |
| Anthropic  | ❌            | ❌            | Use `tool_use` pattern instead                      |

## See also

* [Advanced / Tool calling](/advanced/tool-calling) — Anthropic schema-constrained workaround
* [API Reference / Chat](/api-reference/chat/create-a-chat-completion) — full schema with try-it
