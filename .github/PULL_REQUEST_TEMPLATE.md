## What this changes

<!-- One or two sentences. What is different after this merges? -->

## Why

<!-- The problem, or a link to the issue. -->

## Evidence

<!--
The house rule: don't add a claim the tests don't support.
Paste the result of `python -m pytest tests/ -q`, and whatever else shows this works.
If you couldn't verify part of it, say so — "unverified" is an acceptable answer here,
a silent gap is not.
-->

```
$ python -m pytest tests/ -q

```

## Checklist

- [ ] Tests pass locally (`python -m pytest tests/ -q` → 0 failed)
- [ ] No new **required** dependency (optional extras are fine — the core is stdlib-only by design)
- [ ] Nothing added to the README or docs that this PR doesn't actually demonstrate
- [ ] `CHANGELOG.md` updated, if the change is user-visible
- [ ] No private paths, keys, or session material in the diff
- [ ] Append-only records (`docs/AIOS_AGENT_LEDGER.md`, `docs/contracts/`) were added to, not rewritten
