"""
Post model.

A published piece of content. Every post must carry the rationale for
why it was published and the sources it was derived from, per the PRD's
"Publishing Rationale" requirement and the exact Feed API shape.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    # Why this topic was judged worth publishing (Editorial Judgment output)
    rationale = Column(Text, nullable=False)

    # JSON-encoded list of source URLs/references this post was derived from
    sources = Column(Text, nullable=False, default="[]")

    # Fingerprint used for dedup against future topic candidates (Stage 13)
    fingerprint = Column(String, nullable=True, index=True)

    created_at = Column(DateTime, default=_now, index=True)
