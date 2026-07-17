# LearnOS S+1.1 Results (2026-07-17) — causal gate FIXES the harm, but compounding stays untestable (honest)

**한 줄**: 인과-ablation 게이트는 S+1의 진단된 해악(memory-poisoning)을 **고쳤다** — 그러나 그 과정에서
더 깊은 진실이 드러났다: **이 태스크 기질에선 애초에 복리가 측정 불가**다. no-launder 양방향.

## 무엇이 바뀌었나 (S+1 → S+1.1)
- 신규: `causal_gate.py`(항목 제거 시 held-out 악화할 때만 승격) + `gene_pool.py`(MAP-Elites niche/
  열성보존/자원cap) + `evolve_s11.py`(이종 mutation router) + `run_s11.py`. S+1 코드 재사용.
- 프로토콜 동일: A(mine) / B(transfer-holdout, 12) / sentinel(10), Blind-Curator 감사.

## B-transfer-holdout curve (결정적 지표) — S+1 vs S+1.1
| | iter -1 (라이브러리 없음) | 최종 (iter 11) | 판정 |
|---|---|---|---|
| **S+1** | 12/12 | **10/12** | 주입이 B를 **해침** (falling) |
| **S+1.1** | 12/12 | **12/12** | **flat — 해악 제거됨** (falling 아님) |
sentinel: S+1.1 10/10 → 10/10 (무회귀). paired: n_discordant=0, p=1.0 (신호 없음, 천장 탓).

## 인과-게이트 통계 (작동 확인)
- `scaffold_tool_candidates_considered: 3` → **3개 전부 인과-무책임으로 기각**
  (`causal_rejected_no_responsibility: 3`, WITH/WITHOUT 둘 다 통과 = 기여 없음).
- `causally_verified_promoted: 0`, `degenerate_prefiltered: 0`.
- 결과: **라이브러리에 tool/scaffold가 하나도 안 들어감** → gene_pool 비어 있음
  (`num_niches: 0, num_specialists: 0, total_recessive_retained: 0`).
- router: reuse_tool/reuse_scaffold = 0 (재사용 없음 — 풀이 비었으니 당연). code_patch만 승격.

## 정직한 판정 (양방향)
- **POSITIVE (실제)**: 인과-게이트는 옳은 안전장치다. S+1은 degenerate 항목이 라이브러리를 오염시켜
  B를 떨어뜨렸다(12→10). S+1.1은 그 항목들을 **인과 증거로 정확히 거부**해 B가 안 떨어진다(12→12).
  "memory-poisoning"의 진단과 처방이 맞았다.
- **NEGATIVE / NULL (복리 미입증)**: 복리(B 상승)는 여전히 **입증 못 함** — 두 이유:
  1. **천장**: base 모델이 B를 이미 12/12 푼다 → 오를 여지 없음.
  2. **기질 부적합**: bug-fix 태스크에서 **인과적으로 재사용가능한 스킬/도구가 하나도 안 나왔다**
     (3개 후보 전부 non-causal). 각 수정이 idiosyncratic해서 A에서 채굴한 게 B에 인과적으로 도움
     안 됨 → 복리할 물건 자체가 없음.
- **§9 Sutton 정합**: naive 스킬-축적은 frozen 모델 위에서 복리 안 됨 — 재확인. 단 이번엔 게이트가
  **가짜 복리를 거부**함으로써 그 사실을 정직하게 노출했다 (자기재가 벤치옵티마이저가 안 됨).

## pivot (negative→terminus 아님) — 이건 게이트 문제가 아니라 **기질(substrate) 문제**
복리를 측정하려면 태스크 기질이 두 조건을 만족해야 한다:
1. **Headroom**: base 모델이 B에서 실패해야 (개선 여지). bug-fix 12/12는 실격.
2. **전이가능 구조**: 태스크들이 **공유 재사용 구조**를 가져 A에서 채굴한 스킬/도구가 B에 인과적으로
   도움되어야. 각 수정이 독립적이면 복리할 게 없다.
→ **다음(S+1.2 / 다음 스프린트) = 태스크 기질 재설계**: base가 실패하고 + 공유 구조가 있는 문제군
   (예: 같은 API/라이브러리를 반복 쓰는 태스크열, 커리큘럼식 난이도 상승 — Sutton식 경험 누적과
   정합). 게이트·gene-pool은 그대로 두고 **substrate에 headroom+transfer를 넣어** 재판정.

## 종합 (세 keystone-급 결과)
DriftBench STOP · S+1 no-transfer(해악) · S+1.1 harm-fixed-but-untestable — 셋 다 같은 방향:
**frozen 모델 주위 naive 축적은 복리 안 되고, 정직한 게이트는 가짜 복리를 거부한다.** 다리는
안 죽었다 — 하지만 그 다리를 건너려면 (a) 인과-검증 축적(S+1.1이 확립) + (b) headroom·transfer 있는
기질(다음)이 **둘 다** 필요하다. flat이 계속되면 Sutton 편 증거로 그대로 공개.
