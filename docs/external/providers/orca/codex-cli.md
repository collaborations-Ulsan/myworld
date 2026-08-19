> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Codex CLI

> Use OrcaRouter inside OpenAI's Codex CLI — OpenAI Responses API.

[Codex CLI](https://github.com/openai/codex) (`@openai/codex`) is OpenAI's
terminal coding agent. Recent versions speak the **OpenAI Responses API**.

<Info>
  **Protocol: OpenAI Responses API**

  * **Base URL:** `https://api.orcarouter.ai/v1` (includes `/v1`)
  * **wire\_api:** must be `"responses"` — current Codex builds removed the older `"chat"` value
  * OrcaRouter implements `/v1/responses`, so it works out of the box
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs Codex CLI (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool codex
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool codex
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

```bash theme={null}
npm install -g @openai/codex
```

## Configure

Edit `~/.codex/config.toml`:

```toml theme={null}
model = "orcarouter/auto"
model_provider = "orcarouter"

[model_providers.orcarouter]
name = "OrcaRouter"
base_url = "https://api.orcarouter.ai/v1"
wire_api = "responses"
env_key = "ORCA_KEY"
```

Then export the key the config refers to:

```bash theme={null}
export ORCA_KEY="sk-orca-..."
```

## Run

```bash theme={null}
codex exec --skip-git-repo-check "Reply with exactly: OK"
```

## Model catalog (per-key opt-in)

Codex ships a bundled catalog of the models it knows. OrcaRouter can serve Codex
its own catalog instead — one entry per router in your workspace
(`orcarouter/auto`, your named routers, plus the built-in fusion tiers and
`orcarouter/free`), with the context window and tool wiring taken from the
official Codex catalog for your client version. That's what makes
`orcarouter/...` a *known* model to Codex rather than an unrecognized slug.

<Warning>
  **This is off by default on every API key, and leaving it off fails silently.**

  Turn on the **Codex model catalog** switch (`codex_catalog_enabled`) on the key
  you use with Codex — it's in the key's settings in the
  [Dashboard](https://www.orcarouter.ai/console), and it defaults to off for every
  key, including keys you created before the feature existed.

  With it off, OrcaRouter answers Codex's catalog request with `HTTP 200` and an
  empty list. **There is no error and no warning anywhere** — not in Codex, not in
  your logs. Codex merges an empty list as a no-op, keeps its bundled catalog, and
  falls back to its stock defaults for the unknown `orcarouter/...` slug. Requests
  still work, so the only symptom is that you quietly get Codex's fallback context
  window instead of the window the router actually supports.
</Warning>

Once it's on, the `/model` menu lists your **router aliases** — `orcarouter/auto`,
`orcarouter/free`, and any [named routers](/routing/named-routers) enabled in your
workspace — not individual model IDs. Routing to a concrete model still happens
server-side.

<Note>
  **Codex only asks for a catalog when the provider uses command-backed auth.**
  The `env_key` setup above never sends the request, so the switch has no effect
  on it — flipping it on changes nothing until you move that provider to a
  credential command. Requests keep working either way; only the catalog is
  skipped.
</Note>

<Note>
  Workspace admins have a matching workspace-wide switch that turns the catalog off
  for every key in the workspace. It behaves identically when off: empty list, no
  error. If the per-key switch is on and Codex still shows no OrcaRouter models,
  check with your workspace admin.
</Note>

## Notes

* Model names use the `vendor/model` format; `orcarouter/auto` is simplest.
* On Windows, Codex runs under WSL2.

<Note>
  **Other Codex clients (IDE / Desktop / Cloud):** OpenAI's VS Code extension,
  JetBrains plugin, and Desktop app all *nominally* share this same
  `~/.codex/config.toml`, but custom providers currently misbehave in those GUIs
  (open upstream bugs) — for OrcaRouter, use the CLI. The Cloud/Web agent can't
  BYOK at all. See [Codex clients (IDE / Desktop / Cloud)](/integrations/codex-clients)
  for the full breakdown.
</Note>

## Enable thinking / reasoning

Set `model_reasoning_effort` in `config.toml` (`minimal` / `low` / `medium` /
`high` / `xhigh`; default `medium`), or pick it from the `/model` menu in an
interactive session.
