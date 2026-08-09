"""
Agent routes — POST /api/agent/init, GET /api/agent/feed.

Locked to the exact hackathon evaluator contract. Only these two
public endpoints exist — no `/generate`, no `/run`, nothing else the
evaluator could call to manually trigger a cycle. Everything after
`/init` happens autonomously via the Stage 18 scheduler.
"""
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.agent import Agent
from app.models.post import Post
from app.schemas.agent import AgentInitRequest, AgentInitResponse, FeedPost, FeedResponse
from app.services.agent_service import get_or_create_agent
from app.services.scheduler import start_scheduler

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/init", response_model=AgentInitResponse)
def init_agent(body: AgentInitRequest | None = None, db: Session = Depends(get_db)):
    """Create the agent row (or return the existing one), start the
    autonomous publish-cycle scheduler, and flip status to "active".

    Accepts an optional `{"persona": {"name", "domain"}}` body per the
    evaluator contract; when provided it overrides the persona.json
    defaults for this agent's name (domain is stored for future use).
    Returns ONLY `{"agentId": "..."}` — no extra fields.

    `start_scheduler()` is idempotent, so a repeat `/init` call
    (`get_or_create_agent` already returns the same row) is safe and
    never starts a second competing scheduler, and never exposes a
    separate manual-trigger endpoint.
    """
    persona_name = None
    if body is not None and body.persona is not None:
        persona_name = body.persona.name

    agent = get_or_create_agent(db, persona_name=persona_name)
    start_scheduler(agent.id)

    if agent.status != "active":
        agent.status = "active"
        db.commit()
        db.refresh(agent)

    return AgentInitResponse(agentId=agent.id)


@router.post("/stop")
def stop_agent(db: Session = Depends(get_db)):
    """Pause/stop the autonomous background scheduler and flip agent status to paused."""
    from app.services.scheduler import stop_scheduler
    stop_scheduler()

    agent = db.query(Agent).order_by(Agent.created_at.desc()).first()
    if agent:
        agent.status = "paused"
        db.commit()

    return {"status": "paused", "message": "Background publish scheduler paused."}


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    """Return the current agent status (active/paused/not_initialized) and nextRunTime.
    Used by the frontend to display status and countdown to next cycle.
    """
    from app.services.scheduler import get_next_run_time
    from app.services.topic_discovery import load_topic_sources

    agent = db.query(Agent).order_by(Agent.created_at.desc()).first()
    sources = [s["name"] for s in load_topic_sources()]

    if agent is None:
        return {"status": "not_initialized", "agentId": None, "nextRunTime": None, "sources": sources}
    return {
        "status": agent.status,
        "agentId": agent.id,
        "nextRunTime": get_next_run_time() if agent.status == "active" else None,
        "sources": sources,
    }


@router.get("/feed", response_model=FeedResponse)
def get_feed(agentId: str | None = None, db: Session = Depends(get_db)):
    """Return published posts, newest first, as `{"posts": [...]}`.

    Accepts an optional `agentId` query parameter matching the PRD specification
    `GET /api/agent/feed?agentId=abc-123`. If provided, filters by that agentId;
    otherwise returns posts for the latest agent.
    """
    if agentId:
        agent = db.query(Agent).filter_by(id=agentId).first()
    else:
        agent = db.query(Agent).order_by(Agent.created_at.desc()).first()

    if agent is None:
        return FeedResponse(posts=[])

    posts = (
        db.query(Post)
        .filter(Post.agent_id == agent.id)
        .order_by(Post.created_at.desc())
        .all()
    )

    feed_posts = []
    for post in posts:
        try:
            sources = json.loads(post.sources) if post.sources else []
        except (TypeError, ValueError):
            sources = []
        feed_posts.append(
            FeedPost(
                id=post.id,
                createdAt=post.created_at,
                title=post.title or "",
                text=post.content,
                rationale=post.rationale,
                sources=sources,
            )
        )

    return FeedResponse(posts=feed_posts)
