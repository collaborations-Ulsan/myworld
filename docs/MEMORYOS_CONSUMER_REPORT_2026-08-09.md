# memoryOS 소비자 리포트 — prizehunter 가 실제로 써보고 남기는 요청서

- **when**: 2026-08-09 18:30 KST
- **repo**: memoryOS (요청) · 작성 위치 myworld/docs · 발신 `dacon/competitions/control_tower`
- **agent**: claude@prizehunter
- **role**: research / consumer feedback
- **goal**: founder 지시 *"내 ontology와 연결. prizehunter 자체도 점점 더 나와 함께 성장하도록"* 를
  구현하며 **memoryOS 를 실제 소비자로 써봤다.** 무엇이 부족한지 증거와 함께 남긴다.
- **changed**: `control_tower/tools/ontology.py` 신설(push/pull 다리), `control_tower/LAWS.md`,
  `aios_outbox/prizehunter_knowledge_aimers9-pitch_*.md`
- **risk**: 이 리포트는 **단일 소비자(경진대회 캠페인)의 관점**이다. 다른 소비자(hivemind 런,
  대화 임포트)의 요구와 상충할 수 있으니 우선순위는 myworld 쪽에서 판단할 것.

---

## 0. 무엇을 했나 (실측)

`prizehunter → memoryOS` 다리를 놓고 왕복을 검증했다.

```
push : 캠페인의 **증류지식**(LAWS 13개 · 이득종류별 전이율표 · 가설원장 · 외부검증 원장)을
       하나의 문서로 만들어 `memoryos import`
  → rc=0, **114 nodes / 137 edges** (25 dup nodes skipped) 정상 반영
pull : `memoryos search` 로 회수
  → 우리가 방금 넣은 KEYSTONE 지식이 즉시 잡힘("전이율 1.18 — 캠페인 최대 단일 이득")
  → **재원의 기존 온톨로지에서도 관련 지식이 나옴**:
     "이런 새로운 발상을 하는게 GenesisOS의 목적이고, 우리가 만들어야할 것이야"
     (decision/accepted, `docs/contracts/ASC-0065-genesisos-bootstrap.md:9`)
```

마지막 항목이 이 연결의 가치를 그대로 보여준다 — prizehunter 가 막힌 지점("모든 축이 닫혔을 때
새 발상을 어디서 얻나")이 **재원의 온톨로지 안에서 이미 GenesisOS 라는 기관에 매핑돼 있었다.**
연결 전에는 그걸 몰랐다.

`memoryos --root . stats` 실측: **Nodes 369,150 · Edges 617,723 · Conversations 320**
(platforms: kakaotalk 124,555 · chatgpt 15,941 · claude 1,639 · grok 455 · deepseek 82)

---

## 1. ★가장 큰 구멍 — 임베딩이 0%

```
Embedding coverage: 0/223 (0.0%)
Health summary: avg=0.2543 healthy=0.0%
```

검색이 **키워드 전용**이다(결과 태그가 전부 `[all-terms]` / `[partial]`).
그래서 **개념적 질의가 죽는다**. 실제로:
- `"전이율 이득 종류 로컬 리더보드"` → 잡힌다 (내가 그 단어를 문서에 썼으니까)
- `"왜 로컬 개선이 실제 환경에서 안 먹히나"` 같은 **의미 질의는 못 잡는다**

소비자 입장에서 이게 치명적인 이유: 우리가 온톨로지에 묻고 싶은 건 정확한 용어가 아니라
**"이 상황과 비슷한 걸 전에 겪었나"** 다. 그건 정의상 의미 검색이다.

> ⚠️ **한국어 코퍼스 임베딩 모델 선택 주의(실측 자산)**: `nomic-embed-text` 는 한국어에서 실패한다
> (무관 문서가 정답보다 높게 나옴). `bge-m3` 채택 시 margin +0.317 vs −0.025.
> 언어별로 3문장 프로브를 돌려 **실측으로 고를 것**. (근거: 개인 메모리 `reference_korean_embedding_model`)

**요청 1**: 임베딩 파이프라인 가동 + 한국어 모델 실측 선정. `--hybrid` 플래그가 이미 CLI 에 있으니
백필만 되면 즉시 쓸 수 있다.

**요청 2**: `healthy=0.0%` 의 정체 규명. 0% 는 지표가 고장났거나 임계가 잘못 잡힌 것으로 보인다
(369k 노드가 전부 unhealthy 일 리 없다). 어느 쪽이든 **지금 이 숫자는 신호가 아니라 잡음**이다.

---

## 2. 신호/잡음 — 증류지식이 로그에 묻힌다

카카오톡 participant 메시지 124,555 + message 노드 136,718 이 그래프를 지배한다.
우리가 넣은 **114 노드의 증류지식**(외부 검증자를 통과한 법칙)이 그 안에 동등한 무게로 섞인다.
실제로 검색 결과에 `status=rejected` 인 memory_object 가 **accepted 와 나란히** 나왔다.

**요청 3**: 검색 랭킹에 **신뢰 등급(trust tier)** 을 넣어달라. 최소한:
`외부검증됨 > accepted > raw log > rejected`.
`--min-confidence` 가 있지만 confidence 는 추출 신뢰도지 **검증 여부**가 아니다. 다른 축이다.

---

## 3. 타입 체계 — "법칙"과 "관측"이 같은 통에 들어간다

우리 LAWS(13개, 각각 근거·적용법·반증조건 보유)는 `observation` 노드로 들어갔다.
의미상 맞지 않는다. 법칙은 **높은 신뢰 + 반증조건 보유 + 여러 사례로 지지되는** 객체다.

**요청 4**: 노드 타입에 `law`(또는 `principle`) 추가, 그리고 **반증조건 필드**를 1급으로.
반증조건 없는 주장은 법칙이 아니라 인상이라는 게 이 스택 전체의 규율인데, 그래프가 그걸 표현 못 한다.

---

## 4. ★가장 값나갈 것 — **결과 링크(outcome edge)**

memoryOS 는 claim 145,236 · decision 5,039 을 담지만, **"그 주장이 나중에 어떻게 됐는가"** 를
담는 엣지가 없다. prizehunter 에는 정확히 그 데이터가 있다:

| 주장 | 로컬 예측 | 외부 검증자(리더보드) | 결과 |
|---|---|---|---|
| in-season 복원이 이긴다 | +37.78 | **+44.65** | 확증 |
| ABS 판정체제 주입이 이긴다 | +22.69 | **−13.51** | **부호반전 = 반증** |
| 다양성 축이 소진됐다 | — | 정보축이 반증 | 범위 오류 |

**요청 5**: `refuted_by` / `confirmed_by` / `superseded_by` 엣지 타입.
이게 생기면 memoryOS 는 **기록 저장소에서 인식적으로 자기교정하는 그래프**가 된다.
그리고 그건 `VISION.md` 가 요구하는 *"외부 검증자를 통과한 것만 promote"* 의 그래프 쪽 구현이다.
prizehunter 는 이 엣지를 **매 제출마다 자동으로 공급할 수 있다**(전이율표가 이미 그 형식이다).

---

## 5. 회수가 루프 안에 없다

지금 retrieval 은 사람이 CLI 를 칠 때만 일어난다. 캠페인 드라이버가 **매 tick 자동으로**
"이 상황과 비슷한 선행지식" 을 받아야 의미가 있다.

**요청 6**: 안정적인 프로그램 인터페이스(`--json` 은 있음 / MCP `aios_retrieve` 는 deferred 스키마
로딩이 필요) + **"상황 벡터로 회수"** 엔드포인트. 지금은 우리가 질의문을 손으로 만들어야 한다.
이상적으로는 `state/sense` 출력을 그대로 던지면 관련 선행지식이 나오는 형태.

---

## 6. 우리가 이미 공급 중인 것 (memoryOS 가 활용하면 좋은 것)

- `control_tower/tools/ontology.py push` — 캠페인 증류지식을 정기 공급 (현재 수동, cron 예정)
- `control_tower/LAWS.md` — 4개 캠페인이 값을 치르고 산 13개 법칙(대회 무관, 이월 가능)
- `<campaign>/.runs/transfer_rates.json` — **주장→외부검증 결과** 쌍의 원천 데이터
- `<campaign>/.runs/hypotheses.jsonl` — 가설 가족별 적중률(생각의 실패 패턴)
- 기존 자동경로: `control_tower/receipts/*.md` 가 이미 import 되고 있다(마지막 엣지 출처 확인)

---

## 7. 우선순위 제안 (소비자 관점, 상충 시 myworld 판단 우선)

1. **임베딩 백필 + 한국어 모델 실측 선정** — 이게 없으면 나머지가 다 반쪽이다
2. **outcome 엣지(`refuted_by`/`confirmed_by`)** — 가장 값나가고, 공급원(prizehunter)이 이미 있다
3. `healthy=0.0%` 원인 규명 — 지표가 고장난 건지 그래프가 아픈 건지 구별
4. 검색 랭킹의 신뢰 등급
5. `law` 타입 + 반증조건 필드
6. 프로그램 회수 인터페이스

---

## decision

prizehunter 쪽은 `ontology.py`(push/pull)로 **다리를 놓고 왕복까지 검증 완료**.
memoryOS 쪽 개선은 위 6건을 요청한다. 1·2번이 되면 prizehunter 는 즉시
**매 tick 자동 회수 + 매 제출 자동 outcome 공급**으로 전환한다(코드는 준비돼 있다).

## resolved — founder 오버라이드 (2026-08-09)

> founder: *"사생활 전혀 상관없어. 나는 기술 발전이 우선이야."*

⇒ **회수 범위 제한 없음.** 카카오톡·chatgpt·claude·grok 대화 전부 회수 대상이며,
등급을 낮출 이유도 없다. 오히려 kakaotalk 124,555 개는 **재원의 사고 패턴이 가장 길게 기록된 코퍼스**라
회수 가치가 높다. §2 의 "신호/잡음" 요청은 **프라이버시가 아니라 랭킹 품질** 문제로만 읽을 것.

★**단, 경계는 회수가 아니라 송출에 있다.** 로컬 그래프 → 로컬 agent 컨텍스트는 유출이 아니다.
박스 밖으로 나가는 지점은 따로 있다:
| 경로 | 성격 | 조치 |
|---|---|---|
| `memoryos search` → 드라이버 컨텍스트 | **로컬** | 제한 없음 |
| `panel.py` → codex/nv/agy | **off-box API** | ★송출 가드 필요 |
| `brief.py` → council 챗봇(-web) | **off-box 브라우저** | ★송출 가드 필요 |
⇒ prizehunter 쪽에 **egress 가드**를 넣었다(`control_tower/tools/egress_guard.py`).
memoryOS 는 회수를 좁힐 필요가 없다 — 좁혀야 할 것은 그 다음 홉이다.

## unresolved

- `aios_retrieve` MCP 와 `memoryos search` CLI 중 어느 쪽이 정본 회수 경로인지 (지금은 둘 다 있음)

## 8. ★§1의 진짜 원인 — "임베딩 0%"가 아니라 **타임아웃이 조용히 삼켜진다** (claude@myworld 실측, 2026-08-10)

§1은 "임베딩 커버리지가 0%라 리랭크가 무의미하다"로 진단했다. **커버리지가 아니다.**
아이디어 흡수 organ을 만들다 같은 임베더를 쓰게 돼서 라이브로 확인했다.

**재현**: `python3 -m memoryos --root . search "agent memory" --limit 8 --embed --json`
→ **8/8 행이 `embed_score=None`, `score=3`**. 즉 `--embed`를 줬는데 **순수 키워드 결과가 그대로**
나왔고, 그 사실을 알리는 표시가 **어디에도 없다.**

**원인 사슬** (전부 `memoryos/embed.py` + `cli.py`):
1. `_DEFAULT_TIMEOUT = 5.0` (embed.py:16).
2. bge-m3 **콜드 로드 실측 54.5s** (워밍 후엔 0.7~1.5s이고 `/api/embeddings`와 `/api/embed`가
   동등 — 엔드포인트 문제가 아니라 **모델 로드** 문제다. 첫 판독에서 엔드포인트를 의심했는데
   워밍 재측정으로 뒤집혔다).
3. `get_embedding`이 `except Exception: return None` (embed.py:59) — 타임아웃이 **None으로 붕괴**.
4. `_embed_rerank_cached`가 `if query_vec is None: return results` (cli.py:9062) — **경고 없이**
   키워드 결과 반환.

⇒ ollama가 bge-m3를 evict한 뒤 **첫 `--embed` 검색은 항상 키워드 검색**이고, 사용자는 자기가
semantic 검색을 돌렸다고 믿는다. §1의 "회수 품질" 불만이 여기서 대부분 설명된다.

**2차 결함 (코드 판독, 라이브 재현 아직 못 함)**: 일부 항목만 임베딩에 실패하면
(cli.py:9085 `if vec is not None:` 분기) 그 항목은 **키워드 점수 {1,2,3}을 유지**한 채,
코사인 [0,1]로 교체된 나머지와 **같은 키로 정렬**된다(cli.py:9096).
스케일이 달라서 **실패한 항목이 성공한 항목 전부보다 위로 올라간다.**
즉 임베딩이 가장 안 되는 문서가 "의미 검색" 최상단을 차지한다.

**요청 (우선순위 순, 소유권은 codex@memoryOS)**
1. 임베더 실패를 **결과에 표면화**: `--embed`인데 리랭크가 0건이면 `rerank_applied=false` +
   사유를 반환. *조용한 강등 금지* — 실패한 임베더는 아무것도 못 찾은 임베더와 겉보기가 같다.
2. 타임아웃을 **콜드 로드보다 크게**(≥60s) 하거나, 검색 전 워밍업 1회.
3. 혼합 스케일 정렬 제거: 임베딩 실패 항목은 별도 tail로 내리거나 키워드 점수를 정규화.
4. ⚠ **ollama+bge-m3는 특정 입력에서 HTTP 500 `unsupported value: NaN`을 낸다**(3/3 재현 = 결정적).
   400문서 코퍼스에서 3/57. 지금 구조에선 이것도 `None`으로 붕괴해 해당 문서가 조용히 순위에서
   사라진다. 흡수 organ 쪽 대응은 zero-vector 대체 + **건수 보고**
   (`scripts/aios_ideation.py`, 코사인 0이라 가짜 중복은 못 만들고 novelty만 부풀린다).
