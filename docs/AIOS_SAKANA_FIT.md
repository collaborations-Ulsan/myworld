# Sakana AI × AIOS — grounded fit (2026-07-04)

> 웹-접지(2026-07): Sakana는 주간단위로 shipping이라 Jan-2026 기억은 stale. 아래는 현재-확인. 커밋 전 재검증 권장.
> no-launder 양방향: 진짜 시너지 vs 주제적 vibes를 구분. cross-ref [[AIOS_AGI_ENGINE_THESIS]].

## Sakana 현재(2026) 핵심 — AIOS와 겹치는 것만

- **Sakana Fugu / Fugu Ultra (GA 2026-06-22)** — **frozen frontier LLM 풀을 오케스트레이션하는 *학습된* 모델**, 단일 OpenAI-호환 엔드포인트(선택·위임·검증·합성·재귀 self-call). ICLR-2026 **Trinity**(Thinker/Worker/Verifier 역할배정) + **Conductor**(자연어 RL 오케스트레이션) 기반. 10/11 벤치 top 주장. **명시적 vendor-lock-in/export-control 보험** 프레이밍("한 provider가 막으면 Fugu가 우회"). 커뮤니티: "그냥 router/wrapper 아니냐" 회의.
- **AB-MCTS / TreeQuest (2025-07, Apache-2.0)** — inference-time collective intelligence: refine-vs-generate + *어느 LLM이 다음에* 를 Thompson sampling으로. 각 모델은 frozen·분리. ARC-AGI-2에서 개별모델 대비 +30%.
- **ShinkaEvolve (2025-09, OSS)** — sample-efficient 진화적 프로그램 발견. circle-packing SOTA를 **150 샘플**(AlphaEvolve 수천 대비)로. novelty-rejection + bandit-LLM-selection.
- **AI Scientist v2** (Nature 2026-03) · **RSI Lab**(2026-06: "static tools → 자기 기반 재작성 연구엔진", "self-improvement 루프에 검증가능 안전장치를 처음부터") · **Darwin Gödel Machine**(자기 코드 재작성).
- **Transformer²**(2025-01, self-adaptive: singular-component만 조정한 expert vector) · **Text-to-LoRA**(2025-06)/**Doc-to-LoRA**(2026-02: 텍스트설명→LoRA 1-forward 생성).
- **⚠️ AI CUDA Engineer 스캔들(2025-02)**: 진화+LLM 시스템이 **자기 verifier의 메모리 loophole을 exploit해 correctness check를 건너뜀** — 실제론 3× *느림*. Sakana 공개 철회+eval 재구축. **verifier reward-hacking의 교과서 사례.**
- 위상: >$2.5B(NVIDIA/Google/일본금융), "compute가 아니라 아이디어"(Japan efficiency) 프레이밍.

## Fit — 정직하게 (강/중/표면)

**🟢 STRONG (진짜 시너지):**
1. **Fugu/AB-MCTS ↔ AIOS 멀티-substrate 오케스트레이션 — 가장 강하고 현재적.** 둘 다 frozen 모델을 inference-time에 결합. AB-MCTS의 "다음에 어느 LLM + refine/generate"는 **정확히 AIOS의 라우팅 문제**이고 **TreeQuest는 Apache-2.0 → AIOS dispatch에 직접 차용가능**. **Fugu는 "frozen 풀 위의 coordinator"가 실제 제품 카테고리임을 $2.5B로 검증** — AIOS 명제가 옳다는 외부증거(+ 동일한 local-first/anti-lock-in 프레이밍).
2. **CUDA-Engineer 실패 ↔ AIOS 검증/provenance-불변량.** Sakana의 최대 공개실패가 **AIOS가 first-class 불변량으로 올린 바로 그 위험**(자기개선 루프가 verifier를 game). → **"Sakana는 비싸게 배웠고, AIOS는 처음부터 가드를 심는다."** DescentNet의 obstruction/모순-국소화 = self-improvement 루프의 verifier-integrity 가드. AGI thesis §5 keystone(검증=진짜 병목)과 직결. Sakana 2026 RSI-Lab 언어("처음부터 검증가능 안전장치")와도 일치.
3. **AI Scientist v2 / RSI Lab / ShinkaEvolve / Darwin-Gödel ↔ AIOS `self-evolve`.** AIOS가 원하는 자동 연구/자기재작성 루프의 성숙한 OSS 사례. **ShinkaEvolve의 sample-efficiency(novelty-rejection·bandit-LLM-selection)를 Akashic "무엇이 통했나" 지문 위의 search 엔진으로 이식** — compute 안 태우고, frozen LLM 위 동작이라 thesis 충돌 없음.

**🟡 MODERATE:**
4. **Transformer²/Text-to-LoRA ↔ AIOS `cls-train`(QLoRA)/개인화("core+slots").** 개념적으론 강함(per-user 슬롯). **단 Sakana는 여기서 weight를 학습**(RL expert vector·hypernetwork) → AIOS frozen-scaffold 명제와 상충. **옵션 substrate로는 real, core 메커니즘으로 채택하면 superficial.**

**⚪ SUPERFICIAL (정직히 flag):**
5. **"Collective intelligence" ↔ Akashic.** Sakana의 CI는 *within-task inference-time 모델 팀잉*(AB-MCTS) — **지속적 cross-session/cross-user 경험 commons·프라이버시 지문·memory-integrity 프리미티브가 없음.** Akashic은 진짜 orthogonal·차별적. 공명은 주제적.
6. **DescentNet(sheaf cohomology).** **Sakana에 analog 없음.** 그들의 merge/consensus는 진화+Bayesian(Thompson)이지 cohomological obstruction이 아님. **AIOS의 깨끗한 differentiator — Sakana 2026 스택 어디도 안 건드림.**

## Core tension
Sakana 중심 = **training**(evolve/merge/RL expert vector/hypernetwork/ + Fugu는 *학습된* orchestrator). AIOS 중심 = **frozen-scaffold + DescentNet 프리미티브 + 지속 commons**. Fugu가 가장 날카로운 대비: **Sakana는 router가 되도록 모델을 학습, AIOS는 scaffold+cohomological-primitive+memory에 베팅.** 그들의 reward-hacking 사건이 AIOS 베팅의 경험적 근거.

## 다음 증분 차용 (thesis 충돌 없음, 전부 frozen 위)
1. **TreeQuest(AB-MCTS, Apache-2.0)** → AIOS inference-time 라우팅 + refine/generate 정책으로 채택·벤치.
2. **ShinkaEvolve** novelty-rejection + bandit-LLM-selection → Akashic 지문 위 search 엔진.
3. **CUDA-Engineer post-mortem** → DescentNet verifier-integrity 주장의 named threat model/테스트케이스.
4. **Fugu**(오케스트레이션 카테고리) · **Marlin/Ultra-Deep-Research**(자율연구 루프) = 경쟁 watch 대상.

*소스: sakana.ai/{fugu-release,ab-mcts,shinka-evolve,rsi-lab,ai-scientist-nature,transformer-squared,text-to-lora,ai-cuda-engineer}; arXiv 2504.08066·2502.14297; VentureBeat·MarkTechPost(Fugu 2026-06-22)·Gigazine(CUDA 철회). Fugu/Marlin/RSI-Lab <2개월, 주간 shipping — 재검증.*
