> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Auto Router

> orcarouter/auto — let OrcaRouter pick a model per request, matching model strength to how hard the request is.

`orcarouter/auto` is a [named router](/routing/named-routers) we
create for every account on signup. It sizes the model to the request:
easy turns go to a small, cheap model and harder ones to a stronger
one, decided fresh per request.

## Usage

<CodeGroup>
  ```python Python theme={null}
  response = client.chat.completions.create(
      model="orcarouter/auto",
      messages=[{"role": "user", "content": "..."}],
  )
  ```

  ```ts TypeScript theme={null}
  const response = await openai.chat.completions.create({
    model: "orcarouter/auto",
    messages: [{ role: "user", content: "..." }],
  });
  ```
</CodeGroup>

No other setup required — the router exists the moment your account is
created.

## Default behavior

The seed configuration:

* **Pattern**: empty — matches **every chat model your account has
  access to**. New models that come online become candidates
  automatically.
* **Strategy**: `gated_adaptive` — scores each request's difficulty and
  narrows to a weak or a strong pool before picking. See
  [Adaptive](/routing/named-routers#adaptive).
* **Weak and strong pools**: pre-populated with current small and
  frontier models. They're ordinary router fields — open the router to
  see what yours hold today, and edit them freely.
* **Default model**: seeded with a general-purpose model, used as the
  safety net when the pattern resolves to nothing available.

<Note>
  These are the values stamped on routers seeded from mid-2026 onward.
  An older account may still carry the original `cheapest` seed —
  existing routers are never rewritten under you. Open the router in the
  dashboard to see what yours is actually set to.
</Note>

You can see and edit your Auto Router in the dashboard under **Routing**.
You can narrow the pattern (e.g. restrict to `openai/*`), swap the
strategy, set a `default_model`, or delete the router entirely — same
as any [named router](/routing/named-routers).

## Switching strategies

Pick a different strategy to change how `orcarouter/auto` resolves
picks. Full mechanics for each are in
[Named Routers](/routing/named-routers#strategies).

| Card     | Backend enum                | What it does                                                                                                                                                                                                        |
| -------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cheapest | `cheapest`                  | Lowest per-token price among live candidates.                                                                                                                                                                       |
| Quality  | `quality`                   | Highest quality score among live candidates, regardless of price.                                                                                                                                                   |
| Balanced | `balanced`                  | Picks a low-cost option that still meets a quality bar; falls back to the highest-quality option if nothing meets the bar. Default for new routers you create yourself.                                             |
| Adaptive | `linucb` / `gated_adaptive` | Per-router LinUCB contextual bandit that learns from your real traffic to weigh quality, cost, latency, and reliability per request. Two sub-modes (Standard / Gated) — Gated is what `orcarouter/auto` ships with. |

Adaptive needs a short warm-up per model before it starts steering
picks. During warm-up it behaves like Balanced — that's expected, not
a bug.

## When to prefer Auto Router over explicit model names

* You don't want to pin to a specific model; you want each request
  served by a model sized to it.
* You're prototyping and don't want to care about which provider is up.
* You want OrcaRouter's routing to "just work" without thinking about it.

## When to prefer explicit model names

* You need deterministic output — picking different models at different
  times will change generation style and quality.
* You're using features specific to one model (e.g. Claude's
  `cache_control`, or a model's native image generation).
* You want predictable per-request cost.

## Seeing what Auto Router picked

Check the `X-Orca-Resolved-Model` response header. See
[Response Headers](/routing/response-headers).

```python theme={null}
res = client.chat.completions.with_raw_response.create(
    model="orcarouter/auto", ...
)
actual_model = res.headers.get("X-Orca-Resolved-Model")
# e.g. "openai/gpt-4o-mini"
```
