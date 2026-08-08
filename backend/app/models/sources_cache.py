"""
SourcesCache model.

Caches raw topic candidates pulled from live sources during Topic
Discovery, so the fetcher (Stage 11/12) can skip content it has already
seen rather than re-fetching or re-evaluating it every scheduler run.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourceCache(Base):
    __tablename__ = "sources_cache"

    id = Column(String, primary_key=True, default=_uuid)

    source_name = Column(String, nullable=False)  # e.g. "hackernews", "arxiv"
    url = Column(String, nullable=True)
    title = Column(String, nullable=False)
    raw_summary = Column(Text, nullable=True)

    # Hash of normalized content used for fast "already seen" checks (Stage 12/13)
    content_hash = Column(String, nullable=False, unique=True, index=True)

    fetched_at = Column(DateTime, default=_now)
