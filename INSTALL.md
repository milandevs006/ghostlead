# GhostLead v0.3.0 — local installation

GhostLead is a local single-owner workspace plus a separate synthetic monitoring lab. It is not a public SaaS deployment. The v0.3.0 release target must pass the gates in [STAGE-3.10.md](STAGE-3.10.md) before publication. Do not expose the backend, frontend or lab to the internet.

## Requirements

- Python 3.10+ (the verification environment used Python 3.13.5; check the pinned dependencies on your Python version).
- Node.js compatible with the locked Next.js version (Node 22 LTS recommended; check package engines), npm and Git.
- Free loopback ports 8000, 3000, 5501, 5502. Internet access for dependency downloads and optional public DNS lookups. No paid API or virtual environment required.

Keep your existing `data/` directory and user account. Before applying any patch, stop the servers and follow the database backup instructions in [STAGE-3.10.md](STAGE-3.10.md). Do not overwrite your local database, or copy a database from another installation. If `GHOSTLEAD_DATABASE_URL` overrides the default, identify and protect that database separately.

## Windows installation

From the repository root (adjust the directory for a fresh clone):

```powershell
cd D:\ghostlead
python -m pip install -r requirements-dev.txt
python -m pytest -q
cd frontend
npm ci
npx --no-install tsc --noEmit
npm run lint
npm run build
```

Stop on any failure. Do not update the lockfile or suppress errors just to finish a release. For local usage only, `requirements.txt` is sufficient; `requirements-dev.txt` includes the test dependencies.

## Start the application

Terminal 1, from repository root:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`start-windows.bat` is an equivalent backend-only launcher that uses your installed Python and does not create a virtual environment. Terminal 2, from the frontend directory after `npm ci` and a successful build:

```powershell
cd D:\ghostlead\frontend
npm run start -- --hostname 127.0.0.1
```

For local development instead, use `npm run dev -- --hostname 127.0.0.1`. Open http://127.0.0.1:3000. Use the same host consistently, as cookies are host-specific. The backend also serves its legacy local interface at http://127.0.0.1:8000. Use your existing account; if an already configured workspace unexpectedly asks for setup, stop and inspect the database path before creating an account.

## Isolated lab

From the root in a separate terminal:

```powershell
python -m lab.server
```

Then from another terminal:

```powershell
python -m lab.monitoring
$log = "$env:TEMP\ghostlead-lab-evidence.jsonl"
python -m lab.scheduler --interval-seconds 5 --runs 2 | Set-Content -Encoding utf8 $log
python -m lab.evidence import $log
python -m lab.evidence status
```

The lab is a deliberately synthetic fixture. It binds only to 127.0.0.1:5501, uses no external HTTP destinations, and writes no workspace records. Evidence is stored separately at `~/.ghostlead-lab/evidence-v1.sqlite3`. Use trusted local logs only. Stop lab and scheduler before running regression tests. No continuous background scheduling, automated production form submissions or CRM delivery verification is implemented.

## Release checks and recovery

See [Stage 3.10](STAGE-3.10.md) for full release gates, backups, source archive, tagging, rollback and known limitations. See [README](README.md) for module documentation, [Release notes](RELEASE-v0.3.0.md) for the release scope, and [Static README](docs/assets/v0.3.0/STATIC.md) for a reduced-motion alternative.
