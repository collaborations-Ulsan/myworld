> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# OpenAI SDK

> Change one line to use OrcaRouter with the official OpenAI SDK.

OrcaRouter exposes a first-class OpenAI surface. Point your existing
OpenAI SDK at OrcaRouter's base URL and your code keeps working the
way your SDK expects — streaming, tool calling, structured outputs
(`json_object` and `json_schema`), and vision are all supported. When
you target a model from a different provider, OrcaRouter's translation
layer adapts request and response to that provider's native shape so
your SDK code stays unchanged.

## Python

```python theme={null}
from openai import OpenAI

client = OpenAI(
    base_url="https://api.orcarouter.ai/v1",
    api_key="sk-orca-...",
)
```

## TypeScript / Node

```ts theme={null}
import OpenAI from "openai";

const openai = new OpenAI({
  baseURL: "https://api.orcarouter.ai/v1",
  apiKey: "sk-orca-...",
});
```

## Async Python

```python theme={null}
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://api.orcarouter.ai/v1",
    api_key="sk-orca-...",
)
```

## Using environment variables

The OpenAI SDK reads `OPENAI_API_KEY` and `OPENAI_BASE_URL` by default.
Set them once and the SDK picks them up without per-call config:

```bash theme={null}
export OPENAI_API_KEY="sk-orca-..."
export OPENAI_BASE_URL="https://api.orcarouter.ai/v1"
```

## What changes in your code

Only the base URL and the API key. Request parameters, response shape,
streaming protocol, error handling — all unchanged. Model names are
**provider-prefixed** (`openai/gpt-4o-mini`, `anthropic/claude-sonnet-4.6`,
`google/gemini-2.5-pro`, `deepseek/deepseek-chat`,
`grok/grok-4-fast-reasoning`, `qwen/qwen3.6-plus`,
`kimi/kimi-k2.6`, `minimax/minimax-m2.7`) so clients always know which
provider served the request; OrcaRouter handles the cross-provider
translation internally through the same client object.

## Want to add web\_search?

Web search works with the OpenAI SDK against OrcaRouter. See
[Advanced / Web search](/advanced/web-search) for the per-endpoint
parameter shapes and which models support it.

## Other SDKs

Using the Anthropic SDK or google-genai SDK directly? See
[Compatibility / Anthropic SDK](/compatibility/anthropic-sdk) and
[Compatibility / Google GenAI SDK](/compatibility/google-genai-sdk).
