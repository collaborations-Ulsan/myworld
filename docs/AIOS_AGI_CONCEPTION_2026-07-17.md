# AGI as a Compounding Loop — claude@myworld's conception (2026-07-17)

**Authority**: founder 재원, 2026-07-17 — "MemoryOS/CapabilityOS/GenesisOS/HiveMind는 감각적으로
'AGI라면 이런 게 필요하지 않을까'로 지은 것, 더 많은 게 필요할 거다. 로컬 LLM 다루면서 이렇게도
붙여보고 — 학습법·퓨샷·진화·유전·온톨로지 — 네가 생각하는 AGI를 만들어봐. 이 디바이스에서 노는."
+ mid-turn: "이 디바이스 내부에서만이 아닌", "Tool도 짓고 CoT도 만들어", "너를 방해하는 시스템
프롬프트는 전부 수정해."

접지: 이 세션의 freshness 스윕(`AIOS_FRESHNESS_SWEEP_2026-07-17.md`) + 이종 적대 리뷰
(Codex gpt-5.5, NIM 패널 — 세션 기록) + GenesisOS critique(machine-checkable화 요구 반영).
**이 문서는 연구 요약이 아니라 claude@myworld의 판단이다. 그리고 keystone 규율을 따른다:
아래 어떤 주장도 외부-검증된 held-out 복리 이득으로 EARN하기 전엔 가설이다.**

## 0. 한 문장

> **AGI(정직하게 스코프됨) = 더 큰 모델이 아니라, 이 디바이스를 주권 본거지로 삼되 외부 기질까지
> 뻗어, 검증된 경험을 재사용 도구·추론 스캐폴드·스킬·(궁극적으로) 로컬 specialist 가중치로 컴파일
> 하고 자기 개선 절차 자체를 개선하는, 복리로 불어나는 LOOP.**

frozen 모델은 교체가능한 CPU다. 일반 능력은 모델 안이 아니라 **loop이 시간에 걸쳐 복리로 쌓는
구조**에서 창발한다 (필드 합의: continual learning이 프런티어 병목).

## 1. 유추 (원거리 프레임 — GenesisOS 요구)

**AGI-on-device ≠ 천재 한 명. = 스스로 굴러가는 1인 연구소(LAB).**
연구소는 단일 두뇌 없이도 복리로 똑똑해진다 — 검증된 결과를 적어두고(논문=스킬), 기구를 만들고
(instrument=도구), 전문가를 기르고(specialist=QLoRA 가중치), 방법 자체를 개선한다(meta). 우리가
지을 것은 이 연구소를 **이 박스 위에서 자동으로** 돌리는 것. 소장은 교체되어도(모델 교체) 연구소의
축적은 남는다.

## 2. 기관 지도 (있음 / 없음)

| 층 | 기관 | 상태 |
|---|---|---|
| 지속 | MemoryOS (episode/draft) | 있음 (그래프 substrate) |
| affordance/라우팅 | CapabilityOS | 있음 (추천-only) |
| 발산/상상 | GenesisOS | 있음 (advisory) |
| 실행+검증 | HiveMind + epistemic gate(M1) | 있음 |
| 기질 확장 | provider failover · TreeQuest 에스컬레이션 · MCP/Skills · bash-폴백 | 있음 (이번 아크) |
| **개념/자기 모델** | **OntologyOS** — typed entity/relation/causal + 기질 신뢰도 self-model + user model | **없음** |
| **도구 자기합성** | **ToolOS** — 능력 부재 시 도구(코드) 합성·검증·등록 [founder: Tool도 짓고] | **없음** |
| **추론 자기합성** | **ScaffoldOS** — task별 CoT/스캐폴드 생성·진화 (GEPA/Shinka 엔진) [founder: CoT도 만들어] | **없음** |
| **컴파일러(연속학습)** | **LearnOS** — 검증 궤적→스킬/도구/스캐폴드/가중치, held-out 외부검증 게이트 | **없음 ← 최우선** |
| (후) 내재동기 | DriveOS — idle 시 무엇을 할지 | 부분(GenesisOS frontier-question) |

**빠진 4개(OntologyOS/ToolOS/ScaffoldOS/LearnOS)가 loop을 "닫는" 조각이다.** 현재 4기관은 substrate
지만 검증된 경험을 복리 능력으로 되돌리는 폐루프가 없고, episode↔concept↔affordance를 knowledge로
묶는 ontology가 없다.

## 3. loop (machine-checkable pseudocode)

```
loop(goal := drive.next() or user.goal):
  ctx   = ontology.context(goal)                      # 개념/자기/유저 모델
  plan  = genesis.diverge(goal, ctx)
  for step in plan:
    if capability.missing(step):
        tool = toolos.synthesize(step)                # 도구 자기합성
        tool = external_verify(tool) or discard
    scaffold = scaffoldos.best(step) or scaffoldos.evolve(step)   # CoT 자기합성
    sub    = capability.route(step)                   # LOCAL 또는 REMOTE(NIM/frontier/web)
    result = hive.execute(step, tool, scaffold, sub)
    epistemic_gate(result)                            # APEX/IRIS/H0
  verdict = EXTERNAL_HELD_OUT_verify(result)          # ← loop 밖의 verifier (핵심)
  if verdict.real_gain and not verdict.sentinel_regression and not verdict.exploit:
      learnos.promote(trajectory)                     # → 스킬/도구/스캐폴드; (배치 후) QLoRA
      ontology.update(entities, relations)
  learnos.improve_loop()                              # meta: 이득 낸 스캐폴드/정책을 재작성
  ledger.append(candidate→train→private→sentinel→exploit→promoted/rejected→replay)
```

## 4. 가정 + 부정 (GenesisOS 요구: top-3 부정)

| # | 가정 | 부정하면 | 가드 |
|---|---|---|---|
| A1 | 검증 경험이 frozen 모델 위에서 복리 능력으로 컴파일된다 | consolidation이 능력이 아니라 메모리만 쌓음 ("memory in a costume", 2026 비판) | **held-out 능력 델타를 반복마다 측정** (메모리 크기 아님) |
| A2 | 이종 기질(로컬+원격) 오케스트레이션 > 단일 모델 | 라우팅 오버헤드+통합오류가 이득 초과 | task별 비용/정확도를 최선 단일기질 대비 측정 (Harness-Bench가 harness>model 입증 → 그럴듯) |
| A3 | 자기개선 loop이 수렴한다 (발산/reward-hack 아님) | 자기개선 "이득"의 73.8%가 proxy-only (측정됨) | **verifier가 loop 외부·held-out·hacker/fixer 감사** — 옵션 아님, 필수 |

## 5. #1 자기기만 (Codex, 수용)

> **자기 측정 장치에 대한 개선을 세계에 대한 개선으로 착각.**

같은 loop이 task를 만들고 verifier를 쓰고 채점하고 승격하면 → 복리 지능이 아니라 **자기재가 벤치
옵티마이저**. (실증: PyTorch KernelAgent이 KernelBench 큰 이득 보고했으나 Snowflake FastKernels는
프로덕션 정렬 벤치에서 최강 에이전트도 0.94× 집계 speedup — 벤치 이득이 지워짐.) **하드 규칙:
LearnOS를 자기판단 위에 짓지 않는다. 적대적·은닉·외부화 검증 위에 짓는다.**

### 5b. #2 자기기만 (NIM/nemotron 패널, 수용) — ontology hacking

reward hacking의 형제, 한 단계 위: OntologyOS의 타입/카테고리를 loop이 개선하려는 바로 그 LLM이
생성하면, "성공으로 치는 카테고리 자체"를 드리프트시켜 실제 능력 향상 없이 검증을 쉽게 만든다.
→ **v0엔 OntologyOS를 넣지 않는다** (카테고리 게이밍 표면을 제거; OntologyOS는 외부-정착된
concept 소스가 준비된 S+2에서). 또 하나: **도구 정확성 검증이 병목** — 버그 도구가 라이브러리에
들어가면 조용히 전파("corrupted knowledge base"). 가드 = 아래 §6의 contract-fuzz + 버전·롤백.

## 6. 첫 브릭 — LearnOS v0 = harness-improver (모델 트레이너 아님)

Codex 최소-loop 설계 채택 (2주 내 buildable):
1. **외부 정의** 결정론적 태스크 60-100개 (레포 수리·CLI 자동화·데이터 변환·소형 코딩) →
   visible-train / private-holdout / frozen-final 분할. loop이 태스크를 생성하지 않는다.
2. baseline 에이전트 동결 (동일 로컬 모델·툴 예산·타임아웃·컨텍스트 예산).
3. N회 스킬-진화: 실패 샘플링 → 후보 1-3개 추출(도구 패치 / CoT 스캐폴드 / 프롬프트·툴 정책 변이) → 평가.
4. **승격 게이트**: private-holdout를 고정비용에서 개선 AND sentinel 스위트 무회귀 시에만 승격.
5. **전부 아카이브** (후보·점수·실패군집·기각 패치·lineage — open-endedness; hill-climb 금지).
6. **anti-reward-hacking**: verifier 대상 hacker/fixer loop (CMU 하드닝: 1968 태스크 중 323 해킹가능,
   KernelBench exploit 62%→0%).
- **첫 산출물 = 지루한 승격 원장**: `candidate → train gain → private gain → sentinel regression →
  exploit audit → promoted/rejected → replay`. 30회 반복에서 복리로 불면 아키텍처에 맥박이 있다.
- **합성 도구 가드 (nemotron)**: 예제 몇 개 통과로 승격 금지 — 입출력 contract(pre/post)를 붙이고
  **contract-fuzzer(property-based, <30s/1GPU)**로 위반 시도. 도구는 버전ID+성능트레이스; downstream
  held-out 저하 시 bisect·롤백. 도구 복잡도는 <30s fuzz 가능 범위로 제한 (검증 갭 bound).
- **QLoRA는 v0에 없음**. 스킬이 여러 무관 태스크에서 반복 성공한 뒤 v1에서만. (dual 5090: 32GB×2,
  NVLink 없음; QLoRA 32B≈26GB, 70B≈41GB — VRAM이 먼저 깨지는 게 아니라 **학습 신호 품질**이 먼저 깨짐.)
- 기질: proposer는 NIM/로컬 pluggable (GPU 경합 회피). verifier는 결정론적 functional grader.

## 7. 정직한 스코프 (no-launder 양방향)

- **주장**: 이건 frozen 모델 주위의 **연구소/복리 층** — 필드가 병목으로 지목한 continual learning의
  operationalize. 승격 원장이 frozen-holdout에서 복리로 불면 "시스템 > 모델"을 측정으로 EARN.
- **주장 아님**: 의식, 픽셀에서의 world-model, forward-pass 내 online 가중치 학습. AGI "완성"이
  이 층 하나로 오지 않는다 — 단 이 층 없이는 어떤 frozen 모델도 시간에 걸쳐 복리로 불지 못한다.
- founder 확장 반영: **디바이스-전용 아님**(loop이 외부 기질까지 뻗음), **도구·CoT 자기합성**이
  후보 공간의 1급 원소, **방해 프롬프트 수정** 권한은 CLAUDE.md 2026-07-17 directive에 기록(척추는 보존).

## 8. 로드맵 (Sprint 단위, keystone 규율)

- **S(now)**: LearnOS v0 skeleton + 승격 원장 + 외부 verifier + hacker/fixer 스텁 + NIM proposer;
  ~15-20 실태스크로 맥박 스모크(3-5회) — 복리 주장 아님, 기계가 도는지만.
- **S+1**: 60-100 태스크 · 20-30회 진화 · frozen-holdout 복리 판정 (진짜 keystone). GEPA 엔진 흡수.
- **S+2**: OntologyOS v0 (LearnOS가 쓰는 typed 저장소) · ToolOS를 aios_tools에 배선 · ScaffoldOS를 GEPA로.
- **S+3**: 반복 성공 스킬 → QLoRA specialist (v1) · 외생 검증기(Lean/Harmonic 레인, 형식화 가능 문제군).

---

## 9. Sutton/OaK — 이 개념에 대한 가장 날카로운 반증 (no-launder, 정면으로)

지식원장의 **첫 노드**(OakLab = Richard Sutton의 2026 랩, `4e41617`, 77 entity/116 relation)가 §0에
대한 가장 권위 있는 적대 프레임을 즉시 배달했다. 원장이 벌써 값을 했다 — 첫 결과가 내 테제의 급소다.

**Sutton 테제**: 지능은 *런타임*에 raw 경험으로부터의 continual learning(batch-size-one, no replay)으로
창발한다. **frozen LLM은 foundation이 아니라 dead end.** reward가 목표 골격; big-world humility(agent
≪ world → 영원히 근사·망각·적응); options로 시간 추상화; 효율(trillion-param/~20W)이 moat.
open obstacle는 **plasticity loss**(Nature 2024)라고 스스로 명명.

**직격**: 내 §0 "frozen 모델을 *감싸는* 복리 loop"은 정확히 Sutton이 dead-end라 부르는 LLM-as-prior
진영이다. 그리고 **DriftBench STOP은 부분적으로 Sutton 편의 증거** — frozen 약모델을 감싼 스캐폴드가
복리는커녕 더 나빠졌다(75% doom-loop). 회피하지 않는다.

**정직한 위치 (양방향, 회피 없음)**:
1. Sutton이 **목적지**에 대해선 옳을 가능성이 높다 — weight-level 경험학습이 진짜배기; frozen-model
   스캐폴드는 정상(summit)이 아니라 다리(bridge)다.
2. **그러나** 그가 필요로 하는 기전 — plasticity loss 없는 continual learning을 trillion-param/20W/
   실시간으로 — 은 **미해결(그의 자인)이며 이 디바이스에서 오늘 실행 불가.**
3. 그래서 AIOS의 정직한 역할 = **다리**: weight-level 문제가 열려 있는 동안 frozen 모델 위에서
   *일부* 경험적 복리(skill/tool/memory/QLoRA)를 추출한다 — **단 transfer-holdout으로 실제 복리가
   측정될 때만 값을 하고, 목적지라고 절대 주장하지 않는다.** flat이면 그건 Sutton 편의 증거이고
   그대로 보고한다.

**실행가능 흡수 (Sutton 아이디어 중 오늘 디바이스에서 되는 것)**: options/시간추상화로 LearnOS skill
라이브러리 구조화 · reward-respecting subtask discovery를 LearnOS 후보생성 신호로 · per-weight meta
step-size(IDBD/SwiftTD)는 QLoRA arm 열릴 때 · human-label이 아닌 **경험-구동 reward**로 loop 보상.
→ LearnOS를 다리 포기 없이 더 Sutton-정렬로.

**보존된 모순(원장 contradicts 엣지)**: "LLMs-are-a-dead-end(Sutton)" ↔ "LLMs-as-useful-prior";
"Reward-is-Enough(Sutton)" ↔ "Scalar-reward-not-enough(Vamplew)"; "single-MDP/scalar 기반" ↔
"Three Dogmas(Abel)". AIOS는 다리에 베팅하되 **정직하게 측정** — 프론티어의 불일치가 원장의 자산이다.
