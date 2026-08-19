> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Named Routers

> Save a routing strategy and invoke it by name.

OrcaRouter lets you save a routing strategy as a named router. Call it
from your code as `orcarouter/{name}` and OrcaRouter resolves it to a
concrete model at request time, based on the rules you configured.

This is useful when you want to:

* Swap routing behavior without redeploying your app (change the router
  in the dashboard; your code stays the same).
* Let different teams or services choose their own routing policy
  independently of the application that calls the API.
* Reference routing logic that's too complex to inline in `extra_body`.

## Using a router

<CodeGroup>
  ```python Python theme={null}
  response = client.chat.completions.create(
      model="orcarouter/production-chat",
      messages=[...],
  )
  ```

  ```ts TypeScript theme={null}
  const response = await openai.chat.completions.create({
    model: "orcarouter/production-chat",
    messages: [...],
  });
  ```
</CodeGroup>

To find out which concrete model a router resolved to, read the
`X-Orca-Router` and `X-Orca-Resolved-Model` response headers — see
[Response Headers](/routing/response-headers). The `model` field in
the response body itself reflects whatever the upstream returned (often
the bare upstream name, e.g. `gpt-4o-mini-2024-07-18`).

## Creating a router

Routers are created in the dashboard under **Routing**. Each router has:

* **Name** — the `{name}` in `orcarouter/{name}`. Must be unique within
  your workspace; lowercase letters, digits, `_`, and `-` (1-50 chars).
  The name `orcarouter` is reserved.
* **Allowed models** — one or more glob patterns (comma- or
  newline-separated, case-insensitive) limiting which models this
  router can pick. Examples: `openai/*` or
  `openai/*, anthropic/claude-haiku-*`. Empty matches every model
  your account has access to.
* **Strategy** — how to pick among matching models. See
  [Strategies](#strategies) below.
* **Mundane models** / **Hard models** — additional model lists used
  only by the **Adaptive · Gated** strategy. See
  [Adaptive](#adaptive) below.
* **Default model** — a safety-net model used if the pattern resolves
  to nothing.
* **Prefer free models** (`prefer_free`) — serve the free models your
  workspace has claimed before any paid one. Off by default. See
  [Prefer free models](#prefer-free-models) below.
* **Enabled** — disable the router without deleting it.

## Strategies

The strategy decides which of the matching models actually serves each
request. There are six, picked in the editor or set via the API:

| Strategy            | API enum         | Picks by                                       |
| ------------------- | ---------------- | ---------------------------------------------- |
| Cheapest            | `cheapest`       | Lowest price per token                         |
| Quality             | `quality`        | Highest quality score                          |
| Balanced            | `balanced`       | Cheapest model that still clears a quality bar |
| Adaptive · Standard | `linucb`         | Learned reward, across the whole allowed list  |
| Adaptive · Gated    | `gated_adaptive` | Request difficulty first, then learned reward  |
| DSL                 | `dsl`            | Rules you author in YAML + CEL                 |

Omit `strategy` on the API and you get `balanced`. Every strategy
degrades to Balanced rather than failing a request, so a router is
never left with nothing to serve.

### Cheapest

Sorts the live candidates by price per token and takes the lowest, ties
broken alphabetically so repeated requests land on the same model.
Candidates with no configured price are skipped; if none of them is
priced, the alphabetically first is used. Best when you want the
cheapest live chat model on every request and don't care about
output-style consistency across calls.

### Quality

Sorts the candidates by quality score and takes the highest, price
ignored, ties broken alphabetically. Best when output quality dominates
cost.

### Balanced

Two passes: drop every candidate below the quality bar, then take the
cheapest of what remains. If nothing clears the bar it falls back to
the highest-quality candidate — so you get a cheap model only when it
is also good enough. This is the default, needs no per-router tuning,
and is the fallback the other strategies degrade to.

### Adaptive

A per-router LinUCB contextual bandit that learns from your real
production traffic instead of from a static price or quality table.

Each request is turned into a feature vector — prompt size, code and
math markers, reasoning cues, system-prompt length, tool and vision
use, language mix, requested output budget. Every (model, budget tier,
task class) combination is a bandit *arm*. The router scores each arm
as *predicted reward + an uncertainty bonus*, so models it has little
data on still get tried, then samples the winner with a low-temperature
softmax rather than always taking the argmax. After the response, the
outcome is folded back into the arm as a single reward: success, minus
cost, minus latency, minus rate-limit hits, minus structured-output
failures. A 5xx puts that model in a short cooldown.

The cost is that it needs traffic. An arm has to accumulate a warm-up
number of observations (10 by default) before Adaptive will steer; until
at least one candidate is warm, every request falls through to Balanced.
Because arms are keyed per budget tier and task class, warm-up happens
per bucket, not once per router — a low-volume router may sit on
Balanced behavior for a long time. That's expected, not a bug.

Two sub-modes:

* **Standard** (API enum: `linucb`) — considers every Allowed model
  for each request. Best when traffic is roughly uniform and you want
  the router to find the best option across your full list.
* **Gated** (API enum: `gated_adaptive`) — each request first gets a
  difficulty score between 0 and 1, computed from prompt length,
  reasoning cues, system-prompt length, code-keyword density, tool use,
  and math markers. Below the mundane threshold (0.3 by default) the
  candidates are narrowed to the **Mundane models** pool; above the hard
  threshold (0.7) to the **Hard models** pool; in between, the full
  Allowed list is used. The bandit then picks inside that band. Best
  when your traffic mixes simple and complex calls.
  Each pool is intersected with Allowed models; empty or
  non-overlapping pools quietly fall back to the full Allowed list,
  so requests are never starved. Configure the two pools (`weak_pool`
  and `strong_pool` at the API level — up to 2000 chars each) in the
  editor when you pick Gated.

### DSL

Hands the decision to rules you write yourself in YAML + CEL, matching
on request shape, task classification, and agent session state. Rules
can only re-rank or narrow within the router's allowed set — they can
never widen it. Roll-out is staged: a shadow mode logs what the rules
*would* have picked while the previous strategy keeps serving, and a
canary percentage decides how much live traffic the rules take.
Requests outside the canary, and any request where the source is empty,
no rule matches, or evaluation errors or times out, fall back to
Balanced. See [Routing DSL](/routing/routing-dsl).

## Prefer free models

`prefer_free` (**Prefer free models** in the editor) is off by default.
Turn it on and the router prefers a free stand-in for a paid candidate
*before* the strategy makes its pick — within whatever set the strategy
has already arrived at, not instead of it. On **Adaptive · Gated** that
means the difficulty band comes first: a mundane request takes a free
mundane model, and a hard request still escalates to a paid model when
no free model sits in the hard band.

A free model is only offered when the paid model it stands in for is
already a candidate for this router, so Allowed models and your group's
catalogue still apply.

It never starves a request. If no free model fits the set the strategy
arrived at, the set is left untouched and paid models serve as usual.

<Note>
  This toggle draws on free stand-ins provisioned as a workspace free
  package. It is **not** how you reach the ordinary
  [`-free` models](/routing/free-models) — those are ordinary catalog
  entries you call by id. With no free package configured, turning
  `prefer_free` on changes nothing.
</Note>

`prefer_free` is inert — no preference applied, no lookup performed —
in these cases:

* **Strategy is `dsl`.** Your rules own routing; narrowing the
  candidates first would bypass the constraints a matched rule
  declares.
* **The conversation is already pinned.** With
  [session affinity](/routing/session-affinity), an established pin
  wins so the provider's prompt cache stays warm.
* **The endpoint can't serve free calls.** Only chat completions,
  legacy completions, `/v1/messages`, `/v1/responses`, and Gemini
  `:generateContent` are covered. Embeddings, rerank, audio, image,
  video, and realtime requests route exactly as they would with the
  toggle off.

## Seeded router: `orcarouter/auto`

Every OrcaRouter account is seeded with a default router called `auto`
on signup — see [Auto Router](/routing/auto-router). You can use
it immediately without any configuration.
