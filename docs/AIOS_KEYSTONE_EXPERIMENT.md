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
