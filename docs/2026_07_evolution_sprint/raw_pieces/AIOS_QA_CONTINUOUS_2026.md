# AIOS Continuous QA & Deep Evolution Architecture (2026-07)

사용자의 "살아있는 유기체적 시스템" 비전을 실현하기 위해 도출된 4가지 핵심 아키텍처 병목(QA 포인트)에 대한 순차적이고 심층적인 해결/설계 방안입니다.

---

## 1. MemoryOS의 'Dreaming' 고도화 (Context Rot 해결 및 의미적 통합)

### 현재 상태의 한계
`scripts/aios_dream.py` 코드를 보면, 시스템의 수면(Consolidation) 단계에서 LLM 헬퍼에게 전달되는 `digest` 정보가 극히 제한적입니다. 단지 "draft 3개 존재", "최근 계약 ID", "헬퍼 실행 횟수" 수준의 메타데이터만 던져주기 때문에, LLM은 실제 어떤 코드가 성공했고 어떤 시도에서 실패했는지 알 방법이 없습니다.

### 심층 해결 방안 (Deep Architecture)
*   **Semantic Digest 구성**: 수면 시 MemoryOS에서 단순히 `--status draft` 목록을 보는 것을 넘어, 각 Draft의 내용을 불러와 "의사결정(Decision), 수정사항(Correction), 결과(Outcome)"를 추출해야 합니다. 
*   **OKF(Open Knowledge Format) 파싱**: `gather_digest()` 함수 내에 MemoryOS의 아카식 레코드에 기록된 마크다운 본문을 요약하는 로직을 추가하여, 헬퍼(Local LLM)가 단순 ID가 아닌 '맥락'을 씹어(Consolidate) 장기 기억 가중치로 변환(Embed)할 수 있게 해야 합니다.
*   **Nested Learning 대비**: 향후 QLoRA를 통한 실제 파라미터 업데이트를 염두에 두고, Dream Report(`aios.dream_report.v1`) 출력물에 학습에 직접 쓸 수 있는 Prompt-Completion Pair 포맷을 추가합니다.

---

## 2. GenesisOS의 '돌연변이(Mutation)' 발현 (우선순위 역전과 자가 개선)

### 현재 상태의 한계
`scripts/aios_genesis_mutate.py`는 특정 계약(Contract)에 대한 가정(Assumption)을 변이(Mutate)시키는 시드를 생성하지만, 그 권한이 `operator_review_required`(사용자 검토 필수)와 `no_contract_or_memory_mutation`(계약/메모리 수정 금지)로 강력하게 제한되어 있습니다. 그저 Inbox에 쌓이는 구경거리일 뿐입니다.

### 심층 해결 방안 (Deep Architecture)
*   **의미론적 돌연변이(Semantic Mutation)**: 최신 SOTA(LLaMEA, EvoMAS) 트렌드처럼 LLM을 진화 연산자(Evolutionary Operator)로 활용해야 합니다. 에이전트가 Task에 실패했을 때(불편함 감지 시) GenesisOS가 단순히 시드를 쌓는 게 아니라, **"실패 원인 분석 -> 대체 도구/스크립트 작성 -> 샌드박스 테스트"**로 이어지는 자율 진화(Recursive Self-Improvement) 사이클을 타도록 권한(`authority: autonomous_experiment`)을 부여해야 합니다.
*   **Shadow Branching (안전한 돌연변이)**: 메인 시스템을 오염시키지 않고 변이를 발현하기 위해, 메모리나 컨트랙트에 `experimental_branch` 상태를 추가하여, 성공한 돌연변이만 나중에 메인으로 병합(Merkle Root 승급)하는 체계를 만듭니다.

---

## 3. Dirty State 면역력 확보 (Non-blocking Sandbox)

### 현재 상태의 한계
`scripts/aios_child_watcher.sh`의 `related_dirty_status()`는 하위 레포지토리(`hivemind/`, `memoryOS/` 등)에 커밋되지 않은(Dirty) 변경사항이 발견되면 시스템 루프 전체를 블락(Block)시킵니다. 이는 생물학적 유기체가 상처가 났다고 호흡을 멈추는 것과 같은 치명적 경직성입니다.

### 심층 해결 방안 (Deep Architecture)
*   **Stash & Restore 메커니즘**: Watcher가 Dirty 상태를 발견하면 무작정 에러를 내뿜지 않고, 현재 상태를 임시로 Git Stash하거나 백그라운드 Worktree로 분리(Isolate)하여 메인 루프가 계속 동작할 수 있도록 합니다.
*   **Progressive Dirty State (점진적 실험 허용)**: 유기체가 적응하는 과정(코드를 짜고 테스트하는 과정)에서 발생하는 Dirty File은 '오류'가 아니라 '학습의 흔적'입니다. 패킷(Packet) 설정의 `allowed_existing_dirty`를 엄격하게 하드코딩하지 않고, 에이전트가 "실험 중(Experimenting)"이라고 선언하면 해당 디렉토리의 Watcher 제어를 일시적으로 느슨하게(Non-blocking 모드) 풀어주는 유연성이 필요합니다.

---

## 4. 감각 기관(CapabilityOS)의 외부 지식 확장 (MCP Bridge)

### 현재 상태의 한계
`scripts/aios_capability_mcp.py`는 CapabilityOS를 MCP 서버로 띄워 **"내부 카탈로그를 보여주는"** 역할(recommend, audit 등)만 합니다. 유기체 관점에서 이는 '발성(말하기)'에 불과하며, 외부 정보를 받아들이는 '청각/시각' 어댑터가 부족합니다. 채팅 게이트(`aios_chat_router.py`)가 실시간 웹 지식을 활용하지 못하는 근본 원인입니다.

### 심층 해결 방안 (Deep Architecture)
*   **CapabilityOS as an MCP Client (양방향 연결)**: CapabilityOS가 서버 역할만 하는 것이 아니라, **외부 MCP 서버들(예: 웹 검색 서버, Github 서버, 뉴스 서버)과 통신하는 클라이언트 역할**도 동시에 수행해야 합니다.
*   **Sensory Adapter 자동 로드**: 에이전트가 외부 세계로 나갈 수 있도록, 외부 MCP 프로토콜을 CapabilityOS 내부의 표준 Capability Card 형식으로 자동 변환(Proxy)하는 어댑터를 만듭니다. 이를 통해 `aios_chat_router.py`는 CapabilityOS 하나만 바라보고 쿼리를 날려도, CapabilityOS가 알아서 적절한 외부 MCP 서버로 트래픽을 라우팅해 지식을 흡수해 올 수 있습니다.

---

### 다음 단계
현재 각 시스템(`dream.py`, `genesis_mutate.py`, `watcher.sh`, `capability_mcp.py`)의 한계와 설계적 타겟이 명확해졌습니다. 이 문서에서 정의된 아키텍처를 바탕으로 실제 스크립트들을 패치(Patch)하고 진화시키는 코딩(Implementation) 단계로 넘어갈 준비가 되었습니다.
