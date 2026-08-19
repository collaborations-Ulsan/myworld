# Harness construction + failure introspection — absorbed from ECC (2026-08-16)

Source: [affaan-m/ECC](https://github.com/affaan-m/ECC) skills `agent-harness-construction` and
`agent-introspection-debugging`, MIT. **ECC is not installed** — see the verdict at the bottom for
why. These two documents are the only parts of its 285-skill surface that were judged load-bearing
for AIOS and absent from our stack, so they are absorbed as text, adapted, and attributed here.

Why these two: AIOS already owns *who* executes (HiveMind), *what is remembered* (MemoryOS), and
*what is recommended* (CapabilityOS). What it has never written down is **how a tool surface should
be shaped so an agent can actually succeed on it**, and **what to do the moment a run fails**. The
DNA invariant "stop conditions named — no silent failure" states the requirement; neither of those
was a procedure until now.

---

## 1. Harness construction — designing an action space

Completion quality is bounded by four things, and only four: **action space, observation, recovery,
context budget.** A weak model on a well-shaped surface beats a strong model on a bad one.

### Action space

- Stable, explicit tool names. Renaming a tool invalidates every learned habit.
- Schema-first, narrow inputs. A `dict` parameter is an untyped escape hatch.
- Deterministic output shapes — the same call shape returns the same field set, always.
- No catch-all tools unless isolation is genuinely impossible.

**Granularity by risk, not by convenience:**

| Tool size | Use for | Why |
|---|---|---|
| micro | deploy, migration, permission change | each step individually refusable and auditable |
| medium | the ordinary read / search / edit loop | matches how work actually decomposes |
| macro | only when round-trip overhead dominates | collapses the surface an operator can veto |

This maps directly onto AIOS's own boundaries: CapabilityOS **recommends** and must therefore stay
micro/medium so a recommendation is inspectable; HiveMind **executes** and may hold macro tools
because it produces receipts.

### Observation format

Every tool response should carry:

- `status`: `success | warning | error`
- `summary`: one line, the result itself, not a restatement of the request
- `next_actions`: what can be done now
- `artifacts`: paths / IDs, so the next call references instead of re-reads

### Error recovery contract

Every error path owes the caller three things: a **root-cause hint**, a **safe retry instruction**,
and an **explicit stop condition**. An error that says only what failed forces the agent to guess,
and a guessing agent retries.

> AIOS note: this is the missing operational half of DNA invariant 4 ("stop conditions named").
> The invariant says a stop condition must exist; this says it must be *carried in the error
> payload*, where the agent will actually read it.

### Context budgeting

1. Keep the system prompt minimal and invariant.
2. Large guidance belongs in on-demand skills, not the prompt.
3. Reference files; do not inline long documents.
4. Compact at **phase boundaries**, not at arbitrary token thresholds.

### Anti-patterns

Overlapping tool semantics · opaque output with no recovery hint · error-only output with no next
step · context stuffed with references nothing will use.

### Benchmarks worth tracking

completion rate · retries per task · pass@1 and pass@3 · **cost per successful task** (not cost per
call — a cheap call that fails is not cheap).

---

## 2. Failure introspection — four phases before a retry

The rule this encodes: **a blind retry destroys the evidence that would have explained the
failure.** Capture first.

### Phase 1 — capture

```markdown
## Failure Capture
- Session / task:
- Goal in progress:
- Error:
- Last successful step:
- Last failed tool / command:
- Repeated pattern seen:
- Environment assumptions to verify:
```

### Phase 2 — diagnose against known patterns

| Pattern | Likely cause | Check |
|---|---|---|
| max tool calls / same command repeating | loop with no exit path | inspect the last N calls for repetition |
| degraded reasoning, context growth | unbounded notes, duplicated plans, pasted logs | look for duplication and low-signal bulk |
| `ECONNREFUSED` / timeout | service down or wrong port | verify health, URL, port assumptions |
| `429` / quota | retry storm, missing backoff | count calls, inspect retry spacing |
| file missing after write / stale diff | wrong cwd, branch drift, race | re-check path, cwd, `git status`, real existence |
| tests still failing after the "fix" | wrong hypothesis | isolate one failing test, re-derive the bug |

Four questions: is this **logic / state / environment / policy**? Did the agent lose the real
objective and start optimizing a subtask? Is it deterministic or transient? What is the smallest
reversible action that would validate the diagnosis?

### Phase 3 — contained recovery

Smallest action that changes the *diagnosis surface*: stop retrying and restate the hypothesis ·
trim context to goal + blockers + evidence · re-check actual filesystem / branch / process state ·
narrow to one command, one file, one test · **switch from speculative reasoning to direct
observation** · escalate when high-risk or externally blocked.

### Phase 4 — introspection report

The written diagnosis is the artifact. It is what makes the failure reusable instead of repeated.

---

## What was deliberately NOT absorbed

- **`agent-self-evaluation`** — the agent self-rates its own output on five axes. This is exactly
  the shape the 2026-07-17 founder directive forbids: a loop that generates its own task, writes
  its own verifier, and scores itself is "a self-ratifying benchmark optimizer, not intelligence."
  Self-scoring may be an input to a human/heterogeneous review; it may never be the gate.
- **`autonomous-loops`** — 611 lines, and its own header says "retained for compatibility only."
- **`benchmark-methodology`** — despite the name it scores marketing positioning, voice, and
  visual craft. Not a benchmark methodology in our sense.
- **ECC's `council`** — four same-model voices (Skeptic / Pragmatist / Critic subagents). Our
  measured ceiling says same-family panels add **+0.047** over cross-family and heterogeneous
  panels are worth ≈2 effective votes; a same-weights panel is the fake de-biasing our rules name
  explicitly. Installing it would have shadowed `council/hub.py`, which reaches six real external
  substrates, with a strictly weaker tool of the same name.

## Why ECC is not installed (measured 2026-08-16)

240,311★, MIT, actively maintained — a good project, wrong fit for this stack.

- **~25,305 tokens** of always-loaded skill descriptions for 285 skills (our whole current surface
  is ~7,100 after pruning).
- Hooks fire **6 node processes per Bash call (~150ms)**, 8 per Edit, 4 per Read, 7 on Stop.
- 50 of 285 skills target frameworks this workspace does not use.
- `ecc-agentshield` (its security scanner, separately installable): on `~/.claude` it produced 75
  findings / grade D, but the distinctive HIGHs were substring false positives — "Encoded payload
  detected" on the string `Backward compatibility`, "skill tampering" on `skip verification`,
  "suspicious instruction in comment" on `<!-- OMC:START -->`. Pointed at `council/` — the
  directory that actually holds credentials — it scanned **0 files and returned grade A/100**. A
  silent all-clear is worse than a false positive.

Treat the repo as a **quarry, not a dependency**: read it, take what is load-bearing, install
nothing.
