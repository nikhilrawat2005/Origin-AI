"""
LLM provider abstraction.

`base_provider.LLMProvider` is the interface every concrete provider
implements: `gemini_provider.GeminiProvider` (Stage 6) and
`openrouter_provider.OpenRouterProvider` (Stage 7). `llm_factory.py`
(Stage 7) picks a provider based on `settings.llm_provider` via
`get_llm_provider()`. From this stage on, nothing outside this package
should import a concrete provider class directly — callers depend on
`LLMProvider` and get their instance from the factory.
"""
