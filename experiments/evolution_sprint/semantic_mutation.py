#!/usr/bin/env python3
"""Semantic mutation prototype for AIOS evolution experiments.

This module is deliberately a shadow branch: it proposes repaired Python
functions, validates them only through scripts/aios_sandbox.py, appends lineage
records, and never writes to scripts/ or promotes a survivor into the kernel.

Schema: aios.semantic_mutation.v1. Stdlib-only; Ollama access uses urllib.
"""
from __future__ import annotations

import argparse
import ast
import copy
import dataclasses
import hashlib
import importlib.util
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_LINEAGE = HERE / "semantic_mutation_lineage.jsonl"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODELS = ("qwen3-coder:30b", "qwen3:8b")
SCHEMA = "aios.semantic_mutation.v1"


@dataclasses.dataclass(frozen=True)
class FailedArtifact:
    """A failed artifact: candidate parent code, external test, and error text."""

    function_source: str
    failing_unit_test: str
    error_text: str
    artifact_id: str = "failed-artifact"


@dataclasses.dataclass(frozen=True)
class Candidate:
    code: str
    source: str
    model: str | None = None
    note: str = ""


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def artifact_hash(artifact: FailedArtifact) -> str:
    return sha256_text(
        json.dumps(dataclasses.asdict(artifact), sort_keys=True, ensure_ascii=False)
    )


def _dedupe_candidates(candidates: list[Candidate], limit: int) -> list[Candidate]:
    seen: set[str] = set()
    out: list[Candidate] = []
    for cand in candidates:
        code = cand.code.strip() + "\n"
        if not code or sha256_text(code) in seen:
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        if not any(isinstance(node, ast.FunctionDef) for node in tree.body):
            continue
        seen.add(sha256_text(code))
        out.append(dataclasses.replace(cand, code=code))
        if len(out) >= limit:
            break
    return out


class _BinOpMutation(ast.NodeTransformer):
    def __init__(self, target_index: int, new_op: ast.operator) -> None:
        self.target_index = target_index
        self.new_op = new_op
        self.seen = -1

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        self.seen += 1
        if self.seen == self.target_index:
            node.op = copy.deepcopy(self.new_op)
        return node


class _CompareMutation(ast.NodeTransformer):
    def __init__(self, target_index: int, new_op: ast.cmpop) -> None:
        self.target_index = target_index
        self.new_op = new_op
        self.seen = -1

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        self.seen += 1
        if self.seen == self.target_index and len(node.ops) == 1:
            node.ops = [copy.deepcopy(self.new_op)]
        return node


class _BoolMutation(ast.NodeTransformer):
    def __init__(self, target_index: int) -> None:
        self.target_index = target_index
        self.seen = -1

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, bool):
            self.seen += 1
            if self.seen == self.target_index:
                return ast.copy_location(ast.Constant(not node.value), node)
        return node


def _unparse_mutation(tree: ast.AST, source: str, note: str) -> Candidate | None:
    try:
        ast.fix_missing_locations(tree)
        return Candidate(code=ast.unparse(tree) + "\n", source=source, note=note)
    except Exception:
        return None


def deterministic_mutations(function_source: str, *, limit: int = 8) -> list[Candidate]:
    """Offline deterministic mutation set. It never calls a model or test runner."""

    try:
        base = ast.parse(function_source)
    except SyntaxError:
        return []

    candidates: list[Candidate] = []
    bin_ops = (ast.Add(), ast.Sub(), ast.Mult(), ast.Div(), ast.FloorDiv(), ast.Mod())
    cmp_ops = (ast.Eq(), ast.NotEq(), ast.Lt(), ast.LtE(), ast.Gt(), ast.GtE())
    n_bin = sum(isinstance(node, ast.BinOp) for node in ast.walk(base))
    n_cmp = sum(
        isinstance(node, ast.Compare) and len(node.ops) == 1 for node in ast.walk(base)
    )
    n_bool = sum(
        isinstance(node, ast.Constant) and isinstance(node.value, bool)
        for node in ast.walk(base)
    )

    for index in range(n_bin):
        original = [node for node in ast.walk(base) if isinstance(node, ast.BinOp)][
            index
        ].op
        for op in bin_ops:
            if type(op) is type(original):
                continue
            tree = copy.deepcopy(base)
            cand = _unparse_mutation(
                _BinOpMutation(index, op).visit(tree),
                "deterministic_ast",
                f"binop[{index}] -> {type(op).__name__}",
            )
            if cand:
                candidates.append(cand)

    for index in range(n_cmp):
        original = [
            node
            for node in ast.walk(base)
            if isinstance(node, ast.Compare) and len(node.ops) == 1
        ][index].ops[0]
        for op in cmp_ops:
            if type(op) is type(original):
                continue
            tree = copy.deepcopy(base)
            cand = _unparse_mutation(
                _CompareMutation(index, op).visit(tree),
                "deterministic_ast",
                f"compare[{index}] -> {type(op).__name__}",
            )
            if cand:
                candidates.append(cand)

    for index in range(n_bool):
        tree = copy.deepcopy(base)
        cand = _unparse_mutation(
            _BoolMutation(index).visit(tree),
            "deterministic_ast",
            f"bool[{index}] flipped",
        )
        if cand:
            candidates.append(cand)

    return _dedupe_candidates(candidates, limit)


def _ollama_prompt(artifact: FailedArtifact, n: int) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the semantic mutation operator for a local agent OS. "
                "Return only JSON: an array of Python function source strings. "
                "Do not include tests, prose, markdown, imports unless required, "
                "or file writes. The external unit test is the selector."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Generate {n} candidate repairs for this failed Python function.\n\n"
                "FAILED FUNCTION:\n"
                f"{artifact.function_source}\n\n"
                "FAILING UNIT TEST:\n"
                f"{artifact.failing_unit_test}\n\n"
                "ERROR TEXT:\n"
                f"{artifact.error_text}\n"
            ),
        },
    ]


def _extract_json_slice(text: str) -> str | None:
    starts = [pos for pos in (text.find("["), text.find("{")) if pos >= 0]
    if not starts:
        return None
    start = min(starts)
    for end in range(len(text), start, -1):
        chunk = text[start:end].strip()
        if not chunk:
            continue
        try:
            json.loads(chunk)
            return chunk
        except json.JSONDecodeError:
            continue
    return None


def parse_llm_candidates(text: str, *, source: str, model: str) -> list[Candidate]:
    found: list[str] = []
    js = _extract_json_slice(text)
    if js:
        data = json.loads(js)
        if isinstance(data, list):
            found = [item for item in data if isinstance(item, str)]
        elif isinstance(data, dict) and isinstance(data.get("candidates"), list):
            found = [item for item in data["candidates"] if isinstance(item, str)]
    if not found:
        found = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.S | re.I)
    return [Candidate(code=item, source=source, model=model) for item in found]


def _post_ollama(
    *,
    url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_s: float,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "stream": False,
            "messages": messages,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        raw = response.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    message = data.get("message") if isinstance(data, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("ollama response did not contain message.content")
    return message["content"]


def generate_candidates(
    artifact: FailedArtifact,
    *,
    n: int,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    use_llm: bool = True,
    ollama_timeout_s: float = 2.0,
) -> tuple[list[Candidate], dict[str, Any]]:
    """Generate candidates through Ollama when reachable, else deterministic AST."""

    if n <= 0:
        return [], {"mode": "none", "degraded": False, "errors": []}

    errors: list[str] = []
    if use_llm and os.environ.get("AIOS_SEMANTIC_MUTATION_NO_LLM") != "1":
        for model in OLLAMA_MODELS:
            try:
                text = _post_ollama(
                    url=ollama_url,
                    model=model,
                    messages=_ollama_prompt(artifact, n),
                    timeout_s=ollama_timeout_s,
                )
                llm = _dedupe_candidates(
                    parse_llm_candidates(text, source="ollama", model=model), n
                )
                if llm:
                    if len(llm) < n:
                        llm.extend(
                            deterministic_mutations(
                                artifact.function_source, limit=n - len(llm)
                            )
                        )
                        llm = _dedupe_candidates(llm, n)
                    return llm, {
                        "mode": "ollama",
                        "model": model,
                        "degraded": False,
                        "errors": errors,
                    }
                errors.append(f"{model}: no parseable candidate functions")
            except (
                OSError,
                TimeoutError,
                ValueError,
                json.JSONDecodeError,
                urllib.error.URLError,
                urllib.error.HTTPError,
            ) as exc:
                errors.append(f"{model}: {exc.__class__.__name__}: {exc}")

    offline = deterministic_mutations(artifact.function_source, limit=n)
    return offline, {
        "mode": "deterministic_offline",
        "degraded": True,
        "errors": errors or ["ollama disabled by caller or environment"],
    }


def _load_sandbox(root: Path = ROOT) -> tuple[ModuleType | None, str | None]:
    sandbox_path = root / "scripts" / "aios_sandbox.py"
    if not sandbox_path.is_file():
        return None, f"sandbox engine missing: {sandbox_path}"
    try:
        spec = importlib.util.spec_from_file_location(
            "aios_sandbox_semantic_mutation", sandbox_path
        )
        if spec is None or spec.loader is None:
            return None, "sandbox import spec unavailable"
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        if not hasattr(module, "run_untrusted_code"):
            return None, "sandbox lacks run_untrusted_code"
        return module, None
    except Exception as exc:
        return None, f"sandbox import failed: {exc.__class__.__name__}: {exc}"


def _program(candidate_code: str, unit_test: str) -> str:
    return (
        candidate_code.rstrip()
        + "\n\n# --- external verifier: failing_unit_test selector ---\n"
        + unit_test.rstrip()
        + "\n"
    )


def evaluate_candidate(
    candidate: Candidate,
    artifact: FailedArtifact,
    *,
    now: str,
    sandbox_module: ModuleType | Any | None = None,
    sandbox_error: str | None = None,
    timeout_s: float = 30.0,
    receipt_log: Path | str | None = None,
) -> dict[str, Any]:
    """Evaluate exactly one candidate. Refusal never falls back to unsandboxed exec."""

    candidate_hash = sha256_text(candidate.code)
    if sandbox_module is None:
        return {
            "schema": SCHEMA,
            "ts": now,
            "candidate_hash": candidate_hash,
            "verdict": "refused_sandbox_unavailable",
            "survivor": False,
            "sandboxed": False,
            "returncode": None,
            "engine": "none",
            "error": sandbox_error or "sandbox unavailable",
            "candidate": candidate,
        }

    result = sandbox_module.run_untrusted_code(
        _program(candidate.code, artifact.failing_unit_test),
        lang="python",
        timeout=timeout_s,
        now=now,
        receipt_log=receipt_log,
    )
    if not result.sandboxed:
        verdict = "refused_sandbox_unavailable"
        error = result.reason
    elif result.ok:
        verdict = "survivor"
        error = ""
    else:
        verdict = "rejected"
        error = (result.stderr or result.stdout or result.reason)[-1000:]

    return {
        "schema": SCHEMA,
        "ts": now,
        "candidate_hash": candidate_hash,
        "verdict": verdict,
        "survivor": verdict == "survivor",
        "sandboxed": bool(result.sandboxed),
        "returncode": result.returncode,
        "engine": result.engine,
        "error": error,
        "reason": result.reason,
        "stdout_tail": result.stdout[-400:],
        "stderr_tail": result.stderr[-400:],
        "candidate": candidate,
    }


def append_lineage(lineage_path: Path | str, record: dict[str, Any]) -> None:
    path = Path(lineage_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def evolve_failed_artifact(
    artifact: FailedArtifact,
    *,
    n: int,
    now: str,
    lineage_path: Path | str = DEFAULT_LINEAGE,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    use_llm: bool = True,
    ollama_timeout_s: float = 2.0,
    timeout_s: float = 30.0,
    sandbox_root: Path = ROOT,
    receipt_log: Path | str | None = None,
) -> dict[str, Any]:
    """Generate, sandbox-select, append lineage, and return a report."""

    parent_hash = artifact_hash(artifact)
    candidates, generation = generate_candidates(
        artifact,
        n=n,
        ollama_url=ollama_url,
        use_llm=use_llm,
        ollama_timeout_s=ollama_timeout_s,
    )
    sandbox_module, sandbox_error = _load_sandbox(sandbox_root)
    evaluations: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates):
        evaluation = evaluate_candidate(
            candidate,
            artifact,
            now=now,
            sandbox_module=sandbox_module,
            sandbox_error=sandbox_error,
            timeout_s=timeout_s,
            receipt_log=receipt_log,
        )
        lineage_record = {
            "schema": SCHEMA,
            "kind": "lineage",
            "ts": now,
            "artifact_id": artifact.artifact_id,
            "generation": generation,
            "candidate_index": index,
            "parent_hash": parent_hash,
            "candidate_hash": evaluation["candidate_hash"],
            "candidate_source": candidate.source,
            "candidate_model": candidate.model,
            "candidate_note": candidate.note,
            "verdict": evaluation["verdict"],
            "survivor": evaluation["survivor"],
            "sandboxed": evaluation["sandboxed"],
            "engine": evaluation["engine"],
            "returncode": evaluation["returncode"],
            "error": evaluation["error"],
        }
        append_lineage(lineage_path, lineage_record)
        evaluations.append(evaluation)

    survivors = [
        {
            "candidate_hash": item["candidate_hash"],
            "source": item["candidate"].source,
            "model": item["candidate"].model,
            "code": item["candidate"].code,
        }
        for item in evaluations
        if item["survivor"]
    ]
    return {
        "schema": SCHEMA,
        "kind": "report",
        "ts": now,
        "artifact_id": artifact.artifact_id,
        "parent_hash": parent_hash,
        "lineage_path": str(Path(lineage_path)),
        "generation": generation,
        "candidate_count": len(candidates),
        "evaluated_count": len(evaluations),
        "survivor_count": len(survivors),
        "survivors": survivors,
        "verdicts": [
            {
                "candidate_hash": item["candidate_hash"],
                "verdict": item["verdict"],
                "sandboxed": item["sandboxed"],
                "engine": item["engine"],
                "error": item["error"],
            }
            for item in evaluations
        ],
        "shadow_branch": {
            "writes_to_scripts": False,
            "auto_promotes": False,
            "selection": "sandbox_only",
        },
        "limitations": [
            "LLM repairs depend on local Ollama availability and output format.",
            "Offline mutations are small AST perturbations, not broad program synthesis.",
            "A passing unit test proves only the supplied selector, not general correctness.",
            "No survivor is written into kernel files or skill registries.",
        ],
    }


def demo_artifact() -> FailedArtifact:
    return FailedArtifact(
        artifact_id="demo-broken-add",
        function_source=textwrap.dedent(
            """
            def add(a, b):
                return a - b
            """
        ).strip(),
        failing_unit_test=textwrap.dedent(
            """
            assert add(2, 3) == 5
            assert add(-2, 7) == 5
            """
        ).strip(),
        error_text="AssertionError: add(2, 3) returned -1, expected 5",
    )


def _artifact_from_json(path: Path) -> FailedArtifact:
    data = json.loads(path.read_text(encoding="utf-8"))
    return FailedArtifact(
        function_source=str(data["function_source"]),
        failing_unit_test=str(data["failing_unit_test"]),
        error_text=str(data.get("error_text", "")),
        artifact_id=str(data.get("artifact_id", path.stem)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="run the built-in demo")
    source.add_argument("--artifact-json", type=Path, help="failed artifact JSON")
    parser.add_argument("--n", type=int, default=6)
    parser.add_argument("--lineage", type=Path, default=DEFAULT_LINEAGE)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-timeout", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc).isoformat()
    artifact = demo_artifact() if args.demo else _artifact_from_json(args.artifact_json)
    report = evolve_failed_artifact(
        artifact,
        n=args.n,
        now=now,
        lineage_path=args.lineage,
        ollama_url=args.ollama_url,
        use_llm=not args.no_llm,
        ollama_timeout_s=args.ollama_timeout,
        timeout_s=args.timeout,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["evaluated_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
