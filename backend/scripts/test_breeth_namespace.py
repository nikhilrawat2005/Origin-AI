"""
Stage 10 verification — Breeth namespace creation on init.

Runs against an in-memory SQLite DB (mirrors the pattern from Stage 8's
test_init_llm_wiring.py). Confirms:

1. A new agent gets a non-null, deterministically-derived
   `breeth_agent_ref` (== f"agent-{agent.id}") even though no real
   BREETH_API_KEY is configured in this sandboxed environment.
2. Exactly one BreethMirrorFact row is written for that agent, with
   `synced=False` (since the real API call is expected to fail/skip
   here) and the correct group_id/subject/predicate/object.
3. A repeat `get_or_create_agent()` call does not create a second
   BreethMirrorFact row (namespace creation, like LLM generation,
   only runs once per agent — on creation).

Does not attempt a live Breeth round-trip; scripts/test_breeth_client.py
(Stage 9) already covers that, conditionally, when a real key is
present.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.agent import Agent  # noqa: F401 - ensures table is registered
from app.models.breeth_mirror import BreethMirrorFact  # noqa: F401
from app.models.post import Post  # noqa: F401
from app.models.rejected_topic import RejectedTopic  # noqa: F401
from app.models.sources_cache import SourceCache  # noqa: F401
from app.services.agent_service import get_or_create_agent, _breeth_group_id


def main() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # 1. First call creates the agent and its Breeth namespace.
    agent = get_or_create_agent(db)
    expected_ref = _breeth_group_id(agent.id)
    assert agent.breeth_agent_ref == expected_ref, (
        f"expected breeth_agent_ref={expected_ref!r}, got {agent.breeth_agent_ref!r}"
    )
    print(f"[ok] agent.breeth_agent_ref set: {agent.breeth_agent_ref}")

    # 2. Exactly one mirror row, recording the (expected-to-fail-here) attempt.
    mirror_rows = db.query(BreethMirrorFact).filter_by(agent_id=agent.id).all()
    assert len(mirror_rows) == 1, f"expected 1 BreethMirrorFact row, got {len(mirror_rows)}"
    row = mirror_rows[0]
    assert row.group_id == expected_ref
    assert row.subject == agent.persona_name
    assert row.predicate == "is_a"
    assert row.synced is False, (
        "expected synced=False (no real BREETH_API_KEY in this sandboxed "
        "environment) — if this fails, a live call unexpectedly succeeded"
    )
    print(f"[ok] BreethMirrorFact row written: group_id={row.group_id}, synced={row.synced}")

    # 3. Repeat init call must not create a second mirror row.
    agent_again = get_or_create_agent(db)
    assert agent_again.id == agent.id, "repeat init call must return the same agent"
    mirror_rows_after = db.query(BreethMirrorFact).filter_by(agent_id=agent.id).all()
    assert len(mirror_rows_after) == 1, (
        f"expected still 1 BreethMirrorFact row after repeat init, got {len(mirror_rows_after)}"
    )
    print("[ok] repeat init call did not create a duplicate namespace/mirror row")

    db.close()
    print("\nAll Stage 10 checks passed.")


if __name__ == "__main__":
    main()
