"""Organs-as-tools through the kernel loop (blueprint step 2): the 132 standalone
scripts become registry handlers the turn-loop dispatches, behind an authority gate.
The point: tool-calls now flow THROUGH the kernel, not around it.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_tools as T
import aios_turn_loop as L


def scripted(steps):
    it = iter(steps)
    return lambda h: next(it)


class RegistryTests(unittest.TestCase):
    def test_registry_exposes_organs_as_tools(self) -> None:
        reg = T.build_registry()
        for name in ("self.audit", "interior.read", "stakes.record", "memory.retrieve",
                     "capability.route", "genesis.challenge", "fs.read", "fs.write"):
            self.assertIn(name, reg.handlers)

    def test_list_tools_discovery(self) -> None:
        names = {t["name"] for t in T.list_tools()}
        self.assertIn("self.audit", names)


class GateTests(unittest.TestCase):
    def test_read_and_advisory_allowed(self) -> None:
        g = T.gate_for("codex@myworld")
        self.assertEqual(g("self.audit", {}), L.ALLOW)
        self.assertEqual(g("capability.route", {}), L.ALLOW)
        self.assertEqual(g("fs.read", {}), L.ALLOW)

    def test_write_gated_by_authority(self) -> None:
        # commit_to_child_repo excludes outsider → ASK; child_agent is authorized → ALLOW
        self.assertEqual(T.gate_for("test_outsider")("fs.write", {}), L.ASK)
        self.assertEqual(T.gate_for("codex@hivemind")("fs.write", {}), L.ALLOW)

    def test_unknown_tool_fail_closed(self) -> None:
        self.assertEqual(T.gate_for("codex@myworld")("mystery.tool", {}), L.DENY)


class FlowThroughKernelTests(unittest.TestCase):
    def test_goal_flows_through_kernel_invoking_real_organs(self) -> None:
        reg = T.build_registry()
        r = L.run_loop("inspect", scripted([
            {"tool_calls": [L.ToolCall("self.audit",
                {"claims": [{"text": "sandbox", "path": "scripts/aios_sandbox.py"}]}, call_id="c1")]},
            {"tool_calls": [L.ToolCall("interior.read",
                {"traces": [{"kind": "Bash"} for _ in range(5)]}, call_id="c2")]},
            {"tool_calls": []},
        ]), reg, gate=T.gate_for("codex@myworld"))
        self.assertEqual(r["exit"], "model_finished")
        self.assertTrue(r["kernel_routed"])              # every call went through the kernel gate
        self.assertEqual([t["status"] for t in r["trajectory"]], ["ok", "ok"])

    def test_outsider_write_escalates_not_silent(self) -> None:
        reg = T.build_registry()
        r = L.run_loop("write", scripted([
            {"tool_calls": [L.ToolCall("fs.write", {"path": "x"}, call_id="w1")]},
            {"tool_calls": []},
        ]), reg, gate=T.gate_for("test_outsider"))
        self.assertEqual(r["exit"], "needs_approval")


class HandlerTests(unittest.TestCase):
    def test_self_audit_handler_runs_in_process(self) -> None:
        # Use absolute path so this passes regardless of CWD
        import os, pathlib
        abs_path = str(pathlib.Path(__file__).resolve().parents[1] / "scripts" / "aios_tools.py")
        r = T.HANDLERS["self.audit"]({"claims": [{"text": "exists", "path": abs_path}]})
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["trustworthy"])                # the file does exist

    def test_fs_read_is_repo_scoped_and_size_only(self) -> None:
        out = T.HANDLERS["fs.read"]({"path": "../../../etc/passwd"})
        self.assertEqual(out["status"], "denied_scope")  # bounded to the repo
        ok = T.HANDLERS["fs.read"]({"path": "scripts/aios_tools.py"})
        self.assertEqual(ok["status"], "ok")
        self.assertIn("bytes", ok)                       # size, never content

    def test_sibling_backed_degrades_without_crash(self) -> None:
        # capability.route shells to a sibling; here it just must not crash and must
        # return a status the loop can react to
        r = T.HANDLERS["capability.route"]({"task": "anything"})
        self.assertIn(r["status"], ("ok", "unavailable"))


if __name__ == "__main__":
    unittest.main()


class FsGrepTests(unittest.TestCase):
    def test_grep_finds_files_mentioning_pattern(self) -> None:
        r = T.HANDLERS["fs.grep"]({"pattern": "EpistemicGate", "path": "scripts", "glob": "*.py"})
        self.assertEqual(r["status"], "ok")
        paths = [h["path"] for h in r["hits"]]
        self.assertIn("scripts/aios_epistemic_gate.py", paths)

    def test_grep_is_repo_bounded(self) -> None:
        r = T.HANDLERS["fs.grep"]({"pattern": "x", "path": "../../.."})
        self.assertEqual(r["status"], "denied_scope")

    def test_grep_requires_pattern(self) -> None:
        self.assertEqual(T.HANDLERS["fs.grep"]({})["status"], "bad_args")

    def test_grep_registered_as_read_class(self) -> None:
        self.assertEqual(T.TOOL_SPEC["fs.grep"][0], "read")


class OpenAIToolsSchemaTests(unittest.TestCase):
    """to_openai_tools (masterplan §4 M5/D2-4): TOOL_SPEC rendered as the OpenAI
    tools/function-call JSON schema, so a native tool-calling client can drive
    the same registry the JSON-prompt sampler uses."""

    def setUp(self) -> None:
        self.schema = T.to_openai_tools()
        self.by_name = {t["function"]["name"]: t for t in self.schema}

    def test_every_tool_spec_entry_present(self) -> None:
        self.assertEqual(set(self.by_name), set(T.TOOL_SPEC))

    def test_each_entry_is_a_valid_function_schema_dict(self) -> None:
        for tool in self.schema:
            self.assertEqual(tool["type"], "function")
            fn = tool["function"]
            self.assertIsInstance(fn["name"], str)
            self.assertIsInstance(fn["description"], str)
            params = fn["parameters"]
            self.assertEqual(params["type"], "object")
            self.assertIsInstance(params["properties"], dict)

    def test_description_excludes_args_hint(self) -> None:
        desc = self.by_name["memory.retrieve"]["function"]["description"]
        self.assertNotIn("Args:", desc)

    def test_string_arg_parsed_from_hint(self) -> None:
        params = self.by_name["memory.retrieve"]["function"]["parameters"]
        self.assertEqual(params["properties"]["task"], {"type": "string"})
        self.assertIn("task", params["required"])

    def test_array_arg_parsed_from_hint(self) -> None:
        params = self.by_name["self.audit"]["function"]["parameters"]
        self.assertEqual(params["properties"]["claims"], {"type": "array", "items": {}})

    def test_empty_args_hint_yields_permissive_empty_object(self) -> None:
        params = self.by_name["fs.list"]["function"]["parameters"]
        self.assertEqual(params, {"type": "object", "properties": {}})

    def test_unparseable_hint_degrades_honestly_not_fabricated(self) -> None:
        # A hint with no "Args:" JSON at all must never invent parameter names.
        schema = T._args_hint_to_schema("No args hint here at all")
        self.assertEqual(schema, {"type": "object", "properties": {}})


class FsListTests(unittest.TestCase):
    """fs.list (masterplan §4 M5/D4-6 fix): no args -> pinned key-docs set
    (backward compatible); {"path", "glob"} -> a real bounded directory listing.
    Kills the doom-loop a fixed 9-doc list caused for goals outside docs/."""

    def test_no_args_returns_pinned_docs_backward_compatible(self) -> None:
        r = T.HANDLERS["fs.list"]({})
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["mode"], "pinned")
        self.assertIn("docs/AIOS_NORTHSTAR.md", [f["path"] for f in r["files"]])

    def test_path_arg_lists_a_real_directory(self) -> None:
        r = T.HANDLERS["fs.list"]({"path": "scripts", "glob": "aios_mcp_*.py"})
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["mode"], "directory")
        paths = {f["path"] for f in r["files"]}
        self.assertIn("scripts/aios_mcp_client.py", paths)
        self.assertIn("scripts/aios_mcp_server.py", paths)
        # glob excludes non-matching files
        self.assertNotIn("scripts/aios_tools.py", paths)

    def test_directory_listing_is_bounded_to_50_entries(self) -> None:
        r = T.HANDLERS["fs.list"]({"path": "scripts"})   # scripts/ has hundreds of files
        self.assertEqual(r["status"], "ok")
        self.assertLessEqual(r["count"], 50)
        self.assertLessEqual(len(r["files"]), 50)

    def test_path_is_repo_bounded_like_fs_grep(self) -> None:
        r = T.HANDLERS["fs.list"]({"path": "../../.."})
        self.assertEqual(r["status"], "denied_scope")

    def test_privacy_dirs_excluded(self) -> None:
        for privacy_path in ("_from_desktop", "dain", "minyoung"):
            r = T.HANDLERS["fs.list"]({"path": privacy_path})
            self.assertEqual(r["status"], "denied_scope", privacy_path)

    def test_nonexistent_directory_is_honest_not_found(self) -> None:
        r = T.HANDLERS["fs.list"]({"path": "no/such/dir/at/all"})
        self.assertEqual(r["status"], "not_found")

    def test_single_file_path_lists_just_that_file(self) -> None:
        r = T.HANDLERS["fs.list"]({"path": "scripts/aios_tools.py"})
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["count"], 1)
        self.assertEqual(r["files"][0]["path"], "scripts/aios_tools.py")
        self.assertEqual(r["files"][0]["type"], "file")

    def test_registered_as_read_class(self) -> None:
        self.assertEqual(T.TOOL_SPEC["fs.list"][0], "read")


class SkillUseWiringTests(unittest.TestCase):
    """skill.use (masterplan §4 M5/D4-6): the Agent Skills loader wired into
    the same tool registry as every other organ."""

    def test_registered_in_handlers_and_registry(self) -> None:
        self.assertIn("skill.use", T.HANDLERS)
        reg = T.build_registry()
        self.assertIn("skill.use", reg.handlers)

    def test_registered_as_advisory_class(self) -> None:
        self.assertEqual(T.TOOL_SPEC["skill.use"][0], "advisory")

    def test_loads_the_dogfood_driftbench_skill(self) -> None:
        r = T.HANDLERS["skill.use"]({"name": "aios-driftbench-prereg"})
        self.assertEqual(r["status"], "ok")
        self.assertIn("DriftBench", r["text"])

    def test_missing_skill_is_honest_not_found(self) -> None:
        r = T.HANDLERS["skill.use"]({"name": "no-such-skill-xyz"})
        self.assertEqual(r["status"], "not_found")
