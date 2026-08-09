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
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.sources_cache import SourceCache
from app.services.topic_discovery import TopicCandidate, discover_topics

logger = logging.getLogger(__name__)

# Cache entries older than this are treated as expired and re-considered.
# Keep at 24h so ACCEPTED/published URLs are locked for a full day and
# are never re-fed into the pipeline. REJECTED URLs are handled
# differently: `release_rejected_from_cache()` (called by the scheduler
# after each cycle) immediately deletes their cache rows so they become
# re-eligible on the very next cycle. This two-tier strategy means:
#   - Published stories: never re-processed (24h lock).
#   - Rejected stories: re-eligible next cycle, but `RejectedTopic`
#     fingerprint fast-rejects them with zero LLM calls — keeping cost
#     low while keeping the candidate pool from drying up.
#   - Truly new RSS articles that appeared since the last cycle: always
#     new to the cache, always fully evaluated.
CACHE_TTL_HOURS = 24  # Only applies to accepted/published URLs now.


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

    Entries older than CACHE_TTL_HOURS are treated as expired and
    re-considered — this ensures the agent continues finding content even
    when RSS feeds haven't published entirely new articles since the last cycle.
    """
    new_candidates: list[TopicCandidate] = []
    expiry_cutoff = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)

    for candidate in candidates:
        content_hash = compute_content_hash(candidate)
        existing = (
            db.query(SourceCache).filter_by(content_hash=content_hash).first()
        )

        if existing is not None:
            # If the cache entry is still fresh, skip this candidate
            fetched_at = existing.fetched_at
            # Make naive datetime timezone-aware for comparison
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            if fetched_at > expiry_cutoff:
                continue
            # Entry is expired — delete it so we re-insert with a fresh timestamp
            db.delete(existing)
            db.flush()

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


def release_unaccepted_from_cache(db: Session, unaccepted_candidates: list[TopicCandidate]) -> int:
    """Delete sources_cache rows for candidates that were NOT accepted (rejected or skipped due to max_accepts).

    Only ACCEPTED (published) candidates remain locked in sources_cache for 24h.
    Releasing unaccepted candidates ensures:
      1. Explicitly rejected candidates are fast-rejected by fingerprint on future runs.
      2. Unevaluated candidates (skipped when max_accepts was reached) remain in the candidate
         pool for subsequent scheduler cycles so the agent keeps finding new topics.

    Returns the count of cache rows deleted.
    """
    deleted = 0
    for candidate in unaccepted_candidates:
        content_hash = compute_content_hash(candidate)
        existing = db.query(SourceCache).filter_by(content_hash=content_hash).first()
        if existing is not None:
            db.delete(existing)
            deleted += 1
    db.commit()
    if deleted:
        logger.info(
            "release_unaccepted_from_cache: freed %d unaccepted URL(s) back into the candidate pool.",
            deleted,
        )
    return deleted


def release_rejected_from_cache(db: Session, rejected_candidates: list[TopicCandidate]) -> int:
    """Backwards-compatible alias for `release_unaccepted_from_cache`."""
    return release_unaccepted_from_cache(db, rejected_candidates)


def discover_new_topics(db: Session, sources=None, client=None) -> list[TopicCandidate]:
    """Fetch raw candidates (Stage 11's discover_topics) and return only
    the ones not already cached, caching every new one along the way.

    Unaccepted candidates are freed back into the pool after judgment
    by `release_unaccepted_from_cache()` — called by the scheduler.
    """
    candidates = discover_topics(sources=sources, client=client)
    new_candidates = filter_new_candidates(db, candidates)
    logger.info(
        "discover_new_topics: %d fetched, %d new after cache dedup",
        len(candidates),
        len(new_candidates),
    )
    return new_candidates
