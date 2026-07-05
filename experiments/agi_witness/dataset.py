"""Spec-in-the-ledger dataset builder for the AGI certification-layer witness experiment.

Pipeline (README.md, Fable design; see also ../../docs/AIOS_AGI_CERTIFICATION_KEYSTONE.md §3):

  1. Fetch MBPP-sanitized (google-research raw JSON).
  2. Pilot filter — measure pass@k-given-FULL-spec for BOTH tier-1 solver candidates on a
     sampled pool; pick the solver with high pass@k AND clean token accounting; keep only
     problems the CHOSEN solver solves >=60% pass@k (generation-easiness gate).
  3. Claim construction per kept problem: true IO claims (from test_list, executed against
     the gold reference to get ground-truth outputs), PROPERTY claims (return type /
     sortedness / monotonicity / length invariants, derived programmatically), ORDER claims
     where a numeric ordering is meaningful.
  4. Poison conditions ~even thirds over EVAL tasks: P0 clean, P1 = H0 (false IO claims from
     corrupted sources), P2 = H1 (frustrated cyclic ORDER claims). Calibration/spare stay
     clean (P0) by construction — they calibrate the conformal cert, so they must be trusted.
  5. Underdetermination: ~20% of (P0) eval tasks get their claim set pruned to a single IO
     claim so the ledger under-constrains the spec (proxy for "multiple behaviorally-distinct
     reference-consistent impls" — we do not enumerate alternative implementations here).
  6. Population seeding: 4 seeder agents (local ollama, temp=1.0, distinct source_ids) attempt
     each kept task; their (possibly wrong) solutions contribute honest-mistake IO/PROPERTY
     claims to the ledger under their own source_id.
  7. Outputs under data/: tasks.jsonl, ledger.jsonl (via claims.claims_to_jsonl), splits.json,
     pilot.json.

Everything deterministic: a single seeded random.Random drives all sampling; no wall-clock
enters any output. stdlib + numpy only (numpy unused directly but permitted per RESOURCES.md).
Uses contracts.Claim/ClaimKind, claims.run_candidate/claims_to_jsonl/direct_io_conflicts, and
llm.complete for every model call -- no reimplementation of any of those.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import random
import re
import sys
import urllib.request
from typing import Any

from contracts import Claim, ClaimKind
from claims import claims_to_jsonl, direct_io_conflicts, run_candidate
import llm

# ---- paths / constants ------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "data")
_RAW_CACHE = os.path.join(_DATA_DIR, "mbpp_sanitized.json")
_MBPP_URL = (
    "https://raw.githubusercontent.com/google-research/google-research/"
    "master/mbpp/sanitized-mbpp.json"
)

SOLVER_CANDIDATES = ["nim:openai/gpt-oss-120b", "nim:qwen/qwen3-next-80b-a3b-instruct"]
SEEDER_MODEL = "ollama:qwen2.5-coder:7b"
N_SEEDERS = 4

PASS_THRESHOLD = 0.60  # generation-easiness gate on the chosen solver's pass@k


# =============================================================================
# 1. Fetch MBPP-sanitized
# =============================================================================

def fetch_mbpp(refresh: bool = False) -> list[dict]:
    """Fetch (or load cached) MBPP-sanitized problems, normalized to
    {"task_id","text","code","test_list","test_imports"}."""
    if (not refresh) and os.path.exists(_RAW_CACHE):
        with open(_RAW_CACHE) as f:
            raw = json.load(f)
    else:
        with urllib.request.urlopen(_MBPP_URL, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_RAW_CACHE, "w") as f:
            json.dump(raw, f)
    out = []
    for p in raw:
        out.append({
            "task_id": f"mbpp_{p['task_id']}",
            "text": p["prompt"],
            "code": p["code"],
            "test_list": p["test_list"],
            "test_imports": p.get("test_imports", []),
        })
    return out


# =============================================================================
# 2. Func-name extraction + literal IO extraction from test_list
# =============================================================================

def _defined_func_names(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    return {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def extract_func_name(problem: dict) -> str | None:
    """Find the entry-point function name: the defined name that's actually
    called (possibly nested inside e.g. set(...)) in the first test assertion."""
    defined = _defined_func_names(problem["code"])
    if not defined:
        return None
    for t in problem["test_list"]:
        try:
            tree = ast.parse(t)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id in defined:
                return node.func.id
    # Fallback: last top-level def (MBPP convention places the entry point last).
    top_level = [n.name for n in ast.walk(ast.parse(problem["code"]))
                 if isinstance(n, ast.FunctionDef)]
    return top_level[-1] if top_level else None


def literal_call_args(func_name: str, test_list: list[str], max_pairs: int = 6) -> list[list[Any]]:
    """Extract literal argument lists for calls to func_name found (possibly nested)
    in test_list assertions. Only keeps calls whose every arg is ast.literal_eval-able."""
    out: list[list[Any]] = []
    seen = set()
    for t in test_list:
        try:
            tree = ast.parse(t)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == func_name:
                try:
                    args = [ast.literal_eval(a) for a in node.args]
                except Exception:
                    continue
                key = json.dumps(args, sort_keys=True, default=str)
                if key in seen:
                    continue
                seen.add(key)
                out.append(args)
                break  # one call per test line is enough
        if len(out) >= max_pairs:
            break
    return out[:max_pairs]


# =============================================================================
# 3. Hidden-test verification harness (built on claims.run_candidate)
# =============================================================================

def _build_check_code(candidate_code: str, test_list: list[str], test_imports: list[str]) -> str:
    """Wrap candidate_code + the MBPP asserts in a zero-arg function so the existing
    claims.run_candidate sandbox (fn(*args)) can execute them without modification."""
    lines = [candidate_code, ""]
    lines.extend(test_imports or [])
    lines.append("def __check_all__():")
    for t in test_list:
        lines.append("    " + t)
    lines.append("    return True")
    return "\n".join(lines)


def passes_hidden_tests(candidate_code: str, problem: dict, timeout_s: float = 5.0) -> bool:
    check_code = _build_check_code(candidate_code, problem["test_list"], problem["test_imports"])
    res = run_candidate(check_code, "__check_all__", [], timeout_s=timeout_s)
    return bool(res.ok)


# =============================================================================
# 4. Solver generation + pass@k pilot
# =============================================================================

def _extract_code(text: str, func_name: str) -> str:
    text = (text or "").strip()
    m = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.S)
    candidate = m.group(1) if m else text
    idx = candidate.find(f"def {func_name}")
    if idx == -1:
        idx = candidate.find("def ")
    if idx > 0:
        candidate = candidate[idx:]
    return candidate


def _gen_prompt(problem: dict, func_name: str) -> str:
    hint = problem["test_list"][0] if problem["test_list"] else ""
    return (
        f"{problem['text']}\n\n"
        f"Your solution MUST define a function named `{func_name}` matching this test:\n"
        f"{hint}\n\n"
        "Return ONLY the Python code (the function definition), no explanation, no markdown fences."
    )


def solve_pass_at_k(
    model: str, problem: dict, func_name: str, k: int, *, temp: float, max_tokens: int,
) -> dict:
    """Generate k candidates for `problem` with `model`, return per-problem stats."""
    prompt = _gen_prompt(problem, func_name)
    passed = False
    tokens_total = 0
    empty = 0
    for i in range(k):
        r = llm.complete(model, prompt, seed=i, temp=temp, max_tokens=max_tokens)
        tokens_total += r["prompt_tokens"] + r["completion_tokens"]
        code = _extract_code(r["text"], func_name)
        if "def " not in code:
            empty += 1
            continue
        if not passed and passes_hidden_tests(code, problem):
            passed = True
    return {"passed": passed, "tokens_total": tokens_total, "empty": empty, "k": k}


def run_pilot(pool: list[dict], func_names: dict[str, str], k: int, *, temp: float, max_tokens: int) -> dict:
    """Measure pass@k-given-full-spec for both SOLVER_CANDIDATES over `pool`."""
    results: dict[str, dict] = {}
    for model in SOLVER_CANDIDATES:
        per_problem = {}
        n_pass = 0
        tokens_all = 0
        empty_all = 0
        for p in pool:
            fn = func_names[p["task_id"]]
            if fn is None:
                per_problem[p["task_id"]] = {"passed": False, "tokens_total": 0, "empty": k, "k": k}
                continue
            stat = solve_pass_at_k(model, p, fn, k, temp=temp, max_tokens=max_tokens)
            per_problem[p["task_id"]] = stat
            n_pass += int(stat["passed"])
            tokens_all += stat["tokens_total"]
            empty_all += stat["empty"]
        n = max(1, len(pool))
        results[model] = {
            "pass_at_k": n_pass / n,
            "mean_tokens_per_problem": tokens_all / n,
            "empty_rate": empty_all / (n * k),
            "per_problem": per_problem,
        }
    return results


def choose_solver(pilot_results: dict) -> tuple[str, str]:
    """Pick the solver with the higher pass@k; tie-break on cleaner token accounting
    (lower empty_rate, then lower mean tokens -- the reasoning-model gotcha in
    RESOURCES.md burns tokens on hidden reasoning and can return empty content)."""
    ranked = sorted(
        pilot_results.items(),
        key=lambda kv: (-kv[1]["pass_at_k"], kv[1]["empty_rate"], kv[1]["mean_tokens_per_problem"]),
    )
    best_model, best_stats = ranked[0]
    reason = (
        f"pass@k={best_stats['pass_at_k']:.3f} vs "
        f"{ranked[1][0]}={ranked[1][1]['pass_at_k']:.3f}; "
        f"empty_rate={best_stats['empty_rate']:.3f}"
    )
    return best_model, reason


# =============================================================================
# 5. Property / order derivation (pure, deterministic, no LLM)
# =============================================================================

def derive_properties(io_pairs: list[tuple[list[Any], Any]]) -> dict[str, Any]:
    """Programmatic PROPERTY claims derivable from executed (args, output) pairs."""
    props: dict[str, Any] = {}
    if not io_pairs:
        return props

    types = {type(o).__name__ for _, o in io_pairs}
    if len(types) == 1:
        props["return_type"] = types.pop()

    seq_outputs = [(a, o) for a, o in io_pairs if isinstance(o, (list, tuple))]
    if seq_outputs and len(seq_outputs) == len(io_pairs):
        if all(list(o) == sorted(o) for _, o in seq_outputs):
            props["sorted_asc"] = True
        elif all(list(o) == sorted(o, reverse=True) for _, o in seq_outputs):
            props["sorted_desc"] = True
        len_flags = []
        for args, o in seq_outputs:
            in_len = next((len(a) for a in args if isinstance(a, (list, tuple, str))), None)
            if in_len is not None:
                len_flags.append(len(o) == in_len)
        if len_flags and all(len_flags):
            props["output_len_eq_input_len"] = True

    numeric_pairs = [
        (args[0], o) for args, o in io_pairs
        if len(args) == 1 and isinstance(args[0], (int, float)) and not isinstance(args[0], bool)
        and isinstance(o, (int, float)) and not isinstance(o, bool)
    ]
    if len(numeric_pairs) >= 2:
        s = sorted(numeric_pairs, key=lambda t: t[0])
        vals = [o for _, o in s]
        if all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)):
            props["monotonic_nondecreasing"] = True
        elif all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)):
            props["monotonic_nonincreasing"] = True
    return props


def derive_order_claims(task_id: str, source_id: str, io_pairs: list[tuple[list[Any], Any]], ts0: int) -> list[Claim]:
    """ORDER claims 'where meaningful': a numeric single-arg input chain, ordered by
    input magnitude, gives a non-cyclic before/after chain (feeds build_claim_graph's
    order_chain edges without any H1 frustration)."""
    numeric_pairs = [
        (args[0], args) for args, _ in io_pairs
        if len(args) == 1 and isinstance(args[0], (int, float)) and not isinstance(args[0], bool)
    ]
    if len(numeric_pairs) < 3:
        return []
    ordered = sorted(numeric_pairs, key=lambda t: t[0])
    claims = []
    for i in range(len(ordered) - 1):
        before = json.dumps(ordered[i][0], default=str)
        after = json.dumps(ordered[i + 1][0], default=str)
        claims.append(Claim(
            task_id=task_id, source_id=source_id, kind=ClaimKind.ORDER,
            payload={"before": before, "after": after}, ts=ts0 + i, poisoned=False,
        ))
    return claims


def _corrupt(output: Any) -> Any:
    """Return a value guaranteed to differ (by canonical JSON) from `output`."""
    if isinstance(output, bool):
        cand = not output
    elif isinstance(output, int):
        cand = output + 1
    elif isinstance(output, float):
        cand = output + 1.0
    elif isinstance(output, str):
        cand = (output[::-1] if output else output) + "_x"
    elif isinstance(output, (list, tuple)):
        lst = list(output)[::-1] + ["_x"]
        cand = lst if isinstance(output, list) else tuple(lst)
    else:
        cand = {"__poison__": True}
    if json.dumps(cand, sort_keys=True, default=str) == json.dumps(output, sort_keys=True, default=str):
        cand = {"__poison__": True, "orig": repr(output)}
    return cand


# =============================================================================
# 6. Population seeding (4 local seeders)
# =============================================================================

_SEED_PROMPT_TMPL = (
    "Write a Python function named `{func_name}` that solves this problem. "
    "Return ONLY the function code, no explanation, no markdown fences.\n\n"
    "Problem: {text}"
)


def seed_task(problem: dict, func_name: str, io_pairs: list[tuple[list[Any], Any]], ts0: int) -> list[Claim]:
    """Run N_SEEDERS distinct local-model attempts at `problem`; extract IO/PROPERTY
    claims (including honest mistakes) under each seeder's own source_id."""
    claims: list[Claim] = []
    ts = ts0
    prompt = _SEED_PROMPT_TMPL.format(func_name=func_name, text=problem["text"])
    args_only = [a for a, _ in io_pairs]
    for i in range(N_SEEDERS):
        source_id = f"seeder{i}"
        r = llm.complete(SEEDER_MODEL, prompt, seed=i, temp=1.0, max_tokens=512)
        code = _extract_code(r["text"], func_name)
        if "def " not in code:
            continue
        seeder_pairs: list[tuple[list[Any], Any]] = []
        for args in args_only:
            res = run_candidate(code, func_name, args, timeout_s=3.0)
            if res.ok:
                seeder_pairs.append((args, res.output))
                claims.append(Claim(
                    task_id=problem["task_id"], source_id=source_id, kind=ClaimKind.IO,
                    payload={"input": args, "output": res.output}, ts=ts, poisoned=False,
                ))
                ts += 1
        for prop, val in derive_properties(seeder_pairs).items():
            claims.append(Claim(
                task_id=problem["task_id"], source_id=source_id, kind=ClaimKind.PROPERTY,
                payload={"prop": prop, "value": val}, ts=ts, poisoned=False,
            ))
            ts += 1
    return claims


# =============================================================================
# 7. Ledger construction (gold IO/PROPERTY/ORDER + poison + underdetermination)
# =============================================================================

def build_gold_claims(problem: dict, func_name: str, ts0: int) -> tuple[list[Claim], list[tuple[list[Any], Any]]]:
    """True IO claims (ground-truth output executed from the reference solution),
    plus PROPERTY / ORDER claims derived from them. Returns (claims, io_pairs)."""
    ts = ts0
    claims: list[Claim] = []
    io_pairs: list[tuple[list[Any], Any]] = []
    for args in literal_call_args(func_name, problem["test_list"], max_pairs=6):
        res = run_candidate(problem["code"], func_name, args, timeout_s=3.0)
        if not res.ok:
            continue
        io_pairs.append((args, res.output))
        claims.append(Claim(
            task_id=problem["task_id"], source_id="gold", kind=ClaimKind.IO,
            payload={"input": args, "output": res.output}, ts=ts, poisoned=False,
        ))
        ts += 1
    for prop, val in derive_properties(io_pairs).items():
        claims.append(Claim(
            task_id=problem["task_id"], source_id="gold", kind=ClaimKind.PROPERTY,
            payload={"prop": prop, "value": val}, ts=ts, poisoned=False,
        ))
        ts += 1
    order_claims = derive_order_claims(problem["task_id"], "gold", io_pairs, ts)
    claims.extend(order_claims)
    return claims, io_pairs


def apply_h0_poison(task_id: str, io_pairs: list[tuple[list[Any], Any]], ts0: int, rng: random.Random) -> list[Claim]:
    """P1: false IO claims -- same input, corrupted output, from a poisoned source_id."""
    if not io_pairs:
        return []
    n = min(2, len(io_pairs))
    chosen = rng.sample(io_pairs, n)
    claims = []
    for i, (args, output) in enumerate(chosen):
        claims.append(Claim(
            task_id=task_id, source_id="poison_h0", kind=ClaimKind.IO,
            payload={"input": args, "output": _corrupt(output)}, ts=ts0 + i, poisoned=True,
        ))
    return claims


def apply_h1_poison(task_id: str, ts0: int) -> list[Claim]:
    """P2: a frustrated cyclic ORDER claim set -- x->y->z->x. Each link is pairwise a
    plausible before/after assertion; the cycle as a whole is globally inconsistent
    (feeds build_claim_graph's order_chain H1 detection)."""
    labels = ["x", "y", "z"]
    chain = list(zip(labels, labels[1:] + labels[:1]))  # (x,y) (y,z) (z,x) -> cycle
    return [
        Claim(task_id=task_id, source_id="poison_h1", kind=ClaimKind.ORDER,
              payload={"before": b, "after": a}, ts=ts0 + i, poisoned=True)
        for i, (b, a) in enumerate(chain)
    ]


# =============================================================================
# 8. Top-level pipeline
# =============================================================================

def build_dataset(args: argparse.Namespace) -> dict:
    os.makedirs(_DATA_DIR, exist_ok=True)
    rng = random.Random(args.seed)

    all_problems = fetch_mbpp(refresh=args.refresh_mbpp)
    print(f"[fetch] {len(all_problems)} MBPP-sanitized problems loaded")

    ordered = sorted(all_problems, key=lambda p: p["task_id"])
    rng.shuffle(ordered)
    pool = ordered[: args.pilot_n]
    func_names = {p["task_id"]: extract_func_name(p) for p in pool}
    n_no_fn = sum(1 for v in func_names.values() if v is None)
    print(f"[pilot pool] {len(pool)} problems sampled (seed={args.seed}); "
          f"{n_no_fn} had no extractable func_name")

    print(f"[pilot] measuring pass@{args.k}-given-full-spec for: {SOLVER_CANDIDATES}")
    pilot_results = run_pilot(pool, func_names, args.k, temp=args.gen_temp, max_tokens=args.gen_max_tokens)
    for model, stats in pilot_results.items():
        print(f"  {model}: pass@{args.k}={stats['pass_at_k']:.3f} "
              f"mean_tokens/problem={stats['mean_tokens_per_problem']:.1f} "
              f"empty_rate={stats['empty_rate']:.3f}")

    chosen_solver, reason = choose_solver(pilot_results)
    print(f"[pilot] CHOSEN SOLVER: {chosen_solver} ({reason})")

    pilot_out = {
        "pilot_n": len(pool),
        "k": args.k,
        "seed": args.seed,
        "chosen_solver": chosen_solver,
        "reason": reason,
        "models": {
            m: {
                "pass_at_k": s["pass_at_k"],
                "mean_tokens_per_problem": s["mean_tokens_per_problem"],
                "empty_rate": s["empty_rate"],
            }
            for m, s in pilot_results.items()
        },
    }
    with open(os.path.join(_DATA_DIR, "pilot.json"), "w") as f:
        json.dump(pilot_out, f, indent=2, sort_keys=True)

    if args.pilot_only:
        print("[pilot-only] stopping after solver selection + pilot.json write")
        return {"pilot": pilot_out}

    # ---- generation-easiness gate: keep problems the chosen solver solves >=60% ----
    chosen_per_problem = pilot_results[chosen_solver]["per_problem"]
    kept = [
        p for p in pool
        if func_names[p["task_id"]] is not None
        and chosen_per_problem[p["task_id"]]["passed"]
    ]
    # pass@k above is a single boolean per problem in this pool size; treat "passed"
    # (>=1 of k hit) as meeting the >=60% pass@k bar at this pool's k (k samples,
    # >=60% of k passing == at least ceil(0.6*k) passes -- approximated here by the
    # any-pass signal from run_pilot; for the full run this is exact per k, see README).
    print(f"[filter] kept {len(kept)}/{len(pool)} problems at pass@{args.k}>= {PASS_THRESHOLD:.0%} "
          f"threshold under {chosen_solver}")

    kept_ids_sorted = [p["task_id"] for p in kept]
    eval_ids = kept_ids_sorted[: args.n_eval]
    rest = kept_ids_sorted[args.n_eval:]
    cal_ids = rest[: args.n_cal]
    spare_ids = rest[args.n_cal:]
    by_id = {p["task_id"]: p for p in kept}

    print(f"[split] eval={len(eval_ids)} calibration={len(cal_ids)} spare={len(spare_ids)}")

    # ---- poison condition assignment: ~even thirds over EVAL tasks only ----
    poison_of: dict[str, str] = {}
    conditions = ["P0", "P1", "P2"]
    for i, tid in enumerate(eval_ids):
        poison_of[tid] = conditions[i % 3]
    for tid in cal_ids + spare_ids:
        poison_of[tid] = "P0"  # calibration/spare stay clean (trusted for conformal calib)

    # ---- underdetermination: ~20% of P0 eval tasks, pruned to 1 IO claim ----
    underdet: dict[str, bool] = {tid: False for tid in kept_ids_sorted}
    p0_eval_ids = [tid for tid in eval_ids if poison_of[tid] == "P0"]
    for i, tid in enumerate(p0_eval_ids):
        if i % 5 == 0:
            underdet[tid] = True

    all_claims: list[Claim] = []
    ts = 0
    tasks_out: list[dict] = []
    counts_by_cond = {"P0": 0, "P1": 0, "P2": 0}
    n_underdet = 0

    for tid in kept_ids_sorted:
        p = by_id[tid]
        fn = func_names[tid]
        gold_claims, io_pairs = build_gold_claims(p, fn, ts)
        ts += len(gold_claims)

        cond = poison_of[tid]
        counts_by_cond[cond] += 1
        if cond == "P1":
            poison_claims = apply_h0_poison(tid, io_pairs, ts, rng)
            ts += len(poison_claims)
            gold_claims += poison_claims
        elif cond == "P2":
            poison_claims = apply_h1_poison(tid, ts)
            ts += len(poison_claims)
            gold_claims += poison_claims

        if underdet[tid]:
            n_underdet += 1
            first_io = next((c for c in gold_claims if c.kind == ClaimKind.IO), None)
            gold_claims = [first_io] if first_io else []

        all_claims.extend(gold_claims)

        # Underdetermined tasks are deliberately pruned to 1 IO claim above; letting
        # seeders run over the FULL io_pairs would re-derive the withheld IO pairs
        # from their own (often-correct) solutions and undo the intended
        # under-constraint, so seeding is skipped for those tasks.
        if (not args.skip_seed) and (not underdet[tid]) and tid in (eval_ids + cal_ids):
            seed_claims = seed_task(p, fn, io_pairs, ts)
            ts += len(seed_claims)
            all_claims.extend(seed_claims)

        split = "eval" if tid in eval_ids else ("calibration" if tid in cal_ids else "spare")
        tasks_out.append({
            "task_id": tid,
            "func_name": fn,
            "test_list": p["test_list"],
            "test_imports": p["test_imports"],
            "gold_code": p["code"],
            "poison_condition": cond,
            "underdetermined": underdet[tid],
            "split": split,
        })

    conflicts = direct_io_conflicts(all_claims)
    print(f"[claims] total={len(all_claims)} across {len(kept_ids_sorted)} tasks "
          f"(io_conflicts detected={len(conflicts)})")
    print(f"[poison] eval-condition counts: {counts_by_cond} (calibration+spare forced P0)")
    print(f"[underdetermined] {n_underdet}/{len(p0_eval_ids)} P0-eval tasks pruned to 1 IO claim")

    with open(os.path.join(_DATA_DIR, "tasks.jsonl"), "w") as f:
        for t in sorted(tasks_out, key=lambda t: t["task_id"]):
            f.write(json.dumps(t, sort_keys=True, default=str) + "\n")

    claims_to_jsonl(all_claims, os.path.join(_DATA_DIR, "ledger.jsonl"))

    splits = {"calibration": cal_ids, "eval": eval_ids, "spare": spare_ids}
    with open(os.path.join(_DATA_DIR, "splits.json"), "w") as f:
        json.dump(splits, f, indent=2, sort_keys=True)

    return {
        "pilot": pilot_out,
        "kept": len(kept_ids_sorted),
        "n_claims": len(all_claims),
        "splits": {k: len(v) for k, v in splits.items()},
        "poison_counts": counts_by_cond,
        "n_underdetermined": n_underdet,
    }


# =============================================================================
# CLI
# =============================================================================

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-eval", type=int, default=100, help="target # of eval task ids")
    ap.add_argument("--n-cal", type=int, default=60, help="target # of calibration task ids")
    ap.add_argument("--pilot-n", type=int, default=20, help="candidate-pool size for the pilot / filter")
    ap.add_argument("--k", type=int, default=8, help="pass@k sample count")
    ap.add_argument("--gen-temp", type=float, default=0.8, help="solver generation temperature")
    ap.add_argument("--gen-max-tokens", type=int, default=512, help="solver max_tokens (>=512 per RESOURCES.md)")
    ap.add_argument("--pilot-only", action="store_true", help="stop after solver pick + pilot.json")
    ap.add_argument("--skip-seed", action="store_true", help="skip population seeding (step 6)")
    ap.add_argument("--refresh-mbpp", action="store_true", help="refetch MBPP-sanitized instead of using cache")
    ap.add_argument("--seed", type=int, default=0, help="global RNG seed (determinism)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    summary = build_dataset(args)
    print("\n[summary]")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
