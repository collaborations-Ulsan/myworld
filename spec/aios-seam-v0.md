# AIOS Seam v0 — the language-neutral boundary

> An ecosystem designer does not pick languages. They specify the seam and let
> everyone else pick. This file is the seam. It contains no Python, names no
> runtime, and requires nothing of a participant except that it can hash bytes
> and write JSON lines.

**Status: v0 draft.** The conformance checker (`scripts/aios_conform.py`) is
normative where this text and the checker disagree — the checker runs, prose
does not. A change to either without the other is a defect.

## 0. Why a seam at all

Our own measurement, three mechanisms across 96 episodes: everything we
**offered** was used zero times; only what was **injected or enforced** moved a
number. An ecosystem is that failure at a larger scale — a specification nobody
implements is an offer. So this seam is defined so that a **non-conforming
participant is rejected by a check, not by a policy document**.

The single test of whether this seam is real:

> **A foreign implementation, in a language that is not ours, linking none of
> our code, can produce artifacts that pass `aios_conform.py`.**

If that is impossible, the seam does not exist and what we have is a codebase.
`spec/examples/producer.sh` exists to keep us honest about this: POSIX shell and
`sha256sum`, no Python, no imports.

## 1. Artifact A — the event ledger

An **arc** is an append-only sequence of events. One JSON object per line, UTF-8,
`\n`-terminated, no trailing whitespace.

Line content is the participant's business. The seam constrains only the
**identity of the history**:

```
leaf(i, line)  = "sha256:" || hex( SHA256( decimal(i) || 0x00 || line_without_newline ) )
root(leaves)   = "sha256:" || hex( SHA256("") )                     if leaves is empty
                 fold(sort(leaves))                                  otherwise

fold(layer)    = layer[0]                                            if len(layer) == 1
                 fold([ "sha256:" || hex(SHA256(a || b))
                        for (a, b) in pairs(layer) ])                otherwise
pairs(layer)   = consecutive pairs; if the layer has odd length the last element
                 is paired with ITSELF.
```

Two properties are load-bearing and a participant MUST preserve both:

1. **Position salting** — `i` is the 0-based line index and it is inside the
   leaf hash. Reordering a history therefore changes the root. A Merkle tree
   over unsalted lines would call a reordered history identical, which would
   make "append-only" unenforceable.
2. **Concatenation, not re-hashing** — `a` and `b` in `fold` are the leaf
   *strings* including their `sha256:` prefix, concatenated as text.

*Rationale for sorting before folding: the leaves already carry position, so
sorting yields a canonical tree shape without losing order information.*

## 2. Artifact B — the cycle receipt

A participant claims to have completed one operating cycle by emitting a receipt
with `"schema": "aios.minimal_operation.v1"` and these four members:

| member | required keys | meaning |
|---|---|---|
| `sense` | `predicate`, `evaluated_by`, `input_digest`, `model_consulted` | a condition was judged |
| `act` | `operator`, `invoked_by`, `model_offered_choice` | something was executed |
| `verify` | `oracle_cmd_digest`, `verdict`, `verifier_identity` | a judge ruled on the result |
| `settle` | `outcome`, `root_before`, `root_after` | the ruling was durably recorded |

A receipt is **conforming** iff all of the following hold:

```
sense.model_consulted      == false
act.invoked_by             == "host"
act.model_offered_choice   == false
verify.verifier_identity   != act.operator
verify.verdict             ∈ {"pass", "fail"}
settle.outcome             ∈ {"committed", "reverted"}
settle.root_before         != settle.root_after
verify.verdict == "pass"   ⟺  settle.outcome == "committed"
every *_digest / root_*    matches ^sha256:[0-9a-f]{64}$
```

Each clause is there because dropping it admits a specific fake:

- `model_consulted`/`invoked_by`/`model_offered_choice` — without these a system
  that merely *offered* an action could claim the cycle. That is the exact thing
  we measured at zero.
- `verifier_identity != operator` — without it the executor grades itself.
- `root_before != root_after` — without it a cycle can claim to have settled
  while writing nothing.
- the `verdict ⟺ outcome` biconditional — without it a participant can report
  `fail` and commit anyway, or report `pass` and revert, and the verdict becomes
  decoration.

**A conforming receipt is not a claim that the work was good.** It is a claim
that a condition was judged without asking a model, something ran without a
model selecting it, a separate judge ruled, and the ruling changed a durable
record. Nothing more is asserted, and a participant MUST NOT read more into it.

## 2b. Separation — the verifier must live below what it judges

A string comparison of `verifier_identity != operator` catches a receipt that
*names* the executor as its own judge. It does not catch a verifier the executor
can **rewrite**, and those are different failures. Enforcement is not a matter of
speed or language; it is a matter of who can modify whom, and a check running
inside the trust domain it checks is not a check.

Two extra members make the separation explicit and refusable:

| member | values | meaning |
|---|---|---|
| `act.executes_code` | bool | the operator ran code supplied by an untrusted party (a falsifier, a fetched script, a model-authored program) |
| `verify.isolation` | `same_process` · `separate_process` · `remote` · `sandboxed` | how the verifier was kept out of the executor's reach |

**Rule.** `act.executes_code = true` ⟹ `verify.isolation ≠ same_process`.

A text-only operator (a remote model returning a string) may honestly declare
`same_process`, because a string cannot reach into the verifier. The moment the
operator RUNS something, that stops being true, and the receipt must show the
boundary rather than assert good intentions.

This clause exists because it will be violated by the obvious next step. A
ledger row already carries a `falsifier`; the design's whole direction is to make
those runnable. On the day a falsifier executes, the executor becomes untrusted
code inside our own process, and without this clause the receipt would look
exactly as conforming as it does today.

## 2c. Binding — an edge that fired but was ignored is a new zero

Forcing an invocation is not enough. A mandatory operator can be called on every
single cycle and still change nothing, because the caller is free to drop what it
returned:

```
operator invoked   32/32
primary ignores the output
effect on outcome  none
```

That is the same failure as an unused offer wearing a receipt. `sense`/`act`
prove the host DECIDED and RAN; nothing so far proves the result was USED.

A receipt therefore MAY carry an `edge` — a host-mandated sub-step whose output
feeds the act — and when it does, the binding is enforced:

| member | meaning |
|---|---|
| `edge.edge_id` | which mandatory edge this is |
| `edge.invoked_by` | must be `host`; an edge the model chose to call is an offer |
| `edge.output_digest` | digest of what the edge produced |
| `act.context_components` | digests of everything that composed this act's input |

**Rule.** `edge` present ⟹ `edge.invoked_by == "host"` **and**
`edge.output_digest ∈ act.context_components`.

Read it as the difference between four things a receipt could mean, which must
not be conflated:

```
Activation   the edge fired                    ← sense/act already prove this
Delivery     its output entered the next input ← THIS clause
Uptake       the information changed behaviour ← not provable from a receipt
Value        the change improved the oracle    ← an experiment, not a schema
```

**Correction (2026-08-13).** An earlier version of this section claimed the
clause buys Delivery. It does not — it buys **D0, declared coupling**. Listing a
digest in `act.context_components` does not show that the bytes that digest
names were assembled into the input, so a producer can name the edge and omit
its content. §2d adds the step that closes that gap. The ladder below is the
honest decomposition:

```
D0  manifest inclusion            the digest was declared      ← this section
D1  exact-byte delivery           the bytes were assembled     ← §2d
U0  canary processed              the content passed through   ← §2d
U1  decision changed under intervention                        ← counterfactual replay
V   external oracle improved                                   ← an experiment
```

The clause buys D0 and nothing more, and the honesty is the point: a
conforming receipt still does not show that the information mattered. Separating
Uptake from Value needs a **sham edge** — the same call, the same latency, the
same token volume, carrying a schema-matched pack with no information — because
without it a real edge's effect cannot be told apart from extra compute, extra
delay, longer context, or the framing that someone reviewed the work. The seam
deliberately does NOT encode which arm a receipt belongs to; blinding is the
experiment's business, and a checker that could read the arm would leak it.

## 2d. Exact-byte delivery and the uptake canary

D0 is cheap to forge. Two additions make the next two rungs checkable.

### D1 — the input manifest must tile the input

```json
"act_input": {
  "serialized_request_digest": "sha256:R",
  "length": 6960,
  "assembled_by": "host-adapter",
  "components": [
    {"kind": "edge_output", "digest": "sha256:E", "start": 4812, "end": 6960}
  ]
}
```

**Rules.** Components MUST be ordered, non-overlapping, and their spans MUST
tile `[0, length)` with no gap. `edge.output_digest` MUST appear as a component
with a byte range. `assembled_by` MUST NOT be the act's operator.

Why tiling: an offset list that need not cover the input lets a producer declare
a range for the edge and quietly assemble something else. Requiring the spans to
account for every byte means naming the edge without carrying it forces a lie
about the rest of the input as well.

Why `assembled_by`: the manifest has to come from whatever actually serialises
the request onto stdin or the wire, not from the component being attested. This
is §2b's principle applied to the manifest — a description of the input written
by the thing being described is not evidence.

**What this still does not prove**: that the serialised request reached a model.
A receipt cannot show that, and the spec says so rather than implying otherwise.

### U0 — the canary

The edge payload carries a random nonce, and the act's structured output must
return

```
uptake_commitment = SHA256(nonce || act_id || selected_action)
```

The checker recomputes it. A matching commitment proves the act **read a value
that existed only inside the edge** and carried it into its structured output —
channel uptake, which is strictly more than delivery.

**It does not prove the advice was used.** Copying a nonce that sat beside the
content is exactly what a model ignoring the content would still do. U0 is a
floor, not a finding, and anything above it needs an intervention:

```
Run A   state S, edge E    -> projection (selected file, hypothesis id, tool)
Run B   state S, edge E'   -> same projection
        only the edge payload differs
```

Different projections mean the decision depended on the edge. That is U1, it
costs two runs, and it belongs in an experiment rather than in a schema — a
sampled 5-10% is enough while every run carries D1 and U0.

## 2e. A declared enforcement gap must be internally consistent

A receipt MAY carry `enforcement_gap` — which forbidden rungs a cage actually
refuses and which it cannot. Optional, because requiring it would invalidate
every receipt written before the field existed. What is checked is what is
CLAIMED:

- listing a rung at or below L4 as needing a human grant is refused; a cage
  refuses those deterministically, and overstating the gap hides where
  enforcement really stops
- `fully_cage_enforceable: true` alongside a non-empty gap is refused
- reporting dishonesty with nothing unenforceable to be dishonest about is refused

**`honest` and `fully_cage_enforceable` are different questions.** A grant that
forbids deployment and SAYS a cage cannot refuse it is honest and not fully
enforceable at the same time. Collapsing the two makes candour look like a
defect, which is how a schema teaches producers to stop declaring.

## 3. Artifact C — the enforcement boundary

`aios.sandbox_receipt.v1`, referenced from `act.receipt` when the act ran
untrusted code. This artifact is **not** specified as an implementation
(namespaces, containers, VMs are all acceptable); it is specified as a set of
claims that must be *false-if-untrue*:

| key | meaning |
|---|---|
| `engine` | what enforced it — free text, but must name a mechanism, not an intention |
| `network` | `"denied"` or `"allowed"`. `"denied"` asserts an attempt would fail |
| `paths_denied` | paths the executed code could not read, as claimed |

The seam takes no position on how a participant achieves this. It takes a hard
position on how the claim is checked: `"denied"` MUST be backed by a probe that
actually attempted the operation and observed refusal. **A capability claim not
backed by an attempted-and-refused probe is a lie in this schema**, and the
conformance checker cannot detect it — which is why this section says so
explicitly rather than pretending the checker covers it.

## 4. What the seam deliberately does NOT specify

Naming these keeps the seam from growing into a framework:

- the language, runtime, process model, or scheduler of a participant
- what a ledger line contains beyond being one JSON object
- what an oracle is, how it decides, or what it is written in — only that its
  identity differs from the operator's and its command is digested
- retrieval, memory, planning, prompting, or any model-facing concern

## 5. Versioning

`v0` means: expect breaking changes; the conformance checker is the reference.
A participant states the version it targets in the schema string. There is no
negotiation mechanism yet, and adding one before there is a second implementation
would be designing for an ecosystem that does not exist.

## 6. Open — stated rather than hidden

1. No signature or attestation. Any participant can fabricate a conforming
   receipt about work it never did. The seam currently establishes *shape*, not
   *authenticity*. Externally there is 2026 work on exactly this
   (receiver-attested receipts, delegation-receipt drafts at IETF); adopting one
   is a decision, not an oversight.
2. `oracle_cmd_digest` digests the oracle's *command*, not its behaviour. Two
   different oracles with the same command line are indistinguishable.
3. No revocation: a settled receipt cannot be withdrawn, only superseded by a
   later event, and supersede semantics are not in v0.
