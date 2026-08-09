"""
topic_discovery.py — Stage 11 scope.

Reads `app/core/topic_sources.json` and fetches raw topic candidates
from each configured source. This stage is intentionally shallow: it
produces a flat list of `TopicCandidate` objects and nothing more — no
deduplication against `sources_cache` (Stage 12), no fingerprinting
(Stage 13), no editorial judgment (Stage 14). Every call re-fetches
everything from scratch.

Two source types are supported, matched to the two shapes real feeds
actually come in:
- `hn_algolia` — Hacker News via the Algolia Search API (JSON), used
  instead of scraping HN directly since it's a stable, well-documented
  public JSON endpoint with no auth required.
- `rss` — standard RSS 2.0 `<item>` feeds (arXiv, MIT Tech Review),
  parsed with the standard library's `xml.etree.ElementTree` rather
  than adding a `feedparser` dependency — Stage 11's needs
  (title/link/pubDate/description) don't need a general-purpose feed
  library.

Per-source fetch/parse failures are caught individually and logged,
not raised — a malformed or temporarily-down feed must not take down
discovery for every other source, especially once this runs
unattended under Stage 18's scheduler.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

TOPIC_SOURCES_PATH = Path(__file__).resolve().parent.parent / "core" / "topic_sources.json"

FETCH_TIMEOUT_SECONDS = 15.0


@dataclass
class TopicCandidate:
    """A single raw, unjudged, unfiltered topic pulled from a source.

    Deliberately minimal — just enough for Stage 12's cache/dedup and
    Stage 14's editorial judgment to work with. No `id`/`fingerprint`
    field yet (Stage 13).
    """

    title: str
    url: str
    source_name: str
    category: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None


class TopicSourceError(RuntimeError):
    """Raised when a single source's config is malformed (bad `type`).

    Not raised for network/parse failures against an otherwise
    well-configured source — those are caught and logged per-source
    (see module docstring) so one bad or slow feed doesn't block
    discovery from every other source.
    """


@lru_cache
def load_topic_sources() -> list[dict]:
    """Load and cache the configured source list from topic_sources.json."""
    with open(TOPIC_SOURCES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["sources"]


def _parse_hn_algolia(payload: dict, source_name: str, category: str) -> list[TopicCandidate]:
    """Parse an Algolia HN search response into candidates.

    Story hits with no title or no URL (self-posts sometimes lack a
    direct `url`, falling back to the HN discussion page) are skipped
    rather than producing a candidate with a missing field.
    """
    candidates: list[TopicCandidate] = []
    for hit in payload.get("hits", []):
        title = hit.get("title")
        url = hit.get("url") or (
            f"https://news.ycombinator.com/item?id={hit['objectID']}"
            if hit.get("objectID")
            else None
        )
        if not title or not url:
            continue

        published_at = None
        created_at = hit.get("created_at")
        if created_at:
            try:
                published_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                published_at = None

        candidates.append(
            TopicCandidate(
                title=title,
                url=url,
                source_name=source_name,
                category=category,
                summary=None,
                published_at=published_at,
            )
        )
    return candidates


# RSS 2.0 items are un-namespaced; Atom-style feeds sometimes wrap
# content in a namespace, which the two configured sources don't use.
# Kept as a plain tag lookup rather than full namespace handling since
# both current sources are standard RSS 2.0.
def _parse_rss(xml_text: str, source_name: str, category: str) -> list[TopicCandidate]:
    """Parse an RSS 2.0 feed's <item> elements into candidates.

    Items missing a title or link are skipped (same reasoning as the
    HN parser) rather than producing an incomplete candidate.
    """
    candidates: list[TopicCandidate] = []
    root = ElementTree.fromstring(xml_text)

    for item in root.iterfind(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        url = (link_el.text or "").strip()
        if not title or not url:
            continue

        description_el = item.find("description")
        summary = description_el.text.strip() if description_el is not None and description_el.text else None

        pubdate_el = item.find("pubDate")
        published_at = None
        if pubdate_el is not None and pubdate_el.text:
            try:
                # RFC 2822, e.g. "Tue, 05 Aug 2025 00:00:00 -0400"
                from email.utils import parsedate_to_datetime
                published_at = parsedate_to_datetime(pubdate_el.text.strip())
            except (TypeError, ValueError):
                published_at = None

        candidates.append(
            TopicCandidate(
                title=title,
                url=url,
                source_name=source_name,
                category=category,
                summary=summary,
                published_at=published_at,
            )
        )
    return candidates


def fetch_source(source: dict, client: httpx.Client) -> list[TopicCandidate]:
    """Fetch and parse a single configured source.

    Raises `TopicSourceError` only for a malformed source config
    (unknown `type`) — a programmer/config error worth failing loudly
    on. Network errors, non-2xx responses, and parse errors against an
    otherwise valid source are caught here, logged, and result in an
    empty list for that source rather than propagating, per the
    module-level "one bad feed shouldn't block discovery" rule.
    """
    name = source["name"]
    source_type = source["type"]
    url = source["url"]
    category = source.get("category", "uncategorized")

    if source_type not in ("hn_algolia", "rss"):
        raise TopicSourceError(f"Unknown topic source type: {source_type!r} for source {name!r}")

    try:
        response = client.get(url, timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True)
        response.raise_for_status()
    except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
        logger.warning("Topic source fetch failed for %r: %s", name, exc)
        return []

    try:
        if source_type == "hn_algolia":
            return _parse_hn_algolia(response.json(), name, category)
        return _parse_rss(response.text, name, category)
    except Exception as exc:  # noqa: BLE001 - malformed response body from an
        # otherwise-reachable source must not crash discovery.
        logger.warning("Topic source parse failed for %r: %s", name, exc)
        return []


def discover_topics(sources: Optional[list[dict]] = None, client: Optional[httpx.Client] = None) -> list[TopicCandidate]:
    """Fetch raw topic candidates from every configured source.

    `sources` and `client` are injectable for testing (see
    scripts/test_topic_discovery.py) — production callers use the
    defaults (topic_sources.json, a fresh httpx.Client).
    """
    sources = sources if sources is not None else load_topic_sources()
    owns_client = client is None
    client = client if client is not None else httpx.Client(
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 AetherBot/1.0"
        },
    )

    all_candidates: list[TopicCandidate] = []
    try:
        for source in sources:
            all_candidates.extend(fetch_source(source, client))
    finally:
        if owns_client:
            client.close()

    return all_candidates
