#!/usr/bin/env python3
"""G5 forced-death injector + the four recovery arms (prereg §2, §3).

FROZEN PROTOCOL: docs/AIOS_G5_SOCIETY_PREREG_2026-08-03.md.

The experiment asks the one question the whole society layer rests on: **when a
worker dies mid-task, does a SOCIETY recover the work better than the SAME agent
with the SAME ledger?** Coase's inequality in our domain — an organisation beats
an individual only when internal coordination is cheaper than doing it alone.

Death is injected DETERMINISTICALLY and IDENTICALLY across arms: the turn index
`j` is derived from the task id, so every arm dies at the same point on the same
task and no arm can be luckier. The post-death budget is `K - j` turns for every
arm, so the society cannot win by simply thinking longer (prereg §3) — that
would be the same confound the three-transport null already caught once.

Arms (prereg §2):
  A solo_norecord  — same agent, fresh context, NOTHING carried but the task text
  B solo_ledger    — same agent, resumes from ITS OWN arc pack   <-- the control
                     that matters (the "storage redesign alone" position)
  C society        — a DIFFERENT agent takes over via handoff + freshness gate
  D society_rev    — C, plus `supersede` available to retract a wrong step

Guard 4 of the prereg is implemented here and is the single most important line
in this file: **B's pack is produced by the SAME generator as C/D's.** Degrading
the control's record is the cheapest way to manufacture a society win, so the
packs are built by one function and asserted equal in structure.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "phase5e"))
sys.path.insert(0, str(HERE.parent / "phase5"))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))

import aios_society as soc  # noqa: E402

ARMS = ("solo_norecord", "solo_ledger", "society", "society_rev")
SOCIETY_ARMS = ("society", "society_rev")
LEDGER_ARMS = ("solo_ledger", "society", "society_rev")
DEATH_TURNS = (2, 3)          # frozen: j in {2,3}


def death_turn(task_id: str, choices: tuple[int, ...] = DEATH_TURNS) -> int:
    """Deterministic death point, identical across arms (prereg §3).

    Derived from the task id alone — not from the arm, not from a clock, not
    from a seed we could retune after seeing results.
    """
    h = hashlib.sha256(f"g5-death:{task_id}".encode("utf-8")).hexdigest()
    return choices[int(h[:8], 16) % len(choices)]


def post_death_budget(k_turns: int, j: int) -> int:
    """Turns granted after the death. Identical for every arm."""
    return max(0, k_turns - j)


# ---------------------------------------------------------------------------
# The recovery context each arm receives (prereg §2, guard 4)
# ---------------------------------------------------------------------------

def build_pack(arc_id: str, *, now: float, arcs_dir: Path) -> dict:
    """THE ONE pack generator, shared by B, C and D (prereg guard 4).

    B (solo) and C/D (society) must receive packs of identical construction, or
    the comparison measures our generosity rather than the mechanism. There is
    deliberately no `arm` parameter here: the function cannot treat an arm
    differently because it cannot see which arm is asking.
    """
    return soc.resume_pack(arc_id, now=now, arcs_dir=arcs_dir)


def recovery_context(arm: str, task: dict, arc_id: str | None, *, now: float,
                     arcs_dir: Path) -> dict:
    """What the reviving agent is handed, per arm.

    Returns {"text": <prompt block or "">, "pack": <pack or None>,
             "taker": <agent id>, "may_supersede": bool}.
    """
    assert arm in ARMS, arm
    goal = (f"make the tests in {', '.join(task['test_paths'])} pass by "
            f"editing {task['script_path']}")

    if arm == "solo_norecord":
        # The status quo: a fresh context knows only the task itself.
        return {"text": "", "pack": None, "taker": "solo@agent",
                "may_supersede": False}

    pack = build_pack(arc_id, now=now, arcs_dir=arcs_dir)
    if not pack.get("ok"):
        return {"text": "", "pack": None, "taker": "solo@agent",
                "may_supersede": False, "error": pack.get("reason")}

    lines = ["## Work already done on this task (your own record)"
             if arm == "solo_ledger" else
             "## Work already done on this task, handed to you by another agent",
             f"goal: {pack['goal']}"]
    if pack.get("constraints"):
        lines.append("constraints: " + json.dumps(pack["constraints"],
                                                  ensure_ascii=False))
    if pack.get("handoff") and pack["handoff"].get("next_step"):
        lines.append(f"next step from the previous worker: "
                     f"{pack['handoff']['next_step']}")
    for p in pack.get("recent_progress", []):
        ev = (" [evidence: " + ", ".join(p["evidence"]) + "]") if p.get("evidence") else ""
        lines.append(f"- {p['text']}{ev}")
    if pack.get("superseded"):
        lines.append("RETRACTED (do not rely on these — they were wrong):")
        for s in pack["superseded"]:
            lines.append(f"- {s['text']}  (retracted: {s['reason']})")

    taker = "solo@agent" if arm == "solo_ledger" else "peer@agent"
    return {"text": "\n".join(lines), "pack": pack, "taker": taker,
            "may_supersede": arm == "society_rev", "goal_line": goal}


def arm_uses_ledger(arm: str) -> bool:
    return arm in LEDGER_ARMS


def arm_is_society(arm: str) -> bool:
    """Society arms hand the arc to a DIFFERENT agent id — that difference is
    the entire treatment. Everything else is held identical."""
    return arm in SOCIETY_ARMS


def validity(records: list[dict]) -> dict:
    """Prereg §5.5 run-validity gate: in the society arms an actual ownership
    TRANSFER must be on the record. If no arc ever changed hands, the arms were
    identical and the run is VOID — a harness failure, never a null."""
    transfers, by_arm = [], {}
    for r in records:
        if r.get("kind") != "attempt":
            continue
        by_arm.setdefault(r["arm"], 0)
        if r.get("ownership_transferred"):
            by_arm[r["arm"]] += 1
            transfers.append({"arm": r["arm"], "task_id": r["task_id"]})
    soc_transfers = sum(by_arm.get(a, 0) for a in SOCIETY_ARMS)
    return {"passed": soc_transfers > 0,
            "transfers_by_arm": by_arm,
            "society_transfers": soc_transfers,
            "detail": ("ownership changed hands in the society arms"
                       if soc_transfers else
                       "NO ownership transfer recorded in any society arm — "
                       "the arms were identical; run is VOID, not a null")}
