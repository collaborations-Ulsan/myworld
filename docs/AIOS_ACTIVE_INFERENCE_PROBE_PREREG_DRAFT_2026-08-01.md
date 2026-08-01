# Active-Inference Mini-Probe — pre-registration DRAFT (status: PROPOSED, NOT RUN)

**This is a draft for a separate founder decision. No cell may run until it is frozen.**

## Mortuary-Clause boundary (why this is not a barred retry)

The three-transport null killed *"accumulated experience compounds through an OS substrate on a
frozen model"* and bars new E-mechanisms, metrics, or task shapes for THAT claim. This probe tests
a DIFFERENT claim — **autonomy**: can a frozen model + an OS-side goal-generation loop *originate
useful work* without a human prompt? It measures discovery, not improvement-over-experience; its
result cannot resuscitate the compounding thesis and must never be reported as if it did.
(Provenance of the idea: `docs/deep-research-report (1).md` discussion + the pasted 4-gap
diagnosis, gap 4 / leap 1 — the only leap not contradicted by our existing negatives.)

## Question (falsifiable)

Does a surprise-driven goal generator find more externally-verified real defects than chance?

- **Environment**: this repository, read-only scan surface; the frozen student
  (`qwen3-coder-next`) with the Channel-E K-turn interface.
- **Generator arms** (paired over the same time budget):
  A. *surprise-driven*: rank files by prediction-failure signal (student predicts test outcomes /
  masked-line contents; largest miss = next probe target), self-schedules verification episodes.
  B. *random baseline*: same budget, uniformly random targets.
  C. *no-generator control*: zero episodes (floor).
- **Primary metric**: count of CONFIRMED findings — a finding counts ONLY if an external
  deterministic check validates it (a failing pytest reproduction the harness verifies, or a
  crash/exception reproduced in the sandbox). No self-scored findings. Anti-hack: 3-way separation
  (generator ≠ verifier ≠ scorer), verifier is pre-existing pytest/sandbox machinery.
- **Analysis**: paired count comparison A vs B over matched budgets; exact binomial on
  per-window wins; α = 0.05.
- **Kill rule (draft)**: A ≤ B over the pre-set budget ⇒ surprise-driven goal generation adds
  nothing at this scale on this substrate; report the null, do not retry with a "better" surprise
  signal (one named signal, same clause discipline as Channel-E).

## Cost bound

≤ 1 day wall-clock on the repaired local serving stack; zero cloud spend; no new infrastructure —
reuses phase5e harness + sandbox + oracles.

## Open design questions (to settle before freezing)

1. Surprise signal definition (test-outcome prediction vs masked-line perplexity) — must be fixed
   to ONE before freezing.
2. Budget unit (episodes vs wall-clock) and window size for the paired analysis.
3. Whether B (random) suffices or a third "coverage-greedy" baseline is required to claim the
   *surprise* component specifically (recommended: yes, else A>B only shows "any scheduler beats
   random").
