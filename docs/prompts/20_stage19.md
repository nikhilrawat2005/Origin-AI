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
