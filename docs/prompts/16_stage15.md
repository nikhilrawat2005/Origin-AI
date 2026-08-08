# Stage 15 — Memory Service (Breeth Dedup)

## Goal
`memory_service.py` — query Breeth (plus the SQLite mirror) for
previously *published* topics before an editorially-accepted candidate
reaches Stage 16's post writer, per the 20-stage plan and Stage 14's
own docstring, which explicitly deferred this layer.

---

## Prompt(s)

User: "now go for stage 15" (after uploading `aether-stage14.zip` and
`PROJECT_STATUS.md`).

---

## AI Response Summary

- Unzipped and inspected the delivered `aether-stage14.zip` directly
  rather than trusting `PROJECT_STATUS.md` alone, to confirm the
  actual on-disk state (models, services, prior scripts) matched what
  the resume doc claimed before writing anything new.
- Re-read `RejectedTopic`'s Stage 2 docstring, `BreethMirrorFact`'s
  Stage 10 docstring, and `editorial_judgment.py`'s Stage 14 docstring
  together: Stage 10's docstring explicitly says "Stage 15's
  memory_service has a local fallback to query against if a live
  Breeth search call fails" — so the local-mirror-fallback design
  wasn't something to invent from scratch, it was already scoped two
  stages earlier. Stage 14's docstring confirmed the split: "(Not this
  stage) checking Breeth for *published* topics — that's Stage 15's
  memory service."
- Reviewed `Post`'s Stage 2 docstring/model: `fingerprint` was already
  a column ("used for dedup against future topic candidates") but
  unused by anything until now — decision: make the local
  `posts.fingerprint` lookup Layer 1, authoritative, and checked
  first, since it's free (no network) and exact.
- Reviewed `BreethClient.search()` (Stage 9): returns a raw dict with
  an `edges` key confirmed by the connection test, but no pinned-down
  edge shape beyond that. Decision: read edges defensively
  (`_edge_text()` checks several plausible key names rather than
  assuming one schema) instead of coupling tightly to an unconfirmed
  structure.
- Main design decision this stage: **fail open**, not fail closed, on
  Breeth specifically — the opposite posture from Stage 14's editorial
  judgment. Justification: Stage 14 fails closed because an ambiguous
  *editorial* call should default to *not publishing* (matches the
  persona's "reject more than it accepts" value). But a Breeth
  *infrastructure* outage has nothing to do with whether a topic is
  actually a duplicate — treating "Breeth is down" as "assume
  duplicate" would silently starve the feed for a reason unrelated to
  content quality, directly undermining the PRD's "feed must grow on
  its own" success criterion. `PROJECT_STATUS.md`'s own "Known
  Constraints" #2 (no real `BREETH_API_KEY` in this sandboxed
  environment) makes this not just a theoretical edge case but the
  expected default state during local dev.
- `_check_breeth_semantic()` returns `None` (not a `(bool, str)` tuple)
  specifically to signal "the call itself failed" as distinct from
  "the call succeeded and found nothing" — `check_memory()` uses that
  `None` sentinel to decide whether to fall back to the local mirror,
  keeping the two failure/success paths structurally distinct rather
  than overloading a boolean.
- `SEMANTIC_OVERLAP_THRESHOLD = 0.6` chosen as a deliberately generous
  fuzzy-match threshold — this layer's whole purpose is catching what
  Stage 13's exact fingerprint match structurally cannot (a reworded
  story from a different source), so it needs looser matching than a
  hash comparison, at the cost of being a soft/heuristic signal rather
  than a guarantee (documented plainly in the module docstring so a
  future stage doesn't mistake it for authoritative).
- `check_memory_batch()` added as the batch entry point, matching the
  shape `judge_candidates()` (Stage 14) already returns, so Stage 18's
  eventual scheduler chain reads as a straight pipeline:
  `discover_new_topics()` → `judge_candidates()` (accepted only) →
  `check_memory_batch()` (not-duplicate only) → post writer.
- `backend/scripts/test_memory_service.py` — seven checks against an
  in-memory DB with a `FakeBreethClient` (scripted response or forced
  exception, no network/API key needed): Layer 1 fingerprint match
  short-circuits with zero Breeth calls; a genuinely new candidate
  passes with no matching edges; a semantically similar edge (real
  keyword overlap between a candidate's title/summary and a fake
  edge's text) is flagged; a Breeth exception falls back to the local
  mirror and, with the mirror empty, fails open; a Breeth exception
  *plus* a matching synced mirror fact still correctly flags a
  duplicate through the fallback; an agent with no
  `breeth_agent_ref` yet skips the semantic check without calling
  Breeth; and `check_memory_batch()` preserves order across a batch.
- Ran the new script, then re-ran all eleven prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) — all passed,
  no regressions.

## Decisions Taken

- **Accepted:** two-layer design — authoritative local
  `posts.fingerprint` match first, soft Breeth semantic search second
  — rather than relying on Breeth alone, since local dev in this
  sandboxed environment has no real `BREETH_API_KEY` and the exact
  case (same agent, same story, reworded) is both the most common
  duplicate and the cheapest to catch without any network call.
- **Accepted:** fail **open** on Breeth failures specifically —
  directly justified by `PROJECT_STATUS.md`'s "Known Constraints" #2
  and the PRD's "feed must grow on its own" success criterion; an
  infrastructure outage must never look like "reject everything."
  This is a deliberate asymmetry with Stage 14's fail-closed editorial
  judgment, called out explicitly in the module docstring so it reads
  as an intentional design choice, not an inconsistency.
- **Accepted:** local `breeth_mirror_facts` fallback on Breeth
  failure, per `BreethMirrorFact`'s own Stage 10 docstring reserving
  this exact use — even though it will typically find nothing until
  Stage 17's publisher starts writing post-published facts into it.
- **Accepted:** defensive, key-agnostic parsing of Breeth's `edges`
  (`_edge_text()`) rather than assuming a specific schema, since
  nothing beyond the `edges` key itself has been confirmed live
  against the real API in this project so far.
- **Deferred:** writing post-published facts into `breeth_mirror_facts`
  itself — that's Stage 17's publisher; this stage only *reads* from
  that table as a fallback.
- **Deferred:** wiring `check_memory_batch()` into any route or the
  scheduler — Stage 18, once the scheduler exists.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/memory_service.py`
- `backend/scripts/test_memory_service.py`
- `docs/prompts/16_stage15.md`

## Files Modified
- `README.md` — project status bumped to Stage 15, repo tree updated,
  Stage 15 verification section added.
- `PROJECT_STATUS.md` — Stage 15 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 15 entry appended.

## Git Commit
```
feat(backend): add memory service with local fingerprint + Breeth semantic dedup against published topics, failing open on Breeth
```

## Stage Outcome
`python3 scripts/test_memory_service.py` (run from `backend/`, venv
active) passes all seven checks against an in-memory DB with a fake
Breeth client — no real API key needed. Re-ran all eleven prior
verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) —
all pass, no regressions. Nothing wired into any route or the
(not-yet-existing) scheduler this stage — `check_memory()`/
`check_memory_batch()` exist as standalone, directly-callable
functions only, same posture as Stages 12 and 14.

## Next Stage
Stage 16 — Post Writer: `post_writer.py` — generate post text +
rationale via `LLMFactory`, given a judged-accepted, memory-cleared
topic candidate (the output of Stage 14 + Stage 15 combined).
