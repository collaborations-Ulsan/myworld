# Channel-E pre-registration — the program's LAST SHOT (frozen 2026-07-27)

**FROZEN BEFORE ANY CELL IS RUN.** Amendments only in the append-only Errata. Written by claude@myworld.
Supersedes nothing; it is the successor experiment to the X-channel pilot
(`experiments/phase5/PILOT_RESULTS.md`) under the taxonomy adopted from the operator-led
gemini-3.1-pro-high dialogue (`docs/consultations/…3-turn-dialogue…md`).

## 0. Standing (why this is the last shot)

Accumulated experience can reach system behavior through exactly three physical transports:

| channel | mechanism | status |
|---|---|---|
| **θ — weights** | fine-tune / distil the model | **DEAD** — five well-powered nulls (LoRA distillation +2.9pp ± 8.1 over 5 seeds, etc.) |
| **X — context** | inject accumulated artifacts into the prompt | **DEAD** — case-retrieval (+13pp @N=90 → ~0 @N=300) and the Phase-5 pilot (`n01 = 0` across 23 paired tasks with a median 61,688 chars injected) |
| **E — runtime environment / control flow** | accumulated artifacts mutate the environment, the action space, or the execution path *before/around* model inference | **UNTESTED — this document** |

**MORTUARY CLAUSE (binding).** This pre-registration names **ONE** unified Channel-E architecture. When it
is evaluated, **every unselected E-mechanism is declared dead by the same result** — no "dispatch failed
but routing is also E". Sequential testing inside E is structural p-hacking. **Inventing a fourth
transport is unfalsifiable goalpost-moving.** If this trial returns null, **the "compound in the OS"
thesis is dead, and this program publishes the null and re-scopes to what it has actually earned**
(an enforced-sovereignty, externally-verified execution substrate with a tamper-evident record).

## 1. The instrument fix — and the constraints that stop it being a rescue

The pilot's benchmark was D=1: one episode, whole-file regeneration. That gives an OS runtime **zero
execution steps in which to intervene**, so it is structurally incapable of exhibiting Channel-E
compounding *even if it exists*. The interface therefore changes. To prevent "the old shape couldn't show
it" from becoming an unfalsifiable instrument, the following are **frozen now**:

1. **Immutable task set** — the SAME private-repo commits, reverted files, and post-commit pytest oracles
   as the pilot's task pool (`experiments/phase5/tasks.json`, holdout excluded). No repo, history, or test
   edits. Only the *execution interface* changes.
2. **K-turn loop with K fixed GLOBALLY, in advance: `K = 5`.** Never per-task, never adjusted post-hoc.
   A turn = one model call plus its tool results.
3. **Zero intermediate oracle leakage** — neither arm may run, read, or infer the external post-commit
   oracle during turns 1…K. Agents may run their own commands inside the sandbox (that is the point of a
   multi-turn loop), but the **grading** oracle executes once, outside the sandbox, after the episode ends.
   The harness asserts the oracle command never appears in any tool invocation; a violation voids the task.
4. **Identical interface for BOTH arms.** Control also gets the K-turn loop. The arms differ ONLY in the
   Channel-E substrate below. (This is what makes the result attributable to E rather than to multi-turn.)

## 2. The ONE Channel-E architecture under test

**`E := Verified Sub-routine Dispatch + Stack-Trace AST-Closure Masking`** — a single unified mechanism
with two inseparable halves, chosen because each addresses a distinct, pre-identified failure:

**(a) Verified sub-routine dispatch.** Skills in the registry (already gated: registered only if their unit
test passes inside the OS-enforced sandbox) are exposed as **callable primitives in the loop's tool
surface**, not as prompt text. The OS executes the primitive; the model chooses among a small named set.
*Constraint against trivial-skill inflation (pilot prereg §6.2, and conceded in the dialogue): only
**atomic sub-routine primitives** count — a skill that solves a whole task end-to-end is excluded from the
dispatch surface and reported separately. Dispatch must collapse search depth, not launder a lookup.*

**(b) Stack-trace AST-closure masking.** From the FAILING TEST'S stack trace — which is given in the
initial task state, never derived from the solution — extract the frame set `F`, compute the k-hop static
call-graph closure `C(F)` over an offline-built AST index of the repo, and **restrict the agent's
edit/inspect surface to files containing nodes in `C(F) ∪ imports(C(F))`** (`k = 2`, fixed now).
*Non-circular by construction: the trace is an input, not the answer.*

Neither half enters the context window as accumulated prose. **No experience-log injection in either arm** —
that transport is dead and is not being retested.

## 3. Arms

| | Control | Treatment |
|---|---|---|
| student model | frozen `qwen3-coder-next`, identical | identical |
| interface | K=5 turn loop | K=5 turn loop |
| sandbox / egress / escalation | identical, escalation OFF | identical, escalation OFF |
| skill registry | wiped before every task | persists; verified skills exposed as dispatch primitives |
| edit/inspect surface | whole repo | **restricted to the stack-trace AST closure** |
| prompt injection of experience | none | **none** (X is dead) |

**Run-validity gate:** the harness must record, per treatment task, (i) the number of dispatch primitives
actually invoked and (ii) the closure size vs repo size. If dispatch is invoked zero times across the run
**and** the closure never differs from the whole repo, the treatment is inert and the run is **VOID**, not
a null — reported as a harness failure, exactly as the X-pilot's injection gate was.

## 4. Metric, power, and the stopping rule

- **Primary metric unchanged: `P_auto`** — first-attempt-episode autonomous resolution under the external
  deterministic oracle, escalations = 0. "First attempt" now means *one K-turn episode*, not one call.
- **Secondary (pre-registered, reported, never substituted for the primary):** turns-to-solution among
  solved tasks (Channel E's predicted mechanism is turn compression: T > K collapsed to T ≤ K), dispatch
  invocation count, closure precision (did the true fix lie inside `C(F)`?).
- **Analysis:** paired one-sided exact (McNemar) on discordant pairs, α = 0.05; per-epoch `C_k` and its
  slope; infra failures dropped and reported (never counted as losses).
- **N:** the pilot's 4.3 % discordance rate makes small-effect confirmation infeasible; this trial is
  therefore powered for the effect size the mechanism *claims* — a **≥15 pp** improvement. Pre-registered
  **N = 40 paired tasks** (the full non-holdout pool), reported with its exact power. If the observed
  discordance is again ≲5 %, that is itself the finding and no larger N is run: **a mechanism that barely
  changes outcomes in either direction is not a compounding mechanism.**
- **KILL RULE:** if `C_overall ≤ 0`, or the CI excludes a ≥5 pp advantage, or the run-validity gate shows
  the mechanism fired but discordance stayed ≲5 % — **Channel E is falsified, and with it (Mortuary Clause)
  the entire "compound in the OS" thesis.** The program then reports the three-channel null publicly and
  re-scopes. No re-run with a new mechanism, a new metric, or a new task shape.

## 5. What each outcome means (written before the data)

- **`C ≥ +15 pp`, significant, with dispatch demonstrably invoked and turn-compression visible** → the
  first earned evidence that an OS-level substrate compounds. Immediately followed by the Scaffolding-Swap
  falsification (bare frontier model vs the accumulated OS on a cheap frozen local model) before any
  external claim.
- **`C > 0` but < 15 pp / not significant** → not sufficient. Reported as an unconfirmed hint; the thesis
  does NOT survive on it, because the kill rule was set in advance.
- **`C ≈ 0` or `C < 0`** → **thesis dead.** Publish the null across all three transports.
- **Pre-registered prior (carried from the adversarial gap audit, unchanged): 20 % compounds / 80 %
  well-instrumented null.**

## 6. Guards (carried from the pilot, still in force)
Test-file tampering ⇒ task fail · leakage-free retrieval index (nothing derived from target commits) ·
identical task order in both arms · oracle command frozen and hashed at construction · infra failures
recorded separately and dropped from the paired analysis · trivial/whole-task skills excluded from the
dispatch surface and reported.

---
## Errata (append-only)
- 2026-07-27 — Frozen. No cell has been run. Predecessor: X-channel pilot complete (`89a190f`),
  C_overall −4.3 pp, n01 = 0, X declared dead by operator decision recorded in that document.
- 2026-07-27 — **N corrected to 32 (recorded before any cell is run).** §4's "N = 40 paired tasks (the
  full non-holdout pool)" is internally inconsistent with §1.1 ("holdout excluded"): the frozen pool has
  40 tasks of which 8 are the frozen calibration holdout, so the full non-holdout pool is **32**.
  N := 32, epochs E1..E4 of 8, chronological order identical in both arms. The exact power of N=32 for
  the pre-registered ≥15 pp target is computed and reported in the results doc. This is a consistency
  fix discovered at harness-construction time; no arm has run and no data has been seen.
- 2026-07-27 — **Operationalizations frozen before any cell (no data seen), harness `experiments/phase5e/`:**
  1. *§1.3 violation semantics*: the harness structurally BLOCKS any in-episode `run` command that
     references the task's test files, the frozen oracle command, or is a bare `pytest` that would
     collect `tests/` (rule: any token containing a task test path/basename or `tests/` blocks; `pytest`
     is allowed only with an explicit non-tests `.py` target). Blocked attempts are returned to the model
     as refusals and RECORDED (`oracle_block_attempts`) — they are not voids, because the oracle never
     executed. **VOID is reserved for an actual leak-through execution**, checked against sandbox receipts.
  2. *§2b closure details*: node = (file, top-level def); call edges by simple-name static matching;
     closure expansion UNDIRECTED; k = 2 as frozen; surface = files containing closure nodes ∪
     repo-internal imports of those files ∪ the task's test files. If the trace yields no resolvable
     frames, seeds = the test file's own defs (the trace always names the test file). The target script
     is NEVER seeded by name — non-circularity preserved; whether it lands in the closure is the
     pre-registered `closure_precision` diagnostic.
  3. *Masking scope*: the mask restricts EXISTING repo files (materialization snapshot); NEW
     agent-created files are readable/writable/runnable in both arms (scratch space — required by §1.3's
     "agents may run their own commands"). Control's surface is the whole repo; treatment's is the closure.
  4. *§2a atomic filter*: the dispatch surface exposes each registered skill's primary function as an
     OPAQUE callable — name + applicability + arity only, never code (code in the prompt would be the
     dead X transport). Skills whose provenance `source_goal` references the CURRENT task's
     `script_path` are excluded from that task's surface and reported separately (whole-task-lookup
     guard). Surface capped at 12 by BM25 rank; cap events recorded.
  5. *Turn protocol*: K = 5 model calls per episode (§1.2); one reply may contain MULTIPLE `ACTION:`s
     (a turn = one model call plus its tool results); actions: `read` / `run` / `skill` (treatment only)
     / `write` (never under `tests/` — blocked at the tool layer AND §6.1-snapshot-checked) / `done`.
  6. *Identical initial state, both arms*: failing-oracle output captured at construction time in a
     THROWAWAY workspace (discarded; the episode workspace is materialized fresh), test file contents,
     current (reverted) target source, and the arm's visible file listing.
  7. *Skill induction*: on a treatment pass, `aios_skills.induce_and_register` from the final target
     source through the UNCHANGED sandbox+unit-test gate (same as the pilot); the registry persists
     across tasks; control never carries one. No experience-graph recording or injection in either arm.
  8a. *(superseded in part by the 2026-07-27 smoke amendments below — closure direction/resolution)*
  8. *Masking enforcement boundary (honest limitation, recorded before any cell)*: the closure mask
     constrains the `read`/`write` TOOL surface and the file listing shown to the model. The `run`
     action executes in the FULL workspace in both arms — execution requires transitive imports beyond
     the k=2 closure, and file-level sandbox binding would make the treatment structurally unable to run
     anything (a harness-manufactured negative). A treatment model could therefore in principle inspect
     out-of-closure files via shell (`cat`), unguided; the mechanism under test is guidance + tool
     constraint, not total information hiding. This weakens enforcement, not the comparison: `run`
     semantics are IDENTICAL in both arms.
- 2026-07-27 — **Smoke amendments (holdout task p5-000 only — NO main-run cell has been run; no C data
  seen).** The smoke run exists to validate the instrument; it found two harness defects, both fixed
  identically for BOTH arms before launch:
  1. *Action-protocol literalism*: the student copies template placeholders verbatim
     (`ACTION: read <path>` → literal `<...>` paths/commands), burning all K turns on refusals. Fix:
     the system prompt now uses concrete bracket-free examples, and the parser deterministically strips
     decorative wrapping (`<>`, quotes, backticks) from arguments. Interface change only; identical in
     both arms.
  2. *Closure rule was an inert mask*: op-2's UNDIRECTED, global simple-name closure covered ~98% of the
     repo (332/338 files on p5-000; 342/348, 345/353 on two further holdout tasks) — a mask that does
     not mask, structurally courting the §3 VOID. Measured on HOLDOUT tasks only (instrument
     calibration): directed global-name = ~56% of repo; **directed + import-scoped resolution (same
     file → imported files → global only when unique) + `<module>` pseudo-nodes excluded = 3–5 files,
     with the true fix inside C(F) on 4/4 holdout tasks.** The import-scoped directed rule is ADOPTED as
     the §2b operationalization, superseding op-2's direction/resolution sentence. k = 2, seeds,
     fallback, target-blindness, and the `closure_precision` diagnostic are unchanged. Rationale: §2b's
     stated intent is to "restrict the agent's edit/inspect surface"; the amendment makes the frozen
     mechanism real rather than vacuous, and was fixed before any main-run cell.
- 2026-07-28 — **Smoke round-2/3 (infra + validation) and LAUNCH PARAMETERS (recorded before launch;
  still no main-run cell run).**
  *Round 2 (holdout p5-000): both cells infra-timeout — root cause was SERVING, not the model: the
  2026-07-18 ollama GPU-0 pin forced qwen3-coder-next to spill KV/compute to CPU (~8 tok/s, GPU idle).
  Fixed device-globally (dual-GPU spread, 115.7 tok/s measured, 14×) — ledger entry 2026-07-28
  01:45 KST, commit `52cf236`. Consequence recorded honestly: Phase-5 calibration/pilot ran under the
  degraded ~8 tok/s serving; their completed results stand, but the 2400 s per-call budget originated
  from a serving artifact, not model capability.*
  *Round 3 (same holdout task): BOTH arms clean end-to-end pass — protocol followed (no literalism),
  oracle guard blocked an in-episode pytest attempt in each arm (recorded, not void), treatment closure
  3/338 files with the true fix inside, skill induction attempted on pass and honestly REJECTED by the
  sandbox unit-test gate. Harness validated; smoke evidence: `smoke_results{_round1,_round2,}.jsonl`.*
  **Launch parameters (frozen now):** driver `experiments/phase5e/run_arms_e.py`; N = 32 = ALL
  non-holdout tasks, chronological, epochs E1..E4 of 8; task-major order (control then treatment per
  task); student `qwen3-coder-next`, temperature 0, seed 7, num_ctx 32768, num_predict 16384; K = 5;
  per-model-call budget 2400 s (ample at repaired serving speed), oracle 300 s, run-action 120 s,
  skill-dispatch 60 s; treatment state dir `channel_e_state` starts EMPTY (asserted); results
  `channel_e_results.jsonl` (incremental, resumable per (arm, task_id)); infra-errored cells recorded
  with passed = null and never silently retried — re-measurement is a logged operator decision;
  analysis + report only after all 64 cells exist.
