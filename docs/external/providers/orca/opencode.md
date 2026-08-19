> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# OpenCode

> Use OrcaRouter inside OpenCode — OpenAI-compatible, configured via opencode.json.

[OpenCode](https://opencode.ai) ([GitHub](https://github.com/sst/opencode)) is
an open-source terminal AI coding agent that works with many providers.

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (includes `/v1`)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs OpenCode (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool opencode
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool opencode
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

<Warning>
  Claude **reasoning** models over the OpenAI protocol reject `temperature != 1`
  (`400 temperature may only be set to 1 when thinking is enabled`). Use a
  non-reasoning model, or enable `reasoningEffort` — see
  [Enable thinking](#enable-thinking-reasoning).
</Warning>

## Install

```bash theme={null}
npm install -g opencode-ai
```

## Configure

Config file: `~/.config/opencode/opencode.json`.

```json theme={null}
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "orcarouter": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OrcaRouter",
      "options": { "baseURL": "https://api.orcarouter.ai/v1", "apiKey": "sk-orca-..." },
      "models": { "orcarouter/auto": { "name": "OrcaRouter Auto" } }
    }
  },
  "model": "orcarouter/orcarouter/auto"
}
```

Swap in a specific model if you prefer, e.g. `google/gemini-2.5-flash` or
`anthropic/claude-opus-4.8`. Model IDs always use the `vendor/model` format.

## Run

```bash theme={null}
opencode run "Reply with exactly: OK"
```

Expected output: `OK`.

## Notes

* The base URL must include `/v1`.
* Model references use the `provider/model` format. Because the provider is
  named `orcarouter` and the model ID also carries a `vendor` prefix, the
  reference is three segments: `orcarouter/orcarouter/auto` (or
  `orcarouter/anthropic/claude-opus-4.8` for a specific model).

<Note>
  **VS Code extension:** OpenCode's official VS Code extension (`sst-dev.opencode`)
  runs the CLI inside the editor and shares the same `opencode.json` — there's no
  separate in-editor endpoint setting. Configure it once as above and the
  extension picks it up.
</Note>

## Enable thinking / reasoning

Set `reasoningEffort` in the model's `options`:

```json theme={null}
"models": {
  "anthropic/claude-sonnet-4.6": {
    "name": "Sonnet 4.6",
    "options": { "reasoningEffort": "high" }
  }
}
```

Enabling `reasoningEffort` also sidesteps the `temperature` warning above —
with thinking enabled, `temperature = 1` is legal, so the 400 disappears. For
Anthropic-native control, the `@ai-sdk/anthropic` provider accepts
`thinking: { type: "enabled", budgetTokens: N }`.
