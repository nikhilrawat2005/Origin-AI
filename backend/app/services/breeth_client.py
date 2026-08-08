"""
BreethClient — thin wrapper around Breeth's REST API.

Stage 9 scope: connection only. Enough to write a structured fact and
read it back via search, proving the credentials and base URL are
correct. Namespace-per-agent (via Breeth's `group_id`) and wiring this
into `/init` land in Stage 10; the fuller memory surface Aether's
pipeline actually needs — checking for duplicate topics before
publishing, storing rejected topics, recalling publishing history —
lands progressively from Stage 15 onward. This file intentionally
exposes only the two primitives (`write_fact`, `search`) needed to
prove connectivity; it is not the final memory_service.

API reference used (docs.thebreeth.com, fetched live since the API
wasn't in training data — see PROJECT_STATUS.md "Known Constraints"):
- Base URL: https://api.thebreeth.com, all routes under /v1.
- Auth: `Authorization: Bearer <ck_live_... API key>` on every request.
- `POST /v1/facts` — write a single subject/predicate/object triple.
  Chosen over `POST /v1/episodes` for the write side of this stage's
  test because it's a structured, minimal-overhead ingest path
  (episodes are meant for free-form prose and run a heavier pipeline)
  — a better fit for "prove the connection works" than for actual
  topic/post storage, which will decide between the two later once
  there's real content to write.
- `POST /v1/search` — hybrid (BM25 + vector + graph) retrieval, scoped
  to the caller's team/project automatically. Used as the "read"
  half of the connection test: write a fact, then search for it.
- Errors come back as a JSON envelope: `{"error": "<slug>", "message": "..."}`.
"""
import httpx

from app.core.config import get_settings

BREETH_API_VERSION = "v1"


class BreethConfigError(RuntimeError):
    """Raised when BreethClient is used without a configured API key."""


class BreethAPIError(RuntimeError):
    """Raised when Breeth returns a non-2xx response.

    Carries the parsed error envelope (`slug`, `message`) when the API
    returned one, so callers can distinguish e.g. `quota_exceeded` from
    `unauthenticated` without re-parsing the response themselves.
    """

    def __init__(self, status_code: int, slug: str, message: str):
        self.status_code = status_code
        self.slug = slug
        self.message = message
        super().__init__(f"Breeth API error {status_code} ({slug}): {message}")


class BreethClient:
    """Minimal client for Breeth's REST API — connection-only scope."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.breeth_api_key
        self._base_url = (base_url if base_url is not None else settings.breeth_base_url).rstrip("/")

    def write_fact(
        self,
        subject: str,
        predicate: str,
        object_: str,
        group_id: str = "default",
        extract_intent: bool = False,
    ) -> dict:
        """Write a single subject/predicate/object fact via POST /v1/facts.

        Returns the parsed response body (same shape as /v1/episodes:
        `ok`, `episode_name`, `extracted`, `group_id`, `warning`, ...).
        """
        return self._post(
            "/facts",
            {
                "subject": subject,
                "predicate": predicate,
                "object": object_,
                "group_id": group_id,
                "extract_intent": extract_intent,
            },
        )

    def search(self, query: str, group_id: str = "default", limit: int = 10) -> dict:
        """Hybrid search via POST /v1/search.

        Returns the parsed response body (`edges`, `_cache`, and
        `director_profile` if the query was subjective).
        """
        return self._post(
            "/search",
            {"query": query, "group_id": group_id, "limit": limit},
        )

    def _post(self, path: str, body: dict) -> dict:
        if not self._api_key:
            raise BreethConfigError(
                "BREETH_API_KEY is not set. Add it to backend/.env "
                "(see .env.example) to make live calls."
            )

        url = f"{self._base_url}/{BREETH_API_VERSION}{path}"
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30.0,
        )

        if response.status_code >= 400:
            try:
                envelope = response.json()
                slug = envelope.get("error", "unknown_error")
                message = envelope.get("message", response.text)
            except ValueError:
                slug = "unknown_error"
                message = response.text
            raise BreethAPIError(response.status_code, slug, message)

        return response.json()
