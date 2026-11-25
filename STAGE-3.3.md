# Stage 3.3 — Network safety preflight and new branding

Development version: `0.3.0-alpha.3`. Stable release remains `v0.2.0`.

## Install

Stop both servers, switch to `develop`, review `git status`, and back up the entire `data/` folder outside the repository. Extract this patch into the existing repository, retaining all other files. The patch replaces `app/main.py`, `frontend/src/app/page.tsx`, `frontend/src/app/layout.tsx`, `frontend/src/app/favicon.ico` and `README.md`. It adds the safety module, tests, brand component, styles, public brand assets and versioned documentation assets. No requirements changes. Do not replace `globals.css`, the old tests, your database, or the previous documentation assets.

```powershell
cd D:\ghostlead
python -m pytest -v
cd frontend
npx tsc --noEmit
npm run build
```

Start the backend from the root with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload` and the frontend from `frontend` with `npm run dev`. Open http://localhost:3000.

## Acceptance

- Approved shield icon and wordmark on loading, authentication, sidebar (including collapsed mode) and browser tab. The assets are cropped raster PNG/ICO renditions of the approved artwork, not a true vector master. The legacy port-8000 UI is unchanged. Loading motion respects reduced-motion settings.
- Open Network safety; select an unverified site. URL policy may pass, but the verification gate blocks the preflight. The button intentionally permits a blocked decision to be logged; it will not query destination DNS for an unverified site.
- Click Run safety preflight once; see blocked outcome and history. Refresh and confirm history persists. No new monitoring results or lead events should appear. Wait 15 seconds between preflights.
- If a domain owner publishes a valid TXT proof and explicitly permits testing, run a preflight for that registered site. It performs only fixed-resolver A and AAAA lookups. A passing decision means all returned addresses passed preliminary checks at that time. It does not indicate the website is healthy, grant permission to send requests, or guarantee future DNS answers.
- Public DNS intelligence, analytics, imports and existing journey data continue working.

## Engineering constraints

Only HTTP and HTTPS with default ports, canonical ASCII hostnames, no credentials, fragments, controls or backslashes. Internationalized hostnames must be entered in their ASCII punycode form for this conservative policy. Reject non-global/reserved, loopback, private, multicast, link-local and disallowed IPv6 transition addresses. Both A and AAAA must resolve without unexpected errors; genuine no-answer is allowed per family. Maximum 32 combined addresses, sequential DNS lifetimes 3 seconds per family. Fixed recursive resolver 8.8.8.8, no direct website connection. Process-local lock and cooldown; 30 audit decisions retained per site. Table created additively; site deletion cascades. Audit events are not monitor runs. Read endpoints do not perform network IO. Proof checked before and after DNS; revocation, expiry or changed proof blocks the decision. Redirect helper only allows same origin and at most three redirects, but no HTTP transport calls it yet.

**Before active HTTP or browser automation:** enforce fresh proof checks and per-hop DNS validation at request time, numeric-address socket pinning and peer checks, TLS verification against original hostname, proxy bypass prevention, strict time/response budgets, process/network egress isolation, and tests for redirects, rebinding and browser subresources. These are not implemented by a DNS preflight. No production readiness claim. Do not expose development servers publicly. Proposed connect/response limits in the policy module are not enforced until a transport exists.

41 backend test cases passed in the sandbox, using mocks and temporary databases. TSX syntax checked, not full Next.js compilation. Test live preflight only when you have authorisation. Keep the main branch stable until v0.3.0 is released.
