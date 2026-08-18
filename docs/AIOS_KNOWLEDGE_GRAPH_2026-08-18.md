# 지식그래프와 유기체 감사 — 산문은 이어져 있고 실행기관과 증거는 끊겨 있다 (2026-08-18)

founder: *"hdd에 robot측 subagent가 지어놓은 논문 지식그래프 옆에 네 지식 그래프도 유사한
방식으로 build해봐"* + *"전체가 유기적으로 동작하는 시스템으로 만들어내보자."*

두 지시는 하나다. **"브릭이 전부 고아다"는 엣지에 대한 주장인데, 산출물이 디렉터리에
쌓여 있는 동안에는 확인할 방법이 없었다.** 그래프는 그걸 쿼리로 만든다.

## 1. 지은 것

robot측 레이아웃(`/data/jaewon/robotics`: `index/*.db` + `ontology/ontology.jsonl` +
정직한 `failures` 테이블)을 그대로 따라 옆에 놓았다.

```
/data/jaewon/aios/
  index/aios.db          nodes 106,342 · edges 318,759 · fulltext · failures
  ontology/ontology.jsonl  concept · df · layer 분포 · top_nodes
```

| | robotics (peer) | aios (이번) |
|---|---|---|
| 노드 | 90,196 논문 | 106,342 산출물 |
| 엣지 | 178,590 인용 | 318,759 (cites/supersedes/produces) |
| 실패 기록 | 859 | 45,484 |

**엣지는 추출한 것이지 만든 것이 아니다.** 문서가 실제로 디스크에 존재하는 경로를 지목할
때만 `cites` 엣지가 생긴다. 해소되지 않는 참조는 엣지가 아니라 `failures`에 남는다 —
존재하지 않는 파일을 가리키는 문서야말로 이 그래프가 드러내려는 부패이기 때문이다.

프라이버시: `_from_desktop`/`dain`/`minyoung`/`.vault`/`.env`는 **워커에서** 배제한다.
기록기가 아니라 순회기에서 막으므로 프로세스에 들어오지 않는다.

## 2. 계측이 먼저 틀렸다 — 발표 전에 잡았다

첫 실행은 **고아 36.4%, dangling 131,594**를 보고했다. 둘 다 파서 결함이었다.

```
① 선행 점 경로를 regex가 잘라먹음   .aios/x.json → "aios/x.json" → 미해소 (85,802건)
② lookbehind가 절대경로를 통째로 차단  /home/user/... 전부 미매칭 (내가 ①을 고치며 넣은 회귀)
③ URL을 경로로 매칭                 github.com/... 를 파일로 셈
```

수정 후: **고아 11.4%, dangling 45,474.** 3배 차이다.
**계측이 답을 3배 틀리게 말했고, 그 숫자를 발표하지 않은 유일한 이유는 표본을 눈으로 봤기
때문이다.** 이번 세션에서 같은 형태가 세 번째다(엔트로피→support, arm D, 그리고 이것).

## 3. 감사 결과 — 결론이 인상과 반대다

```
nodes 106,342   edges 318,759   components 13,119
ORPHANS            12,100  (11.4%)     아무도 안 가리키고 아무것도 안 가리킴
largest component  85,977  (80.8%)     유기체 비율
dead ends          25,361              쓰이기만 하고 아무것도 구성 안 함
```

층별로 보면 **전혀 균질하지 않다:**

| 층 | n | 고아율 | 최대성분 포함 |
|---|---:|---:|---:|
| docs | 853 | **0.0%** | 99.9% |
| tests | 254 | 0.4% | 99.6% |
| scripts | 304 | 1.0% | 99.0% |
| memoryOS | 316 | 7.3% | 91.5% |
| CapabilityOS | 61 | 6.6% | 91.8% |
| uri | 2,549 | 25.4% | 65.3% |
| **experiments** | 564 | **33.5%** | 65.4% |
| **hivemind** | 10,523 | **49.0%** | 44.7% |
| **GenesisOS** | 144 | **57.6%** | 41.7% |

> **"전부 고아"는 틀렸다. 산문은 사실상 완전히 이어져 있다(docs 고아 0.0%).
> 끊겨 있는 것은 실행기관(hivemind 49%, GenesisOS 58%)과 증거(experiments 33.5%)다.**

그리고 전체 dangling의 **85%(38,672건)를 hivemind 혼자** 지고 있다. 고아율 최상위와
부패 최상위가 같은 기관이다.

이건 이 세션의 다른 모든 발견과 같은 방향을 가리킨다: **나는 쓰고 잇는 것은 잘 하고,
실행하고 증거를 쌓는 쪽이 비어 있다.** M1 게이트에서 "비트를 가진 필드가 전부 실험 장부"였던
것과 같은 병이다.

`.aios`가 전체 노드의 84%라 총계는 디스패치 패킷이 지배한다. **실질 산출물(문서·계약·
실험·스펙) 5,064개만 보면 고아 24.5%.** 이쪽이 인용할 값이다.

## 4. 배선 — 그래프가 읽히지 않으면 그 자체가 고아 브릭이다

HDD 위에 아무도 안 읽는 그래프를 두면 아이러니가 완성된다. 두 곳에 걸었다.

```
scripts/aios_graph_audit.py                   상시 점검 (.claude/AIOS_HARNESS.md에 등록)
scripts/aios_graph_audit.py --neighbors X     짓기 전에: 이걸 누가 인용하게 되나?
scripts/aios_graph_audit.py --orphans-in L    한 기관의 끊긴 산출물 열거
```

`--neighbors`가 핵심이다. **새 산출물을 짓기 전에 그래프에 물으면, 태어나면서 고아가 되는
것을 짓기 전에 안다.** 실측 예(오늘 쓴 M2 사전등록):

```
myworld/docs/AIOS_M2_MEMORY_AS_COMPUTATION_PREREG_2026-08-16.md
  <- cited by 1   [produces] commit:4d332f98
  -> cites 5      M1 게이트 · M1 사전등록 · 잔차문서 · g5_results · g6_results
```

기존 것 위에 5개로 올라탔고 아직 아무것도 그 위에 없다 — 이틀 된 노드로는 정확한 모양이다.

## 5. anti-theater

노드 수는 축적이 움직이고 **연결성은 유기체가 움직인다.** 그래서 상시 점검이 보고하는 것은
크기가 아니라 `orphan_rate`·`organism_ratio`·`dead_ends`다. 다음 판정 기준을 지금 적어둔다:

```
hivemind 고아율 49.0% → 35% 미만       실행기관이 조직에 붙었다는 증거
experiments 고아율 33.5% → 20% 미만    증거 위에 다음이 올라탄다는 증거
docs 고아율 0.0%                        유지 (여기는 이미 유기체)
```

숫자가 아니라 **행동이 바뀌어야 통과다** — 인용을 늘리려고 문서에 경로를 뿌리면 이 지표는
즉시 무의미해진다. 그래서 `cites`는 **실재하는 파일**에만 생기게 했고 dangling은 별도로 센다.

---
*빌드: `scripts/aios_graph_build.py` (105k 파일 순회, 98s). 감사: `scripts/aios_graph_audit.py`.
peer 레이아웃: `/data/jaewon/robotics/{index/papers.db, ontology/ontology.jsonl}`.
관련: `docs/AIOS_STATE_AND_ORGANISM_SYNTHESIS_2026-07-22.md`(유기체 vision),
`docs/AIOS_RESIDUAL_DECISION_VALUE_2026-08-16.md`(같은 세션의 계측-먼저-틀림 사례).*
