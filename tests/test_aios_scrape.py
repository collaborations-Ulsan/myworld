"""tests/test_aios_scrape.py -- web.scrape (scrapling-backed stealth fetch tool).

Founder directive (2026-07-22): bind scrapling into AIOS as a real capability via
the existing tool registry (scripts/aios_tools.py TOOL_SPEC/HANDLERS pattern).

Everything here is either pure arg-shape validation (no network) or a MOCKED
fetcher (no live network) -- deterministic and safe on a clean clone whether or
not scrapling's browser deps are installed. Live end-to-end verification of the
real scrapling fetch happens separately (not in this suite), matching how
web.fetch/web.search have no live-network unit tests either.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_tools as T  # noqa: E402


class RegistrationTests(unittest.TestCase):
    def test_registered_in_tool_spec_and_handlers(self) -> None:
        self.assertIn("web.scrape", T.TOOL_SPEC)
        self.assertIn("web.scrape", T.HANDLERS)

    def test_registered_as_advisory_class(self) -> None:
        self.assertEqual(T.TOOL_SPEC["web.scrape"][0], "advisory")

    def test_registered_in_build_registry(self) -> None:
        reg = T.build_registry()
        self.assertIn("web.scrape", reg.handlers)

    def test_advisory_class_always_allowed_by_gate(self) -> None:
        g = T.gate_for("test_outsider")
        import aios_turn_loop as L
        self.assertEqual(g("web.scrape", {"url": "https://example.com"}), L.ALLOW)


class ArgShapeAndDenialTests(unittest.TestCase):
    """No network at all -- these are rejected before any fetcher is touched."""

    def test_rejects_empty_url(self) -> None:
        r = T.HANDLERS["web.scrape"]({"url": ""})
        self.assertEqual(r["status"], "denied")

    def test_rejects_non_http_scheme(self) -> None:
        r = T.HANDLERS["web.scrape"]({"url": "file:///etc/passwd"})
        self.assertEqual(r["status"], "denied")
        self.assertIn("http", r["reason"])

    def test_rejects_ftp_scheme(self) -> None:
        r = T.HANDLERS["web.scrape"]({"url": "ftp://example.com/x"})
        self.assertEqual(r["status"], "denied")

    def test_blocks_localhost(self) -> None:
        r = T.HANDLERS["web.scrape"]({"url": "http://localhost:8080/x"})
        self.assertEqual(r["status"], "denied")
        self.assertIn("private", r["reason"])

    def test_blocks_loopback_ip(self) -> None:
        r = T.HANDLERS["web.scrape"]({"url": "http://127.0.0.1/secret"})
        self.assertEqual(r["status"], "denied")

    def test_blocks_private_lan_ip(self) -> None:
        r = T.HANDLERS["web.scrape"]({"url": "http://192.168.1.1/admin"})
        self.assertEqual(r["status"], "denied")

    def test_blocks_link_local(self) -> None:
        r = T.HANDLERS["web.scrape"]({"url": "http://169.254.169.254/latest/meta-data/"})
        self.assertEqual(r["status"], "denied")


class MockedFetchTests(unittest.TestCase):
    """Mocked at the scrapling.fetchers.Fetcher/StealthyFetcher call boundary --
    no live network. Verifies success shape, HTTP-error degrade, exception/timeout
    degrade, and that stealth=True actually routes to the stealth fetcher."""

    def _fake_response(self, status: int = 200, title: str = "Example Domain",
                        text: str = "Example Domain\nThis domain is for use in examples.",
                        url: str = "https://example.com/") -> MagicMock:
        resp = MagicMock()
        resp.status = status
        resp.url = url
        resp.get_all_text.return_value = text
        resp.css.return_value.get.return_value = title
        return resp

    def test_success_shape(self) -> None:
        fake = self._fake_response()
        with patch("scrapling.fetchers.Fetcher.get", return_value=fake) as m:
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com"})
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["http_status"], 200)
        self.assertEqual(r["title"], "Example Domain")
        self.assertIn("Example Domain", r["text"])
        self.assertFalse(r["stealth"])
        m.assert_called_once()
        _, kwargs = m.call_args
        self.assertEqual(kwargs.get("timeout"), 12)  # seconds, not ms -- Fetcher's own unit

    def test_text_is_truncated_to_max(self) -> None:
        long_text = "x" * 10_000
        fake = self._fake_response(text=long_text)
        with patch("scrapling.fetchers.Fetcher.get", return_value=fake):
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com"})
        self.assertEqual(r["status"], "ok")
        self.assertEqual(len(r["text"]), T._SCRAPE_MAX_TEXT)

    def test_http_error_status_degrades_honestly(self) -> None:
        fake = self._fake_response(status=404)
        with patch("scrapling.fetchers.Fetcher.get", return_value=fake):
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com/missing"})
        self.assertEqual(r["status"], "unavailable")
        self.assertIn("404", r["reason"])

    def test_fetch_exception_degrades_honestly_not_crash(self) -> None:
        with patch("scrapling.fetchers.Fetcher.get", side_effect=TimeoutError("timed out")):
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com/slow"})
        self.assertEqual(r["status"], "unavailable")
        self.assertIn("TimeoutError", r["reason"])

    def test_dns_style_exception_degrades_honestly(self) -> None:
        with patch("scrapling.fetchers.Fetcher.get", side_effect=OSError("Could not resolve host")):
            r = T.HANDLERS["web.scrape"]({"url": "https://no-such-host.invalid"})
        self.assertEqual(r["status"], "unavailable")
        self.assertIn("OSError", r["reason"])

    def test_stealth_flag_routes_to_stealthy_fetcher_not_plain(self) -> None:
        fake = self._fake_response()
        with patch("scrapling.fetchers.StealthyFetcher.fetch", return_value=fake) as m_stealth, \
             patch("scrapling.fetchers.Fetcher.get") as m_plain:
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com", "stealth": True})
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["stealth"])
        m_stealth.assert_called_once()
        m_plain.assert_not_called()
        _, kwargs = m_stealth.call_args
        self.assertEqual(kwargs.get("timeout"), 20_000)  # milliseconds -- StealthyFetcher's own unit

    def test_stealth_fetch_exception_degrades_honestly(self) -> None:
        with patch("scrapling.fetchers.StealthyFetcher.fetch", side_effect=RuntimeError("browser not found")):
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com", "stealth": True})
        self.assertEqual(r["status"], "unavailable")
        self.assertIn("RuntimeError", r["reason"])

    def test_missing_title_degrades_to_empty_not_crash(self) -> None:
        fake = self._fake_response()
        fake.css.return_value.get.return_value = None  # no <title> on the page
        with patch("scrapling.fetchers.Fetcher.get", return_value=fake):
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com"})
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["title"], "")


class MissingDependencyTests(unittest.TestCase):
    """Forces the lazy `from scrapling.fetchers import ...` to fail regardless of
    whether scrapling is actually installed in this environment, so the honest
    'not installed' degrade path is always exercised."""

    def test_missing_scrapling_degrades_honestly_not_crash(self) -> None:
        with patch.dict(sys.modules, {"scrapling": None, "scrapling.fetchers": None}):
            r = T.HANDLERS["web.scrape"]({"url": "https://example.com"})
        self.assertEqual(r["status"], "unavailable")
        self.assertIn("scrapling", r["reason"].lower())


if __name__ == "__main__":
    unittest.main()
