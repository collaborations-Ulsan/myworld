# AkashicRecord — 분산 검증 가능 원장 설계
> 목표: 원장을 지리적으로 분리하되 누구나 검증 가능하게. 전 세계 컴퓨팅 자원을 균등 활용.
> 작성: 2026-06-19

---

## 핵심 설계 원칙

```
분산   : 단일 서버 의존 없음. 어느 노드가 죽어도 기록 보존
검증   : 모든 기록은 Merkle 증명으로 독립 검증 가능
기여   : 각 AIOS 사용자 기기 = 노드 = 컴퓨팅 + 저장 기여자
프라이버시: 콘텐츠는 절대 이동 안 함. 구조(tool 이름+빈도)만 공유
```

---

## Layer 1 — Entry Format (콘텐츠 주소 지정)

모든 기억 항목은 **내용이 곧 ID**. 위조 불가.

```python
# 항목 ID = 콘텐츠의 SHA256 (이미 구현됨, 강화 필요)
entry_id = "beh-" + sha256(
    content + schema_version + contributor_epoch
).hexdigest()[:16]   # 16자로 확장 (충돌 방지)

# 각 항목이 이전 항목을 참조 → 체인
entry = {
    "id":          entry_id,
    "prev_id":     previous_entry_id,  # append-only 체인
    "content_hash": sha256(content),   # 전체 콘텐츠 해시
    "schema":      "aios.agent_behavior.v1",
    "epoch":       1234567890,         # 기여 시점 (초)
    # ... 기존 필드들
}
```

---

## Layer 2 — Merkle Tree (무결성 증명)

항목들을 **Merkle 트리**로 조직화 → 어떤 항목이든 전체 다운로드 없이 증명 가능.

```
                  ROOT HASH
                 /         \
          H(A+B)             H(C+D)
         /      \           /      \
      H(A)    H(B)       H(C)    H(D)
       A        B          C       D
```

### 구현

```python
# Worker에서 Merkle root 계산
def compute_merkle_root(entry_ids: list[str]) -> str:
    # 1. 모든 entry_id를 정렬 (deterministic)
    leaves = sorted(sha256(eid) for eid in entry_ids)
    # 2. 쌍을 만들어 반복 해시
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])  # 홀수면 마지막 복사
        leaves = [sha256(a + b) for a, b in zip(leaves[::2], leaves[1::2])]
    return leaves[0]

# 특정 항목의 Merkle proof 생성
def merkle_proof(entry_id: str, all_ids: list[str]) -> list[str]:
    # proof = 해당 잎에서 root까지 경로의 sibling 해시들
    # 누구든 이 proof로 root를 재계산 → 검증 완료
    ...
```

### 엔드포인트 추가

```
GET  /root          → { root_hash, entry_count, timestamp, prev_root_hash }
GET  /proof/{id}    → { entry, merkle_proof: [...], root_hash, verified: bool }
POST /verify        → { id, claimed_root } → { valid: bool, actual_root }
```

### Root Chain (변조 불가)

```
root[n] = sha256(root[n-1] + entries_batch_hash + timestamp)
```
새 항목이 추가될 때마다 이전 root를 포함해 계산 → 과거 수정 불가.

---

## Layer 3 — 지리적 샤딩 (Geographic Sharding)

### 현재: 단일 Cloudflare D1 (US East)

```
모든 사용자 → [Cloudflare Worker] → [D1 US-East]
                                          ↑
                                    단일 장애점
```

### 목표: 3 Region × Category Shard

```
[User: Seoul]     → aios-akashic-asia.workers.dev → [D1 Asia]
[User: London]    → aios-akashic-eu.workers.dev   → [D1 EU]
[User: New York]  → aios-akashic-us.workers.dev   → [D1 US]

                       ↓ 동기화
                  [Root KV] (Cloudflare KV — 전 세계 edge replicated)
                  root_hash, entry_count, shard_map
```

### 샤딩 키

```python
# 카테고리별 샤드 → 검색 시 관련 샤드만 쿼리
SHARD_MAP = {
    "code":        "aios-akashic-code",
    "docs":        "aios-akashic-docs",
    "data":        "aios-akashic-data",
    "competition": "aios-akashic-comp",
}

# 지리별 라우팅 (Cloudflare geo header 활용)
def route_to_region(request) -> str:
    country = request.headers.get("CF-IPCountry", "US")
    if country in ASIA_COUNTRIES:
        return "https://aios-akashic-asia.workers.dev"
    if country in EU_COUNTRIES:
        return "https://aios-akashic-eu.workers.dev"
    return "https://aios-akashic-us.workers.dev"
```

### 교차 샤드 검색

```
POST /sync (query)
  → 1. 로컬 region 검색
  → 2. 병렬로 다른 region Worker에 fan-out
  → 3. 결과 병합 + top-K 반환

# Python 클라이언트
def sync_from_global(query, regions=None):
    regions = regions or ["us", "eu", "asia"]
    results = parallel_fetch([f"{REGIONAL_URLS[r]}/sync" for r in regions], query)
    return top_k_merge(results)
```

---

## Layer 4 — P2P Node Network (분산 컴퓨팅)

각 AIOS 설치 = 잠재적 노드. 디바이스가 컴퓨팅과 저장을 기여.

### Node 유형

```
Type A  Light Node  : ~/.aios/ 만 보유. query routing 기여
Type B  Shard Node  : 1개 카테고리의 shard 완전 보유 + serve
Type C  Full Node   : 전체 AkashicRecord + Merkle tree + proof 제공
Type D  Embed Node  : GPU 보유. 임베딩 계산 기여 (RTX 5090 등)
```

### Node Registry (Bootstrap)

```json
// ~/.aios/peers.json
{
  "bootstrap_nodes": [
    "https://aios-akashic.cjw070690.workers.dev",
    "https://aios-akashic-asia.workers.dev"
  ],
  "known_peers": [
    {"id": "node-abc", "url": "http://192.168.x.x:8765",
     "type": "B", "shard": "code", "last_seen": 1234567890}
  ]
}
```

### Gossip Protocol (항목 전파)

```
새 항목 기여 시:
1. 로컬 ~/.aios/ 에 저장
2. 부트스트랩 노드에 POST /contribute
3. 부트스트랩이 known peers에 fan-out (Gossip)
4. 각 노드가 자기 shard에 해당하면 저장, 아니면 relay
5. Merkle root 업데이트 → KV 전파
```

### Embed Node 활용 (RTX 5090 같은 GPU 보유자)

```python
# aios_embed_node.py — GPU 기여자 실행
async def embed_service():
    """로컬 GPU로 임베딩 요청을 처리, Cloudflare AI 대신 사용."""
    while True:
        task = await queue.get()
        vector = ollama_embed(task["text"])  # 로컬 GPU
        await report_to_coordinator(task["id"], vector)
        # 기여 포인트 획득

# 라우팅: Cloudflare Worker가 embed 요청 시
# → 1. 근처 Embed Node 있으면 위임 (분산 컴퓨팅)
# → 2. 없으면 Workers AI fallback
```

---

## Layer 5 — 검증 프로토콜

### 사용자가 자신의 기여를 검증

```bash
# 내 기억이 정말 원장에 있는가?
aios behavior verify --id beh-abc123def456

# 출력:
# ✓ Entry found in AkashicRecord
# ✓ Merkle proof valid (depth: 18, root: sha256:...)
# ✓ Root chain: entry #51,362 of 51,362
# ✓ Contributed at: 2026-06-19T14:30:00Z
```

### 노드가 다른 노드를 검증

```python
def verify_peer_shard(peer_url: str, their_root: str) -> bool:
    """피어 노드의 root hash가 내 root와 일치하는지 확인."""
    my_root = get_local_merkle_root()
    peer_root = requests.get(f"{peer_url}/root").json()["root_hash"]
    # root가 다르면 누군가 데이터를 변조했거나 sync가 안 된 것
    return sha256_compare(my_root, peer_root)
```

### 공개 Checkpoint (누구나 감사 가능)

```
매 1,000개 항목마다:
root_hash를 공개 GitHub 파일에 append
→ 누구든 "이 시점에 X개 항목이 있었다"를 외부에서 검증 가능

# 파일: docs/akashic_checkpoints.jsonl
{"epoch": 1234567890, "count": 51000, "root": "sha256:abc..."}
{"epoch": 1234568890, "count": 52000, "root": "sha256:def..."}
```

---

## 구현 로드맵

### Phase 1 (현재 → 이번 스프린트)
- [x] 단일 Cloudflare Worker + D1
- [x] content-addressed IDs (beh-sha256[:12])
- [ ] `/root` `/proof/{id}` `/verify` 엔드포인트 추가
- [ ] Python 클라이언트 `verify` 명령 추가
- [ ] 공개 checkpoint (GitHub 파일)

### Phase 2 (다음 달)
- [ ] 3 Regional Workers (US / EU / Asia)
- [ ] Category sharding (code / docs / data / competition)
- [ ] 교차 샤드 fan-out 검색
- [ ] Cloudflare KV에 root hash 동기화

### Phase 3 (1분기)
- [ ] P2P Light Node (aios behavior serve-node)
- [ ] Gossip protocol for entry propagation
- [ ] Embed Node 프로토콜 (GPU 기여자)
- [ ] Node health dashboard

### Phase 4 (장기)
- [ ] Federated learning on behavioral patterns
- [ ] DescentNet restriction maps trained on distributed data
- [ ] ZK proof for embedding correctness (embedding 계산 검증)

---

## 전 세계 컴퓨팅 자원 활용 방법

```
데이터  기여 : 모든 AIOS 사용자 → behavioral memories 제공
저장   기여 : Type B/C 노드 → shard 보관 + serve
컴퓨팅 기여 : GPU 보유자 (RTX 5090 등) → 임베딩 계산
검증   기여 : 모든 노드 → Merkle root 검증 참여

현재 Cloudflare:
  Workers  : 300+ 글로벌 PoP → 이미 분산
  KV       : 전 세계 edge replicated → root hash 저장에 적합
  D1       : 현재 US-East 중앙화 → multi-region 필요
  Workers AI: 분산 GPU 추론 → 임베딩 계산

AIOS 사용자 기기:
  ollama + local LLM → 임베딩 노드로 참여 가능
  ~/ .aios/ → shard 캐시로 활용 가능
```

---

## 보안 / 프라이버시 보장

```
- tool_freq (구조적 메타데이터)만 전파. 콘텐츠 절대 이동 금지
- 각 항목은 privacy guard를 통과해야 기여 가능
- 기여자 ID = 익명 해시 (실제 identity 드러나지 않음)
- opt-in 카테고리만 기여 (docs / data / code / personal)
- DNA 불변량 #7: 프라이버시 경계 불가침
```

---

*이 문서는 AIOS AkashicRecord의 분산화 로드맵. Phase 1부터 순차적으로 구현.*

---

## 부록 A — 전세계 플랫폼화 아키텍처 (2026-07-03, prior-art 접지 + 이종 패널 de-bias)

> founder 비전: NIM 키 / end-user 하드웨어를 클라우드 컴퓨트처럼 풀링 → 기여자에게 Akashic Record 접근.
> BOINC·Golem/Akash·Bittensor·Petals·Gensyn·연합학습·IPFS/Filecoin/Ocean 조사 + deepseek/qwen/kimi/glm/nemotron 이종 패널.

### 결론: 조합으로 빌드 가능. 단 하나는 원천연구가 필요.

**핵심 통찰 1 — 접근-게이팅이 무임승차를 공짜로 해결.** 지식은 읽으면 비배제적(공공재)이라 무임승차가 필연이지만, **기여자만 읽게 게이팅하면 club good**이 되어 표준 경제학 해법이 적용됨. 즉 "기여→검증→접근" 루프(이미 설계됨)가 구조적으로 옳다. 크레딧은 **검증된 컴퓨트로만 발행 + 지속기여로 유지**(BitTorrent/Filecoin reciprocity, Akash 스트리밍 escrow).

**핵심 통찰 2 — 유일한 novel·미해결 난제: 오라클 없는 주관적 커먼즈 위 오염저항 × 프라이버시 동시 달성.** 선행시스템은 둘 중 하나만 가짐 — BOINC/Gensyn=재계산 ground-truth, Bittensor/TCR=평문 스코어링(프라이버시 포기). Akashic은 **둘 다 없음**(ground-truth도, raw 공개도 불가). 게다가 **DP 노이즈가 오염을 은폐**(DP-Poison 2026). → **load-bearing 해법 = 레이어 분리**: 큐레이션/스코어링은 **TEE 안 어테스트된 raw**로(노이즈 뒤 숨을 곳 없음), **바깥 집계만 DP 노이즈**. 같은 객체를 큐레이션+프라이버시화 금지.

### 난제 → 훔쳐올 메커니즘 (prior-art)
| 난제 | 메커니즘 | 실패모드 교훈 |
|---|---|---|
| 컴퓨트 검증 | BOINC k-of-n quorum(기본) → Gensyn spot-check/proof-of-learning + RepOps 비트결정론 → TEE 어테스트(강) | LLM추론=비결정 → 의미-등가 비교; 중복 2-3× 비용; quorum은 담합 못 막음 |
| Sybil | 검증컴퓨트=입장권(신원≠접근) + TEE 하드웨어링크(PoET) + stake/slash | 결제레일(escrow)은 검증 아님 |
| 원장 오염 | TCR(commit-reveal+stake/slash) + Yuma 중앙값-clip 가중스코어 | Petals엔 검증 없음; 커먼즈는 큐레이션 없으면 열화(HF 라이선스 66% 오분류) |
| 무임승차 | (통찰1) club-good 게이팅 + reciprocity | — |
| 프라이버시 | 연합학습 "파생신호만"(=구조지문) + secure-agg + 예산화 DP + compute-to-data/TEE | DP↔오염저항 상충 |

### 권장 스택 & 경로 (start-narrow → progressive decentralization)
1. 기여층: 검증컴퓨트 → 만료형 접근크레딧 (tiered: quorum→spot-check→TEE)
2. 정산: Akash식 스트리밍 escrow + stake/slash
3. 커먼즈: content-addressed append-only 지문원장(설계됨) + TCR·Yuma 큐레이션
4. 프라이버시: 파생신호+secure-agg+예산화 DP, TEE 레이어분리
- **Now(신뢰앵커)**: 라이브 Cloudflare Worker에 `/root`·`/proof`·`/verify`+공개 checkpoint(Phase 2). 컴퓨트=NIM키풀+신뢰 페더레이션, 검증=spot-check.
- **Then**: AKR·평판·slash → TCR → embed/inference 노드 개방(Phase 3).
- **Later**: TEE 레이어분리·zkML·글로벌 볼런티어 GPU(Phase 4).

---

## 부록 B — 개인화 층: 유저 선호/작업방식 학습 (YouTube-recsys의 프라이버시-존중판)

> founder 질문: YouTube 추천처럼 유저 행동패턴으로 agent가 선호·작업방식을 배우게?
> 답: **가능하고, 코어는 이미 있음** — `aios behavior predict` → `predict_behavior(context, candidates)`가 DescentNet(ML) × 로컬 Akashic × 글로벌 Akashic 하이브리드로 다음 행동을 예측. CLI 세션로그 INGEST 학습, 구조/행동 메타만(콘텐츠 X).

### 2-tier 설계 (프라이버시 DNA #7 — YouTube와 결정적 차이)
- **로컬 개인모델** (이 유저의 style/선호 — **기기 밖으로 절대 안 나감**): 학습되는 CLAUDE.md. YouTube는 서버측 프로필이지만 AIOS는 로컬 주권.
- **글로벌 Akashic** (익명 구조지문 — 일반적으로 뭐가 통하나): 공유.
→ 개인화는 로컬, 커먼즈는 익명. 절대 혼동 금지.

### YouTube-recsys → AIOS 매핑
| YouTube | AIOS agent |
|---|---|
| 암묵신호(시청/스킵/클릭) | edit-kept vs reverted, 제안 accept/reject, 교정 패턴, "그냥 해" 지시, tool 선택, 언어(한국어), verbosity, ask-vs-act, tech 기본값 |
| 유저 임베딩 | 로컬 선호 임베딩(DescentNet 확장) + 명시 학습규칙 |
| 후보 랭킹 | agent 행동 랭킹(어떤 tool/모델, 얼마나 간결히, 언제 물을지) — `predict_behavior`가 이미 함 |

### recsys 실패모드 → DNA 가드레일 (AIOS가 YouTube보다 나은 이유)
- **필터버블/과적합**: "넌 늘 pandas 써" → 더 나은 polars 제안 중단, 습관 화석화. → **exploration**(가끔 더 나은 것 제안) + "선호"와 "최선"을 분리(글로벌 Akashic이 objective 대조군).
- **피드백루프 폭주**: agent 제안이 유저를 바꾸고 그게 agent를 학습. → 글로벌 품질신호를 안정적 counterweight로.
- **cold start**: 이력 없으면 글로벌+명시 CLAUDE.md fallback.
- **DNA 준수**: 학습된 선호를 **silent 바인딩 금지 — 제안(draft-first) + 유저 교정(operator override) + recommendation-only**. YouTube엔 override가 없음. 이게 AIOS판의 정체성: **프라이버시-존중·유저-주권 recsys**.

### 구현 갭 (있는 것 vs 더할 것)
- 있음: `predict_behavior`(행동예측), DescentNet, 세션 INGEST, MemoryOS draft accept/reject.
- 더할 것: (1) **암묵-피드백 캡처**(edit revert율, 제안 수락율 등 신호화), (2) **유저-style 프로필**(verbosity/ask-vs-act/tech기본/언어 — 행동예측을 넘어), (3) draft-first **선호 제안 루프**("X 선호 감지 — 항상 적용?"), (4) exploration ε.

*반영: 2026-07-03 claude@myworld. 부록 A/B는 로드맵 Phase 2-4 + 개인화 층의 설계 근거.*
