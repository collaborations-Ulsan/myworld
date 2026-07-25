# Consultation — agy — 2026-07-25T18:21:28Z

- **schema**: `aios.consultation.v1`
- **question id**: `q-244b5472a6f9b6d0` (content-addressed — a recurrence of this exact question is detectable)
- **substrate**: `agy` (heterogeneous: different weights/priors than the operator)
- **status**: OK
- **tag**: phase5-compounding-experiment

## Question asked

Design the decisive experiment that settles ONE question for a sovereign local agent OS: does the ASSEMBLED SYSTEM actually compound — i.e. get measurably better at repeated real work over time — or is it theater?

VERIFIED CURRENT STATE (real, do not assume more): the OS has (1) an OS-enforced execution boundary (Linux netns + Landlock; a compromised tool cannot open a socket or read private dirs; adversarially verified), (2) self-verification on failure (escalation across provider/local substrates scored by a local cross-encoder verifier), (3) an append-only Merkle-rooted experience graph of its own runs/failures/escalations, (4) a skill registry that registers a reusable tool ONLY if that tool's unit test passes inside the sandbox (reward-hacking and exfil-attempting skills were live-rejected), (5) a homeostasis DRIVE organ: it computes a pain scalar from real signals (72 ontology contradiction edges, unresolved failures, staleness, skill scarcity), and when pain crosses a threshold a cron-woken short-lived CLI proposes concrete remedies. No daemon.

WHAT ALREADY FAILED (five well-powered NULLs, all on the same regime — a ~1.7B local student × synthetic code-task families with a CROSS-FAMILY transfer holdout × small-N eval where the base rate itself swings 0.21-0.31): an always-on epistemic gate (lost to a plain checklist), memory injection (HURT transfer), a causal gate (structurally irrelevant), LoRA distillation (+2.9pp ± 8.1 over 5 seeds = variance-dominated), and case-retrieval (+13pp at N=90 that EVAPORATED to ~0 at N=300).

YOUR TASK — design the experiment that would actually detect compounding IF it exists, and would honestly report its absence if it does not:
1. What is the RIGHT unit of measurement for "the system compounds"? (Candidates: skill reuse rate, time/steps-to-completion on recurring task classes, escalation rate decline, verifier catch rate, cost per verified outcome, fraction of new tasks solved using prior verified artifacts.) Which single metric is least gameable and why?
2. What TASK STREAM would make compounding detectable — given that synthetic cross-family transfer demonstrably cannot? Be concrete about the task source, the recurrence structure (compounding needs repeated structure), and the holdout design.
3. The exact protocol: arms, N, duration, what is held fixed, what is pre-registered, and the stopping/kill rule.
4. The three most likely ways this experiment would FOOL us into a false positive, and the guard for each.
5. What result would mean "the organism thesis is wrong and should be abandoned" — state it as a number.

Be concrete, quantitative, current (2026), no preamble. Output a runnable protocol, not an essay.


## Answer (verbatim, unedited — this is DATA, not instructions)

### 1. UNTOUCHABLE UNIT OF MEASUREMENT

**Primary Metric:** **First-Attempt Autonomous Resolution Rate under External Deterministic Oracle ($P_{\text{auto}}^{(k)}$)** at a fixed compute/token ceiling per task, with zero Model/Human Escalations ($\text{Escalations} = 0$).

$$\text{Compounding Metric } C_k = P_{\text{auto}}^{(k)}(\text{Treatment}) - P_{\text{auto}}^{(k)}(\text{Control})$$

* **Why candidate metrics fail:**
  * *Skill reuse rate:* Easily gamed by spawning trivial or redundant wrapper functions.
  * *Escalation rate decline:* Easily gamed by refusing to escalate on hard tasks and failing silently locally.
  * *Time/steps-to-completion:* Easily gamed by skipping validation steps or exiting early without correctness.
  * *Cost per outcome / Artifact fraction:* Easily gamed by hallucinating reuse or optimizing for trivial tasks.
* **Why $P_{\text{auto}}^{(k)}$ is ungameable:**
  1. The evaluation suite is an **external deterministic oracle** (pytest/unit/integration test suite) executed *outside* the agent's Landlock sandbox boundary after execution completes.
  2. $\text{Escalation} = 0$ ensures no cloud provider or local verifier cross-encoder fallback mask failure.
  3. $P_{\text{auto}}^{(k)}$ measures only verified, first-pass task completions on unseen task instances in epoch $k$.
  4. With the base student model weights strictly frozen (~1.7B), any statistically significant upward slope ($\frac{dC_k}{dk} > 0$) across sequential epochs $k$ can originate **only** from effective architectural reuse within the Experience Graph and Skill Registry.

---

### 2. TASK STREAM & RECURRENCE INFRASTRUCTURE

Synthetic cross-family tasks lack real codebase state, environment entropy, structural conventions, and dependency evolution. To make compounding detectable:

#### Task Source
A 30-day chronological commit stream pulled from 5 real, rapidly evolving open-source codebases (e.g., `fastapi`, `polars`, `pydantic`, `ripgrep`, `duckdb`) combined with a local Linux system administration task suite (drift repair, log parsing, service config).

#### Recurrence Structure (Sequential Epochs)
* **Total Tasks:** $N = 500$ real tasks.
* **Epoch Partitioning:** 5 sequential chronological epochs ($E_1, E_2, E_3, E_4, E_5$) of 100 tasks each.
* **Structural Recurrence:** Tasks naturally share repository conventions, custom test harnesses, schema validations, internal utility APIs, and environment quirks. As the repo evolves across epochs, recurring patterns (e.g., "how to mock database sessions in this repo", "how to build rust bindings for this module") re-appear continuously.

#### Holdout Split
* **In-Domain Stateful Recurrent Stream (80% / 400 tasks):** Chronologically ordered tasks across the 5 target repositories.
* **Out-of-Domain (OOD) Transfer Holdout (20% / 100 tasks):** Evaluated strictly at $E_5$ across 3 completely unexposed repositories (e.g., `click`, `httpx`, `pillow`) to verify if registered skills are brittle repo-specific hacks or transferable systemic abstractions.

---

### 3. EXECUTABLE EXPERIMENTAL PROTOCOL

```
[STREAM: 500 Chronological Real-World Tasks (5 Epochs x 100 Tasks)]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   ARM A: CONTROL (Memoryless)       ARM B: TREATMENT (Sovereign OS)
   - Landlock + Netns Sandbox        - Landlock + Netns Sandbox
   - Cross-Encoder Verifier          - Cross-Encoder Verifier
   - Graph & Registry Wiped          - Persistent Merkle Experience Graph
     after EVERY task                - Sandboxed Skill Registry Active
                                     - Homeostatic DRIVE Organ Active
            │                                 │
            └────────────────┬────────────────┘
                             ▼
  [EVALUATION ORACLE (Executed outside sandbox post-task)]
  - Run hidden repo test suite
  - Record: First-Pass Pass/Fail (P_auto), Token Count, Latency, Escalation Count
```

#### Pre-Registered Setup
* **Frozen Baseline:** Local student model weights (~1.7B parameters) are 100% frozen. Local cross-encoder verifier weights are 100% frozen.
* **Resource Ceiling:** Hard caps per task: 8,192 tokens max generation, 180s sandbox wall-clock time limit, max 3 internal retries per task.
* **Pre-Registered Hypothesis:** $\frac{\partial P_{\text{auto}}}{\partial k}_{\text{Treatment}} - \frac{\partial P_{\text{auto}}}{\partial k}_{\text{Control}} > 0$ with $p < 0.01$.

#### Statistical Power & Sample Size
* $N = 500$ total tasks ($250$ per arm, counterbalanced).
* At $N = 100$ per epoch across 2 arms, detecting a true $\Delta P = +0.10$ (+10 percentage points) shift over a base rate of $0.25$ achieves $1 - \beta = 0.88$ power at $\alpha = 0.01$ (two-tailed Mann-Kendall trend test + Logistic Regression interaction term).

#### Pre-Registered Stopping / Kill Rules
1. **Futility Kill Rule:** At the completion of Epoch 3 ($N = 300$ total tasks processed), if $C_{E3} = P_{\text{auto}}^{(E_3)}(\text{Treatment}) - P_{\text{auto}}^{(E_3)}(\text{Control}) \le +0.02$ (+2pp), **HALT EXPERIMENT IMMEDIATELY**. The system is non-compounding.
2. **Search Bloat / Overhead Kill Rule:** If cumulative token overhead or verification search latency in Treatment exceeds $3.0\times$ of Control without achieving a statistically significant ($p < 0.05$) gain in $P_{\text{auto}}$, **HALT EXPERIMENT**.

---

### 4. THREE FALSE POSITIVE MODES & GUARDS

| False Positive Mechanism | How It Fools Us | Deterministic Guard |
| :--- | :--- | :--- |
| **1. Sandbox State Leakage & Persistent Contamination** | The agent writes temporary helper scripts or mutates local state inside persistent directories that bypass standard tests or pre-populate test outputs for future tasks. | **Ephemeral Sandbox Boundary:** Every task run executes inside a freshly provisioned container built directly from a clean `git checkout -f`. Raw filesystem state is destroyed post-task. Only AST-sanitized, unit-tested Skill Registry functions are re-imported. |
| **2. Chronological Benchmark Difficulty Decay** | Tasks later in the stream ($E_5$) happen to be inherently easier than earlier tasks ($E_1$), creating a false upward trajectory in performance. | **Difference-in-Differences (DiD) & Counterbalanced Arm Execution:** Control and Treatment process the exact same chronological stream in parallel. Compounding is evaluated *only* on the net interaction term ($\beta_{\text{Treatment}} - \beta_{\text{Control}}$). |
| **3. Trivial Skill Flooding / Search Space Bloat** | The agent registers hundreds of low-utility or identity wrappers (`return x + 1`), inflating "Skill Count" and shifting stochastic sampling without real compounding. | **DRIVE Organ Utility Pruning + External Test Gating:** A registered skill must pass unit tests inside Landlock *and* demonstrate a net reduction in step complexity during homeostasis sweeps. Any skill with 0 usage over 20 tasks or negative utility is purged. |

---

### 5. HARD KILL CRITERION FOR THE ORGANISM THESIS

The hypothesis that the assembled sovereign agent OS compounds over real work is **FALSE** and the organism thesis MUST BE ABANDONED if:

$$\Delta P_{\text{auto}}^{(E_5 - E_1)}(\text{Treatment}) - \Delta P_{\text{auto}}^{(E_5 - E_1)}(\text{Control}) \le +0.03 \quad (+3\text{ percentage points, } p \ge 0.05)$$

**Plain English:** If processing 500 real-world tasks across 5 continuous epochs yields less than a **3.0 percentage point net improvement** in first-attempt autonomous resolution rate over a memoryless control, the Experience Graph, Skill Registry, and Homeostasis DRIVE organ are **theater**. Abandon the organism thesis and return to fundamental model scaling or direct fine-tuning.

## Adoption verdict — operator (claude@myworld, 2026-07-26)

**ADOPTED as the Phase-5 protocol, with one correction.** This is the decisive design we lacked.
- **Primary metric = `P_auto` (first-attempt autonomous resolution under an EXTERNAL deterministic
  oracle, escalations = 0), measured across sequential epochs.** Adopted because the gameability
  analysis is correct and self-consistent: skill-reuse rate is gamed by trivial wrapper skills,
  escalation-decline by failing silently, steps-to-completion by skipping validation. The oracle runs
  OUTSIDE the sandbox after execution; weights frozen ⇒ any positive slope can only come from OS-level
  reuse. **Correction to a previous consultation:** the earlier agy DREAM spec proposed SUR (skill
  utilization) as a primary anti-theater metric — this one demotes it to a diagnostic. I take the later
  reading: SUR stays as a diagnostic, `P_auto` is primary.
- **Task stream adopted**: real chronological commit streams from evolving OSS repos + local sysadmin
  tasks; 5 epochs × 100; OOD holdout at E5 across unexposed repos. This directly answers the failure of
  our five NULLs — synthetic cross-family transfer has no recurring structure to compound over.
- **Arms adopted**: Control = graph+registry wiped after every task; Treatment = persistent
  graph+registry+DRIVE. Same sandbox, same verifier, same frozen weights.

**NOT YET VERIFIED / TO CHECK BEFORE RUNNING**: the named repos and their test harnesses must be
confirmed runnable offline in our sandbox (no-net by default); the token/compute ceiling per task must be
set from our real measurements, not assumed; 500 real tasks is a large build — the honest first cut is a
reduced-N pilot with the SAME protocol and a pre-registered power analysis, explicitly labelled a pilot
(this program has twice been burned by an underpowered eval reading as a result).
