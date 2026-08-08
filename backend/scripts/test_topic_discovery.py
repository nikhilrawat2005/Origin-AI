"""
Stage 11 verification — Topic Sources Config + Fetcher.

Confirms:
1. `topic_sources.json` loads and every configured source has the
   required fields (`name`, `type`, `url`, `category`) and a known
   `type`.
2. `_parse_hn_algolia` correctly turns a canned Algolia response into
   TopicCandidates, skipping hits missing a title/url.
3. `_parse_rss` correctly turns a canned RSS 2.0 feed into
   TopicCandidates, skipping items missing a title/link.
4. `discover_topics()` aggregates across multiple sources and, when
   one source fails (bad status code) and another succeeds, still
   returns candidates from the working source rather than raising —
   using `httpx.MockTransport` to fully exercise the real HTTP/parse
   path without needing live network access to Hacker News/arXiv
   (unavailable in this sandboxed environment, same constraint as
   Stages 6/7/9's live-API smoke tests — but here the parsing logic
   itself is testable offline against canned response bodies, which
   is stronger coverage than those stages could get).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.services.topic_discovery import (
    load_topic_sources,
    _parse_hn_algolia,
    _parse_rss,
    discover_topics,
)

SAMPLE_HN_RESPONSE = {
    "hits": [
        {
            "title": "New LLM benchmark released",
            "url": "https://example.com/benchmark",
            "objectID": "111",
            "created_at": "2026-08-01T12:00:00.000Z",
        },
        {
            # No url, but has objectID -> should fall back to HN item link
            "title": "Ask HN: best AI reading list?",
            "url": None,
            "objectID": "222",
            "created_at": "2026-08-02T09:30:00.000Z",
        },
        {
            # No title at all -> should be skipped
            "title": None,
            "url": "https://example.com/no-title",
            "objectID": "333",
            "created_at": "2026-08-03T09:30:00.000Z",
        },
    ]
}

SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example AI Feed</title>
    <item>
      <title>Researchers propose new attention mechanism</title>
      <link>https://example.com/paper-1</link>
      <description>A new approach to attention in transformers.</description>
      <pubDate>Tue, 05 Aug 2025 00:00:00 -0400</pubDate>
    </item>
    <item>
      <!-- Missing link -> should be skipped -->
      <title>Untitled paper with no link</title>
      <description>Should not appear as a candidate.</description>
    </item>
  </channel>
</rss>
"""


def test_config_loads():
    print("1. Loading topic_sources.json...")
    sources = load_topic_sources()
    assert len(sources) >= 1, "expected at least one configured source"
    for source in sources:
        for field in ("name", "type", "url", "category"):
            assert field in source, f"source missing required field {field!r}: {source}"
        assert source["type"] in ("hn_algolia", "rss"), f"unknown source type: {source['type']!r}"
    print(f"   OK — {len(sources)} sources configured, all required fields present")


def test_hn_algolia_parser():
    print("2. Parsing sample HN Algolia response...")
    candidates = _parse_hn_algolia(SAMPLE_HN_RESPONSE, "Hacker News (AI/ML)", "industry")
    assert len(candidates) == 2, f"expected 2 candidates (1 skipped for no title), got {len(candidates)}"
    assert candidates[0].title == "New LLM benchmark released"
    assert candidates[0].url == "https://example.com/benchmark"
    assert candidates[1].url == "https://news.ycombinator.com/item?id=222", "expected HN link fallback"
    assert all(c.source_name == "Hacker News (AI/ML)" for c in candidates)
    print(f"   OK — {len(candidates)} candidates parsed, missing-title hit skipped, HN link fallback works")


def test_rss_parser():
    print("3. Parsing sample RSS feed...")
    candidates = _parse_rss(SAMPLE_RSS_FEED, "Example AI Feed", "research")
    assert len(candidates) == 1, f"expected 1 candidate (1 skipped for no link), got {len(candidates)}"
    c = candidates[0]
    assert c.title == "Researchers propose new attention mechanism"
    assert c.url == "https://example.com/paper-1"
    assert c.summary == "A new approach to attention in transformers."
    assert c.published_at is not None, "expected pubDate to parse"
    print(f"   OK — 1 candidate parsed, missing-link item skipped, pubDate parsed to {c.published_at}")


def test_discover_topics_partial_failure():
    print("4. Testing discover_topics() aggregation with one source failing...")

    fake_sources = [
        {"name": "Working HN Source", "type": "hn_algolia", "url": "https://fake.test/hn", "category": "industry"},
        {"name": "Broken RSS Source", "type": "rss", "url": "https://fake.test/broken-rss", "category": "research"},
        {"name": "Working RSS Source", "type": "rss", "url": "https://fake.test/rss", "category": "commentary"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/hn":
            return httpx.Response(200, json=SAMPLE_HN_RESPONSE)
        if request.url.path == "/broken-rss":
            return httpx.Response(503, text="Service Unavailable")
        if request.url.path == "/rss":
            return httpx.Response(200, text=SAMPLE_RSS_FEED)
        raise AssertionError(f"unexpected request: {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    candidates = discover_topics(sources=fake_sources, client=client)

    # 2 from the working HN source + 1 from the working RSS source;
    # the broken RSS source contributes 0 and does not raise.
    assert len(candidates) == 3, f"expected 3 total candidates, got {len(candidates)}"
    source_names = {c.source_name for c in candidates}
    assert source_names == {"Working HN Source", "Working RSS Source"}, (
        f"expected only working sources represented, got {source_names}"
    )
    print(f"   OK — {len(candidates)} candidates aggregated across sources; "
          f"broken source failed gracefully without raising")


def main() -> None:
    test_config_loads()
    test_hn_algolia_parser()
    test_rss_parser()
    test_discover_topics_partial_failure()
    print("\nAll Stage 11 checks passed.")


if __name__ == "__main__":
    main()
