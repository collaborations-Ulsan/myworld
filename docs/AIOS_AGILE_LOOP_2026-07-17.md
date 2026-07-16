# AIOS Agile Loop — 상설 프로세스 헌장 (2026-07-17)

**Authority**: founder 2026-07-17 — "Council 활용해서 Agile Process로 QA까지 진행하며, AGI를 위한
AIOS·AIOS를 위한 AGI, 다양한 방법론들(진화, 모델링, 유전, harmonic agent, …), 가장 최신의 자료와
가장 최신의 모델들과 루프돌면서 완성해나가."

## 사이클 (스프린트 = 세션 단위)

1. **Ground** — 기록에서 상태 델타 + freshness 스윕 (신모델·신방법론; WebSearch + Council).
2. **Plan** — 백로그 랭킹; 비자명 선택은 Council de-bias 패널 (`hub panel --set debias`) 또는
   nv panel/codex 적대 레인. 판단 종합은 main context.
3. **Build** — executor subagent 병렬 (파일 소유권 분리, 경로 명시 커밋).
4. **QA 게이트 (DoD — 전 항목 충족 전엔 "완료" 금지)**:
   (a) 테스트 통과 + 회귀 0, (b) 라이브 검증 (해당 시 오프라인 조건), (c) 이종 리뷰 ≥1
   비-Claude (codex stdin-diff / nv panel / council), (d) 정직한 한계 명기, (e) durable 기록
   (커밋 + 필요시 ledger/self-obs).
5. **Review** — 결과를 Council/이종 기질에 교차 (특히 keystone급), no-launder 양방향.
6. **Retro** — self-obs 항목 + memory 갱신 + 다음 스프린트 백로그.

## 방법론 레인 (탐색은 병렬, 판정은 실험)

- **진화/유전**: DGM-H/HyperAgents(2603.19461) 노선 — 아카이브 + 메타-수정. 흡수 후보:
  OpenEvolve(MAP-Elites), MAE(Proposer/Solver/Judge 1모델 3역), AVO. 기존 자산: TreeQuest(이미
  흡수), self-improve 스킬, prizehunter LoRA 루프.
- **Harmonic**: 확립 브랜드 없음(2026-07 조사). 실물 근접 = MOAT(EMNLP 2025, planner↔executor
  교대 정렬·수렴 보장) + 공유 스킬/메모리 조화(OpenSpace/MemOS). AIOS 적용점: head↔subagent 정렬.
- **모델링**: DriftBench(동결 prereg)가 판정 기구; SLM-delta·capsule(ASC-0284)류 A/B가 도구.
- **스킬 진화**: OpenSpace(HKUDS) FIX/DERIVED/CAPTURED — skills_loader(이미 흡수)의 다음 층.

모든 방법론 주장은 keystone 규율을 따른다: 사전 기준 → 실험 → 정직 보고 (수렴·데모는 증거 아님).

## 최신성 루프

스프린트 Ground 단계마다: 신모델 체크(NIM 카탈로그·ollama pull 가능·frontier), 방법론 스윕
(arXiv/HF/Council-Perplexity). 애그리게이터 수치는 교차검증 전 hypothesis-grade.

## Sprint 1 (2026-07-17) 백로그

| # | 항목 | 판정 |
|---|---|---|
| S1-1 | 7/12 워킹트리 커밋 (기록 안착) | ✅ 70017d8 |
| S1-2 | WP-A 실상 검증 → 잔여 갭 마감 → **freeze → DriftBench Stage-1 실제 실행** | 최우선 |
| S1-3 | 판정: analyze.py 두 바(13/18 + 17/24) 계산·공개, 이종 리뷰 | S1-2 뒤 |
| S1-4 | Retro + Sprint 2 계획 (방법론 흡수 우선순위: 웹 스윕 교차검증 후) | 마감 |

이월 (Sprint 2 후보): OpenSpace 스킬진화 흡수 · MAE식 자기개선 루프를 DriftBench-화 ·
MOAT식 head↔subagent 정렬 · ASC-0281 seeds 1,3 영수증 커밋 · 신모델 풀 갱신(GLM-5.2/Qwen3.5-397B
교차검증 후 ollama/NIM 풀 반영) · 7/12 세션 self-obs 공백 (타 세션 작업 — 기록만, 대필 금지).
