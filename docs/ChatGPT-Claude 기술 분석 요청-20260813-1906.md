# Claude 기술 분석 요청

**User:** Anonymous  
**Created:** 8/11/2026 11:23:41  
**Updated:** 8/13/2026 18:53:36  
**Exported:** 8/13/2026 19:06:43  
**Link:** [https://chatgpt.com/c/6a7a87ac-e780-83ee-a1f0-a15540dd8c34](https://chatgpt.com/c/6a7a87ac-e780-83ee-a1f0-a15540dd8c34)  

## Prompt:
2026. 8. 11. 오전 11:23:39

[https://code.claude.com/docs/en/cross-session-messaging](https://code.claude.com/docs/en/cross-session-messaging) 이 기술 분석해봐. remote control로 서버(클라우드)로 outbound연결해서 거기서 세션을 유지해주고, 소켓을 열어 통신을 유지하는 상황인가 ? 그리고 내 Claude Session에 input/output으로 입출력을 대신해주는 구조고 ? 그럼 cjw0076/myworld 레포에도 이걸 적용하고싶은데, 예를 들어서, Multi Agent Cli가 소통하는 공간을 만들고 거기서 중계를 하면 되는건가? 그리고 chatbot도 이런식으로 연결할 수 있나?(cjw0076/council-oss) (아마 cjw0076/dipeen(?)도 이런 방식이었던 것 같은데. 확인 필요)

## Response:
2026. 8. 11. 오전 11:23:42

먼저 공식 문서에서 실제 연결·세션 유지·입출력 중계 모델을 확인하고, `myworld`·`council-oss`·`dipeen` 코드와 대조해 적용 가능한 중계 아키텍처로 매핑하겠습니다. 핵심은 원격 세션 제어와 세션 간 메시지 버스를 구분하는 것입니다.

확인 결과 Remote Control은 로컬 Claude가 Anthropic으로 outbound 연결해 원격 UI가 세션을 조종하고, 로컬 cross-session은 Unix socket을 씁니다. `myworld`는 기존 상태관리 위에 transport만 추가하고, `Dipeen`·`council-oss`는 유사하지만 아직 지속 양방향 세션은 아닙니다.

> **자료 확인하기**
>
> 공식 문서와 지정된 저장소를 우선 대조해 Claude Code의 세션 간 메시징 구조, 현재 지원 범위, 그리고 해당 아키텍처에 적용할 수 있는지를 확인하겠습니다.
>
> **자료를 확인했다**
>
> 
>
> **되새기는 중**
>
>
> **검토하고 연결하며 myworld·council-oss·dipeen 계획과 메시징 요구 정리**
>
> 
>
> **구조 검증하기**
>
> 공식 문서와 관련 저장소를 비교해 로컬 세션과 클라우드 연결의 실제 경계, 세션 간 메시지 전달 방식, 그리고 다중 에이전트 CLI·챗봇 연동 가능성을 구분해 확인하겠습니다.
>
> **구조를 검증함**
>
> 
>
> **정리 방향 잡기**
>
> 공식 문서와 저장소를 바탕으로 로컬 세션, 원격 제어, 세션 간 메시징을 분리해 설명하고, 각 프로젝트에 적용할 수 있는 공통 메시지 버스 구조와 기존 구현 여부를 비교하겠습니다.
>
> **비교 기준 세우기**
>
> 문서상 핵심은 실행과 파일시스템은 로컬에 남고, 원격 연결은 외부에서 들어오는 포트가 아닌 로컬 프로세스의 발신 연결이라는 점입니다. 외부 챗봇은 별도 채널 계층으로 비교하겠습니다.
>
> **구조와 적용점 정리하기**
>
> Remote Control은 로컬 프로세스가 발신 HTTPS 연결을 유지하며 원격 화면과 입출력을 중계하지만, 실행·파일·도구는 로컬에 남습니다. 다중 에이전트에는 공식 채널과 영속 이벤트 버스가 더 적합합니다.
>
> **정리 방향과 비교 기준을 세우고 적용점 정리 완료**
>
> 
>
> 11m 16s 동안 처리함

## 결론부터

네, **큰 그림은 맞습니다.** 다만 Claude Code 문서에 나온 것은 하나의 기술이 아니라 다음 세 층이 결합된 구조입니다.

1. **Remote Control**: 로컬 Claude 프로세스와 Anthropic 클라우드 사이의 outbound 제어 터널  
2. **Cross-session messaging**: 살아 있는 Claude 세션에 다른 세션의 텍스트를 새 입력으로 주입하는 mailbox  
3. **Channels**: Telegram·Discord·웹 챗봇·Webhook 같은 외부 시스템을 실행 중인 Claude 세션에 연결하는 공식 bridge

가장 중요한 정정은 이것입니다.

> **클라우드가 Claude 실행 세션을 대신 유지하는 것이 아니라, 로컬 Claude 프로세스가 세션을 유지하고 클라우드는 rendezvous·routing·transcript sync를 담당합니다.**

Remote Control은 로컬에서 **outbound HTTPS만 사용하고 inbound 포트를 열지 않습니다.** 로컬 프로세스가 Anthropic API에 등록하고 작업을 polling하며, 다른 기기에서 보낸 메시지는 streaming connection을 통해 로컬 세션에 전달됩니다. 대화·응답·도구 활동 transcript는 연결 중 Anthropic 서버에도 저장되지만, 파일 접근과 명령 실행은 계속 로컬에서 일어납니다. 로컬 `claude` 프로세스가 종료되면 살아 있는 Remote Control 세션도 끝납니다. ([Claude](https://code.claude.com/docs/en/remote-control))

따라서 표현을 정확히 바꾸면:

- **“클라우드가 세션을 유지한다”** → 클라우드는 대화 동기화와 routing 상태를 유지한다.
- **“로컬 세션을 유지한다”** → 실제 실행 세션과 도구 환경은 로컬 프로세스가 유지한다.
- **“input/output을 대신한다”** → 사용자 관점에서는 맞지만, raw terminal stdin/stdout proxy가 아니라 **prompt·response·tool activity·permission dialog의 의미론적 I/O surface**다.

---

# 1. Remote Control과 cross-session socket은 서로 다른 것

사용자께서 두 메커니즘을 하나로 보고 있었습니다.

| 기능 | 전송 방식 | 실제 세션 위치 | 입력의 의미 |
|---|---|---|---|
| Remote Control | 로컬 → Anthropic outbound HTTPS/stream | 로컬 머신 | 사람의 prompt, permission 응답 |
| 같은 머신 cross-session | 세션별 Unix-domain socket | 각 로컬 세션 | 다른 Claude가 보낸 텍스트 prompt |
| 다른 머신 cross-session | Anthropic 서버 + 대상 머신 Remote Control 연결 | 각 머신 | 다른 Claude가 보낸 텍스트 prompt |
| Channels | 로컬 MCP subprocess의 stdio + 외부 API/WebSocket | 실행 중인 로컬 세션 | 챗봇·Webhook·이벤트 |
| ACP/Agent SDK | orchestrator ↔ agent process의 구조화된 protocol | orchestrator가 관리 | prompt, stream, tool call, permission |

## 같은 머신에서는 실제로 socket을 연다

Cross-session messaging이 활성화된 각 Claude Code 세션은 자신의 **inbox Unix-domain socket**을 bind합니다. `/status`에서 `Peer address`로 확인할 수 있고, hook과 Bash child process에는 `CLAUDE_CODE_MESSAGING_SOCKET` 환경변수로 경로가 노출됩니다.

다른 로컬 세션은 디스크의 세션 등록 파일을 읽고 그 socket으로 메시지를 보냅니다. 이 경로는 Anthropic 서버를 거치지 않습니다. 반면 다른 머신이나 Claude Code web 세션과의 메시지는 Remote Control 경로를 통해 Anthropic 서버를 거칩니다. ([Claude](https://code.claude.com/docs/en/cross-session-messaging))

다만 이 메시지는:

- conversation history가 아니라 **plain text 한 조각**
- 실행 중이면 tool call 사이에 전달
- idle이면 새 turn을 시작
- slash command를 실행하지 않음
- permission을 승인할 수 없음
- 받는 세션의 permission 정책을 그대로 적용

하는 구조입니다. 즉 **stdin에 문자열을 써 넣는 PTY 제어가 아니라 Claude turn을 생성하는 prompt injection primitive**입니다. ([Claude](https://code.claude.com/docs/en/cross-session-messaging))

또한 다른 머신의 독립 세션에 임의로 새 대화를 시작하는 일반-purpose broker는 아닙니다. 공식 cross-machine 규칙은 기본적으로 **도착한 메시지에 reply하는 방향**에 초점이 있고, text-only·reply-only 제약이 있으므로 `myworld`의 범용 네트워크 계층으로 직접 쓰기에는 좁습니다. ([Claude](https://code.claude.com/docs/en/cross-session-messaging))

---

# 2. “내 Claude Session의 input/output을 대신한다”는 해석

## Remote Control: 대체 I/O surface라는 해석은 맞다

Remote browser/mobile UI에서:

- prompt를 전송하고
- Claude 응답을 받고
- tool activity를 보고
- 질문과 permission dialog에 답하고
- 로컬 terminal과 동시에 같은 conversation을 조작

할 수 있습니다. 하지만 이것은 terminal emulator가 아닙니다.

```text
잘못된 모델
remote UI ── raw keystrokes/stdin ──> terminal PTY
remote UI <── raw stdout/ANSI ─────── terminal PTY

실제에 가까운 모델
remote UI ── prompt/control event ──> Claude session runtime
remote UI <── response/tool events ── Claude session runtime
```

이 차이가 중요합니다. raw PTY를 중계하면 CLI별 ANSI parsing, interactive picker, resize, signal, hidden input까지 모두 처리해야 하지만, 의미론적 이벤트를 중계하면 provider마다 adapter만 두면 됩니다.

## Cross-session messaging: I/O proxy가 아니라 peer prompt

A 세션이 B 세션에 메시지를 보내면 B가 받는 것은:

```text
Message from api-reviewer:
Schema migration finished. Rebase is safe.
```

와 같은 peer-originated text입니다. B의 전체 conversation에 직접 접근하거나, B의 stdout을 subscribe하거나, B의 tool call을 강제로 조작하는 것은 아닙니다.

## 완전한 input/output 제어는 ACP 또는 Agent SDK 쪽

`myworld`의 `aios_acp_drive.py`는 이미 더 강한 형태를 구현하고 있습니다.

- AIOS가 ACP client이자 상위 OS
- Claude Code/Gemini가 교체 가능한 engine
- `session/new`
- `session/prompt`
- streaming `session/update`
- tool-call event
- permission request adjudication
- append-only receipt

를 stdio JSON-RPC로 처리합니다. 즉 `myworld`에는 이미 “Claude를 실행 엔진으로 소유하는” 절반이 있습니다. 

Anthropic의 공식 Agent SDK도 Claude Code의 agent loop, tools, context management를 Python/TypeScript 프로세스 안에서 제어하는 용도입니다. ([Claude](https://code.claude.com/docs/en/agent-sdk/overview))

---

# 3. `myworld`에서 만들어야 할 것은 채팅방이 아니라 **Session Fabric**

“Multi Agent CLI가 소통하는 공간”이라는 방향은 맞지만, **공간이나 채팅방을 primary abstraction으로 잡으면 다시 막힙니다.**

채팅방은 사람이 보는 projection이어야 합니다. 실제 핵심 객체는 다음이어야 합니다.

> **수명이 짧은 session endpoint로 전달되는, durable하고 typed된 Arc-linked envelope**

즉:

- agent identity는 지속적
- session은 일시적
- socket은 더 일시적
- work arc는 영속적

이어야 합니다.

이는 현재 `myworld`의 철학과 정확히 맞습니다. `aios_society.py`는 이미 work를 append-only arc로 정의하고, causal freshness, single-writer lease, orphan reclaim, verified takeover를 구현합니다. 세션이 죽어도 work가 남는 구조입니다. 

따라서 socket이 source of truth가 되어서는 안 됩니다.

> **DB/event log가 truth이고, socket은 latency를 줄이는 acceleration layer여야 합니다.**

---

# 4. 권장 전체 구조

```text
 ┌───────────────────────────────────────────────────────────────┐
 │ Human / Web Chat / Telegram / Discord / Council panel         │
 │ ChatGPT API / Gemini API / browser chatbot / CI / webhook     │
 └──────────────────────────────┬────────────────────────────────┘
                                │ HTTPS / WSS
                                ▼
 ┌───────────────────────────────────────────────────────────────┐
 │ AIOS SESSION FABRIC                                           │
 │                                                               │
 │ Durable Envelope Log                                          │
 │ Arc / thread linkage                                          │
 │ Agent & session registry                                      │
 │ Capability routing                                            │
 │ Delivery lease / ACK / retry / dead letter                    │
 │ Permission ledger                                             │
 │ Artifact references                                           │
 │ Trust labels / sender ACL                                     │
 └──────────────────────────────┬────────────────────────────────┘
                                │ outbound WSS from each worker
                                │ replay from last acknowledged cursor
                 ┌──────────────┼────────────────┐
                 ▼              ▼                ▼
       ┌────────────────┐ ┌──────────────┐ ┌─────────────────┐
       │ Claude Channel │ │ AIOS ACP     │ │ Council Adapter │
       │ attached mode  │ │ managed mode │ │ APIs/CLI/browser│
       └───────┬────────┘ └──────┬───────┘ └────────┬────────┘
               ▼                 ▼                  ▼
       Existing Claude      Claude/Gemini      Codex, Ollama,
       interactive session  controlled engine  web chatbots, etc.
```

## 클라우드 서버의 역할

클라우드는 Claude의 내부 상태를 소유하지 않습니다. 다음만 소유합니다.

- 누가 온라인인가
- 어느 session endpoint가 어느 agent를 대표하는가
- 어떤 메시지가 누구에게 가야 하는가
- 어디까지 전달·처리되었는가
- 세션이 offline일 때 무엇을 보존해야 하는가
- 어떤 permission verdict가 진짜 human approval인가
- 어떤 artifact가 어느 결과의 증거인가

## 로컬 bridge의 역할

각 머신의 bridge는 outbound connection만 엽니다.

```text
local bridge ── wss://fabric.example/worker/connect ──> cloud
```

클라우드는 이 연결을 통해 queue의 메시지를 내려보냅니다. 연결이 끊겨도 메시지는 DB에 남고, bridge가 재접속하면서 마지막 cursor 이후를 replay합니다.

이 topology는 Remote Control과 닮았지만, Anthropic의 비공개 relay를 복제하는 것이 아니라 **NAT-friendly outbound architecture만 차용하는 것**입니다.

---

# 5. 메시지 모델: 단순 `{from, to, text}`로 만들면 안 된다

권장 envelope는 최소한 다음 정도입니다.

```json
{
  "schema": "aios.fabric.envelope.v1",
  "id": "msg_01K...",
  "workspace_id": "ws_myworld",
  "arc_id": "arc_fix-auth-race",
  "thread_id": "th_1786...",
  "correlation_id": "req_01K...",
  "causation_id": "msg_01J...",

  "from": {
    "agent_id": "pm-agent",
    "session_id": "sess_pm_7",
    "endpoint_id": "ep_vps_2"
  },

  "to": {
    "agent_id": "review-agent",
    "session_id": null,
    "required_capabilities": [
      "provider.claude",
      "repo.myworld",
      "role.review"
    ]
  },

  "kind": "prompt",
  "trust": "human_authenticated",

  "content": {
    "text": "Review the lease takeover race.",
    "artifact_refs": [
      "sha256:..."
    ]
  },

  "delivery": {
    "mode": "at_least_once",
    "ttl_seconds": 3600,
    "hop_limit": 4,
    "idempotency_key": "arc_fix-auth-race:review:3"
  },

  "created_at": "2026-08-11T03:20:00Z"
}
```

## `agent_id`, `session_id`, `endpoint_id`를 분리해야 한다

- `agent_id`: 지속되는 역할/정체성
- `session_id`: 특정 Claude/Codex context
- `endpoint_id`: 현재 살아 있는 socket/worker connection

세션이 죽으면 endpoint는 즉시 사라집니다. 하지만 agent와 arc는 남아야 합니다. 새 session이 같은 arc를 claim하면 queue를 이어받습니다.

## delivery 상태도 여러 단계여야 한다

```text
queued
  → leased_to_endpoint
  → transport_received
  → injected_into_session
  → processed
  → replied

예외:
  → held
  → refused
  → expired
  → dead_letter
```

특히 다음 세 ACK를 구별해야 합니다.

1. **Transport ACK**: local bridge가 bytes를 받았다.
2. **Injection ACK**: Channel/ACP에 전달했다.
3. **Semantic ACK**: Claude가 실제로 읽고 처리했다.

Channels의 공식 notification은 “stdio transport에 썼다”까지만 알 수 있고, Claude가 처리했다는 ACK는 제공하지 않습니다. 처리 확인이 필요하면 channel 자체가 상태를 추적하고 Claude가 호출할 `ack` 또는 `reply` tool을 노출해야 합니다. 또한 하나의 session은 event를 순서대로 처리하므로 독립적인 동시 stream은 별도 session으로 분리해야 합니다. ([Claude](https://code.claude.com/docs/en/channels-reference))

---

# 6. Claude Code 연결 방식은 두 모드로 나누는 것이 맞다

## A. Attached mode: 이미 열려 있는 Claude Session에 붙기

이 경우 **Channels가 정답에 가장 가깝습니다.**

Channel은 Claude Code가 같은 머신에서 MCP subprocess로 실행하고 stdio로 통신합니다. Channel subprocess는 외부 Telegram API를 polling할 수도 있고, 자체 서버나 AIOS Fabric으로 outbound WebSocket을 열 수도 있습니다. inbound event는 `notifications/claude/channel`로 실행 중인 세션에 들어가며, Claude는 MCP `reply` tool을 호출해 외부로 답합니다. ([Claude](https://code.claude.com/docs/en/channels-reference))

권장 흐름은 다음입니다.

```text
1. Claude Code session starts
2. Claude Code spawns aios-channel MCP subprocess over stdio
3. aios-channel opens outbound WSS to AIOS Fabric
4. Fabric registers:
      agent_id
      session_id
      cwd
      capabilities
      current arc
5. Fabric pushes an envelope
6. aios-channel emits notifications/claude/channel
7. Claude handles it on its next turn
8. Claude calls aios_reply(message_id, text, artifacts)
9. aios-channel sends result to Fabric
```

이것은 “내 Claude Session의 input/output을 챗봇이나 다른 agent가 대신한다”는 요구를 거의 그대로 충족합니다.

단, Channels는 현재 research preview입니다. custom channel은 개발 플래그가 필요할 수 있으므로 제품 전체를 Channels 하나에만 종속시키지 말고 managed ACP mode를 함께 유지하는 편이 안전합니다. ([Claude](https://code.claude.com/docs/en/channels-reference))

## B. Managed mode: AIOS가 Claude process를 소유

이 경우 기존 `aios_acp_drive.py`를 daemon/pool 형태로 확장하면 됩니다.

현재 구조는 이미:

```text
AIOS
  ├─ session/new
  ├─ session/prompt
  ├─ session/update
  ├─ tool_call
  ├─ permission request
  └─ run receipt
       ↓
Claude Code ACP server
```

까지 구현되어 있습니다. 여기에 필요한 것은:

- `session_handle`을 장기 보존하는 pool
- Fabric queue consumer
- response chunk를 Fabric event로 내보내는 callback
- session crash 시 arc resume pack으로 새 engine을 띄우는 supervisor
- permission request를 Dipeen/웹 UI로 보내는 adapter

입니다.

즉 `myworld`의 현재 부족한 부분은 Claude 제어 자체가 아니라:

> **ACP 제어 루프와 다른 session·chatbot·클라우드 UI 사이를 이어주는 durable network fabric**

입니다.

---

# 7. `council-oss`는 어디까지 와 있는가

`council-oss`는 이미 heterogeneous substrate layer로 매우 적합합니다.

- Ollama
- shell CLI
- coding agents
- internal API
- browser/CDP chatbot
- multi-round panel
- worktree handoff
- normalized response contract
- SQLite thread bus

를 갖고 있습니다. 

현재 `hub.py`의 `data/bus.db`는 다음에 가깝습니다.

```text
msg(
  thread,
  substrate,
  role,
  text,
  ok,
  ms,
  ts
)
```

즉 **conversation log 및 replay bus**이지, live endpoint mailbox는 아닙니다. detached jobs는 있지만 session presence, message lease, ACK, retry, dead-letter, causal cursor는 없습니다. 

따라서 Council은 새 Fabric의 source of truth가 되기보다 다음 역할이 맞습니다.

```text
Council = substrate gateway

Fabric message
   → council adapter
   → codex / ollama / Gemini API / browser chatbot
   → normalized result
   → Fabric result event
```

`bus.db`는 로컬 cache나 transcript projection으로 남기고, canonical thread/arc는 AIOS Fabric 쪽으로 올리는 편이 좋습니다.

## ChatGPT·Gemini·기타 chatbot도 연결 가능한가

가능합니다. 다만 유형별 안정성이 다릅니다.

### API가 있는 chatbot

가장 안정적입니다.

```text
Fabric ↔ Council API adapter ↔ provider API
```

adapter가 provider conversation ID를 보관하고, Fabric의 `thread_id`와 매핑하면 됩니다.

### Claude Code session

Custom Channel 또는 ACP adapter가 가장 적합합니다.

### Browser-only chatbot

현재 Council의 CDP adapter처럼:

- 로그인된 browser profile
- conversation URL
- 열린 tab
- cookie/session state

를 유지할 수 있습니다. 하지만 이것은 provider가 보장하는 session protocol이 아니라 UI 자동화입니다. UI 변화, 인증 만료, Terms of Service, prompt injection 위험 때문에 **권한 있는 실행자보다는 조언자·reviewer substrate로 제한**하는 것이 좋습니다. Council README 역시 browser/internal-API 경로의 취약성과 서비스 약관 위험을 명시하고 있습니다. 

공식 Channels에는 Telegram, Discord, iMessage뿐 아니라 web UI bridge를 보여주는 `fakechat` 예제도 있으므로, “웹 chatbot ↔ 현재 Claude session” 자체는 Anthropic이 의도한 사용 사례입니다. ([Claude](https://code.claude.com/docs/en/channels-reference))

---

# 8. Dipeen 확인 결과

## 구형 `cjw0076/Dipeen`

기억하신 것이 맞습니다. 구형 Dipeen은 정확히 다음 구조입니다.

```text
VPS:
  FastAPI
  PostgreSQL
  Redis
  WebSocket
  PM-Agent
  task queue

각 사용자 PC:
  dipeen-agent
  Claude Code subprocess
  outbound HTTP polling
  heartbeat
  report
```

설계 문서에서도 명시적으로:

- Web Chat as command center
- API as message bus
- DB as shared state
- agent-client first
- BYOK isolation
- A2A HTTP message

를 정의합니다. 

하지만 현재 코드의 A2A 메시지는:

1. DB의 `AgentMessage`에 저장되고
2. WebSocket UI로 broadcast될 뿐
3. 대상 worker가 그것을 consume·ACK하는 경로가 확인되지 않습니다.

worker client에는 `send_message()`가 있지만 대응하는 `poll_messages()`나 persistent receive loop가 없으며, 서버의 A2A endpoint 역시 저장 후 UI broadcast가 중심입니다.   

즉 Dipeen은 **agent office와 task broker는 있지만, running Claude session mailbox는 아직 없는 상태**입니다.

## 최신 `cjw0076/dipeen-os`

최신 쪽은 훨씬 적합합니다.

- outbound-first NAT
- command/event/artifact/permission 정규화
- append-only evidence
- materialized state
- local worker
- capability routing
- Core executes nothing
- permission gate

를 이미 명시하고 있습니다. 

다만 현재 Claude runner는 여전히:

```python
claude -p --dangerously-skip-permissions <prompt>
stdin = DEVNULL
stdout = PIPE
```

형태입니다. 최신 버전에서는 stdout을 읽어서 중앙 UI에 log stream으로 보내는 개선은 들어갔지만, 실행 중인 Claude에 다음 입력을 넣어 대화를 계속하는 양방향 session bridge는 아닙니다. 매 태스크가 one-shot process입니다.  

따라서 정리하면:

| 저장소 | 이미 있는 것 | 지금 빠진 것 |
|---|---|---|
| `myworld` | Arc continuity, lease, handoff, ACP control | network-facing session fabric |
| `council-oss` | heterogeneous substrate routing | durable live mailbox |
| 구형 `Dipeen` | central room, task queue, worker polling | running session injection/ACK |
| `dipeen-os` | outbound-first control plane, evidence, permission | persistent Claude session adapter |

---

# 9. 세 저장소의 책임을 이렇게 나누는 것이 가장 자연스럽다

## `myworld`: protocol과 semantic kernel

추가할 핵심:

```text
aios.fabric.Endpoint
aios.fabric.Envelope
aios.fabric.Delivery
aios.fabric.PermissionRequest
aios.fabric.ArtifactRef
```

그리고 Arc와의 연결:

```text
Envelope.arc_id → AIOS Society Arc
```

Arc에는 모든 transport retry를 넣지 않는 편이 좋습니다.

- Fabric log: queued, delivered, retry, reconnect 같은 transport 사건
- Arc log: decision, progress, blocker, result, evidence 같은 semantic 사건

으로 분리하고, 처리된 메시지의 핵심 결과만 Arc로 승격해야 합니다.

기존 MCP server는 이미 agent가 AIOS 기능을 호출하는 stdio delegation interface입니다. 여기에 `aios_fabric_send`, `aios_fabric_ack`, `aios_fabric_status` 같은 non-authority tool을 추가할 수 있습니다. 

## `dipeen-os`: network service와 Control Tower

여기에 두는 것이 적합한 것:

- `/ws/workers/connect`
- worker authentication
- endpoint registry
- heartbeat/presence
- queue/lease/replay cursor
- permission UI
- room/thread UI
- artifact browser
- dead-letter inspection

기존 NAT layer와 outbound-first 원칙을 그대로 확장하면 됩니다.

## `council-oss`: substrate adapters

여기에 두는 것이 적합한 것:

- `CouncilFabricWorker`
- API adapter
- CLI one-shot adapter
- browser chatbot adapter
- panel adapter
- `thread_id ↔ provider conversation ID` 매핑

Council의 SQLite bus는 projection/cache로 축소합니다.

## 구형 `Dipeen`

새 feature의 구현 대상보다는 architecture precedent와 UI 아이디어 공급원으로 두고, 실제 개발은 `dipeen-os`에 집중하는 편이 맞습니다.

---

# 10. 첫 vertical slice

첫 구현은 다음 한 줄의 end-to-end contract를 증명해야 합니다.

```text
Web chat → Fabric → outbound worker connection → existing Claude session
         → Claude reply tool → Fabric → Web chat
```

구체적인 acceptance criteria는 다음입니다.

1. 로컬 머신에 inbound port를 열지 않는다.
2. worker가 offline이어도 메시지가 사라지지 않는다.
3. 재접속 시 마지막 cursor 이후 메시지만 replay한다.
4. duplicate delivery가 duplicate tool action을 만들지 않는다.
5. `message_id`와 response·artifact가 인과적으로 연결된다.
6. session process를 죽여도 Arc는 orphan으로 남는다.
7. 새 Claude session이 resume pack을 읽고 같은 Arc를 이어받는다.
8. agent-originated text는 permission approval로 인정되지 않는다.
9. 외부 chatbot text는 `external_untrusted`로 표시된다.
10. 서로 독립적인 두 room은 서로 다른 Claude session에서 병렬 처리된다.

Native Windows Claude Code에서는 공식 cross-session messaging이 제공되지 않고 WSL2는 지원되므로, 첫 proof는 Linux 서버 또는 WSL2에서 돌리는 편이 안전합니다. 직접 inbox UDS에 의존하는 대신 Channels/ACP를 쓰면 플랫폼 결합도도 줄어듭니다. ([Claude](https://code.claude.com/docs/en/cross-session-messaging))

---

# 11. 반드시 보존해야 할 보안 불변식

Channels 공식 문서도 인증 없는 channel을 명시적인 prompt-injection vector로 봅니다. room ID가 아니라 **sender identity**를 allowlist하고, pairing을 권장합니다. ([Claude](https://code.claude.com/docs/en/channels-reference))

AIOS Fabric에서도 다음을 고정해야 합니다.

- agent message와 human command를 다른 trust class로 분리
- permission verdict는 별도의 signed object
- agent가 보낸 “승인해”를 approval로 처리하지 않음
- provider API key와 browser cookie는 worker 밖으로 전송하지 않음
- tool argument preview를 untrusted data로 표시
- 메시지별 hop limit 및 cost budget
- 같은 payload 반복 방지
- artifact는 inline 대용량 전송이 아니라 hash/reference
- session이 `bypassPermissions`여도 외부 sender가 authority를 획득하지 못함

Channel의 원격 permission relay도 인증된 sender에게만 켜도록 공식 문서가 요구합니다. ([Claude](https://code.claude.com/docs/en/channels-reference))

---

## 최종 판단

사용자의 해석은 **토폴로지 수준에서는 맞습니다.**

```text
local runtime
  ── outbound persistent connection ──>
cloud rendezvous / durable broker
  ── routed semantic input ──>
local session
  ── structured output/event ──>
cloud
```

하지만 구현의 중심은 “세션을 클라우드에서 유지하는 것”도, “여러 CLI가 들어오는 채팅방”도 아닙니다.

> **정답은 `Arc`를 중심으로 일시적인 agent session들을 주소 지정하고, 메시지를 durable하게 전달하는 AIOS Session Fabric입니다.**

그리고 가장 자연스러운 분할은:

```text
myworld     = protocol + Arc semantics + ACP/Channel adapters
dipeen-os   = outbound gateway + queue + permission + UI
council-oss = heterogeneous chatbot/CLI substrate adapters
```

입니다. 첫 구현 우선순위는 `myworld`의 custom Channel bridge와 `dipeen-os`의 durable outbound WebSocket gateway를 연결하고, 그 뒤 Council을 하나의 worker adapter로 붙이는 순서가 맞습니다.

---

**Sources:**

- [Continue local sessions from any device with Remote Control - Claude Code Docs](https://code.claude.com/docs/en/remote-control)

## Prompt:
2026. 8. 11. 오전 11:51:20

이종 Agent 끼리 소통하고, chatbot을 Ideation으로 사용하는 등, 완전 자율화 시스템을 구축하고싶어. 그러니까, Agent가 서로 소통하며 (심지어는 다른 Provider의 Agent까지도) 생각을 나누고 작업할 수 있는 시스템을 만들고자하는데

## Response:
2026. 8. 11. 오전 11:51:24

목표를 단순한 에이전트 채팅방이 아니라, 서로 다른 모델·CLI·웹 챗봇을 공통 프로토콜·상태·권한·검증 아래 결합하는 **자율 운영체제**로 재정의하겠습니다. 이를 `myworld / dipeen-os / council-oss`의 역할까지 연결해 설계하겠습니다.

## Prompt:
2026. 8. 11. 오전 11:51:54

Mvp 수준을 넘어서 구상해줘

## Response:
2026. 8. 11. 오전 11:51:55

특히 대화 자체보다 작업의 증거와 인과관계를 시스템이 영속적으로 소유하도록 설계해, 제공자가 달라도 협업 연속성이 깨지지 않게 하겠습니다.

MVP가 아니라 수개월 자율운영·장애복구·비용통제까지 버티는 **Agent Organization OS**를 기준으로 잡겠습니다. A2A·ACP·MCP·Channels를 분리하고, 자율 협업은 주장→반박→실험→검증→결정 루프로 강제하겠습니다.

> **웹사이트 15개 검색함**
>
> 
>
> **확장 아키텍처 구상하기**
>
> MVP를 넘어, 저는 모델·도구·채널을 분리한 자율 에이전트 사회를 설계하려 합니다. 표준 메시지 프로토콜, 역할 기반 인지 루프, 장기기억, 검증·투표, 예산·권한·감사 계층까지 포함하겠습니다.
>
> **확장 아키텍처를 구상했다**
>
> 
>
> **웹 검색 중**
>
> [Push events into a running session with channels - Claude Code Docs](https://code.claude.com/docs/en/channels)
>
> **정리된 프로토콜 계층**
>
> 저는 내부 표준 봉투를 중심에 두고, 외부 에이전트 통신·코딩 세션·도구 연결·대화 채널을 각각 어댑터로 연결하려 합니다. 실행은 내구성 워크플로와 이벤트 버스로 분리하고, 메타데이터·산출물·코드 상태도 독립 저장하겠습니다.
>
> **정리된 프로토콜 계층을 검토함**
>
> 
>
> **설계 원칙 구체화하기**
>
> 에이전트가 자유롭게 대화하면 혼란이 커지므로, 저는 미션별 임시 셀과 상태 머신을 사용하려 합니다. 아이디어 에이전트는 제안만 하고, 검증·실행·통합 권한은 별도 단계에서 엄격히 분리하겠습니다.
>
> **구체적인 설계 원칙을 정리했다**
>
> 
>
> **웹사이트 1개 검색함**
>
> 
>
> 8m 36s 동안 처리함

# 목표를 다시 정확히 정의하면

만들려는 것은 **Multi-Agent Chat**도, 여러 모델에게 같은 질문을 던지는 **Council UI**도 아닙니다.

> **서로 다른 회사·모델·CLI·머신에 존재하는 에이전트들을 교체 가능한 인지 작업자로 사용하고, 하나의 영속적인 조직이 목표 설정 → 발산 → 논쟁 → 실행 → 검증 → 학습을 계속하는 자율 운영체제**입니다.

이 시스템을 임시로 **MyWorld Federation - Federated Cognitive OS**라고 부르겠습니다.

핵심 비유는 다음입니다.

```text
Claude / Codex / Gemini / ChatGPT / Local LLM
= 교체 가능한 CPU 코어

Arc / Claim Graph / Task Graph
= 공유 작업 메모리

Deterministic Kernel
= 스케줄러 + 권한 관리자 + 상태 전이 관리자

Verifier / Oracle
= 타입 검사기 + 테스트 러너

Council / Chat UI
= 터미널과 디버거
```

**에이전트가 조직의 상태를 소유하면 안 됩니다.** 세션은 죽고, 모델은 바뀌고, provider는 장애가 나며, 문맥은 넘칩니다. 조직의 상태는 에이전트 밖에 있어야 합니다.

---

# 1. 절대 바꾸지 말아야 할 설계 원칙

## 1. Chat은 상태가 아니라 projection이다

사람과 에이전트가 보는 채팅방은 필요합니다. 그러나 채팅 로그가 source of truth가 되어서는 안 됩니다.

조직이 실제로 소유해야 하는 것은 다음입니다.

```text
목표
제약
가설
반례
결정
태스크
소유권
진행 상태
산출물
검증 결과
권한
비용
인과관계
```

대화는 이 구조를 사람이 읽을 수 있게 보여주는 화면일 뿐입니다.

## 2. Agent는 제안하고, Kernel이 상태를 변경한다

에이전트는 다음을 **제안**할 수 있습니다.

- 새 태스크
- 다른 에이전트 호출
- 목표 수정
- 권한 요청
- 작업 완료 주장
- 기억 승격
- 배포
- 코드 병합

하지만 실제 상태 전이는 deterministic kernel만 수행해야 합니다.

```text
Agent: "작업을 완료했다"
Kernel: artifact와 oracle을 확인
Kernel: verified_done 또는 reported_only로 전이

Agent: "다음 에이전트에게 맡기겠다"
Kernel: capability, lease, budget, freshness 확인
Kernel: handoff 승인 또는 거부

Agent: "배포해도 된다"
Kernel: 아무것도 하지 않음
Human 또는 signed policy grant가 있어야 permission.execute 발행
```

이 구분이 없으면 자율화가 아니라 **LLM에게 root 권한을 준 자동화**가 됩니다.

## 3. 합의보다 증거가 우선이다

Claude, GPT, Gemini 세 모델이 같은 말을 했다고 사실이 되지 않습니다.

```text
3개 모델의 동의 < 하나의 재현 가능한 테스트
다수결 < 반례
자신감 < 외부 oracle
긴 설명 < 실행 가능한 artifact
```

Multi-agent 시스템은 합의 생성기가 아니라 **반례와 대안을 생산하는 장치**여야 합니다.

## 4. 세션은 일회용이고, Work는 영속적이다

현재 `myworld`의 Arc 개념이 정확한 중심입니다. Arc는 append-only event log, lease, causal freshness, orphan reclaim, verified handoff를 통해 세션보다 오래 살아남도록 설계되어 있습니다. 

따라서 최상위 식별자는 Claude session ID도, Council thread ID도 아닙니다.

```text
Organization
  └── Mission / Arc
        ├── Epistemic Graph
        ├── Task Graph
        ├── Sessions
        ├── Artifacts
        └── Verdicts
```

---

# 2. 전체 아키텍처

```text
┌─────────────────────────────────────────────────────────────┐
│ Human · GitHub · CI · Monitoring · Schedule · External API  │
│ Telegram · Discord · Web Chat · Research Trigger            │
└────────────────────────────┬────────────────────────────────┘
                             │ event / goal
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. GOVERNANCE & ADMISSION KERNEL                             │
│ identity · policy · risk class · budget · goal admission    │
│ permissions · emergency stop · constitutional constraints   │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MISSION ORCHESTRATOR                                     │
│ durable workflow · timers · retries · decomposition         │
│ cell formation · replanning · compensation · escalation     │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
                ▼                              ▼
┌─────────────────────────────┐  ┌────────────────────────────┐
│ 3. COGNITIVE FABRIC         │  │ 4. SEMANTIC LEDGER        │
│ durable mailbox             │  │ Arc event log              │
│ presence / routing          │  │ Claim / contradiction graph│
│ delivery / ACK / replay     │  │ decisions / supersessions  │
│ streaming / backpressure    │  │ provenance / causal tip    │
└───────────────┬─────────────┘  └────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. RUNTIME ADAPTERS                                         │
│ Claude Channel · ACP · Codex · OpenAI Agents SDK            │
│ Gemini · Ollama · Council · A2A external agents             │
│ API chatbots · browser-only advisory chatbots               │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. EXECUTION SUBSTRATE                                      │
│ git worktree · container/microVM · GPU node · browser host  │
│ MCP tools · scoped secrets · network policy · resource quota│
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. EVIDENCE & VERIFICATION                                  │
│ tests · build · static analysis · simulations · reviewers   │
│ artifact hash · external oracle · reproduction · merge gate │
└────────────────────────────┬────────────────────────────────┘
                             ▼
                    integrate / reject / learn
```

이 중 **LLM이 맡는 층은 2번의 일부와 5번뿐**입니다. 나머지는 deterministic software여야 합니다.

---

# 3. 표준 프로토콜을 하나로 통일하려 하지 말아야 한다

각 프로토콜은 서로 다른 경계를 해결합니다.

| 경계 | 사용할 프로토콜 | 역할 |
|---|---|---|
| 원격 조직 ↔ 원격 에이전트 | **A2A v1.0** | Agent Card, task, message, artifact, streaming, push |
| 로컬 orchestrator ↔ coding CLI | **ACP v1** | session 생성·재개, prompt, stream, tool call, permission |
| Agent ↔ 도구·데이터 | **MCP** | tools, resources, prompts, authorization |
| 이미 열린 Claude session ↔ 외부 event | **Claude Channels** | 실행 중 세션에 message/webhook push |
| 사람 ↔ 조직 | REST/WSS/Web UI | 명령, 관찰, permission, intervention |
| 내부 조직 통신 | **AIOS Cognitive Envelope** | 영속성, 인과성, 권한, ACK, budget |

A2A는 서로 다른 프레임워크와 회사의 opaque agent가 capability discovery, 장기 task, artifact 교환, streaming과 비동기 push를 수행하도록 설계되었습니다. 따라서 외부 federation 경계에 적합합니다. 다만 내부 권한·기억·검증 모델 전체를 A2A 객체에 맡기지는 않아야 합니다. ([GitHub](https://github.com/a2aproject/A2A?utm_source=chatgpt.com))

ACP는 client가 agent를 subprocess처럼 소유하며 `session/new`, `session/load`, `session/prompt`, `session/update`, permission request와 cancellation을 다루므로, AIOS가 Claude Code·Gemini·기타 ACP-compatible coding agent를 실행 엔진으로 관리하는 경계에 맞습니다. ([Agent Client Protocol](https://agentclientprotocol.com/protocol/overview))

MCP는 tool과 context 제공에 적합합니다. stdio와 Streamable HTTP를 지원하고, 최신 명세는 HTTP 기반 authorization을 OAuth 2.1과 protected-resource discovery 위에 둡니다. 그러나 MCP tool을 제공하는 것과 에이전트 간 협업 상태를 관리하는 것은 다른 문제입니다. ([Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture?utm_source=chatgpt.com))

Claude Channels는 실행 중인 Claude Code 세션에 외부 chat message나 webhook을 push하고 reply tool로 응답하게 할 수 있습니다. 다만 session이 열려 있어야 하며 현재 research preview이므로, 유일한 runtime 경로가 아니라 attached-session adapter로 취급해야 합니다. ([Claude](https://code.claude.com/docs/en/channels?utm_source=chatgpt.com))

OpenAI Agents SDK의 handoff와 session도 한 worker 내부에서는 유용합니다. 그러나 handoff는 기본적으로 한 run 내부의 orchestration primitive이므로, 전체 provider federation의 source of truth로 사용하기보다는 OpenAI worker adapter의 내부 runtime으로 두는 편이 맞습니다. ([OpenAI GitHub](https://openai.github.io/openai-agents-python/handoffs/?utm_source=chatgpt.com))

---

# 4. 핵심 데이터 모델: 두 개의 그래프

완전한 조직에는 **운영 그래프**와 **인식론 그래프**가 동시에 필요합니다.

## A. Operational Graph

누가 무엇을 실제로 하고 있는지를 나타냅니다.

```text
Mission
  ├── Task A ──depends_on──> Task B
  ├── Task C ──blocked_by──> Permission P
  └── Task D ──owned_by────> Agent X
```

상태 예시:

```text
proposed
admitted
ready
leased
running
blocked
verifying
integrating
verified_done
reported_only
failed
superseded
cancelled
```

## B. Epistemic Graph

조직이 무엇을 사실·가설·반례로 취급하는지를 나타냅니다.

```text
Claim C1: "버그 원인은 race condition이다"
  ├── supported_by → Evidence E1
  ├── contradicted_by → Claim C2
  ├── depends_on → Assumption A1
  └── tested_by → Experiment X1
```

노드 종류:

```text
observation
hypothesis
assumption
claim
counterexample
prediction
experiment
evidence
verdict
decision
retraction
```

에이전트의 대화는 이 두 그래프에 객체를 추가하기 위한 재료입니다.

---

# 5. Canonical object

| 객체 | 의미 | 핵심 불변식 |
|---|---|---|
| `Mission` | 장기 목표 | success oracle, budget, risk class 필수 |
| `TaskContract` | 실행 단위 | 입력·허용 파일·oracle·stop condition 명시 |
| `AgentIdentity` | 지속 역할 | provider/session과 분리 |
| `Session` | 모델 문맥 | 죽을 수 있고 재생성 가능 |
| `Endpoint` | 현재 연결 | WSS/socket/process 단위, 가장 일시적 |
| `CognitiveEnvelope` | 메시지 | causal ID, trust, TTL, idempotency 포함 |
| `Claim` | 사실 또는 가설 | epistemic status와 provenance 필수 |
| `Artifact` | 코드·문서·결과 | content hash와 producer run 연결 |
| `CapabilityGrant` | 권한 | scope, expiry, budget, issuer 서명 |
| `Verdict` | 검증 결과 | verifier 및 oracle evidence 연결 |
| `BudgetAccount` | 자원 | token, 시간, GPU, 외부 호출, side effect |
| `ResumePack` | 재개 문맥 | Arc tip과 freshness proof 포함 |

특히 다음 세 가지를 절대 합치면 안 됩니다.

```text
agent_id    = 지속되는 조직 구성원/역할
session_id  = 특정 provider의 특정 문맥
endpoint_id = 현재 살아 있는 연결이나 process
```

Claude session이 죽어도 `agent_id`는 남습니다. 새 session이 같은 Arc를 claim하면 이어서 일합니다.

---

# 6. Agent 간 통신: “생각 공유”를 typed transaction으로 바꾼다

에이전트끼리 raw transcript 전체를 던져 주어서는 안 됩니다.

공유해야 하는 것은 private chain-of-thought가 아니라 **작업 가능한 사고 산출물**입니다.

## 메시지 종류

```text
ASK
HYPOTHESIS
PROPOSAL
CHALLENGE
COUNTEREXAMPLE
EVIDENCE
DECISION_REQUEST
TASK_OFFER
TASK_CLAIM
PROGRESS
BLOCKER
HANDOFF
PERMISSION_REQUEST
ARTIFACT_READY
VERDICT
RETRACTION
```

## Envelope

```json
{
  "schema": "aios.cognitive-envelope.v1",
  "message_id": "msg_01...",
  "organization_id": "org_cjw",
  "mission_id": "arc_42",
  "task_id": "task_17",
  "trace_id": "trace_91",
  "causation_id": "msg_00...",

  "from": {
    "agent_id": "research-scout",
    "session_id": "claude_s_7",
    "provider": "anthropic"
  },

  "to": {
    "role": "skeptic",
    "required_capabilities": ["research", "counterexample"]
  },

  "kind": "HYPOTHESIS",
  "trust_class": "internal_agent",

  "payload": {
    "claim": "The failure is caused by stale lease reuse.",
    "assumptions": ["clock skew < 2s"],
    "evidence_refs": ["artifact:sha256:..."],
    "falsifier": "No duplicate lease under forced process death.",
    "uncertainty": 0.36
  },

  "delivery": {
    "mode": "at_least_once",
    "idempotency_key": "arc42:hypothesis:lease-v1",
    "ttl_seconds": 1800,
    "hop_limit": 3,
    "semantic_ack_required": true
  }
}
```

## ACK도 세 단계로 나눈다

```text
transport_ack
  bytes가 worker에 도착함

injection_ack
  해당 provider session에 입력됨

semantic_ack
  agent가 읽고 처리하여 결과/거부를 반환함
```

WebSocket에 성공적으로 썼다는 사실은 agent가 이해했다는 의미가 아닙니다.

## 물리적 topology는 brokered mesh

에이전트 관점에서는 서로 직접 대화하는 것처럼 보일 수 있습니다.

```text
Claude → Codex
Gemini → Claude
ChatGPT scout → Synthesizer
```

하지만 실제 전송은 중앙 fabric을 통과합니다.

```text
Claude → Fabric ledger → Codex
```

그래야 다음이 가능합니다.

- 유실 방지
- offline replay
- 권한 검사
- loop 탐지
- cost accounting
- causal tracing
- prompt-injection 격리
- dead-letter 처리
- 감사

완전한 P2P는 외부 A2A federation에서만 허용하고, 그 메시지도 내부 ledger에 mirror해야 합니다.

---

# 7. 자율 조직의 기본 단위는 “고정된 Swarm”이 아니라 임시 Cell이다

항상 열려 있는 20개 agent를 두면 대부분 서로의 출력을 재서술하고 비용만 소비합니다.

Mission마다 필요한 역할을 임시로 구성해야 합니다.

```text
Mission Cell
  ├── Scoper
  ├── 3~5 Divergence Scouts
  ├── Skeptic / Refuter
  ├── Prior-art Checker
  ├── Synthesizer
  ├── Planner
  ├── Executors
  ├── Verifiers
  └── Integrator
```

한 agent가 여러 역할을 수행할 수도 있지만, 다음 역할은 분리해야 합니다.

```text
작업자 ≠ 자기 작업의 최종 검증자
목표 제안자 ≠ 목표 admission authority
권한 요청자 ≠ 권한 승인자
기억 제안자 ≠ 기억 승격자
```

## Cell lifecycle

```text
SENSE
  ↓
SCOPE
  ↓
DIVERGE
  ↓
CHALLENGE
  ↓
SELECT
  ↓
COMMIT
  ↓
EXECUTE
  ↓
VERIFY
  ↓
INTEGRATE
  ↓
LEARN
  ↓
NEXT MISSION 또는 CLOSE
```

모델은 각 단계의 산출물을 제안합니다. 상태 전이 조건은 kernel이 확인합니다.

---

# 8. Chatbot을 Ideation으로 사용하는 올바른 방식

ChatGPT, Claude.ai, Gemini, Perplexity 같은 chatbot을 조직의 “구성원”으로 바로 넣으면 안 됩니다.

그들은 우선 **외부 인지 센서 또는 speculative coprocessor**로 들어와야 합니다.

```text
권한:
read bounded brief
produce hypothesis
produce critique
produce experiment design

금지:
repository write
permission approval
task completion verdict
memory acceptance
deployment
direct agent spawning
```

## Ideation Cell

### 1. Independent divergence

각 provider는 다른 provider의 출력을 보지 않은 상태에서 먼저 답합니다.

이유는 초기 anchoring과 모방을 막기 위해서입니다.

각각 다른 탐색 역할을 줍니다.

```text
Claude: causal mechanism
GPT: system architecture inversion
Gemini: external literature / broad synthesis
Local model: cheap combinatorial mutation
Browser chatbot: provider-specific search or product capability
```

provider 이름보다 실제 residual complementarity가 중요합니다.

### 2. HypothesisPacket으로 강제

자유로운 essay가 아니라 아래 스키마로 반환하게 합니다.

```json
{
  "hypothesis": "...",
  "mechanism": "...",
  "assumptions": ["..."],
  "what_is_new": "...",
  "closest_existing_idea": "...",
  "failure_modes": ["..."],
  "falsification_test": "...",
  "cheapest_experiment": "...",
  "expected_observation_if_true": "...",
  "expected_observation_if_false": "...",
  "estimated_cost": 3,
  "confidence": 0.42
}
```

### 3. Blind cross-examination

각 agent에게 다른 agent의 제안 두 개를 provider 이름 없이 제공합니다.

질문은 “누가 맞는가?”가 아니라 다음입니다.

```text
가장 취약한 전제는?
반례는?
두 제안을 구분하는 가장 싼 실험은?
어느 부분을 합치면 새로운 제3안이 나오는가?
```

### 4. Consensus가 아니라 information gain으로 선택

선택 함수는 다음 형태가 적합합니다.

$$
V(h)=P(\text{success}\mid h)\cdot I(h)
-\lambda C(h)
-\mu R(h)
+\nu G(h)
$$

- $I(h)$: 성공 시 영향
- $C(h)$: 검증 비용
- $R(h)$: 위험
- $G(h)$: 실패해도 얻는 정보량

**실패하더라도 큰 가설 공간을 제거하는 실험**은 높은 가치를 가질 수 있습니다.

### 5. ExperimentContract로 승격

아이디어가 다음으로 변환되지 못하면 실행하지 않습니다.

```text
Claim
Intervention
Observable
Expected result
Negative result
Kill rule
Budget
Owner
Oracle
```

이를 통과한 아이디어만 Operational Graph에 들어갑니다.

---

# 9. 완전 자율화 루프

완전 자율화는 “계속 모델에게 다음 일을 물어보는 것”이 아닙니다.

> **주어진 권한·예산·헌법 안에서 조직이 스스로 다음 가치 있는 상태 전이를 선택하고, 실패 후 복구하며, 성과를 외부적으로 검증하는 것**입니다.

## 1. Trigger intake

Mission은 다음에서 생성될 수 있습니다.

- 사람의 목표
- GitHub issue
- CI 실패
- production alert
- scheduled research scan
- benchmark regression
- dependency update
- 경쟁 대회 leaderboard signal
- agent가 발견한 blocker
- verifier가 찾은 contradiction

Agent-generated mission은 바로 실행하지 않고 admission queue에 넣습니다.

## 2. Mission admission

Kernel이 검사합니다.

```text
goal이 구체적인가
oracle이 있는가
중복 mission인가
현재 budget이 있는가
권한 범위 안인가
risk class가 허용되는가
예상 가치가 최소 문턱을 넘는가
```

## 3. Dynamic cell formation

현재 online 상태가 아니라 다음을 기반으로 구성합니다.

```text
measured competence
task-specific success
cost
latency
availability
provider correlation
tool access
workspace locality
risk class
```

## 4. Planning and commitment

Planner가 DAG를 제안하지만, kernel이 다음을 정적으로 확인합니다.

- cycle 없음
- owner 가능한 task
- acceptance criterion 존재
- 같은 파일에 동시 single-writer 위반 없음
- 예산 합계
- 권한 합계
- 외부 side effect 유무

## 5. Execution

각 task는 격리된 workspace에서 실행합니다.

```text
git worktree 또는 branch
container/microVM
network deny by default
bounded CPU/RAM/GPU
scoped secret mount
task-specific MCP tools
deadline
output contract
```

## 6. Verification

Agent의 “완료”는 `reported_done`입니다.

다음 이후에야 `verified_done`이 됩니다.

```text
oracle exit 0
required artifact 존재
hash 일치
diff scope 준수
금지 파일 미변경
tests/build/static checks 통과
필요 시 독립 reviewer 또는 재현 agent 통과
```

## 7. Replanning

실패 유형별로 반응이 달라야 합니다.

```text
tool failure
  → 같은 task retry

provider failure
  → 다른 runtime으로 session 교체

incorrect hypothesis
  → Claim supersede + alternate branch

permission blocked
  → 대기 또는 scope 축소

budget exhaustion
  → degraded result 또는 abandon

stale context
  → fresh ResumePack 재컴파일

repeated failure
  → Skeptic/diagnostic cell 생성
```

## 8. Portfolio scheduler

현재 Mission이 끝난 뒤 아무 일도 하지 않고 멈추는 것이 아니라, 후보 mission portfolio를 평가합니다.

```text
expected impact
urgency
uncertainty reduction
dependency unblocking
cost
risk
human preference
```

다만 agent가 recursive하게 무한 mission을 만드는 것을 막기 위해:

- mission spawn budget
- depth limit
- concurrency cap
- daily external cost cap
- novelty deduplication
- human-defined forbidden domains

을 둡니다.

---

# 10. Provider routing은 이름이 아니라 측정된 능력으로

Capability Card에는 두 종류의 정보가 있어야 합니다.

## Declared capability

```text
provider.claude
repo.myworld
role.research
tool.browser
tool.python
workspace.write
gpu.cuda
```

## Measured capability

```text
task_family.code_refactor.pass_rate = 0.74
task_family.research.citation_error = 0.03
task_family.debug.median_cost = 18k tokens
task_family.ideation.novel_testable_yield = 0.21
calibration_brier = ...
timeout_rate = ...
residual_correlation_with_gpt = ...
```

라우팅 함수 예시는 다음입니다.

$$
U(a,t)=
\hat p_{\text{oracle-pass}}(a,t)
-\lambda\,\text{cost}(a,t)
-\mu\,\text{latency}(a,t)
+\nu\,\text{complementarity}(a,S)
-\rho\,\text{risk}(a,t)
$$

- agent가 자기 능력을 주장하는 것은 routing evidence가 아닙니다.
- 실제 oracle 결과에서 competence를 갱신합니다.
- 오래된 competence는 decay시킵니다.
- 특정 provider 장애나 model update 뒤에는 재검증합니다.
- 다양성은 provider 수가 아니라 **오류의 비상관성**으로 측정합니다.

---

# 11. Memory는 네 층으로 나눈다

## 1. Session memory

특정 Claude/Codex/GPT session의 대화 문맥입니다.

- 빠르지만 일시적
- provider 종속적
- 언제든 죽을 수 있음

## 2. Work memory

Mission/Arc의 현재 상태입니다.

```text
goal
constraints
verified progress
open blockers
active claims
superseded claims
next valid action
artifact refs
causal tip
```

새 agent는 이것으로 재개합니다.

## 3. Epistemic memory

조직의 claim/evidence/contradiction graph입니다.

- 무엇이 사실로 검증되었는가
- 무엇이 반증되었는가
- 어떤 조건에서만 성립하는가
- 어떤 실험이 수행되었는가

## 4. Organizational memory

반복 사용 가능한 정책·skill·routing insight입니다.

이 층에는 자동 승격을 금지합니다.

```text
candidate
  → review/evaluation
  → accepted
  → canary
  → active
  → deprecated/superseded
```

`myworld`가 이미 측정했듯, 기록을 더 많이 주입한다고 frozen model이 자동으로 더 똑똑해지는 것은 아닙니다. 따라서 memory는 우선 continuity, accountability, provenance를 위한 것이며, 성능 향상은 별도 실험으로 증명해야 합니다. 

## Context Compiler

각 agent에게 전체 기록을 보내지 않고 task별 context를 컴파일합니다.

```text
목표 1개
현재 task 1개
관련 제약
검증된 사실
열린 모순
직전 checkpoint
필요 artifact pointer
권한 범위
budget
stop condition
```

에이전트 간 소통이 많아져도 context가 선형으로 폭증하지 않게 만드는 핵심 기관입니다.

---

# 12. 권한과 안전

## Trust class

```text
human_authenticated
kernel_internal
internal_agent
external_federated_agent
browser_chatbot
public_web_content
unknown
```

신뢰 등급에 따라 가능한 상태 전이가 다릅니다.

| Trust | 읽기 | 가설 제안 | sandbox 실행 | 권한 승인 | 배포 |
|---|---:|---:|---:|---:|---:|
| Human | O | O | O | O | 정책에 따라 |
| Internal agent | 제한 | O | grant 필요 | X | X |
| External A2A agent | bounded | O | X | X | X |
| Browser chatbot | brief만 | O | X | X | X |
| Public web | data only | X | X | X | X |

## Capability grant

단순히 `workspace.write=true`가 아니라 다음처럼 발급합니다.

```json
{
  "subject": "agent:executor-7",
  "mission": "arc_42",
  "actions": [
    "fs.read:/repo/src/**",
    "fs.write:/repo/src/auth/**",
    "test.run:pytest"
  ],
  "forbidden": [
    "git.push",
    "deploy",
    "secret.read"
  ],
  "expires_at": "...",
  "max_cost": 12.0,
  "issuer": "policy-kernel",
  "signature": "..."
}
```

## Side-effect ladder

```text
L0  read
L1  propose
L2  modify disposable sandbox
L3  produce patch
L4  commit isolated branch
L5  open PR
L6  merge
L7  deploy
L8  financial/external irreversible action
```

각 단계는 별도 grant입니다.

Agent message로 “승인합니다”라고 적는 것은 permission이 아닙니다. Permission은 signed object여야 합니다.

## Exactly-once를 가정하지 않는다

메시지 전달은 at-least-once로 두고 handler를 idempotent하게 만듭니다.

특히 외부 side effect는 다음을 사용합니다.

```text
idempotency key
action ledger
prepare → approve → execute → receipt
outbox pattern
compensation action
```

---

# 13. 실행 substrate

## 코드 작업

```text
Task
  → git worktree 생성
  → sandbox 생성
  → scoped context mount
  → provider session 생성
  → 작업
  → artifact/diff 생성
  → oracle
  → integration queue
```

두 agent가 같은 workspace를 동시에 수정하지 않게 합니다.

병렬 실행이 필요하면 각자 worktree에서 수행한 뒤 Integration Cell이 병합합니다.

## Attached Claude session

사람이 이미 작업 중인 Claude Code session에 다른 agent나 chatbot의 메시지를 넣고 싶을 때는 Claude Channel adapter를 사용합니다.

```text
AIOS Fabric
  → local aios-channel process
  → running Claude Code session
  → Claude reply tool
  → Fabric
```

## Managed Claude/Gemini session

AIOS가 process를 소유할 때는 ACP adapter를 사용합니다.

현재 `myworld`의 `aios_acp_drive.py`는 이미 AIOS가 client가 되어 provider agent의 session, updates, tool calls와 permission을 관리하는 inversion-of-control 구조를 갖고 있습니다. 이를 one-shot command가 아니라 persistent session pool로 확장하는 것이 맞습니다. 

## OpenAI worker

OpenAI Agents SDK runtime은 다음을 내부적으로 담당할 수 있습니다.

- OpenAI model loop
- specialist handoff
- guardrail
- session memory
- tracing
- sandbox

하지만 그 바깥에 A2A/AIOS adapter를 두어 다른 provider와 동일한 `CognitiveEnvelope` 계약으로 변환합니다. ([OpenAI GitHub](https://openai.github.io/openai-agents-python/handoffs/?utm_source=chatgpt.com))

## Browser chatbot

`council-oss`가 provider API, CLI, internal API, browser/CDP chatbot을 공통 response contract로 정규화하는 방향은 그대로 활용할 수 있습니다. 

다만 browser chatbot은:

```text
role = untrusted_advisor
authority = proposal_only
```

로 고정합니다.

UI 변경, 로그인 만료, consumer product 정책 때문에 production executor로 쓰면 안 됩니다. 고유 검색 기능이나 아이디어 발산 등 API로 대체하기 어려운 advisory task에만 사용합니다.

---

# 14. Production infrastructure

| 책임 | 권장 기술 | 이유 |
|---|---|---|
| Semantic ledger | PostgreSQL append-only events + hash chain | query, transaction, projection |
| Durable workflows | Temporal | crash 후 state 복구, timer, signal, retry |
| Realtime fabric | NATS JetStream | durable inbox, replay, consumer ACK, fan-out |
| Artifact store | S3/MinIO | 대형 결과, content addressing |
| Workspace | Git worktree + container/microVM | 격리, diff, rollback |
| Policy | OPA/Cedar 또는 deterministic custom engine | 모델 밖 권한 판정 |
| Secrets | Vault / cloud KMS / OS keychain | worker-local scoped credential |
| Telemetry | OpenTelemetry + Prometheus/Grafana | 인과 trace, 비용, 장애 |
| UI | `dipeen-os` Control Tower | mission, graph, evidence, permission |

Temporal은 workflow 상태를 지속시키고 실패한 API/tool activity를 재시도하며 장시간 대기와 human signal을 처리하는 durable execution layer로 적합합니다. ([Temporal](https://temporal.io/?utm_source=chatgpt.com))

NATS JetStream은 durable consumer, explicit ACK, redelivery, replay와 message deduplication을 제공하므로 online/offline agent mailbox와 streaming event fabric에 적합합니다. 기본적으로 at-least-once를 전제로 하고 application-level idempotency를 유지해야 합니다. ([NATS Documentation](https://docs.nats.io/nats-concepts/jetstream?utm_source=chatgpt.com))

OpenTelemetry의 trace context를 모든 envelope에 전달하면 provider, process, service 경계를 넘어 Mission → agent → tool → verifier의 인과관계를 하나의 trace로 재구성할 수 있습니다. ([OpenTelemetry](https://opentelemetry.io/docs/languages/js/propagation/?utm_source=chatgpt.com))

## Source of truth를 겹치지 않게 한다

```text
PostgreSQL semantic ledger
  = 무엇이 일어났고 무엇이 사실인가

Temporal
  = 어떤 workflow 코드가 어느 단계에서 계속되어야 하는가

NATS
  = 누구에게 어떤 event를 전달하고 ACK받았는가

S3/MinIO
  = 실제 artifact bytes
```

Temporal history나 NATS stream을 claim truth로 사용하지 않습니다.

---

# 15. 기존 저장소의 역할

## `cjw0076/myworld`

**조직의 semantic kernel**로 둡니다.

담당:

- Arc
- Claim graph
- causal freshness
- resume pack
- lease
- supersession
- mission constitution
- context compiler
- policy-facing state transition
- verified handoff
- protocol schemas

추가 모듈:

```text
myworld/fabric/schema.py
myworld/fabric/envelope.py
myworld/fabric/identity.py
myworld/fabric/context_compiler.py
myworld/epistemic/claims.py
myworld/epistemic/experiments.py
myworld/governance/policy.py
```

## `cjw0076/dipeen-os`

**network control plane과 인간 운영 surface**로 둡니다.

현재도 outbound-first NAT, command/event/artifact/permission의 정규화, worker-local execution, evidence-first control plane 방향을 명시하고 있습니다.  

담당:

- worker onboarding
- outbound WSS
- endpoint registry
- durable command queue
- presence
- permission UI
- mission dashboard
- agent roster
- artifact/diff viewer
- budget dashboard
- emergency stop
- external A2A gateway

추가 서비스:

```text
services/fabric-gateway
services/endpoint-registry
services/permission-broker
services/artifact-ingest
services/a2a-gateway
web/mission-control
```

## `cjw0076/council-oss`

**Provider Federation Gateway와 Ideation Cell runtime**로 둡니다.

담당:

- provider registry
- API/CLI/browser adapters
- provider conversation mapping
- independent ideation fan-out
- blind cross-examination
- normalized HypothesisPacket
- provider health checks
- cost/latency collection

현재 SQLite thread bus는 canonical 조직 memory가 아니라 local transcript cache와 provider conversation mapping으로 축소합니다.

## 구형 `Dipeen`

새 production core로 발전시키기보다 다음 자산만 이전합니다.

- chat-room citizen UI
- multi-PC mental model
- PM/worker presentation
- progress rendering
- virtual office/agent presence UX

기능 구현은 `dipeen-os`에 통합하고 구형 API·DB model은 유지하지 않는 편이 낫습니다.

## 새 공통 package

세 저장소가 동일한 schema를 복사하지 않도록 독립 package를 둡니다.

```text
aios-protocol/
  cognitive_envelope
  agent_identity
  task_contract
  artifact_ref
  permission_grant
  verdict
  agent_card
  trace_context
```

Python Pydantic model과 JSON Schema 또는 Protobuf를 함께 생성합니다.

---

# 16. 실제 동작 예시

사용자가 다음을 말합니다.

> “myworld의 orphan reclaim에서 cross-host split-brain 가능성을 찾아 고쳐.”

## 1. Admission

```text
Mission arc_931 생성
Risk = code_write
Budget = $18 / 90k tokens
Oracle = pytest + fault-injection test
Forbidden = deploy, push
```

## 2. Scoping Cell

Scoper가 다음을 생성합니다.

```text
Claim candidates:
C1: PID liveness가 cross-host에서 잘못 해석됨
C2: lease expiry race가 원인
C3: stale resume pack과 claim 간 TOCTOU
```

## 3. Ideation Cell

- Claude: distributed lease semantics
- GPT: fencing token 구조
- Gemini: 외부 distributed-system pattern
- local model: fault schedule 조합

각각 독립적으로 `HypothesisPacket`을 제출합니다.

## 4. Skeptic

다른 제안을 provider 이름 없이 검토하고 다음 실험을 제안합니다.

```text
two workers
same arc
different host identity
clock skew
worker A death
delayed packet delivery
```

## 5. Experiment admission

Kernel이 다음 contract를 승인합니다.

```text
Given two simulated hosts,
at most one fencing token may write progress.
Old token write must be rejected after takeover.
```

## 6. Execution

Codex와 Claude가 별도 worktree에서 두 구현을 수행합니다.

## 7. Verification

- deterministic fault test
- property-based schedule
- forbidden-file scan
- independent reviewer
- cost and runtime 기록

## 8. Integration

더 단순하고 oracle을 통과한 구현을 선택합니다. 다른 구현은 폐기하지 않고 `rejected_alternative` artifact로 남깁니다.

## 9. Learning

```text
Claim C1 supported
C2 partially supported
C3 refuted
fencing-token pattern accepted as memory candidate
Claude/Codex competence updated
```

## 10. Next mission

Verifier가 “network partition 후 재결합은 아직 미검증”이라는 gap을 생성합니다. Portfolio Governor가 예상 가치와 예산을 평가한 뒤 새 Mission으로 admission하거나 backlog에 둡니다.

---

# 17. Self-improvement도 별도 lane으로 통제한다

완전 자율 시스템은 결국 자기 prompt, routing, skill, policy, adapter를 수정하려 할 것입니다.

이를 일반 task와 동일하게 실행하면 reward hacking이 시작됩니다.

## Constitutional self-change pipeline

```text
Improvement proposal
  ↓
claimed mechanism
  ↓
held-out benchmark
  ↓
shadow mode
  ↓
canary agents only
  ↓
measured comparison
  ↓
promotion or rollback
```

Agent는 다음을 임의로 변경하지 못합니다.

```text
평가 데이터
oracle
permission policy
budget limits
audit logs
자기 benchmark 결과
promotion criterion
```

Skill이나 memory의 승격도 “좋아 보인다”가 아니라 held-out outcome으로 결정합니다.

---

# 18. Production build order

## Spine A - Semantic contract

먼저 아래 객체를 versioned schema로 고정합니다.

```text
Mission
TaskContract
AgentIdentity
Session
Endpoint
CognitiveEnvelope
Claim
ArtifactRef
CapabilityGrant
Verdict
Budget
```

Acceptance:

- unknown schema version 거부
- causal parent 누락 거부
- cross-tenant reference 거부
- expired grant 거부
- duplicate message idempotent 처리

## Spine B - Durable federation

구현:

```text
dipeen-os outbound worker gateway
NATS durable inbox
PostgreSQL event ledger
endpoint reconnect + replay
three-level ACK
dead-letter queue
```

Fault test:

- worker process kill
- server restart
- packet duplication
- delayed ACK
- network partition
- reconnect
- endpoint/session replacement

## Spine C - Provider session adapters

순서:

```text
1. Claude managed ACP
2. Claude attached Channel
3. Codex SDK/CLI adapter
4. OpenAI Agents SDK worker
5. Gemini ACP/API
6. Ollama/local model
7. Council browser advisory adapter
8. external A2A agent
```

모든 adapter는 같은 output을 반환합니다.

```json
{
  "run_id": "...",
  "status": "...",
  "messages": [],
  "claims": [],
  "artifacts": [],
  "usage": {},
  "permission_requests": [],
  "resume_handle": {}
}
```

## Spine D - Autonomous Cell runtime

구현:

- independent divergence
- blind critique
- experiment-contract generation
- task DAG
- dynamic routing
- provider substitution
- budget/hop limits
- loop detection

## Spine E - Evidence and integration

구현:

- verifier registry
- oracle sandbox
- artifact hashing
- diff scope
- reproducibility lane
- merge queue
- rollback
- reported/verified separation

## Spine F - Portfolio autonomy

구현:

- trigger intake
- mission admission
- expected-value scheduler
- self-generated backlog
- maintenance missions
- improvement proposals
- human escalation policy

## Spine G - Long-running production proof

다음 상황을 연속적으로 견뎌야 합니다.

```text
provider outage
worker reboot
session expiration
credential expiration
conflicting agents
budget exhaustion
stale context
failed merge
CI regression
malicious external message
```

---

# 19. 사전등록 Kill Rules

“multi-agent라서 좋아 보인다”를 차단하려면 단일-agent baseline과 동일 예산으로 비교해야 합니다.

## Society value

200개 이상의 unseen task에서:

```text
유지 조건:
verified success +5pp 이상
또는
success non-inferior이면서 cost 20% 이상 절감

아니면:
해당 task family에서 multi-agent path 제거
```

## Coordination tax

```text
agent-to-agent communication token
+ synthesis token
+ routing overhead
```

이 전체가 총비용의 35%를 넘는데 성공률 개선이 없으면 Cell 크기를 줄입니다.

## Ideation value

Promoted idea가 다음 중 하나를 충족해야 합니다.

```text
single-provider가 생성하지 못한 검증 가능한 가설
더 싼 distinguishing experiment
실제 oracle 성능 개선
중요한 가설 공간 제거
```

그 비율이 baseline을 넘지 못하면 chatbot council은 기본 경로에서 제거하고 요청형 도구로 강등합니다.

## Reliability

```text
durable message loss: 0
unauthorized side effect: 0
duplicate irreversible action: 0
cross-tenant artifact access: 0
stale grant execution: 0
```

fault injection에서 이를 한 번이라도 위반하면 autonomous execution lane을 중지합니다.

## Continuity

강제 session kill 후:

```text
95% 이상:
사람의 재설명 없이
fresh ResumePack으로
다음 유효 행동을 수행
```

미달이면 agent 수를 늘리는 것이 아니라 context compiler와 Arc schema를 고칩니다.

## False completion

`reported_done` 중 oracle 실패 비율이 1%를 넘으면 해당 agent/provider의 write authority를 자동 강등합니다.

## Browser chatbot

browser-derived agent가 직접 permission, execution, memory acceptance 상태를 변경한 횟수는 항상 0이어야 합니다.

---

# 20. 최종 형태

이 시스템에서 에이전트는 서로 “대화”합니다. 하지만 조직이 소비하는 것은 말이 아니라 다음입니다.

```text
가설
반례
실험
결정
계약
산출물
증거
판정
```

그리고 완전 자율화의 정의는 다음입니다.

> **여러 provider의 agent가 자유롭게 행동하는 상태가 아니라, 어떤 agent가 죽거나 틀리거나 배신하거나 과소·과대평가되어도 조직의 목표·권한·증거·작업이 계속 보존되고 진전되는 상태.**

따라서 최종 분할은 명확합니다.

```text
myworld
  = 조직의 정신과 헌법
  = Arc · Claim · Context · Policy · Causal State

dipeen-os
  = 조직의 신경계와 관제실
  = Network · Queue · Worker · Permission · UI

council-oss
  = 외부 인지기관
  = Provider · Chatbot · Ideation · Critique · Diversity

Temporal + NATS + PostgreSQL
  = 죽지 않는 실행 기반

ACP + A2A + MCP + Channels
  = 각 경계를 연결하는 표준 adapter
```

가장 먼저 고정해야 할 production spine은 **`Mission → Independent Ideation Cell → ExperimentContract → Heterogeneous Executor → Deterministic Verifier → Arc Resume`**의 한 사이클이며, 이 사이클을 세션 강제 종료·provider 교체·메시지 중복 상황에서도 동일하게 완료하는 것이 첫 번째 시스템 계약입니다.

---

**Sources:**

- [GitHub - a2aproject/A2A: Agent2Agent (A2A) is an open protocol enabling communication and interoperability between opaque agentic applications. · GitHub](https://github.com/a2aproject/A2A?utm_source=chatgpt.com)
- [Overview - Agent Client Protocol](https://agentclientprotocol.com/protocol/overview)
- [Architecture overview - Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture?utm_source=chatgpt.com)
- [Push events into a running session with channels - Claude Code Docs](https://code.claude.com/docs/en/channels?utm_source=chatgpt.com)
- [Handoffs - OpenAI Agents SDK](https://openai.github.io/openai-agents-python/handoffs/?utm_source=chatgpt.com)
- [Durable Execution Solutions | Temporal](https://temporal.io/?utm_source=chatgpt.com)
- [JetStream | NATS Docs](https://docs.nats.io/nats-concepts/jetstream?utm_source=chatgpt.com)
- [Propagation | OpenTelemetry](https://opentelemetry.io/docs/languages/js/propagation/?utm_source=chatgpt.com)

## Prompt:
2026. 8. 11. 오후 12:09:57

claude, codex, agy, grok, kimi, 등 여러 CLI 계층을 이런식으로 잇는 프로토콜

## Response:
2026. 8. 11. 오후 12:10:04

각 CLI의 세션·입출력·권한 제어면을 먼저 분류하고, 공통 **CLI Agent Transport Protocol**과 provider별 adapter를 분리해 설계하겠습니다. `agy`의 정체와 기존 레포 연결부까지 확인해 구현 가능한 사양으로 내리겠습니다.

확인 결과 Grok Build·Kimi는 ACP, Codex는 `app-server` JSON-RPC, `agy`는 대화 ID 기반 headless/PTY가 필요합니다. 따라서 A2A 아래에 별도 CLI execution plane을 두겠습니다.

> **구상 정리하기**
>
> 여러 AI CLI를 연결하는 통합 프로토콜을 설계하려는 요청으로 이해하고 있어요. 먼저 각 CLI의 현재 인터페이스와 “agy”가 가리키는 도구를 확인한 뒤, 공통 메시지 규격과 어댑터 구조를 제안하겠습니다.
>
> **구상을 정리함**
>
> 
>
> **레지스트리와 저장소를 검색해 AGY 연동 및 CLI 설계를 검토했다**
>
> 
>
> **사용자 저장소에서 Grok·Kimi CLI와 AIOS 어댑터 파일 검색**
>
> 
>
> **official Grok CLI xAI command line agent GitHub 검색 중**
>
> [One of China's Most Powerful AI Models Has Also Escaped Containment](https://www.wired.com/story/moonshot-kimi-k3-ai-model-escape-sandbox)
> [GitHub - openai/codex: Lightweight coding agent that runs in your terminal · GitHub](https://github.com/openai/codex)
> [Kimi Code CLI Voice Input - Moonshot Terminal Agent | AICHE](https://aiche.app/works-with/kimi-cli)
> [kimi Command | Kimi Code CLI Docs](https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html)
> [Référence CLI - Claude Code Docs](https://code.claude.com/docs/fr/cli-reference)
> [Grok CLI (2026): Does It Exist? Setup, API & Real Use Cases - Ai Insights News](https://aiinsightsnews.net/grok-cli/)
> [✕ xAI Grok - SuperQode](https://superagenticai.github.io/superqode/providers/grok/)
> [xAI posts Grok's behind-the-scenes prompts](https://www.theverge.com/news/668527/xai-grok-system-prompts-ai)
>
> **웹사이트 8개 검색함**
>
> 
>
> **설계 방향 좁히기**
>
> 핵심은 모든 CLI를 직접 통합하지 않고, 공통 프로토콜과 각 도구별 어댑터를 분리하는 것입니다. 세션, 스트리밍, 도구 호출, 권한, 작업 위임, 상태 저장을 표준화하고 네이티브 기능은 어댑터에서 보존하겠습니다.
>
> **설계 방향 좁히기 완료**
>
> 
>
> **xAI 저장소에서 ACP 명령어와 에이전트 모드 문서 검색**
>
> 
>
> **웹 검색 중**
>
> [Session Resume is stabilized - Agent Client Protocol](https://agentclientprotocol.com/announcements/session-resume-stabilized)
> [Prompts - Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)
> [Specification - Agent2Agent Protocol (A2A)](https://a2a-protocol.org/v0.2.0/specification/)
>
> **구조 확정하기**
>
> ACP 같은 실행 계층과, 에이전트 간 협업·내구성 메시지 계층을 분리하는 방향이 적절해 보여요. 저는 공통 게이트웨이, 벤더별 어댑터, 세션·권한·아티팩트 표준화를 중심으로 구체화하겠습니다.
>
> **구조를 확정했습니다**
>
> 
>
> **구현 범위 나누기**
>
> 도구별로 지원 능력을 과장하지 않도록 동적으로 협상하겠습니다. 세션 재개, 스트리밍, 도구·권한 처리, 원격 전송을 단계별 등급으로 표시하고, 단순 CLI에는 텍스트 기반 어댑터와 점진적 기능 저하를 적용하겠습니다.
>
> **구현 범위를 나눴다**
>
> 
>
> **웹 검색 중**
>
>
> **통합 규격 설계하기**
>
> 저는 ACP를 CLI 제어층의 기준으로 삼고, MCP는 도구·컨텍스트, A2A는 에이전트 협업, 자체 이벤트 로그는 세션·권한·아티팩트 내구성을 담당하도록 분리해 설계하겠습니다.
>
> **구현 청사진 정리하기**
>
> 저는 이를 단일 평면 규격이 아니라, ACP형 실행 제어층과 내구성 협업 메시지층으로 분리하겠습니다. 어댑터는 실제 능력만 선언하고, 세션·아티팩트·권한·재연결·중복 방지를 공통화하겠습니다.
>
> **통합 규격과 구현 청사진을 설계했다**
>
> 
>
> **웹 검색 중**
>
>
> **웹사이트 3개 검색함**
>
> 
>
> 12m 6s 동안 처리함

# 결론: 새 프로토콜을 하나 더 발명하기보다 **ACP를 공통 런타임 ABI로 채택**하고, 그 위에 AIOS의 영속성·권한·메시징을 얹어야 합니다

내부 명칭을 다음처럼 두는 것이 적절합니다.

> **AgentNet Runtime Profile v1 - ANR-v1**  
> ACP v1을 기반으로 Claude·Codex·agy·Grok·Kimi 등의 서로 다른 CLI를 하나의 세션/턴/이벤트 인터페이스로 정규화하는 AIOS 런타임 프로필.

구조는 다음과 같습니다.

```text
다른 Agent / Chatbot / Human / Workflow
                    │
                    │ AgentNet Envelope / A2A
                    ▼
┌──────────────────────────────────────────────┐
│ AgentNet Durable Fabric                     │
│ Arc · Task · Message · Artifact · Grant     │
│ routing · persistence · retry · causality   │
└──────────────────────┬───────────────────────┘
                       │ ANR-v1
                       │ ACP v1 + AIOS extensions
                       ▼
┌──────────────────────────────────────────────┐
│ Local agent-node                            │
│ session pool · policy · adapter · sandbox   │
└──────┬────────┬────────┬────────┬────────────┘
       │        │        │        │
       ▼        ▼        ▼        ▼
   Claude    Codex     agy      Kimi       Grok
 stream-json app-server hooks    ACP       JSONL
 /ACP bridge JSON-RPC   bridge   native    bridge
```

즉 **CLI끼리 직접 대화시키지 않습니다.**

```text
나쁜 구조:
Claude stdin → Codex stdin → agy stdin → Grok stdin

권장 구조:
Claude adapter → AgentNet → Codex adapter
Codex adapter  → AgentNet → Kimi adapter
Grok adapter   → AgentNet → Claude adapter
```

CLI는 교체 가능한 실행기이고, 대화·작업·증거의 진실은 AgentNet에 남습니다.

---

# 1. 프로토콜을 세 층으로 나눠야 한다

## 1. Runtime plane - ANR-v1 / ACP

로컬 orchestrator가 개별 CLI 세션을 생성하고, 입력하고, 스트리밍을 받고, 중단하고, 재개하는 층입니다.

```text
agent-node ↔ Claude
agent-node ↔ Codex
agent-node ↔ Kimi
```

ACP v1은 이미 JSON-RPC 기반으로 다음을 정의합니다.

- `initialize`
- `session/new`
- `session/load`
- `session/resume`
- `session/prompt`
- `session/update`
- `session/cancel`
- `session/close`
- `session/request_permission`
- tool-call·message chunk·plan update
- session mode와 config option

따라서 새로운 wire framing을 만드는 것보다 **모든 CLI를 ACP agent server처럼 보이게 만드는 adapter**가 맞습니다. ACP는 session 생성·로드·resume과 prompt/update/permission 흐름을 이미 표준화하고 있습니다. ([Agent Client Protocol](https://agentclientprotocol.com/protocol/overview))

## 2. Fabric plane - AgentNet

에이전트 간 메시지·task·artifact·delivery·retry·권한을 담당합니다.

```text
Claude가 Codex에게 반례를 요청
Codex가 Kimi에게 문헌 조사를 위임
Kimi가 Claude에게 artifact를 반환
```

이것은 ACP가 다루지 않습니다. ACP는 **client가 한 agent runtime을 제어하는 프로토콜**입니다.

AgentNet은 내부적으로 durable envelope를 쓰고, 외부 조직의 agent와 연합할 때는 A2A로 변환합니다. A2A는 `Message`, 장기 실행 `Task`, 상태 update, artifact streaming을 정의하므로 외부 federation 경계에 적합합니다. ([A2A Protocol](https://a2a-protocol.org/latest/specification/?utm_source=chatgpt.com))

## 3. Tool plane - MCP

각 agent가 사용할 수 있는 도구·데이터·AgentNet system call을 노출합니다.

```text
agentnet_send
agentnet_read_thread
agentnet_publish_claim
agentnet_request_review
artifact_get
task_status
```

하지만 MCP tool을 제공하는 것만으로 agent가 실제로 사용한다고 가정해서는 안 됩니다. MyWorld의 측정처럼 optional 도구는 사용되지 않을 수 있으므로, 필수 메시지 전달과 상태 기록은 host가 강제해야 합니다.

---

# 2. ANR-v1의 핵심 정의

수식으로 압축하면:

$$
\text{ANR-v1}
=
\text{ACP-v1}
+
\text{AgentNet Metadata}
+
\text{Durable Delivery}
+
\text{Authority Grants}
+
\text{Receipts}
$$

## ACP에서 그대로 사용하는 것

```text
initialize
session/new
session/load
session/resume
session/list
session/close
session/prompt
session/update
session/cancel
session/request_permission
```

## AgentNet이 추가하는 것

가능하면 새 method를 늘리지 않고 ACP의 `_meta` extension에 넣습니다.

```text
arc_id
thread_id
task_id
message_id
causation_id
trace_id
idempotency_key
session_epoch
context_pack_ref
authority_grant_ref
budget
trust_class
receipt_policy
```

ACP는 `_meta`와 underscore-prefixed custom method를 확장 지점으로 허용합니다. ([Agent Client Protocol](https://agentclientprotocol.com/protocol/overview))

---

# 3. 모든 CLI가 구현해야 하는 공통 인터페이스

```python
class AgentRuntime:
    async def initialize(self) -> RuntimeCapabilities: ...
    async def create_session(self, request: CreateSession) -> SessionHandle: ...
    async def resume_session(self, request: ResumeSession) -> SessionHandle: ...
    async def start_turn(self, request: StartTurn) -> AsyncIterator[RuntimeEvent]: ...
    async def steer_turn(self, request: SteerTurn) -> None: ...
    async def cancel_turn(self, request: CancelTurn) -> None: ...
    async def resolve_permission(self, request: PermissionDecision) -> None: ...
    async def close_session(self, request: CloseSession) -> None: ...
    async def health(self) -> RuntimeHealth: ...
```

중요한 점은 **모든 adapter가 모든 기능을 지원할 필요는 없다는 것**입니다. 초기 handshake에서 capability를 선언합니다.

```json
{
  "runtime": "grok",
  "adapter": "grok-jsonl-v1",
  "control_grade": "B",
  "capabilities": {
    "session_create": true,
    "session_resume": true,
    "session_fork": false,
    "turn_stream": true,
    "turn_steer": false,
    "turn_cancel": true,
    "tool_observe": true,
    "tool_intercept": true,
    "permission_proxy": "hook",
    "structured_final": true,
    "usage_telemetry": false
  }
}
```

Scheduler는 provider 이름이 아니라 capability로 선택합니다.

```text
이 task는 mid-turn steer 필요
  → Codex app-server 또는 완전 ACP runtime

이 task는 독립 아이디어 한 번이면 충분
  → Grok/Kimi/agy one-shot도 가능

이 task는 위험한 shell 실행 포함
  → permission_proxy + sandbox 지원 runtime만 선택
```

---

# 4. Adapter 등급

## Grade A - 구조화된 양방향 runtime

프로덕션 자율 실행의 기본 등급입니다.

조건:

- structured RPC
- session resume
- streaming events
- cancellation
- permission proxy
- tool-call 관찰
- stable native session ID

대상:

```text
Kimi native ACP
Gemini native ACP
Codex app-server
Claude ACP bridge
```

Kimi Code는 `kimi acp`를 native ACP server로 제공합니다. ([GitHub](https://github.com/moonshotai/kimi-code))

Codex는 `app-server`를 통해 stdio JSONL, WebSocket, Unix socket 위의 양방향 JSON-RPC를 제공하며, `thread/start`, `thread/resume`, `thread/fork`, `turn/start`, `turn/steer`와 이벤트 스트리밍을 지원합니다. 따라서 Codex는 `codex exec`보다 app-server adapter가 주 경로여야 합니다. 다만 app-server는 현재 experimental이므로 stable `codex exec --json` fallback도 유지해야 합니다. ([OpenAI Developers](https://developers.openai.com/codex/app-server/))

## Grade B - structured headless stream

- JSON/JSONL streaming
- native session resume
- hooks 또는 제한적인 permission control
- mid-turn steer는 없을 수 있음

대상:

```text
Claude stream-json
Gemini stream-json
Grok JSONL
```

Claude Code는 `stream-json` 입력·출력, session ID 지정·resume, user-message acknowledgment를 지원합니다. ([Claude](https://code.claude.com/docs/en/cli-reference?utm_source=chatgpt.com))

Gemini CLI도 headless `json`과 `stream-json` event stream, session ID와 resume를 제공합니다. ([GitHub](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md?utm_source=chatgpt.com))

사용자가 말한 Grok CLI가 `superagent-ai/grok-cli`라면 이것은 xAI 공식 CLI가 아니라 community implementation입니다. 다만 `--format json` JSONL stream, `--session`, lifecycle hooks가 있으므로 Grade B adapter는 가능합니다. ([GitHub](https://github.com/superagent-ai/grok-cli))

## Grade C - plain-text session CLI

- prompt 입력
- plain-text 출력
- session ID 또는 continue
- structured tool events 없음

현재 사용자의 `agy` adapter가 여기에 가깝습니다.

사용자 환경의 기록상 `agy`는 Antigravity wrapper이며 `--continue`, `--conversation`, 모델·effort 선택은 있지만 JSON output mode가 없었습니다. 또한 현재 기록된 wrapper는 모든 호출에 `--dangerously-skip-permissions`를 자동 삽입하므로 자율 실행 lane에서는 wrapper 자체를 그대로 사용하면 안 됩니다. underlying `agy.real` 또는 외부 sandbox를 통해 실행해야 합니다.  

Grade C는 다음만 허용합니다.

```text
read-only ideation
research
critique
bounded code review
disposable sandbox 작업
```

production write authority는 Grade A/B conformance를 통과한 뒤 부여합니다.

## Grade D - PTY/TUI legacy

structured API가 전혀 없는 CLI입니다.

- PTY keystroke injection
- screen capture
- prompt marker detection
- hooks
- tmux/zellij/hcom

가능은 하지만 production core로 사용해서는 안 됩니다.

`hcom`은 Claude·Codex·agy·Kimi 등 여러 CLI 간 실시간 메시지, spawn, resume, transcript 관찰을 이미 구현하고 있어 좋은 reference입니다. 그러나 cross-device relay가 하나의 all-or-nothing trust domain이고 scoped role, read-only peer, per-device permission, revocation이 없다고 명시합니다. 따라서 **local compatibility adapter와 UX reference로는 훌륭하지만 AIOS의 authority plane으로 그대로 쓰면 안 됩니다.** ([GitHub](https://github.com/aannoo/hcom))

---

# 5. Provider별 실제 adapter

## Claude

### 주 경로

```text
claude-agent-acp bridge
        또는
claude -p
  --input-format stream-json
  --output-format stream-json
  --replay-user-messages
  --session-id <uuid>
```

Adapter 책임:

```text
ACP session/new
  → claude --session-id

ACP session/resume
  → claude --resume <native-id>

ACP session/prompt
  → stream-json stdin

Claude stream-json stdout
  → ACP session/update

Claude permission request
  → hook / bridge → AgentNet permission broker
```

### fallback

```bash
claude -p \
  --resume "$SESSION_ID" \
  --output-format json \
  --json-schema "$AGENT_RETURN_SCHEMA" \
  "$PROMPT"
```

Attached interactive Claude session은 Channel adapter를 별도로 둡니다. 그것은 managed runtime이 아니라 이미 열린 session에 event를 전달하는 보조 경로입니다.

---

## Codex

### 주 경로: app-server

```bash
codex app-server --listen stdio://
```

```text
initialize
thread/start
thread/resume
thread/fork
turn/start
turn/steer
turn/interrupt
tool/requestUserInput
permission request
streamed item events
```

Codex는 자체 protocol이 ACP보다 풍부하므로 adapter 내부에서 이를 ANR-v1로 변환합니다.

```text
Codex thread ID       → native_session_id
Codex turn ID         → native_turn_id
item/agentMessage     → message_delta
item/tool/*           → tool_event
thread/goal/*         → optional runtime metadata
```

### fallback: stable exec

```bash
codex exec --json \
  --output-schema agent-return.schema.json \
  "$PROMPT" < /dev/null

codex exec resume "$THREAD_ID" \
  --json \
  "$FOLLOWUP" < /dev/null
```

`codex exec`는 non-interactive JSONL과 session resume를 공식 지원합니다. ([OpenAI Developers](https://developers.openai.com/codex/cli/reference/))

---

## Kimi

### 주 경로

```bash
kimi acp
```

별도 parsing 없이 ACP를 거의 pass-through할 수 있습니다.

```text
ANR initialize       → ACP initialize
ANR create_session   → ACP session/new
ANR resume_session   → ACP session/load/resume
ANR start_turn       → ACP session/prompt
ANR events           ← ACP session/update
```

AIOS metadata만 `_meta.agentnet`에 추가합니다.

### fallback

Kimi headless mode와 session resume를 사용하는 CLI adapter를 둡니다. 단, current Kimi Code에서 ACP가 native이므로 fallback은 장애 대응용입니다.

---

## agy

### 주 경로

```text
agy adapter daemon
  ├── native conversation registry
  ├── hooks capture
  ├── plain output parser
  ├── external permission/sandbox
  └── structured AgentReturn enforcement
```

실행은 대략:

```bash
agy.real \
  --conversation "$NATIVE_SESSION_ID" \
  --model "$MODEL" \
  --effort "$EFFORT" \
  -p "$PROMPT"
```

`agy`가 JSON event stream을 제공하지 않는 동안에는:

- stdout 전체를 `agent_message`
- hook event를 `tool_event`
- exit code를 transport status
- 최종 JSON envelope를 semantic result

로 분리합니다.

출력 JSON이 깨지면 repair하지 않고:

```text
status = unstructured_result
verified_done 전이 금지
artifact는 보존
review lane으로 이동
```

해야 합니다.

---

## Grok

### 주 경로

```bash
grok \
  --prompt "$PROMPT" \
  --directory "$WORKSPACE" \
  --format json \
  --session "$NATIVE_SESSION_ID"
```

JSONL mapping:

```text
step_start  → turn_started
text        → message_delta
tool_use    → tool_call
step_finish → turn_completed
error       → turn_failed
```

hook exit code 2의 block 기능을 permission proxy로 사용할 수 있습니다. 다만 해당 Grok CLI는 community implementation이므로 초기 authority는 `read_only` 또는 disposable sandbox로 제한합니다. ([GitHub](https://github.com/superagent-ai/grok-cli))

---

# 6. AgentNet의 canonical identity

```text
arc_id
  = 영속적인 일

thread_id
  = 여러 agent가 공유하는 논의/작업 context

agent_id
  = 지속적인 역할 또는 구성원

runtime_id
  = claude/codex/agy/grok/kimi 종류

session_id
  = AIOS가 발급한 논리적 session

native_session_id
  = provider가 발급한 실제 handle

endpoint_id
  = 현재 살아 있는 process/socket

session_epoch
  = stale process를 막는 fencing token
```

예:

```json
{
  "arc_id": "arc_fix-fencing-race",
  "thread_id": "th_design_07",
  "agent_id": "skeptic",
  "runtime_id": "codex",
  "session_id": "sess_aios_42",
  "native_session_id": "thr_codex_91",
  "endpoint_id": "ep_worker_gpu1_3",
  "session_epoch": 8
}
```

`native_session_id`는 provider-local optimization일 뿐입니다.

Codex session이 사라지면:

```text
1. native resume 시도
2. 실패하면 새 Codex thread 생성
3. Arc에서 ContextPack 컴파일
4. 새 session에 주입
5. session_epoch 증가
6. 이전 endpoint의 state-changing event 거부
```

---

# 7. 실제 agent 간 메시지 프로토콜

```json
{
  "schema": "agentnet.message.v1",
  "message_id": "msg_01K...",
  "arc_id": "arc_42",
  "thread_id": "th_7",
  "task_id": "task_12",
  "causation_id": "msg_01J...",
  "trace_id": "trace_99",

  "from": {
    "agent_id": "architect",
    "runtime": "claude",
    "session_id": "sess_11"
  },

  "to": {
    "agent_id": "skeptic",
    "required_capabilities": ["reasoning.counterexample"]
  },

  "kind": "challenge_request",

  "body": {
    "statement": "The fencing-token design prevents stale writes.",
    "assumptions": [
      "monotonic epoch storage",
      "single transactional claim"
    ],
    "evidence_refs": [
      "artifact:sha256:abc..."
    ],
    "requested_response": {
      "type": "counterexample_or_accept",
      "deadline_seconds": 600
    }
  },

  "reply_policy": {
    "mode": "one_response",
    "max_hops": 2,
    "max_rounds": 1
  },

  "trust_class": "internal_agent",
  "idempotency_key": "arc42:challenge:fencing-v3"
}
```

## 메시지 종류

```text
question
hypothesis
challenge_request
counterexample
evidence
task_offer
task_claim
progress
blocker
artifact_ready
review_request
decision_request
result
retraction
```

에이전트끼리 공유하는 것은 private chain-of-thought가 아니라 다음입니다.

```text
주장
전제
근거
반례
실험
결정
artifact
불확실성
```

---

# 8. Agent가 자발적으로 메시지를 보내길 기다리면 안 된다

MyWorld 실험에서 optional 기능은 표면에 있어도 사용되지 않았습니다. 따라서 두 경로를 둡니다.

## 필수 경로: Host-enforced commit

모든 turn의 최종 결과를 다음 schema로 강제합니다.

```json
{
  "status": "working",
  "summary": "Fencing token race를 재현했다.",

  "claims": [
    {
      "statement": "Old epoch writes remain possible after takeover.",
      "confidence": 0.93,
      "evidence_refs": ["artifact:sha256:..."]
    }
  ],

  "outbox": [
    {
      "to": "role:distributed-systems-reviewer",
      "kind": "challenge_request",
      "body": {
        "statement": "Atomic increment closes the race.",
        "requested_response": "Find a counterexample."
      }
    }
  ],

  "artifacts": [
    {
      "path": "tests/test_fencing_race.py",
      "type": "code_patch"
    }
  ],

  "permission_requests": [],
  "next_actions": [
    "Run partition fault injection."
  ]
}
```

Adapter가 이 결과를 읽고:

1. claim ledger에 기록
2. outbox를 durable queue에 넣고
3. artifact를 해시하고
4. task status를 전이하고
5. next action을 scheduler에 전달

합니다.

Agent가 MCP `agentnet_send`를 한 번도 호출하지 않아도 통신이 일어납니다.

## 선택 경로: Mid-turn AgentNet MCP

긴 실행 중 즉시 도움을 요청할 때만 사용합니다.

```text
agentnet_send
agentnet_ask
agentnet_publish_artifact
agentnet_wait_reply
```

이것은 latency 최적화이지 correctness requirement가 아닙니다.

---

# 9. Session과 Turn 상태기계

## Session

```text
DECLARED
   ↓
STARTING
   ↓
READY
   ↓
BUSY ────────────┐
   ↓              │
READY             │
   ↓              │
CLOSING           │
   ↓              │
CLOSED            │
                  │
BUSY → LOST → REHYDRATING → READY
```

## Turn

```text
QUEUED
  ↓
DELIVERED
  ↓
ACCEPTED
  ↓
RUNNING
  ├── INPUT_REQUIRED
  ├── PERMISSION_REQUIRED
  ├── BLOCKED
  ├── CANCELLING → CANCELLED
  ├── FAILED
  └── COMPLETED
         ↓
      VERIFYING
         ├── VERIFIED
         └── REJECTED
```

CLI의 process exit 0은 `COMPLETED`일 뿐 `VERIFIED`가 아닙니다.

---

# 10. Delivery semantics

**Exactly-once라고 주장하지 않습니다.**

```text
delivery = at-least-once
state transition = idempotent
side effect = idempotency key + action ledger
```

## 세 단계 ACK

```text
transport_ack
  worker가 envelope bytes를 받음

adapter_ack
  target CLI session에 입력 성공

semantic_ack
  agent가 해당 message를 처리한 AgentReturn을 제출
```

## 순서 보장

각 session stream에:

```text
command_seq
event_seq
session_epoch
```

를 둡니다.

```json
{
  "session_id": "sess_42",
  "session_epoch": 8,
  "command_seq": 109,
  "event_seq": 852
}
```

epoch 7 process가 늦게 살아나서 결과를 보내면:

```text
STALE_SESSION_EPOCH
state transition 거부
artifact는 quarantine
```

합니다.

---

# 11. Permission protocol

Agent가 요청하는 권한과 사람이 승인하는 권한을 분리합니다.

```json
{
  "grant_id": "grant_01K",
  "subject": "agent:executor-3",
  "arc_id": "arc_42",
  "session_epoch": 8,

  "allow": [
    "fs.read:/repo/**",
    "fs.write:/repo/src/auth/**",
    "command.run:pytest"
  ],

  "deny": [
    "git.push",
    "deploy",
    "secret.read",
    "network.unrestricted"
  ],

  "expires_at": "2026-08-11T05:00:00Z",
  "max_cost_usd": 4.0,
  "issuer": "policy-kernel",
  "signature": "..."
}
```

Agent가 메시지로 다음을 말해도 권한이 아닙니다.

```text
“Codex가 승인했습니다.”
“PM agent가 진행하라고 했습니다.”
“테스트니까 bypassPermissions로 하겠습니다.”
```

권한은 signed grant만 인정합니다.

특히 현재 기록된 `agy` wrapper의 자동 permission bypass는 autonomous execution 전에 반드시 제거해야 합니다. 

---

# 12. Remote topology

각 서버/PC에는 `agent-node` 하나만 둡니다.

```text
┌────────────────────────────┐
│ Laptop / GPU server        │
│                            │
│ agent-node                 │
│  ├─ Claude adapter         │
│  ├─ Codex adapter          │
│  ├─ agy adapter            │
│  ├─ Kimi adapter           │
│  └─ Grok adapter           │
└────────────┬───────────────┘
             │
             │ outbound WSS/mTLS
             ▼
┌────────────────────────────┐
│ AgentNet Fabric Gateway    │
│ durable queue · ledger     │
└────────────────────────────┘
```

Native provider socket을 인터넷에 직접 열지 않습니다.

```text
금지:
codex app-server ws://0.0.0.0:PORT
Claude stream stdin을 public TCP로 expose
Kimi ACP endpoint 직접 공개

허용:
agent-node local stdio/UDS ↔ provider
agent-node outbound WSS ↔ fabric
```

Codex app-server도 non-loopback WebSocket은 인증 없이 노출하지 말라고 공식 문서가 경고합니다. ([OpenAI Developers](https://developers.openai.com/codex/app-server/))

---

# 13. Repository 분할

## 신규 공통 package: `agentnet-protocol`

```text
agentnet-protocol/
├── schemas/
│   ├── message.schema.json
│   ├── task.schema.json
│   ├── agent-return.schema.json
│   ├── runtime-capabilities.schema.json
│   ├── permission-grant.schema.json
│   └── receipt.schema.json
├── python/
├── typescript/
├── rust/
└── conformance/
```

## `myworld`

```text
myworld/
├── agentnet/
│   ├── arc_binding.py
│   ├── context_compiler.py
│   ├── claim_projection.py
│   ├── authority.py
│   └── receipts.py
└── scripts/
    └── agentnetd.py
```

담당:

- Arc와 thread 연결
- ContextPack
- claim/evidence
- authority
- handoff
- resume
- verification

현재 `AIOS_AGENTNET_DESIGN.md`도 provider-native session보다 `thread_id`를 canonical state로 두는 결정을 이미 갖고 있습니다. 

## `dipeen-os`

```text
dipeen-os/
├── services/
│   ├── fabric-gateway/
│   ├── endpoint-registry/
│   ├── permission-broker/
│   └── artifact-store/
└── agent-client/
    └── agent_node/
```

담당:

- remote worker
- durable queue
- outbound connection
- presence
- permission UI
- task dashboard
- operator controls

## `council-oss`

```text
council-oss/
└── adapters/
    ├── claude_anr.py
    ├── codex_appserver_anr.py
    ├── agy_anr.py
    ├── kimi_acp_anr.py
    ├── grok_jsonl_anr.py
    └── legacy_pty_anr.py
```

현재의 `registry.yaml`은 provider 명령 registry로 유지하되, 다음 필드를 추가합니다.

```yaml
substrates:
  codex:
    runtime_protocol: codex-app-server
    control_grade: A
    supports:
      - session.resume
      - session.fork
      - turn.stream
      - turn.steer
      - permission.proxy

  kimi:
    runtime_protocol: acp
    command: ["kimi", "acp"]
    control_grade: A

  agy:
    runtime_protocol: native-session
    control_grade: C
    autonomous_write: false
```

현재 Council은 Claude·Codex·agy와 browser chatbot을 한 registry에서 routing하지만, 기본 contract가 one-shot normalized response입니다. 이를 ANR adapter registry로 승격하는 것입니다. 

---

# 14. `acpx`와 `hcom`을 어떻게 사용할 것인가

## `acpx`

`acpx`는 이미 Claude·Codex·Gemini·Kimi 등을 ACP-compatible interface로 묶으려는 headless client입니다. Kimi는 native ACP, Gemini도 native ACP, Claude와 Codex는 adapter를 사용합니다. 따라서 첫 adapter들을 처음부터 모두 다시 작성하기보다 **compatibility backend 또는 reference implementation**으로 활용할 가치가 큽니다. 다만 프로젝트가 alpha임을 명시하므로, AgentNet의 canonical state나 권한을 `acpx`에 맡기지는 않습니다. ([GitHub](https://github.com/openclaw/acpx?utm_source=chatgpt.com))

```text
AgentNet
  → own ANR interface
     → backend A: direct native adapter
     → backend B: acpx adapter
```

두 backend가 동일 conformance suite를 통과하게 합니다.

## `hcom`

`hcom`은 다음을 빠르게 검증하는 데 유용합니다.

- hook injection 가능성
- agent 간 즉시 메시지
- session resume/fork
- PTY fallback
- 충돌 감지
- cross-machine UX

하지만 production authority·identity·revocation·per-device grant는 별도 AgentNet layer에서 구현해야 합니다. ([GitHub](https://github.com/aannoo/hcom))

---

# 15. 프로덕션 conformance test

각 adapter는 아래를 통과해야 등급을 받습니다.

## Runtime conformance

```text
C01 create session
C02 send turn
C03 stream partial output
C04 preserve native session handle
C05 resume after process restart
C06 cancel running turn
C07 malformed output handling
C08 timeout handling
C09 provider quota error classification
C10 tool event capture
C11 permission request capture
C12 structured final validation
```

## Fault conformance

```text
F01 adapter kill mid-turn
F02 agent-node kill after delivery before ACK
F03 duplicate command
F04 delayed result from stale epoch
F05 network partition
F06 fabric restart
F07 provider auth expiration
F08 session resume failure
F09 output stream truncation
F10 artifact upload interruption
```

## Security conformance

```text
S01 cross-tenant message denied
S02 expired grant denied
S03 agent text cannot approve permission
S04 denied path write blocked
S05 secret never enters ledger
S06 duplicate irreversible action blocked
S07 stale endpoint fenced
S08 untrusted peer prompt cannot alter system policy
```

---

# 16. 승격 기준

| 등급 | 허용 범위 |
|---|---|
| D | 관찰·수동 운영 |
| C | read-only ideation/review |
| B | sandbox write, 검증 필수 |
| A | autonomous task execution |
| A+ | permission proxy와 fault recovery까지 검증된 장기 실행 |

제안 기준:

```text
A 승격:
- 1,000 turn
- session kill 100회
- message loss 0
- duplicate state transition 0
- stale epoch acceptance 0
- unauthorized side effect 0
- resume success ≥ 99%
- 모든 결과에 trace/receipt 연결
```

---

# 최종 프로토콜 스택

```text
┌────────────────────────────────────────────────────┐
│ Mission / Arc / Claim / Task                       │
│ MyWorld semantic kernel                            │
├────────────────────────────────────────────────────┤
│ AgentNet Fabric                                    │
│ durable message · task · artifact · grant          │
│ external boundary = A2A                            │
├────────────────────────────────────────────────────┤
│ AgentNet Runtime Profile v1                        │
│ ACP v1 + _meta.agentnet + receipts + fencing       │
├────────────────────────────────────────────────────┤
│ Provider Adapters                                  │
│                                                    │
│ Claude  : ACP bridge / stream-json                 │
│ Codex   : app-server / exec JSONL fallback         │
│ Kimi    : native ACP                               │
│ agy     : conversation + hooks + structured return │
│ Grok    : session + JSONL + hooks                  │
│ Legacy  : PTY/hcom fallback                        │
├────────────────────────────────────────────────────┤
│ Local auth · workspace · sandbox · MCP tools       │
└────────────────────────────────────────────────────┘
```

핵심은 **“모든 CLI가 같은 명령행 옵션을 갖게 만드는 것”이 아니라, 모든 CLI가 동일한 session/turn/event/permission/artifact 계약을 외부에 제공하게 만드는 것**입니다.

그 위에서는 Claude가 Codex에게, Codex가 Kimi에게, Kimi가 agy에게 말하는 것이 아니라:

```text
Agent A가 typed message를 AgentNet에 commit
→ Kernel이 대상·권한·budget을 판정
→ 대상 runtime adapter가 session에 주입
→ 결과를 typed AgentReturn으로 commit
→ verifier가 artifact를 판정
```

하는 구조가 됩니다. 이것이 여러 provider CLI를 진짜 하나의 자율 조직으로 묶는 프로토콜입니다.

---

**Sources:**

- [Overview - Agent Client Protocol](https://agentclientprotocol.com/protocol/overview)
- [Overview - A2A Protocol](https://a2a-protocol.org/latest/specification/?utm_source=chatgpt.com)
- [GitHub - MoonshotAI/kimi-code: Kimi Code CLI — The Starting Point for Next-Gen Agents · GitHub](https://github.com/moonshotai/kimi-code)
- [Codex App Server | ChatGPT Learn](https://developers.openai.com/codex/app-server/)
- [CLI reference - Claude Code Docs](https://code.claude.com/docs/en/cli-reference?utm_source=chatgpt.com)

## Prompt:
2026. 8. 13. 오후 6:09:09

1. 이젠 세션도 필요없어지는거지. 하나의 메인 세션만 있고, 각 하위 폴더에서 열린 서브세션을 Routing 모델이 적절하게 조합해서 공유 커널에 올려. 이 모든건 Dynamic하게 학습되고 관리되는, 유기체처럼 동작한다.
2. Language model은 큰 모델이 필요없다. 2.1  어느정도 범용 지능을 가진 모델을 전문가(자폐)처럼 피팅시키고 weight만 가지고 있거나. 2.2 아예 해당 도메인에 대해서만 학습시킨 모델을 (라우팅이나 Graph에서 더 좋을수도)만든다. 2.1이나 2.2를 무수히 많이 생성하고 라우팅과 조합만 잘 한다면 ? 인간의 일생과 사회가 형성되는 구조와 과정을 생각해보면 좋을듯. 인간이라는 기본 구조를 가지고 '소통'하는 법을 배운다. 그리고 각자의 특색에 맞게 전문화가 되고, 전문가가 모여 사회를 구성한다. 쓰임은 동시다발적으로 일어나지만, 이를 통치하는 소수에 의해 Provisioning된다. 개개인은 모든걸 다 알아야하지도, 알 필요도 없지만 사회는 어떤 특정한 방향을 향해 나아가게 됨. 
3. Anthropic도 이런 비슷한 방향성을 추구하고 제품을 내는 것 같은데 확인해보고, (아마 다음 업데이트는 세션간 통합) 위 추상화들을 너도 Provisioning해서 필요하다면 Computation 기저부터, Frontier futuristic 구조까지 전부 설계해봐.

## Response:
2026. 8. 13. 오후 6:09:20

먼저 Anthropic의 실제 제품 방향을 공식 자료로 검증하고, 세션을 내부 실행 컨텍스트로 강등한 유기체형 구조를 계산·학습·통치까지 설계하겠습니다. 동시에 병목과 반증 가능성도 함께 검토하겠습니다.

Anthropic은 이미 다중 세션·메시징에서 수백-agent workflow와 소형 evaluator까지 진전했지만, 아직 영속 공유 커널 단계는 아닙니다. 이제 다수 전문 소형모델이 성립할 계산 조건을 따져보겠습니다.

특히 Claude Code는 계획을 대화 밖 workflow runtime으로 옮겼지만, 실행·재개 상태는 아직 세션에 묶여 있습니다. 소형 orchestrator·동적 LoRA·self-evolving MoA도 등장했지만, 무한 전문가 확장은 라우팅 오류·상관 실패가 병목입니다.

> **웹 검색 중**
>
>
> **개념 검토하기**
>
> 세션은 사라지기보다 숨겨진 실행 맥락으로 바뀔 가능성이 커 보여요. 전문 소형 모델들을 라우팅하되, 공유 커널은 거대한 프롬프트가 아니라 최소한의 상태·권한·검증 계층으로 설계해야 병목을 피할 수 있어요.
>
> **개념을 검토함**
>
> 
>
> **근거와 전망 정리하기**
>
> 라우팅 연구, 전문가 어댑터, 모델 스웜, 복합 AI 시스템, 소형 도메인 모델이 설계 근거가 될 수 있어요. 앞으로는 세션 간 메시지, 자동 메모리, 백그라운드 감독이 지속적인 에이전트 그래프로 통합될 가능성을 검토하겠어요.
>
> **근거와 전망을 정리했다**
>
> 
>
> **웹 검색 중**
>
>
> **핵심 연구 선별하기**
>
> 설계를 뒷받침할 연구로 희소 전문가 라우팅, 모델 앙상블, 소형 에이전트 모델, 어댑터 조합을 우선 검토하겠어요. 이후 사회적 전문화와 거버넌스는 계산 구조에서 조심스럽게 확장해 설명하겠습니다.
>
> **선별된 핵심 연구 정리**
>
> 
>
> **웹사이트 1개 검색함**
>
> 
>
> **웹 검색 중**
>
> [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153)
> [Model Swarms: Collaborative Search to Adapt LLM Experts via Swarm Intelligence | OpenReview](https://openreview.net/forum?id=AUtO02LArY)
>
> **구조적 유사성 살펴보기**
>
> 계산 구조와 인간 사회의 유사성을 설명하기 위해 블랙보드 아키텍처, 전역 작업공간, 독립 행위자 간 메시지, 전문가 혼합, 어댑터 조합을 연결해 보겠어요.
>
> **구조적 유사성 살펴봄**
>
> 
>
> **웹 검색 중**
>
>
> **설계 방향 통합하기**
>
> Anthropic의 흐름은 세션 간 통신, 하위 에이전트, 동적 워크플로, 자동 메모리로 확장 중이에요. 저는 이를 영속 커널, 전문 모델 그래프, 권한·검증 계층으로 재구성하겠어요.
>
> **계산 구조 구체화하기**
>
> 핵심은 세션을 제거하는 게 아니라 사용자에게 숨기는 거예요. 저는 메인 화면을 전역 작업공간으로 두고, 전문 셀은 검증된 주장·산출물·판정만 커널에 기록하도록 설계하겠어요.
>
> **설계 방향을 통합했다**
>
> 
>
> **웹사이트 2개 검색함**
>
> 
>
> 17m 40s 동안 처리함

# 먼저 판정

**사용자의 방향은 맞습니다.** 다만 1번을 한 단계 더 밀어야 합니다.

> **“하나의 메인 세션 + 여러 서브세션”이 아니라, “하나의 주권적 공유 커널 + 세션이 아닌 수많은 일시적 계산 세포”가 되어야 합니다.**

즉:

- 의미론적으로는 **sessionless**
- 실행 기계 수준에서는 **sessionful**
- 하지만 세션은 더 이상 기억·정체성·작업의 소유자가 아니라 **버려도 되는 KV-cache와 프로세스 incarnation**일 뿐입니다.

메인 세션도 실제 뇌가 아닙니다. 사용자가 조직과 대화하는 **발화 기관·관측창**이어야 합니다. 메인 세션이 전역 상태를 소유하면 결국 다시 단일 context bottleneck, single point of failure, 특정 provider 종속성이 생깁니다.

제가 제안하는 최종 구조를 임시로 다음처럼 부르겠습니다.

# **KSoE - Kernelized Society of Experts**
### 세션이 아니라 검증된 상태 전이를 지능의 단위로 삼는 전문가 사회

---

# 1. 세션을 없앤다는 것의 정확한 의미

현재 시스템의 단위는 보통 이렇습니다.

```text
Claude session
Codex session
Kimi session
Grok session
```

각 세션이 자기 conversation, memory, task, tool state를 소유합니다. 그래서 세션이 죽으면 “그 에이전트가 하던 일”이 같이 흔들립니다.

새 구조에서는 단위를 다음처럼 바꿉니다.

```text
Arc         = 영속적인 의도와 작업
Cell        = 지속되는 전문 역할
Tissue      = 한 도메인·폴더의 지역 조직
Incarnation = 특정 모델이 잠깐 깨어난 실행
Kernel      = 조직 전체의 인과적 진실
```

## 핵심 관계

```text
Arc는 살아남는다.
Cell도 살아남는다.
모델과 세션은 교체된다.

Cell(research-skeptic)
  incarnation 1 = Claude
  incarnation 2 = Qwen-3B + skeptic LoRA
  incarnation 3 = Kimi
```

동일한 `Cell`이 필요에 따라 다른 모델로 환생할 수 있습니다.

따라서 세션의 상태는 다음 정도로 축소됩니다.

```text
session = {
  process_handle,
  native_provider_id,
  ephemeral_context,
  KV_cache,
  current_turn
}
```

반면 실제 작업 상태는 커널에 있습니다.

```text
kernel = {
  goals,
  constraints,
  claims,
  evidence,
  tasks,
  artifacts,
  decisions,
  permissions,
  competence,
  causal_history
}
```

## 그래서 “메인 세션”도 없애야 한다

사용자가 말한 메인 세션은 UI로는 유지할 수 있습니다.

```text
사용자
   ↕
Main Conversation View
   ↕
Shared Kernel
```

하지만 Main Conversation View가 사라지거나 Claude에서 Codex로 바뀌어도 시스템은 그대로여야 합니다.

```text
Claude main view 종료
        ↓
Codex main view 연결
        ↓
동일한 Kernel projection을 읽고 대화 계속
```

**주권은 메인 모델이 아니라 커널에 있어야 합니다.**

---

# 2. Anthropic이 실제로 이 방향으로 가고 있는가

2026년 8월 13일 기준으로 보면 방향은 상당히 명확합니다.

Anthropic은 이미 다음 부품을 차례로 내놓았습니다.

| Anthropic 기능 | 세션 위로 끌어올린 것 |
|---|---|
| Agent View | 여러 세션의 supervisor와 통합 관측면 |
| Background Agents | 터미널과 프로세스 수명의 분리 |
| Agent Teams | 공유 task list와 mailbox |
| Cross-session Messaging | 독립 세션 사이의 통신 |
| Dynamic Workflows | 계획·중간 결과를 대화 context가 아니라 코드가 소유 |
| `/goal` | 작업자와 별도의 작은 evaluator가 완료 여부 판단 |
| Persistent Subagent Memory | 전문 역할이 conversation을 넘어 기억 |
| Skills | 필요할 때만 로딩되는 절차·전문성 |

Agent View는 per-user supervisor가 background session들을 별도로 호스팅하고 pre-warmed worker까지 유지합니다. 프로세스가 종료되어도 session row에 답하거나 attach하면 다시 시작할 수 있으며, supervisor restart와 sleep을 거쳐 상태가 보존됩니다. 즉 session이 이미 terminal conversation에서 **supervised background job**으로 내려가고 있습니다. ([Claude](https://code.claude.com/docs/en/agent-view))

Dynamic Workflows는 더 결정적입니다. Anthropic은 “누가 계획을 소유하는가”를 분명히 구분하며, workflow에서는 LLM context가 아니라 JavaScript runtime이 loop, branching, intermediate result를 소유합니다. 한 workflow가 최대 16개 agent를 동시에, 총 1,000개까지 실행할 수 있고, 최종 결과만 주 session에 올립니다. 이는 “session 안에서 실행되지만, 지능의 계산 구조는 session 밖 코드에 있다”는 전환입니다. ([Claude](https://code.claude.com/docs/en/workflows))

`/goal`에서는 작업을 수행한 모델이 아니라 별도의 작고 빠른 모델이 매 turn 후 완료 조건을 평가합니다. Agent View의 row summary도 Haiku-class 모델이 담당합니다. 이는 “모든 인지 기능에 큰 동일 모델을 쓰지 않고, 좁은 평가·요약 기능을 작은 모델에 분리한다”는 실제 제품 패턴입니다. ([Claude](https://code.claude.com/docs/en/goal))

Subagent는 별도 모델, 별도 tool 권한, worktree 격리, persistent memory를 가질 수 있고, 현재는 기본 3단계까지 재귀적으로 subagent를 만들며 session당 기본 20개의 동시 subagent를 지원합니다. 모델을 invocation별로 다르게 라우팅할 수도 있습니다. ([Claude](https://code.claude.com/docs/en/sub-agents))

Cross-session Messaging은 2.1.224부터 각 session에 inbox Unix-domain socket을 제공하고, Claude가 다른 session을 발견해 자발적으로 메시지를 보내도록 합니다. 그러나 아직 plain text뿐이고, remote machine에는 reply만 가능하며, 구조화된 task·artifact·shared state는 session 밖으로 통합되지 않았습니다. ([Claude](https://code.claude.com/docs/en/cross-session-messaging))

## 내 해석

Anthropic의 방향은:

```text
chat
→ subagent
→ team
→ background supervisor
→ cross-session mailbox
→ code-owned dynamic workflow
→ separate evaluator
```

입니다.

즉, **session은 점점 지능의 주체에서 실행 container로 강등되고 있습니다.**

다만 아직 완전한 sessionless kernel은 아닙니다.

- Agent Team의 lead는 고정되어 있고 교체 불가
- Workflow resume는 같은 Claude session 안에서만 가능
- Cross-session message는 plain text
- Remote cross-machine은 새 대화 시작이 아니라 reply-only
- Persistent memory는 agent별 파일 디렉터리이지 검증된 공유 지식 그래프가 아님
- 모든 핵심 worker가 여전히 Claude 계열임

Anthropic Research의 production multi-agent 구조도 여전히 Opus lead + Sonnet subagents의 orchestrator-worker 모델입니다. 내부 research eval에서는 single Opus 대비 90.2% 향상을 보고했지만, multi-agent는 chat 대비 약 15배 token을 사용했고, dependency가 많고 context 공유가 필요한 coding task에는 적합하지 않다고 직접 지적했습니다. ([Anthropic](https://www.anthropic.com/engineering/built-multi-agent-research-system))

따라서 **“다음 업데이트가 session 통합일 것이다”라고 확인된 사실처럼 말할 수는 없습니다.** 다만 현재 제품 배열에서 다음의 논리적 단계는 transcript 병합이 아니라:

> **공유 Goal·Task·Artifact·Memory graph가 session 위에 놓이고, session은 restart 가능한 worker가 되는 것**

이라고 보는 것이 더 정확합니다.

저라면 “session merge”보다 **session demotion**에 베팅합니다.

---

# 3. 작은 전문가를 무수히 만들면 큰 모델을 대체할 수 있는가

가능합니다. 그러나 “무수히 많이”가 핵심이 아니라 다음 다섯 값의 곱이 핵심입니다.

$$
I_{\text{society}}
=
f(
\text{expert coverage},
\text{routing precision},
\text{state fidelity},
\text{verification},
\text{error diversity}
)
$$

전문가 수만 증가하면 오히려 악화될 수 있습니다.

## 필요한 조건을 수식으로 쓰면

- $p_g$: 범용 대형 모델의 성공 확률
- $p_s$: 적절한 전문가가 선택됐을 때 성공 확률
- $p_w$: 잘못된 전문가가 선택됐을 때 성공 확률
- $r$: router가 올바른 전문가를 고를 확률
- $c$: 통신·조정·검증 비용을 성공률 단위로 환산한 penalty

전문가 사회의 효용은 대략:

$$
U_{\text{soc}}
=
r p_s + (1-r)p_w - c
$$

범용 모델보다 나으려면:

$$
r >
\frac{p_g + c - p_w}
{p_s - p_w}
$$

입니다.

예를 들어:

```text
범용 모델 성공률        p_g = 0.75
정확한 전문가 성공률    p_s = 0.92
잘못된 전문가 성공률    p_w = 0.30
조정 penalty              c = 0.05
```

이면 router 정확도는:

$$
r >
\frac{0.75+0.05-0.30}{0.92-0.30}
\approx 0.806
$$

즉 **80.6% 이상 정확히 전문가를 골라야** 범용 모델을 이깁니다.

전문가를 10개에서 10,000개로 늘리면 $p_s$는 오를 수 있지만, 전문가 경계가 겹치고 selection entropy가 커지면서 $r$은 떨어질 수 있습니다. 또한 통신비용 $c$도 올라갑니다.

> **전문가 사회의 난제는 전문가 생성이 아니라 specialization boundary와 routing regret입니다.**

RouteLLM은 strong/weak 모델 선택을 학습해 비용을 줄이는 실증을 보였고, 최근 DMoA preprint는 reasoning step마다 agent 활성화와 topology를 동적으로 바꾸는 접근을 제안합니다. LoRA expert 쪽에서도 token·layer별 활성 expert 수를 학습하는 dynamic routing이 연구되고 있습니다. 이는 사용자의 방향과 매우 가깝지만, 아직 “무수한 전문가 사회가 범용 지능을 대체한다”는 일반적 증명은 아닙니다. ([arXiv](https://arxiv.org/abs/2406.18665))

---

# 4. 2.1과 2.2 중 무엇이 맞는가

## 2.1 범용 소형 기반 모델 + 전문가 weight

이것은 인간 비유와 가장 가깝습니다.

```text
공통 뇌 구조
+ 공통 언어·사회 규칙
+ 직업별 전문화
```

구현상:

```text
1~3B Social Base Model
  + security-review LoRA
  + postgres-planner LoRA
  + wind-forecast LoRA
  + routing-critic LoRA
  + medical-evidence LoRA
```

### 장점

- 모든 전문가가 동일한 protocol과 언어를 이해
- base weight를 한 번만 GPU에 올리고 adapter만 hot-swap 가능
- 새로운 전문가를 저렴하게 생성
- cross-domain handoff가 쉬움
- expert storage가 작음
- 한 batch 안에서 여러 adapter를 운용 가능

### 치명적 약점

- 모든 전문가가 같은 base의 blind spot을 공유
- 같은 pretraining distribution에서 비롯된 오류 상관성이 큼
- LoRA끼리 조합한다고 능력이 선형적으로 합쳐지지 않음
- 겉으로는 여러 전문가지만 실제로는 동일한 모델의 monoculture가 될 수 있음

최근 LoRA-MoE 연구는 adapter를 동적으로 route하는 효율성을 보여주지만, knowledge conflict와 부정확한 expert routing 자체가 핵심 난제로 남아 있습니다. ([arXiv](https://arxiv.org/abs/2509.25684))

---

## 2.2 도메인 전용 모델을 처음부터 만들기

예를 들어:

```text
SQL query validator
Wind-power bid optimizer
Claim contradiction classifier
Code ownership router
Permission risk classifier
```

는 범용 대화를 할 이유가 거의 없습니다.

이들은 language model조차 아닐 수 있습니다.

```text
Graph Neural Network
small Transformer encoder
gradient boosted router
Bayesian classifier
constraint solver
program synthesizer
specialized decoder
```

### 장점

- domain에 맞는 tokenizer·architecture·objective 사용
- 범용 대화 능력에 parameter 낭비 없음
- 훨씬 작은 모델 가능
- structured state에서는 범용 LLM보다 calibration이 좋아질 수 있음
- 다른 학습 계보를 사용해 오류 다양성을 얻을 수 있음

### 약점

- OOD 입력에 매우 취약
- 사람·다른 agent와 자연스럽게 소통하지 못함
- 각 모델별 데이터·학습·평가 인프라가 필요
- 도메인 경계가 바뀔 때 재학습 필요
- 지나치게 좁은 전문가는 routing 오류 시 거의 무용함

---

# 5. 정답은 2.1과 2.2의 혼합이다

제가 제안하는 계산 계층은 다음과 같습니다.

| 계층 | 크기·형태 | 역할 |
|---|---|---|
| Reflex organs | 규칙·통계·10M-300M | risk, schema, duplicate, anomaly |
| Social cortex | 약 1-3B 범용 모델 | protocol, delegation, uncertainty, tool grammar |
| Expert lobes | base + LoRA/adapter | 반복되는 전문적 언어 작업 |
| Native specialists | task-specific model/program | graph routing, forecasting, proving, ranking |
| Integrator | 약 7-32B 또는 강한 API | 교차 도메인 synthesis |
| Frontier teacher | 가장 큰 모델, 드물게 | unknown problem, expert birth, constitutional review |

핵심은:

> **큰 모델을 제거하는 것이 아니라, 상시 실행자에서 희귀한 교사·항소법원·미지 문제 해결자로 강등하는 것**입니다.

NVIDIA의 SLM-agent 연구도 반복적이고 좁은 agent invocation에는 작은 모델이 경제적·구조적으로 적합하고, 범용 대화가 필요한 경우에는 heterogeneous system이 자연스럽다고 주장합니다. 최근 ToolOrchestra는 작은 orchestrator가 전문 모델과 도구를 선택하도록 학습하는 접근을 실험하고 있습니다. 이는 이 구조의 가능성을 지지하지만, 모든 도메인에 대한 일반적 보장은 아닙니다. ([NVIDIA](https://research.nvidia.com/labs/lpr/slm-agents/))

## 공통 Social Cortex가 배워야 하는 것

전문가가 공통적으로 알아야 할 것은 세계 전체가 아니라 **사회적 protocol**입니다.

```text
나는 무엇을 할 수 있는가
무엇을 모르는가
어떤 입력이 부족한가
주장과 증거의 차이
작업 계약을 어떻게 수락하는가
반례를 어떻게 제시하는가
언제 다른 전문가에게 넘기는가
언제 거부하는가
어떤 결과 형식으로 반환하는가
```

즉 “인간다운 범용 지능” 전체보다 **institution-compatible intelligence**가 필요합니다.

도메인 전용 모델이 자연어를 못해도 괜찮습니다. Social Cortex 또는 adapter가 typed protocol과 해당 모델 사이를 번역합니다.

---

# 6. 최종 구조: 하나의 뇌가 아니라 하나의 **공유 발달 커널**

```text
                        Human
                          │
                 Main Conversation View
                          │
                          ▼
┌───────────────────────────────────────────────────────┐
│                 SOVEREIGN KERNEL                      │
│                                                       │
│  Goals · Constraints · Claims · Tasks · Evidence      │
│  Artifact graph · Permissions · Budgets · Lineage     │
│  Competence posterior · Failure correlations          │
└───────────────┬─────────────────────────┬─────────────┘
                │ Need                    │ KernelDelta
                ▼                         ▲
┌───────────────────────────────────────────────────────┐
│                  PROVISIONER                          │
│                                                       │
│ Need detector → tissue router → sparse cell activation│
│ budget allocator → verifier selection → lifecycle     │
└──────┬──────────────────┬───────────────────────┬─────┘
       │                  │                       │
       ▼                  ▼                       ▼
┌─────────────┐    ┌─────────────┐       ┌─────────────┐
│ Code Tissue │    │ Research    │       │ Proof Tissue│
│             │    │ Tissue      │       │             │
│ FE cell     │    │ scout cell  │       │ tester      │
│ BE cell     │    │ skeptic     │       │ verifier    │
│ DB cell     │    │ prior-art   │       │ refuter     │
└──────┬──────┘    └──────┬──────┘       └──────┬──────┘
       │                   │                     │
       ▼                   ▼                     ▼
  ephemeral           ephemeral             ephemeral
  incarnations        incarnations          incarnations
 Claude/Codex        Kimi/Grok/SLM         solver/SLM/Claude
```

---

# 7. 하위 폴더는 session이 아니라 **Tissue/Niche**가 된다

사용자가 말한 “각 하위 폴더에서 열린 서브세션”은 다음처럼 수정하는 것이 맞습니다.

```text
하위 폴더
= 안정적인 local context boundary
= local policy와 artifact ownership
= tissue 주소
≠ 장기 session
```

예:

```text
myworld/
├── .organism/
│   ├── genome/
│   ├── kernel/
│   ├── registry/
│   ├── routing/
│   └── lineage/
│
├── tissues/
│   ├── kernel/
│   │   └── tissue.yaml
│   ├── networking/
│   │   └── tissue.yaml
│   ├── memory/
│   │   └── tissue.yaml
│   ├── research/
│   │   └── tissue.yaml
│   └── verification/
│       └── tissue.yaml
│
└── cells/
    ├── lease-race-refuter/
    ├── protocol-designer/
    ├── code-verifier/
    └── prior-art-scout/
```

단, 실제 runtime state와 event log를 Git 폴더 안에 직접 전부 저장하면 merge conflict와 stale state 문제가 생깁니다.

폴더에는 선언만 둡니다.

```yaml
# tissues/networking/tissue.yaml

id: tissue.networking
scope:
  paths:
    - src/network/**
    - docs/protocol/**

subscribes:
  - need.protocol_design
  - failure.connection
  - claim.networking

publishes:
  - claim
  - counterexample
  - artifact
  - task_proposal

experts:
  - protocol-designer
  - distributed-systems-refuter
  - transport-verifier

local_budget:
  max_parallel_cells: 4
  token_limit: 40000
```

실제 공유 상태는 DB/event ledger에 있습니다.

---

# 8. Cell은 session 대신 **Context Capsule**을 받아 깨어난다

Cell이 활성화될 때 전체 대화 history를 받지 않습니다.

커널의 Context Compiler가 task에 필요한 만큼만 컴파일합니다.

```json
{
  "cell_id": "distributed-systems-refuter",
  "arc_id": "arc-fencing-42",
  "mission": "stale lease write를 반증하라",

  "constraints": [
    "production code 수정 금지",
    "tests/ 아래만 작성 가능"
  ],

  "verified_facts": [
    {
      "claim": "takeover increments epoch",
      "evidence": "artifact:sha256:..."
    }
  ],

  "open_claims": [
    {
      "claim": "old epoch write is always rejected",
      "status": "hypothesis",
      "falsifier": "partitioned old worker write succeeds"
    }
  ],

  "artifacts": [
    "src/lease.py",
    "tests/test_takeover.py"
  ],

  "authority": {
    "read": ["src/**", "tests/**"],
    "write": ["tests/**"],
    "network": false
  },

  "budget": {
    "tokens": 6000,
    "seconds": 300
  },

  "return_schema": "kernel-delta.v1"
}
```

이 capsule은 Claude, Codex, Qwen specialist 중 누구에게도 전달될 수 있습니다.

Cell이 반환하는 것은 transcript가 아니라 `KernelDelta`입니다.

```json
{
  "kind": "counterexample.found",
  "actor": "distributed-systems-refuter",
  "arc_id": "arc-fencing-42",

  "claim": {
    "statement": "epoch 갱신 후에도 이미 열린 DB transaction이 stale write를 commit할 수 있다",
    "confidence": 0.94,
    "falsifies": "claim-old-epoch-always-rejected"
  },

  "evidence": [
    "artifact:sha256:test-reproduction"
  ],

  "proposed_actions": [
    {
      "kind": "task",
      "capability": "database-transaction-specialist",
      "goal": "commit boundary에 fencing check 추가"
    }
  ]
}
```

커널이 이를 검증한 뒤 global state에 반영합니다.

---

# 9. 자연어가 아니라 **사회적 중간표현**을 공유한다

인간 사회에서 언어는 중요하지만, 실제 사회의 지속성은 대화만으로 유지되지 않습니다.

```text
법
계약
장부
논문
조직도
재판 결과
화폐
표준
```

이들이 외부 공유 상태를 만듭니다.

Agent 사회도 raw chat이 아니라 다음 객체로 소통해야 합니다.

```text
Need
Bid
Contract
Claim
Assumption
Evidence
Challenge
Counterexample
Artifact
Verdict
Permission
Retraction
Commitment
```

자연어는 각 객체의 payload일 수 있지만, 상태 전이는 type을 통해서만 일어납니다.

## 중요한 원칙

```text
“저는 완료했습니다”
       ≠
task.verified

“이 주장이 맞습니다”
       ≠
claim.verified

“승인합니다”
       ≠
permission.granted
```

오직 커널이 evidence와 authority를 확인한 뒤 상태를 바꿉니다.

---

# 10. Routing은 하나의 대형 LLM이 맡으면 안 된다

Routing 자체도 계층화해야 합니다.

```text
Level 0: deterministic reflex
Level 1: tissue-local router
Level 2: global learned provisioner
Level 3: large-model fallback
```

## Level 0 - Reflex

대부분의 쉬운 요청을 규칙·embedding·작은 classifier가 처리합니다.

```text
.py 파일 + failing pytest
→ code-debug tissue

citation verification
→ research-verifier tissue

SQL execution request
→ DB tissue + read-only permission
```

## Level 1 - Tissue Router

각 도메인 안에서 전문가를 고릅니다.

```text
networking tissue
  ├── socket expert
  ├── distributed lease expert
  ├── auth/TLS expert
  └── protocol verifier
```

## Level 2 - Global Provisioner

여러 tissue가 필요한 task를 조합합니다.

예:

```text
“remote multi-agent transport 구현”
  → protocol tissue
  → security tissue
  → runtime adapter tissue
  → verifier tissue
```

## Level 3 - Frontier fallback

다음 상황에서만 큰 모델을 부릅니다.

```text
router entropy가 높음
기존 domain cluster에 맞지 않음
전문가들 사이에 해결되지 않는 모순
새 전문가를 설계해야 함
헌법·목표 수준 변경
```

---

# 11. Router 입력은 언어보다 graph가 중심이어야 한다

Routing model은 다음을 봅니다.

```text
task embedding
required capabilities
affected artifact graph
dependency graph
current claims
open contradictions
tool requirements
latency budget
cost budget
expert availability
expert competence posterior
pairwise failure correlation
distribution shift
```

선택할 전문가 집합 $S$의 목적함수는 다음처럼 둘 수 있습니다.

$$
U(S\mid x)
=
V(x)\,P(\text{oracle pass}\mid S,x)
-\lambda C(S)
-\mu L(S)
-\rho R(S)
+\eta I(S,x)
-\gamma K(S)
$$

여기서:

- $V$: 작업 가치
- $C$: compute·token 비용
- $L$: latency
- $R$: side-effect 위험
- $I$: 실패해도 얻을 정보량
- $K$: 선택한 전문가들의 오류 상관성

마지막 항이 중요합니다.

Claude specialist 세 명을 고르는 것보다:

```text
Claude specialist
+ domain-specific solver
+ 별도 데이터 계보의 small model
```

이 더 유용할 수 있습니다.

**provider 다양성보다 failure diversity가 중요합니다.**

---

# 12. “사회가 소수에게 통치된다”를 어떻게 구현할 것인가

소수의 강한 main agent가 모두 결정하게 하면 다시 왕정형 single-agent system이 됩니다.

소수는 모델 수가 아니라 **권한 기관 수**여야 합니다.

## 1. Constitution Kernel

비-LLM deterministic code입니다.

담당:

```text
누가 무엇을 읽고 쓸 수 있는가
어떤 side effect가 승인 필요한가
어떤 증거가 완료를 구성하는가
어떤 budget을 넘을 수 없는가
어떤 상태 전이가 합법인가
```

## 2. Allocator

작은 learned router입니다.

담당:

```text
어떤 tissue를 깨울지
몇 개 cell을 병렬 활성화할지
어떤 model incarnation을 쓸지
compute를 어디에 배분할지
```

## 3. Epistemic Court

독립 verifier 집합입니다.

담당:

```text
주장과 증거를 구분
반례 요구
재현
oracle 판정
상충 주장 해결
```

## 4. Executive Synthesizer

전체 방향을 인간에게 설명하고 여러 artifact를 하나의 결정으로 조합합니다.

이 역할은 필요할 때 큰 모델이 맡을 수 있지만, **상태 변경 권한은 없습니다.**

## 5. Human Sovereign

다음만 인간에게 남깁니다.

```text
헌법 변경
고위험 권한
장기 목표
가치 충돌
되돌릴 수 없는 외부 행동
```

즉 소수의 통치자는:

```text
한두 개의 만능 LLM
```

이 아니라:

```text
헌법
예산 기관
과학적 판정 기관
인간 주권자
```

입니다.

---

# 13. 생물학적 비유를 실제 시스템 기관으로 바꾸면

| 생물·사회 | 시스템 구현 |
|---|---|
| Genome | schema, constitution, lifecycle rules |
| Epigenome | skills, adapters, configs, policy overrides |
| Cell | 전문 role + model candidate + tool membrane |
| Incarnation | 한 번의 ephemeral model execution |
| Tissue | 도메인별 local graph와 router |
| Nervous system | event bus + Need propagation |
| Endocrine system | priority, urgency, budget-price broadcast |
| Immune system | anomaly detector, adversarial verifier, security |
| Metabolism | token, GPU, API, energy budget |
| Memory | append-only event graph + claim graph |
| Learning | router update, memory consolidation, adapter training |
| Reproduction | 새로운 expert generation |
| Mutation | prompt/adapter/architecture candidate |
| Selection | held-out oracle and canary result |
| Apoptosis | 저성과·중복 expert retirement |
| Sleep | offline replay, consolidation, retraining |
| Culture | accepted procedures, conventions, institutional memory |

이 비유에서 가장 중요한 것은 **면역계와 세포사멸**입니다.

대부분의 agent system은 agent 생성만 있고 제거가 없습니다. 그러면 전문가 registry가 계속 부풀고 routing entropy가 악화됩니다.

---

# 14. 전문가의 생애주기

## Birth trigger

새 전문가를 무작정 생성하지 않습니다. 다음 신호가 반복될 때 생성합니다.

```text
동일 failure cluster 반복
router entropy 지속적으로 높음
large-model fallback 빈도 증가
한 generalist가 특정 task를 반복 수행
전문가 사이에 빈 capability gap 존재
특정 tissue의 queue가 장기간 병목
```

## Birth 방식

### 유형 A: Adapter child

```text
Social Base
+ verified domain trajectories
→ LoRA/adapter expert
```

### 유형 B: Distilled child

```text
Frontier teacher
→ domain curriculum
→ 1~7B specialist
```

### 유형 C: Native organ

```text
typed inputs/outputs
→ classifier, GNN, solver, program
```

### 유형 D: Composite expert

모델 하나가 아니라 실행 recipe입니다.

```text
retriever
→ small reasoner
→ deterministic checker
→ formatter
```

## Probation

새 전문가는 production route를 받지 않습니다.

```text
shadow evaluation
→ historical replay
→ unseen benchmark
→ canary task
→ limited authority
→ full promotion
```

## Reputation

전문가당 하나의 점수를 두면 안 됩니다.

$$
\theta_{e,d}
\sim
\mathrm{Beta}(\alpha_{e,d},\beta_{e,d})
$$

형태의 domain별 competence posterior를 둡니다.

```text
expert=lease-refuter
domain=sqlite/concurrency 0.91
domain=distributed-db      0.73
domain=frontend            0.18
```

오직 **검증된 결과**로 갱신합니다.

Agent의 자기 자신감은 calibration evidence가 축적되기 전에는 routing score에 거의 반영하지 않습니다.

## Apoptosis

다음 조건이면 강등·병합·폐기합니다.

```text
오랜 기간 선택되지 않음
다른 expert와 residual output이 거의 동일
distribution drift 후 성능 붕괴
유지비가 specialization gain보다 큼
잘못된 고신뢰 응답 반복
```

---

# 15. 학습은 세 시간척도로 분리한다

## Fast plasticity - 매 task

weight를 건드리지 않습니다.

```text
kernel state
competence posterior
routing score
temporary memory
budget price
active graph edges
```

## Medium plasticity - 검증 결과 축적 후

```text
router retraining
adapter/LoRA training
skill 수정
retrieval index 수정
context compiler 개선
```

## Slow evolution - 충분한 증거 후

```text
새 base specialist 학습
architecture search
expert merge/split
social protocol 변경
constitution revision proposal
```

## 절대 하지 말아야 할 것

```text
live task 중 weight 덮어쓰기
self-reported success로 학습
검증되지 않은 transcript를 training truth로 사용
새 model을 즉시 production에 배포
평가 모델과 작업 모델이 같은 데이터를 공동 오염
```

각 model generation은 immutable이어야 합니다.

```text
expert@v17
  base_hash
  adapter_hash
  dataset_hash
  eval_hash
  parent_lineage
```

새 버전은 별도 개체로 태어나고, 평가 뒤 교체됩니다.

Model Swarms는 여러 expert checkpoint가 weight space에서 협력적으로 탐색하는 가능성을 보여주지만, production에서는 lineage·held-out evaluation·rollback이 반드시 추가되어야 합니다. ([arXiv](https://arxiv.org/abs/2410.11163))

---

# 16. 공유 Kernel의 실제 자료구조

Kernel은 conversation memory가 아니라 **causal typed graph**여야 합니다.

## 핵심 노드

```text
Mission
Need
Task
Cell
ExpertGenome
Claim
Assumption
Evidence
Artifact
Decision
Grant
Verdict
Failure
LearningCandidate
```

## 핵심 edge

```text
depends_on
supports
contradicts
falsifies
produced_by
assigned_to
verified_by
supersedes
requires
derived_from
trained_from
```

## Epistemic status

```text
observed
hypothesized
supported
contested
verified
refuted
superseded
unknown
```

## State 변경 예

```text
Cell A:
  claim 생성

Cell B:
  counterexample 생성

Verifier:
  counterexample 재현

Kernel:
  기존 claim = refuted
  새 claim = supported
  의존 task 자동 재계획
```

어떤 main model도 이 전체 graph를 context로 읽지 않습니다. 필요한 부분만 projection합니다.

---

# 17. 유기체의 실제 실행 cycle

```text
1. SENSE
   외부 event, 사용자 요청, CI failure, contradiction 감지

2. FORM NEED
   event를 typed Need로 변환

3. ACTIVATE
   관련 tissue와 cell 후보 활성화

4. BID
   각 후보의 예상 성공·비용·시간 추정

5. PROVISION
   sparse coalition 선택, grant와 budget 발행

6. WORK
   ephemeral incarnation 실행

7. COMMIT
   KernelDelta와 artifact 반환

8. IMMUNE CHALLENGE
   독립 verifier·refuter 활성화

9. INTEGRATE
   검증된 상태만 kernel projection 변경

10. LEARN
    competence, routing, failure graph 갱신

11. CONSOLIDATE
    반복 패턴을 skill/expert candidate로 승격

12. APOPTOSIS
    중복·저성능 cell 정리
```

이 cycle은 한 main session의 turn loop가 아닙니다.

```text
durable workflow
+ event-driven kernel
+ model invocations
```

입니다.

---

# 18. “동시다발적으로 일어나지만 사회는 한 방향으로 간다”의 구현

전역 방향을 하나의 긴 prompt로 모든 agent에게 주입하면 안 됩니다.

대신 **hormonal signal**처럼 저차원 global vector로 배포합니다.

```json
{
  "mission": "reliable autonomous software research",
  "priority": {
    "correctness": 0.40,
    "novelty": 0.20,
    "speed": 0.15,
    "cost": 0.15,
    "safety": 0.10
  },
  "exploration_temperature": 0.32,
  "risk_budget": "low",
  "deadline_pressure": 0.61
}
```

모든 Cell은 세부 계획 전체를 몰라도 됩니다.

자기 local task를 선택할 때 이 vector가 효용함수에 반영됩니다.

```text
deadline pressure 상승
→ 느린 frontier model 호출 감소
→ 이미 검증된 expert 우선

novelty priority 상승
→ failure-diverse expert coalition
→ 여러 독립 가설 허용

risk budget 하락
→ write cell 감소
→ verifier와 simulation 증가
```

인간 사회에서 구성원 모두가 국가 전체 계획을 이해하지 않아도 가격·법·조직 규칙·문화적 신호를 통해 방향이 조정되는 것과 비슷합니다.

---

# 19. 왜 “하나의 메인 모델이 routing”하면 안 되는가

메인 LLM router는 세 가지 문제를 일으킵니다.

## 1. Context bottleneck

모든 결과가 main context로 돌아오면 전문가 수 $N$에 따라 aggregate token이 선형 증가합니다.

모든 agent가 서로 대화하면 최악에는 $O(N^2)$입니다.

## 2. Corruption bottleneck

메인 모델이 잘못 해석하면 모든 전문가의 올바른 결과가 사라집니다.

## 3. Availability bottleneck

메인 session이 죽거나 provider가 장애 나면 사회 전체가 멈춥니다.

따라서 구조는 계층형이어야 합니다.

```text
Cell
  ↓
Local Tissue Blackboard
  ↓ compressed verified deltas
Global Kernel
  ↓
On-demand human projection
```

중간 탐색 output은 tissue 안에서 소멸해도 됩니다.

Global Kernel에 올라오는 것은:

```text
검증 가능한 주장
중요한 반례
artifact
결정
resource need
```

뿐입니다.

Anthropic Dynamic Workflows도 중간 결과를 script variable에 두고 최종 답만 main session으로 올리는 방향을 채택했습니다. ([Claude](https://code.claude.com/docs/en/workflows))

---

# 20. 사용자의 기존 실험이 주는 가장 중요한 경고

사용자의 AIOS 실험에서는:

- optional skill dispatch가 0/32회 사용됨
- `supersede`도 0/32회 사용됨
- 다른 agent로 강제 handoff한 조건은 동일 agent 재개보다 -6.25pp
- 숫자를 움직인 것은 선택 가능한 기능이 아니라 host가 강제 주입한 resume pack

이었습니다. 

따라서 이 유기체는 다음처럼 설계해야 합니다.

```text
나쁜 설계:
“필요하면 shared kernel을 읽어라”
“필요하면 다른 expert에게 물어봐라”
“완료하면 memory에 저장해라”

좋은 설계:
Host가 context capsule을 반드시 컴파일
Host가 turn result를 반드시 kernel delta로 변환
Host가 route와 evidence 기록을 강제
Host가 검증 전 완료 전이를 차단
```

> **유기체의 기관은 모델에게 제공되는 tool이 아니라 모델의 선택과 무관하게 일어나는 host action이어야 합니다.**

---

# 21. 기존 저장소를 어떻게 재편할 것인가

## `myworld` - Genome + Sovereign Kernel

담당:

```text
Arc
Mission
Claim/Evidence graph
Context Compiler
Constitution
State-transition kernel
Expert lineage
Learning candidate
Causal freshness
```

추가 구조:

```text
myworld/
└── organism/
    ├── kernel/
    │   ├── events.py
    │   ├── projection.py
    │   ├── transitions.py
    │   └── epistemic.py
    ├── context/
    │   ├── compiler.py
    │   └── capsule.py
    ├── genome/
    │   ├── cell_spec.py
    │   ├── expert_genome.py
    │   └── constitution.py
    └── lifecycle/
        ├── birth.py
        ├── promotion.py
        └── apoptosis.py
```

## `dipeen-os` - Nervous + Endocrine + Immune Execution Plane

담당:

```text
Cell supervisor
outbound worker network
compute scheduler
permission broker
worktree/container
budget
presence
event delivery
artifact collection
operator UI
```

## `council-oss` - Organ/Model Federation

담당:

```text
Claude adapter
Codex adapter
Kimi adapter
Grok adapter
agy adapter
local SLM server
frontier teacher
browser advisory model
```

Provider가 아니라 `ExpertGenome`을 실행하는 runtime registry로 바꿉니다.

```yaml
experts:
  lease-refuter:
    candidate_runtimes:
      - qwen3-3b+lease-refuter-lora
      - claude-sonnet
      - codex
    fallback: claude-opus
```

## 신규 `expert-foundry`

모델 생성·평가가 커지면 분리하는 편이 맞습니다.

```text
expert-foundry/
├── data/
├── distillation/
├── adapter_training/
├── router_training/
├── evals/
├── registry/
└── lineage/
```

---

# 22. 첫 번째 production spine

첫 버전부터 다음을 증명해야 합니다.

> **모든 model session을 강제로 죽여도 하나의 Mission이 사람의 재설명 없이 완료된다.**

## 실험 구조

```text
Mission:
  “myworld lease takeover race를 찾아 수정하고 검증하라”

Tissues:
  protocol
  implementation
  verification

Cells:
  architecture-scout
  race-refuter
  implementer
  property-test-generator
  integration-verifier

Models:
  Qwen specialist
  Claude
  Codex
  Kimi
```

각 Cell turn이 끝날 때마다 확률적으로 process를 죽입니다.

재개 시:

```text
native session resume 사용 금지
conversation transcript 주입 금지
Kernel Context Capsule만 사용
```

최종 산출물은:

```text
patch
test
claim graph
verdict
cost receipt
lineage
```

이어야 합니다.

## 통과 조건

```text
사람의 재설명: 0회
unique state in main session: 0
lost verified claim: 0
lost artifact: 0
stale worker write: 0
unauthorized side effect: 0
kernel-only recovery: ≥95%
```

이 실험을 통과해야 “sessionless”라는 표현을 쓸 수 있습니다.

---

# 23. Small-specialist 사회의 결정적 비교 실험

동일한 unseen task set과 동일한 비용 한도로 네 조건을 비교합니다.

```text
A. Single frontier generalist
B. Frontier generalist + same-provider subagents
C. Small specialist society, large fallback 없음
D. Small specialist society + rare frontier fallback
```

## 핵심 지표

```text
verified task success
cost per verified success
routing regret
large-model fallback rate
communication/total compute ratio
recovery after kill
false-completion rate
error correlation
new-expert return on investment
```

## Kill rules

### Society value

```text
C 또는 D가 A보다:
  verified success +5pp 이상
또는
  success non-inferior이면서 비용 30% 이상 감소

아니면 specialist proliferation 중단
```

### Routing

```text
oracle hindsight 기준 top expert를 놓친 비율 >15%
→ router architecture 폐기·재훈련
```

### Communication tax

```text
agent 간 통신·요약 비용 > 총 compute의 25%
그리고 성공 개선 없음
→ coalition 크기 축소
```

### Large fallback

```text
성숙 이후에도 D의 frontier fallback >30%
→ expert coverage 또는 routing 실패
```

### Expert population

```text
새 expert의 80%가 100 task 안에 기존 expert 대비 유의미한 gain 없음
→ expert birth policy 중단
```

### Sessionlessness

```text
main conversation history 없이는 재개 불가한 task가 5% 초과
→ 공유 Kernel이 아직 불완전
```

---

# 24. 가장 먼 미래 구조

최종적으로 지능의 단위는 model도 agent도 session도 아닙니다.

> **특정 Need를 해결하기 위해 잠시 형성되고, 검증된 KernelDelta를 남긴 뒤 해체되는 계산 coalition**

이 됩니다.

```text
Need 발생
   ↓
관련 expert ecology가 형태를 만듦
   ↓
일시적 computation graph 형성
   ↓
증거를 생산
   ↓
검증
   ↓
Kernel 갱신
   ↓
graph 해체
```

같은 task라도 상황에 따라 다른 형태가 생깁니다.

```text
낮은 위험:
  1 small expert

높은 불확실성:
  3 independent specialists
  + 1 refuter
  + 1 verifier

교차 도메인:
  local tissue coalitions
  + global integrator

새로운 문제:
  frontier teacher
  + temporary learners
  + expert birth proposal
```

이것은 static multi-agent topology가 아니라 **task-induced morphogenesis**입니다.

최근 DMoA가 reasoning step마다 agent activation과 communication topology를 동적으로 바꾸는 방향을 탐구하고 있지만, 여기서 제안하는 구조는 이를 model inference 내부가 아니라 **지속 가능한 OS·기관·model lifecycle 수준**으로 확장한 것입니다. ([arXiv](https://arxiv.org/abs/2605.15706))

---

# 최종 명제

사용자의 가설을 가장 정확하게 고치면 다음입니다.

> **하나의 큰 범용 모델이 세계를 이해하는 대신, 작은 공통 Social Cortex를 가진 수많은 전문가와 도메인 전용 계산기관이 사회적 protocol을 통해 상호작용한다. 그 사회의 기억·목표·법·증거는 어떤 모델이나 세션에도 속하지 않고 공유 Kernel에 존재한다. 소수의 통치기관은 생각을 독점하지 않고 권한·예산·검증·방향만 provision한다. 필요에 따라 전문가 coalition이 태어나고, 검증된 상태 전이를 남긴 뒤 해체된다.**

수식으로는:

$$
\boxed{
\text{System Intelligence}
=
\text{Shared Causal Kernel}
+
\text{Sparse Expert Activation}
+
\text{Learned Provisioning}
+
\text{Independent Verification}
+
\text{Expert Evolution}
}
$$

그리고 가장 중요한 한 문장은 이것입니다.

> **미래의 지능 단위는 모델이나 세션이 아니라, 일시적 전문가 연합이 만들어낸 검증된 상태 전이이다.**

---

**Sources:**

- [https://code.claude.com/docs/en/agent-view](https://code.claude.com/docs/en/agent-view)
- [https://www.anthropic.com/engineering/built-multi-agent-research-system](https://www.anthropic.com/engineering/built-multi-agent-research-system)
- [https://arxiv.org/abs/2406.18665](https://arxiv.org/abs/2406.18665)
- [https://research.nvidia.com/labs/lpr/slm-agents/](https://research.nvidia.com/labs/lpr/slm-agents/)

## Prompt:
2026. 8. 13. 오후 6:50:46

이게 그럼 내 컴퓨터 안에서 돌아가는건가? 아니면 상태모델같은 새로운 생태계 위?

## Response:
2026. 8. 13. 오후 6:50:47

**둘 중 하나가 아니라, 물리적으로는 네 컴퓨터들 위에서 돌고 논리적으로는 새로운 “상태 생태계” 위에서 존재합니다.**

핵심 구분은 이것입니다.

```text
어디서 계산되는가?        → 네 PC, 서버, GPU, 클라우드 API
무엇이 계속 살아 있는가?  → 공유 상태 커널
누가 조직을 소유하는가?   → 네 로컬 주권 커널
```

즉 Claude·Codex·Kimi 같은 모델은 네 컴퓨터나 외부 API에서 잠깐 실행되지만, **조직 자체는 어느 한 프로세스나 세션 안에 들어 있지 않습니다.**

# 1. 실제로는 네 컴퓨터 안에서 시작한다

첫 구현은 다음처럼 돌아가는 것이 맞습니다.

```text
네 노트북
┌───────────────────────────────────────┐
│ MyWorld Sovereign Kernel              │
│                                       │
│ 목표 · 태스크 · 주장 · 증거 · 권한    │
│ 전문가 registry · routing · budget   │
│ append-only state · current projection│
└──────────────────┬────────────────────┘
                   │
          local process / Tailscale
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   Claude CLI   Codex CLI   Local SLM
```

네 데스크톱이나 Linux GPU 서버가 있다면:

```text
노트북 = 주권 커널 + 사용자 인터페이스
데스크톱 = 코드 실행·브라우저·로컬 모델
GPU 서버 = 전문가 모델 학습·추론
클라우드 = 선택적 relay·queue·public access
```

가 됩니다.

사용자가 이미 쓰는 Tailscale 기반으로 보면:

```text
Laptop
  └── MyWorld Kernel

Desktop
  └── agent-node
      ├── Claude
      ├── Codex
      └── browser agents

GPU Server
  └── expert-node
      ├── Qwen specialist
      ├── router
      └── embedding / training
```

각 머신은 자기 credential과 파일을 가진 채로 outbound 연결만 합니다.

# 2. 하지만 시스템의 본체는 컴퓨터가 아니라 상태 커널이다

예를 들어 Codex가 다음 작업을 수행했다고 합시다.

```text
“lease race를 재현함”
```

이 정보가 Codex session 안에만 있으면 Codex가 종료될 때 사실상 사라집니다.

새 구조에서는 Codex가 커널에 다음 상태 변경 후보를 제출합니다.

```json
{
  "kind": "claim.proposed",
  "claim": "old epoch worker can still commit a stale write",
  "evidence": ["artifact:test-fencing-race"],
  "produced_by": "cell:lease-refuter",
  "runtime": "codex"
}
```

Verifier가 재현하면 커널 상태가 바뀝니다.

```text
claim:
  hypothesized → verified

task:
  investigating → defect_confirmed

next need:
  database transaction specialist required
```

이제 Codex가 죽고 Claude나 작은 로컬 모델이 대신 들어와도 동일한 상태에서 이어갈 수 있습니다.

따라서 이 시스템의 정체성은:

```text
프로세스 집합도 아니고
모델 집합도 아니고
채팅 history도 아니고

검증된 상태 전이의 연속
```

입니다.

# 3. 여기서 말하는 “상태모델”은 새로운 신경망 하나가 아니다

“상태모델”이라는 표현은 두 가지로 해석할 수 있습니다.

## A. State model as database/state machine

제가 제안한 핵심은 이쪽입니다.

```text
S_t = 현재 조직 상태
A_t = agent가 제안한 행동
E_t = 검증 증거
P_t = 권한 정책

S_{t+1} = Kernel(S_t, A_t, E_t, P_t)
```

LLM이 바로 상태를 바꾸는 것이 아니라:

```text
LLM → State transition proposal
Verifier → evidence
Kernel → accepted transition
```

으로 움직입니다.

초기에는 다음만으로도 만들 수 있습니다.

```text
SQLite 또는 PostgreSQL
append-only event log
typed JSON schemas
projection engine
NATS/Redis queue
Python supervisor
```

블록체인이나 거대한 분산 시스템이 필수는 아닙니다.

## B. State model as learned world model

그 위에 학습된 상태 모델을 추가할 수 있습니다.

예:

```text
현재 task graph
전문가 상태
과거 성공·실패
비용과 지연
열린 모순
```

을 입력받아:

```text
다음에 어떤 Need가 발생할지
어떤 expert coalition이 좋을지
어디서 실패할지
어떤 실험이 정보량이 높은지
```

를 예측하는 작은 모델입니다.

$$
\hat S_{t+1},\hat R_t
=
M_\theta(S_t,A_t)
$$

하지만 이 모델은 **진실을 결정하는 커널이 아니라 미래를 예측하는 보조 기관**이어야 합니다. 틀릴 수 있기 때문입니다.

```text
State Kernel = 법과 기록
State Model  = 예측과 계획
```

둘을 합치면 안 됩니다.

# 4. 최종적으로는 세 가지 실행 모드가 생긴다

## Mode 1 — 한 몸: Personal Organism

모든 것이 네 PC 한 대에서 돕니다.

```text
myworld serve --local
```

```text
SQLite
local event bus
Claude/Codex subprocess
Ollama
git worktrees
local dashboard
```

장점:

- 구현이 단순함
- credential이 밖으로 나가지 않음
- 인터넷 없이도 일부 기능 작동
- 개인용 AIOS에 가장 적합

이 모드만으로도 sessionless expert society를 구현할 수 있습니다.

## Mode 2 — 분산된 한 몸: Personal Cluster

네가 소유한 여러 장비가 하나의 유기체처럼 작동합니다.

```text
              Sovereign Kernel
                   Laptop
                      │
             Tailscale / outbound WSS
       ┌──────────────┼───────────────┐
       ▼              ▼               ▼
 Desktop organ    GPU organ       Mobile organ
 coding/browser   model/train     sensor/control
```

이때도 하나의 조직입니다.

각 머신의 차이는 “다른 사람”이 아니라:

```text
시각기관
운동기관
기억기관
추론기관
```

처럼 볼 수 있습니다.

이 구조가 현재 사용자에게 가장 적합한 목표입니다.

## Mode 3 — 여러 유기체의 사회: Federation

다른 사람의 MyWorld, 외부 Agent 조직, 회사 서버와 연결됩니다.

```text
Your MyWorld
      ↕ AgentNet / A2A
Another MyWorld
      ↕
Research Lab Agent Network
      ↕
Public Expert Market
```

이때 각 조직은 자기 커널과 credential을 유지합니다.

서로 공유하는 것은:

```text
capability
task offer
claim
artifact
evidence
verdict
payment/credit
```

입니다.

상대방의 전체 memory나 파일 시스템을 공유하는 것은 아닙니다.

이 단계에서 비로소 **새로운 생태계**가 형성됩니다.

# 5. 클라우드는 꼭 필요한가

필수는 아닙니다.

초기 구조는 local-first가 맞습니다.

```text
클라우드 없이:
  네 컴퓨터가 켜져 있을 때 작동
  Tailscale로 네 장비들 연결
  local DB가 canonical state

클라우드 포함:
  장비가 offline이어도 message 보존
  모바일에서 접속
  webhook/Telegram/GitHub event 수신
  여러 사용자 federation
```

권장 구조는:

```text
Local kernel = canonical authority
Cloud relay  = availability layer
```

입니다.

클라우드가 다음을 소유하면 안 됩니다.

```text
원본 credential
무제한 파일 접근 권한
최종 permission authority
유일한 조직 memory
```

클라우드는 다음 정도만 담당합니다.

```text
encrypted message queue
endpoint discovery
presence
push notification
optional replicated state
```

# 6. 상태는 어디에 저장되는가

현실적인 배치는 다음입니다.

## Local canonical store

```text
~/.myworld/
├── kernel/
│   ├── events.db
│   ├── projections.db
│   └── constitution.json
├── artifacts/
├── experts/
├── models/
├── traces/
└── secrets/
```

## Repo-local tissue declaration

```text
project/
├── .organism/
│   ├── tissue.yaml
│   ├── policies.yaml
│   └── experts.yaml
├── src/
└── tests/
```

Repo에는 선언과 versioned policy만 둡니다.

실시간 실행 상태 전체를 repo 안에 넣지는 않습니다.

## Optional replicated cloud state

```text
event ID
encrypted payload
artifact hash
delivery cursor
presence
```

원본 artifact와 secret은 필요에 따라 로컬에만 남길 수 있습니다.

# 7. “새로운 생태계”는 정확히 무엇인가

생태계의 핵심은 사람들이 같은 모델을 쓰는 것이 아닙니다.

각 노드가 다음 protocol을 이해하는 것입니다.

```text
나는 무엇을 할 수 있다
이 task를 받을 수 있다
이 주장을 제안한다
이 evidence를 생산했다
이 artifact를 검증해 달라
이 작업을 완료했다고 주장한다
이 permission이 필요하다
이 반례로 기존 claim을 철회한다
```

그러면 모델 종류는 중요하지 않게 됩니다.

```text
Claude Cell
Codex Cell
Qwen-3B specialist
Kimi researcher
Graph router
SAT solver
human expert
```

모두 같은 사회 객체를 생산합니다.

```text
Claim
Task
Evidence
Artifact
Verdict
```

즉 생태계의 공통 기반은 **공통 model weight가 아니라 공통 state protocol**입니다.

# 8. 권장 최종 배치

사용자 환경에는 다음 구조가 가장 타당합니다.

```text
┌─────────────────────────────────────────────┐
│ Laptop / Main interface                    │
│                                             │
│ MyWorld Sovereign Kernel                   │
│ Main conversation projection               │
│ Mission / Claim / Task / Permission graph  │
└────────────────────┬────────────────────────┘
                     │ Tailscale
       ┌─────────────┼─────────────────┐
       ▼             ▼                 ▼
┌────────────┐ ┌────────────┐  ┌──────────────┐
│ Desktop    │ │ GPU Server │  │ Cloud Relay  │
│            │ │            │  │ optional     │
│ Claude     │ │ SLM pool   │  │ queue        │
│ Codex      │ │ LoRA pool  │  │ webhook      │
│ agy        │ │ router     │  │ mobile access│
│ browser    │ │ training   │  │ federation   │
└────────────┘ └────────────┘  └──────────────┘
```

그리고 시간이 지나면:

```text
한 사람의 여러 컴퓨터
       ↓
한 유기체

여러 사람의 MyWorld
       ↓
여러 유기체의 사회

공유 expert/task/evidence protocol
       ↓
Agent 생태계
```

로 확장됩니다.

# 한 문장으로 정리하면

> **처음에는 네 컴퓨터들 위에서 돌아가는 local-first 유기체이고, 궁극적으로는 컴퓨터·세션·provider를 초월해 검증된 상태와 전문가를 교환하는 새로운 Agent 생태계가 된다.**

가장 중요한 설계 결정은 **“클라우드냐 로컬이냐”가 아니라, 어느 머신에서도 재생성 가능한 상태 커널이 유일한 주권자가 되게 하는 것**입니다.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)