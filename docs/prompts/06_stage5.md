# Stage 5 — Persona Bible + Prompt Builder

## Goal
Define Aether's editorial identity as a static file (`persona.json`) and
a service (`persona_service.py`) that turns it into a voice-profile
prompt. No LLM call yet — that starts Stage 6 (provider interface) and
is actually used for the first time in Stage 8 (wired into `/init`).

---

## Prompt(s)

User: "now make stage 5" (approval to proceed after reviewing the
uploaded `aether-stage4.zip` and `PROJECT_STATUS.md`).

---

## AI Response Summary

- `backend/app/core/persona.json` — the persona bible. Fields: `name`,
  `tagline`, `description`, `tone` (primary + avoid list), `voice_traits`,
  `editorial_values`, `topics_of_interest`, `topics_avoided`,
  `sourcing_standards` (minimum_sources + preferred/disallowed source
  types), `writing_style_rules`, `sample_voice`. Every field maps
  directly to something the PRD asks Aether to have an opinion about:
  editorial judgment (Stage 14), sourcing (Stage 15/16), and consistent
  voice across every future post.
- `backend/app/services/persona_service.py`:
  - `load_persona()` — reads and `@lru_cache`s the JSON file. Cached
    because the bible is static config, not per-agent state; per-agent
    state (the LLM-generated `persona_description` on the `Agent` row)
    stays separate and is Stage 8's job.
  - `build_voice_profile_prompt(persona=None)` — flattens the bible into
    one prose string in the bible's field order, so nothing is silently
    dropped if the bible grows later. Chose prose over handing the raw
    JSON to the model — see decisions below.
  - `get_persona_name()` — thin accessor Stage 8 will use to seed
    `Agent.persona_name` without needing the full prompt.
- `backend/scripts/test_persona.py` — standalone verification: loads the
  bible, asserts all 11 required fields exist, builds the prompt, asserts
  it's non-trivial length and contains the persona name / first voice
  trait / sample voice line (a cheap "nothing got silently dropped"
  check), and checks `get_persona_name()`. Ran it directly — all checks
  passed, prompt built to 2576 chars.

## Decisions Taken

- **Accepted:** Prose output from `build_voice_profile_prompt()` instead
  of returning/serializing the raw JSON for the model to interpret.
  Instruction-following models are more reliable with written directives
  ("Avoid: breathless hype, clickbait framing...") than with a nested
  JSON object they're implicitly asked to parse and obey. This is the
  one real design decision of the stage.
- **Accepted:** `persona.json` lives under `app/core/`, next to
  `config.py`, not in a new top-level `persona/` package — it's static
  config like `.env.example`, not a service with logic.
- **Accepted:** `load_persona()` is cached but takes no dependency on
  the database — this stage is about the *template* voice, not any
  specific agent's stored state, keeping it decoupled from Stage 4's
  `Agent` model.
- **Deferred:** Nothing about editorial *judgment* (accept/reject logic)
  is implemented here — that's Stage 14 and will consume this prompt,
  not duplicate it.
- **Deferred:** Not wired into `/api/agent/init` or any route yet. The
  LLMProvider abstraction this prompt will actually be sent through
  doesn't exist until Stage 6/7; wiring it into `/init` early would mean
  redoing that wiring in Stage 8 anyway.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/core/persona.json`
- `backend/app/services/persona_service.py`
- `backend/scripts/test_persona.py`

## Files Modified
- `README.md` — project status bumped to Stage 5, repo tree updated,
  Stage 5 verification section added.

## Git Commit
```
feat(backend): add persona bible and voice-profile prompt builder
```

## Stage Outcome
`python -m scripts.test_persona` (run from `backend/`) loads
`persona.json`, confirms all required fields are present, builds the
full voice-profile prompt, and asserts it contains the persona name, a
voice trait, and the sample voice line. All checks passed locally — see
output captured in this stage's development session. No database, no
network, no LLM call required for this stage's verification.

## Next Stage
Stage 6 — LLMProvider Interface: `base_provider.py` (an ABC with
`generate` / `judge` / `summarize`) plus a first concrete
`gemini_provider.py` implementation. This is what will eventually carry
`persona_service.build_voice_profile_prompt()` to a real model call.
