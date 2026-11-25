# GhostLead Stage 2.2 — White theme refinement (preview)

This patch is based on the previously delivered Phase 1 frontend source, not a fresh checkout of your GitHub repository. It replaces only `frontend/src/app/page.tsx` and `frontend/src/app/globals.css`. If you edited either locally, review and merge the changes rather than overwriting your work. No database, backend, demo records or configuration secrets are included.

## Install

1. Make sure you are on `develop` with a clean working tree. Stop the Next.js server with Ctrl+C. Keep the existing backend and database intact.
2. Extract the ZIP and copy the two files into your existing project's `frontend/src/app/` folder. Leave `layout.tsx`, `next.config.ts`, package files and the backend unchanged.
3. In the frontend directory, run `npm install motion` (or keep the already installed package), `npx tsc --noEmit`, then `npm run build`. If either command fails, do not commit yet.
4. Run `npm run dev`. Keep FastAPI running separately from the project root with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`. Visit http://localhost:3000.

## Changes

- White and navy design with refined hierarchy, scope strip, compact metrics, real workspace readiness progress and a redesigned journey topology.
- Motion page transitions (reduced motion preference respected), desktop sidebar collapse, mobile navigation dismissal, command search (Ctrl+K / Cmd+K), and a slide-out observation details drawer.
- ECharts visual styling and date selector; no fabricated chart values. Navigation and search use actual pages, websites and monitors, not external services.
- The existing API, authentication, imports, deletion, reconciliation and export implementation are retained. No new automated monitoring is introduced.

## Check before committing

- Sign in using your existing account; compare website counts and data with v0.1 and Phase 1. Empty metrics should remain blank where no observations exist.
- Use the sidebar, collapse/expand control, search for a real registered site, switch date ranges and choose a site in the journey panel.
- Test record workflows using your own data; only inspect an observation drawer if a real record exists. No test or demo records are required.
- Check the responsive layout, keyboard navigation and reduced motion. This patch has not been fully accessibility-audited.
- TypeScript/JSX transpilation syntax checked in the authoring environment; full dependency-aware build, browser testing and regression testing must be performed on your laptop. The original source baseline was inspected but the remote GitHub commit was not independently fetched.

## Scope

Editable React Flow workflows, richer ECharts analytics, Excel/JSON import, full incident lifecycle, and automated monitoring are not part of this patch. The UI remains a local development preview, not production-ready. No new backend or schema migrations are required.

After acceptance, inspect `git diff` and `git status`; stage the two changed frontend files and any updated package.json/package-lock.json. Keep private data out of Git. Commit on `develop`, not `main`.
