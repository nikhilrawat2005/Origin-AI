# Stage 4 — `POST /api/agent/init` (basic)

## Goal
Wire the first real backend route: creates an `agent` row in SQLite and
returns `agentId`. No persona/LLM logic yet — that starts Stage 5.

---

## Prompt(s)

User: "start work on stage 4" (approval to proceed to Stage 4 after
reviewing the uploaded `aether-stage3.zip` and `PROJECT_STATUS.md`).

---

## AI Response Summary

- `backend/app/services/agent_service.py` — `get_or_create_agent(db)`:
  queries for the most recently created `Agent` row; returns it if
  present, otherwise creates one and commits. This is the one
  substantive design decision this stage — see below.
- `backend/app/routes/agent.py` — `POST /api/agent/init`, depends on
  `get_db`, calls the service, returns an `AgentInitResponse`.
- `backend/app/schemas/agent.py` — `AgentInitResponse` (agentId, status,
  personaName, createdAt). Built manually in the route rather than via
  `from_attributes` because the API field names (`agentId`,
  `personaName`) intentionally differ from the ORM column names
  (`id`, `persona_name`) and auto-mapping would silently break if
  either side's naming drifted.
- `backend/app/main.py` — added a `startup` event calling `init_db()`
  (idempotent — `create_all()` no-ops on existing tables) and
  `app.include_router(agent_routes.router)`. Added `import app.models`
  so all four models are registered on `Base.metadata` before
  `init_db()` runs (previously only exercised via the standalone
  Stage 2 test script, which imports models directly).
- Verified live: started uvicorn, called `/api/agent/init` twice,
  confirmed both responses return the identical `agentId`, then
  queried `agents` via `sqlite3` directly and confirmed exactly one
  row exists. Deleted the throwaway `aether.db` before packaging.

## Decisions Taken

- **Accepted:** Idempotent `/init` — instead of erroring or blindly
  inserting a new row on repeat calls, return the existing agent
  unchanged. The PRD says the evaluator calls init "exactly once," but
  a hackathon demo/dev loop will hit it more than once; idempotency
  satisfies both without adding an error path the PRD never asked for.
  This was already flagged as the intended design in the Stage 2
  `Agent` model docstring, so Stage 4 just implements it.
- **Accepted:** Manual field-by-field construction of
  `AgentInitResponse` over `model_validate(agent)` with
  `from_attributes=True` + aliases — fewer moving parts to get wrong
  for a 4-field response, and it stays correct even if the ORM and API
  field names diverge further later.
- **Deferred:** No `DELETE`/reset endpoint for agents, even though it'd
  help local testing — out of scope per PRD section 5 ("no other public
  APIs unless absolutely necessary"). Devs can just delete `aether.db`.
- **Deferred:** Response still returns model defaults for persona name
  — real persona generation is explicitly Stage 5 (persona.json +
  prompt builder) and Stage 8 (LLM-wired). Not pulled forward.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/routes/agent.py`
- `backend/app/services/agent_service.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/agent.py`

## Files Modified
- `backend/app/main.py` — startup hook (`init_db()`), router include,
  model registration import.
- `README.md` — project status bumped to Stage 4, repo tree updated,
  Stage 4 verification section added.

## Git Commit
```
feat(backend): add POST /api/agent/init with idempotent agent creation
```

## Stage Outcome
Backend boots with `uvicorn app.main:app --reload --port 8000`, tables
are created automatically on startup, and `curl -X POST
http://localhost:8000/api/agent/init` returns a valid
`agentId`/`status`/`personaName`/`createdAt` payload. Calling it a
second time returns the same `agentId` — confirmed via direct
`sqlite3` query showing exactly one row in `agents` after two calls.

## Next Stage
Stage 5 — Persona Bible + Prompt Builder: `persona.json` +
`persona_service.py` build a voice profile (no LLM call yet — that's
Stage 6/8).
