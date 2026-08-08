"""
memory_service.py — Stage 15 scope.

Given an editorially-accepted `TopicCandidate` (Stage 14) plus its
fingerprint (Stage 13), decide whether Aether has already *published*
this topic before it reaches Stage 16's post writer. This is exactly
the layer Stage 14's own docstring flagged as "not this stage":
checking Breeth (and the SQLite mirror) for previously *published*
topics — as opposed to Stage 14's narrower fingerprint check against
*rejected* topics only.

Two dedup layers, checked in order:

1. Local exact match — `posts.fingerprint` (Stage 13's algorithm,
   already stamped onto every `Post` per its Stage 2 docstring:
   "Fingerprint used for dedup against future topic candidates").
   Authoritative, fast, no network dependency. Catches an exact
   reworded/reordered-title repeat of something this agent already
   published.

2. Breeth semantic search — `BreethClient.search()` (Stage 9) scoped
   to the agent's own namespace (`agent.breeth_agent_ref`, Stage 10),
   looking for prior published-topic facts whose keyword overlap with
   this candidate clears `SEMANTIC_OVERLAP_THRESHOLD`. Catches what
   fingerprinting structurally can't: the same underlying story
   covered from a genuinely different source/title that doesn't
   collapse to the same fingerprint. This is a *soft* signal — a fuzzy
   keyword-overlap scan over whatever `edges` Breeth returns, not a
   hard structural guarantee — so it can flag a possible duplicate,
   but a miss here is not proof of novelty on its own.

Unlike Stage 14's editorial judgment (fails *closed* — any LLM error
rejects), this stage fails *open* on the Breeth call specifically.
Per PROJECT_STATUS.md's "Known Constraints" #2, there's no real
BREETH_API_KEY in this sandboxed environment, so a missing key or a
Breeth outage must never block an otherwise-novel, already-*accepted*
topic from being published — that would silently starve the feed for
a reason that has nothing to do with editorial judgment. On a Breeth
failure this module falls back to a best-effort local keyword scan
over `breeth_mirror_facts` (Stage 10's local mirror table), exactly
the fallback that table's own Stage 10 docstring reserved for this
stage. That fallback will typically find nothing until Stage 17's
publisher starts writing post-published facts into it — that's
expected, not a bug here. Layer 1 (`posts.fingerprint`) is unaffected
by any of this and remains authoritative regardless of Breeth's
availability.
"""
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.breeth_mirror import BreethMirrorFact
from app.models.post import Post
from app.services.breeth_client import BreethClient
from app.services.fingerprint import extract_keywords, fingerprint_candidate
from app.services.topic_discovery import TopicCandidate

logger = logging.getLogger(__name__)

# Fraction of the candidate's keywords that must also appear in a
# Breeth edge's (or local mirror fact's) own keyword set to count as a
# semantic duplicate. Deliberately generous rather than exact — this
# layer's job is to catch near-misses Layer 1's exact fingerprint match
# won't, not to be a second precise fingerprint check.
SEMANTIC_OVERLAP_THRESHOLD = 0.6


@dataclass
class MemoryCheckResult:
    """The outcome of checking one accepted candidate against memory."""

    candidate: TopicCandidate
    fingerprint: str
    is_duplicate: bool
    reason: str
    checked_via: list[str] = field(default_factory=list)


def _keyword_overlap_ratio(candidate_keywords: list[str], other_text: str) -> float:
    """Fraction of `candidate_keywords` that also appear in the
    keyword set extracted from `other_text`. 0.0 if candidate_keywords
    is empty (nothing to overlap against, so no match).
    """
    if not candidate_keywords:
        return 0.0
    other_keywords = set(extract_keywords(other_text))
    matched = sum(1 for kw in candidate_keywords if kw in other_keywords)
    return matched / len(candidate_keywords)


def _published_by_fingerprint(db: Session, agent_id: str, fingerprint: str) -> Post | None:
    """Layer 1: exact local match against `posts.fingerprint`."""
    return (
        db.query(Post)
        .filter_by(agent_id=agent_id, fingerprint=fingerprint)
        .first()
    )


def _edge_text(edge: dict) -> str:
    """Flatten a Breeth search edge into one string for keyword
    extraction. Breeth's edge shape isn't pinned down by anything this
    project has verified beyond Stage 9's connection test (`edges` was
    the only field name confirmed), so this reads defensively — any of
    the plausible text-bearing keys present get joined; anything else
    is ignored rather than raising.
    """
    parts = []
    for key in ("subject", "predicate", "object", "fact", "content", "text"):
        value = edge.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts)


def _check_breeth_semantic(
    agent: Agent, candidate: TopicCandidate, breeth_client: BreethClient
) -> tuple[bool, str] | None:
    """Query Breeth's own namespace for a semantically similar,
    previously-published topic.

    Returns `(is_duplicate, reason)` on a successful call (even if it
    found nothing), or `None` if the call itself failed — the caller
    falls back to the local mirror in that case, per this module's
    fail-open policy.
    """
    if not agent.breeth_agent_ref:
        return False, "Agent has no Breeth namespace yet; skipping semantic check."

    candidate_keywords = extract_keywords(candidate.title, candidate.summary)

    try:
        response = breeth_client.search(
            candidate.title, group_id=agent.breeth_agent_ref, limit=5
        )
    except Exception as exc:  # noqa: BLE001 — any Breeth failure falls back, doesn't reject
        logger.warning(
            "memory_service: Breeth search failed, falling back to local mirror: %s", exc
        )
        return None

    edges = response.get("edges", []) if isinstance(response, dict) else []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        overlap = _keyword_overlap_ratio(candidate_keywords, _edge_text(edge))
        if overlap >= SEMANTIC_OVERLAP_THRESHOLD:
            return True, (
                f"Possible duplicate of a previously published topic in Breeth "
                f"memory (keyword overlap {overlap:.0%}): {_edge_text(edge)[:120]!r}"
            )

    return False, "No semantically similar published topic found in Breeth."


def _check_local_mirror_fallback(
    db: Session, agent_id: str, candidate: TopicCandidate
) -> tuple[bool, str]:
    """Best-effort fallback when Breeth itself is unreachable: scan
    `breeth_mirror_facts` (Stage 10) for a synced fact whose text
    overlaps this candidate's keywords enough to count as a semantic
    duplicate. Will typically find nothing until Stage 17's publisher
    starts writing post-published facts here — expected, not a bug.
    """
    candidate_keywords = extract_keywords(candidate.title, candidate.summary)

    facts = (
        db.query(BreethMirrorFact)
        .filter_by(agent_id=agent_id, synced=True)
        .all()
    )
    for fact in facts:
        text = f"{fact.subject} {fact.predicate} {fact.object}"
        overlap = _keyword_overlap_ratio(candidate_keywords, text)
        if overlap >= SEMANTIC_OVERLAP_THRESHOLD:
            return True, (
                f"Possible duplicate found in local Breeth mirror fallback "
                f"(keyword overlap {overlap:.0%}): {text[:120]!r}"
            )

    return False, "No match in local Breeth mirror fallback (or nothing synced yet)."


def check_memory(
    db: Session,
    agent: Agent,
    candidate: TopicCandidate,
    breeth_client: BreethClient | None = None,
) -> MemoryCheckResult:
    """Check whether an editorially-accepted candidate has already
    been published, before it reaches Stage 16's post writer.

    Fails open on Breeth specifically (see module docstring) — a
    missing API key or a Breeth outage never blocks an otherwise-novel
    candidate. Layer 1's local fingerprint match is unaffected by
    Breeth's availability and is checked first regardless.
    """
    fingerprint = fingerprint_candidate(candidate)
    checked_via: list[str] = ["posts_table"]

    existing_post = _published_by_fingerprint(db, agent.id, fingerprint)
    if existing_post is not None:
        logger.info(
            "check_memory: fingerprint match against already-published post (%s)",
            candidate.title,
        )
        return MemoryCheckResult(
            candidate=candidate,
            fingerprint=fingerprint,
            is_duplicate=True,
            reason=f"Already published (fingerprint match): {existing_post.title!r}",
            checked_via=checked_via,
        )

    client = breeth_client or BreethClient()
    semantic_result = _check_breeth_semantic(agent, candidate, client)

    if semantic_result is not None:
        checked_via.append("breeth_search")
        is_duplicate, reason = semantic_result
    else:
        checked_via.append("breeth_mirror_fallback")
        is_duplicate, reason = _check_local_mirror_fallback(db, agent.id, candidate)

    return MemoryCheckResult(
        candidate=candidate,
        fingerprint=fingerprint,
        is_duplicate=is_duplicate,
        reason=reason,
        checked_via=checked_via,
    )


def check_memory_batch(
    db: Session,
    agent: Agent,
    candidates: list[TopicCandidate],
    breeth_client: BreethClient | None = None,
) -> list[MemoryCheckResult]:
    """Batch wrapper over `check_memory`, reusing one `BreethClient`
    across the whole batch instead of constructing one per call.

    Not wired into any route or the scheduler yet — Stage 18 will
    chain this after Stage 14's `judge_candidates()` (accepted results
    only) as the next step before Stage 16's post writer:
    `discover_new_topics(db)` -> `judge_candidates(...)` (accepted only)
    -> `check_memory_batch(...)` (not-duplicate only) -> post writer.
    """
    client = breeth_client or BreethClient()
    return [
        check_memory(db, agent, candidate, breeth_client=client)
        for candidate in candidates
    ]
