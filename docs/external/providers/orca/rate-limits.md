> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Rate Limits

> OrcaRouter rate-limits per workspace. How to handle 429s.

OrcaRouter rate-limits at the **workspace** level, not per API key.
All keys belonging to the same workspace draw from the same bucket.
When the limit is exceeded you get an HTTP `429 Too Many Requests`
response with a `Retry-After` header.

## Why workspace-scoped

Workspaces are how OrcaRouter groups the keys, members, and billing
that belong to a single team or individual. Shared limits inside a
workspace make traffic predictable as your team grows: adding a new
key (or a new member) doesn't multiply your shared budget. If you
need a higher ceiling, upgrade the workspace's plan.

OrcaRouter does not expose per-model rate limits to callers — the
gateway behaves like a single logical provider from your application's
view, consistent with [provider opacity](/operations/data-handling).
Internal throttling toward upstream providers happens transparently
and is not part of the public contract.

## Response

A rate-limited request always returns:

```http theme={null}
HTTP/1.1 429 Too Many Requests
Retry-After: <seconds>
```

Some rate-limit paths also include a JSON body explaining the limit
that was hit; others (the fastest-path workspace bucket) return only
the status code and headers. **Don't depend on the body shape —
check status code 429 and read `Retry-After`.**

When a body is present it follows the OpenAI-compatible envelope with
`error.type` set to `orcarouter_api_error`. The `error.message` may be
localized (currently Chinese) — see
[Errors](/operations/errors) for the envelope structure.

`Retry-After` is in seconds. It's the rate-limit window duration
(conservative — safe to wait exactly that long); the next window
will have full budget. Immediately retrying without waiting will
fail again.

## Recommended client behavior

1. On `429`, read `Retry-After`.
2. Wait that many seconds.
3. Retry the same request.
4. If a second `429` occurs, increase the wait by 2× (exponential
   backoff) up to 60 seconds.
5. If you see `429` repeatedly, consider splitting traffic across
   multiple models with `extra_body.models` — see
   [Model Fallbacks](/routing/model-fallbacks).

The OpenAI Python and TypeScript SDKs handle `Retry-After`
automatically by default. You don't need custom code unless you've
disabled retries.

## Reactive, not predictive

OrcaRouter does not return `X-RateLimit-Remaining` / `X-RateLimit-Reset`
headers, so you can't pre-emptively check how much budget is left.
Treat `429` as the signal — back off when you see it, then resume.
