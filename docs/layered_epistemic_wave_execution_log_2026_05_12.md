# Layered Epistemic Architecture Wave Execution Log

**Date:** 2026-05-12
**Scope:** Layered Epistemic Architecture execution pass, Waves 0-3 plus
frontend/runtime verification incidents.
**Status:** Waves 0-3, latency fixes, sign-in fix, and CORS split-brain fix are
pushed to `origin/main`. Remaining dirty architecture/vault docs are local and
separate from pushed runtime commits.

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
8652a30 Allow explicit frontend CORS origins
2c30f3c Speed dev cold tabs and auth warmup
3c96ea8 Make Google sign-in click deterministic
0398668 Narrow insights and speed initial auth load
3f482c3 Tighten frontend cold-load latency
60073fc Reduce analytics tab latency
5dfe94d Dual-write core output surfaces
5c37e1b Fix frontend dev runtime imports
a88e213 Document layered architecture wave pass
eaf3964 Align Wave 1 legacy guard with dual-write rollout
41a193c Add Wave 1 output surface registry
8e53172 Enforce Wave 0 identity scoping
f902d82 Document layered epistemic architecture
```

## Wave 2: Core-Surface Dual-Write And Backend Readiness

**Commit:** `5dfe94d Dual-write core output surfaces`
**Pushed:** yes, to `origin/main`.

Implemented behavior:

- Core first-wave surfaces dual-write through the output-surface emitter.
- Legacy `ReflectionViewLog` compatibility remains where frontend read/dismiss
  behavior still depends on it.
- Archetype proximity readiness moved into backend response metadata:
  - `ready`
  - `display_mode`
  - `eligible_sample_count`
  - `min_n_required`
  - `truth_class`
  - `clean_profile`
- Reminder/prediction worker surfaces use registered surface metadata.
- This wave preserved the Wave 1 kernel:
  - registered `surface_id`,
  - declared `truth_class`,
  - declared `usage_class`,
  - backend-governed render/suppression,
  - no frontend override.

## Wave 3: Narrow Insights

**Commit:** `0398668 Narrow insights and speed initial auth load`
**Pushed:** yes, to `origin/main`.

Implemented behavior:

- `/v1/analytics/insights` remains user-facing but is narrowed to
  contract-safe trace/metric style outputs.
- Immediately allowed generators:
  - `estimation_trend`
  - `initiation_delay`
  - `retroactive_rate`
- Legacy/unsafe generators are reported as suppressed with stable metadata
  instead of disappearing silently:
  - `time_of_day`
  - `readiness`
  - `abandonment`
  - `best_category`
  - `worst_category`
  - `discrepancy_signal`
  - `pause_pattern`
  - `morning_anchor`
  - `archetype_divergence`
  - `calibration_maturation`
- Suppression metadata includes owner/deadline:
  - owner: `Insights Rewrite`
  - deadline: `Wave 3`
- Backend response exposes additive contract fields so frontend cannot invent
  readiness:
  - `surface_id`
  - `truth_class`
  - `usage_class`
  - `clean_profile`
  - `eligible_sample_count`
  - `suppressed_reason`
  - `fallback_mode`
  - `legacy_adapter`

Verification:

- `tests/test_insights.py`
- `tests/test_output_surfaces.py`
- frontend typecheck/build during the latency pass.

## Frontend Latency And Auth Pass

Pushed commits:

- `3f482c3 Tighten frontend cold-load latency`
- `3c96ea8 Make Google sign-in click deterministic`
- `2c30f3c Speed dev cold tabs and auth warmup`

Relevant fixes:

- `npm run dev` now runs Next with Turbopack and Node IPv4 flags.
- `npm run dev:clean` removes `.next` before dev startup for the known stale
  `.next` corruption path.
- Landing page warms auth endpoints and, in development, HTTP-prewarms app
  routes after idle.
- Google sign-in uses a deterministic manual NextAuth POST and direct redirect.
- CSRF is warmed/cached before sign-in click or keyboard focus.

Browser verification after idle prewarm:

```text
/today_dom_ms=159
/pulse_dom_ms=241
/calendar_dom_ms=279
/deadlines_dom_ms=311
/table_dom_ms=200
/insights_dom_ms=271
/settings_dom_ms=253
```

Remaining known dev-only cost:

- first landing compile after a clean `.next` is still around 8 seconds under
  `next dev`.

## CORS Split-Brain Incident

**Commit:** `8652a30 Allow explicit frontend CORS origins`
**Pushed:** yes, to `origin/main`.
**Dedicated note:** `docs/runtime_incident_cors_split_brain_2026_05_12.md`

Root cause:

- local frontend correctly used `NEXT_PUBLIC_API_URL=http://localhost:8000`;
- running backend container still had `FRONTEND_URL=https://lyraos.org`;
- backend CORS allowed exactly `[settings.FRONTEND_URL]`;
- browser preflight from `http://localhost:3000` failed with `400`;
- browser surfaced the failure as `users/me fetch failed: "Failed to fetch"`;
- backend itself was healthy.

Fix:

- Added `CORS_ALLOWED_ORIGINS`.
- Backend CORS now uses `settings.cors_allowed_origins`.
- Docker dev default includes:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
  - `https://lyraos.org`
- Added `backend/tests/test_config.py`.

Verification:

- backend health returned `200`;
- preflight passed for localhost, 127.0.0.1, and `.org`;
- browser-side fetch from localhost reached backend and returned a normal
  invalid-token `401`;
- `tests/test_config.py` passed.

Epistemic integrity note:

- This was a transport-boundary fix only.
- It did not loosen:
  - identity scoping,
  - output-surface registration,
  - `truth_class`,
  - exposure emission,
  - backend suppression authority,
  - clean-data gates.
- CORS admits browser origins to transport. Auth, scope, registry, exposure, and
  suppression still decide whether data or claims may flow.

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

## Moriarty Alt-Account Stress Pass

Date: 2026-05-12.

Account exercised:

- `moriartyholmesberg@gmail.com`
- backend user id observed through `/v1/users/me`: `15`

Method:

- Used a short-lived NextAuth session token for the moriarty account rather
  than relying on browser-cached Google state.
- Exercised the live public path through `https://lyraos.org` and
  `https://api.lyraos.org`.
- Did not change frontend or backend ports.

Routes visited:

- `/today`
- `/deadlines`
- `/insights`
- `/calendar`
- `/pulse`
- `/table`
- `/settings`

Direct API checks from the same authenticated browser session:

- `/v1/users/me`: `200`, email `moriartyholmesberg@gmail.com`, user id `15`
- `/v1/tasks/query?state=all`: `200`, task count `42`
- `/v1/deadlines`: `200`, deadline count `14`
- `/v1/analytics/insights`: `200`, backend-governed readiness metadata,
  `0` rendered insights for this account, `10` suppressed rewrite generators
- `/v1/analytics/archetype/proximity?days=14`: `200`, backend-governed
  readiness metadata, `ready=false`
- `/v1/notifications/pending`: `200`
- `/v1/stopwatch/status`: `200`

Observed failures:

- Cloudflare RUM beacons aborted with `net::ERR_ABORTED`.
- No app/API request failed during the pass.

Conclusion:

- Public auth, user scoping, task/deadline reads, analytics readiness, and
  exposure-governed insight narrowing work for a non-operator alt account with
  real seeded stress data.

## Wave 4: Diagnostics And Enforcement Proof

Status: implemented locally, awaiting final browser/live endpoint verification
before push.

Wave 4 added an operator-only output-surface diagnostics path:

- service: `backend/app/services/output_surfaces.py`
- endpoint: `GET /v1/analytics/output_surfaces/diagnostics`
- schema version: `output_surface_diagnostics_v1`

The diagnostic reports:

- registry coverage:
  - registered surface count
  - `truth_class` counts
  - `usage_class` counts
  - unregistered render surfaces
  - unregistered decision triggers
- dual-write integrity:
  - decision count
  - render count
  - suppression count
  - decision rows missing a terminal render/suppression event
  - per-surface activity
- legacy adapter reliance:
  - legacy adapter rows
  - v0 render rows
  - parity delta
- current-data eligibility for interpretation/intervention surfaces:
  - clean profile
  - projection class
  - candidate N
  - clean N
  - contaminated N
  - UNKNOWN N
  - exposed/intervention N
  - suppression reason
  - fallback mode
  - operator-only skew flags

Mixed-row projection rule now has code-level representation:

- `measured_execution` -> `raw_observed`
- `planning_calibration` -> `raw_observed`
- `pause_process` -> `raw_observed`
- `descriptive_history` -> `correction_adjusted_effective`
- `deadline_completion_behavior` -> `external_submission_trace`

Missing projection fails closed:

- `projection_class_for_profile("unknown_future_profile")` raises
  `missing_projection_for_profile`.

Verification run:

```powershell
& "d:\Projects\Lyra Secretary v0.1\.venv311\Scripts\python.exe" -m pytest tests/test_output_surfaces.py
& "d:\Projects\Lyra Secretary v0.1\.venv311\Scripts\python.exe" -m pytest tests/test_insights.py tests/test_analytics_archetype_proximity.py
npx tsc --noEmit
```

Results:

- `tests/test_output_surfaces.py`: `12 passed`
- `tests/test_insights.py tests/test_analytics_archetype_proximity.py`:
  `15 passed`
- `npx tsc --noEmit`: passed
