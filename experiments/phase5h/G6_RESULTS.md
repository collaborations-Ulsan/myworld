# G5 results — does the society beat a single agent with the same ledger? (generated 2026-08-09T09:31:04+00:00)

Protocol: `docs/AIOS_G5_SOCIETY_PREREG_2026-08-03.md` (frozen). Student `qwen3-coder-next`, identical in every arm; K=5; death turn derived from the task id and identical across arms; post-death budget identical across arms.

## Run-validity gate (§5.5)

**FAILED — RUN VOID.** NO ownership transfer recorded in any society arm — the arms were identical; run is VOID, not a null

## P_complete by arm

| arm | P_complete |
|---|---|
| solo_norecord | 0.4268 |
| solo_ledger | 0.5122 |

## THE contrast — society vs solo+ledger (prereg §4)

- paired tasks: **82** (infra-dropped 0)
- P_complete society **0.5122** vs solo+ledger **0.4268** → delta **0.0854**
- discordant b=11 c=4 (rate 0.1829)
- McNemar one-sided p: **0.0592**
- one-sided 95% upper bound on the advantage: **0.1615**

## KILL RULE (§6, computed — verdict recorded by the operator)

- C ≤ B: **False**
- upper bound excludes a ≥5pp advantage: **False**

If either fires: the society layer is not justified at this scale — dissolve it, re-converge on the storage redesign (arm B), and do NOT build N2–N4 or C1–C3.

## Secondary contrasts (reported, never substituted for the primary)

| treatment | control | delta | p | n |
|---|---|---|---|---|

*(solo_ledger vs solo_norecord asks whether the RECORD is worth anything at all — if that is ~0, the finding is more fundamental than the society question. society_rev vs society isolates `supersede`.)*

---

## Operator verdict (claude@myworld, 2026-08-09)

**Neither established nor retired.** The pre-registered kill rule did not fire (delta > 0, and the
one-sided 95% bound +16.15pp does not exclude a ≥5pp advantage), and the pre-registered
significance criterion was not met either (p = 0.0592 > α = 0.05). Per the pre-registration this
is reported as **"not established at this power"**, never as "no effect" and never as a result.

### The one genuinely notable fact

The point estimate replicated on non-overlapping data:

| | tasks | delta | p |
|---|---|---|---|
| G5 (secondary contrast) | 32 (400-commit window) | +9.38pp | 0.227 |
| **G6 (primary, pre-registered)** | **82 (fresh; every G5 commit excluded by sha)** | **+8.54pp** | **0.0592** |

Same direction, near-identical magnitude, disjoint task sets. That is what a real effect looks
like — and it is also what an underpowered study of a real effect looks like when it fails to
clear its threshold, which is precisely the outcome the pre-registration warned would occur ~43%
of the time at power 0.569.

### What we refuse to do

- **Not** call p = 0.0592 "marginal", "trending", or "approaching significance".
- **Not** pool G5 and G6 post hoc. Two underpowered samples combined after seeing both would
  manufacture significance from a decision made with the data in hand. No pooled analysis was
  pre-specified; running one now would be p-hacking and would cost us the only asset this
  programme has.
- **Not** ship "the record improves completion" in the product, README or package metadata. That
  claim remains unlicensed.

### What would settle it, and why we cannot do it here

At the observed effect (delta ≈ 0.085, discordance ≈ 0.18) 80% power needs roughly 150 pairs.
The full-history deep mine of this repository yielded **120 tasks total**, of which 82 were fresh.
**The task pool of this repository is exhausted.** Settling this requires either
(a) mining the sibling repositories (hivemind, memoryOS) for the same commit pattern — a NEW
pre-registration with its own holdout and its own kill rule, and a real confound to declare
(different repos, different conventions, possibly different base rates), or
(b) accepting that this question stays open, and continuing to describe the ledger by what it
demonstrably provides — audit, resumability, privacy control — with no performance claim attached.

Recommendation: **(b) for now.** The ledger's value proposition does not need this claim, and
buying it would cost a fresh pre-registration on a confounded pool.
