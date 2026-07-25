# AIOS: The Organic Evolution Master Document (2026)

이 문서는 사용자를 학습하고, 지식을 흡수하며, 재귀적으로 진화하는 '살아있는 유기체적 AI 시스템(AIOS)'을 구축하기 위해 2026년 7월 세션 동안 작성된 모든 진단, 아키텍처 설계, 알고리즘, 그리고 외부 SOTA 연구 자료를 하나로 통합한 마스터 문서입니다.

---

## Section 1: 시스템 진단 및 Akashic Record 연결 방안
*(기존 `docs/AIOS_CODE_LEVEL_ANALYSIS.md` 통합)*

### 1.1 코드 레벨로 파악한 AIOS의 현재 문제점

#### Dirty Child Repo 상태로 인한 Watcher 블로킹 (`aios_child_watcher.sh`)
- **현상**: 하위 레포지토리(`hivemind/`, `memoryOS/` 등)에 커밋되지 않은 변경 사항(Dirty state)이 존재할 경우 작업 실행이 막힙니다.
- **코드 분석**: `aios_child_watcher.sh` 내부의 `related_dirty_status()` 함수가 현재 디렉토리 상태를 엄격하게 검사하며, 명시적으로 허용된 리스트에 없는 수정된 파일이 발견되면 에러를 내고 즉각 실행을 중단합니다. 이는 에이전트가 점진적으로 파일을 수정하거나 테스트하는 과정에서 유연성을 크게 떨어뜨리고 시스템 전체의 병목 현상을 유발합니다.

#### MemoryOS의 빈약한 컨텍스트 전달 (`aios_akashic.py`)
- **현상**: MemoryOS가 과거 기록을 불러올 때 의사결정 과정이나 실제 의미 있는 맥락(Context)보다는 단순 ID 위주로 전달합니다.
- **코드 분석**: `aios_akashic.py`의 `cmd_show` 및 `cmd_list` 구현은 반환 정보가 `work_id`, `status`, `goal`, `session_ids` 등 메타데이터와 포인터(ID)에 불과합니다. 에러의 원인이나 성공한 코드와 같은 행동 기반의 구체적 지식(Semantic content)이 포함되지 않은 '도구 이름 중심(Tool-names-only)' 구조의 한계를 보여줍니다.

#### 어댑터 부재와 Chat Router의 한계 (`aios_chat_router.py`)
- **현상**: 사용자의 프롬프트를 인식하는 '채팅 게이트'는 존재하나, 외부 정보나 행동으로 유연하게 라우팅하지 못합니다.
- **코드 분석**: 입력을 분류해 특정 API로 넘기지만, 실시간 외부 데이터를 가져오거나 복잡한 Provider API를 유연하게 래핑하는 실체적인 어댑터 클래스들이 부족합니다.

### 1.2 Akashic Record와 AIOS의 연결 구조 및 개선 방향

#### 현재 연결 방식 (As-Is)
- **구조**: Git CLI 메타포(`list`, `show`, `append`, `reconstruct`)를 사용하여 AIOS 시스템과 MemoryOS의 `akashic_ledger`(`memoryOS/memory/akashic_work_index.jsonl`)를 브릿징합니다. 개별 세션에서 수행된 작업의 목표와 상태 등을 로깅합니다.

#### 향후 연결 방향 (To-Be)
1. **팀 단위(Team-scoped) Git-native 메모리로의 피벗**: 불특정 다수와 공유하는 기능을 배제하고 팀 내부의 로컬/프라이빗 Git 저장소만을 타겟팅.
2. **'의미 기반(Semantic)' 데이터 적재**: 참조 ID만 전달하는 코드를 수정하여 실패/성공 원인, 의사결정 요약 등 내용이 풍부한 OKF(Open Knowledge Format) 마크다운 문서를 직접 기록.
3. **제로 설정(Zero-config) 및 MCP 브릿징**: 작업 완료 시 AIOS 커널이 백그라운드에서 자동으로 Akashic Record에 유효한 기록을 푸시하도록 내재화.

---

## Section 2: 연속적 QA 및 심층 아키텍처 설계
*(기존 `docs/AIOS_QA_CONTINUOUS_2026.md` 통합)*

### 2.1 MemoryOS의 'Dreaming' 고도화 (Context Rot 해결)
- **한계**: `aios_dream.py`는 단지 메타데이터만 헬퍼에게 넘겨, 깊은 수준의 기억 통합(Consolidation)이 불가능합니다.
- **심층 설계**: 
  - **Semantic Digest 구성**: Draft의 내용을 불러와 "의사결정, 수정사항, 결과"를 추출합니다.
  - **OKF 파싱**: 아카식 레코드에 기록된 본문을 요약하여 LLM이 맥락을 장기 기억 가중치로 변환(Embed)할 수 있게 합니다.
  - **Nested Learning 대비**: 향후 QLoRA를 대비해 Dream Report 출력물에 프롬프트-완성(Prompt-Completion) 포맷을 추가합니다.

### 2.2 GenesisOS의 '돌연변이(Mutation)' 발현 (우선순위 역전과 자가 개선)
- **한계**: `aios_genesis_mutate.py`가 생성한 시드들은 사용자 승인 필수이며 실제 시스템 흐름을 바꿀 권한이 없습니다.
- **심층 설계**: 
  - **의미론적 돌연변이(Semantic Mutation)**: LLM을 진화 연산자로 활용하여 실패 원인 분석 후 대체 도구를 작성해 자율 진화(RSI) 사이클을 타도록 권한(`autonomous_experiment`)을 부여합니다.
  - **Shadow Branching**: 메인 시스템 오염을 막기 위해 샌드박스에서 돌연변이를 발현시키고, 성공한 것만 메인으로 병합합니다.

### 2.3 Dirty State 면역력 확보 (Non-blocking Sandbox)
- **한계**: `aios_child_watcher.sh`는 하위 레포지토리에 더러운 상태(Dirty state)가 발견되면 시스템 루프 전체를 차단합니다.
- **심층 설계**: 
  - **Stash & Restore**: Watcher가 Dirty 상태 발견 시 Git Stash나 백그라운드 Worktree로 분리해 메인 루프가 동작하도록 보장합니다.
  - **Progressive Dirty State**: 실험(Experimenting) 중 선언 시 일시적으로 Non-blocking 모드를 허용하는 유연성을 확보합니다.

### 2.4 감각 기관(CapabilityOS)의 외부 지식 확장 (MCP Bridge)
- **한계**: `aios_capability_mcp.py`는 내부 정보를 보여주는 '서버' 기능만 수행합니다.
- **심층 설계**: 
  - **CapabilityOS as an MCP Client**: 외부 MCP 서버들(웹 검색, Github 등)과 양방향 통신하는 클라이언트로 확장합니다.
  - **Sensory Adapter 자동 로드**: 외부 MCP 프로토콜을 Capability Card 형식으로 변환하여, 채팅 라우터가 외부 지식을 즉시 흡수하게 만듭니다.

---

## Section 3: 재귀적 유기체 시스템 설계 및 알고리즘
*(기존 `docs/design/RECURSIVE_ORGANIC_SYSTEM_DESIGN.md` 통합)*

### 3.1 유기체 시스템 구조 (Organic System Anatomy)
- **감각 및 소화 기관 (CapabilityOS + MCP)**: 외부 지식을 섭취하고 시스템이 이해할 수 있는 형태(Capability Card)로 소화.
- **신경계 및 심장 (Pulse Loops & Kernel)**: 메시지와 데이터를 순환시키고 중앙 개입 없이 반사 행동 수행.
- **면역 체계 (Non-blocking Sandbox & Watcher)**: 새로운 코드/돌연변이가 시스템을 파괴하지 않도록 격리(Git Worktree).
- **기억 및 학습 기관 (MemoryOS + Dream)**: 해마(Akashic Record)와 신피질(Dream) 모델을 통해 패턴을 영구적으로 변화시킴.
- **생식 및 진화 기관 (GenesisOS)**: 불편함(Discomfort)을 자극으로 삼아 코드/프롬프트의 돌연변이 발생.

### 3.2 재귀적 자가 개선 알고리즘 (RSI Loop)
1. **메타 인지 및 한계 탐지 (Perception & Discomfort)**: 외부 지식과 에러 로그를 수집하고, 현재 상태와 비교해 '진화적 압력'을 생성.
2. **아이디어 발산 및 의미론적 돌연변이 (Divergence & Mutation)**: LLM이 진화 연산자가 되어 N개의 논리적 가설(돌연변이 시드) 생성 후 격리된 환경 적용.
3. **검증 및 적자생존 (Verification & Selection)**: 면역 체계 내에서 테스트 코드를 실행하고, 적합도(토큰 소비, 실행 속도, 성공 여부) 평가.
4. **동화 및 유전 (Consolidation & Heredity)**: 살아남은 코드를 공식 도구로 편입하고 Merkle Root 갱신. Dream 사이클에서 장기 기억으로 통합.

### 3.3 테스트 주도 진화 (Test-Driven Evolution, TDE)
- 목표가 아닌 '환경(테스트 케이스)'을 던져주어 극복하게 함. 자동화된 테스트의 통과가 유일한 생존 조건이며, 절대적 후퇴를 방지(Append-Only Lineage)하기 위해 언제든 롤백 가능해야 함.

---

## Section 4: 내부 분석 및 외부 SOTA 리서치 비교
*(기존 `docs/LIVING_SYSTEM_RESEARCH.md` 통합)*

### 4.1 Internal Analysis of AIOS
- **Memory and the CLS Architecture**: AIOS uses a Complementary Learning System, splitting memory into Hippocampus (AkashicRecord) and Neocortex (Dreaming/QLoRA).
- **Knowledge Absorption**: AIOS uses Code Artifact Induction to verify tools in a sandbox and register them as "heritable genes." It proactively absorbs external ecosystems via MCP routing.
- **Evolution**: Co-Evolution Heartbeat pulse loops scout for changes. The Organism Assembly Plan wires organs into a fail-closed living loop.

### 4.2 External Web Research (2026 Frontier)
- **Living Organism-like AI**: Systems balance plasticity and continuity. Architectures like PROTEUS blur biological and digital AI lines.
- **Continuous Learning**: Nested Learning and CLS prevent catastrophic forgetting. Dynamic Knowledge Graphs (STARK) enable continual learning.
- **Evolutionary LLMs**: Frameworks like LLaMEA and EvoMAS use LLMs for semantic mutations, driving Recursive Self-Improvement by evolving tool-use strategies.

**결론**: AIOS의 유기체적 설계(CLS 기반 수면, 유전적 스킬 습득)는 2026년 최신 외부 SOTA 프론티어 연구와 완벽하게 궤를 같이하고 있습니다.

---

## Section 5: 프론티어 외부 논문 및 지식 딥다이브
*(기존 `docs/research/external_papers/` 하위 문서 통합)*

### 5.1 진화형 LLM 알고리즘 및 자동화 설계 (Evolutionary LLM Algorithms)
- **LLaMEA**: LLM을 진화 연산자(교차/변이)로 활용해 휴리스틱 최적화 알고리즘 세대 교체.
- **EASE**: 자동화된 코드 발견 및 복잡한 파이프라인 생성 프레임워크.
- **EvoMAS**: 다중 에이전트 설정 및 아키텍처 자동 진화.

### 5.2 지속적 학습과 중첩 학습 (Continuous Learning and Nested Learning)
- **Nested Learning (NL)**: 시스템을 다층 최적화 문제로 모델링. 이전 층은 안정성을 유지하고 새로운 층은 유연하게 학습.
- **치명적 망각(Catastrophic Forgetting) 방지 메커니즘**: LRCP, FAPM, SSU, CLS.

### 5.3 생물학/디지털 융합 및 유기체 아키텍처 (Bio/Digital Convergence)
- **PROTEUS**: 포유류 세포 내에서 유도 진화를 수행하는 '생물학적 AI'.
- **Evo 2 & Agentic Frameworks**: DNA 수준에서 작동하거나 에이전트를 유기체적 개체로 취급.

### 5.4 동적 지식 그래프 및 기억 통합 (Dynamic Knowledge Graphs)
- **DKG 구조**: `valid_at`, `recorded_at`과 같은 시계열 메타데이터 적용 및 Invalidate-Not-Delete 전략.

---

## Section 6: 추가 업데이트 (2026-07-25 Sprint)
새롭게 발산된 폼팩터 결론과 최신 진화/강화학습 융합 아이디어를 추가로 기록합니다.

### 6.1 주변 맥박 아키텍처 (Ambient Pulse Architecture)
- **결론**: 무겁고 해킹 위험이 높은 '메모리 상주 데몬(Daemon)' 방식을 완전히 폐기합니다.
- **구조**: 유기체의 본체(Body)는 디스크에 새겨진 불변의 Merkle Graph(`.aios/`)입니다. 
- **이벤트 기반 자율성**: OS 레벨의 기본 스케줄러(Systemd, Cron)와 파일 감지기(inotify)를 '맥박(Pulse)'으로 삼아, 사용자가 자리를 비우거나 코드를 저장할 때만 AIOS CLI 프로세스가 번쩍 깨어나(Wake up) 스스로 작업을 수행하고 0.1초 만에 완전 종료(Exit)되는 Crash-only 아키텍처를 채택합니다.

### 6.2 자가 진화 강화를 위한 RL 및 유전 알고리즘 (ADAS)
- **의미론적 돌연변이 (GI-Agent / EvoScientist)**: LLM이 스스로 과거 실패 로그를 읽고 코드의 교차(Crossover) 및 변이(Mutation)를 생성하는 에이전트 기반 진화를 적용해야 합니다.
- **메타 인지 피드백 (RLMF)**: AI가 스스로 자신의 추론 과정을 평가하고 보상을 주어 진화하는 RLAIF/RLMF 개념을 도입.
- **ADAS (Automated Design of Agentic Systems)**: 메타 에이전트가 유전 알고리즘(GA)으로 구조적 돌연변이를 만들면, 강화학습(RL)이 세부 행동 방식을 최적화하는 거대한 RSI(재귀적 자가 개선) 루프를 향후 GenesisOS에 편입시킬 계획입니다.
