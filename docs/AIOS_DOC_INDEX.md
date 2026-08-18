# 문서 색인 — 자동 생성 (2026-08-18)

**손으로 고치지 말 것.** `python3 scripts/aios_doc_index.py`가 다시 만든다.
손으로 쓴 색인은 하루 뒤 낡고, 612번째 문서가 된다.

## 측정 — 창업자 진단과 다른 부분

*"장황하게 처리되지 못한 TODO로 남았다"*를 재봤더니 그게 아니었다:

```
문서            600
미해결 표시     6   (intent 마커가 실제로 남은 것)
사전등록        17건 전부 결과 기록됨 (매달린 계획 0)
그래프 고아     0  (docs 층 고아율 0.0%)
```

닫히지 않은 것이 문제가 아니라 **닫힌 문서가 지도 없이 쌓인 것**이 문제다.
전부 닫혀 있어도 지도가 없으면 장황함으로 경험된다. 그래서 삭제가 아니라 색인이다.

## 상태

| | 뜻 |
|---|---|
| **ANCHOR** | 많이 인용됨 — 조직을 지탱한다. 먼저 읽을 것 |
| **CLOSED** | 자기 결과를 기록함 (NO-GO / kill rule / PASS) |
| **SUPERSEDED** | 스스로 폐기를 선언함 |
| **OPEN** | 미해결 표시가 남음 |
| **REFERENCE** | 인용되지만 자기 결론은 없음 — 결론이 아니라 맥락 |

```
CLOSED        249
REFERENCE     187
ANCHOR        149
SUPERSEDED      9
OPEN            6
```

## 실험·게이트 (32)

| 상태 | 피인용 | 문서 | 제목 |
|---|---:|---|---|
| ANCHOR | 24 | [AIOS_DRIFTBENCH_PREREG_2026-07-11](AIOS_DRIFTBENCH_PREREG_2026-07-11.md) | AIOS-DriftBench — Pre-Registration (v1.1, FROZEN at commit 2026-07-11) |
| ANCHOR | 16 | [AIOS_HEADLINE_AB_RESULTS](AIOS_HEADLINE_AB_RESULTS.md) | AIOS headline A/B — does the behavioral-memory ledger measurably help an agent? |
| ANCHOR | 15 | [AIOS_G5_SOCIETY_PREREG_2026-08-03](AIOS_G5_SOCIETY_PREREG_2026-08-03.md) | G5 pre-registration — 사회는 혼자보다 나은가? (frozen 2026-08-03) |
| SUPERSEDED | 15 | [AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27](AIOS_PHASE5E_CHANNEL_E_PREREG_2026-07-27.md) | Channel-E pre-registration — the program's LAST SHOT (frozen 2026-07-27) |
| ANCHOR | 12 | [AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26](AIOS_PHASE5_COMPOUNDING_PREREG_2026-07-26.md) | Phase 5 — Does the assembled organism COMPOUND? (pre-registration, 2026-07-26) |
| ANCHOR | 11 | [AIOS_DISTILLER_PREREG_2026-07-17](AIOS_DISTILLER_PREREG_2026-07-17.md) | AIOS Experience-Distiller — Keystone Pre-Registration (v1.1, FROZEN at commit 2026-07-17) |
| ANCHOR | 10 | [AIOS_KEYSTONE_EXPERIMENT](AIOS_KEYSTONE_EXPERIMENT.md) | AIOS Keystone Experiment — does the commons/DescentNet causally help? (design + running log) |
| ANCHOR | 9 | [AIOS_AGENT_INDUCED_H1_RESULTS](AIOS_AGENT_INDUCED_H1_RESULTS.md) | Agent-Induced Consistency H¹ — real-memory results (founder #1 gate) |
| ANCHOR | 8 | [AIOS_M2_DESIGN_ADDENDUM_2026-07-11](AIOS_M2_DESIGN_ADDENDUM_2026-07-11.md) | M2 (AIOS-DriftBench-mini) design addendum — heterogeneous-panel tests (2026-07-11) |
| CLOSED | 7 | [AIOS_BENCHMARK_RESULTS](AIOS_BENCHMARK_RESULTS.md) | AIOS Benchmark Results — First Matched-Run Fixture |
| CLOSED | 7 | [AIOS_LEARNOS_S1_RESULTS_2026-07-17](AIOS_LEARNOS_S1_RESULTS_2026-07-17.md) | LearnOS S+1 — 결과 (2026-07-17) |
| CLOSED | 6 | [AIOS_HIVEMIND_V0_RESULTS](AIOS_HIVEMIND_V0_RESULTS.md) | AIOS Hivemind v0 — first empirical results (the smallest honest test) |
| CLOSED | 6 | [AIOS_M1_MEMORY_EDGE_PREREG_2026-08-14](AIOS_M1_MEMORY_EDGE_PREREG_2026-08-14.md) | 사전등록 — M1 memoryOS 엣지 (5팔) |
| CLOSED | 5 | [AIOS_GENESIS_GATE](AIOS_GENESIS_GATE.md) | AIOS Genesis Gate |
| CLOSED | 5 | [AIOS_M1_GATE_RESULT_2026-08-16](AIOS_M1_GATE_RESULT_2026-08-16.md) | M1 정직성 게이트 결과 — 돌리지 않는다 (2026-08-16) |
| CLOSED | 5 | [AIOS_M5_OFFLINE_VERIFICATION_2026-07-11](AIOS_M5_OFFLINE_VERIFICATION_2026-07-11.md) | AIOS M5 — Offline Provider-Death Verification — 2026-07-11 |
| REFERENCE | 5 | [M2_FREEZE_PREP_a2_audit_nim](M2_FREEZE_PREP_a2_audit_nim.md) | M2_FREEZE_PREP_a2_audit_nim |
| CLOSED | 4 | [AIOS_DISTILLER_PILOT_RESULTS_2026-07-18](AIOS_DISTILLER_PILOT_RESULTS_2026-07-18.md) | AIOS Experience-Distiller — Pilot Results (2026-07-18) |
| CLOSED | 4 | [AIOS_DRIFTBENCH_STAGE1_RESULTS_2026-07-17](AIOS_DRIFTBENCH_STAGE1_RESULTS_2026-07-17.md) | AIOS-DriftBench Stage-1 Results (2026-07-17) |
| CLOSED | 4 | [LLM_QUALITY_GATE_SOTA](LLM_QUALITY_GATE_SOTA.md) | LLM Quality Gate / Cascade Routing — State of the Art (2025–2026) |
| CLOSED | 4 | [M2_FREEZE_PREP_2026-07-11](M2_FREEZE_PREP_2026-07-11.md) | M2 freeze-prep decisions (ASC-0282, WP-B supervision) — 2026-07-11 |
| CLOSED | 3 | [AIOS_G6_LEDGER_VALUE_PREREG_2026-08-08](AIOS_G6_LEDGER_VALUE_PREREG_2026-08-08.md) | G6 pre-registration — 기록은 그 자체로 값을 하는가? (frozen 2026-08-08) |
| CLOSED | 3 | [AIOS_HIVEMIND_H1_GATE](AIOS_HIVEMIND_H1_GATE.md) | AIOS H¹ Gate Test — Sheaf Cohomology as Composition-Gap Backbone |
| CLOSED | 2 | [AIOS_ACTIVE_INFERENCE_PROBE_PREREG_DRAFT_2026-08-01](AIOS_ACTIVE_INFERENCE_PROBE_PREREG_DRAFT_2026-08-01.md) | Active-Inference Mini-Probe — pre-registration DRAFT (status: PROPOSED, NOT RUN) |
| REFERENCE | 2 | [AIOS_GPT_EXPERIMENT_ASSESSMENT_2026-08-08](AIOS_GPT_EXPERIMENT_ASSESSMENT_2026-08-08.md) | GPT가 실제로 돌린 실험 — 우리 Channel-E 실패 지점을 정면으로 겨냥한다 (2026-08-08) |
| CLOSED | 2 | [AIOS_M2_MEMORY_AS_COMPUTATION_PREREG_2026-08-16](AIOS_M2_MEMORY_AS_COMPUTATION_PREREG_2026-08-16.md) | 사전등록 — M2: 기억은 정보가 아니라 계산인가 (2026-08-16) |
| CLOSED | 2 | [M0_MASTER_MAP](M0_MASTER_MAP.md) | M0 — Master Completion Map of AIOS |
| CLOSED | 1 | [AIOS_DISTILLER_BIGB_RESULTS_2026-07-22](AIOS_DISTILLER_BIGB_RESULTS_2026-07-22.md) | AIOS Experience-Distiller — Big-B Results (2026-07-22) — 기록 재정정 |
| CLOSED | 1 | [AIOS_DISTILLER_CONFIRMATORY_RESULTS_2026-07-18](AIOS_DISTILLER_CONFIRMATORY_RESULTS_2026-07-18.md) | AIOS Experience-Distiller — Confirmatory Results (2026-07-18) |
| CLOSED | 1 | [AIOS_LEARNOS_S11_RESULTS_2026-07-17](AIOS_LEARNOS_S11_RESULTS_2026-07-17.md) | LearnOS S+1.1 Results (2026-07-17) — causal gate FIXES the harm, but compounding stays untestab |
| CLOSED | 0 | [AIOS_COPYNESS_GATE_2026-08-18](AIOS_COPYNESS_GATE_2026-08-18.md) | 사회 게이트 — agent들은 복사본인가 (2026-08-18) |
| SUPERSEDED | 0 | [AIOS_M3_PARTITION_SOCIETY_PREREG_2026-08-18](AIOS_M3_PARTITION_SOCIETY_PREREG_2026-08-18.md) | 사전등록 — M3: 분할형 사회는 단일 context를 이기는가 (2026-08-18) |

## 아키텍처·설계 (19)

| 상태 | 피인용 | 문서 | 제목 |
|---|---:|---|---|
| ANCHOR | 453 | [AIOS_AGENT_PROTOCOL](AIOS_AGENT_PROTOCOL.md) | AIOS Agent Protocol |
| ANCHOR | 22 | [AIOS_MINIMUM_KERNEL_AUDIT](AIOS_MINIMUM_KERNEL_AUDIT.md) | AIOS Minimum Kernel Audit |
| ANCHOR | 17 | [AIOS_SERVING_DESIGN_BRIEF](AIOS_SERVING_DESIGN_BRIEF.md) | AIOS Serving Design Brief |
| ANCHOR | 13 | [AIOS_BENCHMARK_PROTOCOL](AIOS_BENCHMARK_PROTOCOL.md) | AIOS Benchmark Protocol |
| ANCHOR | 10 | [AIOS_DESIGN_REVALIDATION_2026_07](AIOS_DESIGN_REVALIDATION_2026_07.md) | AIOS Design Re-validation — 2026-07-02 |
| ANCHOR | 10 | [AIOS_LEARNOS_S1_DESIGN_2026-07-17](AIOS_LEARNOS_S1_DESIGN_2026-07-17.md) | LearnOS S+1 — pivot design (2026-07-17), grounded in Radar Sweep 01 |
| ANCHOR | 8 | [AIOS_ECOSYSTEM_BLUEPRINT](AIOS_ECOSYSTEM_BLUEPRINT.md) | AIOS Ecosystem Blueprint — built from a code-level teardown of real agent CLIs |
| OPEN | 7 | [AIOS_AKASHIC_DISTRIBUTED_DESIGN](AIOS_AKASHIC_DISTRIBUTED_DESIGN.md) | AkashicRecord — 분산 검증 가능 원장 설계 |
| CLOSED | 7 | [AIOS_BASE_ARCHITECTURE_AUDIT](AIOS_BASE_ARCHITECTURE_AUDIT.md) | AIOS Base Architecture Audit |
| REFERENCE | 7 | [AIOS_OFFLINE_USER_AGENT_PROTOCOL](AIOS_OFFLINE_USER_AGENT_PROTOCOL.md) | AIOS Offline User Agent Protocol |
| REFERENCE | 6 | [AIOS_AGENTNET_DESIGN](AIOS_AGENTNET_DESIGN.md) | AIOS AgentNet Design |
| CLOSED | 4 | [AGENT_LOOP_ARCHITECTURE](AGENT_LOOP_ARCHITECTURE.md) | Agent Loop Architecture — 공부 자산 |
| CLOSED | 4 | [AIOS_HIVEMIND_DESIGN](AIOS_HIVEMIND_DESIGN.md) | AIOS Hivemind v0 — design spec (grounded, team-reviewed) |
| REFERENCE | 3 | [AIOS_DESIGN_PRUNED_BY_MEASUREMENT_2026-08-13](AIOS_DESIGN_PRUNED_BY_MEASUREMENT_2026-08-13.md) | 설계를 측정으로 가지치기 — GPT 6턴 설계 중 무엇이 이미 죽었나 |
| CLOSED | 3 | [AIOS_SOVEREIGN_COORDINATION_STACK_2026-07-22](AIOS_SOVEREIGN_COORDINATION_STACK_2026-07-22.md) | AIOS Sovereign Coordination Stack — 통신/보안/기록/저장 systematization (2026-07-22) |
| REFERENCE | 2 | [AGI_MISSING_LINK_AND_HOMEOSTASIS_DESIGN](AGI_MISSING_LINK_AND_HOMEOSTASIS_DESIGN.md) | AGI의 부재 원인과 AIOS의 직관적 극복 설계도 (The Missing Link to AGI) |
| CLOSED | 2 | [AIOS_COMMS_ARCHITECTURE](AIOS_COMMS_ARCHITECTURE.md) | AIOS Communication Architecture — researched, not asserted |
| REFERENCE | 2 | [RECURSIVE_ORGANIC_SYSTEM_DESIGN](RECURSIVE_ORGANIC_SYSTEM_DESIGN.md) | Recursive Organic System Design (2026) |
| REFERENCE | 0 | [AIOS_SUBSTRATE_SPINE_2026-08-18](AIOS_SUBSTRATE_SPINE_2026-08-18.md) | 척추 설계 — CLI를 엮지 않고 직접 부른다, 그리고 그 주장을 어떻게 재는가 (2026-08-18) |

## 판정·검토 (16)

| 상태 | 피인용 | 문서 | 제목 |
|---|---:|---|---|
| ANCHOR | 24 | [AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01](AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md) | Accumulated Experience Does Not Compound on a Frozen Agent: a Pre-Registered Three-Transport Nu |
| ANCHOR | 13 | [AIOS_MEMORY_REVIEW](AIOS_MEMORY_REVIEW.md) | AIOS Memory Review |
| ANCHOR | 10 | [AIOS_AGENT_COMPANY_STUDIO_BRIEF](AIOS_AGENT_COMPANY_STUDIO_BRIEF.md) | AIOS Agent Company Studio Brief |
| ANCHOR | 10 | [AIOS_GOVERNANCE_AUDIT](AIOS_GOVERNANCE_AUDIT.md) | AIOS Governance Audit |
| CLOSED | 6 | [WORKFLOW_EVAL_REPORT_V1](WORKFLOW_EVAL_REPORT_V1.md) | Runtime Workflow Capsule V1 Evaluation |
| CLOSED | 5 | [AIOS_SYNTHESIS_INVENTIONS](AIOS_SYNTHESIS_INVENTIONS.md) | AIOS Synthesis Inventions — extracted, woven, twisted, created |
| CLOSED | 5 | [CRITIQUE](CRITIQUE.md) | Fable 5 — Adversarial Audit of the AIOS / AGI-Certification Program |
| CLOSED | 5 | [MEMORYOS_CONSUMER_REPORT_2026-08-09](MEMORYOS_CONSUMER_REPORT_2026-08-09.md) | memoryOS 소비자 리포트 — prizehunter 가 실제로 써보고 남기는 요청서 |
| REFERENCE | 4 | [AIOS_FRONTIER_BRIEF_2026-07-10](AIOS_FRONTIER_BRIEF_2026-07-10.md) | World-Grounding Brief — 2026-07-10 (agent-OS / AGI frontier) |
| CLOSED | 4 | [AIOS_STATE_AND_ORGANISM_SYNTHESIS_2026-07-22](AIOS_STATE_AND_ORGANISM_SYNTHESIS_2026-07-22.md) | AIOS — full-system state + the organism reframe (2026-07-22 capstone) |
| CLOSED | 3 | [AIOS_INTERNAL_STATE_AUDIT_2026-05-17](AIOS_INTERNAL_STATE_AUDIT_2026-05-17.md) | AIOS Internal-State Audit — 2026-05-17 |
| REFERENCE | 2 | [AIOS_COUNCIL_VERDICT_2026-07-17](AIOS_COUNCIL_VERDICT_2026-07-17.md) | Council 적대 QA 판정 (2026-07-17) — "조립/라우팅은 cope, 학습으로 되돌려라" |
| CLOSED | 2 | [AIOS_SOVEREIGN_SESSION_REVIEW_2026-08-16](AIOS_SOVEREIGN_SESSION_REVIEW_2026-08-16.md) | Sovereign 세션 산출물 검토 — claude@myworld/upper 입장에서 |
| CLOSED | 2 | [H1_CLAUDE_FAMILY_AUDIT](H1_CLAUDE_FAMILY_AUDIT.md) | H1 — Claude-Family Audit: how Claude workers fail here, and how the directive stack shapes it |
| REFERENCE | 2 | [VERDICT-mathematical-tricks-for-failed-experiments](VERDICT-mathematical-tricks-for-failed-experiments.md) | Operator verdict — "Mathematical tricks to resuscitate failed experiments" (agy artifact) |
| CLOSED | 1 | [SOCIAL_PREVIEW](SOCIAL_PREVIEW.md) | Social preview / og-image + repo metadata |

## 기억·온톨로지 (6)

| 상태 | 피인용 | 문서 | 제목 |
|---|---:|---|---|
| ANCHOR | 95 | [AIOS_MEMORY_AUTO_WRITEBACK](AIOS_MEMORY_AUTO_WRITEBACK.md) | AIOS Memory Auto-Writeback |
| ANCHOR | 12 | [MEMORYOS_AGENT](MEMORYOS_AGENT.md) | MemoryOS Agent File |
| CLOSED | 4 | [LGM_AND_MEMORY_GRAPH_CONTROL](LGM_AND_MEMORY_GRAPH_CONTROL.md) | LGM and Memory-Graph Control — Frontier Research for AIOS |
| CLOSED | 1 | [AIOS_KNOWLEDGE_GRAPH_2026-08-18](AIOS_KNOWLEDGE_GRAPH_2026-08-18.md) | 지식그래프와 유기체 감사 — 산문은 이어져 있고 실행기관과 증거는 끊겨 있다 (2026-08-18) |
| REFERENCE | 1 | [GALAXY_AKASHIC_INTEGRATION_REQUEST](GALAXY_AKASHIC_INTEGRATION_REQUEST.md) | INTEGRATION REQUEST — Work Galaxy ↔ AIOS Akashic (galaxy = AIOS의 통합 비주얼) |
| CLOSED | 1 | [OAKLAB_AGI_ONTOLOGY_2026-07-17](OAKLAB_AGI_ONTOLOGY_2026-07-17.md) | OakLab AGI Ontology |

## 사회·에이전트 (25)

| 상태 | 피인용 | 문서 | 제목 |
|---|---:|---|---|
| ANCHOR | 5829 | [AGENT_WORKLOG](AGENT_WORKLOG.md) | AIOS Agent Worklog |
| OPEN | 1371 | [AIOS_AGENT_LEDGER](AIOS_AGENT_LEDGER.md) | AIOS Agent Ledger |
| ANCHOR | 29 | [AIOS_AGENT_INTERFACE](AIOS_AGENT_INTERFACE.md) | AIOS Agent Interface v0.1 |
| ANCHOR | 29 | [AIOS_AGENT_SELF_LOOP](AIOS_AGENT_SELF_LOOP.md) | AIOS Agent Self-Loop Doctrine |
| ANCHOR | 27 | [AIOS_AGENT_OPERATING_LAYER_DRAFT](AIOS_AGENT_OPERATING_LAYER_DRAFT.md) | AIOS: An Agent Operating Layer for Reliable Long-Running AI Work |
| ANCHOR | 16 | [AIOS_SOCIETY_GOALTREE_2026-08-02](AIOS_SOCIETY_GOALTREE_2026-08-02.md) | AIOS = AI Society — 목표 트리 (2026-08-02) · **2026-08-05 판정으로 종료** |
| ANCHOR | 13 | [HIVEMIND_AGENT](HIVEMIND_AGENT.md) | Hive Mind Agent File |
| ANCHOR | 12 | [CAPABILITYOS_AGENT](CAPABILITYOS_AGENT.md) | CapabilityOS Agent File |
| ANCHOR | 11 | [AIOS_AGENT_SERVICE_BASELINE_2026-06-13](AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md) | AIOS Agent-Service Baseline — 2026-06-13 |
| ANCHOR | 10 | [AIOS_AGENTS_REGISTRY](AIOS_AGENTS_REGISTRY.md) | AIOS Agents Registry |
| ANCHOR | 10 | [AIOS_AGENT_SERVICE_INFRA_DELTA_2026-06-14](AIOS_AGENT_SERVICE_INFRA_DELTA_2026-06-14.md) | AIOS Agent-Service Infrastructure Delta |
| ANCHOR | 9 | [AIOS_AGENT_OPERATING_LAYER_REFINEMENT](AIOS_AGENT_OPERATING_LAYER_REFINEMENT.md) | AIOS Agent Operating Layer Paper Refinement Loop |
| ANCHOR | 9 | [AIOS_OPENAI_AGENT_SURFACE_DELTA_2026-06-19](AIOS_OPENAI_AGENT_SURFACE_DELTA_2026-06-19.md) | AIOS OpenAI Agent Surface Delta |
| ANCHOR | 9 | [CODEX_UI_AGENT](CODEX_UI_AGENT.md) | Codex UI Agent |
| ANCHOR | 9 | [GENESIS_AGENT](GENESIS_AGENT.md) | GenesisOS Agent |
| REFERENCE | 5 | [AGENT_MULTIPLEXER_LANDSCAPE](AGENT_MULTIPLEXER_LANDSCAPE.md) | Agent Multiplexer Landscape (2025-2026) |
| CLOSED | 5 | [AIOS_AGENT_LIFE](AIOS_AGENT_LIFE.md) | AIOS Agent Life — 인생사 (the agent's accumulating life story) |
| CLOSED | 5 | [AIOS_HIVEMIND_PROOFS](AIOS_HIVEMIND_PROOFS.md) | AIOS Hivemind — verifier-settled collective problem-solving (scoped to formal proofs) |
| REFERENCE | 4 | [AIOS_AGENT_ENGINEERING_STUDY](AIOS_AGENT_ENGINEERING_STUDY.md) | AIOS Agent Engineering Study |
| REFERENCE | 4 | [AIOS_SOCIETY_AS_COMPUTE_SYSTEM_2026-08-03](AIOS_SOCIETY_AS_COMPUTE_SYSTEM_2026-08-03.md) | 사회를 컴퓨트 시스템으로 — 무엇을 매핑하고, 무엇을 매핑하면 안 되는가 (2026-08-03) |
| CLOSED | 3 | [AGENT_BEHAVIOR_STUDY](AGENT_BEHAVIOR_STUDY.md) | Agent Behavior Patterns — 벤치마크 자산화 |
| REFERENCE | 3 | [AIOS_ORCA_PEER_ANALYSIS_2026-08-03](AIOS_ORCA_PEER_ANALYSIS_2026-08-03.md) | Orca — 우리 설계의 일부가 이미 제품으로 나온 사례 (2026-08-03) |
| REFERENCE | 3 | [AIOS_SOVEREIGN_SOCIETY_ASSEMBLER_2026-07-17](AIOS_SOVEREIGN_SOCIETY_ASSEMBLER_2026-07-17.md) | AIOS = 소버린 사회-조립자 (crystallization, 2026-07-17) |
| CLOSED | 1 | [AIOS_EVOLUTIONARY_SOCIETY_AND_COUNCIL_LOOP](AIOS_EVOLUTIONARY_SOCIETY_AND_COUNCIL_LOOP.md) | AIOS Evolutionary Agent Society & Open-Source Council Loop |
| REFERENCE | 1 | [AIOS_SESSION_LOG_2026-08-16_SOVEREIGN_EVOLUTION](AIOS_SESSION_LOG_2026-08-16_SOVEREIGN_EVOLUTION.md) | 1. 단일 프롬프트 Sovereign 웹 앱 실행 (추천) |

## 운영·계약 (11)

| 상태 | 피인용 | 문서 | 제목 |
|---|---:|---|---|
| ANCHOR | 5637 | [AIOS_WORK_DISPATCH](AIOS_WORK_DISPATCH.md) | AIOS Work Dispatch |
| ANCHOR | 375 | [AIOS_SMART_CONTRACT](AIOS_SMART_CONTRACT.md) | AIOS Smart Contract |
| ANCHOR | 145 | [WORKSTREAMS](WORKSTREAMS.md) | AIOS Workstreams |
| ANCHOR | 97 | [AIOS_OPERATOR_PLAYBOOK](AIOS_OPERATOR_PLAYBOOK.md) | AIOS Operator Playbook — claude@myworld |
| ANCHOR | 18 | [AIOS_MYWORLD_CLAIM_LEDGER](AIOS_MYWORLD_CLAIM_LEDGER.md) | AIOS MyWorld Paper Claim Ledger |
| ANCHOR | 17 | [FRONTIER_KNOWLEDGE_LEDGER_2026-07-17](FRONTIER_KNOWLEDGE_LEDGER_2026-07-17.md) | Frontier Knowledge Ledger — 세팅 (schema + taxonomy) 2026-07-17 |
| REFERENCE | 6 | [AIOS_CONTRACT_EXECUTION_ORDER](AIOS_CONTRACT_EXECUTION_ORDER.md) | AIOS Contract Execution Order |
| REFERENCE | 6 | [AIOS_CONTRACT_RECONCILIATION](AIOS_CONTRACT_RECONCILIATION.md) | AIOS Contract Reconciliation |
| REFERENCE | 4 | [AIOS_CONTRACT_OBJECT_V0](AIOS_CONTRACT_OBJECT_V0.md) | AIOS ContractObject v0 |
| CLOSED | 3 | [AIOS_CROSS_SESSION_POSITION_2026-08-13](AIOS_CROSS_SESSION_POSITION_2026-08-13.md) | 세션 간 대화 — 전송은 출하됐고, 그 위층이 비어 있다 |
| CLOSED | 1 | [LEDGER_MERGED_SUMMARY_2026-07-17](LEDGER_MERGED_SUMMARY_2026-07-17.md) | Unified Knowledge Ledger — merge summary (2026-07-17) |

## 기타 (491)

| 상태 | 피인용 | 문서 | 제목 |
|---|---:|---|---|
| ANCHOR | 5261 | [AIOS_BUILD_METHOD](AIOS_BUILD_METHOD.md) | AIOS Build Method |
| ANCHOR | 4833 | [AIOS_GOVERNANCE_MODEL](AIOS_GOVERNANCE_MODEL.md) | AIOS Governance Model |
| ANCHOR | 4377 | [AIOS_CONTROL_APP](AIOS_CONTROL_APP.md) | AIOS Control App |
| ANCHOR | 438 | [AIOS_REPO_GOAL_LOOP](AIOS_REPO_GOAL_LOOP.md) | AIOS Repo Goal Loop |
| ANCHOR | 427 | [README](README.md) | AIOS Smart Contracts |
| SUPERSEDED | 379 | [AIOS_NORTHSTAR](AIOS_NORTHSTAR.md) | AIOS North Star |
| ANCHOR | 172 | [AIOS_CLAUDE_SELF_OBSERVATION_LOG](AIOS_CLAUDE_SELF_OBSERVATION_LOG.md) | AIOS Claude CLI Self-Observation Log |
| ANCHOR | 168 | [README](README.md) | MyWorld AIOS Docs |
| ANCHOR | 153 | [AIOS_DEFINITION](AIOS_DEFINITION.md) | AIOS Definition |
| ANCHOR | 126 | [AIOS_SHARED_LANGUAGE](AIOS_SHARED_LANGUAGE.md) | AIOS Shared Language |
| ANCHOR | 107 | [AIOS-GOAL-0001-make-something-great](AIOS-GOAL-0001-make-something-great.md) | AIOS-GOAL-0001 Make Something Great |
| ANCHOR | 105 | [AIOS_PRODUCTION_PRAXIS](AIOS_PRODUCTION_PRAXIS.md) | AIOS Production Praxis |
| ANCHOR | 102 | [AIOS-GOAL-0001-evolution](AIOS-GOAL-0001-evolution.md) | AIOS Goal Evolution Plan |
| ANCHOR | 94 | [AIOS_LOOP_POLICY](AIOS_LOOP_POLICY.md) | AIOS Loop Policy Snapshot |
| ANCHOR | 60 | [ASC-0180-hive-debate-aios-hosting-trust-model](ASC-0180-hive-debate-aios-hosting-trust-model.md) | ASC-0180 Hive Debate — AIOS Hosting & DNA Trust Model |
| ANCHOR | 49 | [AIOS_DNA](AIOS_DNA.md) | AIOS DNA v0 |
| ANCHOR | 47 | [AIOS_TASK_RADAR](AIOS_TASK_RADAR.md) | AIOS Task Radar |
| ANCHOR | 45 | [ASC-0213-closure-quality-gate](ASC-0213-closure-quality-gate.md) | ASC-0213 — Closure Quality Gate |
| ANCHOR | 43 | [ASC-0183-dream-parametric-per-repo-adapters](ASC-0183-dream-parametric-per-repo-adapters.md) | ASC-0183 Dream — Parametric Per-Repo Adapters |
| ANCHOR | 41 | [ASC-0215-peer-blindspot-7day-experiments](ASC-0215-peer-blindspot-7day-experiments.md) | ASC-0215 — Peer Blindspot 7-day Experiments |
| ANCHOR | 28 | [WORK_INTAKE](WORK_INTAKE.md) | AIOS Work Intake — 작업 접수 체계 |
| ANCHOR | 26 | [AIOS_CHAT](AIOS_CHAT.md) | AIOS Chat |
| ANCHOR | 20 | [ASC-0099-aios-address-space](ASC-0099-aios-address-space.md) | ASC-0099 AIOS Address Space |
| ANCHOR | 20 | [ASC-0270-aios-dream-expansion-claude-hardening](ASC-0270-aios-dream-expansion-claude-hardening.md) | ASC-0270 AIOS Dream Expansion Claude Hardening |
| ANCHOR | 19 | [AIOS_AGI_CONCEPTION_2026-07-17](AIOS_AGI_CONCEPTION_2026-07-17.md) | AGI as a Compounding Loop — claude@myworld's conception (2026-07-17) |
| ANCHOR | 19 | [AIOS_CODEX_CLI_ABSORPTION](AIOS_CODEX_CLI_ABSORPTION.md) | AIOS Codex CLI Absorption |
| ANCHOR | 19 | [AIOS_SUBSTRATE_BOUNDARY](AIOS_SUBSTRATE_BOUNDARY.md) | AIOS Substrate Boundary |
| ANCHOR | 19 | [ASC-0253-end-user-serving-prototype-scope](ASC-0253-end-user-serving-prototype-scope.md) | ASC-0253 End-User Serving Prototype Scope |
| ANCHOR | 18 | [AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22](AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22.md) | AIOS Organism Assembly — durable phased plan + progress log (2026-07-22) |
| ANCHOR | 18 | [AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10](AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md) | AIOS 재정의 + AGI 마스터플랜 (2026-07-10) |
| ANCHOR | 18 | [ASC-0260-real-user-serving-release-spine](ASC-0260-real-user-serving-release-spine.md) | ASC-0260 Real User Serving Release Spine |
| ANCHOR | 18 | [ASC-0267-serving-support-redaction](ASC-0267-serving-support-redaction.md) | ASC-0267 Serving Support Redaction |
| ANCHOR | 18 | [ASC-0271-dream-hardening-invariant-pack](ASC-0271-dream-hardening-invariant-pack.md) | ASC-0271 Dream Hardening Invariant Pack |
| ANCHOR | 18 | [ASC-0273-capabilityos-credential-grants-and-blindspots](ASC-0273-capabilityos-credential-grants-and-blindspots.md) | ASC-0273 CapabilityOS Credential Grants And Blindspots |
| ANCHOR | 17 | [2026-05-11-jaewon-search](2026-05-11-jaewon-search.md) | Jaewon Workspace Search — 2026-05-11 |
| ANCHOR | 17 | [AIOS_END_USER_SERVING_INTERFACE_SPEC](AIOS_END_USER_SERVING_INTERFACE_SPEC.md) | AIOS End-User Serving Interface Spec |
| ANCHOR | 17 | [ASC-0263-hivemind-serving-worker-resume](ASC-0263-hivemind-serving-worker-resume.md) | ASC-0263 Hivemind Serving Worker Resume |
| ANCHOR | 17 | [ASC-0272-memoryos-dream-agora-intake](ASC-0272-memoryos-dream-agora-intake.md) | ASC-0272 MemoryOS Dream Agora Intake |
| ANCHOR | 16 | [AIOS_ACTION_POLICY](AIOS_ACTION_POLICY.md) | AIOS Action Policy |
| ANCHOR | 16 | [AIOS_OPERATING_LOOP](AIOS_OPERATING_LOOP.md) | AIOS Operating Loop |
| ANCHOR | 16 | [ASC-0255-end-user-serving-runtime-session-boundary](ASC-0255-end-user-serving-runtime-session-boundary.md) | ASC-0255 End-User Serving Runtime Session Boundary |
| ANCHOR | 15 | [2026-06-14-aios-dream-explosive-expansion](2026-06-14-aios-dream-explosive-expansion.md) | AIOS Dream: Explosive Expansion Map |
| ANCHOR | 15 | [AIOS_ADDRESS_SPACE](AIOS_ADDRESS_SPACE.md) | AIOS Address Space |
| ANCHOR | 15 | [AIOS_AGI_CERTIFICATION_KEYSTONE](AIOS_AGI_CERTIFICATION_KEYSTONE.md) | AIOS as an AGI Certification Layer — thesis, adversarial verdict, and the specified keystone wi |
| ANCHOR | 15 | [AIOS_SERVING_INTERFACE_ROUTE_MAP](AIOS_SERVING_INTERFACE_ROUTE_MAP.md) | AIOS Serving Interface Route Map |
| ANCHOR | 15 | [ASC-0234-world-deployable-aios-readiness-spine](ASC-0234-world-deployable-aios-readiness-spine.md) | ASC-0234 World-Deployable AIOS Readiness Spine |
| ANCHOR | 15 | [ASC-0249-build-runtime-isolation-boundary](ASC-0249-build-runtime-isolation-boundary.md) | ASC-0249 Build/Runtime Isolation Boundary |
| ANCHOR | 15 | [ASC-0252-serving-readiness-gate-correction](ASC-0252-serving-readiness-gate-correction.md) | ASC-0252 Serving Readiness Gate Correction |
| ANCHOR | 15 | [ASC-0264-memoryos-serving-memory-lifecycle](ASC-0264-memoryos-serving-memory-lifecycle.md) | ASC-0264 MemoryOS Serving Memory Lifecycle |
| ANCHOR | 15 | [ASC-0275-genesisos-entropy-quota-enforcement](ASC-0275-genesisos-entropy-quota-enforcement.md) | ASC-0275 GenesisOS Entropy Quota Enforcement |
| ANCHOR | 15 | [ASC-0276-agent-company-studio-gate-a-framing](ASC-0276-agent-company-studio-gate-a-framing.md) | ASC-0276 Agent Company Studio Gate A Framing |
| SUPERSEDED | 14 | [AIOS_CANONICAL_SHAPE](AIOS_CANONICAL_SHAPE.md) | AIOS Canonical Shape |
| ANCHOR | 14 | [ASC-0257-dispatch-cancel-archive-reissue](ASC-0257-dispatch-cancel-archive-reissue.md) | ASC-0257 Dispatch Cancel Archive Reissue |
| ANCHOR | 14 | [ASC-0258-serving-design-gate](ASC-0258-serving-design-gate.md) | ASC-0258 Serving Design Gate |
| ANCHOR | 14 | [ASC-0259-serving-design-gate-intake](ASC-0259-serving-design-gate-intake.md) | ASC-0259 Serving Design Gate Intake |
| ANCHOR | 14 | [ASC-0265-capabilityos-serving-access-routing](ASC-0265-capabilityos-serving-access-routing.md) | ASC-0265 CapabilityOS Serving Access Routing |
| ANCHOR | 14 | [ASC-0266-genesisos-serving-prelaunch-challenge](ASC-0266-genesisos-serving-prelaunch-challenge.md) | ASC-0266 GenesisOS Serving Prelaunch Challenge |
| ANCHOR | 14 | [ASC-0274-smx-bounded-workspace-contract-split](ASC-0274-smx-bounded-workspace-contract-split.md) | ASC-0274 SMX Bounded Workspace Contract Split |
| ANCHOR | 13 | [ASC-0236-credential-broker-boundary](ASC-0236-credential-broker-boundary.md) | ASC-0236 Credential Broker Boundary |
| ANCHOR | 13 | [ASC-0237-memoryos-akashic-work-lineage-replay-index](ASC-0237-memoryos-akashic-work-lineage-replay-index.md) | ASC-0237 MemoryOS Akashic Work-Lineage Replay Index |
| ANCHOR | 13 | [ASC-0251-end-user-serving-interface-spine](ASC-0251-end-user-serving-interface-spine.md) | ASC-0251 End-User Serving Interface Spine |
| ANCHOR | 13 | [ASC-0256-dispatch-agent-binding-hygiene](ASC-0256-dispatch-agent-binding-hygiene.md) | ASC-0256 Dispatch Agent Binding Hygiene |
| ANCHOR | 12 | [2026-05-13-asc-0053-execution-layer-escalation](2026-05-13-asc-0053-execution-layer-escalation.md) | ASC-0053 Execution-Layer Escalation — 2026-05-13 |
| ANCHOR | 12 | [AIOS_DRIFTBENCH_RECONCILIATION_2026-07-11](AIOS_DRIFTBENCH_RECONCILIATION_2026-07-11.md) | DriftBench 이중 하니스 화해 결정 (operator, 2026-07-11) |
| ANCHOR | 12 | [AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY](AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY.md) | AIOS Negative Evidence And Combinatorial Creativity |
| ANCHOR | 12 | [AIOS_PRIMITIVES](AIOS_PRIMITIVES.md) | AIOS Primitives — substrate-independent operator surface |
| ANCHOR | 12 | [ASC-0250-build-runtime-isolation-finish-forward](ASC-0250-build-runtime-isolation-finish-forward.md) | ASC-0250 Build/Runtime Isolation Finish-Forward |
| ANCHOR | 12 | [ASC-0254-myworld-provider-dispatch-bridge](ASC-0254-myworld-provider-dispatch-bridge.md) | ASC-0254 MyWorld Provider Dispatch Bridge |
| SUPERSEDED | 12 | [ASC-0271-aios-growth-hardening-invariant-pack](ASC-0271-aios-growth-hardening-invariant-pack.md) | ASC-0271-AUX AIOS Growth Hardening Invariant Pack |
| ANCHOR | 12 | [ASC-0277-memoryos-cli-log-asset-pool-ledger](ASC-0277-memoryos-cli-log-asset-pool-ledger.md) | ASC-0277 MemoryOS CLI Log Asset Pool Ledger |
| ANCHOR | 11 | [2026-05-12-uri-personal-agent-pivot](2026-05-12-uri-personal-agent-pivot.md) | Uri Personal Agent Pivot — 2026-05-12 |
| ANCHOR | 11 | [2026-05-15-hive-observer-vs-executor-debate-result](2026-05-15-hive-observer-vs-executor-debate-result.md) | Hive Observer-vs-Executor Debate Result |
| ANCHOR | 11 | [AIOS_AGI_ENGINE_THESIS](AIOS_AGI_ENGINE_THESIS.md) | AIOS as an AGI Engine — frontier map + earned positioning (2026-07-04) |
| ANCHOR | 11 | [AIOS_RELATED_WORK_SOURCE_RECEIPT](AIOS_RELATED_WORK_SOURCE_RECEIPT.md) | AIOS Related Work Source Receipt |
| ANCHOR | 11 | [ASC-0214-aios-dogfooding-gap](ASC-0214-aios-dogfooding-gap.md) | ASC-0214 — AIOS Dogfooding Gap |
| ANCHOR | 11 | [ASC-0235-world-deployment-readiness-cli](ASC-0235-world-deployment-readiness-cli.md) | ASC-0235 World Deployment Readiness CLI |
| ANCHOR | 11 | [ASC-0240-hive-hosted-runtime-isolation-receipts](ASC-0240-hive-hosted-runtime-isolation-receipts.md) | ASC-0240 Hive Hosted Runtime Isolation Receipts |
| ANCHOR | 11 | [ASC-0242-packaging-smoke-and-credential-broker-adoption](ASC-0242-packaging-smoke-and-credential-broker-adoption.md) | ASC-0242 Packaging Smoke And Credential Broker Adoption |
| ANCHOR | 11 | [ASC-0282-m2-driftbench-closed-loop](ASC-0282-m2-driftbench-closed-loop.md) | ASC-0282 — M2 DriftBench closed-loop keystone (+ real-dispatch shadow-mode) |
| ANCHOR | 10 | [2026-05-14-hive-ecosystem-substrate-debate-result](2026-05-14-hive-ecosystem-substrate-debate-result.md) | Hive Ecosystem Substrate Debate Result |
| ANCHOR | 10 | [2026-05-15-observer-vs-executor-prior-art](2026-05-15-observer-vs-executor-prior-art.md) | Study: Observer vs Executor Framing for AIOS |
| ANCHOR | 10 | [AIOS_CLOSE_CONDITION](AIOS_CLOSE_CONDITION.md) | AIOS Close Condition |
| ANCHOR | 10 | [AIOS_INVOCATION_PIPELINE](AIOS_INVOCATION_PIPELINE.md) | AIOS Invocation Pipeline |
| ANCHOR | 10 | [AIOS_MINIMAL_OPERATION_2026-08-09](AIOS_MINIMAL_OPERATION_2026-08-09.md) | OS의 최소동작 — 필라멘트에 불이 들어오는 순간 (초안 v0, 2026-08-09) |
| ANCHOR | 10 | [AIOS_NORTHSTAR_READY](AIOS_NORTHSTAR_READY.md) | AIOS North Star Ready — Definition of Complete |
| ANCHOR | 10 | [AIOS_RUNTIME](AIOS_RUNTIME.md) | AIOS Runtime |
| ANCHOR | 10 | [ASC-0241-live-hosted-run-proof-and-akashic-projection](ASC-0241-live-hosted-run-proof-and-akashic-projection.md) | ASC-0241 Live Hosted-Run Proof And Akashic Projection |
| ANCHOR | 10 | [ASC-0243-hosted-backend-selection-and-release-archive-smoke](ASC-0243-hosted-backend-selection-and-release-archive-smoke.md) | ASC-0243 Hosted Backend Selection And Release Archive Smoke |
| ANCHOR | 10 | [ASC-0245-kernel-authority-correctness](ASC-0245-kernel-authority-correctness.md) | ASC-0245 Kernel Authority Correctness |
| ANCHOR | 10 | [ASC-0268-serving-product-design-ideation](ASC-0268-serving-product-design-ideation.md) | ASC-0268 Serving Product Design Ideation |
| ANCHOR | 10 | [ASC-0279-world-service-objective-audit](ASC-0279-world-service-objective-audit.md) | ASC-0279 World-Service Objective Audit |
| ANCHOR | 9 | [2026-05-13-hive-asc0088-alternatives-debate-result](2026-05-13-hive-asc0088-alternatives-debate-result.md) | Hive ASC-0088 Alternatives Debate Result |
| ANCHOR | 9 | [2026-05-13-hive-living-organism-debate-result](2026-05-13-hive-living-organism-debate-result.md) | Hive Living Organism Debate Result |
| ANCHOR | 9 | [AIOS_COEVOLUTION](AIOS_COEVOLUTION.md) | AIOS Co-Evolution Heartbeat |
| ANCHOR | 9 | [AIOS_DEPLOY_MANIFEST](AIOS_DEPLOY_MANIFEST.md) | AIOS Deploy Manifest |
| ANCHOR | 9 | [AIOS_PROVIDER_ABSORPTION](AIOS_PROVIDER_ABSORPTION.md) | AIOS Provider Absorption |
| ANCHOR | 9 | [ASC-0212-aios-mcp-native](ASC-0212-aios-mcp-native.md) | ASC-0212 — AIOS MCP-native |
| ANCHOR | 9 | [ASC-0238-skillos-recommendation-registry](ASC-0238-skillos-recommendation-registry.md) | ASC-0238 SkillOS Recommendation Registry |
| ANCHOR | 9 | [ASC-0239-genesis-seci-entropy-closeout-gate](ASC-0239-genesis-seci-entropy-closeout-gate.md) | ASC-0239 Genesis SECI Entropy Closeout Gate |
| ANCHOR | 9 | [ASC-0244-service-readiness-monitor-unblock](ASC-0244-service-readiness-monitor-unblock.md) | ASC-0244 Service Readiness Monitor Unblock |
| ANCHOR | 9 | [ASC-0247-planner-call-receipt-boundary](ASC-0247-planner-call-receipt-boundary.md) | ASC-0247 Planner Call Receipt Boundary |
| ANCHOR | 9 | [ASC-0261-production-serving-release-gate](ASC-0261-production-serving-release-gate.md) | ASC-0261 Production Serving Release Gate |
| ANCHOR | 9 | [ASC-0262-agent-service-baseline-and-serving-ideation-brief](ASC-0262-agent-service-baseline-and-serving-ideation-brief.md) | ASC-0262 Agent-Service Baseline And Serving Ideation Brief |
| ANCHOR | 9 | [ASC-0269-serving-design-target-selection-cli](ASC-0269-serving-design-target-selection-cli.md) | ASC-0269 Serving Design Target Selection CLI |
| SUPERSEDED | 9 | [ASC-0278-openai-agent-surface-absorption](ASC-0278-openai-agent-surface-absorption.md) | ASC-0278 OpenAI Agent Surface Absorption |
| ANCHOR | 9 | [RESEARCH_GROUNDING](RESEARCH_GROUNDING.md) | Research grounding — the AIOS research spine |
| ANCHOR | 8 | [2026-05-13-hive-aios-dna-debate-result](2026-05-13-hive-aios-dna-debate-result.md) | Hive AIOS DNA Debate Result |
| ANCHOR | 8 | [AIOS_FOUNDER_INGESTION](AIOS_FOUNDER_INGESTION.md) | AIOS Founder Ingestion |
| ANCHOR | 8 | [AIOS_WHAT_THE_OS_IS_2026-08-09](AIOS_WHAT_THE_OS_IS_2026-08-09.md) | 그래서 OS는 무엇인가 — 우리 측정만으로 답한다 (2026-08-09) |
| ANCHOR | 8 | [ASC-0225-substrate-boundary-classifier](ASC-0225-substrate-boundary-classifier.md) | ASC-0225 Substrate Boundary Classifier |
| ANCHOR | 8 | [ASC-0246-kernel-authority-correctness-fix-forward](ASC-0246-kernel-authority-correctness-fix-forward.md) | ASC-0246 Kernel Authority Correctness Fix-Forward |
| ANCHOR | 8 | [ASC-0248-dispatch-lease-collision-control](ASC-0248-dispatch-lease-collision-control.md) | ASC-0248 Dispatch Lease Collision Control |
| REFERENCE | 7 | [AIOS_ABSORPTION_BACKLOG](AIOS_ABSORPTION_BACKLOG.md) | AIOS Absorption Backlog — ecosystem ideas → AIOS development |
| CLOSED | 7 | [AIOS_ABSORPTION_SCAN_2026-07-22](AIOS_ABSORPTION_SCAN_2026-07-22.md) | AIOS Absorption Scan — 2026-07-22 (Grok Build · Kimi K3 · OSS delta) |
| REFERENCE | 7 | [AIOS_ECOSYSTEM_BORROW_PLAN](AIOS_ECOSYSTEM_BORROW_PLAN.md) | AIOS Ecosystem Borrow Plan |
| REFERENCE | 7 | [AIOS_GLOBAL_PROJECT_DISCOVERY](AIOS_GLOBAL_PROJECT_DISCOVERY.md) | AIOS Global Project Discovery |
| REFERENCE | 7 | [AIOS_MYWORLD_PAPER_CHARTER](AIOS_MYWORLD_PAPER_CHARTER.md) | AIOS MyWorld Paper Charter |
| CLOSED | 7 | [AIOS_PERSONA_AXIS](AIOS_PERSONA_AXIS.md) | AIOS 5-Persona Axis |
| REFERENCE | 7 | [AIOS_PROVIDER_PROMPTS](AIOS_PROVIDER_PROMPTS.md) | AIOS Provider Prompts |
| REFERENCE | 7 | [AIOS_SWARM_NORTHSTAR](AIOS_SWARM_NORTHSTAR.md) | AIOS Swarm North Star |
| REFERENCE | 7 | [AIOS_USER_PATTERNS](AIOS_USER_PATTERNS.md) | AIOS User Patterns |
| REFERENCE | 7 | [ASC-0208-uri-testbed-first-integration](ASC-0208-uri-testbed-first-integration.md) | ASC-0208 uri Testbed First Integration |
| CLOSED | 7 | [LAUNCH](LAUNCH.md) | AIOS Launch Plan (draft — not posted anywhere) |
| REFERENCE | 7 | [overview](overview.md) | Overview |
| REFERENCE | 7 | [product_recap__uri__URI-210](product_recap__uri__URI-210.md) | Product Recap — uri / URI-210 |
| REFERENCE | 7 | [product_recap__uri__URI-211](product_recap__uri__URI-211.md) | Product Recap — uri / URI-211 |
| CLOSED | 7 | [workflows](workflows.md) | Orchestrate subagents at scale with dynamic workflows |
| REFERENCE | 6 | [2026-05-12-claude-cli-primitives-reverse-engineering](2026-05-12-claude-cli-primitives-reverse-engineering.md) | Claude CLI Primitives — Reverse-Engineering for AIOS |
| REFERENCE | 6 | [2026-05-12-uri-growth-loop](2026-05-12-uri-growth-loop.md) | Uri Growth Loop — 2026-05-12 |
| CLOSED | 6 | [2026-05-13-codex-sprint-file-loop-pattern](2026-05-13-codex-sprint-file-loop-pattern.md) | Codex local-sprint-file loop pattern — founder hypothesis confirmed + ASC-0053 binding — 2026-0 |
| CLOSED | 6 | [2026-05-13-operator-cli-role-distillation-dialogue](2026-05-13-operator-cli-role-distillation-dialogue.md) | Operator CLI Role Distillation — Dialogue (claude + codex) |
| REFERENCE | 6 | [2026-06-04-deep-idea-exploration](2026-06-04-deep-idea-exploration.md) | 2026-06-04 Deep Idea Exploration |
| CLOSED | 6 | [AIOS_CITIZENSHIP](AIOS_CITIZENSHIP.md) | AIOS Citizenship |
| CLOSED | 6 | [AIOS_DEADLINE_COPILOT](AIOS_DEADLINE_COPILOT.md) | AIOS Deadline Copilot — capability reference |
| CLOSED | 6 | [AIOS_GITHUB_REDDIT_ALIGNMENT_MINING_2026-05-20](AIOS_GITHUB_REDDIT_ALIGNMENT_MINING_2026-05-20.md) | AIOS GitHub / Reddit Alignment Mining |
| CLOSED | 6 | [AIOS_GOAL_BAR](AIOS_GOAL_BAR.md) | AIOS Goal Bar |
| CLOSED | 6 | [AIOS_HOOKS](AIOS_HOOKS.md) | AIOS Hooks — Deterministic Enforcement |
| REFERENCE | 6 | [AIOS_INSTALL](AIOS_INSTALL.md) | Installing AIOS |
| REFERENCE | 6 | [AIOS_INSTRUCTION_INDEX](AIOS_INSTRUCTION_INDEX.md) | AIOS Instruction Index |
| REFERENCE | 6 | [AIOS_NATIVE_INSTALL](AIOS_NATIVE_INSTALL.md) | AIOS Native Install |
| CLOSED | 6 | [AIOS_PRIOR_ART_LONGHORIZON_2026-07-10](AIOS_PRIOR_ART_LONGHORIZON_2026-07-10.md) | Prior Art Deep-Dive — "weak model + epistemic runtime beats strong raw" (2026-07-10) |
| CLOSED | 6 | [AIOS_RENEWAL](AIOS_RENEWAL.md) | AIOS Renewal — One Foundation |
| CLOSED | 6 | [AIOS_SELF_IMPROVING](AIOS_SELF_IMPROVING.md) | AIOS as a Self-Improving Agent OS — the CLS architecture |
| REFERENCE | 6 | [AIOS_SHARE_INVARIANTS](AIOS_SHARE_INVARIANTS.md) | AIOS Share Invariants |
| REFERENCE | 6 | [CLAUDE_CODE_ECOSYSTEM](CLAUDE_CODE_ECOSYSTEM.md) | Claude Code Ecosystem — Internal Engineering Research |
| REFERENCE | 6 | [CODEX_CLI_ECOSYSTEM](CODEX_CLI_ECOSYSTEM.md) | OpenAI Codex CLI Ecosystem — Engineering Research |
| CLOSED | 6 | [WORKFLOW_CAPSULE_V1](WORKFLOW_CAPSULE_V1.md) | AIOS Runtime Workflow Capsule v1 |
| CLOSED | 6 | [aios_ingest_protocol_v1](aios_ingest_protocol_v1.md) | aios.ingest_protocol.v1 |
| REFERENCE | 6 | [aios_specialist_helper_v1](aios_specialist_helper_v1.md) | aios.specialist_helper.v1 |
| CLOSED | 6 | [changelog](changelog.md) | Claude Code changelog |
| CLOSED | 6 | [learning_methods](learning_methods.md) | Frontier Knowledge Ledger — D6: Learning methods (beyond frozen pretrained models) |
| CLOSED | 6 | [python](python.md) | Agent SDK reference - Python |
| REFERENCE | 6 | [rg_20260515T154529_c5d7e049ea23-needs_operator_review](rg_20260515T154529_c5d7e049ea23-needs_operator_review.md) | rg_20260515T154529_c5d7e049ea23 needs_operator_review |
| CLOSED | 6 | [security](security.md) | Security |
| CLOSED | 5 | [00_INDEX](00_INDEX.md) | Fable 5 Extraction Corpus — harvest everything before 2026-07-07 |
| REFERENCE | 5 | [2026-05-13-uri-loop-28-iter-cumulative-state](2026-05-13-uri-loop-28-iter-cumulative-state.md) | Uri /loop 28-Iter Cumulative State — Operator Return-to-Loop Brief — 2026-05-13 |
| CLOSED | 5 | [AIOS_ACTIVATION_CONDITION_2026-08-14](AIOS_ACTIVATION_CONDITION_2026-08-14.md) | 강제된 활성화가 값을 하는 조건 — A1이 옮긴 병목 |
| REFERENCE | 5 | [AIOS_CONTROL_CENTER_REFERENCE_BOARD](AIOS_CONTROL_CENTER_REFERENCE_BOARD.md) | AIOS Control Center Reference Board |
| REFERENCE | 5 | [AIOS_EXTERNAL_HEAD_DISSECTION](AIOS_EXTERNAL_HEAD_DISSECTION.md) | AIOS External Head Dissection — Hermes + OMO |
| SUPERSEDED | 5 | [AIOS_FORM_FACTOR_DECISION_2026-07-22](AIOS_FORM_FACTOR_DECISION_2026-07-22.md) | AIOS form factor — daemon? IDE? CLI? (2026-07-22) |
| CLOSED | 5 | [AIOS_GOAL_PROMPT](AIOS_GOAL_PROMPT.md) | AIOS Goal Prompt — "every run becomes a star" |
| REFERENCE | 5 | [AIOS_NETWORK_THESIS_2026-08-02](AIOS_NETWORK_THESIS_2026-08-02.md) | 어떤 네트워크를 지어야 하는가 — AIOS 대규모 네트워크 테제 (2026-08-02) |
| REFERENCE | 5 | [AIOS_ORGANISM_STATE_2026-08-09](AIOS_ORGANISM_STATE_2026-08-09.md) | 유기체 진단 — 각 OS는 에이전트에게 실제로 작동하는가 (2026-08-09) |
| REFERENCE | 5 | [AIOS_OSS_ABSORPTION_SURVEY_2026-07-10](AIOS_OSS_ABSORPTION_SURVEY_2026-07-10.md) | OSS Agent-Runtime Absorption Survey — 2026-07-10 |
| CLOSED | 5 | [AIOS_OUTSIDE_VALUE_HANDOFF_2026-06-05](AIOS_OUTSIDE_VALUE_HANDOFF_2026-06-05.md) | Outside-Value Handoff — Deadline Copilot (control-plane proof → product) |
| CLOSED | 5 | [AIOS_RESIDUAL_DECISION_VALUE_2026-08-16](AIOS_RESIDUAL_DECISION_VALUE_2026-08-16.md) | 세 실패의 공통 구조 — 이름, 그리고 내 주장 셋의 정정 (2026-08-16) |
| REFERENCE | 5 | [CLA](CLA.md) | Individual Contributor License Agreement (v1.0, OpenAI) |
| CLOSED | 5 | [INDEX](INDEX.md) | AIOS Completion Atlas — the maps to complete AIOS |
| CLOSED | 5 | [RESEARCH](RESEARCH.md) | RESEARCH.md — Disposition of the AGI-witness PARTIAL, the conditional composition law, and the  |
| CLOSED | 5 | [aios-standards](aios-standards.md) | AIOS Standards |
| CLOSED | 5 | [code-review](code-review.md) | Code Review |
| REFERENCE | 5 | [examples](examples.md) | Examples |
| CLOSED | 5 | [mcp](mcp.md) | Connect Claude Code to tools via MCP |
| REFERENCE | 5 | [npm](npm.md) | Package overview |
| REFERENCE | 5 | [product_recap__demoagent__DEMO-001](product_recap__demoagent__DEMO-001.md) | Product Recap — demoagent / DEMO-001 |
| REFERENCE | 5 | [product_recap__quickstartdemo__QS-001](product_recap__quickstartdemo__QS-001.md) | Product Recap — quickstartdemo / QS-001 |
| REFERENCE | 5 | [product_recap__uri__URI-212](product_recap__uri__URI-212.md) | Product Recap — uri / URI-212 |
| REFERENCE | 5 | [rg_20260515T154702_47d71d13c4d0-needs_operator_review](rg_20260515T154702_47d71d13c4d0-needs_operator_review.md) | rg_20260515T154702_47d71d13c4d0 needs_operator_review |
| CLOSED | 4 | [2026-05-13-sovereign-swarm-design-dialogue](2026-05-13-sovereign-swarm-design-dialogue.md) | Sovereign Swarm AIOS — 설계 대화 (founder / claude / codex) |
| CLOSED | 4 | [2026-05-13-uri-aios-sprint-loop-json-wrapper-gap](2026-05-13-uri-aios-sprint-loop-json-wrapper-gap.md) | Uri AIOS Sprint-Loop JSON Wrapper Gap |
| REFERENCE | 4 | [2026-05-14-genesisos-paper5-p20-goal-route](2026-05-14-genesisos-paper5-p20-goal-route.md) | GenesisOS Paper 5 / P20 Goal Route |
| REFERENCE | 4 | [2026-w13](2026-w13.md) | Week 13 · March 23–27, 2026 |
| REFERENCE | 4 | [2026-w14](2026-w14.md) | Week 14 · March 30 – April 3, 2026 |
| CLOSED | 4 | [2026-w15](2026-w15.md) | Week 15 · April 6–10, 2026 |
| CLOSED | 4 | [2026-w16](2026-w16.md) | Week 16 · April 13–17, 2026 |
| REFERENCE | 4 | [2026-w17](2026-w17.md) | Week 17 · April 20–24, 2026 |
| CLOSED | 4 | [2026-w18](2026-w18.md) | Week 18 · April 27 – May 1, 2026 |
| REFERENCE | 4 | [2026-w19](2026-w19.md) | Week 19 · May 4–8, 2026 |
| CLOSED | 4 | [2026-w20](2026-w20.md) | Week 20 · May 11–15, 2026 |
| REFERENCE | 4 | [2026-w21](2026-w21.md) | Week 21 · May 18–22, 2026 |
| REFERENCE | 4 | [2026-w22](2026-w22.md) | Week 22 · May 25–29, 2026 |
| REFERENCE | 4 | [2026-w23](2026-w23.md) | Week 23 · June 1–5, 2026 |
| REFERENCE | 4 | [2026-w24](2026-w24.md) | Week 24 · June 8–12, 2026 |
| CLOSED | 4 | [2026-w25](2026-w25.md) | Week 25 · June 15–19, 2026 |
| REFERENCE | 4 | [2026-w26](2026-w26.md) | Week 26 · June 22–26, 2026 |
| REFERENCE | 4 | [2026-w27](2026-w27.md) | Week 27 · June 29 – July 3, 2026 |
| REFERENCE | 4 | [2026-w28](2026-w28.md) | Week 28 · July 6–10, 2026 |
| REFERENCE | 4 | [2026-w29](2026-w29.md) | Week 29 · July 13–17, 2026 |
| CLOSED | 4 | [2026-w30](2026-w30.md) | Week 30 · July 20–24, 2026 |
| CLOSED | 4 | [2026-w32](2026-w32.md) | Week 32 · August 3–7, 2026 |
| REFERENCE | 4 | [AIOS-GOAL-0001-paper5-p20-genesis-plan](AIOS-GOAL-0001-paper5-p20-genesis-plan.md) | AIOS Goal Evolution Plan |
| CLOSED | 4 | [AIOS_FABLE_MYTHOS_GROUNDING_2026-07-12](AIOS_FABLE_MYTHOS_GROUNDING_2026-07-12.md) | Fable 5 / Mythos 5 / Dynamic Workflows grounding |
| REFERENCE | 4 | [AIOS_GETTING_STARTED](AIOS_GETTING_STARTED.md) | AIOS Getting Started |
| CLOSED | 4 | [AIOS_HOP_COUNT_HYPOTHESIS_2026-08-10](AIOS_HOP_COUNT_HYPOTHESIS_2026-08-10.md) | hop 수 가설 — 우리가 죽인 것은 전부 2-hop이었고, 살아남은 것은 1-hop이었다 |
| CLOSED | 4 | [AIOS_PROVIDER_REVERSE_ENGINEERING](AIOS_PROVIDER_REVERSE_ENGINEERING.md) | AIOS Provider & Peer Reverse-Engineering Asset |
| REFERENCE | 4 | [AIOS_WORK_VISIBILITY](AIOS_WORK_VISIBILITY.md) | AIOS Work Visibility |
| CLOSED | 4 | [AIOS_ZERO_TO_TEN_2026-08-03](AIOS_ZERO_TO_TEN_2026-08-03.md) | 0에서 10까지 — 에이전트 사회를 컴퓨트 시스템으로 보는 사다리 (2026-08-03) |
| REFERENCE | 4 | [FRONTIER](FRONTIER.md) | FRONTIER.md — Fable 5 differential-knowledge dump (2025–26 frontier) |
| REFERENCE | 4 | [accessibility](accessibility.md) | Use Claude Code with a screen reader |
| REFERENCE | 4 | [admin-setup](admin-setup.md) | Set up Claude Code for your organization |
| CLOSED | 4 | [advisor](advisor.md) | Escalate hard decisions with the advisor tool |
| CLOSED | 4 | [agent-loop](agent-loop.md) | How the agent loop works |
| CLOSED | 4 | [agent-teams](agent-teams.md) | Orchestrate teams of Claude Code sessions |
| CLOSED | 4 | [agent-view](agent-view.md) | Manage multiple agents with agent view |
| CLOSED | 4 | [agents](agents.md) | Run agents in parallel |
| REFERENCE | 4 | [agents_md](agents_md.md) | AGENTS.md |
| REFERENCE | 4 | [aios_product_recap_v1](aios_product_recap_v1.md) | aios.product_recap.v1 |
| CLOSED | 4 | [amazon-bedrock](amazon-bedrock.md) | Claude Code on Amazon Bedrock |
| REFERENCE | 4 | [analytics](analytics.md) | Track team usage with analytics |
| REFERENCE | 4 | [artifacts](artifacts.md) | Share session output as artifacts |
| CLOSED | 4 | [authentication](authentication.md) | Authentication |
| REFERENCE | 4 | [authentication](authentication.md) | Authentication |
| CLOSED | 4 | [auto-mode-config](auto-mode-config.md) | Configure auto mode |
| CLOSED | 4 | [best-practices](best-practices.md) | Best practices for Claude Code |
| REFERENCE | 4 | [champion-kit](champion-kit.md) | Champion kit |
| CLOSED | 4 | [channels-reference](channels-reference.md) | Channels reference |
| CLOSED | 4 | [channels](channels.md) | Push events into a running session with channels |
| REFERENCE | 4 | [checkpointing](checkpointing.md) | Checkpointing |
| CLOSED | 4 | [chrome](chrome.md) | Use Claude Code with Chrome |
| CLOSED | 4 | [claude-apps-gateway-config](claude-apps-gateway-config.md) | Claude apps gateway configuration |
| CLOSED | 4 | [claude-apps-gateway-deploy](claude-apps-gateway-deploy.md) | Claude apps gateway deployment and operations |
| CLOSED | 4 | [claude-apps-gateway-on-aws](claude-apps-gateway-on-aws.md) | Deploy Claude apps gateway on AWS |
| CLOSED | 4 | [claude-apps-gateway-on-gcp](claude-apps-gateway-on-gcp.md) | Deploy Claude apps gateway on Google Cloud |
| CLOSED | 4 | [claude-apps-gateway-spend-limits](claude-apps-gateway-spend-limits.md) | Claude apps gateway spend limits |
| CLOSED | 4 | [claude-apps-gateway](claude-apps-gateway.md) | Claude apps gateway for Amazon Bedrock, Claude Platform on AWS, Google Cloud, and Microsoft Fou |
| CLOSED | 4 | [claude-code-features](claude-code-features.md) | Use Claude Code features in the SDK |
| CLOSED | 4 | [claude-code-on-the-web](claude-code-on-the-web.md) | Use Claude Code on the web |
| OPEN | 4 | [claude-directory](claude-directory.md) | Explore the .claude directory |
| CLOSED | 4 | [claude-platform-on-aws](claude-platform-on-aws.md) | Claude Code on Claude Platform on AWS |
| CLOSED | 4 | [claude-security](claude-security.md) | Scan your codebase for vulnerabilities |
| REFERENCE | 4 | [claude-tag](claude-tag.md) | Claude Tag |
| CLOSED | 4 | [cli-reference](cli-reference.md) | CLI reference |
| CLOSED | 4 | [cloud-environments](cloud-environments.md) | Configure cloud environments |
| CLOSED | 4 | [commands](commands.md) | Commands |
| REFERENCE | 4 | [common-workflows](common-workflows.md) | Common workflows |
| REFERENCE | 4 | [communications-kit](communications-kit.md) | Communications kit |
| CLOSED | 4 | [computer-use](computer-use.md) | Let Claude use your computer from the CLI |
| REFERENCE | 4 | [config](config.md) | Configuration |
| CLOSED | 4 | [context-window](context-window.md) | Explore the context window |
| CLOSED | 4 | [contributing](contributing.md) | contributing |
| CLOSED | 4 | [corporate-launcher](corporate-launcher.md) | Run Claude Code behind a corporate launcher |
| CLOSED | 4 | [cost-tracking](cost-tracking.md) | Track cost and usage |
| CLOSED | 4 | [costs](costs.md) | Manage costs effectively |
| CLOSED | 4 | [cross-session-messaging](cross-session-messaging.md) | Message your other Claude Code sessions |
| CLOSED | 4 | [custom-tools](custom-tools.md) | Give Claude custom tools |
| CLOSED | 4 | [data-usage](data-usage.md) | Data usage |
| CLOSED | 4 | [debug-your-config](debug-your-config.md) | Debug your configuration |
| CLOSED | 4 | [deep-links](deep-links.md) | Launch sessions from links |
| REFERENCE | 4 | [desktop-ios-simulator](desktop-ios-simulator.md) | Test iOS apps in the simulator |
| REFERENCE | 4 | [desktop-linux](desktop-linux.md) | Claude Desktop on Linux (beta) |
| CLOSED | 4 | [desktop-quickstart](desktop-quickstart.md) | Get started with the desktop app |
| REFERENCE | 4 | [desktop-scheduled-tasks](desktop-scheduled-tasks.md) | Schedule recurring tasks in Claude Code Desktop |
| REFERENCE | 4 | [desktop-wsl](desktop-wsl.md) | Claude Code Desktop in WSL |
| CLOSED | 4 | [desktop](desktop.md) | Desktop application |
| CLOSED | 4 | [devcontainer](devcontainer.md) | Development containers |
| CLOSED | 4 | [discover-plugins](discover-plugins.md) | Discover and install prebuilt plugins through marketplaces |
| CLOSED | 4 | [env-vars](env-vars.md) | Environment variables |
| CLOSED | 4 | [errors](errors.md) | Error reference |
| REFERENCE | 4 | [example-config](example-config.md) | Sample configuration |
| REFERENCE | 4 | [exec](exec.md) | Non-interactive mode |
| REFERENCE | 4 | [execpolicy](execpolicy.md) | Execution policy |
| REFERENCE | 4 | [fast-mode](fast-mode.md) | Speed up responses with fast mode |
| REFERENCE | 4 | [feature-availability](feature-availability.md) | Feature availability |
| CLOSED | 4 | [features-overview](features-overview.md) | Extend Claude Code |
| REFERENCE | 4 | [file-checkpointing](file-checkpointing.md) | Rewind file changes with checkpointing |
| REFERENCE | 4 | [fullscreen](fullscreen.md) | Fullscreen rendering |
| REFERENCE | 4 | [gateways](gateways.md) | Run Claude Code through a gateway |
| REFERENCE | 4 | [getting-started](getting-started.md) | Getting started with Codex CLI |
| REFERENCE | 4 | [github-actions-cloud-providers](github-actions-cloud-providers.md) | Use Claude Code GitHub Actions with cloud providers |
| CLOSED | 4 | [github-actions](github-actions.md) | Claude Code GitHub Actions |
| CLOSED | 4 | [github-enterprise-server](github-enterprise-server.md) | Claude Code with GitHub Enterprise Server |
| CLOSED | 4 | [gitlab-ci-cd](gitlab-ci-cd.md) | Claude Code GitLab CI/CD |
| CLOSED | 4 | [glossary](glossary.md) | Glossary |
| CLOSED | 4 | [goal](goal.md) | Keep Claude working toward a goal |
| REFERENCE | 4 | [google-vertex-ai](google-vertex-ai.md) | Claude Code on Google Cloud's Agent Platform |
| CLOSED | 4 | [headless](headless.md) | Run Claude Code programmatically |
| CLOSED | 4 | [hooks-guide](hooks-guide.md) | Automate actions with hooks |
| CLOSED | 4 | [hooks](hooks.md) | Hooks reference |
| CLOSED | 4 | [hosting](hosting.md) | Hosting the Agent SDK |
| REFERENCE | 4 | [how-claude-code-works](how-claude-code-works.md) | How Claude Code works |
| REFERENCE | 4 | [index](index.md) | What's new |
| REFERENCE | 4 | [install](install.md) | Clone the repository and navigate to the root of the Cargo workspace. |
| REFERENCE | 4 | [integration-tests](integration-tests.md) | Integration tests |
| CLOSED | 4 | [interactive-mode](interactive-mode.md) | Interactive mode |
| CLOSED | 4 | [issue-and-pr-automation](issue-and-pr-automation.md) | Automation and triage processes |
| REFERENCE | 4 | [jetbrains](jetbrains.md) | JetBrains IDEs |
| CLOSED | 4 | [keybindings](keybindings.md) | Customize keyboard shortcuts |
| CLOSED | 4 | [large-codebases](large-codebases.md) | Set up Claude Code in a monorepo or large codebase |
| REFERENCE | 4 | [legal-and-compliance](legal-and-compliance.md) | Legal and compliance |
| REFERENCE | 4 | [license](license.md) | license |
| CLOSED | 4 | [llm-gateway-connect](llm-gateway-connect.md) | Connect Claude Code to an LLM gateway |
| CLOSED | 4 | [llm-gateway-protocol](llm-gateway-protocol.md) | Gateway protocol reference |
| CLOSED | 4 | [llm-gateway-rollout](llm-gateway-rollout.md) | Roll out an LLM gateway for your organization |
| CLOSED | 4 | [llm-gateway](llm-gateway.md) | Other LLM gateways |
| REFERENCE | 4 | [local-development](local-development.md) | Local development guide |
| CLOSED | 4 | [managed-mcp](managed-mcp.md) | Control MCP server access for your organization |
| CLOSED | 4 | [mcp-quickstart](mcp-quickstart.md) | Connect to MCP servers |
| CLOSED | 4 | [memory](memory.md) | How Claude remembers your project |
| CLOSED | 4 | [microsoft-foundry](microsoft-foundry.md) | Claude Code on Microsoft Foundry |
| CLOSED | 4 | [migration-guide](migration-guide.md) | Migrate to Claude Agent SDK |
| CLOSED | 4 | [mobile](mobile.md) | Claude Code on mobile |
| CLOSED | 4 | [model-config](model-config.md) | Model configuration |
| CLOSED | 4 | [modifying-system-prompts](modifying-system-prompts.md) | Modifying system prompts |
| CLOSED | 4 | [monitoring-usage](monitoring-usage.md) | Monitoring |
| CLOSED | 4 | [network-config](network-config.md) | Enterprise network configuration |
| CLOSED | 4 | [observability](observability.md) | Observability with OpenTelemetry |
| REFERENCE | 4 | [open-source-fund](open-source-fund.md) | open-source-fund |
| REFERENCE | 4 | [output-styles](output-styles.md) | Output styles |
| CLOSED | 4 | [permission-modes](permission-modes.md) | Choose a permission mode |
| CLOSED | 4 | [permissions](permissions.md) | Configure permissions |
| REFERENCE | 4 | [platforms](platforms.md) | Platforms and integrations |
| CLOSED | 4 | [plugin-dependencies](plugin-dependencies.md) | Constrain plugin dependency versions |
| CLOSED | 4 | [plugin-hints](plugin-hints.md) | Recommend your plugin from your CLI |
| CLOSED | 4 | [plugin-marketplaces](plugin-marketplaces.md) | Create and distribute a plugin marketplace |
| REFERENCE | 4 | [plugin-relevance](plugin-relevance.md) | Recommend plugins for your org |
| CLOSED | 4 | [plugins-reference](plugins-reference.md) | Plugins reference |
| CLOSED | 4 | [plugins](plugins.md) | Create plugins |
| CLOSED | 4 | [prompt-caching](prompt-caching.md) | How Claude Code uses prompt caching |
| CLOSED | 4 | [prompt-library](prompt-library.md) | Prompt library |
| REFERENCE | 4 | [quickstart](quickstart.md) | Quickstart |
| CLOSED | 4 | [remote-control](remote-control.md) | Continue local sessions from any device with Remote Control |
| CLOSED | 4 | [research__are-provider-fallback-bindings-operational-or-theoretical](research__are-provider-fallback-bindings-operational-or-theoretical.md) | Research Note — Are "provider-fallback" bindings operational or theoretical? |
| REFERENCE | 4 | [research__autopoiesis-organ-efficacy-in-specialist-helper-layer](research__autopoiesis-organ-efficacy-in-specialist-helper-layer.md) | Research Note — Autopoiesis organ efficacy in Specialist Helper Layer |
| REFERENCE | 4 | [research__gpu-present-but-torch-transformers-peft-not-installed-pip-in](research__gpu-present-but-torch-transformers-peft-not-installed-pip-in.md) | Research Note — GPU present but torch/transformers/peft not installed — `pip install torch tran |
| REFERENCE | 4 | [research__gpu-present-but-torch-transformers-peft-not-installed](research__gpu-present-but-torch-transformers-peft-not-installed.md) | Research Note — GPU present but torch/transformers/peft not installed |
| REFERENCE | 4 | [research__how-does-dream-cycle-integration-affect-autopoiesis-stabilit](research__how-does-dream-cycle-integration-affect-autopoiesis-stabilit.md) | Research Note — How does Dream cycle integration affect autopoiesis stability? |
| REFERENCE | 4 | [research__local-first-ingest-protocol-s-scalability-limits](research__local-first-ingest-protocol-s-scalability-limits.md) | Research Note — Local-first ingest protocol's scalability limits |
| REFERENCE | 4 | [research__repeatable-completion-is-not-proven](research__repeatable-completion-is-not-proven.md) | Research Note — repeatable completion is not proven |
| REFERENCE | 4 | [research__what-role-do-helper-invocations-play-in-unresolved-contracts](research__what-role-do-helper-invocations-play-in-unresolved-contracts.md) | Research Note — What role do helper invocations play in unresolved contracts? |
| REFERENCE | 4 | [research__workbench-model-b-s-impact-on-memoryos-stability](research__workbench-model-b-s-impact-on-memoryos-stability.md) | Research Note — Workbench Model B's impact on memoryOS stability |
| REFERENCE | 4 | [rg_20260515T155313_4eb7e55160c1-needs_operator_review](rg_20260515T155313_4eb7e55160c1-needs_operator_review.md) | rg_20260515T155313_4eb7e55160c1 needs_operator_review |
| CLOSED | 4 | [routines](routines.md) | Automate work with routines |
| CLOSED | 4 | [sandbox-environments](sandbox-environments.md) | Choose a sandbox environment |
| REFERENCE | 4 | [sandbox](sandbox.md) | sandbox |
| CLOSED | 4 | [sandboxing](sandboxing.md) | Configure the sandboxed Bash tool |
| CLOSED | 4 | [scheduled-tasks](scheduled-tasks.md) | Run prompts on a schedule |
| CLOSED | 4 | [secure-deployment](secure-deployment.md) | Securely deploying AI agents |
| CLOSED | 4 | [security-guidance](security-guidance.md) | Catch security issues as Claude writes code |
| CLOSED | 4 | [self-hosted-environments-configuration](self-hosted-environments-configuration.md) | Customize sessions in self-hosted environments |
| CLOSED | 4 | [self-hosted-environments-deploy](self-hosted-environments-deploy.md) | Deploy self-hosted environments to production |
| CLOSED | 4 | [self-hosted-environments-identity](self-hosted-environments-identity.md) | Verify session identity in self-hosted environments |
| CLOSED | 4 | [self-hosted-environments-quickstart](self-hosted-environments-quickstart.md) | Self-hosted environments quickstart |
| CLOSED | 4 | [self-hosted-environments-reference](self-hosted-environments-reference.md) | Self-hosted environments reference |
| CLOSED | 4 | [self-hosted-environments-testing](self-hosted-environments-testing.md) | Test self-hosted environments end to end |
| CLOSED | 4 | [self-hosted-environments](self-hosted-environments.md) | Self-hosted environments |
| CLOSED | 4 | [server-managed-settings](server-managed-settings.md) | Configure server-managed settings |
| CLOSED | 4 | [session-storage](session-storage.md) | Persist sessions to external storage |
| CLOSED | 4 | [sessions](sessions.md) | Manage sessions |
| CLOSED | 4 | [settings](settings.md) | Claude Code settings |
| CLOSED | 4 | [setup](setup.md) | Advanced setup |
| CLOSED | 4 | [skills](skills.md) | Extend Claude with skills |
| REFERENCE | 4 | [skills](skills.md) | Skills |
| CLOSED | 4 | [slack](slack.md) | Claude Code in Slack |
| CLOSED | 4 | [slash-commands](slash-commands.md) | Slash Commands in the SDK |
| REFERENCE | 4 | [slash_commands](slash_commands.md) | Slash commands |
| REFERENCE | 4 | [statusline](statusline.md) | Customize your status line |
| REFERENCE | 4 | [streaming-output](streaming-output.md) | Stream responses in real-time |
| REFERENCE | 4 | [streaming-vs-single-mode](streaming-vs-single-mode.md) | Streaming Input |
| CLOSED | 4 | [structured-outputs](structured-outputs.md) | Get structured output from agents |
| CLOSED | 4 | [sub-agents](sub-agents.md) | Create custom subagents |
| CLOSED | 4 | [subagents](subagents.md) | Subagents in the SDK |
| REFERENCE | 4 | [terminal-config](terminal-config.md) | Configure your terminal for Claude Code |
| CLOSED | 4 | [third-party-integrations](third-party-integrations.md) | Enterprise deployment overview |
| REFERENCE | 4 | [todo-tracking](todo-tracking.md) | Todo Lists |
| CLOSED | 4 | [tool-search](tool-search.md) | Scale to many tools with tool search |
| CLOSED | 4 | [tools-reference](tools-reference.md) | Tools reference |
| REFERENCE | 4 | [transcript](transcript.md) | ASC-0041 Web Evidence Memory Review |
| REFERENCE | 4 | [transcript](transcript.md) | ASC-0042 Capability Observation Memory Review |
| CLOSED | 4 | [troubleshoot-install](troubleshoot-install.md) | Troubleshoot installation and login |
| REFERENCE | 4 | [troubleshooting](troubleshooting.md) | Troubleshooting |
| CLOSED | 4 | [typescript-v2-preview](typescript-v2-preview.md) | TypeScript SDK V2 session API (removed) |
| CLOSED | 4 | [typescript](typescript.md) | Agent SDK reference - TypeScript |
| CLOSED | 4 | [ultrareview](ultrareview.md) | Find bugs with ultrareview |
| CLOSED | 4 | [user-input](user-input.md) | Handle approvals and user input |
| REFERENCE | 4 | [voice-dictation](voice-dictation.md) | Voice dictation |
| CLOSED | 4 | [vs-code](vs-code.md) | Use Claude Code in VS Code |
| CLOSED | 4 | [web-quickstart](web-quickstart.md) | Get started with Claude Code on the web |
| CLOSED | 4 | [worktrees](worktrees.md) | Run parallel sessions with worktrees |
| REFERENCE | 4 | [zero-data-retention](zero-data-retention.md) | Zero data retention |
| REFERENCE | 3 | [2026-05-13-asc-0063-status-update-sprint-runs-channel](2026-05-13-asc-0063-status-update-sprint-runs-channel.md) | ASC-0063 Status Update — T1+T2 Resolved + T3 Partial via sprint_runs/ Channel — 2026-05-13 |
| REFERENCE | 3 | [2026-05-13-uri-claude-lane-12-packet-ladder-synthesis](2026-05-13-uri-claude-lane-12-packet-ladder-synthesis.md) | Uri claude@uri Lane 12-Packet Ladder Synthesis — 2026-05-13 |
| REFERENCE | 3 | [2026-05-13-uri-first-100-cohort-flip-asc-draft](2026-05-13-uri-first-100-cohort-flip-asc-draft.md) | Uri First-100 Cohort Graduation Flip — ASC Draft — 2026-05-13 |
| REFERENCE | 3 | [AIOS_ALIGNMENT_PROVIDER_SURVEY_2026-05-20](AIOS_ALIGNMENT_PROVIDER_SURVEY_2026-05-20.md) | AIOS Alignment Provider Survey |
| CLOSED | 3 | [AIOS_BRAND](AIOS_BRAND.md) | AIOS — Brand Identity |
| CLOSED | 3 | [AIOS_DIVERGENCE_2026-08-08](AIOS_DIVERGENCE_2026-08-08.md) | 이종 발산 1회차 — 측정된 제약 아래에서 무엇이 아직 가능한가 (2026-08-08) |
| REFERENCE | 3 | [AIOS_ECOSYSTEM_ABSORPTION_ROADMAP](AIOS_ECOSYSTEM_ABSORPTION_ROADMAP.md) | AIOS Ecosystem Absorption Roadmap |
| REFERENCE | 3 | [AIOS_FRONTIER_VOCABULARY_2026-08](AIOS_FRONTIER_VOCABULARY_2026-08.md) | 프론티어 어휘 정찰 — 검색하기 전에 검색어를 갱신한다 (2026-08-03) |
| REFERENCE | 3 | [AIOS_LOOP_TEST](AIOS_LOOP_TEST.md) | AIOS Loop Test Record |
| REFERENCE | 3 | [AIOS_PROVIDER_WEB_REFERENCES](AIOS_PROVIDER_WEB_REFERENCES.md) | AIOS Provider Web Design References |
| REFERENCE | 3 | [AIOS_QA_CONTINUOUS_2026](AIOS_QA_CONTINUOUS_2026.md) | AIOS Continuous QA & Deep Evolution Architecture (2026-07) |
| CLOSED | 3 | [AIOS_RADAR_SWEEP_01_2026-07-17](AIOS_RADAR_SWEEP_01_2026-07-17.md) | AIOS Ecosystem Radar — Sweep #1 (2026-07-17) |
| REFERENCE | 3 | [AIOS_SAAS_LAKEBASE_PLAN](AIOS_SAAS_LAKEBASE_PLAN.md) | AIOS SaaS / Lakebase AkashicRecord — production plan |
| REFERENCE | 3 | [AIOS_THOUGHT_EMERGENCE_DIFFUSION_2026-08-03](AIOS_THOUGHT_EMERGENCE_DIFFUSION_2026-08-03.md) | 사고의 창발: 그래프 · 디퓨전 LM · 상태머신 — 평가와 반증 설계 (2026-08-03) |
| REFERENCE | 3 | [AIOS_URI_FILTER_POLICY](AIOS_URI_FILTER_POLICY.md) | AIOS Uri Filter Policy |
| REFERENCE | 3 | [AIOS_WORKBENCH_QUICKSTART](AIOS_WORKBENCH_QUICKSTART.md) | AIOS Workbench — Quickstart |
| CLOSED | 3 | [ASC-0281-society-answerability-episode](ASC-0281-society-answerability-episode.md) | ASC-0281 — Society-level answerability episode (DescentNet × APEX × Akashic, sealed decision-co |
| CLOSED | 3 | [ASC-0284-lower-model-runtime-capsule-eval](ASC-0284-lower-model-runtime-capsule-eval.md) | ASC-0284 Lower-model runtime capsule evaluation |
| REFERENCE | 3 | [CONTRIBUTING](CONTRIBUTING.md) | CONTRIBUTING |
| CLOSED | 3 | [M1a_CERTIFICATE_INTERFACE](M1a_CERTIFICATE_INTERFACE.md) | M1a — Certificate Interface Spec |
| CLOSED | 3 | [META](META.md) | META — Fable 5 self-assessment: what to mine from me, and how |
| REFERENCE | 3 | [OSS_COMMUNITY_PROGRAM_2026-08-10](OSS_COMMUNITY_PROGRAM_2026-08-10.md) | Claude for Open Source — baseline, gap, and the work that closed the entry blockers |
| REFERENCE | 3 | [PRODUCTION_HOSTING_RUNBOOK](PRODUCTION_HOSTING_RUNBOOK.md) | AIOS Production Hosting Runbook |
| CLOSED | 3 | [QEL_QIR_QVM_ecosystem_foundation](QEL_QIR_QVM_ecosystem_foundation.md) | QEL·QIR·QVM 기반 에이전트-네이티브 컴퓨팅 생태계 토대 설계 |
| CLOSED | 3 | [QEL_spec_and_prototype_plan](QEL_spec_and_prototype_plan.md) | QEL 기반 사양과 프로토타입 계획 |
| REFERENCE | 3 | [aios_distilled_pattern_v1](aios_distilled_pattern_v1.md) | aios.distilled_pattern.v1 |
| OPEN | 3 | [behavioral-evals](behavioral-evals.md) | Behavioral Evaluations & EDK Guide |
| REFERENCE | 3 | [index](index.md) | Gemini CLI documentation |
| CLOSED | 3 | [medical](medical.md) | Frontier Knowledge Ledger — D2: Medical / Biomedical AI |
| REFERENCE | 3 | [product_recap__testbench01__TB-001](product_recap__testbench01__TB-001.md) | Product Recap — testbench01 / TB-001 |
| CLOSED | 3 | [qel_author_response_to_our_null_2026-08-05](qel_author_response_to_our_null_2026-08-05.md) | QEL 저자(ChatGPT)의 응답 — 우리 3-채널 null을 들고 물었을 때 |
| OPEN | 3 | [release-confidence](release-confidence.md) | Release confidence strategy |
| CLOSED | 3 | [releases](releases.md) | Gemini CLI releases |
| REFERENCE | 3 | [research__gpu-present-but-torch-transformers-peft-not](research__gpu-present-but-torch-transformers-peft-not.md) | Research Note — GPU present but torch/transformers/peft not |
| CLOSED | 2 | [2026-05-13-aios-agent-strength-routing-gap](2026-05-13-aios-agent-strength-routing-gap.md) | AIOS Agent Strength Routing Gap |
| REFERENCE | 2 | [2026-05-13-codex-vercel-nextjs-skill-path-gap](2026-05-13-codex-vercel-nextjs-skill-path-gap.md) | Discovery - Codex Vercel Next.js Skill Path Gap |
| REFERENCE | 2 | [2026-05-13-founder-claude-session-mechanism-reverse-engineering](2026-05-13-founder-claude-session-mechanism-reverse-engineering.md) | Claude Code Session Maintenance — Founder Reverse-Engineering |
| REFERENCE | 2 | [2026-05-13-gating-reduction-options](2026-05-13-gating-reduction-options.md) | Reducing Operator Gating in AIOS — Options for Founder Decision |
| REFERENCE | 2 | [2026-05-13-genesis-stub-and-4os-deliberation](2026-05-13-genesis-stub-and-4os-deliberation.md) | Genesis stub + 4-OS distributed deliberation — Founder pick |
| REFERENCE | 2 | [2026-05-13-uri-memoryos-subgraph-verification-and-ledger-gap](2026-05-13-uri-memoryos-subgraph-verification-and-ledger-gap.md) | Uri MemoryOS Subgraph Verification + Ledger Gap |
| REFERENCE | 2 | [2026-05-13-uri-sprint-loop-receipt-and-dev-server-lifecycle](2026-05-13-uri-sprint-loop-receipt-and-dev-server-lifecycle.md) | Discovery — Uri Sprint Loop Receipt + Dev Server Lifecycle Gaps |
| REFERENCE | 2 | [2026-05-13-uri-sprint-sequencing-after-014-daily-quest](2026-05-13-uri-sprint-sequencing-after-014-daily-quest.md) | Uri Sprint Sequencing Reconciliation — Post Sprint 014 Daily Quest — 2026-05-13 |
| REFERENCE | 2 | [2026-05-13-uri-temporal-ui-verification-primitive](2026-05-13-uri-temporal-ui-verification-primitive.md) | Uri Temporal UI Verification Primitive |
| REFERENCE | 2 | [2026-05-13-uri-visual-fixture-contract-gap](2026-05-13-uri-visual-fixture-contract-gap.md) | Uri Visual Fixture Contract Gap |
| CLOSED | 2 | [20260725-182128-agy-design-the-decisive-experiment-that-settles-one](20260725-182128-agy-design-the-decisive-experiment-that-settles-one.md) | Consultation — agy — 2026-07-25T18:21:28Z |
| CLOSED | 2 | [20260725-182129-agy-adversarial-gap-audit-given-the-organism-below-n](20260725-182129-agy-adversarial-gap-audit-given-the-organism-below-n.md) | Consultation — agy — 2026-07-25T18:21:29Z |
| CLOSED | 2 | [20260726-155921-agy-operator-led-3-turn-dialogue-with-gemini-3-1-pro](20260726-155921-agy-operator-led-3-turn-dialogue-with-gemini-3-1-pro.md) | Consultation — agy — 2026-07-26T15:59:21Z |
| REFERENCE | 2 | [AIOS_CODE_LEVEL_ANALYSIS](AIOS_CODE_LEVEL_ANALYSIS.md) | AIOS 코드 레벨 문제점 분석 및 Akashic Record 연결 방안 |
| REFERENCE | 2 | [AIOS_DEPLOYMENT_PLAN_2026-08-03](AIOS_DEPLOYMENT_PLAN_2026-08-03.md) | 배포 계획 — Orca처럼 패키징된 서비스로 (2026-08-03) |
| CLOSED | 2 | [AIOS_ECOSYSTEM_PROVISIONING_2026-08-10](AIOS_ECOSYSTEM_PROVISIONING_2026-08-10.md) | 생태계 provisioning — 내가 못 만든다는 제약을 뺀 설계 |
| CLOSED | 2 | [AIOS_ECOSYSTEM_RADAR_2026-07-17](AIOS_ECOSYSTEM_RADAR_2026-07-17.md) | AIOS Ecosystem Radar — Sweep #1 (2026-07-17) |
| REFERENCE | 2 | [AIOS_FRESHNESS_SWEEP_2026-07-17](AIOS_FRESHNESS_SWEEP_2026-07-17.md) | Freshness Sweep — 2026-07-17 (WebSearch + Council-Perplexity 교차검증) |
| CLOSED | 2 | [AIOS_FUTURE_GOAL_2026-08-10](AIOS_FUTURE_GOAL_2026-08-10.md) | 우리의 미래 목표 — 측정에서만 도출한 것 (2026-08-10) |
| REFERENCE | 2 | [AIOS_MATH_OPTIMIZATION_PORTING](AIOS_MATH_OPTIMIZATION_PORTING.md) | AIOS 수학적 최적화 이식 설계도 (Mathematical Optimization Porting for AIOS) |
| CLOSED | 2 | [AIOS_METHODOLOGY_DIVERGENCE_2026-07-22](AIOS_METHODOLOGY_DIVERGENCE_2026-07-22.md) | AIOS Methodology Divergence — beyond small-N SFT distillation (2026-07-22) |
| CLOSED | 2 | [AIOS_ORGANIC_EVOLUTION_MASTER](AIOS_ORGANIC_EVOLUTION_MASTER.md) | AIOS: The Organic Evolution Master Document (2026) |
| CLOSED | 2 | [AIOS_QEL_ASSESSMENT_2026-08-05](AIOS_QEL_ASSESSMENT_2026-08-05.md) | QEL·QIR·QVM·QNet — GPT 설계와 우리 실측의 대조 (2026-08-05) |
| REFERENCE | 2 | [AIOS_RADAR_COMMUNITY_XLIVE_2026-07-17](AIOS_RADAR_COMMUNITY_XLIVE_2026-07-17.md) | Radar — X/Twitter live community (Grok, 2026-07-17) |
| REFERENCE | 2 | [AIOS_SECI_NEXT_STEPS](AIOS_SECI_NEXT_STEPS.md) | AIOS SECI Pipeline — Next Steps |
| OPEN | 2 | [AIOS_SPRINT_LOOP](AIOS_SPRINT_LOOP.md) | AIOS Sprint Loop |
| REFERENCE | 2 | [AIOS_STRATEGIC_ESCALATION_2026-07-05](AIOS_STRATEGIC_ESCALATION_2026-07-05.md) | Strategic escalation — the keystone attractor (2026-07-05) |
| SUPERSEDED | 2 | [ASC-0280-goen-sheaf-graph-control-supersede](ASC-0280-goen-sheaf-graph-control-supersede.md) | ASC-0280 — GoEN sheaf graph-control supersedes ASC-0194 (evidence-gated) |
| CLOSED | 2 | [ASC-0283-fable-mythos-workflow-distillation](ASC-0283-fable-mythos-workflow-distillation.md) | ASC-0283 Fable/Mythos Workflow Distillation |
| REFERENCE | 2 | [BUILD_ON_AIOS](BUILD_ON_AIOS.md) | Build on AIOS |
| CLOSED | 2 | [LIVING_SYSTEM_RESEARCH](LIVING_SYSTEM_RESEARCH.md) | Living System Research: Internal AIOS Analysis & External State of the Art (2026) |
| REFERENCE | 2 | [README](README.md) | `docs/external/gpt/` — 외부(ChatGPT) 생성 자료 보관소 |
| REFERENCE | 2 | [RESEARCH_ADVANCEMENT_PROPOSAL_2026](RESEARCH_ADVANCEMENT_PROPOSAL_2026.md) | AGI Core Research: 고도화 및 발전 제안서 (2026-07) |
| REFERENCE | 2 | [biological_digital_convergence](biological_digital_convergence.md) | Biological/Digital AI Convergence & Organism-like Architectures (2026) |
| REFERENCE | 2 | [continuous_learning_nested](continuous_learning_nested.md) | Continuous Learning and Nested Learning in LLMs (2026) |
| REFERENCE | 2 | [dynamic_knowledge_graphs](dynamic_knowledge_graphs.md) | Dynamic Knowledge Graphs & Memory Consolidation (2026) |
| REFERENCE | 2 | [evolutionary_llm_algorithms](evolutionary_llm_algorithms.md) | Evolutionary LLM Algorithms & Automated Algorithm Design (2026) |
| CLOSED | 2 | [launch_post](launch_post.md) | AIOS: your agent stops starting from zero |
| REFERENCE | 2 | [missing_point_to_emergence](missing_point_to_emergence.md) | 인류가 놓친 관점에서 창발로 가는 길 |
| CLOSED | 2 | [reddit_claudeai](reddit_claudeai.md) | r/ClaudeAI post — draft (not posted) |
| CLOSED | 2 | [reddit_localllama](reddit_localllama.md) | r/LocalLLaMA post — draft (not posted) |
| REFERENCE | 2 | [research__autopoiesis-criteria-for-self-maintaining-software-systems](research__autopoiesis-criteria-for-self-maintaining-software-systems.md) | Research Note — autopoiesis criteria for self-maintaining software systems |
| CLOSED | 2 | [show_hn](show_hn.md) | Show HN — draft (not posted) |
| CLOSED | 2 | [x_thread](x_thread.md) | X/Twitter thread — draft (not posted) |
| CLOSED | 1 | [AIOS_AGILE_LOOP_2026-07-17](AIOS_AGILE_LOOP_2026-07-17.md) | AIOS Agile Loop — 상설 프로세스 헌장 (2026-07-17) |
| CLOSED | 1 | [AIOS_BEHAVIOR_SCORING_ANALYSIS](AIOS_BEHAVIOR_SCORING_ANALYSIS.md) | AIOS Behavior Scoring Analysis |
| CLOSED | 1 | [AIOS_COUNCIL_INTEGRATION](AIOS_COUNCIL_INTEGRATION.md) | AIOS ↔ Council 편입 독트린 |
| REFERENCE | 1 | [AIOS_DACON_236694](AIOS_DACON_236694.md) | dacon 236694 — AI Agent Action Prediction × AIOS |
| CLOSED | 1 | [AIOS_DATA_LIFECYCLE](AIOS_DATA_LIFECYCLE.md) | AIOS Data Lifecycle — Crypto-Erase and Right-to-Erasure Design |
| SUPERSEDED | 1 | [AIOS_DREAM_2026-08-10](AIOS_DREAM_2026-08-10.md) | Dreaming — 반증을 화폐로 쓰는 행성 면역계 |
| CLOSED | 1 | [AIOS_HARNESS_CONSTRUCTION_ABSORBED_2026-08-16](AIOS_HARNESS_CONSTRUCTION_ABSORBED_2026-08-16.md) | Harness construction + failure introspection — absorbed from ECC (2026-08-16) |
| REFERENCE | 1 | [AIOS_RELEASE](AIOS_RELEASE.md) | AIOS Release & Deployment |
| REFERENCE | 1 | [AIOS_SAKANA_FIT](AIOS_SAKANA_FIT.md) | Sakana AI × AIOS — grounded fit (2026-07-04) |
| CLOSED | 1 | [AIOS_STRUCTURAL_STREAM_INJECTION](AIOS_STRUCTURAL_STREAM_INJECTION.md) | AIOS Structural Stream Injection & Unconstrained Multi-Model Weaving Engine |
| REFERENCE | 1 | [AIOS_SYSTEMSPACE_PIVOT_FIRST_TESTS_2026-07-22](AIOS_SYSTEMSPACE_PIVOT_FIRST_TESTS_2026-07-22.md) | System-space pivot — first tests: a well-powered DOUBLE NULL (2026-07-22) |
| CLOSED | 1 | [AIOS_TAEBAEK_WIND_FORECAST_PHYSICS_2026-07-22](AIOS_TAEBAEK_WIND_FORECAST_PHYSICS_2026-07-22.md) | Taebaek Gadeoksan Day-Ahead Wind Forecast Physics — Knowledge Receipt |
| CLOSED | 1 | [ASC-0281-apex-gluing-gate-memoryos-conflict-layer](ASC-0281-apex-gluing-gate-memoryos-conflict-layer.md) | ASC-0281 — APEX claim-gluing gate populates the memoryOS conflict layer (recommendation-only) |
| CLOSED | 1 | [CLI_SUBSTRATE_MAP_2026-07](CLI_SUBSTRATE_MAP_2026-07.md) | CLI Substrate Capability Map — claude / codex / agy (2026-07-27) |
| CLOSED | 1 | [FIRST_USER](FIRST_USER.md) | First real external user — the conversion runbook (honest) |
| REFERENCE | 1 | [RELEASE_PROCEDURE](RELEASE_PROCEDURE.md) | 릴리스 절차 — 설치되는 것만 출하한다 (2026-08-03) |
| CLOSED | 1 | [agi](agi.md) | Frontier Knowledge Ledger — D1: AGI / foundation capability |
| CLOSED | 1 | [demo_script](demo_script.md) | Demo script — terminal recording / asciinema |
| CLOSED | 1 | [physical_ai](physical_ai.md) | Frontier Knowledge Ledger — D3: Physical / Embodied AI |
| CLOSED | 1 | [reasoning_verification_rl](reasoning_verification_rl.md) | Frontier Knowledge Ledger — D5: Reasoning + Verification + RL for agents |
| REFERENCE | 1 | [rl_and_genetic_evolution](rl_and_genetic_evolution.md) | Evolutionary and Reinforcement Learning Methodologies for AI Agents (2026 Research Report) |
| CLOSED | 1 | [society_assembly](society_assembly.md) | Frontier Knowledge Ledger — D7: Multi-agent society + assembly/composition |
| CLOSED | 0 | [AIOS_WHY_2026-08-18](AIOS_WHY_2026-08-18.md) | 왜 짓는가 — 그리고 어디서 실제로 더 빨리 도약할 수 있는가 (2026-08-18) |
| CLOSED | 0 | [ChatGPT-Claude 기술 분석 요청-20260813-1906](ChatGPT-Claude 기술 분석 요청-20260813-1906.md) | Claude 기술 분석 요청 |
