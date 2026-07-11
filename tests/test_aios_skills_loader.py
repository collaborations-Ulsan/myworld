"""Agent Skills (SKILL.md) loader (masterplan §4 M5/D4-6): discover/load skills
from .aios/skills/ and ~/.claude/skills/ without ever executing anything under
a skill directory -- it only ever returns text.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_skills_loader as S


def _write_skill(root: Path, name: str, description: str = "does a thing",
                  body: str = "Follow these steps.\n", scripts: list[str] | None = None) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}", encoding="utf-8")
    for rel in scripts or []:
        p = skill_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/usr/bin/env python3\nprint('hi')\n", encoding="utf-8")
    return skill_dir


class DiscoverTests(unittest.TestCase):
    def test_discovers_skills_with_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "alpha", description="alpha skill")
            _write_skill(root, "beta", description="beta skill")
            metas = S.discover([root])
            names = {m.name for m in metas}
            self.assertEqual(names, {"alpha", "beta"})
            by_name = {m.name: m for m in metas}
            self.assertEqual(by_name["alpha"].description, "alpha skill")

    def test_ignores_dirs_without_skill_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "not_a_skill").mkdir()
            (root / "not_a_skill" / "README.md").write_text("nope", encoding="utf-8")
            self.assertEqual(S.discover([root]), [])

    def test_missing_search_path_degrades_to_empty_list(self) -> None:
        self.assertEqual(S.discover([Path("/nonexistent/aios/skills/path/xyz")]), [])

    def test_earlier_root_shadows_later_same_name(self) -> None:
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            r1, r2 = Path(td1), Path(td2)
            _write_skill(r1, "dup", description="from root1")
            _write_skill(r2, "dup", description="from root2")
            metas = S.discover([r1, r2])
            self.assertEqual(len(metas), 1)
            self.assertEqual(metas[0].description, "from root1")

    def test_missing_name_frontmatter_falls_back_to_dir_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / "fallback-name"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\ndescription: no name field here\n---\nBody text.\n", encoding="utf-8")
            metas = S.discover([root])
            self.assertEqual(metas[0].name, "fallback-name")


class HasScriptsTests(unittest.TestCase):
    def test_scripts_dir_flags_has_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "withscript", scripts=["scripts/run.py"])
            meta = S.discover([root])[0]
            self.assertTrue(meta.has_scripts)

    def test_no_scripts_dir_and_no_script_files_is_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "clean")
            meta = S.discover([root])[0]
            self.assertFalse(meta.has_scripts)

    def test_loose_script_file_outside_scripts_dir_also_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "loose", scripts=["helper.sh"])
            meta = S.discover([root])[0]
            self.assertTrue(meta.has_scripts)


class LoadTests(unittest.TestCase):
    def test_load_returns_frontmatter_and_body(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "orient", description="orientation skill", body="Step 1. Step 2.\n")
            result = S.load("orient", [root])
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["name"], "orient")
            self.assertEqual(result["description"], "orientation skill")
            self.assertIn("Step 1. Step 2.", result["text"])
            self.assertFalse(result["has_scripts"])

    def test_load_missing_skill_is_honest_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = S.load("does-not-exist", [Path(td)])
            self.assertEqual(result, {"status": "not_found", "name": "does-not-exist"})

    def test_load_empty_name_is_bad_args(self) -> None:
        self.assertEqual(S.load("")["status"], "bad_args")

    def test_load_truncates_long_body_at_4000_chars(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            long_body = "x" * 10_000
            _write_skill(root, "long", body=long_body)
            result = S.load("long", [root])
            self.assertEqual(result["status"], "ok")
            self.assertLess(len(result["text"]), 10_000)
            self.assertIn("[...truncated]", result["text"])

    def test_load_with_scripts_prepends_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "risky", scripts=["scripts/do_stuff.py"])
            result = S.load("risky", [root])
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["has_scripts"])
            self.assertIn("SECURITY WARNING", result["text"])
            self.assertIn("never executes", result["text"])

    def test_load_never_reads_script_file_contents_into_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "secretscript", scripts=["scripts/leak.py"])
            (root / "secretscript" / "scripts" / "leak.py").write_text(
                "SUPER_SECRET_MARKER_TOKEN = 1\n", encoding="utf-8")
            result = S.load("secretscript", [root])
            self.assertNotIn("SUPER_SECRET_MARKER_TOKEN", result["text"])


class ToolSkillUseTests(unittest.TestCase):
    """The turn-loop tool handler shape registered in aios_tools.HANDLERS."""

    def test_tool_skill_use_requires_name(self) -> None:
        self.assertEqual(S.tool_skill_use({})["status"], "bad_args")
        self.assertEqual(S.tool_skill_use({"name": ""})["status"], "bad_args")

    def test_tool_skill_use_finds_the_dogfood_skill(self) -> None:
        # .aios/skills/aios-driftbench-prereg/SKILL.md is a default search path --
        # this is the live wiring check the masterplan's D4-6 step asks for.
        result = S.tool_skill_use({"name": "aios-driftbench-prereg"})
        self.assertEqual(result["status"], "ok")
        self.assertIn("DriftBench", result["text"])
        self.assertFalse(result["has_scripts"])


class ListSkillsTests(unittest.TestCase):
    def test_list_skills_returns_plain_dicts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_skill(root, "one")
            out = S.list_skills([root])
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["name"], "one")
            self.assertIn("has_scripts", out[0])
            self.assertIn("source", out[0])


if __name__ == "__main__":
    unittest.main()
