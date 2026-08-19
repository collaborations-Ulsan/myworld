> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# oh-my-pi

> Use OrcaRouter inside oh-my-pi — OpenAI-compatible, configured via models.yml.

[oh-my-pi](https://github.com/can1357/oh-my-pi) (command `omp`) is a minimal,
extensible terminal coding agent. It's a coding-first fork of
[pi-mono](https://github.com/badlogic/pi-mono) (command `pi`) — a related but
separate tool with its own install/config.

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (includes the `/v1` suffix)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs oh-my-pi (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool oh-my-pi
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool oh-my-pi
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

```bash theme={null}
bun install -g @oh-my-pi/pi-coding-agent
```

Requires bun >= 1.3.14. The installed command is `omp`.

## Configure

First export your API key as an environment variable:

```bash theme={null}
export ORCA_KEY="sk-orca-..."
```

Config file: `~/.omp/agent/models.yml`.

```yaml theme={null}
providers:
  orcarouter:
    baseUrl: https://api.orcarouter.ai/v1
    api: openai-completions
    apiKey: ORCA_KEY
    authHeader: true
    models:
      - id: orcarouter/auto
        name: OrcaRouter Auto
        reasoning: false
        input: [text]
        contextWindow: 200000
        maxTokens: 8192
        compat:
          supportsDeveloperRole: false
          maxTokensField: max_tokens
```

Swap `orcarouter/auto` for a specific model if you prefer, e.g. `anthropic/claude-opus-4.8` or `google/gemini-2.5-flash`. Model IDs always use the `vendor/model` format.

## Run

```bash theme={null}
omp -p --model "orcarouter/orcarouter/auto" "Reply with exactly: OK"
```

Expected output: `OK`.

## Notes

* Requires bun >= 1.3.14.
* The `base_url` must include `/v1`.
* The `apiKey` field takes the **name** of an environment variable, not the key itself; with `authHeader: true` it is sent as `Authorization: Bearer <value>`.
* Model references use the `provider/model` format — here `orcarouter/orcarouter/auto` (provider `orcarouter` + model ID `orcarouter/auto`).
* Use `-p` for non-interactive runs.
* oh-my-pi is a fork of pi-mono. The command here is `omp`; the upstream pi-mono uses `pi` and the `@mariozechner/pi-coding-agent` package — they are configured separately.

## Enable thinking / reasoning

The default model entry above has `reasoning: false`. To enable reasoning and allow effort selection, declare a `thinking` block plus a `compat.reasoningEffortMap` on the model:

```yaml theme={null}
models:
  - id: anthropic/claude-sonnet-4.6
    name: Claude Sonnet 4.6
    reasoning: true
    thinking:
      minLevel: low
      maxLevel: xhigh
      mode: effort
    input: [text]
    contextWindow: 200000
    maxTokens: 8192
    compat:
      supportsDeveloperRole: false
      supportsReasoningEffort: true
      maxTokensField: max_tokens
      thinkingFormat: openai
      reasoningEffortMap: { low: low, medium: medium, high: high, xhigh: high }
```

Then pick an effort level at runtime with a `model:level` suffix (within `minLevel..maxLevel`):

```bash theme={null}
omp -p --model "orcarouter/anthropic/claude-sonnet-4.6:high" "What is 17*23?"
```

Verified: the `:high` suffix selects the effort level and works against OrcaRouter.
