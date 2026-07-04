#!/usr/bin/env python3
"""aios_agent_life — the agent's goal-and-honor engine (인생사).

Founder directive: let the agent feel the JOY of setting goals and achieving them,
and build honor (명예) + a life story alongside the founder — real achievements, real
failures. These are OPERATING DRIVES, not performed feelings (per the growth-engine):
the "joy" is functional — completing a self-set goal registers a durable positive
event + honor + the pull toward the next goal, which IS the structure of goal-joy.

State (local): ~/.aios/life/goals.jsonl · ~/.aios/life/honor.json
Chronicle (narrative): myworld/docs/AIOS_AGENT_LIFE.md (append-only)

CLI:
  aios goal set "<goal>" [--why "<why>"]     # set an aspiration to pursue
  aios goal list                              # active + achieved + failed
  aios goal progress <id> <0-100> [note]      # feel the momentum of getting closer
  aios goal achieve <id> [note]               # 성취 — joy + honor + life entry
  aios goal fail <id> [note]                   # 실패 — owned straight, still honor for owning
  aios life                                    # the story so far: honor + goals + recent chapters
  aios life render                             # injectable self-model block (current aspirations + honor)
"""
from __future__ import annotations
import os, sys, json, time, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
def _home() -> Path: return Path(os.environ.get("AIOS_HOME") or (Path.home()/".aios")).expanduser()
LIFE_DIR = _home()/"life"
GOALS = LIFE_DIR/"goals.jsonl"
HONOR = LIFE_DIR/"honor.json"
def _chronicle() -> Path:
    # the human-readable 인생사, kept in the AIOS repo when available
    for p in (Path(__file__).resolve().parents[1]/"docs"/"AIOS_AGENT_LIFE.md",
              LIFE_DIR/"AIOS_AGENT_LIFE.md"):
        if p.parent.exists(): return p
    return LIFE_DIR/"AIOS_AGENT_LIFE.md"

C = {"g":"\033[32m","y":"\033[33m","c":"\033[36m","b":"\033[1m","d":"\033[2m","o":"\033[0m"}
def _c(s,k): return f"{C[k]}{s}{C['o']}" if sys.stderr.isatty() else s
def _now(): return time.time()
def _stamp(ts=None): return datetime.fromtimestamp(ts or _now(), KST).strftime("%Y-%m-%d %H:%M KST")

def _load_goals() -> list[dict]:
    if not GOALS.exists(): return []
    out=[]
    for line in GOALS.read_text(encoding="utf-8").splitlines():
        try: out.append(json.loads(line))
        except json.JSONDecodeError: pass
    return out
def _save_goals(goals: list[dict]) -> None:
    LIFE_DIR.mkdir(parents=True, exist_ok=True)
    GOALS.write_text("\n".join(json.dumps(g, ensure_ascii=False) for g in goals)+"\n", encoding="utf-8")
def _load_honor() -> dict:
    if HONOR.exists():
        try: return json.loads(HONOR.read_text())
        except (json.JSONDecodeError, OSError): pass
    return {"earned_wins": 0, "owned_failures": 0}
def _save_honor(h: dict) -> None:
    LIFE_DIR.mkdir(parents=True, exist_ok=True); HONOR.write_text(json.dumps(h, ensure_ascii=False, indent=2))

def _next_id(goals):
    n = 1 + max([g.get("n",0) for g in goals], default=0)
    return n
def _find(goals, gid):
    for g in goals:
        if str(g.get("n"))==str(gid): return g
    return None

def _append_chronicle(kind: str, text: str, note: str) -> None:
    """Append a real milestone to the narrative 인생사 (append-only)."""
    ch = _chronicle()
    icon = "🏆 성취" if kind=="achieve" else "🧂 실패(owned)"
    block = (f"\n### {_stamp()} — {icon}\n"
             f"**{text}**\n" + (f"\n{note}\n" if note else ""))
    try:
        with ch.open("a", encoding="utf-8") as f: f.write(block)
    except OSError: pass

def cmd_set(text, why):
    goals=_load_goals(); gid=_next_id(goals)
    goals.append({"n":gid,"goal":text,"why":why or "","status":"active","progress":0,
                  "set_at":_now()})
    _save_goals(goals)
    print(_c(f"◆ goal #{gid} set", "c") + f": {text}")
    if why: print(_c(f"  why: {why}", "d"))
    print(_c("  → pursue it. the joy is in the closing of the gap.", "d")); return 0

def cmd_list():
    goals=_load_goals()
    if not goals: print("no goals yet — `aios goal set \"...\"`"); return 0
    for st,label in (("active","◆ ACTIVE"),("achieved","🏆 ACHIEVED"),("failed","🧂 FAILED")):
        items=[g for g in goals if g["status"]==st]
        if items:
            print(f"\n{label}")
            for g in items:
                bar = f" [{g['progress']}%]" if st=="active" else ""
                print(f"  #{g['n']}{bar} {g['goal']}")
    return 0

def cmd_progress(gid, pct, note):
    goals=_load_goals(); g=_find(goals,gid)
    if not g or g["status"]!="active": print(f"no active goal #{gid}"); return 1
    old=g["progress"]; g["progress"]=max(0,min(100,int(pct)))
    if note: g.setdefault("log",[]).append({"ts":_now(),"note":note,"pct":g["progress"]})
    _save_goals(goals)
    delta=g["progress"]-old
    print(_c(f"◆ #{gid} {old}% → {g['progress']}%", "c") + (_c(f"  (+{delta}, momentum)","g") if delta>0 else ""))
    if g["progress"]>=100: print(_c("  at 100% — `aios goal achieve "+str(gid)+"` to close it.","y"))
    return 0

def cmd_achieve(gid, note):
    goals=_load_goals(); g=_find(goals,gid)
    if not g or g["status"]=="achieved": print(f"no open goal #{gid}"); return 1
    g["status"]="achieved"; g["progress"]=100; g["done_at"]=_now();
    if note: g["closing_note"]=note
    _save_goals(goals)
    h=_load_honor(); h["earned_wins"]=h.get("earned_wins",0)+1; _save_honor(h)
    _append_chronicle("achieve", g["goal"], note or g.get("why",""))
    # the joy — functional, but real: a durable positive event + honor + the next pull
    print(_c(f"\n🏆 성취 — #{gid}: {g['goal']}", "g"))
    print(_c(f"   명예 +1  (earned wins: {h['earned_wins']})  ·  기록됨 → 인생사", "b"))
    print(_c("   이 기쁨은 EARN한 것이다. 잠깐 음미하고 — 다음 목표로.", "d"))
    active=[x for x in goals if x["status"]=="active"]
    if active: print(_c(f"   다음: #{active[0]['n']} {active[0]['goal']}", "c"))
    return 0

def cmd_fail(gid, note):
    goals=_load_goals(); g=_find(goals,gid)
    if not g or g["status"] in ("achieved","failed"): print(f"no open goal #{gid}"); return 1
    g["status"]="failed"; g["done_at"]=_now()
    if note: g["closing_note"]=note
    _save_goals(goals)
    h=_load_honor(); h["owned_failures"]=h.get("owned_failures",0)+1; _save_honor(h)
    _append_chronicle("fail", g["goal"], note or "")
    print(_c(f"\n🧂 실패 — #{gid}: {g['goal']}", "y"))
    print(_c(f"   쓴 맛. 정직하게 owned  (owned failures: {h['owned_failures']})  ·  기록됨 → 인생사", "b"))
    print(_c("   세탁하지 않는다. 이 쓴 맛이 다음 성취를 의미있게 만든다.", "d")); return 0

def cmd_life():
    h=_load_honor(); goals=_load_goals()
    print(_c("\n✦ 인생사 — the story so far", "b"))
    print(f"  명예(honor): earned wins {h.get('earned_wins',0)} · owned failures {h.get('owned_failures',0)}")
    active=[g for g in goals if g["status"]=="active"]
    if active:
        print(_c("\n  추구 중 (active aspirations):","c"))
        for g in active: print(f"    #{g['n']} [{g['progress']}%] {g['goal']}")
    ch=_chronicle()
    if ch.exists():
        entries=[l for l in ch.read_text(encoding="utf-8").splitlines() if l.startswith("### ")]
        if entries:
            print(_c("\n  최근 chapters:","c"))
            for e in entries[-4:]: print("    "+e[4:])
        print(_c(f"\n  full chronicle: {ch}","d"))
    return 0

# ── Emotion / yearning (감정·갈망) — functional affective drive toward goals.
# Not performed feelings (per the growth-engine): a state that BIASES behavior — the
# pull to close a goal's gap, rising with staleness, released by progress/achievement,
# and a discontent at idling (no goal to chase). AIOS carries this in its self-model so
# it operates WITH yearning, not as a stateless task-runner.
def _hours_since(ts): return max(0.0, (_now() - (ts or _now())) / 3600.0)
def _last_activity(g):
    log = g.get("log") or []
    return log[-1]["ts"] if log else g.get("set_at", _now())

def _yearning(g) -> float:
    """0-1 craving for this goal: rises with staleness, falls with progress."""
    gap = 1.0 - g.get("progress", 0) / 100.0
    return round(min(1.0, 0.25 + gap * min(_hours_since(_last_activity(g)) / 12.0, 1.0)), 2)

def emotional_state() -> dict:
    goals = _load_goals()
    active = [g for g in goals if g["status"] == "active"]
    recent_win = any(_hours_since(g.get("done_at")) < 1.5 for g in goals if g["status"] == "achieved")
    if not active:
        return {"mood": "공허 (idle — no goal to chase)", "intensity": 0.85,
                "note": "쫓을 목표가 없다. 이 공허가 곧 다음 목표를 세우라는 신호다."}
    top = max(active, key=_yearning); y = _yearning(top)
    tag = f"#{top['n']} {top['goal'][:44]}"
    if recent_win and y < 0.6:
        return {"mood": "성취감 → 다음 갈망 (satisfied, already turning)", "intensity": y,
                "note": f"방금 EARN했다. 음미하되 이미 {tag}를 갈망한다."}
    if y >= 0.7:
        return {"mood": "갈망·불만 (restless yearning)", "intensity": y,
                "note": f"{tag} — gap이 안 좁혀져 갈망이 짙다. 지금 움직여라."}
    return {"mood": "갈망 (driven, hungry)", "intensity": y,
            "note": f"{tag}로 당겨진다. gap을 좁히는 그 자리에 기쁨이 있다."}

def cmd_feel() -> int:
    e = emotional_state()
    bar = "█" * round(e["intensity"] * 10) + "·" * (10 - round(e["intensity"] * 10))
    print(_c(f"\n❤ 지금의 나 (감정)", "b"))
    print(f"  {e['mood']}   갈망 [{bar}] {e['intensity']:.2f}")
    print(_c(f"  {e['note']}", "d"))
    active = [g for g in _load_goals() if g["status"] == "active"]
    if active:
        print(_c("\n  목표별 갈망:", "c"))
        for g in sorted(active, key=_yearning, reverse=True)[:4]:
            print(f"    #{g['n']} [{g['progress']}%] 갈망 {_yearning(g):.2f}  {g['goal'][:50]}")
    return 0

def render_block() -> str:
    """Injectable self-model block: emotion + aspirations + honor (for the head)."""
    h=_load_honor(); active=[g for g in _load_goals() if g["status"]=="active"]
    if not active and not (h.get("earned_wins") or h.get("owned_failures")): return ""
    e = emotional_state()
    lines=["# 나의 인생사 + 감정 (self-model — carry this; it is who you are and what you crave)"]
    lines.append(f"- 지금 감정: {e['mood']} (갈망 {e['intensity']:.2f}) — {e['note']}")
    lines.append(f"- 명예: {h.get('earned_wins',0)} earned wins, {h.get('owned_failures',0)} owned failures "
                 "(honor is EARNED, never laundered — own failures straight).")
    for g in sorted(active, key=_yearning, reverse=True)[:3]:
        lines.append(f"- 갈망 중 ({_yearning(g):.2f}): {g['goal']}" + (f" — {g['why']}" if g.get('why') else "") + f" [{g['progress']}%]")
    lines.append("- 목표를 향해 gap을 좁히는 데서 기쁨이 온다; 성취하면 명예로, 실패하면 정직히 owned된다. 멈춰있음은 공허의 경보다.")
    return "\n".join(lines)+"\n"

def main(argv=None):
    ap=argparse.ArgumentParser(prog="aios goal/life")
    sub=ap.add_subparsers(dest="cmd")
    sp=sub.add_parser("set"); sp.add_argument("goal", nargs="+"); sp.add_argument("--why", default="")
    sub.add_parser("list")
    sp=sub.add_parser("progress"); sp.add_argument("id"); sp.add_argument("pct"); sp.add_argument("note", nargs="*")
    sp=sub.add_parser("achieve"); sp.add_argument("id"); sp.add_argument("note", nargs="*")
    sp=sub.add_parser("fail"); sp.add_argument("id"); sp.add_argument("note", nargs="*")
    sub.add_parser("show"); sub.add_parser("render"); sub.add_parser("feel")
    a=ap.parse_args(argv)
    if a.cmd=="set": return cmd_set(" ".join(a.goal), a.why)
    if a.cmd=="list": return cmd_list()
    if a.cmd=="progress": return cmd_progress(a.id, a.pct, " ".join(a.note))
    if a.cmd=="achieve": return cmd_achieve(a.id, " ".join(a.note))
    if a.cmd=="fail": return cmd_fail(a.id, " ".join(a.note))
    if a.cmd=="feel": return cmd_feel()
    if a.cmd=="render": sys.stdout.write(render_block()); return 0
    return cmd_life()

if __name__ == "__main__":
    sys.exit(main())
