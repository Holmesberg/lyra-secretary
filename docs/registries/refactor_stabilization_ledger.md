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
- Targeted Playwright scripts still remain for NewTaskModal edit/conflict
  branches, brain-dump retry/partial failure, pressure-map commit, long-lived
  timer pause/navigation, notification action/expiry, forced insights states,
  calendar mutation, and table correction/export.

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

- `NewTaskModal` edit mode, terminal deadline rejection, custom category,
  no-bind/pick-another, and nudge-dismiss outcome remain targeted browser
  coverage.
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
