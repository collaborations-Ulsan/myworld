# Social preview / og-image + repo metadata

> DRAFT / notes. No external service touched to produce this file — the
> "already applied" fields below were read from the live repo via
> `gh repo view cjw0076/myworld --json description,repositoryTopics` (a
> read-only lookup, not a change) on the date this kit was authored, so the
> founder can see current state before deciding whether to update it.

## What's already applied (verified read-only, current as of authoring)

**GitHub one-line description (live):**

> AIOS — a local-first memory layer for AI agents. Your agents learn from
> every run and carry forward what worked, across Claude Code / Codex / any
> MCP client. White-box, draft-first, with published evals. Install as a
> Claude Code plugin in 2 commands.

**Topics (live):** `agent-memory`, `ai-agent`, `ai-agents`, `claude`,
`claude-code`, `developer-tools`, `llm`, `local-first`, `mcp`, `memory`.

**Homepage URL (live):** `https://aios-akashic.cjw070690.workers.dev/`

These already match the core positioning well (local-first, white-box,
cross-CLI, published evals, plugin install) — no urgent change needed. One
optional refinement to consider, in line with the 2026-07-02 revalidation's
"narrow the positioning" verdict: the description could add "cross-CLI" or
"behavioral" explicitly, since those are the two legs of the conjunction
that most differentiate AIOS from Mem0-class fact stores. Not required for
launch; a nice-to-have wording pass.

Optional topic to consider adding: `agent-evals` or `llm-eval` — the
published-eval angle is one of the three proof points and isn't reflected
in the current topic list, and topics are how people find this repo via
GitHub topic search rather than a direct link.

## Social preview / og-image concept

**Concept:** A plain, technical, no-hype card — the opposite of a glossy
SaaS launch graphic, matching the white-box/honest positioning.

- **Background:** dark terminal background (matches the README's terminal
  demo aesthetic), not a gradient/marketing-template look.
- **Primary text (large):** `AIOS`
- **Secondary text (medium):** `Local-first, white-box, cross-CLI memory
  for AI agents.`
- **Tertiary text (small, monospace, styled like a terminal output line):**
  `pass@1 0.45 → 0.60 (measured) — see the honest negative in the repo`
  This is the single most distinctive line to put on the card: it signals
  "we measure and publish, including the parts that didn't work" before
  anyone even clicks through, which is exactly the trust signal the target
  communities said is missing from this category.
- **Footer:** `github.com/cjw0076/myworld` + the two-line install snippet
  (`/plugin marketplace add cjw0076/myworld` / `/plugin install
  aios@aios-claude`) in a small monospace block, styled like a terminal.

**Explicitly avoid:** stock-photo brain/network graphics, gradient
"AI product" backgrounds, any tagline using "revolutionary," "next-gen," or
similar. The card should look like something a systems engineer made, not
something a growth team made — consistent with the "white-box, not hype"
positioning everywhere else in this kit.

**File format/size:** standard GitHub social preview constraints — 1280×640
px minimum, PNG or JPG. Not produced in this pass (no external image
generation was run for this draft); this document is the brief for
producing it, to be executed as a follow-up when the founder wants the
actual image made.
