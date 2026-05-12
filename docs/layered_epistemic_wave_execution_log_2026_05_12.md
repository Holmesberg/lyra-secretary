# Layered Epistemic Architecture Wave Execution Log

**Date:** 2026-05-12  
**Scope:** Layered Epistemic Architecture execution pass, Wave 0 and Wave 1.  
**Status:** Wave 0 and Wave 1 are pushed to `origin/main`. Wave 2 and Wave 3
work remains local and unverified.

This log records what happened during the pass so future work does not depend
on operator memory, chat context, or local terminal history.

## Operating Principle Captured

The pass established the working rule:

> Hard kernel, soft periphery. Strictness scales with epistemic risk.

Kernel rules remain strict:

- identity/scope must resolve before product reads or writes,
- output surfaces must be registered before render,
- every output surface declares `truth_class`,
- user-facing output goes through the authorized emission path,
- frontend requests never override backend suppression,
- unregistered, unknown, or under-specified surfaces fail closed.

Periphery is risk-scaled:

- trace outputs can carry a light contract,
- metric outputs need declared inputs and sign conventions,
- interpretations and interventions need thresholds, provenance, exposure, and
  fallback behavior,
- identity-level claims are nearly locked down.

This operating discipline was added to:

- `docs/layered_epistemic_architecture.md`
- `LyraOS/01_System_Map/Layered Epistemic Architecture.md`

## Wave 0: Identity And Scoping Preconditions

**Commit:** `8e53172 Enforce Wave 0 identity scoping`  
**Pushed:** yes, to `origin/main`.

Wave 0 was not pushed immediately at first. After review, the worktree was split
so Wave 0 could be pushed independently before Wave 1.

Implemented behavior:

- `UserScopeMiddleware` no longer defaults anonymous HTTP requests to operator
  scope.
- `get_db()` no longer overwrites request identity with fallback operator scope.
- `get_current_user()` trusts middleware or explicit `X-User-Id`; missing
  identity fails closed.
- Notification polling requires explicit identity and no longer falls back to
  operator scope.
- Worker notification writes no longer self-HTTP back into
  `/v1/notifications/push`; they use `notification_queue.enqueue_user_notification`.

Primary files:

- `backend/app/main.py`
- `backend/app/api/deps.py`
- `backend/app/api/v1/endpoints/notifications.py`
- `backend/app/services/notification_queue.py`
- `backend/app/workers/jobs/reminders.py`
- `backend/app/workers/jobs/pause_prediction.py`
- `backend/app/workers/jobs/resume_prediction.py`
- `backend/app/workers/jobs/timer_overflow.py`

Live backend verification before Wave 1:

- Docker backend container was confirmed live and restarted.
- Anonymous product endpoints returned `401`, including:
  - `/v1/users/me`
  - `/v1/analytics/insights`
  - `/v1/analytics/archetype/proximity?days=14`
  - `/v1/analytics/bias_factor/lookup?...`
  - `/v1/notifications/pending`
- Alt-account bearer request resolved to the alt user, not operator scope.
- Alt-account `/v1/analytics/insights` returned a backend-governed locked
  response rather than operator data.

## Wave 1: Registry And Emission Contract

**Initial commit:** `41a193c Add Wave 1 output surface registry`  
**Correction commit:** `eaf3964 Align Wave 1 legacy guard with dual-write rollout`  
**Pushed:** yes, to `origin/main`.

Implemented behavior:

- Added versioned output-surface registry:
  - `backend/app/core/output_surface_registry.json`
- Added shared output-surface emitter:
  - `backend/app/services/output_surfaces.py`
- Registry entries declare:
  - `surface_id`
  - `truth_class`
  - `usage_class`
  - `channel`
  - `exposure_category`
  - `signal_targets`
  - `clean_profile`
  - `min_n`
  - `time_window_days`
  - `fallback_mode`
  - `operator_only`
  - `legacy_adapter`
  - `render_policy_version`
  - `interruptiveness`
  - `salience_level`
- Shared emitter writes:
  - `ExposureDecisionEvent`
  - `ExposureRenderEvent`
  - `SuppressionEvent`
  - optional legacy `ReflectionViewLog` adapter rows
- Operator-only surfaces reject non-operator users at the emitter.
- Unregistered surfaces fail before render or suppression emission.

Wave 1 scope correction:

- The first Wave 1 static test was too strict because it forbade direct legacy
  `ReflectionViewLog` writers before Wave 2 converted existing legacy surfaces.
- That was corrected in `eaf3964`.
- Wave 1 now enforces the kernel while allowing existing legacy writers in:
  - `backend/app/api/v1/endpoints/stopwatch.py`
  - `backend/app/services/task_manager.py`
- Those legacy writers are expected to move through the shared emitter during
  Wave 2 dual-write.

Clean verification at pushed Wave 1 commit `eaf3964`:

- Focused Wave 1 tests:
  - `tests/test_output_surfaces.py`: `9 passed`
- Full backend suite:
  - `737 passed, 1 xfailed`

## Push Policy Established

Future wave execution must push after each completed wave.

Observed correction in this pass:

- Wave 0 had not been pushed initially.
- The dirty tree was split.
- Wave 0 was committed and pushed first.
- Wave 1 was committed and pushed second.
- Wave 2 and Wave 3 local edits were left uncommitted.

Current pushed stack after this pass:

```text
eaf3964 Align Wave 1 legacy guard with dual-write rollout
41a193c Add Wave 1 output surface registry
8e53172 Enforce Wave 0 identity scoping
f902d82 Document layered epistemic architecture
```

## Local Uncommitted Work After Wave 1

Wave 2/Wave 3 and related documentation/frontend work remains local.

As of the pass, local dirty areas included:

- architecture docs:
  - `docs/layered_epistemic_architecture.md`
  - `docs/cortex_contract_v0.md`
  - `docs/cortex_product_research_contract_v0.md`
  - `LyraOS/01_System_Map/Layered Epistemic Architecture.md`
  - `LyraOS/01_System_Map/Data Flow Map.md`
  - `LyraOS/01_System_Map/Epistemic Core.md`
- backend dual-write/readiness work:
  - `backend/app/api/v1/endpoints/analytics.py`
  - `backend/app/api/v1/endpoints/stopwatch.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/workers/jobs/reminders.py`
  - `backend/app/workers/jobs/pause_prediction.py`
  - `backend/app/workers/jobs/resume_prediction.py`
- frontend readiness and dev-runtime work:
  - `frontend/app/(app)/insights/page.tsx`
  - `frontend/components/archetype-insights-card.tsx`
  - `frontend/lib/archetype.ts`
  - `frontend/lib/tasks.ts`
  - `frontend/instrumentation.ts`
  - `frontend/tailwind.config.ts`

`LyraOS/.obsidian/graph.json` is local Obsidian UI state and should not be
included in architecture or wave commits.

## Browser And Tunnel Incident

During browser verification, `localhost:3000` showed unstyled/raw HTML.

Root cause:

- `localhost:3000` was served by an old WSL `next start` process from
  2026-05-10.
- The HTML pointed at hashed CSS chunk files that no longer existed in
  `.next/static/css`.
- CSS chunk requests returned HTTP `400`, so the browser rendered unstyled HTML.

Initial recovery:

- The stale WSL `next start` process was stopped.
- A native Windows `next dev` process was started on `localhost:3000`.
- Local CSS then resolved as:
  - `/_next/static/css/app/layout.css?...`
  - HTTP `200`
  - `Content-Type: text/css`

Second failure:

- The Windows `next dev` process crashed when compiling auth because
  `tailwind.config.ts` used `require("tailwindcss-animate")`.
- Under the current ESM load path, that produced:
  - `ReferenceError: require is not defined`
- `frontend/tailwind.config.ts` was patched locally to use an ESM import:
  - `import tailwindcssAnimate from "tailwindcss-animate"`
  - `plugins: [tailwindcssAnimate]`

Public `.org` outage:

- `lyraos.org` returned `502`.
- `api.lyraos.org` also returned `502` during parts of the recovery.
- Cloudflare tunnel logs showed:
  - frontend origin: `http://localhost:3000`
  - backend origin: `http://localhost:8000`
  - frontend failures were `connect: connection refused` against
    `127.0.0.1:3000` inside WSL.

Important topology detail:

- `cloudflared` runs inside WSL.
- Its `localhost:3000` means WSL-local `127.0.0.1:3000`, not Windows
  `localhost:3000`.
- Native Windows Next on `localhost:3000` is visible to the Windows browser, but
  not to the WSL tunnel as WSL `localhost`.

Temporary detour:

- The Cloudflare config was briefly changed to point frontend ingress at
  `http://172.24.96.1:3000`, the Windows host address reachable from WSL.
- This was reverted.
- The final Cloudflare config was restored to the original:

```yaml
ingress:
  - hostname: lyraos.org
    service: http://localhost:3000
  - hostname: api.lyraos.org
    service: http://localhost:8000
  - service: http_status:404
```

Final recovery state:

- Windows `next dev` runs bound to `0.0.0.0:3000`.
- WSL cannot currently run the frontend directly because it has no Linux `node`
  binary and resolves `npm` to Windows npm.
- A temporary WSL-local TCP bridge was started:
  - script: `/tmp/lyra_tcp_proxy.py`
  - listens: `127.0.0.1:3000` inside WSL
  - forwards to: `172.24.96.1:3000`
- `cloudflared` is again using its original `http://localhost:3000` frontend
  origin, which now reaches the TCP bridge.

Verified final public state:

- `https://lyraos.org`: HTTP `200`, title `LyraOS - Your Cognitive Operating System`
- `https://api.lyraos.org`: HTTP `200`, body starts with
  `{"message":"Lyra Secretary API is running"}`

Current runtime processes needed for `.org`:

- Windows `node.exe` serving Next on port `3000`.
- WSL `python3 /tmp/lyra_tcp_proxy.py` bridging WSL localhost to Windows host.
- WSL `cloudflared tunnel --loglevel info run lyra-prod`.
- Docker backend serving FastAPI on port `8000`.

## Frontend Runtime Debt

The current bridge is a recovery mechanism, not the durable deployment shape.

Recommended durable fix before the next serious browser pass:

1. Install a real Linux Node runtime inside WSL and run the frontend from WSL,
   or
2. Add a frontend Docker service to `docker-compose.yml`, or
3. Make Cloudflare tunnel config intentionally point to a stable Windows-host
   address and document that as the deployment topology.

Preferred direction:

- Add a frontend Docker service or restore proper WSL Node.
- Avoid relying on a `/tmp` TCP bridge for production-facing `.org`.

Also commit or deliberately discard the local `frontend/tailwind.config.ts`
ESM patch. Without it, the native Windows dev server can crash again when auth
or Tailwind recompiles.

## Verification Commands Used

Backend:

```powershell
& "d:\Projects\Lyra Secretary v0.1\.venv311\Scripts\python.exe" -m pytest tests/test_output_surfaces.py
& "d:\Projects\Lyra Secretary v0.1\.venv311\Scripts\python.exe" -m pytest
```

Wave 1 clean worktree verification:

```powershell
git worktree add --detach $env:TEMP\lyra-wave1-verify eaf3964
```

Local frontend checks:

```powershell
Invoke-WebRequest http://localhost:3000 -UseBasicParsing
Invoke-WebRequest http://localhost:3000/_next/static/css/app/layout.css -UseBasicParsing
Get-NetTCPConnection -LocalPort 3000
```

Tunnel/origin checks:

```powershell
wsl.exe curl -I --max-time 5 http://127.0.0.1:3000
wsl.exe curl -I --max-time 5 http://localhost:8000
Invoke-WebRequest https://lyraos.org -UseBasicParsing
Invoke-WebRequest https://api.lyraos.org -UseBasicParsing
```

## Follow-Up Checklist

- Keep pushing after each wave.
- Before Wave 2, decide whether the Wave 2 local edits should be split further
  by surface group.
- Run browser verification only after confirming the local/public frontend
  topology is stable.
- Replace the temporary WSL TCP bridge with a durable frontend runtime.
- Commit the Tailwind ESM fix separately if native Windows dev remains a
  supported path.
- Do not commit Obsidian UI-state files.
- Keep Wave 2 focused on core-surface dual-write and backend readiness.
