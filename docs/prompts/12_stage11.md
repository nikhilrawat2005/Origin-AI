# Stage 11 — Topic Sources Config + Fetcher

## Goal
`topic_sources.json` + `topic_discovery.py` — raw topic candidates
fetched from configured sources, no caching/dedup yet.

---

## Prompt(s)

User: "continue" (after approving Stage 10's `aether-stage10.zip`).

---

## AI Response Summary

- Picked three sources spanning the categories `persona.json` (Stage
  5) already defines interest in — industry news, research, and
  commentary — rather than one source per category being arbitrary:
  Hacker News (Algolia Search API, JSON, no auth), arXiv cs.AI (RSS),
  MIT Technology Review's AI feed (RSS). Chose Algolia's HN search API
  over scraping HN's HTML or using its Firebase item API directly —
  it's a documented, stable, filterable JSON endpoint built for
  exactly this kind of query.
- `app/services/topic_discovery.py`:
  - `TopicCandidate` — a plain dataclass, deliberately thin (no
    fingerprint/id field — that's Stage 13's job specifically).
  - Two parsers, `_parse_hn_algolia()` and `_parse_rss()`. RSS parsed
    with the standard library's `ElementTree` rather than adding
    `feedparser` — Stage 11 only needs title/link/description/pubDate
    from a standard RSS 2.0 `<item>`, which doesn't justify a new
    dependency. Both parsers skip individual items missing a
    title/url rather than producing an incomplete candidate or
    raising.
  - `fetch_source()` fetches+parses exactly one source; network errors
    and parse errors are caught and logged per-source, returning `[]`
    for that source, not raised — reasoning explicitly tied to Stage
    18: once this runs unattended under the scheduler, one temporarily
    -down or malformed feed must not stop discovery from every other
    source. `TopicSourceError` is reserved for a genuinely malformed
    *config* entry (unknown `type`), which is a programmer error worth
    failing loudly on, distinct from a live source having a bad day.
  - `discover_topics()` aggregates across all sources, with injectable
    `sources`/`client` parameters specifically so the verification
    script can exercise the real HTTP + parsing code path against
    canned responses without live network access.
- `backend/scripts/test_topic_discovery.py` — four checks: config
  loads with all required fields, HN parser handles a canned response
  (including the "self-post with no `url`, falls back to the HN item
  link" case and a missing-title skip), RSS parser handles a canned
  feed (including a missing-link skip and RFC-2822 `pubDate` parsing),
  and a `discover_topics()` aggregation test using
  `httpx.MockTransport` with three fake sources — one returns `200`
  JSON, one returns `503`, one returns `200` RSS — confirming the
  final candidate list only contains the two working sources' items
  and that the `503` source didn't raise or block the others.
- Ran the new script, then re-ran all seven prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10) — all passed, no regressions.

## Decisions Taken

- **Accepted:** three sources at launch (HN, arXiv, MIT Tech Review)
  rather than more — matches persona.json's existing category split
  without inventing categories the persona bible doesn't already
  claim to cover; more sources can be appended to
  `topic_sources.json` later without any code change, since
  `discover_topics()` just iterates whatever's configured.
- **Accepted:** per-source failure isolation (catch, log, continue)
  over failing the whole discovery run on any single source error —
  directly required by the PRD's "zero further human prompting"
  autonomy goal; a brittle discovery step would silently stall the
  whole pipeline under the scheduler with no one there to notice.
- **Accepted:** stdlib `ElementTree` over adding `feedparser` — avoids
  a new dependency for a well-defined, standard RSS 2.0 shape; can
  revisit if a future source needs Atom or a more exotic feed dialect.
- **Accepted:** testing via `httpx.MockTransport` against canned
  response bodies rather than only testing the "no live access, skip
  the live call" path used in Stages 6/7/9 — the parsing logic here
  doesn't depend on a stateful third-party account or secret API key,
  so it's fully and meaningfully testable offline; used that
  opportunity for real coverage instead of settling for the weaker
  pattern by default.
- **Deferred:** no `sources_cache` dedup — every call currently
  re-fetches and re-returns everything, including items seen on a
  previous run. That's explicitly Stage 12.
- **Deferred:** no fingerprinting/normalization of titles — Stage 13.
- **Deferred:** no retry/backoff on individual source fetches — same
  reasoning as prior network-touching stages, deferred to Stage 18.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/core/topic_sources.json`
- `backend/app/services/topic_discovery.py`
- `backend/scripts/test_topic_discovery.py`
- `docs/prompts/12_stage11.md`

## Files Modified
- `README.md` — project status bumped to Stage 11, repo tree updated,
  Stage 11 verification section added.
- `PROJECT_STATUS.md` — Stage 11 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 11 entry appended.

## Git Commit
```
feat(backend): add topic sources config and discovery fetcher
```

## Stage Outcome
`python3 scripts/test_topic_discovery.py` (run from `backend/`, venv
active) passes all four checks, fully offline via `httpx.MockTransport`
— no live network access to Hacker News/arXiv/MIT Tech Review was
used or needed to verify the parsing and aggregation logic itself.
Re-ran all seven prior verification scripts (Stages 2, 5, 6, 7, 8, 9,
10) — all pass, no regressions. No database changes, no routes
touched, nothing wired into `/init` or the (not-yet-existing)
scheduler this stage — `discover_topics()` exists as a standalone,
directly-callable function only.

## Next Stage
Stage 12 — Sources Cache: wire `sources_cache` (the `SourceCache`
model from Stage 2, unused until now) into the discovery path — hash
each candidate, skip ones already seen, so repeated `discover_topics()`
calls don't keep re-surfacing the same items forever.
