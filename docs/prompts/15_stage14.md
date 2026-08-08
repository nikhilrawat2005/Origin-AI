# Stage 14 — Editorial Judgment

## Goal
`editorial_judgment.py` — accept/reject each newly-discovered
candidate against the persona's editorial voice, logging rejections
(with reason) to `rejected_topics`, per the 20-stage plan.

---

## Prompt(s)

User: "continue" (after approving Stage 13's `aether-stage13.zip`).

---

## AI Response Summary

- Re-read `RejectedTopic`'s Stage 2 model docstring before designing
  anything: it already states the table "prevents re-evaluating the
  same rejected topic repeatedly" — which directly implies a
  fingerprint-based short-circuit belongs in this stage, using Stage
  13's `fingerprint_candidate()`, before spending an LLM call.
- Reviewed `LLMProvider.judge()`'s docstring (Stage 6): explicitly
  says parsing the raw text into accept/reject "is the caller's job
  (Stage 14's editorial_judgment.py), not the provider's" — confirmed
  this stage owns prompt construction and response parsing, not the
  provider layer.
- Reviewed `persona.json` and `persona_service.build_voice_profile_prompt()`
  (Stage 5): the persona bible already encodes `editorial_values`
  (including "prefer signal over volume — reject more than it
  accepts" and "never publish the same underlying story twice, even
  reworded" — the latter is effectively Stage 13/14 working together),
  `topics_of_interest`/`topics_avoided`, and `sourcing_standards`.
  Decision: put none of that logic in `editorial_judgment.py` itself —
  the system prompt (the voice profile) carries all editorial
  criteria, keeping this module's own logic limited to prompt
  plumbing, response parsing, and persistence.
- `_build_judgment_prompt()`: states the candidate's concrete fields
  (title/source/url/category/summary) and a strict required response
  format (`ACCEPT: <reason>` / `REJECT: <reason>`), instructing the
  model to judge "based strictly on the editorial values... defined
  above" (i.e. in the system prompt) rather than repeating the
  criteria in the user prompt.
- `_parse_judgment()`: strict on the ACCEPT case (must start with the
  literal prefix), permissive on everything else — missing prefix,
  garbage text, empty string — all fall through to REJECT with a
  descriptive reason. This "fail closed" posture was the main design
  decision this stage, directly justified by the persona's own stated
  preference to reject more than it accepts.
- `judge_candidate()` wraps the fingerprint short-circuit, the LLM
  call (wrapped in try/except so a provider outage also fails closed
  rather than raising into whatever calls this — important since
  Stage 18's scheduler will eventually call this unattended), parsing,
  and — only on rejection — persisting a `RejectedTopic` row.
  Acceptance creates no row; there's nothing to persist for an
  accepted topic yet (that's Stage 16's post writer / Stage 17's
  publisher).
- `judge_candidates()` added as the batch entry point matching the
  list shape Stage 12's `discover_new_topics()` already returns, so
  Stage 18's scheduler chain can compose them directly:
  `discover_new_topics(db)` → `judge_candidates(db, agent_id, ...)`.
- `backend/scripts/test_editorial_judgment.py` — six checks against an
  in-memory DB with a `ScriptedProvider` (returns a pre-set sequence of
  responses, one per call) and a `RaisingProvider` (always throws), no
  network/API key needed: ACCEPT parsing + no rejection row; REJECT
  parsing + row with correct fingerprint/reason; the fingerprint
  short-circuit against a reworded/reordered-title near-duplicate of a
  rejected topic (asserts zero additional LLM calls AND no duplicate
  row); unparseable-response fail-closed; provider-exception
  fail-closed without propagating; and batch ordering via
  `judge_candidates()`.
- Ran the new script, then re-ran all ten prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13) — all passed, no
  regressions.

## Decisions Taken

- **Accepted:** fingerprint-based short-circuit against
  `rejected_topics` before any LLM call — directly implied by
  `RejectedTopic`'s own Stage 2 docstring and by `persona.json`'s
  "never publish the same underlying story twice, even reworded"
  value; also the practical payoff of Stage 13 existing at all.
- **Accepted:** fail-closed on every ambiguous/error path (unparseable
  text, empty response, provider exception) — matches the persona's
  explicit "reject more than it accepts" editorial value; an LLM
  outage should degrade to "publish nothing new," never to "publish
  everything."
- **Accepted:** strict `ACCEPT`/`REJECT` prefix format enforced via
  prompt instructions and lenient parsing on the caller side, rather
  than asking for structured JSON output — keeps the provider
  abstraction's `judge(prompt, system) -> str` shape (Stage 6) exactly
  as-is instead of requiring provider-specific JSON-mode support that
  not all providers may have.
- **Accepted:** all editorial criteria live in the system prompt
  (persona voice profile) rather than being duplicated as code-level
  rules in `editorial_judgment.py` — keeps the persona bible
  (`persona.json`) the single source of truth for what Aether does
  and doesn't cover, so future changes to editorial taste are a
  content edit, not a code change.
- **Deferred:** Breeth-based memory dedup against previously
  *published* topics — Stage 15's job; this stage only guards against
  re-judging something already in `rejected_topics`.
- **Deferred:** wiring `judge_candidates()` into any route or the
  scheduler — Stage 18, once the scheduler exists.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/editorial_judgment.py`
- `backend/scripts/test_editorial_judgment.py`
- `docs/prompts/15_stage14.md`

## Files Modified
- `README.md` — project status bumped to Stage 14, repo tree updated,
  Stage 14 verification section added.
- `PROJECT_STATUS.md` — Stage 14 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 14 entry appended.

## Git Commit
```
feat(backend): add editorial judgment with fail-closed LLM accept/reject and rejected_topics logging
```

## Stage Outcome
`python3 scripts/test_editorial_judgment.py` (run from `backend/`,
venv active) passes all six checks against an in-memory DB with a
scripted fake provider — no real API key needed. Re-ran all ten prior
verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13) — all
pass, no regressions. Nothing wired into any route or the (not-yet-
existing) scheduler this stage — `judge_candidate()`/
`judge_candidates()` exist as standalone, directly-callable functions
only, same posture as Stage 12's `discover_new_topics()`.

## Next Stage
Stage 15 — Memory Service (Breeth dedup): `memory_service.py`,
checking Breeth + the SQLite mirror for previously *published* topics
before a candidate reaches the post writer — the memory layer this
stage's fingerprint short-circuit doesn't cover (that only guards
against re-judging already-*rejected* topics).
