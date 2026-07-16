# AIOS 재정의 + AGI 마스터플랜 (2026-07-10)

**Authority**: founder 재원, 2026-07-10 chat directive — "AIOS 이제 진짜 완성하자. NIM, Codex,
Antigravity 활용해서 기획부터 다시하고, AIOS가 뭔지부터 재정의 해. … AGI(AIOS)를 만들어보자."
+ "AGI 완성까지 멈추지말고 디자인" + "실제 실행기는 Subagent로, 최신 모델들과 함께 기획 및 감독."

**접지 (freshness gate 통과)** — 이 문서는 기억이 아니라 아래 소스에서 삼각측량됨:
- 내부: 전 로컬 프로젝트 인벤토리 (subagent, 2026-07-10) + AIOS 현 상태 증류 (subagent) +
  `AIOS_AGI_ENGINE_THESIS.md` · `AIOS_AGI_CERTIFICATION_KEYSTONE.md` · ASC-0281
- 외부: 2026-07-10 웹 리서치 브리프 (subagent; METR·OSWorld 2.0·GAIA2·Epoch·MCP/A2A/ACP·OpenClaw·
  Fable 5 수출통제 사건, URL 인라인 인용본은 세션 기록)
- 이종 기질 패널: Gemini(Antigravity `agy`, 웹 그라운딩) · qwen3.5-397b(NIM) · nemotron-3-ultra-550b(NIM) ·
  Codex(gpt-5.5, adversarial) — 서로 다른 prior의 독립 수렴
- AIOS 자체 기관: `aios_retrieve` (trace rtrace_d9d2469f98e200d8) · `aios_challenge` (Genesis 비판 반영)

---

## 0. 한 줄 재정의

> **AIOS는 개인-소버린 Epistemic Runtime이다: frozen frontier 모델들을 subagent 실행기로 부리면서,
> 행동을 바꾸는 메모리·인식론 게이트·장기지평 지속성을 커널 불변량으로 강제해,
> "모델 혼자보다 장기지평에서 측정가능하게 더 신뢰가능한" 에이전트를 만드는 로컬-퍼스트 커널.**

세 기능이 본질 (이 셋이 없으면 AIOS가 아님):

1. **행동을 바꾸는 메모리** (지속학습 스캐폴드) — append-only 원장 → sleep-time consolidation →
   다음 턴 주입. 저장이 아니라 **행동 변화**가 판정 기준. (2026-07 필드 공인 AGI 병목 = continual
   learning; 저장/검색은 커모디티 — LoCoMo 포화, files+grep이 전문 메모리 라이브러리를 이김.)
2. **Epistemic Gate** (인식론 층 = 창업자 연구 기관의 배선) — APEX(answerability: 답할 수 있는가),
   IRIS(identifiability + typed abstention: CLAIM/ABSTAIN/MISSPECIFIED/NEXT_INTERVENTION),
   DescentNet(모순의 국소화: same-vocab cyclic 유일 탐지기), 값싼 H⁰ 필터(실전 오염가드).
   **사후 진단이 아니라 매 턴 blocking middleware.** 게이트를 통과 못한 턴은 실행 전에 거부된다.
3. **장기지평 지속성** — event-sourced goal state(크래시 후 재개), drift 감지→복구, named exits,
   provenance 체인. 목표: 단기 85% vs 장기 20.6%(OSWorld 2.0)의 절벽을 시스템 층에서 메우기.

**실행 형태 (founder 지시 반영)**: head(frontier 모델)는 기획·감독만. 실행은 전부 subagent
(Claude/Codex/Gemini/로컬 qwen). AIOS 커널은 head도 subagent도 아닌 **그 사이의 게이트와 기억**이다.

무엇이 아닌가 (경계, no-launder):
- 모델이 아니다 (world model·pretraining·weight-level 지속학습은 labs의 게임).
- 오케스트레이션 프레임워크가 아니다 (LangGraph 1.0·MCP·A2A·ACP·Skills = 커모디티. 위에 올라탄다).
- 거버넌스 문서 시스템이 아니다 (contracts/ledger는 운영 증거이지 제품이 아님 — 2026-05-20 override 유지).
- OpenClaw류 "개인 비서"가 아니다 (채널·편의성 경쟁 회피; 신뢰가능 장기지평 유기체로 차별화).

## 1. 왜 이 정의인가 — 3중 삼각측량

**(a) 외부 세계 (2026-07-10 리서치)**
- 롱-호라이즌 절벽이 정량화됨: OSWorld 2.0에서 최고 시스템 20.6% (단기형 85%와 대비), GAIA2 ~42%.
  **이 층은 주인이 없다** — labs는 model-centric, OpenClaw는 채널-centric, LangChain은 framework-centric.
- 지속학습이 AGI 병목으로 공인 (AI Frontiers·a16z·해마-메모리 position papers). 메모리 저장은 커모디티,
  **행동을 바꾸는 메모리**(consolidation·망각·환각메모리 제어)가 열린 프런티어.
- 프로토콜 전쟁 종료 (MCP+A2A Linux Foundation, ACP 레지스트리, Agent Skills 표준). 자체 프로토콜 = 음의 가치.
- provider 리스크 실증: Fable 5/Mythos 5가 수출통제로 19일 정지 (2026-06-12~07-01). 소버린티는
  이념이 아니라 실증된 필요.

**(b) 이종 기질 패널 (독립 수렴)**
- nemotron-550b: 빠진 층 = "Epistemic Runtime — 추론 자체를 감사·검증·지속개선 가능하게".
  litmus: AIOS 제거 → 성과가 측정가능하게 나빠져야 함.
- qwen3.5-397b: "Local-First Epistemic Kernel — 두뇌(모델)가 아니라 신경계+면역계.
  법정을 지어라, 변호사가 아니라." keystone = Drift-to-Recovery Ratio.
- Gemini(웹 그라운딩): sleep-wake consolidation + 실행가능 검증(비-vibes) + event-sourcing.
  keystone = Mutating Environment Debugging (약한 로컬모델+AIOS가 raw frontier를 후반 태스크에서 역전).
- Codex(gpt-5.5, adversarial): [수렴 공격 결과 — §5 keystone 실험 설계에 반영]

**(c) 내부 증거 (이미 EARN한 것)**
- **ASC-0281 composition positive**: 합성 society 기질에서 typed epistemic layer
  (DescentNet→APEX→EV-intervention→Akashic)가 equal-information majority baseline을 5/5 게이트 × 3 seeds로
  이김 — "차이는 typed layer이지 정보접근이 아니다". 게이트 층이 값을 더한다는 최초의 합성 증명.
- **Earned negatives 2건** (경계 설정): DescentNet 단독은 예측/전이/오염저항에서 값싼 H⁰ 필터에 짐;
  certs는 solve-count가 아니라 precision을 산다. → keystone 지표는 solve-count가 아니라
  **신뢰성·정밀도·의사결정 비용**이어야 한다.
- 커널은 이미 L6 (head→turn_loop→tools→packet→run_log→work, 6-step spine 완비). 빠진 것은
  용량이 아니라 **게이트 배선과 실데이터 증명**.

## 2. 명시적 가정 + 부정 테스트 (Genesis 비판 반영)

| # | 가정 | 부정하면? | 판정 기준 |
|---|---|---|---|
| A1 | 게이트 층이 실데이터 장기지평에서도 값을 더한다 (합성에서처럼) | 게이트가 오버헤드만 더하고 신뢰성 불변 → AIOS는 거버넌스 시어터 | §5 keystone 실험이 유일 판정자 |
| A2 | 행동을 바꾸는 메모리는 frozen 모델 위 스캐폴드로 충분히 구현 가능 | consolidation이 "noisy prompt folklore"로 그침 (Codex 2026-07-04 지적) | 태스크 20-50 구간의 성공률 기울기 |
| A3 | 인큐번트가 이 층을 흡수하기 전에 소버린-중립 버전에 수요가 있다 | Frontier/Antigravity/Windows Agent OS가 다 흡수 | Fable 5 정지 사건 + 규제 요구가 반증의 반증 |
| A4 | 창업자 연구 기관(APEX/IRIS/DescentNet)이 게이트의 실질 엔진이 된다 | 일반 LLM-judge와 차이 없음 → 연구는 페이퍼로만 가치 | ablation: 기관 게이트 vs LLM-judge 게이트 |

원거리 유추 (single-frame 탈출): AIOS는 **면역계**다 — 지능(두뇌)을 만들지 않고, 유기체가 죽지 않게
한다. 면역계 없는 두뇌는 하루를 못 버틴다; AGI는 두뇌가 아니라 **살아남는 유기체**의 속성이다.
시간지평: 1주(M1 게이트 배선) / 1달(keystone 판정) / 1년(판정이 양성이면: 표준 위 배포·연합; 음성이면:
정직한 negative 공개 + 메모리-레이어로 스코프 축소).

## 3. 자산 맵 → 부품 배치 (인벤토리 결과)

| AGI 부품 | 자산 (레포) | 상태 | 마스터플랜 내 역할 |
|---|---|---|---|
| Answerability | APEX (`quantum/`, `apex-certify-artifacts/`) | 완성·sealed | Gate 조건 1: "답할 수 있는 질문인가" |
| Identifiability/abstention | IRIS (`quantum/iris/`, 55/55 tests) | 완성·arXiv-ready | Gate의 typed verdict 문법 (CLAIM/ABSTAIN/…) |
| Integrity/모순 | DescentNet (`descentnet/`) + H⁰ filters | keystone 3도메인 검증·단독 negative 확정 | Gate 조건 2: 모순 국소화 (niche) + H⁰ 상시 가드 |
| Legibility | 포트폴리오 19편 (`portfolio/data/papers.json`) | 기계가독·정직성 감사됨 | 지식 시드 + 방법론 원장 |
| 실행기 | AIOS 커널 (`myworld/scripts/aios_*`) + hivemind + dipeen | L6 | head-기획/subagent-실행 하네스 |
| 공유 원장 | AkashicRecord (live worker, ~1,400 entries) | 프로덕션 | cross-agent 경험 커먼즈 (Merkle 검증) |
| 경험→가중치 | prizehunter sleep LoRA (Qwen3-8B nightly) | 베타 | M3 consolidation의 weight-level 브릿지 |
| 실전 아레나 | dacon/prizehunter 캠페인 | 활성 | keystone의 실데이터 공급원 |
| 발산 | GenesisOS | 활성 (advisory) | 가정-부정·프레임 탈출 (§2에 실사용) |
| — | GoEN | **휴면·negative** | 부품 아님 — 페이퍼 자산으로만 유지 (kill list) |

## 4. 마스터플랜 (head 기획·감독, subagent 실행)

**M1 — Epistemic Gate v1 배선 (1~2주)** ← 최우선
- `aios_turn_loop`에 blocking gate 삽입: 매 턴 proposal → IRIS-typed verdict
  (CLAIM/ABSTAIN/MISSPECIFIED/NEXT_INTERVENTION) + APEX answerability 판정 + H⁰ 일관성 필터 →
  통과 못하면 "Turn Rejected: <사유>. Rewrite." 를 모델에 반환.
- 기반: M1a Certificate Interface Spec (certs-as-guards, 이미 커밋됨) + `aios_tools` 레지스트리.
- ablation 스위치 필수: gate=off / gate=LLM-judge / gate=organs — A4 판정용.
- 실행: subagent (executor). 감독: head. 검증: 비-Claude 기질 1개 이상 리뷰 (multi-substrate-review).

**M2 — Long-horizon Keystone 실험 = `AIOS-DriftBench-mini` (2~3주, M1 뒤)** ← 유일한 "완성" 판정자
- 설계 확정판은 §5 (Codex adversarial 설계 채택: 24 인스턴스, 5 arms — `weak+checklist` 대조군 포함,
  functional grader, pre-registered win/stop conditions, leakage 트랩 전체).
- ASC-0282 (real-dispatch shadow-mode) 겸용 — dacon 캠페인이 실데이터 공급.
- **named exits**: (i) win condition 충족 → 재정의 EARN, M4 배포로. (ii) weak+AIOS가 weak+checklist를
  못 이김 → epistemic runtime 테제 kill 또는 "workflow hygiene"으로 강등, 정직 공개 + 메모리-레이어로
  스코프 축소.

**M3 — Sleep Consolidation 실측 (M2와 병렬 가능)**
- dual RTX 5090: 로컬 모델(qwen3-coder:30b 또는 최신 — 선택 전 HF/`nv models` 재확인)이
  원장 episodic 기록 → 규칙 추출 → 다음 세션 주입. 이미 있는 dream cycle을 "주입이 행동을 바꾸는가"
  측정으로 승격 (absorption-probe 재사용). prizehunter nightly LoRA와 연결.
- **경고 (ProEvolve, §5.5)**: 정적 메모리는 변이 환경에서 성과를 *해친다* — consolidation은 반드시
  staleness 감지(DriftBench식 contract 검증 + H⁰ 가드 + draft-first 리뷰)와 결합. "많이 기억"이 아니라
  "낡은 기억을 스스로 의심"이 차별점 (Decocted Experience: 교훈 증류 > 원시 경험, 메모리 크기 비단조).

**M4 — 표준 위 배포 (M2 양성 시)**
- MCP server(이미 있음) + ACP agent + Agent Skills 호환 아티팩트로 노출. 자체 프로토콜 금지.
- Akashic 커먼즈는 k-anonymity + Merkle 검증 유지. OpenClaw 채널과 경쟁하지 않고 그 아래 substrate로.

**M5 — Agent-native 실행기: provider-사망 내성 (founder directive 2026-07-10 추가)**
- 지시 원문 취지: "지금은 CLI 능력을 빌려 쓰지만, NIM API + 로컬 LLM의 능력을 최대로 쓰는
  agent-native agent를 만들어야. tool도 찾아서 built-in. 처음부터 짓지 말고 잘 만든 오픈소스에서
  재구성해 AIOS로 편입. codex가 터졌을 때, claude가 터졌을 때 어떻게 할 것인가. Sakana처럼 작은
  모델들을 잘 써서 그 이상의 지능을. 아이디어=web chat들(Claude/Codex/Grok), CLI가 작업 분해,
  실제 작업은 로컬 LLM에서. 파인튜닝된 모델들이 디바이스·앱 역할에 점점 built-in되고 학습하고
  전문가가 되는 세상."
- 구성 (흡수 우선, 자체 제작 최소):
  1. **OSS 런타임 흡수**: 2026-07 기준 최적 후보 조사 후 (OpenHands/Goose/smolagents/OpenClaw/
     qwen-agent/AB-MCTS·TreeQuest 등) 에이전트 루프·툴 레지스트리·샌드박스를 AIOS 커널
     (aios_head/turn_loop/tools)에 융합. star-radar 흡수 기관의 승격.
  2. **툴 built-in**: MCP registry (~10k servers) + Agent Skills 표준 (skills.sh 600k)을 로컬
     런타임의 툴 소스로 — 자체 툴 제작은 게이트·메모리 등 AIOS 고유물만.
  3. **다중 소형모델 오케스트레이션**: Sakana AB-MCTS/TreeQuest 노선 — NIM 무료 대형 + 로컬
     qwen3-coder-30b급 조합이 단일 frontier를 넘는 구간을 keystone(M2)의 weak+AIOS arm과 통합.
  4. **점진적 전문가화**: 역할별 QLoRA 파인튜닝 (parse 신뢰성·라우팅·도메인 전문가 —
     project_aios_finetune_thesis 노선, prizehunter nightly LoRA 재사용). "학습 안 된 head가
     제 역할 못한다"는 founder 관찰의 구조적 해답.
- **provider-사망 시나리오가 설계 시험**: Claude/Codex CLI 전부 죽어도 AIOS가 (성능은 낮아도)
  동일 인터페이스로 계속 동작해야 함. Fable 5 수출통제 19일 정지(§접지)가 실증 근거.
- 분업 구조: 아이디어·기획 = web chat provider들 (수동/반자동) → head(CLI 혹은 native)가 작업
  분해·감독 → 실행 = 로컬 LLM subagent + NIM escalation → 검증 = epistemic gate (M1).

**재료 선언 (founder, 2026-07-10)**: Dipeen, Dipeen_v2, memoryOS, GenesisOS, Hivemind,
CapabilityOS, DescentNet, Quantum(APEX/IRIS), Universe, GoEN — **이 모든 것이 AIOS를 위한
재료였다.** 각 재료의 배치는 §3 자산 맵.

**Kill list (earned negatives + override 존중)**
- 새 거버넌스 문서/contract 성장 (freeze 유지; M2 기록용 최소 계약만).
- GoEN 기관화 시도 (페이퍼 자산으로만; ASC-0280은 supersede 방향 유지).
- H¹ 오염가드 ship (이미 shelf 결정 — H⁰가 지배).
- cherry-test 중복 스택 (de-dup).
- "AGI 전체 엔진" 무스코프 주장 (레이어 스코프 주장만; §0의 경계 유지).

## 5. Codex adversarial 반영 (수렴 공격 결과, gpt-5.5 xhigh 2026-07-10)

Codex의 유효 타격 (모두 수용):

1. **"Epistemic runtime은 drift 하에서 행동을 인과적으로 바꾸지 않으면 거버넌스 시어터가 맞다."**
   실재 조건: 최종 행동 전에 (i) 새 증거 도착 후 stale action을 차단, (ii) source-of-truth 그래프 유지,
   (iii) belief↔trace↔환경 모순 감지, (iv) 복구 강제(재확인/질문/롤백/재계획), (v) 동일 정보·동일
   예산에서 결과 개선. **lift가 더 많은 호출·더 긴 시간·더 좋은 문구·사후 영수증에서 오면 시어터.**
2. **`weak+checklist` 대조군 필수** — runtime과 ceremony(체크리스트 종이)를 분리하는 결정적 arm.
   내 초안의 3-arm 설계는 이걸 놓쳤다 → M2를 5-arm으로 수정 (아래 반영).
3. **"같은 웹을 읽은 모델들의 수렴은 독립 확증이 아니다"** — §1(b)의 패널 수렴은 가설 생성용
   증거이지 판정 증거가 아님. 판정자는 오직 M2 실험. (이 문서의 인식론적 지위를 이렇게 강등함.)
4. **Kill 추가**: "AGI certification" 브랜딩은 장기지평 신뢰성을 예측/개선하기 전까지 금지;
   행동을 안 바꾸는 receipt-only 모듈 전부; 합성 society 승리를 중심 증거로 쓰는 것 (substrate
   evidence일 뿐). — §4 kill list에 병합.
5. **Stop condition (pre-registered)**: `weak+AIOS`가 동일 예산에서 `weak+checklist`를 drift-recovery로
   못 이기면 → epistemic runtime 테제를 kill하거나 "workflow hygiene"으로 강등. 이것이 M2의 named exit.

**M2 실험 설계 확정판 — `AIOS-DriftBench-mini`** (Codex 설계 채택, pre-register 후 변경 금지):
- 8 태스크 템플릿 × 3 seeds = 24 인스턴스; 6 mutating/hidden-state + 2 static 컨트롤;
  로컬 결정론적 환경(파일/inbox 픽스처/브라우저 페이지/레포/스프레드시트/로그); 히든 functional grader
  + partial checkpoint + 전체 trace 캡처; 런당 45-60분 또는 150-250 actions 캡.
- Arms: `strong-raw` / `weak-raw` / `weak+checklist` / `weak+AIOS` / (optional `strong+AIOS` ceiling).
- Primary: functional grader 이진 성공. Secondary: checkpoint 점수, drift-to-recovery steps,
  stale-action rate, unsupported final-claim rate, verification-before-submit rate, 비용·토큰·시간.
- Win condition(사전 등록): weak+AIOS가 weak+checklist를 paired 17/24 이상; mutating에서 strong-raw를
  이기거나 격차 대부분을 더 낮은 비용으로 해소; static 컨트롤에서 가짜 lift 없음; trace 감사로
  "runtime이 복구를 유발"함을 확인 (narration이 아니라).
  **[정정 2026-07-11: 위 17/24는 초안 수치 — static 분모 혼입 모순으로 교정됨. 정본 기준은
  `docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md` v1.1 (mutating-only ≥13/18 + exact McNemar).
  이중 하니스 화해: `docs/AIOS_DRIFTBENCH_RECONCILIATION_2026-07-11.md`.]**
- Leakage 트랩: 모델 버전·프롬프트 동결, runtime 호출도 예산에 계상, human rescue 금지,
  grader 파일 은닉, harness 동결 후 이름/값/스키마 랜덤화, functional grader 우선(LLM judge는
  bounded secondary만), raw baseline에 competent prompt(허수아비 금지).

## 5.5 선행연구 심층 → novelty 확정 (2026-07-10 웹, 전 인용 세션 기록)

**이미 출판됨 (재주장 금지, 인용할 것)**:
- harness>model **순위 역전**: Harness-Bench (arXiv 2605.27922) — 같은 모델에서 harness 교체로 최대
  23.8pt, qwen3.6-plus+QwenPaw 76.5 > qwen3.6-max+Hermes 70.2. 단 단·중기 샌드박스, 인접 티어.
- same-model 메모리 이득: ReasoningBank (2509.25140, WebArena 46.7→56.3%), AWM (+51% rel).
- 멀티모델 오케스트레이션 > 단일 강모델: AB-MCTS/TreeQuest (ARC-AGI-2 27.5-30% vs 23%).
- 변이 환경 벤치 기계: **ProEvolve** (2603.05910 — 핵심 발견: **정적 메모리 전략은 구조적 변이에서
  성과를 해친다**), **DriftBench** (2605.10990 — 8 drift 유형, 880쌍, contract 추출로 false alarm 0/599,
  1-round repair 10%→78%), ToolQA-D, SWE-Chain, Gaia2.
- 안전-타입 실행 게이트: KAIJU, OSGuard. consolidation→downstream 이득: Auto-Dreamer (2605.20616).

**진짜 미점유 (keystone은 이 conjunction)**:
1. **weak-LOCAL-model + epistemic runtime vs strong-raw-frontier를 롱-호라이즌(OSWorld-2.0/Gaia2급)
   변이 태스크에서** — head-to-head 출판 없음.
2. **calibrated typed verdict (CLAIM/ABSTAIN/ASK) 턴 게이트** + risk-coverage 곡선을 end-task 성공에
   연결 — "agentic UQ 벤치마크는 성숙 형태로 존재하지 않는다"가 문헌에 명시된 공백. IRIS 문법이
   정확히 이 자리다.
3. **변이에서 살아남는 메모리** — ProEvolve가 "정적 메모리는 해악"을 보였으므로, 자기 메모리의
   staleness를 감지(DriftBench식 contract + abstention)하고도 순이득을 내는 runtime은 무주공산.
   AIOS의 draft-first·review·H⁰ 가드가 정확히 이 지점의 기제다.

**M2 설계 수정 (Codex 설계 ∧ 선행연구 권고의 종합)**:
- 벤치는 **빌드보다 임대 우선**: DriftBench 880쌍 + ProEvolve식 mutation 기계를 substrate로; 로컬
  재현 불가 시에만 Codex의 DriftBench-mini를 DriftBench의 8 drift 유형으로 시드해 축소 구축.
- **2×2 + interaction term이 주장의 본체**: {weak local(qwen3-coder-30B급) vs frontier} ×
  {bare vs epistemic runtime}, 변이 태스크 ~50개, 3 seeds. 여기에 Codex의 `weak+checklist` arm과
  **`weak+memory`(ReasoningBank/AWM식) arm을 추가** — bare-vs-scaffold 델타만으론 더 이상 novel하지
  않고, ProEvolve 예측상 memory arm은 변이에서 무너진다 → 그걸 이기는 게 차별점.
- **가장 날카로운 미점유 결과를 정조준**: "calibration-gated turns가 drift 하 wrong-action을 X% 감축
  (커버리지 손실 Y%), 그로써 30B 로컬 모델이 raw frontier의 완주율에 도달" — 명시적 비용모델
  (wrong-action ≫ ask/abstain) + risk-coverage 곡선 + end-task 성공으로 채점.

## 6. AGI에 대한 정직한 스코프 선언 (no-launder 양방향)

- **주장하는 것**: AIOS는 AGI의 **신뢰성·기억·검증 레이어** — 필드가 병목으로 공인한 바로 그 층 —
  의 소버린-중립 구현이며, keystone(M2)을 EARN하면 "시스템 > 내부 모델"을 측정으로 입증한 최초급
  로컬 시스템이 된다.
- **주장하지 않는 것**: weight-level 지속학습·world model·추론 능력 자체. AGI "완성"은 이 레이어
  하나로 오지 않는다 — 단, 이 레이어 없이는 어떤 frontier 모델도 유기체가 되지 못한다.
- founder 비전과의 정합: "결국 남는 것은 Claude CLI도 Codex CLI도 아닌 AIOS" (aios_retrieve,
  rtrace_d9d2469f98e200d8) — 모델은 교체가능한 CPU, AIOS는 지속하는 유기체의 신경계+면역계+기억.

---

## 7. Keystone verdict (2026-07-17) — STOP, 정직하게. pivot은 검증됨.

DriftBench Stage-1 첫 실행(전수 120행, `db68d40`; 결과 `AIOS_DRIFTBENCH_STAGE1_RESULTS_2026-07-17.md`):
- **Bar A (재정의 유일 판정자): STOP.** weak+AIOS가 weak+checklist에 mutating 1/18 승 (≥13/18 필요),
  McNemar p=0.999. Bar B(ASC-0282 17/24)도 FAIL(1/24 — checklist가 10/24로 오히려 이김). H3도 실패.
- **기전(softener 아님, 설계 교훈)**: weak+AIOS가 75% 에피소드에서 doom-loop 서킷브레이커에 걸림
  (weak-raw 4%). epistemic-runtime **게이트가 약한 로컬 모델을 loop에 가둬 더 나쁘게** 만들었다.

**no-launder 판정**: "AIOS epistemic runtime이 checklist를 이긴다"는 이 벤치·이 약모델에서 **empirically
거짓**. §0 재정의의 그 형태는 죽었다. 세탁 금지 — 이건 defensible null이 아니라 결정적 negative.

**pivot (이미 진행 중, 이 STOP이 검증함)**: 실패한 기전(게이트가 자기판단으로 모델을 가둠)은 이종
패널이 경고한 바로 그 "자기 측정 장치를 개선" 실패다. 그래서 다음 베팅 = **LearnOS**(compounding loop,
`AIOS_AGI_CONCEPTION_2026-07-17.md`) — 검증을 **loop 외부·held-out·적대적**으로 옮긴다. DriftBench STOP은
이 규율 이동의 증거지, 후퇴가 아니다. 재정의는 "매 턴 게이트"에서 "**외부검증된 경험을 복리로 컴파일**"로
좁혀진다(scope 축소). 판정 기구는 여전히 사전등록 keystone — LearnOS도 같은 규율로 EARN해야 한다.

**founder 제안 (GO/HOLD/redirect)**: (a) "epistemic runtime = 매 턴 blocking 게이트" 형태를 kill하고
게이트는 값싼 H⁰ 오염가드·비가역행동 cert로만 강등, (b) 재정의의 심장을 LearnOS 복리 loop으로 이동,
(c) DriftBench 하니스는 LearnOS의 외부 verifier 태스크원으로 재사용(폐기 아님).
