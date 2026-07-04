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
