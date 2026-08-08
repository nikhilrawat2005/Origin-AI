"""
Stage 12 verification — Sources Cache.

Runs against an in-memory SQLite DB. Confirms:
1. `compute_content_hash()` is deterministic and source+url sensitive
   (same source+url -> same hash; different url or different source ->
   different hash).
2. `filter_new_candidates()` inserts a SourceCache row per new
   candidate and returns all of them the first time they're seen.
3. Calling it again with the *same* candidates returns an empty list
   (everything already cached) and does not insert duplicate rows.
4. A mixed batch (some already-cached, some new) returns only the new
   ones, and a batch with an internal duplicate (two candidates that
   hash identically) only inserts/returns one of them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.agent import Agent  # noqa: F401
from app.models.post import Post  # noqa: F401
from app.models.rejected_topic import RejectedTopic  # noqa: F401
from app.models.sources_cache import SourceCache
from app.models.breeth_mirror import BreethMirrorFact  # noqa: F401
from app.services.topic_discovery import TopicCandidate
from app.services.sources_cache_service import compute_content_hash, filter_new_candidates


def make_candidate(title, url, source_name="Hacker News (AI/ML)", category="industry"):
    return TopicCandidate(title=title, url=url, source_name=source_name, category=category)


def main() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    c1 = make_candidate("New LLM benchmark released", "https://example.com/benchmark")
    c2 = make_candidate("Different story", "https://example.com/other-story")

    print("1. Confirming compute_content_hash() is deterministic and sensitive to url/source...")
    h1a = compute_content_hash(c1)
    h1b = compute_content_hash(make_candidate(c1.title, c1.url))
    assert h1a == h1b, "same source+url should hash identically"
    h2 = compute_content_hash(c2)
    assert h1a != h2, "different url should hash differently"
    h1_diff_source = compute_content_hash(make_candidate(c1.title, c1.url, source_name="arXiv cs.AI"))
    assert h1a != h1_diff_source, "different source with same url should hash differently"
    print("   OK")

    print("2. First-time filter_new_candidates() returns and caches all new candidates...")
    new1 = filter_new_candidates(db, [c1, c2])
    assert len(new1) == 2, f"expected 2 new candidates, got {len(new1)}"
    assert db.query(SourceCache).count() == 2, "expected 2 SourceCache rows after first call"
    print(f"   OK — {len(new1)} new candidates cached")

    print("3. Repeat call with the same candidates returns none...")
    new2 = filter_new_candidates(db, [c1, c2])
    assert new2 == [], f"expected no new candidates on repeat call, got {len(new2)}"
    assert db.query(SourceCache).count() == 2, "expected still 2 SourceCache rows, no duplicates inserted"
    print("   OK — no duplicates, no new candidates surfaced")

    print("4. Mixed batch (1 already-cached + 1 new + 1 internal duplicate) filters correctly...")
    c3 = make_candidate("A third, brand-new story", "https://example.com/third-story")
    c3_dupe = make_candidate("A third, brand-new story (dupe)", "https://example.com/third-story")  # same url -> same hash
    new3 = filter_new_candidates(db, [c1, c3, c3_dupe])
    assert len(new3) == 1, f"expected exactly 1 new candidate (c1 already cached, c3/c3_dupe collide), got {len(new3)}"
    assert new3[0].url == "https://example.com/third-story"
    assert db.query(SourceCache).count() == 3, f"expected 3 total SourceCache rows, got {db.query(SourceCache).count()}"
    print("   OK — already-cached item skipped, in-batch duplicate collapsed to one row")

    db.close()
    print("\nAll Stage 12 checks passed.")


if __name__ == "__main__":
    main()
