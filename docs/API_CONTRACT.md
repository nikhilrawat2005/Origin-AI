# Aether — Public API Contract

The PRD (`PROJECT_STATUS.md` §5) allows exactly two public endpoints.
This is the frozen contract for both, as actually implemented as of
Stage 20. `backend/scripts/test_api_contract.py` asserts this contract
holds against the real FastAPI app (not just against the Pydantic
schema definitions), so a future change to either route can't silently
drift from what's documented here without a test failing.

## `POST /api/agent/init`

Idempotent — the evaluator calls this exactly once, but a repeat call
is safe and returns the same agent (never starts a second scheduler).

**Request:** no body.

**Response `200`:**

```json
{
  "agentId": "string (uuid)",
  "status": "string — \"initializing\" | \"active\"",
  "personaName": "string",
  "personaDescription": "string | null",
  "breethAgentRef": "string | null",
  "createdAt": "string (ISO 8601 datetime)"
}
```

- `status` is `"active"` by the time the response is sent — the
  scheduler is started and its first tick is fired (immediately, not
  after a full `PUBLISH_INTERVAL_MINUTES`) before `/init` returns.
- `personaDescription` is `null` only if the LLM call failed (e.g. no
  real `GEMINI_API_KEY` configured) — init still succeeds in that case
  per `agent_service.py`'s documented graceful-degradation behavior.
- `breethAgentRef` is always populated (it's a locally-derived id, not
  something Breeth returns) even if the underlying remote Breeth write
  failed.

## `GET /api/agent/feed`

Read-only, no side effects — safe to poll repeatedly, and safe to call
before `/init` has ever been called.

**Request:** no params.

**Response `200`, no agent yet:**

```json
{
  "agentId": null,
  "personaName": null,
  "status": null,
  "posts": []
}
```

**Response `200`, agent exists:**

```json
{
  "agentId": "string (uuid)",
  "personaName": "string",
  "status": "string",
  "posts": [
    {
      "id": "string (uuid)",
      "title": "string",
      "content": "string",
      "rationale": "string",
      "sources": ["string (url)", "..."],
      "createdAt": "string (ISO 8601 datetime)"
    }
  ]
}
```

- `posts` is always sorted newest-first (`created_at DESC`).
- Every post always has non-empty `title`/`content`/`rationale` — the
  `Post` model (Stage 2) makes `rationale` and `sources` required
  columns, and `post_writer.py` (Stage 16) fails loud rather than
  publishing an incomplete post.
- `sources` is `[]` (not omitted, not `null`) both for a post with
  genuinely no sources and for a post whose stored `sources` JSON
  failed to parse — the frontend never needs to null-check this field.

## What's deliberately absent

Per §2's out-of-scope list: no auth/session fields, no pagination
params (`?page=`, `?cursor=`), no `PATCH`/`DELETE` on posts, no
per-post engagement fields (likes, views), no webhook/callback
registration. Adding any of these would be scope creep beyond what the
PRD's two-endpoint, two-page design calls for.
