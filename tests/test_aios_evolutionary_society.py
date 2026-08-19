#!/usr/bin/env python3
"""Comprehensive Unit and Integration Tests for AIOS Evolutionary Council & Society Loop.

Tests:
1. Heterogeneous Substrate & Council Deliberation (N_eff, fallback, consensus)
2. Dynamic Agent Graph Engine (cyclic loops, state blackboard, oracle gating)
3. Genetic Evolution Engine (mutation, crossover, fitness scoring, hall of fame)
4. Cross-Session Message Bus (correlation IDs, capability routing, convergence)
5. Council Chatbot Integration (ideation -> compilation -> execution)
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from aios_hetero_council import HeteroCouncil, SubstrateClient
from aios_evolutionary_graph import (
    AgentGenome,
    DynamicGraphEngine,
    EvolutionaryOptimizer,
    GraphState,
    create_default_genome,
)
from aios_cross_session_bus import AgentIdentity, AgentMessage, CrossSessionBus
from aios_council_chatbot import CouncilChatbot


class HeteroCouncilTests(unittest.TestCase):
    def setUp(self):
        # Use mock substrates to ensure deterministic and hermetic test runs
        self.mock_substrates = [
            {"id": "qwen-mock", "provider": "mock", "model": "qwen3-coder", "family": "qwen", "role": "coder"},
            {"id": "deepseek-mock", "provider": "mock", "model": "deepseek-v4", "family": "deepseek", "role": "architect"},
            {"id": "llama-mock", "provider": "mock", "model": "llama-3.1", "family": "llama", "role": "critic"},
            {"id": "qwen-alt-mock", "provider": "mock", "model": "qwen3-alt", "family": "qwen", "role": "verifier"},
        ]
        self.council = HeteroCouncil(substrates=self.mock_substrates)

    def test_n_eff_calculation(self):
        # 4 members: 2 qwen, 1 deepseek, 1 llama
        # n_eff = 1.0 (deepseek) + 1.0 (llama) + (1.0 + 0.2) (qwen) = 3.2
        n_eff = self.council.calculate_n_eff(self.mock_substrates)
        self.assertEqual(n_eff, 3.2)

    def test_ideation_and_debate_flow(self):
        topic = "Implement Dynamic Memory Graph"
        ideation = self.council.ideate(topic)
        self.assertEqual(ideation["phase"], "ideation")
        self.assertEqual(len(ideation["proposals"]), 4)
        self.assertTrue(all(p["ok"] for p in ideation["proposals"]))

        debate = self.council.debate(topic, ideation["proposals"])
        self.assertEqual(debate["phase"], "debate")
        self.assertEqual(len(debate["critiques"]), 4)

        consensus = self.council.synthesize_consensus(topic, ideation, debate)
        self.assertEqual(consensus["phase"], "consensus")
        self.assertTrue(len(consensus["consensus_text"]) > 0)


class EvolutionaryGraphTests(unittest.TestCase):
    def setUp(self):
        self.genome = create_default_genome("test-genome-v1")
        # Ensure all nodes use mock provider for tests
        for role in self.genome.substrate_map:
            self.genome.substrate_map[role]["provider"] = "mock"

    def test_dynamic_graph_execution_success(self):
        engine = DynamicGraphEngine(self.genome)
        state = engine.run("Implement thread-safe queue in Python")
        self.assertTrue(state.oracle_passed)
        self.assertGreater(state.step_count, 0)
        self.assertIn("plan", state.data)
        self.assertIn("code", state.data)

    def test_genetic_mutation_and_crossover(self):
        opt = EvolutionaryOptimizer(population_size=4)
        parent_a = create_default_genome("parent-a")
        parent_b = create_default_genome("parent-b")

        mutated = opt.mutate(parent_a, gen=1)
        self.assertEqual(mutated.generation, 1)
        self.assertIn(parent_a.id, mutated.parent_ids)

        crossed = opt.crossover(parent_a, parent_b, gen=1)
        self.assertEqual(crossed.generation, 1)
        self.assertEqual(len(crossed.parent_ids), 2)

    def test_evolutionary_generation_cycle(self):
        opt = EvolutionaryOptimizer(population_size=2)
        opt.initialize_population()
        # Ensure mock
        for g in opt.population:
            for role in g.substrate_map:
                g.substrate_map[role]["provider"] = "mock"

        tasks = ["Test Task 1", "Test Task 2"]
        next_pop = opt.evolve_generation(tasks, gen=0)
        self.assertEqual(len(next_pop), 2)
        self.assertGreaterEqual(opt.hall_of_fame[-1].fitness_score, 0.0)


class CrossSessionBusTests(unittest.TestCase):
    def setUp(self):
        self.bus = CrossSessionBus()

    def test_agent_registration_and_messaging(self):
        agent_a = "agent-session-alpha"
        agent_b = "agent-session-beta"

        self.bus.register_agent(agent_a, ["provider.ollama", "role.coder"], "qwen", "ollama")
        self.bus.register_agent(agent_b, ["provider.nim", "role.critic"], "deepseek", "nim")

        # Send query with correlation ID
        corr_id = "corr-test-12345"
        msg = self.bus.send_message(
            sender_id=agent_a,
            recipient_id=agent_b,
            content="Please review this memory contract.",
            correlation_id=corr_id,
        )

        self.assertEqual(msg.correlation_id, corr_id)

        # Receive in recipient's inbox
        received = self.bus.receive_messages(agent_b, correlation_id=corr_id)
        self.assertTrue(any(m.id == msg.id for m in received))

    def test_convergence_detection(self):
        history = [
            AgentMessage(
                id="1", correlation_id="c1", sender_id="a", recipient_id="b",
                kind="critique", content="The interface has a race condition in locking."
            ),
            AgentMessage(
                id="2", correlation_id="c1", sender_id="b", recipient_id="a",
                kind="response", content="I agree, all invariants satisfied and consensus reached."
            ),
        ]
        converged = self.bus.check_convergence(history)
        self.assertTrue(converged)


class CouncilChatbotTests(unittest.TestCase):
    def test_chatbot_compile_flow(self):
        bot = CouncilChatbot("test-bot")
        # Ensure mock
        for s in bot.council.substrates:
            s["provider"] = "mock"

        bot.handle_ideate("Build Evolutionary Society Core")
        bot.handle_debate("Build Evolutionary Society Core")
        bot.handle_compile()

        self.assertTrue(bot.current_genome.id.startswith("compiled-"))
        self.assertIn("Build Evolutionary Society Core", bot.current_genome.prompt_dna["architect"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
