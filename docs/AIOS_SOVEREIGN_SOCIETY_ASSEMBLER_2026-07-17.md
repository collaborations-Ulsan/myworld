# AIOS = 소버린 사회-조립자 (crystallization, 2026-07-17)

**Authority**: founder 2026-07-17 — (1) "AIOS 스스로 독립하자. CLI 옆에 붙는 구조 말고, AIOS 안에 CLI
power base를 두고 AIOS 독자 시스템이 CLI를 잘 활용하게." (2) "frozen 너머 방법·논문이 쏟아진다.
새로 짓기보다 가져와 얼마나 잘 붙이느냐, 사회를 만드느냐, 흩어진 것을 모아 하나의 AGI로 만드느냐."

이 두 지시가 AIOS의 정체를 확정한다. 이 세션의 세 negative(DriftBench STOP · S+1 해악 · S+1.1
harm-fixed)가 가르친 규율과 정합한다.

## 한 줄 정체

> **AIOS = 소버린(독립) 사회-조립자: local/NIM을 base로 독자 실행하며 CLI·모델·프론티어 방법을
> power-tool·시민으로 부려, 흩어진 프론티어 조각을 *인과-검증된 하나의 사회*로 조립해 AGI를 향하는
> 운영 층.** 발명이 아니라 조립. 감싸이는 게 아니라 감싸는 것.

## Directive 1 — CLI 관계 역전 (독립)

- **전(sidecar)**: AIOS가 CLI 옆에 붙음. CLI=host, AIOS=plugin. 입력기를 CLI로 빌림.
- **후(sovereign)**: AIOS=base. CLI(claude/codex/gemini)=AIOS가 부리는 **power-tool**. 기본은
  local(qwen3-coder:30b)/NIM, 어려운/실패한 스텝만 프론티어 CLI로 **escalate**.
- **실측(2026-07-17)**: 대부분 이미 M5가 지음 — `aios_head.py`가 독립 CLI 엔트리, claude/codex/gemini/
  ollama 전부 adapter, capability 라우팅+auto_local_nim 존재. **완성분**: sovereign escalation 라우팅
  (local-first→CLI-power-tool) + `aios` 엔트리 + 독립성 증명 (이번 빌드; 진행 중).
- **독립성 시험**: `aios <goal>`이 Claude Code에 호스팅되지 않고, local을 default로 스탠드얼론 완주하며
  필요 시 CLI를 subprocess 도구로 호출 — 그 반대가 아님. provenance로 어느 기질이 각 스텝을 처리했는지 감사.

## Directive 2 — 조립이 방법론이다 (사회)

- **핵심 인식**: frozen 너머 방법이 쏟아진다(이번 세션 지식원장이 그 지도 — 833 노드/47 모순). 우리가
  이길 방법은 labs를 **out-invent**가 아니라 **out-assemble** — 흩어진 조각을 하나의 사회로 잘 붙이기.
- **AGI = 사회**: 단일 모델도 단일 loop도 아닌, 조립된 시민(모델·CLI·organ·방법)의 **사회**. Sutton의
  "경험에서 배우는 유기체", 창업자의 "아기처럼·gene-pool·speciation", MAE/MOAT/AC-DC의 전문가 사회가
  같은 방향 — 다양한 시민이 인과-검증된 관계로 협력.
- **지도·조립자·시민**: 지식원장(OntologyOS)=조각 지도. AIOS=조립자. CLI/모델/방법/organ=시민.
  레이더 organ=새 조각을 사회에 연속 유입.
- **성공 지표 재정의**: novelty가 아니라 **통합 품질 + 사회 coherence**. "얼마나 잘 붙였나"가 통화.

## 세 negative가 못박은 조립 규율 (naive gluing 금지)

1. **DriftBench STOP**: 약한 내부 검증자로 감싸면 checklist에 진다 → 조립은 **강한 외부 검증**으로.
2. **S+1 해악**: 인과-미검증 축적은 오염시킨다 → 조립은 **인과-검증 통합**(항목이 실제 기여할 때만).
3. **S+1.1 harm-fixed**: 인과-게이트가 가짜 조립을 거부 → 그러나 복리엔 **올바른 기질**(headroom+전이구조)도
   필요. → **조립 ≠ 붙이기. 조립 = 인과-검증된 시민을 올바른 기질 위에서 협력시키기.**

## 실행 함의 (이어서)

- **독립 완성**(directive 1): sovereign escalation 라우팅 + `aios` 엔트리 + 독립 증명 (진행 중).
- **조립 방법 gather**(directive 2·3): 지식원장에 나머지 방법 유입 중 — D5(추론·검증·RL),
  D7(멀티에이전트 **사회**·조립/composition: model-merge·MoA·routing·specialist-coevolution).
  특히 "사회를 만드는" 방법(어떻게 조각을 하나로)이 D7의 핵심.
- **다음 조립 실험**: society/assembly 방법 중 디바이스-실행가능 top을 흡수해, 인과-게이트(S+1.1)를
  단일-태스크가 아니라 **시민 사회(이종 모델+organ) 조립**에 적용 — "assembled society > single strong
  model"이 언제 성립하는지(D7이 답할 모순: multi-agent-helps vs -hurts)를 keystone 규율로 판정.

## 정직 스코프 (no-launder)

- **주장**: AIOS의 정체 = 소버린 사회-조립자. 대부분의 독립 기계는 이미 있고(M5), 이 세션은 그걸
  **완성+포지셔닝 확정**한다. 조립-우선은 세 negative가 준 인과-검증 규율 위에서만 정직하다.
- **주장 아님**: "조립하면 AGI 완성" 아님 — 조립된 사회가 단일 강모델을 **측정가능하게** 이기는
  기질·방법을 EARN해야 한다(D7 모순 + keystone). naive 사회는 단일 모델에 지기도 한다(MedAgentBoard).
  flat이면 그대로 공개.
