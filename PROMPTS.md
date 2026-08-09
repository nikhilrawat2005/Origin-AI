# Aether — Prompt Log

Full prompt-by-prompt build history for Aether, in chronological order —
one section per stage, from initial planning through the release
candidate (Stage 20). Kept as proof of the vibe-coded build process, per
the hackathon's authenticity requirements. Post-hackathon fixes/features
(after Stage 20) are logged separately in `AI_USAGE_LOG.md`.

---

# Project Planning

## Goal
Establish the source-of-truth PRD for Aether, agree on scope boundaries
(what is explicitly out of scope), lock the tech stack, and break the
build into 20 independently testable stages before writing any code.

---

## Prompt(s)

The user supplied the full Aether PRD in one message, covering:
- Project objective and mandatory hackathon requirements
- Explicit out-of-scope list (auth, dashboards, multi-agent, etc.)
- Tech stack (Next.js, FastAPI, SQLite, Breeth, Gemini, APScheduler, Railway)
- Frontend scope (2 screens only: Landing, Feed)
- Backend scope (2 public endpoints only: `/api/agent/init`, `/api/agent/feed`)
- Functional flow (init → persona → scheduler → discovery → judgment →
  memory check → generate → save memory → publish → feed)
- Rule 13: mandatory AI development documentation system
  (`docs/AI_USAGE_LOG.md` + `docs/prompts/0X_stageN.md` per stage)
- A 20-stage build plan, each stage a single testable unit

---

## AI Response Summary

- Confirmed understanding of scope and constraints.
- Flagged three practical limitations up front rather than discovering
  them mid-project: (1) no direct git/Railway push access — commit
  messages and structure will be generated, actual push/deploy is the
  user's action; (2) no real API keys for Gemini/Breeth — will build
  correct integration code and `.env.example`, user supplies real keys
  to run live tests; (3) limited built-in knowledge of the Breeth API,
  so its client (Stage 9) will be built after a web search of current
  Breeth docs rather than guessed.
- Proposed following the stage plan exactly as given, stopping after
  each stage for approval per Rule 13's "Stage Completion Checklist."

## Decisions Taken

- **Accepted as-is:** the full 20-stage plan, tech stack, scope
  boundaries, and documentation system — no changes requested by AI.
- **Clarified:** deployment and git operations are advisory
  (Claude generates commands/messages; user executes them) since Claude
  operates in a sandboxed container without Railway/GitHub credentials.

## Files Created
None yet — this stage is planning only.

## Files Modified
None.

## Git Commit
N/A — no code produced in this stage.

## Stage Outcome
Shared understanding of the full project scope, constraints, and stage
sequence. No code written yet. Documentation system initialized.

## Next Stage
Stage 1 — Repo + Backend Skeleton: FastAPI app boots, folder structure,
`config.py`, `.env.example`, health check route.

---

# Stage 1 — Repo + Backend Skeleton

## Goal
Get a minimal FastAPI service booting cleanly with the correct folder
structure, centralized env-driven config, and a working health check —
the foundation every later stage builds on. No agent logic yet.

---

## Prompt(s)

User: "yes" (approval to begin Stage 1 after the planning discussion).

---

## AI Response Summary

- Created the backend package layout: `app/main.py`, `app/core/config.py`,
  and empty `app/routes/`, `app/services/`, `app/models/` packages
  (populated in later stages).
- `config.py` centralizes all environment variable reads via a single
  cached `Settings` object (pydantic-settings), so no other module ever
  calls `os.environ` directly — keeps Railway env wiring auditable.
- `main.py` wires CORS (open, since PRD explicitly excludes auth) and
  exposes `GET /api/health` for liveness checks.
- Added `requirements.txt` pinned to specific versions and a
  `.env.example` listing exactly the five variables the PRD requires
  (`GEMINI_API_KEY`, `BREETH_API_KEY`, `DATABASE_URL`, `APP_ENV`, `PORT`).
- Installed dependencies and ran the server locally to confirm
  `/api/health` returns `200 {"status":"ok", ...}` before marking the
  stage done.

## Decisions Taken

- **Accepted:** pydantic-settings for config over raw `os.getenv` calls —
  gives validation and a single typed source of truth, low overhead cost.
- **Accepted:** open CORS (`allow_origins=["*"]`) since the PRD explicitly
  puts authentication out of scope; revisit only if Railway deployment
  needs stricter rules.
- **Deferred:** database engine creation, SQLAlchemy models, and any
  routes beyond health — those are Stage 2 and Stage 4 respectively, to
  keep this stage a single testable unit per the plan.
- **Rejected:** nothing proposed was rejected — scope for this stage was
  narrow and unambiguous.

## Files Created
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/__init__.py`, `core/__init__.py`, `routes/__init__.py`,
  `services/__init__.py`, `models/__init__.py`
- `backend/requirements.txt`
- `backend/.env.example`
- `README.md`

## Files Modified
None (first code stage).

## Git Commit
```
feat(backend): bootstrap FastAPI skeleton with config and health check
```

## Stage Outcome
`uvicorn app.main:app` boots without error. `GET /api/health` verified
locally, returns `{"status":"ok","app":"aether-backend","env":"development"}`.
Folder structure and config pattern are in place for all later backend
stages to build on.

## Next Stage
Stage 2 — Database Models: SQLite + SQLAlchemy models for `agents`,
`posts`, `rejected_topics`, `sources_cache` (no routes yet).

---

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

---

# Stage 3 — Frontend Skeleton

## Goal
Boot a Next.js (App Router) frontend with exactly the two pages the PRD
allows — Landing and Feed — as static skeletons, with no API calls yet.

---

## Prompt(s)

User: "stage 3 se kam start karo" ("start work from stage 3" — approval to
proceed to Stage 3 after Stage 2 review, resuming from
`PROJECT_STATUS.md` + `aether-stage2.zip`).

---

## AI Response Summary

- Scaffolded `frontend/` as a Next.js 14 App Router project:
  `package.json`, `tsconfig.json`, `next.config.js`, `.gitignore`.
- `app/layout.tsx` — root layout, sets page metadata (title/description),
  imports `globals.css`.
- `app/globals.css` — minimal hand-written dark theme (no UI framework),
  since the PRD explicitly caps frontend scope at two pages and pulling
  in Tailwind/component libraries this early adds dependency weight for
  no benefit yet.
- `app/page.tsx` (Landing) — project name, persona placeholder
  ("Not yet initialized"), description, static "Not Initialized" status
  badge, and a **disabled** Initialize button. Button is intentionally
  inert — it's wired to `POST /api/agent/init` in Stage 4, not now.
- `app/feed/page.tsx` (Feed) — static empty-state card
  ("No posts yet..."). Wired to `GET /api/agent/feed` in Stage 19.
- Simple top nav (Landing / Feed) shared via `globals.css`, no separate
  nav component yet — only two links, doesn't earn its own file at this
  size.
- Verified the skeleton actually builds: `npm install` then
  `npx next build` — both routes compiled and prerendered as static
  content with zero errors. Removed `node_modules` and `.next` before
  packaging the ZIP.

## Decisions Taken

- **Accepted:** Plain CSS over Tailwind/component library — PRD caps
  the frontend at two pages with no dashboard/analytics/settings, so a
  styling framework is scope creep at this stage. Revisit only if a
  later stage's UI complexity actually demands it.
- **Modified:** Pinned `next` to `14.2.35` instead of the originally
  planned `14.2.5` — `14.2.5` carries a known security advisory
  (see Next.js security update, Dec 2025); `14.2.35` is the latest
  patched release on the same major/minor line, so no other behavior
  changes.
- **Accepted:** Initialize button rendered `disabled` rather than wired
  to a stub/fake handler — PRD Stage 3 scope is explicitly "no API
  calls yet"; a fake handler would misrepresent what's actually wired.
- **Deferred:** No shared `<Nav>` component, no design tokens file —
  two links and a handful of CSS variables don't yet justify the
  abstraction; will factor out if Stage 19's Feed page rendering adds
  real complexity.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/next.config.js`
- `frontend/.gitignore`
- `frontend/app/layout.tsx`
- `frontend/app/globals.css`
- `frontend/app/page.tsx`
- `frontend/app/feed/page.tsx`

## Files Modified
- `README.md` — project status bumped to Stage 3, frontend run
  instructions added.

## Git Commit
```
feat(frontend): bootstrap Next.js app router skeleton with Landing and Feed pages
```

## Stage Outcome
`npx next build` inside `frontend/` compiles cleanly and prerenders both
`/` and `/feed` as static routes. `npm run dev` boots the dev server on
`http://localhost:3000` with a working Landing page and Feed page — no
backend calls made, matching Stage 3 scope exactly.

## Next Stage
Stage 4 — `POST /api/agent/init` (basic): creates an `agent` row in
SQLite and returns `agentId`. No persona/LLM logic yet — that's Stage 5
onward.

---

# Stage 4 — `POST /api/agent/init` (basic)

## Goal
Wire the first real backend route: creates an `agent` row in SQLite and
returns `agentId`. No persona/LLM logic yet — that starts Stage 5.

---

## Prompt(s)

User: "start work on stage 4" (approval to proceed to Stage 4 after
reviewing the uploaded `aether-stage3.zip` and `PROJECT_STATUS.md`).

---

## AI Response Summary

- `backend/app/services/agent_service.py` — `get_or_create_agent(db)`:
  queries for the most recently created `Agent` row; returns it if
  present, otherwise creates one and commits. This is the one
  substantive design decision this stage — see below.
- `backend/app/routes/agent.py` — `POST /api/agent/init`, depends on
  `get_db`, calls the service, returns an `AgentInitResponse`.
- `backend/app/schemas/agent.py` — `AgentInitResponse` (agentId, status,
  personaName, createdAt). Built manually in the route rather than via
  `from_attributes` because the API field names (`agentId`,
  `personaName`) intentionally differ from the ORM column names
  (`id`, `persona_name`) and auto-mapping would silently break if
  either side's naming drifted.
- `backend/app/main.py` — added a `startup` event calling `init_db()`
  (idempotent — `create_all()` no-ops on existing tables) and
  `app.include_router(agent_routes.router)`. Added `import app.models`
  so all four models are registered on `Base.metadata` before
  `init_db()` runs (previously only exercised via the standalone
  Stage 2 test script, which imports models directly).
- Verified live: started uvicorn, called `/api/agent/init` twice,
  confirmed both responses return the identical `agentId`, then
  queried `agents` via `sqlite3` directly and confirmed exactly one
  row exists. Deleted the throwaway `aether.db` before packaging.

## Decisions Taken

- **Accepted:** Idempotent `/init` — instead of erroring or blindly
  inserting a new row on repeat calls, return the existing agent
  unchanged. The PRD says the evaluator calls init "exactly once," but
  a hackathon demo/dev loop will hit it more than once; idempotency
  satisfies both without adding an error path the PRD never asked for.
  This was already flagged as the intended design in the Stage 2
  `Agent` model docstring, so Stage 4 just implements it.
- **Accepted:** Manual field-by-field construction of
  `AgentInitResponse` over `model_validate(agent)` with
  `from_attributes=True` + aliases — fewer moving parts to get wrong
  for a 4-field response, and it stays correct even if the ORM and API
  field names diverge further later.
- **Deferred:** No `DELETE`/reset endpoint for agents, even though it'd
  help local testing — out of scope per PRD section 5 ("no other public
  APIs unless absolutely necessary"). Devs can just delete `aether.db`.
- **Deferred:** Response still returns model defaults for persona name
  — real persona generation is explicitly Stage 5 (persona.json +
  prompt builder) and Stage 8 (LLM-wired). Not pulled forward.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/routes/agent.py`
- `backend/app/services/agent_service.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/agent.py`

## Files Modified
- `backend/app/main.py` — startup hook (`init_db()`), router include,
  model registration import.
- `README.md` — project status bumped to Stage 4, repo tree updated,
  Stage 4 verification section added.

## Git Commit
```
feat(backend): add POST /api/agent/init with idempotent agent creation
```

## Stage Outcome
Backend boots with `uvicorn app.main:app --reload --port 8000`, tables
are created automatically on startup, and `curl -X POST
http://localhost:8000/api/agent/init` returns a valid
`agentId`/`status`/`personaName`/`createdAt` payload. Calling it a
second time returns the same `agentId` — confirmed via direct
`sqlite3` query showing exactly one row in `agents` after two calls.

## Next Stage
Stage 5 — Persona Bible + Prompt Builder: `persona.json` +
`persona_service.py` build a voice profile (no LLM call yet — that's
Stage 6/8).

---

# Stage 5 — Persona Bible + Prompt Builder

## Goal
Define Aether's editorial identity as a static file (`persona.json`) and
a service (`persona_service.py`) that turns it into a voice-profile
prompt. No LLM call yet — that starts Stage 6 (provider interface) and
is actually used for the first time in Stage 8 (wired into `/init`).

---

## Prompt(s)

User: "now make stage 5" (approval to proceed after reviewing the
uploaded `aether-stage4.zip` and `PROJECT_STATUS.md`).

---

## AI Response Summary

- `backend/app/core/persona.json` — the persona bible. Fields: `name`,
  `tagline`, `description`, `tone` (primary + avoid list), `voice_traits`,
  `editorial_values`, `topics_of_interest`, `topics_avoided`,
  `sourcing_standards` (minimum_sources + preferred/disallowed source
  types), `writing_style_rules`, `sample_voice`. Every field maps
  directly to something the PRD asks Aether to have an opinion about:
  editorial judgment (Stage 14), sourcing (Stage 15/16), and consistent
  voice across every future post.
- `backend/app/services/persona_service.py`:
  - `load_persona()` — reads and `@lru_cache`s the JSON file. Cached
    because the bible is static config, not per-agent state; per-agent
    state (the LLM-generated `persona_description` on the `Agent` row)
    stays separate and is Stage 8's job.
  - `build_voice_profile_prompt(persona=None)` — flattens the bible into
    one prose string in the bible's field order, so nothing is silently
    dropped if the bible grows later. Chose prose over handing the raw
    JSON to the model — see decisions below.
  - `get_persona_name()` — thin accessor Stage 8 will use to seed
    `Agent.persona_name` without needing the full prompt.
- `backend/scripts/test_persona.py` — standalone verification: loads the
  bible, asserts all 11 required fields exist, builds the prompt, asserts
  it's non-trivial length and contains the persona name / first voice
  trait / sample voice line (a cheap "nothing got silently dropped"
  check), and checks `get_persona_name()`. Ran it directly — all checks
  passed, prompt built to 2576 chars.

## Decisions Taken

- **Accepted:** Prose output from `build_voice_profile_prompt()` instead
  of returning/serializing the raw JSON for the model to interpret.
  Instruction-following models are more reliable with written directives
  ("Avoid: breathless hype, clickbait framing...") than with a nested
  JSON object they're implicitly asked to parse and obey. This is the
  one real design decision of the stage.
- **Accepted:** `persona.json` lives under `app/core/`, next to
  `config.py`, not in a new top-level `persona/` package — it's static
  config like `.env.example`, not a service with logic.
- **Accepted:** `load_persona()` is cached but takes no dependency on
  the database — this stage is about the *template* voice, not any
  specific agent's stored state, keeping it decoupled from Stage 4's
  `Agent` model.
- **Deferred:** Nothing about editorial *judgment* (accept/reject logic)
  is implemented here — that's Stage 14 and will consume this prompt,
  not duplicate it.
- **Deferred:** Not wired into `/api/agent/init` or any route yet. The
  LLMProvider abstraction this prompt will actually be sent through
  doesn't exist until Stage 6/7; wiring it into `/init` early would mean
  redoing that wiring in Stage 8 anyway.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/core/persona.json`
- `backend/app/services/persona_service.py`
- `backend/scripts/test_persona.py`

## Files Modified
- `README.md` — project status bumped to Stage 5, repo tree updated,
  Stage 5 verification section added.

## Git Commit
```
feat(backend): add persona bible and voice-profile prompt builder
```

## Stage Outcome
`python -m scripts.test_persona` (run from `backend/`) loads
`persona.json`, confirms all required fields are present, builds the
full voice-profile prompt, and asserts it contains the persona name, a
voice trait, and the sample voice line. All checks passed locally — see
output captured in this stage's development session. No database, no
network, no LLM call required for this stage's verification.

## Next Stage
Stage 6 — LLMProvider Interface: `base_provider.py` (an ABC with
`generate` / `judge` / `summarize`) plus a first concrete
`gemini_provider.py` implementation. This is what will eventually carry
`persona_service.build_voice_profile_prompt()` to a real model call.

---

# Stage 6 — LLMProvider Interface

## Goal
Define the interface every LLM backend implements (`base_provider.py`)
and ship the first concrete implementation (`gemini_provider.py`). No
factory and no wiring into `/init` yet — Stage 7 adds a second provider
and the factory; Stage 8 is the first place any of this actually gets
called from a route.

---

## Prompt(s)

User: "now stage 6" (approval to proceed after reviewing the delivered
`aether-stage5.zip`).

---

## AI Response Summary

- `backend/app/services/llm/base_provider.py` — `LLMProvider(ABC)` with
  four members: `name` (property, for logging/debugging) and three
  abstract methods — `generate`, `judge`, `summarize` — all sharing the
  shape `(prompt, system=None) -> str`. Kept as three distinct methods
  instead of one `generate()` reused with different prompts, so a
  concrete provider can later give judgment calls different model
  parameters (e.g. lower temperature, a cheaper model) than long-form
  post writing, without changing the interface.
- `backend/app/services/llm/gemini_provider.py` — `GeminiProvider`.
  Calls `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  directly via `httpx` rather than the `google-genai` SDK — researched
  current Gemini REST usage first (per the Stage 0 flag about
  unfamiliar APIs, applied here proactively rather than waiting for the
  Breeth stage where it was originally flagged), confirmed the
  `x-goog-api-key` header + `contents`/`systemInstruction` request
  shape is current. One extra dependency avoided since `httpx` is
  already in `requirements.txt`. `judge()` and `summarize()` both
  route through a shared private `_call()`; `summarize()` wraps the
  text in a short fixed instruction rather than exposing a separate
  prompt-template system this early.
  - Raises `GeminiConfigError` (a `RuntimeError` subclass) with an
    actionable message if `GEMINI_API_KEY` is unset, instead of letting
    the call fail deep inside `httpx` with a confusing 401.
- `backend/app/core/config.py` / `.env.example` — added `GEMINI_MODEL`
  (default `gemini-2.5-flash`) so the model is swappable per deployment
  without a code change.
- `backend/scripts/test_llm_provider.py` — standalone verification:
  confirms `LLMProvider()` raises `TypeError` (proves it's a real ABC,
  not just a class with `pass` bodies), confirms `GeminiProvider` is an
  `LLMProvider` instance with `name == "gemini"` and all three methods
  callable, confirms the missing-key path raises `GeminiConfigError`,
  and conditionally runs one live `generate()` call only if
  `GEMINI_API_KEY` is present in the environment — skipped cleanly
  otherwise, per the Stage 0 "no real API keys in this sandbox"
  constraint. Ran it — all checks passed, live call correctly skipped.

## Decisions Taken

- **Accepted:** REST via `httpx` over the `google-genai` SDK. Fewer new
  dependencies, and the interface this stage needs (one endpoint, plain
  JSON in/out) doesn't benefit from an SDK's extra surface (streaming,
  file uploads, embeddings) that this project doesn't use anywhere in
  the PRD.
- **Accepted:** `judge()` and `summarize()` implemented as thin wrappers
  around the same `_call()` as `generate()` for now, rather than fully
  separate code paths — the interface exists to let that change later
  (Stage 14/16 may want different temperature/model per method) without
  breaking callers; there's no reason to duplicate logic before there's
  an actual reason to diverge.
- **Accepted:** A dedicated `GeminiConfigError` instead of letting a
  missing key surface as an `httpx.HTTPStatusError` from a 401 — much
  clearer for local dev and for the evaluator if a key is ever missing
  at demo time.
- **Deferred:** No retry/backoff logic on the HTTP call — out of scope
  until a stage actually depends on this running unattended (Stage 18's
  scheduler). Revisit then if flakiness shows up.
- **Deferred:** No token/cost accounting — not in the PRD's success
  criteria.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/llm/__init__.py`
- `backend/app/services/llm/base_provider.py`
- `backend/app/services/llm/gemini_provider.py`
- `backend/scripts/test_llm_provider.py`

## Files Modified
- `backend/app/core/config.py` — added `gemini_model` setting.
- `backend/.env.example` — added `GEMINI_MODEL`.
- `README.md` — project status bumped to Stage 6, repo tree updated,
  Stage 6 verification section added, env var list updated.

## Git Commit
```
feat(backend): add LLMProvider interface and Gemini implementation
```

## Stage Outcome
`python -m scripts.test_llm_provider` (run from `backend/`) confirms
`LLMProvider` is a true ABC, `GeminiProvider` implements the full
interface, and the missing-API-key path fails clearly instead of
confusingly. Live Gemini call is skipped in this environment (no real
`GEMINI_API_KEY` available) — confirmed the skip path itself works
correctly and printed the expected message. No database, no routes, no
scheduler touched this stage.

## Next Stage
Stage 7 — LLMFactory + Second Provider: `llm_factory.py` (env-driven
switch on `settings.llm_provider`) plus `openrouter_provider.py` as the
second concrete `LLMProvider`.

---

# Stage 7 — LLMFactory + Second Provider

## Goal
Add a second `LLMProvider` implementation (OpenRouter) and
`llm_factory.py`, which picks between it and `GeminiProvider` off
`settings.llm_provider`. This is the point at which the rest of the
codebase should start depending on `LLMProvider` + the factory instead
of a concrete class — nothing gets wired into a route yet (that's
Stage 8), but the abstraction itself needs to be provably swappable
before anything depends on it.

---

## Prompt(s)

User: "stage 7 bnao" (build stage 7), after reviewing the delivered
`aether-stage6.zip`.

---

## AI Response Summary

- `backend/app/services/llm/openrouter_provider.py` —
  `OpenRouterProvider`. Calls
  `https://openrouter.ai/api/v1/chat/completions` directly via
  `httpx`, same dependency-minimalism reasoning as `GeminiProvider`
  (Stage 6): no new dependency, and OpenRouter's OpenAI-compatible
  shape is small enough that an SDK adds nothing here. Structured to
  mirror `GeminiProvider` closely — a shared private `_call()`,
  `judge()`/`summarize()` as thin wrappers around it, a dedicated
  `OpenRouterConfigError` for a missing key — specifically so the two
  providers read as genuinely interchangeable, not superficially
  similar. Chose OpenRouter as the second provider because it fronts
  many models behind one API shape, which is a better test of the
  `LLMProvider` abstraction than picking another single-model API
  would be: if Aether's pipeline can talk to it through the same
  interface, the interface isn't secretly Gemini-shaped.
- `backend/app/services/llm/llm_factory.py` — `get_llm_provider()`.
  Internally a small `dict[str, type[LLMProvider]]` registry
  (`{"gemini": GeminiProvider, "openrouter": OpenRouterProvider}`)
  keyed by `settings.llm_provider`, lowercased for a case-insensitive
  match. Raises `UnknownLLMProviderError` (not a silent fallback to
  Gemini) if `LLM_PROVIDER` is misspelled or unset to something
  unrecognized — a wrong provider name failing loudly at startup is
  much better than it silently running against the wrong model.
  Accepts an optional explicit `provider_name` argument (default
  `None`, falls back to the env-driven setting) so tests/scripts can
  force a specific provider without mutating `.env`.
- `backend/app/core/config.py` / `.env.example` — added
  `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` (default
  `openai/gpt-4o-mini` — cheap/fast default, swappable per
  deployment), matching the `GEMINI_API_KEY`/`GEMINI_MODEL` pattern
  from Stage 6.
- `backend/app/services/llm/__init__.py` — docstring updated to state
  the new package-level rule now that the factory exists: routes/
  services outside `app/services/llm/` should call
  `get_llm_provider()` rather than importing a concrete provider
  class. (Nothing outside the package imports a provider yet — this
  is a rule for Stage 8 onward, stated now so it isn't missed.)
- `backend/scripts/test_llm_factory.py` — standalone verification,
  structured to parallel `test_llm_provider.py`: confirms
  `OpenRouterProvider` implements the full interface and reports
  `name == "openrouter"`; confirms its missing-key path raises
  `OpenRouterConfigError`; confirms `get_llm_provider()` with no args
  resolves to `GeminiProvider` (proving the `.env` default actually
  takes effect), confirms `get_llm_provider("openrouter")` resolves to
  `OpenRouterProvider`, confirms `get_llm_provider("GEMINI")` also
  resolves correctly (case-insensitivity), confirms
  `get_llm_provider("not-a-real-provider")` raises
  `UnknownLLMProviderError`; and conditionally runs one live
  OpenRouter `generate()` call only if `OPENROUTER_API_KEY` is present
  — skipped cleanly otherwise, per the same sandboxed-environment
  constraint noted for Gemini in Stage 6.
- Ran both `scripts/test_llm_factory.py` (new) and
  `scripts/test_llm_provider.py` (Stage 6, re-run to check for
  regressions) — all checks passed. Note on how this was verified:
  this sandboxed container has no network access, so
  `pip install -r requirements.txt` could not reach PyPI this session.
  Rather than skip verification, minimal local stand-ins for `httpx`
  and `pydantic_settings` were placed on `PYTHONPATH` (not shipped in
  the project) purely so the real project code — unmodified — could be
  imported and its actual logic (ABC enforcement, factory switching,
  error paths) exercised end-to-end offline. The live-API-call branch
  in both scripts still correctly self-skips regardless, since no real
  key is configured either way — this is orthogonal to the network
  constraint and would skip the same way with real dependencies
  installed.

## Decisions Taken

- **Accepted:** Dict-based registry in `llm_factory.py` over an
  if/elif chain — trivial to extend with a third provider later
  (append one entry), and it's the natural shape for "name → class"
  lookups.
- **Accepted:** `UnknownLLMProviderError` on a bad `LLM_PROVIDER`
  value instead of silently defaulting to Gemini. A misconfigured env
  var should fail at the point it's read, not surface later as
  mysteriously-wrong model output.
- **Accepted:** OpenRouter as the second provider (matches the
  original Stage 7 plan in `PROJECT_STATUS.md`) — reasoning above on
  why it's a better abstraction test than a second single-model API.
- **Accepted:** Case-insensitive provider name matching — env vars get
  typed by hand often enough that `LLM_PROVIDER=Gemini` shouldn't be a
  hard failure.
- **Deferred:** No retry/backoff, no token/cost accounting — same
  deferral as Stage 6, for the same reason (out of scope until Stage
  18's scheduler actually needs unattended reliability).
- **Deferred:** No caching of the constructed provider instance inside
  `get_llm_provider()` (it constructs a fresh one per call). Providers
  are cheap to construct (no connection pooling, no I/O in `__init__`)
  so there's no performance reason to cache yet; revisit only if a
  future stage shows otherwise.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/llm/openrouter_provider.py`
- `backend/app/services/llm/llm_factory.py`
- `backend/scripts/test_llm_factory.py`

## Files Modified
- `backend/app/services/llm/__init__.py` — docstring updated for the
  post-factory package rule.
- `backend/app/core/config.py` — added `openrouter_api_key`,
  `openrouter_model` settings.
- `backend/.env.example` — added `OPENROUTER_API_KEY`,
  `OPENROUTER_MODEL`.
- `README.md` — project status bumped to Stage 7, repo tree updated,
  Stage 7 verification section added, env var list updated.

## Git Commit
```
feat(backend): add LLMFactory and OpenRouter provider for env-driven LLM switching
```

## Stage Outcome
`python -m scripts.test_llm_factory` (run from `backend/`) confirms
`OpenRouterProvider` implements the full `LLMProvider` interface, its
missing-key path fails clearly, and — the actual point of this stage —
`get_llm_provider()` genuinely switches between `GeminiProvider` and
`OpenRouterProvider` based on `LLM_PROVIDER`, with a loud failure for
an unrecognized value instead of a silent wrong default.
`scripts/test_llm_provider.py` (Stage 6) re-run to confirm no
regression. Live OpenRouter call is skipped in this environment (no
real `OPENROUTER_API_KEY` available) — confirmed the skip path itself
works correctly. No database, no routes, no scheduler touched this
stage.

## Next Stage
Stage 8 — Wire LLM into Init: `/init` calls
`persona_service.build_voice_profile_prompt()` (Stage 5) and passes it
through `get_llm_provider().generate()` (Stage 7's factory) to produce
and save the agent's actual voice profile — the first place any of the
LLM abstraction gets called from a real request.

---

# Stage 8 — Wire LLM into Init

## Goal
Make `POST /api/agent/init` generate the agent's actual persona voice
profile via the LLM on creation, using Stage 5's prompt builder and
Stage 7's provider factory — the first place any of the LLM
abstraction gets called from a real request path.

---

## Prompt(s)

User: "now stage 8", after reviewing the delivered `aether-stage7.zip`.

---

## AI Response Summary

- `backend/app/services/agent_service.py` — `get_or_create_agent()`
  now sets `persona_name` from `persona_service.get_persona_name()`
  (the bible's actual name) instead of relying on the `Agent` model's
  bare `"Aether"` default — same value today, but correct even if the
  bible's name ever changes. On creation only, calls a new private
  helper, `_generate_persona_description()`, which builds the
  voice-profile prompt (`persona_service.build_voice_profile_prompt()`)
  and sends a short fixed instruction through
  `get_llm_provider().generate()`, with the voice profile as the
  `system` prompt. The instruction explicitly asks for a third-person,
  no-greeting bio — matches how `persona_description` will actually be
  displayed on the landing page (Stage 3's frontend scope), not a
  chatty reply.
  - The whole call is wrapped in `try/except Exception` (broad on
    purpose) that logs a warning and returns `None` rather than
    letting the exception propagate. Reasoning: this sandboxed
    environment has no real `GEMINI_API_KEY`/`OPENROUTER_API_KEY` (per
    `PROJECT_STATUS.md`'s "Known Constraints"), so an unhandled
    exception here would make `/init` fail outright — which breaks the
    PRD's core contract ("the evaluator calls init exactly once");
    that call must succeed. A missing/broken LLM degrades the response
    (`persona_description: null`) instead of blocking the whole
    pipeline. This mirrors `GeminiProvider`'s own philosophy from
    Stage 6 (fail clearly, don't block) one level higher: the provider
    fails clearly *inside* itself, and the caller here decides that
    failure shouldn't be fatal to agent creation.
  - Placed *inside* the `if existing is not None: return` branch's
    implicit else — i.e., only reached on the very first successful
    creation — so idempotency (Stage 4's core guarantee) is untouched:
    a second `/init` call still returns the same row without a second
    LLM call, confirmed explicitly in the test via a call counter.
- `backend/app/schemas/agent.py` — added
  `personaDescription: str | None = None` to `AgentInitResponse`.
- `backend/app/routes/agent.py` — passes `agent.persona_description`
  through in the response; no other route logic changed.
- `backend/scripts/test_init_llm_wiring.py` — standalone verification,
  offline-runnable without a real API key:
  - Uses an in-memory SQLite session (`sqlite:///:memory:`) so the test
    doesn't touch `aether.db` or require any server running.
  - Injects a `FakeProvider` (matching the `LLMProvider` interface) by
    monkeypatching `agent_service.get_llm_provider` for the duration of
    the first two checks, with a call counter to prove the LLM is
    called exactly once across two `get_or_create_agent()` calls.
  - Restores the real `get_llm_provider` afterward and calls
    `_generate_persona_description()` directly against whatever
    provider is actually configured — in this environment that's
    `GeminiProvider` with no key, so it exercises the real
    graceful-fallback path (not a fake), confirming the fallback
    logic itself (not just the mock) works, and that
    `get_or_create_agent()` still succeeds afterward regardless of the
    outcome.
- Ran `test_init_llm_wiring.py`, plus re-ran `test_llm_provider.py`
  (Stage 6) and `test_llm_factory.py` (Stage 7) to check for
  regressions. Same offline-verification note as Stage 7: this sandbox
  has no network access this session, so the real `sqlalchemy`,
  `httpx`, and `pydantic_settings` packages could not be installed
  from PyPI. Minimal local stand-ins for those three (not shipped in
  the project) were placed on `PYTHONPATH` so the actual, unmodified
  project code could be imported and exercised end-to-end — including
  a working in-memory "SQLite" session store sufficient to prove
  `get_or_create_agent()`'s create/idempotency logic for real, not
  just import-check it. This is a test-environment workaround only;
  the shipped code has no dependency on the stubs and will run
  correctly against the real packages once `pip install -r
  requirements.txt` can reach PyPI.

## Decisions Taken

- **Accepted:** Broad `except Exception` around the LLM call in
  `_generate_persona_description()`, logging + returning `None` rather
  than raising. `/init` succeeding is a hard PRD requirement; a
  persona description is an enrichment, not a precondition for a valid
  agent row.
- **Accepted:** Generation gated to creation-only (not on every
  `/init` call) — preserves Stage 4's idempotency guarantee and avoids
  burning LLM calls/cost on repeated evaluator polling.
- **Accepted:** `persona_name` now sourced from `persona_service`
  instead of the model default — removes a second source of truth for
  the same value.
- **Deferred:** No retry on a failed generation call, and no way to
  manually re-trigger generation for an agent that already has
  `persona_description = None` — out of scope until there's a stage
  (or an ops need) that actually requires it; the PRD doesn't ask for
  this and adding it now would be an unrequested extra endpoint.
- **Deferred:** No storage of *why* generation failed (just a log
  line) — the PRD's "rationale" requirement is about published posts
  (Stage 16), not about `/init` itself, so no schema field was added
  for this.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/scripts/test_init_llm_wiring.py`

## Files Modified
- `backend/app/services/agent_service.py` — LLM-backed persona
  description generation on creation.
- `backend/app/schemas/agent.py` — added `personaDescription` field.
- `backend/app/routes/agent.py` — returns the new field.
- `README.md` — project status bumped to Stage 8, repo tree updated,
  Stage 8 verification section added.

## Git Commit
```
feat(backend): generate persona description via LLM on agent init
```

## Stage Outcome
`python -m scripts.test_init_llm_wiring` (run from `backend/`)
confirms a new agent gets its `persona_name` from the persona bible
and an LLM-generated `persona_description`, confirms the LLM is called
exactly once even across a repeat init, and confirms the real
graceful-fallback path (no API key configured, as expected in this
sandbox) still produces a valid agent with `persona_description = None`
instead of a failed request. `test_llm_provider.py` and
`test_llm_factory.py` re-run with no regressions. Frontend's
Initialize button is still not wired to this endpoint — that's a later
frontend stage once the feed (Stage 19) gives the flow something to
show after initializing.

## Next Stage
Stage 9 — Breeth Client (connection only): `breeth_client.py` —
connect, write/read a test fact, verified via a standalone script. Per
`PROJECT_STATUS.md`'s Known Constraints #3, current Breeth docs will
be web-searched first since the API is less familiar, rather than
guessed at.

---

# Stage 9 — Breeth Client (connection only)

## Goal
Add `breeth_client.py` — connect, write a test fact, read it back —
verified via a standalone script. Per `PROJECT_STATUS.md`'s Known
Constraint #3, web-search current Breeth docs first since the API is
unfamiliar, rather than guessing.

---

## Prompt(s)

User: "start", after reviewing the delivered `aether-stage8.zip`
(shorthand for "start the next stage," consistent with prior "now
stage N" approvals).

---

## AI Response Summary

- **Research first.** Searched the web for Breeth, landed on
  `thebreeth.com` (confirmed as the correct project — matches the
  `BREETH_API_KEY` env var name in `PROJECT_STATUS.md` and the
  "Memory: Breeth" line in the tech stack table), then fetched
  `docs.thebreeth.com` directly. Read the REST API overview page (base
  URL, auth, scopes, error envelope) and the three most relevant
  endpoint pages: `POST /v1/episodes`, `POST /v1/facts`, and
  `POST /v1/search`. Confirmed current, real API shapes rather than
  inferring from the marketing homepage's short MCP snippet.
- `backend/app/services/breeth_client.py` — `BreethClient`.
  - `write_fact()` → `POST /v1/facts`. Chose this over
    `POST /v1/episodes` for the stage's write-side test specifically
    because the docs describe it as "a fast write path" for
    already-structured S-P-O data with "minimal-overhead ingest,"
    versus episodes' heavier prose-extraction pipeline meant for
    natural-language content — a better fit for "prove the connection
    and credentials work" than for testing extraction quality. (Later
    stages that actually store post content/topics will decide between
    facts and episodes based on what's being written, not on this
    stage's precedent.)
  - `search()` → `POST /v1/search`, used as the read side of the
    connection test — write, then search for what was written.
  - `BreethConfigError` (missing key) and `BreethAPIError` (non-2xx,
    carrying the parsed `slug`/`message` from Breeth's JSON error
    envelope) — same pattern as `GeminiConfigError`/
    `OpenRouterConfigError` from Stages 6/7, so a bad `BREETH_API_KEY`
    fails exactly as clearly as a bad Gemini/OpenRouter key does.
    `BreethAPIError` additionally exposes the parsed slug because
    Breeth's error slugs are meaningfully different in what a caller
    should do next (`402 payment_required` vs `429 quota_exceeded` vs
    `403 missing_scope` all need different handling later, e.g. in
    Stage 15's memory-check logic) — worth not losing that at this
    layer even though nothing consumes it yet.
- `backend/app/core/config.py` / `.env.example` — added
  `BREETH_BASE_URL` (default `https://api.thebreeth.com`) alongside
  the existing `BREETH_API_KEY` — same swappable-per-deployment
  pattern as `GEMINI_MODEL`/`OPENROUTER_MODEL`.
- `backend/scripts/test_breeth_client.py` — standalone verification,
  same shape as Stage 6/7's scripts: confirms the missing-key error
  path, then conditionally runs a live test only if `BREETH_API_KEY`
  is set. The live test writes a fact whose object value is a
  freshly-generated UUID-based marker (not a fixed string), then
  searches for that exact marker and asserts it appears in the
  results — this makes the test self-contained and re-runnable against
  the same Breeth account without stale data from a previous run
  causing a false pass.
- Ran the new script plus re-ran `test_llm_provider.py`,
  `test_llm_factory.py`, and `test_init_llm_wiring.py` (Stages 6-8) —
  all passed, no regressions. Same offline-verification caveat as
  Stages 7-8: no network access to PyPI this session, so the real
  `httpx`/`pydantic_settings` packages could not be installed; the
  local stand-ins on `PYTHONPATH` (not shipped) were reused to import
  and exercise the actual, unmodified project code. This stage's live
  Breeth round-trip is additionally untestable regardless of stub
  status, since it requires real network access to `api.thebreeth.com`
  and a real API key — neither available in this sandbox — so the
  skip path (not the live path) is what's actually been exercised
  here; the live path is written to spec from the fetched docs but
  unverified against the real API until a key + network access are
  available.

## Decisions Taken

- **Accepted:** `POST /v1/facts` over `POST /v1/episodes` for this
  stage's write-side test, per the docs' own "when to use" guidance —
  structured atomic data, minimal overhead, exactly what a connection
  test needs.
- **Accepted:** `BreethAPIError` carries the parsed slug/message
  instead of just re-raising `httpx.HTTPStatusError` — Breeth's error
  slugs (`quota_exceeded`, `payment_required`, `missing_scope`, etc.)
  are semantically distinct enough that later stages (Stage 15's
  memory checks running unattended under the scheduler) will likely
  want to branch on them, so it's worth preserving now rather than
  re-adding this parsing later.
- **Accepted:** `BREETH_BASE_URL` as a separate configurable setting
  rather than hardcoding `api.thebreeth.com` — matches the
  `GEMINI_MODEL`/`OPENROUTER_MODEL` swappability precedent and costs
  nothing.
- **Deferred:** No namespace-per-agent (`group_id` scoping tied to a
  specific `Agent.breeth_agent_ref`) — that's explicitly Stage 10's
  job per the 20-stage plan. This stage's test script uses a
  throwaway `group_id: "stage9-test"`, not a real agent's namespace.
- **Deferred:** No retry/backoff on the HTTP call — same deferral
  reasoning as Stages 6/7 (out of scope until Stage 18's scheduler
  needs unattended reliability).
- **Deferred:** No wrapping of `POST /v1/episodes` yet — not needed
  for this stage's connection test; will likely be added once Stage
  15+ needs to write richer prose (e.g. full post content) into
  memory, at which point the choice between facts and episodes will be
  made per-call based on the content being written.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/breeth_client.py`
- `backend/scripts/test_breeth_client.py`

## Files Modified
- `backend/app/core/config.py` — added `breeth_base_url` setting.
- `backend/.env.example` — added `BREETH_BASE_URL`.
- `README.md` — project status bumped to Stage 9, repo tree updated,
  Stage 9 verification section added, env var list updated.

## Git Commit
```
feat(backend): add Breeth client for facts/search with connection verification
```

## Stage Outcome
`python -m scripts.test_breeth_client` (run from `backend/`) confirms
`BreethClient`'s missing-API-key path fails clearly. The live
write/search round-trip is implemented to the fetched API spec but
unverified against the real Breeth API in this session — no real
`BREETH_API_KEY` and no network access to `api.thebreeth.com` are
available in this sandboxed environment (see PROJECT_STATUS.md "Known
Constraints"); the script's skip path was confirmed to work correctly
instead. `test_llm_provider.py`, `test_llm_factory.py`, and
`test_init_llm_wiring.py` (Stages 6-8) re-run with no regressions. No
database changes, no routes touched, no scheduler touched this stage —
`Agent.breeth_agent_ref` (added to the model back in Stage 2) still
isn't populated by anything; that's Stage 10.

## Next Stage
Stage 10 — Breeth Namespace on Init: `/init` creates a Breeth
namespace (via `group_id`, scoped per-agent) and stores it on
`Agent.breeth_agent_ref`, with a SQLite mirror stub for whatever local
bookkeeping the memory layer needs before Stage 15's fuller
memory_service exists.

---

# Stage 10 — Breeth Namespace on Init

## Goal
`/init` creates a Breeth namespace, stores it on `Agent.breeth_agent_ref`,
and mirrors the attempt in a local SQLite stub table — per the
20-stage plan and Stage 9's deferred scope.

---

## Prompt(s)

User: "start with stage 10" (after uploading `aether-stage9.zip` and
`PROJECT_STATUS.md`).

---

## AI Response Summary

- **Verified the delivered ZIP first**, rather than trusting the
  uploaded `PROJECT_STATUS.md` at face value: unzipped
  `aether-stage9.zip`, cross-checked its `docs/AI_USAGE_LOG.md`,
  `docs/prompts/`, and `backend/app/services/` contents against the
  20-stage plan. Confirmed Stages 1-9 are genuinely done (matching
  code, tests, and log entries all present) even though the *uploaded*
  `PROJECT_STATUS.md` snapshot was stale (only reflected through Stage
  2) — the ZIP's own in-repo copy of that file was more current
  (through Stage 6) but itself hadn't been updated for Stages 7-9
  either, so it was caught up to Stage 9 as part of this stage's docs
  work before adding the Stage 10 entry.
- Breeth doesn't have an explicit "create namespace" call — namespace
  scoping is implicit via `group_id` on every fact/search call (per
  Stage 9's docs research). So "creating a namespace" means: pick a
  `group_id` for the agent, and write the first fact into it.
  `agent_service._breeth_group_id()` derives it deterministically as
  `f"agent-{agent.id}"` rather than anything Breeth generates.
- `_create_breeth_namespace()` writes one identity fact (persona name
  `is_a` "autonomous AI technology research persona") via Stage 9's
  `BreethClient.write_fact()`, wrapped in the same broad
  try/except-and-log pattern as Stage 8's LLM call — no real
  `BREETH_API_KEY` in this sandbox, and `/init` must still succeed
  without a live Breeth call.
- Key asymmetry vs. the LLM-generated persona description: `breeth_agent_ref`
  is set **regardless** of whether the remote write succeeds, because
  the `group_id` is a locally-derived identifier Aether owns, not
  something Breeth returns — it stays valid and retriable even if
  today's write failed, whereas a failed LLM call genuinely has no
  description to fall back to.
- Added `app/models/breeth_mirror.py` (`BreethMirrorFact`) as the
  "SQLite mirror stub" called for in the stage plan: one row per
  namespace-creation attempt, recording `group_id` /
  `subject`/`predicate`/`object` and a `synced` flag. Scoped narrowly —
  written on this one write path only, not queried by anything besides
  its own verification script yet — so Stage 15's `memory_service` has
  a local fallback table to build read paths against instead of
  introducing it under time pressure then.
- Wired `breethAgentRef` through `AgentInitResponse` and the route.
- `backend/scripts/test_breeth_namespace.py` — new standalone script,
  same in-memory-DB pattern as Stage 8's `test_init_llm_wiring.py`:
  confirms `breeth_agent_ref` is set and matches the deterministic
  group_id, confirms exactly one `BreethMirrorFact` row exists with
  `synced=False` (expected here, no real key), confirms a repeat
  `get_or_create_agent()` call doesn't create a duplicate mirror row.
- Ran a full server-boot smoke test via FastAPI's `TestClient` (using
  the `with TestClient(app) as c:` form so the startup event actually
  fires `init_db()`) — called `/api/agent/init` twice, confirmed
  `breethAgentRef` present and identical to `f"agent-{agentId}"` on
  both calls.
- Re-ran all prior verification scripts (Stages 2, 5, 6, 7, 8, 9).
  `scripts/test_models.py` failed on its exact-table-set assertion
  (`{"agents", "posts", "rejected_topics", "sources_cache"}`), since
  the new `breeth_mirror_facts` table is a real, intended schema
  change this stage — updated the assertion to include it and
  re-verified, rather than leaving a stale check in place.

## Decisions Taken

- **Accepted:** `group_id = f"agent-{agent.id}"` as the namespace
  identity, computed locally rather than requested from Breeth — no
  Breeth endpoint returns or reserves a namespace/group id, so there's
  nothing to request; the deterministic local id is both simpler and
  collision-free per agent.
- **Accepted:** `breeth_agent_ref` set unconditionally on creation
  (unlike `persona_description`, which stays `None` on LLM failure) —
  justified above; flagged explicitly in both the code docstring and
  this log so it isn't misread later as an inconsistency with Stage
  8's pattern.
- **Accepted:** `BreethMirrorFact` as a new table now, even though nothing outside
  this write path and its own test reads it yet — it's explicitly
  named in the stage plan ("SQLite mirror stub") and Stage 15 will
  need somewhere to build a fallback query against; better to land the
  schema now under this stage's docs/testing discipline than add it
  ad hoc later.
- **Accepted:** updating Stage 2's `test_models.py` in this stage
  rather than treating the regression as out of scope — Rule 13
  requires "confirmation the code actually runs," and a stale
  assertion failing on legitimate schema growth isn't a passing test
  suite.
- **Accepted:** catching up the in-repo `PROJECT_STATUS.md` from Stage
  6 to Stage 9 before appending the Stage 10 entry, since it's the
  designated resume document and Rule 13 requires it stay current —
  leaving it 3 stages stale would break the "paste this doc into a new
  chat" resume flow the doc itself promises.
- **Deferred:** no read/query path against `BreethMirrorFact` yet —
  that's Stage 15's job (`memory_service.py`, Breeth + SQLite mirror
  query before accept).
- **Deferred:** no retry/backoff on the namespace write — same
  reasoning as Stages 6/7/9, deferred to Stage 18's scheduler.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/models/breeth_mirror.py`
- `backend/scripts/test_breeth_namespace.py`
- `docs/prompts/11_stage10.md`

## Files Modified
- `backend/app/models/__init__.py` — registered `BreethMirrorFact`.
- `backend/app/services/agent_service.py` — added
  `_breeth_group_id()`, `_create_breeth_namespace()`; wired into
  `get_or_create_agent()`.
- `backend/app/schemas/agent.py` — `AgentInitResponse.breethAgentRef`.
- `backend/app/routes/agent.py` — passes `breethAgentRef` through.
- `backend/scripts/test_models.py` — updated table-set assertion.
- `PROJECT_STATUS.md` — caught up Stages 7-9 (previously missing) and
  added the Stage 10 entry; bumped resume pointer to Stage 11 /
  `aether-stage10.zip`.
- `docs/AI_USAGE_LOG.md` — Stage 10 entry appended.

## Git Commit
```
feat(backend): create per-agent Breeth namespace on init with local mirror
```

## Stage Outcome
`python3 scripts/test_breeth_namespace.py` (run from `backend/`, venv
active) passes all three checks. Re-ran `test_models.py` (after fixing
its table-set assertion), `test_persona.py`, `test_llm_provider.py`,
`test_llm_factory.py`, `test_init_llm_wiring.py`, and
`test_breeth_client.py` — all pass, no other regressions. Full
FastAPI `TestClient` smoke test confirms the actual HTTP path: server
boots, `/api/health` returns 200, `POST /api/agent/init` called twice
returns the same `agentId` and a `breethAgentRef` of
`f"agent-{agentId}"` on both calls, with no duplicate `BreethMirrorFact`
row created on the second call. No live Breeth write was exercised
(no real `BREETH_API_KEY` in this sandbox, per Known Constraints) —
the graceful-fallback path (`synced=False`, `breeth_agent_ref` still
set) is what's actually been verified, same caveat as Stage 9.

## Next Stage
Stage 11 — Topic Sources Config + Fetcher: `topic_sources.json`
(source list/config) + `topic_discovery.py` (fetches raw topic
candidates from those sources), no caching/dedup yet — that's Stage
12's `sources_cache` wiring.

---

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

---

# Stage 12 — Sources Cache

## Goal
Wire `sources_cache` into the discovery path — dedup fetch, hash
check — per the 20-stage plan.

---

## Prompt(s)

User: "continue" (after approving Stage 11's `aether-stage11.zip`).

---

## AI Response Summary

- Reviewed the `SourceCache` model (Stage 2): `content_hash` is
  already `unique=True, index=True`, so the model was designed with
  this stage's dedup-by-hash approach in mind from the start.
- `compute_content_hash()` hashes `source_name + "|" + url` (SHA-256)
  rather than title — reasoning: the same URL from the same source
  fetched twice is always the same feed entry (a re-fetch of an
  unchanged feed), whereas two different stories from the same source
  could plausibly share very similar titles without being duplicates.
  Explicitly scoped narrower than Stage 13's planned fingerprinting
  (normalized title + keywords + source), which is meant to catch the
  *same underlying story* republished under a different URL — this
  stage only needs literal-URL-level dedup to stop re-caching/re-
  considering identical feed entries across scheduler runs.
- `filter_new_candidates()` checks candidates one at a time against
  the DB (not a single bulk `IN` query), specifically so that two
  candidates within the *same* discovery batch that hash identically
  (e.g. a feed listing the same item twice, or two sources returning
  overlapping content) don't both get inserted — the first occurrence
  claims the hash in the session, the second is filtered out against
  that now-updated state before the batch is committed.
- `discover_new_topics()` added as the single combined entry point
  (`discover_topics()` + `filter_new_candidates()`) that later stages
  will actually call — not wired into any route or scheduler yet,
  since neither exists until Stage 18.
- `backend/scripts/test_sources_cache.py` — four checks against an
  in-memory DB: hash determinism and sensitivity to both url and
  source; first-call caching of all new candidates; a repeat call with
  identical candidates returning nothing and creating no duplicate
  rows; a mixed batch (one already-cached candidate, one genuinely new
  candidate, and one in-batch duplicate sharing a URL with the new
  one) correctly returning exactly one new candidate and creating
  exactly one new row.
- Ran the new script, then re-ran all eight prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11) — all passed, no regressions.

## Decisions Taken

- **Accepted:** hash over `source_name + url` rather than title or
  full content — matches what `content_hash`'s `unique=True` was
  clearly designed to enforce, and keeps this stage's scope to literal
  re-fetch dedup rather than reaching into Stage 13's territory.
- **Accepted:** per-candidate DB lookups over a single batch query —
  correctness (no duplicate rows even within one batch) mattered more
  here than the minor query-count cost, especially since batch sizes
  from `discover_topics()` are small (tens of items, not thousands).
- **Accepted:** `discover_new_topics()` as a thin combining function
  now, even though nothing calls it yet — gives Stage 18 a single,
  already-tested entry point to wire into the scheduler chain instead
  of composing `discover_topics()` + `filter_new_candidates()` calls
  itself at that point.
- **Deferred:** fingerprint-based near-duplicate detection (same story,
  different URL/title) — Stage 13, as planned.
- **Deferred:** no expiry/pruning of old `sources_cache` rows — not
  called for by the PRD or the stage plan; the table is expected to
  grow unbounded for now, matching the "posts, rejected topics,
  publishing history" memory requirements language in
  `PROJECT_STATUS.md` §7, which doesn't mention pruning.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/sources_cache_service.py`
- `backend/scripts/test_sources_cache.py`
- `docs/prompts/13_stage12.md`

## Files Modified
- `README.md` — project status bumped to Stage 12, repo tree updated,
  Stage 12 verification section added.
- `PROJECT_STATUS.md` — Stage 12 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 12 entry appended.

## Git Commit
```
feat(backend): wire sources_cache into discovery for URL-level dedup
```

## Stage Outcome
`python3 scripts/test_sources_cache.py` (run from `backend/`, venv
active) passes all four checks against an in-memory SQLite DB. Re-ran
all eight prior verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11)
— all pass, no regressions. No routes touched, nothing wired into
`/init` or the (not-yet-existing) scheduler this stage —
`discover_new_topics()` exists as a standalone, directly-callable
function only, same posture as Stage 11's `discover_topics()`.

## Next Stage
Stage 13 — Fingerprinting: a normalized title + keywords + source ->
fingerprint function, unit-testable, to catch the same underlying
story appearing under a different URL or title variant — a level of
dedup this stage's literal URL-hash approach explicitly doesn't cover.

---

# Stage 13 — Fingerprinting

## Goal
A normalized title+keywords+source → fingerprint function,
unit-testable, per the 20-stage plan — distinct from Stage 12's
literal URL-hash dedup, meant to catch the same underlying story
republished under a different URL or title variant.

---

## Prompt(s)

User: "now go for 13" (after Stage 12's `aether-stage12.zip`, with
`PROJECT_STATUS.md` reattached to restore context).

---

## AI Response Summary

- Re-read `PROJECT_STATUS.md` and unzipped the supplied
  `aether-stage12.zip` to confirm the actual state of the repo (rather
  than trusting the status doc's stage number alone, since the
  document itself notes it may be stale) — confirmed the zip matches
  "Stage 12 done" and that `sources_cache_service.py`'s docstring
  already names Stage 13's job precisely: "normalized title + keywords
  + source, meant to catch the same underlying story republished under
  a different URL/title variant."
- Reviewed `topic_discovery.py`'s `TopicCandidate` dataclass and
  `sources_cache_service.py`'s `compute_content_hash()` before writing
  anything, to match existing code style (module docstrings that state
  scope boundaries explicitly, small pure functions, SHA-256 over a
  pipe-joined basis string) and to make sure this stage's fingerprint
  is clearly differentiated from Stage 12's hash rather than
  duplicating it.
- `extract_keywords()`: tokenizes with a simple `[a-z0-9]+` regex
  (lowercased first), strips a short hand-picked stopword list, dedupes
  while preserving first-seen order, caps at `MAX_KEYWORDS=8`. Title
  tokens come before summary tokens so the title (the strongest
  "what is this story" signal) fills the keyword budget first.
- `normalize_source()`: strips everything but lowercase alphanumerics,
  so `"Hacker News (AI/ML)"` and `"hackernews-ai-ml"` normalize
  identically — protects the fingerprint from source-name formatting
  drift in `topic_sources.json` over time.
- `compute_fingerprint()`: SHA-256 over `normalized_source + "|" +
  "|".join(sorted(keywords))`. Sorting the keywords (unlike Stage 12's
  raw, order-sensitive `source_name|url` hash) is the key design
  choice — it's what makes a reworded or reordered headline for the
  same story, same source, collapse to the same fingerprint, which is
  exactly the gap Stage 12's docstring named as out of its scope.
- `fingerprint_candidate()` added as a thin convenience wrapper over
  a `TopicCandidate`, matching the pattern of Stage 12's functions
  operating directly on candidates.
- `backend/scripts/test_fingerprinting.py` — seven checks, no DB
  needed since fingerprinting doesn't touch persistence this stage:
  determinism; the core "reworded/reordered title, same story+source"
  collapse case; a genuinely different story not colliding; the same
  title from a different source not colliding; stopword stripping and
  `max_keywords` capping; source-name normalization; and
  `fingerprint_candidate()` agreeing with a direct
  `compute_fingerprint()` call.
- Ran the new script, then re-ran all nine prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12) — all passed, no regressions.

## Decisions Taken

- **Accepted:** keyword-set (sorted, deduped) fingerprint over a
  literal title hash — a literal hash of the title string would
  reintroduce exactly the problem this stage exists to solve (any
  rewording breaks it); sorted keywords is the simplest thing that
  actually catches reordered/reworded variants of the same story.
- **Accepted:** small hand-picked stopword list over an NLP library
  dependency — the PRD scope (`PROJECT_STATUS.md` §2) rules out
  heavier infrastructure like a vector DB, and headline-style titles
  don't need general-purpose NLP; a short stopword list is enough to
  strip the noise words that would otherwise pad every keyword set.
- **Accepted:** `MAX_KEYWORDS=8` cap — arbitrary but reasonable; keeps
  the fingerprint stable against a couple of extra trailing words in a
  longer title/summary variant of the same headline, while eight
  keywords is still specific enough that two different stories on the
  same broad topic (e.g. two different LLM releases) won't share every
  keyword and collide.
- **Accepted:** `_MIN_KEYWORD_LENGTH = 2` rather than the more typical
  3+ — short but meaningful tech terms ("ai", "ml", "llm") are common
  in this domain and would otherwise be dropped as noise.
- **Deferred:** wiring the fingerprint into `sources_cache` (e.g. an
  additional `fingerprint` column + a lookup alongside Stage 12's
  `content_hash` check) — the stage plan scopes Stage 13 as "a...
  fingerprint function, unit-testable," not the wiring; wiring
  near-duplicate rejection into the actual dedup/judgment path belongs
  with Stage 14 (Editorial Judgment) and/or Stage 15 (Memory Service),
  which are where "should this be published" decisions are made.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/fingerprint.py`
- `backend/scripts/test_fingerprinting.py`
- `docs/prompts/14_stage13.md`

## Files Modified
- `README.md` — project status bumped to Stage 13, repo tree updated,
  Stage 13 verification section added.
- `PROJECT_STATUS.md` — Stage 13 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 13 entry appended.

## Git Commit
```
feat(backend): add title+keywords+source fingerprinting for near-duplicate detection
```

## Stage Outcome
`python3 scripts/test_fingerprinting.py` (run from `backend/`, venv
active) passes all seven checks — pure unit tests, no DB required.
Re-ran all nine prior verification scripts (Stages 2, 5, 6, 7, 8, 9,
10, 11, 12) — all pass, no regressions. Nothing wired into
`sources_cache`, any model, or any route this stage — `fingerprint.py`
exists as a standalone, directly-callable module only.

## Next Stage
Stage 14 — Editorial Judgment: `editorial_judgment.py`, deciding
accept/reject for each newly-discovered (and now fingerprintable)
candidate, with rejections logged to `rejected_topics`.

---

# Stage 14 — Editorial Judgment

## Goal
`editorial_judgment.py` — accept/reject each newly-discovered
candidate against the persona's editorial voice, logging rejections
(with reason) to `rejected_topics`, per the 20-stage plan.

---

## Prompt(s)

User: "continue" (after approving Stage 13's `aether-stage13.zip`).

---

## AI Response Summary

- Re-read `RejectedTopic`'s Stage 2 model docstring before designing
  anything: it already states the table "prevents re-evaluating the
  same rejected topic repeatedly" — which directly implies a
  fingerprint-based short-circuit belongs in this stage, using Stage
  13's `fingerprint_candidate()`, before spending an LLM call.
- Reviewed `LLMProvider.judge()`'s docstring (Stage 6): explicitly
  says parsing the raw text into accept/reject "is the caller's job
  (Stage 14's editorial_judgment.py), not the provider's" — confirmed
  this stage owns prompt construction and response parsing, not the
  provider layer.
- Reviewed `persona.json` and `persona_service.build_voice_profile_prompt()`
  (Stage 5): the persona bible already encodes `editorial_values`
  (including "prefer signal over volume — reject more than it
  accepts" and "never publish the same underlying story twice, even
  reworded" — the latter is effectively Stage 13/14 working together),
  `topics_of_interest`/`topics_avoided`, and `sourcing_standards`.
  Decision: put none of that logic in `editorial_judgment.py` itself —
  the system prompt (the voice profile) carries all editorial
  criteria, keeping this module's own logic limited to prompt
  plumbing, response parsing, and persistence.
- `_build_judgment_prompt()`: states the candidate's concrete fields
  (title/source/url/category/summary) and a strict required response
  format (`ACCEPT: <reason>` / `REJECT: <reason>`), instructing the
  model to judge "based strictly on the editorial values... defined
  above" (i.e. in the system prompt) rather than repeating the
  criteria in the user prompt.
- `_parse_judgment()`: strict on the ACCEPT case (must start with the
  literal prefix), permissive on everything else — missing prefix,
  garbage text, empty string — all fall through to REJECT with a
  descriptive reason. This "fail closed" posture was the main design
  decision this stage, directly justified by the persona's own stated
  preference to reject more than it accepts.
- `judge_candidate()` wraps the fingerprint short-circuit, the LLM
  call (wrapped in try/except so a provider outage also fails closed
  rather than raising into whatever calls this — important since
  Stage 18's scheduler will eventually call this unattended), parsing,
  and — only on rejection — persisting a `RejectedTopic` row.
  Acceptance creates no row; there's nothing to persist for an
  accepted topic yet (that's Stage 16's post writer / Stage 17's
  publisher).
- `judge_candidates()` added as the batch entry point matching the
  list shape Stage 12's `discover_new_topics()` already returns, so
  Stage 18's scheduler chain can compose them directly:
  `discover_new_topics(db)` → `judge_candidates(db, agent_id, ...)`.
- `backend/scripts/test_editorial_judgment.py` — six checks against an
  in-memory DB with a `ScriptedProvider` (returns a pre-set sequence of
  responses, one per call) and a `RaisingProvider` (always throws), no
  network/API key needed: ACCEPT parsing + no rejection row; REJECT
  parsing + row with correct fingerprint/reason; the fingerprint
  short-circuit against a reworded/reordered-title near-duplicate of a
  rejected topic (asserts zero additional LLM calls AND no duplicate
  row); unparseable-response fail-closed; provider-exception
  fail-closed without propagating; and batch ordering via
  `judge_candidates()`.
- Ran the new script, then re-ran all ten prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13) — all passed, no
  regressions.

## Decisions Taken

- **Accepted:** fingerprint-based short-circuit against
  `rejected_topics` before any LLM call — directly implied by
  `RejectedTopic`'s own Stage 2 docstring and by `persona.json`'s
  "never publish the same underlying story twice, even reworded"
  value; also the practical payoff of Stage 13 existing at all.
- **Accepted:** fail-closed on every ambiguous/error path (unparseable
  text, empty response, provider exception) — matches the persona's
  explicit "reject more than it accepts" editorial value; an LLM
  outage should degrade to "publish nothing new," never to "publish
  everything."
- **Accepted:** strict `ACCEPT`/`REJECT` prefix format enforced via
  prompt instructions and lenient parsing on the caller side, rather
  than asking for structured JSON output — keeps the provider
  abstraction's `judge(prompt, system) -> str` shape (Stage 6) exactly
  as-is instead of requiring provider-specific JSON-mode support that
  not all providers may have.
- **Accepted:** all editorial criteria live in the system prompt
  (persona voice profile) rather than being duplicated as code-level
  rules in `editorial_judgment.py` — keeps the persona bible
  (`persona.json`) the single source of truth for what Aether does
  and doesn't cover, so future changes to editorial taste are a
  content edit, not a code change.
- **Deferred:** Breeth-based memory dedup against previously
  *published* topics — Stage 15's job; this stage only guards against
  re-judging something already in `rejected_topics`.
- **Deferred:** wiring `judge_candidates()` into any route or the
  scheduler — Stage 18, once the scheduler exists.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/editorial_judgment.py`
- `backend/scripts/test_editorial_judgment.py`
- `docs/prompts/15_stage14.md`

## Files Modified
- `README.md` — project status bumped to Stage 14, repo tree updated,
  Stage 14 verification section added.
- `PROJECT_STATUS.md` — Stage 14 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 14 entry appended.

## Git Commit
```
feat(backend): add editorial judgment with fail-closed LLM accept/reject and rejected_topics logging
```

## Stage Outcome
`python3 scripts/test_editorial_judgment.py` (run from `backend/`,
venv active) passes all six checks against an in-memory DB with a
scripted fake provider — no real API key needed. Re-ran all ten prior
verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13) — all
pass, no regressions. Nothing wired into any route or the (not-yet-
existing) scheduler this stage — `judge_candidate()`/
`judge_candidates()` exist as standalone, directly-callable functions
only, same posture as Stage 12's `discover_new_topics()`.

## Next Stage
Stage 15 — Memory Service (Breeth dedup): `memory_service.py`,
checking Breeth + the SQLite mirror for previously *published* topics
before a candidate reaches the post writer — the memory layer this
stage's fingerprint short-circuit doesn't cover (that only guards
against re-judging already-*rejected* topics).

---

# Stage 15 — Memory Service (Breeth Dedup)

## Goal
`memory_service.py` — query Breeth (plus the SQLite mirror) for
previously *published* topics before an editorially-accepted candidate
reaches Stage 16's post writer, per the 20-stage plan and Stage 14's
own docstring, which explicitly deferred this layer.

---

## Prompt(s)

User: "now go for stage 15" (after uploading `aether-stage14.zip` and
`PROJECT_STATUS.md`).

---

## AI Response Summary

- Unzipped and inspected the delivered `aether-stage14.zip` directly
  rather than trusting `PROJECT_STATUS.md` alone, to confirm the
  actual on-disk state (models, services, prior scripts) matched what
  the resume doc claimed before writing anything new.
- Re-read `RejectedTopic`'s Stage 2 docstring, `BreethMirrorFact`'s
  Stage 10 docstring, and `editorial_judgment.py`'s Stage 14 docstring
  together: Stage 10's docstring explicitly says "Stage 15's
  memory_service has a local fallback to query against if a live
  Breeth search call fails" — so the local-mirror-fallback design
  wasn't something to invent from scratch, it was already scoped two
  stages earlier. Stage 14's docstring confirmed the split: "(Not this
  stage) checking Breeth for *published* topics — that's Stage 15's
  memory service."
- Reviewed `Post`'s Stage 2 docstring/model: `fingerprint` was already
  a column ("used for dedup against future topic candidates") but
  unused by anything until now — decision: make the local
  `posts.fingerprint` lookup Layer 1, authoritative, and checked
  first, since it's free (no network) and exact.
- Reviewed `BreethClient.search()` (Stage 9): returns a raw dict with
  an `edges` key confirmed by the connection test, but no pinned-down
  edge shape beyond that. Decision: read edges defensively
  (`_edge_text()` checks several plausible key names rather than
  assuming one schema) instead of coupling tightly to an unconfirmed
  structure.
- Main design decision this stage: **fail open**, not fail closed, on
  Breeth specifically — the opposite posture from Stage 14's editorial
  judgment. Justification: Stage 14 fails closed because an ambiguous
  *editorial* call should default to *not publishing* (matches the
  persona's "reject more than it accepts" value). But a Breeth
  *infrastructure* outage has nothing to do with whether a topic is
  actually a duplicate — treating "Breeth is down" as "assume
  duplicate" would silently starve the feed for a reason unrelated to
  content quality, directly undermining the PRD's "feed must grow on
  its own" success criterion. `PROJECT_STATUS.md`'s own "Known
  Constraints" #2 (no real `BREETH_API_KEY` in this sandboxed
  environment) makes this not just a theoretical edge case but the
  expected default state during local dev.
- `_check_breeth_semantic()` returns `None` (not a `(bool, str)` tuple)
  specifically to signal "the call itself failed" as distinct from
  "the call succeeded and found nothing" — `check_memory()` uses that
  `None` sentinel to decide whether to fall back to the local mirror,
  keeping the two failure/success paths structurally distinct rather
  than overloading a boolean.
- `SEMANTIC_OVERLAP_THRESHOLD = 0.6` chosen as a deliberately generous
  fuzzy-match threshold — this layer's whole purpose is catching what
  Stage 13's exact fingerprint match structurally cannot (a reworded
  story from a different source), so it needs looser matching than a
  hash comparison, at the cost of being a soft/heuristic signal rather
  than a guarantee (documented plainly in the module docstring so a
  future stage doesn't mistake it for authoritative).
- `check_memory_batch()` added as the batch entry point, matching the
  shape `judge_candidates()` (Stage 14) already returns, so Stage 18's
  eventual scheduler chain reads as a straight pipeline:
  `discover_new_topics()` → `judge_candidates()` (accepted only) →
  `check_memory_batch()` (not-duplicate only) → post writer.
- `backend/scripts/test_memory_service.py` — seven checks against an
  in-memory DB with a `FakeBreethClient` (scripted response or forced
  exception, no network/API key needed): Layer 1 fingerprint match
  short-circuits with zero Breeth calls; a genuinely new candidate
  passes with no matching edges; a semantically similar edge (real
  keyword overlap between a candidate's title/summary and a fake
  edge's text) is flagged; a Breeth exception falls back to the local
  mirror and, with the mirror empty, fails open; a Breeth exception
  *plus* a matching synced mirror fact still correctly flags a
  duplicate through the fallback; an agent with no
  `breeth_agent_ref` yet skips the semantic check without calling
  Breeth; and `check_memory_batch()` preserves order across a batch.
- Ran the new script, then re-ran all eleven prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) — all passed,
  no regressions.

## Decisions Taken

- **Accepted:** two-layer design — authoritative local
  `posts.fingerprint` match first, soft Breeth semantic search second
  — rather than relying on Breeth alone, since local dev in this
  sandboxed environment has no real `BREETH_API_KEY` and the exact
  case (same agent, same story, reworded) is both the most common
  duplicate and the cheapest to catch without any network call.
- **Accepted:** fail **open** on Breeth failures specifically —
  directly justified by `PROJECT_STATUS.md`'s "Known Constraints" #2
  and the PRD's "feed must grow on its own" success criterion; an
  infrastructure outage must never look like "reject everything."
  This is a deliberate asymmetry with Stage 14's fail-closed editorial
  judgment, called out explicitly in the module docstring so it reads
  as an intentional design choice, not an inconsistency.
- **Accepted:** local `breeth_mirror_facts` fallback on Breeth
  failure, per `BreethMirrorFact`'s own Stage 10 docstring reserving
  this exact use — even though it will typically find nothing until
  Stage 17's publisher starts writing post-published facts into it.
- **Accepted:** defensive, key-agnostic parsing of Breeth's `edges`
  (`_edge_text()`) rather than assuming a specific schema, since
  nothing beyond the `edges` key itself has been confirmed live
  against the real API in this project so far.
- **Deferred:** writing post-published facts into `breeth_mirror_facts`
  itself — that's Stage 17's publisher; this stage only *reads* from
  that table as a fallback.
- **Deferred:** wiring `check_memory_batch()` into any route or the
  scheduler — Stage 18, once the scheduler exists.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/memory_service.py`
- `backend/scripts/test_memory_service.py`
- `docs/prompts/16_stage15.md`

## Files Modified
- `README.md` — project status bumped to Stage 15, repo tree updated,
  Stage 15 verification section added.
- `PROJECT_STATUS.md` — Stage 15 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 15 entry appended.

## Git Commit
```
feat(backend): add memory service with local fingerprint + Breeth semantic dedup against published topics, failing open on Breeth
```

## Stage Outcome
`python3 scripts/test_memory_service.py` (run from `backend/`, venv
active) passes all seven checks against an in-memory DB with a fake
Breeth client — no real API key needed. Re-ran all eleven prior
verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) —
all pass, no regressions. Nothing wired into any route or the
(not-yet-existing) scheduler this stage — `check_memory()`/
`check_memory_batch()` exist as standalone, directly-callable
functions only, same posture as Stages 12 and 14.

## Next Stage
Stage 16 — Post Writer: `post_writer.py` — generate post text +
rationale via `LLMFactory`, given a judged-accepted, memory-cleared
topic candidate (the output of Stage 14 + Stage 15 combined).

---

# Stage 16 — Post Writer

## Goal
`post_writer.py` — generate post text + rationale via `LLMFactory`,
given a judged-accepted (Stage 14), memory-cleared (Stage 15) topic
candidate, per the 20-stage plan.

---

## Prompt(s)

User: "now go for stage 16" (after approving Stage 15's
`aether-stage15.zip`).

---

## AI Response Summary

- Re-read `LLMProvider`'s Stage 6 docstring: `generate` is explicitly
  scoped for "open-ended text generation (post writing, persona voice
  profile generation)" — confirmed this stage should call `generate()`,
  not `judge()` (Stage 14's method) or `summarize()`.
- Reviewed `Post`'s Stage 2 model docstring again (already read in
  Stage 15): `rationale` is `nullable=False` and `sources` is
  "JSON-encoded list of source URLs/references this post was derived
  from" — both required inputs this stage must produce, alongside
  title/content, before Stage 17 can persist anything.
- Reviewed `persona.json`'s `writing_style_rules` and
  `sourcing_standards` (`minimum_sources: 1`): confirmed a single
  `candidate.url` as `sources` satisfies the persona's own stated
  minimum, so no source-aggregation logic was needed this stage —
  explicitly noted as out of scope rather than silently skipped.
- Design decision: `write_post()` takes the full `JudgmentResult`
  (Stage 14's dataclass), not just a bare `TopicCandidate`. Reasoning:
  the editorial acceptance reason (`judgment.reason`) is valuable
  context for the rationale the model writes — grounding "why was this
  worth covering" in the actual editorial decision rather than asking
  the model to reconstruct a rationale from nothing — and it lets
  `write_post()` assert immediately if ever called on a *rejected*
  result, catching a caller-side bug before spending an LLM call.
- Prompt format: settled on a strict `TITLE:` / `RATIONALE:` /
  `CONTENT:` three-marker response (mirroring Stage 14's `ACCEPT:` /
  `REJECT:` precedent for keeping provider-agnostic plain-text parsing
  instead of requiring JSON-mode support not every provider has), with
  `CONTENT:` last since it's the only open-ended multi-paragraph
  section and everything after that marker is unambiguously the body.
- Main design decision this stage: fail **loud** (raise
  `PostWriteError`) rather than fail closed (Stage 14's posture) or
  fail open (Stage 15's posture) on any generation/parsing problem.
  Reasoning: Stage 14's fail-closed REJECT is a genuinely safe default
  verdict; Stage 15's fail-open "assume novel" is safe because Layer 1
  (local fingerprint) is still authoritative regardless. Post writing
  has no equivalent safe default — there's no meaningful "placeholder
  post" that respects `persona.json`'s "prefer signal over volume"
  value, so a caller-visible exception (for Stage 17 to catch, log,
  and skip that cycle) is the only sound behavior. Documented this
  three-way asymmetry (closed / open / loud) explicitly in the module
  docstring so it reads as intentional across stages, not inconsistent.
- `_parse_post_response()` requires all three markers present *and* in
  the documented order *and* each section non-empty — chose strict
  positional parsing (`str.find` + slicing) over regex for
  readability, since the format is simple and linear.
- `backend/scripts/test_post_writer.py` — seven checks with a
  `ScriptedProvider` (pre-set response sequence) and a `RaisingProvider`
  (always throws), no network/API key needed: well-formed response
  parses correctly with `sources == [candidate.url]` and the
  fingerprint carried through from the judgment; a response missing a
  marker raises; sections out of order raise; an empty `CONTENT:`
  section raises; a provider exception raises `PostWriteError` without
  leaking the raw exception; a *rejected* `JudgmentResult` raises
  immediately with zero provider calls; and an empty response string
  raises.
- Ran the new script, then re-ran all twelve prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15) — all
  passed, no regressions.

## Decisions Taken

- **Accepted:** `write_post()` takes the full `JudgmentResult`, not a
  bare candidate — grounds the generated rationale in the actual
  editorial acceptance reason and lets misuse (calling this on a
  rejected result) be caught immediately without an LLM call.
- **Accepted:** fail **loud** (`PostWriteError`) on any
  generation/parsing failure — the only sound behavior given there's
  no safe placeholder post, explicitly contrasted with Stage 14's
  fail-closed and Stage 15's fail-open postures in the module
  docstring.
- **Accepted:** strict three-marker (`TITLE:`/`RATIONALE:`/`CONTENT:`)
  plain-text response format, parsed positionally — keeps the
  provider abstraction's `generate(prompt, system) -> str` shape
  (Stage 6) exactly as-is, same rationale as Stage 14's `ACCEPT:`/
  `REJECT:` precedent.
- **Accepted:** `sources` populated with only `[candidate.url]` —
  matches `persona.json`'s `minimum_sources: 1` and the fact that no
  earlier stage's `TopicCandidate` carries more than one URL; explicit
  scope note added rather than silently building partial
  source-aggregation logic.
- **Deferred:** persisting the `WrittenPost` to the `posts` table and
  pushing a summary fact to Breeth — Stage 17's publisher.
- **Deferred:** wiring `write_post()` into any route or the
  scheduler — Stage 18, once the scheduler exists.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/post_writer.py`
- `backend/scripts/test_post_writer.py`
- `docs/prompts/17_stage16.md`

## Files Modified
- `README.md` — project status bumped to Stage 16, repo tree updated,
  Stage 16 verification section added.
- `PROJECT_STATUS.md` — Stage 16 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 16 entry appended.

## Git Commit
```
feat(backend): add post writer generating title/content/rationale via LLMFactory, failing loud on malformed output
```

## Stage Outcome
`python3 scripts/test_post_writer.py` (run from `backend/`, venv
active) passes all seven checks with a scripted fake provider — no
real API key needed. Re-ran all twelve prior verification scripts
(Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15) — all pass, no
regressions. Nothing wired into any route or the (not-yet-existing)
scheduler this stage — `write_post()` exists as a standalone,
directly-callable function only, same posture as Stages 12, 14, and 15.

## Next Stage
Stage 17 — Publisher: `publisher.py` — writes a `WrittenPost` (this
stage's output) to the `posts` table, pushes a summary fact to Breeth
via `BreethClient.write_fact()` (Stage 9) so future memory checks
(Stage 15) can find it, and marks the cycle published.

---

# Stage 17 — Publisher

## Goal
`publisher.py` — writes a `WrittenPost` (Stage 16's output) to the
`posts` table, pushes a summary fact to Breeth, and marks the cycle
published, per the 20-stage plan.

---

## Prompt(s)

User: "stage 17 now" (after approving Stage 16's `aether-stage16.zip`).

---

## AI Response Summary

- Re-read `agent_service._create_breeth_namespace()` (Stage 10) before
  designing anything, since it's the only other place in the codebase
  that already writes to Breeth on behalf of an agent. Its docstring
  states the exact pattern this stage needed: a best-effort remote
  write wrapped in a broad try/except, with a `BreethMirrorFact` row
  written locally *regardless* of whether the remote write actually
  succeeded (`synced` records the true outcome). Decision: reuse this
  pattern verbatim rather than inventing a different one for
  publishing — consistency across the two places in the codebase that
  talk to Breeth matters more than any marginal improvement a
  from-scratch design might offer.
- Cross-checked against Stage 15's `memory_service.py` docstring
  again: its local-mirror fallback path explicitly depends on
  `breeth_mirror_facts` actually containing rows to scan, and notes
  it "will typically find nothing until Stage 17's publisher starts
  writing post-published facts into it." This stage is exactly that —
  confirms the mirror-write isn't optional polish, it's required for
  Stage 15's own documented fallback to ever have data.
- Decision: the mirrored/pushed fact's `object` field is the post's
  own title, not a generic placeholder like `"a topic"`. Directly
  driven by re-reading Stage 15's `_edge_text()` and
  `_check_local_mirror_fallback()`: both extract keywords from
  whatever text is in the `object` field and compare against a future
  candidate's title/summary keywords — a generic object string would
  make Stage 15's whole semantic-dedup layer silently useless once
  wired together in Stage 18.
- Decision: treat the local `Post` write and the remote Breeth write
  asymmetrically on purpose, and say so explicitly in the docstring —
  the `Post` row is a plain required DB write (no fail-open/fail-closed
  framing needed, same as Stage 2's models or Stage 14's
  `rejected_topics`), while only the Breeth call gets the
  best-effort/mirror treatment. This avoids over-generalizing Stage
  15's "fail open on Breeth" framing to a context (a local DB insert)
  where it doesn't actually apply.
- Decision: skip the remote Breeth call outright (not just catch a
  failure from it) when `agent.breeth_agent_ref` is `None` — there's
  no `group_id` to write into, so attempting the call would only ever
  raise; short-circuiting avoids a guaranteed-failing network call and
  logs a clearer reason than a generic exception message would. The
  local mirror row still gets written in this case too (with
  `group_id="unassigned"`), keeping the "always mirror locally"
  invariant intact even in this edge case.
- `backend/scripts/test_publisher.py` — six checks against an
  in-memory DB with a `FakeBreethClient` (succeeds or raises, no
  network/API key needed): a persisted `Post` has all the right
  fields and a generated id; a successful Breeth write yields a
  `synced=True` mirror fact with the post's title as `object`; a
  Breeth exception still persists the `Post` and yields a
  `synced=False` mirror fact rather than blocking publishing; an
  agent with no `breeth_agent_ref` skips the remote call (asserted via
  a call counter) but still persists the post and mirrors locally with
  `group_id="unassigned"`; two distinct posts for the same agent
  create two independent rows with no accidental dedup at this layer;
  and a persisted fingerprint round-trips correctly via a direct query
  (kept dependency-free from `memory_service` itself, to keep this
  script's fixtures self-contained per-stage as prior scripts do).
- Ran the new script, then re-ran all thirteen prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16) — all
  passed, no regressions.

## Decisions Taken

- **Accepted:** reuse Stage 10's exact best-effort-remote +
  always-local-mirror pattern for the Breeth "published" fact, rather
  than designing a new approach — consistency with the only other
  Breeth-writing code path in the project, and Stage 15's fallback
  path already assumes this shape exists.
- **Accepted:** mirrored fact's `object` is the post's actual title —
  required for Stage 15's keyword-overlap matching to have anything
  meaningful to compare against once the pipeline is fully wired
  (Stage 18).
- **Accepted:** skip the remote Breeth call (not attempt-then-catch)
  when the agent has no namespace yet, while still writing the local
  mirror row — avoids a guaranteed-failing call and keeps the
  "always mirror" invariant intact regardless of *why* the remote
  write didn't happen.
- **Accepted:** no special fail-open/fail-closed framing for the
  `Post` row write itself — it's a plain required DB write like any
  other model in this codebase; only the Breeth call gets the
  best-effort treatment.
- **Deferred:** anything about *deciding* what to publish or *whether*
  a candidate should reach this stage — entirely Stages 14–16's job;
  this stage assumes it's handed an already-accepted, memory-cleared,
  successfully-written `WrittenPost`.
- **Deferred:** wiring `publish_post()` into any route or the
  scheduler — Stage 18, once the scheduler exists. That's also where
  the full pipeline (discover → judge → memory → write → publish)
  gets chained together and exercised end-to-end for the first time.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/publisher.py`
- `backend/scripts/test_publisher.py`
- `docs/prompts/18_stage17.md`

## Files Modified
- `README.md` — project status bumped to Stage 17, repo tree updated,
  Stage 17 verification section added.
- `PROJECT_STATUS.md` — Stage 17 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 17 entry appended.

## Git Commit
```
feat(backend): add publisher persisting posts and pushing best-effort published facts to Breeth
```

## Stage Outcome
`python3 scripts/test_publisher.py` (run from `backend/`, venv active)
passes all six checks against an in-memory DB with a fake Breeth
client — no real API key needed. Re-ran all thirteen prior
verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
16) — all pass, no regressions. Nothing wired into any route or the
(not-yet-existing) scheduler this stage — `publish_post()` exists as a
standalone, directly-callable function only, same posture as every
service stage since Stage 12.

## Next Stage
Stage 18 — Scheduler Wiring: chain Stages 11/12 → 14 → 15 → 16 → 17
(`discover_new_topics()` → `judge_candidates()` (accepted only) →
`check_memory_batch()` (not-duplicate only) → `write_post()` →
`publish_post()`) behind APScheduler, driven by
`PUBLISH_INTERVAL_MINUTES` from the environment — the first point
where the full autonomous pipeline actually runs end-to-end.

---

# Stage 18 — Scheduler Wiring

## Goal
`scheduler.py` — chain Stages 11/12 → 14 → 15 → 16 → 17
(`discover_new_topics()` → `judge_candidates()` (accepted only) →
`check_memory_batch()` (not-duplicate only) → `write_post()` →
`publish_post()`) behind APScheduler, driven by
`PUBLISH_INTERVAL_MINUTES` from the environment, started from
`POST /api/agent/init` — the first point the full autonomous pipeline
runs end-to-end with zero further human prompting, per the PRD's core
success criterion.

---

## Prompt(s)

User: "create stage 18" (uploaded `aether-stage17.zip` and
`PROJECT_STATUS.md` as the resume context — the uploaded status doc's
own text was stale relative to the actual zip contents, which were
already at Stage 17; proceeded from the zip's real state, not the
doc's stated "Stage 3 NEXT UP" line).

---

## AI Response Summary

- Extracted `aether-stage17.zip` and read every service file involved
  in the chain (`topic_discovery.py`, `sources_cache_service.py`,
  `editorial_judgment.py`, `memory_service.py`, `post_writer.py`,
  `publisher.py`) plus `agent_service.py`, `routes/agent.py`,
  `config.py`, and the `Agent` model before writing anything — every
  one of those six services' own docstrings already stated exactly
  where it plugs into this stage's chain, so the wiring order was a
  transcription task, not a design decision.
- Confirmed `apscheduler==3.10.4` was already in `requirements.txt`
  (added in Stage 1, unused until now) and `publish_interval_minutes`
  already existed in `config.py` with a comment marking it "wired in
  Stage 18" — nothing to add to either file.
- Decision: `run_publish_cycle(db, agent)` is a plain function with no
  APScheduler knowledge, kept directly unit-testable the same way
  every prior service has been — mirrors the README's own Stage 17
  manual-pipeline snippet almost exactly, which effectively already
  was this function's design, just not yet made real.
- Decision: wrap each stage of the chain (discovery, judgment, memory
  check) in its own try/except that logs and returns `0` rather than
  letting an exception propagate out of `run_publish_cycle()`. None of
  Stages 12/14/15's docstrings promise they can't raise on a genuinely
  unexpected failure (only their *documented* failure modes — Stage
  14's fail-closed REJECT, Stage 15's fail-open Breeth fallback — are
  guaranteed not to raise), and an autonomous scheduler that dies on
  the first unexpected exception defeats the PRD's "zero further human
  prompting" requirement outright.
- Decision: Stage 16's `PostWriteError` (its own documented fail-loud
  mode) is caught *per candidate*, not per cycle — looping over
  `survivors` with an individual try/except around
  `write_post()`/`publish_post()` so one bad generation doesn't
  discard other candidates that would have written and published
  cleanly in the same cycle.
- Decision: `_tick()` opens its own `SessionLocal()` session rather
  than trying to reuse anything from `get_db()` — a
  `BackgroundScheduler` job runs on its own thread, entirely outside
  any FastAPI request lifecycle, so there is no request-scoped session
  to borrow. Modeled the close-in-`finally` shape directly on
  `get_db()`'s own pattern for consistency.
- Decision: `start_scheduler()` is idempotent via a module-level
  `_scheduler` guard, directly because `get_or_create_agent()` (Stage
  4/10) is itself idempotent and returns the same row on a repeat
  `/init` call — the scheduler needed the same guarantee, or a second
  `/init` call would start a second `BackgroundScheduler` polling
  twice as often against the same agent with no way to detect or
  correct it later.
- Decision: schedule the first tick to fire immediately
  (`next_run_time=datetime.now()`) rather than waiting one full
  `PUBLISH_INTERVAL_MINUTES` before the first cycle. Read PRD Section
  9 ("posts appear automatically over time, feed grows with no human
  prompts") as implying the evaluator should see growth starting
  promptly after the single `/init` call, not after an arbitrary wait
  tied to whatever interval is configured; every tick after the first
  still respects the configured interval exactly.
- Decision: wire the scheduler start into `routes/agent.py` (not
  `agent_service.py`) — `agent_service.py`'s own Stage 10 docstring
  scopes it to "creates the agent row for POST /api/agent/init" and
  explicitly notes "Scheduler start (Stage 18) is still not wired in
  here," treating it as a separate concern the route layer owns.
  Flips `agent.status` to `"active"` in the route immediately after
  confirming the scheduler is running, only committing when the value
  actually changes (repeat calls are then a true no-op DB-wise).
- Added an `on_event("shutdown")` hook in `main.py` calling
  `stop_scheduler()` — not explicitly required by the stage plan, but
  without it a local-dev auto-reload would leave an orphaned
  background thread running after every restart; cheap enough to add
  now rather than as a fix-up later.
- Verified end-to-end via FastAPI's `TestClient` (not just the mocked
  unit script): a fresh `POST /api/agent/init` returns
  `status: "active"`, a repeat call returns the identical `agentId`,
  and the scheduler's immediate first tick genuinely executed the real
  pipeline against the real (network-restricted-in-this-sandbox) topic
  sources — each source failed individually with a `403` exactly as
  Stage 11's per-source try/except already anticipated, without
  crashing the process or leaving an unhandled exception in the logs.
  This is real confirmation the wiring works, not just that the mocks
  return the right shapes.
- `backend/scripts/test_scheduler.py` — six checks against an
  in-memory DB with every chained function monkeypatched via
  `unittest.mock.patch.object` on the `scheduler` module's own
  imported names (clean because `scheduler.py` imports each function
  by name into its own namespace, so patching there doesn't touch the
  real implementations Stages 12–17's own scripts already cover): no
  candidates short-circuits before judgment (asserted via
  `assert_not_called()`); no accepted candidates short-circuits before
  the memory check; all-duplicates short-circuits before the post
  writer; a mixed batch (one duplicate, one `PostWriteError`, one
  clean success) returns `1` and calls `publish_post()` exactly once
  with the correct `WrittenPost`; discovery raising an unexpected
  exception is caught and returns `0` instead of propagating;
  `start_scheduler()`/`stop_scheduler()` idempotency, using the real
  (not mocked) APScheduler classes to confirm object identity across
  calls.
- Ran the new script, then re-ran all fourteen prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17) —
  all passed, no regressions.

## Decisions Taken

- **Accepted:** `run_publish_cycle()` stays a plain, APScheduler-free
  function for direct testability — all scheduling machinery isolated
  to `start_scheduler()`/`_tick()`.
- **Accepted:** every stage of the chain individually try/excepted,
  logging and returning `0` rather than raising — required so an
  unexpected failure anywhere in the pipeline skips one cycle instead
  of silently ending the autonomous loop.
- **Accepted:** `PostWriteError` caught per-candidate inside the
  survivors loop, not per-cycle — preserves other candidates in the
  same batch that would have published cleanly.
- **Accepted:** `start_scheduler()` idempotent via a module-level
  guard, matching `get_or_create_agent()`'s existing idempotency
  contract exactly.
- **Accepted:** immediate first tick
  (`next_run_time=datetime.now()`), then the configured interval
  after — prioritizes the evaluator seeing prompt feed growth over a
  literal "always wait one interval first" reading of the plan.
- **Accepted:** scheduler start + status flip live in the route layer,
  not `agent_service.py` — consistent with Stage 10's own explicit
  scoping note.
- **Accepted:** an `on_event("shutdown")` hook stopping the scheduler
  — small addition beyond the stage's literal scope, justified by
  avoiding orphaned background threads across local-dev reloads.
- **Deferred:** anything about the feed's actual JSON response shape
  or the Next.js Feed page rendering real data — Stage 19.
- **Deferred:** any change to `PUBLISH_INTERVAL_MINUTES`'s default or
  to the topic source list — out of this stage's scope; the `403`s
  seen during E2E verification are a sandbox network restriction, not
  a defect in Stage 11's fetcher, which already degrades per-source
  exactly as designed.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/scheduler.py`
- `backend/scripts/test_scheduler.py`
- `docs/prompts/19_stage18.md`

## Files Modified
- `backend/app/routes/agent.py` — starts the scheduler and flips
  `status` to `"active"` on `/init`.
- `backend/app/main.py` — added `on_event("shutdown")` calling
  `stop_scheduler()`.
- `README.md` — project status bumped to Stage 18, repo tree updated,
  Stage 17's manual-pipeline snippet replaced with the Stage 18
  verification section (mocked unit script + live `/init` walkthrough).
- `PROJECT_STATUS.md` — Stage 18 entry added, 20-stage plan table
  corrected (a stale duplicate tail of rows 12–20 lacking DONE/NEXT UP
  markers was cleaned up while updating it), resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 18 entry appended.

## Git Commit
```
feat(backend): wire discover->judge->memory->write->publish into an APScheduler-driven autonomous publish cycle, started from /init
```

## Stage Outcome
`python -m scripts.test_scheduler` (run from `backend/`, venv active)
passes all six checks against an in-memory DB with every pipeline
stage monkeypatched — no network or API keys needed. Re-ran all
fourteen prior verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11,
12, 13, 14, 15, 16, 17) — all pass, no regressions. Also verified live
via FastAPI's `TestClient`: `POST /api/agent/init` now returns
`status: "active"`, a repeat call is idempotent (same `agentId`, no
second scheduler), and the scheduler's immediate first tick genuinely
ran the real pipeline end-to-end against real topic sources (each
failing individually with a `403` under this sandbox's network
restrictions, handled exactly as Stage 11 already designed, without
crashing the process).

## Next Stage
Stage 19 — Feed Endpoint + Feed Page: `GET /api/agent/feed` (exact PRD
JSON shape) + the Next.js Feed page going live against it — the first
point the frontend actually displays real, autonomously published
posts.

---

# Stage 19 — Feed Endpoint + Feed Page

## Goal
`GET /api/agent/feed` (exact PRD JSON shape) + the Next.js Feed page
going live against it — the first point the frontend actually displays
real, autonomously published posts, and the Landing page's Initialize
button actually calls the real backend instead of sitting disabled.

---

## Prompt(s)

User: "nwo go for stage 19" (uploaded `aether-stage18.zip` and
`PROJECT_STATUS.md` as resume context).

---

## AI Response Summary

- Extracted `aether-stage18.zip` and read `routes/agent.py`,
  `schemas/agent.py`, `models/post.py`, `models/agent.py`,
  `publisher.py`, `database.py`, `main.py`, `config.py`, and every
  frontend file (`page.tsx`, `feed/page.tsx`, `layout.tsx`,
  `globals.css`, `package.json`, `next.config.js`) before writing
  anything — `Post.sources` is a JSON-encoded string column (Stage 2),
  which was the one detail that shaped the route (see below); the
  frontend's dark-panel/card CSS system was already fully defined in
  `globals.css`, so the wired pages reused it rather than introducing
  new styling.
- Decision: `GET /api/agent/feed` returns an empty feed (all identity
  fields `null`, `posts: []`) with a 200 when no agent exists yet,
  rather than a 404. The PRD doesn't say the evaluator waits for
  `/init` before its first `/feed` poll, and an empty feed is already
  a valid rendered state (Stage 3's own empty-state UI). The route
  never creates an agent as a side effect — that stays `/init`'s job
  alone, per §5's "only 2 public endpoints" split of responsibilities.
- Decision: added `FeedPost`/`FeedResponse` schemas rather than
  reusing/extending `AgentInitResponse` — the feed's shape (a list of
  posts with `rationale`/`sources`) is structurally different from the
  init response and conflating them would make both harder to read.
- Decision: `json.loads()` on `Post.sources` happens per-post inside a
  narrow try/except, falling back to `[]` for that post only on a
  parse failure — chosen so one bad row can't 500 the entire feed for
  every other post.
- Decision: Feed page polls (`setInterval`, 30s, cleaned up on
  unmount) instead of fetching once — the PRD's core success criterion
  is specifically that the feed grows *without* further human
  prompting, so a fetch-once page would never visibly demonstrate that
  without a manual browser refresh.
- Decision: added `frontend/app/lib/api.ts` as a thin typed wrapper
  around two `fetch()` calls rather than pulling in a client library
  (SWR/React Query, an API SDK) — the PRD scopes the frontend to
  exactly two pages hitting exactly two endpoints; a dependency for
  that is scope creep the PRD's §2 out-of-scope list would flag on the
  backend side too.
- Decision: Landing page's Initialize button now calls `initAgent()`
  on click, shows a loading state, and once `status === "active"`
  displays the LLM-generated `personaDescription` (falling back to the
  static tagline Stage 3 already had if the LLM call was skipped —
  matches `agent_service.py`'s own documented graceful-degradation
  behavior when no real `GEMINI_API_KEY` is configured) plus a link to
  the Feed page.
- Added `frontend/.env.local.example` for `NEXT_PUBLIC_API_URL`
  (defaults to `http://localhost:8000` in code if unset) — needed once
  the frontend is deployed anywhere other than alongside a
  localhost:8000 backend.
- `backend/scripts/test_feed_endpoint.py` — four checks via FastAPI's
  `TestClient` against an in-memory SQLite DB (`StaticPool`, needed
  because a bare `:memory:` engine hands `TestClient`'s worker thread a
  fresh empty DB per connection otherwise): empty feed before any
  agent exists; agent-with-zero-posts returns identity fields with
  `posts: []`; posts return newest-first with `sources` correctly
  decoded back into a list; a malformed `sources` string falls back to
  `[]` without breaking the other two posts in the same response.
- Verified live: `uvicorn` + `curl` — `GET /feed` before `/init`
  returns the empty shape, `POST /init` returns the usual
  `AgentInitResponse`, `GET /feed` immediately after returns the
  agent's identity with `posts: []` (no posts yet since no live
  `GEMINI_API_KEY`/`BREETH_API_KEY` in this sandbox, matching every
  prior stage's documented graceful-degradation behavior). Also ran
  `npm run build` on the frontend — compiles clean, both routes
  prerender as static shells (client components hydrate and fetch on
  mount, which is expected and correct for data that must always be
  fresh).

## Decisions Taken

- **Accepted:** `/feed` is side-effect-free and returns an empty,
  200-status shape before any agent exists rather than a 404.
- **Accepted:** new `FeedPost`/`FeedResponse` schemas instead of
  extending `AgentInitResponse`.
- **Accepted:** per-post `json.loads()` with a narrow try/except and
  `[]` fallback, so one malformed row can't break the whole feed.
- **Accepted:** Feed page polls every 30s rather than fetching once.
- **Accepted:** a hand-rolled `fetch()` wrapper (`lib/api.ts`) instead
  of a data-fetching library — matches the PRD's minimal-frontend
  scope.
- **Accepted:** Landing page shows the real LLM-generated persona
  description once available, falling back to the static tagline
  otherwise.
- **Deferred:** nothing meaningful remains for the 2-page, 2-endpoint
  PRD scope beyond Stage 20's deploy/release-candidate checklist.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/scripts/test_feed_endpoint.py`
- `frontend/app/lib/api.ts`
- `frontend/.env.local.example`
- `docs/prompts/20_stage19.md`

## Files Modified
- `backend/app/schemas/agent.py` — added `FeedPost`, `FeedResponse`.
- `backend/app/routes/agent.py` — added `GET /api/agent/feed`.
- `frontend/app/page.tsx` — Initialize button now calls
  `POST /api/agent/init`, renders live agent/persona state.
- `frontend/app/feed/page.tsx` — now a client component polling
  `GET /api/agent/feed`, rendering created time/title/content/
  rationale/sources per post.
- `README.md` — project status bumped to Stage 19, repo tree updated,
  new "Verifying the Feed Endpoint" + "Running the Frontend Against
  the Live Backend" sections.
- `PROJECT_STATUS.md` — Stage 19 entry added, 20-stage plan table
  updated, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 19 entry appended.

## Git Commit
```
feat: add GET /api/agent/feed and wire both frontend pages to the live backend (init + polling feed)
```

## Stage Outcome
`python -m scripts.test_feed_endpoint` (run from `backend/`) passes
all four checks against an in-memory DB — no network or API keys
needed. Verified live via `uvicorn` + `curl`: the feed correctly
transitions from the empty pre-init shape to the populated
agent-identity shape across a real `POST /api/agent/init` call.
`npm run build` in `frontend/` compiles clean with no type errors,
both routes prerendering successfully. Re-running prior backend
verification scripts (Stages 2, 5–18) was not repeated this stage
since none of their underlying modules were touched — only
`schemas/agent.py` and `routes/agent.py` changed, both purely
additive (a new endpoint + two new schema classes; `POST /init`'s
existing behavior and response shape are untouched).

## Next Stage
Stage 20 — Release Candidate: Railway deploy, API contract check, a
full end-to-end autonomous run (real `GEMINI_API_KEY`/
`BREETH_API_KEY`, watching the feed actually grow with zero further
human prompting), docs sync, final `README.md`, final cumulative ZIP.

---

# Stage 20 — Release Candidate

## Goal
Railway deploy configs, API contract check, a full end-to-end
autonomous run, docs sync, final `README.md`, final cumulative ZIP —
the closing stage of the 20-stage plan.

---

## Prompt(s)

User: "now go for stage 20" (continuing directly from Stage 19 in the
same conversation; `aether-stage19.zip` already delivered and
approved).

---

## AI Response Summary

- Re-confirmed the working tree from Stage 19 was intact (no context
  reset this time) before making any changes.
- Recognized Stage 20 needs no new *application* code — Stage 19
  already closed out the PRD's full functional scope (both endpoints
  live, both pages wired, the autonomous pipeline running). What
  remains for a genuine release candidate is deployability,
  documentation, and verification, not features.
- Added `backend/railway.json` / `frontend/railway.json` — Nixpacks
  build/start config for **two separate Railway services** from one
  repo, each with its own `Root Directory`. Decision: two services,
  not one combined deployment, specifically because the backend runs
  a long-lived `BackgroundScheduler` (Stage 18) — a frontend-only
  redeploy shouldn't bounce that process, and Railway's per-service
  restart/scale model only gives you that if they're separate
  services to begin with.
- Wrote `docs/DEPLOYMENT.md` as an exact, copy-pasteable walkthrough
  (git push → create backend service → create frontend service → set
  env vars → verify). Explicitly re-flagged, rather than silently
  omitted, that Claude's sandbox cannot `git push` to a real remote or
  create a real Railway project (`PROJECT_STATUS.md` §12's Known
  Constraint #1, stated at project start) — the deploy config and
  guide are as far as this stage can go without the repo owner's own
  GitHub/Railway accounts.
- Flagged, in the same doc, that `DATABASE_URL=sqlite:///./aether.db`
  writes to Railway's ephemeral local filesystem and is **not**
  persisted across redeploys — a real operational consequence of the
  locked SQLite choice (`PROJECT_STATUS.md` §3) that a release
  candidate's deployment doc shouldn't leave unstated. Noted the fix
  (swap `DATABASE_URL` to a Railway Postgres plugin) is a one-variable
  change given `core/config.py`'s existing env-driven design, without
  actually making that change — switching databases isn't in scope
  unless asked.
- Wrote `docs/API_CONTRACT.md`, freezing the exact JSON shape of both
  public endpoints (already implemented in Stages 4–19; this stage
  documents, not designs, the shape).
- Added `backend/scripts/test_api_contract.py` — deliberately separate
  from Stage 19's `test_feed_endpoint.py`: that script tests route
  *logic* (empty state, ordering, malformed-sources fallback), this
  one asserts the *documented contract* (exact key sets, types,
  nullability) holds against the real app, so a future response-model
  change can't silently drift from what `API_CONTRACT.md` promises
  without a test catching it.
- Ran the new script (4/4 pass), then re-ran all 17 prior verification
  scripts (Stages 2, 5–19) back-to-back — zero regressions, confirming
  Stage 19/20's changes were purely additive (one new route, two new
  schema classes, two new scripts; nothing existing was modified in a
  way that could have broken anything).
- Did a genuine live E2E run against a real `uvicorn` process (not
  just `TestClient`) in this sandbox, in one shell invocation so the
  background process survived long enough to hit: `GET /feed` empty
  before init → `POST /init` (`status: "active"`) → repeat `POST
  /init` (identical `agentId`, confirms idempotency) → `GET /feed`
  after init. Server logs confirmed the scheduler's immediate first
  tick ran the complete pipeline for real: all three configured topic
  sources individually failed with `403` under this sandbox's network
  restrictions, handled exactly as Stage 11's per-source try/except
  already designed for, with no crash and no unhandled exception.
- Also re-ran `npm run build` on the frontend — clean, no regressions.
- Synced all docs to reflect completion: `README.md`'s Project Status
  now reads "Stage 20 of 20 — Release Candidate, all 20 stages
  complete," with a new Stage 20 verification section and a closing
  "Release Notes" section stating plainly what's done vs. what still
  needs the repo owner (real `git push` + Railway project creation; a
  live run with real API keys) rather than implying the sandbox
  completed those too.

## Decisions Taken

- **Accepted:** two separate Railway services (backend, frontend) from
  one repo via per-service `Root Directory`, not a single combined
  deployment — required so a frontend redeploy can't bounce the
  backend's long-lived scheduler.
- **Accepted:** `docs/DEPLOYMENT.md` explicitly re-states the sandbox
  can't push/deploy for real, rather than presenting the Railway
  configs as if deployment were already done.
- **Accepted:** the SQLite-on-Railway ephemeral-storage caveat is
  documented, not silently worked around by switching databases.
- **Accepted:** a dedicated `test_api_contract.py`, distinct in intent
  from `test_feed_endpoint.py`, to guard the frozen contract
  specifically.
- **Accepted:** no new application code this stage — Stage 19 already
  delivered full PRD functional scope; adding features here would be
  scope creep the PRD itself doesn't call for.
- **Deferred:** actually creating the Railway project, pushing to
  GitHub, and running a live end-to-end cycle with real
  `GEMINI_API_KEY`/`BREETH_API_KEY` — belongs to the repo owner, not
  achievable inside this sandbox regardless of stage.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/railway.json`
- `frontend/railway.json`
- `docs/DEPLOYMENT.md`
- `docs/API_CONTRACT.md`
- `backend/scripts/test_api_contract.py`
- `docs/prompts/21_stage20.md`

## Files Modified
- `README.md` — Project Status bumped to "Stage 20 of 20 — Release
  Candidate," repo tree updated (railway.json entries, docs/
  additions), new Stage 20 verification section, closing Release
  Notes section.
- `PROJECT_STATUS.md` — Stage 20 entry added, plan table's Stage 20
  row marked DONE, resume pointer updated (project complete; any
  future work is maintenance, not a numbered stage).
- `docs/AI_USAGE_LOG.md` — Stage 20 entry appended.

## Git Commit
```
chore: release candidate — Railway deploy configs, API contract doc + check, full regression pass, deployment guide
```

## Stage Outcome
`python -m scripts.test_api_contract` passes all 4 checks against an
in-memory DB. Full regression: all 17 prior verification scripts
(Stages 2, 5–19) re-run back-to-back, zero failures. Live E2E against
a real `uvicorn` process confirms the exact empty→active→populated
transition and idempotent `/init`, with the scheduler's real first
tick executing the full pipeline cleanly (each topic source
individually 403'd under this sandbox's network restrictions, handled
exactly as designed). `npm run build` on the frontend compiles clean.
All 20 stages of the plan are now complete.

## Next Stage
None planned — the 20-stage plan is complete. Any further work (a real
Railway deployment by the repo owner, live keys, or a genuinely new
feature request) would be its own separate task, not a continuation of
this numbered plan.

---

## Addendum — Evaluator Contract Audit Fixes

A follow-up review of the delivered Stage 20 ZIP against the exact
hackathon evaluator contract, done in the same conversation as a
closing hardening pass rather than as a new numbered stage.

### Prompt(s)

User uploaded `aether-stage20.zip` and pasted a Hinglish audit
checklist reviewing the delivered build. MUST FIX items: exact
`/api/agent/feed` JSON shape (`text` not `content`, no wrapping `agent`
object, ISO 8601 `createdAt`, empty feed as `{"posts":[]}`); exact
`/api/agent/init` response (`{"agentId":"..."}` only); OpenRouter as
primary LLM provider with Gemini as an optional, non-mandatory
fallback; confirm the Breeth-primary/SQLite-fallback memory design;
confirm the autonomous scheduler chain and that no `/generate`/`/run`
endpoint exists; confirm `PUBLISH_INTERVAL_MINUTES` is configurable;
confirm live topic sources with preserved source URLs; confirm
editorial rejections are actually stored with a reason; confirm the
persona is frozen. Strongly recommended: don't fake-compress the real
20-stage history, keep `AI_USAGE_LOG.md` honest, add
`docs/PROJECT_STATE.md`, clean `.env.example` to only variables
actually used, and verify secrets never reach GitHub.

### AI Response Summary

Checked each item against the real Stage 20 code rather than assuming
anything was still broken:

- Confirmed the memory fallback design, scheduler chain (no manual
  trigger route), rejected-topic storage, live topic sources, and
  frozen persona were all already correct from earlier stages — no
  code changes needed for these, verification only.
- Found `/init` and `/feed` genuinely did not match the evaluator's
  exact contract (extra fields on `/init`; `content`/`title` instead
  of `text`, and a wrapping identity object, on `/feed`). Rewrote
  `schemas/agent.py` and `routes/agent.py` to the exact shape, added
  an optional `{"persona": {"name","domain"}}` request body to
  `/init`, and forced `createdAt` to ISO 8601 UTC with a `Z` suffix via
  a Pydantic `field_serializer`. Updated the frontend
  (`lib/api.ts`/`page.tsx`/`feed/page.tsx`) to match.
- Flipped the default `LLM_PROVIDER` from `gemini` to `openrouter` in
  `core/config.py`; Gemini provider code and env vars stay in place as
  an explicit, non-mandatory fallback.
- Added `docs/PROJECT_STATE.md` (new file) and `backend/.gitignore`
  (new file — the backend had none, only the frontend did).
- Cleaned `backend/.env.example` down to exactly the variables
  `core/config.py` reads.
- Updated `scripts/test_api_contract.py` and
  `scripts/test_feed_endpoint.py` to assert the new exact shapes, and
  a small default-provider assertion in `scripts/test_llm_factory.py`.
  Re-ran all 17 backend verification scripts plus a real
  `npm run build` on the frontend — zero regressions.
- Updated `docs/API_CONTRACT.md`, `PROJECT_STATUS.md`'s tech-stack
  line, and the minimum necessary lines of `README.md`/
  `docs/DEPLOYMENT.md` (env var lists, example output) rather than
  rewriting either wholesale.

### Files Changed
- `backend/app/schemas/agent.py`
- `backend/app/routes/agent.py`
- `backend/app/services/agent_service.py`
- `backend/app/core/config.py`
- `backend/.env.example`
- `backend/.gitignore` (new)
- `backend/scripts/test_api_contract.py`
- `backend/scripts/test_feed_endpoint.py`
- `backend/scripts/test_llm_factory.py`
- `frontend/app/lib/api.ts`
- `frontend/app/page.tsx`
- `frontend/app/feed/page.tsx`
- `docs/API_CONTRACT.md`
- `docs/DEPLOYMENT.md`
- `docs/PROJECT_STATE.md` (new)
- `PROJECT_STATUS.md`
- `README.md`

### Commit
```
fix: lock API to exact evaluator contract, OpenRouter as primary LLM, env cleanup, add PROJECT_STATE.md
```

---
