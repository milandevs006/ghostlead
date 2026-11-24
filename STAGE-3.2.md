# GhostLead Stage 3.2 — Public Website Intelligence

Internal version: `0.3.0-alpha.2`. Install on `develop`, not the stable v0.2.0 branch.

## Installation

Stop both servers. Back up the full `data/` directory outside the repository. Compare local changes before replacing files. Extract the patch into the project root, retaining the directory layout. Do not replace the database, existing README, documentation assets, globals.css, previous analytics/import/journey components or `tests/test_app.py` (keep your Windows cleanup fix).

No additional packages beyond the Stage 3.1 requirements are needed. Run `python -m pip install -r requirements.txt` and `python -m pytest -v` from the project root. From `frontend/`, run `npx tsc --noEmit` and `npm run build`.

Start the backend from the root: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`. In a second terminal, change to `frontend/` and run `npm run dev`. Open http://localhost:3000 and choose Website intelligence. Select a registered public hostname, then click Analyse domain. No DNS query is made on page load. The public DNS lookup does not require proof of control. Verification remains separate and mandatory before future active monitoring; this phase does not implement active monitoring.

## DNS behaviour

The application uses Google's public recursive DNS resolver (8.8.8.8), fixed in code, rather than the system resolver. DNS requests are sent to that resolver over conventional DNS, not encrypted DNS. Do not register private hostnames for public lookup. Local/reserved suffixes, IP literals and non-standard web ports are rejected by the existing hostname validator. This validator is not an SSRF defence for future HTTP requests. No connection is made to returned addresses, website endpoints or target nameservers directly. Lookups are bounded (3 seconds per query, four workers, nine fixed queries, one lookup at a time and a 15-second process-local cooldown). Network policy may block public DNS; results then show timeout or resolver error. No system resolver fallback is performed.

Queries are A, AAAA, NS, CNAME, MX, TXT, SOA, DS for the exact registered hostname and TXT for `_dmarc.<hostname>`. The results are not a complete zone inventory. SPF, DMARC and DS signals are not a security audit, DNSSEC validation, policy inheritance check, or proof of hosting. Provider hints are based only on known nameserver suffixes. Record output capped at 20 values per query and 1024 characters per value; truncated results are marked. TTL is the value returned by the resolver, not necessarily the authoritative default.

Each explicitly requested lookup persists a snapshot in the new `dns_snapshots` table, created automatically. Retains 20 snapshots per website, including errors; older snapshots are pruned. Deleting a website cascades to its snapshots. CSV and JSON export the selected snapshot. No monitoring observations or lead events are created. No demo data. The relationship map groups DNS records rather than implying traffic flows.

Verification now uses the same fixed resolver and distinguishes missing names, no TXT records, token mismatch, timeouts and resolver failure. Existing verification state, tokens, permissions, and expiry rules are preserved. Publishing a TXT record still requires the website owner's cooperation.

## Testing

Eight backend tests passed in the development sandbox using isolated test databases and mocked DNS. The three modified/new TSX files passed syntax transpilation. Full frontend type-check/build, browser rendering, Windows runtime and live DNS verification must be validated locally. The patch is based on the delivered Stage 3.1 archive rather than a fresh checkout of the current private repository. No real DNS or HTTP requests were made during tests.
