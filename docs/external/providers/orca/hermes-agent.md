> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Hermes Agent

> Use OrcaRouter inside Hermes Agent — OpenAI-compatible, configured via config.yaml.

A terminal AI agent from Nous Research (command `hermes`). Site:
[https://hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com)
(repo:
[https://github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)).

Supported on Linux / macOS / WSL2. **Windows is not natively supported** —
install inside WSL2.

<Info>
  **Protocol: OpenAI-compatible** (Chat Completions)

  * **Base URL:** `https://api.orcarouter.ai/v1` (must include `/v1`)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  On **Linux / macOS / WSL2**, this installs Hermes (if missing), writes both
  `config.yaml` and the `.env` key, and smoke-tests OrcaRouter. You'll be prompted
  for your API key (or set `ORCA_KEY` in the environment to run unattended — prefer
  that over a `--key` flag, which lands in your shell history).

  Hermes has no npm package, so the installer would run Nous Research's own
  third-party installer — that needs the explicit `--allow-third-party-install`
  opt-in below. Without it the command stops with manual-install instructions.

  ```bash theme={null}
  curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool hermes --allow-third-party-install
  ```

  On **Windows**, run that same command inside a WSL2 (Ubuntu) shell — Hermes isn't
  supported natively. To set it up by hand instead, follow the steps below.
</Tip>

## Install

On Linux / macOS / WSL2:

```sh theme={null}
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc   # or ~/.zshrc
```

On **Windows**, Hermes is not natively supported — open a WSL2 (Ubuntu) shell and run the same command above inside it.

## Configure

**Two files** — the endpoint goes in `config.yaml`, the API key goes in `.env`.

**1. `~/.hermes/config.yaml`** — the endpoint:

```yaml theme={null}
model:
  api_mode: chat_completions
  base_url: https://api.orcarouter.ai/v1
  default: orcarouter/auto
  provider: custom
```

**2. `~/.hermes/.env`** — the API key. With a `custom` provider, Hermes derives
the env-var name from the base-URL host (`api.orcarouter.ai` → `ORCAROUTER_API_KEY`)
and injects it as the Bearer token. **The key must be under this exact name:**

```sh theme={null}
ORCAROUTER_API_KEY=sk-orca-...
```

<Warning>
  **Do not put the key under `OPENAI_API_KEY`.** For a `custom` provider Hermes
  sends that as a placeholder no-key value, and the upstream rejects it with
  `401 Invalid token`. The key must be `ORCAROUTER_API_KEY` (the `<VENDOR>_API_KEY`
  derived from the host). Likewise, don't switch `provider` to `openrouter` — that
  forces `base_url` to `openrouter.ai` and hits the wrong service (also 401).
</Warning>

## Run

Hermes is interactive. Launch it and verify the model responds:

```sh theme={null}
hermes          # or: hermes --tui
```

Inside the session, use `/model` to switch models. You can also run `hermes model` first to configure a Custom Endpoint via the interactive menu.

## Notes

* The base URL keeps the trailing `/v1`.
* Use `api_mode: chat_completions` — OrcaRouter speaks Chat Completions, not the Responses API.
* `default: orcarouter/auto` uses automatic routing; `provider: custom` selects the custom endpoint.
* **The key lives in `~/.hermes/.env` as `ORCAROUTER_API_KEY`**, not in `config.yaml`. Using `OPENAI_API_KEY` for a custom provider results in a `401`.
* Model names use `vendor/model` format. Swap `orcarouter/auto` for a specific model like `anthropic/claude-opus-4.8` or `google/gemini-2.5-flash`.
* On Windows you must run Hermes inside WSL2.
