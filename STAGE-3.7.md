# Stage 3.7 — Automated monitoring engine

Development milestone: v0.3.0-alpha.7. Stable tag remains v0.2.0. PROJECT MONOLITH is paused; the core UI/backend are unchanged (alpha.3).

## What changed

`lab.monitoring` orchestrates one discovery run in a separate Python process, checks the returned scope and observation structure, then applies the existing Stage 3.6 analysis. It emits a versioned JSON run envelope with UUID, UTC timestamps, monotonic elapsed duration, execution status, coverage, observed health, error code and analysis. It writes no history or application data. There is no automatic repeat, form submission or external target.

| Execution | Exit code | Meaning |
| --- | --- | --- |
| completed | 0 | Eligible observed links checked, within configured limits; issues may still be present. |
| partial | 2 | At least one unchecked/failed observation, excluded link, or truncated discovery. |
| failed | 1 | No usable analysis (worker timeout, failure, invalid output, etc.). |

`observed_health` is `issues_detected`, `no_issues_observed`, or `unknown`. Observed issues remain visible on partial runs; incomplete coverage cannot establish absence of issues. Neither completed nor no_issues_observed is an uptime SLA or full-site guarantee. API paths are deliberately excluded. A command-line argument error also returns 2 (without a JSON envelope).

## Run locally (PowerShell)

From D:\ghostlead, terminal 1:

```powershell
python -m lab.server
```

Terminal 2:

```powershell
$r = python -m lab.monitoring | ConvertFrom-Json
$code = $LASTEXITCODE
$r | Select-Object run_id,started_at,finished_at,duration_ms,execution_status,observed_health,coverage,error_code
$r.analysis.summary
$r.analysis.findings | Format-Table path,status,elapsed_ms,category,severity
$code
```

Run the old `python -m lab.analysis --format html` if a standalone visual analysis report is needed (separate fresh run). For this run's JSON, save `$r | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 "$env:TEMP\ghostlead-monitoring-run.json"`.

## Safety boundary

The trusted discovery worker connects directly to literal 127.0.0.1:5501, checks the local lab identity marker, does not use proxies, does not follow redirects, performs only GET requests and accepts no custom target. The marker is not authentication. No production database writes. This is process separation for execution control, not an OS sandbox. The existing discovery limits (20 pages, 256 KiB per response, four-second socket timeout, cooperative 25-second budget) remain. The worker receives a 32-second subprocess timeout; on timeout the worker is killed and reaped. Process creation/cleanup may add time. The timeout error branch is tested using a mocked timeout, not an actual 32-second hang. Public DNS pinning, TLS hostname validation, external redirect validation and network egress enforcement for real sites remain unimplemented. No external HTTP monitoring is enabled.

## Verification

Stop any running lab server before tests (the new integration test binds port 5501). Run from the root:

```powershell
python -m pytest tests/test_lab.py tests/test_lab_discovery.py tests/test_lab_analysis.py tests/test_lab_monitoring.py -v
```

67 passed in 20.92s in the Linux development sandbox (45 existing + 22 new). The live fixed-port subprocess test observed seven pages, one broken link, one server error, one slow page and no form submissions. The full application regression suite, Windows-local validation and external HTTP safeguards were not tested in this phase.

## Acceptance

- [ ] 67 lab tests pass locally with port 5501 free.
- [ ] Start lab and run monitor; completed / issues_detected, three findings.
- [ ] Stop lab and rerun; failed / unknown, no analysis.
- [ ] No new production database records or modified core app files.
- [ ] README animations and static edition render on GitHub.

## Commit

```powershell
git checkout develop
git add lab/monitoring.py tests/test_lab_monitoring.py STAGE-3.7.md README.md docs/assets/v0.3-alpha.7/
git diff --cached --stat
git diff --cached --name-only
git commit -m "feat: orchestrate bounded lab monitoring runs"
git push origin develop
git status
git log -1 --oneline
```

Next: Stage 3.8 scheduled local monitoring. External monitoring remains gated on tested connection-layer safeguards; do not treat this milestone as production readiness.
