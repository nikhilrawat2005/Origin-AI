"""
Agent service — Stage 10 scope.

Creates the agent row for POST /api/agent/init. Stage 4 only created a
bare row; Stage 8 wired in LLM-generated persona descriptions. Stage
10 adds the second piece of on-creation setup: giving the new agent
its own Breeth namespace (a `group_id`, Breeth's scoping mechanism —
see breeth_client.py) so all of its facts stay isolated from any other
agent that might ever exist, and mirroring that attempt locally via
BreethMirrorFact regardless of whether the remote write actually
succeeded. Scheduler start (Stage 18) is still not wired in here.

Single-active-agent behavior unchanged from Stage 4: the PRD says the
evaluator calls POST /api/agent/init exactly once. The Agent model
supports multiple rows (see model docstring) so local dev isn't
blocked by leftover rows, but the service enforces "at most one agent
matters" by always returning the most recently created row on repeat
calls instead of minting duplicates — and, since generation only runs
on creation, repeat calls never re-trigger an LLM or Breeth call
either.
"""
import logging

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.breeth_mirror import BreethMirrorFact
from app.services.persona_service import build_voice_profile_prompt, get_persona_name
from app.services.llm.llm_factory import get_llm_provider
from app.services.breeth_client import BreethClient

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


def _breeth_group_id(agent_id: str) -> str:
    """Deterministic Breeth `group_id` for an agent — this *is* the
    "namespace": Breeth scopes facts/search by group_id rather than
    exposing a separate namespace-creation call, so establishing a
    namespace means picking this id and writing the first fact into
    it.
    """
    return f"agent-{agent_id}"


def _create_breeth_namespace(db: Session, agent: Agent) -> str:
    """Establish (best-effort) the new agent's Breeth namespace.

    Always returns the computed group_id — it's a locally-derived
    identifier, not something Breeth generates, so it's valid to store
    on the agent row and retry against even if today's write fails.
    The actual remote write is wrapped in a broad try/except for the
    same reason as `_generate_persona_description`: no real
    BREETH_API_KEY is available in this sandboxed environment (see
    PROJECT_STATUS.md "Known Constraints"), and /init must still
    succeed and create the agent row without a live Breeth call.

    Either way, a BreethMirrorFact row is written locally recording
    the attempt and whether it actually synced — Stage 15's
    memory_service gets a local fallback to fall back on, and nothing
    about namespace creation is silently lost even when the remote
    call fails.
    """
    group_id = _breeth_group_id(agent.id)
    subject = agent.persona_name
    predicate = "is_a"
    object_ = "autonomous AI technology research persona"

    synced = False
    try:
        BreethClient().write_fact(
            subject=subject,
            predicate=predicate,
            object_=object_,
            group_id=group_id,
        )
        synced = True
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring.
        logger.warning("Breeth namespace write skipped for %s: %s", group_id, exc)

    db.add(
        BreethMirrorFact(
            agent_id=agent.id,
            group_id=group_id,
            subject=subject,
            predicate=predicate,
            object=object_,
            synced=synced,
        )
    )
    db.commit()
    return group_id


def get_or_create_agent(db: Session, persona_name: str | None = None) -> Agent:
    """Return the existing agent if one exists, else create one,
    generate its persona description via the LLM, and establish its
    Breeth namespace.

    `persona_name`, when passed (from the evaluator's optional
    `POST /api/agent/init` body, `{"persona": {"name", "domain"}}`),
    overrides persona.json's default name for this agent. Persona
    identity is otherwise frozen from persona.json (Stage 5's persona
    bible) rather than the model's bare default, so a new agent is
    named and voiced correctly even before any LLM call succeeds.
    persona_description is LLM-generated on creation only;
    breeth_agent_ref is set on creation only, right after, once the
    row has an id to derive the namespace from. status stays
    "initializing" until Stage 18 flips it to "active" once the
    scheduler is running.
    """
    existing = (
        db.query(Agent).order_by(Agent.created_at.desc()).first()
    )
    if existing is not None:
        return existing

    agent = Agent(persona_name=persona_name or get_persona_name())
    agent.persona_description = _generate_persona_description()
    db.add(agent)
    db.commit()
    db.refresh(agent)

    agent.breeth_agent_ref = _create_breeth_namespace(db, agent)
    db.commit()
    db.refresh(agent)
    return agent
