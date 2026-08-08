"""
LLMProvider — the interface every concrete model backend implements.

Stage 6 scope: define the interface and ship the first implementation
(Gemini). Stage 7 adds a second provider (OpenRouter) and an
`llm_factory.py` that picks between them off `settings.llm_provider` —
that's the point at which the rest of the codebase (editorial judgment
in Stage 14, post writing in Stage 16, persona voice-profile generation
in Stage 8) starts depending on `LLMProvider` instead of a concrete
class. Nothing outside this package should import a concrete provider
directly once Stage 7 lands.

Three methods, matching the three distinct jobs Aether's pipeline needs
an LLM for (per the PRD's functional flow):

- `generate`  — open-ended text generation (post writing, persona voice
  profile generation).
- `judge`     — a yes/no-with-reasoning call (editorial acceptance).
  Kept separate from `generate` rather than reusing it with a different
  prompt, because a provider may want to use different model params
  (e.g. lower temperature, a smaller/cheaper model) for judgment calls
  than for long-form writing.
- `summarize` — condensing a longer text into a shorter one (used when
  feeding source material into the editorial/writing steps without
  blowing the context budget).

All three share the same `(prompt, system=None) -> str` shape so a
caller doesn't need to know which concrete provider it's talking to.
"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface for all LLM backends (Gemini, OpenRouter, ...)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for logging/debugging, e.g. 'gemini'."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Open-ended generation. Returns the model's raw text output.

        `system` is typically the persona voice-profile prompt from
        `persona_service.build_voice_profile_prompt()`.
        """
        raise NotImplementedError

    @abstractmethod
    def judge(self, prompt: str, system: str | None = None) -> str:
        """A judgment/evaluation call (e.g. "should this topic be
        published?"). Returns the model's raw text output — parsing
        that into an accept/reject decision is the caller's job
        (Stage 14's editorial_judgment.py), not the provider's.
        """
        raise NotImplementedError

    @abstractmethod
    def summarize(self, text: str, system: str | None = None) -> str:
        """Condense `text` into a shorter form. Returns the summary."""
        raise NotImplementedError
