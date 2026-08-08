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

---

### Stage 3
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Frontend Skeleton
**Summary:** Bootstrapped the Next.js 14 (App Router) frontend with
exactly the two pages the PRD allows — Landing (`/`) and Feed
(`/feed`) — as static skeletons with no API calls yet. Landing shows
project name, persona placeholder, description, a static "Not
Initialized" status badge, and a disabled Initialize button (wired to
`POST /api/agent/init` in Stage 4). Feed shows a static empty state
(wired to `GET /api/agent/feed` in Stage 19). Used plain CSS (no UI
framework) to keep the dependency footprint minimal per PRD scope.
Pinned `next` to `14.2.35` (latest patched 14.2.x) instead of the
originally-planned `14.2.5`, which has a known security advisory.
Verified with `npm install` + `npx next build`: both routes compile
and prerender as static content with no errors; `node_modules` and
`.next` removed before packaging.
**Files Changed:**
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/next.config.js`
- `frontend/.gitignore`
- `frontend/app/layout.tsx`
- `frontend/app/globals.css`
- `frontend/app/page.tsx`
- `frontend/app/feed/page.tsx`
- `README.md`
**Commit:** `feat(frontend): bootstrap Next.js app router skeleton with Landing and Feed pages`
**Prompt File:** `docs/prompts/04_stage3.md`

---

### Stage 4
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** `POST /api/agent/init` (basic)
**Summary:** Wired the first real backend route. `app/routes/agent.py`
exposes `POST /api/agent/init`; `app/services/agent_service.py` holds
the logic (`get_or_create_agent`) — creates an `Agent` row on first
call, returns the existing row unchanged on any later call, so the
endpoint is idempotent and matches the PRD's "evaluator calls init
exactly once" contract without blocking repeated local-dev testing.
`app/schemas/agent.py` adds `AgentInitResponse`. `main.py` now calls
`init_db()` on FastAPI startup and includes the agent router. No
persona/LLM/Breeth logic yet — the created row just carries the
`Agent` model's defaults (`persona_name="Aether"`,
`status="initializing"`). Verified end-to-end: booted the server,
called `/api/agent/init` twice, confirmed identical `agentId` in both
responses and exactly one row in `agents` via direct sqlite3 query.
**Files Changed:**
- `backend/app/routes/agent.py`
- `backend/app/services/agent_service.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/agent.py`
- `backend/app/main.py`
- `README.md`
**Commit:** `feat(backend): add POST /api/agent/init with idempotent agent creation`
**Prompt File:** `docs/prompts/05_stage4.md`

---

### Stage 5
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Persona Bible + Prompt Builder
**Summary:** Added `app/core/persona.json` — Aether's static editorial
identity: tone, voice traits, editorial values, topics of interest/avoided,
sourcing standards, writing style rules, and a one-line sample of the
voice. Added `app/services/persona_service.py`, which loads and caches
that file and flattens it into a single reusable prompt string via
`build_voice_profile_prompt()` — plain prose, not raw JSON, since models
follow written instructions more reliably than a JSON blob asked to be
"interpreted." No LLM call happens this stage; the prompt is built but
not sent anywhere yet. Verified with a standalone script
(`scripts/test_persona.py`) that checks every required field is present
in the bible and that the generated prompt contains the persona name, a
voice trait, and the sample voice line.
**Files Changed:**
- `backend/app/core/persona.json`
- `backend/app/services/persona_service.py`
- `backend/scripts/test_persona.py`
- `README.md`
**Commit:** `feat(backend): add persona bible and voice-profile prompt builder`
**Prompt File:** `docs/prompts/06_stage5.md`

---

### Stage 6
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** LLMProvider Interface
**Summary:** Added `app/services/llm/base_provider.py` — an ABC
(`LLMProvider`) with `name`, `generate`, `judge`, and `summarize`, kept
as three separate methods (rather than one `generate` reused with
different prompts) so a provider can later tune params per call type
(e.g. lower temperature for judgment) without touching the others.
Added the first implementation, `app/services/llm/gemini_provider.py`
(`GeminiProvider`), which calls the Gemini REST `generateContent`
endpoint directly via `httpx` (already a dependency) rather than adding
the `google-genai` SDK, keeping the dependency footprint small for a
single-endpoint use case. Raises a clear `GeminiConfigError` if
`GEMINI_API_KEY` is missing rather than surfacing a raw HTTP/auth
failure. Added `GEMINI_MODEL` (default `gemini-2.5-flash`) to
`config.py`/`.env.example`. No factory and no wiring into `/init` this
stage — a provider is instantiated directly by the verification script
only. Verified with `scripts/test_llm_provider.py`: confirms the ABC
can't be instantiated directly, confirms `GeminiProvider` implements
the full interface, confirms the missing-key error path, and — since no
real `GEMINI_API_KEY` is available in this sandboxed environment —
skips the live API smoke test with an explicit message instead of
failing.
**Files Changed:**
- `backend/app/services/llm/__init__.py`
- `backend/app/services/llm/base_provider.py`
- `backend/app/services/llm/gemini_provider.py`
- `backend/scripts/test_llm_provider.py`
- `backend/app/core/config.py`
- `backend/.env.example`
- `README.md`
**Commit:** `feat(backend): add LLMProvider interface and Gemini implementation`
**Prompt File:** `docs/prompts/07_stage6.md`
