> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Bring Your Own Key (BYOK)

> Attach your own upstream provider keys to a workspace and route through OrcaRouter while your provider invoices you directly.

BYOK lets a workspace serve its own traffic with **its own upstream
provider credentials**. The request still goes through OrcaRouter —
same endpoints, same models, same routing, same logs — but the tokens
are billed to your provider account under your contract, not resold by
us.

<Tip>
  This is **self-serve**. Any workspace **Admin** or **Owner** can add a
  key at [orcarouter.ai/console/byok](https://www.orcarouter.ai/console/byok).
  No sales conversation, no ticket.
</Tip>

## Who it's for

* You have negotiated pricing, committed spend, or a capacity
  reservation with a provider and want it to keep counting.
* You are required to keep the provider invoice relationship in your
  own name.
* You want one gateway, one API surface, and per-key control across
  providers you already pay for directly.

If none of those apply, don't use BYOK — platform routing is simpler
and there is nothing to maintain.

## Connecting a key

Everything happens in the console at `/console/byok`. Two kinds of key
can be attached:

<AccordionGroup>
  <Accordion title="A provider key">
    Pick the provider from the dropdown, paste the key, and choose which
    models it may serve. The key rides the provider's official endpoint.
    Which providers appear in the dropdown is set per deployment — the
    dropdown is authoritative, and a provider that isn't listed cannot
    accept a key.

    Google Vertex AI is the one exception to the "paste a key" shape: it
    takes a **service-account JSON** (it must contain `project_id`,
    `client_email` and `private_key`) plus an optional region such as
    `us-central1`. Blank region means `global`.
  </Accordion>

  <Accordion title="A custom OpenAI-compatible endpoint">
    Supply a `base_url` and a key. You then declare which platform
    models the endpoint serves, and optionally a **model mapping** — a
    JSON object of `"platform model": "upstream model"` — so a request
    for a catalog model reaches the name your endpoint actually uses.
    The console can fetch `GET {base_url}/models` to fill the upstream
    side in for you.

    The `base_url` is used verbatim, so keep your own version segment
    (`/v1`, `/v2`, …) on it.
  </Accordion>
</AccordionGroup>

Each key carries:

| Field                   | What it does                                                                                                            |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Allowed models**      | Comma/newline list, `*` wildcards allowed. Empty = every model of that provider your workspace can already route to.    |
| **Always use this key** | Forbids falling back to platform capacity for this provider. See [Fallback](#fallback-the-one-choice-you-have-to-make). |
| **Status**              | Enable or disable the key without deleting it.                                                                          |
| **Sort order**          | Which key is tried first when several match.                                                                            |

Use **Test** on a saved key before you send real traffic. It makes one
side-effect-free probe against the same endpoint a real request would
use and reports latency or a provider-side reason. It never writes a
usage or cost row. The probe is rate limited (it would otherwise be a
key-validation oracle), so don't loop it.

<Note>
  The raw secret is never returned after you save it. The console only
  ever shows a masked label. "Rotating" a key replaces the stored secret
  in place — it does not reveal the old one.
</Note>

## What you pay

A BYOK request is charged a **platform fee** instead of the token
price. The fee is a percentage of **what the same request would have
cost you on OrcaRouter's normal pricing**, after any group or workspace
discount you already have — it is not a percentage of your provider's
invoice, and it is not added on top of the provider's rate.

The default rate is **5%**. The console shows the exact rate for your
deployment on the BYOK page. A deployment may set it to `0`, which is a
valid, fee-free configuration.

Two consequences worth knowing:

* The fee is **floored**, not rounded up. A request whose fee works out
  below one unit costs nothing rather than being rounded to one.
* Your usage log keeps both numbers: what we charged, and the full
  normal price of the same traffic. The BYOK page in the console
  surfaces them as **fee** and **routed volume** per day, per provider,
  per model and per key, alongside error counts and last-used time.

Fallback requests are the exception — see below.

For everything else about charges and the `usage` object, see
[Billing & usage](/operations/billing-and-usage).

## Fallback: the one choice you have to make

When a BYOK key can't serve a request — the provider returns
`401`/`403`, the stored secret can't be read, the endpoint isn't
reachable — OrcaRouter has two options, and you decide which:

<CardGroup cols={2}>
  <Card title="Fall back (default)" icon="shuffle">
    The request is re-served on **platform** capacity at **full
    platform price**. Nothing fails, but you pay the normal rate for
    that request, not the BYOK fee. The log row is tagged
    `byok_fallback` so it is countable after the fact.
  </Card>

  <Card title="Never fall back" icon="lock">
    Turn on **Always use this key**. The request fails with
    `byok:key_unavailable` instead of quietly moving to platform
    capacity. Pick this when "billed to my provider account" is a hard
    requirement, not a preference.
  </Card>
</CardGroup>

The pin is per key but takes effect per **provider**: if any enabled
key for a provider has *Always use this key* on, no request for that
provider will fall back — including one that a different, unpinned key
was serving.

Fallback is single-shot. A failed BYOK attempt is not retried against
another one of your keys; the retry goes to platform capacity (or
aborts, if you pinned the provider).

<Warning>
  The default is to fall back, so an unnoticed dead key shows up as a
  higher bill rather than as errors. Watch the **fallback requests** KPI
  on the BYOK page, or pin the provider.
</Warning>

## Errors and recovery

### `byok:key_unavailable` — HTTP 503

Returned only when a key could not be used **and** fallback is
forbidden for that provider (you pinned *Always use this key*, or the
deployment has BYOK fallback turned off). The message names the reason
and the remedy.

This error deliberately **stops the whole chain**: it skips the
same-model retry *and* skips your `extra_body.models`
[model fallbacks](/routing/model-fallbacks). Every one of those is
another route to platform capacity, which is precisely what the pin
forbids. Handle it in your client — do not expect a backup model to
absorb it.

### Keys that disable themselves

A key is automatically disabled when:

* the provider answers **401** or **403** — the credential is dead or
  not authorized for that model; or
* the stored secret can no longer be decrypted.

Transient provider failures (`429`, `5xx`) never disable a key.

The workspace owner and every workspace admin are notified when this
happens, and the event lands in the key's event feed with its reason.
To recover, **rotate the key** in the console — saving a new secret
clears the disable and re-enables the key in one step. You can also
re-enable it manually if you believe the failure was a false positive.

<Note>
  Disabling or deleting a key always works, even if BYOK itself has been
  turned off for your workspace. Adding a key, rotating one, and testing
  one are the operations that require BYOK to be active.
</Note>

### Nothing routes through the key at all

Work down this list:

1. The key's **status** is enabled, not disabled or auto-disabled.
2. The requested model is inside the key's **allowed models**, and your
   workspace can already route to that model without BYOK.
3. For a custom endpoint: **served models** is not empty (empty means
   "serves nothing"), and the mapping resolves to a name your endpoint
   accepts.
4. **Test** the key and read the reason it reports.

## Limits

* **Chat-style traffic only.** Image, video, music, and other async task
  models are always served on platform capacity, whatever keys you
  attach.
* **Azure OpenAI is not supported.** An Azure credential is bound to a
  deployment endpoint and API version, so a key alone cannot serve a
  request.
* BYOK does not change rate limiting: workspace-level limits still
  apply. See [Rate limits](/operations/rate-limits).
* The BYOK console surface is authenticated as a **workspace admin**,
  not with an inference key. An `sk-orca-…` key cannot manage BYOK keys
  — which is deliberate, so a leaked inference key can never read or
  rotate your provider credentials. See
  [Scoped keys overview](/security/keys/overview).
* If your workspace holds a Zero Data Retention grant, a BYOK key
  carries ZDR traffic only after the workspace **owner** attests that
  the provider account behind it is configured for zero retention.
  Un-attested keys are skipped for ZDR requests and the traffic routes
  normally. See [Zero Data Retention](/operations/zero-data-retention).
* If the BYOK page is not visible in your console, either your role is
  below Admin or BYOK is not enabled for your workspace yet.
