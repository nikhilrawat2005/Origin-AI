# Stage 12 — Sources Cache

## Goal
Wire `sources_cache` into the discovery path — dedup fetch, hash
check — per the 20-stage plan.

---

## Prompt(s)

User: "continue" (after approving Stage 11's `aether-stage11.zip`).

---

## AI Response Summary

- Reviewed the `SourceCache` model (Stage 2): `content_hash` is
  already `unique=True, index=True`, so the model was designed with
  this stage's dedup-by-hash approach in mind from the start.
- `compute_content_hash()` hashes `source_name + "|" + url` (SHA-256)
  rather than title — reasoning: the same URL from the same source
  fetched twice is always the same feed entry (a re-fetch of an
  unchanged feed), whereas two different stories from the same source
  could plausibly share very similar titles without being duplicates.
  Explicitly scoped narrower than Stage 13's planned fingerprinting
  (normalized title + keywords + source), which is meant to catch the
  *same underlying story* republished under a different URL — this
  stage only needs literal-URL-level dedup to stop re-caching/re-
  considering identical feed entries across scheduler runs.
- `filter_new_candidates()` checks candidates one at a time against
  the DB (not a single bulk `IN` query), specifically so that two
  candidates within the *same* discovery batch that hash identically
  (e.g. a feed listing the same item twice, or two sources returning
  overlapping content) don't both get inserted — the first occurrence
  claims the hash in the session, the second is filtered out against
  that now-updated state before the batch is committed.
- `discover_new_topics()` added as the single combined entry point
  (`discover_topics()` + `filter_new_candidates()`) that later stages
  will actually call — not wired into any route or scheduler yet,
  since neither exists until Stage 18.
- `backend/scripts/test_sources_cache.py` — four checks against an
  in-memory DB: hash determinism and sensitivity to both url and
  source; first-call caching of all new candidates; a repeat call with
  identical candidates returning nothing and creating no duplicate
  rows; a mixed batch (one already-cached candidate, one genuinely new
  candidate, and one in-batch duplicate sharing a URL with the new
  one) correctly returning exactly one new candidate and creating
  exactly one new row.
- Ran the new script, then re-ran all eight prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11) — all passed, no regressions.

## Decisions Taken

- **Accepted:** hash over `source_name + url` rather than title or
  full content — matches what `content_hash`'s `unique=True` was
  clearly designed to enforce, and keeps this stage's scope to literal
  re-fetch dedup rather than reaching into Stage 13's territory.
- **Accepted:** per-candidate DB lookups over a single batch query —
  correctness (no duplicate rows even within one batch) mattered more
  here than the minor query-count cost, especially since batch sizes
  from `discover_topics()` are small (tens of items, not thousands).
- **Accepted:** `discover_new_topics()` as a thin combining function
  now, even though nothing calls it yet — gives Stage 18 a single,
  already-tested entry point to wire into the scheduler chain instead
  of composing `discover_topics()` + `filter_new_candidates()` calls
  itself at that point.
- **Deferred:** fingerprint-based near-duplicate detection (same story,
  different URL/title) — Stage 13, as planned.
- **Deferred:** no expiry/pruning of old `sources_cache` rows — not
  called for by the PRD or the stage plan; the table is expected to
  grow unbounded for now, matching the "posts, rejected topics,
  publishing history" memory requirements language in
  `PROJECT_STATUS.md` §7, which doesn't mention pruning.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/sources_cache_service.py`
- `backend/scripts/test_sources_cache.py`
- `docs/prompts/13_stage12.md`

## Files Modified
- `README.md` — project status bumped to Stage 12, repo tree updated,
  Stage 12 verification section added.
- `PROJECT_STATUS.md` — Stage 12 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 12 entry appended.

## Git Commit
```
feat(backend): wire sources_cache into discovery for URL-level dedup
```

## Stage Outcome
`python3 scripts/test_sources_cache.py` (run from `backend/`, venv
active) passes all four checks against an in-memory SQLite DB. Re-ran
all eight prior verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11)
— all pass, no regressions. No routes touched, nothing wired into
`/init` or the (not-yet-existing) scheduler this stage —
`discover_new_topics()` exists as a standalone, directly-callable
function only, same posture as Stage 11's `discover_topics()`.

## Next Stage
Stage 13 — Fingerprinting: a normalized title + keywords + source ->
fingerprint function, unit-testable, to catch the same underlying
story appearing under a different URL or title variant — a level of
dedup this stage's literal URL-hash approach explicitly doesn't cover.
