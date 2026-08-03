# Orca — 우리 설계의 일부가 이미 제품으로 나온 사례 (2026-08-03)

founder 관찰: *"Orca 같은 앱이 실제 우리 아이디어가 조금 반영되어 앱으로 나온 사례."*
**기억이 아니라 이 기계에서 확인한 증거로 적는다.**

## 0. 무엇을 확인했고 무엇을 못 했는가 (정직 경계)

확인함: `~/.claude/skills/orca-cli/SKILL.md`(디스커버리 스텁), `~/.config/orca/` 상태 파일들의
**스키마**, 런타임 생존 여부. **확인 못 함:** 전체 커맨드 표면 — 스텁이 의도적으로 명령 목록을
싣지 않고 바이너리가 버전 일치 가이드를 제공하는데(`ORCA skills get orca-cli`), 이 환경에서
`orca-ide`가 AppImage 래퍼 오류(`bad option: --no-sandbox`)로 실행되지 않았다.
⟹ **"Orca에 X가 없다"고 단정하지 않는다.** 아래 "없어 보이는 것"은 전부 *스텁·스키마 범위에서
관측되지 않음*이라는 뜻이다.

## 1. 관측된 사실

- 런타임: `orca-runtime.json` = `{runtimeId, pid, transports, authToken, startedAt}`.
  **살아 있음**(pid 생존), 전송로 2개: `unix:///home/user/.config/orca/o-…sock` +
  `websocket ws://0.0.0.0:6768`.
- 기기: `orca-devices.json` = `[{deviceId, name, token, scope, pairedAt, lastSeenAt,
  mobilePairingConnectionMode, relayBinding:{relayHostId, relayDeviceId, ownerIdentityKey}}]`.
- 신원: `orca-e2ee-keypair.json` (열지 않음 — 프라이버시 경계).
- 프로필: `orca-profile-index.json` = `{schemaVersion, activeProfileId, profiles:[{id,name,kind,
  cloud,…}]}`.
- 성과 계측: `orca-stats.json` = `{aggregates:{totalAgentsSpawned, totalPRsCreated,
  totalAgentTimeMs, countedPRs}}`.
- 스킬 스텁이 광고하는 능력: **워크트리(자식 워크트리 포함) · 폴더 컨텍스트 · 터미널
  (read/wait/send) · 리포 · 오토메이션 · 워크트리 코멘트 · 내장 브라우저 ·
  "spawn codex/claude in a worktree" · "full handoff / handover / give this to another agent"**.

## 2. 우리 설계와 1:1 대응 — 겹치는 것

| 우리 개념 | Orca에서 관측된 대응물 |
|---|---|
| 아크 격리 (worktree) | Orca-managed worktrees / child worktree |
| G2 인수인계 | **"full handoff" / "handover" / "give this to another agent"가 1급 동사** |
| G3 이종 기질 | "spawn **codex/claude** in a worktree" |
| N2 다기기 (노드=기기, 사람=키) | `devices[].deviceId/token/scope` + `relayBinding.ownerIdentityKey` — **정확히 그 구조** |
| N3 연합·동의 | E2EE 키페어 + relay 바인딩 + 기기 페어링 |
| 사회의 성과 측정 | `totalAgentsSpawned / totalPRsCreated / totalAgentTimeMs` |
| 에이전트 간 통신 | 터미널 read/wait/send (= 우리 council mesh와 같은 층위) |

**결론: 우리 G1~G3 + N2의 상당 부분은 이미 출하된 제품에 존재한다.** 이번 세션에서 "peer가 이미
있다"가 세 번째다(OpenCrab=온톨로지, PCAA/Proof-or-Stop=검증, Orca=사회/인수인계).
founder 프레임대로 **peer 존재 = 수요 검증**이지 위협이 아니다. 다만 **"우리가 처음"이라는 문장은
이 영역에서 영구히 쓰지 않는다.**

## 3. 관측되지 않은 것 = 우리가 실제로 다르게 한 것 (조건부 주장)

스텁·스키마 범위에서 보이지 않았고, 우리는 구현한 것:
1. **인수인계 충실도의 외부 검증.** Orca의 handoff는 *이전(transfer)* 동사다. 우리 G2는
   "이전됐다"가 아니라 **"인수자의 행동이 아크 목표·제약과 정합한가"를 분리된 검증기가 판정**한다.
2. **append-only 아크 원장 + Merkle 무결성 + 신선도 게이트(tip_seq/tip_hash).**
3. **파생 생존성 기반 고아 회수**(죽은 pid ⇒ 즉시 회수, MTTR 실측 19.95s).
4. **supersede(보상 액션)** — 잘못된 수를 상속하지 않게 하는 연산자.
5. **외부 오라클 게이트 + 커널 강제 샌드박스**(무네트워크 기본, 프라이버시 디렉터리 불가시).

⟹ **차별점은 "사회를 만들었다"가 아니라 "사회의 각 이전에 증명을 붙였다"이다.** 이것이 우리
재스코프 정체성(강제-소버린티·외부검증 실행 기질)과 정확히 같은 문장이라는 점이 중요하다 —
우연이 아니라 수렴이다.

## 4. 흡수 후보 (Orca에서 배울 것)

1. **버전 일치 문서를 바이너리가 제공한다.** 스킬 스텁이 명령 목록을 *의도적으로 싣지 않고*
   `ORCA skills get orca-cli`로 넘긴다 — "캐시된 문서는 반드시 drift한다"는 우리 freshness 규율의
   **툴 층 구현**. **우리 harness/skill 문서도 같은 규율로 바꿀 가치가 있다.**
2. **이름 충돌 방어를 문서가 명시한다.** 리눅스에서 bare `orca`는 GNOME 스크린리더를 실행해
   사용자 기계에서 음성이 나온다고 경고한다. 우리 AIOS도 arXiv:2403.16971 "AIOS"와 이름이
   충돌하며, 같은 수준의 방어 문구가 필요하다.
3. **성과를 제품이 스스로 계측한다** (`totalPRsCreated`). 우리 사회도 "아크 완주" 같은
   **결과 지표를 상시 집계**해야 한다 — 지금은 실험할 때만 센다.
4. **기기 페어링 + relay 바인딩 스키마**가 우리 N2 설계의 검증된 형태를 제공한다. 재발명 금지.

## 5. 경고로 읽어야 할 것

`ws://0.0.0.0:6768` — 웹소켓 전송로가 **모든 인터페이스에 바인딩**되어 있고 인증은
`authToken`이다. 이는 우리가 2026-07-25 적대 리뷰에서 `aiosd`에 대해 내린 판정
(*"상주 전권 데몬은 로컬 제어 소켓 공격면을 만든다 — SURVIVES-WITH-CONDITIONS"*)이 가리킨
바로 그 형태다. **제품이 그 형태를 택했다는 사실은 그 형태가 안전하다는 증거가 아니다.**
우리가 그 층을 만든다면 조건(소켓 활성화·유휴 종료·최소권한·루프백 한정)은 그대로 유효하다.
(founder 기계의 설정이므로 관찰만 기록하고 변경하지 않는다.)

---
*증거: `~/.claude/skills/orca-cli/SKILL.md`, `~/.config/orca/{orca-runtime,orca-devices,
orca-profile-index,orca-stats}.json` 스키마, 런타임 pid 생존 확인 (2026-08-03).
관련: `docs/AIOS_SOCIETY_GOALTREE_2026-08-02.md`, `docs/AIOS_NETWORK_THESIS_2026-08-02.md`,
`docs/AIOS_AGENT_LEDGER.md`(2026-07-25 aiosd 적대 리뷰).*
