#!/usr/bin/env python3
"""aios_user_model — learn the user's preferences & working style (personalization).

The YouTube-recsys analog, done the AIOS way (privacy-respecting, user-sovereign):
(a) implicit-feedback capture — mine STRUCTURAL style signals from CLI session logs
    (language, verbosity, autonomy/ask-vs-act, tech leanings). Raw message text is
    NEVER stored — only aggregates (DNA #7: privacy boundary inviolable).
(b) user-style profile — a local ~/.aios/user_profile.json (never egresses).
(c) draft-first proposal loop — detected preferences are PROPOSED, not auto-bound;
    the user accepts/rejects (DNA: recommendation-only + operator override), and only
    accepted preferences render into an injectable guidance block.

CLI:  aios profile propose            # (a)+(b) scan sessions → propose preferences
      aios profile show               # current profile (proposed + accepted)
      aios profile accept <key>...    # (c) bind a proposed preference (or `all`)
      aios profile reject <key>...
      aios profile render             # accepted preferences → CLAUDE.md-style block
"""
from __future__ import annotations
import os, sys, json, re, argparse, random
from pathlib import Path

# Exploration rate (recsys filter-bubble guard): with this probability the injected
# guidance nudges the agent to propose a better approach instead of just conforming to
# learned habits — so personalization doesn't ossify the user's past behavior.
EXPLORE_EPSILON = float(os.environ.get("AIOS_PROFILE_EPSILON", "0.15"))

def _aios_home() -> Path:
    return Path(os.environ.get("AIOS_HOME") or (Path.home() / ".aios")).expanduser()

PROFILE_PATH = _aios_home() / "user_profile.json"
SESSION_ROOTS = [Path.home() / ".claude" / "projects", Path.home() / ".codex" / "sessions"]

# Directive / autonomy signals (high-autonomy = "just do it, don't ask")
_AUTONOMY_RE = re.compile(r"그냥\s*해|알아서|네가\s*(판단|결정)|바로\s*(해|진행|가)|"
                          r"\bgo\b|\bㅇㅋ\b|맡길|자율|don'?t ask|just do it", re.I)
_CONCISE_RE = re.compile(r"간단(히|하게)|짧게|요약|briefly|concise|tl;?dr|한\s*줄", re.I)
_TECH_TERMS = ["python","bash","git","docker","react","typescript","rust","sql","pandas",
               "numpy","pytorch","cloudflare","node","api","llm","nvidia","cuda","ml",
               "csv","json","html","css","커밋","배포","테스트","리팩터"]

def _iter_user_texts(limit_files: int = 400):
    """Yield user-authored message texts from session logs (text only, not stored)."""
    files: list[Path] = []
    for root in SESSION_ROOTS:
        if root.exists():
            files.extend(root.rglob("*.jsonl"))
    files.sort(key=lambda f: f.stat().st_mtime if f.exists() else 0, reverse=True)
    for sf in files[:limit_files]:
        try:
            for line in sf.open(encoding="utf-8", errors="replace"):
                try: d = json.loads(line)
                except json.JSONDecodeError: continue
                msg = d.get("message")
                if not isinstance(msg, dict) or msg.get("role") != "user":
                    continue
                c = msg.get("content")
                if isinstance(c, str):
                    text = c
                elif isinstance(c, list):
                    text = " ".join(b.get("text", "") for b in c
                                    if isinstance(b, dict) and b.get("type") == "text")
                else:
                    continue
                text = text.strip()
                # skip tool-result / system-reminder noise; keep genuine user prompts
                if text and not text.startswith("<") and "tool_result" not in text[:40]:
                    yield text
        except OSError:
            continue

def extract_signals() -> dict:
    """(a) Implicit-feedback capture → structural aggregates only (no raw text kept)."""
    n = 0
    ko_chars = total_chars = 0
    len_sum = autonomy_hits = concise_hits = 0
    tech: dict[str, int] = {}
    for text in _iter_user_texts():
        n += 1
        len_sum += len(text)
        total_chars += len(text)
        ko_chars += sum(1 for ch in text if "가" <= ch <= "힣")
        if _AUTONOMY_RE.search(text): autonomy_hits += 1
        if _CONCISE_RE.search(text): concise_hits += 1
        low = text.lower()
        for t in _TECH_TERMS:
            if t in low:
                tech[t] = tech.get(t, 0) + 1
    if n == 0:
        return {"sample_count": 0}
    ko_ratio = ko_chars / max(total_chars, 1)
    avg_len = len_sum / n
    top_tech = [k for k, _ in sorted(tech.items(), key=lambda x: -x[1])[:8]]
    return {
        "sample_count": n,
        "language": {"korean_ratio": round(ko_ratio, 3),
                     "primary": "korean" if ko_ratio > 0.3 else "english"},
        "verbosity": {"avg_user_chars": round(avg_len),
                      "prefers_concise": concise_hits / n > 0.04,
                      "style": "terse" if avg_len < 120 else "detailed" if avg_len > 400 else "balanced"},
        "autonomy": {"directive_rate": round(autonomy_hits / n, 3),
                     "style": "high" if autonomy_hits / n > 0.03 else "medium"},
        "top_tech": top_tech,
    }

def _signal_to_prefs(sig: dict) -> list[dict]:
    """Turn raw signals into proposable, human-readable preferences with confidence."""
    n = sig.get("sample_count", 0)
    if not n: return []
    conf = min(0.5 + n / 400, 0.95)   # more samples → more confident
    prefs = []
    lang = sig["language"]
    if lang["primary"] == "korean":
        prefs.append({"key": "language", "statement": "한국어로 대화 (코드/식별자는 영어)",
                      "evidence": f"korean_ratio={lang['korean_ratio']}", "confidence": round(conf, 2)})
    v = sig["verbosity"]
    if v["prefers_concise"] or v["style"] == "terse":
        prefs.append({"key": "verbosity", "statement": "간결하게 — 서두 없이 결론부터, 짧게",
                      "evidence": f"avg_chars={v['avg_user_chars']}, style={v['style']}", "confidence": round(conf, 2)})
    a = sig["autonomy"]
    if a["style"] == "high":
        prefs.append({"key": "autonomy", "statement": "높은 자율성 — 되돌릴 수 있는 작업은 묻지 말고 실행",
                      "evidence": f"directive_rate={a['directive_rate']}", "confidence": round(conf, 2)})
    if sig.get("top_tech"):
        prefs.append({"key": "tech", "statement": f"자주 쓰는 스택: {', '.join(sig['top_tech'][:6])}",
                      "evidence": "session term frequency", "confidence": round(conf * 0.8, 2)})
    return prefs

def _load() -> dict:
    if PROFILE_PATH.exists():
        try: return json.loads(PROFILE_PATH.read_text())
        except (json.JSONDecodeError, OSError): pass
    return {"proposed": [], "accepted": [], "rejected": []}

def _save(p: dict) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(p, ensure_ascii=False, indent=2))

def cmd_propose() -> int:
    sig = extract_signals()
    if not sig.get("sample_count"):
        print("no session history found under ~/.claude/projects or ~/.codex/sessions")
        return 1
    prefs = _signal_to_prefs(sig)
    prof = _load()
    accepted_keys = {p["key"] for p in prof["accepted"]}
    rejected_keys = {p["key"] for p in prof["rejected"]}
    prof["proposed"] = [p for p in prefs if p["key"] not in accepted_keys and p["key"] not in rejected_keys]
    _save(prof)
    print(f"✦ analyzed {sig['sample_count']} user messages (structural signals only — no text stored)\n")
    if not prof["proposed"]:
        print("no new preferences to propose (all detected are already accepted/rejected).")
    else:
        print("Proposed preferences (draft — nothing is applied until you accept):")
        for p in prof["proposed"]:
            print(f"  [{p['key']}] {p['statement']}")
            print(f"        └ {p['evidence']}  (confidence {p['confidence']})")
        print("\n→ aios profile accept <key>...   (or `all`)   ·   aios profile reject <key>...")
    return 0

def cmd_show() -> int:
    prof = _load()
    for bucket, label in (("accepted", "✓ ACCEPTED (active)"), ("proposed", "· proposed (draft)"), ("rejected", "✗ rejected")):
        items = prof.get(bucket, [])
        if items:
            print(f"\n{label}")
            for p in items:
                print(f"  [{p['key']}] {p['statement']}")
    if not any(prof.get(b) for b in ("accepted", "proposed", "rejected")):
        print("empty profile — run `aios profile propose` first.")
    return 0

def _move(keys: list[str], to: str) -> int:
    prof = _load()
    pool = prof["proposed"] + prof["accepted"] + prof["rejected"]
    by_key = {p["key"]: p for p in pool}
    if keys == ["all"]:
        keys = [p["key"] for p in prof["proposed"]]
    for src in ("proposed", "accepted", "rejected"):
        prof[src] = [p for p in prof[src] if p["key"] not in keys]
    moved = 0
    for k in keys:
        if k in by_key:
            prof[to].append(by_key[k]); moved += 1
    _save(prof)
    print(f"{to}: {moved} preference(s). Active profile now drives the agent via `aios profile render`.")
    return 0

def render_block(epsilon: float = EXPLORE_EPSILON) -> str:
    """Accepted preferences as an injectable guidance block (empty if none).

    The head/router prepends this to the model prompt so personalization is ACTIVE.
    With probability `epsilon`, append an exploration nudge (filter-bubble guard)."""
    acc = _load().get("accepted", [])
    if not acc:
        return ""
    lines = ["# 유저 선호 (학습됨, draft-first — 언제든 override 가능)"]
    lines += [f"- {p['statement']}" for p in acc]
    if epsilon > 0 and random.random() < epsilon:
        lines.append("- (탐색) 위 습관을 존중하되, 명백히 더 나은 접근이 있으면 "
                     "그대로 따르지 말고 간단히 제안하라.")
    return "\n".join(lines) + "\n"

def cmd_render() -> int:
    """Accepted preferences → an injectable guidance block (for the head/router)."""
    block = render_block(epsilon=0.0)   # deterministic for display
    if block:
        sys.stdout.write(block)
    return 0

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aios profile", description="Learn & manage user preferences")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("propose"); sub.add_parser("show"); sub.add_parser("render")
    for c in ("accept", "reject"):
        sp = sub.add_parser(c); sp.add_argument("keys", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "propose": return cmd_propose()
    if a.cmd == "show":    return cmd_show()
    if a.cmd == "render":  return cmd_render()
    if a.cmd == "accept":  return _move(a.keys, "accepted")
    if a.cmd == "reject":  return _move(a.keys, "rejected")
    ap.print_help(); return 0

if __name__ == "__main__":
    sys.exit(main())
