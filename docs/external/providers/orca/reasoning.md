> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Reasoning

> Reasoning models across all providers, with one unified effort syntax.

Reasoning models spend extra compute on a hidden "thinking" pass
before producing the final answer. They're slower and more expensive
but solve harder problems. OrcaRouter provides **one unified syntax**
for controlling reasoning effort across every provider — pick whichever
form fits your client.

## Two ways to set effort

### 1. The `reasoning_effort` field (OpenAI shape)

Pass it on a Chat Completions request. Values: `low`, `medium`,
`high` (and `minimal` / `max` on some models).

```python theme={null}
resp = client.chat.completions.create(
    model="anthropic/claude-opus-4.6",
    messages=[{"role": "user", "content": "Hard math problem..."}],
    reasoning_effort="high",
)
```

OrcaRouter translates this field to the upstream's native shape:

* **OpenAI o-series and gpt-5-pro family**: forwarded as native
  `reasoning_effort`.
* **Anthropic Claude**: mapped to `thinking: {type: "enabled",
  budget_tokens: ...}` with budgets `low`→1280, `medium`→2048,
  `high`→4096. For `claude-opus-4.6` specifically, mapped to
  `thinking: {type: "adaptive"}` plus `output_config.effort`.
* **Google Gemini**: mapped to `generationConfig.thinkingConfig`
  with `includeThoughts: true` and a thinking-level / budget set
  from the effort.
* **xAI Grok**: forwarded for grok-3-mini family (which accepts
  `reasoning_effort` natively).
* **DeepSeek reasoner**: model is reasoner-by-design;
  `reasoning_effort` is a no-op.

### 2. The `-{effort}` model-name suffix

You can also bake the effort into the model name. Recognized suffixes:
`-minimal` / `-low` / `-medium` / `-high` / `-max`.

```python theme={null}
# Equivalent to model="anthropic/claude-opus-4.6" + reasoning_effort="high"
resp = client.chat.completions.create(
    model="anthropic/claude-opus-4.6-high",
    messages=[...],
)
```

Works the same way across providers — pick whichever line is more
readable in your code.

## Reasoning model families in this deployment

OpenAI:

* `openai/o1`, `o1-pro`
* `openai/o3`, `o3-mini`, `o3-mini-high`
* `openai/o4-mini`, `o4-mini-high`
* `openai/gpt-5-pro` and `gpt-5.x-pro` family

Anthropic (extended thinking on Claude 4 / Opus):

* `anthropic/claude-sonnet-4.6`, `claude-opus-4.6`, `claude-opus-4.7`,
  etc. — pair with `reasoning_effort` or the `-{effort}` suffix.

Google Gemini (extended thinking on Gemini 2.5 / 3.x):

* `google/gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-3-pro-preview`,
  etc. — pair with `reasoning_effort` or the `-{effort}` suffix.

DeepSeek:

* `deepseek/deepseek-reasoner` — reasoner-by-design.

xAI Grok:

* `grok/grok-4-fast-reasoning`, `grok-4-1-fast-reasoning`
* `grok/grok-3-mini` paired with `reasoning_effort: low` or `high`

Call `/v1/models` for the live catalog.

## Reasoning trace in the response

For OpenAI Responses API the model's hidden reasoning is returned as
`reasoning` items in the response output. For Anthropic via native
`/v1/messages`, thinking arrives as `content_block` entries of type
`thinking`. The gateway also surfaces a `reasoning_content` field on
chat-completion responses where the upstream provides one.

You can display the trace for transparency or ignore it in production.

## Billing

Reasoning tokens are tracked separately on `completion_tokens_details
.reasoning_tokens` in the response usage object — see
[Operations / Billing & Usage](/operations/billing-and-usage).
