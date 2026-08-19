> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Zero Data Retention

> Prompts and outputs are processed in memory and never written to disk.

OrcaRouter does not log, store, or retain the content of your prompts
or model outputs.

## What this means, concretely

* **Requests** (prompts, messages, tool call payloads, uploaded audio
  and images) are routed to the destination provider in memory and
  **discarded** as soon as the response comes back.
* **Responses** (generated text, tool results, generated images, TTS
  audio) are streamed back to you in memory and **not written to any
  persistent store**.
* **Error logs** capture a truncated error *message* from the upstream
  (e.g., "rate limit exceeded", "context length exceeded") for debugging
  — but **never** the prompt or response content that triggered the error.

## What we do keep

See [Data Handling](/operations/data-handling) for the full list. In summary:
timestamps, token counts, latency, and HTTP status codes — the metadata
necessary to bill correctly and detect abuse. Never content.

## Why this is the default (not a per-request opt-in)

Some API platforms let you toggle retention per-request. We made
non-retention the default because:

1. The overwhelming majority of commercial and personal use cases don't
   benefit from having prompt content stored.
2. A default-on flag is an attack surface — misconfiguration leaks
   prompts.
3. Zero retention is a differentiator from direct-provider use: OpenAI
   retains 30 days of abuse logs; Anthropic retains similarly. OrcaRouter
   does not add a second retention layer on top.

If you need content retention for your own observability or evaluation,
capture prompts and responses **in your own application** before sending
them. OrcaRouter will never hold a copy.

## Caveat: upstream providers still receive your data

OrcaRouter routes traffic to the chosen upstream — OpenAI, Anthropic,
Google, and so on — under each provider's own terms and retention
policies. The zero-retention guarantee covers OrcaRouter's own
servers; it does not cover what those upstream providers retain.
If you need end-to-end retention guarantees that span the upstream
too, check that provider's policy or pick one that offers explicit
ZDR itself.
