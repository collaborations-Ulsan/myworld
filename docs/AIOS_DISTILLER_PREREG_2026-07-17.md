# AIOS Experience-Distiller — Keystone Pre-Registration (v1.1, FROZEN at commit 2026-07-17)

> v1 → Codex(gpt-5.5) 동결-전 공격 리뷰 12건 전수 반영 → v1.1 커밋으로 동결.

**Authority**: founder GO (2026-07-17) on the Council-verdict pivot (`6a15d19`) — AIOS = **소버린
경험-증류기**: escalation의 검증된 궤적을 인과-게이트로 선별해 로컬 weight(LoRA)로 증류, 로컬 모델이
자기가 부리는 사회로부터 실제로 학습. 조립/라우팅은 수단.

**지위**: 사전등록. 첫 런 전 커밋; 본문 불변, 변경은 Errata append-only. Council의 반증실험을
그대로 포함한다 — 이 실험은 pivot을 EARN할 수도, 반증할 수도 있다 (no-launder 양방향).

## 1. 가설 (사전 고정)

- **H1 (confirmatory — weight-level transfer)**: 소버린 escalation에서 인과-게이트로 선별한 검증
  궤적을 LoRA로 증류하면, **작은 로컬 모델**의 held-out 태스크 성공률이 base 대비 통계적으로 유의하게
  상승하고 sentinel 무회귀다. (S+1/S+1.1이 context-level에서 실패한 transfer 질문의 weight-level 재판정.)
- **H2 (secondary — 자립도)**: 증류 후 escalation rate(로컬 실패→frontier 호출 비율)가 하락한다.
- **H3 (Council disproof arm — 아키텍처 정당성)**: 변이 태스크에서 Full-AIOS(소버린 라우팅+검증+증류)가
  Naive-Linear(로컬 실패 시 raw error를 frontier CLI로, 스캐폴드 없음)와 raw-frontier를 성공률에서
  이기거나, 지지 못하면 **아키텍처가 friction임을 인정하고 그대로 공개**한다.

## 2. 기질 (S+1.1 천장 진단의 해법)

- **학생(증류 대상) = 작은 로컬 모델**: qwen3 1.7b~4b (HF weights, LoRA 가능). 작은 모델 = 자주
  실패(headroom + escalation 데이터 생성) + 빠른 학습. **천장 문제와 학습 문제를 동시에 해결.**
- **교사(사회) = 소버린 escalation 캐스케이드** (f31d055): local(작은 모델) 실패 → qwen3-coder:30b →
  NIM → frontier CLI. 교사의 성공 궤적이 원료.
- 태스크: LearnOS 태스크셋 확장(작은 모델이 30-70% 실패하는 난이도로 재캘리브레이션; 결정론적
  functional grader) — A(mine/train) / B(held-out) / sentinel 3분할, B는 증류 데이터에 절대 불포함
  (구조적 격리, S+1 규율 유지).

## 3. 파이프라인 (전부 기존 자산 재활용)

1. **궤적 수집**: 소버린 모드로 A-태스크 실행 → 학생 실패 시 escalation → 교사 성공 궤적 + provenance.
2. **인과-게이트 선별** (S+1.1 재사용): 궤적/수정이 held-out 테스트를 실제로 통과시키는 것만 —
   verified-only. Blind-Curator 감사(검증자 결함 주입) 통과 후에만 신뢰.
3. **증류 데이터셋**: (task, teacher_trajectory→solution) SFT 쌍. 개인정보·비밀 스캔 후 저장.
4. **LoRA 학습**: 학생 모델에 QLoRA/LoRA (dual 5090; 1.7-4b는 <10GB — GPU 경합 고려). 밤새/배치.
5. **판정**: B에서 base-학생 vs LoRA-학생 (paired, 동일 예산·프롬프트); sentinel; escalation rate;
   H3 disproof arm (변이 서브셋에서 Full-AIOS vs Naive-Linear vs raw-frontier).

## 4. 판정 기준 (사전 고정)

- **H1 성공**: B에서 LoRA-학생이 base-학생을 paired로 유의하게(one-sided exact test α=0.05) 상회 +
  sentinel 무회귀 + Blind-Curator 감사 통과. 실패 시: weight-level에서도 transfer 불성립 = Sutton의
  "frozen 주위 스캐폴드" 비판이 weight-증류에도 미침을 시사 — 그대로 공개.
- **H3 성공**: Full-AIOS ≥ Naive-Linear AND ≥ raw-frontier (변이 서브셋 성공률). 실패 시: "스캐폴드는
  friction" — 아키텍처 강등을 공개하고 증류 파이프라인만 유지(라우팅 미니멀화).
- 지표 전수 보고, 선택 보고 금지. 모델 핀·시드·프롬프트 해시·스크립트 해시는 첫 런 전 Errata에.

## 5. 가드 (기존 규율 전부 승계)

held-out 구조 격리 · 인과-게이트 · sentinel · Blind-Curator 검증자 감사 · 개인정보/비밀 스캔(증류
데이터에 `_from_desktop`/dain/minyoung/키 절대 불포함) · no-launder · 교사 궤적의 라이선스/ToS 존중
(자기 시스템 로그의 자기 증류 — 외부 재배포 아님).

## 6. Codex 동결-전 리뷰 반영 (2026-07-17, 12건 전수)

- **False-positive 가드 (필수)**: (1) B는 **별도 생성기 계열 + metamorphic 변형 + 히든 시드**로 —
  A와 문법 공유 금지(안 그러면 LoRA가 capability 아닌 템플릿/교사-수정-스타일 학습). (2) grader에
  **해결 후 생성한 adversarial 테스트 + property 테스트 + 최소 1개 블라인드 리뷰 슬라이스** 추가
  (결정론 grader만이면 테스트-만족 학습). (3) 평가는 **stripped prompt + solution-only 채점**
  (교사-rationale 모방이 prompt-shaped held-out만 올리는 것 차단; 궤적을 채점하지 않음).
- **대조군 2개 (필수 — 인과-게이트/궤적의 가치 증명)**: `Student-LoRA-unverified`(같은 태스크·같은
  교사량, **인과-게이트 없음**) → 검증이 실제로 일하는지; `Student-LoRA-solution-only` vs
  `trajectory+solution` → 궤적이 최종답 너머 가치 있는지.
- **최소 N (사전 고정)**: `N_train ≥ 250` 검증 궤적, 미만이면 **pilot only** 표기. 이질적 태스크군이면
  500+. 4b는 궤적 truncate/pack + eval을 루프 밖에 둘 때만 현실적; 1.7b는 밤샘 QLoRA 현실적.
- **Sentinel 보호**: base/sentinel rehearsal 10-20% 혼합 또는 KL/early-stop — escalated 실패만 학습하면
  "개선"이 기존 능력과 맞바꿈일 수 있음.
- **H2 정정**: escalation-rate 하락은 confidence 게이밍일 수 있음 → **동일 예산에서 성공한 로컬 solve만**
  카운트(호출 수 감소 아님).
- **H3 정정**: primary = 성공률, secondary = **cost/privacy-조정 성공** (raw-frontier가 성공은 이겨도
  비용/프라이버시에서 질 수 있음).
- **2주 솔로 축소**: H3 Council 매트릭스 전폭 대신 → **Full-AIOS vs Student-LoRA-unverified vs base**를
  한 mutation family에서; raw-frontier/naive-linear 매트릭스는 후속. (인과-게이트 가치 증명이 최우선.)

## Errata (append-only)
- (v1.1 동결. v1→v1.1: Codex 리뷰 12건 반영 — B 생성기 분리+metamorphic, adversarial/property/blind
  grader, stripped-prompt solution-only 채점, Student-LoRA-unverified·solution-only 대조군, N≥250,
  sentinel rehearsal, H2 동일예산-성공만, H3 cost-adjusted, 2주 스코프 축소.)
- **2026-07-18 PILOT 결과** (`64e8950`, `AIOS_DISTILLER_PILOT_RESULTS_2026-07-18.md`): N_verified=25(pilot).
  학생 qwen3:1.7b, substrate 캘리브레이션 50% pass(헤드룸 확인). B(36) held-out: base 0.389 →
  verified-LoRA **0.694**(+30.5pp, p=0.0037) / unverified-LoRA **0.750**(+36.1pp, p=0.00049), sentinel
  무회귀, escalation 0.61→0.25-0.31. **H1 directional EARNED**(증류가 학생을 유의하게 개선 — 아크 첫
  weight-level positive). **인과-게이트 무이득**(unverified≥verified, 2태스크 차=pilot 노이즈) — 작은
  N에서 데이터 양이 필터를 이김. 환경: torch cu128로 RTX 5090 GPU 언블록.
- **confirmatory 설계 (다음 런, 사전 고정)**: N_verified≥250(또는 스코프시 명시), arms =
  base / verified-LoRA / unverified-LoRA / **soft-weight-LoRA**(hard filter 대신 인과-신뢰도 가중) —
  게이트의 진짜 값어치를 "질이 양을 이기는 구간"에서 판정. 교사 캐스케이드는 **local/NIM 우선**(frontier
  CLI quota 최소화). GPU 학습·평가(cu128). 나머지 v1.1 가드 전부 승계.
- **2026-07-18 confirmatory 런 START (핀)**: founder GO. collect `--seed 42 --a-instances 64`
  (8 A-family × 64 = 512 A-태스크) `--time-budget-s 21600`(6h) `--out-dir data/confirmatory`,
  detached(PID 657299, 세션-생존). 학생 = qwen3:1.7b(ollama), 교사 = 소버린 캐스케이드(local
  qwen3-coder:30b→NIM→frontier CLI, local/NIM 우선). 목표 N_verified≥250. 학습·평가는 torch
  2.11+cu128 GPU(cu124 블로커 해소됨). arms(계획): base/verified/unverified/soft-weight.
  결과 도착 시 이 Errata에 N_verified·B pass·게이트 판정 append.
- (첫 confirmatory 런 전 핀 기록 예정: 학생/교사 모델 ID, 시드, 프롬프트 해시, 학습 스크립트 해시, N_train 실측.)
