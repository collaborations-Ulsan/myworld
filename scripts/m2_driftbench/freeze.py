#!/usr/bin/env python3
"""m2_driftbench freeze — hash-seal the harness (ASC-0282 WP-B / WP-B2).

At freeze time: sha256 over every harness source + grader spec + fixture
template + eval template descriptors + frozen prompts, plus the frozen
generator params (seeds {11,12,13}), written as a seal receipt JSON. `verify`
recomputes and reports ANY post-freeze drift — a drifted file voids the run
(contract §5: stop, void, re-register append-only; seals are never edited or
deleted).

WP-B2 additions:
  * the manifest cross-references (READ-ONLY, never edited from here) the two
    hash-frozen dual-harness files experiments/driftbench/schema.py +
    analyze.py, and records whether they still match the reconciliation doc's
    frozen prefixes (1ed8fd8b… / 53f4037e…) — schema/analyze drift is verdict-
    authority drift and voids the run exactly like harness drift;
  * eval INSTANCES are generated post-seal from (sealed code x public seed) and
    are therefore derived data: they are hashed into a separate GENERATION
    receipt that chains to this seal's combined hash — they are never written
    into a sealed dir (that would read as seal drift).

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
_REPO_ROOT = _DIR.parents[1]

HARNESS_SOURCES = (
    "fixtures.py", "env.py", "agent_arm.py", "grader.py",
    "meter.py", "trace.py", "run_stage1.py", "freeze.py",
    # WP-B2 freeze packet modules:
    "prompts.py", "labelers.py", "memory.py", "probes.py", "slm_delta.py",
)
SEALED_DIRS = ("grader_specs", "dev_templates", "eval_templates")   # every *.json inside
EVAL_SEEDS = (11, 12, 13)                          # sealed; never re-rolled

# Dual-harness cross-reference (reconciliation 2026-07-11): rows must conform
# to schema.py; verdicts are computed ONLY by analyze.py. Their sha256 values
# were frozen in the prereg-A Errata; these prefixes are copied from
# docs/AIOS_DRIFTBENCH_RECONCILIATION_2026-07-11.md and re-checked at seal.
CROSS_REF_FILES = (
    "experiments/driftbench/schema.py",
    "experiments/driftbench/analyze.py",
)
CROSS_REF_EXPECTED_PREFIXES = {
    "experiments/driftbench/schema.py": "1ed8fd8b",
    "experiments/driftbench/analyze.py": "53f4037e",
}

# Canonical seal receipt location (contract §6 receipts dir). fixtures.
# generate_eval_instances refuses to run unless this receipt exists.
DEFAULT_SEAL_PATH = Path(
    "/home/user/workspaces/jaewon/descentnet/run_artifacts/descentnet/m2_freeze_seal.json")


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


def cross_ref_hashes(repo_root: "Path | None" = None) -> dict:
    """sha256 of the hash-frozen dual-harness files (READ-ONLY cross-reference)
    + whether each still matches the reconciliation doc's frozen prefix."""
    root = Path(repo_root) if repo_root else _REPO_ROOT
    out: dict = {}
    for rel in CROSS_REF_FILES:
        p = root / rel
        if not p.is_file():
            out[rel] = {"sha256": None, "matches_reconciliation": False,
                        "note": "file missing"}
            continue
        digest = _sha256(p)
        out[rel] = {"sha256": digest,
                    "matches_reconciliation":
                        digest.startswith(CROSS_REF_EXPECTED_PREFIXES[rel])}
    return out


def seal(out_path: "Path | str", root: "Path | None" = None,
         repo_root: "Path | None" = None) -> dict:
    manifest = compute_manifest(root=root)
    xref = cross_ref_hashes(repo_root=repo_root)
    receipt = {
        "schema": "m2.freeze_seal.v2",
        "contract": "ASC-0282",
        "sealed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "eval_seeds": list(EVAL_SEEDS),
        "row_seed_map": {str(i): s for i, s in enumerate(EVAL_SEEDS)},
        "note": ("post-freeze drift in any sealed file voids the run "
                 "(append-only re-registration required); dev_ templates are "
                 "sealed too so smoke fixtures cannot silently morph into eval; "
                 "eval instances are post-seal derived data hashed in the "
                 "generation receipt, chained to combined_sha256"),
        "files": manifest,
        "cross_ref_frozen": xref,
        "combined_sha256": combined_hash(manifest),
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    return receipt


def verify(seal_path: "Path | str", root: "Path | None" = None,
           repo_root: "Path | None" = None) -> dict:
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
    # The frozen dual-harness files are verdict authority: their drift voids
    # the run exactly like harness drift (checked only when the seal recorded
    # them — v1 seals from the dev packet predate cross_ref_frozen).
    sealed_xref = sealed.get("cross_ref_frozen")
    if sealed_xref:
        current_xref = cross_ref_hashes(repo_root=repo_root)
        for rel, entry in sealed_xref.items():
            if current_xref.get(rel, {}).get("sha256") != entry.get("sha256"):
                drift.append({"file": rel, "kind": "frozen_cross_ref_drifted"})
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
