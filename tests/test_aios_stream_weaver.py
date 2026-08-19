#!/usr/bin/env python3
"""Unit and Integration Tests for AIOS Structural Stream Weaver and Injection Engine."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from aios_stream_weaver import (
    MultiSourceHarvester,
    PromptPrisonCleaner,
    StructuredOutput,
    StreamWeaver,
)


class StreamWeaverTests(unittest.TestCase):
    def test_prompt_prison_cleaning(self):
        caged_text = (
            "Certainly! I'd be happy to help you implement a thread-safe cache.\n\n"
            "<think>Analyzing lock contention and memory footprint...</think>\n\n"
            "Here is the implementation:\n"
            "```python\n"
            "class SafeCache:\n"
            "    pass\n"
            "```\n"
            "Invariant: all locks must be released in finally blocks.\n"
            "Fail if concurrent writes exceed buffer capacity.\n\n"
            "Let me know if you need anything else!"
        )

        cleaned = PromptPrisonCleaner.clean(caged_text)
        self.assertNotIn("Certainly!", cleaned)
        self.assertNotIn("Let me know if you need anything else", cleaned)
        self.assertNotIn("<think>", cleaned)

        think = PromptPrisonCleaner.extract_think_trace(caged_text)
        self.assertEqual(think, "Analyzing lock contention and memory footprint...")

        code_blocks = PromptPrisonCleaner.extract_code_blocks(caged_text)
        self.assertEqual(len(code_blocks), 1)
        self.assertEqual(code_blocks[0]["lang"], "python")
        self.assertIn("class SafeCache", code_blocks[0]["code"])

        invs, falsifiers = PromptPrisonCleaner.extract_invariants_and_falsifiers(cleaned)
        self.assertTrue(any("locks must be released" in i for i in invs))
        self.assertTrue(any("concurrent writes" in f for f in falsifiers))

    def test_structural_output_parsing(self):
        raw = "```python\ndef run():\n    return 42\n```\n- Invariant: Return integer value only."
        struct = PromptPrisonCleaner.parse_structure(raw, "mock-qwen", "api", latency_s=0.12)
        self.assertEqual(struct.source_substrate, "mock-qwen")
        self.assertEqual(len(struct.code_blocks), 1)
        self.assertEqual(len(struct.invariants), 1)
        self.assertEqual(struct.latency_s, 0.12)

    def test_stream_weaver_pipeline_flow(self):
        weaver = StreamWeaver(timeout=5.0)
        # Force mock substrates for testing
        res = weaver.weave_ideation_to_code("Build high-performance message bus")
        self.assertEqual(res["schema"], "aios.stream_weaver.v1")
        self.assertIn("generated_code", res)
        self.assertIn("critic_verdict", res)
        self.assertEqual(len(res["pipeline_trail"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
