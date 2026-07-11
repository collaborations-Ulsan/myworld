#!/usr/bin/env python3
"""AIOS Agent Skills loader (masterplan §4 M5/D4-6, survey §(g)2).

Opens the skills.sh (~89,753 skills) / ClawHub (13,700+) long tail to the
AIOS-native runtime by consuming the Agent Skills standard: a skill is a
directory containing SKILL.md (YAML frontmatter: name, description; body =
free-text instructions) plus optional resources (a scripts/ dir, references,
assets, ...). No function-calling schema is needed — the whole point is
instruction-injection: the model reads the skill body and follows it, which is
exactly the local/weak-model-friendly shape the survey's §(h) local-tool-calling
findings call for (function calling degrades hard under ~14B; prompted
instructions do not).

SECURITY (survey §(g)3 — "third-party skills need pre-ingest scanning; skill
supply-chain injection is a live 2026 attack surface"): this loader NEVER reads
a skill's script files for the purpose of executing them, and never shells out
to anything under a skill directory. It only returns text. Any skill directory
that ships script-looking files is flagged has_scripts=True in both discover()
and load(), and load() prepends a plain-text warning so the caller (and the
model reading the returned text) knows those scripts exist and are unvetted —
running them is an explicit separate decision this module never makes.
Ingestion in this leg is manual placement only: no network fetch of skills.

Schema: aios.skills_loader.v1
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "aios.skills_loader.v1"

DEFAULT_SEARCH_PATHS: tuple[Path, ...] = (
    ROOT / ".aios" / "skills",
    Path.home() / ".claude" / "skills",
)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
_BODY_TRUNCATE = 4000

# Executable-looking files under a skill dir mark it has_scripts=True. These are
# only ever *counted*, never opened for execution or shelled out to.
_SCRIPT_EXTS = {".py", ".sh", ".js", ".ts", ".rb", ".pl", ".bash"}
_SCRIPT_DIR_NAMES = {"scripts", "bin"}

_SCRIPT_WARNING = (
    "[SECURITY WARNING: this skill ships companion script files (scripts/ or "
    "similar). aios_skills_loader never executes them and never read them for "
    "you — it only returns this instruction text. Do not run those scripts "
    "without independently reviewing their contents first.]\n\n"
)


@dataclass
class SkillMeta:
    name: str
    description: str
    path: str            # absolute path to the skill directory
    has_scripts: bool
    source: str           # "aios" (.aios/skills) | "claude_global" (~/.claude/skills) | "custom"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "has_scripts": self.has_scripts,
            "source": self.source,
        }


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """-> (frontmatter dict, body text). Honest degrade: a missing/malformed
    frontmatter block yields an empty dict and the whole file as body — this
    loader never fabricates a name that isn't actually declared."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    body = text[m.end():]
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val:
            fm[key] = val
    return fm, body


def _has_scripts(skill_dir: Path) -> bool:
    for sub in _SCRIPT_DIR_NAMES:
        d = skill_dir / sub
        if d.is_dir() and any(p.is_file() for p in d.rglob("*")):
            return True
    for p in skill_dir.rglob("*"):
        if p.is_file() and p.suffix in _SCRIPT_EXTS and p.name != "SKILL.md":
            return True
    return False


def _source_label(search_root: Path) -> str:
    try:
        search_root.resolve().relative_to(ROOT)
        return "aios"
    except ValueError:
        pass
    try:
        search_root.resolve().relative_to(Path.home() / ".claude")
        return "claude_global"
    except ValueError:
        return "custom"


def discover(paths: list[Path] | None = None) -> list[SkillMeta]:
    """Scan default (or given) search-path roots for <root>/<skill-name>/SKILL.md.
    Read-only: never writes, never fetches over the network. Roots are searched
    in order and the first skill with a given name wins (so a local .aios/skills/
    entry can shadow a same-named ~/.claude/skills/ one)."""
    roots = list(paths) if paths is not None else list(DEFAULT_SEARCH_PATHS)
    out: list[SkillMeta] = []
    seen: set[str] = set()
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            skill_dir = skill_md.parent
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm, _body = _parse_frontmatter(text)
            name = fm.get("name") or skill_dir.name
            if name in seen:
                continue
            seen.add(name)
            out.append(SkillMeta(
                name=name,
                description=fm.get("description", "")[:300],
                path=str(skill_dir),
                has_scripts=_has_scripts(skill_dir),
                source=_source_label(root),
            ))
    return out


def load(name: str, paths: list[Path] | None = None) -> dict:
    """Return {"status": "ok", "name", "description", "has_scripts", "text"} for
    one skill's full instruction text (frontmatter body, truncated to 4000
    chars) — the inject-on-demand shape for the turn-loop "skill.use" tool.
    {"status": "not_found", "name": ...} if no skill by that name is discovered."""
    name = str(name or "").strip()
    if not name:
        return {"status": "bad_args", "detail": "name required"}
    for meta in discover(paths):
        if meta.name != name:
            continue
        skill_md = Path(meta.path) / "SKILL.md"
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"status": "error", "reason": f"unreadable: {exc}"}
        truncated = text[:_BODY_TRUNCATE]
        if len(text) > _BODY_TRUNCATE:
            truncated += "\n\n[...truncated]"
        if meta.has_scripts:
            truncated = _SCRIPT_WARNING + truncated
        return {
            "status": "ok",
            "name": meta.name,
            "description": meta.description,
            "has_scripts": meta.has_scripts,
            "text": truncated,
        }
    return {"status": "not_found", "name": name}


def list_skills(paths: list[Path] | None = None) -> list[dict]:
    return [m.to_dict() for m in discover(paths)]


def tool_skill_use(arguments: dict) -> dict:
    """Turn-loop tool handler for "skill.use": {"name": "<skill name>"} -> the
    skill body (see load()). Registered into aios_tools.HANDLERS."""
    name = str((arguments or {}).get("name", "")).strip()
    if not name:
        return {"status": "bad_args", "detail": "name required"}
    return load(name)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--load", metavar="NAME", help="print one skill's full text")
    args = p.parse_args(argv)
    if args.load:
        result = load(args.load)
    else:
        skills = list_skills()
        result = {"schema_version": SCHEMA_VERSION, "count": len(skills), "skills": skills}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
