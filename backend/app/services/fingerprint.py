"""
fingerprint.py — Stage 13 scope.

Stage 12's `compute_content_hash()` only catches the *literal* same
URL from the same source appearing twice (a re-fetch of an unchanged
feed). It deliberately does nothing for the case where the same
underlying story shows up a second time under a different URL or a
reworded title — e.g. a wire story picked up by two different feed
entries, or a headline that gets tweaked between an initial post and
a later edit. That near-duplicate case is this stage's job.

Approach: reduce a candidate to its normalized source + a small,
order-independent set of "significant" keywords pulled from its title
(and summary, if present), then hash that canonical form. Two
candidates whose titles are reworded/reordered but share the same
core keyword set and source collapse to the same fingerprint; a
candidate that's actually a different story (different keywords) does
not, even from the same source.

This is intentionally a simple keyword-overlap fingerprint, not a
semantic/embedding-based similarity check — no vector DB is in scope
per `PROJECT_STATUS.md` §2, and the PRD's editorial/memory stages
(14/15) are where any heavier judgment calls belong. This stage only
produces a deterministic, unit-testable fingerprint function; nothing
is wired into the DB or discovery pipeline yet.
"""
import hashlib
import re

from app.services.topic_discovery import TopicCandidate

# Common English words that carry no distinguishing signal for
# telling two tech/AI news stories apart. Kept short and boring on
# purpose — this is not meant to be a general-purpose NLP stopword
# list, just enough to strip noise from headline-style titles.
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "of", "in", "on", "for",
        "to", "with", "at", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "as", "it", "its", "this", "that",
        "these", "those", "will", "can", "could", "would", "should",
        "new", "how", "what", "why", "into", "over", "after", "up",
        "out", "about", "than", "now", "your", "you", "we", "our",
    }
)

_WORD_RE = re.compile(r"[a-z0-9]+")

# Cap keeps the fingerprint stable and short-title-friendly: a couple
# of extra trailing words in a longer title/summary shouldn't change
# whether it fingerprints the same as a shorter variant of the same
# story, as long as the leading significant keywords still match.
MAX_KEYWORDS = 8

# Minimum token length to count as a keyword. Kept at 2 rather than
# the more typical 3+ specifically so short but meaningful tech terms
# like "ai", "ml", "llm" aren't dropped as noise.
_MIN_KEYWORD_LENGTH = 2


def _tokenize(text: str) -> list[str]:
    """Lowercase and split into alphanumeric tokens."""
    return _WORD_RE.findall(text.lower())


def extract_keywords(
    title: str, summary: str | None = None, max_keywords: int = MAX_KEYWORDS
) -> list[str]:
    """Pull a small, order-preserving, deduplicated list of significant
    keywords out of a title (and optional summary).

    Title tokens are considered before summary tokens, since the
    title is the strongest signal of what a story actually is; the
    summary is only used to fill in additional distinguishing
    keywords up to `max_keywords`.
    """
    tokens = _tokenize(title)
    if summary:
        tokens += _tokenize(summary)

    significant = [
        t for t in tokens if t not in _STOPWORDS and len(t) >= _MIN_KEYWORD_LENGTH
    ]

    seen: list[str] = []
    for token in significant:
        if token in seen:
            continue
        seen.append(token)
        if len(seen) >= max_keywords:
            break

    return seen


def normalize_source(source_name: str) -> str:
    """Collapse a source name to lowercase alphanumerics only, so
    formatting differences (e.g. "Hacker News (AI/ML)" vs
    "hackernews-ai-ml") don't produce different fingerprints for the
    same underlying feed.
    """
    return re.sub(r"[^a-z0-9]+", "", source_name.lower())


def compute_fingerprint(
    title: str, source_name: str, summary: str | None = None
) -> str:
    """Deterministic SHA-256 fingerprint over normalized source +
    sorted significant keywords.

    Keywords are sorted before hashing (unlike Stage 12's raw
    source+url hash) specifically so that title reordering/rewording
    that preserves the same core keyword set still produces the same
    fingerprint — that's the whole point of this stage over Stage
    12's literal, order-sensitive URL hash.
    """
    keywords = extract_keywords(title, summary)
    basis = normalize_source(source_name) + "|" + "|".join(sorted(keywords))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def fingerprint_candidate(candidate: TopicCandidate) -> str:
    """Convenience wrapper for fingerprinting a `TopicCandidate`
    directly, since that's what Stage 11's discovery and Stage 12's
    cache filter both already operate on.
    """
    return compute_fingerprint(candidate.title, candidate.source_name, candidate.summary)
