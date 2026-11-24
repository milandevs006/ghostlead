# GhostLead v0.2 — Phase 1 frontend migration

This patch replaces only four files in your existing Next.js frontend. It does not contain a database, account, seeded records, backend changes or npm dependencies. Keep the existing `app`, `data`, `frontend/package.json` and `frontend/package-lock.json` files. Back up your database outside the repository before development. Stop the existing Next.js dev server before copying files.

## Install on Windows

1. Extract the ZIP. Copy the contents of its `frontend` folder into your existing `ghostlead/frontend` folder, replacing the four matching files. Do not replace the whole folder. If you changed these files already, save copies first.
2. In the existing `ghostlead` root, start the backend: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`.
3. In a separate VS Code terminal, from the root: `cd frontend`; `npm install lucide-react echarts echarts-for-react`; `npm run dev`.
4. Open http://localhost:3000 and sign into your existing account. If you used 127.0.0.1 for the original frontend, you may need to sign in again. A first-time setup prompt on an already configured database means you should stop and verify the backend/database path instead of creating another account.
5. The original interface remains accessible at http://127.0.0.1:8000. Both frontends use the same database. Do not expose either server publicly.
6. Stop the Next.js dev server and run `npx tsc --noEmit` and `npm run build` from `frontend`. If the build passes, restart with `npm run dev`.

## What is included

- White-theme responsive layout, existing login/setup/logout, nine workspace screens.
- Real API-backed overview, ECharts daily observations, a read-only customer journey topology, search, record creation/deletion, observation details, CSV imports/exports and reconciliation.
- No sample records or artificial statistics. Counts and statuses come only from the API. No live tests are executed.
- Existing FastAPI REST contract, same-origin Next.js API rewrite, no change to SQLite schema.

## Not yet included

Editable React Flow topology, Excel/JSON imports, automated monitoring, production-grade access control, PostgreSQL, full accessibility review and a public deployment. TypeScript transpilation syntax checks passed; dependency-aware type checking, Next.js production build, browser end-to-end testing and proxy authentication have not been run in the authoring environment. Verify on your machine before merging to main.

## Quick acceptance check

- Sign in with the current owner credentials. Verify the registered website count and the existing website record are unchanged.
- Check that absent results show a dash or an empty state, not fake metrics.
- Check the nine screens and compare counts to the original application.
- If you choose to add real records, confirm that they are visible in both frontends. Do not delete actual records just to test.
- Confirm CSV exports contain only your own records. Never commit your database, secrets or uploaded private records.

## Commit after validation

From the project root, inspect `git status` and `git diff`. Confirm no database or private customer files are staged. Run `git add frontend` then `git diff --cached --stat` and `git diff --cached --name-only`. Commit and push on `develop` only after the checks pass. Do not merge to `main` yet.
