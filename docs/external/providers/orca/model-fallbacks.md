> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Model Fallbacks

> Chain multiple models — if one fails, try the next.

OrcaRouter can try multiple models in order until one succeeds. Useful
for resilience (if one provider is throttling or down) and for cost
control (prefer a cheaper model, fall back to a stronger one if needed).

## How to use

Put an ordered list of model IDs in `extra_body.models` and set
`extra_body.route` to `"fallback"`. The primary `model` field still
matters — it's the first attempt — but OrcaRouter ignores it in favor of
the chain if the chain is present.

<CodeGroup>
  ```python Python theme={null}
  response = client.chat.completions.create(
      model="openai/gpt-4o",
      messages=[{"role": "user", "content": "..."}],
      extra_body={
          "models": ["openai/gpt-4o", "anthropic/claude-haiku-4.5", "google/gemini-2.5-pro"],
          "route": "fallback",
      },
  )
  ```

  ```ts TypeScript theme={null}
  const response = await openai.chat.completions.create({
    model: "openai/gpt-4o",
    messages: [{ role: "user", content: "..." }],
    // @ts-expect-error - extra_body is forwarded
    extra_body: {
      models: ["openai/gpt-4o", "anthropic/claude-haiku-4.5", "google/gemini-2.5-pro"],
      route: "fallback",
    },
  });
  ```

  ```bash cURL theme={null}
  curl https://api.orcarouter.ai/v1/chat/completions \
    -H "Authorization: Bearer sk-orca-..." \
    -H "Content-Type: application/json" \
    -d '{
      "model": "openai/gpt-4o",
      "messages": [{"role":"user","content":"..."}],
      "extra_body": {
        "models": ["openai/gpt-4o", "anthropic/claude-haiku-4.5", "google/gemini-2.5-pro"],
        "route": "fallback"
      }
    }'
  ```
</CodeGroup>

## Rules

* Maximum **5 models** in the chain. Extras are silently truncated.
* Recommended: all models in a chain should be the **same endpoint type**
  (all chat, or all image). Mixing a chat model with an image model won't
  crash the gateway, but the fallback that actually serves the request
  needs to match the endpoint you called (e.g. if you call
  `/v1/chat/completions`, only chat models in the chain are usable).
* Fallback behavior:
  * Unresolvable `orcarouter/{name}` entries (bad name, disabled router)
    are silently skipped.
  * Models the calling key cannot access (model-allowlist mismatch) are
    silently skipped.
  * [Free models](/routing/free-models) are dropped from the chain
    below the first position. A `-free` id can be your **primary**, but
    a chain never fails over *into* free capacity.
  * When the primary model fails upstream (5xx / 429 / network error),
    the next chain entry is tried.
  * The request fails only when **every** chain entry has been exhausted.
  * **Streaming caveat**: once any byte of the response has been sent
    to the client, fallback can no longer kick in — if the upstream
    drops mid-stream, the client sees a truncated stream, not a
    transparent retry on the next model.
* Billing happens for the model that **actually served** the response, at
  that model's rate — not the primary's.
* `extra_body.route` must be exactly `"fallback"` for the chain to
  activate. Any other value (or missing) → the chain is ignored and
  only the top-level `model` is used.

## How to tell which model served the response

Check the `X-Orca-Fallback-Level` and `X-Orca-Fallback-Model` response
headers. See [Response Headers](/routing/response-headers).

```python theme={null}
response = client.chat.completions.with_raw_response.create(...)
served_by = response.headers.get("X-Orca-Fallback-Model", "primary")
# "primary" means level 0; otherwise the fallback model name
```

## When not to use this

If you want OrcaRouter to *automatically* pick the cheapest available
model without writing a chain, use [`orcarouter/auto`](/routing/auto-router)
instead. Fallback chains are for cases where you want explicit control
over the ordering.
