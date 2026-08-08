# Stage 9 — Breeth Client (connection only)

## Goal
Add `breeth_client.py` — connect, write a test fact, read it back —
verified via a standalone script. Per `PROJECT_STATUS.md`'s Known
Constraint #3, web-search current Breeth docs first since the API is
unfamiliar, rather than guessing.

---

## Prompt(s)

User: "start", after reviewing the delivered `aether-stage8.zip`
(shorthand for "start the next stage," consistent with prior "now
stage N" approvals).

---

## AI Response Summary

- **Research first.** Searched the web for Breeth, landed on
  `thebreeth.com` (confirmed as the correct project — matches the
  `BREETH_API_KEY` env var name in `PROJECT_STATUS.md` and the
  "Memory: Breeth" line in the tech stack table), then fetched
  `docs.thebreeth.com` directly. Read the REST API overview page (base
  URL, auth, scopes, error envelope) and the three most relevant
  endpoint pages: `POST /v1/episodes`, `POST /v1/facts`, and
  `POST /v1/search`. Confirmed current, real API shapes rather than
  inferring from the marketing homepage's short MCP snippet.
- `backend/app/services/breeth_client.py` — `BreethClient`.
  - `write_fact()` → `POST /v1/facts`. Chose this over
    `POST /v1/episodes` for the stage's write-side test specifically
    because the docs describe it as "a fast write path" for
    already-structured S-P-O data with "minimal-overhead ingest,"
    versus episodes' heavier prose-extraction pipeline meant for
    natural-language content — a better fit for "prove the connection
    and credentials work" than for testing extraction quality. (Later
    stages that actually store post content/topics will decide between
    facts and episodes based on what's being written, not on this
    stage's precedent.)
  - `search()` → `POST /v1/search`, used as the read side of the
    connection test — write, then search for what was written.
  - `BreethConfigError` (missing key) and `BreethAPIError` (non-2xx,
    carrying the parsed `slug`/`message` from Breeth's JSON error
    envelope) — same pattern as `GeminiConfigError`/
    `OpenRouterConfigError` from Stages 6/7, so a bad `BREETH_API_KEY`
    fails exactly as clearly as a bad Gemini/OpenRouter key does.
    `BreethAPIError` additionally exposes the parsed slug because
    Breeth's error slugs are meaningfully different in what a caller
    should do next (`402 payment_required` vs `429 quota_exceeded` vs
    `403 missing_scope` all need different handling later, e.g. in
    Stage 15's memory-check logic) — worth not losing that at this
    layer even though nothing consumes it yet.
- `backend/app/core/config.py` / `.env.example` — added
  `BREETH_BASE_URL` (default `https://api.thebreeth.com`) alongside
  the existing `BREETH_API_KEY` — same swappable-per-deployment
  pattern as `GEMINI_MODEL`/`OPENROUTER_MODEL`.
- `backend/scripts/test_breeth_client.py` — standalone verification,
  same shape as Stage 6/7's scripts: confirms the missing-key error
  path, then conditionally runs a live test only if `BREETH_API_KEY`
  is set. The live test writes a fact whose object value is a
  freshly-generated UUID-based marker (not a fixed string), then
  searches for that exact marker and asserts it appears in the
  results — this makes the test self-contained and re-runnable against
  the same Breeth account without stale data from a previous run
  causing a false pass.
- Ran the new script plus re-ran `test_llm_provider.py`,
  `test_llm_factory.py`, and `test_init_llm_wiring.py` (Stages 6-8) —
  all passed, no regressions. Same offline-verification caveat as
  Stages 7-8: no network access to PyPI this session, so the real
  `httpx`/`pydantic_settings` packages could not be installed; the
  local stand-ins on `PYTHONPATH` (not shipped) were reused to import
  and exercise the actual, unmodified project code. This stage's live
  Breeth round-trip is additionally untestable regardless of stub
  status, since it requires real network access to `api.thebreeth.com`
  and a real API key — neither available in this sandbox — so the
  skip path (not the live path) is what's actually been exercised
  here; the live path is written to spec from the fetched docs but
  unverified against the real API until a key + network access are
  available.

## Decisions Taken

- **Accepted:** `POST /v1/facts` over `POST /v1/episodes` for this
  stage's write-side test, per the docs' own "when to use" guidance —
  structured atomic data, minimal overhead, exactly what a connection
  test needs.
- **Accepted:** `BreethAPIError` carries the parsed slug/message
  instead of just re-raising `httpx.HTTPStatusError` — Breeth's error
  slugs (`quota_exceeded`, `payment_required`, `missing_scope`, etc.)
  are semantically distinct enough that later stages (Stage 15's
  memory checks running unattended under the scheduler) will likely
  want to branch on them, so it's worth preserving now rather than
  re-adding this parsing later.
- **Accepted:** `BREETH_BASE_URL` as a separate configurable setting
  rather than hardcoding `api.thebreeth.com` — matches the
  `GEMINI_MODEL`/`OPENROUTER_MODEL` swappability precedent and costs
  nothing.
- **Deferred:** No namespace-per-agent (`group_id` scoping tied to a
  specific `Agent.breeth_agent_ref`) — that's explicitly Stage 10's
  job per the 20-stage plan. This stage's test script uses a
  throwaway `group_id: "stage9-test"`, not a real agent's namespace.
- **Deferred:** No retry/backoff on the HTTP call — same deferral
  reasoning as Stages 6/7 (out of scope until Stage 18's scheduler
  needs unattended reliability).
- **Deferred:** No wrapping of `POST /v1/episodes` yet — not needed
  for this stage's connection test; will likely be added once Stage
  15+ needs to write richer prose (e.g. full post content) into
  memory, at which point the choice between facts and episodes will be
  made per-call based on the content being written.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/breeth_client.py`
- `backend/scripts/test_breeth_client.py`

## Files Modified
- `backend/app/core/config.py` — added `breeth_base_url` setting.
- `backend/.env.example` — added `BREETH_BASE_URL`.
- `README.md` — project status bumped to Stage 9, repo tree updated,
  Stage 9 verification section added, env var list updated.

## Git Commit
```
feat(backend): add Breeth client for facts/search with connection verification
```

## Stage Outcome
`python -m scripts.test_breeth_client` (run from `backend/`) confirms
`BreethClient`'s missing-API-key path fails clearly. The live
write/search round-trip is implemented to the fetched API spec but
unverified against the real Breeth API in this session — no real
`BREETH_API_KEY` and no network access to `api.thebreeth.com` are
available in this sandboxed environment (see PROJECT_STATUS.md "Known
Constraints"); the script's skip path was confirmed to work correctly
instead. `test_llm_provider.py`, `test_llm_factory.py`, and
`test_init_llm_wiring.py` (Stages 6-8) re-run with no regressions. No
database changes, no routes touched, no scheduler touched this stage —
`Agent.breeth_agent_ref` (added to the model back in Stage 2) still
isn't populated by anything; that's Stage 10.

## Next Stage
Stage 10 — Breeth Namespace on Init: `/init` creates a Breeth
namespace (via `group_id`, scoped per-agent) and stores it on
`Agent.breeth_agent_ref`, with a SQLite mirror stub for whatever local
bookkeeping the memory layer needs before Stage 15's fuller
memory_service exists.
