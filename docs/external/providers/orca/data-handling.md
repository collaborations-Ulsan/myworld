> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Data Handling

> What OrcaRouter stores, what we don't, and how long we keep it.

## Short version

* We don't persist the content of your prompts or model outputs.
* We do keep a metadata log per request — timestamp, model, token counts,
  latency, HTTP status code — for billing, security, and debugging.
* We never sell your data.
* For the complete legally-binding policy, see our
  [Privacy Policy](https://www.orcarouter.ai/privacy.html).

## What we store

**Account metadata**

* Your email address and display name
* Password hash (never stored in clear)
* OAuth provider IDs (Google, Microsoft, GitHub, OIDC) if you sign in that way

**Per-request metadata** (one row per API call)

* Timestamp
* API key identifier (not the secret value)
* Model requested and whether it was resolved from a router
* Input and output token counts
* Latency and HTTP status code
* Truncated error message if the upstream returned one
* Source IP address (for rate-limiting and abuse prevention)

**Billing records**

* Stripe customer ID and invoice metadata
* Last four digits of the card (not the full number — Stripe holds that)

## What we do **not** store

* Prompt content
* Model outputs (response text, generated images, audio, etc.)
* Tool call arguments or tool call results
* Files you upload to `/v1/audio/*` or `/v1/images/edits`

All of these are processed in-transit — forwarded to the destination
provider and returned to you — and then discarded. This is the core
promise of [Zero Data Retention](/operations/zero-data-retention).

## Where your data goes

OrcaRouter is a proxy. When you send a request, we forward it to the
upstream provider (OpenAI, Anthropic, Google, etc.) under their own terms
and privacy policy. We don't transform the content. The list of
subprocessors and their roles is in our
[Privacy Policy](https://www.orcarouter.ai/privacy.html).

## How to delete everything

* Delete your account from the dashboard. We purge your account data
  within 30 days (brief grace period in case of accidental deletion).
* Request-level metadata (the per-request log rows) has its own
  retention — 13 months from the request date by default. This retention
  is necessary to respond to billing disputes and detect abuse.
* Billing records are retained for 7 years under accounting law
  requirements. These are numbers, not prompts.

## Questions

Email [privacy@orcarouter.ai](mailto:privacy@orcarouter.ai). EU residents
can also reach our Data Protection Officer at
[dpo@orcarouter.ai](mailto:dpo@orcarouter.ai).
