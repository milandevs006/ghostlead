# Stage 3.9 — Evidence and incident detection (v0.3.0-alpha.9)

## Scope

Standalone offline evidence ingestion for the local lab only. The existing scheduler is unchanged: first save its JSONL output, then explicitly import it. No automatic writes from the scheduler, external monitoring, real customer records, changes to the main application database or UI changes. PROJECT MONOLITH remains paused. The core runtime still reports alpha.3. This milestone is alpha.9.

## Windows PowerShell

Extract the patch into `D:\ghostlead`. Stop existing lab/scheduler processes before tests (ports 5501 and 5502 must be free).

```powershell
cd D:\ghostlead
python -m pytest tests/test_lab.py tests/test_lab_discovery.py tests/test_lab_analysis.py tests/test_lab_monitoring.py tests/test_lab_scheduler.py tests/test_lab_evidence.py -v
```

Terminal 1: `python -m lab.server`

Terminal 2:

```powershell
$log = "$env:TEMP\ghostlead-lab-evidence.jsonl"
python -m lab.scheduler --interval-seconds 5 --runs 2 | Set-Content -Encoding utf8 $log
python -m lab.evidence import $log
$r = python -m lab.evidence status | ConvertFrom-Json
$r | Select-Object open_incidents,recovered_incidents
$r.recent_incidents | Format-Table path,category,severity,occurrences,opened,last_seen,recovered
$r.recent_timeline | Format-Table incident_id,event,timestamp,run_id
```

On a fresh database, the unchanged lab normally produces three open incidents with two occurrences each (broken link, server error, slow response). Timing varies. Reimporting the same file counts duplicates without changing incident occurrences. A new scheduler session with later timestamps adds new observations.

## Incident rules and integrity

- Store validated run ID, UTC start/finish, duration, status, error code, recomputed page classifications, HTTP status, latency, referring paths and error labels. Do not store bodies, form values, tokens or customer records.
- Fixed lab scope and origin, validated bounded page paths, classifications recomputed from observed status/timing/referrers. Completed runs cannot include explicitly incomplete pages, unchecked redirects, truncation or page errors. This is schema validation, not authentication of local JSONL evidence. Import only logs you generated yourself.
- One open incident per path and category. Positive findings open or repeat an incident even if coverage is partial. A category change can open another incident for the path; it does not close the earlier issue. Only an explicitly healthy page in a completed run resolves its open incidents. Absent pages, partial results, failures and redirects do not imply recovery. A later recurrence creates a new incident ID.
- Each import commits atomically, with a unique run ID and SHA-256 digest of normalized content. Exact normalized duplicates are ignored; conflicting IDs or previously unseen out-of-order timestamps reject the batch. Clock regressions need operator review, not automatic replay. A missing result from a scheduler-level exception is counted separately and not converted into fabricated evidence.
- File limit 16 MiB, line limit 256 KiB, 100 attempts per import, 10,000 stored runs. The status command shows counts and the latest 100 incidents and timeline events; it is not a complete export. No retention/pruning or automatic backups. The database is stored at `~/.ghostlead-lab/evidence-v1.sqlite3` (Windows: `$HOME\.ghostlead-lab\evidence-v1.sqlite3`), outside the repository, separate from the production workspace. An unrelated database with an existing schema is rejected. Local file permissions are inherited from the user account; no encryption or tamper-proof audit claims.
- Backup by closing evidence commands then copying that file to a private location. Do not commit JSONL logs or evidence database. To start a new lab history, stop evidence commands and archive the file outside the repository; do not touch the actual workspace database.

## Verification

25 new evidence cases passed; all 114 lab regression tests passed in the Linux development environment (37.54 seconds). A real Stage 3.8 two-run JSONL import produced 3 opened incidents and 3 repeats; replay ignored both run IDs. Recovery, recurrence, incomplete checks and rollback were tested with controlled unit-test fixtures, not a live recovery event. Windows acceptance and main application tests remain pending. External connection-level safeguards are still not implemented; no real external HTTP monitoring is enabled.

## GitHub

```powershell
cd D:\ghostlead
git checkout develop
git status
git add lab/evidence.py tests/test_lab_evidence.py STAGE-3.9.md README.md docs/assets/v0.3-alpha.9/
git diff --cached --stat
git diff --cached --name-only
git commit -m "feat: persist lab evidence and deduplicate incident lifecycles"
git push origin develop
git status
git log -1 --oneline
```

Next: Stage 3.10 final security/integration testing, then the v0.3.0 local stable release and development freeze, contingent on acceptance. Do not change main until release review.
