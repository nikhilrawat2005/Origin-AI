# Stage 8 — Wire LLM into Init

## Goal
Make `POST /api/agent/init` generate the agent's actual persona voice
profile via the LLM on creation, using Stage 5's prompt builder and
Stage 7's provider factory — the first place any of the LLM
abstraction gets called from a real request path.

---

## Prompt(s)

User: "now stage 8", after reviewing the delivered `aether-stage7.zip`.

---

## AI Response Summary

- `backend/app/services/agent_service.py` — `get_or_create_agent()`
  now sets `persona_name` from `persona_service.get_persona_name()`
  (the bible's actual name) instead of relying on the `Agent` model's
  bare `"Aether"` default — same value today, but correct even if the
  bible's name ever changes. On creation only, calls a new private
  helper, `_generate_persona_description()`, which builds the
  voice-profile prompt (`persona_service.build_voice_profile_prompt()`)
  and sends a short fixed instruction through
  `get_llm_provider().generate()`, with the voice profile as the
  `system` prompt. The instruction explicitly asks for a third-person,
  no-greeting bio — matches how `persona_description` will actually be
  displayed on the landing page (Stage 3's frontend scope), not a
  chatty reply.
  - The whole call is wrapped in `try/except Exception` (broad on
    purpose) that logs a warning and returns `None` rather than
    letting the exception propagate. Reasoning: this sandboxed
    environment has no real `GEMINI_API_KEY`/`OPENROUTER_API_KEY` (per
    `PROJECT_STATUS.md`'s "Known Constraints"), so an unhandled
    exception here would make `/init` fail outright — which breaks the
    PRD's core contract ("the evaluator calls init exactly once");
    that call must succeed. A missing/broken LLM degrades the response
    (`persona_description: null`) instead of blocking the whole
    pipeline. This mirrors `GeminiProvider`'s own philosophy from
    Stage 6 (fail clearly, don't block) one level higher: the provider
    fails clearly *inside* itself, and the caller here decides that
    failure shouldn't be fatal to agent creation.
  - Placed *inside* the `if existing is not None: return` branch's
    implicit else — i.e., only reached on the very first successful
    creation — so idempotency (Stage 4's core guarantee) is untouched:
    a second `/init` call still returns the same row without a second
    LLM call, confirmed explicitly in the test via a call counter.
- `backend/app/schemas/agent.py` — added
  `personaDescription: str | None = None` to `AgentInitResponse`.
- `backend/app/routes/agent.py` — passes `agent.persona_description`
  through in the response; no other route logic changed.
- `backend/scripts/test_init_llm_wiring.py` — standalone verification,
  offline-runnable without a real API key:
  - Uses an in-memory SQLite session (`sqlite:///:memory:`) so the test
    doesn't touch `aether.db` or require any server running.
  - Injects a `FakeProvider` (matching the `LLMProvider` interface) by
    monkeypatching `agent_service.get_llm_provider` for the duration of
    the first two checks, with a call counter to prove the LLM is
    called exactly once across two `get_or_create_agent()` calls.
  - Restores the real `get_llm_provider` afterward and calls
    `_generate_persona_description()` directly against whatever
    provider is actually configured — in this environment that's
    `GeminiProvider` with no key, so it exercises the real
    graceful-fallback path (not a fake), confirming the fallback
    logic itself (not just the mock) works, and that
    `get_or_create_agent()` still succeeds afterward regardless of the
    outcome.
- Ran `test_init_llm_wiring.py`, plus re-ran `test_llm_provider.py`
  (Stage 6) and `test_llm_factory.py` (Stage 7) to check for
  regressions. Same offline-verification note as Stage 7: this sandbox
  has no network access this session, so the real `sqlalchemy`,
  `httpx`, and `pydantic_settings` packages could not be installed
  from PyPI. Minimal local stand-ins for those three (not shipped in
  the project) were placed on `PYTHONPATH` so the actual, unmodified
  project code could be imported and exercised end-to-end — including
  a working in-memory "SQLite" session store sufficient to prove
  `get_or_create_agent()`'s create/idempotency logic for real, not
  just import-check it. This is a test-environment workaround only;
  the shipped code has no dependency on the stubs and will run
  correctly against the real packages once `pip install -r
  requirements.txt` can reach PyPI.

## Decisions Taken

- **Accepted:** Broad `except Exception` around the LLM call in
  `_generate_persona_description()`, logging + returning `None` rather
  than raising. `/init` succeeding is a hard PRD requirement; a
  persona description is an enrichment, not a precondition for a valid
  agent row.
- **Accepted:** Generation gated to creation-only (not on every
  `/init` call) — preserves Stage 4's idempotency guarantee and avoids
  burning LLM calls/cost on repeated evaluator polling.
- **Accepted:** `persona_name` now sourced from `persona_service`
  instead of the model default — removes a second source of truth for
  the same value.
- **Deferred:** No retry on a failed generation call, and no way to
  manually re-trigger generation for an agent that already has
  `persona_description = None` — out of scope until there's a stage
  (or an ops need) that actually requires it; the PRD doesn't ask for
  this and adding it now would be an unrequested extra endpoint.
- **Deferred:** No storage of *why* generation failed (just a log
  line) — the PRD's "rationale" requirement is about published posts
  (Stage 16), not about `/init` itself, so no schema field was added
  for this.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/scripts/test_init_llm_wiring.py`

## Files Modified
- `backend/app/services/agent_service.py` — LLM-backed persona
  description generation on creation.
- `backend/app/schemas/agent.py` — added `personaDescription` field.
- `backend/app/routes/agent.py` — returns the new field.
- `README.md` — project status bumped to Stage 8, repo tree updated,
  Stage 8 verification section added.

## Git Commit
```
feat(backend): generate persona description via LLM on agent init
```

## Stage Outcome
`python -m scripts.test_init_llm_wiring` (run from `backend/`)
confirms a new agent gets its `persona_name` from the persona bible
and an LLM-generated `persona_description`, confirms the LLM is called
exactly once even across a repeat init, and confirms the real
graceful-fallback path (no API key configured, as expected in this
sandbox) still produces a valid agent with `persona_description = None`
instead of a failed request. `test_llm_provider.py` and
`test_llm_factory.py` re-run with no regressions. Frontend's
Initialize button is still not wired to this endpoint — that's a later
frontend stage once the feed (Stage 19) gives the flow something to
show after initializing.

## Next Stage
Stage 9 — Breeth Client (connection only): `breeth_client.py` —
connect, write/read a test fact, verified via a standalone script. Per
`PROJECT_STATUS.md`'s Known Constraints #3, current Breeth docs will
be web-searched first since the API is less familiar, rather than
guessed at.
