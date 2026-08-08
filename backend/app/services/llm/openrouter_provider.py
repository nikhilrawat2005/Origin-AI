"""
OpenRouterProvider — the second concrete `LLMProvider` implementation.

Exists to prove the abstraction in `base_provider.py` actually holds:
if Aether's pipeline (editorial judgment, post writing, persona voice
generation) can run against either this or `GeminiProvider` with zero
caller-side changes, the interface is doing its job. OpenRouter is a
reasonable second choice because it fronts many models behind one
OpenAI-compatible `/chat/completions` shape, so this also demonstrates
the interface isn't accidentally Gemini-shaped.

Model is configurable via `OPENROUTER_MODEL` (defaults to
"openai/gpt-4o-mini" — a cheap, fast default; swap via env for any
model OpenRouter fronts).
"""
import httpx

from app.core.config import get_settings
from app.services.llm.base_provider import LLMProvider

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterConfigError(RuntimeError):
    """Raised when OpenRouterProvider is used without a configured API key."""


class OpenRouterProvider(LLMProvider):
    """LLMProvider backed by OpenRouter's OpenAI-compatible chat API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.openrouter_api_key
        self._model = model if model is not None else settings.openrouter_model

    @property
    def name(self) -> str:
        return "openrouter"

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._call(prompt, system)

    def judge(self, prompt: str, system: str | None = None) -> str:
        # Same underlying call as generate() for now — kept separate
        # per the LLMProvider interface, mirroring GeminiProvider's
        # reasoning: a future tweak (lower temperature, cheaper model)
        # can land here without touching generate().
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
            raise OpenRouterConfigError(
                "OPENROUTER_API_KEY is not set. Add it to backend/.env "
                "(see .env.example) to make live calls."
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = httpx.post(
            OPENROUTER_API_BASE,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self._model, "messages": messages},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                f"Unexpected OpenRouter response shape: {data}"
            ) from exc
