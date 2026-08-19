> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Crush

> Use OrcaRouter inside Crush — OpenAI-compatible, configured via crush.json.

[Crush](https://github.com/charmbracelet/crush) is Charm's open-source terminal
AI coding agent.

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (includes the `/v1` suffix)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs Crush (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool crush
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool crush
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

```bash theme={null}
npm install -g @charmland/crush
```

The npm package is a launcher; the first run downloads the platform binary automatically (requires network access).

## Configure

Config file: `~/.config/crush/crush.json` (Windows: `%USERPROFILE%\.config\crush\crush.json`).

```json theme={null}
{
  "$schema": "https://charm.land/crush.json",
  "providers": {
    "orcarouter": {
      "type": "openai",
      "base_url": "https://api.orcarouter.ai/v1",
      "api_key": "sk-orca-...",
      "models": [
        { "id": "orcarouter/auto", "name": "OrcaRouter Auto", "context_window": 200000, "default_max_tokens": 4096 }
      ]
    }
  }
}
```

Swap `orcarouter/auto` for a specific model if you prefer, e.g. `anthropic/claude-opus-4.8` or `google/gemini-2.5-flash`. Model IDs always use the `vendor/model` format.

## Run

```bash theme={null}
crush run "Reply with exactly: OK"
```

Expected output: `OK`.

## Notes

* The `base_url` must include `/v1`.
* First run downloads the binary, so initial startup needs network access.
* `models[].id` uses the `vendor/model` format (e.g. `orcarouter/auto`, `anthropic/claude-opus-4.8`).

## Enable thinking / reasoning

Set it per model in `crush.json`:

* **OpenAI-style models** — `"reasoning_effort": "high"` (values `low` / `medium` / `high`), and mark the model `"can_reason": true`.
* **Anthropic models** — `"think": true` (boolean toggle for extended thinking).

```json theme={null}
"models": [
  { "id": "anthropic/claude-sonnet-4.6", "name": "Sonnet 4.6", "context_window": 200000, "default_max_tokens": 4096, "can_reason": true, "reasoning_effort": "high" }
]
```

Verified: `reasoning_effort: "high"` works against OrcaRouter.
