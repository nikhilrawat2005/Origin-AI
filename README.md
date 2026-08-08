# Aether — An Autonomous AI Technology Research Persona

Built for the ABTalks Hackathon. Aether is an autonomous AI persona that,
once initialized, independently discovers AI/tech topics, judges whether
they deserve publishing, writes posts in a consistent editorial voice,
remembers what it has already covered, and keeps publishing over time —
with no further human prompting.

This is **not** a chatbot and **not** a generic content generator.

## Project Status

🚧 **Stage 1 of 20 — Repo + Backend Skeleton**

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
│   │   │   └── config.py    # env-driven settings (single source of truth)
│   │   ├── routes/          # API routes (empty until Stage 4+)
│   │   ├── services/        # business logic (empty until Stage 5+)
│   │   └── models/          # SQLAlchemy models (empty until Stage 2)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # Next.js app (Stage 3+)
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

## Running the Frontend

Not yet implemented — arrives in Stage 3.

## Required Environment Variables

See `backend/.env.example`:

- `GEMINI_API_KEY`
- `BREETH_API_KEY`
- `DATABASE_URL`
- `APP_ENV`
- `PORT`

## Development Philosophy

Build only what the PRD requires. No auth, no dashboards, no placeholder
pages, no feature creep. Every stage ships working code, updated docs,
and a suggested git commit — see `docs/prompts/` for the full trail.
