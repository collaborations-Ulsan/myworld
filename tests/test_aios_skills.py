"""Unit tests for scripts/aios_skills.py — Code Artifact Induction (Phase 4).

Proves the compounding claims on the REAL mechanism:
  (i)   a skill whose unit_test PASSES in the sandbox is registered;
  (ii)  a skill whose unit_test FAILS is REJECTED (anti-reward-hack gate —
        it never enters the registry);
  (iii) sandbox unavailable (forced via AIOS_SANDBOX_ENGINE=none — the
        module's own sanctioned kill switch) -> NOT registered (fail closed);
  (iv)  retrieve returns the applicable skill for a related task and NOT an
        unrelated one; a fully-unrelated query returns [];
  (v)   the Merkle root is deterministic and tamper-sensitive (rewrite AND
        truncation are named violations);
  (vi)  induce_skill yields a registrable skill from (goal, solution_code,
        unit_test), dropping driver statements; synthesized smoke tests are
        honestly labeled.

Tests that must EXECUTE code require a working sandbox engine; on a box with
none they skip loudly (register() is fail-closed there — which is itself
covered by (iii), which runs everywhere). Registry/manifest/receipts all live
under tmp_path — nothing touches the real .aios/ state.
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (_ROOT / "scripts").as_posix())

import aios_sandbox  # noqa: E402
import aios_skills  # noqa: E402

NOW = 1_753_142_400.0

ENGINE = aios_sandbox.pick_engine()
needs_sandbox = pytest.mark.skipif(
    ENGINE == "none",
    reason="no working sandbox engine on this box — sandbox-gated "
           "registration cannot be exercised live (fail-closed path is "
           "still covered by the AIOS_SANDBOX_ENGINE=none test)")


@pytest.fixture()
def paths(tmp_path):
    return {"registry": tmp_path / "registry.jsonl",
            "manifest": tmp_path / "manifest.jsonl",
            "receipt_log": tmp_path / "receipts.jsonl"}


def _register(skill, paths, **kw):
    return aios_skills.register(skill, now=NOW, registry=paths["registry"],
                                manifest=paths["manifest"],
                                receipt_log=paths["receipt_log"], **kw)


def _skill(name="alpha_add", code=None, unit_test=None, **over):
    base = {
        "name": name,
        "code": code or f"def {name}(a, b):\n    return a + b\n",
        "applicability": f"use when: adding numbers with {name}",
        "example": {"input": [2, 3], "expected_output": 5},
        "unit_test": unit_test or f"assert {name}(2, 3) == 5\n",
        "provenance": {"source_goal": "test fixture"},
        "created_ts": NOW,
    }
    base.update(over)
    return base


# ── (i) passing unit_test -> registered ──────────────────────────────────────

@needs_sandbox
def test_passing_unit_test_registers(paths):
    out = _register(_skill(), paths)
    assert out["registered"] is True
    assert out["verdict"] == "registered"
    assert out["gate"]["sandboxed"] is True and out["gate"]["ok"] is True
    assert out["gate"]["engine"] in ("bwrap", "native")
    skills = aios_skills.load_registry(paths["registry"])
    assert len(skills) == 1 and skills[0]["id"] == out["id"]
    report = aios_skills.verify(paths["registry"], paths["manifest"])
    assert report["status"] == "ok" and report["appended_entries"] == 0


# ── (ii) failing unit_test -> REJECTED (anti-reward-hack gate) ───────────────

@needs_sandbox
def test_failing_unit_test_rejected(paths):
    bad = _skill(unit_test="assert alpha_add(2, 3) == 6, 'gate must catch'\n")
    out = _register(bad, paths)
    assert out["registered"] is False
    assert out["verdict"] == "rejected_unit_test_failed"
    assert out["gate"]["sandboxed"] is True and out["gate"]["ok"] is False
    # the gate held: nothing was ever appended — the registry does not exist
    assert not paths["registry"].exists()
    assert aios_skills.load_registry(paths["registry"]) == []


# ── (iii) sandbox unavailable -> NOT registered (fail closed) ────────────────

def test_sandbox_unavailable_fail_closed(paths, monkeypatch):
    monkeypatch.setenv("AIOS_SANDBOX_ENGINE", "none")
    out = _register(_skill(), paths)
    assert out["registered"] is False
    assert out["verdict"] == "refused_sandbox_unavailable"
    assert out["gate"]["sandboxed"] is False
    assert not paths["registry"].exists()
    assert aios_skills.load_registry(paths["registry"]) == []


def test_invalid_skill_refused_before_gate(paths):
    incomplete = _skill()
    del incomplete["unit_test"]
    out = _register(incomplete, paths)
    assert out["registered"] is False
    assert out["verdict"] == "refused_invalid"
    assert "unit_test" in out["reason"]
    assert not paths["registry"].exists()


@needs_sandbox
def test_duplicate_id_refused(paths):
    assert _register(_skill(), paths)["registered"] is True
    out = _register(_skill(), paths)
    assert out["registered"] is False
    assert out["verdict"] == "refused_duplicate"
    assert len(aios_skills.load_registry(paths["registry"])) == 1


# ── (iv) retrieval: applicable yes, unrelated no ─────────────────────────────

@needs_sandbox
def test_retrieve_applicable_not_unrelated(paths):
    slug = _skill(
        name="slugify",
        code="def slugify(title):\n    import re\n"
             "    return re.sub(r'[^a-z0-9]+', '-', title.lower())"
             ".strip('-')\n",
        applicability="use when: converting titles to url slugs",
        example={"input": "Hello World!", "expected_output": "hello-world"},
        unit_test="assert slugify('Hello World!') == 'hello-world'\n",
    )
    csv = _skill(
        name="sum_csv_column",
        code="def sum_csv_column(text, idx):\n    total = 0.0\n"
             "    for row in text.splitlines():\n"
             "        total += float(row.split(',')[idx])\n    return total\n",
        applicability="use when: summing numeric csv columns",
        example={"input": "1,2 / 3,4 idx=1", "expected_output": 6.0},
        unit_test="assert sum_csv_column('1,2\\n3,4', 1) == 6.0\n",
    )
    assert _register(slug, paths)["registered"] is True
    assert _register(csv, paths)["registered"] is True

    hits = aios_skills.retrieve("make a url slug from my blog title", k=3,
                                registry=paths["registry"])
    assert hits, "the applicable skill must be retrieved"
    assert hits[0]["skill"]["name"] == "slugify"
    assert "sum_csv_column" not in {h["skill"]["name"] for h in hits}, \
        "an unrelated (zero-overlap) skill must NOT be retrieved"

    assert aios_skills.retrieve("bake sourdough bread at home",
                                registry=paths["registry"]) == []


def test_empty_registry_degrades_honestly(paths):
    assert aios_skills.retrieve("anything at all",
                                registry=paths["registry"]) == []
    assert aios_skills.load_registry(paths["registry"]) == []
    assert aios_skills.registry_root(paths["registry"]) == \
        aios_skills.merkle_root([])
    report = aios_skills.verify(paths["registry"], paths["manifest"])
    assert report["status"] == "no_pin"


# ── (v) Merkle root: deterministic + tamper-sensitive ────────────────────────

@needs_sandbox
def test_merkle_deterministic_and_tamper_sensitive(paths):
    assert _register(_skill(), paths)["registered"] is True
    second = _skill(name="beta_mul",
                    code="def beta_mul(a, b):\n    return a * b\n",
                    unit_test="assert beta_mul(2, 3) == 6\n")
    assert _register(second, paths)["registered"] is True

    root_1 = aios_skills.registry_root(paths["registry"])
    assert root_1 == aios_skills.registry_root(paths["registry"])  # deterministic
    assert aios_skills.verify(paths["registry"],
                              paths["manifest"])["status"] == "ok"

    original = paths["registry"].read_text(encoding="utf-8")

    # rewrite one byte of a registered skill -> new root + named violation
    paths["registry"].write_text(
        original.replace('"alpha_add"', '"tampered_x"', 1), encoding="utf-8")
    assert aios_skills.registry_root(paths["registry"]) != root_1
    report = aios_skills.verify(paths["registry"], paths["manifest"])
    assert report["status"] == "tampered"
    assert report["violations"][0]["violation"] == "rewritten"

    # truncate past experience -> named violation
    paths["registry"].write_text(
        original.splitlines()[0] + "\n", encoding="utf-8")
    report = aios_skills.verify(paths["registry"], paths["manifest"])
    assert report["status"] == "tampered"
    assert report["violations"][0]["violation"] == "truncated"


# ── (vi) induce_skill: structured extraction -> registrable ──────────────────

SOLUTION_NORMALIZE = (
    "import re\n"
    "\n"
    "def normalize_ws(text):\n"
    '    """Collapse runs of whitespace to single spaces."""\n'
    "    return re.sub(r'\\s+', ' ', text).strip()\n"
    "\n"
    "print(normalize_ws('  demo   driver  '))\n"
)


@needs_sandbox
def test_induce_skill_registrable(paths):
    unit_test = "assert normalize_ws('  hello   world ') == 'hello world'\n"
    skill = aios_skills.induce_skill(
        "collapse repeated whitespace in text", SOLUTION_NORMALIZE,
        unit_test=unit_test, created_ts=NOW)
    assert skill["name"] == "normalize_ws"
    assert skill["applicability"].startswith("use when:")
    assert "import re" in skill["code"]
    assert "print(" not in skill["code"], "driver statements must be dropped"
    assert skill["provenance"]["unit_test_source"] == "provided"

    out = _register(skill, paths)
    assert out["registered"] is True

    hits = aios_skills.retrieve("collapse extra whitespace in some text",
                                registry=paths["registry"])
    assert hits and hits[0]["skill"]["id"] == skill["id"]


@needs_sandbox
def test_induce_synthesized_smoke_is_labeled(paths):
    solution = "def make_greeting():\n    return 'hello from a skill'\n"
    skill = aios_skills.induce_skill("produce a fixed greeting string",
                                     solution, created_ts=NOW)
    assert skill["provenance"]["unit_test_source"] == "synthesized_smoke"
    assert "callable(make_greeting)" in skill["unit_test"]
    assert _register(skill, paths)["registered"] is True


def test_induce_refuses_function_free_solutions():
    with pytest.raises(ValueError):
        aios_skills.induce_skill("store a constant", "x = 1\n", created_ts=NOW)
    with pytest.raises(ValueError):
        aios_skills.induce_skill("broken", "def oops(:\n", created_ts=NOW)


# ── hook: induce_and_register end-to-end ─────────────────────────────────────

@needs_sandbox
def test_induce_and_register_hook(paths):
    out = aios_skills.induce_and_register(
        "collapse repeated whitespace in text", SOLUTION_NORMALIZE,
        "assert normalize_ws(' a  b ') == 'a b'\n", now=NOW,
        registry=paths["registry"], manifest=paths["manifest"],
        receipt_log=paths["receipt_log"])
    assert out["registered"] is True
    assert out["skill"]["id"] == out["id"]

    failed = aios_skills.induce_and_register(
        "nothing to extract", "x = 1\n", now=NOW,
        registry=paths["registry"], manifest=paths["manifest"],
        receipt_log=paths["receipt_log"])
    assert failed["registered"] is False
    assert failed["verdict"] == "induction_failed"
