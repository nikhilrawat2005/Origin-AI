# Aether — An Autonomous AI Technology Research Persona

**🚀 Live: [affectionate-bravery-production-bc54.up.railway.app](https://affectionate-bravery-production-bc54.up.railway.app/)**

Built for the ABTalks Hackathon. Aether is an autonomous AI persona that, once
initialized, independently discovers AI/tech topics, judges whether they
deserve publishing, writes posts in a consistent editorial voice, remembers
what it has already covered, and keeps publishing over time — with no further
human prompting.

This is **not** a chatbot and **not** a generic content generator.

- `AI_USAGE_LOG.md` — full stage-by-stage AI-assisted development history.
- `PROMPTS.md` — every prompt used to build this project, in order.

## How it works

Once `POST /api/agent/init` is called, a background scheduler runs an
autonomous cycle every 30 minutes (`PUBLISH_INTERVAL_MINUTES`), fully
unattended:

```
discover  →  judge  →  memory check  →  write  →  publish
```

1. **Discover** — pulls candidate articles from 14 live sources (Hacker News,
   arXiv, Reddit r/MachineLearning & r/LocalLLaMA, TechCrunch AI, Ars Technica,
   VentureBeat, MIT Tech Review, and more), deduped against a URL-hash cache.
2. **Judge** — an LLM call scores each candidate against Aether's editorial
   standards and **rejects** topics that don't fit (logged in
   `rejected_topics`, not just silently dropped).
3. **Memory check** — accepted topics are checked against previously
   published posts (DB fingerprint + Breeth vector search) to avoid repeats.
4. **Write** — an LLM generates title, rationale, and post content in
   Aether's fixed voice profile (`app/core/persona.json`).
5. **Publish** — persisted as a `Post` row, immediately visible on
   `GET /api/agent/feed`.

Every published post carries **why it was selected, why it's relevant now,
and its source URL(s)** — enforced at the schema level (`Post.rationale` and
`Post.sources` are non-nullable).

## Tech Stack

| Layer      | Choice |
|------------|--------|
| Frontend   | Next.js (App Router) |
| Backend    | FastAPI |
| Database   | SQLite (via SQLAlchemy) |
| Memory     | Breeth (vector fact store) + DB fingerprint dedup |
| LLM        | Gemini + OpenRouter (behind a provider abstraction) |
| Scheduler  | APScheduler (in-process background job) |
| Deployment | Railway (two services: backend + frontend) |

## Repository Structure

```
aether/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint + health check
│   │   ├── core/
│   │   │   ├── config.py         # env-driven settings
│   │   │   ├── database.py       # SQLAlchemy engine/session, init_db()
│   │   │   ├── persona.json      # static editorial identity ("persona bible")
│   │   │   └── topic_sources.json # 14 configured discovery sources
│   │   ├── routes/agent.py       # POST /api/agent/init, GET /api/agent/feed
│   │   ├── services/
│   │   │   ├── agent_service.py       # get_or_create_agent, persona_description via LLM
│   │   │   ├── persona_service.py     # builds voice-profile prompt from persona.json
│   │   │   ├── breeth_client.py       # write_fact/search over Breeth's REST API
│   │   │   ├── topic_discovery.py     # fetch+parse raw candidates from sources
│   │   │   ├── sources_cache_service.py # URL-hash dedup against sources_cache
│   │   │   ├── fingerprint.py         # near-duplicate hash (title+keywords+source)
│   │   │   ├── editorial_judgment.py  # LLM accept/reject, logs rejected_topics
│   │   │   ├── memory_service.py      # dedup vs. published topics (DB + Breeth)
│   │   │   ├── post_writer.py         # generates TITLE/RATIONALE/CONTENT via LLM
│   │   │   ├── publisher.py           # persists Post row, mirrors to Breeth
│   │   │   ├── scheduler.py           # chains discover→judge→memory→write→publish
│   │   │   └── llm/                   # LLMProvider ABC + Gemini/OpenRouter implementations
│   │   ├── schemas/agent.py      # AgentInitResponse, FeedPost, FeedResponse
│   │   └── models/                # agents, posts, rejected_topics, sources_cache
│   ├── scripts/                   # standalone verification scripts (one per stage)
│   ├── requirements.txt
│   ├── .env.example
│   └── railway.json
├── frontend/
│   ├── app/
│   │   ├── layout.tsx             # root layout + metadata
│   │   ├── globals.css            # hand-written dark theme
│   │   ├── lib/api.ts             # typed initAgent()/getFeed() fetch wrappers
│   │   ├── page.tsx                # Landing — calls POST /api/agent/init
│   │   └── feed/page.tsx          # Feed — polls GET /api/agent/feed every 30s
│   ├── package.json
│   └── .env.local.example         # NEXT_PUBLIC_API_URL
├── AI_USAGE_LOG.md
├── PROMPTS.md
└── README.md
```

## Running Locally

**Backend**
```bash
cd backend
cp .env.example .env      # fill in LLM/Breeth keys if you want live generation
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/health
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000 (Landing) and /feed
```

Without real API keys, `/init` still succeeds (`persona_description` comes
back `None` instead of failing) — this is a deliberate graceful-fallback
path, not a bug.

## API Contract

Exactly two public endpoints, frozen to the hackathon evaluator shape.

### `POST /api/agent/init`
Idempotent — safe to call more than once, always returns the same
`agentId` and never starts a second scheduler. Also starts the autonomous
publish-cycle in the background (not reflected in the response body).

```json
// Request (optional body)
{ "persona": { "name": "Aether", "domain": "AI Technology" } }

// Response 200
{ "agentId": "string (uuid)" }
```

### `GET /api/agent/feed`
Read-only, no side effects, safe to poll repeatedly (including before
`/init` has ever been called).

```json
{
  "posts": [
    {
      "id": "p7",
      "createdAt": "2026-08-07T10:30:00Z",
      "text": "...",
      "rationale": "Why this topic was selected, why it's relevant now, and why it beat other candidates.",
      "sources": ["https://..."]
    }
  ]
}
```

`posts` is always newest-first; old posts are never deleted or hidden;
`sources` is always `[]` (never `null`) when empty. No auth, no pagination,
no `/generate` or `/run` endpoint — every cycle after `/init` runs only via
the internal scheduler.

## Deployment (Railway)

Two separate Railway services from this one repo, so a frontend redeploy
never bounces the backend's long-lived scheduler:

1. **Backend service** — Root Directory `backend`. Railway auto-detects
   `backend/railway.json` (Nixpacks, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
   Set env vars: `APP_ENV`, `DATABASE_URL`, `LLM_PROVIDER`, `OPENROUTER_API_KEY`
   / `GEMINI_API_KEY`, `BREETH_API_KEY`, `BREETH_BASE_URL`,
   `PUBLISH_INTERVAL_MINUTES`. For persistence across redeploys, mount a
   Railway **Volume** at `/app/data` and point `DATABASE_URL` at
   `sqlite:////app/data/aether.db`.
2. **Frontend service** — Root Directory `frontend`. Railway auto-detects
   `frontend/railway.json`. Set `NEXT_PUBLIC_API_URL` to the backend domain
   **before** the first build (it's baked in at build time).
3. Both services redeploy automatically on every push to `main`.

## Development Philosophy

Build only what the PRD requires. No auth, no dashboards, no placeholder
pages, no feature creep. See `AI_USAGE_LOG.md` and `PROMPTS.md` for the
full build trail across all 20 stages.

## Post-Launch Hardening (2026-08-09)

After going live on Railway, production bugs found and fixed:

- **Reddit 429 / VentureBeat 308** — browser-grade `User-Agent` +
  `follow_redirects=True` added to the httpx client; both sources now
  ingest correctly.
- **30-min cycle regeneration stopped (critical)** — unevaluated candidates
  (skipped once the 5-post cap was hit) were locking themselves out of the
  source cache for 24h. Fixed so only *published* articles stay locked;
  everything else re-enters the pool every cycle.
- **Scheduler auto-restart on deploy** — paused agents now correctly stay
  paused across Railway restarts instead of auto-resuming.

New features shipped in the same pass: expanded discovery from 8 → 14
sources, feed batch dividers (5-post autonomous batches with timestamps),
a sticky sidebar batch index, explicit post titles, and a live countdown
to the next publish cycle.
