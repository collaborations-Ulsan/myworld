# Dynamic Knowledge Graphs & Memory Consolidation (2026)

Knowledge representation for agents has shifted from static vector databases to Dynamic Knowledge Graphs (DKGs) that support long-term memory consolidation and historical tracking.

## Dynamic Knowledge Graphs (DKGs)
- **Temporal Metadata:** DKGs implement bi-temporal modeling (e.g., `valid_at` vs. `recorded_at` timestamps) to maintain a revision-conscious archive.
- **Invalidate-Not-Delete Strategy:** Facts are superseded rather than removed. This allows agents to retain a historical trace of their evolving world view, preventing the collapse of context across long time horizons.
- **Memory Consolidation:** Like biological sleep, consolidation decays outdated information and subsumes redundant facts into structural knowledge.

## STARK Benchmark & Framework
While STARK generally refers to a "Strategic Team of Agents for Refining Kernels" in multi-agent hardware optimization, the **STaRK Benchmark** evaluates LLM retrieval on semi-structured knowledge bases, assessing how effectively models handle textual and relational data in complex, dynamic graphs.
