> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Firewall

> Workspace-scoped policy plane for agent tool calls. Govern what your agents are allowed to do — block, sanitize, hold-for-approval, or cap the cost of every tool call, MCP dispatch, and outbound request, with no change to your agent code.

Guardrails screen the *text* that flows through a model. The **Firewall**
governs the *actions* an agent takes — the tools it calls, the MCP
servers it reaches, the skills it loads, and the hosts it talks to. It is
the action-layer peer of [Guardrails](/features/guardrails): same
workspace scoping, same attach-once model, same "policy lives in the
gateway, not your app" promise.

This page is the conceptual overview and operations reference. Three
companion pages cover the moving parts in depth:

<CardGroup cols={3}>
  <Card title="Rules" icon="filter" href="/features/firewall-rules">
    The matching language — tool globs, argument clauses, egress lists,
    sanitizers, and sequences.
  </Card>

  <Card title="MCP servers" icon="plug" href="/features/firewall-mcp">
    Register and govern Model Context Protocol servers behind a single
    audited gateway.
  </Card>

  <Card title="Skills" icon="shield-halved" href="/features/firewall-skills">
    Scan and risk-score the capabilities your agents install before they
    can run.
  </Card>
</CardGroup>

## 1. What is the Firewall

An AI agent doesn't just generate text — it *acts*. It calls `shell.exec`,
queries `db.query`, fetches a URL, loads a community skill, or routes a
tool call through a third-party MCP server. Each of those is an action
with real-world consequences, and prompt-level guardrails can't see them.

The **Firewall** is a **workspace-scoped, named policy** that the gateway
evaluates on every tool call. You author a policy once, attach an API key
to it (or set one as the workspace default), and from then on every tool
call that key issues is checked against the policy — *before* it reaches
the tool.

Each policy is an ordered list of **rules**. A rule decides one thing —
*which tool calls it applies to* (a tool-name glob, optionally scoped to a
skill and to an enforcement surface) and *what to do about them* (a
**verdict**: allow, audit, deny, sanitize, hold for approval, or cap
cost). The engine walks the rules in priority order, **first match wins**,
and falls back to the policy's default verdict if nothing matches.

Editing a policy takes effect on **every key attached to it** on the next
call. No redeploy. No agent-code change. The policy is enforced at the
gateway — your agent keeps issuing tool calls exactly as before.

<Note>
  **Detection happens at the gateway, on first use.** The Firewall sits on
  the LLM-relay path, not inside your agent's package manager or
  filesystem. A tool, MCP server, or skill an agent self-installs is caught
  the first time its call crosses the gateway — not at install time. This is
  deliberate: it's the one choke point that sees *every* provider, every
  agent, and every tool call regardless of how the capability got there.
</Note>

## 2. The four enforcement surfaces

Every tool call is evaluated against exactly one **surface** — the point
in the request lifecycle where the firewall sees it:

| Surface        | What it sees                                                                                                                                         |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`inbound`**  | The tools an agent *advertises* to the model on the request (tool definitions). Lets you block a dangerous tool before the model can even choose it. |
| **`response`** | The `tool_calls` the model *emits* in its reply.                                                                                                     |
| **`mcp`**      | A `tools/call` dispatched through the [Firewall MCP gateway](/features/firewall-mcp) or evaluated via the SDK hook.                                  |
| **`egress`**   | An outbound network destination (host / IP / CIDR) reported by a tool — the SSRF and data-exfiltration surface.                                      |

A rule with no stage applies to **all** surfaces; pin a rule to one
surface when a verdict only makes sense there (e.g. an egress allowlist).

## 3. Core concepts

| Concept             | Definition                                                                                                                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Policy**          | A named, workspace-scoped set of rules. Has `enabled`, `is_default`, a `default_verdict`, and a `shadow_mode` flag.                                                                             |
| **Rule**            | One check inside a policy: a priority, a tool/skill match, an optional surface, an optional argument predicate, and a verdict. See [Rules](/features/firewall-rules).                           |
| **Verdict**         | The action a rule (or the default) produces — see [§4](#4-verdicts).                                                                                                                            |
| **Default verdict** | Applied when no rule matches. One of `allow`, `audit` (default), or `deny`.                                                                                                                     |
| **Shadow mode**     | The policy evaluates and logs but never blocks — every enforcing verdict is downgraded to `audit` and the reason is prefixed `[shadow] would …`. Your safe-rollout switch.                      |
| **Observe mode**    | A workspace-level setting. When a request resolves to *no* policy and observe mode is on, the call is allowed but logged as a coverage *gap* — that's what populates the Discovered-tools view. |

### Scoping and resolution

Policies resolve exactly like Guardrails and API keys — workspace-shared
when you have an active workspace. For any tool call the gateway resolves
the policy in this order:

1. **Key attachment** — if the calling key has a `firewall_policy_id`,
   that policy applies (when it exists and is enabled).
2. **Workspace default** — otherwise the workspace's enabled `is_default`
   policy applies.
3. **Neither** — no enforcement. With **observe mode on**, the call is
   allowed and logged as a gap; with it off, the call is allowed silently
   (byte-identical to a workspace that never enabled the feature).

At most one policy per workspace can be the default; promoting a new
default demotes the old one in the same transaction.

<Note>
  **Fail-open on the unknown, fail-closed on the ambiguous.** If policy
  resolution hits a transient error the gateway degrades to observe/allow
  rather than taking traffic down. But where *not* enforcing would defeat
  the rule — an egress report with no usable destination, an approval store
  that's unreachable, a skill whose ownership can't be resolved — the engine
  **fails closed** (deny or hold). Availability is preserved; safety isn't
  silently skipped on the cases that matter.
</Note>

## 4. Verdicts

A rule (or the default verdict) produces one of:

| Verdict                | What it does                                                                                                                                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`allow`**            | Let the call through. Logged.                                                                                                                                                                                                                               |
| **`audit`**            | Allow, but record it for review. The default `default_verdict` — observe everything, block nothing, until you're ready.                                                                                                                                     |
| **`deny`**             | Block the call. The agent sees a tool error (or HTTP 400 on the inbound surface).                                                                                                                                                                           |
| **`sanitize`**         | Redact matched substrings from the tool *arguments* (secrets, PII) and forward the cleaned call. See [sanitizers](/features/firewall-rules#5-sanitizers). On the `inbound` surface — where there are no call-time args yet — sanitize escalates to a block. |
| **`pending_approval`** | Hold the call for a human. The agent gets a "held" response; a reviewer approves or rejects out-of-band; the agent re-submits with a single-use approval token. See [§7](#7-human-approval-hitl).                                                           |
| **`cap_cost`**         | Deny once the agent run's accumulated spend exceeds a per-rule cents cap. A circuit-breaker for runaway loops.                                                                                                                                              |

In shadow mode, `deny` / `sanitize` / `pending_approval` are all downgraded
to `audit` so you can measure a policy's impact before it changes traffic.

## 5. How a tool call is evaluated

1. A tool call reaches the gateway (advertised inbound, emitted in a
   response, dispatched through the MCP gateway, or reported as egress).
2. The engine resolves the active policy ([§3](#scoping-and-resolution)).
3. It walks the policy's rules in **priority order** (lower priority
   first; ties broken by rule id). A rule matches when its surface, its
   tool-name glob, its optional skill-name glob, its optional argument
   clauses, and its optional egress scope **all** match.
4. **First match wins** → the rule's verdict applies. If no rule matches →
   the policy's `default_verdict`.
5. If the call is owned by a governed [skill](/features/firewall-skills),
   the skill's enforcement mode is applied on top — a skill in `block`
   mode forces a deny; a skill in `quarantine` mode escalates anything
   short of deny to `pending_approval`.
6. The decision is logged as a firewall event (unless it's a dry run),
   correlated to the agent run and session.

## 6. What a block looks like

A denied call on the **inbound** surface returns **HTTP 400** with an
OpenAI-shaped error body, error code `firewall_blocked`, and a message
naming the tool and the reason — e.g. `tool "shell.exec" blocked by
firewall: destructive shell command`. The error carries structured
`metadata` (reason code, risk factors, score) and is marked **skip-retry**
(re-running the same call would just block again).

A call dispatched through the **MCP gateway** is blocked as a *tool error*
(`firewall deny: <reason>`) rather than a transport failure, so the model
sees the rejection and can react — pick another tool, ask the user, or
stop — instead of crashing.

A **held** call (`pending_approval`) returns HTTP 400 with code
`firewall_approval_pending` and an approval id the client polls on.

## 7. Human approval (HITL)

A `pending_approval` verdict turns a tool call into an out-of-band review:

1. The engine enqueues an approval record and returns a "held" response
   carrying its id; the call does **not** reach the tool.
2. A reviewer resolves it — from the console (Developer+), or via an
   **HMAC-signed webhook callback** to your own approval system.
3. Your agent (or the MCP SDK) **polls** the approval id; once approved it
   re-submits the original call with a single-use
   `X-OrcaRouter-Firewall-Approval` header, and the gateway lets it
   through that one time.

Decisions are first-writer-wins and idempotent. If the underlying rule was
edited after the hold, the enrichment notes `rule_changed` so reviewers
know the context shifted.

## 8. Autonomy levels: one switch for your whole posture

Tuning policies rule-by-rule is the precise path; **autonomy levels** are
the fast one. A single control atomically replaces your workspace's
Firewall *and* Guardrails posture in one transaction, with one-click undo:

| Level            | Posture                                                                                                                                      |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **`tight`**      | Block destructive shell, secrets in arguments, and SSRF egress (default deny); PII Shield + Secrets Blocker guardrails on; observe mode off. |
| **`balanced`**   | Audit destructive shell, flag PII; observe mode off. The recommended starting posture.                                                       |
| **`permissive`** | No enforcing policy, no guardrails; observe mode on so you still see everything.                                                             |

Undo restores the exact prior state from the audit snapshot.

## 9. Anomaly detection

Beyond static rules, the Firewall learns each workspace's normal tool-use
shape and flags deviations on a viewer-readable feed:

* **Rate / cost spikes** — per-tool activity is scored against a learned
  **hour-of-week baseline** (a 14-day rolling average), so "100 `db.query`
  calls at 3am Sunday" stands out even if each call is individually
  allowed.
* **`retry_loop`** — an agent hammering the same failing tool.
* **`novel_path`** — a tool-to-tool transition this workspace has never
  made before.

The feed reports tool names, redacted token ids, and counts only. You can
**snooze** an anomaly for up to 7 days while you investigate.

## 10. Observability

The Firewall leaves a trail you can act on, all workspace-scoped:

| Surface              | What it gives you                                                                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Events**           | Every evaluation, filterable by verdict, surface, tool, run, and session. The raw record behind everything else.                                           |
| **Runs & sessions**  | Events rolled up by agent run or conversation — verdict breakdown, distinct tools and models, first/last seen. The "what did this agent actually do" view. |
| **Discovered tools** | Every tool the workspace has seen, flagged **covered** (a rule applies) or **gap** (nothing does). Drives policy authoring from real traffic.              |
| **Simulate**         | Preview what an autonomy level *would* change before you apply it.                                                                                         |
| **Test**             | Dry-run a policy against a sample tool call and see the verdict, the matched rule, and the reason — nothing is persisted, nothing is dispatched.           |
| **Audit**            | Every policy, rule, and settings change writes an audit row (workspace + central) after the change commits. Secrets and rule blobs are never logged.       |

## 11. Relationship to the rest of the gateway

| Surface                                   | Composes with the Firewall how?                                                                                                                                       |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[Guardrails](/features/guardrails)**    | Complementary planes. Guardrails screen prompt/response *text*; the Firewall governs tool *actions*. Both can apply to one request. Autonomy levels set both at once. |
| **[Routing](/routing/model-fallbacks)**   | Independent. Routing picks the model/channel; the firewall judges the tool calls regardless of which model served them.                                               |
| **API keys**                              | A key attaches to a policy via `firewall_policy_id`; the binding lives on the key in the gateway. No attachment falls back to the workspace default.                  |
| **[MCP gateway](/features/firewall-mcp)** | The firewall *is* the MCP gateway — every server you register dispatches its `tools/call` through the engine.                                                         |
| **[Skills](/features/firewall-skills)**   | A governed skill's enforcement mode rides on top of the rule verdict, so a quarantined skill is held even if no rule names its tools.                                 |

## 12. Connecting an agent to the Firewall gateway

There are two ways a tool call reaches the engine:

* **MCP gateway** — point your MCP client (Claude Desktop, Cursor, an
  agent framework) at `https://api.orcarouter.ai/api/v1/firewall/mcp`. The
  gateway exposes every reachable registered server's tools, namespaced
  `<server>.<tool>`, and evaluates each `tools/call` inline. See
  [MCP servers](/features/firewall-mcp).
* **Evaluate hook** — call `POST /api/v1/firewall/evaluate` from your own
  agent loop *before* dispatching a tool call, and act on the verdict.

Both require a **firewall-gateway-scoped token** — a dedicated API key
minted for this purpose. A regular key gets `403` on these routes.

## 13. API reference

All console routes are workspace-scoped via the workspace context and
enforce RBAC consistently: reads and the test/simulate sandboxes are open
to every member; writes require **Developer+**.

### Policies & settings

| Method & path                                 | Role       | Purpose                                                    |
| --------------------------------------------- | ---------- | ---------------------------------------------------------- |
| `GET /api/workspace/firewall/settings`        | Member     | Read workspace firewall settings (observe mode, defaults). |
| `PUT /api/workspace/firewall/settings`        | Developer+ | Update settings.                                           |
| `GET /api/workspace/firewall/policies`        | Member     | List policies (with rule + attached-key counts).           |
| `GET /api/workspace/firewall/policies/:id`    | Member     | Single policy detail.                                      |
| `POST /api/workspace/firewall/policies`       | Developer+ | Create a policy.                                           |
| `PUT /api/workspace/firewall/policies`        | Developer+ | Update a policy.                                           |
| `DELETE /api/workspace/firewall/policies/:id` | Developer+ | Delete a policy (409 if keys are still attached).          |

### Posture, presets & sandboxes

| Method & path                                          | Role       | Purpose                                      |
| ------------------------------------------------------ | ---------- | -------------------------------------------- |
| `GET /api/workspace/firewall/presets`                  | Member     | Built-in rule presets.                       |
| `POST /api/workspace/firewall/autonomy`                | Developer+ | Apply an autonomy level.                     |
| `POST /api/workspace/firewall/autonomy/undo/:audit_id` | Developer+ | Undo an autonomy change.                     |
| `GET /api/workspace/firewall/simulate`                 | Member     | Preview an autonomy level (`?level=`).       |
| `POST /api/workspace/firewall/test`                    | Developer+ | Dry-run a policy against a sample tool call. |

### Observability

| Method & path                                               | Role       | Purpose                             |
| ----------------------------------------------------------- | ---------- | ----------------------------------- |
| `GET /api/workspace/firewall/discovered-tools`              | Member     | Tools seen, flagged covered / gap.  |
| `GET /api/workspace/firewall/events`                        | Developer+ | List firewall events (filterable).  |
| `GET /api/workspace/firewall/events/by-request/:request_id` | Developer+ | Events for one request.             |
| `GET /api/workspace/firewall/events/aggregate`              | Developer+ | Runs / sessions rollup.             |
| `GET /api/workspace/firewall/trace/by-run`                  | Developer+ | Trace nodes for a run (`?run_id=`). |
| `GET /api/workspace/firewall/anomalies`                     | Member     | Anomaly feed (`?window=`).          |
| `POST /api/workspace/firewall/anomalies/snooze`             | Developer+ | Snooze the anomaly feed.            |

Rules, MCP servers, and skills each have their own endpoints — see
[Rules](/features/firewall-rules#api-reference),
[MCP servers](/features/firewall-mcp#api-reference), and
[Skills](/features/firewall-skills#api-reference).

### Gateway (machine-to-machine)

These run on a firewall-gateway-scoped token, not the console session:

| Method & path                                  | Purpose                                    |
| ---------------------------------------------- | ------------------------------------------ |
| `POST /api/v1/firewall/evaluate`               | Pre-dispatch verdict for one tool call.    |
| `POST /api/v1/firewall/evaluate_plan`          | Pre-execution check for a multi-step plan. |
| `ANY /api/v1/firewall/mcp`                     | The unified MCP gateway endpoint.          |
| `GET /api/v1/firewall/approvals/:id`           | Poll a held call's approval state.         |
| `POST /api/v1/firewall/approvals/:id/callback` | HMAC-signed approval callback.             |

## 14. FAQ

<AccordionGroup>
  <Accordion title="What if no policy resolves on a tool call?">
    With **observe mode off**, behavior is byte-identical to a workspace
    that never enabled the feature — nothing is blocked or logged. With
    **observe mode on**, the call is allowed but recorded as a coverage
    gap so it shows up in Discovered tools.
  </Accordion>

  <Accordion title="How do I roll out a policy safely?">
    Turn on **shadow mode**. The policy evaluates and logs exactly as it
    would in production, but every enforcing verdict is downgraded to
    `audit` and the reason is prefixed `[shadow] would …`. Watch the
    events and runs views, confirm it fires on what you expect and nothing
    you don't, then turn shadow mode off to start enforcing.
  </Accordion>

  <Accordion title="Does a blocked tool call cost quota?">
    An inbound block fires before the upstream model call, so it costs no
    model tokens. Audit / allow verdicts don't change billing. A
    `cap_cost` rule is itself a billing control — it denies once the run's
    spend crosses your cents cap.
  </Accordion>

  <Accordion title="Firewall or Guardrails — which do I use?">
    Both, for different layers. **Guardrails** screen the text in prompts
    and responses (PII, secrets, jailbreaks). The **Firewall** governs the
    actions an agent takes (which tools, which MCP servers, which hosts).
    A request can pass through both. The `tight` autonomy level configures
    them together.
  </Accordion>

  <Accordion title="Is enforcement guaranteed for every tool an agent runs?">
    The Firewall enforces on tool calls that cross the gateway — the
    relay path, the MCP gateway, and the evaluate hook. A tool your agent
    executes entirely inside its own process, never touching the gateway,
    is outside the firewall's view. The design goal is to make the gateway
    the single audited path for the calls that matter (model-mediated
    tools, MCP dispatch, network egress); route those through it and they
    are governed.
  </Accordion>
</AccordionGroup>

## See also

Going deeper on agent security? The **Secure Your Agents (Zero Trust)** guides put this feature in a zero-trust workflow.

<CardGroup cols={2}>
  <Card title="Secure your agents (Zero Trust)" icon="shield-halved" href="/security/firewall/overview">
    The zero-trust agent firewall playbook — tool allow-lists, argument checks, and egress control.
  </Card>

  <Card title="Secure Agents baseline" icon="shield-check" href="/security/concepts/secure-agents-baseline">
    One switch that sets your Firewall and Guardrails posture together.
  </Card>
</CardGroup>
