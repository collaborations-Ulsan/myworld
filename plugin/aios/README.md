# aios — AIOS as a Claude Code plugin

Zero-config distribution of the AIOS organ head. Two slash commands, no `pip`,
no venv, no PyPI, no `claude mcp add`:

```
/plugin marketplace add cjw0076/myworld
/plugin install aios@aios-claude
```

## What it wires

- **`hooks/hooks.json`** — a `SessionStart` hook that runs
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/aios_agent_self.py carry --to claude --hook`.
  It auto-births the composite SELF (identity + accepted behavioral memory +
  last checkpoint) and injects it as `additionalContext` every session.
- **`.mcp.json`** — the AIOS MCP stdio server
  (`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/aios_mcp_server.py --root ${CLAUDE_PLUGIN_ROOT}`).
  Exposes `route` / `helper_run` / `retrieve` / `challenge` / `observe`, the
  discovery/invoke gateway, and the 5 self tools
  (`aios_self_status/birth/learn/checkpoint/carry`).

## Bundling

`scripts/` is a symlink to the repo's `scripts/` core. On `claude plugin install`
the plugin subtree is copied to the plugin cache and the symlink is
**dereferenced into a real directory**, so the installed plugin carries its own
stdlib-only Python copy — it never reaches back into the source repo and needs
nothing installed at runtime.

The AIOS core is stdlib-only, so bare `python3` runs it. The sibling-OS-backed
tools (`route`/`retrieve`/`challenge`) additionally use the MemoryOS /
CapabilityOS / GenesisOS packages when present; without them those tools return
a graceful error while the self tools and tool listing work fully offline.

Not a dependency of the `pip install -e .` path or the `aios` launcher — this is
an additional distribution surface.
