"""
Agent model.

Represents the autonomous persona created by POST /api/agent/init.
The PRD implies a single active agent (init is called "exactly once"
by the evaluator), but the table supports multiple rows so local dev
can re-init without hacks — the API layer (Stage 4+) enforces the
"only one active agent" behavior.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=_uuid)

    # Persona identity (built in Stage 5 from persona.json + LLM voice profile)
    persona_name = Column(String, nullable=False, default="Aether")
    persona_description = Column(Text, nullable=True)

    # Reference to this agent's namespace in Breeth persistent memory
    breeth_agent_ref = Column(String, nullable=True)

    # Lifecycle status: "initializing" -> "active" (scheduler running)
    status = Column(String, nullable=False, default="initializing")

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
