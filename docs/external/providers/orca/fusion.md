> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Fusion (Fable 5-level)

> Call a curated panel of frontier models behind one slug — they answer in parallel and a judge returns the single strongest answer, cross-checked against the rest. A Fable 5-level option you can call today, OpenAI-compatible.

**Fable 5 is gone. This is the answer you can call today.**

**Fusion** runs a panel of frontier models in parallel, then a judge returns
the single strongest answer — Fable-5-level intelligence behind one slug, no
waitlist. You call it like any other model; the fan-out, the judging, and the
per-leg billing all happen for you.

<Tip>
  **The judge is the point.** Several frontier models answer in parallel, and a
  judge returns the strongest answer *verbatim* — cross-checked against the
  rest, not one model's first try, and never a black-box blend. You always get
  a real model's complete answer, not a benchmark we cherry-picked.
</Tip>

This is the "call a preset" front door to the
[Routing DSL](/routing/routing-dsl): the panels below are curated and managed
for you. Want a different panel, a different judge, or your own gating rules?
Compose your own in the DSL.

## How it works

<Steps>
  <Step title="Route by difficulty">
    Casual chat goes straight to a cheap default. The hard stuff — code,
    agents, tool use — earns the full panel.
  </Step>

  <Step title="Fan out to the panel">
    Every model takes a swing at once — independent attempts that each catch
    what the others miss.
  </Step>

  <Step title="The judge picks the strongest">
    A judge reads them all and hands back the single best answer *verbatim* — a
    real model's complete response, never a blend.
  </Step>
</Steps>

No cherry-picked benchmarks, no hidden black box: the panel and the judge are
listed below, and the DSL equivalent lets you inspect every leg.

## The panels

Three curated panels, frontier to budget. Call the slug — we keep the members
current so you don't have to.

| Call it as                | Panel                                      | Best for                   |
| ------------------------- | ------------------------------------------ | -------------------------- |
| `orcarouter/fusion`       | Claude Opus 4.8 · GPT-5.5 · Gemini 3.1 Pro | Hardest reasoning and code |
| `orcarouter/fusion-mini`  | Claude Opus 4.8 · GPT-5.5                  | A leaner two-model panel   |
| `orcarouter/fusion-flash` | A budget panel of cheaper models           | Cost-sensitive fan-out     |

The judge is Claude Opus 4.8 for all three.

## Call it

Fusion is OpenAI-compatible — swap the model slug, everything else stays the
same:

```bash theme={null}
curl https://api.orcarouter.ai/v1/chat/completions \
  -H "Authorization: Bearer $ORCAROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "orcarouter/fusion",
    "messages": [{"role": "user", "content": "Find the data race in this Go cache and give a corrected version."}]
  }'
```

## Billing

A fan-out runs each panel member plus the judge, so a fanned-out request is
billed as the **sum of those underlying completions** — at cost, zero markup —
and **only on the requests that actually fan out**. Easy requests fall through
to a cheaper default and bill as a single call. Each leg appears as its own
row in your request logs, sharing one request.

## Beyond the preset

The presets are `best_of_n` over a fixed panel. The same engine, authored as
[Routing DSL](/routing/routing-dsl), hands you the whole graph:

* **Route by difficulty** — fan out only on the hard requests; keep "hi" on a
  cheap default so you never pay panel price for chit-chat.
* **Swap the judge** — pick the arbiter model, or change the strategy entirely:
  `synthesize` to fuse one answer, `tests_pass` to keep the patch that passes,
  `majority`, or `first`.
* **Build your own panel** — any models, any number of legs, your own gating.
* **Cascade on a weak answer** — retry with a stronger model when the first
  one looks low-confidence.
* **Ship it like infra** — shadow a ruleset, canary it onto a slice of
  traffic, and dry-run it against a sample request before it serves anyone.

Load a **Claude Fable 5 Level** template in the DSL editor to start from a
working panel and edit it to the models you use.

<Card title="Compose your own panel" icon="wand-magic-sparkles" href="/routing/routing-dsl">
  Pick the models, swap the judge, and set exactly when the panel fires — your
  whole routing graph in a few lines of YAML.
</Card>
