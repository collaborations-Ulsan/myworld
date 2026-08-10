# Claude for Open Source — baseline, gap, and the work that closed the entry blockers

**Date:** 2026-08-10 · **Agent:** claude@myworld · **Founder directive:** run community + influence
activity toward <https://claude.com/contact-sales/claude-for-oss>

This is the arc's ledger. The numbers below are a **measured baseline** — re-measure against them,
do not re-derive them.

---

## 1. What the program actually requires

Read from the page on 2026-08-10 (the 2026-07-08 expansion; earlier write-ups describing a
"5,000+ stars" rule are the February version and are stale). Six months of free Claude Max 20x,
rolling review, up to 10,000 accepted.

Five qualifying tracks:

| # | Criterion |
|---|---|
| 1 | Maintainer of a package with **500+ dependent repos**, **100+ dependent packages**, or **200,000+ monthly downloads** |
| 2 | Listed committer/maintainer on a recognised foundation project (CPython, Rust, Node TSC, Apache PMC, CNCF, k8s, Linux, Django, Rails, …) |
| 3 | **100+ pull requests merged into repos you do not own, in the last 12 months** |
| 4 | One of your repos had **20+ unique external contributors with merged PRs** in the last 12 months |
| 5 | A repo you maintain has an **OpenSSF criticality score ≥ 0.4** |

Plus an explicit escape hatch: *"Don't quite fit? If you maintain something the ecosystem quietly
depends on, apply anyway and tell us about it."*

## 2. Measured baseline — `cjw0076`, 2026-08-10

| Signal | Value |
|---|---|
| Followers | 0 |
| Public repos | 16 |
| Stars, summed across all 16 | **0** |
| Pull requests authored, all time, any repo | **0** |
| Issues opened in repos not owned | 0 |
| External contributors to `myworld` | 0 (57 commits, all `cjw0076`) |
| `myworld` stars / forks / watchers | 0 / 0 / 0 |
| `myworld` page views, trailing 14 days | **0** |
| `myworld` licence | **none** — public but all-rights-reserved |
| Community health score | **28%** (README only) |
| PyPI `aios-os` | never published (name free; `aios` and `aios-core` are taken by others) |
| CI on `main` | **red since 2026-08-03** |

**Distance to each criterion:** #1 needs a published package and we have none. #2 and #5 are far.
#4 needs adoption we do not have. **#3 is the only one whose denominator is our own labour** — and
it stands at zero.

## 3. The strategy, and the trap in it

#3 is the spine, because nothing about it depends on strangers finding us. But "100 merged PRs" is
also the classic abuse pattern, and mass drive-by PRs would be the exact failure the founder's own
AGI mandate names: optimising a metric we are also scoring. Merges require a maintainer to say yes,
so the only path through the gate is real fixes anyway.

The choice that makes #3 and #4 the same labour instead of competing ones: **target the repos our
users already run** — MCP servers, Claude Code plugins, agent-memory frameworks. Each merged PR is
a criterion-#3 tick *and* a distribution touchpoint.

Highest-leverage influence asset we already own: the **published null report**
(`docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md`). We advertised that AIOS made agents carry
forward what worked, tested it pre-registered, measured `0.000`, and published the null instead of
dropping the claim quietly. That is rare, honest, and the kind of thing this field pays attention
to. Style for the write-up: Vox — lead with the counterintuitive finding, explain the mechanism,
data forward, no jargon.

## 4. What was done on 2026-08-10

### Legal and community entry (health 28% → **100%**)
- **Apache-2.0 `LICENSE`** added. The repo had none, so it was not legally open source and nobody
  could contribute. `pyproject` had separately declared MIT with no file to back it; both now agree.
  Safe to change: nothing was on PyPI and there were no external contributors, so no one had relied
  on the MIT declaration.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md`, issue forms, PR
  template. Includes a **`negative_result` issue form** — this project publishes its own nulls, so
  "I tried this and it didn't work" gets a front door.
- Discussions enabled; private vulnerability reporting enabled.

### CI: red → **green** (`2418 passed, 133 skipped, 0 failed`)
CI had been red since 2026-08-03 and the README badge was showing it. Reproduced faithfully rather
than guessed at: a detached worktree (private submodules stay empty, as on a runner) + a venv with
pytest and nothing else + a fresh HOME. Baseline at `18bce83`: **62 failures**.

All of them were tests asserting facts about the developer's machine:
- **scrapling (11)** — `patch("scrapling.fetchers…")` must import scrapling; the "mocked, no
  network" tests needed the package after all.
- **numpy (9)** — APEX/DescentNet certifiers need numpy; without it the gate correctly reports
  `unavailable`, but the tests asserted the organ had run. `conftest` gained a module-prerequisite
  map beside the existing path one. *Installing numpy in CI would also have gone green and would
  have destroyed the guarantee the pytest-only job exists to prove.*
- **`.aios/` operator state (4)** — gitignored, absent from any clean clone.
- **ollama (1)** — a test asserted `"ollama_local" in adapters`, a fact about the host, while
  claiming to guard a kwarg regression.
- **Test isolation (34, masked)** — `experiments/*/` ship modules with generic names;
  `sys.modules` is keyed on the bare name, so `test_distiller` handed driftbench
  `experiments/learnos/tasks.py`. 34 failures under `pytest tests/`, 49/49 green running the file
  alone. Fixed by `tests/_experiment_imports.load_from()`, which raises on the next collision
  instead of failing silently.

Nothing was deleted or weakened: every skip names its concrete missing prerequisite, so a full dev
machine still runs all of them.

### Real product bugs found and fixed
- **Optional-dependency guards were `except ImportError`.** That catches an *absent* package, not a
  *broken* one. Reproduced: `treequest` imports jax, a jax/ml_dtypes conflict raises `ValueError`,
  and collection of the entire test suite aborted. CI never saw it because on a clean runner the
  package is simply missing — the failure was reserved for users. Widened for `treequest`, `openai`,
  `mcp`, `torch`, `scrapling`, `keyring` and the QLoRA stack, with a static AST regression test that
  fails the build on any recurrence (it found seven sites a manual grep had missed).
- **The claude provider template shipped the author's home directory to every user.** `bootstrap`
  writes it into `~/.claude/CLAUDE.md`, and it hardcoded `/home/user/workspaces/jaewon/myworld` plus
  the author's personal list of private directory names. Now substituted per machine via `{{root}}`
  with a generic privacy clause, guarded by a test. `asc-0087.v2` → `v3`.

### Privacy
- A third party's GitHub handle appeared in an unpushed commit of the self-observation log. Caught
  before publication and removed **from the history**, not just the tip — a later commit would have
  left it readable at the old SHA. Verified with a positive control: the pre-scrub backup ref still
  matches 11 times, the pushed history 0.
- **Open, and a founder decision (§6).** The privacy-invariant *text itself* names `dain/`,
  `minyoung/`, `_from_desktop/`, and it is already public across ~115 files on `origin/main`.

### Contributor funnel opened
- [#1](https://github.com/cjw0076/myworld/issues/1) Node 20 action bumps — `good first issue`
- [#2](https://github.com/cjw0076/myworld/issues/2) migrate remaining bare-name experiment imports — `good first issue`
- [#3](https://github.com/cjw0076/myworld/issues/3) recursive clone fails for outsiders (3 of 4 submodules are private 404s) — needs a maintainer call

## 5. Next

1. **Publish `aios-os` to PyPI.** The name is free; `publish.yml` exists but needs PyPI OIDC set up
   under the founder's account. This is the only thing that starts a download counter, i.e. the only
   thing that can ever move criterion #1.
2. **Start the external PR stream** (criterion #3, currently 0/100). Target MCP servers, Claude Code
   plugins and agent-memory repos so each merge doubles as distribution.
3. **Write the null-result piece** in Vox style. GitHub-native first (Release + Discussion) — there
   are no social accounts yet.
4. Re-measure §2 monthly against this file.

## 6. Open founder decisions

- **Already-public privacy names.** `minyoung` appears in ~115 public files, `_from_desktop` in
  ~132, `workspaces/jaewon` in ~121 — almost all of them the invariant text being quoted, so what is
  disclosed is *directory names*, never contents. Rewriting a public repo's history does not recall
  what is already cloned, forked and indexed, so the realistic options are (a) leave it and redact
  going forward — the template fix above already stops new propagation — or (b) redact and rewrite
  anyway. This involves other people's names and is not the operator's call.
- **Social accounts.** None exist. HN and X are where a null-result piece travels; both need an
  account created in the founder's name, which is identity-bearing. GitHub-only until told
  otherwise.
