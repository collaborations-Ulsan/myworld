# INTEGRATION REQUEST — Work Galaxy ↔ AIOS Akashic (galaxy = AIOS의 통합 비주얼)

> founder 지시(2026-07-22): work_galaxy를 AIOS akashic의 **비주얼로 통합**. 이 요청은 dacon/ops 컨텍스트에서
> 남기고, **실제 통합은 AIOS(myworld) 컨텍스트/드라이버가 수행**(AIOS 편집 프로토콜 존중).

## 무엇을 통합하나
- **이미 있는 것**:
  - `apps/akashic-ui/galaxy.html` — "AIOS Memory Galaxy": AkashicRecord **behavioral-similarity** 3D force graph,
    라이브 Worker `aios-akashic.*.workers.dev/graph` (+ `/predict`). `scripts/aios_akashic.py`, `memoryOS/memory/
    akashic_work_index.jsonl`(work-lineage 원장, schema `aios.akashic_work_index.v1`).
  - `apps/serving/neural-map.html`, `apps/showcase/index.html`.
- **새로 만든 것 (dacon/ops 쪽)**:
  - `dacon/../ops/galaxy/` — **Work Universe**: 재원의 "모든 작업"(대회·논문·quantum·deepfake·AIOS organ·products)을
    typed 노드 + 도메인 성운(named galaxies)으로. 파이프라인 `build_work_graph.py`(소스: inventory_diverse.json +
    portfolio_registry.tsv), 뷰어 `work_galaxy.html`(three@0.149 UMD + 3d-force-graph, glow별·bloom각·hover-이웃·
    fly-to·baked 좌표·Pretendard), standalone `work_galaxy_standalone.html`. SwiftShader로 렌더검증됨.

## 요청 (권고 방식 = 진짜 통합)
1. **all-work를 akashic WORK 아이템으로 등록** — build_work_graph의 노드(대회/논문/시스템/…)를
   `akashic_work_index.jsonl`(WORK schema)에 typed로 ingest → akashic이 behavioral records + all-work를 함께 보유.
2. **galaxy를 단일 소스로** — work_galaxy 뷰어(더 폴리시됨)를 akashic Worker `/graph`가 서빙하는 통합 데이터에 연결
   (behavioral-similarity 엣지 + all-work 도메인 성운 둘 다). 즉 **galaxy.html/work_galaxy.html 병합 → AIOS의 얼굴**.
3. **배포** — Cloudflare Pages로 공개(founder의 고가시성 "튀어나온 돌" 아티팩트). 게이트=founder.

## 재사용 포인터
- 뷰어 크래프트(성운명명·glow·bloom·인터랙션)는 `ops/galaxy/work_galaxy.html`에서 그대로 가져올 수 있음.
- 레퍼런스 스펙: `dacon/competitions/control_tower/research/GALAXY_REFERENCES.md`.
- ★ three UMD 글로벌은 **≤0.149**만 존재(0.161+는 ESM전용 → 기존 galaxy.html의 커스텀 THREE 코드도 잠재 버그, 0.149로 교체 필요).
- 환경 WebGL: 이 sandbox는 Xvfb+GPU패스스루 없어 WebGL 불가 → 렌더검증은 **SwiftShader**(`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`).

_남긴이: dacon/ops 세션 · 2026-07-22 · 실제 통합은 myworld 드라이버가._
