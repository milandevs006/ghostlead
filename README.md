# GhostLead · v0.1.0

A local-first foundation for a future commercial lead-integrity platform. The approved design uses white surfaces, steel-blue charts, midnight navy typography, a persistent sidebar, a journey topology and distinct workspace views. It is a working application, not a static dashboard or a public production service.

## Start on Windows

1. Install Python 3.11–3.13 from https://www.python.org/downloads/ (enable **Add Python to PATH**). An Internet connection is needed on the first dependency installation. No paid APIs, accounts or hosting are required.
2. Extract the entire ZIP into a folder you own, such as Documents\GhostLead.
3. Double-click `start-windows.bat`. On first launch it creates a virtual environment and installs dependencies. Keep the command window open.
4. Open http://127.0.0.1:8000 in Chrome or Edge. Create your own workspace, email and password (12 characters minimum).
5. Open **Data imports** or add a website manually. The database starts entirely empty.

To stop the server, press Ctrl+C in the command window. Double-click the launcher again to resume. The virtual environment and database persist in your extracted folder.

### Manual startup (PowerShell)

From the extracted `ghostlead` directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If port 8000 is occupied, change it to 8001 and open the matching URL. If `py` is not available on Windows, substitute `python`. The app uses local CSS and JavaScript and has no CDN dependencies.

## Data ownership and import workflow

**No seed script, no sample records, no pre-created account, no database file in the distribution.** The backend creates its schema automatically. Only your authenticated manual entry and imports create business records. The only other generated records are account/session metadata, creation timestamps and import history.

1. Register or import websites.
2. Create or import monitors referencing exact existing website URLs.
3. Record or import actual monitor observations.
4. Import lead events from source and destination records.
5. Review Overview, Journey map, Lead explorer and Incidents. Export CSV in Reports.

Download header-only templates in the Data imports page or use `templates/`. Fill them with your own data; do not import blank files. CSV files must contain UTF-8 text, the exact headers (any order), up to 10,000 rows and up to 2 MB. Invalid rows and duplicates reject the entire batch. No silent overwrites. For values containing commas or line breaks, use properly quoted CSV fields. Excel users should save as CSV UTF-8. XLSX is not supported in this release.

| Import type | Columns | Rules |
| --- | --- | --- |
| Websites | `name,url` | Unique full HTTP(S) URL, no fragments/credentials; trailing slash removed. |
| Monitors | `website_url,name,kind` | Unique name per website; existing URL. Kind: Contact form, Booking flow, CRM delivery, Webhook, Website availability, Other. |
| Monitor results | `website_url,monitor_name,observed_at,status,latency_ms,detail` | Existing monitor; ISO 8601 timestamp with timezone; status `passed`, `failed`, `inconclusive`. Optional latency is integer milliseconds; detail up to 2000 chars. Unique monitor/timestamp. |
| Lead events | `website_url,event_key,stage,observed_at` | Existing website; opaque shared key; stage `source` or `destination`; ISO 8601 timestamp with timezone; unique site/key/stage. |

`observed_at` format: `YYYY-MM-DDTHH:MM:SSZ` or a timestamp with explicit UTC offset. The backend normalises timestamps to UTC. Manual-entry date/time fields use the browser's local timezone. Website URL and monitor name must match the registered values. Avoid personal names, phone numbers, emails, payment details, secrets or sensitive data in event IDs and evidence fields.

## How metrics are calculated

- **Registered websites:** count of website records.
- **Check pass rate:** passed / (passed + failed) for selected period; inconclusive excluded from denominator. No conclusive results displays an em dash, not a fake 0% or 100%.
- **Lead match rate:** fraction of source identifiers observed during the selected period for which any corresponding destination event exists in the uploaded records. It is not a measured real-world delivery rate.
- **Open incidents:** monitors whose latest uploaded result is failed. A later inconclusive result makes the latest state inconclusive; a later passed result shows a recorded pass. This does not certify current health or actual resolution. Historical observations remain until deleted.
- **Journey topology:** counts of unique source and destination identifiers and exact matches, all-time or per website.
- **Lead explorer:** joins records using exact website and event identifier. Source-only or destination-only means unmatched in the supplied data, not necessarily missing or lost leads.
- **Chart:** counts of observations per UTC day, up to the 60 most recent observed dates in the selected period. No invented time series.

The dashboard refreshes on save/import/delete and on demand. It does not run background scans or live push updates. There are no paid integrations or fabricated results.

## Technical architecture

- FastAPI / Python: authenticated JSON API, validation, explicit data endpoints.
- SQLAlchemy 2: relational data model, foreign keys, uniqueness, atomic import transaction.
- SQLite: persistent local database. `GHOSTLEAD_DATABASE_URL` allows alternate SQLAlchemy URLs, but PostgreSQL needs a driver and migration/compatibility testing before adoption.
- Native HTML/CSS/modern JavaScript: responsive custom design, SVG analytical visualisations, accessible native dialogs, filterable tables. No frontend build step, no CDN, no paid UI libraries. Next.js/TypeScript were considered but npm access was unavailable in the build environment; this release uses a locally testable frontend with a separate JSON API. It can be replaced by Next.js later.
- Argon2: password hashing. Random session tokens stored as hashes; HttpOnly, SameSite=Strict cookies, seven-day expiration. Same-origin custom-header mutation checks and no CORS configuration. Basic local login throttling.
- No outbound requests or autonomous browser tests from the app. Registering a URL stores it only.

```
ghostlead/
  app/
    main.py           # API, database model, validation, authentication
    static/
      index.html      # app shell
      style.css       # GhostLead design system
      app.js          # interface, charts, forms, CSV exports
  templates/          # headers only; no rows
  tests/test_app.py   # isolated lifecycle test (temporary database)
  requirements.txt
  requirements-dev.txt
  start-windows.bat
  README.md
  ROADMAP.md
  .gitignore
```

## Storage, backups and deletion

The first launch creates `data/ghostlead.db`. This is your real local database. Do not commit it to source control or share it publicly. For a complete backup, stop the application and copy the database file to a secure location. For a restore, stop the app and replace the database with a backup made by the same schema version. CSV exports are useful for analysis, not a full backup of accounts, IDs or import history; spreadsheet formula protection may prefix some values with a quote. Deleting a website cascades to its monitors, results and events. Deleting a monitor cascades to its observations. The original import history remains as metadata. Confirm before deleting. Editing is not implemented yet; delete/recreate carefully or ask for an editing feature in the next version.

No password-reset or multi-user workflow is implemented. Keep your password securely. Do not delete the database to reset a password unless you intentionally want to lose all workspace data.

## Testing

Install dev dependencies and run from the root directory:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

On Windows with the launcher-created environment, use `.venv\Scripts\python.exe` instead of `python`. The API lifecycle test uses a disposable database and verifies empty startup, access controls, setup, inserts, duplicate rejection, timezone validation, transactional rollback, successful CSV import, cascade deletion, signout and login. JavaScript and Python syntax were checked. The browser runtime in the authoring environment blocked navigation; full visual/browser end-to-end testing remains outstanding. The user should perform a smoke test locally before adding important data. No test database or test data is included as an active workspace.

## Deployment boundary

This is a **local single-owner starter**, not a production-ready multi-tenant SaaS. Bind to `127.0.0.1`, not a public interface. Do not port-forward it. Public deployment needs HTTPS and secure cookies, verified domain ownership for any future checks, RBAC and tenant isolation, migrations, stronger rate limits, backups, observability, privacy/retention policy, dependency review, security testing and integration authorization. Do not enter confidential customer data before these controls are evaluated. See ROADMAP.md.
