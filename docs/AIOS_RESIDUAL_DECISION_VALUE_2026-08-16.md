# 세 실패의 공통 구조 — 이름, 그리고 내 주장 셋의 정정 (2026-08-16)

founder: *"실패한 지점은 council로 더 구조적이고 더 깊은 곳을 건드려봐 연구자로서."*

세 지점을 하나로 묶어 이종 패널에 걸었다.

```
(1) M1 게이트     실패 서명 0.811 bits, 전부 oracle_failed. task_id는 6.09 bits.
(2) A1/MCF-0     지속 상태가 경로 73.6% 바꾸고 검증 +0.123 올리고도 고정 라우터에 패배.
(3) 진화 런       명예의 전당 1위가 provider=mock (0.9556 vs 실제 provider 0.7955).
```

내 가설: *"세 경우 모두 결정에 쓰이는 키가 이미 결과를 결정하고, 재려던 기제는 키가
결정하지 못하는 잔차 위에서만 값을 가지는데, 세 번 다 그 잔차를 재기 전에 확인하지 않았다."*

## 0. 이 문서의 증거 등급 — 먼저

**패널은 20 substrate 중 10개만 답했고 유효 독립표 n_eff = 1.9 (rho_bar 0.474).**
따라서 아래 어느 것도 "N개가 동의했으므로 참"이 아니다. 쓸 수 있는 이유는 다르다:

| 등급 | 내용 |
|---|---|
| **내가 직접 계산해 확인** | 엔트로피 반례 (§1) |
| **1차 출처로 확인** | Shah–Peters no-free-lunch, Blackwell–Sherman–Stein (§3, §2) |
| **검증 가능하나 미확인** | Watson–Wright CPI, Candès CRT, Le Cam deficiency의 정확한 형태 |
| **미확인 채로 인용 안 함** | 나머지 |

## 1. 내가 틀렸다 — 엔트로피는 support를 제한하지 않는다

`docs/AIOS_M1_GATE_RESULT_2026-08-16.md` §2(a)는 이렇게 썼다:

> *"회수 키가 1비트 이하다. 실패 서명으로 인덱싱한 오프라인 테이블은 **최대 2행**이고…"*

**엔트로피에서 행 수를 추론한 것이고, 그 추론은 무효다.** 직접 반례를 계산했다:

```python
p = [0.5, 0.25] + [0.25/1000]*1000     # 1002개의 서로 다른 값
H = 3.991 bits                          # 1 bit보다 훨씬 큼 — 그러나 반대 방향도 성립
```

0.811 bits는 희귀 범주 수천 개와 양립한다. **행 수를 제한하는 것은 엔트로피가 아니라
관측된 support cardinality다.** 내 결론(2행)은 살아남는다 — 실제로 distinct signature를
세었더니 정확히 2개였기 때문이다(`{oracle_failed,rc=1}`:123, `{oracle_failed,rc=2}`:41).
**결론은 맞고 적어둔 근거가 틀렸다.** 서명 엔트로피는 진단 빈곤의 *징후*지 테이블 크기의
*증명*이 아니다.

두 substrate가 독립적으로 같은 지적을 했고, 나는 그 지적을 믿어서가 아니라
**한 줄로 반증 가능해서** 채택했다.

## 2. 이름 — 있다. 단 하나가 아니라 층위별로 다르다

내가 "잔차"라고 부른 것은 이미 이름이 있고, **셋이 서로 다른 명제다.**

기호: `K` = 결정 시점에 합법적으로 관측 가능한 키 · `S` = 런타임 상태·회수 결과 ·
`A` = 행동 · `Y`(또는 잠재결과 `Y(a)`) = 결과 · `U` = 실제 외부 효용.

| 층위 | 조건 | 이름 | 출처 |
|---|---|---|---|
| 분포 | `I(Y;S∣K)=0`, 즉 `Y ⊥ S ∣ K` | 조건부 예측 충분성 (K는 Y에 대한 Markov blanket) | Dawid 1979 |
| **결정(고정 U)** | `ΔU(S∣K) = V_U(K,S) − V_U(K) = 0` | **조건부 정보가치 0 (EVSI = 0)** | Bayesian decision analysis |
| 결정(모든 U) | K가 (K,S)의 garbling ⟺ 모든 사전분포·손실에서 위험 동일 | **Blackwell sufficiency / BSS 정리** | Blackwell 1951·53; Sherman·Stein |
| 정량 | 두 실험의 거리 | Le Cam deficiency | — (미확인) |

### 여기서 내가 재려던 것이 틀린 양이었다

**`ΔU = 0`은 조건부 독립보다 약하다.** `S`가 `Y`에 대한 정보를 실제로 갖고 있어도
(`I(Y;S∣K) > 0`), 그 정보가 **행동 경계를 넘기지 못하면** `ΔU = 0`이다.
예: S가 실패의 세부 유형을 알려주지만 모든 유형에서 같은 조치가 최적인 경우.

⟹ **비트를 늘리는 것으로는 부족하다.** 내가 게이트 재실행 조건에 써둔
*"서명 엔트로피 ≥ 3.0 bits, task_id로 설명 안 되는 잔차 ≥ 1.5 bits"*는
**필요조건이지 충분조건이 아니다.** 정보 잔차가 있어도 결정 잔차는 0일 수 있다.
판정량은 CMI가 아니라 `ΔU`, 즉 실제 손실에서의 짝지은 차이다.

**상위 패턴의 이름**: `evaluation-interface shortcut`.
`observable-competence ceiling`은 **현상명으로만** 보존한다 — 정리·절차와 연결할 때는
Blackwell equivalence + decision-specific conditional VoI를 본명으로 쓴다. 검증 가능성이
다르기 때문이다.

## 3. 짓지 않기로 한 것 — CMI 추정기

수백 표본 + 자연어 `S`에서 비모수 `I(Y;S∣K)`를 추정하려 했다. **취소한다.**

Shah & Peters (2020), *Ann. Statist.* 48(3):1514–1538 — 조건변수가 연속일 때
**type I error를 통제하면서 임의의 대안에 검정력을 갖는 조건부 독립 검정은 존재하지 않는다**
(no-free-lunch). 구조 가정 없이는 불가능하다. 1차 출처로 확인했다.

거기에 더해: 텍스트 표현 선택 자체가 감독정보를 누출할 수 있고, CMI 수치는 인코더 오차와
밀도추정기 오차를 구분하지 못한다.

⟹ 대안: **표현을 사전등록하고 실제 손실에 대한 증분을 재는 것.** (CPI/CRT 계열이
후보로 제시됐으나 나는 아직 확인하지 않았고, 확인 전에는 쓰지 않는다.)

## 4. 나머지 정정 셋

### (a) (1)은 "K가 충분하다"의 증거가 아니다 — 반대 방향의 두 실패다

```
fail_reason   실제 이질성을 뭉갠 계측 부족
task_id       처방을 식별자에 암기시키는 누출
```

> **의미 있는 K는 지나치게 조악하고, 풍부한 K는 배치 불가능한 식별자다.**

그리고 더 강한 판정: `task_id`가 `K`에 들어가는 순간 셀당 표본이 `N=1`이 되어
**positivity(overlap)가 깨진다**(Rosenbaum–Rubin 1983의 강한 무시가능성 조건).
그러면 arm D는 일반화 가능한 정책이 아니라 **사후 장부(ex-post ledger)**다.

⟹ 내 게이트 문서는 arm D를 *"baseline이 아니라 거의 오라클"*이라 썼다.
정확히는 **대조군 자체가 아니다** — 배치 불가능하므로 정책이 아니다.
NO-GO 판정은 내가 적었던 것보다 더 굳게 선다.

### (b) (2)는 천장의 **가능성**이지 아직 증명이 아니다

지속 상태가 고정 라우터에 진 것은 Bayes 천장일 수도 있지만,
**추정 분산 · 최적화 실패 · 계산 비용**일 수도 있다. 잉여 `S`는 정보를 안 주면서
파라미터만 늘려 일반화 오차를 **올린다** — regret 0.119 vs 0.057은 그 페널티와 양립한다.

그리고 절차적으로: *"효과를 발견하지 못했다"*는 천장 증거가 **아니다.**
상한 신뢰구간이 최소 실용 효과 `δ_min`보다 작아야 한다 — 등가성 검정(TOST) 형식.
내 kill rule은 `(C−D)`의 단측 상한 `< +5pp`로 이미 이 형태였다. **그 부분은 선다.**
서지 않는 것은 A1/MCF-0을 *확정된 천장*으로 인용해 온 것이다.

### (c) 정보적 충분성 ≠ 계산적 충분성 — memoryOS에 직접 걸린다

`S = f(K)`면 Shannon 정보는 0이다. 그러나 `f`가 비싼 검색·계산이면
**제한된 시간·모델 예산의 정책에게는 값이 있다.** 무제한 Bayes 정책에는 새 정보가 아니지만
실제 정책 클래스에는 유용한 computation이다.

⟹ **M1을 정보 잔차만으로 판정하면 memoryOS를 틀린 이유로 죽인다.**
memoryOS가 실제로 파는 것의 상당 부분은 정보가 아니라 **재계산 회피**다.
두 가설은 분리해서 걸어야 한다:

```
H_info   회수가 K에 없는 정보를 준다        → ΔU > 0, 예산 무제한에서도
H_comp   회수가 같은 정보를 더 싸게 준다     → 동일 예산에서 ΔU > 0, 예산 늘리면 소멸
```

### (d) (3)은 다른 축이다 — 내 묶음이 과했다

reward hacking은 조건부 충분성 문제가 아니라 **proxy-ordering failure / construct validity /
specification gaming**이다(Amodei et al. 2016 계열). (1)(2)와 공유하는 것은
한 층 위의 `evaluation-interface shortcut`뿐이고, **같은 통계적 명제가 아니다.**

내가 걸었던 프레임 — "세 경우 모두 같은 구조" — 는 **틀렸다.** 둘 + 하나다.

## 5. 채택 — Residual Value Gate (기제를 짓기 전에 도는 절차)

지금까지 나는 기제를 짓고 나서 잔차를 물었다. 순서를 뒤집는다.

```
Gate 0  추정량 사전 고정
        U와 손실 L · 결정 시점 · 그 시점의 합법적 K · 후보 S
        일반화 단위(call / task / family / 미래시간) · δ_min · S의 생성·호출 비용

Gate 1  키 감사 — 각 필드를 분류
        결정 전 관측치 / 결정 후 생성치 / 실험 장부 / 개체·과제 식별자 / 배치 재사용 가능 상태
        split은 task·group·time 단위. task_id가 train·test 양쪽에 있으면 일반화 검증이 아니다.
        식별가능성 확인:  Var(S∣K) > 0  그리고  Var(Y(a)∣K) > 0
        ← 같은 K가 반복 안 되거나 행동 overlap이 없으면 "잔차 0"이 아니라 "식별 불가"다

Gate 2  가장 싼 확정 실험
        같은 K의 twin/matched 사례에서 상태 접근권만 무작위화 (Z=0: π(K), Z=1: π(K,S))
        최적화기가 접근 불가능한 외부 oracle로 효용 평가 → ITT 추정
        불가능하면: 동일 예산 K-only vs K+S 학습 + task/group/time nested cross-fitting
                    + 짝지은 손실차 + δ_min에 대한 등가성 검정
```

**잔차가 0으로 나오면 세 갈래를 구분한다** (지금까지 나는 이걸 뭉갰다):

| 상황 | 조치 | 이름 |
|---|---|---|
| 잔차가 정말 0이고 배치분포 안정 | 런타임 루프 제거, 가장 단순한 K-정책. **테이블은 support가 작고 닫힐 때만** — 새 K가 오면 규칙·모델·기권이 필요하다 | 정직한 단순화 |
| 잔차는 있는데 센서가 못 본다 | 계측을 바꿔 `K' = (K, M)` | measurement/identification redesign |
| 환경·과제·피드백을 바꿔 새 변이를 만든다 | **새 사전등록, 새 baseline** | domain redesign |

> 경계: **같은 잠재 과정의 관측만 개선하면 계측 설계, 잠재 과정이나 가능한 행동·결과를
> 바꾸면 도메인 설계다.** 후자를 전자인 척하면 그게 정지규칙 교체다.

## 6. (3)에 거는 하드 불변식

mock을 블랙리스트하는 것은 증상 치료다. 구조는 이렇게 건다:

```
verified real execution = 0   ⟹   fitness가 성공 임계치를 넘을 수 없다
```

통과율·지연은 **그 게이트 이후의 2차 목적**이다. 그리고 실행 증명만으로는 부족하다 —
최적화기가 볼 수 없는 외부 oracle의 품질 판정이 필요하다. 수동 관측 하네스는
개입(intervention) 없이는 **언제나** 가장 적은 엔트로피를 쓰는 substrate로 수렴한다.

## 7. 무엇이 바뀌는가

| 문서/코드 | 변경 |
|---|---|
| `AIOS_M1_GATE_RESULT_2026-08-16.md` §2(a) | 엔트로피→행수 추론 무효. Errata 추가 (본문 보존) |
| 동 §4 재실행 조건 | 비트 문턱은 **필요조건**으로 격하. 통과 조건에 `ΔU` 등가성 검정 추가 |
| `AIOS_M1_MEMORY_EDGE_PREREG` | Errata E2 — 팔 D를 task_id 인덱싱으로 짓지 않는다(positivity). H_info/H_comp 분리 |
| A1/MCF-0 인용 | "확정된 천장" → "천장의 가능성, 등가성 검정 미실시" |
| CMI 추정기 | **짓지 않는다** (Shah–Peters) |
| 진화 루프 | 실행 증명 하드 게이트를 적합도 위에 |

---
*패널: 20 substrate 중 10 응답, n_eff 1.9, rho_bar 0.474 (`.aios/deep_panel.jsonl`).
직접 확인: 엔트로피 반례 계산 · `experiments/phase5g|h/*.jsonl` distinct signature 재계수(=2).
1차 출처 확인: [Shah & Peters 2020](https://projecteuclid.org/journals/annals-of-statistics/volume-48/issue-3/The-hardness-of-conditional-independence-testing-and-the-generalised-covariance/10.1214/19-AOS1857.full) ·
[Blackwell 1953](https://projecteuclid.org/journals/annals-of-mathematical-statistics/volume-24/issue-2/Equivalent-Comparisons-of-Experiments/10.1214/aoms/1177729032.full) ·
[Blackwell's informativeness theorem](https://en.wikipedia.org/wiki/Blackwell%27s_informativeness_theorem) ·
[Deficiency (statistics)](https://en.wikipedia.org/wiki/Deficiency_(statistics)).
관련: `docs/AIOS_M1_MEMORY_EDGE_PREREG_2026-08-14.md`, `docs/AIOS_ACTIVATION_CONDITION_2026-08-14.md`,
`docs/AIOS_SOVEREIGN_SESSION_REVIEW_2026-08-16.md`.*
