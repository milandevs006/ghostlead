# Stage 3.5 — Read-only lab discovery

Apply this additive patch to Stage 3.4 on `develop`. Copy `lab/discovery.py`, `tests/test_lab_discovery.py`, `README.md`, this guide and `docs/assets/v0.3-alpha.5/`. Do not replace your database, previous tests or application source. No extra packages beyond the existing test requirements.

From the repository root:

```powershell
python -m pytest tests/test_lab.py tests/test_lab_discovery.py -v
python -m lab.server
```

In a second terminal from the root:

```powershell
python -m lab.discovery
$r = python -m lab.discovery | ConvertFrom-Json
$r.pages | Format-Table path,status,elapsed_ms,title
$r.summary
$r.pages | ForEach-Object { $_.forms } | ConvertTo-Json -Depth 6
```

Optional report: `$r | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 "$env:TEMP\ghostlead-lab-discovery.json"`. Keep generated reports outside Git.

Expected baseline from the unmodified Stage 3.4 fixture: seven HTML pages, one form, HTTP 404 and 503 on the intended failure pages, and roughly two seconds for `/slow`. Actual elapsed times vary. No requests to form actions or API results; health marker only. Confirm that lab results did not change. Stop the server with Ctrl+C.

The runner uses direct HTTP to the fixed literal loopback address and port 5501 with no proxy, no redirects, no custom targets, no query strings, bounded page count, response bytes and socket timeout. A cooperative budget is checked between reads and requests; it is not a hard deadline. This is for the controlled fixture only, not a production crawler or full SSRF solution. No JavaScript, rendered DOM, third-party website crawling, data persistence or automatic submissions. HTML form fields are described without their values. The health marker is a sanity check, not cryptographic authentication. The main application is unchanged, including its internal alpha.3 version and public network policy. The README milestone is alpha.5.

Commit only the listed patch files after local verification. Stable main and v0.2.0 tag remain unchanged.
