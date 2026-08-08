"""
Agent routes — POST /api/agent/init.

GET /api/agent/feed is added in Stage 19 with the exact PRD JSON shape
for posts; nothing here anticipates that response shape.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.agent import AgentInitResponse
from app.services.agent_service import get_or_create_agent

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/init", response_model=AgentInitResponse)
def init_agent(db: Session = Depends(get_db)):
    """Create the agent row (or return the existing one) and its id.

    Stage 8: on first call, this now generates the persona description
    via the LLM (persona_service + llm_factory) as part of creation. No
    Breeth namespace, no scheduler start — those land in Stages 10 and
    18 and will update the same row returned here.
    """
    agent = get_or_create_agent(db)
    return AgentInitResponse(
        agentId=agent.id,
        status=agent.status,
        personaName=agent.persona_name,
        personaDescription=agent.persona_description,
        createdAt=agent.created_at,
    )
