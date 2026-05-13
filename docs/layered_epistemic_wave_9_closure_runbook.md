# Layered Epistemic Wave 9 Closure Runbook

**Status:** Final-wave operating runbook.
**Created:** 2026-05-13.
**Scope:** Close the layered-architecture execution pass without widening the
runtime surface.

Wave 9 is a closure wave, not an expansion wave.

Allowed work:

- pin operating contracts that reduce context-window and blast-radius risk,
- close proven kernel bypasses discovered by static search,
- add lightweight guards for recurring integrity failures,
- run the full verification gate,
- document final state.

Forbidden work:

- new product surfaces,
- new ports, hostnames, CORS policy, auth semantics, or Cloudflare topology,
- new inference claims,
- performance changes that bypass exposure, render acknowledgement, registry,
  topology, or identity enforcement,
- opportunistic refactors outside the proven closure scope.

## Preflight

1. `git status -sb`
2. `git log -1 --oneline`
3. Read `docs/context_window_blast_radius_contract.md`
4. Confirm topology:

```powershell
node scripts/verify_runtime_topology.mjs --topology public
```

No topology verification means no browser verification.

## Kernel Searches

Run before final browser smoke:

```powershell
rg -n "get_current_user_id\(\)\s*or\s*1|get_current_user_id\(\)or 1" backend/app -g "*.py"
rg -n "ReflectionViewLog\(" backend/app -g "*.py"
rg -n "record_decision\(|record_render\(|record_suppression\(" backend/app -g "*.py"
```

Expected results:

- no runtime `get_current_user_id() or 1` fallback,
- `ReflectionViewLog(` only in `app/db/models.py` and
  `app/services/output_surfaces.py`,
- exposure ledger writes only in `app/services/exposure_ledger.py` and
  `app/services/output_surfaces.py`.

## Tests

Focused backend tests:

```powershell
Push-Location backend
$env:PYTHONPATH='.'
pytest tests/test_runtime_identity_authority.py tests/test_output_surfaces.py
Pop-Location
```

Full backend CI-equivalent if backend code changed:

```powershell
Push-Location backend
$env:PYTHONPATH='.'
pytest tests/
Pop-Location
```

Frontend gates if frontend code changed:

```powershell
Push-Location frontend
npx tsc --noEmit
npm run build
Pop-Location
```

## Browser Smoke

After topology passes, smoke the public `.org` path with:

- `asabryhafez@gmail.com`
- `moriartyholmesberg@gmail.com`

Minimum assertions:

- authenticated product routes load,
- `/v1/users/me` resolves the expected user,
- `/v1/tasks/query`, `/v1/deadlines`, `/v1/analytics/insights`,
  `/v1/analytics/archetype/proximity`, and `/v1/stopwatch/status` return `200`,
- `/v1/analytics/output_surfaces/diagnostics` remains operator-only `403`.

## Push Gate

Push only after:

- focused tests pass,
- full backend CI-equivalent passes when backend changed,
- topology verifier passes,
- browser smoke passes.

After push:

```powershell
gh run list --limit 10 --json databaseId,headSha,status,conclusion,workflowName,createdAt,event,url
gh run watch <run_id> --exit-status
```

CI must be watched to success or diagnosed immediately.
