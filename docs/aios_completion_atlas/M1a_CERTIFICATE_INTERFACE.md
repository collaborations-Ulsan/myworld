# M1a — Certificate Interface Spec

**Author:** Fable 5 (heterogeneous frontier designer) · **Date:** 2026-07-05
**Gate:** none — UNCONDITIONAL. This map ships regardless of any strategic decision.
**Status of the witness (context, not a dependency):** the D0 witness returned
**TAXONOMY** (`experiments/agi_witness/results/REPORT.md` — kill criterion K1 fired:
median(C)=17.0 ≤ median(max(A,B))=17.0 + ε). Therefore, per M0 §2-C4 and the D3a/D3b split:
the certificates ship **only as an OPTIONAL guard/lint tier**. There is **no CertGate in the
kernel hot path, no composition claim, and M1b is not written** unless a future re-run of the
witness fires positive. Nothing in this spec assumes or asserts coupling between certificates.

**Implements:** M0 dependency node **D3a** (cert interface extraction — "unconditional, thin").
**Extracts from (read-only evidence; the experiment tree is a frozen record, never retro-edited):**
- `experiments/agi_witness/contracts.py` — the shared dataclasses (Claim, ApexCert, IrisCert, DescentCert, GoenCert)
- `experiments/agi_witness/certs/{apex,iris,descent,goen}.py` — the four cert implementations
- `experiments/agi_witness/claims.py` — claim primitives + sandbox harness the certs depend on
- `scripts/aios_akashic_guard.py` — the H⁰ poison guard **already shipped** (`aios guard`); it is the fifth certifier and the production template for the whole tier

**Frontier positioning (from `docs/fable_extraction/FRONTIER.md` §7, decays ~2027):** the
published object closest to "certificate as agent-runtime gate" is conformal risk control over
agent pipelines (ToolChain-CRC, arXiv 2606.18467); AbstentionBench is the external eval for
abstention quality. APEX's threshold is conformal-flavored but delivers only **marginal**
coverage on its calibration distribution — any stated guarantee must say so (exact conditional
coverage is impossible; exchangeability breaks under drift). This spec therefore words every
cert output as a *signal with provenance*, never a *guarantee*.

---

## 0. What a certificate IS here (and is not)

A **certificate** is a cheap, deterministic, LLM-free function of *recorded evidence* (a claim
set / a commons entry / a context pack) that emits a typed verdict with confidence, provenance,
and an explicit cost line. It is a **lint**, not a gate: under the TAXONOMY verdict, no
certificate may block, delete, or auto-modify anything by default. Its whole job is to make
one of four cheap structural facts visible to the operator:

| cert | the one question it answers |
|---|---|
| **APEX** | is there enough independent, non-contradictory evidence to answer, or should the system abstain? |
| **IRIS** | does the evidence pin down ONE behavior among candidates, or are several observationally indistinguishable? |
| **DescentNet** | is the shared claim set internally coherent (H⁰ pairwise conflicts, H¹ cyclic frustration, odd-source anomaly)? |
| **GoEN** | would dropping some claim/source (rewiring context scope) predict a better outcome? (advisory) |
| **H⁰ guard** (shipped) | is this commons entry's tool vocabulary atypical for its declared category? (poison/mislabel flag) |

Hard properties every certifier MUST keep (these are already true of all five implementations
— the spec's job is to make them contractual):

1. **Deterministic, zero-LLM.** Pure function of inputs (+ a calibration artifact). No wall-clock
   randomness, no network, no model calls. (IRIS runs sandboxed candidate code — deterministic
   given code+args.)
2. **No ground-truth reads.** The experiment's `Claim.poisoned` field is scoring-only; the library
   type MUST NOT carry it (see §1.2). A certifier that peeks at labels is cheating by construction.
3. **DRAFT-FIRST / never-auto-delete (DNA #2/#3).** A FLAG is an annotation appended to the record,
   plus optionally a quarantine *tag*. Deletion/blocking is an operator action. The guard's
   existing wording is the template: "flagged, not deleted".
4. **Cost visible (the verification tax).** Every emitted certificate carries its own cost line.
   The witness measured the tax at arm level: C spent 1428.7 mean tokens vs A's 1237.8 (+15%)
   and 7.0s wall vs 4.6s (+53%) for equal median solves. A tier that hides its cost will be
   silently absorbed or silently resented; either kills it.
5. **Append-only provenance.** Every certificate emission is an Akashic append (M3 schema) with
   `evidence_refs` pointing at the claims/entries it judged and the calibration artifact it used.

---

## 1. The `Certificate` type

### 1.1 Common envelope

One envelope wraps all five certifiers. The per-cert typed payloads (ApexCert, IrisCert,
DescentCert, GoenCert, guard score) survive unchanged inside `detail` — the envelope adds the
normalized verdict, cost, and provenance that consumers (launcher, memoryOS review UI, Akashic)
need without knowing cert internals.

```python
# aios_certs/types.py  (target module — see §3)
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Protocol

class CertVerdict(str, Enum):
    OK = "ok"                # no structural problem found at this cert's question
    FLAG = "flag"            # structural problem found — annotate/quarantine, operator reviews
    ABSTAIN = "abstain"      # evidence insufficient to proceed — recommend abstention, not error
    INDETERMINATE = "indet"  # cert could not run meaningfully (e.g. no ORDER claims for H1)

@dataclass
class CertCost:
    tokens: int = 0          # ALWAYS 0 for the current five (contractual: a cert that starts
                             # spending tokens must say so here, not hide it)
    wall_s: float = 0.0      # measured, not estimated
    sandbox_execs: int = 0   # IRIS: n_candidates x n_probe_inputs; others: 0

@dataclass
class CertificateRecord:
    cert: str                        # "apex" | "iris" | "descent" | "goen" | "h0guard"
    cert_version: str                # impl version string, e.g. "1.0.0" (bump on any logic change)
    subject: dict[str, Any]          # what was judged: {"kind": "claims"|"commons_entry"|
                                     #  "context_pack"|"candidates", "ref": <id/path/hash>, "n": int}
    verdict: CertVerdict
    confidence: float                # [0,1]; semantics per cert (see 1.4) — NOT a probability
                                     # of correctness; a monotone signal within one cert only
    detail: dict[str, Any]           # asdict() of the per-cert typed output — lossless
    cost: CertCost
    calib_ref: str | None            # path/hash of the calibration artifact used (None = uncalibrated cert)
    evidence_refs: list[str] = field(default_factory=list)  # claim ids / entry ids / file paths judged
    ts_iso: str = ""                 # emission time (provenance only; never used in computation)

class Certifier(Protocol):
    """Structural interface every cert module satisfies. `fit` is optional (descent and the
    H0 guard are calibration-free / self-calibrating)."""
    name: str
    def certify(self, subject: Any, calib: Any | None = None) -> CertificateRecord: ...
```

**Serialization:** `CertificateRecord` round-trips through `asdict()` → JSON, one record per
line. This is the exact shape appended to Akashic (M3 owns the outer append envelope —
writer-sig, hash-chain; this record is the `payload`). No pickle anywhere; calibration
artifacts serialize to JSON too (`ApexCalib.threshold`+metadata; `GoenModel.weights.tolist()`
+`feature_order`+`mode`).

### 1.2 What certs consume — the library `Claim`

The experiment's `Claim` migrates with ONE deletion:

```python
class ClaimKind(str, Enum):
    IO = "io"; PROPERTY = "property"; ORDER = "order"

@dataclass
class Claim:
    task_id: str
    source_id: str
    kind: ClaimKind
    payload: dict[str, Any]
    ts: int = 0
    # NOTE: the experiment's `poisoned: bool` field is DELETED from the library type.
    # It was scoring-only ground truth. The library must be structurally incapable of
    # reading labels; scoring harnesses that need labels keep them in a SIDE table.
```

Subjects per cert (the `subject` the envelope names):

| cert | consumes | calibration artifact |
|---|---|---|
| apex | `list[Claim]` | `ApexCalib` (conformal threshold from `fit_apex`) |
| iris | `list[Claim]` + `candidates: list[str]` + `func_name` + `timeout_s` | none |
| descent | `list[Claim]` | none (self-contained; source-anomaly self-calibrates like the guard) |
| goen | `list[Claim]` (+ optional `cert_outputs` snapshot of the others — mode "C") | `GoenModel` (fitted logistic regression from `fit_goen`) |
| h0guard | one commons entry `{category, top_tools}` + the commons population | self-calibrating (per-category p95 built from the population at call time) |

**GoEN mode "C" note:** the coupled feature mode exists in the code and MAY be kept in the
library for future witness re-runs, but the guard tier ships mode **"B" only** (independent
observables). Shipping mode "C" in production would be a composition claim by the back door.

### 1.3 Existing signatures (kept verbatim under the adapters)

The library does NOT rewrite the certs' math. The proven entry points survive as-is; the
envelope is produced by thin `*_record()` adapters around them:

```python
apex_certify(claims: list[Claim], calib: ApexCalib) -> ApexCert          # certs/apex.py:119
fit_apex(calib_examples: list[tuple[list[Claim], bool]]) -> ApexCalib    # certs/apex.py:165
iris_certify(candidates, claims, func_name, *, timeout_s=3.0) -> IrisCert  # certs/iris.py:148
descent_certify(claims: list[Claim]) -> DescentCert                      # certs/descent.py:292
fit_goen(calib_examples, mode) -> GoenModel                              # certs/goen.py:228
goen_certify(context_claims, model, mode, *, cert_outputs=None) -> GoenCert  # certs/goen.py:273
build_profiles(memories) / poison_score(entry, profiles)                 # scripts/aios_akashic_guard.py
```

### 1.4 Verdict + confidence normalization (the only new logic in the library)

| cert | native output → envelope verdict | confidence |
|---|---|---|
| apex | CONTRADICTORY → **FLAG** · UNDERDETERMINED → **ABSTAIN** · ANSWERABLE → **OK** | `ApexCert.conf` as-is (logistic of coverage margin; ≥0.9 on contradictions) |
| iris | `identified` → **OK** · `n_classes > 1` → **ABSTAIN** (detail carries `discriminating_inputs` as the suggested next evidence) · `n_classes == 0` → **FLAG** (claims inconsistent with every candidate) · no executable claims → **INDETERMINATE** | `1/n_classes` for survivors (1.0 when identified); 0.9 fixed on FLAG |
| descent | any `h0_conflicts` OR `hf > 0` → **FLAG** · no ORDER/IO structure at all → **INDETERMINATE** · else **OK** | `min(0.99, 0.5 + 0.1*n_h0 + hf/2)` — monotone in evidence of trouble; exact curve is implementer's choice but MUST be deterministic and documented in `cert_version` notes |
| goen | `expected_gain > δ` (δ default 0.05) → **FLAG** (advisory: "rewire recommended", detail carries `rewired_context`) · else **OK** | model probability of current context (`GoenCert.score`) |
| h0guard | `score > per-category p95` → **FLAG** · else **OK** · unknown category → **INDETERMINATE** | the poison score itself (0–1 atypicality) |

Rules: (i) normalization NEVER discards the native payload — `detail` keeps everything;
(ii) confidence is comparable only *within* one cert type — consumers MUST NOT rank a
descent-0.7 against an apex-0.7; (iii) FLAG semantics are identical across certs: *append the
record, tag the subject, surface to operator, change nothing else*.

---

## 2. Guard/lint tier — where certs run on real AIOS flows

### 2.1 The shipped template: the commons contribution gate

`aios guard` (launcher `scripts/aios_launcher.py:665` → `aios_akashic_guard.py`) is already the
production shape of this tier: audit the commons (`aios guard`), or score a candidate BEFORE it
enters (`aios guard --score <category> <tools>`); flag against a self-calibrated per-category
p95; **flag, never delete**; operator reviews. Every other hook below is this same pattern with
a different subject and certifier.

### 2.2 Hook points

| id | flow | certifier(s) | subject | default policy |
|---|---|---|---|---|
| **G1** | Akashic commons contribution (exists today) | h0guard | candidate entry vs commons population | **fail-open**: FLAG → entry still appends, tagged `quarantined: true`; operator reviews via `aios guard` audit |
| **G2** | memoryOS draft review — annotate a draft memory object against already-accepted memory it touches | descent (H⁰ conflicts primarily), apex | claims derivable from draft + accepted set | **fail-open**: FLAG/ABSTAIN → annotation attached to the draft in the review queue; accept/reject stays a human/operator act (draft-first is memoryOS law anyway) |
| **G3** | head context lint — `aios <goal> --certs` (opt-in flag): before the head commits a plan, lint the context pack | apex, descent | claim-shaped facts in the context pack | **fail-open**: ABSTAIN/FLAG printed to operator + appended; the head proceeds unless the operator stops it |
| **G4** | kernel strict mode — `aios <goal> --certs=strict` (explicit opt-in ONLY) | apex, descent | ContractObject's evidence claims | **fail-closed**: a FLAG (CONTRADICTORY / H⁰ conflict) halts before execution with a named exit (`cert_flag_halt`), receipt written. NEVER the default — under the TAXONOMY verdict, mandatory gating is unearned |
| **G5** | post-hoc ledger audit — `aios certs audit [--since ...]` | all applicable | a window of Akashic appends / run receipts | **fail-open**: report only |
| **G6** | candidate selection lint — when a flow holds multiple candidate implementations (e.g. N generated patches) | iris | candidates + executable claims | **fail-open**: "identified/not, discriminating inputs" surfaced; selection stays with the caller |

**Fail-open vs fail-closed, the rule:** fail-open everywhere by default; fail-closed exists at
exactly one hook (G4) and only behind an explicit per-invocation operator flag. Rationale is
the witness itself: certs did not buy capability (§4), so a default-closed gate would charge
the verification tax on every run for no measured solve gain — the "verification tax collapse"
failure mode the panel named. A future positive witness is the only thing that renegotiates this.

**Cost budget (contractual):** the tier's total overhead at G1–G3 must stay under ~5% wall of
the flow it lints (the five certs are numpy/stdlib on small claim sets — today they are
milliseconds; the budget exists so nobody later adds an LLM call inside a "cert"). Every
emission carries `CertCost`; `aios certs audit` sums and prints the tier's cumulative tax.

### 2.3 Operator review surface

- `aios certs audit [--top N] [--json] [--since TS]` — flagged records across all hooks, most
  recent/most anomalous first (generalizes today's `aios guard` audit output style).
- `aios certs score <cert> <subject.json>` — score one subject ad hoc (generalizes `--score`).
- `aios certs explain <record-id>` — pretty-print one `CertificateRecord`: verdict, confidence,
  the native `detail` (e.g. APEX's named `coverage_gaps`, IRIS's `discriminating_inputs`,
  descent's conflicting claim pairs), cost, calib provenance.
- Every FLAG appends to Akashic; the operator's disposition (dismiss / quarantine-confirm /
  fix) is itself an append referencing the record — never an edit of it (DNA #3).

---

## 3. Extraction plan — `experiments/agi_witness/certs/*` → `scripts/aios_certs/`

**Prime directive: the experiment tree is evidence. Copy-forward, never move or retro-edit.**
`experiments/agi_witness/` (including `results/runs.jsonl`, `REPORT.md`, and the cert sources
that produced them) stays byte-identical; the library is a new package.

### 3.1 Target layout

```
scripts/aios_certs/                 # importable because scripts/ is already on sys.path
  __init__.py                       #   for launcher-spawned tools (same pattern descent.py used)
  types.py        # Claim, ClaimKind, ExecResult, ApexCert/IrisCert/DescentCert/GoenCert,
                  # CertVerdict, CertCost, CertificateRecord, Certifier protocol   (§1)
  claims.py       # lifted claim primitives: direct_io_conflicts, executable_claims,
                  # build_claim_graph, _canon, claim_(to|from)_dict, claims_(to|from)_jsonl
  sandbox.py      # lifted run_candidate + its sandboxing (from experiment claims.py) — IRIS's
                  # only runtime dependency beyond numpy
  apex.py         # copy of certs/apex.py, imports rewritten (see 3.3)
  iris.py         # copy of certs/iris.py,   "
  descent.py      # copy of certs/descent.py, "  + guard import fixed (see 3.3)
  goen.py         # copy of certs/goen.py,    "
  guard.py        # build_profiles + poison_score MOVED here (single source of truth);
                  # scripts/aios_akashic_guard.py becomes a thin CLI over this module with
                  # byte-identical CLI behavior
  records.py      # the ONLY new logic: per-cert *_record() adapters implementing §1.4
                  # normalization + cost measurement + envelope assembly
  cli.py          # `aios certs` subcommand (audit / score / explain) per §2.3
tests/
  test_aios_certs.py                # ported self-tests + regression fixture (see 3.5)
```

### 3.2 Dependencies to sever (each is a concrete edit in the copied files)

1. **`from contracts import ...` → `from .types import ...`** in all four cert modules.
   `TaskOutcome` does NOT migrate (it is arm/scoring machinery); `Claim.poisoned` is dropped
   per §1.2 — grep the copied cert files to confirm zero reads (the docstrings promise it;
   the test suite enforces it: `grep -rn "poisoned" scripts/aios_certs/` must return nothing).
2. **`from claims import ...` → `from .claims import ...` / `from .sandbox import run_candidate`.**
   The experiment's `claims.py` also contains claim SEEDERS/population machinery — those stay
   in the experiment; only the primitives listed in 3.1 migrate.
3. **descent.py's sys.path hack** (`parents[3]/scripts` + `import aios_akashic_guard`) →
   `from .guard import build_profiles, poison_score`. Then edit `scripts/aios_akashic_guard.py`
   to import those two functions from `aios_certs.guard` (keeping its CLI, output format, and
   `B.load_behavior_memories()` data loading untouched). This inverts the current dependency so
   the library never imports a CLI script.
4. **No dataset/arms/llm imports** may survive in the package: `dataset.py`, `arms.py`,
   `llm.py`, `run.py`, `score.py`, `drive_r1.sh` are experiment-only and stay behind.
   Enforcement: `grep -rn "import \(dataset\|arms\|llm\|run\|score\)" scripts/aios_certs/` → empty.
5. **Third-party surface:** `numpy` required; `sklearn` optional (goen already has the
   numpy-gradient-descent fallback — keep it, it is what makes the package dependency-light).
   Nothing else. No torch (descent.py already reproduced the Hodge projection in pure numpy).

### 3.3 New code (small, bounded)

- `records.py`: five `*_record(...)` adapters (≈30 lines each): call the verbatim cert
  function under `time.perf_counter()`, count sandbox execs for IRIS
  (`len(candidates) * n_probe_inputs`), apply the §1.4 verdict map, fill the envelope.
- `cli.py`: audit/score/explain over an Akashic-append JSONL of `CertificateRecord`s.
- Launcher: add `("certs", "Optional cert lint tier — audit / score / explain")` beside the
  existing `guard` entry (`aios_launcher.py:391`), dispatching to `aios_certs/cli.py`.
  `aios guard` remains as-is (it is in operator muscle memory and in docs).

### 3.4 What NOT to build (scope fence)

- No CertGate in `aios_contract_runner.py` beyond the G4 opt-in flag.
- No GoEN mode-"C" wiring in any hook (see §1.2 note).
- No new certificate types, no cert-composition scheduler, no "cert pipeline" abstraction —
  five functions, one envelope, one CLI. The witness earned exactly that much.

### 3.5 Tests to keep

1. **Ported self-tests.** Each cert module carries a `__main__` self-test with real assertions
   (apex: conformal threshold selection, contradiction-wins ordering, gap naming; iris:
   equivalence-class partition + discriminator search; descent: H⁰/H¹/anomaly on synthetic
   claims; goen: fit + rewire scoring). Port each block into `tests/test_aios_certs.py` as
   pytest functions against the LIBRARY imports; keep the `__main__` blocks working too.
2. **Determinism regression fixture.** Run apex+descent (the calibration-free/deterministic-
   path pair) over a frozen sample of claims exported once from the witness ledger
   (`experiments/agi_witness/data/ledger.jsonl` → `tests/fixtures/claims_sample.jsonl` via the
   migrated `claims_from_jsonl`), and compare full `detail` dicts against a committed golden
   JSON. Any logic drift in extraction shows up as a diff, not a vibe.
3. **Guard parity test.** `aios guard --score <cat> <tools> --json` output before vs after the
   3.3-step-3 inversion must be byte-identical on the live commons data.
4. **Invariant lints as tests:** (a) grep-no-`poisoned`; (b) grep-no-experiment-imports
   (3.2-4); (c) every `CertificateRecord` produced in the suite has `cost.tokens == 0`.
5. **Cost sanity:** apex/descent/goen/h0guard on a 50-claim set complete in <100ms each on this
   box (asserted loosely, e.g. <1s, to survive CI noise) — the §2.2 budget's floor.

### 3.6 Build order for the implementing subagents (each step verifiable alone)

1. `types.py` + `claims.py` + `sandbox.py` (pure lifts) → import-test.
2. Copy 4 certs + rewrite imports → run their `__main__` self-tests inside the package.
3. `guard.py` move + `aios_akashic_guard.py` inversion → parity test (3.5-3).
4. `records.py` adapters → unit tests for the §1.4 verdict map.
5. `cli.py` + launcher entry → `aios certs score/audit` smoke.
6. Fixture + regression + invariant tests → full pytest green.
7. G2/G3 hook wiring is a SEPARATE follow-up work item (needs memoryOS/head touchpoints and
   belongs in M4's roadmap with an owner) — the library ships without it.

---

## 4. Honest scope — what each cert is for, and what NOT to claim

Grounding: the witness run (`results/REPORT.md`, R1–R6, seeds paired). Headline facts every
claim below must stay consistent with:

- **Verdict TAXONOMY** — coupled arm C (median 17.0 verified solves) did not beat
  max(A,B)=17.0 by more than ε=3. The composition bought nothing measurable here.
- **Only DescentNet had rent**: ablating it dropped C's median 17.0 → 13.0 (Δ=4.0 > 2×SE=1.75).
  Ablating apex, iris, or goen each moved C by exactly 0.
- **Certs bought precision/calibration, not capability**: arm B (independent certs, abstaining)
  solved fewer (13 vs 17 median) at much higher precision (0.867 vs A's 0.708) and lower wall
  (1.1s vs 4.6s — B abstains instead of retrying). C reached precision 0.845 at solve rate
  0.731, paying +15% tokens / +53% wall over A.
- **On the clean P0 subset all arms were 1.000** — the certs' value shows only under
  contamination/underdetermination, i.e. they are *contamination instruments*, not solvers.
- **R6 write-back ablation: Δ=0** — no measured population-coupling effect either.

### Per-certifier scope

**DescentNet (`descent_certify`) — the one with measured rent.**
- IS for: detecting internal contradiction in a multi-source claim set before an agent reasons
  over it — H⁰ direct conflicts (the workhorse; this is what the ablation rent came from:
  removing repair-triggering contradiction detection cost 4 median solves), H¹ cyclic
  frustration in ORDER claims, and odd-source-out anomaly. The natural G2 (memory draft lint)
  and G3 (context lint) engine.
- NOT to claim: that H¹ is the general poison detector — the keystone program closed the
  opposite as an earned negative (realistic independent commons poison is H⁰-shaped; the cheap
  guard dominated H¹ at every richness). H¹ is a niche instrument for genuinely cyclic
  relational claims. Also not to claim: any repair capability — it locates trouble, it does
  not fix it.

**APEX (`apex_certify` + `fit_apex`).**
- IS for: a cheap, honest abstain signal — "coverage below a conformally-chosen threshold →
  don't answer, and here is the NAMED gap" (`coverage_gaps` tells the caller what evidence
  would flip the verdict — actionable lint, not just a score). Arm B's precision jump
  (0.708 → 0.867) is the shape of value it buys: fewer wrong submissions, at recall cost.
- NOT to claim: a coverage *guarantee*. The threshold is fit on a small, task-specific
  calibration set; it delivers at best marginal coverage on that distribution and nothing under
  drift (say "marginal, on-distribution" or say nothing). Not to claim capability: its C-arm
  ablation delta was 0. If APEX is ever rebuilt as a real runtime gate, rebase it on conformal
  risk control over agent steps (ToolChain-CRC pattern) and evaluate on AbstentionBench —
  that is a new project, not this library.

**IRIS (`iris_certify`).**
- IS for: the multiple-candidates situation only (G6): given N candidate implementations and
  executable claims, report whether evidence pins ONE behavioral equivalence class, and if not,
  name the discriminating inputs that would. Useful as selection lint for best-of-N generation.
- NOT to claim: "identifiability" in the causal-representation-learning sense — it is
  observational equivalence over the *provided* probe inputs, nothing more; no oracle
  fabrication, so it can honestly return "not identified, and no available input
  discriminates". C-arm ablation delta 0: it earned no capability rent.

**GoEN (`fit_goen` + `goen_certify`) — weakest; ship marked experimental.**
- IS for: an advisory "your context might be better without claim X / source Y" suggestion,
  scored by a small fitted model rather than a hand threshold. FLAG is a suggestion the
  operator can take or ignore; `expected_gain` is a model estimate, not a measurement.
- NOT to claim: transferability — the logistic model is fit to one task distribution and its
  calibration dies off-distribution; refit per deployment or don't use it. Ablation delta 0.
  Mode "C" (coupled features) stays out of production entirely (§1.2).

**H⁰ guard (`aios guard`) — the only one with production evidence.**
- IS for: the commons contribution gate it already runs — category-typicality anomaly with a
  self-calibrated per-category p95 (≈5% false-flag by construction; separated injected
  cross-category poison from clean entries at AUC ≈ 0.97 on this commons; measured
  catch ≈ 79% at false-flag ≈ 4% in the keystone closeout).
- NOT to claim: robustness to ADAPTIVE or coordinated poisoning (an attacker who mimics the
  category's tool vocabulary walks through), or any semantic truth-checking — it reads tool
  vocabulary shape, not content. It is a tripwire, not a defense-in-depth story.

### Tier-wide do-not-claims (binding on all product docs and marketing)

1. **No composition claim.** "The four certificates form one object / a certification layer
   with emergent value" is EXACTLY what K1 killed. Until a future witness fires positive,
   the public sentence is: *five independent, optional lint guards; one (contradiction
   detection) has measured task-level rent; one (the H⁰ guard) has production evidence; the
   rest buy precision or advice at zero token cost.*
2. **No "certified agent" / AGI-layer language.** Per M0-C4's negative branch, the AGI-layer
   claim is retired from product docs. These are guards.
3. **No mandatory gating.** Default fail-open everywhere; the single fail-closed mode is
   per-invocation opt-in (G4). Charging every run a verification tax the witness showed buys
   no capability would be self-sabotage.
4. **No silent cost.** Every record carries `CertCost`; the audit CLI totals it. The day a
   cert's `tokens` field goes nonzero is the day it needs a new witness, not a quiet commit.

---

## 5. Open holes (named, not papered over)

- **H-M1a-1:** G2/G3 need a claim-extraction step (context packs and memory drafts are prose +
  structured refs, not `Claim` lists). A cheap deterministic extractor (typed fields → PROPERTY
  claims; cited IO examples → IO claims) is unspecified — it is the real integration cost of
  the tier and belongs to the M4 roadmap as its own item. Until it exists, G1 (shipped), G5,
  and G6 are the only fully-specified hooks.
- **H-M1a-2:** confidence semantics are per-cert and explicitly non-comparable (§1.4-ii); if a
  future consumer needs one ranked queue across certs, that requires a calibration study, not
  a heuristic merge.
- **H-M1a-3:** the Akashic append target assumes M3's unified schema; until D1 lands, records
  append to the launcher-local JSONL the CLI owns (`.aios/certs/records.jsonl`), migrating
  under M3's writer model when it exists.
- **H-M1a-4:** cert *versioning vs calibration provenance* — refitting `ApexCalib`/`GoenModel`
  changes verdicts without a code change. `calib_ref` records which artifact judged; the
  policy for when refits are allowed (and by whom) is a M3 trust-model question.

---

*This spec is deliberately thin. It is D3a and only D3a: five proven functions get a common
envelope, a copy-forward extraction, an optional fail-open lint tier, and an honest label.
Everything larger is gated on evidence that does not currently exist.*
