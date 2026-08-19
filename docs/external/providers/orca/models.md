> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Models

> Discover and pick from the catalog. Models are provider-prefixed (openai/, anthropic/, google/, deepseek/, grok/, qwen/, kimi/, minimax/, z-ai/, kling/, byteplus/).

## What's available

OrcaRouter routes to eleven upstream providers. Models are addressed by
**provider-prefixed ID**:

| Prefix       | Provider                   | Examples (call `/v1/models` for the live catalog)                                                                             |
| ------------ | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `openai/`    | OpenAI                     | `openai/gpt-4o-mini`, `openai/gpt-5`, `openai/o3-mini`, `openai/gpt-image-1`, `openai/tts-1`                                  |
| `anthropic/` | Anthropic                  | `anthropic/claude-sonnet-4.6`, `anthropic/claude-opus-4.7`                                                                    |
| `google/`    | Google Gemini              | `google/gemini-2.5-flash`, `google/gemini-3-pro-preview`, `google/imagen-4.0-generate-001`                                    |
| `deepseek/`  | DeepSeek                   | `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner`                                                                        |
| `grok/`      | xAI Grok                   | `grok/grok-4-fast-reasoning`, `grok/grok-imagine-image`                                                                       |
| `qwen/`      | Alibaba Qwen               | `qwen/qwen3.6-plus`, `qwen/qwen3-vl-235b-a22b-thinking`, `qwen/qwen3-max`                                                     |
| `kimi/`      | Moonshot Kimi              | `kimi/kimi-k2.5`, `kimi/kimi-k2.6`                                                                                            |
| `minimax/`   | MiniMax (chat + video)     | `minimax/minimax-m2.7`, `minimax/minimax-m2.5-highspeed`, `minimax/minimax-h3` — see [MiniMax Video](/minimax-video/overview) |
| `z-ai/`      | Z.ai (GLM)                 | `z-ai/glm-5.1`, `z-ai/glm-5`, `z-ai/glm-4.7`, `z-ai/glm-4.6`, `z-ai/glm-4.5`, `z-ai/glm-4.5-air`                              |
| `kling/`     | Kling (video)              | `kling/kling-v3-omni`, `kling/kling-v2-6` — see [Kling Video](/kling-video/overview)                                          |
| `byteplus/`  | ByteDance Seedance (video) | `byteplus/dreamina-seedance-2-0-260128` — see [Seedance Video](/seedance-video/overview)                                      |

Whichever model you'd call against the provider's own API, you can
call against OrcaRouter under the prefixed ID. The catalog is exactly
what each upstream publishes.

## List all models programmatically

<CodeGroup>
  ```bash cURL theme={null}
  curl https://api.orcarouter.ai/v1/models \
    -H "Authorization: Bearer sk-orca-..."
  ```

  ```python Python theme={null}
  from openai import OpenAI

  client = OpenAI(
      base_url="https://api.orcarouter.ai/v1",
      api_key="sk-orca-...",
  )

  models = client.models.list()
  for m in models.data:
      print(m.id, m.owned_by)
  ```

  ```ts TypeScript theme={null}
  import OpenAI from "openai";

  const openai = new OpenAI({
    baseURL: "https://api.orcarouter.ai/v1",
    apiKey: "sk-orca-...",
  });

  const models = await openai.models.list();
  for (const m of models.data) {
    console.log(m.id, m.owned_by);
  }
  ```
</CodeGroup>

### Response shape

```json theme={null}
{
  "object": "list",
  "data": [
    {
      "id": "openai/gpt-4o",
      "object": "model",
      "created": 1626777600,
      "owned_by": "openai",
      "supported_endpoint_types": ["openai"]
    },
    {
      "id": "anthropic/claude-sonnet-4.6",
      "object": "model",
      "owned_by": "anthropic",
      "supported_endpoint_types": ["anthropic", "openai"]
    }
  ]
}
```

The list only includes models your account has access to and that have
a pricing ratio configured. See the
[API Reference / Models](/api-reference/models/list-available-models) for the full endpoint spec.

## Get one model

<CodeGroup>
  ```bash cURL theme={null}
  curl https://api.orcarouter.ai/v1/models/openai/gpt-4o-mini \
    -H "Authorization: Bearer sk-orca-..."
  ```

  ```python Python theme={null}
  client.models.retrieve("openai/gpt-4o-mini")
  ```
</CodeGroup>

## Naming conventions

Model IDs in OrcaRouter are **provider-prefixed** by default. The
prefix tells you (and your client-side logs) exactly which provider
will serve the call before the request even leaves your machine.

The bare upstream name (e.g. `gpt-4o-mini`) may also work if your
administrator has configured it as an alias on a channel, but the
default listing in `/v1/models` always uses the prefixed form — code
written against the prefixed names is portable across deployments.

## Picking by capability

| You need…            | Try                                                                                                                                                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cheapest chat        | `openai/gpt-4o-mini`, `google/gemini-2.5-flash-lite`                                                                                                                                                                |
| Strongest reasoning  | `openai/o3-mini-high`, `openai/gpt-5-pro`, `anthropic/claude-opus-4.7`                                                                                                                                              |
| Long context + cheap | `google/gemini-2.5-flash`                                                                                                                                                                                           |
| Web search built-in  | `openai/gpt-4o-search-preview` (chat completions), or any Grok model on `/v1/responses` with the `web_search` tool — see [Web search](/advanced/web-search)                                                         |
| Vision input         | `openai/gpt-4o-mini`, `google/gemini-2.5-flash`, `grok/grok-4-fast-reasoning`                                                                                                                                       |
| Image generation     | `openai/gpt-image-1-mini`, `google/imagen-4.0-fast-generate-001`, `grok/grok-imagine-image`                                                                                                                         |
| Auto-pick cheapest   | `orcarouter/auto` — see [Auto Router](/routing/auto-router)                                                                                                                                                         |
| Video generation     | `kling/kling-v3-omni` ([Kling Video](/kling-video/overview)), `byteplus/dreamina-seedance-2-0-260128` ([Seedance Video](/seedance-video/overview)), `minimax/minimax-h3` ([MiniMax Video](/minimax-video/overview)) |
