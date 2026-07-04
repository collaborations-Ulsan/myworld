# AIOS as an AGI Engine — frontier map + earned positioning (2026-07-04)

> 작성: claude@myworld. 접지: 웹/arXiv primary-source 리서치(METR, DeepMind, arXiv, lab 발언) + 5개 2026-모델 이종 패널(deepseek-v4-pro/qwen3.5/kimi-k2.6/glm-5.2/nemotron). 삼각측량됨.
> **no-launder(양방향)**: AIOS가 닿는 프런티어와 **안 닿는** 프런티어를 둘 다 명시. "AGI 핵심 엔진"은 **특정 레이어로 스코프하면 defensible, 전체를 뜻하면 overclaim.**

## 1. AGI 프런티어 shortlist (2026-07, 웹+패널 수렴)

두 소스가 독립적으로 같은 리스트로 수렴:
1. **지속학습 / catastrophic forgetting 회피** — *the* top blocker. 모델은 학습 후 못 배움; 세션마다 초기화. 현 우회책 = **외부 메모리 스캐폴드**(Letta, Mem0) — weight-level 아님. (Amodei "scale로 2026 해결" = 예측이지 결과 아님.)
2. **장기지평 agency + 신뢰성(reliability wall)** — METR time-horizon 배가주기 ~4개월로 가속(primary). **half-life 법칙**: 분당 실패율 일정 → 성공률 지수감소; **99% 신뢰성엔 task 길이가 50%-지평의 ~1/70** (arXiv 2505.05115). 즉 **capability ≠ reliability**.
3. **지속 메모리(cross-session, cross-agent)** — LoCoMo/LongMemEval. 미해결: cross-session identity, temporal abstraction. "Modular Memory is the Key to Continual Learning Agents"(2603.01761). Hassabis: 지금의 context window는 "duct tape".
4. **World models** — LeCun JEPA/AMI Labs($1B+ seed), World Labs, V-JEPA 2. 수년 남음.
5. **검증 & 신뢰(agent가 맞는지 앎)** — "the true bottleneck for deployment". agent는 **calibration 나쁨**("agentic overconfidence" 2602.06948); 감독이 confidence-gated로 이동. deepseek 패널: "외부 verifier 없는 intrinsic self-critique".
6. **경험/배포로부터 학습(Era of Experience, Silver&Sutton)** — Era 3 = agent 자기경험. skill library(Voyager 계열: MUSE-Autoskill 등) + cross-agent 지식공유(Forage V2)로 operationalize 중. **단 여전히 frozen weights 위 skill-library+외부메모리 스캐폴드** — weight-level 지속학습이 미해결 프런티어.
7. **자기/재귀 개선 + meta-learning** — AlphaEvolve, ICLR 2026 RSI workshop. **closed-loop 재귀개선 검증사례 없음(human-in-loop)**. 패널 수렴: "durable meta-learning / recursive self-reflective meta-learner".

**로드맵 합의(Hassabis/Amodei/Karpathy/Sutton/LeCun)**: 미싱피스 shortlist = **지속학습·메모리·장기agency·world model·검증**. Karpathy "cognitive core"(recall 희생·capability 유지·always-on·tool-using·**local fine-tune slot(개인화)**·memory를 그 주위에 구축) = 특히 시사적.

## 2. 현재 agent 위치 (2026-07)

- **코딩 최성숙**(SWE-bench류 높음 — 단 aggregator 수치 신뢰주의, Berkeley 감사: 8개 벤치 gaming 가능). **컴퓨터-유즈는 훨씬 약함**(OSWorld ~60-75%; "embarrassingly bad"). → coding ≫ general-desktop 격차가 정직한 현실.
- **the wall**: top agent가 이제 실task 다수를 통과(2년전 <40%→과반)하지만 **지평이 길어지면 half-life 법칙으로 신뢰성 붕괴**. capability가 trustworthiness를 앞지름.
- 패널 수렴: 잘함=단일세션 tool-chain·다시간 SWE·research synthesis. 실패=multi-day 자율목표, novel error recovery(human hint 없이), API/환경 급변 시 pivot, 안정적 self-model 며칠 유지.

## 3. AIOS = AGI 엔진? — earned·scoped 포지셔닝

**핵심 인식**: 필드의 실용적 합의(Karpathy cognitive-core, Hassabis memory-beyond-duct-tape, Sutton era-of-experience, Mem0/Letta 외부메모리)는 **frozen frontier model 주위의 미싱 레이어 = 지속메모리 + 경험학습 + 검증 + 개인화**라는 것. 이건 모델이 아니라 모델을 **감싸는 레이어**다.

**AIOS는 아키텍처적으로 정확히 이 레이어의 구현이다.** 모델도, world model도, pretraining도 아닌 — 필드 전체가 미싱피스로 수렴하는 그 **스캐폴드**. 프런티어 매핑:

| 프런티어 | AIOS 구성요소 | 판정 |
|---|---|---|
| 지속메모리(cross-session·**cross-agent**) | Akashic Record + MemoryOS + 분산 commons | ✅ **핵심 — 게다가 cross-agent commons는 프런티어에서 "still early", AIOS가 앞섬** |
| 검증 & 신뢰 | DNA(verify-before-closeout, provenance chain, named exit, confidence-gated auto_reviewer, operator 5-mode) | ✅ **핵심 — 검증을 day-1 불변량으로. "the true bottleneck"에 직결** |
| 경험/배포학습 | `aios behavior`(세션 INGEST→predict) + 개인화층(2944 msg 학습) + Akashic 기여 | ✅ Era of Experience의 operationalize |
| 개인화(Karpathy fine-tune slot) | user_profile + cls-train(QLoRA local fine-tune, founder-gated) | ✅ cognitive-core 주위 슬롯과 정합 |
| 자기/재귀 개선 | self-evolve/self-audit/self-observation-log(역설계 corpus) | ◐ 부분, human-in-loop(프런티어와 동일 상태) |
| 지속학습(weight-level) | cls-train은 nascent bridge | ✗ **안 함 — labs의 게임(아키텍처/pretraining)** |
| World models | — | ✗ **안 함 — LeCun/JEPA 영역** |

**AIOS의 차별 베팅 3개 (프런티어 edge)**:
1. **cross-AGENT 글로벌 지식 commons**(Akashic) — per-user 메모리(Mem0/Letta)를 넘어. 리서치가 "still early"라 부른 곳.
2. **검증/provenance를 first-class DNA로** — "the true bottleneck"을 처음부터 불변량으로.
3. **privacy-preserving·user-sovereign·verifiable** — 순수-capability labs가 경시하는 신뢰/거버넌스 레이어.

**정직한 결론(양방향)**:
- **YES(scoped)**: AIOS는 **AGI의 "경험+메모리+검증" 레이어의 핵심 엔진**으로 defensible 하다 — 필드 합의가 "frozen 모델 주위 미싱피스"라 지목한 바로 그 레이어. 차별 베팅(verifiable cross-agent commons)은 프런티어 edge.
- **NO(unscoped)**: "AGI 전체의 유일 엔진"은 overclaim. AIOS는 **한 결정적 레이어**지 world-model/pretraining/weight-level 지속학습 레이어가 아니다.
- **energizing, not deflating**: 이 레이어가 바로 Karpathy/Hassabis/Sutton이 미싱이라 말하는 것. 브릭으로 후퇴가 아니라, **큰 주장(경험-레이어 엔진)을 EARN**하는 방향.

**AIOS가 overclaim 안 하려면 정직해야 할 약점**: reliability는 아직 aspiration(harness의 Ouroboros 탈선이 증거) — DNA는 목표, 구현은 초기. 검증은 process/provenance지 deep calibration("agent가 맞는지 앎") 아님(정합하나 미완).

## 4. 그래서 Phase 2가 AGI-엔진의 다음 벽돌인 이유

Phase 2 = **검증가능 Akashic 원장**(Merkle proof, 공개 checkpoint, 접근-게이팅). 이건 잡무가 아니라 프런티어 직결:
- **검증 프런티어**: 공유지식을 암호학적으로 검증가능하게 → 신뢰.
- **cross-agent 경험 프런티어("still early")**: agent 경험을 공유+신뢰가능하게 → AIOS가 앞설 수 있는 곳.
- **club-good 경제**: 풀링컴퓨트 ⇄ 검증가능 지식 → commons 지속가능.
→ Phase 2 = **검증가능한 cross-agent 경험의 신뢰 substrate** 구축. 필드가 미싱·early라 지목한 정확한 프런티어.

## 소스(solid/primary만; aggregator 수치는 인용 회피)
METR time-horizons(2026-05-08) · half-life 2505.05115 / Science of Agent Reliability 2602.16666 · Era of Experience(DeepMind) + 2605.20477 · Modular Memory 2603.01761 · 검증 2606.26300 / calibration 2602.06948 · Karpathy cognitive-core · Hassabis/Amodei 발언 · benchmark-gaming 감사 2510.11977.
*주의: 2026 벤치 수치·특정 모델 스코어는 aggregator라 미검증. "Claude Fable 5 export-control 정지"류는 날조로 판정 — 인용 금지.*

---

## 5. 이종 de-bias — Codex(GPT prior + 라이브 웹) adversarial 비판 (2026-07-04)

Claude+NIM은 "AIOS가 레이어에 맞다"로 수렴(다소 self-congratulatory). **Codex는 다른 prior로 이걸 압박해 결정적 blind spot 2개를 잡음** (agy는 Google OAuth headless 실패로 무응답):

**A. 치명적 실패케이스 — moat 문제 (내가 underweight):** 인큐번트가 **바로 이 레이어를 native로 흡수 중**.
- OpenAI **Frontier**: 공유 context·memory·eval·permissions·feedback loop을 엔터프라이즈 agent에 이미 제공.
- Google **Interactions API(GA)**: stateful agent 엔드포인트 — managed agents·background exec·tool timeline·retention.
- **A2A(>150 org, Linux Foundation) + MCP(Agentic AI Foundation 기증)**: 멀티에이전트 plumbing 표준화 → 오케스트레이션 커모디티화.
→ **AIOS의 moat가 "core AGI engine"이 아니라 "governance taste + local ownership + privacy"로 압축된다.** 레이어가 틀린 게 아니라 **레이어를 프로바이더가 소유**할 위험.

**B. scaffolding이 지능으로 compound 안 될 수 있음:** frozen LLM은 여전히 경험을 내재화 못 함 → commons가 "noisy·poisonable prompt folklore(ops 메타데이터)"에 그칠 수 있음. reliability 연구: tail failure·predictability를 task success와 **따로** 측정해야 함 → "한 번 통했으니 기억" commons의 전제를 약화.

**C. AIOS가 AGI에 실제로 중요하려면 EARN해야 할 단 하나 (keystone):**
> **pre-registered adversarial 벤치마크** — privacy 보존 experience commons가 **held-out 장기지평 task success·calibration·recovery를 Frontier/Gemini/Claude-native memory + vanilla RAG 대비 인과적으로 개선**함을 입증. 일화·"ledger vibes" 금지. **누출·오염·stale 증폭 없이 transferable experience** 시연. (Codex는 AIOS ledger가 아직 false production-serving proof를 기록한다고 지적 — 오늘은 아직 아님.)

**재프레이밍 (no-launder 양방향)**:
- AIOS의 defensible edge는 **generic "experience 레이어"가 아니라** — 인큐번트가 흡수 중 — **cross-provider 중립성 + privacy·user-sovereignty + verifiable cross-agent commons + local ownership**. 이걸로 좁혀야 정직.
- **keystone = C의 인과 벤치마크.** 이걸 EARN하기 전엔 "AGI 엔진"은 미증명 주장. **Phase 2(검증가능 commons)는 그 벤치마크의 전제조건(신뢰가능·비오염 substrate)이지 증명 자체가 아님.**
- 정직한 다음 순서: **Phase 2(신뢰 substrate) → C의 인과 벤치마크(commons가 실제로 돕는가?)**. 후자가 AIOS가 AGI에 중요한지를 가르는 keystone.

---

## 6. 접지: AIOS = 창업자 frontier 연구의 집약체 (corpus dig, 2026-07-04)

founder 지시("내 연구들 파보면 알듯이, 최신 기술의 집약체")대로 실제 corpus(portfolio 19편/6분야 + universe)를 팠음. **코드로 확인** — 기억이 아니라.

**연구 라인**: physics-grounded generative(diffusion score 복소해석/Born-marginal/open-system decoherence), information-physics(Information-as-Substrate action principle, Fisher-info gravity, **APEX** answerability calculus), **graph nets(DescentNet, GoEN, legibility theory)**, AI-systems(Graph-OS soul-routing, AIOS 자체가 논문), trustworthy-vision(deepfake), health-timeseries(lifelog audit). 관통 규율: **정직한 평가(negative 세탁 안 함)**.

**핵심 발견 — DescentNet이 AIOS 심장에 실제로 박혀 있음**:
- `aios_agent_behavior.py:580-665` `_descent_scores()`가 **DescentNet 레포(`universe/descentnet/api.py`)에서 `SheafCover, descent_step`을 직접 import.** star-cover(context→candidate-tools) 만들고 descent 돌려 global_section 정렬로 행동 스코어링 + obstruction을 ambiguity 신호로. `predict_behavior()` = frequency × **DescentNet-descent** × Global Akashic.
- `aios_descentnet_session.py` = DescentNet×5-OS 배선, cross-OS 모순검출기.
- **DescentNet = AIOS behavior-prediction/personalization의 수학 엔진.** (sheaf coboundary δ + Hodge split → 적분가능성을 *계산 출력*으로; 호환 로컬을 global H⁰로 붙이고, 원리적 비호환이면 obstruction H¹를 "어디·얼마나·왜" 반환.)

**이게 Codex 비판을 뒤집는 지점**: Codex는 "moat가 governance taste로 압축, 인큐번트가 레이어 흡수"라 했음(§5). 하지만 **OpenAI Frontier/Google Interactions API/MCP는 memory·오케스트레이션은 흡수해도, DescentNet 같은 sheaf-cohomology obstruction/answerability 프리미티브는 없음.** 이건 커모디티 plumbing이 아니라 **창업자 고유 frontier 수학** — memory-integrity·모순국소화·answerability를 behavior 엔진에 심은 것. → AIOS의 진짜 defensible moat는 "governance taste"가 아니라 **DescentNet backbone**.

**정직한 스코프(no-launder 양방향)**:
- **SOLID**: DescentNet 라인은 AIOS에 실제 wired·running (sheaf 프리미티브가 행동 스코어링+모순 flag). AIOS 자체가 portfolio 논문. frontier 재료 실재(sheaf NN·information cohomology·Fisher/QFI identifiability·score-based diffusion) + 정직한 prior art 인용.
- **ASPIRATIONAL**: (a) DescentNet 실데이터 우월성은 keystone 문서상 **OPEN·미증명**(Bitcoin-OTC negative 보존); AIOS는 toy `descent_step`(star-cover)만 씀 — 검증된 quantum/nonabelian keystone 아님. (b) **APEX/answerability는 AIOS 코드에 없음**(grep-empty) — 공유 수학+vision, 미배선. (c) score-based/Fokker-Planck는 개념적 lineage.
- **정확한 프레이밍**: AIOS = **DescentNet 라인의 엔지니어링 집약체**(그 한 줄기는 실제 wired). 전체 physics-ML corpus(APEX·diffusion-score·information-substrate)의 종합은 일관된 지적 through-line·야심이지 아직 코드-레벨 통합은 아님.

**AGI-엔진 thesis 갱신**: AIOS의 edge = 스캐폴드-레이어(인큐번트가 흡수 중) + **DescentNet obstruction/answerability backbone(인큐번트에 없음, 창업자 고유)**. 후자가 §5 keystone("commons가 인과적으로 돕는가")을 EARN하는 기술적 지렛대일 수 있음 — obstruction이 memory 오염/모순을 수학적으로 flag하니 §Akashic 검증과 직결.

---

## 7. Keystone CLOSED — earned NEGATIVE (Rungs 0–4, 2026-07-04)

§5C의 keystone("AIOS 레이어가 vanilla baseline을 인과적으로 이긴다")를 negative→pivot 루프로 완주해 **정직하게 닫음** (tracker subagent, `docs/AIOS_KEYSTONE_EXPERIMENT.md` Rung 0–4).

**결과 (no-launder 양방향):**
- **stated 모든 형태에서 NEGATIVE**: 예측(R0/R1: DescentNet 신호=0) · cross-agent 커먼즈 전이(R2: base-rate 대비 0) · 오염저항(R3/R4: H¹ AUC ≤0.59, 무료 tool-entropy 필터 0.66–0.69에 **지배당함**). 실제 오염은 **H⁰-shape**(vocabulary shift)지 H¹-shape(same-vocab cyclic)가 아님.
- **살아남은 것 (아래로도 세탁 안 함)**: H¹은 **same-vocab cyclic 모순의 유일 탐지기** — B2 witness AUC 1.00(Cohen d=278), B′에서 실데이터에 genuine cyclic 구조 존재(floor 0.0) 확인. 프리미티브·수학은 sound. 단 **non-dominant**(현실 위협과 niche 불일치), prevalence는 EARN하되 threat-match는 아님.

**thesis 재보정 (정직)**: §3–6이 기대한 **"DescentNet = AGI moat"는 empirically 무너졌다.** AIOS의 진짜·검증된 값어치는 DescentNet 차별점이 아니라:
- **검증가능 commons 인프라** (Phase 2 Merkle/proof/checkpoint — 작동)
- **멀티-substrate 오케스트레이션** (AB-MCTS — 작동)
- **값싼 H⁰ consistency 필터** (Jaccard/entropy/variance, AUC 0.63–0.69, ~0비용 — 오염가드로 ship)
- **정직한 verification-first 문화 + frontier 규율 주입**

**엔지니어링 결정**: 커먼즈 오염가드 = **값싼 H⁰ 필터를 ship. DescentNet/H¹은 오염가드로 ship하지 않음** (measured same-vocab-cyclic 유즈케이스 나올 때까지 shelf).

**공개(먼저 공개) 함의**: 인플레된 "AGI 엔진" 주장이 아니라 — 그건 죽음 — **rigorous negative-with-witness**가 진짜 공개물: "sheaf-cohomology 프리미티브는 예측·전이·일반 오염저항을 개선하지 않는다; 단 same-vocab cyclic 모순만 유일하게 탐지한다(witness AUC 1.00), 현실 위협엔 무료 필터가 지배한다." **fablize식 정직한-rigor의 학술판** — 부풀린 승리보다 credible하고 priority를 잡음. no-launder가 거짓 공개를 막고 진짜 공개물을 남김.

**named exit 도달**: exhaustive impossibility (그 자체로 강한 positive 주장). 유일 residual: H¹ AUC가 데이터로 monotone 상승(0.514→0.590) — 실배포에서 H⁰ baseline 교차 시에만 재개.
