# Stage 10 — Breeth Namespace on Init

## Goal
`/init` creates a Breeth namespace, stores it on `Agent.breeth_agent_ref`,
and mirrors the attempt in a local SQLite stub table — per the
20-stage plan and Stage 9's deferred scope.

---

## Prompt(s)

User: "start with stage 10" (after uploading `aether-stage9.zip` and
`PROJECT_STATUS.md`).

---

## AI Response Summary

- **Verified the delivered ZIP first**, rather than trusting the
  uploaded `PROJECT_STATUS.md` at face value: unzipped
  `aether-stage9.zip`, cross-checked its `docs/AI_USAGE_LOG.md`,
  `docs/prompts/`, and `backend/app/services/` contents against the
  20-stage plan. Confirmed Stages 1-9 are genuinely done (matching
  code, tests, and log entries all present) even though the *uploaded*
  `PROJECT_STATUS.md` snapshot was stale (only reflected through Stage
  2) — the ZIP's own in-repo copy of that file was more current
  (through Stage 6) but itself hadn't been updated for Stages 7-9
  either, so it was caught up to Stage 9 as part of this stage's docs
  work before adding the Stage 10 entry.
- Breeth doesn't have an explicit "create namespace" call — namespace
  scoping is implicit via `group_id` on every fact/search call (per
  Stage 9's docs research). So "creating a namespace" means: pick a
  `group_id` for the agent, and write the first fact into it.
  `agent_service._breeth_group_id()` derives it deterministically as
  `f"agent-{agent.id}"` rather than anything Breeth generates.
- `_create_breeth_namespace()` writes one identity fact (persona name
  `is_a` "autonomous AI technology research persona") via Stage 9's
  `BreethClient.write_fact()`, wrapped in the same broad
  try/except-and-log pattern as Stage 8's LLM call — no real
  `BREETH_API_KEY` in this sandbox, and `/init` must still succeed
  without a live Breeth call.
- Key asymmetry vs. the LLM-generated persona description: `breeth_agent_ref`
  is set **regardless** of whether the remote write succeeds, because
  the `group_id` is a locally-derived identifier Aether owns, not
  something Breeth returns — it stays valid and retriable even if
  today's write failed, whereas a failed LLM call genuinely has no
  description to fall back to.
- Added `app/models/breeth_mirror.py` (`BreethMirrorFact`) as the
  "SQLite mirror stub" called for in the stage plan: one row per
  namespace-creation attempt, recording `group_id` /
  `subject`/`predicate`/`object` and a `synced` flag. Scoped narrowly —
  written on this one write path only, not queried by anything besides
  its own verification script yet — so Stage 15's `memory_service` has
  a local fallback table to build read paths against instead of
  introducing it under time pressure then.
- Wired `breethAgentRef` through `AgentInitResponse` and the route.
- `backend/scripts/test_breeth_namespace.py` — new standalone script,
  same in-memory-DB pattern as Stage 8's `test_init_llm_wiring.py`:
  confirms `breeth_agent_ref` is set and matches the deterministic
  group_id, confirms exactly one `BreethMirrorFact` row exists with
  `synced=False` (expected here, no real key), confirms a repeat
  `get_or_create_agent()` call doesn't create a duplicate mirror row.
- Ran a full server-boot smoke test via FastAPI's `TestClient` (using
  the `with TestClient(app) as c:` form so the startup event actually
  fires `init_db()`) — called `/api/agent/init` twice, confirmed
  `breethAgentRef` present and identical to `f"agent-{agentId}"` on
  both calls.
- Re-ran all prior verification scripts (Stages 2, 5, 6, 7, 8, 9).
  `scripts/test_models.py` failed on its exact-table-set assertion
  (`{"agents", "posts", "rejected_topics", "sources_cache"}`), since
  the new `breeth_mirror_facts` table is a real, intended schema
  change this stage — updated the assertion to include it and
  re-verified, rather than leaving a stale check in place.

## Decisions Taken

- **Accepted:** `group_id = f"agent-{agent.id}"` as the namespace
  identity, computed locally rather than requested from Breeth — no
  Breeth endpoint returns or reserves a namespace/group id, so there's
  nothing to request; the deterministic local id is both simpler and
  collision-free per agent.
- **Accepted:** `breeth_agent_ref` set unconditionally on creation
  (unlike `persona_description`, which stays `None` on LLM failure) —
  justified above; flagged explicitly in both the code docstring and
  this log so it isn't misread later as an inconsistency with Stage
  8's pattern.
- **Accepted:** `BreethMirrorFact` as a new table now, even though nothing outside
  this write path and its own test reads it yet — it's explicitly
  named in the stage plan ("SQLite mirror stub") and Stage 15 will
  need somewhere to build a fallback query against; better to land the
  schema now under this stage's docs/testing discipline than add it
  ad hoc later.
- **Accepted:** updating Stage 2's `test_models.py` in this stage
  rather than treating the regression as out of scope — Rule 13
  requires "confirmation the code actually runs," and a stale
  assertion failing on legitimate schema growth isn't a passing test
  suite.
- **Accepted:** catching up the in-repo `PROJECT_STATUS.md` from Stage
  6 to Stage 9 before appending the Stage 10 entry, since it's the
  designated resume document and Rule 13 requires it stay current —
  leaving it 3 stages stale would break the "paste this doc into a new
  chat" resume flow the doc itself promises.
- **Deferred:** no read/query path against `BreethMirrorFact` yet —
  that's Stage 15's job (`memory_service.py`, Breeth + SQLite mirror
  query before accept).
- **Deferred:** no retry/backoff on the namespace write — same
  reasoning as Stages 6/7/9, deferred to Stage 18's scheduler.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/models/breeth_mirror.py`
- `backend/scripts/test_breeth_namespace.py`
- `docs/prompts/11_stage10.md`

## Files Modified
- `backend/app/models/__init__.py` — registered `BreethMirrorFact`.
- `backend/app/services/agent_service.py` — added
  `_breeth_group_id()`, `_create_breeth_namespace()`; wired into
  `get_or_create_agent()`.
- `backend/app/schemas/agent.py` — `AgentInitResponse.breethAgentRef`.
- `backend/app/routes/agent.py` — passes `breethAgentRef` through.
- `backend/scripts/test_models.py` — updated table-set assertion.
- `PROJECT_STATUS.md` — caught up Stages 7-9 (previously missing) and
  added the Stage 10 entry; bumped resume pointer to Stage 11 /
  `aether-stage10.zip`.
- `docs/AI_USAGE_LOG.md` — Stage 10 entry appended.

## Git Commit
```
feat(backend): create per-agent Breeth namespace on init with local mirror
```

## Stage Outcome
`python3 scripts/test_breeth_namespace.py` (run from `backend/`, venv
active) passes all three checks. Re-ran `test_models.py` (after fixing
its table-set assertion), `test_persona.py`, `test_llm_provider.py`,
`test_llm_factory.py`, `test_init_llm_wiring.py`, and
`test_breeth_client.py` — all pass, no other regressions. Full
FastAPI `TestClient` smoke test confirms the actual HTTP path: server
boots, `/api/health` returns 200, `POST /api/agent/init` called twice
returns the same `agentId` and a `breethAgentRef` of
`f"agent-{agentId}"` on both calls, with no duplicate `BreethMirrorFact`
row created on the second call. No live Breeth write was exercised
(no real `BREETH_API_KEY` in this sandbox, per Known Constraints) —
the graceful-fallback path (`synced=False`, `breeth_agent_ref` still
set) is what's actually been verified, same caveat as Stage 9.

## Next Stage
Stage 11 — Topic Sources Config + Fetcher: `topic_sources.json`
(source list/config) + `topic_discovery.py` (fetches raw topic
candidates from those sources), no caching/dedup yet — that's Stage
12's `sources_cache` wiring.
