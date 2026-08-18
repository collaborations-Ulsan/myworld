> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Firewall: MCP Servers

> Register Model Context Protocol servers behind a single audited gateway. Every tools/call — from the bundled server or your own remote MCP servers — is firewall-evaluated before it runs, with SSRF protection and encrypted credentials.

The [Model Context Protocol](https://modelcontextprotocol.io) (MCP) lets
agents call tools hosted by external servers. That's powerful and
dangerous in equal measure: every MCP server an agent connects to is a
fresh set of tools, credentials, and network reach that nobody reviewed.

The Firewall's **MCP gateway** puts a single audited choke point in front
of all of them. You register each MCP server once; the gateway exposes
their tools to your agents under one connection and runs every `tools/call`
through the [firewall engine](/features/firewall) before it reaches the
real server.

## 1. What MCP governance gives you

* **One gateway, every server.** Your agent connects to *one* endpoint.
  The gateway aggregates the tools of every reachable registered server,
  namespaced `<server>.<tool>`, so `github.create_issue` and
  `shell.exec` show up side by side under a single MCP connection.
* **Policy on every call.** Each `tools/call` is evaluated by your
  [policy](/features/firewall) first. A blocked call comes back to the
  model as a tool *error* (`firewall deny: …`), not a transport failure,
  so the agent can react instead of crashing. `sanitize` rewrites the
  arguments before forwarding; `pending_approval` holds the call.
* **SSRF-guarded.** Remote endpoints are validated against the gateway's
  SSRF policy — intranet ranges and cloud-metadata addresses are blocked,
  and the resolved dial IP is re-checked to defeat DNS rebinding, on every
  hop including redirects.
* **Encrypted credentials.** Server auth secrets are encrypted at rest and
  masked on read. The gateway injects them at dispatch time; they never
  reach the model or the client.

## 2. Two kinds of server

| Kind                     | `endpoint`            | Behavior                                                                                                 |
| ------------------------ | --------------------- | -------------------------------------------------------------------------------------------------------- |
| **BYO (bring-your-own)** | A streamable-HTTP URL | The gateway proxies `tools/call` to your remote MCP server.                                              |
| **Bundled**              | empty                 | OrcaRouter's in-process MCP server. Registered so it's visible and governable; not separately probeable. |

## 3. Registering a server

A server record carries:

| Field       | Notes                                                                                                         |
| ----------- | ------------------------------------------------------------------------------------------------------------- |
| `name`      | Business key, unique per workspace, ≤ 128 chars. **No `.`** — it's the `<server>.<tool>` namespace separator. |
| `endpoint`  | The MCP server URL (≤ 512 chars). Empty for the bundled server.                                               |
| `auth_mode` | `none` (default), `bearer`, `oauth`, or `basic`.                                                              |
| `auth_json` | Mode-specific credentials (see below). Required whenever `auth_mode` isn't `none`.                            |
| `enabled`   | Defaults to `true`. A disabled server is omitted from the gateway entirely.                                   |
| `status`    | Reachability — `ok` (default), `degraded`, or `down`. Set by [probing](#4-probe-discover-its-tools).          |

Credential shapes by mode:

```jsonc theme={null}
// bearer
{ "token": "ghp_…" }
// oauth
{ "client_id": "…", "client_secret": "…", "token_url": "…" }
// basic
{ "username": "…", "password": "…" }
// none
""
```

A registration request looks like:

```bash theme={null}
curl https://api.orcarouter.ai/api/workspace/firewall/mcp_servers \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "github",
    "endpoint": "https://api.githubcopilot.com/mcp",
    "auth_mode": "bearer",
    "auth_json": "{\"token\":\"ghp_x\"}",
    "enabled": true
  }'
```

A duplicate name in the same workspace returns **HTTP 409** (the same name
in a *different* workspace is fine).

<Note>
  **Secrets are never stored in plaintext.** `auth_json` is encrypted at
  rest with a workspace secrets key. If that key isn't configured, the write
  is rejected rather than persisting a credential unencrypted. On read,
  secrets and the endpoint are masked; echo the mask back on an update to
  keep the stored value. Switching between two credentialed auth modes
  requires fresh `auth_json` (the ciphertext is shape-bound to its mode).
</Note>

## 4. Probe: discover its tools

Before you can write rules against a server's tools, you need to know
their names. **Probe** the server:

```bash theme={null}
curl -X POST \
  https://api.orcarouter.ai/api/workspace/firewall/mcp_servers/42/probe \
  -H "Authorization: Bearer sk-orca-..."
```

The gateway runs an MCP `initialize` + `tools/list` against the endpoint
(using the decrypted credentials, bounded at 10s), records the
reachability `status` and a timestamp, and returns the advertised tools
with their input schemas:

```json theme={null}
{
  "status": "ok",
  "last_checked_at": 1700000000,
  "tools": [
    { "name": "create_issue", "description": "…", "input_schema": { } }
  ]
}
```

Now you can author rules like `tool_name_glob: github.*` knowing exactly
what `github.create_issue` accepts. The bundled (empty-endpoint) server
isn't probeable and returns a 400.

## 5. Lifecycle & enforcement

* **Enabled vs. disabled.** A disabled server is dropped from the runtime
  registry — its tools disappear from the gateway and its credentials are
  never decrypted. That's the off switch.
* **Reachability.** `status` (`ok` / `degraded` / `down`) reflects the
  last probe; an unreachable server is skipped when the gateway builds its
  tool set.
* **Per-call verdict.** At dispatch the engine returns a verdict for the
  specific `<server>.<tool>` call with its arguments:
  * `allow` / `audit` → forwarded (audit logs, still allows).
  * `sanitize` → forwarded with rewritten arguments.
  * `deny` / `pending_approval` / anything unknown → blocked as a tool
    error. (Through the unified gateway, a held call surfaces as a
    permanent error rather than threading the approval id — use the
    [evaluate hook](/features/firewall#12-connecting-an-agent-to-the-firewall-gateway)
    when you need the approval handshake.)
* **Deletion** is a soft delete; the name slot is freed immediately so you
  can re-register under the same name.

Every change invalidates the gateway's per-workspace tool cache
immediately, so a newly registered, disabled, or re-probed server takes
effect on the next connection rather than after a cache TTL.

## 6. Connecting a client

Point any MCP client at the gateway endpoint with a
**firewall-gateway-scoped token**:

```text theme={null}
https://api.orcarouter.ai/api/v1/firewall/mcp
```

The gateway speaks streamable HTTP (POST messages, GET for the SSE
stream, DELETE to end a session) and identifies itself as
`orcarouter-firewall-gateway`. It advertises every enabled, reachable
server's tools under the `<server>.<tool>` namespace, re-exposing each
tool's input schema verbatim. A token without the firewall-gateway scope
gets **403** — mint a dedicated gateway token for this.

## API reference

### Console (workspace-scoped, RBAC)

| Method & path                                        | Role       | Purpose                                           |
| ---------------------------------------------------- | ---------- | ------------------------------------------------- |
| `GET /api/workspace/firewall/mcp_servers`            | Member     | List servers (secrets masked, endpoint redacted). |
| `GET /api/workspace/firewall/mcp_servers/:id`        | Member     | Single server, masked.                            |
| `POST /api/workspace/firewall/mcp_servers`           | Developer+ | Register a server (409 on duplicate name).        |
| `PUT /api/workspace/firewall/mcp_servers`            | Developer+ | Update a server (id in body).                     |
| `DELETE /api/workspace/firewall/mcp_servers/:id`     | Developer+ | Soft-delete; frees the name.                      |
| `POST /api/workspace/firewall/mcp_servers/:id/probe` | Developer+ | Probe reachability + discover tools.              |

### Gateway (firewall-gateway-scoped token)

| Method & path                      | Purpose                                                                   |
| ---------------------------------- | ------------------------------------------------------------------------- |
| `ANY /api/v1/firewall/mcp`         | The unified MCP gateway dispatch endpoint.                                |
| `GET /api/v1/firewall/mcp_servers` | Runtime registry (decrypted auth, enabled servers only) for an SDK proxy. |
| `POST /api/v1/firewall/evaluate`   | Evaluate a single `tools/call` before dispatching it yourself.            |

## FAQ

<AccordionGroup>
  <Accordion title="Why route MCP through OrcaRouter at all?">
    So there's one place that sees every tool call. Without a gateway,
    each agent connects to each MCP server directly — no shared policy, no
    audit trail, no SSRF protection, and credentials scattered across
    agent configs. The gateway centralizes all of that: one connection,
    one policy, one audited log, encrypted secrets injected at dispatch.
  </Accordion>

  <Accordion title="What happens when a blocked MCP call comes back?">
    The model receives it as a tool error (`firewall deny: <reason>`), the
    same shape it would get from any failing tool. That lets the agent
    adapt — try a different approach, ask the user, or stop — instead of
    treating it as a transport crash.
  </Accordion>

  <Accordion title="Can I govern the same tool differently per server?">
    Yes — that's what the `<server>.<tool>` namespace is for. A rule with
    `tool_name_glob: trusted.*` can `allow` while `community.*` is
    `audit`ed or `pending_approval`. Combine it with a
    [skill-name glob](/features/firewall-rules#3-skill-name-glob) for even
    finer scoping.
  </Accordion>

  <Accordion title="Does the gateway protect against SSRF?">
    Yes. Endpoint URLs and their resolved dial IPs are validated against
    the SSRF policy on registration and on every dispatch hop — intranet
    ranges and the cloud-metadata address are refused, and the resolved IP
    is re-checked to defeat DNS rebinding. Pair it with an
    [egress rule](/features/firewall-rules#6-egress-destination-lists) to
    govern where tools may reach.
  </Accordion>
</AccordionGroup>

## See also

Going deeper on agent security? The **Secure Your Agents (Zero Trust)** guides put this feature in a zero-trust workflow.

<CardGroup cols={2}>
  <Card title="Secure MCP servers (Zero Trust)" icon="plug" href="/security/mcp/overview">
    Connect, authenticate, and govern MCP servers under a zero-trust posture.
  </Card>

  <Card title="MCP trust checklist" icon="list-check" href="/security/mcp/trust-checklist">
    What to verify before you trust a third-party MCP server.
  </Card>
</CardGroup>
