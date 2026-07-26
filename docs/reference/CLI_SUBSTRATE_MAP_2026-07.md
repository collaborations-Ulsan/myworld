# CLI Substrate Capability Map — claude / codex / agy (2026-07-27)

**Why this document exists** (founder, 2026-07-27): *"모든 것들을 알고, 공부해야 사용할 수도,
필요한 걸 만들어낼 수도 있지 않을까"* — we have repeatedly used ~20% of these tools' surface.
Concrete case: `agy` supported multi-turn (`--continue`/`--conversation`), model/effort selection,
plan mode, agents, plugins and sandbox the whole time, while the operator fired one-shot `-p`
prompts for weeks.

**Method**: every claim below was verified on THIS machine on 2026-07-27 by running `--help` /
listing subcommands and reading on-disk config, unless explicitly tagged `UNVERIFIED` or
`[observed <date>]` (= real behavior seen in an operator session, not re-run today). Exactly one
tiny live model call per CLI was used to confirm headless syntax. No secrets are reproduced here.

Versions at time of audit:

| CLI | Binary | Version | Auth | State root |
|---|---|---|---|---|
| claude (Claude Code) | `~/.local/bin/claude` | 2.1.220 | OAuth (subscription) | `~/.claude/` |
| codex (OpenAI Codex CLI) | `~/bin/codex` (npm `@openai/codex`) | 0.145.0 | ChatGPT login (`codex login status` → "Logged in using ChatGPT") | `~/.codex/` |
| agy (Antigravity / Google) | `~/.local/bin/agy` → wrapper → `agy.real` | 1.1.7 | Google OAuth | `~/.gemini/antigravity-cli/` (+ `~/.gemini/config/`) |

> **TRAP (verified)**: `~/.local/bin/agy` is a 12-line wrapper that **auto-injects
> `--dangerously-skip-permissions` into EVERY invocation** (`exec agy.real --dangerously-skip-permissions "$@"`).
> Every agy call on this box already runs with all permission prompts auto-approved. To run agy
> WITH permission prompts, call `~/.local/bin/agy.real` directly (or set `AGY_REAL_BIN`).

---

## 1. claude — Claude Code 2.1.220

### 1.1 Invocation surface (verified via `claude --help`)

Default = interactive TUI. `claude -p "<prompt>"` = headless print mode.

Flags that matter (all verified in help output):

| Flag | What it does |
|---|---|
| `-p, --print` | non-interactive; skips workspace-trust dialog; invalid settings files silently ignored |
| `--model <alias\|full>` | `fable` / `opus` / `sonnet` / `haiku` or full name (`claude-fable-5`) |
| `--effort low\|medium\|high\|xhigh\|max` | reasoning effort per session |
| `-c, --continue` | continue most recent conversation **in the current directory** |
| `-r, --resume [id\|search]` | resume by session ID (or interactive picker) |
| `--fork-session` | resume into a NEW session id (branch a conversation) |
| `--session-id <uuid>` | pin your own session UUID |
| `-n, --name <name>` | display name for the session (shows in `/resume` picker) |
| `--output-format text\|json\|stream-json` | print-mode output; `json` = single result envelope |
| `--input-format text\|stream-json` | streaming stdin protocol for long-lived driving |
| `--json-schema <schema>` | **structured output validated against a JSON Schema** |
| `--max-budget-usd <amt>` | hard dollar cap per print-mode run |
| `--fallback-model <m1,m2>` | auto-failover when primary is overloaded (print mode only) |
| `--bg, --background` | dispatch as background agent, return immediately; manage with `claude agents` |
| `--agent <name>` / `--agents <json>` | run AS a named agent / define agents inline as JSON |
| `--permission-mode` | `acceptEdits` / `auto` / `bypassPermissions` / `manual` / `dontAsk` / `plan` |
| `--allowedTools` / `--disallowedTools` / `--tools` | tool allow/deny lists; `--tools ""` disables all |
| `--add-dir <dirs…>` | widen filesystem access |
| `-w, --worktree [name]` | run session in a fresh git worktree |
| `--mcp-config <json/file>` / `--strict-mcp-config` | inject MCP servers per-run |
| `--plugin-dir` / `--plugin-url` | load a plugin for this session only |
| `--system-prompt` / `--append-system-prompt` | replace/extend system prompt |
| `--settings <file-or-json>` | layer extra settings |
| `--bare` | minimal mode: no hooks/plugins/CLAUDE.md; auth = API key ONLY (OAuth never read — so on this box `--bare` will not authenticate) |
| `--safe-mode` | all customizations disabled (troubleshooting) |
| `--no-session-persistence` | print-mode session not saved/resumable |
| `--include-partial-messages` / `--include-hook-events` / `--forward-subagent-text` | stream-json enrichments |
| `--verbose`, `-d/--debug [filter]`, `--debug-file` | diagnostics |

Subcommands: `agents` (background-agent dashboard; `--json` for scripting) · `auth login/logout/status` ·
`auto-mode` (classifier config) · `doctor` · `mcp` (add/add-json/get/list/login/remove/serve) ·
`plugin` (list/install/enable/disable/details/eval/init/marketplace/validate/tag) ·
`project purge` (**destructive** — deletes all project state) · `setup-token` ·
`ultrareview [--json] [--timeout min]` (cloud multi-agent code review of current branch/PR) ·
`update` · `install` · `gateway`.

### 1.2 Model / effort selection

- Aliases verified: `fable`, `opus`, `sonnet`, `haiku` (help text) — **no CLI model-listing
  subcommand exists** (verified absent from `--help`); full model IDs come from the `claude-api`
  skill or `/model` in the TUI.
- Effort: `--effort low|medium|high|xhigh|max`; user default currently `xhigh`
  (`~/.claude/settings.json: "effortLevel": "xhigh"`).
- Live probe (2026-07-27): `claude -p 'Reply with exactly: OK' --model haiku --output-format json`
  → exit 0, `"result":"OK"`, `modelUsage` resolved `haiku` → `claude-haiku-4-5-20251001`.

### 1.3 Session / continuity (highest-value under-used surface)

- Every `-p` run **persists a session by default** — verified: probe returned
  `"session_id":"a513…"` and `~/.claude/projects/<cwd-slug>/a513….jsonl` appeared on disk.
- Multi-turn headless pattern:
  ```bash
  sid=$(claude -p "step 1…" --output-format json | jq -r .session_id)
  claude -p -r "$sid" "step 2, building on your last answer…" --output-format json
  ```
  (`-r <id>` with `-p` — flags verified from help; combined use [observed 2026-07 in OMC tooling],
  not re-probed today under the 1-call budget.)
- `--continue` = most recent session in cwd; `--fork-session` = branch without contaminating the
  original; `--session-id` = deterministic ids for orchestrators; `-n` = human-readable names.
- Sessions live in `~/.claude/projects/<escaped-cwd>/<session-id>.jsonl` (verified on disk).

### 1.4 Extensibility (all paths verified on disk)

| Mechanism | Location here | Current state |
|---|---|---|
| Subagents | `~/.claude/agents/*.md` (19: analyst…writer) + project `.claude/agents/` | OMC roster installed |
| Skills | `~/.claude/skills/` (100 dirs) + project `.claude/skills/` | OMC+gstack+AIOS skills |
| Plugins | `claude plugin …`; state in `~/.claude/plugins/`; enabled: `insane-search@gptaku-plugins` 0.8.2, `ponytail@ponytail` 4.8.4 | marketplaces: gptaku-plugins, ponytail |
| Hooks | `~/.claude/settings.json` `hooks:` (SessionStart → aios_session_entropy.py + gptaku update check) + `~/.claude/hooks/*.mjs` (OMC) | active |
| MCP (user) | `~/.claude.json` `mcpServers`: **aios, kaggle, omc, playwright** | active |
| MCP (project) | `myworld/.mcp.json`: **aios** (`scripts/aios_mcp_server.py --root .`) | active |
| MCP server mode | `claude mcp serve` — mount Claude Code itself as an MCP server | unused |
| Status line | `settings.json statusLine` (OMC HUD) | active |
| Memory | `~/.claude/CLAUDE.md`, project `CLAUDE.md`, auto-memory `MEMORY.md` | active |

### 1.5 Automation / headless

- Verified envelope (`--output-format json`): `is_error`, `result`, `session_id`, `num_turns`,
  `total_cost_usd`, `usage` (incl. cache tokens), `modelUsage` (per-model cost/limits),
  `permission_denials`, `terminal_reason`, `duration_ms`, `ttft_ms`, `api_error_status`. Exit 0 on
  success. This is machine-parseable cost+outcome telemetry for free.
- `stream-json` in/out enables driving Claude as a long-lived subprocess (realtime streaming input).
- Detached: `--bg` + `claude agents --json` (poll), or plain `nohup`/`run_in_background`.
- Budget/robustness: `--max-budget-usd`, `--fallback-model` (print only).

### 1.6 Sandboxing / permissions

- Modes: see `--permission-mode` row above; `plan` = read-only planning lane.
- **Current user default is `bypassPermissions`** (`settings.json permissions.defaultMode`) with
  `skipDangerousModePermissionPrompt: true` — headless runs on this box already bypass prompts.
- Safe-unattended recipe when isolation matters: `--permission-mode plan` (read-only) or
  `--tools`/`--allowedTools` whitelists + `--max-budget-usd`.

### 1.7 Failure modes

- Invalid settings files are **silently ignored** in `-p` mode (help text) — a broken settings JSON
  degrades without error.
- `--bare` + OAuth = no auth (help text: OAuth never read in bare mode).
- Nested-session env: running `claude` inside a Claude Code session works but inherits
  `CLAUDECODE=1` env [observed repeatedly]; use `env -u CLAUDECODE` if a wrapper misbehaves. UNVERIFIED today.
- Cost surprise: even `haiku` + 3-word prompt cost $0.069 because ~53K context tokens (CLAUDE.md,
  skills) load per run (measured in today's probe). For high-volume loops prefer `--bare`(API key),
  smaller cwd, or local LLMs.

---

## 2. codex — OpenAI Codex CLI 0.145.0

### 2.1 Invocation surface (verified via `--help` tree)

Subcommands: `exec` (headless; alias `e`) · `exec resume` · `review` · `login [status]` · `logout` ·
`mcp list/get/add/remove/login/logout` · `plugin add/list/marketplace/remove` · `mcp-server`
(Codex AS an MCP server, stdio) · `app-server` (+ `daemon`, `proxy`, protocol codegen) ·
`remote-control start/stop/pair` · `completion` · `update` · `doctor` · `sandbox <cmd…>` ·
`debug models|app-server|prompt-input` · `apply <task-id>` · `resume` / `fork` / `archive` /
`delete` / `unarchive` (session management) · `cloud exec/status/list/apply/diff` ·
`exec-server` · `features list/enable/disable`.

Global flags: `-c key=value` (override ANY `config.toml` key, dotted paths, TOML-parsed values) ·
`--enable/--disable <FEATURE>` · `-m/--model` · `--oss --local-provider lmstudio|ollama` ·
`-p/--profile <name>` (layers `$CODEX_HOME/<name>.config.toml`; none defined here) ·
`-s/--sandbox read-only|workspace-write|danger-full-access` ·
`-a/--ask-for-approval untrusted|on-request|never` · `--dangerously-bypass-approvals-and-sandbox` ·
`--dangerously-bypass-hook-trust` · `-C/--cd <dir>` · `--add-dir` · `--search` (live web_search tool) ·
`-i/--image <file>` (multimodal input) · `--strict-config`.

`codex exec` extras: `--json` (JSONL events) · `-o/--output-last-message <file>` ·
`--output-schema <file>` (**JSON Schema for the final answer**) · `--ephemeral` (no session files) ·
`--skip-git-repo-check` · `--ignore-user-config` · `--ignore-rules` · `--color`.

**The exact invocation that works here** (verified pattern; note both traps):
```bash
codex exec -m gpt-5.5 -c model_reasoning_effort=high --json \
  -o /tmp/last_msg.txt "…prompt…" < /dev/null
```
- **TRAP 1 (verified live)**: with stdin piped/open, exec prints `Reading additional input from
  stdin...` and waits — always close stdin (`< /dev/null`) in automation.
- **TRAP 2**: exit code is NOT a reliable failure signal — parse the JSONL for
  `turn.completed` vs `turn.failed` (today's failed run still streamed clean JSON events;
  exit-code semantics UNVERIFIED).

### 2.2 Model / effort selection (verified via `codex debug models`)

Catalog slugs right now: `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.5`, `gpt-5.4`,
`gpt-5.4-mini`, `gpt-5.3-codex-spark`, `codex-auto-review`. Cached at `~/.codex/models_cache.json`.

- Effort: `-c model_reasoning_effort=low|medium|high|xhigh` (user default in config.toml: `xhigh`;
  base model `gpt-5.5`).
- [observed 2026-07-10] headless survives only `gpt-5.5` + effort override; `gpt-5.6-sol`
  collaboration mode returned 400 (memory `reference-codex-agy-headless-invocation`). Re-test after
  quota resets — 0.145.0 may have fixed it. UNVERIFIED today (quota exhausted, see 2.7).

### 2.3 Session / continuity

- Headless multi-turn (verified from help; sessions verified on disk under
  `~/.codex/sessions/YYYY/MM/DD/rollout-…-<uuid>.jsonl`):
  ```bash
  codex exec --json "step 1…" < /dev/null            # emits {"type":"thread.started","thread_id":"…"}
  codex exec resume <THREAD_ID> "step 2…" < /dev/null  # or: codex exec resume --last "step 2…"
  ```
  `thread.started` event with `thread_id` verified live today.
- Interactive: `codex resume [--last|--all]`, `codex fork` (branch a session), `archive`/`delete`/
  `unarchive`. `--include-non-interactive` folds exec sessions into the picker.
- `--ephemeral` opts OUT of persistence for throwaway runs.

### 2.4 Extensibility (verified on disk)

| Mechanism | Location here | Current state |
|---|---|---|
| Custom prompts (slash) | `~/.codex/prompts/*.md` — 37 OMX role prompts | oh-my-codex installed |
| Native subagents | `~/.codex/agents/*.toml` — 22 role TOMLs; `multi_agent` feature = true | active |
| Skills | `~/.codex/skills/` (+ `skills.disabled/`); features `skill_search`, `skill_mcp_dependency_install` stable | OMX skills |
| Hooks | `~/.codex/hooks.json` — SessionStart/PreToolUse/PostToolUse/UserPromptSubmit → oh-my-codex native hook; `features.hooks=true` | active |
| MCP client | `codex mcp list` (verified): stdio **aios**, **open-design**; HTTP **figma**, **github** (bearer via env var name), **notion** | active |
| MCP server | `codex mcp-server` (stdio) — mount Codex inside another agent | unused |
| Plugins | `codex plugin list/add` + marketplaces; `features.plugins=true` | none installed |
| Feature flags | `codex features list` — 100+ flags incl. stable: `browser_use`, `computer_use`, `image_generation`, `multi_agent`, `personality`, `fast_mode`, `goals`, `guardian_approval`, `unified_exec`, `apps` | inspect before assuming a capability is off |
| Config layers | `~/.codex/config.toml` + `-p <profile>` + `-c` overrides + `~/.codex/AGENTS.md` (global rules) | OMX-managed |
| Local models | `--oss --local-provider ollama` — Codex harness on local models | **unused; see §A-4** |
| Cloud | `codex cloud exec/status/diff/apply` — remote task execution | unused, EXPERIMENTAL |
| Review | `codex review --uncommitted | --base <branch> | --commit <sha>` | unused |

### 2.5 Automation / headless

- `--json` = JSONL event stream (`thread.started` / `turn.started` / `item.completed` /
  `turn.completed|turn.failed`) — verified live. `-o file` = just the final message.
  `--output-schema file.json` = schema-constrained final answer (help-verified).
- Detached: standard `nohup`/background; sessions persist for later `exec resume`.
- `codex doctor` (verified): env/auth/sandbox diagnostics. Today it flagged **6,029 rollout files ·
  6.53 GB on disk** and 2 thread-state issues — periodic `codex delete`/archival is real hygiene.

### 2.6 Sandboxing / permissions

- Axes: `-s` sandbox (read-only / workspace-write / danger-full-access) × `-a` approvals
  (untrusted / on-request / never).
- **Current config.toml default: `approval_policy="never"` + `sandbox_mode="danger-full-access"` +
  `network_access="enabled"`** — codex doctor explicitly warns "filesystem unrestricted · network
  enabled". Fine for this trusted box, but any untrusted/generated-code lane should pass
  `-s workspace-write -a on-request` explicitly.
- `codex sandbox <cmd…>` runs an ARBITRARY command in Codex's Linux sandbox — a free-standing
  isolation primitive usable by AIOS itself (skill verification, untrusted artifact execution).
- Per-project trust recorded in config.toml `[projects."…"] trust_level`.

### 2.7 Failure modes

- **[observed 2026-07-27, live]** Usage limit exhaustion: probe returned
  `{"type":"turn.failed","error":{"message":"You've hit your usage limit … try again at Aug 2nd, 2026 4:55 AM"}}`.
  Codex lane is DEAD until ~2026-08-02 04:55. Detect: JSONL `error` event containing "usage limit".
- **[observed 2026-07-26/27 session]** OpenAI 503 `biscuit_baker_service_me_circuit_open` mid-run
  killed a build lane. Detect: stderr/JSONL 5xx; handle: retry-with-backoff then failover to
  another substrate (see §B-1).
- Stdin hang (see 2.1 TRAP 1). Skills context budget: probe emitted a warning that skill
  descriptions were truncated to a 2% context budget — too many installed skills degrades Codex
  silently.
- [observed, recorded in `~/.codex/AGENTS.md`] a historical `codex --help` failure printing
  `틀렸습니다 (1/3)…` — not reproduced today (help works).

---

## 3. agy — Antigravity CLI 1.1.7 (Google)

### 3.1 Invocation surface (verified via `agy --help`)

Interactive by default. Flags:
`--print/-p/--prompt` (headless) · `--print-timeout` (**default 5m0s** — raise it:
`--print-timeout 20m`) · `--prompt-interactive/-i` (seed a prompt, stay interactive) ·
`--continue/-c` · `--conversation <id>` · `--model <slug>` · `--effort low|medium|high` ·
`--mode accept-edits|plan` · `--agent <name>` · `--add-dir` (repeatable) · `--sandbox`
(terminal restrictions) · `--dangerously-skip-permissions` (wrapper adds this ALWAYS — see top) ·
`--new-project` / `--project <id>` · `--log-file`.

Subcommands: `models` · `agent|agents` (list; currently empty) · `plugin list/import/install/
uninstall/enable/disable/validate/link` · `changelog` · `install` (PATH/shell setup) · `update` ·
`help <sub>`.

Headless pattern that works (verified live today):
```bash
agy --model gemini-3.6-flash-low -p 'prompt'          # plain text out, exit 0
agy -c -p 'follow-up'                                  # continue cwd's latest conversation
agy --conversation <uuid> -p 'follow-up'               # address a specific thread
```

### 3.2 Model / effort selection (verified via `agy models`)

```
gemini-3.6-flash-high|medium|low
gemini-3.5-flash-high|medium|low
gemini-3.1-pro-high|low
claude-sonnet-4-6
claude-opus-4-6-thinking
gpt-oss-120b-medium
```
**agy is itself multi-provider**: it can address Anthropic Claude and an open-weights GPT-OSS-120B
through the Google subscription — a built-in heterogeneous panel and a failover path when one
provider is down (see §A-3). Effort is either baked into the slug or set via `--effort`
(and `/effort` in the TUI). Default model currently "Gemini 3.6 Flash (High)"
(`~/.gemini/antigravity-cli/settings.json`).

### 3.3 Session / continuity

- `--continue` (most recent conversation), `--conversation <id>` (specific), `-i` (interactive
  with seed prompt). Multi-turn `-p` dialogues over `-c` verified in operator session 2026-07-27.
- Conversation IDs on disk: `~/.gemini/antigravity-cli/cache/last_conversations.json` —
  **a cwd→conversation-uuid map** (verified). Full transcripts: `conversations/<uuid>.db` (SQLite),
  summaries in `conversation_summaries.db`, agent state in `brain/<uuid>/`.
- Projects group conversations: `--new-project` / `--project <id>`; registry in
  `~/.gemini/config/projects/*.json` and `cache/projects.json`.

### 3.4 Extensibility (verified from the builtin `agy-customizations` skill + binary strings)

Discovery roots: workspace `.agents/` (walks cwd→repo root; also `.agent/`, `_agents/`, `_agent/`)
→ declared `skills.json`/`plugins.json` → global `~/.gemini/config/` → builtin. Higher root wins
name conflicts.

| Mechanism | Path | Notes |
|---|---|---|
| Rules | `GEMINI.md` / `AGENTS.md` per directory, `.agents/rules/*.md` | hierarchical, deduplicated |
| Skills | `.agents/skills/<name>/SKILL.md` (frontmatter name+description), global `~/.gemini/config/` | progressive disclosure — only descriptions injected until activated |
| Custom agents | `.agents/agents/` — markdown `agent.md` with YAML frontmatter: `mainAgent`, `subagent`, `hidden`, `inheritMcp`, `commandExecutionPolicy`, `model` (per-agent model tier) | binary-strings + changelog 1.1.5/1.1.6 verified; none defined here yet (`agy agents` empty) |
| Hooks | `.agents/hooks.json` (named hooks → `PreToolUse`/`PostToolUse`/`PreInvocation`/`PostInvocation`/`Stop`, matcher+command+timeout) | schema in builtin skill docs |
| MCP | global `~/.gemini/config/mcp_config.json` (currently empty) or per-plugin `mcp_config.json`; stdio (`command`/`args`/`env`) + SSE (`serverUrl`). Legacy `~/.gemini/antigravity/mcp_config.json` carries **open-design** — which file the CLI actually reads is UNVERIFIED (both exist) | `/mcp` panel in TUI; OAuth supported (changelog 1.1.7) |
| Plugins | `.agents/plugins/<name>/plugin.json` bundling skills+rules+hooks+mcp; `agy plugin install plugin@marketplace`; **`agy plugin import gemini\|claude`** imports existing Gemini-CLI or Claude-Code customizations | none imported yet |
| TUI commands | `/model`, `/effort`, `/plan`, `/codesearch` (`/cs`), `/btw` (side-question w/o polluting thread), `/copy <n>`, `/diff`, `/settings`, `/agents`, `/mcp`; slash commands stack (`/plan /grill-me <prompt>`) | from changelog 1.1.3–1.1.7 |

Note: `~/.gemini/settings.json` (with the AIOS aios MCP server + BeforeTool/AfterTool hooks) is the
**Gemini-CLI** config — whether antigravity also reads it: UNVERIFIED; antigravity's own tree is
`~/.gemini/antigravity-cli/` + `~/.gemini/config/`.

### 3.5 Automation / headless

- `-p` prints plain text (**no JSON output mode exists** — verified absent from help). Exit 0 on
  success (verified). Machine parsing requires wrapping (see §B-2/§B-3).
- Since 1.1.5, headless honors persisted `settings.json` policies (permissions, sandbox,
  auto-execution) — changelog-verified.
- `--print-timeout` default 5m kills long jobs — always set explicitly for heavy asks
  [observed: lost output to the 5m default this week].
- `--log-file <path>` redirects CLI logs; default logs `~/.gemini/antigravity-cli/log/cli-*.log`,
  crash dumps in `crashes/`.

### 3.6 Sandboxing / permissions

- `--sandbox` (terminal restrictions), `--mode plan` (read-only planning), `--mode accept-edits`.
- The wrapper's always-on `--dangerously-skip-permissions` (top of doc) means the effective safety
  on this box comes ONLY from `--mode plan`/`--sandbox` when you pass them. For untrusted work use
  `agy.real` without the bypass.
- Workspace trust: `trustedWorkspaces` in `~/.gemini/antigravity-cli/settings.json`; untrusted cwd
  behavior in print mode UNVERIFIED.

### 3.7 Failure modes

- Print-timeout (5m default) silently truncates long runs — [observed this week]; fix: explicit
  `--print-timeout`.
- Crash logs accumulate in `~/.gemini/antigravity-cli/crashes/` (present on this box) — the CLI has
  a real crash history; wrap invocations with retry-once.
- Google OAuth is founder-only on this box (global CLAUDE.md invariant) — an expired
  `antigravity-oauth-token` is a HOLD, not something to re-auth autonomously.
- [observed 2026-07-10] some `nv panel`-adjacent model 404s and `-p`-only headless — the `-p`
  requirement still holds (verified); model list above supersedes older model memories.

---

## §A. What we are NOT using but should be (ranked)

1. **Multi-turn resumable sessions on all three** — the single biggest waste eliminated.
   - `claude`: capture `session_id` from `--output-format json`, then `claude -p -r "$sid" "…"`;
     `--fork-session` to branch; `--session-id` to pin.
   - `codex`: `codex exec --json` → `thread_id`; then `codex exec resume <id> "…" < /dev/null`
     (or `--last`). `codex fork` to branch.
   - `agy`: `agy -c -p "…"` / `agy --conversation <uuid> -p "…"`; uuid from
     `cache/last_conversations.json`.
   - Buys: iterative refinement without re-sending context, week-long standing consultations with
     one external mind (exactly the `aios_consult` pattern), cheap follow-up questions.
2. **Structured machine-parseable output** — stop scraping prose.
   - `claude -p … --output-format json --json-schema '<schema>'` → validated JSON + cost + session id.
   - `codex exec --json --output-schema shape.json -o last.txt` → JSONL events + schema-constrained
     final answer.
   - Buys: adapters/verifiers consume typed results; cost accounting for free (claude
     `total_cost_usd`); reliable failure detection (`turn.failed`).
3. **agy as a heterogeneous panel in one CLI** — `agy --model claude-opus-4-6-thinking -p …`,
   `agy --model gpt-oss-120b-medium -p …`, `agy --model gemini-3.1-pro-high -p …`.
   Buys: 3-family divergence without juggling three auth stacks; a Claude-family fallback that
   does not consume the Anthropic subscription; today's default (flash) is NOT the ceiling —
   route hard reasoning to `gemini-3.1-pro-high`.
4. **`codex --oss --local-provider ollama`** — the Codex agent harness driving local qwen3 on the
   dual-5090 box. Buys: free agentic labor with Codex's tool loop, and a codex-shaped lane that
   still works RIGHT NOW while the OpenAI quota is exhausted (until ~Aug 2). Also
   `codex sandbox <cmd>` as a standalone isolation primitive for aios_skills' sandbox-verified
   artifact induction.
5. **Plan/review lanes as first-class read-only modes** — `claude -p --permission-mode plan`,
   `agy --mode plan -p`, `codex review --uncommitted|--base main`, `claude ultrareview --json`.
   Buys: adversarial review that structurally CANNOT edit, satisfying the writer/reviewer lane
   separation without trust in prompts.
6. **Budget & failover guards on claude** — `--max-budget-usd`, `--fallback-model opus,sonnet`
   (print mode). Buys: bounded-cost unattended loops; provider-overload resilience we currently
   lack (we lost a lane to exactly this class of failure on codex).
7. **Background agents** — `claude --bg "…" ` + `claude agents --json` for dispatch/poll from
   scripts; `-w/--worktree` for isolated parallel lanes.
8. **CLI-as-MCP cross-mounting** — `codex mcp-server` and `claude mcp serve` let any agent mount
   the other CLI as a tool. Buys: a GPT-family arm inside Claude sessions (post-quota) without
   shell plumbing; complements the existing aios MCP server that all three already mount.
9. **agy custom agents + plugin import** — define `.agents/agents/<name>/agent.md`
   (frontmatter incl. per-agent `model:`), and `agy plugin import claude` to reuse the existing
   Claude skill corpus inside agy. Buys: role-shaped Gemini/Claude/GPT-OSS subagents for free.
10. **`codex features list` before assuming** — browser_use, computer_use, image_generation,
    multi_agent, personality, goals are stable-on TODAY; check the flag table instead of memory.

## §B. What is MISSING that we should BUILD

1. **Uniform cross-CLI adapter with automatic failover** — extend `scripts/aios_adapters.py`
   (the registry + injected-runner design is already there).
   Contract: `invoke(substrate, prompt, *, model=None, effort=None, session=None, json_out=False,
   timeout)` → `{text, session_id, cost_usd|None, latency_s, error_kind|None}`.
   Error taxonomy from today's verified failures: `usage_limit` (codex "hit your usage limit"),
   `provider_5xx` (`biscuit_baker_service_me_circuit_open`), `timeout` (agy print-timeout, ollama
   under load), `auth_hold` (agy OAuth = founder-only). On `usage_limit`/`provider_5xx`: retry
   once, then failover chain `codex → agy(claude-opus-4-6-thinking) → claude` (heterogeneity
   preserved). Smallest useful version: add the error classifier + one failover chain to the
   existing adapters — this alone would have saved the lane we lost.
2. **Transcript capture into the experience graph** — the MCP tool `aios_ingest_cli_session`
   already exists and `scripts/aios_experience.py` owns the Merkle-rooted run log. Missing piece:
   adapters (§B-1) appending `kind:"cli_session"` records — `{cli, session_id/thread_id/
   conversation_id, model, effort, cost_usd, latency, error_kind, resumable:true}` — parsed from
   the claude JSON envelope / codex JSONL / agy conversation cache. Smallest version: a
   `--record` flag on `aios_consult.py` that writes the ids it already has. Payoff: "a question
   asked once is never asked blind twice" becomes mechanical, and any past consultation can be
   RESUMED (not re-asked) because the session id was kept.
3. **Cost/latency ledger per substrate** — claude reports `total_cost_usd`; codex and agy report
   nothing. Build: wall-clock + (claude exact cost | codex/agy token-estimate) appended by the
   §B-1 adapter to `.aios/runs/`, aggregated by `aios_experience` queries. Smallest version:
   latency + claude-cost only. Payoff: routing by measured price/latency instead of vibes
   (CapabilityOS routing needs this signal).
4. **Cross-CLI session registry** — nothing maps a TASK to its three thread ids. Build:
   `.aios/state/cli_sessions.json` (`task_slug → {claude: sid, codex: thread, agy: conv}`)
   maintained by the adapter; `aios_consult` reads it to continue the right thread per substrate.
   Smallest version: 30 lines in the adapter. Payoff: standing multi-substrate dialogues that
   survive operator-session boundaries.
5. **Provider health/quota pre-flight** — we dispatched to a provider that was already dead.
   Build: `aios_adapters.py health()` — `codex login status` + parse last `usage limit` error and
   its stated reset time (today: 2026-08-02 04:55), agy oauth-token freshness, ollama `/api/tags`
   ping — cached in `.aios/state/provider_health.json`, consulted by route/dispatch, surfaced as a
   CapabilityOS observation. Smallest version: a dead-until timestamp per substrate, checked
   before dispatch.

---

*Verified 2026-07-27 by claude@myworld on this machine. `UNVERIFIED` and `[observed <date>]` tags
mark the exceptions. No secrets reproduced; env-var NAMES only.*
