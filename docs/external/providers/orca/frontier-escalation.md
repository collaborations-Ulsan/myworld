> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Frontier Escalation

> Let a router move a conversation to a stronger model when the task outgrows the one it started on.

A conversation usually starts easy. The first turn is a short opener, so a
router picks a cheap model — and [session affinity](/routing/session-affinity)
then keeps every later turn on that same model, even after the task has
turned into a multi-file refactor.

Frontier Escalation is the escape hatch. When a session outgrows the model
it was pinned to, the router moves that **one session** to a stronger pool
and keeps it there; everyone else's traffic is unaffected. You don't change
the model you call — you keep calling `orcarouter/{name}`.

It applies to [named router](/routing/named-routers) traffic only. A request
that names a model directly is never escalated.

## Turning it on

In the dashboard, open your router and find **Frontier escalation** under
its behavior settings. Three modes:

| Mode              | What escalates                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| **Off** (default) | Nothing. A stuck conversation stays on its pinned model until the client starts a new session. |
| **Manual**        | Only what the client explicitly asks for, via the request headers below.                       |
| **Auto**          | The client headers, plus automatic triggers (difficulty and failure signals).                  |

Enabling either mode turns **session awareness on** for the router — a
router can't observe a conversation across turns without it.

## The escalation pool

Escalation needs somewhere to escalate *to*: a comma-separated list of
model names or `@pool:<name>` references, set in **Escalate to**. Leave it
empty and the router falls back to its own Hard models (the strong pool).
Saving fails if neither resolves to anything.

The pool is a tier, not a second router:

* **Base tier** — the escalation pool's models are removed from the
  candidate set, so a base session can never drift onto them. (Exception:
  an Adaptive-gated router with an empty **Escalate to** field keeps its
  full set, so its normal difficulty banding still works.)
* **Strong tier** — candidates are narrowed to the escalation pool. If
  nothing in the pool can serve this turn, the request is served at base
  tier rather than failing.
* The session's sticky model pin is honored **within** the current tier, so
  an escalated session stays on one strong model instead of being re-picked
  every turn.

## Escalating from the client

Both headers are honored in Manual and Auto mode (values are
case-insensitive):

| Header                        | Effect                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------ |
| `X-OrcaRouter-Tier: strong`   | Escalate the whole session. Later turns stay strong.                                 |
| `X-OrcaRouter-Escalate: once` | Serve this one request from the strong pool. The session's tier is unchanged.        |
| `X-OrcaRouter-Tier: base`     | Return to base tier now. Also vetoes an automatic escalation that was about to fire. |

```bash theme={null}
curl https://api.orcarouter.ai/v1/chat/completions \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -H "X-OrcaRouter-Session-Id: conv-9f3c1a" \
  -H "X-OrcaRouter-Escalate: once" \
  -d '{
    "model": "orcarouter/production-chat",
    "messages": [{"role": "user", "content": "..."}]
  }'
```

This is the whole client-side contract — useful when your app already knows
a turn is hard (the user hit "think harder", a plan step failed, a review
pass is starting).

## Escalating automatically

Auto mode adds two triggers on top of the headers:

* **Difficulty** — the last two consecutive turns both scored above the
  router's hard threshold. Scoring looks at what the latest turn actually
  added, not the whole transcript, so a long conversation doesn't escalate
  just for being long.
* **Failure signals** — two objective strikes inside a short window.
  Strikes come from the incoming request: several errored tool results in
  the latest turn, or a test-failure shape in the prompt after the agent
  has already edited files. The threshold is configurable (default 2).

<Note>
  Automatic escalations are **canary-gated, and the canary starts at 0** —
  which means shadow mode: decisions are recorded, nothing actually
  switches. Raise **Rollout** to a percentage of sessions (or to all) when
  you want them to take effect. Client-requested escalations are always
  live; the client asked.
</Note>

## Coming back down

An escalated session returns to base on its own only when the task has
clearly cooled off: it has gone idle past the provider's prompt-cache
window, has run at least three clean turns since escalating, and the
current turn scores calm. Otherwise it stays strong.

Two faster paths back: send `X-OrcaRouter-Tier: base`, or start a new
session. Tier memory is per session **and** per router, and expires after
4 hours idle.

## Safety limits

| Limit                           | Meaning                                                                                                                                                              |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Max escalations per session** | How many times one session may ratchet up. Default 1. Not refunded when a session is reset back to base. A `once` boost is exempt.                                   |
| **Escalated-spend share cap**   | The share of the router's trailing-24h spend that may be served at strong tier, in percent. Applies to *every* trigger, client asks and `once` included. 0 = no cap. |

When a limit blocks an escalation the request is still served — at base
tier — and the response header says why.

## Seeing what happened

Escalation-eligible requests carry an `X-Orca-Session-Tier` response header,
one per request:

| Value                             | Meaning                                                           |
| --------------------------------- | ----------------------------------------------------------------- |
| `base`                            | Served at base tier.                                              |
| `strong`                          | Served at strong tier; the session was already escalated.         |
| `strong; reason=explicit`         | Escalated by `X-OrcaRouter-Tier: strong`.                         |
| `strong; reason=once`             | One-turn boost from `X-OrcaRouter-Escalate: once`.                |
| `strong; reason=difficulty`       | Automatic — the difficulty trigger fired.                         |
| `strong; reason=strikes`          | Automatic — the failure-signal trigger fired.                     |
| `base; reason=reset`              | The client sent `X-OrcaRouter-Tier: base`.                        |
| `base; reason=de_escalated`       | The session cooled off and returned to base.                      |
| `base; reason=strong_unavailable` | Strong tier was resolved but no pool model could serve this turn. |
| `base; reason=denied:session_cap` | Blocked by the per-session cap.                                   |
| `base; reason=denied:share_cap`   | Blocked by the spend-share cap.                                   |

Shadow-mode decisions report plain `base` — nothing switched, so nothing
changed for the caller. `X-Orca-Resolved-Model` still tells you exactly
which model served; see [Response Headers](/routing/response-headers).

The header is absent when escalation isn't in play for the request — the
router has escalation off, uses the DSL strategy, or the conversation
couldn't be identified.

## What it costs

Escalation adds no fee of its own: an escalated turn is billed at the
served model's normal price. The cost change is simply that a strong-pool
model usually costs more per token than the one the session started on, and
switching models means that turn's prompt cache starts cold.

Two knobs bound the exposure — **max escalations per session** caps how
often any one conversation can ratchet up, and the **escalated-spend share
cap** bounds strong-tier spend as a fraction of the router's own trailing
24h. Start in shadow mode to see how often escalation *would* fire on your
real traffic before it costs anything.

## Not covered

* **[Routing DSL](/routing/routing-dsl) routers** — these settings are
  ignored entirely. DSL rules are re-evaluated every turn and already
  express escalation directly: match on `difficulty` or `agent_state.*`
  (turns taken, tools used, whether tests just failed) and steer to a
  stronger model from the rule itself.
* **Direct model calls** — a request naming a model is served by that
  model, always.
* **Unidentifiable conversations** — with no resolvable session there is
  nothing to escalate. See
  [Session Affinity](/routing/session-affinity) for how a session is
  identified.
