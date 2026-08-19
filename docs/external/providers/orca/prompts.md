> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Prompts

> Workspace-scoped prompt registry. Edit once, every bound key picks up the new version on the next call — no redeploy, no SDK change.

Once you have a workspace and an API key (see
[Introduction](/introduction)), prompts are the next step. This page is
the canonical reference for OrcaRouter's prompt registry — what it is,
how to use it, and how it composes with the rest of the gateway.

## 1. What is the prompt registry

The prompt registry is a **workspace-scoped library of reusable system
messages**. You save a prompt once, bind any API key to it (or send a
`prompt_ref` per request), and the gateway injects that prompt as the
system message before forwarding the request to the upstream model.

Editing a prompt updates **every key bound to it** on the very next call.
No redeploy. No code change. No SDK upgrade. The binding lives in the
gateway, not in your application.

This is the same idea Langfuse and LangSmith pioneered, but with one
difference: OrcaRouter is the **delivery layer**. Your app code calls
`/v1/chat/completions` exactly as before; the gateway resolves and
injects the prompt. There's nothing to install in the application.

Prompts are workspace-scoped — every member sees the workspace's prompts;
nothing crosses tenant boundaries.

## 2. Quickstart — bind your first prompt in 5 steps

<Steps>
  <Step title="Create a prompt">
    In the console, go to `/console/prompts` and click **New prompt**.
    Name it `support-agent`. Paste the system message:

    > *"You are a concise support agent for Acme. Answer in 2 sentences or fewer."*

    Save — this creates version 1.
  </Step>

  <Step title="Bind a key">
    Go to `/console/token`, create or edit an API key, pick `support-agent`
    from the **Prompt** dropdown, and `production` from the **Label**
    dropdown.
  </Step>

  <Step title="Send a request">
    Using that key, call OrcaRouter exactly as before:

    ```bash theme={null}
    curl https://api.orcarouter.ai/v1/chat/completions \
      -H "Authorization: Bearer sk-orca-..." \
      -H "Content-Type: application/json" \
      -d '{
        "model": "openai/gpt-4o-mini",
        "messages": [
          {"role": "user", "content": "What are your business hours?"}
        ]
      }'
    ```

    The gateway prepends your saved system message before forwarding. The
    response header `X-Orca-Prompt: support-agent@production:v1` confirms
    which prompt was injected.
  </Step>

  <Step title="Edit the prompt">
    Back in `/console/prompts`, edit `support-agent` — change the system
    message. Save — version 2 is created automatically; `production`
    still points to v1.
  </Step>

  <Step title="Promote">
    Click **Labels** on the prompt row, move `production` to v2, confirm.
    The very next request through your key gets v2's system message. **No
    application change.**
  </Step>
</Steps>

That's the headline value.

## 3. Concepts: prompts, versions, labels

| Concept     | Definition                                                                                                       | Mutability                                                          |
| ----------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **Prompt**  | A named, workspace-scoped entry. Identifier: `name` (regex `^[a-zA-Z0-9._-]{1,128}$`).                           | Soft-deletable (30-day trash + purge).                              |
| **Version** | An immutable snapshot of the prompt's content. Created automatically on every save. Identifier: monotonic `int`. | Immutable — never edited, never reused.                             |
| **Label**   | A movable pointer to a version (e.g. `production` → v7).                                                         | Movable atomically via *Promote*; the audit log records every move. |

### Reserved labels

* `production` is **auto-pinned to v1** on every new prompt's first
  version. Moving it is a production-traffic switch — Owner-only RBAC.
* `latest` is **automatically maintained** by the gateway and always
  points at the newest version. You cannot move `latest` by hand.

You can add **custom labels** (e.g. `staging`, `canary`, `eu-prod`)
later via the *Labels* dialog and bind keys to them. Until a label is
pinned to a version, a key bound to `name@<that-label>` fails open
with no injection.

### Why this shape

The split between immutable versions and movable labels is the
deploy-without-code primitive. Application code refers to a *label*
(implicitly, via the key binding, or explicitly via `prompt_ref`).
Promoting moves the label — the application sees the new content on the
next call without any code change. Rolling back is just promoting an
older version onto the label.

## 4. Production patterns: promote, rollback, staged release

### Promote

Open *Labels* on a prompt row, pick the target version, click *Promote*.
The label move is atomic and audited (the audit log shows who moved
which label from which version to which version, when). Every key bound
to `name@<label>` picks up the new version on the next request.

<Note>
  **Owner-only.** Promote is a production-traffic change and is gated to
  workspace Owners (`POST /api/prompt/:id/label`). Developers and Viewers
  see the labels list and the audit history but no *Promote* button; the
  dialog surfaces an inline "ask an Owner" hint so the gate is visible
  rather than silent.
</Note>

### Rollback

*Restore* on an older version in the *History* drawer. Restore copies
that version's content forward as a **new** version (history is never
mutated) and moves `latest` to it. To make traffic actually fall back,
*Promote* the relevant label to the restored version.

### Staged release

Bind your canary keys to `name@staging`, your prod keys to
`name@production`. Promote `staging` to a new version, observe in
Insights, then promote `production` when satisfied. No key edits, no
deploy, no SDK update.

### A/B traffic split

The Label dialog has a *Split traffic* toggle. Enable it to point a
single label at multiple versions with weighted distribution
(e.g. v7: 60%, v8: 40%). Bucketing is deterministic per
`(workspace, token, request-id)` so a single conversation stays on the
same bucket across retries.

## 5. Templating: `{{var}}` substitution

Prompt content supports Mustache-style `{{var}}` placeholders. Caller
values come from `prompt_ref.variables` (see [§6](#6-per-request-override-prompt_ref)).

Rules:

* **Single-pass substitution.** Variable values are emitted as literal
  text. They are NOT re-evaluated as a template — this prevents prompt
  injection where a caller-supplied value tries to inject more
  `{{...}}` directives.
* **Unknown placeholders stay verbatim.** If a placeholder `{{foo}}` has
  no matching variable, the literal `{{foo}}` is emitted (and a warning
  is logged). Requests never fail because a variable was missing.
* **Dotted access.** `{{user.name}}` walks nested objects when the
  caller passes a nested map.
* **Sections.** `{{#flag}}...{{/flag}}` shows the block only when `flag`
  is truthy. Inverted sections (`{{^flag}}...`) show the block when
  `flag` is missing/falsy.
* **Rendered size cap: 256 KiB.** If the final rendered text exceeds
  this threshold, the entire injection is skipped (the response carries
  no `X-Orca-Prompt` header) and the request is forwarded unchanged —
  protection against variable-blowup amplification.

External providers honor their native syntax:

* **Langfuse** prompts use the same `{{var}}` Mustache syntax.
* **LangSmith** prompts declare `template_format: f-string | mustache`
  in their manifest. The gateway honors that declaration.

## 6. Per-request override: `prompt_ref`

Override or select a prompt **per request** without changing the key
binding. Add a top-level `prompt_ref` field to the request body:

```json theme={null}
{
  "model": "openai/gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "Who is on call tonight?"}
  ],
  "prompt_ref": {
    "name": "support-agent",
    "label": "staging",
    "variables": {
      "product_name": "Orca"
    }
  }
}
```

Precedence (highest wins): request `prompt_ref` > key binding (native
`PromptId`/`PromptLabel` or `PromptProviderId`) > channel `SystemPrompt`

> none.

`prompt_ref` is **consumed by the gateway and stripped before forwarding
upstream** — strict providers never see the unknown field.

Shape:

```ts theme={null}
type PromptRef = {
  provider?: string;   // omit for native; or the provider's configured name for external
  name: string;        // required
  label?: string;      // mutually exclusive with `version`
  version?: string;    // pin to a specific version
  variables?: { [key: string]: string };  // mustache substitution
};
```

Use cases: A/B testing different prompt versions for the same key;
canary rollout from the caller side; per-request variable interpolation.

## 7. Chat-shaped prompts (system + few-shot)

Most prompts are a single system string. But sometimes you want the
gateway to inject a richer template — a system message plus a few-shot
sequence of user/assistant turns. The registry supports this as
`kind: 'chat'`.

The console *Create prompt* modal exposes a `Text` / `Chat` toggle. When
you pick `Chat`, the content editor becomes a list of
`{role, content}` rows (system, user, assistant) — add as many as you
need. On save, the rows are persisted as `messages_json`. Once created,
`kind` is immutable.

Behavior on injection:

* **No system message in the request** ⇒ the gateway prepends the
  template's system message and the template's few-shot turns appear
  *before* the caller's messages.
* **System message in the request** ⇒ injection follows the format
  adapter's default. For OpenAI-shaped requests, the template's system
  message is prepended; for Claude-shaped requests, the template's
  system goes into the native `system` parameter.

For external chat prompts (Langfuse, LangSmith), the gateway flattens
the template into the same shape.

## 8. Relationship to the rest of the gateway

| Surface        | Composes with Prompts how?                                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Models**     | Prompts are model-agnostic. The same prompt rides over GPT-5, Claude, Gemini. Routing picks the upstream model based on the request's `model` and the key's group — Prompts never overrides that. |
| **Routing**    | Routing runs first; the prompt resolver runs after. So the resolved prompt rides whatever channel the router picked, including across a fallback chain.                                           |
| **Guardrails** | Guardrails are an independent gate that inspects and redacts content. Prompts inject a system message; they do not bypass policy. A request can carry both — guardrails always run.               |
| **API Keys**   | A key binds to a prompt at a label (e.g. `support-agent@production`). The binding lives on the key in the gateway, so promoting a new version shifts every key on that label at once.             |
| **Insights**   | Every request stamps `prompt_id`, `prompt_version`, `prompt_label` on its log row. Insights slices by prompt — usage, error rate, latency, cost.                                                  |

The router stays the **sole model authority**. Even external prompts
that declare a `config` (Langfuse `config.model`, LangSmith
`model_config`) — the gateway ignores those fields. Prompts inject text
only; model selection is the router's job.

## 9. External sources: Langfuse, LangSmith, Generic HTTP

Federation: connect an external prompt source once, then bind keys or
send `prompt_ref` against names hosted there. Native and external
prompts bind and serve identically — only the resolver backend differs.

Supported sources:

* **Langfuse** — `GET {base}/api/public/v2/prompts/{name}?label=...`,
  Basic auth from your `public:secret` pair. Text and chat prompts.
* **LangSmith** — `GET {base}/commits/{owner}/{name}/{tag|hash|latest}`,
  `x-api-key` header. The gateway parses the serialized manifest to
  extract messages/text and the `template_format` declaration. Embedded
  `model_config` / `model_provider` fields are stripped (defense in
  depth: the registry serves text only).
* **Generic HTTP** — operator-configured connector for any prompt
  registry that exposes a single HTTP call per fetch. See below for the
  configurable fields.

Connect a source under **Integrations → Prompt sources** (Owner-only
config; secrets are stored encrypted, masked on read). The Test & Save
flow dry-resolves a known prompt before persisting and rejects
SSRF-blocked URLs (loopback, private, link-local, metadata ranges).

### Generic HTTP connector fields

A Generic HTTP source is a "describe one HTTP call and one response shape"
adapter. Used for self-hosted prompt stores AND for third-party platforms
that don't need their own backend integration (PromptLayer, simple custom
APIs, etc.). The fields are deliberately small — multi-step flows or
provider-specific protocols are out of scope.

| Field              | Default                         | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------ | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| URL template       | required                        | The full request URL with `{name}` / `{label}` / `{version}` placeholders. Placeholders in the path use `PathEscape`; placeholders in the query string use `QueryEscape` so `&`/`=` in a prompt name can't inject extra query params.                                                                                                                                                                                                                                                          |
| HTTP method        | `GET`                           | `GET` or `POST`. Choose POST when the platform requires a request body.                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Auth header name   | `Authorization`                 | The HTTP header the secret is sent in. Set to `X-API-KEY` (or similar) for providers that use a custom header.                                                                                                                                                                                                                                                                                                                                                                                 |
| Auth scheme prefix | `Bearer ` (with trailing space) | String prepended to the secret in the header value. Set to empty if the platform expects a raw API key, or to `Token ` / other custom prefix.                                                                                                                                                                                                                                                                                                                                                  |
| Body template      | empty                           | POST-only. The raw request body with two placeholder families. **Verbatim**: `{name}` / `{label}` / `{version}` substitute the literal value (use for form-encoded, XML, or template bodies — you own escaping). **JSON-safe**: `{name_json}` / `{label_json}` / `{version_json}` substitute a fully quoted JSON string literal (e.g. `"hello"`) — use these INSIDE JSON bodies so a request-side prompt name containing `"` / `\` / control characters cannot inject sibling fields upstream. |
| Response JSON path | empty                           | Optional dot-path into the response JSON where the prompt payload lives (e.g. `data.0.template.messages`). Empty = auto-detect top-level `text` / `prompt` / `messages` shapes.                                                                                                                                                                                                                                                                                                                |

Example — connecting PromptLayer manually:

```
URL template:        https://api.promptlayer.com/rest/get-prompt-template?prompt_name={name}&label={label}&version={version}
HTTP method:         GET
Auth header name:    X-API-KEY
Auth scheme prefix:  (empty)
Body template:       (empty)
Response JSON path:  prompt_template.messages
Secret:              <your PromptLayer API key>
```

### Resiliency

* **TTL cache** (default 60s) so prompt edits propagate within a minute.
* **Stale-while-revalidate** — cached value serves while the next
  refresh runs in the background.
* **Stale-on-error** — if the external source returns 5xx or times out,
  the gateway serves the last-known-good response. User traffic is
  never hard-failed by a provider outage.

## 10. Observability

Every prompt-injected request leaves four breadcrumbs.

### Response header

```
X-Orca-Prompt: support-agent@production:v7 (native)
```

Format:

* Native: `name@label:vN (native)` (or `name@label (native)` when the
  version int is unknown).
* External: `name@label:<provider-version-tag> (langfuse)` etc.
* Label omitted ⇒ no `@label` segment.

### Log columns

`Log.PromptId`, `Log.PromptVersion`, `Log.PromptLabel` — typed columns,
indexed for Insights queries.

### Insights drilldown

In `/console/insights`, the filter row has a **Prompt** facet — pick a
prompt and every tab (latency, errors, cost) filters to that
`prompt_id`. This is the loop closure for "I edited a prompt — what
changed about the traffic?".

### Audit

Every label move and rollback is recorded in the prompt's **Promote
history** with actor user id, timestamp, from-version, and to-version.
Visible to every member; mutate gated by Owner role.

## 11. API reference

All routes are workspace-scoped via the `X-Workspace-Id` header. RBAC
is enforced consistently: reads are open to every member; writes are
Developer+; production-traffic changes (label moves, rollbacks,
provider config, webhooks) are Owner-only.

### Prompts

| Method & path                       | Role       | Purpose                                                                              |
| ----------------------------------- | ---------- | ------------------------------------------------------------------------------------ |
| `GET /api/prompt/`                  | Member     | List prompts (paginated, supports `?tag=`).                                          |
| `GET /api/prompt/?in_trash=true`    | Owner      | List soft-deleted prompts (Owner-only — recovery class).                             |
| `GET /api/prompt/search`            | Member     | Keyword + tag search (rate-limited).                                                 |
| `GET /api/prompt/tags`              | Member     | Tag typeahead for the workspace.                                                     |
| `GET /api/prompt/:id`               | Member     | Single prompt detail.                                                                |
| `GET /api/prompt/:id/versions`      | Member     | Version history (newest first).                                                      |
| `GET /api/prompt/:id/labels`        | Member     | Current label → version map.                                                         |
| `GET /api/prompt/:id/tags`          | Member     | Tag set for one prompt.                                                              |
| `GET /api/prompt/:id/label_history` | Member     | Promotion audit log.                                                                 |
| `GET /api/prompt/:id/analytics`     | Member     | Per-prompt usage chart data.                                                         |
| `GET /api/prompt/analytics/top`     | Member     | Workspace-wide most-used prompts.                                                    |
| `POST /api/prompt/`                 | Developer+ | Create prompt (text or chat).                                                        |
| `PUT /api/prompt/`                  | Developer+ | Update prompt (creates a new version).                                               |
| `POST /api/prompt/:id/tags`         | Developer+ | Replace the tag set.                                                                 |
| `POST /api/prompt/:id/run`          | Developer+ | Playground "Try it" (rate-limited 30/min/workspace).                                 |
| `DELETE /api/prompt/:id`            | Developer+ | Soft-delete to trash (default); `?purge=true` is Owner-only hard delete.             |
| `POST /api/prompt/:id/restore`      | Owner      | Restore from trash.                                                                  |
| `POST /api/prompt/:id/rollback`     | Owner      | Restore an older version as a new version.                                           |
| `POST /api/prompt/:id/label`        | Owner      | Move a label to a version (atomic, audited; also accepts a `split` payload for A/B). |

### Prompt providers (federation)

| Method & path                                  | Role       | Purpose                                            |
| ---------------------------------------------- | ---------- | -------------------------------------------------- |
| `GET /api/prompt_provider/`                    | Member     | List connected sources (masked secrets).           |
| `POST /api/prompt_provider/`                   | Owner      | Connect a source.                                  |
| `PUT /api/prompt_provider/`                    | Owner      | Update a source.                                   |
| `DELETE /api/prompt_provider/:id`              | Owner      | Disconnect.                                        |
| `POST /api/prompt_provider/test`               | Owner      | Dry-resolve before save.                           |
| `GET /api/prompt_provider/:id/prompts`         | Member     | List prompts available in an external source.      |
| `POST /api/prompt_provider/:id/prompts/import` | Developer+ | Import an external prompt into the local registry. |

### Prompt webhooks

| Method & path                       | Role   | Purpose                               |
| ----------------------------------- | ------ | ------------------------------------- |
| `GET /api/prompt_webhook/`          | Member | List webhooks.                        |
| `POST /api/prompt_webhook/`         | Owner  | Add a webhook (secret returned once). |
| `PUT /api/prompt_webhook/:id`       | Owner  | Edit.                                 |
| `DELETE /api/prompt_webhook/:id`    | Owner  | Remove.                               |
| `POST /api/prompt_webhook/:id/test` | Owner  | Send a sample event.                  |

### Webhook event delivery

Each delivery POSTs a JSON envelope to your configured URL:

```json theme={null}
{
  "event": "label.promoted",
  "workspace_id": "ws_...",
  "occurred_at": "2025-01-15T08:30:00Z",
  "data": { "...": "event-specific fields" }
}
```

Event types: `prompt.created`, `prompt.updated`, `prompt.deleted`,
`label.promoted`, `version.rolled_back`.

Headers on every delivery:

* `X-Orca-Webhook-Id` — your webhook's id (use to dedupe).
* `X-Orca-Event` — same as the envelope's `event` field.
* `X-Orca-Signature` — formatted as `sha256=<hex>`, where `<hex>` is
  the HMAC-SHA256 of the raw request body keyed with the webhook
  secret. Compare in constant time.

### Request payload addition

```ts theme={null}
type ChatCompletionsRequest = {
  // ... all existing OpenAI-compatible fields ...
  prompt_ref?: PromptRef;  // gateway-only; stripped before upstream
};
```

## 12. FAQ

<AccordionGroup>
  <Accordion title="What if no prompt resolves on a request?">
    Behavior is byte-identical to a workspace that never enabled the
    feature. If the key isn't bound, no `prompt_ref` is present, and no
    channel default is set, the gateway makes zero modifications. The
    response carries no `X-Orca-Prompt` header. Log columns are NULL.

    This is the regression guarantee: the resolver is a verified no-op
    when nothing is bound.
  </Accordion>

  <Accordion title="How does SystemPromptOverride interact with the registry?">
    `SystemPromptOverride` is the existing channel-level system-prompt
    default. A bound registry prompt overrides the channel default —
    documented and intentional. When nothing resolves, the channel
    default still works exactly as before.

    When the caller's request already includes a system message,
    behavior is decided by the format adapter: OpenAI-shaped requests
    get the template's system message prepended; Claude-shaped requests
    place the template's system in the native `system` parameter.
  </Accordion>

  <Accordion title="Can I limit which prompts a specific key can use?">
    Not in v1. Any key may `prompt_ref` any prompt in *its own*
    workspace. This matches the workspace-scoped key model from Langfuse
    and LangSmith. Cross-workspace access is denied at the resolver
    level (re-checked in the relay path; never trusted from a stale
    binding).

    Per-key prompt allowlists are a possible future add.
  </Accordion>

  <Accordion title="Are injected prompt tokens billed?">
    Yes. Injected system-prompt tokens count toward usage / quota /
    billing exactly like any other system message. Over-long prompts
    that exceed the model's context window return the upstream's normal
    error — the gateway does not pre-truncate.
  </Accordion>

  <Accordion title="Does the registry override the model?">
    No. External providers' `config.model` / `model_config` fields are
    ignored. Model selection stays the router's sole authority — Prompts
    inject text only.
  </Accordion>

  <Accordion title="What happens to a key bound to a deleted prompt?">
    The resolver treats missing / deleted / unauthorized prompts as
    **fail-safe skip** — the request is forwarded unchanged with no
    error to the caller. The Edit and Promote modals show a "Used by N
    keys" badge so you can see the blast radius before you delete or
    promote.
  </Accordion>

  <Accordion title="How fast do label moves propagate?">
    Native label moves are \~immediate (the gateway syncs from the DB on
    a seconds-bounded interval, plus a local-map write on the controller
    write path). External label moves appear within the configured
    cache TTL (default 60s). Both are documented expectations, not
    defects.
  </Accordion>

  <Accordion title="Can I edit chat prompts in the UI?">
    Yes. The *Create prompt* modal exposes a `Text` / `Chat` toggle;
    chat mode shows a structured `{role, content}` editor. Once a
    prompt is created, its `kind` is immutable (you'd create a new
    prompt to change shape).
  </Accordion>

  <Accordion title="Where do prompt-stamp breadcrumbs end up?">
    * Response header `X-Orca-Prompt` on the user-facing response.
    * `Log.PromptId` / `PromptVersion` / `PromptLabel` columns on the
      request log row.
    * Insights **Prompt** filter facet — pick a prompt; every Insights
      tab filters to that `prompt_id`.
  </Accordion>

  <Accordion title="How do I rotate a webhook secret?">
    Edit the webhook via `PUT /api/prompt_webhook/:id` and provide a new
    `secret` value. The new secret is shown once in the response — copy
    it then; afterwards the secret is masked. (There is no dedicated
    rotate endpoint; rotation is a normal edit.)
  </Accordion>
</AccordionGroup>

## See also

Going deeper on agent security? The **Secure Your Agents (Zero Trust)** guides put this feature in a zero-trust workflow.

<CardGroup cols={2}>
  <Card title="Defend against prompt injection" icon="syringe" href="/security/threats/prompt-injection">
    How prompt injection works against agents, and how the gateway stops it.
  </Card>

  <Card title="Block prompt injection" icon="shield-halved" href="/security/guardrails/prompt-injection">
    Turn on the injection guardrail and the spotlight defense.
  </Card>
</CardGroup>
