# AIOS Launch Plan (draft — not posted anywhere)

> Status: DRAFT. Nothing in `docs/marketing/` has been posted to any external
> service. All assets are ready to fire with minimal edits when the founder
> says go. Grounded in `docs/AIOS_DESIGN_REVALIDATION_2026_07.md` (community
> lane + cross-cutting findings), `docs/AIOS_HEADLINE_AB_RESULTS.md`,
> `docs/RESEARCH_GROUNDING.md`, and `README.md`. No fabricated numbers, no
> invented users, no claims beyond what those docs support.

## 1. Positioning

**One-liner** (verbatim spine, from the 2026-07-02 design revalidation, Bet ①
synthesis):

> AIOS is the local-first, white-box, cross-CLI memory layer that learns
> *what worked* — behavioral, not facts — and proves it with published evals.

Plus the second pillar the revalidation validated (Bet ⑤, "unanimous
double-down"): a portable **composite self** — identity + human-reviewed
learnings + last checkpoint — so a frozen model stops being amnesiac every
session, across Claude Code, Codex, and any MCP client.

**Emotional hook:** "Your agent stops starting from zero."

**Credibility hook (lead with this, not last):** "We measured it — pass@1
0.45→0.60 on the first attempt, but an always-on injected prefix hurt retry
recovery 68%→19%. So we inject guidance on attempt 1 only." This is the
literal honest-negative-then-fix story from
`docs/AIOS_HEADLINE_AB_RESULTS.md` + the Arm-C follow-up in
`docs/RESEARCH_GROUNDING.md`. Per the revalidation's cross-cutting finding
#1: *"the community's most-repeated demand is 'evals or it didn't happen' —
lead the product story with measured evidence."* This is the one asset every
competitor in this space is missing. Do not bury it in a FAQ — it is the
headline.

### The three proof points (use in every asset, in this order)

1. **The conjunction nobody else occupies.** Provider memory (Claude Code
   auto-memory, Anthropic "Dreaming", Codex CLI Memories, Gemini Memory Bank)
   is black-box and locked to one CLI. Generic memory stores (Mem0, Zep,
   Cognee, EverOS) store *facts*, not *what worked*, and ship no controlled
   eval. AIOS is the one that is local-first **+** white-box **+**
   cross-CLI-portable **+** behavioral **+** backed by a published controlled
   A/B. Each leg alone is not new; the conjunction is unoccupied (Bet ①
   synthesis).
2. **The honest eval, negative included.** pass@1 0.45→0.60 (+33% relative)
   first-shot; always-on injection collapsed retry recovery 68%→19%; the
   fix (attempt-1-only injection) recovered most of the loss and is what
   shipped. Even the corrected version honestly still trails bare-agent
   final solve rate (0.85 vs 0.775) — its real, defensible win is a
   better *and cheaper* first shot (pass@1 +0.07, tokens −14% vs bare),
   not a higher final solve rate. State that boundary out loud.
3. **The composite self is draft-first and white-box.** Nothing enters your
   SELF without explicit human review (`aios self accept ...`). It renders
   for any substrate (`aios self carry --to codex`). This is the DNA moat
   (Bet ⑤) provider memory does not offer.

### The honest caveats (state in every asset, never hide)

- **0 external users today.** This has not been dogfooded by anyone outside
  the founder yet.
- **The eval is N=40 per arm, one 3.8B local model (phi4-mini), 8 synthetic
  "counter-prior" coding tasks.** Directional, not definitive — the docs say
  so explicitly, and so do we.
- **A stronger model (qwen2.5-coder:7b) was *above the ceiling* for this
  battery** — bare pass@1 was already ~6/6, leaving no headroom for the
  ledger to show anything. This is a real calibration finding, not spin:
  it means we don't yet know whether the effect holds on stronger models or
  harder tasks.
- **No fixed-advice control arm yet** — we have not isolated "ledger-derived
  guidance" from "any generic advice prefix." That is an open item, stated
  as such in `docs/RESEARCH_GROUNDING.md`.
- **The cross-agent / shared-ledger network effect is roadmap, not present
  value.** Today's value is single-user, local. (The 2026-07-02 revalidation
  explicitly recommends retiring the public-pool headline — see the DO NOT
  list below.)

## 2. Channel-by-channel plan

Each row cites the specific community-culture finding from
`docs/AIOS_DESIGN_REVALIDATION_2026_07.md` that the framing is built on.

### Show HN
- **Framing:** Technical + eval + caveat. Lead with the mechanism (behavioral
  signature → ledger → attempt-1-only injection), then the numbers, then
  "where it's early." No hype adjectives.
- **Why this framing:** HN's loudest, most-repeated demand across the
  community lane is *"evals or it didn't happen"* / *"memory arena"* /
  *"no benchmarks = FOMO"* (cross-cutting finding #1). A post that leads with
  a controlled A/B *including the honest negative* is exactly the wedge the
  revalidation identifies as unoccupied.
- **Asset:** `show_hn.md`.

### r/LocalLLaMA
- **Framing:** Local-first, white-box, anti-cloud. No API key required for
  the base demo (`aios demo` runs offline). Ollama-native for the local
  provider path.
- **Why this framing:** Bet ① community lane: *"local-first distrust of
  cloud memory is strong in the CLI-power-user segment."* This sub punishes
  anything that reads as "another cloud memory SaaS" and rewards
  self-hostable, inspectable, offline-capable tools with real numbers
  attached.
- **Asset:** `reddit_localllama.md`.

### r/ClaudeAI
- **Framing:** The 2-command Claude Code plugin install, the composite self,
  and an honest comparison to Claude Code's own built-in auto-memory /
  Anthropic "Dreaming" — positioned as complementary (white-box, portable to
  Codex too), not "better than Anthropic's own feature."
- **Why this framing:** This audience already has Claude Code auto-memory;
  claiming to replace it would read as competing with the platform they're
  loyal to. Differentiate on portability + white-box review, not on beating
  a shipped first-party feature.
- **Asset:** `reddit_claudeai.md`.

### r/AI_Agents
- **Framing:** Agent builders who are eval-literate and explicitly skeptical
  of prompt-only claims (see `docs/research/AIOS_GITHUB_REDDIT_ALIGNMENT_MINING_2026-05-20.md`
  Reddit Signal 1: "are most LLM eval tools still too prompt-focused?").
  Lead with the behavioral-signature mechanism and the workflow-level A/B,
  not a prompt template. No dedicated post file drafted yet (not in this
  kit's file list) — same core assets (`show_hn.md` body, adapted) can seed
  it when this channel's turn comes.
- **Why this framing:** this audience explicitly distrusts single-prompt
  evals; a workflow-level, attempt-aware A/B is credible here specifically
  because it is *not* a prompt score.

### X/Twitter thread
- **Framing:** Hook → problem → mechanism → the honest eval → 2-command
  install → caveats → CTA. Build-in-public tone; the honest-negative beat is
  itself a strong retweet-driver in this audience (a builder admitting a
  measured failure and showing the fix reads as credible, not weak).
- **Asset:** `x_thread.md`.

### MCP registry listing
- **Framing:** Passive discovery, not a push post. Keep the listing
  description factual and matched to the README (local-first, white-box,
  cross-CLI, published eval) — no urgency language, no "join the network."
- **Why:** distribution via a zero-config install channel is the identified
  gap (cross-cutting finding #2: "every winner won via a zero-config
  channel"). The MCP registry entry is discoverability infrastructure, not a
  community post — it should already say what's true and stay that way.

### Claude Code plugin marketplace discovery
- **Framing:** Same as above — ensure the plugin manifest/description
  matches the 2-command install story in the README exactly. This is the
  "shortest path to install-to-value" the revalidation calls out; get the
  metadata right once rather than campaign it.

## 3. Timing — soft now vs. hard later

**SOFT NOW** (owned channels, no community judgment gate, reversible,
assets-ready signals only):
- Publish `launch_post.md` on the owned blog/repo channel — no external gate,
  safe to ship as-is.
- Confirm the MCP registry listing and Claude Code plugin marketplace
  metadata are accurate and discoverable (passive; not a "launch").
- Post the `x_thread.md` thread on the founder's own X account whenever
  ready — it's an owned channel, not a one-shot community gate the way a
  subreddit or Show HN post is.
- Keep all assets current as the eval and user count change.

**HARD LATER** (Show HN + r/LocalLLaMA + r/ClaudeAI + r/AI_Agents pushes),
gated on:
1. **The eval is strengthened** — at minimum, run the fixed-advice control
   arm (`docs/RESEARCH_GROUNDING.md` open item #2) so the claim "this is
   ledger-derived, not just any advice prefix" is defensible under
   HN/Reddit-grade scrutiny. Ideally also one non-synthetic or
   stronger-model replication.
2. **1–2 real users exist** outside the founder — even a single external
   dogfooder who confirms the install works and the demo runs as described
   materially changes how "0 external users" reads in a thread.

**Why premature hard-launch burns the one shot:** Show HN and these
subreddits are single-shot reputational surfaces — a post that reads as
"another memory project, no real users, thin eval" gets buried or
downvoted, and the same title/story cannot be re-posted later without
looking like spam. The revalidation's community lane is explicit that this
exact profile ("another memory layer, no benchmarks") is what gets punished.
Soft-launching first (owned channels + passive discovery) lets us fix the
two gated items above without spending the one hard-launch attempt on a
weaker version of the story we can tell in a few weeks.

## 4. DO NOT

- Do NOT post any of these assets to any external service without explicit
  founder go — everything here is a draft.
- Do NOT fabricate engagement, users, testimonials, or upvotes.
- Do NOT cross-post the identical text to multiple subreddits on the same
  day — each asset is tailored to its sub's culture on purpose; reusing one
  verbatim elsewhere reads as spam and defeats that tailoring.
- Do NOT lead with hype words ("revolutionary," "game-changing," "10x",
  "the future of memory"). Lead with the mechanism and the numbers.
- Do NOT claim the cross-agent / shared-ledger network effect as present
  value. It is roadmap. The 2026-07-02 revalidation explicitly recommends
  retiring the public-pool headline (Bet ④: "kill as product thesis, park as
  research lane, pivot the sharing story to team-scope") — do not resurrect
  it as a marketing hook.
- Do NOT hide or soften the retry-recovery negative (68%→19%) or the "0
  external users" / "N=40, one 3.8B model" caveats. They are the trust
  signal, not a liability to bury.
- Do NOT claim benchmark results beyond what `docs/AIOS_HEADLINE_AB_RESULTS.md`
  and the Arm-C follow-up in `docs/RESEARCH_GROUNDING.md` actually show.
