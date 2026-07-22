# AIOS Sovereign Coordination Stack — 통신/보안/기록/저장 systematization (2026-07-22)

**Origin**: founder directive "관련해서 통신/보안/기록/저장 관련 연구 및 시스템화 (fable)", following the
agent-mediated-coordination thesis ([[project_agent_mediated_coordination_thesis]]) and the OpenCrab peer
analysis. Four freshness-gated research sweeps (Fable agents, all claims live-verified 2026-07-22) →
this synthesis. **Through-line: ABSORB the wire/primitives (network effects are decided), BUILD only the
sovereignty layer (delegation, egress-gate, witnessing) — that is our moat, not a reinvented protocol.**

The four pillars converge into one stack for how sovereign per-person AIOSes coordinate on behalf of people
WITHOUT a central broker, a server DB, or a shared honeypot — the three sovereignty-killers, each flagged
independently by a different pillar.

---

## The convergent architecture (one diagram in words)

```
  Person A's AIOS  ──────────  A2A wire (JSON-RPC)  ──────────  Person B's AIOS
   [sovereign]         signed AgentCard @ /.well-known           [sovereign]
        │                                                              │
   ┌────┴─────────────── every off-box byte ────────────────┐         │
   │ EGRESS GATE (build — keystone):                        │         │
   │   path denylist(_from_desktop/dain/minyoung/.env)      │         │
   │   → GLiNER2-PII scrub → CaMeL provenance check         │         │
   │   → OpenFGA ReBAC authz → append-only egress receipt   │         │
   └────┬───────────────────────────────────────────────────┘         │
        │ scoped view only (knowledge stays home)                      │
   [ Akashic Record: tlog-tiles Merkle log, signed checkpoints, peer-witnessed ]
   [ Storage: append-only JSONL ledger = SoT; LadybugDB + sqlite-vec = projections ]
```

Peer messages are **DATA, never instructions** (GitLost kill-chain). Knowledge **stays home**; only
per-request, scoped, PII-scrubbed, ReBAC-authorized views cross the boundary, each leaving a signed receipt.

---

## Pillar 1 — COMMUNICATION (통신): absorb A2A, build delegation

- **Landscape (2026)**: MCP won the agent↔tool axis (stateless RC ships 2026-07-28); **A2A v1.0** (Linux
  Foundation, Apache-2.0, Jan 2026, 150+ orgs) won the agent↔agent axis — **IBM ACP merged INTO A2A Aug
  2025** (rival absorbed, network effect decided). AGNTCY/SLIM (infra tier, IETF draft, unproven), ANP
  `did:wba` (only *shipped* decentralized agent-identity, not ecosystem-ready). Delegation standards race
  ongoing: OAuth token-exchange RFC 8693 + `draft-oauth-ai-agents-on-behalf-of` (OBO), SPIFFE SVIDs.
- **AIOS map**: MCP organ surface = already on the winning tool-axis standard. `aios_dispatch.py` packets
  (`aios.lease.v0`, inbox/outbox) = a homegrown, single-tenant, filesystem A2A-Tasks equivalent. **Gap**:
  no network endpoint, no AgentCard/discovery, no signed capability advertisement, no agent identity, no
  user→agent delegation token.
- **Systematize**: (1) Adopt **A2A v1.0 (JSON-RPC)** as the inter-AIOS wire; map dispatch packets → A2A
  Tasks (already Task-shaped), receipts → task artifacts. (2) Each AIOS serves an AgentCard advertising a
  *privacy-gated subset* of CapabilityOS cards. (3) **Build the delegation layer** (no standard has won —
  our draft-first/consent DNA is the differentiator): DID-keyed identity + OBO-scoped "acting-for-<person>"
  token on every outbound task; inbound tasks hit the operator-checkpoint gate before acceptance.
  (4) Discovery = peer-exchange + TOFU key-pinning, `deploy/akashic-worker/` as store-and-forward relay —
  **no registry** (a central registry reinstates the provider dependency sovereignty removes).
- **Anti-pattern**: inventing an AIOS-proprietary peer protocol; centralized broker/registry for discovery.

## Pillar 2 — SECURITY (보안): the egress-gate is the keystone

- **Landscape (2026)**: SPIFFE/SPIRE workload identity (→ AIMS 9-layer agent-identity stack, 2026-03);
  **OpenFGA** (CNCF Incubating) / SpiceDB = productionized Zanzibar ReBAC (the standardized form of
  OpenCrab's ReBAC); MCP auth = OAuth 2.1+PKCE mandatory (RFC 9728/8707); W3C DIDs+VCs for agents (MCP-I →
  DIF, 2026-03); **MLS (RFC 9420)** group E2EE; **CaMeL** (DeepMind) control/data-flow prompt-injection
  defense; OWASP Agentic Top-10 (2026, injection still #1). **Fresh threat evidence**: Grok Build CLI
  bulk-uploaded whole repos (2026-07-12); **GitLost** (2026-07-06) prompt-injected agentic workflows to
  exfiltrate private repos; MCP H1-2026 ~200k exposed instances, tool-poisoning top vuln; TEE.Fail
  (<$1k) breaks TDX/SEV/SGX attestation.
- **AIOS map**: our privacy boundary is today a **prompt-level convention — exactly the layer Grok
  Build/GitLost prove worthless** (transport can bulk-exfiltrate regardless of instructions). DNA
  invariants map (recommendation-only ≈ least-privilege; provenance-chain ≈ CaMeL labels). **Gap**: no
  crypto identity, no cross-person authz model, no *enforcement point* proving non-leakage, no encrypted
  peer channel.
- **Systematize**: (1) **Identity (absorb)**: per-AIOS on-device keypair — SPIFFE-style SVID + a DID with
  a VC binding agent→person; sign the AgentCard (unsigned cards are the known A2A hole). (2) **AuthZ
  (absorb)**: embed **OpenFGA** as the sharing policy engine (`peerB_agent → viewer → node_X`); every
  egress requires a passing check → recommendation-only becomes *machine-enforced*. (3) **EGRESS GATE
  (build — THE keystone)**: one choke-point for all off-box bytes — path denylist → **GLiNER2-PII scrub**
  (300M open model) → CaMeL provenance check (private-tainted data cannot pass without explicit grant) →
  append-only egress receipt. Converts "provable non-leakage" from promise to log. (4) **Grants as
  capabilities**: short-lived, audience-bound (RFC 8707), attenuable Biscuit-style tokens; revocation =
  tuple delete + TTL. (5) **Transport**: MLS (mls-rs) for peer channels.
- **Anti-pattern**: treating inbound peer messages as instructions; pooling members' knowledge in a shared
  central store (breach-once-lose-everything honeypot); long-lived broad tokens.

## Pillar 3 — RECORDING (기록): absorb transparency-log + witnessing

- **Landscape (2026)**: **C2SP tlog-tiles** (2026 default for tamper-evident append-only logs; Merkle
  tiles + independent witnesses defeat split-view); **Sigstore Rekor v2** (GA 2025-10, production proof);
  **in-toto/DSSE + SLSA v1.2** (the industry "receipt" shape); C2PA 2.1 = ISO/IEC 22144 (media provenance,
  pattern only); Automerge 3.0 CRDT (convergence ≠ tamper-evidence); **AT Protocol** personal repos (best
  deployed sovereign-per-person verifiable record: content-addressed MST + signed commits + DID); IETF
  COSE Merkle-proofs / SCITT receipts; PROV-AGENT extends W3C PROV for agents.
- **AIOS map**: Akashic ledger ≈ transparency log; run-receipts/ASC closeouts ≈ in-toto attestations;
  `evidence_refs` ≈ attestation subjects; git ≈ content-addressed Merkle DAG. **Gap**: append-only *by
  convention* only (plain markdown, no signatures; evidence_refs are paths not digests). **Person B cannot
  verify person A's record** — A could rewrite history, and even a signed solo log can equivocate.
- **Systematize**: (1) content-address `evidence_refs` as `sha256:` digests. (2) receipts become
  in-toto/DSSE signed statements anchored to a per-person DID. (3) **Merkle-chain the Akashic log per
  tlog-tiles** (Tessera or a small pure-Python writer); every append emits a signed checkpoint — files stay
  plain/append-only/local-first. (4) **Peer witnessing = the cross-party trust mechanism**: peer AIOSes
  exchange checkpoints, verify consistency proofs, co-sign — detects tampering AND equivocation with zero
  central infra; optionally mirror to public Rekor for outside anchoring.
- **Anti-pattern**: bolting on a blockchain/vendor ledger (AWS killed QLDB 2025-07); "signed but
  unwitnessed" logs (can still fork their story per audience).

## Pillar 4 — STORAGE (저장): ledger is SoT, everything else is a projection

- **Landscape (2026)**: **Kuzu archived Oct 2025** (Apple acquired) → **LadybugDB** momentum fork
  ("DuckDB for graphs", embedded, Cypher→GQL, Parquet-native, MIT); **sqlite-vec** (single-file, zero-dep,
  pre-v1); **LanceDB/Lance** (embedded vector on columnar lakehouse); DuckDB+DuckPGQ (ISO SQL/PGQ);
  Chroma (embedded, Apache-2.0); FalkorDB fast but SSPLv1 (license drag). Interchange: **GQL =
  ISO/IEC 39075:2024**, openCypher converging to it; **RDF 1.2** Candidate Rec (triple-terms fit
  contradiction/provenance edges). New agent-memory packs: MIF (JSON-LD+MD+PROV), Portable Agent Memory
  (Merkle-DAG, arXiv:2605.11032). **LazyGraphRAG** killed heavy up-front indexing (~700x cheaper) → 2026
  norm = vector-first, graph-enrich, per-query routing.
- **AIOS map**: `_merged.json` already IS a property graph (`{id,label,source[],domain[]}`) mapping
  losslessly to Pack v1 `nodes.jsonl`/`edges.jsonl`, to openCypher/GQL, and to JSON-LD via one `@context`.
  Semantic-FS triad: graph=have, pointer=have, **vector=MISSING** (no embedding lane keyed to node IDs).
  **Gap**: no queryable substrate (grep-only), no vector lane, no signed single artifact, no federation
  semantics beyond `domain[]` union.
- **Systematize**: (1) **SoT stays the append-only JSONL ledger** (git-friendly, DNA-invariant); all DBs
  are disposable compiled projections (consistent with the Lakebase decision). (2) **Graph head:
  LadybugDB** (embedded, MIT) compiled from the ledger; hedge = DuckDB+DuckPGQ over the same Parquet.
  (3) **Vector lane: sqlite-vec** (one file, zero-dep) keyed by node id; upgrade to LanceDB at ~10⁶ chunks.
  (4) **Interchange: adopt OpenCrab Pack v1 container** (1:1 with our ledger, buys peer interop) EXTENDED
  with: JSON-LD `@context` → RDF 1.2 export (W3C-stable federation lingua franca); per-node content hash +
  Merkle root → verifiable artifact (ties to Pillar 3); a declared merge rule. **Write our own spec
  down** (OpenCrab's pack license unverified). (5) **Federation = pack exchange**: a peer pack imports as a
  **draft subgraph** (draft-first invariant), merged by node-hash identity, conflicts become contradiction
  edges — never overwrites.
- **Anti-pattern**: canonicalizing into any server DB (Neo4j/FalkorDB/Qdrant server) — SSPL/infra
  dependency kills one-artifact sovereignty; even embedded engines die (Kuzu), so the *ledger* is the
  artifact and every DB a disposable projection. Also fatal: a bespoke binary format with no JSON escape.

---

## Build order (keystone-first, cheapest-decisive-first)

1. **Pack v1 exporter** (storage; CPU-only, in-repo) — `_merged.json` → Pack v1 ZIP (+ content hashes +
   JSON-LD context). Cheapest, dogfoods interop, ties storage↔recording. *In progress this session.*
2. **Egress gate** (security keystone) — the choke-point that makes the privacy boundary *enforced* not
   *asserted*. Highest-value: today the boundary is the exact prompt-level convention Grok Build/GitLost
   proved worthless. Denylist + GLiNER2 scrub + provenance + receipt.
3. **Merkle-chain the Akashic log** (recording) — tlog-tiles writer + signed checkpoints. Makes the record
   cross-party verifiable; small.
4. **A2A endpoint + signed AgentCard + DID identity** (communication) — the first inter-AIOS wire; gated by
   the egress gate + OpenFGA. This is the "two people's agents coordinate" MVP.
5. **OpenFGA authz + peer witnessing + MLS transport** — hardening for real multi-party use.

## Honest scope (no-launder)
This is a *design synthesis grounded in a live 2026 landscape scan*, not shipped code. Every recommendation
is "absorb X / build thin Y" — deliberately minimal, because the moat is the sovereignty layer (egress
gate, delegation, witnessing, draft-first federation), not the absorbed primitives. The single most
load-bearing brick is #2 (egress gate): without an *enforcement point*, "privacy-sovereign" is a slogan the
2026 threat evidence directly refutes. Related: [[reference_opencrab_peer_ontology_platform]],
[[project_agent_mediated_coordination_thesis]], [[project_aios_saas_lakebase_pivot]].
