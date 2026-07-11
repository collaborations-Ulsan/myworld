#!/usr/bin/env python3
"""m2_driftbench meter — token accounting, single frozen denominator (ASC-0282 WP-B).

Denominator (prereg v1.1 §B, frozen): ALL model tokens consumed by the arm,
INCLUDING gate llm-judge calls, runtime-internal calls, sub-agent spawns and
retrieval. Wall-clock and action-count are reported separately and are NEVER
substitutable for tokens. Changing the denominator post hoc is a protocol
violation.

Honesty over precision: the reused ollama REST adapter
(scripts/aios_adapters.py:make_ollama_rest_adapter) returns only the reply
content string — it exposes NO usage info — so this packet counts a DOCUMENTED
estimate, ceil(chars/4), and every such entry is marked estimate=true in the
receipts. `add_exact` exists for future adapters that do return usage.

Known gap (named, this packet): the gate's llm-judge mode makes its adapter
call INTERNALLY (scripts/aios_epistemic_gate.py:_gate_llm_judge), invisible to
this meter — so the weak+llm-judge arm is NOT metered correctly yet and stays
a NotImplementedError stub in agent_arm.py until the freeze packet wires a
metered adapter through that seam. The organs gate is contractually
zero-LLM-call (gate module docstring), so weak+aios needs no such wiring.

stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """Documented estimate: ceil(len/4) chars-per-token; 0 for empty."""
    if not text:
        return 0
    return int(math.ceil(len(text) / 4.0))


@dataclass
class TokenMeter:
    """Accumulates per-model-call token counts for ONE arm on ONE instance."""
    ceiling: int = 60_000            # per-instance hard ceiling (dev default)
    entries: list = field(default_factory=list)
    wall_s: float = 0.0              # reported separately, never substituted
    action_count: int = 0            # reported separately, never substituted

    def add_model_call(self, prompt: str, completion: str, source: str = "agent") -> dict:
        e = {"source": source, "estimate": True,
             "prompt_tokens": estimate_tokens(prompt),
             "completion_tokens": estimate_tokens(completion)}
        self.entries.append(e)
        return e

    def add_exact(self, prompt_tokens: int, completion_tokens: int, source: str = "agent") -> dict:
        e = {"source": source, "estimate": False,
             "prompt_tokens": int(prompt_tokens),
             "completion_tokens": int(completion_tokens)}
        self.entries.append(e)
        return e

    @property
    def prompt_tokens(self) -> int:
        return sum(e["prompt_tokens"] for e in self.entries)

    @property
    def completion_tokens(self) -> int:
        return sum(e["completion_tokens"] for e in self.entries)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def over_budget(self) -> bool:
        return self.total_tokens > self.ceiling

    @property
    def any_estimate(self) -> bool:
        return any(e["estimate"] for e in self.entries)

    def to_dict(self) -> dict:
        return {
            "schema": "m2.meter.v1",
            "denominator": "all model tokens incl. gate calls (prereg v1.1 §B)",
            "model_calls": len(self.entries),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimate": self.any_estimate,
            "estimate_method": "ceil(chars/4); adapter exposes no usage info",
            "ceiling": self.ceiling,
            "over_budget": self.over_budget,
            "wall_s": round(self.wall_s, 3),
            "action_count": self.action_count,
        }
