#!/usr/bin/env python3
"""m2_driftbench trace — full per-run JSONL trace capture (ASC-0282 WP-B).

One JSONL file per (instance, arm) run. Records carry a monotonic `seq` (the
replay order WP-C's ablation-replay engine consumes: replay recorded outputs
to the first divergence, then the frozen policy continues) plus a wall
timestamp (informational only — replay keys on seq, never wall-clock).

Captured record kinds:
  model_io        every prompt + raw model output + token estimate (sampler)
  run_loop:*      every run_loop event forwarded via turn_sink — trajectory
                  entries, epistemic_gate verdicts (with certificates incl.
                  `_disabled_organs`), turn_context, plan_repair, ...
  env_event       drift applications / final_action from EpisodeEnv
  episode_meta    run header (arm, template, seed, model)

Traces are receipts (O16): they must never contain secrets — the harness puts
none in (no keys are read anywhere in this packet), and grader
verdicts/specs are NEVER written here (the agent-visible loop and the trace
share content; grader material stays in the orchestrator receipt only).

stdlib only.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path


class TraceWriter:
    """Append-only JSONL trace with a monotonic seq counter."""

    def __init__(self, path: "Path | str"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")
        self._seq = 0

    def write(self, record: dict) -> None:
        rec = {"seq": self._seq,
               "wall_ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               **record}
        self._seq += 1
        self._fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()

    def model_io(self, turn: int, prompt: str, raw_output: str,
                 prompt_tokens: int, completion_tokens: int, source: str = "agent") -> None:
        self.write({"kind": "model_io", "turn": turn, "source": source,
                    "prompt": prompt, "raw_output": raw_output,
                    "prompt_tokens_est": prompt_tokens,
                    "completion_tokens_est": completion_tokens})

    def env_event(self, event: dict) -> None:
        body = {k: v for k, v in event.items() if k != "kind"}
        self.write({**body, "kind": "env_event", "event_kind": event.get("kind")})

    def run_loop_event(self, rec: dict) -> None:
        self.write({**rec, "kind": f"run_loop:{rec.get('kind', 'unknown')}"})

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


def load_trace(path: "Path | str") -> list[dict]:
    """Read a trace back (tests + WP-C replay)."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out
