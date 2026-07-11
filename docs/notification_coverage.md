# Notification Coverage

> **Status:** current operator/system coverage as of 2026-05-16.

LyraOS has two notification paths with different trust boundaries:

Security companion: `docs/prodblueprint_security.md` defines the broader
trusted-alpha access-control, audit, redaction, and provider-failure boundary.

- **Per-user queue:** authenticated in-app/user-facing delivery through
  `notifications:pending:{user_id}` and `/v1/notifications/web/pending`.
- **Operator relay channel:** shared relay-polled queue for system state,
  operator-owned events, and redacted observability metadata only. The relay
  sends this through its existing Telegram bot. Non-operator behavioral
  content must not be sent to this channel.

The legacy `/v1/notifications/pending` route requires an explicit channel and
must not be used by new callers. Operator relay delivery uses either
`/v1/notifications/openclaw/pending` from an authenticated relay agent flow
or the deterministic relay in `scripts/openclaw_operator_relay.mjs`, which
drains only `notifications:pending:{OPENCLAW_OPERATOR_USER_ID}` and sends
operator messages through the existing relay Telegram configuration.

## Boundary Rules

1. User-owned behavioral events go to the per-user queue.
2. The operator relay channel can mirror operator-owned events.
3. The operator relay channel may mirror non-operator notification *metadata* only when
   the payload body, task title, raw ids, URLs, emails, user agent, notes, and
   error context are redacted or hashed. This is operator observability, not
   delivery to the user.
4. The operator relay channel may mirror in-app toast/modal output-surface *metadata*
   only. Rendered copy stays in the product and exposure ledger; the operator channel sees
   surface id, channel, hashed user/task/exposure/render ids, template, and
   trigger source.
5. Notification lifecycle render may complete an already-created
   output-surface exposure only when the lifecycle row carries both
   `exposure_id` and `surface_id`. Queue/reserve/deliver alone do not create
   exposure-render truth; browser render creates render truth, and later
   dismiss/ack/action/expiry creates interaction-outcome truth.
6. System-health alerts may go to the operator relay channel, but should avoid task
   titles, emails, tokens, iCal URLs, OAuth tokens, or raw payload bodies.
7. Repeated failures must use dedupe/cooldown through
   `app.services.operator_notifier.notify_operator`.
8. Missing operator relay delivery must never break a
   product mutation or research write.
8a. The operator relay is observation-only. It must not mutate task, session,
    provider, notification-lifecycle, exposure, or user activity state.
9. Provider outage/auth failures are provider-scoped degradations unless they
   are widespread or persistent. They should say what provider failed, whether
   reconnect is needed, and whether Lyra kept existing data.
10. Scheduler/bootstrap/database failures are Lyra platform failures. If they
   repeat, triage immediately.

## Operational Alert Contract

Every operator-facing operational alert with `warn` or `error` severity must
include the triage block from
`app.services.operator_notifier.format_alert_context`:

- affected provider/subsystem,
- affected user scope: count, unknown bootstrap scope, or hashed/redacted user
  reference from `redacted_user_ref`,
- retry behavior,
- whether user action is needed,
- whether data integrity is at risk.

Provider-auth examples:

```text
Affected provider/subsystem: Moodle Web Services / submission sync
Affected user scope: user#...
Retry behavior: Will retry on future cycles, but success requires reconnect.
User action needed: Yes - reconnect Moodle Web Services in Settings.
Data integrity risk: No deadline completion is inferred while auth is rejected.
```

Platform bootstrap example:

```text
Affected provider/subsystem: scheduler.per-user / database bootstrap
Affected user scope: unknown user count; bootstrap could not load user ids
Retry behavior: Retried, disposed the DB pool, then waits for next tick.
User action needed: No student action. Operator should triage if repeated.
Data integrity risk: No per-user mutation attempted before bootstrap completed.
```

Repeated bootstrap `OperationalError` opens a short DB backoff so scheduler
jobs do not hammer the pooler during an outage. See
`docs/incidents/2026-05-17-per-user-bootstrap-operationalerror.md`.

Per-user iteration DB outage example:

```text
Affected provider/subsystem: scheduler.per-user / timer_overflow
Affected user scope: user#...; remaining users in this job were not attempted
Retry behavior: This user iteration and remaining users were skipped; DB pool was disposed and DB backoff opened.
User action needed: No student action. Operator should triage the Lyra DB path if this repeats.
Data integrity risk: DB session was rolled back, closed, and scope was cleared before stopping fanout.
```

Per-user `OperationalError` alerts must use the caller's job name, not a
generic `_run_for_one_user` label.

Authentication database outage example:

```text
HTTP status: 503
Detail: authentication database temporarily unavailable
```

This is fail-closed platform degradation. It must not be presented as an
expired user token, must not fall back to `X-User-Id`, and must not widen user
scope.

Reminder candidate-bootstrap example:

```text
Affected provider/subsystem: scheduler.reminders / candidate bootstrap
Affected user scope: unknown candidate-user count; bootstrap could not load planned tasks in the reminder window
Retry behavior: Retried, disposed the DB pool, then waits for next scheduler tick.
User action needed: No student action. Operator should triage if this repeats.
Data integrity risk: No reminder notification or output-surface row was attempted before user iteration.
```

The former `llm_enrichment` scheduler path was retired on 2026-07-11. Its
incident records remain historical and do not describe current notification
coverage.

## Current Coverage Matrix

| Subsystem | User queue | operator relay channel | Cooldown | Notes |
| --- | --- | --- | --- | --- |
| Pre-task reminders | yes | operator-owned full text; non-operator redacted metadata only | per task, 2h | Candidate scan is upcoming-task scoped; user-facing content stays in the authenticated queue. |
| Timer overflow | yes | operator-owned full text; non-operator redacted metadata only | per session, 24h | User-facing content stays in the authenticated queue. |
| Pause prediction | yes | operator-owned full text; non-operator redacted metadata only | per firing, 10m | Candidate scan is active-session scoped; raw task ids/titles stay out of the shared bot. |
| Resume prediction | yes | operator-owned full text; non-operator redacted metadata only | job-level firing caps | Raw task title and ids stay in the per-user queue; the operator mirror sees redacted metadata only. |
| In-app toasts/modals | n/a | redacted metadata only | no content mirror | `stopwatch.micro_mirror`, `stopwatch.calibration_nudge`, `task.creation_nudge`, and similar modal/toast surfaces mirror render metadata only. Dashboard pages/cards do not mirror. |
| Scheduler health | no | yes | 30m | Job error, missed run, and max-instance events. |
| Per-user job exceptions | no | yes | 30m | Reports job/user id and exception class only. |
| Moodle iCal | no | operator-owned/system | 15m-6h | Errors, summaries, and unparseable-event drift. |
| Moodle Web Services | no | operator-owned/system | 15m-6h | Auth, decrypt, base-url, user-id, fetch failures. |
| Google Calendar | no | operator-owned only | 1h-24h | Revoked/failed operator calendar sync. |
| Stale/orphan recovery | no | operator-owned only | 30m | Recovery summaries; no user content. |
| Overdue/missed deadline sweep | no | operator-owned only | caller-specific | Existing operator-only summaries. |

## Runtime Relay

`scripts/start_openclaw_operator_relay.ps1` installs and restarts the live
operator relay bridge inside `openclaw-openclaw-gateway-1`. The relay:

- reads the Telegram bot token and allowlisted operator chat from the relay's
  existing config/environment;
- drains `notifications:pending:1` by default;
- relays `payload.message` exactly for `operator_alert` and other known
  message-bearing payloads;
- requeues on send failure instead of dropping alerts;
- is restarted by `scripts/start_public_after_reboot.ps1` and checked by
  `scripts/watch_public_runtime.ps1`.

## Explicit Non-Coverage

- Exposure/reconciliation bookkeeping should remain log/diagnostic-first unless
  failure affects user-facing state.
- Feedback has a separate operator feedback fanout because it intentionally
  includes user-submitted text and optional user email.
- Non-operator task titles, raw pause/resume/reminder/timer message bodies,
  URLs, emails, user agents, notes, error context, and raw ids must not enter
  the shared operator relay channel.
- Redacted notification metadata may enter the operator relay channel only
  through `app.services.notification_queue.mirror_user_notification_to_operator`
  and only as an observability mirror after the authenticated per-user queue
  write is attempted.
- Redacted toast/modal output-surface metadata may enter the operator relay
  channel only through
  `app.services.output_surfaces.mirror_output_surface_render_to_operator`.
  Dashboard page/card renders are excluded to avoid high-volume behavioral
  surveillance.
