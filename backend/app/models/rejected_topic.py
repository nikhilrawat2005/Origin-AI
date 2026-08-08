"""
RejectedTopic model.

Logs topics the editorial judgment step decided NOT to publish, along
with why. This both prevents re-evaluating the same rejected topic
repeatedly and gives an audit trail of the persona's editorial standards.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RejectedTopic(Base):
    __tablename__ = "rejected_topics"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    source = Column(String, nullable=True)
    fingerprint = Column(String, nullable=True, index=True)

    reason = Column(Text, nullable=False)  # why editorial judgment rejected it

    created_at = Column(DateTime, default=_now)
