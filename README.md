# Aether — An Autonomous AI Technology Research Persona

Built for the ABTalks Hackathon. Aether is an autonomous AI persona that,
once initialized, independently discovers AI/tech topics, judges whether
they deserve publishing, writes posts in a consistent editorial voice,
remembers what it has already covered, and keeps publishing over time —
with no further human prompting.

This is **not** a chatbot and **not** a generic content generator.

## Project Status

🚧 **Stage 10 of 20 — Breeth Namespace on Init**

See `docs/AI_USAGE_LOG.md` for full development history and
`docs/prompts/` for the prompt/decision log of every stage.

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
│   │   │   └── persona.json # static editorial identity (the "persona bible")
│   │   ├── routes/
│   │   │   └── agent.py     # POST /api/agent/init
│   │   ├── services/
│   │   │   ├── agent_service.py    # get_or_create_agent — creates agent, generates persona_description via LLM, creates Breeth namespace
│   │   │   ├── persona_service.py  # loads persona.json, builds voice-profile prompt
│   │   │   ├── breeth_client.py    # BreethClient — write_fact/search over Breeth's REST API
│   │   │   └── llm/
│   │   │       ├── base_provider.py        # LLMProvider ABC (generate/judge/summarize)
│   │   │       ├── gemini_provider.py      # GeminiProvider — REST calls via httpx
│   │   │       ├── openrouter_provider.py  # OpenRouterProvider — REST calls via httpx
│   │   │       └── llm_factory.py          # get_llm_provider() — env-driven switch
│   │   ├── schemas/
│   │   │   └── agent.py     # AgentInitResponse (incl. personaDescription, breethAgentRef)
│   │   └── models/          # agents, posts, rejected_topics, sources_cache, breeth_mirror_facts
│   ├── scripts/
│   │   ├── test_models.py             # standalone DB model verification script
│   │   ├── test_persona.py            # standalone persona/prompt-builder verification script
│   │   ├── test_llm_provider.py       # standalone LLMProvider/Gemini verification script
│   │   ├── test_llm_factory.py        # standalone LLMFactory/OpenRouter verification script
│   │   ├── test_init_llm_wiring.py    # standalone /init + LLM-generation verification script
│   │   ├── test_breeth_client.py      # standalone Breeth connection verification script
│   │   └── test_breeth_namespace.py   # standalone Breeth namespace-on-init verification script
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.tsx        # root layout + metadata
│   │   ├── globals.css       # hand-written dark theme, no UI framework
│   │   ├── page.tsx          # Landing page (static skeleton)
│   │   └── feed/
│   │       └── page.tsx      # Feed page (static skeleton)
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
└── docs/
    ├── AI_USAGE_LOG.md        # master stage index
    └── prompts/               # one file per stage
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

## Development Philosophy

Build only what the PRD requires. No auth, no dashboards, no placeholder
pages, no feature creep. Every stage ships working code, updated docs,
and a suggested git commit — see `docs/prompts/` for the full trail.
