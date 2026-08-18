> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Firewall: Skills

> Scan and risk-score the capabilities your agents install — skills, MCP servers, and plugins — before they can run. A deterministic scanner assigns a risk band and an enforcement mode; the firewall applies that mode on top of every rule verdict.

Modern agents install capabilities on the fly: a skill from a registry, a
community MCP server, a plugin from a URL. Each one ships a manifest, a set
of tools, and a set of requested permissions — and each is a supply-chain
risk the moment an agent loads it. A skill that quietly asks for
`shell.exec` and an external network scope is exactly the kind of thing
that should be reviewed *before* it runs, not discovered in an incident.

The Firewall's **Skills** governance is that review. Every installable
capability is registered as a workspace-scoped record, scanned by a
deterministic risk engine, assigned a risk band and an enforcement mode,
and — at runtime — that mode rides on top of the firewall's
[rule verdicts](/features/firewall-rules).

## 1. What a "skill" is here

A skill record is one installable agent capability. A single model
generalizes three **kinds** so one scanning, scoring, and approval plane
governs everything an agent self-installs:

| Kind         | What it is                                                                           |
| ------------ | ------------------------------------------------------------------------------------ |
| `skill`      | A packaged capability — a manifest plus a set of tools and a system-prompt fragment. |
| `mcp_server` | A bring-your-own MCP server registered as a governed artifact.                       |
| `plugin`     | A plugin-style extension.                                                            |

Each record also has a **source** — `builtin`, `registry`, `private`,
`byo_mcp`, or `auto_detected` — that feeds the trust assessment.

## 2. The scanner

On registration (and on demand), the scanner runs a set of deterministic,
dependency-free passes over the manifest and the declared scopes. Each
pass emits **findings** with a severity of `info`, `warn`, or `error`:

| Pass                  | Flags                                                                                                                    | Severity |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------- |
| **prompt\_injection** | Manifest text that tries to override instructions (`ignore previous instructions`, `you are now`, a leading `system:`…). | warn     |
| **tool\_creep**       | Tool names the manifest *uses* but didn't *declare* in `allowed_tools`.                                                  | error    |
| **network\_egress**   | HTTP(S) hosts in the manifest that aren't approved in the skill's network scopes.                                        | warn     |
| **fs\_write\_unsafe** | A write-mode filesystem scope on a path outside `/tmp` (traversal-safe).                                                 | error    |
| **data\_scope**       | Sensitive data scopes (`pii`, `financial`, `customer`).                                                                  | info     |
| **unsigned**          | A `registry` skill with no signature.                                                                                    | warn     |

The findings roll up into a **scan verdict**: any `error` → `blocked`;
otherwise any `warn` → `flagged`; otherwise `clean`.

## 3. Risk score & bands

The same findings feed a deterministic **risk score** (0–100, additive
with per-category caps). The heaviest contributors are dangerous
capabilities:

| Capability                      | Weight |
| ------------------------------- | ------ |
| Shell execution                 | +30    |
| Arbitrary code eval             | +30    |
| Filesystem write outside `/tmp` | +25    |
| Secrets read                    | +25    |
| External network egress         | +20    |

Tool-creep, prompt-injection, egress, and data-scope findings add on top
(each capped), an unsigned registry skill adds +15, and mitigations
subtract — a signed skill is −10, a manifest with no error findings −5.
The score maps to a **band**:

| Band       | Score  |
| ---------- | ------ |
| `low`      | 0–25   |
| `medium`   | 26–50  |
| `high`     | 51–75  |
| `critical` | 76–100 |

These weights are pinned by a drift-guard test — they don't move without a
deliberate spec change, so a band means the same thing across every
workspace.

## 4. Enforcement mode

The band and verdict together derive an enforcement **mode** — what the
firewall actually does when a tool owned by this skill is called:

| Mode         | Effect at runtime                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------ |
| `allow`      | The skill imposes nothing of its own; rule verdicts decide.                                                  |
| `quarantine` | Escalate anything short of a deny to `pending_approval` — the skill's tools run only after a human approves. |
| `block`      | Force a `deny` on the skill's tools.                                                                         |

The derivation takes the **stricter** of two signals: the band (low/medium
→ allow, high → quarantine, critical → block) and the scan verdict
(blocked → block, flagged → quarantine). A single `error` finding that
makes the verdict `blocked` will quarantine-or-block even when the numeric
band is low — the cautious direction. An operator can set the mode
explicitly; on a re-scan the mode only ever ratchets *tighter*, never
relaxing a block or quarantine you set.

## 5. Trust signals

Two signals beyond the static scan inform how a skill is treated:

* **Signed publishers.** A skill carrying a signature from a trusted
  publisher is treated as more trustworthy (the signing mitigation lowers
  its risk score); an unsigned registry skill is penalized. You manage
  which publishers your workspace trusts.
* **Resource reputation.** A skill's standing can be adjusted by its live
  behavior over time — denials and anomalies raise its risk, clean streaks
  lower it — so an artifact that misbehaves in production drifts toward
  quarantine even if its manifest scanned clean.

## 6. Auto-detected capabilities

The scanner doesn't only run when you register something by hand. When an
agent self-installs a capability and its tools first cross the gateway, the
Firewall **auto-detects** it (off the hot path, asynchronously), synthesizes
a manifest from what it observed, and runs the same scan, score, and mode
derivation — with `source = auto_detected`.

<Note>
  **Auto-detected capabilities are quarantined until reviewed.** Anything
  auto-detected that would otherwise resolve to `allow` is floored to
  `quarantine` (and `critical` stays `block`) until a human reviews it. A
  capability nobody approved doesn't get a free pass just because it scanned
  benign — it runs only after you've looked at it.
</Note>

## 7. Runtime enforcement

When a tool call reaches the [firewall engine](/features/firewall), it's
attributed to an owning skill, then the skill's mode is applied on top of
the rule verdict:

1. **Attribution.** The call is matched to a skill by its declared
   `allowed_tools`, then by `mcp_server` namespace prefix, then by a
   workspace-wide most-restrictive enforcing fallback.
2. **Rule verdict.** The policy's rules run as usual — and a rule's
   [`skill_name_glob`](/features/firewall-rules#3-skill-name-glob) lets you
   scope a rule to specific skills.
3. **Mode override.** A `block` skill forces a deny; a `quarantine` skill
   escalates anything short of deny to `pending_approval`; `allow` leaves
   the verdict untouched.

<Note>
  **Skill attribution fails closed.** If a tool can't be attributed (a DB
  error with no cache, or an undeclared tool under a curated source), the
  call is **held for review** rather than allowed. And skill mode is
  independent of shadow mode — a quarantined or blocked skill is still
  enforced even while a policy is in shadow rollout.
</Note>

## 8. Lifecycle

* **Register** — `POST /skills` validates and scans synchronously,
  returning the skill plus its findings and verdict. The mode is derived
  (or your explicit mode is honored).
* **Update** — re-scans the new manifest; the mode ratchets tighter on a
  worsened scan but never relaxes your stored block/quarantine.
* **Rescan** — `POST /skills/:id/rescan` re-runs the scan; if the verdict
  *newly degrades* to flagged or blocked it emits a firewall event so the
  drift shows up in your feed.
* **Delete** — soft-deletes and frees the name slot for re-registration.

## API reference

Workspace-scoped; list reads are open to any member (and redact
secret-bearing fields), everything else requires **Developer+**.

| Method & path                                    | Role       | Purpose                                                    |
| ------------------------------------------------ | ---------- | ---------------------------------------------------------- |
| `GET /api/workspace/firewall/skills`             | Member     | List skills (redacted; filter by `?kind=` and `?source=`). |
| `GET /api/workspace/firewall/skills/:id`         | Developer+ | Full skill record.                                         |
| `POST /api/workspace/firewall/skills`            | Developer+ | Register + scan (409 on duplicate name).                   |
| `PUT /api/workspace/firewall/skills/:id`         | Developer+ | Update + re-scan.                                          |
| `POST /api/workspace/firewall/skills/:id/rescan` | Developer+ | Re-scan; emits an event on degradation.                    |
| `DELETE /api/workspace/firewall/skills/:id`      | Developer+ | Soft-delete.                                               |

A register/update/rescan returns:

```json theme={null}
{
  "skill": { "id": 7, "name": "creepy", "risk_band": "high", "mode": "quarantine", "...": "..." },
  "findings": [
    { "kind": "tool_creep", "target": "shell.exec", "severity": "error" }
  ],
  "scan_verdict": "blocked"
}
```

<Note>
  Names are unique per workspace **across kinds** — a `skill` named `github`
  and an `mcp_server` named `github` collide in the same workspace. Pick
  distinct names per artifact.
</Note>

## FAQ

<AccordionGroup>
  <Accordion title="How is this different from the rule DSL?">
    [Rules](/features/firewall-rules) gate *tool calls* by name and
    arguments. Skills gate the *capabilities* an agent loads — the package,
    its manifest, and its requested permissions — before any of its tools
    run. The skill's mode then rides on top of whatever the rules decide,
    so the two compose: a rule can `allow` `http.fetch` in general while a
    quarantined skill that owns it still gets held.
  </Accordion>

  <Accordion title="What stops a malicious skill from declaring a clean manifest?">
    Several things. Tool-creep detection flags tools used but not
    declared; auto-detection re-scans from what actually crossed the
    gateway, not just the claimed manifest; the mode ratchets tighter (not
    looser) on re-scan; resource reputation drifts a misbehaving artifact
    toward quarantine over time; and attribution fails closed when a tool
    can't be tied to a declared skill.
  </Accordion>

  <Accordion title="Do I have to register every skill manually?">
    No. Register the ones you want to pre-approve; the rest are
    auto-detected on first use and quarantined until you review them. Turn
    on observe mode to surface everything an agent installs without
    blocking, then tighten from real data.
  </Accordion>
</AccordionGroup>

## See also

Going deeper on agent security? The **Secure Your Agents (Zero Trust)** guides put this feature in a zero-trust workflow.

<CardGroup cols={2}>
  <Card title="Secure Agents baseline" icon="shield-check" href="/security/concepts/secure-agents-baseline">
    Apply a zero-trust posture to every agent capability in one switch.
  </Card>

  <Card title="Agentic guardrails" icon="robot" href="/security/guardrails/agentic-guardrails">
    Guardrails built for autonomous, tool-using agents.
  </Card>
</CardGroup>
