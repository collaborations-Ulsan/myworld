# OSS Agent-Runtime Absorption Survey — 2026-07-10

> 작성: 리서치 subagent (GitHub API live + web, 2026-07-10). 마스터플랜 M5(Agent-native 실행기)의
> 접지 원본. founder directive: "처음부터 짓지 말고 잘 만든 오픈소스에서 재구성해 AIOS로 편입."

## Ranked 흡수 타깃 top 3 (+1)

1. **nanobot (HKUDS)** — github.com/HKUDS/nanobot — 45,204★, MIT, 순수 Python ~4,000줄, 오늘도 push.
   self-hosted 개인 agent runtime: agent loop, tool registry (files/shell/web/MCP/cron/image/subagents),
   MEMORY.md 메모리, skills, chat bridges, WebUI+terminal. 로컬 vLLM + OpenAI-compat 클라우드 지원.
   **흡수**: 골격 전체 — turn loop·tool registry+schemas·MCP client·skills loader·cron/subagent 패턴
   (하루면 전독 가능). **스킵**: chat bridges, 자체 메모리 (memoryOS 있음).
2. **mini-swe-agent (Princeton/SWE-agent)** — 5,675★, MIT, 2026-07-06 push. ~100줄 agent 클래스로
   SWE-bench Verified >74%; **tool-calling 자체가 없음** — 턴당 bash 블록 1개 → 약한 로컬 모델에서
   최강 견고성 (JSON 파서 붕괴 없음). litellm으로 모든 모델; env 백엔드: local/docker/podman/
   singularity/bubblewrap. **흡수**: bash-only 폴백 루프 + sandbox 추상화 (verbatim vendoring 가능).
3. **smolagents (HF)** — 28,272★, Apache-2.0, v1.26.0 (2026-05-29). CodeAgent = 행동을 JSON이 아닌
   Python 코드로 — 로컬 모델 function-calling 취약성의 또 다른 검증된 우회. sandboxed local python
   executor + MCP. **흡수**: code-as-action 패턴 + 제한된 Python executor. **스킵**: HF Hub 결합.
- **TreeQuest / AB-MCTS (Sakana)** — 554★, Apache-2.0, 순수 Python 라이브러리. 멀티-LLM AB-MCTS:
  ARC-AGI-2에서 최고 단일 모델 대비 ~30%↑. generate/score API에 {로컬 qwen3-coder, NIM 대형} 풀을
  직접 wrap. **founder 지정: 어려운 태스크 에스컬레이션 기관으로 흡수.** 루프 위에 조합되는 라이브러리.

## 기타 후보 요지

- **OpenClaw** — 382,426★ (GitHub 1위), TypeScript 430k+줄, 라이선스 API상 NOASSERTION (문서는 MIT 주장
  — vendoring 전 확인 필수). 로컬 실사용: 14B-32B+ 필요, 소형 모델은 multi-step 루프 실패; Qwen3.6이
  포맷 최적. **코드 말고 개념만**: gateway 설계, ClawHub skills registry (13,700+ skills, SkillSpector
  스캐닝). SKILL.md는 OpenClaw 없이도 소비 가능.
- **OpenHands** — 80,301★; 진짜 보물은 **software-agent-sdk** (MIT): event-sourced state + deterministic
  replay, typed tools + MCP, local↔sandbox workspace 추상화 (arXiv 2511.03690). 로컬 모델 증거 최강:
  Qwen3.6-35B-A3B 1순위 권장 (2026-05), Devstral Small 46.8% SWE-bench-V via Ollama. 무겁지만 패턴 채석장.
- **Goose (Block→Linux Foundation)** — 51,013★, Apache-2.0, Rust. MCP-first (70+ extensions), Ollama 경로
  프로덕션급. MCP-native 설계 검증용; Rust라 코드 흡수는 스킵.
- **Letta** — 23,728★, Apache-2.0. editable core-memory-block 패턴만 차용 (memoryOS 있음).
- **Qwen-Agent** — 16,697★. **Qwen 전용 tool-calling 템플릿+파서만 복사** (qwen3-coder 하네스용).
- **AgentScope 2.0** — 27,713★. engine+sandbox dual-core, async sandboxed tools — sandbox 연구용.
- 스킵: Aider(러너 아님), MS Agent Framework(enterprise), Open Interpreter(Rust화), MetaGPT(stale),
  OWL(라이선스 미설정), agiresearch AIOS(NOASSERTION, 이름충돌 peer — scheduler 아이디어만).

## (g) 툴 레이어 — 수백 개 툴 확보법

1. **MCP 클라이언트 1회 통합** → 공식 registry 9,652 servers (2026-05-24; Glama ~20k). 공식 mcp
   python-sdk 또는 nanobot의 MCP client를 리프트.
2. **Agent Skills 표준(SKILL.md) 로더** (~200줄: frontmatter 읽고 on-demand 주입) → skills.sh
   (~89,753 skills) + ClawHub (13,700+) 개방. skills = prompt+script 폴더 → **function-calling 불필요,
   로컬 모델에 이상적.**
3. 네이티브 built-in은 5-10개만 (bash, file r/w/edit, web-fetch/search, python-exec) — 모든 진지한
   런타임이 이 분할로 수렴. 보안: 서드파티 skill은 ingest 전 스캔 (SkillSpector 선례; skill 공급망
   주입이 2026 활성 공격면).

## (h) 로컬 모델 tool-calling (2026-07)

- 실측 well-formed rate: Llama-3.3-70B ~97% (48GB, dual-5090 적합); **qwen3-coder-30b·Qwen3-32B·
  GLM-5.1-32B·Gemma-4-27B: 93-96%** (상주 모델이 신뢰 밴드); gpt-oss-20b ~85% 최속;
  **gpt-oss-120b는 harmony 포맷 필수** (아니면 붕괴). Qwen3.6-35B-A3B = OpenHands 현 1순위.
- 하네스 트릭: ①vLLM + 모델-매칭 파서 (`qwen3coder` XML 파서 + xgrammar 제약 디코딩; Qwen 코더는
  XML-native > 강제-JSON) ②**컨텍스트 ≥22k** (ollama 4k 기본값이 agent 행동을 조용히 죽임)
  ③tool 턴에서 thinking 끄기 (vLLM 0.19 버그: <think> 안 XML tool_call 드랍) ④Ollama ≥0.5.0 또는
  streaming off ⑤14B 미만은 function calling 금지 — bash-only(mini-swe) 또는 code-as-action(smolagents).

## 최소 흡수 경로 (~1-2주 → aios_head/turn_loop/tools에 융합)

1. **D1-2**: mini-swe-agent 루프 시맨틱을 `aios_turn_loop` 보장-폴백 모드로 vendoring (턴당 bash 1개,
   모든 모델에서 동작); bubblewrap/podman env 추상화를 sandbox로 리프트.
2. **D2-4**: nanobot 전독 (4k줄) → tool registry+schema 패턴과 provider client를 `aios_tools`/`aios_head`에
   흡수 — OpenAI-compat 클라이언트 1개를 vLLM (qwen3-coder-30b, `--tool-call-parser qwen3_coder`,
   xgrammar)과 NIM (`integrate.api.nvidia.com/v1`)에 failover로. 네이티브 툴: bash, file r/w/edit,
   web-fetch/search, python-exec.
3. **D4-6**: MCP client (공식 python-sdk) → registry servers가 툴로; SKILL.md 로더 → skills.sh/ClawHub가
   롱테일 라이브러리로. 기존 기관 (memoryOS, CapabilityOS routing)은 그대로 memory/routing 층.
4. **D7-10**: `pip install treequest` → AB-MCTS를 에스컬레이션 기관으로 wrap: generate-fn 풀 =
   {로컬 qwen3-coder, NIM deepseek-v4/qwen3.5-397b/gpt-oss-120b}, score-fn = Hive verifier.
5. **검증 = 5개 실전 태스크를 완전 오프라인** (ollama만, provider CLI 없음, NIM 없음) —
   provider-사망 내성 주장을 이걸로 EARN.

*전체 URL은 세션 기록; 별표/라이선스/push 날짜는 2026-07-10 GitHub API 실측.*
