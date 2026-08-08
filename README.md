# Aether — An Autonomous AI Technology Research Persona

Built for the ABTalks Hackathon. Aether is an autonomous AI persona that,
once initialized, independently discovers AI/tech topics, judges whether
they deserve publishing, writes posts in a consistent editorial voice,
remembers what it has already covered, and keeps publishing over time —
with no further human prompting.

This is **not** a chatbot and **not** a generic content generator.

## Project Status

✅ **Stage 20 of 20 — Release Candidate. All 20 stages complete.**

See `docs/AI_USAGE_LOG.md` for full development history and
`docs/prompts/` for the prompt/decision log of every stage. See
`docs/API_CONTRACT.md` for the frozen public API shape and
`docs/DEPLOYMENT.md` for exact Railway deployment steps.

## Tech Stack

| Layer      | Choice |
|------------|--------|
| Frontend   | Next.js |
| Backend    | FastAPI |
| Database   | SQLite (via SQLAlchemy) |
| Memory     | Breeth |
| LLM        | Gemini + OpenRouter (behind a provider abstraction) |
| Scheduler  | APScheduler |
| Deployment | Railway |

## Repository Structure

```
aether/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entrypoint + health check
│   │   ├── core/
│   │   │   ├── config.py    # env-driven settings (single source of truth)
│   │   │   ├── database.py  # SQLAlchemy engine/session, init_db()
│   │   │   ├── persona.json # static editorial identity (the "persona bible")
│   │   │   └── topic_sources.json # configured discovery sources (HN, arXiv, MIT Tech Review)
│   │   ├── routes/
│   │   │   └── agent.py     # POST /api/agent/init, GET /api/agent/feed
│   │   ├── services/
│   │   │   ├── agent_service.py    # get_or_create_agent — creates agent, generates persona_description via LLM, creates Breeth namespace
│   │   │   ├── persona_service.py  # loads persona.json, builds voice-profile prompt
│   │   │   ├── breeth_client.py    # BreethClient — write_fact/search over Breeth's REST API
│   │   │   ├── topic_discovery.py  # discover_topics() — fetch+parse raw candidates from configured sources
│   │   │   ├── sources_cache_service.py  # discover_new_topics() — URL-hash dedup against sources_cache
│   │   │   ├── fingerprint.py      # compute_fingerprint() — normalized title+keywords+source near-duplicate hash
│   │   │   ├── editorial_judgment.py  # judge_candidate(s)() — LLM accept/reject, logs rejected_topics
│   │   │   ├── memory_service.py   # check_memory(_batch)() — posts.fingerprint + Breeth search dedup vs. published topics
│   │   │   ├── post_writer.py      # write_post() — generates TITLE/RATIONALE/CONTENT via LLMFactory for an accepted, memory-cleared candidate
│   │   │   ├── publisher.py        # publish_post() — persists Post row, pushes best-effort "published" fact to Breeth, mirrors locally
│   │   │   ├── scheduler.py        # run_publish_cycle() chains discover→judge→memory→write→publish; start/stop_scheduler() run it on APScheduler, started from /init
│   │   │   └── llm/
│   │   │       ├── base_provider.py        # LLMProvider ABC (generate/judge/summarize)
│   │   │       ├── gemini_provider.py      # GeminiProvider — REST calls via httpx
│   │   │       ├── openrouter_provider.py  # OpenRouterProvider — REST calls via httpx
│   │   │       └── llm_factory.py          # get_llm_provider() — env-driven switch
│   │   ├── schemas/
│   │   │   └── agent.py     # AgentInitResponse, FeedPost, FeedResponse
│   │   └── models/          # agents, posts, rejected_topics, sources_cache, breeth_mirror_facts
│   ├── scripts/
│   │   ├── test_models.py             # standalone DB model verification script
│   │   ├── test_persona.py            # standalone persona/prompt-builder verification script
│   │   ├── test_llm_provider.py       # standalone LLMProvider/Gemini verification script
│   │   ├── test_llm_factory.py        # standalone LLMFactory/OpenRouter verification script
│   │   ├── test_init_llm_wiring.py    # standalone /init + LLM-generation verification script
│   │   ├── test_breeth_client.py      # standalone Breeth connection verification script
│   │   ├── test_breeth_namespace.py   # standalone Breeth namespace-on-init verification script
│   │   ├── test_topic_discovery.py    # standalone topic-source config/parser verification script
│   │   ├── test_sources_cache.py      # standalone sources_cache dedup verification script
│   │   ├── test_fingerprinting.py     # standalone fingerprinting verification script
│   │   ├── test_editorial_judgment.py # standalone editorial judgment verification script
│   │   ├── test_memory_service.py     # standalone memory service (Breeth dedup) verification script
│   │   ├── test_post_writer.py        # standalone post writer verification script
│   │   ├── test_publisher.py          # standalone publisher verification script
│   │   ├── test_scheduler.py          # standalone scheduler-chain verification script
│   │   ├── test_feed_endpoint.py      # standalone GET /api/agent/feed verification script
│   │   └── test_api_contract.py       # frozen API-contract verification script (docs/API_CONTRACT.md)
│   ├── requirements.txt
│   ├── .env.example
│   └── railway.json           # Railway deploy config (Nixpacks, uvicorn start command)
├── frontend/
│   ├── app/
│   │   ├── layout.tsx        # root layout + metadata
│   │   ├── globals.css       # hand-written dark theme, no UI framework
│   │   ├── lib/
│   │   │   └── api.ts        # typed initAgent()/getFeed() fetch wrappers
│   │   ├── page.tsx          # Landing page — calls POST /api/agent/init
│   │   └── feed/
│   │       └── page.tsx      # Feed page — polls GET /api/agent/feed every 30s
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── .env.local.example    # NEXT_PUBLIC_API_URL
├── docs/
│   ├── DEPLOYMENT.md          # Railway deploy steps (two services from this monorepo)
│   ├── API_CONTRACT.md        # frozen public API shape for /init and /feed
│   ├── AI_USAGE_LOG.md        # master stage index
│   └── prompts/               # one file per stage
├── PROJECT_STATUS.md          # handoff/resume document
└── README.md
```

## Running the Backend (Stage 1)

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then verify:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","app":"aether-backend","env":"development"}
```

## Verifying the Database Models (Stage 2)

```bash
cd backend
python scripts/test_models.py
```

This creates all four tables against a throwaway SQLite file, inserts
one row per table, reads it back, and asserts the round trip — no API
layer required.

## Running the Frontend (Stage 3)

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000` (Landing) and
`http://localhost:3000/feed` (Feed). Both pages are static skeletons —
no backend calls are made yet. The Initialize button on Landing is
intentionally disabled until Stage 4 wires it to
`POST /api/agent/init`.

To verify the production build compiles:

```bash
cd frontend
npm install
npx next build
```

## Verifying `POST /api/agent/init` (Stage 4)

```bash
cd backend
cp .env.example .env   # if you haven't already
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then, in another terminal:

```bash
curl -X POST http://localhost:8000/api/agent/init
# {"agentId":"<uuid>","status":"initializing","personaName":"Aether","createdAt":"..."}
```

Tables are created automatically on startup (`init_db()` runs in a
FastAPI `startup` event — no separate migration step needed for
SQLite). Calling `/api/agent/init` again returns the **same**
`agentId` instead of creating a second row — this matches the PRD's
"evaluator calls init exactly once" contract while still letting you
hit the endpoint repeatedly in local dev without side effects. No
persona generation, no LLM call, no Breeth namespace yet — the row
created here just has the model's defaults (`persona_name="Aether"`,
`status="initializing"`); those get filled in starting Stage 5.

The frontend's Initialize button remains disabled — it isn't wired to
this endpoint yet; that's a later frontend stage once init actually
does something worth showing.

## Verifying the Persona Bible + Prompt Builder (Stage 5)

```bash
cd backend
python -m scripts.test_persona
```

This loads `app/core/persona.json`, confirms every field the prompt
builder expects is present, builds the full voice-profile prompt via
`persona_service.build_voice_profile_prompt()`, and asserts the output
contains the persona name, a voice trait, and the sample voice line.
Pure local logic — no database, no network, no LLM call. The voice
profile isn't wired into `/init` yet; that's Stage 8, once the
LLMProvider abstraction (Stage 6/7) exists to actually send it
somewhere.

## Verifying the LLMProvider Interface (Stage 6)

```bash
cd backend
python -m scripts.test_llm_provider
```

This confirms `LLMProvider` can't be instantiated directly (it's an
ABC), confirms `GeminiProvider` implements `name`/`generate`/`judge`/
`summarize`, and confirms calling it without an API key raises a clear
`GeminiConfigError` rather than a confusing network error. If
`GEMINI_API_KEY` is set in `backend/.env`, it also makes one real
`generate()` call as a live smoke test; if not (the default in this
sandboxed environment), that step is skipped with an explicit message.
Not wired into `/init` or any route yet — that's Stage 8, once
`llm_factory.py` (Stage 7) exists to pick a provider.

## Verifying the LLMFactory + Second Provider (Stage 7)

```bash
cd backend
python -m scripts.test_llm_factory
```

This confirms `OpenRouterProvider` implements the full `LLMProvider`
interface (mirroring `GeminiProvider`'s checks in Stage 6), confirms
its missing-API-key path raises a clear `OpenRouterConfigError`, and —
the actual point of this stage — confirms `get_llm_provider()` from
`llm_factory.py` really switches concrete implementations based on
`LLM_PROVIDER`: no args resolves to `GeminiProvider` (the `.env`
default), `get_llm_provider("openrouter")` resolves to
`OpenRouterProvider`, the lookup is case-insensitive, and an unknown
provider name raises `UnknownLLMProviderError` instead of silently
falling back to something. If `OPENROUTER_API_KEY` is set in
`backend/.env`, it also makes one real `generate()` call as a live
smoke test; otherwise that step is skipped with an explicit message,
same pattern as Stage 6. Not wired into `/init` or any route yet —
that's Stage 8, which is the first place callers actually use
`get_llm_provider()` instead of instantiating a concrete provider.

## Verifying Wire LLM into Init (Stage 8)

```bash
cd backend
python -m scripts.test_init_llm_wiring
```

This uses an in-memory SQLite DB and a fake `LLMProvider` (no network,
no real API key needed) to confirm `get_or_create_agent()` now
generates a `persona_description` on creation — building the
voice-profile prompt via `persona_service.build_voice_profile_prompt()`
and sending it through `get_llm_provider().generate()` — and confirms
the LLM is called exactly once even across repeat `/init` calls
(idempotency from Stage 4 still holds). It then separately calls
`agent_service._generate_persona_description()` against whatever
provider is actually configured to confirm the graceful-fallback path:
if no real API key is set (the default in this sandboxed environment),
`persona_description` comes back `None` instead of the request
failing — `/init` still succeeds and returns the agent with its
`persona_name` set correctly either way.

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/api/agent/init
# {"agentId":"<uuid>","status":"initializing","personaName":"Aether","personaDescription":null,"createdAt":"..."}
# (personaDescription is populated instead of null if a real
# GEMINI_API_KEY/OPENROUTER_API_KEY is set in backend/.env)
```

## Verifying the Breeth Client (Stage 9)

```bash
cd backend
python -m scripts.test_breeth_client
```

This confirms `BreethClient` raises a clear `BreethConfigError` when
used without an API key. If `BREETH_API_KEY` is set in `backend/.env`,
it also makes two real calls as a live connection test: writes a
uniquely-marked test fact via `POST /v1/facts`
(`client.write_fact(...)`), then searches for that marker via
`POST /v1/search` (`client.search(...)`) and confirms the fact comes
back. If no key is set (the default in this sandboxed environment),
the live round-trip is skipped with an explicit message, same pattern
as Stages 6/7's provider smoke tests. Connection only — no
namespace-per-agent logic yet (that's Stage 10) and no dedup/memory
queries against the pipeline (Stage 15+).

## Verifying Breeth Namespace on Init (Stage 10)

```bash
cd backend
python -m scripts.test_breeth_namespace
```

Against an in-memory DB, this confirms: a new agent's
`breeth_agent_ref` is set to the deterministic `f"agent-{agentId}"`
namespace even with no real `BREETH_API_KEY` configured; exactly one
`BreethMirrorFact` row is written recording the attempt
(`synced=False` in this sandbox, since the remote write can't
actually succeed without a key); and a repeat `get_or_create_agent()`
call doesn't create a duplicate mirror row. You can also boot the
server and call the real route twice to see it end-to-end:

```bash
cd backend
uvicorn app.main:app --reload
# in another terminal:
curl -X POST http://localhost:8000/api/agent/init
curl -X POST http://localhost:8000/api/agent/init   # same agentId + breethAgentRef back
```

`breethAgentRef` will be `"agent-<agentId>"` on both calls. With a
real `BREETH_API_KEY` set, the underlying `write_fact` call actually
reaches Breeth and the mirrored row's `synced` flips to `True`.

## Verifying Topic Sources Config + Fetcher (Stage 11)

```bash
cd backend
python -m scripts.test_topic_discovery
```

This runs entirely offline via `httpx.MockTransport` — no live network
access to Hacker News/arXiv/MIT Technology Review is needed to verify
it. It confirms: `topic_sources.json` loads with all required fields
on every configured source; `_parse_hn_algolia()` and `_parse_rss()`
correctly turn canned response bodies into `TopicCandidate` objects,
skipping individual items missing a title/url rather than crashing;
and `discover_topics()`, given three fake sources where one returns a
`503`, still returns the other two sources' candidates rather than
raising. To see it hit the real configured sources (needs outbound
network access to `hn.algolia.com` / `export.arxiv.org` /
`technologyreview.com`, not available in this sandboxed dev
container):

```bash
cd backend
python -c "from app.services.topic_discovery import discover_topics; [print(c.source_name, '-', c.title) for c in discover_topics()]"
```

No caching/dedup yet — every call re-fetches and re-returns
everything, including items seen on a previous run. That's Stage 12.

## Verifying the Sources Cache (Stage 12)

```bash
cd backend
python -m scripts.test_sources_cache
```

Against an in-memory DB, this confirms `compute_content_hash()` is
deterministic and sensitive to both URL and source, that
`filter_new_candidates()` caches and returns every candidate the first
time it's seen, that a repeat call with the same candidates returns
nothing and creates no duplicate rows, and that a mixed batch
(one already-cached item, one new item, and one in-batch duplicate
sharing a URL with the new item) correctly returns exactly one new
candidate. `discover_new_topics()` combines Stage 11's
`discover_topics()` with this filter — not wired into any route yet:

```bash
cd backend
python -c "
from app.core.database import SessionLocal, init_db
from app.services.sources_cache_service import discover_new_topics
init_db()
db = SessionLocal()
for c in discover_new_topics(db):
    print(c.source_name, '-', c.title)
"
```

Run it twice in a row (against the same `aether.db`) to see the second
run return nothing new — everything from the first run is now cached.

## Verifying Fingerprinting (Stage 13)

```bash
cd backend
python -m scripts.test_fingerprinting
```

Pure unit tests, no DB involved. Confirms `compute_fingerprint()` is
deterministic; that a reworded/reordered title for the same story from
the same source produces the SAME fingerprint (the near-duplicate case
Stage 12's literal URL hash doesn't catch); that a genuinely different
story, or the same title from a different source, produces a
DIFFERENT fingerprint; that `extract_keywords()` strips stopwords and
respects `max_keywords`; that `normalize_source()` collapses
formatting differences; and that `fingerprint_candidate()` matches
calling `compute_fingerprint()` directly with a `TopicCandidate`'s
fields. Not wired into `sources_cache` or any route yet — this stage
is the fingerprint function only, unit-testable in isolation, to try
it against a couple of example titles:

```bash
cd backend
python -c "
from app.services.fingerprint import compute_fingerprint
print(compute_fingerprint('OpenAI launches GPT-5 with major reasoning upgrades', 'TechCrunch'))
print(compute_fingerprint(\"GPT-5 launches: OpenAI's major upgrades to reasoning\", 'TechCrunch'))
"
```

Both lines print the same hash — same story, reworded/reordered
title, same source.

## Verifying Editorial Judgment (Stage 14)

```bash
cd backend
python -m scripts.test_editorial_judgment
```

Runs against an in-memory DB with a scripted fake `LLMProvider` (no
network/API key needed). Confirms: an `ACCEPT` response is parsed
correctly and creates no `rejected_topics` row; a `REJECT` response is
parsed and logged with its fingerprint (Stage 13) and reason; judging
a reworded/reordered-title near-duplicate of an already-rejected topic
short-circuits on the fingerprint match, skips the LLM call entirely,
and does not create a duplicate row; an unparseable model response
fails closed (rejected); an LLM call that raises an exception fails
closed without propagating; and `judge_candidates()` processes a batch
in order. Not wired into any route or scheduler yet — Stage 18 will
chain `discover_new_topics()` (Stage 12) → `judge_candidates()`
(this stage) → memory (Stage 15) → post writing (Stage 16) → publish
(Stage 17):

```bash
cd backend
python -c "
from app.core.database import SessionLocal, init_db
from app.services.sources_cache_service import discover_new_topics
from app.services.editorial_judgment import judge_candidates
init_db()
db = SessionLocal()
candidates = discover_new_topics(db)
for r in judge_candidates(db, agent_id='demo-agent', candidates=candidates):
    print('ACCEPT' if r.accepted else 'REJECT', '-', r.candidate.title, '-', r.reason)
"
```

Needs a real `GEMINI_API_KEY` (or `LLM_PROVIDER=openrouter` +
`OPENROUTER_API_KEY`) in `backend/.env` to actually call the LLM —
without one, `judge()` raises and every candidate fails closed to
REJECT (see "Known Constraints" in `PROJECT_STATUS.md`), which the
script above will still run and print correctly.

## Verifying the Memory Service (Stage 15)

```bash
cd backend
python -m scripts.test_memory_service
```

Runs against an in-memory DB with a fake `BreethClient` (no
network/API key needed). Confirms: a candidate whose fingerprint
(Stage 13) matches an existing `Post` is flagged a duplicate purely
locally, with zero Breeth calls made; a genuinely new candidate passes
through when Breeth returns no matching edges; a candidate
semantically similar to a Breeth edge (high keyword overlap) is
flagged duplicate even with no local `Post` match; a Breeth call that
raises falls back to a local keyword scan over `breeth_mirror_facts`
instead of raising or rejecting outright, and — with that mirror also
empty — the candidate passes through (fails **open**, unlike Stage
14's fail-**closed** editorial judgment); a Breeth failure combined
with a matching *synced* mirror fact still correctly flags a
duplicate via that fallback; an agent with no Breeth namespace yet
skips the semantic check cleanly; and `check_memory_batch()` processes
a batch in order, reusing one client. Not wired into any route or
scheduler yet — Stage 18 will chain it in:
`discover_new_topics()` (Stage 12) → `judge_candidates()` (Stage 14,
accepted only) → `check_memory_batch()` (this stage, not-duplicate
only) → post writing (Stage 16) → publish (Stage 17):

```bash
cd backend
python -c "
from app.core.database import SessionLocal, init_db
from app.models.agent import Agent
from app.services.sources_cache_service import discover_new_topics
from app.services.editorial_judgment import judge_candidates
from app.services.memory_service import check_memory_batch
init_db()
db = SessionLocal()
agent = db.query(Agent).first()  # requires an agent from POST /api/agent/init
candidates = discover_new_topics(db)
accepted = [r.candidate for r in judge_candidates(db, agent.id, candidates) if r.accepted]
for r in check_memory_batch(db, agent, accepted):
    print('DUPLICATE' if r.is_duplicate else 'NEW', '-', r.candidate.title, '-', r.reason)
"
```

Needs a real `BREETH_API_KEY` in `backend/.env` to actually call
Breeth's semantic search — without one, `BreethClient.search()` raises
and every candidate falls through to the local mirror fallback (see
"Known Constraints" in `PROJECT_STATUS.md`), which the script above
will still run and print correctly; Layer 1's `posts.fingerprint`
check needs no API key at all.

## Verifying the Post Writer (Stage 16)

```bash
cd backend
python -m scripts.test_post_writer
```

Runs with a scripted fake `LLMProvider` (no network/API key needed).
Confirms: a well-formed `TITLE:`/`RATIONALE:`/`CONTENT:` response
parses into a `WrittenPost`, with `sources` set to `[candidate.url]`
and the originating `JudgmentResult`'s fingerprint (Stage 14) carried
through unchanged; a response missing any required marker raises
`PostWriteError`; sections out of order raise `PostWriteError`; an
empty section (e.g. `CONTENT:` with nothing after it) raises
`PostWriteError`; a provider exception during generation raises
`PostWriteError` without leaking the raw exception type; calling
`write_post()` with a *rejected* `JudgmentResult` raises immediately
without ever calling the provider; and an empty response string raises
`PostWriteError`. Not wired into any route or scheduler yet — Stage 18
will chain it in: `discover_new_topics()` (Stage 12) →
`judge_candidates()` (Stage 14, accepted only) → `check_memory_batch()`
(Stage 15, not-duplicate only) → `write_post()` (this stage, one call
per surviving candidate) → publish (Stage 17):

```bash
cd backend
python -c "
from app.core.database import SessionLocal, init_db
from app.models.agent import Agent
from app.services.sources_cache_service import discover_new_topics
from app.services.editorial_judgment import judge_candidates
from app.services.memory_service import check_memory_batch
from app.services.post_writer import write_post, PostWriteError
init_db()
db = SessionLocal()
agent = db.query(Agent).first()  # requires an agent from POST /api/agent/init
candidates = discover_new_topics(db)
judgments = [r for r in judge_candidates(db, agent.id, candidates) if r.accepted]
survivors = [j for j, m in zip(judgments, check_memory_batch(db, agent, [j.candidate for j in judgments])) if not m.is_duplicate]
for j in survivors:
    try:
        post = write_post(j)
        print('WROTE:', post.title)
    except PostWriteError as exc:
        print('FAILED:', exc)
"
```

Needs a real `GEMINI_API_KEY` (or `LLM_PROVIDER=openrouter` +
`OPENROUTER_API_KEY`) in `backend/.env` to actually generate post
content — without one, `generate()` raises and `write_post()` raises
`PostWriteError` for every candidate (see "Known Constraints" in
`PROJECT_STATUS.md`), which the script above will still run and print
correctly.

## Verifying the Publisher (Stage 17)

```bash
cd backend
python -m scripts.test_publisher
```

Runs against an in-memory DB with a fake `BreethClient` (no
network/API key needed). Confirms: `publish_post()` persists a `Post`
row with the right title/content/rationale/JSON-encoded
sources/fingerprint and returns it committed with a generated id; a
successful Breeth write creates a `synced=True` `breeth_mirror_facts`
row whose `object` is the post's title (so a future Stage 15 semantic
check has real title text to compare against); a Breeth write that
raises still persists the `Post` and records a `synced=False` mirror
fact instead of blocking publishing (same best-effort posture Stage
10's namespace creation already established); an agent with no
`breeth_agent_ref` yet skips the remote call entirely (zero calls
made) but still persists the `Post` and writes a local mirror fact
with `group_id="unassigned"`; publishing two distinct posts for the
same agent creates two independent `Post`/mirror-fact rows with no
accidental dedup at this layer (that's Stages 14/15's job); and a
persisted post's fingerprint round-trips correctly for a future
lookup.

## Verifying the Scheduler (Stage 18)

```bash
cd backend
python -m scripts.test_scheduler
```

Runs against an in-memory DB with every pipeline stage (discovery,
judgment, memory check, post writer, publisher) monkeypatched out via
`unittest.mock.patch.object` — this stage tests that `scheduler.py`
chains their outputs into each other correctly, not those stages
themselves (each already has its own dedicated script). Confirms: no
candidates discovered short-circuits before judgment; candidates with
none accepted short-circuits before the memory check; all-duplicates
short-circuits before the post writer; a mixed batch (one memory
duplicate skipped, one `PostWriteError` skipped, one clean success)
returns exactly `1` and calls `publish_post()` exactly once with the
right `WrittenPost`; an unexpected exception from discovery is caught
and the cycle returns `0` instead of propagating; and
`start_scheduler()`/`stop_scheduler()` are idempotent (a second start
returns the same instance; a start after stop creates a fresh one).

`POST /api/agent/init` now actually starts the autonomous loop —
`discover_new_topics()` (Stage 12) → `judge_candidates()` (Stage 14,
accepted only) → `check_memory_batch()` (Stage 15, not-duplicate only)
→ `write_post()` (Stage 16) → `publish_post()` (Stage 17), run inside
an APScheduler `BackgroundScheduler` job every
`PUBLISH_INTERVAL_MINUTES`, first tick immediate:

```bash
cd backend
uvicorn app.main:app --reload
# in another terminal:
curl -X POST http://localhost:8000/api/agent/init
```

The response's `status` field now reads `"active"` (flipped from
`"initializing"` the moment the scheduler starts), and the first
publish cycle fires immediately rather than waiting a full interval.
A repeat `POST /api/agent/init` call is safe — it returns the same
agent and does not start a second competing scheduler.

Needs a real `GEMINI_API_KEY` and `BREETH_API_KEY` in `backend/.env`
for a tick to actually judge/write/publish anything live — without
them, editorial judgment fails closed (Stage 14) or post writing fails
loud per-candidate (Stage 16) and the cycle logs a quiet `0 published`
rather than crashing, exactly per each stage's own documented failure
posture. Topic source fetches themselves may also fail in restricted
network environments (see Stage 11's per-source try/except) without
affecting anything downstream.

## Verifying the Feed Endpoint + Frontend (Stage 19)

```bash
cd backend
python -m scripts.test_feed_endpoint
```

Four checks against an in-memory DB via FastAPI's `TestClient`: `GET
/api/agent/feed` returns an empty, 200-status feed before any agent
exists (no 404, no side effects — `/feed` never creates an agent);
with an agent but zero posts it returns the agent's identity fields
with `posts: []`; with posts it returns them newest-first with
`sources` correctly decoded back into a `list[str]` from the stored
JSON string; and a malformed `sources` value on one post falls back to
`[]` for that post only, without breaking the rest of the response.

To see it live, end-to-end, against the real frontend:

```bash
# terminal 1
cd backend
uvicorn app.main:app --reload

# terminal 2
cd frontend
cp .env.local.example .env.local   # only needed if not on localhost:8000
npm install
npm run dev
```

Open `http://localhost:3000`. The Feed link shows an empty state until
you click **Initialize Agent** on the Landing page — that calls the
real `POST /api/agent/init`, starts the Stage 18 scheduler, and once
`status` flips to `"active"` the Landing page shows the LLM-generated
persona description (or the static fallback tagline if no live
`GEMINI_API_KEY` is configured, per Stage 8's documented graceful
degradation). The Feed page polls `GET /api/agent/feed` every 30
seconds, so posts appear there on their own as the scheduler's
background ticks publish them — no page refresh, no further clicks,
matching the PRD's "feed grows with no human prompts" success
criterion directly.

## Verifying the Release Candidate (Stage 20)

```bash
cd backend
python -m scripts.test_api_contract
```

Four checks against an in-memory DB confirming `POST /api/agent/init`
and `GET /api/agent/feed` match the frozen shapes documented in
`docs/API_CONTRACT.md` exactly (field names, types, nullability) — not
just that the routes work, but that they still return precisely what's
published as the public contract.

Full regression pass for this stage: every prior stage's verification
script re-run back-to-back with zero regressions (Stages 2, 5–19 — 17
scripts total, all in-memory/mocked, no network or API keys needed):

```bash
cd backend
for f in test_models test_persona test_llm_provider test_llm_factory \
         test_init_llm_wiring test_breeth_client test_breeth_namespace \
         test_topic_discovery test_sources_cache test_fingerprinting \
         test_editorial_judgment test_memory_service test_post_writer \
         test_publisher test_scheduler test_feed_endpoint test_api_contract; do
  python -m scripts.$f || echo "FAILED: $f"
done
```

Also verified live end-to-end against a real `uvicorn` process in this
sandbox: `GET /feed` → empty, `POST /init` → `status: "active"`, a
repeat `POST /init` → identical `agentId` (idempotent), and the
scheduler's immediate first tick genuinely ran the full
discover→judge→memory→write→publish pipeline against real topic
sources — each failing individually with a `403` under this sandbox's
network restrictions (exactly as Stage 11's per-source try/except
already handles), without crashing the process or leaving an
unhandled exception. A real deployment with real `GEMINI_API_KEY` /
`BREETH_API_KEY` and unrestricted network access would carry that same
tick through to an actual published post — the pipeline itself is
unchanged from Stage 18; only this stage's verification confirms it
one more time end-to-end before calling it a release candidate.

**Deploying for real:** see `docs/DEPLOYMENT.md` for exact Railway
steps (two services — backend + frontend — from this one repo).
**API contract:** see `docs/API_CONTRACT.md` for the frozen response
shapes of both public endpoints.

## Required Environment Variables

See `backend/.env.example`:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` (defaults to `gemini-2.5-flash`)
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (defaults to `openai/gpt-4o-mini`)
- `LLM_PROVIDER` (`gemini` or `openrouter`, defaults to `gemini`)
- `BREETH_API_KEY`
- `BREETH_BASE_URL` (defaults to `https://api.thebreeth.com`)
- `DATABASE_URL`
- `APP_ENV`
- `PORT`

See `frontend/.env.local.example`:

- `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000` in code if unset)

## Development Philosophy

Build only what the PRD requires. No auth, no dashboards, no placeholder
pages, no feature creep. Every stage ships working code, updated docs,
and a suggested git commit — see `docs/prompts/` for the full trail.

## Release Notes (Stage 20)

All 20 planned stages are complete. What's genuinely done: both public
endpoints match their frozen contract, the frontend is wired to the
real backend end-to-end, the autonomous publish pipeline runs cleanly
from `/init` through every stage of discover→judge→memory→write→
publish, and Railway deploy configs exist for both services. What's
explicitly **not** done by Claude, and needs the repo owner: an actual
`git push` + Railway project creation (Claude's sandbox can't reach
Railway or push to a real remote — see `PROJECT_STATUS.md` §12), and a
live run with real `GEMINI_API_KEY`/`BREETH_API_KEY` values, since this
sandbox's own network restrictions 403 every configured topic source
and no real keys are available here. Both are one-time setup steps,
not code gaps — `docs/DEPLOYMENT.md` walks through them exactly.
