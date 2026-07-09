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

Commit: `46b63de docs: mark stale authority docs subordinate`
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

Commit: `d95e796 frontend: extract deadline picker slot`.

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

Commit: `68dc180 frontend: centralize mutation cache invalidation`.

Follow-up commit: `0a3bf46 docs: record r3 exposure cleanup proof`.

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

Commit: `6cbab9b frontend: share brain dump commit builders`.

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

## R3 - Pressure Map Planning Helper Extraction

Commit: `fd0ca15 frontend: extract pressure map planning helpers`.

Changed authority:

- No pressure-map recovery, task creation, deadline binding, exposure,
  ClaimCompiler, Cortex, or operator authority changed.
- `frontend/lib/pressure-map-planning.ts` now owns pressure-map planning
  helpers: plan-row shape, local-time math, estimate formatting, linked
  deadline evidence estimates, cold-start calibration text, option item
  selection, and plan-row construction.
- `PulseAcademicPressureMap` continues to own UI state, preview dialog
  lifecycle, enrichment API calls, task creation, force-conflict handling,
  cache invalidation, and user-visible commit behavior.

Removed paths:

- Removed the inline pressure-map planning/evidence helper block from
  `frontend/components/pulse/PulseAcademicPressureMap.tsx`.
- No runtime route, backend path, data model, or mutation path was removed.

Parked paths:

- Real backend pressure-map recovery options remain gated while pressure safe
  mode is active; the browser verifier still uses a recovery fixture only to
  cover the preview/commit seam.
- Deeper pressure-map reducer/state-machine extraction remains parked until a
  later frontend seam.
- Calendar drag/resize, provider credential browser mutation, account
  hard-delete/Redis purge, and OpenClaw pending drain remain gated verifier
  paths.

Moved authority:

- Pure planning/evidence computation moved into `pressure-map-planning`.
- No runtime authority moved. The component still decides when a preview opens
  and when confirmed rows become tasks.

Agent-loop findings:

- A mini explorer loop confirmed that `PlanRow`, estimate helpers, local-time
  helpers, calibration copy, option filtering, and `buildRows` are safe to move
  into a library.
- The same loop flagged that `buildRows` reads current time, so it is
  deterministic relative to "now" rather than mathematically pure. It remains
  safe for this seam because it has no app mutation, I/O, hook, cache, or API
  side effects.
- The loop confirmed `PlanPreviewDialog`, `enrichColdStartRows`,
  `openPlanPreview`, `commitPlan`, and hook/memo state must remain in the
  component because they own UI state, async calls, mutation, or JSX event
  wiring.

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
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-pressure-map-planning-helpers-local-current --out-dir tmp\browser-product-loop\r3-pressure-map-planning-helpers-local-current`
  passed.
- Product-loop artifact:
  `tmp/browser-product-loop/r3-pressure-map-planning-helpers-local-current/result.json`.
- Verification classification:
  the shell command timed out at 300 seconds while the underlying Node verifier
  was still running. The process was allowed to finish and produced a passing
  result. This was classified as local orchestration timeout budget, not a
  product bug, verifier logic bug, authority bug, topology bug, documentation
  bug, or measurement bug.
- Touched path coverage:
  pressure-map seeded deadline appeared in the map; preview was available;
  dismiss did not create tasks; editable plan row rendered; double-lock created
  exactly one recovery block; the committed block kept the explicit deadline
  binding and planning-footprint provenance; calendar showed the committed
  block before cleanup; export contained the relevant task/deadline/session,
  pause, exposure, and notification evidence; cleanup left no active timer and
  no unrendered synthetic creation-nudge exposures.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-pressure-map-planning-helpers-operator-local-current`
  passed.
- Operator read-only artifact:
  `tmp/operator-readonly-stress-r3-pressure-map-planning-helpers-operator-local-current/result.json`.
- Operator outcome:
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, `cohort_status=yellow`, zero count diffs,
  zero route count diffs, and zero dashboard snapshot diffs.

Behavior parity statement:

- Plan-row construction preserves the same default start spacing, option
  filtering, estimate basis, linked-deadline evidence, cold-start source text,
  category fallback, conflict state defaults, and deadline binding fields.
- Preview editing still computes duration and end-time exactly as before.
- Cold-start enrichment still calls the same bias lookup endpoint and rewrites
  only pending rows.
- Commit behavior still sends the same `createTask` payloads and invalidates
  the same pressure-recovery caches after commit.

Rollback note:

- Revert the R3 pressure-map planning-helper seam commit only. This restores
  the inline helper block in `PulseAcademicPressureMap` and removes
  `frontend/lib/pressure-map-planning.ts` without touching backend code,
  schemas, production data, or browser-verifier cleanup logic.

## R3 - Stopwatch Elapsed Fallback Helper Extraction

Commit: `f4a8d9a frontend: share stopwatch elapsed fallback`.

Changed authority:

- No stopwatch command, timer lifecycle, pause/resume/switch mutation,
  optimistic rollback, exposure, notification, Cortex, ClaimCompiler, or
  operator authority changed.
- `frontend/lib/stopwatch-time.ts` now owns the second-precision elapsed
  fallback: prefer `elapsed_seconds`, otherwise use `elapsed_minutes * 60`.
- `ActiveTimerBanner`, `PausedOthersChips`, and `RadialFocusTimer` continue to
  own their local timer anchoring, ticking, pause freezing, resume rebasing,
  optimistic cache updates, and user interactions.

Removed paths:

- Removed repeated inline `elapsed_seconds ?? elapsed_minutes * 60` fallback
  expressions from timer display surfaces.
- No runtime route, backend path, data model, or mutation path was removed.

Parked paths:

- Stopwatch controller extraction remains parked. The current seam deliberately
  avoids moving hooks, refs, effects, mutation handlers, or React Query
  optimistic update logic.
- Pause reason options, switch chips, Pulse reflection flow, and early-stop
  confirmation remain local until a larger characterized seam is justified.

Moved authority:

- Only pure display-boundary fallback math moved into `stopwatch-time`.
- No runtime authority moved.

Agent-loop findings:

- A mini explorer loop recommended extracting only a tiny elapsed-seconds
  helper as the smallest safe stopwatch seam.
- It explicitly rejected moving `anchor`, `frozenSec`, `lastDisplayedRef`,
  `prevPausedRef`, `pauseStartRef`, `localPaused`, 1Hz tick effects,
  task-change reset effects, server catch-up, pause/resume/switch optimistic
  updates, and Pulse focus-card state in this pass.
- It identified browser parity requirements around running ticks, pause freeze,
  cumulative paused time, resume continuation, switch elapsed anchoring, and
  cross-surface elapsed agreement.

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
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-stopwatch-elapsed-helper-local-current --out-dir tmp\browser-product-loop\r3-stopwatch-elapsed-helper-local-current`
  passed.
- Product-loop artifact:
  `tmp/browser-product-loop/r3-stopwatch-elapsed-helper-local-current/result.json`.
- Touched path coverage:
  timer start opened an active session with second-precision elapsed; pause was
  reflected in status; resume/stop/reflection completed; export contained the
  dogfood stopwatch session and pause event; notification lifecycle evidence
  was terminal; cleanup left no active timer and no unrendered synthetic
  creation-nudge exposures.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-stopwatch-elapsed-helper-operator-local-current`
  passed.
- Operator read-only artifact:
  `tmp/operator-readonly-stress-r3-stopwatch-elapsed-helper-operator-local-current/result.json`.
- Operator outcome:
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, `cohort_status=yellow`, zero count diffs,
  zero route count diffs, and zero dashboard snapshot diffs.

Behavior parity statement:

- Banner and radial timer still prefer second-precision elapsed values.
- Banner and optimistic switch chips still fall back to minute precision when
  second precision is absent.
- No pause/resume/switch command payload, optimistic cache mutation, rollback
  behavior, reason-picker behavior, reflection flow, or task-state mapping
  changed.

Rollback note:

- Revert the R3 stopwatch elapsed-helper seam commit only. This restores the
  inline fallback expressions and removes `frontend/lib/stopwatch-time.ts`
  without touching backend code, schemas, production data, or browser-verifier
  cleanup logic.

## R3 - Calibration Nudge Card Presentational Extraction

Commit: `e2e0e6e frontend: extract calibration nudge card`.

Changed authority:

- No task creation, edit, interruption, conflict override, deadline binding,
  creation-nudge exposure, calibration lookup, suppression, Cortex,
  ClaimCompiler, or operator authority changed.
- `frontend/components/calibration-nudge-card.tsx` now owns only the
  presentational calibration-nudge card copy, display rows, and button markup.
- `NewTaskModal` continues to own lookup timing, local research fallback,
  backend hydration, exposure render/suppression acknowledgement, nudge
  decision state, duration/end mutations, submit payloads, conflict branching,
  deadline preview/picker state, and modal reset/edit synchronization.

Removed paths:

- Removed the inline calibration-nudge JSX block from
  `frontend/components/new-task-modal.tsx`.
- No runtime route, backend path, data model, exposure path, or mutation path
  was removed.

Parked paths:

- NewTaskModal draft-state, creation-nudge effect, deadline-preview effect,
  submit/edit/interruption flow, and conflict reducer extraction remain parked.
- Payload-helper extraction remains parked; this seam deliberately avoids
  moving submit payload shape or exposure accounting.

Moved authority:

- Presentational nudge-card rendering moved into `CalibrationNudgeCard`.
- No runtime authority moved.

Agent-loop findings:

- A mini explorer loop recommended the nudge card as the smallest safe
  NewTaskModal extraction.
- The loop explicitly kept form state, reset/edit sync, schedule handlers,
  AM/PM and past-start suggestions, nudge state, bias lookup, exposure
  render/suppression effects, deadline preview/picker state, create/reschedule
  mutations, and conflict state in `NewTaskModal`.

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
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-calibration-nudge-card-local-current --out-dir tmp\browser-product-loop\r3-calibration-nudge-card-local-current`
  passed.
- Product-loop artifact:
  `tmp/browser-product-loop/r3-calibration-nudge-card-local-current/result.json`.
- Touched path coverage:
  new-task nudge keep branch preserved the original duration; deadline
  suggestion/picker/no-deadline branches still passed; custom category persisted;
  terminal deadline binding remained rejected/hidden; soft conflict override
  branch still worked; export contained task/deadline/session/pause/exposure and
  notification evidence; cleanup left no active timer and no unrendered
  synthetic creation-nudge exposures.
- Non-blocking finding:
  the product loop observed one deadline suggestion render at `3916ms` against
  a `3000ms` senior UX budget. This was classified as a pre-existing
  user-facing latency issue, not caused by the presentational nudge-card seam.
  GitHub issue #149 tracks it.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-calibration-nudge-card-operator-local-current`
  passed.
- Operator read-only artifact:
  `tmp/operator-readonly-stress-r3-calibration-nudge-card-operator-local-current/result.json`.
- Operator outcome:
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, `cohort_status=yellow`, zero count diffs,
  zero route count diffs, and zero dashboard snapshot diffs.

Behavior parity statement:

- The card renders the same research/personal/blended copy, estimate rows,
  disabled states, test ids, and "Use"/"Keep" labels as before.
- The parent still performs the same exposure acknowledgement and nudge-decision
  writes before changing duration/end or dismissing the card.
- No submit payload, conflict branch, deadline binding, duration update,
  modal reset, or cache invalidation behavior changed.

Rollback note:

- Revert the R3 calibration-nudge-card seam commit only. This restores the
  inline nudge JSX in `NewTaskModal` and removes
  `frontend/components/calibration-nudge-card.tsx` without touching backend
  code, schemas, production data, or browser-verifier cleanup logic.

## R4 - Operator Dashboard Metric Helper Extraction

Commit: `502218d backend: extract operator dashboard metric helpers`.

Changed authority:

- No operator authorization, cohort-readiness rule, exposure invariant,
  notification lifecycle rule, clean-trace denominator, provider-integrity rule,
  Redis state, task/session/deadline state, or dashboard response contract
  changed.
- `backend/app/services/operator_dashboard_metrics.py` now owns read-only
  helper primitives used by `/v1/operator/dashboard`: metric metadata, hashes,
  test/synthetic user classification, percentage math, dynamic-issue shaping,
  watchlist status derivation, dropoff detection, activity-date maps, Redis
  pending-notification snapshotting, and last-activity aggregation.
- `backend/app/api/v1/endpoints/operator.py` remains the operator-authenticated
  dashboard endpoint and still owns the assembled cockpit payload, readiness
  semantics, and request-scope reset/restore boundary.

Removed paths:

- Removed the inline helper implementations from `operator.py`.
- No route, endpoint, table, schema, production data, output surface, exposure
  lifecycle path, or mutation path was removed.

Parked paths:

- Full operator payload-builder extraction remains parked until the helper seam
  has aged through more verification.
- Analytics route-thin service extraction remains parked; analytics still owns
  several hotter exposure/render/suppression paths and should be split only
  after smaller diagnostic seams.
- Output-surface terminal-state classifier extraction remains parked as the
  next likely exposure-diagnostics seam.
- Stopwatch active-store extraction remains parked as a later backend seam.

Moved authority:

- Read-only helper computation moved into an operator dashboard service module.
- No runtime authority moved. The endpoint continues to enforce operator access,
  clear/restore request user scope, and return the dashboard payload.

Agent-loop findings:

- The R4 operator/analytics explorer recommended starting with operator
  dashboard helper or payload extraction rather than analytics insights because
  `/operator` is read-only and strongly characterized, while analytics still
  mixes clean-profile filtering, public translation, Redis seen-state, and
  exposure render/suppression writes.
- The R4 output-surface explorer recommended a future pure exposure
  terminal-state classifier, not a delivery-path refactor.
- The R4 stopwatch/task explorer recommended a future active stopwatch-store
  seam around active-state recovery/cleanup, not `stop()` or finalization.

Tests and verification:

- Python compile:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator and admin route tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py -q`
  passed (`16 passed`).
- Exposure and output-surface contract tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_exposure_ledger_v0.py tests\test_output_surfaces.py -q`
  passed (`42 passed`).
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id s1c-openclaw-relay-gate-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-s1c-openclaw-relay-gate-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `7125ms`, mobile `6684ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and
  `cohort_status=yellow` for real-data gaps only.
- Static authority scan:
  `.\.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py`
  passed in report-only mode with `missing_owner_count=0`.
- Static refactor contract scan:
  `.\.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py`
  passed with zero findings.
- Local-current frontend proof used `http://localhost:3013` with
  `compiled_api_origin=http://localhost:8000` and build id
  `dev-local-current`.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-operator-metrics-helper-operator-local-current`
  passed.
- Operator read-only artifact:
  `tmp/operator-readonly-stress-r4-operator-metrics-helper-operator-local-current/result.json`.
- Operator outcome:
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, `cohort_status=yellow`, zero count diffs,
  zero route count diffs, and zero dashboard snapshot diffs.
- Non-blocking finding:
  the desktop `/operator` route took `14246ms` against the `12000ms` verifier
  latency budget. GitHub issue #150 tracks this as a verifier-discovered
  performance warning; it is not a semantic/read-only blocker for this seam.

Behavior parity statement:

- `/v1/operator/dashboard` still returns the same cockpit sections, readiness
  split, dynamic issues, notification lifecycle counts, clean-trace ratio
  basis, provider-integrity counts, and privacy-minimized user rows.
- Existing operator tests still monkeypatch `operator_endpoint.RedisClient`;
  the endpoint keeps a compatibility wrapper so Redis snapshot behavior remains
  characterized by the same tests.
- The helper module performs read-only queries and Redis reads only; it does
  not call `db.commit`, `db.flush`, output-surface emitters, exposure writers,
  notification lifecycle writers, or Redis write/delete methods.

Rollback note:

- Revert `502218d` only. This restores the inline helper implementations in
  `operator.py` and removes `operator_dashboard_metrics.py` without touching
  schemas, production data, frontend code, exposure rows, Redis data, or
  browser-verifier cleanup logic.

## R4 - Exposure Terminal Classification Diagnostic Primitive

Commit: `bfdba26 backend: centralize exposure terminal classification`.

Changed authority:

- No exposure write, render acknowledgement, suppression acknowledgement,
  notification lifecycle transition, operator-readiness rule, schema, migration,
  user-facing output surface, or production data changed.
- `backend/app/services/exposure_ledger.py` now owns a pure
  `classify_exposure_terminal_state(...)` diagnostic primitive that classifies
  an existing decision from three inputs only: decision status, render-row
  presence, and suppression-row presence.
- `/v1/operator/dashboard` now uses the classifier to count actionable
  missing-render exposure rows while preserving its existing non-blocking
  treatment of queued and suppressed decisions.
- `output_surface_diagnostics(...)` now uses the same classifier to count
  missing terminal events while preserving the stricter dual-write meaning:
  an actual render row or suppression row is terminal evidence.

Removed paths:

- Removed duplicate local exposure-terminal classification branches from the
  operator dashboard and output-surface diagnostics.
- No route, table, model, endpoint response field, lifecycle event, or cleanup
  path was removed.

Parked paths:

- Output-surface delivery/worker extraction remains parked. Notification queue,
  notification lifecycle transitions, render/suppression emitters, and
  OpenClaw mirroring were deliberately not changed.
- Analytics route-thin extraction remains parked.
- Exposure repair tooling remains parked unless a future production-data repair
  decision is explicitly authorized.

Moved authority:

- Diagnostic classification moved into the Exposure Ledger service as a
  reusable measurement primitive.
- No mutation authority moved. `ExposureLedger` still owns ledger writes through
  its existing append-only record helpers; `OutputSurface` still owns registered
  surface decisions/renders/suppressions; `/operator` remains read-only.

Agent-loop findings:

- The R4 output-surface explorer recommended this exact pure classifier seam as
  the safest way to unify diagnostic meaning without touching delivery or
  schema.
- During implementation, a subtle distinction was preserved: a decision with
  `decision_status="suppressed"` but no suppression row is non-actionable for
  operator rollout, but it is still missing terminal evidence for output-surface
  dual-write diagnostics.

Tests and verification:

- Focused diagnostic tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_exposure_ledger_v0.py::test_exposure_terminal_classifier_preserves_diagnostic_boundaries tests\test_output_surfaces.py::test_output_surface_diagnostics_reports_missing_terminal_event tests\test_operator_dashboard.py::test_operator_dashboard_does_not_block_on_suppressed_exposures tests\test_operator_dashboard.py::test_operator_dashboard_does_not_block_on_queued_notification_decisions -q`
  passed (`4 passed`).
- Broader contract tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_exposure_ledger_v0.py tests\test_output_surfaces.py -q`
  passed (`53 passed`).
- Python compile:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\exposure_ledger.py app\services\output_surfaces.py app\api\v1\endpoints\operator.py`
  passed.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Static authority scan:
  `.\.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py`
  passed in report-only mode with `missing_owner_count=0`.
- Static refactor contract scan:
  `.\.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py`
  passed with zero findings.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-exposure-terminal-classifier-v2-operator-local-current`
  passed.
- Operator read-only artifact:
  `tmp/operator-readonly-stress-r4-exposure-terminal-classifier-v2-operator-local-current/result.json`.
- Operator outcome:
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, `cohort_status=yellow`, zero count diffs,
  zero route count diffs, zero dashboard snapshot diffs, and no verifier
  warnings.
- Issue tracking:
  the earlier intermittent desktop `/operator` latency warning remains tracked
  in GitHub #150. This corrected-code run completed under the 12s desktop
  budget (`11682ms`).

Behavior parity statement:

- Operator readiness still blocks only on actionable exposure decisions missing
  render or suppression evidence.
- Queued notification decisions remain counted separately and do not block
  rollout.
- Suppressed decisions remain non-actionable for operator readiness, but
  output-surface dual-write diagnostics still require a real suppression row to
  count as terminal evidence.
- No user-facing claim, synthesis, intervention, or AI runtime path was added.

Rollback note:

- Revert `bfdba26` only. This restores the local classification branches in
  `operator.py` and `output_surfaces.py` and removes
  `classify_exposure_terminal_state(...)` plus its test, without touching
  schemas, production data, frontend code, Redis data, or lifecycle rows.

## R4 - Active Stopwatch Store Extraction

Code commit: `15068c1`

Changed authority:

- No endpoint payload, schema, frontend behavior, or task lifecycle behavior
  changed.
- `backend/app/services/active_stopwatch_store.py` now owns active stopwatch
  Redis/DB recovery and orphan cleanup implementation.
- `StopwatchManager` remains the public stopwatch service surface and keeps
  compatibility methods for `_get_active`, `_recover_from_db`,
  `_close_orphan_session`, `_close_open_pause_events`, and `void_cleanup`.
- The mutation surface registry now lists `active_stopwatch_store.py` under
  `stopwatch_session_authority`.

Removed paths:

- Inline active-state recovery and orphan-cleanup bodies were removed from
  `stopwatch_manager.py`.
- No route, schema, frontend component, production data, or user-visible path
  was removed.

Parked paths:

- Stopwatch `stop()`/finalizer extraction remains parked because it mixes final
  pause accounting, `TaskManager.complete_task`, calibration nudges,
  micro-mirror behavior, Redis clearing, and paused-parent payload semantics.
- Task lifecycle/binding/integration effects remain parked.
- Notification/output-surface effects remain parked.

Moved authority:

- Active stopwatch recovery/cleanup implementation moved into a narrower store.
- Stopwatch truth authority did not move; `StopwatchManager`, canonical
  stopwatch endpoints, and Redis stopwatch state methods remain the owning
  surface.

Agent-loop findings:

- The R4 backend extraction pass chose the active-store seam because it reduces
  `stopwatch_manager.py` size while leaving start/pause/resume/stop semantics
  untouched.
- The seam was intentionally kept below the finalizer boundary to avoid
  changing execution duration, pause aggregation, completion, reflection, or
  calibration behavior.

Tests and verification:

- Focused recovery/void/orphan tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_void_clears_stopwatch.py tests\test_stopwatch_recovery.py tests\test_recovery_and_negative_pause.py tests\test_pause_resume_pause_event.py::test_close_orphan_session_closes_open_pause_events tests\test_state_consistency.py::test_recover_from_db_blocks_terminal_states tests\test_mutations_reject_voided.py::test_stopwatch_stop_voided_mid_session tests\test_mutations_reject_voided.py::test_update_completion_rejects_voided -q`
  passed (`13 passed`).
- Broader stopwatch suite:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_stopwatch_switch.py tests\test_stopwatch_start_errors.py tests\test_stopwatch_pause_counter_anchor.py tests\test_stale_pause_resolution.py tests\test_mutations_reject_voided.py -q`
  passed (`33 passed`).
- Python compile:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\active_stopwatch_store.py app\services\stopwatch_manager.py`
  passed.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Static authority scan:
  `.\.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py`
  passed in report-only mode with `missing_owner_count=0`.
- Static refactor contract scan:
  `.\.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py`
  passed with zero findings.
- Holmesberg mutable product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r4-active-stopwatch-store-local-current --out-dir tmp\browser-product-loop\r4-active-stopwatch-store-local-current`
  passed.
- Holmesberg artifact:
  `tmp/browser-product-loop/r4-active-stopwatch-store-local-current/result.json`.
- Holmesberg outcome:
  task/deadline binding, brain dump, pressure-map commit seam, timer
  start/pause/resume/stop, export evidence, exposure render/ack rows,
  notification lifecycle terminal rows, and cleanup all passed. The exported
  dogfood pause event showed nonzero `duration_minutes`.
- Operator read-only proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-active-stopwatch-store-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-active-stopwatch-store-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, and `cohort_status=yellow` for real-data
  gaps only.

Behavior parity statement:

- `_get_active`, `_recover_from_db`, `_close_orphan_session`,
  `_close_open_pause_events`, and `void_cleanup` remain callable on
  `StopwatchManager` and delegate to the store.
- `close_orphan_session` still commits and invalidates task ranges.
- `close_open_pause_events` still does not commit; callers own the transaction.
- `void_cleanup` still uses the current request user key and clears Redis only
  when the active stopwatch points at the voided task.
- Start, pause, resume, switch, stop, completion, reflection, and export
  behavior are unchanged.

Rollback note:

- Revert `15068c1` only. This restores the inline active-state recovery and
  orphan-cleanup bodies in `stopwatch_manager.py`, removes
  `active_stopwatch_store.py`, and removes its registry entry without touching
  schemas, production data, frontend code, Redis data, or lifecycle rows.

## R5a - Stale Authority Docs And OpenClaw Compatibility Guard

Changed authority:

- `docs/current_transition_state.md` now reflects the active
  `wave-5-sovereignty-integrity-cycle` freeze-closure frame instead of the old
  evidence-packet branch.
- `docs/building_phases.md` no longer claims to be the forward-looking source
  of truth during the architecture freeze.
- `docs/testing_patterns.md` now distinguishes production fail-closed identity
  from the test harness default identity.
- `docs/import_integrations_capability_map.md` now marks provider mappings as
  historical capability hypotheses, not provider truth or adapter authority.
- `docs/deadline_mechanism_design.md` now marks old `APPROVED`,
  `parser_auto`, soft-warning RCT, and per-deadline `bias_factor` wording as
  historical/parked unless promoted by current authority.
- `openclaw/skills/lyra-secretary/SKILL.md` now states that the old direct
  backend-control skill is compatibility/reference material only.
- `openclaw/config/agent.yml` now parks legacy direct-backend mutation tools as
  `tools: []`.
- `docs/audits/doc_alignment_findings_2026_06_04.csv` marks F003, F004, and
  F006 resolved by this pass.

Removed paths:

- No Lyra app route, schema, frontend component, backend service, production
  data, Redis key, or user-facing product path was removed.
- Legacy OpenClaw direct-backend tool definitions were removed from the local
  compatibility config because direct Docker reachability is not authorization.

Parked paths:

- OpenClaw direct task/timer mutation remains parked until a current
  authenticated/audited canonical command path is explicitly authorized.
- Old April roadmap phase planning remains historical context.
- Deadline soft-warning RCT and per-deadline calibration claims remain parked.
- Provider adapter expansion and passive telemetry remain parked.
- Broader doc-alignment findings not touched by this pass remain open in the
  audit CSV.

Moved authority:

- Current transition authority moved from the old evidence-packet branch frame
  to the freeze-closure sequence: E0, R2, S1c hardening, R5a, R3/R4 seams,
  R5b, R6, then post-freeze planning.
- `AGENT_HANDOFF.md` is treated as historical onboarding context, not a
  governing implementation document.
- OpenClaw is reaffirmed as an operator reasoning environment/future draft host,
  not a mutation owner.

Agent-loop findings:

- Explorer B found that runtime behavior was healthier than stale docs: Jarvis
  endpoints are parked, exposure fails closed, and provider/deadline code mostly
  respects canonical ownership, but old docs/config could still mislead future
  agents.
- The highest-risk stale path was OpenClaw's old direct backend command shell,
  because local skill/config files can become live operator behavior.

Tests and verification:

- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- YAML parse:
  `openclaw/config/agent.yml` parsed successfully with PyYAML.
- Forbidden-claim grep:
  high-signal active-authority terms were reduced to intentional historical
  audit records and the explicit `tools: []` parking marker.
- Runtime behavior:
  no Lyra app code changed.
- Operator-cookie browser smoke:
  first run `r5a-stale-authority-cleanup-operator-local-current` produced no
  data diffs and no dashboard snapshot diffs, but failed the route text wait on
  both desktop/mobile after a cold/warm-up over-budget navigation. Classified
  as verifier/topology warm-up latency rather than product regression because
  `/v1/health`, `/operator`, and dashboard snapshots were healthy.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r5a-stale-authority-cleanup-v2-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r5a-stale-authority-cleanup-v2-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `7624ms`, mobile `8216ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and
  `cohort_status=yellow` for real-data gaps only.

Behavior parity statement:

- Lyra product runtime behavior is unchanged.
- Test auth behavior is unchanged; only documentation now describes the current
  fail-closed/runtime vs test-harness distinction.
- Provider/deadline runtime behavior is unchanged; docs now say provider rows
  remain candidates/evidence unless explicitly confirmed.
- OpenClaw local compatibility config no longer exposes direct mutation tools
  by default; reintroduction requires explicit authenticated/audited command
  authority.

Rollback note:

- Revert the R5a docs/config commit only. This restores the previous stale
  docs/config wording and OpenClaw tool metadata without touching Lyra schemas,
  production data, frontend code, backend runtime code, Redis data, or
  lifecycle rows.

## S1c - OpenClaw Operator Relay Hermetic Gate

Changed authority:

- No Lyra product route, schema, frontend component, user-facing behavior, or
  production data changed.
- `scripts/openclaw_operator_relay.mjs` now exposes a small testable relay core
  while preserving the existing CLI loop.
- `scripts/run_s1c_verification_stack.ps1` now runs the hermetic relay test as
  a standard S1c gate.
- Relay send-failure reasons are sanitized before logs/dead-letter metadata can
  include them.

Removed paths:

- No runtime path was removed.
- No OpenClaw queue, Redis key, Telegram setting, or operator alert path was
  deleted.

Parked paths:

- Live Telegram/Redis relay smoke remains a runtime runbook concern.
- OpenClaw direct product mutation remains parked.
- Provider credential browser mutation and account hard-delete browser proof
  remain gated on disposable credentials/accounts.

Moved authority:

- Relay reliability proof moved from manual-only inspection into a reusable
  hermetic gate.
- Operator alert transport authority remains with the OpenClaw relay and
  canonical notification/operator alert services.

Agent-loop findings:

- Explorer C identified OpenClaw pending-drain as the largest remaining
  reusable verification gap. Backend redaction/mirroring tests existed, but the
  relay's `pending -> processing -> ack/requeue/dead_letter` state machine was
  not covered by a fast hermetic test.

Tests and verification:

- Relay unit/harness test:
  `node scripts\test_openclaw_operator_relay.mjs` passed.
- Node syntax checks:
  `node --check scripts\openclaw_operator_relay.mjs` and
  `node --check scripts\test_openclaw_operator_relay.mjs` passed.
- S1c lightweight stack:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology local -SkipBackendFull -SkipFrontendBuild -SkipBrowser`
  passed, including authority scan hard-fail mode, refactor contract scan
  hard-fail mode, the new OpenClaw relay hermetic test, and Alembic fresh DB
  smoke.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.

Behavior parity statement:

- Normal relay startup still reads Telegram config, restores processing rows,
  blocks on pending notifications, sends Telegram messages, acknowledges only
  after send success, requeues on send failure, and dead-letters malformed JSON.
- The new test proves pending entries move into processing before send,
  successful sends remove processing rows only after the send function runs,
  send failures requeue instead of dropping, malformed JSON moves to
  dead-letter, and logs do not expose injected token/raw-payload strings.
- No Lyra app runtime behavior changed. The operator read-only browser proof
  was run anyway as the standard post-wave cockpit sanity check.

Rollback note:

- Revert the S1c relay-hardening commit only. This restores the previous relay
  script and removes the hermetic test from the S1c stack without touching Lyra
  schemas, production data, frontend code, backend app code, Redis data, or
  lifecycle rows.

## R3 - Pulse Re-entry Cache Invalidation Helper

Changed authority:

- No product authority changed.
- Pulse remains the hub for re-entry prompts.
- The shared frontend query-key contract now owns the exact Pulse re-entry
  cache invalidation set.

Removed paths:

- No runtime path was removed.
- No route, schema, API payload, timer command, task mutation, exposure row, or
  provider path changed.

Parked paths:

- Deeper stopwatch controller extraction remains parked.
- Deeper NewTaskModal submit-flow extraction remains parked.
- Shared brain-dump reducer extraction remains parked until onboarding coverage
  is strong enough.

Moved authority:

- The Pulse re-entry refresh invalidation list moved from
  `PulseReentryQueue.tsx` into `frontend/lib/query-keys.ts`.

Agent-loop findings:

- Explorer D ranked this as the smallest R3 extraction seam: it preserves the
  current invalidation set exactly and does not touch payload shape, UI branch
  logic, or mutation authority.

Tests and verification:

- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Frontend typecheck-equivalent:
  `npm exec tsc -- --noEmit --pretty false` passed from `frontend/`.
- Health preflight:
  local API `/v1/health` returned 200 and local frontend returned 200.
- Operator-cookie browser proof before mutable loop:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-pulse-reentry-cache-helper-operator-local-current`
  passed.
- Operator artifact before mutable loop:
  `tmp/operator-readonly-stress-r3-pulse-reentry-cache-helper-operator-local-current/result.json`.
- Holmesberg mutable product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-pulse-reentry-cache-helper-holmesberg-local-current --out-dir tmp\browser-product-loop\r3-pulse-reentry-cache-helper-holmesberg-local-current`
  passed with `ok=true`.
- Holmesberg product artifact:
  `tmp/browser-product-loop/r3-pulse-reentry-cache-helper-holmesberg-local-current/result.json`.
- Product-loop coverage included route renders, deadline linkage, creation nudge
  branches, brain-dump retry and double-submit protection, pressure-map commit,
  timer pause/resume/stop, export evidence, exposure render/ack rows,
  notification lifecycle terminal rows, operator leak checks, and cleanup proof.
- Product-loop cleanup proof:
  no active Holmesberg timer remained and no unrendered synthetic creation-nudge
  exposure rows remained.
- Non-fatal product-loop issues were classified as existing gated/verifier
  conditions: onboarding gate skip for the chaos account, fallback deadline
  picker use, Today-view visibility gaps after backend assertions, parser title
  normalization, pressure safe-mode recovery fixture, provider credential
  mutation, hard-delete purge, calendar drag/resize, and OpenClaw pending drain.
  The deadline-suggestion UX budget remains tracked by GitHub issue #149.
- Operator-cookie browser proof after mutable loop:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-pulse-reentry-cache-helper-post-holmesberg-operator-local-current`
  passed.
- Operator artifact after mutable loop:
  `tmp/operator-readonly-stress-r3-pulse-reentry-cache-helper-post-holmesberg-operator-local-current/result.json`.
- Operator outcome after mutable loop:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6597ms`, mobile `5169ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and
  cohort status remains yellow only for real-data gaps.

Behavior parity statement:

- Pulse re-entry still invalidates stopwatch status, tasks, task range,
  task evidence, and pressure map caches after resume, stale-resolution,
  mark-done, and abandon actions.
- The helper intentionally does not invalidate `me` or `deadlines`, matching the
  previous inline behavior.

Rollback note:

- Revert the R3 Pulse re-entry cache helper commit only. This restores inline
  invalidation calls without touching schemas, production data, backend code,
  exposure lifecycle rows, Redis data, or user content.

## R3 - Brain Dump Binding Choice Helper

Changed authority:

- No product authority changed.
- Pulse and onboarding still own their modal/page flows.
- `frontend/lib/brain-dump-ui.ts` now owns the pure binding-choice transition
  shared by both surfaces.

Removed paths:

- No runtime path was removed.
- No route, schema, API payload, task/deadline mutation, exposure lifecycle row,
  provider path, or onboarding completion path changed.

Parked paths:

- Full shared brain-dump reducer extraction remains parked.
- First-run onboarding end-to-end browser automation remains parked until the
  disposable-account path is ready.

Moved authority:

- The "choose yes/no and clear competing deadline bindings for the same parsed
  task" transition moved from duplicate component-local functions into
  `chooseBrainDumpBinding()`.

Agent-loop findings:

- Explorer D ranked this as the next-smallest R3 seam after query-key
  invalidation. The duplicated Pulse/onboarding blocks were identical and
  suitable for a pure helper; deeper reducer extraction remains too broad for
  this pass.

Tests and verification:

- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Frontend typecheck-equivalent:
  `npm exec tsc -- --noEmit --pretty false` passed from `frontend/`.
- Health preflight:
  local API `/v1/health` returned 200 and local frontend returned 200.
- Holmesberg mutable product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-brain-dump-binding-helper-holmesberg-local-current --out-dir tmp\browser-product-loop\r3-brain-dump-binding-helper-holmesberg-local-current`
  passed with `ok=true`.
- Holmesberg product artifact:
  `tmp/browser-product-loop/r3-brain-dump-binding-helper-holmesberg-local-current/result.json`.
- Product-loop coverage included route renders, deadline linkage, edit mode,
  creation nudge branches, brain-dump parse/commit, partial failure, retry,
  double-submit protection, pressure-map commit, timer pause/resume/stop, export
  evidence, exposure render/ack rows, notification lifecycle terminal rows,
  operator leak checks, and cleanup proof.
- Product-loop cleanup proof:
  no active Holmesberg timer remained and no unrendered synthetic creation-nudge
  exposure rows remained.
- Non-fatal product-loop issues were classified as existing gated/verifier
  conditions: onboarding gate skip for the chaos account, fallback deadline
  picker use, parser title normalization, pressure safe-mode recovery fixture,
  provider credential mutation, hard-delete purge, calendar drag/resize, and
  OpenClaw pending drain. The deadline-suggestion UX budget remains tracked by
  GitHub issue #149.
- Operator-cookie browser proof after mutable loop:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-brain-dump-binding-helper-post-holmesberg-operator-local-current`
  passed.
- Operator artifact after mutable loop:
  `tmp/operator-readonly-stress-r3-brain-dump-binding-helper-post-holmesberg-operator-local-current/result.json`.
- Operator outcome after mutable loop:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6110ms`, mobile `5145ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and
  cohort status remains yellow only for real-data gaps.

Behavior parity statement:

- Choosing "yes" for one binding still marks that binding "yes" and marks all
  other bindings for the same parsed task "no".
- Choosing "no" still only marks the selected binding "no".
- Initial tier-1/tier-2 binding choice behavior is unchanged.

Rollback note:

- Revert the R3 brain-dump binding helper commit only. This restores duplicate
  local helper bodies in Pulse and onboarding without touching schemas,
  production data, backend code, exposure lifecycle rows, Redis data, or user
  content.

## R3 - NewTaskModal Nudge Payload Helper

Changed authority:

- No product authority changed.
- NewTaskModal still owns task creation/edit/interruption UI flow.
- `createTask()` payload field names and backend semantics are unchanged.

Removed paths:

- No runtime path was removed.
- No route, schema, API contract, exposure lifecycle row, timer command, task
  mutation authority, deadline binding authority, or provider path changed.

Parked paths:

- Full NewTaskModal draft-state extraction remains parked.
- Deadline preview state extraction remains parked.
- Submit/edit/interruption flow extraction remains parked beyond this small
  nudge payload helper.

Moved authority:

- The repeated conversion from modal nudge outcome state into
  `CreateTaskInput` fields moved into `nudgePayloadFromDecision()`.
- The repeated conversion from a rendered `CalibrationNudge` plus user choice
  into modal nudge outcome state moved into `nudgeDecisionFromCalibration()`.

Agent-loop findings:

- Explorer D identified the nudge telemetry payload as the smallest viable
  NewTaskModal seam. Explorer E was spawned for a focused follow-up; the local
  implementation matched its recommendation to keep the mapper module-local and
  defer render-snapshot extraction because that path touches exposure telemetry
  intent.

Tests and verification:

- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Frontend typecheck-equivalent:
  `npm exec tsc -- --noEmit --pretty false` passed from `frontend/`.
- Backend contract tests:
  initial bare `python -m pytest backend/tests/test_calibration_nudge_event.py backend/tests/test_output_surfaces.py`
  failed with `ModuleNotFoundError: No module named 'fastapi'`; classified as
  verifier environment selection, not product failure.
- Backend contract tests rerun with canonical venv:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_calibration_nudge_event.py tests\test_output_surfaces.py -q`
  passed, `47 passed`.
- Full frontend production build was not run during this live-dev seam because
  GitHub issue #144 tracks dev-server corruption risk from concurrent frontend
  builds. Typecheck plus browser proof were used here; production build remains
  required for wave closure.
- Holmesberg mutable product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-new-task-nudge-payload-helper-holmesberg-local-current --out-dir tmp\browser-product-loop\r3-new-task-nudge-payload-helper-holmesberg-local-current`
  passed with `ok=true`.
- Holmesberg product artifact:
  `tmp/browser-product-loop/r3-new-task-nudge-payload-helper-holmesberg-local-current/result.json`.
- Product-loop coverage included route renders, deadline linkage, soft-conflict
  force-create, nudge keep branch, no-deadline branch, custom category, deadline
  pick-another, edit mode, terminal-deadline rejection, brain-dump parse/commit,
  partial failure, retry, double-submit protection, pressure-map commit, timer
  pause/resume/stop, export evidence, exposure render/ack rows, notification
  lifecycle terminal rows, operator leak checks, and cleanup proof.
- Product-loop cleanup proof:
  no active Holmesberg timer remained and no unrendered synthetic creation-nudge
  exposure rows remained.
- Non-fatal product-loop issues were classified as existing gated/verifier
  conditions: onboarding gate skip for the chaos account, fallback deadline
  picker use, parser title normalization, pressure safe-mode recovery fixture,
  provider credential mutation, hard-delete purge, calendar drag/resize, and
  OpenClaw pending drain. The deadline-suggestion UX budget remains tracked by
  GitHub issue #149.
- Operator-cookie browser proof after mutable loop:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-new-task-nudge-payload-helper-post-holmesberg-operator-local-current`
  passed.
- Operator artifact after mutable loop:
  `tmp/operator-readonly-stress-r3-new-task-nudge-payload-helper-post-holmesberg-operator-local-current/result.json`.
- Operator outcome after mutable loop:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5996ms`, mobile `5092ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and
  cohort status remains yellow only for real-data gaps.

Behavior parity statement:

- Normal create, soft-conflict force-create, and interruption-create still send
  the same `nudge_decision`, `nudge_suggested_duration_minutes`,
  `nudge_bias_factor`, `nudge_sample_size`, and `nudge_viewed_at` fields when a
  nudge decision exists.
- When no nudge decision exists, those fields remain omitted.
- Nudge "Use" and "Keep" handlers still record the same suggested minutes, bias
  factor, sample size, viewed-at timestamp, and accepted/dismissed decision.
- Edit-mode reschedule behavior remains unchanged and still does not write
  nudge outcome payload.

Rollback note:

- Revert the R3 NewTaskModal nudge payload helper commit only. This restores
  inline payload spreads without touching schemas, production data, backend
  code, exposure lifecycle rows, Redis data, or user content.

## R3 - Today Refresh Invalidation Helper And CI/CD Loop Leg

Changed authority:

- No product authority changed.
- Today remains the execution surface for task commands.
- The post-wave runbook now treats CI/CD as a separate proof leg after push,
  distinct from local-current browser proof and hosted-public proof.

Removed paths:

- No runtime path was removed.
- No route, schema, API contract, exposure lifecycle row, timer command, task
  mutation authority, deadline binding authority, provider path, or deployment
  workflow changed.

Parked paths:

- Further Today state-machine extraction remains parked.
- Active-timer-banner extraction remains parked.
- CI/CD hard-fail lint gating remains parked until issue #153 is resolved.

Moved authority:

- The repeated Today command refresh invalidation moved into
  `invalidateTodayTaskCommandSurfaces()`.
- The helper invalidates the same current-day task, next-day task, and stopwatch
  status query surfaces as the previous inline code.

Agent-loop findings:

- Explorer F recommended this as the final low-risk R3 seam before stopping
  frontend extraction: extract only the Today refresh invalidation helper and
  leave optimistic state, rollback snapshots, and mutation logic untouched.

Tests and verification:

- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Frontend typecheck-equivalent:
  `npm exec tsc -- --noEmit --pretty false` passed from `frontend/`.
- Frontend lint:
  `npm run lint` failed before checking source because `next lint` is
  deprecated/interactive under the current Next.js setup. Classified as a
  CI/CD operations and verifier-harness bug, not a product regression. Tracked
  as GitHub issue #153.
- First Holmesberg mutable product-loop attempt timed out at the shell command
  budget after producing late-run artifacts but no `result.json`. Classified as
  local harness timeout budget, not product behavior. The orphan process had
  already exited when inspected.
- Holmesberg mutable product-loop rerun:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r3-today-refresh-helper-holmesberg-local-current-rerun --out-dir tmp\browser-product-loop\r3-today-refresh-helper-holmesberg-local-current-rerun`
  passed with `ok=true`.
- Holmesberg product artifact:
  `tmp/browser-product-loop/r3-today-refresh-helper-holmesberg-local-current-rerun/result.json`.
- Product-loop coverage included route renders, deadline linkage, soft-conflict
  force-create, nudge Keep branch, no-deadline branch, custom category,
  deadline pick-another, edit mode, terminal-deadline rejection, brain-dump
  parse/commit, partial failure, retry, double-submit protection, pressure-map
  commit, timer pause/resume/stop, export evidence, exposure render/ack rows,
  notification lifecycle terminal rows, operator leak checks, and cleanup proof.
- Product-loop cleanup proof:
  no active Holmesberg timer remained and no unrendered synthetic creation-nudge
  exposure rows remained.
- Operator-cookie browser proof after mutable loop:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-today-refresh-helper-post-holmesberg-operator-local-current`
  passed.
- Operator artifact after mutable loop:
  `tmp/operator-readonly-stress-r3-today-refresh-helper-post-holmesberg-operator-local-current/result.json`.
- Operator outcome after mutable loop:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6586ms`, mobile `5177ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Today command refresh still invalidates the same current-day task,
  next-day task, and stopwatch status query surfaces.
- Start, stop, skip, void, deadline-binding save, and other command handlers
  keep their existing optimistic updates, rollback snapshots, and mutation
  behavior.
- The CI/CD runbook change only changes verification documentation; it does not
  alter deployment workflow behavior.

CI/CD proof note:

- Local lint cannot currently serve as a hard CI/CD gate because issue #153
  must be resolved first.
- Post-push GitHub Actions/PR check status must be recorded for this seam after
  the branch is pushed.

Rollback note:

- Revert the R3 Today refresh helper commit only. This restores inline
  invalidations without touching schemas, production data, backend code,
  exposure lifecycle rows, Redis data, deployment workflows, or user content.

## CI/CD - Provider Credential Test Redis Isolation

Changed authority:

- No runtime authority changed.
- CI/CD is now treated as an explicit post-push proof leg for the refactor loop.

Removed paths:

- No runtime path was removed.
- No production Redis behavior changed.

Parked paths:

- CI workflow Node action deprecation warnings remain parked as CI maintenance.
- Frontend lint hard-gating remains parked behind issue #153.

Moved authority:

- The provider credential security test now owns its Redis cache-invalidation
  side-effect through a local fake client. Production `calendar_sync.RedisClient`
  ownership is unchanged.

Bug and classification:

- GitHub issue #154 tracks the failing CI backend test.
- Classification: CI/CD operations bug and verifier-harness bug.
- Failing run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28549542307`.
- Root cause:
  `tests/test_provider_credentials_security.py::test_google_refresh_token_is_encrypted_at_rest`
  called `calendar_sync.store_refresh_token()`, which invalidated the Google
  access-token cache through a real Redis client. CI does not provision Redis.

Tests and verification:

- Local exact failing test:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_provider_credentials_security.py::test_google_refresh_token_is_encrypted_at_rest -q`
  passed.
- Local provider credential security file:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_provider_credentials_security.py -q`
  passed, `2 passed`.
- CI rerun after the fix:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28549752568`
  passed on head `58b1d0c0bd15c76cbaf65b083a46aa6d3e475dda`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Behavior parity statement:

- The test still verifies Google refresh-token encryption at rest and successful
  decryption back to the raw token.
- The test no longer depends on a live Redis daemon for the cache-delete
  side-effect.
- Production `store_refresh_token()` still invalidates the access-token cache.

Rollback note:

- Revert the CI/CD provider credential Redis isolation commit only. This
  restores the test's live Redis dependency without touching runtime code,
  schemas, production data, exposure lifecycle rows, or user content.

## R4 - OpenClaw Pending Compatibility Peek

Changed authority:

- OpenClaw operator relay remains the single delivery authority for operator
  alerts.
- `/v1/notifications/openclaw/pending` and legacy
  `/v1/notifications/pending?channel=openclaw` are now operator-gated,
  compatibility-only, and read-only.
- The compatibility endpoints explicitly report
  `delivery_authority=openclaw_operator_relay` and
  `destructive_drain=false`.

Removed paths:

- Removed the internal `drain_user_notifications()` helper from
  `notification_queue.py`.
- Removed the HTTP path that destructively popped Redis queue items before
  confirmed OpenClaw delivery.

Parked paths:

- Full OpenClaw runtime/service extraction remains parked.
- GitHub Actions Node deprecation maintenance remains tracked by issue #155.
- Frontend lint hard-gating remains parked behind issue #153.

Moved authority:

- Compatibility polling now uses `peek_user_notifications(..., channel="openclaw")`.
- Reliable dequeue/ack/requeue/dead-letter authority remains in
  `scripts/openclaw_operator_relay.mjs`.
- Test Redis cleanup moved away from the OpenClaw product endpoint and into the
  Redis test helper path.

Agent-loop findings:

- Explorer C identified the destructive `/openclaw/pending` endpoint as the
  sharpest remaining authority risk because it used Redis `lpop` while the
  relay already owned processing/ack/requeue semantics.
- Conservative resolution: keep the route briefly for compatibility, but make
  it operator-only and non-destructive. No schema migration and no runtime AI
  wiring.

Tests and verification:

- Removed references:
  `rg 'drain_user_notifications' backend/app backend/tests -n` returns no
  matches.
- Notification/OpenClaw tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_notification_queue_openclaw_mirror.py -q`
  passed, `12 passed`.
- Operator route security:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_route_security.py -q`
  passed, `6 passed`.
- Operator notifier:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_notifier.py -q`
  passed, `7 passed`.
- Multi-user notification isolation:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_multiuser_isolation_adversarial.py::test_notifications_per_user_isolated -q`
  passed.
- Relay reliability:
  `node scripts\test_openclaw_operator_relay.mjs` passed with
  restore/processing/ack/requeue/dead-letter checks.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-openclaw-pending-peek-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-openclaw-pending-peek-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `8140ms`, mobile `5673ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Web notification pending/ack behavior remains peek/ack based.
- OpenClaw compatibility endpoints still return pending operator queue payloads
  to the operator account, but no longer remove Redis items.
- Non-operators cannot access the OpenClaw pending compatibility endpoint.
- The reliable relay remains responsible for actual queue consumption and
  confirmed delivery.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28550722518`.
- Head SHA:
  `25aced5f5bf4d9724152b856e0b0e515410dee4a`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the R4 OpenClaw pending compatibility peek commit only. This restores
  the previous destructive OpenClaw pending drain behavior without touching
  schemas, production data, frontend code, exposure lifecycle rows, or user
  content.

## R4 - Operator Lifecycle Snapshot Builder

Changed authority:

- No runtime mutation authority changed.
- `/v1/operator/dashboard` remains the operator cockpit authority.
- Notification/exposure lifecycle health is now computed by the read-only
  `notification_lifecycle_snapshot()` builder in
  `operator_dashboard_metrics.py` instead of inline route code.
- Redis pending queue inspection still uses the existing read-only operator
  snapshot helper.

Removed paths:

- Removed duplicated notification/exposure lifecycle aggregation code from the
  operator route body.
- Removed route-level dependency on notification lifecycle and suppression ORM
  models for this lifecycle subsection.

Parked paths:

- Broader analytics extraction remains parked until operator truth stays green.
- Hard-failing frontend lint remains parked behind issue #153.
- GitHub Actions Node deprecation maintenance remains tracked by issue #155.

Moved authority:

- Lifecycle calculation moved from a route-owned block to a registered
  operator metric helper.
- Dashboard rendering, readiness issue generation, and cohort/implementation
  status assembly remain in the operator route for now.

Verifier finding:

- Classification: verifier/harness bug.
- The first browser proof failed intermittently because
  `browser_stress_operator_readonly.mjs` used a brittle visible text locator as
  canonical route proof. Backend dashboard snapshots and exported data counts
  stayed unchanged, and the failure flipped between desktop and mobile on
  rerun.
- Fix: route readiness now waits on DOM body text evidence while backend state,
  exported evidence, and operator invariant snapshots remain canonical proof.
  Failure screenshots are saved as contextual artifacts only.

Tests and verification:

- Operator dashboard fixtures:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py -q`
  passed, `10 passed`.
- Operator route security:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_route_security.py -q`
  passed, `6 passed`.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Verifier syntax:
  `node --check scripts\browser_stress_operator_readonly.mjs` passed.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-operator-lifecycle-builder-operator-local-current-fixed-verifier`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-operator-lifecycle-builder-operator-local-current-fixed-verifier/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6880ms`, mobile `5009ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and readiness semantics are unchanged.
- Exposure-without-render remains critical.
- Suppressed and queued-without-render rows remain counted separately and do
  not become actionable exposure blockers.
- Operator dashboard reads remain side-effect-free.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28551496478`.
- Head SHA:
  `e1216904047d3ec9bfceee3ee3b428b0ad30c9ea`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.
- Verifier bug issue:
  GitHub issue #156 was opened and closed as resolved by this commit.

Rollback note:

- Revert the operator lifecycle snapshot builder commit only. This restores the
  inline route aggregation and the previous verifier locator without touching
  schemas, production data, exposure lifecycle rows, Redis queues, or user
  content.

## R4 - Operator Data Freshness Builder

Changed authority:

- No runtime mutation authority changed.
- `/v1/operator/dashboard` remains the operator cockpit authority.
- Data freshness packaging is now computed by the read-only
  `data_freshness_snapshot()` helper in `operator_dashboard_metrics.py`.
- Cohort readiness, dynamic issues, and warning semantics remain in the
  operator route.

Removed paths:

- Removed duplicated timestamp-packaging code from the operator route body.
- Removed stale route imports that existed only for data-freshness timestamp
  aggregation.

Parked paths:

- Cohort readiness/watchlist extraction remains parked because agents split on
  whether it could blur `/operator` readiness authority.
- Provider integrity and measurement integrity extractions remain parked until
  stronger characterization coverage exists.
- Frontend lint hard-gating remains parked behind issue #153.
- GitHub Actions Node deprecation maintenance remains tracked by issue #155.

Moved authority:

- Source freshness timestamp calculation moved from inline route code to a
  registered operator metric helper.
- The intentional `notifications_last_seen_at=None` source gap remains
  visible to the operator route and still creates the
  `notification_source_freshness_not_instrumented` warning.

Agent-loop findings:

- Explorer B ranked `data_freshness` as the lowest-risk next extraction because
  it is timestamp packaging and must preserve the intentional notification
  freshness gap.
- Explorer C recommended a small verifier contract test so the corrected
  browser-proof behavior stays protected by CI.
- Explorer A proposed readiness/watchlist extraction, but that seam remains
  parked for now because readiness authority should stay unambiguous.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `17 passed`.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-data-freshness-builder-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-data-freshness-builder-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5951ms`, mobile `5413ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and readiness semantics are unchanged.
- `notifications_last_seen_at` remains uninstrumented and appears in
  `data_freshness.stale_sources`.
- The notification source freshness warning remains present and non-blocking.
- Operator dashboard reads remain side-effect-free.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28555537840`.
- Head SHA:
  `45c23dd0211f8acf9aa41da3308b191c64d773c8`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator data freshness builder commit only. This restores inline
  route timestamp packaging without touching schemas, production data,
  exposure lifecycle rows, Redis queues, or user content.

## R4 - Operator Product Loop Funnel Builder

Changed authority:

- No runtime mutation authority changed.
- `/v1/operator/dashboard` remains the operator cockpit authority.
- Product-loop funnel payload assembly is now computed by the read-only
  `product_loop_funnel_snapshot()` helper in `operator_dashboard_metrics.py`.
- The operator route still owns the upstream DB counts, dynamic issues, and
  cohort readiness semantics.

Removed paths:

- Removed duplicated product-loop funnel dict assembly from the operator route.
- Removed the route-level dependency on the `dropoff_points()` helper.

Parked paths:

- Product-loop funnel instrumentation gaps remain explicit and are not filled
  by inference.
- Cohort readiness/watchlist extraction remains parked until readiness
  authority is explicitly settled.
- Measurement integrity extraction remains parked until broader denominator and
  dirty-bucket characterization exists.

Moved authority:

- Funnel formatting moved from inline route code to a registered operator
  metric helper.
- Product-loop counts remain diagnostic/product-health signals only; they do
  not become clean-data evidence or ClaimCompiler authority.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `17 passed`.
- Drift coverage added:
  an exposure-contaminated stopped session still counts as
  `product_loop_funnel.timer_stopped_cleanly=1` while
  `measurement_integrity.clean_trace_ratio=0.0`, preserving the distinction
  between product-loop progress and clean measurement evidence.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-product-loop-funnel-builder-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-product-loop-funnel-builder-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6895ms`, mobile `5292ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and readiness semantics are unchanged.
- Funnel dropoff warnings still derive from the same funnel values.
- Product-loop clean-stop count remains weaker than clean-trace measurement and
  must not be read as a clean evidence denominator.
- Operator dashboard reads remain side-effect-free.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28555825510`.
- Head SHA:
  `ff8374287a3aef3abea487590f13416e6cb6e575`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator product-loop funnel builder commit only. This restores
  inline funnel assembly without touching schemas, production data, exposure
  lifecycle rows, Redis queues, or user content.

## R4 - Operator State Invariants Builder

Changed authority:

- No runtime mutation authority changed.
- `/v1/operator/dashboard` remains the operator cockpit authority.
- State-invariant payload assembly is now computed by the read-only
  `state_invariants_snapshot()` helper in `operator_dashboard_metrics.py`.
- The operator route still owns the upstream task/session counts, dynamic
  issues, implementation/cohort status, and minimum fix set.

Removed paths:

- Removed duplicated state-invariant dict assembly from the operator route.

Parked paths:

- Cohort readiness/watchlist extraction remains parked until readiness
  authority is explicitly settled.
- Measurement integrity extraction remains parked until broader denominator and
  dirty-bucket characterization exists.
- State repair remains out of scope; this pass only preserves diagnostics.

Moved authority:

- State-invariant formatting moved from inline route code to a registered
  operator metric helper.
- State-invariant issue severity and cohort blocking remain in the operator
  route, where the readiness contract already lives.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `17 passed`.
- Characterization added:
  `paused_tasks_without_open_session` and
  `open_sessions_for_executed_tasks` now have explicit dashboard and dynamic
  issue assertions.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-state-invariants-builder-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-state-invariants-builder-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5651ms`, mobile `5645ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and readiness semantics are unchanged.
- State-invariant critical issues still derive from the same route-owned
  invariant counts.
- `/operator` remains read-only and does not repair or mutate state.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28556158661`.
- Head SHA:
  `d360e5a696bd6b08d41042c2f5dc965fa674cfd9`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator state-invariants builder commit only. This restores
  inline state-invariant assembly without touching schemas, production data,
  exposure lifecycle rows, Redis queues, or user content.

## R4 - Operator Provider Integrity Builder

Changed authority:

- No runtime mutation authority changed.
- `/v1/operator/dashboard` remains the operator cockpit authority.
- Provider-integrity payload assembly is now computed by the read-only
  `provider_integrity_snapshot()` helper in `operator_dashboard_metrics.py`.
- The operator route still owns provider queries/counts, dynamic issues,
  implementation/cohort status, and provider blocker semantics.

Removed paths:

- Removed duplicated provider-integrity dict assembly from the operator route.

Parked paths:

- Provider query extraction remains parked; this pass only moves count-in,
  payload-out formatting.
- Provider connection-model extraction remains parked until schema authority is
  granted.
- Measurement integrity extraction remains parked because provider-only rows
  still participate in denominator and dirty-reason decisions.

Moved authority:

- Provider-integrity formatting moved from inline route code to a registered
  operator metric helper.
- Provider-truth violation severity and cohort blocking remain in the operator
  route, where readiness authority already lives.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `18 passed`.
- Characterization added:
  provider deadlines with missing provenance and provider completion candidates
  still surface `provider_rows_missing_provenance` and
  `provider_truth_violation` without treating provider completion as clean
  execution truth.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-provider-integrity-builder-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-provider-integrity-builder-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5758ms`, mobile `4553ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and readiness semantics are unchanged.
- Provider completion rows remain provenance/candidates; they do not become
  clean execution truth.
- Provider warning/blocker issue emission remains route-owned.
- `/operator` remains read-only and does not repair provider state.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28556532122`.
- Head SHA:
  `d2570867e8b602c84f92a83e675c3aca536e3812`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator provider-integrity builder commit only. This restores
  inline provider-integrity assembly without touching schemas, production data,
  exposure lifecycle rows, provider rows, Redis queues, or user content.

## R4 - Operator Privacy Boundary Builder

Changed authority:

- No runtime mutation authority changed.
- `/v1/operator/dashboard` remains the operator cockpit authority.
- Privacy-boundary payload assembly is now computed by the read-only
  `privacy_boundary_snapshot()` helper in `operator_dashboard_metrics.py`.
- The operator route still owns the privacy-boundary dynamic issue and cohort
  blocking semantics.

Removed paths:

- Removed duplicated privacy-boundary dict assembly from the operator route.

Parked paths:

- Reliability and output-surface diagnostics extraction remain parked.
- Measurement integrity extraction remains parked.
- Privacy leak detection remains explicit and static in this pass; no new
  scanner or runtime inspection authority was added.

Moved authority:

- Privacy-boundary formatting moved from inline route code to a registered
  operator metric helper.
- Privacy violation interpretation remains in the operator route.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `18 passed`.
- Characterization expanded:
  privacy-boundary assertions now cover raw task titles, raw emails, provider
  tokens, raw provider URLs, and user debug mode.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-privacy-boundary-builder-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-privacy-boundary-builder-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5713ms`, mobile `4609ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and readiness semantics are unchanged.
- Privacy-boundary flags remain false unless the route-owned gate detects a
  violation in future work.
- `/operator` remains read-only and does not repair or mutate state.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28556787664`.
- Head SHA:
  `3faaaee15b053e4aed8c22e9d151b0d3bd2a4aaa`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator privacy-boundary builder commit only. This restores
  inline privacy-boundary assembly without touching schemas, production data,
  exposure lifecycle rows, provider rows, Redis queues, or user content.

## R4 - Stopwatch Current Pause Anchor Helper

Changed authority:

- No runtime mutation authority changed.
- Stopwatch session authority remains with `StopwatchManager` and Redis
  stopwatch state methods.
- This pass extracted the read-only current-pause display anchor calculation
  from `StopwatchManager.get_status()` into `_derive_current_pause_anchor()`.

Removed paths:

- Removed duplicated inline parsing of `pause_state["paused_at"]` from
  `get_status()`.

Parked paths:

- Broader stopwatch store/lifecycle/finalizer/effects extraction remains
  parked.
- Timer recovery, stale-session recovery, and worker-side stopwatch mutation
  seams remain parked until their characterization tests are hardened.
- No schema, Redis-key, or notification/exposure lifecycle change was made.

Moved authority:

- No business authority moved. The helper is a count-in, payload-out display
  primitive for the existing stopwatch status response.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\stopwatch_manager.py`
  passed.
- Stopwatch characterization:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_stopwatch_pause_counter_anchor.py tests\test_stopwatch_recovery.py tests\test_state_consistency.py::test_self_heal_skipped_task_clears_banner -q`
  passed, `5 passed`.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed.
- Holmesberg mutable browser proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --force-pressure-recovery --run-id r4-stopwatch-pause-anchor-helper-holmesberg-local-current`
  passed.
- Holmesberg artifact:
  `tmp/browser-product-loop/r4-stopwatch-pause-anchor-helper-holmesberg-local-current/result.json`.
- Holmesberg outcome:
  non-operator identity resolved, route smoke passed, task/deadline linkage
  passed, duration nudge keep branch passed, timer pause/resume/stop path
  passed, table delta/export evidence contained task, stopwatch session, pause
  event, exposure decision/render/ack rows, and notification lifecycle terminal
  rows.
- Holmesberg cleanup proof:
  cleanup left no active timer and no unrendered synthetic creation-nudge
  exposures; cleaned suppression id
  `b42c337c-bbc5-4b77-8d9f-23e75d02a8d1`.
- Product-loop proof note:
  pressure-map recovery options were unavailable and the verifier used a
  browser-only recovery fixture for commit-seam coverage. This does not prove
  pressure-map recovery semantics.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-stopwatch-pause-anchor-helper-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-stopwatch-pause-anchor-helper-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5819ms`, mobile `4660ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- The active-work elapsed time semantics are unchanged.
- Malformed or missing `paused_at` still falls back to `0` seconds and `null`
  start anchor.
- The paused-duration display keeps using the original pause anchor rather than
  restarting from navigation or refresh.
- No user, task, session, provider, notification, exposure, or Redis lifecycle
  authority changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28557459916`.
- Head SHA:
  `2e854b23add747c925a7643a4740549c4c368f1d`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the stopwatch pause-anchor helper commit only. This restores the
  inline `get_status()` parsing block without touching schemas, production
  data, exposure lifecycle rows, provider rows, Redis queues, or user content.

## R4 - Operator Static Metadata Builder

Changed authority:

- No runtime mutation authority changed.
- `/v1/operator/dashboard` remains the operator cockpit authority.
- Static operator metadata assembly for metric confidence and meaningful
  activity definitions moved into read-only helper primitives in
  `operator_dashboard_metrics.py`.

Removed paths:

- Removed inline `metric_confidence` dict assembly from the operator route.
- Removed inline `meaningful_activity_definition` dict assembly from the
  operator route.

Parked paths:

- Cohort readiness/watchlist extraction remains parked.
- Measurement integrity extraction remains parked.
- Reliability and output-surface diagnostics extraction remain parked.
- Provider, Moodle, Jarvis/OpenClaw, and passive academic telemetry work remain
  blocked by R5a doc cleanup requirements before domain-specific extraction.

Moved authority:

- No truth or readiness authority moved. Only static presentation metadata moved
  from route-local assembly to operator metric helpers.
- The route still owns dynamic issue construction, implementation/cohort status,
  readiness blockers, and dashboard response composition.

Agent loop notes:

- Explorer A recommended this as the safest next R4 backend seam because it is
  static payload only: no DB query, no denominator, no readiness threshold, no
  exposure lifecycle, and no schema.
- Explorer B found the reusable wave loop still lacks structured CI/CD proof
  collection and recommended a read-only GitHub Actions proof helper.
- Explorer C found no global block on this seam, but identified provider/Moodle,
  Jarvis/OpenClaw, parked active-looking docs, and passive academic telemetry
  docs as blockers for work in those domains.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `18 passed`.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-operator-static-metadata-builder-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-operator-static-metadata-builder-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5704ms`, mobile `4616ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and values are unchanged.
- `metric_confidence` keeps the same metric keys and tier strings.
- `meaningful_activity_definition` keeps the same meta fields and
  included/excluded activity event lists.
- `/operator` remains read-only and does not repair or mutate state.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28557828081`.
- Head SHA:
  `704b586b00815a88f7f99bcba99dc45adf787748`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator static metadata builder commit only. This restores inline
  static metadata assembly in the operator route without touching schemas,
  production data, exposure lifecycle rows, provider rows, Redis queues, or user
  content.

## CI/CD - Structured Wave Proof Collector

Changed authority:

- No Lyra app runtime authority changed.
- CI/CD proof collection became a reusable, read-only verification leg through
  `scripts/collect_github_ci_cd_proof.ps1`.
- The post-wave dogfood wrapper can now opt into CI/CD proof collection with
  `-IncludeCiCdProof`.

Removed paths:

- None.

Parked paths:

- Automatic GitHub issue creation/update for CI failures remains parked because
  it mutates external project state.
- Broadening `.github/workflows/ci.yml` to run on every wave branch push remains
  parked because it changes branch policy/cost/noise.
- Frontend lint hard-gating remains parked behind issue #153.
- GitHub Actions Node deprecation maintenance remains tracked by issue #155.

Moved authority:

- Manual CI proof remains valid, but the standard artifact path now includes a
  structured JSON collector for GitHub Actions and PR-check state.
- The helper classifies missing/no-matching CI as CI/CD operations state instead
  of silently treating it as success.

Agent loop notes:

- Explorer B found that the runbook required post-push CI/CD proof, but the
  reusable wrapper did not implement structured collection.
- The implemented helper is read-only: `gh run list`, `gh run view`,
  `gh pr list`, and `gh pr checks` only.

Tests and verification:

- Standalone collector proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\collect_github_ci_cd_proof.ps1 -Branch wave-5-sovereignty-integrity-cycle -Workflow CI -OutFile tmp\ci-cd-proof\ci-helper-48b2842.json -FailOnUnsuccessful`
  passed.
- Collector artifact:
  `tmp/ci-cd-proof/ci-helper-48b2842.json`.
- Collector outcome:
  `ok=true`, `status=ci_success`, branch
  `wave-5-sovereignty-integrity-cycle`, head `48b2842`, matching CI run
  `28558079385`, and PR state `no_pr`.
- PowerShell parse smoke:
  `powershell -NoProfile -ExecutionPolicy Bypass -Command '$null = [scriptblock]::Create((Get-Content .\scripts\run_post_wave_dogfood_loop.ps1 -Raw)); $null = [scriptblock]::Create((Get-Content .\scripts\collect_github_ci_cd_proof.ps1 -Raw)); Write-Output parsed'`
  passed.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id ci-cd-proof-helper-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-ci-cd-proof-helper-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5771ms`, mobile `4771ms`, `implementation_green=true`,
  `implementation_blockers=[]`, and `exposure_without_render_count=0`.

Behavior parity statement:

- No product route, API route, model, schema, Redis key, exposure lifecycle,
  provider path, or browser UI behavior changed.
- CI/CD proof collection is opt-in and local-artifact-only unless the caller
  explicitly chooses `-CiCdFailOnUnsuccessful`.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28558079385`.
- Head SHA:
  `48b2842b3e68f9271032d6256032b718d97099a5`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the CI/CD proof collector commit only. This removes the standalone
  collector script, wrapper switches, and runbook text without touching Lyra app
  runtime behavior, schemas, production data, exposure lifecycle rows, provider
  rows, Redis queues, or user content.

## R4 - Operator Recommendations Projection Helper

Changed authority:

- No product, exposure, provider, readiness, or cohort authority changed.
- Operator recommendation row projection moved from the `/operator` route into
  `operator_dashboard_metrics.operator_recommendations_snapshot`.
- `/operator` still owns dashboard response composition and dynamic issue
  construction; the helper only projects already-built issue dictionaries into
  the existing response shape.

Removed paths:

- Removed route-local list comprehension for `operator_recommendations`.

Parked paths:

- Provider/Moodle, Jarvis/OpenClaw, passive academic telemetry, and measurement
  computation extraction remain blocked behind R5a stale-doc authority cleanup.
- Analytics/service extraction remains parked until operator truth and exposure
  invariants stay stable through standard verification.

Moved authority:

- No truth authority moved. A route presentation projection moved to the
  operator metric-builder layer.

Agent loop notes:

- Explorer A recommended this as a safe R4 follow-up seam because it is
  read-only payload shaping over existing dynamic issues: no DB query, no
  denominator, no threshold, no exposure lifecycle write, no schema, and no
  provider state.
- Explorer C's R5a blocker still applies to provider, Moodle, Jarvis/OpenClaw,
  passive academic telemetry, and active-looking parked docs.
- Verifier note: the first static-scan command used a backend-relative Python
  path from repo root. This was classified as a harness/command-path issue,
  corrected immediately, and did not indicate product behavior.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `18 passed`.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-operator-recommendations-projection-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-operator-recommendations-projection-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5859ms`, mobile `4719ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and values are unchanged.
- Operator recommendations still use the same severity, message,
  suggested_action, related_section, and blocks_cohort_expansion fields.
- `/operator` remains read-only and does not repair, suppress, queue, render, or
  otherwise mutate state.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28558403524`.
- Head SHA:
  `fd7eee230e2c81dd3ca624e4a6bde98934db3954`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator recommendations projection commit only. This restores the
  inline route comprehension without touching schemas, production data,
  exposure lifecycle rows, provider rows, Redis queues, or user content.

## R4 - Operator User Row Projection Helper

Changed authority:

- No product, exposure, provider, readiness, cohort, identity, or user-data
  authority changed.
- Operator non-operator-user row projection moved from the `/operator` route
  into `operator_dashboard_metrics.operator_user_rows_snapshot`.
- `/operator` still owns user selection, all queries, all denominators, all
  readiness decisions, and dashboard response composition.

Removed paths:

- Removed route-local user payload formatting loop.
- Removed the route-local `email_hash` alias that was only needed by that loop.

Parked paths:

- Provider/Moodle, Jarvis/OpenClaw, passive academic telemetry, and measurement
  computation extraction remain blocked behind R5a stale-doc authority cleanup.
- User account mutation, export/delete, and runtime purge authority were not
  touched and remain under the user-data registry/user endpoint boundary.

Moved authority:

- No truth authority moved. A read-only presentation projection moved to the
  operator metric-builder layer.

Agent loop notes:

- This seam follows the mini-loop recommendation for low-risk R4 work: move
  presentation-only assembly after operator truth and exposure blockers are
  stable.
- The helper accepts already-computed maps and user rows; it performs no DB
  query, Redis call, provider interpretation, exposure lifecycle operation, or
  readiness threshold decision.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `18 passed`.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-operator-user-rows-projection-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-operator-user-rows-projection-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5923ms`, mobile `5114ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and values are unchanged.
- User rows still expose the same minimized fields: id, first name/source,
  hashed email, activity dates/counts, task/session counts, clean trace ratio,
  open/stale timer counts, and last loop stage.
- `/operator` remains read-only and does not repair, suppress, queue, render,
  delete, export, or otherwise mutate state.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28558664138`.
- Head SHA:
  `a19a7a7c57c1a44d5566f39a311be4cd4c3d842b`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator user row projection commit only. This restores the inline
  route user-row loop without touching schemas, production data, exposure
  lifecycle rows, provider rows, Redis queues, export/delete behavior, or user
  content.

## R4 - Operator Bug Watchlist Projection Helper

Changed authority:

- No product, exposure, provider, readiness, cohort, schema, or mutation
  authority changed.
- Operator bug-watchlist projection moved from the `/operator` route into
  `operator_dashboard_metrics.bug_watchlist_snapshot`.
- `/operator` still owns dynamic issue construction, readiness status
  derivation, cohort evidence gaps, and dashboard response composition.

Removed paths:

- Removed route-local K-watchlist dictionary assembly.
- Removed the route-local `watchlist_status_from_issues` alias that was only
  needed by that dictionary.

Parked paths:

- Cohort-readiness extraction remains parked because it is stop/go authority,
  not mere presentation.
- Provider/Moodle, Jarvis/OpenClaw, passive academic telemetry, and measurement
  computation extraction remain blocked behind R5a stale-doc authority cleanup.

Moved authority:

- No truth or readiness authority moved. A read-only dynamic-issue tag
  projection moved to the operator metric-builder layer.

Agent loop notes:

- This seam was chosen over cohort-readiness extraction because it avoids moving
  `safe_to_invite_more_users`, implementation/cohort status, or evidence-gap
  semantics.
- The helper accepts dynamic issues and returns the same K-status row. It
  performs no DB query, Redis call, provider interpretation, exposure lifecycle
  operation, or threshold decision.

Tests and verification:

- Compile check:
  `cd backend && ..\.venv311\Scripts\python.exe -m py_compile app\services\operator_dashboard_metrics.py app\api\v1\endpoints\operator.py`
  passed.
- Operator dashboard, route security, and verifier contract:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py tests\test_verifier_contracts.py -q`
  passed, `18 passed`.
- Refactor contract scan:
  `python scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r4-operator-bug-watchlist-projection-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r4-operator-bug-watchlist-projection-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6076ms`, mobile `4622ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- Dashboard response shape and values are unchanged.
- Bug-watchlist fields keep the same K01/K02/K03/K04/K05 keys and the same
  pass/unknown/fail semantics.
- `/operator` remains read-only and does not repair, suppress, queue, render,
  delete, export, or otherwise mutate state.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28558907077`.
- Head SHA:
  `08eae3b68099f17bf652305296db1720a4eecc79`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the operator bug-watchlist projection commit only. This restores the
  inline route K-watchlist dictionary without touching schemas, production
  data, exposure lifecycle rows, provider rows, Redis queues, export/delete
  behavior, or user content.

## R5a - Stale Authority Docs And CI/CD Proof Alignment

Changed authority:

- Historical roadmap, handoff, audit, manifesto, LyraSim, provider, academic,
  and OpenClaw skill documents now explicitly subordinate themselves to the
  active freeze authority chain.
- CI/CD proof after push is now recorded as part of the stabilization ledger
  expectation, alongside browser/API/export proof and topology labels.
- OpenClaw skill documentation remains reference/compatibility material only;
  it does not authorize live scheduling, timer, task, GPT/OpenClaw synthesis,
  or product mutation during the freeze.

Removed paths:

- No runtime path was removed.
- Stale active-sounding command wording was removed from docs where it could
  imply current runtime permission.
- Legacy `docker-compose` command snippets in active-looking docs were replaced
  with `docker compose`.

Parked paths:

- `/insights`, avoidance/motivation/focus/productivity surfaces, passive
  tracking, behavior-transition equations, new provider adapters, schema
  migrations, OpenClaw/GPT product wiring, LyraSim-to-product behavior, and
  cohort expansion remain parked until a new explicit plan authorizes them.
- `scripts/restart_public_frontend.ps1` remains an unresolved topology
  operations gap, tracked in GitHub issue #158.
- CI branch trigger policy remains unresolved, tracked in GitHub issue #157.
- Alternate local-current frontend origins and wrapper/topology handling remain
  tracked in GitHub issue #147.

Moved authority:

- No product, exposure, provider, task, timer, notification, schema, or cohort
  authority moved.
- Stale docs moved from apparent implementation authority to historical or
  subordinate planning evidence.
- Hosted CI proof is now treated as a separate post-push proof leg rather than
  being inferred from local/browser verification.

Agent loop notes:

- Stale-authority explorer identified LyraSim, phase/backlog, feedback-loop,
  academic/provider, and handoff docs that needed stronger freeze fences.
- Forbidden-claim adversary flagged the manifesto surfacing mandate,
  `dogfood_findings_living.md`, and the OpenClaw skill command protocol as the
  highest-risk stale authority surfaces.
- CI/CD and runbook explorer flagged public restart ambiguity, alternate
  local-current topology proof, and branch CI trigger policy as operational
  gaps requiring issue tracking.

Tests and verification:

- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Stale-authority grep:
  exact live-command phrases for OpenClaw scheduling, live FastAPI mutation,
  and old `docker-compose restart/logs/ps` snippets were removed or fenced.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r5a-stale-docs-ci-cd-authority-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r5a-stale-docs-ci-cd-authority-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `5840ms`, mobile `4628ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Behavior parity statement:

- No runtime source code, schema, migration, product route, API endpoint,
  provider adapter, exposure lifecycle, task/timer behavior, Redis state, or
  user-facing surface changed.
- This pass changes documentation authority and CI/CD process expectations
  only.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28559696002`.
- Head SHA:
  `a9aa73cbc62b7380dc4b019b573532ae23b07b9f`.
- Structured proof:
  `tmp/ci-cd-proof/r5a-stale-authority-a9aa73c.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the docs cleanup commit only. This restores previous document wording
  without touching runtime code, schemas, production data, exposure lifecycle
  rows, provider rows, Redis queues, export/delete behavior, or user content.

## R3 - Table Range Query-Key Factory

Changed authority:

- No product, task, timer, exposure, provider, schema, readiness, or mutation
  authority changed.
- Table's read-only `tasks-range` React Query key now goes through
  `queryKeys.tasksRangeWindow(dateFrom, dateTo)` instead of an inline array.
- The Table page still owns audit/history presentation and still calls the same
  `queryTasksRange(dateFrom, dateTo)` transport function.

Removed paths:

- Removed one route-local raw query-key literal from the Table page.

Parked paths:

- NewTaskModal draft/nudge/deadline/submit extraction remains parked until the
  modal's exposure and rapid-submit behavior is characterized further.
- Stopwatch controller extraction remains parked because it still touches
  optimistic updates, rollback, pause state, and active timer authority.
- Shared brain-dump reducer remains parked until first-run onboarding browser
  coverage is promoted.

Moved authority:

- No command ownership moved. This is a cache-key vocabulary seam only.

Agent loop notes:

- Frontend explorer found the safest R3 continuation was a read-only query-key
  factory adoption, not a controller or reducer extraction.
- Backend explorer identified a later R4 candidate:
  `operator_dashboard_metrics.activity_frequency_snapshot`; it was deferred
  because v5 sequence keeps remaining frontend extraction before backend
  extraction.
- Verification explorer confirmed lint is not a hard gate until issue #153 is
  resolved, and local-current alternate ports remain non-blocking when labeled
  under issue #147.

Tests and verification:

- Typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && npm run build:public` passed.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Table route browser proof:
  operator-cookie local-current Table smoke passed after installing the same
  API proxy pattern used by the operator verifier.
- Table artifact:
  `tmp/browser-readonly/r3-table-query-key-window-operator-table-local-current/result.json`.
- Table outcome:
  `/table` returned `200`, final URL remained `/table`, export/task markers
  rendered, no onboarding redirect occurred, there were no console/page errors,
  and export counts were unchanged.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-table-query-key-window-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r3-table-query-key-window-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6103ms`, mobile `5070ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Verifier bug classifications:

- First Table smoke failed with HTTP `500` because the local-current Next dev
  server on port `3013` was stale/corrupted after `npm run build:public`. This
  matches known issue #144. The verifier server was restarted; no product code
  change was needed.
- Second Table smoke reached `/table` but was CORS-blocked because the ad hoc
  smoke lacked the operator verifier's API proxy. The final proxied smoke
  passed.
- Holmesberg was not used for this read-only proof because that account is
  still in onboarding; using it would have tested onboarding instead of Table
  without an intentional mutable setup.

Behavior parity statement:

- The query key values are unchanged: `["tasks-range", dateFrom, dateTo]`.
- Table fetches the same API range and renders the same audit/history surface.
- No user data, task state, timer state, exposure row, notification row,
  provider row, Redis key, or schema changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28560259913`.
- Head SHA:
  `2f62d3f923842bf92f1f3b29bd58be4aa5e208f6`.
- Structured proof:
  `tmp/ci-cd-proof/r3-table-query-key-2f62d3f.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the Table query-key commit only. This restores the route-local raw
  query-key literal without touching schemas, production data, exposure
  lifecycle rows, provider rows, Redis queues, export/delete behavior, or user
  content.

## R3 - Calendar And Pulse Range Query-Key Factory

Changed authority:

- No product, task, timer, exposure, provider, schema, readiness, or mutation
  authority changed.
- Calendar and Pulse read-only `tasks-range` React Query keys now go through
  `queryKeys.tasksRangeWindow(dateFrom, dateTo)` instead of route-local inline
  arrays.
- Calendar still owns schedule placement and still calls the same
  `queryTasksRange(visibleRange.from, visibleRange.to)` transport function.
- Pulse still owns the hub surface and still calls the same
  `queryTasksRange(fortnightStart, today)` transport function.

Removed paths:

- Removed two route-local raw `tasks-range` query-key literals from Calendar
  and Pulse.

Parked paths:

- Pulse route browser proof remains parked for read-only classification because
  route load may legitimately acknowledge pressure-map exposure render truth
  via `ackExposureRender(pressureQ.data?.exposure_id)`.
- NewTaskModal draft/nudge/deadline/submit extraction remains parked until the
  modal's exposure and rapid-submit behavior is characterized further.
- Stopwatch controller extraction remains parked because it still touches
  optimistic updates, rollback, pause state, and active timer authority.
- Shared brain-dump reducer remains parked until first-run onboarding browser
  coverage is promoted.

Moved authority:

- No command ownership moved. This is a cache-key vocabulary seam only.

Agent loop notes:

- Mini-loop verifier confirmed the key factory preserves the exact key shape:
  `["tasks-range", dateFrom, dateTo]`.
- Mini-loop verifier approved Calendar as a read-only route smoke target when
  no drag/resize/edit action is performed.
- Mini-loop verifier warned not to count Pulse as read-only browser proof
  without explicit exposure-state snapshotting, because Pulse load may create a
  valid exposure-render acknowledgement.

Tests and verification:

- Typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && npm run build:public` passed.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed with only Windows CRLF conversion warnings.
- Calendar route browser proof:
  operator-cookie local-current Calendar smoke passed after installing the same
  API proxy pattern used by the operator verifier.
- Calendar artifact:
  `tmp/browser-readonly/r3-calendar-pulse-range-query-key-calendar-local-current-proxy/result.json`.
- Calendar outcome:
  `/calendar` returned `200`, final URL remained `/calendar`, no onboarding
  redirect occurred, there were no console/page errors, and export counts were
  unchanged.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-calendar-pulse-range-query-key-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r3-calendar-pulse-range-query-key-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `11430ms`, mobile `4716ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Verifier bug classifications:

- First Calendar smoke failed with HTTP `500` at `/api/topology` because the
  local-current Next dev server on port `3013` was stale/corrupted after
  `npm run build:public`. This matches known issue #144. The verifier server
  was restarted; no product code change was needed.
- Second Calendar smoke loaded `/calendar` but browser-side API calls were
  CORS-blocked because the ad hoc smoke lacked the operator verifier's API
  proxy. The final proxied smoke passed.
- Holmesberg was not used for this read-only proof because no mutable
  user-facing behavior changed and synthetic-row cleanup proof would be
  unnecessary risk for a cache-key vocabulary seam.

Behavior parity statement:

- The query key values are unchanged:
  `["tasks-range", visibleRange.from, visibleRange.to]` and
  `["tasks-range", fortnightStart, today]`.
- Calendar and Pulse fetch the same API ranges and render the same surfaces.
- No user data, task state, timer state, exposure row, notification row,
  provider row, Redis key, or schema changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28560745855`.
- Head SHA:
  `3c2fb92746f98e264c9089f384f9562203062777`.
- Structured proof:
  `tmp/ci-cd-proof/r3-calendar-pulse-range-query-key-3c2fb92.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the Calendar/Pulse query-key commit only. This restores the
  route-local raw query-key literals without touching schemas, production data,
  exposure lifecycle rows, provider rows, Redis queues, export/delete behavior,
  or user content.

## R3 - Deadline Binding Query-Key Factory

Changed authority:

- No product, task, timer, exposure, provider, schema, readiness, or mutation
  authority changed.
- Deadline binding read queries now go through named `queryKeys` entries
  instead of route/component-local inline arrays.
- `DeadlinePickerSlot` still owns the NewTaskModal deadline-picker presentation
  and still calls the same `listDeadlines()` transport function.
- `DeadlineBindingDialog` still owns metadata-correction presentation and
  still calls the same `listDeadlines()` transport function when opened.

Removed paths:

- Removed the route-local raw `["deadlines", "bindable"]` query key from the
  NewTaskModal deadline picker slot.
- Removed the route-local raw `["deadlines", "binding-correction"]` query key
  from the deadline binding correction dialog.

Parked paths:

- NewTaskModal creation-nudge/helper extraction remains parked for a separate
  seam. It was temporarily stashed while this proof ran so this commit could
  be verified in isolation.
- Actual task/deadline binding mutation remains untouched.
- Table correction/export and Calendar drag/resize remain separate targeted
  verification surfaces.

Moved authority:

- No command ownership moved. This is a cache-key vocabulary seam only.

Agent loop notes:

- Frontend scout recommended this as the safest next R3 continuation because
  it touches deadline-linkage vocabulary without moving NewTaskModal state,
  deadline authority, parser preview logic, or submit behavior.
- Verification scout required local hard gates, targeted browser proof,
  operator read-only proof, CI/CD proof, and a ledger entry.

Tests and verification:

- Typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed
  with the local dev server stopped.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Whitespace:
  `git diff --check` passed.
- Targeted deadline browser proof:
  operator-cookie local-current `/today` proof opened the New Task modal,
  opened the deadline picker, and did not select or save anything.
- Targeted artifact:
  `tmp/browser-readonly/r3-deadline-binding-query-key-surfaces-local-current/result.json`.
- Targeted outcome:
  `/today` returned `200`, the deadline picker opened, export counts were
  unchanged, and no page errors occurred. The current account had zero visible
  picker options and no visible task binding buttons on `/today`, so the
  correction dialog subproof was gated rather than forced.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-deadline-binding-query-key-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r3-deadline-binding-query-key-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  desktop `6006ms`, mobile `4534ms`, `implementation_green=true`,
  `implementation_blockers=[]`, `exposure_without_render_count=0`, and cohort
  status remains yellow only for real-data gaps.

Verifier bug classifications:

- `npm run build:public` failed twice while the local dev server was running or
  stale, after successful compilation, with missing `.next` page/runtime
  artifacts. This matches known issue #144. Stopping the dev server and
  cleaning `.next` produced a passing build; no product code change was needed.
- The unrelated NewTaskModal helper extraction was already dirty in the
  workspace. It was stashed with `--keep-index` before the exact seam proof,
  then restored after the code commit. It was not part of this commit or CI
  proof.

Behavior parity statement:

- The query key values are unchanged:
  `["deadlines", "bindable"]` and
  `["deadlines", "binding-correction"]`.
- Deadline picker and binding correction surfaces fetch the same deadline list
  data as before.
- No user data, task state, timer state, exposure row, notification row,
  provider row, Redis key, or schema changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28561468761`.
- Head SHA:
  `311e2db9335c5c47a8cf8416ef5a727ef77a40b5`.
- Structured proof:
  `tmp/ci-cd-proof/r3-deadline-binding-query-key-311e2db.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the deadline binding query-key commit only. This restores the
  component-local raw query-key literals without touching schemas, production
  data, exposure lifecycle rows, provider rows, Redis queues, export/delete
  behavior, task/deadline binding mutation, or user content.

## R3 - Creation Nudge Dogfood Rule 11 Gate

Changed authority:

- No product, task, timer, exposure, provider, schema, readiness, or mutation
  authority changed.
- The Holmesberg product-loop verifier now records bias-factor lookup
  requests/responses and classifies `rule11_no_nudge_control_day` as a gated
  branch instead of a failed task-creation nudge render.
- The verifier now uses a per-run custom category for nudge branches so it does
  not rely on Holmesberg's current category defaults or personal-history cells.

Removed paths:

- Removed the verifier's implicit assumption that a visible New Task modal must
  render `task.creation_nudge` for every nudge-eligible-looking task.

Parked paths:

- Browser proof of the `task.creation_nudge` Use branch remains gated whenever
  the account is assigned to Rule 11 no-nudge control. Backend tests continue
  to prove the emission/render-ack contract for renderable nudge decisions.

Moved authority:

- No authority moved. This is verifier classification only.

Issue record:

- GitHub issue #159 tracked the verifier bug and was closed as resolved by
  commit `d38cb32`.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Script syntax:
  `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs` passed.
- Holmesberg product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api true --run-id r3-creation-nudge-harness-rule11-gate --out-dir tmp\browser-product-loop\r3-creation-nudge-harness-rule11-gate`
  passed.
- Holmesberg artifact:
  `tmp/browser-product-loop/r3-creation-nudge-harness-rule11-gate/result.json`.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-creation-nudge-harness-rule11-gate-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r3-creation-nudge-harness-rule11-gate-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- Product runtime behavior is unchanged.
- `task.creation_nudge` remains suppressed under Rule 11 no-nudge control.
- Browser screenshots explain the modal state, but the canonical proof is the
  captured backend bias lookup response with
  `suppressed_reason=rule11_no_nudge_control_day`.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28805318994`.
- Head SHA:
  `d38cb32bb89da0c3db0ee9bb4ea1b1b5663f2d66`.
- Structured proof:
  `tmp/ci-cd-proof/r3-creation-nudge-harness-rule11-d38cb32.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the verifier commit only. This restores the prior hard-fail behavior
  in the dogfood harness without touching schemas, production data, exposure
  lifecycle rows, provider rows, Redis queues, export/delete behavior, or user
  content.

## R3 - Creation Nudge Helper Extraction

Changed authority:

- No product, task, timer, exposure, provider, schema, readiness, or mutation
  authority changed.
- Pure creation-nudge value helpers moved from `NewTaskModal` to
  `frontend/lib/creation-nudge.ts`.
- Creation-nudge render acknowledgement, suppression acknowledgement,
  exposure-id TTL handling, decision state, and modal lifecycle authority remain
  in `NewTaskModal`.

Removed paths:

- Removed inline research-prior constants from `NewTaskModal`.
- Removed inline `NudgeDecisionData`, `NudgeDecisionPayload`,
  `nudgePayloadFromDecision`, `nudgeDecisionFromCalibration`, and
  `localResearchNudge` definitions from `NewTaskModal`.

Parked paths:

- Deeper NewTaskModal state extraction remains parked for later R3 seams.
- Browser proof of the `task.creation_nudge` Use branch remains gated while
  Holmesberg is in Rule 11 no-nudge control.
- Pressure-map recovery mutation, provider credential mutation, hard delete /
  Redis purge, Calendar drag/resize, and OpenClaw pending-drain authority
  remain gated in the reusable product loop.

Moved authority:

- No authority moved. Only pure value construction moved.
- `frontend/lib/creation-nudge.ts` is explicitly documented as pure helper
  code, not exposure/render/suppression authority.

Agent loop notes:

- The frontend scout found the extraction behavior-preserving as long as the
  new helper file is committed with the component.
- The verification scout required backend nudge tests, production build,
  Holmesberg mutable product-loop proof, operator read-only proof, cleanup
  proof, CI/CD proof, and a ledger entry.
- The verifier loop discovered and fixed the Rule 11 no-nudge harness bug
  before accepting the helper extraction proof.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Backend targeted tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest -q tests\test_calibration_nudge_event.py tests\test_output_surfaces.py -k "creation_nudge or nudge_decision or task_creation_nudge"`
  passed with 9 selected tests.
- Frontend typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed
  with the local dev server stopped.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Holmesberg product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api true --run-id r3-creation-nudge-helper-extraction --out-dir tmp\browser-product-loop\r3-creation-nudge-helper-extraction`
  passed.
- Holmesberg artifact:
  `tmp/browser-product-loop/r3-creation-nudge-helper-extraction/result.json`.
- Holmesberg outcome:
  task creation, explicit deadline binding, overlap conflict, nudge Keep branch,
  no-deadline branch, custom category branch, edit branch, terminal deadline
  rejection, brain dump parse/commit/partial/retry/double-submit, pressure map
  read, timer start/pause/resume/stop/navigation persistence, notification
  lifecycle, export evidence, operator privacy scan, and cleanup all passed.
- Creation-nudge Use branch:
  gated by Rule 11 no-nudge control with backend bias lookup responses recorded
  in the product-loop artifact.
- Cleanup proof:
  the product loop ended with no active Holmesberg timer and no unrendered
  synthetic creation-nudge exposures.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api --expect-readiness-split --run-id r3-creation-nudge-helper-extraction-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r3-creation-nudge-helper-extraction-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, and cohort status remains yellow only for
  real-data gaps.

Behavior parity statement:

- The task creation modal builds the same nudge payload fields as before.
- Research-prior suggested minutes use the same category prior table and
  `roundTo5` calculation as before.
- Accept/dismiss decisions still travel through the same create-task payload.
- No user data, task state, timer state, exposure row, notification row,
  provider row, Redis key, or schema changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28805996755`.
- Head SHA:
  `1b04bc91146ff61544b2b0caa13bd9ce39ed2124`.
- Structured proof:
  `tmp/ci-cd-proof/r3-creation-nudge-helper-1b04bc9.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert the creation-nudge helper extraction commit only. This restores the
  inline helper constants/functions in `NewTaskModal` without touching schemas,
  production data, exposure lifecycle rows, provider rows, Redis queues,
  export/delete behavior, task/deadline binding mutation, or user content.

## R3 - New Task Time Recovery Helper Extraction

Changed authority:

- No product, task, timer, exposure, provider, schema, readiness, or mutation
  authority changed.
- Pure local-time recovery math moved from `NewTaskModal` to
  `frontend/lib/task-time.ts`.
- `NewTaskModal` still owns modal state, render behavior, user actions,
  submit/edit/interruption flow, creation-nudge exposure lifecycle calls, and
  task mutation authority.

Removed paths:

- Removed inline AM/PM swap suggestion calculation from `NewTaskModal`.
- Removed inline past-start push-forward calculation from `NewTaskModal`.

Parked paths:

- Deeper NewTaskModal draft-state extraction remains parked for later R3 seams.
- Calendar drag/resize mutation remains gated as a separate browser-specific
  pass.
- Provider credential mutation, account hard-delete / Redis purge, OpenClaw
  pending-drain authority, and pressure-map recovery mutation remain gated in
  the reusable Holmesberg product loop.

Moved authority:

- No authority moved. `frontend/lib/task-time.ts` now owns only pure time
  formatting/arithmetic helpers.
- Browser render, exposure render/suppression acknowledgement, task creation,
  and edit mutation authority did not move.

Agent loop notes:

- The frontend scout recommended this as the next behavior-preserving
  NewTaskModal seam: extract `suggestAmPmSwap` and
  `suggestPushStartToFuture` while preserving `new Date(datetime-local)`
  parsing, same-day checks, strict negative bounds, and exact five-minute push
  behavior.
- The CI/CD scout required exact-head CI proof after commit/push and recommended
  a follow-up runbook seam for full-SHA proof commands.
- A verifier pass found two proof-contract issues: the targeted probe needed
  the standard API proxy for local-current browser proof, and opening
  NewTaskModal legitimately creates `task.creation_nudge` exposure decision /
  suppression lifecycle rows. The proof now treats screenshots as context and
  backend/export row classes as canonical evidence.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed
  with the local dev server stopped.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py` passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with no missing owners and no worker write drift.
- Targeted Holmesberg modal proof:
  `tmp/browser-readonly/r3-new-task-time-recovery-local-current/result.json`.
- Targeted proof outcome:
  Today rendered through local-current proxy; New Task modal opened; push-start
  and AM/PM swap suggestions rendered and were clickable; canceling the modal
  changed no product-row counts. The only count changes were expected
  `task.creation_nudge` exposure-decision and suppression lifecycle rows.
- Holmesberg product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api true --run-id r3-new-task-time-recovery --out-dir tmp\browser-product-loop\r3-new-task-time-recovery`
  passed.
- Holmesberg artifact:
  `tmp/browser-product-loop/r3-new-task-time-recovery/result.json`.
- Holmesberg outcome:
  route rendering, task creation, explicit deadline binding, overlap conflict,
  creation-nudge Keep branch, no-deadline branch, custom category branch,
  terminal deadline rejection, brain dump parse/commit/partial/retry/
  double-submit, pressure-map read, timer start/pause/resume/stop/navigation
  persistence, notification lifecycle, export evidence, operator privacy scan,
  and cleanup all passed.
- Cleanup proof:
  the product loop ended with no active Holmesberg timer and no unrendered
  synthetic creation-nudge exposures.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api true --expect-readiness-split --run-id r3-new-task-time-recovery-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r3-new-task-time-recovery-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, and cohort status remains yellow only for
  real-data gaps.

Behavior parity statement:

- AM/PM swap suggestion behavior remains same-day only, rejects invalid dates,
  rejects zero/positive deltas, rejects deltas at or beyond twelve hours, and
  only suggests when the shifted end is strictly after start.
- Past-start push behavior still rounds up to the next five-minute mark and
  advances by five minutes when `now` is already exactly on a five-minute mark.
- No schema, API payload, task mutation, timer mutation, deadline binding,
  exposure lifecycle contract, notification lifecycle contract, provider truth,
  Redis key, or user-data export shape changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28807559399`.
- Head SHA:
  `0e45c33cc87d5a585cc07979588fa821ebbdac74`.
- Structured proof:
  `tmp/ci-cd-proof/r3-new-task-time-recovery-0e45c33.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.
- CI/CD documentation issue:
  issue #160 tracks the proof-collector footgun where short SHAs fail exact-head
  matching; post-wave docs should show full `git rev-parse HEAD` usage.

Rollback note:

- Revert commit `0e45c33` only. This restores the inline time-recovery
  suggestion calculations in `NewTaskModal` without touching schemas,
  production data, exposure lifecycle rows, provider rows, Redis queues,
  export/delete behavior, task/deadline binding mutation, or user content.

## CI/CD - Full-SHA Proof Runbook Clarification

Changed authority:

- No runtime, product, task, timer, exposure, provider, schema, readiness, or
  mutation authority changed.
- Post-wave CI/CD proof documentation now explicitly requires the full
  `git rev-parse HEAD` value for `collect_github_ci_cd_proof.ps1 -HeadSha`.

Removed paths:

- Removed ambiguity that allowed a seven-character display SHA to be treated as
  an acceptable exact-head proof input.

Parked paths:

- Automatic branch CI trigger policy remains parked under issue #157.
- GitHub Actions Node 20 deprecation maintenance remains parked under issue
  #155.
- Collector normalization of unique short SHAs remains optional future
  hardening; the active runbook now uses full SHAs.

Moved authority:

- No authority moved. The runbook and `.github/instructions.md` now encode the
  CI/CD proof convention; the workflow and collector behavior did not change.

Discovery / issue link:

- Issue #160 was opened after an exact-head proof was first attempted with
  `-HeadSha 0e45c33`. The collector correctly produced
  `no_matching_run_for_head` because GitHub Actions reports the full head SHA.
- Rerunning with `0e45c33cc87d5a585cc07979588fa821ebbdac74` produced a green
  exact-head proof. The runbook now prevents this false proof failure.

Tests and verification:

- Whitespace:
  `git diff --check -- docs\runbooks\post_wave_dogfood_loop.md .github\instructions.md`
  passed.
- Script parse smoke:
  `powershell -NoProfile -ExecutionPolicy Bypass -Command '$null = [scriptblock]::Create((Get-Content .\scripts\run_post_wave_dogfood_loop.ps1 -Raw)); $null = [scriptblock]::Create((Get-Content .\scripts\collect_github_ci_cd_proof.ps1 -Raw)); Write-Output parsed'`
  passed.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api true --expect-readiness-split --run-id ci-cd-full-sha-runbook-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-ci-cd-full-sha-runbook-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No app runtime behavior changed.
- CI/CD proof remains a read-only post-push evidence artifact. It does not
  replace browser dogfood proof, operator invariants, local-current proof, or
  hosted-public proof.

Rollback note:

- Revert the runbook/instructions commit only. This restores the prior CI/CD
  documentation without touching workflows, scripts, schemas, production data,
  exposure lifecycle rows, provider rows, Redis queues, or user content.

## R3 - Pulse Pressure/Evidence Query-Key Factory

Changed authority:

- No product, task, timer, exposure, provider, schema, readiness, or mutation
  authority changed.
- Pulse now uses shared query-key factories for the task-evidence window and
  academic pressure-map horizon.
- Pulse still owns pressure-horizon UI state and still acknowledges pressure
  exposure renders through the existing `ackExposureRender` effect.

Removed paths:

- Removed two remaining inline Pulse query-key literals:
  `["tasks-evidence", taskEvidenceStart, taskEvidenceEnd]` and
  `["pressure-map", pressureHorizonDays]`.

Parked paths:

- Pressure-map planning/helper extraction remains parked.
- Real pressure-map recovery-option browser proof remains gated by pressure
  safe mode.
- Calendar drag/resize mutation, provider credential mutation, account
  hard-delete / Redis purge, and OpenClaw pending-drain authority remain gated
  in the reusable Holmesberg product loop.

Moved authority:

- No authority moved. `frontend/lib/query-keys.ts` now names the exact same
  cache-key shapes; it does not own fetch semantics, exposure semantics,
  invalidation authority, pressure-map computation, or recovery mutation.

Agent loop notes:

- Frontend, authority, and verification scouts agreed this was the lowest-risk
  remaining R3 seam because it preserves exact key shapes and avoids moving
  exposure render, pressure computation, planning commit behavior, or command
  invalidation.
- A verifier/runtime issue was observed while restarting WSL frontend with
  `-NoBuild` after a Windows-side build: the WSL process attempted to serve an
  incompatible `.next` artifact and returned 500s for missing Turbopack runtime
  chunks. This was classified as a topology/verifier bug, not a product
  regression, and recorded on issue #144.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors`
  passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with no missing owners and no worker write drift.
- Holmesberg product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api true --run-id r3-pulse-pressure-evidence-query-key --out-dir tmp\browser-product-loop\r3-pulse-pressure-evidence-query-key`
  passed.
- Holmesberg artifact:
  `tmp/browser-product-loop/r3-pulse-pressure-evidence-query-key/result.json`.
- Holmesberg outcome:
  route rendering, task creation, explicit deadline binding, overlap conflict,
  creation-nudge Keep branch, no-deadline branch, custom category branch,
  terminal deadline rejection, brain dump parse/commit/partial/retry/
  double-submit, pressure-map read, timer start/pause/resume/stop/navigation
  persistence, notification lifecycle, export evidence, operator privacy scan,
  and cleanup all passed.
- Cleanup proof:
  the product loop ended with no active Holmesberg timer and no unrendered
  synthetic creation-nudge exposures.
- Targeted Pulse horizon proof:
  `tmp/browser-readonly/r3-pulse-pressure-evidence-query-key-horizons/result.json`.
- Targeted Pulse outcome:
  pressure-map horizons `14`, `1`, and `7` were requested through the browser;
  every response returned status 200 with pressure exposure metadata; product
  row counts did not change. The only count changes were expected pressure
  exposure lifecycle rows: three decisions, three renders, and three render
  acknowledgements.
- Operator-cookie browser proof:
  `node scripts\browser_stress_operator_readonly.mjs --frontend http://localhost:3013 --api http://localhost:8000 --proxy-api true --expect-readiness-split --run-id r3-pulse-pressure-evidence-query-key-operator-local-current`
  passed.
- Operator artifact:
  `tmp/operator-readonly-stress-r3-pulse-pressure-evidence-query-key-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, and cohort status remains yellow only for
  real-data gaps.

Behavior parity statement:

- The query-key array values are unchanged:
  `["tasks-evidence", dateFrom, dateTo]` and `["pressure-map", horizonDays]`.
- Existing broad invalidation keys, including `queryKeys.tasksEvidence` and
  `queryKeys.pressureMap`, remain unchanged.
- Pulse still fetches the same task-evidence date window, same pressure-map
  horizon values, same deadlines/integrations/user data, and same exposure
  render acknowledgement path.
- No schema, API payload, task mutation, timer mutation, deadline binding,
  exposure lifecycle contract, notification lifecycle contract, provider truth,
  Redis key, or user-data export shape changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28809717950`.
- Head SHA:
  `233ced447aadebd8e77d0e8df23f3a5c1be9857b`.
- Structured proof:
  `tmp/ci-cd-proof/r3-pulse-query-key-233ced4.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.
- Non-blocking CI maintenance warning:
  GitHub Actions Node 20 deprecation warning is tracked as issue #155.

Rollback note:

- Revert commit `233ced4` only. This restores the two inline Pulse query-key
  literals without touching schemas, production data, exposure lifecycle rows,
  provider rows, Redis queues, export/delete behavior, task/deadline binding
  mutation, or user content.

## R3 - Pressure Horizon Display Helper Extraction

Commit: `8046bb5` (`frontend: extract pressure horizon display helpers`).

Changed authority:

- No pressure-map computation, exposure lifecycle, query-key, recovery-plan,
  task-creation, provider, timer, or claim authority changed.
- `frontend/lib/pressure-map-ui.ts` now owns the pressure-map horizon display
  vocabulary: the horizon option list, horizon labels, and selected/unselected
  button class strings.

Removed paths:

- Removed the inline `[1, 7, 14]` horizon option array from
  `PulseAcademicPressureMap`.
- Removed inline horizon label ternaries and horizon button class construction
  from `PulseAcademicPressureMap`.

Parked paths:

- Pressure-map planning, recovery commit behavior, exposure render
  acknowledgement, evidence estimates, deadline linkage, and cache invalidation
  remain parked for separately characterized seams.
- Real pressure-map recovery-option mutation proof remains gated by pressure
  safe mode.
- Calendar drag/resize mutation, provider credential mutation, account
  hard-delete / Redis purge, and OpenClaw pending-drain authority remain gated
  in the reusable Holmesberg product loop.

Moved authority:

- No product authority moved. The extracted helpers own display vocabulary
  only. They do not own pressure-map API reads, exposure semantics, task
  mutation, pressure computation, evidence estimation, cache invalidation,
  ClaimCompiler authority, or user-facing behavioral claims.

Agent loop notes:

- Frontend and verification scouts treated this as a narrow R3 seam because it
  removes another inline UI branch without touching fetches, effects, mutation
  payloads, or exposure acknowledgement.
- The first targeted browser proof produced an `ok:true` result but exited
  non-zero because Playwright route cleanup raced after context close. This was
  classified as a verifier cleanup bug, not a product bug. The proof was rerun
  with tolerant route cleanup and passed. Screenshots remain contextual only;
  backend counts, route responses, and operator invariants are the proof.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors`
  passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with no missing owners and no worker write drift.
- Targeted Pulse horizon proof:
  `tmp/browser-readonly/r3-pressure-map-display-helpers-horizons/result.json`.
- Targeted Pulse outcome:
  pressure-map horizons `14`, `1`, and `7` were requested through the browser;
  labels `day`, `week`, and `14d` were observed; every response returned status
  200 with pressure exposure metadata; product row counts did not change. The
  only count changes were expected pressure exposure lifecycle rows: three
  decisions, three renders, and three render acknowledgements.
- Operator-cookie browser proof:
  `tmp/operator-readonly-stress-r3-pressure-map-display-helpers-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, and cohort status remains yellow only for
  real-data gaps.

Behavior parity statement:

- The horizon option values are unchanged: `1`, `7`, and `14`.
- The visible labels are unchanged: `day`, `week`, and `14d`.
- The selected and unselected button class strings are unchanged.
- Pulse still fetches the same pressure-map horizons, receives the same
  pressure exposure metadata, and acknowledges pressure exposure renders through
  the existing effect.
- No schema, API payload, task mutation, timer mutation, deadline binding,
  exposure lifecycle contract, notification lifecycle contract, provider truth,
  Redis key, or user-data export shape changed.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28810337122`.
- Head SHA:
  `8046bb563452a94cc0f9c1b8737c51304bcd1af9`.
- Structured proof:
  `tmp/ci-cd-proof/r3-pressure-map-display-8046bb5.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.

Rollback note:

- Revert commit `8046bb5` only. This restores the inline horizon option array,
  label ternaries, and class construction in `PulseAcademicPressureMap` without
  touching schemas, production data, exposure lifecycle rows, provider rows,
  Redis queues, export/delete behavior, task/deadline binding mutation, or user
  content.

## R3 - Deadline And Integration Query-Key Vocabulary

Commit: `8ff0f44` (`frontend: name deadline integration query keys`).

Changed authority:

- No task, deadline, provider, exposure, timer, notification, Redis, schema,
  export/delete, or ClaimCompiler authority changed.
- `frontend/lib/query-keys.ts` now names exact existing cache-key tuples for
  integrations and the all-deadlines query.
- Deadline and integration surfaces now import those names instead of spelling
  raw arrays inline.

Removed paths:

- Removed raw `["integrations"]` query/invalidation keys from
  `IntegrationsSection`.
- Removed raw `["deadlines"]` query/invalidation keys from touched
  Today, Calendar, Pulse, Deadlines, and Integrations surfaces.
- Removed raw `["deadlines", "all"]` from the Deadlines page query.

Parked paths:

- Task-day query-key adoption remains parked for a separate seam because Today
  uses `["tasks", viewedDate]` in optimistic execution rollback paths.
- Domain-wide invalidation helpers remain parked until every dependent cache is
  named and characterized.
- Stopwatch controller hooks, NewTaskModal submit/draft extraction, shared
  brain-dump reducer extraction, pressure-map planning mutation, provider
  credential mutation, calendar drag/resize mutation, account hard-delete /
  Redis purge, and OpenClaw pending-drain authority remain gated.

Moved authority:

- No product authority moved. The query-key module names cache keys only and
  does not authorize provider sync, deadline mutation, task mutation, exposure
  lifecycle truth, notification lifecycle truth, clean-data filtering, claim
  authority, or adaptive behavior.

Agent loop notes:

- Frontend and verification scouts agreed that query-key vocabulary adoption is
  among the lowest-risk remaining R3 seams, provided exact tuple values are
  preserved and Today's optimistic task execution keys are left for a separate
  proof seam.
- A fresh scout recommended `tasksDay(date)` next. That recommendation was not
  folded into this seam because it touches Today optimistic execution rollback
  and deserves mutable proof as its own commit.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors`
  passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with no missing owners and no worker write drift.
- Holmesberg product-loop proof:
  `tmp/browser-product-loop/r3-deadline-integration-query-keys/result.json`.
- Holmesberg outcome:
  route rendering, settings/integrations rendering, deadline creation and
  cleanup, explicit deadline binding, overlap conflict, creation-nudge Keep
  branch, no-deadline branch, custom category branch, terminal deadline
  rejection, brain dump parse/commit/partial/retry/double-submit, pressure-map
  read, timer start/pause/resume/stop/navigation persistence, notification
  lifecycle, export evidence, operator privacy scan, and cleanup all passed.
- Cleanup proof:
  the product loop ended with no active Holmesberg timer and no unrendered
  synthetic creation-nudge exposures.
- Operator-cookie browser proof:
  `tmp/operator-readonly-stress-r3-deadline-integration-query-keys-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, and cohort status remains yellow only for
  real-data gaps.

Behavior parity statement:

- `queryKeys.integrations` is exactly `["integrations"]`.
- `queryKeys.deadlines` remains exactly `["deadlines"]`.
- `queryKeys.deadlinesAll` is exactly `["deadlines", "all"]`.
- Query functions, mutation calls, invalidation targets, provider sync
  behavior, deadline creation/edit/void behavior, Today/Calendar/Pulse render
  behavior, and settings integration behavior are unchanged.
- No broad invalidation set was added or removed. Existing predicate
  invalidations for calendar events and deadline-prefixed keys remain unchanged.
- No schema, API payload, task mutation, timer mutation, deadline binding,
  exposure lifecycle contract, notification lifecycle contract, provider truth,
  Redis key, or user-data export shape changed.

Verifier and issue notes:

- The product loop again observed that the deadline suggestion chip did not
  render and used the explicit picker fallback. This is already tracked as
  issue `#149`; this run was added as a comment:
  `https://github.com/Holmesberg/lyra-secretary/issues/149#issuecomment-4895919388`.
- The product loop also recorded expected/gated states: Holmesberg onboarding
  gate skip, Rule 11 creation-nudge suppression, pressure-map recovery safe
  mode, provider credential mutation gate, account delete/purge gate, calendar
  drag/resize manual gate, and OpenClaw pending-drain authority gate.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28811509816`.
- Head SHA:
  `8ff0f44148184697018f39d1648aea83d2c8d66c`.
- Structured proof:
  `tmp/ci-cd-proof/r3-deadline-integration-query-keys-8ff0f44.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.

Rollback note:

- Revert commit `8ff0f44` only. This restores the raw deadline/integration
  cache-key arrays in the touched frontend surfaces without touching schemas,
  production data, exposure lifecycle rows, provider rows, Redis queues,
  export/delete behavior, task/deadline binding mutation, or user content.

## R3 - Task Day Query-Key Factory

Commit: `e86f2af` (`frontend: add task day query key factory`).

Changed authority:

- No task, timer, deadline, provider, exposure, notification, Redis, schema,
  export/delete, ClaimCompiler, or clean-data authority changed.
- `frontend/lib/query-keys.ts` now names the exact existing task-day cache-key
  tuple as `queryKeys.tasksDay(date)`.
- Today and Pulse now import that named tuple instead of spelling raw task-day
  arrays inline.

Removed paths:

- Removed raw `["tasks", viewedDate]` from Today task reads, optimistic cache
  writes, query cancellation, previous-data snapshots, rollback writes, and
  invalidation paths.
- Removed raw `["tasks", nextDate]` from Today command-surface invalidation.
- Removed raw `["tasks", today]` from the Pulse today-task read.

Parked paths:

- Domain-wide invalidation helpers remain parked until every dependent cache is
  named and characterized.
- Stopwatch controller hooks, NewTaskModal submit/draft extraction, shared
  brain-dump reducer extraction, pressure-map planning mutation, provider
  credential mutation, calendar drag/resize mutation, account hard-delete /
  Redis purge, and OpenClaw pending-drain authority remain gated.
- Notification host/verifier timing behavior is tracked separately as issue
  `#161`; it was observed during the first mutable proof attempt and was not
  changed in this seam.

Moved authority:

- No product authority moved. The query-key module names cache keys only.
- Today still owns execution UI behavior.
- Stopwatch/backend execution services still own execution truth.
- The backend remains the source of task, timer, deadline, exposure, provider,
  and export/delete truth.

Agent loop notes:

- A fresh frontend scout recommended `tasksDay(date)` as the next lowest-risk
  query-key seam after deadline/integration vocabulary.
- The scout classified the seam as sensitive enough to deserve its own mutable
  Holmesberg proof because Today uses the tuple for optimistic execution
  rollback, not only passive reads.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed.
- Refactor contract scan:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors`
  passed.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with no missing owners and no worker write drift.
- First Holmesberg product-loop proof:
  `tmp/browser-product-loop/r3-task-day-query-key/result.json`.
- First product-loop classification:
  task creation, task-day cache behavior, timer behavior, and cleanup were not
  implicated; the run failed on notification render lifecycle timing. Pending
  notification follow-up showed `count=0`, so this was classified as a
  notification host/verifier timing bug and recorded as issue `#161`.
- Passing Holmesberg product-loop proof:
  `tmp/browser-product-loop/r3-task-day-query-key-rerun/result.json`.
- Passing Holmesberg outcome:
  route rendering, settings/integrations rendering, deadline creation and
  cleanup, explicit deadline binding, overlap conflict, creation-nudge Keep
  branch, no-deadline branch, custom category branch, terminal deadline
  rejection, brain dump parse/commit/partial/retry/double-submit, pressure-map
  read, timer start/pause/resume/stop/navigation persistence, notification
  lifecycle, export evidence, operator privacy scan, and cleanup all passed.
- Cleanup proof:
  the passing product loop ended with no active Holmesberg timer and no
  unrendered synthetic creation-nudge exposures; synthetic task, deadline, and
  notification IDs were recorded in the proof artifact.
- Operator-cookie browser proof:
  `tmp/operator-readonly-stress-r3-task-day-query-key-operator-local-current/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- `queryKeys.tasksDay(date)` is exactly `["tasks", date]`.
- Today task reads, query cancellation, optimistic cache writes, previous-data
  snapshots, rollback writes, and invalidation targets use the same tuple values
  as before.
- Pulse still reads the same today-task key.
- No mutation payload, API call, stopwatch status key, task state transition,
  rollback branch, deadline binding behavior, exposure lifecycle behavior,
  notification lifecycle behavior, provider truth, Redis key, or export shape
  changed.

Verifier and issue notes:

- Issue `#161` records the intermittent notification host/verifier timing
  failure:
  `https://github.com/Holmesberg/lyra-secretary/issues/161`.
- The passing rerun was added to `#161` as evidence that the query-key seam did
  not reproduce the notification failure:
  `https://github.com/Holmesberg/lyra-secretary/issues/161#issuecomment-4896090694`.
- The product loop continued to record expected/gated states: Holmesberg
  onboarding gate skip, deadline suggestion fallback, brain-dump parser
  normalization, pressure-map safe-mode gate, provider credential mutation gate,
  account delete/purge gate, calendar drag/resize manual gate, and OpenClaw
  pending-drain authority gate.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28812787541`.
- Head SHA:
  `e86f2afa8fd97dbb82fb673ea566cce9f5bbf73c`.
- Structured proof:
  `tmp/ci-cd-proof/r3-task-day-query-key-e86f2af.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.

Rollback note:

- Revert commit `e86f2af` only. This restores the raw task-day cache-key arrays
  in Today and Pulse without touching schemas, production data, exposure
  lifecycle rows, provider rows, Redis queues, export/delete behavior,
  task/deadline binding mutation, timer state, or user content.

## R3 - Shared Me Query-Key Adoption

Commit: `68649d1` (`frontend: adopt shared me query key`).

Changed authority:

- No identity, auth, user account, export/delete, archetype, task, timer,
  deadline, provider, exposure, notification, Redis, schema, clean-data,
  ClaimCompiler, or AI authority changed.
- Existing `queryKeys.me` is now used by the remaining active `/v1/users/me`
  React Query consumers and invalidation sites.

Removed paths:

- Removed raw `["me"]` from the AppLayout `/v1/users/me` query.
- Removed raw `["me"]` from the AppLayout post-gate refresh invalidation.
- Removed raw `["me"]` from the Settings archetype `/v1/users/me` query.
- Removed raw `["me"]` from the Settings archetype refresh invalidation.
- Removed raw `["me"]` from the archetype insights card query.
- Removed raw `["me"]` from the archetype survey completion/skip
  invalidation.

Parked paths:

- Raw `["insights"]`, `["bias_factor", ...]`, `["proximity", ...]`,
  `["proximity-trend", ...]`, `["calendar-events", ...]`,
  `["calendar-events-today", ...]`, `["pause-predictions-pending-confirmation"]`,
  `["notifications-web-pending"]`, and `["user-categories"]` remain parked
  until their ownership and verification weight are explicit.
- Domain-wide invalidation helpers remain parked until every dependent cache is
  named and characterized.
- Stopwatch controller hooks, NewTaskModal submit/draft extraction, shared
  brain-dump reducer extraction, pressure-map planning mutation, provider
  credential mutation, calendar drag/resize mutation, account hard-delete /
  Redis purge, and OpenClaw pending-drain authority remain gated.
- The local wrapper build/dev-server sequencing bug is tracked separately as
  issue `#162` and was not fixed in this seam.

Moved authority:

- No product authority moved. The query-key module names cache keys only.
- AppLayout still owns the current-user gate and auth-expiry recovery surface.
- Settings still owns user export/delete UI and survey retake entry points.
- The backend remains the source of user identity, account, archetype, export,
  deletion, provider, and authorization truth.

Agent loop notes:

- The mini scout recommended this as the next smallest safe R3 seam after the
  task-day key factory.
- The scout classified it as low code risk and medium verification weight
  because AppLayout is the app current-user gate and Settings sits near
  export/delete UI.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend typecheck:
  `cd frontend && npm exec tsc -- --noEmit --pretty false` passed.
- Frontend production build:
  `cd frontend && node scripts/clean-next.mjs && npm run build:public` passed.
- S1C stack partial proof:
  `tmp/post-wave-dogfood/20260706-211923-r3-me-query-key-standard-local`.
  The stack passed diff check, authority scan, refactor contract scan, OpenClaw
  relay hermetic test, Alembic fresh database smoke, and frontend production
  build before the local topology browser leg failed.
- Wrapper failure classification:
  verifier/harness bug and local topology operations bug. The wrapper ran a
  production build while an existing Next dev server was serving from `.next`,
  after which `/api/topology` returned 500 and the dev stderr showed
  `_buildManifest.js.tmp` ENOENT errors. Tracked as issue `#162`.
- Follow-up local topology proof:
  after restarting the local dev frontend, `/api/topology` returned 200 with
  `verified_topology=true`, frontend origin `http://localhost:3000`, API origin
  `http://localhost:8000`, and build id `local-current`.
- Multi-account browser smoke:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_multi_account_browser_smoke.ps1 -Topology local`
  passed for operator and Holmesberg.
- Holmesberg product-loop proof:
  `tmp/browser-product-loop/r3-me-query-key/result.json`.
- Holmesberg outcome:
  route rendering, Settings rendering, Insights rendering, deadline creation and
  cleanup, explicit deadline binding, overlap conflict, creation-nudge Keep
  branch, no-deadline branch, custom category branch, pick-another branch,
  terminal deadline rejection, brain dump parse/commit/partial/retry/double
  submit, pressure-map read, timer start/pause/resume/stop/navigation
  persistence, notification lifecycle, export evidence, operator privacy scan,
  and cleanup all passed.
- Cleanup proof:
  the product loop ended with no active Holmesberg timer and no unrendered
  synthetic creation-nudge exposures; synthetic task, deadline, and notification
  IDs were recorded in the proof artifact.
- Operator-cookie browser proof:
  `tmp/operator-readonly-stress-2026-07-06T18-27-51-109Z/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `implementation_blockers=[]`,
  `exposure_without_render_count=0`, and cohort status remains yellow only for
  real-data gaps.

Behavior parity statement:

- `queryKeys.me` is exactly `["me"]`.
- AppLayout, Settings, archetype insights, and archetype survey invalidation
  use the same tuple value as before.
- No query function, mutation payload, API path, auth recovery behavior,
  current-user gate, survey submit/skip behavior, export/delete behavior,
  provider behavior, task/timer/deadline behavior, exposure lifecycle behavior,
  notification lifecycle behavior, Redis key, or export shape changed.

Verifier and issue notes:

- Issue `#162` records the local wrapper build/dev-server sequencing failure:
  `https://github.com/Holmesberg/lyra-secretary/issues/162`.
- The product loop continued to record expected/gated states: Holmesberg
  onboarding gate skip, deadline suggestion fallback, Today visibility fallback
  for some branch assertions, brain-dump parser normalization, pressure-map
  safe-mode gate, provider credential mutation gate, account delete/purge gate,
  calendar drag/resize manual gate, and OpenClaw pending-drain authority gate.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28814163084`.
- Head SHA:
  `68649d1d16c424fad9252eda2457e4b9d54cc24d`.
- Structured proof:
  `tmp/ci-cd-proof/r3-me-query-key-68649d1.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.

Rollback note:

- Revert commit `68649d1` only. This restores the raw `["me"]` arrays in the
  touched frontend surfaces without touching schemas, production data, exposure
  lifecycle rows, provider rows, Redis queues, export/delete behavior,
  task/deadline binding mutation, timer state, auth session data, or user
  content.

## S1c - Local Wrapper Frontend Restart Before Browser Gates

Commit: `4fdf595` (`scripts: restart local frontend before browser gates`).

Changed authority:

- No product, identity, auth, task, timer, deadline, provider, exposure,
  notification, Redis, schema, ClaimCompiler, AI, or clean-data authority
  changed.
- The S1c verification harness now owns a local-topology readiness step before
  browser gates run after a frontend build.

Removed paths:

- Removed the implicit assumption that a local Next dev server remains valid
  after the verification stack runs a frontend production build.
- Removed the failure mode where a local wrapper run could let browser smoke
  proceed against a dev server whose `.next` artifacts were modified by the
  build step.

Parked paths:

- Hosted-public deployment proof and build-ID matching remain R5b/R6 work.
- CI hard-fail lint gating remains parked until existing lint/noise allowlists
  are encoded.
- Other verifier issues remain separate tickets when they have different
  failure modes.

Moved authority:

- No runtime authority moved. This is a verifier/harness sequencing fix only.
- `run_s1c_verification_stack.ps1` now restarts the local frontend dev server
  when `-Topology local` and browser checks are enabled.
- Browser smoke scripts still own browser assertions; topology endpoint still
  owns frontend/backend topology reporting.

Issue and classification:

- GitHub issue:
  `https://github.com/Holmesberg/lyra-secretary/issues/162`.
- Classification:
  verifier/harness bug and local topology operations bug.
- Root cause:
  `run_post_wave_dogfood_loop.ps1` invoked the S1c stack while a local Next dev
  server was already serving from `.next`; the S1c frontend build rewrote build
  artifacts, after which the local `/api/topology` browser leg returned 500 and
  the dev server logged `_buildManifest.js.tmp` ENOENT errors.
- Resolution:
  before local browser gates, the S1c stack now stops any process listening on
  port 3000, starts `npm run dev -- -p 3000` with local topology env vars, and
  waits for `/api/topology` to report `verified_topology=true`,
  `topology_class=local`, and `compiled_api_origin=http://localhost:8000`.

Tests and verification:

- PowerShell parser check:
  `powershell -NoProfile -ExecutionPolicy Bypass -Command '$null = [scriptblock]::Create((Get-Content .\scripts\run_s1c_verification_stack.ps1 -Raw)); Write-Output parsed'`
  passed.
- Whitespace:
  `git diff --check` passed.
- Full failed-path rerun:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology local -Mode standard -IncludeProductLoop -WaveName "s1c-local-wrapper-dev-restart"`
  passed.
- Wrapper summary artifact:
  `tmp/post-wave-dogfood/20260706-213543-s1c-local-wrapper-dev-restart-standard-local/summary.json`.
- Wrapper outcome:
  `ok=true`, S1C verification stack passed, operator read-only after mutable
  pass passed, Holmesberg full product-loop browser dogfood passed, and
  operator read-only after product-loop dogfood passed.
- Holmesberg product-loop artifact:
  `tmp/post-wave-dogfood/20260706-213543-s1c-local-wrapper-dev-restart-standard-local/holmesberg-product-loop/result.json`.
- Holmesberg outcome:
  `ok=true`, local topology, cleanup recorded synthetic task/deadline and
  notification IDs, and no active Holmesberg timer was left behind.
- Operator-cookie browser proofs:
  `tmp/operator-readonly-stress-2026-07-06T18-37-33-223Z/result.json`,
  `tmp/operator-readonly-stress-2026-07-06T18-39-55-092Z/result.json`, and
  `tmp/operator-readonly-stress-2026-07-06T18-45-34-106Z/result.json`.
- Operator outcome:
  all three read-only runs had zero count diffs, zero route count diffs, zero
  dashboard snapshot diffs, and no warnings or issues.

Behavior parity statement:

- No app behavior changed.
- The harness change only affects local verification sequencing.
- Public topology verification behavior is unchanged.
- Product code, browser scripts, API payloads, mutation paths, database state,
  Redis state, and export/delete behavior are unchanged.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28818905072`.
- Head SHA:
  `4fdf59553d12f248f4fa0664da03ed6e1d0bf877`.
- Structured proof:
  `tmp/ci-cd-proof/s1c-local-wrapper-dev-restart-4fdf595.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.

Rollback note:

- Revert commit `4fdf595` only. This removes the local dev-server restart
  guard from the S1c stack and restores the prior harness sequencing. No
  production data, schema, product runtime, exposure lifecycle row, provider row,
  Redis key, user content, or CI workflow is touched by the rollback.

## S1c - Web Notification Host Refetch And Render-Proof Gate

Commit: `06c1557` (`frontend: refetch web notifications promptly`).

Changed authority:

- No task, timer, deadline, provider, schema, Redis, ClaimCompiler, AI, or
  clean-data authority changed.
- Web notification render truth remains owned by the browser host and web
  notification acknowledgement endpoint.
- The browser product-loop verifier now treats browser render as required
  evidence instead of substituting an API `rendered` acknowledgement when the
  toast is not observed.

Removed paths:

- Removed the 30-second pending-notification polling gap from the app shell by
  refetching pending web notifications on route changes and every 5 seconds
  while the host is mounted.
- Removed the verifier fallback that could turn a missed browser toast into a
  synthetic `rendered` lifecycle acknowledgement.

Parked paths:

- Domain/brand rename work remains separate from this S1c seam.
- Notification delivery load tuning can be revisited after alpha traffic exists.
- Hosted-public deployment proof and build-ID matching remain R5b/R6 work.

Moved authority:

- No runtime authority moved.
- The web notification host still decides whether a pending item can render,
  then records `rendered`, `dismissed`, `acted`, `expired`, or
  `lost_unrendered` through the existing lifecycle API.
- The dogfood verifier now cleans a missed pending synthetic row with
  `lost_unrendered` and fails the render proof instead of recording a false
  render.

Issue and classification:

- GitHub issue:
  `https://github.com/Holmesberg/lyra-secretary/issues/161`.
- Classification:
  product timing bug plus verifier/harness integrity bug.
- Root cause:
  the host used `staleTime=10000` and `refetchInterval=30000`, so a freshly
  queued web notification could remain invisible to the browser inside the
  12-second dogfood window after the shell had recently fetched an empty pending
  list.
- Resolution:
  the host now uses `staleTime=0`, `refetchInterval=5000`,
  `refetchOnMount="always"`, `refetchOnReconnect=true`, and a route-change
  refetch keyed by the current pathname.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend typecheck:
  `npm exec tsc -- --noEmit --pretty false` passed.
- Frontend build:
  `node scripts/clean-next.mjs; npm run build:public` passed.
- Script syntax:
  `node --check scripts\browser_notification_lifecycle_dogfood.mjs` and
  `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs` passed.
- Backend notification lifecycle tests:
  `pytest tests/test_notification_queue_openclaw_mirror.py::test_web_pending_reserves_and_render_ack_marks_only_rendered tests/test_notification_queue_openclaw_mirror.py::test_lost_unrendered_ack_does_not_mark_rendered tests/test_notification_queue_openclaw_mirror.py::test_notification_action_and_expiry_update_after_render_removal tests/test_notification_queue_openclaw_mirror.py::test_linked_notification_render_records_exposure_once -q`
  passed.
- Static authority scans:
  `scripts\scan_refactor_contracts.py --fail-on-errors` and
  `scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed.
- Full post-wave wrapper:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology local -Mode standard -IncludeProductLoop -WaveName "s1c-notification-host-refetch"`
  passed.
- Wrapper summary artifact:
  `tmp/post-wave-dogfood/20260707-145252-s1c-notification-host-refetch-standard-local/summary.json`.
- Holmesberg product-loop artifact:
  `tmp/post-wave-dogfood/20260707-145252-s1c-notification-host-refetch-standard-local/holmesberg-product-loop/result.json`.
- Holmesberg notification proof:
  the synthetic resume-prediction notification appeared in web pending, rendered
  as a browser toast, disappeared from pending without fallback rendered ack,
  and exported terminal lifecycle rows for dismissed, acted, and expired
  synthetic notifications.
- Cleanup proof:
  Holmesberg cleanup recorded synthetic task, deadline, and notification IDs and
  left no active Holmesberg timer.
- Operator-cookie browser proof:
  `tmp/operator-readonly-stress-2026-07-07T12-02-43-088Z/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs, no
  warnings, no issues, `implementation_green=true`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- User-visible notification content, notification payload shape, endpoint
  paths, lifecycle event names, export shape, Redis queue semantics, task/timer
  behavior, provider behavior, and exposure render authority are unchanged.
- The only app behavior change is fresher web pending-notification polling while
  the app shell is open.
- The only verifier behavior change is stricter proof: browser render must be
  observed for render truth, and missed synthetic rows use `lost_unrendered`
  cleanup.

CI/CD proof note:

- GitHub Actions run:
  `https://github.com/Holmesberg/lyra-secretary/actions/runs/28864746303`.
- Head SHA:
  `06c155786f02be86ae0a259fc33357e9d1a252fc`.
- Structured proof:
  `tmp/ci-cd-proof/s1c-notification-host-refetch-06c1557.json`.
- CI jobs passed:
  backend tests, frontend build, and topology contract.

Rollback note:

- Revert commit `06c1557` only. This restores the previous 30-second polling
  cadence and the previous verifier fallback. No schema, production data,
  exposure row, notification lifecycle row, provider row, Redis key, user
  content, or CI workflow is touched by the rollback.

## CI/CD - Deterministic Frontend Lint Gate

Commit: `6d1f2ea` (`ci: make frontend lint deterministic`).

Changed authority:

- No product, task, timer, deadline, provider, exposure, notification, schema,
  Redis, ClaimCompiler, AI, or clean-data authority changed.
- CI now runs a deterministic frontend lint/typecheck leg before the frontend
  production build.
- `npm run lint` in `frontend/` now delegates to `npm run typecheck`, which
  runs `tsc --noEmit --pretty false`.

Removed paths:

- Removed the deprecated interactive `next lint` command from the standard
  frontend package scripts.
- Removed the blocker that made frontend lint unusable as unattended CI/CD
  proof.

Parked paths:

- A full ESLint ownership/configuration pass remains parked until after the
  freeze-closure gates are stable. The current hard gate is deterministic
  TypeScript validity, not style linting.
- GitHub Actions Node 20 deprecation-warning cleanup remains tracked
  separately in issue #155.
- Wave-branch CI trigger policy remains tracked separately in issue #157.

Moved authority:

- No runtime authority moved.
- The frontend package script owns the local lint/typecheck command.
- The GitHub Actions frontend-build job owns the hosted lint/typecheck proof
  before build.

Issue and classification:

- GitHub issue:
  `https://github.com/Holmesberg/lyra-secretary/issues/153`.
- Classification:
  CI/CD operations bug plus verifier/harness automation gap.
- Root cause:
  `next lint` is deprecated for this Next.js version and opened an interactive
  ESLint setup prompt instead of checking source in unattended verification.

Tests and verification:

- Whitespace:
  `git diff --check -- .github\workflows\ci.yml frontend\package.json`
  passed.
- Package metadata:
  `node -e "JSON.parse(require('fs').readFileSync('frontend/package.json','utf8')); console.log('package json ok')"`
  passed.
- Frontend lint/typecheck:
  `npm run lint` passed and executed `tsc --noEmit --pretty false`.
- Frontend build:
  `node scripts\clean-next.mjs; npm run build:public` passed.
- Initial quick local browser proof:
  `run_post_wave_dogfood_loop.ps1 -Topology local -Mode quick -WaveName "ci-frontend-lint-gate"`
  failed at the topology verifier because the pre-existing local frontend
  returned HTTP 500 from `/api/topology`.
- Failure classification:
  topology/verifier setup bug, not a product regression from this CI change.
  Quick mode assumes local topology is already healthy.
- Passing browser proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology local -Mode standard -WaveName "ci-frontend-lint-gate"`
  passed.
- Wrapper summary artifact:
  `tmp/post-wave-dogfood/20260707-151615-ci-frontend-lint-gate-standard-local/summary.json`.
- Operator-cookie browser proof:
  `tmp/operator-readonly-stress-2026-07-07T12-18-34-313Z/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs, no
  warnings, no issues, `implementation_green=true`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- User-visible application behavior is unchanged.
- Hosted CI now fails earlier if the frontend type system fails.
- The command named `lint` is intentionally a deterministic typecheck gate for
  freeze closure; it does not claim ESLint style coverage.

Rollback note:

- Revert commit `6d1f2ea` only. This restores the prior interactive
  `next lint` script and removes the hosted CI lint/typecheck step. No runtime
  code, production data, schema, exposure row, notification lifecycle row,
  provider row, Redis key, user content, or browser verifier is touched by the
  rollback.

## R5b - Public Frontend Restart Compatibility Guard

Commit: current commit (`ops: guard stale public frontend restart path`).

Changed authority:

- `scripts\restart_frontend_wsl.ps1` remains the only authoritative public
  frontend restart path.
- `scripts\restart_public_frontend.ps1` is now a compatibility wrapper only:
  it warns, forwards supported flags to the authoritative WSL script, and can
  dry-run delegation without restarting anything.
- Deployment documentation now explicitly states that
  `restart_public_frontend.ps1` is not a separate restart authority.

Removed paths:

- Removed the stale Windows-hosted public frontend behavior from
  `restart_public_frontend.ps1`.
- Removed the path that could stop a Windows port-3000 process, start
  `npm run start:public` in Windows, and then claim public topology proof while
  Cloudflare was expected to reach the WSL tmux process.

Parked paths:

- Hosted-public build-ID matching remains R6 work.
- Public domain/brand rename remains separate from this ops safety seam.
- GitHub Actions Node 20 deprecation-warning cleanup remains tracked in issue
  #155.

Moved authority:

- No product runtime authority moved.
- Public frontend restart authority is now sealed to
  `scripts\restart_frontend_wsl.ps1`.
- The old public restart filename remains available only to preserve command
  compatibility and produce an explicit warning.

Issue and classification:

- GitHub issue:
  `https://github.com/Holmesberg/lyra-secretary/issues/158`.
- Classification:
  topology/deployment operations bug.
- Root cause:
  the old script name sounded authoritative while starting a Windows frontend
  process that was not the documented WSL/tmux public runtime.

Tests and verification:

- Whitespace:
  `git diff --check -- scripts\restart_public_frontend.ps1 docs\deployment_architecture.md`
  passed.
- PowerShell parser:
  `Parser::ParseFile` passed for `scripts\restart_public_frontend.ps1`.
- Dry-run delegation:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\restart_public_frontend.ps1 -NoBuild -SkipPublicCheck -DryRun`
  printed the delegated `restart_frontend_wsl.ps1` command and did not restart
  the frontend.
- Browser/operator proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology local -Mode quick -WaveName "ops-public-frontend-restart-wrapper"`
  passed.
- Wrapper summary artifact:
  `tmp/post-wave-dogfood/20260707-152509-ops-public-frontend-restart-wrapper-quick-local/summary.json`.
- Operator-cookie browser proof:
  `tmp/operator-readonly-stress-2026-07-07T12-26-54-469Z/result.json`.
- Operator outcome:
  zero count diffs, zero route count diffs, zero dashboard snapshot diffs, no
  issues, `implementation_green=true`, and `exposure_without_render_count=0`.
- Non-blocking warning:
  desktop `/operator` exceeded the existing latency budget; this is tracked by
  issue #150 and did not affect the restart authority fix.

Behavior parity statement:

- The authoritative public restart behavior is unchanged because
  `restart_frontend_wsl.ps1` is unchanged.
- Any caller using the old script path now reaches the authoritative WSL restart
  path instead of accidentally starting an alternate Windows public frontend.
- No user-facing app behavior changed.

Rollback note:

- Revert the ops guard commit only. This restores the old Windows public
  frontend restart behavior and removes the deployment-doc warning. No schema,
  production data, exposure row, notification row, provider row, Redis key,
  user content, CI workflow, or product runtime code is touched by rollback.

## CI/CD - GitHub Actions Node 24 Compatibility

Commit: current commit (`ci: update github actions node runtime majors`).

Changed authority:

- No product, task, timer, deadline, provider, exposure, notification, schema,
  Redis, ClaimCompiler, AI, clean-data, or browser-verifier authority changed.
- CI workflow action versions now use Node 24-compatible major releases:
  `actions/checkout@v5`, `actions/setup-node@v5`, and
  `actions/setup-python@v6`.

Removed paths:

- Removed the Node 20-hosted action versions that caused GitHub Actions to emit
  deprecation annotations while forcing the actions onto Node 24.

Parked paths:

- Wave-branch automatic CI trigger policy remains tracked in issue #157.
- Hosted-public build-ID matching remains R6 work.

Moved authority:

- No runtime authority moved.
- Hosted CI remains the proof authority for backend tests, frontend
  lint/typecheck/build, and static topology contract.

Issue and classification:

- GitHub issue:
  `https://github.com/Holmesberg/lyra-secretary/issues/155`.
- Classification:
  CI/CD operations maintenance warning.
- Root cause:
  the workflow used action majors that targeted Node 20 after GitHub Actions
  began moving hosted action execution to Node 24.

Tests and verification:

- Whitespace:
  `git diff --check -- .github\workflows\ci.yml` passed.
- Hosted CI proof must pass on the exact commit before issue #155 is closed.

Behavior parity statement:

- CI behavior should remain equivalent except that the GitHub-hosted action
  runtime deprecation annotations should disappear.
- User-visible app behavior is unchanged.

Rollback note:

- Revert the CI action-version commit only. This restores the previous action
  major versions and their warnings. No runtime code, production data, schema,
  exposure row, provider row, Redis key, user content, or browser verifier is
  touched by rollback.

## CI/CD - Wave Branch Trigger Policy

Commit: current commit (`ci: run workflow on wave branches`).

Changed authority:

- No product, task, timer, deadline, provider, exposure, notification, schema,
  Redis, ClaimCompiler, AI, clean-data, or browser-verifier authority changed.
- CI now runs automatically on pushes to `wave-*` branches in addition to
  `main`, pull requests to `main`, and manual dispatch.

Removed paths:

- Removed the need to manually dispatch CI after every pushed wave seam on this
  branch family.
- Removed the ambiguous `no_matching_run_for_head` proof state for ordinary
  `wave-*` branch pushes after this commit lands.

Parked paths:

- Pull-request policy remains unchanged: PR checks still target `main`.
- Hosted-public build-ID matching remains R6 work.

Moved authority:

- No runtime authority moved.
- GitHub Actions now owns automatic hosted proof for wave-branch pushes.

Issue and classification:

- GitHub issue:
  `https://github.com/Holmesberg/lyra-secretary/issues/157`.
- Classification:
  CI/CD operations policy gap.
- Root cause:
  the refactor loop required hosted CI proof after pushed seams, while the
  workflow only auto-triggered on `main` pushes and `main` pull requests.

Tests and verification:

- Whitespace:
  `git diff --check -- .github\workflows\ci.yml` must pass.
- Hosted CI proof:
  the first push of this commit to the current `wave-*` branch must create an
  automatic `push`-event CI run for the exact head SHA.

Behavior parity statement:

- User-visible app behavior is unchanged.
- CI will run more often on wave branches, which is intentional for
  freeze-closure proof discipline.

Rollback note:

- Revert the wave-trigger commit only. This restores manual-dispatch-only CI
  proof for wave branches. No runtime code, production data, schema, exposure
  row, provider row, Redis key, user content, or browser verifier is touched by
  rollback.

## App-Facing Rebrand - LyraOS

Commit: this commit (`rebrand app-facing surfaces to LyraOS`).

Changed authority:

- Product brand authority moves from visible `Lyra` / `LyraOS` copy to
  `LyraOS` across app shell, landing page, onboarding, settings, integration
  copy, public policy pages, public AI-readable files, notification copy,
  email copy, and browser-verifier selectors.
- Runtime topology, current public host compatibility, lower-case data
  contracts, env vars, cache keys, and old incident repair scripts do not move
  authority in this seam.

Removed paths:

- Removed public static brand assets:
  `frontend/public/lyraos-logo.png`,
  `frontend/public/lyraos-logo-mark.png`, and
  `frontend/public/lyraos.md`.
- Added replacement public assets/brief:
  `frontend/public/lyraos-logo.png`,
  `frontend/public/lyraos-logo-mark.png`, and
  `frontend/public/lyraos.md`.

Parked paths:

- Domain migration remains parked. Current topology and verification defaults
  may still use `lyraos.org` / `api.lyraos.org` until a separate deployment
  authority change is planned and verified.
- Internal compatibility names remain parked for later migration only where
  safe: `LYRA_*` env vars, `lyra_task`, `planned_lyra_minutes`,
  `lyra-rq-cache`, `lyra:undo-available`, topology manifest hostnames,
  historical repair scripts, and historical docs/audits.
- Broad historical/internal documentation rename is parked. This seam is
  app-facing and public-served-surface only.

Moved authority:

- Public AI-readable product description moved from `/lyraos.md` to
  `/lyraos.md`.
- Public crawler references in `llms.txt`, `robots.txt`, sitemap metadata,
  OpenGraph/Twitter metadata, and JSON-LD now present the LyraOS brand.
- Browser verification selectors now look for LyraOS-visible strings.

Issue and classification:

- No new product bug was discovered.
- Verifier classification notes:
  - Initial bare `pytest ...` failed because the shell resolved to a Python
    environment without FastAPI. Rerun through `.venv311` passed.
  - Initial ad hoc brand-smoke artifact wrapper failed because the temporary JS
    file ran outside `frontend` and could not resolve Playwright. Rerun with
    `node -` from `frontend` passed and saved an artifact.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Frontend:
  `cd frontend && npm run lint` passed.
- Frontend production build:
  `cd frontend && node scripts\clean-next.mjs; npm run build:public` passed.
- Backend targeted tests:
  `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests\test_email_delivery.py tests\test_email_engagement.py tests\test_feedback_endpoint.py tests\test_parse_deadline_preview.py tests\test_reactivation_email_script.py tests\test_user_activation_email.py -q`
  passed.
- Runtime topology contract:
  `node scripts\test_runtime_topology_contract.mjs` passed.
- OpenClaw relay unit:
  `node scripts\test_openclaw_operator_relay.mjs` passed.
- Reusable post-wave dogfood loop:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology local -Mode standard -WaveName lyraos-app-facing-rebrand -IncludeProductLoop`
  passed. Summary:
  `tmp/post-wave-dogfood/20260707-155759-lyraos-app-facing-rebrand-standard-local/summary.json`.
- Holmesberg mutable product-loop proof:
  `tmp/post-wave-dogfood/20260707-155759-lyraos-app-facing-rebrand-standard-local/holmesberg-product-loop/result.json`
  passed with 105 checks, 0 failed checks, cleanup IDs for 8 tasks,
  7 deadlines, and 3 notifications. Non-fatal notes were onboarding gate open,
  one suggestion fallback, parser title normalization, and pressure recovery
  still gated.
- Operator read-only proof after mutable/product loop:
  `tmp/operator-readonly-stress-2026-07-07T13-07-41-301Z/result.json`
  passed with no DB/API/Redis count diffs, no route diffs, no dashboard
  snapshot diffs, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Explicit public brand browser smoke:
  `tmp/rebrand-proof/lyraos-brand-smoke-20260707-161215.json`
  passed for `/`, `/privacy`, `/terms`, `/llms.txt`, `/lyraos.md`; old public
  paths `/lyraos.md`, `/lyraos-logo.png`, and `/lyraos-logo-mark.png` returned
  404.

Behavior parity statement:

- User-facing brand copy changes to LyraOS.
- Task, timer, deadline, exposure, notification, provider, clean-data,
  ClaimCompiler, schema, and Redis behavior should remain unchanged except for
  generated display text and email/public-copy branding.
- Current deployment topology is intentionally unchanged.

Rollback note:

- Revert the LyraOS rebrand commit only. This restores visible Lyra/LyraOS
  copy and old public asset paths. No schema migration, production repair,
  exposure row mutation, provider row mutation, Redis purge, or domain
  migration is part of this seam.

## Freeze Closure - Operational Danger And Proof Discipline

Commit: `61c92e5` (`docs: operationalize refactor danger gates`).

Changed authority:

- No product, task, timer, deadline, provider, exposure, notification, schema,
  Redis, ClaimCompiler, AI, clean-data, or browser-verifier runtime authority
  changed.
- The active freeze-closure plan now defines "danger 3-4/10" as an operational
  gate instead of an intuitive spaghetti score.
- The post-wave runbook now treats hosted-public mutable dogfood as optional
  high-care proof unless test-account cleanup is proven safe.

Removed paths:

- Removed the implicit permission to keep doing R3/R4 cleanup merely because it
  reduces line count, file count, or apparent surface area.

Parked paths:

- Additional brand/domain migration remains parked until a separate topology
  and runtime-host plan is authorized.
- Hosted-public mutable dogfood remains parked unless the mutable test account,
  unique synthetic prefix, cleanup scope, and rollback path are already proven.

Moved authority:

- Refactor continuation authority now depends on recorded danger delta:
  improved observability, reversibility, ownership, measurement integrity, or
  runtime proof.
- Three consecutive cosmetic-only seams must stop opportunistic R3/R4
  refactoring and redirect the next pass to public proof, users, or S1c
  hardening.

Issue and classification:

- No product bug was discovered.
- Classification:
  governance/runbook correction to prevent refactor ceremony from displacing
  product proof.

Tests and verification:

- Whitespace:
  `git diff --check` passed.
- Runtime behavior:
  not applicable; docs-only change.
- CI/CD:
  GitHub Actions CI passed for exact SHA
  `61c92e53d332b0b8808d1781006b8f260aabc503`;
  artifact: `tmp/ci-cd-proof/danger-gates-61c92e5.json`.

Behavior parity statement:

- User-visible app behavior is unchanged.
- The change only alters how future seams are judged, documented, and allowed
  to continue.

Rollback note:

- Revert this docs/runbook commit only. This restores the prior plan wording.
  No runtime code, production data, schema, exposure row, provider row, Redis
  key, user content, or CI workflow is touched by rollback.

## R2 Cockpit - Controlled Evidence Collection Warning Semantics

Commit: `cd244e2` (`operator: allow controlled evidence collection with nonblocking warnings`).

Changed authority:

- `/operator` readiness semantics now distinguish cohort evidence blockers
  from nonblocking warnings when deciding whether controlled evidence
  collection is allowed.
- Warnings still appear in the cockpit and in `cohort_evidence_gaps`, but they
  no longer veto the narrow alpha exception when the only cohort blockers are
  missing real usage data.

Removed paths:

- Removed the accidental path where an instrumentation warning could make
  controlled evidence collection look forbidden even though implementation was
  green and only real closed-loop data was missing.

Parked paths:

- No cohort expansion, marketing launch, AI synthesis, new user-facing insight,
  schema migration, production repair, or hosted-public mutable dogfood is
  authorized by this seam.

Moved authority:

- The controlled evidence collection exception remains owned by the operator
  cockpit readiness contract in `backend/app/api/v1/endpoints/operator.py`.
- Cohort expansion authority still requires `cohort_green` or an explicit
  controlled evidence-collection alpha decision.

Issue and classification:

- Classification:
  operator cockpit semantics bug.
- GitHub issue:
  #163, closed after commit/push/CI proof.

Tests and verification:

- Targeted backend:
  from `backend/`, `..\.venv311\Scripts\python.exe -m pytest
  tests\test_operator_dashboard.py -q` passed after correcting the invocation
  to the repo's Python 3.11 venv and backend working directory.
- Static authority:
  `python scripts\scan_authority_surfaces.py --fail-on-missing
  --fail-on-worker-write-drift` passed.
- Browser proof:
  local operator read-only browser stress passed with zero count diffs,
  implementation green, cohort yellow, and `exposure_without_render_count=0`;
  artifact:
  `tmp/operator-readonly-stress-2026-07-07T23-41-33-322Z/result.json`.
- CI/CD:
  GitHub Actions CI passed for exact SHA
  `cd244e27eb1619d8aea6a17ef90bb558ec2bc394`;
  artifact:
  `tmp/ci-cd-proof/operator-controlled-evidence-cd244e2.json`.

Behavior parity statement:

- User product flows are unchanged.
- The operator dashboard becomes more faithful to the freeze-closure plan: it
  can show implementation green, cohort yellow, visible warnings, and controlled
  evidence collection allowed at the same time.

Rollback note:

- Revert this cockpit commit only. This restores the previous stricter
  controlled evidence flag behavior. No schema, production data, exposure rows,
  provider rows, Redis keys, user content, or public deployment topology are
  touched.

## S1c Hardening - CI Authority Gates And Session Write Detection

Commit: `ee605a8` (`ci: enforce s1c static authority gates`).

Changed authority:

- The mutation surface registry is now an active S1c hard gate for missing
  owners and worker write drift, not only a report-only inventory.
- GitHub Actions CI now runs S1c static gates in addition to backend tests,
  frontend build/typecheck, and topology contract proof.
- The authority scanner now detects SQLAlchemy `session.add(...)`,
  `session.flush(...)`, `session.merge(...)`, `session.execute(...)`, and
  `session.commit(...)` write idioms, not only `db.commit(...)`.

Removed paths:

- Removed a false-negative path where append-only security audit writes were
  invisible to the mutation-surface scan.
- Removed the CI/CD gap where a pushed refactor could pass hosted CI without
  running local S1c authority/refactor gates.

Parked paths:

- No new mutation authority is created.
- Security audit rows remain append-only governance transport only and remain
  forbidden from Cortex, clean-data profiles, ClaimCompiler, adaptive
  scheduling, productivity claims, or user behavior analysis.
- Generic lint expansion, broader cosmetic cleanup, and backend god-module
  extraction remain parked until the S1c hard gates are stable.

Moved authority:

- `backend/app/services/security_audit.py` is explicitly owned by
  `security_audit_authority` in the mutation surface registry.
- CI/CD now participates in S1c proof authority by enforcing:
  authority surface scan, refactor contract scan, OpenClaw relay hermetic test,
  and Alembic fresh database smoke.

Issue and classification:

- Classification:
  S1c measurement/verifier gap and CI/CD operations gap.
- GitHub issue:
  #164, closed after commit/push/CI proof.

Tests and verification:

- Local proof:
  `git diff --check`;
  `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  `python -m py_compile scripts\scan_authority_surfaces.py scripts\scan_refactor_contracts.py`;
  `python scripts\scan_refactor_contracts.py --fail-on-errors`;
  `node scripts\test_openclaw_operator_relay.mjs`;
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_alembic_fresh_smoke.ps1`;
  all passed.
- Hosted proof:
  GitHub Actions CI passed for exact SHA
  `ee605a821df4f9554505dc3295825edbda7305fe`, including the new
  `s1c-static-gates` job; artifact:
  `tmp/ci-cd-proof/s1c-static-gates-ee605a8.json`.

Behavior parity statement:

- Runtime product behavior is unchanged.
- The change only strengthens verification so refactor breakage and authority
  drift become observable in one standard CI/local proof run.

Rollback note:

- Revert this S1c hardening commit only. This removes the new CI job, restores
  the prior scanner marker set, and returns the registry to report-only
  language. No schema, production data, exposure row, provider row, Redis key,
  user content, or public deployment topology is touched.

## R5a Docs - Stale Authority Cleanup Before Extraction

Commit:
`43bbcd151fad22cb01fc0f413d2e64991d077a38`
(`docs: tighten r5a authority boundaries`).

Changed authority:

- No runtime authority changed.
- `docs/integrations_architecture.md` now states that future integrations need
  freeze authority before adding provider adapters, OAuth scopes, passive
  tracking, provider completion truth, AI synthesis, new insights, behavior
  equations, schema work, or automatic interventions.
- `docs/moodle_lms_integration.md` now clarifies that the existing Moodle path
  may be maintained only through canonical provider, deadline, and user-data
  authorities.
- `docs/deadline_mechanism_design.md` now marks the Apr 25 deadline decision as
  provenance, not current permission for schema work, parser inference,
  soft-warning UX, background transitions, or provider-derived completion truth.
- `docs/building_phases.md` now marks Tier 1.5 and Phase 6 as
  historical/parked roadmap material during freeze.
- `docs/architecture.md` now marks the OpenClaw Docker networking section as
  historical reachability documentation, not permission for OpenClaw product
  wiring, identity bypass, AI synthesis, or direct backend mutation.

Removed paths:

- Removed the active-looking docs path where integration architecture could be
  mistaken as permission for new provider expansion during freeze.
- Removed the active-looking Moodle docs path where provider-derived completion
  evidence could be mistaken as clean execution truth.
- Removed the active-looking deadline, retention, Phase 6, and OpenClaw
  networking docs paths where historical design notes could be mistaken as
  permission for runtime work during freeze.

Parked paths:

- New provider adapters, broader LMS expansion, passive tracking, runtime AI
  synthesis, OpenClaw-to-product wiring, user-facing insights,
  behavior-transition equations, schema migrations, parser inference,
  provider-derived completion truth, pause prediction, and automatic
  interventions remain parked.

Moved authority:

- Existing shipped integration, deadline, and OpenClaw maintenance remains
  subordinate to the active authority docs, provider/deadline/user-data
  contracts, clean-data boundaries, exposure lifecycle, and ClaimCompiler
  boundaries.
- Provider facts remain provenance-bearing candidates unless a current active
  contract and explicit user action promote them into native truth.

Issue and classification:

- Classification:
  documentation authority gap.
- GitHub issue:
  #165, closed after commit/push/CI proof.

Tests and verification:

- Local proof:
  `git diff --check` passed.
- Hosted proof:
  GitHub Actions CI passed for exact SHA
  `43bbcd151fad22cb01fc0f413d2e64991d077a38`; run
  `28907350174`; artifact:
  `tmp/ci-cd-proof/r5a-doc-boundaries-43bbcd1.json`.

Behavior parity statement:

- Runtime product behavior is unchanged.
- The change only prevents stale/future docs from authorizing runtime work
  during freeze.

Rollback note:

- Revert this docs commit only. This restores the prior docs wording. No
  runtime code, production data, schema, exposure row, provider row, Redis key,
  user content, or CI workflow is touched.

## R3 Frontend - Query-Key And Invalidation Vocabulary Seam

Commit:
`0b1f3da0784969825f71c8316dbf3e9b6836edad`
(`frontend: centralize calendar query keys`).

Changed authority:

- No runtime authority changed.
- `frontend/lib/query-keys.ts` now names the remaining Today/Calendar calendar
  event query keys and the pending pause-confirmation query key.
- Integrations invalidation now uses shared calendar/deadline predicate helpers
  instead of local inline predicates.

Removed paths:

- Removed raw `calendar-events`, `calendar-events-today`, and
  `pause-predictions-pending-confirmation` query-key call sites from Today and
  Calendar pages.
- Removed inline cache-invalidation predicates from the integrations settings
  surface.

Parked paths:

- NewTaskModal submit/draft/creation-nudge authority remains parked for a
  separate higher-care seam.
- Stopwatch controller extraction remains parked.
- Pressure-map preview/commit authority remains the recommended next real R3
  danger-reduction seam.
- Calendar drag/resize mutation, provider credential mutation, and shared
  brain-dump reducer extraction remain parked until targeted browser proof is
  selected.

Moved authority:

- None. The tuple values are preserved exactly; only their named accessors and
  invalidation predicates moved to the query-key vocabulary module.

Issue and classification:

- Refactor classification:
  frontend cache vocabulary seam, behavior-preserving.
- Verifier classification:
  direct local operator stress first failed because a stale Windows Next.js
  listener owned `localhost:3000`; the corrected local S1c wrapper started a
  verified local-topology frontend before browser proof.
- GitHub issue:
  #166 tracks the verifier/topology collision.

Tests and verification:

- Local proof:
  `git diff --check`;
  `cd frontend; npm run typecheck`;
  `cd frontend; npm run build`;
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology local -SkipBackendFull -SkipFrontendBuild`;
  all passed.
- Browser proof:
  `tmp/operator-readonly-stress-2026-07-08T00-18-17-372Z/result.json`
  passed with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted proof:
  GitHub Actions CI passed for exact SHA
  `0b1f3da0784969825f71c8316dbf3e9b6836edad`; run
  `28908134193`; artifact:
  `tmp/ci-cd-proof/r3-query-keys-0b1f3da.json`.

Behavior parity statement:

- Runtime product behavior is intended to be unchanged.
- Query keys keep the same tuple values, so persisted cache roots and existing
  invalidation semantics remain compatible.

Rollback note:

- Revert this frontend seam commit only. This restores raw query-key call sites
  and inline invalidation predicates. No backend code, schema, production data,
  exposure row, provider row, Redis key, or user content is touched.

## R3 Frontend - Pressure-Map Plan Commit Controller Seam

Commit:
9ff78f07e237f2d5cf385ef517c2806f560bddd9

Changed authority:

- No runtime authority changed.
- The explicit user-action boundary for pressure-map recovery plan creation now
  has one named controller hook:
  `frontend/components/pulse/use-pressure-map-plan-commit.ts`.
- `PulseAcademicPressureMap` remains the presentation and plan-option selection
  surface.
- The hook preserves the existing diagnostic-to-task transition:
  pressure map preview -> explicit lock-in -> canonical `createTask` call ->
  pressure/deadline/task/calendar cache invalidation.

Removed paths:

- Removed pressure-map recovery plan creation state, cold-start enrichment,
  conflict force handling, and cache invalidation from the large
  `PulseAcademicPressureMap` component body.
- Removed the mixed presentation/mutation path where preview rendering and task
  creation were interleaved in a single component.

Parked paths:

- Backend recovery-option gating remains unchanged.
- Pressure-map recovery options remain diagnostic and require explicit user
  action before task creation.
- Hosted-public mutable pressure-map dogfood remains high-care and optional
  unless cleanup proof is safe.
- Stopwatch controller extraction, NewTaskModal submit/creation-nudge
  extraction, calendar drag/resize mutation, and table correction/export
  hardening remain parked for separate seams.

Moved authority:

- No authority moved to the client beyond the pre-existing explicit button path.
- The pressure-map controller owns only local preview state and the explicit
  task-creation command already used by the component.
- The backend task endpoint remains the task mutation authority.
- Deadline linkage remains explicit in the `deadline_id` carried to
  `createTask`; pressure-map estimates remain planning footprint only, not
  execution truth.

Issue and classification:

- Refactor classification:
  frontend mutation-boundary extraction, behavior-preserving.
- Verification classification:
  local topology initially had a stale `localhost:3000` listener returning 500;
  this is the existing verifier/topology issue #166. The S1c wrapper restarted
  a verified local-topology frontend before mutable browser proof.

Tests and verification:

- Local proof:
  `git diff --check`;
  `cd frontend; npm run typecheck`;
  `cd frontend; npm run build`;
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors`;
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_academic_pressure_map.py tests\test_create_task_with_deadline.py -q`;
  all passed.
- Browser proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology local -SkipBackendFull -SkipFrontendBuild`
  passed and verified local topology.
- Holmesberg product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --run-id r3-pressure-map-plan-controller --out-dir tmp\browser-product-loop\r3-pressure-map-plan-controller --force-pressure-recovery`
  passed with `ok=true`.
- Pressure-map chain proof:
  the loop seeded a due-soon deadline, opened pressure map preview, dismissed
  without creating a task, reopened, locked in a recovery block, verified exactly
  one created recovery block, verified deadline binding and planning-footprint
  provenance, verified calendar visibility, and recorded cleanup IDs.
- Browser-only fixture caveat:
  backend returned no real `create_plan`/`split_into_blocks` recovery option for
  the seeded item, so the browser loop forced the recovery option in the
  pressure-map response. The task creation, deadline binding, provenance,
  calendar visibility, and cleanup checks still used the real local backend.
- Operator read-only proof after mutable dogfood:
  `tmp/operator-readonly-stress-2026-07-08T00-40-11-082Z/result.json`
  passed with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted proof:
  GitHub Actions CI passed for exact SHA
  `9ff78f07e237f2d5cf385ef517c2806f560bddd9`; run
  `28908964700`; artifact:
  `tmp/ci-cd-proof/r3-pressure-map-plan-controller-9ff78f0.json`.

Behavior parity statement:

- Runtime product behavior is intended to be unchanged.
- The `createTask` payload, conflict force behavior, cold-start calibration
  lookup, preview dismiss behavior, cache invalidations, and close-on-success
  behavior are preserved.

Rollback note:

- Revert this frontend seam commit only. This restores pressure-map recovery
  preview state and commit logic to `PulseAcademicPressureMap`. No backend code,
  schema, production data, exposure row, provider row, Redis key, or user
  content is touched.

## R3 Frontend - Pause-Reason Contract Seam

Commit:
2ea03c0f44beafebf5e8ff5fe176504bcd2b9ea5

Changed authority:

- No runtime authority changed.
- Frontend pause reasons now have one typed vocabulary module:
  `frontend/lib/stopwatch-pause-reasons.ts`.
- `pauseStopwatch` now accepts `PauseReason` instead of arbitrary `string`.
- `ActiveTimerBanner.quickPauseReason` now accepts `PauseReason` instead of
  arbitrary `string`.
- `PulseFocusCard` keeps the existing one-tap pause behavior but uses the
  named `QUICK_PAUSE_REASON` constant instead of a raw
  `"intentional_break"` literal.

Removed paths:

- Removed the duplicate local `PAUSE_REASON_OPTIONS` list from
  `ActiveTimerBanner`.
- Removed the raw frontend `pauseStopwatch("intentional_break")` mutation call
  from `PulseFocusCard`.
- Removed the loose `string` type path for frontend pause-command reasons.

Parked paths:

- The product/research decision about whether quick pause should continue to
  map to `intentional_break` remains parked.
- Browser proof for multi-paused switch-chip UI remains parked; current
  product-loop coverage does not exercise that chip path.
- Deeper stopwatch elapsed-clock/controller extraction remains parked until it
  reduces observable danger rather than only component size.

Moved authority:

- No pause authority moved.
- The backend stopwatch endpoint remains the validation and mutation authority
  for pause events.
- The frontend vocabulary mirrors the backend enum and prevents new noncanonical
  pause reasons from being introduced accidentally in frontend command code.

Issue and classification:

- Refactor classification:
  frontend measurement-contract seam, behavior-preserving.
- GitHub issue:
  #167 tracks the duplicated/loose frontend pause-reason vocabulary.
- Verifier classification:
  a parallel `npm run typecheck` plus `npm run build` attempt caused a transient
  `.next/types` TS6053 failure while build regenerated Next types. Sequential
  frontend checks passed; the repo verification wrappers already run these
  checks sequentially.

Tests and verification:

- Static proof:
  `rg -n 'pauseStopwatch\("(mental_fatigue|distraction|task_difficulty|external_interruption|intentional_break|prayer|task_switch)"' frontend`
  returned no matches.
- Static proof:
  `rg -n 'quickPauseReason\?: string|pauseStopwatch\(reason\?: string' frontend`
  returned no matches.
- Local proof:
  `git diff --check`;
  `cd frontend; npm run typecheck`;
  `cd frontend; npm run build`;
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors`;
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_pause_resume_pause_event.py tests\test_stopwatch_switch.py tests\test_stopwatch_recovery.py tests\test_stopwatch_pause_counter_anchor.py tests\test_void_clears_stopwatch.py -q`;
  all passed.
- Browser proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_s1c_verification_stack.ps1 -Topology local -SkipBackendFull -SkipFrontendBuild`
  passed and verified local topology.
- Holmesberg product-loop proof:
  `node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology local --run-id r3-pause-reason-contract --out-dir tmp\browser-product-loop\r3-pause-reason-contract --force-pressure-recovery`
  passed with `ok=true`.
- Timer-chain proof:
  product loop verified timer start, pause status, paused-session survival
  across Pulse refresh and Calendar navigation, Today banner visibility,
  pause-counter anchoring, resume, stop, execution delta fields, exported
  stopwatch session rows, exported pause event rows, and cleanup with no active
  Holmesberg timer.
- Operator read-only proof after mutable dogfood:
  `tmp/operator-readonly-stress-2026-07-08T01-06-40-479Z/result.json`
  passed with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/r3-pause-reason-contract-2ea03c0.json` passed for
  commit `2ea03c0f44beafebf5e8ff5fe176504bcd2b9ea5` on GitHub Actions run
  `28910050827`.

Behavior parity statement:

- Runtime product behavior is intended to be unchanged.
- Existing pause labels, quick-pause value, Pulse focus-card pause behavior,
  ActiveTimerBanner reason picker behavior, and backend payload values are
  preserved.

Rollback note:

- Revert this frontend seam commit only. This restores the duplicate local
  pause-reason list and loose string typing. No backend code, schema,
  production data, exposure row, provider row, Redis key, or user content is
  touched.

## R2 Operator - Notification Freshness Read Seam

Commit:
89872b17e0eb38721fe6ab0a0531903b11295dbd

Changed authority:

- No notification lifecycle mutation authority changed.
- The operator dashboard data-freshness snapshot now reads durable
  `NotificationLifecycleEvent` timestamps for `notifications_last_seen_at`
  instead of hard-coding notification freshness as unavailable.
- `NotificationLifecycleEvent.last_transition_at` remains the primary freshness
  timestamp, with `created_at` as a defensive fallback.

Removed paths:

- Removed the stale read path where `/operator` reported
  `notification_source_freshness_not_instrumented` even when durable
  notification lifecycle rows existed.

Parked paths:

- No delivery/source freshness age threshold was added. This seam only
  distinguishes observable notification lifecycle evidence from missing
  lifecycle evidence.
- Invalid recovery action instrumentation remains parked; `/operator` still
  reports that as a cohort evidence gap.

Moved authority:

- No runtime authority moved.
- Notification lifecycle creation and transition authority remains in
  notification lifecycle services and notification endpoints.
- Operator metrics remain read-only diagnostics.

Issue and classification:

- GitHub issue:
  #168 tracks the operator cockpit / measurement bug.
- Verifier classification:
  an initial local operator stress attempt hit a transient local
  `/api/topology` 500 before the patch was verified. A direct topology read
  and repeat operator stress passed; no product code was changed for that
  transient topology event.

Tests and verification:

- Local proof:
  `git diff --check`;
  `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py tests\test_operator_route_security.py -q`;
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors`;
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  all passed.
- Operator read-only browser proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology local`
  passed with artifact
  `tmp/operator-readonly-stress-2026-07-08T01-21-42-682Z/result.json`,
  `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Cockpit result:
  `notification_source_freshness_not_instrumented` no longer appears when
  notification lifecycle rows exist. Cohort remains yellow for true evidence
  gaps including `no_closed_sessions_last_14d`,
  `timer_closure_rate_below_green_threshold`,
  `insufficient_full_loop_users`, `no_closed_sessions_for_trace_ratio`,
  `invalid_recovery_actions_not_instrumented`, and
  `product_loop_dropoff_detected`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/r2-notification-freshness-89872b1.json` passed for commit
  `89872b17e0eb38721fe6ab0a0531903b11295dbd` on GitHub Actions run
  `28910615338`.

Behavior parity statement:

- Runtime product behavior is intended to be unchanged.
- Notification queueing, delivery, render, dismiss, action, exposure,
  suppression, and OpenClaw transport behavior are not changed.

Rollback note:

- Revert this seam commit only. This restores the hard-coded
  `notifications_last_seen_at=None` cockpit behavior. No schema, production
  data, notification lifecycle row, exposure row, Redis key, provider row, or
  user content is touched.

## S1c Hardening - Calendar/Table Mutation Dogfood Gate

Commit:
0a75f43d9b2b48d454c7b12d6c5e97f65c3ba257

Changed authority:

- Table audit/history now opts into voided task rows by calling
  `queryTasksRange(..., { includeVoided: true })`.
- `queryTasksRange` keeps the default voided-row guard for other callers.
- `queryKeys.tasksRangeWindow` now includes the include-voided mode so Table
  cache entries cannot contaminate Pulse or Calendar cache entries.
- Added a reusable local-only Holmesberg browser dogfood gate for calendar and
  table mutation/audit paths.

Removed paths:

- Removed the dead Table path where the `Show voided` checkbox could not reveal
  voided rows because the backend query had already excluded them.

Parked paths:

- Physical Schedule-X drag/resize gesture synthesis remains gated. The new
  proof exercises the same canonical reschedule authority and browser calendar
  rendering, but does not synthesize low-level drag/resize DOM gestures.
- Hosted-public mutable calendar/table dogfood remains blocked by wrapper
  policy until hosted cleanup is explicitly approved.

Moved authority:

- No mutation authority moved.
- Calendar reschedule authority remains `/v1/reschedule`.
- Table correction authority remains `/v1/tasks/{task_id}/execution-correction`.
- Table remains the audit/history surface that may request voided rows for
  client-side reveal; Pulse and Calendar remain on default non-voided reads.

Issue and classification:

- GitHub issue:
  #169 tracks the Table `Show voided` product/audit-history bug.
- Verifier classifications:
  - initial table-correction failure was a harness timing error; the script now
    waits for the exact correction API response and polls canonical task state.
  - a 44-minute correction result exposed second/millisecond truncation in
    synthetic fixtures; the script now creates minute-aligned synthetic rows and
    asserts the backend response's corrected duration.
  - the CSV header expectation was a harness contract error; Table CSV uses
    `actual_duration_minutes` for displayed/effective duration.
  - the first show-voided probe placed the voided row outside Table's default
    date range; the final script places the probe inside today's range.

Tests and verification:

- Frontend proof:
  `cd frontend; npm run typecheck; npm run build`;
  passed.
- Direct browser proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_calendar_table_mutation_dogfood.ps1 -Topology local -RunId s1c-calendar-table-mutation-local-green2 -OutDir tmp\browser-calendar-table-mutation\s1c-calendar-table-mutation-local-green2`;
  passed with `ok=true`.
- Reusable post-wave proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology local -Mode standard -WaveName s1c-calendar-table-mutation -IncludeCalendarTableMutation`;
  passed with summary
  `tmp/post-wave-dogfood/20260708-044448-s1c-calendar-table-mutation-standard-local/summary.json`.
- Calendar/table proof artifact:
  `tmp/post-wave-dogfood/20260708-044448-s1c-calendar-table-mutation-standard-local/calendar-table-mutation/result.json`
  passed with `ok=true`.
- Operator read-only proof after mutable pass:
  `tmp/operator-readonly-stress-2026-07-08T01-50-56-679Z/result.json`
  passed with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Proven paths:
  calendar renders a planned synthetic task; canonical reschedule updates
  planned task times; calendar renders the rescheduled task after reload;
  executed task reschedule is rejected; Table renders an executed synthetic
  row; Table correction reaches the backend and updates effective duration;
  user export contains the correction row; Table hides voided rows by default;
  `Show voided` reveals the voided row; Table CSV contains corrected and
  voided rows; CSV has no obvious private markers; cleanup leaves no active
  Holmesberg timer, no unrendered synthetic creation-nudge exposure debt, and
  no non-voided synthetic tasks.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/s1c-calendar-table-mutation-0a75f43.json` passed for
  commit `0a75f43d9b2b48d454c7b12d6c5e97f65c3ba257` on GitHub Actions run
  `28911782000`.

Behavior parity statement:

- Pulse and Calendar task range reads are intended to remain unchanged.
- Table default visual behavior is intended to remain unchanged: voided rows are
  still hidden until the user enables `Show voided`.
- Table now has the data needed for its existing `Show voided` control to work.

Rollback note:

- Revert this seam commit only. This removes the new S1c browser proof and
  restores Table to the previous non-voided task range query. No schema,
  production data, exposure row, provider row, Redis key, or user content is
  touched.

## R5a Stale Docs - Authority Subordination Gate

Commit:
0e9e827647122bffa2bfcfb1b1d2434427cdf85b

Changed authority:

- No runtime authority changed.
- `docs/current_transition_state.md` now names the stale/parked docs that cannot
  authorize runtime work during freeze closure.
- Known stale planning docs now carry an explicit R5a extraction rule: active
  words such as `ship`, `allowed`, `approved`, schema sketches, passive
  tracking, AI/synthesis, provider adapters, insight surfaces, and behavior
  equations are historical/parked unless promoted by the active authority
  chain.
- `scripts/scan_refactor_contracts.py` now hard-fails if the known stale-doc
  authority banners disappear.

Removed paths:

- Removed the unguarded interpretation path where older `SHIP`, build,
  schema, passive-tracking, AI, provider, or insight wording could be mistaken
  for current freeze-closure permission.

Parked paths:

- No old roadmap, handoff, deadline, academic, provider, simulation, insight,
  passive tracking, OpenClaw/GPT, or behavior-equation proposal is promoted.
- Rebrand/domain migration remains parked for a separate plan.

Moved authority:

- No implementation authority moved.
- Current authority remains with `docs/AUTHORITY.md`,
  `docs/current_transition_state.md`, `docs/operator_dashboard_contract.md`,
  `docs/runbooks/post_wave_dogfood_loop.md`, and the active contracts named
  there.
- Historical/subordinate docs remain context only.

Issue and classification:

- GitHub issue:
  #170 tracks the stale-doc documentation/authority bug.
- Classification:
  documentation bug plus authority bug, behavior-preserving.

Tests and verification:

- Static proof:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors --pretty`
  passed with `error_count=0`.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0`.
- Formatting proof:
  `git diff --check` passed.
- Operator read-only browser proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology local`
  passed with artifact
  `tmp/operator-readonly-stress-2026-07-08T09-41-23-835Z/result.json`,
  `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/r5a-stale-planning-authority-0e9e827.json` passed for
  commit `0e9e827647122bffa2bfcfb1b1d2434427cdf85b` on GitHub Actions run
  `28933136782`.

Behavior parity statement:

- No runtime product behavior, API shape, schema, exposure row, provider row,
  Redis key, user content, or public route changed.

Rollback note:

- Revert this docs/static-scan seam commit only. That restores the prior stale
  doc wording and removes the R5a stale-doc banner guard. No runtime state or
  production data is touched.

## R3 Frontend Extraction - NewTask Submit Controller

Commit:
95d791fc91033b761c552bede5eaf39e72566281

Changed authority:

- NewTask create submission now has a small controller boundary:
  `frontend/components/use-new-task-submit-controller.ts`.
- The controller owns shared create-payload assembly for normal create,
  soft-conflict force-create, and paused-task interruption-create paths.
- The controller now owns per-mode idempotency keys plus a same-payload
  in-flight lock so duplicate gestures cannot race two independent create
  requests before React `submitting` state lands.
- `frontend/lib/tasks.ts` now accepts an explicit `idempotencyKey` for
  `/v1/create` requests.
- The Holmesberg product-loop browser verifier now captures redacted
  `/v1/create` payloads and asserts NewTask description, deadline binding,
  force mode, and idempotency headers from browser behavior plus backend state.

Removed paths:

- Removed duplicated create-payload assembly from `NewTaskModal` for normal,
  force, and interruption create branches.
- Removed the hidden drift where normal create carried description/deadline
  fields but force/interruption branches could diverge during future edits.
- Removed the duplicate-mutation path where same-tick double-clicks on Create
  could create two backend tasks before UI pending state took effect.

Parked paths:

- Full `NewTaskModal` extraction remains incomplete. Draft-state,
  deadline-preview, edit-mode, and interruption UX decomposition remain parked
  for later R3 seams.
- Full isolated interruption-create browser proof remains parked until the
  timer/interruption branch is run as its own seam. The shared controller path
  is covered by code/typecheck, but this seam's browser proof targets normal
  and force create because those are the branches touched by the immediate
  duplicate-mutation finding.
- Hosted-public mutable dogfood remains parked/high-care until hosted cleanup
  proof is explicitly allowed.

Moved authority:

- No backend mutation authority moved.
- `/v1/create` remains the canonical task creation authority.
- NewTask UI still owns modal state and conflict presentation; the new
  controller only owns create submission assembly/idempotency.
- Deadline binding authority remains explicit user binding through the NewTask
  modal and backend deadline validation.

Issue and classification:

- GitHub issue:
  #171 tracks the NewTask create-path drift and idempotency product bug.
- Verifier classifications:
  - first local browser failure was topology/runtime: stale local port-3000
    frontend returned 500 for NextAuth session resolution. Fixed by restarting
    only the local Windows frontend verification process.
  - second local browser failure was a product bug: double-clicking Create
    created two backend tasks with the same title. Fixed with controller-level
    same-payload in-flight locking.

Tests and verification:

- Frontend typecheck:
  `cd frontend; npm run typecheck`; passed.
- Frontend production build:
  `cd frontend; npm run build`; passed after the in-flight lock patch.
- Backend characterization subset:
  `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_idempotency_user_scope.py tests\test_create_task_with_deadline.py tests\test_parse_deadline_preview.py tests\test_calibration_nudge_event.py tests\test_output_surfaces.py -q`;
  passed with `73 passed`.
- Static proof:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors --pretty`
  passed with `error_count=0`.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0`.
- Formatting/syntax proof:
  `git diff --check` and
  `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs`;
  passed.
- Failing mutable browser proof preserved as product-bug evidence:
  `tmp/browser-product-loop/r3-new-task-submit-controller/result.json`
  failed on `normal submit branch creates exactly one backend task` with two
  backend task ids for one title.
- Passing Holmesberg mutable browser proof:
  `tmp/browser-product-loop/r3-new-task-submit-controller-rerun1/result.json`
  passed with `ok=true`.
- Operator read-only browser proof after mutable pass:
  `tmp/operator-readonly-stress-2026-07-08T10-16-17-140Z/result.json`
  passed with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/r3-new-task-submit-controller-95d791f.json` passed for
  commit `95d791fc91033b761c552bede5eaf39e72566281` on GitHub Actions run
  `28935287814`.
- Proven paths:
  normal NewTask create preserves description and explicit deadline binding;
  normal duplicate gesture creates exactly one backend task; normal create
  carries an idempotency header; forced create after overlap preserves
  description and deadline binding; forced create carries force=true and an
  idempotency header; Holmesberg cleanup leaves no active timer and no
  unrendered synthetic creation-nudge exposure debt.

Behavior parity statement:

- User-visible NewTask behavior is intended to stay the same for valid normal,
  soft-conflict, and interruption create flows.
- The intended behavior change is narrower than the UI: duplicate same-payload
  create gestures collapse to one in-flight request instead of creating
  duplicate tasks.
- No schema, backend API shape, provider row, exposure row, Redis key, or
  production data repair changed.

Rollback note:

- Revert this seam commit only. That restores `NewTaskModal`'s previous inline
  create logic and removes the new browser payload/idempotency assertions. No
  schema migration, production data repair, provider data, exposure ledger row,
  Redis key, or user account content is required for rollback.

## S1c/R3 Backend - Create Idempotency Reservation

Commit:
29981de68e9abc0d52470fe56f38881e4c210823

Changed authority:

- `/v1/create` now atomically reserves task-create idempotency keys before
  entering task mutation authority.
- `RedisClient` now owns three explicit idempotency helpers:
  `reserve_idempotency`, `is_idempotency_pending`, and `clear_idempotency`.
- Duplicate same-key create requests now wait briefly for the first request's
  completed response and return that response when available.
- If a same-key duplicate remains pending after the short wait, `/v1/create`
  returns `409 idempotency_in_progress` instead of attempting a second write.
- Conflict responses are now cached under the idempotency key too, so repeated
  client retries replay the same conflict outcome instead of recomputing a new
  branch.

Removed paths:

- Removed the check-then-set race where two concurrent `/v1/create` requests
  with the same idempotency key could both pass the initial cache miss and write
  independently.
- Removed the replay gap where a cached conflict branch could be recomputed on
  retry instead of returning the original bounded response.

Parked paths:

- Full distributed-lock/general idempotency middleware remains parked. This seam
  deliberately protects only the task-create mutation path with the observed
  product risk.
- Hosted-public mutable dogfood remains parked/high-care until hosted cleanup
  proof is explicitly safe.
- Automatic recovery for stale local Next dev-cache topology failures remains
  open in GitHub issue #173.

Moved authority:

- No task lifecycle truth authority moved. `TaskManager` still owns task
  creation semantics; `/v1/create` owns request admission and response caching.
- Redis remains transport/cache authority for idempotency state only.
- No schema, provider, exposure, deadline, or user-data authority changed.

Issue and classification:

- GitHub issue #172 tracks the create endpoint idempotency race.
- Classification: product/runtime mutation bug with measurable duplicate-write
  risk.
- A separate verifier/topology issue was discovered while proving this seam:
  GitHub issue #173 tracks local `/api/topology` failures caused by stale Next
  dev cache artifacts. It is open because only the manual `dev:clean` recovery
  path was used in this pass.

Tests and verification:

- Backend characterization subset:
  `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_idempotency_user_scope.py tests\test_create_task_with_deadline.py tests\test_parse_deadline_preview.py tests\test_calibration_nudge_event.py tests\test_output_surfaces.py -q`;
  passed with `75 passed`.
- New backend tests:
  `test_create_pending_idempotency_key_rejects_duplicate_without_write` and
  `test_create_conflict_response_is_idempotently_replayed`.
- Static proof:
  `.venv311\Scripts\python.exe scripts\scan_refactor_contracts.py --fail-on-errors --pretty`
  passed with `error_count=0`.
- Authority scan:
  `.venv311\Scripts\python.exe scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`
  passed with `missing_owner_count=0` and `worker_write_drift_count=0`.
- Formatting proof:
  `git diff --check` passed.
- Local service proof:
  rebuilt backend with `docker compose up -d --build backend`, ran
  `docker compose exec -T backend alembic upgrade head`, and verified
  `http://localhost:8000/v1/health` returned `{"status":"ok","service":"lyraos-api"}`.
- Initial operator proof exposed a topology/verifier failure before product
  behavior was reached: local `/api/topology` returned `500` from stale Next dev
  cache artifacts. Recovery used the existing `frontend` `npm run dev:clean`
  path and reran the same verifier.
- Operator read-only browser proof before Holmesberg mutable pass:
  `tmp/operator-readonly-stress-2026-07-08T10-34-15-885Z/result.json`
  passed with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Holmesberg mutable product-loop proof:
  `tmp/browser-product-loop/r3-create-idempotency-reserve/result.json` passed
  with `ok=true`, `115` checks, no failed checks, normal and forced NewTask
  create idempotency headers, duplicate-gesture create collapsed to one backend
  task, deadline binding preserved, timer/session/export/delta evidence present,
  and cleanup leaving no active timer or unrendered synthetic creation-nudge
  exposure debt.
- Operator read-only browser proof after Holmesberg mutable pass:
  `tmp/operator-readonly-stress-2026-07-08T10-41-15-168Z/result.json`
  passed with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/create-idempotency-reserve-29981de.json` passed for commit
  `29981de68e9abc0d52470fe56f38881e4c210823` on GitHub Actions run
  `28936612112`.

Behavior parity statement:

- Valid task creation, soft-conflict responses, force-create, deadline binding,
  exposure lifecycle, provider rows, and user-facing NewTask behavior remain
  behavior-preserving.
- The intended runtime behavior change is narrow: a duplicate same-key
  in-flight create request is serialized/replayed or rejected as pending instead
  of being allowed to race a second write.
- Unknown failures after mutation has been attempted fail closed by leaving the
  short-lived pending reservation until TTL expiry, rather than clearing it and
  risking duplicate task creation.

Rollback note:

- Revert commit `29981de68e9abc0d52470fe56f38881e4c210823` only. That restores
  previous `/v1/create` check-then-set idempotency behavior and removes the new
  Redis reservation helpers and tests. No schema migration, production data
  repair, provider rows, exposure rows, or user-data cleanup are required.

## S1c Verifier Hardening - Local Topology Failure Classification

Commit:
717933ad5f7cb9561a6fdc55a93dbc12d6f43b01

Changed authority:

- `scripts/verify_runtime_topology.mjs` now classifies local frontend
  `/api/topology` 500s as verifier/topology failures when they happen before
  product behavior is reached.
- The verifier now emits structured endpoint failure details: classification,
  topology, endpoint, URL, HTTP status, response excerpt, likely cause, detected
  stale Next cache signals, suggested recovery, and local frontend log tails.
- Local Next dev cache signatures such as `.next`, `ENOENT`,
  `app-paths-manifest.json`, and `_buildManifest.js.tmp` are surfaced as
  diagnostic evidence instead of collapsing to `detail: 500`.

Removed paths:

- Removed the ambiguous failure mode where a local topology endpoint 500 could
  be mistaken for a product invariant failure during operator/browser proof.

Parked paths:

- Automatic frontend restart/recovery remains parked. The verifier now gives
  the correct classification and recovery command, but it does not mutate local
  process state.
- Public topology failures remain classified as topology/deployment failures;
  this seam does not add public deployment remediation.

Moved authority:

- No runtime, app, task, exposure, provider, user-data, or deployment authority
  moved.
- Browser proof authority remains in the existing operator/Holmesberg
  verification scripts; this seam only improves preflight evidence quality.

Issue and classification:

- GitHub issue #173 tracks the local topology verifier stale Next cache failure.
- Classification: verifier/topology bug.
- Root evidence from the preceding failed proof: local `/api/topology` returned
  `500` and frontend logs contained stale `.next` `ENOENT` artifacts. A clean
  dev restart restored the same verifier.

Tests and verification:

- Syntax proof:
  `node --check scripts/verify_runtime_topology.mjs`; passed.
- Happy-path topology proof:
  `node scripts/verify_runtime_topology.mjs --topology local --skip-browser`;
  passed with local frontend/backend build IDs as `dev`.
- Formatting proof:
  `git diff --check`; passed.
- Operator wrapper proof:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology local`;
  passed and produced
  `tmp/operator-readonly-stress-2026-07-08T10-51-03-758Z/result.json` with
  `count_diffs=[]`, `route_count_diffs=[]`, `dashboard_snapshot_diffs=[]`,
  `implementation_green=true`, and `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/topology-diagnostics-717933a.json` passed for commit
  `717933ad5f7cb9561a6fdc55a93dbc12d6f43b01` on GitHub Actions run
  `28937101779`.

Behavior parity statement:

- No product runtime behavior changed.
- No schema, API contract, frontend route, user-facing page, exposure row,
  provider row, Redis runtime key, or production data changed.
- The intended behavior change is limited to verifier failure reporting:
  evidence beats screenshots, and topology failures are classified before
  product invariants are judged.

Rollback note:

- Revert commit `717933ad5f7cb9561a6fdc55a93dbc12d6f43b01` only. That restores
  the previous concise topology verifier errors. No runtime state, local cache,
  production data, schema, or browser cookie state is affected.

## S1c Verifier Hardening - Post-Wave Evidence Manifest

Commit:
fade1399671c57f2389e2fa3624574e344542b57

Changed authority:

- `scripts/run_post_wave_dogfood_loop.ps1` now emits a top-level
  `evidence_manifest` inside each post-wave `summary.json`.
- `scripts/verify_runtime_topology.mjs` now accepts `--out-file` and writes a
  structured topology proof artifact while preserving existing stdout/stderr.
- The manifest lifts nested browser proof signals into one standard packet:
  topology proof, frontend/backend build IDs, nested issues, nested warnings,
  route warnings, operator read-only invariants, and Holmesberg cleanup status
  when mutable verification is requested.

Removed paths:

- Removed the need to manually inspect scattered transcripts and nested browser
  artifacts before knowing whether a standard wave proof passed.
- Removed the ambiguous state where topology proof existed only as console
  output and could be lost outside the transcript.

Parked paths:

- Count-diff row-level attribution remains parked and is tracked in GitHub issue
  #175.
- Local/public Next artifact isolation remains open under GitHub issue #144.
- The manifest does not auto-repair production data, restart topology, or run
  mutable hosted-public dogfood.

Moved authority:

- No runtime product, task, exposure, provider, user-data, schema, or deployment
  authority moved.
- Verification proof authority became more explicit: standard wave proof now has
  a single evidence packet instead of relying on screenshots or scattered logs.

Issue and classification:

- GitHub issue #174 tracks this seam.
- Classification: verifier/harness hardening.
- During validation, a hosted-public stale Next chunk incident was discovered
  and recorded on GitHub issue #144. Operational repair rebuilt the WSL public
  frontend to build `bfca848`; structural local/public artifact isolation remains
  open.
- A non-reproducing public operator count-diff failure was preserved as evidence
  in `tmp/operator-readonly-stress-2026-07-08T11-18-53-601Z/result.json`.
  Follow-up API isolation and full read-only rerun passed, and issue #175 tracks
  row-level attribution for future count diffs.

Tests and verification:

- Syntax proof:
  `node --check scripts\verify_runtime_topology.mjs`; passed.
- Parser proof:
  PowerShell parser check for `scripts\run_post_wave_dogfood_loop.ps1`; passed.
- Formatting proof:
  `git diff --check`; passed.
- Topology proof file smoke:
  `node scripts\verify_runtime_topology.mjs --topology local --skip-browser --out-file tmp\topology-preflight-local-manifest-test.json`;
  passed and wrote a structured `topology_verified` artifact.
- Standard local post-wave proof:
  `tmp/post-wave-dogfood/20260708-140924-s1c-verifier-manifest-v2-standard-local/summary.json`
  passed with `evidence_manifest.ok=true`,
  `classification=standard_wave_proof_passed`,
  `implementation_green=true`, `exposure_without_render_count=0`, no nested
  issues, no nested warnings, and cleanup marked not required.
- Hosted-public topology repair proof after the stale chunk incident:
  `tmp/topology-public-after-frontend-restart.json`; passed with public build
  `bfca848`.
- Hosted-public multi-account smoke after repair:
  operator and Holmesberg both resolved successfully on public topology.
- Hosted-public operator read-only rerun after repair:
  `tmp/operator-readonly-stress-2026-07-08T11-26-30-058Z/result.json`; passed
  with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/post-wave-evidence-manifest-fade139.json` passed for commit
  `fade1399671c57f2389e2fa3624574e344542b57` on GitHub Actions run
  `28939196484`.

Behavior parity statement:

- No product runtime behavior changed.
- No schema, API response contract, frontend route, user-facing page, exposure
  row, provider row, Redis runtime key, or production data repair changed.
- The intended behavior change is limited to verifier evidence packaging:
  evidence beats screenshots, and a wave proof now names topology, operator,
  cleanup, warnings, issues, and CI/CD evidence in one place.

Rollback note:

- Revert commit `fade1399671c57f2389e2fa3624574e344542b57` only. That restores
  the previous scattered proof artifacts and topology stdout-only behavior. No
  runtime state, production data, schema, cache, cookie, or deployment rollback
  is required.

## S1c Topology Guard - Local/Public Next Artifact Isolation

Commit:
828475d90a64e55b264167a1548241ff14f64c96

Changed authority:

- `scripts/run_s1c_verification_stack.ps1` now refuses local-topology frontend
  artifact mutation while the WSL hosted-public frontend tmux session
  `lyra-frontend` is running.
- The guarded mutation surfaces are:
  - local topology `frontend production build`;
  - local topology `local frontend dev restart after build`.
- An explicit override exists for intentional local proof:
  `-AllowPublicFrontendArtifactMutation` or
  `LYRA_ALLOW_LOCAL_FRONTEND_WHILE_PUBLIC=1`.

Removed paths:

- Removed the default path where a local S1c verifier run could silently mutate
  `frontend/.next` while hosted public was serving that same artifact tree.
- Removed the default path that produced hosted-public `_next` chunk `400`s and
  browser `ChunkLoadError` after local verifier/build work.

Parked paths:

- Full physical build isolation remains open under GitHub issue #144.
- Local-current alternate port topology drift remains open under GitHub issue
  #147.
- This guard does not split worktrees, add a separate Next `distDir`, or restart
  public automatically after an override.

Moved authority:

- No product runtime, task, exposure, provider, user-data, schema, or deployment
  authority moved.
- Local frontend artifact mutation is now an explicit operator action when the
  hosted-public frontend is active, not an accidental verifier side effect.

Issue and classification:

- GitHub issue #144 tracks the underlying local/public Next artifact hazard.
- Classification: topology/verifier guardrail.
- Discovery evidence: hosted public served stale/mismatched Next static chunks
  on 2026-07-08 until the WSL public frontend was rebuilt to build `bfca848`.

Tests and verification:

- Parser proof:
  PowerShell parser check for `scripts\run_s1c_verification_stack.ps1`; passed.
- Formatting proof:
  `git diff --check`; passed.
- Active public-session proof:
  `wsl.exe -e bash -lc "tmux has-session -t lyra-frontend ..."` reported
  `public_frontend_session=active`, confirming the guard protects a live
  hosted-public frontend.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/local-public-artifact-guard-828475d.json` passed for commit
  `828475d90a64e55b264167a1548241ff14f64c96` on GitHub Actions run
  `28939713882`.
- Hosted-public operator read-only proof after the guard:
  `tmp/operator-readonly-stress-2026-07-08T11-42-29-052Z/result.json`; passed
  with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No app behavior changed for users.
- No schema, API contract, frontend component, provider row, exposure row,
  Redis key, production data repair, or public restart command changed.
- The intended behavior change is verifier-only: local S1c runs fail closed
  instead of risking hosted-public static asset corruption.

Rollback note:

- Revert commit `828475d90a64e55b264167a1548241ff14f64c96` only. That restores
  the previous local S1c behavior where local frontend builds/dev restarts could
  proceed while hosted-public WSL frontend was active. No production data,
  schema, cookie, Redis, or deployment rollback is required.

## S1c Verifier Attribution - Operator Read-Only Count Diffs

Commit:
a81a202388d4ed397af7b0ca15b50dac3b49216c

Changed authority:

- `scripts/browser_stress_operator_readonly.mjs` now packages redacted
  row-level attribution whenever exported section counts change during an
  operator read-only proof.
- Attribution is attached for:
  - pre-dashboard API count diffs;
  - per-route browser count diffs;
  - final before/after count diffs.
- Screenshots remain contextual evidence only. Count-diff proof now includes
  backend export evidence sufficient to classify the likely source of a future
  drift.

Removed paths:

- Removed the evidence gap where a read-only stress failure could report
  `exposure_decision_events` or `exposure_render_events` count movement without
  showing which redacted rows were added or removed.
- Removed the need to reconstruct future count-diff incidents manually from
  separate exports after the fact.

Parked paths:

- This does not change operator runtime behavior or prove a previous transient
  count-diff cause.
- Root cause of the 2026-07-08 transient count-diff remains unknown unless it
  recurs; future failure artifacts should now include attribution sufficient to
  classify it.

Moved authority:

- No product runtime, task, exposure, provider, user-data, schema, deployment,
  or operator dashboard authority moved.
- Verifier evidence authority moved from count-only reports toward redacted
  row-level backend evidence.

Issue and classification:

- GitHub issue #175 tracks this seam.
- Classification: verifier/harness hardening and measurement integrity.
- Triggering incident:
  `tmp/operator-readonly-stress-2026-07-08T11-18-53-601Z/result.json`
  reported a transient pre-route count diff that could not be attributed from
  the artifact alone.

Tests and verification:

- Syntax proof:
  `node --check scripts\browser_stress_operator_readonly.mjs`; passed.
- Harness self-test:
  `node scripts\browser_stress_operator_readonly.mjs --self-test-attribution`;
  passed, proving added-row detection and redaction of non-allowlisted message
  content.
- Formatting proof:
  `git diff --check`; passed.
- Hosted-public operator read-only proof:
  `tmp/operator-readonly-stress-2026-07-08T11-51-07-523Z/result.json`; passed
  with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/operator-readonly-attribution-a81a202.json`; passed for
  commit `a81a202388d4ed397af7b0ca15b50dac3b49216c` on GitHub Actions run
  `28940508011`.

Behavior parity statement:

- No app behavior changed for users.
- No schema, API contract, operator dashboard response, frontend route,
  exposure row, notification row, provider row, Redis key, production repair, or
  deployment behavior changed.
- The intended behavior change is verifier-only: failed read-only proofs become
  more attributable and less likely to overclaim causality.

Rollback note:

- Revert commit `a81a202388d4ed397af7b0ca15b50dac3b49216c` only. That restores
  count-only read-only stress artifacts. No production data, schema, Redis,
  cookie, or deployment rollback is required.

## S1c Topology Guard - Shared Local Frontend Authority

Commit:
117d37a9dd16ea935f4f316faa0491bf0916d254

Changed authority:

- Local frontend topology establishment now lives in
  `scripts/local_frontend_topology.ps1`.
- `scripts/run_s1c_verification_stack.ps1` and
  `scripts/run_operator_readonly_browser_stress.ps1` use the same local
  frontend restart and local/public artifact guard.
- Direct local operator read-only stress now attempts to establish verified
  local topology before browser assertions unless
  `-AssumeLocalFrontendReady` is explicitly passed.

Removed paths:

- Removed duplicated local frontend restart logic from the S1c stack.
- Removed the path where direct local operator read-only stress could treat a
  stale `localhost:3000` listener as valid evidence.
- Removed the path where local operator stress had weaker artifact-isolation
  semantics than the S1c wrapper.

Parked paths:

- Full physical local/public Next artifact isolation remains open under GitHub
  issue #144.
- Direct local operator stress still fails closed rather than mutating local
  frontend artifacts when the WSL hosted-public frontend session
  `lyra-frontend` is active, unless explicitly overridden.

Moved authority:

- No product runtime, task, exposure, provider, user-data, schema, deployment,
  or operator dashboard authority moved.
- Local frontend topology readiness moved from duplicated wrapper code into a
  shared verifier helper.

Issue and classification:

- GitHub issue #166 tracks this seam.
- Classification: verifier/topology bug.
- Triggering symptom: direct
  `scripts\run_operator_readonly_browser_stress.ps1 -Topology local` could be
  misled by stale Windows `localhost:3000` ownership.

Tests and verification:

- Parser proof:
  PowerShell parser check passed for:
  - `scripts\local_frontend_topology.ps1`;
  - `scripts\run_s1c_verification_stack.ps1`;
  - `scripts\run_operator_readonly_browser_stress.ps1`.
- Fail-closed local proof:
  direct local operator stress refused to mutate local frontend artifacts while
  WSL public frontend session `lyra-frontend` was active, with reason
  `operator read-only local topology proof`.
- S1c no-browser local smoke:
  `scripts\run_s1c_verification_stack.ps1 -Topology local -SkipBackendFull -SkipFrontendBuild -SkipBrowser`;
  passed.
- Formatting proof:
  `git diff --check`; passed.
- Hosted-public operator read-only proof:
  `tmp/operator-readonly-stress-2026-07-08T12-02-04-588Z/result.json`; passed
  with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`, and
  `exposure_without_render_count=0`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/local-frontend-topology-guard-117d37a.json`; passed for
  commit `117d37a9dd16ea935f4f316faa0491bf0916d254` on GitHub Actions run
  `28941149262`.

Behavior parity statement:

- No app behavior changed for users.
- No schema, API contract, operator dashboard response, frontend route,
  exposure row, notification row, provider row, Redis key, production repair, or
  deployment behavior changed.
- The intended behavior change is verifier-only: local operator read-only proof
  now shares the same topology establishment and fail-closed artifact guard as
  S1c.

Rollback note:

- Revert commit `117d37a9dd16ea935f4f316faa0491bf0916d254` only. That restores
  duplicated S1c local frontend helper code and returns direct local operator
  stress to assuming its local frontend is already valid. No production data,
  schema, Redis, cookie, or deployment rollback is required.

## Hosted Public Next Artifact Isolation

Commit:
bbd168cc8721950950a6af0ca3e97e410c83cc10

Changed authority:

- Hosted-public frontend builds now use `NEXT_DIST_DIR=.next-public` through
  `frontend/scripts/public-topology.mjs`.
- `frontend/next.config.mjs` accepts `NEXT_DIST_DIR`, defaulting local builds
  to `.next` and public builds to `.next-public`.
- `scripts/restart_frontend_wsl.ps1` and
  `scripts/start_public_after_reboot.ps1` rebuild and validate
  `.next-public/BUILD_ID` before starting `start:public`.
- Local/frontend artifact guards now allow local `.next` mutation while the WSL
  public tmux session is active only when `.next-public` isolation is proven.
- Git hygiene and S1c static scans ignore `.next-public` as generated artifact
  output.

Removed paths:

- Removed the hosted-public path where a local `npm run build` could rewrite
  the same `.next` artifact tree that public `next start` was serving.
- Removed stale runbook wording that described public recovery as rebuilding
  `.next`.

Parked paths:

- Local-current alternate-port verifier isolation remains a separate topology
  hardening surface.
- Cloudflare immutable asset cache remains external state; served HTML asset
  graph proof is required after public restarts.

Moved authority:

- Public frontend artifact ownership moved from implicit Next default `.next`
  to the explicit public topology wrapper plus WSL restart scripts.
- No task, deadline, timer, exposure, provider, user-data, schema, backend, or
  ClaimCompiler authority moved.

Issue and classification:

- GitHub issue #144 tracks this seam.
- Classification: topology/deployment bug with verifier impact.
- Triggering symptom: hosted-public `_next` chunk `400`/`ChunkLoadError` risk
  when local verification/builds and hosted public shared the same `.next`
  artifact family.

Tests and verification:

- Parser proof:
  PowerShell parser check passed for:
  - `scripts\local_frontend_topology.ps1`;
  - `scripts\restart_frontend_wsl.ps1`;
  - `scripts\start_public_after_reboot.ps1`;
  - `scripts\run_s1c_verification_stack.ps1`;
  - `scripts\git_hygiene_summary.ps1`.
- Node/Python syntax proof:
  - `node --check frontend\scripts\public-topology.mjs`; passed.
  - `.venv311\Scripts\python.exe -m py_compile
    scripts\scan_authority_surfaces.py scripts\scan_refactor_contracts.py`;
    passed.
- S1c partial gate:
  `powershell -NoProfile -ExecutionPolicy Bypass -File
  .\scripts\run_s1c_verification_stack.ps1 -Topology local -SkipBackendFull
  -SkipBrowser`; passed, including authority scans, refactor contract scan,
  OpenClaw relay hermetic test, Alembic fresh DB smoke, and local frontend
  production build while hosted public was active and isolated.
- Hosted-public restart proof:
  `scripts\restart_frontend_wsl.ps1`; rebuilt `.next-public`, started the WSL
  `lyra-frontend` tmux session, and public `/api/topology` reported
  `frontend_build_id=bbd168c`.
- Hosted-public topology proof:
  `tmp/topology-public-bbd168c.json`; passed with
  `verified_topology=true`, frontend build `bbd168c`, and backend build `dev`.
- Hosted-public chunk graph proof:
  `tmp/public-chunk-proof/bbd168c-2026-07-08T12-29-51-976Z.json`; passed with
  homepage status `200`, all `14` served `_next/static` assets status `200`,
  and the user-reported console chunk
  `/_next/static/chunks/434-0e9fd793188923f4.js` status `200`.
- Hosted-public operator read-only proof:
  `tmp/operator-readonly-stress-2026-07-08T12-30-37-560Z/result.json`; passed
  with `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`,
  `exposure_without_render_count=0`, and no operator read mutations.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/public-next-distdir-bbd168c.json`; passed for commit
  `bbd168cc8721950950a6af0ca3e97e410c83cc10` on GitHub Actions run
  `28942846394`.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No schema, backend API contract, operator dashboard response, task/deadline
  state, timer state, exposure row, notification row, provider row, Redis key,
  production data repair, or ClaimCompiler behavior changed.
- Intended behavior change is deployment/verifier safety only: public builds
  have a separate artifact directory, local builds stop corrupting hosted-public
  chunks, and local guard behavior is evidence-based instead of blanket
  blocking.

Rollback note:

- Revert commit `bbd168cc8721950950a6af0ca3e97e410c83cc10`, then run
  `powershell -NoProfile -ExecutionPolicy Bypass -File
  .\scripts\restart_frontend_wsl.ps1` to rebuild the public frontend using the
  previous artifact path.
- No production data, schema, Redis, cookie, or backend rollback is required.

## Local-Current Topology Verifier Mode

Commit:
f283db05eb49031ea587147ebc0fbe1336789d57

Changed authority:

- `scripts/verify_runtime_topology.mjs` now supports explicit
  `--topology local-current` proofs with caller-supplied `--frontend`, `--api`,
  `--nextauth`, and optional `--proxy-api`.
- `local-current` is verifier-only. It accepts only localhost/127.0.0.1 origins
  and does not weaken canonical `local` or hosted `public` topology checks.
- `scripts/run_operator_readonly_browser_stress.ps1` and
  `scripts/run_multi_account_browser_smoke.ps1` can now run against
  `local-current` on an explicit port, defaulting to `3013`.
- `scripts/local_frontend_topology.ps1` can start and verify local-current dev
  servers whose frontend/API/NextAuth fields match the requested alternate
  port.
- `scripts/run_s1c_verification_stack.ps1` can pass local-current topology and
  port settings through to reusable browser gates.

Removed paths:

- Removed the path where alternate current-code browser proofs had to be
  described as canonical `local` or as unmanaged ad hoc overrides.
- Removed the path where `localhost:3013` with correct local API/auth fields
  was automatically classified as unusable `mixed` evidence.

Parked paths:

- Direct non-proxied browser API calls from arbitrary local-current ports remain
  parked unless backend CORS explicitly includes those ports.
- This does not create a production topology and does not add new public CORS
  origins.

Moved authority:

- Local-current topology interpretation moved into verifier scripts.
- Runtime topology authority remains with `runtime_topology.json`, frontend
  `/api/topology`, backend `/v1/health/topology`, and the public/local
  contracts.
- No product runtime, task, deadline, timer, exposure, provider, schema, Redis,
  deployment, or ClaimCompiler authority moved.

Issue and classification:

- GitHub issue #147 tracks this seam.
- Classification: verifier/topology bug.
- Triggering symptom: approved alternate local-current browser ports were
  indistinguishable from accidental mixed topology.

Tests and verification:

- Parser and syntax proof:
  - `node --check scripts\verify_runtime_topology.mjs`; passed.
  - PowerShell parser check passed for:
    `scripts\local_frontend_topology.ps1`,
    `scripts\run_operator_readonly_browser_stress.ps1`,
    `scripts\run_multi_account_browser_smoke.ps1`, and
    `scripts\run_s1c_verification_stack.ps1`.
  - `git diff --check`; passed.
- Local-current topology proof:
  `tmp/topology-local-current-3013.json`; passed for
  `frontend=http://localhost:3013`, `api=http://localhost:8000`,
  `nextauth=http://localhost:3013`, and `proxy_api=true`.
- Negative safety proof:
  `tmp/topology-local-current-3013-negative.json`; failed as expected when
  `--nextauth http://localhost:3000` was supplied against frontend
  `http://localhost:3013`.
- Local-current operator read-only proof:
  `tmp/operator-readonly-stress-2026-07-08T12-43-57-239Z/result.json`; passed
  with `proxy_api=true`, `count_diffs=[]`, `route_count_diffs=[]`,
  `dashboard_snapshot_diffs=[]`, `implementation_green=true`,
  `exposure_without_render_count=0`, desktop `/operator` `6841ms`, and mobile
  `/operator` `6150ms`.
- Local-current multi-account proof:
  `scripts\run_multi_account_browser_smoke.ps1 -Topology local-current
  -LocalCurrentPort 3013`; passed for the operator account and Holmesberg
  non-operator account.
- Cleanup proof:
  the temporary `localhost:3013` dev server was stopped after the proof.
- Public strictness proof:
  `tmp/topology-public-after-local-current-change.json`; passed for public
  topology with `--skip-browser`.
- S1c static/no-browser gate:
  `scripts\run_s1c_verification_stack.ps1 -Topology public -SkipBackendFull
  -SkipFrontendBuild -SkipBrowser`; passed.
- Hosted-public operator read-only proof after the script change:
  `tmp/operator-readonly-stress-2026-07-08T12-48-22-229Z/result.json`; passed
  with `count_diffs=[]`, `dashboard_snapshot_diffs=[]`,
  `implementation_green=true`, `exposure_without_render_count=0`, desktop
  `/operator` `8753ms`, and mobile `/operator` `5341ms`.
- Hosted CI/CD proof:
  `tmp/ci-cd-proof/local-current-topology-f283db0.json`; passed for commit
  `f283db05eb49031ea587147ebc0fbe1336789d57` on GitHub Actions run
  `28943906554`.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No schema, backend API behavior, operator dashboard payload, task/deadline
  state, timer state, exposure row, notification row, provider row, production
  data, Redis key, or deployment behavior changed.
- Intended behavior change is verifier-only: alternate current-code local
  browser proofs can be labeled, validated, proxied, and rejected when their
  auth/API fields do not match.

Rollback note:

- Revert commit `f283db05eb49031ea587147ebc0fbe1336789d57` only. That removes
  the explicit local-current verifier mode and returns alternate-port proofs to
  the previous ad hoc/proxy-only workflow.
- No production data, schema, Redis, cookie, backend, or hosted-public rollback
  is required.

## Deadline Suggestion Wait And Local-Current Wrapper Proof Split

Commits:

- `0ec08af2adc8b38f627833175316e9d5d56a02c4`
- `19aa7b315280743f5dc46cadf7067931f43eb343`

Changed authority:

- Deadline-suggestion browser proof now waits on a stable
  `new-task-deadline-suggestion` test id before falling back to text/role
  selectors.
- Local-current wrapper authority now flows through the reusable post-wave
  wrapper, Holmesberg mutable smoke wrapper, product-loop wrapper, and S1c
  wrapper instead of ad hoc caller overrides.
- The post-wave wrapper top-level result now mirrors the evidence manifest
  and fails if the manifest fails.

Removed paths:

- Removed a brittle one-shot deadline-suggestion visibility check that could
  misclassify a late render as missing.
- Removed the path where local-current wrapper runs had to pretend to be
  canonical `local` topology or bypass wrapper routing manually.
- Removed the path where a failed evidence manifest could be hidden behind a
  top-level wrapper success.

Parked paths:

- Full product-loop notification proof remains blocked by GitHub issue #176:
  the pending notification can disappear without the browser verifier proving
  render/dismiss/action/expiry evidence.
- Hosted-public mutable dogfood remains high-care and optional until public
  test-account cleanup is proven safe and a deploy/restart confirmation gate is
  explicitly satisfied.

Moved authority:

- No product runtime, schema, user-facing behavior, task/deadline/timer state,
  exposure authority, notification authority, provider authority, Redis state,
  deployment authority, or ClaimCompiler authority moved.
- Verifier topology plumbing moved into the reusable wrapper scripts.

Issues and classification:

- GitHub issue #149 tracked deadline suggestion render latency and is closed.
  Classification: verifier/browser wait bug.
- GitHub issue #177 tracked the post-wave wrapper evidence-manifest hard-fail
  bug and is closed. Classification: verifier/harness bug.
- GitHub issue #178 tracked local-current mutable smoke browser API proxy
  support and is closed. Classification: verifier/topology harness bug.
- GitHub issue #176 remains open for the notification lifecycle ambiguity.
  Classification: measurement/verifier boundary bug.

Tests and verification:

- Commit `0ec08af2adc8b38f627833175316e9d5d56a02c4`:
  - `node --check scripts\browser_holmesberg_product_loop_dogfood.mjs`;
    passed.
  - `git diff --check`; passed.
  - `frontend npm run typecheck`; passed.
  - Local-current Holmesberg product-loop evidence:
    `tmp\browser-product-loop\deadline-suggestion-wait-0ec08af\result.json`.
    The full loop failed later in notification proof, but deadline-suggestion
    checks passed at 1336ms, 1341ms, and 1519ms.
  - Cleanup-only proof:
    `tmp\browser-product-loop\cleanup-deadline-suggestion-wait-0ec08af\result.json`;
    passed with no active timer and no task rows under the dogfood prefix.
  - Operator read-only proof:
    `tmp\operator-readonly-stress-2026-07-08T15-15-36-449Z\result.json`;
    passed with zero count diffs, `implementation_green=true`, and
    `exposure_without_render_count=0`.
  - Hosted CI/CD proof: GitHub Actions `CI` run `28953929444`; passed.
- Commit `19aa7b315280743f5dc46cadf7067931f43eb343`:
  - `git diff --check`; passed.
  - `node --check scripts\browser_mutable_holmesberg_smoke.mjs`; passed.
  - PowerShell parser checks passed for touched wrapper scripts.
  - Direct local-current mutable proof:
    `tmp\browser-smoke\holmesberg-2026-07-08T15-24-39-578Z\result.json`;
    passed, created and cleaned three tasks and two deadlines, and exercised
    deadline creation, task binding, timer start/pause/resume/stop, parallel
    timer rejection, and brain dump commit.
  - Reusable wrapper local-current proof:
    `tmp\post-wave-dogfood\20260708-182108-wrapper-local-current-proof-quick-local-current\summary.json`;
    passed for topology, multi-account smoke, and operator read-only routing.
  - Reusable wrapper local-current mutable proof:
    `tmp\post-wave-dogfood\20260708-182542-wrapper-local-current-mutable-proof-standard-local-current\summary.json`;
    passed with `mutable_enabled=true`, `evidence_manifest.ok=true`, cleanup
    required and ok, operator read-only summaries ok, and
    `exposure_without_render_count=0`.
  - Hosted CI/CD proof: GitHub Actions `CI` run `28954961117`; passed.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No schema, backend API behavior, operator dashboard payload, task/deadline
  state, timer state, exposure row, notification row, provider row, production
  data, Redis key, public deploy path, or ClaimCompiler behavior changed.
- Intended behavior change is verifier-only: the browser waits on stable
  deadline-suggestion evidence; local-current wrapper proofs are explicit,
  proxied, and manifest-enforced.

Rollback note:

- Revert `19aa7b315280743f5dc46cadf7067931f43eb343` to remove local-current
  wrapper routing and restore the previous wrapper behavior.
- Revert `0ec08af2adc8b38f627833175316e9d5d56a02c4` to remove the stable
  deadline-suggestion test id and polling wait.
- No production data, schema, Redis, cookie, backend, hosted-public deploy, or
  user cleanup rollback is required.

## 2026-07-09 - Operator Readiness Split Wrapper Gate

Wave:

- Branch: `refactor/operator-s1c-hardening`.
- Previous checkpoint PR #180 merged at `3cfb9308d08fbae3b465271d940e474b8a646e57`.
- Seam: verifier-only operator cockpit gate hardening.

Changed authority:

- No product/runtime authority changed.
- The PowerShell operator read-only wrapper now requires the existing browser
  verifier to assert implementation/cohort readiness split labels on `/operator`.

Removed paths:

- Removed the path where wrapper-driven operator browser proof could pass
  without exercising the existing readiness-split label assertion.

Parked paths:

- No backend extraction, frontend extraction, schema work, rebrand/domain
  migration, public deploy/restart, or hosted-public mutable dogfood happened
  in this seam.

Moved authority:

- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, deployment, or ClaimCompiler authority moved.

Issues and classification:

- GitHub issue #176 is closed by commit
  `2f50aed5c37afb2f8074a050415b01e8eb98c3f2`; classification:
  measurement/verifier boundary bug.
- GitHub issue #179 is closed as a topology/deployment recovery with explicit
  hosted build lag; no code change was required.
- This seam did not create a new GitHub issue because it is proactive verifier
  hardening, not a discovered product or harness bug.

Tests and verification:

- `git diff --check`; passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology local-current -LocalCurrentPort 3013 -AssumeLocalFrontendReady -ProxyApi`;
  passed with `expect_readiness_split=true`, zero count diffs,
  `implementation_green=true`, and `exposure_without_render_count=0`.
- Artifact:
  `tmp\operator-readonly-stress-2026-07-09T13-48-49-250Z\result.json`.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No backend API behavior, frontend UI behavior, DB schema, production data,
  Redis state, hosted-public artifact, or public runtime changed.
- Intended behavior change is verifier-only: wrapper calls to operator
  read-only stress now fail if `/operator` drops the readiness split labels.

Rollback note:

- Revert commit `088178d` to remove the wrapper-level
  `--expect-readiness-split true` argument.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Readiness Projection Helper Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: backend read-only helper extraction for the operator stop/go cockpit.
- Commit: `78e1232d5215c86ce86eb8f4bb92ec7d36ebac4f`.

Changed authority:

- No product/runtime mutation authority changed.
- `/v1/operator/dashboard` still owns DB reads, dynamic issue construction, and
  response assembly.
- `operator_dashboard_metrics.py` now owns the pure cohort-readiness projection
  from dynamic issues, clean-trace ratios, timer closure rate, reliability, bug
  watchlist, and loop-volume evidence.

Removed paths:

- Removed duplicate inline implementation/cohort/readiness projection logic from
  the operator endpoint body.

Parked paths:

- Backend writer splits remain parked: task lifecycle, stopwatch finalizer,
  output render/suppression/outcome writers, auth/scoping, provider connection
  model, and `models.py` split.
- No schema migration, production data repair, public deploy/restart, hosted
  mutable dogfood, or rebrand/domain migration happened in this seam.

Moved authority:

- Pure read-only projection authority moved from the route body into
  `operator_dashboard_metrics.cohort_readiness_snapshot`.
- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, Redis, deployment, or ClaimCompiler authority moved.

Issues and classification:

- No GitHub issue was created because this was proactive backend extraction,
  not a discovered bug.
- Classification: product/runtime read-only refactor.

Tests and verification:

- `git diff --check`; passed.
- `python -m py_compile backend/app/api/v1/endpoints/operator.py backend/app/services/operator_dashboard_metrics.py`;
  passed.
- `PYTHONPATH=backend pytest backend/tests/test_operator_dashboard.py -q`;
  passed, 11 tests.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- Local-current operator read-only browser proof:
  `tmp/operator-readonly-stress-2026-07-09T14-36-10-138Z/result.json`; passed
  with zero count diffs, zero dashboard diffs, `implementation_green=true`,
  `cohort_status=yellow`, and `exposure_without_render_count=0`.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No backend API path, response contract, database query, DB write, schema,
  production data, Redis state, hosted-public artifact, or public runtime
  changed.
- The intended change is structural only: cohort-readiness stop/go projection
  is now a named read-only helper, making future operator extraction safer.

Rollback note:

- Revert commit `78e1232d5215c86ce86eb8f4bb92ec7d36ebac4f` to restore the
  inline operator endpoint projection.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Dynamic Issue Projection Helper Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: backend read-only helper extraction for operator dynamic issues.
- Commit: `d3b4cee6a87944e4290c200d7bd20eddf43084d6`.

Changed authority:

- No product/runtime mutation authority changed.
- `/v1/operator/dashboard` still owns DB reads and input snapshot assembly.
- `operator_dashboard_metrics.py` now owns the pure projection from already
  computed privacy, notification, state-invariant, measurement-integrity,
  freshness, product-loop, and provider-integrity snapshots into dynamic issue
  rows.

Removed paths:

- Removed the long inline dynamic-issue construction block from the operator
  endpoint body.

Parked paths:

- Backend writer extraction remains parked: task lifecycle, stopwatch finalizer,
  output render/suppression/outcome writers, auth/scoping, provider connection
  model, and `models.py` split.
- No schema migration, production data repair, public deploy/restart, hosted
  mutable dogfood, or rebrand/domain migration happened in this seam.

Moved authority:

- Pure read-only dynamic-issue projection moved from the route body into
  `operator_dashboard_metrics.operator_dynamic_issues_snapshot`.
- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, Redis, deployment, or ClaimCompiler authority moved.

Issues and classification:

- No GitHub issue was created because this was proactive backend extraction,
  not a discovered bug.
- Classification: product/runtime read-only refactor.

Tests and verification:

- `git diff --check`; passed.
- `python -m py_compile backend/app/api/v1/endpoints/operator.py backend/app/services/operator_dashboard_metrics.py`;
  passed.
- `PYTHONPATH=backend pytest backend/tests/test_operator_dashboard.py -q`;
  passed, 11 tests.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- Local-current operator read-only browser proof:
  `tmp/operator-readonly-stress-2026-07-09T14-43-43-781Z/result.json`; passed
  with zero count diffs, zero dashboard diffs, `implementation_green=true`,
  `cohort_status=yellow`, and `exposure_without_render_count=0`.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No backend API path, response contract, database query, DB write, schema,
  production data, Redis state, hosted-public artifact, or public runtime
  changed.
- The intended change is structural only: operator dynamic issue classification
  is now a named read-only helper, making the route thinner before deeper R4
  extraction.

Rollback note:

- Revert commit `d3b4cee6a87944e4290c200d7bd20eddf43084d6` to restore the
  inline operator endpoint dynamic issue construction.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Broad Refactor Branch CI Trigger

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: CI/CD proof-loop hardening for the broad freeze-closure refactor branch.
- Commit: `ae190761569bf6b97a53155798fb712f63731269`.

Changed authority:

- No product/runtime authority changed.
- GitHub Actions CI now auto-runs on pushes to the active
  `refactor/freeze-closure` branch, matching the user-approved broad-branch
  refactor workflow.

Removed paths:

- Removed the need to manually run `workflow_dispatch` after every pushed seam
  on this branch to obtain hosted CI proof.

Parked paths:

- Broad trigger expansion to all `refactor/**` branches remains parked to avoid
  unnecessary CI cost/noise.
- PR merge, release, public deploy/restart, public mutable dogfood, schema
  migration, and rebrand/domain migration remain blocked without approval.

Moved authority:

- CI proof authority for this branch moved from manual operator dispatch to the
  workflow push trigger.
- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, Redis, deployment, or ClaimCompiler authority moved.

Issues and classification:

- GitHub issue #182 tracks this CI/CD operations policy gap.
- Classification: CI/CD operations gap.

Tests and verification:

- `git diff --check`; passed.
- Push to `refactor/freeze-closure` automatically created GitHub Actions CI run
  `29026954028` with event `push` for exact head
  `ae190761569bf6b97a53155798fb712f63731269`.
- CI run `29026954028` passed:
  - backend tests;
  - frontend lint/typecheck and production build;
  - topology contract;
  - S1c static gates, including authority surface scan, refactor contract scan,
    OpenClaw relay hermetic test, and Alembic fresh database smoke.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No backend API behavior, frontend app behavior, DB schema, production data,
  Redis state, hosted-public artifact, or public runtime changed.
- Intended behavior change is CI/CD only: future pushes to the active broad
  refactor branch produce automatic hosted CI proof.

Rollback note:

- Revert commit `ae190761569bf6b97a53155798fb712f63731269` to remove the
  `refactor/freeze-closure` push trigger and return this branch to manual
  `workflow_dispatch` CI proof.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Deadline Shape Read-Only Service Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: backend read-only analytics helper extraction.
- Commit: `19c5c09dcea5c9a9e7776b3fb54a6aa108a41afd`.

Changed authority:

- No product mutation authority changed.
- `/v1/analytics/deadline-shape` remains the public API surface and still owns
  request scoping through `get_current_user_id()`.
- Deadline-shape query/projection implementation moved behind
  `deadline_shape_service.deadline_shape_snapshot`.

Removed paths:

- Removed inline deadline-shape query/projection code from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- Analytics claim-generation extraction remains parked.
- Exposure-writing analytics paths, task creation nudge lookup, output-surface
  writes, auth/scoping changes, schema changes, production repair, hosted
  mutable dogfood, public deploy/restart, and rebrand/domain migration remain
  blocked without approval.

Moved authority:

- Pure read-only deadline-shape computation moved from the route body into
  `backend/app/services/deadline_shape_service.py`.
- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, Redis, deployment, or ClaimCompiler authority moved.

Issues and classification:

- No GitHub issue was created because this was proactive backend extraction,
  not a discovered bug.
- Classification: product/runtime read-only refactor.

Tests and verification:

- `git diff --check`; passed.
- `python -m py_compile backend/app/api/v1/endpoints/analytics.py backend/app/services/deadline_shape_service.py`;
  passed.
- `PYTHONPATH=backend pytest backend/tests/test_analytics_deadline_shape.py -q`;
  passed, 10 tests.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- `/v1/analytics/deadline-shape` path, parameters, response shape, user
  scoping, voided-row filtering, dirty-stopwatch exclusion, corrected-task
  exclusion, external-source default, and Rule 14/15 aggregates are preserved.
- No DB write, schema, production data, Redis state, hosted-public artifact, or
  public runtime changed.

Rollback note:

- Revert commit `19c5c09dcea5c9a9e7776b3fb54a6aa108a41afd` to restore the
  inline deadline-shape computation in `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Deadline Completion Read-Only Service Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: backend read-only analytics helper extraction.
- Commit: `3cdbf88f618c2906cbe7d97be37a8a6b23d7b9e7`.

Changed authority:

- No product mutation authority changed.
- `/v1/analytics/deadline-completions` remains the public API surface and
  still owns request scoping through `get_current_user_id()`.
- Deadline completion event aggregation moved behind
  `deadline_completion_analytics_service.deadline_completion_snapshot`.

Removed paths:

- Removed inline deadline-completion query/projection code from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- Deadline authority remains with `DeadlineManager` and provider-aware deadline
  normalizers.
- Deadline completion events remain append-only completion/submission traces,
  not stopwatch execution truth.
- Writer extraction, schema changes, production repair, hosted mutable dogfood,
  public deploy/restart, and rebrand/domain migration remain blocked without
  approval.

Moved authority:

- Pure read-only deadline completion aggregation moved from the route body into
  `backend/app/services/deadline_completion_analytics_service.py`.
- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, Redis, deployment, or ClaimCompiler authority moved.

Issues and classification:

- No GitHub issue was created because this was proactive backend extraction,
  not a discovered bug.
- Classification: product/runtime read-only refactor.

Tests and verification:

- `git diff --check`; passed.
- `python -m py_compile backend/app/api/v1/endpoints/analytics.py backend/app/services/deadline_completion_analytics_service.py`;
  passed.
- `PYTHONPATH=backend pytest backend/tests/test_deadline_completion_events.py -q`;
  passed, 5 tests.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- `/v1/analytics/deadline-completions` path, parameters, response shape, user
  scoping, voided-row filtering, external-source default, behavior-count versus
  distinct-deadline split, and completion-trace-not-execution-truth semantics
  are preserved.
- No DB write, schema, production data, Redis state, hosted-public artifact, or
  public runtime changed.

Rollback note:

- Revert commit `3cdbf88f618c2906cbe7d97be37a8a6b23d7b9e7` to restore the
  inline deadline completion aggregation in `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Calibration Nudge Read-Only Service Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: backend read-only analytics helper extraction.
- Commit: `6d34b533cbf45865f74f6be9a173eed290bef573`.

Changed authority:

- No product mutation authority changed.
- `/v1/analytics/calibration_nudge` remains the public API surface and still
  owns request scoping through `get_current_user_id()`.
- Calibration nudge outcome aggregation moved behind
  `calibration_nudge_analytics_service.calibration_nudge_snapshot`.

Removed paths:

- Removed inline calibration nudge query/projection code from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- Calibration nudge event writes remain owned by `TaskManager` and canonical
  task lifecycle code.
- Analytics claim-generation extraction, output-surface writes, task lifecycle
  writes, schema changes, production repair, hosted mutable dogfood, public
  deploy/restart, and rebrand/domain migration remain blocked without
  approval.

Moved authority:

- Pure read-only calibration nudge outcome aggregation moved from the route
  body into `backend/app/services/calibration_nudge_analytics_service.py`.
- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, Redis, deployment, or ClaimCompiler authority moved.

Issues and classification:

- No GitHub issue was created because this was proactive backend extraction,
  not a discovered bug.
- Classification: product/runtime read-only refactor.

Tests and verification:

- `git diff --check`; passed.
- `python -m py_compile backend/app/api/v1/endpoints/analytics.py backend/app/services/calibration_nudge_analytics_service.py`;
  passed.
- `PYTHONPATH=backend pytest backend/tests/test_analytics_calibration_nudge.py -q`;
  passed, 8 tests.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- `/v1/analytics/calibration_nudge` path, parameters, response shape, user
  scoping, voided-row filtering, lookback filtering, accepted/dismissed counts,
  resolved/unresolved counts, acceptance rate, and delta-difference metric are
  preserved.
- No DB write, schema, production data, Redis state, hosted-public artifact, or
  public runtime changed.

Rollback note:

- Revert commit `6d34b533cbf45865f74f6be9a173eed290bef573` to restore the
  inline calibration nudge aggregation in `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Pause Prediction Read-Only Service Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: backend read-only analytics helper extraction.
- Commit: `7956b3326af69a06813421bef3672c21cdcfcfe9`.

Changed authority:

- No product mutation authority changed.
- `/v1/analytics/pause_prediction` remains the public API surface.
- Pause prediction acceptance-rate projection moved behind
  `pause_prediction_analytics_service.pause_prediction_snapshot`.

Removed paths:

- Removed inline pause-prediction summary/projection code from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- Pause prediction log writes remain owned by the pause-prediction lifecycle
  and worker paths.
- Notification lifecycle, runtime intervention wiring, schema changes,
  production repair, hosted mutable dogfood, public deploy/restart, and
  rebrand/domain migration remain blocked without approval.

Moved authority:

- Pure read-only pause-prediction aggregation moved from the route body into
  `backend/app/services/pause_prediction_analytics_service.py`.
- No mutation, exposure, provider, clean-data, notification, task, timer,
  schema, Redis, deployment, or ClaimCompiler authority moved.

Issues and classification:

- No GitHub issue was created because this was proactive backend extraction,
  not a discovered bug.
- Classification: product/runtime read-only refactor.

Tests and verification:

- `git diff --check`; passed.
- `python -m py_compile backend/app/api/v1/endpoints/analytics.py backend/app/services/pause_prediction_analytics_service.py`;
  passed.
- `PYTHONPATH=backend pytest backend/tests/test_analytics_pause_prediction.py -q`;
  passed, 5 tests.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- `/v1/analytics/pause_prediction` path, response shape, reconciled-only
  acceptance-rate denominator, snooze re-fire exclusion, by-mechanism split,
  and existing scoped-query behavior are preserved.
- No DB write, schema, production data, Redis state, hosted-public artifact, or
  public runtime changed.

Rollback note:

- Revert commit `7956b3326af69a06813421bef3672c21cdcfcfe9` to restore the
  inline pause-prediction aggregation in `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - NewTaskModal Deadline Preview Hook Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: frontend behavior-preserving NewTaskModal extraction.
- Commit: `dbfd347de3e05d553b98fba884708587c88505aa`
  (`frontend: extract deadline preview hook`).

Changed authority:

- No product mutation authority changed.
- `NewTaskModal` still owns the selected `deadlineId` and explicit user
  binding actions.
- Deadline preview remains a suggestion/render surface until the user confirms,
  picks another deadline, dismisses it, or creates a task without binding.

Removed paths:

- Removed inline deadline-preview fetch/render-ack effect code from
  `frontend/components/new-task-modal.tsx`.

Parked paths:

- Creation-nudge exposure lifecycle remains in `NewTaskModal` for now because
  it is intervention-sensitive.
- Deadline/backend parser authority, provider adapter work, schema changes,
  hosted-public mutable dogfood, public deploy/restart, and rebrand/domain
  migration remain blocked without approval.

Moved authority:

- Moved read-only deadline-preview state/effect ownership into
  `frontend/components/use-deadline-preview.ts`.
- No backend write, task/deadline canonical binding, exposure denominator,
  schema, Redis, deployment, provider, or ClaimCompiler authority moved.

Issues and classification:

- No GitHub issue was created because this was proactive R3 extraction, not a
  discovered product bug.
- Classification: frontend product/runtime refactor, exposure-sensitive but
  behavior-preserving.
- Verifier classification note: bare `pytest` first used a non-repo Python that
  lacked FastAPI. The same targeted suite passed through `.venv311`, so the
  failed attempt was classified as environment/harness selection, not product
  failure.

Tests and verification:

- `git diff --check`; passed.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- `.venv311\Scripts\python.exe -m pytest backend\tests\test_parse_deadline_preview.py -q`;
  passed, 13 tests.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- Operator read-only local-current proof before mutable verification:
  `tmp/operator-readonly-stress-2026-07-09T15-35-23-966Z/result.json`
  passed with zero count diffs and `exposure_without_render_count=0`.
- Holmesberg local-current product-loop proof:
  `tmp/browser-product-loop/2026-07-09T15-36-58-641Z/result.json` passed.
  It rendered deadline suggestions, confirmed/no-deadline/pick-another
  branches, and recorded cleanup IDs for synthetic tasks, deadlines, and
  notifications.
- Operator read-only local-current proof after mutable verification:
  `tmp/operator-readonly-stress-2026-07-09T15-43-09-399Z/result.json`
  passed with zero count diffs and no issues/warnings.

Behavior parity statement:

- No intentional user-visible behavior changed.
- Deadline preview debounce, stale-response abort behavior, edit-mode
  suppression, manual-choice precedence, render acknowledgement, confirmation,
  dismissal, pick-another, and explicit binding behavior are preserved.
- No production repair, schema migration, public deploy/restart, hosted-public
  artifact mutation, or operator-account product mutation occurred.

Rollback note:

- Revert commit `dbfd347de3e05d553b98fba884708587c88505aa` to restore the
  deadline-preview effect inline in `NewTaskModal`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Backend Pytest Wrapper Harness Hardening

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: S1c verifier/harness hardening.
- Commit: `4ba2cf7058bfb99d9e0d09dff974ffad5680f46f`
  (`scripts: add backend pytest wrapper`).

Changed authority:

- No product/runtime authority changed.
- Local backend test invocation now has an explicit repo-environment wrapper:
  `scripts/run_backend_pytest.ps1`.

Removed paths:

- No runtime path removed.
- The unsafe habit of relying on ambient `pytest` resolution is deprecated for
  local proof commands.

Parked paths:

- CI backend test semantics remain unchanged in this seam.
- Full post-wave wrapper, hosted-public proof, public deploy/restart, schema
  changes, and runtime behavior remain untouched.

Moved authority:

- No app, mutation, exposure, clean-data, provider, task, timer, schema, Redis,
  or deployment authority moved.
- Harness interpreter selection is now owned by a small wrapper that prefers
  `.venv311\Scripts\python.exe` and sets `PYTHONPATH` to `backend`.

Issues and classification:

- GitHub issue: #183, `Verifier: local backend pytest can use wrong Python`.
- Classification: verifier/harness bug.
- Trigger: bare `pytest` resolved to a non-repo Python without FastAPI during
  the deadline-preview hook seam; the same targeted suite passed through the
  repo venv.

Tests and verification:

- PowerShell parser check for `scripts/run_backend_pytest.ps1`; passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_parse_deadline_preview.py -q`;
  passed, 13 tests.
- `git diff --check`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.

Behavior parity statement:

- No user-facing product behavior intentionally changed.
- No DB write, schema migration, Redis state, production data repair,
  hosted-public artifact mutation, public deploy/restart, or operator-account
  product mutation occurred.

Rollback note:

- Revert commit `4ba2cf7058bfb99d9e0d09dff974ffad5680f46f` to remove the local
  backend pytest wrapper.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Calendar/Table Local-Current Dogfood Wrapper

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: S1c verifier/harness hardening.
- Commit: `57b6826` (`scripts: support local-current calendar table dogfood`).

Changed authority:

- No product/runtime authority changed.
- Calendar/table mutation dogfood can now run against `local-current` topology
  through the standard wrapper path.

Removed paths:

- No runtime path removed.
- The post-wave wrapper no longer drops local-current port/proxy context when
  invoking the calendar/table mutation dogfood child wrapper.

Parked paths:

- Hosted-public mutable calendar/table dogfood remains out of scope without
  explicit approval.
- Physical Schedule-X drag/resize gesture synthesis remains gated; this proof
  exercises the same reschedule authority through the canonical API and browser
  render checks.

Moved authority:

- No app, mutation, exposure, clean-data, provider, task, timer, schema, Redis,
  or deployment authority moved.
- Local-current topology trust remains with `verify_runtime_topology.mjs`; the
  child wrapper now runs that verifier before mutable browser steps.

Issues and classification:

- No GitHub issue was created because this was planned S1c gate hardening, not a
  discovered product bug.
- Classification: verifier/harness and topology trust hardening.

Tests and verification:

- PowerShell parser checks for `scripts/run_calendar_table_mutation_dogfood.ps1`
  and `scripts/run_post_wave_dogfood_loop.ps1`; passed.
- `node --check .\scripts\browser_calendar_table_mutation_dogfood.mjs`; passed.
- `git diff --check`; passed.
- Negative topology proof:
  `tmp/negative-local-current-calendar-table-topology.json` failed closed when
  `local-current` was given a public frontend origin.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- Direct Holmesberg local-current calendar/table proof:
  `tmp/calendar-table-local-current-wrapper-direct/result.json` passed with
  cleanup proof, zero server 500s, no active timer, no unrendered synthetic
  creation-nudge exposures, and no non-voided synthetic tasks.
- Standard post-wave proof with calendar/table mutation:
  `tmp/post-wave-dogfood/20260709-190535-calendar-table-local-current-wrapper-standard-local-current/summary.json`
  passed with `standard_wave_proof_passed`, `cleanup.ok=true`, zero nested
  issues/warnings, and operator read-only `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional user-visible product behavior changed.
- Calendar schedule placement, immutable executed-task reschedule rejection,
  Table correction/export, voided-row visibility, and cleanup behavior were
  re-proven through existing browser dogfood.
- No production repair, schema migration, public deploy/restart,
  hosted-public artifact mutation, or operator-account product mutation
  occurred.

Rollback note:

- Revert commit `57b6826` to restore the previous local/public-only
  calendar/table dogfood wrapper behavior.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Active Timer Elapsed Clock Hook Extraction

Wave:

- Branch: `refactor/freeze-closure`.
- Seam: R3 frontend behavior-preserving extraction.
- Commit: `83fbb0807067a3296fd9eb3ddc4cc2fb0c669eb1`
  (`frontend: extract active timer elapsed clock`).

Changed authority:

- No backend, stopwatch command, mutation, Redis, schema, exposure, provider,
  or clean-data authority changed.
- Active timer elapsed/pause-counter display ownership moved from
  `frontend/components/active-timer-banner.tsx` into
  `frontend/lib/hooks/use-active-stopwatch-elapsed-clock.ts`.

Removed paths:

- Removed the inline elapsed-clock state/effects from
  `ActiveTimerBanner`.
- No user-facing timer command, pause reason, resume, switch, stop, or
  query-invalidation path was removed.

Parked paths:

- Deeper stopwatch controller extraction remains parked until command handlers
  can be split without mixing UI display state and mutation semantics.
- Hosted-public mutable dogfood, provider credential mutation, account
  hard-delete/Redis purge, physical Schedule-X drag/resize synthesis, and
  OpenClaw pending drain remain parked/gated.

Moved authority:

- Display-only elapsed timing, pause-counter anchoring, server catch-up,
  pause freeze, and resume rebase moved into the hook.
- `ActiveTimerBanner` still owns pause/resume/switch buttons, optimistic
  query updates, command error handling, and pause reason UI.

Issues and classification:

- No product bug issue was created; this was planned frontend extraction.
- GitHub issue #184 was created for an adjacent verifier/topology discovery:
  the product-loop local-current wrapper can trust stale frontend state after a
  production build. The first product-loop attempt failed before mutation with
  `no backend token resolved`; local-current topology recovery and retry passed.

Tests and verification:

- `git diff --check`; passed.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- Failed pre-mutation verifier artifact, classified as local-current
  topology/verifier state:
  `tmp/browser-product-loop/active-timer-elapsed-hook/result.json`.
- Recovery topology proof:
  `tmp/active-timer-elapsed-hook-topology-proof.json` passed with
  `frontend_build_id=local-current`, `backend_build_id=dev`, and
  `proxy_api=true`.
- Holmesberg local-current product-loop proof:
  `tmp/browser-product-loop/active-timer-elapsed-hook-retry1/result.json`
  passed with 115 checks, including timer start, pause, paused-session
  survival across refresh/navigation, pause counter anchoring, resume, stop,
  execution delta fields, export evidence, and cleanup.
- Operator read-only proof after mutable timer pass:
  `tmp/operator-readonly-stress-2026-07-09T16-30-26-103Z/result.json`
  passed with zero count diffs, `implementation_green=true`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional user-visible behavior changed.
- The active timer still prefers `elapsed_seconds`, never rewinds from
  minute-truncated polling, freezes while paused/reason-picker is open, anchors
  `current_pause_seconds`, rebases after resume, and resets on task swap.
- The product loop ended with no active Holmesberg timer and recorded cleanup
  for synthetic tasks, deadlines, and notifications.
- No production repair, schema migration, public deploy/restart,
  hosted-public artifact mutation, or operator-account product mutation
  occurred.

Rollback note:

- Revert commit `83fbb0807067a3296fd9eb3ddc4cc2fb0c669eb1` to restore the
  elapsed-clock state/effects inline in `ActiveTimerBanner`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Product Loop Local-Current Readiness Gate

Seam:

- `product-loop-local-current-readiness`

Changed authority:

- No product/runtime, mutation, exposure, provider, clean-data, schema, or
  user-facing authority changed.
- The Holmesberg product-loop wrapper now owns local-current readiness checks
  before it delegates to the mutable browser script.

Removed paths:

- Removed the wrapper's ability to enter the browser product loop on
  `local-current` without first proving browser auth helpers and runtime
  topology.

Parked paths:

- Full product-loop execution remains proportional to user-facing seams.
- Hosted-public mutable dogfood remains approval-gated.

Moved authority:

- Local-current frontend startup/readiness remains in
  `scripts/local_frontend_topology.ps1`.
- `scripts/run_holmesberg_product_loop_dogfood.ps1` now calls that helper, the
  browser auth helper self-test, and the runtime topology verifier before
  running the browser loop.

Issues and classification:

- Fixed GitHub issue #184.
- Classification: verifier/harness plus topology trust.
- Root cause: the product-loop wrapper could trust a stale or non-current local
  frontend and then fail inside the browser path instead of failing closed as a
  topology/verifier issue before mutation.

Tests and verification:

- PowerShell parser check for
  `scripts/run_holmesberg_product_loop_dogfood.ps1`; passed.
- `git diff --check`; passed.
- Negative topology proof:
  `tmp/negative-product-loop-local-current-topology.json` failed closed for a
  `local-current` proof pointed at `https://lyraos.org`.
- Cleanup-only Holmesberg local-current wrapper proof:
  `tmp/browser-product-loop/product-loop-local-current-readiness-cleanup/result.json`
  passed with real Holmesberg and operator cookies, auth helper self-test,
  runtime topology verifier, browser cleanup path, and no active timer residue.

Behavior parity statement:

- No intentional app behavior changed.
- The mutable product-loop browser script is unchanged; only the wrapper's
  preflight trust checks changed.
- Cleanup-only proof created no new synthetic product rows.

Rollback note:

- Revert commit `2be9779` to remove the wrapper preflight checks.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - R5a Archived Historical Agent Handoff

Seam:

- `r5a-archive-agent-handoff`

Changed authority:

- No runtime, product, mutation, exposure, provider, clean-data, schema, or
  user-facing authority changed.
- The stale agent handoff document moved out of the active docs root into
  `docs/archive/`.

Removed paths:

- Removed `docs/AGENT_HANDOFF.md` from the default active docs lane.

Parked paths:

- Broader repo reorganization remains parked.
- Other stale docs remain bannered and scanner-gated until a small archive move
  is justified.

Moved authority:

- `docs/archive/AGENT_HANDOFF.md` remains historical onboarding context only.
- `docs/current_transition_state.md` and `scripts/scan_refactor_contracts.py`
  now point at the archived path.

Issues and classification:

- No GitHub issue was created; this was planned R5a docs/authority cleanup.
- Historical audit and ledger references to `docs/AGENT_HANDOFF.md` were left
  intact as historical records, not active pointers.

Tests and verification:

- `python scripts/scan_refactor_contracts.py --fail-on-errors --pretty`;
  passed.
- `git diff --check`; passed.
- Active reference audit:
  `rg -n "docs/AGENT_HANDOFF\\.md" docs scripts README.md MANIFESTO.md -g "!docs/audits/**" -g "!docs/registries/refactor_stabilization_ledger.md"`;
  returned no matches.

Behavior parity statement:

- No app behavior changed.
- No runtime docs were promoted.
- The scanner continues to require the handoff's freeze/subordination banner at
  its archived path.

Rollback note:

- Revert commits `fa145f1` and `5e4c981` to restore the handoff file in the
  root docs lane and reset active pointers.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - New Task Creation-Nudge Exposure Hook

Seam:

- `new-task-creation-nudge-exposure-hook`

Changed authority:

- No backend, schema, provider, clean-data, or public claim authority changed.
- Frontend `task.creation_nudge` exposure render/suppression lifecycle moved
  from `NewTaskModal` into a dedicated hook.

Removed paths:

- Removed inline creation-nudge exposure ID caching, render-ack retry,
  suppression retry, previous-exposure cleanup, and unmount cleanup from
  `frontend/components/new-task-modal.tsx`.

Parked paths:

- Deeper `NewTaskModal` draft-state and JSX extraction remains parked until
  the next behavior-preserving seam has coverage.
- Hosted-public mutable dogfood remains approval-gated.

Moved authority:

- `frontend/lib/hooks/use-creation-nudge-exposure.ts` now owns
  creation-nudge exposure IDs, render acks, suppression acks, previous-exposure
  suppression, and unmount suppression.
- `NewTaskModal` still owns when the nudge is eligible, visible, accepted, or
  dismissed, and `frontend/lib/creation-nudge.ts` still owns pure payload
  shaping.

Issues and classification:

- No GitHub issue was created; this was planned R3 frontend extraction with
  exposure-lifecycle characterization.

Tests and verification:

- `git diff --check`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- Holmesberg local-current product-loop proof:
  `tmp/browser-product-loop/new-task-creation-nudge-exposure-hook/result.json`
  passed with 115 checks.
- Product-loop creation-nudge checks proved bounded authority lookup,
  idempotent render ack, export decision rows, export render/ack rows, and no
  unrendered synthetic creation-nudge exposure residue after cleanup.
- Operator read-only proof after mutable pass:
  `tmp/operator-readonly-stress-2026-07-09T16-58-03-492Z/result.json`
  passed with zero count diffs, `implementation_green=true`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional user-visible behavior changed.
- The nudge still renders, can be accepted or dismissed, writes the same
  decision payload on create, records render truth, suppresses discarded
  backend-ready exposures, and avoids repeat suggestions after a user decision.
- The dogfood run ended with no active Holmesberg timer and no unrendered
  synthetic creation-nudge exposures.

Rollback note:

- Revert commit `a1a1842` to restore creation-nudge exposure lifecycle logic
  inline in `NewTaskModal`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Analytics Bias Lookup Cache Helper

Seam:

- `analytics-bias-lookup-cache-helper`

Changed authority:

- No runtime authority, exposure authority, clean-data semantics, schema, or
  user-facing response shape changed.
- In-memory bias lookup cache and slow-query logging moved from the analytics
  route module into a backend service helper.

Removed paths:

- Removed cache storage, cache TTL handling, deep-copy return protection, and
  slow-query logger setup from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- Analytics route thinning remains incremental.
- Exposure emission, clean-data filters, ClaimCompiler boundaries, insight
  translators, and analytics writer paths remain in place for later seams.

Moved authority:

- `backend/app/services/analytics_bias_lookup_cache.py` now owns the
  read-only cache/logging helper for `/analytics/bias_factor/lookup`.
- `analytics.py` still owns request validation, task eligibility query,
  output-surface decision/suppression, response payload shape, and DB commits.

Issues and classification:

- No GitHub issue was created; this was planned backend read-only extraction.
- A bare `python -m pytest backend\tests\test_output_surfaces.py -q` attempt
  failed because the shell default Python lacked backend dependencies
  (`fastapi`). This was classified as runner selection, and the repo pytest
  wrapper was used for the valid proof.

Tests and verification:

- `git diff --check`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_output_surfaces.py -q`;
  passed, 29 tests.

Behavior parity statement:

- No intentional API behavior changed.
- Cached responses are still deep-copied on read/write, still expire after 30
  seconds, and slow-query logging still uses `lyraos.perf.bias_lookup`.
- Creation-nudge exposure decision/suppression and commit behavior remained in
  the route and stayed covered by output-surface tests.

Rollback note:

- Revert commit `b5dd292` to put the cache/logging helpers back in
  `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Analytics Insight Helper Extraction

Seam:

- `analytics-insight-helper-extraction`

Changed authority:

- No runtime authority, exposure lifecycle authority, clean-data semantics,
  schema, Redis behavior, or user-facing response shape changed.
- Pure insight-generator helper mechanics moved out of the analytics route.

Removed paths:

- Removed local helper definitions for time-of-day bucketing, averages,
  confidence labels, insight candidate construction, median/absolute-minute
  formatting, historical-task checks, safe category eligibility, and
  not-started checks from `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- Public insight translation, exposure render snapshots, Rule 11 hold/reopen
  logic, eligibility filtering, output-surface decisions, suppression writes,
  and DB commit boundaries remain in `analytics.py`.
- Deeper analytics route thinning remains parked until a future declared seam.

Moved authority:

- `backend/app/services/analytics_insight_helpers.py` now owns the pure helper
  functions used by analytics insight generators.
- `analytics.py` keeps the private alias names so existing tests and endpoint
  generator behavior remain stable.

Issues and classification:

- No GitHub issue was created; this was planned backend read-only extraction.

Tests and verification:

- `git diff --check`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_insights.py -q`;
  passed, 19 tests.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_output_surfaces.py -q`;
  passed, 29 tests.

Behavior parity statement:

- No intentional API or user-visible behavior changed.
- Insight generator candidate structure, confidence labels, category
  quarantine for legacy `work`, historical-task checks, not-started checks,
  public insight translation, and output-surface exposure behavior remain
  covered by existing tests.

Rollback note:

- Revert commit `c113ea6` to restore the pure helper definitions inline in
  `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Frontend Timer Invalidation Hook

Seam:

- `frontend-timer-invalidation-hook`

Changed authority:

- No timer command semantics, API payloads, optimistic task state transitions,
  schema, Redis behavior, or user-facing copy changed.
- Shared frontend timer-command cache invalidation moved behind a hook.

Removed paths:

- Removed duplicate local `refreshTimerSurfaces` wrappers from
  `frontend/components/active-timer-banner.tsx`,
  `frontend/components/pulse/PulseFocusCard.tsx`, and the paused-task switch
  chip component.

Parked paths:

- Deeper stopwatch controller extraction remains parked.
- Optimistic pause/resume/switch state transitions remain in
  `ActiveTimerBanner`; Pulse reflection/start/stop state remains in
  `PulseFocusCard`.

Moved authority:

- `frontend/lib/hooks/use-timer-command-invalidation.ts` now owns the
  client-side wrapper around `invalidateTimerCommandSurfaces`.
- `frontend/lib/query-keys.ts` remains the query-key/invalidation contract.

Issues and classification:

- No GitHub issue was created; this was planned R3 behavior-preserving
  frontend extraction.
- Initial `npm run typecheck` failed before local `.next/types` existed after
  artifact cleanup. This was classified as verifier/order artifact; local
  `npm run build` generated the types and the rerun passed.

Tests and verification:

- `git diff --check`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `npm run build` in `frontend`; passed.
- `npm run typecheck` in `frontend` after local build generated `.next/types`;
  passed.
- Holmesberg local-current product-loop proof:
  `tmp/browser-product-loop/timer-invalidation-hook/result.json`; passed with
  115 checks.
- Product-loop timer checks proved start, pause, paused-state survival across
  Pulse refresh and Calendar navigation, Today banner paused visibility,
  anchored pause counter across refresh/navigation, resume, stop, execution
  delta writes, export stopwatch/pause rows, and cleanup with no active timer.
- Operator read-only proof after mutable pass:
  `tmp/operator-readonly-stress-2026-07-09T17-31-00-523Z/result.json`;
  passed with zero count diffs, `implementation_green=true`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional user-visible behavior changed.
- Both Pulse and Today timer command surfaces still invalidate the same timer,
  task, task-range, task-evidence, pressure-map, and user caches after
  successful timer commands.
- Holmesberg synthetic tasks, deadlines, notifications, stopwatch session, and
  pause event were cleaned/voided by the product-loop harness.

Rollback note:

- Revert commit `3b1341e` to restore inline local invalidation callbacks in
  timer command surfaces.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Frontend Typecheck Stale Next Types Guard

Seam:

- `frontend-typecheck-stale-next-types-guard`

Changed authority:

- No product/runtime behavior, user-facing copy, schema, data writes, or
  hosted-public artifacts changed.
- Frontend typecheck now runs through a local verifier wrapper that can recover
  from incomplete local `.next/types` artifacts.

Removed paths:

- Removed direct `tsc --noEmit --pretty false` invocation from
  `frontend/package.json`.

Parked paths:

- Broader frontend proof ordering and public artifact rollback rehearsal remain
  future S1c/CI hardening work.
- The wrapper intentionally does not mutate `.next-public` hosted-public
  artifacts.

Moved authority:

- `frontend/scripts/typecheck.mjs` now owns local frontend typecheck execution
  and the narrow stale `.next/types` recovery path.
- TypeScript remains the source of truth for real type errors.

Issues and classification:

- GitHub issue #185 tracks the verifier/harness bug: local frontend typecheck
  can falsely fail when local generated Next route types are incomplete.

Tests and verification:

- `npm run typecheck`; passed on a normal local state.
- Negative recovery proof: after local generated `.next/types` became
  incomplete, `npm run typecheck` printed the stale local types recovery
  warning, removed local `.next/types`, reran TypeScript, and passed.
- Negative real-error proof: a temporary `frontend/tmp-typecheck-negative.ts`
  with `const shouldBeString: string = 1` made `npm run typecheck` fail with
  `TS2322`, proving the wrapper does not swallow real type errors.
- `npm run build` in `frontend`; passed.
- Final `npm run typecheck` after build regenerated complete local Next types;
  passed without recovery warning.
- `git diff --check`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.

Behavior parity statement:

- No app behavior changed.
- CI and local proof still run TypeScript; only the known stale local
  `.next/types` artifact class is repaired before a retry.

Rollback note:

- Revert commit `d642632` to restore direct package-script typecheck.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Measurement Integrity Snapshot Builder

Seam:

- `operator-measurement-integrity-snapshot-builder`

Changed authority:

- No mutation authority, exposure authority, readiness thresholds, schema,
  Redis behavior, public deployment state, or user-facing cockpit semantics
  changed.
- `/v1/operator/dashboard` remains the authority for operator auth, scoping
  reset, response assembly, dynamic issues, and readiness status.

Removed paths:

- Removed inline clean-trace denominator and dirty-reason computation from
  `backend/app/api/v1/endpoints/operator.py`.

Parked paths:

- Deeper operator response packaging and writer-path service splits remain
  parked.
- Provider connection model, auth/scoping extraction, output-surface writer
  extraction, and `models.py` split remain parked.

Moved authority:

- `backend/app/services/operator_dashboard_metrics.py` now owns the read-only
  measurement-integrity snapshot builder for:
  - eligible closed-session denominator;
  - denominator exclusions;
  - dirty reason distribution;
  - provider-only row reporting;
  - exposure contamination and unknown-exposure treatment;
  - closed/clean session counters consumed by operator user rows.

Issues and classification:

- No GitHub issue was created; this was planned R4/R2 read-only cockpit
  extraction.
- During characterization, the new unknown-exposure test initially failed
  because earlier operator-test rows remained in the test database. Classified
  as test fixture isolation, fixed by clearing the full operator-test ID band
  before asserting exact denominators.

Tests and verification:

- `git diff --check`; passed.
- `python -m compileall -q backend\app\api\v1\endpoints\operator.py backend\app\services\operator_dashboard_metrics.py`;
  passed.
- `python scripts\scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_operator_dashboard.py -q`;
  passed, 12 tests.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_operator_route_security.py backend\tests\test_exposure_ledger_v0.py backend\tests\test_output_surfaces.py -q`;
  passed, 49 tests.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T17-56-37-765Z/result.json`;
  passed with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`,
  `clean_trace_ratio=null`, and `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional API, browser, readiness, or data-write behavior changed.
- Unknown exposure remains dirty, not clean, and remains in the denominator.
- Exposure-contaminated sessions remain dirty, not excluded.
- Provider-only rows remain provenance/candidates and are reported separately
  without becoming clean execution truth.
- Operator/test/synthetic/deleted/voided/non-session rows remain excluded and
  reported through `clean_trace_ratio_basis.excluded_from_denominator`.

Rollback note:

- Revert the operator measurement-integrity snapshot builder commit to restore
  the denominator and dirty-reason computation inline in `operator.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - LyraOS Naming Rollback And Brain Dump Flow Hook

Seam:

- `lyraos-branding-rollback`
- `frontend-brain-dump-flow-hook`

Changed authority:

- No mutation authority, exposure authority, provider authority, claim
  authority, schema, Redis behavior, hosted-public deployment state, or
  readiness denominator changed.
- Public product naming returned to LyraOS/lyraos.org after the alternate-name
  direction was explicitly abandoned.
- Brain-dump parse/commit UI state remains owned by the Pulse and onboarding
  product surfaces; the shared hook only centralizes duplicated controller
  state.

Removed paths:

- Removed active app/source/script/public references to the abandoned alternate
  name.
- Renamed public AI-readable and logo asset paths back to `lyraos*`.

Parked paths:

- Full product/domain rebrand remains parked.
- Deeper frontend extraction of task modal, timer, pressure-map, and query-key
  contracts remains parked for later seams.
- Backend writer-path extraction remains parked.

Moved authority:

- `frontend/lib/hooks/use-brain-dump-flow.ts` now owns shared brain-dump
  browser controller state for parse, binding choice resolution, commit,
  partial failure review, and double-submit prevention.
- `frontend/components/pulse/BrainDumpQuickModal.tsx` and
  `frontend/components/onboarding-flow.tsx` now consume the shared hook while
  preserving their distinct UI copy and exit behavior.

Issues and classification:

- No GitHub issue was opened; the naming rollback was user-directed product
  copy/runtime-host correction before any later rebrand branch.
- The seam is mixed because the user-directed naming rollback overlapped with
  the already-active brain-dump extraction in `onboarding-flow.tsx`. The mix is
  limited to visible copy in the same file; no data/write behavior changed.

Tests and verification:

- Active repo absence checks for abandoned-name tokens, abandoned-domain tokens,
  abandoned public routes, and abandoned logo paths; passed outside ignored
  generated paths.
- `git diff --check`; passed.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `..\.venv311\Scripts\python.exe -m pytest tests/test_email_delivery.py tests/test_email_engagement.py tests/test_user_activation_email.py tests/test_reactivation_email_script.py`;
  passed, 19 tests.
- `..\.venv311\Scripts\python.exe -m pytest tests/test_brain_dump_parser.py tests/test_brain_dump_parser_stress.py tests/test_brain_dump_endpoint.py`;
  passed, 76 tests and 1 expected xfail.
- Holmesberg product-loop proof:
  `tmp/browser-product-loop/brain-dump-flow-hook/result.json`; passed with
  `ok=true`, 115 checks, no warnings, and no gated cleanup gaps.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T18-45-39-999Z/result.json`;
  passed with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional brain-dump behavior changed. Pulse quick capture and
  onboarding still parse raw text, require tier-2 binding decisions, commit
  tasks/deadlines/bindings through the same APIs, show partial commit failures,
  and preserve existing exit behavior.
- No intentional data or email behavior changed beyond restoring LyraOS name,
  lyraos.org URLs, and LyraOS sender constants after the abandoned alternate
  naming pass.

Rollback note:

- Revert the checkpoint commit to restore the prior duplicated brain-dump UI
  state and abandoned alternate naming. If only the hook extraction needs
  rollback, move parse/commit state back into the two consuming components and
  keep the LyraOS naming changes.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Stopwatch Optimistic State Helper

Seam:

- `stopwatch-optimistic-status-helper`

Changed authority:

- No stopwatch mutation authority, task lifecycle authority, schema, Redis
  behavior, backend endpoint behavior, hosted-public deployment state, or
  readiness denominator changed.
- `ActiveTimerBanner` remains the UI command surface for pause, resume, and
  switch actions.

Removed paths:

- Removed duplicated inline optimistic stopwatch-status and task-list shaping
  from `frontend/components/active-timer-banner.tsx`.

Parked paths:

- Full stopwatch controller hook extraction remains parked.
- Backend stopwatch writer/service extraction remains parked.
- Multi-task switch browser edge cases beyond the existing product-loop path
  remain parked.

Moved authority:

- `frontend/lib/stopwatch-optimistic.ts` now owns pure optimistic state
  builders for:
  - pause status flag;
  - resume status flag;
  - task-row state patches;
  - switch target/source status shaping with elapsed-second preservation.

Issues and classification:

- No GitHub issue was opened; this was planned frontend behavior-preserving
  extraction.
- Holmesberg product loop reported unrelated nonblocking issues/gates already
  known to the dogfood wrapper: onboarding gate skip, Today branch visibility
  warnings, parser title normalization, gated pressure-map recovery, disposable
  provider/account cleanup gates, calendar drag/resize gate, and OpenClaw drain
  authority gate. Timer-specific checks passed.

Tests and verification:

- `git diff --check`; passed.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- Holmesberg product-loop proof:
  `tmp/browser-product-loop/2026-07-09T18-57-29-158Z/result.json`; passed with
  `ok=true`. Timer-specific checks passed for active start, pause status,
  paused-session navigation survival, Today banner visibility, pause-counter
  anchoring, resume, stop, export stopwatch row, export pause row, and cleanup
  leaving no active timer.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T19-03-52-910Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional user-visible behavior changed.
- Pause/resume/switch still cancel in-flight stopwatch-status polls, snapshot
  before optimistic mutation, patch task rows immediately, call the same
  stopwatch endpoints, refresh the same query surfaces on success, and roll
  back to the same task states on failure.

Rollback note:

- Revert the stopwatch optimistic helper commit to inline the state builders in
  `ActiveTimerBanner` again.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Integrations Cache Invalidation Contract

Seam:

- `integrations-cache-invalidation-contract`

Changed authority:

- No provider credential authority, provider sync authority, task/deadline
  authority, schema, Redis behavior, hosted-public deployment state, or
  readiness denominator changed.
- Settings Integrations remains the user-facing connection/sync surface.

Removed paths:

- Removed repeated inline integrations/deadlines/user/cache invalidation calls
  from `frontend/components/integrations-section.tsx`.

Parked paths:

- Provider connection model remains parked.
- Disposable provider-credential browser mutation proof remains gated.
- Backend provider sync/idempotency extraction remains parked.

Moved authority:

- `frontend/lib/query-keys.ts` now owns named cache invalidation contracts for:
  - integration account cache refresh after OAuth redirect;
  - integration disconnect cache refresh including calendar-event queries;
  - Moodle feed sync cache refresh;
  - Moodle connect cache refresh including deadline predicate invalidation;
  - integration status-only refresh for Moodle WS disconnect.

Issues and classification:

- No GitHub issue was opened; this was planned frontend behavior-preserving
  extraction for the explicitly carried integrations cache-invalidation
  surface.
- Mutable provider credential dogfood was not run because disposable
  Moodle/Google credentials remain gated by the verification plan.

Tests and verification:

- `git diff --check`; passed.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T19-11-58-426Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional user-visible or data-write behavior changed.
- Each integration action invalidates the same cache families as before:
  OAuth callback refreshes integrations and current-user state; disconnect
  refreshes integrations/current-user plus calendar events; Moodle iCal/WS sync
  refreshes integrations and deadlines; Moodle connect refreshes integrations,
  deadlines, and deadline predicate queries; Moodle WS disconnect refreshes
  integrations only.

Rollback note:

- Revert the integrations cache invalidation commit to inline the invalidation
  calls in `IntegrationsSection` again.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - NewTaskModal Edit-State Sync Effect

Seam:

- `new-task-edit-sync-effect`

Changed authority:

- No task lifecycle authority, deadline authority, creation-nudge exposure
  authority, schema, Redis behavior, hosted-public deployment state, or
  readiness denominator changed.
- `NewTaskModal` still owns task edit/create/interruption modal state and user
  actions.

Removed paths:

- Removed the render-phase edit-task state synchronization branch from
  `frontend/components/new-task-modal.tsx`.

Parked paths:

- Deeper `NewTaskModal` draft-state and JSX extraction remains parked until it
  reduces real danger instead of only reshaping the component.
- Isolated browser proof for Calendar edit-entry remains parked unless the next
  seam touches Calendar editing directly; the product loop still covered the
  create/deadline/nudge paths.

Moved authority:

- Edit-task form hydration now runs in a layout effect keyed by `editingTask`
  identity instead of during render. This preserves the pre-paint edit-modal
  feel while avoiding render-time state mutation.

Issues and classification:

- No GitHub issue was opened; this was planned frontend behavior-preserving
  hardening for the R3 `NewTaskModal` surface.
- Holmesberg product-loop issues were classified as existing verifier/product
  coverage gaps unrelated to this seam: Today visibility timing, onboarding
  gate bypass, normalized brain-dump deadline copy, and gated pressure-map
  mutation. Wrapper result remained `ok=true`.

Tests and verification:

- `git diff --check`; passed.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- Holmesberg mutable product-loop proof:
  `tmp/browser-product-loop/2026-07-09T19-20-22-896Z/result.json`; passed with
  `run_id=new-task-edit-sync-effect`, cleanup proof, create/deadline/nudge
  branch checks, and no unrendered synthetic creation-nudge exposure residue.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T19-26-37-218Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional user-visible or data-write behavior changed.
- Opening an edit task still hydrates title, start/end, duration, category,
  description, and deadline binding from the edited task; create/force/
  interruption submit paths were not changed.

Rollback note:

- Revert this seam commit to restore the guarded inline render branch.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Provider Integrity Query Extraction

Seam:

- `operator-provider-integrity-query-extraction`

Changed authority:

- No provider fact authority, deadline authority, cohort-readiness denominator,
  notification lifecycle rule, schema, Redis behavior, hosted-public deployment
  state, or user-visible product behavior changed.
- `/operator` remains the read-only stop/go cockpit.

Removed paths:

- Removed duplicated provider-integrity SQL assembly from
  `backend/app/api/v1/endpoints/operator.py`.

Parked paths:

- Provider connection model remains parked.
- Provider sync/idempotency writer extraction remains parked.
- Full operator payload-builder extraction remains parked until additional
  read-only query seams prove stable.

Moved authority:

- `backend/app/services/operator_dashboard_metrics.py` now owns
  `provider_integrity_query_snapshot(...)`, the read-only query bundle that
  feeds the existing provider-integrity projection.
- The existing `provider_integrity_snapshot(...)` projection still defines the
  dashboard payload shape.

Issues and classification:

- Opened #186 for an order-dependent operator-dashboard test-harness artifact:
  running the provider-integrity test before the uninstrumented-metrics test
  leaves provider fixture rows outside the latter test's cleanup range.
- Classification: verifier/test-harness bug, not a product/runtime regression.
  File-order operator dashboard tests pass and were used as the seam proof.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\operator.py backend\app\services\operator_dashboard_metrics.py`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py -q`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `git diff --check`; passed.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T19-34-11-773Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional endpoint response change.
- Provider rows still remain provenance/candidates, missing provenance still
  reports as a warning, and provider-native completion still blocks as a truth
  violation when it completes canonical deadlines without user confirmation.

Rollback note:

- Revert this seam commit to restore provider-integrity SQL assembly inline in
  `operator.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Dashboard Test Cleanup Order Hardening

Seam:

- `operator-dashboard-test-cleanup-order-hardening`

Changed authority:

- No runtime authority, provider authority, operator readiness rule, schema,
  Redis behavior, hosted-public deployment state, or user-visible behavior
  changed.
- This is a verifier/test-harness-only seam for #186.

Removed paths:

- None.

Parked paths:

- Broader transaction-per-test fixture isolation remains parked.
- SQLAlchemy warning cleanup for provider subqueries remains parked unless it
  becomes a hard gate or obscures a real failure.

Moved authority:

- None. The operator-dashboard test cleanup helper now clears all
  `user-%@cohort.example.com` fixture users in addition to the caller-provided
  ID range, making the tests order-independent for existing fixture users.

Issues and classification:

- Fixed #186: custom ordering of operator-dashboard tests could leave provider
  fixture rows outside the next test's cleanup range and create a false
  implementation-red cockpit result.
- Classification: verifier/test-harness bug.

Tests and verification:

- Negative proof / reproduced-order check:
  `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py::test_operator_dashboard_provider_integrity_keeps_provider_completion_as_candidate tests\test_operator_dashboard.py::test_operator_dashboard_read_is_side_effect_free tests\test_operator_dashboard.py::test_operator_dashboard_marks_uninstrumented_metrics -q`;
  passed.
- File-order proof:
  `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py -q`;
  passed.
- `git diff --check`; passed.

Behavior parity statement:

- Runtime behavior is unchanged.
- The verifier now fails less falsely when targeted operator-dashboard tests are
  run outside file order.

Rollback note:

- Revert this test-only commit to restore the prior cleanup helper.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Product-Loop Funnel Query Extraction

Seam:

- `operator-product-loop-funnel-query-extraction`

Changed authority:

- No operator readiness thresholds, cohort denominator, task lifecycle
  authority, exposure authority, schema, Redis behavior, hosted-public
  deployment state, or user-visible behavior changed.
- `/operator` remains read-only and continues to expose the same
  product-loop funnel payload.

Removed paths:

- Removed product-loop funnel SQL assembly from
  `backend/app/api/v1/endpoints/operator.py`.

Parked paths:

- Full operator payload-builder extraction remains parked.
- Product-loop funnel instrumentation gaps remain parked:
  `pulse_opened`, `quick_capture_used`, `brain_dump_submitted`,
  `preview_confirmed`, and `recovery_plan_previewed`.

Moved authority:

- `backend/app/services/operator_dashboard_metrics.py` now owns
  `product_loop_funnel_query_snapshot(...)`, the read-only query bundle that
  feeds the existing `product_loop_funnel_snapshot(...)` projection.

Issues and classification:

- No GitHub issue was opened; this was planned R4 backend read-only extraction.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\operator.py backend\app\services\operator_dashboard_metrics.py`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py -q`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `git diff --check`; passed.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T19-44-40-556Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No intentional endpoint response change.
- Product-loop funnel counts, timer-start-to-clean-stop rate, activation
  quality pressure-map count, and readiness inputs remain the same.

Rollback note:

- Revert this seam commit to restore product-loop funnel SQL assembly inline in
  `operator.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Cohort Activity Query Extraction

Seam:

- `operator-cohort-activity-query-extraction`

Changed authority:

- No operator readiness thresholds, cohort denominator, exposure authority,
  provider authority, schema, Redis behavior, hosted-public deployment state, or
  user-visible behavior changed.
- `/operator` remains read-only and continues to expose the same cohort,
  retention, activation, activity-frequency, reliability, and derived full-loop
  payloads.

Removed paths:

- Removed cohort/activation/retention/activity/reliability SQL and payload
  assembly from `backend/app/api/v1/endpoints/operator.py`.

Parked paths:

- Full operator payload-builder extraction remains parked.
- Writer-path splits remain parked: output render/suppress, stopwatch stop,
  task lifecycle, auth/scoping, provider connection model, and `models.py`.

Moved authority:

- `backend/app/services/operator_dashboard_metrics.py` now owns
  `cohort_activity_query_snapshot(...)`, the read-only query/projection bundle
  for cohort activity and reliability payloads.

Issues and classification:

- No GitHub issue was opened; this was planned R4 backend read-only extraction.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\operator.py backend\app\services\operator_dashboard_metrics.py`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py -q`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `git diff --check`; passed.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T19-53-43-748Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29046061042` passed for
  `ec3bb27e142c7761a83fc5cf0404e4a2c1a0f3e9`.

Behavior parity statement:

- No intentional endpoint response change.
- Cohort segments, activation quality, retention, activity frequency,
  reliability, full-loop counts/rates, and readiness inputs remain the same.

Rollback note:

- Revert this seam commit to restore cohort activity assembly inline in
  `operator.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Operator Task/Session State Query Extraction

Seam:

- `operator-task-session-state-query-extraction`

Changed authority:

- No task lifecycle authority, stopwatch write authority, operator readiness
  thresholds, cohort denominator, schema, Redis behavior, hosted-public
  deployment state, or user-visible behavior changed.
- `/operator` remains read-only and continues to expose the same state
  invariant counts and per-user task/session summary fields.

Removed paths:

- Removed task/session state invariant SQL and per-user count assembly from
  `backend/app/api/v1/endpoints/operator.py`.

Parked paths:

- Stopwatch writer-path split remains parked.
- Task lifecycle writer-path split remains parked.
- Full operator payload-builder extraction remains parked.

Moved authority:

- `backend/app/services/operator_dashboard_metrics.py` now owns
  `task_session_state_query_snapshot(...)`, the read-only query bundle for
  task/session state invariants and per-user task/session count inputs.

Issues and classification:

- No GitHub issue was opened; this was planned R4 backend read-only extraction.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\operator.py backend\app\services\operator_dashboard_metrics.py`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_operator_dashboard.py -q`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `git diff --check`; passed.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T20-02-07-264Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29046560424` passed for
  `9c047b0e28c926db4892c5969a444fd9f7fd391e`.

Behavior parity statement:

- No intentional endpoint response change.
- Duplicate-open-session, executing/paused-without-open, executed-missing,
  open-for-executed, stale-reentry, and user-row task/session counts remain the
  same.

Rollback note:

- Revert this seam commit to restore task/session state query assembly inline in
  `operator.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Analytics Discrepancy Snapshot Extraction

Seam:

- `analytics-discrepancy-snapshot-extraction`

Changed authority:

- No analytics claim authority, exposure authority, Redis behavior, schema,
  hosted-public deployment state, or user-visible behavior changed.
- `/analytics/discrepancy` remains a read-only route returning the same
  research/product layer payload.

Removed paths:

- Removed discrepancy measurement query/projection body from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- `/analytics/insights` exposure/write routing remains parked for a later seam.
- Bias-factor lookup exposure write routing remains parked.
- ClaimCompiler, Cortex, and output-surface writer splits remain parked.

Moved authority:

- `backend/app/services/discrepancy_analytics_service.py` now owns
  `discrepancy_snapshot(...)`, the read-only discrepancy measurement query and
  summary projection.

Issues and classification:

- No GitHub issue was opened; this was planned R4 backend read-only extraction.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\analytics.py backend\app\services\discrepancy_analytics_service.py`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_unplanned_rate.py tests\test_insights.py tests\test_multiuser_isolation_adversarial.py::test_analytics_discrepancy_scoped -q`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `git diff --check`; passed.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T20-12-45-203Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
  Warning: desktop `/operator` exceeded the 12000ms latency budget at 12306ms;
  classified as non-blocking for this read-only analytics extraction because no
  operator code path changed and the proof had no issues or state diffs.
- CI proof: GitHub Actions run `29047269722` passed for
  `f260b6133b1b8a048a14d858ef5b6dff2f946e96`.

Behavior parity statement:

- No intentional endpoint response change.
- Research-layer sessions/summary, product-layer sessions/summary,
  `unplanned_execution_rate`, pause-pattern fields, and voided-count behavior
  remain the same.

Rollback note:

- Revert this seam commit to restore `/analytics/discrepancy` computation inline
  in `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Analytics Cascade Snapshot Extraction

Seam:

- `analytics-cascade-snapshot-extraction`

Changed authority:

- No analytics claim authority, exposure authority, Redis behavior, schema,
  hosted-public deployment state, or user-visible behavior changed.
- `/analytics/cascade` remains a read-only route returning the same cascade,
  morning-anchor, daily-chain, and skip-propagation payload.

Removed paths:

- Removed cascade measurement query/projection body from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- `/analytics/insights` exposure/write routing remains parked for a later seam.
- Bias-factor lookup exposure write routing remains parked.
- ClaimCompiler, Cortex, and output-surface writer splits remain parked.

Moved authority:

- `backend/app/services/cascade_analytics_service.py` now owns
  `cascade_snapshot(...)`, the read-only cascade analytics query and response
  projection.

Issues and classification:

- No GitHub issue was opened; this was planned R4 backend read-only extraction.
- First operator read-only attempt
  `tmp/operator-readonly-stress-2026-07-09T20-25-15-403Z/result.json` failed
  because mobile `/operator` timed out waiting for readiness while desktop
  passed and all counts/dashboard snapshots stayed unchanged. Classified as a
  verifier/runtime timing retry, not a product mutation or invariant failure.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\analytics.py backend\app\services\cascade_analytics_service.py`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_cascade.py -q`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `git diff --check`; passed with the existing PowerShell/Git line-ending
  warning for `analytics.py`.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T20-28-51-168Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29048262754` passed for
  `811e3c27faf8b8fda8a1910968b1dc2f56372910`.

Behavior parity statement:

- No intentional endpoint response change.
- `days_analyzed`, aggregate cascade score, skip-followed counts, summary,
  morning-anchor fields, and per-day chain fields remain the same.

Rollback note:

- Revert this seam commit to restore `/analytics/cascade` computation inline in
  `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-09 - Analytics Insight Generator Extraction

Seam:

- `analytics-insight-generator-extraction`

Changed authority:

- No exposure authority, Rule 11 gating authority, Redis seen-state behavior,
  clean-data eligibility behavior, schema, hosted-public deployment state, or
  user-visible insight behavior changed.
- `/analytics/insights` still owns HTTP response assembly and all
  render/suppression writes.

Removed paths:

- Removed inline contract-safe and profile-aware insight generator bodies from
  `backend/app/api/v1/endpoints/analytics.py`.

Parked paths:

- `/analytics/insights` writer-path extraction remains parked.
- Rule 11 reopen-gate extraction remains parked.
- Output-surface render/suppression writer split remains parked.

Moved authority:

- `backend/app/services/analytics_insight_generators.py` now owns the pure
  `_insight_*` generator functions and generator catalogs.
- `analytics.py` keeps compatibility re-exports so direct tests and historical
  imports of `_insight_*` continue to resolve.

Issues and classification:

- No GitHub issue was opened; this was planned R4 backend pure-helper
  extraction.
- Two targeted pytest invocations used stale test names:
  `test_output_surface_exposure_endpoints_emit_expected_lifecycle` /
  `test_archetype_proximity_exposure_suppresses_when_not_ready` /
  `test_analytics_insights_emits_render_lifecycle`, and
  `test_seeded_synthetic_user_insights_surface`. Classified as verifier command
  selection errors. Current covering tests were located and run successfully.

Tests and verification:

- `python -m py_compile backend\app\api\v1\endpoints\analytics.py backend\app\services\analytics_insight_generators.py`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_insights.py -q`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_output_surfaces.py -q`;
  passed.
- `cd backend; ..\.venv311\Scripts\python.exe -m pytest tests\test_lyrasim_v0.py::test_execution_outlier_validates_real_insights_product_seam -q`;
  passed.
- `python scripts/scan_refactor_contracts.py --fail-on-errors`; passed.
- `python scripts/scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift`;
  passed.
- `git diff --check`; passed with the existing PowerShell/Git line-ending
  warning for `analytics.py`.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T20-42-54-321Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29049067082` passed for
  `744c00f44e6ac203f0fb9e8d1627379a6a034744`.

Behavior parity statement:

- No intentional endpoint response change.
- Contract-safe generator output, direct `_insight_*` imports, exposure
  lifecycle behavior, Redis seen-state behavior, and no-contract-safe
  suppression behavior remain the same.

Rollback note:

- Revert this seam commit to restore insight generator functions and catalogs
  inline in `analytics.py`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-10 - Frontend Notification Client Extraction

Seam:

- `frontend-notification-client-extraction`

Changed authority:

- No notification lifecycle authority, exposure/render truth authority, backend
  endpoint behavior, schema, hosted-public deployment state, or user-visible UI
  behavior changed.
- Queue/delivery still do not count as render proof; the extracted client keeps
  the same pending fetch and `rendered`/`acted`/`dismissed`/`expired`/
  `lost_unrendered` acknowledgement payloads.

Removed paths:

- Removed inline notification client types and wrappers from
  `frontend/lib/tasks.ts`.

Parked paths:

- Broader task API client split remains parked.
- Notification lifecycle backend semantics and output-surface writer seams remain
  parked.

Moved authority:

- `frontend/lib/tasks/notifications.ts` now owns the frontend notification client
  wrapper types/functions.
- `frontend/lib/tasks.ts` remains the compatibility re-export surface for
  existing `@/lib/tasks` imports.

Issues and classification:

- No GitHub issue was opened; this was planned R3 frontend behavior-preserving
  extraction.
- Hosted-public topology proof remains blocked by GitHub issue #187 and was not
  treated as proof for this local-current seam.

Tests and verification:

- `git diff --check`; passed with the existing PowerShell/Git line-ending warning
  for touched frontend files.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T22-09-27-521Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29053815542` passed for
  `32a6736a002ae7235f4f9baa28aa21858356a2db`.

Behavior parity statement:

- No intentional endpoint, payload, import-path, or UI behavior change.
- Existing notification host and prediction banner imports continue resolving
  through `@/lib/tasks`.

Rollback note:

- Revert this seam commit to restore notification client wrappers inline in
  `frontend/lib/tasks.ts`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-10 - Frontend Stopwatch Client Extraction

Seam:

- `frontend-stopwatch-client-extraction`

Changed authority:

- No stopwatch lifecycle authority, task lifecycle authority, backend endpoint
  behavior, schema, hosted-public deployment state, or user-visible UI behavior
  changed.
- Timer command idempotency scopes remain unchanged:
  `stopwatch-start:{task_id}`, `stopwatch-stop:initial|confirmed`,
  `stopwatch-pause`, and `stopwatch-resume`.

Removed paths:

- Removed inline stopwatch client types/wrappers and inline idempotency helper
  from `frontend/lib/tasks.ts`.

Parked paths:

- Task CRUD/client extraction remains parked.
- Stopwatch backend store/lifecycle/finalizer/effects splits remain parked.
- Stale-pause backend semantics and task lifecycle writer seams remain parked.

Moved authority:

- `frontend/lib/tasks/stopwatch.ts` now owns frontend stopwatch status,
  stale-pause resolution, switch, start, stop, pause, and resume client wrappers.
- `frontend/lib/tasks/idempotency.ts` now owns the shared frontend idempotency
  header helper.
- `frontend/lib/tasks.ts` remains the compatibility re-export surface for
  existing `@/lib/tasks` imports.

Issues and classification:

- No GitHub issue was opened; this was planned R3 frontend behavior-preserving
  extraction.
- Hosted-public topology proof remains blocked by GitHub issue #187 and was not
  treated as proof for this local-current seam.

Tests and verification:

- `git diff --check`; passed with the existing PowerShell/Git line-ending warning
  for touched frontend files.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- Holmesberg local-current mutable product-loop proof:
  `tmp/browser-product-loop/2026-07-09T22-20-22-816Z/result.json`; passed with
  `116` checks, zero failures, timer start/pause/navigation/resume/stop proof,
  cleanup leaving no active timer, and no unrendered synthetic creation-nudge
  exposures.
- Operator read-only local-current proof after the mutable pass:
  `tmp/operator-readonly-stress-2026-07-09T22-26-43-226Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29054629721` passed for
  `a2ce89396816e4e47cc99fa5dc56948e4e26a596`.

Behavior parity statement:

- No intentional endpoint, payload, idempotency-header, import-path, or UI
  behavior change.
- Existing Today/Pulse/timer imports continue resolving through `@/lib/tasks`.

Rollback note:

- Revert this seam commit to restore stopwatch client wrappers and idempotency
  helper inline in `frontend/lib/tasks.ts`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-10 - Frontend Task Lifecycle Client Extraction

Seam:

- `frontend-task-lifecycle-client-extraction`

Changed authority:

- No task lifecycle authority, deadline-binding authority, table/calendar audit
  authority, backend endpoint behavior, schema, hosted-public deployment state,
  or user-visible UI behavior changed.
- Task create and mark-done idempotency scopes remain unchanged:
  `task-create` and `mark-done:{task_id}`.

Removed paths:

- Removed inline task lifecycle/client types and wrappers from
  `frontend/lib/tasks.ts`.

Parked paths:

- Remaining analytics/insights, user categories, retroactive logging, and LLM
  chip clients in `frontend/lib/tasks.ts` remain parked.
- Deeper UI component extraction remains parked.
- Backend task lifecycle writer split remains parked.

Moved authority:

- `frontend/lib/tasks/lifecycle.ts` now owns frontend task query/create,
  mark-abandoned, mark-done, execution correction, reschedule, deadline binding,
  delete, and void client wrappers.
- `frontend/lib/tasks.ts` remains the compatibility re-export surface for
  existing `@/lib/tasks` imports.

Issues and classification:

- No GitHub issue was opened; this was planned R3 frontend behavior-preserving
  extraction.
- Hosted-public topology proof remains blocked by GitHub issue #187 and was not
  treated as proof for this local-current seam.

Tests and verification:

- `git diff --check`; passed with the existing PowerShell/Git line-ending warning
  for touched frontend files.
- `npm run typecheck` in `frontend`; passed.
- `npm run build` in `frontend`; passed.
- Holmesberg local-current mutable product-loop proof:
  `tmp/browser-product-loop/2026-07-09T22-36-38-239Z/result.json`; passed with
  `116` checks, zero failures, task create/deadline binding/edit/table/export
  proof, timer proof, cleanup leaving no active timer, and no unrendered
  synthetic creation-nudge exposures.
- Operator read-only local-current proof after the mutable pass:
  `tmp/operator-readonly-stress-2026-07-09T22-43-07-014Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29055412273` passed for
  `51de94c9bb088c85870a68acc1e6bff712d332ee`.

Behavior parity statement:

- No intentional endpoint, payload, idempotency-header, import-path, or UI
  behavior change.
- Existing Pulse, Today, Calendar, Table, NewTaskModal, correction, deadline
  binding, and task-row imports continue resolving through `@/lib/tasks`.

Rollback note:

- Revert this seam commit to restore task lifecycle client wrappers inline in
  `frontend/lib/tasks.ts`.
- No data, schema, Redis, hosted-public deploy, or user cleanup rollback is
  required.

## 2026-07-10 - Operator Readiness Projection Extraction

Seam:

- `operator-readiness-projection-extraction`

Changed authority:

- No operator readiness thresholds, cohort denominator, exposure lifecycle
  invariant, backend write path, schema, hosted-public deployment state, or
  user-visible product behavior changed.
- `/operator/dashboard` continues to derive dynamic issues and readiness from
  existing read-only snapshots.

Removed paths:

- Removed inline dynamic-issue, bug-watchlist, recommendation, and cohort
  readiness projection helpers from
  `backend/app/services/operator_dashboard_metrics.py`.

Parked paths:

- Operator metric query extraction remains parked.
- Output render/suppress, stopwatch stop, task lifecycle, auth/scoping,
  provider connection model, and `models.py` writer splits remain parked.
- Hosted-public proof remains blocked by GitHub issue #187 unless public
  topology recovers without deploy/restart.

Moved authority:

- `backend/app/services/operator_readiness.py` now owns read-only operator
  dynamic issue projection, bug-watchlist projection, recommendation rows, and
  implementation/cohort readiness projection.
- `backend/app/services/operator_dashboard_metrics.py` remains the owner for
  read-only metric/query snapshots and re-exports readiness helpers for
  compatibility.
- `backend/app/api/v1/endpoints/operator.py` now imports readiness projection
  helpers from `operator_readiness`.

Issues and classification:

- No GitHub issue was opened; this was planned backend read-only extraction.
- No verifier, topology, product mutation, documentation, or measurement bug was
  discovered in this seam.

Tests and verification:

- `python -m py_compile backend\app\services\operator_readiness.py backend\app\services\operator_dashboard_metrics.py backend\app\api\v1\endpoints\operator.py`;
  passed.
- `git diff --check`; passed with existing PowerShell/Git line-ending warnings
  for touched backend files.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_operator_dashboard.py`;
  passed, `12` tests.
- `python scripts\scan_authority_surfaces.py`; passed in report-only mode with
  `missing_owner_count=0`.
- `python scripts\scan_refactor_contracts.py`; passed in report-only mode with
  zero findings.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T22-55-27-823Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29056016014` passed for
  `8150c880115094228a170a62c8b8e1b7c6b1606b`.

Behavior parity statement:

- No intentional endpoint response, readiness classifier, exposure invariant,
  operator recommendation, or cohort readiness behavior change.
- Existing compatibility imports from `operator_dashboard_metrics` continue to
  resolve.

Rollback note:

- Revert this seam commit to restore readiness projection helpers inline in
  `backend/app/services/operator_dashboard_metrics.py`.
- No data, schema, Redis, hosted-public deploy, user cleanup, or production
  repair rollback is required.

## 2026-07-10 - Operator Redis Notification Snapshot Extraction

Seam:

- `operator-redis-notification-snapshot-extraction`

Changed authority:

- No notification lifecycle authority, exposure/render invariant, Redis write
  path, backend endpoint behavior, schema, hosted-public deployment state, or
  user-visible product behavior changed.
- Redis pending notifications remain a transient queue snapshot and are not
  treated as lifecycle truth.

Removed paths:

- Removed inline Redis pending-notification snapshot and duplicate-prompt
  identity logic from `backend/app/services/operator_dashboard_metrics.py`.

Parked paths:

- Notification lifecycle write authority remains with the lifecycle/queue
  services and endpoints.
- Exposure render/suppression lifecycle writer splits remain parked.
- Hosted-public proof remains blocked by GitHub issue #187 unless public
  topology recovers without deploy/restart.

Moved authority:

- `backend/app/services/operator_notification_snapshot.py` now owns read-only
  Redis pending-notification queue snapshotting, duplicate prompt breakdowns,
  and internal-copy marker checks for `/operator`.
- `backend/app/services/operator_dashboard_metrics.py` remains the owner for
  DB-backed lifecycle metrics and re-exports the Redis snapshot helper for
  compatibility.
- `backend/app/api/v1/endpoints/operator.py` now imports the Redis snapshot
  helper from `operator_notification_snapshot` while preserving the endpoint
  `RedisClient` wrapper used by tests.

Issues and classification:

- No GitHub issue was opened; this was planned backend read-only extraction.
- No verifier, topology, product mutation, documentation, or measurement bug was
  discovered in this seam.

Tests and verification:

- `python -m py_compile backend\app\services\operator_notification_snapshot.py backend\app\services\operator_dashboard_metrics.py backend\app\api\v1\endpoints\operator.py`;
  passed.
- `git diff --check`; passed with existing PowerShell/Git line-ending warnings
  for touched backend files.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_operator_dashboard.py`;
  passed, `12` tests including duplicate legacy reminder fixtures.
- `python scripts\scan_authority_surfaces.py`; passed in report-only mode with
  `missing_owner_count=0`.
- `python scripts\scan_refactor_contracts.py`; passed in report-only mode with
  zero findings.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T23-04-25-289Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`,
  `duplicate_prompt_count=0`, and `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29056430623` passed for
  `3fec7c74100a18e6ea8f8aa44dff12b3c9ad3847`.

Behavior parity statement:

- No intentional endpoint response, duplicate-prompt classification, K02
  watchlist, notification lifecycle, or exposure invariant behavior change.
- Existing compatibility imports from `operator_dashboard_metrics` continue to
  resolve.

Rollback note:

- Revert this seam commit to restore Redis pending-notification snapshot logic
  inline in `backend/app/services/operator_dashboard_metrics.py`.
- No data, schema, Redis, hosted-public deploy, user cleanup, or production
  repair rollback is required.

## 2026-07-10 - Hosted-Public Topology Recovery Proof

Seam:

- `hosted-public-topology-recovery-proof`

Changed authority:

- No code, runtime config, deployment state, data, schema, or public restart
  changed.
- Hosted-public proof status changed from blocked to recovered based on
  read-only verification.

Removed paths:

- None.

Parked paths:

- Hosted-public mutable dogfood remains high-care and requires explicit user
  approval.
- Public deploy/restart remains approval-gated.

Moved authority:

- None.

Issues and classification:

- GitHub issue #187 (`Hosted-public topology proof times out`) was closed after
  public topology and operator read-only proof recovered without deploy/restart.
- Classification: transient topology/deployment reachability issue, recovered.

Tests and verification:

- `node scripts\verify_runtime_topology.mjs --topology public`; passed with
  `frontend_build_id=bbd168c`, `backend_build_id=dev`,
  `frontend_origin=https://lyraos.org`, and
  `api_origin=https://api.lyraos.org`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology public`;
  passed.
- Hosted-public operator read-only artifact:
  `tmp/operator-readonly-stress-2026-07-09T23-11-21-748Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`, and
  `exposure_without_render_count=0`.

Behavior parity statement:

- No app behavior changed.

Rollback note:

- No rollback is required. Reopen #187 if hosted-public read-only topology or
  operator proof fails again.

## 2026-07-10 - Operator Notification Lifecycle Snapshot Extraction

Seam:

- `operator-notification-lifecycle-snapshot-extraction`

Changed authority:

- No notification lifecycle write authority, exposure/render invariant, cohort
  denominator, backend endpoint behavior, schema, hosted-public deployment
  state, or user-visible product behavior changed.
- Queue insertion and delivery remain non-exposure. Browser render remains
  render truth. Suppression remains terminal non-render lifecycle truth.

Removed paths:

- Removed inline DB-backed notification/exposure lifecycle snapshot logic from
  `backend/app/services/operator_dashboard_metrics.py`.

Parked paths:

- Notification lifecycle write authority remains with lifecycle/queue services
  and endpoints.
- Exposure render/suppression writer splits remain parked.
- Output-surface writer extraction and deeper provider/auth/model splits remain
  parked.

Moved authority:

- `backend/app/services/operator_notification_lifecycle.py` now owns the
  read-only `/operator` notification lifecycle snapshot, including queued,
  suppressed, duplicate lifecycle prompts, and actionable
  exposure-without-render classification.
- `backend/app/services/operator_dashboard_metrics.py` remains the owner for
  other DB-backed operator metric/query snapshots and re-exports the lifecycle
  helper for compatibility.
- `backend/app/api/v1/endpoints/operator.py` now imports the lifecycle helper
  from `operator_notification_lifecycle`.

Issues and classification:

- No GitHub issue was opened; this was planned backend read-only extraction.
- No verifier, topology, product mutation, documentation, or measurement bug was
  discovered in this seam.

Tests and verification:

- `python -m py_compile backend\app\services\operator_notification_lifecycle.py backend\app\services\operator_dashboard_metrics.py backend\app\api\v1\endpoints\operator.py`;
  passed.
- `git diff --check`; passed with existing PowerShell/Git line-ending warnings
  for touched backend files.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_pytest.ps1 backend\tests\test_operator_dashboard.py`;
  passed, `12` tests including actionable exposure-without-render, suppressed
  exposure, queued decision, and duplicate reminder fixtures.
- `python scripts\scan_authority_surfaces.py`; passed in report-only mode with
  `missing_owner_count=0`.
- `python scripts\scan_refactor_contracts.py`; passed in report-only mode with
  zero findings.
- Operator read-only local-current proof:
  `tmp/operator-readonly-stress-2026-07-09T23-18-23-786Z/result.json`; passed
  with zero count diffs, zero dashboard snapshot diffs,
  `implementation_green=true`, `cohort_status=yellow`,
  `duplicate_prompt_count=0`, and `exposure_without_render_count=0`.
- CI proof: GitHub Actions run `29057070123` passed for
  `aaad4d9be9cbcec113782e1a9408f3f755524e36`.

Behavior parity statement:

- No intentional endpoint response, notification lifecycle count, queued vs.
  rendered exposure rule, suppression rule, or readiness blocker behavior
  changed.
- Existing compatibility imports from `operator_dashboard_metrics` continue to
  resolve.

Rollback note:

- Revert this seam commit to restore DB-backed notification lifecycle snapshot
  logic inline in `backend/app/services/operator_dashboard_metrics.py`.
- No data, schema, Redis, hosted-public deploy, user cleanup, or production
  repair rollback is required.

## 2026-07-10 - Post-Wave Evidence Manifest Summary

Seam:

- `post-wave-evidence-manifest-summary`

Changed authority:

- No product/runtime behavior, schema, hosted-public deployment state,
  mutation authority, exposure authority, cohort denominator, or readiness
  threshold changed.
- The post-wave wrapper remains verifier/orchestration authority only.

Removed paths:

- None.

Parked paths:

- Hosted-public mutable dogfood remains approval-gated.
- Full hermetic manifest fixture tests remain a future S1c hardening seam.
- Broader whole-wrapper count attribution remains parked unless a within-run
  count diff appears.

Moved authority:

- `scripts/run_post_wave_dogfood_loop.ps1` now surfaces a richer top-level
  `summary.json.evidence_manifest` proof index: topology class, build IDs,
  origins, readiness split, exposure-without-render count, browser
  issues/warnings, count diffs, cleanup status, gated paths, and CI/CD proof.
- `scripts/collect_github_ci_cd_proof.ps1` now accepts both repo-relative and
  absolute `-OutFile` paths. Relative paths remain repo-rooted; rooted paths
  are used directly.

Issues and classification:

- GitHub issue #188 (`CI/CD proof collection rejects absolute outfile paths`)
  was created and closed.
- Classification: CI/CD operations bug / verifier wrapper bug.
- The bug was discovered when the public quick post-wave proof reached CI/CD
  proof collection and failed after browser/topology/operator proof had passed.

Tests and verification:

- PowerShell parser checks for `scripts/run_post_wave_dogfood_loop.ps1` and
  `scripts/collect_github_ci_cd_proof.ps1`; passed.
- `git diff --check`; passed with existing PowerShell/Git line-ending warnings.
- Relative CI/CD outfile proof:
  `tmp/ci-cd-proof/relative-outfile-proof.json`; passed with `ok=true` and
  `status=ci_success`.
- Absolute CI/CD outfile proof:
  `tmp/ci-cd-proof/absolute-outfile-proof.json`; passed with `ok=true` and
  `status=ci_success`.
- Public quick post-wave proof:
  `tmp/post-wave-dogfood/20260710-023245-evidence-manifest-summary-quick-public/summary.json`;
  passed with `ok=true`, `classification=standard_wave_proof_passed`,
  `topology_class=public`, frontend build `bbd168c`, backend build `dev`,
  `implementation_green=true`, `cohort_status=yellow`,
  `exposure_without_render_count=0`, `count_diff_count=0`, and CI run
  `29057234237` represented in the manifest.
- CI proof: GitHub Actions run `29057862778` passed for
  `2c4b63f2c63236fe2e8291d5b9dd7ff2dcbe7041`.

Behavior parity statement:

- No browser product flow, API payload, readiness semantic, exposure lifecycle
  rule, cleanup requirement, or pass/fail classifier changed.
- The manifest change is additive and makes existing proof easier to audit.

Rollback note:

- Revert commit `2c4b63f` to remove the richer manifest fields and restore the
  old repo-relative-only CI/CD proof output behavior.
- No data, schema, Redis, hosted-public deploy, user cleanup, or production
  repair rollback is required.
