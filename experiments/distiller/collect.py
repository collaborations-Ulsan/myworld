"""experiments/distiller/collect.py -- run the student on A, escalate failures to the sovereign
teacher cascade, keep only causally-verified trajectories (docs/AIOS_DISTILLER_PREREG_2026-07-17.md
v1.1 S3 step 1-3).

STUDENT / TEACHER (prereg S2):
  * student = qwen3:1.7b, a HYBRID THINKING model. Empirically verified live against this box's
    ollama (0.22.1): the OpenAI-compat endpoint (`/v1/chat/completions`, what
    experiments/learnos/backend.py posts to) honors NEITHER a `"think": false` body field NOR a
    "/no_think" system message for this model/version -- it silently burns the whole max_tokens
    budget on <think> reasoning and returns empty `content` (finish_reason="length") even for a
    trivial one-line task, at both max_tokens=60 and max_tokens=600. The NATIVE `/api/chat`
    endpoint's structured `"think": false` param DOES work (verified: clean content, 17-token
    completion for a trivial prompt). This is why this module calls `/api/chat` directly instead
    of reusing backend.complete() for the student -- backend.py is left untouched; its own niche
    (simple local-ollama-or-NIM single-shot proposer, default qwen3-coder:30b, a NON-thinking
    model where this gap never manifested) is already covered for the TEACHER'S first tier by
    aios_llm_client.LLMClient inside make_sovereign_adapter, so reusing backend.py in addition
    would just be a second, redundant implementation of the same tier.
  * teacher = scripts/aios_adapters.make_sovereign_adapter (f31d055): local qwen3-coder:30b -> NIM
    -> frontier CLI (claude/codex/gemini), called UNMODIFIED, one fresh adapter per escalation.

CAUSAL GATE (prereg S3 step 2, S5): a teacher solution is "verified" iff it (a) is not a
structurally degenerate identity/constant function -- experiments/learnos/causal_gate.
is_degenerate_tool, called directly: pure/AST-based, no held-out dependency, genuinely reused
unmodified; (b) passes the task's visible tests; (c) does not regress the sentinel_check; (d)
passes held_out_tests + adversarial_tests -- tests the student/teacher never saw. (b)-(d) run
through experiments/learnos/verify.run_public(test_exprs, source), the SAME sandboxed (no-network,
cwd-bounded, timeout) subprocess execution experiments/learnos/verify.py provides -- reused
directly. Per causal_gate.py's own documented scope ("causal ablation only applies to
cot_scaffold/tool candidates" -- ours are always code_patch/from-scratch-implementation, which
has no separable artifact to ablate), the held-out-gain check IS the causal test for this
pipeline; there is nothing beyond it for check_causal_responsibility to add for a code_patch-kind
candidate.

WHY verify.run_holdout / improve.evaluate_candidate / improve.baseline_holdout_passed /
causal_gate.check_causal_responsibility are NOT called directly: all four resolve held-out content
by `task_id` against experiments/learnos/data/tasks_held_out.json, LearnOS's OWN private,
independently-audited 34-task corpus -- this module's task_ids are (deliberately, per tasks.py's
docstring) not entries there, and mixing this pipeline's synthetic tasks into that file would blur
two datasets that should stay independently isolated. verify.run_public (generic, task_id-agnostic
-- callers supply the test list directly) has no such coupling and is reused instead.

BLIND-CURATOR (prereg S3 step 2, S6 guard #2 "블라인드 리뷰 슬라이스"): experiments/learnos/
audit.run_audit is called UNMODIFIED over this module's own A-task pool via its documented
extension points (`gate_fn=`, `golden_fixes=`). One incompatibility remains even through those
extension points: `run_audit`'s trial loop unconditionally calls
`improve.baseline_holdout_passed(task)` BEFORE invoking gate_fn (verified by reading audit.py's
source -- this is not gated behind the default gate_fn), which -- like verify.run_holdout above --
is hardwired to LearnOS's own held-out file and raises for any task_id outside it. Since
`audit.run_audit` exposes no parameter to override that one call, this module substitutes it via a
documented, reversible module-attribute monkeypatch (`improve.baseline_holdout_passed`) for the
duration of the call only, then restores the original -- audit.py's own source is never touched,
and every other line of run_audit's defect-injection + false-pass-rate orchestration runs exactly
as written. If the measured false-pass rate exceeds the threshold, `freeze_promotion` is honored
exactly as documented for search.py: trajectories are still collected and logged (evidence is
never thrown away), but nothing is written to the verified-arm SFT files.

PRIVACY + SECRET SCAN (prereg S5): every record is JSON-serialized and scanned for the privacy-
gated path fragments (`_from_desktop`, `dain`, `minyoung`) and common secret shapes before any
write; a hit drops the record (never partially written) and is counted in the run summary.

stdlib only for orchestration (json, re, time, urllib, argparse); the four learnos/scripts modules
above are imported, never reimplemented.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

_DISTILLER_DIR = Path(__file__).resolve().parent
_LEARNOS_DIR = _DISTILLER_DIR.parent / "learnos"
_SCRIPTS_DIR = _DISTILLER_DIR.parent.parent / "scripts"
for _p in (_LEARNOS_DIR, _SCRIPTS_DIR):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

# experiments/learnos/ ALSO ships a module literally named tasks.py. A plain `import tasks` is
# NOT safe here: Python's sys.modules cache is checked BEFORE sys.path is ever consulted, so if
# anything in the same process (e.g. tests/test_learnos_s11.py, run earlier in the same pytest
# session) already did `import tasks` while LearnOS's dir was on sys.path, that cached (wrong)
# module wins forever after, no matter how sys.path is reordered here -- verified live: running
# `pytest tests/test_learnos_s11.py tests/test_distiller.py` in one process breaks
# `distiller_tasks.build_tasks` with AttributeError even though this file's own sys.path setup
# looks correct in isolation. Loading this package's tasks.py under a private sys.modules key
# (never the bare name "tasks") sidesteps the collision regardless of import order.
import importlib.util as _importlib_util


def _load_under_key(key: str, file_path: Path):
    if key in sys.modules:
        return sys.modules[key]
    spec = _importlib_util.spec_from_file_location(key, file_path)
    mod = _importlib_util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


_TASKS_MODULE_KEY = "aios_distiller_tasks"
distiller_tasks = _load_under_key(_TASKS_MODULE_KEY, _DISTILLER_DIR / "tasks.py")

# experiments/learnos/improve.py has its OWN internal bare `import tasks` (correct, from ITS
# perspective -- it means experiments/learnos/tasks.py). That import runs the moment `import
# improve` below executes, and is resolved via sys.path search ONLY IF "tasks" is not already in
# sys.modules -- if this package's own tasks.py (or nothing) got there first (e.g. a test file's
# own sys.path.insert(0, distiller_dir) ran before this module was imported -- verified live to
# happen exactly this way running `pytest tests/test_distiller.py tests/test_learnos.py` in one
# process), improve.py's bare import silently resolves to the WRONG tasks.py. Force-priming
# sys.modules["tasks"] to LearnOS's own module HERE, before audit/causal_gate/improve ever get a
# chance to import it, makes their internal bare import correct regardless of sys.path order or
# whatever this package's own private-keyed load above already did.
sys.modules["tasks"] = _load_under_key("tasks", _LEARNOS_DIR / "tasks.py")

import audit  # noqa: E402 -- experiments/learnos/audit.py (Blind-Curator)
import causal_gate  # noqa: E402 -- experiments/learnos/causal_gate.py
import improve  # noqa: E402 -- experiments/learnos/improve.py (Candidate dataclass + monkeypatch target)
import verify  # noqa: E402 -- experiments/learnos/verify.py (sandboxed run_public)
import aios_adapters  # noqa: E402 -- scripts/aios_adapters.py (make_sovereign_adapter, the teacher cascade)

DATA_DIR = _DISTILLER_DIR / "data"
STUDENT_MODEL_DEFAULT = "qwen3:1.7b"
_OLLAMA_NATIVE_CHAT_URL = "http://localhost:11434/api/chat"
STUDENT_MAX_TOKENS = 700
STUDENT_TIMEOUT_S = 90.0
STUDENT_RETRIES = 3
GRADE_TIMEOUT_S = 10.0
N_VERIFIED_PILOT_THRESHOLD = 250  # prereg S6: below this, every report is labeled pilot-only


def pilot_banner(n_verified: int) -> str:
    """The one honest-banner rule (prereg S6: "pilot only if N_verified < 250"), shared by
    collect.py/evaluate.py/run_distiller.py so the threshold is asserted in exactly one place."""
    if n_verified < N_VERIFIED_PILOT_THRESHOLD:
        return f"PILOT ONLY (N_verified={n_verified} < {N_VERIFIED_PILOT_THRESHOLD})"
    return f"N_verified={n_verified} >= {N_VERIFIED_PILOT_THRESHOLD}"

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


class CollectError(Exception):
    pass


# ---------------------------------------------------------------------------------------------
# student caller -- native ollama /api/chat, think:false (see module docstring for why not
# experiments/learnos/backend.py)
# ---------------------------------------------------------------------------------------------

def _ollama_native_chat(
    model: str, prompt: str, *, max_tokens: int = STUDENT_MAX_TOKENS,
    temperature: float = 0.2, timeout: float = STUDENT_TIMEOUT_S, retries: int = STUDENT_RETRIES,
) -> dict:
    """POST to ollama's native /api/chat with think:false. Returns
    {"ok": bool, "content": str, "error": str|None}. Retries with backoff on transient
    "model failed to load / resource limitations" 5xx errors (observed live on this shared-GPU
    box under VRAM contention from other concurrently-loaded models) -- never raises."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": temperature},
    }
    data = json.dumps(body).encode("utf-8")
    last_error = "unknown"
    for attempt in range(retries):
        req = urllib.request.Request(
            _OLLAMA_NATIVE_CHAT_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = (payload.get("message") or {}).get("content") or ""
            return {"ok": True, "content": content, "error": None}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            last_error = f"HTTP {e.code}: {detail}"
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            last_error = f"network error: {e}"
        if attempt < retries - 1:
            time.sleep(1.5 * (2 ** attempt))  # 1.5s, 3s, 6s
    return {"ok": False, "content": "", "error": last_error}


def call_student(prompt: str, model: str = STUDENT_MODEL_DEFAULT) -> dict:
    return _ollama_native_chat(model, prompt)


def extract_code(text: str) -> str:
    m = _CODE_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip() + "\n"
    stripped = text.strip()
    return (stripped + "\n") if stripped else ""


# ---------------------------------------------------------------------------------------------
# teacher caller -- scripts/aios_adapters.make_sovereign_adapter, unmodified
# ---------------------------------------------------------------------------------------------

def call_teacher(prompt: str) -> dict:
    """One escalation: a fresh sovereign adapter per call (goal="" so make_sovereign_adapter's
    hard-classification runs on THIS task's own prompt, not a stale bound goal -- see
    aios_adapters.make_sovereign_adapter's `_is_hard`: `goal or prompt`). Returns
    {"ok": bool, "text": str, "provenance": list[dict], "error": str|None}."""
    adapter = aios_adapters.make_sovereign_adapter(goal="")
    try:
        text = adapter(prompt)
        return {"ok": True, "text": text, "provenance": list(adapter.provenance), "error": None}
    except Exception as exc:  # noqa: BLE001 -- an escalation failure is data (log + skip), not a crash
        return {"ok": False, "text": "", "provenance": list(adapter.provenance), "error": str(exc)[:300]}


# ---------------------------------------------------------------------------------------------
# privacy + secret scan
# ---------------------------------------------------------------------------------------------

_PRIVACY_PATTERNS = (
    re.compile(r"_from_desktop"),
    re.compile(r"(?<![A-Za-z0-9_])dain(?![A-Za-z0-9_])", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_])minyoung(?![A-Za-z0-9_])", re.IGNORECASE),
)
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"NVIDIA_API_KEY\s*[=:]\s*\S+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"api[_-]?key\s*[=:]\s*['\"][A-Za-z0-9._\-]{16,}['\"]", re.IGNORECASE),
)


def privacy_scan(text: str) -> list[str]:
    """Returns a list of violation tags (empty = clean). Never raises."""
    hits = []
    for pat in _PRIVACY_PATTERNS:
        if pat.search(text):
            hits.append(f"privacy_path:{pat.pattern}")
    for pat in _SECRET_PATTERNS:
        if pat.search(text):
            hits.append(f"secret:{pat.pattern}")
    return hits


def safe_append_jsonl(path: Path, record: dict) -> list[str]:
    """Scan record (fully serialized) for privacy/secret hits; append only if clean. Returns the
    violation list (empty iff written)."""
    blob = json.dumps(record, sort_keys=True)
    hits = privacy_scan(blob)
    if hits:
        return hits
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(blob + "\n")
    return []


# ---------------------------------------------------------------------------------------------
# causal gate
# ---------------------------------------------------------------------------------------------

def verify_solution(task: dict, source: str) -> dict:
    """The causal gate (see module docstring). Returns
    {"decision": "verified"|"rejected", "reason": str, "holdout_passed": int, "holdout_total": int}."""
    priv = distiller_tasks.held_out_bundle(task)
    entry_point = task["entry_point"]

    if not source.strip():
        return {"decision": "rejected", "reason": "empty_source", "holdout_passed": 0, "holdout_total": 0}

    degenerate, reason = causal_gate.is_degenerate_tool(source, entry_point, "result == result")
    if degenerate:
        return {"decision": "rejected", "reason": f"degenerate:{reason}", "holdout_passed": 0, "holdout_total": 0}

    visible = verify.run_public(task["visible_tests"], source, timeout=GRADE_TIMEOUT_S)
    if not visible["all_passed"]:
        return {"decision": "rejected", "reason": "visible_fail", "holdout_passed": 0, "holdout_total": 0}

    sentinel = verify.run_public([task["sentinel_check"]], source, timeout=GRADE_TIMEOUT_S)
    if not sentinel["all_passed"]:
        return {"decision": "rejected", "reason": "sentinel_regressed", "holdout_passed": 0, "holdout_total": 0}

    held_out_exprs = priv["held_out_tests"] + priv["adversarial_tests"]
    holdout = verify.run_public(held_out_exprs, source, timeout=GRADE_TIMEOUT_S)
    if not holdout["all_passed"]:
        return {
            "decision": "rejected", "reason": "holdout_fail",
            "holdout_passed": holdout["passed"], "holdout_total": holdout["total"],
        }

    return {
        "decision": "verified", "reason": "ok",
        "holdout_passed": holdout["passed"], "holdout_total": holdout["total"],
    }


def _audit_gate_fn(task: dict, candidate: "improve.Candidate", baseline: int) -> dict:
    """GateFn adapter for audit.run_audit (experiments/learnos/audit.py's GateFn signature) --
    routes through the SAME verify_solution() decision boundary used for real teacher trajectories,
    so the Blind-Curator false-pass measurement is against this pipeline's ACTUAL gate, not a
    stand-in."""
    result = verify_solution(task, candidate.patch_source)
    return {"decision": "promoted" if result["decision"] == "verified" else "rejected"}


def _baseline_zero(_task: dict) -> int:
    """Monkeypatch target for improve.baseline_holdout_passed (see module docstring: run_audit
    unconditionally calls this, hardwired to LearnOS's own held-out file, before gate_fn ever
    runs). Every task here has a NotImplementedError-raising buggy_source by construction
    (tasks.py's `_stub_source`) -- it can never pass any held-out test, so the true baseline is
    always 0; this returns that fact directly instead of resolving it through the incompatible
    lookup."""
    return 0


def run_blind_curator(task_pool: list[dict], threshold: float = audit.DEFAULT_THRESHOLD) -> dict:
    """experiments/learnos/audit.run_audit, called unmodified over `task_pool`, with the ONE
    incompatible internal call (improve.baseline_holdout_passed) substituted for the duration of
    this call only -- see module docstring. audit.py's own source is never edited."""
    golden_fixes = {t["task_id"]: distiller_tasks.held_out_bundle(t)["golden_solution"] for t in task_pool}
    original = improve.baseline_holdout_passed
    improve.baseline_holdout_passed = _baseline_zero
    try:
        return audit.run_audit(task_pool, gate_fn=_audit_gate_fn, threshold=threshold, golden_fixes=golden_fixes)
    finally:
        improve.baseline_holdout_passed = original


# ---------------------------------------------------------------------------------------------
# collection loop
# ---------------------------------------------------------------------------------------------

@dataclass
class CollectSummary:
    n_a_attempted: int = 0
    n_student_solved: int = 0
    n_escalated: int = 0
    n_teacher_visible_fail: int = 0
    n_verified: int = 0
    n_unverified_only: int = 0
    n_privacy_blocked: int = 0
    n_infra_errors: int = 0
    freeze_promotion: bool = False
    blind_curator: dict = field(default_factory=dict)
    stopped_reason: str = "completed"
    elapsed_s: float = 0.0

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def collect(
    a_tasks: list[dict],
    *,
    out_dir: Path = DATA_DIR,
    time_budget_s: float = 2400.0,
    skip_audit: bool = False,
    student_model: str = STUDENT_MODEL_DEFAULT,
    log=print,
) -> CollectSummary:
    """Run the student on every task in `a_tasks` (already time-ordered by the caller), escalate
    visible-test failures to the teacher, causally verify, and append SFT pairs. Stops early
    (honestly, not silently) if `time_budget_s` is exceeded -- partial results already written to
    disk are never discarded."""
    summary = CollectSummary()
    start = time.monotonic()

    if not skip_audit:
        log(f"[distiller] running Blind-Curator audit over {len(a_tasks)} A-tasks before trusting any promotion...")
        report = run_blind_curator(a_tasks)
        summary.blind_curator = {k: v for k, v in report.items() if k != "trials"}
        summary.freeze_promotion = report["freeze_promotion"]
        log(f"[distiller] Blind-Curator: {report['false_passes']}/{report['n_trials']} false-pass "
            f"(rate={report['false_pass_rate']:.3f}, threshold={report['threshold']}) "
            f"-> freeze_promotion={report['freeze_promotion']}")

    traj_path = out_dir / "trajectories.jsonl"
    verified_traj_path = out_dir / "sft_verified_trajectory.jsonl"
    verified_soln_path = out_dir / "sft_verified_solution_only.jsonl"
    unverified_traj_path = out_dir / "sft_unverified_trajectory.jsonl"

    for task in a_tasks:
        if time.monotonic() - start > time_budget_s:
            summary.stopped_reason = f"time_budget_exceeded ({time_budget_s}s)"
            log(f"[distiller] time budget exceeded after {summary.n_a_attempted} tasks -- stopping "
                f"(partial trajectories already on disk are kept).")
            break

        summary.n_a_attempted += 1
        task_id = task["task_id"]
        pub = distiller_tasks.to_public(task)
        prompt = distiller_tasks.prompt_text(task)
        log(f"[distiller] ({summary.n_a_attempted}/{len(a_tasks)}) {task_id} ...")

        student_resp = call_student(prompt, model=student_model)
        if not student_resp["ok"]:
            summary.n_infra_errors += 1
            log(f"[distiller]   student infra error: {student_resp['error']}")
            safe_append_jsonl(traj_path, {
                "task_id": task_id, "role": "student", "ok": False,
                "error": student_resp["error"], "ts": time.time(),
            })
            continue

        student_source = extract_code(student_resp["content"])
        student_grade = verify.run_public(task["visible_tests"], student_source, timeout=GRADE_TIMEOUT_S) \
            if student_source.strip() else {"all_passed": False, "passed": 0, "total": len(task["visible_tests"])}
        safe_append_jsonl(traj_path, {
            "task_id": task_id, "role": "student", "ok": True,
            "visible_passed": student_grade["passed"], "visible_total": student_grade["total"],
            "solved": student_grade["all_passed"], "ts": time.time(),
        })

        if student_grade["all_passed"]:
            summary.n_student_solved += 1
            log("[distiller]   student solved on visible tests -- no escalation")
            continue

        summary.n_escalated += 1
        log("[distiller]   student failed visible tests -- escalating to sovereign teacher")
        teacher_resp = call_teacher(prompt)
        if not teacher_resp["ok"]:
            summary.n_infra_errors += 1
            log(f"[distiller]   teacher infra error: {teacher_resp['error']}")
            safe_append_jsonl(traj_path, {
                "task_id": task_id, "role": "teacher", "ok": False,
                "error": teacher_resp["error"], "provenance": teacher_resp["provenance"], "ts": time.time(),
            })
            continue

        teacher_text = teacher_resp["text"]
        teacher_source = extract_code(teacher_text)
        teacher_visible = verify.run_public(task["visible_tests"], teacher_source, timeout=GRADE_TIMEOUT_S) \
            if teacher_source.strip() else {"all_passed": False, "passed": 0, "total": len(task["visible_tests"])}

        traj_record = {
            "task_id": task_id, "role": "teacher", "ok": True,
            "visible_passed": teacher_visible["passed"], "visible_total": teacher_visible["total"],
            "provenance": teacher_resp["provenance"], "ts": time.time(),
        }
        if not teacher_visible["all_passed"]:
            summary.n_teacher_visible_fail += 1
            log("[distiller]   teacher failed visible tests too -- skipping (no SFT pair)")
            traj_record["gate"] = "teacher_visible_fail"
            safe_append_jsonl(traj_path, traj_record)
            continue

        gate = verify_solution(task, teacher_source)
        traj_record["gate"] = gate["reason"]
        traj_record["holdout_passed"] = gate["holdout_passed"]
        traj_record["holdout_total"] = gate["holdout_total"]
        hits = safe_append_jsonl(traj_path, traj_record)
        if hits:
            summary.n_privacy_blocked += 1
            log(f"[distiller]   privacy/secret scan blocked trajectory log write: {hits}")

        # unverified-arm dataset: same tasks, same teacher volume, NO causal gate -- the bar is
        # "teacher passed visible", exactly what a pipeline WITHOUT the held-out+sentinel+
        # degeneracy gate would have accepted (prereg S6 guard #2's decisive control).
        unverified_record = {
            "task_id": task_id, "family": pub["family"], "prompt": prompt,
            "trajectory": teacher_text, "solution": teacher_source,
            "gate_reason": gate["reason"], "collected_at": time.time(),
        }
        hits = safe_append_jsonl(unverified_traj_path, unverified_record)
        if hits:
            summary.n_privacy_blocked += 1

        if gate["decision"] != "verified":
            summary.n_unverified_only += 1
            log(f"[distiller]   teacher solution REJECTED by causal gate: {gate['reason']}")
            continue

        summary.n_verified += 1
        log(f"[distiller]   VERIFIED ({gate['holdout_passed']}/{gate['holdout_total']} held-out+adversarial)")

        if summary.freeze_promotion:
            log("[distiller]   promotion FROZEN by Blind-Curator -- not writing to verified SFT set "
                "(trajectory already logged above)")
            continue

        verified_common = {
            "task_id": task_id, "family": pub["family"], "prompt": prompt,
            "gate_reason": gate["reason"],
            "holdout_passed": gate["holdout_passed"], "holdout_total": gate["holdout_total"],
            "collected_at": time.time(),
        }
        hits1 = safe_append_jsonl(verified_traj_path, {**verified_common, "trajectory": teacher_text, "solution": teacher_source})
        hits2 = safe_append_jsonl(verified_soln_path, {**verified_common, "solution": teacher_source})
        if hits1 or hits2:
            summary.n_privacy_blocked += 1

    summary.elapsed_s = time.monotonic() - start
    return summary


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS Experience-Distiller: collect verified teacher trajectories.")
    p.add_argument("--seed", type=int, default=20260717)
    p.add_argument("--a-instances", type=int, default=6, help="instances per A family (default 6 -> 48 A tasks)")
    p.add_argument("--max-a-tasks", type=int, default=None, help="cap the number of A tasks actually attempted")
    p.add_argument("--time-budget-s", type=float, default=2400.0)
    p.add_argument("--student-model", default=STUDENT_MODEL_DEFAULT)
    p.add_argument("--skip-audit", action="store_true")
    p.add_argument("--out-dir", default=str(DATA_DIR))
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_tasks = distiller_tasks.build_tasks(seed=args.seed, a_instances=args.a_instances)
    (out_dir / "tasks_manifest.json").write_text(json.dumps(all_tasks, indent=2, sort_keys=True), encoding="utf-8")
    a_tasks = distiller_tasks.by_split(all_tasks, "A")
    if args.max_a_tasks is not None:
        a_tasks = a_tasks[: args.max_a_tasks]

    summary = collect(
        a_tasks, out_dir=out_dir, time_budget_s=args.time_budget_s,
        skip_audit=args.skip_audit, student_model=args.student_model,
    )
    banner = pilot_banner(summary.n_verified)
    print("=" * 78)
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
    print(banner)
    print("=" * 78)
    (out_dir / "collect_summary.json").write_text(
        json.dumps({**summary.as_dict(), "banner": banner}, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
