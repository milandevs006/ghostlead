# Stage 3.6 — Broken link and performance analysis

Add `lab/analysis.py`, `tests/test_lab_analysis.py`, this guide, the README and `docs/assets/v0.3-alpha.6/` to Stage 3.5 on develop. No new dependencies, no application or database replacements.

```powershell
cd D:\ghostlead
python -m pytest tests/test_lab.py tests/test_lab_discovery.py tests/test_lab_analysis.py -v
python -m lab.server
```

Second terminal, repository root:

```powershell
$r = python -m lab.analysis | ConvertFrom-Json
$r.summary
$r.latency_ms
$r.findings | Format-Table path,status,elapsed_ms,category,severity
python -m lab.analysis --format html | Set-Content -Encoding utf8 "$env:TEMP\ghostlead-lab-report.html"
Invoke-Item "$env:TEMP\ghostlead-lab-report.html"
```

Each command that invokes the runner performs a new bounded read-only discovery run; timings may differ. No arbitrary targets. Expected unmodified fixture: seven pages, one unique broken-link target `/broken` (404), one server error `/unavailable` (503), and at least one slow successful page `/slow` (about 2 seconds). The default slow threshold is 1000 ms. Other pages can also be slow on a loaded machine. Five completed successful observations expected. P95 uses linear interpolation; it is descriptive of this small sample only. Referrers are discovered links, not exhaustive site coverage. Truncated discovery is clearly indicated. Incomplete responses and unchecked redirects do not establish a broken link. No browser performance, real CRM or external monitoring, automatic form submissions or database writes. The existing discovery limits and cooperative budget apply. Reports remain outside Git. The main runtime is unchanged at alpha.3.

45 lab, discovery and analysis cases passed in the development sandbox (16 new analysis cases). Full application suite not rerun because its source is unchanged. Local acceptance remains pending.

```powershell
git checkout develop
git status
git add lab/analysis.py tests/test_lab_analysis.py README.md STAGE-3.6.md docs/assets/v0.3-alpha.6/
git diff --cached --stat
git diff --cached --name-only
git commit -m "feat: analyse lab broken links and response performance"
git push origin develop
git status
```

Review staged files for sensitive information before committing. Keep main and stable release tags unchanged.
