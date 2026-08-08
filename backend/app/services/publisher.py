"""
publisher.py — Stage 17 scope.

Given a `WrittenPost` (Stage 16's output for an already accepted,
memory-cleared candidate), do the two things nothing before this stage
has done yet: persist it as a `Post` row, and tell Breeth about it so
Stage 15's memory service can find it on a future cycle and correctly
flag a repeat.

Follows the exact same best-effort-remote-write + always-local-mirror
pattern `agent_service._create_breeth_namespace()` (Stage 10) already
established for the namespace-creation Breeth call: the local side
(here, the `Post` row) is authoritative and always happens; the remote
Breeth write is wrapped in a broad try/except and its outcome
(`synced`) is recorded on a `BreethMirrorFact` row regardless of
whether it actually succeeded. This is deliberate, not incidental —
Stage 15's memory service already depends on `breeth_mirror_facts`
being a real (if best-effort) mirror of what publishing attempted to
tell Breeth, per that stage's own module docstring; if this stage
only wrote to Breeth without mirroring locally, Stage 15's fallback
path would have nothing to fall back to even after this stage exists.

The mirrored/pushed fact uses the post's own title as its `object` —
not a generic string — specifically so Stage 15's keyword-overlap
matching (`_check_breeth_semantic` / `_check_local_mirror_fallback`)
has real title text to compare a future candidate against, the same
shape of data those functions were written to expect.

Publishing failure modes are intentionally asymmetric from Stage 16's
post writer: writing the local `Post` row is a plain DB operation with
no external dependency, so nothing here "fails open" or "fails closed"
on it — if the DB write itself fails, that's a genuine unhandled error,
same as any other required DB write in this codebase (Stage 2's models,
Stage 12's sources_cache, Stage 14's rejected_topics). Only the Breeth
side gets the best-effort treatment, matching Stage 10's precedent
exactly.
"""
import json
import logging

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.breeth_mirror import BreethMirrorFact
from app.models.post import Post
from app.services.breeth_client import BreethClient
from app.services.post_writer import WrittenPost

logger = logging.getLogger(__name__)

_PUBLISHED_PREDICATE = "published"


def _push_published_fact(
    db: Session, agent: Agent, post: Post, breeth_client: BreethClient | None = None
) -> bool:
    """Best-effort push of a "published" fact to Breeth, mirrored
    locally regardless of outcome. Returns whether the remote write
    actually synced.

    Skips the remote call entirely (but still writes the local mirror
    row) when the agent has no Breeth namespace yet — there's nowhere
    to write the fact to, and this can legitimately happen if `/init`
    ran without a working `BREETH_API_KEY` (Stage 10's own fallback
    behavior).
    """
    group_id = agent.breeth_agent_ref
    subject = agent.persona_name
    object_ = post.title

    synced = False
    if group_id:
        client = breeth_client or BreethClient()
        try:
            client.write_fact(
                subject=subject,
                predicate=_PUBLISHED_PREDICATE,
                object_=object_,
                group_id=group_id,
            )
            synced = True
        except Exception as exc:  # noqa: BLE001 - deliberately broad, see module docstring.
            logger.warning(
                "publisher: Breeth published-fact write skipped for post %s: %s",
                post.id,
                exc,
            )
    else:
        logger.warning(
            "publisher: agent %s has no Breeth namespace; skipping remote write, "
            "mirroring locally only",
            agent.id,
        )

    db.add(
        BreethMirrorFact(
            agent_id=agent.id,
            group_id=group_id or "unassigned",
            subject=subject,
            predicate=_PUBLISHED_PREDICATE,
            object=object_,
            synced=synced,
        )
    )
    db.commit()
    return synced


def publish_post(
    db: Session,
    agent: Agent,
    written_post: WrittenPost,
    breeth_client: BreethClient | None = None,
) -> Post:
    """Persist `written_post` as a `Post` row and push a corresponding
    "published" fact to Breeth (best-effort, always mirrored locally).

    Returns the persisted `Post`, already committed and refreshed with
    its generated `id`/`created_at`. The `Post` row itself is what
    makes this candidate's fingerprint visible to Stage 15's Layer 1
    check (`posts.fingerprint`) on any future cycle; the Breeth fact
    push is what feeds Stage 15's Layer 2 semantic check and its local
    mirror fallback.
    """
    post = Post(
        agent_id=agent.id,
        title=written_post.title,
        content=written_post.content,
        rationale=written_post.rationale,
        sources=json.dumps(written_post.sources),
        fingerprint=written_post.fingerprint,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    _push_published_fact(db, agent, post, breeth_client=breeth_client)

    return post
