# Demo script — terminal recording / asciinema

> DRAFT, not recorded. This is a script for a future terminal recording
> (asciinema/GIF) to embed in the Show HN post, the launch post, and the
> README. Commands below are copied verbatim from `README.md`'s Quickstart
> and plugin-install sections — do not invent new commands or output for the
> recording; if the real CLI output differs from what's shown here, update
> this script to match the real output, not the other way around.

## Goal

Show, don't tell: 2-command plugin install → composite self born →
a real task run → the ledger carrying it forward into the next run.
Total runtime target: ~45–60 seconds of recorded terminal time.

## Recording setup notes

- Record in a clean terminal, default shell prompt, no personal path/home
  directory visible (use `~/demo/myworld` or similar).
- Use `asciinema rec aios-demo.cast` (or equivalent) at normal typing speed —
  don't speed up the parts that show real output, since the honesty framing
  depends on the output looking unedited.
- Do not overlay fake typing effects on top of doctored output. If a command
  is slow, cut the dead air in post, not the output.

## Beats

### Beat 1 — the install (narration: "two commands, no pip, no setup")

```
$ /plugin marketplace add cjw0076/myworld
$ /plugin install aios@aios-claude
```

*(Narration overlay/voiceover: "This is the whole install. No pip, no venv,
no PyPI. The plugin bundles the AIOS core and wires itself in.")*

### Beat 2 — the composite self is born (narration: "next session, your agent already has a self")

Start a new Claude Code session in the demo repo. The `SessionStart` hook
fires automatically. If narrating manually instead of relying on the hook,
show:

```
$ aios self birth
```

*(Narration: "This compiles your SELF.md — identity, your human-reviewed
learnings, and your last checkpoint. Nothing gets in without you reviewing
it first.")*

### Beat 3 — run 1: a brand-new agent, empty memory (narration: "starting from zero")

```
$ aios demo
```

Expected output (abridged, from the real `aios demo` — reproduce exactly,
do not embellish):

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

*(Narration over Run 1: "Fresh ledger, so the predictor has nothing to go
on — it says so, it doesn't guess.")*

*(Narration over the ingest line: "Now AIOS distills what the agent actually
did — tool sequence, task category — into the ledger. This is the real
ingest path, not a mocked number.")*

*(Narration over Run 2: "Same task, same question. Now there's a prior run
to draw on, and the top suggestion is grounded in exactly what just
happened — not a hard-coded answer.")*

*(Narration over the closing act: "And this is the safety idea underneath
all of it: the model proposes, deterministic code checks the answer. Wrong
answers get caught, not rubber-stamped.")*

### Beat 4 — carry the self to another substrate (narration: "portable, not locked to one CLI")

```
$ aios self carry --to codex
```

*(Narration: "Same self, rendered for a different agent CLI. This is the
cross-CLI part of the pitch — you're not locked into one provider's
memory.")*

### Beat 5 — closing card (text overlay, not spoken)

```
0 external users. N=40 eval. Read the honest negative:
docs/AIOS_HEADLINE_AB_RESULTS.md
github.com/cjw0076/myworld
```

*(This closing card is deliberate: it's the "where it's early" beat in
visual form, not narrated over, so it reads as a calm fact card rather than
an apology.)*

## What NOT to show

- Do not show the AkashicRecord public dashboard/galaxy as if it were the
  headline feature — per `LAUNCH.md`, the cross-user network effect is
  roadmap, not present value, and showing a live public dashboard risks
  implying scale that doesn't exist yet.
- Do not cut around a failed or slow command. If `aios demo` doesn't run
  cleanly on the recording machine, fix the environment before recording —
  don't edit the output.
- Do not add any spoken claim not covered by `LAUNCH.md`'s three proof
  points and honest caveats.
