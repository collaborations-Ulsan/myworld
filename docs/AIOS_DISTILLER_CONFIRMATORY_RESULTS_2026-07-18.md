# AIOS Experience-Distiller — Confirmatory Results (2026-07-18)

**한 줄 (no-launder, 기록 정정)**: pilot의 큰 positive(+30~36pp, p<0.01)가 **확정-규모(N_verified=270,
pilot의 10배)에서 replicate 안 됐다** — 효과가 **+8.3pp(13→16/36), 비유의(p=0.25~0.30)**로 붕괴.
pre-registered H1 바(α=0.05 유의) **미충족 = NULL**. pilot의 강한 신호는 small-N/small-eval-sample
노이즈였다. 인과-게이트는 구조적으로 **null**(교사가 270 escalation 전부 검증 통과 → 걸러낼 것 없음,
verified==unverified). **이게 pre-registration + confirmatory replication이 존재하는 이유다.**

**지위**: `AIOS_DISTILLER_PREREG_2026-07-17.md` v1.1 confirmatory 판정. 앞선 pilot(`9ffcd5a`)의
"아크 첫 positive"를 **정정**한다 — 그 excitement가 내 rigor(confirmatory)에 의해 검증되어 기각됨.

## 설정
- collect `01ecb20`→`(N=270)`: 512 A-태스크, 학생 qwen3:1.7b 47% 해결, 270 escalation 전원 검증
  (`n_teacher_visible_fail=0`, `n_unverified_only=0`). seed 42. 교사 = 소버린 캐스케이드(local-first).
- 학습: **GPU(torch 2.11+cu128, 내가 고친 환경)**, 두 arm 각 ~76초(CPU 대비 2배 빠름), r=16 LoRA 3ep,
  sentinel-rehearsal 15%. eval_loss 단조감소(0.19→0.17). base=Qwen/Qwen3-1.7B HF.
- 평가: B=36 held-out(별도 생성기 계열, stripped+solution-only), sentinel=5, GPU0.

## 결과 (evaluate_report.json)
| arm | B (n/36) | rate | vs base (paired one-sided exact) | sentinel |
|---|---|---|---|---|
| base | 13 | 0.361 | — | 무회귀 |
| verified-LoRA | 16 | 0.444 | +8.3pp, n01=9 n10=6, disc=15, **p=0.304 ❌** | 무회귀 |
| unverified-LoRA | 16 | 0.444 | +8.3pp, n01=6 n10=3, disc=9, **p=0.254 ❌** | 무회귀 |

**pilot(`9ffcd5a`) 대비**: LoRA arm의 B가 0.69~0.75 → **0.444로 하락**(같은 36 B, 같은 채점). base도
0.39→0.36. 순효과 +30pp → **+8pp**(순 3태스크). 두 arm 다 16/36 동일(게이트 null 재확인).

## 판정 (양방향, no-launder)

**H1(증류가 학생을 개선) — pre-registered 바에서 NULL.**
- 명목상 방향은 positive(13→16/36, 두 arm, sentinel 무회귀, pilot과 부호 일치) — 세탁 내려서 "완전
  무효"라 하지 않는다. **그러나 크기 작고(+8pp) 통계적 비유의(p=0.25~0.30)** → **사전등록 H1 미충족.**
- **pilot의 +30~36pp(p<0.01)는 replicate 실패** — small-N(N_train=25) + small-B-eval(36) 노이즈의
  높은 꼬리였다. confirmatory가 그걸 정확히 잡았다. **이게 왜 confirmatory를 돌렸는가의 답이다.**

**인과-게이트 — null(구조적).** verified==unverified(둘 다 16/36). 원인: 교사(소버린 캐스케이드,
강모델 종단)가 held-out 실패 궤적을 거의 안 만듦 → 게이트가 걸러낼 것이 없음. "게이트가 나쁘다"가
아니라 **"신뢰가능한 교사에겐 게이트가 불필요"** — S+1.1의 "인과-게이트가 핵심 fix" 기대도 정정됨.

## 내가 소유하는 설계 결함 (정직)
**training N만 250으로 스케일하고 eval B는 36에 방치했다.** +8pp를 α=0.05로 검출하려면 B도 수백 태스크가
필요(현 disc 9~15로는 underpowered). 즉 이 NULL은 (a) 진짜 무효일 수도, (b) 작은-B로 인한 검출력 부족일
수도 있다 — 구분 불가. **단 효과-크기 붕괴(30→8pp)는 검출력과 무관하게 pilot이 inflated였음을 가리킨다.**

## 종합 (이 아크의 정직한 현주소)
DriftBench STOP · S+1 · S+1.1 · **distiller confirmatory NULL** — 네 번째 rigorous 시도도 replicate되는
EARNED positive를 못 냈다. frozen 모델 주위(스캐폴드/증류) 접근이 이 스케일·기질에서 복리를 내지 못한다는
누적 증거이며, Council·Sutton 비판과 정합한다. **단 negatives는 전부 정직·pre-registered·재현가능** —
이게 진짜 산출물이다(부풀린 승리보다 credible).

## 다음 (surface, 결정은 founder)
1. **B-eval 스케일업**(수백 held-out)으로 +8pp가 진짜인지 검출력 확보 — 값싼 결정적 실험. 유의하면
   작은 positive EARN, 아니면 확정 NULL.
2. **기질/교사 재설계로 게이트를 실제 시험**: 교사가 *가끔 틀리는* 설정(약한 교사/adversarial)에서만
   인과-게이트가 값을 낼 수 있음.
3. **또는 방향 재검토**: 네 번째 null이면 Sutton식 online 학습(streaming RL) 등 더 근본 재검토.
