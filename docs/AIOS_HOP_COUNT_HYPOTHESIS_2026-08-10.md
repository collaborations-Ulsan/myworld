# hop 수 가설 — 우리가 죽인 것은 전부 2-hop이었고, 살아남은 것은 1-hop이었다

founder가 던진 논문: **arXiv:2608.07261**, *Why Knowing Both Hops Is Not Enough:
Understanding Two-Hop Generalization in Language Models* (Zhang·Wang·Wang·Wan·Luo, 2026-08-07).
원장 흡수 완료(`ideation/ledger.jsonl`, verdict=`grounded`, 축자 인용 포함).

논문의 핵심(초록 축자): *"although a model may correctly store each individual hop, it often
fails to combine them"* — 그리고 기제로 *"lower layers correctly construct these intermediate
representations, but upper layers … primarily learn to map them to outputs rather than to reason
over them."*

## 1. 왜 이게 "우리 문제"인가 — 유추가 아니라 재분할

우리 결과를 hop 수로 다시 나누면 **경계가 정확히 갈라진다.** 이건 새 실험이 아니라 기존
결과의 재기술이므로, 그 자체로는 증거가 아니라 **가설**이다.

| 기제 | 사용 시점에 요구되는 hop | 측정 |
|---|---|---|
| sandbox 거부 | **0-hop** (모델 추론이 개입하지 않음) | 작동(강제) |
| resume pack | **1-hop** (*네* 작업 상태를 그대로 제시 → 이어서 하기) | **+9.38pp · +8.54pp** |
| θ (LoRA SFT) | 2-hop (과거 경험 저장 → 새 과제에 적용) | **0.000** |
| X (컨텍스트 주입) | 2-hop (회수된 과거 → 지금 과제에 적용) | **0.000** |
| E (dispatch 노출) | 2-hop (도구 존재 인지 → 지금 해당됨을 판정 → 호출) | **0/32 호출** |
| society 인계 | 2-hop (**남의** 기록 해석 → 내 다음 행동 도출) | **−6.25pp** |
| supersede 제공 | 2-hop (수정 가능함 인지 → 지금이 그 때임을 판정) | **0/32** |

> **0·1-hop은 전부 살았고, 2-hop은 예외 없이 전부 죽었다.**

이 분할은 우리가 그동안 쓴 설명들("제공형은 안 쓰인다", "frozen model은 학습 못 한다")보다
**좁고 예측력이 있다.** 그리고 논문은 그 좁은 설명에 기제 후보를 준다: 두 hop이 **각각
정확히 저장돼 있어도** 상위층이 그것을 *추론*하지 않고 *출력으로 사상*하면 합성은 실패한다.

## 2. 정직한 경고 — 이건 아직 사후 설명이다

- **논문의 증거 범위**: 통제된 기호 환경에서 **from scratch로 훈련한 트랜스포머**다.
  프론티어 LLM이나 에이전트 과제에서 같은 기제가 돈다는 증거는 **이 논문에 없다.**
  `PRIOR: 상위층 사상-vs-추론 기제가 frozen 프론티어 모델에도 적용된다 | FALSIFY: 아래 §3`
- **사후 설명은 뭐든 설명한다.** 우리 표는 이미 아는 결과에 맞춰 그린 것이므로 증거가 아니다.
  그래서 아래를 **미리** 등록한다.

## 3. 사전등록 — 이 가설을 죽이는 방법

기존 G5/G6 하네스를 그대로 쓴다(강제 컨텍스트 사망 후 회복, McNemar).

```
arm A  기록 없음                                        (기존 대조군)
arm B  1-hop 기록: 지금 이 과제의 상태를 그대로 제시      (측정됨: +8.54pp, n=82)
arm C  2-hop 기록: 과거 에피소드의 교훈만 제시.
       내용은 실제로 유용하되, 지금 과제에 적용하려면
       "이 교훈이 지금 해당된다"는 판정이 한 번 더 필요함
```

**예측**: C − A ≈ 0 (구체적으로 |C − A| < 3pp), 그리고 B − C > 0.
**반증**: C − A 가 B − A 와 통계적으로 구별되지 않으면 hop 수 가설은 **틀렸고**,
"제공 vs 주입"이라는 우리의 기존 설명으로 돌아간다.

**교란 통제(중요)**: arm C의 내용은 arm B와 **정보량이 같아야** 한다. 교훈을 짧게 써서
C가 지면 그건 hop 수가 아니라 정보량을 잰 것이다. 사전등록 시 두 팔의 토큰 수를 맞추고,
C의 교훈이 실제로 그 과제에 유효함을 **사람이 라벨링**해 둔다(유효하지 않은 교훈이면
합성 실패가 아니라 무관 정보다).

## 4. 만약 가설이 맞다면 — 설계 규칙이 바뀐다

논문이 제안하는 해법은 **recurrent-style training**, 즉 **가중치를 바꾸는 것**이다.
우리는 프론티어 제공자의 가중치를 통제하지 못하고, θ 채널은 이미 죽었다.
⟹ **합성 능력을 올리는 길은 우리에게 닫혀 있다. 남은 레버는 요구되는 hop 수를 줄이는 것뿐이다.**

| 하지 말 것 | 대신 할 것 |
|---|---|
| "교훈"을 저장하고 모델이 적용하길 기대 | 이 상태에서의 **다음 행동 자체**를 이미 합성해 기록 |
| 검색 품질을 올려 더 좋은 과거를 찾기 | 회수 결과를 **현재 과제 문장으로 재작성**해 주입 |
| 도구 목록을 노출 | 조건이 성립하면 **host가 호출** (= 최소동작 ②) |

⟹ memoryOS 개선의 방향도 바뀐다. 소비자 리포트 §5의 *"회수가 루프 안에 없다"*는 맞지만,
루프에 넣는 것만으로는 부족하다 — **회수된 것을 1-hop 형태로 변환하는 단계**가 없으면
2-hop 팔을 하나 더 만드는 것이다.

## 5. 최소동작과의 관계

이건 최소동작을 흔들지 않고 **강화한다.** ②ACT가 host-mandated여야 하는 이유가 하나 더
생긴다: 모델에게 "이 도구가 지금 해당되는가"를 묻는 것은 정의상 hop을 하나 추가하는 일이고,
우리 데이터는 그 hop에서 0/32로 죽는다.

---
*원장 행: `ideation/ledger.jsonl` (item `src-…`, verdict `grounded`, 축자 근거 포함).
근거: `docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md`, `experiments/phase5g/G5_RESULTS.md`,
`experiments/phase5h/G6_RESULTS.md`, `docs/AIOS_WHAT_THE_OS_IS_2026-08-09.md`,
`docs/AIOS_MINIMAL_OPERATION_2026-08-09.md`. 외부: arXiv:2608.07261.*
