# AIOS ↔ Council 편입 독트린

> **범위**: AIOS(myworld 커널 + hivemind/memoryOS/CapabilityOS/GenesisOS)가 Council을 **어떻게
> 취급하는가**. Council 자체의 아키텍처·기질·명령은 이 문서가 소유하지 않는다 →
> `~/workspaces/jaewon/council/AIOS_COUNCIL_ARCHITECTURE.md` (canonical, Claude가 메인 소유).
> 작성 2026-07-25 · 상태: 독트린(계약 수준). 구현 게이트는 §6.

---

## 0. 한 줄 결론

**Council은 AIOS 커널에 흡수되지 않는다. Council은 execution substrate + capability route이며,
AIOS는 그것을 *지배(govern)* 할 뿐이다.** 그리고 Council의 가장 큰 AIOS 가치는 "챗봇을 더 부르는
것"이 아니라 **검증된 이질 궤적을 학습 데이터로 흘려보내는 것**이다.

---

## 1. 경계 판정 (AIOS_SUBSTRATE_BOUNDARY 적용)

`AIOS_SUBSTRATE_BOUNDARY.md`의 5계층 순서를 Council에 그대로 적용한 결과:

| 계층 | Council의 어느 부분이 여기 속하나 | 소유 |
|---|---|---|
| **Kernel primitive** | 없음 — Council은 authority/receipt/rollback을 발명하지 않는다. 다만 **Council 호출 자체가 권한 게이트를 통과해야 하는 행위**다(외부 전송·ToS 노출·비용) | `myworld` 계약 |
| **Execution substrate** | `hub ask/panel/browse` 실행, headed 브라우저 데몬, async 잡 워커 | `hivemind` (provider-loop receipt) |
| **Capability route** | "이 문제에 어떤 기질이 맞나" — registry.yaml의 기질 카드, focal-diversity 선택 | `CapabilityOS` (capability card + fallback) |
| **Memory/knowledge route** | 근거·인용·prior art (perplexity-api), bus.db 스레드, capture vault | `memoryOS` + 인용 receipt |
| **Genesis challenge** | 프레임 자체가 불안정할 때의 이질 발산·레드팀 | `GenesisOS` (branch set) |

**따라서 Council은 단일 계층이 아니라 4개 계층에 걸친 기질 묶음이다.** 이 경우 boundary 문서의 규칙
그대로 — *"한 계층으로 조용히 뭉개지 말고 praxis envelope / smart contract로 각 역할을 명시하라."*

---

## 2. AIOS가 Council에 대해 가지는 권한 (authority)

Council 호출은 **외부-면(outward-facing) 행위**다. 따라서 커널 게이트를 통과한다.

| 행위 | 권한 요건 | receipt |
|---|---|---|
| `-api` / local / CLI 질의 | 자유 (내부, 저위험) | run receipt |
| **브라우저 챗봇 send** | ToS/계정 리스크 → 볼륨 상한 + 목적 명시 | provider-loop receipt (기질·지연·성공) |
| `browse net/eval` on 외부 사이트 | 사이트가 **founder 자격**으로 로그인됨 → 읽기는 자유, **쓰기/제출/결제는 founder 확인 필수** | 행위 receipt + 대상 URL |
| 프라이버시-게이트 데이터 동반 | **금지** — `_from_desktop/`, `dain/`, `minyoung/`, secrets, capture vault 원문 | — (차단) |

**불변**: privacy boundary는 Council 경유로 우회될 수 없다. 프롬프트에 넣는 순간 외부 전송이다.

---

## 3. Council이 AIOS에 실제로 기여하는 것 (그리고 기여하지 않는 것)

2026-07-17 적대 판정(`AIOS_COUNCIL_VERDICT_2026-07-17.md`)을 **정면으로 존중**해서 쓴다. 그 판정의
급소는 *"조립/라우팅은 대체로 cope, 프론티어가 커모디티화한다"* 였고, 이 문서는 그 반증을 피하지 않는다.

### 3.1 기여하지 **않는** 것 (과대주장 금지)

- ❌ **"이질 라우팅이 moat"** — 아니다. 라우팅은 OpenRouter/LiteLLM/vLLM Semantic Router가 이미
  커모디티화했고, 랩이 트래픽 우위로 캘리브레이션을 앞선다.
- ❌ **"패널 수렴 = 진리"** — 측정된 CEILING상 이질 패널은 **≈2 유효 독립표**(nominal의 24%).
  만장일치는 공유 환각일 수 있다. 수렴을 증거로 승격하는 순간 그 자체가 실패 모드다.
- ❌ **"챗봇을 더 많이 부르면 더 똑똑해진다"** — Tool Bloat / Curse of Compositionality. 컨텍스트
  포화와 산만 토큰면적만 늘린다.

### 3.2 기여하는 것 (durable 잔여)

1. **소버린/정책 라우팅** — privacy-gated, cost, local-exec, compliance 제약 하의 선택. 판정문이
   "durable 잔여"로 남긴 유일한 라우팅 가치. 일반 라우팅이 아니라 **제약 만족**이다.
2. **접근 자체(access)** — 구독 UI 전용 기능(Veo, Deep Research, NotebookLM, Artifacts)과
   per-request 서명 사이트, 그리고 **로그인된 임의 웹**(대회 포털·데이터 포털). 이건 라우팅이 아니라
   **능력의 유무**이고, 커모디티화 논증이 닿지 않는다.
3. **★학습 데이터원 (가장 큰 가치)** — 판정이 지시한 방향: *"frozen 조각을 조립하지 말고, 사회의
   검증된 경험을 학습으로 되돌려라."* Council의 이질 escalation은 그 자체로 목적이 아니라
   **검증된 궤적의 원천**이다.

---

## 4. ★핵심 편입: Council → 경험 증류 파이프라인

AIOS 재정의(**소버린 경험-증류기**)에서 Council이 차지하는 자리는 이것 하나다:

```
Council escalation (이질 기질 · 실제 문제)
        │
        ▼  ① 궤적 포획 — 질의 · 각 기질 답 · 최종 선택 · 근거
   bus.db + 결과 원장
        │
        ▼  ② 인과-ablation 게이트 — "그 자문이 실제로 결과를 바꿨나?"
   검증된 궤적만 통과 (수사 아님, 결과 기준)
        │
        ▼  ③ 로컬 약모델 LoRA-adapt (야간)
   로컬 모델이 자기가 지휘한 사회로부터 실제로 배운다
        │
        ▼  ④ 다음 라운드에 로컬이 더 자주 정답 → escalation 빈도 감소
   측정 가능한 성공 지표 = escalation 의존도 하락
```

**이 파이프라인이 Council을 "셸 스크립트"에서 벗어나게 하는 유일한 경로다.** 조립은 반증 가능하지만,
"escalation을 학습으로 되돌려 의존도를 낮춘다"는 반증 가능한 *진전*이다.

### 4.1 성공/실패 종료 조건 (설계 시점에 명시 — 실험 규율)

- **성공**: 동일 과제 분포에서 escalation 호출 빈도가 유의하게 하락하면서 결과 품질 비하락.
- **실패**: 빈도 불변이거나, 로컬 adapt가 품질을 떨어뜨림 → **학습 경로 기각**, Council은 접근 도구로만
  남기고 §3.2의 1·2만 주장한다 (no-launder: 그 축소를 정직하게 기록).
- **반증 대조군**(판정문의 실험 설계 계승): Full-AIOS(A) vs Naive-Linear(B) vs raw frontier(C).
  B/C가 더 적은 latency·zero doom-loop로 A를 매칭하면 아키텍처 반증.

---

## 5. 계약 표면 (AIOS가 Council을 부르는 방식)

AIOS는 Council 내부를 알 필요가 없다. **한 줄 CLI + 정규화 응답**이 계약 전부다.

```bash
python3 /home/user/workspaces/jaewon/council/hub.py ask <substrate> "Q"      # → Response JSON
python3 .../hub.py panel "Q" --set debias                                     # 이질 발산
python3 .../hub.py browse read|net|eval <url>                                 # 임의 웹 접근
python3 .../hub.py handoff "<goal>" --repo D [--accept "…"]                   # 격리 위임+검증+병합
```

**`handoff`가 AIOS에 특히 중요한 이유**: 이미 **격리(worktree) + 적대 verify + git-reversible 병합**을
갖춘 유일한 Council 서비스다. 즉 §4의 "검증된 궤적"이 실제로 생산되는 지점이며, `data/handoffs/<hid>/`
(packet · events.jsonl · patch.diff · verify.json)가 **인과-ablation 게이트(G2)의 입력 형식**이 된다.
hivemind provider-loop는 handoff를 bounded work로 감싸 run receipt만 붙이면 된다 — 재발명 금지.
```
Response{substrate, ok, text, transport, ms, error, url, image, files}
```

**MCP 게이트웨이를 만들지 않는다** — 등록·스코프 비용만 늘고 능력은 같다. (Council 문서 §6의
"의도적으로 안 짓는 것"과 일치.)

AIOS 측 매핑:
- `hivemind` provider-loop → Council 호출을 bounded work로 감싸고 run receipt 발행.
- `CapabilityOS` → registry.yaml 기질을 capability card로 노출 + fallback plan(= graceful degrade).
- `memoryOS` → 인용·근거를 evidence receipt로, 결정 궤적을 context pack으로.

---

## 6. 구현 게이트 (아직 GO 아님)

| 게이트 | 조건 | 상태 |
|---|---|---|
| G1 | Council 결과 원장(append-only) 존재 — 궤적 포획의 전제 | ❌ 미구현 (Council 로드맵 P1) |
| G2 | 인과-ablation 게이트가 "자문이 결과를 바꿨나"를 판정 | ❌ 미구현 |
| G3 | 야간 LoRA-adapt 파이프라인 + 고정 평가셋 | 부분 (distill/ 자산 존재) |
| G4 | escalation 빈도 지표 베이스라인 측정 | ❌ 미측정 |

**G1 없이는 §4가 서사일 뿐이다.** 따라서 다음 실제 작업은 Council 쪽 P1(결과 원장)이며, 그것이
AIOS 편입의 첫 벽돌이다. 이 문서는 그 벽돌이 놓이기 전에 방향을 고정해 두는 계약이다.

---

## 7. 불변 (이 문서가 바꿀 수 없는 것)

1. **프라이버시 경계 불가침** — Council 프롬프트/캡처 vault를 통한 우회 포함.
2. **원장 append-only** — 기각된 분기·실패한 자문도 지운다는 선택지는 없다.
3. **operator override 절대** — founder가 언제든 무효화·중지.
4. **no-launder 양방향** — Council 기여를 과대주장하지 않고, 동시에 진짜 능력(접근·소버린 제약
   만족)을 방어적 null로 축소하지도 않는다.
5. **판단은 위임되지 않는다** — Council은 발산·노동·접근을 제공하고, 선택·종합·검증은 main context.

---

## 참조

- Council canonical 아키텍처: `~/workspaces/jaewon/council/AIOS_COUNCIL_ARCHITECTURE.md`
- 실전 사용법 + 에스컬레이션 사다리: `~/workspaces/jaewon/council/AGENTS.md`
- L2 발산 원본(근거 인용): `~/workspaces/jaewon/council/COUNCIL_ROADMAP.md`
- 적대 판정(이 문서가 존중하는 반증): `docs/AIOS_COUNCIL_VERDICT_2026-07-17.md`
- 경계 규칙: `docs/AIOS_SUBSTRATE_BOUNDARY.md`
