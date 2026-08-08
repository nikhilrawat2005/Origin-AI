"""
Response schema(s) for the agent endpoints.

Stage 8 added `personaDescription` once `/init` started generating one
via the LLM. Stage 10 adds `breethAgentRef` now that `/init` also
establishes the agent's Breeth namespace (agent_service.
_create_breeth_namespace) — always populated on creation, since the
group_id is locally derived rather than something Breeth returns (see
that function's docstring for why it's set even when the underlying
remote write fails). Schema will keep growing as later stages
(scheduler status) add fields rather than being redefined.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentInitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agentId: str
    status: str
    personaName: str
    personaDescription: str | None = None
    breethAgentRef: str | None = None
    createdAt: datetime
