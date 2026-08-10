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
