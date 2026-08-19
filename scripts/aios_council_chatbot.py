#!/usr/bin/env python3
"""AIOS Council Chatbot & Ideation Studio (aios.council_chatbot.v1).

Interactive Council Chatbot for multi-model Ideation, Cross-Critique, and
Autonomous Graph Workflow Compilation.

Features:
- Real-time brainstorming with OpenSource Model Council (Qwen, DeepSeek NIM, Llama)
- Direct conversion from Council Ideation -> Evolutionary Execution Graph
- Seamless integration with Cross-Session Message Bus & Society Registry
- Slash commands: /ideate, /debate, /compile, /run, /bus, /status, /help
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]

try:
    from aios_hetero_council import HeteroCouncil
    from aios_evolutionary_graph import DynamicGraphEngine, create_default_genome, EvolutionaryOptimizer
    from aios_cross_session_bus import CrossSessionBus
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from aios_hetero_council import HeteroCouncil
    from aios_evolutionary_graph import DynamicGraphEngine, create_default_genome, EvolutionaryOptimizer
    from aios_cross_session_bus import CrossSessionBus


class CouncilChatbot:
    """Interactive Multi-Model Council Ideation Chatbot."""

    def __init__(self, agent_id: str = "operator-console"):
        self.agent_id = agent_id
        self.council = HeteroCouncil()
        self.bus = CrossSessionBus()
        self.last_deliberation: Optional[Dict[str, Any]] = None
        self.current_genome = create_default_genome()

        # Register self to bus
        self.bus.register_agent(
            agent_id=self.agent_id,
            capabilities=["role.operator", "role.orchestrator"],
            model_family="human-ai-hybrid",
            substrate_type="cli",
        )

    def print_banner(self):
        print("=" * 75)
        print("🏛️  AIOS HETEROGENEOUS COUNCIL & EVOLUTIONARY AGENT CHATBOT")
        print("   Substrates: Local Qwen Coder + NVIDIA NIM DeepSeek / Llama")
        print("   Commands: /ideate, /debate, /compile, /run, /bus, /inbox, /status, /exit")
        print("=" * 75)

    def handle_ideate(self, topic: str):
        print(f"\n💡 [Council Ideation] Querying heterogeneous panel on: '{topic}'...")
        res = self.council.ideate(topic)
        self.last_deliberation = {"topic": topic, "ideation": res}

        print(f"📊 Effective Independent Voices ($N_{{eff}}$): {res['n_eff']}")
        for prop in res.get("proposals", []):
            sub_id = prop.get("substrate_id")
            model = prop.get("model")
            provider = prop.get("provider")
            print(f"\n--- 🧠 Proposal from [{sub_id}] ({model} via {provider}) ---")
            print(prop.get("text", "").strip())
        print("\n💡 Tip: Type `/debate` to run adversarial cross-critique on these proposals.")

    def handle_debate(self, topic: Optional[str] = None):
        if not self.last_deliberation or "ideation" not in self.last_deliberation:
            print("⚠️ No previous ideation found. Running ideation first...")
            self.handle_ideate(topic or "General System Evolution")

        top = topic or self.last_deliberation["topic"]
        proposals = self.last_deliberation["ideation"].get("proposals", [])
        print(f"\n⚔️ [Council Debate] Starting adversarial peer review for: '{top}'...")

        debate_res = self.council.debate(top, proposals)
        self.last_deliberation["debate"] = debate_res

        for crit in debate_res.get("critiques", []):
            sub_id = crit.get("substrate_id")
            print(f"\n--- 🔍 Critique from [{sub_id}] ---")
            print(crit.get("text", "").strip())

        print("\n⚖️ Synthesizing unified consensus...")
        cons_res = self.council.synthesize_consensus(top, self.last_deliberation["ideation"], debate_res)
        self.last_deliberation["consensus"] = cons_res

        print("\n📜 [UNIFIED CONSENSUS SPEC]")
        print(cons_res.get("consensus_text", "").strip())
        print("\n💡 Tip: Type `/compile` to turn this consensus into an executable Agent Graph!")

    def handle_compile(self):
        if not self.last_deliberation or "consensus" not in self.last_deliberation:
            print("⚠️ No consensus available to compile. Run `/ideate` and `/debate` first.")
            return

        cons_text = self.last_deliberation["consensus"].get("consensus_text", "")
        topic = self.last_deliberation["topic"]
        print(f"\n⚙️ [Compiling Consensus to Agent Genome] for: '{topic}'")

        # Inject synthesized consensus guidelines into Genome prompt DNA
        genome = create_default_genome(f"compiled-{int(time.time())}")
        genome.prompt_dna["architect"] += f"\n[Council Directive for {topic}]:\n{cons_text[:400]}"
        genome.prompt_dna["coder"] += f"\n[Council Implementation Invariants]:\nFollow consensus specs strictly."
        self.current_genome = genome

        print(f"✅ Generated Genome [{genome.id}] with Council Invariants.")
        print(f"   Active Substrates: {json.dumps(genome.substrate_map, indent=2)}")
        print("💡 Tip: Type `/run <task>` to execute the dynamic graph loop with this genome.")

    def handle_run(self, task: str):
        print(f"\n🚀 [Executing Dynamic Agent Graph Loop] Goal: '{task}'")
        engine = DynamicGraphEngine(self.current_genome)
        state = engine.run(task)

        print(f"\n🏁 Graph Finished: Steps={state.step_count}, Passed={state.oracle_passed}")
        print("Execution Trail:")
        for h in state.history:
            print(f"  [{h['step']}] Node: {h['node']} -> {h['output']}")

        # Save record to society event bus
        self.bus.send_message(
            sender_id=self.agent_id,
            recipient_id="broadcast",
            content=f"Completed graph execution for '{task}': Oracle Passed={state.oracle_passed}",
            kind="receipt",
        )

    def handle_bus_send(self, target: str, message: str):
        msg = self.bus.send_message(sender_id=self.agent_id, recipient_id=target, content=message)
        print(f"📬 Message sent to [{target}] (ID: {msg.id}, Corr: {msg.correlation_id})")

    def handle_inbox(self):
        msgs = self.bus.receive_messages(self.agent_id)
        print(f"\n📥 Inbox for [{self.agent_id}] ({len(msgs)} total):")
        for m in msgs[-5:]:
            print(f"  - From [{m.sender_id}] ({m.kind}): {m.content}")

    def interactive_loop(self):
        self.print_banner()
        while True:
            try:
                user_input = input("\nAIOS Council> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Exiting AIOS Council.")
                break

            if not user_input:
                continue

            if user_input.startswith("/exit") or user_input.startswith("/quit"):
                print("👋 Session ended.")
                break

            elif user_input.startswith("/ideate"):
                topic = user_input[len("/ideate"):].strip() or "Autonomous Agent Graph Evolution"
                self.handle_ideate(topic)

            elif user_input.startswith("/debate"):
                topic = user_input[len("/debate"):].strip() or None
                self.handle_debate(topic)

            elif user_input.startswith("/compile"):
                self.handle_compile()

            elif user_input.startswith("/run"):
                task = user_input[len("/run"):].strip()
                if not task:
                    print("⚠️ Usage: /run <task description>")
                else:
                    self.handle_run(task)

            elif user_input.startswith("/bus"):
                parts = user_input[len("/bus"):].strip().split(" ", 1)
                if len(parts) < 2:
                    print("⚠️ Usage: /bus <recipient_id|broadcast> <message>")
                else:
                    self.handle_bus_send(parts[0], parts[1])

            elif user_input.startswith("/inbox"):
                self.handle_inbox()

            elif user_input.startswith("/status"):
                print(f"Agent ID: {self.agent_id}")
                print(f"Registered Agents: {len(self.bus.registry)}")
                print(f"Substrates: {[s['id'] for s in self.council.substrates]}")
                print(f"Current Genome: {self.current_genome.id}")

            elif user_input.startswith("/help"):
                print("Commands:")
                print("  /ideate <topic>   - Deliberate with Qwen, DeepSeek, and Llama on a concept")
                print("  /debate [topic]   - Run adversarial critique and consensus synthesis")
                print("  /compile          - Compile consensus into an executable Agent Genome")
                print("  /run <task>       - Execute dynamic graph loop for a task")
                print("  /bus <to> <msg>   - Send cross-session dispatch to another agent session")
                print("  /inbox            - Read incoming messages from society bus")
                print("  /status           - Show system and substrate status")
                print("  /exit             - Exit chatbot")

            else:
                # Default behavior: run ideation on the prompt
                self.handle_ideate(user_input)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", help="Run one-shot council deliberation on topic")
    parser.add_argument("--interactive", action="store_true", default=True, help="Run interactive console")
    args = parser.parse_args(argv)

    bot = CouncilChatbot()
    if args.topic:
        bot.handle_ideate(args.topic)
        bot.handle_debate(args.topic)
        bot.handle_compile()
    else:
        bot.interactive_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
