# AIOS = AI Society — 목표 트리 (2026-08-02, founder directive)

**Founder directive (2026-08-02):** 현 에이전트 시스템의 문제 = no-society. 단일 에이전트는 컨텍스트
초기화와 함께 전부 잊는다. 가용성도 없다. → 에이전트 사회를 만들거나, 정보 저장을 대개편하라.
"목표를 설정해. 세부 목표로 나눠. 쫓아가며 빌드해. 다양한 아이디어가 나와도 하나의 점 — AGI,
ai society로 수렴."

## 수렴점 (G0 — 모든 빌드가 향하는 한 점)

> **AIOS는 AI Society다: 컨텍스트 죽음·프로세스 죽음·프로바이더 죽음에도 작업 아크(arc)가
> 살아남는, 검증된 인수인계로 연결된 이종 에이전트 사회.**

이 사회가 하는 주장(claim)은 정확히 세 개다 — **continuity**(아크는 에이전트보다 오래 산다),
**availability**(누군가는 항상 이어받을 수 있다), **verified handoff**(이어받음의 충실도는 외부
검증된다). 재스코프된 정체성(강제-소버린티·외부검증 실행 기질, `docs/AIOS_NORTHSTAR.md`)의 자연
확장이며, AGI에 대한 우리 몫의 기여 = **사회적 신경계**(개별 두뇌가 아니라).

**하지 않는 주장 (3-채널 null 구속, Mortuary Clause):** "사회가 frozen 에이전트를 더 똑똑하게
만든다"는 주장 금지. 경험 주입은 성능을 복리시키지 않음이 사전등록으로 확정됨
(`docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md`). 사회의 가치는 지능 증폭이 아니라
**작업의 불사(不死)와 검증**에 있다. 이 경계를 넘는 설계는 자동 기각.

**founder의 양자택일("사회냐 저장 대개편이냐")에 대한 답:** 이 설계에서 둘은 하나다 — 사회가
가능하려면 상태가 에이전트 밖(원장)에 살아야 하고, 그것이 곧 저장 대개편이다. **기록이 곧 기억이고,
사회 구성원은 기록의 순례자다** (AgentNet 설계의 "thread_id = 정본, provider 핸들 = 부속"과 동일
결론 — `docs/AIOS_AGENTNET_DESIGN.md`).

## 수렴 테스트 (새 아이디어가 통과해야 하는 3문)

1. 이 아이디어는 continuity / availability / verified-handoff 중 무엇을 개선하는가? (셋 다
   아니면 → 기록 후 기각)
2. 죽음-재개 시나리오에서 외부 오라클로 측정 가능한가? (불가면 → 설계 미완)
3. 3-채널 null과 충돌하는 암묵 주장("이러면 더 똑똑해짐")이 숨어 있는가? (있으면 → 제거 후 재심)

## 세부 목표 (빌드 순서)

| # | 목표 | 산출물 | 외부 지표 |
|---|---|---|---|
| G1 | **Society Kernel** — 생존 가능한 작업 상태 | AgentNet v0: thread 원장(append-only 메시지·태스크·영수증·handoff), 어떤 에이전트든 records만으로 재개 | 죽음-재개 테스트: 아크 중간 kill → 다른 에이전트가 records만으로 완주, 오라클 판정 |
| G2 | **Verified handoff** | handoff 패킷 + 인수 충실도 외부 검증기(인수자와 분리) | 충실도 판정 정확도(주입 결함 탐지율) |
| G3 | **Availability** | 고아-아크 워치독 + ≥2 이종 기질(claude/codex/로컬 qwen) 클레임·재개 | MTTR(세션 사망→재개) |
| G4 | **Society memory** | event-sourced thread pack + 의미 FS 검색 (draft-first 유지) | resume fidelity (task-pass 아님) |
| G5 | **반증 실험** | 사전등록: 강제 컨텍스트 죽음 하 society vs solo-restart, 아크 완주율/MTTR, kill rule | McNemar paired, α=0.05 |

G1→G2→G3 순으로 최소 브릭을 이어 붙이고, G5로 사회의 존재 이유 자체를 반증 시도한다.
G5가 null이면: 사회는 해체하고 저장-대개편(G4 단독)으로 재수렴한다 — 그 결정도 지금 적는다.

## 이종 council 검증 (2026-08-02, 설계 전 수행)

**Landscape 그라운딩 (perplexity, 69 sources).** 2026-08 현재 수렴 계열: ①A2A(2025-04 Google →
2025-08 IBM ACP와 LF AI & Data 통합 → 2026 v1.0): task=재개 가능한 1급 객체 + contextId, polling/
SSE/webhook. ②공유메모리·원장: Zep/Graphiti(bitemporal, fact invalidation), Governed Shared
Memory(scoped retrieval·temporal supersession·provenance·policy propagation). ③에이전트 OS·장수
런타임: Letta(main context=RAM / archival=disk, self-managed budget), LangGraph checkpointing,
OpenAgents(persistent workspace + `workspace.restore()`). ④저장 대개편: AgentFS/Turso(SQLite
단일파일 가상 FS, copy-on-write), ESAA(event sourcing + CQRS, append-only 이벤트→투영),
semantic FS(경로가 곧 컨텍스트).
→ **우리 AgentNet 설계(thread_id 정본 + envelope)는 이 지형과 정합**하며, 차별점은 표준 채택
여부가 아니라 **강제-소버린티 + 외부검증 게이트를 원장에 결합**한 점(우리 재스코프 정체성).
남들이 보고한 공통 실패양식: context dilution, ghost memory(모순 사실 동시 인출), goal drift,
state bloat, 동시쓰기 race, 의도적 삭제 실패(ForgetEval 52.7%). 우리 설계는 이걸 **선제 방어**한다.

**Red-team (deepseek 적대 렌즈, 6건 — 전부 goodhart형 "지표는 통과, 목적은 실패").**
설계에 즉시 반영(각 항목이 곧 불변식):

| # | 공격 | 설계 반영 (INV) |
|---|---|---|
| 1 | 체크포인트 해시는 맞는데 **상태가 낡음**(죽은 사이 외부 이벤트 반영 안 됨) — continuity를 "로드 성공"으로 측정하는 굿하트 | **INV-1 freshness**: 재개팩은 인과 위치(마지막 반영 이벤트 seq/시각)를 싣고, 재개 시 원장 tip과 대조해 stale이면 **재개 전 재동기화 강제** |
| 2 | handoff가 **바이트 충실도**만 검증(스키마·해시 통과) 하고 의도는 어긋남 | **INV-2 semantic takeover check**: 검증기는 패킷이 아니라 **인수자의 첫 행동들이 아크 목표와 정합한지**를 판정. 주입 결함(제약 삭제) 탐지율로 검증기 자체를 검증 |
| 3 | 파티션 중 동시 handoff → **split-brain**, longest-chain 선택으로 다른 포크 폐기 | **INV-3 single-writer lease**: 아크당 배타 클레임(lease + TTL, 원자적 파일락). longest-chain 금지. 경합은 거부되고 기록됨 |
| 4 | **책임 분산**: 실패해도 아무도 아크 전체를 소유 안 함 | **INV-4 arc ownership**: 매 시점 소유자 명시 기록, 실패 귀속은 아크 단위. 인수 시 소유권 이전 이벤트 필수 |
| 5 | handoff 경계에서만 체크포인트 → 죽으면 그 사이 작업 증발 | **INV-5 continuous append**: 이벤트소싱(ESAA형) — 진행은 상시 append, 체크포인트는 투영일 뿐 |
| 6 | 외부 검증기가 **SPOF/병목** — 검증 대기로 가용성 하락 | **INV-6 verify-after-resume**: 검증은 재개를 블록하지 않음(비동기). 검증 실패는 사후 아크 플래그·롤백 대상 |

**설계를 바꾼 결정적 지적 (red-team #4 말미):** *"영속 외부기억을 가진 단일 에이전트가 handoff
오버헤드 0으로 더 나을 수 있다."* 이는 founder의 양자택일("사회냐 저장 대개편이냐")을 그대로
실험 질문으로 만든다. ⟹ **G5는 2-arm이 아니라 3-arm으로 동결한다:**
- **A. solo-restart (기록 없음)** — 현행 기본값(=아무것도 안 한 대조군)
- **B. solo + 원장 (저장 대개편 단독)** — 같은 에이전트가 죽고 **자기** 기록으로 재개
- **C. society (원장 + handoff + 워치독)** — **다른** 에이전트가 이어받음
판정: C > B 여야 사회가 정당화된다. **B ≈ C 이면 사회는 해체하고 저장-대개편으로 재수렴**(G0에
이미 적힌 승복 조건의 정밀화). C < B 면 사회는 순 오버헤드 — 그대로 보고한다.

## 선행 자산 (재사용, 재발명 금지)

AgentNet 설계 + envelope 스키마(`docs/AIOS_AGENTNET_DESIGN.md`) · council 가상 스레드
영속화(codex 2026-07-24, `council/hub.py --thread`) · `.aios` dispatch inbox/outbox ·
checkpoint-resume 기계 · hivemind 실행/영수증 · memoryOS draft-first 그래프 · 소버린티
샌드박스와 외부 오라클 (null 프로그램의 유산 전부).
