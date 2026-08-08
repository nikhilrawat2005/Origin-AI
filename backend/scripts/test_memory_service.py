"""
Stage 15 verification — Memory Service (Breeth dedup).

Runs against an in-memory SQLite DB with a `FakeBreethClient` (no
network, no real API key needed), following the same pattern as Stage
14's `test_editorial_judgment.py`. Confirms:
1. A candidate whose fingerprint matches an existing `Post` is flagged
   duplicate via Layer 1 (local, no Breeth call made at all).
2. A genuinely new candidate, with Breeth returning no matching edges,
   passes through as not-a-duplicate ("breeth_search" in checked_via).
3. A candidate that IS semantically similar to a Breeth edge (high
   keyword overlap) is flagged duplicate via Layer 2, even though no
   local Post exists for it.
4. A Breeth call that raises falls back to the local mirror
   (`breeth_mirror_facts`) instead of raising or blindly rejecting —
   and when the mirror is empty, the candidate passes through
   (fail-open).
5. A Breeth failure + a matching synced mirror fact IS flagged
   duplicate via the fallback path.
6. An agent with no `breeth_agent_ref` yet skips the semantic check
   cleanly (no crash, not-a-duplicate) without calling Breeth at all.
7. `check_memory_batch()` processes a batch and returns one
   `MemoryCheckResult` per candidate, in order, reusing one client.
"""
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
from app.services.fingerprint import fingerprint_candidate  # noqa: E402
from app.services.memory_service import check_memory, check_memory_batch  # noqa: E402
from app.services.topic_discovery import TopicCandidate  # noqa: E402

AGENT_ID = "agent-1"


class _CallCounter:
    calls = 0


class FakeBreethClient:
    """Fake BreethClient whose search() either returns a scripted
    response dict or raises, controlled per-instance.
    """

    def __init__(self, response: dict | None = None, raises: bool = False):
        self._response = response if response is not None else {"edges": []}
        self._raises = raises

    def search(self, query: str, group_id: str = "default", limit: int = 10) -> dict:
        _CallCounter.calls += 1
        if self._raises:
            raise RuntimeError("simulated Breeth outage")
        return self._response


def make_candidate(title, url="https://example.com/story", source_name="TechCrunch", summary=None):
    return TopicCandidate(
        title=title, url=url, source_name=source_name, category="industry", summary=summary
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
    print("1. Fingerprint match against an existing Post is flagged duplicate (Layer 1)...")
    db = fresh_db()
    agent = make_agent(db)
    candidate = make_candidate("OpenAI ships a new reasoning benchmark")
    fp = fingerprint_candidate(candidate)
    db.add(Post(agent_id=AGENT_ID, title="OpenAI ships new benchmark", content="...",
                 rationale="...", sources="[]", fingerprint=fp))
    db.commit()
    _CallCounter.calls = 0
    client = FakeBreethClient()
    result = check_memory(db, agent, candidate, breeth_client=client)
    assert result.is_duplicate is True
    assert "Already published" in result.reason
    assert result.checked_via == ["posts_table"]
    assert _CallCounter.calls == 0, "Breeth should not be called when Layer 1 already matched"
    print("   OK — no Breeth call made")

    print("2. Genuinely new candidate, Breeth returns no matching edges...")
    db2 = fresh_db()
    agent2 = make_agent(db2)
    candidate2 = make_candidate("A brand new story nobody has covered")
    client2 = FakeBreethClient(response={"edges": [
        {"subject": "Aether", "predicate": "published", "object": "Completely unrelated other story about chips"}
    ]})
    result2 = check_memory(db2, agent2, candidate2, breeth_client=client2)
    assert result2.is_duplicate is False
    assert result2.checked_via == ["posts_table", "breeth_search"]
    print("   OK")

    print("3. Semantically similar Breeth edge flags duplicate (Layer 2)...")
    db3 = fresh_db()
    agent3 = make_agent(db3)
    candidate3 = make_candidate(
        "Anthropic releases new Claude reasoning benchmark results",
        summary="A detailed look at the new benchmark numbers.",
    )
    client3 = FakeBreethClient(response={"edges": [
        {"subject": "Aether", "predicate": "published",
         "object": "Anthropic Claude reasoning benchmark results release"}
    ]})
    result3 = check_memory(db3, agent3, candidate3, breeth_client=client3)
    assert result3.is_duplicate is True
    assert "Possible duplicate" in result3.reason
    assert result3.checked_via == ["posts_table", "breeth_search"]
    print("   OK")

    print("4. Breeth call raises -> falls back to local mirror, empty mirror -> fail-open...")
    db4 = fresh_db()
    agent4 = make_agent(db4)
    candidate4 = make_candidate("Some novel story during a Breeth outage")
    client4 = FakeBreethClient(raises=True)
    result4 = check_memory(db4, agent4, candidate4, breeth_client=client4)
    assert result4.is_duplicate is False
    assert result4.checked_via == ["posts_table", "breeth_mirror_fallback"]
    print("   OK — Breeth outage did not block a novel candidate")

    print("5. Breeth raises + matching synced mirror fact IS flagged duplicate...")
    db5 = fresh_db()
    agent5 = make_agent(db5)
    candidate5 = make_candidate("Google announces Gemini model update")
    db5.add(BreethMirrorFact(agent_id=AGENT_ID, group_id="ns-agent-1", subject="Aether",
                               predicate="published", object="Google Gemini model update announcement",
                               synced=True))
    db5.commit()
    client5 = FakeBreethClient(raises=True)
    result5 = check_memory(db5, agent5, candidate5, breeth_client=client5)
    assert result5.is_duplicate is True
    assert "local Breeth mirror fallback" in result5.reason
    assert result5.checked_via == ["posts_table", "breeth_mirror_fallback"]
    print("   OK")

    print("6. Agent with no breeth_agent_ref yet skips semantic check, no Breeth call...")
    db6 = fresh_db()
    agent6 = make_agent(db6, breeth_agent_ref=None)
    candidate6 = make_candidate("A story before the namespace exists")
    _CallCounter.calls = 0
    client6 = FakeBreethClient()
    result6 = check_memory(db6, agent6, candidate6, breeth_client=client6)
    assert result6.is_duplicate is False
    assert "no Breeth namespace" in result6.reason
    assert _CallCounter.calls == 0
    print("   OK")

    print("7. check_memory_batch() processes a batch in order...")
    db7 = fresh_db()
    agent7 = make_agent(db7)
    batch = [make_candidate("Story A", url="https://example.com/a"),
             make_candidate("Story B", url="https://example.com/b")]
    client7 = FakeBreethClient(response={"edges": []})
    results = check_memory_batch(db7, agent7, batch, breeth_client=client7)
    assert len(results) == 2
    assert results[0].candidate.title == "Story A" and results[0].is_duplicate is False
    assert results[1].candidate.title == "Story B" and results[1].is_duplicate is False
    print("   OK")

    print("\nAll Stage 15 checks passed.")


if __name__ == "__main__":
    main()
