# Frontier Knowledge Ledger — 세팅 (schema + taxonomy) 2026-07-17

**Authority**: founder 2026-07-17 — "OakLab AGI 온톨로지처럼 지식 원장이 구성되는지 확인하고,
의료·physical ai·AGI 등 최선봉 카테고리를 전부 세팅하고, 그 아래 방법론들(유전 알고리즘·CoT·
diffusion policy·…) 전부 조사시켜."

이 문서는 **OntologyOS의 실체** — 프론티어 전역을 도메인 × 방법론 × 논문/인물/주장으로 구조화한
성장하는 knowledge ledger. **레이더 organ(연속 수집기)이 이 원장을 계속 채운다.** 카테고리(타입)는
**외부 실제 논문·인물에서 정착**되어야 한다 (self-generated 금지 = ontology-hacking 방지, AGI 개념 §5b).

## 1. 통일 스키마 (OakLab 온톨로지와 호환 — 하나의 원장)

**Entities** (stable id + attrs, 모든 노드는 source 필수):
- `Domain` — 최선봉 카테고리 (§2). attrs: name, scope.
- `Methodology` — 방법론 (§3). attrs: name, definition, kind.
- `Paper` — arxiv_id/url, date, title, venue.
- `Person` — name, affiliation(s).
- `Lab` / `Org` — name, kind.
- `Concept` — name, definition.
- `Claim` — statement + asserting paper (provenance 필수).
- `Method` — 구체 기법/시스템 (Methodology의 인스턴스; 예: GEPA, diffusion policy).
- `Benchmark` / `Dataset` — name, what it measures.
- `Model` — name, weights(open/closed), params, date.

**Relations** (모든 엣지 source 추적):
`affiliated_with`(Person→Lab) · `authored`(Person→Paper) · `cites`/`extends`/`contradicts`(Paper↔Paper,
Claim↔Claim) · `proposes`(Paper→Concept/Method/Model) · `in_domain`(Paper/Method→Domain) ·
`domain_has_methodology`(Domain→Methodology) · `method_is_a`(Method→Methodology) ·
`evaluated_on`(Method/Model→Benchmark) · `asserts`(Paper→Claim) · `concept_relates_to`(Concept→Concept).

**저장**: `docs/ontology/ledger/<domain>.json` (도메인별) + merge된 `docs/ontology/ledger/_merged.json`.
draft-first (append; 승인 전 accepted 아님, DNA #2). 매 노드/엣지 provenance.

## 2. 최선봉 도메인 (전부 세팅 — 골격; 우선 3개 deep-populate, 나머지 radar-fed 큐)

| id | Domain | 상태 |
|---|---|---|
| D1 | **AGI / foundation capability** (continual learning, agency, world-model, reliability) | wave-1 (deep) |
| D2 | **Medical / Biomedical AI** (진단, 신약·단백질, 임상, 유전체, 영상) | wave-1 (deep) |
| D3 | **Physical / Embodied AI** (로보틱스, VLA, diffusion policy, world model, sim2real) | wave-1 (deep) |
| D4 | Agentic systems (agent OS, 오케스트레이션, tool-use, long-horizon) | queued |
| D5 | Reasoning (CoT, search, verification, formal/Lean) | queued |
| D6 | Learning methods (RL, continual, self-improve, evolutionary/genetic, meta, few-shot) | queued |
| D7 | Generative modeling (diffusion, flow, AR, world models) | queued |
| D8 | Memory & knowledge (KG/ontology, retrieval, memory systems, consolidation) | queued |
| D9 | Multimodal & perception (vision/audio/video, VLA) | queued |
| D10 | Safety & alignment (reward hacking, interpretability, verification, governance) | queued |
| D11 | Science automation (AI scientist, materials, self-driving labs) | queued |
| D12 | Systems & efficiency (inference, quantization, local-LLM, hardware) | queued |

## 3. 방법론 (cross-cutting; 도메인 아래 태깅)

evolutionary/genetic (GEPA·ShinkaEvolve·LEVI·AlphaEvolve·DGM-H·**RELAI**) · CoT/reasoning-scaffold ·
**diffusion policy**/flow-matching · RL (RLHF·RLVR·GRPO·self-play) · continual/self-improvement ·
memory/retrieval/consolidation · verification/formal (Lean·verifier-hierarchy) · few-shot/ICL ·
ontology/knowledge-graph · world-models (JEPA·video-pretrain) · QLoRA/fine-tune/distill ·
search (MCTS·AB-MCTS·MAP-Elites).

## 4. 구성 파이프라인 ("이런식으로 구성되는지 확인")

1. OakLab 온톨로지(진행 중) = **첫 인스턴스** — 이 스키마가 실제로 채워지는지 검증.
2. wave-1: 도메인당 1 리서치 에이전트가 최신(2026) 논문·인물·방법론·주장을 **타고 들어가** 스키마로 populate
   (도메인당 ~20-40 논문, 커버리지 정직 표기 — "전부"는 1회에 불가, 골격+우선populate+큐가 정직한 형태).
3. 레이더 organ이 신규 논문을 **연속으로** 이 원장에 흘려보냄 (radar seen-ledger → ontology append).
4. 모순(contradicts 엣지)은 보존 — 프론티어의 불일치가 지식이다 (예: "GEPA overfits" vs "GEPA improves").

## 5. 정직 스코프
- "전부 조사"는 1턴에 완결 불가. **카테고리 전부 세팅(골격)은 지금 완료**; 방법론 populate는 우선 3
  도메인 deep + 나머지 큐 + radar 연속. 커버리지는 각 도메인 파일에 명시.
- 원장은 draft-first; accepted 승격은 별도 리뷰. aggregator 출처는 hypothesis-grade 태그.
