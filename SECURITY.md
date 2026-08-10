# Security Policy

## Reporting a vulnerability

**Please do not open a public issue.**

Use GitHub's private vulnerability reporting:
[**Report a vulnerability**](https://github.com/cjw0076/myworld/security/advisories/new).

If that is unavailable to you, email **cjw070690@gmail.com** with `AIOS SECURITY` in
the subject.

Please include: what you did, what happened, what you expected, and the smallest
reproduction you can manage. If you have a patch, hold it until we have agreed on
disclosure timing.

**Response targets:** acknowledgement within 72 hours, an initial assessment within
7 days, and a fix or a stated reason for no fix within 90 days. This is a small
project — if a deadline slips you will hear why, not silence.

You will be credited in the advisory and the changelog unless you ask not to be.

## Supported versions

AIOS is pre-1.0 and moves fast. Only the latest release on `main` receives security
fixes.

## What we consider in scope

AIOS executes code and coordinates external agents on your machine, so its security
surface is mostly about **containment** and **integrity of the record**:

- **Sandbox escape.** Executed code reaching the network when the sandbox is
  configured with no network, or reading directories that are supposed to be
  invisible to it.
- **Privacy-boundary leaks.** Any path by which private local content ends up in a
  prompt, a dispatched packet, a log, or an outbound call. Putting something in a
  prompt counts as sending it.
- **Ledger tampering.** The work ledger is tamper-*evident*; a way to mutate history
  without detection, or to forge a Merkle proof, is a vulnerability.
- **Handoff forgery.** Claiming or resuming an arc you do not hold the lease for, or
  passing verification without having done the work.
- **Authority bypass.** Getting an action executed without the gate that should have
  approved it, or escalating an outsider identity into the authority cast.
- **Credential exposure.** Provider keys or session material written anywhere they
  can be read by executed code or committed to git.

## What is out of scope

- Findings that require the attacker to already have your shell.
- Vulnerabilities in third-party providers, model APIs, or CLIs that AIOS calls —
  report those upstream. If AIOS *amplifies* such a flaw, that part is in scope.
- Missing hardening that has no demonstrated impact. We would still like to hear
  about it; open a normal issue.
- Anything in the `docs/` research record. It is an append-only history, not running
  code.

## A note on what this project claims

AIOS's containment is OS-enforced (sandboxing, no network by default, private
directories hidden from executed code) and is tested, but it has not had an external
security audit. Treat it as defence in depth, not as a boundary you would bet a
secret on. If you find that the enforcement is weaker than the README implies, that
gap between claim and reality is itself a report we want.
