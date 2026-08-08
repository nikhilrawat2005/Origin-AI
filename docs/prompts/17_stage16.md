# Stage 16 — Post Writer

## Goal
`post_writer.py` — generate post text + rationale via `LLMFactory`,
given a judged-accepted (Stage 14), memory-cleared (Stage 15) topic
candidate, per the 20-stage plan.

---

## Prompt(s)

User: "now go for stage 16" (after approving Stage 15's
`aether-stage15.zip`).

---

## AI Response Summary

- Re-read `LLMProvider`'s Stage 6 docstring: `generate` is explicitly
  scoped for "open-ended text generation (post writing, persona voice
  profile generation)" — confirmed this stage should call `generate()`,
  not `judge()` (Stage 14's method) or `summarize()`.
- Reviewed `Post`'s Stage 2 model docstring again (already read in
  Stage 15): `rationale` is `nullable=False` and `sources` is
  "JSON-encoded list of source URLs/references this post was derived
  from" — both required inputs this stage must produce, alongside
  title/content, before Stage 17 can persist anything.
- Reviewed `persona.json`'s `writing_style_rules` and
  `sourcing_standards` (`minimum_sources: 1`): confirmed a single
  `candidate.url` as `sources` satisfies the persona's own stated
  minimum, so no source-aggregation logic was needed this stage —
  explicitly noted as out of scope rather than silently skipped.
- Design decision: `write_post()` takes the full `JudgmentResult`
  (Stage 14's dataclass), not just a bare `TopicCandidate`. Reasoning:
  the editorial acceptance reason (`judgment.reason`) is valuable
  context for the rationale the model writes — grounding "why was this
  worth covering" in the actual editorial decision rather than asking
  the model to reconstruct a rationale from nothing — and it lets
  `write_post()` assert immediately if ever called on a *rejected*
  result, catching a caller-side bug before spending an LLM call.
- Prompt format: settled on a strict `TITLE:` / `RATIONALE:` /
  `CONTENT:` three-marker response (mirroring Stage 14's `ACCEPT:` /
  `REJECT:` precedent for keeping provider-agnostic plain-text parsing
  instead of requiring JSON-mode support not every provider has), with
  `CONTENT:` last since it's the only open-ended multi-paragraph
  section and everything after that marker is unambiguously the body.
- Main design decision this stage: fail **loud** (raise
  `PostWriteError`) rather than fail closed (Stage 14's posture) or
  fail open (Stage 15's posture) on any generation/parsing problem.
  Reasoning: Stage 14's fail-closed REJECT is a genuinely safe default
  verdict; Stage 15's fail-open "assume novel" is safe because Layer 1
  (local fingerprint) is still authoritative regardless. Post writing
  has no equivalent safe default — there's no meaningful "placeholder
  post" that respects `persona.json`'s "prefer signal over volume"
  value, so a caller-visible exception (for Stage 17 to catch, log,
  and skip that cycle) is the only sound behavior. Documented this
  three-way asymmetry (closed / open / loud) explicitly in the module
  docstring so it reads as intentional across stages, not inconsistent.
- `_parse_post_response()` requires all three markers present *and* in
  the documented order *and* each section non-empty — chose strict
  positional parsing (`str.find` + slicing) over regex for
  readability, since the format is simple and linear.
- `backend/scripts/test_post_writer.py` — seven checks with a
  `ScriptedProvider` (pre-set response sequence) and a `RaisingProvider`
  (always throws), no network/API key needed: well-formed response
  parses correctly with `sources == [candidate.url]` and the
  fingerprint carried through from the judgment; a response missing a
  marker raises; sections out of order raise; an empty `CONTENT:`
  section raises; a provider exception raises `PostWriteError` without
  leaking the raw exception; a *rejected* `JudgmentResult` raises
  immediately with zero provider calls; and an empty response string
  raises.
- Ran the new script, then re-ran all twelve prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15) — all
  passed, no regressions.

## Decisions Taken

- **Accepted:** `write_post()` takes the full `JudgmentResult`, not a
  bare candidate — grounds the generated rationale in the actual
  editorial acceptance reason and lets misuse (calling this on a
  rejected result) be caught immediately without an LLM call.
- **Accepted:** fail **loud** (`PostWriteError`) on any
  generation/parsing failure — the only sound behavior given there's
  no safe placeholder post, explicitly contrasted with Stage 14's
  fail-closed and Stage 15's fail-open postures in the module
  docstring.
- **Accepted:** strict three-marker (`TITLE:`/`RATIONALE:`/`CONTENT:`)
  plain-text response format, parsed positionally — keeps the
  provider abstraction's `generate(prompt, system) -> str` shape
  (Stage 6) exactly as-is, same rationale as Stage 14's `ACCEPT:`/
  `REJECT:` precedent.
- **Accepted:** `sources` populated with only `[candidate.url]` —
  matches `persona.json`'s `minimum_sources: 1` and the fact that no
  earlier stage's `TopicCandidate` carries more than one URL; explicit
  scope note added rather than silently building partial
  source-aggregation logic.
- **Deferred:** persisting the `WrittenPost` to the `posts` table and
  pushing a summary fact to Breeth — Stage 17's publisher.
- **Deferred:** wiring `write_post()` into any route or the
  scheduler — Stage 18, once the scheduler exists.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/post_writer.py`
- `backend/scripts/test_post_writer.py`
- `docs/prompts/17_stage16.md`

## Files Modified
- `README.md` — project status bumped to Stage 16, repo tree updated,
  Stage 16 verification section added.
- `PROJECT_STATUS.md` — Stage 16 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 16 entry appended.

## Git Commit
```
feat(backend): add post writer generating title/content/rationale via LLMFactory, failing loud on malformed output
```

## Stage Outcome
`python3 scripts/test_post_writer.py` (run from `backend/`, venv
active) passes all seven checks with a scripted fake provider — no
real API key needed. Re-ran all twelve prior verification scripts
(Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15) — all pass, no
regressions. Nothing wired into any route or the (not-yet-existing)
scheduler this stage — `write_post()` exists as a standalone,
directly-callable function only, same posture as Stages 12, 14, and 15.

## Next Stage
Stage 17 — Publisher: `publisher.py` — writes a `WrittenPost` (this
stage's output) to the `posts` table, pushes a summary fact to Breeth
via `BreethClient.write_fact()` (Stage 9) so future memory checks
(Stage 15) can find it, and marks the cycle published.
