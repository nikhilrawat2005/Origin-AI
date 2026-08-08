# Stage 17 — Publisher

## Goal
`publisher.py` — writes a `WrittenPost` (Stage 16's output) to the
`posts` table, pushes a summary fact to Breeth, and marks the cycle
published, per the 20-stage plan.

---

## Prompt(s)

User: "stage 17 now" (after approving Stage 16's `aether-stage16.zip`).

---

## AI Response Summary

- Re-read `agent_service._create_breeth_namespace()` (Stage 10) before
  designing anything, since it's the only other place in the codebase
  that already writes to Breeth on behalf of an agent. Its docstring
  states the exact pattern this stage needed: a best-effort remote
  write wrapped in a broad try/except, with a `BreethMirrorFact` row
  written locally *regardless* of whether the remote write actually
  succeeded (`synced` records the true outcome). Decision: reuse this
  pattern verbatim rather than inventing a different one for
  publishing — consistency across the two places in the codebase that
  talk to Breeth matters more than any marginal improvement a
  from-scratch design might offer.
- Cross-checked against Stage 15's `memory_service.py` docstring
  again: its local-mirror fallback path explicitly depends on
  `breeth_mirror_facts` actually containing rows to scan, and notes
  it "will typically find nothing until Stage 17's publisher starts
  writing post-published facts into it." This stage is exactly that —
  confirms the mirror-write isn't optional polish, it's required for
  Stage 15's own documented fallback to ever have data.
- Decision: the mirrored/pushed fact's `object` field is the post's
  own title, not a generic placeholder like `"a topic"`. Directly
  driven by re-reading Stage 15's `_edge_text()` and
  `_check_local_mirror_fallback()`: both extract keywords from
  whatever text is in the `object` field and compare against a future
  candidate's title/summary keywords — a generic object string would
  make Stage 15's whole semantic-dedup layer silently useless once
  wired together in Stage 18.
- Decision: treat the local `Post` write and the remote Breeth write
  asymmetrically on purpose, and say so explicitly in the docstring —
  the `Post` row is a plain required DB write (no fail-open/fail-closed
  framing needed, same as Stage 2's models or Stage 14's
  `rejected_topics`), while only the Breeth call gets the
  best-effort/mirror treatment. This avoids over-generalizing Stage
  15's "fail open on Breeth" framing to a context (a local DB insert)
  where it doesn't actually apply.
- Decision: skip the remote Breeth call outright (not just catch a
  failure from it) when `agent.breeth_agent_ref` is `None` — there's
  no `group_id` to write into, so attempting the call would only ever
  raise; short-circuiting avoids a guaranteed-failing network call and
  logs a clearer reason than a generic exception message would. The
  local mirror row still gets written in this case too (with
  `group_id="unassigned"`), keeping the "always mirror locally"
  invariant intact even in this edge case.
- `backend/scripts/test_publisher.py` — six checks against an
  in-memory DB with a `FakeBreethClient` (succeeds or raises, no
  network/API key needed): a persisted `Post` has all the right
  fields and a generated id; a successful Breeth write yields a
  `synced=True` mirror fact with the post's title as `object`; a
  Breeth exception still persists the `Post` and yields a
  `synced=False` mirror fact rather than blocking publishing; an
  agent with no `breeth_agent_ref` skips the remote call (asserted via
  a call counter) but still persists the post and mirrors locally with
  `group_id="unassigned"`; two distinct posts for the same agent
  create two independent rows with no accidental dedup at this layer;
  and a persisted fingerprint round-trips correctly via a direct query
  (kept dependency-free from `memory_service` itself, to keep this
  script's fixtures self-contained per-stage as prior scripts do).
- Ran the new script, then re-ran all thirteen prior verification
  scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16) — all
  passed, no regressions.

## Decisions Taken

- **Accepted:** reuse Stage 10's exact best-effort-remote +
  always-local-mirror pattern for the Breeth "published" fact, rather
  than designing a new approach — consistency with the only other
  Breeth-writing code path in the project, and Stage 15's fallback
  path already assumes this shape exists.
- **Accepted:** mirrored fact's `object` is the post's actual title —
  required for Stage 15's keyword-overlap matching to have anything
  meaningful to compare against once the pipeline is fully wired
  (Stage 18).
- **Accepted:** skip the remote Breeth call (not attempt-then-catch)
  when the agent has no namespace yet, while still writing the local
  mirror row — avoids a guaranteed-failing call and keeps the
  "always mirror" invariant intact regardless of *why* the remote
  write didn't happen.
- **Accepted:** no special fail-open/fail-closed framing for the
  `Post` row write itself — it's a plain required DB write like any
  other model in this codebase; only the Breeth call gets the
  best-effort treatment.
- **Deferred:** anything about *deciding* what to publish or *whether*
  a candidate should reach this stage — entirely Stages 14–16's job;
  this stage assumes it's handed an already-accepted, memory-cleared,
  successfully-written `WrittenPost`.
- **Deferred:** wiring `publish_post()` into any route or the
  scheduler — Stage 18, once the scheduler exists. That's also where
  the full pipeline (discover → judge → memory → write → publish)
  gets chained together and exercised end-to-end for the first time.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `backend/app/services/publisher.py`
- `backend/scripts/test_publisher.py`
- `docs/prompts/18_stage17.md`

## Files Modified
- `README.md` — project status bumped to Stage 17, repo tree updated,
  Stage 17 verification section added.
- `PROJECT_STATUS.md` — Stage 17 entry added, resume pointer bumped.
- `docs/AI_USAGE_LOG.md` — Stage 17 entry appended.

## Git Commit
```
feat(backend): add publisher persisting posts and pushing best-effort published facts to Breeth
```

## Stage Outcome
`python3 scripts/test_publisher.py` (run from `backend/`, venv active)
passes all six checks against an in-memory DB with a fake Breeth
client — no real API key needed. Re-ran all thirteen prior
verification scripts (Stages 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
16) — all pass, no regressions. Nothing wired into any route or the
(not-yet-existing) scheduler this stage — `publish_post()` exists as a
standalone, directly-callable function only, same posture as every
service stage since Stage 12.

## Next Stage
Stage 18 — Scheduler Wiring: chain Stages 11/12 → 14 → 15 → 16 → 17
(`discover_new_topics()` → `judge_candidates()` (accepted only) →
`check_memory_batch()` (not-duplicate only) → `write_post()` →
`publish_post()`) behind APScheduler, driven by
`PUBLISH_INTERVAL_MINUTES` from the environment — the first point
where the full autonomous pipeline actually runs end-to-end.
