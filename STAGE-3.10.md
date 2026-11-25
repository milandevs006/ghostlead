# Stage 3.10 — v0.3.0 release gates

The target is a stable **local** development release, not production certification. No new monitoring capability is enabled. The FastAPI version is aligned with the release target (`0.3.0`); publishing/tagging must wait for local acceptance. `main` and release tags have not been changed by the patch.

## What changed

- New end-to-end loopback scheduler → saved JSONL → validated evidence → duplicate replay → SQLite backup and reopen integration test.
- Root `.gitignore` also excludes SQLite3 databases and their sidecars.
- Backend release metadata aligned; no database schema, backend business logic, frontend, or dependency changes.
- Windows backend launcher uses installed Python rather than creating a virtual environment. It binds only to loopback. Dependencies are installed explicitly by the owner.
- Release instructions, installation guide, README animations and static edition updated.

## Verification

The baseline Python source and tests were reconstructed from previous deliveries and compared to GitHub `develop` blob hashes. The release test uses the lab only, disposable SQLite paths, and verifies that no enquiry was submitted or lab token emitted. Existing API tests use disposable databases and mocked DNS. The standalone TypeScript analytics test is not a dependency-aware frontend build.

See [RELEASE-v0.3.0.md](RELEASE-v0.3.0.md) for actual executed checks and pending gates. The complete Next.js installation, type check, lint, build, browser smoke test and Windows-specific checks must be performed locally against the actual locked repository. Do not mark them as passed without results.

## 1. Backup before applying the patch

Stop the backend, frontend, lab and scheduler; finish all evidence imports. Confirm the real database path (default `D:\ghostlead\data\ghostlead.db`; if `GHOSTLEAD_DATABASE_URL` is set, protect the actual database separately). Keep backups private, outside the repository. Copy the complete data directories only after all processes are stopped; this preserves any SQLite sidecars as well.

```powershell
cd D:\ghostlead
$backup = Join-Path $HOME ("GhostLead-backup-" + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup -ErrorAction Stop
if (Test-Path .\data) { Copy-Item .\data (Join-Path $backup 'data') -Recurse -ErrorAction Stop }
if (Test-Path "$HOME\.ghostlead-lab") { Copy-Item "$HOME\.ghostlead-lab" (Join-Path $backup 'lab') -Recurse -ErrorAction Stop }
Get-ChildItem $backup -Recurse -File | Get-FileHash -Algorithm SHA256
```

Verify copies are present. For each copied database, use Python to run `PRAGMA integrity_check` in read-only mode (use the actual copied database path; an integrity check can fail on a read-only database with uncheckpointed WAL, in which case investigate on a separate working copy). Example for the default application backup:

```powershell
$db = Join-Path $backup 'data\ghostlead.db'
python -c "import pathlib,sqlite3,sys; p=pathlib.Path(sys.argv[1]).resolve(); c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True); print(c.execute('PRAGMA integrity_check').fetchall()); c.close()" $db
```

Expected `[('ok',)]`. Repeat for `lab\evidence-v1.sqlite3` if present. Do not store secrets or customer data in Git. Back up any modified tracked source files separately; the ZIP is an overlay patch, not a replacement repository.

## 2. Local release gates

```powershell
cd D:\ghostlead
git checkout develop
git status
python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Backend/lab regression failed' }
cd frontend
npm ci
if ($LASTEXITCODE -ne 0) { throw 'Locked dependency installation failed' }
npx --no-install tsc --noEmit
if ($LASTEXITCODE -ne 0) { throw 'TypeScript failed' }
npm run lint
if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Next.js build failed' }
$testOut = Join-Path $env:TEMP ('ghostlead-analytics-' + [guid]::NewGuid())
npx --no-install tsc src/app/analytics-model.ts --strict --target es2020 --module commonjs --skipLibCheck --outDir $testOut
if ($LASTEXITCODE -ne 0) { throw 'Analytics compilation failed' }
node tests/analytics-model.test.cjs (Join-Path $testOut 'analytics-model.js')
if ($LASTEXITCODE -ne 0) { throw 'Analytics regression failed' }
cd ..
```

Stop on errors. The fixture ports 5501/5502 must be free. Never run tests against real customer databases. Do not bypass type/lint/build checks or change dependency versions solely to publish. Inspect dependency audit findings (`npm audit`, and optionally `pip-audit` if installed); review applicability, fix or document material issues, and do not run `npm audit fix --force` blindly. These checks need network access and are not an independent security audit.

Start the backend and built frontend on loopback using [INSTALL.md](INSTALL.md). Verify:

- Sign in with your existing account; if a setup prompt appears unexpectedly, stop and inspect database path.
- Compare existing websites, lead records, analytics and saved journeys with pre-upgrade records. Do not delete real records for testing.
- Navigate all existing modules, verify empty/error states and responsiveness at desktop/mobile widths. Test keyboard navigation and reduced motion.
- Verify public DNS and domain proof UI. Only test an owner-authorised domain; real proof can remain pending. Safety preflight must still return `http_enabled: false` and must not initiate external target HTTP requests.
- Run the lab, scheduler and evidence import using trusted fresh lab logs. Confirm three known fixture findings, duplicate replay and evidence persistence. Existing evidence counts may be higher; do not delete it to make counts match a fresh fixture.
- Verify no lab data in the real workspace. Record test output and acceptance results outside the repository (or include a sanitised release checklist).

## 3. Commit the release preparation to develop

```powershell
cd D:\ghostlead
git checkout develop
git status
git add .gitignore app/main.py start-windows.bat tests/test_release_integration.py INSTALL.md README.md STAGE-3.10.md RELEASE-v0.3.0.md docs/assets/v0.3.0/
git diff --cached --stat
git diff --cached --name-only
git diff --cached -- app/main.py .gitignore start-windows.bat
```

Review exactly what is staged. The Python source diff should only change the FastAPI version; no database or dependency changes. Do not stage unrelated files. After review:

```powershell
git commit -m "chore: prepare GhostLead v0.3.0 local release and integration gates"
git push origin develop
git status
git log -1 --oneline
```

## 4. Publish only after acceptance

Confirm tests and browser checks above have passed, review all tracked paths for private data, and ensure `develop` is clean and pushed. Verify remote branch state. If the tag already exists, do not overwrite it. Use a fast-forward merge only; if main and develop diverge, stop and inspect or open a reviewed PR. Do not force-push.

```powershell
git fetch origin --tags
git status
git log --oneline origin/main..origin/develop
git diff --stat origin/main..origin/develop
git ls-files
git tag --list v0.3.0
```

After confirming the above, run individually, stopping at any error:

```powershell
git checkout main
git pull --ff-only origin main
git merge --ff-only origin/develop
git push origin main
git tag -a v0.3.0 -m "GhostLead v0.3.0 - local monitoring foundation"
git push origin v0.3.0
git status
git log -1 --oneline
git show --no-patch v0.3.0
```

If main is protected, use a reviewed PR instead; tag only the accepted commit on main. Generate the exact source archive from the tag (not the working directory, and only after reviewing tracked contents):

```powershell
$zip = Join-Path $HOME 'GhostLead-v0.3.0-source.zip'
git archive --format=zip --prefix=GhostLead-v0.3.0/ --output=$zip v0.3.0
Get-FileHash $zip -Algorithm SHA256
```

In GitHub Releases, draft a release for existing tag `v0.3.0`, title `GhostLead v0.3.0 — Local Monitoring Foundation`, use the scope and known limitations in `RELEASE-v0.3.0.md`, add the source ZIP if desired, and publish only after verifying the exact tag and test results. The source ZIP excludes untracked files but will include anything mistakenly tracked; review the tag before sharing. Return to develop and freeze work:

```powershell
git checkout develop
git status
git log -1 --oneline
```

## 5. Recovery if something fails

Do not reset hard, force-push, delete a tag, or restore over a running database. Stop services. Preserve the current data and evidence directories under new private backup names, then restore the verified complete directories to their original locations only if necessary. Recheck SQLite integrity and launch using the matching source version. The v0.3 patch has no schema migration; prior-version software may not understand newer records, so test on a backup copy. To inspect an older release without disturbing current work, create a separate checkout (e.g. `git worktree add --detach D:\ghostlead-v02 v0.2.0`) and use a separate disposable database. Never point older code at the only copy of real data. If a published release needs correction, create a reviewed new patch release rather than rewriting its tag.

## Scope and freeze

- Domain proof and public DNS lookups exist; live owner-authorised proof remains pending.
- Safety is preflight only. External HTTP connection pinning, TLS/redirect enforcement and egress isolation are not shipped; external monitoring remains disabled.
- Lab automation is bounded, foreground-only. Scheduler exclusion covers scheduler CLI sessions, not manual runs; evidence ingestion is explicit and logs are not authenticated.
- Lab findings and the CLI incident store are not production lead-delivery evidence. No automatic form submission, persistent scheduler, live CRM integration, tenant isolation or public deployment.
- Independent security review, dependency audit, complete browser accessibility verification and production readiness are not established.
- PROJECT MONOLITH, v0.4.0 and commercial deployment are deferred. Once the release is accepted and tagged, stop feature development.
