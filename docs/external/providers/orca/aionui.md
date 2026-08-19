> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# AionUi

> Use OrcaRouter inside AionUi — a free open-source desktop agent, OpenAI-compatible.

[AionUi](https://www.aionui.com) ([GitHub](https://github.com/iOfficeAI/AionUi),
[releases](https://github.com/iOfficeAI/AionUi/releases)) is a free,
open-source local desktop office agent. No paid plan required.

<Info>
  **Protocol: OpenAI-compatible**

  * **API address:** `https://api.orcarouter.ai/v1` (includes `/v1`)
  * Unlike Cherry Studio, which uses the bare address — AionUi keeps the `/v1`
</Info>

## Connect

1. Open AionUi → **Settings → Model configuration** tab.
2. Add a new provider (type: custom / OpenAI) → **Add model**.
3. Set the **API request address** to `https://api.orcarouter.ai/v1` (with
   `/v1`) and the **API Key** to your `sk-orca-...` key.
4. Set the **model name** to `orcarouter/auto` (or a specific `vendor/model`
   like `anthropic/claude-sonnet-4.6`), then **Save**.
5. Go to the chat screen, select the model, and send a message.

<Check>
  Verified in-app: address `https://api.orcarouter.ai/v1`, model
  `orcarouter/auto` — chat returned the correct answer (with thinking shown).
</Check>

## Notes

* AionUi uses the `/v1` address (Cherry Studio uses the bare address).
* The model name must match a model OrcaRouter exposes (`vendor/model` format),
  or use `orcarouter/auto`.
