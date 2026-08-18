> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Firewall Rules

> The matching language behind a firewall policy. Match tool calls by name, skill, arguments, and destination — then allow, audit, deny, sanitize, hold for approval, or cap cost. Deterministic, fail-closed, and safe on the hot path.

A [firewall policy](/features/firewall) is an ordered list of **rules**.
This page is the complete reference for what a rule can express — the
matching language, the verdicts, and how the engine evaluates them.

Rules are authored in the console rule editor, which writes structured
JSON match objects. Everything below describes that vocabulary so you can
read, reason about, and verify a rule precisely — whether you build it in
the UI or post it through the [API](#api-reference).

## 1. Anatomy of a rule

| Field             | Type   | Meaning                                                                                                                              |
| ----------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `priority`        | int    | **Lower runs first.** Ties broken by rule id.                                                                                        |
| `label`           | string | Human name, shown in events and audit.                                                                                               |
| `stage`           | enum   | The [surface](/features/firewall#2-the-four-enforcement-surfaces) — `inbound` / `response` / `mcp` / `egress`. Empty = all surfaces. |
| `tool_name_glob`  | string | [Glob](#2-tool-name-glob) on the tool name.                                                                                          |
| `skill_name_glob` | string | Optional [glob](#3-skill-name-glob) on the owning skill. AND-ed with the tool glob; empty = any skill.                               |
| `verdict`         | enum   | The action — see [§7](#7-verdicts).                                                                                                  |
| `args_match`      | object | Optional [argument predicate](#4-argument-clauses).                                                                                  |
| `sanitize`        | object | Redaction config, used when `verdict = sanitize`. See [§5](#5-sanitizers).                                                           |
| `egress`          | object | Host/CIDR allow/deny list, used when `stage = egress`. See [§6](#6-egress-destination-lists).                                        |
| `cap_cost_cents`  | int    | Run-cost ceiling, used when `verdict = cap_cost`.                                                                                    |
| `sequence`        | object | Ordered multi-step match, enforced reactively. See [§8](#8-sequences).                                                               |
| `notes`           | string | Author rationale; ignored by the engine.                                                                                             |

A rule matches a tool call when **all** of its declared conditions hold:
the stage matches (or is empty), the tool glob matches, the skill glob
matches (or is empty), the argument clauses match (or are absent), and the
egress scope matches (egress rules only). The engine walks rules in
priority order and the **first match wins**.

## 2. Tool-name glob

A deliberately small, case-sensitive grammar — no regex surprises, linear
time, safe on the relay hot path:

| Pattern       | Matches                                               |
| ------------- | ----------------------------------------------------- |
| `""` or `*`   | Every tool.                                           |
| `foo.*`       | Prefix — `foo.bar`, `foo.exec` (not bare `foo`).      |
| `*.exec`      | Suffix — `shell.exec`, `db.exec` (not bare `exec`).   |
| `*.shell.*`   | Infix — `local.shell.exec` (needs ≥1 char each side). |
| anything else | Exact string match (including `foo.*.bar`).           |

Tools are conventionally namespaced `server.tool` or `category.action`, so
`shell.*` catches an entire family and `*.delete` catches a verb across
servers.

## 3. Skill-name glob

The same glob grammar, matched against the **owning skill** of the tool
call (e.g. `community.*`, `builtin.send`). It is AND-ed with
`tool_name_glob`, so:

```text theme={null}
tool_name_glob:  http.fetch
skill_name_glob: community.*
```

matches `http.fetch` **only when** it's owned by a `community.*` skill —
trust the same tool from a built-in skill, gate it from a community one.
An empty skill glob matches any owner. How a tool call is attributed to a
skill is covered in [Skills](/features/firewall-skills#7-runtime-enforcement).

## 4. Argument clauses

Tool-name matching answers *which tool*; argument clauses answer *with
what arguments* — the difference between "block `shell.exec`" and "block
`shell.exec` only when the command is `rm -rf`."

`args_match` is a set of clauses, **all AND-ed together**:

```json theme={null}
{
  "clauses": [
    { "path": "$.command",    "op": "regex",      "value": "rm -rf|drop table" },
    { "path": "$.connection", "op": "in",         "value": ["prod", "replica"] },
    { "path": "$.ip",         "op": "cidr_match", "value": "10.0.0.0/8" }
  ]
}
```

An empty / absent `args_match` is vacuously true — the rule matches on the
glob alone.

### Operators

| Operator     | Matches when                                                                |
| ------------ | --------------------------------------------------------------------------- |
| `eq`         | Scalar equality (numbers compared numerically; type mismatch → no match).   |
| `contains`   | Substring (both operands must be strings).                                  |
| `regex`      | A Go RE2 pattern matches the string value (linear-time, no backreferences). |
| `in`         | The value is an element of the given JSON array.                            |
| `cidr_match` | The string IP falls inside the given CIDR.                                  |
| `gt` / `lt`  | Numeric greater-than / less-than (strings are not coerced).                 |

### Path syntax

A small JSONPath subset over the tool's argument object:

* `$.foo`, `$.foo.bar` — field access
* `$.foo[0]`, `$.arr[1].k` — array indexing
* `$` — the whole arguments object

No wildcards, filters, slices, or recursive descent.

<Note>
  **Argument clauses fail closed — the rule, not the request.** If a path
  doesn't resolve, the arguments are malformed, or a regex/CIDR is invalid,
  the clause evaluates **false** and the rule simply doesn't fire — the call
  falls through to the next rule or the default verdict. A broken clause
  never auto-denies and never crashes the relay. Write your "catch
  everything dangerous" rule as an explicit `deny` with its own glob rather
  than relying on a clause to fail a particular way.
</Note>

The console validates clauses strictly on save (unknown operators, bad
paths, non-array `in` values, uncompilable regexes, and invalid CIDRs are
all rejected) so a malformed clause can't be persisted in the first place.

## 5. Sanitizers

A `sanitize` verdict redacts matched substrings from the tool *arguments*
and forwards the cleaned call — useful for stripping secrets or PII an
agent put in a tool argument without blocking the whole action.

```json theme={null}
{ "presets": ["email", "ssn_us"], "custom": ["foo-\\d+"] }
```

Preset matches are replaced with `[redacted:<preset>]`; custom-regex
matches with `[redacted:custom]`. The built-in preset library:

`aws_access_key`, `aws_secret_key`, `openai_key`, `anthropic_key`,
`bearer_token`, `email`, `ssn_us`, `credit_card` (with a Luhn check).

A sanitize rule must declare at least one preset or custom pattern — an
empty sanitizer is rejected on save. On the `inbound` surface there are no
call-time arguments to redact, so a sanitize verdict there escalates to a
**block**.

## 6. Egress destination lists

An `egress` rule (stage `egress`) matches on an outbound destination — the
SSRF and exfiltration surface:

```json theme={null}
{
  "deny":  ["169.254.169.254", "10.0.0.0/8"],
  "allow": ["api.openai.com"]
}
```

Entries match as a CIDR, an IP literal, or a case-insensitive hostname;
hostnames are best-effort resolved and re-checked against IP/CIDR entries.
The polarity follows the verdict: with an `allow` verdict the `allow` list
defines what's in scope and `deny` carves exceptions out of it; with an
enforcing verdict (`deny`) the `deny` list defines what's blocked and
`allow` carves exceptions out.

`169.254.169.254` (the cloud metadata endpoint) and RFC-1918 ranges are
the canonical things to deny — the `block_ssrf_egress` preset and the
`tight` [autonomy level](/features/firewall#8-autonomy-levels-one-switch-for-your-whole-posture)
ship exactly that.

## 7. Verdicts

| Verdict            | Effect                     | Notes                                                                    |
| ------------------ | -------------------------- | ------------------------------------------------------------------------ |
| `allow`            | Let through, logged.       |                                                                          |
| `audit`            | Allow + record for review. | The usual `default_verdict`.                                             |
| `deny`             | Block the call.            | HTTP 400 on `inbound`; tool error on `mcp`.                              |
| `sanitize`         | Redact args, forward.      | Needs a [sanitizer](#5-sanitizers); escalates to deny on `inbound`.      |
| `pending_approval` | Hold for a human.          | Requires the approval store configured; rejected on `response`/`egress`. |
| `cap_cost`         | Deny past a spend cap.     | Needs a non-negative `cap_cost_cents`; inert on `response`/`egress`.     |

In [shadow mode](/features/firewall#3-core-concepts) every enforcing
verdict is downgraded to `audit` and the reason is prefixed
`[shadow] would …`.

## 8. Sequences

Some risks are only visible across *several* calls — read 50 CRM records,
then export, then hit an external host. A `sequence` rule matches an
ordered chain rather than a single call:

```json theme={null}
{
  "window_seconds": 600,
  "steps": [
    { "match": "crm.*",   "min_count": 3 },
    { "match": "*.export" },
    { "match": "*",       "egress": true }
  ]
}
```

Each step is a tool glob with an optional `min_count` (default 1) and an
optional `egress: true` (the step must be an egress call). Steps must
occur in order — interleaving with other calls is fine — and the whole
chain must complete within `window_seconds` (`0` = no bound).

<Note>
  Sequences are enforced **reactively** by an asynchronous matcher, not
  inline on each call — a sequence with a `*` step would otherwise match
  every single tool call. They light up the events feed and can trigger
  follow-on action, but they don't block the individual call that completes
  the chain in real time.
</Note>

## 9. Built-in presets

Start from a preset instead of a blank rule. They're authored server-side
so the console and these docs describe identical behavior:

| Preset                      | What it does                                                                                               |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `block_destructive_shell`   | Denies destructive shell commands (`rm -rf`, `mkfs`, `dd`, fork bombs, …) via a set of deny-by-glob rules. |
| `block_ssrf_egress`         | Audits egress to the metadata endpoint and RFC-1918 ranges.                                                |
| `block_secrets_in_args`     | Detection-oriented — flags credentials appearing in tool arguments.                                        |
| `block_pii_in_tool_results` | Detection-oriented — surfaces PII in tool results.                                                         |

Apply a preset as a seed, then edit freely — a preset is a starting point,
not a lock.

## 10. Evaluation, limits & safety

* **First match wins.** Rules run in `priority ASC, id ASC` order; the
  first rule whose conditions all hold decides the verdict. No rule
  matches → the policy `default_verdict`.
* **Deterministic and dependency-free.** Glob and clause matching are pure
  string/JSON operations with no network call, safe to run on every tool
  call. Regexes are RE2 — linear time, no catastrophic backtracking.
* **Fail-closed clauses.** A clause that can't be evaluated makes its rule
  *not fire* rather than auto-denying ([§4](#4-argument-clauses)).
* **Strict save-time validation.** Verdict/stage pairings, sanitizer
  non-emptiness, `cap_cost_cents` presence, clause shape, and ref
  resolution are all checked when you save — invalid rules can't be
  persisted.
* **Audited.** Every rule create/update/delete writes an audit row after
  the change commits; rule blobs and secrets are never written to the
  audit log.

## API reference

Rules live under a policy and are workspace-scoped; writes require
**Developer+**.

| Method & path                              | Role       | Purpose                                                       |
| ------------------------------------------ | ---------- | ------------------------------------------------------------- |
| `POST /api/workspace/firewall/rules`       | Developer+ | Create a rule.                                                |
| `PUT /api/workspace/firewall/rules`        | Developer+ | Update a rule (id in body).                                   |
| `DELETE /api/workspace/firewall/rules/:id` | Developer+ | Delete a rule.                                                |
| `GET /api/workspace/firewall/presets`      | Member     | List built-in presets.                                        |
| `POST /api/workspace/firewall/test`        | Developer+ | Dry-run a policy (rules included) against a sample tool call. |

To preview a rule before depending on it, use **Test** — it returns the
verdict, the matched rule, and the reason without dispatching anything.

## See also

Going deeper on agent security? The **Secure Your Agents (Zero Trust)** guides put this feature in a zero-trust workflow.

<CardGroup cols={2}>
  <Card title="Build a firewall policy" icon="filter" href="/security/firewall/create-policy">
    Author a zero-trust policy step by step, then shadow it before you enforce.
  </Card>

  <Card title="Rule schema reference" icon="code" href="/security/firewall/rule-schema">
    Every rule field — globs, argument predicates, egress, and cost caps.
  </Card>
</CardGroup>
