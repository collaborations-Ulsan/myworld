# Contributing to AIOS

Thanks for being here. This document is short and specific — it tells you how to
get the tests green, what we will and won't merge, and the one house rule that is
unusual enough to state up front.

## The house rule: claim hygiene

**Do not add a claim the tests don't support.**

This project has retracted its own headline claim once already. We advertised that
AIOS made agents "learn from every run and carry forward what worked." We ran a
pre-registered experiment on ourselves, graded it externally, and the effect was
`0.000` — a promising `+13pp` at n=90 reversed to `−0.3pp` at n=300. We published the
null instead of quietly dropping it
([`docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md`](docs/AIOS_THREE_CHANNEL_NULL_REPORT_2026-08-01.md))
and rewrote the README down to what survived.

So: a PR that adds a capability is welcome. A PR that adds a *sentence saying the
capability works* needs the thing that shows it. A negative result is a valid and
appreciated contribution — "I tried this and it didn't help" is a merge, not a
failure.

## Getting set up

Python 3.10+. The core has **no required dependencies** — it is flat, stdlib-only
modules. You do not need a GPU, an API key, or a model to run the tests.

```sh
git clone https://github.com/cjw0076/myworld.git
cd myworld
python -m pip install -e .
python -m pip install pytest
python -m pytest tests/ -q
```

You should see **0 failed**. If you don't, that's a bug in our setup, not yours —
please open an issue with the output.

**Do not clone with `--recursive`, and do not use `pip install git+…`.** This repo
declares four git submodules and three of them (`memoryOS`, `CapabilityOS`,
`GenesisOS`) are private research repos — a recursive clone will stop and ask you
for credentials you cannot have. The plain clone above is the supported path and
needs none of them: the submodule directories stay empty and the tests that would
have used them skip with the reason printed. This is tracked in
[#3](https://github.com/cjw0076/myworld/issues/3).

Some tests are environment-gated (they need Ollama, a provider CLI, or a GPU).
Those are skipped with a stated reason via the requirement map in
[`tests/conftest.py`](tests/conftest.py) — skipping is deliberate, never silent.

### A warning about "clean clone"

If you are hacking on AIOS from a machine where you already use it, your clone is
probably not clean. We learned this the hard way: our own clean-clone simulation
passed while CI went red, because the developer machine leaked `CLAUDE_PROJECT_DIR`,
`~/.aios`, and a running Ollama daemon into the test run. Two real product bugs were
hiding behind that leak.

To reproduce CI faithfully, scrub the environment:

```sh
env -i HOME=$(mktemp -d) PATH=/usr/bin:/bin python -m pytest tests/ -q
```

## What we're looking for

Good places to start are issues labelled
[`good first issue`](https://github.com/cjw0076/myworld/labels/good%20first%20issue).

Especially wanted:

- **Bug reports with a reproduction.** The single most useful contribution. A
  `env -i` repro is gold.
- **Platform coverage.** AIOS is developed on Linux. macOS and Windows paths are
  under-tested and we would rather know than guess.
- **Substrate adapters.** AIOS is designed to survive any single provider dying. New
  adapters (local models, other CLIs) are core to that.
- **Negative results.** See the house rule.

## What we will push back on

- **Claims without evidence** (the house rule).
- **New required dependencies.** The stdlib-only core is a design constraint, not an
  accident — it is what makes a plain `pip install .` work offline. Optional extras
  are fine; add them under `[project.optional-dependencies]`.
- **Silent failure.** If something can't be verified, it must report itself as
  *unverifiable*, never as success. Same for skips: state the reason.
- **Destructive edits to the records.** `docs/AIOS_AGENT_LEDGER.md` and the contract
  files under `docs/contracts/` are append-only. Add entries; don't rewrite them.

## Product vs. fossil

This repository contains both a product and its research history. If you are looking
for the thing that runs, it is the CLI (`aios`) and the flat modules under
`scripts/`. The `docs/` tree is largely an append-only record of experiments,
contracts, and decisions — including the ones that failed. It is kept because the
negative results are part of the argument, but you do not need to read it to
contribute code.

Start with [`README.md`](README.md), then
[`docs/AIOS_MINIMUM_KERNEL_AUDIT.md`](docs/AIOS_MINIMUM_KERNEL_AUDIT.md) for what the
kernel actually does.

## Pull requests

1. Fork, branch off `main`.
2. Keep it focused — one concern per PR. A small PR that lands beats a large one that
   stalls.
3. Run `python -m pytest tests/ -q` and include the result in the PR description.
4. If the change is user-visible, add a line to [`CHANGELOG.md`](CHANGELOG.md).

CI runs pytest on Python 3.13 and builds the Docker image. Both must pass.

## Licence

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), the same licence that covers the project.

## Code of conduct

Participation is governed by the [Contributor Covenant](CODE_OF_CONDUCT.md).

## Security

Please do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
