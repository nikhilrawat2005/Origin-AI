"""
Stage 17 verification — Publisher.

Runs against an in-memory SQLite DB with a `FakeBreethClient` (no
network, no real API key needed), following the same pattern as
Stage 15's `test_memory_service.py`. Confirms:
1. `publish_post()` persists a `Post` row with the right fields
   (title, content, rationale, JSON-encoded sources, fingerprint,
   agent_id) and returns it committed with a generated id.
2. A successful Breeth write creates a `synced=True` mirror fact whose
   `object` is the post's title.
3. A Breeth write that raises still persists the `Post` row and
   creates a `synced=False` mirror fact (best-effort, doesn't block
   publishing).
4. An agent with no `breeth_agent_ref` yet skips the remote call
   entirely but still writes a local mirror fact (group_id
   "unassigned"), and the `Post` row is still created.
5. Publishing a second, distinct post for the same agent creates a
   second `Post` row and a second mirror fact — no accidental
   dedup/overwrite at this layer (that's Stages 14/15's job, not
   this stage's).
6. The persisted post's fingerprint round-trips correctly, so a
   future Stage 15 `check_memory()` call against the same fingerprint
   would find it (exercised directly here without importing memory
   service, to keep this script's fixtures self-contained).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base  # noqa: E402
import app.models  # noqa: F401,E402  (register models on Base.metadata)
from app.models.agent import Agent  # noqa: E402
from app.models.breeth_mirror import BreethMirrorFact  # noqa: E402
from app.models.post import Post  # noqa: E402
from app.services.post_writer import WrittenPost  # noqa: E402
from app.services.publisher import publish_post  # noqa: E402
from app.services.topic_discovery import TopicCandidate  # noqa: E402

AGENT_ID = "agent-1"


class _CallCounter:
    calls = 0


class FakeBreethClient:
    """Fake BreethClient whose write_fact() either succeeds silently
    or raises, controlled per-instance.
    """

    def __init__(self, raises: bool = False):
        self._raises = raises

    def write_fact(self, subject, predicate, object_, group_id="default", extract_intent=False):
        _CallCounter.calls += 1
        if self._raises:
            raise RuntimeError("simulated Breeth outage")
        return {"ok": True}


def make_written_post(title="New Benchmark Puts Reasoning Claims to the Test", fingerprint="fp-abc"):
    candidate = TopicCandidate(
        title=title, url="https://example.com/story", source_name="TechCrunch", category="industry"
    )
    return WrittenPost(
        candidate=candidate,
        fingerprint=fingerprint,
        title=title,
        content="OpenAI released a new reasoning benchmark this week...",
        rationale="Primary-source release with reproducible numbers.",
        sources=[candidate.url],
    )


def fresh_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def make_agent(db, breeth_agent_ref="ns-agent-1"):
    agent = Agent(id=AGENT_ID, persona_name="Aether", breeth_agent_ref=breeth_agent_ref, status="active")
    db.add(agent)
    db.commit()
    return agent


def main() -> None:
    print("1. publish_post() persists a Post row with the right fields...")
    db = fresh_db()
    agent = make_agent(db)
    wp = make_written_post()
    post = publish_post(db, agent, wp, breeth_client=FakeBreethClient())
    assert post.id is not None
    assert post.agent_id == AGENT_ID
    assert post.title == wp.title
    assert post.content == wp.content
    assert post.rationale == wp.rationale
    assert json.loads(post.sources) == wp.sources
    assert post.fingerprint == wp.fingerprint
    assert db.query(Post).count() == 1
    print("   OK")

    print("2. Successful Breeth write creates a synced=True mirror fact...")
    facts = db.query(BreethMirrorFact).filter_by(agent_id=AGENT_ID, predicate="published").all()
    assert len(facts) == 1
    assert facts[0].synced is True
    assert facts[0].object == wp.title
    assert facts[0].group_id == "ns-agent-1"
    print("   OK")

    print("3. Breeth write raises -> Post still persisted, mirror fact synced=False...")
    db3 = fresh_db()
    agent3 = make_agent(db3)
    wp3 = make_written_post(title="A story published during a Breeth outage", fingerprint="fp-outage")
    post3 = publish_post(db3, agent3, wp3, breeth_client=FakeBreethClient(raises=True))
    assert post3.id is not None
    assert db3.query(Post).count() == 1
    facts3 = db3.query(BreethMirrorFact).filter_by(agent_id=AGENT_ID, predicate="published").all()
    assert len(facts3) == 1
    assert facts3[0].synced is False
    print("   OK — publishing not blocked by Breeth outage")

    print("4. Agent with no breeth_agent_ref skips the remote call, still mirrors + persists...")
    db4 = fresh_db()
    agent4 = make_agent(db4, breeth_agent_ref=None)
    wp4 = make_written_post(title="A story before the namespace exists", fingerprint="fp-no-ns")
    _CallCounter.calls = 0
    client4 = FakeBreethClient()
    post4 = publish_post(db4, agent4, wp4, breeth_client=client4)
    assert post4.id is not None
    assert _CallCounter.calls == 0, "Breeth should never be called with no namespace"
    facts4 = db4.query(BreethMirrorFact).filter_by(agent_id=AGENT_ID, predicate="published").all()
    assert len(facts4) == 1
    assert facts4[0].synced is False
    assert facts4[0].group_id == "unassigned"
    print("   OK — no Breeth call made, local mirror still written")

    print("5. A second, distinct post creates a second Post row and mirror fact...")
    db5 = fresh_db()
    agent5 = make_agent(db5)
    client5 = FakeBreethClient()
    post_a = publish_post(db5, agent5, make_written_post(title="Story A", fingerprint="fp-a"), breeth_client=client5)
    post_b = publish_post(db5, agent5, make_written_post(title="Story B", fingerprint="fp-b"), breeth_client=client5)
    assert post_a.id != post_b.id
    assert db5.query(Post).count() == 2
    assert db5.query(BreethMirrorFact).filter_by(agent_id=AGENT_ID, predicate="published").count() == 2
    print("   OK")

    print("6. Persisted fingerprint round-trips for a future dedup lookup...")
    db6 = fresh_db()
    agent6 = make_agent(db6)
    wp6 = make_written_post(title="Story to be found later", fingerprint="fp-lookup-me")
    publish_post(db6, agent6, wp6, breeth_client=FakeBreethClient())
    found = db6.query(Post).filter_by(agent_id=AGENT_ID, fingerprint="fp-lookup-me").first()
    assert found is not None
    assert found.title == "Story to be found later"
    print("   OK")

    print("\nAll Stage 17 checks passed.")


if __name__ == "__main__":
    main()
