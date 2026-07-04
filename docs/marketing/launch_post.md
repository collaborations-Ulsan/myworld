# AIOS: your agent stops starting from zero

*A longer-form announcement, safe to publish on an owned channel (repo blog,
personal blog) as-is — no external community gate. Timing: SOFT NOW per
`LAUNCH.md`, still requires founder go before actually publishing.*

---

## The problem

You run Claude Code or Codex to fix a bug. It works. Tomorrow you hit a
similar problem. The agent makes the same wrong turn, wastes the same
tokens, takes the same detour before it gets there. Nothing carried over.
Multiply that by every developer running AI agents today: an enormous
amount of execution happens, and essentially none of it teaches the next
run anything.

I've been building AIOS to close that loop — locally, transparently, and
with an actual measurement of whether the idea holds up, instead of just
shipping the feature and hoping.

## What it is

AIOS is a local-first, white-box, cross-CLI memory layer that learns *what
worked* — behavioral patterns, not facts — and tries to prove that claim
with a published, controlled eval rather than a demo GIF.

Two things it gives an agent:

**1. A behavioral ledger.** Every agent run is distilled into a behavioral
signature: what tools were used, in what order, for what kind of task. It's
stored locally in a Merkle-verified, append-only ledger — every entry is a
plain record you can read, audit, and delete. On the next similar task,
AIOS retrieves the closest match and hands the agent a short "here's what
worked" note before it starts.

**2. A composite self.** A frozen model is born amnesiac every session. The
composite self fixes that at a different layer: a portable SELF bundle
(identity + limits, human-reviewed learnings, last checkpoint) that any
agent can load at birth, and that renders the same way whether you're in
Claude Code, Codex, or any other MCP client. Nothing enters it without
explicit review — there is no silent auto-accept.

## Why local-first and white-box, specifically

Every major provider now ships some flavor of agent memory — Claude Code's
own auto-memory, Anthropic's "Dreaming" work, Codex CLI Memories, Gemini's
Memory Bank. They're all locked to one CLI and black-box: you can't see
exactly what was written, can't take it with you to a different tool, and
can't easily make the model "forget" something wrong. The generic memory
stores in this space (Mem0, Zep, Cognee, and others) solve a related but
different problem — they store *facts*, not *what worked* — and mostly ship
without a controlled eval of their own core claim.

AIOS's bet is the conjunction none of them occupy: local-first (your data
stays on your machine by default), white-box (every record is a file, not
an opaque store), cross-CLI (one ledger, one composite self, portable
across your whole agent fleet), behavioral rather than factual, and backed
by a measured eval instead of a claim. Any one of those legs alone isn't
new. Together, as of writing, nobody else ships all of them.

## The eval — including the part that didn't work

This is the part I want to lead with, not bury in an appendix.

The product's headline claim is "your agent carries forward what worked."
That's a testable claim, so I tested it. Pre-registered, one design, one
run: two arms, identical model, decoding, budget, and oracle, differing in
exactly one thing — whether the prompt was prefixed with a ledger-derived
guidance block, retrieved from a ledger seeded on a disjoint training set
(no leakage, enforced by a hermetic unit test). N=40 trials per arm, on
`phi4-mini` (3.8B).

Why a 3.8B model and not something stronger? Because I tried the stronger
default first (`qwen2.5-coder:7b`) and it was already solving almost every
task in the battery bare — no headroom left for a memory ledger to show
anything. That's a real finding in its own right: an eval is only valid
when the agent is below the task's ceiling, and I'd rather report that
calibration honestly than quietly cherry-pick a model that made the numbers
look good.

**The result was genuinely mixed**, and the mechanism is the interesting
part:

- The ledger **helped first-attempt accuracy**: pass@1 rose from 0.45 to
  0.60 (+33% relative), with fewer attempts and fewer output tokens. On the
  product's own terms, the carried-forward behavior did help the agent get
  it right sooner and more cheaply.
- The ledger **hurt retry recovery**: among trials that failed on the first
  attempt, the bare agent recovered on retry 68% of the time. With the
  ledger's guidance block still sitting in the prompt during the
  oracle-feedback retry, recovery collapsed to 19%. The always-on guidance
  competed with the concrete "expected X, got Y" error signal, anchoring the
  model on its original approach instead of letting it correct.

Net, the naive always-on version actually made final solve rate *worse*
(0.825 → 0.675). I reported that number exactly as it came out — no
post-hoc tuning of the battery or the guidance to move the gap.

The fix followed directly from the mechanism: **inject the guidance on
attempt 1 only, and drop it once oracle feedback is available.** I re-ran
the same battery with that change as a third arm. It beat the always-on
version on every axis I measured — solve rate 0.70 → 0.775, tokens down to
the cheapest of the three arms — and this is what's actually implemented
today (`aios self install-hooks` wires session-start-only injection, not an
always-on prefix).

**The honest boundary, stated plainly:** even the corrected version still
trails the bare agent on final solve rate (0.85 bare vs 0.775 corrected).
Its real, defensible win is a better and cheaper *first* attempt — not a
higher overall solve rate. I'm not aware of anyone else in this space
publishing a result this specific about their own memory feature, including
the part where it didn't beat the baseline. Full numbers:
`docs/AIOS_HEADLINE_AB_RESULTS.md` and the follow-up in
`docs/RESEARCH_GROUNDING.md`.

## Install

The primary path is a Claude Code plugin, two commands, zero setup:

```
/plugin marketplace add cjw0076/myworld
/plugin install aios@aios-claude
```

That wires a session-start hook that auto-births your composite self and
adds the AIOS MCP tools (`route`, `helper_run`, `retrieve`, `challenge`,
`observe`, plus the self tools). Nothing to install at runtime — the
plugin bundles a stdlib-only Python core.

For anyone not on Claude Code:

```
git clone https://github.com/cjw0076/myworld && cd myworld
pip install -e .
aios demo
```

`aios demo` runs the whole loop offline in about ten seconds — no API key,
no GPU required — showing an agent with empty memory, then AIOS ingesting
what it just did, then a second run getting a real suggestion grounded in
the first.

## Where this is early — honestly

- **0 external users so far.** This has been dogfooded by exactly one
  person: me.
- **The eval is small.** N=40 per arm, one 3.8B local model, 8 synthetic
  "counter-prior" coding tasks. Directional, not definitive — the numbers
  say so and so do I.
- **No fixed-advice control arm yet.** I haven't isolated "this specific
  ledger-derived guidance helped" from "any generic advice prefix would have
  helped about as much." That's the next experiment.
- **The cross-agent / shared-ledger idea is roadmap, not measured value.**
  The infrastructure for a shared behavioral ledger exists and is live, but
  there is no evidence yet that pooling across users or agents produces a
  network effect — and recent internal review actually argues *against*
  leading with that story until it's earned (governance risk, cold-start
  data sparsity, and no observed demand for cross-user pooling in the
  research so far). Today's real, measured value is single-user and local.

If any of that sounds like "not ready," I'd push back gently: I'd rather
tell you exactly what's proven and what isn't than ship a bigger-sounding
claim I can't back up. The repo has the harness, the raw numbers, and the
code for all of the above — go check it, or better, go break it.

https://github.com/cjw0076/myworld
