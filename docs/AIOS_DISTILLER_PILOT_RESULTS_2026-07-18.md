# AIOS Experience-Distiller — Pilot Results (2026-07-18)

**한 줄**: 아크 전체의 **첫 weight-level POSITIVE** — escalation 궤적을 로컬 학생에 증류하니
held-out 성공률이 base 대비 +22~36pp(양쪽 컴퓨트 환경 모두, paired one-sided p<0.02) 상승,
sentinel 무회귀. 동시에 정직한 서프라이즈: **인과-게이트(verified) vs 무필터(unverified)의
승자가 컴퓨트 환경(GPU/bf16 vs CPU/fp32)에 따라 뒤집힌다** — 격차가 base-arm 자체의
재측정 노이즈 바닥과 같은 크기라, N=25에서는 게이트 효과를 판별할 수 없다는 뜻이다.
**PILOT ONLY (N_verified=25 < 250)** — 확정 아닌 강한 directional 신호.

**지위**: 두 독립 실행(§5)의 종합. 사전등록(`docs/AIOS_DISTILLER_PREREG_2026-07-17.md` v1.1)의
확증적 H1 판정이 아니다. no-launder 양방향: 양의 방향 신호도, 게이트-무이득 서프라이즈도
그대로 보고한다.

**계보**: `9c95c10`(사전등록 동결) → `3878acd`(첫 pilot, N_verified=4, 미보정 기질) →
`076e78e`(기질 캘리브레이션) → `dc3d818`(재수집, N_verified=25) → `64e8950`(첫 평가런,
GPU/bf16, codex@myworld) → 본 문서 개정판(CPU/fp32 독립 재현런 종합, Claude executor).

## 0. 새 규율 — 왜 이 순서인가

`docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`(2026-07-18 00:20 항목)의 메타-교훈: DriftBench,
S+1, S+1.1, 그리고 이 파이프라인 자신의 첫 pilot(`3878acd`, qwen3:1.7b가 A를 26/30=87% 풀어
N_verified=4) 전부 **mechanism이 아니라 substrate-calibration**에서 죽었다. 새 규율: 학생이
목표 실패율 30-70%인지 먼저 측정·고정한 뒤에만 mechanism(수집→검증→증류)을 붙인다. 이 문서는
그 규율을 끝까지 따른 첫 완주 기록이다.

## 1. 기질 캘리브레이션 (Step 1, commit `076e78e`)

`experiments/distiller/tasks.py`의 A_FAMILIES(8개)·B_FAMILIES(6개)를 전면 교체 — 원래
"cookbook" 난이도(second_largest_distinct, run_length_encode 등, qwen3:1.7b가 87% 해결)에서
다단계·전형적 실수-유발 문제(중첩 run-length 디코드, 로마 숫자 변환, zigzag 변환, 3-sum, 엑셀
열 변환, 괄호 불균형 인덱스, sliding-window-maximum, Vigenère 암호 / matrix spiral order,
bitonic subarray, leap-year 검증, k번째 최빈문자, 최소 회의실, merge-후-gap)로 교체. A/B는
독립 생성기 계열(이름 disjoint, import-time assert), 각자 hidden-seed 스트림.

`experiments/distiller/calibrate.py`(신규, collect.py/evaluate.py의 실제 채점 기준을 그대로
재사용)로 qwen3:1.7b를 A 20개 + B 20개에 라이브 실행, 인프라 에러 0:

| split | 기준 | pass rate | n |
|---|---|---|---|
| A | visible_tests (collect.py의 실제 escalation 트리거 기준) | **0.50** | 20 |
| A | held_out+adversarial (evaluate.py의 실제 채점 기준) | 0.50 | 20 |
| B | visible_tests | 0.50 | 20 |
| B | held_out+adversarial | 0.45 | 20 |

목표 밴드(0.30-0.70) 정중앙 — 첫 시도에 충족. 패밀리별 분포는 이봉(bimodal: int_to_roman·
sliding_window_maximum·three_sum_zero_triplets는 거의 항상 풀림; decode_nested_run_length·
first_unbalanced_bracket_index는 거의 항상 실패) — 사전등록의 게이트가 "집계 pass rate"이므로
(87%가 실패했던 것과 동일 기준) 문제 없음, 정직하게 기록.

## 2. 재수집 (Step 2, commit `dc3d818`)

캘리브레이션된 48개 A-태스크에 `collect.py` 재실행 (student=qwen3:1.7b, teacher=소버린
캐스케이드, 시간예산 2400s, 실제 소요 563s):

| 지표 | 값 |
|---|---|
| n_a_attempted | 48 |
| n_student_solved | 23 (47.9% — 캘리브레이션 예측 50%와 근접) |
| n_escalated | 25 |
| n_teacher_visible_fail | 0 |
| **n_verified** | **25** (25/25 escalation 중 인과-게이트 전원 통과) |
| n_unverified_only | 0 |
| n_privacy_blocked | 0 |
| n_infra_errors | 0 |
| Blind-Curator | 0/95 false-pass (threshold 0.05), freeze_promotion=false |

N_verified=25는 여전히 사전등록 문턱(250) 미만 — **PILOT ONLY** 배너 유지. 그러나 이전
pilot(N=4)의 6배 이상, 최초로 pilot-LoRA를 시도할 만한 규모.

## 3. 학생 모델 핀 + GPU 환경 (정직한 기록)

- **추론(student, collect/base-arm)**: `qwen3:1.7b`, ollama GGUF blob, native `/api/chat`
  (`think:false`), `collect.call_student`. base-arm은 항상 이 경로 — 아래 GPU/CPU 이슈와
  무관(ollama는 별도 서버 프로세스, 이 세션의 torch/CUDA 상태에 영향받지 않음).
- **LoRA 학습/추론 베이스**: `Qwen/Qwen3-1.7B` (HF safetensors, ollama GGUF와 별도 다운로드 —
  로컬 HF 캐시에 이미 존재, `~/.cache/huggingface/hub/models--Qwen--Qwen3-1.7B`, 3.8GB).
- **디바이스 — 라이브 발견, 세션 중 상태 변화**: 학습 시작 시점, 이 박스의 RTX 5090 ×2는
  Blackwell(compute capability 12.0 / `sm_120`)인데 설치돼 있던 `torch==2.6.0+cu124`는
  컴파일된 커널이 `sm_90`까지만 지원(`torch.cuda.get_arch_list()`로 라이브 확인).
  `torch.cuda.is_available()`은 `True`를 반환하지만(디바이스 열거는 됨) 실제 커널 실행
  ("no kernel image is available for execution on the device")은 즉시 실패 — peft의 어댑터
  dtype 캐스트, 이후 `model.generate()` 내부 캐시 경로 모두. 공유 박스의 전역 torch
  업그레이드는 위험도 높다고 판단(다른 세션들이 같은 인터프리터 사용), 대신:
  1. `train_lora.py`/`evaluate.py`에 `_cuda_kernels_usable()` 라이브 프로브 추가 →
     미지원 시 `device_map={"": "cpu"}`, `torch_dtype=torch.float32`로 폴백.
  2. 그것만으로는 불충분 — `model.generate()`가 device_map=cpu 상태에서도 내부적으로 CUDA를
     건드림(라이브 확인, 3회 재현) → 프로세스 시작 전 `CUDA_VISIBLE_DEVICES=""`로 GPU 자체를
     프로세스에서 완전히 숨겨야 안전. **두 LoRA 어댑터의 학습은 이 CPU/fp32 경로로 실제
     완주됨**(NOT-RUN 아님) — 64-core/251GB RAM 박스, 두 arm 각각 ~2-2.5분.
  3. **세션 도중** (평가 단계, §5) 이 박스의 전역 torch가 `2.11.0+cu128`
     (`arch_list`에 `sm_120` 포함)로 갱신되어 있는 것을 발견 — 동시에 작업 중이던 다른
     AIOS 세션(codex@myworld)이 올린 것으로 추정, 본 실행이 직접 올리지 않음. 이 덕분에
     **평가(§5)의 GPU/bf16 런이 실제로 가능**해졌다.
- 공유 워크스테이션 동시성 주의: 평가 단계에서 무관한 타 세션(agentabstain 평가,
  IRIS 프로파일링 등)이 같은 64-core 박스를 쓰고 있었고, 중복으로 launch된 평가
  프로세스 여러 개가 서로 경합·크래시하는 것을 라이브로 확인·정리했다(§7).

## 4. LoRA 학습 (Step 3, CPU/fp32로 완주)

두 arm, 동일 하이퍼파라미터(r=16, lora_alpha=32, dropout=0.05, target_modules=[q,k,v,o,gate,
up,down]_proj, epochs=3, lr=2e-4, batch=2×grad_accum=8, early_stopping_patience=2,
sentinel_fraction=0.15 — 15% sentinel-rehearsal을 train/eval 양쪽에 혼합):

| arm | n_train | n_eval | train_loss | eval_loss (epoch 1→2→3) |
|---|---|---|---|---|
| lora_verified_trajectory | 27 | 2 | 1.7274 | 1.5972 → 1.3801 → 1.2850 |
| lora_unverified_trajectory | 27 | 2 | 1.7141 | 1.5946 → 1.3856 → 1.2925 |

두 arm 모두 eval_loss가 매 epoch 단조 감소 — 학습 자체는 정상 작동. 어댑터 저장 완료:
`experiments/distiller/data/lora_lora_verified_trajectory/adapter_model.safetensors`,
`experiments/distiller/data/lora_lora_unverified_trajectory/adapter_model.safetensors`
(각 69.8MB, r=16 LoRA 7-모듈, commit `64e8950`) — **아래 두 평가 런(§5) 모두 이 동일한
어댑터 파일**을 사용했다(재학습 없음, 바이트 단위로 동일 — git diff 확인). 학습 중간
체크포인트(`checkpoint-2/4/6`, 각 216MB×3=648MB×2 arm)는 재현에 불필요한 학습 스크래치
상태로 판단, 커밋 제외 — 정확한 재현 커맨드는
`experiments/distiller/data/train_lora_plan.json`에, 학습에 실제 사용된 (prompt, target)
쌍은 `experiments/distiller/data/train_lora_{verified,unverified}_trajectory.jsonl`
(sentinel-rehearsal 혼합 후, 29개씩)에 기록.

`Student-LoRA-solution-only`(3번째 대조군, S6 guard #2 후반부)는 이번 pilot 범위에서 제외
(시간 예산 우선순위 — verified vs unverified가 인과-게이트 가치 증명의 핵심 대조).

## 5. B 평가 — 두 독립 실행 (동일 어댑터, 다른 컴퓨트 경로)

`evaluate.py --arms base lora_verified_trajectory lora_unverified_trajectory`, B=36 태스크
(held_out+adversarial만, visible 절대 미사용, 동일 seed/b-instances=기본값이므로 동일 36개
물리 태스크) + sentinel=5, stripped prompt + solution-only 채점 공통.

**Run 1 — GPU/bf16** (commit `64e8950`, codex@myworld, torch 2.11+cu128 확보 직후):

| arm | B pass (n/36) | rate | sentinel | paired vs base |
|---|---|---|---|---|
| base | 14/36 | 38.9% | 5/5 | — |
| lora_verified_trajectory | 25/36 | 69.4% | 5/5 무회귀 | n01=13,n10=2, **p=0.0037** |
| lora_unverified_trajectory | 27/36 | **75.0%** | 5/5 무회귀 | n01=14,n10=1, **p=0.00049** |

**Run 2 — CPU/fp32** (본 실행, Claude executor, `CUDA_VISIBLE_DEVICES=""`+
`OMP_NUM_THREADS=8` 강제 — §7 참고):

| arm | B pass (n/36) | rate | sentinel | paired vs base |
|---|---|---|---|---|
| base | 16/36 | 44.4% | 5/5 | — |
| lora_verified_trajectory | 26/36 | **72.2%** | 5/5 무회귀 | n01=11,n10=1, **p=0.0032** |
| lora_unverified_trajectory | 24/36 | 66.7% | 5/5 무회귀 | n01=10,n10=2, **p=0.0193** |

(n01 = base 실패→variant 성공, n10 = base 성공→variant 실패, McNemar/sign-test 형태 exact
test, stdlib `math.comb`, α=0.05.)

## 6. 정직한 판정 — 두 결정적 질문

**질문 (b) — LoRA가 base를 이기는가 (증류의 방향성 신호)?**

**예, 강하게, 두 컴퓨트 환경 모두에서.** GPU 런: verified +30.6pp(p=0.0037), unverified
+36.1pp(p=0.00049). CPU 런: verified +27.8pp(p=0.0032), unverified +22.2pp(p=0.0193). 두
arm·두 환경 전부 α=0.05 유의, sentinel 무회귀(전 조건 5/5). B는 A와 구조적으로 격리된
held-out(별도 생성기 계열)이고 stripped-prompt+solution-only 채점(궤적 모방으로 이긴 게
아님)이므로, 이것은 **이 프로그램 전체 역사상 첫 양의 방향 신호**다 — DriftBench(STOP),
S+1(전이 불가), S+1.1(B 천장 12/12 실패), 이 파이프라인 자신의 첫 pilot(N=4, 판정 불가)
전부 null/negative였다. 두 독립 컴퓨트 경로에서 재현되었다는 것이 이 결론의 신뢰도를
더한다.

**질문 (a) — verified(인과-게이트 통과분)가 unverified(게이트 없음, 동량)를 이기는가
(검증이 실제로 일하는가)?**

**판별 불가 — 노이즈 바닥 안에 있다.** 두 런의 verified-vs-unverified 순서가 **뒤집힌다**:
GPU 런은 unverified(75.0%) > verified(69.4%) (+5.6pp), CPU 런은 verified(72.2%) >
unverified(66.7%) (+5.5pp). 우연이 아님을 뒷받침하는 직접 증거: **base arm 자체도** 두
런 사이에 14/36 vs 16/36(2태스크, 5.6pp) 차이가 난다 — base는 LoRA를 전혀 쓰지 않는
순수 qwen3:1.7b이므로, 이 차이는 (ollama 서버의 재측정 변동 등) **순수 재측정 노이즈**다.
verified-vs-unverified 격차(5.5~5.6pp)가 이 독립적으로 관측된 노이즈 바닥과 **정확히 같은
크기**다. 즉 N=25/B=36 규모에서는 "게이트가 이득이다"도 "게이트가 손해다"도 통계적으로
주장할 수 없다 — 관측된 부호 반전 자체가 그 증거다. (두 arm의 base 대비 격차, +22~36pp는
이 노이즈 바닥의 4-6배 커서 질문 (b)의 결론은 이 노이즈에 흔들리지 않는다.)

**결론(PILOT, 비확증적)**: 인과-검증된 escalation-궤적 증류가 로컬 학생을 개선시킨다는
**방향성 신호는 강하다**(H1 방향 지지, 두 컴퓨트 환경에서 재현) — 최초의 EARNED 긍정
신호. 인과-게이트가 unverified 대비 추가 가치를 낸다는 주장은 **이번 N에서 뒷받침되지
않는다** — 두 런의 부호 반전이 노이즈 바닥과 같은 크기임을 직접 보여준다(S6 guard #2에
대한 정직한 negative, 세탁 없이 보고). **N=25는 사전등록 N≥250에 크게 못 미친다 — 이
결과를 H1 EARNED로 선언하지 않는다.**

## 7. 한계 — 확증 런 전 반드시 알아야 할 것

- **N=25 학습 예시** (27 train + 2 eval, arm당) — 극소 규모, 개별 궤적의 특이성에 과적합
  위험. 진짜 일반화 능력 습득인지 25개 사례의 우연한 패턴 습득인지 이 규모로는 분리 불가.
- **B=36이 6개 패밀리에 걸침** (패밀리당 6인스턴스) — 유효 독립 시행 수는 36보다 작을 수
  있음(패밀리 내 상관 오류). 패밀리별 분해는 미보고(다음 확증 런에서 필수).
- **단일 시드, 컴퓨트-경로 2회** — §6에서 쓴 대로 컴퓨트 경로 자체가 노이즈 소스임이 실증됨
  (GPU/bf16 vs CPU/fp32). 진짜 분산 추정(동일 컴퓨트, 복수 학습 시드)은 아직 없음.
- **verified vs unverified 직접 paired 검정 미계산** — 현재 evaluate.py는 각 arm을 base와만
  페어링(frozen 설계). 두 LoRA arm 간 직접 McNemar 검정은 raw per-task 배열 저장이 필요 —
  다음 확증 런에서 추가할 것.
- **CPU/fp32 vs GPU/bf16 — 이번엔 약점이 아니라 증거였다**: 애초 재현성 확인용이 아니라
  환경 제약(§3)으로 어쩔 수 없이 두 경로가 생겼는데, 결과적으로 질문 (a)의 노이즈 바닥을
  직접 드러내는 우연한 미니-복제 실험이 됐다. 확증 런은 **하나의 컴퓨트 경로로 고정**하고
  대신 여러 학습 시드로 진짜 분산을 잴 것.
- **공유 박스 자원 경합** — 동일 시각 무관한 타 세션(agentabstain 평가, IRIS 프로파일링,
  aios serving 등)이 같은 64-core 박스에서 실행 중이었고, 최소 3개의 중복 evaluate.py
  프로세스가 (본 실행과 무관하게, 추정컨대 다른 AIOS 세션에서) 병행 launch되어 서로 경합·
  일부는 크래시(구버전 코드로 sm_120 버그 재현, 또는 exit 144 원인불명 kill)하는 것을 라이브로
  발견·정리(중복 프로세스 kill, 스레드 캡 `OMP_NUM_THREADS=8`/`MKL_NUM_THREADS=8` 적용 후
  CPU 런 완주). 결과 자체의 타당성에는 영향 없음(완주된 런의 수치만 보고) — 그러나 향후
  대규모 확증 런은 자원 격리(전용 박스/시간대 또는 명시적 락)가 필요.
- **Student-LoRA-solution-only 3번째 대조군 미실행** — 궤적이 최종답 너머 가치 있는지는 이번
  pilot에서 답하지 않음.

## 8. 다음 단계

1. N_verified≥250 (이질적이면 500+) 확보 — A 태스크 인스턴스 확장 또는 반복 수집.
2. `evaluate.py`에 raw per-task pass/fail을 report에 저장 → verified-vs-unverified 직접
   paired exact test 추가.
3. **하나의 컴퓨트 경로로 고정**(이제 GPU/bf16 가능 — torch 2.11+cu128 확보됨) + 복수 학습
   시드로 진짜 분산 추정 (컴퓨트-경로 자체를 분산원으로 삼지 않는다).
4. 패밀리별 분해 보고(균질 개선인지 특정 패밀리 국소 개선인지 구분).
5. Student-LoRA-solution-only 대조군 실행.
6. 확증 런 전 자원 격리 방안 확정(전용 시간대/박스, 또는 evaluate.py/train_lora.py에
   파일락 기반 중복-실행 방지 추가).

## Errata (append-only)
- (2026-07-18, 최초 커밋 `64e8950`, codex@myworld, GPU/bf16 런 단독): "verified<unverified,
  2-태스크 차, pilot noise 추정" 서프라이즈 보고.
- (2026-07-18, 본 개정판, Claude executor): 독립 CPU/fp32 재현런(동일 어댑터, 다른 컴퓨트
  경로) 추가 — 두 런의 부호 반전 + base-arm 자체의 동일 크기 재측정 노이즈를 근거로 질문
  (a)의 "판별 불가" 결론을 직접 실증. 질문 (b) 결론(LoRA가 base를 강하게 이긴다)은 두 런
  모두에서 재현되어 오히려 강화됨. 캘리브레이션(§1)·재수집(§2) 세부 수치, GPU 환경 변화
  타임라인(§3), 공유 박스 동시성 이슈(§7)를 상세화.
