> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Factory Droid CLI

> Use OrcaRouter inside Factory Droid CLI — OpenAI-compatible, configured via config.json.

[Factory Droid CLI](https://docs.factory.ai/cli/getting-started/overview)
(command `droid`) is Factory AI's terminal AI software-engineering agent.

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (includes the `/v1` suffix)
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs Factory Droid (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  Factory Droid has no npm package, so the installer would run Factory's own
  third-party installer — that needs the explicit `--allow-third-party-install`
  (`-AllowThirdPartyInstall`) opt-in below. Without it the command stops with
  manual-install instructions.

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool factory-droid --allow-third-party-install
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool factory-droid -AllowThirdPartyInstall
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

macOS/Linux:

```bash theme={null}
curl -fsSL https://app.factory.ai/cli | sh
```

Windows (PowerShell):

```powershell theme={null}
irm https://app.factory.ai/cli/windows | iex
```

The installed command is `droid`.

## Configure

Config file: `~/.factory/config.json`.

```json theme={null}
{
  "custom_models": [
    {
      "model_display_name": "OrcaRouter Auto",
      "model": "orcarouter/auto",
      "base_url": "https://api.orcarouter.ai/v1",
      "api_key": "sk-orca-...",
      "provider": "generic-chat-completion-api",
      "max_tokens": 8192
    }
  ]
}
```

Swap `orcarouter/auto` for a specific model if you prefer, e.g. `anthropic/claude-opus-4.8` or `google/gemini-2.5-flash`. Model IDs always use the `vendor/model` format.

## Run

```bash theme={null}
droid exec -m "orcarouter/auto" --auto low "Reply with exactly: OK"
```

Expected output: `OK`.

## Notes

* Custom models go in the `custom_models` array.
* Use `provider: "generic-chat-completion-api"` for the OpenAI-compatible protocol.
* The `base_url` must include `/v1`.
* `--auto <low|medium|high>` controls **autonomy** (how much the agent may do unattended) — it is *not* the reasoning control. See below for thinking.

<Note>
  **VS Code extension:** Factory's official VS Code extension shares the same
  `~/.factory/config.json` as the CLI — the `custom_models` entry above applies to
  both, with no separate in-editor endpoint setting. Two caveats: Factory only
  fully tests and benchmarks against the official Anthropic/OpenAI APIs, and a
  known issue can route subagents back to Anthropic instead of your custom model.
</Note>

## Enable thinking / reasoning

Control reasoning effort with the **`-r` / `--reasoning-effort`** flag (separate from `--auto`):

```bash theme={null}
droid exec -m "anthropic/claude-sonnet-4.6" -r high --auto low "What is 17*23?"
```

Levels: `low` / `medium` / `high` (default is per-model — Anthropic models default off, GPT-5 defaults medium). You can also set it persistently in `settings.json` via `reasoningEffort`. Verified: `-r high` passes through to OrcaRouter. (Note: `custom_models` entries have no reasoning field — control it via `-r` or `settings.json`.)
