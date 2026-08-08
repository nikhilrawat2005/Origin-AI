# AETHER — PROJECT HANDOFF / RESUME DOCUMENT

> **Use this file to resume work if the conversation/context resets.**
> Paste this whole document into a new chat and say:
> **"Continue from Stage 5. Last delivered ZIP: aether-stage4.zip"**
> (update the stage number/zip name to whatever is current at that time)

---

## 1. What This Project Is

**Aether** — an Autonomous AI Technology Research Persona, built for the
ABTalks Hackathon.

Not a chatbot. Not a content generator. Once initialized (one API call),
it must independently:
- Discover AI/tech topics from live sources
- Decide (editorial judgment) whether a topic deserves publishing
- Maintain a consistent editorial persona/voice
- Remember previous publications (persistent memory, no repeats)
- Publish new content over time with **zero further human prompting**
- Attach rationale + sources to every published post

The evaluator calls `POST /api/agent/init` **exactly once**, then only
calls `GET /api/agent/feed` repeatedly. The feed must grow on its own.

## 2. Explicit Out-of-Scope (DO NOT BUILD)

Auth, login, user accounts, admin panel, settings, notifications,
analytics, comments, likes, followers, images, videos, LinkedIn/X
posting, multi-platform publishing, chat interface, vector database,
multi-agent architecture. If it's not in the PRD, don't build it.

## 3. Tech Stack (locked, do not change)

| Layer | Choice |
|---|---|
| Frontend | Next.js |
| Backend | FastAPI |
| Database | SQLite (via SQLAlchemy) |
| Memory | Breeth |
| LLM | Gemini, behind a provider abstraction (swappable) |
| Scheduler | APScheduler |
| Deployment | Railway |

## 4. Frontend Scope — ONLY 2 pages, ever

1. **Landing Page** — Project Name, Persona Name, Description, Agent
   Status, Initialize Button.
2. **Feed Page** — Generated Posts, Created Time, Rationale, Sources.

No dashboard, no analytics, no profile, no graphs, no settings.

## 5. Backend Scope — ONLY 2 public endpoints

- `POST /api/agent/init`
- `GET /api/agent/feed`

No other public APIs unless absolutely necessary.

## 6. Functional Flow

```
Initialization
  → Create Persona
  → Start Scheduler
  → Discover Topics
  → Editorial Evaluation
  → Memory Check
  → Generate Post
  → Save Memory
  → Publish
  → Feed API
```

## 7. Memory (Breeth) must store

Previous posts, rejected topics, persona preferences, editorial style,
publishing history.

## 8. Railway Env Vars

`GEMINI_API_KEY`, `BREETH_API_KEY`, `DATABASE_URL`, `APP_ENV`, `PORT`

## 9. Success Criteria

- Evaluator initializes agent once
- Posts appear automatically over time, feed grows with no human prompts
- Memory prevents repeated publishing
- Every post has rationale + sources
- Deploys on Railway
- Codebase stays modular and clean

## 10. Rule 13 — Mandatory Documentation System

Every stage must produce, before moving to the next stage:
1. Working code
2. Updated `README.md` (if the stage changes how to run/test)
3. Updated `docs/AI_USAGE_LOG.md` (master index, one entry per stage)
4. New `docs/prompts/0X_stageN.md` file (goal, prompts used, AI response
   summary, decisions taken — accepted/modified/rejected + why, files
   created, files modified, suggested git commit, stage outcome, next
   stage)
5. Suggested git commit message
6. A ZIP archive of the full project so far (cumulative, not per-stage delta)
7. Confirmation the code actually runs + how to test it manually

**Claude must stop after each stage and wait for user approval before
starting the next one.** Documentation is never postponed to the end.

## 11. The 20-Stage Plan

| # | Stage | Goal |
|---|---|---|
| 1 | Repo + Backend Skeleton | FastAPI boots, folders, config.py, .env.example, health check ✅ **DONE** |
| 2 | Database Models | SQLite + SQLAlchemy: agents, posts, rejected_topics, sources_cache (no routes) ✅ **DONE** |
| 3 | Frontend Skeleton | Next.js app router boots, empty Landing + Feed pages, no API calls yet ✅ **DONE** |
| 4 | `/api/agent/init` (basic) | Creates agent row, returns agentId — no persona/LLM logic yet ✅ **DONE** |
| 5 | Persona Bible + Prompt Builder | persona.json, persona_service.py builds voice profile (no LLM call yet) ⬅ **NEXT UP** |
| 6 | LLMProvider Interface | base_provider.py (generate/judge/summarize ABC) + Gemini provider |
| 7 | LLMFactory + Second Provider | llm_factory.py + openrouter_provider.py, env-driven switch |
| 8 | Wire LLM into Init | /init generates persona voice profile via LLMFactory, saves it |
| 9 | Breeth Client (connection only) | breeth_client.py — connect, write/read test fact, standalone script |
| 10 | Breeth Namespace on Init | /init creates Breeth namespace, stores breeth_agent_ref, SQLite mirror stub |
| 11 | Topic Sources Config + Fetcher | topic_sources.json + topic_discovery.py, raw candidates, no caching yet |
| 12 | Sources Cache | sources_cache wired in — dedup fetch, hash check |
| 13 | Fingerprinting | Normalized title+keywords+source → fingerprint function, unit-testable |
| 14 | Editorial Judgment | editorial_judgment.py — accept/reject + rejected_topics logging |
| 15 | Memory Service (Breeth dedup) | memory_service.py — Breeth + SQLite mirror query before accept |
| 16 | Post Writer | post_writer.py — text + rationale via LLMFactory, given judged topic + memory |
| 17 | Publisher | publisher.py — writes posts table, pushes summary to Breeth, marks published |
| 18 | Scheduler Wiring | APScheduler chains 11→14→15→16→17, PUBLISH_INTERVAL_MINUTES env-driven |
| 19 | Feed Endpoint + Feed Page | /api/agent/feed (exact PRD JSON shape) + Next.js Feed page live |
| 20 | Release Candidate | Railway deploy, API contract check, full E2E autonomous run, docs sync, final README, final ZIP |

## 12. Known Constraints Claude Flagged Upfront

1. Claude works in a sandboxed container — cannot actually `git push` or
   deploy to Railway. It generates commit messages, folder structure,
   and deployable code; the user runs the real push/deploy.
2. No real `GEMINI_API_KEY` / `BREETH_API_KEY` — Claude wires the
   integration correctly via `.env.example`; user supplies real keys to
   run live tests locally.
3. Breeth API is less familiar — Claude will web-search current Breeth
   docs before building `breeth_client.py` in Stage 9, rather than guess.

## 13. Progress So Far

### ✅ Stage 1 — Repo + Backend Skeleton (DONE)
- `backend/app/main.py` — FastAPI app, CORS, `GET /api/health`
- `backend/app/core/config.py` — centralized env-driven settings
- Empty `routes/`, `services/`, `models/` packages
- `requirements.txt`, `.env.example`, `README.md`
- Verified: server boots, `/api/health` returns
  `{"status":"ok","app":"aether-backend","env":"development"}`
- Commit: `feat(backend): bootstrap FastAPI skeleton with config and health check`

### ✅ Stage 2 — Database Models (DONE)
- `backend/app/core/database.py` — SQLAlchemy engine/session, `init_db()`
- `backend/app/models/agent.py` — Agent (persona, status, breeth_agent_ref)
- `backend/app/models/post.py` — Post (rationale + sources are **required**)
- `backend/app/models/rejected_topic.py` — RejectedTopic (with reason)
- `backend/app/models/sources_cache.py` — SourceCache (unique content_hash)
- `backend/scripts/test_models.py` — standalone verification script
- Verified: all 4 tables create, insert + read-back passes for each
- Commit: `feat(backend): add SQLAlchemy models for agents, posts, rejected_topics, sources_cache`

### ✅ Stage 3 — Frontend Skeleton (DONE)
- `frontend/` — Next.js 14.2.35 (App Router), TypeScript, plain CSS
  (no UI framework)
- `frontend/app/layout.tsx` — root layout + metadata
- `frontend/app/page.tsx` — Landing page: project name, persona
  placeholder, description, static "Not Initialized" badge, disabled
  Initialize button (wired to `POST /api/agent/init` in Stage 4)
- `frontend/app/feed/page.tsx` — Feed page: static empty state (wired
  to `GET /api/agent/feed` in Stage 19)
- No API calls anywhere yet — both pages are fully static, per scope
- Verified: `npm install` + `npx next build` compiles cleanly, both
  routes prerender as static content; `node_modules`/`.next` removed
  before packaging
- Commit: `feat(frontend): bootstrap Next.js app router skeleton with Landing and Feed pages`

### ✅ Stage 4 — `/api/agent/init` (basic) (DONE)
- `backend/app/routes/agent.py` — `POST /api/agent/init`
- `backend/app/services/agent_service.py` — `get_or_create_agent`:
  creates the agent row on first call, returns the same row (same
  `agentId`) on every later call — idempotent per PRD's "init called
  exactly once" contract
- `backend/app/schemas/agent.py` — `AgentInitResponse`
- `backend/app/main.py` — `init_db()` on startup, agent router included
- No persona/LLM/Breeth logic yet — row just carries model defaults
  (`persona_name="Aether"`, `status="initializing"`)
- Verified: booted server, called `/init` twice, confirmed identical
  `agentId` both times and exactly one row in `agents` via direct
  sqlite3 query
- Commit: `feat(backend): add POST /api/agent/init with idempotent agent creation`

### ✅ Stage 5 — Persona Bible + Prompt Builder (DONE)
- `backend/app/core/persona.json` — static editorial identity: tone,
  voice traits, editorial values, topics of interest/avoided, sourcing
  standards, writing style rules, sample voice line
- `backend/app/services/persona_service.py` — `load_persona()` (cached),
  `build_voice_profile_prompt()` (flattens the bible into a single
  prose prompt string), `get_persona_name()`
- `backend/scripts/test_persona.py` — standalone verification script
- No LLM call yet, not wired into `/init` yet — the LLMProvider
  abstraction (Stage 6/7) and the wiring itself (Stage 8) come later
- Verified: all required fields present in the bible, prompt built
  (2576 chars), contains persona name / a voice trait / the sample
  voice line
- Commit: `feat(backend): add persona bible and voice-profile prompt builder`

### ✅ Stage 6 — LLMProvider Interface (DONE)
- `backend/app/services/llm/base_provider.py` — `LLMProvider` ABC:
  `name` property + `generate`/`judge`/`summarize` methods
- `backend/app/services/llm/gemini_provider.py` — `GeminiProvider`,
  calls the Gemini REST `generateContent` endpoint via `httpx`; raises
  `GeminiConfigError` with an actionable message if `GEMINI_API_KEY`
  is missing
- `backend/app/core/config.py` / `.env.example` — added `GEMINI_MODEL`
  (default `gemini-2.5-flash`)
- `backend/scripts/test_llm_provider.py` — standalone verification
  script
- No factory yet, not wired into `/init` yet — that's Stage 7 (second
  provider + `llm_factory.py`) and Stage 8 (wiring) respectively
- Verified: ABC rejects direct instantiation, `GeminiProvider`
  implements the full interface, missing-key path raises a clear
  error; live API call correctly skipped (no real key in this
  sandbox, per Known Constraints)
- Commit: `feat(backend): add LLMProvider interface and Gemini implementation`

## 14. Last Delivered File

**`aether-stage6.zip`** — cumulative project ZIP containing everything
through Stage 6 (backend skeleton + all DB models + Next.js frontend
skeleton + `POST /api/agent/init` + persona bible/prompt builder +
LLMProvider interface/Gemini provider + docs for stages 0/1/2/3/4/5/6).

## 15. How To Resume

Paste this document into a new conversation and say:

> "Continue from Stage 7. Last delivered ZIP: aether-stage6.zip"

Claude should then:
1. Re-read this doc to restore full context (scope, stack, rules, plan)
2. Start Stage 7 exactly as planned: `llm_factory.py` (env-driven
   switch on `LLM_PROVIDER`) plus `openrouter_provider.py` as a second
   concrete `LLMProvider`
3. Continue following Rule 13 (docs + log + commit + ZIP + stop for
   approval) for every stage from there on
