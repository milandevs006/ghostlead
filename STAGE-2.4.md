# GhostLead — Stage 2.4 Analytics Centre

Apply to the Stage 2.3 journey release on `develop`. Stop the Next.js server. Copy the four files under `frontend/src/app/` into the same directory in your project, and copy `frontend/tests/analytics-model.test.cjs` if you want to run the calculation tests. Only `page.tsx` replaces a previous file; compare with your local version before overwriting custom changes. `globals.css` is intentionally untouched, including your journey light-theme fix. No database, backend, accounts, imports, or journey data are changed. Do not replace the entire frontend directory.

Existing dependencies: Next.js, TypeScript, lucide-react, echarts, echarts-for-react, and the dependencies already installed for Stage 2.3. No new libraries are needed. In frontend, run `npx tsc --noEmit`, then `npm run build` and `npm run dev`. Start FastAPI in the repository root using your existing Python environment (`python -m uvicorn app.main:app --reload`). Open localhost:3000 and select Analytics. Check website/date filters, no-data states, search, sorting, and CSV export. Existing pages should still work.

Analytics are computed in memory from the authenticated workspace endpoint. Calendar days and the heatmap use UTC. Source events are included within the selected interval; matching uses an identical website and event identifier, and destination timestamps before the exclusive end. Earlier destination timestamps are counted as identifier matches but excluded from delay calculations. Unmatched identifiers are not necessarily lost leads. No sales conversion or revenue amount is inferred. Monitor durations are distinct from source-to-destination delay. Percentiles use nearest-rank. Pass rate is passed/all recorded checks including inconclusive. Only observed heatmap cells are coloured. Website exports reflect scope, search and sort. The current architecture loads full workspace records and should be replaced with server-side aggregation/pagination before high-volume production use.

Optional calculation test (PowerShell from frontend; output outside repository):

```powershell
npx tsc src/app/analytics-model.ts --strict --target es2020 --module commonjs --skipLibCheck --outDir "$env:TEMP/ghostlead-analytics-test"
node tests/analytics-model.test.cjs "$env:TEMP/ghostlead-analytics-test/analytics-model.js"
```

The calculation test uses isolated in-memory fixtures only; no runtime imports or seeded records. Model strict type-check, calculation tests, TSX syntax transpilation, and CSS parse were verified in the packaging environment. Full Next.js dependency-aware build and browser checks must be performed locally. This patch is based on the last delivered Stage 2.3 source, not a fresh checkout of the private repository. No demo data is shipped as workspace data.
