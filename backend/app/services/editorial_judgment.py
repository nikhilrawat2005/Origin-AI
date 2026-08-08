"""
editorial_judgment.py — Stage 14 scope.

Given a freshly-discovered, cache-filtered `TopicCandidate` (Stages
11/12) and its fingerprint (Stage 13), decide whether Aether should
cover it — and if not, log why to `rejected_topics` (Stage 2's model,
unused until now).

Two dedup layers happen before any LLM call:
1. Fingerprint check against `rejected_topics` — if this exact
   near-duplicate story was already rejected, don't waste an LLM call
   re-judging it; reject immediately with the fingerprint match noted.
   This is exactly what `RejectedTopic`'s own docstring (Stage 2)
   describes: "prevents re-evaluating the same rejected topic
   repeatedly."
2. (Not this stage) checking Breeth for *published* topics — that's
   Stage 15's memory service. This stage only guards against
   re-judging something already in `rejected_topics`.

The actual judgment call uses `LLMProvider.judge()` (Stage 6/7), seeded
with the persona's full voice profile (Stage 5) as the system prompt —
so acceptance criteria come from `persona.json`'s `editorial_values`,
`topics_of_interest`/`topics_avoided`, and `sourcing_standards`, not
from logic hardcoded here. This service's job is building that prompt,
parsing the model's ACCEPT/REJECT response, and persisting the
rejection when applicable — not encoding editorial taste itself.

Fails closed: any judgment call that errors, times out, or returns a
response this module can't confidently parse as ACCEPT is treated as
a REJECT. This matches `persona.json`'s stated editorial value to
"prefer signal over volume — reject more than it accepts" — an
ambiguous or failed judgment should never default to publishing.
"""
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.rejected_topic import RejectedTopic
from app.services.fingerprint import fingerprint_candidate
from app.services.llm.base_provider import LLMProvider
from app.services.llm.llm_factory import get_llm_provider
from app.services.persona_service import build_voice_profile_prompt
from app.services.topic_discovery import TopicCandidate

logger = logging.getLogger(__name__)

_ACCEPT_PREFIX = "ACCEPT"
_REJECT_PREFIX = "REJECT"


@dataclass
class JudgmentResult:
    """The outcome of judging one candidate."""

    candidate: TopicCandidate
    fingerprint: str
    accepted: bool
    reason: str


def _build_judgment_prompt(candidate: TopicCandidate) -> str:
    """Build the per-candidate prompt handed to `LLMProvider.judge()`.

    The persona's editorial standards live in the system prompt
    (`build_voice_profile_prompt()`), not here — this prompt is just
    the concrete facts about the candidate plus the required response
    format, kept separate so the same format instructions apply
    regardless of which persona fields end up mattering most.
    """
    summary_line = f"Summary: {candidate.summary}\n" if candidate.summary else ""
    return (
        "Evaluate whether the following topic is worth covering, based "
        "strictly on the editorial values, topics of interest/avoided, "
        "and sourcing standards defined above.\n\n"
        f"Title: {candidate.title}\n"
        f"Source: {candidate.source_name}\n"
        f"URL: {candidate.url}\n"
        f"Category: {candidate.category}\n"
        f"{summary_line}"
        "\nRespond in exactly this format, with no other text:\n"
        "ACCEPT: <one or two sentence rationale>\n"
        "or\n"
        "REJECT: <one or two sentence rationale>"
    )


def _parse_judgment(raw: str) -> tuple[bool, str]:
    """Parse an LLMProvider.judge() response into (accepted, reason).
    Cleanly strips markdown (like **ACCEPT**) if present.
    """
    if not raw:
        return False, "Editorial judgment returned an empty response."

    text = raw.strip()
    # Strip markdown bolding if present
    clean_text = text.replace("**", "").strip()

    if clean_text.upper().startswith(_ACCEPT_PREFIX):
        reason = clean_text[len(_ACCEPT_PREFIX):].lstrip(":").strip()
        return True, reason or "Accepted (no rationale given)."

    if clean_text.upper().startswith(_REJECT_PREFIX):
        reason = clean_text[len(_REJECT_PREFIX):].lstrip(":").strip()
        return False, reason or "Rejected (no rationale given)."

    return False, f"Unparseable judgment response, rejected by default: {text[:200]!r}"


def _previously_rejected_reason(db: Session, agent_id: str, fingerprint: str) -> str | None:
    """Return the original rejection reason if this fingerprint was
    already rejected for this agent, else None.
    """
    existing = (
        db.query(RejectedTopic)
        .filter_by(agent_id=agent_id, fingerprint=fingerprint)
        .first()
    )
    if existing is None:
        return None
    return f"Previously rejected (fingerprint match): {existing.reason}"


def judge_candidate(
    db: Session,
    agent_id: str,
    candidate: TopicCandidate,
    llm_provider: LLMProvider | None = None,
) -> JudgmentResult:
    """Judge a single candidate, logging a `RejectedTopic` row if
    rejected. Does not touch `posts` or Breeth — this stage only
    decides accept/reject and records rejections.
    """
    fingerprint = fingerprint_candidate(candidate)

    already_rejected_reason = _previously_rejected_reason(db, agent_id, fingerprint)
    if already_rejected_reason is not None:
        logger.info(
            "judge_candidate: skipping LLM call, fingerprint already rejected (%s)",
            candidate.title,
        )
        return JudgmentResult(
            candidate=candidate,
            fingerprint=fingerprint,
            accepted=False,
            reason=already_rejected_reason,
        )

    provider = llm_provider or get_llm_provider()
    system = build_voice_profile_prompt()
    prompt = _build_judgment_prompt(candidate)

    try:
        raw = provider.judge(prompt, system=system)
    except Exception as exc:  # noqa: BLE001 — any provider failure fails closed
        logger.warning("judge_candidate: LLM judge() call failed: %s", exc)
        accepted, reason = False, f"Editorial judgment call failed: {exc}"
    else:
        accepted, reason = _parse_judgment(raw)

    if not accepted:
        logger.info("judge_candidate: REJECTED %r - %s", candidate.title, reason)
        db.add(
            RejectedTopic(
                agent_id=agent_id,
                title=candidate.title,
                source=candidate.source_name,
                fingerprint=fingerprint,
                reason=reason,
            )
        )
        db.commit()
    else:
        logger.info("judge_candidate: ACCEPTED %r - %s", candidate.title, reason)

    return JudgmentResult(
        candidate=candidate, fingerprint=fingerprint, accepted=accepted, reason=reason
    )


def judge_candidates(
    db: Session,
    agent_id: str,
    candidates: list[TopicCandidate],
    llm_provider: LLMProvider | None = None,
) -> list[JudgmentResult]:
    """Judge a batch of candidates (typically Stage 12's
    `discover_new_topics()` output), one at a time.

    Not wired into any route or scheduler yet — Stage 18 will chain
    this after Stage 12's `discover_new_topics()` as the next step in
    the discovery -> judgment -> memory -> generation -> publish flow.
    """
    provider = llm_provider or get_llm_provider()
    return [
        judge_candidate(db, agent_id, candidate, llm_provider=provider)
        for candidate in candidates
    ]
