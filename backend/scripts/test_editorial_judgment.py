"""
Stage 14 verification — Editorial Judgment.

Runs against an in-memory SQLite DB with a `FakeProvider` (no network,
no real API key needed), following the same pattern as Stage 8's
`test_init_llm_wiring.py`. Confirms:
1. An ACCEPT response from the LLM is parsed correctly and creates NO
   `RejectedTopic` row.
2. A REJECT response is parsed correctly and creates a `RejectedTopic`
   row with the right fingerprint + reason.
3. Judging the same (or a reworded/reordered-title) candidate again
   short-circuits on the fingerprint match against `rejected_topics`
   and does NOT call the LLM a second time.
4. An unparseable LLM response fails closed (rejected), and is logged.
5. An LLM call that raises an exception fails closed (rejected), and
   is logged, without propagating the exception.
6. `judge_candidates()` processes a batch and returns one
   `JudgmentResult` per candidate, in order.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base  # noqa: E402
import app.models  # noqa: F401,E402  (register models on Base.metadata)
from app.models.rejected_topic import RejectedTopic  # noqa: E402
from app.services.editorial_judgment import judge_candidate, judge_candidates  # noqa: E402
from app.services.topic_discovery import TopicCandidate  # noqa: E402

AGENT_ID = "agent-1"


class _CallCounter:
    calls = 0


class ScriptedProvider:
    """Fake LLMProvider whose judge() returns a pre-scripted sequence
    of responses, one per call, so each test scenario is deterministic.
    """

    name = "scripted"

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError

    def judge(self, prompt: str, system: str | None = None) -> str:
        _CallCounter.calls += 1
        return self._responses.pop(0)

    def summarize(self, text: str, system: str | None = None) -> str:
        raise NotImplementedError


class RaisingProvider:
    """Fake LLMProvider whose judge() always raises."""

    name = "raising"

    def generate(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError

    def judge(self, prompt: str, system: str | None = None) -> str:
        _CallCounter.calls += 1
        raise RuntimeError("simulated provider outage")

    def summarize(self, text: str, system: str | None = None) -> str:
        raise NotImplementedError


def make_candidate(title, url="https://example.com/story", source_name="TechCrunch"):
    return TopicCandidate(title=title, url=url, source_name=source_name, category="industry")


def fresh_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def main() -> None:
    print("1. ACCEPT response is parsed correctly and logs no rejection...")
    db = fresh_db()
    candidate = make_candidate("OpenAI ships a new reasoning benchmark")
    provider = ScriptedProvider(["ACCEPT: Verifiable primary-source release, on-topic."])
    result = judge_candidate(db, AGENT_ID, candidate, llm_provider=provider)
    assert result.accepted is True
    assert "Verifiable primary-source" in result.reason
    assert db.query(RejectedTopic).count() == 0
    print("   OK")

    print("2. REJECT response is parsed and logged with fingerprint + reason...")
    db2 = fresh_db()
    candidate2 = make_candidate("Vague funding round rumor with no technical detail")
    provider2 = ScriptedProvider(["REJECT: No technical substance, funding news only."])
    result2 = judge_candidate(db2, AGENT_ID, candidate2, llm_provider=provider2)
    assert result2.accepted is False
    assert "No technical substance" in result2.reason
    rows = db2.query(RejectedTopic).all()
    assert len(rows) == 1
    assert rows[0].fingerprint == result2.fingerprint
    assert rows[0].agent_id == AGENT_ID
    print("   OK")

    print("3. Re-judging a reworded/reordered-title near-duplicate of a rejected topic...")
    _CallCounter.calls = 0
    reworded = make_candidate(
        "Funding round rumor: vague, with no technical detail",  # same keywords, reordered
        url="https://example.com/different-url",  # different URL, same story
    )
    provider3 = ScriptedProvider(["ACCEPT: should never be reached"])
    result3 = judge_candidate(db2, AGENT_ID, reworded, llm_provider=provider3)
    assert result3.accepted is False
    assert "Previously rejected" in result3.reason
    assert _CallCounter.calls == 0, "LLM should not be called for an already-rejected fingerprint"
    assert db2.query(RejectedTopic).count() == 1, "no duplicate RejectedTopic row should be created"
    print("   OK — fingerprint short-circuit skipped the LLM call, no duplicate row")

    print("4. Unparseable LLM response fails closed (rejected)...")
    db4 = fresh_db()
    candidate4 = make_candidate("Some ambiguous story")
    provider4 = ScriptedProvider(["I'm not sure, maybe?"])
    result4 = judge_candidate(db4, AGENT_ID, candidate4, llm_provider=provider4)
    assert result4.accepted is False
    assert "Unparseable" in result4.reason
    assert db4.query(RejectedTopic).count() == 1
    print("   OK")

    print("5. LLM call raising an exception fails closed without propagating...")
    db5 = fresh_db()
    candidate5 = make_candidate("Story during a provider outage")
    result5 = judge_candidate(db5, AGENT_ID, candidate5, llm_provider=RaisingProvider())
    assert result5.accepted is False
    assert "judgment call failed" in result5.reason
    assert db5.query(RejectedTopic).count() == 1
    print("   OK — no exception propagated, rejection logged")

    print("6. judge_candidates() processes a batch in order...")
    db6 = fresh_db()
    batch = [make_candidate("Story A", url="https://example.com/a"),
             make_candidate("Story B", url="https://example.com/b")]
    provider6 = ScriptedProvider(["ACCEPT: fine.", "REJECT: not on-topic."])
    results = judge_candidates(db6, AGENT_ID, batch, llm_provider=provider6)
    assert len(results) == 2
    assert results[0].accepted is True and results[0].candidate.title == "Story A"
    assert results[1].accepted is False and results[1].candidate.title == "Story B"
    print("   OK")

    print("\nAll Stage 14 checks passed.")


if __name__ == "__main__":
    main()
