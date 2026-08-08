# Aether — Project State

Quick-resume file. If context resets, read this first, then
`PROJECT_STATUS.md` for full background.

## Current Stage

Release Candidate — post-Stage-20 hardening pass (evaluator-contract
audit fixes applied on top of the Stage 20 build).

## Completed Stages

Stages 1–20 (see `docs/prompts/` for the stage-by-stage build history),
plus this audit pass, which:

- Locked `POST /api/agent/init` to return exactly `{"agentId": "..."}`
  and accept an optional `{"persona": {"name","domain"}}` body.
- Locked `GET /api/agent/feed` to return exactly `{"posts": [...]}`,
  each post carrying `id`, `createdAt` (ISO 8601 UTC, `Z` suffix),
  `text`, `rationale`, `sources` — dropped `title`, renamed
  `content` → `text`, removed the wrapping agent-identity fields.
- Made OpenRouter the default/primary `LLM_PROVIDER`; Gemini remains
  supported as an optional fallback provider, never required.
- Set `PUBLISH_INTERVAL_MINUTES` default to 30, cleaned `.env.example`
  down to only the variables actually read by `core/config.py`.
- Added `backend/.gitignore` (real `.env` was never committed, but
  there was no gitignore protecting against it).
- Updated frontend (`lib/api.ts`, `page.tsx`, `feed/page.tsx`) to match
  the new API contract.
- Updated `docs/API_CONTRACT.md` and the two contract-test scripts
  (`test_api_contract.py`, `test_feed_endpoint.py`) to match.

## Current Objective

Ready for hackathon submission. Remaining optional polish: set real
`OPENROUTER_API_KEY` / `BREETH_API_KEY` values in a real (never
committed) `.env` before a live demo, since all LLM/Breeth calls
degrade gracefully but produce no actual content without a real key.

## Current Branch

Not tracked here — check `git branch` / `git status` locally; this
project's history in this environment has been managed as flat ZIP
handoffs (`aether-stage20.zip` was the last one, this pass supersedes
it).

## Known Blockers

None functional. No real LLM/Breeth API keys are configured in this
sandboxed environment, so:
- Persona descriptions fall back to the static `persona.json` tagline.
- Editorial judgment / post generation cannot run end-to-end without a
  real `OPENROUTER_API_KEY`.
- Breeth memory checks fall back to the local SQLite mirror.

All of this is by design (fail-open / fail-soft), not a bug — see
`memory_service.py` and `agent_service.py` docstrings.

## Next Step

1. Drop a real `OPENROUTER_API_KEY` into a local (gitignored) `.env`.
2. Run `python -m scripts.test_api_contract` and the rest of
   `backend/scripts/test_*.py` to re-verify (17 scripts, all currently
   green).
3. Deploy backend + frontend to Railway per `docs/DEPLOYMENT.md`.
4. Call `POST /api/agent/init` once, then watch `GET /api/agent/feed`
   grow on its own.
