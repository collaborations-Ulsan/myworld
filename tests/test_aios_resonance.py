"""Organism assembly Phase 8 — the RESONANCE organ (scripts/aios_resonance.py).

Proves the self-questioning loop behaves, not vibes:

  - questions are harvested from each of the 4 existing organ inflows
    (ontology contradictions / DRIVE dominant pain / experience failures /
    repeated failures with no covering skill)
  - the SAME contradiction yields the SAME qid across runs (stability) and
    a changed ref yields a different qid
  - amplitude RISES with recurrence and with multi-organ arrival, FALLS
    when a question is settled; ranking is amplitude-ordered
  - ANTI-RUMINATION: a qid asked 3x with no behavioral change is retired
    (status retired_rumination) and excluded from the next harvest; a
    behavioral change or a changed ref escapes retirement
  - resonance_report computes question_resolution_rate + rumination_count
    and emits the RUMINATION verdict at ~0 resolution over a real sample
  - routing names an existing organ (with a concrete invocation) per kind
  - empty/missing inputs degrade honestly, never crash
  - DRIVE wiring: one heartbeat both FEELS and ASKS — the pulse record
    gains a questions section; resonance failure degrades, never breaks
    the pulse

All fixtures are offline and deterministic — no network, no LLM, no daemon.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_drive as D
import aios_resonance as R

NOW = 1_800_000_000.0   # fixed clock (the modules never read the real one)


# -- fixture builders ---------------------------------------------------------

def _ontology(path: Path, edges: list[tuple[str, str]],
              names: dict[str, str] | None = None) -> Path:
    ids = sorted({n for e in edges for n in e})
    ents = [{"id": i, "type": "Claim", "name": (names or {}).get(i, "")}
            for i in ids]
    rels = [{"src_id": s, "rel": "contradicts", "dst_id": d,
             "source": ["test"], "domain": ["D1"]} for s, d in edges]
    path.write_text(json.dumps({
        "entities": ents, "relations": rels,
        "stats": {"contradicts_count": len(edges), "total_entities": len(ids)},
    }), encoding="utf-8")
    return path


def _run(dirp: Path, run_id: str, exit_: str, goal: str = "") -> Path:
    p = dirp / f"{run_id}.jsonl"
    recs = [{"kind": "session_meta", "run_id": run_id, "agent": "codex@test",
             "git_sha": "abc", "ts": "2026-07-01T00:00:00+00:00"},
            {"kind": "outcome", "exit": exit_, "turns": 3, "goal_hint": goal}]
    with p.open("w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    return p


def _registry(path: Path, skills: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for s in skills:
            fh.write(json.dumps(s) + "\n")
    return path


STATE = {"pain": 0.4, "contradicts_count": 2, "unresolved_failures": 2,
         "n_skills": 1, "last_pin_ts": 100.0}


def _pulse_rec(asked: list[dict], state: dict | None = None,
               components: dict | None = None, ts: float = NOW) -> dict:
    """A drive_pulse-shaped history record carrying a questions section."""
    rec = {"schema": "aios.drive.v1", "kind": "drive_pulse", "ts": ts,
           "state": dict(STATE) if state is None else state,
           "questions": {"available": True, "asked": asked}}
    if components is not None:
        rec["components"] = components
    return rec


def _ask(qid: str, kind: str = "contradiction", organ: str = "ontology",
         status: str = "open") -> dict:
    return {"qid": qid, "kind": kind, "organ": organ, "status": status}


class ResonanceBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.ont = self.root / "_merged.json"
        self.reg = self.root / "skills" / "registry.jsonl"
        self.plog = self.runs / "drive-pulses.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def signals(self):
        return R.gather_signals(ontology=self.ont, runs_dir=self.runs)

    def state(self, dominant="failures"):
        return {"dominant": dominant}

    def full_inflow(self):
        """All 4 sources hot: 2 contradictions, a goal failing twice with no
        covering skill, dominant pain = failures."""
        _ontology(self.ont, [("claim:a", "claim:b"), ("claim:c", "claim:d")],
                  names={"claim:a": "reward is enough",
                         "claim:b": "reward is not enough"})
        _run(self.runs, "r-f1", "no_sampler", "fetch weather data")
        _run(self.runs, "r-f2", "no_sampler", "fetch weather data")
        _registry(self.reg, [{"id": "s1", "name": "csv_parse",
                              "applicability": "use when: parse csv rows",
                              "code": "def parse(): pass"}])


# -- harvest: 4 sources -------------------------------------------------------

class TestHarvest(ResonanceBase):
    def test_questions_harvested_from_all_four_sources(self):
        self.full_inflow()
        qs = R.harvest_questions(self.signals(), self.state(), now=NOW,
                                 skills_registry=self.reg)
        by_kind = {}
        for q in qs:
            by_kind.setdefault(q["kind"], []).append(q)
        self.assertEqual(len(by_kind["contradiction"]), 2)
        self.assertEqual(len(by_kind["pain"]), 1)
        self.assertEqual(len(by_kind["failure"]), 1)
        self.assertEqual(len(by_kind["gap"]), 1)
        organs = {q["kind"]: q["organ"] for q in qs}
        self.assertEqual(organs, {"contradiction": "ontology", "pain": "drive",
                                  "failure": "experience", "gap": "skills"})
        # readable text uses the entity NAME when present
        self.assertIn("reward is enough", by_kind["contradiction"][0]["q"])
        # every question carries the required fields
        for q in qs:
            for key in ("qid", "kind", "q", "refs", "organ"):
                self.assertIn(key, q)

    def test_covering_skill_suppresses_gap_question(self):
        self.full_inflow()
        _registry(self.reg, [{"id": "s2", "name": "fetch_weather",
                              "applicability": "use when: fetch weather data",
                              "code": "def fetch_weather(): pass"}])
        qs = R.harvest_questions(self.signals(), self.state(), now=NOW,
                                 skills_registry=self.reg)
        self.assertNotIn("gap", {q["kind"] for q in qs})
        self.assertIn("failure", {q["kind"] for q in qs})

    def test_single_failure_no_gap_question(self):
        _ontology(self.ont, [])
        _run(self.runs, "r-f1", "no_sampler", "one-off goal")
        qs = R.harvest_questions(self.signals(), self.state(None), now=NOW,
                                 skills_registry=self.reg)
        kinds = {q["kind"] for q in qs}
        self.assertEqual(kinds, {"failure"})   # < GAP_MIN_FAILURES -> no gap


# -- qid: stable, content-addressed -------------------------------------------

class TestQidStability(ResonanceBase):
    def test_same_contradiction_same_qid_across_runs(self):
        self.full_inflow()
        q1 = R.harvest_questions(self.signals(), self.state(), now=NOW,
                                 skills_registry=self.reg)
        q2 = R.harvest_questions(self.signals(), self.state(), now=NOW + 999,
                                 skills_registry=self.reg)
        ids1 = sorted(q["qid"] for q in q1)
        ids2 = sorted(q["qid"] for q in q2)
        self.assertEqual(ids1, ids2)

    def test_direction_flip_is_the_same_question(self):
        self.assertEqual(R.qid_for("contradiction", ["claim:a", "claim:b"]),
                         R.qid_for("contradiction", ["claim:b", "claim:a"]))

    def test_changed_ref_changes_qid(self):
        self.assertNotEqual(R.qid_for("contradiction", ["claim:a", "claim:b"]),
                            R.qid_for("contradiction", ["claim:a", "claim:c"]))
        self.assertNotEqual(R.qid_for("failure", ["goal x"]),
                            R.qid_for("gap", ["goal x"]))   # kind is identity too


# -- resonance: amplification + damping ---------------------------------------

class TestAmplitude(ResonanceBase):
    Q = {"qid": "q:x", "kind": "contradiction", "organ": "ontology",
         "refs": ["claim:a", "claim:b"], "q": "Which holds?",
         "on_dominant": False}

    def test_amplitude_rises_with_recurrence(self):
        amp0 = R.resonate([dict(self.Q)], [], now=NOW)[0]["amplitude"]
        hist = [_pulse_rec([_ask("q:x")]), _pulse_rec([_ask("q:x")])]
        amp2 = R.resonate([dict(self.Q)], hist, now=NOW)[0]["amplitude"]
        self.assertGreater(amp2, amp0)
        self.assertEqual(
            R.resonate([dict(self.Q)], hist, now=NOW)[0]
            ["amplitude_parts"]["recurrence"], 2.0)

    def test_amplitude_rises_with_multi_organ_arrival(self):
        fail = {"qid": "q:f", "kind": "failure", "organ": "experience",
                "refs": ["goal g"], "q": "Why failing?", "on_dominant": False}
        gap = {"qid": "q:g", "kind": "gap", "organ": "skills",
               "refs": ["goal g"], "q": "What tool missing?",
               "on_dominant": False}
        alone = R.resonate([dict(fail)], [], now=NOW)[0]["amplitude"]
        together = {q["qid"]: q for q in R.resonate([dict(fail), dict(gap)],
                                                    [], now=NOW)}
        self.assertGreater(together["q:f"]["amplitude"], alone)
        self.assertEqual(together["q:f"]["amplitude_parts"]["multi_organ"], 1.0)

    def test_amplitude_falls_when_settled(self):
        recurring = [_pulse_rec([_ask("q:x")]), _pulse_rec([_ask("q:x")])]
        # asked once, then a later pulse did NOT raise it -> settled, damped
        lapsed = [_pulse_rec([_ask("q:x")]), _pulse_rec([_ask("q:other")])]
        amp_rec = R.resonate([dict(self.Q)], recurring, now=NOW)[0]
        amp_lap = R.resonate([dict(self.Q)], lapsed, now=NOW)[0]
        self.assertFalse(amp_rec["settled"])
        self.assertTrue(amp_lap["settled"])
        self.assertLess(amp_lap["amplitude"], amp_rec["amplitude"])
        self.assertEqual(amp_lap["amplitude_parts"]["damping"],
                         R.AMP_SETTLED_DAMPING)

    def test_dominant_pain_bonus(self):
        on = dict(self.Q, on_dominant=True)
        off = dict(self.Q, on_dominant=False)
        self.assertEqual(
            R.resonate([on], [], now=NOW)[0]["amplitude"]
            - R.resonate([off], [], now=NOW)[0]["amplitude"],
            R.AMP_DOMINANT_BONUS)

    def test_ranking_is_amplitude_ordered(self):
        self.full_inflow()
        hist = []
        out = R.cycle(self.signals(), self.state(), hist, now=NOW,
                      skills_registry=self.reg)
        amps = [q["amplitude"] for q in out["top"]]
        self.assertEqual(amps, sorted(amps, reverse=True))
        # failure+gap share refs (2 organs) -> they outrank lone contradictions
        self.assertIn(out["top"][0]["kind"], {"failure", "gap"})


# -- anti-rumination: the load-bearing damper ---------------------------------

class TestRumination(ResonanceBase):
    def _hist_no_change(self, qid: str, n: int = 3) -> list[dict]:
        return [_pulse_rec([_ask(qid)]) for _ in range(n)]

    def test_asked_3x_no_change_is_retired_and_then_excluded(self):
        self.full_inflow()
        qs = R.harvest_questions(self.signals(), self.state(), now=NOW,
                                 skills_registry=self.reg)
        qid = next(q["qid"] for q in qs if q["kind"] == "contradiction")
        hist = self._hist_no_change(qid, R.RUMINATION_N)
        out = R.cycle(self.signals(), self.state(), hist, now=NOW,
                      skills_registry=self.reg)
        retired = {q["qid"]: q for q in out["retired"]}
        self.assertIn(qid, retired)                       # forcibly RETIRED
        self.assertEqual(retired[qid]["status"], "retired_rumination")
        self.assertEqual(retired[qid]["asked_n"], R.RUMINATION_N)
        self.assertTrue(retired[qid]["reason"])
        self.assertNotIn(qid, {q["qid"] for q in out["top"]})   # never routed
        # the retirement is on the record; the NEXT harvest excludes it
        hist2 = hist + [_pulse_rec(out["asked"])]
        out2 = R.cycle(self.signals(), self.state(), hist2, now=NOW + 60,
                       skills_registry=self.reg)
        asked2 = {q["qid"] for q in out2["asked"]}
        self.assertNotIn(qid, asked2)                     # EXCLUDED entirely
        self.assertGreaterEqual(out2["n_excluded_retired"], 1)

    def test_behavioral_change_escapes_retirement(self):
        qid = R.qid_for("contradiction", ["claim:a", "claim:b"])
        hist = self._hist_no_change(qid, 3)
        # a contradiction was resolved between first ask and the latest pulse
        hist[-1]["state"] = dict(STATE, contradicts_count=1)
        rc = R.rumination_check(qid, hist)
        self.assertFalse(rc["ruminating"])
        self.assertIn("contradiction_resolved", rc["behavior_changes"])

    def test_pin_advance_alone_does_not_escape_retirement(self):
        qid = "q:pinonly"
        hist = self._hist_no_change(qid, 3)
        hist[-1]["state"] = dict(STATE, last_pin_ts=999.0)   # bookkeeping only
        rc = R.rumination_check(qid, hist)
        self.assertTrue(rc["ruminating"])                 # pinning answers nothing

    def test_under_n_asks_not_retired(self):
        qid = "q:young"
        rc = R.rumination_check(qid, self._hist_no_change(qid, 2))
        self.assertFalse(rc["ruminating"])
        self.assertEqual(rc["asked_n"], 2)

    def test_changed_ref_is_a_new_question_and_escapes_exclusion(self):
        self.full_inflow()
        qs = R.harvest_questions(self.signals(), self.state(), now=NOW,
                                 skills_registry=self.reg)
        qid_ab = next(q["qid"] for q in qs if q["refs"] == ["claim:a", "claim:b"])
        hist = self._hist_no_change(qid_ab, 3)
        hist.append(_pulse_rec([_ask(qid_ab, status="retired_rumination")]))
        # the edge's ref changes: a<->b becomes a<->e -> different qid, harvested
        _ontology(self.ont, [("claim:a", "claim:e"), ("claim:c", "claim:d")])
        out = R.cycle(self.signals(), self.state(), hist, now=NOW,
                      skills_registry=self.reg)
        asked = {q["qid"] for q in out["asked"]}
        self.assertNotIn(qid_ab, asked)                   # old qid stays retired
        self.assertIn(R.qid_for("contradiction",
                                sorted(["claim:a", "claim:e"])), asked)


# -- routing: name the existing organ -----------------------------------------

class TestRouting(unittest.TestCase):
    def test_each_kind_routes_to_an_existing_organ(self):
        cases = {
            "contradiction": ("memory.retrieve", ["claim:a", "claim:b"]),
            "failure": ("escalate+verifier", ["goal g"]),
            "gap": ("operator", ["goal g"]),
            "pain": ("genesis.challenge", ["failures"]),
        }
        for kind, (organ, refs) in cases.items():
            r = R.route({"kind": kind, "refs": refs})
            self.assertEqual(r["organ"], organ, kind)
            self.assertTrue(r["invocation"], kind)        # concrete suggestion
        self.assertEqual(R.route({"kind": "???", "refs": []})["organ"],
                         "operator")                      # unknown -> surface


# -- report: resolution rate + the rumination verdict -------------------------

class TestReport(unittest.TestCase):
    def test_resolution_rate_counts_ref_change(self):
        # pulse1 asks A,B,C; latest asks only B -> A,C resolved; B standing
        hist = [
            _pulse_rec([_ask("q:A"), _ask("q:B"), _ask("q:C")]),
            _pulse_rec([_ask("q:B")],
                       components={"contradictions": {"available": True}}),
        ]
        rep = R.resonance_report(hist)
        self.assertEqual(rep["resolved"], 2)
        self.assertEqual(rep["standing"], 1)
        self.assertEqual(rep["question_resolution_rate"], round(2 / 3, 4))
        self.assertEqual(rep["rumination_count"], 0)
        self.assertNotIn("RUMINATION", rep["verdict"])

    def test_organ_going_dark_is_not_resolution(self):
        hist = [
            _pulse_rec([_ask("q:A")]),
            _pulse_rec([],
                       components={"contradictions": {"available": False}}),
        ]
        rep = R.resonance_report(hist)
        self.assertEqual(rep["resolved"], 0)
        self.assertEqual(rep["unobservable"], 1)

    def test_rumination_verdict_at_zero_resolution(self):
        asked = [_ask("q:A"), _ask("q:B"), _ask("q:C")]
        hist = [_pulse_rec(list(asked)) for _ in range(4)]
        rep = R.resonance_report(hist)
        self.assertEqual(rep["question_resolution_rate"], 0.0)
        self.assertIn("RUMINATION", rep["verdict"])
        # retired questions count into rumination_count
        hist2 = hist + [_pulse_rec(
            [_ask("q:A", status="retired_rumination"), _ask("q:B"), _ask("q:C")])]
        rep2 = R.resonance_report(hist2)
        self.assertEqual(rep2["rumination_count"], 1)

    def test_empty_history_is_honest(self):
        rep = R.resonance_report([])
        self.assertIsNone(rep["question_resolution_rate"])
        self.assertIn("never asked", rep["verdict"])
        # pre-Phase-8 pulses (no questions section) are not question-bearing
        rep2 = R.resonance_report([{"kind": "drive_pulse", "ts": NOW}])
        self.assertEqual(rep2["pulses_with_questions"], 0)


# -- honest degradation -------------------------------------------------------

class TestHonestDegradation(ResonanceBase):
    def test_all_missing_inputs_no_questions_no_crash(self):
        out = R.cycle(R.gather_signals(ontology=self.root / "no.json",
                                       runs_dir=self.root / "no-runs"),
                      {"dominant": None}, [], now=NOW,
                      skills_registry=self.root / "no-reg.jsonl")
        self.assertEqual(out["n_harvested"], 0)
        self.assertEqual(out["top"], [])
        self.assertIn("no questions", out["note"])

    def test_corrupt_ontology_degrades(self):
        self.ont.write_text("{not json", encoding="utf-8")
        sig = self.signals()
        self.assertFalse(sig["ontology"]["available"])
        qs = R.harvest_questions(sig, {"dominant": None}, now=NOW,
                                 skills_registry=self.reg)
        self.assertEqual(qs, [])


# -- DRIVE wiring: one heartbeat FEELS and ASKS -------------------------------

class TestDriveWiring(ResonanceBase):
    def drive_paths(self):
        man = self.root / "exp" / "manifest.jsonl"
        man.parent.mkdir(parents=True, exist_ok=True)
        import datetime as dt
        iso = dt.datetime.fromtimestamp(
            NOW - 60, tz=dt.timezone.utc).isoformat(timespec="seconds")
        man.write_text(json.dumps({"schema_version": "aios.experience.v1",
                                   "ts": iso, "n_entries": 1,
                                   "merkle_root": "sha256:x",
                                   "files": {}}) + "\n", encoding="utf-8")
        return dict(ontology=self.ont, runs_dir=self.runs,
                    exp_manifest=man, skills_registry=self.reg)

    def test_pulse_record_carries_questions_and_recurrence_grows(self):
        self.full_inflow()
        for i in range(20):   # make it hurt (over threshold)
            _run(self.runs, f"r-x{i}", "no_sampler", "fetch weather data")
        paths = self.drive_paths()
        rec1 = D.pulse(NOW, pulse_log=self.plog, **paths)
        q1 = rec1["questions"]
        self.assertTrue(q1["available"])
        self.assertGreater(q1["n_open"], 0)
        self.assertLessEqual(len(q1["top"]), R.TOP_K)
        for q in q1["top"]:
            for key in ("qid", "amplitude", "route", "status"):
                self.assertIn(key, q)
        # still exactly one appended record per pulse
        lines = [l for l in self.plog.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        # second heartbeat: same standing questions now RESONATE (recurrence)
        rec2 = D.pulse(NOW + 3600, pulse_log=self.plog, **paths)
        top1 = {q["qid"]: q["amplitude"] for q in q1["top"]}
        gained = [q for q in rec2["questions"]["top"]
                  if q["qid"] in top1 and q["amplitude"] > top1[q["qid"]]]
        self.assertTrue(gained)
        # the questions' fates are readable from the SAME append-only log
        hist = R.read_history(self.plog)
        self.assertEqual(len(R._bearing(hist)), 2)

    def test_resonance_failure_degrades_pulse_survives(self):
        self.full_inflow()
        for i in range(20):
            _run(self.runs, f"r-x{i}", "no_sampler", "fetch weather data")
        paths = self.drive_paths()
        saved = sys.modules.get("aios_resonance")
        sys.modules["aios_resonance"] = None   # forces ImportError in pulse()
        try:
            rec = D.pulse(NOW, pulse_log=self.plog, **paths)
        finally:
            sys.modules["aios_resonance"] = saved
        self.assertFalse(rec["questions"]["available"])
        self.assertIn("resonance unavailable", rec["questions"]["note"])
        self.assertTrue(rec["over_threshold"])            # FEEL still works
        self.assertGreater(len(rec["proposals"]), 0)


# -- CLI smoke (read-only) ----------------------------------------------------

class TestCLI(ResonanceBase):
    def _main(self, *argv) -> dict:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = R.main(["--ontology", str(self.ont),
                         "--runs-dir", str(self.runs),
                         "--exp-manifest", str(self.root / "exp" / "m.jsonl"),
                         "--skills-registry", str(self.reg),
                         "--pulse-log", str(self.plog), *argv])
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def test_ask_standing_report_roundtrip(self):
        self.full_inflow()
        out = self._main("ask")
        self.assertTrue(out["available"])
        self.assertGreater(out["n_harvested"], 0)
        self.assertFalse(self.plog.exists())              # ask records NOTHING
        standing = self._main("standing")
        self.assertEqual(standing["pulses_with_questions"], 0)
        rep = self._main("report")
        self.assertIsNone(rep["question_resolution_rate"])
        self.assertIn("never asked", rep["verdict"])


if __name__ == "__main__":
    unittest.main()
