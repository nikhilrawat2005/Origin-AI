"""
BreethMirrorFact model — Stage 10 scope.

A local SQLite mirror of facts Aether attempts to write into Breeth.
This stage only needs it as a stub: one row per namespace-creation
attempt made from POST /api/agent/init, recording whether the remote
write actually succeeded (`synced`). It exists now so:

1. init/testing don't hard-depend on Breeth actually being reachable
   (no real BREETH_API_KEY in this sandboxed environment — same
   constraint as Stages 6/7/9) — the local row is written regardless,
   the remote call is best-effort.
2. Stage 15's memory_service has a local fallback to query against if
   a live Breeth search call fails, instead of introducing this table
   under time pressure later.

Not queried by anything yet outside its own write path and the Stage
10 verification script — later stages will add read paths as the
actual memory/dedup logic is built.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BreethMirrorFact(Base):
    __tablename__ = "breeth_mirror_facts"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)

    group_id = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    predicate = Column(String, nullable=False)
    object = Column(String, nullable=False)

    # Whether the corresponding remote Breeth write actually succeeded.
    synced = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=_now)
