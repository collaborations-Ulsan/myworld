# control_arms — independent strong-control (arm B) implementations

**Owner: cjw0076 (myworld_computation session).** Author-distinct from arm C
(memoryOS / partition experts, `codex@myworld` / `claude@myworld`) so the
prereg `consumed_by` requirement (implementer ≠ arm-C author, confirmed by
commit author) is satisfied by construction.

This directory holds the **strong control arms** for the peer's memory
experiments. It exists because both preregs make arm B *the whole design*:

> "B 없이 C가 A를 이기면 우리가 발견한 것은 캐싱/압축 일반이고, 그건 이미
> 세상이 안다."  — M2 §2.4 / M3 §1

If the party who authored arm C also builds arm B, they unconsciously build a
B that is easy to beat. The routing fix (`experiment.control_arm` is a
capability the arm-C author does not own) makes that structurally impossible.
I am the independent implementer.

## Seam discipline (frozen)

- **Import none of the peer's `aios_*` / arm-C code.** Every control here is
  reimplemented from prereg *prose* only.
- Each arm is a **standalone CLI I own**, invoked by the peer's `compare`
  harness as an **external subprocess (referee pattern)** — symmetric with the
  way the external oracle is a black box to the arms. The peer's optimizer
  never sees inside arm B; arm B never sees inside the oracle.
- Commits here are authored `cjw0076`. That is the `consumed_by` proof.

Same shape as the existing `../falsifier_executor/` seam participant: my code
in the peer's repo tree, architecturally isolated, run as a referee.

## Fairness findings delivered to the peer (2026-08-19)

The independent implementer's first job is not to build B but to check whether
the prereg *constrains B into weakness*. Two findings (recorded here so they do
not evaporate with chat):

### M2 (memory-as-computation) — two guards, absent ⇒ C wins unfairly

1. **Same-K constraint (leakage symmetry).** Gate 0 removed `task_id` from the
   legitimate key K. If arm C's provenance / draft-accept retrieval hits across
   K-variation while a content-address cache keyed on K cannot, the `task_id`
   leakage M1 excluded has re-entered on C's side in a new shape. ⇒ a strong B
   must carry **exact content-address + semantic near-match retrieval** so it
   competes on the *same* legitimate K, and C's retrieval must be audited to use
   only legitimate K.
2. **Cache invalidation.** A naive cache with no invalidation serves stale wrong
   answers when the corpus changed ⇒ fails Gate 1 (capability) ⇒ hands C an
   unfair win. A strong conventional cache versions its key on the corpus state
   it depends on (build-cache / CDN standard — *not ours*). B is built **with
   version-keyed invalidation**, so it never serves stale, passes Gate 1
   cleanly, and the real contest is Gate 2 cost (= maximise legitimate-K hit
   rate).

⇒ **M2 strong B = exact content-address ⊕ semantic near-match ⊕ prompt-cache ⊕
version-keyed invalidation.**

### M3 (partition society) — one core guard

The three frozen task types (cross-layer citation tracing / supersede chains /
cross-layer evidence contradiction) have answers that are *intrinsically about
the layer / provenance structure*. Removing the mechanical aggregation identity
(E2-1) with a real agent does **not** remove the **structural affinity**:
questions on the layer axis favour a society partitioned on the layer axis. This
is the mirror image of A1's `observable-competence ceiling`.

⇒ a fair B must **not be blinded to the layer / provenance metadata** C's router
uses. B compresses the *same layer structure* into a single resident
**graph-structure-preserving digest** (per-target inbound-by-layer counts,
supersede edges, contradiction pairs), not a prose summary. Then the real
experimental question is sharp: **does that digest fit one context?**
- fits and answers ⇒ C gains nothing (honest null).
- digest itself exceeds context ⇒ partition earns its keep (honest positive).

This B is the M3 analog of A1's shuffle control: it separates "the society earns
the win" from "merely knowing the layer structure suffices" — which a single
context can also have. Secondary (recommended, not required): mix in questions
whose answer is *not* the layer itself, to fully break the identity.

## Build order

1. **`m2_cache.py`** — M2 arm B. Contract-robust core built first (K opaque,
   `compute_fn` callback, pluggable near-match). Thin adapter to the peer's
   `compare` I/O contract wired once the 5 contract answers land.
2. **`m3_digest.py`** — M3 arm B (graph-structure-preserving digest). After M2.

## Contract requested from the peer (prose, not their code)

1. arm I/O signature `compare` expects (question format, exact legitimate-K
   fields, expected oracle-scored answer shape).
2. Fixed model + call contract; Gate-3 frozen alternate model.
3. Corpus access API arms may use (M3: `/data/jaewon/aios/index/aios.db` schema).
4. Oracle interface (input/output only — B is scored by it, never sees it).
5. M2: operational definition of legitimate K (which fields are K, what is
   excluded).

Until (5) lands, `m2_cache.py` treats K as an opaque structured dict.
