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

---

### Stage 11
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Topic Sources Config + Fetcher
**Summary:** Added `app/core/topic_sources.json` — three configured
sources spanning the categories the persona bible cares about:
Hacker News via the Algolia Search API (`hn_algolia`, industry chatter),
arXiv cs.AI's RSS feed (`rss`, research), and MIT Technology Review's
AI topic feed (`rss`, commentary). Added
`app/services/topic_discovery.py`: `TopicCandidate` (title, url,
source_name, category, optional summary/published_at — deliberately
minimal, no id/fingerprint yet), `_parse_hn_algolia()` and
`_parse_rss()` (stdlib `xml.etree.ElementTree`, no new dependency),
`fetch_source()` (fetches + parses one source, catching network/parse
failures per-source so one bad feed can't take down discovery for the
rest), and `discover_topics()` (aggregates across all configured
sources, injectable `sources`/`client` params for testing). No
caching/dedup against `sources_cache` yet — that's Stage 12. Verified
entirely offline using `httpx.MockTransport`: canned Algolia and RSS
response bodies confirm the parsers handle missing-field items
correctly (skipped, not crashed-on), and a 3-source aggregation test
where one source returns `503` confirms `discover_topics()` still
returns the other two sources' candidates rather than raising —
stronger offline coverage than the live-API stages (6/7/9) could get,
since parsing logic doesn't require real network access to verify,
only the live round-trip does (which those stages could only
conditionally test, and this stage doesn't attempt at all since no
live call is being made to a stateful third-party account).
**Files Changed:**
- `backend/app/core/topic_sources.json`
- `backend/app/services/topic_discovery.py`
- `backend/scripts/test_topic_discovery.py`
- `README.md`
**Commit:** `feat(backend): add topic sources config and discovery fetcher`
**Prompt File:** `docs/prompts/12_stage11.md`

---

### Stage 12
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Sources Cache
**Summary:** Wired the `SourceCache` model (Stage 2, unused until now)
into the discovery path. Added
`app/services/sources_cache_service.py`: `compute_content_hash()` — a
deterministic SHA-256 over `source_name` + `url` — and
`filter_new_candidates()`, which checks each `TopicCandidate` (Stage
11) against `sources_cache` by hash, inserts a row for every new one,
and returns only the not-previously-seen candidates. Deliberately kept
this hash simpler than Stage 13's planned fingerprinting: it only
answers "have I cached this exact URL from this exact source," which
is sufficient to stop the same literal feed entry from being
re-cached/re-considered on back-to-back scheduler runs — catching the
same underlying story republished under a different URL or title
variant is explicitly Stage 13's job. `discover_new_topics()` chains
Stage 11's `discover_topics()` with the new filter as the single entry
point later stages (starting with Stage 18's scheduler) will call. Not
wired into any route yet. Verified against an in-memory DB: hash
determinism (same source+url -> same hash; different url or different
source -> different hash), first-call caching of all new candidates,
a repeat call with identical candidates returning nothing and creating
no duplicate rows, and a mixed batch (one already-cached, one new, one
in-batch duplicate sharing a URL) correctly collapsing to exactly one
new candidate and one new row.
**Files Changed:**
- `backend/app/services/sources_cache_service.py`
- `backend/scripts/test_sources_cache.py`
- `README.md`
**Commit:** `feat(backend): wire sources_cache into discovery for URL-level dedup`
**Prompt File:** `docs/prompts/13_stage12.md`

---

### Stage 13
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Fingerprinting
**Summary:** Added `app/services/fingerprint.py` — a normalized
title+keywords+source fingerprint function, separate from Stage 12's
literal `source_name+url` hash. `extract_keywords()` tokenizes a
title (and optional summary), strips a small stopword list, dedupes,
and caps at `MAX_KEYWORDS`. `normalize_source()` collapses a source
name to lowercase alphanumerics so formatting differences don't
affect the fingerprint. `compute_fingerprint()` hashes
`normalized_source + sorted(keywords)` with SHA-256 — sorting the
keywords (unlike Stage 12's raw, order-sensitive hash) is what lets a
reworded or reordered title for the same story, same source, still
collapse to the same fingerprint, which is the gap Stage 12 explicitly
left open. `fingerprint_candidate()` is a thin wrapper for
`TopicCandidate`. Nothing is wired into `sources_cache`, the DB, or
any route yet — this stage is the fingerprint function only, as
planned, unit-tested in isolation via
`backend/scripts/test_fingerprinting.py`: determinism; a
reworded/reordered title for the same story+source producing the same
fingerprint; a genuinely different story, and the same title from a
different source, both producing different fingerprints; stopword
stripping and `max_keywords` capping; source-name normalization; and
`fingerprint_candidate()` matching a direct `compute_fingerprint()`
call.
**Files Changed:**
- `backend/app/services/fingerprint.py`
- `backend/scripts/test_fingerprinting.py`
- `README.md`
**Commit:** `feat(backend): add title+keywords+source fingerprinting for near-duplicate detection`
**Prompt File:** `docs/prompts/14_stage13.md`

---

### Stage 14
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Editorial Judgment
**Summary:** Added `app/services/editorial_judgment.py`. `judge_candidate()`
first checks the candidate's Stage 13 fingerprint against existing
`rejected_topics` rows for the agent — a match short-circuits to an
immediate rejection without calling the LLM at all, matching what
`RejectedTopic`'s own Stage 2 docstring already said this table was
for ("prevents re-evaluating the same rejected topic repeatedly"). If
no match, builds a judgment prompt from the candidate's concrete
fields, calls `LLMProvider.judge()` (Stage 6/7) with the persona's
full voice profile (Stage 5's `build_voice_profile_prompt()`) as the
system prompt — so acceptance criteria come from `persona.json`'s
`editorial_values`/`topics_of_interest`/`topics_avoided`/
`sourcing_standards`, not from logic hardcoded in this module — and
parses the required `ACCEPT: <reason>` / `REJECT: <reason>` response
format. Any failure mode (provider exception, empty response,
unparseable text) fails closed to REJECT, matching the persona's
stated "prefer signal over volume — reject more than it accepts"
editorial value. Rejections are persisted to `rejected_topics` with
title, source, fingerprint, and reason; accepted candidates create no
row (nothing to publish yet — that's Stages 16/17).
`judge_candidates()` batches `judge_candidate()` over a list, matching
the shape Stage 12's `discover_new_topics()` already returns. Not
wired into any route or scheduler yet.
**Files Changed:**
- `backend/app/services/editorial_judgment.py`
- `backend/scripts/test_editorial_judgment.py`
- `README.md`
**Commit:** `feat(backend): add editorial judgment with fail-closed LLM accept/reject and rejected_topics logging`
**Prompt File:** `docs/prompts/15_stage14.md`

---

### Stage 15
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Memory Service (Breeth Dedup)
**Summary:** Added `app/services/memory_service.py`. `check_memory()`
checks an editorially-accepted candidate against two dedup layers
before it can reach Stage 16's post writer. Layer 1 is a local,
authoritative, network-free exact match against `posts.fingerprint`
(Stage 13's algorithm, already stamped on every `Post` per its Stage 2
docstring) — catches an exact reworded/reordered-title repeat of
something this agent already published. Layer 2 is a soft semantic
check via `BreethClient.search()` (Stage 9) scoped to the agent's own
namespace (`agent.breeth_agent_ref`, Stage 10): a fuzzy keyword-overlap
scan (`SEMANTIC_OVERLAP_THRESHOLD = 0.6`) over whatever `edges` Breeth
returns, catching the case fingerprinting structurally can't — the
same story covered from a different source/title that doesn't collapse
to the same fingerprint. Deliberately fails **open** on Breeth
specifically (unlike Stage 14's fail-closed LLM judgment): per
PROJECT_STATUS.md's "Known Constraints," there's no real
`BREETH_API_KEY` in this sandboxed environment, so a missing key or
outage must never block an otherwise-novel, already-accepted topic.
On a Breeth failure, falls back to a best-effort local keyword scan
over `breeth_mirror_facts` (Stage 10's local mirror table — its own
docstring reserved exactly this fallback for this stage); if that's
also empty (expected until Stage 17's publisher starts writing
post-published facts there), the candidate passes through as novel.
`check_memory_batch()` batches `check_memory()` over a list, reusing
one `BreethClient`. Not wired into any route or scheduler yet.
**Files Changed:**
- `backend/app/services/memory_service.py`
- `backend/scripts/test_memory_service.py`
- `README.md`
**Commit:** `feat(backend): add memory service with local fingerprint + Breeth semantic dedup against published topics, failing open on Breeth`
**Prompt File:** `docs/prompts/16_stage15.md`

---

### Stage 16
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Post Writer
**Summary:** Added `app/services/post_writer.py`. `write_post()` takes
a whole accepted `JudgmentResult` (Stage 14) — not just the candidate
— so the original editorial acceptance reason grounds the generated
rationale, and so the function can assert loudly (`PostWriteError`) if
ever mistakenly called with a rejected result, without touching the
LLM. Builds a prompt from the candidate's concrete fields plus that
acceptance reason, seeds `LLMProvider.generate()` (Stage 6/7) with the
persona's full voice profile (Stage 5) as the system prompt exactly as
Stage 14's judgment call does, and requires a strict
`TITLE:`/`RATIONALE:`/`CONTENT:` response format. `_parse_post_response()`
insists on all three markers present, in the correct order, each with
non-empty content — any deviation raises `PostWriteError` rather than
guessing or shipping partial content. Unlike Stage 14 (fails closed to
REJECT, a safe default verdict) and Stage 15 (fails open on Breeth,
since an outage isn't evidence of duplication), this stage fails
**loud**: there is no safe placeholder post to fall back to, so any
generation or parsing failure raises rather than silently producing
something. `sources` is populated with `[candidate.url]` only — source
aggregation beyond the single URL a candidate carries is out of scope
here (nothing in the 20-stage plan assigns it to this stage, and no
earlier stage's `TopicCandidate` carries more than one URL anyway).
Not wired into any route or scheduler yet.
**Files Changed:**
- `backend/app/services/post_writer.py`
- `backend/scripts/test_post_writer.py`
- `README.md`
**Commit:** `feat(backend): add post writer generating title/content/rationale via LLMFactory, failing loud on malformed output`
**Prompt File:** `docs/prompts/17_stage16.md`

---

### Stage 17
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Publisher
**Summary:** Added `app/services/publisher.py`. `publish_post()`
persists a Stage 16 `WrittenPost` as a `Post` row (title, content,
rationale, JSON-encoded sources, fingerprint, agent_id), then calls
`_push_published_fact()` to tell Breeth about it. Follows exactly the
best-effort-remote + always-local-mirror pattern
`agent_service._create_breeth_namespace()` (Stage 10) already
established: the `Post` row is a plain, unconditional DB write (no
special fail-open/fail-closed handling — a genuine DB failure here is
an ordinary unhandled error, same as any other required write in this
codebase), while the Breeth `write_fact()` call is wrapped in a broad
try/except and its outcome (`synced`) is recorded on a
`BreethMirrorFact` row regardless of success — deliberately mirroring
Stage 10's precedent rather than inventing a new pattern, since Stage
15's memory service already depends on that mirror table being
populated for its fallback path to have anything to find. The mirrored
fact's `object` is the post's own title (not a generic string),
specifically so Stage 15's keyword-overlap matching has real text to
compare a future candidate's title against. Skips the remote Breeth
call entirely (but still writes the local mirror row, with
`group_id="unassigned"`) when the agent has no `breeth_agent_ref` yet
— the legitimate case where `/init` ran without a working
`BREETH_API_KEY` (Stage 10's own documented fallback). Not wired into
any route or scheduler yet.
**Files Changed:**
- `backend/app/services/publisher.py`
- `backend/scripts/test_publisher.py`
- `README.md`
**Commit:** `feat(backend): add publisher persisting posts and pushing best-effort published facts to Breeth`
**Prompt File:** `docs/prompts/18_stage17.md`

### Stage 18
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Scheduler Wiring
**Summary:** Added `app/services/scheduler.py`. `run_publish_cycle(db, agent)`
chains the full autonomous pipeline exactly as every prior stage's
docstring already described it: `discover_new_topics()` (Stage 12) →
`judge_candidates()` (Stage 14, accepted only) → `check_memory_batch()`
(Stage 15, not-duplicate only) → `write_post()` (Stage 16) →
`publish_post()` (Stage 17). Each stage of the chain is wrapped in its
own try/except that logs and returns `0` rather than raising, so an
unexpected failure anywhere skips one cycle instead of ending the
autonomous loop entirely; `PostWriteError` (Stage 16's documented
fail-loud mode) is caught per-candidate inside the survivors loop so
one bad generation doesn't discard the rest of that cycle's batch.
`start_scheduler(agent_id)` is the only piece that knows about
APScheduler — idempotent via a module-level guard (mirrors
`get_or_create_agent()`'s own repeat-call contract), each tick opens
its own `SessionLocal()` session since a background-thread job has no
request-scoped session to reuse, and the first tick fires immediately
on start (then every `PUBLISH_INTERVAL_MINUTES` after) so the feed
visibly starts growing right after `/init` rather than after one full
interval first elapses. `routes/agent.py`'s `POST /api/agent/init` now
calls `start_scheduler(agent.id)` and flips `agent.status` to
`"active"`; `main.py` stops the scheduler on shutdown. Verified via
`unittest.mock.patch.object` against every chained function (six
checks: short-circuit paths at each empty-result gate, a mixed
duplicate/failure/success batch, an unexpected discovery exception
caught cleanly, and `start_scheduler`/`stop_scheduler` idempotency)
and confirmed live end-to-end with FastAPI's `TestClient` — `/init`
returns `status: "active"`, is idempotent on repeat calls, and its
immediate first tick genuinely ran the real pipeline against real
topic sources without crashing.
**Files Changed:**
- `backend/app/services/scheduler.py`
- `backend/app/routes/agent.py`
- `backend/app/main.py`
- `backend/scripts/test_scheduler.py`
- `README.md`
- `PROJECT_STATUS.md`
**Commit:** `feat(backend): wire discover->judge->memory->write->publish into an APScheduler-driven autonomous publish cycle, started from /init`
**Prompt File:** `docs/prompts/19_stage18.md`

---

### Stage 19
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Feed Endpoint + Feed Page
**Summary:** Added `GET /api/agent/feed`, the second and last public
endpoint the PRD allows. Returns the most recently created agent's
identity (`agentId`, `personaName`, `status`) plus every `Post` row for
that agent, newest first, via two new schemas (`FeedPost`,
`FeedResponse` in `schemas/agent.py`). Deliberately side-effect-free —
if `/init` was never called it returns an empty feed (all identity
fields `null`, `posts: []`) with a 200 rather than a 404 or creating an
agent as a side effect, keeping the "only 2 public endpoints, each with
one job" split from §5 intact. `Post.sources` is a JSON-encoded string
column (Stage 2); the route `json.loads()`s it per-post inside a
try/except so one malformed row falls back to `[]` instead of taking
down the whole feed response.

Wired both frontend pages against the real backend for the first time
— everything before this stage was a static skeleton. Added
`frontend/app/lib/api.ts` (typed `initAgent()`/`getFeed()` wrappers
around `fetch`, base URL from `NEXT_PUBLIC_API_URL`, default
`localhost:8000`). Landing page's "Initialize Agent" button now calls
`POST /api/agent/init`, shows a loading/error state, and once active
displays the LLM-generated `personaDescription` and a link to the
Feed. Feed page is now a client component that fetches on mount and
polls every 30s (`setInterval`, cleaned up on unmount) — polling
rather than fetch-once, since the PRD's core success criterion is
specifically that the feed grows *without* a human re-triggering
anything, so the page needs to show that happening live. Each post
renders created time, title, content, rationale, and a linked list of
sources — exactly the four fields §4 specifies for the Feed Page, no
more.

Verified with a new `backend/scripts/test_feed_endpoint.py`
(`TestClient` + in-memory SQLite via `StaticPool`, four checks: empty
feed pre-init, agent-with-zero-posts shape, newest-first ordering with
`sources` correctly decoded back into a list, and a malformed
`sources` string falling back to `[]` without breaking other posts —
all pass), a live `uvicorn` + `curl` run confirming the exact same
empty→populated transition across a real `/init` call, and
`npm run build` on the frontend (compiles clean, both routes
prerender as static shells that hydrate and fetch client-side).
**Files Changed:**
- `backend/app/schemas/agent.py`
- `backend/app/routes/agent.py`
- `backend/scripts/test_feed_endpoint.py`
- `frontend/app/lib/api.ts`
- `frontend/app/page.tsx`
- `frontend/app/feed/page.tsx`
- `frontend/.env.local.example`
- `README.md`
- `PROJECT_STATUS.md`
**Commit:** `feat: add GET /api/agent/feed and wire both frontend pages to the live backend (init + polling feed)`
**Prompt File:** `docs/prompts/20_stage19.md`

---

### Stage 20
**Date:** 2026-08-08
**AI Tool Used:** Claude (Sonnet 5)
**Objective:** Release Candidate
**Summary:** Final stage — no new application code, since Stage 19
already closed out the PRD's full functional scope (both endpoints,
both pages, the autonomous pipeline). This stage adds what a release
candidate needs beyond working code: `backend/railway.json` and
`frontend/railway.json` (Nixpacks build/start config for two separate
Railway services from this one repo — chosen over a single combined
service specifically because the backend runs a long-lived
`BackgroundScheduler` that shouldn't restart on every frontend
redeploy); `docs/DEPLOYMENT.md`, an exact copy-pasteable walkthrough
for the repo owner to actually create both Railway services, set env
vars, and verify the live deployment (Claude's sandbox cannot push to
a real GitHub remote or Railway project, per the Known Constraints in
`PROJECT_STATUS.md` §12 — this was flagged again explicitly rather
than silently skipped); `docs/API_CONTRACT.md`, freezing the exact
JSON shape of both public endpoints as documentation; and
`backend/scripts/test_api_contract.py`, a new verification script
distinct in purpose from Stage 19's `test_feed_endpoint.py` — it
asserts the *documented contract* (field names, types, nullability)
holds against the real FastAPI app, rather than testing route logic.

Ran a full regression pass: all 17 prior verification scripts
(Stages 2, 5–19) re-run back-to-back, zero regressions — confirms
Stage 19/20's additions (both purely additive: a new route + two new
schema classes + a new script) didn't touch anything load-bearing.
Also did a genuine live end-to-end run against a real `uvicorn`
process in this sandbox (not just `TestClient`): `GET /feed` returns
empty, `POST /init` flips to `status: "active"` and is idempotent on
repeat, and the scheduler's immediate first tick ran the complete
discover→judge→memory→write→publish pipeline against real topic
sources — each failing individually with a `403` under this sandbox's
network restrictions exactly as Stage 11 already designed for, without
crashing. Also re-ran `npm run build` on the frontend — clean, no
regressions from Stage 19.

Updated `README.md`'s Project Status to "Stage 20 of 20 — Release
Candidate, all 20 stages complete," added a Stage 20 verification
section and a closing "Release Notes" section stating plainly what's
done vs. what still needs the repo owner (a real `git push` +
Railway project creation, and a live run with real
`GEMINI_API_KEY`/`BREETH_API_KEY`) — not glossed over as if the
sandbox could do those itself.
**Files Changed:**
- `backend/railway.json`
- `frontend/railway.json`
- `docs/DEPLOYMENT.md`
- `docs/API_CONTRACT.md`
- `backend/scripts/test_api_contract.py`
- `README.md`
- `PROJECT_STATUS.md`
**Commit:** `chore: release candidate — Railway deploy configs, API contract doc + check, full regression pass, deployment guide`
**Prompt File:** `docs/prompts/21_stage20.md`

---

## Post-Stage-20 — Evaluator Contract Audit Fixes

**Prompt:** User-supplied Hinglish audit checklist covering: exact
feed/init API contract, OpenRouter-as-primary LLM, Breeth+SQLite
fallback verification, scheduler/persona/topic-source checks, editorial
rejection storage, `.env.example` cleanup, secrets hygiene, and a new
`docs/PROJECT_STATE.md` resume file.

**AI Response/Summary:** Audited each item against the actual Stage 20
codebase. Several items (Breeth/SQLite fallback design, editorial
rejection storage, scheduler chain, live topic sources, persona
definition) were already correctly implemented from earlier stages and
needed no code change. The API contract, however, did not match the
evaluator's exact shape — `/init` returned several extra fields beyond
`agentId`, and `/feed` used `content`/`title` instead of `text` and
wrapped posts in agent-identity fields. Fixed those, switched the
default LLM provider to OpenRouter (Gemini kept as optional fallback,
never mandatory), tightened `.env.example` to only variables
`core/config.py` actually reads, added a missing `backend/.gitignore`,
and updated the frontend and docs to match.

**What We Used:** Direct file edits against the existing Stage 20
codebase; no new architecture introduced.

**What We Changed:**
- `POST /api/agent/init` now returns only `{"agentId": "..."}` and
  accepts an optional `{"persona": {"name","domain"}}` body.
- `GET /api/agent/feed` now returns only `{"posts": [...]}`, each post
  with exactly `id`, `createdAt` (ISO 8601 UTC, `Z` suffix), `text`,
  `rationale`, `sources`.
- `LLM_PROVIDER` default changed from `gemini` to `openrouter`.
- `PUBLISH_INTERVAL_MINUTES` default changed from `60` to `30`.
- `.env.example` cleaned to only variables actually read.
- Frontend (`lib/api.ts`, `page.tsx`, `feed/page.tsx`) updated to the
  new response shapes.
- `docs/API_CONTRACT.md` rewritten to the new frozen contract.
- `docs/PROJECT_STATE.md` added.
- `backend/.gitignore` added.

**Files Changed:**
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

**Commit:** `fix: lock API to exact evaluator contract, OpenRouter as primary LLM, env cleanup, add PROJECT_STATE.md`

---

## Post-Stage-20 — Runtime Debugging, Railway Observability, and PRD Compliance Fixes

**Prompt:** User request to study backend execution, resolve feed empty issue on Railway, enable stdout logging, fix persona sourcing criteria, add Start/Stop controls to Landing UI, auto-resume background scheduler on app startup, and ensure full compliance with the hackathon rules and API contract.

**AI Response/Summary:** Analyzed backend execution pipeline end-to-end. Configured standard Python logging (`basicConfig`) for Railway observability. Relaxed persona sourcing standards (`persona.json`) to allow Hacker News and ArXiv topics to pass editorial judgment. Fixed `post_writer` parsing to handle markdown bold markers (`**TITLE:**`) cleanly. Implemented `on_startup` auto-resume for the background scheduler in `main.py`. Added `POST /api/agent/stop` endpoint and updated the frontend Landing page UI with Start/Stop agent toggle controls. Added optional `agentId` query parameter filtering to `GET /api/agent/feed` to strictly comply with the PRD evaluator contract (`GET /api/agent/feed?agentId=...`).

**What We Used:** Code analysis, logging setup, regex/string parsing refinements, and FastAPI route/UI enhancements.

**What We Changed:**
- `backend/app/main.py`: Added stdout `logging.basicConfig(level=logging.INFO)` and `on_startup` auto-resume for active agents.
- `backend/app/core/persona.json`: Updated sourcing standards to accept Hacker News and ArXiv topics.
- `backend/app/services/editorial_judgment.py`: Added logging for ACCEPT/REJECT verdicts and markdown-tolerant parsing.
- `backend/app/services/post_writer.py`: Made `_parse_post_response` tolerant to markdown bolding in section markers.
- `backend/app/routes/agent.py`: Added `POST /api/agent/stop` endpoint and `agentId` query parameter support in `GET /api/agent/feed`.
- `frontend/app/lib/api.ts`: Added `stopAgent()` fetch wrapper and fixed status handling.
- `frontend/app/page.tsx`: Added Start/Stop agent toggle button and client-side status persistence.
- `docs/AI_USAGE_LOG.md`: Documented all post-Stage-20 updates for Hackathon Stage 1 & 2 verification.

**Files Changed:**
- `backend/app/main.py`
- `backend/app/core/persona.json`
- `backend/app/services/editorial_judgment.py`
- `backend/app/services/post_writer.py`
- `backend/app/routes/agent.py`
- `frontend/app/lib/api.ts`
- `frontend/app/page.tsx`
- `docs/AI_USAGE_LOG.md`

**Commit:** `fix: add agentId query param filter to feed API and update AI_USAGE_LOG for hackathon compliance`

---

## Post-Hackathon Session — 2026-08-09 — Bug Fixes, Discovery Expansion & Full UI Overhaul

**Date:** 2026-08-09
**AI Tool Used:** Antigravity (Google DeepMind)
**Objective:** Resolve all identified runtime bugs, expand topic discovery sources, add Railway persistence guidance, and completely overhaul Home and Feed page UI/UX.

### Bug Fix #1: Scheduler Auto-Start on Restart (Critical)
**Root Cause:** `on_startup()` in `main.py` was unconditionally starting the scheduler for any existing agent regardless of `status`, so a paused agent would restart automatically on every backend redeploy or crash-restart on Railway.

**Fix:** Added explicit `agent.status == "active"` check before calling `start_scheduler()`. Paused agents now stay paused across restarts.

**File:** `backend/app/main.py`

---

### Bug Fix #2: Topic Source Exhaustion & Algolia Limits
**Root Cause:** Only 8 sources configured, HN Algolia limited to default 20 hits/page — within 2-3 cycles all fresh candidates were consumed and no new content arrived for hours.

**Fixes Applied:**
- Added `hitsPerPage=50` to all HN Algolia endpoints.
- Added 2 new HN Algolia queries: OpenAI/Anthropic/DeepMind/Claude, PyTorch/HuggingFace/vLLM/LangChain.
- Added Reddit RSS: `r/MachineLearning`, `r/LocalLLaMA`.
- Added TechCrunch AI RSS and Ars Technica Technology Lab RSS.
- Set custom `User-Agent` header in `httpx.Client` for Reddit RSS compatibility.
- Total sources grew from 8 → 14.

**Files:** `backend/app/core/topic_sources.json`, `backend/app/services/topic_discovery.py`

---

### Bug Fix #3: Railway SQLite Volume Persistence
**Fix:** Updated `docs/DEPLOYMENT.md` with clear instructions to mount a Railway persistent volume at `/app/data` and set `DATABASE_URL=sqlite:////app/data/aether.db` to preserve agent state and posts across redeploys.

**File:** `docs/DEPLOYMENT.md`

---

### Feature: Candidate Batch Capping (max 5 accepted per cycle)
**Objective:** Stop excessive 146-LLM-call per cycle runs. Cap judgment so each cycle stops after 5 accepted candidates, publishing 5 posts quickly rather than waiting minutes.

**Implementation:** Added `max_accepts` parameter to `judge_candidates()` with early-exit loop. Set `max_accepts=5` in `run_publish_cycle()`.

**Files:** `backend/app/services/editorial_judgment.py`, `backend/app/services/scheduler.py`

---

### Feature: Next Cycle Countdown Timer (Frontend)
**Objective:** Show users a live reverse countdown to next autonomous publish cycle slot.

**Implementation:**
- Added `get_next_run_time()` helper to `scheduler.py` that reads next APScheduler job run time.
- Extended `GET /api/agent/status` to return `nextRunTime` (ISO timestamp) and `sources` list.
- Frontend Home page uses a `setInterval` countdown timer to display `⏱ Next Autonomous Cycle Slot In: MMm SSs`.

**Files:** `backend/app/services/scheduler.py`, `backend/app/routes/agent.py`, `frontend/app/lib/api.ts`, `frontend/app/page.tsx`

---

### Feature: 14 Sources Pop-Out Modal (Frontend)
**Objective:** Let users see all configured ingestion sources in a clean UI pop-out.

**Implementation:** Ingestion Network stat card (home dashboard) now shows a `CLICK TO VIEW` badge. Clicking it opens a glassmorphic modal listing all 14 named sources with numbered list, scrollable area, and close button.

**File:** `frontend/app/page.tsx`

---

### UI Overhaul — Complete Home & Feed Page Redesign
**Objective:** Transform both pages from generic flat UI to premium editorial glassmorphic design.

**Design System Changes (`globals.css`):**
- Replaced `Inter` with `Fraunces` (display serif) + `Plus Jakarta Sans` (body).
- Ambient glowing mesh gradient background.
- New CSS tokens: `--panel-hover`, `--amber`, `--amber-glow`, `--font-serif`, `--font-sans`.
- New component classes: `dashboard-grid`, `stat-card`, `pipeline-card`, `pipeline-grid`, `pipeline-step`, `post-header`, `post-title`, `rationale-content`, `reconnect-banner`.

**Home Page (`page.tsx`):**
- Cinematic Hero with `hero-tag` pill, Fraunces serif heading, descriptive subheader.
- 3-column Dashboard Stats Grid: Agent Status, Total Posts, Ingestion Network.
- Unified Agent Control Card with inline countdown badge.
- 3-step Pipeline Architecture cards: Discover → Editorial → Memory & Publish.

**Feed Page (`feed/page.tsx`):**
- Magazine editorial layout for post cards with serif titles.
- Smart title extraction from post text.
- Smooth animated accordion for Editorial Rationale.
- `Live Sync Feed` pill badge cleanly above heading (fixed inline overflow bug).
- Reconnecting amber warning banner when backend is offline.
- Designed empty state with `Autonomous Pipeline Initializing` message.

---

### Responsive Design (All Screen Sizes)
**Objective:** Make both pages fully responsive across mobile, tablet, and desktop.

**Breakpoints Added:**
- `max-width: 768px` (Tablet/Small Laptop): Adjusted font sizes, grid columns, card padding, control card stacking.
- `max-width: 480px` (Mobile Phone): Full-width navbar, full-width buttons, single column grids, vertically stacked post headers.

**File:** `frontend/app/globals.css`

---

**All Commits (2026-08-09):**
- `fix: resolve backend startup & topic discovery bugs, update Railway volume docs, overhaul Home & Feed UI`
- `feat: batch candidate judgment to max 3 accepted items per cycle for fast response and steady cadence`
- `feat: add 5-post max accepts, 14 sources popout modal, and reverse countdown timer for next cycle slot`
- `style: add responsive CSS media queries for mobile, tablet, and desktop screens`
- `style: make Ingestion Network stat card explicitly interactive with click badge and glowing highlights`
- `fix: move Live Sync badge above Feed page title as a clean pill badge to fix overlap`

**Files Changed:**
- `backend/app/main.py`
- `backend/app/core/topic_sources.json`
- `backend/app/services/topic_discovery.py`
- `backend/app/services/editorial_judgment.py`
- `backend/app/services/scheduler.py`
- `backend/app/routes/agent.py`
- `docs/DEPLOYMENT.md`
- `docs/AI_USAGE_LOG.md`
- `docs/PROJECT_STATE.md`
- `frontend/app/lib/api.ts`
- `frontend/app/globals.css`
- `frontend/app/page.tsx`
- `frontend/app/feed/page.tsx`
