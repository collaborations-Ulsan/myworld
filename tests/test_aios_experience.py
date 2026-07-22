"""Organism assembly Phase 3 — Sovereign Experience Graph (scripts/aios_experience.py).

Proves the organism can query its OWN continuous experience from real-shaped
run_log JSONL (scripts/aios_run_log.py records: session_meta / turn_context /
trajectory / kind:"escalation" / kind:"outcome"):

  - ingest -> failures / escalations / by-goal / provider-recovery / summary
    return correct results (behavior, not vibes)
  - Merkle root deterministic + tamper-sensitive (mutate one entry -> root changes)
  - append-only pin/verify: appended lines are OK, a rewritten / truncated /
    deleted past entry is a named violation; the manifest itself only grows
  - empty run_log dir degrades honestly ("no experience yet"), never crashes
  - head wiring: aios_head._log_experience_outcome writes the one-line outcome
    record and aios_run_log.reconstruct still works (additive, non-breaking)

All fixtures are offline and deterministic — no network, no model.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import sys

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_experience as X


def _write(dirp: Path, run_id: str, records: list[dict]) -> Path:
    p = dirp / f"{run_id}.jsonl"
    with p.open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p


def _meta(run_id: str, ts: str) -> dict:
    return {"kind": "session_meta", "run_id": run_id, "agent": "codex@myworld",
            "cwd": "/x", "git_sha": "abc1234", "forked_from": "", "ts": ts}


RUN_A = [  # success, Phase-3 outcome record with goal_hint
    _meta("organic-A", "2026-07-20T01:00:00+00:00"),
    {"kind": "turn_context", "turn": 1, "agent": "codex@myworld"},
    {"kind": "trajectory", "turn": 1, "call_id": "", "tool": "memory.retrieve",
     "decision": "allow", "status": "ok", "result": {"hits": 3, "top": "memo"}},
    {"kind": "turn_context", "turn": 2, "agent": "codex@myworld"},
    {"kind": "trajectory", "turn": 2, "call_id": "", "tool": "web.search",
     "decision": "allow", "status": "ok", "result": {"abstract": "Seoul sunny"}},
    {"kind": "outcome", "exit": "model_finished", "turns": 2, "tool_calls": 2,
     "goal_hint": "서울 weather report"},
]

RUN_B = [  # failure (max_turns) -> escalation RECOVERED by ollama; gate ran twice
    _meta("organic-B", "2026-07-20T02:00:00+00:00"),
    {"kind": "turn_context", "turn": 1, "agent": "codex@myworld"},
    {"kind": "epistemic_gate", "turn": 1, "call_id": "c1", "tool": "self.audit",
     "verdict": "OK", "passed": True, "reasons": []},
    {"kind": "trajectory", "turn": 1, "call_id": "c1", "tool": "self.audit",
     "decision": "allow", "status": "ok"},
    {"kind": "turn_context", "turn": 2, "agent": "codex@myworld"},
    {"kind": "epistemic_gate", "turn": 2, "call_id": "c2", "tool": "fs.read",
     "verdict": "MISSPECIFIED", "passed": False, "reasons": ["bad args"]},
    {"kind": "trajectory", "turn": 2, "call_id": "c3", "tool": "fs.read",
     "decision": "allow", "status": "error"},
    {"kind": "escalation", "escalation_attempted": True, "recovered": True,
     "failed_exit": "max_turns", "verifier": "demo", "engine": "fallback",
     "budget_used": 3, "best_score": 0.8,
     "provenance": [
         {"id": 0, "generator": "claude", "score": 0.0, "parent_id": None,
          "ok": False, "error": "CLI missing"},
         {"id": 1, "generator": "ollama", "score": 0.8, "parent_id": None,
          "ok": True, "error": None},
         {"id": 2, "generator": "ollama", "score": 0.6, "parent_id": 1,
          "ok": True, "error": None}]},
    {"kind": "outcome", "exit": "max_turns", "turns": 2, "tool_calls": 2,
     "goal_hint": "fix the parser bug", "escalation_recovered": True},
]

RUN_C = [  # failure proven only by the escalation record (no outcome line)
    _meta("organic-C", "2026-07-20T03:00:00+00:00"),
    {"kind": "turn_context", "turn": 1, "agent": "codex@myworld"},
    {"kind": "trajectory", "turn": 1, "call_id": "", "tool": "self.audit",
     "decision": "allow", "status": "ok"},
    {"kind": "escalation", "escalation_attempted": True, "recovered": False,
     "failed_exit": "loop_detected", "verifier": "demo", "budget_used": 2,
     "error": "all_generators_down", "provider_breakdown": None,
     "provenance": [
         {"id": 0, "generator": "claude", "score": 0.0, "parent_id": None,
          "ok": False, "error": "down"},
         {"id": 1, "generator": "codex", "score": 0.0, "parent_id": None,
          "ok": False, "error": "down"}]},
]

RUN_D = [  # legacy pre-Phase-3 log: no outcome, no escalation -> unknown_exit
    _meta("organic-D", "2026-07-20T04:00:00+00:00"),
    {"kind": "turn_context", "turn": 1, "agent": "codex@myworld"},
    {"kind": "trajectory", "turn": 1, "call_id": "", "tool": "memory.retrieve",
     "decision": "allow", "status": "ok"},
]

N_ENTRIES = len(RUN_A) + len(RUN_B) + len(RUN_C) + len(RUN_D)  # 6+9+4+3 = 22


class ExperienceFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runs = Path(self._tmp.name) / "runs"
        self.runs.mkdir()
        self.manifest = Path(self._tmp.name) / "manifest.jsonl"
        for rid, recs in [("organic-A", RUN_A), ("organic-B", RUN_B),
                          ("organic-C", RUN_C), ("organic-D", RUN_D)]:
            _write(self.runs, rid, recs)
        self.ix = X.ExperienceIndex(self.runs)


class TestIngest(ExperienceFixture):
    def test_counts_and_run_shapes(self):
        self.assertEqual(len(self.ix.runs), 4)
        self.assertEqual(self.ix.entries, N_ENTRIES)
        self.assertEqual(self.ix.malformed, 0)
        by_id = {r["run_id"]: r for r in self.ix.runs}
        a = by_id["organic-A"]
        self.assertEqual((a["turns"], a["tool_calls"], a["status"], a["exit"]),
                         (2, 2, "success", "model_finished"))
        self.assertEqual(a["goal_hint"], "서울 weather report")
        self.assertEqual(by_id["organic-B"]["status"], "failure")
        c = by_id["organic-C"]
        self.assertEqual((c["exit"], c["exit_source"], c["status"]),
                         ("loop_detected", "escalation", "failure"))
        self.assertEqual(by_id["organic-D"]["status"], "unknown_exit")


class TestQueries(ExperienceFixture):
    def test_failures(self):
        out = X.q_failures(self.ix)
        failed_ids = {r["run_id"] for r in out["failed_runs"]}
        self.assertEqual(failed_ids, {"organic-B", "organic-C"})
        self.assertEqual(out["exit_reasons"],
                         {"max_turns": 1, "loop_detected": 1})
        self.assertEqual(out["runs_without_recorded_exit"], 1)
        self.assertEqual(out["tool_errors"],
                         [{"run_id": "organic-B", "turn": 2,
                           "tool": "fs.read", "status": "error"}])
        b = next(r for r in out["failed_runs"] if r["run_id"] == "organic-B")
        self.assertTrue(b["escalation"]["recovered"])
        self.assertEqual(b["escalation"]["recovered_by"], "ollama")

    def test_escalations(self):
        out = X.q_escalations(self.ix)
        self.assertEqual((out["attempted"], out["recovered"]), (2, 1))
        self.assertEqual(out["recovery_rate"], 0.5)
        ev = {e["run_id"]: e for e in out["events"]}
        self.assertEqual(ev["organic-B"]["verifier"], "demo")
        self.assertEqual(ev["organic-B"]["best_score"], 0.8)
        self.assertEqual(ev["organic-B"]["recovered_by"], "ollama")
        self.assertFalse(ev["organic-C"]["recovered"])
        self.assertEqual(ev["organic-C"]["error"], "all_generators_down")

    def test_by_goal(self):
        hits = X.q_by_goal(self.ix, "parser")["matches"]
        self.assertEqual([h["run_id"] for h in hits], ["organic-B"])
        self.assertEqual(hits[0]["matched_in"], "goal_hint")
        weather = X.q_by_goal(self.ix, "Weather")["matches"]  # case-insensitive
        self.assertIn("organic-A", [h["run_id"] for h in weather])
        self.assertEqual(X.q_by_goal(self.ix, "완전없는문자열")["matches"], [])

    def test_provider_recovery(self):
        out = X.q_provider_recovery(self.ix)
        self.assertEqual(out["recovered_by"], {"ollama": 1})
        self.assertEqual(out["providers"]["ollama"],
                         {"generations": 2, "successes": 2, "best_score": 0.8})
        self.assertEqual(out["providers"]["claude"]["generations"], 2)  # B + C
        self.assertEqual(out["providers"]["claude"]["successes"], 0)
        self.assertEqual(out["providers"]["codex"]["generations"], 1)

    def test_summary(self):
        out = X.q_summary(self.ix)
        self.assertFalse(out["no_experience"])
        self.assertEqual(out["runs"], 4)
        self.assertEqual(out["entries"], N_ENTRIES)
        self.assertEqual(out["run_exits"],
                         {"model_finished": 1, "max_turns": 1,
                          "loop_detected": 1, "unknown": 1})
        self.assertEqual(out["escalation"],
                         {"attempted": 2, "recovered": 1, "recovery_rate": 0.5})
        self.assertEqual(out["verifier_gate"],
                         {"checks": 2, "rejections": 1, "catch_rate": 0.5})
        self.assertEqual(out["tool_error_count"], 1)
        self.assertTrue(out["merkle_root"].startswith("sha256:"))


class TestTamperEvidence(ExperienceFixture):
    def test_merkle_deterministic(self):
        again = X.ExperienceIndex(self.runs)
        self.assertEqual(self.ix.root, again.root)
        self.assertEqual(self.ix.root, X.merkle_root(list(self.ix.leaf_hashes)))

    def test_merkle_tamper_sensitive(self):
        root_before = self.ix.root
        p = self.runs / "organic-B.jsonl"
        text = p.read_text(encoding="utf-8")
        mutated = text.replace('"recovered": true', '"recovered": false')
        self.assertNotEqual(text, mutated)  # the mutation really happened
        p.write_text(mutated, encoding="utf-8")
        after = X.ExperienceIndex(self.runs)
        self.assertEqual(after.entries, self.ix.entries)  # same size, changed bytes
        self.assertNotEqual(after.root, root_before)

    def test_pin_verify_append_only(self):
        self.ix.pin(self.manifest)
        self.assertEqual(
            len(self.manifest.read_text(encoding="utf-8").splitlines()), 1)

        # honest APPEND -> ok
        _write(self.runs, "organic-D",
               [{"kind": "outcome", "exit": "model_finished", "turns": 1,
                 "tool_calls": 1, "goal_hint": "late outcome"}])
        v = X.ExperienceIndex(self.runs).verify(self.manifest)
        self.assertEqual(v["status"], "ok")
        self.assertEqual(v["appended_entries"], 1)
        self.assertEqual(v["violations"], [])
        self.assertNotEqual(v["current_root"], v["pinned_root"])  # growth moves root

        # REWRITE a pinned line -> named violation
        pa = self.runs / "organic-A.jsonl"
        pa.write_text(pa.read_text(encoding="utf-8")
                      .replace("model_finished", "model_FORGED"),
                      encoding="utf-8")
        # TRUNCATE a pinned file -> named violation
        pb = self.runs / "organic-B.jsonl"
        pb.write_text("\n".join(
            pb.read_text(encoding="utf-8").splitlines()[:-1]) + "\n",
            encoding="utf-8")
        v2 = X.ExperienceIndex(self.runs).verify(self.manifest)
        self.assertEqual(v2["status"], "tampered")
        viol = {(x["run_id"], x["violation"]) for x in v2["violations"]}
        self.assertIn(("organic-A", "rewritten"), viol)
        self.assertIn(("organic-B", "truncated"), viol)

        # the manifest itself only grows (append-only): pin again -> 2 lines,
        # first line byte-identical
        first = self.manifest.read_text(encoding="utf-8").splitlines()[0]
        X.ExperienceIndex(self.runs).pin(self.manifest)
        lines = self.manifest.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], first)

    def test_verify_without_pin_is_honest(self):
        v = self.ix.verify(self.manifest)  # manifest never written
        self.assertEqual(v["status"], "no_pin")


class TestEmptyExperience(unittest.TestCase):
    def test_empty_and_missing_dir_degrade_honestly(self):
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td) / "runs"
            empty.mkdir()
            for d in (empty, Path(td) / "does-not-exist"):
                ix = X.ExperienceIndex(d)
                s = X.q_summary(ix)
                self.assertTrue(s["no_experience"])
                self.assertEqual(s["runs"], 0)
                self.assertIn("no experience yet", s["note"])
                self.assertEqual(ix.root, X.merkle_root([]))  # deterministic empty root
                self.assertEqual(X.q_failures(ix)["failed_runs"], [])
                self.assertEqual(X.q_escalations(ix)["recovery_rate"], None)
                self.assertEqual(X.q_by_goal(ix, "anything")["matches"], [])
                self.assertEqual(X.q_provider_recovery(ix)["recovered_by"], {})

    def test_malformed_lines_counted_not_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            runs = Path(td)
            p = runs / "organic-bad.jsonl"
            p.write_text('{"kind": "session_meta", "run_id": "organic-bad", '
                         '"agent": "a", "ts": "t"}\nNOT JSON AT ALL\n',
                         encoding="utf-8")
            ix = X.ExperienceIndex(runs)
            self.assertEqual(ix.malformed, 1)
            self.assertEqual(ix.entries, 2)  # malformed bytes still hashed


class TestCLI(ExperienceFixture):
    def test_cli_query_summary(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = X.main(["--runs-dir", str(self.runs), "query", "summary"])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["runs"], 4)

    def test_cli_by_goal_needs_substr(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = X.main(["--runs-dir", str(self.runs), "query", "by-goal"])
        self.assertEqual(rc, 2)


class TestHeadWiring(unittest.TestCase):
    """aios_head._log_experience_outcome -> run log -> experience index,
    end-to-end, and reconstruct() unaffected (additive record kind)."""

    def test_outcome_record_written_and_indexed(self):
        import aios_head as H
        import aios_run_log as rl
        with tempfile.TemporaryDirectory() as td:
            runs = Path(td)
            log = rl.RunLog(run_id="organic-wire", agent="codex@myworld",
                            runs_dir=runs)
            log.open(ts="2026-07-22T00:00:00+00:00")
            log.sink({"kind": "turn_context", "turn": 1})
            H._log_experience_outcome(
                log,
                {"exit": "max_turns", "turns": 1,
                 "trajectory": [{"tool": "self.audit"}],
                 "escalation": {"recovered": True}},
                "테스트 goal for wiring")
            recs = [json.loads(x) for x in
                    log.path.read_text(encoding="utf-8").splitlines()]
            outcome = [r for r in recs if r.get("kind") == "outcome"]
            self.assertEqual(len(outcome), 1)
            self.assertEqual(outcome[0]["exit"], "max_turns")
            self.assertEqual(outcome[0]["tool_calls"], 1)
            self.assertEqual(outcome[0]["goal_hint"], "테스트 goal for wiring")
            self.assertTrue(outcome[0]["escalation_recovered"])
            # non-breaking: reconstruct ignores the new kind
            state = rl.reconstruct(log.path)
            self.assertTrue(state["resumable"])
            self.assertEqual(state["run_id"], "organic-wire")
            # and the experience index reads it back as a failed run
            ix = X.ExperienceIndex(runs)
            self.assertEqual(ix.runs[0]["status"], "failure")
            self.assertEqual(ix.runs[0]["goal_hint"], "테스트 goal for wiring")

    def test_helper_never_raises(self):
        import aios_head as H

        class Boom:
            def sink(self, rec):
                raise RuntimeError("sink down")

        H._log_experience_outcome(Boom(), {"exit": "x"}, "g")  # must not raise


if __name__ == "__main__":
    unittest.main()
