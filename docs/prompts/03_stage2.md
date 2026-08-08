# Stage 2 — Database Models

## Goal
Define the SQLite/SQLAlchemy schema for the four tables the PRD's memory
and publishing flow depends on — `agents`, `posts`, `rejected_topics`,
`sources_cache` — with no routes yet, so the schema can be verified in
isolation before any API logic touches it.

---

## Prompt(s)

User: "continue" (approval to proceed to Stage 2 after Stage 1 review).

---

## AI Response Summary

- Added `app/core/database.py`: SQLAlchemy engine/session factory built
  from `DATABASE_URL`, with the `check_same_thread=False` connect arg
  SQLite needs under FastAPI's threaded request handling, plus a
  `get_db()` dependency (unused until routes exist) and `init_db()` for
  table creation.
- Modeled four tables directly matching the PRD's memory requirements:
  - `agents` — the persona instance; status field tracks
    initializing → active lifecycle; holds `breeth_agent_ref` for the
    Stage 10 Breeth namespace link.
  - `posts` — published content; carries `rationale` and `sources`
    (JSON-encoded) as required fields, not optional, since the PRD
    requires every post to have both. Includes `fingerprint` for future
    dedup use in Stage 13.
  - `rejected_topics` — mirrors the editorial judgment's "reject" branch
    with a required `reason` field, satisfying the memory requirement
    to store rejected topics.
  - `sources_cache` — raw fetched candidates keyed by a unique
    `content_hash`, so Stage 12's fetcher can skip already-seen content.
- Wrote a standalone script (`scripts/test_models.py`, run directly, not
  part of the app) that creates tables against a throwaway SQLite file,
  inserts one row per table, reads it back, and asserts the round trip —
  keeping this stage testable without any route/API layer existing yet.
- Ran the script: all four tables created, all inserts/reads passed.

## Decisions Taken

- **Accepted:** UUID string primary keys (not auto-increment ints) —
  matches the `agentId` shape the PRD's init/feed endpoints will return
  and avoids ID collisions if the DB is ever reset/reseeded.
- **Accepted:** `sources` stored as a JSON-encoded TEXT column rather
  than a separate join table — the PRD explicitly forbids
  over-engineering, and a post's source list is small, static, and only
  ever read as a whole, so a normalized table would add complexity with
  no benefit here.
- **Accepted:** `rationale` and `sources` are `nullable=False` on `Post`
  — enforces the PRD's "every post contains rationale and sources"
  success criterion at the schema level, not just convention.
- **Deferred:** no relationships/back_populates wired between models yet
  (e.g. `Agent.posts`) — will add if a later stage's query patterns
  actually need it, rather than speculatively.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/core/database.py`
- `backend/app/models/agent.py`
- `backend/app/models/post.py`
- `backend/app/models/rejected_topic.py`
- `backend/app/models/sources_cache.py`
- `backend/scripts/test_models.py`
- `backend/scripts/__init__.py`

## Files Modified
- `backend/app/models/__init__.py` — now imports and re-exports all
  four models so `Base.metadata` sees them for `create_all()`.

## Git Commit
```
feat(backend): add SQLAlchemy models for agents, posts, rejected_topics, sources_cache
```

## Stage Outcome
`python scripts/test_models.py` creates all four tables from the models
and successfully inserts/reads back one row per table. Schema is in
place for Stage 4 (`/api/agent/init`) to start writing real `Agent` rows.

## Next Stage
Stage 3 — Frontend Skeleton: Next.js app router boots, empty Landing +
Feed pages, no API calls yet.
