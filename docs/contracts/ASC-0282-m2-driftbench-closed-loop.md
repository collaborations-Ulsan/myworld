---
contract_id: ASC-0282
status: accepted
goal: Execute masterplan M2 (AIOS-DriftBench-mini closed-loop keystone) under the hardened pre-registration, with real-dispatch shadow-mode as reserved by the masterplan
created: 2026-07-11
accepted: 2026-07-11T10:25:00+09:00
closed:
---

> Acceptance cross-check: deepseek-v4-pro (NIM) — VERDICT: ACCEPT, zero
> blocking objections, two non-blocking notes (shadow-mode scrub procedure
> detail; WP-D transition recording) to fold during WP-B. The customary peer
> codex@myworld timed out twice (exit 143, 420s/540s) — substrate gap
> recorded; a codex re-pass may be run when the service recovers.

# ASC-0282 — M2 DriftBench closed-loop keystone (+ real-dispatch shadow-mode)

Minimal execution record permitted by the contract freeze ("M2 기록용 최소
계약만", masterplan §4 kill list). The masterplan reserved this number:
"ASC-0282 (real-dispatch shadow-mode) 겸용" (§4 M2). Founder GO for the M2
push: 2026-07-11 ("마스터플랜이 납득가능한 평가지표인지 판단하고 쭉 밀어봐").

## 1. Canonical protocol

- Design: masterplan §5 (Codex adversarial design) + §5.5 (literature-adjusted
  2x2 + memory arm), `docs/AIOS_REDEFINITION_AGI_MASTERPLAN_2026-07-10.md`.
- Hardened specification (statistics, ablation-replay gate, owner-bias
  two-stage structure, cost accounting, grader isolation):
  `descentnet/docs/DESCENTNET_M2_DRIFTBENCH_PREREG_2026-07-10.md` v1 + v1.1
  + v1.2 (v1.2 folds `myworld/docs/AIOS_M2_DESIGN_ADDENDUM_2026-07-11.md` —
  corrupted-oracle arm, model-family swap, MISSPECIFIED probe, ABSTAIN-AUC
  secondary, SLM-delta untyped baseline arm with the non-factorization
  witness, evaluator blinding). The audit chain is binding: Stage-1 (24
  instances, paired wins >= 17/24, tie != win) is the INTERNAL completion
  judge; Stage-2 (>= 100 hidden instances authored by non-team substrates)
  is required before any external headline claim.

## 2. Scope

- repos: myworld (harness, `aios_turn_loop` gate switches per M1, instance
  fixtures, grader container), descentnet (organ interface + ablation-replay
  instrumentation, receipts), hivemind (run verification only).
- allowed_files: `myworld/scripts/m2_driftbench/**` (new), `myworld/docs/`
  (this contract + receipts index), `descentnet/descentnet/**` (organ on/off
  instrumentation), `descentnet/run_artifacts/descentnet/**` (receipts).
- forbidden_files: `memoryOS/**` raw records (read-only via existing API),
  any `_from_desktop/`, `dain/`, `minyoung/` path, grader secrets into agent-
  visible trees, edits to masterplan §5 thresholds.

## 3. Per-OS responsibility

- myworld: harness, fixtures, freeze/seal procedure, budget metering.
- memoryOS: read-only Akashic access for the memory-integrity organ (no
  auto-accept; draft packets only).
- CapabilityOS: routing recommendation for weak-agent model choice (frontier
  check before selection; recommendation-only).
- GenesisOS: pre-freeze assumption critique of instance templates (advisory).
- hivemind: execution verification of run receipts before closeout.
- descentnet: memory-integrity organ + ablation-replay hooks; the DescentNet
  paper claim attaches only to the organ-credit gate (prereg v1.1 §C).

## 4. Verification gate (closeout requires all)

1. Harness freeze receipt: hash-sealed harness + grader container, seeds
   {11,12,13}, mutation coverage rule satisfied (8 drift types x >= 2), A2
   affordance parity audit by a non-team substrate.
2. Stage-1 run receipts: 24 instances x arms, token-equivalent budget
   accounting per instance, static/mutating fixture isolation evidence.
3. Primary analysis receipt: exact binomial on paired wins (tie != win),
   template-clustered secondary, ablation-replay organ-credit table.
4. Named exit recorded verbatim (EARN / kill / demote per masterplan §5.5
   and prereg v1.1 §A power reading) — honest negative is a valid closeout.
5. Shadow-mode rider: if dacon real-dispatch data is used, privacy scrub
   receipt precedes any fixture ingestion.

## 5. Stop conditions

- Any post-freeze edit to thresholds, seeds, mutation distribution, or cost
  denominator → stop, void, re-register (append-only).
- Grader side-channel detected (agent observes grader state) → stop, reseal.
- Budget overrun > 2x plan (>~300 sequential hours) without founder ping.
- Smoke-gate results used to tune templates/seeds → protocol violation, stop.

## 6. Receipts

- `descentnet/run_artifacts/descentnet/m2_*` (JSON, run-logging contract per
  paper O16) + `myworld` ledger entry at accepted and at closeout only.

## 7. Work Packets

- WP-A (myworld): M1 gate switches `gate=off|llm-judge|organs` wired into
  `aios_turn_loop` with clean per-organ disable flags (prereg v1.1 §C needs
  organ-level instrumentation from day one). Owner: claude@myworld or
  codex@myworld.
- WP-B (myworld+descentnet): Stage-1 harness — 8 templates (6 mutating / 2
  static), instance generator seeded by the 8-type drift taxonomy, hidden
  functional grader in an isolated process, token metering, trace capture,
  smoke on disjoint throwaway templates, then freeze+seal.
- WP-C (descentnet): ablation-replay engine over winning traces + organ-
  credit analysis; DescentNet paper integration hangs on this packet.
- WP-D (post-Stage-1, conditional PASS): Stage-2 hidden set (>= 100
  instances) commissioned from non-team substrates (codex/NIM/third party),
  evaluator-controlled; paper-primary analysis.

## AIOS Role Evidence

DNA citation (per `docs/contracts/README.md` DNA Citation Requirement; this
contract crosses into a child repo and introduces execution behavior — cites
`docs/AIOS_DNA.md`): **Invariant 1 (Decide before acting)** — this contract
precedes all harness code; **Invariant 3 (No record destroyed)** — the prereg
is append-only versioned (v1 -> v1.1 -> v1.2) and receipts are never edited;
**Invariant 4 (Every loop has a named exit)** — §5 stop conditions and the
pre-registered EARN/kill/demote exits; **Invariant 7 (Privacy boundary)** —
§2 forbidden_files and the shadow-mode scrub rider in §4.5.

Draft-first: organ outputs remain recommendation-only draft packets.
Provenance: every receipt cites the prereg version and harness hash. Operator
override and founder override remain possible at every gate.

### 5-Persona Use

- Builder: WP-A/B implementation. Skeptic: the v1.1 adversarial-lane gaps
  are the skeptic's checklist. Auditor: verification gate §4. Librarian:
  receipts indexed in ledger + memory. Founder: GO/HOLD at Stage-1 exit and
  before any Stage-2 external claim.
