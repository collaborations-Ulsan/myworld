# 릴리스 절차 — 설치되는 것만 출하한다 (2026-08-03)

**존재 이유:** 2026-08-03에 실측해보니 출하 대상 휠이 (a) 우리가 반증한 주장을 광고하고 있었고
(b) 자기가 import하는 모듈 14개가 빠져 **`pip install` 후 핵심 경로가 ImportError로 죽었다** —
`aios_egress_gate`·`aios_authority`가 빠진 채 소버린티를 광고하고 있었다.
**"패키징돼 있다"와 "설치하면 동작한다"는 다른 명제다.** 아래는 그 간극을 매번 닫는 절차다.

## 릴리스 전 게이트 (전부 통과해야 태그)

### 1. 클레임 위생
```sh
python3 -m pytest -q tests/test_packaging_completeness.py
```
- 금지 문구가 `pyproject.toml` description에 없는지 (반증된 주장 판매 금지)
- README에 반증된 주장이 남아있지 않은지 **수동 확인**:
```sh
grep -n -iE 'carry forward what worked|makes the .* smarter|learn from every run|smarter for everyone|network effect becomes' README.md
```
  → 히트가 **철회 고지 문맥뿐**이어야 한다. 새 마케팅 문구가 이 목록에 걸리면 그 문구가 틀린 것이다.

### 2. 패키지 완전성 (정적)
같은 테스트가 `py-modules`에서 출발해 import 그래프를 걸어, 출하 코드가 쓰는데 등재되지 않은
모듈이 있으면 실패시킨다. **새 모듈을 추가했다면 `py-modules`에도 추가해야 통과한다.**

### 3. 전체 테스트
```sh
python3 -m pytest -q tests/
```

### 4. 클린 venv 설치 스모크 (실제 사용자 경로)
레포 밖에서, 레포에 의존하지 않고 동작하는지 확인한다:
```sh
rm -rf /tmp/aios_relsmoke && python3 -m venv /tmp/aios_relsmoke
/tmp/aios_relsmoke/bin/pip install --quiet /path/to/myworld
/tmp/aios_relsmoke/bin/python - <<'PY'
import importlib
mods = ["aios_launcher","aios_mcp_server","aios_sandbox","aios_egress_gate",
        "aios_authority","aios_turn_loop","aios_freshness",
        "aios_society","aios_takeover_verify","aios_society_watchdog",
        "aios_skills","aios_experience"]
bad = []
for m in mods:
    try: importlib.import_module(m)
    except Exception as e: bad.append((m, repr(e)[:80]))
assert not bad, bad
print("import OK:", len(mods))
PY
```
그리고 **레포가 없는 디렉터리에서** 아크 CLI 왕복:
```sh
cd /tmp && /tmp/aios_relsmoke/bin/python -c "
import aios_society as s, sys, tempfile, json
d = tempfile.mkdtemp()
assert s.main(['--arcs-dir', d, 'open', '--goal', 'release smoke', '--agent', 'rel@smoke']) == 0
"
```
엔트리포인트 존재 확인: `ls /tmp/aios_relsmoke/bin | grep aios` → `aios`, `aios-mcp`.

### 5. 버전 + 태그
- `pyproject.toml`의 `version`을 올린다(SemVer).
- 커밋 후 `git tag -a vX.Y.Z -m "..."`, 태그도 함께 푸시.

## 이 절차가 덮지 못하는 것 (정직 표기)

- **PyPI 게시는 별도 승인 사항이다.** 이름 선점과 공개 게시는 되돌리기 어렵고, 지금은 founder
  승인 대기 상태다(`docs/AIOS_DEPLOYMENT_PLAN_2026-08-03.md` ④).
- **다인/호스팅 배포는 차단되어 있다** — 아크 원장이 에이전트 텍스트를 그대로 담고 append-only가
  삭제·철회 요구와 충돌한다(같은 문서 B1). 단일 사용자 로컬 설치에는 해당 없음.
- 이 절차는 **설치 가능성**을 검증하지 사회 층의 **가치 주장**을 검증하지 않는다 — 그것은 G5다.

## 공개 푸시 전 프라이버시 스캔 (공개 레포이므로 매번)

```sh
git diff --name-only origin/main..HEAD | grep -iE '_from_desktop|/dain|/minyoung|\.env|private_key|id_rsa'
git diff origin/main..HEAD | grep -E '^\+' | grep -oiE '(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{25,}|nvapi-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)' | sort -u
```
히트가 나오면 **파일 위치를 확인해 테스트 픽스처인지 실제 비밀인지 판정한 뒤에만** 진행한다
(2026-08-03 실행 시 6건 전부 `tests/test_aios_egress_gate.py`의 픽스처였다 — 알파벳 나열·잘린 키).
