> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# OpenClaw

> Use OrcaRouter inside OpenClaw — OpenAI-compatible, configured via openclaw.json.

An open-source, self-hosted personal AI assistant. Site:
[https://openclaw.ai](https://openclaw.ai) (docs:
[https://docs.openclaw.ai](https://docs.openclaw.ai), repo:
[https://github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)).

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (must include `/v1`)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs OpenClaw (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool openclaw
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool openclaw
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

Requires Node 22+. Installs the `openclaw` command:

```sh theme={null}
npm install -g openclaw
```

Or on macOS/Linux:

```sh theme={null}
curl -fsSL https://openclaw.ai/install.sh | bash
```

## Configure

Edit `~/.openclaw/openclaw.json`:

```json theme={null}
{
  "models": {
    "mode": "merge",
    "providers": {
      "orcarouter": {
        "baseUrl": "https://api.orcarouter.ai/v1",
        "apiKey": "sk-orca-...",
        "api": "openai-completions",
        "models": [ { "id": "orcarouter/auto", "name": "OrcaRouter Auto" } ]
      }
    }
  },
  "agents": { "defaults": { "model": { "primary": "orcarouter/orcarouter/auto" } } },
  "gateway": { "mode": "local" }
}
```

## Run

```sh theme={null}
openclaw agent --local --agent main --session-id s1 -m "Reply with exactly: OK"
```

Expect the reply `OK`.

## Notes

* **`baseUrl` must live under `models.providers.<name>`**, not inside each model entry. Putting it on a model gives `Unrecognized key: "baseUrl"`.
* The base URL keeps the trailing `/v1`. Model references use `provider/model`, so the auto router is `orcarouter/orcarouter/auto`.
* The default agent name is `main` (not `default`). For non-interactive runs use `--local` with a `--session-id`.
* Model names use `vendor/model` format. Swap `orcarouter/auto` for a specific model like `anthropic/claude-opus-4.8` or `google/gemini-2.5-flash` (and update the `primary` reference accordingly).

## Thinking / reasoning

OpenClaw talks to OrcaRouter over the standard OpenAI-compatible API
(`api: "openai-completions"`), so reasoning follows the model's own behavior —
pick a reasoning-capable model (e.g. an `anthropic/claude-*` reasoning model)
and it thinks as configured upstream.
