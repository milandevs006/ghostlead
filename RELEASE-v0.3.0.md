# GhostLead v0.3.0 — Local Monitoring Foundation

Release target: v0.3.0. This document is release preparation; the Git tag and published release are created only after the owner completes [Stage 3.10 release gates](STAGE-3.10.md). Do not infer release publication from this file.

## Scope

- Local authenticated single-owner workspace; website/monitor registry, journey layouts, lead reconciliation, CSV/XLSX/JSON import and existing analytics.
- Exact hostname DNS TXT domain-control proof and public DNS intelligence.
- Deny-by-default network safety preflight; no external HTTP monitoring.
- Separate synthetic GhostLead Lab: discovery, broken-link and latency analysis, bounded monitor execution, finite foreground scheduling, offline evidence and incident lifecycle tracking.
- No application database migration in Stage 3.10. Application runtime metadata aligned to the release target, local SQLite files ignored, explicit no-venv launcher and updated documentation.

## Verification

- Python 3.13.5 / Linux: 156 pytest cases passed in 56.94 seconds (41 application/security, 114 lab, 1 new integrated release test).
- TypeScript 5.8.3 / Node 22.16.0: standalone analytics model compiled with strict checking and its Node assertions passed.
- New integration test executed two real loopback scheduler runs, imported their JSONL, detected three incidents, verified duplicate replay and reopened a SQLite backup with six timeline events. No production workspace was used.
- The sandbox dependency check reported an unrelated MoviePy/Pillow conflict; it does not establish a clean project-specific dependency audit.

Pending local gates: Windows regression, locked npm install, full TypeScript/lint/Next.js build, browser interaction/accessibility smoke test, dependency audit review and private backup verification. No live owner-authorised DNS verification or production network enforcement was established in this phase. No claim of public SaaS readiness or independent security certification.

## Known limitations

Lab automation is fixed to loopback and requires manually started processes. A scheduler session is finite and evidence import is explicit. Imported logs are not authenticated. Incidents reflect synthetic lab observations, not real lead loss. DNS proof does not authorise a scan by itself. External HTTP, durable scheduling, CRM integration, multi-tenant isolation and commercial operation are deferred.

## Development freeze

After accepted v0.3.0 is tagged, pause feature development. PROJECT MONOLITH (OpenStatus, Tremor, Plausible and Checkly design direction), v0.4 integrations, cloud deployment, multi-tenancy and billing remain on hold.
