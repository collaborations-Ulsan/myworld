> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Quickstart

> Make your first OrcaRouter call in under a minute.

If you already use the OpenAI SDK, the only change is pointing `base_url`
at OrcaRouter and using an OrcaRouter API key.

## 1. Get an API key

Sign in at [orcarouter.ai](https://www.orcarouter.ai) and copy your key from
the dashboard. OrcaRouter keys start with `sk-orca-`. See
[Get an API key](/getting-started/get-api-key) for the options you can
set when creating a key (credit limit, expiration).

## 2. Make a call

<CodeGroup>
  ```bash cURL theme={null}
  curl https://api.orcarouter.ai/v1/chat/completions \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "model": "openai/gpt-4o-mini",
      "messages": [{"role":"user","content":"Hello, OrcaRouter!"}]
    }'
  ```

  ```python Python theme={null}
  from openai import OpenAI

  client = OpenAI(
      base_url="https://api.orcarouter.ai/v1",
      api_key="sk-orca-...",
  )

  response = client.chat.completions.create(
      model="openai/gpt-4o-mini",
      messages=[{"role": "user", "content": "Hello, OrcaRouter!"}],
  )

  print(response.choices[0].message.content)
  ```

  ```ts TypeScript theme={null}
  import OpenAI from "openai";

  const openai = new OpenAI({
    baseURL: "https://api.orcarouter.ai/v1",
    apiKey: "sk-orca-...",
  });

  const res = await openai.chat.completions.create({
    model: "openai/gpt-4o-mini",
    messages: [{ role: "user", content: "Hello, OrcaRouter!" }],
  });

  console.log(res.choices[0].message.content);
  ```
</CodeGroup>

That's it. Everything else — streaming, tools, vision, JSON mode, Claude
models, Gemini models, Grok models — works exactly as it would against
the provider directly. Swap `openai/gpt-4o-mini` for any model ID
you see in `/v1/models`. Models are namespaced by provider:
`openai/gpt-4o-mini`, `anthropic/claude-sonnet-4.6`,
`google/gemini-2.5-pro`, `deepseek/deepseek-chat`,
`grok/grok-4-fast-reasoning`, `qwen/qwen3.6-plus`,
`kimi/kimi-k2.6`, `minimax/minimax-m2.7`, etc.

## Next steps

<CardGroup cols={2}>
  <Card title="Web search" icon="globe" href="/advanced/web-search">
    Let the model search the web before answering.
  </Card>

  <Card title="Auto Router" icon="wand-magic-sparkles" href="/routing/auto-router">
    Let OrcaRouter pick the cheapest live model.
  </Card>

  <Card title="Model Fallbacks" icon="link" href="/routing/model-fallbacks">
    Chain models for resilience.
  </Card>

  <Card title="Chat Completions" icon="message" href="/api-reference/chat/create-a-chat-completion">
    Full API reference with try-it.
  </Card>
</CardGroup>
