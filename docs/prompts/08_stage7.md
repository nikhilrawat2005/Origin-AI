# Stage 7 — LLMFactory + Second Provider

## Goal
Add a second `LLMProvider` implementation (OpenRouter) and
`llm_factory.py`, which picks between it and `GeminiProvider` off
`settings.llm_provider`. This is the point at which the rest of the
codebase should start depending on `LLMProvider` + the factory instead
of a concrete class — nothing gets wired into a route yet (that's
Stage 8), but the abstraction itself needs to be provably swappable
before anything depends on it.

---

## Prompt(s)

User: "stage 7 bnao" (build stage 7), after reviewing the delivered
`aether-stage6.zip`.

---

## AI Response Summary

- `backend/app/services/llm/openrouter_provider.py` —
  `OpenRouterProvider`. Calls
  `https://openrouter.ai/api/v1/chat/completions` directly via
  `httpx`, same dependency-minimalism reasoning as `GeminiProvider`
  (Stage 6): no new dependency, and OpenRouter's OpenAI-compatible
  shape is small enough that an SDK adds nothing here. Structured to
  mirror `GeminiProvider` closely — a shared private `_call()`,
  `judge()`/`summarize()` as thin wrappers around it, a dedicated
  `OpenRouterConfigError` for a missing key — specifically so the two
  providers read as genuinely interchangeable, not superficially
  similar. Chose OpenRouter as the second provider because it fronts
  many models behind one API shape, which is a better test of the
  `LLMProvider` abstraction than picking another single-model API
  would be: if Aether's pipeline can talk to it through the same
  interface, the interface isn't secretly Gemini-shaped.
- `backend/app/services/llm/llm_factory.py` — `get_llm_provider()`.
  Internally a small `dict[str, type[LLMProvider]]` registry
  (`{"gemini": GeminiProvider, "openrouter": OpenRouterProvider}`)
  keyed by `settings.llm_provider`, lowercased for a case-insensitive
  match. Raises `UnknownLLMProviderError` (not a silent fallback to
  Gemini) if `LLM_PROVIDER` is misspelled or unset to something
  unrecognized — a wrong provider name failing loudly at startup is
  much better than it silently running against the wrong model.
  Accepts an optional explicit `provider_name` argument (default
  `None`, falls back to the env-driven setting) so tests/scripts can
  force a specific provider without mutating `.env`.
- `backend/app/core/config.py` / `.env.example` — added
  `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` (default
  `openai/gpt-4o-mini` — cheap/fast default, swappable per
  deployment), matching the `GEMINI_API_KEY`/`GEMINI_MODEL` pattern
  from Stage 6.
- `backend/app/services/llm/__init__.py` — docstring updated to state
  the new package-level rule now that the factory exists: routes/
  services outside `app/services/llm/` should call
  `get_llm_provider()` rather than importing a concrete provider
  class. (Nothing outside the package imports a provider yet — this
  is a rule for Stage 8 onward, stated now so it isn't missed.)
- `backend/scripts/test_llm_factory.py` — standalone verification,
  structured to parallel `test_llm_provider.py`: confirms
  `OpenRouterProvider` implements the full interface and reports
  `name == "openrouter"`; confirms its missing-key path raises
  `OpenRouterConfigError`; confirms `get_llm_provider()` with no args
  resolves to `GeminiProvider` (proving the `.env` default actually
  takes effect), confirms `get_llm_provider("openrouter")` resolves to
  `OpenRouterProvider`, confirms `get_llm_provider("GEMINI")` also
  resolves correctly (case-insensitivity), confirms
  `get_llm_provider("not-a-real-provider")` raises
  `UnknownLLMProviderError`; and conditionally runs one live
  OpenRouter `generate()` call only if `OPENROUTER_API_KEY` is present
  — skipped cleanly otherwise, per the same sandboxed-environment
  constraint noted for Gemini in Stage 6.
- Ran both `scripts/test_llm_factory.py` (new) and
  `scripts/test_llm_provider.py` (Stage 6, re-run to check for
  regressions) — all checks passed. Note on how this was verified:
  this sandboxed container has no network access, so
  `pip install -r requirements.txt` could not reach PyPI this session.
  Rather than skip verification, minimal local stand-ins for `httpx`
  and `pydantic_settings` were placed on `PYTHONPATH` (not shipped in
  the project) purely so the real project code — unmodified — could be
  imported and its actual logic (ABC enforcement, factory switching,
  error paths) exercised end-to-end offline. The live-API-call branch
  in both scripts still correctly self-skips regardless, since no real
  key is configured either way — this is orthogonal to the network
  constraint and would skip the same way with real dependencies
  installed.

## Decisions Taken

- **Accepted:** Dict-based registry in `llm_factory.py` over an
  if/elif chain — trivial to extend with a third provider later
  (append one entry), and it's the natural shape for "name → class"
  lookups.
- **Accepted:** `UnknownLLMProviderError` on a bad `LLM_PROVIDER`
  value instead of silently defaulting to Gemini. A misconfigured env
  var should fail at the point it's read, not surface later as
  mysteriously-wrong model output.
- **Accepted:** OpenRouter as the second provider (matches the
  original Stage 7 plan in `PROJECT_STATUS.md`) — reasoning above on
  why it's a better abstraction test than a second single-model API.
- **Accepted:** Case-insensitive provider name matching — env vars get
  typed by hand often enough that `LLM_PROVIDER=Gemini` shouldn't be a
  hard failure.
- **Deferred:** No retry/backoff, no token/cost accounting — same
  deferral as Stage 6, for the same reason (out of scope until Stage
  18's scheduler actually needs unattended reliability).
- **Deferred:** No caching of the constructed provider instance inside
  `get_llm_provider()` (it constructs a fresh one per call). Providers
  are cheap to construct (no connection pooling, no I/O in `__init__`)
  so there's no performance reason to cache yet; revisit only if a
  future stage shows otherwise.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/llm/openrouter_provider.py`
- `backend/app/services/llm/llm_factory.py`
- `backend/scripts/test_llm_factory.py`

## Files Modified
- `backend/app/services/llm/__init__.py` — docstring updated for the
  post-factory package rule.
- `backend/app/core/config.py` — added `openrouter_api_key`,
  `openrouter_model` settings.
- `backend/.env.example` — added `OPENROUTER_API_KEY`,
  `OPENROUTER_MODEL`.
- `README.md` — project status bumped to Stage 7, repo tree updated,
  Stage 7 verification section added, env var list updated.

## Git Commit
```
feat(backend): add LLMFactory and OpenRouter provider for env-driven LLM switching
```

## Stage Outcome
`python -m scripts.test_llm_factory` (run from `backend/`) confirms
`OpenRouterProvider` implements the full `LLMProvider` interface, its
missing-key path fails clearly, and — the actual point of this stage —
`get_llm_provider()` genuinely switches between `GeminiProvider` and
`OpenRouterProvider` based on `LLM_PROVIDER`, with a loud failure for
an unrecognized value instead of a silent wrong default.
`scripts/test_llm_provider.py` (Stage 6) re-run to confirm no
regression. Live OpenRouter call is skipped in this environment (no
real `OPENROUTER_API_KEY` available) — confirmed the skip path itself
works correctly. No database, no routes, no scheduler touched this
stage.

## Next Stage
Stage 8 — Wire LLM into Init: `/init` calls
`persona_service.build_voice_profile_prompt()` (Stage 5) and passes it
through `get_llm_provider().generate()` (Stage 7's factory) to produce
and save the agent's actual voice profile — the first place any of the
LLM abstraction gets called from a real request.
