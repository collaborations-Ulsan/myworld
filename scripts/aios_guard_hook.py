#!/usr/bin/env python3
"""PreToolUse enforcement hook for the AIOS operator harness.

Turns the harness from advisory prose into enforcement (gemini review #2,
founder directive "진짜 AIOS를 위해서 모든 리스크 감수"):
- BLOCKS a `git commit` when aios_commit_guard finds ERRORs (e.g. an embedded
  git repo staged as a gitlink with no .gitmodules entry).
- BLOCKS creating a contract (Write to docs/contracts/ASC-*.md) when no fresh
  4-OS ritual token exists.

FAILS OPEN: any internal/parse/subprocess error returns 0 (allow), so a hook
malfunction never blocks legitimate work — we accept the risk of a missed block,
never the risk of a frozen session.

Wire: PreToolUse matcher "Bash|Write". Reads the PreToolUse JSON on stdin.
Schema: aios.guard_hook.v1
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
# Write-tool target path (trailing guard avoids ASC-1.md.bak etc.).
CONTRACT_PATH = re.compile(r"docs/contracts/ASC-[^/\s]*\.md(?![\w.])")
# Bash contract CREATION: a redirect/tee whose target IS a contract path. Must be
# tight — matching any `>` in a command that merely mentions a contract path
# false-blocks innocuous commands (e.g. `... 2>/dev/null`). Only `> <contract>` /
# `>> <contract>` / `tee <contract>` count.
BASH_CONTRACT_WRITE = re.compile(r"(?:>>?|\btee\b)\s+\S*docs/contracts/ASC-[^/\s]*\.md")


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def inject(context: str) -> None:
    """Allow the tool but inject advisory context into agent reasoning."""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": context,
                }
            }
        )
    )
    sys.exit(0)


# Irreversible patterns — GenesisOS challenge injection (allow but warn)
_RISKY = [
    (re.compile(r'\brm\s+-[rf]{1,2}\b'), "rm -rf"),
    (re.compile(r'git\s+push\s+--force'), "force push"),
    (re.compile(r'git\s+reset\s+--hard'), "git reset --hard"),
    (re.compile(r'\bDROP\s+TABLE\b', re.I), "DROP TABLE"),
    (re.compile(r'\btruncate\s+table\b', re.I), "TRUNCATE TABLE"),
    (re.compile(r'dd\s+if='), "dd (disk write)"),
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    cmd = ti.get("command") or ""

    # 0. shared-resource guard.
    #
    # 2026-08-18: I stopped and upgraded the ollama daemon, and only afterwards read the
    # memory saying "Ollama 내리기 전 반드시 파운더에게 교수님 공유 여부 확인할 것" —
    # this box may be shared with the professor. No one was connected, so the impact was
    # zero, but that was luck rather than process: the constraint lived in a memory file
    # that gets read when I happen to look, not at the moment of the action.
    #
    # So it fires here instead. A rule that depends on remembering is not a rule.
    SHARED_STOP = re.compile(
        r"(?:pkill|killall|kill\s+-9?)\s+.*ollama|ollama\s+(?:stop|serve)|"
        r"systemctl\s+(?:stop|restart)\s+ollama")
    if tool == "Bash" and SHARED_STOP.search(cmd):
        inject(
            "SHARED RESOURCE — the ollama daemon on this box may be shared with the "
            "professor (memory: reference_local_llm_assets, 2026-06-21: confirm with the "
            "founder before taking ollama down).\n"
            "Before proceeding: check `ss -tn state established` for remote clients and "
            "`curl -s localhost:11434/api/ps` for resident models someone else may be using. "
            "Prefer `keep_alive=0` eviction (reversible, no downtime) over stopping the "
            "daemon. If a restart is genuinely required, say so and confirm."
        )

    # 1. commit guard
    if tool == "Bash" and "git commit" in cmd:
        try:
            r = subprocess.run(
                [PY, str(ROOT / "scripts" / "aios_commit_guard.py"), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=15,
            )
            res = json.loads(r.stdout)
        except Exception:
            return 0  # guard crashed → fail open
        errors = [f for f in res.get("findings", []) if f.get("level") == "error"]
        if errors:
            lines = "\n".join(f"- {f['message']}" for f in errors)
            deny(
                "AIOS commit-guard blocked this commit:\n"
                + lines
                + "\nFix the ERROR (e.g. `git rm --cached <gitlink>`), then retry."
            )

    # 3. GenesisOS: irreversible pattern challenge (inject, don't block)
    if tool == "Bash":
        for pattern, label in _RISKY:
            if pattern.search(cmd):
                inject(
                    f"GenesisOS challenge — '{label}' is irreversible.\n"
                    "Before proceeding, verify: "
                    "(1) Is this the right target? "
                    "(2) Is there a backup or easy undo? "
                    "(3) Has this been dry-run or tested? "
                    "If all three are confirmed, proceed. "
                    "Otherwise pause and re-examine the assumption."
                )

    # 2. contract-creation ritual gate — via the Write tool OR via a shell write
    #    (echo > / tee / cp …), so the gate can't be bypassed through Bash.
    creating_contract = (
        tool == "Write" and bool(CONTRACT_PATH.search(ti.get("file_path") or ""))
    ) or (
        tool == "Bash" and bool(BASH_CONTRACT_WRITE.search(cmd))
    )
    if creating_contract:
        try:
            rc = subprocess.run(
                [PY, str(ROOT / "scripts" / "aios_ritual_gate.py"), "check", "--max-age-min", "60"],
                cwd=ROOT,
                capture_output=True,
                timeout=10,
            ).returncode
        except Exception:
            return 0  # fail open
        if rc != 0:
            deny(
                "Contract creation blocked: no fresh 4-OS decision trace (<60min). "
                "Run /aios-decide (MemoryOS recall + CapabilityOS route + GenesisOS "
                "challenge + Hive verify), or `python scripts/aios_ritual_gate.py record`, "
                "then write the contract."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
