"""
Response schema(s) for the agent endpoints.

Stage 8: adds `personaDescription` now that `/init` actually generates
one via the LLM (falls back to None if generation was skipped/failed —
see agent_service._generate_persona_description). Schema will keep
growing as later stages (Breeth ref, scheduler status) add fields
rather than being redefined.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentInitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agentId: str
    status: str
    personaName: str
    personaDescription: str | None = None
    createdAt: datetime
