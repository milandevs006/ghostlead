# Stage 3.4 — GhostLead Lab

Development milestone: v0.3.0-alpha.4. Stable tag: v0.2.0. This is a standalone fixture upgrade; the core application's internal FastAPI version stays 0.3.0-alpha.3 because no application runtime files change.

## Installation

From the GhostLead root, switch to `develop` and review `git status`. Extract the patch into the existing repository. It adds `lab/`, `tests/test_lab.py`, `STAGE-3.4.md` and versioned animated documentation assets, and replaces `README.md`. No application files, dependencies, configuration, database or earlier animation assets need replacing.

```powershell
cd D:\ghostlead
python -m pytest tests/test_lab.py -v
python -m lab.server
```

Open http://127.0.0.1:5501 (the exact loopback URL, not `localhost`). Stop with Ctrl+C. No frontend or backend process is needed for the lab. If the port is already in use, stop the conflicting process; the fixture intentionally binds only this local address and port when launched as a module.

## Manual acceptance

1. Open home, pricing and contact pages. The home page links to a deliberately broken page (404), a slow page (2-second delay) and an unavailable page (503).
2. Submit `test-001` with the successful delivery scenario. Inspect Lab results: source and destination true.
3. Submit `test-002` with the dropped scenario: source true, destination false, although the form responds 200.
4. Submit `test-003` with rejection: HTTP 422, both flags false. Check `/lab/results` afterward.
5. View `/api/health` and `/api/results`. Restart the lab and verify that all fixture results have disappeared.
6. Confirm your real GhostLead workspace is unchanged. Do not import lab results into the real workspace or register the lab in GhostLead's normal website monitoring path.

## Boundaries

Python standard-library HTTP server, bound to IPv4 loopback only. Exact Host header check; same-origin check for supplied Origin; per-process form token; small bounded form payload, explicit synthetic ID format, max 100 in-memory event rows; no outbound requests, real CRM, email, storage or third-party assets. Not a production server. No production policy exceptions: the regular GhostLead preflight still blocks localhost and private addresses. Future discovery tests should use a separate explicitly scoped fixture runner rather than weaken public destination policy. The lab provides ground-truth outcomes, not an actual CRM or automated monitoring implementation. Connection-level DNS pinning, peer checks, TLS, redirects, budgets and browser egress safeguards remain pending.

16 lab integration cases passed in the sandbox using a loopback ephemeral port. Existing core regression suite is not modified by the patch; rerun it locally as needed. No full Next.js build is needed for this lab-only change.
