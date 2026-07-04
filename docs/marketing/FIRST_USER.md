# First real external user — the conversion runbook (honest)

Marketing (this dir) is the *reach*. This is the *conversion*: turning one discovered
stranger into AIOS's first **real external user** — and one **unimpeachable** product-domain
memory. Paired, they are the gap-#3 machine (design revalidation's #1 blocker).

## The honest baseline (do not launder this)

- **Verified external users: 0.** No non-founder human has completed a real task with AIOS.
- **Genuine product-domain memory: ≈ 1, not the "4/223" the audit prints.** Of the 4 objects
  the metric counts as product (`scripts/aios_memory_retrieval_audit.py:81-82,194-236`), only
  `mem_0c66b6db9ac73100` truly references an external product (uri files). Two are AIOS-internal
  work **mislabeled** `project=URI` (they reference `myworld/scripts/aios_*`); one is
  `project=aios_execution` (internal work that dodged the internal-set filter by label). The
  metric is a **free `project` string with no notion of who did the work — trivially gameable.**
- **Therefore we do NOT "make 4 → 5" by relabeling anything.** The real 5 must be an external
  task nobody could dispute. (Housekeeping to-do: *supersede* the 2 mislabeled URI objects and
  the `aios_execution` one so the metric tells the truth — append-only correction, DNA #3.)

## What counts as the real first user (kernel-audit pass condition)

`docs/AIOS_MINIMUM_KERNEL_AUDIT.md:176-182` — the task must be:
1. **unrelated to AIOS's own development** (uri calling AIOS is ASC-0208, *not* external),
2. **completed** (started + abandoned ≠ validated),
3. **externally evaluable** (PR merged, their test green, a section adopted), and — decisively —
4. **originated by a human outside our own person-team.** The founder is that team.

⇒ **Founder-on-uri moves the number but is a DOGFOOD, not the external proof.** Label it so.
The true first user = **one outside developer** running the plugin on **their own** repo.

## The path (2 commands → one honest counted memory)

1. **Reach** (marketing): the repo is public, discoverable (memory-led description + 10 topics),
   and the plugin marketplace is live. An outside dev finds it and installs:
   ```
   /plugin marketplace add cjw0076/myworld
   /plugin install aios@aios-claude
   ```
2. **First real value** (their first 5 minutes — a real task, not a demo):
   ```
   aios "<a real failing test / open issue in MY repo>"
   ```
   → head plans (frontier LLM) → routes (CapabilityOS) → executes read-only, then writes with
   patch + receipt + rollback → **their test goes green** (externally evaluable).
3. **The counted memory** — the session's durable decision is proposed as a product memory.
   The `@project` MUST be the external repo/task, **never** `AIOS`/`myworld`/an internal name:
   ```
   # in a .md file:  ```memlang  @project <their-repo-or-task>  !decision [draft] "…"  ```
   python -m memoryos.cli --root memoryOS import --memlang <file>.md
   python -m memoryos.cli --root memoryOS drafts list --status draft --json      # get the id
   python -m memoryos.cli --root memoryOS drafts approve <id> --reviewer <who> --note <why>
   python3 scripts/aios_memory_retrieval_audit.py --json | head            # product 1 → a real 2
   ```
   (Draft-first, DNA #2: explicit review, reviewer a *different pass* than the author. The MCP
   `aios_ingest_cli_session` tool does **not** touch this metric — it feeds the behavioral
   AkashicRecord, a different store; only the memlang draft→approve loop counts.)
4. **Consent** (DNA #7): the user opts into which categories, if any, leave their machine. The
   default is fully local — nothing egresses without an explicit `aios behavior contribute`.

## The `@project` honesty guard (the one rule that keeps this real)

The counted memory must reference the **external** task's files/outcome. If the `project` label
names AIOS/myworld/an internal component, it is internal work and does **not** count — no
exceptions, no relabeling. A gamed 5 is worse than an honest 1.

## What needs the founder vs what is done

- **Done (operator):** discoverability, the 2-command install, the marketing kit, this runbook.
- **Needs a real human (irreducible):** one outside developer actually installs it and finishes
  a real task. Marketing-discovery can supply this *organically* (no hand-off needed) — or the
  founder hands the two commands to one dev / one uri contributor to seed it faster.
- **Optional dogfood (proves the loop mechanically):** founder-on-uri, run + labeled honestly as
  "founder dogfood, not external proof," emitting the exact receipt an outsider would produce.
