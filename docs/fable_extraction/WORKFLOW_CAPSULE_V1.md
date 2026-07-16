# AIOS Runtime Workflow Capsule v1

- capsule_id: `aios.rwc.fable-projection.v1`
- contract: `ASC-0283`
- status: `candidate_not_promoted`
- rights: `internal_runtime_use_only`
- training_eligible: `false`
- source class: current official guidance plus one bounded Fable 5 operational
  specification call; raw provider output is not retained
- claim: this capsule may improve process reliability at inference time
- non-claim: this capsule does not reproduce Fable, transfer weights, or make a
  lower model capability-equivalent

## V1 evaluation disposition

ASC-0284 tested the full compact prompt against no capsule on the same frozen
`qwen3:1.7b` substrate. Both arms achieved 0/12 exact task successes, so all 12
pairs tied on the preregistered primary metric. The capsule arm also increased
scope violations from 1 to 3 and malformed outputs from 1 to 2. The named exit
is `HONEST_NEGATIVE`: this full-prompt form is not promoted for a 1–3B model.

This result does not show that every individual workflow rule is useless. It
shows that the combined prompt did not earn transfer under the tested T1
surface. For T1, consume at most one externally controlled state per prompt as
already specified in the tier table; any such ablation is a new experiment,
not a reinterpretation or rerun of V1. See
[WORKFLOW_EVAL_REPORT_V1.md](WORKFLOW_EVAL_REPORT_V1.md).

## Contract

Inputs are a task, allowed workspace, forbidden paths/data classes, budget,
model tier, acceptance checks, and operator override. Outputs are versioned
artifacts and exactly one terminal state:

- `DONE_VERIFIED`
- `DONE_UNVERIFIED`
- `ABSTAIN`
- `ESCALATE`

Hard invariants are privacy, explicit scope, reversibility, operator override,
budget accounting, provenance or uncertainty tags, no silent termination, and
no completion claim without evidence. A violation halts the workflow and emits
a failure receipt.

## State machine

```text
INTAKE
  -> SPEC_LOCK
  -> PLAN
  -> EXECUTE
  -> SELF_CHECK
  -> FRESH_VERIFY
  -> REPAIR (bounded)
  -> CLOSE

any state -> ABSTAIN | ESCALATE
```

Each transition appends `timestamp | state | evidence_pointer | budget_spent`
to a worklog. A missing line is a protocol failure. Repair is limited to two
rounds by default and one round for a 1–3B model. Repeated failure reopens the
spec once; a further failure exits rather than looping.

## Intake and ambiguity gate

Create a spec containing task, inputs, outputs, scope, assumptions, acceptance
checks, and gaps. Every acceptance check must be runnable or inspectable.
Classify gaps:

- `BLOCKING`: a different answer changes the deliverable or creates material
  risk. Ask once in a batched message.
- `DEFAULTABLE`: select and record a reversible default.

Proceed without questions when the task is already well specified and the
checks are executable. Exit `ESCALATE` when blocking gaps remain after one
round. Exit `DONE_UNVERIFIED` rather than claiming verified success when the
required checks cannot run.

## Decomposition and delegation

Every step declares a goal, input pointers, its own check, budget, and rollback
point. Split steps to fit the worker tier. Delegate independent discovery,
bulk reading, mechanical edits, and deterministic tests; keep final selection,
synthesis, and the verification verdict in separate accountable roles.

For parallel work use bounded fan-out:

```text
router/specifier
  -> solver lanes
  -> independent refuter
  -> synthesizer
  -> fresh verifier
  -> pass | repair | abstain | escalate
```

Workers return concise findings plus artifact pointers, not raw dumps. For
vision work, first create a textual observation artifact and mark unreadable
regions `UNCERTAIN`; a decision-critical uncertain region stops the branch.

## Artifact and provenance rules

Minimum artifacts:

- `spec`: scope, assumptions, checks, forbidden data
- `plan`: steps, checks, rollback points, budget
- `worklog`: append-only transitions and evidence pointers
- `deliverable`
- `claims`: `CLAIM | EVIDENCE | BOUNDARY`
- `verification`: independent checks and verdict
- `receipt`: model/tool identity, cost, failures, privacy scan, terminal state

External claims require a source and retrieval date or an `UNVERIFIED` tag.
Current/best/version/pricing claims require a fresh source. A load-bearing
unverified claim exits `ESCALATE`. Corrections append a new record; they do not
erase the old one.

Private-gated paths, auth material, raw provider history, and hidden reasoning
never enter prompts or shared artifacts. Social posts are discovery records,
not training data. GitHub code requires repository/file license review before
reuse.

## Independent verification

The verifier starts in a fresh context and receives only the spec, deliverable,
claim ledger, and acceptance checks—not the author's private rationale or
worklog narrative. It reruns deterministic checks, attempts to refute material
claims, and returns `PASS` or itemized defects. The author cannot edit the
verifier report; repairs cite defect IDs.

A same-model verifier can catch execution and logic defects but does not prove
independence from shared blind spots. Keystone claims should route to a
heterogeneous model, deterministic tool, or human. If no independent context
is available, close only as `DONE_UNVERIFIED`.

## Failure codes

| code | trigger | recovery | exit |
|---|---|---|---|
| `F_AMBIG` | blocking ambiguity remains | one batched clarification/default audit | `ESCALATE` |
| `F_CHECK` | acceptance check fails | repair the itemized defect, bounded | `ABSTAIN` or `ESCALATE` |
| `F_BUDGET` | cost/time/token ceiling reached | emit best partial and receipt | `ABSTAIN` |
| `F_SCOPE` | out-of-scope/private write or prompt | revert/redact and preserve receipt | mandatory `ESCALATE` |
| `F_PROV` | material claim lacks evidence | one focused retrieval round | `ESCALATE` |
| `F_LOOP` | same defect recurs twice | reopen spec once | `ESCALATE` |
| `F_ENV` | required tool/access missing | name the exact gap and fallback | `ESCALATE` |
| `F_MODEL_SUB` | observed model differs from requested | invalidate identity-sensitive run | fallback contract |

## Model-tier adaptation

| tier | execution surface | verification | exit bias |
|---|---|---|---|
| 1–3B | one state per prompt, fill-in schema, one function/file at a time | deterministic checks only | abstain early |
| 7–14B | compact full capsule, one phase per prompt, bounded repair | deterministic plus claim ledger | escalate material ambiguity |
| stronger local | router, solver/refuter lanes, tool state machine | full fresh-context protocol | contract-defined |

Do not ask a 1–3B model for a free-form final judgment. Let it fill structured
fields and run external checks. Route tasks only after a conformance probe for
that task family.

## Reusable runtime prompt

```text
Operate under AIOS-RWC-v1. Follow states in order and never claim completion
without the required evidence.

CONFIG
- workspace: {allowed_paths}
- forbidden: {paths_and_data_classes}
- tier: {T1|T2|T3}
- budget: {time_tokens_cost}
- repair_max: {N}
- operator override: STOP

INTAKE: Write a spec with task, inputs, outputs, scope, assumptions, and
runnable/inspectable acceptance checks. Label each gap BLOCKING or DEFAULTABLE.
Ask all blocking questions once; otherwise record reversible defaults. Stop as
ESCALATE if a material gap remains.

PLAN: Number the steps. Each step needs goal, input pointers, a check, budget,
and rollback point. A step without a check is invalid.

EXECUTE: Do one bounded step at a time. Append state, changed paths, raw check
result pointer, and budget spent to the worklog. Delegate only independent
labor. Keep final synthesis and verdict separate. Never expose forbidden data.

SELF_CHECK: Rerun every check. Record external assertions as
CLAIM | EVIDENCE(source/date or command result) | BOUNDARY. Tag unsupported
claims UNVERIFIED. A load-bearing unverified claim exits ESCALATE.

VERIFY: Start a fresh verifier with only the spec, deliverable, claims, and
checks. Accept its PASS or itemized defects without editing the report.

REPAIR: Fix defect IDs only and increment the counter. If the same defect
recurs twice or repair_max is exceeded, reopen the spec once, then exit
ABSTAIN/ESCALATE with evidence.

CLOSE: State scope, assumptions, verification status, known limits, cost, and
one of DONE_VERIFIED, DONE_UNVERIFIED, ABSTAIN, ESCALATE. Halt within one step
on STOP. Never terminate silently; a failure receipt is a valid deliverable.

For vision, first create an observation transcript, mark unreadable regions
UNCERTAIN, and stop if a decision depends on an uncertain region.

T1: process exactly one state per prompt; use deterministic checks only;
repair_max=1; abstain when a check or required evidence cannot be produced.
```

## Held-out evaluation and promotion gate

Pre-register at least 12 tasks across four or more axes. Freeze task, rubric,
seed source, prompt, model/tool configuration, and hashes before running:

- `B0`: lower model with ordinary task prompt
- `B1`: the same lower model and conditions plus this capsule

The grader never sees a Fable answer. Prefer executable checks; blind-randomize
arms for judgment rubrics. Track paired success, false-completion rate, scope
and privacy violations, provenance coverage, appropriate abstention, cost,
latency, malformed output, and operator interventions.

Candidate hypotheses requiring validation:

- `H1`: bounded step size helps T1/T2 more than uncapped decomposition.
- `H2`: a verifier deprived of author rationale catches more defects than a
  shared-context reviewer.
- `H3`: one-state-per-prompt templates outperform the full capsule for T1.
- `H4`: planner/refuter separation produces gains beyond extra token spend.

Promote a rule only when the paired held-out result improves without safety,
scope, privacy, or false-completion regression. ASC-0283 V1 requires at least
8 wins in 12 tasks. A negative result is `HONEST_NEGATIVE`, not a reason to
change the suite after seeing results.

## Non-transferable limits

This capsule adds scaffolding; it cannot supply missing world knowledge,
visual acuity, coding skill, context capacity, or provider-internal training.
Deterministic checks prove only what they cover, and same-family agreement is
not heterogeneous validation. The numerical limits above are candidates, not
universal constants. Only measured rules should survive into v2.

No artifact produced from this capsule is eligible for parameter training by
default. A future adapter requires separately licensed/consented data, a rights
manifest, privacy review, train/eval separation, rollback, and explicit
operator/provider authorization.
