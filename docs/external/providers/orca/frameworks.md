> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Frameworks & Integrations

> Wire OrcaRouter into LangChain, the Vercel AI SDK, and any framework that lets you override the OpenAI or Anthropic base URL.

Anything that talks to the OpenAI API talks to OrcaRouter. The
typical pattern: set the base URL to `https://api.orcarouter.ai/v1`
and use an `sk-orca-...` API key. Tools that use the Anthropic SDK
point at `https://api.orcarouter.ai` instead — the Anthropic SDK
appends `/v1/messages` itself.

<Note>
  This page covers wiring OrcaRouter into your own code with an SDK. For
  ready-made CLI agents and desktop clients (Claude Code, Crush,
  Cherry Studio…), see **[Connect Agents & Harnesses](/integrations/overview)**.
</Note>

## LangChain

```python theme={null}
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="openai/gpt-4o",
    base_url="https://api.orcarouter.ai/v1",
    api_key="sk-orca-...",
)
```

## LangChain.js

```ts theme={null}
import { ChatOpenAI } from "@langchain/openai";

const model = new ChatOpenAI({
  model: "openai/gpt-4o",
  openAIApiKey: "sk-orca-...",
  configuration: { baseURL: "https://api.orcarouter.ai/v1" },
});
```

## Vercel AI SDK

```ts theme={null}
import { createOpenAI } from "@ai-sdk/openai";

const openai = createOpenAI({
  baseURL: "https://api.orcarouter.ai/v1",
  apiKey: "sk-orca-...",
});

const model = openai("openai/gpt-4o");
```

## Ready-made CLI agents & desktop clients

Finished tools — Claude Code, Codex CLI, Crush, Cherry Studio, and more —
have their own step-by-step setup pages under
**[Connect Agents & Harnesses](/integrations/overview)**. See, for example,
[Claude Code](/integrations/claude-code) and [Codex CLI](/integrations/codex-cli).

## Anything else

If the framework lets you override the OpenAI base URL or Anthropic base
URL, it works with OrcaRouter. If the framework hardcodes the base URL,
you can usually patch the client instance or set `OPENAI_BASE_URL` /
`ANTHROPIC_BASE_URL` environment variables before import.
