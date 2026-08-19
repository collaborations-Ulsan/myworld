> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# CC Switch

> Use CC Switch to write OrcaRouter's config into Claude Code, Codex, and Gemini CLI from one place.

CC Switch is a cross-platform tool for unified management of AI CLIs — it
switches the provider configuration for Claude Code, Codex, and Gemini CLI
from one place. Get it from
[GitHub](https://github.com/farion1231/cc-switch)
([releases](https://github.com/farion1231/cc-switch/releases)).

<Note>
  CC Switch is a **config switcher** — it writes OrcaRouter's base URL / key /
  model into the config files that Claude Code, Codex, or Gemini CLI read, and
  lets you switch providers from one place. It also has a built-in connection
  test, so you can verify the endpoint right inside CC Switch.
</Note>

## Install the CC Switch app

<CodeGroup>
  ```bash macOS theme={null}
  brew tap farion1231/ccswitch
  brew install --cask cc-switch
  ```

  ```text Windows theme={null}
  Download the .msi or .zip from the releases page.
  ```

  ```bash Linux theme={null}
  # .deb / .AppImage from releases; on Arch:
  paru -S cc-switch-bin
  ```
</CodeGroup>

## Connect

1. Pick the target app at the top of CC Switch (Claude Code / Codex / Gemini).
2. Click **+** to add a provider and fill in:
   * **Name**: e.g. `orcarouter/auto`
   * **Base URL**: use the rule for the target app's protocol — for **Claude Code**
     it's the bare host `https://api.orcarouter.ai` (no `/v1`); for OpenAI-protocol
     apps use `https://api.orcarouter.ai/v1`.
   * **API key**: `sk-orca-...`
   * **Model**: `orcarouter/auto` (or a specific `vendor/model`)
3. Select the provider (it shows **in use**) — CC Switch writes it into the
   target CLI's config.
4. Use the built-in **test** to check connectivity.

<Check>
  Verified in-app: a `orcarouter/auto` provider for Claude Code with base URL
  `https://api.orcarouter.ai` passed CC Switch's built-in test (`orcarouter/auto
    running normally`, \~731ms).
</Check>

## Notes

* Install the CC Switch desktop app first (see above).
* For Claude Code, the base URL is the **bare host** (no `/v1`) — it's an
  Anthropic-protocol tool. See [Claude Code](/integrations/claude-code).
* After switching, the configured CLI (e.g. [Claude Code](/integrations/claude-code)
  or [Codex CLI](/integrations/codex-cli)) uses OrcaRouter directly.
