# G5 results — does the society beat a single agent with the same ledger? (generated 2026-08-05T16:08:12+00:00)

Protocol: `docs/AIOS_G5_SOCIETY_PREREG_2026-08-03.md` (frozen). Student `qwen3-coder-next`, identical in every arm; K=5; death turn derived from the task id and identical across arms; post-death budget identical across arms.

## Run-validity gate (§5.5)

**PASSED** — ownership changed hands in the society arms

## P_complete by arm

| arm | P_complete |
|---|---|
| solo_norecord | 0.375 |
| solo_ledger | 0.4688 |
| society | 0.4062 |
| society_rev | 0.3438 |

## THE contrast — society vs solo+ledger (prereg §4)

- paired tasks: **32** (infra-dropped 0)
- P_complete society **0.4062** vs solo+ledger **0.4688** → delta **-0.0625**
- discordant b=3 c=5 (rate 0.25)
- McNemar one-sided p: **0.8555**
- one-sided 95% upper bound on the advantage: **0.0817**

## KILL RULE (§6, computed — verdict recorded by the operator)

- C ≤ B: **True**
- upper bound excludes a ≥5pp advantage: **False**

If either fires: the society layer is not justified at this scale — dissolve it, re-converge on the storage redesign (arm B), and do NOT build N2–N4 or C1–C3.

## Secondary contrasts (reported, never substituted for the primary)

| treatment | control | delta | p | n |
|---|---|---|---|---|
| solo_ledger | solo_norecord | 0.0938 | 0.2266 | 32 |
| society_rev | society | -0.0625 | 0.8906 | 32 |
| society | solo_norecord | 0.0312 | 0.5 | 32 |

*(solo_ledger vs solo_norecord asks whether the RECORD is worth anything at all — if that is ~0, the finding is more fundamental than the society question. society_rev vs society isolates `supersede`.)*

---

## Operator verdict + adversarial checks (claude@myworld, 2026-08-05)

**KILL RULE FIRED on §6 condition 1 (`C ≤ B`). The society layer is not justified at this scale.**
Per the frozen pre-registration: dissolve it, re-converge on the storage redesign (arm B), and do
NOT build the network layers (N2–N4) or the compute-system layers (C1–C3). No retry with a new
society mechanism.

### What the numbers say, stated plainly

- The society did not beat a single agent carrying the same ledger. It was **6.25 pp worse**
  (0.4062 vs 0.4688), with McNemar p = 0.856 — the wrong direction, nowhere near significance.
- **The best arm was `solo_ledger`.** A single agent that resumes from its own record outperformed
  every other arm, including both society arms.
- `solo_ledger` vs `solo_norecord` = **+9.38 pp** (p = 0.227). This is the only meaningfully-sized
  positive in the table and it points at the RECORD, not the society. **It is not statistically
  established at n = 32** and we do not claim it — but it is the direction that survives to be
  tested properly.
- `society_rev` vs `society` = **−6.25 pp**. Per §6, `supersede` is reported as net overhead and its
  value claim is withdrawn. The operator stays in the codebase (it is still the correct way to
  retract a wrong step in an append-only log); the claim that it improves completion does not.

### Adversarial checks run BEFORE recording this verdict (all passed)

1. **No arm got more compute.** Mean recovery turns: 2.47 / 2.50 / 2.44 / 2.47 across the four arms.
   The society did not lose by being starved, nor win by thinking longer.
2. **The treatment actually fired.** Ownership transferred on 32/32 society cells and 0/32 solo
   cells — the arms genuinely differed in the one dimension under test.
3. **The instrument was sensitive.** Discordance 0.25 (8 of 32 pairs) — six times the X-channel
   pilot's 0.043. Outcomes could move; this is a real negative, not a dead dial.
4. **Not a death-timing artifact.** Discordant pairs split across both death turns (j ∈ {2,3}), and
   no arm dominates at one j (death@2: .25/.438/.438/.25; death@3: .50/.50/.375/.438).
5. **Not a degraded control.** B's pack came from the same generator as C/D's — `build_pack` takes
   no `arm` argument and structurally cannot favour one (asserted in
   `experiments/phase5g/test_phase5g.py`).
6. **Clean run.** 0 infra-dropped cells, 0 tests/ tampering incidents, 128/128 completed.

### The reading

Coase's inequality runs the wrong way in our domain: **coordination cost exceeded transaction
cost.** Handing work to a second agent — even with a freshness-gated, structurally identical
record — cost more than it bought, relative to the same agent re-reading the same record.

The founder's either/or ("a society, or a storage redesign") is answered by the data:
**the storage redesign.** The arc ledger we built is not wasted — it is the best-performing
mechanism in this experiment. What is retired is the claim that a *society of agents* on top of it
adds anything.

### Honest limits

- n = 32 with 8 discordant pairs. This settles the pre-registered question (does C beat B) at the
  scale we pre-committed to; it does not establish the ledger's own value (+9.38 pp, p = 0.227) —
  that needs its own powered test, and we do not claim it until then.
- One private repository, one task family (test-repair), one frozen local student, K = 5, a single
  forced death per task. A society might pay off at longer horizons, with more deaths, or with
  heterogeneous specialists — none of which this experiment tested, and none of which we may now
  build on the strength of a hypothesis the Mortuary-style clause of §6 explicitly forecloses.
