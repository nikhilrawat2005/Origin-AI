"""
LLMFactory — picks a concrete `LLMProvider` off `settings.llm_provider`.

From this stage on, nothing outside the `app/services/llm/` package
should import `GeminiProvider` or `OpenRouterProvider` directly —
callers (Stage 8's `/init` wiring, Stage 14's editorial judgment,
Stage 16's post writer) depend on `LLMProvider` and get their concrete
instance from `get_llm_provider()` here. That's what makes the
provider actually swappable per the PRD's "LLM: Gemini, behind a
provider abstraction (swappable)" requirement — swapping is a one-line
env change (`LLM_PROVIDER=openrouter`), not a code change.
"""
from app.core.config import get_settings
from app.services.llm.base_provider import LLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openrouter_provider import OpenRouterProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
}


class UnknownLLMProviderError(ValueError):
    """Raised when `LLM_PROVIDER` doesn't match a registered provider."""


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Return an `LLMProvider` instance for `provider_name`.

    Defaults to `settings.llm_provider` (env-driven) when not given
    explicitly. Explicit override exists mainly for tests/scripts that
    want to force a specific provider without touching the env.
    """
    settings = get_settings()
    name = (provider_name or settings.llm_provider).lower()

    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        known = ", ".join(sorted(_PROVIDERS))
        raise UnknownLLMProviderError(
            f"Unknown LLM_PROVIDER '{name}'. Known providers: {known}."
        )
    return provider_cls()
