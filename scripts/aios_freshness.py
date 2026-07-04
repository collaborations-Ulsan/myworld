#!/usr/bin/env python3
"""aios_freshness — ground time-sensitive questions via a wrapped web-capable CLI.

Founder architecture: AIOS is a WRAPPER over CLI capabilities. DuckDuckGo scraping
is blocked in this environment, but the wrapped CLIs (Claude / Codex) have working
NATIVE web search. So for recommendation / latest / model-choice questions, DELEGATE
to a CLI's own search instead of answering from a frozen model's stale cache — then
record the grounded answer to a ledger so head/session agents reuse it rather than
re-deriving from stale weights.

(Founder: "answering without checking is not intelligence.")

CLI:  aios ground "<query>"     # force a grounded answer via CLI native search
Env:  AIOS_FRESHNESS_TTL (seconds, default 7d) · AIOS_GROUND_PROVIDER (codex|claude)
"""
from __future__ import annotations
import os, sys, json, subprocess, time, re
from pathlib import Path

def _home() -> Path: return Path(os.environ.get("AIOS_HOME") or (Path.home()/".aios")).expanduser()
LEDGER = _home()/"freshness_ledger.jsonl"
TTL = int(os.environ.get("AIOS_FRESHNESS_TTL", str(7*86400)))
MYWORLD = "/home/user/workspaces/jaewon/myworld"   # a codex-trusted dir

_FRESH_RE = re.compile(
    r"추천|제일\s*좋|가장\s*좋|best\b|latest|newest|현재|지금|요즘|최신|state of the art|\bsota\b|"
    r"recommend|which .* (should|to) (use|pick)|benchmark|가격|\bprice\b|버전|\bversion\b|202[4-9]|"
    r"임베딩|embedding|\bmodel\b|모델|라이브러리|library|framework|프레임워크", re.I)

def is_fresh(goal: str) -> bool:
    return bool(_FRESH_RE.search(goal or ""))

# Stricter gate for AUTO-routing (bare `aios "..."`): require a recommendation /
# superlative / latest signal, so conceptual questions that merely mention "model"
# or "library" aren't sent through a ~28s web search.
_FRESH_ROUTE_RE = re.compile(
    r"추천|제일\s*좋|가장\s*좋|\bbest\b|latest|newest|최신|state of the art|\bsota\b|recommend|"
    r"현재\s*(가장|제일|최고|best)|지금\s*(가장|제일|최고|best)|which\s+.*\s+(should|to)\s+(use|pick)|"
    r"뭐\s*(써|쓰|좋|추천)|뭐가\s*(좋|나)|골라", re.I)

def is_fresh_route(goal: str) -> bool:
    return bool(_FRESH_ROUTE_RE.search(goal or ""))

def _norm(goal: str) -> str:
    return re.sub(r"\s+", " ", (goal or "").strip().lower())[:200]

def _cache_lookup(goal: str):
    if not LEDGER.exists(): return None
    key, now, hit = _norm(goal), time.time(), None
    for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
        try: e = json.loads(line)
        except json.JSONDecodeError: continue
        if e.get("key") == key and now - e.get("ts", 0) < TTL:
            hit = e   # most recent within TTL wins
    return hit

_SEARCH_PROMPT = (
    "Use your web search tool to find the MOST CURRENT information, then answer concisely "
    "(2-4 sentences). Name the specific current best option and cite the source (name + URL "
    "+ date). If you cannot actually search the web, say so explicitly — do NOT answer from "
    "training memory.\n\nQuestion: {q}")

def _cli_ground(goal: str, timeout: int = 90):
    """Invoke a wrapped web-capable CLI's NATIVE search. Returns (answer, provider).

    Codex runs at LOW reasoning effort — the config default (xhigh) makes a simple
    search take 3.5+ min; low effort grounds correctly in ~20s (verified).
    """
    prompt = _SEARCH_PROMPT.format(q=goal)
    pref = os.environ.get("AIOS_GROUND_PROVIDER", "")
    chain = [
        ("codex",  ["codex", "exec", "--skip-git-repo-check",
                    "-c", "model_reasoning_effort=low", prompt]),
        ("claude", ["claude", "--print", prompt]),
    ]
    if pref == "claude":
        chain.reverse()
    for prov, argv in chain:
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=MYWORLD)
            out = (r.stdout or "").strip()
            # strip obvious CLI banners/noise; keep the substantive answer
            out = "\n".join(l for l in out.splitlines()
                            if l.strip() and not l.startswith(("hook:", "warning:", "---", "workdir",
                            "approval", "sandbox", "reasoning", "session id", "OpenAI Codex", "tokens used")))
            if out and len(out) > 25:
                return out, prov
        except Exception:
            continue
    return None, "no CLI grounding available (claude/codex unreachable)"

def ground(goal: str, record: bool = True) -> dict:
    cached = _cache_lookup(goal)
    if cached:
        return {"answer": cached["answer"], "provider": cached.get("provider"),
                "source": "ledger-cache", "ts": cached["ts"]}
    ans, prov = _cli_ground(goal)
    if ans is None:
        return {"answer": None, "error": prov}
    if record:
        entry = {"key": _norm(goal), "goal": goal[:300], "answer": ans[:2500],
                 "provider": prov, "ts": time.time()}
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"answer": ans, "provider": prov, "source": prov, "recorded": record}

def main(argv=None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    if not a:
        print("usage: aios ground \"<query>\""); return 1
    goal = " ".join(a)
    if not is_fresh(goal):
        # not time-sensitive → let the normal path answer
        sys.stderr.write("(not freshness-sensitive — answer normally)\n"); return 0
    sys.stderr.write("✦ grounding via wrapped CLI native web search…\n")
    r = ground(goal)
    if r.get("answer"):
        print(r["answer"])
        sys.stderr.write(f"\n[grounded via {r.get('provider')} · {r.get('source')} · recorded to ledger]\n")
        return 0
    print("내 지식이 오래됐을 수 있음 — 현재 소스로 직접 확인 필요. "
          f"(grounding failed: {r.get('error')})")
    return 1

if __name__ == "__main__":
    sys.exit(main())
