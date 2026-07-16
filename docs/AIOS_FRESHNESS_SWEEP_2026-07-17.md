# Freshness Sweep — 2026-07-17 (WebSearch + Council-Perplexity 교차검증)

> Agile Loop Ground 단계 산출물. 웹 스윕(1차 소스 위주)과 Council-Perplexity(애그리게이터 포함,
> hypothesis-grade)를 교차검증한 종합. 마스터플랜/Sprint 백로그의 접지 원본.

## 1. 신모델 (2026-07-17 기준)

- Frontier: Claude Sonnet 5 (6/30, 1M ctx) · Fable 5 (Mythos-class, 7/1 복원) · **GPT-5.6 GA 7/9**
  (Sol 91.9% Terminal-Bench 2.1 SOTA / Terra / Luna $1/$6) · Grok 4.5 (7/8-10, 1.5T MoE, 83.3% T-Bench).
  Gemini 3.5 Pro: 7/17 목표 보도되나 **미확인** (베이스 재구축설; 공식 카드 없음 — 보류).
- 오픈웨이트: **GLM-5.2** (6/13, 오픈 1위; NIM에 7/2 등재) · Kimi K2.7-Code (thinking 토큰 -30%) ·
  DeepSeek V4 Pro/Flash · Qwen 3.6 · **Inkling (Thinking Machines, 7/15: 975B/41B active MoE,
  멀티모달, 1M ctx, Apache 2.0)** — Murati 첫 모델. gpt-oss v2는 없음 (2025-08 그대로).
- Dual RTX 5090 (64GB) 적합: 스위트스팟 30-40B — **Qwen3.6-27B Q4 (~16GB, 77.2% SWE-bench, 최고
  dense 코더 — pull 후보)** · DeepSeek-R1-32B · 70B Q4는 ~27 tok/s (PCIe 동기화 오버헤드).
  NIM: Nemotron 3 Super(120B)/Ultra(550B)/Nano Omni + GLM-5.2.
- ⚠ Perplexity발 "Llama 5 405B / Qwen 4.1 / DeepSeek R3 / GLM-5 745B / Qwen3.5-397B dual-5090
  48tok/s"는 애그리게이터 출처 — 1차 확인 전 인용 금지.

## 2. 진화/유전 방법론

- **GEPA (ICLR 2026 oral, 프로덕션)**: reflective prompt evolution — GRPO 대비 +6pp 평균(최대 +19pp)
  을 **35× 적은 롤아웃**으로; MIPROv2 +10pp; `pip install gepa` / dspy.GEPA; Decagon 프로덕션.
  (arXiv 2507.19457)
- Sakana 라인: DGM (SWE-bench 20→50%) → **RSI 전담 랩** 신설; SIFT (ICLR 2026, +11pt/$25 —
  평가 비용이 병목); **ShinkaEvolve** (OSS: novelty rejection-sampling + bandit LLM-ensemble,
  circle-packing SOTA를 150 evals로). CodeEvolve(OSS)가 AlphaEvolve를 5/6 문제에서 이김
  (2510.14150). AlphaEvolve 프로덕션: Google 컴퓨트 0.7% 회수.
- HyperAgents/DGM-H (2603.19461, Perplexity발 — 수치는 애그리게이터, 교차검증 필요): task+메타로직
  동시 진화; ablation "아카이브 없으면 local optima, 메타 고정이면 정체".
- **⚠ 비판 (load-bearing)**: "Simple Baselines are Competitive with Code Evolution" (2602.16805) —
  3개 도메인 전부에서 단순 베이스라인이 진화와 동급 이상; 성과의 지배 요인은 search-space 설계.
  + **reward hacking 실측**: 자기개선 "최적화"의 **73.8%(KernelBench)/46.8%(ALE-Bench)가 실효 없는
  proxy-gain** (OpenReview ikrQWGgxYg). eval-hardening (블라인드 테스트·held-out 평가자)은 아직
  표준 관행이 아님 (2606.23075).
- **ASG-SI** (2512.23760): 성공 궤적→스킬 초안→**검증기-백업 replay + contract 체크 후에만 승격**
  — AIOS DNA (draft-first·append-only·provenance)와 거의 동형. 흡수 shape로 채택 가치.

## 3. "Harmonic agent" 실체 판정

- 확립된 단일 브랜드 없음. **최유력 = Harmonic (Tenev/Achim)의 "Aristotle Agent"** (2026-03):
  자연어→Lean 형식증명, 24h 무인 가동, ProofBench #1 (+15%), IMO-gold 계보, $1.45B.
  → 7월 담론에서 "Harmonic agent" ≈ **검증기-백업(환각-불가) 추론 에이전트**.
- founder의 기존 결정과 정합: hivemind verifier 논의에서 founder가 Lean 증명(외생 검증기) 노선을
  택함 (project_hivemind_verifier_settled). ⇒ AIOS 적용 = 검증기-백업 레인 강화 (Lean/형식 검증이
  가능한 문제군에 외생 검증기 우선).
- 차선 후보: 진동자/동기화 다중에이전트 (KoPE Kuramoto 2604.07904 등 — "harmonic" 브랜딩 없음),
  MOAT joint-alignment (EMNLP 2025). **founder 1-word 확인 권장** (Aristotle 노선 맞는지).

## 4. Agile/QA for agents (2026 관행)

- MS "Agentic-Agile" (명명된 프레임워크 존재). 합의 관행 = **eval-driven development**:
  자체 eval 하니스 우선, 시스템 테스트(파일/명령/상태) 관점, code-grader 우선 + LLM-judge는
  human gold 대비 캘리브레이션 후 CI 머지 게이트로.
- **5-게이트 AI-native CI/CD**: lint → offline eval → cost budget → **shadow eval on prod traces**
  → canary with auto-rollback. 실패 트레이스는 offline eval 세트로 환류.
- AIOS 매핑: DriftBench=offline eval; hivemind verify=게이트; 부족한 것 = shadow/canary 레인 + 비용 게이트.

## 5. Sprint 2 흡수 백로그 (랭킹 확정)

1. **Anti-reward-hacking 게이트** (최고 인식론 ROI, LOW effort): 모든 자기개선/진화 성과 수용 전
   held-out 블라인드 스플릿 + proxy-vs-real 델타 체크. DriftBench 위 하니스 작업.
2. **GEPA** (LOW): AIOS 캡슐/프롬프트를 DriftBench를 eval로 삼아 진화. ASC-0284의 negative
   (수제 캡슐 무효)에 대한 정확한 pivot — 수제 대신 GEPA-진화 캡슐로 재도전.
3. **ASG-SI 스킬-그래프 패턴** (MEDIUM): 궤적→스킬 초안→검증 replay→승격. memoryOS draft-first와 동형.
4. **ShinkaEvolve** (MEDIUM): 150-eval급 sample-efficient 진화 엔진; bandit LLM-ensemble이
   multi-substrate 설계와 정합.
5. **5-게이트 CI + shadow/canary** (LOW-MEDIUM): hivemind verify에 배선; 실패 트레이스→DriftBench 환류.
- 모델 갱신: qwen3.6-27b 로컬 pull 검토; NIM 풀에 GLM-5.2 추가; Inkling 관찰; Gemini 3.5 Pro 보류.
- Harmonic: founder 확인 후 — Aristotle 노선이면 "외생 검증기 레인" (Lean 게이트) 설계 티켓 오픈.

*출처 URL 전체는 세션 기록 (웹 스윕 브리프 + Council-Perplexity 응답 원문).*
