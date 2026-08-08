"""
Agent routes — POST /api/agent/init, GET /api/agent/feed.

Stage 19 adds `/feed`, the second and last public endpoint the PRD
allows (§5). It deliberately does no filtering/pagination/query params
— out of scope per §2/§4 (no dashboard, no settings) — it just returns
every published post for the single agent, newest first, which is all
the Feed page needs and all the evaluator's repeated polling checks
for (§9: "feed grows with no human prompts").
"""
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.agent import Agent
from app.models.post import Post
from app.schemas.agent import AgentInitResponse, FeedPost, FeedResponse
from app.services.agent_service import get_or_create_agent
from app.services.scheduler import start_scheduler

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/init", response_model=AgentInitResponse)
def init_agent(db: Session = Depends(get_db)):
    """Create the agent row (or return the existing one), start the
    autonomous publish-cycle scheduler, and flip status to "active".

    Stage 8 wired in LLM-generated persona descriptions on first call.
    Stage 10 added Breeth namespace creation on first call too
    (agent_service._create_breeth_namespace). Stage 18 adds the final
    piece: starting the Stage 18 scheduler, which is what actually
    makes the feed grow with zero further human prompting, per the
    PRD's core success criterion. `start_scheduler()` is idempotent,
    so a repeat `/init` call (get_or_create_agent already returns the
    same row) is safe and never starts a second competing scheduler.
    """
    agent = get_or_create_agent(db)
    start_scheduler(agent.id)

    if agent.status != "active":
        agent.status = "active"
        db.commit()
        db.refresh(agent)

    return AgentInitResponse(
        agentId=agent.id,
        status=agent.status,
        personaName=agent.persona_name,
        personaDescription=agent.persona_description,
        breethAgentRef=agent.breeth_agent_ref,
        createdAt=agent.created_at,
    )


@router.get("/feed", response_model=FeedResponse)
def get_feed(db: Session = Depends(get_db)):
    """Return every published post, newest first.

    Before `/init` has ever been called there's no agent row yet — the
    PRD doesn't say the evaluator waits for init before its first feed
    poll, so this returns an empty feed (`agentId`/`personaName`/
    `status` all `None`, `posts: []`) rather than a 404; an empty feed
    is a perfectly valid, renderable state for the Feed page (matches
    Stage 3's existing empty-state UI) and keeps this endpoint
    side-effect-free (it must never itself create the agent — only
    `/init` does that, per §5's "only 2 public endpoints" split of
    responsibilities).

    `Post.sources` is stored as a JSON-encoded string column (Stage 2);
    `json.loads()` here is what turns it back into the `list[str]`
    `FeedPost.sources` expects, so a malformed/missing value can't
    crash the whole feed for every other post — an unparseable row
    just falls back to `[]` for that one post's sources.
    """
    agent = db.query(Agent).order_by(Agent.created_at.desc()).first()
    if agent is None:
        return FeedResponse()

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
                title=post.title,
                content=post.content,
                rationale=post.rationale,
                sources=sources,
                createdAt=post.created_at,
            )
        )

    return FeedResponse(
        agentId=agent.id,
        personaName=agent.persona_name,
        status=agent.status,
        posts=feed_posts,
    )
