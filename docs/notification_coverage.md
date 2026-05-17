# Notification Coverage

> **Status:** current operator/system coverage as of 2026-05-16.

LyraOS has two notification paths with different trust boundaries:

Security companion: `docs/prodblueprint_security.md` defines the broader
trusted-alpha access-control, audit, redaction, and provider-failure boundary.

- **Per-user queue:** authenticated in-app/user-facing delivery through
  `notifications:pending:{user_id}` and `/v1/notifications/pending`.
- **Operator channel:** shared Telegram bot for system state and
  operator-owned events only. Non-operator behavioral content must not be sent
  to this channel.

## Boundary Rules

1. User-owned behavioral events go to the per-user queue.
2. Operator Telegram can mirror operator-owned events.
3. System-health alerts may go to operator Telegram, but should avoid task
   titles, emails, tokens, iCal URLs, OAuth tokens, or raw payload bodies.
4. Repeated failures must use dedupe/cooldown through
   `app.services.operator_notifier.notify_operator`.
5. Missing Telegram credentials or Telegram delivery failure must never break a
   product mutation or research write.
6. Provider outage/auth failures are provider-scoped degradations unless they
   are widespread or persistent. They should say what provider failed, whether
   reconnect is needed, and whether Lyra kept existing data.
7. Scheduler/bootstrap/database failures are Lyra platform failures. If they
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

LLM enrichment max-instance example:

```text
Affected provider/subsystem: scheduler.health / llm_enrichment
Affected user scope: unknown; a previous instance is still running for this job
Retry behavior: This tick is skipped; scheduler tries again on the next interval.
User action needed: No student action.
Data integrity risk: Low unless the same job remains stuck across repeated intervals.
```

`llm_enrichment` is auxiliary. Max-instance warnings should not page as product
failures unless they are persistent; provider slowness should degrade semantic
enrichment, not authentication, user scoping, or core scheduling truth. See
`docs/incidents/2026-05-17-llm-enrichment-maxinstances.md`.

## Current Coverage Matrix

| Subsystem | User queue | Operator Telegram | Cooldown | Notes |
| --- | --- | --- | --- | --- |
| Pre-task reminders | yes | operator-owned only | per task, 2h | Candidate scan is upcoming-task scoped; non-operator reminders stay in the authenticated queue. |
| Timer overflow | yes | operator-owned only | per session, 24h | Non-operator timer state is not mirrored to the shared bot. |
| Pause prediction | yes | operator-owned only | per firing, 10m | Candidate scan is active-session scoped; fixes the cross-user leak risk. |
| Resume prediction | yes | operator-owned only | job-level firing caps | Existing `user.is_operator` gate remains required. |
| Scheduler health | no | yes | 30m | Job error, missed run, and max-instance events. |
| Per-user job exceptions | no | yes | 30m | Reports job/user id and exception class only. |
| Moodle iCal | no | operator-owned/system | 15m-6h | Errors, summaries, and unparseable-event drift. |
| Moodle Web Services | no | operator-owned/system | 15m-6h | Auth, decrypt, base-url, user-id, fetch failures. |
| Google Calendar | no | operator-owned only | 1h-24h | Revoked/failed operator calendar sync. |
| Notion retry | no | system/operator | 1h | Missing credentials or queue-stopping retry failure. |
| LLM enrichment | no | system | 30m | Aggregate failed/unavailable/pending counts only. |
| Stale/orphan recovery | no | operator-owned only | 30m | Recovery summaries; no user content. |
| Overdue/missed deadline sweep | no | operator-owned only | caller-specific | Existing operator-only summaries. |

## Explicit Non-Coverage

- Exposure/reconciliation bookkeeping should remain log/diagnostic-first unless
  failure affects user-facing state.
- Feedback has a separate operator feedback fanout because it intentionally
  includes user-submitted text and optional user email.
- Non-operator task titles, pause predictions, reminders, and timer events must
  not enter the shared operator Telegram channel.
