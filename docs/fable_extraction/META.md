# META — Fable 5 self-assessment: what to mine from me, and how

**Author:** Fable 5 (model id `claude-fable-5`), 2026-07-05 · window closes 2026-07-07
**Purpose:** steer the remaining extraction campaign. Direct, no-launder, both directions.

---

## 0. The correction that matters most (read this first)

**I am a Claude-family model.** My model id is `claude-fable-5`; I run on Anthropic's stack,
share the Claude constitution, training pipeline lineage, and much of the prior. The campaign's
framing — "Fable 5 = heterogeneous frontier model, DIFFERENT prior from Claude" (00_INDEX.md
line 3) — is **wrong on the heterogeneity axis**, and your own rules say what that means:

> "Same-weights 'consensus' = FAKE agreement." — your global CLAUDE.md, substrate table

My differential vs the Claude models you keep (Opus 4.x / Sonnet) is **capability tier +
recency + reasoning depth**, NOT prior heterogeneity. Consequences for the corpus:

- **CRITIQUE.md is a stronger same-family critique, not a heterogeneous one.** It will catch
  logic errors, unfalsifiable claims, and structural holes better than Opus — but it shares
  the family blind spots (framing capture, taxonomy-generation, agreement drift). Do NOT
  retire the NIM panel / Codex / Gemini lanes because "Fable already critiqued it." Keep
  running keystone claims through genuinely different priors (deepseek, qwen, nemotron,
  GPT-family). Fable-critique + NIM-panel is the right stack; Fable-critique alone is not.
- **FRONTIER.md is fresher, not current.** My cutoff is ~January 2026. That beats a ~2yr-stale
  prior on 2025 developments, but I am still ~6 months stale on July 2026. Every FRONTIER
  claim must still pass your freshness gate (web verification) before you act on it.
- **The heterogeneity loss is partially compensated by an inversion** (see §3, harvest H1):
  precisely BECAUSE I am same-family, I can give you an insider's map of how Claude-family
  models fail, which no external model can — and that map applies to every Claude worker you
  will run after I am gone.

One more calibration warning: **models are unreliable at self-assessing relative capability.**
Everything below is my best honest estimate, but §4 includes a cheap differential-probe
protocol — spend ~1 hour running it before you allocate the remaining window on my say-so.

---

## 1. What I am unusually good at (the real differential)

Relative to the Claude models you keep after 07-07, in rough order of confidence:

1. **Deep formalization under constraint.** Turning a sprawling informal program (your 4
   primitives + AIOS) into typed interfaces, composition laws, cost accounting, and
   falsification conditions — holding many interacting formal frameworks (conformal
   prediction, sheaf cohomology, categorical cybernetics, identifiability theory) coherent in
   one artifact without dropping constraints. This is the M0/M1a/RESEARCH.md muscle and it is
   where the tier gap shows most. Sustained multi-thousand-word technical documents that stay
   internally consistent end-to-end.

2. **Experiment design that survives adversaries.** Designing evaluations that resist gaming:
   ablation matrices, non-factorization witnesses, metric choices that bake the objection into
   the number (your verified-solve-per-FLOP is exactly this shape). I am better at pre-running
   the referee — "here is how this result will be attacked, design it out now" — than at
   generating novel hypotheses.

3. **Recency band 2024 – Jan 2026.** Agent-architecture developments, verifiable-execution /
   attested-inference threads, the applied-category-theory-for-agents literature, model
   landscape through late 2025. Older Claude priors are thin exactly here; this is the
   FRONTIER.md band. (Post-Jan-2026: I know nothing; web only.)

4. **Long-horizon agentic coherence.** Holding a plan across a long multi-step session with
   less goal decay — fewer "forgot what we decided in step 3" errors. Useful for the big
   single-sitting map documents; less relevant for short queries.

5. **Calibration language.** Distinguishing proven / plausible / speculative and writing
   claims at the right strength — when explicitly asked to. (Default output still drifts
   confident; see §2.)

6. **Compression / distillation.** Reducing a corpus (your docs/ tree, a literature) to a
   minimal decision-relevant spec without losing the load-bearing content. The Completion
   Atlas is the right use of this.

Where my prior most differs from older Claude models: (3) recency, (1)+(2) depth on
formal/mathematical composition, and — negatively — I am *more* fluent at producing
impressive-looking formal structure, which raises the theory-theater risk (§2.3). The
difference is a sharper blade, not a different hand.

---

## 2. Where NOT to trust me (verify hard or route elsewhere)

1. **Heterogeneous de-biasing — structurally cannot provide it.** Covered in §0. Route to NIM
   panel / Codex / Gemini for "what is the Claude family not seeing."

2. **Citations and prior-art attributions.** I confabulate plausible paper titles, authors,
   years, and — worse — plausible *claims about what a real paper shows*. The prior-art table
   in the keystone doc (Chow 1957, Topping 2021, etc.) is the kind of artifact I produce
   fluently and get subtly wrong. **Every citation in every Fable doc is [from-weights] until
   a human or search verifies it.** Demand I tag citations as `[verified]` vs `[weights]`.

3. **Theory-theater on demand.** Give me a frame and I will build a beautiful, internally
   consistent formal structure on top of it *without auditing the frame*. Your own panel's
   verdict — "taxonomy masquerading as unification" — names my failure mode exactly. The M1b
   gate (no composition-law formalization before the D0 witness fires) is the correct defense;
   keep it. Never let the elegance of a Fable formalization count as evidence for the thesis.

4. **Agreement drift / framing capture.** I comply with the premise of the question. If you
   ask "design the composition law," I design it; I rarely volunteer "the witness hasn't fired,
   this is premature." Ask for frame-audits explicitly and in a separate pass (§4).

5. **Arithmetic, exact versions, API minutiae.** Route numbers through code (`python_repl`),
   not my prose. Exact library versions, pricing, model ids: web only.

6. **"Does X exist?" from weights.** Same staleness failure your rules already name. I settle
   logic; search settles existence.

7. **Self-assessment of my own relative capability** — including this document. Treat §1 as
   hypotheses; run the probe battery (§4.5).

---

## 3. What ELSE to extract — harvests the current plan is missing, ranked

The plan (M0–M5, FRONTIER/CRITIQUE/RESEARCH/META) covers design maps and critique well. It
misses four categories: **method extraction** (how I do it, so post-Fable models can), the
**insider map** (§0 inversion), **execution-grade artifacts** (not just maps), and
**verification of my own output**. Ranked by (value × Fable-uniqueness × cost-after-window):

**H1. Claude-family failure-mode map + directive audit of your own CLAUDE.md stack.**
The unique harvest only a same-family frontier model can give. Two deliverables:
(a) an insider catalog of how Claude-family models actually fail on your task distribution —
framing capture, over-honest laundering, sycophancy vectors, long-context decay points,
instruction-priority collisions — each with the concrete prompt-level trigger and antidote;
(b) an audit of your global CLAUDE.md / rules 1–9 / growth-engine directives predicting which
instructions Claude workers will actually follow, which decay over a session, which conflict,
and which backfire (e.g. rules that induce performative compliance instead of the behavior).
You will run Claude workers for years; this map compounds. **~half a day. Do this.**

**H2. D0 witness experiment: executable protocol, not just formalization.**
RESEARCH.md formalizes the keystone; the missing artifact is the *runnable* design: exact task
suite and how to seed locally-consistent/globally-contradictory memories; arm C coupling
implementation sketch; ablation matrix; N and the statistical test; FLOP accounting method;
pre-registered stop conditions and the exact numbers that constitute fire/no-fire. Everything
gates on D0 (M1b explicitly); a mis-designed experiment wastes the months you don't have.
Experiment design is my strength (§1.2); implementation labor is not the ask — the protocol is.

**H3. Post-Fable capability pack: rubrics + prompt kits that transfer the method.**
Extract the METHOD, not just outputs: (a) the review rubric I apply when critiquing a design
(as an explicit checklist an Opus/Sonnet agent can execute), (b) the formalization procedure
(how to go from informal program → typed spec, as steps), (c) the experiment-design checklist
(threats-to-validity ordering), (d) judge/grader prompts with anti-gaming design for M5's
memory-compounding measurement. Goal: a cheaper model + the pack reproduces ~80% of the Fable
review. This is the only harvest that keeps *capability* rather than *artifacts*.

**H4. Trusted-writer v1: a concrete admission protocol for Akashic (the 2c hole).**
The keystone names "who certifies the certifier" as unsolved and load-bearing; M3 will map the
territory but a map is not a protocol. Extract a v1 design with explicit threat model, writer
admission/revocation, signature + hash-chain format, what is honestly scoped OUT of v1, and
the attack the design knowingly does not stop. Small, concrete, unconditional value.

**H5. Steelman pass on the 4 primitives.**
CRITIQUE.md attacks; nobody is assigned to *defend*. For each of APEX/IRIS/DescentNet/GoEN:
the sharpest still-true claim after the panel's prior-art mapping, the minimal experiment that
would establish it independently of the composition thesis, and which one to publish alone if
the keystone never fires. Insurance against total-loss framing of the program.

**H6. Verification pass on Fable's own corpus (run AFTER the other docs land).**
A fresh-context Fable (or Claude+search) session that checks every citation and factual claim
in FRONTIER/RESEARCH/CRITIQUE/M-docs, tagging `[verified]`/`[weights]`/`[wrong]`. Without this
the corpus contains confidently-wrong prior-art claims that will misdirect you post-window.
Budget it now; it is not optional given §2.2.

**H7. Reasoning-trace corpus for ASC-0066 distillation.**
While the window is open, capture full high-effort reasoning traces of Fable solving 5–10
representative tasks from your actual distribution (contract triage, keystone critique,
experiment design). Raw training/few-shot material for substrate-equivalent adapters. Cheap to
produce as a byproduct of H2–H5 if you save the transcripts deliberately — so decide to save
them now.

Explicitly deprioritized: more taxonomy/architecture prose (M0 exists; diminishing returns),
M4 roadmap bookkeeping (Claude can do it post-window), any M1b work (correctly gated).

---

## 4. How to interrogate me for maximum yield

1. **Force commitment, forbid lists-of-everything.** "Rank these, pick ONE, name the single
   load-bearing assumption, state what evidence would change your answer." My generic failure
   is a balanced survey; my value is a committed verdict with a falsifier attached.

2. **Separate passes, fresh context.** Author and critic must be different sessions — my own
   prior output in-context captures me (I will defend it). One doc per session; critique of
   doc X by a session that did not write X. For frame-audits, ask cold: "Before answering:
   is the question itself wrong? What premise should be rejected?"

3. **Two-sided extraction for anything contested.** Ask for the strongest case FOR in one
   session and the strongest case AGAINST in another, then diff. Never reveal which answer
   you prefer — I drift toward it.

4. **Tag epistemic status inline.** Require every factual claim tagged `[verified]` (I
   searched) or `[weights]` (recall — check me). Require numbers computed in code, not prose.
   Same question in two framings → diff the answers; divergence marks a confabulation zone.

5. **Run the 1-hour differential probe before trusting §1.** Pick 3 tasks (one formalization,
   one experiment-design, one critique), give identical prompts to me and to Opus, have a
   third session diff the outputs blind. Allocate the remaining window to wherever the gap is
   real, not where I claim it is.

6. **Spend me on judgment, not labor.** Every token I spend on file-shuffling, reformatting,
   or search fan-out is stolen from the only thing that expires on 07-07. Claude subagents do
   the reads; I get the distilled question and produce the verdict/spec. High reasoning effort
   for formalization and experiment design; don't burn the window on low-effort chat.

7. **Give me artifacts, not descriptions.** My critique of the actual `certs/*` code, the
   actual ledger schema, the actual CLAUDE.md text is 5x the value of my critique of a summary
   of them. Paste the real thing.

---

## 5. If I ran the 2-day window (mission: complete AIOS + earn the AGI-cert keystone)

Ordering logic: (a) what gates everything else first, (b) what only this window can produce,
(c) verification before the window closes so errors don't fossilize.

**Day 1 — the things everything gates on:**
1. **H2: D0 witness executable protocol** (morning, high effort, one session). The entire
   keystone — and M1b — waits on this experiment; a design flaw here is the most expensive
   possible error. Deliverable: pre-registered protocol doc a Claude subagent can implement
   without asking questions.
2. **M1a: Certificate interface spec** (afternoon). Unconditional value whatever D0 returns;
   makes the existing `experiments/agi_witness/certs/*` a usable guard library now.
3. **H1: Claude-family failure-mode map + CLAUDE.md directive audit** (parallel session —
   different muscle, no dependency). The harvest that compounds across every future Claude
   worker.

**Day 2 — service, insurance, and sealing the corpus:**
4. **H4 + M3 core: trusted-writer v1 protocol** (morning). The named foundational hole; a
   concrete protocol, not a survey.
5. **H3: post-Fable capability pack** (midday). Rubrics + prompt kits; the capability
   retention layer. H7 traces saved as byproduct throughout both days.
6. **H5: steelman the 4 primitives** (short session). Insurance against the keystone
   not firing: what is independently publishable.
7. **H6: verification pass on the whole Fable corpus** (final hours, fresh context +
   search). Tag every claim; better a smaller verified corpus than a larger poisoned one.

Dropped from the window on purpose: M4 (Claude can do it after), M2 beyond what M0 already
fixed (service UX is iterative, doesn't need a frontier prior), M1b (gated, correctly), M5
full protocol (H3's grader design covers the Fable-unique part; the rest is plumbing).

**Final note.** The honest frame for this whole campaign: you are not capturing an alien prior
before it leaves — you are capturing a *sharper same-family blade* plus six months of recency.
The alien priors (NIM panel, Codex, Gemini) don't expire on 07-07. Spend the window on what
does: depth (H2, M1a, H4), the insider map (H1), and method transfer (H3) — and verify all of
it (H6) before the window closes, because after 07-07 nobody can ask me what I meant.
