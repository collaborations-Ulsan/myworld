"""Deterministic, no-network tests for experiments/radar/ (the AIOS ecosystem-radar
organ, founder directive 2026-07-17: keep tracking frontier + long-tail papers and
X/Reddit/GitHub communities across sessions).

Everything here is pure-function or injected-fake-HTTP: no real network calls.
Covers source parsing (arxiv atom / github json / reddit json), the seen-ledger
dedupe, keyword scoring/ranking, digest generation shape, and dry-run behavior.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Patching an attribute on scrapling.fetchers imports scrapling, so these
# mocked tests need the package even though they never hit the network.
# See the same note in tests/test_aios_scrape.py.
_HAS_SCRAPLING = importlib.util.find_spec("scrapling") is not None

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "experiments" / "radar").as_posix())

import run_radar  # noqa: E402
import score       # noqa: E402
import seen        # noqa: E402
import sources     # noqa: E402


ARXIV_ATOM_SAMPLE = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry>
<id>http://arxiv.org/abs/2607.00001v1</id>
<title>  Test Paper On Reward Hacking In Agents  </title>
<summary>  This paper studies reward hacking and specification gaming in RL agents.  </summary>
<published>2026-07-01T00:00:00Z</published>
</entry>
<entry>
<id>http://arxiv.org/abs/2607.00002v2</id>
<title>Unrelated Paper About Gardening</title>
<summary>This is about tomatoes and gardening tips.</summary>
<published>2026-07-02T00:00:00Z</published>
</entry>
</feed>
"""

GITHUB_SAMPLE = {
    "items": [
        {
            "full_name": "acme/agent-lib",
            "html_url": "https://github.com/acme/agent-lib",
            "description": "An evolutionary agent skill library",
            "stargazers_count": 42,
            "pushed_at": "2026-07-10T00:00:00Z",
        },
        {"full_name": "x/y"},          # minimal record, missing fields tolerated
        {"description": "no full_name -> skipped"},  # must be skipped
    ]
}

REDDIT_SAMPLE = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "abc123",
                    "subreddit": "LocalLLaMA",
                    "title": "New local LLM agent framework release",
                    "created_utc": 1783296000,
                    "permalink": "/r/LocalLLaMA/comments/abc123/x/",
                    "score": 55,
                    "selftext": "desc",
                }
            },
            {"data": {}},  # missing id -> skipped
        ]
    }
}

HF_SAMPLE = [
    {
        "paper": {
            "id": "2607.06701",
            "title": "SPEAR: A Simulator for Photorealistic Embodied AI Research",
            "summary": "A simulator for embodied agents.",
            "publishedAt": "2026-07-07T18:20:33.000Z",
            "upvotes": 12,
        },
        "title": "SPEAR: A Simulator for Photorealistic Embodied AI Research",
        "summary": "A simulator for embodied agents.",
        "publishedAt": "2026-07-07T18:20:33.000Z",
    },
    {"paper": {}},  # missing id -> skipped
]


class SourceParsingTests(unittest.TestCase):
    def test_parse_arxiv_atom(self) -> None:
        items = sources.parse_arxiv_atom(ARXIV_ATOM_SAMPLE)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["id"], "arxiv:2607.00001")
        self.assertEqual(items[0]["title"], "Test Paper On Reward Hacking In Agents")
        self.assertEqual(items[0]["date"], "2026-07-01")
        self.assertEqual(items[0]["source"], "arxiv")
        self.assertIn("reward hacking", items[0]["abstract_or_desc"])
        self.assertEqual(items[1]["id"], "arxiv:2607.00002")

    def test_parse_arxiv_atom_malformed(self) -> None:
        self.assertEqual(sources.parse_arxiv_atom("not xml at all <<<"), [])

    def test_parse_github_search(self) -> None:
        items = sources.parse_github_search(GITHUB_SAMPLE)
        self.assertEqual(len(items), 2)  # third record (no full_name) skipped
        self.assertEqual(items[0]["id"], "github:acme/agent-lib")
        self.assertEqual(items[0]["signal"], 42)
        self.assertEqual(items[0]["date"], "2026-07-10")
        self.assertEqual(items[1]["id"], "github:x/y")
        self.assertEqual(items[1]["signal"], 0)

    def test_parse_github_search_empty(self) -> None:
        self.assertEqual(sources.parse_github_search({}), [])

    def test_parse_reddit_listing(self) -> None:
        items = sources.parse_reddit_listing(REDDIT_SAMPLE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "reddit:LocalLLaMA:abc123")
        self.assertEqual(items[0]["signal"], 55)
        self.assertIn("local llm agent", items[0]["title"].lower())
        self.assertTrue(items[0]["url"].startswith("https://www.reddit.com/r/LocalLLaMA"))

    def test_parse_hf_papers(self) -> None:
        items = sources.parse_hf_papers(HF_SAMPLE)
        self.assertEqual(len(items), 1)  # second record (no id) skipped
        self.assertEqual(items[0]["id"], "hf:2607.06701")
        self.assertEqual(items[0]["signal"], 12)
        self.assertEqual(items[0]["date"], "2026-07-07")


@unittest.skipUnless(
    _HAS_SCRAPLING,
    "requires the scrapling package to patch scrapling.fetchers "
    "(pip install 'scrapling[fetchers]')",
)
class ScraplingFetchTests(unittest.TestCase):
    """fetch_page_via_scrapling (2026-07-22 scrapling absorption) -- mocked at the
    scrapling.fetchers call boundary, no live network. Optional escalation path,
    not wired into fetch_all()'s default sweep."""

    @staticmethod
    def _fake_response(status: int = 200, title: str = "T", text: str = "body text",
                        url: str = "https://x.example/") -> MagicMock:
        resp = MagicMock()
        resp.status = status
        resp.url = url
        resp.get_all_text.return_value = text
        resp.css.return_value.get.return_value = title
        return resp

    def test_success_shape(self) -> None:
        with patch("scrapling.fetchers.Fetcher.get", return_value=self._fake_response()):
            out = sources.fetch_page_via_scrapling("https://x.example/")
        self.assertEqual(out, {"title": "T", "text": "body text", "url": "https://x.example/", "status": 200})

    def test_http_error_raises_like_other_fetch_functions(self) -> None:
        with patch("scrapling.fetchers.Fetcher.get", return_value=self._fake_response(status=403)):
            with self.assertRaises(RuntimeError):
                sources.fetch_page_via_scrapling("https://x.example/blocked")

    def test_stealth_flag_routes_to_stealthy_fetcher(self) -> None:
        with patch("scrapling.fetchers.StealthyFetcher.fetch", return_value=self._fake_response()) as m_stealth, \
             patch("scrapling.fetchers.Fetcher.get") as m_plain:
            sources.fetch_page_via_scrapling("https://x.example/", stealth=True, timeout=5)
        m_stealth.assert_called_once()
        m_plain.assert_not_called()
        _, kwargs = m_stealth.call_args
        self.assertEqual(kwargs.get("timeout"), 5000)  # seconds -> ms for the Playwright-backed fetcher

    def test_not_wired_into_fetch_all_by_default(self) -> None:
        import inspect
        self.assertNotIn("fetch_page_via_scrapling", inspect.getsource(sources.fetch_all))


class SeenLedgerTests(unittest.TestCase):
    def test_load_seen_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(seen.load_seen(Path(tmp) / "nope.jsonl"), set())

    def test_append_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seen.jsonl"
            n = seen.append_seen(["arxiv:1", "github:acme/x"], path)
            self.assertEqual(n, 2)
            loaded = seen.load_seen(path)
            self.assertEqual(loaded, {"arxiv:1", "github:acme/x"})

    def test_append_seen_empty_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seen.jsonl"
            self.assertEqual(seen.append_seen([], path), 0)
            self.assertFalse(path.exists())

    def test_filter_new(self) -> None:
        items = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        fresh = seen.filter_new(items, {"b"})
        self.assertEqual([it["id"] for it in fresh], ["a", "c"])

    def test_second_run_surfaces_nothing_new(self) -> None:
        """The core 'continuous' contract: same items seen twice -> zero new the 2nd time."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seen.jsonl"
            items = [{"id": "arxiv:1"}, {"id": "arxiv:2"}]
            seen_ids_run1 = seen.load_seen(path)
            fresh1 = seen.filter_new(items, seen_ids_run1)
            self.assertEqual(len(fresh1), 2)
            seen.append_seen([it["id"] for it in fresh1], path)

            seen_ids_run2 = seen.load_seen(path)
            fresh2 = seen.filter_new(items, seen_ids_run2)
            self.assertEqual(fresh2, [])


class ScoreTests(unittest.TestCase):
    def test_relevant_ranks_above_irrelevant(self) -> None:
        relevant = {
            "id": "a", "title": "GEPA: evolutionary optimization for self-improving agents",
            "abstract_or_desc": "We study reward hacking and use a verifier to keep long-horizon "
                                 "agent behavior reliable, with continual learning memory.",
            "source": "arxiv", "date": "2026-07-01", "signal": 0,
        }
        irrelevant = {
            "id": "b", "title": "A study of gardening tomatoes",
            "abstract_or_desc": "Tips for growing tomatoes in your backyard garden.",
            "source": "arxiv", "date": "2026-07-01", "signal": 0,
        }
        ranked = score.rank_items([irrelevant, relevant])
        self.assertEqual(ranked[0]["id"], "a")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])
        self.assertEqual(ranked[1]["score"], 0)
        self.assertIn("gepa", ranked[0]["matched_keywords"])

    def test_score_item_no_match(self) -> None:
        score_val, matched = score.score_item({"title": "xyz", "abstract_or_desc": "nothing relevant here"})
        self.assertEqual(score_val, 0)
        self.assertEqual(matched, [])


class DigestTests(unittest.TestCase):
    def test_build_digest_shape(self) -> None:
        results = {
            "arxiv": {"items": [{"id": "arxiv:1"}], "error": None},
            "github": {"items": [], "error": "github: HTTPError: 403"},
        }
        new_by_source = {
            "arxiv": [{"id": "arxiv:1", "title": "T1", "source": "arxiv", "date": "2026-07-17",
                       "url": "https://arxiv.org/abs/1", "abstract_or_desc": "desc"}],
            "github": [],
        }
        ranked = score.rank_items(new_by_source["arxiv"])
        text = run_radar.build_digest(results, new_by_source, ranked, "2026-07-17")
        self.assertIn("AIOS Ecosystem Radar", text)
        self.assertIn("2026-07-17", text)
        self.assertIn("## Summary", text)
        self.assertIn("| arxiv |", text)
        self.assertIn("github: HTTPError: 403", text)
        self.assertIn("## Worth a Look", text)
        self.assertIn("## Session-Gated Sources", text)
        self.assertIn("x_twitter", text)
        self.assertIn("threads", text)
        self.assertIn("T1", text)


class RunRadarTests(unittest.TestCase):
    @staticmethod
    def _fake_fetch(timeout: int = 15) -> dict:
        return {
            "arxiv": {"items": [
                {"id": "arxiv:1", "title": "Reward Hacking Survey", "source": "arxiv",
                 "date": "2026-07-17", "url": "https://arxiv.org/abs/1",
                 "abstract_or_desc": "reward hacking and verifier design", "signal": 0},
                {"id": "arxiv:2", "title": "Gardening Tips", "source": "arxiv",
                 "date": "2026-07-17", "url": "https://arxiv.org/abs/2",
                 "abstract_or_desc": "tomatoes", "signal": 0},
            ], "error": None},
            "github": {"items": [], "error": "github: URLError: timed out"},
        }

    def test_dry_run_writes_no_seen_and_no_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seen_path = Path(tmp) / "seen.jsonl"
            digest_dir = Path(tmp) / "digests"
            receipt = run_radar.run(seen_path=seen_path, digest_dir=digest_dir,
                                     dry_run=True, fetch_fn=self._fake_fetch)
            self.assertTrue(receipt["dry_run"])
            self.assertEqual(receipt["total_new"], 2)
            self.assertIsNone(receipt["digest_path"])
            self.assertFalse(seen_path.exists())
            self.assertFalse(digest_dir.exists())

    def test_real_run_then_second_run_has_no_new(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seen_path = Path(tmp) / "seen.jsonl"
            digest_dir = Path(tmp) / "digests"

            receipt1 = run_radar.run(seen_path=seen_path, digest_dir=digest_dir,
                                      dry_run=False, fetch_fn=self._fake_fetch)
            self.assertEqual(receipt1["total_new"], 2)
            self.assertIsNotNone(receipt1["digest_path"])
            self.assertTrue(Path(receipt1["digest_path"]).exists())
            self.assertTrue(seen_path.exists())
            self.assertEqual(receipt1["seen_appended"], 2)
            # top-ranked should put the reward-hacking paper first
            self.assertEqual(receipt1["top_ranked"][0]["id"], "arxiv:1")

            receipt2 = run_radar.run(seen_path=seen_path, digest_dir=digest_dir,
                                      dry_run=False, fetch_fn=self._fake_fetch)
            self.assertEqual(receipt2["total_new"], 0)
            self.assertEqual(receipt2["seen_appended"], 0)

    def test_receipt_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seen_path = Path(tmp) / "seen.jsonl"
            digest_dir = Path(tmp) / "digests"
            receipt = run_radar.run(seen_path=seen_path, digest_dir=digest_dir,
                                     dry_run=True, fetch_fn=self._fake_fetch)
            json.dumps(receipt)  # must not raise


if __name__ == "__main__":
    unittest.main()
