# Stage 13 — Fingerprinting

## Goal
A normalized title+keywords+source → fingerprint function,
unit-testable, per the 20-stage plan — distinct from Stage 12's
literal URL-hash dedup, meant to catch the same underlying story
republished under a different URL or title variant.

---

## Prompt(s)

User: "now go for 13" (after Stage 12's `aether-stage12.zip`, with
`PROJECT_STATUS.md` reattached to restore context).

---

## AI Response Summary

- Re-read `PROJECT_STATUS.md` and unzipped the supplied
  `aether-stage12.zip` to confirm the actual state of the repo (rather
  than trusting the status doc's stage number alone, since the
  document itself notes it may be stale) — confirmed the zip matches
  "Stage 12 done" and that `sources_cache_service.py`'s docstring
  already names Stage 13's job precisely: "normalized title + keywords
  + source, meant to catch the same underlying story republished under
  a different URL/title variant."
- Reviewed `topic_discovery.py`'s `TopicCandidate` dataclass and
  `sources_cache_service.py`'s `compute_content_hash()` before writing
  anything, to match existing code style (module docstrings that state
  scope boundaries explicitly, small pure functions, SHA-256 over a
  pipe-joined basis string) and to make sure this stage's fingerprint
  is clearly differentiated from Stage 12's hash rather than
  duplicating it.
- `extract_keywords()`: tokenizes with a simple `[a-z0-9]+` regex
  (lowercased first), strips a short hand-picked stopword list, dedupes
  while preserving first-seen order, caps at `MAX_KEYWORDS=8`. Title
  tokens come before summary tokens so the title (the strongest
  "what is this story" signal) fills the keyword budget first.
- `normalize_source()`: strips everything but lowercase alphanumerics,
  so `"Hacker News (AI/ML)"` and `"hackernews-ai-ml"` normalize
  identically — protects the fingerprint from source-name formatting
  drift in `topic_sources.json` over time.
- `compute_fingerprint()`: SHA-256 over `normalized_source + "|" +
  "|".join(sorted(keywords))`. Sorting the keywords (unlike Stage 12's
  raw, order-sensitive `source_name|url` hash) is the key design
  choice — it's what makes a reworded or reordered headline for the
  same story, same source, collapse to the same fingerprint, which is
  exactly the gap Stage 12's docstring named as out of its scope.
- `fingerprint_candidate()` added as a thin convenience wrapper over
  a `TopicCandidate`, matching the pattern of Stage 12's functions
  operating directly on candidates.
- `backend/scripts/test_fingerprinting.py` — seven checks, no DB
  needed since fingerprinting doesn't touch persistence this stage:
  determinism; the core "reworded/reordered title, same story+source"
  collapse case; a genuinely different story not colliding; the same
  title from a different source not colliding; stopword stripping and
  `max_keywords` capping; source-name normalization; and
  `fingerprint_candidate()` agreeing with a direct
  `compute_fingerprint()` call.
- Ran the new script, then re-ran all nine prior verification scripts
  (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12) — all passed, no regressions.

## Decisions Taken

- **Accepted:** keyword-set (sorted, deduped) fingerprint over a
  literal title hash — a literal hash of the title string would
  reintroduce exactly the problem this stage exists to solve (any
  rewording breaks it); sorted keywords is the simplest thing that
  actually catches reordered/reworded variants of the same story.
- **Accepted:** small hand-picked stopword list over an NLP library
  dependency — the PRD scope (`PROJECT_STATUS.md` §2) rules out
  heavier infrastructure like a vector DB, and headline-style titles
  don't need general-purpose NLP; a short stopword list is enough to
  strip the noise words that would otherwise pad every keyword set.
- **Accepted:** `MAX_KEYWORDS=8` cap — arbitrary but reasonable; keeps
  the fingerprint stable against a couple of extra trailing words in a
  longer title/summary variant of the same headline, while eight
  keywords is still specific enough that two different stories on the
  same broad topic (e.g. two different LLM releases) won't share every
  keyword and collide.
- **Accepted:** `_MIN_KEYWORD_LENGTH = 2` rather than the more typical
  3+ — short but meaningful tech terms ("ai", "ml", "llm") are common
  in this domain and would otherwise be dropped as noise.
- **Deferred:** wiring the fingerprint into `sources_cache` (e.g. an
  additional `fingerprint` column + a lookup alongside Stage 12's
  `content_hash` check) — the stage plan scopes Stage 13 as "a...
  fingerprint function, unit-testable," not the wiring; wiring
  near-duplicate rejection into the actual dedup/judgment path belongs
  with Stage 14 (Editorial Judgment) and/or Stage 15 (Memory Service),
  which are where "should this be published" decisions are made.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/fingerprint.py`
- `backend/scripts/test_fingerprinting.py`
- `docs/prompts/14_stage13.md`

## Files Modified
- `README.md` — project status bumped to Stage 13, repo tree updated,
  Stage 13 verification section added.
- `PROJECT_STATUS.md` — Stage 13 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 13 entry appended.

## Git Commit
```
feat(backend): add title+keywords+source fingerprinting for near-duplicate detection
```

## Stage Outcome
`python3 scripts/test_fingerprinting.py` (run from `backend/`, venv
active) passes all seven checks — pure unit tests, no DB required.
Re-ran all nine prior verification scripts (Stages 2, 5, 6, 7, 8, 9,
10, 11, 12) — all pass, no regressions. Nothing wired into
`sources_cache`, any model, or any route this stage — `fingerprint.py`
exists as a standalone, directly-callable module only.

## Next Stage
Stage 14 — Editorial Judgment: `editorial_judgment.py`, deciding
accept/reject for each newly-discovered (and now fingerprintable)
candidate, with rejections logged to `rejected_topics`.
