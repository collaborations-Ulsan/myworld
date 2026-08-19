> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Claude Code

> Use OrcaRouter inside Claude Code — Anthropic protocol, configured via environment variables.

[Claude Code](https://www.anthropic.com/claude-code) is Anthropic's terminal
coding agent. Point it at OrcaRouter with environment variables.

<Info>
  **Protocol: Anthropic Messages**

  * **Base URL:** `https://api.orcarouter.ai` — **without** `/v1`
  * Claude Code appends `/v1/messages` itself; adding `/v1` would produce `/v1/v1/messages` and fail
</Info>

<Tip>
  **⚡ Recommended: one-line setup**

  Skip the manual steps below — this installs Claude Code (if missing), writes the
  config, and smoke-tests OrcaRouter. You'll be prompted for your API key (or set
  `ORCA_KEY` in the environment to run unattended — prefer that over a `--key` flag,
  which lands in your shell history).

  <CodeGroup>
    ```bash macOS / Linux theme={null}
    curl -fsSL https://api.orcarouter.ai/install.sh | sh -s -- --tool claude-code
    ```

    ```powershell Windows theme={null}
    & ([scriptblock]::Create((irm https://api.orcarouter.ai/install.ps1))) -Tool claude-code
    ```
  </CodeGroup>

  To set it up by hand instead, follow the steps below.
</Tip>

## Install

```bash theme={null}
npm install -g @anthropic-ai/claude-code
```

On **Windows**, Claude Code requires Git Bash. Install
[Git for Windows](https://git-scm.com/downloads/win), then set
`CLAUDE_CODE_GIT_BASH_PATH` to your `bash.exe`
(e.g. `C:\Program Files\Git\bin\bash.exe`).

## Configure

```bash theme={null}
export ANTHROPIC_BASE_URL="https://api.orcarouter.ai"     # no /v1
export ANTHROPIC_AUTH_TOKEN="sk-orca-..."
export ANTHROPIC_MODEL="orcarouter/auto"                  # or e.g. anthropic/claude-opus-4.8
export ANTHROPIC_SMALL_FAST_MODEL="anthropic/claude-haiku-4.5"
```

## Run

```bash theme={null}
claude -p "Reply with exactly: OK"
```

You should see `OK`. Then run `claude` for an interactive session and use
`/model` to switch models.

## Notes

* `ANTHROPIC_BASE_URL` must **not** include `/v1`.
* Model names use the `vendor/model` format; `orcarouter/auto` is the simplest choice.
* On Windows, set `CLAUDE_CODE_GIT_BASH_PATH` to your Git Bash `bash.exe`.

<Note>
  **VS Code extension:** Anthropic's official Claude Code extension just runs the
  CLI inside the editor — it shares the same configuration. Set the environment
  variables above (or your `~/.claude/settings.json`) and the extension picks them
  up; there's no separate in-editor endpoint setting.
</Note>

## Enable thinking / reasoning

Extended thinking is **on by default** (adaptive) — a reasoning model thinks
automatically, no extra config needed. To tune it, lower the effort level with
the `/effort` command or via `/model`, disable thinking in `/config`, or set
`MAX_THINKING_TOKENS` to cap the budget on fixed-budget models (adaptive models
ignore a nonzero budget — use effort levels there).
