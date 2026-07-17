"""Provider adapter layer tests — no real CLI is ever invoked."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _load(name: str):
    full = f"{name}_under_test"
    spec = importlib.util.spec_from_file_location(full, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[full] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class AdaptersTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")
        import os
        import unittest.mock as mock
        # Isolate from ambient cloud-provider keys so REST auto-registration
        # (nvidia_nim / anthropic_rest / gemini_rest) is deterministic in any env.
        _env = mock.patch.dict(os.environ, {}, clear=False)
        _env.start()
        for _k in ("NVIDIA_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
            os.environ.pop(_k, None)
        self.addCleanup(_env.stop)

    def test_build_argv_substitutes_prompt_and_binary(self):
        # ollama uses positional-arg mode — prompt appears in argv
        spec = self.a.SPECS["ollama_local"]
        argv = spec.build_argv("hello world")
        self.assertIn("hello world", argv)

    def test_claude_spec_uses_stdin_mode(self):
        # claude uses stdin mode — prompt must NOT appear in argv (sent via stdin)
        spec = self.a.SPECS["claude"]
        self.assertTrue(spec.use_stdin)
        argv = spec.build_argv("hello world")
        self.assertNotIn("hello world", argv)
        self.assertEqual(argv, ["claude", "-p"])
        self.assertEqual(spec.get_stdin("hello world"), "hello world")

    def test_adapter_returns_stdout_on_success(self):
        calls = []

        def fake_runner(argv, stdin_text, timeout):
            calls.append((argv, stdin_text))
            return 0, "RESPONSE TEXT", ""

        adapter = self.a.make_adapter(self.a.SPECS["ollama_local"], runner=fake_runner)
        out = adapter("summarize this")
        self.assertEqual(out, "RESPONSE TEXT")
        # default local model is env-tunable (AIOS_OLLAMA_MODEL); agentic default 30b
        import os as _os
        expected_model = _os.environ.get("AIOS_OLLAMA_MODEL", "qwen3-coder:30b")
        self.assertEqual(calls[0][0][:3], ["ollama", "run", expected_model])

    def test_claude_adapter_sends_prompt_via_stdin(self):
        calls = []

        def fake_runner(argv, stdin_text, timeout):
            calls.append((argv, stdin_text))
            return 0, '{"done":true}', ""

        adapter = self.a.make_adapter(self.a.SPECS["claude"], runner=fake_runner)
        out = adapter("my prompt")
        self.assertEqual(out, '{"done":true}')
        self.assertEqual(calls[0][0], ["claude", "-p"])   # no prompt in argv
        self.assertEqual(calls[0][1], "my prompt")        # prompt in stdin_text

    def test_adapter_raises_on_nonzero(self):
        def fake_runner(argv, stdin_text, timeout):
            return 1, "", "auth required"

        adapter = self.a.make_adapter(self.a.SPECS["gemini"], runner=fake_runner)
        with self.assertRaises(RuntimeError) as ctx:
            adapter("x")
        self.assertIn("auth required", str(ctx.exception))

    def test_build_adapters_filters_by_presence(self):
        # pretend only codex is installed; disable ollama_rest auto-registration
        reg = self.a.build_adapters(
            runner=lambda argv, s, t: (0, "ok", ""),
            which=lambda b: "/usr/bin/" + b if b == "codex" else None,
            rest_available=lambda: False,
        )
        self.assertEqual(set(reg), {"codex"})

    def test_build_adapters_require_present_false_builds_all(self):
        # require_present=False + rest disabled → exactly the SPECS keys
        reg = self.a.build_adapters(
            runner=lambda argv, s, t: (0, "ok", ""),
            which=lambda b: None,
            require_present=False,
            rest_available=lambda: False,
        )
        self.assertEqual(set(reg), set(self.a.SPECS))

    def test_build_adapters_includes_ollama_rest_when_available(self):
        reg = self.a.build_adapters(
            runner=lambda argv, s, t: (0, "ok", ""),
            which=lambda b: None,
            require_present=False,
            rest_available=lambda: True,
        )
        self.assertIn("ollama_rest", reg)

    def test_available_providers_uses_which(self):
        names = self.a.available_providers(which=lambda b: "/x/" + b if b in ("claude", "ollama") else None)
        self.assertIn("claude", names)
        self.assertIn("ollama_local", names)
        self.assertNotIn("gemini", names)

    def test_integration_runner_executes_provider_via_fake_adapter(self):
        """The runner should accept a built adapter registry and run a provider step."""
        runner_mod = _load("aios_contract_runner")
        co = runner_mod.co
        reg = self.a.build_adapters(
            providers=["ollama_local"],
            runner=lambda argv, s, t: (0, "LOCAL THOUGHT", ""),
            require_present=False,
        )
        c = co.ContractObject(contract_id="co-adapt", goal="think")
        c.provider_routes.append(co.ProviderRoute(provider="ollama_local", auth_mode="local", role="background"))
        c.steps.append(co.Step(id="t1", description="local cognition", tool="provider.ollama_local",
                               inputs={"prompt": "what is 2+2"}))
        summary = runner_mod.run_contract(c, adapters=reg)
        self.assertEqual(summary["status"], "closed", summary)
        self.assertTrue(c.receipts[0].success)


class OllamaRestAdapterTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")

    def test_make_ollama_rest_adapter_calls_openai_compat_api(self):
        """Adapter must POST to /v1/chat/completions and parse choices[0].message.content."""
        import json
        import unittest.mock as mock

        response_body = json.dumps({
            "choices": [{"message": {"content": "hello from ollama"}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            adapter = self.a.make_ollama_rest_adapter(timeout=10)
            result = adapter("test prompt")
            self.assertEqual(result, "hello from ollama")
            args, _ = mock_open.call_args
            req = args[0]
            self.assertIn("/v1/chat/completions", req.full_url)

    def test_make_ollama_rest_adapter_sends_no_think_system_message(self):
        """Adapter must include /no_think system message to suppress CoT in qwen3."""
        import json
        import unittest.mock as mock

        captured = {}
        response_body = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        def capture_request(req, timeout=None):
            captured["body"] = json.loads(req.data)
            return mock_resp

        with mock.patch("urllib.request.urlopen", side_effect=capture_request):
            adapter = self.a.make_ollama_rest_adapter(timeout=10)
            adapter("any prompt")
            messages = captured["body"]["messages"]
            system_msgs = [m for m in messages if m["role"] == "system"]
            self.assertTrue(any("/no_think" in m["content"] for m in system_msgs))

    def test_make_ollama_rest_adapter_legacy_url_upgrade(self):
        """Legacy url=/api/generate callers get silently upgraded to /v1 base."""
        import json
        import unittest.mock as mock

        response_body = json.dumps({
            "choices": [{"message": {"content": "upgraded"}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            # Caller passes the old /api/generate URL; adapter must upgrade to /v1/chat/completions
            adapter = self.a.make_ollama_rest_adapter(url="http://localhost:11434/api/generate", timeout=10)
            result = adapter("legacy test")
            self.assertEqual(result, "upgraded")
            args, _ = mock_open.call_args
            req = args[0]
            self.assertIn("/v1/chat/completions", req.full_url)
            self.assertNotIn("api/generate", req.full_url)

    def test_ollama_rest_available_returns_true_on_200(self):
        import unittest.mock as mock
        mock_resp = mock.MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)
        with mock.patch("urllib.request.urlopen", return_value=mock_resp):
            self.assertTrue(self.a._ollama_rest_available())

    def test_ollama_rest_available_returns_false_on_connection_error(self):
        import unittest.mock as mock
        import urllib.error
        with mock.patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            self.assertFalse(self.a._ollama_rest_available())


class GeminiRestAdapterTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")

    def test_gemini_rest_available_with_gemini_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}):
            self.assertTrue(self.a._gemini_rest_available())

    def test_gemini_rest_available_with_google_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "AIza-test"}):
            self.assertTrue(self.a._gemini_rest_available())

    def test_gemini_rest_not_available_when_no_key(self):
        import os
        import unittest.mock as mock
        env = {k: v for k, v in os.environ.items()
               if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(self.a._gemini_rest_available())

    def test_make_gemini_rest_adapter_calls_api(self):
        import json
        import os
        import unittest.mock as mock

        response_body = json.dumps({
            "candidates": [{"content": {"parts": [{"text": "hello from gemini"}]}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}):
            with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
                adapter = self.a.make_gemini_rest_adapter(timeout=10)
                result = adapter("test prompt")
                self.assertEqual(result, "hello from gemini")
                args, _ = mock_open.call_args
                req = args[0]
                self.assertIn("generativelanguage.googleapis.com", req.full_url)
                self.assertIn("AIza-test", req.full_url)

    def test_build_adapters_includes_gemini_rest_when_key_set(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}):
            reg = self.a.build_adapters(
                providers=["gemini_rest"],
                runner=lambda argv, s, t: (0, "ok", ""),
                which=lambda b: None,
                require_present=False,
                rest_available=lambda: False,
            )
            self.assertIn("gemini_rest", reg)


class AnthropicRestAdapterTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")

    def test_anthropic_rest_available_when_key_set(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            self.assertTrue(self.a._anthropic_rest_available())

    def test_anthropic_rest_not_available_when_no_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {}, clear=True):
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertFalse(self.a._anthropic_rest_available())

    def test_make_anthropic_rest_adapter_calls_api(self):
        import json
        import os
        import unittest.mock as mock

        response_body = json.dumps({
            "content": [{"type": "text", "text": "hello from claude"}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
                adapter = self.a.make_anthropic_rest_adapter(timeout=10)
                result = adapter("test prompt")
                self.assertEqual(result, "hello from claude")
                args, _ = mock_open.call_args
                req = args[0]
                self.assertIn("anthropic.com", req.full_url)
                self.assertIn("sk-test-key", req.get_header("X-api-key"))

    def test_build_adapters_includes_anthropic_rest_when_key_set(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            reg = self.a.build_adapters(
                providers=["anthropic_rest"],
                runner=lambda argv, s, t: (0, "ok", ""),
                which=lambda b: None,
                require_present=False,
                rest_available=lambda: False,
            )
            self.assertIn("anthropic_rest", reg)

    def test_build_adapters_excludes_anthropic_rest_when_no_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {}, clear=True):
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                reg = self.a.build_adapters(
                    providers=["anthropic_rest"],
                    runner=lambda argv, s, t: (0, "ok", ""),
                    which=lambda b: None,
                    require_present=False,
                    rest_available=lambda: False,
                )
                self.assertNotIn("anthropic_rest", reg)


class _FakeChatResult:
    """Minimal stand-in for aios_llm_client.ChatResult — only the fields
    make_sovereign_adapter reads."""
    def __init__(self, ok, text="", provider_used="", error=None, fallback_reason=None):
        self.ok = ok
        self.text = text
        self.provider_used = provider_used
        self.error = error
        self.fallback_reason = fallback_reason


class _FakeLLMClient:
    """DI stand-in for aios_llm_client.LLMClient — records every prompt sent."""
    def __init__(self, result: "_FakeChatResult"):
        self._result = result
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools=None):
        self.calls.append(messages)
        return self._result


class SovereignAdapterTest(unittest.TestCase):
    """make_sovereign_adapter (founder directive 2026-07-17): local/NIM first,
    claude/codex/gemini CLI escalation only on hard/failed/rejected — no real
    network or subprocess is ever invoked; every substrate is DI'd."""

    def setUp(self):
        self.a = _load("aios_adapters")

    def test_default_local_success_no_escalation(self):
        client = _FakeLLMClient(_FakeChatResult(ok=True, text="local answer",
                                                 provider_used="local_ollama"))
        adapter = self.a.make_sovereign_adapter(
            goal="what is 2+2", client=client, which=lambda b: None)
        out = adapter("what is 2+2")
        self.assertEqual(out, "local answer")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(adapter.provenance, [
            {"substrate": "local_ollama", "role": "primary", "reason": "local_ok", "ok": True},
        ])

    def test_local_failure_escalates_to_available_frontier_cli(self):
        client = _FakeLLMClient(_FakeChatResult(ok=False, error="both endpoints down",
                                                 fallback_reason="local_ollama: down; nvidia_nim: no api key"))
        calls = []

        def fake_runner(argv, stdin_text, timeout):
            calls.append(argv)
            return 0, "CLAUDE ANSWER", ""

        adapter = self.a.make_sovereign_adapter(
            goal="summarize this repo", client=client, runner=fake_runner,
            which=lambda b: "/usr/bin/claude" if b == "claude" else None)
        out = adapter("summarize this repo")
        self.assertEqual(out, "CLAUDE ANSWER")
        self.assertEqual(len(client.calls), 1)          # local was tried first
        self.assertEqual(len(calls), 1)                 # exactly one CLI subprocess
        self.assertEqual([p["substrate"] for p in adapter.provenance], ["local/nim", "claude"])
        self.assertFalse(adapter.provenance[0]["ok"])
        self.assertTrue(adapter.provenance[1]["ok"])
        self.assertEqual(adapter.provenance[1]["role"], "escalation")

    def test_hard_flag_true_skips_local_entirely(self):
        client = _FakeLLMClient(_FakeChatResult(ok=True, text="should never be used"))
        adapter = self.a.make_sovereign_adapter(
            goal="a trivial goal", client=client, hard=True,
            runner=lambda argv, s, t: (0, "FRONTIER ANSWER", ""),
            which=lambda b: "/usr/bin/codex" if b == "codex" else None)
        out = adapter("a trivial goal")
        self.assertEqual(out, "FRONTIER ANSWER")
        self.assertEqual(client.calls, [])               # local never invoked
        self.assertEqual(adapter.provenance, [
            {"substrate": "codex", "role": "escalation", "reason": "hard_task", "ok": True},
        ])

    def test_long_horizon_goal_autoescalates_without_explicit_hard_flag(self):
        client = _FakeLLMClient(_FakeChatResult(ok=True, text="should never be used"))
        long_goal = (
            "first read every python file under scripts/, then refactor the "
            "provider routing, then migrate the tests, then implement a new "
            "pipeline, then debug and integrate the result, then build and "
            "design the final report"
        )
        adapter = self.a.make_sovereign_adapter(
            goal=long_goal, client=client,
            runner=lambda argv, s, t: (0, "FRONTIER ANSWER", ""),
            which=lambda b: "/usr/bin/claude" if b == "claude" else None)
        out = adapter(long_goal)
        self.assertEqual(out, "FRONTIER ANSWER")
        self.assertEqual(client.calls, [])
        self.assertEqual(adapter.provenance[0]["substrate"], "claude")

    def test_verify_fn_rejection_triggers_escalation(self):
        client = _FakeLLMClient(_FakeChatResult(ok=True, text="weak local answer",
                                                 provider_used="local_ollama"))
        adapter = self.a.make_sovereign_adapter(
            goal="a hard verification task", client=client,
            verify_fn=lambda text: False,
            runner=lambda argv, s, t: (0, "BETTER ANSWER", ""),
            which=lambda b: "/usr/bin/codex" if b == "codex" else None)
        out = adapter("a hard verification task")
        self.assertEqual(out, "BETTER ANSWER")
        self.assertEqual(len(client.calls), 1)
        reasons = [p["reason"] for p in adapter.provenance]
        self.assertIn("verifier_rejected", reasons)
        self.assertEqual(adapter.provenance[-1]["substrate"], "codex")

    def test_no_frontier_cli_available_raises_honest_runtime_error(self):
        client = _FakeLLMClient(_FakeChatResult(ok=False, error="down"))
        adapter = self.a.make_sovereign_adapter(
            goal="goal", client=client, which=lambda b: None)
        with self.assertRaises(RuntimeError) as ctx:
            adapter("goal")
        self.assertIn("sovereign", str(ctx.exception))

    def test_escalation_order_falls_through_to_next_frontier_cli_on_failure(self):
        client = _FakeLLMClient(_FakeChatResult(ok=False, error="down"))

        def fake_runner(argv, stdin_text, timeout):
            if argv[0] == "claude":
                return 1, "", "claude auth expired"
            return 0, "CODEX ANSWER", ""

        adapter = self.a.make_sovereign_adapter(
            goal="goal", client=client, runner=fake_runner,
            which=lambda b: "/usr/bin/" + b if b in ("claude", "codex") else None)
        out = adapter("goal")
        self.assertEqual(out, "CODEX ANSWER")
        escalation_entries = [p for p in adapter.provenance if p["role"] == "escalation"]
        self.assertEqual([e["substrate"] for e in escalation_entries], ["claude", "codex"])
        self.assertFalse(escalation_entries[0]["ok"])
        self.assertTrue(escalation_entries[1]["ok"])

    def test_build_adapters_registers_sovereign_regardless_of_presence(self):
        reg = self.a.build_adapters(
            providers=["sovereign"], goal="g",
            runner=lambda argv, s, t: (0, "ok", ""),
            which=lambda b: None,
            require_present=True,
        )
        self.assertIn("sovereign", reg)

    def test_build_adapters_binds_goal_for_hard_classification(self):
        """A short prompt at call time must still classify as hard when the
        bound goal (from build_adapters(goal=...)) is long-horizon."""
        long_goal = (
            "first read every python file, then refactor, then migrate, "
            "then implement, then debug, then build and design the report"
        )
        reg = self.a.build_adapters(
            providers=["sovereign"], goal=long_goal,
            runner=lambda argv, s, t: (0, "FRONTIER ANSWER", ""),
            which=lambda b: "/usr/bin/claude" if b == "claude" else None,
        )
        out = reg["sovereign"]("short prompt")   # prompt itself is short/clean
        self.assertEqual(out, "FRONTIER ANSWER")
        self.assertEqual(reg["sovereign"].provenance[0]["substrate"], "claude")


if __name__ == "__main__":
    unittest.main()
