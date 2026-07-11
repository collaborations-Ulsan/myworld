#!/usr/bin/env python3
"""m2_driftbench freeze — hash-seal the harness (ASC-0282 WP-B).

At freeze time: sha256 over every harness source + grader spec + fixture
template, plus the frozen generator params (seeds {11,12,13}), written as a
seal receipt JSON. `verify` recomputes and reports ANY post-freeze drift —
a drifted file voids the run (contract §5: stop, void, re-register
append-only; seals are never edited or deleted).

The dev-smoke packet only ships the machinery; the actual Stage-1 seal is
executed at freeze (after the 8 eval templates exist).

stdlib only.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent

HARNESS_SOURCES = (
    "fixtures.py", "env.py", "agent_arm.py", "grader.py",
    "meter.py", "trace.py", "run_stage1.py", "freeze.py",
)
SEALED_DIRS = ("grader_specs", "dev_templates")   # every *.json inside
EVAL_SEEDS = (11, 12, 13)                          # sealed; never re-rolled


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sealed_files(root: "Path | None" = None) -> list[Path]:
    root = Path(root) if root else _DIR
    files = [root / n for n in HARNESS_SOURCES if (root / n).is_file()]
    for d in SEALED_DIRS:
        dd = root / d
        if dd.is_dir():
            files.extend(sorted(dd.glob("*.json")))
    return files


def compute_manifest(files: "list[Path] | None" = None,
                     root: "Path | None" = None) -> dict:
    root = Path(root) if root else _DIR
    files = files if files is not None else sealed_files(root)
    return {str(p.relative_to(root)): _sha256(p) for p in sorted(files)}


def combined_hash(manifest: dict) -> str:
    blob = json.dumps(manifest, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def seal(out_path: "Path | str", root: "Path | None" = None) -> dict:
    manifest = compute_manifest(root=root)
    receipt = {
        "schema": "m2.freeze_seal.v1",
        "contract": "ASC-0282",
        "sealed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "eval_seeds": list(EVAL_SEEDS),
        "note": ("post-freeze drift in any sealed file voids the run "
                 "(append-only re-registration required); dev_ templates are "
                 "sealed too so smoke fixtures cannot silently morph into eval"),
        "files": manifest,
        "combined_sha256": combined_hash(manifest),
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    return receipt


def verify(seal_path: "Path | str", root: "Path | None" = None) -> dict:
    sealed = json.loads(Path(seal_path).read_text(encoding="utf-8"))
    current = compute_manifest(root=root)
    old = sealed.get("files", {})
    drift = []
    for rel in sorted(set(old) | set(current)):
        if rel not in old:
            drift.append({"file": rel, "kind": "added_after_seal"})
        elif rel not in current:
            drift.append({"file": rel, "kind": "removed_after_seal"})
        elif old[rel] != current[rel]:
            drift.append({"file": rel, "kind": "modified_after_seal"})
    return {"ok": not drift, "drift": drift,
            "combined_sha256_sealed": sealed.get("combined_sha256"),
            "combined_sha256_current": combined_hash(current)}


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(prog="m2 freeze")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal")
    s.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--seal", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "seal":
        r = seal(a.out)
        print(json.dumps({"sealed": a.out, "files": len(r["files"]),
                          "combined_sha256": r["combined_sha256"]}, indent=2))
        return 0
    r = verify(a.seal)
    print(json.dumps(r, indent=2))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
