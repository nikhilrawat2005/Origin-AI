# AI Usage Log — Master Index

This file is the master index of every AI-assisted development stage on
Aether. It is updated immediately after each stage completes. Full detail
for each stage lives in `docs/prompts/`.

---

### Stage 1
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Repo + Backend Skeleton
**Summary:** Bootstrapped the FastAPI backend — folder structure
(`app/main.py`, `core/config.py`, empty `routes/`, `services/`,
`models/` packages), centralized env-driven settings, CORS, and a
`GET /api/health` liveness route. Verified the server boots and the
health check returns 200 locally.
**Files Changed:**
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/{__init__.py, core/__init__.py, routes/__init__.py, services/__init__.py, models/__init__.py}`
- `backend/requirements.txt`
- `backend/.env.example`
- `README.md`
**Commit:** `feat(backend): bootstrap FastAPI skeleton with config and health check`
**Prompt File:** `docs/prompts/02_stage1.md`

---

### Stage 2
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Database Models
**Summary:** Added `app/core/database.py` (SQLAlchemy engine/session
factory) and four models — `Agent`, `Post`, `RejectedTopic`,
`SourceCache` — matching the PRD's memory requirements. `Post.rationale`
and `Post.sources` are non-nullable to enforce the "every post has
rationale and sources" success criterion at the schema level. Verified
with a standalone script that creates all tables and round-trips one
row per table against a throwaway SQLite file.
**Files Changed:**
- `backend/app/core/database.py`
- `backend/app/models/agent.py`
- `backend/app/models/post.py`
- `backend/app/models/rejected_topic.py`
- `backend/app/models/sources_cache.py`
- `backend/app/models/__init__.py`
- `backend/scripts/test_models.py`
- `backend/scripts/__init__.py`
**Commit:** `feat(backend): add SQLAlchemy models for agents, posts, rejected_topics, sources_cache`
**Prompt File:** `docs/prompts/03_stage2.md`
