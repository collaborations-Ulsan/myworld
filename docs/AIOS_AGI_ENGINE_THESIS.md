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
