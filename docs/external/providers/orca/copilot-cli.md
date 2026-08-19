> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# GitHub Copilot CLI

> Use OrcaRouter inside GitHub Copilot CLI — Anthropic protocol, configured via environment variables.

[GitHub Copilot CLI](https://docs.github.com/copilot/how-tos/copilot-cli/cli-getting-started)
is GitHub's terminal coding assistant. It supports BYOK (bring your own key),
which lets you point it at OrcaRouter.

<Info>
  **Protocol: Anthropic** (via `COPILOT_PROVIDER_TYPE=anthropic`)

  * **Base URL:** `https://api.orcarouter.ai` — **without** `/v1`
  * With `/v1` the request path becomes `/v1/v1/messages` and fails with a 404
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs Copilot CLI (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool copilot-cli
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool copilot-cli
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

```bash theme={null}
npm install -g @github/copilot
copilot --version
```

Requires Node.js 22+.

## Configure

Set these environment variables:

```bash theme={null}
export COPILOT_PROVIDER_TYPE=anthropic
export COPILOT_PROVIDER_BASE_URL="https://api.orcarouter.ai"   # NOTE: no /v1
export COPILOT_PROVIDER_API_KEY="sk-orca-..."
export COPILOT_MODEL="orcarouter/auto"                         # or e.g. anthropic/claude-opus-4.8
```

## Run

```bash theme={null}
copilot -p "Reply with exactly: OK" --allow-all
```

You should see `OK`. Drop `-p` for an interactive session.

## Notes

* **Base URL must not include `/v1`** — with `/v1` the request path becomes `/v1/v1/messages` and fails with a 404.
* Non-interactive mode requires `--allow-all` (or set `COPILOT_ALLOW_ALL`).
* Model names use the `vendor/model` format; `orcarouter/auto` is the simplest choice.

<Note>
  **Use the CLI, not the VS Code extension.** GitHub Copilot's VS Code extension
  does not currently expose a custom OpenAI-compatible endpoint — its **Add
  Models** picker (Anthropic / OpenAI / Google / OpenRouter / Ollama / Azure) only
  lets you enter an API key, with no base-URL field, so it can't be pointed at
  OrcaRouter. Connect through the Copilot **CLI** with the environment variables
  above instead.
</Note>

## Enable thinking / reasoning

<Warning>
  **The `--effort` flag does NOT work with BYOK custom models.** Copilot CLI
  checks the model name against a built-in allow-list of reasoning-capable
  models; a custom `vendor/model` name isn't on it, so `--effort high` is
  rejected with:

  ```
  Error: Model "anthropic/claude-sonnet-4.6" does not support reasoning effort configuration (requested: "high").
  ```
</Warning>

When pointed at OrcaRouter, run **without** `--effort` — thinking is then
governed by the model's / upstream's default behavior. (Verified.)
