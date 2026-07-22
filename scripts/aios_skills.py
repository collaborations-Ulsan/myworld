#!/usr/bin/env python3
"""AIOS Skill Registry — Code Artifact Induction (organism assembly Phase 4,
docs/AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22.md).

The compounding unit: the organism grows by accumulating VERIFIED, REUSABLE,
TESTED tools — "the gene, not the scar" — not by weight updates and not by raw
text memories. A skill is a self-contained Python artifact plus an EXECUTABLE
unit test; it enters the registry only after that test passes inside the OS
sandbox. A registered skill is sandbox-verified, retrievable for related tasks
(BM25), Merkle-rooted (portable/tamper-evident), and inspectable.

COMPOSES existing organs — nothing is rebuilt:

  gate      scripts/aios_sandbox.py::run_untrusted_code — the skill's code and
            its unit test run together in the OS-enforced sandbox (no network,
            privacy dirs invisible, fail closed). The unit test is the
            EXTERNAL verifier of the anti-reward-hacking mandate: register()
            never edits the code or the test, it only runs them and believes
            the exit code. No working sandbox engine -> NOT registered
            (honest refusal, never an unsandboxed run).
  proof     Merkle root over position-salted per-line hashes of the registry,
            merkle_root() replicated verbatim from
            experiments/ontology/pack_export.py (same replication precedent as
            scripts/aios_experience.py), plus an append-only pin manifest
            mirroring aios_experience's pin/verify so `verify` distinguishes
            honest APPEND growth from a REWRITE of past skills.
  retrieval BM25 class replicated verbatim from
            experiments/distiller/expel_probe.py (importing that module would
            execute its collect/evaluate model-harness imports) over
            applicability + name + code.

HONEST LIMITATIONS (read before trusting a registered skill):
  - The gate is exactly as strong as the unit test: a weak test admits a weak
    skill. Registration proves "this code ran in the sandbox and these asserts
    held" — nothing more.
  - induce_skill is v1 STRUCTURED extraction (AST: keep imports / defs /
    classes / plain assignments in source order, drop driver statements and
    __main__ blocks) — NOT an LLM. It refuses solutions with no top-level
    function. A synthesized smoke test is only an existence/callability floor
    and is labeled as such in provenance.
  - The sandbox has no network, so a skill whose unit test needs the network
    cannot pass this gate (it will be rejected by its own failing test).
  - The Merkle root proves the registry bytes are unchanged since a pin; it
    cannot prove a skill was worth registering.
  - Retrieval is lexical (BM25). Zero-token-overlap skills are never returned;
    an empty registry returns [] ("no skills yet"), never an error.

CLI (the impure edge — supplies the real clock):
  python3 scripts/aios_skills.py register --file skill.json
  python3 scripts/aios_skills.py retrieve "<task>" [-k 3]
  python3 scripts/aios_skills.py list
  python3 scripts/aios_skills.py verify
  python3 scripts/aios_skills.py root

Schema: aios.skill.v1 (records) / aios.skills.v1 (registry ops). Stdlib-only.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_sandbox as _sandbox  # noqa: E402 — Phase-1 enforcement boundary

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".aios" / "skills"
REGISTRY = SKILLS_DIR / "registry.jsonl"
MANIFEST = SKILLS_DIR / "manifest.jsonl"

SKILL_SCHEMA = "aios.skill.v1"
SCHEMA = "aios.skills.v1"
DEFAULT_TIMEOUT = 30.0

# Fields every skill must carry to be registrable. `id` is content-derived
# when absent; `counterexample` is optional by design.
REQUIRED_FIELDS = ("name", "code", "applicability", "example", "unit_test",
                   "provenance", "created_ts")


# ---------------------------------------------------------------------------
# Canonical hashing + Merkle (Phase-3 proof pattern)
# ---------------------------------------------------------------------------

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canon(obj) -> str:
    """Deterministic canonical JSON (sorted keys, no whitespace, unicode kept)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def merkle_root(hashes: list[str]) -> str:
    """Deterministic binary Merkle root over sorted leaf hashes. Empty -> hash of ''.
    Odd layers duplicate the last node (standard). Replicated verbatim from
    experiments/ontology/pack_export.py::merkle_root (the replication precedent
    is scripts/aios_experience.py; order sensitivity comes from the
    position-salted leaf preimage, not from this function)."""
    if not hashes:
        return "sha256:" + _sha256("")
    layer = sorted(hashes)
    while len(layer) > 1:
        nxt: list[str] = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i + 1] if i + 1 < len(layer) else layer[i]
            nxt.append("sha256:" + _sha256(a + b))
        layer = nxt
    return layer[0]


def _leaf(line_no: int, raw_line: str) -> str:
    """Leaf hash for one raw registry line, salted with its position so a
    reorder or renumber changes the root even though merkle_root sorts leaves
    (mirrors aios_experience._leaf; single-file registry, fixed salt)."""
    return _sha256(f"registry:{line_no}:{raw_line}")


def _fold(leaves: list[str]) -> str:
    """Order-sensitive hash chain over the leaf hashes (append-only proof: the
    chain over the first k leaves never changes when lines are appended).
    Mirrors aios_experience._fold."""
    h = ""
    for leaf in leaves:
        h = _sha256(h + leaf)
    return h


# ---------------------------------------------------------------------------
# Registry store (append-only JSONL)
# ---------------------------------------------------------------------------

def _scan(registry: Path | str = REGISTRY) -> dict:
    """One pass over the registry: raw lines, leaf hashes, parsed skills.
    A missing or empty registry is an honest empty result, never an error."""
    path = Path(registry)
    skills: list[dict] = []
    leaves: list[str] = []
    malformed = 0
    if path.is_file():
        for line_no, raw in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            leaves.append(_leaf(line_no, raw))
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(rec, dict):
                skills.append(rec)
            else:
                malformed += 1
    return {"skills": skills, "leaves": leaves, "malformed": malformed}


def load_registry(registry: Path | str = REGISTRY) -> list[dict]:
    """All registered skills (malformed lines skipped, counted by _scan)."""
    return _scan(registry)["skills"]


def registry_root(registry: Path | str = REGISTRY) -> str:
    """Current Merkle root over the registry's position-salted line hashes."""
    return merkle_root(_scan(registry)["leaves"])


def skill_id(skill: dict) -> str:
    """Content-addressed id over the load-bearing fields (name+code+unit_test):
    the same artifact always gets the same id, an edited one gets a new id."""
    return "skill-" + _sha256(_canon({
        "name": skill.get("name"), "code": skill.get("code"),
        "unit_test": skill.get("unit_test")}))[:16]


def pin(*, now: float, registry: Path | str = REGISTRY,
        manifest: Path | str = MANIFEST) -> dict:
    """Append the current root + append-only chain to the manifest (mirrors
    aios_experience.pin; `now` is caller-supplied — no clock in pure logic)."""
    leaves = _scan(registry)["leaves"]
    entry = {"schema": SCHEMA, "kind": "pin", "ts": now,
             "n_entries": len(leaves), "merkle_root": merkle_root(leaves),
             "chain": _fold(leaves)}
    mp = Path(manifest)
    mp.parent.mkdir(parents=True, exist_ok=True)
    with mp.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def verify(registry: Path | str = REGISTRY,
           manifest: Path | str = MANIFEST) -> dict:
    """Compare the registry against the LAST pin: appended-only is OK; a
    rewritten, truncated, or deleted registry is a named violation (mirrors
    aios_experience.verify)."""
    mp = Path(manifest)
    last = None
    if mp.is_file():
        for line in mp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    last = json.loads(line)
                except json.JSONDecodeError:
                    continue
    scan = _scan(registry)
    cur = scan["leaves"]
    if not last:
        return {"schema": SCHEMA, "kind": "verify", "status": "no_pin",
                "note": "no pinned root yet — register a skill (or run pin)",
                "merkle_root": merkle_root(cur), "n_entries": len(cur)}
    k = int(last.get("n_entries") or 0)
    violations: list[dict] = []
    if k and not Path(registry).is_file():
        violations.append({"violation": "missing_file",
                           "pinned_entries": k})
    elif len(cur) < k:
        violations.append({"violation": "truncated", "pinned_entries": k,
                           "current_entries": len(cur)})
    elif _fold(cur[:k]) != last.get("chain"):
        violations.append({"violation": "rewritten", "pinned_entries": k})
    return {"schema": SCHEMA, "kind": "verify",
            "status": "ok" if not violations else "tampered",
            "pinned_ts": last.get("ts"), "pinned_root": last.get("merkle_root"),
            "current_root": merkle_root(cur),
            "appended_entries": len(cur) - k,
            "malformed_lines": scan["malformed"],
            "violations": violations}


# ---------------------------------------------------------------------------
# register — the anti-reward-hacking gate (sandbox-verified, fail closed)
# ---------------------------------------------------------------------------

def _invalid(skill: dict) -> str | None:
    """Reason this skill dict cannot even reach the gate, or None."""
    if not isinstance(skill, dict):
        return "skill must be a dict"
    for field in REQUIRED_FIELDS:
        if field not in skill or skill[field] in (None, ""):
            return f"missing or empty required field: {field}"
    for field in ("name", "code", "applicability", "unit_test"):
        if not isinstance(skill[field], str) or not skill[field].strip():
            return f"field {field} must be a non-empty string"
    if not isinstance(skill["created_ts"], (int, float)):
        return "created_ts must be a number (caller-supplied timestamp)"
    return None


def register(skill: dict, *, now: float,
             registry: Path | str = REGISTRY,
             manifest: Path | str = MANIFEST,
             timeout: float = DEFAULT_TIMEOUT,
             receipt_log: Path | str | None = _sandbox.DEFAULT_RECEIPT_LOG) -> dict:
    """Run the skill's code + unit_test together inside the OS sandbox and
    append to the registry ONLY if the test passes.

    The unit test is external to whoever wrote the code: this function never
    edits either, it executes them (no network, privacy dirs invisible) and
    believes the exit code. Outcomes:

      registered                    — test passed under enforcement; appended
                                      + manifest pinned (tamper evidence).
      rejected_unit_test_failed     — the gate caught it; NOT in the registry.
      refused_sandbox_unavailable   — no working engine: fail closed, the code
                                      never ran and is NOT registered.
      refused_invalid / refused_duplicate — never reached the gate.

    `now` is caller-supplied (CLI passes time.time()); pure logic reads no clock.
    """
    def out(verdict: str, registered: bool, reason: str, **extra) -> dict:
        return {"schema": SCHEMA, "kind": "register", "registered": registered,
                "verdict": verdict, "id": skill.get("id") if isinstance(skill, dict) else None,
                "reason": reason, **extra}

    problem = _invalid(skill)
    if problem is not None:
        return out("refused_invalid", False, f"refused: {problem}")

    skill = dict(skill)  # never mutate the caller's dict
    skill.setdefault("schema", SKILL_SCHEMA)
    skill.setdefault("id", skill_id(skill))

    existing = {s.get("id") for s in load_registry(registry)}
    if skill["id"] in existing:
        return out("refused_duplicate", False,
                   f"refused: skill {skill['id']} already registered "
                   "(append-only registry; changed content gets a new id)",
                   id=skill["id"])

    program = (skill["code"]
               + "\n\n# --- external verifier: unit_test (aios_skills gate) ---\n"
               + skill["unit_test"] + "\n")
    result = _sandbox.run_untrusted_code(program, lang="python",
                                         timeout=timeout, now=now,
                                         receipt_log=receipt_log)
    gate = {"engine": result.engine, "sandboxed": result.sandboxed,
            "ok": result.ok, "returncode": result.returncode,
            "timed_out": result.timed_out, "reason": result.reason,
            "stdout_tail": result.stdout[-400:], "stderr_tail": result.stderr[-400:]}

    if not result.sandboxed:
        return out("refused_sandbox_unavailable", False,
                   f"refused (fail closed): sandbox unavailable — the code "
                   f"never ran and is NOT registered [{result.reason}]",
                   id=skill["id"], gate=gate)
    if not result.ok:
        return out("rejected_unit_test_failed", False,
                   f"rejected: unit_test did not pass in the sandbox "
                   f"[{result.reason}]", id=skill["id"], gate=gate)

    reg = Path(registry)
    reg.parent.mkdir(parents=True, exist_ok=True)
    with reg.open("a", encoding="utf-8") as fh:
        fh.write(_canon(skill) + "\n")
    entry = pin(now=now, registry=reg, manifest=manifest)
    return out("registered", True,
               f"registered: unit_test passed under enforcement "
               f"[{result.reason}]", id=skill["id"], gate=gate,
               n_skills=entry["n_entries"], merkle_root=entry["merkle_root"])


# ---------------------------------------------------------------------------
# retrieve — BM25 over applicability + name + code
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tok(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25:
    """Minimal pure-Python BM25 over the case-prompt corpus (no deps, CPU).
    Replicated verbatim from experiments/distiller/expel_probe.py::BM25
    (importing that module executes its model-harness imports)."""

    def __init__(self, docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = docs_tokens
        self.N = len(docs_tokens)
        self.avgdl = sum(len(d) for d in docs_tokens) / max(1, self.N)
        self.df: dict[str, int] = {}
        self.tf: list[dict[str, int]] = []
        for d in docs_tokens:
            counts: dict[str, int] = {}
            for t in d:
                counts[t] = counts.get(t, 0) + 1
            self.tf.append(counts)
            for t in counts:
                self.df[t] = self.df.get(t, 0) + 1

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def top_k(self, query: str, k: int, exclude_idx: int | None = None) -> list[int]:
        q = _tok(query)
        scores = []
        for i, counts in enumerate(self.tf):
            if i == exclude_idx:
                continue
            dl = len(self.docs[i])
            s = 0.0
            for term in q:
                if term not in counts:
                    continue
                f = counts[term]
                s += self._idf(term) * (f * (self.k1 + 1)) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            scores.append((s, i))
        scores.sort(reverse=True)
        return [i for _, i in scores[:k]]


def retrieve(task_text: str, k: int = 3,
             registry: Path | str = REGISTRY) -> list[dict]:
    """Top-k applicable skills for a task. Zero-token-overlap skills are never
    returned (an unrelated skill is not a retrieval); empty registry -> []."""
    skills = load_registry(registry)
    if not skills or not task_text.strip() or k <= 0:
        return []
    docs = [_tok(f"{s.get('applicability', '')} {s.get('name', '')} "
                 f"{s.get('code', '')}") for s in skills]
    bm25 = BM25(docs)
    query_terms = set(_tok(task_text))
    hits: list[dict] = []
    for i in bm25.top_k(task_text, k=len(skills)):
        shared = query_terms & set(docs[i])
        if not shared:
            continue  # BM25 score 0 — no lexical evidence of applicability
        hits.append({"skill": skills[i], "matched_terms": sorted(shared)[:12]})
        if len(hits) == k:
            break
    return hits


# ---------------------------------------------------------------------------
# induce_skill — v1 structured extraction (AST, honestly NOT an LLM)
# ---------------------------------------------------------------------------

_KEEP_NODES = (ast.Import, ast.ImportFrom, ast.FunctionDef,
               ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)


def _segment(source_lines: list[str], node: ast.stmt) -> str:
    """Source text of a top-level node by line slice (decorators included)."""
    start = node.lineno
    for deco in getattr(node, "decorator_list", []):
        start = min(start, deco.lineno)
    return "\n".join(source_lines[start - 1:node.end_lineno])


def _smoke_test(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Synthesized floor: assert the primary function exists and is callable;
    actually call it only when it takes no required arguments. This is an
    existence check, NOT a semantic spec — provenance labels it as such."""
    a = fn.args
    required = (len(a.posonlyargs) + len(a.args) - len(a.defaults)
                + sum(1 for d in a.kw_defaults if d is None))
    lines = ["# synthesized smoke test (induce_skill v1): existence/callability"
             " floor, NOT a semantic spec",
             f"assert callable({fn.name}), 'primary function {fn.name} missing'"]
    if required == 0 and isinstance(fn, ast.FunctionDef):
        lines.append(f"{fn.name}()")
    return "\n".join(lines) + "\n"


def induce_skill(goal: str, solution_code: str, *,
                 unit_test: str | None = None, created_ts: float,
                 name: str | None = None, example=None,
                 counterexample=None, provenance: dict | None = None) -> dict:
    """Extract a registrable skill from a solved task's code — v1 STRUCTURED
    (AST) extraction, not LLM-magic: keep top-level imports / functions /
    classes / plain assignments in source order; drop driver statements
    (bare expressions, __main__ blocks, loops). The last-defined top-level
    function is taken as the primary entry point. Refuses (ValueError) when
    the solution has no top-level function.

    The returned dict is ready for register(); registration still runs the
    unit test in the sandbox — induction grants nothing by itself.
    """
    if not goal or not goal.strip():
        raise ValueError("induce_skill needs a non-empty goal")
    try:
        tree = ast.parse(solution_code)
    except SyntaxError as exc:
        raise ValueError(f"solution_code does not parse: {exc}") from exc
    kept = [n for n in tree.body if isinstance(n, _KEEP_NODES)]
    fns = [n for n in kept
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not fns:
        raise ValueError("induce_skill v1 needs at least one top-level "
                         "function in solution_code (structured extraction "
                         "is function-shaped)")
    source_lines = solution_code.splitlines()
    code = "\n\n".join(_segment(source_lines, n) for n in kept).rstrip() + "\n"
    primary = fns[-1]
    if unit_test is not None and unit_test.strip():
        test, test_source = unit_test, "provided"
    else:
        test, test_source = _smoke_test(primary), "synthesized_smoke"
    applicability = "use when: " + " ".join(goal.split())
    skill = {
        "schema": SKILL_SCHEMA,
        "name": name or primary.name,
        "code": code,
        "applicability": applicability,
        "example": example or {"input": goal,
                               "expected_output": "unit_test passes "
                                                  "(see unit_test field)"},
        "unit_test": test,
        "provenance": {"source_goal": goal,
                       "induced_by": "aios_skills.induce_skill v1 "
                                     "(structured AST extraction — NOT an LLM)",
                       "unit_test_source": test_source,
                       **(provenance or {})},
        "created_ts": created_ts,
    }
    if counterexample is not None:
        skill["counterexample"] = counterexample
    skill["id"] = skill_id(skill)
    return skill


def induce_and_register(goal: str, solution_code: str,
                        unit_test: str | None = None, *, now: float,
                        registry: Path | str = REGISTRY,
                        manifest: Path | str = MANIFEST,
                        timeout: float = DEFAULT_TIMEOUT,
                        receipt_log: Path | str | None = _sandbox.DEFAULT_RECEIPT_LOG) -> dict:
    """Hook for the head / escalation recovery: induce a skill from a solved
    goal and register it through the sandbox gate. Deliberately NOT forced
    into every solve (Phase-4 v1 = mechanism + clean hook); callers opt in.
    Returns the register() decision with the induced skill attached."""
    try:
        skill = induce_skill(goal, solution_code, unit_test=unit_test,
                             created_ts=now)
    except ValueError as exc:
        return {"schema": SCHEMA, "kind": "register", "registered": False,
                "verdict": "induction_failed", "id": None,
                "reason": f"induction failed: {exc}"}
    decision = register(skill, now=now, registry=registry, manifest=manifest,
                        timeout=timeout, receipt_log=receipt_log)
    decision["skill"] = skill
    return decision


# ---------------------------------------------------------------------------
# CLI — the impure edge: supplies the real clock
# ---------------------------------------------------------------------------

def _brief(skill: dict) -> dict:
    prov = skill.get("provenance")
    return {"id": skill.get("id"), "name": skill.get("name"),
            "applicability": skill.get("applicability"),
            "created_ts": skill.get("created_ts"),
            "source_goal": prov.get("source_goal")
            if isinstance(prov, dict) else None}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="AIOS skill registry — sandbox-verified code artifact "
                    "induction (register / retrieve / list / verify / root)")
    ap.add_argument("--registry", default=str(REGISTRY))
    ap.add_argument("--manifest", default=str(MANIFEST))
    sub = ap.add_subparsers(dest="cmd", required=True)
    reg = sub.add_parser("register",
                         help="sandbox-verify a skill JSON and append it")
    reg.add_argument("--file", required=True, help="path to skill.json")
    reg.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    ret = sub.add_parser("retrieve", help="top-k applicable skills for a task")
    ret.add_argument("task", help="task text")
    ret.add_argument("-k", type=int, default=3)
    sub.add_parser("list", help="registered skills (briefs) + root")
    sub.add_parser("verify", help="append-only check against the last pin")
    sub.add_parser("root", help="print the current Merkle root")
    args = ap.parse_args(argv)

    if args.cmd == "register":
        try:
            skill = json.loads(Path(args.file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"schema": SCHEMA, "registered": False,
                              "verdict": "refused_invalid",
                              "reason": f"cannot read skill file: {exc}"},
                             ensure_ascii=False, indent=2))
            return 2
        if isinstance(skill, dict):
            skill.setdefault("created_ts", time.time())
        decision = register(skill, now=time.time(), registry=args.registry,
                            manifest=args.manifest, timeout=args.timeout)
        print(json.dumps(decision, ensure_ascii=False, indent=2))
        return 0 if decision["registered"] else 2
    if args.cmd == "retrieve":
        hits = retrieve(args.task, k=args.k, registry=args.registry)
        print(json.dumps({"schema": SCHEMA, "kind": "retrieve",
                          "task": args.task, "k": args.k,
                          "n_hits": len(hits), "hits": hits},
                         ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "list":
        scan = _scan(args.registry)
        print(json.dumps({"schema": SCHEMA, "kind": "list",
                          "n_skills": len(scan["skills"]),
                          "malformed_lines": scan["malformed"],
                          "merkle_root": merkle_root(scan["leaves"]),
                          "skills": [_brief(s) for s in scan["skills"]]},
                         ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "verify":
        report = verify(args.registry, args.manifest)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] in ("ok", "no_pin") else 2
    report = {"schema": SCHEMA, "kind": "root",
              "merkle_root": registry_root(args.registry),
              "n_entries": len(_scan(args.registry)["leaves"])}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
