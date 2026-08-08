"""
Standalone verification script for Stage 7 — LLMFactory + Second Provider.

Run with:  python -m scripts.test_llm_factory   (from backend/)

Checks:
1. OpenRouterProvider implements the full LLMProvider interface and
   reports name == "openrouter".
2. Calling OpenRouterProvider without an API key raises a clear
   OpenRouterConfigError.
3. get_llm_provider() returns a GeminiProvider when LLM_PROVIDER=gemini
   (the settings default) and an OpenRouterProvider when explicitly
   asked for "openrouter" — proving the factory actually switches.
4. get_llm_provider() raises UnknownLLMProviderError for a bogus
   provider name instead of silently defaulting to something.
5. If OPENROUTER_API_KEY is set in the environment, makes one real
   generate() call as a live smoke test; otherwise skips cleanly, same
   pattern as Stage 6's Gemini smoke test.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.llm.base_provider import LLMProvider  # noqa: E402
from app.services.llm.gemini_provider import GeminiProvider  # noqa: E402
from app.services.llm.openrouter_provider import (  # noqa: E402
    OpenRouterProvider,
    OpenRouterConfigError,
)
from app.services.llm.llm_factory import (  # noqa: E402
    get_llm_provider,
    UnknownLLMProviderError,
)
from app.core.config import get_settings  # noqa: E402


def main() -> None:
    print("1. Confirming OpenRouterProvider implements the interface...")
    provider = OpenRouterProvider(api_key="", model="openai/gpt-4o-mini")
    assert isinstance(provider, LLMProvider)
    assert provider.name == "openrouter"
    for method in ("generate", "judge", "summarize"):
        assert callable(getattr(provider, method))
    print("   OK — name == 'openrouter', generate/judge/summarize all callable")

    print("2. Confirming missing API key raises a clear error...")
    try:
        provider.generate("hello")
        raise AssertionError("Expected OpenRouterConfigError with no API key")
    except OpenRouterConfigError as e:
        print(f"   OK — OpenRouterConfigError raised: {e}")

    print("3. Confirming get_llm_provider() switches on provider name...")
    settings = get_settings()
    assert settings.llm_provider == "gemini", (
        "expected default LLM_PROVIDER=gemini in .env/.env.example"
    )
    default_provider = get_llm_provider()
    assert isinstance(default_provider, GeminiProvider)
    print("   OK — default (LLM_PROVIDER=gemini) resolves to GeminiProvider")

    explicit_openrouter = get_llm_provider("openrouter")
    assert isinstance(explicit_openrouter, OpenRouterProvider)
    print("   OK — get_llm_provider('openrouter') resolves to OpenRouterProvider")

    explicit_gemini = get_llm_provider("GEMINI")  # case-insensitivity check
    assert isinstance(explicit_gemini, GeminiProvider)
    print("   OK — provider name lookup is case-insensitive")

    print("4. Confirming an unknown provider name fails loudly...")
    try:
        get_llm_provider("not-a-real-provider")
        raise AssertionError("Expected UnknownLLMProviderError")
    except UnknownLLMProviderError as e:
        print(f"   OK — UnknownLLMProviderError raised: {e}")

    print("5. Checking for a real OPENROUTER_API_KEY for a live smoke test...")
    if not settings.openrouter_api_key:
        print(
            "   SKIPPED — no OPENROUTER_API_KEY set in backend/.env. This is "
            "expected in this sandboxed dev environment (see "
            "PROJECT_STATUS.md 'Known Constraints'). Set a real key and "
            "re-run this script to exercise the live path."
        )
    else:
        live_provider = OpenRouterProvider()
        reply = live_provider.generate(
            "Reply with exactly the word: pong",
            system="You are a terse test responder.",
        )
        print(f"   OK — live call succeeded, response: {reply!r}")

    print("\nAll Stage 7 LLMFactory checks passed.")


if __name__ == "__main__":
    main()
