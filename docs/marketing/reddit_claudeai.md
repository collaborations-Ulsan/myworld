# r/ClaudeAI post — draft (not posted)

> DRAFT. Do not post without explicit founder go. Timing: HARD LATER per
> `LAUNCH.md`. Framing: Claude Code plugin install + composite self, honest
> comparison to Claude Code's own auto-memory — complementary, not
> "better than Anthropic's feature" (per `docs/AIOS_DESIGN_REVALIDATION_2026_07.md`,
> Bet ① landscape note: Anthropic already ships "Dreaming" / auto-memory).

## Suggested title

```
Built a Claude Code plugin that gives your agent a portable "composite
self" across sessions (and honestly compared it to Claude's own
auto-memory)
```

## Body

I use Claude Code daily and got tired of every session starting from zero
on problems I'd already solved a version of last week. Built AIOS to fix
that for myself, figured I'd share since it's now a 2-command plugin
install.

**Install:**

```
/plugin marketplace add cjw0076/myworld
/plugin install aios@aios-claude
```

That's it — no pip, no venv, nothing else to set up. It wires a
`SessionStart` hook that auto-births your "composite self" (identity + your
human-reviewed learnings + your last checkpoint) and injects it as session
context, plus adds a small MCP tool set (`route`, `retrieve`, `challenge`,
`observe`, and the self tools).

**How this is different from Claude Code's own memory.** Claude Code
already has auto-memory, and Anthropic's own "Dreaming" work (agents
reviewing their own sessions and writing playbooks) is close to this idea —
credit where due, it's a good idea and they shipped it natively. What AIOS
adds on top:

- **Portable.** The same "composite self" renders for Codex or any other MCP
  client too (`aios self carry --to codex`), not locked to one CLI.
- **White-box.** It's a plain markdown/JSON file you can read, diff, and
  delete — not a black box you have to trust.
- **Draft-first.** Nothing enters your self without explicit review
  (`aios self accept <id> --reviewer ... --note ...`) — no silent
  auto-accept.
- **Measured, not assumed.** I actually ran a controlled A/B to check
  whether the "carry forward what worked" idea holds up (see below), instead
  of shipping the feature and hoping.

**The honest eval.** N=40 per arm, phi4-mini (3.8B) — a controlled test of
whether injecting ledger guidance measurably helps. It's mixed, and I'm not
going to pretend otherwise: it raised first-attempt accuracy (pass@1
0.45→0.60) but an always-on guidance prefix hurt retry recovery
(68%→19%) because it competed with the concrete error message during a
retry. Fix — inject guidance on attempt 1 only, drop it on retry — is what's
actually shipped, and it's what `install-hooks` wires up. Even the fixed
version is honest about its limits: it still trails a bare agent on final
solve rate; its real, measured win is a cheaper and more-often-right first
attempt. Details: `docs/AIOS_HEADLINE_AB_RESULTS.md` in the repo.

**Where it's early:** this is a one-person project so far, 0 external users
before this post, small eval (N=40, one small local model, synthetic
tasks). If you try the plugin and it breaks or the demo output doesn't match
the README, please tell me — that's exactly the feedback that gets it out
of "just works for me."

Repo: https://github.com/cjw0076/myworld
