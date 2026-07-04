#!/usr/bin/env python3
"""aios_akashic_verify — Merkle verifiability for the Akashic Record (Phase 2).

Makes the shared knowledge ledger cryptographically VERIFIABLE (design doc Layers
2 & 5): compute a Merkle root over the content-addressed entry IDs, generate a
compact proof that a given entry is in the ledger, verify that proof against a root
independently, and emit public checkpoints anyone can audit. This is the trust
substrate for a cross-agent experience commons — the AGI-thesis keystone
prerequisite (verifiable experience before we can show it causally helps).

The Cloudflare Worker (deploy/akashic-worker) exposes the same over HTTP (/root,
/proof/{id}, /verify) once deployed — this module is the local core + client, so
verification works offline and the deploy is a separate (founder-gated) step.

CLI:
  aios verify-ledger                 # compute + print the local Merkle root + count
  aios verify-ledger --id <beh-id>   # prove a specific entry is in the ledger
  aios verify-ledger --checkpoint    # append {ts,root,count} to the public checkpoint
"""
from __future__ import annotations
import os, sys, json, hashlib, argparse
from datetime import datetime, timezone
from pathlib import Path

def _home() -> Path: return Path(os.environ.get("AIOS_HOME") or (Path.home()/".aios")).expanduser()
MEMORY = _home()/"memory"/"objects.jsonl"
def _checkpoints() -> Path:
    return Path(__file__).resolve().parents[1]/"docs"/"akashic_checkpoints.jsonl"

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

# ── Merkle tree — MUST match the Cloudflare Worker's canonical algorithm
# (deploy/akashic-worker/src/worker.js) so local verification agrees with the hosted
# commons: leaf = sha256("leaf:"+id) (domain-separated), INSERTION ORDER (never sorted),
# odd tail duplicates the last node, node = sha256(left_hex + right_hex).
def _leaf(entry_id: str) -> str:
    return _sha("leaf:" + entry_id)

def _root_from_leaves(leaves: list[str]) -> str:
    if not leaves:
        return _sha("")
    layer = list(leaves)
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [_sha(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0]

def merkle_root(entry_ids: list[str]) -> str:
    return _root_from_leaves([_leaf(e) for e in entry_ids])   # insertion order

def merkle_proof(entry_ids: list[str], target_id: str) -> "list[dict] | None":
    """Sibling path proving target_id ∈ ledger, or None if absent. `side` = where the
    SIBLING sits (matches the worker's `position`)."""
    leaves = [_leaf(e) for e in entry_ids]
    target = _leaf(target_id)
    if target not in leaves:
        return None
    idx = leaves.index(target)
    layer, proof = list(leaves), []
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        sib = idx + 1 if idx % 2 == 0 else idx - 1
        proof.append({"hash": layer[sib], "side": "right" if idx % 2 == 0 else "left"})
        layer = [_sha(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
        idx //= 2
    return proof

def verify_proof(target_id: str, proof: list[dict], root: str) -> bool:
    """Independently recompute the root from a leaf + proof and compare."""
    h = _leaf(target_id)
    for step in proof:
        h = _sha(h + step["hash"]) if step["side"] == "right" else _sha(step["hash"] + h)
    return h == root

# ── Local ledger access ──────────────────────────────────────────────────────
def _load_ids() -> list[str]:
    if not MEMORY.exists():
        return []
    ids = []
    for line in MEMORY.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("id"):
            ids.append(e["id"])
    return ids

def local_root() -> tuple[str, int]:
    ids = _load_ids()
    return merkle_root(ids), len(ids)

def emit_checkpoint(server: str = "local") -> dict:
    root, n = local_root()
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "root_hash": root,
             "entry_count": n, "server": server, "submitted_by": "aios-verify"}
    cp = _checkpoints()
    cp.parent.mkdir(parents=True, exist_ok=True)
    with cp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aios verify-ledger", description="Akashic Merkle verifiability")
    ap.add_argument("--id", help="prove a specific entry id is in the ledger")
    ap.add_argument("--checkpoint", action="store_true", help="append a public checkpoint")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    ids = _load_ids()
    root = merkle_root(ids)

    if a.id:
        proof = merkle_proof(ids, a.id)
        if proof is None:
            print(f"✗ entry {a.id} is NOT in the ledger ({len(ids)} entries, root {root[:16]}…)")
            return 1
        ok = verify_proof(a.id, proof, root)
        if a.json:
            print(json.dumps({"id": a.id, "in_ledger": True, "verified": ok,
                              "proof_depth": len(proof), "root": root}, indent=2))
        else:
            print(f"✓ entry {a.id} is in the ledger")
            print(f"✓ Merkle proof valid (depth {len(proof)}, root sha256:{root[:24]}…)" if ok
                  else "✗ proof FAILED to verify")
            print(f"  ledger: {len(ids)} entries")
        return 0 if ok else 1

    if a.checkpoint:
        entry = emit_checkpoint()
        print(f"✓ checkpoint appended: {entry['entry_count']} entries @ root sha256:{entry['root_hash'][:24]}…")
        print(f"  → {_checkpoints()}")
        return 0

    if a.json:
        print(json.dumps({"root": root, "entry_count": len(ids)}, indent=2))
    else:
        print(f"Akashic local Merkle root: sha256:{root}")
        print(f"  {len(ids)} content-addressed entries")
        print(f"  verify one: aios verify-ledger --id <beh-id>")
    return 0

if __name__ == "__main__":
    sys.exit(main())
