# GhostLead Stage 2.5 — Advanced Data Imports

Patch for the last delivered Stage 2.4 frontend and Stage 2.3 backend. No data or schema changes. Stop both servers, back up your data directory outside Git, and compare any local source edits before copying files. Preserve globals.css, the journey builder, analytics files, and database. Copy only the paths in this archive into the project root.

## Setup (Windows PowerShell, existing Python environment)

From D:\ghostlead:

    python -m pip install openpyxl==3.1.5 defusedxml==0.7.1
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

In another terminal:

    cd D:\ghostlead\frontend
    npx tsc --noEmit
    npm run build
    npm run dev

Visit http://localhost:3000, select Data imports. Choose a record type and file, Validate & preview, inspect the first 10 rows, then Confirm import. Preview rolls back all tentative writes; confirmation validates again and commits records and import history atomically. Validation stops at first invalid row. No seeded data, no automatic imports.

## Formats and limits

CSV: UTF-8, first row exact field names. XLSX: one worksheet, first row exact field names; use text cells for identifiers and timezone-aware ISO 8601 timestamps, integers for latency_ms. No formulas, macros, embedded objects, or legacy XLS. JSON: array of objects, exact fields, text values except integer latency_ms or null for optional latency_ms/detail. Download header-only CSV template from the UI. Each file must be <=1 MB and <=10,000 rows. The server also caps XLSX expanded size. Import websites before monitors and lead events/results. Duplicates reject the whole file. Existing legacy CSV endpoint unchanged.

## Testing

Backend lifecycle and multi-format tests passed in an isolated copy. To run on your machine, from project root install requirements-dev.txt if needed, then python -m pytest -q. TSX syntax checked; full Next.js build and browser interaction not run in build environment. This is a local starter patch, not a public production security audit. No database or customer records included.
