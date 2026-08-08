# Stage 3 — Frontend Skeleton

## Goal
Boot a Next.js (App Router) frontend with exactly the two pages the PRD
allows — Landing and Feed — as static skeletons, with no API calls yet.

---

## Prompt(s)

User: "stage 3 se kam start karo" ("start work from stage 3" — approval to
proceed to Stage 3 after Stage 2 review, resuming from
`PROJECT_STATUS.md` + `aether-stage2.zip`).

---

## AI Response Summary

- Scaffolded `frontend/` as a Next.js 14 App Router project:
  `package.json`, `tsconfig.json`, `next.config.js`, `.gitignore`.
- `app/layout.tsx` — root layout, sets page metadata (title/description),
  imports `globals.css`.
- `app/globals.css` — minimal hand-written dark theme (no UI framework),
  since the PRD explicitly caps frontend scope at two pages and pulling
  in Tailwind/component libraries this early adds dependency weight for
  no benefit yet.
- `app/page.tsx` (Landing) — project name, persona placeholder
  ("Not yet initialized"), description, static "Not Initialized" status
  badge, and a **disabled** Initialize button. Button is intentionally
  inert — it's wired to `POST /api/agent/init` in Stage 4, not now.
- `app/feed/page.tsx` (Feed) — static empty-state card
  ("No posts yet..."). Wired to `GET /api/agent/feed` in Stage 19.
- Simple top nav (Landing / Feed) shared via `globals.css`, no separate
  nav component yet — only two links, doesn't earn its own file at this
  size.
- Verified the skeleton actually builds: `npm install` then
  `npx next build` — both routes compiled and prerendered as static
  content with zero errors. Removed `node_modules` and `.next` before
  packaging the ZIP.

## Decisions Taken

- **Accepted:** Plain CSS over Tailwind/component library — PRD caps
  the frontend at two pages with no dashboard/analytics/settings, so a
  styling framework is scope creep at this stage. Revisit only if a
  later stage's UI complexity actually demands it.
- **Modified:** Pinned `next` to `14.2.35` instead of the originally
  planned `14.2.5` — `14.2.5` carries a known security advisory
  (see Next.js security update, Dec 2025); `14.2.35` is the latest
  patched release on the same major/minor line, so no other behavior
  changes.
- **Accepted:** Initialize button rendered `disabled` rather than wired
  to a stub/fake handler — PRD Stage 3 scope is explicitly "no API
  calls yet"; a fake handler would misrepresent what's actually wired.
- **Deferred:** No shared `<Nav>` component, no design tokens file —
  two links and a handful of CSS variables don't yet justify the
  abstraction; will factor out if Stage 19's Feed page rendering adds
  real complexity.
- **Rejected:** nothing proposed was rejected this stage.

## Files Created
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/next.config.js`
- `frontend/.gitignore`
- `frontend/app/layout.tsx`
- `frontend/app/globals.css`
- `frontend/app/page.tsx`
- `frontend/app/feed/page.tsx`

## Files Modified
- `README.md` — project status bumped to Stage 3, frontend run
  instructions added.

## Git Commit
```
feat(frontend): bootstrap Next.js app router skeleton with Landing and Feed pages
```

## Stage Outcome
`npx next build` inside `frontend/` compiles cleanly and prerenders both
`/` and `/feed` as static routes. `npm run dev` boots the dev server on
`http://localhost:3000` with a working Landing page and Feed page — no
backend calls made, matching Stage 3 scope exactly.

## Next Stage
Stage 4 — `POST /api/agent/init` (basic): creates an `agent` row in
SQLite and returns `agentId`. No persona/LLM logic yet — that's Stage 5
onward.
