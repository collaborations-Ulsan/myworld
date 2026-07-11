# DriftBench 이중 하니스 화해 결정 (operator, 2026-07-11)

**발견** (harness executor flag, 2026-07-11): 같은 M2 keystone에 대해 두 개의 사전등록·두 개의
하니스가 병렬 존재 —
- **A**: `docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md` v1.1 (동결) + `experiments/driftbench/`
  (fb69a1b; 분석 스크립트 해시 동결) — claude@myworld 레인.
- **B**: `ASC-0282-m2-driftbench-closed-loop.md` (accepted) + `scripts/m2_driftbench/` +
  `descentnet/docs/DESCENTNET_M2_DRIFTBENCH_PREREG_2026-07-10.md` — codex@myworld 체인 (WP-B).

**임계값 충돌**: A = mutating-only ≥13/18 + one-sided exact McNemar α=0.05. B = 전체 24 대상
≥17/24, tie≠win (= statics가 등가면 mutating 17/18 요구; B 자체 power 분석 0.36 @ p=0.65).

**근본 원인 (정직 기록)**: 17/24는 마스터플랜 §5 초안 수치. claude 레인은 Codex 적대 리뷰로
"static 분모 혼입 모순"을 교정해 prereg v1.1에 13/18을 동결했으나 **마스터플랜 §5 본문을 갱신하지
않았고**, codex 체인은 마스터플랜 바를 충실히 동결했다. 문서 간 불일치가 전파된 것 — 어느 쪽의
잘못도 아닌 조정 실패이며, **아직 어떤 런도 실행되지 않아** 오염 없이 화해 가능.

## 결정 (operator pair 권한 내; 기록 파괴 없음; 동결문서 본문 무수정)

1. **역할 분리 — 경쟁이 아니라 조합**:
   - `scripts/m2_driftbench/` (ASC-0282 WP-B) = **실행 substrate** (env/fixtures/meter/trace —
     AIOS 내부 배선 완료된 쪽).
   - `experiments/driftbench/schema.py` + `analyze.py` (해시 동결: 1ed8fd8b…, 53f4037e…) =
     **결과 스키마 + 판정 계산기**. 러너는 schema.py 형식으로 행을 방출하고 analyze.py가 계산한다.
   - `experiments/driftbench/tasks.py` 템플릿은 독립 픽스처 소스로 보존 (m2 픽스처가 leakage 규칙
     위반 시 대체재).
2. **판정 권한 분리 (사전 선언)**:
   - **재정의("Epistemic Runtime") keystone 판정 = A (prereg v1.1) 단독** — 13/18 mutating +
     McNemar + static 등가 가드 + 비용 sweep. 이것이 masterplan §0 재정의의 유일 판정자.
   - **B의 17/24 (tie≠win) = ASC-0282 계약-내부 완료 바로만 유효** (계약 자체가 "INTERNAL
     completion"으로 명명; honest negative closeout 유효로 사전 선언되어 있음).
   - **한 번의 런, 두 바 모두 보고** — 같은 결과 테이블에서 두 기준을 다 계산해 그대로 공개.
     엇갈리면 (예: 13/18 충족, 17/24 미달) 둘 다 straight 보고; 재정의 주장은 A 기준, ASC-0282
     closeout은 B 기준을 따른다. 어느 쪽도 사후 재해석 금지.
3. **마스터플랜 §5 정정**: 본문 말미에 정정 노트 append (17/24 → prereg v1.1이 정본).
4. **descentnet 쪽 prereg는 무수정** (타 레포·동결 문서). 이 화해 문서가 myworld 측 정본 기록이며,
   codex 체인은 ASC-0282 receipts에서 이 문서를 인용하면 된다.

**Founder 노트**: 이 결정은 운영자 수준(가역·append-only·실행 전)으로 판단해 즉시 적용. 재지시
시 (redirect 한 단어면 충분) 전체 롤백 가능 — 어떤 동결 본문도 수정하지 않았으므로.

서명: claude@myworld (operator), 2026-07-11. Evidence: fb69a1b (A 하니스), fb4f961 (B freeze-prep),
7fc6ae5 (ASC-0282 수락), 6ca9c55 (A prereg 동결), harness-executor 충돌 플래그 (세션 기록).
