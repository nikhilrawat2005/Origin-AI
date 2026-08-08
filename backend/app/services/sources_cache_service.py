"""
sources_cache_service.py — Stage 12 scope.

Wires the `SourceCache` model (Stage 2, unused until now) into the
discovery path so repeated `discover_topics()` calls stop
re-surfacing the same items forever. Scope is deliberately narrow:

- `compute_content_hash()` — a simple, deterministic hash over
  `source_name` + `url`. This is *not* the fingerprinting Stage 13
  will add (normalized title + keywords + source, meant to catch the
  same underlying story republished under a different URL/title
  variant) — this stage's hash only needs to answer "have I already
  cached this exact URL from this exact source," which is enough to
  stop wasting cache rows and re-evaluation on the *identical* feed
  entry appearing on back-to-back scheduler runs. Fingerprint-level
  near-duplicate detection is explicitly deferred.
- `filter_new_candidates()` — given a list of `TopicCandidate`s, skips
  ones already in `sources_cache` and inserts a `SourceCache` row for
  every one that's new, returning only the new ones. Editorial
  judgment (Stage 14) and memory-based dedup against Breeth (Stage 15)
  are separate, later concerns — this stage only prevents the same
  literal feed entry from being cached/considered twice.
"""
import hashlib
import logging

from sqlalchemy.orm import Session

from app.models.sources_cache import SourceCache
from app.services.topic_discovery import TopicCandidate, discover_topics

logger = logging.getLogger(__name__)


def compute_content_hash(candidate: TopicCandidate) -> str:
    """Deterministic hash of `source_name` + `url`.

    URL rather than title is the primary key component because the
    same source can legitimately publish two different stories with
    similar titles, but the same URL appearing twice from the same
    source is always the same item (a re-fetch of an unchanged feed).
    """
    basis = f"{candidate.source_name}|{candidate.url}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def filter_new_candidates(db: Session, candidates: list[TopicCandidate]) -> list[TopicCandidate]:
    """Return only the candidates not already present in sources_cache,
    inserting a SourceCache row for each one kept.

    Candidates are deduplicated against the DB one at a time (not a
    single bulk query) so that two candidates in the *same* batch that
    happen to hash identically (e.g. a source listing the same item
    twice) don't both get inserted — the first occurrence claims the
    hash, the second is skipped against the now-updated in-session
    state.
    """
    new_candidates: list[TopicCandidate] = []

    for candidate in candidates:
        content_hash = compute_content_hash(candidate)
        already_seen = (
            db.query(SourceCache).filter_by(content_hash=content_hash).first()
        )
        if already_seen is not None:
            continue

        db.add(
            SourceCache(
                source_name=candidate.source_name,
                url=candidate.url,
                title=candidate.title,
                raw_summary=candidate.summary,
                content_hash=content_hash,
            )
        )
        new_candidates.append(candidate)

    db.commit()
    return new_candidates


def discover_new_topics(db: Session, sources=None, client=None) -> list[TopicCandidate]:
    """Fetch raw candidates (Stage 11's discover_topics) and return only
    the ones not already cached, caching every new one along the way.

    Not wired into any route or scheduler yet — that's Stage 18, which
    will call this as the first step in the discovery -> judgment ->
    memory -> generation -> publish chain.
    """
    candidates = discover_topics(sources=sources, client=client)
    new_candidates = filter_new_candidates(db, candidates)
    logger.info(
        "discover_new_topics: %d fetched, %d new after cache dedup",
        len(candidates),
        len(new_candidates),
    )
    return new_candidates
