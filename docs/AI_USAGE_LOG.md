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

---

### Stage 7
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** LLMFactory + Second Provider
**Summary:** Added `app/services/llm/openrouter_provider.py`
(`OpenRouterProvider`) — the second concrete `LLMProvider`, calling
OpenRouter's OpenAI-compatible `/chat/completions` endpoint via
`httpx`, mirroring `GeminiProvider`'s structure (`_call()` helper,
dedicated `OpenRouterConfigError` for a missing key). Added
`app/services/llm/llm_factory.py` — `get_llm_provider()`, a small
name-to-class registry keyed off `settings.llm_provider`
(case-insensitive), raising `UnknownLLMProviderError` for anything not
registered rather than silently defaulting. Added `OPENROUTER_API_KEY`
and `OPENROUTER_MODEL` (default `openai/gpt-4o-mini`) to
`config.py`/`.env.example`. From this stage on, the codebase's rule is
that nothing outside `app/services/llm/` should import a concrete
provider class directly — callers get an instance from
`get_llm_provider()` instead, which is what makes the provider
actually swappable per the PRD's "LLM: Gemini, behind a provider
abstraction (swappable)" line. No wiring into `/init` or any route
yet — that's Stage 8. Verified with `scripts/test_llm_factory.py`:
confirms `OpenRouterProvider` implements the full interface, confirms
its missing-key error path, confirms the factory resolves to
`GeminiProvider` by default and to `OpenRouterProvider` when asked,
confirms case-insensitive lookup, confirms an unknown provider name
raises `UnknownLLMProviderError`, and — since no real
`OPENROUTER_API_KEY` is available in this sandboxed environment —
skips the live API smoke test with an explicit message, same pattern
as Stage 6's Gemini test. Re-ran `scripts/test_llm_provider.py`
(Stage 6) to confirm nothing regressed.
**Files Changed:**
- `backend/app/services/llm/openrouter_provider.py`
- `backend/app/services/llm/llm_factory.py`
- `backend/app/services/llm/__init__.py`
- `backend/scripts/test_llm_factory.py`
- `backend/app/core/config.py`
- `backend/.env.example`
- `README.md`
**Commit:** `feat(backend): add LLMFactory and OpenRouter provider for env-driven LLM switching`
**Prompt File:** `docs/prompts/08_stage7.md`

---

### Stage 8
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Wire LLM into Init
**Summary:** `POST /api/agent/init` now does real work on first call.
`agent_service.get_or_create_agent()` sets `persona_name` from
`persona_service.get_persona_name()` (the persona bible, not the bare
model default) and, on creation only, calls
`_generate_persona_description()` — builds the voice-profile prompt
via `persona_service.build_voice_profile_prompt()` and sends it as the
`system` prompt to `get_llm_provider().generate()` (Stage 7's
factory), asking for a short landing-page-style bio. The LLM call is
wrapped in a broad try/except that logs a warning and returns `None`
on any failure — no real API key is available in this sandboxed
environment, and `/init` must still succeed and create the agent row
even without a live LLM, since blocking agent creation on an optional
enrichment call would violate the "evaluator calls init exactly once
and it must work" contract. Idempotency from Stage 4 is preserved:
generation only runs inside the `if existing is not None: return`
branch's else-path (i.e., only on the very first call), so repeat
`/init` calls never re-trigger an LLM call. `AgentInitResponse` gained
`personaDescription: str | None`. Verified with
`scripts/test_init_llm_wiring.py` against an in-memory SQLite DB and a
fake `LLMProvider`: confirms a new agent gets the correct
`persona_name` and the fake provider's generated description, confirms
the LLM is called exactly once even across a repeat `get_or_create_agent()`
call, and separately confirms the real graceful-fallback path (no
configured API key in this environment) still succeeds with
`persona_description=None`. Re-ran `scripts/test_llm_provider.py` and
`scripts/test_llm_factory.py` (Stages 6/7) to confirm no regressions.
**Files Changed:**
- `backend/app/services/agent_service.py`
- `backend/app/schemas/agent.py`
- `backend/app/routes/agent.py`
- `backend/scripts/test_init_llm_wiring.py`
- `README.md`
**Commit:** `feat(backend): generate persona description via LLM on agent init`
**Prompt File:** `docs/prompts/09_stage8.md`

---

### Stage 9
**Date:** 2026-08-07
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Breeth Client (connection only)
**Summary:** Per `PROJECT_STATUS.md`'s Known Constraint #3, fetched
current Breeth docs (docs.thebreeth.com) before writing any code
rather than guessing at the API shape. Confirmed: base URL
`https://api.thebreeth.com`, all routes under `/v1`, Bearer-token auth
(`ck_live_...` API keys), and a JSON error envelope
(`{"error": "<slug>", "message": "..."}`). Added
`app/services/breeth_client.py` (`BreethClient`) with two methods for
this stage's connection-test scope: `write_fact(subject, predicate,
object_, group_id, extract_intent)`, calling `POST /v1/facts` (chosen
over `POST /v1/episodes` for the write side of the test — it's the
structured, minimal-overhead ingest path, a better fit for "prove
connectivity" than the heavier prose-extraction pipeline episodes
run), and `search(query, group_id, limit)`, calling `POST /v1/search`
(hybrid BM25 + vector + graph retrieval) as the read side. Both raise
`BreethConfigError` if `BREETH_API_KEY` is unset (mirroring
`GeminiConfigError`/`OpenRouterConfigError` from Stages 6/7) and
`BreethAPIError` (carrying the parsed `slug`/`message`) on any
non-2xx response, so a caller can distinguish e.g. `quota_exceeded`
from `unauthenticated` without re-parsing the response. Added
`BREETH_BASE_URL` (default `https://api.thebreeth.com`) to
`config.py`/`.env.example` alongside the existing `BREETH_API_KEY`, so
the endpoint is swappable without a code change (useful if Breeth ever
ships a staging/self-hosted URL). No namespace-per-agent logic and no
wiring into `/init` yet — that's Stage 10. Verified with
`scripts/test_breeth_client.py`: confirms the missing-key path raises
`BreethConfigError`, and — since no real `BREETH_API_KEY` is available
in this sandboxed environment — conditionally runs a live round-trip
(write a uniquely-marked test fact, then search for that marker and
confirm it comes back) only if a key is present, skipped cleanly
otherwise with an explicit message, same pattern as Stage 6/7's
provider smoke tests. Re-ran `test_llm_provider.py`,
`test_llm_factory.py`, and `test_init_llm_wiring.py` to confirm no
regressions.
**Files Changed:**
- `backend/app/services/breeth_client.py`
- `backend/scripts/test_breeth_client.py`
- `backend/app/core/config.py`
- `backend/.env.example`
- `README.md`
**Commit:** `feat(backend): add Breeth client for facts/search with connection verification`
**Prompt File:** `docs/prompts/10_stage9.md`

---

### Stage 10
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Breeth Namespace on Init
**Summary:** Wired Stage 9's `BreethClient` into `POST /api/agent/init`.
`agent_service._breeth_group_id()` derives a deterministic `group_id`
(`agent-<agent_id>`) per agent — this doubles as the "namespace" since
Breeth scopes facts/search by `group_id` rather than exposing a
separate namespace-creation endpoint. `_create_breeth_namespace()`
best-effort writes an identity fact (`<persona_name> is_a autonomous
AI technology research persona`) into that group on agent creation
only, wrapped in the same broad try/except pattern as Stage 8's LLM
call — no real `BREETH_API_KEY` is available in this sandboxed
environment, and `/init` must still succeed without a live Breeth
call. Added `app/models/breeth_mirror.py` (`BreethMirrorFact`) as a
local SQLite mirror: every namespace-creation attempt writes a row
here recording `group_id`/`subject`/`predicate`/`object` and whether
the remote write actually `synced`, regardless of outcome — this
exists now as a stub so Stage 15's `memory_service` has a local
fallback to query if a live Breeth call fails later, rather than
introducing the table under time pressure then. `agent.breeth_agent_ref`
is always set to the computed `group_id` (unlike the LLM-generated
persona description, which is `None` on failure) since it's a locally
derived identifier, not something Breeth returns — valid to store and
retry against even when today's write fails. `AgentInitResponse`
gained `breethAgentRef`. Adding the new table required updating Stage
2's `test_models.py`, which asserted an exact table set — the one
regression this stage caused, caught by re-running it and fixed before
considering the stage done.
**Files Changed:**
- `backend/app/models/breeth_mirror.py`
- `backend/app/models/__init__.py`
- `backend/app/services/agent_service.py`
- `backend/app/schemas/agent.py`
- `backend/app/routes/agent.py`
- `backend/scripts/test_breeth_namespace.py`
- `backend/scripts/test_models.py`
- `PROJECT_STATUS.md`
**Commit:** `feat(backend): create per-agent Breeth namespace on init with local mirror`
**Prompt File:** `docs/prompts/11_stage10.md`
