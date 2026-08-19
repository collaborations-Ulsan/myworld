> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# pi

> Use OrcaRouter inside pi — OpenAI-compatible, configured via models.json.

[pi](https://github.com/badlogic/pi-mono) (command `pi`, package
`@mariozechner/pi-coding-agent`) is Mario Zechner's terminal AI coding agent —
the upstream project that [oh-my-pi](/integrations/oh-my-pi) (`omp`) forked from.
They are separate tools with separate config.

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (includes the `/v1` suffix)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs pi (if missing), writes the config,
  and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool pi
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool pi
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

```bash theme={null}
npm install -g @mariozechner/pi-coding-agent
# or: bun install -g @mariozechner/pi-coding-agent
```

The installed command is `pi`.

## Configure

pi defines custom OpenAI-compatible endpoints in `~/.pi/agent/models.json` (JSON,
not YAML). Add an `orcarouter` provider:

```json theme={null}
{
  "providers": {
    "orcarouter": {
      "baseUrl": "https://api.orcarouter.ai/v1",
      "api": "openai-completions",
      "apiKey": "ORCA_KEY",
      "models": [
        {
          "id": "orcarouter/auto",
          "name": "OrcaRouter Auto",
          "reasoning": false,
          "input": ["text"],
          "contextWindow": 200000,
          "maxTokens": 8192
        }
      ]
    }
  }
}
```

The `apiKey` field takes the **name of an environment variable** (literal keys
and `!shell-command` forms are also accepted). Export the key it names:

```bash theme={null}
export ORCA_KEY="sk-orca-..."
```

Swap `orcarouter/auto` for a specific model if you prefer, e.g.
`anthropic/claude-opus-4.8` or `google/gemini-2.5-flash`. Model IDs use the
`vendor/model` format.

## Run

```bash theme={null}
pi -p --provider orcarouter --model orcarouter/auto "Reply with exactly: OK"
```

You should see `OK`. Drop `-p` for an interactive session; run
`pi --list-models orcarouter` to confirm the provider is recognized.

## Notes

* Config is JSON at `~/.pi/agent/models.json` — distinct from oh-my-pi's
  `~/.omp/agent/models.yml` (YAML). The two tools do not share config.
* The base URL must include `/v1`.
* `apiKey` is the **name** of an env var by default, not the key itself.
* `api: "openai-completions"` selects the OpenAI Chat Completions protocol.
* The model picker reloads `models.json` each time you open `/model` — edit it
  mid-session without restarting.
* `auth.json` (OAuth/subscription credentials) is separate from `models.json`
  (custom providers); the OrcaRouter provider goes in `models.json`.

## Enable thinking / reasoning

Add a reasoning-capable model with `"reasoning": true`, then pass
`--thinking <level>` (`minimal` / `low` / `medium` / `high` / `xhigh`) at runtime:

```json theme={null}
{
  "id": "anthropic/claude-sonnet-4.6",
  "name": "Claude Sonnet 4.6",
  "reasoning": true,
  "input": ["text"],
  "contextWindow": 200000,
  "maxTokens": 8192
}
```

```bash theme={null}
pi -p --provider orcarouter --model anthropic/claude-sonnet-4.6 --thinking high "What is 17*23?"
```

Verified end-to-end against OrcaRouter: `--thinking high` on a Claude reasoning
model returns the correct answer with no extra config. (If some other endpoint
rejects the `developer` role or `reasoning_effort`, add
`"compat": { "supportsDeveloperRole": false, "supportsReasoningEffort": false }`
on the provider or model — not needed for OrcaRouter.) The default
`orcarouter/auto` entry uses `"reasoning": false` and is unaffected.
