> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Guardrails

> Workspace-scoped content-policy engine. Attach once, every bound key is screened on the next call — block, mask, or flag prompts and responses with no redeploy and no SDK change.

Once you have a workspace and an API key (see
[Introduction](/introduction)), guardrails are how you put a content
policy in front of every model. This page is the canonical reference for
OrcaRouter's guardrail engine — what it is, how to use it, and how it
composes with the rest of the gateway.

## 1. What is the guardrail engine

A **guardrail** is a **workspace-scoped, named content policy** — an
ordered list of rules the gateway runs against request input and model
output. You save a guardrail once, attach any API key to it (or set one
as the workspace default), and the gateway screens every call before and
after the upstream model.

Each rule decides one thing — *what to look for* (a rule type), *where to
look* (a stage: request input or model output), and *what to do about it*
(an action: block, mask, or flag). The engine runs every applicable rule
and folds the results into a single decision.

Editing a guardrail takes effect on **every key attached to it** on the
next call. No redeploy. No code change. No SDK upgrade. The policy lives
in the gateway, not in your application — your app keeps calling
`/v1/chat/completions` exactly as before.

The engine is **deterministic and dependency-free** for the built-in
rule types: pure string and regex matching with no network call, safe to
run on the hot relay path. Advanced rules (external vendors, LLM judge,
contextual grounding) call out and are dispatched concurrently so a slow
check never serializes behind another.

Guardrails are workspace-scoped — every member sees the workspace's
guardrails; nothing crosses tenant boundaries.

## 2. Quickstart — screen your first request in 5 steps

<Steps>
  <Step title="Create a guardrail">
    In the console, go to `/console/guardrails` and click **New
    guardrail**. Name it `pii-shield`. Add one rule:

    * **Type:** PII detection
    * **Stage:** Input (request)
    * **Action:** Mask — redact match
    * **Entities:** `email`, `phone`, `ssn`

    Save.
  </Step>

  <Step title="Test it in the sandbox">
    Open the **Test** tab inside the editor, paste *"email me at
    [jane@acme.com](mailto:jane@acme.com)"*, pick the `input` stage, and run. The sandbox shows
    the verdict and the rendered text — `email me at [EMAIL]` — without
    sending anything upstream.
  </Step>

  <Step title="Attach a key">
    Go to `/console/token`, create or edit an API key, and pick
    `pii-shield` from the **Guardrail** dropdown. The binding lives on
    the key in the gateway.
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
          {"role": "user", "content": "Reply to jane@acme.com please"}
        ]
      }'
    ```

    The gateway masks the email to `[EMAIL]` before forwarding. The
    upstream model never sees the address.
  </Step>

  <Step title="Tighten the policy">
    Back in `/console/guardrails`, edit `pii-shield` — change the action
    on `ssn` to **Block** via per-entity override. Save. The very next
    request that contains an SSN is rejected with HTTP 400
    `guardrail_blocked`. **No application change.**
  </Step>
</Steps>

That's the headline value.

## 3. Concepts: guardrails, rules, stages, actions

| Concept       | Definition                                                                                                               |
| ------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Guardrail** | A named, workspace-scoped policy. Identifier: `name` (≤ 64 chars). Has `enabled`, `is_default`, and a `rules` JSON blob. |
| **Rule**      | One check inside a policy: a `type`, a `stage`, an `action`, plus type-specific fields. Rules run in order.              |
| **Stage**     | `input` (the request), `output` (the model's response), or `both`.                                                       |
| **Action**    | `block` (reject the call), `mask` (redact the match), or `flag` (log only — observe without changing traffic).           |

### Scoping and the workspace default

Guardrails are scoped exactly like API keys: workspace-shared when you
have an active workspace, per-user otherwise. Resolution for any request:

1. **Key attachment** — if the key has an explicit `guardrail_id`, that
   guardrail applies (when it exists and is enabled). An explicit
   attachment never silently falls back; disabling it is the off switch.
2. **Workspace default** — if the key has no attachment, the workspace's
   enabled `is_default` guardrail applies.
3. **Neither** — no enforcement. The request is byte-identical to a
   workspace that never enabled the feature.

At most one guardrail per workspace can be the default. Promoting a new
default demotes the old one in the same transaction.

<Note>
  **Fail-open by design.** If guardrail resolution hits a transient error
  (e.g. a DB hiccup), the gateway degrades to *no enforcement* rather than
  taking traffic down. Safety degrades; availability is preserved.
</Note>

### What a block looks like

A blocked request returns **HTTP 400** with error code
`guardrail_blocked` and a message naming the guardrail and the rule that
fired. A blocked request **costs you no quota** — an input-stage block
fires before metering, and an output-stage block refunds the
pre-consumed quota — and it is marked **skip-retry** (re-running the same
prompt would just block again).

## 4. Rule types

Rules fall into two groups: **built-in** (deterministic, no network) and
**advanced** (call out to a model or vendor).

| Type                                   | Group    | What it does                                                                                                            |
| -------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Keyword denylist** (`keyword`)       | Built-in | Matches any of a list of literal terms — case-insensitive, substring match (so `class` also matches `classic`).         |
| **Regular expression** (`regex`)       | Built-in | Matches an RE2 pattern (linear-time, no backreferences).                                                                |
| **PII detection** (`pii`)              | Built-in | Detects built-in entity types (and your own custom ones). See [§5](#5-pii-detection-in-depth).                          |
| **Maximum length** (`max_chars`)       | Built-in | Caps the character count of the text at a stage.                                                                        |
| **External vendor** (`external`)       | Advanced | Delegates the check to a connected vendor (Aporia, Averta, BYO webhook). See [§9](#9-external-vendors).                 |
| **LLM judge** (`llm_judge`)            | Advanced | Runs a semantic check against a model in your workspace. See [§6](#6-llm-judge).                                        |
| **Contextual grounding** (`grounding`) | Advanced | Scores the answer's faithfulness against the sources retrieved on the request (RAG). See [§7](#7-contextual-grounding). |

A guardrail mixes any number of rules of any types. Advanced rules
(`external`, `llm_judge`, `grounding`) are dispatched **concurrently** so
one slow check doesn't serialize behind another.

## 5. PII detection in depth

A `pii` rule detects sensitive entities and applies the rule's action to
each match. The built-in detector set is closed and shared by the
engine, the validator, and the rule builder:

`email`, `phone`, `credit_card`, `ssn`, `ip`, `iban`, `mac_address`,
`api_key_openai`, `aws_access_key`, `jwt`, `bitcoin_address`.

On a **mask** action, each match is replaced with a typed tag — an email
becomes `[EMAIL]`, an SSN becomes `[SSN]`, and so on.

### Custom entities

Layer your own detectors on top of the built-in set. A custom entity is:

* `name` — lowercase ASCII / digits / underscore, must start with a
  letter (e.g. `employee_id`). Flows into audit logs and telemetry
  unquoted.
* `pattern` — a Go RE2 regex (linear-time, no backreferences).
* `checksum` — optional; `luhn` validates the match with the Luhn
  algorithm (e.g. for card-like numbers).
* `mask_with` — optional verbatim replacement; defaults to
  `[<UPPERCASE_NAME>]`.

Up to **25 custom entities** per rule (each is a regex scan over the full
text, so the cap keeps the hot path linear). Compiled patterns are cached
across requests.

### Per-entity action overrides

A single PII rule can apply different actions to different entities via
`entity_actions`. One rule that **masks** emails / phones / IPs by
default but **blocks** on `credit_card` or `ssn` — instead of three
overlapping rules:

```json theme={null}
{
  "type": "pii",
  "stage": "input",
  "action": "mask",
  "entities": ["email", "phone", "ip", "credit_card", "ssn"],
  "entity_actions": {
    "credit_card": "block",
    "ssn": "block"
  }
}
```

Keys must be an enabled entity on the rule; values must be `block` /
`mask` / `flag`. The validator rejects anything else.

## 6. LLM judge

An `llm_judge` rule runs a semantic check against a model your workspace
can already call. Use it for fuzzy policies that no regex captures —
toxicity, harassment, off-topic, prompt-injection intent.

| Field              | Meaning                                                                                                                          |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `judge_model`      | The model or router alias to evaluate with (e.g. `gpt-4o-mini`, `orcarouter/cheap`). Resolved against your workspace's channels. |
| `judge_rubric`     | The system prompt describing what to flag.                                                                                       |
| `judge_format`     | One of `yes_no`, `score`, or `category` (required; the console pre-selects `yes_no`).                                            |
| `judge_threshold`  | For `score`: block/flag when the score is at or above this value.                                                                |
| `judge_categories` | For `category`: the denied list.                                                                                                 |
| `judge_timeout_ms` | Bounds the judge call. `0` → engine default.                                                                                     |
| `judge_fail_open`  | `true` (default) → a judge error is observed but the request continues; `false` → treat error/timeout as a block.                |

The judge call routes through your workspace's channels, so its tokens
are billed and attributed like any other call (as a judge sub-line). The
engine appends a JSON-schema appendix to your rubric so the model returns
parseable output.

## 7. Contextual grounding

A `grounding` rule measures the assistant's answer against the **sources
retrieved on the request** (your RAG context) and flags or blocks
answers that aren't faithful to them. It reuses the judge seam — same
workspace channels, same cost attribution.

| Field                  | Default        | Meaning                                                                          |
| ---------------------- | -------------- | -------------------------------------------------------------------------------- |
| `grounding_model`      | workspace pick | The model the runner resolves the faithfulness check to.                         |
| `grounding_rubric`     | built-in       | Overrides the default faithfulness rubric.                                       |
| `grounding_threshold`  | `0.7`          | Faithfulness floor, `0.0`–`1.0`. Below it, the action fires.                     |
| `grounding_strict`     | `false`        | When `true`, "no sources provided" is treated as a block (vs the default allow). |
| `grounding_max_bytes`  | `100000`       | Caps the concatenated source context handed to the judge.                        |
| `grounding_timeout_ms` | `3000`         | Bounds the judge call.                                                           |

## 8. Templates, the sandbox, and the eval harness

### Template library

The **New guardrail** split-button opens straight into a template, and
the full library is one click away. Presets are authored server-side so
the console, the sandbox, and these docs describe the exact same
behavior. Categories include:

* **PII** (`pii`) — PII Shield, PII Blocker (strict), Contact-Info
  Redactor, response PII redactor.
* **Secrets** (`secrets`) — AWS / OpenAI / GitHub credential blockers,
  private keys & cloud tokens, crypto wallets, secrets in output.
* **Compliance** (`compliance`) — GDPR (EU PII), PCI (full card block),
  HIPAA (PHI), financial data, compliance logger, legal-disclaimer
  enforcement.
* **Brand** (`brand`) — profanity (block / mask / multilingual),
  competitor mentions, child-safety keywords.
* **Safety** (`safety`) — prompt-injection, jailbreak,
  system-prompt-leak, self-harm.
* **Cost** (`cost`) — prompt / response size caps and token caps.
* **Agent** (`agent`) — URL filter, markdown-image, shell-tool-call,
  and SQL-injection-in-output filters.

Apply a preset as a starting point, then edit freely — a preset is a
seed, not a lock.

### The test sandbox

Every editor has a **Test** tab. Paste a sample, pick a stage, and run
the *current* policy locally — no upstream call, no quota. The sandbox
returns the verdict and (for mask rules) the rendered text, so you can
prove a rule does what you expect before attaching a key.

### Eval / red-team harness

The **Eval** tab runs a guardrail against a corpus of inputs and reports
how it scored — useful for tuning a judge rubric or proving a policy
catches known attacks before you ship it.

* **Bundled corpora** ship with the gateway — adversarial and red-team
  sets (harmful-behavior prompts, tool-injection, multilingual
  red-teaming) plus benign sets to measure false positives.
* **Custom corpora** — upload your own JSONL to test against your real
  traffic shapes.
* **Runs** are listed with their scores; open a run to inspect the
  failures sample by sample.

## 9. External vendors

An `external` rule delegates the check to a connected vendor. Connect a
vendor once under **Integrations** (the header CTA on the Guardrails
page), then reference the connection from a rule.

### Supported vendors

| Vendor                           | What it is                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------- |
| **Aporia Guardrails** (`aporia`) | SLM-ensemble policy engine for prompts and responses.                           |
| **Averta** (`averta`)            | Generic SLM-classifier endpoint (POST text → safe / unsafe + optional rewrite). |
| **BYO Webhook** (`webhook`)      | Your own URL — receive prompts and return allow / block / mask / flag verdicts. |

Aporia and Averta take a base URL + API key; the webhook takes a URL +
auth header + HMAC secret.

### Rule fields

| Field           | Meaning                                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `connection_id` | The connected integration to use (recommended path — vendor + secrets resolve from the workspace's integration at runtime).                       |
| `timeout_ms`    | Bounds the single vendor call. `0` → default.                                                                                                     |
| `fail_open`     | `true` (default) → a vendor error is observed but the request continues; `false` → treat transport error / timeout / unknown provider as a block. |

Secrets are stored encrypted and masked on read. The check call carries
the relay request's cancellation, so a cancelled request doesn't leave a
vendor call hanging.

## 10. Observability

Guardrails leave breadcrumbs you can act on.

### Matches feed

Every rule that fires records a **match** — rule type, action, a detail
string, the stage, and (when enabled) the matched substring. The
**Matches** tab on the Guardrails page is the workspace-wide feed: list,
group, filter, drill into a single match, export to CSV, and mark false
positives.

<Note>
  **Raw-content capture is opt-in.** A guardrail's **Log raw content**
  toggle is off by default — the privacy-conservative posture. With it off,
  the Matches feed records that a rule fired and its detail meta-string,
  but not the actual matched substring (e.g. the email address itself).
  Turn it on per guardrail when you need the substring for triage; the
  setting is non-retroactive.
</Note>

### Stats

The Matches feed powers per-guardrail stats — each guardrail card shows a
7-day match sparkline and count, and the Matches tab carries a workspace
total. To slice activity by policy, use the Matches feed's grouped view
and filters (by guardrail, rule type, action) — that's where
per-guardrail usage, action mix, and false-positive rate live.

### Version history and audit

Every create, update, and delete writes a versioned history row in the
same transaction as the change. Open **History** on a guardrail row to:

* See every version with who changed it and when.
* **Diff** any two versions.
* **Revert** to an older version (recorded as a new version — history is
  never mutated).

## 11. Relationship to the rest of the gateway

| Surface          | Composes with Guardrails how?                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Models**       | Guardrails are model-agnostic. The same policy rides over GPT-5, Claude, Gemini — it screens text, not the model choice.                                                                                                                                                                                                                                                                                                                                            |
| **Routing**      | Independent. Routing decides which model/channel serves the request; guardrails screen the same request/response text regardless and never override model selection. Input screening runs before the upstream call, output screening after the model responds. Judge and grounding rules resolve their own model through your workspace channels, separate from the request's routing.                                                                              |
| **Prompts**      | Independent and complementary. [Prompts](/features/prompts) inject a system message; guardrails inspect and gate content. Both can apply to one request and guardrails always run. Ordering matters: input rules screen the caller's request *before* a registry prompt is injected (injection happens later, in the routing stage), so input rules see the caller's messages, not the injected system prompt; output rules screen the model's response either way. |
| **API Keys**     | A key attaches to a guardrail via `guardrail_id`. The binding lives on the key in the gateway, so editing the guardrail shifts every attached key at once; no attachment falls back to the workspace default.                                                                                                                                                                                                                                                       |
| **Matches feed** | Every rule that fires lands in the workspace's Matches feed (its own store, separate from the request log). Group and filter it by guardrail, rule type, and action to see usage, action mix, and false-positive rate per guardrail.                                                                                                                                                                                                                                |

## 12. API reference

All routes are workspace-scoped via the `X-Workspace-Id` header. RBAC is
enforced consistently: reads and the test sandbox are open to every
member; writes require Developer+ (and the `guardrails:write` permission);
production-traffic changes (delete, revert, vendor config) are gated
accordingly.

### Guardrails

| Method & path                       | Role       | Purpose                                                                                    |
| ----------------------------------- | ---------- | ------------------------------------------------------------------------------------------ |
| `GET /api/guardrail/`               | Member     | List guardrails (with attached-key counts).                                                |
| `GET /api/guardrail/meta`           | Member     | Engine vocabulary — rule types, stages, actions, PII entities, presets, preset categories. |
| `GET /api/guardrail/my-permissions` | Member     | The caller's guardrail permissions (for UI gating).                                        |
| `GET /api/guardrail/:id`            | Member     | Single guardrail detail.                                                                   |
| `GET /api/guardrail/:id/tokens`     | Member     | API keys attached to this guardrail (capped, with true total).                             |
| `POST /api/guardrail/test`          | Member     | Sandbox — evaluate a policy over sample text at a stage. Nothing is persisted.             |
| `POST /api/guardrail/`              | Developer+ | Create a guardrail.                                                                        |
| `PUT /api/guardrail/`               | Developer+ | Update a guardrail (writes a new history version).                                         |
| `DELETE /api/guardrail/:id`         | Developer+ | Delete a guardrail.                                                                        |

### History

| Method & path                             | Role       | Purpose                                    |
| ----------------------------------------- | ---------- | ------------------------------------------ |
| `GET /api/guardrail/:id/history`          | Member     | Version history (newest first).            |
| `GET /api/guardrail/:id/history/diff`     | Member     | Diff two versions.                         |
| `GET /api/guardrail/:id/history/:version` | Member     | A single historical version.               |
| `POST /api/guardrail/:id/revert`          | Developer+ | Restore an older version as a new version. |

### Eval and corpora

| Method & path                            | Role       | Purpose                                                     |
| ---------------------------------------- | ---------- | ----------------------------------------------------------- |
| `POST /api/guardrail/:id/eval`           | Member     | Run an eval over a corpus (bundled name or uploaded JSONL). |
| `GET /api/guardrail/:id/eval/runs`       | Member     | List eval runs for a guardrail (paginated).                 |
| `GET /api/guardrail/eval/runs/:run_id`   | Member     | Single eval-run detail.                                     |
| `GET /api/guardrail/eval/corpora`        | Member     | List workspace corpora + bundled corpora.                   |
| `POST /api/guardrail/eval/corpora`       | Developer+ | Upload a JSONL corpus.                                      |
| `GET /api/guardrail/eval/corpora/:id`    | Member     | Corpus detail.                                              |
| `DELETE /api/guardrail/eval/corpora/:id` | Developer+ | Delete a corpus.                                            |

### Matches

| Method & path                             | Role   | Purpose                                           |
| ----------------------------------------- | ------ | ------------------------------------------------- |
| `GET /api/guardrail/match`                | Member | List matches (workspace-scoped).                  |
| `GET /api/guardrail/match/grouped`        | Member | Matches grouped (e.g. by rule or guardrail).      |
| `GET /api/guardrail/match/stats`          | Member | Match stats (supports `?days=` and `?group_by=`). |
| `GET /api/guardrail/match/export`         | Member | Export matches as CSV.                            |
| `GET /api/guardrail/match/:id`            | Member | Single match detail.                              |
| `POST /api/guardrail/match/:id/mark-fp`   | Admin  | Mark a match as a false positive (rate-limited).  |
| `DELETE /api/guardrail/match/:id/mark-fp` | Admin  | Un-mark a false positive (rate-limited).          |

### Attaching a key

Set `guardrail_id` on the API key (via the key editor or the token API).
`0`/null means *no explicit attachment* — the key falls back to the
workspace default guardrail, if one is set.

## 13. FAQ

<AccordionGroup>
  <Accordion title="What if no guardrail resolves on a request?">
    Behavior is byte-identical to a workspace that never enabled the
    feature. If the key isn't attached and no workspace default is set,
    the gateway makes zero modifications. Nothing is blocked, masked, or
    logged to the Matches feed.
  </Accordion>

  <Accordion title="Does a blocked request cost quota?">
    No. An input-stage block fires before usage is metered; an
    output-stage block refunds the pre-consumed quota after the response
    is rejected. Either way the caller pays no quota, gets HTTP 400
    `guardrail_blocked`, and the request is marked skip-retry (re-running
    the same prompt against another channel would just block again).
  </Accordion>

  <Accordion title="Are output (response) rules enforced on streaming?">
    It depends on the action. **Block** is enforced both ways: on a
    non-streaming response the answer is screened before it returns, and
    on a streaming response a scanner cuts the stream mid-flight and
    emits a replacement message before any blocked content reaches the
    client. **Mask** on output currently applies only to non-streaming
    responses — on a streaming response the original chunk passes through
    unmasked (in-band stream rewriting is a planned enhancement). For
    output masking today, use non-streaming requests or rely on
    input-stage masking. Prove your specific stage/stream combination in
    the sandbox and with an eval run before depending on it.
  </Accordion>

  <Accordion title="What's the difference between mask and block?">
    **Mask** redacts the match (e.g. `jane@acme.com` → `[EMAIL]`) and
    lets the request through with the sanitized text — the upstream model
    never sees the original. **Block** rejects the whole request with
    HTTP 400. **Flag** changes nothing about the traffic and only records
    a match — use it to measure a rule before enforcing it.
  </Accordion>

  <Accordion title="Are injected prompt tokens and judge tokens billed?">
    A built-in rule (keyword / regex / PII / max\_chars) does no model
    call and bills nothing. An `llm_judge` or `grounding` rule calls a
    model through your workspace's channels, so those tokens are billed
    and attributed as a judge sub-line.
  </Accordion>

  <Accordion title="How do I see what a rule actually matched?">
    Turn on **Log raw content** for the guardrail. With it off (the
    default), the Matches feed records that a rule fired and its detail
    meta-string but not the matched substring — the privacy-conservative
    posture. The toggle is non-retroactive: it only affects matches
    recorded after you enable it.
  </Accordion>

  <Accordion title="Can I roll back a guardrail change?">
    Yes. Open **History** on the guardrail, diff the versions, and
    **Revert** to the one you want. Revert copies that version's content
    forward as a new version — history is never mutated — and the change
    takes effect on the next request.
  </Accordion>

  <Accordion title="What happens if an external vendor or judge times out?">
    By default, advanced rules **fail open**: a timeout or transport
    error is recorded as telemetry and the request continues. Set
    `fail_open` (external) or `judge_fail_open` (judge) to `false` to
    **fail closed** — treat the error as a block — for policies where a
    missed check is unacceptable.
  </Accordion>
</AccordionGroup>

## See also

Going deeper on agent security? The **Secure Your Agents (Zero Trust)** guides put this feature in a zero-trust workflow.

<CardGroup cols={2}>
  <Card title="Secure your agents (Zero Trust)" icon="shield-halved" href="/security/guardrails/overview">
    The zero-trust guardrail playbook — block PII, secrets, and prompt injection across every request.
  </Card>

  <Card title="Quickstart" icon="rocket" href="/security/concepts/quickstart">
    Turn on zero trust in 5 minutes — no agent-code change.
  </Card>
</CardGroup>
