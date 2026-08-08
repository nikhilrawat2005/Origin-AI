"""
LLM provider abstraction.

`base_provider.LLMProvider` is the interface every concrete provider
implements (Stage 6: `gemini_provider.GeminiProvider`). Stage 7 adds a
second provider (OpenRouter) and `llm_factory.py`, which picks a
provider based on `settings.llm_provider` — nothing in this package
should be imported directly by routes/services outside this package
once the factory exists; for now (pre-Stage-7) callers import the
concrete provider class directly.
"""
