# AIOS Keystone Experiment — does the commons/DescentNet causally help? (design + running log)

> 설계: Fable (claude@myworld), 2026-07-04. Codex의 keystone 비판(AGI thesis §5)의 답을 EARN하는 실험 프로그램.
> **no-launder 양방향**: 결과를 그대로 보고. negative는 pivot이지 종착점이 아님(rule 9). positive를 null로 세탁도 금지.
> **공개 규칙**: EARNED positive(rigorous·real signal) 전엔 공개 안 함 — "먼저 공개"는 정직한 결과가 있어야.

## The claim (Codex keystone)
AIOS 레이어(**global cross-agent 커먼즈** + **DescentNet** 무결성 프리미티브)가 vanilla baseline 대비 agent 결과를
**인과적으로 개선**한다 — 누출·오염·stale 증폭 없이.

## Rung 0 — DONE (negative, diagnosed)
freq×DescentNet, next-tool 예측, held-out N=300: baseline top1 0.587/top3 0.83 vs AIOS 0.19/0.27 (Δ -0.40/-0.56).
**진단**: (1) DescentNet은 예측용이 아니라 모순/무결성용 — 태스크 미스매치; (2) 곱셈 블렌드가 강한 freq를 희석;
(3) keystone claim(global 커먼즈)을 테스트하지도 않음(use_global off). → **미스매치 proxy이지 moat 반증 아님.**

## Experiments (pivot 순서)

### A — Commons contribution (the keystone, proxy metric) ★ 먼저
- **Arms**: `predict_behavior(use_global=False)` vs `predict_behavior(use_global=True)` — 다른 건 고정, **global 커먼즈만** 변수.
- Held-out next-action 예측 (recent un-ingested 세션). Metric: top-1/3 accuracy + Δ.
- 질문: cross-agent 커먼즈가 예측을 돕는가? Δ>0 = keystone 신호.

### C — Blend fix (prerequisite) ★ A와 병행
- freq×descent가 freq보다 나쁨 → 블렌드가 깨짐. 변형 테스트: freq-only / freq + descent(confident일 때만 gate) /
  additive / rank-fusion. **목표: AIOS arm ≥ freq baseline** (그래야 커먼즈를 얹을 토대).

### B — DescentNet on its REAL job (integrity, not prediction)
- 알려진 모순/오염 엔트리를 주입 → DescentNet obstruction H¹가 baseline보다 잘 flag하는가?
- Akashic poison-resistance keystone(§5C)과 직결 — 이게 DescentNet의 진짜 기여 가설.

### D — Fuller claim (task-success, proxy에서 신호 나오면)
- absorption-probe: bare agent vs +commons-hint(retrieved "what worked" 주입)로 **실제 task** 수행 → success/recovery Δ.
- 예측 proxy를 넘어 "실제로 더 잘 하는가"의 최종 주장.

## Honest guards
- held-out 청결(train=test 금지, time-split); N + effect size 보고; null도 결과(rule 9).
- 결과를 그대로; negative→positive 스핀도, positive→null 세탁도 금지.
- named exits: **EARNED positive keystone** 또는 **exhaustive impossibility**(그 자체로 강한 주장).

## Running log (append-only — subagent가 rung마다 append)
| rung | experiment | setup | result | verdict |
|---|---|---|---|---|
| 0 | freq×descent tool-pred | N=300, use_global=off | Δ top1 -0.40, top3 -0.56 | ✗ negative — mismatched proxy, diagnosed |
| 1 | **C: blend fix** — 8 arms, retrieval+descent shared, held-out time-split (25 ingested excluded) | N=150, vocab=80, k=6 | full-corpus freq **0.42/0.52** (top1/top3); best AIOS arm `gated` (freq-primary, descent tie-break) 0.347/0.467; retr_freq 0.12/0.467; additive 0.04/0.133; mult 0.04/0.14; rrf 0.04/0.067; **descent_only 0.00/0.04** | ✗ **NULL for C's goal** — no freq×descent blend ≥ freq baseline. descent_only≈0 confirms DescentNet carries *zero* next-action signal (Rung0 dx#1 confirmed); every arm letting descent touch top-1 collapses. `gated` only *approaches* baseline. Constraint: next-tool is base-rate-dominated; neither semantic retrieval nor DescentNet adds predictive power. Lever is NOT prediction. (`scripts/aios_keystone_bench_c.py`) |
| 2 | **A: commons contribution (the keystone)** — local-only vs local+GLOBAL, best arm fixed, live authed sync, held-out | N=40 ×2 (sanitized 2 buckets / raw 40 queries) | **Pre-registered contrast (use_global off→on):** freq Δ top1 **+0.375/+0.45**, top3 **+0.15/+0.175** — looks positive. **But clean control (global vs whole-corpus freq, same 40 cases): Δ top1 0.0, top3 +0.025 (1/40 = noise).** local_freq 0.175/0.475 · full_freq 0.35/0.60 · global 0.35/0.625 | ✗ **NULL for the keystone (no-launder).** The positive contrast is a *weak-comparator artifact*: local retrieval underperforms the base rate, and the commons "helps" only by **re-injecting base-rate-common tools (Read/Edit/Bash)** it already had. Against the honest baseline the commons adds ≈0. Not cross-agent knowledge — a roundabout base-rate restorer. Holds for both degenerate (2-bucket) and rich (40-query) retrieval. (`scripts/aios_keystone_bench_a.py`) |
| 3 | **B: DescentNet on its REAL job (poison/contradiction, §5C)** — obstruction H¹ vs cheap baselines; real behavioral entries as sheaf nodes; AUC over N=300 trials | **B1** single-entry poison (cross-cat / random / shuffle), K=6; **B2** matched-energy frustration witness | **Proven+confirmed:** obstruction = harmonic (H¹) part of edge residual ⇒ single-entry poison = removable coboundary ⇒ H¹≡0. **B1:** obstruction mag **≈6–8e-8 (numerically ZERO)** all poison types (AUC 0.72/0.70/0.50 is float-pinv noise, not a usable detector); real (moderate) detectors are **Jaccard AUC 0.67 / node-variance 0.63–0.65**. **B2 (witness):** benign-removable vs frustrated-harmonic edge fields of **identical magnitude** → **obstruction AUC 1.00 (d=278)** vs **raw-edge-norm AUC 0.36 (blind)**. | ⚖ **Split verdict (no-launder both ways).** ✗ **NEGATIVE for the keystone-as-stated:** H¹ is provably/empirically ~0 for the poison that actually threatens a commons (independent bad entries) — it CANNOT flag them; a trivial consistency filter (not the sheaf machinery) is what catches them, and only moderately. ✓ **Narrow EARNED positive (witness):** H¹ uniquely detects *frustrated cyclic* contradiction (AUC 1.0) that magnitude/variance provably miss (AUC ~0.5) — a real non-factorization witness. **Caveat (rule 4): valid separation, prevalence UNPROVEN** — demonstrated on a *constructed* harmonic contradiction; real commons poison is ~all H⁰ (independent), which H¹ can't touch. (`scripts/aios_keystone_bench_b.py`) |
| 4 | **B′: PREVALENCE (terminal rung)** — are REAL commons contradictions cyclic-frustrated (H¹) or independent (H⁰)? HodgeRank on real tool-transition flows (entries' own structure, no injection); clean single-cat vs REAL cross-cat contaminated groups; head-to-head vs cheap H⁰ | N=150 groups ×3 richness (gsize 8/16/24), noise floor = pure-gradient control | **Floor = 0.0 exact** (Hodge split exact ⇒ any HF>0 is real). **Clean HF** mean ~0.23, median collapses with data (0.15→0.02→0.005) but heavy tail persists (p90 ~0.6, max ~0.92) ⇒ genuine cyclic H¹ in real agent flow, not sampling noise. **Contaminated HF** consistently higher (median 0.17–0.34; Δmean **+0.039/+0.050/+0.086**, ↑ with data). **BUT decisive head-to-head — separation AUC (contam vs clean): H¹ harmonic 0.514/0.544/0.590 vs cheap H⁰ tool-entropy 0.675/0.691/0.661.** | ⚖→✗ **Exhaustive-impossibility exit (no-launder both ways).** ✓ Real H¹ EXISTS and real contamination elevates it (B2 witness was real-grounded, not artifact; the signal even ↑ with data — the one non-exhausted lever). ✗ **But H¹ is a POOR poison guard (AUC ≤0.59, near chance) and is DOMINATED at every richness by a trivial H⁰ tool-distribution entropy (AUC ~0.66–0.69) needing zero sheaf machinery.** Real cross-source contamination is H⁰-shaped (vocabulary shift), not H¹-shaped (same-vocab cyclic flip) — H¹'s niche does not match the realistic threat. **Retire H¹ as the commons poison guard; ship the cheap H⁰ consistency filter.** (`scripts/aios_keystone_bench_bprime.py`) |

## Synthesis after Rung 3 (Experiment B) — 2026-07-04
**Keystone status: the "DescentNet poison-resistance" claim does NOT hold as stated, but a narrow, real capability is EARNED.**
- **B1 negative (decisive for the threat model):** obstruction H¹ is **numerically zero (≈1e-7)** for cross-category, randomized, and shuffled single-entry poison — a *theorem*, not a tuning failure (a single bad entry is an H⁰ / removable-coboundary offset; H¹ is by construction invariant to it). The reported AUC≈0.72 is float32 pseudo-inverse noise at 1e-7 scale, **not a deployable detector**. What actually (moderately) flags realistic poison is a **cheap H⁰ consistency filter** — top_tools Jaccard (AUC 0.67) or embedding variance (0.63–0.65) — which needs none of the sheaf machinery.
- **B2 witness (the honest positive):** with two edge-fields of **identical energy**, obstruction separates benign (removable) from frustrated (harmonic) contradiction **perfectly (AUC 1.0, d=278)** while raw magnitude is **blind (AUC 0.36)**. This is DescentNet's genuine, unique job: detecting *distributed cyclic frustration* (A⊕B⊕C⊕…≠0 around a loop) that no node-level or pairwise-magnitude statistic can see. Non-factorization witness with a real predicted consequence (a contradiction cycle invisible to every H⁰ check).
- **The rule-4 line I will not cross:** B2 shows the separation is VALID; it does **not** show it is PREVALENT. The contradiction was constructed. I have **not** demonstrated that real Akashic poison ever takes cyclic-frustrated form — and B1 shows the common threat (independent bad entries) is H⁰, which H¹ cannot defend against. So the keystone ("flag a poisoned entry that would degrade everyone") is **false for the realistic threat** and **true only for a contradiction form not yet shown to occur**.

**Single sharpest next pivot → Experiment B′ (PREVALENCE): measure the H⁰/H¹ split of *real* commons contradictions.** The entire value of the H¹ primitive hinges on one unmeasured fact: do real coherent task-groups in the live Akashic corpus ever exhibit **nonzero obstruction from their OWN declared pairwise relations** (not injected)? Mine the commons for frustrated cycles: build edge measurements from entries' *actual* claimed relations/outcomes and measure the harmonic fraction. If a non-trivial rate of real contradictions is cyclic → H¹ earns a real, non-redundant defensive role (escalate to a §5C poison-resistance build). If real contradictions are ~always independent (H⁰) → **retire H¹ as the poison guard and ship a cheap consistency filter instead.** Either way it closes the keystone with an EARNED positive or an exhaustive impossibility. → escalate to Fable.

## Synthesis after Rung 1–2 (both NULL, honestly) — 2026-07-04
The keystone claim (**global commons + DescentNet causally improve agent outcome**) **LOST support on the prediction proxy**, cleanly:
- **DescentNet** carries *zero* next-action signal (C: descent_only 0.00/0.04; any blend that lets it touch top-1 collapses). Rung 0 diagnosis #1 confirmed: it is not a predictor.
- **Global commons** adds *nothing* over whole-corpus frequency (A control: Δ top1 0.0, top3 +0.025). The headline "+0.375" is base-rate re-injection past a crippled local arm, not cross-agent transfer.
- **Best config for next-action prediction = plain whole-corpus frequency** (`full_freq`). The AIOS layer's most it can do here is *not hurt* (`gated` ties). So the layer should get out of the way on this task.

**Two structural findings (real, actionable):**
1. **Wiring bug — commons is a silent no-op in production.** `_akashic_request` (used by `sync_from_global`) sends **no `X-AIOS-Key`**; `/sync` now returns **402 Payment Required**, which `sync_from_global` swallows to `[]`. So the live `predict_behavior(use_global=True)` path *never* receives global data. Any commons rung is mechanically void until this is fixed (I authenticated manually in Exp A to make A testable at all).
2. **Privacy-collapse — the commons can't retrieve by context.** The privacy sink sanitizes every query to `safe_summary(classify(ctx))` = `category:code`/`docs`/…, so 40 diverse held-out contexts collapse to **2 distinct global queries**; the commons returns near-identical generic patterns. The retrieval-vs-privacy tension is unresolved: content-free queries cannot do context-specific transfer.

**Constraint this null establishes:** the AIOS layer's value (if any) is **NOT in next-action prediction** — that task is base-rate-dominated and both primitives are the wrong tool for it. A positive must be EARNED on the primitives' *real* jobs.

**Sharpest next pivot → Experiment B (DescentNet on its REAL job: integrity / contradiction / poison detection).** Both prediction rungs prove prediction is the wrong task; B tests DescentNet's obstruction-H¹ where it was actually designed to fire — Akashic poison-resistance (thesis §5C). Prereq before any *commons* rung (A-redux / D): fix bug #1 (send the key) and bug #2 (a privacy-preserving but context-bearing query), else the commons is mechanically null. → escalate to Fable.

---

## FINAL KEYSTONE VERDICT — program closed 2026-07-04 (Rungs 0–4)

**One-line verdict for AGI thesis §5:** *Across every tested form — next-action prediction, cross-agent commons transfer, and DescentNet poison-resistance — the AIOS layer (global commons + DescentNet/H¹) does **NOT** causally improve agent outcomes over cheap vanilla baselines; the keystone is an **honestly-earned NEGATIVE** (exhaustive impossibility on the stated claim), with one narrow, real, but non-dominant capability preserved.*

**The full ladder, straight (no-launder both directions):**
| primitive | tested as | result |
|---|---|---|
| DescentNet | next-action predictor (R0/R1) | zero signal; base-rate freq dominates |
| Global commons | cross-agent transfer (R2) | +0 over whole-corpus freq (control); apparent gain = base-rate re-injection |
| DescentNet H¹ | single-entry poison guard (R3-B1) | ≡0 by theorem; cheap Jaccard/variance is the (moderate) real detector |
| DescentNet H¹ | cyclic-contradiction detector (R3-B2) | **AUC 1.0** witness — real & unique, but a *constructed* contradiction |
| DescentNet H¹ | REAL contamination guard (R4-B′) | real signal exists (floor=0, Δ↑ with data) but **AUC ≤0.59, dominated by cheap H⁰ entropy AUC ~0.68** |

**What is EARNED-positive and must not be laundered away:** genuine H¹/cyclic structure is REAL in agent tool-flow (noise floor exactly 0; clean harmonic mean ~0.23 with a heavy tail stable across 3× data), real contamination does elevate it, and H¹ is provably the *unique* detector of same-vocabulary cyclic frustration (B2, AUC 1.0). The math and the primitive are sound.

**What is decisively NEGATIVE:** none of that buys the keystone. The realistic commons threat (merging incompatible sources) is **H⁰-shaped** (vocabulary/distribution shift), which a **free tool-distribution entropy filter catches better (AUC ~0.68) than the entire sheaf-cohomology stack (AUC ≤0.59)** — at every data richness. DescentNet's genuine niche (same-vocab cyclic-order contradiction) is not the shape real poison takes.

**Engineering recommendation (ship this):** **Guard the Akashic commons with a cheap H⁰ consistency filter** — top_tools Jaccard / tool-distribution entropy / embedding variance (all AUC ~0.63–0.69, ~zero cost). **Do NOT ship DescentNet/H¹ as the poison guard.** Keep H¹ on the shelf only if a *future, measured* use-case exhibits same-vocabulary cyclic contradiction (none found in this corpus).

**Only non-exhausted lever (honest residual, not a reopening):** H¹'s contamination-separation AUC rose monotonically with per-group data (0.514→0.544→0.590 over gsize 8→24). At far larger scale it may sharpen — but it started behind and trails the free baseline throughout, so the recommendation stands. Reopen only if that data-scaling crosses the H⁰ baseline in a real deployment measurement.

Harnesses: `scripts/aios_keystone_bench_{c,a,b,bprime}.py`. Program CLOSED — EARNED negative with a bounded real-signal finding. → Fable for final disposition.

---

## ENGINEERING OUTPUT SHIPPED — 2026-07-04 (commit 8415cdb)

The earned negative's constructive recommendation is now shipped as `aios guard`
(`scripts/aios_akashic_guard.py`). It is the cheap H⁰ consistency filter the ladder
proved is the real poison detector — **not** DescentNet/H¹.

- **What it does:** per-category tool-typicality profiles over the 1065-entry commons
  ({code:311, personal:300, data:300, docs:154}); anomaly = 1 − mean typicality of an
  entry's tools vs its declared category. `aios guard` audits the commons; `aios guard
  --score CATEGORY TOOLS` guards a candidate before it enters.
- **Honest calibration:** the commons vocabulary is noisy ReAct trace tokens, so an
  absolute cutoff is meaningless — the flag is RELATIVE (per-category p95 threshold).
  Validated end-to-end: **clean false-flag 4.0%, injected cross-category poison caught
  78.9%, zero training cost** (AUC ~0.97 raw separation; 78.9% is the honest catch once
  poison must beat the category's own p95 — reported straight, not the inflated 97.7% an
  absolute cutoff would claim).
- **DNA-compliant:** draft-first — flags for operator review, never auto-deletes
  (append-only #3, operator override #6).

Loop closed positive on the engineering axis: the negative keystone yielded a shipped,
validated, honestly-measured guard. DescentNet/H¹ stays on the shelf per the recommendation.
