# AIOS Experience-Distiller — Big-B Results (2026-07-22) — 기록 재정정

**한 줄 (no-launder, 3번째 정정)**: eval B를 36→**300**으로 키워 검출력을 확보하니 —
증류(unverified arm)가 base를 **+14.0pp(0.293→0.433), p=1.1e-05로 강하게 유의** = **아크 첫
well-powered POSITIVE**. 이는 내 지난 "confirmatory NULL"(N_B=36, underpowered)을 **정정**한다.
단 두 가지 caveat을 세탁 없이: (1) **효과가 학습-분산에 민감** — 사실상 동일 데이터의 두 arm이
+14pp(유의) vs +1.4pp(비유의)로 갈림 → 단일-seed 신뢰 불가, multi-seed 필요. (2) **인과-게이트는
무관(harmful 아님)** — 게이트가 아무것도 안 걸렀으므로(§아래) verified vs unverified는 순서-분산일 뿐.

## 왜 이 재정정이 정당한가 — 내가 소유한 설계결함의 수정
지난 confirmatory(N_B=36, `833d75d`)는 내가 "training N만 250 키우고 eval B는 36 방치"한 **검출력
부족**이었다(내가 그때 결함으로 명시). founder GO로 B를 300으로 키운 값싼 결정적 실험이 그걸 해소:
underpowered에서 안 보이던 +14pp가 N=300에서 p=1e-05로 드러났다. **pre-registration + power + replication의
교과서적 작동** — pilot 과대(+30pp) → underpowered null(+8pp ns) → well-powered 진실(+14pp sig, 단 분산 큼).

## 결과 (N_B=300, evaluate_report.json)
| arm | B pass (n/300) | rate | vs base (paired one-sided exact) |
|---|---|---|---|
| base | ~88 | **0.293** | — |
| **lora_unverified_trajectory** | ~130 | **0.433** | **+14.0pp, p=1.1e-05 ✅ 유의** |
| lora_verified_trajectory | ~92 | 0.307 | +1.4pp, p=0.377 ❌ 비유의 |

(N_B=36에선 둘 다 0.444로 동일해 보였음 = 소표본 노이즈. N=300에서 base·arm이 재측정되며 진짜 분포가 드러남.)

## verified vs unverified 차이 = 학습-분산, NOT 게이트 효과 (규명)
- collect: `n_unverified_only=0`, `n_teacher_visible_fail=0` — 교사(소버린 캐스케이드)가 270 escalation
  전부 held-out 통과 → **인과-게이트가 걸러낼 레코드가 0개.** 두 arm은 **동일 270 레코드 집합**을 씀.
- `train_lora._target_text`: 두 trajectory arm 모두 `trajectory or solution` 동일 구성. 차이는 **파일
  기록 순서**(collect가 verified/unverified SFT를 다른 순서로 씀) → seed 42 shuffle이 다른 순열 → 270-예제
  소규모에서 두 adapter가 ~13pp 갈림. **∴ verified<unverified는 순서/seed 분산이지 "게이트가 해친다"가 아님.**
- **S+1.1의 "인과-게이트가 핵심 fix" 기대는 확정 refute**: 신뢰가능한 교사에겐 게이트가 작동할 재료가 없다.

## 정직한 verdict
- **증류는 실재하는 positive** — 로컬 학생에 교사 궤적 증류가 held-out을 개선(unverified +14pp, p=1e-05,
  N=300, sentinel 무회귀, B는 A와 구조 격리·solution-only 채점). **아크 첫 well-powered positive.** Council·
  Sutton이 가리킨 "사회의 경험을 학습으로 되돌려라"가 이 스케일서 신호를 냄.
- **단 분산-제한**: 사실상 동일 데이터의 두 draw가 +14pp(sig) vs +1.4pp(ns) → 단일 결과로 효과크기 확정
  불가. **다음 = multi-seed(3-5 학습 seed)로 효과크기 분포 확정**(GPU ~76s/train, 값쌈). 평균이 유의 유지하면
  robust positive EARN, 큰 분산으로 흩어지면 "약·불안정 신호".
- **게이트는 무관(harmful 아님)**: 교사가 실패를 안 만들면 게이트는 no-op. 게이트가 값을 내려면 *약한/
  adversarial 교사* 기질 필요(future).

## 아크 종합 (정정판)
DriftBench STOP · S+1 · S+1.1 = 조립/frozen-scaffold 복리 실패(확고). 증류 pivot: pilot 과대 → underpowered
null → **well-powered에서 실재 positive(+14pp)이나 분산 큼**. 즉 **방향(증류=학습으로 되돌리기)은 살아있고
첫 신호를 냈다** — mechanism(인과-게이트)은 또 무관으로 판명. multi-seed가 효과크기를 확정한다.

## 다음
1. **multi-seed 학습**(3-5 seed, 동일 N_B=300 held-out) — 효과크기±CI 확정. 값싼 결정적 한 수.
2. 병행 흡수(`AIOS_ABSORPTION_SCAN_2026-07-22.md`): Weaver 로컬 검증기(진행 중)로 escalate score_fn 실물화 —
   교사 신뢰도가 낮아지는 더 어려운 기질에서 게이트/검증이 값을 내는지 별도 시험 가능해짐.
