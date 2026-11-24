# GhostLead roadmap

## v0.1 — Current local foundation
- First-time owner setup and persistent authenticated workspace.
- Website/monitor registry, manually recorded observations, atomic CSV import and export.
- Data-derived analytics, event matching, latest-failure investigation and journey map.
- White-theme visual identity; responsive navigation and empty states.

## v0.2 — Data workflows and design refinement
- Review actual user-provided data schemas before building additional import adapters.
- Edit records with audit history, import preview/error report, explicit historical incident lifecycle.
- Add unit tests, real browser end-to-end tests, accessibility checks and larger-dataset pagination.
- Introduce migrations, backup verification and database performance indexes.
- Decide whether to migrate UI to Next.js + TypeScript and visualisations to ECharts/React Flow.

## v0.3 — Authorised monitoring
- Domain verification and explicit test authorisation; URL/network egress policy and SSRF protections.
- Isolated Playwright browser workers, monitored scheduling, quotas, retries and evidence capture.
- API/integration verification using least-privilege tokens; no fabricated data, no CAPTCHA bypass.
- Separate manual, imported and independently observed records with clear provenance.

## v0.4 — Commercial private beta
- PostgreSQL with migrations, organisation membership and enforced tenant isolation; team access.
- Reliable alerts, integration secrets vault, retention controls, observability, security testing and recovery drills.
- Validate customer demand and cost per monitored workflow, pricing, legal/privacy obligations and licensing.

## Public launch
- Commercial-compatible hosting, HTTPS, billing, customer support, status page and tested incident response.
- Launch only after private beta, security review and measured reliability. A zero-cost local build does not guarantee zero-cost commercial operation.
