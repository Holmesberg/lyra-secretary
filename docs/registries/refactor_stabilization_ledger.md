---
authority: active-contract
may_authorize_code: false
runtime_owner: none
created: 2026-06-29
---

# Refactor Stabilization Ledger

Status: active S1 ledger. This file records authority moves, removed paths,
parked paths, tests, and rollback notes for freeze-closure refactor work.

## Entry Format

Each risky refactor PR or wave-sized commit must record:

- changed authority;
- removed paths;
- parked paths;
- moved authority;
- tests or verification added/run;
- rollback note.

## H0 - Docker Context Hotfix

Commit: `aa27f89 ops: exclude local secrets from docker contexts`

Changed authority:

- Docker build contexts now have explicit local secret/data exclusion rules.

Removed paths:

- None.

Parked paths:

- Root `.dockerignore` remains parked because the active compose build context
  is `./backend`; root context hardening requires a separate decision if a root
  Dockerfile/build context is introduced.

Moved authority:

- None.

Tests and verification:

- backend Docker context copy probe excluded `.env`, DBs, cache, coverage, and
  temp artifacts;
- OpenClaw Docker context copy probe excluded `.env`, DBs, cache, coverage,
  temp, `node_modules`, and cookie artifacts;
- `docker compose config --quiet`;
- `git diff --check`;
- public operator-cookie read-only browser stress.

Rollback note:

- Revert `aa27f89` only. No runtime behavior changed.

## S1a - Safety Rails And Authority Registries

Commit: `22eb346 docs: add refactor safety rail registries`

Changed authority:

- Added report-only mutation surface registry.
- Added runtime topology ownership manifest.
- Added user-data ownership/export/delete/runtime purge manifest.
- Added clean-data/provenance vocabulary registry.
- Added identity/scoping ownership note.
- Linked S1a registries from `docs/AUTHORITY.md`.
- Added report-only authority scanner.

Removed paths:

- None.

Parked paths:

- Provider connection model split into future `integration_connection` and
  `credential_state` remains parked until schema authority exists.
- Full Jarvis data-model deletion remains parked; active runtime parking was
  later handled by the S1b Jarvis seam.
- OpenClaw/GPT runtime product wiring remains parked and unauthorized.

Moved authority:

- No runtime authority moved.
- Documentation now names intended owners for mutation-capable surfaces so S1b
  and S1c can seal or test them incrementally.

Tests and verification:

- `python scripts/scan_authority_surfaces.py --fail-on-missing`;
- `python -m py_compile scripts/scan_authority_surfaces.py`;
- `node scripts/test_runtime_topology_contract.mjs`;
- `node scripts/verify_runtime_topology.mjs --topology public --skip-browser`;
- `git diff --check`;
- public operator-cookie browser verification after commit/push.

Rollback note:

- Revert the S1a commit only. This removes documentation registries and the
  report-only scanner without touching runtime behavior.

## S1b - Notification Worker Exposure/Render Authority

Commit: notification/exposure authority seam commit.

Changed authority:

- Reminder, pause-prediction, and resume-prediction workers now create queued
  output-surface decisions only.
- Browser render remains the authority for render truth.
- Dismiss/ack/action remain separate interaction outcome truth.

Removed paths:

- Removed worker-side render claims from reminder, pause-prediction, and
  resume-prediction enqueue paths.

Parked paths:

- OpenClaw relay reliability was later handled by the S1b relay seam.
- Jarvis compatibility vs hard-disable was later resolved by Jarvis runtime
  parking.
- Admin/dashboard consolidation was later handled by admin dashboard
  subordination.

Moved authority:

- Worker enqueue paths moved from `emit_surface_render(...)` to
  `create_output_surface_decision(... decision_status="queued")` plus a linked
  notification `exposure_id`.

Tests and verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_timer_overflow_notifications.py tests/test_notification_queue_openclaw_mirror.py tests/test_reminders_scheduler_contract.py tests/test_pause_prediction_job.py tests/test_resume_prediction_job.py -q`

Rollback note:

- Revert the notification/exposure authority seam commit only. This restores
  the previous worker-side render emission behavior while leaving H0 and S1a
  safety rails intact.

## S1b - OpenClaw Relay Processing Queue

Commit: OpenClaw relay reliability seam commit.

Changed authority:

- OpenClaw operator relay now moves alerts through a processing queue before
  Telegram delivery.
- Alerts are acknowledged from processing only after Telegram send succeeds.
- Malformed payloads move to a dead-letter queue instead of being retried
  forever.

Removed paths:

- Removed destructive `BLPOP` delivery semantics from the relay.

Parked paths:

- Durable backend-side operator-alert dedupe was later handled by the durable
  dedupe seam.
- Jarvis compatibility vs hard-disable was later resolved by Jarvis runtime
  parking.
- Admin/dashboard consolidation was later handled by admin dashboard
  subordination.

Moved authority:

- The relay owns delivery acknowledgement for operator alerts:
  `pending -> processing -> sent/ack` or `pending -> processing -> dead_letter`.

Tests and verification:

- `node --check scripts/openclaw_operator_relay.mjs`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_openclaw_operator_relay.ps1`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_openclaw_operator_relay.ps1 -StatusOnly`;
- Redis queue length checks for `notifications:pending:1`,
  `notifications:pending:1:processing`, and
  `notifications:pending:1:dead_letter`.

Rollback note:

- Revert the OpenClaw relay reliability seam commit and rerun
  `scripts/start_openclaw_operator_relay.ps1`. Pending alerts stay in Redis;
  processing/dead-letter queues can be inspected before any manual repair.

## S1b - Durable Operator Alert Dedupe

Commit: durable operator-alert dedupe seam commit.

Changed authority:

- Operator-alert cooldown dedupe is now enforced through Redis
  `SET ... NX EX`, not only process memory.
- The in-process cooldown remains a local fast path after successful enqueue.

Removed paths:

- Removed process-restart duplicate risk for alerts that provide a stable
  `dedupe_key` and `cooldown_seconds`.

Parked paths:

- Alert delivery success remains owned by the OpenClaw relay processing queue.
- Jarvis compatibility vs hard-disable was later resolved by Jarvis runtime
  parking.
- Admin/dashboard consolidation was later handled by admin dashboard
  subordination.

Moved authority:

- Redis now owns cross-process/cross-restart operator-alert cooldown state for
  deduped alerts.

Tests and verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_operator_notifier.py tests/test_scheduler_degradation_contract.py tests/test_per_user_worker_helper.py -q`

Rollback note:

- Revert the durable operator-alert dedupe seam commit only. This restores
  process-local cooldown behavior; any existing Redis dedupe keys expire by
  their configured cooldown TTL.

## S1b - Admin Dashboard Subordination

Commit: admin dashboard subordination seam commit.

Changed authority:

- `/admin/dashboard` now declares itself `historical_read_only` and
  subordinate to `/operator`.
- Legacy admin dashboard user rows no longer expose raw email addresses.
- The frontend admin table labels the user column as content-minimized user
  identity rather than email.

Removed paths:

- Removed raw email display from the legacy admin dashboard surface.

Parked paths:

- Full admin-dashboard merge/deletion remains parked until R2 operator cockpit
  retry decides which remnants still matter.
- `/admin/feedback` remains a separate feedback triage surface and is not
  changed by this seam.

Moved authority:

- Cohort-readiness authority remains `/operator`; `/admin/dashboard` is an
  explicitly subordinate legacy funnel/coverage view.

Tests and verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_operator_route_security.py tests/test_alpha_funnel.py -q`;
- `cd frontend && npm run build`.

Rollback note:

- Revert the admin dashboard subordination seam commit only. This restores the
  previous legacy admin response/page shape without touching `/operator`.

## S1b - Jarvis Runtime Parking

Commit: Jarvis runtime parking seam commit.

Changed authority:

- `/v1/jarvis/*` is now a disabled compatibility surface. Operator auth still
  applies first; authorized operators receive `410 jarvis_disabled`.
- Pulse no longer renders a Jarvis floating button, chat modal, or Jarvis API
  client.
- OpenClaw remains the operator reasoning shell. Jarvis is not a second product
  mind and may not call models, execute tools, suggest actions, or mutate.

Removed paths:

- Removed active frontend Jarvis client/components.
- Removed active Jarvis endpoint imports of NIM, tool execution, and
  `JarvisInvocation` writes.

Parked paths:

- Historical `JarvisInvocation` rows remain part of export/delete/data
  sovereignty until a schema-backed deletion plan exists.
- `backend/app/services/jarvis_tools.py` remains as a legacy internal
  aggregation dependency for behavioral-signature diagnostics until R4
  extraction.
- Full Jarvis model/table deletion remains parked.

Moved authority:

- Operator reasoning remains with OpenClaw.
- Canonical task/deadline/timer/provider mutations remain with canonical
  services only.

Tests and verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_jarvis_endpoints.py tests/test_operator_route_security.py tests/test_security_audit.py tests/test_delete_account_modern_auxiliary_rows.py tests/test_analytics_behavioral_signature.py -q`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_jarvis_phase2_discovery_tools.py tests/test_nvidia_nim_client.py -q`;
- `cd frontend && npm run build`;
- `python scripts\scan_authority_surfaces.py --fail-on-missing`;
- `python -m py_compile scripts\scan_authority_surfaces.py`;
- `node scripts\verify_runtime_topology.mjs --topology public`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_operator_readonly_browser_stress.ps1 -Topology public`;
- Jarvis-specific operator-cookie browser probe saved screenshots and JSON under
  `tmp/jarvis-parking-*`.

Rollback note:

- Revert the Jarvis runtime parking seam commit only. Historical rows and data
  registry entries are untouched by this seam, so rollback does not require
  data repair.

## S1b - Provider Deadline Authority And Idempotency

Commit: provider deadline authority seam commit.

Changed authority:

- Moodle WS backfill now stages provider-created deadline rows through
  `DeadlineManager.stage_provider_backfill_deadline(...)`.
- Provider completion evidence from Moodle sync is idempotent across repeated
  sync retries.
- Moodle provider completion remains candidate/evidence and does not mark the
  canonical deadline complete.

Removed paths:

- Removed direct `Deadline(...)` construction from the Moodle WS backfill
  service.
- Removed repeated provider completion evidence creation for repeated Moodle WS
  syncs.

Parked paths:

- The broader provider connection model split into `integration_connection` and
  `credential_state` remains parked until schema authority exists.
- Provider-confirmed canonical completion remains unauthorized unless the user
  explicitly confirms it through canonical deadline authority.

Moved authority:

- Provider backfill deadline mutation moved from
  `backend/app/services/moodle_submissions_sync.py` into
  `backend/app/services/deadline_manager.py`.
- Moodle provider completion idempotency now lives beside deadline completion
  event creation in `deadline_manager.py`.

Tests and verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_moodle_submissions_sync.py tests/test_moodle_ics_sync.py tests/test_deadline_completion_events.py -q`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_provider_credentials_security.py tests/test_reconcile_deadline_outcomes_job.py tests/test_operator_route_security.py -q`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_raw_sql_user_scope_scan.py -q`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest -q`;
- `cd frontend && npm run build`;
- `python scripts\scan_authority_surfaces.py --fail-on-missing`;
- `git diff --check`;
- `node scripts\verify_runtime_topology.mjs --topology public`;
- public restart with frontend rebuild after a first `-SkipFrontendBuild`
  attempt correctly failed the topology verifier on stale localhost-compiled
  frontend assets;
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T00-12-59-257Z`.

Rollback note:

- Revert the provider deadline authority seam commit only. No schema migration
  or data repair is required; existing provider candidate/evidence rows remain
  readable by the same models.

## S1c - Browser Auth And Topology Helper Gate

Commit: browser auth helper seam commit.

Changed authority:

- No product/runtime authority changed.
- Operator and multi-account browser verification now share one cookie parsing,
  cookie aliasing, backend-token resolution, user-ref hashing, and API-fetch
  helper.
- The operator read-only browser wrapper runs the helper self-test before
  topology and Playwright checks.

Removed paths:

- Removed duplicated NextAuth cookie parsing and backend-token resolution from
  the operator read-only stress script and two-account smoke script.

Parked paths:

- Two-account browser smoke remains unavailable until non-operator cookies are
  refreshed with full, non-truncated values.
- Broader Playwright fixture extraction remains parked for later S1c/R3 work.

Moved authority:

- Browser auth/test harness behavior moved into
  `scripts/browser_auth_helpers.mjs`.

Tests and verification:

- `node scripts\test_browser_auth_helpers.mjs`;
- `node --check scripts\browser_auth_helpers.mjs`;
- `node --check scripts\browser_stress_operator_readonly.mjs`;
- `node --check scripts\browser_smoke_two_users.mjs`;
- `node --check scripts\test_browser_auth_helpers.mjs`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T00-23-38-309Z`.

Rollback note:

- Revert the browser auth helper seam commit only. This restores duplicated
  browser-script helper code without touching product runtime state or data.

## S1c - Multi-Account Mutable Browser Verification

Commit: multi-account mutable browser verification seam commit.

Changed authority:

- No product/runtime authority changed.
- Browser verification now distinguishes:
  - operator account (`LYRA_COOKIE_ALINASSERSABRY`) as read-only privileged
    verification identity;
  - Holmesberg account (`LYRA_COOKIE_HOLMESBERG`) as non-operator mutable chaos
    verification identity.
- Multi-account smoke asserts operator/non-operator authorization boundaries
  before any mutable runtime path is exercised.

Removed paths:

- Removed the old two-account smoke assumption that `asabryhafez` is the
  required non-operator cookie for runtime access-boundary checks.

Parked paths:

- Full Playwright UI-click regression coverage remains parked for R3; this
  seam adds API-backed mutation checks plus browser-render checks across core
  surfaces.
- Main/alt account broad matrix remains conditional on available full cookies.

Moved authority:

- No product authority moved.
- Test harness ownership for non-operator mutable smoke now lives in
  `scripts/browser_mutable_holmesberg_smoke.mjs` and wrapper
  `scripts/run_holmesberg_mutable_browser_smoke.ps1`.

Tests and verification:

- `node --check scripts\browser_mutable_holmesberg_smoke.mjs`;
- `node --check scripts\browser_smoke_two_users.mjs`;
- PowerShell parser checks for:
  - `scripts\run_multi_account_browser_smoke.ps1`;
  - `scripts\run_holmesberg_mutable_browser_smoke.ps1`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_multi_account_browser_smoke.ps1 -Topology public`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, screenshots and JSON under
  `tmp/browser-smoke/holmesberg-2026-06-30T01-37-17-121Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T01-38-39-105Z`;
- `python scripts\scan_authority_surfaces.py`;
- `cd frontend && npm run build`;
- `git diff --check`.

Behavior parity statement:

- Operator browser verification remains read-only and did not mutate task,
  deadline, stopwatch-session, pause-event, feedback, exposure, or
  notification counts.
- Holmesberg mutable smoke created synthetic task/deadline/timer/brain-dump
  artifacts, proved only one active timer can run, then voided all synthetic
  tasks with `test_contamination` and soft-deleted all synthetic deadlines.

Rollback note:

- Revert the multi-account mutable browser verification seam commit only. This
  removes test harness changes without changing runtime behavior. If rollback
  happens after a failed mutable smoke, inspect that run's `result.json` under
  `tmp/browser-smoke/*` for any cleanup errors before manual data repair.

## S1c - Static Refactor Contract Scan

Commit: static refactor contract scan seam commit.

Changed authority:

- No product/runtime authority changed.
- Added hard static checks for refactor contracts that are precise enough to
  enforce before larger extraction:
  - workers must not emit browser render truth;
  - provider completion event construction stays owned by DeadlineManager;
  - analytics must not instantiate exposure rows directly;
  - frontend must not resurrect a Jarvis runtime client.

Removed paths:

- None.

Parked paths:

- Frontend behavioral/archetype/insight copy review remains report-only until
  ClaimCompiler/user-facing claim boundaries are explicitly reworked.
- Generic `db.commit()` enforcement remains owned by the mutation surface
  registry scan; this seam does not replace that registry.

Moved authority:

- No authority moved. `scripts/scan_refactor_contracts.py` is an enforcement
  harness for existing contracts.

Tests and verification:

- `python -m py_compile scripts\scan_refactor_contracts.py`;
- `python scripts\scan_refactor_contracts.py --fail-on-errors --pretty`;
- `python scripts\scan_refactor_contracts.py --include-review`;
- `python scripts\scan_authority_surfaces.py --fail-on-missing`;
- `git diff --check`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_multi_account_browser_smoke.ps1 -Topology public`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T01-48-46-521Z`.

Behavior parity statement:

- This seam only adds static scanning. It does not change runtime imports,
  routes, mutation paths, frontend behavior, provider sync behavior, exposure
  lifecycle behavior, or user-visible copy.

Rollback note:

- Revert the static refactor contract scan seam commit only. Runtime behavior
  is unchanged, so rollback does not require data repair.

## S1c - Alembic Fresh Database Smoke

Commit: Alembic fresh database smoke seam commit.

Changed authority:

- No product/runtime authority changed.
- Added a repeatable local migration smoke wrapper that creates a temporary
  SQLite database, runs `alembic upgrade head`, verifies `alembic current`, and
  deletes the temporary database when it owns the path.

Removed paths:

- None.

Parked paths:

- Postgres/Supabase migration smoke remains a production-ops runbook action,
  not a local destructive test.
- Schema migration authority remains unchanged; this seam only tests existing
  migrations.

Moved authority:

- No authority moved. `scripts/run_alembic_fresh_smoke.ps1` is a regression
  gate for schema history.

Tests and verification:

- PowerShell parser check for `scripts\run_alembic_fresh_smoke.ps1`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_alembic_fresh_smoke.ps1`, which reported `alembic_current: "056 (head)"`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T01-52-39-668Z`.

Behavior parity statement:

- This seam only adds a local test wrapper. It does not change migrations,
  models, runtime database URLs, application boot, or production data.

Rollback note:

- Revert the Alembic fresh database smoke seam commit only. Runtime behavior is
  unchanged, and the smoke-owned temporary database is deleted automatically.

## S1c - One-Command Verification Stack

Commit: S1c verification stack seam commit.

Changed authority:

- No product/runtime authority changed.
- Added one repeatable verification command for the S1c refactor gate:
  `scripts/run_s1c_verification_stack.ps1`.
- The stack runs diff hygiene, authority scans, static refactor contract scan,
  fresh Alembic smoke, backend suite, frontend production build, multi-account
  browser smoke, and operator read-only browser stress.

Removed paths:

- None.

Parked paths:

- Holmesberg mutable smoke remains opt-in via `-IncludeMutable` because it
  intentionally creates and then voids synthetic rows.
- CI wiring for this stack remains parked until branch/CI runtime cost is
  decided.

Moved authority:

- No authority moved. The wrapper only orchestrates existing verification
  commands.

Tests and verification:

- PowerShell parser check for `scripts\run_s1c_verification_stack.ps1`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology public`;
- stack result:
  - `git diff --check` passed;
  - `scan_authority_surfaces.py --fail-on-missing` passed with 0 missing owners;
  - `scan_refactor_contracts.py --fail-on-errors` passed with 0 errors;
  - Alembic fresh smoke reported `056 (head)`;
  - backend suite: 1055 passed, 1 xfailed;
  - frontend production build passed;
  - multi-account browser smoke passed;
  - operator read-only browser stress passed with screenshots and JSON under
    `tmp/operator-readonly-stress-2026-06-30T02-00-09-112Z`.

Behavior parity statement:

- This seam only adds an orchestration wrapper. It does not change runtime
  code, app behavior, database schema, public topology, or production data.

Rollback note:

- Revert the S1c verification stack seam commit only. Individual underlying
  verification scripts remain available from earlier seams.

## R2 - Operator Legacy Reminder Duplicate Fingerprint

Commit: Operator legacy reminder duplicate fingerprint seam commit.

Changed authority:

- No notification delivery authority changed.
- Tightened `/operator` Redis-pending duplicate detection so canonical
  notifications still use explicit `dedupe_key` or stable target ids, while
  legacy no-target payloads are grouped by privacy-safe content fingerprint
  instead of by notification `type` alone.
- Added `identity_source` to duplicate breakdown diagnostics so operators can
  distinguish dedupe-key, target-id, and legacy-content duplicate buckets.

Removed paths:

- None.

Parked paths:

- No production Redis cleanup was performed. If stale pending user
  notifications remain after deployment, production data repair/purge remains a
  user-approved operator action.
- Notification source freshness instrumentation remains open under R2.

Moved authority:

- No authority moved. The lifecycle ledger remains the durable measurement
  boundary; Redis remains a best-effort pending queue snapshot.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\operator.py scripts\scan_refactor_contracts.py`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py -q`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology public`;
- stack result:
  - `git diff --check` passed;
  - `scan_authority_surfaces.py --fail-on-missing` passed with 0 missing owners;
  - `scan_refactor_contracts.py --fail-on-errors` passed with 0 errors;
  - Alembic fresh smoke reported `056 (head)`;
  - backend suite: 1056 passed, 1 xfailed;
  - frontend production build passed;
  - multi-account browser smoke passed;
  - operator read-only browser stress passed with screenshots and JSON under
    `tmp/operator-readonly-stress-2026-06-30T02-14-03-170Z`.

Behavior parity statement:

- User notification queueing, rendering, acknowledgement, dismissal, action,
  and OpenClaw mirroring behavior are unchanged.
- Existing identical legacy reminder payloads still count as duplicate pending
  prompts and still block cohort expansion.
- Distinct legacy reminder messages no longer collapse into one false duplicate
  bucket when they lack task/session/firing ids.

Rollback note:

- Revert the operator fingerprint seam commit only. Rollback restores the prior
  type-only legacy duplicate grouping and does not require data repair.

## R2 - Operator First-Viewport Ignore Clarity

Commit: Operator first-viewport ignore clarity seam commit.

Changed authority:

- No backend readiness authority changed.
- `/operator` now states a conservative first-viewport `safe to ignore` answer:
  green readiness shows `accepted risks`; red/yellow readiness shows `none yet`.
- The minimum-fix list now visually distinguishes blocker items from warning
  items using existing readiness blocker ids.

Removed paths:

- None.

Parked paths:

- Full post-deploy screenshot verification of the new frontend copy remains
  dependent on public deployment.
- Local `localhost:3002` UI verification was attempted but blocked by local
  backend reachability; no product state changed.

Moved authority:

- No authority moved. The frontend still renders backend readiness state and
  does not derive cohort authority locally.

Tests and verification:

- `cd frontend && npm run build`;
- attempted local production frontend render on `localhost:3002`, blocked by
  local backend fetch failure before cockpit render;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T02-21-45-637Z`.

Behavior parity statement:

- This is display-only. It does not change readiness thresholds, blocker
  classification, notification/exposure lifecycle, dashboard polling, or any
  mutation path.
- The first viewport is more explicit that non-green warnings are not safe to
  ignore without acceptance.

Rollback note:

- Revert the operator first-viewport clarity seam commit only. Runtime backend
  behavior and production data are unaffected.

## R2 - Operator Browser Read-Only Snapshot Gate

Commit: Operator browser read-only snapshot gate seam commit.

Changed authority:

- No product authority changed.
- Strengthened `scripts/browser_stress_operator_readonly.mjs` so browser
  verification snapshots selected `/v1/operator/dashboard` invariants before
  and after the route pass.
- The snapshot covers cohort invite status, notification lifecycle counts,
  state invariants, clean-trace basis, analytic blockers, and provider
  integrity counts.

Removed paths:

- None.

Parked paths:

- Redis key-level inspection remains outside the browser smoke because it
  requires privileged runtime access. The dashboard-exposed lifecycle snapshot
  is the public/operator verification boundary for now.

Moved authority:

- No authority moved. The script observes `/operator`; it does not mutate
  product state or define readiness semantics.

Tests and verification:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`;
- result: operator account resolved, all desktop/mobile core routes loaded,
  exported operator data counts were unchanged, dashboard invariant snapshot had
  zero diffs, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T02-26-03-913Z`.

Behavior parity statement:

- Verification is stricter, but runtime behavior is unchanged.
- The script still treats the operator account as read-only and does not create
  tasks, deadlines, notifications, exposure rows, or Redis entries.

Rollback note:

- Revert the browser read-only snapshot gate seam commit only. This weakens
  verification coverage but does not affect runtime code or production data.

## R3 - Frontend Query Key Contract Seed

Commit: Frontend query key contract seed seam commit.

Changed authority:

- No product/runtime authority changed.
- Added `frontend/lib/query-keys.ts` as the central frontend query-key and
  domain-invalidation contract seed.
- Adopted the central query keys only on low-risk operator/admin dashboard
  pages.

Removed paths:

- None.

Parked paths:

- Pulse/Today/Calendar/Table task and timer query invalidation remain parked
  for later R3 extraction seams with characterization coverage.
- Broad `invalidateDomain()` adoption remains parked until each domain's
  cache dependencies are named and verified.

Moved authority:

- No authority moved. Frontend pages still fetch the same backend endpoints and
  do not define behavioral claims or readiness semantics locally.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_multi_account_browser_smoke.ps1 -Topology public`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T02-30-44-750Z`.

Behavior parity statement:

- Query keys retain the same string values and endpoint fetches. Admin email
  telemetry keeps the same campaign and since-days dimensions.
- No user-facing flow, cache invalidation behavior, API path, mutation path, or
  topology behavior changed.

Rollback note:

- Revert the query key contract seed commit only. This restores inline query
  key arrays on operator/admin pages and removes the unused broader contract.

## R3 - New Task Modal Time Helper Extraction

Commit: New task modal time helper extraction seam commit.

Changed authority:

- No task creation authority changed.
- Extracted pure local date/time/duration formatting helpers from
  `frontend/components/new-task-modal.tsx` into `frontend/lib/task-time.ts`.
- `NewTaskModal` now imports those helpers while retaining its existing state
  machine, nudge exposure handling, deadline preview handling, and submit/edit
  logic.

Removed paths:

- Removed duplicate inline helper bodies from `NewTaskModal`.

Parked paths:

- Creation nudge state/effects remain in the modal until a separate
  characterization seam.
- Deadline preview state/effects remain in the modal until a separate seam.

Moved authority:

- No product authority moved. The extracted module owns only pure local time
  math and display phrasing.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, created/voided 3 synthetic tasks and created/deleted 2 synthetic deadlines under
  `tmp/browser-smoke/holmesberg-2026-06-30T02-38-16-562Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T02-39-32-887Z`.

Behavior parity statement:

- Default start rounding, target-date defaulting, duration math,
  AM/PM-recovery math, time-of-day bucketing, 5-minute rounding, and plan-delta
  copy are moved without semantic changes.
- No API endpoint, cache key, mutation path, exposure write, task creation
  payload, or cleanup behavior changed.

Rollback note:

- Revert the time helper extraction commit only. This restores inline helpers in
  `NewTaskModal` and removes `frontend/lib/task-time.ts`; no data repair is
  needed.

## R3 - Brain Dump Binding Helper Extraction

Commit: Brain dump binding helper extraction seam commit.

Changed authority:

- No brain-dump parser, commit, task, or deadline authority changed.
- Extracted shared UI-local binding helpers from the Pulse quick modal and
  onboarding flow into `frontend/lib/brain-dump-ui.ts`.
- The shared helper owns only binding choice defaults, binding-key fallback, and
  naive local timestamp formatting for existing brain-dump payloads.

Removed paths:

- Removed duplicate inline `localIsoNow()`, `bindingKey()`, and
  `initialBindingChoices()` implementations from:
  - `frontend/components/pulse/BrainDumpQuickModal.tsx`;
  - `frontend/components/onboarding-flow.tsx`.

Parked paths:

- Failure and retry copy remain local because Pulse and onboarding present
  slightly different recovery UX.
- Commit-key generation, retry editing, and route-specific cache invalidation
  remain parked for later R3 seams.
- Backend parser/commit behavior remains unchanged and is not moved in this
  frontend extraction.

Moved authority:

- No product authority moved. Parser and commit API authority remains in
  `frontend/lib/brain-dump.ts` plus the backend brain-dump endpoints.
- `frontend/lib/brain-dump-ui.ts` is a shared UI helper, not a behavioral claim
  or mutation authority.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, created/voided 3 synthetic tasks and created/deleted 2 synthetic deadlines under
  `tmp/browser-smoke/holmesberg-2026-06-30T02-44-51-216Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T02-49-26-315Z`.

Behavior parity statement:

- Binding keys use the same `binding_id` fallback and task/deadline composite
  fallback as before.
- Tier-1 auto bindings still default to `yes` once per task, and competing
  bindings for the same task still default to `no`.
- Local timestamp formatting keeps the same naive local-time string shape.
- No endpoint, mutation payload, cache key, task/deadline cleanup behavior,
  exposure write, or onboarding completion behavior changed.

Rollback note:

- Revert the brain-dump helper extraction commit only. This restores inline
  helper bodies in the two components and removes `frontend/lib/brain-dump-ui.ts`;
  no data repair is needed.

## R3 - Brain Dump Failure Copy Helper Extraction

Commit: Brain dump failure copy helper extraction seam commit.

Changed authority:

- No brain-dump parser, retry, commit, task, or deadline authority changed.
- Moved shared machine-reason-to-user-copy mapping into
  `frontend/lib/brain-dump-ui.ts`.
- Preserved the prior Pulse-only duplicate-deadline copy via an explicit
  option so onboarding keeps its old default copy for that reason.

Removed paths:

- Removed duplicate inline `failureCopy()` implementations from:
  - `frontend/components/pulse/BrainDumpQuickModal.tsx`;
  - `frontend/components/onboarding-flow.tsx`.

Parked paths:

- Pulse and onboarding `retryCopy()` functions remain local because they
  intentionally give different retry guidance.
- Failure review state machines remain local to each surface until a separate
  reducer extraction seam.

Moved authority:

- No product authority moved. The shared helper owns display copy only and
  does not decide whether an item may be committed or retried.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, created/voided 3 synthetic tasks and created/deleted 2 synthetic deadlines under
  `tmp/browser-smoke/holmesberg-2026-06-30T02-55-42-283Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T02-56-54-801Z`.

Behavior parity statement:

- Existing failure reason strings map to the same user-visible strings on both
  surfaces.
- Pulse still renders the duplicate-deadline special copy; onboarding still
  falls back to the prior generic failure copy for that reason.
- Retry hints, retry actions, parser payloads, commit payloads, cache
  invalidation, and cleanup behavior are unchanged.

Rollback note:

- Revert the failure-copy extraction commit only. This restores inline
  `failureCopy()` functions in both components and keeps all data untouched.

## R3 - Brain Dump Query Key Contract Adoption

Commit: Brain dump query key contract adoption seam commit.

Changed authority:

- No cache invalidation behavior, task authority, deadline authority, or
  brain-dump commit authority changed.
- Added central query-key names for task/deadline/me/tasks-range/pressure-map
  frontend caches in `frontend/lib/query-keys.ts`.
- `BrainDumpQuickModal` now imports those keys instead of spelling raw query
  key arrays inline after a successful commit.

Removed paths:

- Removed raw query-key array literals from the Pulse brain-dump commit success
  invalidation block.

Parked paths:

- Wider adoption across Today, Calendar, stopwatch surfaces, pressure map, and
  table remains parked for separate seams with their own characterization.
- Domain-level invalidation groups beyond admin/operator remain parked until
  each product domain's dependencies are named and tested.

Moved authority:

- No product authority moved. The query-key module names cache keys only; it
  does not decide when a mutation is valid or what backend state changes.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, created/voided 3 synthetic tasks and created/deleted 2 synthetic deadlines under
  `tmp/browser-smoke/holmesberg-2026-06-30T03-00-48-680Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T03-02-01-296Z`.

Behavior parity statement:

- The modal still invalidates the same five cache prefixes after commit:
  tasks, deadlines, me, tasks-range, and pressure-map.
- Brain-dump parse/commit payloads, cleanup behavior, task/deadline writes,
  and UI review behavior are unchanged.

Rollback note:

- Revert the query-key adoption commit only. This restores the raw query-key
  arrays in `BrainDumpQuickModal` and removes the new central key constants.

## R3 - Pressure Map Display Helper Extraction

Commit: Pressure map display helper extraction seam commit.

Changed authority:

- No pressure-map computation, evidence estimate, calibration, task creation,
  or recovery-plan authority changed.
- Moved pure pressure-map display helpers into
  `frontend/lib/pressure-map-ui.ts`.

Removed paths:

- Removed inline `fmtHours()`, timing/due/trust label helpers,
  `pressureClass()`, and `genericPressureCopy()` from
  `frontend/components/pulse/PulseAcademicPressureMap.tsx`.

Parked paths:

- Evidence estimate math, linked-deadline history, cold-start calibration,
  recovery-plan row construction, and task creation remain local to the
  component until separately characterized.
- Pressure-map cache invalidation remains inline until the task/pressure domain
  invalidation seam.

Moved authority:

- No product authority moved. The extracted module owns display labels and copy
  normalization only.
- Recovery blocks still write through the existing task creation API path.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, created/voided 3 synthetic tasks and created/deleted 2 synthetic deadlines under
  `tmp/browser-smoke/holmesberg-2026-06-30T03-06-17-456Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T03-07-26-160Z`.

Behavior parity statement:

- Hours, timing labels, trust labels, pressure item classes, and academic-copy
  normalization are moved without semantic changes.
- Pressure-map API reads, exposure acknowledgement behavior, recovery preview,
  task creation payloads, and cleanup behavior are unchanged.

Rollback note:

- Revert the pressure-map display helper extraction commit only. This restores
  the inline display helpers and removes `frontend/lib/pressure-map-ui.ts`;
  no data repair is needed.

## R3 - Pressure Map Query Key Contract Adoption

Commit: Pressure map query key contract adoption seam commit.

Changed authority:

- No recovery-plan creation, pressure-map computation, or cache invalidation
  behavior changed.
- `PulseAcademicPressureMap` now imports central task, deadline, and
  pressure-map query keys instead of spelling raw arrays inline after recovery
  block creation.

Removed paths:

- Removed raw `["tasks"]`, `["pressure-map"]`, and `["deadlines"]` query-key
  arrays from the pressure-map commit success invalidation block.

Parked paths:

- Wider query-key adoption across Today, Calendar, Table, and stopwatch
  surfaces remains parked for separate seams.
- Domain-level task/pressure invalidation remains parked until every dependent
  cache is named and covered.

Moved authority:

- No product authority moved. The query-key module names cache keys only and
  does not authorize task creation, recovery preview, or evidence estimates.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, created/voided 3 synthetic tasks and created/deleted 2 synthetic deadlines under
  `tmp/browser-smoke/holmesberg-2026-06-30T03-10-54-620Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T03-12-06-892Z`.

Behavior parity statement:

- Recovery-plan commit still invalidates the same three cache prefixes:
  tasks, pressure-map, and deadlines.
- Task creation payloads, conflict behavior, force-create behavior, and
  dashboard read-only behavior are unchanged.

Rollback note:

- Revert the pressure-map query-key adoption commit only. This restores the raw
  query-key arrays in `PulseAcademicPressureMap` and leaves runtime data
  untouched.

## R3 - Stopwatch Status Query Key Contract Adoption

Commit: Stopwatch status query key contract adoption seam commit.

Changed authority:

- No stopwatch lifecycle, optimistic update, task state, undo, calendar, or
  Pulse authority changed.
- Added `queryKeys.stopwatchStatus` and replaced raw stopwatch-status query
  key arrays in frontend stopwatch consumers.

Removed paths:

- Removed raw `["stopwatch-status"]` query-key arrays from:
  - `frontend/components/active-timer-banner.tsx`;
  - `frontend/components/pulse/PulseFocusCard.tsx`;
  - `frontend/components/pulse/PulseQuickCaptureV2.tsx`;
  - `frontend/components/pulse/PulseReentryQueue.tsx`;
  - `frontend/app/(app)/today/page.tsx`;
  - `frontend/app/(app)/calendar/page.tsx`;
  - `frontend/components/undo-toast-host.tsx`.

Parked paths:

- Dynamic task-date query keys, calendar-event query keys, pause prediction
  keys, integrations keys, and task evidence keys remain parked for separate
  cache-contract seams.
- Stopwatch controller extraction remains parked; this seam only names the
  cache key.

Moved authority:

- No mutation authority moved. The query-key module names the stopwatch status
  cache key only.
- Optimistic pause/resume/start/stop/switch logic remains in the existing
  surfaces.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, verified deadline/task creation, one-active-timer rejection, stopwatch start/pause/resume/stop, brain dump commit, and cleanup under
  `tmp/browser-smoke/holmesberg-2026-06-30T03-18-59-371Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T03-20-05-829Z`.

Behavior parity statement:

- All status queries, cancellations, optimistic reads/writes, rollbacks, and
  invalidations still target the same stopwatch-status key.
- One-active-timer enforcement, pause/resume, clean stop, undo invalidation,
  calendar live status rendering, and operator read-only invariants are
  unchanged.

Rollback note:

- Revert the stopwatch query-key adoption commit only. This restores raw
  stopwatch-status query-key arrays and keeps runtime data untouched.

## R3 - Timer Refresh Static Query Key Adoption

Commit: Timer refresh static query key adoption seam commit.

Changed authority:

- No timer, task, pressure-map, deadline, undo, or user-state authority
  changed.
- Added `queryKeys.tasksEvidence` and replaced static refresh key literals in
  timer-adjacent frontend surfaces.

Removed paths:

- Removed raw static task/deadline/me/pressure/task-evidence query-key arrays
  from:
  - `frontend/components/active-timer-banner.tsx`;
  - `frontend/components/pulse/PulseFocusCard.tsx`;
  - `frontend/components/pulse/PulseReentryQueue.tsx`;
  - `frontend/components/undo-toast-host.tsx`.

Parked paths:

- Dynamic task-date query keys, calendar-event keys, integration keys, pause
  prediction keys, and insight keys remain parked for separate seams.
- The legacy `["operator-dashboard"]` undo invalidation remains unchanged until
  the operator/admin cache contract is reviewed separately.

Moved authority:

- No mutation authority moved. Query keys are names only; optimistic timer and
  task-state logic remain in their existing surfaces.

Tests and verification:

- `cd frontend && npm run build`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology public`, verified timer start, parallel-active rejection, pause/resume, clean stop, brain dump commit, and cleanup under
  `tmp/browser-smoke/holmesberg-2026-06-30T03-24-57-128Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T03-26-03-011Z`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology public`, passed authority scan, static refactor contract scan, Alembic fresh DB smoke, full backend pytest suite, frontend production build, multi-account browser smoke, and operator read-only browser stress; S1C operator screenshots and JSON under
  `tmp/operator-readonly-stress-2026-06-30T03-32-21-534Z`.

Behavior parity statement:

- Timer refresh paths still invalidate the same static cache prefixes:
  tasks, tasks-range, tasks-evidence, pressure-map, me, deadlines, and
  stopwatch-status as applicable per surface.
- Undo invalidation still targets the same set of caches, including the legacy
  operator-dashboard key.
- No task payload, stopwatch request, optimistic state update, rollback path,
  or cleanup behavior changed.

Rollback note:

- Revert the timer refresh static query-key adoption commit only. This restores
  the raw static query-key arrays and leaves runtime data untouched.

## S1c/R3 - Reusable Post-Wave Dogfood Loop

Commit: Reusable post-wave dogfood loop seam commit.

Changed authority:

- No product/runtime authority changed.
- Added `scripts/run_post_wave_dogfood_loop.ps1` as the reusable verification
  wrapper for post-wave checks.
- Added `docs/runbooks/post_wave_dogfood_loop.md` as the canonical post-wave
  dogfood runbook.
- Added `docs/audits/post_wave_dogfood_gap_audit_2026_06_30.md` to preserve
  six-agent synthesis on documented behavior, current proof, and missing UI
  dogfood coverage.

Removed paths:

- None.

Parked paths:

- Targeted Playwright dogfood scripts remain parked for:
  brain dump modal, `NewTaskModal`, pressure-map preview/commit, timer UI,
  notification lifecycle, insights states, calendar drag/resize, and table
  correction/export flows.
- Legacy direct mutation static hard-fail remains parked until the R4 backend
  extraction seams have stable owners.

Moved authority:

- Post-wave verification ownership moved from ad hoc chat instructions to the
  reusable wrapper/runbook pair.
- Operator account remains read-only; Holmesberg remains the mutable chaos
  account when `-IncludeMutable` is explicitly passed.

Tests and verification:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode quick -WaveName reusable-loop-v2-smoke`, passed cookie checks, `git diff --check`, runtime topology verifier, multi-account browser smoke, and operator read-only stress.
- Output directory:
  `tmp/post-wave-dogfood/20260630-213059-reusable-loop-v2-smoke-quick-public`.
- Operator read-only stress result:
  `tmp/operator-readonly-stress-2026-06-30T18-33-26-728Z`.

Behavior parity statement:

- No application code or runtime behavior changed.
- The new wrapper defaults to read-only verification unless `-IncludeMutable`
  is explicitly provided.
- Cookie checks now hard-fail missing/inconsistent user-env/registry values
  before browser smoke starts.

Rollback note:

- Revert the reusable loop commit only. Existing underlying verification
  scripts remain unchanged.

## S1c/R3 - Full Documented-Surface Dogfood Loop Proof

Commit: uncommitted verification hardening pass.

Changed authority:

- No product/runtime authority changed.
- Hardened the Holmesberg product-loop dogfood verifier so it uses real
  browser-visible state and bounded lifecycle identifiers instead of
  mutation-prone diagnostic probes.
- Added stable frontend test ids for deadline-suggestion choices in
  `NewTaskModal`.

Removed paths:

- Removed the product-loop diagnostic branch that called the
  `task_creation_nudge_lookup` analytics endpoint merely to explain a missing
  selector. That diagnostic call could create a delivered exposure decision
  without browser render proof when the modal already displayed the nudge.

Parked paths:

- Calendar drag/resize, provider credential mutation, OpenClaw pending drain,
  and hard account delete remain gated.
- Targeted Playwright scripts still remain for brain-dump retry/partial
  failure, pressure-map commit, long-lived timer pause/navigation,
  notification action/expiry, forced insights states, calendar mutation, and
  table correction/export. NewTaskModal branch coverage was completed in the
  later `S1c/R3 - NewTaskModal Branch Coverage Proof` entry.

Moved authority:

- No product authority moved.
- The verifier now treats operator checks as read-only cockpit checks and
  Holmesberg checks as mutable product-loop checks.

Tests and verification:

- Reconciled one synthetic dogfood diagnostic exposure row by browser-render
  acknowledgement through the public exposure lifecycle API:
  `f4b3a47a-3f27-4500-90fb-f071c6c48d86`.
- Confirmed Holmesberg export had `danglingCount: 0` for actionable exposure
  decisions after reconciliation.
- `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`, screenshots and JSON under
  `tmp/operator-readonly-stress-2026-07-01T01-09-52-781Z`;
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode standard -IncludeProductLoop -WaveName full-documented-surface-chain`, output under
  `tmp/post-wave-dogfood/20260701-041138-full-documented-surface-chain-standard-public`;
- Nested Holmesberg product-loop result:
  `tmp/post-wave-dogfood/20260701-041138-full-documented-surface-chain-standard-public/holmesberg-product-loop/result.json`;
- Final operator read-only stress result:
  `tmp/operator-readonly-stress-2026-07-01T01-21-18-436Z`.

Behavior parity statement:

- Operator account stayed read-only. Operator dashboard/export counts and
  invariant snapshots did not change before/after `/operator` browser reads.
- Holmesberg product-loop writes remained synthetic and scoped to the
  non-operator chaos account.
- The product loop proved deadline creation, task creation, explicit deadline
  binding, brain-dump write-free parse and explicit commit, timer
  start/pause/resume/stop, pause-event export, task delta export/table display,
  creation-nudge exposure render acknowledgement, pressure-map render metadata,
  notification render/dismiss terminal lifecycle, privacy scans, and cleanup.
- Operator readiness remained yellow only because of the known
  `no_closed_sessions_last_14d` measurement-integrity blocker; notification
  and exposure blockers were zero.

Rollback note:

- Revert only the verifier/test-id hardening changes if the harness itself must
  be rolled back. Runtime data repair is not required for the verifier changes.
  The one synthetic exposure reconciliation already reflects an actual
  browser-visible dogfood nudge and should remain as render truth.

## S1b/R3 - Queued Notification Cockpit Classification And Conflict Branch Proof

Commit: uncommitted operator-cockpit and dogfood coverage pass.

Changed authority:

- Operator cockpit now treats queued, delayed, failed, and suppressed output
  decisions as non-actionable missing-render rows for the critical
  `exposure_without_render_count` blocker.
- Queued notification decisions are still observable through
  `queued_without_render_count`; the row is not hidden, but queue insertion is
  not treated as render-required exposure.
- The Holmesberg product-loop verifier now proves the `NewTaskModal`
  duration-nudge Keep path and overlapping-task soft-conflict Create anyway
  branch through the public browser UI.

Removed paths:

- None.

Parked paths:

- NewTaskModal branch coverage was completed in the later
  `S1c/R3 - NewTaskModal Branch Coverage Proof` entry.
- Calendar drag/resize, provider credential mutation, OpenClaw pending drain,
  hard account delete, notification action/expiry, and forced insights states
  remain gated or targeted.

Moved authority:

- No user/product mutation authority moved.
- Readiness classification now aligns with the notification/exposure doctrine:
  queue is not exposure, browser render is render truth, and interaction
  outcome is separate from render truth.

Tests and verification:

- Product-loop failure artifact that exposed a stale public selector:
  `tmp/browser-product-loop/2026-07-01T01-26-06-577Z/failure.png`.
- Corrected the dogfood selector fallback for public builds and reran:
  `tmp/browser-product-loop/2026-07-01T01-28-28-470Z/result.json`.
- Targeted backend regression:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_operator_dashboard.py::test_operator_dashboard_blocks_on_exposure_without_render tests/test_operator_dashboard.py::test_operator_dashboard_does_not_block_on_suppressed_exposures tests/test_operator_dashboard.py::test_operator_dashboard_does_not_block_on_queued_notification_decisions -q`
- Restarted the public backend after the cockpit classification fix and
  verified operator read-only stress:
  `tmp/operator-readonly-stress-2026-07-01T01-36-58-855Z`.
- Full reusable post-wave wrapper:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode standard -IncludeProductLoop -WaveName full-documented-surface-chain-conflict-branch`
- Full wrapper output:
  `tmp/post-wave-dogfood/20260701-043838-full-documented-surface-chain-conflict-branch-standard-public`.
- Nested Holmesberg product-loop result:
  `tmp/post-wave-dogfood/20260701-043838-full-documented-surface-chain-conflict-branch-standard-public/holmesberg-product-loop/result.json`.
- Final operator read-only stress result:
  `tmp/operator-readonly-stress-2026-07-01T01-48-03-021Z`.

Behavior parity statement:

- Operator account stayed read-only before and after the mutable Holmesberg
  product loop. Dashboard/export counts, route counts, and dashboard snapshots
  did not change on `/operator` browser reads.
- `exposure_without_render_count`, `duplicate_prompt_count`, and
  `render_without_exposure_count` were zero after the full wrapper.
- Operator readiness remained yellow only because of
  `no_closed_sessions_last_14d`; the cockpit blocker is concrete and not a
  stale K-label.
- Holmesberg synthetic writes remained scoped to the non-operator chaos
  account and cleanup left no active timer.

Rollback note:

- Revert the operator dashboard classification change if queued worker
  decisions must again be treated as actionable render-required exposure. That
  would intentionally violate the current notification/exposure doctrine and
  should require an explicit exposure-retention decision.
- Revert only the dogfood selector/branch additions if the harness needs to be
  rolled back; they do not change user/product runtime authority.

## S1c/R3 - NewTaskModal Branch Coverage Proof

Commits:

- `2c1f7b2 test: cover new task modal branch flows`
- `eb4941a docs: record new task branch dogfood proof`

Changed authority:

- No product/runtime authority changed.
- Expanded the Holmesberg product-loop verifier to cover additional
  `NewTaskModal` branches through public browser runtime.
- Added test-only selectors for category/custom-category controls so the
  browser verifier can prove custom-category persistence without relying on
  brittle CSS shape.

Removed paths:

- None.

Parked paths:

- Brain-dump partial failure/retry/edit, pressure-map recovery commit,
  long-lived timer/navigation, notification action/expiry, forced insights
  states, calendar mutation, table correction/export, provider credentials,
  and hard account delete remain targeted or gated.
- `NewTaskModal` nudge absent/error states and rapid double-submit races remain
  targeted.

Moved authority:

- No product authority moved.
- Browser verification now treats deadline-preview suggestions as
  exposure-sensitive render surfaces with captured request/response diagnostics.

Tests and verification:

- Focused Holmesberg product-loop browser pass:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_product_loop_dogfood.ps1 -Topology public -RunId newtask-branches-20260701-053720`
- Focused output:
  `tmp/browser-product-loop/2026-07-01T02-37-21-583Z/result.json`.
- Operator read-only browser stress after the focused mutable pass:
  `tmp/operator-readonly-stress-2026-07-01T02-41-57-136Z`.
- Full reusable post-wave wrapper:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode standard -IncludeProductLoop -WaveName new-task-branch-coverage`
- Full wrapper output:
  `tmp/post-wave-dogfood/20260701-054334-new-task-branch-coverage-standard-public`.
- Nested Holmesberg product-loop result:
  `tmp/post-wave-dogfood/20260701-054334-new-task-branch-coverage-standard-public/holmesberg-product-loop/result.json`.
- Final operator read-only stress result:
  `tmp/operator-readonly-stress-2026-07-01T02-54-16-423Z`.
- `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs`.

Behavior parity statement:

- Operator account stayed read-only; dashboard/export counts, route counts, and
  dashboard snapshots did not change on `/operator` browser reads.
- Holmesberg synthetic writes remained scoped to the non-operator chaos account
  and cleanup left no active timer.
- Public browser proof now covers `NewTaskModal` no-deadline, pick-another,
  custom category, edit mode, terminal-deadline API rejection, terminal deadline
  picker exclusion, duration-nudge Use/Keep, and soft-conflict Create anyway.
- Deadline-preview diagnostic captures proved the API returned
  `task.deadline_binding_suggestion` exposure/render metadata for browser
  suggestions.
- The verifier discovered and corrected a harness lie: Playwright
  `isVisible()` is not a real wait for this branch; the deadline suggestion
  helper now uses `waitFor({ state: "visible" })`.
- The verifier also discovered that shared synthetic deadline tokens can
  correctly trigger the production heuristic's multi-competitive suppression;
  branch fixtures now avoid ambiguous shared tokens.

Rollback note:

- Revert only the test-id additions and Holmesberg product-loop branch coverage
  changes if the verifier must be rolled back. No runtime data repair is
  required; synthetic Holmesberg rows were voided/deleted by cleanup.

## S1c/R3 - Brain-Dump Chaos Coverage And Commit Race Fix

Commits:

- `7e08003 fix: guard brain dump commits against double submit`
- `45627f1 test: cover brain dump recovery branches`

Changed authority:

- No product/runtime authority moved.
- Added a synchronous in-flight commit guard to the live Pulse brain-dump modal
  and the older onboarding brain-dump surface so double-clicks cannot race
  React state and submit duplicate commits.
- Expanded the Holmesberg product-loop verifier to cover brain-dump editable
  parsed rows, mixed success/failure review, edit failed item without retyping,
  retry, and duplicate/double-submit prevention.
- Added an opt-in Playwright API proxy for local-predeploy browser verification
  against the public backend. This is test-harness-only and does not change
  production CORS or runtime authority.

Removed paths:

- None.

Parked paths:

- First-run onboarding brain-dump browser coverage remains targeted even though
  the shared commit race was sealed.
- Pressure-map recovery commit, timer refresh/navigation while paused,
  notification action/expiry, forced insights states, calendar mutation, table
  correction/export, provider credentials, and hard account delete remain
  targeted or gated.

Moved authority:

- None.

Tests and verification:

- Public current-frontend failure that exposed the product race:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_product_loop_dogfood.ps1 -Topology public -RunId brain-dump-branches-20260701-2`
- Failure output:
  `tmp/browser-product-loop/2026-07-01T03-07-43-470Z/result.json`.
- Failure found: `brain dump double-submit creates exactly one task` failed
  because the browser created two tasks with the same synthetic title.
- Frontend production builds:
  `cd frontend && npm run build`
  `cd frontend && npm run build:public`
- Script syntax/whitespace:
  `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs`
  `git diff --check`
- Local fixed-frontend browser proof against public backend:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology public --frontend http://localhost:3010 --api https://api.lyraos.org --proxy-api --run-id brain-dump-branches-local-20260701-2`
- Local fixed-frontend output:
  `tmp/browser-product-loop/2026-07-01T03-16-04-260Z/result.json`.
- Operator read-only browser stress after mutable proof:
  `tmp/operator-readonly-stress-2026-07-01T03-21-06-368Z`.

Behavior parity statement:

- Brain-dump parse remains write-free.
- Mixed brain-dump commit now proves one valid task lands while a stale/past
  item stays visible in the failure review.
- `Edit failed items` reopens only the failed item, preserves its text, and the
  edited retry creates the recovered item exactly once.
- Double-submit on the corrected frontend creates exactly one task.
- Holmesberg synthetic writes remained scoped to the non-operator chaos account
  and cleanup left no active timer.
- Operator account stayed read-only; dashboard/export counts, route counts, and
  dashboard snapshots did not change on `/operator` browser reads.

Rollback note:

- Revert the `commitInFlightRef` guards only if a later backend atomic
  idempotency implementation proves duplicate browser commits are impossible
  independently of frontend state.
- Revert only the product-loop branch/proxy additions if the verifier needs to
  roll back. They are harness-only and do not require runtime data repair;
  synthetic Holmesberg rows were voided/deleted by cleanup.

## S1c/R3 - Pressure-Map Recovery Commit Coverage And Lock-In Guard

Changed authority:

- No product/runtime authority moved.
- Added stable pressure-map recovery preview test selectors so the browser
  verifier can target the seeded obligation row instead of relying on brittle
  text-only matching.
- Added a synchronous `commitInFlightRef` guard to the pressure-map plan preview
  lock-in path so double-clicks cannot race React state and create duplicate
  recovery blocks.
- Expanded the Holmesberg product-loop verifier to cover seeded pressure-map
  visibility, preview, dismiss-no-mutation, editable recovery-block preview,
  double-lock commit, deadline binding, planning-footprint provenance, and
  Calendar visibility.
- Added an explicit `--force-pressure-recovery` browser fixture for local
  pre-deploy verification while the public backend keeps real recovery options
  gated by read-only pressure safe mode. The fixture is test-harness-only and
  must preserve the backend gate as an issue/gated item in the result.

Removed paths:

- None.

Parked paths:

- Real backend pressure-map recovery option emission remains gated until
  read-only pressure safe mode is lifted.
- Provider credentials, hard account delete/Redis purge, calendar drag/resize,
  table correction/export, notification action/expiry, forced insights states,
  and OpenClaw pending-drain checks remain targeted or gated.

Moved authority:

- None.

Tests and verification:

- Frontend production builds:
  `cd frontend && npm run build`
  `cd frontend && npm run build:public`
- Script syntax/whitespace:
  `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs`
- Local fixed-frontend browser proof against public backend:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology public --frontend http://localhost:3010 --api https://api.lyraos.org --proxy-api --force-pressure-recovery --run-id pressure-map-local-20260701-9`
- Local fixed-frontend output:
  `tmp/browser-product-loop/2026-07-01T03-58-49-682Z/result.json`.
- Operator read-only browser stress after mutable proof:
  `tmp/operator-readonly-stress-2026-07-01T04-04-02-208Z`.
- Broad Holmesberg cleanup:
  `tmp/browser-product-loop/2026-07-01T04-05-36-403Z/result.json`.

Behavior parity statement:

- Pressure-map horizon reads remain backend read-only.
- Dismissing a recovery preview does not create dogfood tasks, recovery blocks,
  or deadline mutations.
- Real recovery-option emission remains disabled by the public backend's
  read-only pressure safe mode; the forced browser fixture only proves the UI
  commit seam.
- Double-locking the corrected frontend creates exactly one planned recovery
  block.
- The committed block keeps its deadline binding, stays a planned task with no
  execution truth, and records planning-footprint provenance in the description.
- The committed block appears on Calendar before cleanup.
- Holmesberg synthetic writes remained scoped to the non-operator chaos account
  and cleanup left no active timer.
- Operator account stayed read-only; dashboard/export counts, route counts, and
  dashboard snapshots did not change on `/operator` browser reads.

Rollback note:

- Revert the `commitInFlightRef` guard and pressure-map preview test selectors
  only if a later backend atomic idempotency implementation makes duplicate UI
  commits impossible independently of frontend state.
- Revert only the product-loop pressure-map fixture/branch additions if the
  verifier needs to roll back. They are harness-only and do not require runtime
  data repair; synthetic Holmesberg rows/deadlines were cleaned after the pass.

## S1b/S1c - Timer Pause Navigation And Creation-Nudge Exposure Suppression

Changed authority:

- No user-facing feature authority moved.
- Added owner-scoped suppression acknowledgement for existing delivered
  exposure decisions that the authenticated client discards before render.
  This fills the lifecycle gap between backend lookup delivery and browser
  render truth without fabricating render evidence.
- Hardened `NewTaskModal` duration-nudge telemetry:
  - visible `Use` / `Keep` interactions explicitly acknowledge render;
  - render acknowledgement retries tolerate slow backend decision creation;
  - discarded or aborted lookup decisions record suppression evidence instead
    of leaving actionable delivered-without-render rows.
- Expanded the Holmesberg product-loop verifier to cover timer pause survival
  across Pulse refresh, Calendar navigation, Today banner visibility, return to
  Pulse, anchored pause seconds, resume, stop, and exported pause-event
  duration.

Removed paths:

- None.

Parked paths:

- The five existing live `task_creation_nudge_lookup` rows without render or
  suppression evidence remain a production data-repair decision. They were
  created by Holmesberg dogfood runs and should not be silently rewritten
  without an explicit repair/purge decision.
- Public API deployment is required before the browser can prove the new
  suppression endpoint clears future discarded-nudge rows in production.
- Long-lived stale timer sessions over hours/days remain targeted.

Moved authority:

- Existing-delivered exposure suppression is now owned by
  `/v1/exposures/{exposure_id}/ack/suppress`, backed by
  `suppress_existing_surface_decision`.

Tests and verification:

- Backend targeted tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_output_surfaces.py::test_existing_decision_suppression_is_idempotent tests/test_output_surfaces.py::test_existing_decision_suppression_endpoint_rejects_rendered_decision tests/test_output_surfaces.py::test_existing_decision_suppression_endpoint_rejects_cross_account tests/test_operator_dashboard.py::test_operator_dashboard_does_not_block_on_suppressed_exposures tests/test_operator_dashboard.py::test_operator_dashboard_blocks_on_exposure_without_render -q`
- Frontend public production build:
  `cd frontend && npm run build:public`
- Script syntax:
  `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs`
- Local fixed-frontend browser proof against public backend:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology public --frontend http://localhost:3010 --api https://api.lyraos.org --proxy-api --force-pressure-recovery --run-id creation-nudge-ack-local-20260701-3`
- Local fixed-frontend output:
  `tmp/browser-product-loop/2026-07-01T04-29-55-097Z/result.json`.
- Operator read-only browser stress:
  `tmp/operator-readonly-stress-2026-07-01T04-43-21-954Z`.

Behavior parity statement:

- Planned overlapping tasks remain allowed; only active timers remain singular.
- Timer pause state survives refresh and navigation, and the exported pause
  event records non-zero paused duration after resume/stop.
- Creation nudge `Use` and `Keep` remain instant UI actions; telemetry retries
  in the background and does not block the user.
- Render truth is only recorded for visible nudge cards. Discarded backend
  lookup decisions are suppression evidence, not fake render evidence.
- Operator account stayed read-only; dashboard/export counts, route counts, and
  dashboard snapshots did not change on `/operator` browser reads.

Rollback note:

- Revert the suppression endpoint/helper and frontend suppression calls if a
  later output-surface state machine centralizes delivered/discarded decisions.
- Revert only the timer dogfood verifier expansion if it becomes flaky; it is
  harness-only and synthetic Holmesberg cleanup leaves no active timer.

## S1c - Notification Action And Expiry Lifecycle Coverage

Changed authority:

- No notification delivery authority moved.
- Added backend fixture coverage and targeted Holmesberg browser proof for web
  notification terminal branches after render removal.
- Added a standalone notification lifecycle dogfood script so action/expiry can
  be verified without touching task creation, timer, or nudge surfaces.

Removed paths:

- None.

Parked paths:

- Real worker-triggered linked-exposure browser outcomes,
  duplicate/cooldown behavior, and OpenClaw drain/redaction remain
  targeted/gated surfaces.
- Failed selector attempts left no pending rows; synthetic failed-run action
  rows were terminalized through the existing acted acknowledgement endpoint.

Moved authority:

- None.

Tests and verification:

- Backend targeted tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_notification_queue_openclaw_mirror.py::test_notification_action_and_expiry_update_after_render_removal tests/test_notification_queue_openclaw_mirror.py::test_web_pending_reserves_and_render_ack_marks_only_rendered tests/test_notification_queue_openclaw_mirror.py::test_lost_unrendered_ack_does_not_mark_rendered -q`
- Script syntax:
  `node --check scripts\browser_notification_lifecycle_dogfood.mjs`
- Holmesberg targeted browser proof:
  `node scripts\browser_notification_lifecycle_dogfood.mjs --frontend https://lyraos.org --api https://api.lyraos.org --run-id notification-lifecycle-20260701-3`
- Holmesberg output:
  `tmp/browser-notification-lifecycle/2026-07-01T04-50-58-661Z/result.json`.
- Operator read-only browser stress:
  `tmp/operator-readonly-stress-2026-07-01T04-52-22-671Z`.

Behavior parity statement:

- Browser render still removes web-pending Redis entries.
- Details-link interaction records `acted` lifecycle truth after render.
- Auto-dismiss records `expired` lifecycle truth after render.
- The targeted script leaves no synthetic pending notification rows.
- Operator account stayed read-only; dashboard/export counts, route counts, and
  dashboard snapshots did not change on `/operator` browser reads.

Rollback note:

- Revert the standalone notification lifecycle browser script and backend
  fixture if this coverage becomes flaky; the runtime notification API did not
  change in this slice.

## S1c - Linked Notification Exposure Backend Invariant

Changed authority:

- No notification or exposure authority moved.
- Added fixture coverage that proves notification render lifecycle can complete
  a linked output-surface exposure only at render time, not queue/reserve time.

Removed paths:

- None.

Parked paths:

- Real worker-triggered linked-exposure browser proof remains gated because no
  public test route mints a worker notification exposure on demand. Do not fake
  this by routing an unrelated creation-nudge/modal exposure through a
  notification toast; that would create invalid telemetry.
- Duplicate/cooldown and OpenClaw mirror redaction remain targeted/gated.

Moved authority:

- None.

Tests and verification:

- Backend targeted tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_notification_queue_openclaw_mirror.py::test_linked_notification_render_records_exposure_once tests/test_notification_queue_openclaw_mirror.py::test_notification_action_and_expiry_update_after_render_removal tests/test_notification_queue_openclaw_mirror.py::test_web_pending_reserves_and_render_ack_marks_only_rendered -q`

Behavior parity statement:

- Queue and reserve still do not create exposure render truth.
- Render acknowledgement of a notification with `surface_id` and `exposure_id`
  creates exactly one `ExposureRenderEvent` and one render `ExposureAckEvent`.
- Later terminal notification outcomes do not duplicate render or ack evidence.
- The browser gap is explicitly carried rather than falsified with an invalid
  surface/channel pairing.

Rollback note:

- Revert the linked-exposure fixture only if output surfaces later centralize
  notification render ownership in a different service. Runtime code did not
  change in this slice.

## S1c - Insights Forced-State Browser Coverage

Changed authority:

- No Insights, ClaimCompiler, or exposure authority moved.
- Added a Playwright fixture that intercepts only `/v1/analytics/insights` to
  force locked, held, unlocked, empty-unlocked, delayed, and error states
  through the real `/insights` page.
- Added `-IncludeInsightsStates` to the reusable post-wave dogfood loop.

Removed paths:

- None.

Parked paths:

- Production-data held/unlocked/error states without API interception remain
  opportunistic because they depend on each account's live clean-trace and
  Rule 11 state.

Moved authority:

- None.

Tests and verification:

- Script syntax:
  `node --check scripts\browser_insights_states_dogfood.mjs`
- Forced-state browser proof:
  `node scripts\browser_insights_states_dogfood.mjs --frontend https://lyraos.org --api https://api.lyraos.org`
- Output:
  `tmp/browser-insights-states/2026-07-01T05-06-44-030Z/result.json`.
- Operator read-only browser stress after the forced-state pass:
  `tmp/operator-readonly-stress-2026-07-01T05-09-06-593Z`.

Behavior parity statement:

- Locked state shows session-denominator copy without held-state language.
- Held state shows concrete clean-stop reopen threshold and does not show the
  contradictory `sessions / min sessions` denominator.
- Unlocked and empty-unlocked states render bounded evidence/copy without
  causal, diagnostic, or identity claims.
- Delayed response shows an in-flight loading skeleton and resolves within the
  senior UI budget.
- Error state stays bounded to a retryable load failure.

Rollback note:

- Revert the forced-state script and `-IncludeInsightsStates` wrapper flag if
  the route interception pattern becomes incompatible with the frontend auth
  shell. Runtime Insights code did not change in this slice.

## E0 - Exposure Forensics And Dogfood Suppression Repair

Changed authority:

- No exposure invariant was weakened.
- The five live `task_creation_nudge_lookup` rows without render or suppression
  evidence were classified and repaired through the canonical owner-scoped
  suppression endpoint:
  `/v1/exposures/{exposure_id}/ack/suppress`.
- The repair created suppression evidence with
  `suppression_reason=dogfood_synthetic_cleanup` and did not create render
  evidence.

Removed paths:

- None.

Parked paths:

- `implementation_green` / `cohort_green` split remains R2 work.
- Notification source freshness is still not instrumented and remains a
  warning/dynamic issue.
- Lack of clean closed sessions remains a cohort/data blocker; do not weaken
  the denominator to make the cockpit green.

Moved authority:

- None. E0 confirmed that existing suppression repair authority belongs to
  `suppress_existing_surface_decision` and the exposure suppression endpoint.

Tests and verification:

- Redacted audit:
  `docs/audits/e0_exposure_forensics_2026_07_01.md`
- Private full-ID snapshot:
  `tmp/e0-exposure-forensics/20260701-155800/PRIVATE_full_ids_do_not_commit.json`
  (ignored; do not commit).
- Redacted snapshots:
  `tmp/e0-exposure-forensics/20260701-155800/redacted_snapshot.json`
  and
  `tmp/e0-exposure-forensics/20260701-155800/after_snapshot_redacted.json`.
- Repair result:
  `tmp/e0-exposure-forensics/20260701-155800/repair_result_redacted.json`.
- Operator API after repair reported `exposure_without_render_count=0`,
  readiness `yellow`, and no cohort blockers.
- Operator read-only browser stress:
  `tmp/operator-readonly-stress-2026-07-01T16-01-59-981Z`.

Behavior parity statement:

- Delivered creation-nudge decisions that never reached browser render are now
  represented as suppression evidence, not fake exposure.
- Operator `/operator` reads remained read-only. Export counts, dashboard
  invariant snapshots, and route counts did not change during browser stress.
- Cohort readiness remains yellow because real data volume and instrumentation
  warnings remain unresolved. The exposure blocker itself is closed.

Rollback note:

- If the repair classification is later found wrong, inspect the private E0
  full-ID snapshot and remove only the five `dogfood_synthetic_cleanup`
  suppression rows, then restore the corresponding decisions to their prior
  delivered state. Do not delete or rewrite unrelated exposure history.

## R2 - Operator Implementation/Cohort Readiness Split

Commit: `ebc4144 operator: split implementation and cohort readiness`.

Changed authority:

- No product mutation authority changed.
- `/operator` now reports implementation correctness separately from cohort
  readiness:
  - `implementation_green` means no current cockpit/invariant blocker is known;
  - `cohort_green` means enough clean real-world evidence exists for trusted
    user expansion.
- Controlled evidence collection is explicit and allowed only when
  implementation is green and all cohort gaps are insufficient-real-data gaps.

Removed paths:

- None.

Parked paths:

- Hosted-public frontend deployment of the first-viewport copy remains pending;
  hosted proof at the time of this seam reported frontend build `a5290f8`.
- `notification_source_freshness_not_instrumented`,
  `invalid_recovery_actions_not_instrumented`, and product-loop/cohort-data
  warnings remain real cohort gaps, not implementation blockers.
- Controlled evidence collection remains false while non-real-data warnings are
  present.

Moved authority:

- No authority moved. The frontend renders backend readiness state and does not
  derive expansion permission locally.
- The operator read-only browser verifier now supports opt-in local-current
  API proxy mode for pre-deploy UI/backend proof. This is test-harness-only and
  does not change production CORS or runtime behavior.

Tests and verification:

- Backend targeted suite:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_operator_dashboard.py -q`
  passed `10`.
- Frontend public production build:
  `cd frontend && npm run build:public` passed.
- Script syntax:
  `node --check scripts\browser_stress_operator_readonly.mjs` passed.
- Whitespace:
  `git diff --check` passed.
- Local-current operator browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r2-implementation-split-local-current-v2`
  wrote `tmp/operator-readonly-stress-r2-implementation-split-local-current-v2/result.json`.
- Hosted-public operator read-only stress:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`
  wrote `tmp/operator-readonly-stress-2026-07-01T16-17-28-027Z/result.json`.
- Harness failure classification:
  running `npm run build:public` while a verifier dev server was active
  corrupted that dev server's `.next` session route. This was classified as a
  verifier/topology bug; the broken verifier was stopped, restarted cleanly on
  `localhost:3013`, and the stricter proof passed before final rebuild.

Behavior parity statement:

- Existing `status` and `safe_to_invite_more_users` semantics are unchanged.
- `/operator` remains read-only: exported operator counts, route counts, and
  dashboard invariant snapshots were unchanged before/after browser reads.
- The current live dashboard state is implementation-green/cohort-yellow:
  exposure-without-render is zero, implementation blockers are empty, and
  cohort gaps are explicit.
- A verifier bug was corrected: one cohort-wide operator test previously
  cleaned only two synthetic user ids while asserting global cohort state. The
  fixture now clears the full synthetic operator-dashboard id range before the
  assertion.
- Browser proof required both backend state and visible first-viewport labels:
  `implementation green`, `cohort green`, and `controlled evidence`.

Rollback note:

- Revert the R2 operator cockpit seam commit only. This removes the new
  readiness fields, frontend display cells, verifier proxy option, and related
  tests/docs without touching production data or mutation paths.

## S1c - Worker Write Drift And Output-Surface Static Gate

Commit: `77bfa02 tools: harden s1c authority drift scans`.

Changed authority:

- No product/runtime authority changed.
- The authority surface scanner now hard-fails worker-job write drift when
  `--fail-on-worker-write-drift` is passed.
- The static refactor contract scanner now hard-fails direct app use of
  output-surface helper functions outside the output-surface/exposure-ledger
  owner modules, and direct legacy `ReflectionViewLog` construction outside
  the output-surface/model owner modules.

Removed paths:

- None.

Parked paths:

- Frontend behavioral-claim copy review remains report-only. The latest review
  mode is still too noisy to hard-fail without a narrower allowlist.
- Deeper generic `db.commit()` ownership enforcement remains parked until R4
  extraction narrows service ownership.

Moved authority:

- No authority moved. This seam only encodes existing ownership boundaries as
  static checks.

Tests and verification:

- Worker allowlist/current marker gate:
  `.\.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift --pretty`
  reported `worker_write_drift_count=0`.
- Static refactor contracts:
  `.\.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors --pretty`
  reported `error_count=0`.
- Related backend fixture checks:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_output_surfaces.py::test_app_code_does_not_bypass_output_surface_emitter tests/test_output_surfaces.py::test_app_code_does_not_create_legacy_reflection_rows_directly tests/test_reminders_scheduler_contract.py tests/test_pause_prediction_job.py tests/test_resume_prediction_job.py tests/test_timer_overflow_notifications.py -q`
  passed `28`.
- S1c shortened verification stack:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology public -SkipBackendFull -SkipFrontendBuild`
  passed authority scan, static refactor contracts, Alembic fresh smoke,
  multi-account browser smoke, and operator read-only browser stress.
- Operator read-only stress artifact:
  `tmp/operator-readonly-stress-2026-07-01T16-33-11-917Z/result.json`.

Behavior parity statement:

- Runtime code, routes, worker behavior, scheduler behavior, notification
  behavior, exposure lifecycle behavior, and user/product state are unchanged.
- The new worker gate only fails when a worker job gains a mutation marker not
  present in its explicit S1c allowlist.
- `/operator` remained implementation-green/cohort-yellow and read-only during
  browser stress.

Rollback note:

- Revert the S1c hard-gate seam commit only. This removes the worker drift flag,
  extra static contract checks, and wrapper wiring; runtime behavior and data
  remain untouched.

## R5a - Stale Docs And Authority Cleanup Before Extraction

Commit: R5a docs-authority seam commit
(`docs: mark stale authority docs subordinate`).

Changed authority:

- `docs/AGENT_HANDOFF.md` is explicitly marked as historical handoff context,
  not current implementation authority.
- `docs/building_phases.md` is explicitly marked as a historical phase map
  during the architecture freeze, not current roadmap authority.
- `docs/jarvis_hypothesis_log.md` is explicitly marked as a historical JARVIS
  research log. It cannot authorize runtime JARVIS work or future synthesis.
- Deadline, academic, and provider design docs now carry an explicit freeze
  boundary forbidding new runtime features, passive tracking, runtime AI
  synthesis, behavior-transition equations, new provider adapters, schema
  migrations, and automatic interventions during the freeze.

Removed paths:

- None.

Parked paths:

- Public-copy/runbook cleanup remains R5b.
- Any future provider connection model, passive telemetry, AI synthesis,
  behavior-transition equation, or schema migration remains parked until a
  separate explicit plan authorizes it.

Moved authority:

- No runtime authority moved.
- Old handoff/phase/JARVIS docs are subordinate to the current authority,
  freeze, OpenClaw, and ClaimCompiler boundary docs.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Stale-authority grep over touched docs confirmed the historical/freeze
  boundary wording appears on the old handoff, phase, JARVIS, deadline,
  academic, and provider docs.
- Operator-cookie browser proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`
  passed with zero count diffs, zero dashboard snapshot diffs, and
  `exposure_without_render_count=0`.
- Operator read-only stress artifact:
  `tmp/operator-readonly-stress-2026-07-01T16-42-24-698Z/result.json`.

Behavior parity statement:

- No runtime files, routes, services, schemas, workers, frontend components, or
  product behavior are changed by this seam.
- This seam only prevents stale documents from being interpreted as permission
  during R3/R4 extraction.
- `/operator` remained implementation-green/cohort-yellow and read-only during
  browser stress.

Rollback note:

- Revert the R5a docs-authority seam commit only. This restores the previous
  wording in the touched docs and ledger without touching product code or data.

## R3 - Deadline Picker Slot Presentational Extraction

Commit: pending R3 deadline-picker-slot seam commit.

Changed authority:

- No task, deadline, parser, nudge, exposure, or mutation authority changed.
- `DeadlinePickerSlot` moved from a nested `NewTaskModal` function into
  `frontend/components/deadline-picker-slot.tsx` as a presentational component.
- `NewTaskModal` still owns deadline choice state, parser suggestion state,
  render acknowledgement, submit/edit/interruption payloads, conflict handling,
  and all mutation decisions.

Removed paths:

- Removed the nested `DeadlinePickerSlot` body from
  `frontend/components/new-task-modal.tsx`.

Parked paths:

- Creation nudge state/effects remain in `NewTaskModal`; they are not moved in
  this seam because they carry exposure authority.
- Deadline preview effects remain in `NewTaskModal`; they are not moved in this
  seam because render acknowledgement and suggestion state are authority
  sensitive.
- Create-payload deduplication remains parked because the full-agent preflight
  found existing create/force/interruption branch asymmetry that needs a
  characterized bug-fix pass, not a pure extraction.
- Stopwatch controller extraction and broad `invalidateDomain()` adoption remain
  parked. Full-agent preflight recommended smaller invalidation-helper seams
  first.

Moved authority:

- None. This is a UI rendering extraction only.

Agent-loop findings:

- New-task explorer recommended extracting only the nested deadline picker first
  and preserving all modal-owned state/effects.
- Timer explorer recommended not extracting the stopwatch controller yet; the
  safer future seam is an exact timer command invalidation helper.
- Brain-dump/pressure explorer recommended exact invalidation recipes rather
  than broad domain invalidation or planner extraction.

Tests and verification:

- Frontend production build:
  `cd frontend && npm run build:public` passed. The build includes Next type
  validity checks; there is no standalone `npm run typecheck` script.
- Whitespace:
  `git diff --check` passed after removing a trailing blank line from the modal.
- Local-current frontend proof used `http://localhost:3013` because WSL/Docker
  owns canonical local port `3000`. The dev server reported
  `compiled_api_origin=http://localhost:8000` and build id `dev-local-current`;
  topology verification marked it mixed only because the manifest does not
  recognize alternate local-current ports.
- Holmesberg product-loop browser proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --run-id r3-deadline-picker-slot-local-current --out-dir tmp\browser-product-loop\r3-deadline-picker-slot-local-current`
  passed the touched deadline-picker branches before a later verifier timeout:
  deadline UI create, task binding, soft conflict create-anyway, creation nudge
  keep, no-deadline branch, custom category persistence, pick-another explicit
  deadline binding, and terminal-deadline picker filtering setup.
- Verifier issue:
  GitHub #146 tracks the product-loop edit-visibility timeout after backend
  explicit binding had already passed.
- Topology verifier issue:
  GitHub #147 tracks alternate local-current frontend ports being reported as
  mixed topology.
- Cleanup proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --cleanup-only --prefix "DOGFOOD 17f3964b" --run-id r3-deadline-picker-slot-cleanup --out-dir tmp\browser-product-loop\r3-deadline-picker-slot-cleanup`
  passed. A follow-up residue probe found no matching synthetic tasks and only
  voided DOGFOOD/Zephyr/Orion synthetic deadlines.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-deadline-picker-slot-operator-local-current`
  passed with zero count diffs, zero dashboard snapshot diffs, and
  `exposure_without_render_count=0`.
- Operator read-only stress artifact:
  `tmp/operator-readonly-stress-r3-deadline-picker-slot-operator-local-current/result.json`.

Behavior parity statement:

- The extracted component calls the same callbacks with the same values and
  still fetches bindable deadlines only when the picker is open.
- Bindable deadline filtering remains `planned` or `active` state on top of the
  backend list endpoint's non-voided default.
- Deadline suggestion confirmation, pick-another, no-deadline, clear binding,
  manual picker, and empty/loading states render the same data-testid hooks.
- `/operator` remained implementation-green/cohort-yellow and read-only during
  browser stress.

Rollback note:

- Revert the R3 deadline-picker-slot seam commit only. This restores the nested
  component in `NewTaskModal` and removes
  `frontend/components/deadline-picker-slot.tsx` without touching backend code,
  production data, exposure rows, or task/deadline mutation authority.

## R3 - Query Invalidation Helpers And Dogfood Cleanup Proof

Commit: pending R3 invalidation-helper seam commit.

Changed authority:

- No task, deadline, timer, pressure-map, brain-dump, exposure, or claim
  authority changed.
- `frontend/lib/query-keys.ts` now owns exact invalidation recipes for:
  - timer command surfaces;
  - brain-dump commits;
  - pressure-map recovery commits.
- The Holmesberg product-loop verifier now owns cleanup proof for newly-created
  synthetic creation-nudge decisions that never reached render.

Removed paths:

- Removed duplicate timer invalidation lists from:
  - `frontend/components/active-timer-banner.tsx`;
  - `frontend/components/pulse/PulseFocusCard.tsx`.
- Removed duplicate brain-dump commit invalidation from
  `frontend/components/pulse/BrainDumpQuickModal.tsx`.
- Removed duplicate pressure recovery commit invalidation from
  `frontend/components/pulse/PulseAcademicPressureMap.tsx`.

Parked paths:

- Raw invalidation remains in `PulseReentryQueue`, `undo-toast-host`, Today,
  Calendar, Deadlines, Settings, and Integrations. Those are future small seams,
  not part of this pass.
- `invalidateDomain()` remains narrow for admin/operator only. Broad domain
  invalidation is still parked.
- Calendar drag/resize, provider credential mutation, hard-delete/Redis purge,
  and OpenClaw pending-drain browser mutations remain gated in the product-loop
  verifier until disposable credentials/accounts or authority decisions exist.

Moved authority:

- Cache invalidation recipe ownership moved from individual component command
  handlers into named query-key helpers.
- Synthetic dogfood exposure cleanup moved into the reusable verifier so a
  passed Holmesberg product loop proves its own cleanup instead of relying on a
  later E0 forensic pass.
- No runtime product authority moved.

Agent-loop findings:

- The frontend seam initially preserved prior invalidation lists, but the agent
  loop found the prior lists were under-scoped for warm Pulse/Calendar caches.
- `invalidateBrainDumpCommitCaches()` now also invalidates
  `tasksEvidence`.
- `invalidatePressureRecoveryCommitCaches()` now also invalidates
  `tasksRange` and `tasksEvidence`.
- The product-loop edit-mode timeout is classified as a verifier/harness issue:
  explicit backend deadline binding had passed, but the branch task was not
  visible in the current Today view. The runner now gates only that edit-mode
  sub-branch instead of timing out the whole flow.

Tests and verification:

- Harness syntax:
  `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs` passed.
- Frontend production build:
  `cd frontend && npm run build:public` passed. The build includes Next type
  validity checks; there is no standalone `npm run typecheck` script.
- Whitespace:
  `git diff --check` passed with only CRLF conversion warnings.
- Verifier classification:
  the first rerun failed before product state because local-current
  `/api/auth/session` returned 500 after a production build. This is tracked by
  GitHub #144 as verifier dev-server corruption, not a product failure. The
  local-current dev server was restarted before rerun.
- Holmesberg product-loop browser proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-invalidation-helpers-rerun-local-current --out-dir tmp\browser-product-loop\r3-invalidation-helpers-rerun-local-current`
  passed.
- Product-loop artifact:
  `tmp/browser-product-loop/r3-invalidation-helpers-rerun-local-current/result.json`.
- Covered product surfaces:
  route sweep, deadline create, task create, deadline binding, soft conflict
  create-anyway, duration nudge keep, no-deadline branch, custom category,
  pick-another explicit deadline binding, terminal deadline rejection/filtering,
  brain-dump parse/commit/partial retry/double-submit, pressure-map preview and
  recovery block commit, calendar visibility, timer start/pause/resume/stop,
  pause export, exposure decision/render/ack export, notification
  render/dismiss/action/expiry lifecycle, Insights forbidden-claim scan, Table
  delta/audit rendering, operator privacy scan, and cleanup proof.
- Product-loop cleanup proof:
  `cleanup leaves no unrendered synthetic creation-nudge exposures` passed. The
  runner suppressed one newly-created dogfood-only pre-render creation-nudge
  decision and left zero remaining candidates.
- E0 repair audit for the pre-rerun dogfood row:
  `docs/audits/e0_exposure_forensics_2026_07_01.md`.
- Redacted repair artifacts:
  `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper/redacted_before_snapshot.json`,
  `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper/repair_result_redacted.json`,
  and
  `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper/redacted_after_snapshot.json`.
- Operator read-only proof after repair:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-invalidation-helpers-rerun-operator-local-current`
  passed.
- Operator read-only artifact:
  `tmp/operator-readonly-stress-r3-invalidation-helpers-rerun-operator-local-current/result.json`.
- Operator outcome:
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, `cohort_status=yellow`, zero count diffs,
  zero route count diffs, and zero dashboard snapshot diffs.

Behavior parity statement:

- Timer command handlers still invalidate the same surfaces as before, now
  through `invalidateTimerCommandSurfaces()`.
- Brain-dump and pressure-map commit handlers invalidate a superset of the old
  warm caches so newly-created tasks, evidence rows, deadlines, and pressure
  state appear without hard refresh.
- Existing fire-and-forget invalidation behavior is preserved where prior code
  did not await invalidations. Pressure-map commit still awaits invalidation
  before resolving the commit flow.
- The product-loop verifier no longer treats a non-visible Today edit branch as
  product failure when backend binding already passed; it records a gated
  verifier branch and continues the rest of the documented flow.

Rollback note:

- Revert the R3 invalidation-helper seam commit to restore inline invalidation
  calls in touched frontend components.
- Revert the product-loop cleanup/harness commit to restore the previous
  verifier behavior.
- The production data repair is not reverted through Git. If the redacted E0
  classification were later proven wrong, use the private ignored full-ID
  snapshot from `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper`
  and perform an explicit operator-approved data repair. No render evidence was
  fabricated, and no operator invariant was weakened.

## R3 - Brain Dump Commit Builder Extraction

Commit: pending R3 brain-dump commit-builder seam commit.

Changed authority:

- No brain-dump parse, commit, onboarding, Pulse, task, deadline, exposure, or
  mutation authority changed.
- `frontend/lib/brain-dump-ui.ts` now owns pure helpers for converting parsed
  brain-dump items and selected bindings into commit API payloads.
- Onboarding and Pulse continue to own their own state machines, user-visible
  copy, commit timing, failure handling, idempotency keys, cache invalidation,
  and close/step behavior.

Removed paths:

- Removed duplicated commit-item mapping from:
  - `frontend/components/onboarding-flow.tsx`;
  - `frontend/components/pulse/BrainDumpQuickModal.tsx`.
- Removed duplicated selected-binding mapping from the same two surfaces.

Parked paths:

- A full shared brain-dump reducer remains parked. This seam deliberately does
  not merge onboarding and Pulse state machines.
- Surface-specific copy remains local. For example, Pulse still labels parsed
  deadline bindings as "same dump" while onboarding uses "deadline".
- Retry-copy wording, modal/onboarding step transitions, and failure rendering
  remain local until a larger characterized extraction is justified.

Moved authority:

- Pure payload-shape construction moved into `brain-dump-ui`.
- No runtime authority moved.

Agent-loop findings:

- The planned external explorers disconnected during the network interruption,
  so this pass used a bounded local mini-loop instead of waiting on unavailable
  agents.
- The local loop found an exact duplicated pure transformation shared by
  onboarding and Pulse, while avoiding copy/state/effect unification that would
  change product behavior.

Tests and verification:

- Frontend production build:
  `cd frontend && npm run build:public` passed. The build includes Next type
  validity checks; there is no standalone `npm run typecheck` script.
- Whitespace:
  `git diff --check` passed with only CRLF conversion warnings.
- Local-current frontend proof used `http://localhost:3013` with
  `compiled_api_origin=http://localhost:8000` and build id
  `dev-local-current`; topology remains mixed only because alternate
  local-current ports are tracked separately in GitHub #147.
- Holmesberg product-loop browser proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-brain-dump-commit-builders-local-current --out-dir tmp\browser-product-loop\r3-brain-dump-commit-builders-local-current`
  passed.
- Product-loop artifact:
  `tmp/browser-product-loop/r3-brain-dump-commit-builders-local-current/result.json`.
- Touched path coverage:
  brain-dump parse was write-free; commit created task/deadline rows; partial
  commit saved only the valid item; retry reopened only the failed item; edited
  retry created the recovered item exactly once; double-submit created exactly
  one task; export included committed task/deadline/session/pause/exposure and
  notification rows; cleanup left no active timer and no unrendered synthetic
  creation-nudge exposures.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-brain-dump-commit-builders-operator-local-current`
  passed.
- Operator read-only artifact:
  `tmp/operator-readonly-stress-r3-brain-dump-commit-builders-operator-local-current/result.json`.
- Operator outcome:
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, `cohort_status=yellow`, zero count diffs,
  zero route count diffs, and zero dashboard snapshot diffs.

Behavior parity statement:

- Both surfaces send the same `BrainDumpCommitItem` fields and
  `BrainDumpCommitBinding` fields as before.
- Pulse still supplies its existing commit idempotency key and still invalidates
  dashboard caches after commit.
- Onboarding still calls the same commit endpoint without a commit key and
  exits only after a clean commit.
- Failure handling and review-failure behavior are unchanged.

Rollback note:

- Revert the R3 brain-dump commit-builder seam commit only. This restores local
  payload mapping in onboarding and Pulse without touching backend code,
  schemas, production data, or browser-verifier cleanup logic.
