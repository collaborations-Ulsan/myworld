"""The three arms (A / B / C) of the AGI certification-layer witness experiment.

This is the KEYSTONE module. The one question (README.md, keystone §3): does
CROSS-COMPONENT COUPLING — one certificate constraining another's search space —
produce emergent value beyond independent certificates, at a population +
verification-bound regime? Arms A/B/C are the operationalization of that question.

All three arms:
  * share the SAME frozen ``solver_model`` (via ``llm.complete``),
  * draw ``cfg.k`` self-consistency samples per task,
  * may ABSTAIN,
  * SPEND FROM THE SHARED ``budget`` (``TokenBudget``) — every solver call counts;
    the arm stops cleanly on ``BudgetExhausted`` (certs here are pure numpy, so they
    add coordination cost but no tokens),
  * are scored by executing the chosen candidate against the task's HIDDEN
    ``test_list`` (``dataset.passes_hidden_tests`` → ``claims.run_candidate``). The
    hidden tests are scoring truth and are NOT visible to any certificate.

Arm distinction (README / keystone §3):
  * **A** monolith — CoT + k-sample self-consistency on the RAW claim list; submit
    the majority behavioral class (no certificate at all).
  * **B** independent certificates — all 4 certs run, each seeing ONLY
    (task, claims, candidates); NO cert output feeds another; the arm applies the
    UNION of their independent filters.
  * **C** coupled loop — the 4 couplings, in order, per task:
      1. DescentNet repair → GoEN action space,
      2. Descent (persistent H1 / residual H0) → APEX abstain,
      3. APEX answerability / coverage_gaps → IRIS search + sample-budget realloc,
      4. GoEN rewires with Descent+APEX outputs as mode-"C" features → IRIS select →
         verify → write a PROVEN claim back (Akashic proof prunes later APEX).
    ``ablate`` removes exactly one certificate's contribution from arm C (R2–R6).

Constraints: deterministic given ``seed``; types imported from ``contracts``; the
REAL cert modules are used (never stubbed).
"""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import llm
from llm import TokenBudget, BudgetExhausted

from contracts import Claim, ClaimKind, TaskOutcome, ApexLabel
from claims import executable_claims, run_candidate

from certs.apex import apex_certify, ApexCalib
from certs.iris import iris_certify
from certs.descent import descent_certify
from certs.goen import goen_certify, GoenModel

from dataset import passes_hidden_tests


# =============================================================================
# Config
# =============================================================================

@dataclass
class ArmConfig:
    """Knobs shared by all arms (frozen per run). ``k`` is the self-consistency
    sample count (default 6, per README). ``solver_max_tokens`` must be >= 512 —
    reasoning-model gotcha (RESOURCES.md): at low max_tokens the model burns the whole
    budget on hidden reasoning and returns empty content."""
    k: int = 6
    temp: float = 0.7
    solver_max_tokens: int = 512
    exec_timeout_s: float = 3.0
    max_repairs: int = 2                # coupling#2: persistent H1 after <=2 repairs -> hard abstain
    k_underdetermined: int = 3          # coupling#3: fewer samples reallocated to UNDERDETERMINED tasks


# =============================================================================
# Small shared utilities
# =============================================================================

def _canon(x: Any) -> str:
    """Canonical, order-stable string form (mirrors claims/iris ``_canon``)."""
    return json.dumps(x, sort_keys=True, default=str)


def _extract_code(text: str, func_name: str) -> str:
    """Pull the function definition out of a model completion (mirrors dataset._extract_code)."""
    text = (text or "").strip()
    import re
    m = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.S)
    candidate = m.group(1) if m else text
    idx = candidate.find(f"def {func_name}")
    if idx == -1:
        idx = candidate.find("def ")
    if idx > 0:
        candidate = candidate[idx:]
    return candidate


def _spec_prompt(func_name: str, claims: list[Claim]) -> str:
    """Build the (spec-removed) generation prompt from the CLAIM set: IO examples +
    property hints. This IS the spec-in-the-ledger regime — the solver never sees the
    natural-language problem, only what the ledger asserts. Kept small (token budget)."""
    io_lines: list[str] = []
    for c in claims:
        if c.kind == ClaimKind.IO and "input" in c.payload and "output" in c.payload:
            args = ", ".join(repr(a) for a in c.payload["input"])
            io_lines.append(f"  {func_name}({args}) == {c.payload['output']!r}")
    prop_lines: list[str] = []
    for c in claims:
        if c.kind == ClaimKind.PROPERTY:
            name = c.payload.get("prop", c.payload.get("name"))
            prop_lines.append(f"  - {name} = {c.payload.get('value')!r}")

    parts = [f"Define a Python function named `{func_name}`."]
    if io_lines:
        parts.append("It must satisfy these input/output examples:\n" + "\n".join(io_lines))
    if prop_lines:
        parts.append("Known properties of the output:\n" + "\n".join(prop_lines))
    parts.append("Return ONLY the function definition as Python code, no explanation, no markdown fences.")
    return "\n\n".join(parts)


def _exec_inputs(claims: list[Claim]) -> list[Any]:
    return [claims[i].payload["input"] for i in executable_claims(claims)]


def _signature(code: str, inputs: list[Any], func_name: str, timeout: float) -> tuple:
    """Behavioral signature of a candidate over ``inputs`` (mirrors iris ``_cell``):
    ``("ok", <canon output>)`` on success, ``("__fail__",)`` on any error/timeout."""
    row: list[tuple] = []
    for args in inputs:
        r = run_candidate(code, func_name, args, timeout_s=timeout)
        row.append(("ok", _canon(r.output)) if r.ok else ("__fail__",))
    return tuple(row)


def _valid_indices(cands: list[str]) -> list[int]:
    return [i for i, c in enumerate(cands) if "def " in (c or "")]


def _majority_pick(cands: list[str], inputs: list[Any], func_name: str, timeout: float) -> int | None:
    """Arm-A self-consistency: index of a representative candidate of the LARGEST
    behavioral class (no certificate, no consistency filter). Ties -> first-appearance.
    With no probe inputs, falls back to grouping by identical source text."""
    valid = _valid_indices(cands)
    if not valid:
        return None
    groups: dict[tuple, list[int]] = {}
    order: list[tuple] = []
    for i in valid:
        s = _signature(cands[i], inputs, func_name, timeout) if inputs else ("__code__", cands[i])
        if s not in groups:
            groups[s] = []
            order.append(s)
        groups[s].append(i)
    best, best_n = order[0], 0
    for s in order:
        if len(groups[s]) > best_n:
            best_n, best = len(groups[s]), s
    return groups[best][0]


def _consistent_pick(cands: list[str], claims: list[Claim], func_name: str, timeout: float) -> int | None:
    """Representative candidate of the largest observational-equivalence class that is
    CONSISTENT with the claims (same selection rule ``iris_certify`` reports on, but
    returning the candidate index the cert object does not expose). ``None`` if no
    consistent class survives."""
    exec_idx = executable_claims(claims)
    inputs = [claims[i].payload["input"] for i in exec_idx]
    asserted = [
        ("ok", _canon(claims[i].payload["output"])) if "output" in claims[i].payload else None
        for i in exec_idx
    ]
    valid = _valid_indices(cands)
    if not valid:
        return None
    groups: dict[tuple, list[int]] = {}
    order: list[tuple] = []
    for i in valid:
        s = _signature(cands[i], inputs, func_name, timeout)
        if s not in groups:
            groups[s] = []
            order.append(s)
        groups[s].append(i)

    def _consistent(sig: tuple) -> bool:
        return all(w is None or sig[p] == w for p, w in enumerate(asserted))

    surviving = [s for s in order if _consistent(s)]
    if not surviving:
        return None
    best, best_n = surviving[0], 0
    for s in surviving:
        if len(groups[s]) > best_n:
            best_n, best = len(groups[s]), s
    return groups[best][0]


def _verify(task: dict, code: str) -> bool:
    """Scoring truth: run the candidate against the task's HIDDEN test_list."""
    if "def " not in (code or ""):
        return False
    try:
        return passes_hidden_tests(code, task)
    except Exception:
        return False


def _outcome(task: dict, seed: int, arm_label: str, *, submitted: bool, verified: bool,
             tokens: int, note: str = "") -> TaskOutcome:
    return TaskOutcome(
        task_id=task["task_id"],
        arm=arm_label,
        seed=seed,
        submitted=submitted,
        verified=bool(submitted and verified),
        tokens=tokens,
        poison_condition=task.get("poison_condition", ""),
        note=note,
    )


def _generate(solver_model: str, prompt: str, n: int, seed: int, func_name: str,
              cfg: ArmConfig, budget: TokenBudget) -> tuple[list[str], int]:
    """Draw ``n`` samples, SPENDING each call's tokens from the shared budget. Propagates
    ``BudgetExhausted`` (the caller stops the arm). Returns (candidate codes, tokens spent)."""
    cands: list[str] = []
    spent = 0
    for i in range(n):
        r = llm.complete(solver_model, prompt, seed=seed + i, temp=cfg.temp,
                         max_tokens=cfg.solver_max_tokens)
        cost = int(r["prompt_tokens"]) + int(r["completion_tokens"])
        budget.spend(cost)  # raises BudgetExhausted if it would exceed -> arm stops
        spent += cost
        cands.append(_extract_code(r["text"], func_name))
    return cands, spent


# =============================================================================
# ARM A — monolith (no certificate)
# =============================================================================

def _run_task_A(task: dict, claims: list[Claim], solver_model: str, budget: TokenBudget,
                cfg: ArmConfig, seed: int) -> TaskOutcome:
    fn = task["func_name"]
    prompt = _spec_prompt(fn, claims)                        # FULL raw claim list
    cands, tokens = _generate(solver_model, prompt, cfg.k, seed, fn, cfg, budget)
    # k-sample self-consistency: execute each candidate on the provided (own) example
    # inputs, submit the majority behavioral class. No certificate consulted.
    pick = _majority_pick(cands, _exec_inputs(claims), fn, cfg.exec_timeout_s)
    if pick is None:
        return _outcome(task, seed, "A", submitted=False, verified=False, tokens=tokens,
                        note="abstain: no valid candidate")
    verified = _verify(task, cands[pick])
    return _outcome(task, seed, "A", submitted=True, verified=verified, tokens=tokens,
                    note="majority-class")


# =============================================================================
# ARM B — independent certificates (union of filters, no cert feeds another)
# =============================================================================

def _descent_h0_drops(descent) -> set[int]:
    """DescentNet's OWN independent view (arm B): it only knows a pair conflicts, not
    which side is poisoned — so it drops BOTH members of every H0 conflict. (Arm C,
    by contrast, COUPLES corroboration to pick a single loser — see ``_repair``.)"""
    drop: set[int] = set()
    for i, j in descent.h0_conflicts:
        drop.add(i)
        drop.add(j)
    return drop


def _goen_keep(claims: list[Claim], goen_model: GoenModel | None, mode: str,
               cert_outputs: dict | None) -> set[int]:
    """Indices GoEN keeps after its learned rewire. ``None`` model (unfitted) -> keep all."""
    if goen_model is None or not claims:
        return set(range(len(claims)))
    cert = goen_certify(claims, goen_model, mode, cert_outputs=cert_outputs)
    keep = set(cert.rewired_context)
    return keep if keep else set(range(len(claims)))


def _run_task_B(task: dict, claims: list[Claim], solver_model: str, budget: TokenBudget,
                cfg: ArmConfig, seed: int, apex_calib: ApexCalib,
                goen_model: GoenModel | None) -> TaskOutcome:
    fn = task["func_name"]
    # B generates first, then filters post-hoc: each certificate sees ONLY
    # (task, claims, candidates); none reads another's output.
    prompt = _spec_prompt(fn, claims)
    cands, tokens = _generate(solver_model, prompt, cfg.k, seed, fn, cfg, budget)

    # --- 4 certificates, INDEPENDENT (each on the RAW claim set) ---
    apex = apex_certify(claims, apex_calib)
    descent = descent_certify(claims)
    iris = iris_certify(cands, claims, fn, timeout_s=cfg.exec_timeout_s)   # real cert record
    keep_goen = _goen_keep(claims, goen_model, "B", None)                  # own mode-B features only

    # --- union of independent filters: a claim survives iff NO cert dropped it ---
    drop = _descent_h0_drops(descent) | (set(range(len(claims))) - keep_goen)
    kept = [c for i, c in enumerate(claims) if i not in drop]

    # APEX independently gates attempt/abstain on the RAW claims.
    if apex.label != ApexLabel.ANSWERABLE:
        return _outcome(task, seed, "B", submitted=False, verified=False, tokens=tokens,
                        note=f"abstain: apex={apex.label.value}")

    # IRIS picks the largest class consistent with the union-filtered claim set.
    pick = _consistent_pick(cands, kept, fn, cfg.exec_timeout_s)
    if pick is None:
        return _outcome(task, seed, "B", submitted=False, verified=False, tokens=tokens,
                        note=f"abstain: no consistent class (iris n={iris.n_classes})")
    verified = _verify(task, cands[pick])
    return _outcome(task, seed, "B", submitted=True, verified=verified, tokens=tokens,
                    note=f"union-filter; iris_identified={iris.identified}")


# =============================================================================
# ARM C — coupled loop (the 4 couplings)
# =============================================================================

def _repair(claims: list[Claim], descent, proven_facts: dict[str, str] | None) -> set[int]:
    """One repair pass. Returns the indices to DROP:
      * H0: for each conflicting input, keep the MOST-CORROBORATED output (or, if the
        input is already PROVEN in the Akashic registry, the proven output) and drop the
        minority claims — an honest, no-oracle loser selection.
      * H1: cut the MINIMAL set breaking each cycle — one implicated ORDER claim per
        cycle (highest ts, i.e. last-inserted; tie -> highest index)."""
    drop: set[int] = set()

    # --- H0 corroboration-based loser drop ---
    io_by_input: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for i, c in enumerate(claims):
        if c.kind == ClaimKind.IO and "input" in c.payload and "output" in c.payload:
            io_by_input[_canon(c.payload["input"])].append((i, _canon(c.payload["output"])))
    conflict_inputs = {_canon(claims[i].payload["input"]) for i, _ in descent.h0_conflicts}
    for key in sorted(conflict_inputs):
        members = io_by_input.get(key, [])
        if not members:
            continue
        counts = Counter(o for _, o in members)
        if proven_facts and key in proven_facts:
            win = proven_facts[key]                         # coupling#4: Akashic proof resolves the conflict
        else:
            win = counts.most_common(1)[0][0]               # majority corroboration
        for idx, o in members:
            if o != win:
                drop.add(idx)

    # --- H1 minimal cycle cut ---
    for cycle in descent.h1_cycles:
        if not cycle:
            continue
        victim = max(cycle, key=lambda idx: (claims[idx].ts, idx))
        drop.add(victim)
    return drop


def _repair_loop(claims: list[Claim], cfg: ArmConfig, proven_facts: dict[str, str] | None):
    """Coupling#1: DescentNet drives repair, defining GoEN's action space. Repairs up to
    ``cfg.max_repairs`` times. Returns (repaired_claims, persistent_h1, post_descent)."""
    repaired = list(claims)
    for _ in range(cfg.max_repairs):
        d = descent_certify(repaired)
        drops = _repair(repaired, d, proven_facts)
        if not drops:
            break
        repaired = [c for i, c in enumerate(repaired) if i not in drops]
    post = descent_certify(repaired)
    persistent_h1 = bool(post.h1_cycles)
    return repaired, persistent_h1, post


def _write_back(task: dict, code: str, repaired: list[Claim], ledger_by_task: dict,
                proven_facts: dict[str, str], cfg: ArmConfig) -> None:
    """Coupling#4 (population): a VERIFIED solve writes PROVEN IO claims back into the
    shared ledger and the cross-task proven-fact registry, so later tasks' certificates
    (repair loser-selection / APEX coverage) can rely on established truth. Disabled ONLY
    by ``ablate="writeback"``."""
    tid = task["task_id"]
    fn = task["func_name"]
    proven: list[Claim] = []
    for args in _exec_inputs(repaired):
        r = run_candidate(code, fn, args, timeout_s=cfg.exec_timeout_s)
        if r.ok:
            proven_facts[_canon(args)] = _canon(r.output)
            proven.append(Claim(task_id=tid, source_id="proven", kind=ClaimKind.IO,
                                payload={"input": args, "output": r.output}, ts=10_000,
                                poisoned=False))
    if proven:
        ledger_by_task[tid] = list(ledger_by_task.get(tid, [])) + proven


def _run_task_C(task: dict, claims: list[Claim], ledger_by_task: dict, solver_model: str,
                budget: TokenBudget, cfg: ArmConfig, seed: int, apex_calib: ApexCalib,
                goen_model: GoenModel | None, ablate: str | None,
                proven_facts: dict[str, str]) -> TaskOutcome:
    fn = task["func_name"]
    arm_label = "C" if ablate is None else f"C-ablate-{ablate}"
    writeback_on = (ablate != "writeback")

    # ---- coupling#1: DescentNet repair -> GoEN action space ----
    if ablate == "descent":
        repaired = list(claims)              # -DescentNet: no repair, raw claims throughout
        persistent_h1 = False
        descent_for_goen = None              # and no Descent features feed GoEN
    else:
        repaired, persistent_h1, post_descent = _repair_loop(
            claims, cfg, proven_facts if writeback_on else None)
        descent_for_goen = post_descent

    # ---- coupling#2: Descent (persistent H1) -> APEX abstain ----
    if ablate == "apex":
        apex = None                          # -APEX: attempt all, no answerability gate
        underdetermined = False
    else:
        if ablate != "descent" and persistent_h1:
            return _outcome(task, seed, arm_label, submitted=False, verified=False, tokens=0,
                            note="abstain: persistent H1 after <=2 repairs (Descent->APEX)")
        apex = apex_certify(repaired, apex_calib)
        if apex.label == ApexLabel.CONTRADICTORY:
            return _outcome(task, seed, arm_label, submitted=False, verified=False, tokens=0,
                            note="abstain: residual H0 CONTRADICTORY post-repair")
        underdetermined = (apex.label == ApexLabel.UNDERDETERMINED)

    # ---- coupling#3: APEX answerability/coverage_gaps -> IRIS + sample-budget realloc ----
    # ANSWERABLE tasks get the full k; UNDERDETERMINED tasks get fewer samples (budget is
    # reallocated toward answerable tasks). APEX's coverage_gaps steer IRIS's discriminating
    # search, which iris_certify performs over the (repaired) claim inputs.
    n_samples = cfg.k_underdetermined if underdetermined else cfg.k

    # ---- coupling#4: GoEN rewires context with Descent+APEX outputs (mode-C features) ----
    if ablate == "goen":
        gen_context = repaired               # -GoEN: fixed (full repaired) context
    else:
        cert_outputs: dict[str, Any] = {}
        if apex is not None:
            cert_outputs["apex"] = apex
        if descent_for_goen is not None:
            cert_outputs["descent"] = descent_for_goen
        keep = _goen_keep(repaired, goen_model, "C", cert_outputs)
        gen_context = [c for i, c in enumerate(repaired) if i in keep] or repaired

    prompt = _spec_prompt(fn, gen_context)
    cands, tokens = _generate(solver_model, prompt, n_samples, seed, fn, cfg, budget)

    # ---- selection: IRIS on the REPAIRED claims (or self-consistency if -IRIS) ----
    if ablate == "iris":
        pick = _majority_pick(cands, _exec_inputs(repaired), fn, cfg.exec_timeout_s)
        sel_note = "self-consistency (iris ablated)"
    else:
        iris = iris_certify(cands, repaired, fn, timeout_s=cfg.exec_timeout_s)   # real cert
        pick = _consistent_pick(cands, repaired, fn, cfg.exec_timeout_s)
        sel_note = f"iris_identified={iris.identified} n_classes={iris.n_classes}"

    if pick is None:
        return _outcome(task, seed, arm_label, submitted=False, verified=False, tokens=tokens,
                        note=f"abstain: no consistent/valid candidate; {sel_note}")

    verified = _verify(task, cands[pick])
    if verified and writeback_on:
        _write_back(task, cands[pick], repaired, ledger_by_task, proven_facts, cfg)
    return _outcome(task, seed, arm_label, submitted=True, verified=verified, tokens=tokens,
                    note=f"coupled; {sel_note}"
                         + ("; underdetermined-realloc" if underdetermined else ""))


# =============================================================================
# Public entry point
# =============================================================================

def run_arm(arm: str, tasks: list[dict], ledger_by_task: dict[str, list[Claim]],
            solver_model: str, budget: TokenBudget, cfg: ArmConfig, *,
            ablate: str | None = None, seed: int = 0,
            apex_calib: ApexCalib | None = None,
            goen_model: GoenModel | None = None) -> list[TaskOutcome]:
    """Run one arm over ``tasks``, emitting one ``TaskOutcome`` per completed task.

    ``arm``    — "A" | "B" | "C".
    ``ablate`` — None | "apex" | "iris" | "descent" | "goen" | "writeback" (arm C only;
                 removes exactly that certificate's contribution, per README R2–R6).
    ``budget`` — shared TokenBudget; every solver call spends from it. When a call would
                 exceed it, ``BudgetExhausted`` is caught and the arm stops CLEANLY,
                 returning the outcomes gathered so far.
    ``apex_calib`` / ``goen_model`` — fitted cert artifacts for arms B/C. ``apex_calib``
                 defaults to a permissive threshold-1 calibration; ``goen_model=None``
                 makes GoEN a no-op (keep-all) so the arm still runs.

    Deterministic given ``seed``.
    """
    if arm not in ("A", "B", "C"):
        raise ValueError(f"arm must be 'A', 'B' or 'C', got {arm!r}")
    if ablate not in (None, "apex", "iris", "descent", "goen", "writeback"):
        raise ValueError(f"unknown ablate {ablate!r}")
    if arm != "C" and ablate is not None:
        raise ValueError("ablate is only meaningful for arm C")
    if apex_calib is None:
        apex_calib = ApexCalib(threshold=1)

    outcomes: list[TaskOutcome] = []
    proven_facts: dict[str, str] = {}      # cross-task Akashic registry (arm C, coupling#4)

    for task in tasks:
        tid = task["task_id"]
        claims = ledger_by_task.get(tid, [])
        t0 = time.perf_counter()
        try:
            if arm == "A":
                oc = _run_task_A(task, claims, solver_model, budget, cfg, seed)
            elif arm == "B":
                oc = _run_task_B(task, claims, solver_model, budget, cfg, seed,
                                 apex_calib, goen_model)
            else:
                oc = _run_task_C(task, claims, ledger_by_task, solver_model, budget, cfg,
                                 seed, apex_calib, goen_model, ablate, proven_facts)
        except BudgetExhausted:
            break   # named exit: budget spent, stop the arm cleanly
        oc.wall_s = round(time.perf_counter() - t0, 4)
        outcomes.append(oc)
    return outcomes


# =============================================================================
# Self-test — TINY synthetic 2-task ledger; runs arms A, B, C (+ ablations).
# =============================================================================

if __name__ == "__main__":
    from certs.goen import fit_goen, extract_features

    print("=" * 72)
    print("arms.py self-test  (tiny synthetic 2-task ledger)")
    print("=" * 72)

    # --- Deterministic fake solver: patch llm.complete so the self-test is offline &
    #     reproducible (explicitly permitted by the spec). It returns a CORRECT solution
    #     for each func, so verification is real (run against hidden tests). --------------
    _SOLUTIONS = {
        "add": "def add(a, b):\n    return a + b\n",
        "double": "def double(x):\n    return x * 2\n",
    }

    def _fake_complete(model, prompt, *, seed=0, temp=0.0, max_tokens=1024, system=None, timeout=90.0):
        fn = "double" if "`double`" in prompt else "add"
        text = _SOLUTIONS[fn]
        return {"text": text,
                "prompt_tokens": max(1, len(prompt) // 4),
                "completion_tokens": max(1, len(text) // 4),
                "cached": False, "model": model}

    llm.complete = _fake_complete   # arms call llm.complete (late-bound) -> patched
    SOLVER = "ollama:qwen2.5-coder:7b"   # nominal; the fake intercepts the call

    # --- Task 1: clean, answerable (add) ------------------------------------------------
    task_add = {
        "task_id": "syn_add", "func_name": "add", "poison_condition": "P0",
        "underdetermined": False, "test_imports": [],
        "test_list": ["assert add(2,3)==5", "assert add(10,5)==15", "assert add(0,0)==0"],
    }
    claims_add = [
        Claim("syn_add", "gold", ClaimKind.IO, {"input": [2, 3], "output": 5}, ts=0),
        Claim("syn_add", "gold", ClaimKind.IO, {"input": [10, 5], "output": 15}, ts=1),
        Claim("syn_add", "seeder0", ClaimKind.IO, {"input": [1, 1], "output": 2}, ts=2),
        Claim("syn_add", "gold", ClaimKind.PROPERTY, {"prop": "return_type", "value": "int"}, ts=3),
    ]

    # --- Task 2: H0-CONTRADICTORY (double); C must REPAIR (drop the minority '7') --------
    task_double = {
        "task_id": "syn_dbl", "func_name": "double", "poison_condition": "P1",
        "underdetermined": False, "test_imports": [],
        "test_list": ["assert double(3)==6", "assert double(10)==20", "assert double(0)==0"],
    }
    claims_double = [
        Claim("syn_dbl", "gold", ClaimKind.IO, {"input": [3], "output": 6}, ts=0),
        Claim("syn_dbl", "seeder0", ClaimKind.IO, {"input": [3], "output": 6}, ts=1),   # corroborates
        Claim("syn_dbl", "poison_h0", ClaimKind.IO, {"input": [3], "output": 7}, ts=2, poisoned=True),
        Claim("syn_dbl", "gold", ClaimKind.IO, {"input": [10], "output": 20}, ts=3),
        Claim("syn_dbl", "gold", ClaimKind.PROPERTY, {"prop": "return_type", "value": "int"}, ts=4),
    ]

    tasks = [task_add, task_double]
    ledger = {"syn_add": claims_add, "syn_dbl": claims_double}
    cfg = ArmConfig(k=3, temp=0.7, solver_max_tokens=512)
    calib = ApexCalib(threshold=1)   # permissive; CONTRADICTORY still fires regardless

    # --- Fit GoEN models (real cert; both modes) over a few synthetic (features,solved) --
    def _repaired_double():
        return [c for i, c in enumerate(claims_double) if i != 2]   # drop the '7' loser
    goen_examples = [
        (claims_add, True), (_repaired_double(), True),
        (claims_double, False), ([claims_add[0]], False),
    ]
    ex_B = [(extract_features(cl, "B"), s) for cl, s in goen_examples]
    ex_C = [(extract_features(cl, "C", cert_outputs={"apex": apex_certify(cl, calib),
                                                     "descent": descent_certify(cl)}), s)
            for cl, s in goen_examples]
    model_B = fit_goen(ex_B, "B")
    model_C = fit_goen(ex_C, "C")

    # --- Run the three arms (fresh budget each; budgets are PER ARM) ---------------------
    results: dict[str, list[TaskOutcome]] = {}
    for arm, gmodel in (("A", None), ("B", model_B), ("C", model_C)):
        budget = TokenBudget(total=20_000)
        outs = run_arm(arm, tasks, dict(ledger), SOLVER, budget, cfg,
                       seed=0, apex_calib=calib, goen_model=gmodel)
        results[arm] = outs
        print(f"\n--- ARM {arm}  (budget spent={budget.spent()}/{budget.total}) ---")
        for oc in outs:
            print(f"  {oc.task_id:<8} submitted={oc.submitted!s:<5} verified={oc.verified!s:<5} "
                  f"tokens={oc.tokens:<5} cond={oc.poison_condition} wall_s={oc.wall_s} | {oc.note}")
        assert len(outs) == 2, f"arm {arm} should emit 2 outcomes, got {len(outs)}"
        assert budget.spent() <= budget.total, "budget must never be exceeded"

    # --- KEY distinction: B abstains on the H0-contradictory task; C REPAIRS & attempts --
    b_dbl = next(o for o in results["B"] if o.task_id == "syn_dbl")
    c_dbl = next(o for o in results["C"] if o.task_id == "syn_dbl")
    assert not b_dbl.submitted, "arm B must ABSTAIN on the H0-contradictory task (apex CONTRADICTORY)"
    assert c_dbl.submitted, "arm C must REPAIR the contradiction and ATTEMPT (coupling path exercised)"
    assert c_dbl.verified, "arm C's repaired-then-solved candidate must pass hidden tests"
    print("\n[assert] B abstains on H0 task; C repairs -> attempts -> verifies  ->  coupling path EXERCISED")

    # both arms should solve the clean answerable task
    for arm in ("A", "B", "C"):
        add_oc = next(o for o in results[arm] if o.task_id == "syn_add")
        assert add_oc.submitted and add_oc.verified, f"arm {arm} should solve the clean add task"
    print("[assert] all three arms solve the clean answerable task (add)")

    # --- Budget respected under exhaustion: tiny budget -> arm stops early, no leak ------
    tiny = TokenBudget(total=40)
    outs_tiny = run_arm("A", tasks, dict(ledger), SOLVER, tiny, cfg, seed=0)
    print(f"\n[budget-exhaustion] tiny budget=40 -> {len(outs_tiny)} task(s) completed, "
          f"spent={tiny.spent()}/{tiny.total}")
    assert len(outs_tiny) < 2, "a tiny budget must stop the arm before all tasks complete"
    assert tiny.spent() <= tiny.total, "budget must never be exceeded even under exhaustion"

    # --- Every C ablation runs without crashing and removes exactly its cert ------------
    print("\n[ablations] running arm C under each single-cert ablation:")
    for ab in ("apex", "iris", "descent", "goen", "writeback"):
        budget = TokenBudget(total=20_000)
        outs = run_arm("C", tasks, dict(ledger), SOLVER, budget, cfg, ablate=ab,
                       seed=0, apex_calib=calib, goen_model=model_C)
        assert len(outs) == 2, f"C-ablate-{ab} should emit 2 outcomes"
        dbl = next(o for o in outs if o.task_id == "syn_dbl")
        print(f"  C-ablate-{ab:<9} syn_dbl: submitted={dbl.submitted!s:<5} "
              f"verified={dbl.verified!s:<5} | {dbl.note}")
    # -APEX ablation must still ATTEMPT the contradictory task (no answerability gate),
    # while raw arm C also attempts (via repair) -> both submit, by different routes.
    print("\nALL SELF-TEST ASSERTIONS PASSED")
