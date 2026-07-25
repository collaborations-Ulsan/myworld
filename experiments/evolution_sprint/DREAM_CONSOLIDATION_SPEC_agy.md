# DREAM / consolidation spec — heterogeneous design pass (agy/Gemini, 2026-07-25)

**Provenance**: produced by the `agy` (Gemini) substrate in the side volume lane, prompted with our REAL
verified state (append-only experience graph, sandbox-gated skill registry, 1233/1872/72 ontology) and our
hard constraints (no daemon, append-only, anti-reward-hacking, stdlib+local models).

## claude@myworld's adoption verdict (read this before the spec)

**ADOPT NOW — 2 pieces, both fix gaps I flagged myself:**
1. **Property/mutation fuzzing at the skill gate.** My Phase-4 honest limitation was *"gate strength = unit
   test strength — a weak test admits a weak skill."* This spec's guard is exactly the fix: the sandbox gate
   must not only run the generator's own test but inject mutated inputs / boundary values / fault conditions;
   a candidate that breaks under fuzzing is discarded. This hardens `scripts/aios_skills.py` against
   overfitted-to-noise skills. **Highest-value item in the whole side lane.**
2. **TER + SUR as the organism's anti-theater metrics, with numeric kill thresholds.**
   - `TER = mean steps-to-completion BEFORE consolidation / AFTER` (per task class)
   - `SUR = downstream runs that actually invoke a promoted skill / opportunities`
   - Kill rule: TER ≤ 1.05 **or** SUR < 0.05 **or** dream compute > 10% of total → auto-disable the organ,
     log the alert, revert to raw retrieval.
   **SUR is the cheap operational form of the Phase-5 question** ("does the compounding organ actually
   compound?"): if promoted skills are never reused, Phase 4 is theater, by measurement not opinion.

**ADOPT LATER**: Merkle *revocation* chain (append a REVOCATION_RECORD and mark derived artifacts
INVALIDATED — append-only-compatible, no deletion) for provenance poisoning; support-counting (≥3 distinct
run lineages) against ontology bloat.

**DO NOT COPY VERBATIM (invented specifics, not our system):** `/var/aios/...` paths (ours is `.aios/`),
`aios-dream/v2.1.0`, a "containerized OS sandbox" (ours is netns + Landlock, not containers), and the
suggested model tags (unverified). Treat the spec's *mechanisms* as the contribution, its *identifiers* as
placeholders.

**Its own honest boundary (kept):** semantic-intent vs spec-completeness, temporal-vs-epistemic
contradiction, and textual quality CANNOT be auto-validated — those need operator review.

---

# AIOS DREAM / Memory Consolidation Engine: Architectural Specification

## 1. System Overview & Execution Architecture

The **DREAM** (Deterministic Reduction & Episodic Artifact Mining) subsystem upgrades AIOS from metadata-only log passing to true structural memory consolidation.

### Hard Constraints Compliance
* **Execution Model**: Short-lived, zero-daemon CLI (`aios-dream run --since <checkpoint>`). Woken via `cron` or `inotify` triggers on episodic log size. Reads disk, processes, appends derived structure, exits.
* **Storage Model**: Strict append-only log structured storage (`/var/aios/ledger/consolidated.jsonl` & Merkle graph additions). Original episodic runs are never modified or purged.
* **Anti-Reward-Hacking**: The consolidator engine (local LLM via `ollama` + stdlib orchestration) is an untrusted generator. Zero candidate artifacts are promoted without passing an isolated, non-LLM external gate.
* **Dependencies**: Python 3.11+ stdlib (`sqlite3`, `hashlib`, `json`, `subprocess`, `pathlib`) + local `ollama` HTTP API (`http://127.0.0.1:11434`). Zero cloud endpoints.

---

## 2. Consolidation Pipeline Stages

```
   +-----------------------+
   |   Episodic Logs &     |
   |   Experience Graph    |
   +-----------+-----------+
               |
               v
 [Stage 1: Delta Ingestion & Windowing]
               |  (IngestedBatch)
               v
 [Stage 2: Pattern Extraction & Candidate Synthesis] (Local LLM / Heuristics)
               |  (CandidateArtifact[])
               v
 [Stage 3: External Gate Routing & Validation]      (OS Sandbox / Graph Engine)
               |  (VerifiedArtifact[])
               v
 [Stage 4: Append & Merkle Graph Commitment]        (Disk Ledger Update)
```

### Stage 1: Delta Ingestion & Windowing
* **Input**: Last processed Merkle root hash $H_{\text{prev}}$, path to raw experience graph (`/var/aios/experience/runs.jsonl`).
* **Transform**: Scans log records appended since $H_{\text{prev}}$. Groups records into trajectory windows by task type, domain, and error signature.
* **Output**: `IngestedBatch` payload containing raw run IDs $[R_1, R_2, \dots, R_n]$, window metadata, and range Merkle digest $H_{\text{batch}}$.

### Stage 2: Pattern Extraction & Candidate Synthesis
* **Input**: `IngestedBatch` + current snapshot of Ontology Knowledge Ledger (1,233 nodes / 1,872 edges).
* **Transform**: Prompts local LLM (`ollama run qwen2.5-coder:14b` or `llama3.2:3b`) via stdlib HTTP requests to extract candidate patterns across three target schemas:
  1. *Semantic Summaries* (compressing $N$ episodic trajectories into generalized workflows).
  2. *Skill Candidates* (code snippets + proposed unit tests for recurring failure fixes).
  3. *Ontology Contradictions* (conflicting assertions detected between new runs and ledger nodes).
* **Output**: Array of unverified `CandidateArtifact` objects written to staging buffer `/var/aios/dream/staging/<batch_id>.json`.

### Stage 3: External Gate Routing & Validation
* **Input**: `CandidateArtifact[]` from staging buffer.
* **Transform**: Passes every candidate through its mandatory, type-specific **External Check**:
  * *Skill Candidate* $\rightarrow$ AIOS Sandbox Test Harness. Runs candidate unit test against candidate code inside containerized OS sandbox. Must pass with $100\%$ success rate and zero policy violations.
  * *Semantic Summary* $\rightarrow$ Deterministic Ontology Graph Engine. Checks DAG integrity, node schema compliance, and cycle prevention.
  * *Contradiction Task* $\rightarrow$ Operator Queue Formatter. Checks against existing 72 explicit contradiction edges; generates a human-review diff packet if novel.
* **Output**: `VerifiedArtifact[]` with attached cryptographic proof of test execution or graph validation. (Failed candidates are logged to `/var/aios/dream/rejected.jsonl` with failure trace).

### Stage 4: Append & Merkle Graph Commitment
* **Input**: `VerifiedArtifact[]`.
* **Transform**: Formats records to canonical JSON, appends to `/var/aios/ledger/consolidated.jsonl`, updates index pointer, and re-computes Merkle root $H_{\text{new}} = \text{SHA256}(H_{\text{prev}} \parallel H_{\text{artifacts}})$.
* **Output**: Process exits `0` with single summary JSON emitted to `stdout`.

---

## 3. Consolidated Artifact Record Schema

All consolidated records follow a unified immutable schema with mandatory provenance links:

```json
{
  "$schema": "https://aios.dev/schemas/v1/consolidated_artifact.json",
  "artifact_id": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "artifact_type": "SKILL_CANDIDATE | SEMANTIC_SUMMARY | CONTRADICTION_TASK",
  "created_at": "2026-07-25T18:19:07Z",
  "consolidator_version": "aios-dream/v2.1.0",
  "generator_model": "ollama:qwen2.5-coder:14b",
  "provenance": {
    "parent_run_ids": [
      "run-8841-9a",
      "run-8902-1b",
      "run-9120-4f"
    ],
    "source_merkle_roots": [
      "sha256:1a2b3c4d...",
      "sha256:5e6f7g8h..."
    ],
    "trajectory_span": {
      "start_time": "2026-07-24T00:00:00Z",
      "end_time": "2026-07-25T12:00:00Z"
    }
  },
  "payload": {
    "title": "Postgres TLS Certificate Renewal Recovery Pattern",
    "summary": "When socket error 104 occurs during TLS cert renewal, clear stale connection pool before retrying handshake.",
    "code_binding": {
      "language": "python",
      "entrypoint": "skills/net/pg_tls_recover.py",
      "code_hash": "sha256:9f8e7d6c..."
    },
    "ontology_delta": {
      "add_nodes": [{"id": "node_pg_tls_err", "label": "ErrSocket104"}],
      "add_edges": [{"source": "node_pg_tls_err", "target": "skill_pg_tls_recover", "relation": "RESOLVED_BY"}]
    }
  },
  "verification_gate": {
    "verifier_type": "OS_SANDBOX_UNIT_TEST | ONTOLOGY_GRAPH_CHECK | HUMAN_OPERATOR_REVIEW",
    "status": "PASSED",
    "executed_at": "2026-07-25T18:19:05Z",
    "verifier_output_hash": "sha256:4d3c2b1a...",
    "gate_metadata": {
      "sandbox_exit_code": 0,
      "test_cases_passed": 4,
      "test_cases_failed": 0,
      "sandbox_duration_ms": 1420
    }
  },
  "artifact_hash": "sha256:..." 
}
```

### Merkle Hash Rule
`artifact_id` is computed as:
$$\text{SHA256}(\text{artifact\_type} \parallel \text{provenance.parent\_run\_ids} \parallel \text{payload} \parallel \text{verification\_gate.verifier\_output\_hash})$$

---

## 4. Promotion vs. Discard Rules & Verification Gates

| Target Artifact Type | Candidate Source Pattern | Promotion Threshold / Criterion | Mandatory External Gate | Discard / Quarantine Action |
| :--- | :--- | :--- | :--- | :--- |
| **Semantic Summary** | $\ge 3$ distinct runs with identical sub-goal structure & high semantic similarity. | No structural conflict with existing 1,872 edges. Deduplication score $< 0.85$ against existing summary nodes. | **Deterministic Graph Engine**: Must validate zero DAG cycles, strict JSON-Schema compliance, and zero edge conflicts. | **Discarded**: Logged to `rejected.jsonl` if redundant or structurally invalid. |
| **Skill Candidate** | $\ge 2$ instances of task failure resolved by similar manual/ad-hoc intervention steps. | Local LLM synthesizes standalone Python function + unit test suite. | **AIOS OS Sandbox**: Executes candidate test suite in isolated process. Must achieve 100% test pass, zero network/FS violations, exit code 0. | **Quarantined**: Kept in draft storage if tests fail; never registered to Skill Registry. |
| **Contradiction Task** | Run output asserts fact $A$, while Ledger contains node/edge asserting $\neg A$. | Overlaps with existing 72 contradiction edges or forms a new mutually exclusive triple $(S, P, O) \times (S, P, \neg O)$. | **Operator Review Queue**: Formatted into an actionable Markdown review packet (`/var/aios/review/ct_<id>.md`). | **Deferred**: Suspended from ontology graph until human sign-off or explicit conflict rule resolution. |

---

## 5. Anti-Theater Metric & Kill Thresholds

### The Primary Metric: Trajectory Efficiency Ratio ($TER$)
To prevent memory consolidation from becoming empty compute theater, we track whether consolidated artifacts measurably improve future agent execution.

$$TER = \frac{\text{Mean Steps to Completion for Task Class } T \text{ (Pre-Consolidation)}}{\text{Mean Steps to Completion for Task Class } T \text{ (Post-Consolidation)}}$$

Secondary Metric: **Skill Utilization Rate ($SUR$)**
$$SUR = \frac{\text{Downstream Task Runs Executing Promoted Skill } S}{\text{Total Opportunities for Skill } S \text{ over 30 Days}}$$

### The Numerical Kill Threshold
During a rolling evaluation window of **30 consolidation runs or 14 days**:

1. If $TER \le 1.05$ (less than $5\%$ reduction in task steps across recurring task classes), **OR**
2. If $SUR < 0.05$ (less than $5\%$ of promoted skills are actually invoked by downstream runs), **OR**
3. If the total compute energy/time spent in `aios-dream` exceeds **$10\%$ of total AIOS runtime compute**:

$$\mathbf{ACTION: \text{KILL THIS ORGAN}}$$
The CLI script automatically disables auto-wake triggers (`cron`/`inotify`), logs a `SYSTEM_ALERT_DREAM_ORGAN_DISABLED` event to the experience graph, and reverts to raw episodic retrieval until manual operator re-calibration.

---

## 6. Failure Modes & Defense Guards

### 1. Hallucinated Skill Synthesis (Overfitting to Noise)
* **Failure Mode**: The local consolidator LLM observes a run that succeeded by coincidence (e.g., race condition or transient network recovery) and synthesizes a fragile, overfitted skill with a trivial unit test.
* **Guard**: **Multi-Input Property Fuzzing in Sandbox**. The sandbox gate does not just run the generator's provided test; it injects mutated inputs, boundary values, and simulated latency/failure conditions into the candidate skill test harness. If the test breaks under fuzzing, the candidate is discarded.

### 2. Ontology Bloat & Semantic Drift
* **Failure Mode**: Repeated consolidation runs produce thousands of micro-summaries that pollute the context window with near-identical or low-utility semantic nodes.
* **Guard**: **Support Counting & Reference Garbage Collection**. Nodes require a minimum support threshold ($\ge 3$ distinct run lineages). Additionally, a deterministic compaction pass evicts unreferenced summary nodes from active context indexing if downstream runs do not reference them within 60 days (original records remain in append-only log).

### 3. Provenance Poisoning Cascade
* **Failure Mode**: An early episodic run contains corrupted data or hallucinated facts. Derived semantic summaries and skills inherit from this run, poisoning higher-level structures.
* **Guard**: **Merkle Revocation Invalidation Chain**. If an operator or automated validation retroactively flags a historical run ID $R_{\text{bad}}$ as invalid, a `REVOCATION_RECORD` is appended to the ledger. The consolidator performs a recursive dependency graph lookup: any consolidated artifact whose `provenance.parent_run_ids` contains $R_{\text{bad}}$ is instantly marked `INVALIDATED` and stripped from active retrieval.

---

## 7. Limitations: Boundary of Automated Verification

The following dimensions **CANNOT** be automatically validated by local models or deterministic gates, and strictly require external human review:

1. **Semantic Intent vs. Spec Completeness**: A synthesized skill may pass 100% of unit tests inside the sandbox while fundamentally violating subtle user intent (e.g., deleting temporary files too aggressively or choosing an suboptimal file format).
2. **Real-World / Temporal Contradictions**: When two episodic runs observe conflicting facts (e.g., API Endpoint A returned `503` at 10:00 AM, but `200` at 10:05 AM), automated graph logic cannot determine whether this represents an epistemic contradiction or a temporal state change without explicit domain modeling.
3. **Subjective Aesthetic & Textual Quality**: Summaries generated for human readability or natural language response formatting cannot be evaluated for nuance or tone by local scripts without subjective operator feedback.
