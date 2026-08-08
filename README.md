# Aether — An Autonomous AI Technology Research Persona

Built for the ABTalks Hackathon. Aether is an autonomous AI persona that,
once initialized, independently discovers AI/tech topics, judges whether
they deserve publishing, writes posts in a consistent editorial voice,
remembers what it has already covered, and keeps publishing over time —
with no further human prompting.

This is **not** a chatbot and **not** a generic content generator.

## Project Status

🚧 **Stage 6 of 20 — LLMProvider Interface**

See `docs/AI_USAGE_LOG.md` for full development history and
`docs/prompts/` for the prompt/decision log of every stage.

## Tech Stack

| Layer      | Choice |
|------------|--------|
| Frontend   | Next.js |
| Backend    | FastAPI |
| Database   | SQLite (via SQLAlchemy) |
| Memory     | Breeth |
| LLM        | Gemini (behind a provider abstraction) |
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
│   │   │   ├── agent_service.py    # get_or_create_agent (single-agent logic)
│   │   │   ├── persona_service.py  # loads persona.json, builds voice-profile prompt
│   │   │   └── llm/
│   │   │       ├── base_provider.py    # LLMProvider ABC (generate/judge/summarize)
│   │   │       └── gemini_provider.py  # GeminiProvider — REST calls via httpx
│   │   ├── schemas/
│   │   │   └── agent.py     # AgentInitResponse
│   │   └── models/          # agents, posts, rejected_topics, sources_cache
│   ├── scripts/
│   │   ├── test_models.py         # standalone DB model verification script
│   │   ├── test_persona.py        # standalone persona/prompt-builder verification script
│   │   └── test_llm_provider.py   # standalone LLMProvider/Gemini verification script
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

## Required Environment Variables

See `backend/.env.example`:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` (defaults to `gemini-2.5-flash`)
- `BREETH_API_KEY`
- `DATABASE_URL`
- `APP_ENV`
- `PORT`

## Development Philosophy

Build only what the PRD requires. No auth, no dashboards, no placeholder
pages, no feature creep. Every stage ships working code, updated docs,
and a suggested git commit — see `docs/prompts/` for the full trail.
