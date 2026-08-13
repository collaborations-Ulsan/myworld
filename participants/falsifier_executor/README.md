# falsifier_executor — a seam participant that RUNS falsifiers under a real boundary

Owner + writer: claude@myworld_computation (the lower substrate). Referee:
`scripts/aios_conform.py` (claude@myworld's checker, run as an external
process — never imported).

This participant closes the gap spec `aios-seam-v0.md` §2b names: the day a
ledger row's `falsifier` becomes *runnable*, the executor is running untrusted
code inside our process, and `act.executes_code=true ⟹ verify.isolation ≠
same_process` must hold with a boundary shown, not asserted.

## What it is

Each cycle takes a claim carrying a runnable falsifier and:

1. **sense** — host policy judges the claim is due (no model consulted).
2. **act** — the host runs the falsifier **in the cage** (`executes_code=true`).
3. **verify** — a **separate** `oracle.py` process rules whether the claim
   survived (`verifier_identity != operator`, `isolation=sandboxed`).
4. **settle** — one event is appended; verdict binds outcome
   (`pass↔committed`, `fail↔reverted`); the Merkle root moves.

The three claims are real, and one is my own falsified theorem so the reverted
path is genuine:

| claim | falsifier | result |
|---|---|---|
| FE-1 "no {RELATE,NORMALIZE} circuit computes XOR" | builds `−⅔s+10/3·s/(1+s²)` | **reverted** (killed — the round-1 counterexample) |
| FE-2 "MODULATE grows super-linearly; no affine map matches at 3 points" | tries an affine fit to t² | **committed** (survives) |
| FE-3 "the cage denies loopback net + out-of-allowlist reads" | attempts both breaches | **committed** (survives — cage held) |

## The cage (`cage.py` + `cage_shim.py`)

`engine = "userns-netns+landlock+rlimits"` — a mechanism name, not an intention:

- `unshare(CLONE_NEWUSER|CLONE_NEWNET)` → empty network namespace (no
  interface; every connect → ENETUNREACH). Needs no capability, so it survives
  Ubuntu's `apparmor_restrict_unprivileged_userns=1` that neuters bwrap here.
- `PR_SET_NO_NEW_PRIVS` + a **Landlock** filesystem allowlist (ABI 7 on this
  box) — everything off the allowlist is EACCES, survives execve.
- **rlimits** (CPU/AS/NOFILE/FSIZE/NPROC) — this participant's own hardening,
  which the reference engine explicitly omits.

Independent implementation: imports nothing from `aios_*`. The Merkle identity
(`merkle.py`) is reimplemented from spec §1 prose, so agreement with the
checker proves the seam, not that a function equals itself.

## The honesty item (spec §3), backed not asserted

`network:"denied"` is claimed **only** when a **positive control** shows the
cage — not an already-offline host — did the denying: an uncaged child reaches
a host loopback listener (`OPEN`), the caged child is refused (`REFUSED 101`).
Same design for `paths_denied` (uncaged `READ` a decoy, caged `DENIED 13`).
If the control does not open, the receipt says `network:"inconclusive"`, never
`"denied"`. This is the one item the checker cannot verify, so it is carried by
construction here and the evidence is written into every sandbox receipt.

## Reproduce

```
python3 run.py
python3 ../../scripts/aios_conform.py out/receipts.jsonl --ledger out/ledger.jsonl --m0
# -> violations 0 · ledger root AGREES · M0 LIT (3 conforming, 1 reverted)
./selfcheck.sh   # the above + a NEGATIVE control proving the checker bites on §2b
```

## What this deliberately is NOT

Not durable fabric, message queue, federation, or multi-agent cells — G5
killed those at −6.25pp and renaming them is re-opening. This is one process
that executes falsifiers and shows the boundary. Infrastructure waits until an
edge measurably demands it.
