# World-Grounding Brief — 2026-07-10 (agent-OS / AGI frontier)

> 작성: 리서치 subagent (WebSearch, 2026-07-10). 마스터플랜(`AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md`)의
> 외부 접지 원본. 요약 아님 — 원문 보존.

## 1. Agent OS / "LLM OS" landscape

- agiresearch/AIOS: alive but academic — COLM 2025 paper, kernel updated 2026-06-22, Cerebrum SDK (Apr 2026) Agent Hub. (github.com/agiresearch/AIOS, arxiv.org/html/2503.11444v1)
- **OpenClaw = story of the year**: Peter Steinberger's local-first personal agent (renamed Jan 2026), most-starred repo on GitHub (~150k by Feb; up to 346k+ mid-2026, counts vary); Steinberger joined OpenAI 2026-02-14; OpenClaw Foundation for stewardship. 로컬-퍼스트 any-model 개인 agent OS 카테고리의 수요를 대규모 실증. (en.wikipedia.org/wiki/OpenClaw)
- OpenAI consolidated: Assistants API dies 2026-08-26; AgentKit Agent Builder deprecated 2026-06-03 (gone Nov 30) → code-first Agents SDK + ChatGPT Workspace Agents. 빅랩 플랫폼 층 churn 실재. (developers.openai.com/api/docs/deprecations)
- Anthropic ecosystem = de facto agent runtime: Agent SDK 검색수요 ~50,000% YoY; Agent Skills 오픈 표준 (agentskills.io, 2025-12-18) ~40 호환 제품(Codex, Copilot, Cursor, Gemini CLI 포함); Vercel skills.sh 600k skills (2026-06); Managed Agents + vertical MCP connectors (Code with Claude Tokyo).
- Google agent-first at I/O 2026: Antigravity 2.0 standalone desktop ("home for agents", parallel orchestration, scheduled tasks); Gemini CLI → Antigravity CLI 전환; Jules/Mariner를 Gemini agent stack으로 통합. (blog.google, developers.googleblog.com)
- Microsoft: Windows에 Agent OS 내장 (Entra Agent ID = agent identity, sandboxed Agent Workspaces); W3C WebMCP를 Google과 공저. LangChain: $125M Series B at $1.25B (2025-10), LangGraph 1.0, 90M monthly downloads, Fortune 500의 35%.

## 2. Agent memory

- Graph memory = production 패턴 (taxonomy survey arXiv 2602.05665; GAM 2604.12285); vector+BM25+entity 멀티시그널 검색이 표준.
- **LoCoMo 사실상 포화** — Mem0 91.6, Evermind 93.05; 프런티어는 forgetting·hallucinated-memory(HaluMem)·cross-scenario 일반성으로 이동. (mem0.ai/blog/state-of-ai-agent-memory-2026, arXiv 2604.20006, 2606.04315, MemTrace 2606.17328)
- **겸허 결과**: Letta Filesystem — 파일에 히스토리 저장 + grep만으로 LoCoMo 74.0%, 여러 전문 메모리 라이브러리를 이김. Letta는 git-backed "context repositories"(MemFS)로 피벗, server-side sleep-time agents → client-side subagents로 교체 중. (letta.com/blog/letta-filesystem, /our-next-phase)
- Sleep-time/dream consolidation = named research direction: Letta sleep-time compute, self-consolidation (2602.01966), continuum memory (2601.09913).
- Mem0 $24M (~48K stars); Zep = temporal-KG 니치; 포지셔닝 분화 — Mem0=bolt-on, Zep=temporal facts, Letta=자기 메모리를 페이징하는 runtime.
- 문헌 비판: "contextual agentic memory is a memo, not true memory" (2604.27707) — retrieval-augmented memory ≠ learning.

## 3. MCP + agent protocols

- MCP → Linux Foundation 산하 Agentic AI Foundation 기증 (2025-12). ~10,000+ public servers, registry ~9,652 (2026-05), ~97M monthly SDK downloads, 41% orgs production. 신 spec 2026-07-28 (stateless, enterprise).
- A2A (Linux Foundation) 150+ orgs, 1년차에 enterprise production. 패턴: MCP=tools/data, A2A=agent collaboration.
- ACP (Zed) = editor-agent seam 승자: 50 agents (2026-06), JetBrains 전면 채택, ACP Registry (2026-01: Claude Code, Codex CLI, Copilot CLI, Gemini CLI 등재).

## 4. AGI progress + frontier models

- 최고 압축 릴리즈 사이클: Opus 4.7 → 4.8 (5/28) → **Claude Fable 5 (6/9, Mythos-class, always-on adaptive thinking, 1M context)** → Sonnet 5 (6/30); GPT-5.5 Terminal-Bench 선두; Gemini 3 Pro ARC-AGI-2 77.1%, Gemini 3.5 Flash at I/O 2026.
- **전례 없는 거버넌스 사건**: Fable 5 + Mythos 5, 2026-06-12 미 상무부/BIS 수출통제 지시로 정지 (AI 모델 직접 적용 최초; Amazon 신고 jailbreak 촉발), 2026-07-01 신규 사이버보안 classifier와 함께 복원. **Provider 종속 리스크가 이론이 아니라 실증됨.** (Forbes, The Hacker News)
- 중국 오픈웨이트, Nvidia 없이 학습: DeepSeek V4, GLM-5.1, Qwen 3.6 — Huawei Ascend 학습, 일부 카테고리에서 서방 closed와 경쟁.
- **AGI 병목 합의 = continual learning + long-term memory**: "all that may be needed to reach AGI is a breakthrough in continual learning" (ai-frontiers.org "AGI's Last Bottlenecks"); a16z 동일 라인; hippocampal explicit memory position papers (2606.11245). 지배적 견해: AGI 미달성.
- METR time horizons 가속: 2023년부터 ~4.3개월 배가, 2024년부터 ~3개월 (Time Horizon 1.1, 2026-01); month-long tasks 2027년 가능성. (metr.org)

## 5. Multi-agent orchestration + computer use

- **헤드라인 격차**: OSWorld 12%(2024)→~85%(2026-06, Opus 4.8 OSWorld-Verified 83.5%) BUT **OSWorld 2.0** (장기지평; median 1.6 human-hours)에서 최고 시스템 **20.6%**. (arxiv 2606.29537)
- **GAIA2 (Meta ARE)**: 1,120 비동기 스마트폰 시나리오 + 주입 이벤트; frontier ~42%, no system dominates; 더 많은 reasoning이 시간민감 태스크에서 오히려 악화. (2602.11964)
- SWE-bench Verified 거의 해결 (Opus 4.7 87.6%) → SWE-bench Pro (64.3%), Terminal-Bench, Tau²-Bench, METR HCAST로 이동.
- 신규 장기지평 벤치 증식: Odysseys (web, 2604.24964), WeaveBench (hybrid, 2606.09426) — 단기 점수가 진보를 과장한다고 필드가 명시 인정.

## 6. Local / sovereign AI

- 오픈웨이트 랙 = closed frontier 대비 **~4개월 / 8 ECI points** (Epoch, 2026-01~05 window). (epoch.ai)
- RTX 5090 1장(32GB): 30B급 40-66 tok/s; 2026 추천 Qwen3.6-35B-A3B, Gemma 4 31B, Mistral Small 4; Llama 4 Scout(109B MoE) Q4; gpt-oss-120b 최대 256 tok/s (NVIDIA MoE+offload). Dual 5090/64GB = 70B dense Q4 또는 gpt-oss-120b full-VRAM.
- 프런티어 오픈웨이트 (Kimi K2.6, GLM-5.1, DeepSeek V4)는 dual-5090 초과; EXO식 분산 VRAM pooling이 워크어라운드.
- OpenClaw는 hosted frontier + local open-weight 겸용 — 로컬-퍼스트 개인 에이전트는 주류 무브먼트.

## What changed since early 2026

1. **프로토콜 중립 거버넌스로 통합** (MCP+A2A Linux Foundation, ACP registry, Agent Skills 표준). plumbing 전쟁 종료; 독자 프로토콜 = 음의 가치.
2. **로컬-퍼스트 개인 agent OS가 OpenClaw로 대규모 검증** — 그리고 부분 흡수 (창업자 OpenAI행, 재단 관리).
3. **롱-호라이즌 절벽 정량화**: 단기 85% vs 1.6시간급 20.6%; GAIA2 42%. 지속·상태유지·멀티앱 자율성이 공인된 열린 문제.
4. **메모리 저장/검색 커모디티화** (LoCoMo 포화; files+grep이 라이브러리를 이김), **continual learning/consolidation이 AGI 병목으로 등극**.
5. **Provider 리스크 실증**: 수출통제가 세계 최고 모델을 19일간 정지 (6/12–7/1).
6. 빅랩들이 OS 층 자체로 진입 (Windows Agent OS, Antigravity 2.0, ChatGPT Workspace Agents), 동시에 자기 hosted builder를 죽이고 code-first SDK로.

## Implications (solo founder, local-first multi-provider memory-centric agent OS)

**커모디티 — 빌드 금지, 채택**: 메모리 CRUD/검색 (Mem0/Zep/files+grep), 프레임워크 (LangGraph 1.0), 프로토콜 (MCP/A2A/ACP), skills 배포 (600k), 모델 접근 (오픈웨이트 4개월 랙; 멀티 프로바이더 라우팅 = table stakes).

**열린 갭 — 주인 없음**:
- **롱-호라이즌 층**: 85%-단기 vs 20.6%-장기 절벽을 credible하게 닫는 자가 없음. 필요한 것 = durable state, verification gates, provenance, reset-생존 메모리, 시간/일 단위 실패 복구 — 정확히 control-plane + memory-lifecycle 영토. labs(model-centric)도 OpenClaw(channel-centric)도 LangChain(framework-centric)도 소유 안 함.
- **저장이 아니라 행동을 바꾸는 메모리**: consolidation/sleep-time 루프, draft→review→accept 라이프사이클, 망각, 환각메모리 제어 = 살아있는 연구 프런티어이자 공인 AGI 병목. Letta의 server-side sleep-time 후퇴로 부분 공백.
- **Agent 거버넌스/신뢰**: Fable 5 셧다운 + Entra Agent ID → 감사가능성·agent identity·권한·provider-독립이 조달 요구사항화. append-only·contract-governed·provider-agnostic 층 = 차별적. 소버린티는 실증된 필요.

**전략 주의**:
- OpenClaw가 "내 기기의 개인 비서" 마인드셰어 소유 — 거버넌스드·메모리-중심·롱-호라이즌 유기체로 차별화.
- Interoperate or die: MCP servers + ACP agent + Skills-호환 아티팩트로 노출.
- 플랫폼 churn (AgentKit 1년 수명) → 어느 provider surface가 이기든 그 아래의 durable substrate 포지션 (records, memory, verification).

*전체 URL 인용은 세션 기록 + 이 파일 원문 괄호 표기; OpenClaw star 수는 소스 간 상충(30k–346k), 자릿수 참고용.*
