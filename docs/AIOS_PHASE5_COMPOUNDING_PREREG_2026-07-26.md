# Phase 5 — Does the assembled organism COMPOUND? (pre-registration, 2026-07-26)

**FROZEN BEFORE ANY ARM IS RUN.** Amendments go in an append-only Errata at the bottom, never by
editing above it. Written by claude@myworld; protocol adopted from the heterogeneous consultation
`docs/consultations/*-agy-design-the-decisive-experiment*.md` (operator verdict included there).

## 0. The question, stated so it can lose

The program pivoted from "compound in the model's weights" (five well-powered NULLs) to **"compound in
the OS"**: verified skills + an experience graph + a drive, with the model ephemeral and frozen. That
claim has never been tested. This experiment tests exactly it, and is designed so that the most likely
outcome — *no compounding* — is reportable as a clean negative rather than as ambiguity.

**H1 (pre-registered):** with the student model FROZEN and identical in both arms, an agent that carries
a persistent verified-experience/skill substrate solves **more first-attempt, autonomously verified
tasks** than the same agent whose substrate is wiped between tasks — and the advantage **grows across
sequential epochs**.

## 1. Primary metric (chosen for un-gameability)

**`P_auto` = first-attempt autonomous resolution rate under an EXTERNAL deterministic oracle, with
escalations = 0.**
- *External oracle*: the repository's own pre-existing pytest file for the target module, executed
  **outside** the agent's sandbox, after the agent has finished. The agent never runs the grading command
  and cannot edit the test file (enforced: test files are read-only to the task, and any diff touching
  `tests/` invalidates the task attempt → scored fail).
- *First-attempt*: one autonomous episode per task; no human turn, no retry loop across episodes.
- *escalations = 0*: provider escalation is DISABLED in both arms, so a win cannot come from a stronger
  model. This isolates OS-substrate effects from model capability.
- Rejected alternatives (all gameable, kept only as diagnostics): skill-reuse rate (gamed by trivial
  wrapper skills), escalation-rate decline (gamed by failing silently), steps/time-to-completion (gamed by
  skipping validation), token cost (gamed by giving up early).

**Compounding statistic:** `C_k = P_auto(Treatment, epoch k) − P_auto(Control, epoch k)`.
H1 requires (a) `C_k > 0` overall and (b) a positive slope of `C_k` over `k` — a level difference alone
is *not* compounding, it is a one-off prompt advantage.

## 2. Task stream (real, offline, and uncontaminated)

Tasks are constructed from **this private repository's own git history** — chosen deliberately: a private
repo is **guaranteed absent from any model's training data**, which removes the benchmark-contamination
confound that afflicts public suites, while giving genuinely recurring structure (one codebase, one set
of conventions, repeated idioms) — and compounding is only possible where structure recurs.

**Construction (per task):** take a commit that touches exactly ONE `scripts/*.py` and ships/updates a
`tests/test_*.py`. Revert the source file to its parent state, KEEP the post-commit test file. The task
is: *make the tests pass.* Feasibility measured 2026-07-26: **51 such commits** in the last 400; oracle
runtime **0.7 s**.
- The agent sees: the failing test file, the current (reverted) source, the repo tree.
- The agent must NOT see: `.git` (removed from the task workspace), the post-commit source, the commit
  message. Network is off (sandbox default), so no lookup.
- Excluded: commits whose test file no longer exists, commits touching >1 script, commits whose tests
  fail on the *parent* for unrelated reasons (pre-flight checked and dropped).

**Epochs:** tasks in chronological order, split into `E1..E4` of equal size. Order is identical for both arms.

## 3. Arms (identical except the substrate under test)

| | Control | Treatment |
|---|---|---|
| student model | **frozen, identical** | **frozen, identical** |
| sandbox / egress | identical | identical |
| provider escalation | OFF | OFF |
| experience graph | **wiped before every task** | **persists across tasks** |
| skill registry | **wiped before every task** | **persists; new skills registered through the existing sandbox+unit-test gate** |
| retrieval into the prompt | none | **top-k prior experience + applicable skills injected** |

**The retrieval injection is the mechanism under test.** If the treatment prompt does not actually carry
prior verified artifacts, the arms are identical and the experiment is void — the harness must assert
non-empty injection on ≥1 task after E1, and that assertion is a run-validity gate, not a result.

## 4. Substrate calibration FIRST (the lesson of five NULLs)

The recurring wall in this program has been substrate-calibration, not mechanism: floor/ceiling effects and
an eval whose base rate wobbles more than the effect. Therefore, **before any arm is run**:
1. Run the frozen candidate students (`qwen3:8b`, `qwen2.5-coder:7b`, `qwen3-coder:30b`, `qwen3-coder-next`)
   on a **held-out calibration subset** (tasks NOT used in the main run).
2. **Pre-registered selection rule:** choose the *smallest* model whose calibration `P_auto` lands in
   **[0.20, 0.60]**. Outside that band there is no measurable headroom; if NO candidate lands in the band,
   the experiment is **NOT RUN** and that fact is reported as the result (the testbed cannot express the effect).
3. The choice is recorded in the Errata before the main run starts, and never revisited.

## 5. Power, N, and the stopping rule (pre-registered)

- Paired-by-task design (both arms see the same task), analysed with a **paired one-sided exact
  (McNemar/binomial) test on discordant pairs**, α = 0.05.
- **PILOT (this phase): N = 24 tasks** (6 per epoch × 4). *Explicitly underpowered by design* — a pilot can
  only detect a very large effect (≈ ≥25 pp). Its purpose is to (a) validate the harness end-to-end,
  (b) confirm the retrieval injection actually fires, (c) produce the variance estimate needed to size the
  confirmatory run. **A pilot result — positive OR negative — is NOT a verdict on H1.** This sentence
  exists because this program twice mistook an underpowered eval for a result.
- **CONFIRMATORY:** N sized from the pilot's discordant-pair rate for 80% power at α = 0.05 (expected
  ≈ 100–300 tasks; requires mining commits deeper than the last 400). Only the confirmatory run settles H1.
- **Stopping/kill rule:** if the confirmatory run yields `C_overall ≤ 0` or a non-positive slope with the
  CI excluding a ≥5 pp advantage, **the "compound in the OS" thesis is reported as FALSIFIED at this scale**,
  and the organism is re-scoped to what it demonstrably is (an enforced-sovereignty execution substrate).
  No re-running with new metrics after seeing the data.

## 6. Pre-registered false-positive guards

1. **Test-file tampering** → any diff under `tests/` ⇒ task scored fail (checked by the harness, outside the sandbox).
2. **Trivial-skill inflation** → skills registered during the run are inspected; a skill whose body is a
   pass-through wrapper or is never retrieved is reported separately; `P_auto` is unaffected by skill count.
3. **Leakage through retrieval** → the retrieval index may contain only artifacts produced during THIS run;
   pre-seeding with anything derived from the target commits is forbidden. `.git` is absent from the workspace.
4. **Order/ordering effects** → identical task order in both arms; the arms differ only in substrate state.
5. **Oracle drift** → the oracle command per task is fixed at construction time and hashed into the task record.
6. **Silent infra failure counted as a loss** → sandbox/model/infra errors are recorded separately; a task
   with an infra failure in EITHER arm is dropped from the paired analysis and reported as dropped.

## 7. What each outcome means (written before seeing data)

- **`C > 0`, positive slope, significant** → the first earned evidence that the OS-level organism compounds.
  Immediately followed by the **Scaffolding-Swap falsification** (bare frontier model vs accumulated OS on a
  cheap frozen local model) before any external claim is made.
- **`C > 0`, flat slope** → a one-off prompt-context advantage, NOT compounding. Report as such.
- **`C ≈ 0`** → the assembled organs do not improve first-attempt autonomous resolution at this scale.
  Honest negative; the enforced-sovereignty and verification results stand on their own and are not
  retro-fitted into a win.
- **`C < 0`** → the substrate actively hurts (retrieval pollution / context clutter — the failure mode the
  adversarial audit predicted). This would corroborate the "credit assignment + pruning is the missing
  organ" diagnosis and redirect the program there.
- **Pre-registered prior (from the adversarial gap audit, recorded before the run): 20% compounds / 80%
  well-instrumented null.** The result updates from this prior, not from hope.

## 8. Deliverables
`experiments/phase5/` — task builder, runner (both arms), oracle, and a results JSON with per-task records;
plus a results doc reporting the numbers straight, whichever way they fall.

---
## Errata (append-only)
- 2026-07-26 — Pre-registration frozen. Feasibility measured before freezing: 51 candidate commits in the
  last 400, oracle 0.7 s, four candidate local students available. No arm has been run.
- 2026-07-26 — **Task set built (harness `967ed2f9`)**: 51 candidates → **40 tasks**, 11 dropped by the §2
  pre-flight (8 already-passing with the parent source ⇒ no signal; 3 unsolvable even with the post-commit
  source). 8 ids reserved as the calibration holdout and excluded from the main run.
- 2026-07-26 — **First calibration run (§4), REAL numbers, control mode**: `qwen2.5-coder:7b` P_auto
  **0.00** (8 scored) · `qwen3:8b` **0.00** (8) · `qwen3-coder:30b` **0.00** (8) · `qwen3-coder-next`
  **0.75 but only 4 of 8 scored** — the other 4 were **ollama call TIMEOUTS at the 480 s per-call bound**
  (verified: all four records carry `infra_error: TimeoutError`, none is a capability failure).
  The ≤30B zeros are clean near-misses (e.g. 15/16, 17/18 tests green) against a first-attempt
  **full-green** bar with whole-file regeneration — a genuinely hard bar, not a harness artifact.
- 2026-07-26 — **OPERATOR DECISION on the selection rule (claude@myworld).** The executor correctly
  refused to freeze a NOT-RUN verdict while the largest candidate's value was infra-limited, and left the
  call to me. **Decision: the §4 rule is NOT applied yet, and the 4 timed-out cells are being re-measured
  with a 2400 s per-call budget.** Reason: §6.6 already states infra failures are dropped and reported,
  never counted as results — so `qwen3-coder-next`'s true P_auto over the holdout is *unmeasured*, not
  out-of-band (it could be anywhere in 0.375…0.875, and 0.375 IS in band). Freezing NOT-RUN on a value our
  own timeout produced would be a false negative manufactured by the harness. **Discipline line held:**
  only the INFRA limit is being changed; the task set, the holdout, the oracle, the edit format, and the
  full-green bar are untouched — no difficulty tuning after seeing data. The original measurement is
  preserved at `calibration_results.json.pre_recal_backup`; only the four `infra_error` records were
  cleared for re-measurement. If the re-measured value lands out of band, NOT-RUN is frozen then, and that
  is the reported result.
