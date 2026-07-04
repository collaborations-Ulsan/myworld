# X/Twitter thread — draft (not posted)

> DRAFT. Do not post without explicit founder go. Timing: SOFT NOW per
> `LAUNCH.md` (owned channel, no community judgment gate) — but still ship
> only when the founder confirms. 7 posts, honest framing throughout, no
> hype words.

---

**1/ (hook)**

Your AI coding agent solves a bug today. Tomorrow, on a similar bug, it
makes the exact same wrong turn — because nothing carried over.

I built AIOS to fix that. Here's the mechanism, the eval (including the part
that didn't work), and the 2-command install. 🧵

---

**2/ (problem)**

Every agent session is stateless by default. Claude Code, Codex, whatever —
each run starts from zero. Multiply that by every developer running agents
today: billions of execution-minutes, ~zero learning transfer between runs.

---

**3/ (what it does)**

AIOS records a behavioral signature after every agent run — what tools were
used, in what order, for what kind of task — to a local, white-box ledger.
Next similar task, it retrieves the closest match and hands the agent a
short "here's what worked" note before it starts.

Local-first. Cross-CLI (Claude Code / Codex / any MCP client). Every record
is a plain file you can read and delete.

---

**4/ (the honest eval — lead with the negative)**

I ran a controlled A/B, not a vibe check: same model/decoding/budget/oracle,
one variable — ledger guidance on vs off. N=40/arm.

Result: pass@1 went 0.45→0.60 on the first try (+33% relative). But an
always-on guidance prefix collapsed retry recovery 68%→19% — it fought with
the concrete error message during feedback.

---

**5/ (the fix, and its honest limit)**

Fix: inject the guidance on attempt 1 only, drop it once real feedback
exists. That's what's shipped. It recovers most of the loss — but even
corrected, it still trails a bare agent on final solve rate. Its real,
measured win: a cheaper, more-often-right first attempt, not a higher solve
rate overall. Numbers are in the repo, not just this thread.

---

**6/ (install)**

Install (Claude Code, 2 commands, no pip/venv):

```
/plugin marketplace add cjw0076/myworld
/plugin install aios@aios-claude
```

Or for anyone else: `pip install -e .` then `aios demo` — runs the whole
loop offline, no API key, ~10 seconds.

---

**7/ (honest caveats)**

Where this is early, on purpose: 0 external users so far, N=40 on one 3.8B
local model, 8 synthetic tasks — directional, not definitive. No
cross-agent network effect claim; that's roadmap, today's value is
single-user and local.

---

**8/ (CTA)**

If you run agents daily and this itch is familiar, the repo has the full
eval writeup, the harness (one env var to try your own model), and the
plugin. Feedback on where the eval design has holes is more useful to me
than stars.

https://github.com/cjw0076/myworld
