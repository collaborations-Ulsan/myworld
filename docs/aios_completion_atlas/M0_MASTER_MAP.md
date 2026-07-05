# M0 — Master Completion Map of AIOS

**Author:** Fable 5 (heterogeneous frontier designer) · **Date:** 2026-07-05
**Status:** authoritative frame for the atlas. Built FROM repo reality (scripts/, experiments/,
sibling repos), not from aspiration. Marks: ✅ exists · ◻ missing · ⚠ exists-but-wrong-shape.
**Read with:** `AIOS_NORTHSTAR.md` (product), `AIOS_MINIMUM_KERNEL_AUDIT.md` (kernel 6/6),
`AIOS_AGI_CERTIFICATION_KEYSTONE.md` (thesis + panel verdict + witness).

---

## 0. The one structural recognition (frame for everything below)

AIOS today is **two products sharing one repo**, plus a **fossil**:

1. **The ORGANISM** (founder north star): a permissioned local head — `aios <goal>` →
   plan → governed runtime → provider/local-LLM substrate → receipts → memory. Kernel 6/6 BUILT.
2. **The CERTIFICATION LAYER** (AGI thesis): typed certificates (APEX/IRIS/DescentNet/GoEN)
   over a shared Akashic ledger. Prototyped ONLY inside `experiments/agi_witness/`; verdict pending.
3. **The FOSSIL** (governance exoskeleton): 218 contracts, 5.8k-line ledger, ~50 governance
   docs, dozens of self-development scripts. Frozen by founder override; still ships in the tree.

**Completion = (1) hardened into a service, (2) resolved-and-positioned by the witness verdict,
(3) archived out of the shipping artifact.** The certification layer is NOT assumed into the
architecture: it enters the hot path only if the witness fires; otherwise it ships as an
optional lint/guard tier. Both branches are drawn below — a completed AIOS exists on EITHER.

---

## 1. End-state architecture (with today's status per seam)

```
                            ┌─────────────────────────────────────────────┐
                            │  SERVICE SURFACE                            │
                            │  aios <goal> CLI ✅ (aios_launcher/head)     │
                            │  MCP server ✅ (aios_mcp_server)             │
                            │  chat/copilot ⚠ (aios_chat, copilot_serve — │
                            │   demo-grade)  ·  install/onboard ⚠         │
                            └───────────────┬─────────────────────────────┘
                                            │ goal (NL) + user authority grant
                                            ▼
 ┌───────────────┐  context pack   ┌──────────────────────┐   route rec.  ┌───────────────┐
 │ MemoryOS ✅    │◄───────────────►│  HEAD (planner)      │◄─────────────►│ CapabilityOS ✅│
 │ draft-first   │  evidence-refs  │  aios_head.py ✅      │  observation  │ recommend-only│
 │ graph+akashic │                 │  goal→ContractObject │  write-back ⚠ │ catalog+router│
 │ work index    │                 └─────────┬────────────┘               └───────────────┘
 └───────────────┘                           │ ContractObject (typed plan+authority)
        ▲                                    ▼
        │            ┌───────────────────────────────────────────────┐
        │            │  CERT GATE ◻ (position decided by witness)    │
        │            │  APEX answerability · IRIS identifiability ·  │
        │            │  DescentNet H¹ consistency · GoEN legibility  │
        │            │  today: experiments/agi_witness/certs/*.py    │
        │            │  (prototype, not a library, not in hot path)  │
        │            └───────────────────┬───────────────────────────┘
        │                                ▼
        │            ┌───────────────────────────────────────────────┐
        │  receipts  │  RUNTIME KERNEL ✅ aios_contract_runner.py     │
        └────────────│  fail-closed authority → typed syscall →      │
                     │  backup → receipt → rollback                  │
                     └───────┬───────────────────────┬───────────────┘
                             │ adapter iface         │ dispatch packets
                             ▼                       ▼
        ┌────────────────────────────┐   ┌─────────────────────────────┐
        │ SUBSTRATE ✅                │   │ HIVEMIND ✅ (own repo)       │
        │ aios_adapters.py:          │   │ packet_runner, scheduler,   │
        │ claude/codex/gemini/ollama │   │ verification gates, receipts│
        │ + harness ReAct loop       │   │ fanout_scheduler            │
        │ (aios_harness.py, local)   │   └─────────────────────────────┘
        └────────────────────────────┘
                             │ every action/claim/cert/receipt appends
                             ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ AKASHIC ⚠ — THREE incarnations, no unified schema (open hole H2):      │
 │  (a) local work-lineage: memoryOS akashic_work_index.jsonl ✅           │
 │  (b) global behavioral: aios-akashic.cjw070690.workers.dev ✅ (CF)      │
 │  (c) witness claims-ledger: experiments/agi_witness (typed claims,     │
 │      poison, H⁰/H¹ structure) ✅ — the RICHEST schema of the three     │
 │ + guard: aios_akashic_guard (H⁰ poison flag) ✅ · verify ✅ (partial)   │
 │ Trusted-writer model ◻ (open hole H1)                                  │
 └────────────────────────────────────────────────────────────────────────┘
        ▲
        │ GenesisOS ✅ (critic/mutate/branch CLIs) — proposes/challenges only;
        │ ⚠ NOT wired into the head hot path (challenge-before-commit unused)
```

### Component contracts (the seams — each is an interface + invariants)

| seam | interface (typed) | invariants (DNA) | status |
|---|---|---|---|
| Service→Head | goal:str + authority grant (read-only default; `--allow-write/--allow-network`) | operator override; irreversible acts confirmed | ✅ |
| Head→Kernel | `ContractObject` {goal, scope, steps, capability route} | fail-closed authority; evil-plan reject pre-exec | ✅ |
| Kernel→Substrate | AdapterSpec `plan(goal)→steps`, `execute(step)→result` | absent CLI = named-exit offline, never crash | ✅ |
| Kernel→FS | typed syscall → backup → receipt | every mutation reversible (`.aios/runtime/backups/`) | ✅ |
| Head↔MemoryOS | context-pack request → evidence-linked pack; write = DRAFT only | draft-first; no silent accept; provenance chain | ✅ (pack quality ⚠) |
| Head↔CapabilityOS | recommend(task)→route; observe(run)→catalog update | recommendation-only, never executes | ✅ rec / ⚠ observe loop unmeasured |
| Head↔GenesisOS | challenge(plan)→objections before commit | proposes only, never selects final truth | ◻ (CLI exists, unwired) |
| anything→Akashic | append(typed claim/cert/receipt, evidence_refs, writer-sig) | append-only; provenance; writer admission per H1 | ⚠ (3 schemas, no sig) |
| CertGate→Kernel | `Certificate{type, subject, verdict, cost, evidence}` before action | cert cost accounted (verification tax visible) | ◻ |
| cert↔cert (composition) | coupling graph: Descent→GoEN action space; Descent→APEX abstain; APEX gaps→IRIS; Akashic proofs→prune APEX | exactly the witness C-arm wiring; only ships if witness fires | ◻ (prototype in witness) |

---

## 2. "AIOS is complete when ___" — falsifiable criteria

All six, jointly. Each is a test, not a vibe.

- **C1 — External-task closure.** A user on a FRESH install (no myworld checkout knowledge)
  runs `aios "<real goal outside AIOS development>"` and gets a completed, receipted,
  reversible result — demonstrated on ≥3 distinct external domains, each externally evaluable
  (PR merged / file-organization accepted / artifact used). Fail: any run needs operator
  spelunking into scripts/.
- **C2 — Verifiable execution chain.** For any run, `aios verify <run_id>` recomputes the
  hash-chain over (ContractObject → syscalls → receipts → Akashic appends) OFFLINE and passes;
  tampering any record makes it fail. (This is the minimum "verifiable-agent-execution ledger"
  bar the 2025-26 field is converging on; without it Akashic is a diary, not a ledger.)
- **C3 — Memory compounds, measurably.** Same task class run twice on one install: the second
  run cites accepted memory in its context pack AND improves on a logged metric (tokens, wall,
  or verified quality). The delta is recorded automatically, not asserted.
- **C4 — Witness resolved (either sign).** `experiments/agi_witness` reaches a NAMED exit:
  positive → cert layer enters the hot path per §1 CertGate and M1b is written; negative/
  taxonomy → cert layer ships as optional guard/lint tier (H⁰ guard pattern) and the AGI-layer
  claim is retired from all product docs. PARTIAL (today's state) is not an exit.
- **C5 — Named trust model for Akashic.** Writer admission is specified and enforced — even if
  the v1 answer is "single-operator, key-signed, local-first, global tier read-mostly." The
  circularity (who certifies the certifier) is either solved or explicitly scoped out in the
  shipping docs. Implicit trust = incomplete.
- **C6 — The shipping artifact is the product, not the fossil.** Install delivers ≤~20-file
  core (per kernel audit) + organs; contracts/ledger/sessions live in `_history/` or a separate
  repo; `aios doctor`-style readiness reports level L0–L6 and DNA-invariant lint passes.

---

## 3. Top-level dependency graph (partial order for M4)

```
 [D0] Witness completion (R1 A/B/C + R2–R6 + verdict)          ← RUNNING NOW (runs.jsonl has
   │        (blocks nothing else; gates D3b, M1b)                 C-ablate data; REPORT still PARTIAL)
   │
 [D1] Akashic unification ──────────────┐   (independent of D0: pick ONE schema — start from the
   │   3 schemas → 1 typed append API   │    witness claims-ledger schema, it is the richest —
   │   + hash-chain + local/global tier │    fold (a) work-index and (b) CF worker under it)
   ▼                                    │
 [D2] Trust model v1 (writer-sig,      │
   │   admission policy, verify CLI     │
   │   → C2, C5)                        │
   │                                    │
 [D3a] Cert interface extraction        │  (unconditional, thin: certs/*.py → aios_certs lib
   │    Certificate type + cost         │   with the Certificate type from §1; NO composition
   │    accounting; guard/lint tier     │   claim yet — usable as guards regardless of D0)
   │                                    │
 [D3b] Composition hot-path (ONLY if D0 fires) — CertGate in kernel, coupling graph, M1b spec
   │
 [D4] Service hardening (parallel to all above; depends only on existing kernel)
   │    install/onboard UX · packaged wheel · doctor/readiness · fossil archival (→ C1, C6)
   │
 [D5] Memory-compounding proof (needs D4 stable install; → C3)
   │    + CapabilityOS observation-loop measurement + GenesisOS challenge wiring (the two ⚠ seams)
   ▼
 [D6] External-domain campaign: 3 real outside tasks end-to-end (→ C1 final; the completion gate)
```

Parallel lanes: {D0}, {D1→D2}, {D3a}, {D4→D5} can all run concurrently.
D6 is last and is the only item that closes completion. D3b and M1b are conditional branches.

---

## 4. Atlas index — critique and corrected map set

Critique of the proposed M0–M4:

- **M1 as ordered is premature.** Formalizing the composition in ACT (Poly/sheaves/optics)
  BEFORE the witness verdict is theory-theater — the panel already warned "taxonomy
  masquerading as unification." Split it: a thin unconditional interface spec now; the
  composition law only after the witness fires.
- **M3 under-scopes trust.** The trusted-writer problem is the load-bearing hole (panel 2c),
  not a sub-bullet. M3 must be "Akashic Commons **& Trust**" and own D1+D2 wholly, including
  the 3-incarnation unification, key/signature scheme, and the honest scope-out if v1 stays
  single-operator.
- **One map is missing entirely:** nothing in M0–M4 measures the NORTH-STAR claim itself —
  behavioral memory compounding across runs (C3) and whether CapabilityOS observations actually
  improve routing. Without it, "memory layer for AI agents" is asserted, never shown.
- **M4 must own deprecation.** The fossil archival (kernel audit's Keep/Archive/Delete) is
  executable work with dependencies; it belongs in the roadmap as first-class items, or C6
  never closes.
- The M5+ per-OS specs stay folded into M0/M4 (confirmed: the sibling repos are healthy; their
  gaps are seam-level — GenesisOS wiring, CapabilityOS observation loop — not per-OS rewrites).

**Corrected map set (Claude fans out one Fable/agent per map):**

| id | map | scope | gate |
|---|---|---|---|
| M0 | Master Completion Map | this file | done |
| M1a | Certificate Interface Spec | `Certificate` type, cost accounting, guard/lint tier, extraction plan for `experiments/agi_witness/certs/*` → library | none (unconditional) |
| M1b | Composition Law (ACT: Poly + sheaves + optics; coupling graph as a formal object) | ONLY the coupled wiring proven by the witness | **conditional on D0 positive** |
| M2 | Substrate & Service Map | install/onboard/doctor UX, packaged core, provider adapters, MCP + chat surface, permission model | none |
| M3 | Akashic Commons & Trust Map | schema unification (3→1), hash-chain + `aios verify`, writer admission/signatures, H⁰ guard integration, local/global tiers | none |
| M4 | Roadmap / Gap / Deprecation Map | D0–D6 expanded to work items with owners; fossil archival plan; what Claude subagents build post-Fable | after M1a–M3 drafted |
| M5 | Memory-Compounding Evaluation Map | C3 protocol, CapabilityOS observation-loop metric, GenesisOS challenge-wiring test | none |

---

## 5. Open holes (named as holes; do not paper over)

- **H1 — Trusted writer / circular certification.** Who may write to Akashic; who certifies
  the certifier. `aios guard` (H⁰ poison flag) is a partial, cheap answer only. v1 resolution
  candidate: single-operator key-signed writes + read-mostly global tier — honest but not the
  open-population answer the AGI thesis needs.
- **H2 — Three Akashics.** Work-index, CF worker, witness claims-ledger share a name, not a
  schema. Until D1, "the shared ledger" is a slogan.
- **H3 — Witness pending.** As of this writing REPORT.md = PARTIAL (A/B/C R1 medians absent;
  ablation runs including C-ablate-writeback present in runs.jsonl). The entire cert-layer
  position in §1 is UNDECIDED until the named exit. Both collapse modes remain live:
  verification tax and monolith absorption (panel 2b).
- **H4 — No external user.** C1 has zero completed instances (outside-domain proof from the
  kernel audit was never closed with an externally-evaluated task).
- **H5 — Compounding unmeasured.** The north-star claim (memory across runs/models makes agents
  better) has no measurement anywhere in the tree. M5 exists because of this hole.
- **H6 — Fossil contamination.** A fresh clone still receives 218 contracts + governance
  corpus; the install is the developers' fossil record, not a product start-state.
- **H7 — Unwired organs.** GenesisOS challenge and CapabilityOS observation write-back exist
  as CLIs but the head does not exercise them; the "organism" is partially innervated.

---

## 6. Frontier position (honest, one paragraph)

AIOS is converging with a live 2025-26 field on both flanks, and should say so: (i)
**verifiable / attested agent execution** — agent trust registries, signed action logs,
transparency-log-style (Merkle/CT) receipts for autonomous agents — is exactly the C2 bar;
Akashic's differentiator is not the ledger mechanics (prior art: Certificate Transparency /
Trillian, W3C VC/DID, CRDT substrates — per the panel) but the LOCAL-FIRST, single-user
compounding organism on top of it; (ii) **applied category theory as agent-composition
language** — polynomial functors (Poly), sheaf consistency (Hansen–Ghrist line), optics /
categorical cybernetics — is the right formal home for M1b IF AND ONLY IF the witness proves
there is a composition worth formalizing. Claims about specific current SOTA in either field
must pass the freshness gate (search before citing) — this paragraph names the fields, not
their leaders. The honest external claim until D0 resolves stays: **negative-with-structure,
plus a working governed local head** — never "an AGI architecture."
