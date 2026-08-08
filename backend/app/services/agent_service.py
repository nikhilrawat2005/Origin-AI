"""
Agent service — Stage 8 scope.

Creates the agent row for POST /api/agent/init. Stage 4 only created a
bare row; Stage 8 is the first place any of this actually generates
content — on creation (not on idempotent re-fetch), it builds the
persona voice-profile prompt (Stage 5's persona_service) and sends it
through the LLM abstraction (Stage 7's llm_factory) to produce a short
persona description, stored on the row. Breeth namespace creation
(Stage 10) and scheduler start (Stage 18) are still not wired in here.

Single-active-agent behavior unchanged from Stage 4: the PRD says the
evaluator calls POST /api/agent/init exactly once. The Agent model
supports multiple rows (see model docstring) so local dev isn't
blocked by leftover rows, but the service enforces "at most one agent
matters" by always returning the most recently created row on repeat
calls instead of minting duplicates — and, since generation only runs
on creation, repeat calls never re-trigger an LLM call either.
"""
import logging

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.services.persona_service import build_voice_profile_prompt, get_persona_name
from app.services.llm.llm_factory import get_llm_provider

logger = logging.getLogger(__name__)

PERSONA_DESCRIPTION_PROMPT = (
    "In 2-3 sentences, introduce yourself to a reader encountering you "
    "for the first time. Write in your own voice, as described above. "
    "Do not use a greeting like \"Hello\" or address the reader directly "
    "as \"you\" — write it as a short third-person-free bio a reader "
    "would see on a landing page."
)


def _generate_persona_description() -> str | None:
    """Call the LLM to generate a persona description for a new agent.

    Returns None (rather than raising) if the call fails — most likely
    because no real API key is configured for the selected provider,
    the expected case in this sandboxed dev environment (see
    PROJECT_STATUS.md "Known Constraints"). Init must still succeed and
    create the agent row even without a live LLM available; the row
    just falls back to the static tagline from persona.json instead of
    an LLM-generated description, and can be regenerated at any later
    point once a real key is in place.
    """
    try:
        provider = get_llm_provider()
        system = build_voice_profile_prompt()
        return provider.generate(PERSONA_DESCRIPTION_PROMPT, system=system).strip()
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any
        # provider/config/network failure should degrade gracefully,
        # not block agent creation.
        logger.warning("Persona description generation skipped: %s", exc)
        return None


def get_or_create_agent(db: Session) -> Agent:
    """Return the existing agent if one exists, else create one and
    generate its persona description via the LLM.

    persona_name comes from persona.json (Stage 5's persona bible)
    rather than the model's bare default, so a new agent is named
    correctly even before any LLM call succeeds. persona_description
    is LLM-generated on creation only; status stays "initializing"
    until Stage 18 flips it to "active" once the scheduler is running.
    """
    existing = (
        db.query(Agent).order_by(Agent.created_at.desc()).first()
    )
    if existing is not None:
        return existing

    agent = Agent(persona_name=get_persona_name())
    agent.persona_description = _generate_persona_description()
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent
