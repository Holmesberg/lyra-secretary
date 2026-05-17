# Public Frontend Mixed Topology Incident

**Date:** 2026-05-17.
**Subsystem:** `lyraos.org` public frontend runtime.
**Severity:** high for browser verification; medium for served availability.
**Status:** mitigated and documented.

## Summary

During the scheduler/database hardening pass, the public API remained healthy
but the public frontend was serving a build compiled for local development.
The symptom was:

```text
https://api.lyraos.org/v1/health/topology -> verified public topology
https://lyraos.org -> HTTP 200
https://lyraos.org/api/topology -> mixed topology
```

The frontend packet reported:

```text
topology_class: mixed
compiled_api_origin: http://localhost:8000
nextauth_url: http://localhost:3000
verified_topology: false
```

This made browser verification ambiguous. A public page could load while
auth/API calls were wired to localhost.

## Root Cause

There were two frontend runtimes:

- a Windows `next start` process on port `3000`, started by
  `scripts/restart_public_frontend.ps1`;
- a WSL `next-server` process in tmux session `lyra-frontend`, reached by the
  Cloudflare tunnel.

Cloudflare was hitting the WSL process. The WSL restart script
`scripts/restart_frontend_wsl.ps1` was the documented production restart path,
but it rebuilt with:

```text
npm run build
npm run start
```

Those commands use the default local topology. The correct public commands are:

```text
npm run build:public
npm run start:public
```

The first attempted fix started the correct Windows public build, but it did
not affect the WSL process serving `lyraos.org`. That created false confidence
until the public topology verifier exposed the mismatch.

## Correct Recovery

From the Windows repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restart_frontend_wsl.ps1
node scripts/verify_runtime_topology.mjs --topology public
```

The WSL restart script must:

- kill the `lyra-frontend` tmux session,
- kill stale WSL `next`/`npm run start` processes,
- remove `.next`,
- run `npm run build:public`,
- start `npm run start:public` in WSL tmux,
- assert public topology from `https://lyraos.org/api/topology`.

Do not rely on a Windows port-3000 process for public recovery while
cloudflared is running from WSL. Restart the runtime that Cloudflare actually
reaches.

## Required Verification

Before claiming `.org` is healthy:

```powershell
node scripts/verify_runtime_topology.mjs --topology public
Invoke-WebRequest https://lyraos.org/api/topology -UseBasicParsing
Invoke-WebRequest https://api.lyraos.org/v1/health/topology -UseBasicParsing
```

The public frontend must report:

```text
topology_class: public
frontend_origin: https://lyraos.org
compiled_api_origin: https://api.lyraos.org
nextauth_url: https://lyraos.org
verified_topology: true
```

Then run public two-user smoke:

```powershell
$rawA = [Environment]::GetEnvironmentVariable("LYRA_COOKIE_ASABRYHAFEZ", "User")
$rawM = [Environment]::GetEnvironmentVariable("LYRA_COOKIE_MORIARTY", "User")
$env:LYRA_COOKIE_ASABRYHAFEZ = "__Secure-next-auth.session-token=$rawA"
$env:LYRA_COOKIE_MORIARTY = "__Secure-next-auth.session-token=$rawM"
$env:LYRA_FRONTEND_ORIGIN = "https://lyraos.org"
$env:LYRA_API_ORIGIN = "https://api.lyraos.org"
node scripts/browser_smoke_two_users.mjs
```

The secure cookie name matters. The raw token value may work locally because
the smoke script can alias it as `next-auth.session-token`, but public HTTPS
must use `__Secure-next-auth.session-token`.

## What Went Well

- API topology stayed public and verified.
- The topology verifier caught the mixed frontend before the pass was treated
  as complete.
- Public two-user browser smoke eventually passed for both cookie-backed
  accounts.
- Non-operator admin/JARVIS routes stayed blocked during smoke.

## What Went Wrong

- A script named like a public restart (`restart_public_frontend.ps1`) started
  a Windows process that was not the process behind the Cloudflare tunnel.
- The actual WSL production restart path built a local topology bundle.
- Browser smoke initially ran local and passed, which did not prove `.org`.
- Public smoke initially failed because the saved cookie env vars were raw
  token values, not secure-cookie headers.
- A transient `invalid token: The token is not yet valid (iat)` appeared during
  the restart window. Token timestamp inspection showed no persistent clock
  skew once the frontend was stable.

## Permanent Rules

```text
No public health claim without public topology verifier.
No public browser claim without public two-user smoke.
No push-after-runtime-change unless the served runtime is the one verified.
```

Additional rules:

- Treat `topology_class=mixed` as a hard stop.
- Do not debug product behavior through a mixed topology.
- Do not fix public runtime by starting a second frontend process somewhere
  else.
- Kill stale frontend processes before rebuilding.
- Public `.org` auth must use the secure NextAuth cookie name in smoke tests.
- If public topology and local topology disagree, decide which environment is
  intended before making any product claims.

## Follow-Up

- `scripts/restart_frontend_wsl.ps1` now builds and starts public topology by
  default.
- The script now asserts `https://lyraos.org/api/topology` after restart unless
  `-SkipPublicCheck` is explicitly passed.
- `docs/deployment_architecture.md` links this incident from the mixed
  topology recovery row.
