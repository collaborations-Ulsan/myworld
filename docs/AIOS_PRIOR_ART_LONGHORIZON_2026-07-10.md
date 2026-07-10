# Prior Art Deep-Dive — "weak model + epistemic runtime beats strong raw" (2026-07-10)

> 작성: 리서치 subagent (WebSearch, 2026-07-10). 마스터플랜 §5.5의 원본. keystone(M2) novelty 판정 근거.

## Q1 — "scaffold가 약한 모델을 강한 모델 위로" 출판 사례

- **Harness-Bench** (PKU/Qiyuan, 2026-05-27, arXiv 2605.27922): 106 sandboxed tasks × 8 backends × 6 harnesses, 5,088 trajectories. 같은 모델에서 harness 교체로 최대 **23.8pt**; **순위 역전 출판**: qwen3.6-plus+QwenPaw **76.5** > qwen3.6-max-preview+Hermes **70.2**. 약한 backend일수록 cross-harness 분산 큼. founder 주장에 가장 근접한 기존 결과 — 단 단·중기 샌드박스 워크플로, 인접 티어 API 모델, **변이 환경 아님**.
- **AB-MCTS / TreeQuest** (Sakana, 2025-06): o4-mini+Gemini-2.5-Pro+DeepSeek-R1 조합 ARC-AGI-2 **27.5–30%** vs o4-mini 단독 **23%** (Chollet: pass@k 인플레 주의).
- **CTI-REALM** (2603.13517): GPT-5-Mini + expert-distilled memory 0.371→**0.432** — GPT-5와의 갭 33% 봉합 (역전은 아님).
- **ReasoningBank** (Google, 2509.25140): same-model 메모리 이득 — WebArena 46.7→56.3% (Gemini-2.5-Pro+MaTTS), SWE-bench-V 54.0→57.4%, Claude 3.7 최대 +34.2% rel; steps −16%.
- **Agent Workflow Memory** (ICML 2025, 2409.07429): WebArena +51.1% rel, Mind2Web +24.6%.
- **Interplay of Harness Design & Post-Training** (2606.25447): harness-aware 학습은 약한 모델(Qwen2.5-7B)에 최대 효과; 미니멀 harness는 tool-environment shift에서 붕괴.
- (스캐폴드 아닌 fine-tune 참고: Thinking Machines × Bridgewater Qwen3-235B custom 84.7% vs frontier 78.2%, 13.8× 저렴.)

**Net**: "harness > model"은 2026년 출판·정량화된 결과 (순위 역전 존재). **"약한 LOCAL 모델 + runtime ≥ frontier, 롱-호라이즌 변이 태스크에서"는 미출판.**

## Q2 — 롱-호라이즌 절벽을 닫으려는 시도 (측정된 이득)

- 앵커 확인: **OSWorld 2.0** (2606.29537): 최고 (Opus 4.8, 500 steps) **20.6%** binary / 54.8% partial; 108 workflows, ~318 tool calls each; 실패 taxonomy = 제약 상실, 중간 정보 놓침, 묻지 않고 추측, 검증 생략. **Gaia2** (2602.11964): frontier ~42%, 1,120 시나리오, 비동기 world-state 변이.
- **Checkpoint-and-re-read**: state 직렬화 + 신선한 재독 → RMBench **32.4% vs 9.8%** best baseline.
- **PRMs**: Web-Shepherd 34.55% vs 23.64% (WebArena-lite, 2505.15277); AgentPRM +39.7% rel (VisualWebArena, 8× compute-efficient, WWW 2026); GUI-PRA +14.53%; SWE-TRACE rubric-PRM (2604.14820).
- **Context 관리**: Self-Compacting agents (2606.23525) 최대 +18.1pt에 토큰 30-70% 절감; CompactionRL (2607.05378); ACON −26-54% 메모리 at 95%+ 정확도; Slipstream — compaction을 trajectory 대비 검증 (2605.08580).

## Q3 — 변이 환경 벤치마크: 이미 존재한다

- **ProEvolve — "The World Won't Stay Still"** (Amazon/UCB incl. Dawn Song, 2603.05910, 2026-03): 프로그래머블 그래프 기반 **환경 진화** (tools/schemas/data 변이); schema drift·auth 실패·adversarial error rewriting 포함. **핵심 발견: 정적-설정 메모리 전략은 구조적 변화 하에서 task completion을 악화시킨다 (낡은 경험이 오도).**
- **DriftBench** (2605.10990, 2026-05): 8 drift 유형 (URL·버전·config·API migration·deprecation·schema·auth·dependency); 880쌍; contract 추출 → false alarm **0/599**, 알려진 drift에 100%p/76%r; repair 10%→78%.
- 기타: ToolQA-D (API drift, agent 미인지), SWE-Chain (2605.14415, 연쇄 패키지 업그레이드), STT-Arena (2605.18548), Gaia2 async events, ToolMisuseBench (2604.01508). "Mutating Environment Debugging"이라는 이름은 없지만 substrate는 이미 지어져 있음.

## Q4 — Abstention / typed verdicts in agent loops

- QA-레벨 abstention은 성숙: Abstain-R1 (2604.17073), PassiveQA (Answer/Ask/Abstain, 2604.04565), conformal abstention, BRAG (answerability posterior + validity gate).
- 실행-게이팅은 safety-typed이지 epistemic이 아님: KAIJU intent-gated kernel (2604.02375), POLARIS validator-gated execution, OSGuard pre-execution guardrail (2606.15034).
- **공백이 문헌에 명시**: interactive 롱-호라이즌 세팅의 agentic UQ 벤치마크는 "성숙 형태로 존재하지 않음" (Zylos 2026-04, ICML 2025 position paper 인용). **calibrated CLAIM/ABSTAIN 턴-레벨 verdict + 측정된 end-task 이득을 ship한 곳 없음.**

## Q5 — Sleep-time / offline consolidation → downstream 성공

- **Sleep-time Compute** (Letta/Berkeley, 2504.13171): +13-18% 정확도, 5× test-time compute 절감 — 단 stateful QA/math, agent task 아님.
- **Auto-Dreamer** (2605.20616, 2026-05): 학습된 offline consolidator (end-to-end agent reward에 GRPO) → **ScienceWorld +7pt, 12× 작은 메모리**, ALFWorld/WebArena 전이. **"consolidation이 downstream 성공을 개선" 출판 결과 = 이것.**
- 관련: Mem-π, ExpSeek, "Decocted Experience" (2604.04373) — 교훈 증류 > 원시 경험; 메모리 크기 비단조 sweet spot.

## Novelty verdict

**이미 됨 (인용, 재주장 금지)**: harness>model 순위 역전 (Harness-Bench); same-model 메모리 이득 (ReasoningBank, AWM); 멀티모델 오케스트레이션 > 단일 강모델 (AB-MCTS); 변이 벤치 기계 (ProEvolve, DriftBench, ToolQA-D, Gaia2); safety-typed 사전실행 게이트 (KAIJU/OSGuard); consolidation→downstream (Auto-Dreamer).

**진짜 열림 (정직한 keystone)**:
1. **conjunction**: weak-LOCAL-model + epistemic runtime vs strong-raw-frontier, **롱-호라이즌(OSWorld-2.0/Gaia2급) 변이 태스크** — head-to-head 없음. Harness-Bench 역전은 인접 티어 API 모델·단기.
2. **calibrated typed verdicts (CLAIM/ABSTAIN/ASK) 턴 게이트** + risk-coverage 곡선 → end-task 성공 연결 — agentic-UQ 공백이 문헌에 기록됨.
3. **변이에서 살아남는 메모리**: ProEvolve가 정적 메모리의 해악을 입증 — 자기 메모리/skill의 staleness를 감지(DriftBench식 contracts + abstention)하고도 순이득인 epistemic runtime은 무주공산.

## 최소 정직 실험 3권고

1. **벤치는 빌드 말고 임대**: ProEvolve-evolved 환경 또는 Gaia2 + DriftBench 880쌍을 mutation substrate로. binary AND partial credit (OSWorld-2.0식), arm별 고정 tool-call 예산.
2. **2×2 + interaction term이 주장**: {weak local (qwen3-coder-30B급) vs frontier} × {bare vs epistemic runtime}, 변이 태스크 ~50, 3 seeds. **ReasoningBank/AWM식 memory arm을 baseline에 포함** — bare-vs-scaffold 델타만으론 더는 novel하지 않음. Fallback 주장 (same-model drift-error 감축)은 memory baseline을 변이 하에서 이길 때만 출판가치 (ProEvolve 예측: memory baseline은 거기서 무너짐).
3. **abstention gate를 측정가능하게**: 비가역 행동 전 typed verdict; 명시적 비용모델 (wrong-action ≫ ask/abstain) + risk-coverage calibration 곡선 + end-task 성공으로 채점. **가장 날카로운 미점유 결과: "calibration-gated turns가 drift 하 wrong-action을 X% 감축 (커버리지 손실 Y%), 그로써 30B 로컬 모델이 raw frontier 완주율에 도달."**

*Sources: arXiv 2605.27922 · sakana.ai/ab-mcts · 2509.25140 · 2409.07429 · 2603.13517 · 2606.29537 · 2602.11964 · 2505.15277 · AgentPRM (WWW 2026) · 2606.23525 · 2605.08580 · 2603.05910 · 2605.10990 · 2605.14415 · 2604.02375 · 2606.15034 · 2604.17073 · 2604.04565 · Zylos UQ survey 2026-04 · 2504.13171 · 2605.20616 · 2606.25447 · Tongyi "Harness Gap".*
