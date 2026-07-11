"""aios_llm_client tests (masterplan §4 M5/D2-4) — no live network call.

Failover transport is dependency-injected via `post=` so every test drives a
fake `post(url, body, headers, timeout) -> dict` (or one that raises), the same
pattern as aios_adapters' fake `runner`.
"""
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


class EndpointOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.llm = _load("aios_llm_client")

    def test_default_endpoints_local_ollama_first_nim_second(self) -> None:
        eps = self.llm.default_endpoints()
        self.assertEqual([e.name for e in eps], ["local_ollama", "nvidia_nim"])

    def test_local_ollama_does_not_need_a_key(self) -> None:
        eps = self.llm.default_endpoints()
        self.assertFalse(eps[0].needs_key)

    def test_nim_needs_a_key(self) -> None:
        eps = self.llm.default_endpoints()
        self.assertTrue(eps[1].needs_key)

    def test_env_overrides_model_and_base_url(self) -> None:
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {
            "AIOS_OLLAMA_MODEL": "qwen3:8b",
            "AIOS_OLLAMA_BASE_URL": "http://localhost:9999/v1",
            "AIOS_NIM_MODEL": "some/other-model",
        }):
            eps = self.llm.default_endpoints()
        self.assertEqual(eps[0].model, "qwen3:8b")
        self.assertEqual(eps[0].base_url, "http://localhost:9999/v1")
        self.assertEqual(eps[1].model, "some/other-model")


class FailoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.llm = _load("aios_llm_client")

    def _endpoints(self, key_present: bool = True):
        ep_a = self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "qwen3-coder:30b")
        ep_b = self.llm.Endpoint("nvidia_nim", "https://integrate.api.nvidia.com/v1",
                                 "deepseek-ai/deepseek-v4-pro", needs_key=True,
                                 key_fn=(lambda: "sk-fake-key") if key_present else (lambda: ""))
        return [ep_a, ep_b]

    def test_primary_endpoint_used_when_it_succeeds(self) -> None:
        def fake_post(url, body, headers, timeout):
            self.assertIn("localhost:11434", url)
            return {"choices": [{"message": {"content": "hi"}}]}
        client = self.llm.LLMClient(self._endpoints(), post=fake_post)
        res = client.chat([{"role": "user", "content": "hello"}])
        self.assertTrue(res.ok)
        self.assertEqual(res.provider_used, "local_ollama")
        self.assertEqual(res.text, "hi")
        self.assertIsNone(res.fallback_reason)

    def test_fails_over_to_nim_when_ollama_unreachable(self) -> None:
        calls = []

        def fake_post(url, body, headers, timeout):
            calls.append(url)
            if "11434" in url:
                raise ConnectionError("connection refused")
            return {"choices": [{"message": {"content": "from nim"}}]}
        client = self.llm.LLMClient(self._endpoints(), post=fake_post)
        res = client.chat([{"role": "user", "content": "hello"}])
        self.assertTrue(res.ok)
        self.assertEqual(res.provider_used, "nvidia_nim")
        self.assertEqual(res.text, "from nim")
        self.assertIsNotNone(res.fallback_reason)
        self.assertIn("local_ollama", res.fallback_reason)
        # bounded retry: 2 attempts against the dead endpoint, then 1 against NIM
        self.assertEqual(len([c for c in calls if "11434" in c]), 2)

    def test_skips_nim_when_no_key_and_ollama_dead(self) -> None:
        def fake_post(url, body, headers, timeout):
            raise ConnectionError("connection refused")
        client = self.llm.LLMClient(self._endpoints(key_present=False), post=fake_post)
        res = client.chat([{"role": "user", "content": "hello"}])
        self.assertFalse(res.ok)
        self.assertIn("no api key", res.fallback_reason)

    def test_total_failure_is_honest_not_fabricated(self) -> None:
        def fake_post(url, body, headers, timeout):
            raise TimeoutError("timed out")
        client = self.llm.LLMClient(self._endpoints(), post=fake_post)
        res = client.chat([{"role": "user", "content": "hello"}])
        self.assertFalse(res.ok)
        self.assertEqual(res.text, "")
        self.assertIsNotNone(res.error)
        self.assertEqual(res.provider_used, "")


class KeyNeverLeaksTests(unittest.TestCase):
    """The leaked-key incident (CLAUDE.md): the resolved key must appear ONLY in
    the Authorization header, never in the ChatResult or its provenance."""

    def setUp(self) -> None:
        self.llm = _load("aios_llm_client")

    def test_key_reaches_auth_header_but_never_the_result(self) -> None:
        secret = "nvapi-super-secret-do-not-leak"
        seen_headers = {}

        def fake_post(url, body, headers, timeout):
            seen_headers.update(headers)
            return {"choices": [{"message": {"content": "ok"}}]}

        eps = [self.llm.Endpoint("nvidia_nim", "https://integrate.api.nvidia.com/v1",
                                 "deepseek-ai/deepseek-v4-pro", needs_key=True,
                                 key_fn=lambda: secret)]
        client = self.llm.LLMClient(eps, post=fake_post)
        res = client.chat([{"role": "user", "content": "hello"}])
        self.assertEqual(seen_headers.get("Authorization"), f"Bearer {secret}")
        self.assertNotIn(secret, repr(res))
        self.assertNotIn(secret, str(res.to_provenance()))

    def test_provenance_record_shape_has_no_content_fields(self) -> None:
        def fake_post(url, body, headers, timeout):
            return {"choices": [{"message": {"content": "some reply text"}}]}
        client = self.llm.LLMClient(
            [self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "qwen3-coder:30b")],
            post=fake_post)
        res = client.chat([{"role": "user", "content": "hello"}])
        prov = res.to_provenance()
        self.assertEqual(set(prov), {"provider_used", "model", "latency_ms",
                                     "fallback_reason", "ok", "tool_call_count"})
        self.assertNotIn("some reply text", str(prov))

    def test_missing_env_and_config_file_resolves_to_empty_key(self) -> None:
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NVIDIA_API_KEY", None)
            with mock.patch.object(self.llm.Path, "read_text", side_effect=OSError("no file")):
                self.assertEqual(self.llm._read_nvidia_api_key(), "")

    def test_env_var_key_takes_priority_over_file(self) -> None:
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"NVIDIA_API_KEY": "from-env"}):
            self.assertEqual(self.llm._read_nvidia_api_key(), "from-env")

    def test_reads_export_prefixed_key_from_config_file(self) -> None:
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NVIDIA_API_KEY", None)
            with mock.patch.object(
                self.llm.Path, "read_text",
                return_value="export NVIDIA_API_KEY=nvapi-from-file\n",
            ):
                self.assertEqual(self.llm._read_nvidia_api_key(), "nvapi-from-file")


class ToolCallParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.llm = _load("aios_llm_client")

    def test_native_tool_calls_are_parsed(self) -> None:
        def fake_post(url, body, headers, timeout):
            self.assertIn("tools", body)
            return {"choices": [{"message": {
                "content": None,
                "tool_calls": [{
                    "id": "call_1", "type": "function",
                    "function": {"name": "memory.retrieve",
                                "arguments": '{"task": "aios status"}'},
                }],
            }}]}
        client = self.llm.LLMClient(
            [self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "qwen3-coder:30b")],
            post=fake_post)
        res = client.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
        self.assertTrue(res.ok)
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0]["name"], "memory.retrieve")
        self.assertEqual(res.tool_calls[0]["arguments"], {"task": "aios status"})

    def test_malformed_arguments_json_degrades_to_empty_dict(self) -> None:
        def fake_post(url, body, headers, timeout):
            return {"choices": [{"message": {
                "tool_calls": [{"id": "c1", "function": {"name": "fs.list", "arguments": "{not json"}}],
            }}]}
        client = self.llm.LLMClient(
            [self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "qwen3-coder:30b")],
            post=fake_post)
        res = client.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
        self.assertEqual(res.tool_calls[0]["arguments"], {})

    def test_no_tool_calls_is_graceful_text_degrade(self) -> None:
        def fake_post(url, body, headers, timeout):
            return {"choices": [{"message": {"content": "plain text reply, no tool call"}}]}
        client = self.llm.LLMClient(
            [self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "qwen3-coder:30b")],
            post=fake_post)
        res = client.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
        self.assertTrue(res.ok)
        self.assertEqual(res.tool_calls, [])
        self.assertEqual(res.text, "plain text reply, no tool call")

    def test_tools_rejected_with_400_degrades_on_same_endpoint(self) -> None:
        calls = []

        def fake_post(url, body, headers, timeout):
            calls.append(dict(body))
            if body.get("tools"):
                raise self.llm._HTTPStatusError(400, "tools not supported by this model")
            return {"choices": [{"message": {"content": "text-only reply"}}]}
        client = self.llm.LLMClient(
            [self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "some-model")],
            post=fake_post)
        res = client.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
        self.assertTrue(res.ok)
        self.assertEqual(res.provider_used, "local_ollama")
        self.assertEqual(res.text, "text-only reply")
        self.assertIn("degraded to text", res.fallback_reason)
        # first attempt WITH tools, second attempt WITHOUT — same endpoint, no failover
        self.assertTrue(calls[0].get("tools"))
        self.assertNotIn("tools", calls[1])


class ToolCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.llm = _load("aios_llm_client")

    def test_known_tool_capable_model(self) -> None:
        self.assertTrue(self.llm.supports_tools("qwen3-coder:30b"))
        self.assertTrue(self.llm.supports_tools("deepseek-ai/deepseek-v4-pro"))

    def test_documented_non_tool_capable_model(self) -> None:
        self.assertFalse(self.llm.supports_tools("nvidia/nemotron-super-49b"))

    def test_unknown_model_defaults_to_false(self) -> None:
        self.assertFalse(self.llm.supports_tools("totally-unknown-model-xyz"))

    def test_primary_supports_tools_reads_first_endpoint(self) -> None:
        eps = [self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "qwen3-coder:30b"),
               self.llm.Endpoint("nvidia_nim", "https://integrate.api.nvidia.com/v1", "unknown-model")]
        client = self.llm.LLMClient(eps, post=lambda *a: {})
        self.assertTrue(client.primary_supports_tools())

    def test_primary_supports_tools_false_for_unverified_primary(self) -> None:
        eps = [self.llm.Endpoint("local_ollama", "http://localhost:11434/v1", "some-unverified-model")]
        client = self.llm.LLMClient(eps, post=lambda *a: {})
        self.assertFalse(client.primary_supports_tools())


if __name__ == "__main__":
    unittest.main()
