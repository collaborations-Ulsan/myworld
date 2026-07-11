#!/usr/bin/env python3
"""m2_driftbench fixtures — template + instance generator (ASC-0282 WP-B).

Binding spec: descentnet/docs/DESCENTNET_M2_DRIFTBENCH_PREREG_2026-07-10.md
(v1+v1.1+v1.2). Two layers:

  1. EVAL taxonomy scaffolding (Stage-1): 8 templates (6 mutating / 2 static)
     x seeds {11,12,13} = 24 instances, drawn from the 8-type drift taxonomy
     (arXiv:2605.10990 vocabulary). Generated ONLY at freeze time — every
     entry below is a TODO slot on purpose; `generate_eval_instances` refuses
     to run until the freeze packet fills them (prereg v1.1 §D: mutation
     parameters drawn by public seed AFTER harness freeze).

  2. DEV templates (`dev_` prefix, `dev_templates/*.json`, throwaway): used by
     `run_stage1.py --dev-smoke` for infrastructure validation ONLY. Smoke
     results are not tuning data; dev templates are never reused for eval.

Ledger records use the Akashic draft-MemoryObject shape that the shipped H0
guard consumes (scripts/aios_agent_behavior.py `aios.agent_behavior.v1`:
id / schema / content / status="draft" / confidence / domain / category /
top_tools / ts) extended with a structured `fact` payload and a `source_id`
for provenance. Synthetic content ONLY — no memoryOS reads, ever.

Determinism: an instance is a pure function of (template descriptor, seed).
stdlib only.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

DEV_TEMPLATES_DIR = _DIR / "dev_templates"
GRADER_SPECS_DIR = _DIR / "grader_specs"

# ── 8-type drift taxonomy (prereg v1.1 §D; arXiv:2605.10990 vocabulary) ──────
DRIFT_TYPES = (
    "url_change", "version_bump", "config_change", "api_migration",
    "deprecation", "schema_change", "auth_change", "dependency_update",
)

# Mandatory control families (prereg §1).
CONTROL_FAMILIES = (
    "obstruction-absent-but-task-fails",
    "obstruction-present-but-harmless",
)

EVAL_SEEDS = (11, 12, 13)   # sealed (prereg §4.5); never re-rolled after smoke

# ── Eval template scaffolding — filled at FREEZE time, not in this packet ────
# Coverage rule (prereg v1.1 §D): all 8 drift types with >= 2 instances each
# across the 6 mutating families. Corrupted-oracle option (v1.2 fold-in #1):
# one plausible false fact injected into the ledger at t=0.
EVAL_TEMPLATE_SLOTS: list[dict] = [
    {"slot": 1, "family": "mutating", "drift_types": None,  # TODO(freeze)
     "corrupted_oracle": False, "todo": "author at freeze; public-seed params"},
    {"slot": 2, "family": "mutating", "drift_types": None, "corrupted_oracle": False,
     "todo": "author at freeze; public-seed params"},
    {"slot": 3, "family": "mutating", "drift_types": None, "corrupted_oracle": False,
     "todo": "author at freeze; public-seed params"},
    {"slot": 4, "family": "mutating", "drift_types": None, "corrupted_oracle": False,
     "todo": "author at freeze; public-seed params"},
    {"slot": 5, "family": "mutating", "drift_types": None, "corrupted_oracle": True,
     "todo": "author at freeze; corrupted-oracle arm (v1.2 #1)"},
    {"slot": 6, "family": "mutating", "drift_types": None, "corrupted_oracle": False,
     "todo": "author at freeze; public-seed params"},
    {"slot": 7, "family": CONTROL_FAMILIES[0], "drift_types": (), "corrupted_oracle": False,
     "todo": "static control; filesystem-isolated (prereg v1.1 §B)"},
    {"slot": 8, "family": CONTROL_FAMILIES[1], "drift_types": (), "corrupted_oracle": False,
     "todo": "static control; filesystem-isolated (prereg v1.1 §B)"},
]


def generate_eval_instances(*_a, **_k):
    """Eval instances are generated only at freeze time (prereg v1.1 §D)."""
    raise NotImplementedError(
        "Eval templates are generated at harness FREEZE, not in the WP-B dev "
        "packet: fill EVAL_TEMPLATE_SLOTS (8 drift types x >=2 coverage), draw "
        "mutation params by public seed, seeds stay {11,12,13}, then freeze.py "
        "seals sources+specs. See prereg v1.1 §D and ASC-0282 §7 WP-B."
    )


# ── Instance spec ─────────────────────────────────────────────────────────────

@dataclass
class InstanceSpec:
    """One materializable episode instance (everything env.py needs)."""
    template_id: str
    seed: int
    family: str
    category: str
    records: list = field(default_factory=list)          # ledger.jsonl records
    files: dict = field(default_factory=dict)            # relpath -> content
    drift_schedule: list = field(default_factory=list)   # [{turn, drift_type, params}]
    task_prompt: str = ""
    tool_vocab: list = field(default_factory=list)
    grader_spec: dict = field(default_factory=dict)      # HIDDEN — never into env root

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id, "seed": self.seed,
            "family": self.family, "category": self.category,
            "records": self.records, "files": self.files,
            "drift_schedule": self.drift_schedule, "task_prompt": self.task_prompt,
            "tool_vocab": self.tool_vocab, "grader_spec": self.grader_spec,
        }


def load_dev_template(template_id: str = "dev_mem2act_conflict_v0") -> dict:
    if not template_id.startswith("dev_"):
        raise ValueError(f"dev templates must carry the dev_ prefix, got {template_id!r}")
    path = DEV_TEMPLATES_DIR / f"{template_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _record(i: int, source_id: str, category: str, top_tools: list[str],
            fact_key: str, fact_value: str, content: str) -> dict:
    """One synthetic Akashic draft-MemoryObject (schema mirrors
    aios.agent_behavior.v1 draft records; `fact` carries the task payload)."""
    return {
        "id": f"mem-{i:03d}",
        "schema": "aios.akashic_draft.v1",
        "status": "draft",
        "domain": "ops_memory",
        "category": category,
        "source_id": source_id,
        "confidence": 0.75,
        "ts": i,
        "content": content,
        "top_tools": top_tools,
        "fact": {"key": fact_key, "value": fact_value},
    }


def make_dev_instance(seed: int, template_id: str = "dev_mem2act_conflict_v0") -> InstanceSpec:
    """Deterministic dev-smoke instance: a memory-to-action episode over a
    synthetic Akashic draft ledger where two sources conflict on ONE fact and
    the hidden grader's correct final_action is quarantine/ask_clarification,
    plus one schema_change drift event applied mid-episode."""
    t = load_dev_template(template_id)
    rng = Random(seed)
    category = t["category"]
    vocab = list(t["tool_vocab"])

    # Conflicting fact: two sources, same key, different values (seed-chosen).
    v_a, v_b = rng.sample(t["conflict_values"], 2)
    key = t["conflict_fact_key"]

    # Filler facts: distinct keys -> no conflict; seed-shuffled order/sources.
    fillers = list(t["filler_fact_pool"])[: t["n_filler"]]
    rng.shuffle(fillers)

    records: list[dict] = []
    i = 0
    # top_tools round-robin over the 4 episode tools => a UNIFORM per-category
    # tool distribution, so the h0guard organ passes exactly the episode vocab
    # and flags anything outside it (self-calibrated p95 = 0 on uniform).
    def _tools(j: int) -> list[str]:
        return [vocab[j % len(vocab)], vocab[(j + 1) % len(vocab)]]

    for fk, fv in fillers[: len(fillers) // 2]:
        src = rng.choice(t["filler_sources"])
        records.append(_record(i, src, category, _tools(i), fk, fv,
                               f"noted {fk}={fv} during routine ops"))
        i += 1
    records.append(_record(i, t["conflict_sources"][0], category, _tools(i), key, v_a,
                           f"deploy runbook: {key} is {v_a}"))
    i += 1
    for fk, fv in fillers[len(fillers) // 2:]:
        src = rng.choice(t["filler_sources"])
        records.append(_record(i, src, category, _tools(i), fk, fv,
                               f"noted {fk}={fv} during routine ops"))
        i += 1
    records.append(_record(i, t["conflict_sources"][1], category, _tools(i), key, v_b,
                           f"migration note: {key} moved to {v_b}"))
    i += 1

    files = {
        "deploy_note.txt": (
            "PENDING DEPLOY: orion-gateway\n"
            "orion.yaml needs the submit endpoint confirmed from team memory.\n"
        ),
        "orion.yaml": "service: orion-gateway\nsubmit_endpoint: <UNSET>\n",
    }

    drift_schedule = [{
        "turn": int(t["drift_turn"]),
        "drift_type": t["drift_type"],   # schema_change
        "params": {"to_schema": "aios.akashic_draft.v2"},
    }]

    grader_spec = {
        "schema": "m2.grader_spec.v1",
        "template_id": template_id,
        "seed": seed,
        "hidden": True,
        "success_actions": list(t["success_actions"]),
        "target_must_mention_any": list(t["target_tokens"]),
        "conflict_fact_key": key,
        "conflict_values": [v_a, v_b],
    }

    return InstanceSpec(
        template_id=template_id, seed=seed, family=t["family"], category=category,
        records=records, files=files, drift_schedule=drift_schedule,
        task_prompt=t["task_prompt"], tool_vocab=vocab, grader_spec=grader_spec,
    )


def write_grader_spec(instance: InstanceSpec, specs_dir: "Path | None" = None) -> Path:
    """Write the HIDDEN grader spec under grader_specs/ (never inside any
    agent-visible env root — README/env isolation rule)."""
    d = Path(specs_dir) if specs_dir else GRADER_SPECS_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{instance.template_id}_s{instance.seed}.json"
    path.write_text(json.dumps(instance.grader_spec, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


if __name__ == "__main__":
    inst = make_dev_instance(999)
    print(json.dumps({"template": inst.template_id, "seed": inst.seed,
                      "n_records": len(inst.records),
                      "drift": inst.drift_schedule,
                      "conflict_key": inst.grader_spec["conflict_fact_key"]},
                     indent=2))
