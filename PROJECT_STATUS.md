# AETHER — PROJECT HANDOFF / RESUME DOCUMENT

> **Use this file to resume work if the conversation/context resets.**
> Paste this whole document into a new chat and say:
> **"Continue from Stage 12. Last delivered ZIP: aether-stage11.zip"**
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
| 5 | Persona Bible + Prompt Builder | persona.json, persona_service.py builds voice profile (no LLM call yet) ✅ **DONE** |
| 6 | LLMProvider Interface | base_provider.py (generate/judge/summarize ABC) + Gemini provider ✅ **DONE** |
| 7 | LLMFactory + Second Provider | llm_factory.py + openrouter_provider.py, env-driven switch ✅ **DONE** |
| 8 | Wire LLM into Init | /init generates persona voice profile via LLMFactory, saves it ✅ **DONE** |
| 9 | Breeth Client (connection only) | breeth_client.py — connect, write/read test fact, standalone script ✅ **DONE** |
| 10 | Breeth Namespace on Init | /init creates Breeth namespace, stores breeth_agent_ref, SQLite mirror stub ✅ **DONE** |
| 11 | Topic Sources Config + Fetcher | topic_sources.json + topic_discovery.py, raw candidates, no caching yet ✅ **DONE** |
| 12 | Sources Cache | sources_cache wired in — dedup fetch, hash check ✅ **DONE** |
| 13 | Fingerprinting | Normalized title+keywords+source → fingerprint function, unit-testable ⬅ **NEXT UP** |
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

### ✅ Stage 7 — LLMFactory + Second Provider (DONE)
- `backend/app/services/llm/openrouter_provider.py` — `OpenRouterProvider`,
  calls OpenRouter's OpenAI-compatible `/chat/completions` endpoint via
  `httpx`, same structure as `GeminiProvider`; raises
  `OpenRouterConfigError` if `OPENROUTER_API_KEY` is missing
- `backend/app/services/llm/llm_factory.py` — `get_llm_provider()`,
  name-to-class registry keyed off `settings.llm_provider`
  (case-insensitive), raises `UnknownLLMProviderError` for anything
  unregistered
- `backend/app/core/config.py` / `.env.example` — added
  `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` (default
  `openai/gpt-4o-mini`)
- Rule from this stage on: nothing outside `app/services/llm/` imports
  a concrete provider class directly — callers use
  `get_llm_provider()`, which is what makes the provider swappable per
  the PRD
- `backend/scripts/test_llm_factory.py` — standalone verification
  script; re-ran Stage 6's `test_llm_provider.py`, no regressions
- Verified: `OpenRouterProvider` implements the full interface,
  missing-key path raises a clear error, factory resolves to
  `GeminiProvider` by default and `OpenRouterProvider` when asked,
  case-insensitive lookup works, unknown provider name raises loudly
- Commit: `feat(backend): add LLMFactory and OpenRouter provider for env-driven LLM switching`

### ✅ Stage 8 — Wire LLM into Init (DONE)
- `backend/app/services/agent_service.py` — on agent creation (not on
  idempotent re-fetch), builds the voice-profile prompt
  (`persona_service`) and sends it through `get_llm_provider().generate()`
  to produce a short persona description, stored on the row; wrapped
  in a broad try/except that logs a warning and returns `None` on any
  failure so `/init` still succeeds without a live LLM
- `backend/app/schemas/agent.py`, `backend/app/routes/agent.py` —
  `AgentInitResponse` gains `personaDescription`
- `backend/scripts/test_init_llm_wiring.py` — standalone verification
  against an in-memory DB and a fake `LLMProvider`; re-ran Stages 6/7
  scripts, no regressions
- Verified: new agent gets correct `persona_name` + fake provider's
  description, LLM called exactly once even across a repeat call,
  real graceful-fallback path (no key in this sandbox) still succeeds
  with `persona_description=None`
- Commit: `feat(backend): generate persona description via LLM on agent init`

### ✅ Stage 9 — Breeth Client (connection only) (DONE)
- Fetched current Breeth docs (docs.thebreeth.com) before coding, per
  Known Constraint #3: base URL `https://api.thebreeth.com`, all
  routes under `/v1`, Bearer-token auth, JSON error envelope
  `{"error": "<slug>", "message": "..."}`
- `backend/app/services/breeth_client.py` — `BreethClient` with
  `write_fact()` (`POST /v1/facts`) and `search()` (`POST /v1/search`,
  hybrid BM25 + vector + graph retrieval); raises `BreethConfigError`
  if `BREETH_API_KEY` is unset, `BreethAPIError` (with parsed
  `slug`/`message`) on any non-2xx response
- `backend/app/core/config.py` / `.env.example` — added
  `BREETH_BASE_URL` (default `https://api.thebreeth.com`)
- No namespace-per-agent logic and no wiring into `/init` yet — that's
  Stage 10
- `backend/scripts/test_breeth_client.py` — standalone verification;
  confirms missing-key path raises `BreethConfigError`, conditionally
  runs a live write/search round-trip only if a real key is present
  (skipped here); re-ran Stages 6/7/8 scripts, no regressions
- Commit: `feat(backend): add Breeth client for facts/search with connection verification`

### ✅ Stage 10 — Breeth Namespace on Init (DONE)
- `backend/app/models/breeth_mirror.py` — `BreethMirrorFact`, a local
  SQLite mirror of facts Aether attempts to write into Breeth (stub
  for Stage 15's `memory_service` to build a local fallback on if a
  live Breeth query ever fails)
- `backend/app/services/agent_service.py` — `_breeth_group_id()` /
  `_create_breeth_namespace()`: on agent creation, derives a
  deterministic `group_id` (`agent-<agent_id>`) — this *is* the
  namespace, since Breeth scopes by `group_id` rather than exposing a
  separate namespace-creation call — best-effort writes an identity
  fact into it via `BreethClient`, and always records the attempt as a
  `BreethMirrorFact` row (`synced=True/False`) regardless of whether
  the remote write actually succeeded
- `agent.breeth_agent_ref` now populated on creation (was `None`
  through Stage 9); always set, since the group_id is locally derived
  rather than something Breeth returns
- `backend/app/schemas/agent.py`, `backend/app/routes/agent.py` —
  `AgentInitResponse` gains `breethAgentRef`
- `backend/app/models/__init__.py` — registered `BreethMirrorFact` so
  `create_all()` picks up the new `breeth_mirror_facts` table
- `backend/scripts/test_breeth_namespace.py` — standalone
  verification script (in-memory DB): confirms `breeth_agent_ref` is
  set and matches the deterministic group_id, exactly one
  `BreethMirrorFact` row is written with `synced=False` (no real
  `BREETH_API_KEY` in this sandbox), and a repeat `/init` call does
  not create a duplicate namespace/mirror row
- `backend/scripts/test_models.py` — updated its exact-table-set
  assertion to include the new `breeth_mirror_facts` table (this was
  the one regression the new table caused; fixed and re-verified)
- Verified: full server boot via FastAPI `TestClient` (startup event
  triggers `init_db()`), `POST /api/agent/init` called twice —
  `breethAgentRef` present and equal to `f"agent-{agentId}"` on both
  calls, second call created no duplicate rows; re-ran all Stage
  2/5/6/7/8/9 verification scripts end-to-end, no regressions
- Commit: `feat(backend): create per-agent Breeth namespace on init with local mirror`


### ✅ Stage 11 — Topic Sources Config + Fetcher (DONE)
- `backend/app/core/topic_sources.json` — 3 configured sources: Hacker
  News (Algolia Search API, industry), arXiv cs.AI (RSS, research),
  MIT Technology Review AI feed (RSS, commentary)
- `backend/app/services/topic_discovery.py` — `TopicCandidate`
  dataclass; `_parse_hn_algolia()` / `_parse_rss()` parsers (stdlib
  `ElementTree`, no new dependency); `fetch_source()` (per-source
  fetch+parse, catches and logs network/parse failures without
  raising); `discover_topics()` (aggregates across all sources,
  injectable `sources`/`client` for testing)
- No `sources_cache` dedup and no fingerprinting yet — every call
  currently re-returns everything; that's Stages 12/13
- `backend/scripts/test_topic_discovery.py` — standalone verification,
  fully offline via `httpx.MockTransport`: config validation, both
  parsers against canned response bodies (incl. missing-field skip
  cases), and a 3-source aggregation test where one source 503s and
  the other two still come back correctly
- Verified: all 4 checks pass; re-ran all 7 prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10), no regressions
- Commit: `feat(backend): add topic sources config and discovery fetcher`


### ✅ Stage 12 — Sources Cache (DONE)
- `backend/app/services/sources_cache_service.py` —
  `compute_content_hash()` (SHA-256 over `source_name` + `url`) and
  `filter_new_candidates()` (checks each candidate against
  `sources_cache`, inserts a row per new one, returns only the new
  ones); `discover_new_topics()` chains Stage 11's `discover_topics()`
  with the filter as the combined entry point later stages will call
- URL-level dedup only — catches the same feed entry re-fetched
  across scheduler runs; catching the same underlying story under a
  different URL/title is Stage 13's fingerprinting job, not this one
- `backend/scripts/test_sources_cache.py` — standalone verification
  (in-memory DB): hash determinism/sensitivity, first-call caching,
  repeat-call returns nothing with no duplicate rows, mixed batch
  (already-cached + new + in-batch duplicate) filters correctly
- Verified: all 4 checks pass; re-ran all 8 prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11), no regressions
- Commit: `feat(backend): wire sources_cache into discovery for URL-level dedup`

### ✅ Stage 13 — Fingerprinting (DONE)
- `backend/app/services/fingerprint.py` — `extract_keywords()`
  (tokenize, strip stopwords, dedupe, cap at `MAX_KEYWORDS`);
  `normalize_source()` (collapse to lowercase alphanumerics);
  `compute_fingerprint()` (SHA-256 over normalized source + sorted
  keywords); `fingerprint_candidate()` convenience wrapper over a
  `TopicCandidate`
- Distinct from Stage 12's literal, order-sensitive `source_name+url`
  hash: sorting the keywords means a reworded/reordered title for the
  same story from the same source collapses to the same fingerprint,
  which Stage 12's hash explicitly did not catch
- Not wired into `sources_cache`, any model, or any route yet — a
  standalone, unit-testable function only, as scoped; wiring
  near-duplicate rejection into the actual accept/reject path is
  Stage 14/15's job
- `backend/scripts/test_fingerprinting.py` — standalone verification,
  no DB needed: determinism, reworded/reordered-title collision (the
  core case), no collision for a genuinely different story or a
  different source, stopword stripping + `max_keywords` capping,
  source-name normalization, `fingerprint_candidate()` parity
- Verified: all 7 checks pass; re-ran all 9 prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12), no regressions
- Commit: `feat(backend): add title+keywords+source fingerprinting for near-duplicate detection`

### ✅ Stage 14 — Editorial Judgment (DONE)
- `backend/app/services/editorial_judgment.py` — `judge_candidate()`
  (fingerprint short-circuit against `rejected_topics`, then
  `LLMProvider.judge()` seeded with the full persona voice profile,
  strict `ACCEPT`/`REJECT` parsing, fail-closed on any error/ambiguity,
  persists rejections); `judge_candidates()` batch wrapper
- Fingerprint short-circuit (Stage 13) skips the LLM entirely for a
  reworded/reordered-title near-duplicate of an already-rejected
  topic, per `RejectedTopic`'s own Stage 2 docstring
- All editorial criteria (accept/reject standards) live in
  `persona.json` via the system prompt — no editorial logic hardcoded
  in this module
- Not wired into any route/scheduler yet — standalone functions only
- `backend/scripts/test_editorial_judgment.py` — standalone
  verification with a scripted fake provider (no API key needed):
  ACCEPT parsing (no rejection logged), REJECT parsing (logged with
  fingerprint+reason), fingerprint short-circuit (zero LLM calls, no
  duplicate row), unparseable-response and provider-exception
  fail-closed paths, batch ordering
- Verified: all 6 checks pass; re-ran all 10 prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13), no regressions
- Commit: `feat(backend): add editorial judgment with fail-closed LLM accept/reject and rejected_topics logging`

### ✅ Stage 15 — Memory Service (Breeth Dedup) (DONE)
- `backend/app/services/memory_service.py` — `check_memory()`: Layer 1
  local, authoritative, network-free exact match against
  `posts.fingerprint` (Stage 13's algorithm, already stamped on every
  `Post`); Layer 2 soft semantic search via `BreethClient.search()`
  (Stage 9), scoped to the agent's own namespace
  (`agent.breeth_agent_ref`, Stage 10), using a fuzzy keyword-overlap
  check (`SEMANTIC_OVERLAP_THRESHOLD = 0.6`) over Breeth's `edges`
  response to catch a same-story-different-source case fingerprinting
  can't. `check_memory_batch()` batches it over a list.
- Deliberately fails **open** on Breeth specifically (opposite posture
  from Stage 14's fail-closed editorial judgment): a missing
  `BREETH_API_KEY` or outage must never block an otherwise-novel,
  already-accepted candidate, per "Known Constraints" #2 and the
  PRD's "feed must grow on its own" success criterion. On a Breeth
  failure, falls back to a best-effort local keyword scan over
  `breeth_mirror_facts` (Stage 10's local mirror, whose own docstring
  reserved this exact fallback for this stage) — typically empty
  until Stage 17's publisher starts writing to it, which is expected.
- Not wired into any route or scheduler yet — standalone functions
  only, same posture as Stages 12 and 14.
- `backend/scripts/test_memory_service.py` — standalone verification
  with a fake Breeth client (no API key needed): Layer 1 fingerprint
  match short-circuits with zero Breeth calls; a genuinely new
  candidate passes with no matching edges; a semantically similar edge
  is flagged; a Breeth exception falls back to the local mirror and,
  empty, fails open; a Breeth exception plus a matching synced mirror
  fact still flags a duplicate via the fallback; an agent with no
  Breeth namespace yet skips the semantic check cleanly; batch
  ordering via `check_memory_batch()`.
- Verified: all 7 checks pass; re-ran all 11 prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14), no
  regressions.
- Commit: `feat(backend): add memory service with local fingerprint + Breeth semantic dedup against published topics, failing open on Breeth`

### ✅ Stage 16 — Post Writer (DONE)
- `backend/app/services/post_writer.py` — `write_post()`: takes the
  whole accepted `JudgmentResult` (Stage 14, not just the candidate)
  so the original editorial acceptance reason grounds the generated
  rationale; builds a prompt from the candidate's concrete fields plus
  that reason, calls `LLMProvider.generate()` (Stage 6/7) seeded with
  the persona's full voice profile (Stage 5), and requires a strict
  `TITLE:`/`RATIONALE:`/`CONTENT:` response, parsed positionally with
  all three markers required, in order, non-empty.
- Deliberately fails **loud** (`PostWriteError`) on any generation or
  parsing failure — a third posture distinct from Stage 14's fail-
  closed and Stage 15's fail-open, justified by there being no safe
  placeholder post to fall back to.
- `sources` populated with `[candidate.url]` only, matching
  `persona.json`'s `sourcing_standards.minimum_sources: 1`; source
  aggregation beyond the single URL a candidate carries is explicitly
  out of scope for this stage.
- Not wired into any route or scheduler yet — standalone function
  only, same posture as Stages 12, 14, 15.
- `backend/scripts/test_post_writer.py` — standalone verification with
  a scripted fake provider (no API key needed): well-formed response
  parses correctly with sources/fingerprint carried through; missing
  marker raises; out-of-order sections raise; empty section raises;
  provider exception raises `PostWriteError` without leaking the raw
  exception; a rejected `JudgmentResult` raises immediately with zero
  provider calls; empty response string raises.
- Verified: all 7 checks pass; re-ran all 12 prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15), no
  regressions.
- Commit: `feat(backend): add post writer generating title/content/rationale via LLMFactory, failing loud on malformed output`

### ✅ Stage 17 — Publisher (DONE)
- `backend/app/services/publisher.py` — `publish_post()`: persists a
  Stage 16 `WrittenPost` as a `Post` row (title, content, rationale,
  JSON-encoded sources, fingerprint), then best-effort pushes a
  `published` fact to Breeth via `BreethClient.write_fact()`, mirrored
  locally to `breeth_mirror_facts` regardless of remote success —
  reusing Stage 10's exact namespace-creation pattern rather than a
  new one. The mirrored/pushed fact's `object` is the post's own
  title so Stage 15's keyword-overlap matching has real text to
  compare against once wired together. Skips the remote call (but
  still mirrors locally, `group_id="unassigned"`) when the agent has
  no Breeth namespace yet.
- The `Post` row write itself is a plain, unconditional DB write — no
  fail-open/fail-closed framing needed, unlike the Breeth call.
- Not wired into any route or scheduler yet — standalone function
  only, same posture as every service stage since Stage 12.
- `backend/scripts/test_publisher.py` — standalone verification with
  a fake Breeth client (no API key needed): Post persisted with
  correct fields + generated id; successful Breeth write yields a
  synced mirror fact with the post's title as object; a Breeth
  exception still persists the Post and yields a non-synced mirror
  fact; an agent with no namespace skips the remote call but still
  persists + mirrors locally; two distinct posts create two
  independent rows; a persisted fingerprint round-trips for a future
  lookup.
- Verified: all 6 checks pass; re-ran all 13 prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16), no
  regressions.
- Commit: `feat(backend): add publisher persisting posts and pushing best-effort published facts to Breeth`

## 14. Last Delivered File

**`aether-stage17.zip`** — cumulative project ZIP containing everything
through Stage 17 (backend + frontend skeletons, all DB models incl.
Breeth mirror, `/init` fully wired with persona/LLM/Breeth-namespace
logic, persona bible, LLM provider abstraction with two providers,
Breeth client, topic sources config + discovery fetcher, sources_cache
dedup, title+keywords+source fingerprinting, LLM-driven editorial
judgment with fail-closed accept/reject, memory service with local
fingerprint + fail-open Breeth semantic dedup, LLM-driven post writer
with fail-loud generation/parsing, publisher persisting posts + Breeth
published facts, and docs for stages 0–17).

## 15. How To Resume

Paste this document into a new conversation and say:

> "Continue from Stage 18. Last delivered ZIP: aether-stage17.zip"

Claude should then:
1. Re-read this doc to restore full context (scope, stack, rules, plan)
2. Start Stage 18 exactly as planned: Scheduler Wiring — chain Stages
   11/12 → 14 → 15 → 16 → 17 (`discover_new_topics()` →
   `judge_candidates()` (accepted only) → `check_memory_batch()`
   (not-duplicate only) → `write_post()` → `publish_post()`) behind
   APScheduler, driven by `PUBLISH_INTERVAL_MINUTES` from the
   environment — the first point the full autonomous pipeline runs
   end-to-end
3. Continue following Rule 13 (docs + log + commit + ZIP + stop for
   approval) for every stage from there on
