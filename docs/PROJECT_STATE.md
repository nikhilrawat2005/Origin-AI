# Aether — Project State

Quick-resume file. If context resets, read this first, then
`PROJECT_STATUS.md` for full background.

## Current Stage

Post-Hackathon — Stage 20 complete + full bug fixes, discovery expansion,
UI overhaul, responsive design, and autonomous batching features applied.

## Completed Stages

Stages 1–20 complete (see `docs/prompts/` for stage-by-stage build history),
plus post-hackathon hardening pass, plus the **2026-08-09 session** which:

### Bug Fixes
- **Bug #1 (Critical):** Fixed `on_startup()` in `main.py` to check
  `agent.status == "active"` before auto-resuming the scheduler.
  Paused agents now stay paused across Railway restarts/redeploys.
- **Bug #2:** Expanded `topic_sources.json` from 8 → 14 sources.
  Added `hitsPerPage=50` to HN Algolia. Added Reddit ML/LocalLLaMA RSS,
  TechCrunch AI, Ars Technica. Added custom `User-Agent` to `httpx.Client`.
- **Bug #3:** Documented Railway persistent volume setup in `DEPLOYMENT.md`
  (`/app/data/aether.db`) to preserve DB across redeploys.

### New Features
- **Batch Capping:** `judge_candidates()` now accepts `max_accepts=N`.
  Each publish cycle caps at **5 accepted posts** — fast 10-15s execution
  instead of 3-4 minute 146-LLM-call exhaustion runs.
- **Countdown Timer:** `GET /api/agent/status` now returns `nextRunTime`
  (ISO timestamp from APScheduler). Frontend shows live reverse countdown
  `⏱ Next Autonomous Cycle Slot In: MMm SSs`.
- **Sources Pop-Out Modal:** Ingestion Network dashboard card opens a
  glassmorphic modal listing all 14 configured sources when clicked.

### UI/UX Overhaul
- **Fonts:** `Fraunces` serif (headings) + `Plus Jakarta Sans` (body).
- **Home Page:** Cinematic hero, 3-column stats dashboard, agent control
  card with countdown, 3-step pipeline architecture visual.
- **Feed Page:** Magazine editorial post cards, smart title extraction,
  animated rationale accordion, Live Sync pill badge above heading.
- **Responsive:** Full breakpoints for Mobile (≤480px), Tablet (≤768px),
  and Desktop.

## Current Objective

System is live on Railway. Autonomous publish cycle runs every 30 minutes,
publishing up to 5 high-quality AI/ML research posts per cycle from 14
configured ingestion sources.

## Current Branch

`main` — all changes committed and pushed to `https://github.com/Pranjal6804/aether.git`

## Known Issues / Limitations

- `Reddit r/LocalLLaMA` RSS occasionally returns `429 Too Many Requests`
  — handled gracefully (logged as WARNING, source skipped for that cycle).
- `VentureBeat AI` RSS returns `308 Permanent Redirect` — httpx does not
  follow redirects by default, so this source is skipped. Fix: add
  `follow_redirects=True` to `httpx.Client` if needed.
- Editorial judgment is deliberately strict — expect ~5-15% accept rate
  from raw candidates, which is by design.

## Next Steps (Optional Polish)

1. Add `follow_redirects=True` to `httpx.Client` for redirect-following
   sources like VentureBeat.
2. Consider adding a `cycle_number` field to posts for clean Feed UI
   timeline grouping (each group of 5 = one cycle).
3. Feed page UI separator between different publish cycle batches.
