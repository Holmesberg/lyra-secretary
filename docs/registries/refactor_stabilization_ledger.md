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
