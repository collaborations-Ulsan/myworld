# AIOS Experience-Distiller — Pilot Results (2026-07-18)

**한 줄**: 아크 전체의 **첫 weight-level POSITIVE** — escalation 궤적을 로컬 학생에 증류하니 held-out
성공률이 **38.9% → 69-75% (+30~36pp, p<0.01, sentinel 무회귀)**. 동시에 정직한 서프라이즈: **인과-게이트
(verified)가 무필터(unverified)를 못 이겼다** — pilot scale에서 내 대표 mechanism이 값을 못 함.
**PILOT ONLY (N_verified=25 < 250)** — 확정 아닌 강한 directional 신호.

## 설정 (사전등록 `9c95c10` 준수, 환경 수정 후 GPU 실행)
- 학생 = qwen3:1.7b(HF weights). 교사 = 소버린 escalation 캐스케이드(f31d055). N_verified=25(collect `dc3d818`).
- substrate 캘리브레이션(`076e78e`): 학생이 강화 A에서 50% pass = 진짜 헤드룸(네 번째 벽을 처음 넘음).
- B = 36 held-out(별도 생성기 계열, 격리) + sentinel 5. 채점 = **stripped prompt + solution-only**.
- 환경: torch 2.11+cu128(RTX 5090 sm_120 언블록) — 원 데이터 `evaluate_report.json`.

## 결과 (evaluate_report.json)
| arm | B pass | escalation | vs base (paired one-sided) | sentinel |
|---|---|---|---|---|
| base 학생 | **0.389** | 0.611 | — | 1.0 (기준) |
| verified-LoRA (인과-게이트) | **0.694** | 0.306 | +30.5pp, n01=13 n10=2, **p=0.0037 ✅** | 1.0 무회귀 |
| unverified-LoRA (무필터 대조군) | **0.750** | 0.250 | +36.1pp, n01=14 n10=1, **p=0.00049 ✅** | 1.0 무회귀 |

## 판정 (양방향, no-launder)

**Q(b) 증류가 로컬 모델을 개선하나 → YES, 강하게 (첫 positive).**
- 두 LoRA arm 모두 base를 유의하게 상회(+30~36pp, p<0.01), sentinel 무회귀. escalation도 61%→25-31%로
  하락(H2 확인: 자립도↑). **"에이전트가 사회로부터 실제로 학습한다"의 첫 weight-level 증거.** Council이
  가리키고 창업자가 GO한 pivot이 pilot scale에서 EARN. Sutton-정합 방향(weight-level 학습)에 신호.

**Q(a) 인과-게이트(verified)가 무필터(unverified)를 이기나 → NO (정직한 서프라이즈).**
- unverified(0.750) ≥ verified(0.694). 차이 =2 태스크/36 → **두 LoRA arm은 pilot scale에서 통계적
  구분 불가**(base 대비 점프는 크고 유의; 서로간 차이는 노이즈 범위). 즉 **인과-게이트가 이득을 못 보임 —
  오히려 데이터 감소로 근소 열세.** 가설: 작은 N에선 SFT 데이터 *양*이 필터된 *질*을 이긴다(known SFT
  효과). 내 S+1.1 대표 mechanism이 여기선 값을 못 했다 — 세탁 없이 기록.

## 함의 · 다음 (사전등록 대상)
1. **distillation 방향 = EARNED (pilot)** → 전체 N≥250 confirmatory 런 정당화(이제 GPU 언블록).
2. **인과-게이트 재검토**: N=25에서 무이득. 재판정 질문 — (a) N↑(질이 양을 이기는 구간)에서 flip하나?
   (b) hard filter 대신 soft weighting이 나은가? (c) 데이터 임계 위에서만 적용? confirmatory 런에
   verified/unverified/soft-weight를 arm으로 사전등록해 인과-게이트의 *진짜 값어치*를 가른다.
3. **주의**: N=25·36 B는 pilot. 확정 주장 금지. verified<unverified는 노이즈일 수 있으나 "게이트가
   명백히 돕지 않았다"는 사실은 유효.

**종합**: 이 아크의 세 negative(조립 복리 안 됨) 뒤, 방향을 **학습으로 되돌리자** 첫 positive가 나왔다.
mechanism(인과-게이트)이 아니라 **방향(증류)**이 값을 했고, 그 mechanism조차 pilot에선 겸손해졌다 —
정확히 substrate-first·no-launder가 가르친 대로 "mechanism 정교화보다 올바른 방향·기질이 먼저."
