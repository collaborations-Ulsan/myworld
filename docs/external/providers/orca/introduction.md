> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Welcome to OrcaRouter

> One API. Multi-provider. Zero markup.

OrcaRouter is an OpenAI-compatible API gateway. Point your existing
OpenAI SDK at `https://api.orcarouter.ai/v1` and route requests across
OpenAI, Anthropic, Google Gemini, DeepSeek, xAI Grok, Alibaba Qwen,
Moonshot Kimi, MiniMax (chat + video), Kling, and ByteDance Seedance
(video) — at provider cost price.

## Why OrcaRouter

<CardGroup cols={2}>
  <Card title="Zero markup, ever" icon="circle-dollar-to-slot">
    You pay the provider's published price per token. OrcaRouter's revenue
    comes from optional paid subscription plans, not from inflating your
    token cost.
  </Card>

  <Card title="OpenAI-compatible by design" icon="code">
    Every request and response is in the OpenAI JSON shape. Change one
    line (`base_url`) and your existing code keeps working — streaming,
    tool calling, vision, and reasoning all behave the way your SDK
    expects, with the gateway translating to each upstream as needed.
  </Card>

  <Card title="Speaks every protocol natively" icon="languages">
    OrcaRouter exposes OpenAI, Anthropic, and Gemini surfaces directly,
    and translates between them when you call across protocols (e.g.
    OpenAI SDK → Claude). New provider features that aren't in the
    common shape stay reachable on the native path.
  </Card>

  <Card title="Smart routing" icon="route" href="/routing/model-fallbacks">
    Fallback chains via `extra_body.models`, named routers, and
    `orcarouter/auto` for cheapest-live-model selection.
  </Card>
</CardGroup>

## Where to start

<CardGroup cols={2}>
  <Card title="Quickstart" icon="rocket" href="/getting-started/quickstart">
    Make your first call in under a minute.
  </Card>

  <Card title="Compatibility" icon="plug" href="/compatibility/openai-sdk">
    Point your OpenAI / Anthropic / Google GenAI SDK at OrcaRouter.
  </Card>

  <Card title="Advanced" icon="sparkles" href="/advanced/web-search">
    Web search, tool calling, vision, reasoning, streaming.
  </Card>

  <Card title="API Reference" icon="book-open" href="/api-reference/chat/create-a-chat-completion">
    Every endpoint with code samples and try-it.
  </Card>
</CardGroup>
