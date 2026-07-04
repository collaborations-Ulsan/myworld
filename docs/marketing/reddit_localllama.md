# r/LocalLLaMA post — draft (not posted)

> DRAFT. Do not post without explicit founder go. Timing: HARD LATER per
> `LAUNCH.md`. Framing: local-first, white-box, anti-cloud — this sub's
> loudest signal (per `docs/AIOS_DESIGN_REVALIDATION_2026_07.md`, Bet ①) is
> distrust of cloud memory + "evals or it didn't happen."

## Suggested title

```
AIOS: a local, white-box memory layer for agents — with a published A/B
(including the part that didn't work)
```

## Body

Posting here because this sub is exactly the audience that (rightly) doesn't
trust "cloud memory for your agent" and wants numbers, not a landing page.

**What it is.** AIOS runs entirely locally by default. It watches what an
agent CLI (Claude Code, Codex, or anything speaking MCP) actually did on a
task — which tools, in what order — and writes that as a plain-text,
Merkle-verified record on your own disk. Next similar task, it retrieves the
closest past record and hands the agent a short "here's what worked" note.
No cloud dependency for the core loop; `aios demo` runs offline, no API key.

**Why white-box matters here specifically.** Every record is a file you can
open, diff, and delete. Nothing enters your "composite self" (the
identity + learnings + checkpoint bundle that carries across sessions)
without you explicitly reviewing and accepting it — there's no silent
auto-write. If you want to run the local-model path end to end, it's plain
Ollama underneath (`aios setup apply` pulls a small model); nothing about
the design assumes a hosted provider.

**The eval, honestly.** I ran a controlled A/B (same model/decoding/budget/
oracle, one variable: ledger guidance on or off), N=40 per arm, on
`phi4-mini` (3.8B). I originally tried `qwen2.5-coder:7b` as the default and
had to drop down — that model was already solving ~6/6 bare on this task
battery, so there was no headroom left for a memory ledger to show anything.
Worth knowing if you're benchmarking your own local setups: model-vs-task
ceiling matters more than people give it credit for.

Results on phi4-mini: the ledger raised first-attempt accuracy (pass@1
0.45→0.60) but an always-on guidance prefix wrecked retry recovery
(68%→19%, because it competed with the concrete oracle error during the
retry). Net solve rate actually went *down* with the naive always-on
version. Fix: inject the guidance on attempt 1 only, drop it once there's
real feedback to react to — that's what's shipped now, and it recovers most
(not all) of the loss. Full numbers and the honest boundary (the corrected
version still trails a bare agent on final solve rate — its real win is a
cheaper, better first attempt, not a higher solve rate) are in the repo:
`docs/AIOS_HEADLINE_AB_RESULTS.md`, `docs/RESEARCH_GROUNDING.md`.

**Where it's early:** N=40, one 3.8B model, 8 synthetic tasks — directional,
not definitive. No external users yet besides me. If anyone here wants to
run the harness against their own local model (it's one env var,
`AIOS_AB_MODEL`), I'd genuinely like the data point.

Repo: https://github.com/cjw0076/myworld
