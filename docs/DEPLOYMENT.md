# Deploying Aether on Railway

Aether deploys as **two separate Railway services** from this one
repo — a backend (FastAPI) service and a frontend (Next.js) service —
each pointed at a different root directory. This matches the locked
tech stack (§3 of `PROJECT_STATUS.md`: "Deployment | Railway") and
keeps the two halves independently restartable/scalable, which matters
here specifically because the backend runs a long-lived
`BackgroundScheduler` — you don't want a frontend redeploy to bounce
that process.

Claude works in a sandboxed container and cannot run `railway up` or
push to a real Railway project on your behalf (see
`PROJECT_STATUS.md` §12, "Known Constraints"). Everything below is
exact, copy-pasteable steps for you to run.

## 1. Push this repo to GitHub

Railway deploys from a GitHub repo. If you haven't already:

```bash
cd aether
git init
git add .
git commit -m "chore: initial commit through Stage 20 (release candidate)"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## 2. Create the backend service

1. In the Railway dashboard: **New Project → Deploy from GitHub repo**
   → select this repo.
2. On the new service, go to **Settings → Source** and set
   **Root Directory** to `backend`.
3. Railway auto-detects `backend/railway.json` (Nixpacks builder,
   `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`) —
   no manual build/start command entry needed.
4. Go to **Variables** and add:
   ```
   APP_ENV=production
   DATABASE_URL=sqlite:///./aether.db
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=<your real key>
   OPENROUTER_MODEL=openai/gpt-4o-mini
   GEMINI_API_KEY=<optional, only if LLM_PROVIDER=gemini>
   GEMINI_MODEL=gemini-2.5-flash
   BREETH_API_KEY=<your real key>
   BREETH_BASE_URL=https://api.thebreeth.com
   PUBLISH_INTERVAL_MINUTES=30
   ```
   (`PORT` is injected by Railway automatically — don't set it
   yourself.)
5. Deploy. Once live, note the generated domain, e.g.
   `https://aether-backend-production.up.railway.app`.
6. Confirm it's up:
   ```bash
   curl https://<backend-domain>/api/health
   # {"status":"ok","app":"aether-backend","env":"production"}
   ```

   > **SQLite Persistence on Railway note:** By default, SQLite writes to the container's ephemeral disk. To persist data across Railway redeploys without switching to Postgres:
   > 1. In Railway backend service settings, add a **Volume** mounted at `/app/data`.
   > 2. Update `DATABASE_URL` environment variable to `sqlite:////app/data/aether.db`.
   > 3. This ensures agent status, posts, and candidate cache survive process restarts and redeployments seamlessly.

## 3. Create the frontend service

1. In the same Railway project: **New → GitHub Repo** → same repo
   again (a second service).
2. **Settings → Source → Root Directory** → `frontend`.
3. Railway auto-detects `frontend/railway.json`
   (`npm install && npm run build`, then
   `npm run start -- -p $PORT`).
4. **Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://<backend-domain-from-step-2>
   ```
   `NEXT_PUBLIC_*` vars are baked in at build time in Next.js, so set
   this **before** the first deploy/build — changing it later requires
   a rebuild, not just a restart.
5. Deploy. Railway gives you a second domain, e.g.
   `https://aether-frontend-production.up.railway.app` — this is the
   URL you hand to the evaluator.

## 4. Verify the full deployed flow

```bash
# Evaluator's exact flow:
curl -X POST https://<backend-domain>/api/agent/init
curl https://<backend-domain>/api/agent/feed
# ...repeat the feed call over time; it should grow on its own.
```

Then open `https://<frontend-domain>` in a browser: click
**Initialize Agent** on the Landing page, then watch the Feed page —
it polls every 30 seconds and should show new posts appearing with no
further clicks, per the PRD's core success criterion (§9).

## 5. Redeploying after a code change

Railway redeploys automatically on every push to `main` for both
services (default GitHub-trigger behavior) — no extra steps needed
beyond `git push`. Remember the SQLite caveat above: a backend
redeploy resets the agent/posts, so re-run `POST /api/agent/init`
afterward.
