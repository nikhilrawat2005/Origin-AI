"""
Stage 19 verification — GET /api/agent/feed.

Runs against an in-memory SQLite DB via FastAPI's TestClient, overriding
`get_db` the same way FastAPI's own docs recommend for tests (no real
`aether.db` file touched). Confirms:
1. Before any agent exists, `/feed` returns 200 with an empty feed
   (`agentId`/`personaName`/`status` all null, `posts: []`) rather than
   a 404 or 500 — matches the route's documented "no side effects, no
   agent required" behavior.
2. With an agent and zero posts, `/feed` returns the agent's identity
   fields populated but `posts: []`.
3. With posts, `/feed` returns them newest-first with every field the
   PRD's Feed Page needs: `id`, `title`, `content`, `rationale`,
   `sources` (correctly JSON-decoded back into a list), `createdAt`.
4. A post with a malformed `sources` string doesn't crash the whole
   feed — it falls back to `[]` for that post only, other posts are
   unaffected.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
import app.models  # noqa: F401,E402  (register models on Base.metadata)
from app.models.agent import Agent  # noqa: E402
from app.models.post import Post  # noqa: E402
from app.main import app  # noqa: E402

# StaticPool: TestClient calls run in a worker thread, and a bare
# ":memory:" engine hands each new connection a *fresh* empty DB
# unless every connection is forced through the same one (same
# pattern Stage 15/17's own in-memory test fixtures avoid by using a
# real temp-file DB; StaticPool is the equivalent fix for TestClient
# specifically, which owns connection lifecycle itself).
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def test_empty_feed_before_any_agent():
    resp = client.get("/api/agent/feed")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["agentId"] is None
    assert body["personaName"] is None
    assert body["status"] is None
    assert body["posts"] == []
    print("PASS: empty feed before any agent exists")


def test_feed_with_agent_no_posts():
    db = TestingSessionLocal()
    agent = Agent(persona_name="Aether", status="active")
    db.add(agent)
    db.commit()
    db.refresh(agent)
    agent_id = agent.id
    db.close()

    resp = client.get("/api/agent/feed")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["agentId"] == agent_id
    assert body["personaName"] == "Aether"
    assert body["status"] == "active"
    assert body["posts"] == []
    print("PASS: agent with zero posts returns identity + empty posts")


def test_feed_with_posts_newest_first_and_sources_decoded():
    db = TestingSessionLocal()
    agent = db.query(Agent).order_by(Agent.created_at.desc()).first()

    older = Post(
        agent_id=agent.id,
        title="Older Post",
        content="Older content.",
        rationale="Older rationale.",
        sources='["https://example.com/a"]',
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    newer = Post(
        agent_id=agent.id,
        title="Newer Post",
        content="Newer content.",
        rationale="Newer rationale.",
        sources='["https://example.com/b", "https://example.com/c"]',
        created_at=datetime.now(timezone.utc),
    )
    malformed = Post(
        agent_id=agent.id,
        title="Malformed Sources Post",
        content="Still has content.",
        rationale="Still has rationale.",
        sources="not valid json",
        created_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    db.add_all([older, newer, malformed])
    db.commit()
    db.close()

    resp = client.get("/api/agent/feed")
    assert resp.status_code == 200, resp.text
    posts = resp.json()["posts"]
    assert len(posts) == 3

    titles = [p["title"] for p in posts]
    assert titles == ["Malformed Sources Post", "Newer Post", "Older Post"], titles

    newer_post = posts[1]
    assert newer_post["sources"] == [
        "https://example.com/b",
        "https://example.com/c",
    ]
    assert newer_post["rationale"] == "Newer rationale."
    assert "id" in newer_post and "createdAt" in newer_post

    malformed_post = posts[0]
    assert malformed_post["sources"] == []
    print("PASS: posts returned newest-first with sources decoded; malformed sources fall back to []")


if __name__ == "__main__":
    test_empty_feed_before_any_agent()
    test_feed_with_agent_no_posts()
    test_feed_with_posts_newest_first_and_sources_decoded()
    print("\nAll Stage 19 feed endpoint checks passed.")
