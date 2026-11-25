# Stage 3.8 — Scheduled monitoring (v0.3.0-alpha.8)

## Scope

A standalone foreground scheduler for the existing local GhostLead Lab monitoring engine. No UI, FastAPI, SQLite, dependencies or existing lab modules are replaced. PROJECT MONOLITH remains paused. The main application runtime is still alpha.3; alpha.8 is the development milestone. No external HTTP monitoring or production data writes.

## Install and run (Windows PowerShell)

Extract the patch into the existing repository root `D:\ghostlead`. Stop any running lab/scheduler before testing. Ports 5501 (lab) and 5502 (scheduler guard) must be available.

```powershell
cd D:\ghostlead
python -m pytest tests/test_lab.py tests/test_lab_discovery.py tests/test_lab_analysis.py tests/test_lab_monitoring.py tests/test_lab_scheduler.py -v
```

Terminal 1: `python -m lab.server`

Terminal 2: `python -m lab.scheduler --interval-seconds 5 --runs 3`

The default is 3 runs separated by 30 seconds. Interval bounds: 5–3600 seconds; run count: 1–100. The first run starts immediately; subsequent runs start only after the previous attempt finishes and the delay elapses. Failed or partial attempts consume one slot and do not trigger an immediate retry. No missed-run catch-up or automatic restart. The 32-second discovery worker timeout from Stage 3.7 remains in effect; it is not a hard bound on total scheduler shutdown time.

For readable output while the session runs:

```powershell
python -m lab.scheduler --interval-seconds 5 --runs 3 | ForEach-Object {
    $e = $_ | ConvertFrom-Json
    if ($e.event -eq 'run_finished') {
        $e.result | Select-Object run_id,execution_status,observed_health,duration_ms,error_code
        if ($e.scheduler_error) { $e.scheduler_error }
    } elseif ($e.event -eq 'session_stopped') { $e.counts; $e.reason }
}
```

Optional lab-only JSONL evidence outside the repository:

```powershell
python -m lab.scheduler --interval-seconds 5 --runs 3 | Set-Content -Encoding utf8 "$env:TEMP\ghostlead-lab-schedule.jsonl"
```

## Event contract

Every event is a single JSON line with schema_version, local_lab_only scope, session_id and UTC timestamp. `session_started` declares the configuration; `run_started` declares the sequence; `run_finished` contains the Stage 3.7 result or a redacted scheduler error; `waiting` declares the next delay; `session_stopped` reports attempted run counts and termination reason. Exit codes: 0 all completed (even if issues observed), 1 any failed or guard unavailable, 2 partial with no failure or invalid CLI arguments, 130 stop requested. The scheduler continues after individual failed runs up to the configured limit.

## Safety and stop behaviour

The CLI holds an exclusive TCP bind on 127.0.0.1:5502 with no listener, no reuse options and Windows exclusive-address use where supported. A second scheduler process fails closed if the port cannot be acquired. This is a local CLI guard, not a distributed lock, not protection against manual `lab.monitoring`/discovery commands and not an OS sandbox. Do not run these manually in parallel with the scheduler. Port conflicts with unrelated software also block the scheduler. The guard releases when the process exits.

Ctrl+C or a handled SIGTERM requests a cooperative stop: no further runs are intentionally scheduled and an in-progress run is allowed to return. A terminal-wide Ctrl+C may also interrupt the discovery child and make that attempt fail; forced termination, closed consoles, power loss or broken output pipes can prevent the final summary. No persistent queue, daemon, database history, real website monitoring, form submission, evidence retention or incident deduplication. Stage 3.9 will address lab evidence and incident lifecycle. Connection-level protections remain pending for external monitoring.

## Verification in the Linux sandbox

89 lab regression cases passed (38.24s), including 22 new scheduler cases. An additional live two-run session completed with distinct run IDs and three findings per attempt; targeted SIGINT during the waiting interval returned 130 with exactly one attempted run; stopping the lab produced exit 1 with one failed attempt. Windows acceptance, terminal-wide Ctrl+C and the full application regression suite remain pending.

## Acceptance

- Confirm the tests pass and the lab responds.
- Run three scheduled attempts and inspect three unique run IDs, three completed results, and a final summary.
- Confirm each completed fixture result reports three known findings (404, 503 and slow response), not three new production incidents.
- Start a second scheduler while the first is waiting; it must reject the session.
- Press Ctrl+C during a waiting interval; no further attempt should start.
- Stop the lab and run a single scheduled attempt; it should report failure, not healthy observations.
- Confirm no production workspace data has changed.

## GitHub

```powershell
git checkout develop
git status
git add lab/scheduler.py tests/test_lab_scheduler.py STAGE-3.8.md README.md docs/assets/v0.3-alpha.8/
git diff --cached --stat
git diff --cached --name-only
git commit -m "feat: schedule bounded non-overlapping lab monitoring sessions"
git push origin develop
git status
git log -1 --oneline
```

Only stage the files listed above; do not commit runtime JSONL, SQLite records or credentials. To undo an already committed patch use a reviewed `git revert` of its commit, rather than resetting shared history.
