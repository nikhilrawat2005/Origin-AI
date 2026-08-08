"""
Stage 18 verification — Scheduler Wiring.

Exercises `run_publish_cycle()` (the pure, non-APScheduler part of
`scheduler.py`) against an in-memory DB with every pipeline stage
(discovery, judgment, memory check, post writer, publisher)
monkeypatched out — this stage isn't re-testing Stages 12/14/15/16/17
themselves (each already has its own dedicated script), it's testing
that `scheduler.py` chains their outputs into each other correctly
and degrades safely when a stage returns nothing or fails. Also
exercises `start_scheduler()` / `stop_scheduler()`'s idempotency
without ever letting a real APScheduler tick actually fire (interval
is left at whatever `.env`/default resolves to; the test only checks
that a second `start_scheduler()` call is a no-op object-identity-wise
and that `stop_scheduler()` clears the guard).

Confirms:
1. No candidates discovered -> returns 0, nothing downstream called.
2. Candidates discovered but none accepted -> returns 0, memory check
   never called.
3. Accepted candidates but all flagged as memory duplicates -> returns
   0, post writer never called.
4. Mixed batch: one memory-duplicate (skipped), one PostWriteError
   (skipped, doesn't abort the cycle), one clean success -> returns 1,
   publish_post called exactly once, with the successful WrittenPost.
5. Discovery raising an unexpected exception -> caught, returns 0,
   does not propagate out of run_publish_cycle().
6. start_scheduler() is idempotent: a second call returns the exact
   same scheduler object rather than creating a new one; stop_scheduler()
   clears the module-level guard so a later start creates a fresh one.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base  # noqa: E402
import app.models  # noqa: F401,E402  (register models on Base.metadata)
from app.models.agent import Agent  # noqa: E402
from app.services.editorial_judgment import JudgmentResult  # noqa: E402
from app.services.memory_service import MemoryCheckResult  # noqa: E402
from app.services.post_writer import PostWriteError, WrittenPost  # noqa: E402
from app.services.topic_discovery import TopicCandidate  # noqa: E402
from app.services import scheduler as scheduler_module  # noqa: E402

AGENT_ID = "agent-1"


def fresh_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def make_agent(db):
    agent = Agent(id=AGENT_ID, persona_name="Aether", breeth_agent_ref="ns-agent-1", status="active")
    db.add(agent)
    db.commit()
    return agent


def make_candidate(title):
    return TopicCandidate(title=title, url=f"https://example.com/{title}", source_name="TechCrunch", category="industry")


def make_judgment(candidate, accepted=True, fingerprint=None):
    return JudgmentResult(
        candidate=candidate,
        fingerprint=fingerprint or f"fp-{candidate.title}",
        accepted=accepted,
        reason="Accepted for test." if accepted else "Rejected for test.",
    )


def make_memory_result(candidate, is_duplicate, fingerprint=None):
    return MemoryCheckResult(
        candidate=candidate,
        fingerprint=fingerprint or f"fp-{candidate.title}",
        is_duplicate=is_duplicate,
        reason="test",
        checked_via=["posts_table"],
    )


def main() -> None:
    print("1. No candidates discovered -> returns 0, nothing downstream called...")
    db = fresh_db()
    agent = make_agent(db)
    with patch.object(scheduler_module, "discover_new_topics", return_value=[]) as m_discover, \
         patch.object(scheduler_module, "judge_candidates") as m_judge:
        result = scheduler_module.run_publish_cycle(db, agent)
    assert result == 0
    m_discover.assert_called_once()
    m_judge.assert_not_called()
    print("   OK")

    print("2. Candidates discovered, none accepted -> returns 0, memory check never called...")
    db = fresh_db()
    agent = make_agent(db)
    candidates = [make_candidate("Story A")]
    judgments = [make_judgment(candidates[0], accepted=False)]
    with patch.object(scheduler_module, "discover_new_topics", return_value=candidates), \
         patch.object(scheduler_module, "judge_candidates", return_value=judgments), \
         patch.object(scheduler_module, "check_memory_batch") as m_memory:
        result = scheduler_module.run_publish_cycle(db, agent)
    assert result == 0
    m_memory.assert_not_called()
    print("   OK")

    print("3. Accepted candidates, all memory duplicates -> returns 0, post writer never called...")
    db = fresh_db()
    agent = make_agent(db)
    candidates = [make_candidate("Story B")]
    judgments = [make_judgment(candidates[0], accepted=True)]
    memory_results = [make_memory_result(candidates[0], is_duplicate=True)]
    with patch.object(scheduler_module, "discover_new_topics", return_value=candidates), \
         patch.object(scheduler_module, "judge_candidates", return_value=judgments), \
         patch.object(scheduler_module, "check_memory_batch", return_value=memory_results), \
         patch.object(scheduler_module, "write_post") as m_write:
        result = scheduler_module.run_publish_cycle(db, agent)
    assert result == 0
    m_write.assert_not_called()
    print("   OK")

    print("4. Mixed batch: duplicate skipped, PostWriteError skipped, one success published...")
    db = fresh_db()
    agent = make_agent(db)
    c_dup = make_candidate("Duplicate Story")
    c_fail = make_candidate("Story That Fails Writing")
    c_ok = make_candidate("Story That Publishes")
    candidates = [c_dup, c_fail, c_ok]
    judgments = [make_judgment(c) for c in candidates]
    memory_results = [
        make_memory_result(c_dup, is_duplicate=True),
        make_memory_result(c_fail, is_duplicate=False),
        make_memory_result(c_ok, is_duplicate=False),
    ]
    written_ok = WrittenPost(
        candidate=c_ok, fingerprint="fp-ok", title="Published Title",
        content="body", rationale="why", sources=[c_ok.url],
    )

    def fake_write_post(judgment, llm_provider=None):
        if judgment.candidate is c_fail:
            raise PostWriteError("simulated generation failure")
        return written_ok

    published_calls = []

    def fake_publish_post(db_, agent_, written_post, breeth_client=None):
        published_calls.append(written_post)
        return object()

    with patch.object(scheduler_module, "discover_new_topics", return_value=candidates), \
         patch.object(scheduler_module, "judge_candidates", return_value=judgments), \
         patch.object(scheduler_module, "check_memory_batch", return_value=memory_results), \
         patch.object(scheduler_module, "write_post", side_effect=fake_write_post), \
         patch.object(scheduler_module, "publish_post", side_effect=fake_publish_post):
        result = scheduler_module.run_publish_cycle(db, agent)
    assert result == 1, f"expected 1 published, got {result}"
    assert len(published_calls) == 1
    assert published_calls[0] is written_ok
    print("   OK — one duplicate skipped, one write failure skipped, one published")

    print("5. Discovery raises unexpectedly -> caught, returns 0, does not propagate...")
    db = fresh_db()
    agent = make_agent(db)
    with patch.object(scheduler_module, "discover_new_topics", side_effect=RuntimeError("boom")):
        result = scheduler_module.run_publish_cycle(db, agent)
    assert result == 0
    print("   OK — exception contained, cycle returned 0 instead of raising")

    print("6. start_scheduler() is idempotent; stop_scheduler() clears the guard...")
    scheduler_module.stop_scheduler()  # ensure clean slate regardless of prior state
    assert not scheduler_module.is_running()
    s1 = scheduler_module.start_scheduler(AGENT_ID)
    assert scheduler_module.is_running()
    s2 = scheduler_module.start_scheduler(AGENT_ID)
    assert s1 is s2, "second start_scheduler() call should return the same instance"
    scheduler_module.stop_scheduler()
    assert not scheduler_module.is_running()
    s3 = scheduler_module.start_scheduler(AGENT_ID)
    assert s3 is not s1, "after stop_scheduler(), a new start should create a fresh instance"
    scheduler_module.stop_scheduler()
    print("   OK")

    print("\nAll Stage 18 checks passed.")


if __name__ == "__main__":
    main()
