# AIOS 코드 레벨 문제점 분석 및 Akashic Record 연결 방안

## 1. 코드 레벨로 파악한 AIOS의 현재 문제점

### 1.1 Dirty Child Repo 상태로 인한 Watcher 블로킹 (`aios_child_watcher.sh`)
- **현상**: 하위 레포지토리(예: `hivemind/`, `memoryOS/` 등)에 커밋되지 않은 변경 사항(Dirty state)이 존재할 경우, 작업 실행이 막힙니다.
- **코드 분석**: 
  - `aios_child_watcher.sh` 내부의 `related_dirty_status()` 함수는 현재 디렉토리 상태를 엄격하게 검사합니다.
  - 패킷(Packet)에 명시적으로 허용된 `allowed_existing_dirty`나 `allowed_existing_dirty_baseline` 리스트에 없는 수정된 파일이 발견되면 에러를 내고 즉각 실행을 중단합니다. 
  - 이는 에이전트가 점진적으로 파일을 수정하거나 테스트하는 과정에서 유연성을 크게 떨어뜨리고, 시스템 전체의 병목 현상을 유발합니다.

### 1.2 MemoryOS의 빈약한 컨텍스트 전달 (`aios_akashic.py`)
- **현상**: MemoryOS가 과거 기록을 불러올 때, 의사결정 과정이나 실제 의미 있는 맥락(Context)보다는 단순 ID 위주로 전달합니다.
- **코드 분석**: 
  - `aios_akashic.py`의 `cmd_show` 및 `cmd_list` 구현을 보면 반환 및 출력하는 정보가 `work_id`, `status`, `goal`, `session_ids`, `checkpoint_refs`, `memory_draft_ids` 등 메타데이터와 포인터(ID)에 불과합니다.
  - '에러의 원인이 무엇이었는지', '어떤 코드가 성공했는지'와 같은 행동 기반의 구체적 지식(Semantic content)이 포함되어 있지 않은 '도구 이름 중심(Tool-names-only)' 구조의 한계를 코드 단에서 여실히 보여줍니다.

### 1.3 어댑터 부재와 Chat Router의 한계 (`aios_chat_router.py`)
- **현상**: 사용자의 프롬프트를 인식하는 '채팅 게이트'는 존재하나, 실질적으로 외부 정보나 행동으로 유연하게 라우팅하지 못합니다.
- **코드 분석**:
  - `aios_chat_router.py`는 입력을 분류해 특정 API로 넘기지만, 실시간 외부 데이터를 가져오거나(Current-info route) 복잡한 Provider API를 유연하게 래핑(Wrapping)하는 실체적인 어댑터 클래스들이 부족하여 단순한 수준의 답변을 반환하는 데 그칩니다.

---

## 2. Akashic Record와 AIOS의 연결 구조 및 개선 방향

### 현재 연결 방식 (As-Is)
- **구현 파일**: `scripts/aios_akashic.py`
- **구조**: Git CLI 메타포(`list`, `show`, `append`, `reconstruct`)를 사용하여 AIOS 시스템과 MemoryOS의 `akashic_ledger`를 브릿징(연결)합니다.
  - **저장소**: `memoryOS/memory/akashic_work_index.jsonl`에 저장.
  - **역할**: 개별 세션에서 수행된 작업(Work Item, 예: `WORK-20260612-001`)의 작업 목표와 상태, 생성된 체크포인트 파일들을 로깅하여, 에이전트나 사용자가 과거 작업의 계통(Lineage)을 추적할 수 있도록 합니다.

### Akashic Record의 비전 수정 및 향후 연결 방향 (To-Be)
최신 설계 재검증(2026.07) 문서에서 "글로벌/퍼블릭 유저 간의 지식 공유 풀"로서의 Akashic Record는 사용자 수요 부족 및 보안 문제로 인해 사장되었습니다. 따라서 AIOS와의 향후 연결(통합)은 다음과 같이 개선되어야 합니다.

1. **팀 단위(Team-scoped) Git-native 메모리로의 피벗**
   - 불특정 다수와 공유하는 기능을 완전히 배제하고, `aios_akashic.py`가 팀 내부의 로컬 Git 저장소 또는 중앙 집중식 프라이빗 저장소만을 타겟팅하도록 축소·안정화해야 합니다.
2. **단순 ID 기록을 넘은 '의미 기반(Semantic)' 데이터 적재**
   - `aios_akashic.py`의 `append` 단계에서 단순 참조 ID(`--checkpoint-refs`)만 전달하는 코드를 수정해야 합니다. 실패/성공 원인, 의사결정 요약 등 내용이 풍부한(Content-rich) OKF(Open Knowledge Format) 마크다운 문서를 직접 기록할 수 있도록 페이로드 아키텍처를 확장해야 합니다.
3. **제로 설정(Zero-config) 연동 및 MCP 브릿징**
   - AIOS의 워크플로우를 MCP(Model Context Protocol) 형태로 노출시켜, 작업이 완료되거나 리뷰가 통과될 때 쉘 스크립트 기반 명령어 호출 없이 AIOS 커널이 백그라운드에서 자동으로 Akashic Record에 유효한 기록을 푸시(Push)하도록 완전히 내재화해야 합니다.
