# 프론티어 어휘 정찰 — 검색하기 전에 검색어를 갱신한다 (2026-08-03)

founder 방법론: *"검색하기 전에 그 분야의 프론티어 키워드와 동사를 먼저 확인하라."*
**낡은 어휘로 검색하면 낡은 결과가 나온다.** 이 문서는 우리 아크(에이전트 사회 · 연속성 ·
검증 · 컴퓨트 시스템)에 대한 2026-08 시점 어휘 목록이며, 이후 council/검색은 **여기 있는 용어로**
질의한다. 재정찰 주기: 분기 1회 또는 새 아크 시작 시.

## A. 연속성 · 기억 (컨텍스트가 죽는 문제)

| 용어 | 뜻 | 우리 대응물 |
|---|---|---|
| **context engineering** | 프롬프트가 아니라 정보환경 전체(기억·도구·검색·상태) 설계 | 아크 resume pack |
| **context rot** | 입력이 길어질수록 품질이 **측정 가능하게** 하락(≈30k 토큰 이후 가속) | 우리가 팩을 얇게 유지하는 이유 |
| **compaction / context compression** | 오래된 메시지를 요약·압축본으로 대체 | `supersede` + 팩 tail |
| **compaction validation** (Slipstream, arXiv:2605.08580) | 압축이 궤적을 보존했는지 **검증** | G2 takeover 검증과 동형 |
| **rate–distortion view of compaction** (arXiv:2607.08032) | 무엇을 버리고 무엇을 남길지의 정보이론 | 팩 설계 이론 후보 |
| **three-tier memory** | 무손실 세션 메모리 → 압축 세션 → 장기 | 아크 로그/팩/원장 |
| **sleep-time compute** (arXiv:2504.13171, Letta) | 유휴 시간에 백그라운드가 raw context → **learned context** 로 정제 | 워치독의 미래 확장 |
| **agent-native memory** (arXiv:2606.24775) | 에이전트를 위해 처음부터 설계된 기억 시스템 | G4 |

## B. 컴퓨트 시스템 · 실행 (이번 질문의 본진)

| 용어 | 뜻 | 비고 |
|---|---|---|
| **KV cache** | 이전 토큰의 attention K/V — 재계산 회피 | 진짜 "상주 상태" |
| **prefix caching** | 공유 프리픽스 재사용(요청·세션 스코프) | 세션 밖으로는 못 넘김 |
| **KV snapshot sharing** (Prefill-Once-Fan-Out; vLLM×Mooncake store, 2026-05) | KV 스냅샷을 **1급 객체**로 만들어 다른 컨텍스트에 넘김 | **핸드오프의 컴퓨트 층 대응물** |
| **continuous batching** | 토큰 경계에서 새 요청을 실행 큐에 주입 | GPU 이용률 |
| **session-centric scheduling** (SMetric, arXiv:2607.08565) | 요청이 아니라 **세션** 단위 스케줄링 | 아크=세션 |
| **task-parallel agent scheduling** (Justitia, arXiv:2510.17015) | 공정성 + 효율 | 다중 아크 |
| **scheduler-theoretic framework** (arXiv:2604.11378) | "에이전트 루프 → 구조화된 그래프" | founder의 그래프 제안과 직접 접촉 |
| **Agentic Computation Graph (ACG)** | 정적 템플릿 / 동적 런타임 그래프 / 실행 트레이스 3분법 | 아크 = 실행 트레이스 |
| **agents as POSIX processes** (Quine) | PID=정체성, stdio+exit=인터페이스, fork/exec/exit=수명 | 우리 매핑의 선행 |
| **harness-managed virtual memory** (ClawVM, arXiv:2604.10352) | 하네스가 에이전트에게 가상메모리를 제공 | 우리 팩의 정식 이름 |
| **AgentRM** | 미들웨어 자원관리자 | — |
| **AIOS: LLM Agent Operating System** (arXiv:2403.16971) | 커널이 스케줄링·컨텍스트·메모리·저장·접근제어 제공 | **이름 충돌 주의**: 우리 AIOS와 무관한 별개 프로젝트 |
| 실증 | 6개 프레임워크 GitHub 이슈 4만 건 분석 → 근본 문제 = **스케줄링 실패 + 컨텍스트 열화** | 우리가 겨눈 두 축과 정확히 일치 |

## C. 검증 · 증명 (우리 네트워크 테제의 근접 peer — 정직하게 기록)

| 용어 | 뜻 | 우리와의 관계 |
|---|---|---|
| **proof-carrying agent actions (PCAA)** (arXiv:2606.04104) | 벤더 세션 기록이 아니라 **액션 인증서** 중심의 런타임 거버넌스 | **우리 attestation 설계의 출판된 peer** |
| **Proof-or-Stop** (arXiv:2607.14890) | 모든 결과를 claim으로 보고, **신선하고 소스-상태에 묶인 증거**가 게이트 술어를 만족할 때만 승인 | **우리 INV-1 freshness + 오라클 게이트와 같은 형태** |
| **reproducibility verification of tool use** (arXiv:2603.14332) | 도구 사용의 암호학적 바인딩 + 재현성 검증 | 네트워크 테제의 "재실행 가능성" 요건 |
| **ACAP** (IETF draft-yakung-oauth-agent-attestation) | 단명 JWT, 위임마다 스코프 축소 + **delegation-depth** 증가 | 연합 동의 모델 |

> **정직 표기:** 검증-네트워크 아이디어는 우리 고유가 아니다. PCAA·Proof-or-Stop이 2026년 중반에
> 이미 출판됐다. founder 프레임대로 **peer 존재 = 수요 검증**이지 위협이 아니며, 우리 차별점은
> 발명 주장이 아니라 **커널 강제 샌드박스 + 외부 오라클 + 소버린티**의 결합과 실측 null이다.
> 앞으로 이 영역에서 "우리가 처음"이라고 쓰지 않는다.

## D. 동사 목록 (founder 요청 — 논문·문서가 실제로 쓰는 술어)

`compact` · `compress` · `evict` · `summarize` · `checkpoint` · `snapshot` · `restore` ·
`rehydrate` · `resume` · `fork` · `fan out` · `delegate` · `hand off` · `claim` · `lease` ·
`preempt` · `schedule` · `batch` · `prefill` · `decode` · `cache` · `share` · `attest` ·
`certify` · `bind` · `gate` · `admit` · `challenge` · `re-run` · `reproduce` · `verify` ·
`validate (compaction)` · `ground (trajectory)` · `consolidate` · `refine` · `distill` ·
`supersede` · `invalidate` · `narrow (scope)`

검색 시 **명사보다 동사가 더 잘 찍힌다** — "agent memory"보다 "compaction validation",
"handoff"보다 "KV snapshot sharing"이 프론티어 문헌을 직접 연다.

## E. 이 정찰이 즉시 바꾼 것

1. **네트워크 테제**: 근접 peer(PCAA/Proof-or-Stop) 존재 → 신규성 주장 삭제, 차별점을 결합으로 재서술.
2. **컴퓨트 시스템 질문**: 답의 어휘가 확보됨 — KV snapshot 1급 객체화, session-centric scheduling,
   harness-managed VM, ACG 3분법. (설계는 `docs/AIOS_SOCIETY_AS_COMPUTE_SYSTEM_2026-08-03.md`)
3. **G4/G5 지표**: compaction validation·rate-distortion이 "resume fidelity"를 정식 지표로 만들어 줌.
