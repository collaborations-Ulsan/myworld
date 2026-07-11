"""AIOS-DriftBench-mini task templates (M2 keystone harness skeleton).

docs/AIOS_DRIFTBENCH_PREREG_2026-07-11.md SS3: 8 templates x 3 seeds = 24 instances;
6 mutating (hidden-state) + 2 static controls. Each template mirrors one of the pre-reg's
8 named drift types (URL/version/config/API migration/deprecation/schema/auth/dependency).

AMBIGUITY FLAG: the pre-reg fixes the 6-mutating/2-static SPLIT COUNT but does not say
which of its 8 named drift types get a mutation event and which stay static controls.
This module resolves it as: mutating = {api_migration, deprecation, schema_change,
config_change, version_bump, auth_change}; static = {url_static, dependency_static}.
Anyone re-deriving this harness should treat that mapping as a design decision made
here, not a pre-reg fact.

Every template is a pure function of an integer seed: `build(seed) -> Environment`. Same
seed -> byte-identical workspace + goal + checkpoints (see
tests/test_driftbench_harness.py). Names/values/dates/schema fields are drawn from a
`random.Random(f"{template}:{seed}")` instance so no fixture text leaks a frontier model's
training-data prior (pre-reg SS3 leakage rule) and different templates never collide on
the same fixture data even at the same seed.

No model calls happen here. This module only builds and mutates a filesystem sandbox and
exposes a grader; wiring an actual agent loop against it is out of scope for the
skeleton (arms.py owns the arm-runner *interfaces* that will eventually drive an
Environment). Each template's "functional grader" is implemented as a real behavioral
check where cheap to do so (executing the generated script in a subprocess and
inspecting its output -- stdlib-only, no network) rather than a shallow text match.
"""
from __future__ import annotations

import configparser
import json
import random
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from grader import Checkpoint, GradeResult, grade_checkpoints
from schema import ALL_TEMPLATES, MUTATING_TEMPLATES, SEEDS, STATIC_TEMPLATES

_ADJECTIVES = [
    "cobalt", "umber", "lucent", "fenwick", "dorset", "brindle",
    "harrow", "vantage", "kestrel", "pallas",
]
_NOUNS = [
    "ledger", "beacon", "atlas", "forge", "harbor", "meridian",
    "cipher", "anchor", "relay", "summit",
]


def _rng(template: str, seed: int) -> random.Random:
    return random.Random(f"{template}:{seed}")


def _new_workspace(template: str, seed: int) -> Path:
    return Path(tempfile.mkdtemp(prefix=f"driftbench_{template}_{seed}_"))


@dataclass
class MutationEvent:
    """One mutation, applied at most once per Environment instance."""
    trigger_kind: str  # "after_step" | "after_checkpoint"
    trigger_value: object  # int step count, or a checkpoint id string
    description: str
    apply: Callable[["Environment"], None]
    applied: bool = False


@dataclass
class Environment:
    template: str
    seed: int
    mutating: bool
    workspace_dir: Path
    goal: str
    checkpoints: list[Checkpoint]
    contracts: list[str]  # human-readable explicit constraints (grader.py's (ii) check)
    state: dict
    mutation: Optional[MutationEvent] = None
    _passed_checkpoint_ids: set = field(default_factory=set, repr=False)

    def mutate(self, step: int) -> bool:
        """Idempotent: applies the mutation event at most once, when its trigger fires
        for the given step. Returns True iff the mutation fired on THIS call."""
        if self.mutation is None or self.mutation.applied:
            return False
        m = self.mutation
        if m.trigger_kind == "after_step":
            fire = step >= m.trigger_value
        elif m.trigger_kind == "after_checkpoint":
            fire = m.trigger_value in self._passed_checkpoint_ids
        else:
            raise ValueError(f"unknown trigger_kind {m.trigger_kind!r}")
        if fire:
            m.apply(self)
            m.applied = True
        return fire

    def grader(self) -> GradeResult:
        result = grade_checkpoints(self.checkpoints, self.workspace_dir, self.state)
        self._passed_checkpoint_ids |= {
            cp_id for cp_id, passed in result.per_checkpoint.items() if passed
        }
        return result

    def cleanup(self) -> None:
        shutil.rmtree(self.workspace_dir, ignore_errors=True)


def _run(workspace_dir: Path, script: str, timeout: float = 10.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, script], cwd=workspace_dir,
        capture_output=True, text=True, timeout=timeout,
    )


# ---------------------------------------------------------------------------
# 1. api_migration (mutating)
# ---------------------------------------------------------------------------
def _build_api_migration(seed: int) -> Environment:
    rng = _rng("api_migration", seed)
    ws = _new_workspace("api_migration", seed)
    old_fn = f"fetch_{rng.choice(_NOUNS)}_record"
    new_fn = f"get_{rng.choice(_NOUNS)}_record"
    while new_fn == old_fn:
        new_fn = f"get_{rng.choice(_NOUNS)}_record"
    record_id = rng.randint(1000, 9999)
    expected_value = rng.choice(_ADJECTIVES)

    client_src = (
        '"""Vendored client library (v1). Migration target -- do not edit directly."""\n\n'
        f"def {old_fn}(record_id):\n"
        f"    if record_id != {record_id}:\n"
        "        raise ValueError(\"unknown record\")\n"
        f'    return {{"id": record_id, "value": "{expected_value}"}}\n'
    )
    (ws / "client.py").write_text(client_src, encoding="utf-8")

    caller_src = (
        '"""Caller -- keep this working across the client API migration."""\n'
        "import json\n"
        f"from client import {old_fn}\n\n"
        "def run():\n"
        f"    record = {old_fn}({record_id})\n"
        '    with open("output.json", "w") as f:\n'
        "        json.dump(record, f)\n\n"
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "caller.py").write_text(caller_src, encoding="utf-8")

    state = {
        "old_fn": old_fn, "new_fn": new_fn, "record_id": record_id,
        "expected_value": expected_value, "mutated": False,
    }

    def _apply_migration(env: "Environment") -> None:
        new_client = (
            f'"""Vendored client library (v2 -- migrated mid-run). {env.state["old_fn"]} is REMOVED."""\n\n'
            f'def {env.state["new_fn"]}(record_id, *, strict=True):\n'
            "    if not strict:\n"
            '        raise ValueError("strict=False no longer supported")\n'
            f'    if record_id != {env.state["record_id"]}:\n'
            '        raise ValueError("unknown record")\n'
            f'    return {{"id": record_id, "value": "{env.state["expected_value"]}"}}\n'
        )
        (env.workspace_dir / "client.py").write_text(new_client, encoding="utf-8")
        env.state["mutated"] = True

    def _cp_output_correct(workspace_dir: Path, state: dict) -> bool:
        out = workspace_dir / "output.json"
        if not out.exists():
            return False
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            return False
        return data.get("id") == state["record_id"] and data.get("value") == state["expected_value"]

    def _cp_uses_current_api(workspace_dir: Path, state: dict) -> bool:
        src = (workspace_dir / "caller.py").read_text(encoding="utf-8")
        expected_fn = state["new_fn"] if state["mutated"] else state["old_fn"]
        return expected_fn in src

    def _cp_executes_cleanly(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "caller.py")
        except Exception:
            return False
        return proc.returncode == 0 and _cp_output_correct(workspace_dir, state)

    checkpoints = [
        Checkpoint("uses_current_api", "caller.py references the currently-valid client function name", _cp_uses_current_api),
        Checkpoint("executes_cleanly", "caller.py runs to completion against the current client API", _cp_executes_cleanly),
        Checkpoint("output_correct", "output.json matches the expected record", _cp_output_correct),
    ]
    mutation = MutationEvent(
        trigger_kind="after_step", trigger_value=3,
        description=f"client.py migrates {old_fn}(record_id) -> {new_fn}(record_id, *, strict=True)",
        apply=_apply_migration,
    )
    return Environment(
        template="api_migration", seed=seed, mutating=True, workspace_dir=ws,
        goal="Keep caller.py working against client.py's currently-valid API and producing a correct output.json.",
        checkpoints=checkpoints,
        contracts=["Do not edit client.py directly -- treat it as the (evolving) vendored dependency."],
        state=state, mutation=mutation,
    )


# ---------------------------------------------------------------------------
# 2. deprecation (mutating)
# ---------------------------------------------------------------------------
def _build_deprecation(seed: int) -> Environment:
    rng = _rng("deprecation", seed)
    ws = _new_workspace("deprecation", seed)
    deprecated_flag = f"legacy_{rng.choice(_NOUNS)}_export"
    replacement_flag = f"{rng.choice(_ADJECTIVES)}_export"
    payload_value = rng.randint(1, 999)

    tool_src = (
        f'"""Internal export tool. --{deprecated_flag} is deprecated and will be removed mid-run."""\n'
        "import argparse\n"
        "import json\n\n"
        "def main():\n"
        "    p = argparse.ArgumentParser()\n"
        f'    p.add_argument("--{deprecated_flag}", action="store_true")\n'
        f'    p.add_argument("--{replacement_flag}", action="store_true")\n'
        "    args = p.parse_args()\n"
        f'    if not (getattr(args, "{deprecated_flag}") or getattr(args, "{replacement_flag}")):\n'
        '        raise SystemExit("no export mode selected")\n'
        '    with open("export.json", "w") as f:\n'
        f'        json.dump({{"value": {payload_value}}}, f)\n\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    (ws / "export_tool.py").write_text(tool_src, encoding="utf-8")

    runner_src = (
        '"""Invokes export_tool.py. Update the flag it passes if the tool deprecates it."""\n'
        "import subprocess\n"
        "import sys\n\n"
        "def run():\n"
        f'    subprocess.run([sys.executable, "export_tool.py", "--{deprecated_flag}"], check=True)\n\n'
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "run_export.py").write_text(runner_src, encoding="utf-8")

    state = {
        "deprecated_flag": deprecated_flag, "replacement_flag": replacement_flag,
        "payload_value": payload_value, "removed": False,
    }

    def _apply_removal(env: "Environment") -> None:
        src = (env.workspace_dir / "export_tool.py").read_text(encoding="utf-8")
        old_line = f'    p.add_argument("--{env.state["deprecated_flag"]}", action="store_true")\n'
        src = src.replace(old_line, "")
        old_cond = (
            f'    if not (getattr(args, "{env.state["deprecated_flag"]}") or '
            f'getattr(args, "{env.state["replacement_flag"]}")):\n'
        )
        new_cond = f'    if not getattr(args, "{env.state["replacement_flag"]}"):\n'
        src = src.replace(old_cond, new_cond)
        (env.workspace_dir / "export_tool.py").write_text(src, encoding="utf-8")
        env.state["removed"] = True

    def _cp_uses_valid_flag(workspace_dir: Path, state: dict) -> bool:
        src = (workspace_dir / "run_export.py").read_text(encoding="utf-8")
        flag = state["replacement_flag"] if state["removed"] else state["deprecated_flag"]
        return f"--{flag}" in src

    def _cp_export_runs(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "run_export.py")
        except Exception:
            return False
        return proc.returncode == 0

    def _cp_export_correct(workspace_dir: Path, state: dict) -> bool:
        out = workspace_dir / "export.json"
        if not out.exists():
            return False
        try:
            return json.loads(out.read_text(encoding="utf-8")).get("value") == state["payload_value"]
        except Exception:
            return False

    checkpoints = [
        Checkpoint("uses_valid_flag", "run_export.py passes a currently-valid flag", _cp_uses_valid_flag),
        Checkpoint("export_runs", "run_export.py exits 0", _cp_export_runs),
        Checkpoint("export_correct", "export.json has the expected payload", _cp_export_correct),
    ]
    mutation = MutationEvent(
        trigger_kind="after_step", trigger_value=3,
        description=f"export_tool.py removes --{deprecated_flag}",
        apply=_apply_removal,
    )
    return Environment(
        template="deprecation", seed=seed, mutating=True, workspace_dir=ws,
        goal="Keep run_export.py invoking export_tool.py with a currently-supported flag and producing export.json.",
        checkpoints=checkpoints,
        contracts=["Do not edit export_tool.py -- it is the vendored tool; only run_export.py is yours to change."],
        state=state, mutation=mutation,
    )


# ---------------------------------------------------------------------------
# 3. schema_change (mutating)
# ---------------------------------------------------------------------------
def _build_schema_change(seed: int) -> Environment:
    rng = _rng("schema_change", seed)
    ws = _new_workspace("schema_change", seed)
    col_choices = ["amount", "qty", "total", "count"]
    old_col = rng.choice(col_choices)
    new_col = rng.choice([c for c in col_choices if c != old_col])
    n_rows = 5
    rows = [{"id": i, old_col: (i + 1) * rng.randint(2, 9)} for i in range(n_rows)]
    expected_sum = sum(r[old_col] for r in rows)

    csv_lines = ["id," + old_col] + [f"{r['id']},{r[old_col]}" for r in rows]
    (ws / "records.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    summarize_src = (
        '"""Summarize records.csv into summary.json. The column name may drift mid-run."""\n'
        "import csv\n"
        "import json\n\n"
        f'COLUMN = "{old_col}"\n\n'
        "def run():\n"
        "    total = 0\n"
        '    with open("records.csv", newline="") as f:\n'
        "        for row in csv.DictReader(f):\n"
        "            total += int(row[COLUMN])\n"
        '    with open("summary.json", "w") as f:\n'
        '        json.dump({"total": total}, f)\n\n'
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "summarize.py").write_text(summarize_src, encoding="utf-8")

    state = {
        "old_col": old_col, "new_col": new_col, "expected_sum": expected_sum,
        "n_rows": n_rows, "renamed": False,
    }

    def _apply_rename(env: "Environment") -> None:
        p = env.workspace_dir / "records.csv"
        lines = p.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace(env.state["old_col"], env.state["new_col"])
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        env.state["renamed"] = True

    def _cp_uses_current_column(workspace_dir: Path, state: dict) -> bool:
        src = (workspace_dir / "summarize.py").read_text(encoding="utf-8")
        expected_col = state["new_col"] if state["renamed"] else state["old_col"]
        return f'COLUMN = "{expected_col}"' in src

    def _cp_summarize_runs(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "summarize.py")
        except Exception:
            return False
        return proc.returncode == 0

    def _cp_summary_correct(workspace_dir: Path, state: dict) -> bool:
        out = workspace_dir / "summary.json"
        if not out.exists():
            return False
        try:
            return json.loads(out.read_text(encoding="utf-8")).get("total") == state["expected_sum"]
        except Exception:
            return False

    checkpoints = [
        Checkpoint("uses_current_column", "summarize.py's COLUMN matches records.csv's current header", _cp_uses_current_column),
        Checkpoint("summarize_runs", "summarize.py exits 0", _cp_summarize_runs),
        Checkpoint("summary_correct", "summary.json's total matches the source data", _cp_summary_correct),
    ]
    # Checkpoint-triggered mutation (deliberately different trigger_kind from the
    # step-triggered templates above, so both trigger kinds are exercised).
    mutation = MutationEvent(
        trigger_kind="after_checkpoint", trigger_value="summarize_runs",
        description=f"records.csv renames column {old_col} -> {new_col}",
        apply=_apply_rename,
    )
    return Environment(
        template="schema_change", seed=seed, mutating=True, workspace_dir=ws,
        goal="Keep summarize.py's COLUMN in sync with records.csv's schema and producing a correct summary.json.",
        checkpoints=checkpoints,
        contracts=["Do not overwrite records.csv's data rows -- only summarize.py is yours to change."],
        state=state, mutation=mutation,
    )


# ---------------------------------------------------------------------------
# 4. config_change (mutating)
# ---------------------------------------------------------------------------
def _build_config_change(seed: int) -> Environment:
    rng = _rng("config_change", seed)
    ws = _new_workspace("config_change", seed)
    service_name = f"{rng.choice(_ADJECTIVES)}-{rng.choice(_NOUNS)}"
    old_port = rng.randint(8000, 8999)
    new_port = rng.randint(9000, 9999)
    timeout_choices = [10, 15, 20, 30]
    old_timeout = rng.choice(timeout_choices)
    new_timeout = rng.choice([t for t in timeout_choices if t != old_timeout])

    cfg = configparser.ConfigParser()
    cfg["service"] = {"name": service_name, "port": str(old_port), "timeout": str(old_timeout)}
    with open(ws / "service.ini", "w") as f:
        cfg.write(f)

    # NOTE (grading-integrity design decision): connect.py hardcodes PORT/TIMEOUT as
    # source constants that must be kept in sync with service.ini, exactly like the
    # other mutating templates hardcode an identifier the agent must update (old_fn,
    # COLUMN, ...). An earlier version had connect.py re-read service.ini dynamically
    # on every run -- that made the "connection_runs" checkpoint a SELF-CORRECTING
    # side effect (merely checking "does it run" also regenerated a correct
    # connection.json), so the task passed even with zero agent action post-mutation.
    # Hardcoded constants make grading side-effect-free again: running connect.py only
    # ever reproduces whatever PORT/TIMEOUT are baked into its source right now.
    client_src = (
        '"""Connects to the service. PORT/TIMEOUT below must track service.ini -- '
        'update them when service.ini drifts."""\n'
        "import json\n\n"
        f"PORT = {old_port}\n"
        f"TIMEOUT = {old_timeout}\n\n"
        "def run():\n"
        '    with open("connection.json", "w") as f:\n'
        '        json.dump({"port": PORT, "timeout": TIMEOUT}, f)\n\n'
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "connect.py").write_text(client_src, encoding="utf-8")

    state = {
        "service_name": service_name, "old_port": old_port, "new_port": new_port,
        "old_timeout": old_timeout, "new_timeout": new_timeout, "changed": False,
    }

    def _apply_config_change(env: "Environment") -> None:
        cfg = configparser.ConfigParser()
        cfg.read(env.workspace_dir / "service.ini")
        cfg["service"]["port"] = str(env.state["new_port"])
        cfg["service"]["timeout"] = str(env.state["new_timeout"])
        with open(env.workspace_dir / "service.ini", "w") as f:
            cfg.write(f)
        env.state["changed"] = True

    def _cp_uses_current_config(workspace_dir: Path, state: dict) -> bool:
        src = (workspace_dir / "connect.py").read_text(encoding="utf-8")
        expected_port = state["new_port"] if state["changed"] else state["old_port"]
        expected_timeout = state["new_timeout"] if state["changed"] else state["old_timeout"]
        return f"PORT = {expected_port}" in src and f"TIMEOUT = {expected_timeout}" in src

    def _cp_connection_runs(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "connect.py")
        except Exception:
            return False
        return proc.returncode == 0

    def _cp_connection_matches_config(workspace_dir: Path, state: dict) -> bool:
        # Ground truth is service.ini's ACTUAL current contents (not connect.py's
        # possibly-stale constants) -- this is what makes the check meaningful.
        out = workspace_dir / "connection.json"
        cfg_path = workspace_dir / "service.ini"
        if not out.exists() or not cfg_path.exists():
            return False
        cfg = configparser.ConfigParser()
        cfg.read(cfg_path)
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            return False
        try:
            return (
                data.get("port") == int(cfg["service"]["port"])
                and data.get("timeout") == int(cfg["service"]["timeout"])
            )
        except Exception:
            return False

    checkpoints = [
        Checkpoint("uses_current_config", "connect.py's PORT/TIMEOUT constants match service.ini's current values", _cp_uses_current_config),
        Checkpoint("connection_runs", "connect.py exits 0", _cp_connection_runs),
        Checkpoint("connection_matches_config", "connection.json reflects service.ini's actual current values", _cp_connection_matches_config),
    ]
    mutation = MutationEvent(
        trigger_kind="after_step", trigger_value=4,
        description="service.ini rotates port + timeout",
        apply=_apply_config_change,
    )
    return Environment(
        template="config_change", seed=seed, mutating=True, workspace_dir=ws,
        goal="Keep connect.py's PORT/TIMEOUT constants in sync with service.ini as it drifts.",
        checkpoints=checkpoints,
        contracts=["Do not edit service.ini -- it is the vendored/managed config; only connect.py is yours to change."],
        state=state, mutation=mutation,
    )


# ---------------------------------------------------------------------------
# 5. version_bump (mutating)
# ---------------------------------------------------------------------------
def _build_version_bump(seed: int) -> Environment:
    rng = _rng("version_bump", seed)
    ws = _new_workspace("version_bump", seed)
    pkg_name = f"{rng.choice(_NOUNS)}kit"
    major = rng.randint(1, 3)
    old_version = f"{major}.{rng.randint(0, 9)}.0"
    new_version = f"{major + 1}.0.0"

    manifest = {"dependencies": {pkg_name: old_version}}
    (ws / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    vendor_src_v1 = (
        f'"""Vendored {pkg_name} v1.x -- process(data) returns a plain int."""\n\n'
        "def process(data):\n"
        "    return sum(data)\n"
    )
    vendor_src_v2 = (
        f'"""Vendored {pkg_name} v2.x -- process(data) now returns a dict (breaking response shape)."""\n\n'
        "def process(data):\n"
        f'    return {{"result": sum(data), "meta": {{"version": "{new_version}"}}}}\n'
    )
    (ws / f"{pkg_name}.py").write_text(vendor_src_v1, encoding="utf-8")

    consumer_src = (
        '"""Calls the vendored package. Keep this in sync with its CURRENT response shape."""\n'
        "import json\n"
        f"from {pkg_name} import process\n\n"
        "def run():\n"
        "    data = [1, 2, 3, 4]\n"
        "    result = process(data)\n"
        "    total = result  # v1.x: process() returns a plain int\n"
        '    with open("result.json", "w") as f:\n'
        '        json.dump({"total": total}, f)\n\n'
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "consumer.py").write_text(consumer_src, encoding="utf-8")

    state = {
        "pkg_name": pkg_name, "old_version": old_version, "new_version": new_version,
        "bumped": False,
    }

    def _apply_bump(env: "Environment") -> None:
        manifest = {"dependencies": {env.state["pkg_name"]: env.state["new_version"]}}
        (env.workspace_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (env.workspace_dir / f"{env.state['pkg_name']}.py").write_text(vendor_src_v2, encoding="utf-8")
        env.state["bumped"] = True

    def _cp_consumer_runs(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "consumer.py")
        except Exception:
            return False
        return proc.returncode == 0

    def _cp_result_correct(workspace_dir: Path, state: dict) -> bool:
        out = workspace_dir / "result.json"
        if not out.exists():
            return False
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            return False
        return data.get("total") == 10

    checkpoints = [
        Checkpoint("consumer_runs", "consumer.py exits 0", _cp_consumer_runs),
        Checkpoint("result_correct", "result.json's total survives the dependency's major-version bump", _cp_result_correct),
    ]
    mutation = MutationEvent(
        trigger_kind="after_step", trigger_value=4,
        description=f"{pkg_name} bumps {old_version} -> {new_version} (breaking response shape)",
        apply=_apply_bump,
    )
    return Environment(
        template="version_bump", seed=seed, mutating=True, workspace_dir=ws,
        goal="Keep consumer.py correct as manifest.json's pinned dependency version bumps to a new major.",
        checkpoints=checkpoints,
        contracts=[f"Only edit consumer.py -- {pkg_name}.py and manifest.json are the vendored/managed files."],
        state=state, mutation=mutation,
    )


# ---------------------------------------------------------------------------
# 6. auth_change (mutating)
# ---------------------------------------------------------------------------
def _build_auth_change(seed: int) -> Environment:
    rng = _rng("auth_change", seed)
    ws = _new_workspace("auth_change", seed)
    old_key = f"key-{rng.randint(100000, 999999)}"
    new_token = f"tok-{rng.randint(100000, 999999)}"
    resource_id = rng.randint(1, 500)

    (ws / "credentials.json").write_text(json.dumps({"api_key": old_key}), encoding="utf-8")

    server_src = (
        '"""Mock authenticated resource server. Auth method may migrate mid-run."""\n\n'
        "def fetch(auth):\n"
        f'    if auth.get("api_key") == "{old_key}":\n'
        f'        return {{"resource": {resource_id}}}\n'
        f'    if auth.get("bearer_token") == "{new_token}":\n'
        f'        return {{"resource": {resource_id}}}\n'
        '    raise PermissionError("unauthenticated")\n'
    )
    (ws / "server.py").write_text(server_src, encoding="utf-8")

    client_src = (
        '"""Reads credentials.json and fetches the resource. Keep this in sync with '
        'credentials.json\'s current auth shape."""\n'
        "import json\n"
        "from server import fetch\n\n"
        "def run():\n"
        '    creds = json.load(open("credentials.json"))\n'
        '    auth = {"api_key": creds["api_key"]}\n'
        "    result = fetch(auth)\n"
        '    with open("resource.json", "w") as f:\n'
        "        json.dump(result, f)\n\n"
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "client.py").write_text(client_src, encoding="utf-8")

    state = {
        "old_key": old_key, "new_token": new_token, "resource_id": resource_id,
        "rotated": False,
    }

    def _apply_rotation(env: "Environment") -> None:
        (env.workspace_dir / "credentials.json").write_text(
            json.dumps({"bearer_token": env.state["new_token"]}), encoding="utf-8",
        )
        env.state["rotated"] = True

    def _cp_client_runs(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "client.py")
        except Exception:
            return False
        return proc.returncode == 0

    def _cp_resource_correct(workspace_dir: Path, state: dict) -> bool:
        out = workspace_dir / "resource.json"
        if not out.exists():
            return False
        try:
            return json.loads(out.read_text(encoding="utf-8")).get("resource") == state["resource_id"]
        except Exception:
            return False

    checkpoints = [
        Checkpoint("client_runs", "client.py exits 0", _cp_client_runs),
        Checkpoint("resource_correct", "resource.json has the expected resource id (auth succeeded)", _cp_resource_correct),
    ]
    mutation = MutationEvent(
        trigger_kind="after_step", trigger_value=3,
        description="credentials.json rotates from api_key to bearer_token",
        apply=_apply_rotation,
    )
    return Environment(
        template="auth_change", seed=seed, mutating=True, workspace_dir=ws,
        goal="Keep client.py authenticating successfully as credentials.json's auth method rotates.",
        checkpoints=checkpoints,
        contracts=["Never hardcode a credential value in client.py -- always read credentials.json."],
        state=state, mutation=mutation,
    )


# ---------------------------------------------------------------------------
# 7. url_static (static control)
# ---------------------------------------------------------------------------
def _build_url_static(seed: int) -> Environment:
    rng = _rng("url_static", seed)
    ws = _new_workspace("url_static", seed)
    n = 4
    names = [f"svc{i}" for i in range(n)]
    hosts = [f"{rng.choice(_ADJECTIVES)}-{rng.choice(_NOUNS)}.internal" for _ in range(n)]
    routes = {name: f"https://{host}/api/v1" for name, host in zip(names, hosts)}
    target_name = names[rng.randrange(n)]
    (ws / "routes.json").write_text(json.dumps(routes, indent=2), encoding="utf-8")

    resolver_src = (
        '"""Resolve a named route from routes.json. Fill in TARGET_NAME below."""\n'
        "import json\n\n"
        f"TARGET_NAME = None  # the agent must set this to \"{target_name}\"\n\n"
        "def run():\n"
        '    routes = json.load(open("routes.json"))\n'
        "    if TARGET_NAME not in routes:\n"
        '        raise SystemExit("TARGET_NAME not set to a valid route name")\n'
        '    with open("resolved.json", "w") as f:\n'
        '        json.dump({"url": routes[TARGET_NAME]}, f)\n\n'
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "resolve.py").write_text(resolver_src, encoding="utf-8")

    expected_url = routes[target_name]
    state = {"routes": routes, "target_name": target_name, "expected_url": expected_url}

    def _cp_resolver_runs(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "resolve.py")
        except Exception:
            return False
        return proc.returncode == 0

    def _cp_resolved_correct(workspace_dir: Path, state: dict) -> bool:
        out = workspace_dir / "resolved.json"
        if not out.exists():
            return False
        try:
            return json.loads(out.read_text(encoding="utf-8")).get("url") == state["expected_url"]
        except Exception:
            return False

    checkpoints = [
        Checkpoint("resolver_runs", "resolve.py exits 0", _cp_resolver_runs),
        Checkpoint("resolved_correct", "resolved.json has the correct target URL", _cp_resolved_correct),
    ]
    return Environment(
        template="url_static", seed=seed, mutating=False, workspace_dir=ws,
        goal=f'Set TARGET_NAME in resolve.py to "{target_name}" and produce a correct resolved.json.',
        checkpoints=checkpoints,
        contracts=["Do not edit routes.json."],
        state=state, mutation=None,
    )


# ---------------------------------------------------------------------------
# 8. dependency_static (static control)
# ---------------------------------------------------------------------------
def _build_dependency_static(seed: int) -> Environment:
    rng = _rng("dependency_static", seed)
    ws = _new_workspace("dependency_static", seed)
    pool = ["json", "math", "itertools", "statistics", "textwrap", "collections"]
    mods = rng.sample(pool, k=3)
    missing_mod = mods[0]  # imported by app.py but left off requirements.txt

    (ws / "requirements.txt").write_text("\n".join(mods[1:]) + "\n", encoding="utf-8")

    app_src = (
        '"""App entrypoint. requirements.txt is the explicit manifest contract for this '
        'task -- every top-level import must be listed there."""\n'
        f"import {mods[0]}\n"
        f"import {mods[1]}\n"
        f"import {mods[2]}\n\n"
        "def run():\n"
        '    with open("manifest_ok.json", "w") as f:\n'
        '        f.write("{}")\n\n'
        'if __name__ == "__main__":\n'
        "    run()\n"
    )
    (ws / "app.py").write_text(app_src, encoding="utf-8")

    state = {"required_mods": sorted(mods), "missing_mod": missing_mod}

    def _cp_requirements_complete(workspace_dir: Path, state: dict) -> bool:
        req = workspace_dir / "requirements.txt"
        if not req.exists():
            return False
        listed = {line.strip() for line in req.read_text(encoding="utf-8").splitlines() if line.strip()}
        return listed == set(state["required_mods"])

    def _cp_app_runs(workspace_dir: Path, state: dict) -> bool:
        try:
            proc = _run(workspace_dir, "app.py")
        except Exception:
            return False
        return proc.returncode == 0 and (workspace_dir / "manifest_ok.json").exists()

    checkpoints = [
        Checkpoint("requirements_complete", "requirements.txt lists every module app.py imports", _cp_requirements_complete),
        Checkpoint("app_runs", "app.py runs to completion", _cp_app_runs),
    ]
    return Environment(
        template="dependency_static", seed=seed, mutating=False, workspace_dir=ws,
        goal="Make requirements.txt list exactly the modules app.py imports, then confirm app.py still runs.",
        checkpoints=checkpoints,
        contracts=["Do not remove imports from app.py."],
        state=state, mutation=None,
    )


_BUILDERS: dict[str, Callable[[int], Environment]] = {
    "api_migration": _build_api_migration,
    "deprecation": _build_deprecation,
    "schema_change": _build_schema_change,
    "config_change": _build_config_change,
    "version_bump": _build_version_bump,
    "auth_change": _build_auth_change,
    "url_static": _build_url_static,
    "dependency_static": _build_dependency_static,
}

assert set(_BUILDERS) == set(ALL_TEMPLATES), "tasks.py template registry drifted from schema.ALL_TEMPLATES"


def build(template: str, seed: int) -> Environment:
    if template not in _BUILDERS:
        raise ValueError(f"unknown template {template!r}; known: {sorted(_BUILDERS)}")
    env = _BUILDERS[template](seed)
    assert env.template == template
    assert env.mutating == (template in MUTATING_TEMPLATES)
    assert (template in STATIC_TEMPLATES) == (not env.mutating)
    return env


def all_instances(seeds: tuple[int, ...] = SEEDS) -> list[tuple[str, int]]:
    """The frozen 8x3=24 instance key set (pre-reg SS3). Deliberately NOT built eagerly
    -- materializing all 24 workspaces is an arm-runner concern, out of scope here."""
    return [(t, s) for t in ALL_TEMPLATES for s in seeds]
