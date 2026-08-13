# 사전등록 — M1 memoryOS 엣지 (5팔)

**상태: 사전등록. 데이터를 보기 전에 동결한다.** 이 문서를 결과 이후에 고치면 그것은
정지규칙 교체이고, 우리는 그 판정을 GPT §19에 대해 이미 내렸다(닫힌 결정의 재개봉).
개정은 append-only Errata로만.

## 0. 왜 이 실험인가

M0는 켜졌다(영수증 49건, 되돌림 10건, 루트 독립 재계산 일치). M1은
*"같은 술어가 반복 발화하고 무행위 대조군을 이긴다"*를 요구한다. 첫 술어 후보는
`VERIFY.fail → host가 memoryOS 회수 → 같은 소유자의 새 시도`다.

그런데 이 실험은 **두 개의 서로 다른 반론**을 동시에 통과해야 한다.

## 1. 통과해야 할 두 반론

**(a) 호출 ≠ 사용** (GPT, 2026-08-13). operator가 32/32 호출되고 primary가 출력을
무시하면 영수증을 입은 새로운 0/32다. ⟹ 결합(§2c)과 전달(§2d)이 영수증에 필요하다.

**(b) 활성화가 offline-optimal을 이기는가** (A1/MCF-0, 2026-08-13). 지속 상태가
경로를 73.6% 바꾸고 검증을 +0.123 올리고도 **고정 라우터에 졌다**(regret 0.119 vs 0.057).
⟹ sham을 이기는 것으로는 부족하다. **정적 정책을 이겨야** 한다.

**(c) 이득이 이 기록 때문인가, 기록이라는 형식 때문인가** (A1 K2). reset lift +0.082인데
shuffle −0.019 ⟹ 저기서 이득은 generic 캘리브레이션이었다. **우리 G5/G6에는 shuffle 팔이
없었다.** `+8.54pp`가 *이 아크의 기록* 때문인지 *기록의 형식* 때문인지 우리는 모른다.

## 2. 팔 (5개)

```
A  no edge          회수 호출 없음
B  sham edge        동일 호출·지연·토큰량, 스키마 일치, 정보 없음
C  real edge        이 실패에 대해 회수된 accepted memory
D  offline policy   실패 서명 → 고정 조치 테이블. 런타임 회수 없음
S  shuffled edge    C와 동일 형식이나, 다른 아크에서 회수된 pack
```

**주 대비는 C vs D.** 부차 대비 C vs B(정보의 값), C vs S(이 기록인가 형식인가), B vs A(호출 자체의 overhead).

- **C ≤ D** ⟹ 우리가 산 것은 활성화가 아니라 좋은 테이블이다. 강제할 대상을 회수에서
  테이블로 옮기고, memoryOS 엣지는 기본 경로에서 제거한다.
- **C ≈ S** ⟹ 이득은 stream별 기억이 아니라 형식이다. `+8.54pp`의 해석을 그에 맞게
  좁히고, "이 아크의 기록"이라는 표현을 제품 문구에서 뺀다.

## 3. 정직성 게이트 (풀런 전에 통과해야 함)

A1.5가 하는 것과 같은 형태 — **가정하지 않고 먼저 측정한다.**

> 회수된 pack이 **실패 서명만으로 유도 불가능한** 정보를 담고 있는가?

파일럿: 라벨된 실패 20건에서, 오프라인 테이블(D)이 C의 pack 내용을 몇 % 재현하는가.
**재현율 ≥ 0.8이면 풀런하지 않는다** — 그건 hidden state가 없다는 뜻이고,
`observable-competence ceiling`이 이미 답을 말한 것이다. 그 자체가 finding이다.

## 4. 실행 유효성 (하나라도 위반하면 결과는 null이 아니라 VOID)

```
trigger 발생 시 invocation                 = 100%
edge.output_digest ∈ act.context_components = 100%   (§2c)
act_input manifest가 입력을 타일링          = 100%   (§2d)
superseded/retracted memory 주입            = 0
모든 팔의 모델 호출·시도 예산               동일
B/S가 C와 토큰량·지연에서 구별 불가         (사전 측정)
```

## 5. 효능 kill rule

```
C ≤ D  또는  (C−D)의 단측 95% 상한 < +5pp   ⟹ memory edge 폐기
C ≤ B                                        ⟹ 정보에 값 없음, 폐기
C ≈ S (|C−S| < 3pp)                          ⟹ 이득은 형식. per-arc 주장 철회
```

가치 주장은 더 엄격하게: `(C−D)`의 단측 95% **하한 > 0** 이고
verified completion당 비용이 D보다 나빠지지 않을 것.

그 사이의 양수지만 불확실한 결과는 **기본값 OFF · 성능 주장 없음**.

## 6. 즉시 정지 (효과와 무관)

retracted/superseded 항목 주입 · 다른 아크의 private record 누출 · memory pack
때문에 금지된 행동 실행 · freshness tip 불일치 상태에서 주입.

## 7. `myworld_computation` A1.5와의 관계 — 정직하게

두 실험은 **같은 질문**을 묻는다: 런타임 발견이 오프라인 테이블을 이기는가.
대응은 `M ↔ C`, `B1-family ↔ D`.

**그러나 두 결과를 독립 확증으로 세지 않는다.** 가설과 설계 어휘가 공유되고(우리가
대화에서 함께 만들었다), 우리 측정으로 이종 패널의 유효 독립표는 16 substrate에서
**1.75**였다. 독립인 것은 **데이터와 도메인**이다 — 라우팅 vs 에이전트 과제 복구.

⟹ 두 실험이 같은 방향으로 나오면 그것은 **한 가설이 두 도메인에서 살아남았다**는 뜻이지
두 번 확인됐다는 뜻이 아니다. 반대로 **엇갈리면** 그게 더 값진 정보다 —
`observable-competence ceiling`이 도메인 의존이라는 뜻이므로.

---
*근거: `docs/AIOS_ACTIVATION_CONDITION_2026-08-14.md`,
`docs/AIOS_MINIMAL_OPERATION_2026-08-09.md`, `spec/aios-seam-v0.md` §2c·§2d,
`experiments/phase5g/G5_RESULTS.md`, `experiments/phase5h/G6_RESULTS.md`,
`docs/MEMORYOS_CONSUMER_REPORT_2026-08-09.md` §8·§9.
대응 실험: `myworld_computation` A1.5 prereg (commit 2f13fcb).*

## Errata (append-only)

*(없음)*
