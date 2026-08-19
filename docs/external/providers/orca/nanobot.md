> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# nanobot

> Use OrcaRouter inside nanobot — OpenAI-compatible, configured via config.json.

A lightweight AI agent CLI. Official repo:
[https://github.com/HKUDS/nanobot](https://github.com/HKUDS/nanobot)

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (must include `/v1`)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs nanobot (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool nanobot
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool nanobot
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

Requires [uv](https://github.com/astral-sh/uv) first, then install the `nanobot` command:

```sh theme={null}
uv tool install nanobot-ai
```

## Configure

Edit `~/.nanobot/config.json`:

```json theme={null}
{
  "agents": {
    "defaults": {
      "model": "orcarouter/auto",
      "provider": "custom",
      "maxTokens": 4096,
      "temperature": 0.1
    }
  },
  "providers": {
    "custom": {
      "apiKey": "sk-orca-...",
      "apiBase": "https://api.orcarouter.ai/v1"
    }
  }
}
```

## Run

```sh theme={null}
nanobot agent -m "Reply with exactly: OK" --no-logs --no-markdown
```

Expect the reply `OK`.

## Notes

* Use the predefined `custom` provider — **do not invent your own provider name**. Custom names are ignored and you get a `provider 'None'` error.
* Do **not** add an `apiType` field to the `custom` provider. Only the built-in `openai` provider supports `apiType`; adding it to `custom` fails validation.
* The base URL keeps the trailing `/v1`, and `agents.defaults.provider` must be set to `custom`.
* Model names use `vendor/model` format. Swap `orcarouter/auto` for a specific model like `anthropic/claude-opus-4.8` or `google/gemini-2.5-flash`.

## Enable thinking / reasoning

Set `reasoningEffort` under `agents.defaults` (or a `modelPresets` entry). Valid values: `none` / `low` / `medium` / `high` / `max`. Omitting it (or `null`) follows the model's default.

```json theme={null}
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4.6",
      "provider": "custom",
      "maxTokens": 16000,
      "reasoningEffort": "high"
    }
  },
  "providers": { "custom": { "apiKey": "sk-orca-...", "apiBase": "https://api.orcarouter.ai/v1" } }
}
```

<Warning>
  **`maxTokens` must be larger than the thinking budget.** nanobot translates
  `reasoningEffort: high` into an Anthropic `thinking.budget_tokens`; if
  `maxTokens` (e.g. the default 4096) is smaller, the upstream returns
  `400 max_tokens must be greater than thinking.budget_tokens`. Bumping
  `maxTokens` to \~16000 fixes it. (Verified: returns `✻ 391`.)
</Warning>
