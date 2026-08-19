> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Free Models

> The -free tier — what it is, how it is limited, and why its 429s need different handling from ordinary ones.

Some models are served at no charge under a model id ending in `-free`.
They are ordinary catalog models priced at `$0`: same weights and same
capabilities as the paid model they shadow, billed at nothing. Calling
one never touches your wallet.

What you pay instead is volume. Free traffic runs under its own rate
limits, and on the lowest tier a per-request prompt-size cap as well.

## Finding them

Free ids appear in `/v1/models` and in the public
[`/api/pricing`](https://api.orcarouter.ai/api/pricing) catalog like any
other model — look for the `-free` suffix and a `$0` price. Today that is
the DeepSeek V4 line:

```
deepseek/deepseek-v4-flash-free
deepseek/deepseek-v4-pro-free
```

Treat the catalog as the source of truth rather than this list; free
capacity changes as models come and go.

## Usage

Call a `-free` id exactly as you would the paid one.

<CodeGroup>
  ```python Python theme={null}
  response = client.chat.completions.create(
      model="deepseek/deepseek-v4-flash-free",
      messages=[{"role": "user", "content": "..."}],
  )
  ```

  ```ts TypeScript theme={null}
  const response = await openai.chat.completions.create({
    model: "deepseek/deepseek-v4-flash-free",
    messages: [{ role: "user", content: "..." }],
  });
  ```
</CodeGroup>

## Limits

Free usage is capped three ways. All of them are tuned live and none of
them is published as a number — you find out by being told no, so build
for the `429` rather than counting requests yourself.

**Requests per minute and per day.** Counted per workspace on fixed
windows: a minute bucket, and a day bucket that rolls at `00:00` UTC.

**Tiered by what you have paid, ever.** An account that has never topped
up gets a deliberately small daily allowance. Crossing a modest
lifetime-spend threshold moves you to a higher tier with a much larger
daily budget — this is lifetime spend, not a subscription, so a single
top-up keeps you there.

**A per-request prompt cap on the lower tier.** Below the spend
threshold there is also a ceiling on how many prompt tokens a single
free request may carry. It is small — a long document or a full
conversation history will exceed it — and it applies per request, so no
amount of waiting or slowing down gets you past it. Higher tiers lift it.

<Note>
  The prompt cap is the limit that surprises people. A script that works
  on short prompts and fails on long ones, with no pattern in time, has
  hit this and not a rate limit.
</Note>

## Handling the 429

Every free-tier rejection returns `429` with error code
`free_rate_limited` and the same message, whichever limit tripped. The
one thing that distinguishes them is the `Retry-After` header:

| Response                        | What it means                                                                                                            | What to do                                                         |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `429` **with** `Retry-After`    | A rate window is full. The value is the seconds left in the window that tripped — to the next minute, or to `00:00` UTC. | Wait out `Retry-After`, then retry once.                           |
| `429` **without** `Retry-After` | The request itself was too big for the free tier's prompt cap.                                                           | Shorten the prompt. Retrying unchanged fails identically, forever. |

Do **not** back off exponentially on the first case. A free window
refills completely at its boundary rather than easing back gradually, so
the correct behavior is to wait exactly as long as you were told and try
again — the opposite of the guidance for ordinary quota
[429s](/operations/rate-limits).

And do not retry at all on the second case. A missing `Retry-After` is
the gateway telling you that time will not fix this request.

## What free models will not do

* **They never fall back to a paid model.** A saturated free model is not
  quietly rolled over to the paid one, and an `extra_body.models` chain
  won't rescue it either. To keep going, call the paid base model.
* **They cannot be a fallback target.** A `-free` id works as the
  *primary* model of a request, but a free id listed further down an
  [`extra_body.models`](/routing/model-fallbacks) chain is dropped from
  it. A chain cannot fail over *into* free capacity — otherwise a paid
  request would silently land on a rate-limited tier at the worst
  possible moment.
* **They do not affect your paid traffic.** Free-tier limits are counted
  against free ids only. Exhausting the free daily budget has no effect
  on the same workspace's calls to the paid model — including the paid
  model that the free id shadows.
* **They are not capacity.** Ceilings are tuned live and deliberately
  unpublished. Treat the free tier as best-effort, and move production
  traffic onto the paid base model.

## `orcarouter/free`

`orcarouter/free` is a built-in [named router](/routing/named-routers)
that covers the free tier with a single id. It scores each request's
difficulty and routes light work to the smaller free model and harder
work to the stronger one, so you don't have to choose per call.

```python theme={null}
response = client.chat.completions.create(
    model="orcarouter/free",
    messages=[{"role": "user", "content": "..."}],
)
```

The same free-tier limits apply to whatever it picks, and it never
escapes to a paid model. Like every router alias it authorizes as a
unit: if your API key has an allowed-model list, add `orcarouter/free`
to it — whitelisting the pool members does not unlock the router.
