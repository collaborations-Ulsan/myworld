# QEL·QIR·QVM·QNet — GPT 설계와 우리 실측의 대조 (2026-08-05)

founder가 ChatGPT로 생성한 설계 2편을 전달: `docs/external/gpt/`
(`QEL·QIR·QVM 기반 에이전트-네이티브 컴퓨팅 생태계 토대 설계.pdf` 25p,
`QEL 기반 사양과 프로토타입 계획.pdf` 44p — 각각 grep 가능한 `.md` 추출본 동봉).
**원본 PDF가 도표·표 기준 정본이고, `.md`는 검색·diff용이다.**

## 0. 한 줄 판정

> **이 설계는 우리가 12주 동안 실측으로 도달한 구조와 독립적으로 수렴했고, 우리가 아직 못 푼
> 문제 하나(프라이버시 vs append-only)에 구체적 답을 준다. 다만 실행 규모가 8–10명 × 12개월이며,
> 우리에게는 아직 그것을 정당화할 게이트(N1/G5)가 통과되지 않았다.**

문서의 최종 명제가 우리 재스코프 정체성과 **같은 문장**이라는 점이 이 대조의 핵심이다:

> *"QEL의 핵심은 AI가 더 많은 프로그램을 쓰게 하는 것이 아니라, AI가 만든 제안이 언제
> 사실·권한·행동·기억이 될 수 있는지를 계산 가능한 계약으로 만드는 것이다."*
> — 우리: *"AIOS는 지능을 검증하고 구속하는 인프라이지, 제조하는 기계가 아니다."*
> (`docs/AIOS_NORTHSTAR.md`, 3-채널 null 이후 재스코프)

## 1. 수렴 — 우리가 코드로 만든 것을 QEL은 타입으로 만든다

| QEL/QVM/QNet | 우리 구현 | 비고 |
|---|---|---|
| `Proposal → Observation → Attested → Established` 인식론 타입 격자 | 아크 이벤트 + "unverifiable은 성공이 아니다" 규율 | **우리는 규율, 저쪽은 타입** — 컴파일러가 강제 |
| `Established`에 policy·scope·**expiry**, "expiry 지난 Established 사용 = stale evidence" **금지** | **INV-1 freshness gate** (`tip_seq`/`tip_hash`, stale pack 거부) | 같은 불변식, 다른 층위 |
| "verifier와 executor의 동일 control-root" **금지** (자기검증) | **G2**: 검증기는 인수자와 분리, 자기 채점 거부 | 동일 |
| `stage → verify → commit` + `compensate` | claim → progress → 검증된 인수 → close | Saga 보상 액션과 같은 계열 |
| `deopt` / `Disputed` / `Revoked` (반례 시 국소 철회) | **INV-7 `supersede`** (역사 보존, 투영만 변경) | 동일 연산자 |
| `ExecutionReceipt` + SCITT/Rekor inclusion proof | akashic Merkle 원장 + 검증 네트워크 테제 | 동일 |
| **selective replay** (합성 실험: 새 capability 시 전체의 약 4.98%만 재생) | **"로그에서 재계산하는 기계"** (`docs/AIOS_ZERO_TO_TEN`) | 동일 결론 |
| `Hot State = f_projection(Relevant Evidence)`, `Cold Ledger = Canonical Typed Evidence` | 아크 로그=진실, 투영=파생 상태 | 동일 |
| QNet: **"개인 기억은 로컬에, 검증 가능한 전이만 네트워크에"** | 네트워크 테제: wire는 arc offer·attestation·challenge만, **기억은 절대 안 나름** | **문장까지 같음** |
| "로그에 기록됐다 ≠ 작업이 참되게 수행됐다" (SCITT 주의) | red-team: **"attestation은 실행이 아니라 로깅을 증명한다"** | 같은 공격을 독립 발견 |
| `control-root` 기준 독립성 (identity 문자열 아님), assurance-graded | 노드=기기, 사람=키; delegation-depth 축소 | 동일 |

**이 수렴은 우연이 아니다.** 양쪽 다 "생성 모델의 출력은 기본적으로 신뢰할 수 없다"에서 출발해
같은 결론에 도달했다 — 신뢰는 **재실행 가능한 증거**에서만 나온다.

## 2. QEL이 우리보다 앞선 것 (흡수 후보)

1. **B1 프라이버시 문제의 답.** 우리는 *"append-only 원장이 삭제·철회 요구와 충돌한다"*를
   **미해결**로 등재하고 N2 이상 확장을 정지시켰다(`AIOS_SOCIETY_GOALTREE` 프라이버시 재검토).
   QEL의 답: **공개 ledger에는 commitment와 비개인적 metadata만, 실제 데이터는 삭제 가능한
   private storage에, 필요시 암호키 폐기로 접근 제거** + 4-plane 분리(Private State / Selective
   Predicate / Encrypted Artifact / Public Receipt) + consent를 UI 체크박스가 아니라
   **versioned capability**로. ⟹ **즉시 흡수 대상. B1 해제 경로가 생겼다.**
2. **금지 프로그램 표(compiler가 거부해야 하는 것)** — 우리 "클레임 위생"의 기계화 버전.
   `Proposal`을 persistent fact에 직접 저장 / capability 복사 / 미선언 effect / 자기검증 /
   stage에서 비가역 effect / 무증거 merge·split / model이 생성한 operator 직접 설치 /
   expiry 지난 `Established` 사용 / receipt에 원문 개인정보. **우리 원장·검증기에 린트로 이식 가능.**
3. **실패 조건 표 = kill rule의 확장판.** "대부분의 operator가 결국 unrestricted shell을 요구 →
   effect model 실패", "verifier 비용이 실행 비용을 지속 초과 → 검증 경제성 실패",
   "immutable log에 삭제 불가 개인정보 축적 → privacy architecture 실패" 등 14개.
   우리 사전등록 규율과 같은 정신이며, **QEL 쪽이 더 촘촘하다.**
4. **타입화된 capability**(linear/affine/shareable, 위임=범위 축소) — 우리는 lease만 있고
   권한은 관례다. 권한 증폭을 **컴파일 시점에** 막는 것은 우리가 못 하는 일.
5. **참조 우선순위 규율**: 원전 표준 > 학술 > 국내 원문 > 보조 > **후순위(마케팅 문서, 자체 평가만
   있는 vendor benchmark)**. 우리 freshness gate에 그대로 추가할 가치가 있다.

## 3. 우리가 QEL보다 앞선 것 (그리고 QEL이 알아야 할 것)

1. **돌아가는 코드와 측정된 결과.** QEL은 설계 문서다. 우리는 사회 커널 3모듈 + 100+ 테스트 +
   라이브 회수 MTTR 19.95초 + 클린 venv 설치 검증을 갖고 있다.
2. **3-채널 null.** QEL 문서 어디에도 *"축적된 증거가 에이전트를 더 낫게 만드는가"*에 대한
   측정이 없다. 우리는 사전등록으로 **아니다**를 측정했다(θ/X/E, `C_overall = 0.000`).
   ⟹ **QEL의 가치 명제는 "능력 향상"이 아니라 "권한·안전·검증"이어야 하며, 다행히 문서 스스로
   그렇게 말한다.** 이 정합은 우연이 아니라 두 프로그램이 같은 벽에 부딪힌 결과로 읽어야 한다.
3. **합성 실험과 실측의 구분.** 문서의 수치(decode-and-apply 2.06배, 압축 1.31배, selective
   replay 4.98%, Cognitive JIT 2.29배, newcomer lane surplus 95.7% 유지·active provider
   9.5%→25.5%)는 **문서가 스스로 "실제 시장 예측이 아니라 메커니즘 검증용 합성 실험"이라고
   명시**한다 — 정직하다. 다만 **합성 결과는 가설이지 증거가 아니다.** 인용할 때 이 라벨을
   떼면 안 된다.

## 4. 규모 현실 — 그리고 우리 게이트

문서의 권고 팀은 **8–10명 × 12개월**(PL/컴파일러 2, Rust 런타임 2, 보안/분산 2, 에이전트/검증
1–2, 시뮬레이션 1, 제품 1, 형식기법 0.5–1). 우리는 operator 1쌍이다.

**우리 게이트 규율(적대 council §4b.1)은 그대로 적용된다:** 각 단계는 *"queue+files로는 불가능한
능력"*을 대야 착수한다. QEL 전체를 짓는 것은 현재 우리 게이트를 통과하지 못한다.
**N1(G5: 사회 > solo+원장)이 여전히 먼저다** — 하네스는 오늘 완성됐고(12+41 tests green), 실행만
남았다.

## 5. 결정 (operator)

| | 판정 |
|---|---|
| QEL 전체 구현 | **NOT NOW** — 8–10명 규모, 우리 게이트 미통과. 재평가 시점: N1 통과 후 |
| **프라이버시 4-plane + commitment-only ledger + crypto-shredding** | **흡수 진행** — 우리 B1을 푸는 유일한 구체안. 설계로 먼저, 코드는 N1 이후 |
| **금지 프로그램 표 → 린트** | **흡수 진행** — 우리 검증기/원장에 규칙으로 이식(저비용, 즉시 가치) |
| **참조 우선순위 규율** | **흡수 진행** — freshness gate에 추가 |
| 타입화 capability(Q-Rust DSL) | **보류** — lease로 충분한지 G5가 먼저 말해야 함 |
| QNet 경제층(수수료·challenge reserve) | **보류** — 우리 네트워크 테제의 미해결 항목("누가 재실행 비용을 내나")과 동일 지점. QEL도 답을 갖고 있지 않고 메커니즘만 제안 |

**하지 않을 것:** 이 문서의 합성 수치를 우리 근거로 인용하는 것. "QEL 설계가 있으니 검증됐다"고
말하는 것. 그리고 QEL을 3-채널 null의 우회로로 쓰는 것 — 이 설계는 능력이 아니라 **권한과 증거**를
다루므로 null과 충돌하지 않지만, 그 경계를 흐리는 순간 같은 실패를 반복한다.

---
*자료: `docs/external/gpt/` (PDF 2편 + 추출 md). 대조 대상: `docs/AIOS_NORTHSTAR.md`,
`docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md`, `docs/AIOS_NETWORK_THESIS_2026-08-02.md`,
`docs/AIOS_ZERO_TO_TEN_2026-08-03.md`, `docs/AIOS_SOCIETY_GOALTREE_2026-08-02.md`(B1),
`scripts/aios_society.py`(INV-1/7), `scripts/aios_takeover_verify.py`(G2).
공유 링크(`chatgpt.com/share/6a72f607…`)는 브라우저 스크랩이 0바이트로 실패 — 내용은 위 PDF로
갈음했고, 실패 사실을 그대로 기록한다.*
