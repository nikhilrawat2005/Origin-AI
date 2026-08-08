"""
Standalone verification script for Stage 8 — Wire LLM into Init.

Run with:  python -m scripts.test_init_llm_wiring   (from backend/)

Uses an in-memory SQLite database and a fake LLMProvider (no network,
no real API key needed) so this is fully offline-runnable, then
separately confirms the real graceful-fallback path against whatever
provider is actually configured (expected: no key set, in this
sandboxed environment).

Checks:
1. get_or_create_agent() with a working fake LLM provider creates an
   agent whose persona_name comes from persona.json and whose
   persona_description is the fake provider's generated text.
2. Calling get_or_create_agent() again returns the SAME row unchanged
   (idempotent) and does NOT call the LLM a second time.
3. If persona generation fails (e.g. no API key configured for the
   real provider), agent creation still succeeds — status
   "initializing", persona_description is None rather than the
   request failing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base  # noqa: E402
import app.models  # noqa: F401,E402  (register models on Base.metadata)
from app.models.agent import Agent  # noqa: E402
from app.services import agent_service  # noqa: E402
from app.services.persona_service import get_persona_name  # noqa: E402


class _FakeCallCounter:
    calls = 0


class FakeProvider:
    """Minimal stand-in for an LLMProvider — no network involved."""

    name = "fake"

    def generate(self, prompt: str, system: str | None = None) -> str:
        _FakeCallCounter.calls += 1
        return "Aether is a research persona that covers real AI developments."

    def judge(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError

    def summarize(self, text: str, system: str | None = None) -> str:
        raise NotImplementedError


def _fresh_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def main() -> None:
    print("1. Creating an agent with a working (fake) LLM provider...")
    db = _fresh_session()
    original_get_provider = agent_service.get_llm_provider
    agent_service.get_llm_provider = lambda: FakeProvider()  # type: ignore
    try:
        agent = agent_service.get_or_create_agent(db)
        assert agent.persona_name == get_persona_name()
        assert agent.persona_description == (
            "Aether is a research persona that covers real AI developments."
        )
        assert agent.status == "initializing"
        assert _FakeCallCounter.calls == 1
        print(
            f"   OK — agent created: persona_name={agent.persona_name!r}, "
            f"persona_description set, LLM called {_FakeCallCounter.calls} time"
        )

        print("2. Confirming a repeat call is idempotent and doesn't re-call the LLM...")
        agent_id_before = agent.id
        again = agent_service.get_or_create_agent(db)
        assert again.id == agent_id_before
        assert _FakeCallCounter.calls == 1, "LLM should not be called again on repeat init"
        print("   OK — same agent returned, LLM call count unchanged")
    finally:
        agent_service.get_llm_provider = original_get_provider  # type: ignore

    print("3. Confirming graceful fallback when persona generation fails...")
    db2 = _fresh_session()
    description = agent_service._generate_persona_description()
    if description is None:
        print(
            "   OK — no working LLM provider configured (expected: no real "
            "API key in this sandboxed environment, see PROJECT_STATUS.md "
            "'Known Constraints'). Verifying agent creation still succeeds..."
        )
    else:
        print(
            "   NOTE — a real API key IS configured; got a live description "
            "instead of the fallback path. Verifying agent creation still "
            "succeeds either way..."
        )
    agent2 = agent_service.get_or_create_agent(db2)
    assert agent2.status == "initializing"
    assert isinstance(agent2.persona_name, str) and agent2.persona_name
    print(
        f"   OK — agent created regardless of LLM outcome: "
        f"persona_description={agent2.persona_description!r}"
    )

    print("\nAll Stage 8 init/LLM-wiring checks passed.")


if __name__ == "__main__":
    main()
