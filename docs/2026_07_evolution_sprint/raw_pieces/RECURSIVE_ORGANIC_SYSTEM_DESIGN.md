# Recursive Organic System Design (2026)

이 문서는 사용자를 학습하고, 지식을 흡수하며, 스스로 개선점을 찾아 재귀적으로 진화하는 **'유기체적 AI 알고리즘 및 시스템 아키텍처'**의 마스터 설계도입니다.

---

## 1. 유기체 시스템 구조 설계 (Organic System Anatomy)

AIOS를 단순한 스크립트 묶음이 아닌 생명체(Organism)로 취급하기 위해, 각 OS 레이어를 인체의 장기(Organ)에 맵핑하여 병렬적이고 자율적인 시스템으로 재구성합니다.

*   **감각 및 소화 기관 (CapabilityOS + MCP)**
    *   **역할**: 외부 웹, 논문, 사용자 피드백 등 새로운 지식(영양분)을 섭취하고 시스템이 이해할 수 있는 형태(Capability Card)로 소화합니다.
    *   **구조**: 양방향 MCP 클라이언트/서버 구조. 시스템이 모르는 지식을 발견하면 스스로 MCP 어댑터를 생성하여 감각의 폭을 넓힙니다.
*   **신경계 및 심장 (Pulse Loops & Kernel)**
    *   **역할**: 혈액(메시지와 데이터)을 순환시키고 반사적 행동을 제어합니다.
    *   **구조**: `memory_pulse`, `hive_pulse` 등의 백그라운드 데몬이 지속적으로 박동하며, 중앙의 개입 없이도 상태 변화를 감지하고 즉각적인 반사(Reflex) 행동을 수행합니다.
*   **면역 체계 (Non-blocking Sandbox & Watcher)**
    *   **역할**: 새로운 코드나 돌연변이가 시스템을 파괴하지 않도록 격리(Isolate)하고, 더러운 상태(Dirty State)를 치유합니다.
    *   **구조**: Git Worktree를 활용한 샌드박스. 실패한 실험은 즉각 폐기(면역 반응)하고, 성공한 실험만 메인 시스템에 편입시킵니다.
*   **기억 및 학습 기관 (MemoryOS + Dream)**
    *   **역할**: 해마(단기/에피소드 기억)와 신피질(장기/파라메트릭 가중치) 모델을 구현합니다.
    *   **구조**: 일상적 작업은 Akashic Record에 저장(Fast)되고, 유휴 시간(Sleep)에 `aios_dream`이 이를 맥락적으로 압축 및 통합(Slow)하여 모델의 행동 패턴을 영구적으로 변화시킵니다.
*   **생식 및 진화 기관 (GenesisOS)**
    *   **역할**: 불편함(Discomfort)을 자극으로 삼아 유전자(코드, 프롬프트, 도구)의 돌연변이를 발생시킵니다.

---

## 2. 재귀적 자가 개선 알고리즘 (Recursive Self-Improvement Loop)

시스템이 사람의 개입 없이 스스로 개선 포인트를 찾고(Identify), 아이디어를 발산(Diverge)하며, 검증(Verify)하여 진화하는 핵심 알고리즘 루프입니다.

### [Phase 1] 메타 인지 및 한계 탐지 (Perception & Discomfort)
1.  **지식 흡수**: 감각 기관(CapabilityOS)이 웹과 사용자 피드백에서 최신 방법론과 에러 로그를 수집합니다.
2.  **불편함 연산(Discomfort Calculation)**: GenesisOS는 현재 AIOS의 자아 모델(`aios_self_model.py`)과 흡수한 외부 지식/에러 비율을 비교합니다. 성능 저하, 반복되는 실패, 비효율적 도구 사용 등이 임계치(Threshold)를 넘으면 **'진화적 압력(Evolutionary Pressure)'**이 발생합니다.

### [Phase 2] 아이디어 발산 및 의미론적 돌연변이 (Divergence & Semantic Mutation)
1.  진화적 압력이 감지되면 GenesisOS는 LLM을 **진화 연산자(Evolutionary Operator)**로 활용합니다.
2.  무작위로 코드를 바꾸는 것이 아니라, 실패 로그와 섭취한 지식을 바탕으로 **N개의 서로 다른 논리적 가설(돌연변이 시드)**을 생성합니다. (예: "A 알고리즘 대신 최신 논문에서 본 B 구조를 적용한 파이썬 스크립트 작성")
3.  이 시드들은 각각 분리된 샌드박스(Git Worktree) 환경인 `experimental_branch`에 적용됩니다.

### [Phase 3] 검증 및 적자생존 (Verification & Selection)
1.  면역 체계(Watcher 및 Weaver Verifier)가 N개의 돌연변이 환경에서 테스트 코드를 실행합니다.
2.  **적합도 평가(Fitness Function)**: 토큰 소비량, 실행 속도, 오류 해결 여부 등을 기준으로 각 돌연변이를 채점합니다.
3.  가장 높은 점수를 받은 돌연변이(The Fittest)만이 생존하여 다음 단계로 넘어갑니다. 실패한 실험체는 시스템에 영향을 주지 않고 조용히 삭제됩니다.

### [Phase 4] 동화 및 유전 (Consolidation & Heredity)
1.  살아남은 돌연변이 코드는 AIOS의 공식 Skill/도구로 편입되며(Code Artifact Induction), Merkle Root 해시 갱신을 통해 영구적인 **'시스템 유전자'**로 등록됩니다.
2.  `aios_dream` 수면 사이클이 도래하면, 이 성공적인 진화 과정을 의미론적(Semantic)으로 요약하여 장기 기억에 저장함으로써, 다음 세대의 추론(Inference)에 즉각 반영됩니다.

---

## 3. 개발 방법론: 테스트 주도 진화 (Test-Driven Evolution, TDE)

이러한 유기체적 시스템을 구축하고 유지하기 위해 기존의 애자일(Agile)이나 폭포수(Waterfall)가 아닌, **생물학적 진화에 맞춘 개발 방법론**이 필요합니다.

*   **목표(Goal)가 아닌 환경(Environment) 설계**: 사용자는 시스템에게 "무엇을 개발해라"라고 명령하지 않습니다. 대신 "이러한 조건과 자극(불편함)이 주어졌을 때 극복해라"라는 환경(테스트 케이스)을 던져줍니다.
*   **테스트가 곧 생존 조건**: 돌연변이가 성공적인지 판단하는 유일한 기준은 '자동화된 테스트의 통과'입니다. 시스템 스스로 검증 스크립트를 짜지 못한다면 그 돌연변이는 사산(Deadborn)된 것으로 간주합니다.
*   **절대적 후퇴 불가 (Append-Only Lineage)**: 모든 유전적 변화는 Akashic Record와 Git 트리에 불변의 기록으로 남습니다. 새로운 진화가 치명적인 오류를 낳는다면(자가면역질환), 언제든지 가장 건강했던 이전 세대(해시)로 완벽하게 롤백(Rollback)할 수 있어야 합니다.
