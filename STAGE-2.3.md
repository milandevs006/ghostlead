# GhostLead — Stage 2.3: Visual Journey Builder

Patch for the Stage 2.2 Next.js frontend and the original v0.1 FastAPI backend. No database, demo records, package-lock, or credentials are supplied. No paid APIs. This is still a single-owner local development application, not production-ready SaaS.

## Before installation

1. Commit your working Stage 2.2 source on `develop`. Review `git status` and make sure no private records are staged.
2. Stop both development servers. Copy the entire `data` directory to a safe location outside the Git repository (and retain your original database). Never commit the backup. The backup should be made with the backend stopped.
3. Copy these files from the ZIP to the matching paths inside the existing project:
   - `app/main.py` (original backend plus additive journey model/API)
   - `tests/test_app.py` (extended temporary-database tests)
   - `frontend/src/app/page.tsx`
   - `frontend/src/app/globals.css`
   - `frontend/src/app/journey-builder.tsx` (new)
   - `STAGE-2.3.md` (optional guide)
   Review the diff if you have made local source edits. Do not replace the entire `app` or `frontend` folder. Do not replace `data` or `package.json`/`package-lock.json`.
4. In the `frontend` folder, run `npm install @xyflow/react` (the package may already be installed), then `npx tsc --noEmit` and `npm run build`. This patch also uses the existing Motion, Lucide, and ECharts dependencies.
5. From the repository root, optionally install test dependencies using `python -m pip install -r requirements-dev.txt` and run `python -m pytest -q tests/test_app.py`. Tests use an isolated temporary SQLite database; they do not write to your actual data.
6. Start FastAPI from the project root: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`. At startup it automatically creates the new `journey_layouts` table if absent. All existing tables stay unchanged. Start `npm run dev` from `frontend` in a second terminal. Open http://localhost:3000.

## Use the builder

- Select Journey map, then choose a registered website. Each website has its own independent layout, initially empty.
- Enter your own stage name and choose a stage type. Add stages only for the real workflow you want to document.
- Drag stages, connect right handles to left handles, zoom and pan. Select a node or edge to edit or remove it in the inspector.
- Click Save journey. Refresh the page and verify the saved layout reappears. Unsaved changes are not automatically persisted. A warning appears before ordinary page/site changes and browser unload. Stale concurrent saves are rejected; reload before retrying.
- The existing source/destination event summary remains separate. Workflow design does not execute tests or create lead events, monitoring results, or incident records.
- Deleting a website also deletes its saved layout. This follows the original deletion behavior for dependent records.

## Validation

Backend lifecycle tests passed, including journey authorization, empty layout, save/read, invalid edge rejection, stale revision rejection, clearing the layout and cascade delete. An isolated v0.1 -> Stage 2.3 database migration check also passed: an existing login and registered website were preserved and its journey began empty. TypeScript/JSX transpilation syntax and CSS parsing passed. The npm dependency is unavailable in the authoring environment; a complete Next.js type check/build and browser interaction test must be done locally before release. Do not merge into `main` until verified.
