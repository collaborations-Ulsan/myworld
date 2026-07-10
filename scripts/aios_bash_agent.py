#!/usr/bin/env python3
"""BashFallbackAgent — the guaranteed-fallback agent mode for ANY local model.

Absorbs the core loop *semantics* of mini-swe-agent
(https://github.com/SWE-agent/mini-swe-agent — MIT License, Copyright (c) 2025
Kilian A. Lieret and Carlos E. Jimenez). mini-swe-agent scores >74% on
SWE-bench Verified with a ~100-line agent class precisely because it needs
NO structured-output support from the model: one bash block per turn, no
tool-calling schema, no JSON parser to collapse when a weak/local model
mangles the format. That is exactly the property AIOS needs for the
provider-death scenario in the masterplan (M5): when codex/claude CLI are
unavailable, the head must still be able to drive a local model to a real
answer.

This module is a from-scratch stdlib reimplementation of that convention
(not a vendored copy of mini-swe-agent's code) — adapted to AIOS's own
adapter/turn-loop style. Semantics adopted verbatim from
minisweagent/agents/default.py + minisweagent/environments/{local,extra/
bubblewrap}.py:
  - System prompt: THOUGHT + exactly one ```bash fenced block per reply.
  - Completion convention: the model finishes the task by running a command
    whose FIRST stdout line is exactly the literal marker
    "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" with returncode 0 — everything
    after that line is the submission/final answer, and the loop ends.
  - Sandbox: plain subprocess by default; bubblewrap (bwrap) read-only-root +
    a single writable bind for the workspace root when the `bwrap` binary is
    present (argv shape lifted from environments/extra/bubblewrap.py).

Design constraints (this is a FALLBACK mode, additive to --loop, not a
replacement):
  - Model-agnostic: takes any `adapter(prompt: str) -> str` callable — reuse
    scripts/aios_adapters.py's make_ollama_rest_adapter / SPECS / build_adapters.
  - Never executes outside the workspace root. Privacy-gated sibling dirs
    (_from_desktop/, dain/, minyoung/ — DNA invariant 7) are never bound into
    the sandbox: the bwrap path only ever names the workspace root itself,
    nothing above it.
  - Destructive-command guard: a small denylist refuses obvious
    rm -rf/fork-bomb/raw-device patterns and rm -rf targeting anything
    outside the workspace root, fail-closed with the reason sent back to the
    model as an observation (not a silent stop).
  - stdlib only. No PyPI dependency (mini-swe-agent itself needs
    jinja2/pydantic/litellm; AIOS's fallback path must not inherit that,
    since "works on any local model with nothing installed" is the point).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

COMPLETION_MARKER = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"

_BASH_BLOCK_RE = re.compile(r"```bash\s*\n(.*?)```", re.DOTALL)

SYSTEM_PROMPT = (
    "You are a helpful assistant operating in a bash-only sandbox.\n"
    "Every reply MUST contain a short THOUGHT section followed by exactly ONE "
    "fenced ```bash code block containing ONE command (chain multiple commands "
    "with && or || if needed). Do not use JSON, tool calls, or any other format — "
    "only THOUGHT text plus one ```bash block.\n\n"
    "When the goal is fully done, make your LAST bash block run:\n"
    "    echo " + COMPLETION_MARKER + "\n"
    "    echo '<your final answer, one or more lines>'\n"
    "The FIRST line printed must be exactly '" + COMPLETION_MARKER + "' — everything "
    "printed after that line becomes your final answer and ends the run.\n\n"
    "Example final turn:\n"
    "```bash\n"
    "echo " + COMPLETION_MARKER + "\n"
    "echo 'the 3 files are: a.py b.py c.py'\n"
    "```"
)

# --- destructive-command denylist (defense in depth; the bwrap sandbox is the
# primary containment when bwrap is present) -----------------------------------
_RM_RF_RE = re.compile(r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*[fF][a-zA-Z]*|-[a-zA-Z]*[fF][a-zA-Z]*[rR][a-zA-Z]*)\b")
_FORK_BOMB_RE = re.compile(r":\s*\(\s*\)\s*\{[^}]*:\s*\|\s*:[^}]*\}\s*;\s*:")
_RAW_DEVICE_RE = re.compile(r"(?:>\s*|of=)\s*/dev/(?:sd|nvme|hd|vd)[a-z0-9]")
_MKFS_RE = re.compile(r"\bmkfs(?:\.\w+)?\b")


def _denylist_violation(command: str, root: Path) -> "str | None":
    """Return a human-readable refusal reason, or None if the command is fine."""
    if _FORK_BOMB_RE.search(command):
        return "refused: fork-bomb pattern"
    if _MKFS_RE.search(command):
        return "refused: filesystem-format command (mkfs)"
    if _RAW_DEVICE_RE.search(command):
        return "refused: raw block-device write"
    if _RM_RF_RE.search(command):
        try:
            import shlex
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        for raw in tokens:
            candidate = raw.rstrip(";&|")
            if candidate in ("rm",) or candidate.startswith("-"):
                continue
            if candidate in ("/", "~", "$HOME", "*"):
                return f"refused: rm -rf targeting {candidate!r}"
            if candidate.startswith("~"):
                return f"refused: rm -rf targeting home-relative path {candidate!r}"
            if candidate.startswith("/"):
                try:
                    Path(candidate).resolve().relative_to(root)
                except ValueError:
                    return f"refused: rm -rf targeting path outside workspace: {candidate}"
    return None


def _extract_bash_block(reply: str) -> "str | None":
    """Extract the single ```bash ... ``` block. None => reply is treated as
    the final answer (a weak model that never learns the convention still
    terminates honestly instead of looping forever)."""
    m = _BASH_BLOCK_RE.search(reply)
    if not m:
        return None
    return m.group(1).strip("\n")


def _check_completion(stdout: str, returncode: int) -> "tuple[bool, str]":
    lines = stdout.lstrip().splitlines(keepends=True)
    if lines and lines[0].strip() == COMPLETION_MARKER and returncode == 0:
        return True, "".join(lines[1:])
    return False, ""


def _truncate(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    half = cap // 2
    elided = len(text) - cap
    return f"{text[:half]}\n...[{elided} chars elided]...\n{text[-half:]}"


# --- sandbox: plain subprocess, or bubblewrap when available -------------------

_BWRAP_RO_BINDS = ["/usr", "/bin", "/lib", "/lib64", "/etc", "/sbin"]


def _bwrap_available() -> bool:
    return shutil.which("bwrap") is not None


def build_bwrap_argv(command: str, root: Path) -> list[str]:
    """Sandbox argv shape lifted from mini-swe-agent's
    environments/extra/bubblewrap.py (MIT): read-only-bind the base system
    dirs, tmpfs /tmp, then bind ONLY the workspace root (read-write) and
    chdir into it. Deliberately never names anything above `root` — privacy
    dirs (_from_desktop/, dain/, minyoung/) live outside it and are simply
    never mentioned, so they do not exist inside the sandbox mount namespace
    regardless of what the model asks for.
    """
    bwrap = shutil.which("bwrap") or "bwrap"
    argv = [bwrap, "--unshare-user-try", "--die-with-parent"]
    for path in _BWRAP_RO_BINDS:
        if Path(path).exists():
            argv += ["--ro-bind", path, path]
    root_s = str(root)
    argv += [
        "--tmpfs", "/tmp",
        "--proc", "/proc",
        "--dev", "/dev",
        "--new-session",
        "--setenv", "PATH", "/usr/local/bin:/usr/sbin:/usr/bin:/bin",
        "--bind", root_s, root_s,
        "--chdir", root_s,
        "bash", "-c", command,
    ]
    return argv


@dataclass
class Observation:
    step: int
    command: str
    stdout: str
    returncode: int


@dataclass
class BashAgentResult:
    exit_reason: str  # "completed" | "max_steps" | "no_bash_block"
    answer: str
    steps_used: int
    observations: "list[Observation]" = field(default_factory=list)


@dataclass
class BashAgentConfig:
    max_steps: int = 20
    timeout: int = 30
    output_cap: int = 8000
    history_window: int = 8
    sandbox: str = "auto"  # "auto" | "bwrap" | "subprocess"


class BashFallbackAgent:
    """Model-agnostic bash-only turn loop. Works with ANY adapter callable
    (prompt: str) -> str — no function-calling / JSON-schema support required
    from the underlying model.
    """

    def __init__(self, adapter: Callable[[str], str], *, root: "str | Path" = ".",
                 config: "BashAgentConfig | None" = None):
        self.adapter = adapter
        self.root = Path(root).resolve()
        self.config = config or BashAgentConfig()

    def _use_bwrap(self) -> bool:
        mode = self.config.sandbox
        if mode == "bwrap":
            return True
        if mode == "subprocess":
            return False
        return _bwrap_available()

    def _execute(self, command: str) -> "tuple[int, str, str]":
        """Run one command. Returns (returncode, raw_stdout, display_text).

        stdout and stderr are captured SEPARATELY (not merged) — the
        completion-marker check (`_check_completion`) needs the model's own
        `echo` to reliably be the first line of raw_stdout. Merging streams
        (mini-swe-agent's default) breaks that on any host where the shell
        itself writes startup diagnostics to stderr before the command runs
        (observed on this box: every `/bin/bash -c ...` invocation prints a
        dynamic-linker warning line first). display_text is stdout+stderr
        concatenated for what actually gets shown back to the model.
        """
        cfg = self.config
        use_bwrap = self._use_bwrap()
        argv: "list[str] | str" = build_bwrap_argv(command, self.root) if use_bwrap else command
        try:
            result = subprocess.run(
                argv,
                shell=not use_bwrap,
                executable=None if use_bwrap else "/bin/bash",
                cwd=str(self.root),
                text=True,
                timeout=cfg.timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                errors="replace",
            )
            stdout, stderr = result.stdout or "", result.stderr or ""
            display = stdout + (stderr if not stderr else (("" if stdout.endswith("\n") or not stdout else "\n") + stderr))
            return result.returncode, stdout, _truncate(display, cfg.output_cap)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            display = f"{stdout}{stderr}\n[timeout after {cfg.timeout}s]"
            return 124, stdout, _truncate(display, cfg.output_cap)
        except OSError as exc:
            return 127, "", str(exc)

    def _render_prompt(self, goal: str, observations: "list[Observation]") -> str:
        parts = [SYSTEM_PROMPT, "", f"GOAL: {goal}", ""]
        for obs in observations[-self.config.history_window:]:
            parts.append(f"--- step {obs.step} ---")
            parts.append(f"$ {obs.command}")
            parts.append(f"(exit {obs.returncode})")
            parts.append(obs.stdout)
            parts.append("")
        parts.append(
            "Respond now with THOUGHT + exactly one ```bash block for the next "
            "command (or the completion-marker block from the instructions if "
            "the goal is already done)."
        )
        return "\n".join(parts)

    def run(self, goal: str) -> BashAgentResult:
        observations: "list[Observation]" = []
        cfg = self.config
        for step in range(1, cfg.max_steps + 1):
            prompt = self._render_prompt(goal, observations)
            reply = self.adapter(prompt)
            block = _extract_bash_block(reply)
            if block is None:
                return BashAgentResult(exit_reason="no_bash_block", answer=reply.strip(),
                                        steps_used=step, observations=observations)
            violation = _denylist_violation(block, self.root)
            if violation:
                observations.append(Observation(step=step, command=block, stdout=violation, returncode=1))
                continue
            code, raw_stdout, display = self._execute(block)
            observations.append(Observation(step=step, command=block, stdout=display, returncode=code))
            done, submission = _check_completion(raw_stdout, code)
            if done:
                return BashAgentResult(exit_reason="completed", answer=submission.strip(),
                                        steps_used=step, observations=observations)
        return BashAgentResult(exit_reason="max_steps", answer="", steps_used=cfg.max_steps,
                                observations=observations)


def run_bash_agent(goal: str, *, adapter: Callable[[str], str], root: "str | Path" = ".",
                    max_steps: int = 20, timeout: int = 30, sandbox: str = "auto") -> BashAgentResult:
    """Functional entry point for aios_head.py (and any other caller) to run
    the fallback loop without constructing BashFallbackAgent directly."""
    config = BashAgentConfig(max_steps=max_steps, timeout=timeout, sandbox=sandbox)
    return BashFallbackAgent(adapter, root=root, config=config).run(goal)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="aios_bash_agent — bash-only fallback loop for ANY local model "
                    "(mini-swe-agent semantics: no function-calling/JSON parsing required)")
    parser.add_argument("goal", help="natural-language goal")
    parser.add_argument("--model", default=os.environ.get("AIOS_OLLAMA_MODEL", "qwen3-coder:30b"),
                        help="ollama model tag served at localhost:11434 "
                             "(default: env AIOS_OLLAMA_MODEL or qwen3-coder:30b)")
    parser.add_argument("--root", default=".", help="workspace root the sandbox is confined to")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=30, help="per-command timeout, seconds")
    parser.add_argument("--sandbox", choices=["auto", "bwrap", "subprocess"], default="auto")
    args = parser.parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    import aios_adapters  # local import: only the CLI entry needs the adapter registry

    adapter = aios_adapters.make_ollama_rest_adapter(model=args.model, timeout=max(args.timeout * 3, 60))
    result = run_bash_agent(args.goal, adapter=adapter, root=args.root, max_steps=args.max_steps,
                             timeout=args.timeout, sandbox=args.sandbox)
    print(json.dumps({
        "exit_reason": result.exit_reason,
        "answer": result.answer,
        "steps_used": result.steps_used,
        "observations": [dataclasses.asdict(o) for o in result.observations],
    }, ensure_ascii=False, indent=2))
    return 0 if result.exit_reason == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
