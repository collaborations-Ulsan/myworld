> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Codex clients (CLI, IDE, Desktop)

> Use your own OrcaRouter key with Codex — the CLI, the VS Code extension, and the Desktop app all work.

OpenAI ships Codex as more than a terminal tool. Besides the [Codex
CLI](/integrations/codex-cli), there's a VS Code extension and a desktop app. This
page covers using **your own OrcaRouter key** (BYOK) with each, instead of an
OpenAI/ChatGPT subscription.

<Info>
  **Bottom line: the CLI, the VS Code extension, and the Desktop app all work with
  OrcaRouter.**

  These clients all read your `~/.codex/config.toml`, so they pick up the OrcaRouter
  provider you define there. The CLI works out of the box. The **VS Code extension
  and Desktop app also work** — with one catch: the `env_key` API key must be a real
  **OS-level environment variable** (not just one exported in a terminal), and you
  must **restart** the editor/app after setting it.
</Info>

## The surfaces at a glance

| Client                                   | Where it runs                               | BYOK to OrcaRouter?                                                                                                                |
| ---------------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Codex CLI** (`@openai/codex`)          | Terminal (Windows via WSL2)                 | ✅ Works — `model_providers` + `base_url` in `config.toml`. Verified end-to-end.                                                    |
| **VS Code extension** (`openai.chatgpt`) | VS Code, Cursor, Windsurf, VS Code Insiders | ✅ Works — same `config.toml`; the `env_key` must be an **OS-level** env var + restart the editor (see below). Verified end-to-end. |
| **Codex Desktop app**                    | Standalone desktop app                      | ✅ Same shared `config.toml`; set the `env_key` as an OS-level env var (like the other GUI clients).                                |

## Codex CLI

The reference path, verified end-to-end against OrcaRouter (non-streaming + SSE +
reasoning). Full setup, including the one-line installer, is on its own page:

<Card title="Codex CLI setup" icon="terminal" href="/integrations/codex-cli">
  Install, configure `~/.codex/config.toml`, and smoke-test OrcaRouter.
</Card>

The short version — point a custom provider at OrcaRouter's Responses API:

```toml theme={null}
model = "orcarouter/auto"
model_provider = "orcarouter"

[model_providers.orcarouter]
name = "OrcaRouter"
base_url = "https://api.orcarouter.ai/v1"
wire_api = "responses"
env_key = "ORCA_KEY"
```

```bash theme={null}
export ORCA_KEY="sk-orca-..."
```

<Info>
  Current Codex builds require `wire_api = "responses"` (the older `"chat"` value
  was removed). OrcaRouter implements `/v1/responses`, so this works out of the box.
</Info>

<Note>
  **Turn on the model catalog for your key.** Every OrcaRouter API key has a
  **Codex model catalog** switch that is **off by default**. With it off, Codex
  never learns the real context window for `orcarouter/...` models and silently
  uses its stock fallback — no error is shown. This applies to all Codex surfaces
  below, since they share the same key. See
  [Model catalog (per-key opt-in)](/integrations/codex-cli#model-catalog-per-key-opt-in).
</Note>

## VS Code extension (and Cursor / Windsurf)

OpenAI's official extension is **Codex – OpenAI's coding agent**, publisher
`OpenAI`, marketplace ID [`openai.chatgpt`](https://marketplace.visualstudio.com/items?itemName=openai.chatgpt).
It runs the same agent as the CLI and reads the **same `~/.codex/config.toml`**,
so the `orcarouter` provider above is shared automatically. It also works in VS
Code forks (Cursor, Windsurf) and VS Code Insiders.

**It works with OrcaRouter — verified end-to-end** (the extension sent a request
through the `orcarouter` provider and returned the reply). Two things matter:

<Warning>
  **The API key must be an OS-level environment variable, and you must restart the
  editor.**

  The extension authenticates the custom provider via the `env_key` you name in
  `config.toml` (e.g. `ORCA_KEY`). Unlike the CLI, the extension process does **not**
  see a key you merely `export`ed in a terminal — it reads the variable from the OS
  environment it was launched with. So:

  1. Set the key as a **user/system environment variable** (Windows: *Edit
     environment variables for your account* → New → `ORCA_KEY`; macOS/Linux: set
     it in your login shell profile / launchd / systemd, not just the current
     shell).
  2. **Fully quit and reopen** the editor (a "Reload Window" is not enough — it must
     inherit the new environment).

  If the key isn't visible this way, the extension shows
  `Missing environment variable: ORCA_KEY`. Note the extension only honors
  `env_key` — it ignores the `experimental_bearer_token` (inline-key) field that the
  CLI accepts.
</Warning>

After that, the OrcaRouter provider is live in the extension. (The model picker
lists OpenAI's built-in models plus a `Custom` entry when a custom
`model_provider` is the default; the request itself goes to OrcaRouter.)

## Codex Desktop app

OpenAI also ships a standalone Codex desktop application that reads the same
`~/.codex/config.toml`, so the `orcarouter` provider carries over. As with the
other GUI clients, supply the `env_key` via an OS-level environment variable (not
just a shell `export`) and restart the app.

## Recommendation

For OrcaRouter, the **[Codex CLI](/integrations/codex-cli)** is the simplest path —
it picks up the key from an ordinary `export`. The **VS Code extension** and the
**Desktop app** also work, as long as the `env_key` is set as an OS-level
environment variable and you restart the editor/app.
