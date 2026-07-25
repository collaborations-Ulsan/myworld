"""Organism assembly Phase 7 — the DRIVE organ (scripts/aios_drive.py).

Proves pain-triggered proaction behaves, not vibes:

  - pain RISES with more contradictions/failures and FALLS when they clear
  - threshold crossing triggers proposals; under threshold a pulse proposes
    nothing
  - a pulse appends EXACTLY ONE record and is dry-run by default (nothing is
    executed, no state file is touched)
  - proposals target the DOMINANT pain component, with measurable
    expected_effect
  - pulse_effect verifies true on concrete improvement and false on no change
    (the anti-theater gate)
  - report computes the verified-effect fraction (the kill criterion)
  - opt-in acting routes through the EXISTING experience pin organ and its
    effect is verified live
  - empty/missing inputs degrade honestly (pain 0.0 + "no signal"), never crash

All fixtures are offline and deterministic — no network, no model, no daemon.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_drive as D

NOW = 1_800_000_000.0   # fixed clock for pure tests (never read by the module)


# -- fixture builders ---------------------------------------------------------

def _ontology(path: Path, n_contradictions: int) -> Path:
    rels = [{"src_id": f"claim:a{i}", "rel": "contradicts",
             "dst_id": f"claim:b{i}", "source": ["test"], "domain": ["D1"]}
            for i in range(n_contradictions)]
    path.write_text(json.dumps({
        "entities": [], "relations": rels,
        "stats": {"contradicts_count": n_contradictions,
                  "total_entities": 100}}), encoding="utf-8")
    return path


def _run(dirp: Path, run_id: str, exit_: str, goal: str = "") -> Path:
    p = dirp / f"{run_id}.jsonl"
    recs = [{"kind": "session_meta", "run_id": run_id, "agent": "codex@test",
             "git_sha": "abc", "ts": f"2026-07-01T00:00:00+00:00"},
            {"kind": "outcome", "exit": exit_, "turns": 3, "goal_hint": goal}]
    with p.open("w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    return p


def _manifest(path: Path, iso_ts: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "aios.experience.v1",
                                "ts": iso_ts, "n_entries": 1,
                                "merkle_root": "sha256:x", "files": {}}) + "\n",
                    encoding="utf-8")
    return path


def _registry(path: Path, n_skills: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for i in range(n_skills):
            fh.write(json.dumps({"id": f"skill-{i}", "name": f"s{i}",
                                 "code": "def f(): pass"}) + "\n")
    return path


def _iso(epoch: float) -> str:
    import datetime as dt
    return dt.datetime.fromtimestamp(
        epoch, tz=dt.timezone.utc).isoformat(timespec="seconds")


class DriveBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.ont = self.root / "_merged.json"
        self.man = self.root / "exp" / "manifest.jsonl"
        self.reg = self.root / "skills" / "registry.jsonl"
        self.plog = self.root / "runs" / "drive-pulses.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def paths(self):
        return dict(ontology=self.ont, runs_dir=self.runs,
                    exp_manifest=self.man, skills_registry=self.reg)

    def calm(self):
        """Everything healthy: 0 contradictions, all-success runs, full skill
        coverage, fresh pin."""
        _ontology(self.ont, 0)
        _run(self.runs, "r-ok", "model_finished", "solved goal")
        _manifest(self.man, _iso(NOW - 60))            # pinned a minute ago
        _registry(self.reg, D.SKILL_COVERAGE_TARGET)

    def painful(self):
        """Over threshold with failures dominant: 20 failed runs, few
        contradictions, stale-ish pin, thin skills."""
        _ontology(self.ont, 10)
        for i in range(20):
            _run(self.runs, f"r-f{i}", "no_sampler", "fetch weather data")
        _manifest(self.man, _iso(NOW - 200 * 3600))    # 200h stale (past horizon)
        _registry(self.reg, 2)


# -- homeostasis: monotonicity ------------------------------------------------

class TestPainMonotonicity(DriveBase):
    def test_pain_rises_with_contradictions_and_falls_when_cleared(self):
        self.calm()
        p0 = D.homeostasis(NOW, **self.paths())["pain"]
        _ontology(self.ont, 10)
        p10 = D.homeostasis(NOW, **self.paths())["pain"]
        _ontology(self.ont, 100)
        p100 = D.homeostasis(NOW, **self.paths())["pain"]
        self.assertLess(p0, p10)
        self.assertLess(p10, p100)
        _ontology(self.ont, 0)                          # contradictions resolved
        self.assertEqual(D.homeostasis(NOW, **self.paths())["pain"], p0)

    def test_pain_rises_with_failures_and_falls_when_cleared(self):
        self.calm()
        p0 = D.homeostasis(NOW, **self.paths())["pain"]
        for i in range(3):
            _run(self.runs, f"r-f{i}", "no_sampler", "flaky goal")
        p_fail = D.homeostasis(NOW, **self.paths())["pain"]
        self.assertGreater(p_fail, p0)
        for i in range(3):                              # failures cleared
            _run(self.runs, f"r-f{i}", "model_finished", "flaky goal")
        self.assertEqual(D.homeostasis(NOW, **self.paths())["pain"], p0)

    def test_pain_rises_with_staleness(self):
        self.calm()
        p_fresh = D.homeostasis(NOW, **self.paths())["pain"]
        p_later = D.homeostasis(NOW + 100 * 3600, **self.paths())["pain"]
        self.assertGreater(p_later, p_fresh)


# -- threshold + proposals ----------------------------------------------------

class TestThresholdAndProposals(DriveBase):
    def test_under_threshold_pulse_proposes_nothing(self):
        self.calm()
        rec = D.pulse(NOW, pulse_log=self.plog, **self.paths())
        self.assertFalse(rec["over_threshold"])
        self.assertEqual(rec["proposals"], [])

    def test_over_threshold_pulse_emits_ranked_proposals(self):
        self.painful()
        rec = D.pulse(NOW, pulse_log=self.plog, **self.paths())
        self.assertTrue(rec["over_threshold"])
        self.assertGreater(len(rec["proposals"]), 0)
        for p in rec["proposals"]:
            for key in ("action", "target", "rationale", "expected_effect",
                        "component"):
                self.assertIn(key, p)

    def test_proposals_target_dominant_component(self):
        self.painful()
        state = D.homeostasis(NOW, **self.paths())
        self.assertEqual(state["dominant"], "failures")
        props = D.propose_actions(state)
        self.assertEqual(props[0]["component"], "failures")
        # repeated failing goal -> a skill-induction proposal for that class
        self.assertIn("induce_skill_for_task_class",
                      {p["action"] for p in props if p["component"] == "failures"})

    def test_dominant_staleness_proposes_re_pin_first(self):
        _ontology(self.ont, 10)
        _run(self.runs, "r-ok", "model_finished", "solved goal")
        _manifest(self.man, _iso(NOW - 300 * 3600))     # way past horizon
        _registry(self.reg, 2)
        state = D.homeostasis(NOW, **self.paths())
        self.assertEqual(state["dominant"], "staleness")
        props = D.propose_actions(state)
        self.assertEqual(props[0]["action"], "re_pin_experience")


# -- pulse: append-exactly-one + dry-run default ------------------------------

class TestPulseDryRun(DriveBase):
    def test_pulse_appends_exactly_one_record_and_executes_nothing(self):
        self.painful()
        before = {p: p.read_bytes() for p in (self.ont, self.man, self.reg)}
        rec = D.pulse(NOW, pulse_log=self.plog, **self.paths())
        self.assertTrue(rec["dry_run"])                 # dry-run is the DEFAULT
        self.assertEqual(rec["executed"], [])           # NOTHING was executed
        self.assertIsNone(rec["acted_effect"])
        for p, blob in before.items():                  # no state file touched
            self.assertEqual(p.read_bytes(), blob)
        lines = [l for l in self.plog.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)                 # exactly one record
        self.assertEqual(json.loads(lines[0])["kind"], "drive_pulse")
        D.pulse(NOW + 60, pulse_log=self.plog, **self.paths())
        lines = [l for l in self.plog.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)

    def test_first_pulse_effect_is_unknown_not_false(self):
        self.painful()
        rec = D.pulse(NOW, pulse_log=self.plog, **self.paths())
        self.assertIsNone(rec["effect_verified"])       # nothing to compare yet
        self.assertIsNone(rec["effect_since_last"])


# -- pulse_effect: the anti-theater gate --------------------------------------

class TestPulseEffect(unittest.TestCase):
    BEFORE = {"pain": 0.4, "contradicts_count": 72, "unresolved_failures": 2,
              "n_skills": 1, "last_pin_ts": 100.0}

    def test_verified_true_on_concrete_improvement(self):
        after = dict(self.BEFORE, contradicts_count=71, pain=0.39)
        eff = D.pulse_effect(self.BEFORE, after)
        self.assertTrue(eff["effect_verified"])
        self.assertEqual(eff["changes"], ["contradiction_resolved"])
        eff2 = D.pulse_effect(self.BEFORE,
                              dict(self.BEFORE, unresolved_failures=0,
                                   n_skills=2, last_pin_ts=200.0))
        self.assertTrue(eff2["effect_verified"])
        self.assertEqual(set(eff2["changes"]),
                         {"failure_cleared", "skill_registered", "pin_advanced"})

    def test_verified_false_when_nothing_changed(self):
        eff = D.pulse_effect(self.BEFORE, dict(self.BEFORE))
        self.assertFalse(eff["effect_verified"])
        self.assertEqual(eff["changes"], [])
        # things getting WORSE is not an effect either
        worse = dict(self.BEFORE, contradicts_count=80, unresolved_failures=5)
        self.assertFalse(D.pulse_effect(self.BEFORE, worse)["effect_verified"])

    def test_no_signal_axes_cannot_verify(self):
        before = {"pain": None, "contradicts_count": None,
                  "unresolved_failures": None, "n_skills": None,
                  "last_pin_ts": None}
        eff = D.pulse_effect(before, dict(before))
        self.assertFalse(eff["effect_verified"])

    def test_second_pulse_verifies_improvement_between_pulses(self):
        base = DriveBase()
        base.setUp()
        try:
            base.painful()
            D.pulse(NOW, pulse_log=base.plog, **base.paths())
            # operator resolves contradictions + clears one failure between pulses
            _ontology(base.ont, 4)
            _run(base.runs, "r-f0", "model_finished", "fetch weather data")
            rec2 = D.pulse(NOW + 3600, pulse_log=base.plog, **base.paths())
            self.assertTrue(rec2["effect_verified"])
            self.assertIn("contradiction_resolved",
                          rec2["effect_since_last"]["changes"])
            self.assertIn("failure_cleared", rec2["effect_since_last"]["changes"])
            # third pulse with NO change in between -> verified false
            rec3 = D.pulse(NOW + 7200, pulse_log=base.plog, **base.paths())
            self.assertFalse(rec3["effect_verified"])
        finally:
            base.tearDown()


# -- report: the kill criterion -----------------------------------------------

class TestReport(DriveBase):
    def _fake_pulse(self, effect, over=True, executed=()):
        return {"schema": D.SCHEMA, "kind": "drive_pulse", "ts": NOW,
                "ts_iso": _iso(NOW), "pain": 0.4, "over_threshold": over,
                "executed": list(executed), "effect_verified": effect}

    def test_report_computes_verified_effect_fraction(self):
        self.plog.parent.mkdir(parents=True, exist_ok=True)
        recs = [self._fake_pulse(None), self._fake_pulse(True),
                self._fake_pulse(False), self._fake_pulse(False),
                self._fake_pulse(True)]
        with self.plog.open("w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
        rep = D.report(self.plog)
        self.assertEqual(rep["pulses"], 5)
        self.assertEqual(rep["fired_over_threshold"], 5)
        self.assertEqual(rep["effect_checked"], 4)      # None doesn't count
        self.assertEqual(rep["effect_verified"], 2)
        self.assertEqual(rep["verified_effect_fraction"], 0.5)

    def test_report_names_theater_when_fraction_zero(self):
        self.plog.parent.mkdir(parents=True, exist_ok=True)
        with self.plog.open("w", encoding="utf-8") as fh:
            for _ in range(4):
                fh.write(json.dumps(self._fake_pulse(False)) + "\n")
        rep = D.report(self.plog)
        self.assertEqual(rep["verified_effect_fraction"], 0.0)
        self.assertIn("THEATER", rep["verdict"])

    def test_report_on_missing_log_is_honest(self):
        rep = D.report(self.root / "nope.jsonl")
        self.assertEqual(rep["pulses"], 0)
        self.assertIsNone(rep["verified_effect_fraction"])
        self.assertIn("never woken", rep["verdict"])


# -- opt-in acting: routes through the EXISTING pin organ ---------------------

class TestActRoutesThroughExistingGates(DriveBase):
    def test_act_re_pins_experience_and_verifies_effect(self):
        now = time.time()                               # real clock: pin() stamps real time
        _ontology(self.ont, 10)
        _run(self.runs, "r-ok", "model_finished", "solved goal")
        _manifest(self.man, _iso(now - 300 * 3600))     # stale pin, staleness dominant
        _registry(self.reg, 2)
        state = D.homeostasis(now, **self.paths())
        self.assertTrue(state["over_threshold"])
        self.assertEqual(state["dominant"], "staleness")
        man_lines_before = len(self.man.read_text().splitlines())

        rec = D.pulse(now, dry_run=False, pulse_log=self.plog, **self.paths())
        executed = [e for e in rec["executed"] if e["status"] == "executed"]
        self.assertEqual(len(executed), 1)
        self.assertEqual(executed[0]["action"], "re_pin_experience")
        # the pin went through aios_experience.pin: manifest grew by one line
        man_lines_after = len(self.man.read_text().splitlines())
        self.assertEqual(man_lines_after, man_lines_before + 1)
        # the act's effect is verified: pin advanced
        self.assertTrue(rec["acted_effect"]["effect_verified"])
        self.assertIn("pin_advanced", rec["acted_effect"]["changes"])
        self.assertTrue(rec["effect_verified"])
        # non-auto-executable remedies were NOT executed, only named
        skipped = {e["action"] for e in rec["executed"]
                   if e["status"] == "skipped_requires_head"}
        self.assertNotIn("re_pin_experience", skipped)


# -- honest degradation -------------------------------------------------------

class TestHonestDegradation(DriveBase):
    def test_all_missing_inputs_pain_zero_no_signal(self):
        missing = dict(ontology=self.root / "no.json",
                       runs_dir=self.root / "no-runs",
                       exp_manifest=self.root / "no-man.jsonl",
                       skills_registry=self.root / "no-reg.jsonl")
        state = D.homeostasis(NOW, **missing)
        self.assertEqual(state["pain"], 0.0)
        self.assertFalse(state["over_threshold"])
        self.assertIsNone(state["dominant"])
        self.assertIn("no signal", state["note"])
        for comp in state["components"].values():
            self.assertFalse(comp["available"])
        rec = D.pulse(NOW, pulse_log=self.plog, **missing)   # never crashes
        self.assertEqual(rec["proposals"], [])
        self.assertEqual(rec["pain"], 0.0)

    def test_corrupt_ontology_degrades_not_crashes(self):
        self.calm()
        self.ont.write_text("{not json", encoding="utf-8")
        state = D.homeostasis(NOW, **self.paths())
        self.assertFalse(state["components"]["contradictions"]["available"])
        self.assertEqual(state["components"]["contradictions"]["weighted"], 0.0)

    def test_empty_runs_dir_is_no_experience_yet(self):
        self.calm()
        for f in self.runs.glob("*.jsonl"):
            f.unlink()
        state = D.homeostasis(NOW, **self.paths())
        self.assertFalse(state["components"]["failures"]["available"])


# -- CLI smoke ----------------------------------------------------------------

class TestCLI(DriveBase):
    def _main(self, *argv) -> dict:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = D.main([
                "--ontology", str(self.ont), "--runs-dir", str(self.runs),
                "--exp-manifest", str(self.man),
                "--skills-registry", str(self.reg),
                "--pulse-log", str(self.plog), *argv])
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def test_pain_pulse_report_roundtrip(self):
        self.painful()
        pain = self._main("pain")
        self.assertGreater(pain["pain"], pain["threshold"])
        rec = self._main("pulse")
        self.assertTrue(rec["dry_run"])
        self.assertGreater(len(rec["proposals"]), 0)
        rep = self._main("report")
        self.assertEqual(rep["pulses"], 1)
        self.assertIn("verified_effect_fraction", rep)


if __name__ == "__main__":
    unittest.main()
