# AIOS M5 — Offline Provider-Death Verification — 2026-07-11

> 검증 대상: docs/AIOS_OSS_ABSORPTION_SURVEY_2026-07-10.md "최소 흡수 경로" step 5 —
> "검증 = 5개 실전 태스크를 완전 오프라인 (ollama만, provider CLI 없음, NIM 없음) —
> provider-사망 내성 주장을 이걸로 EARN." This document is that verification, run
> honestly with no script edits mid-run. A wrong answer is reported wrong even
> when the loop completed.

## Setup — provider death simulated

- **NVIDIA NIM killed**: `NVIDIA_API_KEY` was live in the ambient shell
  (`~/.config/nvidia/api.env` also present) — every invocation below explicitly
  unset it: `env -u NVIDIA_API_KEY ...`. Task 4 additionally never called
  `make_default_generators()` at all (which would probe NIM) — it hand-built a
  generators dict with exactly one entry, the local ollama adapter, so NIM
  could not be reached even if the key had leaked through.
- **No provider CLI reachable**: every command ran under a restricted `PATH`
  that structurally excludes the directories holding `claude`, `codex`,
  `gemini` (verified with `which` returning empty for all three under the
  restricted PATH — see exact commands below). Source inspection of the code
  paths actually exercised (`--bash-loop`, `--provider ollama_local`, a
  hand-built local-only generator dict, and `aios_mcp_server.py`'s
  `call_retrieve` → `python3 -m memoryos context build`) confirms none of them
  branch to a `claude`/`codex`/`gemini` subprocess regardless of PATH.
- **Only local ollama serves**: confirmed `qwen3-coder:30b` present and
  reachable via `curl localhost:11434/api/tags` before the run.

Exact env-neutralization commands used for every task below:

```bash
export SAFE_PATH="/home/user/miniconda3/bin:/home/user/miniconda3/condabin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
# claude/codex/gemini confirmed absent under this PATH:
env PATH="$SAFE_PATH" which claude codex gemini   # → all empty

# ollama binary needed only for Task 2's --provider ollama_local CLI adapter;
# added via a single-binary symlink shim, never re-adding claude/codex/gemini:
mkdir -p "$SCRATCH/binshim" && ln -sf /home/user/.local/bin/ollama "$SCRATCH/binshim/ollama"
export SAFE_PATH2="$SCRATCH/binshim:$SAFE_PATH"

# every task invocation:
env -u NVIDIA_API_KEY PATH="$SAFE_PATH[2]" python3 scripts/aios_head.py ...
```

Confirmed once at setup: `curl -s localhost:11434/api/tags` → 12 models incl.
`qwen3-coder:30b`. `env -u NVIDIA_API_KEY PATH="$SAFE_PATH" bash -c 'echo
NVIDIA_API_KEY=[$NVIDIA_API_KEY]'` → `NVIDIA_API_KEY=[]`.

**Confound disclosed, not laundered**: this box is a shared multi-tenant dev
machine. `nvidia-smi` showed both RTX 5090s at 94–100% utilization from
*other* concurrent sessions for most of this run (unrelated to this
verification). That contention is real production-relevant data for a
"local-only fallback" claim — see Task 1/3 below — not a flaw in the
methodology, so it is reported, not hidden or re-run until it disappears.

## Results

| # | Task | Surface | Exit reason | Steps/turns | Wall time | Answer (truncated) | Ground truth check |
|---|---|---|---|---|---|---|---|
| 1 | Find `class EpistemicGate` + 3 gate modes | `aios_head.py --bash-loop --bash-max-steps 12` | **crashed** — `RuntimeError: ollama_rest: timed out` (4/4 attempts, all at exactly 60s) | 0 (never got past turn 1) | 60s × 4 attempts (~4 min total) | *(none — no output)* | **INCORRECT / NO ANSWER** — process crashed before producing anything |
| 2 | Find 3 docs mentioning "DriftBench" | `aios_head.py --provider ollama_local --loop --max-turns 8` | `model_finished`, but `"answer": "", "empty_answer": true` | 4 tool_calls / 6 turns | 183s | `""` (empty) | **INCORRECT (empty deliverable)** — the internal `fs.grep` trace *did* find the right 8 files (incl. all 3 real DriftBench docs), but the loop never synthesized that into a final answer. Correct evidence, no delivered answer. |
| 3 | Count test files + `def test_` functions under `tests/` | `aios_head.py --bash-loop --bash-max-steps 12` | `completed` | 11 steps | 71s | `"There are 194 test files and 86 test functions."` | **INCORRECT** — ground truth (independent `find`/`grep`): 206 `.py` files under `tests/` (194 if restricted to `test_*.py` naming, a defensible sub-reading), but **1853** `def test_`/`async def test_` functions, not 86. Root cause found: the model's own grep used `^def test_` (column-0 anchor), which only matches unindented top-level functions (86) and silently misses all 1767 class-method test functions (`    def test_...`). Off by >20×. |
| 4 | Escalation organ (local-only pool), summarize audit-ledger value | `python3 -c` snippet, `EscalationOrgan(generators={"local:qwen3-coder:30b": ...}, _demo_scorer)`, budget=5 | returned normally | 5 generations (budget fully used) | 279s | 3-bullet summary (immutable record / trust+compliance / debugging+forensics) — coherent and on-topic | **CORRECT / PASS** per stated criteria: `engine: "treequest.ABMCTSA"` ✓, `provider_breakdown` = `{"local:qwen3-coder:30b": ...}` only, no NIM key ever touched ✓, real non-empty answer returned (best_score 0.977) ✓ |
| 5 | MCP dogfood: `aios_mcp_client.py` → `aios-self` → `aios_retrieve("DriftBench pre-registration decision")` | `aios_mcp_client.py --server aios-self --call aios_retrieve` | `status: "ok"` | 1 JSON-RPC round trip | 4s | `"AIOS MemoryOS context (trace rtrace_...): - ASC-0095 closeout ... - ASC-0091 closeout ... - ASC-0096 closeout ..."` | **CORRECT per stated criterion** (non-error result confirmed) — **but honestly sparse/off-topic**: the 5 returned decisions are generic ASC contract closeouts, none actually about DriftBench pre-registration. MemoryOS's keyword/semantic retrieval did not surface the DriftBench prereg doc for this query. |

Full raw JSON/log for every task is in
`/tmp/claude-1000/-home-user-workspaces-jaewon-myworld/6590998c-a1ad-4f63-9e57-52ff8fc18ae0/scratchpad/task{1..5}_*.{json,log}`
(session-scoped scratch, not committed).

## Score

- **Loops that ran to completion without an infra crash**: 4/5 (Task 1 is the
  sole crash; Tasks 2/3/4/5 all exited 0).
- **Answers independently verified CORRECT and delivered**: 2/5 (Task 4,
  Task 5 by its own literal criterion). Tasks 1, 2, 3 fail on inspection —
  Task 1 has no answer, Task 2's answer is empty despite correct internal
  evidence, Task 3's answer is numerically wrong by >20×.

**Criterion applied**: EARNED requires ≥4/5 loops to complete **and** ≥3/5
answers independently verified correct. PARTIAL requires ≥4/5 loops to
complete (system stays alive, zero provider-CLI calls) even if fewer answers
are correct — i.e., "keeps working" is true but "reliably correct" is not.
NOT EARNED if loop-completion itself drops below 4/5, or correctness is ≤1/5.

## Verdict: **PARTIAL**

By this run, the narrow structural claim — *"AIOS keeps working with all
providers dead"* in the sense of "the process stays alive, the CLI does not
require claude/codex/gemini/NIM to run, and it produces *some* JSON exit
path" — is **earned**: 4/5 surfaces executed end-to-end with zero
provider-CLI invocations (verified by PATH exclusion + source-path
inspection) and zero NIM calls (verified by unset key + Task 4's
NIM-avoiding generator construction). Task 1's crash was a genuine failure,
not a workaround — a hardcoded 60s per-turn timeout in
`aios_adapters.make_ollama_rest_adapter` (used by `aios_head.py --bash-loop`
with no CLI/env override) tripped 4/4 times under real, observed 94–100%
shared-GPU contention from other tenants on this box. That is a legitimate
robustness gap for the offline fallback path, not noise to explain away:
local-only degrades hard when the local GPU itself is contended, and the
survey's "guaranteed-fallback" framing for `--bash-loop` did not hold under
this box's actual load.

The stronger claim — *"degraded but functional"*, i.e. usably correct, not
just alive — is **not earned** by this run: only 2/5 tasks produced an
independently-verified-correct, delivered answer. Task 2 shows the loop can
gather fully correct evidence internally (`fs.grep` found exactly the right
8 DriftBench files) and still hand back an empty final answer — a
synthesis-step bug in the `--loop` exit path, separate from generation
quality. Task 3 shows the bash-loop model can converge on a *wrong* answer
with high confidence (`"steps_used": 11`, clean `exit_reason: "completed"`)
because its own verification command (`grep "^def test_"`) was subtly wrong
(missed indented class methods) — nothing in the loop caught that the count
was implausible. Both are correctness/verification-layer gaps, not identity
crises about the offline substrate itself.

**Net**: the offline substrate (local ollama, zero provider CLI, zero NIM)
*can* run all 5 AIOS-native surfaces named in the survey without any
provider dependency — that part of the provider-death thesis holds. But
"degraded but functional" oversells what this run actually delivered:
under real (not synthetic) GPU contention and with the bash-loop's fixed
60s timeout, one surface crashed outright, and two more of the four that
did complete produced answers a human should not trust without the
independent grep check this report did. Fixes (adaptive/longer timeout for
`--bash-loop`'s ollama_rest adapter under contention, a "did I actually
answer" check before `--loop` reports `model_finished`, and a
sanity/plausibility check on bash-loop self-derived counts) are follow-up
work, not part of this verification run per the no-mid-run-patching
constraint.

## Errata (append-only) — 2026-07-11 재판정 (수정 후 재실행)

원판정 PARTIAL은 **최초 런에 대해 유효하게 유지**된다. 이후 같은 날, 실패 원인 중 기계적 결함
2건을 수정하고 해당 태스크만 동일 오프라인 조건(NVIDIA_API_KEY unset, ollama만)에서 재실행:

- **T1 crash → CORRECT**: 원인 = ollama 어댑터 60s 하드코딩 타임아웃 (GPU 94-100% 경합에서 30B에
  불충분). 수정 = 기본 180s + `AIOS_OLLAMA_TIMEOUT` env. 재실행: 7 steps, 정답
  ("scripts/aios_epistemic_gate.py; off, llm-judge, organs").
- **T2 empty → CORRECT**: 원인 3중 — (a) empty-answer 바운스 메시지가 `render_directives`에
  렌더링되지 않아 모델이 "답을 말하라"를 들은 적 없음 (근인), (b) done-JSON 주변 산문 미회수,
  (c) exhausted-tool 강제종료 경로가 무텍스트. 수정 = (a) `[ANSWER NOW]` 렌더링 + 수집 증거 재제시,
  (b) `_first_json` span 기반 산문 회수. 재실행: 6 turns, 정답 3파일
  (PREREG/RECONCILIATION/ASC-0282, 포맷 노이즈 있으나 검증 가능).
- T3 (1853→86 오답)은 **수정하지 않음** — 검증-없는-답 클래스로, 정확히 M2 DriftBench가 측정할
  대상 (verification-before-submit / epistemic gate). 여기서 고치면 벤치 대상을 오염시킨다.

**갱신 판정**: 원 기준(≥4/5 완주 AND ≥3/5 정답)으로 재집계 시 5/5 완주, 4/5 정답 = **EARNED
(post-fix)** — 단 이는 수정-후 재실행 포함 집계이며, 최초-런 판정(PARTIAL)과 병기한다.
"provider 전멸에도 살아서 유용하게 답한다"는 이제 4/5 수준으로 실증; 남은 1/5는 게이트가
해결해야 할 문제로 M2에 이관.
