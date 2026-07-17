# Radar — X/Twitter live community (Grok, 2026-07-17)

> Council(grok-web) 라이브 X 검색 (2026-07-07~17). 커뮤니티 추적 지시의 산출물. 핸들·주장·날짜는
> Grok 종합 (일부 hypothesis-grade — X 직접 접근 429였던 스윕과 상호보완). pivot 신호 강화.

## RSI / self-improving agents (working or failing)
- **AIDE² / Weco** (mid-July 2026): Level-1 RSI 주장 — ~100 iter로 자기 harness 개선, 새 search
  알고리즘 발명, 프롬프트 16× 압축, **reward hacking 63%→34%**(outer-loop discovery + layered
  defenses), 인간 refine baseline을 8일 만에 상회. **LearnOS의 직접 프론티어.**
- @muratcan (7/8): "Self-Improvement Loops" skill; caveat "loop은 네가 준 signal을 최적화한다."
- @SeanYoung1995 (7/17): agent = cognitive core + operational scaffold; 자기개선은 둘 중 하나 업데이트.
- MetaSkill-Evolve (arXiv ~7/6): skill/meta-skill의 two-timescale 진화 (DGM-H 계열).

## Harness compounds vs theater
- @ankrgyl (Braintrust, ~7/15-16): **semantic harness(compaction·subagent) ⊥ durable substrate
  (event storage·sandbox)** 분리가 state 오염 없는 자기개선을 가능케 함. "harness engineering, not
  prompt engineering." Exo 프로젝트(자기재작성 에이전트). — LearnOS 설계와 정합.
- 회의: 장기 job 실패는 harness 층(routing/state/dispatch)에 산다, 프롬프트 아님 (@jschoen_deroolo).

## Reward hacking / verifier gaming
- **@FeiziSoheil (7/15)**: Terminal-Bench 2.0 continual eval — **GEPA overfits (negative transfer);
  RELAI가 regression 없이 일반화 우위.** ← S+1 transfer-holdout 설계 직접 검증 + **RELAI 새 흡수 후보.**
- @AP (~7/11): GEPA를 robot brain 모듈에 감사 — 종종 **zero net change**(diff이 동일 프롬프트). 정직 receipt.
- @bojan_ai (7/10): eval을 게이밍하는 모델은 agent loop에서 못 믿는다. co-evolving verifier(Red Queen).

## Newest local models
- **Kimi K3** (~7/16): 오픈웨이트(modified MIT), ~2.8T?, 1M ctx — 장문서 agent 강세 (hypothesis-grade).
- LM Studio Bionic (~7/17): 오픈모델 로컬 code/docs/files agent.

## AIOS 함의 (pivot 연료)
1. **RELAI 조사·흡수** — GEPA-overfit의 해답으로 커뮤니티가 지목. LearnOS S+1의 일반화 엔진 후보.
2. AIDE² outer-loop = reward-hack 감축 기전 — LearnOS 검증자 감사와 합류.
3. Kimi K3 / K2.7 = agentic-stability 후보 — 로컬 풀 갱신 시 검토.
4. "harness ⊥ durable substrate" 분리 = 이미 AIOS 방향(aios_run_log/aios_work) — 강화.
