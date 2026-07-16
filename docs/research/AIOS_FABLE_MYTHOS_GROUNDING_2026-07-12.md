# Fable 5 / Mythos 5 / Dynamic Workflows grounding

- checked: 2026-07-12 KST
- contract: `ASC-0283`
- purpose: separate current official facts, local observations, community
  hypotheses, and prohibited collection paths before AIOS reuses anything
- authority: public-source research plus bounded local provider receipts

## Executive decision

There is no model-expiry bypass to perform. The July 12 deadline covers the
temporary inclusion of Fable 5 in subscription usage limits, not the existence
of Fable 5. The promotion ends at `2026-07-12 23:59:59 PT`, which is
`2026-07-13 15:59:59 KST`; afterward Fable remains available through usage
credits and provider API surfaces. Mythos is not generally public and remains
limited to approved Project Glasswing customers.

AIOS may therefore continue using Fable through authorized account surfaces,
with model-identity, cost, retention, and fallback receipts. It may not evade
authentication, payment, nationality/account, entitlement, classifier, or
safeguard controls. It also may not use Claude outputs as targets for training
a general-purpose or competing model without written permission. The durable
asset produced under this contract is a runtime workflow capsule, evaluation
harness, and capability route—not a weight-distillation corpus.

## Official claim ledger

| claim | evidence | boundary / implication |
|---|---|---|
| Promotional inclusion is extended through July 12, 2026 at 11:59:59 PM PT; Fable can continue through usage credits afterward. | [Claude Help Center: Fable 5 promotional access](https://support.claude.com/en/articles/15424964-claude-fable-5-promotional-access), updated 2026-07-07 and fetched 2026-07-12 | This is not a free-access extension after the deadline and does not grant credits. |
| Fable 5 is generally available; its API identifier is `claude-fable-5`. Mythos 5 is limited to approved Project Glasswing customers. | [Claude model documentation](https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5) | A binary or UI mentioning Mythos is not entitlement evidence. |
| Fable and Mythos share the same underlying model/capabilities; Mythos differs in safeguards and access. | [Anthropic redeployment announcement](https://www.anthropic.com/news/redeploying-fable-5) and [model documentation](https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5) | This does not make Mythos generally reachable, nor authorize safeguard evasion. |
| Fable/Mythos require 30-day retention and are unavailable under zero-data-retention arrangements. | [Claude API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) | Private or sensitive workspace contents must not be sent merely because access works. |
| Documented Fable strengths include long-horizon autonomy, complex first-shot correctness, vision, enterprise artifacts, code review/debugging, ambiguity navigation, and delegation. | [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5) | These are vendor claims and design axes, not proof that a local capsule transfers them. |
| Fresh-context verification, explicit self-checks, bounded autonomy, and less over-prescriptive prompts are recommended; internal reasoning reproduction should not be requested. | [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5) | AIOS stores observable artifacts and verdicts, never hidden reasoning. |
| A refusal can arrive with HTTP 200 and `stop_reason=refusal`; optional fallback may use Opus 4.8. | [Refusals and fallback](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback) | Model-identity probes must not silently fallback; `modelUsage` must identify Fable. |
| Claude outputs may support applications and non-competing classifiers/tools, but using them to train or develop general-purpose or competing AI models is prohibited without written permission. | [Anthropic output-training policy](https://support.claude.com/en/articles/12326764-can-i-use-my-outputs-to-train-an-ai-model) and [Commercial Terms](https://www.anthropic.com/legal/commercial-terms) | `training_eligible=false` is the default for every artifact under ASC-0283. |
| Dynamic Workflows are JavaScript orchestration programs supported in Claude Code 2.1.154+, with up to 16 concurrent and 1,000 total agents per run. | [Claude Code Dynamic Workflows](https://code.claude.com/docs/en/workflows) | They can consume much more usage; scale is not quality and every run needs a budget/exit. |

## Local provider evidence

The locally installed Claude Code version is `2.1.207`. A bounded, authorized
non-persistent probe explicitly requested `claude-fable-5`; the returned
`modelUsage` key was `claude-fable-5`, the context window was 1,000,000, and no
fallback was configured. A second bounded call projected observable workflow
rules into `docs/fable_extraction/WORKFLOW_CAPSULE_V1.md`. Session identifiers
and raw outputs are intentionally not retained in shared artifacts.

The sanitized receipt is
`docs/evidence/ASC-0283/fable_access_and_capsule_receipt.json`. This establishes
authorized access and model identity on 2026-07-12 only. It does not establish
future availability, Mythos entitlement, or capability transfer.

A bounded Dynamic Workflow attempt also established that the Fable parent
could generate a workflow routing review workers to `claude-sonnet-5`.
However, no review result is counted: the first non-interactive run stopped at
a plan-only approval gap, and the execution run ended before final synthesis.
The latter was configured with `--max-budget-usd 1.60` but reported `$2.1645388`
in cost. AIOS classifies this as `provider_budget_guard_overshoot`, records the
failed run, and stops all further provider calls under the contract. Dynamic
Workflow budget flags must be treated as soft/lagging guards until this
behavior is independently resolved.

## Community discovery ledger

Community material is useful for finding failure modes and evaluation ideas,
but it is not an authority for access, terms, or performance claims.

| surface | observation | treatment |
|---|---|---|
| X | Official accounts discussed the July 12 promotion and planner/worker cost-quality patterns, but direct posts were not reliably readable in this environment. | Retain links as discovery records; do not treat mirror text or marketing benchmarks as an independent evaluation. |
| Threads | No verifiable public Fable/Dynamic Workflows post was found; direct access/search was unsuccessful. | Record absence; do not invent a Threads consensus. |
| Reddit | Users corroborated the July 12 UI notice and proposed having Fable create project skills, plans, and review gates. | Hypothesis source only. Anecdotal quality/cost claims require a held-out local test. |
| GitHub | Official docs/cookbooks demonstrate planner-orchestrator plus smaller workers. Community ports expose resumable journals, isolation, routing, and verifier loops. Issues report possible safety-classifier fallback and advisor incompatibility. | Use licensed code only after file/repo license review. Issues are failure hypotheses, not confirmed provider defects. |

Useful references:

- [Anthropic managed-agent planner/executor cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/managed_agents/CMA_plan_big_execute_small.ipynb)
- [Official Anthropic Claude API skill](https://github.com/anthropics/skills/blob/main/skills/claude-api/SKILL.md)
- [Community skill-harvest discussion](https://www.reddit.com/r/ClaudeAI/comments/1ukynrw/friendly_reminder_to_have_fable_5_write_skills/)
- [Community workflow port](https://github.com/QuintinShaw/pi-dynamic-workflows)
- [Provider-neutral workflow port](https://github.com/imsai-sh/open-dynamic-workflows)
- [Reported classifier fallback issue](https://github.com/anthropics/claude-code/issues/66728)
- [Reported advisor compatibility issue](https://github.com/anthropics/claude-code/issues/66742)

## Existing corpus disposition

The pre-existing `docs/fable_extraction/` documents are retained as historical
hypotheses and rubric ideas. An independent audit rejected them as a defensible
distillation dataset because model-identity, citations, claim freshness,
rights, experimental independence, and reproducibility are incomplete. Useful
salvage candidates are independent author/critic contexts,
`CLAIM / EVIDENCE / BOUNDARY`, falsification budgets, and builder/judge/steward
separation. They still require held-out validation.

During this turn, an unrelated workspace path `../distill/` was observed being
populated with a script and files derived from private Claude project history,
including reasoning/tool fields and outputs intended as SFT targets. ASC-0283
does not authorize reading, dispatching, training on, publishing, deleting, or
rewriting those artifacts. They are marked `QUARANTINED_UNREVIEWED`, with
`training_allowed=false`; any future handling requires an explicit privacy,
rights, and provenance audit authorized by the operator.

## Safe continuation route

1. Continue Fable only through legitimate subscription credits/API surfaces.
2. Verify the requested and observed model on every identity-sensitive run.
3. Keep private repository/history content out because of the 30-day retention
   requirement.
4. Use Fable as a bounded planner/advisor/verifier where measured value exceeds
   cost; use smaller workers for mechanical work.
5. Promote only capsule rules that improve held-out paired outcomes without a
   safety, privacy, scope, or false-completion regression.
6. Report the result as workflow transfer, never model equivalence.
