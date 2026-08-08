"""
GeminiProvider — the first concrete `LLMProvider` implementation.

Talks to the Gemini API's REST `generateContent` endpoint directly via
`httpx` rather than pulling in the `google-genai` SDK, to keep the
dependency footprint minimal (httpx is already a dependency for other
reasons) and because the REST surface used here is small (one endpoint,
one shape) — a full SDK is more than this needs.

Model is configurable via `GEMINI_MODEL` (defaults to
"gemini-2.5-flash" — a good cost/quality default for a hackathon
project; swap to a larger model via env if quality matters more than
cost for a given deployment).
"""
import httpx

from app.core.config import get_settings
from app.services.llm.base_provider import LLMProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiConfigError(RuntimeError):
    """Raised when GeminiProvider is used without a configured API key."""


class GeminiProvider(LLMProvider):
    """LLMProvider backed by Google's Gemini API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model if model is not None else settings.gemini_model

    @property
    def name(self) -> str:
        return "gemini"

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._call(prompt, system)

    def judge(self, prompt: str, system: str | None = None) -> str:
        # Same underlying call as generate() for now — kept as a
        # separate method (per the LLMProvider interface) so a future
        # tweak (e.g. lower temperature for judgment calls) can be made
        # here without touching generate()'s behavior.
        return self._call(prompt, system)

    def summarize(self, text: str, system: str | None = None) -> str:
        instruction = (
            "Summarize the following text concisely, preserving all "
            "factual claims, names, and numbers. Do not add commentary.\n\n"
            f"{text}"
        )
        return self._call(instruction, system)

    def _call(self, prompt: str, system: str | None) -> str:
        if not self._api_key:
            raise GeminiConfigError(
                "GEMINI_API_KEY is not set. Add it to backend/.env "
                "(see .env.example) to make live calls."
            )

        url = f"{GEMINI_API_BASE}/{self._model}:generateContent"
        body: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        response = httpx.post(
            url,
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                f"Unexpected Gemini response shape: {data}"
            ) from exc
