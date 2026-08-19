#!/usr/bin/env python3
"""aios.ambient_route.v1 — council, the OSes, chatbots and other sessions, unasked.

Founder: make these usable without naming them.

Two rules decide the shape.

  THE TRIGGER MUST BE DETERMINISTIC. "The agent remembers to consult X" is not a
  mechanism; it is a hope. So the routing here is regex and sqlite — comparisons, the same
  reason the factory's scheduler asks no model.

  CHEAP INLINE, EXPENSIVE ASYNC. Firing a council panel on every prompt would add 90
  seconds to every turn and burn the rate limits that make council worth having. So local
  durable state (mesh cards, the knowledge graph, memoryOS) is read inline in milliseconds,
  and anything that costs a network round trip is ENQUEUED to the factory, where it runs
  between turns and its answer is waiting next time. That is what the factory was for.

What fires, and on what:

  any prompt        -> who in the mesh holds this domain; what we have already written
                       (graph). Both are local reads.
  freshness trigger -> enqueue grounding. "best/latest/추천/version/benchmark/does X exist"
                       is exactly the class where our weights are stale by construction.
  decision marker   -> enqueue a heterogeneous adversarial pass. A keystone decision gets
                       an adversary before a builder; that rule was learned by having a
                       confident grounded architecture call turn out REFUTED at its core.
  subscription-only -> name the chatbot substrate, because no API exists for it and the
                       browser path is the only one.

Never blocks, never raises, never slower than a disk read.
"""
from __future__ import annotations
import json, os, re, sqlite3, sys, time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR",
                           Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(ROOT / "scripts"))
GRAPH = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"

# Korean must NOT use \b. Hangul syllables are word characters, so \b결정\b never matches
# inside "결정하자" — the decision trigger silently failed to fire on a prompt that said
# both 결정 and 아키텍처, and a trigger that quietly does not fire reads exactly like a
# prompt that did not warrant it. English keeps \b to avoid matching inside longer words.
_EN_FRESH = r"best|latest|newest|current|state of the art|sota|benchmark|pricing|version|release"
_KO_FRESH = r"어떤 모델|추천|최신|현재|지금|요즘|제일 좋은|최고"
FRESHNESS = re.compile(rf"(?i)\b({_EN_FRESH})\b|({_KO_FRESH})|does .{{0,20}}exist|\b20\d\d\b")

_EN_DEC = r"decide|choose|should we|architecture|keystone|pivot"
_KO_DEC = r"재설계|아키텍처|결정|선택|골라|방향|전략|설계|정하자|바꾸자"
DECISION = re.compile(rf"(?i)\b({_EN_DEC})\b|({_KO_DEC})")

SUBSCRIPTION_ONLY = re.compile(r"(?i)\b(veo|deep research|notebooklm|sora)\b|영상 생성")
TERM = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{3,}|[가-힣]{2,}")
SKIP = re.compile(r"^\s*(go|ok|네|응|계속|진행|yes|y|n)\s*$", re.I)


def _mesh_holders(terms: set[str]) -> list[tuple[str, str]]:
    try:
        import aios_mesh as mesh
        out = []
        for c in mesh.directory():
            hay = " ".join(c.domains + c.skills + [c.role]).lower()
            hit = [t for t in terms if t in hay]
            if hit:
                out.append((c.name, ",".join(sorted(hit)[:3])))
        return out[:4]
    except Exception:
        return []


def _graph_prior(terms: set[str]) -> list[tuple[str, int]]:
    """What have we already written about this? Local read, indexed, milliseconds."""
    if not GRAPH.exists():
        return []
    try:
        con = sqlite3.connect(f"file:{GRAPH}?mode=ro", uri=True, timeout=2.0)
        rows = []
        for t in sorted(terms)[:4]:
            if len(t) < 5:
                continue
            for (nid,) in con.execute(
                    "select id from nodes where layer='docs' and id like ? limit 3",
                    (f"%{t}%",)):
                n = con.execute("select count(*) from edges where dst=?", (nid,)).fetchone()[0]
                rows.append((nid.split("/")[-1], n))
        con.close()
        return sorted(set(rows), key=lambda r: -r[1])[:4]
    except Exception:
        return []


def _enqueue(goal: str, capability: str) -> str | None:
    try:
        import aios_factory as fac
        return fac.enqueue(goal[:200], capability, depth=0)
    except Exception:
        return None


def route(prompt: str) -> str:
    if SKIP.match(prompt or "") or len(prompt or "") < 12:
        return ""
    terms = {t.lower() for t in TERM.findall(prompt)}
    lines: list[str] = []

    holders = _mesh_holders(terms)
    if holders:
        lines.append("**세션 보유자** (SendMessage로 직접 물을 수 있음):")
        lines += [f"- `{n}` — {why}" for n, why in holders]

    prior = _graph_prior(terms)
    if prior:
        lines.append("**이미 쓴 것** (인용수 순 — 재발명 전에 확인):")
        lines += [f"- `{d}` (피인용 {n})" for d, n in prior]

    queued = []
    if FRESHNESS.search(prompt):
        tid = _enqueue(f"grounding: {prompt[:120]}", "external")
        queued.append(f"외부 그라운딩 (freshness gate) → factory `{tid}`" if tid
                      else "외부 그라운딩 필요 (enqueue 실패)")
    if DECISION.search(prompt):
        tid = _enqueue(f"adversarial review: {prompt[:120]}", "adversarial")
        queued.append(f"이종 적대 검토 → factory `{tid}`" if tid
                      else "적대 검토 필요 (enqueue 실패)")
    if SUBSCRIPTION_ONLY.search(prompt):
        queued.append("구독 UI 전용 능력 — `hub ask <substrate>-web`이 유일한 경로 "
                      "(API 재생 없음)")
    if queued:
        lines.append("**비동기로 걸어둔 것** (이 턴을 막지 않음):")
        lines += [f"- {q}" for q in queued]

    return "\n".join(lines)


def main() -> int:
    try:
        ev = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    try:
        ctx = route(ev.get("prompt") or "")
    except Exception:
        return 0
    if ctx:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "AIOS ambient routing:\n" + ctx}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
