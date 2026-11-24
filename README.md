# GhostLead

<p align="center">
  <b>Lead Integrity & Revenue Protection Platform</b><br/>
  Monitor workflows. Trace failures. Protect every lead.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.2.0-1d4ed8?style=for-the-badge" />
  <img src="https://img.shields.io/badge/status-active%20development-0f766e?style=for-the-badge" />
  <img src="https://img.shields.io/badge/frontend-Next.js%20%2B%20TypeScript-111827?style=for-the-badge" />
  <img src="https://img.shields.io/badge/backend-FastAPI-2563eb?style=for-the-badge" />
  <img src="https://img.shields.io/badge/database-SQLite-475569?style=for-the-badge" />
</p>

---

## What is GhostLead?

**GhostLead** is a local-first platform for documenting customer acquisition workflows, analysing lead delivery records, and investigating where digital business enquiries may be breaking down.

It is being built toward a real commercial monitoring platform for businesses and agencies that want to know:

- where leads are coming from,
- where they are flowing,
- where they are failing,
- and how to investigate those failures clearly.

> **Current release:** `v0.2.0 — Advanced Product Foundation`

---

## Why GhostLead?

Most businesses know how many visitors they attract.

Very few know:

- whether their enquiry forms are actually working,
- whether leads are reaching the destination systems,
- whether they are losing opportunities silently,
- or how their acquisition workflow really looks end to end.

GhostLead is being designed to solve exactly that.

---

## Core Highlights

### Product foundation included in v0.2.0

- **Workspace & Authentication**
  - owner setup
  - login/logout
  - persistent local storage

- **Overview Dashboard**
  - website inventory
  - recorded check summaries
  - lead matching overview
  - incident summaries

- **Journey Builder**
  - visual workflow design with React Flow
  - connect stages visually
  - save website-specific journey layouts

- **Lead Explorer**
  - reconcile source and destination lead events
  - inspect unmatched events

- **Analytics Centre**
  - website/date filters
  - monitoring trends
  - lead-flow analytics
  - failure heatmaps
  - latency percentiles
  - website comparison

- **Incident Views**
  - inspect failures from recorded observations

- **Advanced Import Centre**
  - CSV import
  - Excel (`.xlsx`) import
  - JSON import
  - validation before saving
  - duplicate rejection
  - atomic confirmation

- **Reports**
  - export analytical summaries and recorded data

- **Modern UI**
  - premium white theme
  - responsive layout
  - collapsible sidebar
  - workspace search
  - subtle transitions

---

## Product Status

| Area | Status |
|------|--------|
| App foundation | Released |
| Next.js frontend migration | Completed |
| Journey builder | Completed |
| Analytics centre | Completed |
| Advanced imports | Completed |
| Automated monitoring engine | Planned |
| Domain verification | Planned |
| CRM/API integrations | Planned |
| Multi-tenant SaaS architecture | Planned |
| Commercial launch | Planned |

---

## Tech Stack

| Layer | Technology |
|------|------------|
| Frontend | Next.js, React, TypeScript |
| Styling | Custom CSS |
| Charts & Visuals | Apache ECharts, React Flow |
| Motion & Icons | Motion, Lucide |
| Backend | Python, FastAPI, Uvicorn |
| Persistence | SQLAlchemy 2, SQLite |
| Authentication | Argon2 password hashing, server-side sessions |
| Data Formats | CSV, JSON, XLSX (`openpyxl`) |
| Testing | Pytest, HTTPX, Node.js, TypeScript |
| Version Control | Git, GitHub |

---

## Quick Start

> Developed and tested on Windows / VS Code.  
> No paid API or hosting subscription is required for local development.

### Prerequisites

Install:

- Python 3.11+
- Node.js
- npm
- Git

---

## Run the backend

From the project root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## Run the frontend

Open a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open:

- **Frontend:** http://localhost:3000
- **Backend API / legacy UI:** http://127.0.0.1:8000

> Use **port 3000** for the current GhostLead frontend.

---

## Data Philosophy

## No Demo Data

GhostLead follows a strict **zero-demo-data** policy.

That means:

- no pre-created accounts
- no fake businesses
- no seeded leads
- no artificial incidents
- no fabricated revenue figures

All records come from:

- your manual inputs,
- your uploaded files,
- or your saved workspace activity.

---

## Supported Import Formats

| Record Type | Required Fields |
|------------|-----------------|
| Websites | `name,url` |
| Monitors | `website_url,name,kind` |
| Monitor Results | `website_url,monitor_name,observed_at,status,latency_ms,detail` |
| Lead Events | `website_url,event_key,stage,observed_at` |

### Supported file types

- UTF-8 CSV
- Single-sheet XLSX (without formulas)
- JSON array of objects

### Import limits

- Max file size: **1 MB**
- Max rows: **10,000**

> Invalid or duplicate records reject the entire batch.

---

## Project Structure

```text
ghostlead/
├── app/                       # FastAPI backend + database logic + legacy UI
│   ├── main.py
│   ├── import_formats.py
│   └── static/
├── frontend/                  # Current Next.js frontend
│   ├── src/app/
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   ├── journey-builder.tsx
│   │   ├── analytics-centre.tsx
│   │   ├── analytics-model.ts
│   │   └── import-centre.tsx
│   ├── tests/
│   ├── package.json
│   └── package-lock.json
├── templates/
├── tests/
├── data/                      # Local runtime database (not committed)
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── ROADMAP.md
```

---

## Testing

### Backend

From the repository root:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

### Frontend

From `frontend/`:

```powershell
npx tsc --noEmit
npm run build
```

### Analytics model tests

From `frontend/`:

```powershell
npx tsc src/app/analytics-model.ts --strict --target es2020 --module commonjs --skipLibCheck --outDir "$env:TEMP/ghostlead-analytics-test"
node tests/analytics-model.test.cjs "$env:TEMP/ghostlead-analytics-test/analytics-model.js"
```

> Tests use isolated temporary databases or in-memory fixtures.  
> They do **not** inject demo data into your workspace.

---

## Storage & Security Notes

- Default local database: `data/ghostlead.db`
- Back up the full `data/` directory before major changes
- Never commit:
  - database files
  - customer records
  - exports
  - credentials
  - tokens
  - backups

### Important

The current release is designed for a **single-owner local workspace**.

It is **not yet ready** to be exposed publicly on the internet.

Before public deployment, GhostLead still needs:

- stronger access control
- tenant isolation
- HTTPS
- production security hardening
- privacy safeguards
- deployment testing
- monitoring infrastructure

---

## Roadmap

### Released
- `v0.1.0` — Application Foundation
- `v0.2.0` — Advanced Product Foundation

### Planned
- Domain ownership verification
- Automated website discovery
- Form and contact discovery
- Real monitoring engine
- Incident automation
- CRM/API integrations
- Real-time alerts
- Multi-tenant SaaS architecture
- Billing and subscriptions
- Commercial launch

---

## Branching Strategy

- `main` → stable release branch
- `develop` → active development branch

> Tagged releases should remain immutable.  
> New changes should be added through normal commits.

---

## Documentation

- [Frontend migration](INSTALL.md)
- [Visual journey builder](STAGE-2.3.md)
- [Analytics centre](STAGE-2.4.md)
- [Advanced data imports](STAGE-2.5.md)
- [Roadmap](ROADMAP.md)

---

## Current Limitation

GhostLead `v0.2.0` is a **working local product foundation**, not yet a production-ready SaaS platform and not yet a live automated website scanner.

That distinction is important so the README stays honest.

---

## Vision

GhostLead is being built to become a platform that helps businesses answer one critical question:

### “Are we losing leads without knowing it?”

If the answer is yes, GhostLead should help them find out where, why, and what to do next.