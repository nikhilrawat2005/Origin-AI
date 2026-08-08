"""
Standalone verification script for Stage 6 — LLMProvider Interface.

Run with:  python -m scripts.test_llm_provider   (from backend/)

Checks:
1. LLMProvider cannot be instantiated directly (it's an ABC).
2. GeminiProvider implements the full interface (name, generate,
   judge, summarize) and reports name == "gemini".
3. Calling without an API key raises a clear GeminiConfigError instead
   of a confusing network/auth error.
4. If GEMINI_API_KEY is set in the environment, makes one real
   `generate()` call and prints the response, as a live smoke test.
   If it's not set (the expected case in this sandboxed environment —
   see PROJECT_STATUS.md "Known Constraints"), that step is skipped
   with a clear message rather than failing the script.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.llm.base_provider import LLMProvider  # noqa: E402
from app.services.llm.gemini_provider import (  # noqa: E402
    GeminiProvider,
    GeminiConfigError,
)
from app.core.config import get_settings  # noqa: E402


def main() -> None:
    print("1. Confirming LLMProvider is abstract...")
    try:
        LLMProvider()  # type: ignore[abstract]
        raise AssertionError("LLMProvider should not be instantiable directly")
    except TypeError:
        print("   OK — instantiating LLMProvider directly raises TypeError")

    print("2. Confirming GeminiProvider implements the interface...")
    provider = GeminiProvider(api_key="", model="gemini-2.5-flash")
    assert isinstance(provider, LLMProvider)
    assert provider.name == "gemini"
    for method in ("generate", "judge", "summarize"):
        assert callable(getattr(provider, method))
    print("   OK — name == 'gemini', generate/judge/summarize all callable")

    print("3. Confirming missing API key raises a clear error...")
    try:
        provider.generate("hello")
        raise AssertionError("Expected GeminiConfigError with no API key")
    except GeminiConfigError as e:
        print(f"   OK — GeminiConfigError raised: {e}")

    print("4. Checking for a real GEMINI_API_KEY for a live smoke test...")
    settings = get_settings()
    if not settings.gemini_api_key:
        print(
            "   SKIPPED — no GEMINI_API_KEY set in backend/.env. This is "
            "expected in this sandboxed dev environment (see "
            "PROJECT_STATUS.md 'Known Constraints'). Set a real key and "
            "re-run this script to exercise the live path."
        )
    else:
        live_provider = GeminiProvider()
        reply = live_provider.generate(
            "Reply with exactly the word: pong",
            system="You are a terse test responder.",
        )
        print(f"   OK — live call succeeded, response: {reply!r}")

    print("\nAll Stage 6 LLMProvider checks passed.")


if __name__ == "__main__":
    main()
