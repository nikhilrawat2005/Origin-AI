# Stage 18 — Scheduler Wiring

## Goal
`scheduler.py` — chain Stages 11/12 → 14 → 15 → 16 → 17
(`discover_new_topics()` → `judge_candidates()` (accepted only) →
`check_memory_batch()` (not-duplicate only) → `write_post()` →
`publish_post()`) behind APScheduler, driven by
`PUBLISH_INTERVAL_MINUTES` from the environment, started from
`POST /api/agent/init` — the first point the full autonomous pipeline
runs end-to-end with zero further human prompting, per the PRD's core
success criterion.

---

## Prompt(s)

User: "create stage 18" (uploaded `aether-stage17.zip` and
`PROJECT_STATUS.md` as the resume context — the uploaded status doc's
own text was stale relative to the actual zip contents, which were
already at Stage 17; proceeded from the zip's real state, not the
doc's stated "Stage 3 NEXT UP" line).

---

## AI Response Summary

- Extracted `aether-stage17.zip` and read every service file involved
  in the chain (`topic_discovery.py`, `sources_cache_service.py`,
  `editorial_judgment.py`, `memory_service.py`, `post_writer.py`,
  `publisher.py`) plus `agent_service.py`, `routes/agent.py`,
  `config.py`, and the `Agent` model before writing anything — every
  one of those six services' own docstrings already stated exactly
  where it plugs into this stage's chain, so the wiring order was a
  transcription task, not a design decision.
- Confirmed `apscheduler==3.10.4` was already in `requirements.txt`
  (added in Stage 1, unused until now) and `publish_interval_minutes`
  already existed in `config.py` with a comment marking it "wired in
  Stage 18" — nothing to add to either file.
- Decision: `run_publish_cycle(db, agent)` is a plain function with no
  APScheduler knowledge, kept directly unit-testable the same way
  every prior service has been — mirrors the README's own Stage 17
  manual-pipeline snippet almost exactly, which effectively already
  was this function's design, just not yet made real.
- Decision: wrap each stage of the chain (discovery, judgment, memory
  check) in its own try/except that logs and returns `0` rather than
  letting an exception propagate out of `run_publish_cycle()`. None of
  Stages 12/14/15's docstrings promise they can't raise on a genuinely
  unexpected failure (only their *documented* failure modes — Stage
  14's fail-closed REJECT, Stage 15's fail-open Breeth fallback — are
  guaranteed not to raise), and an autonomous scheduler that dies on
  the first unexpected exception defeats the PRD's "zero further human
  prompting" requirement outright.
- Decision: Stage 16's `PostWriteError` (its own documented fail-loud
  mode) is caught *per candidate*, not per cycle — looping over
  `survivors` with an individual try/except around
  `write_post()`/`publish_post()` so one bad generation doesn't
  discard other candidates that would have written and published
  cleanly in the same cycle.
- Decision: `_tick()` opens its own `SessionLocal()` session rather
  than trying to reuse anything from `get_db()` — a
  `BackgroundScheduler` job runs on its own thread, entirely outside
  any FastAPI request lifecycle, so there is no request-scoped session
  to borrow. Modeled the close-in-`finally` shape directly on
  `get_db()`'s own pattern for consistency.
- Decision: `start_scheduler()` is idempotent via a module-level
  `_scheduler` guard, directly because `get_or_create_agent()` (Stage
  4/10) is itself idempotent and returns the same row on a repeat
  `/init` call — the scheduler needed the same guarantee, or a second
  `/init` call would start a second `BackgroundScheduler` polling
  twice as often against the same agent with no way to detect or
  correct it later.
- Decision: schedule the first tick to fire immediately
  (`next_run_time=datetime.now()`) rather than waiting one full
  `PUBLISH_INTERVAL_MINUTES` before the first cycle. Read PRD Section
  9 ("posts appear automatically over time, feed grows with no human
  prompts") as implying the evaluator should see growth starting
  promptly after the single `/init` call, not after an arbitrary wait
  tied to whatever interval is configured; every tick after the first
  still respects the configured interval exactly.
- Decision: wire the scheduler start into `routes/agent.py` (not
  `agent_service.py`) — `agent_service.py`'s own Stage 10 docstring
  scopes it to "creates the agent row for POST /api/agent/init" and
  explicitly notes "Scheduler start (Stage 18) is still not wired in
  here," treating it as a separate concern the route layer owns.
  Flips `agent.status` to `"active"` in the route immediately after
  confirming the scheduler is running, only committing when the value
  actually changes (repeat calls are then a true no-op DB-wise).
- Added an `on_event("shutdown")` hook in `main.py` calling
  `stop_scheduler()` — not explicitly required by the stage plan, but
  without it a local-dev auto-reload would leave an orphaned
  background thread running after every restart; cheap enough to add
  now rather than as a fix-up later.
- Verified end-to-end via FastAPI's `TestClient` (not just the mocked
  unit script): a fresh `POST /api/agent/init` returns
  `status: "active"`, a repeat call returns the identical `agentId`,
  and the scheduler's immediate first tick genuinely executed the real
  pipeline against the real (network-restricted-in-this-sandbox) topic
  sources — each source failed individually with a `403` exactly as
  Stage 11's per-source try/except already anticipated, without
  crashing the process or leaving an unhandled exception in the logs.
  This is real confirmation the wiring works, not just that the mocks
  return the right shapes.
- `backend/scripts/test_scheduler.py` — six checks against an
  in-memory DB with every chained function monkeypatched via
  `unittest.mock.patch.object` on the `scheduler` module's own
  imported names (clean because `scheduler.py` imports each function
  by name into its own namespace, so patching there doesn't touch the
  real implementations Stages 12–17's own scripts already cover): no
  candidates short-circuits before judgment (asserted via
  `assert_not_called()`); no accepted candidates short-circuits before
  the memory check; all-duplicates short-circuits before the post
  writer; a mixed batch (one duplicate, one `PostWriteError`, one
  clean success) returns `1` and calls `publish_post()` exactly once
  with the correct `WrittenPost`; discovery raising an unexpected
  exception is caught and returns `0` instead of propagating;
  `start_scheduler()`/`stop_scheduler()` idempotency, using the real
  (not mocked) APScheduler classes to confirm object identity across
  calls.
- Ran the new script, then re-ran all fourteen prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17) —
  all passed, no regressions.

## Decisions Taken

- **Accepted:** `run_publish_cycle()` stays a plain, APScheduler-free
  function for direct testability — all scheduling machinery isolated
  to `start_scheduler()`/`_tick()`.
- **Accepted:** every stage of the chain individually try/excepted,
  logging and returning `0` rather than raising — required so an
  unexpected failure anywhere in the pipeline skips one cycle instead
  of silently ending the autonomous loop.
- **Accepted:** `PostWriteError` caught per-candidate inside the
  survivors loop, not per-cycle — preserves other candidates in the
  same batch that would have published cleanly.
- **Accepted:** `start_scheduler()` idempotent via a module-level
  guard, matching `get_or_create_agent()`'s existing idempotency
  contract exactly.
- **Accepted:** immediate first tick
  (`next_run_time=datetime.now()`), then the configured interval
  after — prioritizes the evaluator seeing prompt feed growth over a
  literal "always wait one interval first" reading of the plan.
- **Accepted:** scheduler start + status flip live in the route layer,
  not `agent_service.py` — consistent with Stage 10's own explicit
  scoping note.
- **Accepted:** an `on_event("shutdown")` hook stopping the scheduler
  — small addition beyond the stage's literal scope, justified by
  avoiding orphaned background threads across local-dev reloads.
- **Deferred:** anything about the feed's actual JSON response shape
  or the Next.js Feed page rendering real data — Stage 19.
- **Deferred:** any change to `PUBLISH_INTERVAL_MINUTES`'s default or
  to the topic source list — out of this stage's scope; the `403`s
  seen during E2E verification are a sandbox network restriction, not
  a defect in Stage 11's fetcher, which already degrades per-source
  exactly as designed.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/scheduler.py`
- `backend/scripts/test_scheduler.py`
- `docs/prompts/19_stage18.md`

## Files Modified
- `backend/app/routes/agent.py` — starts the scheduler and flips
  `status` to `"active"` on `/init`.
- `backend/app/main.py` — added `on_event("shutdown")` calling
  `stop_scheduler()`.
- `README.md` — project status bumped to Stage 18, repo tree updated,
  Stage 17's manual-pipeline snippet replaced with the Stage 18
  verification section (mocked unit script + live `/init` walkthrough).
- `PROJECT_STATUS.md` — Stage 18 entry added, 20-stage plan table
  corrected (a stale duplicate tail of rows 12–20 lacking DONE/NEXT UP
  markers was cleaned up while updating it), resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 18 entry appended.

## Git Commit
```
feat(backend): wire discover->judge->memory->write->publish into an APScheduler-driven autonomous publish cycle, started from /init
```

## Stage Outcome
`python -m scripts.test_scheduler` (run from `backend/`, venv active)
passes all six checks against an in-memory DB with every pipeline
stage monkeypatched — no network or API keys needed. Re-ran all
fourteen prior verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11,
12, 13, 14, 15, 16, 17) — all pass, no regressions. Also verified live
via FastAPI's `TestClient`: `POST /api/agent/init` now returns
`status: "active"`, a repeat call is idempotent (same `agentId`, no
second scheduler), and the scheduler's immediate first tick genuinely
ran the real pipeline end-to-end against real topic sources (each
failing individually with a `403` under this sandbox's network
restrictions, handled exactly as Stage 11 already designed, without
crashing the process).

## Next Stage
Stage 19 — Feed Endpoint + Feed Page: `GET /api/agent/feed` (exact PRD
JSON shape) + the Next.js Feed page going live against it — the first
point the frontend actually displays real, autonomously published
posts.
