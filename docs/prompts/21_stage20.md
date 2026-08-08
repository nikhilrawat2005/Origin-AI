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
