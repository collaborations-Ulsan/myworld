# AIOS form factor — daemon? IDE? CLI? (decision, 2026-07-22)

Founder asked: should AIOS be a native app running a **daemon**? Like an **IDE**? How should it behave
in the **CLI**? Grounded against the 2026 landscape (OpenAGI = always-on local daemon that reaches out
proactively; Ollama = daemon; MCP = the dominant agent↔tool standard; "the center of agent architecture
is shifting from prompt loops to managed execution").

## Decision: **one daemon (the living organism), many thin clients.**

Not AIOS-as-IDE. Not CLI-only. **`aiosd` (a local daemon) IS the organism's body; the CLI, MCP, and any
future GUI/IDE panel are thin CLIENTS onto it.**

### Why a daemon — it is the body the assembled organism needs
The organism we just assembled wants to LIVE in a persistent process, not be re-instantiated per CLI call:
- **Continuous self ("느낄 수 있는 살아있음")** requires persistence. The Experience Graph (Phase 3) + Skill
  Registry (Phase 4) are file-backed today; a daemon holds them LIVE — the thread of experience doesn't die
  between commands.
- **Ambient life ("깊은 고찰")**: reflection, the radar (ecosystem absorption), memory consolidation ("sleep")
  run on a background tick — an organism doesn't only act when prompted (OpenAGI's proactive shape).
- **The enforced boundary (Phase 1) + self-verification (Phase 2)** become always-on properties of a running
  process, not per-invocation setup.
- **Peer coordination**: the A2A endpoint (Sovereign Coordination Stack) is served BY the daemon — how one
  person's AIOS reaches another's.
- **"AIOS as base" (provider-independence directive)**: the daemon is the sovereign spine; provider CLIs and
  models are tools it WIELDS and can swap/lose. The daemon outlives any provider.

### IDE — NO as the core, YES as a client
Do not build AIOS *as* an IDE (that couples the organism to one GUI + one workflow). Build the daemon and
let an editor/IDE be ONE client **via MCP** — which we already have (`aios_mcp_server`); Claude Code IS the
IDE-like client today. MCP is the 2026 standard, so any IDE/editor/agent connects to the same organism. The
IDE is a *view onto* the organism, never the organism.

### CLI — a thin client to the daemon, standalone fallback
Mirror `docker`→dockerd / `ollama` CLI→ollama daemon:
- `aios <goal>` / `aios ask` — if `aiosd` is up, connect to it (fast; shares the LIVE self, experience,
  skills, running organs); if not, run standalone in-process (today's `aios --loop`, ephemeral).
- `aios daemon start|stop|status` · `aios experience query …` · `aios skills …` · `aios peer …` — all thin
  clients over a local UNIX-socket IPC to the daemon.
- The CLI is one mouth of the organism, not the organism. Scriptable, pipe-friendly, no GUI dependency.

## The shape in one line
**AIOS = one local daemon (continuous self + organs + ambient loop + peer endpoint + enforced boundary),
exposed through MCP (for IDEs/agents) and a thin CLI (for humans/scripts); models and provider CLIs are
ephemeral tools the daemon wields.** This matches the organism vision (persistent living body),
provider-independence (daemon = base), the Coordination Stack (daemon serves A2A), the compounding reframe
(the OS is the substrate, models are clients), and the 2026 local-first landscape (daemon + MCP).

## Honest current state → next step
We have: the CLI head (`aios --loop`), the MCP sidecar (`aios_mcp_server`), and file-backed experience/skills.
We do NOT have the daemon. It is the natural next organism step — **Phase 6: give the organism a body**
(`aiosd`): a persistent process holding the Experience Graph + Skill Registry + the enforced turn-loop, an
ambient tick (reflection/radar/consolidation), a UNIX-socket IPC, and the CLI re-pointed as a thin client
(standalone fallback preserved). Phase 5 (the learning-measurement experiment) runs AGAINST the daemon.

Guard (anti-theater): "always-on" must earn its keep by BEHAVIOR — the daemon's ambient ticks must produce
real, logged, verifiable effects (a caught drift, an absorbed skill, a consolidated memory), never a
process that merely idles and looks alive. Related: [[project_organism_not_toolbox_vision]],
[[project_provider_independence_two_horizons]], [[project_aios_invocation_gated_not_ambient]],
`docs/AIOS_STATE_AND_ORGANISM_SYNTHESIS_2026-07-22.md`, `docs/AIOS_ORGANISM_ASSEMBLY_PLAN_2026-07-22.md`.
