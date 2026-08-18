> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Tool calling

> Pass tools / function declarations and let the model call them.

OpenAI-style `tools` / `tool_choice` works against every chat-capable
provider. The gateway translates to the upstream's native tool-call
shape.

## Minimal example

```python theme={null}
from openai import OpenAI
client = OpenAI(base_url="https://api.orcarouter.ai/v1", api_key="sk-orca-...")

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

resp = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Weather in Paris?"}],
    tools=tools,
)
print(resp.choices[0].message.tool_calls)
```

## Cross-provider behavior

Same client code works across every chat-capable provider — OrcaRouter
adapts your OpenAI-style `tools` to each upstream's native shape:

* **OpenAI / Grok / DeepSeek**: native target — `tools` keeps the
  OpenAI shape on the wire
* **Anthropic**: OpenAI `tools` is mapped to Anthropic `tools` with
  `input_schema`, preserving JSON Schema `properties` and `required`
* **Gemini**: OpenAI `tools` is mapped to Gemini
  `tools[].functionDeclarations`, with `name` / `description` /
  `parameters` carried through

### Gemini reserved function names

On Gemini targets the gateway recognizes three reserved
`function.name` values and turns them into Gemini's native built-in
tools instead of custom function declarations:

| Reserved name   | Maps to                                                                 |
| --------------- | ----------------------------------------------------------------------- |
| `googleSearch`  | Gemini Google Search grounding (see [Web search](/advanced/web-search)) |
| `codeExecution` | Gemini built-in code execution                                          |
| `urlContext`    | Gemini built-in URL-context tool                                        |

Functions with one of these names don't need `parameters` — pass
`{type: "function", function: {name: "googleSearch"}}` and Gemini
takes it from there. Pick a different name for your own custom tools
so you don't collide with these built-ins.
