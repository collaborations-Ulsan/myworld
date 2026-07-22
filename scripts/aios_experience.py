#!/usr/bin/env python3
"""AIOS Sovereign Experience Graph — the organism's continuous, queryable,
tamper-evident self-record (organism assembly Phase 3,
docs/AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22.md).

COMPOSES existing pieces — no new server, no graph DB, no second store:

  source   scripts/aios_run_log.py JSONL under .aios/runs/ (append-only; one file
           per organic goal: session_meta / turn_context / trajectory /
           kind:"escalation" (Phase 2) / kind:"outcome" (Phase 3 head wiring))
  index    in-memory over the JSONL (the run logs ARE the store; nothing to drift)
  proof    Merkle root over position-salted per-line hashes — merkle_root()
           replicated verbatim from experiments/ontology/pack_export.py — plus an
           append-only pin manifest (.aios/experience/manifest.jsonl) so `verify`
           can distinguish honest APPEND growth from a REWRITE of past experience.

This is the organism querying its OWN continuous experience across sessions:
what it failed at, when it escalated and whether it recovered, which substrate
recovered the failure. Measured by behavior on REAL run_log data.

HONEST LIMITATIONS (read before trusting the numbers):
  - Run logs written before the Phase-3 head wiring carry NO outcome record —
    their exit is reported as unknown_exit (never guessed), unless a Phase-2
    escalation record proves a failure exit.
  - `by-goal` matches goal_hint (Phase-3 logs) or any text already present in
    the log (tool names / trajectory result summaries); pre-Phase-3 logs have
    no goal field, so matches there are best-effort text hits.
  - The Merkle root proves the log bytes are unchanged since a pin; it cannot
    prove the organism logged truthfully in the first place.

CLI:
  python3 scripts/aios_experience.py query summary|failures|escalations|provider-recovery
  python3 scripts/aios_experience.py query by-goal <substr>
  python3 scripts/aios_experience.py root            # print the current Merkle root
  python3 scripts/aios_experience.py pin             # append current root to the manifest
  python3 scripts/aios_experience.py verify          # append-only check vs last pin

Schema: aios.experience.v1  (stdlib-only)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / ".aios" / "runs"                       # aios_run_log.RUNS — same dir
MANIFEST = ROOT / ".aios" / "experience" / "manifest.jsonl"
SCHEMA = "aios.experience.v1"

# Exit classification. SUCCESS/CHECKPOINT mirror aios_turn_loop's named exits;
# failure exits mirror aios_head._ESCALATION_FAILURE_EXITS plus anything else
# that is neither success nor checkpoint (e.g. no_sampler). Replicated, not
# imported: this module must work standalone over a copied runs dir.
SUCCESS_EXITS = frozenset({"model_finished"})
CHECKPOINT_EXITS = frozenset({"needs_approval"})


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def merkle_root(hashes: list[str]) -> str:
    """Deterministic binary Merkle root over sorted leaf hashes. Empty -> hash of ''.
    Odd layers duplicate the last node (standard). Replicated verbatim from
    experiments/ontology/pack_export.py::merkle_root (order sensitivity comes
    from the position-salted leaf preimage, not from this function)."""
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


def _leaf(run_id: str, line_no: int, raw_line: str) -> str:
    """Leaf hash for one raw log line. Salted with (run_id, line position) so a
    reorder, renumber, or cross-file move changes the root even though
    merkle_root sorts its leaves."""
    return _sha256(f"{run_id}:{line_no}:{raw_line}")


def _fold(leaves: list[str]) -> str:
    """Order-sensitive hash chain over a file's leaf hashes (append-only proof:
    the chain over the first k leaves never changes when lines are appended)."""
    h = ""
    for leaf in leaves:
        h = _sha256(h + leaf)
    return h


class ExperienceIndex:
    """In-memory queryable index over every run log in `runs_dir`.

    A missing or empty dir is an honest empty index ("no experience yet"),
    never an error. Read-only over the source: this class NEVER writes to the
    run logs (append-only invariant — the only file it ever appends to is the
    pin manifest, via pin())."""

    def __init__(self, runs_dir: str | Path = RUNS) -> None:
        self.runs_dir = Path(runs_dir)
        self.runs: list[dict] = []
        self.leaf_hashes: list[str] = []
        self.file_leaves: dict[str, list[str]] = {}
        self.entries = 0
        self.malformed = 0
        self._ingest()

    # -- ingest ---------------------------------------------------------------

    def _ingest(self) -> None:
        if not self.runs_dir.is_dir():
            return
        for path in sorted(self.runs_dir.glob("*.jsonl")):
            run_id = path.stem
            leaves: list[str] = []
            run = {
                "run_id": run_id, "agent": "", "git_sha": "", "ts": "",
                "turns": 0, "tool_calls": 0, "tools": Counter(),
                "statuses": Counter(), "tool_errors": [],
                "gate_checks": 0, "gate_rejections": 0,
                "exit": None, "exit_source": None, "goal_hint": "",
                "escalation_recovered": None,
                "escalations": [], "events": Counter(), "records": 0,
            }
            blobs: list[str] = [run_id]
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for line_no, raw in enumerate(text.splitlines(), start=1):
                if not raw.strip():
                    continue
                leaves.append(_leaf(run_id, line_no, raw))
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    self.malformed += 1
                    continue
                if not isinstance(rec, dict):
                    self.malformed += 1
                    continue
                run["records"] += 1
                self._absorb(run, rec, blobs)
            # A run that never recorded an outcome but DID escalate provably
            # failed with the escalation's failed_exit (escalation only fires
            # on failure exits — aios_head._ESCALATION_FAILURE_EXITS).
            if run["exit"] is None and run["escalations"]:
                run["exit"] = run["escalations"][-1].get("failed_exit")
                run["exit_source"] = "escalation"
            run["status"] = _run_status(run)
            run["_search"] = " ".join(blobs).lower()
            self.runs.append(run)
            self.leaf_hashes.extend(leaves)
            self.file_leaves[run_id] = leaves
            self.entries += len(leaves)
        self.runs.sort(key=lambda r: (r["ts"], r["run_id"]))

    @staticmethod
    def _absorb(run: dict, rec: dict, blobs: list[str]) -> None:
        kind = rec.get("kind")
        if kind == "session_meta":
            if not run["agent"]:                      # duplicates exist in real logs
                run["agent"] = str(rec.get("agent") or "")
                run["git_sha"] = str(rec.get("git_sha") or "")
                run["ts"] = str(rec.get("ts") or "")
                blobs.append(run["agent"])
        elif kind == "turn_context":
            try:
                run["turns"] = max(run["turns"], int(rec.get("turn") or 0))
            except (TypeError, ValueError):
                pass
        elif kind == "trajectory":
            run["tool_calls"] += 1
            tool = str(rec.get("tool") or "?")
            status = str(rec.get("status") or "?")
            run["tools"][tool] += 1
            run["statuses"][status] += 1
            blobs.append(tool)
            if status == "error":
                run["tool_errors"].append(
                    {"turn": rec.get("turn"), "tool": tool, "status": status})
            if rec.get("result") is not None:
                blobs.append(json.dumps(rec["result"], ensure_ascii=False))
        elif kind == "epistemic_gate":
            run["gate_checks"] += 1
            if rec.get("passed") is False:
                run["gate_rejections"] += 1
        elif kind == "escalation":
            esc = {k: v for k, v in rec.items() if k != "kind"}
            run["escalations"].append(esc)
            blobs.append(json.dumps(esc, ensure_ascii=False))
        elif kind == "outcome":
            run["exit"] = rec.get("exit")
            run["exit_source"] = "outcome"
            try:
                run["turns"] = max(run["turns"], int(rec.get("turns") or 0))
            except (TypeError, ValueError):
                pass
            if rec.get("goal_hint"):
                run["goal_hint"] = str(rec["goal_hint"])
                blobs.append(run["goal_hint"])
            if "escalation_recovered" in rec:
                run["escalation_recovered"] = bool(rec["escalation_recovered"])
        else:
            run["events"][str(kind)] += 1

    # -- tamper evidence ------------------------------------------------------

    @property
    def root(self) -> str:
        return merkle_root(self.leaf_hashes)

    def file_chains(self) -> dict[str, dict]:
        return {rid: {"entries": len(lv), "chain": _fold(lv)}
                for rid, lv in self.file_leaves.items()}

    def pin(self, manifest: str | Path = MANIFEST) -> dict:
        """Append the current root + per-file chains to the manifest (append-only)."""
        entry = {
            "schema_version": SCHEMA,
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "runs_dir": str(self.runs_dir),
            "n_files": len(self.file_leaves), "n_entries": self.entries,
            "malformed_lines": self.malformed, "merkle_root": self.root,
            "files": self.file_chains(),
        }
        mp = Path(manifest)
        mp.parent.mkdir(parents=True, exist_ok=True)
        with mp.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def verify(self, manifest: str | Path = MANIFEST) -> dict:
        """Compare current state against the LAST pin: appended-only is OK;
        a rewritten, truncated, or deleted past entry is a named violation."""
        mp = Path(manifest)
        last = None
        if mp.is_file():
            for line in mp.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        last = json.loads(line)
                    except json.JSONDecodeError:
                        continue
        if not last:
            return {"schema_version": SCHEMA, "status": "no_pin",
                    "note": "no pinned root yet — run `pin` first",
                    "merkle_root": self.root, "n_entries": self.entries}
        violations: list[dict] = []
        for rid, pinned in (last.get("files") or {}).items():
            cur = self.file_leaves.get(rid)
            k = int(pinned.get("entries") or 0)
            if cur is None:
                violations.append({"run_id": rid, "violation": "missing_file"})
            elif len(cur) < k:
                violations.append({"run_id": rid, "violation": "truncated",
                                   "pinned_entries": k, "current_entries": len(cur)})
            elif _fold(cur[:k]) != pinned.get("chain"):
                violations.append({"run_id": rid, "violation": "rewritten",
                                   "pinned_entries": k})
        return {
            "schema_version": SCHEMA,
            "status": "ok" if not violations else "tampered",
            "pinned_ts": last.get("ts"), "pinned_root": last.get("merkle_root"),
            "current_root": self.root,
            "appended_entries": self.entries - int(last.get("n_entries") or 0),
            "new_files": sorted(set(self.file_leaves) - set(last.get("files") or {})),
            "violations": violations,
        }


def _run_status(run: dict) -> str:
    e = run["exit"]
    if e is None:
        return "unknown_exit"           # pre-Phase-3 log: outcome was never recorded
    if e in SUCCESS_EXITS:
        return "success"
    if e in CHECKPOINT_EXITS:
        return "checkpoint"
    return "failure"


def _run_brief(run: dict) -> dict:
    brief = {"run_id": run["run_id"], "ts": run["ts"], "status": run["status"],
             "exit": run["exit"], "exit_source": run["exit_source"],
             "turns": run["turns"], "tool_calls": run["tool_calls"],
             "goal_hint": run["goal_hint"]}
    if run["escalations"]:
        esc = run["escalations"][-1]
        brief["escalation"] = {
            "attempted": bool(esc.get("escalation_attempted")),
            "recovered": bool(esc.get("recovered")),
            "verifier": esc.get("verifier"), "best_score": esc.get("best_score"),
            "recovered_by": _winner(esc), "error": esc.get("error"),
        }
    return brief


def _winner(esc: dict) -> str | None:
    """The generator whose answer won the escalation (max-score ok provenance
    entry — aios_escalate provenance shape: id/generator/score/parent_id/ok)."""
    ok = [p for p in (esc.get("provenance") or [])
          if isinstance(p, dict) and p.get("ok")]
    if not ok:
        return None
    return max(ok, key=lambda p: float(p.get("score") or 0.0)).get("generator")


def _providers_from(esc: dict) -> dict[str, dict]:
    """Per-generator attempt stats for one escalation, derived from provenance
    (always present in head-written records); provider_breakdown fallback for
    foreign records without provenance."""
    out: dict[str, dict] = {}
    prov = [p for p in (esc.get("provenance") or []) if isinstance(p, dict)]
    if prov:
        for p in prov:
            g = str(p.get("generator") or "?")
            d = out.setdefault(g, {"generations": 0, "successes": 0, "best_score": 0.0})
            d["generations"] += 1
            if p.get("ok"):
                d["successes"] += 1
                d["best_score"] = max(d["best_score"], float(p.get("score") or 0.0))
        return out
    for g, d in (esc.get("provider_breakdown") or {}).items():
        if isinstance(d, dict):
            out[str(g)] = {"generations": int(d.get("generations") or 0),
                           "successes": int(d.get("successes") or 0),
                           "best_score": float(d.get("best_score") or 0.0)}
    return out


# -- queries ------------------------------------------------------------------

def q_failures(ix: ExperienceIndex) -> dict:
    """What did I fail at, and why (exit reasons + tool-level errors)?"""
    failed = [r for r in ix.runs if r["status"] == "failure"]
    tool_errors = [{"run_id": r["run_id"], **e}
                   for r in ix.runs for e in r["tool_errors"]]
    return {
        "schema_version": SCHEMA, "query": "failures",
        "runs_scanned": len(ix.runs),
        "failed_runs": [_run_brief(r) for r in failed],
        "exit_reasons": dict(Counter(r["exit"] for r in failed)),
        "tool_errors": tool_errors,
        "runs_without_recorded_exit": sum(
            1 for r in ix.runs if r["status"] == "unknown_exit"),
        "note": ("no experience yet" if not ix.runs else
                 "unknown_exit runs predate the Phase-3 outcome record — "
                 "their exit is unrecorded, not hidden"),
    }


def q_escalations(ix: ExperienceIndex) -> dict:
    """When did I escalate, did I recover, and what did the verifier say?"""
    events = []
    for r in ix.runs:
        for esc in r["escalations"]:
            events.append({
                "run_id": r["run_id"], "ts": r["ts"],
                "failed_exit": esc.get("failed_exit"),
                "recovered": bool(esc.get("recovered")),
                "recovered_by": _winner(esc) if esc.get("recovered") else None,
                "verifier": esc.get("verifier"),
                "best_score": esc.get("best_score"),
                "engine": esc.get("engine"), "budget_used": esc.get("budget_used"),
                "error": esc.get("error"),
            })
    attempted = len(events)
    recovered = sum(1 for e in events if e["recovered"])
    return {
        "schema_version": SCHEMA, "query": "escalations",
        "runs_scanned": len(ix.runs), "attempted": attempted,
        "recovered": recovered,
        "recovery_rate": round(recovered / attempted, 4) if attempted else None,
        "events": events,
        "note": "no escalation experience yet" if not attempted else "",
    }


def q_by_goal(ix: ExperienceIndex, substr: str) -> dict:
    """Which runs' experience mentions <substr>? goal_hint match is authoritative
    (Phase-3 logs); otherwise best-effort over text already in the log."""
    needle = substr.lower()
    matches = []
    for r in ix.runs:
        if needle in r["goal_hint"].lower():
            matches.append({**_run_brief(r), "matched_in": "goal_hint"})
        elif needle in r["_search"]:
            matches.append({**_run_brief(r), "matched_in": "log_text"})
    return {"schema_version": SCHEMA, "query": "by-goal", "substr": substr,
            "runs_scanned": len(ix.runs), "matches": matches}


def q_provider_recovery(ix: ExperienceIndex) -> dict:
    """Which substrate recovered my failures?"""
    recovered_by: Counter = Counter()
    providers: dict[str, dict] = {}
    attempted = 0
    for r in ix.runs:
        for esc in r["escalations"]:
            attempted += 1
            if esc.get("recovered"):
                w = _winner(esc)
                if w:
                    recovered_by[w] += 1
            for g, d in _providers_from(esc).items():
                agg = providers.setdefault(
                    g, {"generations": 0, "successes": 0, "best_score": 0.0})
                agg["generations"] += d["generations"]
                agg["successes"] += d["successes"]
                agg["best_score"] = max(agg["best_score"], d["best_score"])
    return {
        "schema_version": SCHEMA, "query": "provider-recovery",
        "runs_scanned": len(ix.runs), "escalations": attempted,
        "recovered_by": dict(recovered_by), "providers": providers,
        "note": "no escalation experience yet" if not attempted else "",
    }


def q_summary(ix: ExperienceIndex) -> dict:
    """Counts, escalation recovery-rate, verifier catch-rate, tamper root."""
    exits = Counter(r["exit"] if r["exit"] is not None else "unknown"
                    for r in ix.runs)
    tools: Counter = Counter()
    for r in ix.runs:
        tools.update(r["tools"])
    esc = q_escalations(ix)
    gate_checks = sum(r["gate_checks"] for r in ix.runs)
    gate_rej = sum(r["gate_rejections"] for r in ix.runs)
    return {
        "schema_version": SCHEMA, "query": "summary",
        "runs_dir": str(ix.runs_dir),
        "no_experience": not ix.runs,
        "runs": len(ix.runs), "entries": ix.entries,
        "malformed_lines": ix.malformed,
        "first_ts": ix.runs[0]["ts"] if ix.runs else None,
        "last_ts": ix.runs[-1]["ts"] if ix.runs else None,
        "agents": dict(Counter(r["agent"] for r in ix.runs if r["agent"])),
        "total_turns": sum(r["turns"] for r in ix.runs),
        "total_tool_calls": sum(r["tool_calls"] for r in ix.runs),
        "top_tools": tools.most_common(8),
        "run_exits": dict(exits),
        "tool_error_count": sum(len(r["tool_errors"]) for r in ix.runs),
        "escalation": {"attempted": esc["attempted"], "recovered": esc["recovered"],
                       "recovery_rate": esc["recovery_rate"]},
        # verifier catch-rate = epistemic-gate rejections / gate checks (the gate
        # IS the in-loop verifier). None = the gate never ran, not "perfect".
        "verifier_gate": {
            "checks": gate_checks, "rejections": gate_rej,
            "catch_rate": round(gate_rej / gate_checks, 4) if gate_checks else None},
        "merkle_root": ix.root,
        "note": "no experience yet — run organic goals to grow the self-record"
                if not ix.runs else "",
    }


# -- CLI -----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Query the organism's continuous experience (run logs).")
    ap.add_argument("--runs-dir", default=str(RUNS))
    ap.add_argument("--manifest", default=str(MANIFEST))
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query", help="query the experience index")
    q.add_argument("what", choices=["summary", "failures", "escalations",
                                    "provider-recovery", "by-goal"])
    q.add_argument("substr", nargs="?", help="substring for by-goal")
    sub.add_parser("root", help="print the current Merkle root")
    sub.add_parser("pin", help="append the current root to the manifest")
    sub.add_parser("verify", help="append-only check against the last pin")
    args = ap.parse_args(argv)

    ix = ExperienceIndex(args.runs_dir)
    if args.cmd == "query":
        if args.what == "by-goal":
            if not args.substr:
                print("by-goal needs a substring: query by-goal <substr>")
                return 2
            out = q_by_goal(ix, args.substr)
        else:
            out = {"summary": q_summary, "failures": q_failures,
                   "escalations": q_escalations,
                   "provider-recovery": q_provider_recovery}[args.what](ix)
    elif args.cmd == "root":
        out = {"schema_version": SCHEMA, "merkle_root": ix.root,
               "n_files": len(ix.file_leaves), "n_entries": ix.entries}
    elif args.cmd == "pin":
        out = ix.pin(args.manifest)
    else:
        out = ix.verify(args.manifest)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
