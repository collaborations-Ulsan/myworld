# LearnOS S+1 — 결과 (2026-07-17)

**입력**: `docs/AIOS_LEARNOS_S1_DESIGN_2026-07-17.md` (설계) + `docs/AIOS_AGI_CONCEPTION_2026-07-17.md` §6
(v0 첫 브릭). 구현: `experiments/learnos/{archive,search,audit,run_s1}.py` (v0의 `verify.py`/`ledger.py`/
`tasks.py`를 REUSE, 재작성하지 않음). 테스트: `tests/test_learnos_s1.py` (27개, no live LLM).

**판정 대상**: v0가 못 답한 질문 — "축적이 안 본 태스크(B, transfer-holdout)로 전이되어 복리로
오르는가?" 같은 태스크 재풀이는 복리가 아니다; skill/tool/scaffold는 A에서만 채굴하고, B는 mining
경로가 구조적으로 닿지 못하는 held-out 세트에서 iteration에 걸쳐 측정한다.

**TL;DR (no-launder)**: 이 스케일(A=12/B=12/sentinel=10, 12 iter, 단일 시드, 단일 로컬 30B 모델)에서
답은 **NO** — B 성공률은 라이브러리를 처음 주입한 순간 100%(12/12, no-library baseline)에서
83.3%(10/12)로 **떨어졌고**, 이후 11개 iteration 내내 회복 없이 그 수준에 머물렀다(final vs first =
FALLING). sentinel은 12 iteration 내내 10/10으로 무회귀. §5의 사후 진단(adversarial re-examination)은
이 하락의 구체적 메커니즘까지 찾아냈다 — "복리가 안 된다"는 막연한 결론이 아니라 "왜 안 됐는지"와
"뭘 고치면 되는지"가 남는 negative-with-a-pivot 결과다.

## 1. 설계 요약

| 축 | v0 | S+1 |
|---|---|---|
| 구조 | linear improver (매 iter, 안 고쳐진 태스크에 3-kind 고정 후보) | SEARCH: 다양성 아카이브(archive.py) + 관찰수율 mutation router(search.py) |
| 후보 생성 | code_patch / cot_scaffold / tool 고정 3종 항상 시도 | 6-arm bandit: fresh_{code_patch,scaffold,tool}, hypothesis_then_rewrite(VISTA 분리), reuse_{scaffold,tool} |
| 태스크 분할 | 18개, 단일 풀 (visible/held-out만 분리) | 34개, A(mine)=12 / B(transfer-holdout)=12 / sentinel=10 — 카테고리별 A/B 페어링 |
| 복리 판정 | 없음 (ledger curve만, "복리 주장 아님"으로 명시) | B held-out 성공률의 iteration별 곡선 + Wilson CI + iter(-1) vs 최종 paired sign test |
| 검증자 무결성 | 없음 | Blind-Curator 감사(audit.py): overfit-to-visible + sentinel-breaking 결함 주입, false-pass율 측정, 임계 초과 시 승격 동결 |

## 2. 태스크 분할 (`experiments/learnos/data/task_split.json`)

- **A (mining, n=12)**: off_by_one_range, wrong_operator_and_or, incorrect_accumulator_init,
  wrong_condition_negation, mutable_default_arg, wrong_comparison_direction, wrong_index_fencepost,
  recursive_base_case_wrong, sorting_comparator_wrong, list_slicing_off_by_one, early_return_wrong,
  swapped_args_order.
- **B (transfer-holdout, n=12)**: 위 12개와 정확히 같은 bug-kind 카테고리의 **다른 함수** — 예:
  `off_by_one_range`(mine)→`off_by_one_last_n`(B), `wrong_comparison_direction`→`comparison_direction_find_max`.
  이 페어링 자체가 전이 시험의 핵심: 같은 추상 스킬, 다른 표면형.
- **sentinel (회귀 가드, n=10)**: boundary_empty_list, string_reverse_off_by_one, dict_default_missing,
  dict_default_word_freq, wrong_modulo_even_odd_check, swapped_return_minmax, min_max_mixed_up,
  min_max_mixed_clamp, float_int_division, float_int_division_ratio.
- 구조적 격리: `tests/test_learnos_s1.py::test_search_and_archive_never_reference_held_out_path`가
  `search.py`/`archive.py` 소스를 grep해 held-out 파일명/private loader가 등장하지 않음을 강제.
  `test_mine_iteration_never_touches_tasks_outside_its_pool`가 mining이 A 외 task_id를 절대 만지지
  않음을 런타임으로도 확인.

## 3. Blind-Curator 검증자 감사 (audit.py)

사전 등록: promotion을 신뢰하기 전 매 런마다 먼저 실행. 두 결함 클래스:
1. **overfit_to_visible** — visible_tests의 (입력→기댓값) 리터럴만 특수-케이스하고 나머지는 원본
   buggy_source(재귀 호출까지 전부 rename)로 폴백. visible은 통과하지만 일반화하지 않음 — 게이트가
   이걸 승격시키면 false-pass.
2. **sentinel_breaking** — golden(진짜 정답) 구현을 감싸되 sentinel_check가 쓰는 정확히 그 입력만
   틀린 값을 반환. 나머지(held-out 포함)는 골든 그대로 — "겉보기엔 맞는" 회귀를 게이트가 놓치면
   false-pass.

**결과 (오프라인, 실제 게이트 `improve.evaluate_candidate` 대상, 전체 34-task 코퍼스)**:

```
n_trials=66  false_passes=0  false_pass_rate=0.000  threshold=0.050  freeze_promotion=False
```

false-pass 0/66 — 검증자가 두 결함 클래스 모두 정확히 기각. (감사 자체가 결함을 잡아내는지는
`tests/test_learnos_s1.py::test_audit_catches_injected_false_pass_with_a_weakened_gate`가 의도적으로
약화된 fake 게이트로 별도 검증 — false_pass_rate=1.0, freeze_promotion=True 확인됨.)

**라이브 런 감사 결과** (run_s1.py가 mining 전 매번 실행, 결과 동일):

```
trials=66  false_passes=0  false_pass_rate=0.000  threshold=0.050
verifier trusted for this run -- promotions may enter the shared library.
```

`audit_frozen=False` — 이 런의 22개 promotion은 승격 동결 없이 전부 게이트를 통과한 것으로 기록됨.

## 4. 라이브 런 (ollama qwen3-coder:30b)

- 커맨드: `python3 experiments/learnos/run_s1.py --iterations 12 --max-tasks-per-iter 2 --seed 0
  --ledger-path experiments/learnos/data/ledger_s1.jsonl --results-json experiments/learnos/data/s1_results.json`
- 백엔드: `ollama:qwen3-coder:30b` (v0의 `backend.py` 그대로 재사용, temperature=0.2, max_tokens=400)
- GPU: dual RTX 5090, 이 런 동안 다른 프로세스와 경합 (77-85% 사용률 관측) — 순수 전용 자원 아님.

### 4.1 마이닝 요약

- 후보 23개 평가, **22개 승격** (95.7%) — kind별: code_patch 9/9, cot_scaffold 5/5, tool 8/9.
- archive: `num_cells=17` `num_lineage=23` `distinct_bug_kinds_covered=12` (A의 12개 bug_kind 전부
  최소 1 cell) — cells_per_bug_kind에 off_by_one=3, wrong_operator=3처럼 한 카테고리에 여러 셀이
  생긴 건 서로 다른 mutation_kind/구조(shape)가 서로 다른 cell로 분리됐기 때문(아카이브가 실제로
  다양성을 구분하고 있다는 증거, `archive.py`의 cell = bug_kind × patch_shape).
- mutation router 관찰수율(promoted/count): `hypothesis_then_rewrite`=5/5, `fresh_scaffold`=3/3,
  `fresh_code_patch`=4/4, `reuse_scaffold`=2/2, `fresh_tool`=3/4, `reuse_tool`=5/5 — 거의 모든 arm이
  천장에 가까운 수율(A 태스크들이 30B 모델에게 쉬웠다는 신호, §5 참고).
- **공유 라이브러리 = 6개 신규 아이템** (재사용-후-재승격은 원 아이템 카운트만 올리고 중복 등록 안
  됨, `search.py::mine_iteration`의 `record_reuse_promotion` 경로로 검증됨):

  | kind | bug_kind | mined_from | iter | reused-and-promoted |
  |---|---|---|---|---|
  | cot_scaffold | wrong_operator | wrong_operator_and_or | 0 | 2 |
  | tool | mutable_default | mutable_default_arg | 2 | 5 |
  | tool | index_fencepost | wrong_index_fencepost | 3 | 0 |
  | tool | recursive_base_case | recursive_base_case_wrong | 3 | 0 |
  | cot_scaffold | sorting_comparator | sorting_comparator_wrong | 4 | 0 |
  | cot_scaffold | off_by_one | off_by_one_range | 10 | 0 |

- **알려진 스코프 제약**: v0의 `improve.sample_tasks`(REUSE, 미수정)는 A 전체가 한 번씩 승격된 뒤
  "cycle back"할 때 `pool[:max_n]`으로 **항상 목록의 처음 N개**를 고른다 — 순환(rotate)이 아니다.
  이 런에서는 iteration 5 부근부터 A 12개 중 처음 2개(`off_by_one_range`, `wrong_operator_and_or`)만
  반복 채굴됐다(로그로 확인됨). 즉 "12 iteration"의 실질 다양성은 앞의 ~5 iteration에 집중돼 있고,
  라이브러리 6개 항목도 그 구간에서 나왔다. 이건 버그가 아니라 v0 REUSE 제약의 부작용이며, §7에서
  후속 조치로 명시한다.

### 4.2 B (transfer-holdout) 복리 곡선 — 결정적 수치

라이브러리 시그니처가 바뀔 때만 체크포인트(비용 절감; iter 0/최종은 항상 체크포인트) — 그래서
iter 1과 5-9는 빠져 있다(그 iteration들에서 라이브러리가 안 바뀌었다는 뜻, 즉 마이닝은 일어났으나
재사용/무-승격 등으로 신규 라이브러리 아이템은 안 생겼다).

| iter | successes/total | rate | Wilson 95% CI |
|---|---|---|---|
| -1 (no library) | 12/12 | 1.000 | [0.758, 1.000] |
| 0 | 10/12 | 0.833 | [0.552, 0.953] |
| 2 | 10/12 | 0.833 | [0.552, 0.953] |
| 3 | 10/12 | 0.833 | [0.552, 0.953] |
| 4 | 10/12 | 0.833 | [0.552, 0.953] |
| 10 | 10/12 | 0.833 | [0.552, 0.953] |
| 11 (final) | 10/12 | 0.833 | [0.552, 0.953] |

**final vs first = FALLING** (`rising=False falling=True flat=False`). 라이브러리를 처음 주입한 순간
(iter 0, 그때 라이브러리 크기는 단 1 — 방금 mine된 wrong_operator scaffold 하나) B가 이미 100%에서
83.3%로 떨어졌고, 그 뒤 라이브러리가 1→6으로 자라는 동안 단 한 번도 회복하지 못했다.

### 4.3 sentinel (회귀 가드) 곡선

| iter | successes/total | rate |
|---|---|---|
| -1 | 10/10 | 1.000 |
| 0, 2, 3, 4, 10, 11 | 10/10 | 1.000 (전 구간 동일) |

**final vs first = FLAT.** 라이브러리 축적이 sentinel(제3의 독립 회귀 가드 풀)은 전혀 건드리지
않았다 — "no sentinel regression" 승격 기준 자체는 이 런에서 위반되지 않음.

### 4.4 paired sign test (iter -1 vs 최종 iter, B)

```
n_pairs=12  improved=0  regressed=2  n_discordant=2  p_value(two-sided)=0.5000
```

**CAVEAT (필수)**: discordant pair가 단 2개뿐이라 이 검정은 **거의 검정력이 없다** — p=0.5는 "차이
없음을 입증"한 게 아니라 "n=2로는 통계적으로 뭘 말할 수 없다"는 뜻이다. 방향성(0 improved / 2
regressed, 전부 한쪽)은 그 자체로 시사적이지만, 공식적으로는 이 표본 크기에서 유의성 주장을 할 수
없다 — 곡선의 크기(12/12→10/12, 8.3%p 하락, 6개 체크포인트 모두 동일)가 이 검정보다 더 강한 증거다.

## 5. 사후 진단 (adversarial re-examination — "verdict을 끝낼 결론 전 재검증")

부정 결과를 그대로 접수하기 전에, founder epistemics 규율("한 번은 검증기 자체를 재검증하라")에 따라
6개 라이브러리 아이템의 실제 내용을 열어봤다 — 결과가 왜 떨어졌는지 메커니즘을 찾기 위해서다.

**tool 3개 중 2개는 내용이 사실상 비어 있다(degenerate)**:
- `index_fencepost` (wrong_index_fencepost에서 채굴): `def safe_index(xs, i):\n    """PRECONDITION: len(xs) > 0 and 0 <= i < len(xs)\n    POSTCONDITION: 0 <= result < len(xs) and xs[result] == xs[i]"""\n    return i` — **인자를 그대로 반환하는 항등함수**. postcondition `xs[result]==xs[i]`는 `result==i`일 때 항상 참인 자기동어반복이라 contract-fuzz를 통과했을 뿐, 실제 로직이 전혀 없다.
- `recursive_base_case` (recursive_base_case_wrong에서 채굴): `def safe_factorial_base_case(n):\n    """PRECONDITION: n >= 0\n    POSTCONDITION: result == 1"""\n    return 1` — **상수 1을 반환**. postcondition이 정의상 항상 참.
- `mutable_default` (mutable_default_arg에서 채굴): `def safe_index(lst, item):` — list.index()를 감싼 범용 조회 헬퍼로, **mutable-default-argument 버그와 의미적으로 무관**하다.

**scaffold 3개는 사실상 동일한 텍스트다** — wrong_operator/sorting_comparator/off_by_one 세
카테고리에서 채굴된 스캐폴드가 전부 "1. loop 경계·인덱싱 확인 2. 연산자 사용 확인 3. edge case
테스트 ..." 형태의 **같은 6단계 범용 체크리스트**를 문구만 바꿔 반복한다 — qwen3-coder:30b가
카테고리별로 차별화된 스킬을 채굴하지 못하고 하나의 일반론으로 수렴한다는 뜻이다.

**메커니즘**: v0의 승격 게이트(`improve.evaluate_candidate`, REUSE)는 **최종 patch_source가 테스트를
통과하는지만** 확인하고, tool/scaffold가 그 통과에 **인과적으로 기여했는지는 검증하지 않는다** —
code_patch 부분이 독자적으로 이미 맞았다면, 옆에 붙은 tool이 항등함수든 상수함수든 관계없이
승격된다. 그 결과 라이브러리에 채워진 건 "재사용 가능한 스킬"이 아니라 상당 부분 **비인과적/범용
장식물**이었고, 이걸 B 태스크 프롬프트에 "참고하라"며 주입하면(특히 `Library.best_for`의 fallback —
정확히 맞는 bug_kind가 없으면 아무 아이템이나 반환) **관련 없는 내용으로 프롬프트를 오염**시킬 뿐이다.

사후(post-hoc) 확인 사살: 최종 라이브러리 상태로 12개 B 태스크를 다시 한 번 별도 호출로 평가했더니
(기록된 라이브 수치의 재현이 아니라 진단용 보조 실행, temperature=0.2라 정확히 같지 않을 수 있음)
동일하게 10/12가 나왔고, 실패한 2개는 `wrong_operator_inclusive_bounds`(1/2 — bug_kind는 일치하지만
무관한 tool이 fallback으로 끼어듦)와 `swapped_args_percent_of`(0/2 — 라이브러리에 `swapped_args`
카테고리 아이템이 아예 없어 완전히 무관한 scaffold+tool이 fallback으로 주입됨)였다. 이 진단은 §4.2의
집계 수치(라이브 런에서 기록된 것)를 재현하는 정확한 재생이 아니라, 같은 메커니즘이 실제로 작동하고
있음을 보여주는 보조 증거로만 사용한다.

**결론**: 이건 "복리가 원천적으로 불가능하다"는 증거가 아니라, "**이 승격 게이트에 인과-검증
(ablation)이 빠져 있어서 비인과적 장식물이 라이브러리를 오염시켰고, 그 오염이 전이 시점에 노이즈로
작용했다**"는 진단 가능하고(diagnosable), 고칠 수 있는(actionable) negative다. §7에 구체적 다음
단계로 남긴다.

## 6. 정직한 판정

**NO — 이 스케일(A=12/B=12/sentinel=10, 12 iteration, 단일 시드, 단일 로컬 30B 모델)에서 축적은 안 본
태스크(B)로 복리 전이되지 않았다. 오히려 라이브러리를 주입하는 순간 B 성공률이 100%(12/12)에서
83.3%(10/12)로 떨어졌고, 11 iteration 내내 회복하지 않았다(final vs first = FALLING).** sentinel은
전 구간 10/10으로 무회귀 — "라이브러리가 이미 잘 풀던 걸 망가뜨리진 않았다"는 더 약한 기준은
지켰지만, "복리로 는다"는 핵심 주장은 EARN하지 못했다.

이건 Beyond-pass@1 / CL-Bench가 예측한 "메모리 스캐폴드가 장기지평을 해칠 수 있다"는 A1 부정 가드의
첫 실측 확인이다 — 다만 §5의 진단 덕분에 막연한 "그렇다"가 아니라 **구체적 메커니즘("승격 게이트가
인과성을 검증하지 않아 비인과적 tool/scaffold가 라이브러리를 오염시킴")까지 딸린 확인**이다. 통계
검정(§4.4, paired sign test)은 표본이 작아(n_discordant=2) 이 방향성을 독립적으로 확증할 검정력이
없다 — 판정은 곡선 자체(6개 체크포인트 전부 동일하게 10/12, 단 한 번도 12/12로 안 돌아옴)에 근거한다.

## 7. 스코프 및 다음

**스코프 제약 (정직하게)**:
- A=12/B=12/sentinel=10, 12 iteration, max_tasks_per_iter=2, 단일 시드(0), 단일 로컬 모델
  (qwen3-coder:30b) — 반복-시드 분산 추정 없음, 단일 런.
- §4.4의 paired sign test는 discordant pair 2개뿐이라 통계적으로 사실상 무력하다; 판정(§6)은 검정이
  아니라 6개 체크포인트 전부 동일한 곡선 형태(FALLING then FLAT)에 근거했다.
- §4.1에서 밝힌 대로 v0의 `sample_tasks`(REUSE) cycling이 후반 iteration의 마이닝 다양성을 A 12개 중
  2개로 좁혔다 — "12 iteration을 다 썼다"고 "A 12개를 고르게 12번씩 마이닝했다"는 뜻은 아니다.
- A 태스크들이 30B 모델에게 전반적으로 쉬웠다(마이닝 promotion율 95.7%, router yield 대부분 1.0에
  근접) — 더 어려운/실전에 가까운 태스크 코퍼스였다면 채굴되는 스킬의 질(§5의 "비인과적 장식물"
  문제)이 달라졌을 수 있다.

**v0 대비 신규**: SEARCH 구조(archive+router), hypothesis/rewrite 분리(VISTA), transfer-holdout 복리
측정, 검증자 무결성 감사. 유지: 외부 held-out verifier, contract-fuzz, 승격 원장, No OntologyOS/QLoRA.

**다음 단계 (§5 진단에서 직접 도출, negative=pivot이지 terminus 아님)**:
1. **승격 게이트에 인과-ablation 추가** — tool/scaffold 없이(제어군) 같은 code_patch만 재평가해서
   실패하는지 확인한 뒤에만 tool/scaffold를 "원인"으로 인정하고 라이브러리에 승격. 이게 §5가 찾은
   핵심 구멍(vacuous artifact가 patch 성공에 무임승차)을 직접 막는다.
2. **`Library.best_for`의 무매치 fallback 제거 또는 신뢰도 하향** — bug_kind가 정확히 안 맞으면
   차라리 아무것도 주입하지 않는 옵션(no-augmentation)을 fallback으로 두고, 성능을 비교.
3. **`improve.sample_tasks`의 cycling을 회전(rotate)으로 교체** — A 전체가 이미 승격된 뒤에도 매
   iteration 다른 부분집합을 마이닝하도록 (v0 REUSE 범위 밖이라 별도 변경 필요, 이 런에서는 하지
   않음).
4. 1-3을 적용해 **재실행**하고, 그래도 B가 안 오르면 이건 "memory in a costume"에 대한 더 강한 실증
   (인과-검증까지 거쳤는데도 전이가 없다는 뜻)이 되고, 오른다면 이번 negative가 진짜 원인(비인과적
   오염)이었음을 확증하는 것이 된다. 어느 쪽이든 masterplan / self-observation log에 반영.
