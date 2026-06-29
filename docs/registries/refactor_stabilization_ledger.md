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
- Jarvis deletion remains parked; current registry marks Jarvis as parked or
  compatibility-only until S1b chooses the code path.
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

- OpenClaw relay reliability remains in S1b follow-up.
- Jarvis compatibility vs hard-disable remains in S1b follow-up.
- Admin/dashboard consolidation remains in S1b/R2.

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

- Durable backend-side operator-alert dedupe remains a later S1b seam.
- Jarvis compatibility vs hard-disable remains in S1b follow-up.
- Admin/dashboard consolidation remains in S1b/R2.

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
- Jarvis compatibility vs hard-disable remains in S1b follow-up.
- Admin/dashboard consolidation remains in S1b/R2.

Moved authority:

- Redis now owns cross-process/cross-restart operator-alert cooldown state for
  deduped alerts.

Tests and verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest tests/test_operator_notifier.py tests/test_scheduler_degradation_contract.py tests/test_per_user_worker_helper.py -q`

Rollback note:

- Revert the durable operator-alert dedupe seam commit only. This restores
  process-local cooldown behavior; any existing Redis dedupe keys expire by
  their configured cooldown TTL.
