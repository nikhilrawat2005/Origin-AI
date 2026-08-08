"""
post_writer.py — Stage 16 scope.

Given a candidate that has cleared both dedup gates — Stage 14's
editorial judgment (accepted) and Stage 15's memory check
(not-a-duplicate) — generate the actual publishable artifact: a
title, a post body, and a rationale, via `LLMProvider.generate()`
(Stage 6/7), seeded with the persona's full voice profile (Stage 5)
exactly as Stage 14's judgment call was.

Two things this stage deliberately does NOT do:

1. Re-decide whether to publish. That's Stage 14 (editorial) and
   Stage 15 (memory) — this module trusts its caller to only hand it
   candidates that already passed both. `write_post()` takes the
   accepting `JudgmentResult` (Stage 14) as an input specifically so
   the original editorial acceptance reason is available to seed the
   rationale, rather than asking the model to invent one from
   scratch, disconnected from why the topic was actually accepted.
2. Aggregate or expand sources. `Post.sources` is scoped by its own
   Stage 2 docstring as "a JSON-encoded list of source URLs/references
   this post was derived from" — this stage populates it with the
   single `candidate.url` it was given (satisfying `persona.json`'s
   `sourcing_standards.minimum_sources: 1`). Pulling in *additional*
   corroborating sources beyond the one the topic was discovered from
   is out of scope here; nothing in the 20-stage plan assigns it to
   this stage, and Stage 11's discovery/Stage 12's cache only ever
   carry one URL per candidate to begin with.

Unlike Stage 14's editorial judgment (which fails *closed* to REJECT
on any ambiguity, because "don't publish" is always a safe default)
and Stage 15's memory check (which fails *open* on Breeth
specifically, because an infra outage isn't evidence of duplication),
this stage fails *loud*: a provider exception or an unparseable
response raises `PostWriteError` rather than returning some
placeholder post. Publishing malformed or empty content would violate
`persona.json`'s own editorial values ("prefer signal over volume")
far more than simply not publishing this cycle — there is no safe
"default" post to fall back to the way REJECT is a safe default
verdict.
"""
import logging
from dataclasses import dataclass

from app.services.editorial_judgment import JudgmentResult
from app.services.llm.base_provider import LLMProvider
from app.services.llm.llm_factory import get_llm_provider
from app.services.persona_service import build_voice_profile_prompt
from app.services.topic_discovery import TopicCandidate

logger = logging.getLogger(__name__)

_TITLE_MARKER = "TITLE:"
_RATIONALE_MARKER = "RATIONALE:"
_CONTENT_MARKER = "CONTENT:"


class PostWriteError(RuntimeError):
    """Raised when post generation fails outright or the model's
    response can't be confidently parsed into title/content/rationale.
    Deliberately loud rather than falling back to a placeholder post —
    see module docstring.
    """


@dataclass
class WrittenPost:
    """A generated, not-yet-persisted post, ready for Stage 17's
    publisher to write to the `posts` table.
    """

    candidate: TopicCandidate
    fingerprint: str
    title: str
    content: str
    rationale: str
    sources: list[str]


def _build_post_prompt(candidate: TopicCandidate, accept_reason: str) -> str:
    """Build the per-candidate prompt handed to `LLMProvider.generate()`.

    Editorial voice and writing-style rules live in the system prompt
    (`build_voice_profile_prompt()`), not here — this prompt states
    the concrete facts about the candidate, the original editorial
    acceptance reason (so the rationale the model writes is grounded
    in why this was actually accepted, not invented fresh), and the
    required response format.
    """
    summary_line = f"Summary: {candidate.summary}\n" if candidate.summary else ""
    return (
        "Write a post about the following topic, strictly following the "
        "tone, voice traits, and writing style rules defined above.\n\n"
        f"Title: {candidate.title}\n"
        f"Source: {candidate.source_name}\n"
        f"URL: {candidate.url}\n"
        f"Category: {candidate.category}\n"
        f"{summary_line}"
        f"\nWhy this was accepted for coverage: {accept_reason}\n"
        "\nRespond in exactly this format, with no other text before or "
        "after it:\n"
        f"{_TITLE_MARKER} <a sharp, specific headline — not the raw "
        "source title verbatim>\n"
        f"{_RATIONALE_MARKER} <one or two honest sentences on why this "
        "topic was worth covering, including any weaknesses, per the "
        "editorial values above>\n"
        f"{_CONTENT_MARKER}\n"
        "<the post body: a few focused paragraphs, opening with the "
        "development itself, attributing claims to their source inline, "
        "and closing with why it matters>"
    )


def _parse_post_response(raw: str) -> tuple[str, str, str]:
    """Parse a `TITLE:` / `RATIONALE:` / `CONTENT:` response into
    `(title, rationale, content)`.

    Strict about all three markers being present, in order, with
    non-empty content for each — any deviation raises `PostWriteError`
    rather than guessing. `CONTENT:` may be followed by a newline
    before the body starts (as instructed in the prompt); that's
    stripped, not treated as part of the body.
    """
    if not raw or not raw.strip():
        raise PostWriteError("Post generation returned an empty response.")

    text = raw.strip()
    # Strip markdown bolding (e.g. **TITLE:** or **RATIONALE:**) if LLM wraps markers in markdown
    clean_text = text.replace("**", "").strip()

    title_idx = clean_text.find(_TITLE_MARKER)
    rationale_idx = clean_text.find(_RATIONALE_MARKER)
    content_idx = clean_text.find(_CONTENT_MARKER)

    if title_idx == -1 or rationale_idx == -1 or content_idx == -1:
        raise PostWriteError(
            f"Post response missing required section markers: {text[:200]!r}"
        )
    if not (title_idx < rationale_idx < content_idx):
        raise PostWriteError(
            f"Post response sections out of order: {text[:200]!r}"
        )

    title = clean_text[title_idx + len(_TITLE_MARKER):rationale_idx].strip()
    rationale = clean_text[rationale_idx + len(_RATIONALE_MARKER):content_idx].strip()
    content = clean_text[content_idx + len(_CONTENT_MARKER):].strip()

    if not title:
        raise PostWriteError("Post response had an empty TITLE section.")
    if not rationale:
        raise PostWriteError("Post response had an empty RATIONALE section.")
    if not content:
        raise PostWriteError("Post response had an empty CONTENT section.")

    return title, rationale, content


def write_post(
    judgment: JudgmentResult,
    llm_provider: LLMProvider | None = None,
) -> WrittenPost:
    """Generate a `WrittenPost` for an accepted, memory-cleared
    candidate. Raises `PostWriteError` on any generation or parsing
    failure — see module docstring for why this fails loud rather
    than producing a placeholder.

    Takes the whole `JudgmentResult` (not just the candidate) so the
    original editorial acceptance reason grounds the generated
    rationale, and so a caller can't accidentally call this on a
    rejected result — that's asserted explicitly below.
    """
    if not judgment.accepted:
        raise PostWriteError(
            "write_post() called with a rejected JudgmentResult "
            f"(candidate: {judgment.candidate.title!r}); only accepted, "
            "memory-cleared candidates should reach the post writer."
        )

    candidate = judgment.candidate
    provider = llm_provider or get_llm_provider()
    system = build_voice_profile_prompt()
    prompt = _build_post_prompt(candidate, judgment.reason)

    try:
        raw = provider.generate(prompt, system=system)
    except Exception as exc:  # noqa: BLE001 — any provider failure fails loud
        logger.warning("write_post: LLM generate() call failed: %s", exc)
        raise PostWriteError(f"Post generation call failed: {exc}") from exc

    title, rationale, content = _parse_post_response(raw)

    return WrittenPost(
        candidate=candidate,
        fingerprint=judgment.fingerprint,
        title=title,
        content=content,
        rationale=rationale,
        sources=[candidate.url],
    )
