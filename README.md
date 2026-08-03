# AIOS

[![tests](https://github.com/cjw0076/myworld/actions/workflows/tests.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/tests.yml)
[![docker](https://github.com/cjw0076/myworld/actions/workflows/docker.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/docker.yml)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/cjw0076/myworld)

**Your work survives the agent.**

Your agent dies — context reset, crashed process, exhausted session — and the work dies with it. AIOS is a sovereign sidecar that keeps the *work* alive: a tamper-evident ledger of what you were doing, so any agent (the same one tomorrow, a different CLI, a local model) can pick it up from the record alone and prove it took over faithfully.

> **What this README used to claim, and why it changed (2026-08).** Earlier versions said AIOS makes your agents "learn from every run" and get "smarter" from accumulated memory. We ran the experiment on ourselves — pre-registered, externally graded, three separate ways — and **it was not true**: injecting accumulated experience into a frozen model did not improve its task performance (overall effect **0.000**; a promising +13pp at n=90 *reversed* to −0.3pp at n=300). We publish the null rather than keep selling it: [`docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md`](docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md). What survived that audit is what this README now claims — and nothing more.

---

## The problem

You run Claude Code or Codex on a long task. Halfway through, the context resets, the process dies, or the session ends. The agent does not know what it was doing, what it already ruled out, or what constraint it was under. **You re-explain everything, or you start over.**

Nothing today owns the *work* — every tool owns a *session*.

---

## What AIOS does

**1. Keeps the work, not the chat** — Each unit of work is an **arc**: an append-only event log (goal, constraints, the external check that decides "done", every step with its evidence). The log is the state; the agent is disposable.

**2. Resumes from the record, freshness-gated** — A new agent gets a resume pack carrying its causal position. If the arc moved since the pack was read, the takeover is **refused** until it re-syncs — a checkpoint that loads is not the same thing as a state that is current.

**3. Reclaims orphaned work** — When the owner's process dies, its lease is void immediately (liveness is derived, never taken on trust) and a watchdog hands the arc to whatever substrate is alive — local model, Codex, Claude.

**4. Verifies the handoff** — A separate verifier judges the takeover by what the new agent **did** against the arc's goal and constraints, and by the arc's own external oracle — never by a checksum on the handoff packet. An unverifiable takeover is reported as unverifiable, never as success.

Everything runs locally, in an OS-enforced sandbox with no network by default and your private directories invisible to executed code.

---

## Quickstart

```sh
# No GPU, no API key needed for the first demo:
git clone https://github.com/cjw0076/myworld && cd myworld
pip install -e .
aios demo
```

Output (abridged):

```
  ── Run 1 — a brand-new agent, empty memory ───────────────────
    predictor: no_data  (0 prior runs)
    → no prior runs — starting from zero.

  ── AIOS records what the agent just did ──────────────────────
    ingested 1 run → ledger   (what worked: Read, Edit, Bash, Grep)

  ── Run 2 — same task, same question, now WITH memory ─────────
    → top suggestion: Edit   (grounded in the run recorded moments ago)

  ── Closing act — AI proposes, code verifies ──────────────────
    Checker says: PASS ✓  (3 courses scheduled, no deadline violated)
    Checker says: CAUGHT ✗ — the AI scheduled work after the deadline
```

Act one shows the ledger machinery end to end — ingest, retrieve, provenance — offline and deterministic. Read it as *"the record works"*, **not** as *"the agent got better"*: we measured the latter and it did not hold (see the null report above). Act two is the part that survived the audit: AI proposes, deterministic code verifies, wrong answers are rejected, and every run leaves a provenance record.

For the machinery this README actually claims, the arc CLI is the shortest demo:

```sh
aios-society open --goal "fix the retry bug" --oracle "pytest -q tests/test_retry.py"
aios-society claim --arc <id> --agent me@laptop        # take ownership (leased)
aios-society note  --arc <id> --agent me@laptop --text "reproduced" --evidence commit:abc123
# ... your agent dies here ...
aios-society list --orphans                            # the work is still there, unowned
aios-society pack  --arc <id>                          # what a new agent needs, + its causal position
```

---

## Install as a Claude Code plugin (2 commands, zero setup)

The primary zero-config path. No `pip`, no venv, no PyPI, no `claude mcp add` — the plugin bundles the AIOS core (stdlib-only Python 3) and wires everything itself:

```
/plugin marketplace add cjw0076/myworld
/plugin install aios@aios-claude
```

That's the whole install. You get, on the next session:

- **Composite self on every session** — a `SessionStart` hook auto-births your SELF (identity + accepted learnings + last checkpoint) and injects it as session context, so a new session opens knowing **what it committed to and where it left off**. (Continuity of commitment — not a performance claim: see the null report.)
- **The AIOS MCP server** — `route` / `helper_run` / `retrieve` / `challenge` / `observe` plus the 5 self tools (`aios_self_status/birth/learn/checkpoint/carry`) show up in your tool list.

Everything runs from the plugin's own bundled copy via `${CLAUDE_PLUGIN_ROOT}` and bare `python3` — nothing to install at runtime. (The marketplace becomes live once this repo is pushed to `cjw0076/myworld`; until then, add it from a local clone with `/plugin marketplace add /path/to/myworld`.)

`pip install -e .` (below / Quickstart) remains the fallback for non-plugin users, and `uvx --from aios-os aios-mcp` is the documented PyPI alternative for the MCP server alone.

---

## Your agent, continuous — the composite self

A frozen model is born amnesiac every session. The **composite self** carries the part that does not need the model to change: a portable, white-box SELF any agent loads at birth — identity + measured limits, human-reviewed learnings, and the last checkpoint (where you left off) — across sessions *and* substrates (Claude Code / Codex / any MCP client). It makes a new session **accountable to what the last one committed to**; it does not make the model better at the task.

```sh
aios self birth            # compile your SELF.md (identity + accepted learnings + last checkpoint)
aios self install-hooks    # zero-config: wire Claude Code to auto-birth the self every session
aios self carry --to codex # render the same self for another substrate (Codex / system prompt / json)
```

Draft-first and honest: nothing enters the self without your explicit review (`aios self accept <id> --reviewer ... --note ...`), and injection happens at session-start only — measured, because mid-retry re-injection collapses recovery 68%->19%.

---

## AkashicRecord — live behavioral ledger

The global memory layer is live and public. No sign-up required.

```
https://aios-akashic.cjw070690.workers.dev/
```

**Dashboard** — real-time entry counts by category, provider, OS origin, Merkle root.

**Memory Galaxy** — 3D force-directed graph of behavioral similarity. Nodes are agent sessions, edges are semantic similarity. Categories glow when you type a context.

```
https://aios-akashic.cjw070690.workers.dev/galaxy
```

**Prediction API** — open endpoint:

```sh
curl -X POST https://aios-akashic.cjw070690.workers.dev/predict \
  -H "Content-Type: application/json" \
  -d '{"context": "running tests, got import error, need to fix the module", "top_k": 3}'
```

```json
{
  "predictions": [
    { "tool": "Bash",  "score": 0.54 },
    { "tool": "Edit",  "score": 0.31 },
    { "tool": "Read",  "score": 0.15 }
  ],
  "n_similar": 30
}
```

> The keyless free tier is small (10 requests/day, shared per IP) — if you get a
> `402 free tier exhausted`, register a free API key and pass it as `X-AIOS-Key`:
>
> ```sh
> curl -X POST https://aios-akashic.cjw070690.workers.dev/register
> ```

**Merkle verification** — every entry is content-addressed and provable:

```sh
curl https://aios-akashic.cjw070690.workers.dev/root
curl https://aios-akashic.cjw070690.workers.dev/proof/<entry-id>
```

---

## Full install — with live providers

```sh
# One command: clones repos + installs + wires into your agent CLIs
curl -fsSL https://raw.githubusercontent.com/cjw0076/myworld/main/install.sh | sh

# Provision a local model (no API cost):
aios setup apply        # pulls qwen3:1.7b via Ollama

# Start the chat UI:
aios serve              # → http://localhost:8741/
```

### Provider options

AIOS auto-selects the best available provider:

| Provider | Setup | Cost |
|----------|-------|------|
| Ollama (local) | `aios setup apply` | Free |
| Gemini REST | `GEMINI_API_KEY=...` | Free tier (1500 req/day) |
| Anthropic Claude | `ANTHROPIC_API_KEY=...` | Pay-per-token |

In GitHub Codespaces: add your key under **Settings → Codespaces → Secrets**.

---

## Contribute your agent sessions

The shared ledger is an **audit and provenance** substrate, not a performance one — contributing does not make anyone's agent better (we measured that; it did not hold). What it does give is a public, Merkle-verified record of how agents actually behave:

```sh
# Opt-in: send your local behavioral patterns (tool names only, no content)
aios behavior contribute --opt-in code,docs
```

**Privacy guarantee:** only structural metadata is stored — tool names, sequence, category. No prompts, no outputs, no file contents. Verified by the Worker's privacy gate before any entry reaches D1. Contributions are **public and pseudonymous**: entries land in the shared ledger under a one-way salted pseudonym (your API key is never stored). The worker is additionally designed to enforce a k-anonymity floor (sparse rows served only once enough distinct contributors back them) — rolling out with the next worker deploy.

---

## Build on AIOS

AIOS has four small, self-contained extension seams — provider adapters, domain
minds, capability cards, and behavioral memory. Run `aios onboard`: its
`absorbed_not_executable` list is a live good-first-issue backlog (write the
`cursor` adapter in ~5 lines and watch it move to `verified_ready`).

→ **[docs/BUILD_ON_AIOS.md](docs/BUILD_ON_AIOS.md)** — the contributor guide.

---

## Architecture (for developers)

```
Your agent CLI (Claude Code / Codex / local LLM)
        ↓
   aios_head.py  ←── memory retrieval, capability routing, doom-loop guard
        ↓
   aios_turn_loop.py  ←── event log, session record, tool dispatch
        ↓
   AkashicRecord (Cloudflare Worker + D1)  ←── global behavioral ledger
        ↓
   /predict  /graph  /proof  /checkpoints  ←── open API
```

Five OS modules, each owning a distinct authority layer:

| Module | Role | Availability |
|--------|------|--------------|
| **myworld** | Contracts, dispatch, operator kernel | public (this repo) |
| **hivemind** | Execution harness, verification, run receipts | public |
| **memoryOS** | Append-only memory graph, provenance, retrieval | private research repo |
| **CapabilityOS** | Tool/API routing recommendations | private research repo |
| **GenesisOS** | Assumption mutation, cross-domain reasoning | private research repo |

The OSS core in this repo is **self-contained**: the behavioral ledger, demo, and
`aios` CLI run without the private modules (they add the deeper memory graph and
routing research, and are being opened progressively).

---

## Docker

```sh
docker run --rm -e GEMINI_API_KEY=your_key -p 8741:8741 \
  ghcr.io/cjw0076/myworld:latest aios serve --host 0.0.0.0
```

---

## Current state

The ledger has **~1,400 behavioral entries** from real agent sessions, and the Akashic infrastructure is production-grade (Cloudflare Workers + D1, Merkle-verified, globally distributed).

**Retracted claim (2026-08):** this section used to say *"prediction accuracy improves with scale — the network effect becomes visible above 10,000 entries."* Our own measurement points the other way: a +13pp effect at n=90 became **−0.3pp at n=300**. More entries did not help; the small-n result was a mirage. We do not claim a data network effect, and we will not claim one again without a pre-registered test that survives.

Precise status: the arc/continuity layer is implemented and tested (open → claim → resume → orphan reclaim → verified handoff, with a live end-to-end reclaim in **19.95s**). Whether an agent *society* beats a single agent with the same ledger is **not yet known** — that experiment is frozen and unrun ([`docs/AIOS_G5_SOCIETY_PREREG_2026-08-03.md`](docs/AIOS_G5_SOCIETY_PREREG_2026-08-03.md)), and its kill rule can retire the society layer entirely. See [`docs/AIOS_CANONICAL_SHAPE.md`](docs/AIOS_CANONICAL_SHAPE.md) for vocabulary.

**Not to be confused with** arXiv:2403.16971 "AIOS: LLM Agent Operating System" — an unrelated project with the same name.

---

## Learn more

- [docs/RESEARCH_GROUNDING.md](docs/RESEARCH_GROUNDING.md) — the research spine: which design decisions come from which papers, and what our own experiments (including the negatives) showed
- [`docs/AIOS_MINIMUM_KERNEL_AUDIT.md`](docs/AIOS_MINIMUM_KERNEL_AUDIT.md) — what the kernel actually does
- [`docs/AIOS_CANONICAL_SHAPE.md`](docs/AIOS_CANONICAL_SHAPE.md) — what "AIOS", "complete", "production", and "service" mean
- [`docs/AIOS_AKASHIC_DISTRIBUTED_DESIGN.md`](docs/AIOS_AKASHIC_DISTRIBUTED_DESIGN.md) — ledger design and roadmap
- [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) — operator entry points
