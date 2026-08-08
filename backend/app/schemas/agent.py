"""
Response schema(s) for the agent endpoints.

Stage 8 added `personaDescription` once `/init` started generating one
via the LLM. Stage 10 adds `breethAgentRef` now that `/init` also
establishes the agent's Breeth namespace (agent_service.
_create_breeth_namespace) — always populated on creation, since the
group_id is locally derived rather than something Breeth returns (see
that function's docstring for why it's set even when the underlying
remote write fails). Stage 19 adds `FeedPost`/`FeedResponse` for
`GET /api/agent/feed` — this is the "exact PRD JSON shape" referenced
in `routes/agent.py`: the PRD's Feed Page needs exactly "Generated
Posts, Created Time, Rationale, Sources" (PROJECT_STATUS.md §4), so
`FeedPost` carries precisely those fields (plus `id`/`title` so the
frontend has something to key/render on) and nothing else — no author,
no tags, no engagement metrics, matching §2's explicit out-of-scope
list. `sources` is typed `list[str]` here even though `Post.sources`
is stored as a JSON string column — the route is responsible for the
`json.loads()` conversion so this schema stays a clean, JSON-native
contract for the frontend.
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


class FeedPost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    rationale: str
    sources: list[str]
    createdAt: datetime


class FeedResponse(BaseModel):
    """Whole-feed response: identifies which agent/persona the posts
    belong to (the Landing page's "Agent Status" and Feed page's
    header both need this) plus the posts themselves, newest first —
    matching how a reader expects a feed to read top-to-bottom.
    """

    model_config = ConfigDict(from_attributes=True)

    agentId: str | None = None
    personaName: str | None = None
    status: str | None = None
    posts: list[FeedPost] = []
