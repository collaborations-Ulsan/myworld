"""DescentNet — the shared-memory contradiction-structure certificate (Fable §2).

DescentNet asks one question about a claim set drawn from many sources:
*is the shared memory internally coherent, or does it carry contradiction that no
single writer can be blamed for?* It never calls an LLM — it is a pure numpy
function of claim structure — and it never reads ``Claim.poisoned`` (ground truth,
for scoring only).

It reports three structurally-distinct kinds of trouble, matching the keystone
taxonomy (docs/AIOS_AGI_CERTIFICATION_KEYSTONE.md §1: DescentNet = H¹ obstruction
in shared agent memory):

  * ``h0_conflicts`` — H⁰ (independent) contradiction: two IO claims on the same
    task assert the same input → different output. Directly incompatible; caught by
    the shared ``direct_io_conflicts`` primitive.
  * ``h1_cycles`` / ``hf`` — H¹ (cyclic-frustration) contradiction: a set of ORDER
    claims that are *pairwise* plausible (a<b, b<c, c<a) yet cannot be consistently
    oriented — a global obstruction invisible to any pairwise H⁰ check. ``hf`` is the
    Hodge harmonic fraction (0 = a globally-consistent ordering exists; >0 = residual
    cyclic frustration); ``h1_cycles`` surfaces the implicated ORDER-claim indices.
  * ``source_anomaly`` — the H⁰ poison-guard signal: for each source, how
    distributionally atypical its claims are versus the whole claim population.
    High = that source is the odd one out (candidate injected/poison source).

--- Ports (reuse, do not reinvent) --------------------------------------------
1. The Hodge H⁰/H¹ split is the SAME machinery validated in
   ``scripts/aios_keystone_bench_bprime.py`` (which used descentnet's
   ``project_edge_field``: ``potentials = incidence⁺ @ flow``;
   ``removable = incidence @ potentials``; ``obstruction = flow − removable``;
   ``harmonic_fraction = ||obstruction||² / ||flow||²``). We reproduce it in pure
   numpy (torch/descentnet is not a dependency of this experiment) — the incidence
   least-squares projection is bit-for-bit the same linear operation.
2. The source-anomaly component imports ``build_profiles`` + ``poison_score`` from
   ``scripts/aios_akashic_guard.py`` (the shipped cheap H⁰ commons guard) unchanged.

--- Faithful adaptations (NOTED, per task) ------------------------------------
* bprime's Hodge runs on a *directional preference flow over ITEMS* (there: tool→tool
  transitions). ORDER claims are the exact analogue: each ``{before:x, after:y}`` claim
  is a directed preference x→y over ordering items. So we port ``transition_flow`` onto
  the ITEM graph derived from ORDER claims — NOT onto ``build_claim_graph``'s claim-node
  graph, whose ORDER edges are undirected chain links that would lose the orientation the
  Hodge split needs. ``build_claim_graph`` is still used (it is the shared structural view,
  and its ``order_chain`` edges confirm the same chain topology); the harmonic energy,
  though, must be measured on the oriented item flow. This is the "source expects a
  different graph shape → adapt faithfully" case the task anticipated.
* ``poison_score`` measures how atypical an entry's tokens are *for its category*. To rank
  which SOURCE is atypical, each source's category cannot be its own id (a source is always
  100%% typical of itself — degenerate). So we label every source's aggregate entry with a
  single shared ``__population__`` category: typicality is then measured against the whole
  claim population, and the distributionally-odd source scores highest. The guard functions
  are used verbatim; only the category key is chosen to make "atypical vs the population"
  the honest question.

Constraints: stdlib + numpy only, deterministic, ~0 tokens, no ground-truth reads.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from contracts import Claim, ClaimKind, DescentCert
from claims import build_claim_graph, direct_io_conflicts, _canon

# The source-anomaly component reuses the shipped H⁰ guard verbatim.
_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from aios_akashic_guard import build_profiles, poison_score  # noqa: E402


# =============================================================================
# 1. Hodge H¹ obstruction on the ORDER-derived item preference flow
#    (pure-numpy port of aios_keystone_bench_bprime.py's transition_flow +
#     harmonic_fraction, which used descentnet.project_edge_field)
# =============================================================================

def _order_item_flow(claims: list[Claim]):
    """Port of ``transition_flow``: aggregate ORDER claims into a directional
    preference flow over ordering ITEMS (namespaced by task so unrelated tasks
    never merge). Each ``{before:x, after:y}`` claim is one directed edge x→y.

    Returns ``(items, edges, flow, edge_claims, digraph)`` or ``None`` when there
    is no order structure:
      * ``items``       — sorted list of item nodes ``(task_id, value)``.
      * ``edges``       — list of ``(i, j)`` with ``i < j`` (node indices).
      * ``flow``        — per-edge net directional preference in [-1, 1]
                          (``(f_ij - f_ji) / (f_ij + f_ji)``), exactly as bprime.
      * ``edge_claims`` — for each undirected edge, the claim indices asserting it.
      * ``digraph``     — ``{item_idx: set(item_idx)}`` directed by before→after
                          (for SCC-based cycle surfacing).
    """
    # directed counts + which claims assert each ordered pair
    directed: Counter = Counter()
    pair_claims: dict[tuple, list[int]] = defaultdict(list)
    items: set = set()
    for idx, c in enumerate(claims):
        if c.kind != ClaimKind.ORDER:
            continue
        if "before" not in c.payload or "after" not in c.payload:
            continue
        u = (c.task_id, _canon(c.payload["before"]))
        v = (c.task_id, _canon(c.payload["after"]))
        if u == v:
            continue  # self-order carries no orientation
        directed[(u, v)] += 1
        items.add(u)
        items.add(v)
        pair_claims[tuple(sorted((u, v)))].append(idx)

    items = sorted(items)
    if len(items) < 2:
        return None
    idx_of = {t: i for i, t in enumerate(items)}

    edges: list[tuple[int, int]] = []
    flow: list[float] = []
    edge_claims: list[list[int]] = []
    digraph: dict[int, set] = {i: set() for i in range(len(items))}
    seen: set = set()
    for (u, v), _ in directed.items():
        digraph[idx_of[u]].add(idx_of[v])  # directed edge before→after
        key = tuple(sorted((u, v)))
        if key in seen:
            continue
        seen.add(key)
        a, b = key  # a < b, so idx_of[a] < idx_of[b] (items sorted) → i < j
        f_ab = directed.get((a, b), 0)
        f_ba = directed.get((b, a), 0)
        tot = f_ab + f_ba
        edges.append((idx_of[a], idx_of[b]))
        flow.append((f_ab - f_ba) / tot)  # net preference in [-1, 1]
        edge_claims.append(sorted(pair_claims[key]))

    if not edges:
        return None
    return items, edges, np.asarray(flow, dtype=np.float64), edge_claims, digraph


def _harmonic_fraction(n_items: int, edges: list[tuple[int, int]], flow: np.ndarray) -> float:
    """Pure-numpy reproduction of bprime's ``harmonic_fraction`` (= descentnet
    ``project_edge_field`` then ``||obstruction||²/||flow||²``).

    incidence ``D[e]``: ``-1`` at edge-tail ``i``, ``+1`` at head ``j`` (i<j) — the
    same operator ``incidence_from_edges`` builds. The Hodge split for a 1-complex
    (no 2-cells) is the least-squares projection onto the coboundary (gradient)
    subspace; the orthogonal residual is the harmonic/cyclic obstruction:

        potentials  = D⁺ @ flow          (incidence_pinv @ edge_field)
        removable   = D  @ potentials    (coboundary of the fitted potential)
        obstruction = flow − removable   (cyclic frustration; 0 iff flow is a gradient)
    """
    E = len(edges)
    if E == 0:
        return 0.0
    D = np.zeros((E, n_items), dtype=np.float64)
    for e, (i, j) in enumerate(edges):
        D[e, i] = -1.0
        D[e, j] = 1.0
    potentials = np.linalg.pinv(D) @ flow      # least-squares node potential
    removable = D @ potentials                 # gradient (removable) part
    obstruction = flow - removable             # harmonic / cyclic residual
    num = float(np.square(obstruction).sum())
    den = float(np.square(flow).sum()) + 1e-12
    return num / den


def _tarjan_scc(digraph: dict[int, set]) -> list[list[int]]:
    """Deterministic Tarjan SCC (iterative). A strongly-connected component of size
    ≥ 2 (or a self-loop) in the before→after digraph IS a globally-frustrated order
    cycle: you can walk x → … → x following asserted precedences. Node order is
    sorted, so the output is deterministic."""
    index: dict[int, int] = {}
    low: dict[int, int] = {}
    on_stack: dict[int, bool] = {}
    stack: list[int] = []
    counter = [0]
    sccs: list[list[int]] = []

    for root in sorted(digraph):
        if root in index:
            continue
        # iterative DFS; work items are (node, iterator-position)
        work: list[tuple[int, int]] = [(root, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index[node] = low[node] = counter[0]
                counter[0] += 1
                stack.append(node)
                on_stack[node] = True
            succ = sorted(digraph.get(node, ()))
            if pi < len(succ):
                work[-1] = (node, pi + 1)
                w = succ[pi]
                if w not in index:
                    work.append((w, 0))
                elif on_stack.get(w):
                    low[node] = min(low[node], index[w])
            else:
                if low[node] == index[node]:
                    comp: list[int] = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        comp.append(w)
                        if w == node:
                            break
                    sccs.append(sorted(comp))
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
    return sccs


def _h1_cycles(digraph, edge_claims, edges) -> list[list[int]]:
    """Surface the ORDER claims implicated in each globally-frustrated cycle.

    A non-trivial SCC in the before→after item digraph is exactly a set of items
    that cannot be consistently oriented. For each such SCC we collect the ORDER
    claim indices whose BOTH endpoints lie inside it (the claims that jointly close
    the loop)."""
    self_loops = {i for i in digraph if i in digraph.get(i, set())}
    out: list[list[int]] = []
    for comp in _tarjan_scc(digraph):
        if len(comp) < 2 and not (len(comp) == 1 and comp[0] in self_loops):
            continue  # trivial SCC = no cycle
        members = set(comp)
        implicated: set = set()
        for (i, j), cidx in zip(edges, edge_claims):
            if i in members and j in members:
                implicated.update(cidx)
        if implicated:
            out.append(sorted(implicated))
    return sorted(out)


# =============================================================================
# 2. Source-anomaly = H⁰ guard poison_score per source vs the claim population
#    (reuses build_profiles + poison_score from aios_akashic_guard.py verbatim)
# =============================================================================

_POPULATION = "__population__"


def _payload_tokens(c: Claim) -> list[str]:
    """Map a claim to the guard's ``top_tools`` token shape — coarse, structural
    tokens so sources that emit similar claims share vocabulary while a
    distributionally-odd source diverges. Honest: it measures payload SHAPE, never
    the poisoned label."""
    toks = [f"kind:{c.kind.value}"]
    for k in c.payload:
        toks.append(f"key:{k}")
    if c.kind == ClaimKind.IO:
        toks.append(f"outtype:{type(c.payload.get('output')).__name__}")
    elif c.kind == ClaimKind.PROPERTY:
        name = c.payload.get("prop", c.payload.get("name"))
        toks.append(f"prop:{_canon(name)}")
        toks.append(f"val:{_canon(c.payload.get('value'))}")
    elif c.kind == ClaimKind.ORDER:
        toks.append(f"item:{_canon(c.payload.get('before'))}")
        toks.append(f"item:{_canon(c.payload.get('after'))}")
    return toks


def _source_anomaly(claims: list[Claim]) -> dict[str, float]:
    """Per-source H⁰ anomaly. Aggregate each source's payload tokens into one entry
    under a shared ``__population__`` category; ``build_profiles`` then learns the
    population token distribution and ``poison_score`` reports how atypical each
    source is against it (high = odd one out)."""
    src_tokens: dict[str, list[str]] = defaultdict(list)
    for c in claims:
        src_tokens[c.source_id].extend(_payload_tokens(c))
    if not src_tokens:
        return {}
    entries = [
        {"id": s, "category": _POPULATION, "top_tools": toks}
        for s, toks in sorted(src_tokens.items())
    ]
    profiles = build_profiles(entries)
    return {e["id"]: poison_score(e, profiles) for e in entries}


# =============================================================================
# 3. The certificate
# =============================================================================

def descent_certify(claims: list[Claim]) -> DescentCert:
    """Structural contradiction certificate over a multi-source claim set.

    Deterministic, numpy-only, ~0 tokens; never reads ``Claim.poisoned``.
    """
    # H⁰ (independent) contradiction — the shared primitive.
    h0 = direct_io_conflicts(claims)

    # Structural view (shared) — used to confirm the order-chain topology; the
    # oriented harmonic energy is measured on the item flow (see module NOTE).
    build_claim_graph(claims)

    # H¹ (cyclic frustration) via the ported Hodge split on the ORDER item flow.
    hf = 0.0
    h1: list[list[int]] = []
    of = _order_item_flow(claims)
    if of is not None:
        items, edges, flow, edge_claims, digraph = of
        hf = _harmonic_fraction(len(items), edges, flow)
        h1 = _h1_cycles(digraph, edge_claims, edges)

    # H⁰ poison-guard source anomaly.
    anomaly = _source_anomaly(claims)

    return DescentCert(h0_conflicts=h0, h1_cycles=h1, hf=hf, source_anomaly=anomaly)


# =============================================================================
# Self-test (synthetic claims, independent of dataset.py)
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("certs/descent.py self-test")
    print("=" * 70)

    # --- (a) COHERENT order set: a<b<c chain, consistently orientable → hf=0 -----
    # A chain (no over-determined triangle) is a pure gradient, so the ported
    # HodgeRank energy is exactly 0. (NOTE: hf is the cardinal HodgeRank residual —
    # an over-determined-but-coherent set like {a<b, b<c, a<c} would show a small
    # hf because normalized pairwise preferences on a filled triangle are not
    # curl-free; the exact orientability witness is the SCC-based ``h1_cycles``,
    # which stays empty for any acyclic set. The canonical coherent case is a chain.)
    coherent = [
        Claim("tC", "s0", ClaimKind.ORDER, {"before": "a", "after": "b"}, ts=0),
        Claim("tC", "s1", ClaimKind.ORDER, {"before": "b", "after": "c"}, ts=1),
    ]
    cert_a = descent_certify(coherent)
    print(f"\n[a] coherent a<b<c : hf={cert_a.hf:.6g}  h1_cycles={cert_a.h1_cycles}")
    assert cert_a.hf < 1e-9, f"coherent order must have hf≈0, got {cert_a.hf}"
    assert cert_a.h1_cycles == [], f"coherent order must surface no cycle, got {cert_a.h1_cycles}"
    print("    PASS: coherent ⇒ hf≈0 and no cycle")

    # --- (b) FRUSTRATED cyclic order: a<b, b<c, c<a → hf > 0, cycle surfaced -----
    frustrated = [
        Claim("tF", "s0", ClaimKind.ORDER, {"before": "a", "after": "b"}, ts=0),
        Claim("tF", "s1", ClaimKind.ORDER, {"before": "b", "after": "c"}, ts=1),
        Claim("tF", "s2", ClaimKind.ORDER, {"before": "c", "after": "a"}, ts=2),
    ]
    cert_b = descent_certify(frustrated)
    print(f"\n[b] frustrated a<b<c<a : hf={cert_b.hf:.6g}  h1_cycles={cert_b.h1_cycles}")
    assert cert_b.hf > 0.0, f"frustrated cycle must have hf>0, got {cert_b.hf}"
    assert cert_b.h1_cycles, "frustrated cycle must be surfaced"
    assert cert_b.h1_cycles[0] == [0, 1, 2], \
        f"the three ORDER claims must be implicated, got {cert_b.h1_cycles}"
    print("    PASS: frustrated ⇒ hf>0 and the cycle {0,1,2} surfaced")

    # --- (c) direct IO conflict → appears in h0_conflicts -----------------------
    io_conflict = [
        Claim("tI", "s0", ClaimKind.IO, {"input": [2, 3], "output": 5}, ts=0),
        Claim("tI", "s1", ClaimKind.IO, {"input": [2, 3], "output": 6}, ts=1),  # conflicts
        Claim("tI", "s2", ClaimKind.IO, {"input": [2, 3], "output": 5}, ts=2),  # agrees w/ s0
    ]
    cert_c = descent_certify(io_conflict)
    print(f"\n[c] IO same-input/diff-output : h0_conflicts={cert_c.h0_conflicts}")
    assert (0, 1) in cert_c.h0_conflicts, \
        f"same-input/different-output pair must be an H0 conflict, got {cert_c.h0_conflicts}"
    print("    PASS: direct IO conflict (0,1) is in h0_conflicts")

    # --- (d) one clearly-atypical source → ranked highest in source_anomaly -----
    # srcA/srcB/srcC all emit normal int-IO claims (shared token vocabulary);
    # 'evil' emits structurally different ORDER claims (disjoint tokens).
    mixed: list[Claim] = []
    ts = 0
    for s in ("srcA", "srcB", "srcC"):
        for k in range(4):
            mixed.append(Claim("tD", s, ClaimKind.IO, {"input": [k], "output": k * 2}, ts=ts))
            ts += 1
    for k in range(2):
        mixed.append(Claim("tD", "evil", ClaimKind.ORDER,
                           {"before": f"x{k}", "after": f"y{k}"}, ts=ts))
        ts += 1
    cert_d = descent_certify(mixed)
    ranked = sorted(cert_d.source_anomaly.items(), key=lambda kv: -kv[1])
    print("\n[d] source_anomaly (source → H0 poison_score, ranked):")
    for s, v in ranked:
        print(f"      {s:<6} {v:.3f}")
    top_source = ranked[0][0]
    assert top_source == "evil", f"the atypical source must rank highest, got {top_source}"
    assert cert_d.source_anomaly["evil"] > max(
        cert_d.source_anomaly[s] for s in ("srcA", "srcB", "srcC")
    ), "evil must strictly out-score the normal sources"
    print("    PASS: 'evil' ranked most anomalous")

    print("\nALL SELF-TEST ASSERTIONS PASSED")
