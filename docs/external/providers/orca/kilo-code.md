> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Kilo Code

> Use OrcaRouter inside Kilo Code — VS Code extension or CLI, via the OpenAI Compatible provider.

[Kilo Code](https://kilocode.ai) is an open-source AI coding agent available in
VS Code, JetBrains, **CLI**, Slack, and Cloud. It connects to OrcaRouter through
its **Custom provider** (an OpenAI-compatible endpoint). This guide covers both
the **VS Code extension** (the most common way to use Kilo Code) and the **CLI**
(`@kilocode/cli`, for headless use).

<Info>
  **Protocol: OpenAI-compatible**

  * **Base URL:** `https://api.orcarouter.ai/v1` (includes `/v1`)
  * Model IDs use the `vendor/model` format — the simplest is `orcarouter/auto`
</Info>

<Tip>
  **⚡ Recommended: one-line setup (CLI)**

  For the **CLI** (`@kilocode/cli`), this installs it (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool kilo-code
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool kilo-code
    ```
  </CodeGroup>

  Using the **VS Code extension** instead? Follow the manual steps below.
</Tip>

## VS Code extension

1. Install **Kilo Code** from the VS Code Marketplace (open the Extensions panel
   and search "Kilo Code"), then open it from the **Kilo Code icon in the
   Activity Bar** (the left icon strip). In the panel, click the **⚙ gear** in
   the top-right to open settings.

<Frame caption="Open the Kilo Code panel, then the ⚙ settings (top-right)">
  <img src="https://mintcdn.com/orcarouter/wjhML-Ju5dAzxpib/images/integrations/kilo-code/01-open-panel.jpg?fit=max&auto=format&n=wjhML-Ju5dAzxpib&q=85&s=5eae07248a5a2467b74e3e52016e7d26" alt="The Kilo Code panel with the settings gear highlighted" width="442" height="1334" data-path="images/integrations/kilo-code/01-open-panel.jpg" />
</Frame>

2. Go to **Providers**. Under **Popular providers**, find **Custom provider**
   ("Add an OpenAI-compatible provider by base URL") and click **+ Connect**.

<Frame caption="Pick the Custom provider — an OpenAI-compatible endpoint by base URL">
  <img src="https://mintcdn.com/orcarouter/wjhML-Ju5dAzxpib/images/integrations/kilo-code/02-provider.jpg?fit=max&auto=format&n=wjhML-Ju5dAzxpib&q=85&s=3370f1d0ad75f9afa24e2a9b1f9bfce5" alt="The Custom provider entry in Kilo Code's Providers settings" width="973" height="1008" data-path="images/integrations/kilo-code/02-provider.jpg" />
</Frame>

3. Fill in the provider fields:
   * **Provider ID**: `orcarouter` (lowercase letters, numbers, hyphens, or
     underscores only — **no slashes**; `orcarouter/auto` is rejected here).
   * **Display name**: `OrcaRouter` (anything you like).
   * **Base URL**: `https://api.orcarouter.ai/v1`
   * **API key**: your OrcaRouter key (`sk-orca-...`).

<Frame caption="Provider ID, display name, base URL, and API key">
  <img src="https://mintcdn.com/orcarouter/wjhML-Ju5dAzxpib/images/integrations/kilo-code/03-fields.jpg?fit=max&auto=format&n=wjhML-Ju5dAzxpib&q=85&s=527905d8b118a721c5df869c96276ccc" alt="OrcaRouter provider ID, base URL, and API key in Kilo Code" width="528" height="525" data-path="images/integrations/kilo-code/03-fields.jpg" />
</Frame>

4. Choose your models. Once the key and base URL are valid, Kilo Code fetches the
   live model list from OrcaRouter — tick the ones you want (or **Select all**),
   then click **Submit**. To use auto-routing, also **+ Add model** with the
   model **ID** `orcarouter/auto` (it's a routing alias, so it won't appear in
   the fetched list).

<Frame caption="Kilo Code fetches the live model list from OrcaRouter; tick models and Submit">
  <img src="https://mintcdn.com/orcarouter/wjhML-Ju5dAzxpib/images/integrations/kilo-code/04-models.jpg?fit=max&auto=format&n=wjhML-Ju5dAzxpib&q=85&s=23a0575cfb4b1915d7c949f1218abe18" alt="Kilo Code model picker showing models fetched from OrcaRouter" width="552" height="534" data-path="images/integrations/kilo-code/04-models.jpg" />
</Frame>

5. The provider now shows under **Connected providers** as **OrcaRouter
   (CUSTOM)**.

<Frame caption="OrcaRouter now appears under Connected providers">
  <img src="https://mintcdn.com/orcarouter/wjhML-Ju5dAzxpib/images/integrations/kilo-code/05-connected.jpg?fit=max&auto=format&n=wjhML-Ju5dAzxpib&q=85&s=11a01896657ec4f62db4c6eb77d54f69" alt="OrcaRouter listed under Connected providers in Kilo Code" width="966" height="893" data-path="images/integrations/kilo-code/05-connected.jpg" />
</Frame>

6. Select the **OrcaRouter** model in the chat panel's model picker and send a
   test message — a reply confirms the connection.

<Frame caption="A reply through the OrcaRouter provider confirms the connection">
  <img src="https://mintcdn.com/orcarouter/wjhML-Ju5dAzxpib/images/integrations/kilo-code/06-reply.jpg?fit=max&auto=format&n=wjhML-Ju5dAzxpib&q=85&s=cf1c2fd2577b5d01a8aa9cf355571d49" alt="Kilo Code replying through OrcaRouter" width="596" height="1310" data-path="images/integrations/kilo-code/06-reply.jpg" />
</Frame>

<Note>
  On a large repository, Kilo Code may first ask whether to wait for its snapshot
  system to initialize — choose **Disable for this project** to skip it (git still
  tracks everything) so the request goes through.
</Note>

<Note>
  The **JetBrains** plugin uses the same **Custom provider** with the identical
  base URL / key / model values.
</Note>

## CLI

For headless / scripted use, install the CLI.

### Install

```bash theme={null}
npm install -g @kilocode/cli
```

The command is `kilo`.

### Configure

Config file: `~/.config/kilo/kilo.jsonc` (also accepts `kilo.json`; project-level `./kilo.jsonc` overrides).

```jsonc theme={null}
{
  "$schema": "https://app.kilo.ai/config.json",
  "provider": {
    "orcarouter": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OrcaRouter",
      "options": { "baseURL": "https://api.orcarouter.ai/v1", "apiKey": "sk-orca-..." },
      "models": { "orcarouter/auto": { "name": "OrcaRouter Auto" } }
    }
  },
  "model": "orcarouter/orcarouter/auto"
}
```

Swap in a specific model if you prefer, e.g. `anthropic/claude-opus-4.8` or `google/gemini-2.5-flash`. Model IDs use the `vendor/model` format.

### Run

```bash theme={null}
echo "Reply with exactly: OK" | kilo run --auto --format json
```

Expected: a JSON event with `"type":"text"` and `"text":"OK"`.

### Notes

* The `base_url` includes `/v1`.
* Model references use `provider/model`. Because the provider is named `orcarouter` and the model ID also carries a `vendor` prefix, the reference is three segments: `orcarouter/orcarouter/auto` (or `orcarouter/anthropic/claude-opus-4.8`).
* Headless mode is `kilo run "<prompt>" --auto` (or pipe the prompt via stdin). `--format json` gives a machine-readable event stream.
* **Reasoning/thinking:** use the `--variant <name>` flag for provider-specific reasoning effort (e.g. `high`, `max`, `minimal`), and `--thinking` to display thinking blocks.

<Warning>
  **Known issue:** `--auto` has reported cases of hanging after completion / when
  the key is missing
  ([kilocode issues](https://github.com/Kilo-Org/kilocode/issues)). Wrap with a
  `timeout` in CI and make sure the key is loaded.
</Warning>
