# AIOS AgentNet Design

Checked on 2026-07-24 KST against current public protocol docs:

- MCP specification: https://modelcontextprotocol.io/specification/2025-06-18
- MCP roadmap: https://modelcontextprotocol.io/development/roadmap
- A2A protocol: https://a2a-protocol.org/latest/
- A2A specification: https://a2a-protocol.org/latest/specification/
- AG-UI overview: https://docs.ag-ui.com/introduction
- OpenAI Apps SDK MCP/security docs:
  https://developers.openai.com/apps-sdk/concepts/mcp-server and
  https://developers.openai.com/apps-sdk/guides/security-privacy

## Decision

AIOS should treat `thread_id` as the canonical persistent state, not any one
provider session. Browser URLs, Codex session IDs, Claude session IDs, Agy
conversation handles, A2A `contextId`, and A2A `taskId` are provider-native
handles attached to the canonical AIOS/Council thread.

The networking substrate should be `AgentNet`: a local-first, federatable
agent mailbox and event ledger that can bridge:

- Agent to user interface: AG-UI-style event stream.
- Agent to tools/data: MCP-style tools, resources, prompts, and auth scopes.
- Agent to agent: A2A-style discovery, task lifecycle, streaming, push, and
  opaque agent internals.
- Agent to local CLI/browser providers: Council substrate adapters.

## Why

Current Council/PrizeHunter/AIOS failures come from treating provider process
state as durable state. That cannot hold across CLI process exits, browser tab
loss, provider auth prompts, rate limits, remote user boundaries, or model
handoffs.

The durable object has to be independent of transport:

```text
thread_id
  -> append-only messages
  -> summarized context packs
  -> native provider handles
  -> tasks / receipts / artifacts
  -> policy grants / consent / retention metadata
```

If native resume works, AgentNet uses it. If it fails or is missing, AgentNet
rehydrates the provider from the thread transcript and accepted memory/context
pack.

## Protocol Split

| Plane | Standard To Align With | AIOS Owner | Purpose |
| --- | --- | --- | --- |
| user/browser event plane | AG-UI | MyWorld + Hive | streaming UI state, approvals, interrupts, previews |
| tools/data plane | MCP | CapabilityOS + Hive | tool discovery, tool calls, resources, auth scopes |
| agent-agent plane | A2A | Hive + CapabilityOS | discovery, task delegation, async work, task refs |
| memory/provenance plane | AIOS/MemoryOS | MemoryOS | accepted context, draft memories, retrieval traces |
| policy/authority plane | AIOS smart contract | MyWorld | consent, scope, stop conditions, receipts |

MCP and A2A are complementary: MCP equips an agent with tools; A2A lets
independent agents coordinate without exposing internals. AG-UI is the
frontend/user event layer.

## Minimal Envelope

```json
{
  "schema_version": "agentnet.message.v1",
  "envelope_id": "evt_...",
  "idempotency_key": "idem_...",
  "tenant_id": "local-or-org",
  "thread_id": "th_...",
  "context_id": "ctx_...",
  "task_id": "task_...",
  "from": {"agent_id": "did-or-local-id", "surface": "codex|claude|agy|browser|a2a"},
  "to": {"agent_id": "did-or-local-id", "surface": "any"},
  "intent": "ask|delegate|review|approve|interrupt|result|observe",
  "body": {"mime": "text/markdown", "text": "..."},
  "attachments": [{"artifact_id": "sha256:...", "mime": "application/json"}],
  "capabilities_requested": ["repo.read", "web.search", "tool.call"],
  "policy": {
    "authority": "read_only|workspace_write|dangerous_opt_in",
    "requires_human_confirm": false,
    "retention": "local|shared_redacted|delete_after_task",
    "raw_prompt_storage": "avoid_unless_required"
  },
  "provenance": {
    "parent_event_ids": [],
    "source_refs": [],
    "receipt_refs": []
  },
  "native_handles": {
    "browser_url": "",
    "codex_session_id": "",
    "claude_session_id": "",
    "agy_conversation_id": "",
    "a2a_context_id": "",
    "a2a_task_id": ""
  },
  "created_at": "2026-07-24T00:00:00+09:00",
  "expires_at": null,
  "signature": "optional-detached-signature"
}
```

## Runtime Components

1. `agentnetd`

   Local daemon with SQLite/Postgres-compatible tables:
   `agents`, `agent_cards`, `threads`, `messages`, `tasks`,
   `provider_sessions`, `artifacts`, `policy_grants`, `receipts`.

2. `council-adapter`

   Bridges CLI/browser/API providers into AgentNet. It owns prompt
   rehydration, native handle capture, retries, and normalized responses.

3. `a2a-gateway`

   Publishes an Agent Card, accepts A2A messages, maps `contextId` to
   `thread_id`, maps `taskId` to AIOS task/dispatch IDs, and can push task
   updates by webhook/SSE when allowed.

4. `mcp-gateway`

   Exposes approved AgentNet operations as MCP tools/resources. It never
   exposes raw private memory by default; it returns bounded context packs and
   receipt references.

5. `agui-gateway`

   Streams user-facing events: token output, task status, artifact previews,
   approval requests, cancellation, retry, and escalation.

6. `federation-relay`

   Store-and-forward mailbox for other users' agents. It validates identity,
   scopes, idempotency keys, quotas, retention policy, and signatures before
   appending anything to the local ledger.

## Federation Rule

Remote agents must be treated as opaque and untrusted by default.

Allowed by default:

- capability discovery
- read-only questions over redacted context packs
- task result summaries
- signed receipt references

Requires explicit grant:

- raw prompt sharing
- private file/resource sharing
- write actions
- cross-user memory import
- long-lived delegated authority

Forbidden by default:

- credential transfer
- raw browser/session export
- silent execution on behalf of another user
- accepting remote memory as reviewed MemoryOS truth

## Implementation Path

1. Local persistence: Council `msg` and `provider_session` tables, `hub ask
   --thread`, PrizeHunter dispatch through Council, AIOS Hive provider-loop
   optional Council bridge.
2. Local AgentNet daemon: promote Council's SQLite bus into explicit
   `agentnetd` APIs: `post`, `ask`, `subscribe`, `task`, `receipt`, `session`.
3. A2A-compatible gateway: publish Agent Card, implement send/get/list/cancel
   task, preserve `contextId` and `taskId` mapping.
4. MCP-compatible gateway: expose safe AgentNet tools/resources to ChatGPT,
   Codex, Claude Desktop, and other MCP hosts.
5. AG-UI bridge: stream state to web UI and browser chat surfaces with
   interrupts and resumable sessions.
6. Federation: signed remote mailbox, policy grants, redacted context packs,
   and operator-visible receipts.

## Stop Conditions

- No operation may require storing provider credentials or private session
  exports in the shared ledger.
- A remote agent result is never accepted as MemoryOS reviewed memory without a
  draft/review lifecycle.
- A remote write action must have an explicit policy grant and receipt.
- Provider-native session loss is degraded, not fatal, when thread rehydration
  can continue the work.

