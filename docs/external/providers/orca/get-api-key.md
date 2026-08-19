> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Get an API key

> Sign up, create an OrcaRouter API key, and authenticate.

## Where keys come from

API keys are issued from your [Dashboard](https://www.orcarouter.ai/console).
Every key starts with `sk-orca-`.

## How to send the key

Send your key via the standard `Authorization` header:

```
Authorization: Bearer sk-orca-...
```

This works for every endpoint and every supported SDK (OpenAI,
Anthropic, google-genai, etc.) — point the SDK's `base_url` at
`https://api.orcarouter.ai/v1` and pass the `sk-orca-...` value as
the `api_key`.

## Per-key options at creation

When you create a key in the dashboard, you can set:

* **Name** — a label so you remember what the key is for
* **Credit limit** — cap on total spend in USD; leave blank for
  unlimited (within your account's overall balance)
* **Expiration** — a fixed lifetime (1 hour up to 1 year, or never)

That's everything. There's no per-key rate-limit override and no
per-key model allowlist on the user side; rate limits are applied at
the workspace level (see [Rate Limits](/operations/rate-limits)).
