"""
Agent routes — Stage 4: POST /api/agent/init only.

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

    Stage 4 scope: no persona generation, no LLM, no Breeth namespace,
    no scheduler start. Those land in later stages and will update the
    same row returned here.
    """
    agent = get_or_create_agent(db)
    return AgentInitResponse(
        agentId=agent.id,
        status=agent.status,
        personaName=agent.persona_name,
        createdAt=agent.created_at,
    )
