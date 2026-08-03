# Semantic Mutation Notes

This sprint adds a shadow-branch GenesisOS prototype:

- Input: a failed Python function, its external failing unit test, and error text.
- Mutation operator: local Ollama chat at `http://localhost:11434/api/chat`,
  trying `qwen3-coder:30b` then `qwen3:8b`.
- Offline degradation: if Ollama is unavailable, malformed, disabled, or times
  out, deterministic AST mutations generate a bounded candidate set.
- Selection: each candidate is evaluated only through
  `scripts/aios_sandbox.py::run_untrusted_code`. A missing or unavailable
  sandbox is a refusal, never an unsandboxed run.
- Lineage: every evaluated candidate appends one JSONL record to a caller-chosen
  lineage path, defaulting to
  `experiments/evolution_sprint/semantic_mutation_lineage.jsonl`.
- Shadow discipline: survivors are reported only. The prototype never writes to
  `scripts/`, never registers a skill, and never auto-promotes code.

Run the demo:

```bash
python3 experiments/evolution_sprint/semantic_mutation.py --demo --no-llm --n 6
```

Run the test gate:

```bash
timeout 180 python3 -m pytest experiments/evolution_sprint/test_semantic_mutation.py -q
```

Honest limitations:

- The local model is a mutation source, not trusted execution. The sandboxed unit
  test is the selector.
- Offline AST mutations are intentionally small; they can repair simple operator
  and boolean mistakes but are not general program synthesis.
- A survivor means only that the supplied unit test passed in the sandbox.
- This experiment does not alter the AIOS kernel files or the skill registry.

