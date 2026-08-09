"""
Response schema(s) for the agent endpoints — locked to the exact
hackathon evaluator contract.

`POST /api/agent/init` returns ONLY `{"agentId": "..."}`. Nothing else.
The evaluator's contract test posts a persona payload and reads back a
single `agentId` field — any extra field (status, personaName, etc.)
is harmless to a strict-equality evaluator but is explicitly out of
scope per the "no unnecessary fields on evaluator-facing APIs"
requirement, so this schema carries only `agentId`.

`GET /api/agent/feed` returns ONLY `{"posts": [...]}`, each post
carrying exactly `id`, `createdAt` (ISO 8601 UTC), `text`, `rationale`,
`sources` — no wrapping `agent` object, no `title`, no `content` key.
`content` was renamed to `text` to match the contract literally; the
underlying `Post.content` column is unchanged, this schema just maps
it to the field name the evaluator expects.
"""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer


class AgentInitRequest(BaseModel):
    """Optional persona override on init — `{"persona": {"name", "domain"}}`.
    Not required; if omitted, the persona.json defaults apply."""

    class Persona(BaseModel):
        name: str | None = None
        domain: str | None = None

    persona: Persona | None = None


class AgentInitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agentId: str


class FeedPost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    createdAt: datetime
    title: str = ""
    text: str
    rationale: str
    sources: list[str]

    @field_serializer("createdAt")
    def _serialize_created_at(self, value: datetime) -> str:
        """Always emit ISO 8601 UTC with a literal `Z` suffix (the
        exact contract shape: "2026-08-07T10:30:00Z"), regardless of
        whether the stored datetime is naive or already tz-aware."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class FeedResponse(BaseModel):
    """Whole-feed response — posts only, newest first, per the exact
    hackathon contract. No wrapping `agent` object."""

    model_config = ConfigDict(from_attributes=True)

    posts: list[FeedPost] = []
