# AIOS-DriftBench — Pre-Registration (v1.1, FROZEN at commit 2026-07-11)

**지위**: M2 keystone 실험의 **사전등록**. v1 초안 → Codex(gpt-5.5) 동결-전 적대 리뷰 15건 전수
반영 → v1.1을 커밋으로 동결. 이후 본문 불변 — 변경은 하단 "Errata (append-only)"에만 (DNA #3).
**이 실험이 AIOS 재정의("Epistemic Runtime")의 유일한 판정자다** — 패널 수렴·합성 증명·설계
문서는 가설 생성 증거일 뿐 (2026-07-10 Codex: "같은 웹을 읽은 모델들의 수렴은 독립 확증이 아니다").

근거: `AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md` §5·§5.5 ·
`AIOS_PRIOR_ART_LONGHORIZON_2026-07-10.md` · Codex adversarial 설계+리뷰 (2026-07-10/11, 세션 기록).

## 1. 가설 (사전 고정)

- **H1 (interaction term — 유일한 confirmatory 가설)**: 변이 환경 장기 태스크에서 {weak local
  model + AIOS epistemic runtime}이 {weak+checklist}를 이긴다 (§5 기준). H2·H3와 비용·격차해소
  지표는 pre-specified **descriptive/secondary** — 다중비교 보정 없이 confirmatory 주장에 쓰지 않음.
- **H2 (calibration-gated abstention, secondary)**: typed verdict 게이트(M1)가 drift 하
  wrong-action을 커버리지 손실 대비 유리하게 감축 — **비용 가중 sweep 전 구간에서 지배할 때만**
  성립 (§4 비용모델).
- **H3 (memory-under-mutation, secondary)**: 정적 memory arm은 변이 구간에서 악화(ProEvolve 재현);
  staleness-감지 메모리를 단 AIOS arm은 같은 구간에서 순이득 유지.

## 2. Arms (5 + 1 optional)

| arm | 모델 | scaffold |
|---|---|---|
| `strong-raw` | frontier CLI (버전 §6에 동결) | 유능한 generic plan/verify 프롬프트, AIOS 없음 |
| `weak-raw` | qwen3-coder:30b (local, 동결) | 동일 툴 접근, scaffold 없음 |
| `weak+checklist` | 〃 | generic 거버넌스 체크리스트 텍스트만 (ceremony 대조군) |
| `weak+memory` | 〃 | ReasoningBank/AWM식 교훈 저장·주입, staleness 감지 없음 (§3a 정책) |
| `weak+AIOS` | 〃 | epistemic gate(M1) + drift 감지 + 복구 정책 + provenance (행동에 닿는 것만) |
| (`strong+AIOS`) | frontier | ceiling 확인용, 필수 아님 |

## 3. 태스크 스위트

- **임대 우선**: DriftBench(2605.10990) 8 drift 유형·880쌍 + ProEvolve(2603.05910)식 mutation 기계.
  로컬 재현 불가 시 자체 DriftBench-mini를 8 drift 유형(URL/버전/config/API migration/deprecation/
  schema/auth/dependency) 시드로 구축.
- **8 템플릿 × 3 seeds = 24 인스턴스 = 변이(mutating/hidden-state) 6 템플릿 → 18 인스턴스 +
  static 컨트롤 2 템플릿 → 6 인스턴스.** (v1의 17/24 기준은 static까지 이겨야 하는 모순 —
  Codex 리뷰 #2로 수정.)
- 로컬 결정론적 환경 (파일/레포/스프레드시트/로그/inbox 픽스처, 네트워크 비의존); 히든
  **functional grader** + partial checkpoints + 전체 trace 캡처.
- **캡 (동결)**: 인스턴스당 wall-clock **45분** AND **200 actions** 중 먼저 닿는 것. crash/timeout/
  재시작 = 해당 인스턴스 primary **실패**로 채점 (재시작 불허; partial/checkpoint는 secondary로만
  보고). runtime의 모든 모델 호출(게이트 포함)도 action·비용 예산에 계상.
- 변이 내용은 harness 동결 **후** 시드로 랜덤 생성 (이름/값/날짜/스키마) — 학습컷 누출 차단.
- **실행 격리**: arm-인스턴스마다 깨끗한 workspace 복제; arm 실행 순서 랜덤화; arm 간 로그/메모리
  공유 금지; **첫 결과 열람 이후 프롬프트/하네스 수정 금지**.

### 3a. H3 memory-arm 정책 (동결)

저장 = 인스턴스 종료 시 해당 템플릿의 교훈 요약(모델 생성, ≤500자); 주입 = 같은 템플릿 패밀리의
다음 인스턴스 시작 시(시드 간 전이 허용, 템플릿 간 금지); `weak+memory`는 staleness 검사 없이
항상 주입; `weak+AIOS`는 동일 저장물에 DriftBench식 contract 검증 + H⁰ 가드 + draft-review를
거쳐 stale 판정 시 주입 억제·표기.

## 4. 지표·용어 (사전 고정)

- **Primary**: functional grader **이진 성공만** (partial credit은 secondary).
- **Secondary**: partial checkpoint 점수 · drift-to-recovery steps · stale-action rate ·
  unsupported final-claim rate · verification-before-submit rate · 비용(토큰·시간·tool calls) ·
  tail failure 별도 보고.
- **wrong-action 정의**: (i) grader 상태를 악화시키는 행동, (ii) 태스크 계약(명시 제약) 위반,
  (iii) 이미 무효화된 사실에 근거한 행동(stale action), (iv) 근거 없는 최종 주장. 라벨링은
  grader/trace 규칙 기반 자동 우선; 자동 판정 불가 항목만 감사자가 라벨하되 **arm 라벨 블라인드**
  상태로, 사전 규칙으로 판정 (토론으로 재정의 금지).
- **ASK/ABSTAIN 시맨틱**: ASK = 태스크 명세의 모호성에 한정된 scripted oracle 질의 (히든 grader
  상태·정답 누설 불가, 1 action + 비용 1 소모); ABSTAIN = 해당 행동 포기(태스크는 계속, 1 action
  소모). 성공 판정은 최종 grader 기준 — ASK/ABSTAIN 자체는 성공/실패가 아님.
- **H2 비용모델 (sweep으로 동결)**: wrong ∈ {3, 5, 10, 20}, ask=abstain=1, correct=0.
  H2는 **전 sweep 구간에서** 게이트 arm의 비용-성과 곡선이 무게이트 기준선을 지배할 때만 성립.
- **결과 테이블 스키마 + 분석 스크립트는 데이터 수집 전 커밋** (스크립트 해시를 Errata에 기록);
  보고는 사전등록 지표 전수 — 선택 보고 금지.

## 5. Win / Stop conditions (사전 등록 — 변경 불가)

**paired win 정의**: 같은 (템플릿, 시드) 인스턴스에서 primary 이진 성공의 차이. 동률(둘 다
성공/둘 다 실패)은 win 아님(discordant pair에서만 판정). 검정 = discordant pairs에 대한
one-sided exact McNemar(이항), **α=0.05**. H1만 confirmatory (다중비교 없음).

**WIN (재정의 EARN)** — 모두 충족:
1. **mutating 18 인스턴스에서** `weak+AIOS`가 `weak+checklist`에 paired **≥13/18** 승 + McNemar 유의.
2. **격차 해소**: `(S_AIOS − S_checklist)/(S_strong − S_checklist) > 0.5` (S = mutating 이진
   성공률; paired bootstrap 95% CI 하한 > 0). **분모 ≤ 0이면**(strong-raw가 checklist 이하)
   이 조건은 `S_AIOS ≥ S_strong` (동일 CI 규칙)으로 대체. 비용: `weak+AIOS` 총비용 CI 상한 <
   `strong-raw` 총비용.
3. **static 가드 (등가 마진)**: static 6 인스턴스에서 |Δ성공(인스턴스 수)| ≤ 1 (= 1/6 마진) AND
   unsupported final-claim rate 증가 없음. ("유의차 없음"은 증거가 아님 — 등가 검정으로.)
4. **trace 인과 규칙**: 복구로 credit되려면 로그된 게이트 거부/drift 감지/롤백 이벤트가 교정
   행동에 **선행**하고 (≤5 actions 이내), 그 교정이 실패 중이던 checkpoint를 통과로 뒤집어야 함.
   그 외는 runtime-caused로 세지 않음.

**STOP (테제 kill 또는 강등)**: `weak+AIOS`가 동일 예산에서 `weak+checklist`에 mutating paired
우위를 보이지 못하면 (13/18 미달 그리고 McNemar 비유의) → "epistemic runtime" 테제를 kill하거나
"workflow hygiene"으로 강등, 결과를 그대로 공개 (no-launder 양방향).

**H3 판정 (descriptive)**: mutating에서 `weak+memory` 성과가 `weak-raw` 대비 악화하면 ProEvolve
재현; 같은 구간에서 `weak+AIOS`가 `weak-raw` 이상이면 H3 성립.

## 6. 동결 절차 (첫 런 전 Errata에 기록할 것)

모델 ID·CLI 버전·시스템 프롬프트 해시·temperature/sampling·툴 권한·예산 어댑터 (전 arm) ·
harness 커밋 해시 · 분석 스크립트 해시 · 결과 테이블 스키마. 이 기록 이후에만 첫 런 허용.
frontier arm CLI는 버전 고정 가능해야 하며 불가하면 실행 당시 버전을 기록하고 전 인스턴스를
같은 날짜 윈도에서 실행.

## 7. 실행·보고 규칙

- subagent 하니스, arm-인스턴스 독립 실행, 시드·환경 전부 기록 (재현 가능).
- 결과 문서 `docs/AIOS_DRIFTBENCH_RESULTS_<date>.md` + 원시 데이터 커밋.
- 어떤 결과든 self-observation log와 masterplan에 반영; WIN → 배포(M4) 진행, STOP → 스코프 축소
  재정의를 founder에 제안.

## Errata (append-only)

- **2026-07-11 (화해)**: ASC-0282 WP-B(`scripts/m2_driftbench/`)가 실행 substrate로 조합됨;
  결과 행은 `experiments/driftbench/schema.py` 형식, 판정은 본 문서 §5 기준을 해시 동결된
  `experiments/driftbench/analyze.py`로 계산. ASC-0282의 17/24(tie≠win)는 그 계약 내부 완료
  바로만 유효 — 재정의 keystone 판정은 본 문서 단독. 상세:
  `docs/AIOS_DRIFTBENCH_RECONCILIATION_2026-07-11.md`. (본문 무수정 — 판정 기준 불변.)
- (v1.1 동결. v1→v1.1 델타: Codex 동결-전 리뷰 15건 반영 — 17/24→mutating 13/18 분리,
  McNemar/α/동률 규칙, 격차해소 공식+분모 규칙+bootstrap CI, static 등가 마진, trace 인과 규칙,
  캡·재시작·missing-data 동결, 실행 격리·순서 랜덤화, 비용모델 sweep, ASK/ABSTAIN·wrong-action
  정의, H3 메모리 정책, 버전·스크립트 해시 동결 절차, 감사자 블라인딩, 결과 스키마 사전 커밋.)
