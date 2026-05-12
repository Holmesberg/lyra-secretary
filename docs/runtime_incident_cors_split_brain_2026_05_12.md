# Runtime Incident: CORS Split-Brain During Local/Production Frontend Switch

**Date:** 2026-05-12
**Status:** Fixed and pushed.
**Fix commit:** `8652a30 Allow explicit frontend CORS origins`
**Related latency commits:** `2c30f3c`, `3c96ea8`, `0398668`, `3f482c3`,
`60073fc`

## Summary

The backend was reachable, but the browser reported:

```text
users/me fetch failed: "Failed to fetch"
```

The actual fault was not backend death. It was a CORS split-brain created by
local frontend and backend runtime configuration pointing at different frontend
origins.

## Root Cause In One Line

Single-origin CORS was controlled by one mutable `FRONTEND_URL`, while local
frontend development and public tunnel runtime require different browser
origins to coexist.

## Failure Chain

1. Local frontend was corrected to use:

   ```text
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXTAUTH_URL=http://localhost:3000
   ```

   This stopped local development from accidentally hitting the slow public
   production API.

2. The running backend container still had:

   ```text
   FRONTEND_URL=https://lyraos.org
   ```

3. Backend CORS used exactly one allowed origin:

   ```python
   allow_origins=[settings.FRONTEND_URL]
   ```

4. The browser page at `http://localhost:3000` sent a preflight request to
   `http://localhost:8000`.

5. Backend rejected that preflight because `http://localhost:3000` was not the
   single allowed origin.

6. The browser surfaced the rejected preflight as `Failed to fetch`, making the
   backend look unreachable even though:

   - `http://localhost:8000/` returned `200`,
   - `http://localhost:8000/v1/users/me` returned the expected unauthenticated
     `401`.

## Fix

Backend CORS now uses an explicit origin list:

```text
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://lyraos.org
```

Code changes:

- `backend/app/core/config.py`
  - added `CORS_ALLOWED_ORIGINS`
  - added `settings.cors_allowed_origins`
  - default list includes operator dev origins and public `.org`
- `backend/app/main.py`
  - changed CORS middleware from single `FRONTEND_URL` origin to the explicit
    list
- `docker-compose.yml`
  - sets `CORS_ALLOWED_ORIGINS` for local/dev runtime
- `backend/tests/test_config.py`
  - regression coverage for origin-list behavior and duplicate normalization

## Verification

Backend health:

```powershell
Invoke-WebRequest http://localhost:8000/ -UseBasicParsing
```

Result:

```text
200 {"message":"Lyra Secretary API is running"}
```

Preflight matrix:

| Origin | Result |
| --- | --- |
| `http://localhost:3000` | `200`, `Access-Control-Allow-Origin: http://localhost:3000` |
| `http://127.0.0.1:3000` | `200`, `Access-Control-Allow-Origin: http://127.0.0.1:3000` |
| `https://lyraos.org` | `200`, `Access-Control-Allow-Origin: https://lyraos.org` |

Browser-side verification:

- From `http://localhost:3000`, a browser `fetch()` to
  `http://localhost:8000/v1/users/me` reached the backend.
- A deliberately invalid bearer token returned a normal backend `401`.
- That proves the browser transport layer was fixed; remaining auth behavior is
  regular authentication, not network/CORS failure.

Regression test:

```powershell
..\.venv311\Scripts\python.exe -m pytest tests/test_config.py
```

Result:

```text
2 passed
```

## Relationship To Epistemic Integrity Contracts

This incident was an operational transport-boundary bug, not an epistemic
contract change.

The fix did not loosen:

- identity scope resolution,
- output surface registration,
- `truth_class` requirements,
- exposure emission requirements,
- backend suppression authority,
- frontend non-override rules,
- clean-data or baseline-learning gates.

The CORS origin list only controls which browser origins may reach the backend.
It does not grant data access by itself. Auth, user scoping, registry checks,
exposure decisions, and fail-closed suppression still run after transport.

The correct architectural framing:

```text
CORS = transport admission
Auth + scope = identity admission
Output registry + exposure = epistemic/runtime claim admission
```

Transport admission must be stable enough that the epistemic kernel can run.
It must not become a hidden switch that breaks local verification or public
runtime depending on whichever single environment variable was loaded last.

## Latency Context From Same Pass

The same pass also addressed several local frontend latency/development issues:

- `2c30f3c Speed dev cold tabs and auth warmup`
  - default `npm run dev` uses Turbopack with Node IPv4 flags,
  - added `npm run dev:clean` for known stale `.next` corruption,
  - landing page dev-prewarms app routes,
  - Google sign-in warms/caches CSRF.
- Browser verification after idle prewarm:
  - `/today`: `159ms`
  - `/pulse`: `241ms`
  - `/calendar`: `279ms`
  - `/deadlines`: `311ms`
  - `/table`: `200ms`
  - `/insights`: `271ms`
  - `/settings`: `253ms`

Remaining known dev-only pain:

- first landing compile under `next dev` is still roughly 8s after `.next` is
  cleared;
- this is dev compile latency, not backend unreachability;
- production/runtime verification should avoid mixing `next build` artifacts
  with an already-running dev server.

## Permanent Rule

Do not make CORS depend on a single frontend URL when local dev and public
tunnel origins both need to be valid during the same operator workflow.

Use an explicit allow-list. Treat single-origin CORS as a latent deployment
footgun.
