> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Cherry Studio

> Use OrcaRouter inside Cherry Studio — a free desktop AI client, OpenAI-compatible.

[Cherry Studio](https://cherry-ai.com)
([download](https://cherry-ai.com/download),
[docs](https://docs.cherry-ai.com)) is a free, open-source desktop AI client.
No paid plan required — custom endpoints are open to everyone.

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai` — the **bare** host, no `/v1` (Cherry appends `/v1/chat/completions` itself; verified)
  * If you ever get a 404, try `https://api.orcarouter.ai/v1`
</Info>

## Connect

1. Open Cherry Studio → **Settings (gear) → Model Provider**.
2. At the bottom of the provider list, click **+ Add** to create a **new**
   provider. **Do not use the built-in "cherryin" provider** — its API address
   is a locked dropdown you can't edit. Set name `OrcaRouter`, type **OpenAI**.
3. Fill in:
   * **API Key**: `sk-orca-...`
   * **API Address (Host)**: `https://api.orcarouter.ai` (bare, no `/v1`)
4. Click **Add Model** and enter the **Model ID** in `vendor/model` format,
   e.g. `orcarouter/auto` or `anthropic/claude-sonnet-4.6`.
5. Toggle the provider **on**, then pick the model in chat and send a message.

<Check>
  Verified in-app: a new OpenAI provider with bare URL
  `https://api.orcarouter.ai` and model `orcarouter/auto` returned the correct
  answer.
</Check>

## Notes

* The built-in **cherryin** provider has a locked address dropdown — it can't
  point at OrcaRouter. Always create a fresh **OpenAI** provider.
* Model IDs use the `vendor/model` format, or `orcarouter/auto`.
