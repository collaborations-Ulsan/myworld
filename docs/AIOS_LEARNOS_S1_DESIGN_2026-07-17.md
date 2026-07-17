# LearnOS S+1 — pivot design (2026-07-17), grounded in Radar Sweep 01

**왜 pivot**: DriftBench keystone STOP (weak+AIOS 1/18, 75% doom-loop). 레이더 스윕 01이 인용 증거로
원인과 방향을 못박음 (`docs/research/AIOS_RADAR_SWEEP_01_2026-07-17.md`). LearnOS v0는 3-iter pulse에서
기계는 돌았으나(원장 54행) **복리 신호 없음(5/6 평탄)** + "승격이 다른 태스크로 전이되는가" 미검증.
S+1은 그 질문을 판정한다.

## 근거 (radar, 전부 1차 인용)

| 발견 | 함의 (S+1 설계) |
|---|---|
| RSI 서베이 2607.07663 — 자기개선 강도 ∝ 검증자 위계(formal>PRM>rubric>intrinsic) | STOP 원인 = 약한 검증자. **게이트 검증자는 가능한 가장 강한 것**(functional held-out tests, LLM-judge 아님) |
| LEVI 2605.09764 — 강한 *탐색 구조*가 큰 모델 대체 (archive+mutation router, 3.3-35× 싸게) | **LearnOS를 linear 게이트→SEARCH로**: diversity-preserving archive + mutation routing |
| Beyond pass@1 2603.29231 / CL-Bench 2606.05661 — 메모리 스캐폴드가 장기지평을 *해친다* | 승격물이 순이득임을 **증명 전엔 주입 금지**(내 A1 부정 가드); RDC/VAF/GDS/MOP를 신뢰성 축으로 |
| Blind Curator 2607.07436 — 편향 judge가 skill 폐기 조용히 끔, false-pass는 데이터로 복구 불가·무증상 | **skill 승격 전 defect-injection 감사** — 검증자에 알려진 결함을 주입해 false-pass율 측정 |
| SkillLearnBench(cxcscmu) — self-feedback만으론 recursive drift, 외부 피드백 필수 | v0의 외부 검증자 규율 유지·강화 |
| VISTA 2603.18388 — 결함 seed에서 GEPA 열화(23.81→13.50), hypothesis-gen과 rewriting 분리 시 87.57 회복 | GEPA 흡수 시 **hypothesis-gen ⊥ rewriting** 강제 |
| AutoLab 2606.05080 — 장기지평 성공 예측자 = plan 품질 아닌 **benchmark→edit→feedback loop persistence** | plan이 아니라 loop을 보상 |
| PURE(CJReinforce) — min-form credit가 PRM reward-hack 죽임 | 신용 배분은 min-form |

## S+1 = LearnOS를 SEARCH로 (핵심 업그레이드)

**변경 1 — linear improver → 진화 SEARCH (LEVI/ShinkaEvolve-lite)**:
- diversity-preserving **archive**(모든 후보·점수·lineage; hill-climb 금지 — v0에 이미 원장 있음, 여기에
  MAP-Elites식 다양성 셀 추가).
- **mutation router**: 어떤 후보(코드패치/CoT 스캐폴드/도구)를 어떤 기질(로컬/NIM)로 변이할지 bandit 라우팅.
- 후보 생성(hypothesis)과 재작성(rewrite)을 **분리** (VISTA 교훈).

**변경 2 — 진짜 복리 판정 = TRANSFER-HOLDOUT (v0가 못 한 질문)**:
- 태스크를 **A(mine) / B(transfer-holdout) / sentinel** 3분할. skill/도구/스캐폴드는 **A에서만** 채굴.
- **복리 = B(A에서 안 본 태스크)의 held-out 성공률이 iter에 걸쳐 오르는가.** 같은 태스크 재풀이는 복리 아님.
- 성공 기준(사전 고정): iter k의 축적 라이브러리가 iter 0 baseline 대비 **B에서 통계적으로 유의하게** 상승,
  고정 비용·sentinel 무회귀. 10-15 iter (v0 3→확장).

**변경 3 — 검증자 무결성 감사 (Blind Curator)**:
- 승격을 신뢰하기 전, 검증자에 **알려진 결함 주입**(정답인 척하는 가짜 패치, 미묘한 오답)해서 false-pass율
  측정. 임계 초과면 그 검증자로의 승격 동결(무증상 drift 차단).

**보존 (v0에서)**: 외부 held-out verifier, contract-fuzz 도구, sentinel, 승격 원장, No OntologyOS/QLoRA.

## 정직 스코프

- S+1이 판정하는 것: **"축적이 안 본 태스크(B)로 전이되어 복리로 오르는가."** 오르면 AGI 개념의
  compounding 주장에 첫 실증. 안 오르면 — Beyond-pass@1이 예측하듯 — "memory in a costume"이 재확인되고,
  그 자체가 정직한 결과(no-launder). 어느 쪽이든 masterplan·self-obs에 반영.
- 여전히 keystone 규율: 이 판정도 사전 기준·외부검증·이종 리뷰를 거친다. 데모/평탄은 증거 아님.

## 흡수 대상 (OSS, radar 검증)
- gepa-ai/gepa (MIT, `optimize_anything`) · SakanaAI/ShinkaEvolve (Apache) · ttanv/levi (MIT, hidden gem) —
  S+1은 LEVI 구조를 우선(작은 모델·저비용), GEPA는 프롬프트/CoT 최적화 엔진으로.
