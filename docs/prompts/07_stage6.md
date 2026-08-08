# Stage 6 — LLMProvider Interface

## Goal
Define the interface every LLM backend implements (`base_provider.py`)
and ship the first concrete implementation (`gemini_provider.py`). No
factory and no wiring into `/init` yet — Stage 7 adds a second provider
and the factory; Stage 8 is the first place any of this actually gets
called from a route.

---

## Prompt(s)

User: "now stage 6" (approval to proceed after reviewing the delivered
`aether-stage5.zip`).

---

## AI Response Summary

- `backend/app/services/llm/base_provider.py` — `LLMProvider(ABC)` with
  four members: `name` (property, for logging/debugging) and three
  abstract methods — `generate`, `judge`, `summarize` — all sharing the
  shape `(prompt, system=None) -> str`. Kept as three distinct methods
  instead of one `generate()` reused with different prompts, so a
  concrete provider can later give judgment calls different model
  parameters (e.g. lower temperature, a cheaper model) than long-form
  post writing, without changing the interface.
- `backend/app/services/llm/gemini_provider.py` — `GeminiProvider`.
  Calls `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  directly via `httpx` rather than the `google-genai` SDK — researched
  current Gemini REST usage first (per the Stage 0 flag about
  unfamiliar APIs, applied here proactively rather than waiting for the
  Breeth stage where it was originally flagged), confirmed the
  `x-goog-api-key` header + `contents`/`systemInstruction` request
  shape is current. One extra dependency avoided since `httpx` is
  already in `requirements.txt`. `judge()` and `summarize()` both
  route through a shared private `_call()`; `summarize()` wraps the
  text in a short fixed instruction rather than exposing a separate
  prompt-template system this early.
  - Raises `GeminiConfigError` (a `RuntimeError` subclass) with an
    actionable message if `GEMINI_API_KEY` is unset, instead of letting
    the call fail deep inside `httpx` with a confusing 401.
- `backend/app/core/config.py` / `.env.example` — added `GEMINI_MODEL`
  (default `gemini-2.5-flash`) so the model is swappable per deployment
  without a code change.
- `backend/scripts/test_llm_provider.py` — standalone verification:
  confirms `LLMProvider()` raises `TypeError` (proves it's a real ABC,
  not just a class with `pass` bodies), confirms `GeminiProvider` is an
  `LLMProvider` instance with `name == "gemini"` and all three methods
  callable, confirms the missing-key path raises `GeminiConfigError`,
  and conditionally runs one live `generate()` call only if
  `GEMINI_API_KEY` is present in the environment — skipped cleanly
  otherwise, per the Stage 0 "no real API keys in this sandbox"
  constraint. Ran it — all checks passed, live call correctly skipped.

## Decisions Taken

- **Accepted:** REST via `httpx` over the `google-genai` SDK. Fewer new
  dependencies, and the interface this stage needs (one endpoint, plain
  JSON in/out) doesn't benefit from an SDK's extra surface (streaming,
  file uploads, embeddings) that this project doesn't use anywhere in
  the PRD.
- **Accepted:** `judge()` and `summarize()` implemented as thin wrappers
  around the same `_call()` as `generate()` for now, rather than fully
  separate code paths — the interface exists to let that change later
  (Stage 14/16 may want different temperature/model per method) without
  breaking callers; there's no reason to duplicate logic before there's
  an actual reason to diverge.
- **Accepted:** A dedicated `GeminiConfigError` instead of letting a
  missing key surface as an `httpx.HTTPStatusError` from a 401 — much
  clearer for local dev and for the evaluator if a key is ever missing
  at demo time.
- **Deferred:** No retry/backoff logic on the HTTP call — out of scope
  until a stage actually depends on this running unattended (Stage 18's
  scheduler). Revisit then if flakiness shows up.
- **Deferred:** No token/cost accounting — not in the PRD's success
  criteria.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/llm/__init__.py`
- `backend/app/services/llm/base_provider.py`
- `backend/app/services/llm/gemini_provider.py`
- `backend/scripts/test_llm_provider.py`

## Files Modified
- `backend/app/core/config.py` — added `gemini_model` setting.
- `backend/.env.example` — added `GEMINI_MODEL`.
- `README.md` — project status bumped to Stage 6, repo tree updated,
  Stage 6 verification section added, env var list updated.

## Git Commit
```
feat(backend): add LLMProvider interface and Gemini implementation
```

## Stage Outcome
`python -m scripts.test_llm_provider` (run from `backend/`) confirms
`LLMProvider` is a true ABC, `GeminiProvider` implements the full
interface, and the missing-API-key path fails clearly instead of
confusingly. Live Gemini call is skipped in this environment (no real
`GEMINI_API_KEY` available) — confirmed the skip path itself works
correctly and printed the expected message. No database, no routes, no
scheduler touched this stage.

## Next Stage
Stage 7 — LLMFactory + Second Provider: `llm_factory.py` (env-driven
switch on `settings.llm_provider`) plus `openrouter_provider.py` as the
second concrete `LLMProvider`.
