#!/usr/bin/env python3
"""aios.capabilities.v1 — the closed vocabulary that lets organs assign work to each other.

Founder: each OS should know the others exist and what they can do, so they can give each
other work. That needs a LANGUAGE, and we did not have one. Capability strings were free
text matched by substring, so a typo produced a task that waited forever and a board that
looked busy — measured today as unheld:adversarial sitting with no owner.

So: a closed, versioned vocabulary. An unknown capability is an error AT ENQUEUE, not a
silent eternity in the queue.

WHAT EACH ORGAN IS FOR — re-derived from what actually happened today, not from the role
docs. Every one of the four had zero commits in seven days, and the reason is visible now:
their jobs were built ad hoc elsewhere. Each organ owns a GATE or a LEDGER, never a
service, because a service can be bypassed and a gate cannot.

  memoryOS      not a store — the graph stores better. It owns the DRAFT->ACCEPT gate:
                what is allowed to become accepted knowledge, with provenance. Today it
                holds 397,854 nodes and zero retrieval counts, which is a store's
                statistic, not a gate's.
  CapabilityOS  not a catalogue — aios_model_registry pulls 3,885 live entries. It owns the
                ROUTING-OUTCOME LEDGER: which capability actually worked for which task
                class. Nobody keeps that, which is why our routing table is hand-written.
  GenesisOS     the ADVERSARIAL HOLDER. Today three adversarial tasks queued with no owner
                — that is precisely the hole GenesisOS is for. Its value is conditional:
                measured n_eff says same-weight critics are 1.07 effective votes, so it
                earns its keep only when it reaches heterogeneous substrates.
  HiveMind      EXECUTION EVIDENCE. Receipts that make a claim checkable. The factory's
                close-by-check is a small version of its job.

`consumed_by` is the anti-theatre field. Invocation is not use — 32/32 calls with the
output ignored is 0/32 wearing receipts. Each capability declares what evidence would show
its output was actually consumed, and that is what a task's check must test.
"""
from __future__ import annotations
import json, sys
from dataclasses import dataclass, asdict, field

VOCAB_VERSION = "aios.capability.v1"


@dataclass(frozen=True)
class Capability:
    name: str
    owner: str                  # which organ is accountable
    what: str
    consumed_by: str            # what evidence proves the output was USED, not just made
    ceiling: str                # minimum side-effect ceiling a holder needs
    heterogeneous: bool = False # must reach non-Claude weights to be worth anything


CAPABILITIES: dict[str, Capability] = {c.name: c for c in [
    # --- memoryOS: the accept gate -------------------------------------------------
    Capability("memory.retrieve", "memoryOS",
               "회수: 이 결정에 걸리는 accepted memory를 반환",
               "회수된 pack의 digest가 다음 행동의 입력 manifest에 나타남 (seam §2c)",
               "L0_read"),
    Capability("memory.propose", "memoryOS",
               "초안 제안: 새 기억을 draft로 올린다 (자동 수락 금지, DNA #2)",
               "draft가 review 큐에 존재하고 provenance evidence_refs가 비어있지 않음",
               "L1_local_write"),
    Capability("memory.review", "memoryOS",
               "draft→accept 게이트 판정",
               "accept/reject 기록에 근거가 붙고, accept된 항목이 이후 retrieve에 등장",
               "L1_local_write"),
    # --- CapabilityOS: the routing-outcome ledger ----------------------------------
    Capability("capability.recommend", "CapabilityOS",
               "이 과제 유형에 무엇을 쓸지 권고 (구속하지 않음, DNA #1)",
               "권고가 실제 라우팅을 바꿨거나, 바꾸지 않은 이유가 기록됨",
               "L0_read"),
    Capability("capability.record_outcome", "CapabilityOS",
               "라우팅 결과 기록: 어느 기질이 어느 과제류에서 실제로 통했는가",
               "정적 라우팅표가 이 원장에서 유도됨 (손으로 쓰인 표가 사라짐)",
               "L1_local_write"),
    # --- GenesisOS: the adversary --------------------------------------------------
    Capability("adversarial.refute", "GenesisOS",
               "반증 시도. 동의가 아니라 무너뜨리기를 목표로",
               "반증이 문서·결정을 실제로 바꿨음이 diff로 확인됨",
               "L3_network_read", heterogeneous=True),
    Capability("adversarial.reframe", "GenesisOS",
               "같은 실패가 3회면 SHAPE가 틀렸다 — 직교 재프레이밍 강제",
               "새 프레이밍이 사전등록으로 동결됨 (prereg_superseded 근거 포함)",
               "L1_local_write", heterogeneous=True),
    # --- HiveMind: execution evidence ----------------------------------------------
    Capability("execute.verified", "HiveMind",
               "실행하고 외부 체크로 닫는다 — 주장이 아니라 rc로",
               "close()가 rc=0으로 닫았고 산출물이 존재",
               "L2_process"),
    Capability("execute.receipt", "HiveMind",
               "실행 영수증: seed·입력 digest·산출물 digest·지연",
               "영수증이 원장에 있고 root 재계산이 일치",
               "L1_local_write"),
    # --- control plane -------------------------------------------------------------
    Capability("grounding.external", "myworld",
               "외부 그라운딩. 우리 가중치가 구조적으로 낡은 질문류",
               "답변에 출처 URL과 날짜가 있고 knowledge ledger에 기록됨",
               "L3_network_read", heterogeneous=True),
    Capability("graph.audit", "myworld",
               "유기체 감사: 고아율·연결성·부패",
               "고아율이 판정 기준 대비 보고됨",
               "L0_read"),
    Capability("docs.harvest", "myworld",
               "외부 문서 수확 → 지식그래프 편입",
               "manifest 행이 늘고 새 노드가 그래프에 존재",
               "L3_network_read"),
]}

CEILINGS = ("L0_read", "L1_local_write", "L2_process", "L3_network_read",
            "L4_network_write", "L5_install", "L6_credential", "L7_external_send",
            "L8_irreversible")


def validate(name: str) -> Capability:
    """Unknown capability is an error HERE, not a task that waits forever."""
    c = CAPABILITIES.get(name)
    if c is None:
        near = [k for k in CAPABILITIES if k.split(".")[0] == name.split(".")[0]]
        raise KeyError(
            f"unknown capability {name!r} (vocab {VOCAB_VERSION}). "
            + (f"did you mean: {near}? " if near else "")
            + f"known: {sorted(CAPABILITIES)}")
    return c


def by_owner() -> dict[str, list[Capability]]:
    out: dict[str, list[Capability]] = {}
    for c in CAPABILITIES.values():
        out.setdefault(c.owner, []).append(c)
    return out


def main() -> int:
    if "--json" in sys.argv:
        print(json.dumps({"version": VOCAB_VERSION,
                          "capabilities": [asdict(c) for c in CAPABILITIES.values()]},
                         ensure_ascii=False, indent=1))
        return 0
    print(f"{VOCAB_VERSION} — {len(CAPABILITIES)} capabilities, {len(by_owner())} owners\n")
    for owner, caps in by_owner().items():
        print(f"  {owner}")
        for c in caps:
            het = "  [이종 필수]" if c.heterogeneous else ""
            print(f"    {c.name:<28}{c.ceiling:<18}{c.what[:44]}{het}")
            print(f"      {'소비 증거:':<12}{c.consumed_by[:78]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
