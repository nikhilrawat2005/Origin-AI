"""
Agent service — Stage 4 scope only.

Creates the agent row for POST /api/agent/init. No persona generation,
no LLM calls, no Breeth namespace, no scheduler start yet — those are
wired in Stages 5, 8, 10, and 18 respectively. This stage's entire job
is: "does an agent already exist? if not, create one; return it."

Single-active-agent behavior: the PRD says the evaluator calls
POST /api/agent/init exactly once. The Agent model supports multiple
rows (see model docstring) so local dev isn't blocked by leftover rows,
but the service enforces "at most one agent matters" by always
returning the most recently created row on repeat calls instead of
minting duplicates. This makes /init idempotent from the evaluator's
point of view.
"""
from sqlalchemy.orm import Session

from app.models.agent import Agent


def get_or_create_agent(db: Session) -> Agent:
    """Return the existing agent if one exists, else create a new one.

    Persona name/description are left at their model defaults
    ("Aether" / None) until Stage 5 wires in persona_service. Status
    stays "initializing" until Stage 18 flips it to "active" once the
    scheduler is actually running.
    """
    existing = (
        db.query(Agent).order_by(Agent.created_at.desc()).first()
    )
    if existing is not None:
        return existing

    agent = Agent()
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent
