# Show HN — draft (not posted)

> DRAFT. Do not post without explicit founder go. Timing: HARD LATER per
> `LAUNCH.md` — gated on a fixed-advice control arm and 1-2 real external
> users. Title is <80 chars.

## Title

```
Show HN: AIOS – local, white-box agent memory, with a published mixed eval
```

(74 chars. Alternate if the mods/community prefer terser: `Show HN: AIOS – a
local memory layer for AI agents, benchmarked honestly` — 71 chars.)

## Body

Hi HN. I've been building AIOS, a local-first memory layer that sits between
your agent CLI (Claude Code, Codex, any MCP client) and a behavioral ledger,
so your agent stops repeating the same mistakes every fresh session.

**The mechanism.** Every agent run gets distilled into a behavioral
signature — what tools were used, in what order, for what kind of task —
and written to a local, Merkle-verified ledger. On the next run, AIOS
retrieves the most similar past signature and injects a short "here's what
worked" guidance block into the prompt. It's local by default (no API key
needed for the base demo), white-box (every record is a plain file you can
read and delete), and cross-CLI (the same ledger and the same "composite
self" render for Claude Code, Codex, or a raw MCP client).

**The eval — including the part that didn't work.** I ran a pre-registered,
controlled A/B: identical model, decoding, budget, and oracle, differing in
exactly one thing — whether the prompt got a ledger-derived guidance block.
N=40 per arm, phi4-mini (3.8B, chosen because a stronger 7B coder model was
already at ceiling on this task battery and left no headroom to measure
anything — a real calibration finding, not spin).

Result was genuinely mixed, and the *mechanism* is the interesting part:

- The ledger **helped first-attempt accuracy**: pass@1 went 0.45 → 0.60
  (+33% relative), with fewer attempts and fewer tokens.
- The ledger **hurt retry recovery**: among trials that failed on attempt 1,
  the bare agent recovered 68% of the time on retry; with the ledger's
  guidance block still sitting in the prompt during the retry, recovery
  collapsed to 19%. The guidance was competing with the concrete
  "expected X, got Y" error signal and anchoring the model on its first
  (wrong) approach.

Net effect on final solve rate was actually *negative* (0.825 → 0.675) — I'm
reporting that straight, not laundering it. The fix was obvious once I saw
the mechanism: **inject the guidance on attempt 1 only, drop it once oracle
feedback is available.** Re-ran with that change (Arm C): it beat the
always-on version on every axis (solve rate 0.70 → 0.775, tokens down to the
cheapest of all three arms) — and it's what's actually implemented now.
Full numbers, including the honest boundary that even the corrected version
still trails the bare agent on final solve rate (0.85 vs 0.775 — its real
win is a better, cheaper first shot, not a higher solve rate), are in
`docs/AIOS_HEADLINE_AB_RESULTS.md` and `docs/RESEARCH_GROUNDING.md` in the
repo.

**Install (2 commands, in Claude Code):**

```
/plugin marketplace add cjw0076/myworld
/plugin install aios@aios-claude
```

That wires a session-start hook that auto-births a "composite self" (identity
+ your human-reviewed learnings + your last checkpoint) and adds the AIOS MCP
tools. No pip, no venv, nothing else to install — the plugin bundles a
stdlib-only Python core.

For everyone else: `pip install -e .` then `aios demo` runs the whole loop
offline, no API key, in about ten seconds.

**Where this is early, on purpose:**

- 0 external users so far — I'm the only person who's run this in anger.
- The eval is N=40, one 3.8B local model, 8 synthetic "counter-prior" coding
  tasks. Directional, not definitive.
- I haven't yet isolated "ledger-derived guidance" from "any generic advice
  prefix" — that needs a fixed-advice control arm, which is the next
  experiment I'm running.
- The cross-agent / shared-ledger idea (one agent's ledger helping a
  *different* agent, or across users) is roadmap, not measured. Current real
  ledger scale (~1,400 entries) is well short of what that would need.

Repo: https://github.com/cjw0076/myworld — feedback on the eval design
especially welcome; I'd rather find the next hole myself than have the
ledger paper over it.
