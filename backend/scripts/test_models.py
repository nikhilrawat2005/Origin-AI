"""
Standalone manual test for Stage 2 — Database Models.

Not part of the app runtime. Run directly to verify:
  - All tables get created from the models
  - A row can be inserted and read back for each table

Usage:
    cd backend
    python -m scripts.test_models
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point this test run at its own throwaway SQLite file (not the app's
# default aether.db) before app.core.config reads the environment.
test_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_stage2.db")
test_db_path = os.path.abspath(test_db_path)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

from app.core.database import Base, engine, SessionLocal, init_db  # noqa: E402
from app.models import Agent, Post, RejectedTopic, SourceCache  # noqa: E402


def run():
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("Creating tables...")
    init_db()
    table_names = list(Base.metadata.tables.keys())
    print(f"Tables created: {table_names}")
    assert set(table_names) == {"agents", "posts", "rejected_topics", "sources_cache"}

    db = SessionLocal()
    try:
        agent = Agent(
            persona_name="Aether",
            persona_description="An autonomous AI technology research persona.",
            status="active",
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        print(f"Inserted agent: {agent.id} ({agent.persona_name}, {agent.status})")

        post = Post(
            agent_id=agent.id,
            title="Test Post",
            content="This is a test post body.",
            rationale="Testing that the posts table works end to end.",
            sources=json.dumps(["https://example.com/article"]),
            fingerprint="test-fingerprint-1",
        )
        db.add(post)

        rejected = RejectedTopic(
            agent_id=agent.id,
            title="A topic that was rejected",
            source="hackernews",
            fingerprint="rejected-fingerprint-1",
            reason="Not sufficiently novel — already covered similar ground.",
        )
        db.add(rejected)

        cache_entry = SourceCache(
            source_name="hackernews",
            url="https://news.ycombinator.com/item?id=1",
            title="Some raw candidate topic",
            raw_summary="Raw summary text from the source.",
            content_hash="abc123hash",
        )
        db.add(cache_entry)

        db.commit()

        # Read back
        assert db.query(Post).filter_by(agent_id=agent.id).count() == 1
        assert db.query(RejectedTopic).filter_by(agent_id=agent.id).count() == 1
        assert db.query(SourceCache).filter_by(content_hash="abc123hash").count() == 1

        print("Post round-trip OK.")
        print("RejectedTopic round-trip OK.")
        print("SourceCache round-trip OK.")
        print("\nStage 2 model test PASSED.")
    finally:
        db.close()
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


if __name__ == "__main__":
    run()
