# 척추 설계 — CLI를 엮지 않고 직접 부른다, 그리고 그 주장을 어떻게 재는가 (2026-08-18)

founder 3개 지시를 한 문서로 받는다:
*"점점 좋아지는 local llm·coder·api를 동적으로 엮어 claude code·codex를 뛰어넘는 agent system"*,
*"cli를 연결하는 것보다 이렇게 만드는 게 더 예측가능하고 controllable하지?"*,
*"현재는 CLI가 똑똑하니 Control Plane으로 쓰거나 동적 판단이 필요한 곳에 배선하고 나중엔 이마저도 치환 가능하게."*

## 1. "뛰어넘는다"를 정직하게 정의한다 — harness 대 harness

우리는 모델을 학습시키지 않는다. 그러므로 *"Claude Code를 뛰어넘는다"*가 정직하게 뜻할 수
있는 것은 하나뿐이다: **같은 모델을 물렸을 때 우리 harness가 더 높다.**

그라운딩(2026-08-18):

```
Terminal-Bench 2.1   Codex CLI 89.5 (GPT-5.6 Sol)   Claude Code 89.1 (Opus 5)
harness 기여폭       모델 고정 상태에서 10~15%p
                     LangChain Deep Agents Code: GPT-5.2-Codex 고정에 52.8 → 66.5 (+13.7%p)
2026-07 리포트       "Terminal-Bench measures the harness at least as much as the model"
```

⟹ **이 목표는 도달 가능하고 측정 가능하다.** 모델 경쟁이 아니라 harness 경쟁이고,
harness는 우리가 짓는 바로 그것이다. 지표: **모델을 고정한 Terminal-Bench 2.1 대비.**

## 2. CLI를 엮지 않는 이유 — 같은 세션에서 측정됨

| 방식 | 실측 |
|---|---|
| CLI/웹 패널 (codex·grok·chatgpt·gemini …) | **10/20 응답 (50% 실패)** |
| 직접 HTTP (ollama) | dead 0 · malformed 0, seed 재현 |

CLI가 돌려주는 것은 exit code와 stderr다. 직접 호출은 **seed·토큰수·지연·본문**을 돌려준다.
전자는 다시 돌려보고 기도하는 것이고 후자는 **재생**이다.

이 차이가 이 세션의 다른 실패와 같은 병이다 — M1 게이트가 죽은 이유는
*"비트를 가진 필드가 전부 실험 장부이고 진단은 하나도 없었다"*였다.
**CLI는 그 상태를 구조적으로 만든다.**

## 3. 그래도 CLI가 남는 자리 — 그리고 치환 가능하게 만드는 법

정직하게, CLI가 유일한 경로인 곳이 있다: 구독 UI 전용(Veo·Deep Research·NotebookLM),
요청마다 서명되는 anti-bot 토큰(grok/chatgpt web) — **API 재생이 존재하지 않는다.**

그래서 `scripts/aios_substrate.py`의 규칙은 이렇다:

```
observable=True   직접 호출. 영수증에 seed·토큰·지연·본문.
observable=False  CLI 어댑터. 영수증에 UNOBSERVABLE이 찍힌다.
                  + substitute 필드에 "무엇이 이걸 치환하는가"를 반드시 명시
```

**치환 가능성은 약속이 아니라 필드다.** 모든 CLI 항목이 자기를 대체할 직접 API를 이름으로
지목하게 강제하면, 나중에 치환하는 일이 "재설계"가 아니라 "필드 하나 갈아끼우기"가 된다.
지금 등록된 것: `chatgpt-web → openai api`, `grok-web → xai api`,
`codex-cli → openai responses api`.

`codex-cli`의 note를 그대로 적어둔다 — *"자기 agent loop를 들고 온다; 그게 우리가 대체하려는
바로 그것이다."* CLI를 control plane으로 쓰는 동안 우리는 **남의 harness를 빌려 쓰는 것**이고,
1절의 목표는 정확히 그걸 우리 것으로 바꾸는 일이다.

## 4. 동적 라우팅은 값이 있다고 가정하지 않는다

founder의 표현은 *"동적으로 엮어"*지만, **우리 자신의 측정이 반대 방향을 가리킨 적이 있다** —
A1/MCF-0에서 **얼어붙은 라우터가 적응형 지속상태를 이겼다**(regret 0.057 vs 0.119).

그래서 `aios_substrate.py`에 적응형 라우터는 **일부러 없다.** 있는 것은 정적 표뿐이고,
그것이 적응형이 이겨야 할 baseline이다. M2 사전등록의 arm B와 같은 구조다.

```
B0  단일 최고 모델
B1  정적 능력표 (task_class → model)     ← 지금 있는 것
R   적응형/밴딧 라우터                    ← B1을 이겨야 존재 정당
```

2026 라우팅 지형도 같은 말을 한다: bandit-feedback 온라인 라우터(BaRP·PILOT)가 정적 분류기를
대체하는 중이고 LLMRouterBench(400K instance·33 model·10 baseline)가 나왔지만,
**우리 과제 분포에서 B1을 이긴다는 증거는 우리가 재야 한다.** 남의 벤치마크는 우리 잔차가 아니다.

## 5. 로컬 스택이 낡았다 (그라운딩 결과)

```
지금 돌리는 것   qwen3-coder-next        SWE-bench Verified 70.6
있는 하드웨어    RTX 5090 × 2 = 64GB VRAM
후보             qwen3.6-27b     77.2   22GB — 한 장에 들어감
                 glm-5.2         81.0   Terminal-Bench, 오픈웨이트 agentic 최강
                 deepseek-v4-pro-max 80.6  오픈웨이트 SWE-bench V 최고
```

**+6.6pp를 하드웨어가 남는 채로 놓치고 있었다.** 레지스트리에 `candidate=True`로 올려두고,
설치 전에는 호출하면 실패를 반환한다 — 없는 것을 있는 척하지 않는다.

## 6. 레거시 — 그래프가 답했고, 첫 답은 틀렸다

`scripts/aios_legacy_triage.py`는 **네 신호가 전부 일치할 때만** 후보로 올린다
(그래프 고아 · git 정체 · harness 미언급 · 테스트 미참조). 고아 하나로는 판정하지 않는다 —
아무도 import하지 않는 진입점은 그래프에서 고아이고 그건 지우면 안 되는 것이기 때문이다.

**첫 실행이 감사 기록 574건을 삭제 후보로 올렸다.** `hivemind/.runs/`의 `.md`가 문서로
분류됐기 때문이다. append-only 불변식이 보호하는 대상이고, **감사 추적을 지우자고 제안하는
도구는 도구가 없느니만 못하다.** 기록 디렉터리를 배제하고 재실행:

```
후보 695 → 24
그중 16건이 우리 코드가 아님 — gemini/ 와 gemini-cli/ (같은 upstream 클론 둘)
```

검증: 두 디렉터리는 각 132MB·2,862파일이고 차이는 우리가 넣은 skill 하나뿐
(`gemini-cli/.gemini/skills/aios-operator`). ⟹ **`gemini/`는 순수 중복이고 재클론 가능하다.**
나머지 8건은 memoryOS·uri의 실제 사장된 스크립트·문서.

행동은 `rm`이 아니라 `git mv`다(히스토리 보존·되돌림 가능). `--emit-archive-script`는
스크립트를 **쓰기만 하고 실행하지 않는다.**

---
*그라운딩: WebSearch 2026-08-18(SWE-bench Verified·Terminal-Bench 2.1 리더보드),
`hub ask perplexity-api`(harness 고정-모델 비교). 실측: `.aios/deep_panel.jsonl`(10/20),
`.aios/copyness/`(직접호출 dead 0), `scripts/aios_substrate.py --report`.
관련: `docs/AIOS_KNOWLEDGE_GRAPH_2026-08-18.md`, `docs/AIOS_M2_MEMORY_AS_COMPUTATION_PREREG_2026-08-16.md`(같은 게이트 구조).*
