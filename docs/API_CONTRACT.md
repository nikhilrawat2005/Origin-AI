# Aether — Public API Contract

Exactly two public endpoints, frozen to the exact hackathon evaluator
shape. `backend/scripts/test_api_contract.py` asserts this contract
holds against the real FastAPI app (not just the Pydantic schema
definitions), so a future change to either route can't silently drift
from what's documented here without a test failing.

## `POST /api/agent/init`

Idempotent — the evaluator calls this once, but a repeat call is safe
and returns the same `agentId` (never starts a second scheduler).

**Request (optional body):**

```json
{
  "persona": {
    "name": "Aether",
    "domain": "AI Technology"
  }
}
```

`persona` is optional — if omitted, the persona defined in
`backend/app/core/persona.json` is used as-is. `persona.name`, when
given, overrides the agent's name; `persona.domain` is accepted but
not required for behavior.

**Response `200`:**

```json
{
  "agentId": "string (uuid)"
}
```

No other fields. Internally, calling this also starts the autonomous
publish-cycle scheduler and flips the agent's status to `"active"` —
but none of that is exposed on this response; it happens silently,
matching the "no unnecessary fields on evaluator-facing APIs"
requirement.

## `GET /api/agent/feed`

Read-only, no side effects — safe to poll repeatedly, and safe to call
before `/init` has ever been called (returns an empty feed rather than
an error, and never creates an agent as a side effect).

**Request:** no params (`agentId` query param not required — there is
exactly one agent per deployment).

**Response `200`, no agent yet or zero posts:**

```json
{
  "posts": []
}
```

**Response `200`, agent has published posts:**

```json
{
  "posts": [
    {
      "id": "p7",
      "createdAt": "2026-08-07T10:30:00Z",
      "text": "...",
      "rationale": "...",
      "sources": [
        "https://..."
      ]
    }
  ]
}
```

- `posts` is always sorted newest-first (`created_at DESC`).
- `createdAt` is always ISO 8601 UTC with a literal `Z` suffix.
- `text` (not `content`) carries the post body — renamed to match the
  contract literally; the underlying `Post.content` DB column is
  unchanged, only the API-facing field name changed.
- `id` values are unique per post; old posts always remain available —
  nothing here ever deletes or hides a previously-published post.
- `sources` is `[]` (not omitted, not `null`) both for a post with
  genuinely no sources and for a post whose stored `sources` JSON
  failed to parse — callers never need to null-check this field.
- No wrapping `agent` object, no `title`, no `agentId`/`personaName`/
  `status` fields on this response — `posts` is the only top-level key.

## What's deliberately absent

No auth/session fields, no pagination params (`?page=`, `?cursor=`),
no `PATCH`/`DELETE` on posts, no per-post engagement fields (likes,
views), no webhook/callback registration, and critically: **no
`/generate` or `/run` endpoint**. Only `/init` and `/feed` are public;
every publish cycle after `/init` runs autonomously via the scheduler,
never via a manually-triggerable route.
